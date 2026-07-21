import copy
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1e_checkpoint_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1e_checkpoint_contract_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1ECheckpointContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        source = Path(
            os.environ.get("S22PLUS_FYG8_TEST_SOURCE", str(cls.module.DEFAULT_SOURCE))
        )
        cls.source = source if source.is_absolute() else ROOT / source
        cls.patch = ROOT / cls.module.DEFAULT_PATCH
        cls.patched = cls.module.apply_patch_to_minimal_tree(cls.source, cls.patch)

    def request(self, profile, stage, **kwargs):
        return self.module.encode_request(
            profile,
            stage,
            run_id=self.module.MODEL_RUN_IDS[profile],
            **kwargs,
        )

    def advance(self, profile, *, terminal=True):
        region = self.module.initial_region(0x300000, 9)
        for stage in self.module.PROFILE_STAGE_SEQUENCES[profile]:
            is_terminal = stage == self.module.PROFILE_TERMINAL_STAGE[profile]
            if is_terminal and not terminal:
                break
            item_index = (
                stage - self.module.STAGES["USB_MODULE_BASE"]
                if self.module.STAGES["USB_MODULE_BASE"]
                <= stage
                <= self.module.STAGES["USB_MODULE_LAST"]
                else 0
            )
            region = self.module.apply_request(
                region,
                self.request(
                    profile,
                    stage,
                    item_index=item_index,
                    outcome=(
                        self.module.OUTCOME_SUCCESS
                        if is_terminal
                        else self.module.OUTCOME_PROGRESS
                    ),
                ),
            )
        return region

    def test_abi_sizes_and_carrier_derivation_are_exact(self):
        self.assertEqual(self.module.REQUEST_STRUCT.size, 32)
        self.assertEqual(self.module.SLOT_STRUCT.size, 64)
        self.assertEqual(self.module.REGION_SIZE, 173)
        self.assertEqual(len(self.module.ENTRY_PROOF), 45)
        derived = hashlib.sha256(
            self.module.CARRIER_PREIMAGE.encode("ascii")
        ).hexdigest()
        self.assertEqual(derived, self.module.CARRIER_SHA256)
        self.assertEqual(self.module.CARRIER_ID, bytes.fromhex(derived[:32]))

    def test_profile_schemas_are_derived_and_distinct(self):
        self.assertEqual(
            set(self.module.PROFILE_STAGE_SEQUENCES), {"E1", "E2", "E3", "E4"}
        )
        self.assertEqual(len(set(self.module.PROFILE_SCHEMA_SHA256.values())), 4)
        self.assertEqual(len(set(self.module.MODEL_RUN_IDS.values())), 4)
        for name, preimage in self.module.PROFILE_SCHEMA_PREIMAGES.items():
            digest = hashlib.sha256(preimage.encode("ascii")).hexdigest()
            self.assertEqual(self.module.PROFILE_SCHEMA_SHA256[name], digest)
            self.assertEqual(
                self.module.PROFILE_STAGE_SEQUENCES[name][-1],
                self.module.PROFILE_TERMINAL_STAGE[name],
            )

    def test_request_roundtrip_for_each_profile(self):
        for profile in self.module.PROFILE_NUMBERS:
            with self.subTest(profile=profile):
                stage = self.module.PROFILE_STAGE_SEQUENCES[profile][0]
                encoded = self.request(profile, stage)
                decoded = self.module.decode_request(encoded)
                self.assertEqual(decoded.profile, profile)
                self.assertEqual(
                    decoded.run_id, self.module.MODEL_RUN_IDS[profile].hex()
                )
                self.assertEqual(decoded.stage, stage)

    def test_request_rejects_crc_reserved_profile_run_and_stage_mutations(self):
        valid = bytearray(self.request("E1", self.module.STAGES["PROC_MOUNTED"]))
        mutations = []
        changed_crc = bytearray(valid)
        changed_crc[-1] ^= 1
        mutations.append(changed_crc)
        changed_reserved = bytearray(valid)
        changed_reserved[11] = 1
        mutations.append(changed_reserved)
        unknown_profile = bytearray(valid)
        unknown_profile[5] = 9
        unknown_profile[-4:] = self.module.struct.pack(
            "<I", self.module.crc32(unknown_profile[:-4])
        )
        mutations.append(unknown_profile)
        zero_run = bytearray(valid)
        zero_run[12:28] = bytes(16)
        zero_run[-4:] = self.module.struct.pack(
            "<I", self.module.crc32(zero_run[:-4])
        )
        mutations.append(zero_run)
        bad_stage = bytearray(valid)
        bad_stage[6] = self.module.STAGES["E2_SUCCESS"]
        bad_stage[-4:] = self.module.struct.pack(
            "<I", self.module.crc32(bad_stage[:-4])
        )
        mutations.append(bad_stage)
        for mutated in mutations:
            with self.subTest(mutated=bytes(mutated)), self.assertRaises(
                self.module.CheckError
            ):
                self.module.decode_request(bytes(mutated))

    def test_terminal_success_requires_exact_profile_terminal_stage(self):
        with self.assertRaises(self.module.CheckError):
            self.request(
                "E1",
                self.module.STAGES["CHILD_REAPED"],
                outcome=self.module.OUTCOME_SUCCESS,
            )
        encoded = self.request(
            "E1",
            self.module.STAGES["E1_SUCCESS"],
            outcome=self.module.OUTCOME_SUCCESS,
        )
        self.assertEqual(
            self.module.decode_request(encoded).outcome,
            self.module.OUTCOME_SUCCESS,
        )

    def test_immediate_terminal_success_is_not_the_exact_next_stage(self):
        region = self.module.initial_region(0x300000, 9)
        with self.assertRaises(self.module.CheckError):
            self.module.apply_request(
                region,
                self.request(
                    "E1",
                    self.module.STAGES["E1_SUCCESS"],
                    outcome=self.module.OUTCOME_SUCCESS,
                ),
            )

    def test_initial_region_has_one_valid_entry_slot(self):
        region = self.module.initial_region(0x300000, 9)
        decoded = self.module.decode_region(region)
        self.assertEqual(decoded["active"]["generation"], 0)
        self.assertEqual(decoded["active"]["stage"], self.module.STAGES["ENTRY"])
        self.assertIsNone(decoded["active"]["profile"])
        self.assertEqual(decoded["uncommitted_slots"], [1])
        self.assertFalse(decoded["identity_bound"])

    def test_ab_slots_alternate_and_remain_adjacent(self):
        region = self.module.initial_region(0x300000, 9)
        stages = self.module.PROFILE_STAGE_SEQUENCES["E1"][:3]
        for generation, stage in enumerate(stages, start=1):
            region = self.module.apply_request(region, self.request("E1", stage))
            active = self.module.decode_region(region, "E1")["active"]
            self.assertEqual(active["generation"], generation)
            self.assertEqual(active["slot_id"], generation & 1)
            self.assertEqual(active["stage"], stage)

    def test_torn_inactive_slot_preserves_prior_committed_generation(self):
        region = self.module.initial_region(0x300000, 9)
        region = self.module.apply_request(
            region, self.request("E1", self.module.STAGES["PROC_MOUNTED"])
        )
        before = self.module.decode_region(region, "E1")["active"]
        torn = bytearray(region)
        inactive = before["slot_id"] ^ 1
        start = self.module.ENTRY_SIZE + inactive * self.module.SLOT_SIZE
        torn[start : start + 31] = b"T" * 31
        torn[start + self.module.SLOT_SIZE - 1] = 0
        decoded = self.module.decode_region(bytes(torn), "E1")
        self.assertEqual(decoded["active"], before)
        self.assertEqual(decoded["uncommitted_slots"], [inactive])

    def test_bad_committed_new_slot_falls_back_to_prior_valid_slot(self):
        region = self.module.initial_region(0x300000, 9)
        region = self.module.apply_request(
            region, self.request("E1", self.module.STAGES["PROC_MOUNTED"])
        )
        damaged = bytearray(region)
        active = self.module.decode_region(region, "E1")["active"]
        start = self.module.ENTRY_SIZE + active["slot_id"] * self.module.SLOT_SIZE
        damaged[start + 20] ^= 1
        decoded = self.module.decode_region(bytes(damaged))
        self.assertEqual(decoded["active"]["generation"], 0)
        self.assertEqual(decoded["invalid_committed_slots"], [active["slot_id"]])

    def test_no_valid_committed_slot_fails_closed(self):
        region = bytearray(self.module.initial_region(0x300000, 9))
        region[self.module.ENTRY_SIZE + 20] ^= 1
        with self.assertRaises(self.module.CheckError):
            self.module.decode_region(bytes(region))

    def test_nonadjacent_generations_fail_closed(self):
        first = self.module.encode_slot(
            slot_id=0,
            generation=2,
            profile="E1",
            stage=self.module.STAGES["SYS_MOUNTED"],
            outcome=self.module.OUTCOME_PROGRESS,
            item_index=0,
            detail=0,
            run_id=self.module.MODEL_RUN_IDS["E1"],
            seed_idx=0x300000,
            boot_cnt=9,
        )
        second = self.module.encode_slot(
            slot_id=1,
            generation=5,
            profile="E1",
            stage=self.module.STAGES["DEV_NODES_VERIFIED"],
            outcome=self.module.OUTCOME_PROGRESS,
            item_index=0,
            detail=0,
            run_id=self.module.MODEL_RUN_IDS["E1"],
            seed_idx=0x300000,
            boot_cnt=9,
        )
        with self.assertRaises(self.module.CheckError):
            self.module.decode_region(self.module.ENTRY_PROOF + first + second)

    def test_slot_generation_parity_fails_closed(self):
        malformed = self.module.encode_slot(
            slot_id=0,
            generation=1,
            profile="E1",
            stage=self.module.STAGES["PROC_MOUNTED"],
            outcome=self.module.OUTCOME_PROGRESS,
            item_index=0,
            detail=0,
            run_id=self.module.MODEL_RUN_IDS["E1"],
            seed_idx=0x300000,
            boot_cnt=9,
        )
        with self.assertRaises(self.module.CheckError):
            self.module.decode_region(
                self.module.ENTRY_PROOF
                + malformed
                + bytes(self.module.SLOT_SIZE)
            )

    def test_profile_and_run_id_cannot_change_after_first_update(self):
        region = self.module.initial_region(0x300000, 9)
        region = self.module.apply_request(
            region, self.request("E2", self.module.STAGES["PROC_MOUNTED"])
        )
        with self.assertRaises(self.module.CheckError):
            self.module.apply_request(
                region, self.request("E1", self.module.STAGES["SYS_MOUNTED"])
            )
        with self.assertRaises(self.module.CheckError):
            self.module.apply_request(
                region,
                self.module.encode_request(
                    "E2",
                    self.module.STAGES["SYS_MOUNTED"],
                    run_id=b"R" * 16,
                ),
            )

    def test_terminal_slot_blocks_further_updates(self):
        region = self.advance("E1")
        self.assertTrue(self.module.decode_region(region, "E1")["terminal"])
        with self.assertRaises(self.module.CheckError):
            self.module.apply_request(
                region,
                self.request(
                    "E1",
                    self.module.STAGES["E1_SUCCESS"],
                    outcome=self.module.OUTCOME_SUCCESS,
                ),
            )

    def test_observer_requires_exact_run_and_boot_identity(self):
        region = self.module.initial_region(0x300000, 9)
        region = self.module.apply_request(
            region, self.request("E1", self.module.STAGES["PROC_MOUNTED"])
        )
        observer = b"prefix" + region + b"suffix"
        kwargs = {
            "expected_profile": "E1",
            "expected_run_id": self.module.MODEL_RUN_IDS["E1"],
            "expected_seed_idx": 0x300000,
            "expected_boot_cnt": 9,
        }
        decoded = self.module.decode_observer(observer, **kwargs)
        self.assertEqual(decoded["observer_offset"], len(b"prefix"))
        self.assertTrue(decoded["evidence_verified"])
        for changed in (
            {**kwargs, "expected_run_id": b"X" * 16},
            {**kwargs, "expected_seed_idx": 0x300001},
            {**kwargs, "expected_boot_cnt": 10},
        ):
            with self.assertRaises(self.module.CheckError):
                self.module.decode_observer(observer, **changed)
        for invalid in (
            observer + self.module.ENTRY_PROOF,
            b"prefix" + region[:-1],
            observer + b"[[S22P1E|foreign]]",
            observer + b"[[S22P1E",
            observer + b"[[S22P1",
        ):
            with self.assertRaises(self.module.CheckError):
                self.module.decode_observer(invalid, **kwargs)

    def test_impossible_seed_index_is_rejected_even_with_valid_crc(self):
        impossible = self.module.encode_slot(
            slot_id=1,
            generation=1,
            profile="E1",
            stage=self.module.STAGES["PROC_MOUNTED"],
            outcome=self.module.OUTCOME_PROGRESS,
            item_index=0,
            detail=0,
            run_id=self.module.MODEL_RUN_IDS["E1"],
            seed_idx=1,
            boot_cnt=0,
        )
        with self.assertRaises(self.module.CheckError):
            self.module.decode_region(
                self.module.ENTRY_PROOF + bytes(self.module.SLOT_SIZE) + impossible
            )

    def test_region_placement_is_contiguous_on_both_cursor_sides(self):
        payload = bytes(self.module.LOG_SIZE - 16)
        for cursor in (300, 50):
            with self.subTest(cursor=cursor):
                index = len(payload) + cursor
                updated, position = self.module.place_initial_region(payload, index, 9)
                expected = (
                    cursor - self.module.REGION_SIZE
                    if cursor >= self.module.REGION_SIZE
                    else len(payload) - self.module.REGION_SIZE
                )
                self.assertEqual(position, expected)
                self.assertEqual(
                    updated[position : position + self.module.REGION_SIZE],
                    self.module.initial_region(index, 9),
                )

    def test_region_placement_rejects_unsaturated_index(self):
        payload = bytes(512)
        for index in (0, 511, 0x1_0000_0000):
            with self.subTest(index=index), self.assertRaises(
                self.module.CheckError
            ):
                self.module.place_initial_region(payload, index, 9)

    def test_patch_and_source_contract_pass(self):
        patch_result = self.module.check_patch_policy(self.patch)
        source_result = self.module.check_patched_sources(self.patched)
        self.assertTrue(patch_result["verified"])
        self.assertTrue(source_result["verified"])
        self.assertFalse(source_result["index_mutated"])
        self.assertTrue(source_result["target_guarded_before_physical_dereference"])
        self.assertTrue(source_result["exact_stage_successor_enforced"])

    def test_source_contract_rejects_weakened_target_stage_and_commit_guards(self):
        main_path = "kernel_platform/common/init/main.c"
        mutations = (
            ("task_pid_nr(current) != 1", "false"),
            ("s22plus_fyg8_cp_target_allowed()", "true"),
            (
                "READ_ONCE(head->idx) == s22plus_fyg8_cp_state.seed_idx",
                "true",
            ),
            ("request->stage != expected", "request->stage < expected"),
            ("case 0x10: return 0x11;", "case 0x10: return 0x12;"),
            (
                "case 0x00: return 0x10;",
                "case 0x00: return 0x10;\n\tcase 0x00: return 0x10;",
            ),
            (
                "WRITE_ONCE(target->commit, S22PLUS_FYG8_CP_COMMIT);",
                "WRITE_ONCE(target->commit, 0);",
            ),
            (
                "memcpy(s22plus_fyg8_cp_state.run_id, request.run_id,\n"
                "\t\t       sizeof(s22plus_fyg8_cp_state.run_id));",
                "memcpy(s22plus_fyg8_cp_state.run_id, "
                "s22plus_fyg8_cp_state.run_id,\n"
                "\t\t       sizeof(s22plus_fyg8_cp_state.run_id));",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                patched = copy.deepcopy(self.patched)
                self.assertIn(old, patched[main_path])
                patched[main_path] = patched[main_path].replace(old, new, 1)
                with self.assertRaises(self.module.CheckError):
                    self.module.check_patched_sources(patched)

    def test_patch_policy_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "changed.patch"
            changed.write_bytes(self.patch.read_bytes() + b"\n")
            with self.assertRaises(self.module.CheckError):
                self.module.check_patch_policy(changed)

    def test_full_host_contract_has_no_build_or_device_authority(self):
        result = self.module.run_check(self.source, self.patch)
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["model_selfcheck"]["identity_bound"])
        self.assertTrue(result["run_manifest_binding"]["required_for_live_evidence"])
        self.assertFalse(result["safety"]["device_contact"])
        self.assertFalse(result["safety"]["kernel_build"])
        self.assertFalse(result["safety"]["candidate_packaged"])
        self.assertFalse(result["safety"]["live_authorized"])


if __name__ == "__main__":
    unittest.main()
