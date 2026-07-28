import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p282_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P282ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_ready1_binds_exact_p282_candidate_and_observation(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)

        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p282-process-v2-ready-1",
        )
        self.assertEqual(bundle.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(bundle.manifest["observation"]["timeout_sec"], 300)
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "23a9bdee16c122fb7217d1cbb15df6a55c13cce8b7fc7c50cc6030cf04681b3b",
        )
        self.assertEqual(
            bundle.receipt["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

        acceptance = bundle.manifest["observation"]["acceptance"]
        self.assertEqual(
            acceptance["source_contract_id"],
            "s22plus-fyg8-p282-prebind-child-reinit-decision-v1",
        )
        self.assertEqual(acceptance["terminal_stage"], 0x93)
        observer = bundle.manifest["observation"]["candidate_observer"]
        self.assertEqual(observer["kind"], "exact_cdc_acm_banner_v1")
        self.assertEqual(
            observer["usb_serial"],
            "S22E35525fada87150ec7d94c208f7875b83f",
        )

        verification = bundle.receipt["observation_contract"]["verification"]
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["terminal_stage"], 0x93)
        self.assertEqual(
            bundle.sha256,
            "eec2ad38a8447b4bc9ddb73f44b3b1b7b4aa3688bb481a56d022c7c68a887c07",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["odin_invoked"])
        self.assertFalse(bundle.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
