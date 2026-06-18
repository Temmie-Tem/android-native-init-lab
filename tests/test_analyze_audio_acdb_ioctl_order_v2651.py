"""Tests for V2651 ACDB audio-cal ioctl order analyzer."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2651 = load_revalidation("analyze_audio_acdb_ioctl_order_v2651")


def args(root: Path, **overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "runs_root": root / "runs",
        "builds_root": root / "builds",
        "setcal_capture": root / "runs/v2632-acdb-setcal-capture/ownget-device-artifacts/setcal-events.jsonl",
        "v2634_manifest": root / "builds/v2634/setcal-replay-gate-manifest.json",
        "v2639_manifest": root / "builds/v2639/manifest.json",
        "v2648_run": root / "runs/v2639-acdb-setcal-replay",
        "manifest_path": root / "builds/v2651/manifest.json",
        "write_report": False,
        "report_path": root / "report.md",
        "pretty": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def make_fixture(root: Path, *, include_prepare: bool = False) -> argparse.Namespace:
    local_args = args(root)
    write_jsonl(
        local_args.setcal_capture,
        [
            {"event": "setcal_capture", "sequence": 1, "request": "0xc00461cb", "cal_type": 13, "data_size": 40},
            {"event": "setcal_capture", "sequence": 2, "request": "0xc00461cb", "cal_type": 9, "data_size": 52},
            {"event": "setcal_capture", "sequence": 3, "request": "0xc00461cb", "cal_type": 11, "data_size": 48},
        ],
    )
    write_json(
        local_args.v2634_manifest,
        {
            "set_records": [
                {"sequence": 1, "cal_type": 13, "role": "APP_META_HEADER"},
                {"sequence": 2, "cal_type": 9, "role": "AFE_TOPOLOGY_HEADER"},
                {"sequence": 3, "cal_type": 11, "role": "AUDPROC_PAYLOAD"},
            ]
        },
    )
    write_json(
        local_args.v2639_manifest,
        {
            "remote": {
                "argv": [
                    "helper",
                    "--basic-payload",
                    "39:0:/cache/topology.bin",
                    "--exact-set",
                    "/cache/01-set-arg-cal13.bin",
                    "--exact-set",
                    "/cache/02-set-arg-cal09.bin",
                    "--exact-set",
                    "/cache/03-set-arg-cal11.bin:/cache/03-payload-cal11.bin",
                ]
            }
        },
    )
    replay = local_args.v2648_run / "61_acdb-setcal-helper-deallocate-check.json"
    stdout_tail = "\n".join(
        [
            "AUDIO_ALLOCATE_CALIBRATION ok cal_type=39 buffer=0 cal_size=0 mem_handle=4 arg_len=32",
            "AUDIO_SET_CALIBRATION ok cal_type=39 buffer=0 cal_size=4916 mem_handle=4 arg_len=32",
            "A90_ACDB_SETCAL_SET_OK index=0 cal_type=39 kind=1 has_payload=1",
            "AUDIO_SET_CALIBRATION ok cal_type=13 buffer=0 cal_size=0 mem_handle=-1 arg_len=40",
            "A90_ACDB_SETCAL_SET_OK index=1 cal_type=13 kind=2 has_payload=0",
        ]
    )
    write_json(replay, {"stdout_tail": stdout_tail})
    if include_prepare:
        write_json(
            root / "runs/acdb-extra/result.json",
            {"row": {"request": "0xc00461ca", "name": "AUDIO_PREPARE_CALIBRATION", "cal_type": 8, "ret": 0}},
        )
    return local_args


class AnalyzeAudioAcdbIoctlOrderV2651(unittest.TestCase):
    def test_manifest_classifies_order_gap_when_no_prepare_post_or_cal8(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2651-test-"))
        local_args = make_fixture(root)

        payload = v2651.manifest(local_args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["orders"]["v2632_fake_set_capture"], [13, 9, 11])
        self.assertEqual(payload["orders"]["v2639_native_replay_plan"], [39, 13, 9, 11])
        self.assertFalse(payload["conclusions"]["audio_prepare_seen_in_existing_evidence"])
        self.assertFalse(payload["conclusions"]["cal_type8_seen_in_existing_evidence"])
        self.assertFalse(payload["conclusions"]["existing_evidence_enough_to_change_replay"])
        self.assertIn("real-set-undecoded-requires-android-good-ioctl-order-capture", payload["decision"])

    def test_manifest_surfaces_prepare_and_cal8_if_present(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2651-test-"))
        local_args = make_fixture(root, include_prepare=True)

        payload = v2651.manifest(local_args)

        self.assertTrue(payload["conclusions"]["audio_prepare_seen_in_existing_evidence"])
        self.assertTrue(payload["conclusions"]["cal_type8_seen_in_existing_evidence"])
        self.assertTrue(payload["conclusions"]["existing_evidence_enough_to_change_replay"])
        self.assertIn("order-edge-found", payload["decision"])

    def test_cli_writes_manifest_and_report(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2651-test-"))
        local_args = make_fixture(root)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/analyze_audio_acdb_ioctl_order_v2651.py",
                "--runs-root",
                str(local_args.runs_root),
                "--builds-root",
                str(local_args.builds_root),
                "--setcal-capture",
                str(local_args.setcal_capture),
                "--v2634-manifest",
                str(local_args.v2634_manifest),
                "--v2639-manifest",
                str(local_args.v2639_manifest),
                "--v2648-run",
                str(local_args.v2648_run),
                "--manifest-path",
                str(local_args.manifest_path),
                "--write-report",
                "--report-path",
                str(local_args.report_path),
            ],
            cwd=v2651.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(local_args.manifest_path.exists())
        self.assertTrue(local_args.report_path.exists())
        self.assertIn("AUDIO_PREPARE_CALIBRATION", local_args.report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
