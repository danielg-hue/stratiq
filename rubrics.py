"""Draft analyst protocol, not an empirically validated scoring model."""
from core import ELEMENTS, FRAMEWORKS
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
# Each row: criterion, adverse anchor, favorable anchor, preferred evidence.
_DATA = '''rivalry|Competitive pressure on economic returns|Persistent price wars erode returns|Durable differentiation limits price pressure|Peer margins and industry filings
entrants|Barriers to effective entry|Low barriers and successful entrants|Demonstrated costly entry barriers|Entry history and regulatory records
substitutes|Exposure to alternative solutions|Substitutes rapidly displace demand|Few viable alternatives at comparable cost|Customer switching and adoption data
buyer_power|Customer bargaining leverage|Buyers impose sustained concessions|Fragmented buyers with limited leverage|Contracts and customer disclosures
supplier_power|Supplier bargaining leverage|Suppliers impose material cost increases|Multiple qualified suppliers with leverage|Procurement and supplier disclosures
social|Exposure to demographic and social change|Structural demand erosion|Durable favorable demand shifts|Demographic and demand studies
technology|External technological change|Core offering faces displacement|External technology expands opportunity|Technology adoption and industry studies
economic|Macroeconomic exposure|Material sensitivity with weak mitigation|Resilient demand across cycles|Segment results and economic releases
environment|Environmental exposure|Material unmanaged physical or transition risk|Demonstrated mitigation and opportunity|Environmental disclosures and regulator records
political|Political and policy exposure|Adverse policy threatens operations|Durable favorable policy exposure|Published policy and government records
legal|Legal and regulatory exposure|Material unresolved legal threats|Demonstrated compliance and manageable exposure|Court and regulator records
ethical|Ethical conduct exposure|Documented systemic misconduct|Verified effective ethical safeguards|Investigations and independent audits
value|Resource contribution to customer value|Resources fail to create economic benefit|Resources demonstrably create superior value|Unit economics and customer evidence
rarity|Scarcity of valuable resources|Resources widely available|Valuable resources demonstrably scarce|Peer capability comparisons
imitability|Difficulty of replicating valuable resources|Competitors replicate readily|Replication faces durable structural barriers|Patent and replication evidence
organization|Ability to exploit valuable resources|Organizational barriers prevent realization|Processes reliably realize resource value|Operating results and process evidence
liquidity|Near-term payment capacity|Unfunded near-term obligations|Ample liquid resources under stress|Balance sheet and cash forecasts
solvency|Long-term balance sheet capacity|Unsustainable obligations|Strong loss absorption capacity|Debt and balance sheet disclosures
profitability|Economic profitability|Persistent losses relative to peers|Sustained superior profitability|Income statements and peer data
cash_conversion|Conversion of earnings to cash|Persistent unexplained cash shortfall|Consistent strong cash conversion|Cash flow and income statements
revenue_stability|Historical revenue variability|Severe recurring revenue shocks|Stable revenue through cycles|Historical segment revenue
margin_stability|Historical margin variability|Repeated severe margin compression|Stable margins through cycles|Historical segment margins
capital_efficiency|Returns on deployed capital|Persistent returns below capital cost|Sustained returns above capital cost|Capital and operating income data
debt_service|Capacity to service debt|Coverage insufficient under realistic stress|Strong stressed debt coverage|Debt schedules and cash flows
working_capital|Operating working capital management|Persistent disruptive cash absorption|Efficient sustainable working capital|Receivables inventory and payables
funding_access|Access to external funding|Funding unavailable on viable terms|Diversified reliable funding access|Financing agreements and issuance history
execution|Delivery against stated plans|Repeated material missed commitments|Consistent verified delivery|Dated guidance and actual results
capital_allocation|Quality of investment decisions|Repeated value destructive deployment|Demonstrated disciplined value creation|Acquisition and investment outcomes
board_independence|Effective independent oversight|Documented compromised oversight|Effective independent challenge|Proxy statements and governance records
incentives|Alignment of management incentives|Rewards encourage harmful short-term behavior|Rewards align with durable outcomes|Compensation disclosures
 disclosure|Quality of reporting transparency|Material misleading or opaque disclosures|Consistent transparent reporting|Filings and correction history
succession|Leadership continuity planning|Critical leadership gap without plan|Credible tested succession arrangements|Governance disclosures
internal_controls|Effectiveness of financial controls|Material unresolved control weaknesses|Demonstrated effective controls|Auditor and control reports
shareholder_rights|Protection of investor rights|Material entrenched unequal treatment|Strong enforceable investor protections|Charter and proxy documents
innovation_pipeline|Quality of development pipeline|No credible replacement for declining offerings|Validated promising development portfolio|Pipeline milestones and trials
research_productivity|Output relative to research inputs|Persistent spending without useful output|Consistent valuable research outputs|Research spending and realized outputs
addressable_market|Accessible market opportunity|Realistically accessible market shrinking|Evidence of expanding accessible market|Independent market sizing
organic_growth|Underlying growth excluding acquisitions|Persistent organic contraction|Sustained profitable organic expansion|Organic revenue reconciliations
commercialization|Conversion of innovation to sales|Repeated failed launches|Repeatable successful launches|Launch cohorts and sales data
adaptability|Response to structural change|Repeated failure to adapt|Verified timely successful adaptation|Dated decisions and outcomes
customer_retention|Retention of existing customers|Persistent material churn|Durable superior retention|Cohort retention disclosures
market_share|Relative competitive share|Sustained share loss|Sustained profitable share gains|Independent market share data
brand|Customer preference attributable to brand|Documented preference deterioration|Durable measurable preference premium|Customer studies and pricing data
distribution|Access to customers through channels|Material channel access disadvantages|Durable effective channel access|Channel agreements and sales data
demand_visibility|Visibility into future demand|Unreliable orders and cancellations|Reliable contracted or repeat demand|Backlog and cancellation data
supply_chain|Ability to maintain supply|Repeated unmanaged supply disruption|Verified resilient supply alternatives|Supplier and continuity records
concentration|Dependency on single exposures|Critical unmitigated dependency|Diversified or effectively mitigated exposure|Customer supplier and segment disclosures
cyber_resilience|Ability to withstand cyber incidents|Material unresolved cyber weaknesses|Verified effective recovery and controls|Incident and audit records
workforce|Availability of critical skills|Persistent critical staffing shortages|Reliable skilled workforce capacity|Staffing and retention data
continuity|Ability to sustain critical operations|Untested or failed recovery capability|Verified effective continuity arrangements|Recovery exercises and incident records'''
@dataclass(frozen=True)
class Rubric:
    criterion:str
    adverse:str
    favorable:str
    evidence:str
