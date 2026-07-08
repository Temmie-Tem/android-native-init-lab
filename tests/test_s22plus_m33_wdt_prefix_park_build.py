import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m33_wdt_prefix_park.py")
TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m31b_wdt_managed_park.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m33_wdt_prefix_park", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM33WdtPrefixParkBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_variant_matrix_is_module_load_only_and_monotonic(self):
        labels = [variant.label for variant in self.module.PREFIX_VARIANTS]
        prefix_counts = [variant.prefix_count for variant in self.module.PREFIX_VARIANTS]

        self.assertEqual(labels, ["P12", "P18", "P25", "P27", "P28", "P30", "P40"])
        self.assertEqual(prefix_counts, sorted(prefix_counts))
        self.assertEqual(prefix_counts[-1], len(self.module.EXPECTED_M25_HS_ONLY_SUBSET))
        self.assertEqual(self.module.WATCHDOG_TARGET, "gh_virt_wdt.ko")
        self.assertIn("phy-msm-ssusb-qmp.ko", self.module.M33_EXCLUDED_MODULES)
        self.assertIn("eud.ko", self.module.M33_EXCLUDED_MODULES)

    def test_dependency_complete_wdt_prefix_order_keeps_watchdog_and_full_prefix_matches_expected(self):
        dep_map = {
            "target_a.ko": [],
            "target_b.ko": ["target_a.ko"],
            "target_c.ko": ["target_b.ko"],
            "gh_virt_wdt.ko": ["qcom_wdt_core.ko"],
            "qcom_wdt_core.ko": ["smem.ko"],
            "smem.ko": [],
        }
        original_targets = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        original_expected = self.module.EXPECTED_M32_MODULES
        self.addCleanup(setattr, self.module, "EXPECTED_M25_HS_ONLY_SUBSET", original_targets)
        self.addCleanup(setattr, self.module, "EXPECTED_M32_MODULES", original_expected)
        self.module.EXPECTED_M25_HS_ONLY_SUBSET = ["target_a.ko", "target_b.ko", "target_c.ko"]
        self.module.EXPECTED_M32_MODULES = [
            "target_a.ko",
            "target_b.ko",
            "target_c.ko",
            "smem.ko",
            "qcom_wdt_core.ko",
            "gh_virt_wdt.ko",
        ]

        prefix = self.module.dependency_complete_wdt_prefix_order(
            dep_map=dep_map,
            recovery_basenames=list(dep_map),
            prefix_count=2,
        )
        self.assertEqual(prefix["modules"], ["target_a.ko", "target_b.ko", "smem.ko", "qcom_wdt_core.ko", "gh_virt_wdt.ko"])
        self.assertNotIn("target_c.ko", prefix["modules"])
        self.assertFalse(prefix["key_boundaries"]["configfs_runtime_gadget"])

        full = self.module.dependency_complete_wdt_prefix_order(
            dep_map=dep_map,
            recovery_basenames=list(dep_map),
            prefix_count=3,
        )
        self.assertEqual(full["modules"], self.module.EXPECTED_M32_MODULES)
        self.assertEqual(full["watchdog_target"], "gh_virt_wdt.ko")

    def test_dependency_complete_wdt_prefix_order_rejects_excluded_hard_dep(self):
        dep_map = {
            "target_a.ko": ["phy-msm-ssusb-qmp.ko"],
            "phy-msm-ssusb-qmp.ko": [],
            "gh_virt_wdt.ko": [],
        }
        original_targets = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        original_expected = self.module.EXPECTED_M32_MODULES
        self.addCleanup(setattr, self.module, "EXPECTED_M25_HS_ONLY_SUBSET", original_targets)
        self.addCleanup(setattr, self.module, "EXPECTED_M32_MODULES", original_expected)
        self.module.EXPECTED_M25_HS_ONLY_SUBSET = ["target_a.ko"]
        self.module.EXPECTED_M32_MODULES = ["target_a.ko", "gh_virt_wdt.ko"]

        with self.assertRaisesRegex(SystemExit, "excluded hard deps"):
            self.module.dependency_complete_wdt_prefix_order(
                dep_map=dep_map,
                recovery_basenames=list(dep_map),
                prefix_count=1,
            )

    def test_generated_source_is_m33_prefix_park_not_m31b_or_usb_acm(self):
        variant = self.module.PrefixVariant("P28", 28, "test")
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "m33.c"
            text = self.module.generate_m33_source(TEMPLATE_SOURCE, generated, variant, 41)

        self.assertIn("S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P28", text)
        self.assertIn("s22plus_m33_p28_wdt_prefix_park.modules", text)
        self.assertIn("module_list=wdt_prefix_park", text)
        self.assertIn("variant=P28", text)
        self.assertIn("prefix_targets=28", text)
        self.assertIn("module_load_only=1", text)
        self.assertIn("no_configfs=1", text)
        self.assertIn("no_acm=1", text)
        self.assertNotIn("S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK", text)
        self.assertNotIn("s22plus_m31b_wdt_managed.modules", text)
        self.assertNotIn("usb_gadget", text)
        self.assertNotIn("ss_acm.0", text)
        self.assertNotIn("ttyGS0", text)
        self.assertNotIn("LINUX_REBOOT_CMD_RESTART2", text)

    @unittest.skipUnless(MANIFEST.exists(), "private M33 manifest missing")
    def test_current_manifest_is_host_only_boot_only_prefix_matrix(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        labels = [variant["label"] for variant in manifest["variants"]]

        self.assertEqual(labels, ["P12", "P18", "P25", "P27", "P28", "P30", "P40"])
        self.assertTrue(manifest["matrix"]["full_prefix_matches_m32_modules"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertFalse(manifest["safety"]["auto_reboot"])
        self.assertFalse(manifest["safety"]["intended_reboot_syscall"])
        self.assertIsNone(manifest["safety"]["reboot_request"])
        self.assertFalse(manifest["safety"]["configfs_runtime_gadget"])
        self.assertFalse(manifest["safety"]["acm"])
        for variant in manifest["variants"]:
            self.assertEqual(variant["tar_members"], ["boot.img.lz4"])
            self.assertNotIn("phy-msm-ssusb-qmp.ko", variant["closure"]["modules"])
            self.assertNotIn("eud.ko", variant["closure"]["modules"])
        by_label = {variant["label"]: variant for variant in manifest["variants"]}
        self.assertFalse(by_label["P27"]["closure"]["key_boundaries"]["includes_dwc3"])
        self.assertTrue(by_label["P28"]["closure"]["key_boundaries"]["includes_dwc3"])
        self.assertFalse(by_label["P28"]["closure"]["key_boundaries"]["includes_acm_module"])
        self.assertTrue(by_label["P30"]["closure"]["key_boundaries"]["includes_acm_module"])
        self.assertEqual(by_label["P40"]["closure"]["modules"], self.module.EXPECTED_M32_MODULES)

    @unittest.skipUnless(MANIFEST.exists(), "private M33 manifest missing")
    def test_p40_live_boundary_is_subsumed_by_p30_module_closure(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        by_label = {variant["label"]: variant for variant in manifest["variants"]}
        p30 = by_label["P30"]
        p40 = by_label["P40"]

        self.assertEqual(p30["closure"]["modules"], p40["closure"]["modules"])
        self.assertEqual(p30["closure"]["module_sha256"], p40["closure"]["module_sha256"])
        self.assertEqual(p30["hashes"]["m33_modules"], p40["hashes"]["m33_modules"])
        self.assertEqual(p30["closure"]["modules"], self.module.EXPECTED_M32_MODULES)
        self.assertTrue(p30["closure"]["key_boundaries"]["includes_acm_module"])
        self.assertFalse(p30["closure"]["key_boundaries"]["configfs_runtime_gadget"])

        self.assertNotEqual(p30["hashes"]["ap_tar_md5"], p40["hashes"]["ap_tar_md5"])
        self.assertNotEqual(p30["hashes"]["m33_init"], p40["hashes"]["m33_init"])
        self.assertIn("S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P30", p30["init"]["required_strings"])
        self.assertIn("S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P40", p40["init"]["required_strings"])


if __name__ == "__main__":
    unittest.main()
