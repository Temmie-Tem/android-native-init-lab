"""Host-only tests for the V2489 own-process ACDB GET helper build."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2489 = load_revalidation("build_android_acdb_ownprocess_get_v2489")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2489-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "clang": v2489.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2489.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class BuildAndroidAcdbOwnprocessGetV2489(unittest.TestCase):
    def test_source_state_matches_pure_read_boundary(self) -> None:
        state = v2489.source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["uses_absolute_vendor_paths"])
        self.assertTrue(state["required"]["uses_rtld_now_only"])
        self.assertTrue(state["required"]["uses_libdl_api_resolution"])
        self.assertTrue(state["required"]["uses_android_dlopen_ext"])
        self.assertTrue(state["required"]["uses_android_get_exported_namespace"])
        self.assertTrue(state["required"]["uses_dlext_namespace_flag"])
        self.assertTrue(state["required"]["uses_android_dlextinfo_namespace"])
        self.assertTrue(state["required"]["probes_namespace_sphal"])
        self.assertTrue(state["required"]["probes_namespace_vendor"])
        self.assertTrue(state["required"]["probes_namespace_default"])
        self.assertTrue(state["required"]["probes_namespace_vndk"])
        self.assertTrue(state["required"]["records_namespace_events"])
        self.assertTrue(state["required"]["uses_namespace_load_for_libaudcal"])
        self.assertTrue(state["required"]["uses_namespace_load_for_libacdbloader"])
        self.assertTrue(state["required"]["uses_dlsym_acdb_ioctl"])
        self.assertTrue(state["required"]["uses_dlerror_detail"])
        self.assertTrue(state["required"]["calls_init_v3"])
        self.assertTrue(state["required"]["target_out_len_4916"])
        self.assertEqual(state["bounded_matrix"]["max_calls"], 40)

    def test_dry_run_is_host_only_and_live_blocked(self) -> None:
        payload = v2489.manifest(args())

        self.assertEqual(payload["decision"], "v2489-acdb-ownprocess-get-host-only")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["android_action"], "none")
        self.assertTrue(payload["boundaries"]["no_native_msm_audio_cal_ioctls"])
        self.assertTrue(payload["boundaries"]["no_forbidden_set_ioctl"])
        self.assertTrue(payload["boundaries"]["live_execution_blocked_in_this_unit"])
        self.assertEqual(payload["capture_contract"]["namespace_probe_order"], ["sphal", "vendor", "default", "vndk"])
        self.assertIn("namespace_probe", payload["capture_contract"]["namespace_events"])
        self.assertEqual(payload["capture_contract"]["commands"], ["0x11394", "0x12e01", "0x130da", "0x130dc"])
        self.assertEqual(payload["capture_contract"]["out_lens"], [4, 4916])
        self.assertEqual(payload["capture_contract"]["max_acdb_ioctl_calls"], 40)

    def test_vendor_symbol_state_has_required_exports(self) -> None:
        state = v2489.vendor_symbol_state("readelf")

        loader = state.get("libacdbloader_symbols", {})
        audcal = state.get("libaudcal_symbols", {})
        self.assertTrue(loader.get("has_acdb_loader_init_v3"), loader)
        self.assertTrue(loader.get("imports_acdb_ioctl"), loader)
        self.assertTrue(audcal.get("exports_acdb_ioctl"), audcal)

    @unittest.skipUnless(
        (v2489.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2489.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_pie_with_libdl_dependency(self) -> None:
        payload = v2489.manifest(args(build=True))
        artifact = payload["build"]["artifact"]

        self.assertIn("ELF 32-bit LSB shared object, ARM", artifact["file"])
        self.assertTrue(artifact["needed_libdl"], artifact)
        self.assertTrue(artifact["undefined_dlopen"], artifact)
        self.assertTrue(artifact["undefined_dlsym"], artifact)
        self.assertTrue(artifact["undefined_dlerror"], artifact)
        self.assertTrue(artifact["interpreter_system_linker"], artifact)
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
                "workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py",
                "--dry-run",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
            ],
            cwd=v2489.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2489-acdb-ownprocess-get-host-only")
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
