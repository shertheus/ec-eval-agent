"""Real subprocess integration. Requires an isolated, running evaluation backend."""
import json
import time
import uuid
from brain_eval.cli import request

def wait(exp_id,seconds=300):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=request(f'/v1/experiments/{exp_id}')
        if result['status'] not in ('running','queued'):return result
        time.sleep(.5)
    raise AssertionError('timeout waiting for experiment')

ds=request('/v1/datasets',dict(kind='var',nodes=3,samples=80,edges=2))
protocol=dict(title='integration actual Granger',dataset_ids=[ds['dataset_id']],methods=[dict(name='granger',params={'lag':1})],seeds=[1,2],timeout_seconds=30)
exp=request('/v1/experiments',dict(protocol=protocol,idempotency_key=uuid.uuid4().hex))['experiment_id']
assert wait(exp)['status']=='succeeded'
result=request(f'/v1/experiments/{exp}/results')
assert result['successful_runs']==2
assert result['summaries'][0]['seed_stability_jaccard']==1.
assert 'report.html' in result['artifacts']
print(json.dumps({'passed':'actual subprocess, two seeds, reporting','experiment_id':exp}))

# Deliberately long GPU-free task to exercise cancellation of a real child process.
protocol.update(title='integration cancellation',methods=[dict(name='golem',params={'num_iter':1000000})],seeds=[1,2],timeout_seconds=60)
exp=request('/v1/experiments',dict(protocol=protocol,idempotency_key=uuid.uuid4().hex))['experiment_id']
for _ in range(30):
    if request(f'/v1/experiments/{exp}')['counts'].get('running'):break
    time.sleep(.2)
result=request(f'/v1/experiments/{exp}/actions',{'action':'cancel'})
assert result['counts']=={'cancelled':2},result
print(json.dumps({'passed':'running and queued task cancellation','experiment_id':exp}))

# Very short timeout verifies unsuccessful runs are not silently included in metrics.
protocol.update(title='integration timeout',methods=[dict(name='golem',params={'num_iter':1000000})],seeds=[1],timeout_seconds=5)
exp=request('/v1/experiments',dict(protocol=protocol,idempotency_key=uuid.uuid4().hex))['experiment_id']
assert wait(exp,30)['counts']=={'failed':1}
result=request(f'/v1/experiments/{exp}/results')
assert result['successful_runs']==0 and len(result['failed_or_pending'])==1
print(json.dumps({'passed':'timeout and failure disclosure','experiment_id':exp}))
