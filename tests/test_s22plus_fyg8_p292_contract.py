#!/usr/bin/env python3
"""Focused P2.92 successor contract tests."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p286_source_contracts as registry  # noqa: E402
import s22plus_fyg8_p292_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p292_identity_tiers as tiers  # noqa: E402
import s22plus_fyg8_p292_source_contract as p292  # noqa: E402


class P292ContractTest(unittest.TestCase):
    def test_selector_and_retirement(self) -> None:
        selected = registry.select(p292.CONTRACT_ID, p292.PROFILE)
        self.assertEqual(selected.contract_id, p292.CONTRACT_ID)
        self.assertIn(p292.CONTRACT_ID, intent.candidate_contract_ids())
        self.assertNotIn(
            registry.p290.CONTRACT_ID, intent.candidate_contract_ids()
        )

    def test_tier1_equals_source_contract(self) -> None:
        source = p292.source_bytes(ROOT)
        self.assertEqual(set(source), set(p292.SOURCE_KEYS))
        self.assertEqual(len(source), 93)
        self.assertEqual(source, tiers.tier1_materials(ROOT))
        self.assertIn(b"struct s22_fyg8_e1_slot active;", source["base_patch"])

    def test_implementation_and_sequence_closure(self) -> None:
        result = p292.implementation_result(ROOT)
        self.assertEqual(result["verdict"], p292.IMPLEMENTATION_VERDICT)
        self.assertEqual(result["source_key_count"], 93)
        self.assertEqual(
            result["accept_to_resume"]["closure_case_count"], 171
        )
        self.assertEqual(
            result["accept_to_resume"]["sequence_walk_snapshots"], 214
        )

    def test_reachable_records_include_publication_errno(self) -> None:
        result = p292.validate_reachable_records(
            p292.SOURCE_CHECK_RUN_ID
        )
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["publication_errno_round_trips"],
            3 * 0xFFF,
        )
        self.assertEqual(
            result["publication_position_checks"],
            (len(p292.spec.POSITIONS) - 1) * 3,
        )


if __name__ == "__main__":
    unittest.main()
