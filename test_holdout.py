from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import unittest

from backtest import Observation
from holdout import HoldoutProtocol, development_rows, evaluate_holdout, prediction_digest


def date(month):
    return datetime(2020, month, 1, tzinfo=timezone.utc)


class HoldoutTest(unittest.TestCase):
    def setUp(self):
        self.artifact = b"fixed model"
        self.rows = [
            Observation(str(i), date(5), date(7), date(8),
                        {"strategic": i, "baseline": -i}, i / 10,
                        {"strategic": date(4), "baseline": date(4)})
            for i in range(3)
        ]

        models = ("strategic", "baseline")
        self.protocol = HoldoutProtocol(
            date(5), date(7), date(9), models, sha256(self.artifact).hexdigest(),
            prediction_digest(models, self.rows),
        )

    def test_changed_predictions_rejected(self):
        amended = [replace(self.rows[0], scores={"strategic": 2, "baseline": 0}), *self.rows[1:]]
        with self.assertRaisesRegex(ValueError, "predictions differ"):
            evaluate_holdout(self.protocol, self.protocol.digest, self.artifact, amended)

    def test_matched_fixed_model_comparison(self):
        result = evaluate_holdout(self.protocol, self.protocol.digest, self.artifact, self.rows)
        self.assertEqual(result["cohorts"][0]["rank_ic"], {"strategic": 1, "baseline": -1})

    def test_changed_protocol_or_artifact_rejected(self):
        for protocol, artifact in (
            (replace(self.protocol, end=date(8)), self.artifact),
            (self.protocol, b"changed model"),
        ):
            with self.assertRaisesRegex(ValueError, "differs"):
                evaluate_holdout(protocol, self.protocol.digest, artifact, self.rows)

    def test_development_split_purges_overlap_and_late_labels(self):
        base = self.rows[0]
        mature = replace(base, as_of=date(1), outcome_end=date(2), label_available_at=date(4))
        late = replace(mature, label_available_at=date(5))
        overlap = replace(late, outcome_end=date(6), label_available_at=date(7))
        self.assertEqual(development_rows([mature, late, overlap, base], date(5)), (mature,))

    def test_rejects_mixed_split(self):
        mixed = [*self.rows, replace(self.rows[0], as_of=date(4))]
        with self.assertRaisesRegex(ValueError, "holdout-only"):
            evaluate_holdout(self.protocol, self.protocol.digest, self.artifact, mixed)

    def test_rejects_undefined_comparison(self):
        rows = self.rows[:2]
        protocol = replace(self.protocol, predictions_sha256=prediction_digest(self.protocol.models, rows))
        with self.assertRaisesRegex(ValueError, "no cohort"):
            evaluate_holdout(protocol, protocol.digest, self.artifact, rows)
