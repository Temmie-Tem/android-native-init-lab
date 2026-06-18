"""Tests for the V2692 ACDB lower pointer-target capture build gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2692 = load_revalidation("build_android_acdb_lower_ptrtarget_capture_v2692")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2692-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbLowerPtrtargetCaptureV2692(unittest.TestCase):
    def test_source_state_requires_maps_verified_ptrtarget_capture(self) -> None:
        state = v2692.source_state()
        required = state["required"]

        self.assertTrue(state["required_ok"], required)
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertTrue(required["base_v2674_required_ok"])
        self.assertTrue(required["base_v2674_prohibited_ok"])
        self.assertTrue(required["preinit_writes_block_snapshot"])
        self.assertTrue(required["preinit_snapshot_fields"])
        self.assertTrue(required["preinit_snapshot_before_get"])
        self.assertTrue(required["tap_declares_lower_custom_cmds"])
        self.assertTrue(required["tap_reads_proc_self_maps"])
        self.assertTrue(required["tap_maps_verifies_before_copy"])
        self.assertTrue(required["tap_logs_ptrtarget_status"])
        self.assertTrue(required["tap_dumps_ptrtarget_pre"])
        self.assertTrue(required["tap_ptrtarget_before_real_ioctl"])
        self.assertTrue(required["tap_caps_ptrtarget_window"])
        self.assertTrue(required["ioctl_still_fakes_audio_set"])
        self.assertEqual(
            state["v2692_delta"]["ptrtarget"],
            "maps-verify in_word1 and dump ptrtarget-pre raw bytes privately before real acdb_ioctl",
        )

    def test_dry_run_contract_is_host_only_and_targets_lower_hidden_nodes(self) -> None:
        payload = v2692.make_payload(args())
        contract = payload["capture_contract"]
        boundary = payload["measurement_boundary"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(boundary["no_live_default"])
        self.assertTrue(boundary["no_native_replay"])
        self.assertTrue(boundary["no_speaker_write"])
        self.assertTrue(boundary["raw_payload_private_only"])
        self.assertIn("a90_run_lower_hidden_nodes", contract["call_order"])
        self.assertEqual(contract["target_cal_types"], [24, 10, 14])
        self.assertEqual(contract["get_commands"][24], "0x000130da")
        self.assertEqual(contract["get_commands"][10], "0x00011394")
        self.assertEqual(contract["get_commands"][14], "0x00012e01")
        self.assertEqual(contract["get_commands"][25], "0x000130dc")
        self.assertIn("ptrtarget-pre", contract["ptrtarget"])

    def test_patched_context_restores_v2674_and_nested_sources(self) -> None:
        v2630 = v2692.v2674.v2659.v2630
        v2613 = v2630.v2613
        original_v2674_preinit = v2692.v2674.PREINIT_SOURCE_REL
        original_v2674_preload = v2692.v2674.PRELOAD_ARTIFACT_NAME
        original_v2630_tap = v2630.ACDBTAP_SOURCE_REL
        original_v2613_tap = v2613.ACDBTAP_SOURCE_REL

        with v2692.patched_v2674_constants():
            self.assertEqual(v2692.v2674.PREINIT_SOURCE_REL, v2692.PREINIT_SOURCE_REL)
            self.assertEqual(v2692.v2674.PRELOAD_ARTIFACT_NAME, v2692.PRELOAD_ARTIFACT_NAME)
            self.assertEqual(v2630.ACDBTAP_SOURCE_REL, v2692.ACDBTAP_SOURCE_REL)
            self.assertEqual(v2613.ACDBTAP_SOURCE_REL, v2692.ACDBTAP_SOURCE_REL)

        self.assertEqual(v2692.v2674.PREINIT_SOURCE_REL, original_v2674_preinit)
        self.assertEqual(v2692.v2674.PRELOAD_ARTIFACT_NAME, original_v2674_preload)
        self.assertEqual(v2630.ACDBTAP_SOURCE_REL, original_v2630_tap)
        self.assertEqual(v2613.ACDBTAP_SOURCE_REL, original_v2613_tap)

    @unittest.skipUnless(
        (v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2692.v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_lower_ptrtarget_helper_and_preload(self) -> None:
        payload = v2692.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertTrue(preload["checks"]["soname_v2692"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])
        self.assertTrue(preload["checks"]["exports_lower_runner"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])
        self.assertEqual(len(helper["sha256"]), 64)
        self.assertEqual(len(preload["sha256"]), 64)

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_lower_ptrtarget_capture_v2692.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2692.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(local_args.manifest.exists())
        self.assertTrue(local_args.report.exists())
        self.assertIn("pointer-target", local_args.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
