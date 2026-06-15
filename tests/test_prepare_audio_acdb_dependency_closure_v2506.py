"""Host-only tests for the V2506 private ACDB dependency closure prep script."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation

v2506 = load_revalidation("prepare_audio_acdb_dependency_closure_v2506")


class PrepareAudioAcdbDependencyClosureV2506(unittest.TestCase):
    def test_contract_lists_vendor_closure_and_runtime_external_libs(self) -> None:
        self.assertEqual(v2506.VENDOR_LIBS[0], "libaudcal.so")
        self.assertIn("libdiag.so", v2506.VENDOR_LIBS)
        self.assertIn("libacdbloader.so", v2506.VENDOR_LIBS)
        self.assertIn("libtinyalsa.so", v2506.EXPECTED_SYSTEM_RUNTIME_LIBS)
        self.assertIn("libion.so", v2506.EXPECTED_SYSTEM_RUNTIME_LIBS)
        self.assertTrue(str(v2506.DEFAULT_OUT_DIR).endswith("workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib"))

    def test_dry_manifest_reports_missing_when_output_absent(self) -> None:
        import tempfile
        from argparse import Namespace

        root = Path(tempfile.mkdtemp(prefix="a90-v2506-test-"))
        payload = v2506.build_manifest(Namespace(
            vendor_image=root / "missing.ext4",
            out_dir=root / "out",
            manifest_path=root / "manifest.json",
            debugfs="debugfs",
            readelf="readelf",
            extract=False,
        ))

        self.assertEqual(payload["decision"], "v2506-acdb-dependency-closure-host-only")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["ok"])
        self.assertIn("libdiag.so", payload["missing_vendor_libs"])


if __name__ == "__main__":
    unittest.main()
