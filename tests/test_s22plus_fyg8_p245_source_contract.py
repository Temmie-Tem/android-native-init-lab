import argparse
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as runner  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as contract  # noqa: E402
import s22plus_fyg8_p234_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p245_e2_stock_closure as stock  # noqa: E402
import s22plus_fyg8_p245_source_contract as p245  # noqa: E402


class S22PlusFyg8P245SourceContractTest(unittest.TestCase):
    NONCE = "45" * 16

    @classmethod
    def setUpClass(cls):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="p245-source-contract-", dir=private_tmp
        )
        cls.directory = Path(cls.temporary.name)
        cls.intent_dir = cls.directory / "intent"
        cls.intent_result = intent.create(
            argparse.Namespace(
                source=intent.DEFAULT_SOURCE,
                base_patch=None,
                out=cls.intent_dir,
                nonce_hex=cls.NONCE,
                profile="E2",
                source_contract_id=p245.CONTRACT_ID,
            )
        )
        cls.exact_contract = contract.verify(
            ROOT,
            ROOT / intent.DEFAULT_SOURCE,
            cls.intent_dir / "candidate-intent.json",
            cls.intent_dir / "candidate.patch",
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_registry_and_reachability_are_explicit_and_nonmutating(self):
        self.assertEqual(p245.P245.profile, "E2")
        self.assertEqual(len(p245.STAGE_SEQUENCE), 80)
        self.assertEqual(p245.STAGE_SEQUENCE[-1], 0x8F)
        self.assertEqual(p245.REACHABLE_VARIANTS, 323_585)
        self.assertEqual(
            set(self.intent_result["identity_preimage"]["sources"]),
            set(p245.SOURCE_KEYS),
        )
        self.assertIn("source_contract", p245.SOURCE_KEYS)
        self.assertEqual(
            p245.receipt(
                (
                    ROOT
                    / p245.COMMON_SOURCE_PATHS["legacy_stock_closure"]
                ).read_bytes()
            ),
            {
                "size": 20_194,
                "sha256": (
                    "f252aabf00b06bc6b919761778d588fbf"
                    "1af88ce00ba8eb4d7e7db21d3bc2c87"
                ),
            },
        )

        old_sequence = p245.model.PROFILE_STAGE_SEQUENCES["E2"]
        old_gate = p245.model.STAGES["E2_GATE_7"]
        result = p245.validate_reachable_records(
            bytes.fromhex(self.exact_contract["run_id"])
        )
        self.assertEqual(result["reachable_slot_variants"], 323_585)
        self.assertIs(p245.model.PROFILE_STAGE_SEQUENCES["E2"], old_sequence)
        self.assertEqual(p245.model.STAGES["E2_GATE_7"], old_gate)

    def test_intent_contract_and_materialized_sources_are_exact(self):
        self.assertEqual(self.intent_result["schema"], p245.INTENT_SCHEMA)
        self.assertEqual(self.exact_contract["schema"], p245.CONTRACT_SCHEMA)
        self.assertEqual(
            self.exact_contract["source_contract_id"], p245.CONTRACT_ID
        )
        self.assertEqual(
            self.exact_contract["reachable_record_contract"][
                "reachable_slot_variants"
            ],
            323_585,
        )
        materialized = self.intent_dir / "materialized-sources"
        self.assertEqual(
            {path.name for path in materialized.iterdir()},
            set(p245.MATERIALIZED_FILENAMES.values()),
        )
        generated = p245.source_bytes(ROOT)
        for name, filename in p245.MATERIALIZED_FILENAMES.items():
            self.assertEqual((materialized / filename).read_bytes(), generated[name])

    def test_retained_p242_intent_still_reopens_exactly(self):
        legacy_dir = (
            ROOT / "workspace/private/outputs/s22plus_fyg8_p242/intent"
        )
        legacy_intent = legacy_dir / "candidate-intent.json"
        legacy_patch = legacy_dir / "candidate.patch"
        if not legacy_intent.is_file() or not legacy_patch.is_file():
            self.skipTest("retained private P2.42 intent is unavailable")
        result = contract.verify(
            ROOT,
            ROOT / intent.DEFAULT_SOURCE,
            legacy_intent,
            legacy_patch,
        )
        self.assertEqual(result["schema"], contract.SCHEMA)
        self.assertEqual(result["verdict"], contract.VERDICT)
        self.assertEqual(result["profile"], "E2")
        self.assertNotIn("source_contract_id", result)
        self.assertEqual(result["run_id"], "16148a4f80688a599bd1dec09ae0d69d")

    def test_materialized_source_tampering_fails_closed(self):
        copied = self.directory / "tampered"
        shutil.copytree(self.intent_dir, copied)
        plan = (
            copied
            / "materialized-sources"
            / p245.MATERIALIZED_FILENAMES["plan_header"]
        )
        plan.chmod(0o600)
        plan.write_bytes(plan.read_bytes() + b"\n")
        with self.assertRaisesRegex(
            contract.ContractError, "materialized source mismatch"
        ):
            contract.verify(
                ROOT,
                ROOT / intent.DEFAULT_SOURCE,
                copied / "candidate-intent.json",
                copied / "candidate.patch",
            )

    def test_process_v2_source_binding_is_contract_specific(self):
        normalized = evidence.validate_candidate_source_preimage(
            self.exact_contract,
            "E2",
            self.exact_contract["run_id"],
        )
        self.assertEqual(set(normalized), set(p245.SOURCE_KEYS))
        acceptance = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": p245.decoder.DECODER_ID,
            "policy_id": p245.decoder.POLICY_ID,
            "profile": "E2",
            "source_contract_id": p245.CONTRACT_ID,
            "run_id": self.exact_contract["run_id"],
            "long_family_hex": evidence.e1_latest_stage.model.LONG_FAMILY.hex(),
            "unsat_family_hex": evidence.e1_latest_stage.model.UNSAT_FAMILY.hex(),
            "terminal_stage": 0x8F,
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                name: {
                    "path": f"private/{name}.json",
                    "size": 1,
                    "sha256": "1" * 64,
                }
                for name in ("candidate_static", "run_manifest", "static_check")
            },
        }
        self.assertEqual(
            evidence.validate_acceptance(acceptance)["source_contract_id"],
            p245.CONTRACT_ID,
        )
        execution = runner.execution_critical_source_receipts(acceptance)
        verification = {
            "source_contract_id": p245.CONTRACT_ID,
            "candidate_source_receipts": normalized,
        }
        runner.verify_candidate_source_binding(
            acceptance, verification, execution
        )
        changed = copy.deepcopy(verification)
        changed["candidate_source_receipts"]["plan_header"] = {
            "size": 1,
            "sha256": "0" * 64,
        }
        with self.assertRaisesRegex(
            runner.F1V2Error, "differs from execution-critical sources"
        ):
            runner.verify_candidate_source_binding(
                acceptance, changed, execution
            )

    def test_p245_decoder_classifies_added_gates_and_terminal_exactly(self):
        run_id = bytes.fromhex(self.exact_contract["run_id"])
        model = p245.decoder.model
        header = (
            model.LONG_FAMILY
            + bytes(
                [
                    (model.FORMAT_VERSION << 4)
                    | model.PROFILE_NUMBERS["E2"]
                ]
            )
            + run_id
        )

        def record(stage, outcome, detail):
            generation = p245.STAGE_SEQUENCE.index(stage) + 1
            previous_stage = p245.STAGE_SEQUENCE[generation - 2]
            slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
            slots[(generation - 1) & 1] = p245.decoder.encode_slot(
                header,
                generation=generation - 1,
                stage=previous_stage,
                outcome=model.OUTCOME_PROGRESS,
                item_index=(
                    previous_stage - p245.p244_sources.GATE_STAGE_FIRST
                    if p245.p244_sources.GATE_STAGE_FIRST
                    <= previous_stage
                    <= p245.p244_sources.GATE_STAGE_LAST
                    else 0
                ),
                detail=0,
            )
            slots[generation & 1] = p245.decoder.encode_slot(
                header,
                generation=generation,
                stage=stage,
                outcome=outcome,
                item_index=(
                    stage - p245.p244_sources.GATE_STAGE_FIRST
                    if p245.p244_sources.GATE_STAGE_FIRST
                    <= stage
                    <= p245.p244_sources.GATE_STAGE_LAST
                    else 0
                ),
                detail=detail,
            )
            return header + b"".join(slots)

        acceptance = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": p245.decoder.DECODER_ID,
            "policy_id": p245.decoder.POLICY_ID,
            "profile": "E2",
            "source_contract_id": p245.CONTRACT_ID,
            "run_id": run_id.hex(),
            "long_family_hex": model.LONG_FAMILY.hex(),
            "unsat_family_hex": model.UNSAT_FAMILY.hex(),
            "terminal_stage": p245.decoder.TERMINAL_STAGE,
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                name: {
                    "path": f"private/{name}.json",
                    "size": 1,
                    "sha256": "1" * 64,
                }
                for name in ("candidate_static", "run_manifest", "static_check")
            },
        }
        for stage in range(0x83, 0x87):
            result = evidence.classify_e1_latest_stage(
                record(stage, model.OUTCOME_FAILURE, 110),
                acceptance,
            )
            self.assertEqual(result["classification"], "E2_FAILURE_OBSERVED")
            self.assertFalse(result["integrity_issue"])
            self.assertEqual(result["records"][0]["active"]["stage"], stage)

        terminal = evidence.classify_e1_latest_stage(
            record(p245.decoder.TERMINAL_STAGE, model.OUTCOME_SUCCESS, 0),
            acceptance,
        )
        self.assertEqual(
            terminal["classification"], "E2_SUCCESS_ONE_OR_MORE_BOOTS"
        )
        self.assertTrue(terminal["accepted"])
        self.assertEqual(terminal["fallback_record_count"], 0)
        self.assertEqual(len(terminal["records"][0]["valid_slots"]), 2)

    def test_userspace_and_stock_module_closure_are_p245_bound(self):
        output = self.directory / "userspace"
        result = userspace.build_userspace(
            argparse.Namespace(
                source=intent.DEFAULT_SOURCE,
                intent=self.intent_dir / "candidate-intent.json",
                patch=self.intent_dir / "candidate.patch",
                out=output,
            )
        )
        self.assertEqual(result["verdict"], userspace.P245_E2_VERDICT)
        self.assertTrue(result["two_build_byte_identical"])
        self.assertEqual(
            result["outputs"]["init"]["module_string_counts"],
            {
                name: 1
                for name in userspace._e2_module_files(
                    ROOT,
                    p245.CONTRACT_ID,
                    self.intent_dir / "materialized-sources",
                )
            },
        )
        implementation = result["source_contract"]["source"]
        self.assertEqual(
            implementation["implementation_verdict"],
            p245.p244_checker.VERDICT,
        )

        required = (stock.DEFAULT_VENDOR_RAMDISK, stock.DEFAULT_LZ4)
        if not all((ROOT / path).exists() for path in required):
            self.skipTest("exact FYG8 private stock inputs are unavailable")
        closure = stock.derive_module_closure(
            ROOT,
            ROOT / stock.DEFAULT_VENDOR_RAMDISK,
            ROOT / stock.DEFAULT_LZ4,
            plan_header=(
                self.intent_dir
                / "materialized-sources"
                / p245.MATERIALIZED_FILENAMES["plan_header"]
            ),
        )
        self.assertEqual(closure["count"], 59)
        self.assertEqual(
            stock.closure_sha256(closure),
            stock.EXPECTED_MODULE_CLOSURE_SHA256,
        )

    def test_contract_selector_cannot_be_removed_or_relabelled(self):
        value = json.loads(
            (self.intent_dir / "candidate-intent.json").read_text("ascii")
        )
        value.pop("source_contract_id")
        altered = self.directory / "selector-removed.json"
        altered.write_text(json.dumps(value, sort_keys=True), encoding="ascii")
        with self.assertRaisesRegex(
            contract.ContractError, "source-contract identity"
        ):
            contract.verify(
                ROOT,
                ROOT / intent.DEFAULT_SOURCE,
                altered,
                self.intent_dir / "candidate.patch",
            )

    def test_intent_cli_reports_selected_schema_and_contract(self):
        output = self.directory / "cli-intent"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = intent.main(
                [
                    "--source",
                    str(intent.DEFAULT_SOURCE),
                    "--out",
                    str(output),
                    "--nonce-hex",
                    "56" * 16,
                    "--profile",
                    "E2",
                    "--source-contract-id",
                    p245.CONTRACT_ID,
                ]
            )
        self.assertEqual(rc, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["schema"], p245.INTENT_SCHEMA)
        self.assertEqual(summary["verdict"], p245.INTENT_VERDICT)
        self.assertEqual(summary["source_contract_id"], p245.CONTRACT_ID)


if __name__ == "__main__":
    unittest.main()
