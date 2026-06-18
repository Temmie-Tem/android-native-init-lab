"""Tests for V2638 ACDB SET-cal replay live runner plan."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2638 = load_revalidation("native_audio_acdb_setcal_replay_live_runner_plan_v2638")


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
            "nonzero": bool(data.strip(b"\0")),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha256_matches": True,
            "size_matches": True,
        },
        "remote_path": remote,
        "remote_mode": "0700" if kind == "helper" else "0600",
        "ok": True,
    }


def fake_deploy(root: Path) -> Path:
    remote_dir = "/cache/a90-test-v2638"
    files = [fake_file(root / "helper", b"helper", f"{remote_dir}/helper", "helper")]
    files.append(fake_file(root / "topology", b"T" * 4916, f"{remote_dir}/00-core.bin", "topology"))
    for index, cal_type in enumerate([13, 9, 11, 12, 15, 23, 16, 21], start=1):
        files.append(fake_file(root / f"arg{index}", bytes([index]) * 40, f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin", "set_arg"))
        if cal_type in {11, 15, 16}:
            files.append(fake_file(root / f"payload{index}", bytes([cal_type]) * 12, f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin", "payload"))
    argv = [f"{remote_dir}/helper", "--execute", "--basic-payload", f"39:0:{remote_dir}/00-core.bin"]
    for index, cal_type in enumerate([13, 9, 11, 12, 15, 23, 16, 21], start=1):
        spec = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        if cal_type in {11, 15, 16}:
            spec += f":{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
        argv.extend(["--exact-set", spec])
    argv.extend(["--hold-sec", "10"])
    path = root / "deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "operator_gate2_accepted": False,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "files": files,
    })
    return path


def fake_custom_deploy(root: Path) -> Path:
    remote_dir = "/cache/a90-test-v2677"
    files = [fake_file(root / "helper-custom", b"helper", f"{remote_dir}/helper", "helper")]
    files.append(fake_file(root / "topology-custom", b"T" * 4916, f"{remote_dir}/00-core.bin", "topology"))
    set_args = []
    argv = [f"{remote_dir}/helper", "--execute", "--basic-payload", f"39:0:{remote_dir}/00-core.bin"]
    for index, cal_type in enumerate([24, 14, 13, 9, 11, 12, 15, 23, 16, 21], start=1):
        arg = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(fake_file(root / f"custom-arg{index}", bytes([index]) * 40, arg, "set_arg"))
        payload = None
        if cal_type in {24, 14, 11, 15, 16}:
            payload = f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
            files.append(fake_file(root / f"custom-payload{index}", bytes([cal_type]) * 12, payload, "payload"))
        spec = arg if payload is None else f"{arg}:{payload}"
        argv.extend(["--exact-set", spec])
        set_args.append(
            {
                "sequence": index,
                "cal_type": cal_type,
                "role": f"CAL_{cal_type}",
                "dmabuf_expected": payload is not None,
                "arg_remote": arg,
                "payload_remote": payload,
                "ok": True,
            }
        )
    argv.extend(["--hold-sec", "10"])
    path = root / "custom-deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "operator_gate2_accepted": False,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "set_args": set_args,
        "files": files,
    })
    return path


def fake_core_derived_deploy(root: Path) -> Path:
    remote_dir = "/cache/a90-test-v2684"
    files = [fake_file(root / "helper-core", b"helper", f"{remote_dir}/helper", "helper")]
    argv = [f"{remote_dir}/helper", "--execute"]
    replay_entries = []

    for index, cal_type in enumerate([39, 10, 14]):
        remote = f"{remote_dir}/{index:02d}-basic-cal{cal_type}.bin"
        files.append(fake_file(root / f"basic-{cal_type}", bytes([cal_type & 0xff]) * 396, remote, "payload"))
        argv.extend(["--basic-payload", f"{cal_type}:0:{remote}"])
        replay_entries.append({"sequence": index, "kind": "basic-payload", "cal_type": cal_type, "ok": True})

    set_args = []
    for index, cal_type in enumerate([24, 13, 9, 11, 12, 15, 23, 16, 21], start=3):
        arg = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(fake_file(root / f"core-arg{index}", bytes([index]) * 40, arg, "set_arg"))
        payload = None
        if cal_type in {24, 11, 15, 16}:
            payload = f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
            files.append(fake_file(root / f"core-payload{index}", bytes([cal_type]) * 12, payload, "payload"))
        spec = arg if payload is None else f"{arg}:{payload}"
        argv.extend(["--exact-set", spec])
        set_args.append(
            {
                "sequence": index,
                "cal_type": cal_type,
                "role": f"CAL_{cal_type}",
                "dmabuf_expected": payload is not None,
                "arg_remote": arg,
                "payload_remote": payload,
                "ok": True,
            }
        )
        replay_entries.append({"sequence": index, "kind": "exact-set", "cal_type": cal_type, "ok": True})

    argv.extend(["--hold-sec", "10"])
    path = root / "core-derived-deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "operator_gate2_accepted": False,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "set_args": set_args,
        "replay_entries": replay_entries,
        "files": files,
    })
    return path


class NativeAudioAcdbSetcalReplayLiveRunnerPlanV2638(unittest.TestCase):
    def args(self, root: Path):
        return v2638.parse_args(["--v2636-manifest", str(fake_deploy(root))])

    def test_runner_plan_pins_exact_set_marker_and_self_authorizes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-"))
        plan = v2638.build_runner_plan(self.args(root))

        self.assertTrue(plan["ok"])
        self.assertTrue(plan["execution_contract_ok"])
        self.assertTrue(plan["safe_to_run_native_replay"])
        self.assertTrue(plan["native_replay_ready"])
        self.assertFalse(plan["manual_approval_required"])
        self.assertEqual(plan["remote"]["entry_count"], 9)
        self.assertEqual(plan["remote"]["final_set_index"], 8)
        self.assertEqual(plan["remote"]["payload_entry_indices"], [0, 3, 5, 7])
        self.assertIn("A90_ACDB_SETCAL_SET_OK index=8", plan["remote_scripts"]["start_and_wait_all_set"])
        self.assertEqual(
            sorted(plan["remote_script_paths"]),
            ["deallocate_check", "runtime_cleanup", "start_and_wait_all_set"],
        )
        self.assertTrue(plan["remote_script_paths"]["start_and_wait_all_set"].startswith("/cache/a90-runtime/bin/"))
        self.assertTrue(plan["remote_script_paths"]["start_and_wait_all_set"].endswith("/setcal-start-and-wait-all-set.sh"))
        self.assertEqual(plan["replay_gate_blockers"], [])

    def test_scripts_include_devnode_setup_hash_checks_and_reverse_dealloc_check(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-"))
        plan = v2638.build_runner_plan(self.args(root))
        start = plan["remote_scripts"]["start_and_wait_all_set"]
        cleanup = plan["remote_scripts"]["deallocate_check"]

        self.assertIn("sha256sum -c -", start)
        self.assertIn("/dev/msm_audio_cal", start)
        self.assertIn("/dev/ion", start)
        self.assertIn("A90_SETCAL_REPLAY_ALL_SET_OK", start)
        self.assertIn("setcal-replay.pid", start)
        self.assertIn("/cache/a90-runtime/bin/v2639-setcal-replay-scripts", plan["remote_scripts"]["runtime_cleanup"])
        self.assertIn("A90_SETCAL_REPLAY_WAIT_FOR_DONE timeout=25", cleanup)
        self.assertIn("A90_ACDB_SETCAL_REPLAY_DONE rc=0", cleanup)
        self.assertIn("A90_SETCAL_REPLAY_HELPER_STILL_RUNNING", cleanup)
        for index in [0, 3, 5, 7]:
            self.assertIn(f"A90_ACDB_SETCAL_DEALLOCATE_OK index={index}", cleanup)

    def test_report_redacts_remote_scripts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-"))
        plan = v2638.build_runner_plan(self.args(root))
        report = root / "report.md"
        private_manifest = root / "runner-plan.json"

        v2638.write_report(report, plan, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("ACDB SET-cal replay live runner plan", text)
        self.assertIn("final_set_index", text)
        self.assertNotIn("sha256sum -c -", text)
        self.assertNotIn("local_path_private", text)

    def test_runner_plan_accepts_custom_topology_overlay_manifest(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-custom-"))
        args = v2638.parse_args(["--v2636-manifest", str(fake_custom_deploy(root))])

        plan = v2638.build_runner_plan(args)

        self.assertTrue(plan["ok"])
        self.assertTrue(plan["execution_contract_ok"])
        self.assertEqual(plan["remote"]["entry_count"], 11)
        self.assertEqual(plan["remote"]["file_count"], 17)
        self.assertEqual(plan["remote"]["final_set_index"], 10)
        self.assertEqual(plan["remote"]["payload_entry_indices"], [0, 1, 2, 5, 7, 9])
        self.assertIn("A90_ACDB_SETCAL_SET_OK index=10", plan["remote_scripts"]["start_and_wait_all_set"])
        self.assertEqual(plan["replay_gate_blockers"], [])

    def test_runner_plan_accepts_replay_entries_for_multi_basic_payload_manifest(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-core-"))
        args = v2638.parse_args(["--v2636-manifest", str(fake_core_derived_deploy(root))])

        plan = v2638.build_runner_plan(args)

        self.assertTrue(plan["ok"])
        self.assertTrue(plan["execution_contract_ok"])
        self.assertEqual(plan["remote"]["entry_count"], 12)
        self.assertEqual(plan["remote"]["declared_entry_count"], 12)
        self.assertEqual(plan["remote"]["declared_entry_source"], "replay_entries")
        self.assertEqual(plan["remote"]["file_count"], 17)
        self.assertEqual(plan["remote"]["final_set_index"], 11)
        self.assertEqual(plan["remote"]["payload_entry_indices"], [0, 1, 2, 3, 6, 8, 10])
        self.assertIn("A90_ACDB_SETCAL_SET_OK index=11", plan["remote_scripts"]["start_and_wait_all_set"])
        self.assertEqual(plan["replay_gate_blockers"], [])


if __name__ == "__main__":
    unittest.main()
