from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from sec_filing import package_filing, primary_filing
from strategic_report import strategic_report


ACCESSION = "0000320193-24-000123"
ACCEPTED = "2024-11-01T10:01:36Z"
FILENAME = "aapl-20240928.htm"


def submissions(filename=FILENAME):
    return {"cik": "0000320193", "filings": {"recent": {
        "accessionNumber": [ACCESSION], "acceptanceDateTime": [ACCEPTED],
        "form": ["10-K"], "primaryDocument": [filename],
    }}}


class SecFilingTest(TestCase):
    def test_raw_utf8_byte_offsets_feed_report(self):
        with TemporaryDirectory() as folder:
            archive = Path(folder) / FILENAME
            archive.write_bytes("<p>€ analyst excerpt</p>".encode())
            package = package_filing(submissions(), ACCESSION, archive, "2024-11-02T00:00:00Z",
                                     [{"element": "disclosure", "excerpt": "analyst excerpt", "stance": "context"}])
        self.assertEqual(package["citations"][0]["start"], 7)
        self.assertTrue(package["document"]["origin"].endswith("/320193/000032019324000123/" + FILENAME))
        report = strategic_report({
            "company": "Fixture", "as_of": "2024-11-02T00:00:00Z", "documents": [package["document"]],
            "citations": package["citations"], "risk_flags": [],
            "assessments": [{"element": "disclosure", "status": "unknown", "score": None, "rationale": ""}],
        })
        self.assertTrue(report["evidence_audit"]["integrity_checked"])
        self.assertFalse(report["publication"]["publishable"])

    def test_invalid_record_identity_and_unsafe_filename_rejected(self):
        with self.assertRaisesRegex(ValueError, "filename"):
            primary_filing(submissions("../wrong.htm"), ACCESSION)
        with self.assertRaisesRegex(ValueError, "matching accession"):
            primary_filing(submissions(), "0000320193-24-000124")

    def test_missing_ambiguous_and_future_retrieval_rejected(self):
        with TemporaryDirectory() as folder:
            archive = Path(folder) / FILENAME
            archive.write_bytes(b"duplicate duplicate")
            for excerpt in ("duplicate", "not present"):
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    package_filing(submissions(), ACCESSION, archive, "2024-11-02T00:00:00Z", [
                        {"element": "disclosure", "excerpt": excerpt, "stance": "context"},
                    ])
            with self.assertRaisesRegex(ValueError, "precedes"):
                package_filing(submissions(), ACCESSION, archive, "2024-11-01T09:00:00Z", [])

    def test_definitive_proxy_is_eligible_for_governance_intake(self):
        fixture = submissions()
        fixture["filings"]["recent"]["form"] = ["DEF 14A"]
        filename, url, _ = primary_filing(fixture, ACCESSION)
        self.assertIn(filename, url)
        fixture["filings"]["recent"]["form"] = ["8-K"]
        with self.assertRaisesRegex(ValueError, "unsupported SEC filing form"):
            primary_filing(fixture, ACCESSION)
