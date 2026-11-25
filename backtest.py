"""Matched cross-sectional rank comparisons, not a trading simulator."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite,sqrt
from statistics import mean
from validation import number, provenance, text
@dataclass(frozen=True)
class Observation:
    company: str
    as_of: datetime
    outcome_end: datetime
    label_available_at: datetime
    scores: dict
    total_return: float
    feature_available_at: dict | None = None

def ranks(xs):
    order=sorted(range(len(xs)),key=xs.__getitem__); out=[0.]*len(xs); i=0
    while i<len(xs):
        j=i+1
        while j<len(xs) and xs[order[j]]==xs[order[i]]: j+=1
        for k in order[i:j]: out[k]=(i+j+1)/2
        i=j
    return out

def spearman(a,b):
    if len(a)!=len(b) or len(a)<3 or any(not number(v) for v in (*a,*b)): return None
    x,y=ranks(a),ranks(b); mx,my=mean(x),mean(y)
    den=sqrt(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))
    return sum((v-mx)*(w-my) for v,w in zip(x,y))/den if den else None

def compare(rows, models, evaluation_cutoff):
    if not models or len(set(models))!=len(models): raise ValueError('unique models required')
    if evaluation_cutoff.utcoffset() is None: raise ValueError('timezone required')
    groups={}; seen=set(); excluded=0
    for r in rows:
        if not text(r.company): raise ValueError("company required")
        if r.feature_available_at is None: raise ValueError("feature provenance required")
        provenance(tuple(r.feature_available_at[m] for m in models if m in r.feature_available_at),len(models),r.as_of)
        if any(t.utcoffset() is None for t in (r.as_of,r.outcome_end,r.label_available_at)): raise ValueError('timezone required')
        if not r.as_of<r.outcome_end<=r.label_available_at: raise ValueError('invalid outcome chronology')
        key=(r.company,r.as_of,r.outcome_end)
        if key in seen: raise ValueError('duplicate observation')
        seen.add(key)
        if r.label_available_at>evaluation_cutoff or not number(r.total_return) or r.total_return< -1 or any(r.scores.get(m) is None or not number(r.scores[m]) for m in models): excluded+=1; continue
        groups.setdefault((r.as_of,r.outcome_end),[]).append(r)
    results=[]
    for (start,end),rs in sorted(groups.items()):
        results.append({'as_of':start,'outcome_end':end,'n':len(rs),'rank_ic':{m:spearman([r.scores[m] for r in rs],[r.total_return for r in rs]) for m in models}})
    return {'excluded':excluded,'cohorts':results,'note':'Descriptive only; no independent-sample significance or portfolio returns claimed.'}
