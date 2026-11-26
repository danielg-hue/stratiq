from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sec_cohort import revenue_periods, run
from sec_pilot import CONTRACT_REVENUE
from test_sec_pilot import filing


class CohortTest(unittest.TestCase):
    def test_missing_label_cannot_switch_the_feature_tag(self):
        current = filing("2020-12-31", "2021-03-01", 100, "2020-01-01")
        later = filing("2021-12-31", "2022-03-01", 125, "2021-01-01")
        raw = json.dumps({"facts": {"us-gaap": {
            "Revenues": {"units": {"USD": [current]}},
            CONTRACT_REVENUE: {"units": {"USD": [current, later]}},
        }}}).encode()
        with self.assertRaisesRegex(ValueError, "outcome missing"):
            revenue_periods(raw, 2020, datetime(2021, 4, 1, tzinfo=timezone.utc),
                            datetime(2022, 4, 1, tzinfo=timezone.utc))

    def test_common_tag_is_required_and_vintage_is_respected(self):
        tags = {
            "Assets": [filing("2019-12-31", "2020-03-01", 100), filing("2020-12-31", "2021-03-01", 100)],
            "NetIncomeLoss": [filing("2020-12-31", "2021-03-01", 10, "2020-01-01")],
            "NetCashProvidedByUsedInOperatingActivities": [filing("2020-12-31", "2021-03-01", 7, "2020-01-01")],
            "Revenues": [filing("2020-12-31", "2021-05-01", 100, "2020-01-01"),
                         filing("2021-12-31", "2022-03-01", 125, "2021-01-01")],
            CONTRACT_REVENUE: [filing("2020-12-31", "2021-03-01", 90, "2020-01-01"),
                               filing("2021-12-31", "2022-03-01", 120, "2021-01-01")],
        }
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            cohort = directory / "issuers.tsv"
            cohort.write_text("SYN 123\nMISSING 789\nOTHER 456\n")
            facts = {"cik": 123, "facts": {"us-gaap": {k: {"units": {"USD": v}} for k, v in tags.items()}}}
            for ticker in ("SYN", "OTHER"):
                (directory / f"{ticker}.json").write_text(json.dumps(facts))
            result = run(cohort, directory, 2020)
            self.assertEqual(result["matched_size"], 1)
            self.assertEqual(result["coverage"][0]["revenue_tag"], CONTRACT_REVENUE)
            self.assertEqual(result["coverage"][1]["reason"], "archive missing")
            self.assertEqual(result["coverage"][2]["reason"], "archive CIK does not match cohort")
            facts["facts"]["us-gaap"][CONTRACT_REVENUE]["units"]["USD"].pop()
            (directory / "SYN.json").write_text(json.dumps(facts))
            self.assertEqual(run(cohort, directory, 2020)["matched_size"], 0)
