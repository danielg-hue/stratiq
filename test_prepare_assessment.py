from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

from prepare_assessment import prepare_assessment
from test_strategic_report import bundle


class PrepareAssessmentTest(TestCase):
    def setUp(self):
        fixture = bundle()
        self.document = fixture.pop("documents")[0]
        self.citations = fixture.pop("citations")[:2]
        fixture["assessments"] = fixture["assessments"][:2]
        self.judgments = fixture

    def test_merges_citations_across_exact_document_references(self):
        intakes = [{"document": self.document, "citations": [citation]} for citation in self.citations]
        assembled, report, gaps = prepare_assessment(self.judgments, intakes)
        self.assertEqual(len(assembled["documents"]), 1)
        self.assertEqual(report["scoring"]["assessed"], 2)
        self.assertIsNone(report["scoring"]["index"])
        self.assertEqual(len(gaps["unknown"]), 48)
        self.assertTrue(all(item["preferred_evidence"] for item in gaps["unknown"]))

    def test_metadata_conflicts_and_bad_citations_fail_closed(self):
        first = {"document": self.document, "citations": self.citations}
        variant = deepcopy(first)
        variant["document"]["origin"] = "Other publisher"
        with self.assertRaisesRegex(ValueError, "conflicting intake metadata"):
            prepare_assessment(self.judgments, [first, variant])
        first["citations"][0]["excerpt"] = "altered excerpt"
        with self.assertRaisesRegex(ValueError, "excerpt mismatch"):
            prepare_assessment(self.judgments, [first])

    def test_cli_never_overwrites_an_existing_draft(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            judgment_path, intake_path, output = [folder / name for name in ("judgments", "intake", "draft")]
            judgment_path.write_text(json.dumps(self.judgments))
            intake_path.write_text(json.dumps({"document": self.document, "citations": self.citations}))
            command = [sys.executable, Path(__file__).with_name("prepare_assessment.py"),
                       judgment_path, output, intake_path]
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["bundle.json", "report.json", "research-gaps.json"])
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
