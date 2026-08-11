import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_max77705_runtime_parser_fixture.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_runtime_parser_fixture_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8Max77705RuntimeParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_actual_c_parser_and_summary(self):
        value = self.module.audit(ROOT)
        self.assertEqual(value["valid_vector_count"], 4)
        self.assertEqual(value["invalid_mutation_count"], 13)
        self.assertTrue(value["python_summary_matches_actual_c"])
        self.assertTrue(value["strict_module_string_grammar"])
        self.assertTrue(value["aarch64_freestanding_compile"])
        self.assertFalse(value["sysfs_path_or_driver_override_integrated"])
        self.assertTrue(value["fresh_d0_still_required"])
        self.assertTrue(value["verified"])


if __name__ == "__main__":
    unittest.main()
