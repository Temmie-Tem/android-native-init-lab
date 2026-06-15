"""Host-only tests for the V2475 ACDB ioctl interposer build."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2475 = load_revalidation("build_android_acdbtap_v2475")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2475-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "clang": v2475.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2475.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class BuildAndroidAcdbTapV2475(unittest.TestCase):
    def test_source_state_matches_operator_boundary(self) -> None:
        state = v2475.source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["uses_dlsym_next"])
        self.assertTrue(state["required"]["target_out_len_4916"])
        self.assertTrue(state["required"]["sha256_implemented"])
        self.assertTrue(state["required"]["raw_syscalls_only"])

    def test_dry_run_is_host_only_and_measurement_only(self) -> None:
        payload = v2475.manifest(args())

        self.assertEqual(payload["decision"], "v2475-acdbtap-interposer-build-host-only")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["android_action"], "none")
        self.assertTrue(payload["boundaries"]["no_native_msm_audio_cal_ioctls"])
        self.assertTrue(payload["boundaries"]["no_native_speaker_write"])
        self.assertEqual(payload["capture_contract"]["target_out_len"], 4916)
        self.assertEqual(payload["capture_contract"]["size_query_out_len"], 4)
        self.assertEqual(payload["capture_contract"]["interposed_symbol"], "acdb_ioctl")

    @unittest.skipUnless(
        (v2475.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2475.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_shared_object_with_expected_symbols(self) -> None:
        payload = v2475.manifest(args(build=True))
        artifact = payload["build"]["artifact"]

        self.assertIn("ELF 32-bit LSB shared object, ARM", artifact["file"])
        self.assertTrue(artifact["exports_acdb_ioctl"])
        self.assertTrue(artifact["undefined_dlsym"])
        self.assertEqual(artifact["target"], "armv7a-linux-androideabi29")
        self.assertEqual(len(artifact["sha256"]), 64)
        self.assertTrue(payload["build"]["host_libraries"]["ready"])

    def test_cli_dry_run_outputs_json(self) -> None:
        local_args = args()
        import subprocess
        import sys

        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdbtap_v2475.py",
                "--dry-run",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
            ],
            cwd=v2475.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2475-acdbtap-interposer-build-host-only")
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
