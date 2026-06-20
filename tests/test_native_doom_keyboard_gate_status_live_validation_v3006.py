"""Static checks for V3006 DOOM keyboard-gate status live validation wrapper."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_keyboard_gate_status_live_validation_v3006.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_keyboard_gate_status_live_validation_v3006 as runner  # noqa: E402


class TestNativeDoomKeyboardGateStatusLiveValidationV3006(unittest.TestCase):
    def test_wrapper_targets_v3005_status_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3006"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.69"', text)
        self.assertIn('CANDIDATE_TAG = "v3005-doom-keyboard-gate-status"', text)
        self.assertIn("boot_linux_v3005_doom_keyboard_gate_status.img", text)
        self.assertIn("51efe32f28cfbeae62c5b5d6ccc9b21e65718030ff4bbfe64228f9a155ece622", text)
        self.assertTrue(str(runner.report_path()).endswith("NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md"))

    def test_configure_base_relabels_v3001_runner(self) -> None:
        runner.configure_base()
        self.assertEqual(runner.v3001.RUN_ID, "V3006")
        self.assertEqual(runner.v3001.CANDIDATE_TAG, "v3005-doom-keyboard-gate-status")
        self.assertEqual(runner.v3001.CANDIDATE_SHA256, runner.CANDIDATE_SHA256)
        self.assertIn("video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate", runner.v3001.DOOM_STATUS_MARKERS)

    def test_dry_run_contract_mentions_keyboard_gate_not_mux_sample(self) -> None:
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
        }
        payload = runner.dry_run_payload(Namespace(), state)
        joined = "\n".join(payload["commands"])
        self.assertEqual(payload["decision"], "v3006-doom-keyboard-gate-status-dry-run")
        self.assertTrue(payload["ok"])
        self.assertIn("v3004 USB-keyboard/OTG gate markers", joined)
        self.assertNotIn("doominputmux event3,event0", joined)

    def test_marker_contract_requires_current_v3005_status_strings(self) -> None:
        doom_text = "\n".join(runner.DOOM_STATUS_MARKERS)
        self.assertIn("video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat", doom_text)
        self.assertIn("video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate", doom_text)
        self.assertIn("video.demo.input.hardware_gate=usb-keyboard-otg", doom_text)
        self.assertIn("video.demo.input.command=doominput <keyboard-event> 32 60000", doom_text)
        self.assertNotIn("video.demo.input.button_mux=v2999-doominput-mux-live", doom_text)

    def test_render_report_relabels_to_v3006_and_keeps_status_only_boundary(self) -> None:
        result = {
            "decision": "v3006-doom-keyboard-gate-status-dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": {
                "candidate": {"sha256_ok": True},
                "rollback": {"sha256_ok": True},
                "fallback_v2237": {"sha256_ok": True},
                "fallback_v48": {"exists": True},
                "flash_helper": {"exists": True},
                "operator_prerequisite": "none; status-only live validation does not require button/touch input",
            },
            "preflight_ok": True,
            "rollback_attempted": False,
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V3006 DOOM Keyboard Gate Status Live Handoff Dry Run", report)
        self.assertIn("v3006-doom-keyboard-gate-status-dry-run", report)
        self.assertIn("V3005 Marker Context", report)
        self.assertIn("no `doominput`, no evdev sample", report)
        self.assertIn("tests.test_native_doom_keyboard_gate_status_live_validation_v3006", report)
        self.assertNotIn("Native Init V3001 DOOM Status Stub", report)


if __name__ == "__main__":
    unittest.main()
