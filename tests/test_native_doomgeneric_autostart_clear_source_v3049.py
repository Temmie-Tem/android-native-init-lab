from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3049_doomgeneric_autostart_clear.py")


class NativeDoomgenericAutostartClearSourceV3049Tests(unittest.TestCase):
    def test_builder_contract_pins_v3049_autostart_clear_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3049")
        self.assertEqual(runner.INIT_VERSION, "0.10.83")
        self.assertEqual(runner.INIT_BUILD, "v3049-doomgeneric-autostart-clear")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3049")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3049-autostart-clear")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3049-autostart-clear-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3049-input.state")
        self.assertIn(b"a90.doomgeneric.v3049.autostart=warp-e1m1-skill2", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.clear.reason=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.clear.rc=", runner.REQUIRED_STRINGS)

    def test_adapter_source_adds_warp_skill_autostart_and_keeps_nosound(self) -> None:
        source = runner.v3049_adapter_source()

        self.assertIn("a90.doomgeneric.v3049.autostart=warp-e1m1-skill2", source)
        self.assertIn('static char arg_warp[] = "-warp";', source)
        self.assertIn('static char arg_episode[] = "1";', source)
        self.assertIn('static char arg_map[] = "1";', source)
        self.assertIn('static char arg_skill[] = "-skill";', source)
        self.assertIn('static char arg_skill_value[] = "2";', source)
        self.assertIn("doomgeneric_Create(12, argv);", source)
        self.assertIn('static char arg_nosound[] = "-nosound";', source)
        self.assertIn('static char arg_nomusic[] = "-nomusic";', source)

    def test_loop_stop_clears_last_presented_frame(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video_demo_doom_clear_presented_frame", source)
        self.assertIn('a90_kms_present("doomstop-clear", true)', source)
        self.assertIn("video.demo.doom.clear.reason=%s", source)
        self.assertIn("video.demo.doom.clear.rc=%d", source)
        self.assertIn('video_demo_doom_clear_presented_frame("loop-stop-inactive")', source)
        self.assertIn('video_demo_doom_clear_presented_frame("loop-stop")', source)

    def test_report_template_records_v3050_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3049.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
            },
            "v3033_marker_strings": [
                "v3049-doomgeneric-autostart-clear",
                "a90.doomgeneric.v3049.autostart=warp-e1m1-skill2",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3049 DOOMGENERIC Autostart Clear Source Build", report)
        self.assertIn("`-warp 1 1 -skill 2`", report)
        self.assertIn("Run ID: `V3050`", report)
        self.assertIn("loop-stop", report)


if __name__ == "__main__":
    unittest.main()
