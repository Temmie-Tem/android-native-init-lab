"""Tests for the V2721 corrected core-39 ACDB replay deploy plan."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2721 = load_revalidation("native_audio_acdb_corrected_core39_replay_deploy_plan_v2721")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2721-test-"))
    defaults: dict[str, object] = {
        "v2636_manifest": v2721.DEFAULT_V2636_MANIFEST,
        "v2669_run": v2721.DEFAULT_V2669_RUN,
        "helper": v2721.DEFAULT_HELPER,
        "real_hal_run": v2721.DEFAULT_REAL_HAL_RUN,
        "build_root": root / "build",
        "manifest_path": root / "deploy-plan.json",
        "report_path": root / "report.md",
        "remote_dir": "/cache/a90-acdb-setcal-replay-v2721-test",
        "hold_sec": 10,
        "write_report": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class NativeAudioAcdbCorrectedCore39ReplayDeployPlanV2721(unittest.TestCase):
    def test_build_manifest_is_ready_and_uses_corrected_order(self) -> None:
        manifest = v2721.build_manifest(args())

        self.assertTrue(manifest["ok"], manifest.get("replay_blockers"))
        self.assertTrue(manifest["safe_to_run_native_replay"])
        self.assertEqual(manifest["corrected_manifest_contract"]["replay_order"], v2721.EXPECTED_REPLAY_ORDER)
        self.assertEqual(manifest["corrected_manifest_contract"]["stale_cal_types_present"], [])
        self.assertTrue(manifest["corrected_manifest_contract"]["no_basic_payload_argv"])
        self.assertNotIn("--basic-payload", manifest["remote_argv"])
        self.assertEqual(manifest["helper_contract"]["declared_replay_entries"], 11)
        self.assertTrue(manifest["helper_contract"]["entry_count_fits"])

    def test_core39_is_exact_set_from_v2669_not_legacy_basic_payload(self) -> None:
        manifest = v2721.build_manifest(args())
        first = manifest["replay_entries"][0]

        self.assertEqual(first["cal_type"], 39)
        self.assertEqual(first["kind"], "exact-set")
        self.assertEqual(first["role"], "CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET")
        self.assertTrue(first["payload_remote"])
        self.assertEqual(first["capture"]["payload_sha256"], "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89")

    def test_cal20_headers_are_materialized_private_from_real_hal_trace(self) -> None:
        manifest = v2721.build_manifest(args())
        cal20 = [entry for entry in manifest["replay_entries"] if entry["cal_type"] == 20]

        self.assertEqual(len(cal20), 2)
        self.assertEqual([entry["payload_remote"] for entry in cal20], [None, None])
        self.assertEqual([entry["capture"]["cal_size"] for entry in cal20], [0, 0])
        self.assertEqual([entry["capture"]["mem_handle_captured"] for entry in cal20], [-1, -1])
        self.assertEqual(manifest["cal20_source_summary"]["unique_cal20_arg_count"], 2)
        for entry in cal20:
            self.assertTrue(entry["ok"])
            local_file = next(
                item for item in manifest["files"]
                if item["remote_path"] == entry["arg_remote"]
            )
            self.assertEqual(local_file["local"]["size"], 68)
            self.assertTrue(local_file["local"]["nonzero"])

    def test_perdevice_sequence_reuses_v2636_without_stale_custom_types(self) -> None:
        manifest = v2721.build_manifest(args())
        perdev = manifest["replay_entries"][3:]

        self.assertEqual([entry["cal_type"] for entry in perdev], v2721.PER_DEVICE_SOURCE_ORDER)
        self.assertFalse(set(v2721.FORBIDDEN_STALE_CAL_TYPES) & {entry["cal_type"] for entry in manifest["replay_entries"]})
        payload_types = [entry["cal_type"] for entry in perdev if entry["payload_remote"]]
        self.assertEqual(payload_types, [11, 15, 16])

    def test_write_report_mentions_host_only_and_no_stale_types(self) -> None:
        ns = args()
        manifest = v2721.build_manifest(ns)
        v2721.write_report(ns.report_path, manifest, ns.manifest_path)
        text = ns.report_path.read_text(encoding="utf-8")

        self.assertIn("Host-only", text)
        self.assertIn("stale_cal_types_present: `[]`", text)
        self.assertIn("byte-exact V2669", text)
        self.assertIn("V2466 real-HAL ptrace metadata", text)
        self.assertNotIn("workspace/private/runs/audio", text)
        self.assertNotIn("device-artifacts", text)
        self.assertNotIn(".jsonl", text)


if __name__ == "__main__":
    unittest.main()
