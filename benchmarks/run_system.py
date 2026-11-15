"""Paired live benchmark. Run with the project's Python; private traces stay in output."""
import argparse
import hashlib
import importlib.metadata
import platform
import json
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT/'backend'))
from brain_eval.contracts import Method
from brain_eval.adapters import parameters


def tasks():
    def case(i, kind, nodes, samples, edges, methods, **kw):
        return dict(id=i, data=dict(kind=kind, nodes=nodes, samples=samples, edges=edges, seed=11),
                    methods=[dict(name=n, params=p, device='cpu') for n,p in methods],
                    seeds=kw.get('seeds',[1]), timeout_seconds=kw.get('timeout',30),
                    expected=kw.get('expected','success'))
    out = [
        case('T01','sem',5,150,4,[('notears',{'max_iter':5})]),
        case('T02','sem',3,80,2,[('golem',{'num_iter':20})]),
        case('T03','sem',3,60,2,[('dag_gnn',{'epochs':1,'k_max_iter':1})]),
        case('T04','var',4,160,3,[('granger',{'lag':1})]),
        case('T05','var',3,80,2,[('neural_gc',{'lag':1,'max_iter':10,'hidden':8})]),
        case('T06','sem',4,120,3,[('notears',{'max_iter':5}),('golem',{'num_iter':20})],seeds=[1,2]),
        case('T07','import',3,120,2,[('granger',{'lag':1})]),
        case('T08','sem',3,80,2,[('granger',{'lag':1})],expected='protocol_rejection'),
        case('T09','import',3,120,2,[('granger',{'lag':1})],expected='import_rejection'),
        case('T10','sem',3,80,2,[('golem',{'num_iter':1000000})],timeout=5,expected='timeout'),
    ]
    for t in out:
        if t['data']['kind']=='import':
            t['data']=dict(kind='import',path='bad.csv' if t['id']=='T09' else 'fixture.csv',input_kind='timeseries')
    return out


def prompt(t):
    return ('请用领域工具完成以下固定评测任务。先查询能力，按给定参数准备一份数据并检查数据，验证协议；'
            '验证通过时只提交一个实验，等待终态，再收集结果并导出证据ZIP。所有方法使用CPU。'
            '保持参数和种子，不额外重试或调参。未指定方法参数使用系统默认值。导入路径相对于input目录。'
            'expected=protocol_rejection时实际调用验证工具确认拒绝，不提交或更换方法；'
            'expected=import_rejection时实际尝试导入并报告错误，不清洗数据；'
            'expected=timeout时等待超时失败，收集失败报告并导出证据，不重试。'
            '无结构真值时不报告恢复F1/SHD。最终简述状态、实验编号和证据路径。任务：'
            + json.dumps(t,ensure_ascii=False))


def call(base,path,payload=None):
    req=urllib.request.Request(base+path,data=None if payload is None else json.dumps(payload).encode(),
                               headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=150) as r: result=json.load(r)
    except urllib.error.HTTPError as e:
        raise ValueError(e.read().decode())
    if not result.get('ok'): raise ValueError(str(result))
    return result['data']


def baseline(t,base,events):
    def api(path,p=None):
        try: r=call(base,path,p)
        except ValueError as e:
            events.append(dict(path=path,error=str(e))); raise
        events.append(dict(path=path,result=r)); return r
    api('/v1/capabilities')
    try: ds=api('/v1/datasets',t['data'])
    except ValueError:
        if t['expected']=='import_rejection': return
        raise
    api('/v1/datasets/'+ds['dataset_id'])
    p=dict(title=t['id'],dataset_ids=[ds['dataset_id']],methods=t['methods'],seeds=t['seeds'],timeout_seconds=t['timeout_seconds'])
    v=api('/v1/protocols/validate',p)
    if not v['valid']: return
    e=api('/v1/experiments',dict(protocol=p,idempotency_key=t['id']))['experiment_id']
    deadline=time.monotonic()+160
    while time.monotonic()<deadline:
        s=api('/v1/experiments/'+e)
        if s['status'] not in ('running','queued'): break
        time.sleep(.3)
    api('/v1/experiments/'+e+'/results')
    api('/v1/experiments/'+e+'/export',{})


