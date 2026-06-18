"""Tests for V2677 ACDB custom-topology replay deployment plan."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2677 = load_revalidation("native_audio_acdb_custom_topology_replay_deploy_plan_v2677")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_file(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "local_path_private": str(path),
        "exists": True,
        "ok": True,
        "nonzero": bool(data.strip(b"\0")),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha256_matches": True,
        "size_matches": True,
        "private_only": True,
    }


def deploy_file(path: Path, data: bytes, remote: str, kind: str) -> dict:
    return {
        "kind": kind,
        "local": write_file(path, data),
        "remote_path": remote,
        "remote_mode": "0700" if kind == "helper" else "0600",
        "ok": True,
    }


def fake_v2636(root: Path) -> Path:
    remote_dir = "/cache/old-v2636"
    files = [
        deploy_file(root / "helper", b"helper", f"{remote_dir}/helper", "helper"),
        deploy_file(root / "topology.bin", b"T" * 4916, f"{remote_dir}/00-core.bin", "topology"),
    ]
    set_args = []
    for index, cal_type in enumerate([13, 9, 11, 12, 15, 23, 16, 21], start=1):
        arg_remote = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(deploy_file(root / f"arg-{index}-{cal_type}.bin", bytes([index]) * 40, arg_remote, "set_arg"))
        payload_remote = None
        if cal_type in {11, 15, 16}:
            payload_remote = f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
            files.append(deploy_file(root / f"payload-{index}-{cal_type}.bin", bytes([cal_type]) * 12, payload_remote, "payload"))
        set_args.append(
            {
                "sequence": index,
                "cal_type": cal_type,
                "role": f"LEGACY_{cal_type}",
                "dmabuf_expected": payload_remote is not None,
                "arg_remote": arg_remote,
                "payload_remote": payload_remote,
                "ok": True,
            }
        )
    argv = [f"{remote_dir}/helper", "--execute", "--basic-payload", f"39:0:{remote_dir}/00-core.bin"]
    for item in set_args:
        spec = item["arg_remote"] if item["payload_remote"] is None else f"{item['arg_remote']}:{item['payload_remote']}"
        argv.extend(["--exact-set", spec])
    argv.extend(["--hold-sec", "10"])
    path = root / "v2636.json"
    write_json(
        path,
        {
            "ok": True,
            "all_inputs_ok": True,
            "operator_gate2_accepted": True,
            "remote_dir": remote_dir,
            "hold_sec": 10,
            "files": files,
            "set_args": set_args,
            "remote_argv": argv,
        },
    )
    return path


def fake_v2675_run(root: Path) -> Path:
    run = root / "v2675-run"
    artifacts = run / "ownget-device-artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    events = []
    for sequence, (cal_type, payload_size) in enumerate([(24, 1180), (14, 2356)], start=1):
        arg_data = bytes([cal_type]) * 32
        payload_data = bytes([cal_type + 1]) * payload_size
        arg_name = f"setcal-arg-p00000001-s{sequence:08x}-cal{cal_type:08x}-len00000020.bin"
        payload_name = f"setcal-dmabuf-p00000001-s{sequence:08x}-cal{cal_type:08x}-len{payload_size:08x}.bin"
        (artifacts / arg_name).write_bytes(arg_data)
        (artifacts / payload_name).write_bytes(payload_data)
        events.append(
            {
                "event": "setcal_capture",
                "sequence": sequence,
                "cal_type": cal_type,
                "request": "0xc00461cb",
                "data_size": 32,
                "cal_size": payload_size,
                "mem_handle": 30 + sequence,
                "set_arg": {
                    "path": f"/data/local/tmp/a90-acdb-ownget/{arg_name}",
                    "len": 32,
                    "sha256": hashlib.sha256(arg_data).hexdigest(),
                },
                "dmabuf": {
                    "path": f"/data/local/tmp/a90-acdb-ownget/{payload_name}",
                    "len": payload_size,
                    "sha256": hashlib.sha256(payload_data).hexdigest(),
                    "all_zero": False,
                },
            }
        )
    (artifacts / "setcal-events.jsonl").write_text("\n".join(json.dumps(item, sort_keys=True) for item in events) + "\n", encoding="utf-8")
    return run


def fake_helper_manifest(root: Path) -> Path:
    helper = root / "new-helper"
    helper.write_bytes(b"new-helper-cap-16")
    helper.chmod(0o700)
    manifest = root / "helper-manifest.json"
    write_json(
        manifest,
        {
            "ok": True,
            "build": {
                "tool": {
                    "path": str(helper),
                    "size": helper.stat().st_size,
                    "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                }
            },
        },
    )
    return manifest


class NativeAudioAcdbCustomTopologyReplayDeployPlanV2677(unittest.TestCase):
    def test_build_manifest_prepends_custom_topologies_and_keeps_legacy_order(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2677-"))
        manifest = v2677.build_deploy_plan(fake_v2636(root), fake_v2675_run(root), remote_dir="/cache/test-v2677")

        self.assertTrue(manifest["ok"])
        self.assertTrue(manifest["all_inputs_ok"])
        self.assertEqual(manifest["custom_topology_overlay_cal_types"], [24, 14])
        self.assertEqual([item["cal_type"] for item in manifest["set_args"]], [24, 14, 13, 9, 11, 12, 15, 23, 16, 21])
        self.assertEqual(manifest["summary"]["file_count"], 17)
        self.assertEqual(manifest["summary"]["set_arg_count"], 10)
        self.assertEqual(manifest["summary"]["payload_file_count"], 5)
        self.assertEqual(manifest["summary"]["replay_entry_count"], 11)
        self.assertEqual(manifest["summary"]["final_set_index"], 10)
        self.assertEqual(manifest["remote_argv"].count("--exact-set"), 10)
        self.assertNotIn("cal0000000a", " ".join(manifest["remote_argv"]))

    def test_missing_custom_event_blocks_manifest(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2677-"))
        run = fake_v2675_run(root)
        events = run / "ownget-device-artifacts/setcal-events.jsonl"
        lines = [line for line in events.read_text(encoding="utf-8").splitlines() if '"cal_type": 14' not in line]
        events.write_text("\n".join(lines) + "\n", encoding="utf-8")

        manifest = v2677.build_deploy_plan(fake_v2636(root), run, remote_dir="/cache/test-v2677")

        self.assertFalse(manifest["ok"])
        self.assertFalse(manifest["all_inputs_ok"])
        self.assertIn("failed local size/hash/nonzero", "\n".join(manifest["replay_blockers"]))

    def test_helper_manifest_override_replaces_source_helper(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2677-"))
        helper_manifest = fake_helper_manifest(root)

        manifest = v2677.build_deploy_plan(
            fake_v2636(root),
            fake_v2675_run(root),
            remote_dir="/cache/test-v2677",
            helper_manifest_path=helper_manifest,
        )

        helper = manifest["files"][0]
        self.assertTrue(manifest["ok"])
        self.assertEqual(manifest["source_helper_manifest"], str(helper_manifest))
        self.assertEqual(helper["kind"], "helper")
        self.assertEqual(helper["local"]["sha256"], hashlib.sha256((root / "new-helper").read_bytes()).hexdigest())
        self.assertEqual(helper["remote_path"], "/cache/test-v2677/a90_acdb_setcal_replay_execute_v2635")

    def test_report_redacts_private_paths_and_documents_cal10_policy(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2677-"))
        manifest = v2677.build_deploy_plan(fake_v2636(root), fake_v2675_run(root), remote_dir="/cache/test-v2677")
        report = root / "report.md"
        private_manifest = root / "deploy-plan.json"

        v2677.write_report(report, manifest, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("custom-topology replay deploy plan", text)
        self.assertIn("cal_type_10_policy", text)
        self.assertIn("24", text)
        self.assertIn("14", text)
        self.assertNotIn("local_path_private", text)
        self.assertNotIn("v2675-run/ownget-device-artifacts", text)


if __name__ == "__main__":
    unittest.main()
