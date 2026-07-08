import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m27_hs_prefix_narrow_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM27HsPrefixNarrowLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_marker_check_rejects_missing_ack_and_dtbo_scope(self):
        missing = self.module.missing_policy_markers("S22+ M27 HS prefix-narrow native-init boot+DTBO batch")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("DTBO high-speed cap", missing)
        self.assertIn("stock DTBO rollback", missing)
        self.assertIn("manual download-mode rollback", missing)
        self.assertIn("wait for the original Odin endpoint to disconnect", missing)
        self.assertIn("stop on first no-hit", missing)

    def test_expected_prefix_narrow_batch_is_restricted(self):
        labels = [candidate.label for candidate in self.module.EXPECTED_M27_BATCH]
        self.assertEqual(labels, ["P08", "P12", "P16", "P20", "P22", "P23", "P24"])
        self.assertEqual([candidate.count for candidate in self.module.EXPECTED_M27_BATCH], [8, 12, 16, 20, 22, 23, 24])
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            self.module.selected_candidates(["P25"])
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            self.module.selected_candidates(["P00"])
        with self.assertRaisesRegex(SystemExit, "duplicate"):
            self.module.selected_candidates(["P08", "P08"])

    def test_expected_candidate_hashes_are_pinned(self):
        by_label = self.module.EXPECTED_M27_BY_LABEL
        self.assertEqual(
            by_label["P08"].ap_sha256,
            "60669383e0345dfc5b7f50393ad6aebd3c67307ba32bc107c69eb324d67f499a",
        )
        self.assertEqual(
            by_label["P12"].boot_sha256,
            "02cdc8b95209559618e7e2da0caa6124d24b9f25d5d5b41fe3dce2fa4294a9a3",
        )
        self.assertEqual(
            by_label["P20"].init_sha256,
            "01f88c744d59790991a98e74cec9550803c656c28e29c8daeb51dbe5baafc2b0",
        )
        self.assertEqual(
            by_label["P24"].ap_sha256,
            "fff7ecf3ff9233f76ac17f07ecf56a383696d6ecb06b67f84ef39d8f08876180",
        )

    def test_current_agents_file_contains_m27_live_exception_markers(self):
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        missing = self.module.missing_policy_markers(agents)
        self.assertEqual(missing, [])

    @unittest.skipUnless(MANIFEST.exists(), "private M27 manifest missing")
    def test_top_manifest_verifier_accepts_current_m27_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m27_top_manifest(MANIFEST, Path("/tmp/unused-m27-live-gate-test.log"))

    @unittest.skipUnless(MANIFEST.exists(), "private M27 manifest missing")
    def test_prefix_manifest_verifier_accepts_first_live_batch(self):
        root = Path.cwd()
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            for candidate in self.module.EXPECTED_M27_BATCH:
                self.module.verify_m27_prefix_manifest(root, candidate, Path("/tmp/unused-m27-live-gate-test.log"))

    def test_timeline_schema_reused_is_canonical_events_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.module.record_timeline_event(run_dir, "live_session_start")
            self.module.record_timeline_event(run_dir, "P08_candidate_flash_start")
            data = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(sorted(data.keys()), ["events"])
        self.assertEqual([event["name"] for event in data["events"]], ["live_session_start", "P08_candidate_flash_start"])
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
