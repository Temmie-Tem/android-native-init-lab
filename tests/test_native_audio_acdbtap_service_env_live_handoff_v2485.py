from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import native_audio_acdbtap_live_planner_v2476 as v2476
import native_audio_acdbtap_service_env_live_handoff_v2485 as v2485
import native_audio_acdbtap_service_env_planner_v2484 as v2484


class V2485ServiceEnvLiveHandoffTests(unittest.TestCase):
    def args(self) -> Namespace:
        return Namespace(
            adb="adb",
            serial=None,
            out_dir=None,
            module_out_dir=v2484.DEFAULT_MODULE_OUT_DIR,
            materialize_module=True,
            stage_dir=v2476.DEFAULT_STAGE_DIR,
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

    def test_dry_run_requires_service_env_preload_and_apk_install(self) -> None:
        payload = v2485.dry_run_payload(self.args())
        flat = json.dumps(payload, sort_keys=True)
        self.assertTrue(payload["command_safety"]["ok"])
        self.assertTrue(payload["module_safety"]["ok"])
        self.assertIn(v2484.MODULE_ID, flat)
        self.assertIn(v2484.RC_MARKER, flat)
        self.assertIn("override", flat)
        self.assertIn("setenv LD_PRELOAD", flat)
        self.assertIn("A90_ACDBTAP_SERVICE_PRELOAD_ALL_PIDS", flat)
        self.assertIn("install_stimulus_apk", flat)
        self.assertIn("verify_stimulus_apk", flat)
        self.assertIn("cmd package path", flat)
        self.assertIn("captured-acdbtap-full-outbuf-set-no-4916", flat)
        self.assertIn("cleanup_exact_module", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("setenforce 0", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("AUDIO_SET_CALIBRATION", flat)

    def test_service_preload_confirmation_requires_all_pids_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = Path(tmp) / "stdout.txt"
            stdout.write_text(
                "A90_ACDBTAP_SERVICE_HAL_PIDS 123 456\n"
                "A90_ACDBTAP_SERVICE_PRELOAD_CONFIRMED pid=123 path=/vendor/lib/libacdbtap.so\n"
                "A90_ACDBTAP_SERVICE_PRELOAD_CONFIRMED pid=456 path=/vendor/lib/libacdbtap.so\n"
                "A90_ACDBTAP_SERVICE_PRELOAD_ALL_PIDS\n"
            )
            self.assertTrue(v2485.service_preload_confirmed({"stdout": str(stdout)}))
            stdout.write_text(
                "A90_ACDBTAP_SERVICE_HAL_PIDS 123 456\n"
                "A90_ACDBTAP_SERVICE_PRELOAD_CONFIRMED pid=123 path=/vendor/lib/libacdbtap.so\n"
                "A90_ACDBTAP_SERVICE_PRELOAD_MISSING pid=456 path=/vendor/lib/libacdbtap.so\n"
            )
            self.assertFalse(v2485.service_preload_confirmed({"stdout": str(stdout)}))

    def test_stimulus_start_failure_detects_activity_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = Path(tmp) / "stdout.txt"
            stdout.write_text("Error type 3\nError: Activity class does not exist.\n")
            self.assertTrue(v2485.playback_start_failed({"stdout": str(stdout)}))
            stdout.write_text("Starting: Intent { act=com.a90.nativeinit.audio.PLAY_ROUTE_STIMULUS }\n")
            self.assertFalse(v2485.playback_start_failed({"stdout": str(stdout)}))

    def test_command_safety_rejects_policy_install_and_native_calibration(self) -> None:
        safety = v2485.command_safety({
            "commands": ["setenforce 0", "magisk --install-module x.zip", "AUDIO_SET_CALIBRATION", "service.sh"],
        })
        names = {item["name"] for item in safety["findings"]}
        self.assertIn("silent_permissive", names)
        self.assertIn("magisk_install_module", names)
        self.assertIn("native_cal_set_symbol", names)
        self.assertIn("service_script", names)

    def test_adb_push_sha_recovery_helpers(self) -> None:
        command = ["adb", "push", "workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py", "/data/local/tmp/libacdbtap.so"]
        self.assertTrue(v2485.is_adb_push_command(command))
        self.assertFalse(v2485.is_adb_push_command(["adb", "shell", "true"]))
        expected = v2485.expected_push_sha256(command)
        with tempfile.TemporaryDirectory() as tmp:
            stdout = Path(tmp) / "stdout.txt"
            stdout.write_text(f"{expected}  /data/local/tmp/libacdbtap.so\n")
            self.assertTrue(v2485.remote_sha_matches({"stdout": str(stdout)}, expected))
            stdout.write_text("deadbeef  /data/local/tmp/libacdbtap.so\n")
            self.assertFalse(v2485.remote_sha_matches({"stdout": str(stdout)}, expected))


if __name__ == "__main__":
    unittest.main()
