from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta233_cold_boot_persistence_smoke.py")


class ServerDistroWsta233ColdBootPersistenceSmokeTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args(["--run-dir", str(root / "wsta233"), *extra])

    def fake_pre(self) -> dict:
        return {
            "native_version": "0.11.158 build=v3402-dpublic-hud-presenter-restart-policy",
            "selftest_fail_zero": True,
            "boot_ok": True,
            "uptime_sec": 3861.0,
            "runtime_sd_writable": True,
            "autohud_running": True,
            "tcpctl_running": True,
            "rshell_running": False,
            "tcpctl_port_reachable": True,
            "admin_ssh_port_reachable": False,
            "loopback_smoke_port_reachable": False,
        }

    def fake_post(self) -> dict:
        payload = self.fake_pre()
        payload["uptime_sec"] = 42.0
        return payload

    def install_fake_capture(self, sequence: list[dict]):
        calls: list[str] = []
        old = runner.capture_phase

        def fake_capture(args, run_dir, phase):
            calls.append(phase)
            compact = sequence.pop(0)
            return {"records": {}, "compact_redacted": compact}

        runner.capture_phase = fake_capture
        return old, calls

    def restore_fake_capture(self, old) -> None:
        runner.capture_phase = old

    def write_summary(self, run_dir: Path, *, monitor: dict | None = None) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "scope": "WSTA233 cold-boot persistence smoke private evidence",
            "run_dir": runner.rel(run_dir),
            "events": [],
            "pre_compact_redacted": self.fake_pre(),
            "cold_boot_monitor": monitor or {
                "disconnect_seen": True,
                "reconnect_seen": True,
            },
        }
        (run_dir / runner.SUMMARY_NAME).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_default_run_is_fail_closed(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta233-blocked-explicit-phase-required")
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["native_reboot"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertFalse(result["safety"]["packet_filter_mutation"])

    def test_capture_pre_baseline_writes_private_summary(self) -> None:
        old, calls = self.install_fake_capture([self.fake_pre()])
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                result = runner.run(self.args(root, "--capture-pre-baseline"))
                summary = json.loads((root / "wsta233" / runner.SUMMARY_NAME).read_text(encoding="utf-8"))
        finally:
            self.restore_fake_capture(old)

        self.assertEqual(result["decision"], runner.PREBASELINE_DECISION)
        self.assertEqual(calls, ["pre"])
        self.assertEqual(summary["pre_compact_redacted"]["native_version"], self.fake_pre()["native_version"])
        self.assertIn("pre_baseline_done", [item["name"] for item in summary["events"]])

    def test_post_classification_detects_manual_rebringup_gap(self) -> None:
        old, calls = self.install_fake_capture([self.fake_post()])
        old_restart = runner.command_record

        def fake_command_record(run_dir, phase, name, command, timeout):
            return {"returncode": 0, "output": "{}"}

        runner.command_record = fake_command_record
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                run_dir = root / "wsta233"
                self.write_summary(run_dir)
                result = runner.run(self.args(root, "--capture-post-classify"))
                summary = json.loads((run_dir / runner.SUMMARY_NAME).read_text(encoding="utf-8"))
        finally:
            runner.command_record = old_restart
            self.restore_fake_capture(old)

        self.assertEqual(result["decision"], runner.POST_CLASSIFIED_DECISION)
        self.assertEqual(calls, ["post"])
        classification = result["classification"]
        self.assertTrue(classification["cold_boot_evidence"])
        self.assertTrue(classification["uptime_drop"])
        self.assertTrue(classification["native_pid1_returned"])
        self.assertTrue(classification["native_control_plane_persisted"])
        self.assertFalse(classification["admin_ssh_auto_started"])
        self.assertFalse(classification["loopback_smoke_auto_started"])
        self.assertEqual(
            classification["gap_classification"],
            "native-pid1-and-usb-control-persisted-debian-admin-services-manual-rebringup-required",
        )
        self.assertEqual(summary["classification"]["gap_classification"], classification["gap_classification"])

    def test_post_classification_blocks_without_cold_boot_evidence(self) -> None:
        old, _calls = self.install_fake_capture([self.fake_pre()])
        old_restart = runner.command_record
        runner.command_record = lambda *args, **kwargs: {"returncode": 0, "output": "{}"}
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                run_dir = root / "wsta233"
                self.write_summary(run_dir, monitor={"disconnect_seen": False, "reconnect_seen": False})
                result = runner.run(self.args(root, "--capture-post-classify"))
        finally:
            runner.command_record = old_restart
            self.restore_fake_capture(old)

        self.assertEqual(result["decision"], "wsta233-blocked-cold-boot-evidence-missing")
        self.assertFalse(result["classification"]["cold_boot_evidence"])

    def test_rollback_requires_explicit_ack_before_flash(self) -> None:
        old_preflight = runner.rollback_preflight
        old_command = runner.command_record
        calls: list[str] = []
        runner.rollback_preflight = lambda: {
            "rollback_image_present": True,
            "deep_fallback_present": True,
            "final_fallback_present": True,
            "checked_flash_helper_present": True,
            "rollback_sha256": runner.ROLLBACK_SHA256,
            "deep_fallback_sha256": runner.DEEP_FALLBACK_SHA256,
        }
        runner.command_record = lambda *args, **kwargs: calls.append("command") or {"returncode": 0, "output": "{}"}
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                result = runner.run(self.args(root, "--rollback-v2321"))
        finally:
            runner.rollback_preflight = old_preflight
            runner.command_record = old_command

        self.assertEqual(result["decision"], "wsta233-blocked-explicit-v2321-rollback-ack-required")
        self.assertEqual(calls, [])
        self.assertFalse(result["safety"]["boot_flash"])

    def test_nonprivate_run_dir_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root, "--capture-pre-baseline"))

        self.assertEqual(result["decision"], "wsta233-blocked-nonprivate-run-dir")

    def test_source_uses_checked_boot_rollback_not_raw_flash_paths(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--capture-pre-baseline", source)
        self.assertIn("--capture-post-classify", source)
        self.assertIn("--ack-rollback-to-v2321", source)
        self.assertIn("native_init_flash.py", source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("fastboot", source)
        self.assertNotIn(" dd ", source)
        self.assertNotIn("try" + "cloudflare.com", source)
        self.assertNotIn("ssid" + "=", source.lower())
        self.assertNotIn("psk" + "=", source.lower())


if __name__ == "__main__":
    unittest.main()
