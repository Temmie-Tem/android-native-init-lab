"""Tests for V2634 ACDB SET-cal replay gate."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2634 = load_revalidation("native_audio_acdb_setcal_replay_gate_v2634")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def payload_file(root: Path, name: str, data: bytes) -> dict:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "exists": True,
        "hash_matches_event": True,
        "nonzero": any(data),
        "raw_path_private": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "size_matches_event": True,
        "verified": any(data),
    }


def record(root: Path, sequence: int, cal_type: int, data_size: int, cal_size: int, mem_handle: int, role: str, payload: bytes | None = None) -> dict:
    arg = payload_file(root, f"arg-{sequence}-{cal_type}.bin", bytes([cal_type & 0xFF]) * data_size)
    dmabuf_expected = payload is not None
    dmabuf = (
        payload_file(root, f"dmabuf-{sequence}-{cal_type}.bin", payload)
        if payload is not None
        else {
            "exists": False,
            "hash_matches_event": False,
            "nonzero": False,
            "raw_path_private": None,
            "sha256": None,
            "size": None,
            "size_matches_event": False,
            "verified": False,
        }
    )
    return {
        "arg": arg,
        "cal_size": cal_size,
        "cal_type": cal_type,
        "cal_type_size": max(0, data_size - 16),
        "data_size": data_size,
        "dmabuf": dmabuf,
        "dmabuf_expected": dmabuf_expected,
        "dmabuf_status": "dumped" if dmabuf_expected else "header-only",
        "header_valid": True,
        "mem_handle": mem_handle,
        "role": role,
        "sequence": sequence,
        "verified_for_gate2": True,
    }


def fake_v2633_manifest(root: Path) -> Path:
    records = [
        record(root, 1, 13, 40, 0, -1, "APP_META_HEADER"),
        record(root, 2, 9, 52, 0, -1, "AFE_TOPOLOGY_HEADER"),
        record(root, 3, 11, 48, 18084, 15, "AUDPROC_COMMON_PAYLOAD", b"A" * 18084),
        record(root, 4, 12, 48, 0, 17, "VOL_HEADER_NO_PAYLOAD"),
        record(root, 5, 15, 36, 28, 20, "ASM_STREAM_PAYLOAD", b"B" * 28),
        record(root, 6, 23, 48, 0, -1, "AFE_TOPOLOGY_ID_HEADER"),
        record(root, 7, 16, 44, 1560, 21, "AFE_COMMON_PAYLOAD", b"C" * 1560),
        record(root, 8, 21, 72, 28, -1, "SPEAKER_VI_HEADER"),
    ]
    path = root / "v2633-manifest.json"
    write_json(path, {
        "ok": True,
        "source_decision": "v2631-setcal-manifest-captured-rollback-pass",
        "source_rolled_back": True,
        "records": records,
    })
    return path


def topology(root: Path, *, zero: bool = False) -> Path:
    path = root / "topology.bin"
    data = (b"\0" if zero else b"T") * v2634.TOPOLOGY_LEN
    path.write_bytes(data)
    v2634.TOPOLOGY_SHA256 = hashlib.sha256(data).hexdigest()
    return path


class NativeAudioAcdbSetcalReplayGateV2634(unittest.TestCase):
    def test_default_manifest_is_input_ready_but_replay_blocked(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2634-"))
        manifest = v2634.build_manifest(fake_v2633_manifest(root), topology(root))

        self.assertTrue(manifest["ok"])
        self.assertTrue(manifest["inputs_ok"])
        self.assertFalse(manifest["native_replay_ready"])
        self.assertFalse(manifest["safe_to_run_native_replay"])
        self.assertEqual(manifest["captured_set_order"], v2634.EXPECTED_SET_ORDER)
        self.assertEqual(manifest["summary"]["validated_record_count"], 8)
        self.assertIn("operator Gate-2", manifest["replay_blockers"][0])
        self.assertIn("captured SET arg", "\n".join(manifest["helper_gap"]["required_future_delta"]))

    def test_payload_zero_breaks_input_gate(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2634-"))
        manifest_path = fake_v2633_manifest(root)
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload_path = Path(loaded["records"][2]["dmabuf"]["raw_path_private"])
        payload_path.write_bytes(b"\0" * payload_path.stat().st_size)
        loaded["records"][2]["dmabuf"]["sha256"] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        loaded["records"][2]["dmabuf"]["nonzero"] = False
        write_json(manifest_path, loaded)

        manifest = v2634.build_manifest(manifest_path, topology(root))

        self.assertFalse(manifest["ok"])
        self.assertFalse(manifest["set_records"][2]["dmabuf"]["nonzero"])
        self.assertIn("one or more SET records failed", "\n".join(manifest["replay_blockers"]))

    def test_report_redacts_private_paths_and_states_boundary(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2634-"))
        manifest = v2634.build_manifest(fake_v2633_manifest(root), topology(root))
        report = root / "report.md"
        private_manifest = root / "private.json"

        v2634.write_report(report, manifest, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("SET-cal replay gate", text)
        self.assertIn("not** a live replay approval", text)
        self.assertIn("current V2625 native helper", text)
        self.assertNotIn("raw_path_private", text)
        self.assertNotIn("arg-1-13.bin", text)
        self.assertNotIn("dmabuf-3-11.bin", text)


if __name__ == "__main__":
    unittest.main()
