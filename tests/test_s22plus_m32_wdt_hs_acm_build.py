import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m32_wdt_hs_acm.py")
TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m32_wdt_hs_acm_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m32_wdt_hs_acm", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM32WdtHsAcmBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_variant_constants_are_watchdog_managed_hs_acm(self):
        self.assertEqual(self.module.MARKER, "S22_NATIVE_INIT_USB_ACM_M32_WDT_HS")
        self.assertEqual(self.module.MODULES_RAMDISK, "s22plus_m32_wdt_hs_acm.modules")
        self.assertEqual(self.module.WATCHDOG_TARGET, "gh_virt_wdt.ko")
        self.assertIn("phy-msm-ssusb-qmp.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertIn("eud.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertNotIn("qcom_wdt_core.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertNotIn("gh_virt_wdt.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertNotIn("sec_debug.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertNotIn("minidump.ko", self.module.M32_EXCLUDED_MODULES)
        self.assertNotIn("abc.ko", self.module.M32_EXCLUDED_MODULES)

    def test_dependency_complete_wdt_hs_order_toposorts_and_keeps_watchdog(self):
        dep_map = {
            "dwc3-msm.ko": ["arm_smmu.ko"],
            "usb_f_ss_acm.ko": ["dwc3-msm.ko"],
            "gh_virt_wdt.ko": ["qcom_wdt_core.ko"],
            "qcom_wdt_core.ko": ["qcom-scm.ko"],
            "qcom-scm.ko": ["minidump.ko"],
            "minidump.ko": ["smem.ko"],
            "smem.ko": [],
            "arm_smmu.ko": [],
        }
        original_expected = self.module.EXPECTED_M32_MODULES
        original_targets = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        self.addCleanup(setattr, self.module, "EXPECTED_M32_MODULES", original_expected)
        self.addCleanup(setattr, self.module, "EXPECTED_M25_HS_ONLY_SUBSET", original_targets)
        self.module.EXPECTED_M32_MODULES = [
            "arm_smmu.ko",
            "dwc3-msm.ko",
            "usb_f_ss_acm.ko",
            "smem.ko",
            "minidump.ko",
            "qcom-scm.ko",
            "qcom_wdt_core.ko",
            "gh_virt_wdt.ko",
        ]
        self.module.EXPECTED_M25_HS_ONLY_SUBSET = ["usb_f_ss_acm.ko"]
        recovery = [
            "usb_f_ss_acm.ko",
            "dwc3-msm.ko",
            "arm_smmu.ko",
            "gh_virt_wdt.ko",
            "qcom_wdt_core.ko",
            "qcom-scm.ko",
            "minidump.ko",
            "smem.ko",
        ]

        closure = self.module.dependency_complete_wdt_hs_order(
            dep_map=dep_map,
            recovery_basenames=recovery,
        )

        self.assertEqual(closure["modules"], self.module.EXPECTED_M32_MODULES)
        self.assertEqual(closure["watchdog_modules"], ["qcom_wdt_core.ko", "gh_virt_wdt.ko"])
        self.assertEqual(closure["usb_modules"], ["dwc3-msm.ko", "usb_f_ss_acm.ko", "usb_f_ss_mon_gadget.ko"])

    def test_dependency_complete_wdt_hs_order_rejects_excluded_hard_dep(self):
        dep_map = {
            "usb_f_ss_acm.ko": ["phy-msm-ssusb-qmp.ko"],
            "phy-msm-ssusb-qmp.ko": [],
            "gh_virt_wdt.ko": [],
        }
        original_expected = self.module.EXPECTED_M32_MODULES
        original_targets = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        self.addCleanup(setattr, self.module, "EXPECTED_M32_MODULES", original_expected)
        self.addCleanup(setattr, self.module, "EXPECTED_M25_HS_ONLY_SUBSET", original_targets)
        self.module.EXPECTED_M32_MODULES = ["usb_f_ss_acm.ko", "gh_virt_wdt.ko"]
        self.module.EXPECTED_M25_HS_ONLY_SUBSET = ["usb_f_ss_acm.ko"]
        with self.assertRaisesRegex(SystemExit, "excluded hard deps"):
            self.module.dependency_complete_wdt_hs_order(
                dep_map=dep_map,
                recovery_basenames=list(dep_map),
            )

    def test_generated_source_is_m32_wdt_hs_not_m18_or_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "m32.c"
            text = self.module.generate_m32_source(TEMPLATE_SOURCE, generated, 45)

        self.assertIn("S22_NATIVE_INIT_USB_ACM_M32_WDT_HS", text)
        self.assertIn("watchdog_managed=1", text)
        self.assertIn("module_list=dep_complete_wdt_hs_acm", text)
        self.assertIn("module_count=45", text)
        self.assertIn("dtbo_high_speed_cap=not_included", text)
        self.assertIn("0x0200", text)
        self.assertNotIn("S22_NATIVE_INIT_USB_ACM_M18_FULL", text)
        self.assertNotIn("watchdog_blocklist=1", text)
        self.assertNotIn("module_count=141", text)
        self.assertNotIn("0x0320", text)

    @unittest.skipUnless(MANIFEST.exists(), "private M32 manifest missing")
    def test_current_manifest_is_host_only_boot_only_single_member(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["closure"]["modules"], self.module.EXPECTED_M32_MODULES)
        self.assertEqual(manifest["closure"]["module_count"], 45)
        self.assertEqual(
            manifest["closure"]["module_sha256"],
            "2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c",
        )
        self.assertEqual(manifest["tar_members"], ["boot.img.lz4"])
        self.assertEqual(manifest["hashes"]["base_boot"], self.module.EXPECTED_BASE_BOOT_SHA256)
        self.assertEqual(manifest["hashes"]["nochange_repack_boot"], self.module.EXPECTED_BASE_BOOT_SHA256)
        self.assertTrue(manifest["magiskboot"]["nochange_repack_byte_identical"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertFalse(manifest["safety"]["auto_reboot"])
        self.assertFalse(manifest["safety"]["intended_reboot_syscall"])
        self.assertIsNone(manifest["safety"]["reboot_request"])
        self.assertTrue(manifest["safety"]["acm"])
        self.assertTrue(manifest["safety"]["watchdog_managed"])
        self.assertTrue(manifest["safety"]["qmp_module_excluded"])
        self.assertFalse(manifest["safety"]["dtbo_high_speed_cap_included"])
        self.assertEqual(manifest["safety"]["configfs_runtime_gadget"], "ss_acm.0 only")


if __name__ == "__main__":
    unittest.main()
