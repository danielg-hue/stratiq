"""Shared fail-closed primitive validation. Timestamps are declarations, not verified provenance."""
from math import isfinite
from datetime import datetime

def number(x):
    return type(x) in (int,float) and abs(x)<=1e100 and isfinite(x)

def text(x):
    return isinstance(x,str) and bool(x.strip())

def timestamp(x):
    return isinstance(x,datetime) and x.utcoffset() is not None

def provenance(times,n,as_of):
    if len(times)!=n or any(not timestamp(t) or t>as_of for t in times):
        raise ValueError('point-in-time feature availability required')
