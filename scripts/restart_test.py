"""Run an isolated backend, interrupt a child job, restart and verify persistence."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from brain_eval.cli import request

with tempfile.TemporaryDirectory(prefix='brain-restart-') as tmp:
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    os.environ['BRAIN_EVAL_URL']=f'http://127.0.0.1:{port}'
    env=dict(os.environ,BRAIN_EVAL_WORKSPACE=tmp)
    log=open(Path(tmp)/'server.log','w')
    def start():
        p=subprocess.Popen([sys.executable,'-m','uvicorn','brain_eval.server:app','--host','127.0.0.1','--port',str(port)],env=env,stdout=log,stderr=log)
        for _ in range(100):
            try:request('/v1/health');return p
            except Exception:time.sleep(.1)
        p.terminate();raise AssertionError('backend did not start')
    p=start()
    try:
        ds=request('/v1/datasets',dict(kind='var',nodes=3,samples=80,edges=2))
        protocol=dict(dataset_ids=[ds['dataset_id']],methods=[dict(name='golem',params={'num_iter':1000000})],timeout_seconds=60)
        exp=request('/v1/experiments',dict(protocol=protocol,idempotency_key='restart'))['experiment_id']
        for _ in range(100):
            if request(f'/v1/experiments/{exp}')['counts'].get('running'):break
            time.sleep(.1)
        time.sleep(1)
        p.terminate();p.wait(timeout=15)
        p=start()
        state=request(f'/v1/experiments/{exp}')
        assert state['counts']=={'interrupted':1},state
        assert state['protocol']['methods'][0]['params']['num_iter']==1000000
        state=request(f'/v1/experiments/{exp}/actions',dict(action='retry'))
        assert state['counts'].get('queued') or state['counts'].get('running'),state
        request(f'/v1/experiments/{exp}/actions',dict(action='cancel'))
        print(json.dumps({'passed':True,'checks':['interrupted state persists','protocol preserved','explicit retry','cancellation after retry']}))
    finally:
        p.terminate();p.wait(timeout=15);log.close()
