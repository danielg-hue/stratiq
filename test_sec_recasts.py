from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest import TestCase

from holdout_run import timestamp
from sec_facts import Fact
from sec_recasts import reconcile_recast
from sec_rolling import filing_inputs


class RecastTest(TestCase):
    def setUp(self):
        def fact(accession, form, start, end, available, value):
            cutoff = timestamp(available)
            return Fact(accession, form, date.fromisoformat(start), date.fromisoformat(end),
                        cutoff.date(), cutoff, Decimal(value), "a" * 64)

        accession = "0000773840-26-000143"
        filed = "2026-10-23T04:00:00Z"
        self.facts = (
            fact("annual", "10-K", "2025-01-01", "2025-12-31", "2026-02-18T05:00:00Z", "37442000000"),
            fact(accession, "10-Q", "2026-01-01", "2026-09-30", filed, "15004000000"),
            fact(accession, "10-Q", "2025-01-01", "2025-09-30", filed, "14703000000"),
        )
        self.cutoff = timestamp("2026-11-26T00:00:00Z")

    def test_verified_basis_uses_recast_annual_and_same_filing_comparative(self):
        result = reconcile_recast(773840, self.cutoff, self.facts, filing_inputs(self.facts))
        self.assertEqual(result["trailing_four_quarter_revenue_usd"], "20246000000")
        self.assertEqual(result["year_over_year"]["prior_revenue_usd"], "19891000000")
        self.assertAlmostEqual(result["year_over_year"]["percent"], 1.784726760846614)
        self.assertEqual(result["inputs"][0]["document"], "exhibit992-junexwintersupp.htm")

    def test_recast_cannot_apply_to_a_future_vintage_or_changed_comparative(self):
        annual, interim, prior = self.facts
        for adjusted in ((annual, replace(interim, accession="different"), prior),
                         (annual, interim, replace(prior, value=Decimal("14700000000")))):
            self.assertIsNone(reconcile_recast(773840, self.cutoff, adjusted, filing_inputs(adjusted)))
