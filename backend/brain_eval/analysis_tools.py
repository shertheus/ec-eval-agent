"""Dataset diagnostics and explicitly scoped comparisons of completed experiments."""
import json
import numpy as np
from .datasets import observations, metadata
from .experiments import inspect
from .reports import collect
from .storage import digest


def inspect_dataset(dataset_id):
    X, meta = observations(dataset_id)
    columns = []
    for i, name in enumerate(meta['node_ids']):
        x = X[:, i]
        lag = None
        if meta['kind'] == 'timeseries' and np.std(x[:-1]) > 0 and np.std(x[1:]) > 0:
            lag = float(np.corrcoef(x[:-1], x[1:])[0, 1])
        columns.append(dict(node_id=name, mean=float(x.mean()), std=float(x.std()),
                            minimum=float(x.min()), maximum=float(x.max()), lag1_correlation=lag))
    return dict(metadata=meta, observation_checksum_verified=True, columns=columns,
                missing_values=int((~np.isfinite(X)).sum()),
                notes=['Only aggregate statistics are returned, not raw observations.',
                       'Sample count alone does not establish adequacy or causal identifiability.',
                       'Lag-one correlation is descriptive, not a stationarity test.'])


def dataset_signature(dataset_id):
    m = metadata(dataset_id)
    return digest({k: m[k] for k in ['checksum', 'node_ids', 'kind', 'has_truth', 'sample_interval']})


def compare_experiments(experiment_ids, strict_dataset_match=True):
    if not 2 <= len(experiment_ids) <= 20 or len(set(experiment_ids)) != len(experiment_ids):
        raise ValueError('provide 2 to 20 distinct experiment IDs')
    states = [inspect(e) for e in experiment_ids]
    if any(s['status'] in ('queued', 'running') for s in states):
        raise ValueError('comparison requires terminal experiments')
    signatures = [{dataset_signature(d) for d in s['protocol']['dataset_ids']} for s in states]
    matched = all(s == signatures[0] for s in signatures[1:])
    if strict_dataset_match and not matched:
        raise ValueError('dataset contents or semantics differ; no matched comparison')
    versions = {s['protocol']['metric_version'] for s in states}
    if len(versions) != 1:
        raise ValueError('metric versions differ')
    rows = []
    failures = []
    for state in states:
        result = collect(state['experiment_id'])
        methods = {m['name']: m for m in state['protocol']['methods']}
        for summary in result['summaries']:
            method = methods[summary['method']]
            rows.append(dict(experiment_id=state['experiment_id'],
                             dataset_signature=dataset_signature(summary['dataset_id']),
                             device=method['device'], params=method['params'],
                             seeds=state['protocol']['seeds'], **summary))
        failures.extend(dict(experiment_id=state['experiment_id'], **f) for f in result['failed_or_pending'])
    return dict(experiment_ids=experiment_ids, matched_datasets=matched, metric_version=next(iter(versions)),
                rows=rows, unsuccessful_runs=failures,
                notes=['Grouped by data checksum and semantics; different groups must not be pooled.',
                       'Parameters, devices and seeds are disclosed; no automatic ranking or significance claim.',
                       'Runtime is algorithm execution time, not end-to-end agent time.'])
