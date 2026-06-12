"""Regression tests for native_kernel_a90_boot_window_handoff_v2227."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2227 = load_revalidation("native_kernel_a90_boot_window_handoff_v2227")


class CommandAndArtifactHelpers(unittest.TestCase):
    def test_sha256_load_manifest_and_command_rendering(self):
        old_manifest = v2227.V2226_MANIFEST
        try:
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data.bin"
                data.write_bytes(b"v2227")
                v2227.V2226_MANIFEST = Path(tmp) / "missing.json"

                self.assertEqual(
                    v2227.sha256(data),
                    "a3454351892f33b439364e3d80fd13693b2076eb0f64ecaf337316c108c64237",
                )
                self.assertEqual(v2227.load_build_manifest(), {})
        finally:
            v2227.V2226_MANIFEST = old_manifest

        args = argparse.Namespace(bridge_host="127.0.0.1", bridge_port=54321, timeout=17.0)
        command = v2227.a90ctl_command(args, ["cat", "/cache/result"], allow_error=True)
        self.assertEqual(command[:2], ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py"])
        self.assertIn("--hide-on-busy", command)
        self.assertIn("--allow-error", command)
        self.assertEqual(command[command.index("--input-mode") + 1], "slow")
        self.assertEqual(command[-2:], ["cat", "/cache/result"])

    def test_flash_and_dry_run_commands_render_v2226_and_v2189_steps(self):
        image = Path("workspace/private/inputs/boot_images/test.img")
        native = v2227.flash_command(image, "expected version", "abc123", from_native=True)
        recovery = v2227.flash_command(image, "expected version", "abc123", from_native=False)
        self.assertEqual(native[:2], ["python3", "workspace/public/src/scripts/revalidation/native_init_flash.py"])
        self.assertIn("--from-native", native)
        self.assertNotIn("--from-native", recovery)
        self.assertEqual(native[native.index("--verify-protocol") + 1], "selftest")

        plan = v2227.dry_run_commands({
            "test_image_sha256": "test-sha",
            "rollback_image_sha256": "rollback-sha",
        })
        self.assertIn(
            "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py",
            plan["preflight"],
        )
        self.assertEqual(len(plan["collect"]), len(v2227.HELPER_REMOTE_PATHS))
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
                "wlan_pd_cnss_nonlog_control_flow.label=peripheral-default-service-manager-call-no-return\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_call.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_retcheck.hit_count=1\n"
                "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_default_service_manager_call.hit_count=1\n",
                encoding="utf-8",
            )

            self.assertEqual(v2227.extract_summary_value(path.read_text(), "helper_exit_code"), "0")
            diagnosis = v2227.diagnose_artifacts([path])

        self.assertEqual(diagnosis["kind"], "helper-artifacts-present")
        self.assertEqual(diagnosis["helper_exit_code"], "0")
        self.assertEqual(diagnosis["helper_timed_out"], "0")
        self.assertEqual(diagnosis["supervisor_result"], "ok")
        self.assertEqual(diagnosis["wlan0_present"], "0")
        self.assertEqual(
            diagnosis["nonlog_control_flow"]["label"],
            "peripheral-default-service-manager-call-no-return",
        )
        self.assertEqual(diagnosis["nonlog_control_flow"]["periph_default_service_manager_call_hits"], "1")

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

            self.assertEqual(v2227.diagnose_artifacts([root_missing])["kind"], "property-root-missing")
            self.assertEqual(v2227.diagnose_artifacts([setup])["kind"], "setup-error")
            self.assertEqual(v2227.diagnose_artifacts([unknown])["kind"], "unknown")


class PreflightAndClassification(unittest.TestCase):
    def write_json(self, path: Path, value: dict):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_is_current_window_a90_absent_preflight_positive_and_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            collector_stdout = out_dir / "collector.stdout.txt"
            self.write_json(collector_stdout, {
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
            result = {
                "stdout": json.dumps({
                    "error": "v2221-current-window-contract failed",
                    "out_dir": str(out_dir),
                })
            }

            self.assertTrue(v2227.is_current_window_a90_absent_preflight(result))
            self.assertFalse(v2227.is_current_window_a90_absent_preflight({"stdout": "not json"}))

    def test_is_current_window_collector_busy_preflight_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = {
                "steps": [
                    {"name": "bridge-status", "ok": True},
                    {"name": "native-status", "ok": True},
                    {"name": "native-version", "ok": True},
                    {"name": "native-helpers", "ok": True},
                    {"name": "helper-inventory", "ok": True},
                ]
            }
            self.write_json(out_dir / "summary.json", summary)
            (out_dir / "native-status.stdout.txt").write_text("A90P1 END rc=0 fail=0\n", encoding="utf-8")
            collector_stdout = out_dir / "collector.stdout.txt"
            self.write_json(collector_stdout, {
                "decision": "v2219-a90-uprobe-trace-buffer-failed",
                "error": "event-state failed status=busy rc=-16",
            })
            self.write_json(out_dir / "v2221-current-window-contract.stdout.txt", {
                "decision": "v2221-collector-parser-integration-failed",
                "error": f"v2219-collector failed: {out_dir / 'collector.stderr.txt'}",
            })
            result = {
                "stdout": json.dumps({
                    "error": "v2221-current-window-contract failed",
                    "out_dir": str(out_dir),
                })
            }

            self.assertTrue(v2227.is_current_window_collector_busy_preflight(result))

    def test_classify_dry_run_and_live_branches(self):
        ready = v2227.classify({
            "execute": False,
            "preflight": {
                "v2226_manifest_pass": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        blocked = v2227.classify({
            "execute": False,
            "preflight": {
                "v2226_manifest_pass": False,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        self.assertEqual(ready["decision"], "v2227-boot-window-handoff-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2227-boot-window-handoff-dry-run-blocked")
        self.assertFalse(blocked["pass"])

        cases = [
            (
                {"execute": True, "live_block": "v2222-preflight-failed"},
                "v2227-boot-window-handoff-preflight-failed-no-flash",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": False}},
                "v2227-boot-window-handoff-rollback-selftest-failed",
                False,
            ),
            (
                {"execute": True, "live_block": "test-flash-failed", "rollback": {"ok": True, "selftest_ok": True}},
                "v2227-boot-window-handoff-test-flash-failed-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"diagnosis": {"kind": "property-root-missing"}},
                },
                "v2227-boot-window-helper-property-root-missing-rollback-pass",
                False,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": True}},
                },
                "v2227-boot-window-helper-parsed-rollback-pass",
                True,
            ),
            (
                {
                    "execute": True,
                    "rollback": {"ok": True, "selftest_ok": True},
                    "collect": {"parser": {"parsed_pass": False}},
                },
                "v2227-boot-window-helper-parse-incomplete-rollback-pass",
                False,
            ),
        ]
        for manifest, decision, passed in cases:
            with self.subTest(decision=decision):
                result = v2227.classify(manifest)
                self.assertEqual(result["decision"], decision)
                self.assertEqual(result["pass"], passed)


class ReportAndResidualState(unittest.TestCase):
    def manifest(self, **overrides):
        manifest = {
            "result": {"decision": "v2227-boot-window-handoff-dry-run-ready", "pass": True, "reason": "ready"},
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2227.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2227.ROLLBACK_EXPECT_VERSION,
            },
            "execute": False,
            "out_dir": "workspace/private/runs/kernel/v2227",
            "steps": [],
        }
        manifest.update(overrides)
        return manifest

    def test_render_report_includes_dry_run_plan_and_safety_scope(self):
        report = v2227.render_report(self.manifest(dry_run_commands={"postflight": ["a90ctl.py", "selftest"]}))

        self.assertIn("# Native Init V2227 A90 Boot-Window Handoff Runner", report)
        self.assertIn("Decision: `v2227-boot-window-handoff-dry-run-ready`", report)
        self.assertIn("Live mode requires `--execute` plus the exact confirmation token", report)
        self.assertIn("Dry-Run Command Plan", report)
        self.assertIn("does not flash, reboot", report)

    def test_render_report_includes_nonlog_no_return_diagnosis(self):
        report = v2227.render_report(self.manifest(
            execute=True,
            result={
                "decision": "v2227-boot-window-helper-parsed-rollback-pass",
                "pass": True,
                "reason": "parsed",
            },
            rollback={"ok": True, "selftest_ok": True},
            collect={
                "parser": {
                    "parsed_decision": "hit",
                    "parsed_pass": True,
                    "total_hits": 3,
                    "hit_event_total": 2,
                    "key_hit_event_total": 1,
                    "key_events": {
                        "uprobe:wlfw_start": {"total_hit_count": 1, "first_ts": "1.0"},
                        "uprobe:wlfw_service_request": {"total_hit_count": 0, "first_ts": None},
                        "uprobe:wlfw_cap_qmi": {"total_hit_count": 0, "first_ts": None},
                        "uprobe:wlfw_bdf_entry": {"total_hit_count": 0, "first_ts": None},
                    },
                },
                "diagnosis": {
                    "decision": "helper-artifacts-present",
                    "helper_exit_code": "0",
                    "helper_timed_out": "0",
                    "supervisor_result": "ok",
                    "wlan0_present": "0",
                    "nonlog_control_flow": {
                        "label": "peripheral-default-service-manager-call-no-return",
                        "pm_init_pm_client_register_call_hits": "1",
                        "pm_init_pm_client_register_retcheck_hits": "1",
                        "periph_default_service_manager_call_hits": "1",
                    },
                },
            },
        ))

        self.assertIn("Nonlog Control-Flow Summary", report)
        self.assertIn("peripheral-default-service-manager-call-no-return", report)
        self.assertIn("V2226 fixed the property-root setup failure", report)
        self.assertIn("service-manager/PM trio were intentionally not started", report)

    def test_residual_state_tracks_flash_rollback_and_blocked_cleanup(self):
        dry = v2227.residual_state(self.manifest())
        ok = v2227.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2226-from-native", "ok": True}],
            rollback={"ok": True, "selftest_ok": True, "attempt": "from-native"},
        ))
        bad = v2227.residual_state(self.manifest(
            execute=True,
            steps=[{"name": "flash-v2226-from-native", "ok": True}],
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
