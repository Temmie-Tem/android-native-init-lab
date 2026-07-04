from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta88 = load_script("workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py")


class ServerDistroWsta108OperatorServerStatusTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def wsta88_args(self, root: Path):
        return wsta88.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta88"),
            "--prepare-to-execute",
            "--ttl-sec",
            "300",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])

    def hardening_manifest(self) -> dict:
        return {
            "decision": runner.wsta90.PASS_DECISION,
            "manifest": {
                "state": "SERVICE_HARDENING_MANIFEST_SKELETON",
                "services": [
                    {"name": "dpublic-smoke-httpd"},
                    {"name": "cloudflared-quick-tunnel"},
                    {"name": "dropbear-admin-usb"},
                    {"name": "dpublic-hud"},
                    {"name": "wsta-native-uplink-helper"},
                ],
                "global_policy": {
                    "default_public_off": True,
                    "no_new_privs_default": True,
                    "capability_drop_required": True,
                    "seccomp_ready_for_profile_source": True,
                    "packet_filter_backend_required": False,
                    "root_login_policy": "replace-root-authorized-keys-before-always-on",
                },
                "blocking_before_enforcement": [
                    "staged service users/groups not live-proven",
                    "no-new-privs launcher not live-proven",
                    "syscall traces not captured",
                    "packet-filter backend not inventoried",
                ],
            },
        }

    def packet_filter_proof(self) -> dict:
        return {
            "decision": runner.wsta94.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta94-packet-filter-live-test",
            "checks": {
                "packet_filter_preflight_pass": True,
                "packet_filter_apply_pass": True,
                "packet_filter_default_drop_observed": True,
                "loopback_before_ok": True,
                "loopback_after_ok": True,
                "packet_filter_restore_pass": True,
                "packet_filter_restore_exact": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
            },
            "packet_filter_probe": {
                "parsed": {
                    "preflight_pass": True,
                    "apply_pass": True,
                    "v4_input_drop": True,
                    "v6_input_drop": True,
                    "v4_loopback_accept": True,
                    "v6_loopback_accept": True,
                    "restore_exact_v4": True,
                    "restore_exact_v6": True,
                    "probe_pass": True,
                },
                "stdout": "\n".join([
                    "packet_filter_backend=legacy-iptables",
                    "packet_filter_policy_class=loopback-default-drop",
                    "packet_filter_decision=packet-filter-preflight-pass",
                    "packet_filter_decision=packet-filter-loopback-default-drop-applied",
                    "A90WSTA94_POLICY_V4_INPUT_DROP=1",
                    "A90WSTA94_POLICY_V6_INPUT_DROP=1",
                    "A90WSTA94_RULE_V4_LOOPBACK_ACCEPT=1",
                    "A90WSTA94_RULE_V6_LOOPBACK_ACCEPT=1",
                    "A90WSTA94_LOOPBACK_AFTER_OK=1",
                    "packet_filter_decision=packet-filter-restored",
                    "A90WSTA94_RESTORE_EXACT_V4=1",
                    "A90WSTA94_RESTORE_EXACT_V6=1",
                    "A90WSTA94_PACKET_FILTER_PROBE_PASS",
                ]),
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def packet_filter_control_summary(self) -> dict:
        return {
            "run_dir": "workspace/private/runs/server-distro/packet-filter-control-live-test",
            "packet_filter_preflight_rc": 0,
            "packet_filter_preflight_parsed": {
                "packet_filter_backend": "legacy-iptables",
                "packet_filter_helper_version": "3",
                "packet_filter_secret_values_logged": "0",
            },
            "packet_filter_apply_loopback_default_drop_rc": 0,
            "packet_filter_apply_loopback_default_drop_parsed": {
                "packet_filter_backend": "legacy-iptables",
                "packet_filter_helper_version": "3",
                "packet_filter_policy_class": "loopback-default-drop",
                "packet_filter_control_ssh_accept": "1",
                "packet_filter_secret_values_logged": "0",
            },
            "packet_filter_restore_ok": True,
            "ssh_before_marker": True,
            "ssh_after_apply_marker": True,
            "post_mount_absent": True,
            "post_loop_absent": True,
            "post_dropbear_absent": True,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def launcher_proof(self) -> dict:
        return {
            "decision": runner.wsta110.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta110-service-launcher-live-test",
            "checks": {
                "public_default_off": True,
                "launcher_fail_closed_blocks": True,
                "launcher_exec_pass": True,
                "launcher_uid_gid_pass": True,
                "launcher_no_new_privs_pass": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
            },
            "launcher_probe": {
                "parsed": {
                    "public_enable_absent": True,
                    "unknown_service_blocks": True,
                    "command_required_blocks": True,
                    "child_no_new_privs": True,
                },
                "stdout": "\n".join([
                    "A90WSTA110_PUBLIC_ENABLE_ABSENT=1",
                    "A90WSTA110_UNKNOWN_BLOCKED=1",
                    "A90WSTA110_COMMAND_REQUIRED_BLOCKED=1",
                    "a90_service_launcher_decision=exec",
                    "a90_service_launcher_service=dpublic-smoke-httpd",
                    "a90_service_launcher_user=a90www",
                    "a90_service_launcher_no_new_privs=1",
                    "child_uid=3901",
                    "child_gid=3901",
                    "child_user=a90www",
                    "child_group=a90www",
                    "child_no_new_privs=1",
                    "child_cap_eff=0000000000000000",
                    "A90WSTA110_PROC_UNMOUNTED=1",
                    "A90WSTA110_PROOF_DONE",
                ]),
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def syscall_trace_proof(self) -> dict:
        return {
            "decision": runner.wsta114.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta117-server-only-wsta114-live-test",
            "checks": {
                "public_default_off": True,
                "strace_present": True,
                "trace_started": True,
                "loopback_get_ok": True,
                "trace_file_nonempty": True,
                "syscall_profile_nonempty": True,
                "syscall_core_observed": True,
                "trace_artifact_saved": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
            },
            "syscall_profile": {
                "schema": "a90-wsta114-syscall-profile-v1",
                "service": "dpublic-smoke-httpd",
                "scope": "smoke-service-only",
                "command_shape": (
                    "a90-service-launch dpublic-smoke-httpd strace -f "
                    "a90-dpublic-smoke-httpd 127.0.0.1 8080"
                ),
                "public_default_off": True,
                "loopback_get_ok": True,
                "no_new_privs": True,
                "cap_eff_zero": True,
                "core_syscalls": ["execve", "socket", "bind", "listen"],
                "core_syscalls_observed": True,
                "syscall_count": 18,
                "syscall_names": [
                    "accept",
                    "bind",
                    "brk",
                    "close",
                    "execve",
                    "getrandom",
                    "listen",
                    "mprotect",
                    "prlimit64",
                    "readlinkat",
                    "rseq",
                    "rt_sigaction",
                    "rt_sigreturn",
                    "set_robust_list",
                    "set_tid_address",
                    "setsockopt",
                    "socket",
                    "write",
                ],
                "trace_artifacts": {"all_saved": True, "private_artifact": True},
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def valid_args(self, root: Path, wsta88_json: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta108"),
            "--emit-server-status",
            "--wsta88-operator-workflow-json",
            str(wsta88_json),
            *extra,
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta108"),
            ]))

        self.assertEqual(result["decision"], "wsta108-blocked-emit-server-status-required")
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])

    def test_valid_wsta88_preflight_emits_server_status_without_hardening_manifest(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            result = runner.run(self.valid_args(root, root / "wsta88" / "wsta88_operator_workflow.json"))
            saved = json.loads((root / "wsta108" / "wsta108_operator_server_status.json").read_text(encoding="utf-8"))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        status = result["server_status"]
        self.assertEqual(status["state"], "SERVER_PROFILE_READY_DEFAULT_OFF")
        self.assertEqual(status["exposure"]["public_state"], "PUBLIC_OFF")
        self.assertFalse(status["exposure"]["live_execution_requested"])
        self.assertEqual(status["network_model"]["wifi_owner"], "native-init")
        self.assertEqual(status["network_model"]["debian_role"], "service-surface-consumer")
        self.assertFalse(status["network_model"]["handoff_required_for_wsta88"])
        self.assertTrue(status["packet_filter"]["ready"])
        self.assertEqual(status["hardening"]["state"], "NOT_SUPPLIED")
        self.assertFalse(result["checks"]["hardening_manifest_supplied"])
        self.assertIn("WSTA Operator Server Status", markdown)
        self.assertIn("Switch-root required for WSTA88: `false`", markdown)
        self.assertIn("Packet Filter", markdown)

    def test_valid_wsta88_and_wsta90_manifest_emits_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            self.write_json(manifest_path, self.hardening_manifest())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
            ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        self.assertEqual(hardening["state"], "SERVICE_HARDENING_MANIFEST_SKELETON")
        self.assertEqual(hardening["service_count"], 5)
        self.assertTrue(hardening["global_policy"]["no_new_privs_default"])
        self.assertTrue(hardening["global_policy"]["capability_drop_required"])
        self.assertEqual(hardening["packet_filter_proof"]["state"], "NOT_SUPPLIED")
        self.assertEqual(hardening["launcher_proof"]["state"], "NOT_SUPPLIED")
        self.assertTrue(result["checks"]["hardening_manifest_supplied"])
        self.assertFalse(result["checks"]["packet_filter_proof_supplied"])
        self.assertFalse(result["checks"]["packet_filter_loopback_live_proven"])
        self.assertFalse(result["checks"]["service_launcher_proof_supplied"])
        self.assertFalse(result["checks"]["service_launcher_smoke_live_proven"])
        self.assertFalse(result["checks"]["syscall_trace_proof_supplied"])
        self.assertFalse(result["checks"]["smoke_syscall_trace_live_proven"])

    def test_valid_wsta94_packet_filter_proofs_update_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            proof_path = root / "inputs" / "wsta94_result.json"
            control_path = root / "inputs" / "packet_filter_control_summary.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(proof_path, self.packet_filter_proof())
            self.write_json(control_path, self.packet_filter_control_summary())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
                "--packet-filter-control-summary-json",
                str(control_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["packet_filter_proof"]
        self.assertEqual(proof["state"], "PACKET_FILTER_LOOPBACK_AND_CONTROL_PLANE_LIVE_PROVEN")
        self.assertTrue(proof["loopback_live_proven"])
        self.assertEqual(proof["backend"], "legacy-iptables")
        self.assertEqual(proof["policy"], "loopback-default-drop")
        self.assertTrue(proof["default_drop_observed"])
        self.assertTrue(proof["restore_exact"])
        self.assertTrue(proof["control_proof"]["control_plane_live_proven"])
        self.assertEqual(proof["control_proof"]["helper_version"], "3")
        self.assertNotIn("packet-filter backend not inventoried", hardening["blocking_before_enforcement"])
        self.assertTrue(result["checks"]["packet_filter_proof_supplied"])
        self.assertTrue(result["checks"]["packet_filter_loopback_live_proven"])
        self.assertTrue(result["checks"]["packet_filter_control_summary_supplied"])
        self.assertTrue(result["checks"]["packet_filter_control_plane_live_proven"])
        self.assertIn("Loopback default-drop proof: `true`", markdown)
        self.assertIn("Control plane proof: `true`", markdown)

    def test_valid_wsta88_manifest_and_wsta110_proof_updates_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            proof_path = root / "inputs" / "wsta110_result.json"
            manifest = self.hardening_manifest()
            manifest["manifest"]["blocking_before_enforcement"].insert(0, "non-root users/groups not staged")
            self.write_json(manifest_path, manifest)
            self.write_json(proof_path, self.launcher_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(proof_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["launcher_proof"]
        self.assertEqual(proof["state"], "SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN")
        self.assertTrue(proof["smoke_live_proven"])
        self.assertEqual(proof["service"], "dpublic-smoke-httpd")
        self.assertEqual(proof["user"], "a90www")
        self.assertEqual(proof["uid"], 3901)
        self.assertTrue(proof["no_new_privs"])
        self.assertTrue(proof["cap_eff_zero"])
        self.assertTrue(proof["public_default_off"])
        self.assertTrue(proof["fail_closed_branches"]["unknown_service"])
        self.assertTrue(proof["fail_closed_branches"]["command_required"])
        self.assertIn("cloudflared-quick-tunnel", proof["remaining_profiles"])
        self.assertNotIn("non-root users/groups not staged", hardening["blocking_before_enforcement"])
        self.assertNotIn("no-new-privs launcher not live-proven", hardening["blocking_before_enforcement"])
        self.assertIn(
            "remaining service users/groups not live-proven beyond dpublic-smoke-httpd",
            hardening["blocking_before_enforcement"],
        )
        self.assertIn(
            "remaining service launchers not live-proven beyond dpublic-smoke-httpd",
            hardening["blocking_before_enforcement"],
        )
        self.assertTrue(result["checks"]["service_launcher_proof_supplied"])
        self.assertTrue(result["checks"]["service_launcher_smoke_live_proven"])
        self.assertIn("Smoke launcher proof: `true`", markdown)
        self.assertIn("Smoke launcher user: `a90www`", markdown)

    def test_valid_wsta88_manifest_and_wsta114_trace_proof_updates_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            proof_path = root / "inputs" / "wsta114_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(proof_path, self.syscall_trace_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta114-syscall-trace-proof-json",
                str(proof_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["syscall_trace_proof"]
        self.assertEqual(proof["state"], "SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN")
        self.assertTrue(proof["smoke_syscall_trace_live_proven"])
        self.assertEqual(proof["service"], "dpublic-smoke-httpd")
        self.assertEqual(proof["syscall_count"], 18)
        self.assertIn("bind", proof["syscall_names"])
        self.assertTrue(proof["trace_artifacts_saved"])
        self.assertNotIn("syscall traces not captured", hardening["blocking_before_enforcement"])
        self.assertIn(
            "remaining syscall traces not captured beyond dpublic-smoke-httpd",
            hardening["blocking_before_enforcement"],
        )
        self.assertTrue(result["checks"]["syscall_trace_proof_supplied"])
        self.assertTrue(result["checks"]["smoke_syscall_trace_live_proven"])
        self.assertIn("Smoke syscall trace proof: `true`", markdown)
        self.assertIn("Smoke syscall count: `18`", markdown)
        self.assertIn("Remaining syscall profiles: `cloudflared-quick-tunnel, dropbear-admin-usb, dpublic-hud`", markdown)

    def test_nonpass_wsta88_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta88_json = root / "inputs" / "wsta88_operator_workflow.json"
            self.write_json(wsta88_json, {"decision": "wsta88-blocked"})
            result = runner.run(self.valid_args(root, wsta88_json))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta88-workflow-not-pass")

    def test_nonpass_hardening_manifest_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            manifest = self.hardening_manifest()
            manifest["decision"] = "wsta90-blocked"
            self.write_json(manifest_path, manifest)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta90-manifest-not-pass")

    def test_nonpass_wsta94_packet_filter_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta94_result.json"
            proof = self.packet_filter_proof()
            proof["decision"] = "wsta94-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta94-packet-filter-proof-not-pass")

    def test_incomplete_wsta94_packet_filter_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta94_result.json"
            proof = self.packet_filter_proof()
            proof["packet_filter_probe"]["stdout"] = proof["packet_filter_probe"]["stdout"].replace(
                "packet_filter_backend=legacy-iptables",
                "",
            )
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta94-packet-filter-proof-incomplete")
        self.assertFalse(result["checks"]["packet_filter_loopback_live_proven"])

    def test_incomplete_packet_filter_control_summary_blocks_when_supplied(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            control_path = root / "inputs" / "packet_filter_control_summary.json"
            summary = self.packet_filter_control_summary()
            summary["ssh_after_apply_marker"] = False
            self.write_json(control_path, summary)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--packet-filter-control-summary-json",
                str(control_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-packet-filter-control-summary-incomplete")
        self.assertFalse(result["checks"]["packet_filter_control_plane_live_proven"])

    def test_nonpass_wsta110_launcher_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta110_result.json"
            proof = self.launcher_proof()
            proof["decision"] = "wsta110-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta110-service-launcher-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta110-launcher-proof-not-pass")

    def test_nonpass_wsta114_syscall_trace_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta114_result.json"
            proof = self.syscall_trace_proof()
            proof["decision"] = "wsta114-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta114-syscall-trace-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta114-syscall-trace-proof-not-pass")

    def test_incomplete_wsta110_launcher_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta110_result.json"
            proof = self.launcher_proof()
            proof["launcher_probe"]["stdout"] = proof["launcher_probe"]["stdout"].replace(
                "child_cap_eff=0000000000000000",
                "",
            )
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta110-service-launcher-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta110-launcher-proof-incomplete")
        self.assertFalse(result["checks"]["service_launcher_smoke_live_proven"])

    def test_incomplete_wsta114_syscall_trace_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta114_result.json"
            proof = self.syscall_trace_proof()
            proof["syscall_profile"]["syscall_names"].remove("listen")
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta114-syscall-trace-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta114-syscall-trace-proof-incomplete")
        self.assertFalse(result["checks"]["smoke_syscall_trace_live_proven"])

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            result = runner.run(self.valid_args(root, root / "wsta88" / "wsta88_operator_workflow.json"))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(wsta88.wsta80.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(wsta88.wsta80.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_work(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA108 host-only", payload)
        self.assertIn("--emit-server-status", payload)
        self.assertIn("--wsta88-operator-workflow-json", payload)
        self.assertIn("--wsta94-packet-filter-proof-json", payload)
        self.assertIn("--packet-filter-control-summary-json", payload)
        self.assertIn("--wsta110-service-launcher-proof-json", payload)
        self.assertIn("--wsta114-syscall-trace-proof-json", payload)

    def test_source_is_host_only_and_names_server_model(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("SERVER_PROFILE_READY_DEFAULT_OFF", source)
        self.assertIn("native-init", source)
        self.assertIn("service-surface-consumer", source)
        self.assertIn("wsta88-status-hud", source)
        self.assertIn("PACKET_FILTER_LOOPBACK_DEFAULT_DROP_LIVE_PROVEN", source)
        self.assertIn("SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN", source)
        self.assertIn("SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
