from copy import deepcopy
from unittest import TestCase

from strategic_review import record_review, review_packet
from test_strategic_report import bundle


class StrategicReviewTest(TestCase):
    def setUp(self):
        self.bundle = bundle()
        self.bundle["assessments"] = self.bundle["assessments"][:2]
        self.bundle["citations"] = self.bundle["citations"][:2]
        self.packet = review_packet(self.bundle)
        self.review = {
            "review_sha256": self.packet["review_sha256"], "reviewer": "Fixture Reviewer",
            "decisions": [
                {"element": item["element"], "decision": "agree", "rationale": "Fixture agreement"}
                for item in self.packet["elements"]
            ],
        }

    def test_agreement_is_recorded_without_publication(self):
        result = record_review(self.bundle, self.review)
        self.assertEqual(result["review_status"], "review_recorded")
        self.assertFalse(result["publishable"])
        self.assertEqual(len(result["decisions"]), 2)

    def test_revision_and_missing_or_duplicate_decisions(self):
        review = deepcopy(self.review)
        review["decisions"][0]["decision"] = "unsupported"
        result = record_review(self.bundle, review)
        self.assertEqual(result["review_status"], "revision_required")
        self.assertEqual(result["revision_elements"], [review["decisions"][0]["element"]])
        review["decisions"].pop()
        with self.assertRaisesRegex(ValueError, "missing"):
            record_review(self.bundle, review)
        review["decisions"].append(review["decisions"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            record_review(self.bundle, review)

    def test_changed_score_or_risk_flags_invalidate_decisions(self):
        for field, value in (("score", "1.50"), ("rationale", "Revised rationale")):
            updated = deepcopy(self.bundle)
            updated["assessments"][0][field] = value
            with self.assertRaisesRegex(ValueError, "does not match"):
                record_review(updated, self.review)
        updated = dict(self.bundle, risk_flags=[])
        with self.assertRaisesRegex(ValueError, "does not match"):
            record_review(updated, self.review)
