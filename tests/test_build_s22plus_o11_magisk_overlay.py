import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation").resolve()
SCRIPT = SCRIPT_DIR / "build_s22plus_o11_magisk_overlay.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("build_s22plus_o11_magisk_overlay", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO11MagiskOverlayBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_rc_delta_is_exactly_one_magisk_seclabel(self):
        delta = self.module.require_single_seclabel_delta(
            Path("workspace/public/src/android/s22plus_o1_control.rc"),
            Path("workspace/public/src/android/s22plus_o11_control.rc"),
        )
        self.assertEqual(delta["added_service_option"], "seclabel u:r:magisk:s0")
        self.assertFalse(delta["other_behavioral_delta"])

    def test_extra_rc_behavior_is_rejected(self):
        base = Path("workspace/public/src/android/s22plus_o1_control.rc")
        candidate = Path("workspace/public/src/android/s22plus_o11_control.rc")
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.rc"
            bad.write_text(candidate.read_text(encoding="utf-8") + "\non boot\n    setprop bad 1\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "only by the Magisk seclabel"):
                self.module.require_single_seclabel_delta(base, bad)

    def test_manifest_validator_rejects_missing_service_domain(self):
        manifest = {
            "schema": "s22plus_o11_magisk_overlay_build_v1",
            "run_id": self.module.RUN_ID,
            "variant": self.module.VARIANT,
            "target": self.module.o1.EXPECTED_TARGET,
            "safety": {
                "boot_only": True,
                "host_only_build": True,
                "live_flash_authorized": False,
                "base_is_known_booting_magisk_boot": True,
                "stock_first_stage_preserved": True,
                "stock_magisk_init_preserved": True,
                "kernel_preserved": True,
                "configfs_write": False,
                "sysfs_write": False,
                "module_insertions": False,
                "reboot_request": False,
                "persistent_partition_mount": False,
            },
            "tar_members": ["boot.img.lz4"],
            "ramdisk": {
                "added_entries": self.module.o1.INTENDED_ENTRIES,
                "replaced_entries": [],
                "listing_diff": {
                    "added": sorted(self.module.o1.INTENDED_ENTRIES),
                    "removed": [],
                    "entry_modes": self.module.o1.EXPECTED_ENTRY_MODES,
                },
            },
            "hashes": {
                "base_boot": self.module.o1.EXPECTED_BASE_BOOT_SHA256,
                "original_magisk_init_before": self.module.o1.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
                "original_magisk_init_after": self.module.o1.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
                "overlay_service": self.module.EXPECTED_SERVICE_SHA256,
                "o0_daemon": self.module.EXPECTED_DAEMON_SHA256,
                "kernel_before": self.module.EXPECTED_KERNEL_SHA256,
                "kernel_after": self.module.EXPECTED_KERNEL_SHA256,
            },
            "o11_delta": {
                "added_service_option": "seclabel u:r:magisk:s0",
                "other_behavioral_delta": False,
            },
        }
        self.assertIn("o11-service-seclabel-mismatch", self.module.validate_o11_manifest(manifest))


if __name__ == "__main__":
    unittest.main()
