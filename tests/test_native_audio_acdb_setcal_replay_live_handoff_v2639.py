"""Tests for V2639 ACDB SET-cal replay live handoff."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2639 = load_revalidation("native_audio_acdb_setcal_replay_live_handoff_v2639")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_file(path: Path, data: bytes, remote: str, kind: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "kind": kind,
        "local": {
            "local_path_private": str(path),
            "exists": True,
            "ok": True,
            "nonzero": True,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha256_matches": True,
            "size_matches": True,
        },
        "remote_path": remote,
        "ok": True,
    }


def fake_deploy(root: Path, *, gate2: bool = False) -> Path:
    remote_dir = "/cache/a90-test-v2639"
    files = [fake_file(root / "helper", b"helper", f"{remote_dir}/helper", "helper")]
    files.append(fake_file(root / "topology", b"T" * 4916, f"{remote_dir}/00-core.bin", "topology"))
    argv = [f"{remote_dir}/helper", "--execute", "--basic-payload", f"39:0:{remote_dir}/00-core.bin"]
    for index, cal_type in enumerate([13, 9, 11, 12, 15, 23, 16, 21], start=1):
        arg = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(fake_file(root / f"arg{index}", bytes([index]) * 40, arg, "set_arg"))
        if cal_type in {11, 15, 16}:
            payload = f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
            files.append(fake_file(root / f"payload{index}", bytes([cal_type]) * 12, payload, "payload"))
            arg = f"{arg}:{payload}"
        argv.extend(["--exact-set", arg])
    argv.extend(["--hold-sec", "10"])
    path = root / "deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "operator_gate2_accepted": gate2,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "files": files,
    })
    return path


class NativeAudioAcdbSetcalReplayLiveHandoffV2639(unittest.TestCase):
    def test_dry_run_uses_v2638_contract_and_self_authorizes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)

        self.assertTrue(state["live_runner_implemented"])
        self.assertTrue(state["execution_contract_ok"])
        self.assertTrue(state["safe_to_run_native_replay"])
        self.assertEqual(state["replay_gate_blockers"], [])
        self.assertEqual(state["remote"]["final_set_index"], 8)

    def test_verify_live_gate_accepts_legacy_approval_flags_as_noops(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        manifest = fake_deploy(root, gate2=False)
        args = v2639.parse_args([
            "--run-live",
            "--v2636-manifest",
            str(manifest),
        ])
        deploy = v2639.load_deploy_manifest(manifest)
        state = v2639.dry_run_payload(args)

        v2639.verify_live_gate(args, deploy)
        self.assertTrue(state["safe_to_run_native_replay"])

    def test_report_records_blockers(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)
        report = root / "report.md"
        v2639.write_report(report, state)
        text = report.read_text(encoding="utf-8")

        self.assertIn("ACDB SET-cal replay live handoff", text)
        self.assertIn("self-authorized", text)
        self.assertNotIn("local_path_private", text)


if __name__ == "__main__":
    unittest.main()
