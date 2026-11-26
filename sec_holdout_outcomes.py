"""Prepare private FY2026 labels using the externally registered forecast bundle."""
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re

from holdout_run import load_json, register, registration_digest, timestamp
from sec_cohort import annual_period
from sec_facts import select_as_of, vintages
from sec_holdout_freeze import OUTCOME_END, SPEC, serialize
from sec_pilot import ANNUAL_FORMS
from validation import number


def collect_outcomes(specification, artifact, predictions, expected_digest, read_archive, now):
    if specification != SPEC:
        raise ValueError("expected the frozen FY2026 revenue-growth specification")
    protocol, frozen = register(specification, artifact, predictions)
    if registration_digest(protocol, specification["metric"]) != expected_digest:
        raise ValueError("bundle differs from the independently recorded registration")
    if now < protocol.label_cutoff:
        raise ValueError("outcome collection is locked until the registered cutoff")
    included = [row for row in json.loads(artifact)["coverage"] if "excluded" not in row]
    manifest = {str(row["cik"]): row for row in included}
    if len(manifest) != len(included) or manifest.keys() != {row.company for row in frozen}:
        raise ValueError("frozen issuer manifest does not match prediction keys")
    if any(row.outcome_end != timestamp(OUTCOME_END) for row in frozen):
        raise ValueError("prediction horizon differs from the FY2026 outcome window")

    outcomes, provenance, unresolved = [], [], []
    for row in frozen:
        entry = manifest[row.company]
        ticker = entry["ticker"]
        try:
            if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z0-9]+", ticker):
                raise ValueError("invalid frozen ticker")
            raw = read_archive(ticker)
            if int(json.loads(raw)["cik"]) != int(row.company):
                raise ValueError("SEC archive CIK mismatch")
            revenue = vintages(raw, "us-gaap", entry["revenue_tag"], "USD")
            period = annual_period(revenue, 2026, protocol.label_cutoff)
            if period is None:
                raise ValueError("eligible FY2026 annual revenue is unavailable")
            first, last = period
            if first != date.fromisoformat(entry["end"]) + timedelta(days=1):
                raise ValueError("FY2026 period is not adjacent to the frozen FY2025 period")
            fact = select_as_of(revenue, protocol.label_cutoff, start=first, end=last, forms=ANNUAL_FORMS)
            initial = Decimal(entry["initial_revenue"])
            if not initial.is_finite() or initial <= 0 or fact.value < 0 or fact.available_at < row.outcome_end:
                raise ValueError("invalid outcome amount or availability")
            growth = float((fact.value - initial) / initial)
            if not number(growth):
                raise ValueError("invalid outcome growth")
            outcomes.append({
                "company": row.company, "as_of": row.as_of.isoformat(), "outcome_end": row.outcome_end.isoformat(),
                "label_available_at": fact.available_at.isoformat(), "value": growth,
            })
            provenance.append({
                "company": row.company, "ticker": ticker, "revenue_tag": entry["revenue_tag"],
                "period_start": first.isoformat(), "period_end": last.isoformat(),
                "initial_revenue": str(initial), "initial_accession": entry["initial_revenue_accession"],
                "final_revenue": str(fact.value), "final_accession": fact.accession,
                "archive_sha256": fact.source_sha256,
            })
        except (OSError, ValueError, KeyError, ArithmeticError) as error:
            unresolved.append(f"{ticker}: {error}")
    if unresolved:
        raise ValueError("complete-cohort outcome collection blocked:\n" + "\n".join(unresolved))
    return {"metric": specification["metric"], "rows": outcomes}, {
        "registration_sha256": expected_digest, "outcomes": provenance,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("registered_digest", help="digest obtained from the independent custody record")
    parser.add_argument("archives", type=Path)
    parser.add_argument("output", type=Path, help="new private output directory")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("private output directory already exists")
        labels, provenance = collect_outcomes(
            load_json(args.bundle / "specification.json"), (args.bundle / "model.json").read_bytes(),
            load_json(args.bundle / "predictions.json"), args.registered_digest,
            lambda ticker: (args.archives / f"{ticker}.json").read_bytes(), datetime.now(timezone.utc),
        )
        encoded = serialize(labels)
        provenance["outcomes_sha256"] = sha256(encoded.encode()).hexdigest()
        args.output.mkdir(mode=0o700)
        (args.output / "provenance.json").write_text(serialize(provenance))
        (args.output / "outcomes.json").write_text(encoded)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"{error}\n")
    print(f"Collected {len(labels['rows'])} complete-cohort outcomes in the private output directory.")


if __name__ == "__main__":
    main()
