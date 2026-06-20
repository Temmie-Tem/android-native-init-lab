"""Static checks for V3002 DOOM input mux live validation wrapper."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doominput_mux_live_validation_v3002.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doominput_mux_live_validation_v3002 as runner  # noqa: E402


class TestNativeDoominputMuxLiveValidationV3002(unittest.TestCase):
    def test_wrapper_identity_and_report_path(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3002"', text)
        self.assertIn('BUILD_TAG = "v3002-doominput-mux-live"', text)
        self.assertIn('DECISION_PREFIX = "v3002-doominput-mux"', text)
        self.assertIn("NATIVE_INIT_V3002_DOOMINPUT_MUX_LIVE_2026-06-20.md", text)
        self.assertTrue(str(runner.report_path()).endswith("NATIVE_INIT_V3002_DOOMINPUT_MUX_LIVE_2026-06-20.md"))

    def test_wrapper_keeps_v2998_candidate_and_v2999_safety_logic(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_doominput_mux_live_handoff_v2999", text)
        self.assertIn("This reuses the V2999 mux runner", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)

    def test_render_report_relabels_to_v3002_and_adds_live_line(self) -> None:
        result = {
            "decision": "v3002-doominput-mux-state-pass-before-rollback",
            "pass": True,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {"events": ["event3", "event0"]},
            "inputscan": {
                "button_candidates": 2,
                "button_events": [{"event": "event3", "name": "gpio_keys", "class": "buttons"}],
            },
            "event_results": [{"event": "event3", "selected_is_button": True, "inputcaps_button_ok": True, "inputcaps_rc": 0}],
            "doominputmux_rc": 0,
            "doominputmux": {
                "timeout_ms": 60000,
                "parsed": {
                    "doominputmux_event_count": 2,
                    "doominputmux_state_count": 2,
                    "active_state_count": 1,
                    "proxy_state_count": 1,
                    "max_frame": 0,
                    "source_names": ["event0", "event3"],
                    "states": [{"forward": 1, "active": 1}],
                },
            },
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "candidate_selftest_after_doominputmux_fail0": True,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V3002 DOOM Input Mux Live", report)
        self.assertIn("v3002-doominput-mux-state-pass-before-rollback", report)
        self.assertIn("V3002 runs live validation", report)
        self.assertIn("native_doominput_mux_live_validation_v3002.py --live --events event3,event0 --count 24 --timeout-ms 60000", report)
        self.assertIn("proxy state captured", report)
        self.assertNotIn("Native Init V2999 DOOM Input", report)

    def test_render_report_records_non_pass_live_attempt(self) -> None:
        result = {
            "decision": "v3002-doominput-mux-state-not-proven",
            "pass": False,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {"events": ["event3", "event0"]},
            "event_results": [],
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
        }
        report = runner.render_report(result)
        self.assertIn("RECORDED", report)
        self.assertIn("no proxy-state pass", report)


if __name__ == "__main__":
    unittest.main()
