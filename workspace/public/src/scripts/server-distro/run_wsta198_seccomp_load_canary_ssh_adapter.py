#!/usr/bin/env python3
"""WSTA198 SSH/chroot adapter for the WSTA196 seccomp-load canary.

Consumes the WSTA197 transport gate and renders a default-off SSH/chroot
adapter packet for the WSTA196 canary path.  The optional live path is present
but fail-closed: it requires explicit acknowledgements, the private WSTA161
token environment variable, fresh native health, temporary Dropbear over NCM,
and post-run health.  Default execution is host-only and does not load or
enforce seccomp.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90ctl  # noqa: E402
import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402
import run_wsta149_dpublic_hud_intent_syscall_trace as wsta149  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta161_seccomp_loader_gated_apply_helper as wsta161  # noqa: E402
import run_wsta167_seccomp_live_observation as wsta167  # noqa: E402
import run_wsta193_seccomp_correct_token_canary_source as wsta193  # noqa: E402
import run_wsta196_seccomp_load_canary_execute as wsta196  # noqa: E402
import run_wsta197_seccomp_load_canary_transport_gate as wsta197  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA197_TRANSPORT_GATE = (
    DEFAULT_RUN_BASE
    / "wsta197-seccomp-load-canary-transport-gate-20260705T171427KST"
    / wsta197.TRANSPORT_JSON_NAME
)
DEFAULT_LOCAL_IMAGE = wsta149.WSTA115_STRACE_IMAGE
DEFAULT_REMOTE_CLEAN_IMAGE = wsta42.DEFAULT_REMOTE_CLEAN_IMAGE
DEFAULT_WSTA153_POLICY = wsta160.DEFAULT_WSTA153_POLICY
DEFAULT_WSTA156_MANIFEST = wsta160.DEFAULT_WSTA156_MANIFEST
DEFAULT_WSTA156_OBJECT = wsta160.DEFAULT_WSTA156_OBJECT
DEFAULT_WSTA161_MANIFEST = wsta167.DEFAULT_WSTA161_MANIFEST
DEFAULT_WSTA161_HELPER = wsta167.DEFAULT_WSTA161_HELPER
SOURCE_PASS_DECISION = "wsta198-seccomp-load-canary-ssh-adapter-source-pass"
LIVE_PASS_DECISION = "wsta198-seccomp-load-canary-ssh-adapter-live-pass"
SUMMARY_NAME = "wsta198_result.json"
ADAPTER_JSON_NAME = "wsta198_seccomp_load_canary_ssh_adapter.json"
ADAPTER_SH_NAME = "wsta198_seccomp_load_canary_ssh_adapter.sh"
ADAPTER_MD_NAME = "wsta198_seccomp_load_canary_ssh_adapter.md"
FORBIDDEN_TOKEN_PREFIX = "WSTA161-" + "EXPLICIT"


ACK_FLAGS = [
    "--execute-real-seccomp-load-canary-over-ssh",
    "--allow-correct-wsta161-token",
    "--ack-seccomp-load-risk",
    "--ack-single-service-canary-only",
    "--ack-no-flash-no-reboot",
    "--ack-cleanup-required",
    "--ack-ssh-chroot-transport",
]


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def live_requested(args: argparse.Namespace) -> bool:
    return bool(args.execute_real_seccomp_load_canary_over_ssh)


def safety_flags(args: argparse.Namespace) -> dict[str, Any]:
    requested = live_requested(args)
    return {
        "device_action_requested": requested,
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
        "ssh_chroot_transport": False,
        "dropbear_over_ncm": False,
        "fresh_native_health_checked": False,
        "post_run_native_health_checked": False,
        "live_command_generated": bool(args.emit_wsta198_ssh_adapter_packet),
        "live_command_executed": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "token_passed_over_stdin_redacted": False,
        "seccomp_assets_staged": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "post_run_audit_executed": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA198 SSH/chroot adapter for WSTA196 seccomp-load canary",
        "default_mode": "host-only-adapter-packet",
        "source_gate_command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-wsta198-ssh-adapter-packet",
        ],
        "optional_live_command_shape": [
            "python3",
            rel(Path(__file__).resolve()),
            *ACK_FLAGS,
        ],
        "selected_transport": wsta197.SELECTED_TRANSPORT,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "correct_wsta161_token": "operator-env-only",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "adapter": result.get("adapter", {}),
        "execution": {
            "returncode": result.get("execution", {}).get("returncode"),
            "canary_loaded": result.get("canary_parse", {}).get("loaded_marker"),
            "post_health_ok": result.get("checks", {}).get("post_health_valid"),
        },
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def no_external_network_inputs(text: str) -> bool:
    lowered = text.lower()
    return (
        "cloudflared" not in lowered
        and ("ss" + "id=") not in lowered
        and ("ps" + "k=") not in lowered
        and "try" + "cloudflare.com" not in lowered
        and "http" + "://" not in lowered
        and "https" + "://" not in lowered
    )


def validate_wsta197_transport_gate(gate: dict[str, Any]) -> dict[str, bool]:
    checks = wsta197.validate_transport_gate(gate)
    adapter = gate.get("adapter_contract", {}) if isinstance(gate.get("adapter_contract"), dict) else {}
    checks.update({
        "state_ready_for_adapter_only": (
            gate.get("state") == "TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER"
        ),
        "selected_transport_matches": gate.get("selected_transport") == wsta197.SELECTED_TRANSPORT,
        "adapter_runner_self": (
            adapter.get("runner")
            == "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py"
        ),
        "direct_host_execute_disallowed": gate.get("wsta196_direct_host_subprocess_execute_allowed") is False,
        "ready_for_wsta198": gate.get("ready_for_wsta198_transport_adapter") is True,
        "not_ready_for_wsta196_live": gate.get("ready_for_wsta196_live_execute") is False,
    })
    return checks


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_real_seccomp_load_canary_over_ssh:
        return False, "wsta198-blocked-explicit-live-gate-required"
    if not args.allow_correct_wsta161_token:
        return False, "wsta198-blocked-correct-token-allow-required"
    if not args.ack_seccomp_load_risk:
        return False, "wsta198-blocked-seccomp-load-risk-ack-required"
    if not args.ack_single_service_canary_only:
        return False, "wsta198-blocked-single-service-ack-required"
    if not args.ack_no_flash_no_reboot:
        return False, "wsta198-blocked-no-flash-no-reboot-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta198-blocked-cleanup-ack-required"
    if not args.ack_ssh_chroot_transport:
        return False, "wsta198-blocked-ssh-chroot-transport-ack-required"
    return True, "ok"


def private_token_status() -> dict[str, bool]:
    value = os.environ.get(wsta193.PRIVATE_TOKEN_ENV)
    return {
        "private_token_env_present": value is not None,
        "private_token_matches_wsta161": value == wsta161.LOAD_TOKEN,
    }


def seccomp_asset_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "policy": resolve_path(args.wsta153_seccomp_policy_json),
        "filter_manifest": resolve_path(args.wsta156_filter_manifest_json),
        "filter_object": resolve_path(args.wsta156_filter_object),
        "loader_manifest": resolve_path(args.wsta161_loader_helper_manifest_json),
        "loader_helper": resolve_path(args.wsta161_loader_helper),
    }


def validate_seccomp_asset_inputs(paths: dict[str, Path]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for key, path in paths.items():
        checks[f"{key}_private"] = wsta160.is_under(path, PRIVATE_ROOT)
        checks[f"{key}_present"] = path.is_file()
    return checks


def stage_seccomp_canary_assets(
    args: argparse.Namespace,
    run_dir: Path,
    paths: dict[str, Path],
) -> dict[str, Any]:
    policy = load_json(paths["policy"])
    records = {
        "launcher": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SERVICE_LAUNCHER),
            wsta3.launcher_script().encode("utf-8"),
            mode="0755",
            timeout=args.ssh_timeout,
        ),
        "policy": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_POLICY),
            (json.dumps(policy, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "map": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LAUNCHER_MAP),
            wsta3.seccomp_launcher_map_text(policy).encode("utf-8"),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "filter_manifest": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_FILTER_MANIFEST),
            paths["filter_manifest"].read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "filter_object": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_FILTER_OBJECT),
            paths["filter_object"].read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "loader_manifest": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER_MANIFEST),
            paths["loader_manifest"].read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "loader_helper": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER),
            paths["loader_helper"].read_bytes(),
            mode="0755",
            timeout=args.ssh_timeout,
        ),
    }
    records["staged"] = all(bool(item.get("staged")) for item in records.values() if isinstance(item, dict))
    records["secret_values_logged"] = 0
    return records


def live_command_template(transport_gate: Path) -> list[str]:
    return [
        "python3",
        "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py",
        "--run-id",
        "wsta198-seccomp-load-canary-ssh-adapter-live-<fresh-timestamp>",
        "--wsta197-transport-gate-json",
        rel(transport_gate),
        *ACK_FLAGS,
        "--print-full-json",
    ]


def command_script(transport_gate: Path) -> str:
    return "\n".join([
        "#!/bin/sh",
        "set -eu",
        f"cd '{REPO_ROOT}'",
        "ts=$(date +%Y%m%dT%H%M%SKST)",
        'export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/a90_pycache}"',
        f': "${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}"',
        "exec python3 workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py \\",
        '  --run-id "wsta198-seccomp-load-canary-ssh-adapter-live-${ts}" \\',
        f"  --wsta197-transport-gate-json '{rel(transport_gate)}' \\",
        "  --execute-real-seccomp-load-canary-over-ssh \\",
        "  --allow-correct-wsta161-token \\",
        "  --ack-seccomp-load-risk \\",
        "  --ack-single-service-canary-only \\",
        "  --ack-no-flash-no-reboot \\",
        "  --ack-cleanup-required \\",
        "  --ack-ssh-chroot-transport \\",
        "  --print-full-json",
        "",
    ])


def remote_canary_script_template(gate: dict[str, Any]) -> str:
    launcher = gate.get("launcher_command") or []
    if launcher != ["/usr/local/bin/a90-service-launch", wsta193.CANARY_SERVICE, wsta193.CANARY_COMMAND]:
        raise ValueError(f"unexpected launcher command: {launcher!r}")
    return "\n".join([
        "set -eu",
        "echo A90WSTA198_REMOTE_CANARY_BEGIN",
        ': "${A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN:?load-token-required}"',
        "[ -x /usr/local/bin/a90-service-launch ] && echo A90WSTA198_LAUNCHER_PRESENT=1 || exit 31",
        "[ -r /etc/a90-dpublic/seccomp-policy.json ] && echo A90WSTA198_SECCOMP_POLICY_PRESENT=1 || exit 32",
        "[ -r /etc/a90-dpublic/seccomp-launcher-map.env ] && echo A90WSTA198_SECCOMP_MAP_PRESENT=1 || exit 33",
        "[ -r /etc/a90-dpublic/seccomp-filter-manifest.json ] && echo A90WSTA198_FILTER_MANIFEST_PRESENT=1 || exit 34",
        "/usr/bin/env -i \\",
        "  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\",
        "  A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN=1 \\",
        "  A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1 \\",
        "  A90_SERVICE_LAUNCH_SECCOMP_HELPER_MODE=apply \\",
        "  A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE=WSTA163-ALLOW-HELPER-APPLY \\",
        "  A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE=WSTA164-ALLOW-SECCOMP-LOAD-ENV \\",
        '  A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN="$A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN" \\',
        "  /usr/local/bin/a90-service-launch dpublic-hud /bin/true",
    ])


def redacted_text(text: str, token: str) -> str:
    return text.replace(token, "<redacted-wsta161-token>") if token else text


def ssh_exec_token_script(
    args: argparse.Namespace,
    run_dir: Path,
    script: str,
    *,
    token: str,
    timeout: float,
) -> dict[str, Any]:
    command = [*wsta42.ssh_command(args, run_dir), "/bin/sh", "-s"]
    input_script = (
        "A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN="
        + shlex.quote(token)
        + "\nexport A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN\n"
        + script
        + "\n"
    )
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=input_script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "input_redacted": True,
        "redacted_label": "wsta198-seccomp-load-canary-ssh-stdin-token",
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": redacted_text(completed.stdout, token),
        "stderr": redacted_text(completed.stderr, token),
    }


def build_adapter_packet(run_dir: Path, transport_gate_path: Path, gate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    packet_json = run_dir / ADAPTER_JSON_NAME
    packet_sh = run_dir / ADAPTER_SH_NAME
    packet_md = run_dir / ADAPTER_MD_NAME
    script_text = command_script(transport_gate_path)
    packet = {
        "schema": "a90-wsta198-seccomp-load-canary-ssh-adapter-v1",
        "state": "READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH",
        "source_wsta197_transport_gate": rel(transport_gate_path),
        "selected_transport": gate.get("selected_transport"),
        "runner": "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py",
        "canary_service": gate.get("canary_service"),
        "policy_service": gate.get("policy_service"),
        "launcher_command": gate.get("launcher_command"),
        "single_service_canary": True,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "token_transport": "ssh-stdin-redacted-to-remote-env",
        "live_command_template": live_command_template(transport_gate_path),
        "live_command_script": rel(packet_sh),
        "operator_acknowledgements_required": ACK_FLAGS,
        "operator_preflight_checks": [
            "fresh-native-readonly-health-before-canary",
            "temporary-dropbear-over-usb-ncm-only",
            "debian-chroot-marker-present",
            "service-launcher-and-seccomp-assets-present",
            "private-token-env-present-at-execution-time",
            "post-native-readonly-health-after-canary",
        ],
        "abort_conditions": [
            "transport-gate-not-pass",
            "private-token-env-missing-or-wrong",
            "native-health-not-green",
            "chroot-dropbear-setup-fails",
            "service-launcher-or-seccomp-assets-missing",
            "canary-load-marker-not-observed",
            "post-health-regresses",
        ],
        "cleanup_expectations": [
            "dropbear stopped",
            "authorized_keys removed",
            "root shadow restored",
            "chroot unmounted",
            "loop detached",
            "post selftest fail=0",
        ],
        "ready_for_attended_live": True,
        "ready_for_unattended_live": False,
        "default_off": True,
        "live_execution_requested": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "json_path": rel(packet_json),
        "markdown_path": rel(packet_md),
    }
    return packet, script_text


def validate_adapter_packet(packet: dict[str, Any], script_text: str) -> dict[str, bool]:
    serialized = json.dumps(packet, sort_keys=True) + "\n" + script_text
    command = packet.get("live_command_template", [])
    return {
        "schema_ok": packet.get("schema") == "a90-wsta198-seccomp-load-canary-ssh-adapter-v1",
        "state_default_off": (
            packet.get("state")
            == "READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH"
        ),
        "selected_transport_ssh": packet.get("selected_transport") == wsta197.SELECTED_TRANSPORT,
        "runner_self": (
            packet.get("runner")
            == "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py"
        ),
        "single_service_canary": packet.get("single_service_canary") is True,
        "launcher_command_shape": packet.get("launcher_command") == [
            "/usr/local/bin/a90-service-launch",
            wsta193.CANARY_SERVICE,
            wsta193.CANARY_COMMAND,
        ],
        "private_token_env_named": packet.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": packet.get("token_value_included") is False,
        "token_stdin_redacted": packet.get("token_transport") == "ssh-stdin-redacted-to-remote-env",
        "ready_attended_not_unattended": (
            packet.get("ready_for_attended_live") is True
            and packet.get("ready_for_unattended_live") is False
        ),
        "default_off": packet.get("default_off") is True,
        "live_not_requested": packet.get("live_execution_requested") is False,
        "command_targets_self": "run_wsta198_seccomp_load_canary_ssh_adapter.py" in serialized,
        "command_has_execute_gate": "--execute-real-seccomp-load-canary-over-ssh" in serialized,
        "command_has_ack_stack": all(flag in serialized for flag in ACK_FLAGS),
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in script_text,
        "script_uses_fresh_timestamp": "date +%Y%m%dT%H%M%SKST" in script_text and "${ts}" in script_text,
        "command_is_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": no_external_network_inputs(serialized),
        "secret_values_zero": packet.get("secret_values_logged") == 0,
        "public_url_not_logged": packet.get("public_url_value_logged") is False,
    }


def adapter_markdown(packet: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in packet.get("live_command_template") or [])
    lines = [
        "# WSTA198 Seccomp-Load Canary SSH Adapter",
        "",
        f"- State: `{packet.get('state')}`",
        f"- Selected transport: `{packet.get('selected_transport')}`",
        f"- Source WSTA197 gate: `{packet.get('source_wsta197_transport_gate')}`",
        f"- Command script: `{packet.get('live_command_script')}`",
        f"- Private token env: `{packet.get('private_token_env')}`",
        "- Live execution requested: `false`",
        "",
        "## Guardrails",
        "",
    ]
    for item in packet.get("operator_preflight_checks", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "WSTA198 does not run the live canary unless the explicit live flags and private token are supplied.",
        "",
    ])
    return "\n".join(lines)


def classify(result: dict[str, Any], *, executing: bool) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("private_run_dir", "wsta198-blocked-nonprivate-run-dir"),
        ("wsta197_transport_gate_private", "wsta198-blocked-transport-gate-nonprivate"),
        ("wsta197_transport_gate_present", "wsta198-blocked-transport-gate-missing"),
        ("wsta197_transport_gate_valid", "wsta198-blocked-transport-gate-invalid"),
        ("adapter_packet_valid", "wsta198-blocked-adapter-packet-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    if not executing:
        if not checks.get("explicit_source_gate"):
            return "wsta198-blocked-explicit-source-gate-required"
        return SOURCE_PASS_DECISION
    live_order = (
        ("explicit_live_gate", result.get("gate_decision") or "wsta198-blocked-explicit-live-gate"),
        ("private_token_env_present", "wsta198-blocked-private-token-env-missing"),
        ("private_token_matches_wsta161", "wsta198-blocked-private-token-invalid"),
        ("fresh_health_valid", "wsta198-blocked-fresh-health-invalid"),
        ("ssh_key_generated", "wsta198-blocked-ssh-keygen"),
        ("native_stale_cleanup_ok", "wsta198-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta198-blocked-remote-image-ready"),
        ("chroot_mount_ready", "wsta198-blocked-chroot-mount"),
        ("dropbear_started", "wsta198-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta198-blocked-debian-ssh-marker"),
        ("seccomp_asset_inputs_valid", "wsta198-blocked-seccomp-asset-inputs"),
        ("seccomp_assets_staged", "wsta198-blocked-seccomp-assets-stage"),
        ("execution_returncode_bounded", "wsta198-blocked-canary-returncode"),
        ("canary_loaded", "wsta198-blocked-canary-load-not-observed"),
        ("chroot_cleanup_ok", "wsta198-blocked-chroot-cleanup"),
        ("post_health_valid", "wsta198-blocked-post-health-invalid"),
    )
    for key, decision in live_order:
        if not checks.get(key):
            return str(decision)
    return LIVE_PASS_DECISION


def finish_result(out_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def execute_live(
    args: argparse.Namespace,
    result: dict[str, Any],
    out_path: Path,
    run_dir: Path,
    run_id: str,
    gate: dict[str, Any],
) -> dict[str, Any]:
    token = os.environ[wsta193.PRIVATE_TOKEN_ENV]
    result["fresh_health"] = wsta196.run_readonly_health_checks(args.health_timeout)
    result["checks"]["fresh_health_valid"] = all(result["fresh_health"]["checks"].values())
    result["safety"]["fresh_native_health_checked"] = True
    write_json(out_path, result)
    if not result["checks"]["fresh_health_valid"]:
        result["decision"] = classify(result, executing=True)
        return finish_result(out_path, result)

    mounted = False
    try:
        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        result["checks"]["ssh_key_generated"] = result["keygen"].get("returncode") == 0
        public_key = d2.read_public_key(run_dir)
        write_json(out_path, result)
        if not result["checks"]["ssh_key_generated"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["native_stale_cleanup"] = wsta94.native_stale_cleanup(args)
        result["checks"]["native_stale_cleanup_ok"] = bool(result["native_stale_cleanup"].get("cleaned"))
        write_json(out_path, result)
        if not result["checks"]["native_stale_cleanup_ok"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["local_image"] = rel(args.local_image)
        result["checks"]["local_image_present"] = args.local_image.is_file()
        if not result["checks"]["local_image_present"]:
            result["checks"]["local_image_expected_sha"] = False
            result["checks"]["remote_image_ready"] = False
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)
        local_sha = d1.sha256_file(args.local_image)
        result["local_image_sha256"] = local_sha
        result["checks"]["local_image_expected_sha"] = (
            not args.local_image_sha256 or local_sha == args.local_image_sha256
        )
        if not result["checks"]["local_image_expected_sha"]:
            result["checks"]["remote_image_ready"] = False
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        image_ready = wsta42.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)
        result["checks"]["remote_image_ready"] = bool(image_ready)
        write_json(out_path, result)
        if not image_ready:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["mount"] = wsta19.bridge_shell(
            args,
            wsta94.wsta94_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount_parse"] = d2.parse_setup(str(result["mount"].get("text") or ""))
        result["checks"]["chroot_mount_ready"] = bool(
            result["mount_parse"].get("mount_ready") and result["mount_parse"].get("mounted")
        )
        write_json(out_path, result)
        if not result["checks"]["chroot_mount_ready"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["dropbear_start"] = wsta19.bridge_shell(
            args,
            wsta94.wsta94_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["dropbear_parse"] = d2.parse_setup(str(result["dropbear_start"].get("text") or ""))
        result["checks"]["dropbear_started"] = bool(
            result["dropbear_parse"].get("started")
            and result["dropbear_parse"].get("authorized_keys")
            and result["dropbear_parse"].get("shadow_temp_key_only")
        )
        write_json(out_path, result)
        if not result["checks"]["dropbear_started"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        result["checks"]["debian_ssh_marker"] = bool(result["ssh_parse"].get("marker"))
        write_json(out_path, result)
        if not result["checks"]["debian_ssh_marker"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        asset_paths = seccomp_asset_paths(args)
        asset_checks = validate_seccomp_asset_inputs(asset_paths)
        result["seccomp_asset_input_checks"] = asset_checks
        result["checks"]["seccomp_asset_inputs_valid"] = all(asset_checks.values())
        write_json(out_path, result)
        if not result["checks"]["seccomp_asset_inputs_valid"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["seccomp_assets_stage"] = stage_seccomp_canary_assets(args, run_dir, asset_paths)
        result["checks"]["seccomp_assets_staged"] = bool(result["seccomp_assets_stage"].get("staged"))
        result["safety"]["seccomp_assets_staged"] = result["checks"]["seccomp_assets_staged"]
        write_json(out_path, result)
        if not result["checks"]["seccomp_assets_staged"]:
            result["decision"] = classify(result, executing=True)
            return finish_result(out_path, result)

        result["safety"]["device_action"] = "single-service-seccomp-load-canary-over-ssh-chroot"
        result["safety"]["ssh_chroot_transport"] = True
        result["safety"]["dropbear_over_ncm"] = True
        result["safety"]["live_command_executed"] = True
        result["safety"]["correct_wsta161_token_supplied"] = True
        result["safety"]["token_passed_over_stdin_redacted"] = True
        result["execution"] = ssh_exec_token_script(
            args,
            run_dir,
            remote_canary_script_template(gate),
            token=token,
            timeout=args.execution_timeout,
        )
        canary_parse = wsta196.parse_canary_output(result["execution"])
        result["canary_parse"] = canary_parse
        result["checks"]["execution_returncode_bounded"] = canary_parse["returncode_bounded"]
        result["checks"]["canary_loaded"] = (
            canary_parse["load_attempt_marker"]
            and canary_parse["loaded_marker"]
            and canary_parse["apply_ok_marker"]
            and canary_parse["single_service_marker"]
            and canary_parse["policy_service_marker"]
            and canary_parse["token_literal_absent"]
            and canary_parse["no_external_network_inputs"]
        )
        if result["checks"]["canary_loaded"]:
            result["safety"]["seccomp_filter_loaded"] = True
            result["safety"]["seccomp_enforced"] = True
        write_json(out_path, result)
    finally:
        if mounted:
            result["cleanup"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
            result["checks"]["chroot_cleanup_ok"] = bool(wsta94.chroot_cleanup_ok(result))
        else:
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["checks"]["chroot_cleanup_ok"] = True
        result["post_health"] = wsta196.run_readonly_health_checks(args.health_timeout)
        result["checks"]["post_health_valid"] = all(result["post_health"]["checks"].values())
        result["safety"]["post_run_native_health_checked"] = True
        result["safety"]["post_run_audit_executed"] = True
        write_json(out_path, result)

    result["decision"] = classify(result, executing=True)
    result["gate_decision"] = "ok" if result["decision"] == LIVE_PASS_DECISION else result["decision"]
    return finish_result(out_path, result)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta198-seccomp-load-canary-ssh-adapter-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    transport_gate_path = resolve_path(args.wsta197_transport_gate_json)
    executing = live_requested(args)
    live_gate_ok, live_gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA198 SSH/chroot adapter for WSTA196 seccomp-load canary",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta197_transport_gate_json": rel(transport_gate_path),
        "gate_decision": "source-gate" if args.emit_wsta198_ssh_adapter_packet and not executing else live_gate_decision,
        "safety": safety_flags(args),
        "checks": {
            "explicit_source_gate": bool(args.emit_wsta198_ssh_adapter_packet),
            "explicit_live_gate": live_gate_ok,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta197_transport_gate_private": wsta160.is_under(transport_gate_path, PRIVATE_ROOT),
            "wsta197_transport_gate_present": transport_gate_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result, executing=executing)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("wsta197_transport_gate_private", "wsta197_transport_gate_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result, executing=executing)
            return finish_result(out_path, result)

    gate = load_json(transport_gate_path)
    gate_checks = validate_wsta197_transport_gate(gate)
    result["wsta197_transport_gate_checks"] = gate_checks
    result["checks"]["wsta197_transport_gate_valid"] = all(gate_checks.values())
    packet, script_text = build_adapter_packet(run_dir, transport_gate_path, gate)
    packet_checks = validate_adapter_packet(packet, script_text)
    result["adapter_packet_checks"] = packet_checks
    result["checks"]["adapter_packet_valid"] = all(packet_checks.values())
    result["adapter"] = {
        "adapter_json": rel(run_dir / ADAPTER_JSON_NAME),
        "adapter_shell": rel(run_dir / ADAPTER_SH_NAME),
        "adapter_markdown": rel(run_dir / ADAPTER_MD_NAME),
        "state": packet["state"],
        "selected_transport": packet["selected_transport"],
        "canary_service": packet["canary_service"],
        "private_token_env": packet["private_token_env"],
        "ready_for_attended_live": True,
        "ready_for_unattended_live": False,
        "live_execution_requested": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
    }
    if args.emit_wsta198_ssh_adapter_packet and not executing:
        if result["checks"]["wsta197_transport_gate_valid"] and result["checks"]["adapter_packet_valid"]:
            write_json(run_dir / ADAPTER_JSON_NAME, packet)
            write_text(run_dir / ADAPTER_SH_NAME, script_text)
            (run_dir / ADAPTER_SH_NAME).chmod(0o700)
            write_text(run_dir / ADAPTER_MD_NAME, adapter_markdown(packet))
        result["decision"] = classify(result, executing=False)
        result["gate_decision"] = "ok" if result["decision"] == SOURCE_PASS_DECISION else result["decision"]
        return finish_result(out_path, result)

    if not executing:
        result["decision"] = classify(result, executing=False)
        return finish_result(out_path, result)

    token_checks = private_token_status()
    result["token_checks"] = token_checks
    result["checks"].update(token_checks)
    write_json(out_path, result)
    if (
        not live_gate_ok
        or not result["checks"]["wsta197_transport_gate_valid"]
        or not result["checks"]["adapter_packet_valid"]
        or not result["checks"]["private_token_env_present"]
        or not result["checks"]["private_token_matches_wsta161"]
    ):
        result["decision"] = classify(result, executing=True)
        return finish_result(out_path, result)

    return execute_live(args, result, out_path, run_dir, run_id, gate)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta197-transport-gate-json", type=Path, default=DEFAULT_WSTA197_TRANSPORT_GATE)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--bridge-host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=d2.DEFAULT_SSH_PORT)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--health-timeout", type=float, default=20.0)
    parser.add_argument("--setup-timeout", type=float, default=120.0)
    parser.add_argument("--cleanup-timeout", type=float, default=90.0)
    parser.add_argument("--execution-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=30.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--local-image", type=Path, default=DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=wsta149.WSTA115_STRACE_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--wsta156-filter-manifest-json", type=Path, default=DEFAULT_WSTA156_MANIFEST)
    parser.add_argument("--wsta156-filter-object", type=Path, default=DEFAULT_WSTA156_OBJECT)
    parser.add_argument("--wsta161-loader-helper-manifest-json", type=Path, default=DEFAULT_WSTA161_MANIFEST)
    parser.add_argument("--wsta161-loader-helper", type=Path, default=DEFAULT_WSTA161_HELPER)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--emit-wsta198-ssh-adapter-packet", action="store_true")
    parser.add_argument("--execute-real-seccomp-load-canary-over-ssh", action="store_true")
    parser.add_argument("--allow-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-seccomp-load-risk", action="store_true")
    parser.add_argument("--ack-single-service-canary-only", action="store_true")
    parser.add_argument("--ack-no-flash-no-reboot", action="store_true")
    parser.add_argument("--ack-cleanup-required", action="store_true")
    parser.add_argument("--ack-ssh-chroot-transport", action="store_true")
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
        payload = {"decision": "wsta198-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") in (SOURCE_PASS_DECISION, LIVE_PASS_DECISION) else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
