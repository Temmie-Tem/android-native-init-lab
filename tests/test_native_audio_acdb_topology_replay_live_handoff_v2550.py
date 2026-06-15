"""Host-only tests for the V2550 ACDB topology replay live-wrapper plan."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2550 = load_revalidation("native_audio_acdb_topology_replay_live_handoff_v2550")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2550-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "approval": "",
        "manifest_path": root / "manifest.json",
        "helper": v2550.DEFAULT_HELPER,
        "payload": v2550.v2549.STABLE_PAYLOAD,
        "hold_sec": 10,
        "tinyalsa_manifest": v2550.speaker.inv.MANIFEST,
        "pcm_probe_manifest": v2550.speaker.pcm_probe.DEFAULT_MANIFEST,
        "evidence_dir": v2550.speaker.recipe.DEFAULT_EVIDENCE_DIR,
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "device_ip": "192.168.7.2",
        "host_ip": "192.168.7.1",
        "host_prefix": 24,
        "tcp_port": 2325,
        "command_timeout": 60.0,
        "tcp_timeout": 30.0,
        "device_toolbox": v2550.speaker.DEFAULT_DEVICE_TOOLBOX,
        "device_busybox": v2550.speaker.DEFAULT_DEVICE_BUSYBOX,
        "flash_timeout": 900.0,
        "card_timeout": 70.0,
        "poll_interval": 2.0,
        "menu_settle_sec": 1.0,
        "transfer_port": 18220,
        "transfer_delay": 1.0,
        "transfer_timeout": 120.0,
        "repair_host_ncm": True,
        "ncm_setup_timeout": 120.0,
        "ncm_interface_timeout": 20.0,
        "ncm_setup_sudo": "sudo -n",
        "inventory_transport": "auto",
        "card": 0,
        "route_transport": "serial",
        "mixer_timeout": 45.0,
        "playback_timeout": 20.0,
        "duration_ms": v2550.speaker.DEFAULT_DURATION_MS,
        "amplitude": v2550.speaker.DEFAULT_AMPLITUDE,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbTopologyReplayLiveHandoffV2550(unittest.TestCase):
    def test_helper_and_payload_inputs_are_ready(self) -> None:
        helper = v2550.helper_state()
        payload = v2550.payload_state()

        self.assertTrue(helper["ready"], helper)
        self.assertTrue(helper["sha256_ok"])
        self.assertTrue(helper["execute_marker_ok"])
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["sha256"], v2550.v2549.EXPECTED_PAYLOAD_SHA256)

    def test_plan_composes_route_app_type_replay_and_cleanup(self) -> None:
        payload = v2550.plan(args())

        self.assertTrue(payload["ok"], payload["safety"])
        self.assertEqual(payload["decision"], "v2550-acdb-topology-replay-live-wrapper-plan-host-only")
        self.assertFalse(payload["native_calibration_ioctls_run"])
        self.assertFalse(payload["playback_run"])
        self.assertEqual(payload["inputs"]["route_apply_count"], 13)
        self.assertEqual(payload["inputs"]["route_reset_count"], 12)
        self.assertTrue(payload["inputs"]["speaker_app_type_enabled"])
        joined = "\n".join(payload["future_live_sequence"])
        self.assertIn("AUDIO_SET_CALIBRATION ok", joined)
        self.assertIn("reverse route reset", joined)
        self.assertIn("rollback to V2321", joined)
        self.assertIn("AUDIO_DEALLOCATE_CALIBRATION", payload["helper_cleanup_capture_script"])

    def test_safety_rejects_forbidden_plan_tokens(self) -> None:
        payload = v2550.plan(args())
        payload["future_live_sequence"].append("run fastboot as a bad idea")
        safety = v2550.safety(payload)

        self.assertFalse(safety["ok"])
        self.assertTrue(any(item["token"] == "fastboot" for item in safety["findings"]))

    def test_run_live_is_source_only_refusal_even_with_exact_phrase(self) -> None:
        local_args = args(run_live=True, approval=v2550.FUTURE_APPROVAL_PHRASE)
        payload = v2550.plan(local_args)
        refusal = v2550.live_refusal(local_args, payload)

        self.assertFalse(refusal["ok"])
        self.assertTrue(refusal["approval_phrase_matched"])
        self.assertFalse(refusal["native_calibration_ioctls_run"])
        self.assertIn("source-only", refusal["decision"])

    def test_cli_dry_run_outputs_json_and_writes_manifest(self) -> None:
        local_args = args()
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_topology_replay_live_handoff_v2550.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--dry-run",
                "--manifest-path",
                str(local_args.manifest_path),
            ],
            cwd=v2550.snd.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"], payload.get("safety"))
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
