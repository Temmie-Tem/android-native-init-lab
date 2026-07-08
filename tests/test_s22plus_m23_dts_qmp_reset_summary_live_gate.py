import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py")
DRAFT = Path("docs/operations/S22PLUS_M23_DTS_QMP_RESET_SUMMARY_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m23_dts_exact_qmp_reset_summary_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM23DtsQmpResetSummaryLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_capture_scope(self):
        missing = self.module.missing_policy_markers("S22+ M23 DTS-exact QMP/DWC3 native-init boot-only")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn("reset_summary/reset_klog post-rollback capture", missing)
        self.assertIn("/proc/reset_summary", missing)
        self.assertIn("manual download-mode rollback", missing)
        self.assertIn("no EUD sysfs write", missing)

    def test_expected_candidate_hashes_are_pinned(self):
        self.assertEqual(
            self.module.EXPECTED_M23_AP_SHA256,
            "558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8",
        )
        self.assertEqual(
            self.module.EXPECTED_M23_BOOT_SHA256,
            "277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e",
        )
        self.assertEqual(
            self.module.EXPECTED_M23_MODULE_LIST_SHA256,
            "a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349",
        )

    def test_reset_probe_collects_samsung_watchdog_surfaces(self):
        reset_files = set(self.module.collect_reset_reason.__globals__["RESET_FILES"])
        self.assertIn("/proc/reset_summary", reset_files)
        self.assertIn("/proc/reset_klog", reset_files)
        self.assertIn("/proc/reset_history", reset_files)
        self.assertIn("/proc/reset_tzlog", reset_files)
        self.assertIn("/proc/enhanced_boot_stat", reset_files)


if __name__ == "__main__":
    unittest.main()
