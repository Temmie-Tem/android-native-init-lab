"""Tests for the V2600 ACDB indirect-buffer tap build gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2600 = load_revalidation("build_android_acdb_indirect_buffer_tap_v2600")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2600-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "write_report": False,
        "report_path": root / "report.md",
        "clang": None,
        "lld": v2600.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": str(v2600.TOOLCHAIN_ROOT / "bin/llvm-readelf"),
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbIndirectBufferTapV2600(unittest.TestCase):
    def test_source_state_requires_default_off_indirect_capture_support(self) -> None:
        state = v2600.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["tap_capture_inbuf_macro"])
        self.assertTrue(state["required"]["tap_capture_indirect_macro"])
        self.assertTrue(state["required"]["tap_auto_arm_default_off"])
        self.assertTrue(state["required"]["tap_kinded_raw_paths"])
        self.assertTrue(state["required"]["tap_zero_buffer_guard"])
        self.assertFalse(state["prohibited"]["tap_opens_msm_audio_cal"])

    def test_dry_run_contract_is_host_only_and_future_gated(self) -> None:
        payload = v2600.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["android_action"], "none")
        self.assertTrue(payload["capture_contract"]["manual_post_init_arm_required"])
        self.assertTrue(payload["capture_contract"]["dumps_full_inbuf_when_compiled"])
        self.assertTrue(payload["capture_contract"]["scans_bounded_len_ptr_candidates"])
        self.assertTrue(payload["capture_contract"]["future_live_requires_separate_gate"])
        self.assertTrue(payload["boundaries"]["no_native_replay"])
        self.assertTrue(payload["boundaries"]["no_speaker_write"])

    @unittest.skipUnless(
        (v2600.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2600.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_single_arm32_shared_object_with_tap_exports(self) -> None:
        payload = v2600.make_payload(args(build=True))
        binary = payload["build"]["binary"]

        self.assertTrue(payload["ok"], payload)
        self.assertIn("ELF 32-bit LSB shared object, ARM", binary["file"]["stdout"])
        self.assertTrue(binary["symbols"]["exports_acdb_ioctl"])
        self.assertTrue(binary["symbols"]["exports_ioctl"])
        self.assertTrue(binary["symbols"]["exports_a90_arm_capture"])
        self.assertEqual(binary["mode"], "0o600")
        self.assertEqual(len(binary["sha256"]), 64)

    def test_cli_writes_manifest_and_optional_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_indirect_buffer_tap_v2600.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
                "--write-report",
                "--report-path",
                str(local_args.report_path),
            ],
            cwd=v2600.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(local_args.manifest_path.exists())
        self.assertTrue(local_args.report_path.exists())


if __name__ == "__main__":
    unittest.main()
