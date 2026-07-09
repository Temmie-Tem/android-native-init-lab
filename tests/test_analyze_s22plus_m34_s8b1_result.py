import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("analyze_s22plus_m34_s8b1_result", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AnalyzeS22PlusM34S8B1ResultTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def result_payload(self, result: str, rc: int = 0) -> dict:
        return {
            "schema": self.module.EXPECTED_SCHEMA,
            "target": self.module.EXPECTED_TARGET,
            "stage": "S8B1",
            "result": result,
            "rc": rc,
            "rollback_target": "magisk",
            "android_serial": "RFCT519XWGK",
            "candidate_ap_sha256": self.module.EXPECTED_M34_AP_SHA256,
            "candidate_boot_sha256": self.module.EXPECTED_M34_BOOT_SHA256,
            "candidate_init_sha256": self.module.EXPECTED_M34_INIT_SHA256,
            "base_boot_sha256": self.module.EXPECTED_M34_BASE_BOOT_SHA256,
        }

    def timeline_payload(self, names=None) -> dict:
        if names is None:
            names = self.module.REQUIRED_LIVE_PROOF_EVENTS
        return {
            "events": [
                {"name": name, "timestamp_utc": f"2026-07-09T00:00:{index:02d}Z"}
                for index, name in enumerate(names)
            ]
        }

    def test_hit_with_complete_timeline_advances_to_s8b2(self):
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit"),
            self.timeline_payload(),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_PROCEED_B2)
        self.assertTrue(analysis["ok_to_advance"])
        self.assertTrue(analysis["b1_observed"])
        self.assertTrue(analysis["b1_state"])
        self.assertEqual(analysis["next_stage"], "S8B2")
        self.assertEqual(analysis["next_probe"], "port0_partner_exists")
        self.assertTrue(analysis["magisk_baseline_restored"])
        self.assertTrue(analysis["ok_to_live_next_stage"])
        self.assertFalse(analysis["requires_magisk_baseline_restore"])

    def test_hit_with_stock_rollback_advances_b1_but_requires_magisk_baseline_restore(self):
        payload = self.result_payload("download-beacon-hit")
        payload["rollback_target"] = "stock"
        analysis = self.module.classify_result(payload, self.timeline_payload())

        self.assertEqual(analysis["decision"], self.module.DECISION_PROCEED_B2)
        self.assertTrue(analysis["ok_to_advance"])
        self.assertEqual(analysis["next_stage"], "S8B2")
        self.assertFalse(analysis["magisk_baseline_restored"])
        self.assertFalse(analysis["ok_to_live_next_stage"])
        self.assertTrue(analysis["requires_magisk_baseline_restore"])
        self.assertIn("restore/verify Magisk baseline", analysis["next_action"])

    def test_miss_with_complete_timeline_stops_before_b2(self):
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-miss-parked-manual-download-required"),
            self.timeline_payload(),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_B1_MISS_STOP)
        self.assertFalse(analysis["ok_to_advance"])
        self.assertTrue(analysis["b1_observed"])
        self.assertFalse(analysis["b1_state"])
        self.assertIsNone(analysis["next_stage"])

    def test_hit_without_complete_timeline_is_not_enough_to_advance(self):
        names = [name for name in self.module.REQUIRED_LIVE_PROOF_EVENTS if name != "rollback_boot_ready"]
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit"),
            self.timeline_payload(names),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_NO_PROOF)
        self.assertFalse(analysis["ok_to_advance"])
        self.assertIn("rollback_boot_ready", analysis["missing_required_live_events"])

    def test_hit_with_required_events_out_of_order_is_not_enough_to_advance(self):
        names = list(self.module.REQUIRED_LIVE_PROOF_EVENTS)
        rollback_boot_index = names.index("rollback_boot_ready")
        live_end_index = names.index("live_session_end")
        names[rollback_boot_index], names[live_end_index] = names[live_end_index], names[rollback_boot_index]
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit"),
            self.timeline_payload(names),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_NO_PROOF)
        self.assertFalse(analysis["ok_to_advance"])
        self.assertFalse(analysis["required_live_events_in_order"])
        self.assertEqual(analysis["missing_required_live_events"], [])

    def test_hit_with_unparsable_timeline_timestamp_is_not_enough_to_advance(self):
        timeline = self.timeline_payload()
        timeline["events"][0]["timestamp_utc"] = "not-a-timestampZ"
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit"),
            timeline,
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_NO_PROOF)
        self.assertFalse(analysis["ok_to_advance"])
        self.assertTrue(any("unparsable timestamp_utc" in item for item in analysis["timeline_errors"]))

    def test_hit_with_required_timestamps_out_of_order_is_not_enough_to_advance(self):
        timeline = self.timeline_payload()
        timeline["events"][3]["timestamp_utc"] = "2026-07-08T23:59:59Z"
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit"),
            timeline,
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_NO_PROOF)
        self.assertFalse(analysis["ok_to_advance"])
        self.assertTrue(analysis["required_live_events_in_order"])
        self.assertFalse(analysis["required_live_event_timestamps_monotonic"])

    def test_nonzero_rc_requires_recovery_even_if_b1_was_observed(self):
        analysis = self.module.classify_result(
            self.result_payload("download-beacon-hit", rc=4),
            self.timeline_payload(),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_RECOVERY_REQUIRED)
        self.assertTrue(analysis["b1_observed"])
        self.assertTrue(analysis["b1_state"])
        self.assertFalse(analysis["ok_to_advance"])

    def test_rollback_only_result_is_not_b1_proof(self):
        analysis = self.module.classify_result(
            self.result_payload("rollback-from-download-completed"),
            self.timeline_payload(),
        )

        self.assertEqual(analysis["decision"], self.module.DECISION_ROLLBACK_ONLY)
        self.assertFalse(analysis["b1_observed"])
        self.assertFalse(analysis["ok_to_advance"])

    def test_hash_mismatch_invalidates_evidence(self):
        payload = self.result_payload("download-beacon-hit")
        payload["candidate_ap_sha256"] = "0" * 64
        analysis = self.module.classify_result(payload, self.timeline_payload())

        self.assertEqual(analysis["decision"], self.module.DECISION_INVALID)
        self.assertTrue(any("candidate_ap_sha256 mismatch" in item for item in analysis["errors"]))

    def test_cli_write_report_writes_analysis_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            result_json = run_dir / "result.json"
            timeline_json = run_dir / "timeline.json"
            result_json.write_text(json.dumps(self.result_payload("download-beacon-hit")), encoding="utf-8")
            timeline_json.write_text(json.dumps(self.timeline_payload()), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                rc = self.module.main([str(result_json), "--write-report"])

            self.assertEqual(rc, 0)
            report = json.loads((run_dir / "s22plus_m34_s8b1_result_analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(report["decision"], self.module.DECISION_PROCEED_B2)
            self.assertEqual(report["result_json"], str(result_json))
            self.assertEqual(report["timeline_json"], str(timeline_json))


if __name__ == "__main__":
    unittest.main()
