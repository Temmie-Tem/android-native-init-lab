"""Tests for V2615 ACDB per-device manifest candidate builder."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2615 = load_revalidation("analyze_audio_acdb_perdevice_manifest_v2615")


def args(root: Path, **overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "run_dir": root / "run",
        "topology_payload": root / "topology.bin",
        "manifest_path": root / "manifest.json",
        "write_report": False,
        "report_path": root / "report.md",
        "pretty": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_file(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def row(seq: int, cmd: str, buffer: str, data: bytes, raw_name: str, *, ret: str = "0x00000000", all_zero: bool = False) -> dict[str, object]:
    return {
        "seq": f"0x{seq:08x}",
        "cmd": cmd,
        "buffer": buffer,
        "in_len": "0x00000010",
        "out_len": f"0x{len(data):08x}",
        "ret": ret,
        "all_zero": all_zero,
        "sha256": hashlib.sha256(data).hexdigest(),
        "raw_path": f"/data/local/tmp/a90-acdb-tap/{raw_name}",
    }


def write_v2614_run(root: Path, *, zero_stream: bool = False) -> None:
    run = root / "run"
    acdbtap = run / "ownget-device-artifacts/acdbtap"
    ap_common = b"APC" * 64
    ap_stream = b"\x00" * 28 if zero_stream else b"STREAM_PAYLOAD_28_BYTES_OK!!"[:28]
    afe_common = b"AFE" * 80
    rows = [
        row(4, "0x00013265", "ind-ap-common", ap_common, "ap-common.bin"),
        row(8, "0x00013269", "ind-ap-stream", ap_stream, "ap-stream.bin", all_zero=zero_stream),
        row(11, "0x0001326f", "ind-afe-common", afe_common, "afe-common.bin"),
    ]
    for item, data in zip(rows, [ap_common, ap_stream, afe_common], strict=True):
        write_file(acdbtap / Path(str(item["raw_path"])).name, data)
    result = {
        "ok": True,
        "partial_success": True,
        "counts_toward_fails_twice": False,
        "rolled_back": True,
        "target_4916_success": False,
        "decision": "v2490-acdbtap-full-outbuf-set-no-4916-before-helper-exit-before-rollback-rollback-pass",
        "ownget_summary": {
            "acdbtap_rows": rows,
            "acdbtap_row_count": len(rows),
            "acdbtap_raw_file_count": len(rows),
        },
    }
    (run / "result.json").write_text(json.dumps(result), encoding="utf-8")


class AnalyzeAudioAcdbPerdeviceManifestV2615(unittest.TestCase):
    def test_capture_state_accepts_three_nonzero_indirect_payloads(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2615-test-"))
        write_v2614_run(root)

        state = v2615.v2614_capture_state(root / "run")

        self.assertTrue(state["ok"], state)
        self.assertEqual(len(state["entries"]), 3)
        self.assertEqual([entry["candidate_cal_type"] for entry in state["entries"]], [11, 15, 16])
        self.assertTrue(all(entry["raw"]["checks"]["not_all_zero"] for entry in state["entries"]))

    def test_manifest_keeps_native_replay_blocked_for_operator_mapping(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2615-test-"))
        write_v2614_run(root)
        write_file(root / "topology.bin", b"T" * 4916)

        payload = v2615.manifest(args(root))

        self.assertTrue(payload["ok"], payload)
        self.assertFalse(payload["native_replay_ready"])
        self.assertIn("operator", payload["native_replay_blocked_reason"])
        self.assertEqual(payload["candidate_sequence"][0]["candidate_cal_type"], 39)
        self.assertEqual(payload["candidate_sequence"][-1]["source"], "ind-afe-common")
        self.assertTrue((root / "manifest.json").exists())

    def test_zero_payload_is_rejected(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2615-test-"))
        write_v2614_run(root, zero_stream=True)
        write_file(root / "topology.bin", b"T" * 4916)

        payload = v2615.manifest(args(root))

        self.assertFalse(payload["ok"], payload)
        stream = [entry for entry in payload["capture"]["entries"] if entry["buffer"] == "ind-ap-stream"][0]
        self.assertFalse(stream["ok"])
        self.assertFalse(stream["raw"]["checks"]["not_all_zero"])

    def test_cli_writes_manifest_and_report(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2615-test-"))
        write_v2614_run(root)
        write_file(root / "topology.bin", b"T" * 4916)
        local_args = args(root, write_report=True)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/analyze_audio_acdb_perdevice_manifest_v2615.py",
                "--run-dir",
                str(local_args.run_dir),
                "--topology-payload",
                str(local_args.topology_payload),
                "--manifest-path",
                str(local_args.manifest_path),
                "--write-report",
                "--report-path",
                str(local_args.report_path),
            ],
            cwd=v2615.ROOT,
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
        self.assertIn("native_replay_ready: `False`", local_args.report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
