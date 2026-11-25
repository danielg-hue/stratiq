from datetime import date, datetime, timezone
import json
import unittest

from sec_facts import select_as_of, vintages


class SecFactsTest(unittest.TestCase):
    def test_filing_vintages_are_not_visible_before_conservative_cutoff(self):
        first = {"end": "2020-09-30", "filed": "2020-10-15", "val": 100,
                 "accn": "initial", "form": "10-Q"}
        second = dict(first, filed="2020-11-15", val=120, accn="amended", form="10-Q/A")
        raw = json.dumps({"facts": {"us-gaap": {"Assets": {"units": {"USD": [first, second]}}}}})
        records = vintages(raw.encode(), "us-gaap", "Assets", "USD")
        period = {"start": None, "end": date(2020, 9, 30)}
        cutoffs = [(10, 16, 3), (10, 16, 4), (11, 16, 5)]
        selected = [select_as_of(records, datetime(2020, m, d, h, tzinfo=timezone.utc), **period)
                    for m, d, h in cutoffs]
        self.assertEqual([record.value if record else None for record in selected], [None, 100, 120])

    def test_conflicting_values_on_same_day_fail_closed(self):
        entry = {"end": "2020-09-30", "filed": "2020-10-15", "val": 100,
                 "accn": "a", "form": "10-Q"}
        raw = json.dumps({"facts": {"us-gaap": {"Assets": {"units": {"USD": [entry, dict(entry, val=80)]}}}}})
        records = vintages(raw.encode(), "us-gaap", "Assets", "USD")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            select_as_of(records, datetime(2020, 10, 20, tzinfo=timezone.utc),
                         start=None, end=date(2020, 9, 30))
