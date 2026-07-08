import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_6/manifest.json")


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
        self.assertEqual([stage.label for stage in stages], ["S1", "S2", "S3", "S4", "S5", "S6", "S7A"])
        self.assertEqual([stage.number for stage in stages], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(self.module.MARKER_PREFIX, "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT")

        by_label = {stage.label: stage for stage in stages}
        self.assertTrue(by_label["S1"].configfs_gadget)
        self.assertTrue(by_label["S1"].udc_none)
        self.assertFalse(by_label["S1"].max_speed_high_speed)
        self.assertFalse(by_label["S1"].usb_role_force)
        self.assertFalse(by_label["S1"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S1"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S1"].udc_bind)
        self.assertFalse(by_label["S1"].soft_connect)
        self.assertTrue(by_label["S2"].configfs_gadget)
        self.assertTrue(by_label["S2"].udc_none)
        self.assertTrue(by_label["S2"].max_speed_high_speed)
        self.assertTrue(by_label["S2"].usb_role_force)
        self.assertFalse(by_label["S2"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S2"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S2"].udc_bind)
        self.assertFalse(by_label["S2"].soft_connect)
        self.assertTrue(by_label["S3"].configfs_gadget)
        self.assertTrue(by_label["S3"].udc_none)
        self.assertTrue(by_label["S3"].max_speed_high_speed)
        self.assertTrue(by_label["S3"].usb_role_force)
        self.assertFalse(by_label["S3"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S3"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S3"].udc_bind)
        self.assertFalse(by_label["S3"].soft_connect)
        self.assertTrue(by_label["S4"].configfs_gadget)
        self.assertTrue(by_label["S4"].udc_none)
        self.assertTrue(by_label["S4"].max_speed_high_speed)
        self.assertFalse(by_label["S4"].usb_role_force)
        self.assertTrue(by_label["S4"].ssusb_speed_high_speed)
        self.assertTrue(by_label["S4"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S4"].udc_bind)
        self.assertFalse(by_label["S4"].soft_connect)
        self.assertTrue(by_label["S5"].configfs_gadget)
        self.assertTrue(by_label["S5"].udc_none)
        self.assertTrue(by_label["S5"].max_speed_high_speed)
        self.assertFalse(by_label["S5"].usb_role_force)
        self.assertTrue(by_label["S5"].ssusb_speed_high_speed)
        self.assertTrue(by_label["S5"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S5"].udc_bind)
        self.assertTrue(by_label["S5"].soft_connect)
        self.assertFalse(by_label["S5"].stock_softdep_parity)
        self.assertTrue(by_label["S6"].configfs_gadget)
        self.assertTrue(by_label["S6"].udc_none)
        self.assertFalse(by_label["S6"].max_speed_high_speed)
        self.assertFalse(by_label["S6"].usb_role_force)
        self.assertFalse(by_label["S6"].ssusb_speed_high_speed)
        self.assertTrue(by_label["S6"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S6"].udc_bind)
        self.assertFalse(by_label["S6"].soft_connect)
        self.assertTrue(by_label["S6"].stock_softdep_parity)
        self.assertTrue(by_label["S6"].qmp_module_included)
        self.assertTrue(by_label["S6"].eud_module_included)
        self.assertTrue(by_label["S6"].ucsi_glink_included)
        self.assertTrue(by_label["S7A"].configfs_gadget)
        self.assertTrue(by_label["S7A"].udc_none)
        self.assertFalse(by_label["S7A"].max_speed_high_speed)
        self.assertFalse(by_label["S7A"].usb_role_force)
        self.assertFalse(by_label["S7A"].ssusb_speed_high_speed)
        self.assertTrue(by_label["S7A"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S7A"].udc_bind)
        self.assertFalse(by_label["S7A"].soft_connect)
        self.assertTrue(by_label["S7A"].stock_softdep_parity)
        self.assertTrue(by_label["S7A"].qmp_module_included)
        self.assertTrue(by_label["S7A"].eud_module_included)
        self.assertTrue(by_label["S7A"].ucsi_glink_included)
        self.assertTrue(by_label["S7A"].session_producer_parity)
        self.assertTrue(by_label["S7A"].max77705_session_modules_included)
        self.assertTrue(by_label["S7A"].typec_readback_markers)

    def test_source_has_stage_guards_and_no_reboot_syscall(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("#if M34_STAGE >= 2", text)
        self.assertIn("#if M34_STAGE >= 3", text)
        self.assertIn("#if M34_STAGE >= 4", text)
        self.assertIn("#if M34_STAGE == 5", text)
        self.assertIn("#elif M34_STAGE == 6", text)
        self.assertIn("#elif M34_STAGE == 7", text)
        self.assertIn("create_configfs_gadget", text)
        self.assertIn("force_usb_roles_device", text)
        self.assertIn("set_ssusb_speed_high_speed", text)
        self.assertIn("set_ssusb_mode_peripheral", text)
        self.assertIn("bind_udc", text)
        self.assertIn("soft_connect_udc", text)
        self.assertIn("set_max_speed_high_speed", text)
        self.assertIn("a600000.dwc3", text)
        self.assertIn("/sys/class/udc/a600000.dwc3/soft_connect", text)
        self.assertIn("emit_typec_udc_readback", text)
        self.assertIn("/sys/class/typec/port0/data_role", text)
        self.assertIn("/sys/class/typec/port0-partner/uevent", text)
        self.assertIn("/sys/class/udc/a600000.dwc3/current_speed", text)
        self.assertIn('"connect"', text)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/speed", text)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/mode", text)
        self.assertIn('"peripheral"', text)
        self.assertIn("/config/usb_gadget/g1/functions/ss_acm.0", text)
        self.assertIn("/config/usb_gadget/g1/UDC", text)
        self.assertIn("/config/usb_gadget/g1/max_speed", text)
        self.assertIn("0x04E8", text)
        self.assertIn("0x0200", text)
        self.assertIn("900", text)
        self.assertIn("\"none\"", text)
        self.assertNotIn("NR_REBOOT", text)
        self.assertNotIn("LINUX_REBOOT_CMD_RESTART2", text)
        self.assertNotIn("sys_reboot", text)
        self.assertNotIn("ttyGS0", text)

    def test_source_keeps_stock_gadget_order(self):
        text = SOURCE.read_text(encoding="utf-8")
        udc_none = text.index('write_attr("/config/usb_gadget/g1/UDC", "none")')
        id_vendor = text.index('write_attr("/config/usb_gadget/g1/idVendor", "0x04E8")')
        link_acm = text.index('sys_symlinkat("../../functions/ss_acm.0", "/config/usb_gadget/g1/configs/b.1/f1")')
        bind_udc = text.index("static void bind_udc")
        start_max_speed = text.index("set_max_speed_high_speed();")
        start_legacy_role = text.index("force_usb_roles_device();")
        start_ssusb_speed = text.index("set_ssusb_speed_high_speed();")
        start_ssusb_mode = text.index("set_ssusb_mode_peripheral();")
        start_bind = text.index("bind_udc();")
        start_soft_connect = text.index("soft_connect_udc();")

        self.assertLess(udc_none, id_vendor)
        self.assertLess(id_vendor, link_acm)
        self.assertLess(link_acm, bind_udc)
        self.assertLess(start_max_speed, start_legacy_role)
        self.assertLess(start_legacy_role, start_bind)
        self.assertLess(start_max_speed, start_ssusb_speed)
        self.assertLess(start_ssusb_speed, start_ssusb_mode)
        self.assertLess(start_ssusb_mode, start_bind)
        self.assertLess(start_bind, start_soft_connect)

    def test_c_define_string_quotes_for_gcc_preprocessor(self):
        self.assertEqual(self.module.c_define_string("NAME", "VALUE"), '-DNAME="VALUE"')

    @unittest.skipUnless(MANIFEST.exists(), "private M34 manifest missing")
    def test_current_manifest_is_host_only_boot_only_stage_matrix(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["target"], "SM-S906N/g0q/S906NKSS7FYG8")
        self.assertEqual([stage["label"] for stage in manifest["stages"]], ["S1", "S2", "S3", "S4", "S5", "S6", "S7A"])
        self.assertTrue(manifest["matrix"]["p30_is_s0"])
        self.assertEqual(manifest["matrix"]["live_order"], ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertEqual(manifest["matrix"]["host_build_order"], ["S1", "S2", "S3", "S4", "S5", "S6", "S7A"])
        self.assertEqual(manifest["matrix"]["next_host_only_candidate"], "S7A")
        self.assertTrue(manifest["matrix"]["module_closure_matches_p30_and_m32_for_s1_s5"])
        self.assertTrue(manifest["matrix"]["s6_module_closure_restores_stock_dwc3_softdep"])
        self.assertEqual(
            manifest["matrix"]["s6_stock_softdep_targets"],
            ["phy-msm-ssusb-qmp.ko", "eud.ko", "ucsi_glink.ko"],
        )
        self.assertTrue(manifest["matrix"]["s7a_module_closure_restores_stock_session_producer_chain"])
        self.assertEqual(manifest["matrix"]["s7a_uses_firmware_module_filename_qcom_i2c_pmic"], "qcom-i2c-pmic.ko")
        self.assertIn("max77705_charger.ko", manifest["matrix"]["s7a_session_producer_targets"])
        self.assertIn("sec_debug_region.ko", manifest["matrix"]["s7a_risk_modules"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertTrue(manifest["safety"]["requires_s7a_specific_live_risk_review"])
        self.assertEqual(manifest["safety"]["runtime_module_list_buffer_bytes"], self.module.RUNTIME_MODULES_LOAD_BUF)
        self.assertFalse(manifest["safety"]["auto_reboot"])
        self.assertFalse(manifest["safety"]["intended_reboot_syscall"])
        self.assertIsNone(manifest["safety"]["reboot_request"])
        self.assertFalse(manifest["safety"]["persistent_partition_mount"])
        self.assertFalse(manifest["safety"]["block_device_writes"])
        self.assertTrue(manifest["safety"]["stock_order_udc_none_before_ids_and_link"])
        self.assertTrue(manifest["safety"]["stock_order_udc_bind_last"])
        self.assertTrue(manifest["safety"]["stage_s1_no_max_speed_high_speed"])
        self.assertTrue(manifest["safety"]["stage_s1_no_role_force"])
        self.assertTrue(manifest["safety"]["stage_s1_no_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s2_sets_max_speed_high_speed"])
        self.assertTrue(manifest["safety"]["stage_s2_no_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s3_binds_only_a600000_dwc3"])
        self.assertTrue(manifest["safety"]["stage_s4_replaces_dead_usb_role_with_ssusb_role_lever"])
        self.assertTrue(manifest["safety"]["stage_s4_sets_ssusb_speed_high_speed_before_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s4_sets_ssusb_mode_peripheral_before_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s4_no_usb_role_force"])
        self.assertTrue(manifest["safety"]["stage_s5_soft_connect_after_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s5_no_descriptor_or_companion_change"])
        self.assertTrue(manifest["safety"]["stage_s6_includes_qmp_eud_ucsi_softdep_parity"])
        self.assertTrue(manifest["safety"]["stage_s6_no_high_speed_force"])
        self.assertTrue(manifest["safety"]["stage_s6_no_soft_connect"])
        self.assertTrue(manifest["safety"]["stage_s6_no_eud_sysfs_write"])
        self.assertTrue(manifest["safety"]["stage_s6_keeps_ssusb_mode_peripheral_before_udc_bind"])
        self.assertTrue(manifest["safety"]["stage_s7a_restores_max77705_pdic_altmode_session_producer_chain"])
        self.assertTrue(manifest["safety"]["stage_s7a_adds_typec_udc_readback_markers"])
        self.assertTrue(manifest["safety"]["stage_s7a_no_functionfs_or_conn_gadget"])
        self.assertTrue(manifest["safety"]["stage_s7a_contains_sec_debug_region_due_stock_charger_dependency"])

        by_label = {stage["label"]: stage for stage in manifest["stages"]}
        self.assertEqual(
            by_label["S1"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": False,
                "qmp_module_included": False,
                "eud_module_included": False,
                "ucsi_glink_included": False,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S2"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": True,
                "usb_role_force": True,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": False,
                "qmp_module_included": False,
                "eud_module_included": False,
                "ucsi_glink_included": False,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S3"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": True,
                "usb_role_force": True,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": True,
                "soft_connect": False,
                "stock_softdep_parity": False,
                "qmp_module_included": False,
                "eud_module_included": False,
                "ucsi_glink_included": False,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S4"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": True,
                "usb_role_force": False,
                "ssusb_speed_high_speed": True,
                "ssusb_mode_peripheral": True,
                "udc_bind": True,
                "soft_connect": False,
                "stock_softdep_parity": False,
                "qmp_module_included": False,
                "eud_module_included": False,
                "ucsi_glink_included": False,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S5"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": True,
                "usb_role_force": False,
                "ssusb_speed_high_speed": True,
                "ssusb_mode_peripheral": True,
                "udc_bind": True,
                "soft_connect": True,
                "stock_softdep_parity": False,
                "qmp_module_included": False,
                "eud_module_included": False,
                "ucsi_glink_included": False,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S6"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": True,
                "udc_bind": True,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": False,
                "max77705_session_modules_included": False,
                "typec_readback_markers": False,
            },
        )
        self.assertEqual(
            by_label["S7A"]["runtime_steps"],
            {
                "configfs_gadget": True,
                "udc_none": True,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": True,
                "udc_bind": True,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": True,
                "max77705_session_modules_included": True,
                "typec_readback_markers": True,
            },
        )
        for stage in manifest["stages"]:
            self.assertEqual(stage["tar_members"], ["boot.img.lz4"])
            if stage["label"] == "S6":
                self.assertEqual(stage["closure"]["module_count"], 55)
                self.assertEqual(
                    stage["closure"]["stock_softdep_targets"],
                    ["phy-msm-ssusb-qmp.ko", "eud.ko", "ucsi_glink.ko"],
                )
                self.assertEqual(stage["closure"]["stock_softdep_new_modules"], self.module.M34_S6_EXPECTED_NEW_MODULES)
                self.assertIn("phy-msm-ssusb-qmp.ko", stage["closure"]["modules"])
                self.assertIn("eud.ko", stage["closure"]["modules"])
                self.assertIn("ucsi_glink.ko", stage["closure"]["modules"])
                self.assertNotIn("sec_debug_region.ko", stage["closure"]["modules"])
            elif stage["label"] == "S7A":
                self.assertEqual(stage["closure"]["module_count"], 83)
                self.assertEqual(
                    stage["closure"]["session_producer_targets"],
                    [
                        "qcom-i2c-pmic.ko",
                        "mfd_max77705.ko",
                        "max77705_charger.ko",
                        "max77705-fuelgauge.ko",
                        "pdic_max77705.ko",
                        "charger-ulog-glink.ko",
                        "altmode-glink.ko",
                    ],
                )
                self.assertEqual(stage["closure"]["session_producer_new_modules"], self.module.M34_S7A_EXPECTED_NEW_MODULES)
                self.assertIn("qcom-i2c-pmic.ko", stage["closure"]["modules"])
                self.assertIn("mfd_max77705.ko", stage["closure"]["modules"])
                self.assertIn("pdic_max77705.ko", stage["closure"]["modules"])
                self.assertIn("max77705_charger.ko", stage["closure"]["modules"])
                self.assertIn("max77705-fuelgauge.ko", stage["closure"]["modules"])
                self.assertIn("sec_debug_region.ko", stage["closure"]["modules"])
                self.assertTrue(stage["closure"]["contains_sec_debug_region"])
                self.assertTrue(stage["closure"]["requires_live_risk_review"])
                self.assertIn("sec_debug_region.ko", stage["closure"]["risk_modules"])
            else:
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
        s4_required = set(by_label["S4"]["init"]["required_strings"])
        s5_required = set(by_label["S5"]["init"]["required_strings"])
        s6_required = set(by_label["S6"]["init"]["required_strings"])
        s7a_required = set(by_label["S7A"]["init"]["required_strings"])
        self.assertIn("udc_none=1", s1_required)
        self.assertIn("/config/usb_gadget/g1/UDC", s1_required)
        self.assertIn("none", s1_required)
        self.assertIn("max_speed_high_speed=0", s1_required)
        self.assertIn("role_force=0", s1_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s1_required)
        self.assertNotIn("high-speed", s1_required)
        self.assertNotIn("/sys/class/usb_role", s1_required)
        self.assertIn("max_speed_high_speed=1", s2_required)
        self.assertIn("/config/usb_gadget/g1/max_speed", s2_required)
        self.assertIn("high-speed", s2_required)
        self.assertIn("/sys/class/usb_role", s2_required)
        self.assertIn("/config/usb_gadget/g1/UDC", s2_required)
        self.assertNotIn("a600000.dwc3", s2_required)
        self.assertIn("/config/usb_gadget/g1/UDC", s3_required)
        self.assertIn("a600000.dwc3", s3_required)
        self.assertIn("role_force=0", s4_required)
        self.assertNotIn("/sys/class/usb_role", s4_required)
        self.assertIn("ssusb_speed_high_speed=1", s4_required)
        self.assertIn("ssusb_mode_peripheral=1", s4_required)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/speed", s4_required)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/mode", s4_required)
        self.assertIn("peripheral", s4_required)
        self.assertIn("a600000.dwc3", s4_required)
        self.assertIn("soft_connect=0", s4_required)
        self.assertIn("soft_connect=1", s5_required)
        self.assertIn("/sys/class/udc/a600000.dwc3/soft_connect", s5_required)
        self.assertIn("phase=soft_connect", s5_required)
        self.assertIn("value=connect", s5_required)
        self.assertIn("a600000.dwc3", s5_required)
        self.assertIn("max_speed_high_speed=0", s6_required)
        self.assertIn("ssusb_speed_high_speed=0", s6_required)
        self.assertIn("ssusb_mode_peripheral=1", s6_required)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/mode", s6_required)
        self.assertIn("peripheral", s6_required)
        self.assertIn("udc_bind=1", s6_required)
        self.assertIn("a600000.dwc3", s6_required)
        self.assertIn("stock_softdep_parity=1", s6_required)
        self.assertIn("qmp_module=1", s6_required)
        self.assertIn("eud_module=1", s6_required)
        self.assertIn("ucsi_glink=1", s6_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s6_required)
        self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/speed", s6_required)
        self.assertNotIn("high-speed", s6_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s6_required)
        self.assertIn("session_producer_parity=1", s7a_required)
        self.assertIn("max77705_session=1", s7a_required)
        self.assertIn("typec_readback=1", s7a_required)
        self.assertIn("functionfs=0", s7a_required)
        self.assertIn("stock_composite=0", s7a_required)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/speed", s7a_required)
        self.assertIn("/sys/class/typec/port0/data_role", s7a_required)
        self.assertIn("/sys/class/typec/port0/power_role", s7a_required)
        self.assertIn("/sys/class/typec/port0/port_type", s7a_required)
        self.assertIn("/sys/class/typec/port0-partner/uevent", s7a_required)
        self.assertIn("/sys/class/udc/a600000.dwc3/current_speed", s7a_required)
        self.assertIn("typec_pre_bind", s7a_required)
        self.assertIn("typec_post_bind", s7a_required)
        self.assertIn("udc_pre_bind", s7a_required)
        self.assertIn("udc_post_bind", s7a_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s7a_required)
        self.assertNotIn("high-speed", s7a_required)
        self.assertNotIn("phase=ssusb_speed", s7a_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s7a_required)


if __name__ == "__main__":
    unittest.main()
