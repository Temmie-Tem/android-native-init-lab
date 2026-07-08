import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m31b_wdt_managed_park_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m31b_wdt_managed_park_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM31BWdtManagedParkLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_recovery_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M31B_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M31B_BOOT_SHA256, markers)
        self.assertIn("manual Download rollback is recovery-only", markers)
        self.assertIn("PMIC/RDX abnormal reset before the observation window is FAIL", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M31B_AP_SHA256, missing)

    def test_missing_policy_markers_accept_exact_marker_set(self):
        text = " ".join(self.module.policy_required_markers())
        self.assertEqual(self.module.missing_policy_markers(text), [])

    @unittest.skipUnless(MANIFEST.exists(), "private M31B manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m31b_manifest_check.log"
            self.module.verify_m31b_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m31b_manifest_hashes=", text)
            self.assertIn("m31b_manifest_safety=", text)


if __name__ == "__main__":
    unittest.main()
