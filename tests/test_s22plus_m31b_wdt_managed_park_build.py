import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m31b_wdt_managed_park.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_m31b_wdt_managed_park.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m31b_wdt_managed_park_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m31b_wdt_managed_park", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM31BWdtManagedParkBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_watchdog_closure_is_dep_ordered_and_minimal(self):
        dep_map = {
            "gh_virt_wdt.ko": ["qcom_wdt_core.ko", "qcom-scm.ko", "minidump.ko", "smem.ko"],
            "qcom_wdt_core.ko": ["qcom-scm.ko", "minidump.ko", "smem.ko"],
            "qcom-scm.ko": [],
            "minidump.ko": ["smem.ko"],
            "smem.ko": [],
        }
        recovery = ["gh_virt_wdt.ko", "qcom_wdt_core.ko", "minidump.ko", "qcom-scm.ko", "smem.ko"]
        closure = self.module.watchdog_closure(dep_map=dep_map, recovery_basenames=recovery)

        self.assertEqual(closure["modules"], self.module.EXPECTED_WDT_CLOSURE)
        self.assertEqual(closure["module_count"], 5)
        self.assertEqual(
            closure["module_text"],
            "smem.ko\nminidump.ko\nqcom-scm.ko\nqcom_wdt_core.ko\ngh_virt_wdt.ko\n",
        )

    def test_watchdog_closure_rejects_forbidden_modules(self):
        dep_map = {
            "gh_virt_wdt.ko": ["qcom_wdt_core.ko"],
            "qcom_wdt_core.ko": ["dwc3-msm.ko"],
            "dwc3-msm.ko": [],
        }
        with self.assertRaisesRegex(SystemExit, "forbidden module"):
            self.module.watchdog_closure(dep_map=dep_map, recovery_basenames=list(dep_map))

    def test_source_is_watchdog_managed_park_not_download_beacon(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK", text)
        self.assertIn("NR_FINIT_MODULE 273", text)
        self.assertIn("no_reboot_request=1", text)
        self.assertIn("no_download_beacon=1", text)
        self.assertNotIn("LINUX_REBOOT_CMD_RESTART2", text)
        self.assertNotIn("k_download_arg", text)
        self.assertNotIn("usb_gadget", text)
        self.assertNotIn("ss_acm.0", text)
        self.assertNotIn("ttyGS0", text)

    @unittest.skipUnless(MANIFEST.exists(), "private M31B manifest missing")
    def test_current_manifest_is_host_only_boot_only_and_single_member(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["closure"]["modules"], self.module.EXPECTED_WDT_CLOSURE)
        self.assertEqual(manifest["tar_members"], ["boot.img.lz4"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertFalse(manifest["safety"]["auto_reboot"])
        self.assertFalse(manifest["safety"]["intended_reboot_syscall"])
        self.assertIsNone(manifest["safety"]["reboot_request"])
        self.assertFalse(manifest["safety"]["configfs_runtime_gadget"])
        self.assertFalse(manifest["safety"]["acm"])


if __name__ == "__main__":
    unittest.main()
