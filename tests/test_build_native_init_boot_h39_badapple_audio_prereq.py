"""Host-only contract for the H39 Bad Apple audio prerequisite image."""

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_h39_badapple_audio_prereq.py"


def load_builder():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h39_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H39BuilderTests(unittest.TestCase):
    def test_new_identity_and_claim_boundary(self) -> None:
        module = load_builder()
        self.assertEqual(module.CYCLE, "H39")
        self.assertEqual(module.INIT_VERSION, "0.12.003")
        self.assertEqual(module.INIT_BUILD, "h39-badapple-audio-prereq-v1")
        self.assertEqual(
            hashlib.sha256(module.HAZARD_STATEMENT.encode()).hexdigest(),
            module.HAZARD_STATEMENT_SHA256,
        )
        report = module.render_report({"boot_sha256": "0" * 64}, (), (module.EXTRA_FLAG,))
        self.assertIn("Runtime result: `unproved`", report)
        self.assertIn("does not prove `/dev/snd`, ADSP readiness", report)

    def test_build_enables_explicit_mount_before_chime(self) -> None:
        module = load_builder()
        module.configure()
        self.assertEqual(module.h38.FALLBACK_EXPECTED_INIT_FLAG_COUNT, 60)
        self.assertEqual(module.h38.FALLBACK_CYCLE_LABEL, "h39")
        self.assertIn(module.EXTRA_FLAG, module.h38.FALLBACK_REQUIRED_INIT_FLAGS)
        self.assertIn(
            b"audio.boot_prereq.firmware_mounts.cache_flag_required=0",
            module.h38.FALLBACK_REQUIRED_MARKERS,
        )


if __name__ == "__main__":
    unittest.main()
