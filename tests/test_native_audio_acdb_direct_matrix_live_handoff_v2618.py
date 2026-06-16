"""Tests for the V2618 ACDB direct matrix live wrapper."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2618 = load_revalidation("native_audio_acdb_direct_matrix_live_handoff_v2618")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2618-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2617_artifacts": False,
        "v2617_build_root": v2618.v2617.DEFAULT_BUILD_ROOT,
        "v2617_manifest_path": v2618.v2617.DEFAULT_MANIFEST,
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
        "android_root_recheck_attempts": v2618.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": v2618.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
        "android_settle_adb_retry_attempts": v2618.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2618.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


class NativeAudioAcdbDirectMatrixLiveHandoffV2618(unittest.TestCase):
    def test_read_v2617_manifest_checks_manual_arm_contract(self) -> None:
        manifest = v2618.read_v2617_manifest(v2618.v2617.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"], manifest)
        self.assertTrue(manifest["direct_matrix_contract_ok"], manifest)
        self.assertTrue(manifest["armed_contract_ok"], manifest)

    def test_summarize_direct_matrix_partial_no_vol(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2618-summary-"))
        acdbtap = root / "acdbtap"
        acdbtap.mkdir(parents=True, exist_ok=True)
        raw_ap = acdbtap / "acdbtap-00000004-cmd-00013265-len-000046a4.bin"
        raw_ap.write_bytes(b"A" * 18084)
        raw_afe = acdbtap / "acdbtap-0000000b-cmd-0001326f-len-00000618.bin"
        raw_afe.write_bytes(b"B" * 1560)
        raw_size = acdbtap / "acdbtap-00000003-cmd-00013267-len-00000004.bin"
        raw_size.write_bytes((18084).to_bytes(4, "little"))
        write_jsonl(
            acdbtap / "acdbtap-events.jsonl",
            [
                {
                    "event": "acdb_ioctl",
                    "seq": 3,
                    "cmd": "0x00013267",
                    "in_len": 12,
                    "out_len": 4,
                    "ret": 0,
                    "raw_path": str(raw_size),
                    "sha256": hashlib.sha256(raw_size.read_bytes()).hexdigest(),
                },
                {
                    "event": "acdb_ioctl",
                    "seq": 4,
                    "cmd": "0x00013265",
                    "in_len": 20,
                    "out_len": 18084,
                    "ret": 0,
                    "raw_path": str(raw_ap),
                    "sha256": hashlib.sha256(raw_ap.read_bytes()).hexdigest(),
                },
                {
                    "event": "acdb_ioctl",
                    "seq": 11,
                    "cmd": "0x0001326f",
                    "in_len": 16,
                    "out_len": 1560,
                    "ret": 0,
                    "raw_path": str(raw_afe),
                    "sha256": hashlib.sha256(raw_afe.read_bytes()).hexdigest(),
                },
            ],
        )
        helper_rows = [
            {"event": "v2617_direct_matrix", "stage": "before_base_matrix", "code": 0},
            {"event": "v2617_direct_matrix", "stage": "before_vol_sweep", "code": 0},
        ]
        for index in range(42):
            helper_rows.append(
                {
                    "event": "v2617_direct_matrix",
                    "stage": "case_return",
                    "case": "vol-data" if index >= 26 else "audproc-common-data",
                    "cmd": "0x0001326e" if index >= 26 else "0x00013265",
                    "step": index - 26 if index >= 26 else 0,
                    "ret": -19 if index >= 26 else 0,
                }
            )
        helper_rows.append({"event": "v2617_direct_matrix", "stage": "done", "code": 0})
        write_jsonl(root / "acdb-v2617-direct-matrix-events.jsonl", helper_rows)

        summary = v2618.summarize_direct_matrix_capture(root)

        self.assertEqual(summary["classification"], "v2618-direct-matrix-perdevice-partial-no-vol")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["partial_success"])
        self.assertEqual(summary["case_return_count"], 42)
        self.assertTrue(summary["matrix_complete"])
        self.assertEqual(summary["per_device_success_count"], 2)
        self.assertEqual(summary["audproc_payload_count"], 1)
        self.assertEqual(summary["afe_payload_count"], 1)
        self.assertEqual(summary["vol_payload_count"], 0)

    def test_dry_run_uses_v2490_engine_with_v2617_artifacts(self) -> None:
        payload = v2618.dry_run_payload(args())

        self.assertTrue(payload["ok"], payload.get("live_blockers"))
        self.assertTrue(payload["capture_contract"]["manual_arm_after_init"])
        self.assertFalse(payload["capture_contract"]["auto_arm_on_initialize"])
        self.assertFalse(payload["capture_contract"]["exit_on_first_4916"])
        self.assertTrue(payload["v2617_artifacts"]["ok"])
        self.assertTrue(payload["v2490_engine"]["live_ready"])


if __name__ == "__main__":
    unittest.main()
