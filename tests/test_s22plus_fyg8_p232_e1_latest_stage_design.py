import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p232_e1_latest_stage_design.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p232_e1_latest_stage_design_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P232E1LatestStageDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.run_id = cls.module.model_run_id("E1A")

    def request(self, stage, **kwargs):
        return self.module.encode_request(
            "E1A", stage, run_id=self.run_id, **kwargs
        )

    def test_compact_layout_is_exactly_45_bytes_with_128_bit_identity(self):
        record = self.module.initialize_record("E1A", self.run_id)
        self.assertEqual(len(record), 45)
        self.assertEqual(self.module.LONG_HEADER_SIZE, 25)
        self.assertEqual(self.module.SLOT_SIZE, 10)
        self.assertEqual(self.module.SLOT_COUNT, 2)
        self.assertEqual(len(self.run_id), 16)
        self.assertEqual(len(self.module.unsat_record("E1A", self.run_id)), 24)

    def test_run_identity_cannot_embed_an_evidence_family(self):
        for family in (
            self.module.LONG_FAMILY,
            self.module.UNSAT_FAMILY,
            *self.module.LEGACY_FAMILIES,
        ):
            run_id = (family + bytes(16))[:16]
            with self.subTest(family=family):
                with self.assertRaises(self.module.DesignError):
                    self.module.initialize_record("E1A", run_id)

    def test_entry_uses_one_committed_slot_and_one_inactive_slot(self):
        decoded = self.module.decode_record(
            self.module.initialize_record("E1A", self.run_id),
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertEqual(decoded["active"]["generation"], 0)
        self.assertEqual(decoded["active"]["stage"], self.module.STAGES["ENTRY"])
        self.assertEqual(decoded["slot_status"], ["valid", "uncommitted"])

    def test_request_roundtrip_and_crc_tamper(self):
        encoded = self.request(self.module.STAGES["PROC_MOUNTED"])
        decoded = self.module.decode_request(encoded)
        self.assertEqual(decoded.profile, "E1A")
        self.assertEqual(decoded.stage, self.module.STAGES["PROC_MOUNTED"])
        tampered = bytearray(encoded)
        tampered[7] ^= 1
        with self.assertRaises(self.module.DesignError):
            self.module.decode_request(bytes(tampered))

    def test_strict_successor_rejects_skip_replay_and_wrong_identity(self):
        initial = self.module.initialize_record("E1A", self.run_id)
        with self.assertRaises(self.module.DesignError):
            self.module.apply_request(
                initial, self.request(self.module.STAGES["SYS_MOUNTED"])
            )
        first_request = self.request(self.module.STAGES["PROC_MOUNTED"])
        first = self.module.apply_request(initial, first_request)
        with self.assertRaises(self.module.DesignError):
            self.module.apply_request(first, first_request)
        other_run = bytes.fromhex("11" * 16)
        with self.assertRaises(self.module.DesignError):
            self.module.apply_request(
                first,
                self.module.encode_request(
                    "E1A",
                    self.module.STAGES["SYS_MOUNTED"],
                    run_id=other_run,
                ),
            )

    def test_all_profiles_reach_only_their_exact_terminal(self):
        for profile in ("E1A", "E1B", "E2"):
            with self.subTest(profile=profile):
                run_id = self.module.model_run_id(profile)
                record = self.module.initialize_record(profile, run_id)
                for stage in self.module.PROFILE_STAGE_SEQUENCES[profile]:
                    terminal = stage == self.module.PROFILE_TERMINALS[profile]
                    record = self.module.apply_request(
                        record,
                        self.module.encode_request(
                            profile,
                            stage,
                            run_id=run_id,
                            outcome=(
                                self.module.OUTCOME_SUCCESS
                                if terminal
                                else self.module.OUTCOME_PROGRESS
                            ),
                            item_index=self.module._expected_item_index(stage),
                        ),
                    )
                decoded = self.module.decode_record(
                    record, expected_profile=profile, expected_run_id=run_id
                )
                self.assertTrue(decoded["terminal_success"])
                self.assertEqual(
                    decoded["active"]["stage"],
                    self.module.PROFILE_TERMINALS[profile],
                )

    def test_e2_profile_has_exact_capacity_and_item_indices(self):
        sequence = self.module.PROFILE_STAGE_SEQUENCES["E2"]
        self.assertEqual(len(sequence), 76)
        self.assertEqual(len(set(sequence)), 76)
        self.assertEqual(sequence[-1], 0x8F)
        self.assertEqual(max(sequence), 0x8F)
        for index, stage in enumerate(range(0x40, 0x7B)):
            self.assertEqual(self.module._expected_item_index(stage), index)
        for index, stage in enumerate(range(0x7B, 0x83)):
            self.assertEqual(self.module._expected_item_index(stage), index)

    def test_torn_inactive_slot_preserves_prior_valid_stage(self):
        first = self.module.apply_request(
            self.module.initialize_record("E1A", self.run_id),
            self.request(self.module.STAGES["PROC_MOUNTED"]),
        )
        next_request = self.request(self.module.STAGES["SYS_MOUNTED"])
        for phase in ("invalidate", "body"):
            with self.subTest(phase=phase):
                torn = self.module.apply_request(
                    first, next_request, stop_after=phase
                )
                decoded = self.module.decode_record(torn)
                self.assertEqual(
                    decoded["active"]["stage"],
                    self.module.STAGES["PROC_MOUNTED"],
                )
                self.assertTrue(decoded["fallback_used"])

    def test_bad_committed_inactive_slot_falls_back(self):
        record = bytearray(
            self.module.apply_request(
                self.module.initialize_record("E1A", self.run_id),
                self.request(self.module.STAGES["PROC_MOUNTED"]),
            )
        )
        record[25 + 6] ^= 1
        decoded = self.module.decode_record(bytes(record))
        self.assertEqual(decoded["active"]["generation"], 1)
        self.assertEqual(decoded["slot_status"], ["bad-crc", "valid"])

    def test_crc_valid_semantically_invalid_inactive_slot_falls_back(self):
        record = bytearray(
            self.module.apply_request(
                self.module.initialize_record("E1A", self.run_id),
                self.request(self.module.STAGES["PROC_MOUNTED"]),
            )
        )
        header = bytes(record[: self.module.LONG_HEADER_SIZE])
        bad_body = self.module.SLOT_BODY_STRUCT.pack(2, 0x7E, 0, 0, 0)
        bad_crc = self.module._slot_crc(header, 0, bad_body)
        record[25:35] = bad_body + bad_crc.to_bytes(4, "little")
        decoded = self.module.decode_record(bytes(record))
        self.assertEqual(decoded["active"]["generation"], 1)
        self.assertEqual(decoded["slot_status"], ["bad-body", "valid"])

    def test_generation_must_match_slot_parity(self):
        header = self.module._record_header("E1A", self.run_id)
        with self.assertRaises(self.module.DesignError):
            self.module._encode_slot(
                header,
                self.module.Slot(
                    0,
                    1,
                    self.module.STAGES["PROC_MOUNTED"],
                    self.module.OUTCOME_PROGRESS,
                    0,
                    0,
                ),
            )

    def test_failure_is_terminal_and_keeps_errno_detail(self):
        record = self.module.apply_request(
            self.module.initialize_record("E1A", self.run_id),
            self.request(
                self.module.STAGES["PROC_MOUNTED"],
                outcome=self.module.OUTCOME_FAILURE,
                detail=19,
            ),
        )
        decoded = self.module.decode_record(record)
        self.assertTrue(decoded["terminal"])
        self.assertFalse(decoded["terminal_success"])
        self.assertEqual(decoded["active"]["detail"], 19)
        with self.assertRaises(self.module.DesignError):
            self.module.apply_request(
                record, self.request(self.module.STAGES["SYS_MOUNTED"])
            )

    def test_multiboot_success_accepts_other_valid_boot_states(self):
        entry = self.module.initialize_record("E1A", self.run_id)
        failure = self.module.apply_request(
            entry,
            self.request(
                self.module.STAGES["PROC_MOUNTED"],
                outcome=self.module.OUTCOME_FAILURE,
                detail=5,
            ),
        )
        success = self.module._complete_profile("E1A", self.run_id)
        result = self.module.classify_observation(
            b"clean",
            entry + b"gap" + failure + b"gap" + success,
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["minimum_candidate_boots"], 3)

        malformed = bytearray(entry)
        malformed[31] ^= 1
        rejected = self.module.classify_observation(
            b"clean",
            success + b"gap" + bytes(malformed),
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertFalse(rejected["accepted"])
        self.assertTrue(rejected["integrity_issue"])

    def test_foreign_malformed_legacy_and_partial_fail_closed(self):
        good = self.module.initialize_record("E1A", self.run_id)
        foreign = self.module.initialize_record(
            "E1A", bytes.fromhex("22" * 16)
        )
        malformed = bytearray(good)
        malformed[31] ^= 1
        payloads = (
            foreign,
            bytes(malformed),
            self.module.LEGACY_FAMILIES[0] + b"x",
            b"prefix" + self.module.LONG_FAMILY[:6],
            self.module.LONG_FAMILY[-6:] + b"suffix",
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.module.classify_observation(
                    b"clean",
                    payload,
                    expected_profile="E1A",
                    expected_run_id=self.run_id,
                )
                self.assertFalse(result["accepted"])
                self.assertTrue(result["integrity_issue"])

    def test_dirty_baseline_is_rejected(self):
        for baseline in (
            self.module.LONG_FAMILY,
            self.module.UNSAT_FAMILY,
            self.module.LEGACY_FAMILIES[0],
            b"prefix" + self.module.LONG_FAMILY[:5],
        ):
            with self.subTest(baseline=baseline):
                with self.assertRaises(self.module.DesignError):
                    self.module.classify_observation(
                        baseline,
                        b"ordinary",
                        expected_profile="E1A",
                        expected_run_id=self.run_id,
                    )

    def test_visibility_thresholds_remain_24_and_45(self):
        expected = {
            0: "ZERO_AMBIGUOUS",
            23: "ZERO_AMBIGUOUS",
            24: "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS",
            44: "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS",
            45: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
            129: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
        }
        for idx, classification in expected.items():
            with self.subTest(idx=idx):
                result = self.module.simulate_initial_visibility(
                    "E1A", self.run_id, idx=idx
                )
                self.assertEqual(result["classification"], classification)

    def test_invalid_magic_and_nonselection_remain_zero_ambiguous(self):
        cases = (
            {"idx": 45, "magic": 0},
            {"idx": 45, "selected": False},
        )
        for case in cases:
            with self.subTest(case=case):
                result = self.module.simulate_initial_visibility(
                    "E1A", self.run_id, **case
                )
                self.assertEqual(result["classification"], "ZERO_AMBIGUOUS")
                self.assertFalse(result["accepted"])

    def test_result_is_host_only_and_creates_no_artifact_or_authority(self):
        result = self.module.build_result()
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["host_only"])
        self.assertEqual(result["record_layout"]["long_record_bytes"], 45)
        self.assertEqual(result["record_layout"]["binding_bits"], 128)
        self.assertTrue(
            all(not value for value in result["safety"].values())
        )


if __name__ == "__main__":
    unittest.main()
