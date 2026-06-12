"""Regression tests for native_kernel_a90_post_bdf_hold_handoff_v2231."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2231 = load_revalidation("native_kernel_a90_post_bdf_hold_handoff_v2231")


class CommandAndArtifactHelpers(unittest.TestCase):
    def test_sha256_load_manifest_and_command_rendering(self):
        old_manifest = v2231.V2230_MANIFEST
        try:
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data.bin"
                data.write_bytes(b"v2231")
                v2231.V2230_MANIFEST = Path(tmp) / "missing.json"

                self.assertEqual(
                    v2231.sha256(data),
                    "13f2133498d7ba973de617f49e30ed75ab5da8c6587d9015622c6ba474cc2aa2",
                )
                self.assertEqual(v2231.load_build_manifest(), {})
        finally:
            v2231.V2230_MANIFEST = old_manifest

        args = argparse.Namespace(bridge_host="127.0.0.1", bridge_port=54321, timeout=17.0)
        command = v2231.a90ctl_command(args, ["cat", "/cache/result"], allow_error=True)
        self.assertEqual(command[:2], ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py"])
        self.assertIn("--hide-on-busy", command)
        self.assertIn("--allow-error", command)
        self.assertEqual(command[command.index("--input-mode") + 1], "slow")
        self.assertEqual(command[-2:], ["cat", "/cache/result"])

    def test_flash_and_dry_run_commands_render_v2230_and_v2189_steps(self):
        image = Path("workspace/private/inputs/boot_images/test.img")
        native = v2231.flash_command(image, "expected version", "abc123", from_native=True)
        recovery = v2231.flash_command(image, "expected version", "abc123", from_native=False)

        self.assertEqual(native[:2], ["python3", "workspace/public/src/scripts/revalidation/native_init_flash.py"])
        self.assertIn("--from-native", native)
        self.assertNotIn("--from-native", recovery)
        self.assertEqual(native[native.index("--verify-protocol") + 1], "selftest")

        plan = v2231.dry_run_commands({
            "test_image_sha256": "test-sha",
            "rollback_image_sha256": "rollback-sha",
        })
        self.assertIn(
            "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py",
            plan["preflight"],
        )
        self.assertEqual(len(plan["collect"]), len(v2231.HELPER_REMOTE_PATHS))
        self.assertIn("test-sha", plan["flash_test_boot"])
        self.assertIn("rollback-sha", plan["rollback"])

    def test_extract_summary_value_and_diagnose_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "helper.txt"
            path.write_text(
                "A90_EXECNS_RESULT_FILE_BEGIN\n"
                "helper_result_size=12\n"
                "helper_exit_code=0\n"
                "helper_timed_out=0\n"
                "supervisor_result=ok\n"
                "wlan0_present=0\n"
                "wlan_pd_cnss_nonlog_control_flow.label=post-bdf-no-wlan0\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_call.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_retcheck.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_default_service_manager_call.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_name_string16_call.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_bdf_send_ret.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_bdf_result_log.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_done_signal.hit_count=1\n"
                "wlan_pd_service_object_visible_trigger.label=service-object-ready-post-bdf\n"
                "wlan_pd_service_object_visible_trigger.vndservicemanager_ready=1\n"
                "wlan_pd_service_object_visible_trigger.pm_proxy_helper_ready=1\n"
                "wlan_pd_service_object_visible_trigger.per_mgr_ready=1\n"
                "wlan_pd_service_object_visible_trigger.provider_seen=1\n"
                "wlan_pd_service_object_visible_trigger.subsys_modem_holder_opened=1\n"
                "wlan_pd_service_object_visible_trigger.tftp_running=1\n"
                "wlan_pd_service_object_visible_trigger.cnss_daemon_running=1\n"
                "wlan_pd_service_object_visible_trigger.wlfw_start_seen=1\n"
                "wlan_pd_service_object_visible_trigger.wlfw_service_request_seen=1\n"
                "wlan_pd_service_object_visible_trigger.wlfw_service69_seen=0\n"
                "wlan_pd_service_object_visible_trigger.requested_wlanmdsp=0\n"
                "wlan_pd_service_object_visible_trigger.wlan0_present=0\n",
                encoding="utf-8",
            )

            self.assertEqual(v2231.extract_summary_value(path.read_text(), "helper_exit_code"), "0")
            diagnosis = v2231.diagnose_artifacts([path])

        self.assertEqual(diagnosis["kind"], "helper-artifacts-present")
        self.assertEqual(diagnosis["helper_exit_code"], "0")
        self.assertEqual(diagnosis["helper_timed_out"], "0")
        self.assertEqual(diagnosis["supervisor_result"], "ok")
        self.assertEqual(diagnosis["wlan0_present"], "0")
        self.assertEqual(diagnosis["nonlog_control_flow"]["label"], "post-bdf-no-wlan0")
        self.assertEqual(diagnosis["nonlog_control_flow"]["periph_manager_name_string16_call_hits"], "1")
        self.assertEqual(diagnosis["service_object_visible"]["label"], "service-object-ready-post-bdf")
        self.assertEqual(diagnosis["service_object_visible"]["wlfw_service_request_seen"], "1")

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

            self.assertEqual(v2231.diagnose_artifacts([root_missing])["kind"], "property-root-missing")
            self.assertEqual(v2231.diagnose_artifacts([setup])["kind"], "setup-error")
            self.assertEqual(v2231.diagnose_artifacts([unknown])["kind"], "unknown")


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

            self.assertTrue(v2231.is_current_window_a90_absent_preflight(absent_result))
            self.assertTrue(v2231.is_current_window_collector_busy_preflight(busy_result))
            self.assertFalse(v2231.is_current_window_a90_absent_preflight({"stdout": "not json"}))

    def test_classify_dry_run_and_live_branches(self):
        ready = v2231.classify({
            "execute": False,
            "preflight": {
                "v2230_manifest_pass": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        blocked = v2231.classify({
            "execute": False,
            "preflight": {
                "v2230_manifest_pass": False,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        self.assertEqual(ready["decision"], "v2231-post-bdf-hold-handoff-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2231-post-bdf-hold-handoff-dry-run-blocked")
        self.assertFalse(blocked["pass"])

        cases = [
            (
                {"execute": True, "live_block": "v2222-preflight-failed"},
                "v2231-post-bdf-hold-handoff-preflight-failed-no-flash",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": False}},
                "v2231-post-bdf-hold-handoff-rollback-selftest-failed",
                False,
            ),
            (
                {"execute": True, "live_block": "test-flash-failed", "rollback": {"ok": True, "selftest_ok": True}},
                "v2231-post-bdf-hold-handoff-test-flash-failed-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"diagnosis": {"kind": "property-root-missing"}},
                },
                "v2231-post-bdf-hold-helper-property-root-missing-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": True}},
                },
                "v2231-post-bdf-hold-helper-parsed-rollback-pass",
                True,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": False}},
                },
                "v2231-post-bdf-hold-helper-parse-incomplete-rollback-pass",
                False,
            ),
        ]
        for manifest, decision, passed in cases:
            with self.subTest(decision=decision):
                result = v2231.classify(manifest)
                self.assertEqual(result["decision"], decision)
                self.assertEqual(result["pass"], passed)


class ReportAndResidualState(unittest.TestCase):
    def manifest(self, **overrides):
        manifest = {
            "result": {"decision": "v2231-post-bdf-hold-handoff-dry-run-ready", "pass": True, "reason": "ready"},
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2231.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2231.ROLLBACK_EXPECT_VERSION,
            },
            "execute": False,
            "out_dir": "workspace/private/runs/kernel/v2231",
            "steps": [],
        }
        manifest.update(overrides)
        return manifest

    def test_render_report_includes_dry_run_plan_and_safety_scope(self):
        report = v2231.render_report(self.manifest(dry_run_commands={"postflight": ["a90ctl.py", "selftest"]}))

        self.assertIn("# Native Init V2231 Post-BDF Hold Handoff Runner", report)
        self.assertIn("Decision: `v2231-post-bdf-hold-handoff-dry-run-ready`", report)
        self.assertIn("Live mode requires `--execute` plus the exact confirmation token", report)
        self.assertIn("Dry-Run Command Plan", report)
        self.assertIn("does not flash, reboot", report)

    def test_render_report_includes_successful_post_bdf_negative_diagnosis(self):
        report = v2231.render_report(self.manifest(
            execute=True,
            result={
                "decision": "v2231-post-bdf-hold-helper-parsed-rollback-pass",
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
                    "supervisor_result": "ok",
                    "wlan0_present": "0",
                    "service_object_visible": {
                        "label": "service-object-ready-post-bdf",
                        "vndservicemanager_ready": "1",
                        "pm_proxy_helper_ready": "1",
                        "per_mgr_ready": "1",
                        "provider_seen": "1",
                        "tftp_running": "1",
                        "cnss_daemon_running": "1",
                        "subsys_modem_holder_opened": "1",
                        "wlfw_start_seen": "1",
                        "wlfw_service_request_seen": "1",
                        "wlfw_service69_seen": "1",
                        "requested_wlanmdsp": "0",
                        "wlan0_present": "0",
                    },
                },
            },
        ))

        self.assertIn("Service-Object Snapshot", report)
        self.assertIn("service-object-ready-post-bdf", report)
        self.assertIn("V2230 preserves the V2228 service-manager fix", report)
        self.assertIn("remaining blocker is after BDF/QMI progress", report)
        self.assertIn("post-BDF wait gates are no longer the primary blocker", report)

    def test_residual_state_tracks_flash_rollback_and_safety_flags(self):
        dry = v2231.residual_state(self.manifest())
        ok = v2231.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2230-from-native", "ok": True}],
            rollback={"ok": True, "selftest_ok": True, "attempt": "from-native"},
        ))
        bad = v2231.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2230-from-native", "ok": True}],
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
