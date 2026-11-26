"""Build a matched accounting benchmark cohort from archived SEC responses."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from backtest import Observation, compare
from quant import ratio, sloan_accruals
from sec_facts import select_as_of, vintages


ANNUAL_FORMS = ("10-K", "10-K/A")
MODELS = ("return_on_assets", "negative_sloan_accruals")
CONTRACT_REVENUE = "RevenueFromContractWithCustomerExcludingAssessedTax"


def issuer_observation(raw, start, end, next_start, next_end, as_of, outcome_end, evaluation_cutoff,
                       *, revenue_tag=CONTRACT_REVENUE):
    """Use exact annual fiscal periods and one later revenue-growth label."""
    if not start <= end < next_start <= next_end or not as_of < outcome_end <= evaluation_cutoff:
        raise ValueError("invalid pilot chronology")
    if not all(330 <= (last - first).days <= 385
               for first, last in [(start, end), (next_start, next_end)]):
        raise ValueError("pilot requires annual fiscal periods")
    if not end <= as_of.date() < next_end or next_end > outcome_end.date():
        raise ValueError("invalid feature or outcome window")

    payload = json.loads(raw)
    assets = vintages(raw, "us-gaap", "Assets", "USD")
    income = vintages(raw, "us-gaap", "NetIncomeLoss", "USD")
    cash = vintages(raw, "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD")
    sales = vintages(raw, "us-gaap", revenue_tag, "USD")

    def select(facts, cutoff, first, last):
        return select_as_of(facts, cutoff, start=first, end=last, forms=ANNUAL_FORMS)

    balance = select(assets, as_of, None, end)
    net = select(income, as_of, start, end)
    operating_cash = select(cash, as_of, start, end)
    initial_sales = select(sales, as_of, start, end)
    final_sales = select(sales, evaluation_cutoff, next_start, next_end)
    if None in (balance, net, operating_cash, initial_sales, final_sales):
        return None
    if final_sales.available_at < outcome_end:
        return None

    # For flow-to-assets comparisons use the average of opening and closing assets.
    opening = select(assets, as_of, None, start - timedelta(days=1))
    if opening is None:
        return None
    mean_assets = float((opening.value + balance.value) / 2)
    roa = ratio(float(net.value), mean_assets)
    accrual = sloan_accruals(float(net.value), float(operating_cash.value), mean_assets)
    growth = ratio(float(final_sales.value - initial_sales.value), float(initial_sales.value))
    if None in (roa, accrual, growth):
        return None
    balance_available = max(opening.available_at, balance.available_at)
    return Observation(
        company=str(payload["cik"]), as_of=as_of, outcome_end=outcome_end,
        label_available_at=final_sales.available_at,
        scores={"return_on_assets": roa, "negative_sloan_accruals": -accrual},
        total_return=growth,
        feature_available_at={
            "return_on_assets": max(balance_available, net.available_at),
            "negative_sloan_accruals": max(balance_available, net.available_at, operating_cash.available_at),
        },
    )


def run(config_path):
    path = Path(config_path)
    config = json.loads(path.read_text())
    as_of, outcome_end, evaluation_cutoff = (
        datetime.fromisoformat(config[key])
        for key in ("as_of", "outcome_end", "evaluation_cutoff")
    )
    if any(value.utcoffset() is None for value in (as_of, outcome_end, evaluation_cutoff)):
        raise ValueError("timezone-aware cohort timestamps required")
    as_of, outcome_end, evaluation_cutoff = (
        value.astimezone(timezone.utc) for value in (as_of, outcome_end, evaluation_cutoff)
    )
    rows, excluded = [], []
    for issuer in config["issuers"]:
        raw = (path.parent / issuer["archive"]).read_bytes()
        periods = (date.fromisoformat(issuer[key]) for key in ("start", "end", "next_start", "next_end"))
        try:
            row = issuer_observation(raw, *periods, as_of, outcome_end, evaluation_cutoff)
        except ValueError as error:
            excluded.append({"archive": issuer["archive"], "reason": str(error)})
            continue
        if row is None:
            excluded.append({"archive": issuer["archive"], "reason": "incomplete point-in-time accounts"})
        else:
            rows.append(row)
    result = compare(rows, MODELS, evaluation_cutoff)
    return {
        **result, "metric": "revenue_growth", "issuer_count": len(config["issuers"]),
        "issuer_exclusions": excluded,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="JSON cohort specification with archived issuer responses")
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, default=str))
