"""Static checks for V2980 full-inputscan readinput touch handoff."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "workspace/public/src/scripts/revalidation/native_readinput_touch_fullscan_live_handoff_v2980.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2980_READINPUT_TOUCH_FULLSCAN_2026-06-20.md"


def load_module():
    spec = importlib.util.spec_from_file_location("v2980", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNativeReadinputTouchFullscanLiveHandoffV2980(unittest.TestCase):
    def test_runner_identity_and_reuse(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2980"', text)
        self.assertIn('BUILD_TAG = "v2980-readinput-touch-fullscan"', text)
        self.assertIn('CANDIDATE_IMAGE = inputscan_live.CANDIDATE_IMAGE', text)
        self.assertIn('ROLLBACK_IMAGE = inputscan_live.ROLLBACK_IMAGE', text)

    def test_runner_uses_full_inputscan_not_single_event(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"candidate-inputscan-full-before-readinput", ["inputscan"]', text)
        self.assertIn('inputscan_selected_event', text)
        self.assertNotIn('["inputscan", args.event]', text)
        self.assertIn('sock.sendall(b"q\\n")', text)

    def test_scope_excludes_active_mutation(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('sendevent', text)
        self.assertNotIn('input keyevent', text)
        self.assertNotIn('setkey', text)
        self.assertNotIn('audio play', text)
        self.assertNotIn('wifi scan', text)
        self.assertNotIn('setenforce', text)

    def test_parse_readinput_detects_touch_signal(self) -> None:
        module = load_module()
        parsed = module.parse_readinput(
            "event 0: type=0x0003 code=0x0035 value=100\n"
            "event 1: type=0x0003 code=0x0036 value=200\n"
            "event 2: type=0x0000 code=0x0000 value=0\n"
        )
        self.assertEqual(parsed["touch_abs_event_count"], 2)
        self.assertTrue(parsed["has_touch_signal"])

    def test_dry_run_report_documents_fullscan(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn('v2980-readinput-dry-run', text)
        self.assertIn('Full `inputscan`', text)
        self.assertIn('q` and records a cancelled run', text)


if __name__ == "__main__":
    unittest.main()
