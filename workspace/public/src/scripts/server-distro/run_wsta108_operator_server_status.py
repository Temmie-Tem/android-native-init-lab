#!/usr/bin/env python3
"""WSTA108 host-only operator server status bundle.

WSTA88 proves the default-off public workflow.  WSTA90 sketches the service
hardening contract.  WSTA108 combines those two public surfaces into one
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


REPO_ROOT = wsta88.REPO_ROOT
PRIVATE_ROOT = wsta88.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta88.DEFAULT_RUN_BASE
PASS_DECISION = "wsta108-operator-server-status-source-pass"


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


def compact_hardening(manifest_result: dict[str, Any] | None) -> dict[str, Any]:
    if not manifest_result:
        return {
            "state": "NOT_SUPPLIED",
            "service_count": 0,
            "global_policy": {},
            "blocking_before_enforcement": [],
        }
    manifest = manifest_result.get("manifest") if isinstance(manifest_result.get("manifest"), dict) else {}
    services = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    global_policy = manifest.get("global_policy") if isinstance(manifest.get("global_policy"), dict) else {}
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
        "blocking_before_enforcement": list(manifest.get("blocking_before_enforcement") or []),
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


def build_server_status(wsta88_result: dict[str, Any], hardening_result: dict[str, Any] | None) -> dict[str, Any]:
    status_hud = wsta88_result.get("status_hud") if isinstance(wsta88_result.get("status_hud"), dict) else {}
    if not status_hud:
        workflow = wsta88_result.get("workflow") if isinstance(wsta88_result.get("workflow"), dict) else {}
        status_hud = workflow.get("status_hud") if isinstance(workflow.get("status_hud"), dict) else {}
    packet_filter = status_hud.get("packet_filter") if isinstance(status_hud.get("packet_filter"), dict) else {}
    hardening = compact_hardening(hardening_result)
    public_off = (status_hud.get("public_state") or "PUBLIC_OFF") == "PUBLIC_OFF"
    ready_default_off = public_off and bool(packet_filter.get("ready"))
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
        "operator_next_actions": [
            "keep-public-exposure-default-off",
            "use-explicit-wsta88-live-gate-only-when-attended",
            "apply-service-hardening-before-any-always-on-public-profile",
        ],
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
        "",
        "## Hardening",
        "",
        f"- State: `{hardening.get('state')}`",
        f"- Service count: `{hardening.get('service_count')}`",
        f"- No-new-privs default: `{str(bool(hardening_policy.get('no_new_privs_default'))).lower()}`",
        f"- Capability drop required: `{str(bool(hardening_policy.get('capability_drop_required'))).lower()}`",
        f"- Seccomp ready for profile source: `{str(bool(hardening_policy.get('seccomp_ready_for_profile_source'))).lower()}`",
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

    server_status = build_server_status(wsta88_result, hardening_result)
    result["server_status"] = server_status
    result["checks"] = {
        "wsta88_workflow_pass": True,
        "status_hud_present": bool(server_status.get("exposure")),
        "public_state_off": server_status["exposure"].get("public_state") == "PUBLIC_OFF",
        "packet_filter_ready": bool(server_status["packet_filter"].get("ready")),
        "hardening_manifest_supplied": hardening_result is not None,
        "default_public_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
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
