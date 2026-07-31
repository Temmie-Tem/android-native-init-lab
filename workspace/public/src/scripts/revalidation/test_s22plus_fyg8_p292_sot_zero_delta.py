#!/usr/bin/env python3
"""Focused tests for the P2.92 SoT zero-delta gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

import s22plus_fyg8_p292_checkpoint_sot as sot
import s22plus_fyg8_p292_sot_generator as generator
import s22plus_fyg8_p292_sot_zero_delta as zero


class ZeroDeltaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = zero.repo_root()

    @staticmethod
    def _make_writable(path: Path) -> None:
        os.chmod(path, 0o600)

    def test_sot_descriptor_validates(self) -> None:
        result = sot.validate()
        self.assertTrue(result["verified"])
        self.assertEqual(result["position_count"], 107)
        self.assertEqual(
            result["state_representation"],
            "p290-field-subset-without-outcome-detail",
        )

    def test_real_retained_baseline_passes(self) -> None:
        result = zero.run_zero_delta(self.root)
        self.assertEqual(result["verdict"], zero.VERDICT)
        self.assertEqual(result["baseline"]["artifact_count"], 13)
        self.assertTrue(result["run_a"]["baseline_fidelity"])
        self.assertTrue(result["run_b"]["baseline_fidelity"])
        self.assertTrue(result["run_b"]["run_a_determinism"])
        self.assertFalse(result["scope"]["comparison_weakened"])
        self.assertFalse(result["scope"]["repair_present"])

    def test_run_a_mismatch_prevents_run_b(self) -> None:
        calls = 0

        def bad_first(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            nonlocal calls
            calls += 1
            result = generator.materialize(*args, **kwargs)
            target = args[1] / "candidate.patch"
            self._make_writable(target)
            target.write_bytes(target.read_bytes() + b"x")
            os.chmod(target, 0o400)
            return result

        with self.assertRaises(zero.ZeroDeltaError):
            zero.run_zero_delta(self.root, materialize=bad_first)
        self.assertEqual(calls, 1)

    def test_run_b_mismatch_fails_after_run_a(self) -> None:
        calls = 0

        def bad_second(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            nonlocal calls
            calls += 1
            result = generator.materialize(*args, **kwargs)
            if calls == 2:
                target = args[1] / "candidate.patch"
                self._make_writable(target)
                target.write_bytes(target.read_bytes() + b"x")
                os.chmod(target, 0o400)
            return result

        with self.assertRaises(zero.ZeroDeltaError):
            zero.run_zero_delta(self.root, materialize=bad_second)
        self.assertEqual(calls, 2)

    def test_authority_mismatch_prevents_generation(self) -> None:
        calls = 0
        baseline = json.loads(zero.BASELINE_MANIFEST.read_text())
        baseline["authority"]["sha256"] = "0" * 64

        def should_not_run(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            nonlocal calls
            calls += 1
            return generator.materialize(*args, **kwargs)

        with tempfile.TemporaryDirectory(prefix="s22-p292-bad-baseline-") as tmp:
            manifest = Path(tmp) / "baseline.json"
            manifest.write_text(json.dumps(baseline), encoding="ascii")
            with self.assertRaises(zero.ZeroDeltaError):
                zero.run_zero_delta(
                    self.root,
                    manifest_path=manifest,
                    materialize=should_not_run,
                )
        self.assertEqual(calls, 0)

    def test_extra_generated_artifact_fails_closed(self) -> None:
        calls = 0

        def with_extra(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            nonlocal calls
            calls += 1
            result = generator.materialize(*args, **kwargs)
            extra = args[1] / "unexpected"
            extra.write_bytes(b"x")
            return result

        with self.assertRaises(zero.ZeroDeltaError):
            zero.run_zero_delta(self.root, materialize=with_extra)
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
