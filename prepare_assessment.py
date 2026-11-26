"""Assemble and audit a private assessment draft from SEC intake files."""
import argparse
import json
from pathlib import Path

from holdout_run import checked_fields, load_json
from rubrics import RUBRICS
from strategic_report import strategic_report


def prepare_assessment(judgments, intakes):
    checked_fields(judgments, "company as_of assessments risk_flags")
    documents, citations = {}, []
    for intake in intakes:
        checked_fields(intake, "document citations")
        document = intake["document"]
        checked_fields(document, "id origin available_at retrieved_at content_base64 sha256 license")
        if not isinstance(document["id"], str) or not isinstance(intake["citations"], list):
            raise ValueError("invalid intake document or citations")
        prior = documents.setdefault(document["id"], document)
        if prior != document:
            raise ValueError("conflicting intake metadata for the same document")
        citations.extend(intake["citations"])
    bundle = {**judgments, "documents": list(documents.values()), "citations": citations}
    report = strategic_report(bundle)
    gaps = []
    for framework, details in report["frameworks"].items():
        for item in details["elements"]:
            if item["status"] == "unknown":
                rubric = RUBRICS[item["element"]]
                gaps.append({
                    "framework": framework, "element": item["element"], "criterion": rubric.criterion,
                    "preferred_evidence": rubric.evidence, "adverse_anchor": rubric.adverse,
                    "favorable_anchor": rubric.favorable,
                })
    return bundle, report, {"company": report["company"], "as_of": report["as_of"], "unknown": gaps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("judgments", type=Path)
    parser.add_argument("output", type=Path, help="new private draft directory")
    parser.add_argument("intakes", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        bundle, report, gaps = prepare_assessment(load_json(args.judgments),
                                                   [load_json(path) for path in args.intakes])
        encoded = {
            name: json.dumps(data, indent=2, default=str, allow_nan=False) + "\n"
            for name, data in (("bundle.json", bundle), ("report.json", report), ("research-gaps.json", gaps))
        }
        args.output.mkdir(mode=0o700)
        for name, value in encoded.items():
            (args.output / name).write_text(value, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(f'Scored {report["scoring"]["assessed"]} elements. Research gaps: {len(gaps["unknown"])}.')


if __name__ == "__main__":
    main()
