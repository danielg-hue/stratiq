from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from holdout_run import evaluate, register, registration_digest


class HoldoutWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.spec = {"start": "2024-01-01T00:00:00Z", "end": "2024-02-01T00:00:00Z",
                     "label_cutoff": "2025-03-01T00:00:00Z",
                     "models": ["strategic", "baseline"], "metric": "revenue_growth"}
        dates = {"as_of": "2024-01-01T00:00:00Z", "outcome_end": "2025-01-01T00:00:00Z"}
        self.predictions = [
            dict(dates, company=str(i), scores={"strategic": i, "baseline": -i},
                 feature_available_at={model: dates["as_of"] for model in self.spec["models"]})
            for i in range(3)
        ]
        self.labels = {"metric": "revenue_growth", "rows": [
            dict(dates, company=str(i), label_available_at="2025-02-01T00:00:00Z", value=i / 10)
            for i in range(3)
        ]}
        self.artifact = b"locked model"
        protocol, _ = register(self.spec, self.artifact, self.predictions)
        self.digest = registration_digest(protocol, self.spec["metric"])

    def test_separate_cli_round_trip(self):
        with TemporaryDirectory() as scratch:
            directory = Path(scratch)
            paths = [directory / name for name in ("spec.json", "model.bin", "predictions.json", "labels.json")]
            for path, data in zip(paths, (self.spec, self.artifact, self.predictions, self.labels)):
                path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
            script = Path(__file__).with_name("holdout_run.py")
            command = [sys.executable, script]
            registered = json.loads(subprocess.check_output([*command, "register", *paths[:3]]))
            self.assertEqual(registered["registration_sha256"], self.digest)
            report = json.loads(subprocess.check_output([
                *command, "evaluate", *paths[:3], self.digest, paths[3],
            ]))
            self.assertEqual(report["cohorts"][0]["rank_ic"], {"strategic": 1, "baseline": -1})
            self.assertNotIn("rows", report)

    def test_changed_metric_artifact_or_prediction_rejected(self):
        amended = deepcopy(self.predictions)
        amended[0]["scores"]["strategic"] = 20
        for spec, artifact, predictions in [
            (dict(self.spec, metric="total_return"), self.artifact, self.predictions),
            (self.spec, b"other", self.predictions),
            (self.spec, self.artifact, amended),
        ]:
            with self.assertRaisesRegex(ValueError, "differs"):
                evaluate(spec, self.digest, artifact, predictions, self.labels)

    def test_missing_duplicate_and_late_labels_rejected(self):
        first, second, third = self.labels["rows"]
        for rows, message in [
            ([first, second], "missing"),
            ([first, second, first, third], "duplicate"),
            ([dict(first, label_available_at="2025-03-02T00:00:00Z"), second, third], "unavailable"),
        ]:
            with self.assertRaisesRegex(ValueError, message):
                evaluate(self.spec, self.digest, self.artifact, self.predictions, dict(self.labels, rows=rows))

    def test_label_bearing_predictions_and_future_features_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected exactly"):
            register(self.spec, self.artifact, [dict(self.predictions[0], value=0)])
        amended = deepcopy(self.predictions)
        amended[0]["feature_available_at"]["strategic"] = "2024-01-02T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "point-in-time"):
            register(self.spec, self.artifact, amended)
