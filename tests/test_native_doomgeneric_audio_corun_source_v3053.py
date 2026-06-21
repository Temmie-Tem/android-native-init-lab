from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3053_doomgeneric_audio_corun.py")


class NativeDoomgenericAudioCorunSourceV3053Tests(unittest.TestCase):
    def test_builder_contract_pins_v3053_audio_corun_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3053")
        self.assertEqual(runner.INIT_VERSION, "0.10.85")
        self.assertEqual(runner.INIT_BUILD, "v3053-doomgeneric-audio-corun")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3053")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3053-audio-corun")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3053-audio-corun-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3053-input.state")
        self.assertEqual(runner.SOUND_MODE, "native-audio-corun-tone-v3053")
        self.assertEqual(runner.AUDIO_CORUN, 1)
        self.assertEqual(runner.AUDIO_CORUN_DURATION_MS, 10000)
        self.assertEqual(runner.AUDIO_CORUN_AMPLITUDE_MILLI, 80)
        self.assertIn(
            b"a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(b"audio.stop.worker.stop_rc=", runner.REQUIRED_STRINGS)

    def test_adapter_source_adds_audio_corun_marker_but_keeps_doom_sound_disabled(self) -> None:
        source = runner.v3053_adapter_source()

        self.assertIn("a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled", source)
        self.assertIn("marker_checksum(a90_doomgeneric_v3053_audio_policy)", source)
        self.assertIn('static char arg_nosound[] = "-nosound";', source)
        self.assertIn('static char arg_nomusic[] = "-nomusic";', source)
        self.assertIn("doomgeneric_Create(12, argv);", source)

    def test_native_hud_wires_loop_audio_corun_and_audio_stop_tracks_worker(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")
        audio_source = (REPO_ROOT / "workspace/public/src/native-init/a90_audio.c").read_text(encoding="utf-8")

        self.assertIn("A90_DOOMGENERIC_AUDIO_CORUN", hud_source)
        self.assertIn("video_demo_doom_audio_corun_start", hud_source)
        self.assertIn("video.demo.doom.audio.source=native-bounded-tone", hud_source)
        self.assertIn("video.demo.doom.audio.real_doom_sfx=0", hud_source)
        self.assertIn("video.demo.doom.loop_start.audio_nonfatal=1", hud_source)
        self.assertIn("video_demo_doom_audio_corun_stop", hud_source)
        self.assertIn("audio_play_async_worker_pid = pid;", audio_source)
        self.assertIn("audio_play_stop_tracked_worker", audio_source)
        self.assertIn("audio.stop.worker.stop_rc=%d", audio_source)

    def test_report_template_records_v3054_live_gate_and_sfx_boundary(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3053.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "audio_corun": {
                    "enabled": True,
                    "mode": runner.AUDIO_CORUN_MODE,
                    "duration_ms": runner.AUDIO_CORUN_DURATION_MS,
                    "amplitude_milli": runner.AUDIO_CORUN_AMPLITUDE_MILLI,
                },
            },
            "v3033_marker_strings": [
                "v3053-doomgeneric-audio-corun",
                "a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3053 DOOMGENERIC Audio Co-run Source Build", report)
        self.assertIn("Real DOOM SFX backend: `0`", report)
        self.assertIn("Run ID: `V3054`", report)
        self.assertIn("loop-stop", report)


if __name__ == "__main__":
    unittest.main()
