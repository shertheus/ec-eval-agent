"""Persistent single-host queue with process isolation and explicit retries."""
import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from .storage import (db,root,identifier,canonical,write_json,read_json,event,
                      experiment_dir,attempt_dir,checked_id)
from .protocols import validate

TERMINAL={"succeeded","failed","cancelled","interrupted"}


def submit(request):
    result=validate(request.protocol)
    if not result["valid"]: raise ValueError("; ".join(result["errors"]))
    normalized=result["normalized"]
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        existing=c.execute("SELECT id,protocol_hash FROM experiments WHERE idem=?",(request.idempotency_key,)).fetchone()
        if existing:
            if existing["protocol_hash"]!=result["protocol_hash"]:
                raise ValueError("idempotency key already used with a different protocol")
            return dict(experiment_id=existing["id"],protocol_hash=existing["protocol_hash"],reused=True)
        exp_id=identifier("exp")
        write_json(experiment_dir(exp_id)/"protocol.json",normalized)
        write_json(experiment_dir(exp_id)/"validation.json",result)
        c.execute("INSERT INTO experiments VALUES(?,?,?,?,?)",(exp_id,request.idempotency_key,result["protocol_hash"],canonical(normalized),time.time()))
        for ds in normalized["dataset_ids"]:
            for method in normalized["methods"]:
                for seed in normalized["seeds"]:
                    run_id=identifier("run")
                    config=dict(run_id=run_id,experiment_id=exp_id,dataset_id=ds,
                                dataset_checksum=normalized["dataset_checksums"][ds],method=method,
                                seed=seed,timeout_seconds=normalized["timeout_seconds"],protocol_hash=result["protocol_hash"])
                    c.execute("INSERT INTO runs(id,experiment_id,config,status) VALUES(?,?,?,?)",(run_id,exp_id,canonical(config),"queued"))
                    event(c,run_id,"queued")
    return dict(experiment_id=exp_id,protocol_hash=result["protocol_hash"],warnings=result["warnings"],run_count=result["run_count"],reused=False)


def inspect(exp_id, include_logs=False):
    checked_id(exp_id)
    with db() as c:
        exp=c.execute("SELECT * FROM experiments WHERE id=?",(exp_id,)).fetchone()
        if exp is None: raise ValueError("experiment not found")
        rows=[dict(r) for r in c.execute("SELECT * FROM runs WHERE experiment_id=? ORDER BY rowid",(exp_id,))]
        histories=[dict(r) for r in c.execute("SELECT * FROM events WHERE run_id IN (SELECT id FROM runs WHERE experiment_id=?) ORDER BY sequence",(exp_id,))]
    counts=Counter(r["status"] for r in rows)
    status="running" if counts["running"] else "queued" if counts["queued"] else (
        "succeeded" if counts["succeeded"]==len(rows) else "partial_failed" if counts["succeeded"] else "failed")
    for row in rows:
        row["config"]=json.loads(row["config"])
        if include_logs and row["attempt"]:
            folder=attempt_dir(exp_id,row["id"],row["attempt"])
            row["logs"]={name:tail(folder/name) for name in ("stdout.log","stderr.log")}
    return dict(experiment_id=exp_id,status=status,counts=dict(counts),protocol=json.loads(exp["protocol"]),
                protocol_hash=exp["protocol_hash"],runs=rows,events=histories)


def tail(path,limit=4000):
    if not path.exists(): return ""
    with path.open("rb") as f:
        f.seek(max(0,path.stat().st_size-limit))
        return f.read().decode("utf-8",errors="replace")


def recent():
    with db() as c:
        ids=[r[0] for r in c.execute("SELECT id FROM experiments ORDER BY created DESC LIMIT 20")]
    return [{k:v for k,v in inspect(e).items() if k in ("experiment_id","status","counts")} for e in ids]


