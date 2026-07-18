import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_r4w1b_historical_fixture_check.py"


class S22PlusR4W1BHistoricalFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1b_fixture_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_frozen_private_fixture_passes(self):
        args = self.module.parse_args([])
        result = self.module.audit(args)
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["checks"]["fixed_slice_exact_historical_boot"])
        self.assertTrue(result["checks"]["deterministic_ap_exact_historical_ap"])

    def test_checker_imports_only_builder_primitive(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("import s22plus_boot_slice as boot_slice", source)
        self.assertNotIn("build_s22plus_fyg8_r4w1a_candidate", source)
        self.assertNotIn("s22plus_fyg8_r4w1a_static_checker", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("adb", source.lower())
        self.assertNotIn("fastboot", source.lower())


if __name__ == "__main__":
    unittest.main()
