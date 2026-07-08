import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m34_s1_runtime_gadget_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34S1RuntimeGadgetLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_stock_s1_semantics(self):
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
        self.assertIn("no max_speed=high-speed", markers)
        self.assertIn("no usb_role=device", markers)
        self.assertIn("no final UDC bind", markers)
        self.assertIn("no UDC=a600000.dwc3", markers)
        self.assertIn("PMIC/RDX abnormal reset before the observation window is FAIL", markers)
        self.assertIn("phy-msm-ssusb-qmp.ko intentionally excluded", markers)
        self.assertIn("EUD excluded", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, missing)
        self.assertIn(self.module.EXPECTED_M34_MARKER, missing)

    def test_missing_policy_markers_accept_exact_marker_set(self):
        text = " ".join(self.module.policy_required_markers())
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_agents_exception_draft_satisfies_same_policy_markers(self):
        draft = self.module.agents_exception_draft()
        self.assertEqual(self.module.missing_policy_markers(draft), [])
        self.assertIn("DRAFT ONLY", draft)
        self.assertIn(self.module.LIVE_ACK_TOKEN, draft)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, draft)
        self.assertIn("This draft is not active authorization", draft)
        self.assertIn("authorize S2/S3 live", draft)

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.2 manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m34_s1_manifest_check.log"
            self.module.verify_m34_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m34_s1_manifest_hashes=", text)
            self.assertIn("m34_manifest_safety=", text)
            self.assertIn("m34_s1_manifest_runtime_steps=", text)
            self.assertIn("m34_s1_manifest_closure=", text)
            self.assertEqual(len(self.module.EXPECTED_MODULES), 45)
            self.assertIn("dwc3-msm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("usb_f_ss_acm.ko", self.module.EXPECTED_MODULES)
            self.assertNotIn("phy-msm-ssusb-qmp.ko", self.module.EXPECTED_MODULES)
            self.assertNotIn("eud.ko", self.module.EXPECTED_MODULES)


if __name__ == "__main__":
    unittest.main()
