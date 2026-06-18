"""Tests for the V2719 in-hook route-first common-topology SET capture build."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2719 = load_revalidation("build_android_acdb_inhook_route_first_common_setcal_capture_v2719")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2719-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2719.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2719.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbInhookRouteFirstCommonSetcalCaptureV2719(unittest.TestCase):
    def test_source_state_requires_inhook_route_first_boundary(self) -> None:
        state = v2719.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["helper_imports_only_init_v3"])
        self.assertTrue(state["required"]["helper_does_not_call_send_v5"])
        self.assertTrue(state["required"]["helper_does_not_call_common_topology"])
        self.assertTrue(state["required"]["preload_arms_then_send_v5_then_real_common"])
        self.assertTrue(state["required"]["preload_uses_corrected_send_v5_args"])
        self.assertTrue(state["required"]["preload_neutralizes_reentry"])
        self.assertTrue(state["required"]["preload_exits_inside_hook"])
        self.assertTrue(state["required"]["ioctl_always_fakes_audio_set"])
        self.assertIn("post-init helper continuation SIGSEGVs", state["v2719_delta"]["basis"])
        self.assertIn("send_audio_cal_v5(15,1", state["v2719_delta"]["new_call_order"])

    def test_dry_run_contract_uses_v2674_model_not_postinit_retry(self) -> None:
        payload = v2719.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [10, 14, 24])
        self.assertEqual(payload["capture_contract"]["send_audio_cal_v5_args"], [15, 1, "0x11135", 48000, 0, 48000, 1])
        self.assertIn("common hook -> patch initialized -> arm capture -> send_audio_cal_v5", payload["capture_contract"]["call_order"])
        self.assertIn("without real AUDIO_SET_CALIBRATION", payload["capture_contract"]["success_discriminator"])

    def test_patched_context_restores_nested_build_constants(self) -> None:
        original_v2630_helper = v2719.v2630.HELPER_SOURCE_REL
        original_v2630_preinit = v2719.v2630.PREINIT_SOURCE_REL
        original_v2613_helper = v2719.v2630.v2613.HELPER_SOURCE_REL
        original_v2613_preinit = v2719.v2630.v2613.PREINIT_SOURCE_REL
        original_v2608_helper = v2719.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL
        original_v2608_preinit = v2719.v2630.v2613.v2611.v2608.PREINIT_SOURCE_REL
        original_artifact = v2719.v2630.HELPER_ARTIFACT_NAME

        with v2719.patched_v2630_constants():
            self.assertEqual(v2719.v2630.HELPER_SOURCE_REL, v2719.HELPER_SOURCE_REL)
            self.assertEqual(v2719.v2630.PREINIT_SOURCE_REL, v2719.PREINIT_SOURCE_REL)
            self.assertEqual(v2719.v2630.v2613.HELPER_SOURCE_REL, v2719.HELPER_SOURCE_REL)
            self.assertEqual(v2719.v2630.v2613.PREINIT_SOURCE_REL, v2719.PREINIT_SOURCE_REL)
            self.assertEqual(v2719.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL, v2719.HELPER_SOURCE_REL)
            self.assertEqual(v2719.v2630.v2613.v2611.v2608.PREINIT_SOURCE_REL, v2719.PREINIT_SOURCE_REL)
            self.assertEqual(v2719.v2630.HELPER_ARTIFACT_NAME, v2719.HELPER_ARTIFACT_NAME)

        self.assertEqual(v2719.v2630.HELPER_SOURCE_REL, original_v2630_helper)
        self.assertEqual(v2719.v2630.PREINIT_SOURCE_REL, original_v2630_preinit)
        self.assertEqual(v2719.v2630.v2613.HELPER_SOURCE_REL, original_v2613_helper)
        self.assertEqual(v2719.v2630.v2613.PREINIT_SOURCE_REL, original_v2613_preinit)
        self.assertEqual(v2719.v2630.v2613.v2611.v2608.HELPER_SOURCE_REL, original_v2608_helper)
        self.assertEqual(v2719.v2630.v2613.v2611.v2608.PREINIT_SOURCE_REL, original_v2608_preinit)
        self.assertEqual(v2719.v2630.HELPER_ARTIFACT_NAME, original_artifact)

    def test_phase_source_records_order_and_exits_inside_hook(self) -> None:
        source = (v2719.ROOT / v2719.PREINIT_SOURCE_REL).read_text(encoding="utf-8")

        self.assertIn("inhook_before_send_audio_cal_v5", source)
        self.assertIn("inhook_send_audio_cal_v5_return", source)
        self.assertIn("inhook_before_real_common", source)
        self.assertIn("inhook_real_common_return", source)
        self.assertIn("common_reentry_neutralized", source)
        self.assertIn("a90_exit(0)", source)
        self.assertIn("A90_SPEAKER_RX_CAPMASK 1", source)
        self.assertNotIn("A90_V2608_CALL_REAL_COMMON_TOPOLOGY", source)

    @unittest.skipUnless(
        (v2719.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2719.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_helper_and_inhook_route_first_preload(self) -> None:
        payload = v2719.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertTrue(helper["checks"]["no_undefined_common_topology"])
        self.assertTrue(helper["checks"]["no_undefined_send_audio_cal_v5"])
        self.assertTrue(helper["checks"]["no_helper_arm_capture_dependency"])
        self.assertTrue(preload["checks"]["soname_v2719"])
        self.assertTrue(preload["checks"]["exports_phase_common_hook"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2719.ROOT,
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
        report = local_args.report.read_text(encoding="utf-8")
        self.assertIn("in-hook route-first", report)
        self.assertIn("send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)", report)


if __name__ == "__main__":
    unittest.main()
