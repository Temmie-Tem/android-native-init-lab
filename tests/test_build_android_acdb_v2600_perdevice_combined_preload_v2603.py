"""Tests for the V2603 ACDB V2600 per-device combined preload build."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2603 = load_revalidation("build_android_acdb_v2600_perdevice_combined_preload_v2603")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2603-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "write_report": False,
        "report": root / "report.md",
        "clang": v2603.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2603.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbV2600PerdeviceCombinedPreloadV2603(unittest.TestCase):
    def test_source_state_combines_v2600_tap_with_v2591_preinit_overrides(self) -> None:
        state = v2603.source_state()
        required = state["required"]
        delta = state["v2603_delta"]

        self.assertTrue(state["required_ok"], required)
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(required["v2600_tap_source_selected"])
        self.assertTrue(required["v2600_tap_capture_inbuf_macro"])
        self.assertTrue(required["v2600_tap_capture_indirect_macro"])
        self.assertTrue(required["v2600_tap_default_auto_arm_off"])
        self.assertTrue(required["preinit_calls_a90_arm_capture"])
        self.assertTrue(required["preinit_calls_send_audio_cal_v5"])
        self.assertEqual(delta["preinit_extra_cflags"], ["-DA90_SPEAKER_RX_PATH=1", "-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1"])
        self.assertEqual(
            delta["send_audio_cal_v5_call"],
            "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        )

    def test_dry_run_contract_is_host_only_and_explains_v2602_fix(self) -> None:
        payload = v2603.make_payload(args())
        contract = payload["capture_contract"]
        boundary = payload["measurement_boundary"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertIn("V2600 tap-only", contract["reason"])
        self.assertIn("bounded indirect", contract["tap"])
        self.assertIn("fake allocate", contract["ioctl"])
        self.assertIn("V2572 hook", contract["preinit"])
        self.assertEqual(
            contract["per_device_call"],
            "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        )
        self.assertTrue(boundary["no_live_default"])
        self.assertTrue(boundary["no_native_replay"])
        self.assertTrue(boundary["no_speaker_write"])
        self.assertEqual(boundary["fake_audio_cal_env"], "A90_ACDB_FAKE_ALLOCATE=1")

    @unittest.skipUnless(
        (v2603.v2572.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2603.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_helper_and_single_combined_preload(self) -> None:
        payload = v2603.make_payload(args(build=True))
        build = payload["build"]
        helper = build["artifacts"]["helper"]
        preload = build["artifacts"]["preload"]
        tap_compile = build["compile"]["acdbtap_v2600"]
        preinit_compile = build["compile"]["preinit_perdevice_rx_capmask_argorder"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB shared object, ARM", preload["file"]["stdout"])
        self.assertEqual(helper["mode"], "0o600")
        self.assertEqual(preload["mode"], "0o600")
        self.assertEqual(len(helper["sha256"]), 64)
        self.assertEqual(len(preload["sha256"]), 64)
        self.assertIn("-DA90_ACDBTAP_CAPTURE_INBUF=1", tap_compile["command"])
        self.assertIn("-DA90_ACDBTAP_CAPTURE_INDIRECT_CANDIDATES=1", tap_compile["command"])
        self.assertIn("-DA90_SPEAKER_RX_PATH=1", preinit_compile["command"])
        self.assertIn("-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1", preinit_compile["command"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_v2600_perdevice_combined_preload_v2603.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2603.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(local_args.manifest.exists())
        self.assertTrue(local_args.report.exists())


if __name__ == "__main__":
    unittest.main()
