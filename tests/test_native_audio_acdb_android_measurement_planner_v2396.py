"""Host-only tests for the V2396 Android/Magisk ACDB measurement planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2396 = load_revalidation("native_audio_acdb_android_measurement_planner_v2396")




def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_synthetic_acdb_capture(run_dir: Path) -> None:
    artifact_dir = run_dir / "device-artifacts" / "a90-audio-acdb-v2396"
    result = {
        "run_id": "V2397",
        "build_tag": "v2397-audio-acdb-android-magisk-live",
        "decision": "v2397-android-acdb-measurement-captured-rollback-pass",
        "ok": True,
        "rolled_back": True,
        "approval_ok": True,
    }
    write_text(run_dir / "result.json", json.dumps(result))
    write_text(
        run_dir / "stimulus-logcat.stdout.txt",
        "\n".join([
            "A90_AUDIO_STIMULUS_BEGIN",
            "audio_hw_primary platform_send_audio_calibration app_type=69941",
            "ACDB acdb_loader_send_audio_cal_v5 /dev/msm_audio_cal",
            "A90_AUDIO_STIMULUS_END",
            "A90_AUDIO_STIMULUS_FINISH",
        ]),
    )
    for phase in ("baseline", "active", "post"):
        write_text(artifact_dir / f"{phase}-meta.txt", f"phase={phase}\n")
        write_text(artifact_dir / f"{phase}-getprop-audio.txt", "[vendor.audio.test]: [1]\n")
        write_text(artifact_dir / f"{phase}-ps.txt", "audio 123 android.hardware.audio.service\n")
        write_text(artifact_dir / f"{phase}-audio-hal-pids.txt", "123\n")
        write_text(artifact_dir / f"{phase}-audio-hal-123-maps.txt", "/vendor/lib/hw/audio.primary.msmnile.so\n/vendor/lib/libacdbloader.so\n")
        write_text(artifact_dir / f"{phase}-audio-hal-123-fd.txt", "/dev/msm_audio_cal\n/dev/snd/controlC0\n")
        write_text(artifact_dir / f"{phase}-devnodes.txt", "crw------- /dev/msm_audio_cal\ndrwxr-xr-x /dev/snd\n")
        write_text(artifact_dir / f"{phase}-proc-asound.txt", " 0 [tavil]: sm8150-tavil-snd-card\n")
        write_text(artifact_dir / f"{phase}-tinymix-all-values.txt", "3345 INT 4 Audio Stream 0 App Type Cfg  69941 15 48000 2\n")
        write_text(artifact_dir / f"{phase}-dmesg-tail.txt", "send_afe_cal_type cal_block found\nq6asm_send_cal ok\nadm_open returned ADSP_EOK\n")

def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "dry_run": True,
        "materialize_module_template": False,
        "module_out_dir": v2396.DEFAULT_MODULE_OUT_DIR,
        "stimulus_apk": v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": 2000,
        "sample_rate": 48000,
        "amplitude": 0.05,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "from_native": True,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AcdbAndroidMeasurementPlanner(unittest.TestCase):
    def test_dry_run_is_host_only_and_defers_live_until_module_materialized(self) -> None:
        payload = v2396.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["future_live_ready"])
        self.assertIn("AUD-5A-android-acdb-magisk-measurement go:", payload["approval_phrase_required_for_future_live"])
        self.assertIn("module template not materialized", " ".join(payload["future_live_blockers"]))
        self.assertFalse(payload["magisk_module"]["native_runtime_dependency"])

    def test_command_plan_reuses_checked_android_handoff_and_rollback(self) -> None:
        payload = v2396.dry_run_payload(args(adb="/opt/android/adb", serial="A90ADB01"))
        commands = payload["commands"]

        self.assertIn("native_init_flash.py", " ".join(commands["flash_android"]))
        self.assertIn("--post-flash-target", commands["flash_android"])
        self.assertIn("android-adb", commands["flash_android"])
        self.assertEqual(commands["baseline_probe"][:3], ["/opt/android/adb", "-s", "A90ADB01"])
        self.assertEqual(commands["android_reboot_recovery_for_rollback"], ["/opt/android/adb", "-s", "A90ADB01", "reboot", "recovery"])
        self.assertIn("rollback_v2321", commands)
        self.assertIn("--expect-version", commands["rollback_v2321"])
        self.assertIn("0.9.285", commands["rollback_v2321"])
        install_steps = [step for step in commands["stage_transient_module_and_stimulus"] if "install" in step]
        self.assertEqual(len(install_steps), 1)
        self.assertEqual(install_steps[0][:4], ["/opt/android/adb", "-s", "A90ADB01", "install"])
        self.assertIn("workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk", install_steps[0])
        self.assertEqual(commands["collect_private_artifacts"][:3], ["/opt/android/adb", "-s", "A90ADB01"])
        self.assertEqual(commands["collect_private_artifacts"][-1], "<private-run-dir>/device-artifacts")

    def test_plan_contains_acdb_specific_observability(self) -> None:
        payload = v2396.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertIn("/dev/msm_audio_cal", "".join(v2396.module_files().values()))
        self.assertIn("audio-hal-pids", "".join(v2396.module_files().values()))
        self.assertIn("ACDB", payload["measurement_focus"]["log_filter_regex"])
        self.assertIn("q6asm_send_cal", payload["measurement_focus"]["log_filter_regex"])
        self.assertIn("logcat", flat)
        self.assertIn("A90AudioRouteStimulusActivity", flat)
        self.assertIn("a90_acdb_probe.sh", flat)

    def test_command_safety_blocks_persistent_magisk_install_and_native_playback(self) -> None:
        payload = v2396.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"])
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn(" tinymix set ", flat)
        self.assertNotIn("fastboot", flat)
        self.assertEqual(payload["command_safety"]["default_delivery"], "transient Magisk-root helper; no persistent module install")

    def test_module_template_materialization_is_private_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2396.dry_run_payload(args(materialize_module_template=True, module_out_dir=Path(temp_dir)))

            self.assertTrue(payload["magisk_module"]["zip"]["ok"])
            self.assertEqual(payload["magisk_module"]["zip"]["mode"], "0o600")
            self.assertTrue(payload["magisk_module"]["manifest"]["ok"])
            self.assertTrue(payload["future_live_ready"])
            self.assertEqual(payload["future_live_blockers"], [])
            self.assertTrue((Path(temp_dir) / "service.sh").exists())
            self.assertTrue((Path(temp_dir) / "system/bin/a90_acdb_probe.sh").exists())
            self.assertTrue((Path(temp_dir) / "a90_audio_acdb_probe_v2396.zip").exists())


    def test_run_live_requires_exact_aud5a_approval(self) -> None:
        namespace = args(materialize_module_template=True, approval="continue")

        with self.assertRaisesRegex(RuntimeError, "exact AUD-5A"):
            v2396.ensure_live_approval(namespace)

    def test_run_live_gate_accepts_exact_approval_without_running(self) -> None:
        namespace = args(approval=v2396.APPROVAL_PHRASE)

        v2396.ensure_live_approval(namespace)

    def test_live_run_metadata_names_v2397_and_private_out_dir(self) -> None:
        self.assertEqual(v2396.LIVE_RUN_ID, "V2397")
        self.assertIn("v2397-android-acdb-measurement-", str(v2396.default_live_out_dir()))
        self.assertIn("--run-live", subprocess.run(
            [sys.executable, "workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py", "--help"],
            cwd=v2396.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        ).stdout)

    def test_cli_run_live_bad_approval_refuses_before_live_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2396.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2397-android-acdb-measurement-live-refused")
        self.assertIn("exact AUD-5A", payload["reason"])

    def test_post_live_analysis_attaches_v2399_decision_after_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "v2397-android-acdb-measurement-synthetic"
            make_synthetic_acdb_capture(run_dir)
            result = {"ok": True, "rolled_back": True}

            analysis = v2396.attach_post_live_analysis(result, run_dir)

        self.assertEqual(analysis["run_id"], "V2399")
        self.assertEqual(analysis["decision"], "bounded-native-acdb-candidate")
        self.assertEqual(result["post_live_analysis"]["device_action"], "none")

    def test_post_live_analysis_skips_without_rollback_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = {"ok": True, "rolled_back": False}

            analysis = v2396.attach_post_live_analysis(result, Path(temp_dir))

        self.assertEqual(analysis["decision"], "analysis-skipped")
        self.assertFalse(analysis["ok"])
        self.assertEqual(analysis["device_action"], "none")

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2396.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2396-audio-acdb-android-magisk-planner-dry-run")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
