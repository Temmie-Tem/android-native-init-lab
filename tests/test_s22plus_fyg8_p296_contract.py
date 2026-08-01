#!/usr/bin/env python3
"""Focused contract tests for the P2.96 built-in DWC3 successor."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import s22plus_fyg8_p286_source_contracts as selector
import s22plus_fyg8_p296_candidate_intent as candidate_intent
import s22plus_fyg8_p296_change_freeze as change_freeze
import s22plus_fyg8_p296_identity_tiers as identity
import s22plus_fyg8_p296_linked_audit as linked
import s22plus_fyg8_p296_source_contract as contract
import s22plus_fyg8_p296_telemetry_generator as generator
import s22plus_fyg8_p296_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[1]


class P296ContractTests(unittest.TestCase):
    def test_selector_and_identity(self) -> None:
        selected = selector.select(contract.CONTRACT_ID, contract.PROFILE)
        self.assertEqual(selected.contract.contract_id, contract.CONTRACT_ID)
        result = identity.validate()
        self.assertEqual(
            result["tier1_source_key_count"],
            len(contract.SOURCE_KEYS),
        )
        self.assertEqual(result["generated_payload_count"], 13)

    def test_generated_patch_is_boot_deliverable(self) -> None:
        source = generator.generate_bytes(
            ROOT,
            run_id=identity.SOURCE_CHECK_RUN_ID,
            unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
            profile=contract.PROFILE,
        )
        patch = source["candidate_patch"]
        self.assertIn(b"s22_p294_dwc3_state_snapshot", patch)
        self.assertNotIn(b"s22_p294_wrapper_vbus_snapshot", patch)
        self.assertNotIn(b"dwc3-msm-core.c", patch)
        self.assertEqual(
            linked.LINKED_VALIDATOR_SYMBOLS[-1],
            "s22_p294_dwc3_state_snapshot",
        )

    def test_linked_detail_table_uses_current_sot(self) -> None:
        tables = contract.linked_table_bytes()
        rules = tables["s22_fyg8_p290_detail_rules"]
        self.assertEqual(len(rules), len(spec.exact_detail_rules()) * 4)
        self.assertTrue(linked.normalize_linked_table_storage(tables, tables)[1])

    def test_reachable_records_cover_all_telemetry_values(self) -> None:
        result = contract.validate_reachable_records(
            bytes.fromhex("1234567890abcdef1234567890abcdef")
        )
        self.assertEqual(result["telemetry_reachable_variants"], 157)
        self.assertTrue(result["verified"])

    def test_complete_implementation_closure(self) -> None:
        result = contract.implementation_result(ROOT)
        self.assertEqual(result["verdict"], contract.IMPLEMENTATION_VERDICT)
        self.assertTrue(result["patch"]["driver_clean_apply"])
        self.assertEqual(result["patch"]["external_module_patch_count"], 0)
        self.assertTrue(result["telemetry_closure"]["delivery"]["verified"])

    def test_candidate_intent_nested_sot_generation_uses_inherited_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p296-intent-") as temporary:
            output = Path(temporary) / "intent"
            args = candidate_intent.parse_args(
                [
                    "--source-contract-id",
                    contract.CONTRACT_ID,
                    "--profile",
                    contract.PROFILE,
                    "--out",
                    str(output),
                ]
            )
            result = candidate_intent.create(args)
        self.assertEqual(result["verdict"], contract.INTENT_VERDICT)
        self.assertEqual(result["source_contract_id"], contract.CONTRACT_ID)

    def test_change_freeze_excludes_only_verified_a90_commit(self) -> None:
        derived = change_freeze.git_derived_changed_paths(ROOT)
        result = change_freeze.validate_declared_change_set(derived)
        self.assertTrue(result["exact_bidirectional_match"])
        self.assertEqual(
            result["excluded_foreign_target_commit"],
            change_freeze.INTERLEAVED_FOREIGN_TARGET_COMMIT,
        )


if __name__ == "__main__":
    unittest.main()
