"""Freeze the FY2025 SEC accounting features for the FY2026 revenue-growth evaluation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from holdout_run import register, registration_digest, timestamp
from sec_cohort import REVENUE_TAGS, annual_period
from sec_facts import vintages
from sec_pilot import MODELS, issuer_features


SPEC = {
    "start": "2026-04-01T00:00:00+00:00",
    "end": "2026-04-02T00:00:00+00:00",
    "label_cutoff": "2027-04-01T00:00:00+00:00",
    "models": list(MODELS),
    "metric": "revenue_growth",
}
OUTCOME_END = "2027-01-01T00:00:00+00:00"


def freeze(universe, archives):
    as_of = timestamp(SPEC["start"])
    predictions, coverage = [], []
    for line in universe.read_text().splitlines():
        ticker, cik = line.split()
        entry = {"ticker": ticker, "cik": int(cik)}
        try:
            raw = (archives / f"{ticker}.json").read_bytes()
            entry["archive_sha256"] = sha256(raw).hexdigest()
            if int(json.loads(raw)["cik"]) != int(cik):
                raise ValueError("archive CIK mismatch")
            for revenue_tag in REVENUE_TAGS:
                period = annual_period(vintages(raw, "us-gaap", revenue_tag, "USD"), 2025, as_of)
                if period is not None:
                    break
            else:
                raise ValueError("no eligible December FY2025 revenue")
            features = issuer_features(raw, *period, as_of, revenue_tag=revenue_tag)
            if features is None:
                raise ValueError("incomplete FY2025 point-in-time accounts")
            scores, available, initial_sales = features
            entry.update(
                revenue_tag=revenue_tag, start=period[0].isoformat(), end=period[1].isoformat(),
                initial_revenue=str(initial_sales.value), initial_revenue_accession=initial_sales.accession,
            )
            predictions.append({
                "company": str(int(cik)), "as_of": SPEC["start"], "outcome_end": OUTCOME_END,
                "scores": scores, "feature_available_at": {name: value.isoformat() for name, value in available.items()},
            })
        except (FileNotFoundError, ValueError, KeyError) as error:
            entry["excluded"] = "missing archive" if isinstance(error, FileNotFoundError) else str(error)
        coverage.append(entry)
    return predictions, coverage


def serialize(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("universe", type=Path)
    parser.add_argument("archives", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    predictions, coverage = freeze(args.universe, args.archives)
    root = Path(__file__).resolve().parent
    # Include exact model source bytes for reproducibility and bind the denominator manifest.
    artifact = serialize({
        "coverage": coverage,
        "model_sources": {name: (root / name).read_text() for name in (
            "sec_holdout_freeze.py", "sec_pilot.py", "sec_cohort.py", "sec_facts.py", "quant.py", "validation.py",
        )},
    }).encode()
    protocol, frozen = register(SPEC, artifact, predictions)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("specification.json", SPEC), ("predictions.json", predictions), ("registration.json", {
        "registration_sha256": registration_digest(protocol, SPEC["metric"]),
        "protocol_sha256": protocol.digest, "predictions": len(frozen), "universe": len(coverage),
    })):
        (args.output / name).write_text(serialize(value))
    (args.output / "model.json").write_bytes(artifact)


if __name__ == "__main__":
    main()
