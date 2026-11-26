from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from holdout_run import timestamp
from research.rolling_snapshot import build_snapshot, replace_snapshot


class RefreshTest(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.destination = self.folder / "rolling.json"
        self.current = {"cutoff": "2026-11-26T00:00:00+00:00", "issuers": [
            {"cik": 1, "ticker": "ONE", "period_end": "2026-09-30"},
        ]}
        self.before = json.dumps(self.current)
        self.destination.write_text(self.before)

    def test_valid_update_and_identical_retry(self):
        candidate = dict(self.current, cutoff="2026-11-26T01:00:00+00:00")
        self.assertTrue(replace_snapshot(self.destination, candidate))
        self.assertEqual(json.loads(self.destination.read_text()), candidate)
        self.assertFalse(replace_snapshot(self.destination, candidate))

    def test_bad_candidates_leave_last_good_snapshot_intact(self):
        for alteration, expected in (
            ({"cutoff": "2026-11-25T00:00:00+00:00"}, "cutoff is older"),
            ({"issuers": [{"cik": 1, "ticker": "ONE", "unavailable": True}]}, "no usable result"),
            ({"issuers": [{"cik": 1, "ticker": "ONE", "period_end": "2026-06-30"}]}, "move backward"),
            ({"issuers": [{"cik": 2, "ticker": "ONE", "period_end": "2026-09-30"}]}, "universe differs"),
        ):
            candidate = deepcopy(self.current)
            candidate.update(alteration)
            with self.assertRaisesRegex(ValueError, expected):
                replace_snapshot(self.destination, candidate)
            self.assertEqual(self.destination.read_text(), self.before)

    def test_strict_refresh_stops_on_failed_archive(self):
        universe = self.folder / "issuers.tsv"
        universe.write_text("ONE 1\n")

        def failed(ticker, cik):
            raise OSError("SEC download failed")

        with self.assertRaisesRegex(ValueError, "ONE: SEC download failed"):
            build_snapshot(universe, failed, timestamp(self.current["cutoff"]), strict=True)
        self.assertEqual(self.destination.read_text(), self.before)

    def test_known_reporting_basis_gap_can_remain_unavailable_on_refresh(self):
        self.current["issuers"][0] = {"cik": 1, "ticker": "ONE", "unavailable": True,
                                      "unavailable_reason": "reporting_basis"}
        self.destination.write_text(json.dumps(self.current))
        candidate = dict(self.current, cutoff="2026-11-26T01:00:00+00:00")
        self.assertTrue(replace_snapshot(self.destination, candidate))
