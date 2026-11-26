from datetime import date, datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sec_pilot import issuer_observation, run


def filing(end, filed, val, start=None):
    result = {"end": end, "filed": filed, "val": val, "accn": filed, "form": "10-K"}
    if start:
        result["start"] = start
    return result


class PilotTest(unittest.TestCase):
    def setUp(self):
        self.periods = tuple(map(date.fromisoformat, ("2020-01-01", "2020-12-31", "2021-01-01", "2021-12-31")))
        self.times = tuple(datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
                           for t in ("2021-04-01", "2022-01-01", "2022-04-01"))
        self.tags = {
            "Assets": [filing("2019-12-31", "2020-03-01", 100), filing("2020-12-31", "2021-03-01", 100)],
            "NetIncomeLoss": [filing("2020-12-31", "2021-03-01", 10, "2020-01-01"),
                              filing("2020-12-31", "2021-05-01", 90, "2020-01-01")],
            "NetCashProvidedByUsedInOperatingActivities": [filing("2020-12-31", "2021-03-01", 8, "2020-01-01")],
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                filing("2020-12-31", "2021-03-01", 100, "2020-01-01"),
                filing("2021-12-31", "2022-03-01", 125, "2021-01-01"),
            ],
        }

    def archive(self):
        return json.dumps({"cik": 123, "facts": {"us-gaap": {
            tag: {"units": {"USD": values}} for tag, values in self.tags.items()
        }}}).encode()

    def test_benchmarks_ignore_future_restatement(self):
        row = issuer_observation(self.archive(), *self.periods, *self.times)
        self.assertEqual(row.scores, {"return_on_assets": .1, "negative_sloan_accruals": -.02})
        self.assertEqual(row.total_return, .25)
        self.assertTrue(all(timestamp <= row.as_of for timestamp in row.feature_available_at.values()))

    def test_label_and_missing_account_excluded(self):
        as_of, horizon, _ = self.times
        self.assertIsNone(issuer_observation(self.archive(), *self.periods, as_of, horizon, horizon))
        self.tags.pop("Assets")
        self.assertIsNone(issuer_observation(self.archive(), *self.periods, *self.times))

    def test_naive_cohort_timestamps_rejected(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps(dict(zip(("as_of", "outcome_end", "evaluation_cutoff"),
                                                  ("2021-04-01", "2022-01-01", "2022-04-01")))))
            with self.assertRaisesRegex(ValueError, "timezone-aware"):
                run(config)
