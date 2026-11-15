"""Deterministic HTML/CSV/SVG reporting with dataset-level seed aggregation."""
import csv
import html
import itertools
import statistics
from collections import defaultdict
import numpy as np
from .experiments import inspect
from .storage import attempt_dir,experiment_dir,read_json,write_json,file_hash
from .metrics import jaccard


def collect(exp_id):
    state=inspect(exp_id)
    rows=[];groups=defaultdict(list);failures=[]
    for run in state["runs"]:
        if run["status"]!="succeeded":
            failures.append(dict(run_id=run["id"],status=run["status"],error=run["error"]))
            continue
        cfg=run["config"];folder=attempt_dir(exp_id,run["id"],run["attempt"])
        manifest=read_json(folder/"manifest.json")
        if manifest["protocol_hash"]!=state["protocol_hash"]:
            raise ValueError("result protocol does not match experiment")
        for name,checksum in manifest["files"].items():
            if file_hash(folder/name)!=checksum: raise ValueError(f"result integrity failed: {run['id']}/{name}")
        metric=read_json(folder/"metrics.json")
        row=dict(run_id=run["id"],attempt=run["attempt"],dataset_id=cfg["dataset_id"],method=cfg["method"]["name"],
                 seed=cfg["seed"],device=cfg["method"]["device"],**metric)
        rows.append(row)
        graph=np.load(folder/"graph.npz",allow_pickle=False)["adjacency"]
        groups[(row["dataset_id"],row["method"])].append((row,graph))
    summaries=[]
    for (ds,method),items in groups.items():
        summary=dict(dataset_id=ds,method=method,successful_runs=len(items),unit="model initialization seeds within this dataset")
        for metric in ["f1","shd","runtime_seconds","edge_count"]:
            values=[float(r[metric]) for r,g in items if metric in r]
            if values:
                summary[metric+"_mean"]=statistics.mean(values)
                summary[metric+"_std"]=statistics.stdev(values) if len(values)>1 else None
        pairs=[jaccard(a[1],b[1]) for a,b in itertools.combinations(items,2)]
        summary["seed_stability_jaccard"]=statistics.mean(pairs) if pairs else None
        summaries.append(summary)
    output=experiment_dir(exp_id)/"reports"
    output.mkdir(exist_ok=True)
    result=dict(experiment_id=exp_id,status=state["status"],protocol_hash=state["protocol_hash"],
                total_runs=len(state["runs"]),successful_runs=len(rows),failed_or_pending=failures,
                run_metrics=rows,summaries=summaries,counts=state["counts"],
                notes=["F1/SHD only computed when synthetic ground truth exists.",
                       "Seed stability is optimization repeatability, not biological validity or sampling stability.",
                       "No automatic claims of statistical significance or causal identification."])
    write_json(output/"summary.json",result)
    if rows:
        with (output/"runs.csv").open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in rows))))
            writer.writeheader();writer.writerows(rows)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["svg.fonttype"]="none"
        first=next(iter(groups.values()))[0][1]
        fig,ax=plt.subplots(figsize=(5,4))
        ax.imshow(first,vmin=0,vmax=1,cmap="Blues")
        ax.set(xlabel="Target node",ylabel="Source node",title="First successful run (see run table)")
        fig.tight_layout();fig.savefig(output/"connectivity.svg");plt.close(fig)
    escaped=html.escape
    body="".join("<tr>"+"".join(f"<td>{escaped(str(r.get(k,'')))}</td>" for k in ["dataset_id","method","successful_runs","f1_mean","shd_mean","runtime_seconds_mean"])+"</tr>" for r in summaries)
    document=f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Brain evaluation {exp_id}</title>
    <style>body{{font:16px system-ui;max-width:1050px;margin:40px auto;line-height:1.6;padding:20px}}td,th{{padding:9px;border:1px solid #ccc}}table{{border-collapse:collapse}}pre{{white-space:pre-wrap;word-break:break-word}}</style>
    <h1>{escaped(state['protocol']['title'])}</h1><p>Experiment: {exp_id} · Status: {state['status']}</p>
    <p>Protocol SHA256: {state['protocol_hash']}</p><p>{len(rows)} / {len(state['runs'])} runs succeeded.</p>
    <table><tr><th>Dataset</th><th>Method</th><th>Runs</th><th>Mean F1</th><th>Mean SHD</th><th>Mean seconds</th></tr>{body}</table>
    <p>Blank recovery metrics mean no ground truth; they are not zeros. Aggregation is within each dataset across model seeds.</p>
    {'<img src="connectivity.svg" alt="Directed adjacency matrix">' if rows else ''}
    <h2>Pending or unsuccessful runs</h2><pre>{escaped(str(failures))}</pre>
    <h2>Protocol</h2><pre>{escaped(__import__('json').dumps(state['protocol'],ensure_ascii=False,indent=2))}</pre>
    <h2>Evidence</h2><p>summary.json and runs.csv contain run IDs. Each run has an attempt directory containing configuration, environment, logs, graph, metrics and a SHA256 manifest.</p>
    <h2>Interpretation</h2><p>These are method-specific graph estimates. Directional predictions alone do not establish physiological causality. Demonstration budgets are not convergence guarantees.</p></html>"""
    (output/"report.html").write_text(document)
    result["artifacts"]={p.name:dict(path=str(p),sha256=file_hash(p)) for p in output.iterdir() if p.is_file()}
    return result
