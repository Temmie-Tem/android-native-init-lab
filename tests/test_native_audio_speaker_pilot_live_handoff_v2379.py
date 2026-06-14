"""Host-only tests for the V2379 exact-gated native speaker pilot runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from _loader import load_revalidation

v2379 = load_revalidation("native_audio_speaker_pilot_live_handoff_v2379")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "approval": "",
        "manifest": v2379.inv.MANIFEST,
        "pcm_probe_manifest": v2379.pcm_probe.DEFAULT_MANIFEST,
        "playback_tool": "pcm-probe",
        "evidence_dir": v2379.recipe.DEFAULT_EVIDENCE_DIR,
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "device_ip": "192.168.7.2",
        "host_ip": "192.168.7.1",
        "host_prefix": 24,
        "tcp_port": 2325,
        "command_timeout": 60.0,
        "tcp_timeout": 30.0,
        "device_toolbox": v2379.DEFAULT_DEVICE_TOOLBOX,
        "device_busybox": v2379.DEFAULT_DEVICE_BUSYBOX,
        "flash_timeout": 900.0,
        "card_timeout": 70.0,
        "poll_interval": 2.0,
        "menu_settle_sec": 1.0,
        "transfer_port": 18179,
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
        "duration_ms": v2379.DEFAULT_DURATION_MS,
        "amplitude": v2379.DEFAULT_AMPLITUDE,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class NativeSpeakerPilotLiveHandoff(unittest.TestCase):
    def test_dry_run_composes_materialization_route_playback_reset(self) -> None:
        payload = v2379.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2379-native-speaker-pilot-runner-dry-run")
        self.assertIn("AUD-4-native-speaker-pilot go:", payload["approval_phrase_required"])
        self.assertEqual(payload["preflight"]["remote_dir"], "/cache/a90-runtime/bin/v2379-speaker-pilot")
        self.assertEqual([step["artifact"] for step in payload["tool_install_plan"]], ["tinymix", "pcm_probe", "pilot_wav_generated_runtime"])
        runtime = payload["runtime_plan"]
        self.assertEqual(runtime["route_transport"], "serial")
        self.assertEqual(runtime["snapshot_transport"], "auto-selected transfer transport")
        self.assertEqual(runtime["playback_transport"], "auto-selected transfer transport")
        self.assertEqual(len(runtime["route_apply_commands"]), 13)
        self.assertEqual(len(runtime["route_reset_commands"]), 12)
        self.assertEqual(runtime["playback_failure_dmesg_capture"]["step"], "dmesg-after-playback-failure-before-reset")
        self.assertTrue(runtime["playback_failure_dmesg_capture"]["read_only"])
        self.assertEqual(runtime["playback_failure_dmesg_capture"]["transport"], "serial-cmdv1x")
        self.assertEqual(runtime["playback_failure_dmesg_capture"]["bounded_tail_lines"], 240)
        self.assertEqual(
            runtime["playback_failure_dmesg_capture"]["argv"],
            [v2379.DEFAULT_DEVICE_BUSYBOX, "sh", "-c", "dmesg | tail -n 240"],
        )
        self.assertEqual(
            runtime["playback"]["argv"],
            [
                "/cache/a90-runtime/bin/v2379-speaker-pilot/a90_pcm_write_probe_v2386",
                "/cache/a90-runtime/bin/v2379-speaker-pilot/pilot_48k_s16le_stereo_0p02_1s.wav",
                "-D",
                "0",
                "-d",
                "0",
            ],
        )
        flat = json.dumps(payload, sort_keys=True)
        self.assertIn("flash_candidate", flat)
        self.assertIn("snd-materialize-once", flat)
        self.assertIn("transfer_readiness_plan", payload)
        runtime_flat = json.dumps(payload["runtime_plan"], sort_keys=True)
        self.assertNotIn("app_process", runtime_flat)
        self.assertNotIn("am start", runtime_flat)
        self.assertNotIn("/dev/block", runtime_flat)

    def test_preflight_verifies_v2377_recipe_and_pinned_tinyalsa_tools(self) -> None:
        state = v2379.preflight_state(args())

        self.assertTrue(state["ok"])
        self.assertTrue(state["speaker_plan"]["recipe"]["ok"])
        self.assertTrue(state["tools"]["tinymix"]["sha256_ok"])
        self.assertTrue(state["tools"]["tinyplay"]["sha256_ok"])
        self.assertTrue(state["tools"]["pcm_probe"]["sha256_ok"])
        self.assertTrue(state["tools"]["pcm_probe"]["diagnostic_contract"]["reports_pcm_get_error"])
        self.assertEqual(state["playback_tool"], "pcm-probe")
        self.assertTrue(state["command_safety"]["ok"])
        self.assertEqual(state["route_transport"], "serial")
        self.assertTrue(state["tcpctl_remote_failure_is_hard_failure"])
        self.assertEqual(state["magisk_direction"]["role"], "android_measurement_fallback_only")
        self.assertFalse(state["magisk_direction"]["native_runtime_dependency"])
        self.assertFalse(state["magisk_direction"]["aud4_uses_magisk"])

    def test_command_safety_rejects_unbounded_or_forbidden_plans(self) -> None:
        plan = v2379.speaker_plan(args())
        self.assertFalse(v2379.command_safety(plan, amplitude=0.2, duration_ms=1000)["ok"])
        self.assertFalse(v2379.command_safety(plan, amplitude=0.02, duration_ms=1500)["ok"])
        plan["route_apply_commands"][0]["argv"].append("/dev/block/by-name/boot")
        self.assertFalse(v2379.command_safety(plan, amplitude=0.02, duration_ms=1000)["ok"])

    def test_generate_pilot_wav_is_bounded_stereo_48k(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "pilot.wav"
            meta = v2379.generate_pilot_wav(wav_path, duration_ms=1000, amplitude=0.02)
            self.assertTrue(wav_path.exists())
            self.assertEqual(meta["frames"], 48000)
            with wave.open(str(wav_path), "rb") as wav:
                self.assertEqual(wav.getframerate(), 48000)
                self.assertEqual(wav.getnchannels(), 2)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getnframes(), 48000)
        with tempfile.TemporaryDirectory() as temp_dir, self.assertRaisesRegex(ValueError, "amplitude"):
            v2379.generate_pilot_wav(Path(temp_dir) / "bad.wav", duration_ms=1000, amplitude=0.2)

    def test_speaker_pilot_blocked_carries_independent_partial_result(self) -> None:
        partial = {"route_apply": [{"name": "apply-1", "ok": True}], "playback_attempted": True}
        exc = v2379.SpeakerPilotBlocked("playback failed", partial)
        partial["route_apply"].append({"name": "mutated", "ok": False})

        self.assertEqual(str(exc), "playback failed")
        self.assertEqual(exc.partial_result["route_apply"], [{"name": "apply-1", "ok": True}])
        self.assertTrue(exc.partial_result["playback_attempted"])

    def test_adsp_boot_classifier_accepts_lost_end_marker_after_accepted_write(self) -> None:
        step = {
            "stdout_tail": (
                "RuntimeError('A90P1 END marker not found\n\r\n"
                "cmdv1 audi doot-once AUD2_ONE_SHAaudio.adsp_boot_once.version=1\r\n"
                "audio.adsp_boot_once.retry=forbidden\r\n[done] audio (21ms)\r\n')"
            ),
            "stdout_path": "",
        }

        classified = v2379.classify_adsp_boot_once_step(step)

        self.assertTrue(classified["accepted"])
        self.assertEqual(classified["decision"], "accepted-protocol-marker-lost")
        self.assertFalse(classified["end_marker"])
        self.assertEqual(classified["failure_markers"], [])

    def test_adsp_boot_classifier_rejects_refused_or_failed_write(self) -> None:
        step = {
            "stdout_tail": "audio.adsp_boot_once.refused=missing-token\r\naudio.status.activation_write_attempted=0",
            "stdout_path": "",
        }

        classified = v2379.classify_adsp_boot_once_step(step)

        self.assertFalse(classified["accepted"])
        self.assertEqual(classified["decision"], "rejected-or-write-failed")
        self.assertEqual(classified["failure_markers"], ["audio.adsp_boot_once.refused="])

    def test_remote_tool_output_classifies_tcpctl_and_tinyplay_failures(self) -> None:
        bad_tinymix = "\n".join(
            [
                "a90_tcpctl v1 ready",
                "OK authenticated",
                "Invalid mixer control: 'Audio'",
                "[exit 2]",
                "ERR exit=2",
            ]
        )
        tinymix_result = v2379.classify_remote_tool_output(bad_tinymix, ("Invalid mixer control",))

        self.assertFalse(tinymix_result["ok"])
        self.assertEqual(tinymix_result["nonzero_exit_codes"], [2, 2])
        self.assertEqual(tinymix_result["failure_markers"], ["Invalid mixer control"])

        tinyplay_result = v2379.classify_remote_tool_output(
            "Error playing sample\n[exit 0]\nOK",
            ("Error playing sample",),
        )

        self.assertFalse(tinyplay_result["ok"])
        self.assertEqual(tinyplay_result["exit_codes"], [0])
        self.assertEqual(tinyplay_result["failure_markers"], ["Error playing sample"])

        probe_result = v2379.classify_remote_tool_output(
            'A90_PCM_PROBE_WRITE_ERROR rc=-1 errno=22 pcm_error="cannot write initial data: Invalid argument"\n[exit 40]',
            ("A90_PCM_PROBE_WRITE_ERROR", "A90_PCM_PROBE_PCM_OPEN_ERROR"),
        )

        self.assertFalse(probe_result["ok"])
        self.assertEqual(probe_result["nonzero_exit_codes"], [40])
        self.assertEqual(probe_result["failure_markers"], ["A90_PCM_PROBE_WRITE_ERROR"])

    def test_wrong_live_approval_exits_before_flash(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py",
                "--run-live",
                "--approval",
                "wrong",
            ],
            cwd=v2379.snd.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("exact --approval phrase required", completed.stderr)
        self.assertIn(v2379.APPROVAL_PHRASE, completed.stderr)
        self.assertNotIn("native_init_flash.py", completed.stdout)

    def test_cli_dry_run_outputs_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_speaker_pilot_live_handoff_v2379.py",
                "--dry-run",
            ],
            cwd=v2379.snd.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2379-native-speaker-pilot-runner-dry-run")
        self.assertTrue(payload["preflight"]["tools"]["tinyplay"]["sha256_ok"])


if __name__ == "__main__":
    unittest.main()
