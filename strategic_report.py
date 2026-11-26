"""Generate an internal evidence-audited strategic assessment draft."""
import argparse
from base64 import b64decode
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from core import Assessment, Evidence, FRAMEWORKS, index
from evidence import Citation, Document, audit
from holdout_run import checked_fields, load_json, timestamp
from rubrics import publication_gate
from validation import text


def assessment_score(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 32:
        raise ValueError("score must be a decimal string or null")
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal score") from error


def strategic_report(bundle):
    checked_fields(bundle, "company as_of documents citations assessments risk_flags")
    if not text(bundle["company"]):
        raise ValueError("company required")
    for key in ("documents", "citations", "assessments", "risk_flags"):
        if not isinstance(bundle[key], list):
            raise ValueError(f"{key} must be a list")
    if any(not text(flag) for flag in bundle["risk_flags"]):
        raise ValueError("risk flags must be nonempty strings")
    cutoff = timestamp(bundle["as_of"])
    documents, citations = [], []
    for row in bundle["documents"]:
        checked_fields(row, "id origin available_at retrieved_at content_base64 sha256 license")
        if not isinstance(row["content_base64"], str) or len(row["content_base64"]) > 13_333_336:
            raise ValueError("invalid document content")
        documents.append(Document(row["id"], row["origin"], timestamp(row["available_at"]),
                                  timestamp(row["retrieved_at"]), b64decode(row["content_base64"], validate=True),
                                  row["sha256"], row["license"]))
    for row in bundle["citations"]:
        checked_fields(row, "element document_id start end excerpt stance")
        if not all(text(row[key]) for key in ("element", "document_id", "excerpt")):
            raise ValueError("invalid citation text")
        citations.append(Citation(row["element"], row["document_id"], row["start"], row["end"],
                                  row["excerpt"].encode("utf-8"), row["stance"]))

    evidence_audit = audit(documents, citations, cutoff)
    sources = {document.id: document for document in documents}
    references = {}
    for citation in citations:
        references.setdefault(citation.element, []).append(citation)

    assessments = {}
    for row in bundle["assessments"]:
        checked_fields(row, "element status score rationale")
        element = row["element"]
        if not text(element) or element in assessments or not isinstance(row["rationale"], str):
            raise ValueError("duplicate or invalid assessment")
        supporting = [
            Evidence(citation.document_id, sources[citation.document_id].available_at,
                     sources[citation.document_id].origin)
            for citation in references.get(element, ()) if citation.stance == "supports"
        ]
        assessments[element] = Assessment(element, row["status"], assessment_score(row["score"]),
                                          tuple(supporting), row["rationale"])
    if references.keys() - assessments.keys():
        raise ValueError("citations must reference explicit assessments")
    scored = index(assessments.values(), cutoff)
    publication = publication_gate(scored, bundle["risk_flags"])
    frameworks = {}
    for framework, elements in FRAMEWORKS.items():
        results = []
        for element in elements:
            row = assessments.get(element, Assessment(element, "unknown", None))
            results.append({
                "element": element, "status": row.status, "score": row.score, "rationale": row.rationale,
                "citations": [
                    {"document_id": item.document_id, "start": item.start,
                     "end": item.end, "stance": item.stance}
                    for item in references.get(element, ())
                ],
            })
        frameworks[framework] = {
            "assessed": sum(row["status"] == "assessed" for row in results),
            "total": len(elements), "elements": results,
        }
    return {
        "company": bundle["company"], "as_of": cutoff.isoformat(), "status": "internal_draft",
        "scoring": scored, "publication": publication, "frameworks": frameworks,
        "evidence_audit": evidence_audit,
        "sources": [
            {"id": document.id, "origin": document.origin, "sha256": document.digest,
             "available_at": document.available_at.isoformat(), "retrieved_at": document.retrieved_at.isoformat(),
             "license": document.license}
            for document in documents
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        report = strategic_report(load_json(args.bundle))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, indent=2, default=str, allow_nan=False))


if __name__ == "__main__":
    main()
