"""Regression tests for a90harness.failure classification helpers."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_harness

failure = load_harness("failure")


class FailureClassificationSchema(unittest.TestCase):
    def test_to_dict_serializes_all_fields(self):
        item = failure.FailureClassification(
            source="workload:demo",
            kind="workload-failed",
            severity="fail",
            summary="summary",
            detail="detail",
            action="action",
        )

        self.assertEqual(
            item.to_dict(),
            {
                "source": "workload:demo",
                "kind": "workload-failed",
                "severity": "fail",
                "summary": "summary",
                "detail": "detail",
                "action": "action",
            },
        )


class WorkloadEventClassification(unittest.TestCase):
    def test_ok_workload_event_is_not_classified(self):
        self.assertIsNone(failure.classify_workload_event({"workload": "smoke", "ok": True}))

    def test_blocked_ncm_gate_is_deferred_with_specific_action(self):
        item = failure.classify_workload_event(
            {
                "workload": "ncm",
                "status": "blocked",
                "resource_locks": ["ncm"],
                "gate": {
                    "reasons": ["requires host USB NCM precondition"],
                    "metadata": {"requires_ncm": True},
                },
            }
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.kind, "policy-blocked")
        self.assertEqual(item.severity, "deferred")
        self.assertEqual(item.summary, "workload blocked by explicit NCM safety gate")
        self.assertIn("--allow-ncm", item.action)

    def test_generic_blocked_gate_uses_reasons_or_detail(self):
        item = failure.classify_workload_event(
            {
                "name": "dangerous",
                "status": "blocked",
                "detail": "operator missing",
                "gate": {"reasons": ["requires explicit operator confirmation"]},
            }
        )

        self.assertEqual(item.source, "workload:dangerous")
        self.assertEqual(item.kind, "policy-blocked")
        self.assertEqual(item.detail, "requires explicit operator confirmation")
        self.assertIn("required_flags", item.action)

    def test_skipped_ncm_path_absent_is_deferred(self):
        item = failure.classify_workload_event(
            {
                "workload": "ncm_tcp",
                "skipped": True,
                "detail": "NCM path 192.168.7.2 not reachable",
            }
        )

        self.assertEqual(item.kind, "env-ncm-missing")
        self.assertEqual(item.severity, "deferred")
        self.assertIn("192.168.7.2", item.action)

    def test_failed_workload_detail_selects_specific_failure_kinds(self):
        cases = [
            ({"workload": "bridge", "ok": False, "detail": "connection refused"}, "bridge-disconnect"),
            ({"workload": "bridge", "ok": False, "detail": "command timeout"}, "bridge-timeout"),
            ({"workload": "storage", "ok": False, "detail": "sha memory-mismatch"}, "storage-mismatch"),
            ({"workload": "other", "ok": False, "detail": "bad result"}, "workload-failed"),
        ]
        for event, expected_kind in cases:
            with self.subTest(expected_kind=expected_kind):
                item = failure.classify_workload_event(event)
                self.assertEqual(item.kind, expected_kind)
                self.assertEqual(item.severity, "fail")

    def test_failed_workload_detail_includes_nested_module_step_detail_and_error(self):
        item = failure.classify_workload_event(
            {
                "workload": "module",
                "ok": False,
                "detail": "top",
                "module": {"steps": [{"detail": "step detail", "error": "step error"}]},
            }
        )

        self.assertEqual(item.kind, "workload-failed")
        self.assertEqual(item.detail, "top step detail step error")


class ObserverSampleClassification(unittest.TestCase):
    def test_ok_observer_sample_is_not_classified(self):
        self.assertIsNone(failure.classify_observer_sample({"name": "status", "ok": True}))

    def test_observer_failure_kinds_are_selected_from_error_rc_and_status(self):
        cases = [
            ({"name": "serial", "ok": False, "error": "connection reset"}, "serial-disconnect"),
            ({"name": "status", "ok": False, "error": "timeout waiting"}, "bridge-timeout"),
            ({"name": "cmd", "ok": False, "rc": 7, "status": "failed", "error": "bad rc"}, "device-command-failed"),
            ({"name": "sample", "ok": False, "text_excerpt": "weird"}, "observer-failed"),
        ]
        for sample, expected_kind in cases:
            with self.subTest(expected_kind=expected_kind):
                item = failure.classify_observer_sample(sample)
                self.assertEqual(item.source, f"observer:{sample['name']}")
                self.assertEqual(item.kind, expected_kind)
                self.assertEqual(item.severity, "fail")

    def test_observer_detail_is_truncated(self):
        item = failure.classify_observer_sample(
            {"name": "long", "ok": False, "text_excerpt": "x" * 5000}
        )

        self.assertEqual(len(item.detail), 4096)


class ObserverLoadingAndSummary(unittest.TestCase):
    def test_load_observer_samples_filters_missing_invalid_and_wrong_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.jsonl"
            self.assertEqual(failure.load_observer_samples(missing), [])

            path = Path(tmp) / "observer.jsonl"
            path.write_text(
                "\n"
                "not-json\n"
                + json.dumps({"type": "other", "ok": False})
                + "\n"
                + json.dumps({"type": "observer_sample", "name": "status", "ok": True})
                + "\n"
            )

            self.assertEqual(
                failure.load_observer_samples(path),
                [{"type": "observer_sample", "name": "status", "ok": True}],
            )

    def test_summarize_classifications_counts_kind_and_severity_flags(self):
        items = [
            failure.FailureClassification("a", "bridge-timeout", "fail", "", "", ""),
            failure.FailureClassification("b", "bridge-timeout", "fail", "", "", ""),
            failure.FailureClassification("c", "policy-blocked", "deferred", "", "", ""),
        ]

        self.assertEqual(
            failure.summarize_classifications(items),
            {
                "count": 3,
                "by_kind": {"bridge-timeout": 2, "policy-blocked": 1},
                "by_severity": {"fail": 2, "deferred": 1},
                "has_failures": True,
                "has_deferred": True,
            },
        )

    def test_classify_mixed_soak_combines_sources_and_tracks_last_ok_sample(self):
        result = failure.classify_mixed_soak(
            events=[
                {"workload": "ok", "ok": True},
                {"workload": "blocked", "status": "blocked", "detail": "needs flag"},
            ],
            observer_samples=[
                {"name": "status", "ok": True, "cycle": 1, "seq": 2, "host_ts": 3.0, "duration_sec": 0.1},
                {"name": "status", "ok": False, "error": "timeout"},
                {"name": "status", "ok": True, "cycle": 2, "seq": 3, "host_ts": 4.0, "duration_sec": 0.2},
            ],
        )

        self.assertEqual(result["schema"], "a90-failure-classification-v182")
        self.assertEqual(result["summary"]["count"], 2)
        self.assertEqual(result["summary"]["by_kind"], {"policy-blocked": 1, "bridge-timeout": 1})
        self.assertEqual([item["kind"] for item in result["classifications"]], ["policy-blocked", "bridge-timeout"])
        self.assertEqual(
            result["last_ok_observer_sample"],
            {"cycle": 2, "seq": 3, "name": "status", "host_ts": 4.0, "duration_sec": 0.2},
        )


if __name__ == "__main__":
    unittest.main()
