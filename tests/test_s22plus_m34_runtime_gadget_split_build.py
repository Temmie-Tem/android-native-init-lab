import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m34_runtime_gadget_split", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34RuntimeGadgetSplitBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_stage_matrix_is_incremental_runtime_gadget_split(self):
        stages = self.module.STAGES
        self.assertEqual([stage.label for stage in stages], ["S1", "S2", "S3"])
        self.assertEqual([stage.number for stage in stages], [1, 2, 3])
        self.assertEqual(self.module.MARKER_PREFIX, "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT")

        by_label = {stage.label: stage for stage in stages}
        self.assertTrue(by_label["S1"].configfs_gadget)
        self.assertFalse(by_label["S1"].usb_role_force)
        self.assertFalse(by_label["S1"].udc_bind)
        self.assertTrue(by_label["S2"].configfs_gadget)
        self.assertTrue(by_label["S2"].usb_role_force)
        self.assertFalse(by_label["S2"].udc_bind)
        self.assertTrue(by_label["S3"].configfs_gadget)
        self.assertTrue(by_label["S3"].usb_role_force)
        self.assertTrue(by_label["S3"].udc_bind)

    def test_source_has_stage_guards_and_no_reboot_syscall(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("#if M34_STAGE >= 2", text)
        self.assertIn("#if M34_STAGE >= 3", text)
        self.assertIn("create_configfs_gadget", text)
        self.assertIn("force_usb_roles_device", text)
        self.assertIn("bind_udc", text)
        self.assertIn("a600000.dwc3", text)
        self.assertIn("/config/usb_gadget/g1/functions/ss_acm.0", text)
        self.assertNotIn("NR_REBOOT", text)
        self.assertNotIn("LINUX_REBOOT_CMD_RESTART2", text)
        self.assertNotIn("sys_reboot", text)
        self.assertNotIn("ttyGS0", text)

    def test_c_define_string_quotes_for_gcc_preprocessor(self):
        self.assertEqual(self.module.c_define_string("NAME", "VALUE"), '-DNAME="VALUE"')

    @unittest.skipUnless(MANIFEST.exists(), "private M34 manifest missing")
    def test_current_manifest_is_host_only_boot_only_stage_matrix(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["target"], "SM-S906N/g0q/S906NKSS7FYG8")
        self.assertEqual([stage["label"] for stage in manifest["stages"]], ["S1", "S2", "S3"])
        self.assertTrue(manifest["matrix"]["p30_is_s0"])
        self.assertTrue(manifest["matrix"]["module_closure_matches_p30_and_m32"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertFalse(manifest["safety"]["auto_reboot"])
        self.assertFalse(manifest["safety"]["intended_reboot_syscall"])
        self.assertIsNone(manifest["safety"]["reboot_request"])
        self.assertFalse(manifest["safety"]["persistent_partition_mount"])
        self.assertFalse(manifest["safety"]["block_device_writes"])
        self.assertTrue(manifest["safety"]["stage_s1_no_role_force"])
        self.assertTrue(manifest["safety"]["stage_s1_no_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s2_no_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s3_binds_only_a600000_dwc3"])

        by_label = {stage["label"]: stage for stage in manifest["stages"]}
        self.assertEqual(by_label["S1"]["runtime_steps"], {"configfs_gadget": True, "usb_role_force": False, "udc_bind": False})
        self.assertEqual(by_label["S2"]["runtime_steps"], {"configfs_gadget": True, "usb_role_force": True, "udc_bind": False})
        self.assertEqual(by_label["S3"]["runtime_steps"], {"configfs_gadget": True, "usb_role_force": True, "udc_bind": True})
        for stage in manifest["stages"]:
            self.assertEqual(stage["tar_members"], ["boot.img.lz4"])
            self.assertEqual(stage["closure"]["modules"], self.module.EXPECTED_M32_MODULES)
            self.assertEqual(stage["closure"]["module_count"], 45)
            self.assertEqual(
                stage["closure"]["module_sha256"],
                "2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c",
            )
            self.assertIn(f"S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_{stage['label']}", stage["init"]["required_strings"])

        s1_required = set(by_label["S1"]["init"]["required_strings"])
        s2_required = set(by_label["S2"]["init"]["required_strings"])
        s3_required = set(by_label["S3"]["init"]["required_strings"])
        self.assertIn("role_force=0", s1_required)
        self.assertNotIn("/sys/class/usb_role", s1_required)
        self.assertIn("/sys/class/usb_role", s2_required)
        self.assertNotIn("/config/usb_gadget/g1/UDC", s2_required)
        self.assertIn("/config/usb_gadget/g1/UDC", s3_required)
        self.assertIn("a600000.dwc3", s3_required)


if __name__ == "__main__":
    unittest.main()
