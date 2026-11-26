"""Prepare a private strategic score review and record a human decision."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from holdout_run import checked_fields, load_json
from strategic_report import strategic_report
from validation import text


def review_packet(bundle):
    report = strategic_report(bundle)
    scored = {
        row["element"]: row
        for framework in report["frameworks"].values()
        for row in framework["elements"]
        if row["status"] == "assessed"
    }
    if not scored:
        raise ValueError("at least one scored element is required for review")
    scored = {key: {**row, "citations": []} for key, row in scored.items()}
    for citation in bundle["citations"]:
        if citation["element"] in scored:
            scored[citation["element"]]["citations"].append(citation)
    contents = {
        "company": report["company"], "as_of": report["as_of"],
        "methodology": report["scoring"]["methodology"],
        "elements": list(scored.values()), "sources": report["sources"],
        "declared_risk_flags": report["publication"]["critical_flags"],
        "disputed_evidence": report["evidence_audit"]["conflicts"],
    }
    encoded = json.dumps(contents, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode()
    return {**contents, "review_sha256": sha256(encoded).hexdigest()}


def record_review(bundle, review):
    checked_fields(review, "review_sha256 reviewer decisions")
    packet = review_packet(bundle)
    if review["review_sha256"] != packet["review_sha256"]:
        raise ValueError("review does not match the current assessment packet")
    if not text(review["reviewer"]):
        raise ValueError("reviewer name required")
    if not isinstance(review["decisions"], list):
        raise ValueError("decisions must be a list")
    expected = {row["element"] for row in packet["elements"]}
    decisions = {}
    for decision in review["decisions"]:
        checked_fields(decision, "element decision rationale")
        element = decision["element"]
        if not text(element) or element not in expected or element in decisions:
            raise ValueError("unexpected or duplicate review element")
        if decision["decision"] not in ("agree", "revise", "unsupported") or not text(decision["rationale"]):
            raise ValueError("each element requires a valid decision and rationale")
        decisions[element] = decision
    if decisions.keys() != expected:
        raise ValueError("review is missing scored elements")
    changes = sorted(element for element, row in decisions.items() if row["decision"] != "agree")
    return {
        "review_sha256": packet["review_sha256"], "company": packet["company"],
        "as_of": packet["as_of"], "reviewer": review["reviewer"].strip(),
        "review_status": "revision_required" if changes else "review_recorded",
        "revision_elements": changes, "decisions": list(decisions.values()),
        "publishable": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    try:
        bundle = load_json(args.bundle)
        result = record_review(bundle, load_json(args.review)) if args.review else review_packet(bundle)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, default=str, allow_nan=False))


if __name__ == "__main__":
    main()
