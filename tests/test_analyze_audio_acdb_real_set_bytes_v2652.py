"""Tests for V2652 ACDB real SET arg byte decoder."""

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

v2652 = load_revalidation("analyze_audio_acdb_real_set_bytes_v2652")


def pack_set_arg(
    *,
    data_size: int,
    cal_type: int,
    cal_type_size: int,
    buffer_number: int,
    cal_size: int,
    mem_handle: int,
    tail_words: list[int],
) -> str:
    head = struct.pack(
        "<7Ii",
        data_size,
        0,
        cal_type,
        cal_type_size,
        0,
        buffer_number,
        cal_size,
        mem_handle,
    )
    tail = b"".join(struct.pack("<I", word) for word in tail_words)
    return (head + tail).hex()


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def args(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        runs_root=root / "runs/audio",
        setcal_capture=root / "runs/audio/v2632-acdb-setcal/ownget-device-artifacts/setcal-events.jsonl",
        manifest_path=root / "builds/v2652/manifest.json",
        report_path=root / "report.md",
        write_report=False,
        pretty=False,
    )


def make_fixture(root: Path) -> argparse.Namespace:
    local_args = args(root)
    write_jsonl(
        local_args.runs_root
        / "v2461-acdb-compat-live-20260615-190530/device-artifacts/msm-audio-cal-diag-threadset-p1.jsonl",
        [
            {
                "event": "ioctl_entry",
                "request": "0xc00461cb",
                "seq": 1,
                "tid": 11,
                "fd_pid": 10,
                "ts_ms": 100,
                "bytes_hex": pack_set_arg(
                    data_size=32,
                    cal_type=39,
                    cal_type_size=16,
                    buffer_number=0,
                    cal_size=4916,
                    mem_handle=35,
                    tail_words=[4916, 0x1000],
                ),
            },
            {
                "event": "ioctl_entry",
                "request": "0xc00461cb",
                "seq": 2,
                "tid": 11,
                "fd_pid": 10,
                "ts_ms": 101,
                "bytes_hex": pack_set_arg(
                    data_size=68,
                    cal_type=20,
                    cal_type_size=52,
                    buffer_number=0,
                    cal_size=0,
                    mem_handle=-1,
                    tail_words=[15, 0, 1, 3, 48000, 474, 96000, 237, 192000],
                ),
            },
            {
                "event": "ioctl_entry",
                "request": "0xc00461c8",
                "seq": 3,
                "bytes_hex": pack_set_arg(
                    data_size=32,
                    cal_type=39,
                    cal_type_size=16,
                    buffer_number=0,
                    cal_size=4916,
                    mem_handle=35,
                    tail_words=[],
                ),
            },
        ],
    )
    write_jsonl(
        local_args.setcal_capture,
        [
            {"event": "setcal_capture", "request": "0xc00461cb", "cal_type": 13},
            {"event": "setcal_capture", "request": "0xc00461cb", "cal_type": 9},
        ],
    )
    return local_args


class AnalyzeAudioAcdbRealSetBytesV2652(unittest.TestCase):
    def test_decode_set_arg_bytes_reads_signed_mem_handle(self) -> None:
        decoded = v2652.decode_set_arg_bytes(
            pack_set_arg(
                data_size=68,
                cal_type=20,
                cal_type_size=52,
                buffer_number=0,
                cal_size=0,
                mem_handle=-1,
                tail_words=[15, 48000],
            )
        )

        self.assertEqual(decoded["cal_type"], 20)
        self.assertEqual(decoded["mem_handle"], -1)
        self.assertEqual(decoded["scalar_words"], [15, 48000])

    def test_manifest_finds_cal20_extra_type(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2652-test-"))
        local_args = make_fixture(root)

        payload = v2652.manifest(local_args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2652-extra-real-set-cal20-found-host-only")
        self.assertEqual(payload["orders"]["v2632_fake_set_capture"], [13, 9])
        self.assertEqual(payload["real_set_decode"]["cal_type_counts"], {20: 1, 39: 1})
        self.assertEqual(payload["conclusions"]["extra_real_cal_types_not_in_native_replay"], [20])
        self.assertFalse(payload["conclusions"]["cal_type8_seen"])
        self.assertTrue(payload["conclusions"]["native_replay_should_not_rerun_unchanged"])
        self.assertNotIn("bytes_hex", json.dumps(payload))

    def test_cli_writes_manifest_and_report_without_raw_bytes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2652-test-"))
        local_args = make_fixture(root)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/analyze_audio_acdb_real_set_bytes_v2652.py",
                "--runs-root",
                str(local_args.runs_root),
                "--setcal-capture",
                str(local_args.setcal_capture),
                "--manifest-path",
                str(local_args.manifest_path),
                "--write-report",
                "--report-path",
                str(local_args.report_path),
            ],
            cwd=v2652.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2652-extra-real-set-cal20-found-host-only")
        self.assertTrue(local_args.manifest_path.exists())
        report = local_args.report_path.read_text(encoding="utf-8")
        self.assertIn("cal_type `20`", report)
        self.assertIn("`bytes_hex`", report)
        self.assertNotIn("2700000010000000", report)


if __name__ == "__main__":
    unittest.main()
