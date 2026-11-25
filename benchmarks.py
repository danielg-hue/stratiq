"""Additional experimental benchmarks. Annual, comparable accounting inputs only."""
from math import isfinite
from quant import ratio

from validation import number as valid

def safe_ratio(a,b):
    return ratio(a,b) if valid(a) and valid(b) else None

def yields(net_income, free_cash_flow, market_cap):
    return {'earnings_yield':safe_ratio(net_income,market_cap),'fcf_yield':safe_ratio(free_cash_flow,market_cap)}

def magic_formula(ebit, enterprise_value, net_working_capital, net_fixed_assets):
    capital=net_working_capital+net_fixed_assets if valid(net_working_capital) and valid(net_fixed_assets) else None
    return {'earnings_yield':safe_ratio(ebit,enterprise_value),'return_on_capital':safe_ratio(ebit,capital)}

def interest_coverage(ebit, interest_expense):
    return safe_ratio(ebit,interest_expense)

def beneish_m(signals):
    """Eight-variable 1999 model; inputs are precomputed accounting indices, not raw accounts."""
    coefficients={'dsri':.920,'gmi':.528,'aqi':.404,'sgi':.892,'depi':.115,'sgai':-.172,'tata':4.679,'lvgi':-.327}
    if set(signals)!=set(coefficients) or any(not valid(v) for v in signals.values()): return None
    return -4.84+sum(coefficients[k]*signals[k] for k in coefficients)
