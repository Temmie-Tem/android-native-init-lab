"""Static checks for V2991 dual touch doominput live handoff."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doominput_dual_touch_live_handoff_v2991.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doominput_dual_touch_live_handoff_v2991 as runner  # noqa: E402


class TestNativeDoominputDualTouchLiveHandoffV2991(unittest.TestCase):
    def test_runner_reuses_v2989_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2991"', text)
        self.assertIn("CANDIDATE_IMAGE = state_live.CANDIDATE_IMAGE", text)
        self.assertIn("CANDIDATE_TAG = state_live.CANDIDATE_TAG", text)
        self.assertIn("CANDIDATE_SHA256 = state_live.CANDIDATE_SHA256", text)
        self.assertIn('DEFAULT_EVENTS = ("event6", "event8")', text)

    def test_runner_preserves_flash_and_input_safety_boundaries(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_init_flash.py", text)
        self.assertIn("rollback to v2321 and verify selftest fail=0", text)
        self.assertIn("base.rollback_v2321", text)
        self.assertIn("inputcaps <event>", text)
        self.assertIn("doominput <event>", text)
        self.assertIn("no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)

    def test_parse_events_arg_requires_event_names(self) -> None:
        self.assertEqual(runner.parse_events_arg("event6,event8"), ("event6", "event8"))
        with self.assertRaises(Exception):
            runner.parse_events_arg("event6,/dev/input/event8")
        with self.assertRaises(Exception):
            runner.parse_events_arg("")

    def test_touch_sample_pass_requires_state_evidence_and_post_selftest(self) -> None:
        event_result = {
            "selected_is_touch": True,
            "inputcaps_rc": 0,
            "inputcaps_touch_ok": True,
            "doominput_rc": 0,
            "parsed": {"has_touch_state": True},
        }
        self.assertTrue(runner.touch_sample_pass(event_result, post_selftest_ok=True))
        event_result["parsed"] = {"has_touch_state": False}
        self.assertFalse(runner.touch_sample_pass(event_result, post_selftest_ok=True))
        event_result["parsed"] = {"has_touch_state": True}
        self.assertFalse(runner.touch_sample_pass(event_result, post_selftest_ok=False))

    def test_dry_run_contract_mentions_both_touch_events_and_state_requirement(self) -> None:
        args = Namespace(events=("event6", "event8"), count=32, timeout_ms=45000)
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
            "events": ["event6", "event8"],
            "timeout_ms": 45000,
            "count": 32,
        }
        payload = runner.dry_run_payload(args, state)
        self.assertEqual(payload["decision"], "v2991-doominput-dual-touch-dry-run")
        self.assertTrue(payload["ok"])
        self.assertIn("for each requested touch event: inputcaps <event>", payload["commands"])
        self.assertIn("require at least one doominput.state touch-state line", payload["commands"])

    def test_render_report_lists_per_event_results(self) -> None:
        result = {
            "decision": "v2991-doominput-dual-touch-touch-state-not-proven",
            "pass": False,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {"events": ["event6", "event8"]},
            "inputscan": {"touch_events": [{"event": "event6", "name": "sec_touchscreen", "class": "touch"}]},
            "event_results": [
                {
                    "event": "event6",
                    "selected_is_touch": True,
                    "inputcaps_touch_ok": True,
                    "doominput_rc": -110,
                    "parsed": {"doominput_event_count": 0, "doominput_state_count": 0, "touch_state_count": 0},
                    "pass": False,
                }
            ],
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V2991 DOOM Dual Touch State Touch Live", report)
        self.assertIn("`event6` selected_touch=`1`", report)
        self.assertIn("touch_states=`0`", report)


if __name__ == "__main__":
    unittest.main()
