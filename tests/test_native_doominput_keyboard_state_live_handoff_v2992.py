"""Static checks for V2992 USB-keyboard doominput state live handoff."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doominput_keyboard_state_live_handoff_v2992.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doominput_keyboard_state_live_handoff_v2992 as runner  # noqa: E402


class TestNativeDoominputKeyboardStateLiveHandoffV2992(unittest.TestCase):
    def test_runner_reuses_v2989_doominput_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2992"', text)
        self.assertIn("CANDIDATE_IMAGE = state_live.CANDIDATE_IMAGE", text)
        self.assertIn("CANDIDATE_TAG = state_live.CANDIDATE_TAG", text)
        self.assertIn("CANDIDATE_SHA256 = state_live.CANDIDATE_SHA256", text)
        self.assertEqual(runner.CANDIDATE_TAG, "v2989-doominput-state")
        self.assertTrue(str(runner.CANDIDATE_IMAGE).endswith("boot_linux_v2989_doominput_state.img"))

    def test_runner_preserves_flash_and_input_safety_boundaries(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_init_flash.py", text)
        self.assertIn("rollback to v2321 and verify selftest fail=0", text)
        self.assertIn("base.rollback_v2321", text)
        self.assertIn("inputcaps <keyboard-event>", text)
        self.assertIn("doominput <keyboard-event>", text)
        self.assertIn("no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)

    def test_choose_keyboard_event_prefers_keyboard_or_requested_event(self) -> None:
        scan = {
            "keyboard_events": [{"event": "event9", "name": "usbkbd", "class": "keyboard"}],
            "events": [
                {"event": "event6", "name": "sec_touchscreen", "class": "touch"},
                {"event": "event9", "name": "usbkbd", "class": "keyboard"},
            ],
        }
        self.assertEqual(runner.choose_keyboard_event(scan, None)["event"], "event9")
        self.assertEqual(runner.choose_keyboard_event(scan, "event9")["event"], "event9")
        self.assertEqual(runner.choose_keyboard_event(scan, "event6")["class"], "touch")

    def test_evaluator_requires_keyboard_caps_and_doom_button_state(self) -> None:
        result = {
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "inputscan_rc": 0,
            "selected_keyboard_event": {"event": "event9", "class": "keyboard"},
            "inputcaps": {
                "rc": 0,
                "parsed": {
                    "has_event_header": True,
                    "decode": {
                        "ev_key": "1",
                        "key_w": "1",
                        "key_a": "1",
                        "key_s": "1",
                        "key_d": "1",
                        "key_enter": "1",
                        "key_space": "1",
                        "key_esc": "1",
                    },
                },
            },
            "doominput_rc": 0,
            "doominput": {"parsed": {"has_doom_button_state": True}},
            "candidate_selftest_after_doominput_fail0": True,
        }
        self.assertTrue(runner.evaluate_result(result))
        result["doominput"] = {"parsed": {"has_doom_button_state": False}}
        self.assertFalse(runner.evaluate_result(result))
        result["doominput"] = {"parsed": {"has_doom_button_state": True}}
        result["selected_keyboard_event"] = {"event": "event6", "class": "touch"}
        self.assertFalse(runner.evaluate_result(result))

    def test_dry_run_contract_mentions_keyboard_state_surface(self) -> None:
        args = Namespace(event=None, count=32, timeout_ms=45000)
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
            "timeout_ms": 45000,
            "count": 32,
        }
        payload = runner.dry_run_payload(args, state)
        self.assertEqual(payload["decision"], "v2992-doominput-keyboard-state-dry-run")
        self.assertTrue(payload["ok"])
        self.assertIn("select keyboard-class event, or requested keyboard event", payload["commands"])
        self.assertIn("require doominput.state active DOOM button state lines", payload["commands"])

    def test_render_report_lists_keyboard_state_counts(self) -> None:
        result = {
            "decision": "v2992-doominput-keyboard-state-pass-before-rollback",
            "pass": True,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {},
            "inputscan": {"keyboard_candidates": 1, "keyboard_events": [{"event": "event9", "name": "usbkbd", "class": "keyboard"}]},
            "selected_keyboard_event": {"event": "event9", "name": "usbkbd", "class": "keyboard"},
            "inputcaps": {"rc": 0},
            "doominput_rc": 0,
            "doominput": {
                "timeout_ms": 45000,
                "parsed": {
                    "doominput_event_count": 1,
                    "doominput_state_count": 1,
                    "doom_button_state_count": 1,
                    "active_state_count": 1,
                    "states": [{"index": 0, "active": 1, "frame": 0, "forward": 1}],
                },
            },
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V2992 DOOM Input Keyboard State Live", report)
        self.assertIn("keyboard_candidates=`1`", report)
        self.assertIn("buttons=`forward`", report)


if __name__ == "__main__":
    unittest.main()
