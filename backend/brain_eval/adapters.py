"""Method registry and adapters. Only this module imports algorithm libraries."""
import os
import random
import numpy as np
from .contracts import Method

# type, default, minimum, maximum. Budgets are deliberately small for demonstrations.
PARAMS = {
 "notears": {"lambda1":(float,.1,0,100),"max_iter":(int,20,1,1000),"w_threshold":(float,.3,0,100)},
 "golem": {"lambda_1":(float,.02,0,100),"lambda_2":(float,5.,0,100),
           "num_iter":(int,500,1,1000000),"learning_rate":(float,.001,1e-7,1),"graph_thres":(float,.3,0,100)},
 "dag_gnn": {"epochs":(int,20,1,10000),"k_max_iter":(int,2,1,100),
             "encoder_hidden":(int,16,2,512),"decoder_hidden":(int,16,2,512),
             "batch_size":(int,100,2,10000),"graph_threshold":(float,.3,0,100)},
 "granger": {"lag":(int,2,1,20),"alpha":(float,.05,1e-8,.5)},
 "neural_gc": {"lag":(int,2,1,20),"hidden":(int,16,2,256),"max_iter":(int,100,1,100000),
               "lr":(float,.01,1e-7,1),"lam":(float,.1,1e-7,100),"lam_ridge":(float,.01,0,100)},
}


def capabilities():
    return [dict(name=name, supports_cuda=name not in ("notears","granger"),
                 input_kind="timeseries" if name in ("granger","neural_gc") else "observations",
                 assumption="lagged predictive dependencies" if name in ("granger","neural_gc") else "acyclic SEM",
                 checkpoint_resume=False,
                 parameters={k:dict(type=t.__name__,default=d,min=lo,max=hi) for k,(t,d,lo,hi) in fields.items()})
            for name,fields in PARAMS.items()]


def parameters(method: Method):
    fields=PARAMS[method.name]
    unknown=set(method.params)-set(fields)
    if unknown:
        raise ValueError(f"unsupported {method.name} parameters: {sorted(unknown)}")
    result={}
    for name,(typ,default,lo,hi) in fields.items():
        value=method.params.get(name,default)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if typ is int and int(value)!=value:
            raise ValueError(f"{name} must be an integer")
        if not lo <= value <= hi:
            raise ValueError(f"{name} must be in [{lo}, {hi}]")
        result[name]=typ(value)
    if method.device=="cuda" and method.name in ("notears","granger"):
        raise ValueError(f"{method.name} is CPU-only in this implementation")
    return result


