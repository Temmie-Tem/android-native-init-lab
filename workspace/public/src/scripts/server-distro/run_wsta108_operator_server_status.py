#!/usr/bin/env python3
"""WSTA108 host-only operator server status bundle.

WSTA88 proves the default-off public workflow.  WSTA90 sketches the service
hardening contract.  WSTA94 proves the loopback default-drop packet filter.
WSTA110 proves the smoke service launcher inside the Debian chroot.  WSTA120
proves the Dropbear admin live gate.  WSTA122 defines the cloudflared
quick-Tunnel service hardening target.  WSTA125 proves that cloudflared runtime
profile behind a native-owned upstream.  WSTA127 defines the original D-public
HUD service hardening target.  WSTA130 supersedes that direct non-root KMS HUD
target with a split intent-producer/native-presenter display contract.  WSTA108
folds WSTA137 native presenter proof, WSTA144 Debian handoff proof, and the
WSTA149 HUD intent syscall trace proof into that
display contract.  WSTA151 captures the Dropbear admin syscall profile.
WSTA108 combines those public surfaces into one
operator-facing server status bundle without opening a tunnel, touching the
device, or weakening any live gate.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta88_persistent_operator_workflow as wsta88  # noqa: E402
import run_wsta90_service_hardening_manifest as wsta90  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402
import run_wsta114_syscall_trace_chroot_profile as wsta114  # noqa: E402
import run_wsta120_dropbear_admin_live_gate as wsta120  # noqa: E402
import run_wsta122_cloudflared_service_model as wsta122  # noqa: E402
import run_wsta125_native_upstream_cloudflared_runtime as wsta125  # noqa: E402
import run_wsta127_dpublic_hud_service_model as wsta127  # noqa: E402
import run_wsta130_dpublic_hud_presenter_model as wsta130  # noqa: E402
import run_wsta137_dpublic_native_presenter_live_summary as wsta137  # noqa: E402
import run_wsta144_dpublic_hud_shared_run_bind_summary as wsta144  # noqa: E402
import run_wsta147_dpublic_hud_restart_live_summary as wsta147  # noqa: E402
import run_wsta149_dpublic_hud_intent_syscall_trace_summary as wsta149  # noqa: E402
import run_wsta151_dropbear_admin_syscall_trace_summary as wsta151  # noqa: E402


REPO_ROOT = wsta88.REPO_ROOT
PRIVATE_ROOT = wsta88.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta88.DEFAULT_RUN_BASE
PASS_DECISION = "wsta108-operator-server-status-source-pass"

CLOUDFLARED_MODEL_STATE = "CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED"
CLOUDFLARED_RUNTIME_STATE = "CLOUDFLARED_RUNTIME_LIVE_PROVEN"
DPUBLIC_HUD_MODEL_STATE = "DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED"
DPUBLIC_HUD_PRESENTER_MODEL_STATE = "DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED"
DPUBLIC_HUD_PRESENTER_LIVE_STATE = "DPUBLIC_HUD_NATIVE_PRESENTER_LIVE_PROVEN"
DPUBLIC_HUD_PRESENTER_HANDOFF_STATE = "DPUBLIC_HUD_DURABLE_PRESENTER_HANDOFF_LIVE_PROVEN"
DPUBLIC_HUD_PRESENTER_RESTART_STATE = "DPUBLIC_HUD_DURABLE_PRESENTER_RESTART_LIVE_PROVEN"
DPUBLIC_HUD_INTENT_SYSCALL_TRACE_STATE = "DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN"
DROPBEAR_ADMIN_SYSCALL_TRACE_STATE = "DROPBEAR_ADMIN_SYSCALL_TRACE_LIVE_PROVEN"

CLOUDFLARED_RUNTIME_REQUIRED_CHECKS = (
    "wsta28_precondition_pass",
    "native_uplink_confirmed",
    "default_route_wlan0",
    "resolver_ready",
    "egress_route_ready",
    "packet_filter_preflight_pass",
    "packet_filter_apply_pass",
    "runtime_probe_completed",
    "cloudflared_uid_gid_pass",
    "cloudflared_no_new_privs_pass",
    "cloudflared_cap_eff_zero_pass",
    "cloudflared_command_shape_pass",
    "cloudflared_outbound_only_pass",
    "private_url_artifact_saved",
    "trace_file_nonempty",
    "syscall_profile_nonempty",
    "syscall_core_observed",
    "trace_artifact_saved",
    "runtime_cleanup_ok",
    "packet_filter_restore_pass",
    "uplink_service_stop_pass",
    "native_uplink_helper_cleanup_ok",
    "native_uplink_profile_cleanup_ok",
    "chroot_cleanup_ok",
    "final_selftest_fail_zero",
)


def rel(path: Path) -> str:
    return wsta88.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta88.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
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
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA108 host-only operator server status bundle",
        "default_mode": "host-only-existing-redacted-wsta88-output",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-server-status",
            "--wsta88-operator-workflow-json",
            "workspace/private/runs/server-distro/<wsta88-run>/wsta88_operator_workflow.json",
            "--wsta90-service-hardening-manifest-json",
            "workspace/private/runs/server-distro/<wsta90-run>/wsta90_service_hardening_manifest.json",
            "--wsta94-packet-filter-proof-json",
            "workspace/private/runs/server-distro/<wsta94-run>/wsta94_result.json",
            "--packet-filter-control-summary-json",
            "workspace/private/runs/server-distro/<packet-filter-control-run>/packet_filter_control_summary.json",
            "--wsta110-service-launcher-proof-json",
            "workspace/private/runs/server-distro/<wsta110-run>/wsta110_result.json",
            "--wsta114-syscall-trace-proof-json",
            "workspace/private/runs/server-distro/<wsta114-run>/wsta114_result.json",
            "--wsta120-dropbear-admin-proof-json",
            "workspace/private/runs/server-distro/<wsta120-run>/wsta120_result.json",
            "--wsta122-cloudflared-model-json",
            "workspace/private/runs/server-distro/<wsta122-run>/wsta122_cloudflared_service_model.json",
            "--wsta125-cloudflared-runtime-proof-json",
            "workspace/private/runs/server-distro/<wsta125-run>/wsta125_result.json",
            "--wsta127-hud-model-json",
            "workspace/private/runs/server-distro/<wsta127-run>/wsta127_dpublic_hud_service_model.json",
            "--wsta130-hud-presenter-model-json",
            "workspace/private/runs/server-distro/<wsta130-run>/wsta130_dpublic_hud_presenter_model.json",
            "--wsta137-hud-presenter-live-proof-json",
            "workspace/private/runs/server-distro/<wsta137-run>/wsta137_dpublic_native_presenter_live.json",
            "--wsta144-hud-presenter-handoff-proof-json",
            "workspace/private/runs/server-distro/<wsta144-run>/wsta144_dpublic_hud_shared_run_bind_live.json",
            "--wsta147-hud-presenter-restart-proof-json",
            "workspace/private/runs/server-distro/<wsta147-run>/wsta147_dpublic_hud_restart_live.json",
            "--wsta149-hud-intent-syscall-proof-json",
            "workspace/private/runs/server-distro/<wsta149-run>/wsta149_dpublic_hud_intent_syscall_trace_live.json",
            "--wsta151-dropbear-admin-syscall-proof-json",
            "workspace/private/runs/server-distro/<wsta151-run>/wsta151_dropbear_admin_syscall_trace_live.json",
        ],
        "device_action": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "server_status": result.get("server_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta88.redaction_findings(payload)


def require_private_file(value: Path | None, label: str) -> tuple[Path | None, str | None]:
    if value is None:
        return None, f"wsta108-blocked-{label}-required"
    path = resolve_path(value)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta108-blocked-{label}-nonprivate"
    if not path.is_file():
        return None, f"wsta108-blocked-{label}-missing"
    return path, None


def marker_present(proof_result: dict[str, Any], marker: str) -> bool:
    probe = proof_result.get("launcher_probe") if isinstance(proof_result.get("launcher_probe"), dict) else {}
    return marker in str(probe.get("stdout") or "")


def packet_filter_marker_present(proof_result: dict[str, Any], marker: str) -> bool:
    probe = (
        proof_result.get("packet_filter_probe")
        if isinstance(proof_result.get("packet_filter_probe"), dict)
        else {}
    )
    return marker in str(probe.get("stdout") or "")


def compact_packet_filter_control_proof(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {
            "state": "NOT_SUPPLIED",
            "control_plane_live_proven": False,
        }
    preflight = (
        summary.get("packet_filter_preflight_parsed")
        if isinstance(summary.get("packet_filter_preflight_parsed"), dict)
        else {}
    )
    apply_result = (
        summary.get("packet_filter_apply_loopback_default_drop_parsed")
        if isinstance(summary.get("packet_filter_apply_loopback_default_drop_parsed"), dict)
        else {}
    )
    control_plane_live_proven = bool(
        summary.get("packet_filter_preflight_rc") == 0
        and summary.get("packet_filter_apply_loopback_default_drop_rc") == 0
        and summary.get("packet_filter_restore_ok")
        and summary.get("ssh_before_marker")
        and summary.get("ssh_after_apply_marker")
        and summary.get("post_mount_absent")
        and summary.get("post_loop_absent")
        and summary.get("post_dropbear_absent")
        and preflight.get("packet_filter_backend") == "legacy-iptables"
        and apply_result.get("packet_filter_policy_class") == "loopback-default-drop"
        and apply_result.get("packet_filter_control_ssh_accept") == "1"
        and apply_result.get("packet_filter_secret_values_logged") == "0"
    )
    return {
        "state": "PACKET_FILTER_CONTROL_PLANE_LIVE_PROVEN" if control_plane_live_proven else "SUPPLIED_NOT_PROVEN",
        "proof_run_dir": summary.get("run_dir"),
        "control_plane_live_proven": control_plane_live_proven,
        "helper_version": apply_result.get("packet_filter_helper_version") or preflight.get("packet_filter_helper_version"),
        "preflight_ok": summary.get("packet_filter_preflight_rc") == 0,
        "apply_ok": summary.get("packet_filter_apply_loopback_default_drop_rc") == 0,
        "restore_ok": bool(summary.get("packet_filter_restore_ok")),
        "control_session_before_apply": bool(summary.get("ssh_before_marker")),
        "control_session_after_apply": bool(summary.get("ssh_after_apply_marker")),
        "cleanup_ok": bool(
            summary.get("post_mount_absent")
            and summary.get("post_loop_absent")
            and summary.get("post_dropbear_absent")
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_packet_filter_proof(
    proof_result: dict[str, Any] | None,
    control_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    control_proof = compact_packet_filter_control_proof(control_summary)
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "loopback_live_proven": False,
            "control_proof": control_proof,
        }

    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    probe = (
        proof_result.get("packet_filter_probe")
        if isinstance(proof_result.get("packet_filter_probe"), dict)
        else {}
    )
    parsed = probe.get("parsed") if isinstance(probe.get("parsed"), dict) else {}
    backend_live_proven = packet_filter_marker_present(proof_result, "packet_filter_backend=legacy-iptables")
    policy_live_proven = packet_filter_marker_present(proof_result, "packet_filter_policy_class=loopback-default-drop")
    loopback_live_proven = bool(
        proof_result.get("decision") == wsta94.PASS_DECISION
        and checks.get("packet_filter_preflight_pass")
        and checks.get("packet_filter_apply_pass")
        and checks.get("packet_filter_default_drop_observed")
        and checks.get("loopback_before_ok")
        and checks.get("loopback_after_ok")
        and checks.get("packet_filter_restore_pass")
        and checks.get("packet_filter_restore_exact")
        and checks.get("chroot_cleanup_ok")
        and checks.get("final_selftest_fail_zero")
        and parsed.get("preflight_pass")
        and parsed.get("apply_pass")
        and parsed.get("v4_input_drop")
        and parsed.get("v6_input_drop")
        and parsed.get("v4_loopback_accept")
        and parsed.get("v6_loopback_accept")
        and parsed.get("restore_exact_v4")
        and parsed.get("restore_exact_v6")
        and parsed.get("probe_pass")
        and backend_live_proven
        and policy_live_proven
    )
    state = "PACKET_FILTER_LOOPBACK_DEFAULT_DROP_LIVE_PROVEN" if loopback_live_proven else "SUPPLIED_NOT_PROVEN"
    if loopback_live_proven and control_proof.get("control_plane_live_proven"):
        state = "PACKET_FILTER_LOOPBACK_AND_CONTROL_PLANE_LIVE_PROVEN"
    return {
        "state": state,
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "loopback_live_proven": loopback_live_proven,
        "backend": "legacy-iptables" if backend_live_proven else None,
        "policy": "loopback-default-drop" if policy_live_proven else None,
        "preflight_ok": bool(checks.get("packet_filter_preflight_pass")),
        "apply_ok": bool(checks.get("packet_filter_apply_pass")),
        "default_drop_observed": bool(checks.get("packet_filter_default_drop_observed")),
        "loopback_before_ok": bool(checks.get("loopback_before_ok")),
        "loopback_after_ok": bool(checks.get("loopback_after_ok")),
        "restore_ok": bool(checks.get("packet_filter_restore_pass")),
        "restore_exact": bool(checks.get("packet_filter_restore_exact")),
        "cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "control_proof": control_proof,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_launcher_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "smoke_live_proven": False,
            "scope": "not-supplied",
        }

    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    probe = proof_result.get("launcher_probe") if isinstance(proof_result.get("launcher_probe"), dict) else {}
    parsed = probe.get("parsed") if isinstance(probe.get("parsed"), dict) else {}
    smoke_identity = wsta110.wsta3.SERVICE_IDENTITIES["dpublic-smoke-httpd"]
    remaining_profiles = [
        "cloudflared-quick-tunnel",
        "dropbear-admin-usb",
        "dpublic-hud",
        "wsta-native-uplink-helper",
    ]
    smoke_live_proven = bool(
        proof_result.get("decision") == wsta110.PASS_DECISION
        and checks.get("public_default_off")
        and checks.get("launcher_fail_closed_blocks")
        and checks.get("launcher_exec_pass")
        and checks.get("launcher_uid_gid_pass")
        and checks.get("launcher_no_new_privs_pass")
        and checks.get("chroot_cleanup_ok")
        and checks.get("final_selftest_fail_zero")
        and marker_present(proof_result, "child_cap_eff=0000000000000000")
    )
    return {
        "state": "SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN" if smoke_live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "scope": "smoke-service-only",
        "smoke_live_proven": smoke_live_proven,
        "service": "dpublic-smoke-httpd",
        "user": smoke_identity["user"],
        "group": smoke_identity["group"],
        "uid": smoke_identity["uid"],
        "gid": smoke_identity["gid"],
        "network_intent": smoke_identity["network_intent"],
        "no_new_privs": bool(checks.get("launcher_no_new_privs_pass") and parsed.get("child_no_new_privs")),
        "cap_eff_zero": marker_present(proof_result, "child_cap_eff=0000000000000000"),
        "public_default_off": bool(checks.get("public_default_off") and parsed.get("public_enable_absent")),
        "fail_closed_branches": {
            "unknown_service": bool(parsed.get("unknown_service_blocks")),
            "command_required": bool(parsed.get("command_required_blocks")),
        },
        "cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "remaining_profiles": remaining_profiles,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_syscall_trace_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "smoke_syscall_trace_live_proven": False,
            "scope": "not-supplied",
        }

    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    profile = (
        proof_result.get("syscall_profile")
        if isinstance(proof_result.get("syscall_profile"), dict)
        else {}
    )
    trace_artifacts = (
        profile.get("trace_artifacts")
        if isinstance(profile.get("trace_artifacts"), dict)
        else {}
    )
    syscall_names = profile.get("syscall_names") if isinstance(profile.get("syscall_names"), list) else []
    core_syscalls = profile.get("core_syscalls") if isinstance(profile.get("core_syscalls"), list) else []
    smoke_syscall_trace_live_proven = bool(
        proof_result.get("decision") == wsta114.PASS_DECISION
        and checks.get("public_default_off")
        and checks.get("strace_present")
        and checks.get("trace_started")
        and checks.get("loopback_get_ok")
        and checks.get("trace_file_nonempty")
        and checks.get("syscall_profile_nonempty")
        and checks.get("syscall_core_observed")
        and checks.get("trace_artifact_saved")
        and checks.get("chroot_cleanup_ok")
        and checks.get("final_selftest_fail_zero")
        and profile.get("service") == "dpublic-smoke-httpd"
        and profile.get("scope") == "smoke-service-only"
        and profile.get("public_default_off")
        and profile.get("loopback_get_ok")
        and profile.get("no_new_privs")
        and profile.get("cap_eff_zero")
        and profile.get("core_syscalls_observed")
        and trace_artifacts.get("all_saved")
        and all(name in syscall_names for name in wsta114.CORE_SYSCALLS)
    )
    return {
        "state": (
            "SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN"
            if smoke_syscall_trace_live_proven
            else "SUPPLIED_NOT_PROVEN"
        ),
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "scope": "smoke-service-only",
        "smoke_syscall_trace_live_proven": smoke_syscall_trace_live_proven,
        "service": "dpublic-smoke-httpd",
        "command_shape": profile.get("command_shape"),
        "core_syscalls": core_syscalls,
        "core_syscalls_observed": bool(profile.get("core_syscalls_observed")),
        "syscall_count": int(profile.get("syscall_count") or 0),
        "syscall_names": syscall_names,
        "trace_artifacts_saved": bool(trace_artifacts.get("all_saved")),
        "public_default_off": bool(profile.get("public_default_off")),
        "loopback_get_ok": bool(profile.get("loopback_get_ok")),
        "no_new_privs": bool(profile.get("no_new_privs")),
        "cap_eff_zero": bool(profile.get("cap_eff_zero")),
        "cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "remaining_profiles": [
            "cloudflared-quick-tunnel",
            "dropbear-admin-usb",
            "dpublic-hud",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_dropbear_admin_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "dropbear_admin_live_proven": False,
            "scope": "not-supplied",
        }

    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    stage = (
        proof_result.get("admin_stage_parse")
        if isinstance(proof_result.get("admin_stage_parse"), dict)
        else {}
    )
    admin_ssh = (
        proof_result.get("admin_ssh_parse")
        if isinstance(proof_result.get("admin_ssh_parse"), dict)
        else {}
    )
    cleanup = (
        proof_result.get("admin_key_cleanup_parse")
        if isinstance(proof_result.get("admin_key_cleanup_parse"), dict)
        else {}
    )
    postcheck = (
        proof_result.get("postcheck_parse")
        if isinstance(proof_result.get("postcheck_parse"), dict)
        else {}
    )
    root_ssh = proof_result.get("root_ssh") if isinstance(proof_result.get("root_ssh"), dict) else {}
    dropbear_admin_live_proven = bool(
        proof_result.get("decision") == wsta120.PASS_DECISION
        and checks.get("explicit_live_gate")
        and checks.get("baseline_selftest_fail_zero")
        and checks.get("remote_image_ready")
        and checks.get("chroot_mount_ready")
        and checks.get("admin_stage_pass")
        and checks.get("admin_ssh_pass")
        and checks.get("root_ssh_rejected")
        and checks.get("admin_key_cleanup_ok")
        and checks.get("chroot_cleanup_ok")
        and checks.get("final_selftest_fail_zero")
        and stage.get("root_authorized_keys_absent")
        and stage.get("admin_passwd_line")
        and stage.get("admin_group_line")
        and stage.get("admin_shadow_line")
        and stage.get("admin_authorized_keys")
        and stage.get("dropbear_present")
        and stage.get("dropbear_command_safe")
        and stage.get("dropbear_alive")
        and stage.get("dropbear_listen")
        and admin_ssh.get("ssh_ok")
        and admin_ssh.get("uid_3903")
        and admin_ssh.get("gid_3903")
        and admin_ssh.get("user_a90admin")
        and admin_ssh.get("group_a90admin")
        and root_ssh.get("returncode") != 0
        and cleanup.get("cleanup_done")
        and cleanup.get("admin_keys_absent")
        and postcheck.get("dropbear_absent")
        and postcheck.get("mount_absent")
        and postcheck.get("loop_node_absent")
    )
    return {
        "state": "DROPBEAR_ADMIN_LIVE_PROVEN" if dropbear_admin_live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "scope": "dropbear-admin-usb-only",
        "dropbear_admin_live_proven": dropbear_admin_live_proven,
        "service": "dropbear-admin-usb",
        "daemon_privilege_model": "root-boundary-auth-daemon",
        "user": "a90admin",
        "group": "a90admin",
        "uid": 3903,
        "gid": 3903,
        "bind": "192.168.7.2:2222",
        "root_authorized_keys_absent": bool(stage.get("root_authorized_keys_absent")),
        "root_ssh_rejected": bool(checks.get("root_ssh_rejected") and root_ssh.get("returncode") != 0),
        "password_login_disabled": bool(stage.get("dropbear_command_safe")),
        "root_login_disabled": bool(stage.get("dropbear_command_safe")),
        "forwarding_disabled": bool(stage.get("dropbear_command_safe")),
        "admin_key_cleanup_ok": bool(cleanup.get("cleanup_done") and cleanup.get("admin_keys_absent")),
        "final_dropbear_absent": bool(postcheck.get("dropbear_absent")),
        "cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "remaining_profiles": [
            "cloudflared-quick-tunnel",
            "dpublic-hud",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_dropbear_admin_syscall_trace_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "dropbear_admin_syscall_trace_live_proven": False,
            "scope": "not-supplied",
        }
    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    syscalls = proof_result.get("syscall_names") if isinstance(proof_result.get("syscall_names"), list) else []
    core_syscalls_observed = bool(
        proof_result.get("core_syscalls_observed")
        and all(name in syscalls for name in wsta151.CORE_SYSCALLS)
    )
    accept_observed = bool(
        proof_result.get("accept_observed")
        and any(name in syscalls for name in wsta151.ACCEPT_SYSCALLS)
    )
    live_proven = bool(
        proof_result.get("decision") == wsta151.PASS_DECISION
        and proof_result.get("service") == "dropbear-admin-usb"
        and proof_result.get("scope") == "dropbear-admin-usb-daemon"
        and proof_result.get("daemon_privilege_model") == "root-boundary-auth-daemon"
        and proof_result.get("network_scope") == "usb-ncm-admin-only"
        and proof_result.get("uid") == 3903
        and proof_result.get("gid") == 3903
        and proof_result.get("admin_login_uid_gid_proven")
        and proof_result.get("root_ssh_rejected")
        and proof_result.get("root_authorized_keys_absent")
        and proof_result.get("password_login_disabled")
        and proof_result.get("root_login_disabled")
        and proof_result.get("forwarding_disabled")
        and core_syscalls_observed
        and accept_observed
        and proof_result.get("trace_artifacts_saved")
        and all(value is True for value in checks.values())
    )
    return {
        "state": DROPBEAR_ADMIN_SYSCALL_TRACE_STATE if live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("source_run_dir"),
        "scope": "dropbear-admin-usb-daemon",
        "dropbear_admin_syscall_trace_live_proven": live_proven,
        "service": "dropbear-admin-usb",
        "daemon": proof_result.get("daemon"),
        "daemon_privilege_model": proof_result.get("daemon_privilege_model"),
        "bind": proof_result.get("bind"),
        "network_scope": proof_result.get("network_scope"),
        "uid": proof_result.get("uid"),
        "gid": proof_result.get("gid"),
        "admin_login_uid_gid_proven": bool(proof_result.get("admin_login_uid_gid_proven")),
        "root_ssh_rejected": bool(proof_result.get("root_ssh_rejected")),
        "root_authorized_keys_absent": bool(proof_result.get("root_authorized_keys_absent")),
        "password_login_disabled": bool(proof_result.get("password_login_disabled")),
        "root_login_disabled": bool(proof_result.get("root_login_disabled")),
        "forwarding_disabled": bool(proof_result.get("forwarding_disabled")),
        "core_syscalls_observed": core_syscalls_observed,
        "accept_observed": accept_observed,
        "core_syscalls": list(proof_result.get("core_syscalls") or []),
        "accept_syscalls": list(proof_result.get("accept_syscalls") or []),
        "syscall_count": int(proof_result.get("syscall_count") or 0),
        "syscall_names": syscalls,
        "trace_artifacts_saved": bool(proof_result.get("trace_artifacts_saved")),
        "raw_trace_sha256": proof_result.get("raw_trace_sha256"),
        "syscall_list_sha256": proof_result.get("syscall_list_sha256"),
        "dropbear_log_sha256": proof_result.get("dropbear_log_sha256"),
        "public_url_value_logged": False,
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_cloudflared_model(model_result: dict[str, Any] | None) -> dict[str, Any]:
    if not model_result:
        return {
            "state": "NOT_SUPPLIED",
            "model_defined": False,
            "cloudflared_live_proven": False,
            "scope": "not-supplied",
        }

    model = (
        model_result.get("cloudflared_service_model")
        if isinstance(model_result.get("cloudflared_service_model"), dict)
        else {}
    )
    supplied_checks = model_result.get("checks") if isinstance(model_result.get("checks"), dict) else {}
    recomputed_checks = wsta122.validate_model(model)
    model_defined = bool(
        model_result.get("decision") == wsta122.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    identity = model.get("target_identity") if isinstance(model.get("target_identity"), dict) else {}
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    network = model.get("network") if isinstance(model.get("network"), dict) else {}
    launcher = model.get("launcher_policy") if isinstance(model.get("launcher_policy"), dict) else {}
    runtime = model.get("runtime_files") if isinstance(model.get("runtime_files"), dict) else {}
    credentials = model.get("credentials") if isinstance(model.get("credentials"), dict) else {}
    return {
        "state": CLOUDFLARED_MODEL_STATE if model_defined else "SUPPLIED_NOT_PROVEN",
        "decision": model_result.get("decision"),
        "proof_run_dir": model_result.get("run_dir"),
        "scope": "cloudflared-quick-tunnel-model-only",
        "model_defined": model_defined,
        "cloudflared_live_proven": False,
        "service": "cloudflared-quick-tunnel",
        "daemon_privilege_model": model.get("daemon_privilege_model"),
        "user": identity.get("user"),
        "group": identity.get("group"),
        "uid": identity.get("uid"),
        "gid": identity.get("gid"),
        "default_public_off": exposure.get("public_default") == "off",
        "explicit_enable_required": exposure.get("start_requires_private_enable_file")
        == wsta122.QUICK_ENABLE,
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "boot_autostart_without_enable_file_denied": (
            exposure.get("boot_autostart_without_enable_file") is False
        ),
        "origin_loopback_only": network.get("origin_scope") == "loopback-only",
        "metrics_loopback_ephemeral": network.get("metrics_scope") == "loopback-ephemeral",
        "outbound_only": bool(
            network.get("outbound_tunnel_client") is True
            and network.get("public_inbound_listener") is False
        ),
        "packet_filter_precondition": network.get("packet_filter_precondition"),
        "launcher_required": launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch",
        "launcher_user": launcher.get("target_user"),
        "launcher_no_new_privs_required": launcher.get("no_new_privs") is True,
        "launcher_caps_zero_required": launcher.get("effective_capabilities") == "zero",
        "direct_root_start_rejected_for_always_on": launcher.get("direct_root_firstboot_start")
        == "not-acceptable-for-always-on-profile",
        "url_file_private": bool(
            runtime.get("url_file_mode") == "0600"
            and runtime.get("public_url_committable") is False
        ),
        "no_named_tunnel_secret_required": bool(
            credentials.get("quick_tunnel_accountless") is True
            and credentials.get("named_tunnel_credentials_required") is False
            and credentials.get("token_in_command") is False
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "remaining_live_proofs": [
            "launcher runtime user/group and no-new-privs/cap-zero",
            "outbound-only network observation",
            "private URL artifact capture without committed URL value",
            "cleanup removes cloudflared process and runtime sidecars",
            "cloudflared syscall trace before seccomp enforcement",
        ],
    }


def compact_cloudflared_runtime_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "cloudflared_live_proven": False,
            "scope": "not-supplied",
        }

    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    profile = (
        proof_result.get("cloudflared_runtime_profile")
        if isinstance(proof_result.get("cloudflared_runtime_profile"), dict)
        else {}
    )
    trace_artifacts = (
        proof_result.get("trace_artifacts")
        if isinstance(proof_result.get("trace_artifacts"), dict)
        else {}
    )
    if not trace_artifacts and isinstance(profile.get("trace_artifacts"), dict):
        trace_artifacts = profile["trace_artifacts"]
    url_artifact = (
        proof_result.get("private_url_artifact")
        if isinstance(proof_result.get("private_url_artifact"), dict)
        else {}
    )
    syscall_names = profile.get("syscall_names") if isinstance(profile.get("syscall_names"), list) else []
    core_syscalls = profile.get("core_syscalls") if isinstance(profile.get("core_syscalls"), list) else []
    required_syscalls = list(wsta125.wsta124.CORE_SYSCALLS)
    all_required_checks = all(checks.get(key) is True for key in CLOUDFLARED_RUNTIME_REQUIRED_CHECKS)
    url_redacted = bool(
        url_artifact.get("url_artifact_saved")
        and url_artifact.get("stdout_redacted")
        and url_artifact.get("public_url_value_logged") is False
        and int(url_artifact.get("secret_values_logged") or 0) == 0
    )
    trace_saved = bool(
        trace_artifacts.get("all_saved")
        and trace_artifacts.get("private_artifact")
        and trace_artifacts.get("public_url_value_logged") is False
        and int(trace_artifacts.get("secret_values_logged") or 0) == 0
    )
    profile_redacted = bool(
        profile.get("public_url_value_logged") is False
        and int(profile.get("secret_values_logged") or 0) == 0
    )
    top_redacted = bool(
        proof_result.get("public_url_value_logged", False) is False
        and int(proof_result.get("secret_values_logged") or 0) == 0
    )
    core_syscalls_observed = bool(
        profile.get("core_syscalls_observed")
        and all(name in syscall_names for name in required_syscalls)
    )
    cloudflared_live_proven = bool(
        proof_result.get("decision") == wsta125.PASS_DECISION
        and all_required_checks
        and profile.get("service") == wsta125.wsta124.wsta122.SERVICE
        and profile.get("scope") == "cloudflared-quick-tunnel-runtime"
        and profile.get("uid_gid_proven")
        and profile.get("no_new_privs")
        and profile.get("cap_eff_zero")
        and profile.get("command_shape_proven")
        and profile.get("outbound_only")
        and profile.get("outbound_observed")
        and profile.get("private_url_artifact")
        and profile.get("syscall_count", 0) > 0
        and core_syscalls_observed
        and url_redacted
        and trace_saved
        and profile_redacted
        and top_redacted
    )
    return {
        "state": CLOUDFLARED_RUNTIME_STATE if cloudflared_live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "scope": "cloudflared-quick-tunnel-runtime",
        "cloudflared_live_proven": cloudflared_live_proven,
        "service": wsta125.wsta124.wsta122.SERVICE,
        "user": profile.get("user"),
        "uid": profile.get("uid"),
        "gid": profile.get("gid"),
        "native_upstream_confirmed": bool(checks.get("native_uplink_confirmed")),
        "default_route_wlan0": bool(checks.get("default_route_wlan0")),
        "resolver_ready": bool(checks.get("resolver_ready")),
        "egress_route_ready": bool(checks.get("egress_route_ready")),
        "packet_filter_apply_pass": bool(checks.get("packet_filter_apply_pass")),
        "packet_filter_restore_pass": bool(checks.get("packet_filter_restore_pass")),
        "uid_gid_proven": bool(profile.get("uid_gid_proven")),
        "no_new_privs": bool(profile.get("no_new_privs")),
        "cap_eff_zero": bool(profile.get("cap_eff_zero")),
        "command_shape_proven": bool(profile.get("command_shape_proven")),
        "outbound_only": bool(profile.get("outbound_only")),
        "outbound_observed": bool(profile.get("outbound_observed")),
        "socket_outbound_hint": bool(profile.get("socket_outbound_hint")),
        "udp_outbound": bool(profile.get("udp_outbound")),
        "private_url_artifact": bool(profile.get("private_url_artifact") and url_artifact.get("url_artifact_saved")),
        "private_url_redacted": url_redacted,
        "trace_artifacts_saved": trace_saved,
        "core_syscalls": core_syscalls,
        "core_syscalls_observed": core_syscalls_observed,
        "syscall_count": int(profile.get("syscall_count") or 0),
        "syscall_names": syscall_names,
        "runtime_cleanup_ok": bool(checks.get("runtime_cleanup_ok")),
        "uplink_service_stop_pass": bool(checks.get("uplink_service_stop_pass")),
        "native_uplink_helper_cleanup_ok": bool(checks.get("native_uplink_helper_cleanup_ok")),
        "native_uplink_profile_cleanup_ok": bool(checks.get("native_uplink_profile_cleanup_ok")),
        "chroot_cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_hud_model(model_result: dict[str, Any] | None) -> dict[str, Any]:
    if not model_result:
        return {
            "state": "NOT_SUPPLIED",
            "model_defined": False,
            "hud_live_proven": False,
            "scope": "not-supplied",
        }

    model = (
        model_result.get("hud_service_model")
        if isinstance(model_result.get("hud_service_model"), dict)
        else {}
    )
    supplied_checks = model_result.get("checks") if isinstance(model_result.get("checks"), dict) else {}
    recomputed_checks = wsta127.validate_model(model)
    model_defined = bool(
        model_result.get("decision") == wsta127.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    identity = model.get("target_identity") if isinstance(model.get("target_identity"), dict) else {}
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    network = model.get("network") if isinstance(model.get("network"), dict) else {}
    display = model.get("display") if isinstance(model.get("display"), dict) else {}
    launcher = model.get("launcher_policy") if isinstance(model.get("launcher_policy"), dict) else {}
    runtime = model.get("runtime_files") if isinstance(model.get("runtime_files"), dict) else {}
    return {
        "state": DPUBLIC_HUD_MODEL_STATE if model_defined else "SUPPLIED_NOT_PROVEN",
        "decision": model_result.get("decision"),
        "proof_run_dir": model_result.get("run_dir"),
        "scope": "dpublic-hud-model-only",
        "model_defined": model_defined,
        "hud_live_proven": False,
        "service": wsta127.SERVICE,
        "daemon_privilege_model": model.get("daemon_privilege_model"),
        "user": identity.get("user"),
        "group": identity.get("group"),
        "uid": identity.get("uid"),
        "gid": identity.get("gid"),
        "default_public_off": exposure.get("public_default") == "off",
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "boot_autostart_without_device_policy_denied": (
            exposure.get("boot_autostart_without_device_policy") is False
        ),
        "no_network_autostart": exposure.get("network_autostart") is False,
        "no_network_listener": bool(
            network.get("opens_tcp_listener") is False
            and network.get("opens_udp_socket") is False
            and network.get("public_inbound_listener") is False
        ),
        "packet_filter_not_required": network.get("requires_packet_filter") is False,
        "drm_node": display.get("device_node"),
        "drm_node_policy": display.get("device_node_policy"),
        "drm_node_policy_defined": bool(
            display.get("device_node") == wsta127.DRM_NODE
            and display.get("device_source") == wsta127.DRM_SYSFS_DEV
            and display.get("device_node_policy") == "card0-owned-or-group-readable-by-a90hud-before-launch"
        ),
        "drm_master_required": display.get("drm_master_required") is True,
        "kms_surface": display.get("kms_surface"),
        "launcher_required": launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch",
        "launcher_user": launcher.get("target_user"),
        "launcher_no_new_privs_required": launcher.get("no_new_privs") is True,
        "launcher_caps_zero_required": launcher.get("effective_capabilities") == "zero",
        "direct_root_start_rejected_for_always_on": launcher.get("direct_root_firstboot_start")
        == "not-acceptable-for-always-on-profile",
        "runtime_files_private": bool(
            runtime.get("pid_file_private") is True
            and runtime.get("log_file_committable") is False
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "remaining_live_proofs": [
            "launcher runtime user/group and no-new-privs/cap-zero",
            "DRM card0 node ownership/group policy",
            "no-network runtime socket observation",
            "DRM/KMS syscall trace before seccomp enforcement",
            "cleanup removes HUD process and runtime sidecars",
        ],
    }


def compact_hud_presenter_live_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "native_presenter_live_proven": False,
        }

    supplied_checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    recomputed_checks = wsta137.validate_proof(proof_result)
    live_proven = bool(
        proof_result.get("decision") == wsta137.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    candidate = proof_result.get("candidate") if isinstance(proof_result.get("candidate"), dict) else {}
    checked_flash = (
        proof_result.get("checked_flash")
        if isinstance(proof_result.get("checked_flash"), dict)
        else {}
    )
    validate = (
        proof_result.get("validate_proof")
        if isinstance(proof_result.get("validate_proof"), dict)
        else {}
    )
    present = (
        proof_result.get("present_proof")
        if isinstance(proof_result.get("present_proof"), dict)
        else {}
    )
    reject = (
        proof_result.get("reject_proof")
        if isinstance(proof_result.get("reject_proof"), dict)
        else {}
    )
    final_health = (
        proof_result.get("final_health")
        if isinstance(proof_result.get("final_health"), dict)
        else {}
    )
    return {
        "state": DPUBLIC_HUD_PRESENTER_LIVE_STATE if live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "source_run_dir": proof_result.get("source_run_dir"),
        "native_presenter_live_proven": live_proven,
        "candidate_init_version": candidate.get("init_version"),
        "candidate_init_build": candidate.get("init_build"),
        "candidate_boot_sha256": candidate.get("boot_sha256"),
        "checked_flash_used": bool(checked_flash.get("used_checked_helper")),
        "checked_flash_sha_matched": bool(
            checked_flash.get("local_sha_match")
            and checked_flash.get("remote_sha_match")
            and checked_flash.get("boot_readback_sha_match")
        ),
        "checked_flash_boot_health_clean": bool(
            checked_flash.get("booted_v3398")
            and checked_flash.get("boot_ok")
            and checked_flash.get("selftest_fail_zero")
            and checked_flash.get("transport_serial_ready")
            and checked_flash.get("transport_tcpctl_ready")
        ),
        "validate_intent_sequence": validate.get("sequence"),
        "validate_intent_age_ms": validate.get("age_ms"),
        "validate_policy_markers": bool(
            validate.get("forbidden_fields_reject")
            and validate.get("unknown_fields_reject")
            and validate.get("stale_after_marker")
            and validate.get("presenter_owner_native_root")
            and validate.get("debian_direct_kms_zero")
        ),
        "present_sequence": present.get("sequence"),
        "present_age_ms": present.get("age_ms"),
        "present_begin_frame_rc_zero": bool(present.get("present_begin_frame_rc_zero")),
        "present_rc_zero": bool(present.get("present_rc_zero")),
        "present_done": bool(present.get("present_done")),
        "present_framebuffer": present.get("framebuffer"),
        "present_crtc": present.get("crtc"),
        "reject_forbidden_command": bool(
            reject.get("forbidden_command_rejected") and reject.get("forbidden_rc") == -1
        ),
        "reject_stale_intent": bool(
            reject.get("stale_rejected") and reject.get("stale_rc") == -110
        ),
        "final_health_clean": bool(
            final_health.get("v3398_resident")
            and final_health.get("selftest_fail_zero")
            and final_health.get("transport_serial_ready")
            and final_health.get("transport_tcpctl_ready")
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_hud_presenter_handoff_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "handoff_live_proven": False,
        }

    supplied_checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    recomputed_checks = wsta144.validate_proof(proof_result)
    handoff_proven = bool(
        proof_result.get("decision") == wsta144.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    candidate = proof_result.get("candidate") if isinstance(proof_result.get("candidate"), dict) else {}
    checked_flash = (
        proof_result.get("checked_flash")
        if isinstance(proof_result.get("checked_flash"), dict)
        else {}
    )
    native = (
        proof_result.get("native_presenter_pre_handoff")
        if isinstance(proof_result.get("native_presenter_pre_handoff"), dict)
        else {}
    )
    handoff = proof_result.get("handoff") if isinstance(proof_result.get("handoff"), dict) else {}
    debian = proof_result.get("debian") if isinstance(proof_result.get("debian"), dict) else {}
    shared = (
        proof_result.get("shared_run_compare")
        if isinstance(proof_result.get("shared_run_compare"), dict)
        else {}
    )
    drm = (
        proof_result.get("drm_ownership")
        if isinstance(proof_result.get("drm_ownership"), dict)
        else {}
    )
    writer = (
        proof_result.get("a90hud_intent_writer")
        if isinstance(proof_result.get("a90hud_intent_writer"), dict)
        else {}
    )
    consumption = (
        proof_result.get("presenter_consumption")
        if isinstance(proof_result.get("presenter_consumption"), dict)
        else {}
    )
    final_health = (
        proof_result.get("final_health")
        if isinstance(proof_result.get("final_health"), dict)
        else {}
    )
    return {
        "state": DPUBLIC_HUD_PRESENTER_HANDOFF_STATE if handoff_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "source_run_dir": proof_result.get("source_run_dir"),
        "handoff_live_proven": handoff_proven,
        "candidate_init_version": candidate.get("init_version"),
        "candidate_init_build": candidate.get("init_build"),
        "candidate_boot_sha256": candidate.get("boot_sha256"),
        "checked_flash_used": bool(checked_flash.get("used_checked_helper")),
        "checked_flash_sha_matched": bool(
            checked_flash.get("local_sha_match")
            and checked_flash.get("remote_sha_match")
            and checked_flash.get("boot_readback_sha_match")
        ),
        "checked_flash_boot_health_clean": bool(
            checked_flash.get("booted_v3401")
            and checked_flash.get("boot_ok")
            and checked_flash.get("selftest_fail_zero")
            and checked_flash.get("transport_serial_ready")
            and checked_flash.get("transport_tcpctl_ready")
        ),
        "presenter_pid": native.get("pid") or drm.get("presenter_pid"),
        "native_shared_run_mounted": bool(
            native.get("shared_run_marker")
            and native.get("shared_run_tmpfs_mounted")
            and native.get("status_drm_fd")
        ),
        "native_pre_handoff_sequence": native.get("pre_sequence"),
        "native_pre_handoff_present_rc": native.get("pre_present_rc"),
        "switch_root_exec_reached": bool(handoff.get("switch_root_exec_reached")),
        "handoff_preserved_presenter": bool(handoff.get("presenter_preserved")),
        "handoff_shared_run_bind_ok": bool(handoff.get("shared_run_bind_ok")),
        "handoff_shared_run_same_dev": bool(handoff.get("shared_run_same_dev")),
        "handoff_shared_run_same_ino": bool(handoff.get("shared_run_same_ino")),
        "debian_pid1_init": bool(debian.get("pid1_comm_init")),
        "debian_root_userdata_ext4": bool(debian.get("root_is_userdata_ext4")),
        "debian_run_dir_root_a90hud_1770": bool(debian.get("run_dir_root_a90hud_1770")),
        "shared_run_same_mount_after_handoff": bool(
            shared.get("same_dev") and shared.get("same_ino") and shared.get("tmpfs")
        ),
        "presenter_sole_drm_owner_after_handoff": bool(
            drm.get("sole_drm_owner_before") and drm.get("sole_drm_owner_after")
        ),
        "a90hud_writer_uid_gid_3904": bool(writer.get("uid_3904") and writer.get("gid_3904")),
        "a90hud_writer_cap_eff_zero": bool(writer.get("cap_eff_zero")),
        "a90hud_writer_no_drm_fd": bool(writer.get("no_drm_fd")),
        "a90hud_writer_no_network_intent": bool(writer.get("no_network_intent")),
        "debian_intent_sequence": writer.get("intent_sequence"),
        "debian_intent_owner_a90hud": bool(writer.get("intent_owner_a90hud")),
        "presenter_status_after_sequence": consumption.get("status_after_sequence"),
        "presenter_status_after_present_rc": consumption.get("status_after_present_rc"),
        "fresh_debian_intent_consumed": bool(consumption.get("fresh_debian_intent_consumed")),
        "final_health_clean": bool(
            final_health.get("v3401_resident")
            and final_health.get("selftest_fail_zero")
            and final_health.get("transport_serial_ready")
            and final_health.get("transport_tcpctl_ready")
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_hud_presenter_restart_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "restart_live_proven": False,
        }

    supplied_checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    recomputed_checks = wsta147.validate_proof(proof_result)
    restart_proven = bool(
        proof_result.get("decision") == wsta147.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    candidate = proof_result.get("candidate") if isinstance(proof_result.get("candidate"), dict) else {}
    checked_flash = (
        proof_result.get("checked_flash")
        if isinstance(proof_result.get("checked_flash"), dict)
        else {}
    )
    pre = proof_result.get("pre_restart") if isinstance(proof_result.get("pre_restart"), dict) else {}
    restart = proof_result.get("restart") if isinstance(proof_result.get("restart"), dict) else {}
    post = proof_result.get("post_restart") if isinstance(proof_result.get("post_restart"), dict) else {}
    stop = (
        proof_result.get("stop_after_restart")
        if isinstance(proof_result.get("stop_after_restart"), dict)
        else {}
    )
    stale = (
        proof_result.get("stale_pid_cleanup")
        if isinstance(proof_result.get("stale_pid_cleanup"), dict)
        else {}
    )
    final_health = (
        proof_result.get("final_health")
        if isinstance(proof_result.get("final_health"), dict)
        else {}
    )
    return {
        "state": DPUBLIC_HUD_PRESENTER_RESTART_STATE if restart_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("run_dir"),
        "source_run_dir": proof_result.get("source_run_dir"),
        "restart_live_proven": restart_proven,
        "candidate_init_version": candidate.get("init_version"),
        "candidate_init_build": candidate.get("init_build"),
        "candidate_boot_sha256": candidate.get("boot_sha256"),
        "checked_flash_used": bool(checked_flash.get("used_checked_helper")),
        "checked_flash_sha_matched": bool(
            checked_flash.get("local_sha_match")
            and checked_flash.get("remote_sha_match")
            and checked_flash.get("boot_readback_sha_match")
        ),
        "checked_flash_boot_health_clean": bool(
            checked_flash.get("booted_v3402")
            and checked_flash.get("boot_ok")
            and checked_flash.get("selftest_fail_zero")
            and checked_flash.get("verify_native_passed")
        ),
        "pre_restart_pid": pre.get("start_pid"),
        "pre_restart_sequence": pre.get("status_file_sequence"),
        "pre_restart_present_rc": pre.get("status_file_present_rc"),
        "pre_restart_drm_fd": bool(pre.get("status_drm_fd")),
        "restart_policy": restart.get("policy"),
        "restart_stop_pid": restart.get("stop_pid"),
        "restart_start_pid": restart.get("start_pid"),
        "restart_stop_rc": restart.get("stop_rc"),
        "restart_start_rc": restart.get("start_rc"),
        "restart_done": bool(restart.get("done")),
        "post_restart_sequence": post.get("status_file_sequence"),
        "post_restart_present_rc": post.get("status_file_present_rc"),
        "post_restart_drm_fd": bool(post.get("status_drm_fd")),
        "stop_after_restart_done": bool(stop.get("stop_done")),
        "stale_pid_cleanup_marker": bool(stale.get("stale_cleanup_marker")),
        "stale_pid_cleanup_fake_pid": stale.get("fake_pid"),
        "stale_pid_cleanup_start_done": bool(stale.get("start_done")),
        "final_status_stopped": bool(stale.get("final_status_stopped")),
        "final_health_clean": bool(
            final_health.get("v3402_resident")
            and final_health.get("boot_ok")
            and final_health.get("selftest_fail_zero")
            and final_health.get("transport_serial_ready")
            and final_health.get("transport_ncm_ready")
            and final_health.get("transport_tcpctl_ready")
        ),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_hud_intent_syscall_trace_proof(proof_result: dict[str, Any] | None) -> dict[str, Any]:
    if not proof_result:
        return {
            "state": "NOT_SUPPLIED",
            "hud_intent_syscall_trace_live_proven": False,
            "scope": "not-supplied",
        }
    checks = proof_result.get("checks") if isinstance(proof_result.get("checks"), dict) else {}
    syscalls = proof_result.get("syscall_names") if isinstance(proof_result.get("syscall_names"), list) else []
    atomic_rename_observed = bool(
        proof_result.get("atomic_rename_observed")
        and "fsync" in syscalls
        and any(name in syscalls for name in wsta149.ATOMIC_RENAME_SYSCALLS)
    )
    network_syscalls_absent = bool(
        proof_result.get("network_syscalls_absent")
        and not any(name in syscalls for name in wsta149.NETWORK_SYSCALLS)
    )
    ioctl_syscall_absent = bool(proof_result.get("ioctl_syscall_absent") and "ioctl" not in syscalls)
    drm_trace_absent = bool(proof_result.get("drm_trace_absent"))
    live_proven = bool(
        proof_result.get("decision") == wsta149.PASS_DECISION
        and proof_result.get("service") == "dpublic-hud"
        and proof_result.get("scope") == "hud-intent-producer-only"
        and proof_result.get("uid") == 3904
        and proof_result.get("gid") == 3904
        and proof_result.get("no_new_privs")
        and proof_result.get("cap_eff_zero")
        and proof_result.get("public_default_off")
        and proof_result.get("native_presenter_owner")
        and atomic_rename_observed
        and network_syscalls_absent
        and ioctl_syscall_absent
        and drm_trace_absent
        and proof_result.get("trace_artifacts_saved")
        and all(value is True for value in checks.values())
    )
    return {
        "state": DPUBLIC_HUD_INTENT_SYSCALL_TRACE_STATE if live_proven else "SUPPLIED_NOT_PROVEN",
        "decision": proof_result.get("decision"),
        "proof_run_dir": proof_result.get("source_run_dir"),
        "scope": "hud-intent-producer-only",
        "hud_intent_syscall_trace_live_proven": live_proven,
        "service": "dpublic-hud",
        "intent_path": proof_result.get("intent_path"),
        "intent_sequence": proof_result.get("intent_sequence"),
        "uid": proof_result.get("uid"),
        "gid": proof_result.get("gid"),
        "no_new_privs": bool(proof_result.get("no_new_privs")),
        "cap_eff_zero": bool(proof_result.get("cap_eff_zero")),
        "public_default_off": bool(proof_result.get("public_default_off")),
        "native_presenter_owner": bool(proof_result.get("native_presenter_owner")),
        "atomic_rename_observed": atomic_rename_observed,
        "network_syscalls_absent": network_syscalls_absent,
        "ioctl_syscall_absent": ioctl_syscall_absent,
        "drm_trace_absent": drm_trace_absent,
        "core_syscalls_observed": bool(proof_result.get("core_syscalls_observed")),
        "core_syscalls": list(proof_result.get("core_syscalls") or []),
        "syscall_count": int(proof_result.get("syscall_count") or 0),
        "syscall_names": syscalls,
        "trace_artifacts_saved": bool(proof_result.get("trace_artifacts_saved")),
        "raw_trace_sha256": proof_result.get("raw_trace_sha256"),
        "syscall_list_sha256": proof_result.get("syscall_list_sha256"),
        "intent_json_sha256": proof_result.get("intent_json_sha256"),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def compact_hud_presenter_model(
    model_result: dict[str, Any] | None,
    live_proof_result: dict[str, Any] | None,
    handoff_proof_result: dict[str, Any] | None,
    restart_proof_result: dict[str, Any] | None,
    intent_syscall_proof_result: dict[str, Any] | None,
) -> dict[str, Any]:
    live_proof = compact_hud_presenter_live_proof(live_proof_result)
    handoff_proof = compact_hud_presenter_handoff_proof(handoff_proof_result)
    restart_proof = compact_hud_presenter_restart_proof(restart_proof_result)
    intent_syscall_proof = compact_hud_intent_syscall_trace_proof(intent_syscall_proof_result)
    if not model_result:
        return {
            "state": "NOT_SUPPLIED",
            "model_defined": False,
            "scope": "not-supplied",
            "hud_live_proven": False,
            "live_proof": live_proof,
            "handoff_proof": handoff_proof,
            "restart_proof": restart_proof,
            "intent_syscall_trace_proof": intent_syscall_proof,
        }

    model = (
        model_result.get("presenter_architecture_model")
        if isinstance(model_result.get("presenter_architecture_model"), dict)
        else {}
    )
    supplied_checks = model_result.get("checks") if isinstance(model_result.get("checks"), dict) else {}
    recomputed_checks = wsta130.validate_model(model)
    model_defined = bool(
        model_result.get("decision") == wsta130.PASS_DECISION
        and bool(supplied_checks)
        and all(value is True for value in supplied_checks.values())
        and all(value is True for value in recomputed_checks.values())
    )
    supersedes = model.get("supersedes") if isinstance(model.get("supersedes"), dict) else {}
    producer = (
        model.get("debian_intent_producer")
        if isinstance(model.get("debian_intent_producer"), dict)
        else {}
    )
    identity = (
        producer.get("target_identity")
        if isinstance(producer.get("target_identity"), dict)
        else {}
    )
    producer_display = (
        producer.get("display_access")
        if isinstance(producer.get("display_access"), dict)
        else {}
    )
    producer_network = producer.get("network") if isinstance(producer.get("network"), dict) else {}
    producer_launcher = (
        producer.get("launcher_policy")
        if isinstance(producer.get("launcher_policy"), dict)
        else {}
    )
    presenter = model.get("presenter") if isinstance(model.get("presenter"), dict) else {}
    boundary = model.get("boundary") if isinstance(model.get("boundary"), dict) else {}
    intent = (
        boundary.get("intent_schema")
        if isinstance(boundary.get("intent_schema"), dict)
        else {}
    )
    parser = (
        boundary.get("parser_policy")
        if isinstance(boundary.get("parser_policy"), dict)
        else {}
    )
    atomic = intent.get("atomic_update") if isinstance(intent.get("atomic_update"), dict) else {}
    forbidden_fields = intent.get("forbidden_fields") if isinstance(intent.get("forbidden_fields"), list) else []
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    live_proven = bool(live_proof.get("native_presenter_live_proven"))
    handoff_proven = bool(handoff_proof.get("handoff_live_proven"))
    restart_proven = bool(restart_proof.get("restart_live_proven"))
    durable_restart_proven = handoff_proven and restart_proven
    intent_syscall_proven = bool(intent_syscall_proof.get("hud_intent_syscall_trace_live_proven"))
    any_live_proven = live_proven or handoff_proven or durable_restart_proven
    remaining_live_proofs = [
        "intent producer uid/gid/no-new-privs/cap-zero/no-drm/no-network",
        "presenter is sole DRM fd holder during HUD display",
        "presenter owns SETCRTC/PAGE_FLIP and releases DRM on cleanup",
        "intent parser rejects forbidden fields and stale updates",
    ]
    if durable_restart_proven and intent_syscall_proven:
        remaining_live_proofs = []
    elif durable_restart_proven:
        remaining_live_proofs = [
            "optional HUD syscall trace profile before seccomp enforcement",
        ]
    elif handoff_proven:
        remaining_live_proofs = [
            "presenter cleanup/restart policy for long-running appliance mode",
            "optional HUD syscall trace profile before seccomp enforcement",
        ]
    elif live_proven:
        remaining_live_proofs = [
            "durable native presenter service across Debian handoff",
            "fresh Debian-written intent consumed by native presenter during the same handoff",
            "presenter is sole DRM fd holder during Debian handoff",
            "presenter cleanup/restart policy for long-running appliance mode",
        ]
    return {
        "state": (
            DPUBLIC_HUD_INTENT_SYSCALL_TRACE_STATE
            if durable_restart_proven and intent_syscall_proven
            else DPUBLIC_HUD_PRESENTER_RESTART_STATE
            if durable_restart_proven
            else DPUBLIC_HUD_PRESENTER_HANDOFF_STATE
            if handoff_proven
            else DPUBLIC_HUD_PRESENTER_LIVE_STATE
            if live_proven
            else DPUBLIC_HUD_PRESENTER_MODEL_STATE if model_defined else "SUPPLIED_NOT_PROVEN"
        ),
        "decision": model_result.get("decision"),
        "proof_run_dir": model_result.get("run_dir"),
        "scope": "dpublic-hud-presenter-model",
        "model_defined": model_defined,
        "hud_live_proven": any_live_proven,
        "native_presenter_live_proven": any_live_proven,
        "handoff_live_proven": handoff_proven,
        "restart_live_proven": restart_proven,
        "durable_restart_live_proven": durable_restart_proven,
        "intent_syscall_trace_live_proven": intent_syscall_proven,
        "live_proof": live_proof,
        "handoff_proof": handoff_proof,
        "restart_proof": restart_proof,
        "intent_syscall_trace_proof": intent_syscall_proof,
        "supersedes_wsta127_direct_kms": supersedes.get("direct_nonroot_kms") == "rejected-for-live-path",
        "wsta129_boundary": supersedes.get("wsta129_live_boundary"),
        "display_architecture": "split-intent-native-presenter",
        "service": wsta130.SERVICE,
        "producer_user": identity.get("user"),
        "producer_uid": identity.get("uid"),
        "producer_gid": identity.get("gid"),
        "producer_no_drm_or_kms": bool(
            producer_display.get("opens_drm") is False
            and producer_display.get("kms_setcrtc_allowed") is False
            and producer_display.get("drm_fd_expected") is False
        ),
        "producer_no_network": bool(
            producer_network.get("opens_tcp_listener") is False
            and producer_network.get("opens_udp_socket") is False
            and producer_network.get("public_inbound_listener") is False
        ),
        "producer_launcher_required": producer_launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch",
        "producer_launcher_no_new_privs_required": producer_launcher.get("no_new_privs") is True,
        "producer_launcher_caps_zero_required": producer_launcher.get("effective_capabilities") == "zero",
        "presenter_owner": presenter.get("owner"),
        "presenter_privilege_model": presenter.get("privilege_model"),
        "presenter_kms_master_owner": presenter.get("kms_master_owner") is True,
        "drm_node": presenter.get("device_node"),
        "intent_transport": boundary.get("transport"),
        "intent_file": boundary.get("intent_file"),
        "intent_max_bytes": intent.get("max_bytes"),
        "intent_stale_after_ms": intent.get("stale_after_ms"),
        "intent_atomic_update": bool(
            atomic.get("operation") == "write-fsync-rename"
            and atomic.get("final_path") == wsta130.INTENT_FILE
        ),
        "intent_secret_fields_forbidden": all(
            name in forbidden_fields for name in ("url", "ssid", "psk", "token", "secret")
        ),
        "intent_parser_fail_closed": bool(
            parser.get("reject_unknown_fields") is True
            and parser.get("ignore_stale_intent") is True
            and parser.get("no_shell_expansion") is True
            and parser.get("no_path_open_from_intent") is True
            and parser.get("no_public_url_rendering") is True
        ),
        "default_public_off": exposure.get("public_default") == "off",
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "remaining_live_proofs": remaining_live_proofs,
    }


def launcher_proof_is_smoke_live_proven(launcher_proof: dict[str, Any]) -> bool:
    return bool(launcher_proof.get("smoke_live_proven"))


def packet_filter_proof_is_live_proven(packet_filter_proof: dict[str, Any]) -> bool:
    return bool(packet_filter_proof.get("loopback_live_proven"))


def syscall_trace_proof_is_smoke_live_proven(syscall_trace_proof: dict[str, Any]) -> bool:
    return bool(syscall_trace_proof.get("smoke_syscall_trace_live_proven"))


def dropbear_admin_proof_is_live_proven(dropbear_admin_proof: dict[str, Any]) -> bool:
    return bool(dropbear_admin_proof.get("dropbear_admin_live_proven"))


def cloudflared_model_is_defined(cloudflared_model: dict[str, Any]) -> bool:
    return bool(cloudflared_model.get("model_defined"))


def cloudflared_runtime_is_live_proven(cloudflared_runtime: dict[str, Any]) -> bool:
    return bool(cloudflared_runtime.get("cloudflared_live_proven"))


def hud_model_is_defined(hud_model: dict[str, Any]) -> bool:
    return bool(hud_model.get("model_defined"))


def refine_blocking_before_enforcement(
    items: list[Any],
    launcher_proof: dict[str, Any],
    packet_filter_proof: dict[str, Any],
    syscall_trace_proof: dict[str, Any],
    dropbear_admin_proof: dict[str, Any],
    dropbear_admin_syscall_proof: dict[str, Any],
    cloudflared_model: dict[str, Any],
    cloudflared_runtime: dict[str, Any],
) -> list[str]:
    refined: list[str] = []
    smoke_live_proven = launcher_proof_is_smoke_live_proven(launcher_proof)
    packet_filter_live_proven = packet_filter_proof_is_live_proven(packet_filter_proof)
    smoke_syscall_trace_live_proven = syscall_trace_proof_is_smoke_live_proven(syscall_trace_proof)
    dropbear_admin_live_proven = dropbear_admin_proof_is_live_proven(dropbear_admin_proof)
    dropbear_admin_syscall_live_proven = bool(
        dropbear_admin_syscall_proof.get("dropbear_admin_syscall_trace_live_proven")
    )
    cloudflared_model_defined = cloudflared_model_is_defined(cloudflared_model)
    cloudflared_runtime_live_proven = cloudflared_runtime_is_live_proven(cloudflared_runtime)
    for item in items:
        text = str(item)
        if smoke_live_proven and text in {
            "staged service users/groups not live-proven",
            "non-root users/groups not staged",
        }:
            proven = ["dpublic-smoke-httpd"]
            if dropbear_admin_live_proven:
                proven.append("dropbear-admin-usb")
            if cloudflared_runtime_live_proven:
                proven.append("cloudflared-quick-tunnel")
            text = f"remaining service users/groups not live-proven beyond {'/'.join(proven)}"
        elif smoke_live_proven and text == "no-new-privs launcher not live-proven":
            proven = ["dpublic-smoke-httpd"]
            if cloudflared_runtime_live_proven:
                proven.append("cloudflared-quick-tunnel")
            text = f"remaining service launchers not live-proven beyond {'/'.join(proven)}"
        elif packet_filter_live_proven and text == "packet-filter backend not inventoried":
            continue
        elif smoke_syscall_trace_live_proven and text == "syscall traces not captured":
            proven = ["dpublic-smoke-httpd"]
            if dropbear_admin_syscall_live_proven:
                proven.append("dropbear-admin-usb")
            if cloudflared_runtime_live_proven:
                proven.append("cloudflared-quick-tunnel")
            text = f"remaining syscall traces not captured beyond {'/'.join(proven)}"
        elif dropbear_admin_live_proven and text == "dropbear admin user model not finalized":
            continue
        elif (
            cloudflared_model_defined or cloudflared_runtime_live_proven
        ) and text == "cloudflared service model not finalized":
            continue
        if text not in refined:
            refined.append(text)
    return refined


def compact_hardening(
    manifest_result: dict[str, Any] | None,
    packet_filter_proof_result: dict[str, Any] | None,
    packet_filter_control_summary: dict[str, Any] | None,
    launcher_proof_result: dict[str, Any] | None,
    syscall_trace_proof_result: dict[str, Any] | None,
    dropbear_admin_proof_result: dict[str, Any] | None,
    dropbear_admin_syscall_proof_result: dict[str, Any] | None,
    cloudflared_model_result: dict[str, Any] | None,
    cloudflared_runtime_proof_result: dict[str, Any] | None,
    hud_model_result: dict[str, Any] | None,
    hud_presenter_model_result: dict[str, Any] | None,
    hud_presenter_live_proof_result: dict[str, Any] | None,
    hud_presenter_handoff_proof_result: dict[str, Any] | None,
    hud_presenter_restart_proof_result: dict[str, Any] | None,
    hud_intent_syscall_proof_result: dict[str, Any] | None,
) -> dict[str, Any]:
    packet_filter_proof = compact_packet_filter_proof(packet_filter_proof_result, packet_filter_control_summary)
    launcher_proof = compact_launcher_proof(launcher_proof_result)
    syscall_trace_proof = compact_syscall_trace_proof(syscall_trace_proof_result)
    dropbear_admin_proof = compact_dropbear_admin_proof(dropbear_admin_proof_result)
    dropbear_admin_syscall_proof = compact_dropbear_admin_syscall_trace_proof(
        dropbear_admin_syscall_proof_result
    )
    cloudflared_model = compact_cloudflared_model(cloudflared_model_result)
    cloudflared_runtime = compact_cloudflared_runtime_proof(cloudflared_runtime_proof_result)
    hud_model = compact_hud_model(hud_model_result)
    hud_presenter_model = compact_hud_presenter_model(
        hud_presenter_model_result,
        hud_presenter_live_proof_result,
        hud_presenter_handoff_proof_result,
        hud_presenter_restart_proof_result,
        hud_intent_syscall_proof_result,
    )
    hud_intent_syscall_live_proven = bool(hud_presenter_model.get("intent_syscall_trace_live_proven"))
    if hud_presenter_model.get("model_defined"):
        hud_model["superseded_by_presenter_model"] = True
        hud_model["superseded_reason"] = "wsta129-setcrtc-permission-denied"
    if dropbear_admin_proof.get("dropbear_admin_live_proven"):
        launcher_proof["remaining_profiles"] = [
            item
            for item in launcher_proof.get("remaining_profiles", [])
            if item != "dropbear-admin-usb"
        ]
    if dropbear_admin_syscall_proof.get("dropbear_admin_syscall_trace_live_proven"):
        syscall_trace_proof["remaining_profiles"] = [
            item
            for item in syscall_trace_proof.get("remaining_profiles", [])
            if item != "dropbear-admin-usb"
        ]
    if cloudflared_runtime.get("cloudflared_live_proven"):
        cloudflared_model["cloudflared_live_proven"] = True
        cloudflared_model["remaining_live_proofs"] = []
        launcher_proof["remaining_profiles"] = [
            item
            for item in launcher_proof.get("remaining_profiles", [])
            if item != "cloudflared-quick-tunnel"
        ]
        syscall_trace_proof["remaining_profiles"] = [
            item
            for item in syscall_trace_proof.get("remaining_profiles", [])
            if item != "cloudflared-quick-tunnel"
        ]
    if hud_intent_syscall_live_proven:
        syscall_trace_proof["remaining_profiles"] = [
            item
            for item in syscall_trace_proof.get("remaining_profiles", [])
            if item != "dpublic-hud"
        ]
    if not manifest_result:
        return {
            "state": "NOT_SUPPLIED",
            "service_count": 0,
            "global_policy": {},
            "blocking_before_enforcement": [],
            "packet_filter_proof": packet_filter_proof,
            "launcher_proof": launcher_proof,
            "syscall_trace_proof": syscall_trace_proof,
            "dropbear_admin_proof": dropbear_admin_proof,
            "dropbear_admin_syscall_trace_proof": dropbear_admin_syscall_proof,
            "cloudflared_model": cloudflared_model,
            "cloudflared_runtime": cloudflared_runtime,
            "hud_model": hud_model,
            "hud_presenter_model": hud_presenter_model,
        }
    manifest = manifest_result.get("manifest") if isinstance(manifest_result.get("manifest"), dict) else {}
    services = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    global_policy = manifest.get("global_policy") if isinstance(manifest.get("global_policy"), dict) else {}
    blocking_before_enforcement = refine_blocking_before_enforcement(
        list(manifest.get("blocking_before_enforcement") or []),
        launcher_proof,
        packet_filter_proof,
        syscall_trace_proof,
        dropbear_admin_proof,
        dropbear_admin_syscall_proof,
        cloudflared_model,
        cloudflared_runtime,
    )
    if not syscall_trace_proof.get("remaining_profiles"):
        blocking_before_enforcement = [
            item
            for item in blocking_before_enforcement
            if not str(item).startswith("remaining syscall traces not captured")
        ]
    return {
        "state": manifest.get("state"),
        "service_count": len([item for item in services if isinstance(item, dict)]),
        "global_policy": {
            "default_public_off": bool(global_policy.get("default_public_off")),
            "no_new_privs_default": bool(global_policy.get("no_new_privs_default")),
            "capability_drop_required": bool(global_policy.get("capability_drop_required")),
            "seccomp_ready_for_profile_source": bool(global_policy.get("seccomp_ready_for_profile_source")),
            "packet_filter_backend_required": bool(global_policy.get("packet_filter_backend_required")),
            "root_login_policy": global_policy.get("root_login_policy"),
        },
        "blocking_before_enforcement": blocking_before_enforcement,
        "packet_filter_proof": packet_filter_proof,
        "launcher_proof": launcher_proof,
        "syscall_trace_proof": syscall_trace_proof,
        "dropbear_admin_proof": dropbear_admin_proof,
        "dropbear_admin_syscall_trace_proof": dropbear_admin_syscall_proof,
        "cloudflared_model": cloudflared_model,
        "cloudflared_runtime": cloudflared_runtime,
        "hud_model": hud_model,
        "hud_presenter_model": hud_presenter_model,
    }


def exposure_state(status_hud: dict[str, Any], wsta88_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "public_state": status_hud.get("public_state") or "PUBLIC_OFF",
        "default_public_off": bool(status_hud.get("default_public_off", True)),
        "live_execution_requested": bool(status_hud.get("live_execution_requested")),
        "wsta88_decision": wsta88_result.get("decision"),
        "wsta80_preflight_decision": status_hud.get("wsta80_preflight_decision"),
        "wsta80_live_decision": status_hud.get("wsta80_live_decision"),
    }


def build_server_status(
    wsta88_result: dict[str, Any],
    hardening_result: dict[str, Any] | None,
    packet_filter_proof_result: dict[str, Any] | None,
    packet_filter_control_summary: dict[str, Any] | None,
    launcher_proof_result: dict[str, Any] | None,
    syscall_trace_proof_result: dict[str, Any] | None,
    dropbear_admin_proof_result: dict[str, Any] | None,
    dropbear_admin_syscall_proof_result: dict[str, Any] | None,
    cloudflared_model_result: dict[str, Any] | None,
    cloudflared_runtime_proof_result: dict[str, Any] | None,
    hud_model_result: dict[str, Any] | None,
    hud_presenter_model_result: dict[str, Any] | None,
    hud_presenter_live_proof_result: dict[str, Any] | None,
    hud_presenter_handoff_proof_result: dict[str, Any] | None,
    hud_presenter_restart_proof_result: dict[str, Any] | None,
    hud_intent_syscall_proof_result: dict[str, Any] | None,
) -> dict[str, Any]:
    status_hud = wsta88_result.get("status_hud") if isinstance(wsta88_result.get("status_hud"), dict) else {}
    if not status_hud:
        workflow = wsta88_result.get("workflow") if isinstance(wsta88_result.get("workflow"), dict) else {}
        status_hud = workflow.get("status_hud") if isinstance(workflow.get("status_hud"), dict) else {}
    packet_filter = status_hud.get("packet_filter") if isinstance(status_hud.get("packet_filter"), dict) else {}
    hardening = compact_hardening(
        hardening_result,
        packet_filter_proof_result,
        packet_filter_control_summary,
        launcher_proof_result,
        syscall_trace_proof_result,
        dropbear_admin_proof_result,
        dropbear_admin_syscall_proof_result,
        cloudflared_model_result,
        cloudflared_runtime_proof_result,
        hud_model_result,
        hud_presenter_model_result,
        hud_presenter_live_proof_result,
        hud_presenter_handoff_proof_result,
        hud_presenter_restart_proof_result,
        hud_intent_syscall_proof_result,
    )
    public_off = (status_hud.get("public_state") or "PUBLIC_OFF") == "PUBLIC_OFF"
    ready_default_off = public_off and bool(packet_filter.get("ready"))
    syscall_trace_proof = (
        hardening.get("syscall_trace_proof")
        if isinstance(hardening.get("syscall_trace_proof"), dict)
        else {}
    )
    dropbear_admin_proof = (
        hardening.get("dropbear_admin_proof")
        if isinstance(hardening.get("dropbear_admin_proof"), dict)
        else {}
    )
    dropbear_admin_syscall_proof = (
        hardening.get("dropbear_admin_syscall_trace_proof")
        if isinstance(hardening.get("dropbear_admin_syscall_trace_proof"), dict)
        else {}
    )
    cloudflared_model = (
        hardening.get("cloudflared_model")
        if isinstance(hardening.get("cloudflared_model"), dict)
        else {}
    )
    cloudflared_runtime = (
        hardening.get("cloudflared_runtime")
        if isinstance(hardening.get("cloudflared_runtime"), dict)
        else {}
    )
    hud_model = (
        hardening.get("hud_model")
        if isinstance(hardening.get("hud_model"), dict)
        else {}
    )
    hud_presenter_model = (
        hardening.get("hud_presenter_model")
        if isinstance(hardening.get("hud_presenter_model"), dict)
        else {}
    )
    hud_presenter_live = (
        hud_presenter_model.get("live_proof")
        if isinstance(hud_presenter_model.get("live_proof"), dict)
        else {}
    )
    hud_presenter_handoff = (
        hud_presenter_model.get("handoff_proof")
        if isinstance(hud_presenter_model.get("handoff_proof"), dict)
        else {}
    )
    hud_presenter_restart = (
        hud_presenter_model.get("restart_proof")
        if isinstance(hud_presenter_model.get("restart_proof"), dict)
        else {}
    )
    hud_intent_syscall = (
        hud_presenter_model.get("intent_syscall_trace_proof")
        if isinstance(hud_presenter_model.get("intent_syscall_trace_proof"), dict)
        else {}
    )
    hud_live_proven = bool(
        hud_model.get("hud_live_proven") or hud_presenter_model.get("hud_live_proven")
    )
    operator_next_actions = [
        "keep-public-exposure-default-off",
        "use-explicit-wsta88-live-gate-only-when-attended",
        "extend-service-launcher-proof-beyond-dpublic-smoke-httpd-before-always-on-profile",
    ]
    if not dropbear_admin_proof.get("dropbear_admin_live_proven"):
        operator_next_actions.append("prove-dropbear-admin-nonroot-login-before-always-on-profile")
    if not cloudflared_model.get("model_defined"):
        operator_next_actions.append("define-cloudflared-service-model-before-public-profile")
    elif not cloudflared_runtime.get("cloudflared_live_proven"):
        operator_next_actions.append("prove-cloudflared-runtime-through-launcher-before-public-profile")
    if hud_presenter_model.get("durable_restart_live_proven"):
        if hud_intent_syscall.get("hud_intent_syscall_trace_live_proven"):
            operator_next_actions.append("continue-containment-hardening-or-derive-hud-seccomp-policy")
        else:
            operator_next_actions.append("profile-dpublic-hud-syscalls-or-continue-containment-hardening")
    elif hud_presenter_model.get("handoff_live_proven"):
        operator_next_actions.append("continue-dpublic-service-integration-or-containment-hardening")
    elif hud_presenter_model.get("native_presenter_live_proven"):
        operator_next_actions.append("design-durable-dpublic-hud-presenter-service-across-debian-handoff")
    elif hud_presenter_model.get("model_defined"):
        operator_next_actions.append("prototype-dpublic-hud-intent-presenter-boundary-before-live-hud-profile")
    elif hud_model.get("model_defined"):
        operator_next_actions.append("replace-direct-kms-hud-with-presenter-model-before-live-hud-profile")
    else:
        operator_next_actions.append("define-dpublic-hud-service-model-before-hud-live-proof")
    if syscall_trace_proof.get("smoke_syscall_trace_live_proven"):
        if syscall_trace_proof.get("remaining_profiles"):
            operator_next_actions.append(
                "extend-syscall-trace-proof-beyond-dpublic-smoke-httpd-before-seccomp-enforcement"
            )
        else:
            operator_next_actions.append("derive-seccomp-policy-from-live-syscall-baselines")
    else:
        operator_next_actions.append("trace-service-syscalls-before-seccomp-enforcement")
    return {
        "state": "SERVER_PROFILE_READY_DEFAULT_OFF" if ready_default_off else "SERVER_PROFILE_NOT_READY",
        "exposure": exposure_state(status_hud, wsta88_result),
        "network_model": {
            "wifi_owner": "native-init",
            "debian_role": "service-surface-consumer",
            "handoff_required_for_wsta88": False,
            "credential_scope": "native-owned-explicit-live-gate",
        },
        "debian_service_surface": {
            "mode": "chroot-or-appliance-service-surface",
            "switch_root_required": False,
            "default_public_off": True,
            "server_hud_ready_surface": "wsta88-status-hud",
        },
        "lease": status_hud.get("lease") if isinstance(status_hud.get("lease"), dict) else {},
        "packet_filter": packet_filter,
        "image_prep": status_hud.get("image_prep") if isinstance(status_hud.get("image_prep"), dict) else {},
        "manual_stop": status_hud.get("manual_stop") if isinstance(status_hud.get("manual_stop"), dict) else {},
        "hardening": hardening,
        "operator_next_actions": operator_next_actions,
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }


def markdown(server_status: dict[str, Any]) -> str:
    exposure = server_status.get("exposure") if isinstance(server_status.get("exposure"), dict) else {}
    network = server_status.get("network_model") if isinstance(server_status.get("network_model"), dict) else {}
    packet_filter = (
        server_status.get("packet_filter")
        if isinstance(server_status.get("packet_filter"), dict)
        else {}
    )
    lease = server_status.get("lease") if isinstance(server_status.get("lease"), dict) else {}
    hardening = server_status.get("hardening") if isinstance(server_status.get("hardening"), dict) else {}
    hardening_policy = (
        hardening.get("global_policy")
        if isinstance(hardening.get("global_policy"), dict)
        else {}
    )
    launcher_proof = (
        hardening.get("launcher_proof")
        if isinstance(hardening.get("launcher_proof"), dict)
        else {}
    )
    packet_filter_proof = (
        hardening.get("packet_filter_proof")
        if isinstance(hardening.get("packet_filter_proof"), dict)
        else {}
    )
    packet_filter_control_proof = (
        packet_filter_proof.get("control_proof")
        if isinstance(packet_filter_proof.get("control_proof"), dict)
        else {}
    )
    syscall_trace_proof = (
        hardening.get("syscall_trace_proof")
        if isinstance(hardening.get("syscall_trace_proof"), dict)
        else {}
    )
    dropbear_admin_proof = (
        hardening.get("dropbear_admin_proof")
        if isinstance(hardening.get("dropbear_admin_proof"), dict)
        else {}
    )
    dropbear_admin_syscall = (
        hardening.get("dropbear_admin_syscall_trace_proof")
        if isinstance(hardening.get("dropbear_admin_syscall_trace_proof"), dict)
        else {}
    )
    cloudflared_model = (
        hardening.get("cloudflared_model")
        if isinstance(hardening.get("cloudflared_model"), dict)
        else {}
    )
    cloudflared_runtime = (
        hardening.get("cloudflared_runtime")
        if isinstance(hardening.get("cloudflared_runtime"), dict)
        else {}
    )
    hud_model = (
        hardening.get("hud_model")
        if isinstance(hardening.get("hud_model"), dict)
        else {}
    )
    hud_presenter_model = (
        hardening.get("hud_presenter_model")
        if isinstance(hardening.get("hud_presenter_model"), dict)
        else {}
    )
    hud_presenter_live = (
        hud_presenter_model.get("live_proof")
        if isinstance(hud_presenter_model.get("live_proof"), dict)
        else {}
    )
    hud_presenter_handoff = (
        hud_presenter_model.get("handoff_proof")
        if isinstance(hud_presenter_model.get("handoff_proof"), dict)
        else {}
    )
    hud_presenter_restart = (
        hud_presenter_model.get("restart_proof")
        if isinstance(hud_presenter_model.get("restart_proof"), dict)
        else {}
    )
    hud_intent_syscall = (
        hud_presenter_model.get("intent_syscall_trace_proof")
        if isinstance(hud_presenter_model.get("intent_syscall_trace_proof"), dict)
        else {}
    )
    hud_live_proven = bool(
        hud_model.get("hud_live_proven") or hud_presenter_model.get("hud_live_proven")
    )
    lines = [
        "# WSTA Operator Server Status",
        "",
        f"- State: `{server_status.get('state')}`",
        f"- Public state: `{exposure.get('public_state')}`",
        f"- Live execution requested: `{str(bool(exposure.get('live_execution_requested'))).lower()}`",
        f"- Wi-Fi owner: `{network.get('wifi_owner')}`",
        f"- Debian role: `{network.get('debian_role')}`",
        f"- Switch-root required for WSTA88: `{str(bool(network.get('handoff_required_for_wsta88'))).lower()}`",
        "",
        "## Exposure Gate",
        "",
        f"- WSTA88 decision: `{exposure.get('wsta88_decision')}`",
        f"- WSTA80 preflight: `{exposure.get('wsta80_preflight_decision')}`",
        f"- WSTA80 live: `{exposure.get('wsta80_live_decision')}`",
        f"- Lease TTL: `{lease.get('ttl_sec')}`",
        f"- Initial seconds remaining: `{lease.get('initial_seconds_remaining')}`",
        "",
        "## Packet Filter",
        "",
        f"- State: `{packet_filter.get('state')}`",
        f"- Ready: `{str(bool(packet_filter.get('ready'))).lower()}`",
        f"- Backend: `{packet_filter.get('backend')}`",
        f"- Policy: `{packet_filter.get('policy')}`",
        f"- Loopback default-drop proof: `{str(bool(packet_filter_proof.get('loopback_live_proven'))).lower()}`",
        f"- Control plane proof: `{str(bool(packet_filter_control_proof.get('control_plane_live_proven'))).lower()}`",
        f"- Restore exact: `{str(bool(packet_filter_proof.get('restore_exact'))).lower()}`",
        "",
        "## Hardening",
        "",
        f"- State: `{hardening.get('state')}`",
        f"- Service count: `{hardening.get('service_count')}`",
        f"- No-new-privs default: `{str(bool(hardening_policy.get('no_new_privs_default'))).lower()}`",
        f"- Capability drop required: `{str(bool(hardening_policy.get('capability_drop_required'))).lower()}`",
        f"- Seccomp ready for profile source: `{str(bool(hardening_policy.get('seccomp_ready_for_profile_source'))).lower()}`",
        f"- Smoke launcher proof: `{str(bool(launcher_proof.get('smoke_live_proven'))).lower()}`",
        f"- Smoke launcher user: `{launcher_proof.get('user')}`",
        f"- Smoke launcher caps zero: `{str(bool(launcher_proof.get('cap_eff_zero'))).lower()}`",
        f"- Smoke syscall trace proof: `{str(bool(syscall_trace_proof.get('smoke_syscall_trace_live_proven'))).lower()}`",
        f"- Smoke syscall count: `{syscall_trace_proof.get('syscall_count')}`",
        f"- Dropbear admin proof: `{str(bool(dropbear_admin_proof.get('dropbear_admin_live_proven'))).lower()}`",
        f"- Dropbear admin user: `{dropbear_admin_proof.get('user')}`",
        f"- Dropbear root SSH rejected: `{str(bool(dropbear_admin_proof.get('root_ssh_rejected'))).lower()}`",
        f"- Dropbear admin syscall proof: `{str(bool(dropbear_admin_syscall.get('dropbear_admin_syscall_trace_live_proven'))).lower()}`",
        f"- Dropbear admin syscall count: `{dropbear_admin_syscall.get('syscall_count')}`",
        f"- Dropbear admin syscall accept observed: `{str(bool(dropbear_admin_syscall.get('accept_observed'))).lower()}`",
        f"- Cloudflared model: `{str(bool(cloudflared_model.get('model_defined'))).lower()}`",
        f"- Cloudflared model user: `{cloudflared_model.get('user')}`",
        f"- Cloudflared default public off: `{str(bool(cloudflared_model.get('default_public_off'))).lower()}`",
        f"- Cloudflared launcher hardening required: `{str(bool(cloudflared_model.get('launcher_no_new_privs_required') and cloudflared_model.get('launcher_caps_zero_required'))).lower()}`",
        f"- Cloudflared runtime proof: `{str(bool(cloudflared_runtime.get('cloudflared_live_proven'))).lower()}`",
        f"- Cloudflared runtime user: `{cloudflared_runtime.get('user')}`",
        f"- Cloudflared runtime outbound-only: `{str(bool(cloudflared_runtime.get('outbound_only'))).lower()}`",
        f"- Cloudflared runtime private URL artifact: `{str(bool(cloudflared_runtime.get('private_url_artifact'))).lower()}`",
        f"- Cloudflared runtime syscall count: `{cloudflared_runtime.get('syscall_count')}`",
        f"- D-public HUD model: `{str(bool(hud_model.get('model_defined'))).lower()}`",
        f"- D-public HUD user: `{hud_model.get('user')}`",
        f"- D-public HUD no-network: `{str(bool(hud_model.get('no_network_listener'))).lower()}`",
        f"- D-public HUD DRM node policy: `{str(bool(hud_model.get('drm_node_policy_defined'))).lower()}`",
        f"- D-public HUD direct KMS superseded: `{str(bool(hud_model.get('superseded_by_presenter_model'))).lower()}`",
        f"- D-public HUD presenter model: `{str(bool(hud_presenter_model.get('model_defined'))).lower()}`",
        f"- D-public HUD display architecture: `{hud_presenter_model.get('display_architecture')}`",
        f"- D-public HUD intent producer no DRM: `{str(bool(hud_presenter_model.get('producer_no_drm_or_kms'))).lower()}`",
        f"- D-public HUD presenter owner: `{hud_presenter_model.get('presenter_owner')}`",
        f"- D-public HUD intent file: `{hud_presenter_model.get('intent_file')}`",
        f"- D-public HUD live proof: `{str(hud_live_proven).lower()}`",
        f"- D-public HUD native presenter live proof: `{str(bool(hud_presenter_model.get('native_presenter_live_proven'))).lower()}`",
        f"- D-public HUD presenter checked flash: `{str(bool(hud_presenter_live.get('checked_flash_sha_matched') and hud_presenter_live.get('checked_flash_boot_health_clean'))).lower()}`",
        f"- D-public HUD presenter KMS present: `{str(bool(hud_presenter_live.get('present_done'))).lower()}`",
        f"- D-public HUD presenter reject paths: `{str(bool(hud_presenter_live.get('reject_forbidden_command') and hud_presenter_live.get('reject_stale_intent'))).lower()}`",
        f"- D-public HUD handoff proof: `{str(bool(hud_presenter_model.get('handoff_live_proven'))).lower()}`",
        f"- D-public HUD shared run bind: `{str(bool(hud_presenter_handoff.get('handoff_shared_run_bind_ok') and hud_presenter_handoff.get('shared_run_same_mount_after_handoff'))).lower()}`",
        f"- D-public HUD Debian intent consumed: `{str(bool(hud_presenter_handoff.get('fresh_debian_intent_consumed'))).lower()}`",
        f"- D-public HUD handoff sole DRM owner: `{str(bool(hud_presenter_handoff.get('presenter_sole_drm_owner_after_handoff'))).lower()}`",
        f"- D-public HUD restart proof: `{str(bool(hud_presenter_model.get('restart_live_proven'))).lower()}`",
        f"- D-public HUD restart stop/start: `{str(bool(hud_presenter_restart.get('restart_done') and hud_presenter_restart.get('restart_stop_rc') == 0 and hud_presenter_restart.get('restart_start_rc') == 0)).lower()}`",
        f"- D-public HUD restart post-present: `{str(bool(hud_presenter_restart.get('post_restart_sequence') == wsta147.POST_RESTART_SEQUENCE and hud_presenter_restart.get('post_restart_present_rc') == 0 and hud_presenter_restart.get('post_restart_drm_fd'))).lower()}`",
        f"- D-public HUD stale pid cleanup: `{str(bool(hud_presenter_restart.get('stale_pid_cleanup_marker') and hud_presenter_restart.get('final_status_stopped'))).lower()}`",
        f"- D-public HUD intent syscall proof: `{str(bool(hud_intent_syscall.get('hud_intent_syscall_trace_live_proven'))).lower()}`",
        f"- D-public HUD intent syscall count: `{hud_intent_syscall.get('syscall_count')}`",
        f"- D-public HUD intent syscall no-network: `{str(bool(hud_intent_syscall.get('network_syscalls_absent'))).lower()}`",
        f"- D-public HUD intent syscall no-DRM: `{str(bool(hud_intent_syscall.get('ioctl_syscall_absent') and hud_intent_syscall.get('drm_trace_absent'))).lower()}`",
        f"- Remaining launcher profiles: `{', '.join(launcher_proof.get('remaining_profiles') or [])}`",
        f"- Remaining syscall profiles: `{', '.join(syscall_trace_proof.get('remaining_profiles') or [])}`",
        "",
        "## Operator Next Actions",
        "",
    ]
    for item in server_status.get("operator_next_actions", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta108-operator-server-status-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA108 host-only operator server status bundle",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta108-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta108-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta108_operator_server_status.json"
    out_md = run_dir / "wsta108_operator_server_status.md"

    if not args.emit_server_status:
        result["decision"] = "wsta108-blocked-emit-server-status-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    wsta88_path, path_error = require_private_file(args.wsta88_operator_workflow_json, "wsta88-workflow")
    if path_error or wsta88_path is None:
        result["decision"] = path_error or "wsta108-blocked-wsta88-workflow"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    wsta88_result = load_json(wsta88_path)
    if wsta88_result.get("decision") not in {wsta88.PREFLIGHT_DECISION, wsta88.PASS_DECISION}:
        result["decision"] = "wsta108-blocked-wsta88-workflow-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    hardening_result: dict[str, Any] | None = None
    if args.wsta90_service_hardening_manifest_json is not None:
        hardening_path, hardening_error = require_private_file(
            args.wsta90_service_hardening_manifest_json,
            "wsta90-manifest",
        )
        if hardening_error or hardening_path is None:
            result["decision"] = hardening_error or "wsta108-blocked-wsta90-manifest"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hardening_result = load_json(hardening_path)
        if hardening_result.get("decision") != wsta90.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta90-manifest-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    packet_filter_proof_result: dict[str, Any] | None = None
    if args.wsta94_packet_filter_proof_json is not None:
        packet_filter_proof_path, packet_filter_proof_error = require_private_file(
            args.wsta94_packet_filter_proof_json,
            "wsta94-packet-filter-proof",
        )
        if packet_filter_proof_error or packet_filter_proof_path is None:
            result["decision"] = packet_filter_proof_error or "wsta108-blocked-wsta94-packet-filter-proof"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        packet_filter_proof_result = load_json(packet_filter_proof_path)
        if packet_filter_proof_result.get("decision") != wsta94.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta94-packet-filter-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    packet_filter_control_summary: dict[str, Any] | None = None
    if args.packet_filter_control_summary_json is not None:
        packet_filter_control_path, packet_filter_control_error = require_private_file(
            args.packet_filter_control_summary_json,
            "packet-filter-control-summary",
        )
        if packet_filter_control_error or packet_filter_control_path is None:
            result["decision"] = packet_filter_control_error or "wsta108-blocked-packet-filter-control-summary"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        packet_filter_control_summary = load_json(packet_filter_control_path)

    launcher_proof_result: dict[str, Any] | None = None
    if args.wsta110_service_launcher_proof_json is not None:
        launcher_proof_path, launcher_proof_error = require_private_file(
            args.wsta110_service_launcher_proof_json,
            "wsta110-launcher-proof",
        )
        if launcher_proof_error or launcher_proof_path is None:
            result["decision"] = launcher_proof_error or "wsta108-blocked-wsta110-launcher-proof"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        launcher_proof_result = load_json(launcher_proof_path)
        if launcher_proof_result.get("decision") != wsta110.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta110-launcher-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    syscall_trace_proof_result: dict[str, Any] | None = None
    if args.wsta114_syscall_trace_proof_json is not None:
        syscall_trace_proof_path, syscall_trace_proof_error = require_private_file(
            args.wsta114_syscall_trace_proof_json,
            "wsta114-syscall-trace-proof",
        )
        if syscall_trace_proof_error or syscall_trace_proof_path is None:
            result["decision"] = syscall_trace_proof_error or "wsta108-blocked-wsta114-syscall-trace-proof"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        syscall_trace_proof_result = load_json(syscall_trace_proof_path)
        if syscall_trace_proof_result.get("decision") != wsta114.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta114-syscall-trace-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    dropbear_admin_proof_result: dict[str, Any] | None = None
    if args.wsta120_dropbear_admin_proof_json is not None:
        dropbear_admin_proof_path, dropbear_admin_proof_error = require_private_file(
            args.wsta120_dropbear_admin_proof_json,
            "wsta120-dropbear-admin-proof",
        )
        if dropbear_admin_proof_error or dropbear_admin_proof_path is None:
            result["decision"] = dropbear_admin_proof_error or "wsta108-blocked-wsta120-dropbear-admin-proof"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        dropbear_admin_proof_result = load_json(dropbear_admin_proof_path)
        if dropbear_admin_proof_result.get("decision") != wsta120.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta120-dropbear-admin-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    dropbear_admin_syscall_proof_result: dict[str, Any] | None = None
    if args.wsta151_dropbear_admin_syscall_proof_json is not None:
        dropbear_admin_syscall_path, dropbear_admin_syscall_error = require_private_file(
            args.wsta151_dropbear_admin_syscall_proof_json,
            "wsta151-dropbear-admin-syscall-proof",
        )
        if dropbear_admin_syscall_error or dropbear_admin_syscall_path is None:
            result["decision"] = (
                dropbear_admin_syscall_error or "wsta108-blocked-wsta151-dropbear-admin-syscall-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        dropbear_admin_syscall_proof_result = load_json(dropbear_admin_syscall_path)
        if dropbear_admin_syscall_proof_result.get("decision") != wsta151.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta151-dropbear-admin-syscall-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    cloudflared_model_result: dict[str, Any] | None = None
    if args.wsta122_cloudflared_model_json is not None:
        cloudflared_model_path, cloudflared_model_error = require_private_file(
            args.wsta122_cloudflared_model_json,
            "wsta122-cloudflared-model",
        )
        if cloudflared_model_error or cloudflared_model_path is None:
            result["decision"] = cloudflared_model_error or "wsta108-blocked-wsta122-cloudflared-model"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        cloudflared_model_result = load_json(cloudflared_model_path)
        if cloudflared_model_result.get("decision") != wsta122.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta122-cloudflared-model-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    cloudflared_runtime_proof_result: dict[str, Any] | None = None
    if args.wsta125_cloudflared_runtime_proof_json is not None:
        cloudflared_runtime_path, cloudflared_runtime_error = require_private_file(
            args.wsta125_cloudflared_runtime_proof_json,
            "wsta125-cloudflared-runtime-proof",
        )
        if cloudflared_runtime_error or cloudflared_runtime_path is None:
            result["decision"] = (
                cloudflared_runtime_error or "wsta108-blocked-wsta125-cloudflared-runtime-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        cloudflared_runtime_proof_result = load_json(cloudflared_runtime_path)
        if cloudflared_runtime_proof_result.get("decision") != wsta125.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta125-cloudflared-runtime-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_model_result: dict[str, Any] | None = None
    if args.wsta127_hud_model_json is not None:
        hud_model_path, hud_model_error = require_private_file(
            args.wsta127_hud_model_json,
            "wsta127-hud-model",
        )
        if hud_model_error or hud_model_path is None:
            result["decision"] = hud_model_error or "wsta108-blocked-wsta127-hud-model"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_model_result = load_json(hud_model_path)
        if hud_model_result.get("decision") != wsta127.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta127-hud-model-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_presenter_model_result: dict[str, Any] | None = None
    if args.wsta130_hud_presenter_model_json is not None:
        hud_presenter_model_path, hud_presenter_model_error = require_private_file(
            args.wsta130_hud_presenter_model_json,
            "wsta130-hud-presenter-model",
        )
        if hud_presenter_model_error or hud_presenter_model_path is None:
            result["decision"] = (
                hud_presenter_model_error or "wsta108-blocked-wsta130-hud-presenter-model"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_presenter_model_result = load_json(hud_presenter_model_path)
        if hud_presenter_model_result.get("decision") != wsta130.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta130-hud-presenter-model-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_presenter_live_proof_result: dict[str, Any] | None = None
    if args.wsta137_hud_presenter_live_proof_json is not None:
        hud_presenter_live_path, hud_presenter_live_error = require_private_file(
            args.wsta137_hud_presenter_live_proof_json,
            "wsta137-hud-presenter-live-proof",
        )
        if hud_presenter_live_error or hud_presenter_live_path is None:
            result["decision"] = (
                hud_presenter_live_error or "wsta108-blocked-wsta137-hud-presenter-live-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_presenter_live_proof_result = load_json(hud_presenter_live_path)
        if hud_presenter_live_proof_result.get("decision") != wsta137.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta137-hud-presenter-live-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_presenter_handoff_proof_result: dict[str, Any] | None = None
    if args.wsta144_hud_presenter_handoff_proof_json is not None:
        hud_presenter_handoff_path, hud_presenter_handoff_error = require_private_file(
            args.wsta144_hud_presenter_handoff_proof_json,
            "wsta144-hud-presenter-handoff-proof",
        )
        if hud_presenter_handoff_error or hud_presenter_handoff_path is None:
            result["decision"] = (
                hud_presenter_handoff_error or "wsta108-blocked-wsta144-hud-presenter-handoff-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_presenter_handoff_proof_result = load_json(hud_presenter_handoff_path)
        if hud_presenter_handoff_proof_result.get("decision") != wsta144.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta144-hud-presenter-handoff-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_presenter_restart_proof_result: dict[str, Any] | None = None
    if args.wsta147_hud_presenter_restart_proof_json is not None:
        hud_presenter_restart_path, hud_presenter_restart_error = require_private_file(
            args.wsta147_hud_presenter_restart_proof_json,
            "wsta147-hud-presenter-restart-proof",
        )
        if hud_presenter_restart_error or hud_presenter_restart_path is None:
            result["decision"] = (
                hud_presenter_restart_error or "wsta108-blocked-wsta147-hud-presenter-restart-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_presenter_restart_proof_result = load_json(hud_presenter_restart_path)
        if hud_presenter_restart_proof_result.get("decision") != wsta147.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta147-hud-presenter-restart-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    hud_intent_syscall_proof_result: dict[str, Any] | None = None
    if args.wsta149_hud_intent_syscall_proof_json is not None:
        hud_intent_syscall_path, hud_intent_syscall_error = require_private_file(
            args.wsta149_hud_intent_syscall_proof_json,
            "wsta149-hud-intent-syscall-proof",
        )
        if hud_intent_syscall_error or hud_intent_syscall_path is None:
            result["decision"] = (
                hud_intent_syscall_error or "wsta108-blocked-wsta149-hud-intent-syscall-proof"
            )
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result
        hud_intent_syscall_proof_result = load_json(hud_intent_syscall_path)
        if hud_intent_syscall_proof_result.get("decision") != wsta149.PASS_DECISION:
            result["decision"] = "wsta108-blocked-wsta149-hud-intent-syscall-proof-not-pass"
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    server_status = build_server_status(
        wsta88_result,
        hardening_result,
        packet_filter_proof_result,
        packet_filter_control_summary,
        launcher_proof_result,
        syscall_trace_proof_result,
        dropbear_admin_proof_result,
        dropbear_admin_syscall_proof_result,
        cloudflared_model_result,
        cloudflared_runtime_proof_result,
        hud_model_result,
        hud_presenter_model_result,
        hud_presenter_live_proof_result,
        hud_presenter_handoff_proof_result,
        hud_presenter_restart_proof_result,
        hud_intent_syscall_proof_result,
    )
    packet_filter_proof = server_status["hardening"].get("packet_filter_proof", {})
    packet_filter_control_proof = (
        packet_filter_proof.get("control_proof")
        if isinstance(packet_filter_proof.get("control_proof"), dict)
        else {}
    )
    launcher_proof = server_status["hardening"].get("launcher_proof", {})
    syscall_trace_proof = server_status["hardening"].get("syscall_trace_proof", {})
    dropbear_admin_proof = server_status["hardening"].get("dropbear_admin_proof", {})
    dropbear_admin_syscall_proof = server_status["hardening"].get(
        "dropbear_admin_syscall_trace_proof",
        {},
    )
    cloudflared_model = server_status["hardening"].get("cloudflared_model", {})
    cloudflared_runtime = server_status["hardening"].get("cloudflared_runtime", {})
    hud_model = server_status["hardening"].get("hud_model", {})
    hud_presenter_model = server_status["hardening"].get("hud_presenter_model", {})
    hud_presenter_live = (
        hud_presenter_model.get("live_proof")
        if isinstance(hud_presenter_model.get("live_proof"), dict)
        else {}
    )
    hud_presenter_handoff = (
        hud_presenter_model.get("handoff_proof")
        if isinstance(hud_presenter_model.get("handoff_proof"), dict)
        else {}
    )
    hud_presenter_restart = (
        hud_presenter_model.get("restart_proof")
        if isinstance(hud_presenter_model.get("restart_proof"), dict)
        else {}
    )
    hud_intent_syscall = (
        hud_presenter_model.get("intent_syscall_trace_proof")
        if isinstance(hud_presenter_model.get("intent_syscall_trace_proof"), dict)
        else {}
    )
    result["server_status"] = server_status
    result["checks"] = {
        "wsta88_workflow_pass": True,
        "status_hud_present": bool(server_status.get("exposure")),
        "public_state_off": server_status["exposure"].get("public_state") == "PUBLIC_OFF",
        "packet_filter_ready": bool(server_status["packet_filter"].get("ready")),
        "hardening_manifest_supplied": hardening_result is not None,
        "packet_filter_proof_supplied": packet_filter_proof_result is not None,
        "packet_filter_loopback_live_proven": bool(packet_filter_proof.get("loopback_live_proven")),
        "packet_filter_control_summary_supplied": packet_filter_control_summary is not None,
        "packet_filter_control_plane_live_proven": bool(
            packet_filter_control_proof.get("control_plane_live_proven")
        ),
        "service_launcher_proof_supplied": launcher_proof_result is not None,
        "service_launcher_smoke_live_proven": bool(launcher_proof.get("smoke_live_proven")),
        "syscall_trace_proof_supplied": syscall_trace_proof_result is not None,
        "smoke_syscall_trace_live_proven": bool(
            syscall_trace_proof.get("smoke_syscall_trace_live_proven")
        ),
        "dropbear_admin_proof_supplied": dropbear_admin_proof_result is not None,
        "dropbear_admin_live_proven": bool(
            dropbear_admin_proof.get("dropbear_admin_live_proven")
        ),
        "dropbear_admin_syscall_proof_supplied": dropbear_admin_syscall_proof_result is not None,
        "dropbear_admin_syscall_trace_live_proven": bool(
            dropbear_admin_syscall_proof.get("dropbear_admin_syscall_trace_live_proven")
        ),
        "dropbear_admin_syscall_accept_observed": bool(
            dropbear_admin_syscall_proof.get("accept_observed")
        ),
        "dropbear_admin_syscall_trace_artifacts_saved": bool(
            dropbear_admin_syscall_proof.get("trace_artifacts_saved")
        ),
        "cloudflared_model_supplied": cloudflared_model_result is not None,
        "cloudflared_model_defined": bool(cloudflared_model.get("model_defined")),
        "cloudflared_default_public_off": bool(cloudflared_model.get("default_public_off")),
        "cloudflared_launcher_hardening_required": bool(
            cloudflared_model.get("launcher_no_new_privs_required")
            and cloudflared_model.get("launcher_caps_zero_required")
        ),
        "cloudflared_runtime_proof_supplied": cloudflared_runtime_proof_result is not None,
        "cloudflared_runtime_live_proven": bool(cloudflared_runtime.get("cloudflared_live_proven")),
        "cloudflared_runtime_private_url_redacted": bool(
            cloudflared_runtime.get("private_url_redacted")
        ),
        "cloudflared_runtime_trace_artifacts_saved": bool(
            cloudflared_runtime.get("trace_artifacts_saved")
        ),
        "cloudflared_runtime_cleanup_ok": bool(cloudflared_runtime.get("runtime_cleanup_ok")),
        "cloudflared_live_proven": bool(cloudflared_runtime.get("cloudflared_live_proven")),
        "hud_model_supplied": hud_model_result is not None,
        "hud_model_defined": bool(hud_model.get("model_defined")),
        "hud_no_network_listener": bool(hud_model.get("no_network_listener")),
        "hud_drm_node_policy_defined": bool(hud_model.get("drm_node_policy_defined")),
        "hud_launcher_hardening_required": bool(
            hud_model.get("launcher_no_new_privs_required")
            and hud_model.get("launcher_caps_zero_required")
        ),
        "hud_live_proven": bool(hud_model.get("hud_live_proven") or hud_presenter_model.get("hud_live_proven")),
        "hud_presenter_model_supplied": hud_presenter_model_result is not None,
        "hud_presenter_model_defined": bool(hud_presenter_model.get("model_defined")),
        "hud_presenter_live_proof_supplied": hud_presenter_live_proof_result is not None,
        "hud_native_presenter_live_proven": bool(
            hud_presenter_model.get("native_presenter_live_proven")
        ),
        "hud_presenter_checked_flash_proven": bool(
            hud_presenter_live.get("checked_flash_sha_matched")
            and hud_presenter_live.get("checked_flash_boot_health_clean")
        ),
        "hud_presenter_validate_live_proven": bool(
            hud_presenter_live.get("validate_policy_markers")
        ),
        "hud_presenter_present_live_proven": bool(
            hud_presenter_live.get("present_begin_frame_rc_zero")
            and hud_presenter_live.get("present_rc_zero")
            and hud_presenter_live.get("present_done")
        ),
        "hud_presenter_reject_paths_live_proven": bool(
            hud_presenter_live.get("reject_forbidden_command")
            and hud_presenter_live.get("reject_stale_intent")
        ),
        "hud_presenter_handoff_proof_supplied": hud_presenter_handoff_proof_result is not None,
        "hud_presenter_handoff_live_proven": bool(
            hud_presenter_model.get("handoff_live_proven")
        ),
        "hud_presenter_handoff_shared_run_bind_proven": bool(
            hud_presenter_handoff.get("handoff_shared_run_bind_ok")
            and hud_presenter_handoff.get("shared_run_same_mount_after_handoff")
        ),
        "hud_presenter_handoff_fresh_debian_intent_consumed": bool(
            hud_presenter_handoff.get("fresh_debian_intent_consumed")
        ),
        "hud_presenter_handoff_sole_drm_owner": bool(
            hud_presenter_handoff.get("presenter_sole_drm_owner_after_handoff")
        ),
        "hud_presenter_restart_proof_supplied": hud_presenter_restart_proof_result is not None,
        "hud_presenter_restart_live_proven": bool(
            hud_presenter_model.get("restart_live_proven")
        ),
        "hud_presenter_durable_restart_live_proven": bool(
            hud_presenter_model.get("durable_restart_live_proven")
        ),
        "hud_presenter_restart_stop_start_proven": bool(
            hud_presenter_restart.get("restart_done")
            and hud_presenter_restart.get("restart_stop_rc") == 0
            and hud_presenter_restart.get("restart_start_rc") == 0
        ),
        "hud_presenter_restart_post_present_proven": bool(
            hud_presenter_restart.get("post_restart_sequence") == wsta147.POST_RESTART_SEQUENCE
            and hud_presenter_restart.get("post_restart_present_rc") == 0
            and hud_presenter_restart.get("post_restart_drm_fd")
        ),
        "hud_presenter_stale_pid_cleanup_proven": bool(
            hud_presenter_restart.get("stale_pid_cleanup_marker")
            and hud_presenter_restart.get("stale_pid_cleanup_fake_pid") == wsta147.FAKE_STALE_PID
            and hud_presenter_restart.get("stale_pid_cleanup_start_done")
            and hud_presenter_restart.get("final_status_stopped")
        ),
        "hud_intent_syscall_proof_supplied": hud_intent_syscall_proof_result is not None,
        "hud_intent_syscall_trace_live_proven": bool(
            hud_intent_syscall.get("hud_intent_syscall_trace_live_proven")
        ),
        "hud_intent_syscall_no_network": bool(
            hud_intent_syscall.get("network_syscalls_absent")
        ),
        "hud_intent_syscall_no_drm": bool(
            hud_intent_syscall.get("ioctl_syscall_absent")
            and hud_intent_syscall.get("drm_trace_absent")
        ),
        "hud_intent_syscall_atomic_write": bool(
            hud_intent_syscall.get("atomic_rename_observed")
        ),
        "hud_direct_nonroot_kms_rejected": bool(
            hud_presenter_model.get("supersedes_wsta127_direct_kms")
        ),
        "hud_intent_producer_no_drm": bool(hud_presenter_model.get("producer_no_drm_or_kms")),
        "hud_intent_producer_no_network": bool(hud_presenter_model.get("producer_no_network")),
        "hud_native_presenter_owner": hud_presenter_model.get("presenter_owner") == "native-init",
        "hud_intent_schema_fail_closed": bool(
            hud_presenter_model.get("intent_parser_fail_closed")
            and hud_presenter_model.get("intent_secret_fields_forbidden")
        ),
        "default_public_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    if packet_filter_proof_result is not None and not result["checks"]["packet_filter_loopback_live_proven"]:
        result["decision"] = "wsta108-blocked-wsta94-packet-filter-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        packet_filter_control_summary is not None
        and not result["checks"]["packet_filter_control_plane_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-packet-filter-control-summary-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if launcher_proof_result is not None and not result["checks"]["service_launcher_smoke_live_proven"]:
        result["decision"] = "wsta108-blocked-wsta110-launcher-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        syscall_trace_proof_result is not None
        and not result["checks"]["smoke_syscall_trace_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta114-syscall-trace-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        dropbear_admin_proof_result is not None
        and not result["checks"]["dropbear_admin_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta120-dropbear-admin-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        dropbear_admin_syscall_proof_result is not None
        and not result["checks"]["dropbear_admin_syscall_trace_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta151-dropbear-admin-syscall-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        cloudflared_model_result is not None
        and not result["checks"]["cloudflared_model_defined"]
    ):
        result["decision"] = "wsta108-blocked-wsta122-cloudflared-model-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        cloudflared_runtime_proof_result is not None
        and not result["checks"]["cloudflared_runtime_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta125-cloudflared-runtime-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if hud_model_result is not None and not result["checks"]["hud_model_defined"]:
        result["decision"] = "wsta108-blocked-wsta127-hud-model-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        hud_presenter_model_result is not None
        and not result["checks"]["hud_presenter_model_defined"]
    ):
        result["decision"] = "wsta108-blocked-wsta130-hud-presenter-model-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        hud_presenter_live_proof_result is not None
        and not result["checks"]["hud_native_presenter_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta137-hud-presenter-live-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        hud_presenter_handoff_proof_result is not None
        and not result["checks"]["hud_presenter_handoff_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta144-hud-presenter-handoff-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        hud_presenter_restart_proof_result is not None
        and not result["checks"]["hud_presenter_restart_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta147-hud-presenter-restart-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if (
        hud_intent_syscall_proof_result is not None
        and not result["checks"]["hud_intent_syscall_trace_live_proven"]
    ):
        result["decision"] = "wsta108-blocked-wsta149-hud-intent-syscall-proof-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"

    md_text = markdown(server_status)
    findings = redaction_findings(public_summary(result)) + redaction_findings({"markdown": md_text})
    if findings:
        result["decision"] = "wsta108-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--emit-server-status", action="store_true")
    parser.add_argument("--wsta88-operator-workflow-json", type=Path)
    parser.add_argument("--wsta90-service-hardening-manifest-json", type=Path)
    parser.add_argument("--wsta94-packet-filter-proof-json", type=Path)
    parser.add_argument("--packet-filter-control-summary-json", type=Path)
    parser.add_argument("--wsta110-service-launcher-proof-json", type=Path)
    parser.add_argument("--wsta114-syscall-trace-proof-json", type=Path)
    parser.add_argument("--wsta120-dropbear-admin-proof-json", type=Path)
    parser.add_argument("--wsta151-dropbear-admin-syscall-proof-json", type=Path)
    parser.add_argument("--wsta122-cloudflared-model-json", type=Path)
    parser.add_argument("--wsta125-cloudflared-runtime-proof-json", type=Path)
    parser.add_argument("--wsta127-hud-model-json", type=Path)
    parser.add_argument("--wsta130-hud-presenter-model-json", type=Path)
    parser.add_argument("--wsta137-hud-presenter-live-proof-json", type=Path)
    parser.add_argument("--wsta144-hud-presenter-handoff-proof-json", type=Path)
    parser.add_argument("--wsta147-hud-presenter-restart-proof-json", type=Path)
    parser.add_argument("--wsta149-hud-intent-syscall-proof-json", type=Path)
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta108-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
