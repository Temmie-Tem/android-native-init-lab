import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_max77705_checkpoint_fixture.py"


def load_fixture():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_checkpoint_fixture_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class Max77705CheckpointTest(unittest.TestCase):
    def test_actual_c_request_v3_publisher(self) -> None:
        fixture = load_fixture()
        result = fixture.audit()
        self.assertTrue(result["verified"])
        self.assertEqual(result["request_count"], 15)
        self.assertEqual(result["request_bytes"], 1500)
        self.assertEqual(result["terminal_bucket_preimages"], 9)
        self.assertEqual(result["mux_class_preimages"], 5)
        self.assertTrue(result["existing_v2_publisher_byte_identical"])
        self.assertTrue(result["actual_c_bytes_equal_carrier_model"])


if __name__ == "__main__":
    unittest.main()
