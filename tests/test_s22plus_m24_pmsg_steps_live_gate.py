import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py")
DRAFT = Path("docs/operations/S22PLUS_M24_PMSG_STEPS_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m24_pmsg_steps_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM24PmsgStepsLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_pmsg_scope(self):
        missing = self.module.missing_policy_markers("S22+ M24 pmsg-step DTS-exact QMP/DWC3 native-init boot-only")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn("pmsg/pstore/last_kmsg/reset-context post-rollback capture", missing)
        self.assertIn("/dev/pmsg0", missing)
        self.assertIn("A90_STEP:M24:", missing)
        self.assertIn("module_prepare", missing)
        self.assertIn("manual download-mode rollback", missing)

    def test_expected_candidate_hashes_are_pinned(self):
        self.assertEqual(
            self.module.EXPECTED_M24_AP_SHA256,
            "e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8",
        )
        self.assertEqual(
            self.module.EXPECTED_M24_BOOT_SHA256,
            "0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df",
        )
        self.assertEqual(
            self.module.EXPECTED_M24_INIT_SHA256,
            "4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341",
        )
        self.assertEqual(
            self.module.EXPECTED_M24_MODULE_LIST_SHA256,
            "a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349",
        )

    def test_reset_probe_collects_samsung_watchdog_surfaces(self):
        reset_files = set(self.module.collect_reset_reason.__globals__["RESET_FILES"])
        self.assertIn("/proc/reset_summary", reset_files)
        self.assertIn("/proc/reset_klog", reset_files)
        self.assertIn("/proc/reset_history", reset_files)
        self.assertIn("/proc/reset_tzlog", reset_files)
        self.assertIn("/proc/enhanced_boot_stat", reset_files)

    def test_summarize_pmsg_steps_extracts_ordered_unique_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            pstore = run_dir / "android_pstore"
            pstore.mkdir()
            (pstore / "post_m24_boot_rollback_pmsg-ramoops-0.bin").write_text(
                "noise\n"
                "A90_STEP:M24:pid1_start\n"
                "A90_STEP:M24:module_prepare index=28 name=phy-msm-ssusb-qmp.ko\n"
                "A90_STEP:M24:module_prepare index=28 name=phy-msm-ssusb-qmp.ko\n"
                "A90_STEP:M24:module_finit index=28 name=phy-msm-ssusb-qmp.ko\n",
                encoding="utf-8",
            )
            log_path = run_dir / "log.txt"
            steps = self.module.summarize_pmsg_steps(run_dir, log_path, "post_m24_boot_rollback")

        self.assertEqual(
            steps,
            [
                "A90_STEP:M24:pid1_start",
                "A90_STEP:M24:module_prepare index=28 name=phy-msm-ssusb-qmp.ko",
                "A90_STEP:M24:module_finit index=28 name=phy-msm-ssusb-qmp.ko",
            ],
        )


if __name__ == "__main__":
    unittest.main()
