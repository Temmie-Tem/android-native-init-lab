"""Static checks for V2995 DOOM input residual branch audit."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_input_residual_branch_audit_v2995.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_input_residual_branch_audit_v2995 as runner  # noqa: E402


class TestNativeDoomInputResidualBranchAuditV2995(unittest.TestCase):
    def test_runner_is_host_only_source_audit(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2995"', text)
        self.assertIn("v2995-doom-input-residual-branches-gated", text)
        self.assertIn("Host-only/source audit; no flash", text)
        self.assertIn("physical_buttons", text)
        self.assertNotIn("native_init_flash.py", text)
        self.assertNotIn("a90ctl", text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)

    def test_extract_switch_case_codes_finds_doom_and_excludes_physical_buttons(self) -> None:
        sample = """
static void doominput_apply_key(struct doominput_state *state,
                                unsigned int code,
                                int value) {
    switch (code) {
    case KEY_W:
    case KEY_UP:
        state->forward = true;
        break;
    case KEY_SPACE:
        state->use = true;
        break;
    default:
        break;
    }
}
"""
        codes = runner.extract_switch_case_codes(sample, "doominput_apply_key")
        self.assertEqual(codes, ["KEY_SPACE", "KEY_UP", "KEY_W"])
        self.assertFalse(set(codes).intersection(runner.DEVICE_BUTTON_CODES))

    def test_extract_menu_button_codes_finds_native_buttons(self) -> None:
        sample = """
unsigned int a90_input_button_mask_from_key(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return A90_INPUT_BUTTON_VOLUP;
    case KEY_VOLUMEDOWN:
        return A90_INPUT_BUTTON_VOLDOWN;
    case KEY_POWER:
        return A90_INPUT_BUTTON_POWER;
    default:
        return 0;
    }
}
"""
        self.assertEqual(
            runner.extract_menu_button_codes(sample),
            ["KEY_POWER", "KEY_VOLUMEDOWN", "KEY_VOLUMEUP"],
        )

    def test_v2991_summary_extracts_buttons_and_zero_touch(self) -> None:
        sample = {
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "inputscan": {
                "keyboard_candidates": 0,
                "keyboard_events": [],
                "touch_candidates": 2,
                "touch_events": [{"event": "event6", "name": "sec_touchscreen", "class": "touch"}],
                "button_candidates": 2,
                "button_events": [{"event": "event3", "name": "gpio_keys", "class": "buttons"}],
            },
            "event_results": [
                {"event": "event6", "doominput_rc": -110, "parsed": {"doominput_event_count": 0, "doominput_state_count": 0}},
                {"event": "event8", "doominput_rc": -110, "parsed": {"doominput_event_count": 0, "doominput_state_count": 0}},
            ],
        }
        summary = runner.v2991_input_summary(sample)
        self.assertEqual(summary["keyboard_candidates"], 0)
        self.assertEqual(summary["button_candidates"], 2)
        self.assertEqual(summary["zero_touch_events"], ["event6", "event8"])
        self.assertTrue(summary["rollback_clean"])

    def test_render_report_records_buttons_not_current_doom_fallback(self) -> None:
        payload = {
            "decision": runner.DECISION,
            "v2991": {
                "keyboard_candidates": 0,
                "keyboard_events": [],
                "touch_candidates": 2,
                "touch_events": [{"event": "event6", "name": "sec_touchscreen", "class": "touch"}],
                "button_candidates": 2,
                "button_events": [{"event": "event3", "name": "gpio_keys", "class": "buttons"}],
                "zero_touch_events": ["event6", "event8"],
                "rollback_clean": True,
            },
            "source": {
                "menu_button_codes": ["KEY_POWER", "KEY_VOLUMEDOWN", "KEY_VOLUMEUP"],
                "doominput_key_codes": ["BTN_TOUCH", "KEY_W", "KEY_A", "KEY_S", "KEY_D", "KEY_SPACE"],
                "device_buttons_mapped_by_doominput": [],
            },
            "prior_reports": {"v2993_touch_repeat_saturated": True, "v2994_keyboard_live_not_actionable": True},
            "branch_status": {
                "touch_repeat": "gated-new-touch-hypothesis-required",
                "usb_keyboard": "gated-a90-keyboard-evdev-required",
                "physical_buttons": "not-current-doom-fallback",
                "physical_buttons_viable_now": False,
            },
            "inputs": {
                "v2991_result": "v2991.json",
                "v2993_report": "v2993.md",
                "v2994_report": "v2994.md",
                "menu_apps_source": "40_menu_apps.inc.c",
                "input_source": "a90_input.c",
            },
            "next_action": "Do not flash another input live run.",
        }
        report = runner.render_report(payload)
        self.assertIn("Native Init V2995 DOOM Input Residual Branch Audit", report)
        self.assertIn("Physical button viable as current DOOM fallback: `0`", report)
        self.assertIn("not-current-doom-fallback", report)
        self.assertIn("## Host Validation", report)


if __name__ == "__main__":
    unittest.main()
