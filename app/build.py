"""Prepare the static StratIQ research explorer from the checked-in cohort reports."""
import argparse
import json
from pathlib import Path
import shutil
import sys


def build(destination, draft=None):
    source = Path(__file__).resolve().parent
    sys.path.insert(0, str(source.parent))
    from rubrics import FRAMEWORKS, RUBRICS
    research = source.parent / "research"
    names = json.loads((research / "sec-pilot-names.json").read_text())
    reports = []
    for path in sorted(research.glob("sec-pilot-[0-9][0-9][0-9][0-9].json"), reverse=True):
        report = json.loads(path.read_text())
        for issuer in report["coverage"]:
            issuer["name"] = names[issuer["ticker"]]
        reports.append(report)
    if not reports:
        raise ValueError("no SEC cohort reports found")
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ("index.html", "style.css", "main.mjs", "rolling.mjs", "download.mjs", "scoring.mjs"):
        shutil.copyfile(source / filename, destination / filename)
    shutil.copyfile(research / "rolling" / "explorer.json", destination / "rolling.json")
    (destination / "cohorts.json").write_text(json.dumps(reports, ensure_ascii=False), encoding="utf-8")

    registry = {framework: {element: RUBRICS[element].criterion for element in elements}
                for framework, elements in FRAMEWORKS.items()}
    (destination / "scoring-registry.json").write_text(json.dumps(registry), encoding="utf-8")
    packaged_draft = destination / "internal-scoring-draft.json"
    if draft is not None:
        report = json.loads(draft.read_text())
        if report.get("status") != "internal_draft" or report.get("publication", {}).get("publishable") is not False:
            raise ValueError("only internal strategic drafts can be packaged")
        packaged_draft.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    else:
        packaged_draft.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--internal-draft", type=Path)
    args = parser.parse_args()
    build(args.destination, args.internal_draft)
