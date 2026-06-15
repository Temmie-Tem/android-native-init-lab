"""Host-only tests for the V2416 ACDB payload capture live handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2416 = load_revalidation("native_audio_acdb_payload_capture_live_handoff_v2416")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": v2416.v2415.DEFAULT_HELPER_OUT_DIR,
        "cc": v2416.v2415.DEFAULT_CC,
        "stimulus_apk": v2416.v2396.DEFAULT_STIMULUS_APK,
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
        "capture_duration_sec": 8,
        "capture_warmup_sec": 0.0,
        "max_bytes": 512,
        "from_native": True,
        "approval": "",
        "out_dir": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AcdbPayloadCaptureLiveHandoff(unittest.TestCase):
    def test_dry_run_names_v2416_and_reuses_v2415_contract(self) -> None:
        payload = v2416.dry_run(args())

        self.assertEqual(payload["run_id"], "V2416")
        self.assertEqual(payload["decision"], "v2416-acdb-payload-capture-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["capture_contract"]["target_device"], "/dev/msm_audio_cal")
        self.assertIn("AUD-5D-acdb-payload-capture go:", payload["approval_phrase_required_for_live"])

    def test_dry_run_can_materialize_private_helper_for_live_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2416.dry_run(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

            self.assertTrue(payload["capture_helper"]["ok"], payload["capture_helper"].get("build"))
            self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
            self.assertTrue(payload["capture_helper"]["build"]["aarch64_static"])

    def test_bad_approval_refuses_before_live_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_live_handoff_v2416.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2416.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2416-acdb-payload-capture-live-refused")
        self.assertIn("exact AUD-5D", payload["reason"])

    def test_summarize_capture_artifacts_hashes_without_raw_hex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts" / "artifacts"
            artifact_dir.mkdir(parents=True)
            raw = "00112233"
            (artifact_dir / "audio-hal-pids.txt").write_text("123\n")
            (artifact_dir / "msm-audio-cal-ioctl-123.jsonl").write_text("\n".join([
                json.dumps({"event": "start", "pid": 123}),
                json.dumps({"event": "ioctl_entry", "seq": 1, "request": "0xc018c8ca", "bytes_hex": raw, "read_len": 4}),
                json.dumps({"event": "ioctl_exit", "seq": 1, "request": "0xc018c8ca", "ret": 0}),
            ]) + "\n")

            summary = v2416.summarize_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "captured-msm-audio-cal-payload-events")
        self.assertEqual(summary["ioctl_entries"], 1)
        self.assertEqual(summary["requests"], ["0xc018c8ca"])
        self.assertEqual(summary["payload_hashes"][0]["sha256"], hashlib.sha256(bytes.fromhex(raw)).hexdigest())
        self.assertNotIn(raw, json.dumps(summary))
        self.assertFalse(summary["raw_payload_in_summary"])

    def test_run_live_uses_rollback_and_private_summary_under_mocked_steps(self) -> None:
        original_run_step = v2416.route.run_step
        original_copy = v2416.route.copy_sealed_android_boot
        original_start_logcat = v2416.route.start_logcat_capture
        original_stop_logcat = v2416.route.stop_logcat_capture
        calls: list[str] = []

        def fake_copy(selected: dict[str, object], out_dir: Path) -> dict[str, object]:
            target = out_dir / "android_boot_0600.img"
            target.write_bytes(b"ANDROID!")
            return {"ok": True, "path": v2416.rel(target), "selected": selected.get("path")}

        def fake_run_step(name: str, command: list[str], out_dir: Path, *, timeout_sec: float, check: bool = True) -> dict[str, object]:
            calls.append(name)
            stdout = out_dir / f"{name}.stdout.txt"
            stderr = out_dir / f"{name}.stderr.txt"
            stdout_text = "uid=0(root) gid=0(root)\n" if name == "android-post-handoff-settle-2" else ""
            if name == "collect-private-artifacts":
                artifact_dir = out_dir / "device-artifacts" / "artifacts"
                artifact_dir.mkdir(parents=True, exist_ok=True)
                (artifact_dir / "audio-hal-pids.txt").write_text("123\n")
                (artifact_dir / "msm-audio-cal-ioctl-123.jsonl").write_text("\n".join([
                    json.dumps({"event": "start", "pid": 123}),
                    json.dumps({"event": "ioctl_entry", "seq": 1, "request": "0x1", "bytes_hex": "aa", "read_len": 1}),
                    json.dumps({"event": "ioctl_exit", "seq": 1, "request": "0x1", "ret": 0}),
                ]) + "\n")
            stdout.write_text(stdout_text)
            stderr.write_text("")
            return {"name": name, "command": command, "stdout": v2416.rel(stdout), "stderr": v2416.rel(stderr), "ok": True, "rc": 0, "timeout_sec": timeout_sec}

        def fake_start_logcat(route_args: argparse.Namespace, out_dir: Path) -> dict[str, object]:
            return {"record": {"name": "payload-capture-logcat", "ok": None}, "proc": None}

        def fake_stop_logcat(capture: dict[str, object] | None) -> None:
            if capture:
                capture["record"]["ok"] = True

        v2416.route.run_step = fake_run_step
        v2416.route.copy_sealed_android_boot = fake_copy
        v2416.route.start_logcat_capture = fake_start_logcat
        v2416.route.stop_logcat_capture = fake_stop_logcat
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir) / "run"
                helper_dir = Path(temp_dir) / "helper"
                payload = v2416.run_live(args(
                    approval=v2416.APPROVAL_PHRASE,
                    out_dir=out_dir,
                    helper_out_dir=helper_dir,
                    adb_command_timeout=1.0,
                    flash_timeout=1.0,
                ))
        finally:
            v2416.route.run_step = original_run_step
            v2416.route.copy_sealed_android_boot = original_copy
            v2416.route.start_logcat_capture = original_start_logcat
            v2416.route.stop_logcat_capture = original_stop_logcat

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["rolled_back"])
        self.assertIn("rollback-pass", payload["decision"])
        self.assertEqual(payload["payload_capture_summary"]["classification"], "captured-msm-audio-cal-payload-events")
        self.assertIn("flash-android", calls)
        self.assertIn("prepare-private-artifacts-for-pull", calls)
        self.assertIn("rollback-v2321", calls)
        self.assertIn("collect-private-artifacts", calls)


if __name__ == "__main__":
    unittest.main()
