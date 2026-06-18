"""Tests for the V2693 lower ACDB pointer-target capture live wrapper."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2693 = load_revalidation("native_audio_acdb_lower_ptrtarget_capture_live_handoff_v2693")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2693-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2692_artifacts": False,
        "v2692_build_root": v2693.v2692.DEFAULT_BUILD_ROOT,
        "v2692_manifest_path": v2693.v2692.DEFAULT_MANIFEST,
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
        "android_root_recheck_attempts": v2693.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": v2693.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
        "android_settle_adb_retry_attempts": v2693.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2693.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_jsonl(path: Path, rows: list[dict[str, object] | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    for row in rows:
        out.append(row if isinstance(row, str) else json.dumps(row, sort_keys=True))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


class NativeAudioAcdbLowerPtrtargetCaptureLiveHandoffV2693(unittest.TestCase):
    def test_read_v2692_manifest_checks_ptrtarget_contract(self) -> None:
        manifest = v2693.read_v2692_manifest(v2693.v2692.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"], manifest)
        self.assertTrue(manifest["ptrtarget_contract_ok"], manifest)

    def test_tolerant_jsonl_accepts_c_emitted_hex_fields(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2693-hex-"))
        path = root / "acdbtap-events.jsonl"
        path.write_text(
            '{"event":"ptrtarget_status","seq":0x1,"cmd":0x130da,"in_len":0x8,"ptr":0xe9383000,"requested_len":0x20,"dump_len":0x20,"map_start":0xe9383000,"map_end":0xe9384000,"status":"ptrtarget_maps_verified"}\n',
            encoding="utf-8",
        )

        rows = v2693.read_tolerant_jsonl(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cmd"], 0x130DA)
        self.assertEqual(rows[0]["ptr"], 0xE9383000)

    def test_summarize_ptrtarget_capture_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2693-success-"))
        tap = root / "acdbtap"
        payload = bytes(range(32))
        sha = hashlib.sha256(payload).hexdigest()
        raw_path = "/data/local/tmp/a90-acdb-tap/acdbtap-ptrtarget-pre-0001-000130da-00000020.bin"
        (tap / Path(raw_path).name).parent.mkdir(parents=True, exist_ok=True)
        (tap / Path(raw_path).name).write_bytes(payload)
        write_jsonl(
            tap / "acdbtap-events.jsonl",
            [
                '{"event":"ptrtarget_status","seq":0x1,"cmd":0x130da,"in_len":0x8,"ptr":0xe9383000,"requested_len":0x20,"dump_len":0x20,"map_start":0xe9383000,"map_end":0xe9384000,"status":"ptrtarget_maps_verified"}',
                {
                    "seq": 1,
                    "pid": 1,
                    "tid": 1,
                    "cmd": 0x130DA,
                    "in_len": 8,
                    "out_len": 32,
                    "ret": 0,
                    "buffer": "ptrtarget-pre",
                    "sha256": sha,
                    "raw_path": raw_path,
                    "raw_written": True,
                    "is_target_4916": False,
                    "is_size_query_4": False,
                    "all_zero": False,
                },
            ],
        )
        write_jsonl(
            root / "acdb-v2674-lower-hidden-inhook-events.jsonl",
            [
                {
                    "event": "v2692_lower_block_snapshot",
                    "cal_type": 24,
                    "get_arg0": "0x00000020",
                    "get_arg1": "0xe9383000",
                    "mem_handle": -1,
                }
            ],
        )

        summary = v2693.summarize_ptrtarget_capture(root)

        self.assertEqual(summary["classification"], "v2693-ptrtarget-captured")
        self.assertTrue(summary["success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertEqual(summary["ptrtarget_maps_verified_cal_types"], [24])
        self.assertEqual(summary["ptrtarget_dumped_cal_types"], [24])
        self.assertEqual(summary["block_snapshot_cal_types"], [24])
        self.assertEqual(summary["ptrtarget_records"][0]["raw_sha256"], sha)

    def test_summarize_ptrtarget_status_only_is_partial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2693-status-"))
        write_jsonl(
            root / "acdbtap" / "acdbtap-events.jsonl",
            [
                '{"event":"ptrtarget_status","seq":0x1,"cmd":0x11394,"in_len":0x8,"ptr":0xe9382000,"requested_len":0x0,"dump_len":0x0,"map_start":0x0,"map_end":0x0,"status":"ptrtarget_zero_len"}'
            ],
        )

        summary = v2693.summarize_ptrtarget_capture(root)

        self.assertEqual(summary["classification"], "v2693-ptrtarget-status-only")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_dry_run_ready_uses_v2692_artifacts(self) -> None:
        payload = v2693.dry_run_payload(args())

        self.assertTrue(payload["ok"], payload.get("live_blockers"))
        self.assertTrue(payload["live_ready"])
        self.assertIn("ptrtarget", payload["decision"])
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [10, 14, 24])
        self.assertTrue(payload["v2692_artifacts"]["manifest"]["ptrtarget_contract_ok"])


if __name__ == "__main__":
    unittest.main()
