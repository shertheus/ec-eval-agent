"""Immutable snapshots of observations and metadata, with separately held truth."""
import os
from pathlib import Path
import numpy as np
from .contracts import DatasetRequest
from .storage import root, identifier, checked_id, write_json, read_json, file_hash


def dataset_dir(dataset_id):
    return root()/"datasets"/checked_id(dataset_id)


def metadata(dataset_id):
    p = dataset_dir(dataset_id)/"metadata.json"
    if not p.exists():
        raise ValueError(f"dataset not found: {dataset_id}")
    return read_json(p)


def prepare(request: DatasetRequest):
    # Runs in an isolated subprocess because gCastle uses process-global RNG state.
    truth = None
    seed = request.seed
    rng = np.random.default_rng(seed)
    warnings = []
    if request.kind == "sem":
        from .compat import gcastle_networkx
        gcastle_networkx()
        from castle.datasets import DAG, IIDSimulation
        np.random.seed(seed)
        W = DAG.erdos_renyi(n_nodes=request.nodes, n_edges=request.edges,
                           weight_range=(0.5, 1.5), seed=seed)
        simulation = IIDSimulation(W, n=request.samples,
            method="linear" if request.mechanism == "linear" else "nonlinear",
            sem_type="gauss" if request.mechanism == "linear" else "mlp",
            noise_scale=request.noise_scale)
        X = np.asarray(simulation.X, dtype=float)
        truth = np.asarray(simulation.B) != 0
        kind = "iid"
        if request.mechanism != "linear":
            warnings.append("gCastle nonlinear generator noise_scale semantics differ; inspect generator version")
    elif request.kind == "var":
        n = request.nodes
        W = np.zeros((n, n))
        pairs = [(i,j) for i in range(n) for j in range(n) if i != j]
        for idx in rng.choice(len(pairs), request.edges, replace=False):
            i,j = pairs[idx]
            W[i,j] = rng.uniform(.25,.65)*rng.choice([-1,1])
        np.fill_diagonal(W,.25)
        # Row-vector transition: x[t] = x[t-1] @ W + eps; scale to stationarity.
        radius = max(abs(np.linalg.eigvals(W)))
        W *= .8/max(float(radius),.8)
        X = np.zeros((request.samples+200,n))
        for t in range(1,len(X)):
            signal = X[t-1] if request.mechanism == "linear" else np.tanh(X[t-1])
            X[t] = signal@W + rng.normal(0,request.noise_scale,n)
        X = X[200:]
        truth = W != 0
        kind = "timeseries"
    else:
        base = Path(os.environ.get("BRAIN_EVAL_INPUT", "input")).resolve()
        supplied = Path(request.path)
        path = (base/supplied).resolve() if not supplied.is_absolute() else supplied.resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError("input must be an existing file inside BRAIN_EVAL_INPUT")
        if path.stat().st_size > 100*1024**2:
            raise ValueError("input exceeds 100 MiB")
        if path.suffix == ".npy":
            X = np.load(path, allow_pickle=False)
        elif path.suffix == ".csv":
            X = np.loadtxt(path, delimiter=",")
        else:
            raise ValueError("supported inputs: numeric headerless CSV or NPY; rows are observations/time")
        kind = request.input_kind
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] < 30 or not 2 <= X.shape[1] <= 200:
        raise ValueError("data must have shape (observations>=30, 2<=nodes<=200)")
    if X.shape[0] > 100000 or not np.isfinite(X).all():
        raise ValueError("too many observations or NaN/Inf present; explicit preprocessing required")
    if np.any(X.std(axis=0) <= 1e-12):
        raise ValueError("constant channel detected; remove or resolve explicitly")
    node_ids = request.node_ids or [f"ROI-{i+1}" for i in range(X.shape[1])]
    if len(node_ids) != X.shape[1] or len(set(node_ids)) != len(node_ids):
        raise ValueError("node_ids must be unique and match columns")
    ds_id = identifier("ds")
    folder = dataset_dir(ds_id)
    folder.mkdir(parents=True)
    np.save(folder/"observations.npy",X)
    if truth is not None:
        np.save(folder/"truth.npy",truth.astype(np.uint8))
    meta = dict(dataset_id=ds_id, kind=kind, name=request.name,
                shape=list(X.shape), node_ids=node_ids, has_truth=truth is not None,
                checksum=file_hash(folder/"observations.npy"),
                sample_interval=request.sample_interval, source=request.source,
                orientation="source_row_to_target_column", warnings=warnings,
                generation=request.model_dump() if request.kind != "import" else None,
                preprocessing="none; algorithm transformations recorded per run")
    if truth is not None:
        offdiag=np.array(truth,copy=True)
        np.fill_diagonal(offdiag,False)
        meta["realized_offdiagonal_edges"]=int(offdiag.sum())
        if request.kind=="sem":
            meta["warnings"].append("ER graph n_edges is a generator setting, not an exact realized edge count; see realized_offdiagonal_edges")
    write_json(folder/"metadata.json",meta)
    return meta


def observations(dataset_id):
    meta = metadata(dataset_id)
    path = dataset_dir(dataset_id)/"observations.npy"
    if file_hash(path) != meta["checksum"]:
        raise ValueError("dataset integrity check failed")
    return np.load(path,allow_pickle=False),meta
