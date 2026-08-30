"""Host-only identity and boundary tests for the H41 demo candidate."""

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h41_badapple_video_demo.py"


def load_builder():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h41_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H41BuilderTests(unittest.TestCase):
    def test_fresh_identity_and_unproved_boundary(self) -> None:
        module = load_builder()
        self.assertEqual(module.CYCLE, "H41")
        self.assertEqual(module.INIT_VERSION, "0.12.008")
        self.assertEqual(module.INIT_BUILD, "h41-badapple-video-demo-v2")
        self.assertEqual(
            hashlib.sha256(module.HAZARD_STATEMENT.encode()).hexdigest(),
            module.HAZARD_STATEMENT_SHA256,
        )
        report = module.render_report({"boot_sha256": "0" * 64}, (), ())
        self.assertIn("Runtime result: `unproved`", report)
        self.assertIn("do not prove H41", report)
        self.assertIn("H40 candidate and rollback attempts remain consumed", report)

    def test_runtime_configuration_preserves_h40_lifecycle(self) -> None:
        module = load_builder()
        module.configure()
        self.assertEqual(module.h38.FALLBACK_CYCLE_LABEL, "h40v3")
        self.assertEqual(module.h38.FALLBACK_EXPECTED_INIT_FLAG_COUNT, 61)
        self.assertIn(module.h40.MOUNT_FLAG, module.h38.FALLBACK_REQUIRED_INIT_FLAGS)
        self.assertIn(module.h40.SIBLING_FLAG, module.h38.FALLBACK_REQUIRED_INIT_FLAGS)
        self.assertIs(
            module.h38.CONSTRUCTION_EXTRAS["bootChimeBeforeInteractiveHudFork"], True
        )
        self.assertEqual(module.h38.CONSTRUCTION_EXTRAS["audioSyncWaitMs"], 10000)
        self.assertEqual(
            module.h38.CONSTRUCTION_EXTRAS["sourceRuntimeDeltaFromH40V3"],
            "version-and-build-identity-only",
        )


if __name__ == "__main__":
    unittest.main()
