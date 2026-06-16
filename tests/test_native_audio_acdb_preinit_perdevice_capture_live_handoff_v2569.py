"""Tests for the V2569 ACDB pre-init-tail per-device live handoff wrapper."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2569 = load_revalidation("native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569")
v2568 = load_revalidation("build_android_acdb_preinit_perdevice_capture_v2568")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2569-live-test-"))
    defaults: dict[str, object] = {
        "dry_run": False,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2568_artifacts": False,
        "v2568_build_root": root / "build",
        "v2568_manifest_path": root / "build/manifest.json",
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
        "android_root_recheck_attempts": 1,
        "android_root_recheck_sleep_sec": 0.0,
        "android_settle_adb_retry_attempts": 1,
        "android_settle_adb_retry_sleep_sec": 0.0,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class NativeAudioAcdbPreinitPerdeviceCaptureLiveHandoffV2569(unittest.TestCase):
    def test_to_v2490_args_forces_combined_preload_and_fake_allocate(self) -> None:
        local = args()
        artifacts = {
            "helper": {"path": "workspace/private/builds/audio/x/bin/helper", "sha256": "a" * 64},
            "preload": {"path": "workspace/private/builds/audio/x/bin/preload.so", "sha256": "b" * 64},
        }

        base = v2569.to_v2490_args(local, artifacts)

        self.assertTrue(base.use_combined_preload)
        self.assertFalse(base.enable_acdbtap_preload)
        self.assertFalse(base.disable_ioctl_trace)
        self.assertTrue(base.fake_audio_cal_allocate)
        self.assertEqual(base.helper_sha256, "a" * 64)
        self.assertEqual(base.combined_preload_sha256, "b" * 64)

    def test_summary_accepts_topology_and_per_device_records(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2569-summary-ok-"))
        acdbtap = root / "acdbtap"
        topology = b"T" * 4916
        per_device = b"P" * 128
        topology_raw = acdbtap / "acdbtap-00000002-cmd-00013296-len-00001334.bin"
        per_device_raw = acdbtap / "acdbtap-00000003-cmd-00012000-len-00000080.bin"
        topology_raw.parent.mkdir(parents=True, exist_ok=True)
        topology_raw.write_bytes(topology)
        per_device_raw.write_bytes(per_device)
        write_jsonl(root / "acdb-v2568-preinit-perdevice-events.jsonl", [
            {"event": "v2568_preinit_perdevice", "stage": "entered_common_topology_hook", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "before_real_common_topology", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "real_common_topology_return", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "patch_initialized_flag_return", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "before_send_audio_cal_v5", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "send_audio_cal_v5_return", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "exit_before_init_tail", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000002",
                "cmd": "0x00013296",
                "in_len": "0x00000008",
                "out_len": "0x00001334",
                "ret": "0x00000000",
                "raw_path": "/data/local/tmp/a90-acdb-tap/" + topology_raw.name,
                "sha256": hashlib.sha256(topology).hexdigest(),
            },
            {
                "seq": "0x00000003",
                "cmd": "0x00012000",
                "in_len": "0x00000010",
                "out_len": "0x00000080",
                "ret": "0x00000000",
                "raw_path": "/data/local/tmp/a90-acdb-tap/" + per_device_raw.name,
                "sha256": hashlib.sha256(per_device).hexdigest(),
            },
        ])

        summary = v2569.summarize_preinit_perdevice_capture(root)

        self.assertEqual(summary["classification"], "v2569-preinit-perdevice-manifest-captured")
        self.assertTrue(summary["full_success"])
        self.assertTrue(summary["real_common_topology_called"])
        self.assertTrue(summary["patch_initialized_flag_ok"])
        self.assertTrue(summary["send_audio_cal_v5_reached"])
        self.assertTrue(summary["exited_before_init_tail"])
        self.assertEqual(summary["topology_success_count"], 1)
        self.assertEqual(summary["per_device_success_count"], 1)

    def test_summary_rejects_zero_topology_as_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2569-summary-zero-"))
        acdbtap = root / "acdbtap"
        raw = acdbtap / "acdbtap-00000002-cmd-00013296-len-00001334.bin"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\0" * 4916)
        write_jsonl(root / "acdb-v2568-preinit-perdevice-events.jsonl", [
            {"event": "v2568_preinit_perdevice", "stage": "before_real_common_topology", "code": 0},
            {"event": "v2568_preinit_perdevice", "stage": "real_common_topology_return", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000002",
                "cmd": "0x00013296",
                "in_len": "0x00000008",
                "out_len": "0x00001334",
                "ret": "0x00000000",
                "raw_path": "/data/local/tmp/a90-acdb-tap/" + raw.name,
                "sha256": hashlib.sha256(b"\0" * 4916).hexdigest(),
            },
        ])

        summary = v2569.summarize_preinit_perdevice_capture(root)

        self.assertNotEqual(summary["classification"], "v2569-preinit-perdevice-manifest-captured")
        self.assertFalse(summary["full_success"])

    def test_summary_flags_real_set_passthrough(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2569-summary-set-"))
        write_jsonl(root / "ioctl-trace-events.jsonl", [
            {"event": "ioctl_trace", "name": "AUDIO_SET_CALIBRATION", "intercept": "pass-through"},
        ])

        summary = v2569.summarize_preinit_perdevice_capture(root)

        self.assertEqual(summary["classification"], "v2569-boundary-violation-real-audio-set-passthrough")
        self.assertFalse(summary["full_success"])

    def test_dry_run_reports_not_ready_without_artifacts(self) -> None:
        payload = v2569.dry_run_payload(args())

        self.assertFalse(payload["ok"])
        self.assertIn("V2568 pre-init-tail helper/preload artifacts are not ready", payload["live_blockers"])

    def test_builder_manifest_can_be_selected_when_artifacts_exist(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2569-select-test-"))
        helper = root / "helper"
        preload = root / "preload.so"
        helper.write_bytes(b"helper")
        preload.write_bytes(b"preload")
        helper.chmod(0o600)
        preload.chmod(0o600)
        manifest = {
            "ok": True,
            "build": {
                "artifacts": {
                    "helper": {"ok": True, "path": v2568.rel(helper), "sha256": hashlib.sha256(b"helper").hexdigest()},
                    "preload": {"ok": True, "path": v2568.rel(preload), "sha256": hashlib.sha256(b"preload").hexdigest()},
                }
            },
            "sources": {
                "required": {
                    "preinit_exports_common_topology": True,
                    "preinit_calls_real_common_topology": True,
                    "preinit_patches_init_flag": True,
                    "preinit_calls_send_audio_cal_v5": True,
                    "preinit_exits_before_init_tail": True,
                    "ioctl_fake_allocate_set": True,
                }
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        selected = v2569.selected_artifacts(args(v2568_manifest_path=manifest_path))

        self.assertTrue(selected["ok"], selected)
        self.assertTrue(selected["manifest"]["checks"]["preinit_patches_init_flag"])


if __name__ == "__main__":
    unittest.main()
