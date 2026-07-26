import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p270_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P272ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_ready_manifest_reopens_exact_e3_bundle_without_live_authority(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)

        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p270-process-v2-ready-1",
        )
        self.assertEqual(bundle.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "a172448aaaab429591bfb31fb0ad57e635d6c362b27620eab2f528787eef3d66",
        )
        self.assertEqual(
            bundle.receipt["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

        acceptance = bundle.manifest["observation"]["acceptance"]
        self.assertEqual(acceptance["profile"], "E2")
        self.assertEqual(acceptance["terminal_stage"], 0x90)
        self.assertEqual(
            acceptance["source_contract_id"],
            "s22plus-fyg8-p260-e3-exact-acm-banner-v1",
        )
        observer = bundle.manifest["observation"]["candidate_observer"]
        self.assertEqual(observer["kind"], "exact_cdc_acm_banner_v1")
        self.assertEqual(observer["usb_driver"], "cdc_acm")

        verification = bundle.receipt["observation_contract"]["verification"]
        self.assertEqual(
            verification["schema"],
            "device_action_f1_e1_latest_stage_offline_contract_v1",
        )
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["terminal_stage"], 0x90)
        self.assertEqual(
            bundle.sha256,
            "52e2e95c3d346a1e2936f3ec2a7a7f6efd5e3ed080ceacb7803b250cdca70347",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["odin_invoked"])
        self.assertFalse(bundle.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
