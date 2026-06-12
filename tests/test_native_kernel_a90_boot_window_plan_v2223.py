"""Regression tests for native_kernel_a90_boot_window_plan_v2223."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2223 = load_revalidation("native_kernel_a90_boot_window_plan_v2223")


class FileAndInventoryHelpers(unittest.TestCase):
    def test_sha256_file_and_load_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = root / "payload.bin"
            json_path = root / "data.json"
            data_path.write_bytes(b"a90\n")
            json_path.write_text('{"ok": true, "count": 3}', encoding="utf-8")

            self.assertEqual(
                v2223.sha256_file(data_path),
                "31c6cb20ec6951d335cf43112411a1a3ff3297f7b9b669f0d695700bd33bc4cd",
            )
            self.assertEqual(v2223.load_json(json_path), {"ok": True, "count": 3})

    def test_latest_v2222_summary_selects_newest_summary(self):
        old_private_runs = v2223.PRIVATE_RUNS
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runs = Path(tmp)
                older = runs / "v2222-boot-window-preflight-old" / "summary.json"
                newer = runs / "v2222-boot-window-preflight-new" / "summary.json"
                unrelated = runs / "v2223-boot-window-plan-new" / "summary.json"
                older.parent.mkdir()
                newer.parent.mkdir()
                unrelated.parent.mkdir()
                older.write_text("{}", encoding="utf-8")
                newer.write_text("{}", encoding="utf-8")
                unrelated.write_text("{}", encoding="utf-8")
                older.touch()
                newer.touch()
                unrelated.touch()
                # Make ordering deterministic even on coarse timestamp filesystems.
                import os

                os.utime(older, (100, 100))
                os.utime(newer, (200, 200))
                os.utime(unrelated, (300, 300))
                v2223.PRIVATE_RUNS = runs

                self.assertEqual(v2223.latest_v2222_summary(), newer)
        finally:
            v2223.PRIVATE_RUNS = old_private_runs

    def test_source_marker_audit_requires_markers_and_mode_guard(self):
        old_helper_source = v2223.HELPER_SOURCE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "a90_android_execns_probe.c"
                source.write_text(
                    "\n".join(
                        [
                            "wifi-companion-wlan-pd-cnss-output-visibility-start-only",
                            "--allow-wlan-pd-cnss-output-visibility",
                            "append_wlan_pd_cnss_nonlog_control_flow_summary",
                            "cnss_wlfw_uprobe_collect_trace",
                            "--result-output-path",
                            "is_wifi_companion_wlan_pd_cnss_output_visibility_mode",
                            "wifi-companion-wlan-pd-cnss-output-visibility-start-only requires --allow-wlan-pd-cnss-output-visibility",
                            "--allow-wlan-pd-cnss-output-visibility requires wifi-companion-wlan-pd-cnss-output-visibility-start-only mode",
                        ]
                    ),
                    encoding="utf-8",
                )
                v2223.HELPER_SOURCE = source

                audit = v2223.source_marker_audit()

                self.assertTrue(audit["all_present"])
                self.assertTrue(audit["mode_guard_ok"])
                self.assertEqual(audit["allow_flag"]["count"], 3)
                self.assertTrue(audit["collect_func"]["present"])
        finally:
            v2223.HELPER_SOURCE = old_helper_source

    def test_boot_image_inventory_records_existing_and_missing_candidates(self):
        old_boot_inputs = v2223.BOOT_INPUTS
        old_candidates = v2223.BASELINE_BOOT_CANDIDATES
        try:
            with tempfile.TemporaryDirectory() as tmp:
                boot_inputs = Path(tmp)
                existing = boot_inputs / "boot_linux_v2189_security_p0_stage_fix.img"
                existing.write_bytes(b"boot")
                v2223.BOOT_INPUTS = boot_inputs
                v2223.BASELINE_BOOT_CANDIDATES = [
                    "boot_linux_v2189_security_p0_stage_fix.img",
                    "missing.img",
                ]

                rows = v2223.boot_image_inventory()

                self.assertEqual(len(rows), 2)
                self.assertTrue(rows[0]["exists"])
                self.assertEqual(rows[0]["size"], 4)
                self.assertEqual(rows[0]["sha256"], "4509beb0ab401d71fa4a5cd94a55c9a74f13332776ae4019c5bfc4c2005157ff")
                self.assertEqual(rows[0]["mode"], oct(existing.stat().st_mode & 0o777))
                self.assertFalse(rows[1]["exists"])
                self.assertNotIn("sha256", rows[1])
        finally:
            v2223.BOOT_INPUTS = old_boot_inputs
            v2223.BASELINE_BOOT_CANDIDATES = old_candidates


class PlanBuilders(unittest.TestCase):
    def test_contract_summary_loads_linked_contract(self):
        old_repo_root = v2223.REPO_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                summary_path = root / "run" / "summary.json"
                contract_path = root / "run" / "contract.json"
                summary_path.parent.mkdir()
                contract_path.write_text('{"current_preflight_pass": true}', encoding="utf-8")
                summary_path.write_text(
                    json.dumps({"contract_path": str(contract_path.relative_to(root)), "pass": True}),
                    encoding="utf-8",
                )
                v2223.REPO_ROOT = root

                summary, contract = v2223.contract_summary(summary_path)

                self.assertTrue(summary["pass"])
                self.assertEqual(contract, {"current_preflight_pass": True})
        finally:
            v2223.REPO_ROOT = old_repo_root

    def test_build_capture_plan_ready_requires_preflight_source_and_v2189(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "v2223-boot-window-plan-test"
            source_summary = Path(tmp) / "v2222" / "summary.json"
            source_summary.parent.mkdir()
            source_summary.write_text("{}", encoding="utf-8")
            summary = {"pass": True, "contract_path": "workspace/private/runs/kernel/v2222/contract.json"}
            contract = {
                "current_preflight_pass": True,
                "expected_event_sequence": ["a90cnss:wlfw_start"],
                "forbidden_without_new_approval": ["probe_write_user execution"],
            }
            audit = {"all_present": True}
            boot_images = [
                {
                    "path": "workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img",
                    "exists": True,
                }
            ]

            plan = v2223.build_capture_plan(
                out_dir=out_dir,
                v2222_summary_path=source_summary,
                v2222_summary=summary,
                v2222_contract=contract,
                source_audit=audit,
                boot_images=boot_images,
            )

            self.assertTrue(plan["ready_for_approval"])
            self.assertTrue(plan["host_only_plan"])
            self.assertTrue(plan["requires_explicit_user_approval"])
            self.assertEqual(plan["expected_event_sequence"], ["a90cnss:wlfw_start"])
            self.assertEqual(plan["forbidden_without_new_approval"], ["probe_write_user execution"])
            self.assertEqual(plan["baseline_boot_images"], boot_images)
            self.assertEqual(plan["helper_runtime"]["mode"], "wifi-companion-wlan-pd-cnss-output-visibility-start-only")
            self.assertIn("--allow-wlan-pd-cnss-output-visibility", plan["execution_routes"]["manual_late_window_command_for_debug_only"])
            self.assertFalse(plan["next_artifact_gap"]["dedicated_v2223_test_boot_image_exists"])

    def test_build_capture_plan_not_ready_without_v2189_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "v2223-boot-window-plan-test"
            source_summary = Path(tmp) / "summary.json"
            source_summary.write_text("{}", encoding="utf-8")

            plan = v2223.build_capture_plan(
                out_dir=out_dir,
                v2222_summary_path=source_summary,
                v2222_summary={"pass": True},
                v2222_contract={"current_preflight_pass": True},
                source_audit={"all_present": True},
                boot_images=[{"path": "workspace/private/inputs/boot_images/boot_linux_v724.img", "exists": True}],
            )

            self.assertFalse(plan["ready_for_approval"])

    def test_residual_state_is_host_only_and_safe(self):
        residual = v2223.residual_state({})

        self.assertFalse(residual["device_touched"])
        self.assertFalse(residual["flash_reboot"])
        self.assertTrue(residual["rollback_ok"])
        self.assertEqual(residual["rollback_attempt"], "not-needed-host-only-plan")
        self.assertTrue(residual["selftest_ok"])
        self.assertFalse(residual["tracefs_control_write"])
        self.assertFalse(residual["bpf_attach"])
        self.assertFalse(residual["partition_write"])


if __name__ == "__main__":
    unittest.main()
