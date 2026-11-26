import json
from unittest import TestCase

from holdout_run import timestamp
from sec_rolling import rolling_revenue
from test_sec_pilot import filing


def data():
    annual = filing("2025-12-31", "2026-02-20", 100, "2025-01-01")
    current = dict(filing("2026-06-30", "2026-08-01", 65, "2026-01-01"), form="10-Q", accn="q2")
    prior = dict(filing("2025-06-30", "2026-08-01", 45, "2025-01-01"), form="10-Q", accn="q2")
    later = dict(filing("2026-09-30", "2026-11-01", 90, "2026-01-01"), form="10-Q", accn="q3")
    return [annual, current, prior, later]


def archive(records):
    return json.dumps({"cik": 1, "entityName": "Fixture", "facts": {
        "us-gaap": {"Revenues": {"units": {"USD": records}}},
    }}).encode()


class RollingTest(TestCase):
    def test_annual_to_interim_with_cutoff_at_filing_availability(self):
        raw = archive(data())
        before = rolling_revenue(raw, timestamp("2026-08-02T03:59:59Z"))
        self.assertEqual(before["period_end"], "2025-12-31")
        self.assertEqual(before["trailing_four_quarter_revenue_usd"], "100")
        after = rolling_revenue(raw, timestamp("2026-08-02T04:00:00Z"))
        self.assertEqual(after["period_end"], "2026-06-30")
        self.assertEqual(after["trailing_four_quarter_revenue_usd"], "120")
        self.assertEqual(after["interim_quarters"], 2)
        self.assertEqual([row["accession"] for row in after["inputs"]][1:], ["q2", "q2"])

    def test_incomplete_newer_period_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "prior-year YTD"):
            rolling_revenue(archive(data()), timestamp("2026-11-26T00:00:00Z"))

    def test_cross_filing_comparative_is_rejected(self):
        records = data()[:3]
        records[2]["accn"] = "other"
        with self.assertRaisesRegex(ValueError, "prior-year YTD"):
            rolling_revenue(archive(records), timestamp("2026-08-05T00:00:00Z"))


    def test_late_annual_revision_does_not_mix_with_older_interim_comparatives(self):
        records = data()[:3]
        records.append(dict(records[0], filed="2026-09-01", form="10-K/A", accn="amended", val=110))
        with self.assertRaisesRegex(ValueError, "annual baseline was revised"):
            rolling_revenue(archive(records), timestamp("2026-09-05T00:00:00Z"))

    def test_nonnumeric_json_fact_is_rejected(self):
        for value in (True, "100"):
            records = data()[:1]
            records[0]["val"] = value
            with self.assertRaisesRegex(ValueError, "JSON number"):
                rolling_revenue(archive(records), timestamp("2026-08-05T00:00:00Z"))
