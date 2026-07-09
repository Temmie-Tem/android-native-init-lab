import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_13/manifest.json")
S10B_LABELS = ["S10B0", "S10B1", "S10B2", "S10B3", "S10B4", "S10B5", "S10B6"]
S10C_LABELS = ["S10C0"]
STAGE_LABELS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7A", "S7A2", "S8B1", "S8B1A", "S9", "S10A", *S10B_LABELS, *S10C_LABELS]


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
        self.assertEqual([stage.label for stage in stages], STAGE_LABELS)
        self.assertEqual([stage.number for stage in stages], list(range(1, 21)))
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
        self.assertTrue(by_label["S7A2"].configfs_gadget)
        self.assertTrue(by_label["S7A2"].udc_none)
        self.assertFalse(by_label["S7A2"].max_speed_high_speed)
        self.assertFalse(by_label["S7A2"].usb_role_force)
        self.assertFalse(by_label["S7A2"].ssusb_speed_high_speed)
        self.assertTrue(by_label["S7A2"].ssusb_mode_peripheral)
        self.assertTrue(by_label["S7A2"].udc_bind)
        self.assertFalse(by_label["S7A2"].soft_connect)
        self.assertTrue(by_label["S7A2"].stock_softdep_parity)
        self.assertTrue(by_label["S7A2"].qmp_module_included)
        self.assertTrue(by_label["S7A2"].eud_module_included)
        self.assertTrue(by_label["S7A2"].ucsi_glink_included)
        self.assertTrue(by_label["S7A2"].session_producer_parity)
        self.assertTrue(by_label["S7A2"].max77705_session_modules_included)
        self.assertTrue(by_label["S7A2"].typec_readback_markers)
        self.assertTrue(by_label["S7A2"].geni_i2c_transport_parity)
        self.assertTrue(by_label["S7A2"].typec_role_write_discriminator)
        self.assertFalse(by_label["S8B1"].configfs_gadget)
        self.assertFalse(by_label["S8B1"].udc_none)
        self.assertFalse(by_label["S8B1"].max_speed_high_speed)
        self.assertFalse(by_label["S8B1"].usb_role_force)
        self.assertFalse(by_label["S8B1"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S8B1"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S8B1"].udc_bind)
        self.assertFalse(by_label["S8B1"].soft_connect)
        self.assertTrue(by_label["S8B1"].stock_softdep_parity)
        self.assertTrue(by_label["S8B1"].qmp_module_included)
        self.assertTrue(by_label["S8B1"].eud_module_included)
        self.assertTrue(by_label["S8B1"].ucsi_glink_included)
        self.assertTrue(by_label["S8B1"].session_producer_parity)
        self.assertTrue(by_label["S8B1"].max77705_session_modules_included)
        self.assertFalse(by_label["S8B1"].typec_readback_markers)
        self.assertTrue(by_label["S8B1"].geni_i2c_transport_parity)
        self.assertFalse(by_label["S8B1"].typec_role_write_discriminator)
        self.assertEqual(by_label["S8B1"].beacon_probe, "typec_port_or_i2c_device")
        self.assertFalse(by_label["S8B1A"].configfs_gadget)
        self.assertFalse(by_label["S8B1A"].udc_none)
        self.assertFalse(by_label["S8B1A"].max_speed_high_speed)
        self.assertFalse(by_label["S8B1A"].usb_role_force)
        self.assertFalse(by_label["S8B1A"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S8B1A"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S8B1A"].udc_bind)
        self.assertFalse(by_label["S8B1A"].soft_connect)
        self.assertTrue(by_label["S8B1A"].stock_softdep_parity)
        self.assertTrue(by_label["S8B1A"].qmp_module_included)
        self.assertTrue(by_label["S8B1A"].eud_module_included)
        self.assertTrue(by_label["S8B1A"].ucsi_glink_included)
        self.assertTrue(by_label["S8B1A"].session_producer_parity)
        self.assertTrue(by_label["S8B1A"].max77705_session_modules_included)
        self.assertFalse(by_label["S8B1A"].typec_readback_markers)
        self.assertTrue(by_label["S8B1A"].geni_i2c_transport_parity)
        self.assertFalse(by_label["S8B1A"].typec_role_write_discriminator)
        self.assertEqual(by_label["S8B1A"].beacon_probe, "typec_port_or_i2c_any_0066")
        self.assertFalse(by_label["S8B1A"].devlink_supplier_closure)
        self.assertFalse(by_label["S9"].configfs_gadget)
        self.assertFalse(by_label["S9"].udc_none)
        self.assertFalse(by_label["S9"].max_speed_high_speed)
        self.assertFalse(by_label["S9"].usb_role_force)
        self.assertFalse(by_label["S9"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S9"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S9"].udc_bind)
        self.assertFalse(by_label["S9"].soft_connect)
        self.assertTrue(by_label["S9"].stock_softdep_parity)
        self.assertTrue(by_label["S9"].qmp_module_included)
        self.assertTrue(by_label["S9"].eud_module_included)
        self.assertTrue(by_label["S9"].ucsi_glink_included)
        self.assertTrue(by_label["S9"].session_producer_parity)
        self.assertTrue(by_label["S9"].max77705_session_modules_included)
        self.assertFalse(by_label["S9"].typec_readback_markers)
        self.assertTrue(by_label["S9"].geni_i2c_transport_parity)
        self.assertFalse(by_label["S9"].typec_role_write_discriminator)
        self.assertEqual(by_label["S9"].beacon_probe, "typec_port_or_i2c_any_0066")
        self.assertTrue(by_label["S9"].devlink_supplier_closure)
        self.assertFalse(by_label["S10A"].configfs_gadget)
        self.assertFalse(by_label["S10A"].udc_none)
        self.assertFalse(by_label["S10A"].max_speed_high_speed)
        self.assertFalse(by_label["S10A"].usb_role_force)
        self.assertFalse(by_label["S10A"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S10A"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S10A"].udc_bind)
        self.assertFalse(by_label["S10A"].soft_connect)
        self.assertTrue(by_label["S10A"].stock_softdep_parity)
        self.assertTrue(by_label["S10A"].qmp_module_included)
        self.assertTrue(by_label["S10A"].eud_module_included)
        self.assertTrue(by_label["S10A"].ucsi_glink_included)
        self.assertTrue(by_label["S10A"].session_producer_parity)
        self.assertTrue(by_label["S10A"].max77705_session_modules_included)
        self.assertFalse(by_label["S10A"].typec_readback_markers)
        self.assertTrue(by_label["S10A"].geni_i2c_transport_parity)
        self.assertFalse(by_label["S10A"].typec_role_write_discriminator)
        self.assertIsNone(by_label["S10A"].beacon_probe)
        self.assertEqual(by_label["S10A"].module_load_probe, "proc_modules_core_loaded")
        self.assertTrue(by_label["S10A"].devlink_supplier_closure)
        self.assertEqual(
            self.module.M34_S10B_PROC_MODULE_PREFIXES,
            [
                ("S10B0", 13, ["cmd_db"]),
                ("S10B1", 14, ["cmd_db", "qcom_rpmh"]),
                ("S10B2", 15, ["cmd_db", "qcom_rpmh", "gcc_waipio"]),
                ("S10B3", 16, ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc"]),
                ("S10B4", 17, ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc", "i2c_msm_geni"]),
                (
                    "S10B5",
                    18,
                    ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc", "i2c_msm_geni", "mfd_max77705"],
                ),
                ("S10B6", 19, self.module.M34_S10A_PROC_MODULES_CORE_NAMES),
            ],
        )
        for label, number, modules in self.module.M34_S10B_PROC_MODULE_PREFIXES:
            stage = by_label[label]
            self.assertEqual(stage.number, number)
            self.assertFalse(stage.configfs_gadget)
            self.assertFalse(stage.udc_none)
            self.assertFalse(stage.max_speed_high_speed)
            self.assertFalse(stage.usb_role_force)
            self.assertFalse(stage.ssusb_speed_high_speed)
            self.assertFalse(stage.ssusb_mode_peripheral)
            self.assertFalse(stage.udc_bind)
            self.assertFalse(stage.soft_connect)
            self.assertTrue(stage.stock_softdep_parity)
            self.assertTrue(stage.qmp_module_included)
            self.assertTrue(stage.eud_module_included)
            self.assertTrue(stage.ucsi_glink_included)
            self.assertTrue(stage.session_producer_parity)
            self.assertTrue(stage.max77705_session_modules_included)
            self.assertFalse(stage.typec_readback_markers)
            self.assertTrue(stage.geni_i2c_transport_parity)
            self.assertFalse(stage.typec_role_write_discriminator)
            self.assertIsNone(stage.beacon_probe)
            self.assertEqual(stage.module_load_probe, f"proc_modules_prefix_{len(modules)}")
            self.assertTrue(stage.devlink_supplier_closure)
        self.assertFalse(by_label["S10C0"].configfs_gadget)
        self.assertFalse(by_label["S10C0"].udc_none)
        self.assertFalse(by_label["S10C0"].max_speed_high_speed)
        self.assertFalse(by_label["S10C0"].usb_role_force)
        self.assertFalse(by_label["S10C0"].ssusb_speed_high_speed)
        self.assertFalse(by_label["S10C0"].ssusb_mode_peripheral)
        self.assertFalse(by_label["S10C0"].udc_bind)
        self.assertFalse(by_label["S10C0"].soft_connect)
        self.assertTrue(by_label["S10C0"].stock_softdep_parity)
        self.assertTrue(by_label["S10C0"].qmp_module_included)
        self.assertTrue(by_label["S10C0"].eud_module_included)
        self.assertTrue(by_label["S10C0"].ucsi_glink_included)
        self.assertTrue(by_label["S10C0"].session_producer_parity)
        self.assertTrue(by_label["S10C0"].max77705_session_modules_included)
        self.assertFalse(by_label["S10C0"].typec_readback_markers)
        self.assertTrue(by_label["S10C0"].geni_i2c_transport_parity)
        self.assertFalse(by_label["S10C0"].typec_role_write_discriminator)
        self.assertIsNone(by_label["S10C0"].beacon_probe)
        self.assertEqual(by_label["S10C0"].module_load_probe, "finit_cmd_db_accepted")
        self.assertTrue(by_label["S10C0"].devlink_supplier_closure)

    def test_source_has_stage_guards_and_no_unintended_reboot_syscall(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("#if M34_STAGE >= 2", text)
        self.assertIn("#if M34_STAGE >= 3", text)
        self.assertIn("#if M34_STAGE >= 4", text)
        self.assertIn("#if M34_STAGE == 5", text)
        self.assertIn("#elif M34_STAGE == 6", text)
        self.assertIn("#elif M34_STAGE == 7", text)
        self.assertIn("#elif M34_STAGE == 8", text)
        self.assertIn("#elif M34_STAGE == 9", text)
        self.assertIn("#elif M34_STAGE == 10", text)
        self.assertIn("#elif M34_STAGE == 11", text)
        self.assertIn("#elif M34_STAGE == 12", text)
        self.assertIn("#elif M34_STAGE >= 13 && M34_STAGE <= 19", text)
        self.assertIn("#elif M34_STAGE == 20", text)
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
        self.assertIn("maybe_force_typec_device_sink", text)
        self.assertIn("phase=typec_partner_check", text)
        self.assertIn("phase=typec_role_write", text)
        self.assertIn('"device"', text)
        self.assertIn('"sink"', text)
        self.assertIn('"connect"', text)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/speed", text)
        self.assertIn("/sys/devices/platform/soc/a600000.ssusb/mode", text)
        self.assertIn('"peripheral"', text)
        self.assertIn("/config/usb_gadget/g1/functions/ss_acm.0", text)
        self.assertIn("/config/usb_gadget/g1/UDC", text)
        self.assertIn("/config/usb_gadget/g1/max_speed", text)
        self.assertIn("s8_beacon_probe", text)
        self.assertIn("s8_b1_typec_port_or_i2c_present", text)
        self.assertIn("s8_b1a_typec_port_or_i2c_any_0066_present", text)
        self.assertIn("phase=s9_b1_probe", text)
        self.assertIn("phase=s10a_module_load_probe", text)
        self.assertIn("phase=s10b_module_load_prefix_probe", text)
        self.assertIn("phase=s10c_module_loader_audit_probe", text)
        self.assertIn("proc_modules_core_loaded", text)
        self.assertIn("proc_modules_prefix", text)
        self.assertIn("finit_cmd_db_accepted", text)
        self.assertIn("S10B_PREFIX_MODULES", text)
        self.assertIn("cmd-db.ko", text)
        self.assertIn("cmd_db_rc=", text)
        self.assertIn("/proc/modules", text)
        self.assertIn("cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni,mfd_max77705,pdic_max77705", text)
        self.assertIn("devlink_supplier_closure=1", text)
        self.assertIn("substrate_load_set=waipio_devlink", text)
        self.assertIn("gcc_waipio=1", text)
        self.assertIn("manual_power_write=0", text)
        self.assertIn("/sys/bus/i2c/devices/57-0066", text)
        self.assertIn("/sys/bus/i2c/devices", text)
        self.assertIn("*-0066", text)
        self.assertIn("reboot_request=download", text)
        self.assertIn("download_beacon=1", text)
        self.assertIn("NR_REBOOT 142", text)
        self.assertIn("LINUX_REBOOT_CMD_RESTART2", text)
        self.assertIn("sys_reboot_download", text)
        self.assertIn("0x04E8", text)
        self.assertIn("0x0200", text)
        self.assertIn("900", text)
        self.assertIn("\"none\"", text)
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
        built_labels = [stage["label"] for stage in manifest["stages"]]
        self.assertEqual(manifest["target"], "SM-S906N/g0q/S906NKSS7FYG8")
        self.assertEqual(built_labels, manifest["matrix"]["host_build_order"])
        self.assertTrue(set(built_labels).issubset(set(STAGE_LABELS)))
        self.assertTrue(manifest["matrix"]["p30_is_s0"])
        self.assertEqual(manifest["matrix"]["live_order"], ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertEqual(manifest["matrix"]["next_host_only_candidate"], "S10C0")
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
        self.assertTrue(manifest["matrix"]["s7a2_closes_missing_geni_i2c_transport"])
        self.assertEqual(manifest["matrix"]["s7a2_geni_i2c_transport_targets"], ["gpi.ko", "msm-geni-se.ko", "i2c-msm-geni.ko"])
        self.assertEqual(manifest["matrix"]["s7a2_geni_i2c_transport_order_actual"], ["msm-geni-se.ko", "gpi.ko", "i2c-msm-geni.ko"])
        self.assertTrue(manifest["matrix"]["s7a2_typec_role_write_discriminator"])
        self.assertEqual(manifest["matrix"]["s8b1_download_beacon_probe"], "typec_port_or_i2c_device")
        self.assertEqual(manifest["matrix"]["s8b1_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s8b1_false_action"], "park")
        self.assertEqual(manifest["matrix"]["s8b1_probe_paths"], ["/sys/class/typec/port0", "/sys/bus/i2c/devices/57-0066"])
        self.assertTrue(manifest["matrix"]["s8b1_keeps_s7a2_module_recipe"])
        self.assertTrue(manifest["matrix"]["s8b1_skips_downstream_configfs_and_udc_to_isolate_probe"])
        self.assertEqual(manifest["matrix"]["s8b1a_download_beacon_probe"], "typec_port_or_i2c_any_0066")
        self.assertEqual(manifest["matrix"]["s8b1a_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s8b1a_false_action"], "park")
        self.assertEqual(manifest["matrix"]["s8b1a_probe_paths"], ["/sys/class/typec/port0", "/sys/bus/i2c/devices/*-0066"])
        self.assertTrue(manifest["matrix"]["s8b1a_keeps_s7a2_module_recipe"])
        self.assertTrue(manifest["matrix"]["s8b1a_widens_i2c_adapter_number_assumption"])
        self.assertTrue(manifest["matrix"]["s8b1a_skips_downstream_configfs_and_udc_to_isolate_probe"])
        self.assertEqual(manifest["matrix"]["s9_download_beacon_probe"], "typec_port_or_i2c_any_0066")
        self.assertEqual(manifest["matrix"]["s9_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s9_false_action"], "park")
        self.assertEqual(manifest["matrix"]["s9_probe_paths"], ["/sys/class/typec/port0", "/sys/bus/i2c/devices/*-0066"])
        self.assertTrue(manifest["matrix"]["s9_starts_from_s8b1a_b1_recipe"])
        self.assertTrue(manifest["matrix"]["s9_closes_devlink_supplier_substrate"])
        self.assertEqual(manifest["matrix"]["s9_devlink_supplier_load_set"], self.module.M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
        self.assertEqual(manifest["matrix"]["s9_devlink_supplier_targets"], self.module.M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
        self.assertEqual(manifest["matrix"]["s9_devlink_supplier_new_modules"], ["qcom-pdc.ko", "pinctrl-msm.ko", "pinctrl-waipio.ko"])
        self.assertTrue(manifest["matrix"]["s9_skips_downstream_configfs_and_udc_to_isolate_probe"])
        self.assertEqual(manifest["matrix"]["s10a_module_load_probe"], "proc_modules_core_loaded")
        self.assertEqual(manifest["matrix"]["s10a_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s10a_false_action"], "park")
        self.assertEqual(manifest["matrix"]["s10a_core_proc_modules"], self.module.M34_S10A_PROC_MODULES_CORE_NAMES)
        self.assertTrue(manifest["matrix"]["s10a_starts_from_s9_module_recipe"])
        self.assertTrue(manifest["matrix"]["s10a_separates_module_load_from_probe_bind_failure"])
        self.assertTrue(manifest["matrix"]["s10a_skips_downstream_configfs_and_udc_to_isolate_module_load"])
        expected_s10b_ladder = [
            {
                "label": label,
                "stage_number": number,
                "module_load_probe": f"proc_modules_prefix_{len(modules)}",
                "prefix_index": index,
                "prefix_expected": len(modules),
                "prefix_modules": modules,
            }
            for index, (label, number, modules) in enumerate(self.module.M34_S10B_PROC_MODULE_PREFIXES)
        ]
        self.assertEqual(manifest["matrix"]["s10b_module_load_prefix_ladder"], expected_s10b_ladder)
        self.assertEqual(manifest["matrix"]["s10b_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s10b_false_action"], "park")
        self.assertTrue(manifest["matrix"]["s10b_starts_from_s9_module_recipe"])
        self.assertTrue(manifest["matrix"]["s10b_bisects_s10a_all_core_miss"])
        self.assertTrue(manifest["matrix"]["s10b_skips_downstream_configfs_and_udc_to_isolate_module_load"])
        self.assertEqual(manifest["matrix"]["s10c0_module_load_probe"], "finit_cmd_db_accepted")
        self.assertEqual(manifest["matrix"]["s10c0_probe_module"], "cmd-db.ko")
        self.assertEqual(manifest["matrix"]["s10c0_probe_proc_name"], "cmd_db")
        self.assertEqual(manifest["matrix"]["s10c0_true_action"], "reboot(download)")
        self.assertEqual(manifest["matrix"]["s10c0_false_action"], "park")
        self.assertTrue(manifest["matrix"]["s10c0_starts_from_s9_module_recipe"])
        self.assertTrue(manifest["matrix"]["s10c0_avoids_proc_modules_dependency"])
        self.assertTrue(manifest["matrix"]["s10c0_uses_direct_finit_module_rc"])
        self.assertTrue(manifest["matrix"]["s10c0_beacon_hit_means_cmd_db_finit_accepted"])
        self.assertTrue(manifest["matrix"]["s10c0_skips_downstream_configfs_and_udc_to_isolate_module_load"])
        self.assertFalse(manifest["safety"]["live_flash_authorized"])
        self.assertTrue(manifest["safety"]["requires_new_sha_pinned_agents_exception_before_flash"])
        self.assertTrue(manifest["safety"]["requires_s7a_specific_live_risk_review"])
        self.assertEqual(manifest["safety"]["runtime_module_list_buffer_bytes"], self.module.RUNTIME_MODULES_LOAD_BUF)
        self.assertEqual(manifest["safety"]["auto_reboot"], "download-if-probe-true")
        self.assertTrue(manifest["safety"]["intended_reboot_syscall"])
        self.assertEqual(manifest["safety"]["reboot_request"], "download-if-probe-true")
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
        self.assertTrue(manifest["safety"]["stage_s7a2_starts_from_s7a"])
        self.assertTrue(manifest["safety"]["stage_s7a2_adds_geni_i2c_transport"])
        self.assertTrue(manifest["safety"]["stage_s7a2_role_write_discriminator_if_no_partner"])
        self.assertTrue(manifest["safety"]["stage_s7a2_no_soft_connect"])
        self.assertTrue(manifest["safety"]["stage_s8b1_starts_from_s7a2_module_recipe"])
        self.assertEqual(manifest["safety"]["stage_s8b1_beacon_probe"], "typec_port_or_i2c_device")
        self.assertTrue(manifest["safety"]["stage_s8b1_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s8b1_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s8b1a_starts_from_s7a2_module_recipe"])
        self.assertEqual(manifest["safety"]["stage_s8b1a_beacon_probe"], "typec_port_or_i2c_any_0066")
        self.assertTrue(manifest["safety"]["stage_s8b1a_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s8b1a_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s8b1a_widens_i2c_adapter_number_assumption"])
        self.assertTrue(manifest["safety"]["stage_s9_starts_from_s8b1a_b1_recipe"])
        self.assertTrue(manifest["safety"]["stage_s9_closes_devlink_supplier_substrate"])
        self.assertEqual(manifest["safety"]["stage_s9_beacon_probe"], "typec_port_or_i2c_any_0066")
        self.assertTrue(manifest["safety"]["stage_s9_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s9_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s9_driver_load_only_no_manual_power_write"])
        self.assertTrue(manifest["safety"]["stage_s10a_starts_from_s9_module_recipe"])
        self.assertEqual(manifest["safety"]["stage_s10a_module_load_probe"], "proc_modules_core_loaded")
        self.assertEqual(manifest["safety"]["stage_s10a_core_proc_modules"], self.module.M34_S10A_PROC_MODULES_CORE_NAMES)
        self.assertTrue(manifest["safety"]["stage_s10a_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s10a_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s10a_driver_load_only_no_manual_power_write"])
        self.assertTrue(manifest["safety"]["stage_s10a_separates_module_load_from_probe_bind_failure"])
        self.assertTrue(manifest["safety"]["stage_s10b_starts_from_s9_module_recipe"])
        self.assertEqual(manifest["safety"]["stage_s10b_module_load_prefix_ladder"], expected_s10b_ladder)
        self.assertTrue(manifest["safety"]["stage_s10b_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s10b_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s10b_driver_load_only_no_manual_power_write"])
        self.assertTrue(manifest["safety"]["stage_s10b_bisects_s10a_all_core_miss"])
        self.assertTrue(manifest["safety"]["stage_s10c0_starts_from_s9_module_recipe"])
        self.assertEqual(manifest["safety"]["stage_s10c0_module_load_probe"], "finit_cmd_db_accepted")
        self.assertEqual(manifest["safety"]["stage_s10c0_probe_module"], "cmd-db.ko")
        self.assertTrue(manifest["safety"]["stage_s10c0_true_reboot_download_false_park"])
        self.assertTrue(manifest["safety"]["stage_s10c0_no_proc_modules_dependency"])
        self.assertTrue(manifest["safety"]["stage_s10c0_no_configfs_udc_or_role_write"])
        self.assertTrue(manifest["safety"]["stage_s10c0_driver_load_only_no_manual_power_write"])

        by_label = {stage["label"]: stage for stage in manifest["stages"]}
        if built_labels != STAGE_LABELS:
            self.assertEqual(built_labels, ["S10C0"])
            s10c0 = by_label["S10C0"]
            self.assertEqual(s10c0["hashes"]["base_boot"], "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e")
            self.assertEqual(s10c0["hashes"]["m34_modules"], "c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26")
            self.assertEqual(s10c0["stage_number"], 20)
            self.assertEqual(s10c0["tar_members"], ["boot.img.lz4"])
            self.assertEqual(s10c0["ramdisk"]["module_files_injected_into_boot_ramdisk"], 0)
            self.assertEqual(s10c0["ramdisk"]["module_list_files_injected_into_boot_ramdisk"], 1)
            self.assertEqual(s10c0["closure"]["module_count"], 89)
            self.assertIn("cmd-db.ko", s10c0["closure"]["modules"])
            self.assertIn("sec_debug_region.ko", s10c0["closure"]["modules"])
            s10c0_required = set(s10c0["init"]["required_strings"])
            self.assertIn("version=0.11", s10c0_required)
            self.assertIn("module_load_probe=finit_cmd_db_accepted", s10c0_required)
            self.assertIn("proc_modules=0", s10c0_required)
            self.assertIn("direct_finit_rc=1", s10c0_required)
            self.assertIn("probe_module=cmd-db.ko", s10c0_required)
            self.assertIn("phase=s10c_module_loader_audit_probe", s10c0_required)
            self.assertIn("predicate=cmd_db_finit_accepted", s10c0_required)
            self.assertIn("cmd_db_rc=", s10c0_required)
            self.assertIn("true_action=reboot_download", s10c0_required)
            self.assertIn("false_action=park", s10c0_required)
            self.assertNotIn("/proc/modules", s10c0_required)
            return
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
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
                "geni_i2c_transport_parity": False,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": None,
            },
        )
        self.assertEqual(
            by_label["S7A2"]["runtime_steps"],
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
                "geni_i2c_transport_parity": True,
                "typec_role_write_discriminator": True,
                "beacon_probe": None,
                "module_load_probe": None,
            },
        )
        self.assertEqual(
            by_label["S8B1"]["runtime_steps"],
            {
                "configfs_gadget": False,
                "udc_none": False,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": True,
                "max77705_session_modules_included": True,
                "typec_readback_markers": False,
                "geni_i2c_transport_parity": True,
                "typec_role_write_discriminator": False,
                "beacon_probe": "typec_port_or_i2c_device",
                "module_load_probe": None,
            },
        )
        self.assertEqual(
            by_label["S8B1A"]["runtime_steps"],
            {
                "configfs_gadget": False,
                "udc_none": False,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": True,
                "max77705_session_modules_included": True,
                "typec_readback_markers": False,
                "geni_i2c_transport_parity": True,
                "typec_role_write_discriminator": False,
                "beacon_probe": "typec_port_or_i2c_any_0066",
                "module_load_probe": None,
            },
        )
        self.assertEqual(
            by_label["S9"]["runtime_steps"],
            {
                "configfs_gadget": False,
                "udc_none": False,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": True,
                "max77705_session_modules_included": True,
                "typec_readback_markers": False,
                "geni_i2c_transport_parity": True,
                "typec_role_write_discriminator": False,
                "beacon_probe": "typec_port_or_i2c_any_0066",
                "module_load_probe": None,
            },
        )
        self.assertEqual(
            by_label["S10A"]["runtime_steps"],
            {
                "configfs_gadget": False,
                "udc_none": False,
                "max_speed_high_speed": False,
                "usb_role_force": False,
                "ssusb_speed_high_speed": False,
                "ssusb_mode_peripheral": False,
                "udc_bind": False,
                "soft_connect": False,
                "stock_softdep_parity": True,
                "qmp_module_included": True,
                "eud_module_included": True,
                "ucsi_glink_included": True,
                "session_producer_parity": True,
                "max77705_session_modules_included": True,
                "typec_readback_markers": False,
                "geni_i2c_transport_parity": True,
                "typec_role_write_discriminator": False,
                "beacon_probe": None,
                "module_load_probe": "proc_modules_core_loaded",
            },
        )
        for label, _number, modules in self.module.M34_S10B_PROC_MODULE_PREFIXES:
            self.assertEqual(
                by_label[label]["runtime_steps"],
                {
                    "configfs_gadget": False,
                    "udc_none": False,
                    "max_speed_high_speed": False,
                    "usb_role_force": False,
                    "ssusb_speed_high_speed": False,
                    "ssusb_mode_peripheral": False,
                    "udc_bind": False,
                    "soft_connect": False,
                    "stock_softdep_parity": True,
                    "qmp_module_included": True,
                    "eud_module_included": True,
                    "ucsi_glink_included": True,
                    "session_producer_parity": True,
                    "max77705_session_modules_included": True,
                    "typec_readback_markers": False,
                    "geni_i2c_transport_parity": True,
                    "typec_role_write_discriminator": False,
                    "beacon_probe": None,
                    "module_load_probe": f"proc_modules_prefix_{len(modules)}",
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
            elif stage["label"] == "S7A2":
                self.assertEqual(stage["closure"]["module_count"], 86)
                self.assertEqual(stage["closure"]["geni_i2c_transport_targets"], ["gpi.ko", "msm-geni-se.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["geni_i2c_transport_order_actual"], ["msm-geni-se.ko", "gpi.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["session_producer_targets"], self.module.M34_S7A_SESSION_PRODUCER_TARGETS)
                self.assertEqual(stage["closure"]["additional_new_modules"], self.module.M34_S7A2_EXPECTED_NEW_MODULES)
                self.assertIn("msm-geni-se.ko", stage["closure"]["modules"])
                self.assertIn("gpi.ko", stage["closure"]["modules"])
                self.assertIn("i2c-msm-geni.ko", stage["closure"]["modules"])
                self.assertIn("qcom-i2c-pmic.ko", stage["closure"]["modules"])
                self.assertIn("mfd_max77705.ko", stage["closure"]["modules"])
                self.assertIn("pdic_max77705.ko", stage["closure"]["modules"])
                self.assertLess(stage["closure"]["modules"].index("i2c-msm-geni.ko"), stage["closure"]["modules"].index("pdic_max77705.ko"))
                self.assertIn("sec_debug_region.ko", stage["closure"]["modules"])
                self.assertTrue(stage["closure"]["contains_sec_debug_region"])
                self.assertTrue(stage["closure"]["requires_live_risk_review"])
                self.assertIn("sec_debug_region.ko", stage["closure"]["risk_modules"])
            elif stage["label"] in ("S8B1", "S8B1A"):
                self.assertEqual(stage["closure"]["module_count"], 86)
                self.assertEqual(stage["closure"]["geni_i2c_transport_targets"], ["gpi.ko", "msm-geni-se.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["geni_i2c_transport_order_actual"], ["msm-geni-se.ko", "gpi.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["session_producer_targets"], self.module.M34_S7A_SESSION_PRODUCER_TARGETS)
                self.assertEqual(stage["closure"]["additional_new_modules"], self.module.M34_S7A2_EXPECTED_NEW_MODULES)
                self.assertIn("msm-geni-se.ko", stage["closure"]["modules"])
                self.assertIn("gpi.ko", stage["closure"]["modules"])
                self.assertIn("i2c-msm-geni.ko", stage["closure"]["modules"])
                self.assertIn("qcom-i2c-pmic.ko", stage["closure"]["modules"])
                self.assertIn("mfd_max77705.ko", stage["closure"]["modules"])
                self.assertIn("pdic_max77705.ko", stage["closure"]["modules"])
                self.assertLess(stage["closure"]["modules"].index("i2c-msm-geni.ko"), stage["closure"]["modules"].index("pdic_max77705.ko"))
                self.assertIn("sec_debug_region.ko", stage["closure"]["modules"])
                self.assertTrue(stage["closure"]["contains_sec_debug_region"])
                self.assertTrue(stage["closure"]["requires_live_risk_review"])
                self.assertIn("sec_debug_region.ko", stage["closure"]["risk_modules"])
            elif stage["label"] in ("S9", "S10A", *S10B_LABELS):
                self.assertEqual(stage["closure"]["module_count"], 89)
                self.assertEqual(stage["closure"]["geni_i2c_transport_targets"], ["gpi.ko", "msm-geni-se.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["geni_i2c_transport_order_actual"], ["msm-geni-se.ko", "gpi.ko", "i2c-msm-geni.ko"])
                self.assertEqual(stage["closure"]["session_producer_targets"], self.module.M34_S7A_SESSION_PRODUCER_TARGETS)
                self.assertEqual(stage["closure"]["devlink_supplier_load_set"], self.module.M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
                self.assertEqual(stage["closure"]["devlink_supplier_targets"], self.module.M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
                self.assertEqual(stage["closure"]["additional_new_modules"], self.module.M34_S9_EXPECTED_NEW_MODULES)
                self.assertEqual(stage["closure"]["devlink_supplier_new_modules"], self.module.M34_S9_EXPECTED_NEW_MODULES)
                self.assertEqual(
                    stage["closure"]["devlink_supplier_order_actual"],
                    [
                        "qcom_rpmh.ko",
                        "clk-rpmh.ko",
                        "gdsc-regulator.ko",
                        "clk-qcom.ko",
                        "gcc-waipio.ko",
                        "icc-bcm-voter.ko",
                        "icc-rpmh.ko",
                        "qcom-pdc.ko",
                        "rpmh-regulator.ko",
                        "pinctrl-msm.ko",
                        "pinctrl-waipio.ko",
                        "qnoc-waipio.ko",
                        "arm_smmu.ko",
                    ],
                )
                self.assertEqual(
                    stage["closure"]["devlink_supplier_already_present_modules"],
                    [
                        "clk-qcom.ko",
                        "qcom_rpmh.ko",
                        "icc-rpmh.ko",
                        "icc-bcm-voter.ko",
                        "gcc-waipio.ko",
                        "clk-rpmh.ko",
                        "rpmh-regulator.ko",
                        "gdsc-regulator.ko",
                        "qnoc-waipio.ko",
                        "arm_smmu.ko",
                    ],
                )
                self.assertIn("clk-qcom.ko", stage["closure"]["modules"])
                self.assertIn("qcom_rpmh.ko", stage["closure"]["modules"])
                self.assertIn("qcom-pdc.ko", stage["closure"]["modules"])
                self.assertIn("pinctrl-msm.ko", stage["closure"]["modules"])
                self.assertIn("pinctrl-waipio.ko", stage["closure"]["modules"])
                self.assertIn("arm_smmu.ko", stage["closure"]["modules"])
                self.assertIn("gcc-waipio.ko", stage["closure"]["modules"])
                self.assertIn("rpmh-regulator.ko", stage["closure"]["modules"])
                self.assertIn("qnoc-waipio.ko", stage["closure"]["modules"])
                self.assertIn("i2c-msm-geni.ko", stage["closure"]["modules"])
                self.assertIn("pdic_max77705.ko", stage["closure"]["modules"])
                self.assertLess(stage["closure"]["modules"].index("qcom-pdc.ko"), stage["closure"]["modules"].index("msm-geni-se.ko"))
                self.assertLess(stage["closure"]["modules"].index("pinctrl-waipio.ko"), stage["closure"]["modules"].index("msm-geni-se.ko"))
                self.assertLess(stage["closure"]["modules"].index("i2c-msm-geni.ko"), stage["closure"]["modules"].index("pdic_max77705.ko"))
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
        s7a2_required = set(by_label["S7A2"]["init"]["required_strings"])
        s8b1_required = set(by_label["S8B1"]["init"]["required_strings"])
        s8b1a_required = set(by_label["S8B1A"]["init"]["required_strings"])
        s9_required = set(by_label["S9"]["init"]["required_strings"])
        s10a_required = set(by_label["S10A"]["init"]["required_strings"])
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
        self.assertIn("session_producer_parity=1", s7a2_required)
        self.assertIn("max77705_session=1", s7a2_required)
        self.assertIn("typec_readback=1", s7a2_required)
        self.assertIn("functionfs=0", s7a2_required)
        self.assertIn("stock_composite=0", s7a2_required)
        self.assertIn("geni_i2c_transport=1", s7a2_required)
        self.assertIn("i2c_msm_geni=1", s7a2_required)
        self.assertIn("gpi_dma=1", s7a2_required)
        self.assertIn("msm_geni_se=1", s7a2_required)
        self.assertIn("role_write_discriminator=1", s7a2_required)
        self.assertIn("phase=typec_partner_check", s7a2_required)
        self.assertIn("phase=typec_role_write", s7a2_required)
        self.assertIn("role_device_rc=", s7a2_required)
        self.assertIn("role_sink_rc=", s7a2_required)
        self.assertIn("/sys/class/typec/port0/data_role", s7a2_required)
        self.assertIn("/sys/class/typec/port0/power_role", s7a2_required)
        self.assertIn("device", s7a2_required)
        self.assertIn("sink", s7a2_required)
        self.assertIn("a600000.dwc3", s7a2_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s7a2_required)
        self.assertNotIn("high-speed", s7a2_required)
        self.assertNotIn("phase=ssusb_speed", s7a2_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s7a2_required)
        self.assertIn("version=0.8", s8b1_required)
        self.assertIn("configfs_gadget=0", s8b1_required)
        self.assertIn("stock_order=0", s8b1_required)
        self.assertIn("udc_none=0", s8b1_required)
        self.assertIn("udc_bind=0", s8b1_required)
        self.assertIn("role_force=0", s8b1_required)
        self.assertIn("typec_readback=0", s8b1_required)
        self.assertIn("role_write_discriminator=0", s8b1_required)
        self.assertIn("session_producer_parity=1", s8b1_required)
        self.assertIn("max77705_session=1", s8b1_required)
        self.assertIn("geni_i2c_transport=1", s8b1_required)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_device", s8b1_required)
        self.assertIn("b1=1", s8b1_required)
        self.assertIn("reboot_request=download", s8b1_required)
        self.assertIn("download_beacon=1", s8b1_required)
        self.assertIn("phase=s8_b1_probe", s8b1_required)
        self.assertIn("predicate=typec_port_or_i2c_device", s8b1_required)
        self.assertIn("true_action=reboot_download", s8b1_required)
        self.assertIn("false_action=park", s8b1_required)
        self.assertIn("/sys/class/typec/port0", s8b1_required)
        self.assertIn("/sys/bus/i2c/devices/57-0066", s8b1_required)
        self.assertIn("download", s8b1_required)
        self.assertNotIn("/config/usb_gadget/g1/functions/ss_acm.0", s8b1_required)
        self.assertNotIn("phase=configfs_done", s8b1_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s8b1_required)
        self.assertNotIn("phase=max_speed", s8b1_required)
        self.assertNotIn("high-speed", s8b1_required)
        self.assertNotIn("/sys/class/usb_role", s8b1_required)
        self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/mode", s8b1_required)
        self.assertNotIn("phase=ssusb_mode", s8b1_required)
        self.assertNotIn("/config/usb_gadget/g1/UDC", s8b1_required)
        self.assertNotIn("/sys/class/udc", s8b1_required)
        self.assertNotIn("a600000.dwc3", s8b1_required)
        self.assertNotIn("phase=udc_bind", s8b1_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s8b1_required)
        self.assertNotIn("phase=typec_role_write", s8b1_required)
        self.assertIn("version=0.8", s8b1a_required)
        self.assertIn("configfs_gadget=0", s8b1a_required)
        self.assertIn("stock_order=0", s8b1a_required)
        self.assertIn("udc_none=0", s8b1a_required)
        self.assertIn("udc_bind=0", s8b1a_required)
        self.assertIn("role_force=0", s8b1a_required)
        self.assertIn("typec_readback=0", s8b1a_required)
        self.assertIn("role_write_discriminator=0", s8b1a_required)
        self.assertIn("session_producer_parity=1", s8b1a_required)
        self.assertIn("max77705_session=1", s8b1a_required)
        self.assertIn("geni_i2c_transport=1", s8b1a_required)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_any_0066", s8b1a_required)
        self.assertIn("b1a=1", s8b1a_required)
        self.assertIn("reboot_request=download", s8b1a_required)
        self.assertIn("download_beacon=1", s8b1a_required)
        self.assertIn("phase=s8_b1a_probe", s8b1a_required)
        self.assertIn("predicate=typec_port_or_i2c_any_0066", s8b1a_required)
        self.assertIn("true_action=reboot_download", s8b1a_required)
        self.assertIn("false_action=park", s8b1a_required)
        self.assertIn("/sys/class/typec/port0", s8b1a_required)
        self.assertIn("/sys/bus/i2c/devices", s8b1a_required)
        self.assertIn("*-0066", s8b1a_required)
        self.assertIn("download", s8b1a_required)
        self.assertNotIn("/sys/bus/i2c/devices/57-0066", s8b1a_required)
        self.assertNotIn("/config/usb_gadget/g1/functions/ss_acm.0", s8b1a_required)
        self.assertNotIn("phase=configfs_done", s8b1a_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s8b1a_required)
        self.assertNotIn("phase=max_speed", s8b1a_required)
        self.assertNotIn("high-speed", s8b1a_required)
        self.assertNotIn("/sys/class/usb_role", s8b1a_required)
        self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/mode", s8b1a_required)
        self.assertNotIn("phase=ssusb_mode", s8b1a_required)
        self.assertNotIn("/config/usb_gadget/g1/UDC", s8b1a_required)
        self.assertNotIn("/sys/class/udc", s8b1a_required)
        self.assertNotIn("a600000.dwc3", s8b1a_required)
        self.assertNotIn("phase=udc_bind", s8b1a_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s8b1a_required)
        self.assertNotIn("phase=typec_role_write", s8b1a_required)
        self.assertIn("version=0.8", s9_required)
        self.assertIn("configfs_gadget=0", s9_required)
        self.assertIn("stock_order=0", s9_required)
        self.assertIn("udc_none=0", s9_required)
        self.assertIn("udc_bind=0", s9_required)
        self.assertIn("role_force=0", s9_required)
        self.assertIn("typec_readback=0", s9_required)
        self.assertIn("role_write_discriminator=0", s9_required)
        self.assertIn("session_producer_parity=1", s9_required)
        self.assertIn("max77705_session=1", s9_required)
        self.assertIn("geni_i2c_transport=1", s9_required)
        self.assertIn("devlink_supplier_closure=1", s9_required)
        self.assertIn("substrate_load_set=waipio_devlink", s9_required)
        self.assertIn("clk_qcom=1", s9_required)
        self.assertIn("qcom_rpmh=1", s9_required)
        self.assertIn("icc_rpmh=1", s9_required)
        self.assertIn("icc_bcm_voter=1", s9_required)
        self.assertIn("gcc_waipio=1", s9_required)
        self.assertIn("clk_rpmh=1", s9_required)
        self.assertIn("rpmh_regulator=1", s9_required)
        self.assertIn("gdsc_regulator=1", s9_required)
        self.assertIn("qnoc_waipio=1", s9_required)
        self.assertIn("arm_smmu=1", s9_required)
        self.assertIn("qcom_pdc=1", s9_required)
        self.assertIn("pinctrl_msm=1", s9_required)
        self.assertIn("pinctrl_waipio=1", s9_required)
        self.assertIn("driver_load_only=1", s9_required)
        self.assertIn("manual_power_write=0", s9_required)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_any_0066", s9_required)
        self.assertIn("s9_b1=1", s9_required)
        self.assertIn("reboot_request=download", s9_required)
        self.assertIn("download_beacon=1", s9_required)
        self.assertIn("phase=s9_b1_probe", s9_required)
        self.assertIn("predicate=typec_port_or_i2c_any_0066", s9_required)
        self.assertIn("true_action=reboot_download", s9_required)
        self.assertIn("false_action=park", s9_required)
        self.assertIn("/sys/class/typec/port0", s9_required)
        self.assertIn("/sys/bus/i2c/devices", s9_required)
        self.assertIn("*-0066", s9_required)
        self.assertIn("download", s9_required)
        self.assertNotIn("/sys/bus/i2c/devices/57-0066", s9_required)
        self.assertNotIn("phase=s8_b1a_probe", s9_required)
        self.assertNotIn("/config/usb_gadget/g1/functions/ss_acm.0", s9_required)
        self.assertNotIn("phase=configfs_done", s9_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s9_required)
        self.assertNotIn("phase=max_speed", s9_required)
        self.assertNotIn("high-speed", s9_required)
        self.assertNotIn("/sys/class/usb_role", s9_required)
        self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/mode", s9_required)
        self.assertNotIn("phase=ssusb_mode", s9_required)
        self.assertNotIn("/config/usb_gadget/g1/UDC", s9_required)
        self.assertNotIn("/sys/class/udc", s9_required)
        self.assertNotIn("a600000.dwc3", s9_required)
        self.assertNotIn("phase=udc_bind", s9_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s9_required)
        self.assertNotIn("phase=typec_role_write", s9_required)
        self.assertIn("version=0.9", s10a_required)
        self.assertIn("configfs_gadget=0", s10a_required)
        self.assertIn("stock_order=0", s10a_required)
        self.assertIn("udc_none=0", s10a_required)
        self.assertIn("udc_bind=0", s10a_required)
        self.assertIn("role_force=0", s10a_required)
        self.assertIn("typec_readback=0", s10a_required)
        self.assertIn("role_write_discriminator=0", s10a_required)
        self.assertIn("session_producer_parity=1", s10a_required)
        self.assertIn("max77705_session=1", s10a_required)
        self.assertIn("geni_i2c_transport=1", s10a_required)
        self.assertIn("devlink_supplier_closure=1", s10a_required)
        self.assertIn("both_graphs_closure=1", s10a_required)
        self.assertIn("module_load_probe=proc_modules_core_loaded", s10a_required)
        self.assertIn("s10a_module_load_probe=1", s10a_required)
        self.assertIn("proc_modules=1", s10a_required)
        self.assertIn("core_module_count=8", s10a_required)
        self.assertIn("core_modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni,mfd_max77705,pdic_max77705", s10a_required)
        self.assertIn("cmd_db=1", s10a_required)
        self.assertIn("smem=1", s10a_required)
        self.assertIn("qcom_scm=1", s10a_required)
        self.assertIn("qcom_ipc_logging=1", s10a_required)
        self.assertIn("reboot_request=download", s10a_required)
        self.assertIn("download_beacon=1", s10a_required)
        self.assertIn("phase=s10a_module_load_probe", s10a_required)
        self.assertIn("predicate=proc_modules_core_loaded", s10a_required)
        self.assertIn("loaded_count=", s10a_required)
        self.assertIn("expected=8", s10a_required)
        self.assertIn("modules=cmd_db,qcom_rpmh,gcc_waipio,pinctrl_waipio,qcom_pdc,i2c_msm_geni,mfd_max77705,pdic_max77705", s10a_required)
        self.assertIn("true_action=reboot_download", s10a_required)
        self.assertIn("false_action=park", s10a_required)
        self.assertIn("phase=s10a_module_load_reboot_returned", s10a_required)
        self.assertIn("/proc/modules", s10a_required)
        self.assertIn("download", s10a_required)
        self.assertNotIn("s8_beacon_probe=typec_port_or_i2c_any_0066", s10a_required)
        self.assertNotIn("phase=s9_b1_probe", s10a_required)
        self.assertNotIn("phase=s8_b1a_probe", s10a_required)
        self.assertNotIn("/sys/bus/i2c/devices", s10a_required)
        self.assertNotIn("/sys/class/typec/port0", s10a_required)
        self.assertNotIn("/config/usb_gadget/g1/functions/ss_acm.0", s10a_required)
        self.assertNotIn("phase=configfs_done", s10a_required)
        self.assertNotIn("/config/usb_gadget/g1/max_speed", s10a_required)
        self.assertNotIn("phase=max_speed", s10a_required)
        self.assertNotIn("high-speed", s10a_required)
        self.assertNotIn("/sys/class/usb_role", s10a_required)
        self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/mode", s10a_required)
        self.assertNotIn("phase=ssusb_mode", s10a_required)
        self.assertNotIn("/config/usb_gadget/g1/UDC", s10a_required)
        self.assertNotIn("/sys/class/udc", s10a_required)
        self.assertNotIn("a600000.dwc3", s10a_required)
        self.assertNotIn("phase=udc_bind", s10a_required)
        self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", s10a_required)
        self.assertNotIn("phase=typec_role_write", s10a_required)
        for index, (label, _number, modules) in enumerate(self.module.M34_S10B_PROC_MODULE_PREFIXES):
            required = set(by_label[label]["init"]["required_strings"])
            modules_csv = ",".join(modules)
            self.assertIn("version=0.10", required)
            self.assertIn("configfs_gadget=0", required)
            self.assertIn("stock_order=0", required)
            self.assertIn("udc_none=0", required)
            self.assertIn("udc_bind=0", required)
            self.assertIn("role_force=0", required)
            self.assertIn("typec_readback=0", required)
            self.assertIn("role_write_discriminator=0", required)
            self.assertIn("session_producer_parity=1", required)
            self.assertIn("max77705_session=1", required)
            self.assertIn("geni_i2c_transport=1", required)
            self.assertIn("devlink_supplier_closure=1", required)
            self.assertIn("both_graphs_closure=1", required)
            self.assertIn(f"module_load_probe=proc_modules_prefix_{len(modules)}", required)
            self.assertIn("s10b_module_load_prefix_probe=1", required)
            self.assertIn("proc_modules=1", required)
            self.assertIn("s10b_ladder=1", required)
            self.assertIn(f"prefix_index={index}", required)
            self.assertIn(f"prefix_expected={len(modules)}", required)
            self.assertIn(f"prefix_modules={modules_csv}", required)
            self.assertIn("cmd_db=1", required)
            self.assertIn("smem=1", required)
            self.assertIn("qcom_scm=1", required)
            self.assertIn("qcom_ipc_logging=1", required)
            self.assertIn("reboot_request=download", required)
            self.assertIn("download_beacon=1", required)
            self.assertIn("phase=s10b_module_load_prefix_probe", required)
            self.assertIn("predicate=proc_modules_prefix", required)
            self.assertIn("loaded_count=", required)
            self.assertIn(f"expected={len(modules)}", required)
            self.assertIn(f"modules={modules_csv}", required)
            self.assertIn("true_action=reboot_download", required)
            self.assertIn("false_action=park", required)
            self.assertIn("phase=s10b_module_load_reboot_returned", required)
            self.assertIn("/proc/modules", required)
            self.assertIn("download", required)
            self.assertNotIn("s10a_module_load_probe=1", required)
            self.assertNotIn("phase=s10a_module_load_probe", required)
            self.assertNotIn("predicate=proc_modules_core_loaded", required)
            self.assertNotIn("s8_beacon_probe=typec_port_or_i2c_any_0066", required)
            self.assertNotIn("phase=s9_b1_probe", required)
            self.assertNotIn("phase=s8_b1a_probe", required)
            self.assertNotIn("/sys/bus/i2c/devices", required)
            self.assertNotIn("/sys/class/typec/port0", required)
            self.assertNotIn("/config/usb_gadget/g1/functions/ss_acm.0", required)
            self.assertNotIn("phase=configfs_done", required)
            self.assertNotIn("/config/usb_gadget/g1/max_speed", required)
            self.assertNotIn("phase=max_speed", required)
            self.assertNotIn("high-speed", required)
            self.assertNotIn("/sys/class/usb_role", required)
            self.assertNotIn("/sys/devices/platform/soc/a600000.ssusb/mode", required)
            self.assertNotIn("phase=ssusb_mode", required)
            self.assertNotIn("/config/usb_gadget/g1/UDC", required)
            self.assertNotIn("/sys/class/udc", required)
            self.assertNotIn("a600000.dwc3", required)
            self.assertNotIn("phase=udc_bind", required)
            self.assertNotIn("/sys/class/udc/a600000.dwc3/soft_connect", required)
            self.assertNotIn("phase=typec_role_write", required)


if __name__ == "__main__":
    unittest.main()
