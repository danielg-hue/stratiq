"""Run a December-year-end SEC benchmark cohort against local filing archives."""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from backtest import compare
from sec_facts import vintages
from sec_pilot import ANNUAL_FORMS, CONTRACT_REVENUE, MODELS, issuer_observation

REVENUE_TAGS = ("Revenues", CONTRACT_REVENUE, "SalesRevenueNet")


def annual_period(facts, year, cutoff):
    periods = {
        (fact.start, fact.end) for fact in facts
        if fact.start is not None and fact.end.year == year and fact.end.month == 12
        and 350 <= (fact.end - fact.start).days <= 380
        and fact.form in ANNUAL_FORMS and fact.available_at <= cutoff
    }
    if len(periods) > 1:
        raise ValueError("ambiguous December fiscal period")
    return next(iter(periods), None)


def revenue_periods(raw, feature_year, as_of, cutoff):
    for tag in REVENUE_TAGS:
        facts = vintages(raw, "us-gaap", tag, "USD")
        current = annual_period(facts, feature_year, as_of)
        if current is None:
            continue
        following = annual_period(facts, feature_year + 1, cutoff)
        if following is None:
            raise ValueError("outcome missing under the feature-period revenue tag")
        return tag, current, following
    raise ValueError("missing December fiscal period with eligible revenue")


def run(issuers_path, archive_dir, feature_year):
    if not 2000 <= feature_year <= 9997:
        raise ValueError("invalid feature year")
    issuers = [tuple(line.split()) for line in issuers_path.read_text().splitlines() if line.strip()]
    if len({ticker for ticker, _ in issuers}) != len(issuers) or len({int(cik) for _, cik in issuers}) != len(issuers):
        raise ValueError("duplicate issuer in cohort")
    as_of = datetime(feature_year + 1, 4, 1, tzinfo=timezone.utc)
    horizon = datetime(feature_year + 2, 1, 1, tzinfo=timezone.utc)
    cutoff = datetime(feature_year + 2, 4, 1, tzinfo=timezone.utc)
    rows, coverage = [], []
    for ticker, cik in issuers:
        entry = {"ticker": ticker, "cik": int(cik)}
        try:
            if not ticker.isascii() or not ticker.isalnum():
                raise ValueError("invalid archive ticker")
            raw = (archive_dir / f"{ticker}.json").read_bytes()
            entry["sha256"] = sha256(raw).hexdigest()
            if int(json.loads(raw)["cik"]) != int(cik):
                raise ValueError("archive CIK does not match cohort")
            tag, (start, end), (next_start, next_end) = revenue_periods(raw, feature_year, as_of, cutoff)
            entry["revenue_tag"] = tag
            if next_start != end + timedelta(days=1):
                raise ValueError("fiscal periods are not adjacent")
            row = issuer_observation(
                raw, start, end, next_start, next_end, as_of, horizon, cutoff, revenue_tag=tag,
            )
            if row is None:
                raise ValueError("incomplete point-in-time accounts or outcome")
            rows.append(row)
            entry["included"] = True
        except FileNotFoundError:
            entry.update(included=False, reason="archive missing")
        except (ValueError, KeyError) as error:
            entry.update(included=False, reason=str(error))
        coverage.append(entry)

    result = compare(rows, MODELS, cutoff)
    differences = []
    for index in range(len(rows)):
        reduced = compare(rows[:index] + rows[index + 1:], MODELS, cutoff)
        for cohort in reduced["cohorts"]:
            first, second = (cohort["rank_ic"][name] for name in MODELS)
            if first is not None and second is not None:
                differences.append(first - second)
    return {
        "universe_size": len(issuers), "matched_size": len(rows),
        "feature_year": feature_year, "coverage": coverage, "comparison": result,
        "leave_one_out_rank_difference_range": [min(differences), max(differences)] if differences else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issuers", type=Path)
    parser.add_argument("archives", type=Path)
    parser.add_argument("feature_year", type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.issuers, args.archives, args.feature_year), indent=2, default=str))
