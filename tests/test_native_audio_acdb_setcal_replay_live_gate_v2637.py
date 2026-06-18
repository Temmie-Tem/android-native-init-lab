"""Tests for V2637 ACDB SET-cal replay live gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2637 = load_revalidation("native_audio_acdb_setcal_replay_live_gate_v2637")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_deploy_manifest(root: Path, *, gate2: bool = False, ok: bool = True) -> Path:
    path = root / "deploy-plan.json"
    write_json(
        path,
        {
            "ok": ok,
            "all_inputs_ok": ok,
            "operator_gate2_accepted": gate2,
            "remote_dir": "/cache/a90-acdb-setcal-replay-v2636",
            "remote_argv": [
                "/cache/a90-acdb-setcal-replay-v2636/a90_acdb_setcal_replay_execute_v2635",
                "--execute",
                "--basic-payload",
                "39:0:/cache/a90-acdb-setcal-replay-v2636/00-core_custom_topologies.bin",
            ],
            "remote_preflight": {
                "expected_files": 13,
                "expected_args": 22,
            },
            "summary": {
                "file_count": 13,
                "remote_arg_count": 22,
            },
            "replay_blockers": [
                "operator Gate-2 has not accepted the V2633/V2634 SET-layer package",
            ],
        },
    )
    return path


class NativeAudioAcdbSetcalReplayLiveGateV2637(unittest.TestCase):
    def test_default_payload_is_self_authorized_when_inputs_are_pinned(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2637-"))
        manifest = fake_deploy_manifest(root, gate2=False)

        payload = v2637.dry_run_payload(manifest)

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["safe_to_run_native_replay"])
        self.assertTrue(payload["native_replay_ready"])
        self.assertFalse(payload["approval_phrase_supplied"])
        self.assertFalse(payload["operator_gate2_accepted_manifest"])
        self.assertFalse(payload["manual_approval_required"])
        self.assertFalse(payload["summary"]["gate_closed"])
        self.assertEqual(payload["summary"]["decision"], "v2637-setcal-replay-live-gate-prereqs-satisfied")
        self.assertEqual(payload["replay_blockers"], [])

    def test_verify_live_gate_accepts_legacy_fields_as_noops(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2637-"))
        manifest_path = fake_deploy_manifest(root, gate2=False)
        deploy = v2637.load_deploy_manifest(manifest_path)["raw"]

        v2637.verify_live_gate("", operator_gate2_accepted=False, deploy_manifest=deploy)

    def test_verify_live_gate_still_rejects_unverified_inputs(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2637-"))
        manifest_path = fake_deploy_manifest(root, gate2=True, ok=False)
        deploy = v2637.load_deploy_manifest(manifest_path)["raw"]

        with self.assertRaises(SystemExit) as raised:
            v2637.verify_live_gate(
                v2637.APPROVAL_PHRASE,
                operator_gate2_accepted=True,
                deploy_manifest=deploy,
            )
        self.assertIn("deployment manifest inputs are not all verified", str(raised.exception))

    def test_verify_live_gate_accepts_all_legacy_fields_too(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2637-"))
        manifest_path = fake_deploy_manifest(root, gate2=True)
        deploy = v2637.load_deploy_manifest(manifest_path)["raw"]

        v2637.verify_live_gate(
            v2637.APPROVAL_PHRASE,
            operator_gate2_accepted=True,
            deploy_manifest=deploy,
        )

    def test_report_records_private_manifest_but_no_raw_payload_paths(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2637-"))
        manifest = fake_deploy_manifest(root, gate2=False)
        payload = v2637.dry_run_payload(manifest)
        report = root / "report.md"
        private_manifest = root / "live-gate.json"

        v2637.write_report(report, payload, private_manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("ACDB SET-cal replay live gate", text)
        self.assertIn("self-authorizes", text)
        self.assertIn("legacy compatibility", text)
        self.assertNotIn("00-core_custom_topologies.bin", text)
        self.assertNotIn("local_path_private", text)


if __name__ == "__main__":
    unittest.main()
