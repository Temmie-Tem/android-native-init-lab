"""Static checks for V2988 decoded readinput live handoff."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_readinput_doom_decode_live_handoff_v2988.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_readinput_doom_decode_live_handoff_v2988 as runner  # noqa: E402


class TestNativeReadinputDoomDecodeLiveHandoffV2988(unittest.TestCase):
    def test_runner_targets_v2987_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2988"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.64"', text)
        self.assertIn('CANDIDATE_TAG = "v2987-readinput-doom-decode"', text)
        self.assertIn("boot_linux_v2987_readinput_doom_decode.img", text)
        self.assertIn("fc5d680be0b6575ea4650a4e84a2ee7f0620cc02693e77b5f4453f44f9ffad21", text)

    def test_runner_preserves_flash_and_input_safety_boundaries(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_init_flash.py", text)
        self.assertIn("rollback to v2321 and verify selftest fail=0", text)
        self.assertIn("base.rollback_v2321", text)
        self.assertIn("inputcaps <event>", text)
        self.assertIn("readinput <event>", text)
        self.assertIn("no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)

    def test_parse_decoded_readinput_extracts_touch_and_doom_roles(self) -> None:
        sample = "\n".join([
            "event 0: type=0x0003 code=0x0035 value=750",
            "event.decode 0: type=EV_ABS code=ABS_MT_POSITION_X role=touch_x value=750",
            "event 1: type=0x0003 code=0x0036 value=1000",
            "event.decode 1: type=EV_ABS code=ABS_MT_POSITION_Y role=touch_y value=1000",
            "event 2: type=0x0001 code=0x0011 value=1",
            "event.decode 2: type=EV_KEY code=KEY_W role=doom_forward value=1",
            "event 3: type=0x0000 code=0x0000 value=0",
            "event.decode 3: type=EV_SYN code=SYN_REPORT role=frame value=0",
        ])
        parsed = runner.parse_decoded_readinput(sample)
        self.assertEqual(parsed["event_count"], 4)
        self.assertEqual(parsed["decoded_event_count"], 4)
        self.assertEqual(parsed["touch_decoded_event_count"], 2)
        self.assertEqual(parsed["doom_decoded_event_count"], 1)
        self.assertEqual(parsed["doom_decoded_press_count"], 1)
        self.assertIn("touch_x", parsed["touch_roles"])
        self.assertIn("doom_forward", parsed["doom_roles"])
        self.assertTrue(parsed["has_touch_decoded_event"])
        self.assertTrue(parsed["has_doom_decoded_press"])

    def test_choose_event_auto_prefers_keyboard_then_touch_event6(self) -> None:
        scan = {
            "keyboard_events": [{"event": "event9", "name": "usbkbd", "class": "keyboard"}],
            "touch_events": [{"event": "event6", "name": "sec_touchscreen", "class": "touch"}],
            "events": [
                {"event": "event6", "name": "sec_touchscreen", "class": "touch"},
                {"event": "event9", "name": "usbkbd", "class": "keyboard"},
            ],
        }
        mode, selected = runner.choose_event(scan, None, "auto")
        self.assertEqual(mode, "keyboard")
        self.assertEqual(selected["event"], "event9")

        scan["keyboard_events"] = []
        mode, selected = runner.choose_event(scan, None, "auto")
        self.assertEqual(mode, "touch")
        self.assertEqual(selected["event"], "event6")

    def test_touch_and_keyboard_evaluators_require_decoded_role_evidence(self) -> None:
        common = {
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "inputscan_rc": 0,
            "inputcaps": {"rc": 0, "parsed": {}},
            "readinput_rc": 0,
            "candidate_selftest_after_readinput_fail0": True,
        }
        touch = {
            **common,
            "selected_mode": "touch",
            "selected_event": {"event": "event6", "class": "touch"},
            "inputcaps": {
                "rc": 0,
                "parsed": {
                    "has_event_header": True,
                    "decode": {"ev_abs": "1", "btn_touch": "1", "mt_x": "1", "mt_y": "1", "mt_tracking_id": "1"},
                },
            },
            "readinput": {"parsed": {"has_touch_decoded_event": True}},
        }
        keyboard = {
            **common,
            "selected_mode": "keyboard",
            "selected_event": {"event": "event9", "class": "keyboard"},
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
            "readinput": {"parsed": {"has_doom_decoded_press": True}},
        }
        self.assertTrue(runner.evaluate_result(touch))
        self.assertTrue(runner.evaluate_result(keyboard))
        touch["readinput"] = {"parsed": {"has_touch_decoded_event": False}}
        self.assertFalse(runner.evaluate_result(touch))

    def test_preflight_and_dry_run_contract_mentions_latest_decode_surface(self) -> None:
        args = Namespace(mode="auto", event=None, count=32, timeout_ms=45000)
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
            "requested_mode": "auto",
            "timeout_ms": 45000,
            "count": 32,
        }
        payload = runner.dry_run_payload(args, state)
        self.assertEqual(payload["decision"], "v2988-readinput-doom-decode-dry-run")
        self.assertTrue(payload["ok"])
        self.assertIn("require decoded event roles from event.decode lines", payload["commands"])


if __name__ == "__main__":
    unittest.main()
