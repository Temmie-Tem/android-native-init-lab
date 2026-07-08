import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s7a2_geni_i2c_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_7/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m34_s7a2_geni_i2c_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34S7A2GeniI2cLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_s7a2_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_BOOT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_INIT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_TEMPLATE_SOURCE_SHA256, markers)
        self.assertIn("stock max77705 PDIC altmode session-producer closure", markers)
        self.assertIn("GENI I2C transport closure", markers)
        self.assertIn("session_producer_parity=1", markers)
        self.assertIn("max77705_session=1", markers)
        self.assertIn("typec_readback=1", markers)
        self.assertIn("geni_i2c_transport=1", markers)
        self.assertIn("i2c_msm_geni=1", markers)
        self.assertIn("gpi_dma=1", markers)
        self.assertIn("msm_geni_se=1", markers)
        self.assertIn("role_write_discriminator=1", markers)
        self.assertIn("phase=typec_partner_check", markers)
        self.assertIn("phase=typec_role_write", markers)
        self.assertIn("role_device_rc=", markers)
        self.assertIn("role_sink_rc=", markers)
        self.assertIn("data_role=device", markers)
        self.assertIn("power_role=sink", markers)
        self.assertIn("functionfs=0", markers)
        self.assertIn("stock_composite=0", markers)
        self.assertIn("no ssusb/speed high-speed write", markers)
        self.assertIn("read-only ssusb speed marker", markers)
        self.assertIn("no soft_connect", markers)
        self.assertIn("qcom-i2c-pmic.ko included", markers)
        self.assertIn("gpi.ko included", markers)
        self.assertIn("msm-geni-se.ko included", markers)
        self.assertIn("i2c-msm-geni.ko included", markers)
        self.assertIn("mfd_max77705.ko included", markers)
        self.assertIn("pdic_max77705.ko included", markers)
        self.assertIn("max77705_charger.ko included", markers)
        self.assertIn("max77705-fuelgauge.ko included", markers)
        self.assertIn("sec_debug_region.ko present due stock charger dependency", markers)
        self.assertIn("requires_s7a_specific_live_risk_review", markers)
        self.assertIn("stage_s7a2_no_charge_otg_rail_gpio_writes", markers)
        self.assertIn("/sys/class/typec/port0/data_role", markers)
        self.assertIn("/sys/class/udc/a600000.dwc3/current_speed", markers)
        self.assertIn("lsusb -d 04e8:6860 -v", markers)
        self.assertIn("PMIC/RDX abnormal reset before the observation window is FAIL", markers)
        self.assertNotIn("usb_role=device", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, missing)
        self.assertIn(self.module.EXPECTED_M34_MARKER, missing)
        self.assertIn("session_producer_parity=1", missing)
        self.assertIn("max77705_session=1", missing)
        self.assertIn("typec_readback=1", missing)
        self.assertIn("geni_i2c_transport=1", missing)
        self.assertIn("role_write_discriminator=1", missing)

    def test_missing_policy_markers_accept_exact_marker_set(self):
        text = " ".join(self.module.policy_required_markers())
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_agents_exception_draft_satisfies_same_policy_markers(self):
        draft = self.module.agents_exception_draft()
        self.assertEqual(self.module.missing_policy_markers(draft), [])
        self.assertTrue(self.module.has_draft_only_m34_exception(draft))
        self.assertIn("DRAFT ONLY", draft)
        self.assertIn(self.module.LIVE_ACK_TOKEN, draft)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, draft)
        self.assertIn("This draft is not active authorization", draft)
        self.assertIn("session_producer_parity=1", draft)
        self.assertIn("max77705_session=1", draft)
        self.assertIn("typec_readback=1", draft)
        self.assertIn("geni_i2c_transport=1", draft)
        self.assertIn("role_write_discriminator=1", draft)
        self.assertIn("data_role=device", draft)
        self.assertIn("power_role=sink", draft)
        self.assertIn("sec_debug_region.ko present due stock charger dependency", draft)
        self.assertIn("does not authorize S1/S2/S3/S4/S5/S6 repeat", " ".join(draft.split()))

    def test_agents_exception_active_template_passes_policy_gate(self):
        template = self.module.agents_exception_active_template()
        self.assertEqual(self.module.missing_policy_markers(template), [])
        self.assertFalse(self.module.has_draft_only_m34_exception(template))
        self.assertNotIn("DRAFT ONLY", template)
        self.assertNotIn("This draft is not active authorization", template)
        self.assertIn(self.module.LIVE_ACK_TOKEN, template)
        self.assertIn("Narrow operator-authorized exception", template)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(template, encoding="utf-8")
            log_path = Path(tmp) / "active_template_check.log"
            self.module.verify_agents_exception(root, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("agents_exception_draft_only_present=0", text)
            self.assertIn("agents_exception_missing=[]", text)

    def test_verify_agents_exception_rejects_draft_only_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(self.module.agents_exception_draft(), encoding="utf-8")
            log_path = Path(tmp) / "draft_only_check.log"
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_agents_exception(root, log_path)
            self.assertIn("draft-only M34 S7A2", str(caught.exception))
            self.assertIn("agents_exception_draft_only_present=1", log_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.7 manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m34_s7a2_manifest_check.log"
            self.module.verify_m34_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m34_s7a2_manifest_hashes=", text)
            self.assertIn("m34_manifest_safety=", text)
            self.assertIn("m34_s7a2_manifest_runtime_steps=", text)
            self.assertIn("m34_s7a2_manifest_closure=", text)
            self.assertEqual(len(self.module.EXPECTED_MODULES), 86)
            self.assertIn("dwc3-msm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("usb_f_ss_acm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("phy-msm-ssusb-qmp.ko", self.module.EXPECTED_MODULES)
            self.assertIn("eud.ko", self.module.EXPECTED_MODULES)
            self.assertIn("ucsi_glink.ko", self.module.EXPECTED_MODULES)
            self.assertIn("gpi.ko", self.module.EXPECTED_MODULES)
            self.assertIn("msm-geni-se.ko", self.module.EXPECTED_MODULES)
            self.assertIn("i2c-msm-geni.ko", self.module.EXPECTED_MODULES)
            self.assertIn("mfd_max77705.ko", self.module.EXPECTED_MODULES)
            self.assertIn("pdic_max77705.ko", self.module.EXPECTED_MODULES)
            self.assertIn("sec_debug_region.ko", self.module.EXPECTED_MODULES)

    def test_acm_match_requires_stock_samsung_vid_pid(self):
        self.assertTrue(self.module.is_m34_s7a2_acm({"vendor": "04E8", "product": "6860"}))
        self.assertFalse(self.module.is_m34_s7a2_acm({"vendor": "04e8", "product": "685d"}))
        self.assertFalse(self.module.is_m34_s7a2_acm({"vendor": "18d1", "product": "4ee7"}))

    def test_samsung_usb_summary_classifies_android_and_upload_endpoints(self):
        sample = """
T:  Bus=02 Lev=02 Prnt=02 Port=02 Cnt=01 Dev#= 91 Spd=5000 MxCh= 0
D:  Ver= 3.20 Cls=02(commc) Sub=02 Prot=00 MxPS= 9 #Cfgs=  1
P:  Vendor=04e8 ProdID=685d Rev=01.00
S:  Manufacturer=Samsung
S:  Product=SAMSUNG USB
I:  If#= 0 Alt= 0 #EPs= 1 Cls=02(commc) Sub=02 Prot=01 Driver=(none)
I:  If#= 1 Alt= 0 #EPs= 2 Cls=0a(data ) Sub=00 Prot=00 Driver=(none)

T:  Bus=02 Lev=02 Prnt=02 Port=02 Cnt=01 Dev#= 93 Spd=5000 MxCh= 0
D:  Ver= 3.20 Cls=00(>ifc ) Sub=00 Prot=00 MxPS= 9 #Cfgs=  1
P:  Vendor=04e8 ProdID=6860 Rev=05.04
S:  Manufacturer=SAMSUNG
S:  Product=SAMSUNG_Android
I:  If#= 1 Alt= 0 #EPs= 1 Cls=02(commc) Sub=02 Prot=01 Driver=cdc_acm
I:  If#= 2 Alt= 0 #EPs= 2 Cls=0a(data ) Sub=00 Prot=00 Driver=cdc_acm
"""
        summary = self.module.samsung_usb_devices_summary(sample)
        self.assertEqual([device["product_id"] for device in summary], ["685d", "6860"])
        self.assertEqual(summary[0]["product"], "SAMSUNG USB")
        self.assertEqual(summary[0]["speed_mbps"], 5000)
        self.assertIn("(none)", summary[0]["drivers"])
        self.assertIn("02:commc", summary[0]["interface_classes"])
        self.assertIn("cdc_acm", summary[1]["drivers"])
        self.assertEqual(summary[1]["product"], "SAMSUNG_Android")

    def test_host_usb_redaction_removes_serials_and_by_id_links(self):
        sample = "\n".join(
            [
                "  iSerial                 3 serial_fake_123",
                "ID_SERIAL=Samsung_serial_fake_123",
                "ID_SERIAL_SHORT=serial_fake_123",
                "ID_USB_SERIAL=Samsung_serial_fake_123",
                "ID_USB_SERIAL_SHORT=serial_fake_123",
                "DEVLINKS=/dev/serial/by-id/usb-Samsung_serial_fake_123-if02 /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0",
            ]
        )
        redacted = self.module.redact_host_usb_text(sample)
        self.assertNotIn("serial_fake_123", redacted)
        self.assertIn("iSerial                 3 <redacted>", redacted)
        self.assertIn("ID_SERIAL=<redacted>", redacted)
        self.assertIn("ID_SERIAL_SHORT=<redacted>", redacted)
        self.assertIn("ID_USB_SERIAL=<redacted>", redacted)
        self.assertIn("ID_USB_SERIAL_SHORT=<redacted>", redacted)
        self.assertIn("/dev/serial/by-id/<redacted>", redacted)
        self.assertIn("/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0", redacted)


if __name__ == "__main__":
    unittest.main()
