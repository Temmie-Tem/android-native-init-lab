import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "device_action_f1_evidence_v2.py"
RUN_ID = bytes.fromhex("395f27c3ac34ebe61395d7efd5a058e8")


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "device_action_f1_evidence_v2_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class DeviceActionF1EvidenceV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.checkpoint = cls.module.checkpoint

    def acceptance(self):
        return {
            "kind": self.module.CHECKPOINT_KIND,
            "source": "/proc/last_kmsg",
            "marker": self.checkpoint.ENTRY_PROOF.decode("ascii"),
            "family": self.checkpoint.ENTRY_FAMILY.decode("ascii"),
            "exact_count": 1,
            "decoder": self.module.CHECKPOINT_DECODER,
            "profile": "E1",
            "run_id": RUN_ID.hex(),
            "terminal_stage": self.checkpoint.PROFILE_TERMINAL_STAGE["E1"],
            "terminal_outcome": "success",
            "require_two_valid_slots": True,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/run-manifest.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/static-check.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }

    def region_through(self, count, *, failure=False):
        region = self.checkpoint.initial_region(0x300000, 9)
        sequence = self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]
        for index, stage in enumerate(sequence[:count]):
            is_last = index == count - 1
            if failure and is_last:
                outcome = self.checkpoint.OUTCOME_FAILURE
                detail = -5
            elif stage == self.checkpoint.PROFILE_TERMINAL_STAGE["E1"]:
                outcome = self.checkpoint.OUTCOME_SUCCESS
                detail = 0
            else:
                outcome = self.checkpoint.OUTCOME_PROGRESS
                detail = 0
            request = self.checkpoint.encode_request(
                "E1", stage, run_id=RUN_ID, outcome=outcome, detail=detail
            )
            region = self.checkpoint.apply_request(region, request)
        return region

    def classify(self, region):
        return self.module.classify_checkpoint(
            b"prefix" + region + b"suffix", self.acceptance()
        )

    def test_terminal_success_requires_exact_two_slot_checkpoint(self):
        result = self.classify(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_TERMINAL_SUCCESS")
        self.assertEqual(result["exact_count"], 1)
        self.assertTrue(result["checkpoint"]["two_valid_slots"])
        self.assertEqual(result["checkpoint"]["active"]["run_id"], RUN_ID.hex())

    def test_progress_and_failure_are_diagnostic_not_acceptance(self):
        progress = self.classify(self.region_through(3))
        failure = self.classify(self.region_through(3, failure=True))
        self.assertFalse(progress["accepted"])
        self.assertEqual(progress["classification"], "CHECKPOINT_PROGRESS_ONLY")
        self.assertFalse(failure["accepted"])
        self.assertEqual(failure["classification"], "CHECKPOINT_TERMINAL_FAILURE")
        self.assertEqual(failure["checkpoint"]["active"]["detail"], -5)

    def test_changed_run_id_is_decode_failure(self):
        acceptance = self.acceptance()
        acceptance["run_id"] = "4" * 32
        result = self.module.classify_checkpoint(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"])),
            acceptance,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_DECODE_FAILURE")

    def test_duplicate_and_partial_family_are_integrity_failures(self):
        region = self.region_through(
            len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"])
        )
        duplicate = self.module.classify_checkpoint(
            region + region, self.acceptance()
        )
        partial = self.module.classify_checkpoint(
            b"prefix" + self.checkpoint.ENTRY_FAMILY[:8], self.acceptance()
        )
        self.assertEqual(
            duplicate["classification"], "CHECKPOINT_FAMILY_INTEGRITY_FAILURE"
        )
        self.assertEqual(
            partial["classification"], "CHECKPOINT_FAMILY_INTEGRITY_FAILURE"
        )
        self.assertFalse(duplicate["accepted"])
        self.assertFalse(partial["accepted"])

    def test_corrupt_new_slot_falls_back_without_pass(self):
        region = bytearray(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        active = self.checkpoint.decode_region(bytes(region))["active"]
        start = self.checkpoint.ENTRY_SIZE + active["slot_id"] * self.checkpoint.SLOT_SIZE
        region[start + 20] ^= 0x01
        result = self.classify(bytes(region))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_PROGRESS_ONLY")
        self.assertEqual(result["checkpoint"]["invalid_committed_slots"], [active["slot_id"]])

    def test_terminal_success_with_only_one_valid_slot_is_rejected(self):
        region = bytearray(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        decoded = self.checkpoint.decode_region(bytes(region))
        active_slot = decoded["active"]["slot_id"]
        older_slot = active_slot ^ 1
        commit = (
            self.checkpoint.ENTRY_SIZE
            + older_slot * self.checkpoint.SLOT_SIZE
            + self.checkpoint.SLOT_SIZE
            - 1
        )
        region[commit] = 0
        result = self.classify(bytes(region))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_TERMINAL_MISMATCH")

    def test_marker_acceptance_shape_remains_supported(self):
        marker = {
            "kind": self.module.MARKER_KIND,
            "source": "/proc/last_kmsg",
            "marker": "legacy marker",
            "family": "legacy family",
            "exact_count": 1,
        }
        self.assertEqual(self.module.validate_acceptance(marker), marker)


if __name__ == "__main__":
    unittest.main()
