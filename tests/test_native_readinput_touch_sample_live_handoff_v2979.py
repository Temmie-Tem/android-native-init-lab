"""Static checks for V2979 bounded readinput touch sample handoff."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "workspace/public/src/scripts/revalidation/native_readinput_touch_sample_live_handoff_v2979.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2979_READINPUT_TOUCH_SAMPLE_2026-06-20.md"


def load_module():
    spec = importlib.util.spec_from_file_location("v2979", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNativeReadinputTouchSampleLiveHandoffV2979(unittest.TestCase):
    def test_runner_reuses_v2977_candidate_and_v2321_rollback(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2979"', text)
        self.assertIn('CANDIDATE_IMAGE = inputscan_live.CANDIDATE_IMAGE', text)
        self.assertIn('ROLLBACK_IMAGE = inputscan_live.ROLLBACK_IMAGE', text)
        self.assertIn('rollback to v2321 and verify selftest fail=0', text)

    def test_runner_has_bounded_cancel_path(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('sock.sendall(b"q\\n")', text)
        self.assertIn('sample_timeout', text)
        self.assertIn('cancel_timeout', text)
        self.assertIn('readinput evdev read-only sample only', text)
        self.assertNotIn('sendevent', text)
        self.assertNotIn('input keyevent', text)
        self.assertNotIn('setkey', text)
        self.assertNotIn('audio play', text)
        self.assertNotIn('wifi scan', text)
        self.assertNotIn('setenforce', text)

    def test_parse_readinput_detects_touch_abs(self) -> None:
        module = load_module()
        parsed = module.parse_readinput("""
readinput: waiting on /dev/input/event6 (16 events), q/Ctrl-C cancels
event 0: type=0x0003 code=0x0035 value=612
event 1: type=0x0003 code=0x0036 value=1344
event 2: type=0x0000 code=0x0000 value=0
A90P1 END seq=1 cmd=readinput rc=0 errno=0 duration_ms=1 flags=0x0 status=ok
""")
        self.assertEqual(parsed["event_count"], 3)
        self.assertEqual(parsed["abs_event_count"], 2)
        self.assertEqual(parsed["syn_event_count"], 1)
        self.assertTrue(parsed["has_touch_signal"])
        self.assertEqual(parsed["touch_abs_event_count"], 2)

    def test_parse_readinput_detects_btn_touch(self) -> None:
        module = load_module()
        parsed = module.parse_readinput("event 0: type=0x0001 code=0x014a value=1\n")
        self.assertTrue(parsed["has_touch_signal"])
        self.assertEqual(parsed["btn_touch_event_count"], 1)

    def test_dry_run_report_documents_human_touch_gate(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn('v2979-readinput-dry-run', text)
        self.assertIn('readinput', text)
        self.assertIn('q` and records a cancelled run', text)
        self.assertIn('no input injection', text)


if __name__ == "__main__":
    unittest.main()
