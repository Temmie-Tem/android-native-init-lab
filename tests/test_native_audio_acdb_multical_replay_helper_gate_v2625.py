"""Tests for the V2625 ACDB multi-cal replay helper gate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2625 = load_revalidation("native_audio_acdb_multical_replay_helper_gate_v2625")


def write_fixture_manifest(root: Path) -> Path:
    manifest = root / "v2624.json"
    payload = {
        "run_id": "V2624",
        "build_tag": "v2624-audio-acdb-multical-replay-gate",
        "ok": True,
        "operator_gate2_accepted": False,
        "operator_accept_vol_negative": False,
        "gate2_accepted_for_manifest": False,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": ["operator Gate-2 has not accepted the per-device mapping"],
        "topology": {
            "order": 0,
            "kind": "topology",
            "category": "CORE_CUSTOM_TOPOLOGIES",
            "cal_type": 39,
            "buffer_number": 0,
            "gate2_status": "operator-verified",
            "raw": {
                "path_private": "workspace/private/inputs/audio/acdb_replay/payloads/core.bin",
                "size": 4916,
                "sha256": "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89",
            },
        },
        "per_device_candidates": [
            {
                "order": 1,
                "kind": "per_device_candidate",
                "category": "AUDPROC_COMMON_CANDIDATE",
                "proposed_cal_type": 11,
                "gate2_status": "pending-operator-mapping",
                "raw": {
                    "path_private": "workspace/private/runs/audio/x/audproc-common.bin",
                    "size": 8,
                    "sha256": "a" * 64,
                },
            },
            {
                "order": 2,
                "kind": "per_device_candidate",
                "category": "AUDPROC_STREAM_CANDIDATE",
                "proposed_cal_type": 15,
                "gate2_status": "pending-operator-mapping",
                "raw": {
                    "path_private": "workspace/private/runs/audio/x/asm.bin",
                    "size": 32,
                    "sha256": "b" * 64,
                },
            },
            {
                "order": 3,
                "kind": "per_device_candidate",
                "category": "AFE_COMMON_CANDIDATE",
                "proposed_cal_type": 16,
                "gate2_status": "pending-operator-mapping",
                "raw": {
                    "path_private": "workspace/private/runs/audio/x/afe.bin",
                    "size": 1560,
                    "sha256": "c" * 64,
                },
            },
        ],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2625-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "build_helper": False,
        "write_report": False,
        "v2624_manifest": write_fixture_manifest(root),
        "hold_sec": 10,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "report_path": root / "report.md",
        "cc": "aarch64-linux-gnu-gcc",
        "strip": "aarch64-linux-gnu-strip",
        "no_strip": True,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbMulticalReplayHelperGateV2625(unittest.TestCase):
    def test_helper_source_contains_multical_contract_tokens(self) -> None:
        state = v2625.helper_source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["ready"], state)
        self.assertTrue(state["required_tokens"]["entry_parser"])
        self.assertTrue(state["required_tokens"]["reverse_cleanup"])
        self.assertFalse(any(state["prohibited_tokens"].values()))

    def test_v2624_manifest_is_redacted_but_keeps_private_future_args(self) -> None:
        state = v2625.v2624_state(args().v2624_manifest)

        self.assertTrue(state["ready"], state)
        self.assertEqual(state["private_entry_count"], 4)
        self.assertFalse(state["gate2_accepted_for_manifest"])
        self.assertFalse(state["safe_to_run_native_replay"])
        self.assertTrue(all("workspace/private/" not in json.dumps(entry) for entry in state["redacted_entries"]))
        self.assertTrue(any("workspace/private/" in item for item in state["future_private_entry_args"]))

    def test_manifest_is_host_only_and_keeps_live_replay_blocked(self) -> None:
        payload = v2625.make_manifest(args())

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2625-acdb-multical-replay-helper-gate-host-only")
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["native_calibration_ioctls_run"])
        self.assertFalse(payload["future_live_plan"]["safe_to_run_now"])
        self.assertTrue(payload["future_live_plan"]["blocked_until_gate2_acceptance"])
        self.assertTrue(payload["safety"]["future_live_requires_operator_gate2"])

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "aarch64-linux-gnu-gcc unavailable")
    def test_build_helper_compiles_execute_enabled_binary(self) -> None:
        payload = v2625.make_manifest(args(build_helper=True))
        build = payload["build"]

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(build["built"])
        self.assertTrue(build["compile_defines"]["A90_ENABLE_NATIVE_MULTICAL_EXECUTE"])
        self.assertTrue(build["tool"]["execute_compiled_in"])
        self.assertIn("ARM aarch64", build["tool"]["file"])
        self.assertTrue(build["static_probe"]["strings_has_start_marker"])
        self.assertTrue(build["static_probe"]["strings_has_set_marker"])
        self.assertTrue(build["static_probe"]["strings_has_reverse_dealloc_marker"])

    def test_cli_writes_manifest_and_report(self) -> None:
        local_args = args()
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_helper_gate_v2625.py",
                "--dry-run",
                "--write-report",
                "--v2624-manifest",
                str(local_args.v2624_manifest),
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
                "--report-path",
                str(local_args.report_path),
                "--no-strip",
            ],
            cwd=v2625.ROOT,
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
        self.assertIn("ACDB multi-cal replay helper gate", local_args.report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
