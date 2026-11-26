"""Compute point-in-time trailing-four-quarter SEC revenue from annual and YTD filings."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

from holdout_run import timestamp
from sec_cohort import REVENUE_TAGS
from sec_facts import fetch_company_facts, select_as_of, vintages

ANNUAL = ("10-K", "10-K/A")
INTERIM = ("10-Q", "10-Q/A")
QUARTERS = ((75, 105), (165, 200), (255, 295))


def quarter_count(start, end):
    if start is None:
        return None
    days = (end - start).days + 1
    return next((count for count, (lo, hi) in enumerate(QUARTERS, 1) if lo <= days <= hi), None)


def trailing_revenue(facts, cutoff):
    eligible = [fact for fact in facts if fact.available_at <= cutoff and fact.start is not None]
    annual_periods = {(fact.start, fact.end) for fact in eligible if fact.form in ANNUAL
                      and 350 <= (fact.end - fact.start).days <= 380}
    if not annual_periods:
        return None
    end = max(last for _, last in annual_periods)
    starts = {first for first, last in annual_periods if last == end}
    if len(starts) != 1:
        raise ValueError("ambiguous latest annual period")
    start = starts.pop()
    annual = select_as_of(eligible, cutoff, start=start, end=end, forms=ANNUAL)
    next_start = end + timedelta(days=1)
    interim_ends = {fact.end for fact in eligible if fact.form in INTERIM and fact.end > end}
    if not interim_ends:
        return end, annual.value, 0, (annual,)
    last = max(interim_ends)
    count = quarter_count(next_start, last)
    if count is None:
        raise ValueError("latest interim filing cannot be aligned with preceding fiscal year")
    current = select_as_of(eligible, cutoff, start=next_start, end=last, forms=INTERIM)
    if current is None:
        raise ValueError("latest interim filing is missing cumulative revenue")
    comparative = [fact for fact in eligible if fact.accession == current.accession and fact.start == start
                   and fact.form in INTERIM and fact.end < end and quarter_count(start, fact.end) == count]
    prior_ends = {fact.end for fact in comparative}
    if len(prior_ends) != 1:
        raise ValueError("missing or ambiguous prior-year YTD revenue in the same filing")
    prior = select_as_of(comparative, cutoff, start=start, end=prior_ends.pop(), forms=INTERIM)
    return last, annual.value + current.value - prior.value, count, (annual, current, prior)


def rolling_revenue(raw, cutoff):
    """Resolve the latest complete annual/YTD combination across known revenue tags."""
    if cutoff.utcoffset() is None:
        raise ValueError("timezone-aware cutoff required")
    candidates = []
    problems = []
    for tag in REVENUE_TAGS:
        facts = vintages(raw, "us-gaap", tag, "USD")
        if not facts:
            continue
        try:
            result = trailing_revenue(facts, cutoff)
        except ValueError as error:
            problems.append((max(f.end for f in facts if f.available_at <= cutoff), error))
            continue
        if result is not None:
            candidates.append((tag, result))
    if not candidates:
        if problems:
            raise max(problems, key=lambda item: item[0])[1]
        raise ValueError("no eligible annual revenue baseline")
    tag, (end, revenue, interim_quarters, sources) = max(candidates, key=lambda item: item[1][0])
    if any(period > end for period, _ in problems):
        raise ValueError("a newer reported period could not be reconciled")
    if revenue < 0:
        raise ValueError("negative trailing revenue")
    payload = json.loads(raw)
    return {
        "company": payload["entityName"], "cik": int(payload["cik"]),
        "as_of": cutoff.isoformat(), "period_end": end.isoformat(), "revenue_tag": tag,
        "trailing_four_quarter_revenue_usd": str(revenue), "interim_quarters": interim_quarters,
        "source_sha256": sources[0].source_sha256,
        "inputs": [
            {"role": role, "accession": fact.accession, "start": fact.start.isoformat(),
             "end": fact.end.isoformat(), "available_at": fact.available_at.isoformat(), "revenue_usd": str(fact.value)}
            for role, fact in zip(("annual", "current_ytd", "prior_ytd"), sources)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--cik", type=int)
    parser.add_argument("--as-of", help="timezone-aware cutoff, defaults to current UTC time")
    args = parser.parse_args()
    try:
        cutoff = timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc)
        raw = args.archive.read_bytes() if args.archive else fetch_company_facts(
            args.cik, os.environ.get("STRATIQ_SEC_USER_AGENT"),
        )
        if args.cik is not None and int(json.loads(raw)["cik"]) != args.cik:
            raise ValueError("SEC response CIK does not match request")
        result = rolling_revenue(raw, cutoff)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
