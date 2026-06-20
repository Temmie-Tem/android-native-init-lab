"""Static checks for V2997 physical-button doominput proxy live handoff."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doominput_button_proxy_live_handoff_v2997.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doominput_button_proxy_live_handoff_v2997 as runner  # noqa: E402


class TestNativeDoominputButtonProxyLiveHandoffV2997(unittest.TestCase):
    def test_runner_targets_v2996_button_proxy_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2997"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.66"', text)
        self.assertIn('CANDIDATE_TAG = "v2996-doominput-button-proxy"', text)
        self.assertIn("boot_linux_v2996_doominput_button_proxy.img", text)
        self.assertIn("1509ce74701f2f8d30e7a5ee924b108ca9bb60debed8afab5f9352643e2a4a75", text)
        self.assertEqual(runner.DEFAULT_EVENTS, ("event3", "event0"))

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
        self.assertEqual(runner.parse_events_arg("event3,event0"), ("event3", "event0"))
        with self.assertRaises(Exception):
            runner.parse_events_arg("event3,/dev/input/event0")
        with self.assertRaises(Exception):
            runner.parse_events_arg("")

    def test_button_proxy_caps_ok_accepts_power_or_volume_keys(self) -> None:
        base_caps = {"has_event_header": True, "decode": {"ev_key": "1"}}
        for key in ("key_volup", "key_voldown", "key_power"):
            caps = {"has_event_header": True, "decode": {"ev_key": "1", key: "1"}}
            self.assertTrue(runner.button_proxy_caps_ok(caps))
        self.assertFalse(runner.button_proxy_caps_ok(base_caps))
        self.assertFalse(runner.button_proxy_caps_ok({"has_event_header": True, "decode": {"ev_key": "0", "key_power": "1"}}))

    def test_proxy_state_fields_track_v2996_mapped_states(self) -> None:
        parsed = {
            "states": [
                {"forward": 1, "back": 0, "fire": 0},
                {"forward": 0, "back": 1, "fire": 1},
            ]
        }
        self.assertEqual(runner.proxy_state_fields(parsed), ["back", "fire", "forward"])
        self.assertTrue(runner.has_proxy_button_state(parsed))
        self.assertFalse(runner.has_proxy_button_state({"states": [{"left": 1, "right": 1}]}))

    def test_button_sample_pass_requires_button_caps_state_and_post_selftest(self) -> None:
        event_result = {
            "selected_is_button": True,
            "inputcaps_rc": 0,
            "inputcaps_button_ok": True,
            "doominput_rc": 0,
            "parsed": {"states": [{"forward": 1, "active": 1}]},
        }
        self.assertTrue(runner.button_sample_pass(event_result, post_selftest_ok=True))
        event_result["parsed"] = {"states": [{"left": 1, "active": 1}]}
        self.assertFalse(runner.button_sample_pass(event_result, post_selftest_ok=True))
        event_result["parsed"] = {"states": [{"fire": 1, "active": 1}]}
        self.assertFalse(runner.button_sample_pass(event_result, post_selftest_ok=False))

    def test_dry_run_contract_mentions_button_proxy_requirement(self) -> None:
        args = Namespace(events=("event3", "event0"), count=16, timeout_ms=45000)
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
            "events": ["event3", "event0"],
            "timeout_ms": 45000,
            "count": 16,
        }
        payload = runner.dry_run_payload(args, state)
        self.assertEqual(payload["decision"], "v2997-doominput-button-proxy-dry-run")
        self.assertTrue(payload["ok"])
        self.assertTrue(any("operator presses VOLUMEUP/VOLUMEDOWN/POWER" in item for item in payload["commands"]))
        self.assertIn("require doominput.state forward/back/fire proxy state lines", payload["commands"])

    def test_render_report_lists_button_proxy_counts(self) -> None:
        result = {
            "decision": "v2997-doominput-button-proxy-state-pass-before-rollback",
            "pass": True,
            "live_executed": True,
            "out_dir": "workspace/private/runs/input/example",
            "preflight": {"events": ["event3", "event0"]},
            "inputscan": {"button_candidates": 2, "button_events": [{"event": "event3", "name": "gpio_keys", "class": "buttons"}]},
            "event_results": [
                {
                    "event": "event3",
                    "selected_is_button": True,
                    "inputcaps_button_ok": True,
                    "doominput_rc": 0,
                    "parsed": {
                        "doominput_event_count": 1,
                        "doominput_state_count": 1,
                        "active_state_count": 1,
                        "states": [{"forward": 1, "active": 1}],
                    },
                    "pass": True,
                }
            ],
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V2997 DOOM Input Button Proxy Live", report)
        self.assertIn("button_candidates=`2`", report)
        self.assertIn("proxy_fields=`forward`", report)
        self.assertIn("not a final DOOM control scheme", report)


if __name__ == "__main__":
    unittest.main()
