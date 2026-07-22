import importlib
import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P226ArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p221_builder = importlib.import_module(
            "build_s22plus_fyg8_p221_candidate"
        )
        cls.artifact = importlib.import_module(
            "s22plus_fyg8_p225_build_artifact_contract"
        )
        cls.builder = importlib.import_module(
            "build_s22plus_fyg8_p226_candidate"
        )
        cls.checker = importlib.import_module(
            "s22plus_fyg8_p226_candidate_static_checker"
        )

    def test_adapters_bind_p225_inputs_without_mutating_p221_core(self):
        original_schema = self.p221_builder.SCHEMA
        args = self.builder.parse_args([])
        self.assertEqual(args.image, self.builder.DEFAULT_IMAGE)
        self.assertEqual(args.vmlinux, self.builder.DEFAULT_VMLINUX)
        self.assertEqual(args.out, self.builder.DEFAULT_OUT)
        self.assertEqual(self.p221_builder.SCHEMA, original_schema)
        self.assertNotEqual(self.builder.SCHEMA, original_schema)

    def test_exact_private_artifact_and_candidate_closure(self):
        if os.environ.get("S22PLUS_P226_ARTIFACT_AUDIT") != "1":
            self.skipTest("set S22PLUS_P226_ARTIFACT_AUDIT=1 for private closure")
        build_root = ROOT / "workspace/private/outputs/s22plus_fyg8_p225_build/artifacts"
        result = self.artifact.verify(
            image=(build_root / "Image").read_bytes(),
            vmlinux=(build_root / "vmlinux").read_bytes(),
            config=(build_root / ".config").read_bytes(),
            build_result=(build_root / "build-result.json").read_bytes(),
            vmlinux_path=build_root / "vmlinux",
        )
        self.assertTrue(result["verified"])
        self.assertFalse(result["reset_retention_proven"])
        static_path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p226_candidate/"
            "static-check-result.json"
        )
        static = json.loads(static_path.read_text(encoding="ascii"))
        self.assertEqual(static["schema"], self.checker.SCHEMA)
        self.assertEqual(static["verdict"], self.checker.VERDICT)
        self.assertTrue(static["candidate"]["verified"])
        self.assertTrue(static["candidate"]["extracted_artifact_closure"]["boot_only_ap"])
        self.assertFalse(static["candidate"]["writer_exclusion"]["sec_log_buf_loaded"])
        self.assertFalse(static["safety"]["live_authorized"])


if __name__ == "__main__":
    unittest.main()