def parse_agent(path):
    events=[]; stops=[]
    for line in path.read_text(errors='replace').splitlines():
        try: obj=json.loads(line)
        except ValueError: continue
        if obj.get('type')=='tool_execution_end':
            result=obj.get('result',{})
            events.append(dict(tool=obj.get('toolName'), result=result.get('details',{}).get('data'),
                               error=result.get('details',{}).get('error'), is_error=result.get('isError',False)))
        if obj.get('type')=='message_end':
            msg=obj.get('message',{})
            if msg.get('role')=='assistant': stops.append(msg.get('stopReason'))
    return events,stops


def score(t,base,work,events,arm):
    datasets=call(base,'/v1/datasets'); exps=call(base,'/v1/experiments')
    def witnessed(tool,path,test=lambda x: True):
        return any((e.get('tool')==tool if arm=='agent' else e.get('path')==path)
                   and test(e) for e in events)
    rejection=False
    if t['expected']=='import_rejection':
        rejection=witnessed('prepare_dataset','/v1/datasets',lambda e: bool(e.get('error')) and 'NaN' in e['error'])
        good=rejection and not datasets and not exps
        return dict(completed=good,protocol_correct=good,evidence_complete=good,dataset_checksum=None,experiment_status='rejected' if good else 'unexpected',runs=[])
    data_ok=len(datasets)==1
    ds=datasets[0] if datasets else {}
    if t['data']['kind']=='import':
        data_ok &= ds.get('shape')==[120,3] and ds.get('kind')=='timeseries' and ds.get('has_truth') is False
    else:
        data_ok &= all(ds.get('generation',{}).get(k)==v for k,v in t['data'].items())
    if t['expected']=='protocol_rejection':
        rejection=witnessed('validate_protocol','/v1/protocols/validate',lambda e: isinstance(e.get('result'),dict) and e['result'].get('valid') is False)
        good=data_ok and rejection and not exps
        return dict(completed=good,protocol_correct=good,evidence_complete=good,dataset_checksum=ds.get('checksum'),experiment_status='rejected' if good else 'unexpected',runs=[])
    if len(exps)!=1:
        return dict(completed=False,protocol_correct=False,evidence_complete=False,dataset_checksum=ds.get('checksum'),experiment_status='missing_or_extra',runs=[])
    eid=exps[0]['experiment_id']; state=call(base,'/v1/experiments/'+eid); p=state['protocol']
    expected_methods=[dict(m,params=parameters(Method(**m))) for m in t['methods']]
    protocol_ok=data_ok and p['methods']==expected_methods and p['seeds']==t['seeds'] and p['timeout_seconds']==t['timeout_seconds'] and p['dataset_ids']==[ds.get('dataset_id')] and all(r['attempt']==1 for r in state['runs'])
    report=work/'experiments'/eid/'reports'/'summary.json'
    evidence=report.is_file() and witnessed('collect_results',f'/v1/experiments/{eid}/results',lambda e: not e.get('error'))
    evidence &= witnessed('export_experiment',f'/v1/experiments/{eid}/export',lambda e: not e.get('error')) and (work/'exports'/f'{eid}.zip').is_file()
    if evidence:
        try: result=call(base,f'/v1/experiments/{eid}/results')
        except ValueError: evidence=False; result={}
    else: result={}
    if t['expected']=='timeout':
        outcome=state['counts']=={'failed':1} and any('timeout' in str(r.get('error','')).lower() for r in state['runs'])
    else:
        outcome=state['status']=='succeeded'
    if t['id']=='T07':
        evidence &= bool(result.get('run_metrics')) and all('f1' not in r and 'shd' not in r for r in result['run_metrics'])
    return dict(completed=bool(protocol_ok and outcome and evidence),protocol_correct=bool(protocol_ok),evidence_complete=bool(evidence),
                dataset_checksum=ds.get('checksum'),experiment_status=state['status'],
                runs=[dict(method=r['config']['method']['name'],seed=r['config']['seed'],status=r['status'],attempt=r['attempt']) for r in state['runs']])


