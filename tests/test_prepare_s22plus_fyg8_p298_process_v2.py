#!/usr/bin/env python3
"""Focused tests for the P2.98 Process-v2 offline-promotion adapter."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import prepare_s22plus_fyg8_p234_process_v2 as base  # noqa: E402
import prepare_s22plus_fyg8_p298_process_v2 as adapter  # noqa: E402
import s22plus_fyg8_p298_candidate_static_checker as checker  # noqa: E402
import s22plus_fyg8_p298_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p298_identity_tiers as identity  # noqa: E402
import s22plus_fyg8_p298_source_contract as contract  # noqa: E402
import s22plus_fyg8_p298_telemetry_decoder as telemetry_decoder  # noqa: E402


def receipt(data: bytes) -> dict[str, int | str]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class P298ProcessV2PromotionAdapterTest(unittest.TestCase):
    def repair_fixture(self) -> dict:
        artifact_names = set(checker.repro.ARTIFACT_LIMITS)
        build_a = {
            name: {"size": index + 1, "sha256": f"{index + 1:064x}"}
            for index, name in enumerate(sorted(artifact_names))
        }
        build_b = copy.deepcopy(build_a)
        build_b["build-result.json"] = {"size": 99, "sha256": "f" * 64}
        repair_files = {
            path.as_posix(): receipt((ROOT / path).read_bytes())
            for path in checker.TIER2_REPAIR_PATHS
        }
        repair = {
            "schema": "s22plus_fyg8_p298_postbuild_tier2_repair_v1",
            "historical_postbuild_result": checker.HISTORICAL_POSTBUILD_RESULT,
            "historical_pre_lto_qualification": checker.HISTORICAL_QUALIFICATION,
            "a_b_artifacts_reopened": {
                "build_a": build_a,
                "build_b": build_b,
            },
            "a_b_artifact_inodes_distinct": True,
            "byte_identical_artifacts_reverified": sorted(
                artifact_names - {"build-result.json"}
            ),
            "tier1_candidate_identity_changed": False,
            "tier2_repair_files": repair_files,
            "fresh_full_lto_claimed": False,
            "verified": True,
        }
        return {
            "build_repro": {
                "fresh_reverification": False,
                "image": build_a["Image"],
                "immutable_build_time_proof_revalidated": True,
                "linked_audit_verified": True,
                "result": checker.HISTORICAL_POSTBUILD_RESULT,
                "tier2_repair": repair,
                "two_clean_builds_byte_identical": True,
            }
        }

    def test_adapter_configures_only_the_versioned_frontier(self) -> None:
        previous_checker = base.static_checker
        with adapter._validation_context():
            self.assertIs(base.static_checker, checker)
            self.assertIs(base.e2_closure_selector, closure_selector)
            self.assertEqual(base.SCHEMA, adapter.SCHEMA)
            self.assertEqual(base.TARGET, checker.TARGET)
        self.assertIs(base.static_checker, previous_checker)

    def test_defaults_are_p298_scoped(self) -> None:
        args = adapter.parse_args([])
        for value in (args.candidate_static, args.candidate_ap, args.out):
            self.assertIn("s22plus_fyg8_p298", value.as_posix())

    def test_registered_decoder_and_e2_closure_select_p298(self) -> None:
        decoder = evidence._latest_stage_decoder(contract.CONTRACT_ID, "E2")
        closure = evidence._select_e2_closure(contract.CONTRACT_ID)
        self.assertEqual(decoder.DECODER_ID, telemetry_decoder.DECODER_ID)
        self.assertEqual(closure.source_contract.CONTRACT_ID, contract.CONTRACT_ID)
        self.assertEqual(evidence.P298_CANDIDATE_STATIC_SCHEMA, checker.SCHEMA)
        self.assertEqual(evidence.P298_CANDIDATE_STATIC_VERDICT, checker.VERDICT)

    def test_execution_receipts_bind_all_three_p298_tiers(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(
            {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "profile": "E2",
                "source_contract_id": contract.CONTRACT_ID,
            }
        )
        self.assertEqual(
            len(
                [name for name in receipts if name.startswith("candidate_source_")]
            ),
            len(contract.SOURCE_KEYS),
        )
        self.assertEqual(
            len([name for name in receipts if name.startswith("p298_tier2_")]),
            len(identity.tier2_materials(ROOT)),
        )
        self.assertEqual(
            len([name for name in receipts if name.startswith("p298_tier3_")]),
            len(identity.tier3_materials(ROOT)),
        )

    def test_historical_repair_contract_is_accepted(self) -> None:
        repair = adapter._historical_build_repair(self.repair_fixture())
        self.assertIs(repair["verified"], True)
        self.assertIs(repair["fresh_full_lto_claimed"], False)

    def test_historical_repair_contract_rejects_false_freshness(self) -> None:
        fixture = self.repair_fixture()
        fixture["build_repro"]["fresh_reverification"] = True
        with self.assertRaisesRegex(base.PromotionError, "immutable build-time"):
            adapter._historical_build_repair(fixture)

    def test_historical_repair_contract_rejects_unequal_a_b(self) -> None:
        fixture = self.repair_fixture()
        fixture["build_repro"]["tier2_repair"]["a_b_artifacts_reopened"][
            "build_b"
        ]["Image"] = {"size": 8, "sha256": "8" * 64}
        with self.assertRaisesRegex(base.PromotionError, "A/B Image receipt"):
            adapter._historical_build_repair(fixture)

    def test_historical_repair_contract_rejects_changed_repair_file(self) -> None:
        fixture = self.repair_fixture()
        first = checker.TIER2_REPAIR_PATHS[0].as_posix()
        fixture["build_repro"]["tier2_repair"]["tier2_repair_files"][first][
            "sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(base.PromotionError, "files changed"):
            adapter._historical_build_repair(fixture)

    def test_live_evidence_accepts_only_exact_historical_repair(self) -> None:
        fixture = self.repair_fixture()
        repair_files = evidence._validate_p298_historical_build_repair(
            fixture["build_repro"]
        )
        self.assertEqual(
            repair_files,
            fixture["build_repro"]["tier2_repair"]["tier2_repair_files"],
        )
        fixture["build_repro"]["tier2_repair"][
            "fresh_full_lto_claimed"
        ] = True
        with self.assertRaisesRegex(evidence.EvidenceError, "contract differs"):
            evidence._validate_p298_historical_build_repair(
                fixture["build_repro"]
            )

    def test_live_execution_binding_rechecks_tier2_repair_files(self) -> None:
        fixture = self.repair_fixture()
        execution = process_v2.execution_critical_source_receipts(
            {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "profile": "E2",
                "source_contract_id": contract.CONTRACT_ID,
            }
        )
        verification = {
            "source_contract_id": contract.CONTRACT_ID,
            "candidate_source_receipts": {
                name: execution[f"candidate_source_{name}"]
                for name in contract.SOURCE_KEYS
            },
            "tier2_repair_files": (
                evidence._validate_p298_historical_build_repair(
                    fixture["build_repro"]
                )
            ),
        }
        acceptance = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": "E2",
            "source_contract_id": contract.CONTRACT_ID,
        }
        process_v2.verify_candidate_source_binding(
            acceptance, verification, execution
        )
        mutated = copy.deepcopy(execution)
        mutated["p298_tier2_direct_p298_e2_stock_closure"]["sha256"] = (
            "0" * 64
        )
        with self.assertRaisesRegex(process_v2.F1V2Error, "Tier-2 repair differs"):
            process_v2.verify_candidate_source_binding(
                acceptance, verification, mutated
            )

    def test_validation_context_restores_generic_validator(self) -> None:
        original = base.validate_static
        with adapter._validation_context():
            self.assertIs(base.validate_static, adapter._validate_static_configured)
        self.assertIs(base.validate_static, original)

    def test_validation_context_restores_all_indirect_modules(self) -> None:
        def snapshot():
            return {
                module: dict(vars(module))
                for module in adapter._snapshot_indirect_modules()
            }

        before = snapshot()
        with adapter._validation_context():
            shared = next(
                module
                for module in before
                if module.__name__
                == "s22plus_fyg8_p286_candidate_static_checker"
            )
            self.assertEqual(shared.SCHEMA, checker.SCHEMA)
            self.assertEqual(shared.DEFAULT_CANDIDATE, checker.DEFAULT_CANDIDATE)
        after_success = snapshot()
        self.assertEqual(set(after_success), set(before))
        for module, values in before.items():
            self.assertEqual(set(after_success[module]), set(values))
            self.assertTrue(
                all(after_success[module][name] is value for name, value in values.items())
            )

        with self.assertRaisesRegex(RuntimeError, "forced"):
            with adapter._validation_context():
                raise RuntimeError("forced")
        after_exception = snapshot()
        for module, values in before.items():
            self.assertEqual(set(after_exception[module]), set(values))
            self.assertTrue(
                all(
                    after_exception[module][name] is value
                    for name, value in values.items()
                )
            )

    def test_adapter_has_no_live_or_device_transport(self) -> None:
        source = (
            SCRIPT_DIR / "prepare_s22plus_fyg8_p298_process_v2.py"
        ).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "device_action_f1_live_v2", "adb ", "flash"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
