import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "build_s22plus_fyg8_r4w1d_candidate.py"
REPRO = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_r4w1d_static_repro_20260721/repro/result.json"
)
CARRIER = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i/carrier.boot.img"
)
IMAGE = ROOT / "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate_inputs/Image"


class S22PlusFyg8R4W1DCandidateBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1d_builder_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_reproduction_result_and_real_candidate_contract(self):
        receipt = self.module.verify_reproduction_result(REPRO.read_bytes())
        self.assertEqual(receipt["schema"], self.module.REPRO_SCHEMA)
        candidate, construction = self.module.build_candidate_bytes(
            CARRIER.read_bytes(), IMAGE.read_bytes()
        )
        self.assertEqual(len(candidate), self.module.engine.BOOT_SIZE)
        self.assertTrue(construction["marker"]["valid_single_exact"])
        self.assertEqual(
            self.module.engine.boot_slice.sha256_bytes(candidate),
            "18db8c8d8f32b2d128131937865454af50ab255bc5c922a00ba29d0d0b0e6fa0",
        )

    def test_reproduction_mutation_fails_closed(self):
        data = json.loads(REPRO.read_bytes())
        data["images"][0]["family_count"] = 2
        with self.assertRaises(self.module.BuildError):
            self.module.verify_reproduction_result(json.dumps(data).encode())

    def test_engine_binding_is_restored(self):
        before = {
            name: getattr(self.module.engine, name)
            for name in ("SCHEMA", "RUNG", "CARRIER_SHA256", "MARKER")
        }
        with self.module._bind_engine_contract():
            self.assertEqual(self.module.engine.SCHEMA, self.module.SCHEMA)
            self.assertEqual(self.module.engine.RUNG, "R4W1-D")
        self.assertEqual(
            before,
            {
                name: getattr(self.module.engine, name)
                for name in ("SCHEMA", "RUNG", "CARRIER_SHA256", "MARKER")
            },
        )

    def test_source_has_no_device_or_live_authority(self):
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for token in ("adb", "fastboot", "--execute", "candidate_flash_start"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
