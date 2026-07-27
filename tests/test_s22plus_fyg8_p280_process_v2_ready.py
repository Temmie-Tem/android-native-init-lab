import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p280_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P280ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_ready1_binds_exact_p280_candidate_and_observation(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)

        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p280-process-v2-ready-1",
        )
        self.assertEqual(bundle.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(bundle.manifest["observation"]["timeout_sec"], 240)
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "6713cfef1ad2abe5d2b144f695c1e0cbc71ea0dbf6c78212565b19cb8beb3486",
        )
        self.assertEqual(
            bundle.receipt["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

        acceptance = bundle.manifest["observation"]["acceptance"]
        self.assertEqual(
            acceptance["source_contract_id"],
            "s22plus-fyg8-p280-parent-pullup-discriminator-v1",
        )
        self.assertEqual(acceptance["terminal_stage"], 0x90)
        observer = bundle.manifest["observation"]["candidate_observer"]
        self.assertEqual(observer["kind"], "exact_cdc_acm_banner_v1")
        self.assertEqual(
            observer["usb_serial"],
            "S22E3568abdddae4a0320e14c95aad8bf1e9c",
        )

        verification = bundle.receipt["observation_contract"]["verification"]
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["terminal_stage"], 0x90)
        self.assertEqual(
            bundle.sha256,
            "8f81f6a75b43e643b66408ca4ab4e4a79a97742f1b3c38884f61437d59e4e37b",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["odin_invoked"])
        self.assertFalse(bundle.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
