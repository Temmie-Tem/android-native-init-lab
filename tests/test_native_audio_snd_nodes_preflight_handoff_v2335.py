"""Host-only regression tests for the V2335 audio snd preflight runner."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2335 = load_revalidation("native_audio_snd_nodes_preflight_handoff_v2335")


def args() -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host="127.0.0.1",
        bridge_port=54321,
        command_timeout=60.0,
        menu_settle_sec=0.0,
    )


class CommandConstruction(unittest.TestCase):
    def test_a90ctl_command_uses_slow_input_and_optional_hide(self) -> None:
        command = v2335.a90ctl_command(args(), ["audio", "snd-status"], hide_on_busy=True, timeout=90.0)

        self.assertEqual(command[:2], ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py"])
        self.assertIn("--input-mode", command)
        self.assertEqual(command[command.index("--input-mode") + 1], "slow")
        self.assertIn("--hide-on-busy", command)
        self.assertEqual(command[-2:], ["audio", "snd-status"])

    def test_dry_run_marks_observations_retryable_but_keeps_materializer_one_shot(self) -> None:
        plan = v2335.dry_run_plan(v2335.preflight_state())

        for command in plan["candidate_health"]:
            self.assertIn("--input-mode", command)
            self.assertIn("slow", command)
            self.assertIn("--hide-on-busy", command)

        audio_commands = [item for item in plan["audio_window"] if isinstance(item, list)]
        adsp_status = audio_commands[0]
        adsp_boot = audio_commands[1]
        snd_status_before = audio_commands[2]
        materialize = audio_commands[3]
        snd_status_after = audio_commands[4]
        settle_notes = [item for item in plan["audio_window"] if isinstance(item, str) and "settle auto menu" in item]

        self.assertIn("--hide-on-busy", adsp_status)
        self.assertIn("--hide-on-busy", snd_status_before)
        self.assertIn("--hide-on-busy", snd_status_after)
        self.assertIn("--hide-on-busy", adsp_boot)
        self.assertNotIn("--retry-unsafe", adsp_boot)
        self.assertNotIn("--hide-on-busy", materialize)
        self.assertNotIn("--retry-unsafe", materialize)
        self.assertEqual(materialize[-3:], ["audio", "snd-materialize-once", v2335.SND_TOKEN])
        self.assertEqual(len(settle_notes), 2)
        self.assertIn("ADSP boot", settle_notes[0])
        self.assertIn("/dev/snd materializer", settle_notes[1])


class ApprovalAndPreflight(unittest.TestCase):
    def test_live_approval_requires_exact_phrase(self) -> None:
        with self.assertRaises(SystemExit):
            v2335.verify_live_approval(argparse.Namespace(approval="AUD-3-preflight 라이브 승인"))

        v2335.verify_live_approval(argparse.Namespace(approval=v2335.APPROVAL_PHRASE))

    def test_preflight_ok_requires_candidate_rollback_and_fallback_hashes(self) -> None:
        good = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
        }
        bad = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": False},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
        }

        self.assertTrue(v2335.FLASH.exists())
        self.assertTrue(v2335.A90CTL.exists())
        self.assertTrue(v2335.preflight_ok(good))
        self.assertFalse(v2335.preflight_ok(bad))


class ObservationRetry(unittest.TestCase):
    def test_menu_settle_hides_before_one_shot_without_audio_retry(self) -> None:
        calls: list[dict] = []

        def fake_transport_step(out_dir, steps, name, serial_args, native_args, *, timeout, retry_observation, allow_error=False):
            del out_dir, serial_args, allow_error
            calls.append({
                "name": name,
                "native_args": native_args,
                "timeout": timeout,
                "retry_observation": retry_observation,
            })
            step = {"name": name, "ok": True, "stdout_path": ""}
            steps.append(step)
            return step

        with tempfile.TemporaryDirectory() as tempdir, mock.patch.object(
            v2335,
            "run_serial_transport_step",
            side_effect=fake_transport_step,
        ):
            steps: list[dict] = []
            result = v2335.run_menu_settle_step(
                Path(tempdir),
                steps,
                "settle-before-adsp-boot-once",
                args(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(calls, [{
            "name": "settle-before-adsp-boot-once",
            "native_args": ["hide"],
            "timeout": 20.0,
            "retry_observation": True,
        }])
        self.assertEqual(steps[0]["name"], "settle-before-adsp-boot-once")
        self.assertEqual(steps[1]["name"], "settle-before-adsp-boot-once-settle")
        self.assertEqual(steps[1]["command"], ["host", "sleep", "0.000"])

    def test_observation_uses_recoverable_serial_transport_without_calling_real_bridge(self) -> None:
        calls: list[dict] = []

        def fake_transport_step(out_dir, steps, name, serial_args, native_args, *, timeout, retry_observation, allow_error=False):
            del out_dir, serial_args, allow_error
            calls.append({
                "name": name,
                "native_args": native_args,
                "timeout": timeout,
                "retry_observation": retry_observation,
            })
            step = {"name": name, "ok": True, "stdout_path": ""}
            steps.append(step)
            return step

        with tempfile.TemporaryDirectory() as tempdir, mock.patch.object(
            v2335,
            "run_serial_transport_step",
            side_effect=fake_transport_step,
        ):
            steps: list[dict] = []
            result = v2335.run_a90ctl_observation(
                args(),
                Path(tempdir),
                steps,
                "audio-snd-status",
                ["audio", "snd-status"],
                timeout=10.0,
                attempts=2,
                delay_sec=0,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(calls, [{
            "name": "audio-snd-status-attempt-1",
            "native_args": ["audio", "snd-status"],
            "timeout": 10.0,
            "retry_observation": True,
        }])

    def test_serial_transport_step_records_recovery_and_never_retries_token_by_default(self) -> None:
        captured: list[dict] = []

        def fake_recovered(command, *, host, port, timeout, retry_unsafe, recovery_step_prefix):
            captured.append({
                "command": command,
                "host": host,
                "port": port,
                "timeout": timeout,
                "retry_unsafe": retry_unsafe,
                "recovery_step_prefix": recovery_step_prefix,
            })
            return {
                "command": ["cmdv1", *command],
                "started": "2026-06-14T00:00:00+00:00",
                "elapsed_sec": 0.1,
                "rc": 0,
                "ok": True,
                "stdout": "ok\n",
                "stderr": "",
                "serial_recovery_contract": 1,
                "serial_recovery": {"retry_allowed": retry_unsafe, "recovered": False},
            }

        with tempfile.TemporaryDirectory() as tempdir, mock.patch.object(
            v2335.transport,
            "run_serial_command_recovered",
            side_effect=fake_recovered,
        ):
            steps: list[dict] = []
            record = v2335.run_serial_transport_step(
                Path(tempdir),
                steps,
                "snd-materialize-once",
                args(),
                ["audio", "snd-materialize-once", v2335.SND_TOKEN],
                timeout=90.0,
                retry_observation=False,
            )

        self.assertTrue(record["ok"])
        self.assertEqual(record["transport"], "a90_transport.serial")
        self.assertEqual(record["serial_recovery"], {"retry_allowed": False, "recovered": False})
        self.assertEqual(captured[0]["command"], ["audio", "snd-materialize-once", v2335.SND_TOKEN])
        self.assertFalse(captured[0]["retry_unsafe"])


class AudioStatusParsing(unittest.TestCase):
    def test_inline_sound_class_fields_satisfy_pre_materialization_gate(self) -> None:
        sample = """
