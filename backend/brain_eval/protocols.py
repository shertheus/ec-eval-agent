from .contracts import Protocol,Method
from .datasets import metadata
from .adapters import parameters
from .storage import digest


def validate(protocol: Protocol):
    errors=[];warnings=[]; datasets=[]
    for ds in protocol.dataset_ids:
        try:
            datasets.append(metadata(ds))
        except ValueError as e:
            errors.append(str(e))
    normalized=protocol.model_dump()
    for idx,method in enumerate(protocol.methods):
        try:
            normalized["methods"][idx]["params"]=parameters(method)
            for data in datasets:
                if method.name in ("granger","neural_gc"):
                    if data["kind"] != "timeseries":
                        errors.append(f"{method.name} requires declared time ordering; {data['dataset_id']} is IID")
                    lag=parameters(method)["lag"]
                    if data["shape"][0]-lag <= data["shape"][1]*lag+1:
                        errors.append(f"{method.name}: too few observations for declared lag and nodes")
                elif data["kind"]=="timeseries":
                    warnings.append(f"{method.name} uses rows as observations without explicit lags; autocorrelation and DAG assumptions must be discussed")
                if not data["has_truth"]:
                    warnings.append(f"{data['dataset_id']}: no truth, no recovery F1/SHD; report edges, runtime and repeat stability")
        except ValueError as e:
            errors.append(str(e))
    normalized["dataset_checksums"]={d["dataset_id"]:d["checksum"] for d in datasets}
    normalized["metric_version"]="region-v1-reversal-cost-one-exclude-self"
    normalized["aggregation_unit"]="model seeds within each dataset; independent dataset summaries separately"
    count=len(protocol.dataset_ids)*len(protocol.methods)*len(protocol.seeds)
    return dict(valid=not errors,errors=errors,warnings=sorted(set(warnings)),
                run_count=count,timeout_budget_seconds=count*protocol.timeout_seconds,
                normalized=normalized,protocol_hash=digest(normalized))
