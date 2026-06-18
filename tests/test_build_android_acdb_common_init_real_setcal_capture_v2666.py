import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "workspace/public/src/scripts/revalidation/build_android_acdb_common_init_real_setcal_capture_v2666.py"
spec = importlib.util.spec_from_file_location("v2666", MODULE)
v2666 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = v2666
spec.loader.exec_module(v2666)


class BuildInitRealSetcalCaptureV2666(unittest.TestCase):
    def test_source_state_is_init_real_and_measurement_safe(self):
        args = v2666.parse_args([])
        state = v2666.source_state(args)
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])
        required = state["required"]
        self.assertTrue(required["helper_does_not_import_send_audio_cal_v5"])
        self.assertTrue(required["helper_skips_send_audio_cal_v5"])
        self.assertTrue(required["phase_hook_init_real_event_path_v2666"])
        self.assertTrue(required["phase_hook_calls_real_common_during_init"])
        self.assertTrue(required["phase_hook_exits_after_init_real"])
        self.assertTrue(required["phase_hook_fails_closed_on_patch_failure"])
        self.assertTrue(required["v2663_common_path_targets_ok"])
        prohibited = state["prohibited"]
        self.assertFalse(prohibited["helper_calls_send_audio_cal_v5"])
        self.assertFalse(prohibited["combined_native_speaker_write"])

    def test_payload_contract_names_target_cals_and_removed_send_v5(self):
        args = v2666.parse_args([])
        payload = v2666.make_payload(args)
        self.assertTrue(payload["ok"])
        contract = payload["capture_contract"]
        self.assertEqual(contract["target_cal_types"], [10, 14, 24])
        self.assertIn("send_audio_cal_v5", contract["removed_from_v2659"])
        self.assertIn("init-time common hook", contract["call_order"])
        self.assertIn("exit_group(0)", contract["call_order"])
        self.assertNotIn("send_audio_cal_v5 ->", contract["call_order"])

    def test_report_mentions_init_real_next_unit(self):
        args = v2666.parse_args([])
        payload = v2666.make_payload(args)
        report_path = Path("/tmp/v2666-report.md")
        v2666.write_report(payload, report_path)
        text = report_path.read_text(encoding="utf-8")
        self.assertIn("init-time common hook", text)
        self.assertIn("no `send_audio_cal_v5`", text)
        self.assertIn("cal_types `10`, `14`, and `24`", text)


if __name__ == "__main__":
    unittest.main()
