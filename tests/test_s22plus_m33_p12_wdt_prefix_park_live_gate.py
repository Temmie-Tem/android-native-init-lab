import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m33_p12_wdt_prefix_park_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m33_p12_wdt_prefix_park_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM33P12WdtPrefixParkLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_prefix_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M33_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M33_BOOT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M33_MODULE_LIST_SHA256, markers)
        self.assertIn("watchdog-managed prefix park", markers)
        self.assertIn("prefix_targets=12", markers)
        self.assertIn("module_load_only=1", markers)
        self.assertIn("manual Download rollback is recovery-only", markers)
        self.assertIn("PMIC/RDX abnormal reset before the observation window is FAIL", markers)
        self.assertIn("phy-msm-ssusb-qmp.ko intentionally excluded", markers)
        self.assertIn("EUD excluded", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M33_AP_SHA256, missing)
        self.assertIn(self.module.EXPECTED_M33_MARKER, missing)

    def test_missing_policy_markers_accept_exact_marker_set(self):
        text = " ".join(self.module.policy_required_markers())
        self.assertEqual(self.module.missing_policy_markers(text), [])

    @unittest.skipUnless(MANIFEST.exists(), "private M33 manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m33_manifest_check.log"
            self.module.verify_m33_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m33_p12_manifest_hashes=", text)
            self.assertIn("m33_manifest_safety=", text)
            self.assertIn("m33_p12_manifest_closure=", text)


if __name__ == "__main__":
    unittest.main()