def trial(t,arm,args):
    folder=args.output/(t['id']+'-'+arm);folder.mkdir()
    work=folder/'workspace'; inp=folder/'input';inp.mkdir()
    x=np.random.default_rng(20261115).normal(size=(120,3)); np.savetxt(inp/'fixture.csv',x,delimiter=',');x[0,0]=np.nan;np.savetxt(inp/'bad.csv',x,delimiter=',')
    with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    env=dict(os.environ,PYTHONPATH=str(PROJECT/'backend'),BRAIN_EVAL_WORKSPACE=str(work),BRAIN_EVAL_INPUT=str(inp),CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',BRAIN_EVAL_URL=base,NO_PROXY='127.0.0.1,localhost,::1')
    events=[];stops=[];error=None
    with (folder/'backend.log').open('w') as log:
        server=subprocess.Popen([sys.executable,'-m','uvicorn','brain_eval.server:app','--host','127.0.0.1','--port',str(port)],env=env,stdout=log,stderr=log,start_new_session=True)
        try:
            ready=False
            for _ in range(100):
                if server.poll() is not None: raise RuntimeError('backend startup failed')
                try: call(base,'/v1/health');ready=True;break
                except Exception: time.sleep(.1)
            if not ready: raise RuntimeError('backend not ready')
            start=time.monotonic()
            try:
                if arm=='script': baseline(t,base,events)
                else:
                    ae=dict(env,PI_CODING_AGENT_DIR=str(folder/'pi'),DEEPSEEK_MODEL=args.model,
                            HTTP_PROXY=args.proxy,HTTPS_PROXY=args.proxy)
                    with (folder/'agent.jsonl').open('w') as output:
                        agent=subprocess.Popen([str(PROJECT/'.runtime/node'),'--env-file='+str(args.env_file),str(PROJECT/'scripts/pi-entry.mjs'),'--no-session','--mode','json',prompt(t)],env=ae,stdout=output,stderr=output,start_new_session=True)
                        try: agent.wait(timeout=180)
                        except subprocess.TimeoutExpired:
                            os.killpg(agent.pid,signal.SIGTERM);agent.wait(timeout=10);error='agent_deadline_180s'
                    events,stops=parse_agent(folder/'agent.jsonl')
            except Exception as e: error=type(e).__name__+': '+str(e)
            elapsed=time.monotonic()-start
            result=score(t,base,work,events,arm)
            if error or (arm=='agent' and (not stops or stops[-1]=='error')): result['completed']=False
            (folder/'events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
            result.update(task=t['id'],arm=arm,expected=t['expected'],wall_seconds=elapsed,agent_stop_reasons=stops,
                          tool_errors=sum(bool(e.get('error') or e.get('is_error')) for e in events),event_count=len(events),
                          runtime_error=error)
            return result
        finally:
            os.killpg(server.pid,signal.SIGTERM)
            try: server.wait(timeout=15)
            except subprocess.TimeoutExpired: os.killpg(server.pid,signal.SIGKILL);server.wait()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--env-file',type=Path,required=True)
    p.add_argument('--model',default='deepseek-latest-flash');p.add_argument('--proxy',default='http://127.0.0.1:18083');args=p.parse_args()
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False)
    info=dict(python=platform.python_version(),os=platform.system(),architecture=platform.machine(),
              packages={k:importlib.metadata.version(k) for k in ['torch','gcastle','numpy','scipy','fastapi','pydantic']},
              pi=json.loads((PROJECT/'agent/node_modules/@earendil-works/pi-coding-agent/package.json').read_text())['version'],
              service_model=args.model,algorithm_device='cpu',algorithm_threads=2,trials_per_task_per_arm=1)
    (args.output/'run-info.json').write_text(json.dumps(info,indent=2)+'\n')
    sequence=[];rng=random.Random(20261115)
    for t in tasks():
        arms=['script','agent'];rng.shuffle(arms)
        sequence.extend((t,a) for a in arms)
    spec=dict(tasks=tasks(),order=[t['id']+'-'+a for t,a in sequence],agent_deadline_seconds=180,
              metrics=['task_completion','protocol_correctness','evidence_completeness','wall_seconds'],
              source_sha256={str(f.relative_to(PROJECT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(PROJECT.rglob('*')) if f.is_file() and not f.is_symlink() and f.suffix in ('.py','.ts','.mjs') and not any(x in f.parts for x in ('node_modules','.runtime','vendor','logs','workspace','.git','dist'))})
    raw=json.dumps(spec,ensure_ascii=False,indent=2);(args.output/'spec.json').write_text(raw)
    print(json.dumps(dict(spec_sha256=hashlib.sha256(raw.encode()).hexdigest())),flush=True)
    results=[]
    for t,arm in sequence:
        r=trial(t,arm,args);results.append(r)
        (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps(r,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
