import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m34_s6_stock_softdep_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34S6StockSoftdepLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_stock_softdep_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_BOOT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_INIT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_TEMPLATE_SOURCE_SHA256, markers)
        self.assertIn("stock-ordered configfs gadget/function/config", markers)
        self.assertIn("UDC=none", markers)
        self.assertIn("0x04E8:0x6860", markers)
        self.assertIn("ss_acm.0 link", markers)
        self.assertIn("no g1/max_speed=high-speed", markers)
        self.assertIn("no /sys/class/usb_role", markers)
        self.assertIn("no ssusb/speed=high-speed", markers)
        self.assertIn("ssusb/mode=peripheral", markers)
        self.assertIn("final UDC bind", markers)
        self.assertIn("UDC=a600000.dwc3", markers)
        self.assertIn("no soft_connect", markers)
        self.assertIn("no /sys/class/udc/a600000.dwc3/soft_connect", markers)
        self.assertIn("stock dwc3_msm softdep parity", markers)
        self.assertIn("stock_softdep_parity=1", markers)
        self.assertIn("qmp_module=1", markers)
        self.assertIn("eud_module=1", markers)
        self.assertIn("ucsi_glink=1", markers)
        self.assertIn("phy-msm-ssusb-qmp.ko included", markers)
        self.assertIn("eud.ko included without EUD sysfs write", markers)
        self.assertIn("ucsi_glink.ko included", markers)
        self.assertIn("no descriptor or companion-function change", markers)
        self.assertIn("enhanced host USB observation", markers)
        self.assertIn("lsusb -d 04e8:6860 -v", markers)
        self.assertIn("usb-devices", markers)
        self.assertIn("udev properties", markers)
        self.assertIn("host dmesg delta", markers)
        self.assertIn("PMIC/RDX abnormal reset before the observation window is FAIL", markers)
        self.assertIn("no EUD sysfs write", markers)
        self.assertIn("phy-msm-ssusb-qmp.ko", markers)
        self.assertIn("eud.ko", markers)
        self.assertIn("ucsi_glink.ko", markers)
        self.assertNotIn("usb_role=device", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, missing)
        self.assertIn(self.module.EXPECTED_M34_MARKER, missing)
        self.assertIn("ssusb/mode=peripheral", missing)
        self.assertIn("stock_softdep_parity=1", missing)
        self.assertIn("no soft_connect", missing)

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
        self.assertIn("no /sys/class/usb_role", draft)
        self.assertIn("ssusb/mode=peripheral", draft)
        self.assertIn("no `g1/max_speed=high-speed`", draft)
        self.assertIn("no `ssusb/speed=high-speed`", draft)
        self.assertIn("no soft_connect", draft)
        self.assertIn("`soft_connect`", draft)
        self.assertIn("stock_softdep_parity=1", draft)
        self.assertIn("eud.ko included without EUD sysfs write", draft)
        self.assertIn("does not authorize S1/S2/S3/S4/S5 repeat", " ".join(draft.split()))

    def test_verify_agents_exception_rejects_draft_only_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(self.module.agents_exception_draft(), encoding="utf-8")
            log_path = Path(tmp) / "draft_only_check.log"
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_agents_exception(root, log_path)
            self.assertIn("draft-only M34 S6", str(caught.exception))
            self.assertIn("agents_exception_draft_only_present=1", log_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.5 manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m34_s6_manifest_check.log"
            self.module.verify_m34_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m34_s6_manifest_hashes=", text)
            self.assertIn("m34_manifest_safety=", text)
            self.assertIn("m34_s6_manifest_runtime_steps=", text)
            self.assertIn("m34_s6_manifest_closure=", text)
            self.assertEqual(len(self.module.EXPECTED_MODULES), 55)
            self.assertIn("dwc3-msm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("usb_f_ss_acm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("phy-msm-ssusb-qmp.ko", self.module.EXPECTED_MODULES)
            self.assertIn("eud.ko", self.module.EXPECTED_MODULES)
            self.assertIn("ucsi_glink.ko", self.module.EXPECTED_MODULES)

    def test_acm_match_requires_stock_samsung_vid_pid(self):
        self.assertTrue(self.module.is_m34_s6_acm({"vendor": "04E8", "product": "6860"}))
        self.assertFalse(self.module.is_m34_s6_acm({"vendor": "04e8", "product": "685d"}))
        self.assertFalse(self.module.is_m34_s6_acm({"vendor": "18d1", "product": "4ee7"}))

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
