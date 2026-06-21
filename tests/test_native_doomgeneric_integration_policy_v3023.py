from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_integration_policy_v3023.py")


class NativeDoomgenericIntegrationPolicyV3023Tests(unittest.TestCase):
    def test_collect_state_promotes_private_source_integration_policy(self) -> None:
        state = runner.collect_state()
        source = state["source"]

        self.assertEqual(state["run_id"], "V3023")
        self.assertEqual(state["decision"], "v3023-doomgeneric-private-integration-policy-ready")
        self.assertTrue(source["source_exists"])
        self.assertEqual(source["git_head"], runner.PINNED_COMMIT)
        self.assertTrue(source["git_head_matches_pin"])
        self.assertTrue(source["git_status_clean"])
        self.assertTrue(state["reports"]["v3020_port_probe_pass"])
        self.assertTrue(state["reports"]["v3022_demo_checkpoint_pass"])
        self.assertEqual(state["public_wads"]["count"], 0)
        self.assertEqual(state["private_wads"]["count"], 0)
        self.assertFalse(state["live_wad_ready"])
        self.assertEqual(
            state["source_handling_policy"]["next_step"],
            "private-build-only-native-init-integration",
        )
        self.assertEqual(state["build_policy"]["next_run_id"], "V3024")
        self.assertTrue(state["safe_to_continue_host_only"])

    def test_asset_and_command_policy_keep_wads_runtime_private(self) -> None:
        state = runner.collect_state()

        self.assertFalse(state["asset_policy"]["commit_wad"])
        self.assertFalse(state["asset_policy"]["embed_wad_in_boot_image"])
        self.assertEqual(state["asset_policy"]["boot_image_wad_byte_limit"], 0)
        self.assertEqual(state["asset_policy"]["runtime_wad_root"], "/cache/a90-runtime/pkg/doom/v3024/")
        self.assertEqual(state["command_surface_policy"]["default_play_frames"], 300)
        self.assertEqual(state["command_surface_policy"]["max_play_frames"], 5400)
        self.assertIn("runtime-private", state["command_surface_policy"]["verify"])
        self.assertIn("runtime-private", state["command_surface_policy"]["play"])
        self.assertFalse(state["port_policy"]["touch_or_otg_required"])
        self.assertFalse(state["port_policy"]["evdev_injection"])

    def test_render_report_records_selector_markers(self) -> None:
        report = runner.render_report(runner.collect_state())

        self.assertIn("Native Init V3023 DOOMGENERIC Integration Policy", report)
        self.assertIn("v3023-doomgeneric-private-integration-policy-ready", report)
        self.assertIn("Private doomgeneric source pinned: `1`", report)
        self.assertIn("V3020 port probe pass: `1`", report)
        self.assertIn("Public WAD files committed/present: `0`", report)
        self.assertIn("Runtime WAD currently staged: `0`", report)
        self.assertIn("Safe next host-only unit: `1`", report)
        self.assertIn("Public vendoring is deferred", report)
        self.assertIn("Run ID: `V3024`", report)

    def test_count_files_reports_counts_without_file_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DOOM1.WAD").write_bytes(b"wad")
            (root / "ignore.txt").write_text("ignore", encoding="utf-8")

            result = runner.count_files(root, ".wad")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total_bytes"], len(b"wad"))
        self.assertNotIn("DOOM1.WAD", str(result))
        self.assertNotIn("files", result)


if __name__ == "__main__":
    unittest.main()
