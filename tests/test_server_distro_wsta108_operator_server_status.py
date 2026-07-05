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

    def dropbear_admin_proof(self) -> dict:
        return {
            "decision": runner.wsta120.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta120-dropbear-admin-live-test",
            "checks": {
                "explicit_live_gate": True,
                "baseline_selftest_fail_zero": True,
                "remote_image_ready": True,
                "chroot_mount_ready": True,
                "admin_stage_pass": True,
                "admin_ssh_pass": True,
                "root_ssh_rejected": True,
                "admin_key_cleanup_ok": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
            },
            "admin_stage_parse": {
                "root_authorized_keys_absent": True,
                "admin_passwd_line": True,
                "admin_group_line": True,
                "admin_shadow_line": True,
                "admin_authorized_keys": True,
                "dropbear_present": True,
                "dropbear_command_safe": True,
                "dropbear_alive": True,
                "dropbear_listen": True,
            },
            "admin_ssh_parse": {
                "ssh_ok": True,
                "uid_3903": True,
                "gid_3903": True,
                "user_a90admin": True,
                "group_a90admin": True,
            },
            "admin_key_cleanup_parse": {
                "cleanup_done": True,
                "admin_keys_absent": True,
                "dropbear_absent": False,
            },
            "postcheck_parse": {
                "done": True,
                "dropbear_absent": True,
                "mount_absent": True,
                "loop_node_absent": True,
            },
            "root_ssh": {
                "returncode": 255,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def dropbear_admin_syscall_proof(self) -> dict:
        return {
            "decision": runner.wsta151.PASS_DECISION,
            "source_run_dir": "workspace/private/runs/server-distro/wsta151-dropbear-admin-syscall-test",
            "service": "dropbear-admin-usb",
            "scope": "dropbear-admin-usb-daemon",
            "daemon": "/usr/sbin/dropbear",
            "daemon_privilege_model": "root-boundary-auth-daemon",
            "bind": "192.168.7.2:2222",
            "network_scope": "usb-ncm-admin-only",
            "uid": 3903,
            "gid": 3903,
            "admin_login_uid_gid_proven": True,
            "root_ssh_rejected": True,
            "root_authorized_keys_absent": True,
            "password_login_disabled": True,
            "root_login_disabled": True,
            "forwarding_disabled": True,
            "core_syscalls_observed": True,
            "accept_observed": True,
            "core_syscalls": list(runner.wsta151.CORE_SYSCALLS),
            "accept_syscalls": list(runner.wsta151.ACCEPT_SYSCALLS),
            "syscall_count": 8,
            "syscall_names": [
                "accept",
                "bind",
                "brk",
                "close",
                "execve",
                "listen",
                "socket",
                "write",
            ],
            "trace_artifacts_saved": True,
            "raw_trace_sha256": "raw-sha",
            "syscall_list_sha256": "syscalls-sha",
            "dropbear_log_sha256": "log-sha",
            "checks": {
                "source_decision_pass": True,
                "source_no_forbidden_device_mutation": True,
                "strace_image_sha_match": True,
                "admin_boundary_proven": True,
                "daemon_policy_proven": True,
                "core_syscalls_proven": True,
                "accept_syscall_proven": True,
                "trace_artifacts_saved": True,
                "log_policy_clean": True,
                "cleanup_ok": True,
                "final_health_clean": True,
                "redaction_clean": True,
            },
            "public_url_value_logged": False,
            "admin_public_key_value_logged": False,
            "secret_values_logged": 0,
        }

    def seccomp_smoke_proof(self) -> dict:
        return {
            "decision": runner.wsta208.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta208-real-service-seccomp-test",
            "checks": {
                "explicit_live_gate": True,
                "fresh_health_valid": True,
                "helper_exec_after_load_compiled": True,
                "seccomp_asset_inputs_valid": True,
                "seccomp_assets_staged": True,
                "seccomp_real_service_markers": True,
                "service_functional_under_seccomp": True,
                "chroot_cleanup_ok": True,
                "post_health_valid": True,
            },
            "safety": {
                "seccomp_filter_loaded": True,
                "seccomp_enforced": True,
                "service_functional_under_seccomp": True,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "public_smoke": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "postcheck_parse": {
                "done": True,
                "dropbear_absent": True,
                "mount_absent": True,
                "loop_node_absent": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def seccomp_dropbear_proof(self) -> dict:
        return {
            "decision": runner.wsta209.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta209-dropbear-admin-seccomp-test",
            "checks": {
                "explicit_live_gate": True,
                "fresh_health_valid": True,
                "helper_exec_after_load_compiled": True,
                "seccomp_asset_inputs_valid": True,
                "seccomp_assets_installed": True,
                "admin_seccomp_stage_pass": True,
                "seccomp_dropbear_markers": True,
                "admin_ssh_pass": True,
                "root_ssh_rejected": True,
                "admin_seccomp_cleanup_ok": True,
                "chroot_cleanup_ok": True,
                "post_health_valid": True,
            },
            "safety": {
                "seccomp_filter_loaded": True,
                "seccomp_enforced": True,
                "service_functional_under_seccomp": True,
                "root_login_negative_test": True,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "public_smoke": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "admin_public_key_value_logged": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "admin_seccomp_stage_parse": {
                "seccomp_dropbear_markers": True,
                "dropbear_command_safe": True,
            },
            "admin_ssh_parse": {
                "ssh_ok": True,
                "uid_3903": True,
                "gid_3903": True,
            },
            "cleanup_parse": {
                "dropbear_cleanup_ok": True,
            },
            "postcheck_parse": {
                "done": True,
                "dropbear_absent": True,
                "mount_absent": True,
                "loop_node_absent": True,
            },
            "public_url_value_logged": False,
            "admin_public_key_value_logged": False,
            "secret_values_logged": 0,
        }

    def native_uplink_boundary_policy(self) -> dict:
        return {
            "decision": runner.NATIVE_UPLINK_BOUNDARY_POLICY_DECISION,
            "policy": {
                "schema": "a90-wsta212-native-uplink-boundary-policy-v1",
                "state": runner.NATIVE_UPLINK_BOUNDARY_POLICY_STATE,
                "service": "wsta-native-uplink-helper",
                "classification": "native-owned-root-boundary",
                "allowed_ops": ["status", "scan"],
                "denied_ops": [
                    "connect",
                    "associate",
                    "association",
                    "dhcp",
                    "ping",
                    "public-tunnel",
                    "tunnel",
                ],
                "debian_service_launcher_allowed": False,
                "debian_service_seccomp_target": False,
            },
            "checks": {
                "manifest_service_boundary_preserve": True,
                "wsta22_live_status_no_credentials_or_public": True,
                "wsta22_live_scan_redacted_no_connect_or_public": True,
                "seccomp_exclusion_native_uplink_not_launchable_under_debian_seccomp": True,
                "helper_source_denies_before_request_write": True,
                "policy_debian_cannot_start_connectivity": True,
                "policy_launcher_not_debian_launchable": True,
            },
            "safety": {
                "device_action": False,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "wifi_association": False,
                "dhcp": False,
                "ping": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "rootfs_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def apparmor_feasibility(self) -> dict:
        return {
            "decision": runner.APPARMOR_FEASIBILITY_DECISION,
            "apparmor": {
                "schema": "a90-wsta214-apparmor-feasibility-v1",
                "state": runner.APPARMOR_UNAVAILABLE_STATE,
                "recommendation": "do-not-use-apparmor-as-immediate-d-harden-lever",
                "preferred_current_hardening_lever": "legacy-iptables-loopback-default-drop",
                "kernel_config_ready": False,
                "runtime_observed": False,
                "userspace_staged": False,
                "profile_source_ready": False,
            },
            "checks": {
                "audit_schema_ok": True,
                "audit_state_known": True,
                "audit_kernel_config_recorded": True,
                "audit_runtime_observation_recorded": True,
                "audit_userspace_staging_recorded": True,
                "audit_unavailable_has_blocking_evidence": True,
                "audit_ready_requires_kernel_and_runtime_or_userspace": True,
                "audit_profile_load_stays_disabled": True,
                "audit_redaction_clean": True,
            },
            "safety": {
                "device_action": False,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "rootfs_mount": False,
                "package_install": False,
                "lsm_profile_load": False,
                "userdata_touch": False,
                "switch_root": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def default_drop_hardening_policy(self) -> dict:
        return {
            "decision": runner.DEFAULT_DROP_HARDENING_POLICY_DECISION,
            "policy": {
                "schema": "a90-wsta216-legacy-iptables-default-drop-hardening-policy-v1",
                "state": runner.DEFAULT_DROP_HARDENING_POLICY_STATE,
                "hardening_lever": "legacy-iptables-loopback-default-drop",
                "backend": "legacy-iptables",
                "policy": "loopback-default-drop",
                "activation": "explicit-operator-gated",
                "default_public_off": True,
                "live_execution_requested": False,
                "packet_filter_mutation_by_wsta216": False,
            },
            "checks": {
                "operator_status_packet_filter_proof_state": True,
                "operator_status_required_next_actions_present": True,
                "wsta94_packet_filter_default_drop_observed": True,
                "wsta94_packet_filter_established_related_rule_observed": True,
                "control_summary_ssh_before_after_apply": True,
                "source_wiring_wsta42_applies_before_cloudflared": True,
                "source_wiring_wsta42_restores_in_finally": True,
                "source_wiring_wsta79_accepts_contract": True,
                "policy_state_ok": True,
                "policy_activation_explicit": True,
                "policy_default_public_off": True,
                "policy_no_live_execution": True,
                "policy_restore_exact_required": True,
                "policy_apply_before_public_exposure": True,
                "policy_restore_before_public_off_success": True,
                "policy_live_gate_required_for_apply": True,
                "policy_wsta216_does_not_mutate_filters": True,
                "policy_attended_gate_required": True,
                "policy_redaction_clean": True,
            },
            "safety": {
                "device_action": False,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "public_smoke": False,
                "packet_filter_mutation": False,
                "rootfs_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def attended_default_drop_live_proof(self) -> dict:
        def wsta55_cycle() -> dict:
            return {
                "decision": runner.WSTA55_LIVE_DECISION,
                "gate_decision": "ok",
                "checks": {
                    "public_smoke_ok": True,
                    "ttl_expiry_stops_public": True,
                    "packet_filter_restore_ok": True,
                    "final_selftest_fail_zero": True,
                },
                "image_prep": {
                    "work_restore_attempted": True,
                },
                "ttl_expiry": {
                    "forced_for_wsta55": True,
                    "ttl_expiry_stops_public": True,
                    "public_state_after_expiry": "PUBLIC_OFF",
                    "lease_id_present": True,
                    "lease_id_value_redacted": True,
                    "secret_values_logged": 0,
                },
            }

        packet_filter_hardening = {
            "state": "PACKET_FILTER_REQUIRED_DEFAULT_OFF",
            "activation": "explicit-operator-gated",
            "default_public_off": True,
            "backend": "legacy-iptables",
            "policy": "loopback-default-drop",
            "apply_before": "public-exposure-start",
            "required_sequence": [
                "preflight-helper",
                "save-existing-rules-before-mutation",
                "apply-loopback-default-drop-before-public-exposure",
                "restore-exact-rules-before-public-off-success",
            ],
            "restore_on": ["manual-stop", "retire", "failure-cleanup"],
            "secret_values_logged": 0,
        }
        return {
            "decision": runner.ATTENDED_DEFAULT_DROP_LIVE_DECISION,
            "gate_decision": "ok",
            "run_dir": "workspace/private/runs/server-distro/wsta219-attended-live-test",
            "checks": {
                "default_public_off": True,
                "explicit_live_gate": True,
                "live_execution_requested": True,
                "packet_filter_hardening_ready": True,
                "wsta80_preflight_pass": True,
                "wsta80_live_pass": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "status_hud": {
                "public_state": "PUBLIC_OFF",
                "default_public_off": True,
                "live_execution_requested": True,
                "packet_filter": {
                    "state": "PACKET_FILTER_REQUIRED_DEFAULT_OFF",
                    "ready": True,
                    "backend": "legacy-iptables",
                    "policy": "loopback-default-drop",
                    "apply_before": "public-exposure-start",
                    "restore_on": ["manual-stop", "retire", "failure-cleanup"],
                },
                "manual_stop": {
                    "requested": True,
                    "cleanup_ok": True,
                    "public_state_after_stop": "PUBLIC_OFF",
                    "state": "CLEANED_PUBLIC_OFF",
                },
            },
            "workflow": {
                "packet_filter_hardening_ready": True,
                "packet_filter_hardening": packet_filter_hardening,
            },
            "wsta80_redacted": {
                "decision": runner.WSTA80_LIVE_DECISION,
                "gate_decision": "ok",
                "checks": {
                    "ack_packet_filter_mutation": True,
                    "force_packet_filter_restore_proof": True,
                    "packet_filter_hardening_ready": True,
                },
                "wsta58_redacted": {
                    "decision": runner.WSTA58_LIVE_DECISION,
                    "gate_decision": "ok",
                    "checks": {
                        "initial_packet_filter_restore_ok": True,
                        "renewal_packet_filter_restore_ok": True,
                        "manual_stop_cleanup_ok": True,
                        "manual_stop_public_state_off": True,
                    },
                    "initial": wsta55_cycle(),
                    "renewal": wsta55_cycle(),
                },
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def cloudflared_egress_allowlist_policy(self) -> dict:
        return {
            "decision": runner.wsta221.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta221-egress-policy-test",
            "policy": {
                "schema": runner.wsta221.POLICY_SCHEMA,
                "state": runner.wsta221.POLICY_STATE,
                "hardening_lever": runner.wsta221.HARDENING_LEVER,
                "service": runner.wsta221.SERVICE,
                "backend": "legacy-iptables",
                "policy": "cloudflared-egress-allowlist",
                "activation": "explicit-operator-gated-after-default-drop",
                "default_public_off": True,
                "live_execution_requested": False,
                "packet_filter_mutation_by_wsta221": False,
                "target_identity": {
                    "user": "a90tunnel",
                    "uid": 3902,
                    "gid": 3902,
                },
                "policy_contract": {
                    "preserve_existing_input_default_drop": True,
                    "apply_after_loopback_default_drop": True,
                    "fail_closed_if_owner_match_unavailable": True,
                    "restore_exact_rules_before_public_off_success": True,
                    "control_plane_must_survive_apply": True,
                    "forbid_public_url_logging": True,
                    "forbid_secret_logging": True,
                },
                "next_live_gate_requirements": [
                    "preflight iptables owner match and rule restore support",
                    "derive redacted DNS/TLS egress route in live session",
                ],
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "checks": {
                "operator_status_ready": True,
                "cloudflared_model_ready": True,
                "cloudflared_runtime_ready": True,
                "policy_ready": True,
            },
            "safety": {
                "device_action": False,
                "packet_filter_mutation": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def cloudflared_egress_allowlist_live_proof(self) -> dict:
        def wsta55_cycle() -> dict:
            return {
                "decision": runner.WSTA55_LIVE_DECISION,
                "gate_decision": "ok",
                "checks": {
                    "public_smoke_ok": True,
                    "ttl_expiry_stops_public": True,
                    "packet_filter_restore_ok": True,
                    "final_selftest_fail_zero": True,
                    "wsta45_pass": True,
                    "dpublic_cleanup_ok": True,
                    "native_uplink_profile_cleanup_ok": True,
                    "chroot_cleanup_ok": True,
                    "wsta48_all_pass": True,
                    "wsta48_redaction_ok": True,
                    "public_url_value_logged": False,
                    "secret_values_logged": 0,
                },
                "image_prep": {
                    "work_restore_attempted": True,
                },
                "ttl_expiry": {
                    "forced_for_wsta55": True,
                    "ttl_expiry_stops_public": True,
                    "public_state_after_expiry": "PUBLIC_OFF",
                    "lease_id_present": True,
                    "lease_id_value_redacted": True,
                    "secret_values_logged": 0,
                },
            }

        dns4_count = 30
        tls4_count = 2
        return {
            "decision": runner.wsta226.LIVE_PASS_DECISION,
            "gate_decision": "ok",
            "run_dir": "workspace/private/runs/server-distro/wsta229-egress-live-test",
            "checks": {
                "explicit_live_gate": True,
                "live_execution_requested": True,
                "route_artifact_ready": True,
                "route_schema_ok": True,
                "route_state_ok": True,
                "route_dns4_present": True,
                "route_tls4_present": True,
                "route_route_values_private": True,
                "route_route_values_logged_false": True,
                "route_public_url_not_logged": True,
                "route_secrets_not_logged": True,
                "route_redaction_clean_public_view": True,
                "wsta88_live_pass": True,
            },
            "route_summary": {
                "schema": runner.wsta226.ROUTE_SCHEMA,
                "state": runner.wsta226.ROUTE_STATE,
                "dns4_count": dns4_count,
                "tls4_count": tls4_count,
                "route_values_private": True,
                "route_values_logged": False,
                "route_values_redacted": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "wsta88_redacted": {
                "decision": runner.wsta88.PASS_DECISION,
                "gate_decision": "ok",
                "checks": {
                    "cloudflared_egress_allowlist_enabled": True,
                    "force_cloudflared_egress_allowlist_proof": True,
                    "cloudflared_egress_dns4_count": dns4_count,
                    "cloudflared_egress_tls4_count": tls4_count,
                    "cloudflared_egress_route_values_redacted": True,
                    "default_public_off": True,
                    "live_execution_requested": True,
                    "wsta80_preflight_pass": True,
                    "wsta80_live_pass": True,
                    "public_url_value_logged": False,
                    "secret_values_logged": 0,
                },
                "status_hud": {
                    "public_state": "PUBLIC_OFF",
                    "default_public_off": True,
                    "live_execution_requested": True,
                    "manual_stop": {
                        "cleanup_ok": True,
                        "public_state_after_stop": "PUBLIC_OFF",
                    },
                },
                "wsta80_redacted": {
                    "decision": runner.WSTA80_LIVE_DECISION,
                    "gate_decision": "ok",
                    "checks": {
                        "ack_packet_filter_mutation": True,
                        "force_packet_filter_restore_proof": True,
                        "cloudflared_egress_allowlist_enabled": True,
                        "force_cloudflared_egress_allowlist_proof": True,
                        "cloudflared_egress_dns4_count": dns4_count,
                        "cloudflared_egress_tls4_count": tls4_count,
                        "cloudflared_egress_route_values_redacted": True,
                        "wsta58_pass": True,
                        "public_url_value_logged": False,
                        "secret_values_logged": 0,
                    },
                    "wsta58_redacted": {
                        "decision": runner.WSTA58_LIVE_DECISION,
                        "gate_decision": "ok",
                        "checks": {
                            "initial_wsta55_pass": True,
                            "renewal_wsta55_pass": True,
                            "initial_packet_filter_restore_ok": True,
                            "renewal_packet_filter_restore_ok": True,
                            "manual_stop_cleanup_ok": True,
                            "manual_stop_public_state_off": True,
                            "wsta48_all_pass": True,
                            "wsta48_redaction_ok": True,
                            "public_url_value_logged": False,
                            "secret_values_logged": 0,
                        },
                        "initial": wsta55_cycle(),
                        "renewal": wsta55_cycle(),
                        "manual_stop": {
                            "ok": True,
                            "manual_stop_public_state": "PUBLIC_OFF",
                            "public_url_value_logged": False,
                            "secret_values_logged": 0,
                        },
                    },
                },
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def cloudflared_model_proof(self) -> dict:
        model = runner.wsta122.cloudflared_service_model()
        return {
            "decision": runner.wsta122.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta122-cloudflared-service-model-test",
            "cloudflared_service_model": model,
            "checks": runner.wsta122.validate_model(model),
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def cloudflared_runtime_proof(self) -> dict:
        return {
            "decision": runner.wsta125.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta125-runtime-live-test",
            "checks": {
                "wsta28_precondition_pass": True,
                "native_uplink_confirmed": True,
                "default_route_wlan0": True,
                "resolver_ready": True,
                "egress_route_ready": True,
                "packet_filter_preflight_pass": True,
                "packet_filter_apply_pass": True,
                "runtime_probe_completed": True,
                "cloudflared_uid_gid_pass": True,
                "cloudflared_no_new_privs_pass": True,
                "cloudflared_cap_eff_zero_pass": True,
                "cloudflared_command_shape_pass": True,
                "cloudflared_outbound_only_pass": True,
                "private_url_artifact_saved": True,
                "trace_file_nonempty": True,
                "syscall_profile_nonempty": True,
                "syscall_core_observed": True,
                "trace_artifact_saved": True,
                "runtime_cleanup_ok": True,
                "packet_filter_restore_pass": True,
                "uplink_service_stop_pass": True,
                "native_uplink_helper_cleanup_ok": True,
                "native_uplink_profile_cleanup_ok": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
            },
            "cloudflared_runtime_profile": {
                "schema": "a90-wsta124-cloudflared-runtime-profile-v1",
                "service": "cloudflared-quick-tunnel",
                "scope": "cloudflared-quick-tunnel-runtime",
                "user": "a90tunnel",
                "uid": 3902,
                "gid": 3902,
                "uid_gid_proven": True,
                "no_new_privs": True,
                "cap_eff_zero": True,
                "command_shape_proven": True,
                "outbound_only": True,
                "outbound_observed": True,
                "socket_outbound_hint": False,
                "udp_outbound": False,
                "private_url_artifact": True,
                "core_syscalls": ["execve", "socket", "connect"],
                "core_syscalls_observed": True,
                "syscall_count": 52,
                "syscall_names": ["connect", "execve", "socket"],
                "trace_artifacts": {"all_saved": True, "private_artifact": True},
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "private_url_artifact": {
                "url_artifact_saved": True,
                "url_len": 68,
                "private_path": "workspace/private/runs/server-distro/wsta125-runtime-live-test/wsta124-cloudflared-public-url.txt",
                "stdout_redacted": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "trace_artifacts": {
                "all_saved": True,
                "private_artifact": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def hud_model_proof(self) -> dict:
        model = runner.wsta127.hud_service_model()
        return {
            "decision": runner.wsta127.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta127-dpublic-hud-model-test",
            "hud_service_model": model,
            "checks": runner.wsta127.validate_model(model),
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def hud_presenter_model_proof(self) -> dict:
        model = runner.wsta130.presenter_architecture_model()
        return {
            "decision": runner.wsta130.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta130-dpublic-hud-presenter-model-test",
            "presenter_architecture_model": model,
            "checks": runner.wsta130.validate_model(model),
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def hud_presenter_live_proof(self) -> dict:
        proof = {
            "decision": runner.wsta137.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta137-dpublic-native-presenter-live-test",
            "source_run_dir": "workspace/private/runs/server-distro/wsta137-source-live-test",
            "candidate": {
                "init_version": runner.wsta137.INIT_VERSION,
                "init_build": runner.wsta137.INIT_BUILD,
                "boot_image": runner.wsta137.HELPER_BOOT_IMAGE,
                "boot_sha256": runner.wsta137.BOOT_SHA256,
            },
            "checked_flash": {
                "used_checked_helper": True,
                "local_sha_match": True,
                "remote_sha_match": True,
                "boot_readback_sha_match": True,
                "booted_v3398": True,
                "boot_ok": True,
                "selftest_fail_zero": True,
                "transport_serial_ready": True,
                "transport_tcpctl_ready": True,
            },
            "validate_proof": {
                "intent_schema": runner.wsta137.INTENT_SCHEMA,
                "sequence": 13701,
                "age_ms": 653,
                "intent_valid": True,
                "forbidden_fields_reject": True,
                "unknown_fields_reject": True,
                "stale_after_ms": runner.wsta137.STALE_AFTER_MS,
                "stale_after_marker": True,
                "presenter_owner_native_root": True,
                "debian_direct_kms_zero": True,
                "validate_only": True,
            },
            "present_proof": {
                "sequence": 13702,
                "age_ms": 556,
                "intent_valid": True,
                "present_begin_frame_rc_zero": True,
                "present_rc_zero": True,
                "present_done": True,
                "framebuffer": "1080x2400",
                "crtc": 133,
            },
            "reject_proof": {
                "forbidden_command_rejected": True,
                "forbidden_rc": -1,
                "stale_rejected": True,
                "stale_rc": -110,
                "stale_age_ms": 102866,
                "stale_after_ms": runner.wsta137.STALE_AFTER_MS,
            },
            "final_health": {
                "v3398_resident": True,
                "selftest_fail_zero": True,
                "transport_serial_ready": True,
                "transport_tcpctl_ready": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        proof["checks"] = runner.wsta137.validate_proof(proof)
        return proof

    def hud_presenter_handoff_proof(self) -> dict:
        proof = {
            "decision": runner.wsta144.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta144-dpublic-hud-shared-run-bind-test",
            "source_run_dir": "workspace/private/runs/server-distro/wsta144-source-live-test",
            "candidate": {
                "init_version": runner.wsta144.INIT_VERSION,
                "init_build": runner.wsta144.INIT_BUILD,
                "boot_image": runner.wsta144.BOOT_IMAGE,
                "boot_sha256": runner.wsta144.BOOT_SHA256,
            },
            "checked_flash": {
                "used_checked_helper": True,
                "local_sha_match": True,
                "remote_sha_match": True,
                "boot_readback_sha_match": True,
                "booted_v3401": True,
                "boot_ok": True,
                "selftest_fail_zero": True,
                "transport_serial_ready": True,
                "transport_tcpctl_ready": True,
            },
            "native_presenter_pre_handoff": {
                "pid": 625,
                "shared_run_marker": True,
                "shared_run_tmpfs_mounted": True,
                "status_drm_fd": True,
                "debian_direct_kms_zero": True,
                "pre_sequence": runner.wsta144.PRE_HANDOFF_SEQUENCE,
                "pre_present_rc": 0,
            },
            "handoff": {
                "switch_root_exec_reached": True,
                "presenter_preserved": True,
                "stale_drm_owners_killed": True,
                "shared_run_bind_ok": True,
                "shared_run_same_dev": True,
                "shared_run_same_ino": True,
                "firstboot_intent_presented": True,
            },
            "debian": {
                "ssh_ready": True,
                "pid1_comm_init": True,
                "proc1_exe_usr_sbin_init": True,
                "debian_version": "12.14",
                "root_is_userdata_ext4": True,
                "run_dir_root_a90hud_1770": True,
            },
            "shared_run_compare": {
                "same_dev": True,
                "same_ino": True,
                "tmpfs": True,
                "root_a90hud_1770": True,
            },
            "drm_ownership": {
                "presenter_alive": True,
                "presenter_pid": 625,
                "presenter_exe_deleted": True,
                "presenter_has_card0_fd": True,
                "drm_before_lines": ["DRMFD pid=625 user=root comm=init fd=3 target=/dev/dri/card0 (deleted)"],
                "drm_after_lines": ["DRMFD pid=625 user=root comm=init fd=3 target=/dev/dri/card0 (deleted)"],
                "sole_drm_owner_before": True,
                "sole_drm_owner_after": True,
            },
            "a90hud_intent_writer": {
                "identity": True,
                "launcher_exec": True,
                "no_network_intent": True,
                "no_new_privs": True,
                "uid_3904": True,
                "gid_3904": True,
                "cap_eff_zero": True,
                "no_drm_fd": True,
                "intent_written": True,
                "intent_sequence": runner.wsta144.DEBIAN_SEQUENCE,
                "intent_owner_a90hud": True,
                "intent_schema": runner.wsta144.INTENT_SCHEMA,
            },
            "presenter_consumption": {
                "status_before_sequence": 1,
                "status_before_present_rc": 0,
                "status_after_sequence": runner.wsta144.DEBIAN_SEQUENCE,
                "status_after_present_rc": 0,
                "fresh_debian_intent_consumed": True,
            },
            "final_health": {
                "v3401_resident": True,
                "selftest_fail_zero": True,
                "transport_serial_ready": True,
                "transport_tcpctl_ready": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        proof["checks"] = runner.wsta144.validate_proof(proof)
        return proof

    def hud_presenter_restart_proof(self) -> dict:
        proof = {
            "decision": runner.wsta147.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta147-dpublic-hud-restart-test",
            "source_run_dir": "workspace/private/runs/server-distro/wsta147-source-live-test",
            "candidate": {
                "init_version": runner.wsta147.INIT_VERSION,
                "init_build": runner.wsta147.INIT_BUILD,
                "boot_image": runner.wsta147.BOOT_IMAGE,
                "boot_sha256": runner.wsta147.BOOT_SHA256,
            },
            "checked_flash": {
                "used_checked_helper": True,
                "from_native": True,
                "local_sha_match": True,
                "remote_sha_match": True,
                "boot_readback_sha_match": True,
                "booted_v3402": True,
                "boot_ok": True,
                "selftest_fail_zero": True,
                "verify_native_passed": True,
            },
            "pre_restart": {
                "start_pid": 661,
                "start_done": True,
                "shared_run_mounted": True,
                "restart_policy_marker": True,
                "intent_sequence": runner.wsta147.PRE_RESTART_SEQUENCE,
                "presented": True,
                "status_running": True,
                "status_pid": 661,
                "status_drm_fd": True,
                "status_restart_policy": True,
                "status_file_sequence": runner.wsta147.PRE_RESTART_SEQUENCE,
                "status_file_present_rc": 0,
            },
            "restart": {
                "policy": runner.wsta147.RESTART_POLICY,
                "stop_pid": 661,
                "stop_released_drm": True,
                "stop_term": True,
                "stop_done": True,
                "stop_rc": 0,
                "start_pid": 669,
                "start_done": True,
                "start_rc": 0,
                "done": True,
            },
            "post_restart": {
                "intent_sequence": runner.wsta147.POST_RESTART_SEQUENCE,
                "presented": True,
                "status_running": True,
                "status_pid": 669,
                "status_drm_fd": True,
                "status_file_sequence": runner.wsta147.POST_RESTART_SEQUENCE,
                "status_file_present_rc": 0,
            },
            "stop_after_restart": {
                "stop_pid": 669,
                "stop_done": True,
            },
            "stale_pid_cleanup": {
                "fake_pid": runner.wsta147.FAKE_STALE_PID,
                "stale_cleanup_marker": True,
                "start_pid": 680,
                "start_done": True,
                "final_stop_done": True,
                "final_status_stopped": True,
            },
            "final_health": {
                "v3402_resident": True,
                "boot_ok": True,
                "selftest_fail_zero": True,
                "transport_serial_ready": True,
                "transport_ncm_ready": True,
                "transport_tcpctl_ready": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        proof["checks"] = runner.wsta147.validate_proof(proof)
        return proof

    def hud_intent_syscall_proof(self) -> dict:
        return {
            "decision": runner.wsta149.PASS_DECISION,
            "source_run_dir": "workspace/private/runs/server-distro/wsta149-dpublic-hud-intent-syscall-test",
            "service": "dpublic-hud",
            "scope": "hud-intent-producer-only",
            "intent_path": "/run/a90-dpublic/hud-intent.json",
            "intent_sequence": 14901,
            "command_shape": (
                "a90-service-launch dpublic-hud strace -f "
                "a90-dpublic-hud-intent --output /run/a90-dpublic/hud-intent.json"
            ),
            "uid": 3904,
            "gid": 3904,
            "no_new_privs": True,
            "cap_eff_zero": True,
            "public_default_off": True,
            "native_presenter_owner": True,
            "atomic_rename_observed": True,
            "network_syscalls_absent": True,
            "ioctl_syscall_absent": True,
            "drm_trace_absent": True,
            "core_syscalls_observed": True,
            "core_syscalls": ["execve", "openat", "write", "fsync", "close"],
            "syscall_count": 22,
            "syscall_names": [
                "brk",
                "close",
                "execve",
                "fsync",
                "mmap",
                "openat",
                "renameat",
                "write",
            ],
            "trace_artifacts_saved": True,
            "raw_trace_sha256": "raw-sha",
            "syscall_list_sha256": "syscalls-sha",
            "intent_json_sha256": "intent-sha",
            "checks": {
                "source_decision_pass": True,
                "source_no_mutating_device_action": True,
                "strace_image_sha_match": True,
                "identity_and_launcher_proven": True,
                "intent_write_proven": True,
                "atomic_path_proven": True,
                "no_network_syscalls": True,
                "no_drm_or_ioctl": True,
                "trace_artifacts_saved": True,
                "final_health_clean": True,
                "redaction_clean": True,
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

    def test_valid_wsta88_manifest_and_wsta120_admin_proof_updates_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            proof_path = root / "inputs" / "wsta120_result.json"
            manifest = self.hardening_manifest()
            manifest["manifest"]["blocking_before_enforcement"].insert(0, "non-root users/groups not staged")
            self.write_json(manifest_path, manifest)
            self.write_json(proof_path, self.dropbear_admin_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta120-dropbear-admin-proof-json",
                str(proof_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["dropbear_admin_proof"]
        self.assertEqual(proof["state"], "DROPBEAR_ADMIN_LIVE_PROVEN")
        self.assertTrue(proof["dropbear_admin_live_proven"])
        self.assertEqual(proof["service"], "dropbear-admin-usb")
        self.assertEqual(proof["daemon_privilege_model"], "root-boundary-auth-daemon")
        self.assertEqual(proof["user"], "a90admin")
        self.assertEqual(proof["uid"], 3903)
        self.assertTrue(proof["root_authorized_keys_absent"])
        self.assertTrue(proof["root_ssh_rejected"])
        self.assertTrue(proof["password_login_disabled"])
        self.assertTrue(proof["root_login_disabled"])
        self.assertTrue(proof["forwarding_disabled"])
        self.assertTrue(proof["admin_key_cleanup_ok"])
        self.assertTrue(proof["final_dropbear_absent"])
        self.assertNotIn("dropbear admin user model not finalized", hardening["blocking_before_enforcement"])
        self.assertIn("non-root users/groups not staged", hardening["blocking_before_enforcement"])
        self.assertTrue(result["checks"]["dropbear_admin_proof_supplied"])
        self.assertTrue(result["checks"]["dropbear_admin_live_proven"])
        self.assertIn("Dropbear admin proof: `true`", markdown)
        self.assertIn("Dropbear admin user: `a90admin`", markdown)
        self.assertIn("Dropbear root SSH rejected: `true`", markdown)

    def test_valid_wsta88_manifest_launcher_and_wsta122_model_updates_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            manifest = self.hardening_manifest()
            manifest["manifest"]["blocking_before_enforcement"].append("cloudflared service model not finalized")
            self.write_json(manifest_path, manifest)
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(model_path, self.cloudflared_model_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta122-cloudflared-model-json",
                str(model_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        model = hardening["cloudflared_model"]
        self.assertEqual(model["state"], "CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED")
        self.assertTrue(model["model_defined"])
        self.assertFalse(model["cloudflared_live_proven"])
        self.assertEqual(model["service"], "cloudflared-quick-tunnel")
        self.assertEqual(model["user"], "a90tunnel")
        self.assertEqual(model["uid"], 3902)
        self.assertTrue(model["default_public_off"])
        self.assertTrue(model["explicit_enable_required"])
        self.assertTrue(model["operator_gate_required"])
        self.assertTrue(model["origin_loopback_only"])
        self.assertTrue(model["metrics_loopback_ephemeral"])
        self.assertTrue(model["outbound_only"])
        self.assertTrue(model["launcher_required"])
        self.assertEqual(model["launcher_user"], "a90tunnel")
        self.assertTrue(model["launcher_no_new_privs_required"])
        self.assertTrue(model["launcher_caps_zero_required"])
        self.assertTrue(model["direct_root_start_rejected_for_always_on"])
        self.assertTrue(model["url_file_private"])
        self.assertTrue(model["no_named_tunnel_secret_required"])
        self.assertNotIn("cloudflared service model not finalized", hardening["blocking_before_enforcement"])
        self.assertIn("cloudflared-quick-tunnel", hardening["launcher_proof"]["remaining_profiles"])
        self.assertTrue(result["checks"]["cloudflared_model_supplied"])
        self.assertTrue(result["checks"]["cloudflared_model_defined"])
        self.assertTrue(result["checks"]["cloudflared_default_public_off"])
        self.assertTrue(result["checks"]["cloudflared_launcher_hardening_required"])
        self.assertFalse(result["checks"]["cloudflared_live_proven"])
        self.assertIn("prove-cloudflared-runtime-through-launcher-before-public-profile",
                      result["server_status"]["operator_next_actions"])
        self.assertIn("Cloudflared model: `true`", markdown)
        self.assertIn("Cloudflared model user: `a90tunnel`", markdown)
        self.assertIn("Cloudflared default public off: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta125_cloudflared_runtime_proof_retires_runtime_gap(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            manifest = self.hardening_manifest()
            manifest["manifest"]["blocking_before_enforcement"].append("cloudflared service model not finalized")
            self.write_json(manifest_path, manifest)
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(model_path, self.cloudflared_model_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta122-cloudflared-model-json",
                str(model_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        runtime = hardening["cloudflared_runtime"]
        model = hardening["cloudflared_model"]
        self.assertEqual(runtime["state"], "CLOUDFLARED_RUNTIME_LIVE_PROVEN")
        self.assertTrue(runtime["cloudflared_live_proven"])
        self.assertEqual(runtime["service"], "cloudflared-quick-tunnel")
        self.assertEqual(runtime["user"], "a90tunnel")
        self.assertEqual(runtime["uid"], 3902)
        self.assertTrue(runtime["native_upstream_confirmed"])
        self.assertTrue(runtime["default_route_wlan0"])
        self.assertTrue(runtime["resolver_ready"])
        self.assertTrue(runtime["egress_route_ready"])
        self.assertTrue(runtime["packet_filter_apply_pass"])
        self.assertTrue(runtime["packet_filter_restore_pass"])
        self.assertTrue(runtime["uid_gid_proven"])
        self.assertTrue(runtime["no_new_privs"])
        self.assertTrue(runtime["cap_eff_zero"])
        self.assertTrue(runtime["command_shape_proven"])
        self.assertTrue(runtime["outbound_only"])
        self.assertTrue(runtime["outbound_observed"])
        self.assertTrue(runtime["private_url_artifact"])
        self.assertTrue(runtime["private_url_redacted"])
        self.assertTrue(runtime["trace_artifacts_saved"])
        self.assertTrue(runtime["core_syscalls_observed"])
        self.assertEqual(runtime["syscall_count"], 52)
        self.assertIn("connect", runtime["syscall_names"])
        self.assertTrue(runtime["runtime_cleanup_ok"])
        self.assertTrue(runtime["final_selftest_fail_zero"])
        self.assertTrue(model["cloudflared_live_proven"])
        self.assertEqual(model["remaining_live_proofs"], [])
        self.assertNotIn("cloudflared-quick-tunnel", hardening["launcher_proof"]["remaining_profiles"])
        self.assertNotIn("cloudflared-quick-tunnel", hardening["syscall_trace_proof"]["remaining_profiles"])
        self.assertNotIn("cloudflared service model not finalized", hardening["blocking_before_enforcement"])
        self.assertIn(
            "remaining service launchers not live-proven beyond dpublic-smoke-httpd/cloudflared-quick-tunnel",
            hardening["blocking_before_enforcement"],
        )
        self.assertIn(
            "remaining syscall traces not captured beyond dpublic-smoke-httpd/cloudflared-quick-tunnel",
            hardening["blocking_before_enforcement"],
        )
        self.assertTrue(result["checks"]["cloudflared_runtime_proof_supplied"])
        self.assertTrue(result["checks"]["cloudflared_runtime_live_proven"])
        self.assertTrue(result["checks"]["cloudflared_runtime_private_url_redacted"])
        self.assertTrue(result["checks"]["cloudflared_runtime_trace_artifacts_saved"])
        self.assertTrue(result["checks"]["cloudflared_runtime_cleanup_ok"])
        self.assertTrue(result["checks"]["cloudflared_live_proven"])
        self.assertNotIn(
            "prove-cloudflared-runtime-through-launcher-before-public-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Cloudflared runtime proof: `true`", markdown)
        self.assertIn("Cloudflared runtime user: `a90tunnel`", markdown)
        self.assertIn("Cloudflared runtime private URL artifact: `true`", markdown)
        self.assertIn("Cloudflared runtime syscall count: `52`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta127_hud_model_adds_hud_status_without_live_claim(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(hud_path, self.hud_model_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta127-hud-model-json",
                str(hud_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        hud = hardening["hud_model"]
        self.assertEqual(hud["state"], "DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED")
        self.assertTrue(hud["model_defined"])
        self.assertFalse(hud["hud_live_proven"])
        self.assertEqual(hud["service"], "dpublic-hud")
        self.assertEqual(hud["user"], "a90hud")
        self.assertEqual(hud["uid"], 3904)
        self.assertTrue(hud["default_public_off"])
        self.assertTrue(hud["operator_gate_required"])
        self.assertTrue(hud["no_network_listener"])
        self.assertTrue(hud["packet_filter_not_required"])
        self.assertEqual(hud["drm_node"], "/dev/dri/card0")
        self.assertTrue(hud["drm_node_policy_defined"])
        self.assertTrue(hud["drm_master_required"])
        self.assertEqual(hud["kms_surface"], "dumb-framebuffer-xbgr8888")
        self.assertTrue(hud["launcher_required"])
        self.assertTrue(hud["launcher_no_new_privs_required"])
        self.assertTrue(hud["launcher_caps_zero_required"])
        self.assertTrue(hud["direct_root_start_rejected_for_always_on"])
        self.assertTrue(result["checks"]["hud_model_supplied"])
        self.assertTrue(result["checks"]["hud_model_defined"])
        self.assertTrue(result["checks"]["hud_no_network_listener"])
        self.assertTrue(result["checks"]["hud_drm_node_policy_defined"])
        self.assertTrue(result["checks"]["hud_launcher_hardening_required"])
        self.assertFalse(result["checks"]["hud_live_proven"])
        self.assertIn(
            "replace-direct-kms-hud-with-presenter-model-before-live-hud-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("dpublic-hud", hardening["launcher_proof"]["remaining_profiles"])
        self.assertIn("dpublic-hud", hardening["syscall_trace_proof"]["remaining_profiles"])
        self.assertIn("D-public HUD model: `true`", markdown)
        self.assertIn("D-public HUD user: `a90hud`", markdown)
        self.assertIn("D-public HUD no-network: `true`", markdown)
        self.assertIn("D-public HUD DRM node policy: `true`", markdown)
        self.assertIn("D-public HUD live proof: `false`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta130_hud_presenter_model_supersedes_direct_kms_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(hud_path, self.hud_model_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta127-hud-model-json",
                str(hud_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        hud = hardening["hud_model"]
        presenter = hardening["hud_presenter_model"]
        self.assertTrue(hud["superseded_by_presenter_model"])
        self.assertEqual(hud["superseded_reason"], "wsta129-setcrtc-permission-denied")
        self.assertEqual(presenter["state"], "DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED")
        self.assertTrue(presenter["model_defined"])
        self.assertTrue(presenter["supersedes_wsta127_direct_kms"])
        self.assertEqual(presenter["wsta129_boundary"], "setcrtc-permission-denied")
        self.assertEqual(presenter["display_architecture"], "split-intent-native-presenter")
        self.assertEqual(presenter["producer_user"], "a90hud")
        self.assertTrue(presenter["producer_no_drm_or_kms"])
        self.assertTrue(presenter["producer_no_network"])
        self.assertEqual(presenter["presenter_owner"], "native-init")
        self.assertTrue(presenter["presenter_kms_master_owner"])
        self.assertEqual(presenter["intent_file"], "/run/a90-dpublic/hud-intent.json")
        self.assertTrue(presenter["intent_parser_fail_closed"])
        self.assertTrue(result["checks"]["hud_presenter_model_supplied"])
        self.assertTrue(result["checks"]["hud_presenter_model_defined"])
        self.assertTrue(result["checks"]["hud_direct_nonroot_kms_rejected"])
        self.assertTrue(result["checks"]["hud_intent_producer_no_drm"])
        self.assertTrue(result["checks"]["hud_intent_producer_no_network"])
        self.assertTrue(result["checks"]["hud_native_presenter_owner"])
        self.assertTrue(result["checks"]["hud_intent_schema_fail_closed"])
        self.assertIn(
            "prototype-dpublic-hud-intent-presenter-boundary-before-live-hud-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "prove-dpublic-hud-runtime-drm-boundary-before-always-on-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("D-public HUD direct KMS superseded: `true`", markdown)
        self.assertIn("D-public HUD presenter model: `true`", markdown)
        self.assertIn("D-public HUD display architecture: `split-intent-native-presenter`", markdown)
        self.assertIn("D-public HUD intent producer no DRM: `true`", markdown)
        self.assertIn("D-public HUD presenter owner: `native-init`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta137_hud_presenter_live_proof_updates_operator_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(hud_path, self.hud_model_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(live_path, self.hud_presenter_live_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta127-hud-model-json",
                str(hud_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        presenter = result["server_status"]["hardening"]["hud_presenter_model"]
        live = presenter["live_proof"]
        self.assertEqual(presenter["state"], "DPUBLIC_HUD_NATIVE_PRESENTER_LIVE_PROVEN")
        self.assertTrue(presenter["model_defined"])
        self.assertTrue(presenter["hud_live_proven"])
        self.assertTrue(presenter["native_presenter_live_proven"])
        self.assertTrue(live["native_presenter_live_proven"])
        self.assertTrue(live["checked_flash_used"])
        self.assertTrue(live["checked_flash_sha_matched"])
        self.assertTrue(live["checked_flash_boot_health_clean"])
        self.assertEqual(live["validate_intent_sequence"], 13701)
        self.assertEqual(live["present_sequence"], 13702)
        self.assertEqual(live["present_framebuffer"], "1080x2400")
        self.assertEqual(live["present_crtc"], 133)
        self.assertTrue(live["reject_forbidden_command"])
        self.assertTrue(live["reject_stale_intent"])
        self.assertTrue(result["checks"]["hud_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_live_proof_supplied"])
        self.assertTrue(result["checks"]["hud_native_presenter_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_checked_flash_proven"])
        self.assertTrue(result["checks"]["hud_presenter_validate_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_present_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_reject_paths_live_proven"])
        self.assertIn(
            "design-durable-dpublic-hud-presenter-service-across-debian-handoff",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "prototype-dpublic-hud-intent-presenter-boundary-before-live-hud-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("D-public HUD live proof: `true`", markdown)
        self.assertIn("D-public HUD native presenter live proof: `true`", markdown)
        self.assertIn("D-public HUD presenter checked flash: `true`", markdown)
        self.assertIn("D-public HUD presenter KMS present: `true`", markdown)
        self.assertIn("D-public HUD presenter reject paths: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta144_hud_presenter_handoff_proof_updates_operator_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(hud_path, self.hud_model_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(live_path, self.hud_presenter_live_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta127-hud-model-json",
                str(hud_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        presenter = result["server_status"]["hardening"]["hud_presenter_model"]
        handoff = presenter["handoff_proof"]
        self.assertEqual(presenter["state"], "DPUBLIC_HUD_DURABLE_PRESENTER_HANDOFF_LIVE_PROVEN")
        self.assertTrue(presenter["handoff_live_proven"])
        self.assertTrue(presenter["hud_live_proven"])
        self.assertTrue(presenter["native_presenter_live_proven"])
        self.assertTrue(handoff["handoff_live_proven"])
        self.assertTrue(handoff["checked_flash_sha_matched"])
        self.assertTrue(handoff["checked_flash_boot_health_clean"])
        self.assertTrue(handoff["native_shared_run_mounted"])
        self.assertTrue(handoff["handoff_shared_run_bind_ok"])
        self.assertTrue(handoff["shared_run_same_mount_after_handoff"])
        self.assertTrue(handoff["presenter_sole_drm_owner_after_handoff"])
        self.assertTrue(handoff["a90hud_writer_no_drm_fd"])
        self.assertEqual(handoff["debian_intent_sequence"], runner.wsta144.DEBIAN_SEQUENCE)
        self.assertTrue(handoff["fresh_debian_intent_consumed"])
        self.assertTrue(result["checks"]["hud_presenter_handoff_proof_supplied"])
        self.assertTrue(result["checks"]["hud_presenter_handoff_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_handoff_shared_run_bind_proven"])
        self.assertTrue(result["checks"]["hud_presenter_handoff_fresh_debian_intent_consumed"])
        self.assertTrue(result["checks"]["hud_presenter_handoff_sole_drm_owner"])
        self.assertIn(
            "continue-dpublic-service-integration-or-containment-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "design-durable-dpublic-hud-presenter-service-across-debian-handoff",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("D-public HUD handoff proof: `true`", markdown)
        self.assertIn("D-public HUD shared run bind: `true`", markdown)
        self.assertIn("D-public HUD Debian intent consumed: `true`", markdown)
        self.assertIn("D-public HUD handoff sole DRM owner: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta147_hud_restart_proof_updates_operator_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(hud_path, self.hud_model_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(live_path, self.hud_presenter_live_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta127-hud-model-json",
                str(hud_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        presenter = result["server_status"]["hardening"]["hud_presenter_model"]
        restart = presenter["restart_proof"]
        self.assertEqual(presenter["state"], "DPUBLIC_HUD_DURABLE_PRESENTER_RESTART_LIVE_PROVEN")
        self.assertTrue(presenter["handoff_live_proven"])
        self.assertTrue(presenter["restart_live_proven"])
        self.assertTrue(presenter["durable_restart_live_proven"])
        self.assertEqual(restart["restart_policy"], runner.wsta147.RESTART_POLICY)
        self.assertEqual(restart["restart_stop_rc"], 0)
        self.assertEqual(restart["restart_start_rc"], 0)
        self.assertTrue(restart["restart_done"])
        self.assertEqual(restart["post_restart_sequence"], runner.wsta147.POST_RESTART_SEQUENCE)
        self.assertEqual(restart["post_restart_present_rc"], 0)
        self.assertTrue(restart["post_restart_drm_fd"])
        self.assertTrue(restart["stale_pid_cleanup_marker"])
        self.assertEqual(restart["stale_pid_cleanup_fake_pid"], runner.wsta147.FAKE_STALE_PID)
        self.assertTrue(result["checks"]["hud_presenter_restart_proof_supplied"])
        self.assertTrue(result["checks"]["hud_presenter_restart_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_durable_restart_live_proven"])
        self.assertTrue(result["checks"]["hud_presenter_restart_stop_start_proven"])
        self.assertTrue(result["checks"]["hud_presenter_restart_post_present_proven"])
        self.assertTrue(result["checks"]["hud_presenter_stale_pid_cleanup_proven"])
        self.assertIn(
            "profile-dpublic-hud-syscalls-or-continue-containment-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "continue-dpublic-service-integration-or-containment-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("D-public HUD restart proof: `true`", markdown)
        self.assertIn("D-public HUD restart stop/start: `true`", markdown)
        self.assertIn("D-public HUD restart post-present: `true`", markdown)
        self.assertIn("D-public HUD stale pid cleanup: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta149_hud_intent_syscall_proof_retires_hud_syscall_gap(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(hud_path, self.hud_model_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(live_path, self.hud_presenter_live_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta127-hud-model-json",
                str(hud_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        presenter = hardening["hud_presenter_model"]
        proof = presenter["intent_syscall_trace_proof"]
        self.assertEqual(presenter["state"], "DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN")
        self.assertTrue(presenter["durable_restart_live_proven"])
        self.assertTrue(presenter["intent_syscall_trace_live_proven"])
        self.assertTrue(proof["hud_intent_syscall_trace_live_proven"])
        self.assertTrue(proof["no_new_privs"])
        self.assertTrue(proof["cap_eff_zero"])
        self.assertTrue(proof["atomic_rename_observed"])
        self.assertTrue(proof["network_syscalls_absent"])
        self.assertTrue(proof["ioctl_syscall_absent"])
        self.assertTrue(proof["drm_trace_absent"])
        self.assertTrue(result["checks"]["hud_intent_syscall_proof_supplied"])
        self.assertTrue(result["checks"]["hud_intent_syscall_trace_live_proven"])
        self.assertTrue(result["checks"]["hud_intent_syscall_no_network"])
        self.assertTrue(result["checks"]["hud_intent_syscall_no_drm"])
        self.assertTrue(result["checks"]["hud_intent_syscall_atomic_write"])
        self.assertNotIn("dpublic-hud", hardening["syscall_trace_proof"]["remaining_profiles"])
        self.assertNotIn(
            "profile-dpublic-hud-syscalls-or-continue-containment-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "continue-containment-hardening-or-derive-hud-seccomp-policy",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("D-public HUD intent syscall proof: `true`", markdown)
        self.assertIn("D-public HUD intent syscall count: `22`", markdown)
        self.assertIn("D-public HUD intent syscall no-network: `true`", markdown)
        self.assertIn("D-public HUD intent syscall no-DRM: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta151_dropbear_admin_syscall_proof_retires_dropbear_syscall_gap(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            dropbear_syscall_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(dropbear_syscall_path, self.dropbear_admin_syscall_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(dropbear_syscall_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["dropbear_admin_syscall_trace_proof"]
        self.assertEqual(proof["state"], "DROPBEAR_ADMIN_SYSCALL_TRACE_LIVE_PROVEN")
        self.assertTrue(proof["dropbear_admin_syscall_trace_live_proven"])
        self.assertEqual(proof["service"], "dropbear-admin-usb")
        self.assertEqual(proof["uid"], 3903)
        self.assertEqual(proof["gid"], 3903)
        self.assertTrue(proof["root_ssh_rejected"])
        self.assertTrue(proof["password_login_disabled"])
        self.assertTrue(proof["core_syscalls_observed"])
        self.assertTrue(proof["accept_observed"])
        self.assertTrue(proof["trace_artifacts_saved"])
        self.assertTrue(result["checks"]["dropbear_admin_syscall_proof_supplied"])
        self.assertTrue(result["checks"]["dropbear_admin_syscall_trace_live_proven"])
        self.assertTrue(result["checks"]["dropbear_admin_syscall_accept_observed"])
        self.assertTrue(result["checks"]["dropbear_admin_syscall_trace_artifacts_saved"])
        self.assertNotIn("dropbear-admin-usb", hardening["syscall_trace_proof"]["remaining_profiles"])
        self.assertIn(
            "remaining syscall traces not captured beyond dpublic-smoke-httpd/dropbear-admin-usb",
            hardening["blocking_before_enforcement"],
        )
        self.assertIn("Dropbear admin syscall proof: `true`", markdown)
        self.assertIn("Dropbear admin syscall count: `8`", markdown)
        self.assertIn("Dropbear admin syscall accept observed: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_valid_wsta208_wsta209_seccomp_proofs_retire_seccomp_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            smoke_path = root / "inputs" / "wsta208_result.json"
            dropbear_path = root / "inputs" / "wsta209_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(smoke_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_path, self.seccomp_dropbear_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["seccomp_enforcement_proof"]
        self.assertEqual(proof["state"], "REAL_SERVICE_SECCOMP_SMOKE_AND_DROPBEAR_LIVE_PROVEN")
        self.assertTrue(proof["seccomp_real_services_live_proven"])
        self.assertTrue(proof["all_supplied_seccomp_proofs_live_proven"])
        self.assertEqual(proof["proven_services"], ["dpublic-smoke-httpd", "dropbear-admin-usb"])
        self.assertTrue(proof["smoke_service"]["seccomp_live_proven"])
        self.assertTrue(proof["dropbear_admin_service"]["seccomp_live_proven"])
        self.assertTrue(proof["dropbear_admin_service"]["root_login_negative_test"])
        self.assertTrue(result["checks"]["wsta208_seccomp_smoke_proof_supplied"])
        self.assertTrue(result["checks"]["wsta209_seccomp_dropbear_proof_supplied"])
        self.assertTrue(result["checks"]["seccomp_smoke_service_live_proven"])
        self.assertTrue(result["checks"]["seccomp_dropbear_admin_live_proven"])
        self.assertTrue(result["checks"]["seccomp_real_services_live_proven"])
        self.assertIn(
            "move-to-capability-drop-nftables-or-apparmor-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn("derive-seccomp-policy-from-live-syscall-baselines", result["server_status"]["operator_next_actions"])
        self.assertIn("Seccomp real-service proof: `true`", markdown)
        self.assertIn("Seccomp proven services: `dpublic-smoke-httpd, dropbear-admin-usb`", markdown)
        self.assertIn("Seccomp smoke service proof: `true`", markdown)
        self.assertIn("Seccomp Dropbear admin proof: `true`", markdown)
        self.assertNotIn("http://", summary_text)
        self.assertNotIn("https://", summary_text)
        self.assertNotIn("http://", markdown)
        self.assertNotIn("https://", markdown)

    def test_wsta211_capability_drop_status_retires_nonroot_launcher_gap(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        proof = hardening["capability_drop_proof"]
        self.assertEqual(proof["state"], "NONROOT_SERVICE_CAPABILITY_DROP_LIVE_PROVEN")
        self.assertTrue(proof["nonroot_services_capability_drop_live_proven"])
        self.assertEqual(
            proof["proven_services"],
            ["dpublic-smoke-httpd", "cloudflared-quick-tunnel", "dpublic-hud"],
        )
        self.assertEqual(proof["remaining_nonroot_services"], [])
        self.assertEqual(hardening["launcher_proof"]["remaining_profiles"], ["wsta-native-uplink-helper"])
        self.assertTrue(result["checks"]["capability_drop_nonroot_services_live_proven"])
        self.assertTrue(result["checks"]["capability_drop_smoke_service_live_proven"])
        self.assertTrue(result["checks"]["capability_drop_cloudflared_live_proven"])
        self.assertTrue(result["checks"]["capability_drop_hud_live_proven"])
        self.assertIn(
            "remaining service users/groups not live-proven beyond dpublic-smoke-httpd/dropbear-admin-usb/cloudflared-quick-tunnel/dpublic-hud",
            hardening["blocking_before_enforcement"],
        )
        self.assertNotIn(
            "extend-service-launcher-proof-beyond-dpublic-smoke-httpd-before-always-on-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "move-to-capability-drop-nftables-or-apparmor-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-nftables-default-drop-or-apparmor-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Capability-drop non-root services proof: `true`", markdown)
        self.assertIn(
            "Capability-drop proven services: `dpublic-smoke-httpd, cloudflared-quick-tunnel, dpublic-hud`",
            markdown,
        )
        self.assertIn("Capability-drop remaining non-root services: ``", markdown)

    def test_wsta213_native_uplink_boundary_status_retires_root_boundary_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["native_uplink_boundary_policy"]
        self.assertEqual(proof["state"], runner.NATIVE_UPLINK_BOUNDARY_POLICY_STATE)
        self.assertTrue(proof["native_uplink_boundary_policy_defined"])
        self.assertEqual(proof["allowed_debian_ops"], ["status", "scan"])
        self.assertIn("connect", proof["denied_debian_ops"])
        self.assertFalse(proof["debian_service_launcher_allowed"])
        self.assertFalse(proof["debian_service_seccomp_target"])
        hardening = result["server_status"]["hardening"]
        self.assertEqual(hardening["launcher_proof"]["remaining_profiles"], [])
        self.assertNotIn(
            "remaining service users/groups not live-proven beyond dpublic-smoke-httpd/dropbear-admin-usb/cloudflared-quick-tunnel/dpublic-hud",
            hardening["blocking_before_enforcement"],
        )
        self.assertNotIn(
            "remaining service launchers not live-proven beyond dpublic-smoke-httpd/cloudflared-quick-tunnel/dpublic-hud",
            hardening["blocking_before_enforcement"],
        )
        self.assertTrue(result["checks"]["wsta212_native_uplink_boundary_policy_supplied"])
        self.assertTrue(result["checks"]["native_uplink_boundary_policy_defined"])
        self.assertTrue(result["checks"]["native_uplink_debian_status_scan_only"])
        self.assertTrue(result["checks"]["native_uplink_connectivity_stays_native_owned"])
        self.assertTrue(result["checks"]["native_uplink_not_debian_launcher_or_seccomp_target"])
        self.assertNotIn(
            "continue-root-boundary-policy-for-wsta-native-uplink-helper",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-nftables-default-drop-or-apparmor-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Native uplink boundary policy: `true`", markdown)
        self.assertIn("Native uplink allowed Debian ops: `status, scan`", markdown)
        self.assertIn("Native uplink Debian launcher target: `false`", markdown)

    def test_wsta215_apparmor_feasibility_parks_apparmor_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            apparmor_path = root / "inputs" / "wsta214_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(apparmor_path, self.apparmor_feasibility())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta214-apparmor-feasibility-json",
                str(apparmor_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["apparmor_feasibility"]
        self.assertEqual(proof["state"], runner.APPARMOR_UNAVAILABLE_STATE)
        self.assertTrue(proof["apparmor_unavailable_under_current_evidence"])
        self.assertFalse(proof["apparmor_immediate_lever_available"])
        self.assertEqual(proof["preferred_current_hardening_lever"], "legacy-iptables-loopback-default-drop")
        self.assertTrue(result["checks"]["wsta214_apparmor_feasibility_supplied"])
        self.assertTrue(result["checks"]["apparmor_unavailable_under_current_evidence"])
        self.assertTrue(result["checks"]["apparmor_immediate_lever_parked"])
        self.assertTrue(result["checks"]["apparmor_profile_load_disabled"])
        self.assertTrue(result["checks"]["preferred_hardening_lever_legacy_iptables"])
        self.assertNotIn(
            "continue-containment-hardening-with-nftables-or-apparmor",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "move-to-nftables-default-drop-or-apparmor-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-legacy-iptables-default-drop-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("AppArmor feasibility: `APPARMOR_NOT_AVAILABLE_UNDER_CURRENT_EVIDENCE`", markdown)
        self.assertIn("Preferred current hardening lever: `legacy-iptables-loopback-default-drop`", markdown)

    def test_wsta217_default_drop_hardening_policy_moves_to_attended_live_use(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            apparmor_path = root / "inputs" / "wsta214_result.json"
            default_drop_path = root / "inputs" / "wsta216_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(apparmor_path, self.apparmor_feasibility())
            self.write_json(default_drop_path, self.default_drop_hardening_policy())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta214-apparmor-feasibility-json",
                str(apparmor_path),
                "--wsta216-default-drop-hardening-policy-json",
                str(default_drop_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["default_drop_hardening_policy"]
        self.assertEqual(proof["state"], runner.DEFAULT_DROP_HARDENING_POLICY_STATE)
        self.assertTrue(proof["default_drop_hardening_policy_defined"])
        self.assertEqual(proof["hardening_lever"], "legacy-iptables-loopback-default-drop")
        self.assertEqual(proof["activation"], "explicit-operator-gated")
        self.assertFalse(proof["live_execution_requested"])
        self.assertFalse(proof["packet_filter_mutation_by_wsta216"])
        self.assertTrue(proof["control_plane_preserved"])
        self.assertTrue(result["checks"]["wsta216_default_drop_hardening_policy_supplied"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_defined"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_default_off"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_explicit_gate"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_no_live_execution"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_no_mutation_here"])
        self.assertTrue(result["checks"]["default_drop_hardening_policy_control_plane_preserved"])
        self.assertNotIn(
            "continue-containment-hardening-with-legacy-iptables-default-drop",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "move-to-legacy-iptables-default-drop-hardening",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-attended-default-drop-live-use-or-next-hardening-layer",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Default-drop hardening policy: `true`", markdown)
        self.assertIn("Default-drop hardening state: `LEGACY_IPTABLES_DEFAULT_DROP_HARDENING_POLICY_DEFINED`", markdown)
        self.assertIn("Default-drop hardening mutates filters here: `false`", markdown)

    def test_wsta220_attended_default_drop_live_retires_attended_live_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            apparmor_path = root / "inputs" / "wsta214_result.json"
            default_drop_path = root / "inputs" / "wsta216_result.json"
            attended_live_path = root / "inputs" / "wsta219_operator_workflow.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(apparmor_path, self.apparmor_feasibility())
            self.write_json(default_drop_path, self.default_drop_hardening_policy())
            self.write_json(attended_live_path, self.attended_default_drop_live_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta214-apparmor-feasibility-json",
                str(apparmor_path),
                "--wsta216-default-drop-hardening-policy-json",
                str(default_drop_path),
                "--wsta219-attended-default-drop-live-json",
                str(attended_live_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["attended_default_drop_live"]
        self.assertEqual(proof["state"], runner.ATTENDED_DEFAULT_DROP_LIVE_STATE)
        self.assertTrue(proof["attended_default_drop_live_proven"])
        self.assertEqual(proof["packet_filter_backend"], "legacy-iptables")
        self.assertEqual(proof["packet_filter_policy"], "loopback-default-drop")
        self.assertTrue(proof["ack_packet_filter_mutation"])
        self.assertTrue(proof["force_packet_filter_restore_proof"])
        self.assertTrue(proof["initial_public_smoke_ok"])
        self.assertTrue(proof["renewal_public_smoke_ok"])
        self.assertTrue(proof["initial_ttl_public_off"])
        self.assertTrue(proof["renewal_ttl_public_off"])
        self.assertEqual(proof["public_state_after_manual_stop"], "PUBLIC_OFF")
        self.assertTrue(result["checks"]["wsta219_attended_default_drop_live_supplied"])
        self.assertTrue(result["checks"]["attended_default_drop_live_proven"])
        self.assertTrue(result["checks"]["attended_default_drop_live_default_off"])
        self.assertTrue(result["checks"]["attended_default_drop_live_explicit_execution"])
        self.assertTrue(result["checks"]["attended_default_drop_live_packet_filter_ready"])
        self.assertTrue(result["checks"]["attended_default_drop_live_ack_packet_filter_mutation"])
        self.assertTrue(result["checks"]["attended_default_drop_live_force_restore_proof"])
        self.assertNotIn(
            "move-to-attended-default-drop-live-use-or-next-hardening-layer",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-next-hardening-layer-after-attended-default-drop-live",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Attended default-drop live: `true`", markdown)
        self.assertIn("Attended default-drop state: `LEGACY_IPTABLES_DEFAULT_DROP_ATTENDED_LIVE_PROVEN`", markdown)

    def test_wsta221_cloudflared_egress_policy_concretizes_next_hardening_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            dropbear_syscall_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            apparmor_path = root / "inputs" / "wsta214_result.json"
            default_drop_path = root / "inputs" / "wsta216_result.json"
            attended_live_path = root / "inputs" / "wsta219_operator_workflow.json"
            egress_policy_path = root / "inputs" / "wsta221_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(model_path, self.cloudflared_model_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(dropbear_syscall_path, self.dropbear_admin_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(apparmor_path, self.apparmor_feasibility())
            self.write_json(default_drop_path, self.default_drop_hardening_policy())
            self.write_json(attended_live_path, self.attended_default_drop_live_proof())
            self.write_json(egress_policy_path, self.cloudflared_egress_allowlist_policy())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta122-cloudflared-model-json",
                str(model_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(dropbear_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta214-apparmor-feasibility-json",
                str(apparmor_path),
                "--wsta216-default-drop-hardening-policy-json",
                str(default_drop_path),
                "--wsta219-attended-default-drop-live-json",
                str(attended_live_path),
                "--wsta221-cloudflared-egress-allowlist-policy-json",
                str(egress_policy_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["cloudflared_egress_allowlist_policy"]
        self.assertEqual(proof["state"], runner.wsta221.POLICY_STATE)
        self.assertTrue(proof["cloudflared_egress_allowlist_policy_defined"])
        self.assertEqual(proof["hardening_lever"], runner.wsta221.HARDENING_LEVER)
        self.assertFalse(proof["live_execution_requested"])
        self.assertFalse(proof["packet_filter_mutation_by_wsta221"])
        self.assertTrue(result["checks"]["wsta221_cloudflared_egress_allowlist_policy_supplied"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_policy_defined"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_owner_match_fail_closed"])
        self.assertNotIn(
            "move-to-next-hardening-layer-after-attended-default-drop-live",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "move-to-cloudflared-egress-allowlist-live-gate",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn("Cloudflared egress allowlist policy: `true`", markdown)
        self.assertIn("Cloudflared egress allowlist state: `CLOUDFLARED_EGRESS_ALLOWLIST_HARDENING_POLICY_DEFINED`", markdown)

    def test_wsta230_cloudflared_egress_live_retires_egress_live_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            dropbear_syscall_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            apparmor_path = root / "inputs" / "wsta214_result.json"
            default_drop_path = root / "inputs" / "wsta216_result.json"
            attended_live_path = root / "inputs" / "wsta219_operator_workflow.json"
            egress_policy_path = root / "inputs" / "wsta221_result.json"
            egress_live_path = root / "inputs" / "wsta229_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(model_path, self.cloudflared_model_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(dropbear_syscall_path, self.dropbear_admin_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(apparmor_path, self.apparmor_feasibility())
            self.write_json(default_drop_path, self.default_drop_hardening_policy())
            self.write_json(attended_live_path, self.attended_default_drop_live_proof())
            self.write_json(egress_policy_path, self.cloudflared_egress_allowlist_policy())
            self.write_json(egress_live_path, self.cloudflared_egress_allowlist_live_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta122-cloudflared-model-json",
                str(model_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(dropbear_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta214-apparmor-feasibility-json",
                str(apparmor_path),
                "--wsta216-default-drop-hardening-policy-json",
                str(default_drop_path),
                "--wsta219-attended-default-drop-live-json",
                str(attended_live_path),
                "--wsta221-cloudflared-egress-allowlist-policy-json",
                str(egress_policy_path),
                "--wsta229-cloudflared-egress-allowlist-live-json",
                str(egress_live_path),
            ))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        proof = result["server_status"]["hardening"]["cloudflared_egress_allowlist_live"]
        self.assertEqual(proof["state"], runner.CLOUDFLARED_EGRESS_ALLOWLIST_LIVE_STATE)
        self.assertTrue(proof["cloudflared_egress_allowlist_live_proven"])
        self.assertEqual(proof["dns4_count"], 30)
        self.assertEqual(proof["tls4_count"], 2)
        self.assertTrue(proof["route_values_redacted"])
        self.assertTrue(proof["ack_packet_filter_mutation"])
        self.assertTrue(proof["force_packet_filter_restore_proof"])
        self.assertTrue(proof["force_cloudflared_egress_allowlist_proof"])
        self.assertTrue(proof["initial_public_smoke_ok"])
        self.assertTrue(proof["renewal_public_smoke_ok"])
        self.assertTrue(proof["manual_stop_cleanup_ok"])
        self.assertTrue(result["checks"]["wsta229_cloudflared_egress_allowlist_live_supplied"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_proven"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_default_off"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_route_values_redacted"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_ack_packet_filter_mutation"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_force_restore_proof"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_force_egress_proof"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_initial_public_smoke"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_renewal_public_smoke"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_initial_restore"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_renewal_restore"])
        self.assertTrue(result["checks"]["cloudflared_egress_allowlist_live_manual_stop_public_off"])
        self.assertNotIn(
            "prepare-attended-cloudflared-egress-allowlist-live-gate",
            result["server_status"]["operator_next_actions"],
        )
        self.assertNotIn(
            "move-to-cloudflared-egress-allowlist-live-gate",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "continue-dpublic-server-endgame-after-cloudflared-egress-live",
            result["server_status"]["operator_next_actions"],
        )
        self.assertEqual(
            result["server_status"]["operator_next_actions"].count(
                "continue-dpublic-server-endgame-after-cloudflared-egress-live"
            ),
            1,
        )
        self.assertIn("Cloudflared egress allowlist live: `true`", markdown)
        self.assertIn("Cloudflared egress allowlist live state: `CLOUDFLARED_EGRESS_ALLOWLIST_ATTENDED_LIVE_PROVEN`", markdown)
        self.assertIn("Cloudflared egress allowlist route counts: `30/2`", markdown)
        self.assertIn("Cloudflared egress allowlist live restore: `true`", markdown)

    def test_wsta231_server_endgame_status_prunes_retired_hardening_blockers(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            dropbear_syscall_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            smoke_seccomp_path = root / "inputs" / "wsta208_result.json"
            dropbear_seccomp_path = root / "inputs" / "wsta209_result.json"
            native_uplink_path = root / "inputs" / "wsta212_result.json"
            default_drop_path = root / "inputs" / "wsta216_result.json"
            attended_live_path = root / "inputs" / "wsta219_operator_workflow.json"
            egress_policy_path = root / "inputs" / "wsta221_result.json"
            egress_live_path = root / "inputs" / "wsta229_result.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            self.write_json(model_path, self.cloudflared_model_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(dropbear_syscall_path, self.dropbear_admin_syscall_proof())
            self.write_json(smoke_seccomp_path, self.seccomp_smoke_proof())
            self.write_json(dropbear_seccomp_path, self.seccomp_dropbear_proof())
            self.write_json(native_uplink_path, self.native_uplink_boundary_policy())
            self.write_json(default_drop_path, self.default_drop_hardening_policy())
            self.write_json(attended_live_path, self.attended_default_drop_live_proof())
            self.write_json(egress_policy_path, self.cloudflared_egress_allowlist_policy())
            self.write_json(egress_live_path, self.cloudflared_egress_allowlist_live_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
                "--wsta122-cloudflared-model-json",
                str(model_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(dropbear_syscall_path),
                "--wsta208-real-service-seccomp-proof-json",
                str(smoke_seccomp_path),
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(dropbear_seccomp_path),
                "--wsta212-native-uplink-boundary-policy-json",
                str(native_uplink_path),
                "--wsta216-default-drop-hardening-policy-json",
                str(default_drop_path),
                "--wsta219-attended-default-drop-live-json",
                str(attended_live_path),
                "--wsta221-cloudflared-egress-allowlist-policy-json",
                str(egress_policy_path),
                "--wsta229-cloudflared-egress-allowlist-live-json",
                str(egress_live_path),
            ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        self.assertEqual(hardening["launcher_proof"]["remaining_profiles"], [])
        self.assertEqual(hardening["syscall_trace_proof"]["remaining_profiles"], [])
        self.assertEqual(hardening["blocking_before_enforcement"], [])
        self.assertNotIn(
            "define-cloudflared-service-model-before-public-profile",
            result["server_status"]["operator_next_actions"],
        )
        self.assertIn(
            "continue-dpublic-server-endgame-after-cloudflared-egress-live",
            result["server_status"]["operator_next_actions"],
        )
        for stale in (
            "remaining service users/groups not live-proven beyond dpublic-smoke-httpd/dropbear-admin-usb/cloudflared-quick-tunnel/dpublic-hud",
            "remaining service launchers not live-proven beyond dpublic-smoke-httpd/cloudflared-quick-tunnel/dpublic-hud",
            "syscall traces not captured",
            "packet-filter backend not inventoried",
        ):
            self.assertNotIn(stale, hardening["blocking_before_enforcement"])

    def test_all_syscall_profiles_retired_removes_syscall_blocker(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            syscall_path = root / "inputs" / "wsta114_result.json"
            runtime_path = root / "inputs" / "wsta125_result.json"
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            hud_syscall_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            dropbear_syscall_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            self.write_json(manifest_path, self.hardening_manifest())
            self.write_json(syscall_path, self.syscall_trace_proof())
            self.write_json(runtime_path, self.cloudflared_runtime_proof())
            self.write_json(presenter_path, self.hud_presenter_model_proof())
            self.write_json(live_path, self.hud_presenter_live_proof())
            self.write_json(handoff_path, self.hud_presenter_handoff_proof())
            self.write_json(restart_path, self.hud_presenter_restart_proof())
            self.write_json(hud_syscall_path, self.hud_intent_syscall_proof())
            self.write_json(dropbear_syscall_path, self.dropbear_admin_syscall_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta114-syscall-trace-proof-json",
                str(syscall_path),
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
                "--wsta149-hud-intent-syscall-proof-json",
                str(hud_syscall_path),
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(dropbear_syscall_path),
            ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        self.assertEqual(hardening["syscall_trace_proof"]["remaining_profiles"], [])
        self.assertNotIn(
            "remaining syscall traces not captured beyond dpublic-smoke-httpd/dropbear-admin-usb/cloudflared-quick-tunnel",
            hardening["blocking_before_enforcement"],
        )
        self.assertIn(
            "derive-seccomp-policy-from-live-syscall-baselines",
            result["server_status"]["operator_next_actions"],
        )

    def test_wsta120_and_smoke_launcher_proofs_refine_shared_user_group_blocker(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            launcher_path = root / "inputs" / "wsta110_result.json"
            admin_path = root / "inputs" / "wsta120_result.json"
            manifest = self.hardening_manifest()
            self.write_json(manifest_path, manifest)
            self.write_json(launcher_path, self.launcher_proof())
            self.write_json(admin_path, self.dropbear_admin_proof())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta110-service-launcher-proof-json",
                str(launcher_path),
                "--wsta120-dropbear-admin-proof-json",
                str(admin_path),
            ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        self.assertNotIn("dropbear-admin-usb", hardening["launcher_proof"]["remaining_profiles"])
        self.assertIn(
            "remaining service users/groups not live-proven beyond dpublic-smoke-httpd/dropbear-admin-usb",
            hardening["blocking_before_enforcement"],
        )

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

    def test_nonpass_wsta120_dropbear_admin_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta120_result.json"
            proof = self.dropbear_admin_proof()
            proof["decision"] = "wsta120-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta120-dropbear-admin-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta120-dropbear-admin-proof-not-pass")

    def test_nonpass_wsta122_cloudflared_model_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            proof = self.cloudflared_model_proof()
            proof["decision"] = "wsta122-blocked"
            self.write_json(model_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta122-cloudflared-model-json",
                str(model_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta122-cloudflared-model-not-pass")

    def test_nonpass_wsta125_cloudflared_runtime_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            runtime_path = root / "inputs" / "wsta125_result.json"
            proof = self.cloudflared_runtime_proof()
            proof["decision"] = "wsta125-blocked"
            self.write_json(runtime_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta125-cloudflared-runtime-proof-not-pass")

    def test_nonpass_wsta127_hud_model_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            proof = self.hud_model_proof()
            proof["decision"] = "wsta127-blocked"
            self.write_json(hud_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta127-hud-model-json",
                str(hud_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta127-hud-model-not-pass")

    def test_nonpass_wsta130_hud_presenter_model_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            proof = self.hud_presenter_model_proof()
            proof["decision"] = "wsta130-blocked"
            self.write_json(presenter_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta130-hud-presenter-model-not-pass")

    def test_nonpass_wsta137_hud_presenter_live_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            proof = self.hud_presenter_live_proof()
            proof["decision"] = "wsta137-blocked"
            self.write_json(live_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta137-hud-presenter-live-proof-not-pass")

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

    def test_incomplete_wsta120_dropbear_admin_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta120_result.json"
            proof = self.dropbear_admin_proof()
            proof["admin_ssh_parse"]["uid_3903"] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta120-dropbear-admin-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta120-dropbear-admin-proof-incomplete")
        self.assertFalse(result["checks"]["dropbear_admin_live_proven"])

    def test_incomplete_wsta122_cloudflared_model_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            model_path = root / "inputs" / "wsta122_cloudflared_service_model.json"
            proof = self.cloudflared_model_proof()
            proof["checks"]["launcher_caps_zero_required"] = False
            self.write_json(model_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta122-cloudflared-model-json",
                str(model_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta122-cloudflared-model-incomplete")
        self.assertFalse(result["checks"]["cloudflared_model_defined"])

    def test_incomplete_wsta125_cloudflared_runtime_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            runtime_path = root / "inputs" / "wsta125_result.json"
            proof = self.cloudflared_runtime_proof()
            proof["private_url_artifact"]["stdout_redacted"] = False
            self.write_json(runtime_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta125-cloudflared-runtime-proof-json",
                str(runtime_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta125-cloudflared-runtime-proof-incomplete")
        self.assertFalse(result["checks"]["cloudflared_runtime_live_proven"])
        self.assertFalse(result["checks"]["cloudflared_runtime_private_url_redacted"])

    def test_incomplete_wsta127_hud_model_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            hud_path = root / "inputs" / "wsta127_dpublic_hud_service_model.json"
            proof = self.hud_model_proof()
            proof["hud_service_model"]["display"]["device_node_policy"] = "root-only"
            self.write_json(hud_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta127-hud-model-json",
                str(hud_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta127-hud-model-incomplete")
        self.assertFalse(result["checks"]["hud_model_defined"])
        self.assertFalse(result["checks"]["hud_drm_node_policy_defined"])

    def test_incomplete_wsta130_hud_presenter_model_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            presenter_path = root / "inputs" / "wsta130_dpublic_hud_presenter_model.json"
            proof = self.hud_presenter_model_proof()
            proof["presenter_architecture_model"]["boundary"]["parser_policy"]["reject_unknown_fields"] = False
            self.write_json(presenter_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta130-hud-presenter-model-json",
                str(presenter_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta130-hud-presenter-model-incomplete")
        self.assertFalse(result["checks"]["hud_presenter_model_defined"])
        self.assertFalse(result["checks"]["hud_intent_schema_fail_closed"])

    def test_incomplete_wsta137_hud_presenter_live_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            live_path = root / "inputs" / "wsta137_dpublic_native_presenter_live.json"
            proof = self.hud_presenter_live_proof()
            proof["present_proof"]["present_done"] = False
            proof["checks"] = runner.wsta137.validate_proof(proof)
            self.write_json(live_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta137-hud-presenter-live-proof-json",
                str(live_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta137-hud-presenter-live-proof-incomplete")
        self.assertFalse(result["checks"]["hud_native_presenter_live_proven"])
        self.assertFalse(result["checks"]["hud_presenter_present_live_proven"])

    def test_incomplete_wsta144_hud_presenter_handoff_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            handoff_path = root / "inputs" / "wsta144_dpublic_hud_shared_run_bind_live.json"
            proof = self.hud_presenter_handoff_proof()
            proof["presenter_consumption"]["fresh_debian_intent_consumed"] = False
            proof["checks"] = runner.wsta144.validate_proof(proof)
            self.write_json(handoff_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta144-hud-presenter-handoff-proof-json",
                str(handoff_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta144-hud-presenter-handoff-proof-incomplete")
        self.assertFalse(result["checks"]["hud_presenter_handoff_live_proven"])
        self.assertFalse(result["checks"]["hud_presenter_handoff_fresh_debian_intent_consumed"])

    def test_incomplete_wsta147_hud_restart_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            restart_path = root / "inputs" / "wsta147_dpublic_hud_restart_live.json"
            proof = self.hud_presenter_restart_proof()
            proof["restart"]["done"] = False
            proof["checks"] = runner.wsta147.validate_proof(proof)
            self.write_json(restart_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta147-hud-presenter-restart-proof-json",
                str(restart_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta147-hud-presenter-restart-proof-incomplete")
        self.assertFalse(result["checks"]["hud_presenter_restart_live_proven"])
        self.assertFalse(result["checks"]["hud_presenter_restart_stop_start_proven"])

    def test_nonpass_wsta149_hud_intent_syscall_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            proof = self.hud_intent_syscall_proof()
            proof["decision"] = "wsta149-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta149-hud-intent-syscall-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta149-hud-intent-syscall-proof-not-pass")

    def test_incomplete_wsta149_hud_intent_syscall_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta149_dpublic_hud_intent_syscall_trace_live.json"
            proof = self.hud_intent_syscall_proof()
            proof["syscall_names"].append("socket")
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta149-hud-intent-syscall-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta149-hud-intent-syscall-proof-incomplete")
        self.assertFalse(result["checks"]["hud_intent_syscall_trace_live_proven"])
        self.assertFalse(result["checks"]["hud_intent_syscall_no_network"])

    def test_nonpass_wsta151_dropbear_admin_syscall_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            proof = self.dropbear_admin_syscall_proof()
            proof["decision"] = "wsta151-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta151-dropbear-admin-syscall-proof-not-pass")

    def test_incomplete_wsta151_dropbear_admin_syscall_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta151_dropbear_admin_syscall_trace_live.json"
            proof = self.dropbear_admin_syscall_proof()
            proof["syscall_names"].remove("accept")
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta151-dropbear-admin-syscall-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta151-dropbear-admin-syscall-proof-incomplete")
        self.assertFalse(result["checks"]["dropbear_admin_syscall_trace_live_proven"])
        self.assertFalse(result["checks"]["dropbear_admin_syscall_accept_observed"])

    def test_incomplete_wsta208_seccomp_proof_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta208_result.json"
            proof = self.seccomp_smoke_proof()
            proof["checks"]["seccomp_real_service_markers"] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta208-real-service-seccomp-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta208-real-service-seccomp-proof-incomplete")
        self.assertFalse(result["checks"]["seccomp_smoke_service_live_proven"])
        self.assertFalse(result["checks"]["seccomp_real_services_live_proven"])

    def test_nonpass_wsta209_seccomp_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta209_result.json"
            proof = self.seccomp_dropbear_proof()
            proof["decision"] = "wsta209-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta209-dropbear-admin-seccomp-proof-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta209-dropbear-admin-seccomp-proof-not-pass")

    def test_nonpass_wsta216_default_drop_hardening_policy_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta216_result.json"
            proof = self.default_drop_hardening_policy()
            proof["decision"] = "wsta216-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta216-default-drop-hardening-policy-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta216-default-drop-hardening-policy-not-pass")

    def test_incomplete_wsta216_default_drop_hardening_policy_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta216_result.json"
            proof = self.default_drop_hardening_policy()
            proof["policy"]["live_execution_requested"] = True
            proof["checks"]["policy_no_live_execution"] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta216-default-drop-hardening-policy-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta216-default-drop-hardening-policy-incomplete")
        self.assertFalse(result["checks"]["default_drop_hardening_policy_defined"])
        self.assertFalse(result["checks"]["default_drop_hardening_policy_no_live_execution"])

    def test_nonpass_wsta219_attended_default_drop_live_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta219_operator_workflow.json"
            proof = self.attended_default_drop_live_proof()
            proof["decision"] = "wsta88-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta219-attended-default-drop-live-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta219-attended-default-drop-live-not-pass")

    def test_incomplete_wsta219_attended_default_drop_live_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta219_operator_workflow.json"
            proof = self.attended_default_drop_live_proof()
            proof["wsta80_redacted"]["checks"]["force_packet_filter_restore_proof"] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta219-attended-default-drop-live-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta219-attended-default-drop-live-incomplete")
        self.assertFalse(result["checks"]["attended_default_drop_live_proven"])
        self.assertFalse(result["checks"]["attended_default_drop_live_force_restore_proof"])

    def test_nonpass_wsta221_cloudflared_egress_allowlist_policy_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta221_result.json"
            proof = self.cloudflared_egress_allowlist_policy()
            proof["decision"] = "wsta221-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta221-cloudflared-egress-allowlist-policy-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta221-cloudflared-egress-allowlist-policy-not-pass")

    def test_incomplete_wsta221_cloudflared_egress_allowlist_policy_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta221_result.json"
            proof = self.cloudflared_egress_allowlist_policy()
            proof["policy"]["packet_filter_mutation_by_wsta221"] = True
            proof["checks"]["policy_ready"] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta221-cloudflared-egress-allowlist-policy-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta221-cloudflared-egress-allowlist-policy-incomplete")
        self.assertFalse(result["checks"]["cloudflared_egress_allowlist_policy_defined"])
        self.assertFalse(result["checks"]["cloudflared_egress_allowlist_no_mutation_here"])

    def test_nonpass_wsta229_cloudflared_egress_allowlist_live_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta229_result.json"
            proof = self.cloudflared_egress_allowlist_live_proof()
            proof["decision"] = "wsta226-blocked"
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta229-cloudflared-egress-allowlist-live-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta229-cloudflared-egress-allowlist-live-not-pass")

    def test_incomplete_wsta229_cloudflared_egress_allowlist_live_blocks_even_with_pass_decision(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            proof_path = root / "inputs" / "wsta229_result.json"
            proof = self.cloudflared_egress_allowlist_live_proof()
            proof["wsta88_redacted"]["wsta80_redacted"]["checks"][
                "force_cloudflared_egress_allowlist_proof"
            ] = False
            self.write_json(proof_path, proof)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta229-cloudflared-egress-allowlist-live-json",
                str(proof_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta229-cloudflared-egress-allowlist-live-incomplete")
        self.assertFalse(result["checks"]["cloudflared_egress_allowlist_live_proven"])
        self.assertFalse(result["checks"]["cloudflared_egress_allowlist_live_force_egress_proof"])

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
        self.assertIn("--wsta120-dropbear-admin-proof-json", payload)
        self.assertIn("--wsta151-dropbear-admin-syscall-proof-json", payload)
        self.assertIn("--wsta212-native-uplink-boundary-policy-json", payload)
        self.assertIn("--wsta214-apparmor-feasibility-json", payload)
        self.assertIn("--wsta216-default-drop-hardening-policy-json", payload)
        self.assertIn("--wsta219-attended-default-drop-live-json", payload)
        self.assertIn("--wsta221-cloudflared-egress-allowlist-policy-json", payload)
        self.assertIn("--wsta229-cloudflared-egress-allowlist-live-json", payload)
        self.assertIn("--wsta122-cloudflared-model-json", payload)
        self.assertIn("--wsta125-cloudflared-runtime-proof-json", payload)
        self.assertIn("--wsta127-hud-model-json", payload)
        self.assertIn("--wsta130-hud-presenter-model-json", payload)
        self.assertIn("--wsta137-hud-presenter-live-proof-json", payload)
        self.assertIn("--wsta149-hud-intent-syscall-proof-json", payload)

    def test_source_is_host_only_and_names_server_model(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("SERVER_PROFILE_READY_DEFAULT_OFF", source)
        self.assertIn("native-init", source)
        self.assertIn("service-surface-consumer", source)
        self.assertIn("wsta88-status-hud", source)
        self.assertIn("PACKET_FILTER_LOOPBACK_DEFAULT_DROP_LIVE_PROVEN", source)
        self.assertIn("SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN", source)
        self.assertIn("SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN", source)
        self.assertIn("DROPBEAR_ADMIN_LIVE_PROVEN", source)
        self.assertIn("DROPBEAR_ADMIN_SYSCALL_TRACE_LIVE_PROVEN", source)
        self.assertIn("CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED", source)
        self.assertIn("CLOUDFLARED_RUNTIME_LIVE_PROVEN", source)
        self.assertIn("DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED", source)
        self.assertIn("DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED", source)
        self.assertIn("DPUBLIC_HUD_NATIVE_PRESENTER_LIVE_PROVEN", source)
        self.assertIn("DPUBLIC_HUD_DURABLE_PRESENTER_HANDOFF_LIVE_PROVEN", source)
        self.assertIn("DPUBLIC_HUD_DURABLE_PRESENTER_RESTART_LIVE_PROVEN", source)
        self.assertIn("DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN", source)
        self.assertIn("LEGACY_IPTABLES_DEFAULT_DROP_ATTENDED_LIVE_PROVEN", source)
        self.assertIn("CLOUDFLARED_EGRESS_ALLOWLIST_HARDENING_POLICY_DEFINED", source)
        self.assertIn("CLOUDFLARED_EGRESS_ALLOWLIST_ATTENDED_LIVE_PROVEN", source)
        self.assertIn("split-intent-native-presenter", source)
        self.assertIn("prototype-dpublic-hud-intent-presenter-boundary-before-live-hud-profile", source)
        self.assertIn("design-durable-dpublic-hud-presenter-service-across-debian-handoff", source)
        self.assertIn("continue-dpublic-service-integration-or-containment-hardening", source)
        self.assertIn("profile-dpublic-hud-syscalls-or-continue-containment-hardening", source)
        self.assertIn("continue-containment-hardening-or-derive-hud-seccomp-policy", source)
        self.assertIn("--wsta151-dropbear-admin-syscall-proof-json", source)
        self.assertIn("--wsta137-hud-presenter-live-proof-json", source)
        self.assertIn("--wsta144-hud-presenter-handoff-proof-json", source)
        self.assertIn("--wsta147-hud-presenter-restart-proof-json", source)
        self.assertIn("--wsta149-hud-intent-syscall-proof-json", source)
        self.assertIn("--wsta219-attended-default-drop-live-json", source)
        self.assertIn("--wsta221-cloudflared-egress-allowlist-policy-json", source)
        self.assertIn("--wsta229-cloudflared-egress-allowlist-live-json", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
