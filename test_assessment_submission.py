from unittest import TestCase
from unittest.mock import Mock

from assessment_submission import prepare_submission, submit_assessment
from test_strategic_report import bundle


def request_for(data):
    document = data["documents"][0]
    return {
        "request_id": "00000000-0000-0000-0000-000000000030",
        "company_id": "00000000-0000-0000-0000-000000000001",
        "methodology_version": "qa-1", "model_version": "qa-adapter",
        "sources": {document["id"]: {
            "id": "00000000-0000-0000-0000-000000000031",
            "url": document["origin"], "content_sha256": document["sha256"],
            "available_at": document["available_at"], "retrieved_at": document["retrieved_at"],
            "license_status": "research_only",
        }},
    }


class AssessmentSubmissionTest(TestCase):
    def test_matches_registry_and_preserves_internal_status(self):
        data = bundle()
        request = request_for(data)
        payload = prepare_submission(data, request)
        self.assertEqual(len(payload["assessments"]), 50)
        self.assertEqual(len(payload["citations"]), 50)
        self.assertTrue(payload["citations"][0]["locator"].endswith(":supports"))
        self.assertFalse(payload["manifest"]["publication"]["publishable"])
        data["citations"].reverse()
        data["assessments"].reverse()
        self.assertEqual(prepare_submission(data, request), payload)

    def test_mismatched_metadata_or_extra_registry_record_rejected(self):
        data = bundle()
        for field, value in [
            ("content_sha256", "0" * 64), ("license_status", "commercial_allowed"),
            ("url", "other publisher"), ("available_at", "2023-01-02T00:00:00Z"),
            ("retrieved_at", "2023-01-03T00:00:00Z"),
        ]:
            request = request_for(data)
            request["sources"]["source-1"][field] = value
            with self.assertRaisesRegex(ValueError, "does not match"):
                prepare_submission(data, request)
        request = request_for(data)
        request["sources"]["unreferenced"] = {}
        with self.assertRaisesRegex(ValueError, "exactly the cited"):
            prepare_submission(data, request)

    def test_parameterized_cursor_keeps_rationale_out_of_sql(self):
        data = bundle()
        rationale = "Rationale includes quotes ' and line\nbreaks"
        data["assessments"][0]["rationale"] = rationale
        request = request_for(data)
        cursor = Mock()
        cursor.fetchone.return_value = (request["request_id"],)
        self.assertEqual(submit_assessment(cursor, data, request), request["request_id"])
        statement, parameters = cursor.execute.call_args.args
        self.assertNotIn("Rationale includes quotes", statement)
        self.assertIn("Rationale includes quotes", parameters[6])
        self.assertEqual(len(parameters), 8)

    def test_incomplete_draft_never_reaches_database(self):
        data = bundle()
        data["assessments"] = data["assessments"][:1]
        data["citations"] = data["citations"][:1]
        cursor = Mock()
        with self.assertRaisesRegex(ValueError, "coverage"):
            submit_assessment(cursor, data, request_for(data))
        cursor.execute.assert_not_called()
