import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_p318_max77705_runtime_parser_fixture.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p318_max77705_runtime_parser_fixture_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8P318Max77705RuntimeParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_actual_timed_parser_and_summary(self):
        value = self.module.audit(ROOT)
        self.assertEqual(value["valid_vector_count"], 4)
        self.assertEqual(value["invalid_mutation_count"], 14)
        self.assertTrue(value["timing_mask_and_value_bijection"])
        self.assertTrue(value["source_reachable_stage_masks"])
        self.assertTrue(value["monotonic_sample_order_enforced"])
        self.assertEqual(value["retention_minimum_ns"], 30_000_000_000)
        self.assertTrue(value["aarch64_freestanding_compile"])
        self.assertFalse(value["candidate_ready"])
        self.assertTrue(value["verified"])


if __name__ == "__main__":
    unittest.main()