RUBRICS={}
for line in _DATA.splitlines():
    key,*parts=line.strip().split('|'); RUBRICS[key]=Rubric(*parts)
assert set(RUBRICS)==ELEMENTS
# Related constructs: flag for ablation, do not automatically discount.
OVERLAP_GROUPS=(('rivalry','market_share','profitability'),('value','brand','customer_retention'),('solvency','debt_service','liquidity','funding_access'),('technology','innovation_pipeline','adaptability'),('capital_efficiency','capital_allocation','profitability'),('supplier_power','supply_chain','concentration'),('internal_controls','disclosure','ethical'))
ANCHORS={-2:'Severe documented adverse condition',-1:'Material adverse condition with partial mitigation',0:'Balanced or immaterial effect supported by evidence',1:'Material favorable condition with limitations',2:'Durable strong favorable condition supported by evidence'}

def evidence_independence(records):
    """Count declared origin groups, not URLs. Origin declarations require verification."""
    groups=set()
    for r in records:
        origin=r.get('origin')
        if not isinstance(origin,str) or not origin.strip(): raise ValueError('origin required')
        groups.add(origin.strip().casefold())
    return len(groups)

def publication_gate(result, flags):
    """Fail closed until trusted evidence and risk review pipeline exists."""
    from decimal import Decimal
    from validation import number
    allowed={'insolvency','fraud','continuity','regulatory_shutdown'}
    flags=tuple(flags)
    if any(f not in allowed for f in flags): raise ValueError('unknown risk flag')
    score=result.get('index')
    valid=(score.is_finite() if isinstance(score,Decimal) else number(score)) and 0<=score<=100
    return {'publishable':False,'critical_flags':tuple(sorted(set(flags))), 'index':score if valid else None,'reason':'trusted evidence and risk review unavailable'}
