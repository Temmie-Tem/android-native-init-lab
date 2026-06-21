from __future__ import annotations

import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3051_doomgeneric_autostart_probe_fix.py")


class NativeDoomgenericAutostartProbeFixSourceV3051Tests(unittest.TestCase):
    def test_builder_contract_pins_v3051_probe_fix_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3051")
        self.assertEqual(runner.INIT_VERSION, "0.10.84")
        self.assertEqual(runner.INIT_BUILD, "v3051-doomgeneric-autostart-probe-fix")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3051")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3051-autostart-probe-fix")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3051-autostart-probe-fix-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3051-input.state")
        self.assertIn(b"a90.doomgeneric.v3051.probe=autostart-argv12", runner.REQUIRED_STRINGS)

    def test_adapter_source_updates_native_probe_to_autostart_arg_contract(self) -> None:
        source = runner.v3051_adapter_source()

        self.assertIn("a90.doomgeneric.v3051.probe=autostart-argv12", source)
        self.assertIn("char *argv[13] = {0};", source)
        self.assertIn("a90_doomgeneric_prepare_argv(argv, 13)", source)
        self.assertIn("argc != 12", source)
        self.assertIn('strcmp(argv[7], "-warp")', source)
        self.assertIn('strcmp(argv[8], "1")', source)
        self.assertIn('strcmp(argv[9], "1")', source)
        self.assertIn('strcmp(argv[10], "-skill")', source)
        self.assertIn('strcmp(argv[11], "2")', source)
        self.assertIn("doomgeneric_Create(12, argv);", source)

    def test_report_template_records_v3052_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3051.img",
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
                "v3051-doomgeneric-autostart-probe-fix",
                "a90.doomgeneric.v3051.probe=autostart-argv12",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3051 DOOMGENERIC Autostart Probe Fix Source Build", report)
        self.assertIn("Run ID: `V3052`", report)
        self.assertIn("engine-probe `rc=0`", report)


if __name__ == "__main__":
    unittest.main()
