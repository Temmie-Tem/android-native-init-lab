#!/usr/bin/env python3
"""Focused tests for P2.92 Stage C three-tier identities."""

from __future__ import annotations

import unittest

import s22plus_fyg8_p292_identity_mutation_matrix as matrix
import s22plus_fyg8_p292_identity_tiers as tiers


class IdentityMutationMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = matrix.zero.repo_root()

    def test_descriptor_validates(self) -> None:
        result = tiers.validate()
        self.assertTrue(result["verified"])
        self.assertEqual(result["generated_payload_count"], 13)
        self.assertEqual(result["tier1_source_key_count"], 93)
        self.assertGreater(result["inherited_nonpayload_key_count"], 0)
        self.assertEqual(
            result["path_validation"]["multi_tier_path_count"], 0
        )
        self.assertEqual(
            result["path_validation"]["zero_tier_path_count"], 0
        )

    def test_real_mutation_matrix_passes(self) -> None:
        result = matrix.run_matrix(self.root)
        self.assertEqual(result["verdict"], matrix.VERDICT)
        self.assertEqual(len(result["mutations"]), 7)
        self.assertTrue(
            result["tier_assignment"][
                "moving_path_requires_descriptor_change"
            ]
        )
        self.assertTrue(
            result["downstream_rejection"][
                "stale_qualification_rejected"
            ]
        )
        self.assertFalse(
            result["stage_c"]["independent_review_complete"]
        )

    def test_duplicate_assignment_fails(self) -> None:
        values = {
            name: list(paths)
            for name, paths in tiers.path_tiers().items()
        }
        values["tier1_payload"].append(values["tier2_qualification"][0])
        with self.assertRaises(tiers.IdentityTierError):
            tiers.validate_path_tiers(values)

    def test_unassigned_path_fails(self) -> None:
        values = {
            name: list(paths)
            for name, paths in tiers.path_tiers().items()
        }
        universe = set().union(*(set(paths) for paths in values.values()))
        values["tier2_qualification"].pop()
        with self.assertRaises(tiers.IdentityTierError):
            tiers.validate_path_tiers(
                values, expected_universe=universe
            )


if __name__ == "__main__":
    unittest.main()
