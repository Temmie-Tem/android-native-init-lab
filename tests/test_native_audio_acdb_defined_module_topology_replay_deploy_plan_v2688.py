import tempfile
import unittest
from pathlib import Path

import native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688 as v2688


class V2688DeployPlanTests(unittest.TestCase):
    def test_build_plan_replaces_only_cal10_and_cal14_basic_payloads(self):
        plan = v2688.build_plan(v2688.DEFAULT_BASE_MANIFEST, v2688.DEFAULT_CANDIDATE_DIR)
        self.assertTrue(plan["native_replay_ready"])
        self.assertEqual(plan["run_id"], "V2688")
        self.assertEqual(plan["summary"]["cal_order"], [39, 10, 14, 24, 13, 9, 11, 12, 15, 23, 16, 21])
        entries = {entry["cal_type"]: entry for entry in plan["replay_entries"] if entry["entry_kind"] == "basic-payload"}
        self.assertIn("DEFINED_MODULES_ONLY", entries[10]["role"])
        self.assertIn("DEFINED_MODULES_ONLY", entries[14]["role"])
        self.assertEqual(entries[14]["removed_module_ids"], [0x10001F30, 0x10001F10])
        self.assertNotIn("DEFINED_MODULES_ONLY", entries[39]["role"])

    def test_remote_paths_move_to_v2688_runtime_dir(self):
        plan = v2688.build_plan(v2688.DEFAULT_BASE_MANIFEST, v2688.DEFAULT_CANDIDATE_DIR)
        blob = str(plan)
        self.assertIn("/cache/a90-acdb-setcal-replay-v2688", blob)
        self.assertNotIn("/cache/a90-acdb-setcal-replay-v2684", blob)
        self.assertIn("01-defined-modules-payload-cal10-topo10004000.bin", blob)
        self.assertIn("02-defined-modules-payload-cal14-topo10005000.bin", blob)

    def test_cli_writes_private_manifest_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "deploy-plan.json"
            report = Path(tmp) / "report.md"
            plan = v2688.build_plan(v2688.DEFAULT_BASE_MANIFEST, v2688.DEFAULT_CANDIDATE_DIR)
            v2688.write_json(manifest, plan, mode=0o600)
            report.write_text(v2688.markdown(plan), encoding="utf-8")
            self.assertTrue(manifest.exists())
            self.assertEqual(oct(manifest.stat().st_mode & 0o777), "0o600")
            self.assertIn("V2688", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
