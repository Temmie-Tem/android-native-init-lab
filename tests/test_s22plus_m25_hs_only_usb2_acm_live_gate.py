import importlib.util
import io
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py")
DRAFT = Path("docs/operations/S22PLUS_M25_HS_ONLY_USB2_ACM_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m25_hs_only_usb2_acm_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM25HsOnlyUsb2AcmLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_dtbo_scope(self):
        missing = self.module.missing_policy_markers("S22+ M25 HS-only USB2 ACM native-init boot+DTBO")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("DTBO high-speed cap", missing)
        self.assertIn("phy-msm-ssusb-qmp.ko intentionally excluded", missing)
        self.assertIn("stock DTBO rollback", missing)
        self.assertIn("manual download-mode rollback", missing)

    def test_expected_candidate_hashes_are_pinned(self):
        self.assertEqual(
            self.module.EXPECTED_M25_BOOT_AP_SHA256,
            "7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_BOOT_SHA256,
            "0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_DTBO_AP_SHA256,
            "35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_PATCHED_DTBO_RAW_SHA256,
            "8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17",
        )

    def test_hs_only_module_policy_excludes_fault_path(self):
        modules = set(self.module.EXPECTED_M25_MODULES)
        self.assertEqual(len(modules), 40)
        self.assertIn("phy-msm-snps-hs.ko", modules)
        self.assertIn("phy-msm-snps-eusb2.ko", modules)
        self.assertIn("dwc3-msm.ko", modules)
        self.assertNotIn("phy-msm-ssusb-qmp.ko", modules)
        self.assertNotIn("eud.ko", modules)
        self.assertNotIn("ucsi_glink.ko", modules)
        self.assertNotIn("qcom_wdt_core.ko", modules)

    @unittest.skipUnless(MANIFEST.exists(), "private M25 manifest missing")
    def test_manifest_verifier_accepts_current_m25_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m25_manifest(MANIFEST, Path("/tmp/unused-m25-live-gate-test.log"))

    def test_read_partition_hash_uses_direct_sha_not_pipe(self):
        commands = []

        def adb_shell(command, *, serial, timeout):
            commands.append((command, serial, timeout))
            return SimpleNamespace(
                returncode=0,
                stdout=f"{self.module.EXPECTED_BASE_BOOT_SHA256}  /dev/block/by-name/boot\n",
                stderr="",
            )

        with patch.object(self.module, "adb_shell", adb_shell), patch.object(
            self.module, "append_log", lambda *_args, **_kwargs: None
        ):
            actual = self.module.read_partition_hash(Path("/tmp/unused.log"), "ADB123", "boot", "current")

        self.assertEqual(actual, self.module.EXPECTED_BASE_BOOT_SHA256)
        self.assertEqual(len(commands), 1)
        self.assertIn("sha256sum /dev/block/by-name/boot", commands[0][0])
        self.assertIn("toybox sha256sum /dev/block/by-name/boot", commands[0][0])
        self.assertLess(commands[0][0].find("toybox sha256sum"), commands[0][0].find("sha256sum /dev/block/by-name/boot"))
        self.assertNotIn("dd if=", commands[0][0])
        self.assertNotIn(" | sha256sum", commands[0][0])

    def test_read_partition_hash_rejects_unsafe_partition_name(self):
        with self.assertRaisesRegex(SystemExit, "unsafe partition name"):
            self.module.read_partition_hash(Path("/tmp/unused.log"), "ADB123", "boot;reboot", "current")

    def test_record_timeline_event_writes_canonical_events_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.module.record_timeline_event(run_dir, "live_session_start")
            self.module.record_timeline_event(run_dir, "candidate_flash_start")
            data = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(sorted(data.keys()), ["events"])
        self.assertEqual([event["name"] for event in data["events"]], ["live_session_start", "candidate_flash_start"])
        for event in data["events"]:
            self.assertEqual(sorted(event.keys()), ["name", "timestamp_utc"])
            self.assertTrue(event["timestamp_utc"].endswith("Z"))

    def test_record_timeline_event_rejects_noncanonical_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timeline.json"
            path.write_text(json.dumps({"events": [], "steps": []}), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "non-canonical timeline shape"):
                self.module.record_timeline_event(Path(tmp), "live_session_start")

    def test_record_timeline_event_rejects_noncanonical_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timeline.json"
            path.write_text(
                json.dumps({"events": [{"name": "live_session_start", "timestamp_utc": "bad"}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "invalid timestamp"):
                self.module.record_timeline_event(Path(tmp), "live_session_end")

    def test_restore_dtbo_from_android_mode_records_session_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            odin = Path(tmp) / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")

            with (
                patch.object(self.module, "verify_ap", lambda *_args, **_kwargs: None),
                patch.object(self.module, "verify_ap_member", lambda *_args, **_kwargs: None),
                patch.object(self.module, "verify_m25_manifest", lambda *_args, **_kwargs: None),
                patch.object(self.module, "verify_agents_exception", lambda *_args, **_kwargs: None),
                patch.object(self.module, "require_current_android", return_value="ADB123"),
                patch.object(self.module, "verify_android_stability", lambda *_args, **_kwargs: None),
                patch.object(self.module, "verify_partition_hash", lambda *_args, **_kwargs: None),
                patch.object(self.module, "restore_dtbo_from_android", return_value=0),
                patch("sys.stdout", new_callable=io.StringIO),
            ):
                rc = self.module.main(
                    [
                        "--restore-dtbo-from-android",
                        "--ack",
                        self.module.RESTORE_DTBO_ACK_TOKEN,
                        "--run-dir",
                        str(run_dir),
                        "--odin",
                        str(odin),
                    ]
                )

            data = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual([event["name"] for event in data["events"]], ["live_session_start", "live_session_end"])

    def test_magisk_rollback_verifies_magisk_boot_hash_before_dtbo_restore(self):
        events = []
        verify_calls = []

        def record_event(_run_dir, name):
            events.append(name)

        def verify_hash(_log_path, _serial, partition, expected_sha, label):
            verify_calls.append((partition, expected_sha, label))

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "log.txt"
            with (
                patch.object(self.module, "record_timeline_event", record_event),
                patch.object(self.module, "flash_ap", return_value=0),
                patch.object(self.module, "poll_android", return_value="ADB123"),
                patch.object(self.module, "verify_partition_hash", verify_hash),
                patch.object(self.module, "capture_post_boot_rollback_surfaces", return_value={}),
                patch.object(self.module, "restore_dtbo_from_android", return_value=0),
            ):
                rc = self.module.rollback_boot_from_odin_device(
                    odin=Path("/tmp/odin4"),
                    boot_rollback_ap=Path("/tmp/magisk-ap.tar.md5"),
                    stock_boot_fallback_ap=Path("/tmp/stock-ap.tar.md5"),
                    dtbo_rollback_ap=Path("/tmp/dtbo-ap.tar.md5"),
                    odin_device="/dev/bus/usb/001/002",
                    run_dir=run_dir,
                    log_path=log_path,
                    rollback_target=self.module.ROLLBACK_MAGISK,
                    odin_wait_sec=1,
                    android_wait_sec=1,
                )

        self.assertEqual(rc, 0)
        self.assertIn("rollback_boot_ready", events)
        self.assertIn(("boot", self.module.EXPECTED_BASE_BOOT_SHA256, "boot_restore"), verify_calls)

    def test_stock_rollback_skips_root_boot_hash_check(self):
        events = []
        verify_calls = []

        def record_event(_run_dir, name):
            events.append(name)

        def verify_hash(_log_path, _serial, partition, expected_sha, label):
            verify_calls.append((partition, expected_sha, label))

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "log.txt"
            with (
                patch.object(self.module, "record_timeline_event", record_event),
                patch.object(self.module, "flash_ap", return_value=0),
                patch.object(self.module, "poll_android", return_value="ADB123"),
                patch.object(self.module, "verify_partition_hash", verify_hash),
                patch.object(self.module, "capture_post_boot_rollback_surfaces", return_value={}),
                patch.object(self.module, "restore_dtbo_from_android", return_value=0),
            ):
                rc = self.module.rollback_boot_from_odin_device(
                    odin=Path("/tmp/odin4"),
                    boot_rollback_ap=Path("/tmp/stock-ap.tar.md5"),
                    stock_boot_fallback_ap=Path("/tmp/stock-ap.tar.md5"),
                    dtbo_rollback_ap=Path("/tmp/dtbo-ap.tar.md5"),
                    odin_device="/dev/bus/usb/001/002",
                    run_dir=run_dir,
                    log_path=log_path,
                    rollback_target=self.module.ROLLBACK_STOCK,
                    odin_wait_sec=1,
                    android_wait_sec=1,
                )
            log_text = log_path.read_text(encoding="utf-8")

        self.assertEqual(rc, 0)
        self.assertIn("rollback_boot_ready", events)
        self.assertNotIn("boot", [call[0] for call in verify_calls])
        self.assertIn("boot_restore_hash_check=skipped rollback_target=stock", log_text)


if __name__ == "__main__":
    unittest.main()
