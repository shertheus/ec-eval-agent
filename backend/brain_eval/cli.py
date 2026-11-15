"""Same execution API for reproducible fixed-script baseline and Pi tools."""
import argparse
import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path


def request(path,payload=None):
    url=os.environ.get("BRAIN_EVAL_URL","http://127.0.0.1:8765")+path
    body=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=150) as r: result=json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()) from e
    if not result.get("ok"): raise RuntimeError(str(result))
    return result["data"]


def show(value): print(json.dumps(value,ensure_ascii=False,indent=2))


def demo(device="cpu",methods=None,kind="sem"):
    ds=request("/v1/datasets",dict(kind=kind,name="installation-demo",nodes=5,samples=150,edges=4,seed=11))
    specs=[]
    for name in (methods or ["notears","golem"]):
        params={"notears":{"max_iter":5},"golem":{"num_iter":30},"dag_gnn":{"epochs":2,"k_max_iter":1},
                "granger":{"lag":1},"neural_gc":{"max_iter":10,"lag":1}}[name]
        specs.append(dict(name=name,params=params,device="cpu" if name in ("notears","granger") else device))
    protocol=dict(title="Installation demo: short budget, not a scientific benchmark",dataset_ids=[ds["dataset_id"]],
                  methods=specs,seeds=[1],timeout_seconds=180)
    validation=request("/v1/protocols/validate",protocol)
    if not validation["valid"]: raise RuntimeError(str(validation))
    submitted=request("/v1/experiments",dict(protocol=protocol,idempotency_key=uuid.uuid4().hex))
    exp_id=submitted["experiment_id"]
    print(f"Experiment: {exp_id}",flush=True)
    deadline=time.monotonic()+len(specs)*190+30
    last=None
    while time.monotonic()<deadline:
        state=request(f"/v1/experiments/{exp_id}")
        if state["counts"]!=last:
            print(json.dumps(state["counts"]),flush=True);last=state["counts"]
        if state["status"] not in ("running","queued"):
            result=request(f"/v1/experiments/{exp_id}/results")
            show(result)
            if state["status"]!="succeeded": raise RuntimeError("some demo runs failed; inspect run logs")
            return
        time.sleep(1)
    raise RuntimeError(f"demo wait budget exceeded; experiment continues: {exp_id}")


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor")
    sub.add_parser("list")
    d=sub.add_parser("demo");d.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    d.add_argument("--methods",nargs="+");d.add_argument("--kind",choices=["sem","var"],default="sem")
    for cmd in ["status","results","cancel","retry","export","inspect-data"]:
        s=sub.add_parser(cmd);s.add_argument("id")
    for cmd in ["dataset","validate","submit"]:
        s=sub.add_parser(cmd);s.add_argument("file",type=Path)
    c=sub.add_parser("compare");c.add_argument("ids",nargs="+");c.add_argument("--allow-different-data",action="store_true")
    args=parser.parse_args()
    if args.command=="doctor": show(dict(health=request("/v1/health"),environment=request("/v1/environment"),capabilities=request("/v1/capabilities")))
    elif args.command=="inspect-data": show(request(f"/v1/datasets/{args.id}"))
    elif args.command=="export": show(request(f"/v1/experiments/{args.id}/export",{}))
    elif args.command=="compare": show(request("/v1/comparisons",dict(experiment_ids=args.ids,strict_dataset_match=not args.allow_different_data)))
    elif args.command=="list": show(request("/v1/experiments"))
    elif args.command=="demo": demo(args.device,args.methods,args.kind)
    elif args.command in ("cancel","retry"): show(request(f"/v1/experiments/{args.id}/actions",dict(action=args.command)))
    elif args.command=="status": show(request(f"/v1/experiments/{args.id}?logs=true"))
    elif args.command=="results": show(request(f"/v1/experiments/{args.id}/results"))
    else:
        payload=json.loads(args.file.read_text())
        path={"dataset":"/v1/datasets","validate":"/v1/protocols/validate","submit":"/v1/experiments"}[args.command]
        if args.command=="submit":payload=dict(protocol=payload,idempotency_key=uuid.uuid4().hex)
        show(request(path,payload))


if __name__=="__main__":
    try:main()
    except Exception as e:
        print(str(e),file=sys.stderr);sys.exit(1)
