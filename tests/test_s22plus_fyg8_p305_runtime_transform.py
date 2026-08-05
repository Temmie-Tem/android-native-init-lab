from __future__ import annotations

import sys
import unittest
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p304_generator as p304  # noqa: E402
import s22plus_fyg8_p304_overlay_contract as contract  # noqa: E402
import s22plus_fyg8_p305_generator as generator  # noqa: E402
import s22plus_fyg8_p305_runtime_transform as subject  # noqa: E402


@lru_cache(maxsize=1)
def _runtime() -> bytes:
    parent = contract.verify_parent(ROOT)
    generated = p304.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(parent["run_id"]),
        unsat_tag=bytes.fromhex(parent["unsat_tag_hex"]),
        profile=parent["profile"],
    )
    return generated["runtime_wrapper"]


class RuntimeTransformTest(unittest.TestCase):
    def test_transform_folds_exact_final_pair_without_shifting_gate(self) -> None:
        result = subject.transform(_runtime())
        self.assertIn(b"index < P305_FOLDED_MODULE_INDEX", result)
        self.assertIn(b"index = P305_FOLDED_MODULE_INDEX", result)
        self.assertIn(b"p241_load_and_verify_module(index)", result)
        self.assertIn(
            b"S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX",
            result,
        )
        self.assertIn(b"S22_P241_GATE_STAGE_BASE 0x7cU", result)
        self.assertIn(b"S22PLUS_O2_MODULE_PLAN_COUNT == 61U", result)

    def test_transform_retains_exact_tail_failure_index(self) -> None:
        result = subject.transform(_runtime())
        start = result.index(b"long p305_folded_load_rc")
        end = result.index(b"long p305_checkpoint_rc", start)
        branch = result[start:end]
        self.assertIn(b"P305_FOLDED_FAILURE_BASE + index", branch)
        self.assertIn(b"fail_at(", branch)
        self.assertEqual(subject.FOLDED_FAILURE_BASE + 59, 0x73B)
        self.assertEqual(subject.FOLDED_FAILURE_BASE + 60, 0x73C)

    def test_transform_statically_separates_module_and_gate_stages(self) -> None:
        result = subject.transform(_runtime())
        self.assertIn(
            b"S22_P241_GATE_STAGE_BASE > S22_P241_MODULE_STAGE_BASE",
            result,
        )
        self.assertIn(
            b"P305_FOLDED_MODULE_INDEX <\n            S22_P241_GATE_STAGE_BASE",
            result,
        )
        self.assertIn(b"S22PLUS_O2_MODULE_PLAN_COUNT <= 256U", result)

    def test_transform_rejects_already_transformed_or_wrong_shape(self) -> None:
        runtime = _runtime()
        transformed = subject.transform(runtime)
        with self.assertRaises(subject.TransformError):
            subject.transform(transformed)
        with self.assertRaises(subject.TransformError):
            subject.transform(
                runtime.replace(
                    b"index < S22PLUS_O2_MODULE_PLAN_COUNT",
                    b"index <= S22PLUS_O2_MODULE_PLAN_COUNT",
                    1,
                )
            )

    def test_generator_changes_only_runtime_wrapper(self) -> None:
        parent = contract.verify_parent(ROOT)
        baseline = p304.generate_bytes(
            ROOT,
            run_id=bytes.fromhex(parent["run_id"]),
            unsat_tag=bytes.fromhex(parent["unsat_tag_hex"]),
            profile=parent["profile"],
        )
        result = generator.generate_bytes(
            ROOT,
            run_id=bytes.fromhex(parent["run_id"]),
            unsat_tag=bytes.fromhex(parent["unsat_tag_hex"]),
            profile=parent["profile"],
        )
        self.assertEqual(
            {key for key in result if result[key] != baseline[key]},
            {"runtime_wrapper"},
        )
        self.assertEqual(result["plan_header"], baseline["plan_header"])
        self.assertEqual(result["candidate_patch"], baseline["candidate_patch"])


if __name__ == "__main__":
    unittest.main()
