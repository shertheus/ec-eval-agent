"""One disposable process per run, with committed evidence artifacts."""
import json
import os
import platform
import sys
import time
import traceback
from importlib.metadata import version,PackageNotFoundError
from pathlib import Path
import numpy as np
from .storage import read_json,write_json,file_hash


def environment():
    packages={}
    for name in ["numpy","scipy","torch","gcastle","fastapi","uvicorn","pydantic","matplotlib","networkx"]:
        try: packages[name]=version(name)
        except PackageNotFoundError: packages[name]=None
    return dict(python=sys.version,platform=platform.platform(),packages=packages,
                cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
                cpu_threads=os.environ.get("OMP_NUM_THREADS"))


def run(config_path):
    import fcntl
    lock=(Path(config_path).parent/"run.lock").open("a+")
    fcntl.flock(lock,fcntl.LOCK_EX)
    from .contracts import Method
    from .datasets import observations,dataset_dir
    from .adapters import fit
    from .metrics import graph_metrics
    config=read_json(config_path)
    folder=Path(config_path).parent
    try:
        X,meta=observations(config["dataset_id"])
        if meta["checksum"] != config["dataset_checksum"]:
            raise ValueError("dataset changed since protocol was frozen")
        env=environment()
        method=Method.model_validate(config["method"])
        if method.device=="cuda":
            import torch
            if not torch.cuda.is_available(): raise ValueError("CUDA unavailable")
            env.update(gpu=torch.cuda.get_device_name(0),torch_cuda=torch.version.cuda)
            torch.cuda.synchronize()
        started=time.monotonic()
        adjacency,weights,diagnostics=fit(X,method,config["seed"])
        elapsed=time.monotonic()-started
        if method.name in ("notears","golem","dag_gnn"):
            import inspect
            import hashlib
            import castle.algorithms as algorithms
            cls=getattr(algorithms,{"notears":"Notears","golem":"GOLEM","dag_gnn":"DAG_GNN"}[method.name])
            env["algorithm_class_sha256"]=hashlib.sha256(inspect.getsource(cls).encode()).hexdigest()
            env["compatibility"]="gCastle 1.0.3 / NetworkX 3 ndarray aliases; project compat.py"
        arrays={"adjacency":adjacency}
        if weights is not None: arrays["weights"]=weights
        if "lag_weights" in diagnostics:
            arrays["lag_weights"]=np.asarray(diagnostics.pop("lag_weights"))
        np.savez_compressed(folder/"graph.npz",**arrays)
        metric=dict(runtime_seconds=elapsed,edge_count=int(adjacency.sum()),has_truth=meta["has_truth"])
        if meta["has_truth"]:
            metric.update(graph_metrics(adjacency,np.load(dataset_dir(config["dataset_id"])/"truth.npy",allow_pickle=False)))
        write_json(folder/"environment.json",env)
        write_json(folder/"diagnostics.json",diagnostics)
        write_json(folder/"metrics.json",metric)
        write_json(folder/"manifest.json",dict(run_id=config["run_id"],protocol_hash=config["protocol_hash"],
            node_ids=meta["node_ids"],orientation="source_row_to_target_column",evaluation_level="region",
            files={n:file_hash(folder/n) for n in ["config.json","graph.npz","metrics.json","diagnostics.json","environment.json"]}))
        print(json.dumps(dict(status="succeeded",metrics=metric)),flush=True)
    except Exception as e:
        write_json(folder/"error.json",dict(type=type(e).__name__,message=str(e)))
        traceback.print_exc()
        raise


if __name__=="__main__":
    if sys.argv[1]=="dataset":
        from .contracts import DatasetRequest
        from .datasets import prepare
        print(json.dumps(prepare(DatasetRequest.model_validate_json(sys.stdin.read()))))
    else:
        run(sys.argv[1])
