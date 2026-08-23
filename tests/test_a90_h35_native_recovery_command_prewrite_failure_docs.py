"""Pin the closed H35 pre-write incident without reading private evidence."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md"
GOAL = ROOT / "GOAL_A90.md"


class A90H35NativeRecoveryCommandPrewriteFailureDocsTest(unittest.TestCase):
    def test_report_preserves_exact_no_write_and_closed_recovery(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        for token in (
            "RECOVERY_CLOSED_PREWRITE_ONLY_H35_UNPROVED",
            "bridge command outcome uncertain after one send for 'recovery': None",
            "`writeStarted=false`",
            "`bootWrittenReadbackExact=false`",
            "`systemReturnAttempted=false`",
            "H35 therefore received no boot opportunity",
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
            "RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED",
            "0.9.285 / v2321-usb-clean-identity-rodata",
            "candidate guard remains as the consumed no-replay marker",
            "serial_tcp_bridge.py` correctly requires an owner-private parent",
        ):
            self.assertIn(token, text)

    def test_report_binds_all_durable_record_receipts(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        for token in (
            "89f203221385146f8fc43356e6fecb14c3a87e6c36203f439e8bfa8a5fe37bfc",
            "19cc40642a5d24dd92723283b4b2f971bc2b1bbedb50f28ebaa218faa22eb4cf",
            "bf7c30cd5bbeec393726f842cd2c720fbea8d9247bbed52fa1c4c4b419d37eda",
            "912d72e01c83f8792f1dcd289b009820a05b5792eebd8f3510365bac1dcd55c1",
        ):
            self.assertIn(token, text)

    def test_goal_records_consumption_without_new_authority(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        flat = " ".join(goal.split())
        self.assertLessEqual(len(goal.splitlines()), 900)
        self.assertIn(REPORT.name, goal)
        self.assertIn("H35 is consumed and never replayed", flat)
        self.assertIn("H35 never booted and remains unproved", flat)
        self.assertIn("No H36 identity or authority exists", flat)


if __name__ == "__main__":
    unittest.main()
