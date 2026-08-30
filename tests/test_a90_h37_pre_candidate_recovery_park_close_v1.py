"""Host-only source constraints for the fixed H37 park closer."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h37_pre_candidate_recovery_park_close_v1.py"


class H37ParkCloseTest(unittest.TestCase):
    def test_fixed_scope_and_no_effect_primitives(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "a90-h37-f1-20260829-01"', text)
        self.assertIn("_require_candidate_guard_absent", text)
        self.assertIn("_release_active_guard", text)
        self.assertIn("read_result", text)
        self.assertIn("next_log_dir", text)
        self.assertNotIn("backend.flash", text)
        self.assertNotIn("native_init_flash", text)
        self.assertNotIn("/usr/bin/adb", text)
        self.assertNotIn("reboot", text.lower())
        self.assertNotIn("while True", text)

    def test_exact_consumed_prefix_is_pinned(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for name in ("00-prepared.json", "10-approved.json", "11-recovery-transition-intent.json", "13-recovery-transition-parked.json"):
            self.assertIn(name, text)
        self.assertIn('"candidateBytesTransferred": 0', text)
        self.assertIn('"rollbackBytesTransferred": 0', text)


if __name__ == "__main__":
    unittest.main()
