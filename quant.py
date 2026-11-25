"""Deterministic benchmarks; inputs must be point-in-time, consistently scaled."""
from validation import number

def finite(x):
    return x if number(x) else None

def ratio(a,b):
    if a is None or b is None or not number(a) or not number(b) or b<=0: return None
    return finite(a/b)

def altman_z_manufacturing(working_capital, retained_earnings, ebit, assets, market_equity, liabilities, sales):
    xs=[ratio(working_capital,assets),ratio(retained_earnings,assets),ratio(ebit,assets),ratio(market_equity,liabilities),ratio(sales,assets)]
    return None if None in xs else finite(sum(a*b for a,b in zip(xs,[1.2,1.4,3.3,.6,1])))

def piotroski_from_accounts(current, prior):
    from core import piotroski
    def metrics(x):
        return [ratio(x.get('net_income'),x.get('begin_assets')),ratio(x.get('cfo'),x.get('begin_assets')),ratio(x.get('long_debt'),x.get('average_assets')),ratio(x.get('current_assets'),x.get('current_liabilities')),ratio(x.get('gross_profit'),x.get('sales')),ratio(x.get('sales'),x.get('begin_assets'))]
    a,b=metrics(current),metrics(prior)
    issuance=current.get('equity_issued')
    if None in a or None in b or type(issuance) is not bool: return None
    return piotroski(dict(zip(('positive_roa','positive_cfo','improving_roa','cfo_exceeds_income','lower_leverage','higher_current_ratio','no_equity_issuance','higher_gross_margin','higher_asset_turnover'),(a[0]>0,a[1]>0,a[0]>b[0],a[1]>a[0],a[2]<b[2],a[3]>b[3],not issuance,a[4]>b[4],a[5]>b[5]))))

def dupont(net_income,sales,average_assets,average_equity):
    parts=[ratio(net_income,sales),ratio(sales,average_assets),ratio(average_assets,average_equity)]
    roe=None if None in parts else finite(parts[0]*parts[1]*parts[2])
    return None if roe is None else {'margin':parts[0],'turnover':parts[1],'leverage':parts[2],'roe':roe}

def roic(nopat,average_invested_capital):
    return ratio(nopat,average_invested_capital)

def economic_value_added(nopat,invested_capital,wacc):
    if any(x is None or not number(x) for x in (nopat,invested_capital,wacc)) or invested_capital<=0 or wacc<0: return None
    return finite(nopat-invested_capital*wacc)

def sloan_accruals(net_income,cfo,average_assets):
    if not number(net_income) or not number(cfo): return None
    return ratio(net_income-cfo,average_assets)
