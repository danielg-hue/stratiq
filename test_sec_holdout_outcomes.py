import json
from unittest import TestCase
from unittest.mock import Mock

from holdout_run import evaluate, register, registration_digest, timestamp
from sec_holdout_freeze import OUTCOME_END, SPEC
from sec_holdout_outcomes import collect_outcomes
from test_sec_pilot import filing


class OutcomesTest(TestCase):
    def setUp(self):
        self.predictions = [
            {"company": str(cik), "as_of": SPEC["start"], "outcome_end": OUTCOME_END,
             "scores": dict(zip(SPEC["models"], (cik, -cik))),
             "feature_available_at": dict.fromkeys(SPEC["models"], SPEC["start"])}
            for cik in range(1, 4)
        ]
        self.artifact = json.dumps({"coverage": [
            {"ticker": f"ISSUER{cik}", "cik": cik, "end": "2025-12-31", "revenue_tag": "Revenues",
             "initial_revenue": "100", "initial_revenue_accession": "frozen"}
            for cik in range(1, 4)
        ]}).encode()
        protocol, _ = register(SPEC, self.artifact, self.predictions)
        self.digest = registration_digest(protocol, SPEC["metric"])
        self.now = timestamp(SPEC["label_cutoff"])

    def archive(self, ticker):
        cik = int(ticker[-1])
        return json.dumps({"cik": cik, "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            filing("2026-12-31", "2027-02-01", 100 + 10*cik, "2026-01-01"),
            filing("2026-12-31", "2027-04-05", 300, "2026-01-01"),
        ]}}}}}).encode()

    def collect(self, reader, now=None, digest=None):
        return collect_outcomes(SPEC, self.artifact, self.predictions, digest or self.digest,
                                reader, now or self.now)

    def test_frozen_denominator_and_cutoff_flow_to_evaluator(self):
        outcomes, evidence = self.collect(self.archive)
        self.assertEqual([row["value"] for row in outcomes["rows"]], [.1, .2, .3])
        self.assertEqual(evidence["outcomes"][1]["final_accession"], "2027-02-01")
        result = evaluate(SPEC, self.digest, self.artifact, self.predictions, outcomes)
        self.assertEqual(list(result["cohorts"][0]["rank_ic"].values()), [1, -1])

    def test_before_cutoff_or_modified_registration_never_reads_labels(self):
        reader = Mock(side_effect=AssertionError)
        with self.assertRaisesRegex(ValueError, "locked until"):
            self.collect(reader, timestamp("2026-11-26T00:00:00Z"))
        with self.assertRaisesRegex(ValueError, "differs"):
            self.collect(reader, digest="0" * 64)
        reader.assert_not_called()

    def test_missing_or_unmatched_issuer_blocks_whole_cohort(self):
        def broken(ticker):
            if ticker == "ISSUER2":
                raise FileNotFoundError("archive missing")
            if ticker == "ISSUER3":
                return self.archive("ISSUER1")
            return self.archive(ticker)

        with self.assertRaisesRegex(ValueError, "ISSUER2: archive missing"):
            self.collect(broken)
        with self.assertRaisesRegex(ValueError, "ISSUER3: SEC archive CIK mismatch"):
            self.collect(broken)
