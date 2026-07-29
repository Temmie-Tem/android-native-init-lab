import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p284_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P284ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_ready1_binds_exact_p284_candidate_and_observation(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)

        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p284-process-v2-ready-1",
        )
        self.assertEqual(bundle.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(bundle.manifest["observation"]["timeout_sec"], 300)
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "f0362df50d105ec2cd198572ff87c4f7c194e92ab8cea9279bd802ed04541682",
        )
        self.assertEqual(
            bundle.receipt["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

        acceptance = bundle.manifest["observation"]["acceptance"]
        self.assertEqual(
            acceptance["source_contract_id"],
            "s22plus-fyg8-p284-sysfs-ingestion-correction-v1",
        )
        self.assertEqual(
            acceptance["run_id"],
            "023060c8dd0ab036f8547a816624356f",
        )
        self.assertEqual(acceptance["terminal_stage"], 0x93)
        observer = bundle.manifest["observation"]["candidate_observer"]
        self.assertEqual(observer["kind"], "exact_cdc_acm_banner_v1")
        self.assertEqual(
            observer["usb_serial"],
            "S22E3023060c8dd0ab036f8547a816624356f",
        )

        verification = bundle.receipt["observation_contract"]["verification"]
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["terminal_stage"], 0x93)
        self.assertEqual(
            bundle.receipt["manifest"]["sha256"],
            "2500f977a2fdbe90d060e5a35ab4b6583d2857328b66206fc3ec700fca99fdd9",
        )
        self.assertEqual(
            bundle.sha256,
            "c3a670ba0477723380e2b685525a19db92880bc52d53ccae36dd342c2f598eaf",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["odin_invoked"])
        self.assertFalse(bundle.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
