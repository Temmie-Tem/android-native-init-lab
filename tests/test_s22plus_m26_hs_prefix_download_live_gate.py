import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m26_hs_prefix_download_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m26_hs_prefix_download_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m26_hs_prefix_download_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM26HsPrefixDownloadLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_marker_check_rejects_missing_ack_and_dtbo_scope(self):
        missing = self.module.missing_policy_markers("S22+ M26 HS prefix-download native-init boot+DTBO batch")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("DTBO high-speed cap", missing)
        self.assertIn("stock DTBO rollback", missing)
        self.assertIn("manual download-mode rollback", missing)
        self.assertIn("wait for the original Odin endpoint to disconnect", missing)

    def test_expected_first_live_batch_is_restricted(self):
        labels = [candidate.label for candidate in self.module.EXPECTED_M26_BATCH]
        self.assertEqual(labels, ["P00", "P24", "P27", "P30"])
        self.assertEqual([candidate.count for candidate in self.module.EXPECTED_M26_BATCH], [0, 24, 27, 30])
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            self.module.selected_candidates(["P25"])
        with self.assertRaisesRegex(SystemExit, "duplicate"):
            self.module.selected_candidates(["P00", "P00"])

    def test_expected_candidate_hashes_are_pinned(self):
        by_label = self.module.EXPECTED_M26_BY_LABEL
        self.assertEqual(
            by_label["P00"].ap_sha256,
            "1f8763c5f08461bb351f1b461898bf568652e292c79aef9e1f46fb9af4bbd79b",
        )
        self.assertEqual(
            by_label["P24"].boot_sha256,
            "ff231f7fdb410a8fa3489cd63bc8d2f9f539dc823a4086f5917e75a1b24b7af8",
        )
        self.assertEqual(
            by_label["P27"].init_sha256,
            "5289ef3bdb344fa09e8a18d0183b8d7d4ce5c98d4eb83fe0f68813d5bf444a22",
        )
        self.assertEqual(
            by_label["P30"].ap_sha256,
            "a4510148c14652ffd87c8c0c6dd2ec1b127a36136ed1d28849bba04028ea8c9c",
        )

    @unittest.skipUnless(MANIFEST.exists(), "private M26 manifest missing")
    def test_top_manifest_verifier_accepts_current_m26_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m26_top_manifest(MANIFEST, Path("/tmp/unused-m26-live-gate-test.log"))

    @unittest.skipUnless(MANIFEST.exists(), "private M26 manifest missing")
    def test_prefix_manifest_verifier_accepts_first_live_batch(self):
        root = Path.cwd()
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            for candidate in self.module.EXPECTED_M26_BATCH:
                self.module.verify_m26_prefix_manifest(root, candidate, Path("/tmp/unused-m26-live-gate-test.log"))

    def test_timeline_schema_reused_is_canonical_events_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.module.record_timeline_event(run_dir, "live_session_start")
            self.module.record_timeline_event(run_dir, "P00_candidate_flash_start")
            data = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(sorted(data.keys()), ["events"])
        self.assertEqual([event["name"] for event in data["events"]], ["live_session_start", "P00_candidate_flash_start"])
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
