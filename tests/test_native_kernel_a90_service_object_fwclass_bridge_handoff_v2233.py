"""Regression tests for native_kernel_a90_service_object_fwclass_bridge_handoff_v2233."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2233 = load_revalidation("native_kernel_a90_service_object_fwclass_bridge_handoff_v2233")


class CommandAndArtifactHelpers(unittest.TestCase):
    def test_sha256_load_manifest_and_command_rendering(self):
        old_manifest = v2233.V2232_MANIFEST
        try:
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data.bin"
                data.write_bytes(b"v2233")
                v2233.V2232_MANIFEST = Path(tmp) / "missing.json"

                self.assertEqual(
                    v2233.sha256(data),
                    "0dd884db98d310c053a9e06574467b18da52e4288cea51439fce0d6ef0412730",
                )
                self.assertEqual(v2233.load_build_manifest(), {})
        finally:
            v2233.V2232_MANIFEST = old_manifest

        args = argparse.Namespace(bridge_host="127.0.0.1", bridge_port=54321, timeout=17.0)
        command = v2233.a90ctl_command(args, ["cat", "/cache/result"], allow_error=True)
        self.assertEqual(command[:2], ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py"])
        self.assertIn("--hide-on-busy", command)
        self.assertIn("--allow-error", command)
        self.assertEqual(command[command.index("--input-mode") + 1], "slow")
        self.assertEqual(command[-2:], ["cat", "/cache/result"])

    def test_flash_and_dry_run_commands_render_v2232_and_v2189_steps(self):
        image = Path("workspace/private/inputs/boot_images/test.img")
        native = v2233.flash_command(image, "expected version", "abc123", from_native=True)
        recovery = v2233.flash_command(image, "expected version", "abc123", from_native=False)

        self.assertEqual(native[:2], ["python3", "workspace/public/src/scripts/revalidation/native_init_flash.py"])
        self.assertIn("--from-native", native)
        self.assertNotIn("--from-native", recovery)
        self.assertEqual(native[native.index("--verify-protocol") + 1], "selftest")

        plan = v2233.dry_run_commands({
            "test_image_sha256": "test-sha",
            "rollback_image_sha256": "rollback-sha",
        })
        self.assertIn(
            "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py",
            plan["preflight"],
        )
        self.assertEqual(len(plan["collect"]), len(v2233.HELPER_REMOTE_PATHS))
        self.assertIn("test-sha", plan["flash_test_boot"])
        self.assertIn("rollback-sha", plan["rollback"])

    def test_extract_summary_value_and_diagnose_artifacts_with_fwclass_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "helper.txt"
            path.write_text(
                "A90_EXECNS_RESULT_FILE_BEGIN\n"
                "helper_result_size=12\n"
                "helper_exit_code=0\n"
                "helper_timed_out=0\n"
                "supervisor_result=wlan0-ready\n"
                "wlan0_present=1\n"
                "wlan_pd_cnss_nonlog_control_flow.label=post-bdf-wlan0\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_bdf_send_ret.hit_count=1\n"
                "wlan_pd_service_object_visible_trigger.label=service-object-ready-post-bdf\n"
                "wlan_pd_service_object_visible_trigger.wlfw_service_request_seen=1\n"
                "post_fw_ready_boot_wlan_trigger.begin=1\n"
                "post_fw_ready_boot_wlan_trigger.pre.fw_ready_processed=1\n"
                "post_fw_ready_boot_wlan_trigger.final.fw_ready_processed=1\n"
                "post_fw_ready_boot_wlan_trigger.final.register_driver_posted=1\n"
                "post_fw_ready_boot_wlan_trigger.final.register_driver_processed=1\n"
                "post_fw_ready_boot_wlan_trigger.path.exists=1\n"
                "post_fw_ready_boot_wlan_trigger.path.writable=1\n"
                "post_fw_ready_boot_wlan_trigger.gate_ready=1\n"
                "post_fw_ready_boot_wlan_trigger.executed=1\n"
                "post_fw_ready_boot_wlan_trigger.write_rc=0\n"
                "post_fw_ready_boot_wlan_trigger.reason=fw-ready\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.begin=1\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.seen_count=1\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count=1\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.timed_out=0\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.final_seen=1\n"
                "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.final_fed=1\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.register_driver.posted=1\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.register_driver.processed=1\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.fw_ready.processed=1\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.cfg_req=2\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.cfg_resp=2\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.state.hex=0xd85\n"
                "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.state.line=FW READY\n",
                encoding="utf-8",
            )

            self.assertEqual(v2233.extract_summary_value(path.read_text(), "helper_exit_code"), "0")
            diagnosis = v2233.diagnose_artifacts([path])

        self.assertEqual(diagnosis["kind"], "helper-artifacts-present")
        self.assertEqual(diagnosis["supervisor_result"], "wlan0-ready")
        self.assertEqual(diagnosis["wlan0_present"], "1")
        self.assertEqual(diagnosis["post_fw_ready_boot_wlan"]["executed"], "1")
        self.assertEqual(diagnosis["post_fw_ready_boot_wlan"]["write_rc"], "0")
        self.assertEqual(
            diagnosis["qcacld_firmware_class_fallback_feeder"]["after_boot_wlan_trigger"]["fed_count"],
            "1",
        )
        self.assertEqual(diagnosis["icnss_after_boot_wlan_long_window"]["state_hex"], "0xd85")

    def test_diagnose_artifacts_classifies_setup_errors_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_missing = Path(tmp) / "root-missing.txt"
            setup = Path(tmp) / "setup.txt"
            unknown = Path(tmp) / "unknown.txt"
            root_missing.write_text(
                "helper_status=setup-error\nsetup_error=lstat property root: No such file or directory\nchild_exit_code=20\n",
                encoding="utf-8",
            )
            setup.write_text("helper_status=setup-error\nhelper_exit_code=20\n", encoding="utf-8")
            unknown.write_text("ordinary log\n", encoding="utf-8")

            self.assertEqual(v2233.diagnose_artifacts([root_missing])["kind"], "property-root-missing")
            self.assertEqual(v2233.diagnose_artifacts([setup])["kind"], "setup-error")
            self.assertEqual(v2233.diagnose_artifacts([unknown])["kind"], "unknown")


class PreflightAndClassification(unittest.TestCase):
    def write_json(self, path: Path, value: dict):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_current_window_preflight_classifiers_accept_absent_and_busy_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "absent"
            out_dir.mkdir()
            self.write_json(out_dir / "collector.stdout.txt", {
                "decision": "v2219-a90-uprobe-trace-buffer-ready-current-window-nohit",
                "event_exists_count": 0,
                "event_enabled_count": 0,
                "selftest_fail0": True,
            })
            self.write_json(out_dir / "v2221-current-window-contract.stdout.txt", {
                "decision": "v2221-collector-parser-integration-failed",
                "pass": False,
                "error": f"v2219-collector failed: {out_dir / 'collector.stderr.txt'}",
            })
            absent_result = {
                "stdout": json.dumps({
                    "error": "v2221-current-window-contract failed",
                    "out_dir": str(out_dir),
                })
            }

            busy_dir = Path(tmp) / "busy"
            busy_dir.mkdir()
            self.write_json(busy_dir / "summary.json", {
                "steps": [
                    {"name": "bridge-status", "ok": True},
                    {"name": "native-status", "ok": True},
                    {"name": "native-version", "ok": True},
                    {"name": "native-helpers", "ok": True},
                    {"name": "helper-inventory", "ok": True},
                ]
            })
            (busy_dir / "native-status.stdout.txt").write_text("A90P1 END rc=0 fail=0\n", encoding="utf-8")
            self.write_json(busy_dir / "collector.stdout.txt", {
                "decision": "v2219-a90-uprobe-trace-buffer-failed",
                "error": "event-state failed status=busy rc=-16",
            })
            self.write_json(busy_dir / "v2221-current-window-contract.stdout.txt", {
                "decision": "v2221-collector-parser-integration-failed",
                "error": f"v2219-collector failed: {busy_dir / 'collector.stderr.txt'}",
            })
            busy_result = {
                "stdout": json.dumps({
                    "error": "v2221-current-window-contract failed",
                    "out_dir": str(busy_dir),
                })
            }

            self.assertTrue(v2233.is_current_window_a90_absent_preflight(absent_result))
            self.assertTrue(v2233.is_current_window_collector_busy_preflight(busy_result))
            self.assertFalse(v2233.is_current_window_a90_absent_preflight({"stdout": "not json"}))

    def test_classify_dry_run_and_live_branches(self):
        ready = v2233.classify({
            "execute": False,
            "preflight": {
                "v2232_manifest_pass": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        blocked = v2233.classify({
            "execute": False,
            "preflight": {
                "v2232_manifest_pass": False,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        self.assertEqual(ready["decision"], "v2233-service-object-fwclass-bridge-handoff-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2233-service-object-fwclass-bridge-handoff-dry-run-blocked")
        self.assertFalse(blocked["pass"])

        cases = [
            (
                {"execute": True, "live_block": "v2222-preflight-failed"},
                "v2233-service-object-fwclass-bridge-handoff-preflight-failed-no-flash",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": False}},
                "v2233-service-object-fwclass-bridge-handoff-rollback-selftest-failed",
                False,
            ),
            (
                {"execute": True, "live_block": "test-flash-failed", "rollback": {"ok": True, "selftest_ok": True}},
                "v2233-service-object-fwclass-bridge-handoff-test-flash-failed-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"diagnosis": {"kind": "property-root-missing"}},
                },
                "v2233-service-object-fwclass-bridge-helper-property-root-missing-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": True}},
                },
                "v2233-service-object-fwclass-bridge-helper-parsed-rollback-pass",
                True,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": False}},
                },
                "v2233-service-object-fwclass-bridge-helper-parse-incomplete-rollback-pass",
                False,
            ),
        ]
        for manifest, decision, passed in cases:
            with self.subTest(decision=decision):
                result = v2233.classify(manifest)
                self.assertEqual(result["decision"], decision)
                self.assertEqual(result["pass"], passed)


class ReportAndResidualState(unittest.TestCase):
    def manifest(self, **overrides):
        manifest = {
            "result": {
                "decision": "v2233-service-object-fwclass-bridge-handoff-dry-run-ready",
                "pass": True,
                "reason": "ready",
            },
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2233.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2233.ROLLBACK_EXPECT_VERSION,
            },
            "execute": False,
            "out_dir": "workspace/private/runs/kernel/v2233",
            "steps": [],
        }
        manifest.update(overrides)
        return manifest

    def test_render_report_includes_dry_run_plan_and_safety_scope(self):
        report = v2233.render_report(self.manifest(dry_run_commands={"postflight": ["a90ctl.py", "selftest"]}))

        self.assertIn("# Native Init V2233 Service-Object FWClass Bridge Handoff Runner", report)
        self.assertIn("Decision: `v2233-service-object-fwclass-bridge-handoff-dry-run-ready`", report)
        self.assertIn("Live mode requires `--execute` plus the exact confirmation token", report)
        self.assertIn("Dry-Run Command Plan", report)
        self.assertIn("does not flash, reboot", report)

    def test_render_report_includes_wlan0_ready_bridge_diagnosis(self):
        report = v2233.render_report(self.manifest(
            execute=True,
            result={
                "decision": "v2233-service-object-fwclass-bridge-helper-parsed-rollback-pass",
                "pass": True,
                "reason": "parsed",
            },
            rollback={"ok": True, "selftest_ok": True},
            collect={
                "parser": {
                    "parsed_decision": "hit",
                    "parsed_pass": True,
                    "total_hits": 9,
                    "hit_event_total": 5,
                    "key_hit_event_total": 4,
                    "key_events": {
                        "uprobe:wlfw_start": {"total_hit_count": 1, "first_ts": "1.0"},
                        "uprobe:wlfw_service_request": {"total_hit_count": 1, "first_ts": "2.0"},
                        "uprobe:wlfw_cap_qmi": {"total_hit_count": 1, "first_ts": "3.0"},
                        "uprobe:wlfw_bdf_entry": {"total_hit_count": 1, "first_ts": "4.0"},
                    },
                },
                "diagnosis": {
                    "decision": "helper-artifacts-present",
                    "helper_exit_code": "0",
                    "helper_timed_out": "0",
                    "supervisor_result": "wlan0-ready",
                    "wlan0_present": "1",
                    "post_fw_ready_boot_wlan": {
                        "begin": "1",
                        "pre_fw_ready_processed": "1",
                        "final_fw_ready_processed": "1",
                        "final_register_driver_posted": "1",
                        "final_register_driver_processed": "1",
                        "path_exists": "1",
                        "path_writable": "1",
                        "gate_ready": "1",
                        "executed": "1",
                        "write_rc": "0",
                        "reason": "fw-ready",
                    },
                    "qcacld_firmware_class_fallback_feeder": {
                        "after_boot_wlan_trigger": {
                            "seen_count": "1",
                            "fed_count": "1",
                            "timed_out": "0",
                            "request_0_final_seen": "1",
                            "request_0_final_fed": "1",
                        },
                    },
                    "icnss_after_boot_wlan_long_window": {
                        "fw_ready_processed": "1",
                        "register_driver_posted": "1",
                        "register_driver_processed": "1",
                        "state_hex": "0xd85",
                        "state_line": "FW READY",
                    },
                },
            },
        ))

        self.assertIn("Post-FW_READY Boot WLAN Trigger", report)
        self.assertIn("QCACLD Firmware-Class Feeder", report)
        self.assertIn("ICNSS After Boot-WLAN Long Window", report)
        self.assertIn("V2232 crossed the V2231 post-BDF wall", report)
        self.assertIn("post-FW_READY driver-start/firmware_class tail", report)

    def test_residual_state_tracks_flash_rollback_and_safety_flags(self):
        dry = v2233.residual_state(self.manifest())
        ok = v2233.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2232-from-native", "ok": True}],
            rollback={"ok": True, "selftest_ok": True, "attempt": "from-native"},
        ))
        bad = v2233.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2232-from-native", "ok": True}],
            rollback={"ok": False, "selftest_ok": False, "attempt": "from-recovery"},
        ))

        self.assertFalse(dry["device_touched"])
        self.assertFalse(dry["partition_write"])
        self.assertTrue(dry["rollback_ok"])
        self.assertTrue(ok["device_touched"])
        self.assertTrue(ok["flash_reboot"])
        self.assertTrue(ok["test_flash_ok"])
        self.assertTrue(ok["rollback_ok"])
        self.assertEqual(ok["rollback_attempt"], "from-native")
        self.assertFalse(ok["cleanup_required"])
        self.assertTrue(bad["cleanup_required"])
        self.assertEqual(bad["residual_risk"], "rollback-or-selftest-incomplete")
        self.assertTrue(bad["partition_write"])
        self.assertFalse(bad["wifi_scan_connect"])
        self.assertFalse(bad["bpf_attach"])


if __name__ == "__main__":
    unittest.main()
