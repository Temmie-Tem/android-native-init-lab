import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_p318_dwc3_latch_parser_qualification.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p318_dwc3_latch_parser_qualification_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8P318Dwc3LatchParserQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = load_module().audit(ROOT)

    def test_exact_snapshot_and_gate_grammar(self):
        self.assertEqual(self.value["valid_snapshot_count"], 5)
        self.assertEqual(self.value["invalid_snapshot_count"], 14)
        self.assertTrue(self.value["masked_raw_kind_cross_check"])
        self.assertTrue(self.value["gate_readback_exact_one_newline"])

    def test_cross_compiles_but_is_not_integrated(self):
        self.assertTrue(self.value["aarch64_freestanding_compile"])
        self.assertFalse(self.value["runtime_integration"])
        self.assertFalse(self.value["candidate_ready"])
        self.assertTrue(self.value["verified"])


if __name__ == "__main__":
    unittest.main()
