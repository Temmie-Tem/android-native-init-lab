"""Host-only tests for the V2531 ACDB ioctl trace preload builder."""

from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2531 = load_revalidation("build_android_ioctl_trace_preload_v2531")


class BuildAndroidIoctlTracePreloadV2531(unittest.TestCase):
    def test_source_invariants(self) -> None:
        state = v2531.source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["exports_ioctl"])
        self.assertTrue(state["required"]["uses_raw_ioctl_syscall"])
        self.assertTrue(state["required"]["logs_audio_allocate_name"])
        self.assertTrue(state["required"]["logs_set_name_only"])
        self.assertFalse(state["prohibited"]["opens_msm_audio_cal"])
        self.assertFalse(state["prohibited"]["calls_acdb_ioctl"])

    def test_manifest_without_build_is_host_only(self) -> None:
        args = Namespace(
            build=False,
            build_root=Path(tempfile.mkdtemp(prefix="a90-v2531-build-")),
            clang=None,
            lld=v2531.TOOLCHAIN_ROOT / "bin/ld.lld",
            readelf=str(v2531.TOOLCHAIN_ROOT / "bin/llvm-readelf"),
            file="file",
        )

        payload = v2531.manifest(args)

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertTrue(payload["boundaries"]["observes_existing_ioctl_calls_only"])
        self.assertTrue(payload["boundaries"]["does_not_issue_extra_ioctl"])

    def test_private_build_exports_ioctl(self) -> None:
        args = Namespace(
            build=True,
            build_root=Path(tempfile.mkdtemp(prefix="a90-v2531-build-")),
            clang=None,
            lld=v2531.TOOLCHAIN_ROOT / "bin/ld.lld",
            readelf=str(v2531.TOOLCHAIN_ROOT / "bin/llvm-readelf"),
            file="file",
        )

        payload = v2531.manifest(args)

        self.assertTrue(payload["ok"], payload.get("build"))
        binary = payload["build"]["binary"]
        self.assertTrue(binary["exists"], binary)
        self.assertTrue(binary["symbols"]["exports_ioctl"], binary["symbols"])
        self.assertTrue(binary["symbols"]["undefined_errno"], binary["symbols"])
        self.assertTrue(binary["symbols"]["does_not_import_acdb"], binary["symbols"])
        self.assertIn("ELF 32-bit", binary["file"]["stdout"])


if __name__ == "__main__":
    unittest.main()
