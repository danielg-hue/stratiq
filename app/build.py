"""Prepare the static StratIQ research explorer from the checked-in cohort reports."""
import json
from pathlib import Path
import shutil
import sys


def build(destination):
    source = Path(__file__).resolve().parent
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
    for filename in ("index.html", "style.css", "main.mjs", "rolling.mjs"):
        shutil.copyfile(source / filename, destination / filename)
    shutil.copyfile(research / "rolling" / "explorer.json", destination / "rolling.json")
    (destination / "cohorts.json").write_text(json.dumps(reports, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
