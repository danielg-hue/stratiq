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

    features = issuer_features(raw, start, end, as_of, revenue_tag=revenue_tag)
    if features is None:
        return None
    scores, available, initial_sales = features
    final_sales = select_as_of(vintages(raw, "us-gaap", revenue_tag, "USD"),
                               evaluation_cutoff, start=next_start, end=next_end, forms=ANNUAL_FORMS)
    if final_sales is None or final_sales.available_at < outcome_end:
        return None
    growth = ratio(float(final_sales.value - initial_sales.value), float(initial_sales.value))
    if growth is None:
        return None
    return Observation(
        company=str(json.loads(raw)["cik"]), as_of=as_of, outcome_end=outcome_end,
        label_available_at=final_sales.available_at, scores=scores, total_return=growth,
        feature_available_at=available,
    )


def issuer_features(raw, start, end, as_of, *, revenue_tag=CONTRACT_REVENUE):
    """Compute annual benchmarks using only filings available at the feature cutoff."""
    def select(concept, first, last):
        return select_as_of(vintages(raw, "us-gaap", concept, "USD"),
                            as_of, start=first, end=last, forms=ANNUAL_FORMS)

    balance = select("Assets", None, end)
    opening = select("Assets", None, start - timedelta(days=1))
    net = select("NetIncomeLoss", start, end)
    operating_cash = select("NetCashProvidedByUsedInOperatingActivities", start, end)
    initial_sales = select(revenue_tag, start, end)
    if None in (balance, opening, net, operating_cash, initial_sales) or initial_sales.value <= 0:
        return None
    mean_assets = float((opening.value + balance.value) / 2)
    roa = ratio(float(net.value), mean_assets)
    accrual = sloan_accruals(float(net.value), float(operating_cash.value), mean_assets)
    if None in (roa, accrual):
        return None
    balance_available = max(opening.available_at, balance.available_at)
    return (
        {"return_on_assets": roa, "negative_sloan_accruals": -accrual},
        {
            "return_on_assets": max(balance_available, net.available_at),
            "negative_sloan_accruals": max(balance_available, net.available_at, operating_cash.available_at),
        },
        initial_sales,
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
