"""Tests for the V2626 ACDB AFE topology probe build gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2626 = load_revalidation("build_android_acdb_afe_topology_probe_v2626")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2626-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "write_report": False,
        "build_root": root / "build",
        "manifest": root / "build/manifest.json",
        "report": root / "report.md",
        "clang": v2626.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2626.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildAndroidAcdbAfeTopologyProbeV2626(unittest.TestCase):
    def test_source_state_requires_afe_topology_only_probe(self) -> None:
        state = v2626.source_state()

        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        required = state["required"]
        self.assertTrue(required["helper_calls_init_v3_with_meta_head"])
        self.assertTrue(required["helper_arms_after_init_before_probe"])
        self.assertTrue(required["helper_has_afe_topology_id_cmd"])
        self.assertTrue(required["helper_has_afe_topologies_cmd"])
        self.assertTrue(required["helper_has_capacity_sweep"])
        self.assertTrue(required["helper_omits_crashing_tail_meta"])
        self.assertTrue(required["helper_omits_vol_sweep"])
        self.assertTrue(required["tap_has_afe_topology_indirect_layout"])

    def test_probe_shape_matches_missing_afe_topology_gate(self) -> None:
        probe = v2626.source_state()["probe_matrix"]

        self.assertEqual(probe["direct_commands"], ["0x130d8", "0x13262"])
        self.assertEqual(probe["afe_topology_capacity_sweep"], [4, 256, 4096])
        self.assertEqual(probe["tap_indirect_layout"]["kind"], "ind-afe-topology")
        self.assertEqual(probe["tap_indirect_layout"]["ptr_word"], 1)
        self.assertEqual(probe["tap_indirect_layout"]["cap_word"], 0)

    def test_dry_run_contract_is_capture_only(self) -> None:
        payload = v2626.make_payload(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertTrue(payload["measurement_boundary"]["no_native_replay"])
        self.assertEqual(payload["measurement_boundary"]["fake_audio_cal_env"], "A90_ACDB_FAKE_ALLOCATE=1")
        self.assertIn("AFE topology", payload["capture_contract"]["postinit"])
        self.assertFalse(payload["sources"]["armed_capture_contract"]["auto_arm_on_initialize"])
        self.assertFalse(payload["sources"]["armed_capture_contract"]["exit_on_first_4916"])

    def test_patched_context_restores_v2613_constants(self) -> None:
        original_helper = v2626.v2613.HELPER_SOURCE_REL
        original_artifact = v2626.v2613.HELPER_ARTIFACT_NAME

        with v2626.patched_v2613_constants():
            self.assertEqual(v2626.v2613.HELPER_SOURCE_REL, v2626.HELPER_SOURCE_REL)
            self.assertEqual(v2626.v2613.HELPER_ARTIFACT_NAME, v2626.HELPER_ARTIFACT_NAME)

        self.assertEqual(v2626.v2613.HELPER_SOURCE_REL, original_helper)
        self.assertEqual(v2626.v2613.HELPER_ARTIFACT_NAME, original_artifact)

    @unittest.skipUnless(
        (v2626.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists()
        and (v2626.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists(),
        "private Android clang/lld unavailable",
    )
    def test_build_outputs_arm32_helper_and_combined_preload(self) -> None:
        payload = v2626.make_payload(args(build=True))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertIn("ELF 32-bit LSB", helper["file"]["stdout"])
        self.assertIn("ELF 32-bit LSB", preload["file"]["stdout"])
        self.assertEqual(len(helper["sha256"]), 64)
        self.assertEqual(len(preload["sha256"]), 64)
        self.assertTrue(preload["checks"]["soname_v2626"])
        self.assertTrue(helper["checks"]["does_not_reference_send_audio_cal_v5"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args(write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/build_android_acdb_afe_topology_probe_v2626.py",
                "--build-root",
                str(local_args.build_root),
                "--manifest",
                str(local_args.manifest),
                "--write-report",
                "--report",
                str(local_args.report),
            ],
            cwd=v2626.ROOT,
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
