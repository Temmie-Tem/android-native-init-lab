#!/usr/bin/env python3
"""WSTA197 transport gate for the WSTA196 seccomp-load canary.

Consumes WSTA196 source-gate evidence and prior Debian/chroot transport proofs
to choose the live execution transport for a future attended WSTA198 adapter.
This unit is host-only and does not execute WSTA196, contact the device, supply
the correct WSTA161 token, load seccomp, or enforce seccomp.
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

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta149_dpublic_hud_intent_syscall_trace as wsta149  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta167_seccomp_live_observation as wsta167  # noqa: E402
import run_wsta193_seccomp_correct_token_canary_source as wsta193  # noqa: E402
import run_wsta196_seccomp_load_canary_execute as wsta196  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA196_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta196-seccomp-load-canary-source-gate-20260705T170553KST"
    / wsta196.SUMMARY_NAME
)
DEFAULT_WSTA196_SOURCE_GATE = (
    DEFAULT_RUN_BASE
    / "wsta196-seccomp-load-canary-source-gate-20260705T170553KST"
    / wsta196.SOURCE_GATE_JSON_NAME
)
DEFAULT_WSTA149_LIVE_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta149-dpublic-hud-intent-syscall-trace-live-20260705T1058KST"
    / wsta149.RESULT_NAME
)
DEFAULT_WSTA167_SOURCE_GATE = (
    DEFAULT_RUN_BASE
    / "wsta167-seccomp-live-observation-source-gate-20260705T1354KST"
    / wsta167.RESULT_NAME
)
PASS_DECISION = "wsta197-seccomp-load-canary-transport-gate-pass"
SUMMARY_NAME = "wsta197_result.json"
TRANSPORT_JSON_NAME = "wsta197_seccomp_load_canary_transport_gate.json"
TRANSPORT_MD_NAME = "wsta197_seccomp_load_canary_transport_gate.md"
FORBIDDEN_TOKEN_PREFIX = "WSTA161-" + "EXPLICIT"
SELECTED_TRANSPORT = "debian-chroot-dropbear-ssh-over-ncm"


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
        "host_transport_gate_only": True,
        "transport_packet_generated": True,
        "transport_packet_executed": False,
        "wsta196_execute_invoked": False,
        "live_command_generated": False,
        "live_command_executed": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA197 host-only WSTA196 transport decision gate",
        "default_mode": "host-only-transport-gate",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-wsta197-seccomp-load-canary-transport-gate",
        ],
        "selected_transport": SELECTED_TRANSPORT,
        "live_execution": "not-run-by-wsta197",
        "correct_wsta161_token": "not-supplied",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "transport": result.get("transport", {}),
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


def no_mutation_safety(safety: dict[str, Any], *, allow_chroot_work_image: bool = False) -> dict[str, bool]:
    return {
        "boot_flash_false": safety.get("boot_flash") is False,
        "native_reboot_false": safety.get("native_reboot") is False,
        "wifi_connect_false": safety.get("wifi_connect") is False,
        "dhcp_false": safety.get("dhcp") is False,
        "public_tunnel_false": safety.get("public_tunnel") is False,
        "packet_filter_mutation_false": safety.get("packet_filter_mutation") is False,
        "userdata_touch_false": safety.get("userdata_touch") is False,
        "switch_root_false": safety.get("switch_root") is False,
        "public_url_not_logged": safety.get("public_url_value_logged") is False,
        "secret_values_zero": safety.get("secret_values_logged") == 0,
        "rootfs_chroot_shape_ok": (
            allow_chroot_work_image
            or safety.get("rootfs_chroot_mutation", False) is False
        ),
    }


def validate_wsta196_result(payload: dict[str, Any], source_gate_path: Path) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    source_gate = payload.get("source_gate", {}) if isinstance(payload.get("source_gate"), dict) else {}
    no_mutation = no_mutation_safety(safety)
    return {
        "decision_source_gate_pass": payload.get("decision") == wsta196.SOURCE_GATE_PASS_DECISION,
        "explicit_source_gate": checks.get("explicit_source_gate") is True,
        "not_execution_gate": checks.get("explicit_execution_gate") is False,
        "wsta195_readiness_valid": checks.get("wsta195_readiness_valid") is True,
        "wsta194_packet_valid": checks.get("wsta194_packet_valid") is True,
        "source_gate_valid": checks.get("source_gate_valid") is True,
        "source_gate_path_matches": source_gate.get("source_gate_json") == rel(source_gate_path),
        "source_gate_attended_ready": source_gate.get("ready_for_attended_execution") is True,
        "source_gate_not_unattended": source_gate.get("ready_for_unattended_execution") is False,
        "source_gate_not_executed": source_gate.get("live_command_executed") is False,
        "source_gate_no_load": source_gate.get("seccomp_filter_loaded") is False,
        "source_gate_no_enforce": source_gate.get("seccomp_enforced") is False,
        "safety_no_mutation": all(no_mutation.values()),
        "safety_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "safety_no_load": safety.get("seccomp_filter_loaded") is False,
        "safety_no_enforce": safety.get("seccomp_enforced") is False,
    }


def validate_wsta196_source_gate(source_gate: dict[str, Any]) -> dict[str, bool]:
    checks = wsta196.validate_source_gate(source_gate)
    checks.update({
        "launcher_command_shape": source_gate.get("launcher_command") == [
            "/usr/local/bin/a90-service-launch",
            wsta193.CANARY_SERVICE,
            wsta193.CANARY_COMMAND,
        ],
        "requires_fresh_health": source_gate.get("fresh_native_health_check_required") is True,
        "requires_post_health": source_gate.get("post_run_native_health_check_required") is True,
        "ready_attended_not_unattended": (
            source_gate.get("ready_for_attended_execution") is True
            and source_gate.get("ready_for_unattended_execution") is False
        ),
    })
    return checks


def validate_wsta149_live(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    no_mutation = no_mutation_safety(safety, allow_chroot_work_image=True)
    return {
        "decision_pass": payload.get("decision") == wsta149.PASS_DECISION,
        "explicit_live_gate": checks.get("explicit_live_gate") is True,
        "chroot_mount_ready": checks.get("chroot_mount_ready") is True,
        "dropbear_started": checks.get("dropbear_started") is True,
        "debian_ssh_marker": checks.get("debian_ssh_marker") is True,
        "service_hardening_assets_staged": checks.get("service_hardening_assets_staged") is True,
        "launcher_exec_logged": checks.get("launcher_exec_logged") is True,
        "service_identity_ok": checks.get("service_identity_ok") is True,
        "public_default_off": checks.get("public_default_off") is True,
        "network_syscalls_absent": checks.get("network_syscalls_absent") is True,
        "final_selftest_fail_zero": checks.get("final_selftest_fail_zero") is True,
        "chroot_cleanup_ok": checks.get("chroot_cleanup_ok") is True,
        "safety_no_forbidden_mutation": all(no_mutation.values()),
    }


def validate_wsta167_source_gate(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    contract_checks = payload.get("contract_checks", {}) if isinstance(payload.get("contract_checks"), dict) else {}
    no_mutation = no_mutation_safety(safety)
    return {
        "decision_is_source_gate_block": payload.get("decision") == "wsta167-blocked-seccomp-live-observation-required",
        "contract_valid": checks.get("contract_valid") is True,
        "local_inputs_present": checks.get("local_inputs_present") is True,
        "explicit_live_gate_false": checks.get("explicit_live_gate") is False,
        "contract_schema_ok": contract_checks.get("schema_ok") is True,
        "script_no_external_network_inputs": contract_checks.get("script_no_external_network_inputs") is True,
        "load_expected_false": contract_checks.get("load_expected_false") is True,
        "enforcement_expected_false": contract_checks.get("enforcement_expected_false") is True,
        "correct_token_false": contract_checks.get("correct_token_false") is True,
        "safety_no_mutation": all(no_mutation.values()),
        "safety_no_load": safety.get("seccomp_filter_loaded") is False,
        "safety_no_enforce": safety.get("seccomp_enforced") is False,
        "safety_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def build_transport_gate(
    run_dir: Path,
    wsta196_result: Path,
    wsta196_source_gate: Path,
    wsta149_result: Path,
    wsta167_result: Path,
    source_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "a90-wsta197-seccomp-load-canary-transport-gate-v1",
        "state": "TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER",
        "selected_transport": SELECTED_TRANSPORT,
        "transport_gate_json": rel(run_dir / TRANSPORT_JSON_NAME),
        "transport_gate_markdown": rel(run_dir / TRANSPORT_MD_NAME),
        "source_wsta196_result": rel(wsta196_result),
        "source_wsta196_source_gate": rel(wsta196_source_gate),
        "source_wsta149_live_transport_proof": rel(wsta149_result),
        "source_wsta167_seccomp_asset_source_gate": rel(wsta167_result),
        "canary_service": source_gate.get("canary_service"),
        "policy_service": source_gate.get("policy_service"),
        "launcher_command": source_gate.get("launcher_command"),
        "single_service_canary": True,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "wsta196_direct_host_subprocess_execute_allowed": False,
        "wsta196_direct_host_subprocess_reason": (
            "a90-service-launch is a Debian/chroot target; host-local subprocess is not a live device transport"
        ),
        "ready_for_wsta198_transport_adapter": True,
        "ready_for_wsta196_live_execute": False,
        "execution_sequence": [
            "fresh-native-readonly-health",
            "prepare-or-reuse-sd-work-image",
            "mount-debian-chroot",
            "start-temporary-dropbear-over-ncm",
            "stage-service-launcher-seccomp-policy-map-filter-helper",
            "run-single-service-canary-via-ssh-with-private-token-env",
            "parse-load-and-single-service-markers",
            "cleanup-dropbear-and-chroot",
            "post-native-readonly-health",
        ],
        "adapter_contract": {
            "runner": "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py",
            "input_transport_gate": rel(run_dir / TRANSPORT_JSON_NAME),
            "must_not_put_token_on_command_line": True,
            "must_redact_token_from_stdout_stderr": True,
            "must_fail_closed_without_wsta196_ack_flags": True,
            "must_fail_closed_without_private_token_env": True,
            "must_fail_closed_without_fresh_health": True,
            "must_cleanup_chroot_dropbear_even_on_failure": True,
        },
        "forbidden_in_wsta197": [
            "device contact",
            "boot flash",
            "native reboot",
            "Wi-Fi connect or DHCP",
            "public tunnel",
            "packet filter mutation",
            "userdata write",
            "switch-root",
            "WSTA196 live execute",
            "correct WSTA161 token",
            "seccomp load",
            "seccomp enforcement",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_transport_gate(gate: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(gate, sort_keys=True)
    adapter = gate.get("adapter_contract", {}) if isinstance(gate.get("adapter_contract"), dict) else {}
    return {
        "schema_ok": gate.get("schema") == "a90-wsta197-seccomp-load-canary-transport-gate-v1",
        "state_blocks_live_until_adapter": (
            gate.get("state") == "TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER"
        ),
        "selected_transport_ssh": gate.get("selected_transport") == SELECTED_TRANSPORT,
        "single_service_canary": gate.get("single_service_canary") is True,
        "canary_service_hud": gate.get("canary_service") == wsta193.CANARY_SERVICE,
        "policy_service_hud_intent": gate.get("policy_service") == "dpublic-hud-intent",
        "launcher_command_shape": gate.get("launcher_command") == [
            "/usr/local/bin/a90-service-launch",
            wsta193.CANARY_SERVICE,
            wsta193.CANARY_COMMAND,
        ],
        "private_token_env_named": gate.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": gate.get("token_value_included") is False,
        "correct_token_not_supplied": gate.get("correct_wsta161_token_supplied") is False,
        "seccomp_not_loaded": gate.get("seccomp_filter_loaded") is False,
        "seccomp_not_enforced": gate.get("seccomp_enforced") is False,
        "direct_host_execute_disallowed": gate.get("wsta196_direct_host_subprocess_execute_allowed") is False,
        "ready_for_adapter": gate.get("ready_for_wsta198_transport_adapter") is True,
        "not_ready_for_live_execute": gate.get("ready_for_wsta196_live_execute") is False,
        "execution_sequence_has_health": "fresh-native-readonly-health" in gate.get("execution_sequence", [])
        and "post-native-readonly-health" in gate.get("execution_sequence", []),
        "adapter_runner_wsta198": (
            adapter.get("runner")
            == "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py"
        ),
        "adapter_no_token_cmdline": adapter.get("must_not_put_token_on_command_line") is True,
        "adapter_redacts_token": adapter.get("must_redact_token_from_stdout_stderr") is True,
        "adapter_fail_closed_health": adapter.get("must_fail_closed_without_fresh_health") is True,
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": no_external_network_inputs(serialized),
        "secret_values_zero": gate.get("secret_values_logged") == 0,
        "public_url_not_logged": gate.get("public_url_value_logged") is False,
    }


def transport_markdown(gate: dict[str, Any]) -> str:
    lines = [
        "# WSTA197 Seccomp-Load Canary Transport Gate",
        "",
        f"- State: `{gate.get('state')}`",
        f"- Selected transport: `{gate.get('selected_transport')}`",
        f"- Canary service: `{gate.get('canary_service')}`",
        f"- Private token env: `{gate.get('private_token_env')}`",
        f"- WSTA196 direct host subprocess allowed: `{str(gate.get('wsta196_direct_host_subprocess_execute_allowed')).lower()}`",
        f"- Ready for WSTA198 adapter: `{str(gate.get('ready_for_wsta198_transport_adapter')).lower()}`",
        f"- Ready for WSTA196 live execute: `{str(gate.get('ready_for_wsta196_live_execute')).lower()}`",
        "",
        "## Execution Sequence",
        "",
    ]
    for item in gate.get("execution_sequence", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "WSTA197 is a host-only transport decision gate. It does not execute WSTA196.",
        "",
    ])
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_gate", "wsta197-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta197-blocked-nonprivate-run-dir"),
        ("wsta196_result_private", "wsta197-blocked-wsta196-result-nonprivate"),
        ("wsta196_source_gate_private", "wsta197-blocked-wsta196-source-gate-nonprivate"),
        ("wsta149_live_result_private", "wsta197-blocked-wsta149-result-nonprivate"),
        ("wsta167_source_gate_private", "wsta197-blocked-wsta167-result-nonprivate"),
        ("wsta196_result_present", "wsta197-blocked-wsta196-result-missing"),
        ("wsta196_source_gate_present", "wsta197-blocked-wsta196-source-gate-missing"),
        ("wsta149_live_result_present", "wsta197-blocked-wsta149-result-missing"),
        ("wsta167_source_gate_present", "wsta197-blocked-wsta167-result-missing"),
        ("wsta196_result_valid", "wsta197-blocked-wsta196-result-invalid"),
        ("wsta196_source_gate_valid", "wsta197-blocked-wsta196-source-gate-invalid"),
        ("wsta149_live_transport_valid", "wsta197-blocked-wsta149-transport-invalid"),
        ("wsta167_seccomp_asset_gate_valid", "wsta197-blocked-wsta167-asset-gate-invalid"),
        ("transport_gate_valid", "wsta197-blocked-transport-gate-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta197-seccomp-load-canary-transport-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    wsta196_result_path = resolve_path(args.wsta196_result_json)
    wsta196_source_gate_path = resolve_path(args.wsta196_source_gate_json)
    wsta149_path = resolve_path(args.wsta149_live_result_json)
    wsta167_path = resolve_path(args.wsta167_source_gate_json)
    result: dict[str, Any] = {
        "scope": "WSTA197 host-only WSTA196 transport decision gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta196_result_json": rel(wsta196_result_path),
        "wsta196_source_gate_json": rel(wsta196_source_gate_path),
        "wsta149_live_result_json": rel(wsta149_path),
        "wsta167_source_gate_json": rel(wsta167_path),
        "gate_decision": "not-run",
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_wsta197_seccomp_load_canary_transport_gate),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta196_result_private": wsta160.is_under(wsta196_result_path, PRIVATE_ROOT),
            "wsta196_source_gate_private": wsta160.is_under(wsta196_source_gate_path, PRIVATE_ROOT),
            "wsta149_live_result_private": wsta160.is_under(wsta149_path, PRIVATE_ROOT),
            "wsta167_source_gate_private": wsta160.is_under(wsta167_path, PRIVATE_ROOT),
            "wsta196_result_present": wsta196_result_path.is_file(),
            "wsta196_source_gate_present": wsta196_source_gate_path.is_file(),
            "wsta149_live_result_present": wsta149_path.is_file(),
            "wsta167_source_gate_present": wsta167_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in (
        "explicit_gate",
        "wsta196_result_private",
        "wsta196_source_gate_private",
        "wsta149_live_result_private",
        "wsta167_source_gate_private",
        "wsta196_result_present",
        "wsta196_source_gate_present",
        "wsta149_live_result_present",
        "wsta167_source_gate_present",
    ):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    wsta196_result = load_json(wsta196_result_path)
    source_gate = load_json(wsta196_source_gate_path)
    wsta149_result = load_json(wsta149_path)
    wsta167_result = load_json(wsta167_path)
    result["wsta196_result_checks"] = validate_wsta196_result(wsta196_result, wsta196_source_gate_path)
    result["wsta196_source_gate_checks"] = validate_wsta196_source_gate(source_gate)
    result["wsta149_live_transport_checks"] = validate_wsta149_live(wsta149_result)
    result["wsta167_seccomp_asset_gate_checks"] = validate_wsta167_source_gate(wsta167_result)
    result["checks"].update({
        "wsta196_result_valid": all(result["wsta196_result_checks"].values()),
        "wsta196_source_gate_valid": all(result["wsta196_source_gate_checks"].values()),
        "wsta149_live_transport_valid": all(result["wsta149_live_transport_checks"].values()),
        "wsta167_seccomp_asset_gate_valid": all(result["wsta167_seccomp_asset_gate_checks"].values()),
    })
    transport_gate = build_transport_gate(
        run_dir,
        wsta196_result_path,
        wsta196_source_gate_path,
        wsta149_path,
        wsta167_path,
        source_gate,
    )
    result["transport_gate_checks"] = validate_transport_gate(transport_gate)
    result["checks"]["transport_gate_valid"] = all(result["transport_gate_checks"].values())
    result["transport"] = {
        "transport_gate_json": rel(run_dir / TRANSPORT_JSON_NAME),
        "transport_gate_markdown": rel(run_dir / TRANSPORT_MD_NAME),
        "state": transport_gate["state"],
        "selected_transport": SELECTED_TRANSPORT,
        "canary_service": transport_gate["canary_service"],
        "ready_for_wsta198_transport_adapter": True,
        "ready_for_wsta196_live_execute": False,
        "wsta196_direct_host_subprocess_execute_allowed": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
    }
    result["decision"] = classify(result)
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    if result["decision"] == PASS_DECISION:
        write_json(run_dir / TRANSPORT_JSON_NAME, transport_gate)
        write_text(run_dir / TRANSPORT_MD_NAME, transport_markdown(transport_gate))
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta196-result-json", type=Path, default=DEFAULT_WSTA196_RESULT)
    parser.add_argument("--wsta196-source-gate-json", type=Path, default=DEFAULT_WSTA196_SOURCE_GATE)
    parser.add_argument("--wsta149-live-result-json", type=Path, default=DEFAULT_WSTA149_LIVE_RESULT)
    parser.add_argument("--wsta167-source-gate-json", type=Path, default=DEFAULT_WSTA167_SOURCE_GATE)
    parser.add_argument("--emit-wsta197-seccomp-load-canary-transport-gate", action="store_true")
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
        payload = {"decision": "wsta197-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
