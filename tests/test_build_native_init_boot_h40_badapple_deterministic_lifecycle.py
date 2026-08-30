"""Host-only builder contract for the H40 Bad Apple lifecycle candidate."""

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h40_badapple_deterministic_lifecycle.py"


def load_builder():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h40_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H40BuilderTests(unittest.TestCase):
    def test_identity_hazard_and_unproved_boundary(self) -> None:
        module = load_builder()
        self.assertEqual(module.CYCLE, "H40")
        self.assertEqual(module.INIT_VERSION, "0.12.006")
        self.assertEqual(module.INIT_BUILD, "h40-badapple-deterministic-lifecycle-v3")
        self.assertEqual(
            hashlib.sha256(module.HAZARD_STATEMENT.encode()).hexdigest(),
            module.HAZARD_STATEMENT_SHA256,
        )
        report = module.render_report({"boot_sha256": "0" * 64}, (), ())
        self.assertIn("Runtime result: `unproved`", report)
        self.assertIn("remain unproved", report)

    def test_build_binds_both_boot_prerequisites_and_lifecycle_markers(self) -> None:
        module = load_builder()
        module.configure()
        self.assertEqual(module.h38.FALLBACK_EXPECTED_INIT_FLAG_COUNT, 61)
        self.assertEqual(module.h38.FALLBACK_CYCLE_LABEL, "h40v3")
        self.assertIn(module.MOUNT_FLAG, module.h38.FALLBACK_REQUIRED_INIT_FLAGS)
        self.assertIn(module.SIBLING_FLAG, module.h38.FALLBACK_REQUIRED_INIT_FLAGS)
        self.assertIn(
            b"video.stream.audio_sync.cancelled_by_physical_input=1",
            module.h38.FALLBACK_REQUIRED_MARKERS,
        )
        self.assertEqual(module.h38.CONSTRUCTION_EXTRAS["audioSyncWaitMs"], 10000)
        self.assertIs(
            module.h38.CONSTRUCTION_EXTRAS["bootChimeBeforeInteractiveHudFork"], True
        )


if __name__ == "__main__":
    unittest.main()
