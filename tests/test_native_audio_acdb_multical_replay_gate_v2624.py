"""Tests for V2624 ACDB multi-cal replay gate."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2624 = load_revalidation("native_audio_acdb_multical_replay_gate_v2624")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def topology_file(root: Path, *, zero: bool = False) -> Path:
    path = root / "topology.bin"
    if zero:
        path.write_bytes(b"\0" * v2624.TOPOLOGY_LEN)
    else:
        data = bytearray((index % 251) + 1 for index in range(v2624.TOPOLOGY_LEN))
        path.write_bytes(data)
        v2624.TOPOLOGY_SHA256 = hashlib.sha256(data).hexdigest()
    return path


def v2622_manifest(root: Path) -> Path:
    candidates = []
    specs = [
        ("AUDPROC_COMMON_CANDIDATE", "0x00013265", "ind-ap-common", 18084, "a" * 64),
        ("AUDPROC_STREAM_CANDIDATE", "0x00013269", "ind-ap-stream", 28, "b" * 64),
        ("AFE_COMMON_CANDIDATE", "0x0001326f", "ind-afe-common", 1560, "c" * 64),
    ]
    for order, (category, cmd, buffer, size, digest) in enumerate(specs, 1):
        candidates.append({
            "order": order,
            "category": category,
            "cmd": cmd,
            "seq": f"0x{order:08x}",
            "buffer": buffer,
            "out_len": size,
            "raw_size": size,
            "sha256": digest,
            "nonzero": True,
            "hash_matches_event": True,
            "verified_for_gate2": True,
            "raw_path_private": f"workspace/private/runs/audio/fake/{buffer}.bin",
        })
    path = root / "v2622.json"
    write_json(path, {
        "ok": True,
        "payload_candidates": candidates,
        "vol_status": {
            "source_decision": "v2621-vol-isolated-vol-sweep-no-payload-rollback-pass",
            "classification": "v2621-vol-isolated-vol-sweep-no-payload",
            "vol_direct_get_exhausted_for_current_tuple": True,
            "vol_payload_count": 0,
            "vol_size_ret_values": [-19],
            "vol_data_ret_values": [-19],
        },
        "summary": {"vol_status_source_decision": "v2621-vol-isolated-vol-sweep-no-payload-rollback-pass"},
    })
    return path


class NativeAudioAcdbMulticalReplayGateV2624(unittest.TestCase):
    def test_default_gate_is_ready_for_operator_but_not_native_replay(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2624-"))
        manifest = v2624.build_gate_manifest(v2622_manifest(root), topology_file(root))

        self.assertTrue(manifest["ok"])
        self.assertFalse(manifest["gate2_accepted_for_manifest"])
        self.assertFalse(manifest["native_replay_ready"])
        self.assertFalse(manifest["safe_to_run_native_replay"])
        self.assertEqual(len(manifest["per_device_candidates"]), 3)
        self.assertIn("operator Gate-2", manifest["replay_blockers"][0])
        self.assertTrue(manifest["helper_gap"]["current_helper_single_topology_only"])

    def test_operator_flags_accept_manifest_but_still_do_not_run_replay(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2624-"))
        manifest = v2624.build_gate_manifest(
            v2622_manifest(root),
            topology_file(root),
            operator_gate2_accepted=True,
            operator_accept_vol_negative=True,
        )

        self.assertTrue(manifest["ok"])
        self.assertTrue(manifest["gate2_accepted_for_manifest"])
        self.assertFalse(manifest["native_replay_ready"])
        self.assertIn("current native replay helper is topology-only", "\n".join(manifest["replay_blockers"]))

    def test_zero_topology_payload_fails_validation(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2624-"))
        old_sha = v2624.TOPOLOGY_SHA256
        try:
            v2624.TOPOLOGY_SHA256 = hashlib.sha256(b"\0" * v2624.TOPOLOGY_LEN).hexdigest()
            manifest = v2624.build_gate_manifest(v2622_manifest(root), topology_file(root, zero=True))
        finally:
            v2624.TOPOLOGY_SHA256 = old_sha

        self.assertFalse(manifest["ok"])
        self.assertFalse(manifest["topology"]["ok"])
        self.assertIn("topology payload validation failed", manifest["replay_blockers"])

    def test_report_is_redacted_and_boundary_is_explicit(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2624-"))
        manifest = v2624.build_gate_manifest(v2622_manifest(root), topology_file(root))
        report = root / "report.md"
        private_manifest = root / "private-manifest.json"

        v2624.write_report(report, manifest, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("multi-cal replay gate", text)
        self.assertIn("not** a live replay approval", text)
        self.assertIn("current_helper_single_topology_only", text)
        self.assertNotIn("raw_path_private", text)
        self.assertNotIn("workspace/private/runs/audio/fake", text)


if __name__ == "__main__":
    unittest.main()
