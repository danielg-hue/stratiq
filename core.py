"""StratIQ experimental baseline; no market predictions."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from validation import text, timestamp
FRAMEWORKS = {
'porter': ['rivalry','entrants','substitutes','buyer_power','supplier_power'],
'steeple':['social','technology','economic','environment','political','legal','ethical'],
'vrio':['value','rarity','imitability','organization'],
'financial':['liquidity','solvency','profitability','cash_conversion','revenue_stability','margin_stability','capital_efficiency','debt_service','working_capital','funding_access'],
'governance':['execution','capital_allocation','board_independence','incentives','disclosure','succession','internal_controls','shareholder_rights'],
'growth':['innovation_pipeline','research_productivity','addressable_market','organic_growth','commercialization','adaptability'],
'market':['customer_retention','market_share','brand','distribution','demand_visibility'],
'operations':['supply_chain','concentration','cyber_resilience','workforce','continuity']}
ELEMENTS = frozenset(x for xs in FRAMEWORKS.values() for x in xs)
@dataclass(frozen=True)
class Evidence:
    id: str
    available_at: datetime
    source: str
@dataclass(frozen=True)
class Assessment:
    element: str
    status: str
    score: Decimal | None
    evidence: tuple[Evidence,...] = ()
    rationale: str = ''
def index(rows, cutoff):
    minimum=Decimal('.8')
    if not timestamp(cutoff): raise ValueError('timezone required')
    rows=list(rows)
    if len({r.element for r in rows})!=len(rows): raise ValueError('duplicate element')
    if not {r.element for r in rows} <= ELEMENTS: raise ValueError('unknown element')
    assessed=[]; na=0
    for r in rows:
        if r.status not in ('assessed','unknown','na'): raise ValueError('status')
        if any(not timestamp(e.available_at) or e.available_at>cutoff or not text(e.source) or not text(e.id) for e in r.evidence): raise ValueError('invalid or future evidence')
        if r.status=='assessed':
            if not isinstance(r.score, Decimal) or not r.score.is_finite() or not -2<=r.score<=2 or r.score*4 != (r.score*4).to_integral_value(): raise ValueError('invalid score')
            if not r.evidence or not r.rationale.strip(): raise ValueError('evidence and rationale required')
            assessed.append(r.score)
        else:
            if r.score is not None: raise ValueError('unscored status')
            if r.status=='na':
                raise ValueError('NA not authorized in baseline-0.4; use unknown')
                na+=1
    applicable=len(ELEMENTS)-na
    coverage=Decimal(len(assessed))/applicable if applicable else Decimal(0)
    raw=sum(assessed,Decimal(0))
    return {'methodology':'baseline-0.8','evidence_verified':False,'raw':raw,'coverage':coverage,'index':50+25*raw/len(assessed) if len(assessed)>=40 and coverage>=minimum and all(sum(r.status=='assessed' and r.element in es for r in rows)*2>=len(es) for es in FRAMEWORKS.values()) else None,'assessed':len(assessed),'na':na}

def eligible_training(rows, test_start):
    """Purge labels whose outcome windows touch or cross the test boundary."""
    return [r for r in rows if r['as_of'] < r['outcome_end'] < test_start and r['label_available_at'] < test_start and r['label_available_at'] >= r['outcome_end']]

def piotroski(signals):
    """Nine precomputed point-in-time boolean signals; missing inputs suppress score."""
    keys=('positive_roa','positive_cfo','improving_roa','cfo_exceeds_income','lower_leverage','higher_current_ratio','no_equity_issuance','higher_gross_margin','higher_asset_turnover')
    if any(type(signals.get(k)) is not bool for k in keys): return None
    return sum(signals[k] for k in keys)
