import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "workspace/public/src/scripts/revalidation"),
               str(ROOT / "workspace/public/src/scripts/analysis")]
import prepare_s22plus_fyg8_p345_process_v2 as prepare

class P345PreparationTests(unittest.TestCase):
    def test_actual_full_bundle_rehearsal_does_not_publish(self):
        paths = (prepare.DEFAULT_STATIC_OUTPUT, prepare.DEFAULT_PROMOTION, prepare.DEFAULT_MANIFEST)
        before = tuple(path.exists() for path in paths)
        value = prepare.build()
        self.assertTrue(value["common_offline_verified"])
        self.assertFalse(value["published"])
        self.assertFalse(value["created"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["run_directory_created"])
        self.assertEqual(before, tuple(path.exists() for path in paths))

    def test_private_publisher_same_bytes_only_and_no_replace(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            self.assertTrue(prepare._write(path, b"{}", 0o400))
            self.assertFalse(prepare._write(path, b"{}", 0o400))
            with self.assertRaises(prepare.PromotionError):
                prepare._write(path, b"different", 0o400)
            self.assertEqual(path.read_bytes(), b"{}")
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)

    def test_rehashed_predecessor_promotion_still_rejected(self):
        static = prepare.candidate_static.build_result()
        payloads, _, pins = prepare._payloads(static,
            static_path=prepare.DEFAULT_STATIC_OUTPUT, promotion=prepare.DEFAULT_PROMOTION)
        acceptance = prepare.adapter.acceptance_fixture()
        acceptance["contract"] = copy.deepcopy(pins)
        import json
        run = json.loads(payloads["run_manifest"])
        run["run_id"] = prepare.evidence.P344_RUN_ID
        payloads["run_manifest"] = prepare.canonical(run)
        acceptance["contract"]["run_manifest"].update(prepare.identity(payloads["run_manifest"]))
        with self.assertRaises(prepare.evidence.EvidenceError):
            prepare.evidence.verify_offline_contract(acceptance, payloads=payloads,
                receipts=acceptance["contract"],
                candidate_ap=static["candidate"]["a"]["ap_tar_md5"])

if __name__ == "__main__":
    unittest.main()
