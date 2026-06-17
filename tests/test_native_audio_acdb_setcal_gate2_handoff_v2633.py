"""Tests for the V2633 SET-calibration Gate-2 handoff package."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2633 = load_revalidation("native_audio_acdb_setcal_gate2_handoff_v2633")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def event_for(
    artifact_dir: Path,
    sequence: int,
    cal_type: int,
    data_size: int,
    cal_size: int,
    mem_handle: int,
    arg_bytes: bytes,
    dmabuf_bytes: bytes | None = None,
) -> dict:
    arg_name = f"setcal-arg-s{sequence:04d}-cal{cal_type:08x}.bin"
    arg_path = artifact_dir / arg_name
    arg_path.write_bytes(arg_bytes)
    dmabuf_status = "header-only"
    dmabuf_path = ""
    dmabuf_len = 0
    dmabuf_sha = "0" * 64
    dmabuf_all_zero = False
    if dmabuf_bytes is not None:
        dmabuf_name = f"setcal-dmabuf-s{sequence:04d}-cal{cal_type:08x}.bin"
        dmabuf_local = artifact_dir / dmabuf_name
        dmabuf_local.write_bytes(dmabuf_bytes)
        dmabuf_status = "dumped"
        dmabuf_path = f"/data/local/tmp/a90-acdb-ownget/{dmabuf_name}"
        dmabuf_len = len(dmabuf_bytes)
        dmabuf_sha = v2633.sha256_file(dmabuf_local)
        dmabuf_all_zero = not any(dmabuf_bytes)
    elif cal_size > 0:
        dmabuf_status = "no-mem-handle"
        dmabuf_len = cal_size
    return {
        "event": "setcal_capture",
        "sequence": sequence,
        "header_valid": True,
        "data_size": data_size,
        "version": 0,
        "cal_type": cal_type,
        "cal_type_size": max(0, data_size - 16),
        "cal_hdr_version": 0,
        "buffer_number": 0,
        "cal_size": cal_size,
        "mem_handle": mem_handle,
        "set_arg": {
            "path": f"/data/local/tmp/a90-acdb-ownget/{arg_name}",
            "len": len(arg_bytes),
            "dump_rc": 0,
            "sha256": v2633.sha256_file(arg_path),
            "all_zero": not any(arg_bytes),
        },
        "dmabuf": {
            "status": dmabuf_status,
            "path": dmabuf_path,
            "len": dmabuf_len,
            "dump_rc": 0 if dmabuf_bytes is not None else -1,
            "mmap_errno": 0,
            "sha256": dmabuf_sha,
            "all_zero": dmabuf_all_zero,
        },
    }


def fake_previous_manifest(root: Path, payloads: dict[int, bytes]) -> Path:
    manifest_path = root / "previous-gate2.json"
    candidates = []
    category_by_cal = {
        11: "AUDPROC_COMMON_CANDIDATE",
        15: "AUDPROC_STREAM_CANDIDATE",
        16: "AFE_COMMON_CANDIDATE",
    }
    for cal_type, payload in payloads.items():
        raw_path = root / f"previous-cal{cal_type}.bin"
        raw_path.write_bytes(payload)
        candidates.append({
            "category": category_by_cal[cal_type],
            "out_len": len(payload),
            "sha256": v2633.sha256_file(raw_path),
            "raw_path_private": str(raw_path),
        })
    write_json(manifest_path, {"ok": True, "payload_candidates": candidates})
    return manifest_path


def fake_v2632_run() -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="a90-v2633-run-"))
    run_dir = root / "v2632-acdb-setcal-capture-test"
    artifact_dir = run_dir / "ownget-device-artifacts"
    artifact_dir.mkdir(parents=True)
    payloads = {
        11: b"\x1f\x03\x01\x00" + b"A" * 18080,
        15: b"\xfe\x0b\x01\x00" + b"B" * 24,
        16: b"\x5f\x02\x01\x00" + b"C" * 1556,
    }
    previous_payloads = {
        11: b"\xa4\x46\x00\x00" + b"A" * 18080,
        15: b"\x1c\x00\x00\x00" + b"B" * 24,
        16: b"\x18\x06\x00\x00" + b"C" * 1556,
    }
    rows = [
        event_for(artifact_dir, 1, 13, 40, 0, -1, b"\x0d" * 40),
        event_for(artifact_dir, 2, 9, 52, 0, -1, b"\x09" * 52),
        event_for(artifact_dir, 3, 11, 48, len(payloads[11]), 15, b"\x0b" * 48, payloads[11]),
        event_for(artifact_dir, 4, 12, 48, 0, 17, b"\x0c" * 48),
        event_for(artifact_dir, 5, 15, 36, len(payloads[15]), 20, b"\x0f" * 36, payloads[15]),
        event_for(artifact_dir, 6, 23, 48, 0, -1, b"\x17" * 48),
        event_for(artifact_dir, 7, 16, 44, len(payloads[16]), 21, b"\x10" * 44, payloads[16]),
        event_for(artifact_dir, 8, 21, 72, 28, -1, b"\x15" * 72),
    ]
    write_jsonl(artifact_dir / "setcal-events.jsonl", rows)
    write_json(
        run_dir / "v2631-result.json",
        {
            "decision": "v2631-setcal-manifest-captured-rollback-pass",
            "ok": True,
            "rolled_back": True,
            "operator_valuable": True,
            "counts_toward_fails_twice": False,
            "setcal_summary": {
                "classification": "v2631-setcal-manifest-captured",
                "real_audio_set_pass_through_count": 0,
                "fake_audio_set_count": 8,
            },
        },
    )
    return run_dir, fake_previous_manifest(root, previous_payloads)


class NativeAudioAcdbSetcalGate2HandoffV2633(unittest.TestCase):
    def test_build_manifest_verifies_set_args_payloads_and_redacts_private_paths(self) -> None:
        run_dir, previous_manifest = fake_v2632_run()

        manifest = v2633.build_manifest(run_dir, previous_manifest)

        self.assertTrue(manifest["ok"])
        self.assertFalse(manifest["native_replay_ready"])
        self.assertEqual(manifest["summary"]["ordered_cal_types"], v2633.EXPECTED_ORDER)
        self.assertEqual(manifest["summary"]["record_count"], 8)
        self.assertEqual(manifest["summary"]["verified_record_count"], 8)
        self.assertEqual(manifest["summary"]["previous_payload_tail_match_count"], 3)
        self.assertIn("raw_path_private", manifest["records"][0]["arg"])
        self.assertNotIn("raw_path_private", manifest["records_redacted"][0]["arg"])

    def test_zero_set_arg_breaks_gate2_verification(self) -> None:
        run_dir, previous_manifest = fake_v2632_run()
        first_arg = next((run_dir / "ownget-device-artifacts").glob("setcal-arg-s0001-*.bin"))
        first_arg.write_bytes(b"\x00" * first_arg.stat().st_size)
        rows = [json.loads(line) for line in (run_dir / "ownget-device-artifacts/setcal-events.jsonl").read_text().splitlines()]
        rows[0]["set_arg"]["sha256"] = v2633.sha256_file(first_arg)
        rows[0]["set_arg"]["all_zero"] = True
        write_jsonl(run_dir / "ownget-device-artifacts/setcal-events.jsonl", rows)

        manifest = v2633.build_manifest(run_dir, previous_manifest)

        self.assertFalse(manifest["ok"])
        self.assertEqual(manifest["summary"]["verified_record_count"], 7)
        self.assertFalse(manifest["records"][0]["arg"]["nonzero"])

    def test_write_report_mentions_gate_boundary(self) -> None:
        run_dir, previous_manifest = fake_v2632_run()
        manifest = v2633.build_manifest(run_dir, previous_manifest)
        report = run_dir / "report.md"
        private_manifest = run_dir / "private.json"

        v2633.write_report(report, manifest, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("Gate-2", text)
        self.assertIn("not a native replay manifest", text)
        self.assertIn("AFE_TOPOLOGY_HEADER", text)


if __name__ == "__main__":
    unittest.main()
