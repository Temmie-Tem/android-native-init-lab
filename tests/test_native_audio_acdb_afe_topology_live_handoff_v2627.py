"""Tests for the V2627 ACDB AFE topology live wrapper."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2627 = load_revalidation("native_audio_acdb_afe_topology_live_handoff_v2627")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2627-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2626_artifacts": False,
        "v2626_build_root": v2627.v2626.DEFAULT_BUILD_ROOT,
        "v2626_manifest_path": v2627.v2626.DEFAULT_MANIFEST,
        "helper_path": None,
        "helper_sha256": None,
        "preload_path": None,
        "preload_sha256": None,
        "out_dir": root / "run",
        "adb": "adb",
        "serial": None,
        "from_native": True,
        "android_timeout": 240.0,
        "flash_timeout": 420.0,
        "adb_command_timeout": 90.0,
        "adb_pull_timeout": 120.0,
        "helper_timeout": 90.0,
        "android_root_recheck_attempts": v2627.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": v2627.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
        "android_settle_adb_retry_attempts": v2627.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2627.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


class NativeAudioAcdbAfeTopologyLiveHandoffV2627(unittest.TestCase):
    def test_read_v2626_manifest_checks_afe_topology_contract(self) -> None:
        manifest = v2627.read_v2626_manifest(v2627.v2626.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"], manifest)
        self.assertTrue(manifest["afe_topology_contract_ok"], manifest)
        self.assertTrue(manifest["armed_contract_ok"], manifest)

    def test_summarize_afe_topology_payload_capture(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2627-summary-"))
        acdbtap = root / "acdbtap"
        acdbtap.mkdir(parents=True, exist_ok=True)
        raw_topo = acdbtap / "acdbtap-00000003-cmd-00013262-len-00000004.bin"
        raw_topo.write_bytes((0x1001025D).to_bytes(4, "little"))
        write_jsonl(
            acdbtap / "acdbtap-events.jsonl",
            [
                {
                    "event": "acdb_ioctl",
                    "seq": 3,
                    "cmd": "0x00013262",
                    "in_len": 8,
                    "out_len": 4,
                    "ret": 0,
                    "buffer": "ind-afe-topology",
                    "raw_path": str(raw_topo),
                    "sha256": hashlib.sha256(raw_topo.read_bytes()).hexdigest(),
                }
            ],
        )
        helper_rows = [
            {"event": "v2626_afe_topology_probe", "stage": "before_afe_topology_probe", "code": 0},
            {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-id", "cmd": "0x000130d8", "ret": 0},
            {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap4", "cmd": "0x00013262", "step": 4, "ret": 0},
            {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap256", "cmd": "0x00013262", "step": 256, "ret": 0},
            {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap4096", "cmd": "0x00013262", "step": 4096, "ret": 0},
            {"event": "v2626_afe_topology_probe", "stage": "done", "code": 0},
        ]
        write_jsonl(root / "acdb-v2626-afe-topology-probe-events.jsonl", helper_rows)

        summary = v2627.summarize_afe_topology_capture(root)

        self.assertEqual(summary["classification"], "v2627-afe-topology-candidate-captured")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["success"])
        self.assertTrue(summary["probe_complete"])
        self.assertEqual(summary["afe_topology_payload_count"], 1)
        self.assertEqual(len(summary["afe_topology_candidates"]), 1)
        self.assertEqual(summary["capacity_case_count"], 3)

    def test_summarize_afe_topology_size_only_is_partial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2627-summary-size-"))
        acdbtap = root / "acdbtap"
        acdbtap.mkdir(parents=True, exist_ok=True)
        raw_zero = acdbtap / "acdbtap-00000003-cmd-00013262-len-00000004.bin"
        raw_zero.write_bytes(b"\0" * 4)
        write_jsonl(
            acdbtap / "acdbtap-events.jsonl",
            [
                {
                    "event": "acdb_ioctl",
                    "seq": 3,
                    "cmd": "0x00013262",
                    "in_len": 8,
                    "out_len": 4,
                    "ret": 0,
                    "buffer": "ind-afe-topology",
                    "raw_path": str(raw_zero),
                    "sha256": hashlib.sha256(raw_zero.read_bytes()).hexdigest(),
                }
            ],
        )
        write_jsonl(
            root / "acdb-v2626-afe-topology-probe-events.jsonl",
            [
                {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap4", "ret": 0},
                {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap256", "ret": 0},
                {"event": "v2626_afe_topology_probe", "stage": "case_return", "case": "afe-topology-cap4096", "ret": 0},
                {"event": "v2626_afe_topology_probe", "stage": "done", "code": 0},
            ],
        )

        summary = v2627.summarize_afe_topology_capture(root)

        self.assertEqual(summary["classification"], "v2627-afe-topology-direct-size-only")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["partial_success"])
        self.assertFalse(summary["success"])

    def test_dry_run_uses_v2490_engine_with_v2626_artifacts(self) -> None:
        payload = v2627.dry_run_payload(args())

        self.assertTrue(payload["ok"], payload.get("live_blockers"))
        self.assertTrue(payload["capture_contract"]["manual_arm_after_init"])
        self.assertFalse(payload["capture_contract"]["auto_arm_on_initialize"])
        self.assertFalse(payload["capture_contract"]["exit_on_first_4916"])
        self.assertTrue(payload["v2626_artifacts"]["ok"])
        self.assertTrue(payload["v2490_engine"]["live_ready"])


if __name__ == "__main__":
    unittest.main()
