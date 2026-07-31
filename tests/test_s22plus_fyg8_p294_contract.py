#!/usr/bin/env python3
"""Focused P2.94 successor contract tests."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p286_source_contracts as registry  # noqa: E402
import s22plus_fyg8_p294_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p294_identity_tiers as tiers  # noqa: E402
import s22plus_fyg8_p294_pre_lto_qualification as pre_lto  # noqa: E402
import s22plus_fyg8_p294_source_contract as p294  # noqa: E402
import s22plus_fyg8_p294_telemetry_model as model  # noqa: E402
import s22plus_fyg8_p294_telemetry_spec as spec  # noqa: E402


class P294ContractTest(unittest.TestCase):
    def test_selector_and_retirement(self) -> None:
        selected = registry.select(p294.CONTRACT_ID, p294.PROFILE)
        self.assertEqual(selected.contract_id, p294.CONTRACT_ID)
        self.assertEqual(intent.parse_args([]).profile, p294.PROFILE)
        self.assertIn(p294.CONTRACT_ID, intent.candidate_contract_ids())
        self.assertNotIn(registry.P292_CONTRACT_ID, intent.candidate_contract_ids())

    def test_tier1_equals_source_contract(self) -> None:
        source = p294.source_bytes(ROOT)
        self.assertEqual(set(source), set(p294.SOURCE_KEYS))
        self.assertEqual(len(source), 103)
        self.assertEqual(source, tiers.tier1_materials(ROOT))
        self.assertIn(b"s22_p294_dwc3_state_snapshot", source["base_patch"])

    def test_candidate_patch_rebinds_without_duplicate_defconfig(self) -> None:
        with intent._base_context():
            source, _receipts = intent.base.base.source_receipts(
                ROOT, p294.PROFILE, p294.CONTRACT_ID
            )
        run_id = bytes.fromhex("11" * 16)
        unsat = model.unsat_record(p294.PROFILE, run_id)
        unsat_tag = unsat[len(model.UNSAT_FAMILY) :]
        patch = intent.build_patch(
            source["base_patch"], run_id, unsat_tag, p294.PROFILE
        )
        result = intent.audit_patch(
            intent.DEFAULT_SOURCE,
            patch,
            run_id,
            unsat_tag,
            p294.PROFILE,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["targets"]), 5)

    def test_implementation_and_telemetry_closure(self) -> None:
        result = p294.implementation_result(ROOT)
        self.assertEqual(result["verdict"], p294.IMPLEMENTATION_VERDICT)
        self.assertEqual(result["source_key_count"], 103)
        telemetry = result["telemetry_closure"]
        self.assertEqual(telemetry["runtime_classifier"]["case_count"], 64512)
        self.assertEqual(telemetry["runtime_classifier"]["detail_count"], 149)
        self.assertTrue(telemetry["pair_adjacency"]["verified"])

    def test_linked_table_bytes_match_telemetry_sot(self) -> None:
        tables = p294.linked_table_bytes()
        rules = tables["s22_fyg8_p290_detail_rules"]
        self.assertEqual(len(rules), len(spec.exact_detail_rules()) * 4)
        self.assertIn(spec.LINK_STATE_DETAIL_BASE.to_bytes(2, "little"), rules)
        self.assertIn(spec.FIXED_MISMATCH_DETAIL_BASE.to_bytes(2, "little"), rules)

    def test_pre_lto_defaults_are_p294_bound_and_context_local(self) -> None:
        inherited = pre_lto.base.inherited.base.base
        previous_userspace = inherited.DEFAULT_USERSPACE_RESULT
        previous_lifecycle = inherited.DEFAULT_LIFECYCLE_RESULT
        args = pre_lto.parse_args([])
        self.assertEqual(args.userspace_result, pre_lto.DEFAULT_USERSPACE_RESULT)
        self.assertEqual(args.lifecycle_result, pre_lto.DEFAULT_LIFECYCLE_RESULT)
        self.assertEqual(inherited.DEFAULT_USERSPACE_RESULT, previous_userspace)
        self.assertEqual(inherited.DEFAULT_LIFECYCLE_RESULT, previous_lifecycle)


if __name__ == "__main__":
    unittest.main()
