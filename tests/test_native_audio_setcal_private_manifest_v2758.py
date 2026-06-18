"""Tests for the V2758 audio SET-cal private manifest verification boundary."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
SCRIPT_DIR = REPO / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import native_audio_setcal_payload_manifest_v2758 as manifest_v2758  # noqa: E402
import native_audio_speaker_profiles_v2749 as profiles  # noqa: E402


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalPrivateManifestV2758(unittest.TestCase):
    def test_native_setcal_exposes_verify_manifest_without_ioctl(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[argi], "--manifest") == 0', text)
        self.assertIn('--verify") == 0', text)
        self.assertIn("audio.setcal.verify.manifest", text)
        self.assertIn("audio.setcal.verify.ioctl_attempted=0", text)
        self.assertIn("a90_helper_sha256_file(path, actual_sha256", text)
        verify_start = text.index("static int audio_setcal_verify_manifest")
        verify_end = text.index("static void audio_setcal_print_execute_plan", verify_start)
        self.assertNotIn("AUDIO_SET_CALIBRATION", text[verify_start:verify_end])

    def test_native_manifest_paths_are_bounded_to_runtime_or_legacy_cache(self) -> None:
        text = source_text()

        self.assertIn('#define AUDIO_SETCAL_RUNTIME_PREFIX "/cache/a90-runtime"', text)
        self.assertIn('#define AUDIO_SETCAL_LEGACY_REPLAY_PREFIX "/cache/a90-acdb-setcal-replay-"', text)
        self.assertIn("audio_setcal_path_has_dotdot", text)
        self.assertIn("audio_setcal_manifest_path_allowed", text)
        self.assertIn("audio_setcal_payload_path_allowed", text)

    def test_stage_api_adds_native_verify_before_replay(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        verify = stages["verify-private-acdb-manifest"]
        replay = stages["replay-acdb-setcal-sequence"]
        self.assertLess(verify["order"], replay["order"])
        self.assertTrue(verify["native_implemented"])
        self.assertFalse(verify["writes_runtime_state"])
        self.assertIn("--verify", verify["command"])
        self.assertIn(profiles.DEFAULT_SETCAL_MANIFEST_PATH, verify["command"])
        self.assertTrue(replay["native_implemented"])
        self.assertIn("--execute", replay["command"])

    def test_generator_builds_line_manifest_from_deploy_plan_shape(self) -> None:
        profile = profiles.INTERNAL_SPEAKER_SAFE
        files = []
        replay_entries = []
        for index, cal_type in enumerate(profile.acdb_set_order):
            role = f"ROLE_{index}"
            dmabuf_expected = index in {0, 5, 7, 9}
            arg_remote = f"/cache/a90-acdb-setcal-replay-v2725/{index:02d}-arg.bin"
            files.append(
                {
                    "kind": "set_arg",
                    "remote_path": arg_remote,
                    "local": {"size": 32 + index, "sha256": f"{index:064x}"},
                }
            )
            payload_remote = None
            if dmabuf_expected:
                payload_remote = f"/cache/a90-acdb-setcal-replay-v2725/{index:02d}-payload.bin"
                files.append(
                    {
                        "kind": "payload",
                        "remote_path": payload_remote,
                        "local": {"size": 100 + index, "sha256": f"{index + 100:064x}"},
                    }
                )
            replay_entries.append(
                {
                    "sequence": index,
                    "cal_type": cal_type,
                    "role": role,
                    "dmabuf_expected": dmabuf_expected,
                    "arg_remote": arg_remote,
                    "payload_remote": payload_remote,
                }
            )

        lines = manifest_v2758.build_manifest_lines({"files": files, "replay_entries": replay_entries})
        manifest = "\n".join(lines)
        self.assertIn("version 1", manifest)
        self.assertIn(f"profile {profile.profile_id}", manifest)
        self.assertIn("entry_count 11", manifest)
        self.assertEqual(sum(1 for line in lines if line.startswith("entry ")), 11)
        self.assertIn("/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/00-arg.bin", manifest)
        self.assertNotIn("workspace/private", manifest)
        cal_types = [int(line.split()[2]) for line in lines if line.startswith("entry ")]
        self.assertEqual(cal_types, list(profile.acdb_set_order))
        self.assertNotIn(10, cal_types)
        self.assertNotIn(14, cal_types)
        self.assertNotIn(24, cal_types)


if __name__ == "__main__":
    unittest.main()
