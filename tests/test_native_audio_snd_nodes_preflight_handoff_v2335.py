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

        adsp_status = plan["audio_window"][0]
        adsp_boot = plan["audio_window"][1]
        snd_status_before = plan["audio_window"][3]
        materialize = plan["audio_window"][4]
        snd_status_after = plan["audio_window"][5]

        self.assertIn("--hide-on-busy", adsp_status)
        self.assertIn("--hide-on-busy", snd_status_before)
        self.assertIn("--hide-on-busy", snd_status_after)
        self.assertIn("--hide-on-busy", adsp_boot)
        self.assertNotIn("--retry-unsafe", adsp_boot)
        self.assertNotIn("--hide-on-busy", materialize)
        self.assertNotIn("--retry-unsafe", materialize)
        self.assertEqual(materialize[-3:], ["audio", "snd-materialize-once", v2335.SND_TOKEN])


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
    def test_observation_retries_read_only_commands_with_hide_but_does_not_call_real_bridge(self) -> None:
        calls: list[list[str]] = []

        def fake_run_step(out_dir, steps, name, command, *, timeout, allow_error=False):
            del out_dir, allow_error
            calls.append(command)
            steps.append({"name": name, "ok": len(calls) > 1})
            if len(calls) == 1:
                raise RuntimeError("A90P1 END marker not found")
            return {"name": name, "ok": True, "stdout_path": ""}

        with tempfile.TemporaryDirectory() as tempdir, mock.patch.object(v2335, "run_step", side_effect=fake_run_step):
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
        self.assertEqual(len(calls), 2)
        for command in calls:
            self.assertIn("--input-mode", command)
            self.assertIn("slow", command)
            self.assertIn("--hide-on-busy", command)
            self.assertEqual(command[-2:], ["audio", "snd-status"])


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
