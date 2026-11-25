"""Chronological, matched-cohort experimental weight selection; no portfolio claims."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from statistics import mean
from backtest import spearman
from validation import number, text, provenance

@dataclass(frozen=True)
class Sample:
    company: str
    as_of: datetime
    outcome_end: datetime
    label_available_at: datetime
    features: tuple[float,...]
    outcome: float
    feature_available_at: tuple[datetime,...] = ()

def walk_forward(rows, candidates, boundaries, evaluation_cutoff, min_cohort=5):
    """Candidates must be predeclared. Select on mature training cohorts only.
    Test windows are disjoint by snapshot date; outcome windows may overlap.
    No significance claims. Feature timestamps required; source authenticity must be verified upstream.
    """
    rows=tuple(rows); candidates=tuple(tuple(w) for w in candidates); boundaries=tuple(boundaries)
    if len(boundaries)<2 or any(a>=b for a,b in zip(boundaries,boundaries[1:])): raise ValueError('ordered boundaries required')
    if any(t.utcoffset() is None for t in (*boundaries,evaluation_cutoff)): raise ValueError('timezone required')
    if not candidates or not candidates[0] or min_cohort<3: raise ValueError('invalid configuration')
    n=len(candidates[0]); seen=set()
    horizons=set()
    for w in candidates:
        if len(w)!=n or any(not number(x) or x<0 for x in w) or abs(sum(w)-1)>1e-9: raise ValueError('weights must sum to one')
    for r in rows:
        if any(t.utcoffset() is None for t in (r.as_of,r.outcome_end,r.label_available_at)) or not r.as_of<r.outcome_end<=r.label_available_at: raise ValueError('chronology')
        if not text(r.company): raise ValueError("company required")
        horizons.add(((r.outcome_end.year-r.as_of.year)*12+r.outcome_end.month-r.as_of.month, r.outcome_end.day-r.as_of.day, r.outcome_end.time(), r.as_of.time()))
        key=(r.company,r.as_of,r.outcome_end)
        if key in seen: raise ValueError('duplicate')
        seen.add(key)
        if len(r.feature_available_at)!=n or any(t.utcoffset() is None or t>r.as_of for t in r.feature_available_at): raise ValueError('feature availability required')
        if len(r.features)!=n or any(not number(x) for x in (*r.features,r.outcome)): raise ValueError('invalid features')
    if len(horizons)>1: raise ValueError("mixed calendar horizons")
    def evaluate(subset,w):
        groups={}
        for r in subset: groups.setdefault((r.as_of,r.outcome_end),[]).append(r)
        vals=[]
        for key,rs in sorted(groups.items()):
            if len(rs)<min_cohort: continue
            ic=spearman([sum(a*b for a,b in zip(r.features,w)) for r in rs],[r.outcome for r in rs])
            vals.append(ic if ic is not None else 0.0)
        return (mean(vals),len(vals)) if vals else (None,0)
    results=[]
    for start,end in zip(boundaries,boundaries[1:]):
        train=[r for r in rows if r.label_available_at<start and r.label_available_at<=evaluation_cutoff]
        test=[r for r in rows if start<=r.as_of<end and r.label_available_at<=evaluation_cutoff]
        fits=[evaluate(train,w) for w in candidates]
        # Constant predictions receive zero rank signal; all candidates share cohorts.
        eligible=[i for i,(v,k) in enumerate(fits) if v is not None and k==max(x[1] for x in fits)]
        if not eligible: results.append({'start':start,'status':'insufficient_training'}); continue
        i=max(eligible,key=lambda i:fits[i][0])
        if not evaluate(test,candidates[i])[1]: results.append({'start':start,'status':'insufficient_testing'}); continue
        results.append({'start':start,'end':end,'weights':candidates[i],'train':fits[i],'test':evaluate(test,candidates[i]),'baseline':evaluate(test,candidates[0]),'status':'evaluated'})
    return results
