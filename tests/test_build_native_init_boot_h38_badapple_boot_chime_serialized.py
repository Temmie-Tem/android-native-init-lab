"""Host-only contract for the H38 boot-chime serialization image."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h38_badapple_boot_chime_serialized.py"


def load_builder():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h38_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H38BuilderTests(unittest.TestCase):
    def test_candidate_is_new_and_runtime_unproved(self) -> None:
        module = load_builder()
        self.assertEqual(module.CYCLE, "H38")
        self.assertEqual(module.INIT_VERSION, "0.12.002")
        self.assertEqual(module.INIT_BUILD, "h38-badapple-boot-chime-serialized-v1")
        self.assertIn(b"audio.boot_chime.owner=pid1-tracked-worker", module.REQUIRED_STRINGS)
        report = module.render_report({"boot_sha256": "0" * 64}, (), ())
        self.assertIn("Runtime result: `unproved`", report)
        self.assertIn("Device action: `none`", report)
        self.assertIn(module.HAZARD_ID, report)
        self.assertIn(module.HAZARD_STATEMENT_SHA256, report)

    def test_candidate_and_rollback_paths_remain_private(self) -> None:
        module = load_builder()
        self.assertIn("workspace/private", str(module.BOOT_IMAGE))
        self.assertEqual(module.BASE_BOOT, module.previous.BOOT_IMAGE)


if __name__ == "__main__":
    unittest.main()
