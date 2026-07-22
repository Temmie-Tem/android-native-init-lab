import argparse
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load_module(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tested", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P233E1ImplementationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.model = load_module("s22plus_fyg8_p232_e1_latest_stage_design")
        cls.decoder = load_module("s22plus_fyg8_p233_e1_decoder")
        cls.checker = load_module("s22plus_fyg8_p233_e1_static_checker")
        cls.evidence = load_module("device_action_f1_evidence_v2")
        cls.live = load_module("device_action_f1_live_v2")
        cls.check_result = cls.checker.build_result(
            argparse.Namespace(
                source=cls.checker.DEFAULT_SOURCE,
                patch=cls.checker.DEFAULT_PATCH,
                client=cls.checker.DEFAULT_CLIENT,
                runtime=cls.checker.DEFAULT_RUNTIME,
                legacy_runtime=cls.checker.DEFAULT_LEGACY_RUNTIME,
                header=cls.checker.DEFAULT_HEADER,
                child=cls.checker.DEFAULT_CHILD,
            )
        )
        cls.run_id = hashlib.sha256(b"P233-TEST-NON-MODEL-RUN").digest()[:16]

    @classmethod
    def acceptance(cls, profile="E1A", run_id=None):
        run_id = cls.run_id if run_id is None else run_id
        artifact = {
            "path": "workspace/private/p233-placeholder.json",
            "size": 1,
            "sha256": "1" * 64,
        }
        return {
            "kind": cls.evidence.E1_LATEST_STAGE_KIND,
            "source": cls.evidence.CHECKPOINT_SOURCE,
            "decoder": cls.decoder.DECODER_ID,
            "policy_id": cls.decoder.POLICY_ID,
            "profile": profile,
            "run_id": run_id.hex(),
            "long_family_hex": cls.model.LONG_FAMILY.hex(),
            "unsat_family_hex": cls.model.UNSAT_FAMILY.hex(),
            "terminal_stage": cls.model.PROFILE_TERMINALS[profile],
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                "candidate_static": dict(artifact),
                "run_manifest": dict(artifact),
                "static_check": dict(artifact),
            },
        }

    def complete(self, profile="E1A"):
        record = self.model.initialize_record(profile, self.run_id)
        for stage in self.model.PROFILE_STAGE_SEQUENCES[profile]:
            terminal = stage == self.model.PROFILE_TERMINALS[profile]
            request = self.model.encode_request(
                profile,
                stage,
                run_id=self.run_id,
                outcome=(
                    self.model.OUTCOME_SUCCESS
                    if terminal
                    else self.model.OUTCOME_PROGRESS
                ),
                item_index=self.model._expected_item_index(stage),
            )
            record = self.model.apply_request(record, request)
        return record

    def test_source_implementation_static_contract_passes(self):
        result = self.check_result
        self.assertEqual(result["verdict"], self.checker.VERDICT)
        self.assertTrue(result["patch"]["clean_apply"])
        self.assertTrue(result["patch"]["default_disabled"])
        self.assertEqual(
            result["patch"]["targets"], sorted(self.checker.PATCH_TARGETS)
        )
        self.assertEqual(
            result["reachable_record_contract"]["reachable_slot_variants"],
            90114,
        )
        self.assertEqual(
            result["reachable_record_contract"]["zero_crc_count"], 0
        )
        self.assertEqual(
            result["reachable_record_contract"]["family_collision_count"], 0
        )
        self.assertTrue(
            result["reachable_record_contract"][
                "adjacent_slot_combinations_verified"
            ]
        )
        for profile, run_id in result["reachable_record_contract"][
            "checked_run_ids"
        ].items():
            self.assertNotEqual(run_id, self.model.model_run_id(profile).hex())
        self.assertTrue(result["safety"]["host_only"])
        self.assertTrue(
            all(
                not value
                for name, value in result["safety"].items()
                if name != "host_only"
            )
        )

    def test_reachable_contract_accepts_one_candidate_identity(self):
        result = self.checker.validate_reachable_records({"E1A": self.run_id})
        self.assertEqual(result["profiles"], ["E1A"])
        self.assertEqual(result["checked_run_ids"], {"E1A": self.run_id.hex()})
        self.assertEqual(result["reachable_slot_variants"], 32769)

    def test_e1a_excludes_and_e1b_includes_exact_watchdog_closure(self):
        linked = self.check_result["linked_userspace"]
        self.assertEqual(set(linked["E1A"]["module_string_counts"].values()), {0})
        self.assertEqual(set(linked["E1B"]["module_string_counts"].values()), {1})
        self.assertLess(linked["E1A"]["size"], linked["E1B"]["size"])
        self.assertEqual(self.check_result["sources"]["watchdog_module_count"], 5)
        self.assertTrue(self.check_result["sources"]["sec_log_buf_absent"])

    def test_patch_geometry_mutation_is_rejected(self):
        source = self.checker.resolve(ROOT, self.checker.DEFAULT_SOURCE)
        patch_path = self.checker.resolve(ROOT, self.checker.DEFAULT_PATCH)
        original = patch_path.read_bytes()
        mutated = original.replace(
            b"#define S22_FYG8_E1_LONG_SIZE\t\t45U",
            b"#define S22_FYG8_E1_LONG_SIZE\t\t46U",
            1,
        )
        self.assertNotEqual(mutated, original)
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "mutated.patch"
            candidate.write_bytes(mutated)
            with self.assertRaises(self.checker.CheckError):
                self.checker.audit_patch(source, candidate, mutated)

    def test_patch_must_preserve_active_slot_item_index(self):
        source = self.checker.resolve(ROOT, self.checker.DEFAULT_SOURCE)
        patch_path = self.checker.resolve(ROOT, self.checker.DEFAULT_PATCH)
        original = patch_path.read_bytes()
        mutated = original.replace(
            b"s22_fyg8_e1_state.item_index, 0,",
            b"0, 0,",
            1,
        )
        self.assertNotEqual(mutated, original)
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "mutated.patch"
            candidate.write_bytes(mutated)
            with self.assertRaises(self.checker.CheckError):
                self.checker.audit_patch(source, candidate, mutated)

    def test_decoder_accepts_terminal_success_among_valid_boot_states(self):
        entry = self.model.initialize_record("E1A", self.run_id)
        failure = self.model.apply_request(
            entry,
            self.model.encode_request(
                "E1A",
                self.model.STAGES["PROC_MOUNTED"],
                run_id=self.run_id,
                outcome=self.model.OUTCOME_FAILURE,
                detail=5,
            ),
        )
        observed = entry + b"gap" + failure + b"gap" + self.complete()
        decoded = self.decoder.classify_observation(
            observed,
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertTrue(decoded["accepted"])
        self.assertEqual(decoded["entry_count"], 1)
        self.assertEqual(decoded["failure_count"], 1)
        self.assertEqual(decoded["success_count"], 1)

    def test_decoder_rejects_malformed_record_even_with_success(self):
        malformed = bytearray(self.model.initialize_record("E1A", self.run_id))
        malformed[31] ^= 1
        decoded = self.decoder.classify_observation(
            self.complete() + b"gap" + bytes(malformed),
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertFalse(decoded["accepted"])
        self.assertTrue(decoded["integrity_issue"])

    def test_baseline_rejects_all_related_families_and_partials(self):
        clean = self.decoder.classify_clean_baseline(
            b"ordinary retained data",
            expected_profile="E1A",
            expected_run_id=self.run_id,
        )
        self.assertTrue(clean["baseline_clean"])
        for payload in (
            self.model.LONG_FAMILY,
            self.model.UNSAT_FAMILY,
            self.model.LEGACY_FAMILIES[0],
            b"prefix" + self.model.LONG_FAMILY[:6],
        ):
            with self.subTest(payload=payload):
                dirty = self.decoder.classify_clean_baseline(
                    payload,
                    expected_profile="E1A",
                    expected_run_id=self.run_id,
                )
                self.assertFalse(dirty["baseline_clean"])
                self.assertTrue(dirty["integrity_issue"])

    def test_process_v2_adapter_is_opt_in_and_classifies_raw_success(self):
        acceptance = self.acceptance()
        self.evidence.validate_acceptance(acceptance)
        result = self.evidence.classify_e1_latest_stage(
            self.complete(), acceptance
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["policy_id"], self.decoder.POLICY_ID)
        live_result = self.live.classify_acceptance(self.complete(), acceptance)
        self.assertEqual(live_result["classification"], result["classification"])
        self.assertTrue(live_result["accepted"])

    def test_process_v2_adapter_rejects_model_identity(self):
        model_id = self.model.model_run_id("E1A")
        with self.assertRaises(self.evidence.EvidenceError):
            self.evidence.validate_acceptance(self.acceptance(run_id=model_id))

    def test_source_only_adapter_cannot_become_live_ready(self):
        acceptance = self.acceptance()
        with self.assertRaisesRegex(
            self.evidence.EvidenceError, "no candidate-bound offline contract"
        ):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads={},
                receipts={},
                candidate_ap={"size": 1, "sha256": "2" * 64},
            )

    def test_adapter_clean_baseline_dispatch_is_fail_closed(self):
        acceptance = self.acceptance()
        clean = self.evidence.classify_clean_baseline(b"ordinary", acceptance)
        self.assertTrue(clean["baseline_clean"])
        dirty = self.evidence.classify_clean_baseline(
            self.model.UNSAT_FAMILY, acceptance
        )
        self.assertFalse(dirty["baseline_clean"])
        self.assertTrue(dirty["integrity_issue"])


if __name__ == "__main__":
    unittest.main()
