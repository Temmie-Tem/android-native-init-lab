from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3031_doomgeneric_visible_frame.py")
ROOT = REPO_ROOT


class NativeDoomgenericVisibleFrameSourceV3031Tests(unittest.TestCase):
    def test_bridge_adds_bounded_frame_render_contract_without_input_injection(self) -> None:
        header = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        source = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        combined = header + source

        self.assertIn("struct a90_doomgeneric_frame_render", combined)
        self.assertIn("a90_doomgeneric_bridge_render_frame", combined)
        self.assertIn("--wad-frame-dump", combined)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_FRAME_PATH", combined)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_FRAME_WIDTH", combined)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_FRAME_BYTES", combined)
        self.assertIn("a90_doomgeneric_bridge_verify_wad", combined)
        self.assertNotIn("/dev/input", combined)
        self.assertNotIn("uinput", combined.lower())
        self.assertNotIn("native_init_flash.py", combined)
        self.assertNotIn("/efs", combined)

    def test_video_doom_frame_command_verifies_wad_then_blits_to_kms(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video demo doom frame [frames] --wad runtime-private --sha256", text)
        self.assertIn("a90_doomgeneric_bridge_render_frame", text)
        self.assertIn("video.demo.doom.frame=doomgeneric-sd-wad-visible-frame", text)
        self.assertIn("video.demo.doom.frame.verify.sha256_match=%d", text)
        self.assertIn("video_demo_doom_print_frame_render(\"video.demo.doom.frame.render\", &render)", text)
        self.assertIn("%s.ok=%d", text)
        self.assertIn("video.demo.doom.frame.display.presented=1", text)
        self.assertIn("video.demo.doom.frame.display.path=kms-dumb-buffer", text)
        self.assertIn("a90_kms_present(\"doomframe\", true)", text)
        self.assertIn("video.status.doomgeneric.visible_frame=1", text)

    def test_menu_doom_action_launches_visible_frame_preview_and_restores_menu(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c").read_text(encoding="utf-8")
        menu = (ROOT / "workspace/public/src/native-init/a90_menu.c").read_text(encoding="utf-8")

        self.assertIn("menu.demo.doom.action=visible-frame-preview", text)
        self.assertIn("demo_argv[3] = \"frame\";", text)
        self.assertIn("demo_argv[4] = \"8\";", text)
        self.assertIn("demo_argv[6] = \"runtime-private\";", text)
        self.assertIn("demo_argv[8] = (char *)doomgeneric.expected_wad_sha256;", text)
        self.assertIn("menu.demo.doom.frame_rc=%d", text)
        self.assertIn("auto_hud_show_menu(state, false);", text)
        self.assertIn("WAD FRAME PREVIEW", menu)

    def test_builder_contract_pins_v3031_visible_frame_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3031")
        self.assertEqual(runner.INIT_VERSION, "0.10.75")
        self.assertEqual(runner.INIT_BUILD, "v3031-doomgeneric-visible-frame")
        self.assertEqual(runner.RUNTIME_WAD_PATH, "/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD")
        self.assertEqual(runner.EXPECTED_WAD_SHA256, "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3031-frame.xbgr8888")
        self.assertEqual(runner.FRAME_WIDTH, 640)
        self.assertEqual(runner.FRAME_HEIGHT, 400)
        self.assertEqual(runner.FRAME_STRIDE, 2560)
        self.assertEqual(runner.FRAME_BYTES, 1024000)
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3031")
        self.assertIn(b"--wad-frame-dump", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.frame=doomgeneric-sd-wad-visible-frame", runner.REQUIRED_STRINGS)
        self.assertFalse(runner.ENGINE_RAMDISK_PATH.lower().endswith(".wad"))
        self.assertEqual(runner.v3029.count_wad_entries(["init", runner.ENGINE_RAMDISK_PATH]), 0)

    def test_adapter_source_adds_frame_dump_cli_while_preserving_wad_smoke(self) -> None:
        source = runner.v3031_adapter_source()

        self.assertIn("a90.doomgeneric.v3031.visible_frame=frame-dump-xbgr8888", source)
        self.assertIn("a90.doomgeneric.v3031.frame_dump=raw-xbgr8888-file", source)
        self.assertIn("a90_doomgeneric_run_wad_frame_dump", source)
        self.assertIn("a90_doomgeneric_dump_frame_xbgr8888", source)
        self.assertIn('strcmp(argv[1], "--wad-frame-dump") == 0', source)
        self.assertIn('strcmp(argv[5], "--output") == 0', source)
        self.assertIn("a90_doomgeneric_run_wad_smoke", source)
        self.assertIn("doomgeneric_Tick()", source)
        self.assertNotIn("/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD", source)

    def test_report_template_records_v3032_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3031.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_frame": {
                "runtime_wad_root": runner.RUNTIME_WAD_ROOT,
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "runtime_wad_max_bytes": runner.RUNTIME_WAD_MAX_BYTES,
                "ramdisk_wad_file_count": 0,
                "public_wad_file_count": 0,
                "wad_embedded_in_boot": 0,
                "helper_frame_command": "helper --wad-frame-dump",
                "frame_command": "video demo doom frame 8 --wad runtime-private",
                "frame_path": runner.FRAME_PATH,
                "frame_format": "xbgr8888-raw",
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "frame_stride": runner.FRAME_STRIDE,
                "frame_bytes": runner.FRAME_BYTES,
                "kms_path": "existing-kms-dumb-buffer-blit-present",
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3031/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3031_marker_strings": [
                "v3031-doomgeneric-visible-frame",
                "video demo doom frame [frames] --wad runtime-private --sha256",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3031 DOOMGENERIC Visible Frame Source Build", report)
        self.assertIn("WAD files in ramdisk: `0`", report)
        self.assertIn("WAD bytes embedded in boot image: `0`", report)
        self.assertIn("video demo doom frame", report)
        self.assertIn("Run ID: `V3032`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
