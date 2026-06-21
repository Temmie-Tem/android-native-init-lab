from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_feasibility_v3019.py")


class NativeDoomgenericFeasibilityV3019Tests(unittest.TestCase):
    def test_collect_state_matches_current_frontier(self) -> None:
        state = runner.collect_state()

        self.assertEqual(state["run_id"], "V3019")
        self.assertEqual(state["decision"], "v3019-doomgeneric-feasibility-host-pass")
        self.assertTrue(state["v3017_doompad_loop_proven"])
        self.assertTrue(state["goal_v3017_frontier_current"])
        self.assertTrue(state["current_native_status_not_wad_backed"])
        self.assertTrue(state["doompad_consumer_source_present"])
        self.assertFalse(state["source_vendored"])
        self.assertEqual(state["public_wads"]["count"], 0)
        self.assertFalse(state["asset_policy"]["commit_wad"])
        self.assertFalse(state["asset_policy"]["embed_wad_in_boot_image"])
        self.assertTrue(state["safe_to_continue_host_only"])

    def test_size_baseline_records_boot_delta_when_artifacts_exist(self) -> None:
        state = runner.collect_state()
        sizes = state["sizes"]

        self.assertIsInstance(sizes["rollback_boot_image_bytes"], int)
        self.assertIsInstance(sizes["v3016_boot_image_bytes"], int)
        self.assertEqual(
            sizes["v3016_boot_delta_vs_rollback_bytes"],
            sizes["v3016_boot_image_bytes"] - sizes["rollback_boot_image_bytes"],
        )

    def test_render_report_records_policy_sources_and_next_unit(self) -> None:
        state = runner.collect_state()
        report = runner.render_report(state)

        self.assertIn("Native Init V3019 DOOMGENERIC Feasibility Audit", report)
        self.assertIn("v3019-doomgeneric-feasibility-host-pass", report)
        self.assertIn("https://github.com/id-Software/DOOM", report)
        self.assertIn("https://github.com/ozkl/doomgeneric", report)
        self.assertIn("/cache/a90-runtime/pkg/doom/v3020/", report)
        self.assertIn("WAD/IWAD data must not be committed", report)
        self.assertIn("Current native status is not WAD-backed: `1`", report)
        self.assertIn("Safe next unit: `1`", report)

    def test_count_files_reports_counts_without_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wad = root / "DOOM1.WAD"
            ignored = root / "readme.txt"
            wad.write_bytes(b"wad-bytes")
            ignored.write_text("ignore", encoding="utf-8")

            result = runner.count_files(root, ".WAD")

        self.assertTrue(result["exists"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total_bytes"], len(b"wad-bytes"))
        self.assertNotIn("files", result)
        self.assertNotIn("DOOM1.WAD", str(result))


if __name__ == "__main__":
    unittest.main()
