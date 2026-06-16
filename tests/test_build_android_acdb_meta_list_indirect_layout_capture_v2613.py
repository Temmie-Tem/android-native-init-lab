"""Tests for the V2613 ACDB meta-list indirect-layout capture build gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2613 = load_revalidation("build_android_acdb_meta_list_indirect_layout_capture_v2613")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2613-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbMetaListIndirectLayoutCaptureV2613(unittest.TestCase):
    def test_source_state_requires_command_specific_indirect_layouts(self) -> None:
        state = v2613.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        required = state["required"]
        self.assertTrue(required["helper_calls_init_v3_with_meta_head"])
        self.assertTrue(required["helper_arms_after_init_before_send"])
        self.assertTrue(required["tap_layout_dump_before_generic_scan"])
        self.assertTrue(required["tap_allows_high_android32_user_va"])
        self.assertTrue(required["tap_audproc_common_layout"])
        self.assertTrue(required["tap_audproc_stream_layout"])
        self.assertTrue(required["tap_gain_dep_layout"])
        self.assertTrue(required["tap_afe_common_layout"])
        self.assertTrue(required["tap_length_from_out_word0_and_cap_guard"])
        self.assertTrue(required["tap_ret0_only_indirect_dump"])

    def test_dry_run_contract_is_host_only_and_payload_private(self) -> None:
        payload = v2613.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])
        self.assertIn("out_word0", payload["capture_contract"]["indirect_policy"])
        self.assertIn("ret==0", payload["capture_contract"]["success_discriminator"])
        self.assertEqual(
            payload["sources"]["v2613_delta"]["layout_map"]["0x13265"],
            "AUDPROC common: ptr=in_word4, cap=in_word3, len=out_word0",
        )

    def test_patched_context_restores_v2608_constants(self) -> None:
        original_helper = v2613.v2611.v2608.HELPER_SOURCE_REL
        original_tap = v2613.v2611.v2608.v2600.ACDBTAP_SOURCE_REL

        with v2613.patched_v2608_constants():
            self.assertEqual(v2613.v2611.v2608.HELPER_SOURCE_REL, v2613.HELPER_SOURCE_REL)
            self.assertEqual(v2613.v2611.v2608.v2600.ACDBTAP_SOURCE_REL, v2613.ACDBTAP_SOURCE_REL)

        self.assertEqual(v2613.v2611.v2608.HELPER_SOURCE_REL, original_helper)
        self.assertEqual(v2613.v2611.v2608.v2600.ACDBTAP_SOURCE_REL, original_tap)

    @unittest.skipUnless(
        (v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_helper_and_combined_preload(self) -> None:
        payload = v2613.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertEqual(len(helper["sha256"]), 64)
        self.assertEqual(len(preload["sha256"]), 64)
        self.assertTrue(preload["checks"]["soname_v2613"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_indirect_layout_capture_v2613.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2613.ROOT,
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
