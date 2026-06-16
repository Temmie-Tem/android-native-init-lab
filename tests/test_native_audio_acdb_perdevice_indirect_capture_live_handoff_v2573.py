"""Host-only tests for the V2573 ACDB per-device indirect live wrapper."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2573 = load_revalidation("native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_raw(root: Path, name: str, data: bytes) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/data/local/tmp/a90-acdb-tap/{name}"


class AcdbPerdeviceIndirectCaptureLiveV2573(unittest.TestCase):
    def test_to_v2490_args_forces_v2572_artifacts_and_fake_allocate(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2573-args-"))
        helper = root / "helper"
        preload = root / "preload.so"
        helper.write_bytes(b"helper")
        preload.write_bytes(b"preload")
        artifacts = {
            "helper": {"path": str(helper), "sha256": hashlib.sha256(b"helper").hexdigest()},
            "preload": {"path": str(preload), "sha256": hashlib.sha256(b"preload").hexdigest()},
        }
        args = Namespace(
            dry_run=True,
            run_live=False,
            out_dir=None,
            adb="adb",
            serial=None,
            from_native=True,
            android_timeout=240.0,
            flash_timeout=420.0,
            adb_command_timeout=90.0,
            adb_pull_timeout=120.0,
            helper_timeout=90.0,
            android_root_recheck_attempts=v2573.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
            android_root_recheck_sleep_sec=v2573.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
            android_settle_adb_retry_attempts=v2573.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
            android_settle_adb_retry_sleep_sec=v2573.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
            readelf="readelf",
            file="file",
        )

        base = v2573.to_v2490_args(args, artifacts)

        self.assertTrue(base.use_combined_preload)
        self.assertTrue(base.fake_audio_cal_allocate)
        self.assertFalse(base.enable_acdbtap_preload)
        self.assertEqual(base.helper_path, helper)
        self.assertEqual(base.combined_preload_so, preload)

    def test_summarize_perdevice_indirect_capture_accepts_nonzero_non_topology_record(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2573-per-device-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        per_device = bytes([3]) * 128
        per_device_path = write_raw(acdbtap, "acdbtap-00000002-cmd-00012e01-len-00000080.bin", per_device)
        write_jsonl(artifact / "acdb-v2572-perdevice-indirect-events.jsonl", [
            {"event": "v2572_perdevice_indirect", "stage": "skip_real_common_topology", "code": 0},
            {"event": "v2572_perdevice_indirect", "stage": "patch_initialized_flag_return", "code": 0},
            {"event": "v2572_perdevice_indirect", "stage": "before_send_audio_cal_v5", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000002",
                "cmd": "0x00012e01",
                "in_len": "0x00000008",
                "out_len": "0x00000080",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(per_device).hexdigest(),
                "raw_path": per_device_path,
                "raw_written": True,
                "is_target_4916": False,
                "buffer": "indirect",
                "all_zero": False,
            },
        ])
        write_jsonl(artifact / "ioctl-trace-events.jsonl", [
            {
                "event": "ioctl_trace",
                "request": "0xc00461cb",
                "name": "AUDIO_SET_CALIBRATION",
                "intercept": "fake-success",
                "arg_snapshot": {"cal_type": 11, "cal_size": 128},
            }
        ])

        summary = v2573.summarize_perdevice_indirect_capture(artifact)

        self.assertEqual(summary["classification"], "v2573-perdevice-indirect-captured")
        self.assertTrue(summary["full_success"])
        self.assertTrue(summary["per_device_success"])
        self.assertTrue(summary["send_audio_cal_v5_reached"])
        self.assertTrue(summary["skip_real_common_topology_seen"])
        self.assertTrue(summary["patch_initialized_flag_ok"])
        self.assertEqual(summary["topology_success_count"], 0)
        self.assertEqual(summary["per_device_success_count"], 1)
        self.assertEqual(summary["real_audio_set_pass_through_count"], 0)

    def test_real_audio_set_passthrough_is_boundary_violation(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2573-boundary-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        per_device = bytes([4]) * 64
        per_device_path = write_raw(acdbtap, "acdbtap-00000001-cmd-00012e01-len-00000040.bin", per_device)
        write_jsonl(artifact / "acdb-v2572-perdevice-indirect-events.jsonl", [
            {"event": "v2572_perdevice_indirect", "stage": "before_send_audio_cal_v5", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000001",
                "cmd": "0x00012e01",
                "in_len": "0x00000008",
                "out_len": "0x00000040",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(per_device).hexdigest(),
                "raw_path": per_device_path,
                "raw_written": True,
                "is_target_4916": False,
                "all_zero": False,
            },
        ])
        write_jsonl(artifact / "ioctl-trace-events.jsonl", [
            {"event": "ioctl_trace", "name": "AUDIO_SET_CALIBRATION", "intercept": "pass-through"}
        ])

        summary = v2573.summarize_perdevice_indirect_capture(artifact)

        self.assertEqual(summary["classification"], "v2573-boundary-violation-real-audio-set-passthrough")
        self.assertFalse(summary["full_success"])
        self.assertEqual(summary["real_audio_set_pass_through_count"], 1)

    def test_topology_recapture_without_helper_marker_is_not_per_device_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2573-topology-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        topology = bytes([1]) * 4916
        init_record = bytes([2]) * 16
        topology_path = write_raw(acdbtap, "acdbtap-00000003-cmd-00013296-len-00001334.bin", topology)
        init_path = write_raw(acdbtap, "acdbtap-00000000-cmd-000131de-len-00000010.bin", init_record)
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000000",
                "cmd": "0x000131de",
                "in_len": "0x00000000",
                "out_len": "0x00000010",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(init_record).hexdigest(),
                "raw_path": init_path,
                "raw_written": True,
                "is_target_4916": False,
                "all_zero": False,
            },
            {
                "seq": "0x00000003",
                "cmd": "0x00013296",
                "in_len": "0x00000008",
                "out_len": "0x00001334",
                "ret": "0x00000000",
                "sha256": hashlib.sha256(topology).hexdigest(),
                "raw_path": topology_path,
                "raw_written": True,
                "is_target_4916": True,
                "all_zero": False,
            },
        ])

        summary = v2573.summarize_perdevice_indirect_capture(artifact)

        self.assertEqual(summary["classification"], "v2573-init-common-topology-recaptured-before-per-device")
        self.assertFalse(summary["full_success"])
        self.assertFalse(summary["per_device_success"])
        self.assertFalse(summary["send_audio_cal_v5_reached"])
        self.assertEqual(summary["per_device_success_count"], 0)


if __name__ == "__main__":
    unittest.main()
