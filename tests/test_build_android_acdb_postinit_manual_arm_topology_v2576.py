"""Host-only tests for the V2576 post-init manual-arm ACDB capture build."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2576 = load_revalidation("build_android_acdb_postinit_manual_arm_topology_v2576")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2576-build-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "clang": v2576.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2576.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class BuildAndroidAcdbPostinitManualArmTopologyCaptureV2576(unittest.TestCase):
    def test_source_state_requires_manual_arm_topology_capture(self) -> None:
        state = v2576.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["tap_auto_arm_macro"])
        self.assertTrue(state["required"]["tap_custom_topology_only_macro"])
        self.assertTrue(state["required"]["tap_custom_topology_size_cmd"])
        self.assertTrue(state["required"]["helper_has_postinit_fallback_arm"])
        self.assertTrue(state["required"]["helper_calls_common_topology_fallback"])

    def test_manifest_declares_manual_arm_after_init_compile_flags(self) -> None:
        payload = v2576.manifest(args())
        cflags = payload["toolchain"]["preload_cflags"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertIn("-DA90_ACDBTAP_ARMED_CAPTURE=1", cflags)
        self.assertIn("-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0", cflags)
        self.assertIn("-DA90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=0", cflags)
        self.assertIn("-DA90_ACDBTAP_EXIT_ON_TARGET=1", cflags)
        self.assertTrue(payload["capture_contract"]["arm_point"].startswith("manual-arm"))

    @unittest.skipUnless(
        (v2576.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2576.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_helper_and_single_combined_preload(self) -> None:
        payload = v2576.manifest(args(build=True))
        build = payload["build"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(build["helper"]["ok"], build["helper"])
        self.assertTrue(build["preload"]["ok"], build["preload"])
        self.assertIn("ELF 32-bit LSB", build["helper"]["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB shared object, ARM", build["preload"]["file"]["stdout"])
        self.assertEqual(build["helper"]["mode"], "0o600")
        self.assertEqual(build["preload"]["mode"], "0o600")
        self.assertEqual(len(build["helper"]["sha256"]), 64)
        self.assertEqual(len(build["preload"]["sha256"]), 64)

    def test_cli_writes_manifest(self) -> None:
        local_args = args()
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_postinit_manual_arm_topology_v2576.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
            ],
            cwd=v2576.ROOT,
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


if __name__ == "__main__":
    unittest.main()
