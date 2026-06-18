"""Tests for the V2654 custom-topology SET capture build gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2654 = load_revalidation("build_android_acdb_custom_topology_setcal_capture_v2654")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2654-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2654.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2654.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbCustomTopologySetcalCaptureV2654(unittest.TestCase):
    def test_source_state_requires_full_manifest_and_fake_set_boundary(self) -> None:
        state = v2654.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(state["required"]["helper_imports_common_topology"])
        self.assertTrue(state["required"]["helper_calls_common_topology_before_send_v5"])
        self.assertTrue(state["required"]["ioctl_always_fakes_audio_set"])
        self.assertTrue(state["required"]["ioctl_dumps_same_process_dmabuf"])
        self.assertEqual(state["v2654_delta"]["acceptance"], "future live capture must include byte-exact cal_types 10, 14, and 24; cal20 alone is insufficient")

    def test_dry_run_contract_targets_custom_topology(self) -> None:
        payload = v2654.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [10, 14, 24])
        self.assertEqual(payload["capture_contract"]["supplemental_cal_types"], [20])
        self.assertIn("send_common_custom_topology", payload["capture_contract"]["call_order"])
        self.assertIn("fake-successes every AUDIO_SET_CALIBRATION", payload["measurement_boundary"]["no_real_audio_set"])

    def test_patched_context_restores_helper_source_and_names(self) -> None:
        original_helper = v2654.v2630.HELPER_SOURCE_REL
        original_v2613_helper = v2654.v2630.v2613.HELPER_SOURCE_REL
        original_artifact = v2654.v2630.HELPER_ARTIFACT_NAME

        with v2654.patched_v2630_constants():
            self.assertEqual(v2654.v2630.HELPER_SOURCE_REL, v2654.HELPER_SOURCE_REL)
            self.assertEqual(v2654.v2630.v2613.HELPER_SOURCE_REL, v2654.HELPER_SOURCE_REL)
            self.assertEqual(v2654.v2630.HELPER_ARTIFACT_NAME, v2654.HELPER_ARTIFACT_NAME)

        self.assertEqual(v2654.v2630.HELPER_SOURCE_REL, original_helper)
        self.assertEqual(v2654.v2630.v2613.HELPER_SOURCE_REL, original_v2613_helper)
        self.assertEqual(v2654.v2630.HELPER_ARTIFACT_NAME, original_artifact)

    @unittest.skipUnless(
        (v2654.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2654.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_full_manifest_helper_and_setcal_preload(self) -> None:
        payload = v2654.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertTrue(helper["checks"]["undefined_common_topology"])
        self.assertTrue(helper["checks"]["undefined_send_audio_cal_v5"])
        self.assertTrue(preload["checks"]["soname_v2654"])
        self.assertIn(" UND mmap", preload["symbols"]["stdout"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_custom_topology_setcal_capture_v2654.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2654.ROOT,
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
        self.assertIn("custom-topology", local_args.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
