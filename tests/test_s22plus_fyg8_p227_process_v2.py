import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p226_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P227ProcessV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module(
            "prepare_s22plus_fyg8_p227_process_v2"
        )
        cls.p222 = importlib.import_module(
            "prepare_s22plus_fyg8_p222_process_v2"
        )
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_adapter_pins_exact_p226_closure_and_restores_core(self):
        original_schema = self.p222.SCHEMA
        args = self.module.parse_args([])
        self.assertEqual(args.p221_static, self.module.DEFAULT_P226_STATIC)
        self.assertEqual(args.candidate_ap, self.module.DEFAULT_CANDIDATE_AP)
        self.assertEqual(self.module.CANDIDATE_AP["size"], 27_064_361)
        self.assertRegex(self.module.CANDIDATE_AP["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(self.p222.SCHEMA, original_schema)

    def test_exact_private_promotion_inputs_derive_common_contract(self):
        static_path = ROOT / self.module.DEFAULT_P226_STATIC
        if not static_path.is_file():
            self.skipTest("private P2.26 static result is not present")
        static = json.loads(static_path.read_text(encoding="ascii"))
        run_payload, static_payload = self.module.derive(
            static, self.module.CANDIDATE_AP
        )
        run = json.loads(run_payload)
        promoted = json.loads(static_payload)
        self.assertEqual(run["candidate_ap"], self.module.CANDIDATE_AP)
        self.assertEqual(run["observation_contract"]["zero_classification"], "ZERO_AMBIGUOUS")
        self.assertTrue(promoted["candidate"]["record_verification"]["verified"])
        self.assertFalse(promoted["safety"]["live_authorized"])

    def test_ready_manifest_passes_common_bundle_without_live_authority(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)
        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p226-process-v2-ready-1",
        )
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            self.module.CANDIDATE_AP["sha256"],
        )
        self.assertEqual(
            bundle.receipt["observation_contract"]["verification"]["schema"],
            "device_action_f1_same_ring_offline_contract_v2",
        )
        self.assertEqual(
            bundle.sha256,
            "ea6b06e26e7c2b14890da3cd9dfc05c9fa6d38c31ed5726716856be135714a00",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
