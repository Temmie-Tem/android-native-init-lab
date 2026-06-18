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


class NativeAudioAcdbSetcalReplayLiveRunnerPlanV2638(unittest.TestCase):
    def args(self, root: Path):
        return v2638.parse_args(["--v2636-manifest", str(fake_deploy(root))])

    def test_runner_plan_pins_exact_set_marker_and_gate_blockers(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-"))
        plan = v2638.build_runner_plan(self.args(root))

        self.assertTrue(plan["ok"])
        self.assertTrue(plan["execution_contract_ok"])
        self.assertFalse(plan["safe_to_run_native_replay"])
        self.assertEqual(plan["remote"]["entry_count"], 9)
        self.assertEqual(plan["remote"]["final_set_index"], 8)
        self.assertEqual(plan["remote"]["payload_entry_indices"], [0, 3, 5, 7])
        self.assertIn("A90_ACDB_SETCAL_SET_OK index=8", plan["remote_scripts"]["start_and_wait_all_set"])
        self.assertIn("operator Gate-2 acceptance", "\n".join(plan["replay_gate_blockers"]))

    def test_scripts_include_devnode_setup_hash_checks_and_reverse_dealloc_check(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2638-"))
        plan = v2638.build_runner_plan(self.args(root))
        start = plan["remote_scripts"]["start_and_wait_all_set"]
        cleanup = plan["remote_scripts"]["deallocate_check"]

        self.assertIn("sha256sum -c -", start)
        self.assertIn("/dev/msm_audio_cal", start)
        self.assertIn("/dev/ion", start)
        self.assertIn("A90_SETCAL_REPLAY_ALL_SET_OK", start)
        self.assertIn("A90_ACDB_SETCAL_REPLAY_DONE rc=0", cleanup)
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


if __name__ == "__main__":
    unittest.main()
