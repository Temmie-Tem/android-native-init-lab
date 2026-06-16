"""Host-only tests for the V2555 ACDB full-manifest live wrapper."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2555 = load_revalidation("native_audio_acdb_full_manifest_live_handoff_v2555")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_raw(root: Path, name: str, data: bytes) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/data/local/tmp/a90-acdb-tap/{name}"


class AcdbFullManifestLiveV2555(unittest.TestCase):
    def test_to_v2490_args_forces_manual_arm_artifacts_and_fake_allocate(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2555-args-"))
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
            android_root_recheck_attempts=v2555.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
            android_root_recheck_sleep_sec=v2555.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
            android_settle_adb_retry_attempts=v2555.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
            android_settle_adb_retry_sleep_sec=v2555.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
            readelf="readelf",
            file="file",
        )

        base = v2555.to_v2490_args(args, artifacts)

        self.assertTrue(base.use_combined_preload)
        self.assertTrue(base.fake_audio_cal_allocate)
        self.assertFalse(base.enable_acdbtap_preload)
        self.assertEqual(base.helper_path, helper)
        self.assertEqual(base.combined_preload_so, preload)

    def test_summarize_full_manifest_requires_topology_and_per_device_nonzero(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2555-full-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        topology = bytes([1]) * 4916
        per_device = bytes([2]) * 128
        topology_path = write_raw(acdbtap, "acdbtap-00000001-cmd-00013296-len-00001334.bin", topology)
        per_device_path = write_raw(acdbtap, "acdbtap-00000002-cmd-00012e01-len-00000080.bin", per_device)
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000001",
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

        summary = v2555.summarize_full_manifest(artifact)

        self.assertEqual(summary["classification"], "v2555-full-manifest-captured")
        self.assertTrue(summary["full_success"])
        self.assertEqual(summary["topology_success_count"], 1)
        self.assertEqual(summary["per_device_success_count"], 1)
        self.assertEqual(summary["real_audio_set_pass_through_count"], 0)

    def test_zero_4916_or_ret_failure_is_not_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2555-zero-"))
        artifact = root / "device"
        acdbtap = artifact / "acdbtap"
        zero = b"\0" * 4916
        raw_path = write_raw(acdbtap, "acdbtap-00000001-cmd-00013296-len-00001334.bin", zero)
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {
                "seq": "0x00000001",
                "cmd": "0x00013296",
                "in_len": "0x00000008",
                "out_len": "0x00001334",
                "ret": "0xfffffffe",
                "sha256": hashlib.sha256(zero).hexdigest(),
                "raw_path": raw_path,
                "raw_written": True,
                "is_target_4916": True,
                "all_zero": True,
            }
        ])

        summary = v2555.summarize_full_manifest(artifact)

        self.assertFalse(summary["full_success"])
        self.assertFalse(summary["partial_success"])
        self.assertIn("dispatch-ret-failed-zero-outbuf", summary["classification"])


if __name__ == "__main__":
    unittest.main()
