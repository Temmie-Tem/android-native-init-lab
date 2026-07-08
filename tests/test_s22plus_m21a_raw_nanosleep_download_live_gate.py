import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_raw_nanosleep_download_m21a.S")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m21a_raw_nanosleep_download_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m21a_raw_nanosleep_download_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM21ARawNanosleepDownloadLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_current_agents_file_retires_consumed_m30_m21a_policy(self):
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        missing = self.module.missing_policy_markers(agents)
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn("no Odin endpoint before the 90 second dwell threshold", missing)
        self.assertIn("Consumed exception (2026-07-09, S22+ M30/M21A", agents)
        self.assertIn("Retired unconsumed exception (2026-07-08, S22+ M21A", agents)

    def test_expected_hashes_and_runtime_constants_are_pinned(self):
        self.assertEqual(self.module.EXPECTED_DWELL_SEC, 90)
        self.assertEqual(
            self.module.EXPECTED_M21A_AP_SHA256,
            "d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79",
        )
        self.assertEqual(
            self.module.EXPECTED_M21A_BOOT_SHA256,
            "61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5",
        )
        self.assertEqual(
            self.module.EXPECTED_M21A_INIT_SHA256,
            "10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30",
        )

    def test_source_is_raw_nanosleep_download_only(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD", text)
        self.assertIn("mov     x8, #101", text)
        self.assertIn("mov     x8, #142", text)
        self.assertIn(".xword 90", text)
        self.assertNotIn("/dev/kmsg", text)
        self.assertNotIn("/lib/modules", text)
        self.assertNotIn("finit_module", text)
        self.assertNotIn("usb_gadget", text)
        self.assertNotIn("/config", text)

    def test_observe_timed_download_rejects_early_odin(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "log.txt"
            with (
                patch.object(self.module, "host_snapshot", lambda *_args, **_kwargs: None),
                patch.object(self.module, "odin_devices", return_value=["/dev/bus/usb/001/002"]),
                patch.object(self.module, "adb_rows", return_value=[]),
                patch.object(self.module.time, "monotonic", side_effect=[0.0, 5.0, 5.0]),
                patch.object(self.module.time, "sleep", lambda _seconds: None),
            ):
                result, device = self.module.observe_timed_download(
                    run_dir,
                    log_path,
                    odin=Path("/tmp/odin4"),
                    dwell_sec=90,
                    dwell_grace_sec=30,
                )

        self.assertEqual(result, "early-odin-before-dwell")
        self.assertEqual(device, "/dev/bus/usb/001/002")

    def test_observe_timed_download_accepts_post_dwell_odin(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "log.txt"
            with (
                patch.object(self.module, "host_snapshot", lambda *_args, **_kwargs: None),
                patch.object(self.module, "odin_devices", return_value=["/dev/bus/usb/001/002"]),
                patch.object(self.module, "adb_rows", return_value=[]),
                patch.object(self.module.time, "monotonic", side_effect=[0.0, 95.0, 95.0]),
                patch.object(self.module.time, "sleep", lambda _seconds: None),
            ):
                result, device = self.module.observe_timed_download(
                    run_dir,
                    log_path,
                    odin=Path("/tmp/odin4"),
                    dwell_sec=90,
                    dwell_grace_sec=30,
                )

        self.assertEqual(result, "timed-download-after-dwell")
        self.assertEqual(device, "/dev/bus/usb/001/002")

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

    @unittest.skipUnless(MANIFEST.exists(), "private M21A manifest missing")
    def test_manifest_verifier_accepts_current_m21a_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m21a_manifest(MANIFEST, Path("/tmp/unused-m21a-live-gate-test.log"))


if __name__ == "__main__":
    unittest.main()
