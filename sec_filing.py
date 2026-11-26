"""Package an archived SEC primary filing and literal citations for analyst review."""
import argparse
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import re

from core import ELEMENTS
from holdout_run import checked_fields, load_json, timestamp
from validation import text


MAX_BYTES = 10_000_000
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "DEF 14A"}


def primary_filing(submissions, accession):
    if not isinstance(accession, str) or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession):
        raise ValueError("invalid accession number")
    records = submissions["filings"]["recent"]
    names = ("accessionNumber", "acceptanceDateTime", "form", "primaryDocument")
    if len({len(records[name]) for name in names}) != 1:
        raise ValueError("misaligned SEC submission records")
    positions = [i for i, number in enumerate(records["accessionNumber"]) if number == accession]
    if len(positions) != 1:
        raise ValueError("expected one matching accession in recent submissions")
    position = positions[0]
    if records["form"][position] not in FORMS:
        raise ValueError("unsupported SEC filing form")
    filename = records["primaryDocument"][position]
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.html?", filename):
        raise ValueError("invalid SEC primary document filename")
    cik = submissions["cik"]
    if type(cik) not in (int, str) or not re.fullmatch(r"[0-9]{1,10}", str(cik)) or int(cik) == 0:
        raise ValueError("invalid filing issuer CIK")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filename}"
    return filename, url, timestamp(records["acceptanceDateTime"][position])


def package_filing(submissions, accession, archive, retrieved_at, selections):
    filename, url, accepted = primary_filing(submissions, accession)
    if archive.name != filename:
        raise ValueError("archive filename does not match SEC primary document")
    retrieved = timestamp(retrieved_at)
    if retrieved < accepted:
        raise ValueError("retrieval precedes SEC acceptance")
    with archive.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("primary document exceeds intake size or is empty")
    if not isinstance(selections, list):
        raise ValueError("citation selections must be a list")
    digest = sha256(raw).hexdigest()
    document_id = f"sec:{int(submissions['cik'])}:{accession}:{digest}"
    citations = []
    seen = set()
    for row in selections:
        checked_fields(row, "element excerpt stance")
        element, excerpt, stance = (row[key] for key in ("element", "excerpt", "stance"))
        if not text(element) or element not in ELEMENTS or not text(excerpt):
            raise ValueError("invalid element or citation excerpt")
        if stance not in ("supports", "contradicts", "context"):
            raise ValueError("invalid citation stance")
        needle = excerpt.encode("utf-8")
        start = raw.find(needle)
        if start < 0 or raw.find(needle, start + 1) >= 0:
            raise ValueError("citation must match exactly once in the original bytes")
        if (element, start, len(needle)) in seen:
            raise ValueError("duplicate citation selection")
        seen.add((element, start, len(needle)))
        citations.append({
            "element": element, "document_id": document_id, "start": start,
            "end": start + len(needle), "excerpt": excerpt, "stance": stance,
        })
    return {
        "document": {
            "id": document_id, "origin": url, "available_at": accepted.isoformat(),
            "retrieved_at": retrieved.isoformat(), "content_base64": b64encode(raw).decode("ascii"),
            "sha256": digest, "license": "research_only",
        },
        "citations": citations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submissions", type=Path)
    parser.add_argument("accession")
    parser.add_argument("archive", type=Path)
    parser.add_argument("retrieved_at")
    parser.add_argument("selections", type=Path)
    args = parser.parse_args()
    try:
        result = package_filing(
            load_json(args.submissions), args.accession, args.archive, args.retrieved_at, load_json(args.selections),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