class Scheduler:
    def __init__(self):
        self.stop_flag=threading.Event()
        self.guard=threading.RLock()
        self.active=None
        self.thread=None
        self.lock_file=None

    def start(self):
        self.lock_file=(root()/"scheduler.lock").open("a+")
        fcntl.flock(self.lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # A worker holds run.lock for its entire process lifetime; survive coordinator crash safely.
        with db() as c:
            for row in c.execute("SELECT * FROM runs WHERE status='running'").fetchall():
                folder=attempt_dir(row["experiment_id"],row["id"],row["attempt"])
                handle=(folder/"run.lock").open("a+")
                try:
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    handle.close()
                    raise RuntimeError(f"previous worker {row['id']} still alive; wait for it to exit before restarting backend")
                handle.close()
                status="succeeded" if (folder/"manifest.json").exists() else "interrupted"
                c.execute("UPDATE runs SET status=?,pid=NULL,ended=?,error=? WHERE id=?",(status,time.time(),"recovered after backend restart",row["id"]))
                event(c,row["id"],status,"backend restart recovery")
        self.thread=threading.Thread(target=self.loop,daemon=True)
        self.thread.start()

    def close(self):
        self.stop_flag.set()
        with self.guard:
            if self.active:
                self._terminate(self.active["process"])
                self._finish(self.active["id"],"interrupted","backend shutdown")
                self.active=None
        if self.thread: self.thread.join(timeout=8)
        if self.lock_file: self.lock_file.close()

    def _finish(self,run_id,status,error=""):
        with db() as c:
            c.execute("UPDATE runs SET status=?,pid=NULL,ended=?,error=? WHERE id=?",(status,time.time(),error,run_id))
            event(c,run_id,status,error)

    @staticmethod
    def _terminate(process):
        if process.poll() is not None: return
        try: os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError: return
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=3)

    def control(self,exp_id,action):
        inspect(exp_id)
        with self.guard:
            if action=="cancel":
                if self.active and self.active["experiment_id"]==exp_id:
                    self._terminate(self.active["process"])
                    self._finish(self.active["id"],"cancelled","user requested")
                    self.active=None
                with db() as c:
                    ids=[r[0] for r in c.execute("SELECT id FROM runs WHERE experiment_id=? AND status='queued'",(exp_id,))]
                    for rid in ids:
                        c.execute("UPDATE runs SET status='cancelled',ended=? WHERE id=?",(time.time(),rid))
                        event(c,rid,"cancelled","user requested")
            else:
                with db() as c:
                    ids=[r[0] for r in c.execute("SELECT id FROM runs WHERE experiment_id=? AND status IN ('failed','interrupted','cancelled')",(exp_id,))]
                    for rid in ids:
                        c.execute("UPDATE runs SET status='queued',error=NULL WHERE id=?",(rid,))
                        event(c,rid,"queued","explicit retry; original protocol unchanged")
        return inspect(exp_id)

    def loop(self):
        while not self.stop_flag.wait(.3):
            try:
                with self.guard:
                    self.tick()
            except Exception:
                import traceback
                traceback.print_exc()
                self.stop_flag.wait(1)

    def tick(self):
        if self.active:
            job=self.active;process=job["process"]
            if time.monotonic()-job["clock"]>job["timeout"]:
                self._terminate(process)
                self._finish(job["id"],"failed","timeout: budget exceeded; parameters unchanged")
                self.active=None
            elif process.poll() is not None:
                folder=job["folder"]
                success=process.returncode==0 and (folder/"manifest.json").exists()
                reason="" if success else tail(folder/"stderr.log",2000)
                self._finish(job["id"],"succeeded" if success else "failed",reason)
                self.active=None
            return
        with db() as c:
            row=c.execute("SELECT * FROM runs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
            if row is None: return
            row=dict(row)
            attempt=row["attempt"]+1
            folder=attempt_dir(row["experiment_id"],row["id"],attempt)
            folder.mkdir(parents=True,exist_ok=False)
            config=json.loads(row["config"])
            write_json(folder/"config.json",config)
            env=dict(os.environ)
            env.update(PYTHONUNBUFFERED="1",CASTLE_BACKEND="pytorch",OMP_NUM_THREADS="2",MKL_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2")
            env["CUDA_VISIBLE_DEVICES"] = os.environ.get("BRAIN_EVAL_GPU","0") if config["method"]["device"]=="cuda" else ""
            # Persist running state before launch so crash recovery can reconcile artifacts.
            c.execute("UPDATE runs SET status='running',attempt=?,started=?,ended=NULL,error=NULL WHERE id=?",(attempt,time.time(),row["id"]))
            event(c,row["id"],"running",f"attempt={attempt}")
        try:
            with (folder/"stdout.log").open("wb") as out,(folder/"stderr.log").open("wb") as err:
                process=subprocess.Popen([sys.executable,"-m","brain_eval.worker",str(folder/"config.json")],
                                         stdout=out,stderr=err,env=env,start_new_session=True)
            with db() as c:
                c.execute("UPDATE runs SET pid=? WHERE id=?",(process.pid,row["id"]))
            self.active=dict(id=row["id"],experiment_id=row["experiment_id"],process=process,
                             clock=time.monotonic(),timeout=config["timeout_seconds"],folder=folder)
        except Exception as e:
            self._finish(row["id"],"failed",str(e))
