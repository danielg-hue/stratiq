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


    def test_36_week_third_quarter_pairs_with_same_filing_comparative(self):
        facts = [
            filing("2025-12-27", "2026-02-03", 93925, "2024-12-29"),
            dict(filing("2026-09-05", "2026-10-08", 68898, "2025-12-28"), form="10-Q", accn="q3"),
            dict(filing("2025-09-06", "2026-10-08", 64582, "2024-12-29"), form="10-Q", accn="q3"),
        ]
        cutoff = timestamp("2026-11-26T00:00:00Z")
        result = rolling_revenue(archive(facts), cutoff)
        self.assertEqual(result["trailing_four_quarter_revenue_usd"], "98241")
        self.assertEqual(result["interim_quarters"], 3)
        facts[-1]["end"] = "2025-09-20"
        with self.assertRaisesRegex(ValueError, "differ by more than one week"):
            rolling_revenue(archive(facts), cutoff)

    def test_growth_uses_original_matching_prior_window(self):
        records = data()[:3]
        records.extend([
            filing("2024-12-31", "2025-02-20", 90, "2024-01-01"),
            dict(filing("2025-06-30", "2025-08-01", 45, "2025-01-01"), form="10-Q", accn="prior-q2"),
            dict(filing("2024-06-30", "2025-08-01", 40, "2024-01-01"), form="10-Q", accn="prior-q2"),
        ])
        cutoff = timestamp("2026-08-05T00:00:00Z")
        result = rolling_revenue(archive(records), cutoff)
        self.assertEqual(result["year_over_year"]["prior_period_end"], "2025-06-30")
        self.assertEqual(result["year_over_year"]["prior_revenue_usd"], "95")
        self.assertAlmostEqual(result["year_over_year"]["percent"], 100 * 25 / 95)
        records[2]["val"] = 46
        revised = rolling_revenue(archive(records), cutoff)
        self.assertEqual(revised["trailing_four_quarter_revenue_usd"], "119")
        self.assertIsNone(revised["year_over_year"])
