"""Host-only tests for the V2512 exec-linked own-process ACDB GET helper build."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2512 = load_revalidation("build_android_acdb_ownprocess_get_exec_linked_v2512")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2512-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "clang": v2512.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2512.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class BuildAndroidAcdbOwnprocessGetExecLinkedV2512(unittest.TestCase):
    def test_source_state_matches_exec_linked_pure_read_boundary(self) -> None:
        state = v2512.source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["direct_decl_acdb_loader_init_v3"])
        self.assertTrue(state["required"]["direct_decl_acdb_ioctl"])
        self.assertTrue(state["required"]["acdb_root_audconf_open"])
        self.assertTrue(state["required"]["does_not_use_acdbdata_root"])
        self.assertTrue(state["required"]["calls_init_v3_direct"])
        self.assertTrue(state["required"]["calls_acdb_ioctl_direct"])
        self.assertTrue(state["required"]["target_out_len_4916"])
        self.assertEqual(state["bounded_matrix"]["max_calls"], 40)

    def test_dry_run_is_host_only_and_live_blocked(self) -> None:
        payload = v2512.manifest(args())

        self.assertEqual(payload["decision"], "v2512-acdb-ownprocess-exec-linked-host-only")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["android_action"], "none")
        self.assertTrue(payload["boundaries"]["no_native_msm_audio_cal_ioctls"])
        self.assertTrue(payload["boundaries"]["no_forbidden_set_ioctl"])
        self.assertTrue(payload["boundaries"]["no_hal_injection"])
        self.assertTrue(payload["boundaries"]["live_execution_blocked_in_this_unit"])
        self.assertEqual(payload["capture_contract"]["required_dt_needed"], v2512.REQUIRED_NEEDED)
        self.assertEqual(payload["capture_contract"]["acdb_files_path"], "/vendor/etc/audconf/OPEN")
        self.assertEqual(payload["capture_contract"]["commands"], ["0x11394", "0x12e01", "0x130da", "0x130dc"])
        self.assertEqual(payload["capture_contract"]["out_lens"], [4, 4916])
        self.assertEqual(payload["capture_contract"]["max_acdb_ioctl_calls"], 40)

    def test_vendor_lib_state_has_required_symbols_and_closure(self) -> None:
        state = v2512.vendor_lib_state("readelf")

        self.assertTrue(state["all_required_present"], state["libs"])
        loader = state.get("libacdbloader_symbols", {})
        audcal = state.get("libaudcal_symbols", {})
        self.assertTrue(loader.get("has_acdb_loader_init_v3"), loader)
        self.assertTrue(loader.get("imports_acdb_ioctl"), loader)
        self.assertTrue(audcal.get("exports_acdb_ioctl"), audcal)

    @unittest.skipUnless(
        (v2512.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2512.TOOLCHAIN_ROOT / "bin/ld.lld").exists()
        and all((v2512.VENDOR_LIB_DIR / name).exists() for name in v2512.REQUIRED_NEEDED),
        "private Android clang/lld or ACDB closure unavailable",
    )
    def test_build_outputs_arm32_pie_with_acdb_dt_needed(self) -> None:
        payload = v2512.manifest(args(build=True))
        artifact = payload["build"]["artifact"]

        self.assertIn("ELF 32-bit LSB shared object, ARM", artifact["file"])
        self.assertTrue(artifact["needed_ok"], artifact["needed"])
        self.assertTrue(artifact["undefined_acdb_loader_init_v3"], artifact)
        self.assertTrue(artifact["undefined_acdb_ioctl"], artifact)
        self.assertFalse(artifact["undefined_dlopen"], artifact)
        self.assertFalse(artifact["undefined_dlsym"], artifact)
        self.assertFalse(artifact["undefined_dlerror"], artifact)
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
                "workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py",
                "--dry-run",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
            ],
            cwd=v2512.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2512-acdb-ownprocess-exec-linked-host-only")
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
