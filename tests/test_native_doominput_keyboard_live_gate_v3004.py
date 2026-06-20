"""Static checks for V3004 USB-keyboard/OTG DOOM input live gate."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doominput_keyboard_live_gate_v3004.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doominput_keyboard_live_gate_v3004 as runner  # noqa: E402


class TestNativeDoominputKeyboardLiveGateV3004(unittest.TestCase):
    def test_wrapper_identity_and_report_path(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3004"', text)
        self.assertIn('BUILD_TAG = "v3004-doominput-keyboard-live-gate"', text)
        self.assertIn('DECISION_PREFIX = "v3004-doominput-keyboard"', text)
        self.assertIn("NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md", text)
        self.assertTrue(str(runner.report_path()).endswith("NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md"))

    def test_wrapper_reuses_v2992_candidate_and_safety_logic(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_doominput_keyboard_state_live_handoff_v2992", text)
        self.assertIn("reuses the V2992", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)

    def test_configure_base_sets_v3004_identity_without_changing_candidate(self) -> None:
        runner.configure_base()
        self.assertEqual(runner.v2992.RUN_ID, "V3004")
        self.assertEqual(runner.v2992.BUILD_TAG, "v3004-doominput-keyboard-live-gate")
        self.assertEqual(runner.v2992.DECISION_PREFIX, "v3004-doominput-keyboard")
        self.assertEqual(runner.v2992.DEFAULT_TIMEOUT_MS, 60000)
        self.assertEqual(runner.v2992.CANDIDATE_TAG, "v2989-doominput-state")

    def test_render_report_relabels_to_v3004_and_adds_gate_context(self) -> None:
        result = {
            "decision": "v3004-doominput-keyboard-dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {},
            "preflight_ok": True,
            "rollback_attempted": False,
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V3004 DOOM Input Keyboard State Live Handoff Dry Run", report)
        self.assertIn("v3004-doominput-keyboard-dry-run", report)
        self.assertIn("V3003 recorded the current frontier as hardware-stimulus-gated", report)
        self.assertIn("USB keyboard/OTG live path", report)
        self.assertIn("Host Validation", report)
        self.assertNotIn("Native Init V2992 DOOM Input", report)

    def test_render_report_records_live_non_pass_attempt(self) -> None:
        result = {
            "decision": "v3004-doominput-keyboard-not-proven",
            "pass": False,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {},
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
        }
        report = runner.render_report(result)
        self.assertIn("RECORDED", report)
        self.assertIn("no keyboard-state pass", report)


if __name__ == "__main__":
    unittest.main()
