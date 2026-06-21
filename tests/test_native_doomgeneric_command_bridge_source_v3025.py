from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3025_doomgeneric_command_bridge.py")
ROOT = REPO_ROOT


class NativeDoomgenericCommandBridgeSourceV3025Tests(unittest.TestCase):
    def test_bridge_module_reports_private_helper_without_public_wad_or_uinput(self) -> None:
        header = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        source = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        combined = header + source

        self.assertIn("v3025-doomgeneric-command-bridge", combined)
        self.assertIn("doomgeneric-private-link-v3025", combined)
        self.assertIn("/bin/a90_doomgeneric_private_engine_v3024", combined)
        self.assertIn("/cache/a90-runtime/pkg/doom/v3024/", combined)
        self.assertIn("serial-doompad-to-DG_GetKey", combined)
        self.assertIn("disabled-nosound-nomusic", combined)
        self.assertIn("a90_doomgeneric_bridge_probe", combined)
        self.assertNotIn("/dev/input", combined)
        self.assertNotIn("uinput", combined.lower())
        self.assertNotIn("native_init_flash.py", combined)
        self.assertNotIn("/efs", combined)

    def test_video_doom_status_adds_active_bridge_and_probe_markers(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn('a90_console_printf("video.demo.engine=doompad-loop-not-doomgeneric\\r\\n");', text)
        self.assertIn("video_demo_doom_bridge_status", text)
        self.assertIn("video.demo.engine.active=%s", text)
        self.assertIn("video.demo.engine.helper=%s", text)
        self.assertIn("video.demo.asset.wad.embedded_in_boot=%d", text)
        self.assertIn("video.demo.input.otg_required=0", text)
        self.assertIn("video demo doom engine-probe", text)
        self.assertIn("a90_doomgeneric_bridge_probe(3000", text)
        self.assertIn("video.demo.doom.engine_probe.rc=%d", text)

    def test_menu_status_keeps_legacy_doompad_and_exposes_bridge_state(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c").read_text(encoding="utf-8")

        self.assertIn('a90_console_printf("menu.demo.doom.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertIn("menu.demo.doom.engine.active=%s", text)
        self.assertIn("menu.demo.doom.engine.helper=%s", text)
        self.assertIn("menu.demo.doom.input.otg_required=0", text)
        self.assertIn("menu.demo.doom.engine.probe.command=video demo doom engine-probe", text)

    def test_builder_contract_packages_v3024_engine_helper_not_wad_files(self) -> None:
        self.assertEqual(runner.CYCLE, "V3025")
        self.assertEqual(runner.INIT_VERSION, "0.10.73")
        self.assertEqual(runner.INIT_BUILD, "v3025-doomgeneric-command-bridge")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3024")
        self.assertEqual(runner.ENGINE_EXPECTED_SHA256, "8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735")
        self.assertIn(b"video demo doom engine-probe", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey", runner.REQUIRED_STRINGS)
        self.assertFalse(runner.ENGINE_RAMDISK_PATH.lower().endswith(".wad"))
        self.assertEqual(runner.count_wad_entries(["init", runner.ENGINE_RAMDISK_PATH]), 0)
        self.assertEqual(runner.count_wad_entries(["cache/DOOM1.WAD", runner.ENGINE_RAMDISK_PATH]), 1)

    def test_report_template_records_v3026_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3025.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_command_bridge": {
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3024/doom",
                "engine_binary_sha256": runner.ENGINE_EXPECTED_SHA256,
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
                "ramdisk_wad_file_count": 0,
                "runtime_wad_root": runner.RUNTIME_WAD_ROOT,
            },
            "v3025_marker_strings": [
                "v3025-doomgeneric-command-bridge",
                "video demo doom engine-probe",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3025 DOOMGENERIC Command Bridge Source Build", report)
        self.assertIn("WAD files in ramdisk: `0`", report)
        self.assertIn("video demo doom engine-probe", report)
        self.assertIn("Run ID: `V3026`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
