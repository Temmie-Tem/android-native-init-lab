import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_transfer_manifest.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_kernel_transfer_manifest_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8KernelTransferManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_every_file_has_sensitivity_and_hash_policy(self):
        for _path, _role, sensitivity, expected in self.module.FILE_SPECS:
            self.assertIn(sensitivity, {"public", "private-proprietary"})
            if sensitivity == "private-proprietary" and expected is not None:
                self.assertEqual(len(expected), 64)

    def test_host_requirements_match_full_lto_floor(self):
        self.assertEqual(30 * 1024**3, 32212254720)
        self.assertEqual(len(self.module.REPO_SPECS), 4)
        self.assertEqual(
            self.module.REPO_SPECS[0][3],
            "toolchains/aosp-clang-android12-release",
        )
        self.assertTrue(self.module.REPO_SPECS[1][3].startswith("source/"))

    def test_transfer_contains_repo_root_markers(self):
        paths = {str(item[0]) for item in self.module.FILE_SPECS}
        self.assertIn("AGENTS.md", paths)
        self.assertIn("GOAL.md", paths)
        self.assertIn(
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_r2_audit.py",
            paths,
        )
        self.assertIn(
            "docs/module-map/s22plus-fyg8/symbol-crc-requirements.tsv",
            paths,
        )
        self.assertIn(
            "docs/module-map/s22plus-fyg8-super/layout-manifest.json",
            paths,
        )


if __name__ == "__main__":
    unittest.main()
