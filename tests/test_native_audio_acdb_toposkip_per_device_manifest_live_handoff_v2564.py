"""Tests for V2564 topology-skip per-device ACDB live wrapper."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2564 = load_revalidation("native_audio_acdb_toposkip_per_device_manifest_live_handoff_v2564")
v2561 = load_revalidation("build_android_acdb_toposkip_per_device_manifest_v2561")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_raw(root: Path, name: str, data: bytes) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/data/local/tmp/a90-acdb-tap/{name}"


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2564-test-"))
    defaults: dict[str, object] = {
        "dry_run": False,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2561_artifacts": False,
        "v2561_build_root": root / "build",
        "v2561_manifest_path": root / "build/manifest.json",
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
        "helper_timeout": 120.0,
        "android_root_recheck_attempts": 1,
        "android_root_recheck_sleep_sec": 0.0,
        "android_settle_adb_retry_attempts": 1,
        "android_settle_adb_retry_sleep_sec": 0.0,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class ToposkipPerDeviceManifestLiveV2564(unittest.TestCase):
    def test_read_v2561_manifest_requires_toposkip_contract(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2564-manifest-"))
        helper = root / "helper"
        preload = root / "preload.so"
        helper.write_bytes(b"helper")
        preload.write_bytes(b"preload")
        helper.chmod(0o600)
        preload.chmod(0o600)
        manifest = {
            "ok": True,
            "build": {
                "helper": {"ok": True, "path": v2561.rel(helper), "sha256": hashlib.sha256(b"helper").hexdigest()},
                "preload": {"ok": True, "path": v2561.rel(preload), "sha256": hashlib.sha256(b"preload").hexdigest()},
            },
            "source_state": {
                "required": {
                    "helper_calls_send_audio_cal_v5": True,
                    "helper_no_decl_common_topology": True,
                    "toposkip_exports_common_topology": True,
                    "toposkip_returns_success": True,
                    "toposkip_logs_private_marker": True,
                    "tap_post_initialize_auto_arm": True,
                    "ioctl_fake_allocate_mode": True,
                }
            },
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")

        selected = v2564.selected_artifacts(args(v2561_manifest_path=path))

        self.assertTrue(selected["ok"], selected)
        self.assertTrue(selected["manifest"]["checks"]["toposkip_exports_common_topology"])

    def test_summary_requires_topology_skip_marker_for_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2564-success-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        per_device = bytes([7]) * 128
        raw_path = write_raw(acdbtap, "acdbtap-00000002-cmd-00012e01-len-00000080.bin", per_device)
        write_jsonl(artifact / "acdb-toposkip-events.jsonl", [
            {"event": "topology_skip", "stage": "common_topology_short_circuit", "code": 0},
        ])
        write_jsonl(artifact / "acdb-per-device-manifest-events.jsonl", [
            {"event": "per_device_helper", "stage": "before_send_audio_cal_v5", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000002",
                "cmd": "0x00012e01",
                "in_len": "0x00000008",
                "out_len": "0x00000080",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(per_device).hexdigest(),
                "raw_path": raw_path,
                "raw_written": True,
                "is_target_4916": False,
                "all_zero": False,
            },
        ])
        write_jsonl(artifact / "ioctl-trace-events.jsonl", [
            {"event": "ioctl_trace", "name": "AUDIO_SET_CALIBRATION", "intercept": "fake-success"},
        ])

        summary = v2564.summarize_toposkip_per_device_manifest(artifact)

        self.assertEqual(summary["classification"], "v2564-toposkip-per-device-manifest-captured")
        self.assertTrue(summary["full_success"])
        self.assertTrue(summary["per_device_success"])
        self.assertEqual(summary["topology_skip_marker_count"], 1)

    def test_summary_rejects_per_device_record_without_topology_skip_marker(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2564-no-marker-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        per_device = bytes([8]) * 64
        raw_path = write_raw(acdbtap, "acdbtap-00000001-cmd-00012e01-len-00000040.bin", per_device)
        write_jsonl(artifact / "acdb-per-device-manifest-events.jsonl", [
            {"event": "per_device_helper", "stage": "before_send_audio_cal_v5", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000001",
                "cmd": "0x00012e01",
                "in_len": "0x00000008",
                "out_len": "0x00000040",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(per_device).hexdigest(),
                "raw_path": raw_path,
                "raw_written": True,
                "is_target_4916": False,
                "all_zero": False,
            },
        ])

        summary = v2564.summarize_toposkip_per_device_manifest(artifact)

        self.assertEqual(summary["classification"], "v2564-topology-skip-marker-missing")
        self.assertFalse(summary["full_success"])
        self.assertEqual(summary["topology_skip_marker_count"], 0)


if __name__ == "__main__":
    unittest.main()
