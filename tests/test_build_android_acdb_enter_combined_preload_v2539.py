"""Host-only tests for the V2539 ACDB enter-trace combined preload build."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2539 = load_revalidation("build_android_acdb_enter_combined_preload_v2539")


def args(**overrides):
    root = Path(tempfile.mkdtemp(prefix="a90-v2539-test-"))
    values = {
        "build": False,
        "build_root": root,
        "manifest_path": root / "manifest.json",
        "clang": v2539.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2539.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": str(v2539.TOOLCHAIN_ROOT / "bin/llvm-readelf"),
        "file_cmd": "file",
    }
    values.update(overrides)
    return type("Args", (), values)()


class V2539BuildTests(unittest.TestCase):
    def test_source_state_has_enter_logging_and_boundaries(self) -> None:
        state = v2539.source_state()
        self.assertTrue(state["required_ok"], state)
        self.assertTrue(state["prohibited_ok"], state)
        self.assertTrue(state["required"]["tap_enter_macro"])
        self.assertTrue(state["required"]["tap_enter_event"])

    def test_manifest_describes_enter_trace_delta(self) -> None:
        payload = v2539.manifest(args())
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["boundaries"]["logs_enter_before_real_acdb_ioctl"])
        self.assertIn("pre-return", payload["v2538_delta"])
        self.assertEqual(payload["artifact_name"], v2539.ARTIFACT_NAME)

    @unittest.skipUnless(
        (v2539.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2539.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android ARM32 clang/lld not available",
    )
    def test_build_exports_both_hooks(self) -> None:
        payload = v2539.manifest(args(build=True))
        self.assertTrue(payload["ok"], payload)
        binary = payload["build"]["binary"]
        self.assertEqual(binary["mode"], "0o600")
        self.assertTrue(binary["symbols"]["exports_acdb_ioctl"], binary)
        self.assertTrue(binary["symbols"]["exports_ioctl"], binary)
        self.assertTrue(binary["symbols"]["undefined_dlsym"], binary)
        self.assertTrue(binary["symbols"]["undefined_errno"], binary)
        self.assertIn("ARM", binary["file"]["stdout"])


if __name__ == "__main__":
    unittest.main()
