#!/usr/bin/env python3
"""WSTA153 host-only seccomp policy source from live syscall baselines.

Consumes a WSTA108 operator status bundle that already folded the WSTA114,
WSTA125, WSTA149, and WSTA151 live syscall proofs.  Emits a deterministic
source-only seccomp policy draft:

  * one observed allowlist per service profile;
  * default-deny posture and a clear "not enforced" state;
  * fail-closed checks that all remaining syscall profiles are retired.

This unit does not build, load, or enforce seccomp filters.
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

import run_wsta108_operator_server_status as wsta108  # noqa: E402


REPO_ROOT = wsta108.REPO_ROOT
PRIVATE_ROOT = wsta108.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta108.DEFAULT_RUN_BASE
DEFAULT_WSTA108_STATUS = (
    DEFAULT_RUN_BASE
    / "wsta152-operator-status-dropbear-admin-syscall-v2-20260705T1158KST"
    / "wsta108_operator_server_status.json"
)
PASS_DECISION = "wsta153-seccomp-policy-source-pass"
RESULT_NAME = "wsta153_seccomp_policy.json"
SUMMARY_NAME = "wsta153_result.json"


def rel(path: Path) -> str:
    return wsta108.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta108.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "policy": result.get("policy", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def unique_sorted_syscalls(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    names = {str(item) for item in values if isinstance(item, str) and item}
    return sorted(names)


def service_policy(*,
                   service: str,
                   profile_name: str,
                   source: dict[str, Any],
                   source_state: str,
                   identity: dict[str, Any],
                   network_scope: str,
                   notes: list[str]) -> dict[str, Any]:
    allowlist = unique_sorted_syscalls(source.get("syscall_names"))
    return {
        "service": service,
        "profile_name": profile_name,
        "source_state": source_state,
        "source_proof_run_dir": source.get("proof_run_dir"),
        "architecture": "aarch64",
        "profile_class": "observed-live-baseline",
        "default_action": "ERRNO(EPERM)",
        "allowlist": allowlist,
        "allowlist_count": len(allowlist),
        "observed_syscall_count": int(source.get("syscall_count") or 0),
        "deny_by_default": True,
        "kill_process_on_violation": False,
        "enforcement": {
            "enabled": False,
            "reason": "WSTA153 source policy only; no seccomp filter loaded",
            "next_gate": "build launcher integration with fail-open logging or bounded fail-closed live proof",
        },
        "identity": identity,
        "network_scope": network_scope,
        "no_new_privs": source.get("no_new_privs"),
        "cap_eff_zero": source.get("cap_eff_zero"),
        "trace_artifacts_saved": bool(source.get("trace_artifacts_saved")),
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "notes": notes,
    }


def hardening(status: dict[str, Any]) -> dict[str, Any]:
    server_status = status.get("server_status") if isinstance(status.get("server_status"), dict) else {}
    return server_status.get("hardening") if isinstance(server_status.get("hardening"), dict) else {}


def baseline_sources(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    h = hardening(status)
    hud_presenter = h.get("hud_presenter_model") if isinstance(h.get("hud_presenter_model"), dict) else {}
    hud_intent = (
        hud_presenter.get("intent_syscall_trace_proof")
        if isinstance(hud_presenter.get("intent_syscall_trace_proof"), dict)
        else {}
    )
    return {
        "dpublic-smoke-httpd": h.get("syscall_trace_proof")
        if isinstance(h.get("syscall_trace_proof"), dict)
        else {},
        "cloudflared-quick-tunnel": h.get("cloudflared_runtime")
        if isinstance(h.get("cloudflared_runtime"), dict)
        else {},
        "dropbear-admin-usb": h.get("dropbear_admin_syscall_trace_proof")
        if isinstance(h.get("dropbear_admin_syscall_trace_proof"), dict)
        else {},
        "dpublic-hud-intent": hud_intent,
    }


def validate_status(status: dict[str, Any]) -> dict[str, bool]:
    h = hardening(status)
    policy = h.get("global_policy") if isinstance(h.get("global_policy"), dict) else {}
    syscall_trace = h.get("syscall_trace_proof") if isinstance(h.get("syscall_trace_proof"), dict) else {}
    sources = baseline_sources(status)
    return {
        "status_decision_pass": status.get("decision") == wsta108.PASS_DECISION,
        "server_ready_default_off": (
            status.get("server_status", {}).get("state")
            == "SERVER_PROFILE_READY_DEFAULT_OFF"
        ),
        "seccomp_profile_source_ready": bool(policy.get("seccomp_ready_for_profile_source")),
        "remaining_syscall_profiles_retired": syscall_trace.get("remaining_profiles") == [],
        "smoke_syscall_live_proven": bool(
            sources["dpublic-smoke-httpd"].get("smoke_syscall_trace_live_proven")
        ),
        "cloudflared_runtime_live_proven": bool(
            sources["cloudflared-quick-tunnel"].get("cloudflared_live_proven")
        ),
        "dropbear_admin_syscall_live_proven": bool(
            sources["dropbear-admin-usb"].get("dropbear_admin_syscall_trace_live_proven")
        ),
        "hud_intent_syscall_live_proven": bool(
            sources["dpublic-hud-intent"].get("hud_intent_syscall_trace_live_proven")
        ),
        "all_sources_have_full_syscall_lists": all(
            bool(unique_sorted_syscalls(source.get("syscall_names")))
            for source in sources.values()
        ),
        "redaction_clean": not bool(wsta108.redaction_findings(public_summary({"policy": status}))),
    }


def build_policy(status_path: Path, status: dict[str, Any]) -> dict[str, Any]:
    sources = baseline_sources(status)
    smoke = sources["dpublic-smoke-httpd"]
    cloudflared = sources["cloudflared-quick-tunnel"]
    dropbear = sources["dropbear-admin-usb"]
    hud_intent = sources["dpublic-hud-intent"]
    services = [
        service_policy(
            service="dpublic-smoke-httpd",
            profile_name="seccomp-dpublic-smoke-httpd-observed-v1",
            source=smoke,
            source_state=str(smoke.get("state")),
            identity={
                "user": "a90www",
                "uid": 3901,
                "gid": 3901,
                "privilege_model": "non-root-loopback-http",
            },
            network_scope="loopback-127.0.0.1:8080-only",
            notes=[
                "Observed through WSTA114 smoke-service-only strace.",
                "Candidate allowlist is exact observed baseline; enforce only after bounded live proof.",
            ],
        ),
        service_policy(
            service="cloudflared-quick-tunnel",
            profile_name="seccomp-cloudflared-quick-tunnel-observed-v1",
            source=cloudflared,
            source_state=str(cloudflared.get("state")),
            identity={
                "user": cloudflared.get("user"),
                "uid": cloudflared.get("uid"),
                "gid": cloudflared.get("gid"),
                "privilege_model": "non-root-outbound-client",
            },
            network_scope="outbound-only-plus-loopback-origin",
            notes=[
                "Observed through WSTA125 native-upstream cloudflared runtime proof.",
                "Public URL values remain private/redacted; policy artifact contains no URL.",
            ],
        ),
        service_policy(
            service="dropbear-admin-usb",
            profile_name="seccomp-dropbear-admin-usb-observed-v1",
            source=dropbear,
            source_state=str(dropbear.get("state")),
            identity={
                "user": "root-boundary-daemon",
                "admin_user": "a90admin",
                "admin_uid": dropbear.get("uid"),
                "admin_gid": dropbear.get("gid"),
                "privilege_model": dropbear.get("daemon_privilege_model"),
            },
            network_scope=str(dropbear.get("network_scope") or "usb-ncm-admin-only"),
            notes=[
                "Observed through WSTA151 Dropbear admin USB trace.",
                "Root-boundary daemon needs a separate loader decision before enforcement.",
                "Root SSH remains disabled; admin login is a90admin key-only.",
            ],
        ),
        service_policy(
            service="dpublic-hud-intent",
            profile_name="seccomp-dpublic-hud-intent-observed-v1",
            source=hud_intent,
            source_state=str(hud_intent.get("state")),
            identity={
                "user": "a90hud",
                "uid": hud_intent.get("uid"),
                "gid": hud_intent.get("gid"),
                "privilege_model": "non-root-intent-producer",
            },
            network_scope="no-network-intent-file-only",
            notes=[
                "Observed through WSTA149 HUD intent producer trace.",
                "Native init remains KMS owner; this profile is for the Debian intent producer only.",
            ],
        ),
    ]
    return {
        "schema": "a90-wsta153-seccomp-policy-source-v1",
        "state": "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES",
        "source_status_json": rel(status_path),
        "enforcement_state": "SOURCE_ONLY_NOT_ENFORCED",
        "default_action": "ERRNO(EPERM)",
        "architecture": "aarch64",
        "services": services,
        "service_count": len(services),
        "excluded_boundaries": [
            {
                "name": "wsta-native-uplink-helper",
                "reason": "native-owned credential and Wi-Fi control boundary; not a Debian service seccomp profile",
            },
            {
                "name": "native-dpublic-hud-presenter",
                "reason": "native-init KMS owner; Debian seccomp profile covers only dpublic-hud-intent",
            },
        ],
        "next_live_gate": {
            "required": True,
            "suggested_unit": "WSTA154",
            "scope": "launcher-side seccomp dry-run/enforcement design before any filter load",
        },
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }


def validate_policy(policy: dict[str, Any]) -> dict[str, bool]:
    services = policy.get("services") if isinstance(policy.get("services"), list) else []
    names = [item.get("service") for item in services if isinstance(item, dict)]
    return {
        "schema_ok": policy.get("schema") == "a90-wsta153-seccomp-policy-source-v1",
        "source_only_not_enforced": policy.get("enforcement_state") == "SOURCE_ONLY_NOT_ENFORCED",
        "service_count_four": len(services) == 4,
        "expected_services_present": set(names) == {
            "dpublic-smoke-httpd",
            "cloudflared-quick-tunnel",
            "dropbear-admin-usb",
            "dpublic-hud-intent",
        },
        "all_profiles_default_deny": all(
            isinstance(item, dict)
            and item.get("deny_by_default") is True
            and item.get("default_action") == "ERRNO(EPERM)"
            for item in services
        ),
        "all_allowlists_nonempty": all(
            isinstance(item, dict)
            and isinstance(item.get("allowlist"), list)
            and bool(item["allowlist"])
            for item in services
        ),
        "all_profiles_not_enforced": all(
            isinstance(item, dict)
            and isinstance(item.get("enforcement"), dict)
            and item["enforcement"].get("enabled") is False
            for item in services
        ),
        "redaction_clean": not bool(wsta108.redaction_findings(policy)),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta153-seccomp-policy-source-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    status_path = resolve_path(args.wsta108_operator_status_json)
    result: dict[str, Any] = {
        "scope": "WSTA153 host-only seccomp policy source from live baselines",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_seccomp_policy_source),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "status_json_private": is_under(status_path, PRIVATE_ROOT),
            "status_json_present": status_path.is_file(),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta153-blocked-explicit-gate-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta153-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["status_json_private"]:
        result["decision"] = "wsta153-blocked-status-json-nonprivate"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["status_json_present"]:
        result["decision"] = "wsta153-blocked-status-json-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result

    status = load_json(status_path)
    status_checks = validate_status(status)
    result["status_checks"] = status_checks
    result["checks"].update({f"status_{key}": value for key, value in status_checks.items()})
    if not all(status_checks.values()):
        result["decision"] = "wsta153-blocked-status-not-ready-for-seccomp-policy"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    policy = build_policy(status_path, status)
    policy_checks = validate_policy(policy)
    result["policy"] = policy
    result["policy_checks"] = policy_checks
    result["checks"].update({f"policy_{key}": value for key, value in policy_checks.items()})
    result["decision"] = PASS_DECISION if all(policy_checks.values()) else "wsta153-blocked-policy-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / RESULT_NAME, policy)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta108-operator-status-json", type=Path, default=DEFAULT_WSTA108_STATUS)
    parser.add_argument("--emit-seccomp-policy-source", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta153-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
