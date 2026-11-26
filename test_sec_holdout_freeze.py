import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from sec_holdout_freeze import freeze
from test_sec_pilot import filing


class SecHoldoutFreezeTest(TestCase):
    def test_prediction_compiles_without_outcome_and_ignores_late_revision(self):
        tags = {
            "Assets": [filing("2024-12-31", "2025-03-01", 100), filing("2025-12-31", "2026-03-01", 100)],
            "Revenues": [filing("2025-12-31", "2026-03-01", 100, "2025-01-01")],
            "NetIncomeLoss": [filing("2025-12-31", "2026-03-01", 10, "2025-01-01")],
            "NetCashProvidedByUsedInOperatingActivities": [
                filing("2025-12-31", "2026-03-01", 8, "2025-01-01"),
            ],
        }
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            universe = folder / "issuers"
            universe.write_text("ONE 123\n")
            payload = {"cik": 123, "facts": {"us-gaap": {
                tag: {"units": {"USD": records}} for tag, records in tags.items()
            }}}
            archive = folder / "ONE.json"
            archive.write_text(json.dumps(payload))
            before, coverage = freeze(universe, folder)
            self.assertEqual(coverage[0]["initial_revenue"], "100")
            self.assertEqual(before[0]["scores"], {"return_on_assets": .1, "negative_sloan_accruals": -.02})
            tags["NetIncomeLoss"].append(filing("2025-12-31", "2026-05-01", 99, "2025-01-01"))
            tags["Revenues"].append(filing("2026-12-31", "2027-02-01", 150, "2026-01-01"))
            archive.write_text(json.dumps(payload))
            self.assertEqual(freeze(universe, folder)[0], before)
