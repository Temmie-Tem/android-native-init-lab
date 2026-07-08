import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m28_dep_complete_download_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m28_dep_complete_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM28DepCompleteLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_marker_check_rejects_missing_ack_and_dtbo_scope(self):
        missing = self.module.missing_policy_markers("S22+ M28 dependency-complete native-init boot+DTBO batch")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("DTBO high-speed cap", missing)
        self.assertIn("stock DTBO rollback", missing)
        self.assertIn("manual download-mode rollback", missing)
        self.assertIn("wait for the original Odin endpoint to disconnect", missing)
        self.assertIn("S24 first", missing)
        self.assertIn("do not run F43 if S24 fails", missing)
        self.assertIn("stop on first no-hit", missing)

    def test_expected_dep_complete_batch_is_restricted_and_ordered(self):
        labels = [candidate.label for candidate in self.module.EXPECTED_M28_BATCH]
        self.assertEqual(labels, ["S24", "F43"])
        self.assertEqual([candidate.module_count for candidate in self.module.EXPECTED_M28_BATCH], [26, 43])
        self.assertEqual([candidate.label for candidate in self.module.selected_candidates(["S24"])], ["S24"])
        self.assertEqual([candidate.label for candidate in self.module.selected_candidates(["S24", "F43"])], ["S24", "F43"])
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            self.module.selected_candidates(["P08"])
        with self.assertRaisesRegex(SystemExit, "ordered sequence"):
            self.module.selected_candidates(["F43"])
        with self.assertRaisesRegex(SystemExit, "duplicate"):
            self.module.selected_candidates(["S24", "S24"])

    def test_expected_candidate_hashes_are_pinned(self):
        by_label = self.module.EXPECTED_M28_BY_LABEL
        self.assertEqual(
            by_label["S24"].ap_sha256,
            "c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f",
        )
        self.assertEqual(
            by_label["S24"].modules_sha256,
            "8c605e2c69aad74f80191bdbc1843b002539d22d49bcffa86bb85bbcb343e5e4",
        )
        self.assertEqual(
            by_label["F43"].boot_sha256,
            "6453b8f2dd685757148056ba8767c2820b0547123f4e5e5e423c4adb0c70496c",
        )
        self.assertEqual(
            by_label["F43"].reincluded_hard_suppliers,
            ("sec_debug.ko", "minidump.ko", "abc.ko"),
        )

    def test_current_agents_file_authorizes_exact_m28_live_gate_policy(self):
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        missing = self.module.missing_policy_markers(agents)
        self.assertEqual(missing, [])

    @unittest.skipUnless(MANIFEST.exists(), "private M28 manifest missing")
    def test_top_manifest_verifier_accepts_current_m28_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m28_top_manifest(MANIFEST, Path("/tmp/unused-m28-live-gate-test.log"))

    @unittest.skipUnless(MANIFEST.exists(), "private M28 manifest missing")
    def test_variant_manifest_verifier_accepts_first_live_batch(self):
        root = Path.cwd()
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            for candidate in self.module.EXPECTED_M28_BATCH:
                self.module.verify_m28_variant_manifest(root, candidate, Path("/tmp/unused-m28-live-gate-test.log"))

    def test_timeline_schema_reused_is_canonical_events_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.module.record_timeline_event(run_dir, "live_session_start")
            self.module.record_timeline_event(run_dir, "S24_candidate_flash_start")
            data = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(sorted(data.keys()), ["events"])
        self.assertEqual([event["name"] for event in data["events"]], ["live_session_start", "S24_candidate_flash_start"])
        for event in data["events"]:
            self.assertEqual(sorted(event.keys()), ["name", "timestamp_utc"])
            self.assertTrue(event["timestamp_utc"].endswith("Z"))

    def test_restore_stock_dtbo_if_needed_refuses_unknown_hash(self):
        with patch.object(self.module, "read_partition_hash", return_value="0" * 64):
            with self.assertRaisesRegex(SystemExit, "unexpected DTBO hash"):
                self.module.restore_stock_dtbo_if_needed(
                    odin=Path("/tmp/odin4"),
                    dtbo_rollback_ap=Path("/tmp/dtbo.tar.md5"),
                    run_dir=Path("/tmp"),
                    log_path=Path("/tmp/log.txt"),
                    serial="ADB123",
                    odin_wait_sec=1,
                    android_wait_sec=1,
                )

    def test_restore_stock_dtbo_if_needed_skips_stock(self):
        with (
            patch.object(self.module, "read_partition_hash", return_value=self.module.EXPECTED_STOCK_DTBO_RAW_SHA256),
            patch.object(self.module, "restore_dtbo_from_android") as restore,
            patch.object(self.module, "append_log", lambda *_args, **_kwargs: None),
        ):
            rc = self.module.restore_stock_dtbo_if_needed(
                odin=Path("/tmp/odin4"),
                dtbo_rollback_ap=Path("/tmp/dtbo.tar.md5"),
                run_dir=Path("/tmp"),
                log_path=Path("/tmp/log.txt"),
                serial="ADB123",
                odin_wait_sec=1,
                android_wait_sec=1,
            )
        self.assertEqual(rc, 0)
        restore.assert_not_called()


if __name__ == "__main__":
    unittest.main()
