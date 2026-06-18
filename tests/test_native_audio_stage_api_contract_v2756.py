"""Tests for the V2756 audio speaker stage API contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
AUDIO_STAGE_H = REPO / "workspace/public/src/native-init/a90_audio_stage.h"
AUDIO_STAGE_C = REPO / "workspace/public/src/native-init/a90_audio_stage.c"


def source_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (AUDIO_C, AUDIO_STAGE_H, AUDIO_STAGE_C)
    )


class NativeAudioStageApiContractV2756(unittest.TestCase):
    def test_python_profile_exports_ordered_stage_api(self) -> None:
        stage_ids = profiles.staged_contract()
        stages = profiles.stage_manifests("internal-speaker-safe")

        self.assertEqual(stage_ids[0], "preflight-v2321-health")
        self.assertIn("write-global-app-type-config", stage_ids)
        self.assertIn("verify-private-acdb-manifest", stage_ids)
        self.assertIn("prepare-acdb-payload-bundle", stage_ids)
        self.assertIn("load-acdb-payload-files", stage_ids)
        self.assertIn("replay-acdb-setcal-sequence", stage_ids)
        self.assertIn("plan-bounded-pcm-playback", stage_ids)
        self.assertIn("bounded-pcm-playback", stage_ids)
        self.assertIn("plan-audio-stop-cleanup", stage_ids)
        self.assertEqual(stage_ids[-1], "rollback-v2321")
        self.assertEqual(len(stage_ids), len(stages))
        self.assertEqual([stage["order"] for stage in stages], sorted(stage["order"] for stage in stages))
        self.assertTrue(any(stage["native_implemented"] for stage in stages))
        self.assertTrue(any(not stage["native_implemented"] for stage in stages))

    def test_python_stage_commands_are_profile_parameterized(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        self.assertEqual(stages["write-global-app-type-config"]["command"], ["audio", "app-type", "internal-speaker-safe", "--write"])
        self.assertEqual(
            stages["apply-core-speaker-route"]["command"],
            ["audio", "route", "internal-speaker-safe", "--apply", "--layer", "core"],
        )
        self.assertEqual(
            stages["reset-core-speaker-route"]["command"],
            ["audio", "route", "internal-speaker-safe", "--reset", "--layer", "core"],
        )
        self.assertEqual(
            stages["verify-private-acdb-manifest"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--verify",
                "--dry-run",
            ],
        )
        self.assertTrue(stages["verify-private-acdb-manifest"]["native_implemented"])
        self.assertFalse(stages["verify-private-acdb-manifest"]["writes_runtime_state"])
        self.assertEqual(
            stages["prepare-acdb-payload-bundle"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--prepare",
                "--dry-run",
            ],
        )
        self.assertTrue(stages["prepare-acdb-payload-bundle"]["native_implemented"])
        self.assertFalse(stages["prepare-acdb-payload-bundle"]["writes_runtime_state"])
        self.assertEqual(
            stages["load-acdb-payload-files"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--load",
                "--dry-run",
            ],
        )
        self.assertTrue(stages["load-acdb-payload-files"]["native_implemented"])
        self.assertFalse(stages["load-acdb-payload-files"]["writes_runtime_state"])
        self.assertEqual(
            stages["replay-acdb-setcal-sequence"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--execute",
            ],
        )
        self.assertFalse(stages["replay-acdb-setcal-sequence"]["native_implemented"])
        self.assertEqual(
            stages["plan-bounded-pcm-playback"]["command"],
            ["audio", "play", "internal-speaker-safe", "--mode", "probe", "--dry-run"],
        )
        self.assertTrue(stages["plan-bounded-pcm-playback"]["native_implemented"])
        self.assertFalse(stages["plan-bounded-pcm-playback"]["writes_runtime_state"])
        self.assertEqual(
            stages["bounded-pcm-playback"]["command"],
            ["audio", "play", "internal-speaker-safe", "--mode", "probe", "--execute"],
        )
        self.assertEqual(stages["bounded-pcm-playback"]["speaker_scope"], "internal-speaker")
        self.assertEqual(
            stages["plan-audio-stop-cleanup"]["command"],
            ["audio", "stop", "internal-speaker-safe", "--dry-run"],
        )
        self.assertTrue(stages["plan-audio-stop-cleanup"]["native_implemented"])
        self.assertFalse(stages["plan-audio-stop-cleanup"]["writes_runtime_state"])

    def test_profile_manifest_includes_stage_api_without_private_paths(self) -> None:
        manifest = profiles.profile_manifest()
        text = repr(manifest)

        self.assertIn("stage_api", manifest)
        self.assertIn("staged_contract", manifest)
        self.assertIn("apply-core-speaker-route", manifest["staged_contract"])
        self.assertNotIn("workspace/private", text)
        self.assertNotIn("local_path_private", text)

    def test_native_audio_exposes_read_only_stages_subcommand(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "stages") == 0', text)
        self.assertIn("return audio_print_stages(argv, argc);", text)
        self.assertIn("audio.stages.read_only=1", text)
        self.assertIn("audio.stages.all_native_ready=0", text)
        self.assertIn("usage: audio stages [%s]", text)

    def test_native_stage_table_matches_key_profile_stages(self) -> None:
        text = source_text()

        required = [
            "preflight-v2321-health",
            "adsp-boot-once",
            "snd-materialize-once",
            "write-global-app-type-config",
            "verify-private-acdb-manifest",
            "prepare-acdb-payload-bundle",
            "load-acdb-payload-files",
            "replay-acdb-setcal-sequence",
            "apply-core-speaker-route",
            "plan-bounded-pcm-playback",
            "bounded-pcm-playback",
            "plan-audio-stop-cleanup",
            "reset-core-speaker-route",
            "rollback-v2321",
        ]
        for stage_id in required:
            with self.subTest(stage_id=stage_id):
                self.assertIn(f'.id = "{stage_id}"', text)

    def test_native_stage_policy_keeps_unfinished_write_paths_non_native(self) -> None:
        text = source_text()

        self.assertRegex(
            text,
            re.compile(r'\.id = "replay-acdb-setcal-sequence".*?\.native_implemented = false', re.DOTALL),
        )
        self.assertRegex(
            text,
            re.compile(r'\.id = "bounded-pcm-playback".*?\.native_implemented = true', re.DOTALL),
        )
        self.assertRegex(
            text,
            re.compile(r'\.id = "plan-bounded-pcm-playback".*?\.native_implemented = true', re.DOTALL),
        )
        self.assertRegex(
            text,
            re.compile(r'\.id = "plan-audio-stop-cleanup".*?\.native_implemented = true', re.DOTALL),
        )
        self.assertRegex(
            text,
            re.compile(r'\.id = "apply-core-speaker-route".*?\.native_implemented = true', re.DOTALL),
        )
        self.assertIn('.command_template = "audio route %s --apply --layer core"', text)
        self.assertIn('.command_template = "audio route %s --reset --layer core"', text)
        self.assertIn('verify-private-acdb-manifest', text)
        self.assertIn('prepare-acdb-payload-bundle', text)
        self.assertIn('load-acdb-payload-files', text)
        self.assertIn('plan-bounded-pcm-playback', text)
        self.assertIn('plan-audio-stop-cleanup', text)
        self.assertIn('--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --verify --dry-run"', text)
        self.assertIn('--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --prepare --dry-run"', text)
        self.assertIn('--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --load --dry-run"', text)
        self.assertIn('--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --execute"', text)
        self.assertIn('.command_template = "audio play %s --mode probe --dry-run"', text)
        self.assertIn('.command_template = "audio play %s --mode probe --execute"', text)
        self.assertIn('.command_template = "audio stop %s --dry-run"', text)


if __name__ == "__main__":
    unittest.main()
