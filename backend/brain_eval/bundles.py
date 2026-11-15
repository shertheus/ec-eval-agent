"""Export verified evidence without raw observations or model credentials."""
import json
import os
import tempfile
import zipfile
from pathlib import Path
from .experiments import inspect
from .reports import collect
from .datasets import dataset_dir
from .storage import root, experiment_dir, attempt_dir, file_hash


def export_experiment(exp_id):
    state = inspect(exp_id)
    if state['status'] in ('queued', 'running'):
        raise ValueError('export requires a terminal experiment')
    collect(exp_id)  # Verify successful run manifests before exporting.
    files = []
    base = experiment_dir(exp_id)
    for name in ['protocol.json', 'validation.json']:
        files.append((base/name, name))
    for name in ['summary.json', 'runs.csv', 'connectivity.svg', 'report.html']:
        if (base/'reports'/name).exists():
            files.append((base/'reports'/name, 'reports/'+name))
    for run in state['runs']:
        for attempt in range(1, run['attempt']+1):
            folder = attempt_dir(exp_id, run['id'], attempt)
            for name in ['config.json', 'environment.json', 'metrics.json', 'diagnostics.json',
                         'manifest.json', 'graph.npz', 'stdout.log', 'stderr.log']:
                if (folder/name).exists():
                    files.append((folder/name, f"runs/{run['id']}/attempt-{attempt}/{name}"))
    for ds in state['protocol']['dataset_ids']:
        files.append((dataset_dir(ds)/'metadata.json', f'datasets/{ds}/metadata.json'))
    output = root()/'exports'
    output.mkdir(exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=exp_id+'-', suffix='.tmp', dir=output)
    os.close(fd)
    try:
        checksums = {}
        with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path, name in files:
                if path.is_symlink() or not path.is_file():
                    raise ValueError('export refuses symlinks and missing evidence')
                content = path.read_bytes()
                import hashlib
                checksums[name] = hashlib.sha256(content).hexdigest()
                archive.writestr(name, content)
            archive.writestr('bundle-manifest.json', json.dumps(dict(
                experiment_id=exp_id, protocol_hash=state['protocol_hash'], files=checksums,
                omitted=['raw observations', 'raw truth', 'model configuration', 'API credentials'],
                notes=['Contains metadata, environment and execution logs; review before sharing.']), indent=2))
        if inspect(exp_id) != state:
            raise ValueError('experiment changed during export; retry after it is terminal')
        target = output/(exp_id+'.zip')
        os.replace(temp, target)
        return dict(experiment_id=exp_id, path=str(target), sha256=file_hash(target),
                    bytes=target.stat().st_size, evidence_files=len(files), includes_raw_data=False)
    finally:
        Path(temp).unlink(missing_ok=True)
