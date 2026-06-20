"""Static checks for V2986 DOOM USB-keyboard live handoff."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_keyboard_live_handoff_v2986.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_keyboard_live_handoff_v2986 as runner  # noqa: E402


class TestNativeDoomKeyboardLiveHandoffV2986(unittest.TestCase):
    def test_runner_targets_v2985_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2986"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.63"', text)
        self.assertIn('CANDIDATE_TAG = "v2985-doom-keyboard-caps"', text)
        self.assertIn("boot_linux_v2985_doom_keyboard_caps.img", text)
        self.assertIn("4ffdb9b6078e99b3c5f40db42c0c9ef9d01f7936006be33943a65d9965343e54", text)

    def test_runner_preserves_live_flash_and_rollback_boundaries(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_init_flash.py", text)
        self.assertIn("rollback to v2321 and verify selftest fail=0", text)
        self.assertIn("base.rollback_v2321", text)
        self.assertIn("inputcaps <keyboard-event>", text)
        self.assertIn("readinput <keyboard-event>", text)
        self.assertIn("no input injection, no EVIOCGRAB, no keymap changes, no sysfs writes", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("ioctl(", text)
        self.assertNotIn("writefile", text)

    def test_keyboard_caps_contract_accepts_wasd_or_arrows_plus_actions(self) -> None:
        wasd = {
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
        }
        arrows = {
            "has_event_header": True,
            "decode": {
                "ev_key": "1",
                "key_up": "1",
                "key_down": "1",
                "key_left": "1",
                "key_right": "1",
                "key_enter": "1",
                "key_space": "1",
                "key_esc": "1",
            },
        }
        missing_action = {
            "has_event_header": True,
            "decode": {
                "ev_key": "1",
                "key_w": "1",
                "key_a": "1",
                "key_s": "1",
                "key_d": "1",
                "key_enter": "1",
                "key_space": "1",
                "key_esc": "0",
            },
        }
        self.assertTrue(runner.keyboard_caps_ok(wasd))
        self.assertTrue(runner.keyboard_caps_ok(arrows))
        self.assertFalse(runner.keyboard_caps_ok(missing_action))

    def test_parse_keyboard_readinput_extracts_doom_keys(self) -> None:
        sample = "\n".join([
            "event 0: type=0x0001 code=0x0011 value=1",
            "event 1: type=0x0000 code=0x0000 value=0",
            "event 2: type=0x0001 code=0x0011 value=0",
            "event 3: type=0x0001 code=0x0067 value=1",
        ])
        parsed = runner.parse_keyboard_readinput(sample)
        self.assertEqual(parsed["event_count"], 4)
        self.assertEqual(parsed["keyboard_key_event_count"], 3)
        self.assertEqual(parsed["doom_key_event_count"], 3)
        self.assertEqual(parsed["doom_key_press_count"], 2)
        self.assertTrue(parsed["has_doom_key_event"])
        self.assertEqual(parsed["doom_key_events"][0]["name"], "KEY_W")
        self.assertEqual(parsed["doom_key_events"][2]["name"], "KEY_UP")


if __name__ == "__main__":
    unittest.main()
