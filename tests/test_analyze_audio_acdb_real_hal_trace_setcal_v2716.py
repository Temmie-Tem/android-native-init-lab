"""Tests for V2716 real-HAL ACDB SET_CAL target reparse."""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2716 = load_revalidation("analyze_audio_acdb_real_hal_trace_setcal_v2716")


def pack_set_arg(*, data_size: int = 32, cal_type: int, cal_size: int, mem_handle: int) -> str:
    return struct.pack(
        "<7Ii",
        data_size,
        0,
        cal_type,
        16 if data_size == 32 else data_size - 16,
        0,
        0,
        cal_size,
        mem_handle,
    ).hex()


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def make_args(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        runs_root=root / "runs/audio",
        run_name=[
            "v2461-acdb-compat-live-20260615-190530",
            "v2466-acdb-dmabuf-live-20260615-200643",
        ],
        manifest_path=root / "builds/v2716/manifest.json",
        report_path=root / "report.md",
        write_report=False,
    )


def make_fixture(root: Path, *, include_target: bool) -> argparse.Namespace:
    local_args = make_args(root)
    rows = [
        {
            "event": "ioctl_entry",
            "request": "0xc00461cb",
            "seq": 1,
            "bytes_hex": pack_set_arg(cal_type=39, cal_size=4916, mem_handle=37),
        },
        {
            "event": "ioctl_entry",
            "request": "0xc00461cb",
            "seq": 2,
            "bytes_hex": pack_set_arg(data_size=68, cal_type=20, cal_size=0, mem_handle=-1),
        },
    ]
    if include_target:
        rows.append(
            {
                "event": "ioctl_entry",
                "request": "0xc00461cb",
                "seq": 3,
                "bytes_hex": pack_set_arg(cal_type=24, cal_size=1180, mem_handle=41),
            }
        )
    write_jsonl(
        local_args.runs_root
        / "v2466-acdb-dmabuf-live-20260615-200643/device-artifacts/msm-audio-cal-diag-threadset-p1.jsonl",
        rows,
    )
    return local_args


class AnalyzeAudioAcdbRealHalTraceSetcalV2716(unittest.TestCase):
    def test_manifest_classifies_missing_target_topologies(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2716-test-"))
        local_args = make_fixture(root, include_target=False)

        payload = v2716.build_payload(local_args)

        self.assertEqual(payload["decision"], "v2716-real-hal-trace-no-subsystem-custom-topology-set")
        self.assertEqual(payload["summary"]["observed_cal_types"], [20, 39])
        self.assertEqual(payload["summary"]["present_target_cal_types"], [])
        self.assertEqual(payload["summary"]["missing_target_cal_types"], [10, 14, 24])
        self.assertFalse(payload["conclusions"]["existing_trace_is_sufficient_for_gate4_manifest"])
        self.assertNotIn("bytes_hex", json.dumps(payload))

    def test_manifest_classifies_present_target_topology(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2716-test-"))
        local_args = make_fixture(root, include_target=True)

        payload = v2716.build_payload(local_args)

        self.assertEqual(payload["decision"], "v2716-real-hal-trace-custom-topology-set-present")
        self.assertEqual(payload["summary"]["present_target_cal_types"], [24])
        self.assertTrue(payload["conclusions"]["existing_trace_contains_cal24"])

    def test_cli_writes_manifest_and_report(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2716-test-"))
        local_args = make_fixture(root, include_target=False)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/analyze_audio_acdb_real_hal_trace_setcal_v2716.py",
                "--runs-root",
                str(local_args.runs_root),
                "--manifest-path",
                str(local_args.manifest_path),
                "--report-path",
                str(local_args.report_path),
                "--write-report",
            ],
            cwd=v2716.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(local_args.manifest_path.exists())
        self.assertTrue(local_args.report_path.exists())
        report = local_args.report_path.read_text(encoding="utf-8")
        self.assertIn("present target cal_types 10/14/24: `(none)`", report)
        self.assertIn("cal_type `39` and cal_type", report)


if __name__ == "__main__":
    unittest.main()
