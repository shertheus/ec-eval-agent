import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI,Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .contracts import DatasetRequest,Protocol,Submission,Action
from .storage import initialize,root,read_json
from .experiments import Scheduler,submit,inspect,recent
from .protocols import validate
from .adapters import capabilities

scheduler=Scheduler()


@asynccontextmanager
async def lifespan(app):
    initialize()
    scheduler.start()
    try: yield
    finally: scheduler.close()


app=FastAPI(title="Brain Connectivity Evaluation",version="0.1.0",lifespan=lifespan)


def ok(data): return dict(ok=True,schema_version="1",data=data)


@app.exception_handler(ValueError)
async def value_error(request,exc):
    return JSONResponse(status_code=400,content=dict(ok=False,error=dict(code="INVALID_REQUEST",message=str(exc),retryable=False)))


@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse(status_code=422,content=dict(ok=False,error=dict(code="SCHEMA_ERROR",message=str(exc),retryable=False)))


@app.get("/v1/health")
def health():
    return ok(dict(status="ready",schema_version="1",workspace=str(root()),scheduler_alive=bool(scheduler.thread and scheduler.thread.is_alive())))


@app.get("/v1/environment")
def environment():
    from .worker import environment
    result=environment()
    probe=subprocess.run(["nvidia-smi","--query-gpu=index,name,memory.total,memory.used,driver_version","--format=csv,noheader"],capture_output=True,text=True,timeout=10) if __import__('shutil').which("nvidia-smi") else None
    result["gpu_inventory"]=probe.stdout.strip() if probe and probe.returncode==0 else "unavailable"
    result["selected_gpu"]=os.environ.get("BRAIN_EVAL_GPU","0")
    return ok(result)


@app.get("/v1/capabilities")
def catalog():
    return ok(dict(methods=capabilities(),generators=["sem","var"],imports=["npy","csv"],metrics=["f1","shd","precision","recall","runtime_seconds","seed_stability_jaccard"],
                   model_note="Agent credentials configured separately; health is not an LLM validation"))


@app.post("/v1/datasets")
def dataset(request:DatasetRequest):
    env=dict(os.environ,CASTLE_BACKEND="pytorch",CUDA_VISIBLE_DEVICES="",OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2")
    try:
        p=subprocess.run([sys.executable,"-m","brain_eval.worker","dataset"],input=request.model_dump_json(),
                         capture_output=True,text=True,timeout=120,env=env)
    except subprocess.TimeoutExpired:
        raise ValueError("dataset generation exceeded 120 seconds; reduce size")
    if p.returncode:
        raise ValueError(p.stderr[-2000:])
    return ok(json.loads(p.stdout.strip().splitlines()[-1]))


@app.get("/v1/datasets")
def dataset_list():
    paths=sorted((root()/"datasets").glob("*/metadata.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:100]
    return ok([read_json(p) for p in paths])


@app.post("/v1/protocols/validate")
def validate_protocol(protocol:Protocol): return ok(validate(protocol))


@app.post("/v1/experiments")
def submit_experiment(request:Submission): return ok(submit(request))


@app.get("/v1/experiments")
def list_experiments(): return ok(recent())


@app.get("/v1/experiments/{exp_id}")
def inspect_experiment(exp_id:str,logs:bool=False): return ok(inspect(exp_id,logs))


@app.post("/v1/experiments/{exp_id}/actions")
def action(exp_id:str,request:Action): return ok(scheduler.control(exp_id,request.action))


@app.get("/v1/experiments/{exp_id}/results")
def results(exp_id:str):
    from .reports import collect
    return ok(collect(exp_id))
