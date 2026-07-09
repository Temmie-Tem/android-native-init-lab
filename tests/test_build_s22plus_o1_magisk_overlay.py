import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation").resolve()
SCRIPT = SCRIPT_DIR / "build_s22plus_o1_magisk_overlay.py"
RC = Path("workspace/public/src/android/s22plus_o1_control.rc")
SERVICE = Path("workspace/public/src/android/s22plus_o1_service.sh")


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("build_s22plus_o1_magisk_overlay", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO1MagiskOverlayBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_real_sources_satisfy_bounded_runtime_contract(self):
        state = self.module.require_source_contract(RC, SERVICE)
        self.assertTrue(state["ready"])
        service = SERVICE.read_text(encoding="utf-8")
        self.assertLess(service.index("wait_stock_state running"), service.index(': >"$MARKER"'))
        self.assertIn("trap on_exit EXIT", service)
        self.assertIn("trap 'exit 128' HUP INT TERM", service)
        self.assertIn('STATUS="/dev/.s22plus_o1_status"', service)
        self.assertIn("result=pass\\ndaemon_rc=0\\nrestore_rc=0", service)

    def test_rc_cannot_stop_stock_service_before_wrapper_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = Path(tmp) / "bad.rc"
            rc.write_text(RC.read_text(encoding="utf-8") + "\n    stop DR-daemon\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "source contract failed"):
                self.module.require_source_contract(rc, SERVICE)

    def test_service_contract_rejects_persistent_or_sysfs_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Path(tmp) / "bad.sh"
            service.write_text(SERVICE.read_text(encoding="utf-8") + "\ncat /sys/kernel/debug/x\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "source contract failed"):
                self.module.require_source_contract(RC, service)

    def test_cpio_listing_parser_extracts_mode_and_name(self):
        listing = (
            "Loading cpio: [ramdisk.cpio]\n"
            "-rw-r--r--\t0\t0\t408 B\t0:0\toverlay.d/test.rc\n"
            "drwxr-x---\t0\t0\t0 B\t0:0\toverlay.d/sbin\n"
        )
        self.assertEqual(
            self.module.parse_cpio_listing(listing),
            {"overlay.d/test.rc": "-rw-r--r--", "overlay.d/sbin": "drwxr-x---"},
        )

    def test_manifest_validator_accepts_only_exact_boot_overlay_contract(self):
        manifest = {
            "target": self.module.EXPECTED_TARGET,
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
                "added_entries": self.module.INTENDED_ENTRIES,
                "replaced_entries": [],
                "listing_diff": {
                    "added": sorted(self.module.INTENDED_ENTRIES),
                    "removed": [],
                    "entry_modes": self.module.EXPECTED_ENTRY_MODES,
                },
            },
            "hashes": {
                "base_boot": self.module.EXPECTED_BASE_BOOT_SHA256,
                "original_magisk_init_before": self.module.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
                "original_magisk_init_after": self.module.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
            },
        }
        self.assertEqual(self.module.validate_manifest(manifest), [])
        manifest["ramdisk"]["listing_diff"]["removed"] = ["init"]
        self.assertIn("ramdisk-listing-removed-entry-present", self.module.validate_manifest(manifest))


if __name__ == "__main__":
    unittest.main()