audio.rpmsg.count=20 adsp_like=7 cdsp_like=0
audio.sound_class.count=128 card_like=1 control_like=1
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card
audio.snd.9.name=controlC0 sysfs_dev=116:2 devnode=/dev/snd/controlC0 state=missing
audio.snd.24.name=pcmC0D0c sysfs_dev=116:4 devnode=/dev/snd/pcmC0D0c state=missing
audio.snd_status.entries=128 allowed=61 with_dev=61 listed=61 missing=61 already_ok=0 invalid=0 refused=67 created=0 failed=0
audio.status.audio_playback_attempted=0
"""

        parsed = v2335.parse_key_values(sample)
        classification = v2335.classify_audio_status(sample)

        self.assertEqual(parsed["audio.sound_class.count"][-1], "128")
        self.assertEqual(parsed["audio.sound_class.card_like"][-1], "1")
        self.assertEqual(parsed["audio.sound_class.control_like"][-1], "1")
        self.assertEqual(parsed["audio.dev_snd.count"][-1], "0")
        self.assertEqual(parsed["audio.dev_snd.control_like"][-1], "0")
        self.assertEqual(parsed["audio.dev_snd.pcm_like"][-1], "0")
        self.assertIn("sm8150-tavil-snd-card", parsed["audio.proc_asound_cards"][-1])
        self.assertTrue(classification["has_audio_card"])
        self.assertTrue(classification["has_sound_class_control"])
        self.assertFalse(classification["has_dev_snd_control"])
        self.assertFalse(classification["has_dev_snd_pcm"])

    def test_ok_dev_snd_summary_or_state_marks_materialized_nodes(self) -> None:
        summary_sample = """
audio.dev_snd.count=2 control_like=1 pcm_like=1
"""
        state_sample = """
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.snd.0.name=controlC0 sysfs_dev=116:2 devnode=/dev/snd/controlC0 state=ok
audio.snd.1.name=pcmC0D0p sysfs_dev=116:3 devnode=/dev/snd/pcmC0D0p state=ok
"""

        summary = v2335.classify_audio_status(summary_sample)
        state = v2335.classify_audio_status(state_sample)

        self.assertTrue(summary["has_dev_snd_control"])
        self.assertTrue(summary["has_dev_snd_pcm"])
        self.assertTrue(state["has_dev_snd_control"])
        self.assertTrue(state["has_dev_snd_pcm"])


if __name__ == "__main__":
    unittest.main()
