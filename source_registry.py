"""Register byte-verified archive metadata through a trusted ingestion cursor."""
import argparse
from base64 import b64decode
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from assessment_submission import LICENSES
from evidence import Document, audit
from holdout_run import checked_fields, load_json, timestamp


INSERT_SQL = """
insert into stratiq_private.source
    (id, url, content_sha256, available_at, retrieved_at, license_status)
values (%s::uuid, %s, %s, %s::timestamptz, %s::timestamptz, %s)
on conflict (id) do nothing
"""
SELECT_SQL = """
select id, url, content_sha256, available_at, retrieved_at, license_status
from stratiq_private.source where id = %s::uuid
"""


def source_record(document):
    checked_fields(document, "id origin available_at retrieved_at content_base64 sha256 license")
    encoded = document["content_base64"]
    if not isinstance(encoded, str) or len(encoded) > 13_333_336:
        raise ValueError("invalid archive content")
    origin = document["origin"]
    if not isinstance(origin, str) or any(character.isspace() or ord(character) < 32 for character in origin):
        raise ValueError("expected an HTTPS source URL")
    url = urlsplit(origin)
    if url.scheme != "https" or not url.hostname or url.username is not None or url.fragment:
        raise ValueError("expected an HTTPS source URL without credentials or fragments")
    available = timestamp(document["available_at"])
    retrieved = timestamp(document["retrieved_at"])
    raw = b64decode(encoded, validate=True)
    archived = Document(document["id"], origin, available, retrieved, raw, document["sha256"], document["license"])
    audit([archived], [], retrieved)

    # URL and content identify a version. The initial metadata stays immutable.
    identity = json.dumps(["stratiq-source-v1", origin, archived.digest], separators=(",", ":"))
    return {
        "id": str(uuid5(NAMESPACE_URL, identity)), "url": origin, "content_sha256": document["sha256"],
        "available_at": available.isoformat(), "retrieved_at": retrieved.isoformat(),
        "license_status": LICENSES[document["license"]],
    }


def register_source(cursor, document):
    """Insert or verify an identical immutable record in a read-committed transaction."""
    record = source_record(document)
    cursor.execute(INSERT_SQL, tuple(record.values()))
    cursor.execute(SELECT_SQL, (record["id"],))
    row = cursor.fetchone()
    if row is None:
        raise ValueError("registered source could not be read back")
    persisted = {
        "id": str(row[0]), "url": row[1], "content_sha256": row[2],
        "available_at": timestamp(row[3].isoformat()).isoformat(),
        "retrieved_at": timestamp(row[4].isoformat()).isoformat(), "license_status": row[5],
    }
    if persisted != record:
        raise ValueError("immutable source metadata differs from registered record")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path, help="output of sec_filing.py")
    args = parser.parse_args()
    try:
        intake = checked_fields(load_json(args.intake), "document citations")
        record = source_record(intake["document"])
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
