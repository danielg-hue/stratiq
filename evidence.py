"""Local evidence integrity, not publisher authentication or semantic verification."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from validation import timestamp, text
from core import ELEMENTS

@dataclass(frozen=True)
class Document:
    id: str
    origin: str
    available_at: datetime
    retrieved_at: datetime
    content: bytes
    digest: str
    license: str

@dataclass(frozen=True)
class Citation:
    element: str
    document_id: str
    start: int
    end: int
    excerpt: bytes
    stance: str


def audit(documents, citations, cutoff):
    if not timestamp(cutoff): raise ValueError('invalid cutoff')
    docs = {}
    for d in documents:
        if not isinstance(d, Document) or not text(d.id) or not text(d.origin): raise ValueError('invalid document')
        if d.id != d.id.strip() or d.id in docs: raise ValueError('duplicate or noncanonical id')
        if not timestamp(d.available_at) or not timestamp(d.retrieved_at) or d.available_at > cutoff or d.retrieved_at < d.available_at: raise ValueError('invalid chronology')
        if type(d.content) is not bytes or not d.content or len(d.content)>10_000_000: raise ValueError('invalid content')
        if sha256(d.content).hexdigest()!=d.digest: raise ValueError('digest mismatch')
        if d.license not in ('research_only','commercial'): raise ValueError('license not eligible')
        docs[d.id]=d
    # Connected components: same declared origin OR identical bytes count once.
    parents={k:k for k in docs}
    def root(k):
        while parents[k]!=k:
            parents[k]=parents[parents[k]]; k=parents[k]
        return k
    seen={}
    for k,d in docs.items():
        for token in [('origin',d.origin.strip().casefold()),('digest',d.digest)]:
            if token in seen: parents[root(k)]=root(seen[token])
            else: seen[token]=k
    groups={}; stances={}; keys=set()
    for c in citations:
        if not isinstance(c,Citation) or c.element not in ELEMENTS or c.document_id not in docs or c.stance not in ('supports','contradicts','context'): raise ValueError('invalid citation')
        d=docs[c.document_id]
        if type(c.start) is not int or type(c.end) is not int or not 0<=c.start<c.end<=len(d.content): raise ValueError('invalid span')
        if type(c.excerpt) is not bytes or not c.excerpt.strip() or d.content[c.start:c.end]!=c.excerpt: raise ValueError('excerpt mismatch')
        key=(c.element,c.document_id,c.start,c.end)
        if key in keys: raise ValueError('duplicate citation')
        keys.add(key)
        groups.setdefault(c.element,set()).add(root(c.document_id))
        stances.setdefault(c.element,set()).add(c.stance)
    return {'integrity_checked':True,'publisher_authenticated':False,'claims_verified':False,'publishable':False,'independent_group_candidates':{k:len(v) for k,v in groups.items()},'conflicts':sorted(k for k,v in stances.items() if {'supports','contradicts'}<=v)}
