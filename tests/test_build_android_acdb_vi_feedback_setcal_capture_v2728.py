"""Tests for the V2728 ACDB vi-feedback SET-calibration capture build."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2728 = load_revalidation("build_android_acdb_vi_feedback_setcal_capture_v2728")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2728-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2728.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2728.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbViFeedbackSetcalCaptureV2728(unittest.TestCase):
    def test_source_state_pins_vi_feedback_tuple_and_reuses_fake_set(self) -> None:
        state = v2728.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        required = state["required"]
        self.assertTrue(required["base_v2630_required_ok"])
        self.assertTrue(required["helper_prepares_empty_meta_list"])
        self.assertTrue(required["helper_arms_after_init_before_send"])
        self.assertTrue(required["helper_event_identity_v2728"])
        self.assertTrue(required["helper_vi_feedback_tuple"])
        self.assertTrue(required["ioctl_fake_setcal_capture_reused"])

    def test_dry_run_contract_is_host_only_and_vi_feedback_specific(self) -> None:
        payload = v2728.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])
        self.assertIn("fake-successes AUDIO_SET_CALIBRATION", payload["measurement_boundary"]["no_real_audio_set"])
        self.assertEqual(
            payload["capture_contract"]["vi_feedback_call"],
            {
                "acdb_id": 102,
                "path": 1,
                "app_type": "0x11132",
                "sample_rate": 8000,
                "stack_arg5": 0,
                "afe_sample_rate": 8000,
                "instance": 1,
            },
        )
        self.assertIn("cal_type 17", payload["capture_contract"]["expected_live_records"])
        self.assertEqual(payload["sources"]["v2728_delta"]["expected_cal_types"], [11, 17])

    def test_patch_context_restores_v2630_and_v2613_constants(self) -> None:
        original_v2630_helper = v2728.v2630.HELPER_SOURCE_REL
        original_v2630_artifact = v2728.v2630.HELPER_ARTIFACT_NAME
        original_v2613_helper = v2728.v2630.v2613.HELPER_SOURCE_REL
        original_v2608_helper = v2728.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL

        with v2728.patched_v2630_constants():
            self.assertEqual(v2728.v2630.HELPER_SOURCE_REL, v2728.HELPER_SOURCE_REL)
            self.assertEqual(v2728.v2630.HELPER_ARTIFACT_NAME, v2728.HELPER_ARTIFACT_NAME)
            self.assertEqual(v2728.v2630.v2613.HELPER_SOURCE_REL, v2728.HELPER_SOURCE_REL)
            self.assertEqual(v2728.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL, v2728.HELPER_SOURCE_REL)

        self.assertEqual(v2728.v2630.HELPER_SOURCE_REL, original_v2630_helper)
        self.assertEqual(v2728.v2630.HELPER_ARTIFACT_NAME, original_v2630_artifact)
        self.assertEqual(v2728.v2630.v2613.HELPER_SOURCE_REL, original_v2613_helper)
        self.assertEqual(v2728.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL, original_v2608_helper)

    @unittest.skipUnless(
        (v2728.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2728.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_helper_and_preload(self) -> None:
        payload = v2728.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertEqual(len(helper["sha256"]), 64)
        self.assertEqual(len(preload["sha256"]), 64)
        self.assertTrue(preload["checks"]["soname_v2728"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_vi_feedback_setcal_capture_v2728.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2728.ROOT,
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
