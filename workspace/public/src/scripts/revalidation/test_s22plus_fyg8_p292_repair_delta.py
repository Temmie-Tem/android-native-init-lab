#!/usr/bin/env python3
"""Focused tests for the attributed P2.92 repair delta."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

import s22plus_fyg8_p292_repair_delta as delta
import s22plus_fyg8_p292_repair_generator as generator
import s22plus_fyg8_p292_repair_spec as spec


class RepairDeltaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = delta.zero.repo_root()

    @staticmethod
    def _rewrite(path: Path, data: bytes) -> None:
        os.chmod(path, 0o600)
        path.write_bytes(data)
        os.chmod(path, 0o400)

    def test_repair_spec_validates(self) -> None:
        result = spec.validate()
        self.assertTrue(result["verified"])
        self.assertEqual(result["repair_artifact_count"], 5)
        self.assertEqual(result["retained_record_size"], 45)
        self.assertEqual(result["retained_slot_count"], 2)

    def test_publication_error_round_trip(self) -> None:
        for operation in (
            spec.OPERATION_OPEN,
            spec.OPERATION_WRITE,
            spec.OPERATION_CLOSE,
        ):
            for error in (-1, -5, -116, -spec.ERRNO_MAX):
                detail = spec.encode_publication_error(operation, error)
                self.assertEqual(
                    spec.decode_publication_error(detail),
                    (operation, error),
                )
                self.assertTrue(
                    spec.is_publication_error_detail(
                        spec.OUTCOME_FAILURE, detail
                    )
                )

    def test_real_repair_delta_passes(self) -> None:
        result = delta.run_repair_delta(self.root)
        self.assertEqual(result["verdict"], delta.VERDICT)
        self.assertEqual(
            set(result["delta"]["actual_changed_keys"]),
            spec.REPAIR_ARTIFACT_KEYS,
        )
        self.assertEqual(result["delta"]["unchanged_key_count"], 8)
        self.assertTrue(result["delta"]["run_a_b_determinism"])
        self.assertFalse(result["delta"]["comparison_weakened"])

    def test_undeclared_delta_fails(self) -> None:
        def bad(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            result = generator.materialize(*args, **kwargs)
            target = (
                args[1]
                / "materialized-sources"
                / "s22plus_fyg8_p286_e3_plan.h"
            )
            self._rewrite(target, target.read_bytes() + b"x")
            return result

        with self.assertRaises(delta.RepairDeltaError):
            delta.run_repair_delta(self.root, materialize=bad)

    def test_missing_declared_delta_fails(self) -> None:
        baseline = (
            self.root
            / "workspace/private/outputs/s22plus_fyg8_p290/intent"
            / "materialized-sources/s22plus_r4w1e_checkpoint.h"
        ).read_bytes()

        def bad(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            result = generator.materialize(*args, **kwargs)
            target = (
                args[1]
                / "materialized-sources"
                / "s22plus_r4w1e_checkpoint.h"
            )
            self._rewrite(target, baseline)
            return result

        with self.assertRaises(delta.RepairDeltaError):
            delta.run_repair_delta(self.root, materialize=bad)

    def test_run_b_mutation_fails(self) -> None:
        calls = 0

        def bad(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            nonlocal calls
            calls += 1
            result = generator.materialize(*args, **kwargs)
            if calls == 2:
                target = args[1] / "candidate.patch"
                self._rewrite(target, target.read_bytes() + b"x")
            return result

        with self.assertRaises(delta.RepairDeltaError):
            delta.run_repair_delta(self.root, materialize=bad)
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
