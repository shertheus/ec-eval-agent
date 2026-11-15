"""Execute with stock gCastle wheel first on PYTHONPATH to check clean installs."""
import tempfile
import os
import json
from pathlib import Path
import castle
from brain_eval.contracts import DatasetRequest,Method
from brain_eval.datasets import prepare,observations
from brain_eval.adapters import fit

assert '.whl/' in castle.__file__,castle.__file__
with tempfile.TemporaryDirectory() as tmp:
    os.environ['BRAIN_EVAL_WORKSPACE']=tmp
    ds=prepare(DatasetRequest(kind='sem',nodes=3,edges=2,samples=60))
    X,meta=observations(ds['dataset_id'])
    configs=[Method(name='notears',params={'max_iter':2}),
             Method(name='golem',device='cuda',params={'num_iter':5}),
             Method(name='dag_gnn',device='cuda',params={'epochs':1,'k_max_iter':1})]
    for method in configs:
        graph,_,_=fit(X,method,1)
        assert graph.shape==(3,3)
    print(json.dumps(dict(passed=True,source=castle.__file__,methods=[m.name for m in configs],
                         scope='Original PyPI gCastle wheel with project compatibility code on reused CUDA runtime')))
