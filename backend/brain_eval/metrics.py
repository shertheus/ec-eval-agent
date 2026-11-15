"""Region graph metrics with explicit, tested orientation and reversal counting."""
import numpy as np


def graph_metrics(estimate, truth):
    pred = np.array(estimate,dtype=bool,copy=True)
    true = np.array(truth,dtype=bool,copy=True)
    if pred.shape != true.shape or pred.ndim != 2 or pred.shape[0] != pred.shape[1]:
        raise ValueError("square estimate and truth with same shape required")
    np.fill_diagonal(pred,False)
    np.fill_diagonal(true,False)
    tp=int((pred & true).sum()); fp=int((pred & ~true).sum()); fn=int((~pred & true).sum())
    precision=tp/(tp+fp) if tp+fp else 0.
    recall=tp/(tp+fn) if tp+fn else 0.
    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.
    # Reverse-only mismatch costs one; other directed additions/deletions cost one each.
    shd=0
    for i in range(len(pred)):
        for j in range(i+1,len(pred)):
            p=(bool(pred[i,j]),bool(pred[j,i])); t=(bool(true[i,j]),bool(true[j,i]))
            reverse=(p in [(True,False),(False,True)] and t==p[::-1])
            shd += 1 if reverse else sum(a != b for a,b in zip(p,t))
    return dict(precision=precision,recall=recall,f1=f1,shd=shd,
                tp=tp,fp=fp,fn=fn,edge_count=int(pred.sum()),
                metric_version="region-v1-reversal-cost-one-exclude-self",
                zero_denominator="zero",orientation="source_row_to_target_column")


def jaccard(a,b):
    a=np.array(a,dtype=bool,copy=True);b=np.array(b,dtype=bool,copy=True)
    np.fill_diagonal(a,False);np.fill_diagonal(b,False)
    union=(a|b).sum()
    return float((a&b).sum()/union) if union else 1.
