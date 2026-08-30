"""Host-only contract tests for the H37 Bad Apple evidence builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h37_badapple_evidence.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h37_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H37BuilderTest(unittest.TestCase):
    def test_exact_equal_length_identity(self) -> None:
        module = load_module()
        self.assertEqual(module.CYCLE, "H37")
        self.assertEqual(module.INIT_VERSION, "0.12.001")
        self.assertEqual(module.INIT_BUILD, "h37-badapple-video-evidence-temporary-v001")
        self.assertEqual(len(module.OLD_VERSION), len(module.INIT_VERSION))
        self.assertEqual(len(module.OLD_BUILD), len(module.INIT_BUILD))
        self.assertEqual(
            len(f"A90 Linux init {module.OLD_VERSION} ({module.OLD_BUILD})"),
            len(f"A90 Linux init {module.INIT_VERSION} ({module.INIT_BUILD})"),
        )

    def test_inputs_and_outputs_are_exactly_scoped(self) -> None:
        module = load_module()
        private = ROOT / "workspace/private"
        self.assertTrue(module.BASE_BOOT.is_relative_to(private))
        self.assertTrue(module.STREAM.is_relative_to(private))
        self.assertTrue(module.OUT_DIR.is_relative_to(private))
        self.assertTrue(module.BOOT_IMAGE.is_relative_to(private))
        self.assertEqual(module.BASE_BOOT_SHA256, "57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1")
        self.assertEqual(module.STREAM_SHA256, "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0")


if __name__ == "__main__":
    unittest.main()
