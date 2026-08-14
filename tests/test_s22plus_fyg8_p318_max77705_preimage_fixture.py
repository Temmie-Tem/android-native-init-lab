import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_p318_max77705_preimage_fixture.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p318_max77705_preimage_fixture_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8P318Max77705PreimageFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = load_module().audit(ROOT)

    def test_actual_c_covers_every_positive_semantic(self):
        self.assertEqual(self.value["row_count"], 121)
        self.assertEqual(self.value["terminal_rows"], 15)
        self.assertEqual(self.value["mux_rows"], 5)
        self.assertEqual(self.value["overflow_rows"], 1)
        self.assertEqual(self.value["observer_site_error_rows"], 98)
        self.assertTrue(self.value["actual_c_python_byte_identity"])
        self.assertTrue(self.value["retained_vector_cross_group_unique"])
        self.assertEqual(len(set(self.value["receipts"].values())), 121)

    def test_eagain_and_claim_busy_obligations_remain_distinct(self):
        self.assertEqual(self.value["observable_eagain_rows"], 6)
        self.assertEqual(self.value["additional_eagain_rows"], 2)
        self.assertTrue(self.value["claim_busy_policy_rejected"])
        self.assertTrue(self.value["claim_busy_decoder_preimage_empty"])
        self.assertTrue(self.value["verified"])


if __name__ == "__main__":
    unittest.main()
