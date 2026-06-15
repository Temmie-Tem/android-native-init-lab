from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import native_audio_acdbtap_live_handoff_v2477 as v2477


class V2477AcdbTapLiveHandoffTests(unittest.TestCase):
    def args(self) -> Namespace:
        return Namespace(
            adb="adb",
            serial=None,
            stage_dir=Path("workspace/private/inputs/audio/acdb-cross-validation/v2476"),
            stimulus_apk=Path("workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk"),
            duration_ms=2000,
            sample_rate=48000,
            amplitude=0.05,
            active_delay_sec=0.75,
            post_delay_sec=1.0,
            capture_observe_sec=8.0,
            android_timeout=240.0,
            adb_command_timeout=45.0,
            flash_timeout=240.0,
            from_native=False,
            android_root_recheck_attempts=4,
            android_root_recheck_sleep_sec=2.0,
        )

    def test_stage_commands_require_preload_confirmation_marker(self) -> None:
        flat = json.dumps(v2477.dry_run_payload(self.args()), sort_keys=True)
        self.assertIn("A90_ACDBTAP_PRELOAD_CONFIRMED", flat)
        self.assertIn("LD_PRELOAD", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertIn("AudioTrack", flat)

    def test_command_safety_rejects_calibration_and_silent_policy(self) -> None:
        safety = v2477.command_safety({"commands": ["AUDIO_ALLOCATE_CALIBRATION", "setenforce 0"]})
        names = {item["name"] for item in safety["findings"]}
        self.assertIn("native_cal_allocate_symbol", names)
        self.assertIn("silent_permissive", names)

    def test_preload_confirmed_reads_step_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stdout.txt"
            path.write_text("x\nA90_ACDBTAP_PRELOAD_CONFIRMED pid=123\n")
            record = {"stdout": str(path)}
            self.assertTrue(v2477.preload_confirmed(record))

    def test_summarize_acdbtap_artifacts_reports_ordered_full_set_without_raw_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cap = out / "acdbtap-device-artifacts"
            cap.mkdir()
            (cap / "acdbtap-events.jsonl").write_text(
                json.dumps({
                    "seq": "0x00000001",
                    "cmd": "0x00012abc",
                    "in_len": "0x00000020",
                    "out_len": "0x00001334",
                    "ret": "0x00000000",
                    "sha256": "a" * 64,
                    "raw_written": True,
                    "is_target_4916": True,
                    "is_size_query_4": False,
                    "raw_path": "/data/local/tmp/a90-acdb-tap/acdbtap.bin",
                }) + "\n" +
                json.dumps({
                    "seq": "0x00000002",
                    "cmd": "0x00004567",
                    "in_len": "0x00000010",
                    "out_len": "0x00000080",
                    "ret": "0x00000000",
                    "sha256": "b" * 64,
                    "raw_written": True,
                    "is_target_4916": False,
                    "is_size_query_4": False,
                    "raw_path": "/data/local/tmp/a90-acdb-tap/acdbtap2.bin",
                }) + "\n"
            )
            (cap / "acdbtap-00000001-cmd-00012abc-len-00001334.bin").write_bytes(b"x")
            (cap / "acdbtap-00000002-cmd-00004567-len-00000080.bin").write_bytes(b"y")
            summary = v2477.summarize_acdbtap_artifacts(out)
            self.assertEqual(summary["classification"], "captured-acdbtap-full-outbuf-set-with-4916")
            self.assertEqual(summary["target_4916_count"], 1)
            self.assertEqual(summary["event_count"], 2)
            self.assertEqual(summary["raw_file_count"], 2)
            self.assertTrue(summary["raw_complete"])
            self.assertEqual([event["cmd"] for event in summary["ordered_events"]], ["0x00012abc", "0x00004567"])
            self.assertNotIn("raw_path", summary["target_events"][0])
            self.assertNotIn("raw_path", summary["ordered_events"][0])

    def test_summarize_acdbtap_artifacts_does_not_accept_metadata_without_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cap = out / "acdbtap-device-artifacts"
            cap.mkdir()
            (cap / "acdbtap-events.jsonl").write_text(
                json.dumps({
                    "seq": "0x00000001",
                    "cmd": "0x00012abc",
                    "in_len": "0x00000020",
                    "out_len": "0x00001334",
                    "ret": "0x00000000",
                    "sha256": "a" * 64,
                    "raw_written": False,
                    "is_target_4916": True,
                    "is_size_query_4": False,
                }) + "\n"
            )
            summary = v2477.summarize_acdbtap_artifacts(out)
            self.assertEqual(summary["classification"], "acdbtap-metadata-with-missing-raw")
            self.assertFalse(summary["raw_complete"])


if __name__ == "__main__":
    unittest.main()
