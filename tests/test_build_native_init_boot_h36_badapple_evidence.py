"""Host-only source contract for the fresh A90 H36 demo candidate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h36_badapple_evidence.py"


def load_module():
    scripts = SCRIPT.parent
    public_src = ROOT / "workspace/public/src"
    sys.path.insert(0, str(public_src))
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("a90_h36_badapple_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H36BadAppleEvidenceBuilderTest(unittest.TestCase):
    def test_identity_and_evidence_boundary(self) -> None:
        module = load_module()
        self.assertEqual(module.CYCLE, "H36")
        self.assertEqual(module.INIT_VERSION, "0.12.0")
        self.assertEqual(module.INIT_BUILD, "h36-badapple-video-evidence-demo-v1")
        self.assertEqual(len(module.OLD_VERSION), len(module.INIT_VERSION))
        self.assertEqual(len(module.OLD_BUILD), len(module.INIT_BUILD))
        self.assertEqual(module.STREAM_SHA256, "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0")

    def test_build_outputs_remain_private(self) -> None:
        module = load_module()
        private = ROOT / "workspace/private"
        self.assertTrue(module.OUT_DIR.is_relative_to(private))
        self.assertTrue(module.BOOT_IMAGE.is_relative_to(private))
        self.assertTrue(module.MANIFEST.is_relative_to(private))


if __name__ == "__main__":
    unittest.main()
