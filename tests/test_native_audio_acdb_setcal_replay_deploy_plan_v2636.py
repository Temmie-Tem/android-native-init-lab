"""Tests for V2636 ACDB SET-cal replay deployment plan."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2636 = load_revalidation("native_audio_acdb_setcal_replay_deploy_plan_v2636")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_file(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path_private": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def fake_record(root: Path, sequence: int, cal_type: int, payload: bytes | None = None) -> dict:
    arg = write_file(root / f"arg-{sequence}-{cal_type}.bin", bytes([cal_type & 0xFF]) * 40)
    dmabuf = write_file(root / f"payload-{sequence}-{cal_type}.bin", payload) if payload is not None else {}
    return {
        "sequence": sequence,
        "cal_type": cal_type,
        "role": f"CAL_{cal_type}",
        "dmabuf_expected": payload is not None,
        "arg": arg,
        "dmabuf": dmabuf,
    }


def fake_manifests(root: Path) -> Path:
    helper = write_file(root / "helper", b"helper-binary")
    topology = write_file(root / "topology.bin", b"T" * 4916)
    records = [
        fake_record(root, 1, 13),
        fake_record(root, 2, 9),
        fake_record(root, 3, 11, b"A" * 12),
        fake_record(root, 4, 12),
        fake_record(root, 5, 15, b"B" * 8),
        fake_record(root, 6, 23),
        fake_record(root, 7, 16, b"C" * 16),
        fake_record(root, 8, 21),
    ]
    v2634 = root / "v2634.json"
    write_json(v2634, {
        "ok": True,
        "operator_gate2_accepted": False,
        "topology": topology,
        "set_records": records,
    })
    v2635 = root / "v2635.json"
    write_json(v2635, {
        "ok": True,
        "v2634_manifest": {
            "path": str(v2634),
            "operator_gate2_accepted": False,
        },
        "build": {
            "tool": {
                "path": helper["path_private"],
                "size": helper["size"],
                "sha256": helper["sha256"],
            },
        },
    })
    return v2635


class NativeAudioAcdbSetcalReplayDeployPlanV2636(unittest.TestCase):
    def test_build_deploy_plan_verifies_inputs_and_remote_argv(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2636-"))
        manifest = v2636.build_deploy_plan(fake_manifests(root), remote_dir="/cache/test-v2636", hold_sec=7)

        self.assertTrue(manifest["ok"])
        self.assertTrue(manifest["all_inputs_ok"])
        self.assertFalse(manifest["safe_to_run_native_replay"])
        self.assertEqual(manifest["summary"]["file_count"], 13)
        self.assertEqual(manifest["summary"]["set_arg_count"], 8)
        self.assertEqual(manifest["summary"]["payload_file_count"], 3)
        self.assertEqual(manifest["remote_argv"][0], "/cache/test-v2636/a90_acdb_setcal_replay_execute_v2635")
        self.assertIn("--basic-payload", manifest["remote_argv"])
        self.assertEqual(manifest["remote_argv"].count("--exact-set"), 8)
        self.assertEqual(manifest["remote_argv"][-2:], ["--hold-sec", "7"])

    def test_zero_input_breaks_gate(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2636-"))
        v2635 = fake_manifests(root)
        v2634 = Path(json.loads(v2635.read_text())["v2634_manifest"]["path"])
        loaded = json.loads(v2634.read_text())
        payload_path = Path(loaded["set_records"][2]["dmabuf"]["path_private"])
        payload_path.write_bytes(b"\0" * payload_path.stat().st_size)
        loaded["set_records"][2]["dmabuf"]["sha256"] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        write_json(v2634, loaded)

        manifest = v2636.build_deploy_plan(v2635)

        self.assertFalse(manifest["ok"])
        self.assertIn("one or more deployment inputs failed", "\n".join(manifest["replay_blockers"]))

    def test_report_redacts_local_private_paths(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2636-"))
        manifest = v2636.build_deploy_plan(fake_manifests(root), remote_dir="/cache/test-v2636")
        report = root / "report.md"
        private_manifest = root / "deploy.json"

        v2636.write_report(report, manifest, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("SET-cal replay deployment plan", text)
        self.assertIn("/cache/test-v2636", text)
        self.assertIn("not a live replay approval", text)
        self.assertNotIn("local_path_private", text)
        self.assertNotIn("arg-1-13.bin", text)
        self.assertNotIn("payload-3-11.bin", text)


if __name__ == "__main__":
    unittest.main()