def fit(X,method: Method,seed):
    p=parameters(method)
    np.random.seed(seed);random.seed(seed)
    import torch
    torch.set_num_threads(int(os.environ.get("BRAIN_EVAL_THREADS","2")))
    torch.manual_seed(seed)
    if method.device=="cuda":
        if not torch.cuda.is_available():
            raise ValueError("CUDA requested but unavailable; no silent CPU fallback")
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
    extra={"effective_parameters":p,"preprocessing":"none", "convergence":"not certified; inspect logs"}
    if method.name in ("notears","golem","dag_gnn"):
        from .compat import gcastle_networkx
        gcastle_networkx()
        os.environ["CASTLE_BACKEND"]="pytorch"
        from castle.algorithms import Notears,GOLEM,DAG_GNN
        cls={"notears":Notears,"golem":GOLEM,"dag_gnn":DAG_GNN}[method.name]
        args=dict(p)
        if method.name != "notears":
            args.update(device_type="gpu" if method.device=="cuda" else "cpu",device_ids=None,seed=seed)
        if method.name=="golem":
            args["checkpoint_iter"]=max(1,p["num_iter"]//5)
        algo=cls(**args)
        algo.learn(X)
        adjacency=np.asarray(algo.causal_matrix,dtype=float)
        weights=None
        if hasattr(algo,"weight_causal_matrix"):
            weights=np.asarray(algo.weight_causal_matrix,dtype=float)
        extra["native_postprocessing"]="gCastle method's threshold/pruning; inspect pinned upstream source"
    elif method.name=="granger":
        from scipy.stats import f as f_dist
        # Conditional multivariate Granger: all other lagged channels are controls.
        lag=p["lag"]; n=X.shape[1]
        Y=X[lag:]
        Z=np.concatenate([X[lag-k:len(X)-k] for k in range(1,lag+1)],axis=1)
        Z=np.column_stack([np.ones(len(Y)),Z])
        dof=len(Y)-Z.shape[1]
        if dof<=0 or np.linalg.matrix_rank(Z)<Z.shape[1]:
            raise ValueError("insufficient observations or rank-deficient lagged design")
        coef=np.linalg.lstsq(Z,Y,rcond=None)[0]
        full_sse=((Y-Z@coef)**2).sum(axis=0)
        pvalues=np.ones((n,n))
        for source in range(n):
            cols=[1+k*n+source for k in range(lag)]
            reduced=np.delete(Z,cols,axis=1)
            residual=Y-reduced@np.linalg.lstsq(reduced,Y,rcond=None)[0]
            stat=np.maximum(0,((residual**2).sum(axis=0)-full_sse)/lag)/(full_sse/dof+1e-15)
            pvalues[source]=f_dist.sf(stat,lag,dof)
        # Bonferroni threshold declared in metadata, self edges excluded.
        adjacency=pvalues < p["alpha"]/(n*(n-1))
        weights=1-pvalues
        lag_weights=coef[1:].reshape(lag,n,n)
        extra.update(pvalues=pvalues.tolist(),lag_weights=lag_weights.tolist(),lag_values=list(range(1,lag+1)),
                     threshold_rule="Bonferroni alpha / (nodes * (nodes - 1))",convergence="closed form least squares")
    else:
        from .vendor.neural_gc.cmlp import cMLP,train_model_ista
        # Original cMLP returns target x source; convert once at this interface.
        mean=X.mean(axis=0);scale=X.std(axis=0)
        normalized=(X-mean)/scale
        data=torch.tensor(normalized[None],dtype=torch.float32,device=method.device)
        model=cMLP(X.shape[1],p["lag"],[p["hidden"]]).to(method.device)
        train_model_ista(model,data,lr=p["lr"],max_iter=p["max_iter"],
                         lam=p["lam"],lam_ridge=p["lam_ridge"],penalty="GL",
                         check_every=max(1,p["max_iter"]//5),verbose=1)
        weights=model.GC(threshold=False).detach().cpu().numpy().T
        adjacency=weights>0
        raw_lag=model.GC(threshold=False,ignore_lag=False).detach().cpu().numpy()
        # Conv1d kernel runs oldest to newest; index 0 after conversion is lag 1.
        lag_weights=raw_lag[:,:,::-1].transpose(2,1,0)
        extra.update(preprocessing="per-channel z-score on supplied observations",mean=mean.tolist(),scale=scale.tolist(),
                     lag_weights=lag_weights.tolist(),lag_values=list(range(1,p["lag"]+1)),
                     threshold_rule="group-lasso nonzero input weight norm",native_orientation="target_row_source_column")
    adjacency=np.asarray(adjacency)
    if adjacency.shape!=(X.shape[1],X.shape[1]) or not np.isfinite(adjacency).all():
        raise ValueError("algorithm returned invalid adjacency")
    if weights is not None and not np.isfinite(weights).all():
        raise ValueError("algorithm returned nonfinite weights")
    extra["native_diagonal"]=np.diag(adjacency).tolist()
    adjacency=(adjacency!=0).astype(np.uint8)
    np.fill_diagonal(adjacency,0)
    import networkx as nx
    extra["is_dag"]=nx.is_directed_acyclic_graph(nx.from_numpy_array(adjacency,create_using=nx.DiGraph))
    if method.device=="cuda":
        torch.cuda.synchronize()
        extra["peak_gpu_allocated_bytes"]=torch.cuda.max_memory_allocated()
    return adjacency,weights,extra
