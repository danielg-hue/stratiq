from base64 import b64encode
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from core import ELEMENTS
from strategic_report import strategic_report


def bundle():
    content = "€ analyst evidence".encode()
    document = {
        "id": "source-1", "origin": "Synthetic filing", "available_at": "2023-01-01T00:00:00Z",
        "retrieved_at": "2023-01-02T00:00:00Z", "content_base64": b64encode(content).decode(),
        "sha256": sha256(content).hexdigest(), "license": "research_only",
    }
    return {
        "company": "Synthetic", "as_of": "2023-03-01T00:00:00Z", "documents": [document],
        "citations": [
            {"element": element, "document_id": "source-1", "start": 0, "end": len(content),
             "excerpt": content.decode(), "stance": "supports"} for element in sorted(ELEMENTS)
        ],
        "assessments": [
            {"element": element, "status": "assessed", "score": "1.25", "rationale": "Synthetic rationale"}
            for element in sorted(ELEMENTS)
        ],
        "risk_flags": ["fraud"],
    }


class StrategicReportTest(unittest.TestCase):
    def test_cli_outputs_draft_even_with_full_coverage(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "bundle.json"
            path.write_text(json.dumps(bundle()))
            result = subprocess.check_output([sys.executable, Path(__file__).with_name("strategic_report.py"), path])
        report = json.loads(result)
        self.assertEqual(report["scoring"]["index"], "81.25")
        self.assertEqual(report["scoring"]["assessed"], 50)
        self.assertEqual(report["publication"]["critical_flags"], ["fraud"])
        self.assertFalse(report["publication"]["publishable"])
        self.assertFalse(report["evidence_audit"]["claims_verified"])
        self.assertNotIn("content_base64", report["sources"][0])

    def test_incomplete_report_shows_unknown_without_index(self):
        data = bundle()
        data["assessments"] = data["assessments"][:1]
        data["citations"] = data["citations"][:1]
        report = strategic_report(data)
        self.assertIsNone(report["scoring"]["index"])
        self.assertEqual(sum(frame["assessed"] for frame in report["frameworks"].values()), 1)
        self.assertEqual(sum(frame["total"] for frame in report["frameworks"].values()), 50)

    def test_invalid_sources_and_unsupported_scores_block_report(self):
        for field, value, expected in [
            ("sha256", "0" * 64, "digest mismatch"),
            ("available_at", "2024-01-01T00:00:00Z", "chronology"),
            ("license", "restricted", "license"),
        ]:
            data = bundle()
            data["documents"][0][field] = value
            with self.assertRaisesRegex(ValueError, expected):
                strategic_report(data)
        original = bundle()
        for field, value, expected in [
            ("excerpt", "changed", "excerpt mismatch"),
            ("end", 16, "excerpt mismatch"),
            ("stance", "context", "evidence and rationale required"),
        ]:
            data = deepcopy(original)
            data["citations"][0][field] = value
            with self.assertRaisesRegex(ValueError, expected):
                strategic_report(data)

    def test_reference_without_assessment_rejected(self):
        data = bundle()
        data["assessments"].pop()
        with self.assertRaisesRegex(ValueError, "explicit assessments"):
            strategic_report(data)
