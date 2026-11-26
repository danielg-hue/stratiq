from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock

from holdout_run import timestamp
from source_registry import register_source, source_record
from test_strategic_report import bundle


def document():
    result = bundle()["documents"][0]
    result["origin"] = "https://www.sec.gov/Archives/test.htm"
    return result


class SourceRegistryTest(TestCase):
    def test_retries_reuse_id_while_content_identity_is_per_url(self):
        original = document()
        result = source_record(original)
        self.assertEqual(result, source_record(deepcopy(original)))
        self.assertNotEqual(result["id"], source_record(dict(original, origin=original["origin"] + "l"))["id"])

    def test_metadata_readback_mismatch_fails_closed(self):
        original = document()
        record = source_record(original)
        cursor = Mock()
        row = (record["id"], record["url"], record["content_sha256"],
               timestamp(record["available_at"]), timestamp(record["retrieved_at"]), record["license_status"])
        cursor.fetchone.return_value = row
        self.assertEqual(register_source(cursor, original), record)
        self.assertEqual(cursor.execute.call_args_list[0].args[1], tuple(record.values()))
        cursor.fetchone.return_value = (*row[:-1], "commercial_allowed")
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            register_source(cursor, original)

    def test_rejects_tampered_bytes_and_credential_bearing_urls(self):
        original = document()
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            source_record(dict(original, sha256="0" * 64))
        for origin in ("https://token@www.sec.gov/private", "http://www.sec.gov/test", "https://www.sec.gov/test#x"):
            with self.assertRaisesRegex(ValueError, "HTTPS source URL"):
                source_record(dict(original, origin=origin))
