from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3029_doomgeneric_sd_wad_command.py")
ROOT = REPO_ROOT


class NativeDoomgenericSdWadCommandSourceV3029Tests(unittest.TestCase):
    def test_bridge_module_verifies_runtime_wad_before_play_without_public_wad_or_uinput(self) -> None:
        header = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        source = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        combined = header + source

        self.assertIn("runtime_wad_path", combined)
        self.assertIn("expected_wad_sha256", combined)
        self.assertIn("a90_doomgeneric_bridge_verify_wad", combined)
        self.assertIn("a90_doomgeneric_bridge_play", combined)
        self.assertIn("a90_helper_sha256_file", combined)
        self.assertIn("--wad-smoke", combined)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES", combined)
        self.assertNotIn("/dev/input", combined)
        self.assertNotIn("uinput", combined.lower())
        self.assertNotIn("native_init_flash.py", combined)
        self.assertNotIn("/efs", combined)

    def test_video_doom_command_surface_routes_sd_wad_verify_and_play(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video.demo.asset.wad.runtime_path=%s", text)
        self.assertIn("video.demo.asset.wad.expected_sha256=%s", text)
        self.assertIn("video demo doom verify --wad runtime-private --sha256", text)
        self.assertIn("video demo doom play [frames] --wad runtime-private --sha256", text)
        self.assertIn("video_demo_doom_args_request_runtime_wad", text)
        self.assertIn("video_demo_doom_run_wad_command", text)
        self.assertIn("a90_doomgeneric_bridge_verify_wad", text)
        self.assertIn("a90_doomgeneric_bridge_play", text)
        self.assertIn("video.demo.doom.verify=doomgeneric-sd-wad", text)
        self.assertIn("video.demo.doom.play=doomgeneric-sd-wad-smoke", text)
        self.assertIn("video.demo.doom.play.verify.sha256_match=%d", text)

    def test_menu_exposes_sd_wad_commands_without_launching_play(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c").read_text(encoding="utf-8")

        self.assertIn("menu.demo.doom.action=visible-frame-preview", text)
        self.assertIn("menu.demo.doom.asset.wad.runtime_path=%s", text)
        self.assertIn("menu.demo.doom.asset.wad.expected_sha256=%s", text)
        self.assertIn("menu.demo.doom.verify.command=video demo doom verify --wad runtime-private --sha256", text)
        self.assertIn("menu.demo.doom.sd_wad_play.command=video demo doom play [frames] --wad runtime-private --sha256", text)
        self.assertIn("menu.demo.doom.frame.command=video demo doom frame 8 --wad runtime-private --sha256", text)

    def test_builder_contract_uses_sd_wad_metadata_and_no_wad_ramdisk_payload(self) -> None:
        self.assertEqual(runner.CYCLE, "V3029")
        self.assertEqual(runner.INIT_VERSION, "0.10.74")
        self.assertEqual(runner.INIT_BUILD, "v3029-doomgeneric-sd-wad-command")
        self.assertEqual(runner.RUNTIME_WAD_PATH, "/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD")
        self.assertEqual(runner.EXPECTED_WAD_SHA256, "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3029")
        self.assertIn(b"--wad-smoke", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.verify=doomgeneric-sd-wad", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.play=doomgeneric-sd-wad-smoke", runner.REQUIRED_STRINGS)
        self.assertFalse(runner.ENGINE_RAMDISK_PATH.lower().endswith(".wad"))
        self.assertEqual(runner.count_wad_entries(["init", runner.ENGINE_RAMDISK_PATH]), 0)
        self.assertEqual(runner.count_wad_entries(["mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD"]), 1)

    def test_adapter_source_runs_bounded_wad_smoke_against_sd_path(self) -> None:
        source = runner.v3029_adapter_source()

        self.assertIn('/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD', source)
        self.assertIn("a90.doomgeneric.v3029.sd_wad_command=1", source)
        self.assertIn("a90.doomgeneric.v3029.wad_smoke=bounded", source)
        self.assertIn("a90_doomgeneric_run_wad_smoke", source)
        self.assertIn("doomgeneric_Create(7, argv)", source)
        self.assertIn("doomgeneric_Tick()", source)
        self.assertIn('strcmp(argv[1], "--wad-smoke") == 0', source)
        self.assertIn('strcmp(argv[3], "--frames") == 0', source)
        self.assertNotIn("/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD", source)

    def test_report_template_records_v3030_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3029.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_sd_wad_command": {
                "runtime_wad_root": runner.RUNTIME_WAD_ROOT,
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "runtime_wad_max_bytes": runner.RUNTIME_WAD_MAX_BYTES,
                "ramdisk_wad_file_count": 0,
                "public_wad_file_count": 0,
                "wad_embedded_in_boot": 0,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3029/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
                "helper_smoke_command": "helper --wad-smoke",
            },
            "v3029_marker_strings": [
                "v3029-doomgeneric-sd-wad-command",
                "video demo doom verify --wad runtime-private --sha256",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3029 DOOMGENERIC SD WAD Command Source Build", report)
        self.assertIn("WAD files in ramdisk: `0`", report)
        self.assertIn("WAD bytes embedded in boot image: `0`", report)
        self.assertIn("video demo doom verify --wad runtime-private --sha256", report)
        self.assertIn("Run ID: `V3030`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
