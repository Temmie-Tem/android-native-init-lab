import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_only_live_core.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_boot_only_live_core", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusBootOnlyLiveCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.marker = b"\n[[S22TEST|id=abc|phase=OK]]\n"
        cls.family = b"[[S22TEST|"

    def classify(self, payload):
        return self.module.classify_marker_family(
            payload,
            exact_marker=self.marker,
            family_prefix=self.family,
            historical_family=b"[[S22OLD|",
        )

    def test_timeline_is_ordered_single_events_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.append_event(path, events, name)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"events"})
            self.assertTrue(self.module.timeline_complete(data["events"]))

    def test_timeline_rejects_out_of_order_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            with self.assertRaises(self.module.LiveCoreError):
                self.module.append_event(path, events, self.module.TIMELINE_NAMES[1])
            self.module.append_event(path, events, self.module.TIMELINE_NAMES[0])
            with self.assertRaises(self.module.LiveCoreError):
                self.module.append_event(path, events, self.module.TIMELINE_NAMES[0])

    def test_durable_create_is_exclusive_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "state.json"
            self.module.durable_create_json(path, {"value": 1})
            with self.assertRaises(self.module.LiveCoreError):
                self.module.durable_create_json(path, {"value": 2})
            target = root / "target"
            target.write_text("x", encoding="ascii")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaises(self.module.LiveCoreError):
                self.module.durable_create_json(link, {"value": 3})

    def test_exact_and_repeated_exact_are_positive(self):
        one = self.classify(b"before" + self.marker + b"after")
        self.assertTrue(one["acceptance_present"])
        self.assertEqual(one["exact_count"], 1)
        repeated = self.classify(self.marker + self.marker)
        self.assertTrue(repeated["acceptance_present"])
        self.assertEqual(repeated["exact_count"], 2)

    def test_foreign_malformed_and_boundary_partial_fail_integrity(self):
        foreign = self.classify(b"\n[[S22TEST|id=bad|phase=OK]]\n")
        self.assertTrue(foreign["integrity_issue"])
        missing_newline = self.classify(b"[[S22TEST|id=abc|phase=OK]]")
        self.assertTrue(missing_newline["integrity_issue"])
        partial_tail = self.classify(b"prefix" + self.marker[:20])
        self.assertTrue(partial_tail["integrity_issue"])
        partial_head = self.classify(self.marker[-20:] + b"suffix")
        self.assertTrue(partial_head["integrity_issue"])

    def test_exact_marker_at_payload_tail_is_positive(self):
        result = self.classify(b"prefix" + self.marker)
        self.assertTrue(result["acceptance_present"])
        self.assertFalse(result["partial_at_tail"])

    def test_exact_marker_plus_tail_partial_is_integrity_failure(self):
        result = self.classify(self.marker + b"prefix" + self.marker[:20])
        self.assertEqual(result["exact_count"], 1)
        self.assertTrue(result["partial_at_tail"])
        self.assertTrue(result["integrity_issue"])

    def test_delimiter_mismatch_is_integrity_failure(self):
        result = self.classify(self.marker + self.marker[1:-1])
        self.assertEqual(result["exact_count"], 1)
        self.assertEqual(result["exact_record_count"], 2)
        self.assertEqual(result["delimiter_mismatch_count"], 1)
        self.assertTrue(result["integrity_issue"])

    def test_historical_family_is_reported_but_distinct(self):
        result = self.classify(b"\n[[S22OLD|id=old]]\n")
        self.assertTrue(result["baseline_absent"])
        self.assertFalse(result["integrity_issue"])
        self.assertEqual(result["historical_family_count"], 1)

    def test_unanchored_loose_text_is_not_a_marker(self):
        result = self.classify(b"S22TEST id=abc ordinary text")
        self.assertTrue(result["baseline_absent"])
        self.assertEqual(result["family_count"], 0)

    def test_stable_hash_and_read_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.bin"
            path.write_bytes(b"payload")
            self.assertEqual(self.module.read_stable_file(path), b"payload")
            self.assertEqual(
                self.module.hash_stable_file(path),
                {"size": 7, "sha256": self.module.sha256_bytes(b"payload")},
            )

    def test_capture_exec_out_records_eof_and_empty_stderr(self):
        module = self.module

        def fake_acquire(_argv, capture_dir, name, **kwargs):
            return module.raw_capture.publish_captured_bytes(
                capture_dir,
                name,
                stdout=b"observer",
                stdout_name=kwargs.get("stdout_name"),
                stderr_name=kwargs.get("stderr_name"),
            )

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module.raw_capture, "acquire_command", side_effect=fake_acquire
        ):
            receipt = module.capture_adb_exec_out(
                "serial",
                "cat /proc/last_kmsg",
                Path(temporary) / "capture.bin",
                root=True,
                timeout=1,
                maximum=1024,
            )
        self.assertTrue(receipt["read_to_eof"])
        self.assertEqual(receipt["bytes"], 8)
        self.assertEqual(receipt["stderr_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
