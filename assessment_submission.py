"""Prepare a sealed-snapshot request from an audited StratIQ assessment."""
import argparse
import json
from pathlib import Path
from uuid import UUID

from holdout_run import checked_fields, load_json, timestamp
from strategic_report import strategic_report
from validation import text


LICENSES = {"research_only": "research_only", "commercial": "commercial_allowed"}

SUBMIT_SQL = """
select stratiq_private.submit_assessment(
    %s::uuid, %s::uuid, %s::text, %s::timestamptz, %s::text,
    %s::jsonb, %s::jsonb, %s::jsonb
)
"""


def prepare_submission(bundle, request):
    checked_fields(request, "request_id company_id methodology_version model_version sources")
    if not all(text(request[key]) for key in ("request_id", "company_id", "methodology_version", "model_version")):
        raise ValueError("request, company, methodology and model identifiers required")
    if not isinstance(request["sources"], dict):
        raise ValueError("source registry records must be keyed by document ID")
    report = strategic_report(bundle)
    if report["scoring"]["index"] is None:
        raise ValueError("report coverage does not qualify for sealing")
    assessments, citations = [], []
    for framework in report["frameworks"].values():
        for row in framework["elements"]:
            assessments.append({key: row[key] for key in ("element", "status", "score", "rationale")})
            for citation in row["citations"]:
                citations.append({"element": row["element"], **citation})

    documents = {source["id"]: source for source in report["sources"]}
    referenced = {citation["document_id"] for citation in citations}
    if request["sources"].keys() != referenced:
        raise ValueError("registry must contain exactly the cited documents")
    source_ids = {}
    for document_id, record in request["sources"].items():
        checked_fields(record, "id url content_sha256 available_at retrieved_at license_status")
        document = documents[document_id]
        if (record["content_sha256"] != document["sha256"] or record["url"] != document["origin"]
                or timestamp(record["available_at"]) != timestamp(document["available_at"])
                or timestamp(record["retrieved_at"]) != timestamp(document["retrieved_at"])
                or record["license_status"] != LICENSES[document["license"]]):
            raise ValueError("registered source does not match audited document")
        if not text(record["id"]):
            raise ValueError("missing registry source UUID")
        source_ids[document_id] = str(UUID(record["id"]))
    if len(set(source_ids.values())) != len(source_ids):
        raise ValueError("duplicate registry source UUID")

    entries = [
        {
            "element": citation["element"],
            "source_id": source_ids[citation["document_id"]],
            "locator": f'utf8-bytes:{citation["start"]}-{citation["end"]}:{citation["stance"]}',
        }
        for citation in citations
    ]
    manifest = {
        "scoring_methodology": report["scoring"]["methodology"],
        "audit": report["evidence_audit"],
        "publication": report["publication"],
        "sources": [
            {"source_id": source_ids[key], "sha256": documents[key]["sha256"]}
            for key in sorted(source_ids)
        ],
    }
    return {
        "request_id": str(UUID(request["request_id"])),
        "company_id": str(UUID(request["company_id"])),
        "methodology_version": request["methodology_version"],
        "cutoff": report["as_of"],
        "model_version": request["model_version"],
        "manifest": manifest,
        "assessments": assessments,
        "citations": sorted(entries, key=lambda row: (row["element"], row["source_id"], row["locator"])),
    }


def submit_assessment(cursor, bundle, request):
    """Submit with a psycopg-compatible cursor inside the worker transaction."""
    payload = prepare_submission(bundle, request)
    cursor.execute(SUBMIT_SQL, (
        payload["request_id"], payload["company_id"], payload["methodology_version"],
        payload["cutoff"], payload["model_version"],
        *(json.dumps(payload[key], default=str, allow_nan=False)
          for key in ("manifest", "assessments", "citations")),
    ))
    return str(cursor.fetchone()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        result = prepare_submission(load_json(args.bundle), load_json(args.request))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, default=str, allow_nan=False))


if __name__ == "__main__":
    main()
