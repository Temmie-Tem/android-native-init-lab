"""Static checks for V2978 inputscan live handoff."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "workspace/public/src/scripts/revalidation/native_inputscan_live_handoff_v2978.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2978_INPUTSCAN_LIVE_2026-06-20.md"


def load_module():
    spec = importlib.util.spec_from_file_location("v2978", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNativeInputscanLiveHandoffV2978(unittest.TestCase):
    def test_runner_uses_v2977_candidate_and_v2321_rollback(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2978"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.60"', text)
        self.assertIn('CANDIDATE_TAG = "v2977-inputscan-summary"', text)
        self.assertIn('boot_linux_v2977_inputscan_summary.img', text)
        self.assertIn('ROLLBACK_IMAGE = av_live.ROLLBACK_IMAGE', text)
        self.assertIn('rollback v2321 and verify selftest fail=0', text)

    def test_runner_scope_is_inventory_only(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('["inputscan"]', text)
        self.assertNotIn('["readinput"', text)
        self.assertNotIn('audio play', text)
        self.assertNotIn('wifi scan', text)
        self.assertNotIn('setenforce', text)
        self.assertIn('no readinput sample, no input injection, no keymap changes', text)

    def test_parse_inputscan_extracts_candidates(self) -> None:
        module = load_module()
        parsed = module.parse_inputscan("""
inputscan.event=event6 name=sec_touchscreen dev=13:70 node=/dev/input/event6 class=touch
  ev.key=1 ev.abs=1 btn_touch=1 abs_xy=0 mt_xy=1 key_power=0 key_volup=0 key_voldown=0 key_wasd=0 key_enter_space_esc=0
inputscan.event=event9 name=usb-keyboard dev=13:73 node=/dev/input/event9 class=keyboard
  ev.key=1 ev.abs=0 btn_touch=0 abs_xy=0 mt_xy=0 key_power=0 key_volup=0 key_voldown=0 key_wasd=1 key_enter_space_esc=1
inputscan.summary events=2 nodes=2 touch_candidates=1 keyboard_candidates=1 button_candidates=0
""")
        self.assertTrue(parsed["summary_found"])
        self.assertEqual(parsed["event_count"], 2)
        self.assertEqual(parsed["touch_candidates"], 1)
        self.assertEqual(parsed["keyboard_candidates"], 1)
        self.assertEqual(parsed["touch_events"][0]["name"], "sec_touchscreen")
        self.assertEqual(parsed["keyboard_events"][0]["event"], "event9")
        self.assertTrue(parsed["touch_event_count_matches"])
        self.assertTrue(parsed["keyboard_event_count_matches"])

    def test_parse_inputscan_normalizes_class_tokens(self) -> None:
        module = load_module()
        parsed = module.parse_inputscan(
            "inputscan.event=event8 name=sec_touchpad dev=13:72 node=/dev/input/event8 class=touch,buttons\r\n"
            "inputscan.summary events=1 nodes=1 touch_candidates=1 keyboard_candidates=0 button_candidates=1\r\n"
        )
        self.assertEqual(parsed["events"][0]["class"], "touch,buttons")
        self.assertEqual(parsed["touch_events"][0]["event"], "event8")
        self.assertEqual(parsed["button_events"][0]["event"], "event8")
        self.assertTrue(parsed["touch_event_count_matches"])
        self.assertTrue(parsed["button_event_count_matches"])

    def test_reclassify_existing_result_without_device_action(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            stdout = run_dir / "06_candidate-inputscan.txt"
            stdout.write_text(
                "inputscan.event=event6 name=sec_touchscreen dev=13:70 node=/dev/input/event6 class=touch\n"
                "inputscan.event=event0 name=qpnp_pon dev=13:64 node=/dev/input/event0 class=buttons\n"
                "inputscan.summary events=2 nodes=2 touch_candidates=1 keyboard_candidates=0 button_candidates=1\n",
                encoding="utf-8",
            )
            result = {
                "decision": "v2978-inputscan-marker-failed",
                "pass": False,
                "error_type": "RuntimeError",
                "error": "old parser failure",
                "out_dir": "workspace/private/runs/input/test",
                "candidate_version_ok": True,
                "candidate_status_ok": True,
                "candidate_selftest_fail0": True,
                "candidate_help_has_inputscan": True,
                "inputscan_rc": 0,
                "inputscan_stdout_path": str(stdout),
                "candidate_selftest_after_inputscan_fail0": True,
                "rollback_attempted": True,
                "rollback_step_ok": True,
                "rollback_version_ok": True,
                "rollback_selftest_fail0": True,
            }
            (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
            original_report = module.REPORT_PATH
            module.REPORT_PATH = run_dir / "report.md"
            try:
                reclassified = module.reclassify_run(run_dir)
            finally:
                module.REPORT_PATH = original_report
        self.assertTrue(reclassified["pass"])
        self.assertEqual(reclassified["decision"], "v2978-inputscan-live-pass-before-rollback")
        self.assertTrue(reclassified["posthoc_reclassified"])
        self.assertNotIn("error", reclassified)

    def test_report_documents_deferred_human_touch_sample(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn('V2978 validates the V2977 `inputscan` command', text)
        self.assertIn('readinput <event> 1', text)
        self.assertIn('No input stream read', text)


if __name__ == "__main__":
    unittest.main()
