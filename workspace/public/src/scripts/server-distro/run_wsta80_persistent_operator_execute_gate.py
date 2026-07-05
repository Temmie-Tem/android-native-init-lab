#!/usr/bin/env python3
"""WSTA80 host-only persistent operator execute gate.

WSTA79 says whether a WSTA78 operator packet is still current.  WSTA80 is the
last fail-closed gate before a separately selected WSTA58 live run: it consumes
a private WSTA79 READY status, reloads the referenced WSTA78 operator packet,
validates the WSTA58 command template, and writes a default-off execution gate.

Default execution is host-only preflight.  Optional WSTA58 delegation exists
only behind the full explicit WSTA58 live acknowledgement stack; no token value
is written to WSTA80 public output.
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

import run_wsta58_renewal_manual_stop_proof as wsta58  # noqa: E402
import run_wsta79_persistent_operator_packet_status as wsta79  # noqa: E402


REPO_ROOT = wsta79.REPO_ROOT
PRIVATE_ROOT = wsta79.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta79.DEFAULT_RUN_BASE
PREFLIGHT_DECISION = "wsta80-persistent-operator-execute-gate-preflight-pass"
PASS_DECISION = "wsta80-persistent-operator-execute-gate-live-pass"


def rel(path: Path) -> str:
    return wsta79.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return wsta79.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta79.is_under(path, root)


def live_requested(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "execute_wsta58_from_status", False))


def safety_flags(args: argparse.Namespace, gate_ok: bool = False) -> dict[str, Any]:
    requested = live_requested(args)
    return {
        "device_action": requested and gate_ok,
        "boot_flash": False,
        "native_reboot": requested and gate_ok and bool(args.allow_native_reboot),
        "wifi_connect": "wsta58-explicit-live-gated" if requested and gate_ok else False,
        "dhcp": "wsta58-explicit-live-gated" if requested and gate_ok else False,
        "public_tunnel": "wsta58-explicit-public-live-gated" if requested and gate_ok else False,
        "public_smoke": "wsta58-explicit-public-live-gated" if requested and gate_ok else False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def cloudflared_egress_enabled(args: argparse.Namespace) -> bool:
    return wsta58.cloudflared_egress_enabled(args)


def cloudflared_egress_dns4_values(args: argparse.Namespace) -> list[str]:
    return wsta58.cloudflared_egress_dns4_values(args)


def cloudflared_egress_tls4_values(args: argparse.Namespace) -> list[str]:
    return wsta58.cloudflared_egress_tls4_values(args)


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA80 host-only persistent operator execute gate",
        "default_mode": "host-only-preflight",
        "input": "workspace/private/runs/server-distro/<wsta79-run>/wsta79_operator_packet_status.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta79-operator-packet-status-json",
            "workspace/private/runs/server-distro/<wsta79-run>/wsta79_operator_packet_status.json",
        ],
        "optional_live_execution": [
            "--execute-wsta58-from-status",
            "--allow-operator-live",
            "--allow-native-reboot",
            "--allow-public-live",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--ack-packet-filter-mutation",
            "--force-packet-filter-restore-proof",
            "--force-ttl-expiry-proof",
            "--force-manual-stop-proof",
            "--native-confirm-token",
            "<native-confirm-token>",
            "--public-confirm-token",
            "<public-confirm-token>",
        ],
        "optional_cloudflared_egress_allowlist": [
            "--enable-cloudflared-egress-allowlist",
            "--force-cloudflared-egress-allowlist-proof",
            "--cloudflared-egress-dns4",
            "<redacted-dns-route>",
            "--cloudflared-egress-tls4",
            "<redacted-tls-route>",
        ],
        "live_execution": "not-run-by-default",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "execute_gate": result.get("execute_gate", {}),
        "wsta58_redacted": result.get("wsta58_redacted", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta79.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta80-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta80-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta80-blocked-{label}-missing"
    return path, None


def validate_status(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta80-blocked-status-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta79.PASS_DECISION:
        return False, "wsta80-blocked-status-not-pass", {"decision": payload.get("decision")}
    status = payload.get("operator_packet_status")
    if not isinstance(status, dict):
        return False, "wsta80-blocked-status-missing", {}
    if status.get("state") != "READY_TO_RUN_DEFAULT_OFF" or status.get("ready_for_live") is not True:
        return False, "wsta80-blocked-status-not-ready", {
            "state": status.get("state"),
            "ready_for_live": status.get("ready_for_live"),
        }
    if status.get("wsta78_recheck_decision") != wsta79.wsta78.PASS_DECISION:
        return False, "wsta80-blocked-wsta78-recheck-not-pass", {
            "wsta78_recheck_decision": status.get("wsta78_recheck_decision"),
        }
    if status.get("packet_match") is not True or status.get("template_match") is not True:
        return False, "wsta80-blocked-status-drift", {
            "packet_match": status.get("packet_match"),
            "template_match": status.get("template_match"),
        }
    if status.get("packet_filter_hardening_ready") is not True:
        return False, "wsta80-blocked-packet-filter-hardening-not-ready", {
            "packet_filter_hardening_ready": status.get("packet_filter_hardening_ready"),
        }
    if status.get("live_execution_requested") is not False:
        return False, "wsta80-blocked-status-live-execution-requested", {}
    if status.get("public_url_value_logged") is not False:
        return False, "wsta80-blocked-status-public-url-logged", {}
    if status.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta80-blocked-status-secret-values-logged", {}
    packet_path, path_error = require_private_path(status.get("wsta78_operator_packet"), "wsta78-operator-packet")
    if path_error or packet_path is None:
        return False, path_error or "wsta80-blocked-wsta78-operator-packet", {}
    return True, "ok", {"payload": payload, "status": status, "packet_path": packet_path}


def validate_operator_packet(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta80-blocked-operator-packet-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta79.wsta78.PASS_DECISION:
        return False, "wsta80-blocked-operator-packet-not-pass", {"decision": payload.get("decision")}
    packet = payload.get("operator_packet")
    if not isinstance(packet, dict):
        return False, "wsta80-blocked-operator-packet-missing", {}
    if packet.get("state") != "READY_OPERATOR_PACKET_DEFAULT_OFF" or packet.get("ready_for_live") is not True:
        return False, "wsta80-blocked-operator-packet-not-ready", {"state": packet.get("state")}
    if packet.get("live_execution_requested") is not False:
        return False, "wsta80-blocked-operator-packet-live-execution-requested", {}
    if packet.get("public_url_value_logged") is not False:
        return False, "wsta80-blocked-operator-packet-public-url-logged", {}
    if packet.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta80-blocked-operator-packet-secret-values-logged", {}
    if not wsta79.packet_filter_hardening_ready(packet):
        return False, "wsta80-blocked-operator-packet-filter-hardening-missing", {
            "packet_filter_hardening": packet.get("packet_filter_hardening"),
        }
    command = packet.get("wsta58_live_command_template")
    if not isinstance(command, list) or not command:
        return False, "wsta80-blocked-command-template-missing", {}
    command_text = json.dumps(command)
    if "<native-confirm-token>" not in command_text or "<public-confirm-token>" not in command_text:
        return False, "wsta80-blocked-command-template-placeholders-missing", {}
    if wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN in command_text:
        return False, "wsta80-blocked-native-confirm-token-value-logged", {}
    if wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN in command_text:
        return False, "wsta80-blocked-public-confirm-token-value-logged", {}
    if redaction_findings({"command": command}):
        return False, "wsta80-blocked-command-template-redaction-finding", {}
    return True, "ok", {"payload": payload, "packet": packet, "command": command}


def gate_from_status(status_path: Path,
                     status: dict[str, Any],
                     packet_path: Path,
                     packet: dict[str, Any],
                     out_json: Path,
                     out_md: Path) -> dict[str, Any]:
    return {
        "state": "READY_FOR_EXPLICIT_WSTA58_LIVE_GATE",
        "wsta79_operator_packet_status": rel(status_path),
        "wsta78_operator_packet": rel(packet_path),
        "selected_wsta76_launch_brief": status.get("selected_wsta76_launch_brief"),
        "selected_wsta73_arming_packet": status.get("selected_wsta73_arming_packet"),
        "initial_seconds_remaining": status.get("initial_seconds_remaining"),
        "wsta78_recheck_decision": status.get("wsta78_recheck_decision"),
        "packet_match": status.get("packet_match"),
        "template_match": status.get("template_match"),
        "wsta58_live_command_template": packet.get("wsta58_live_command_template"),
        "operator_required_replacements": packet.get("operator_required_replacements") or [],
        "operator_acknowledgements_required": packet.get("operator_acknowledgements_required") or [],
        "abort_conditions": packet.get("abort_conditions") or [],
        "cleanup_expectations": packet.get("cleanup_expectations") or [],
        "packet_filter_hardening": status.get("packet_filter_hardening") or packet.get("packet_filter_hardening"),
        "packet_filter_hardening_ready": status.get("packet_filter_hardening_ready"),
        "execution_guardrails": [
            "wsta80-does-not-execute-live-by-default",
            "wsta79-status-must-be-current-ready",
            "replace-placeholders-out-of-band-only",
            "explicit-wsta58-gate-required",
            "packet-filter-helper-preflight-required",
            "packet-filter-apply-before-public-exposure",
            "packet-filter-restore-required-on-stop-retire-failure",
            "abort-if-packet-filter-restore-proof-missing",
            "verify-public-off-after-wsta58",
        ],
        "recommended_next_action": "operator-may-run-explicit-wsta58-live-gate-from-wsta80",
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(gate: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in gate.get("wsta58_live_command_template") or [])
    lines = [
        "# WSTA Persistent Operator Execute Gate",
        "",
        f"- State: `{gate.get('state')}`",
        f"- WSTA79 status: `{gate.get('wsta79_operator_packet_status')}`",
        f"- WSTA78 packet: `{gate.get('wsta78_operator_packet')}`",
        f"- Selected WSTA76 brief: `{gate.get('selected_wsta76_launch_brief')}`",
        f"- Selected WSTA73 packet: `{gate.get('selected_wsta73_arming_packet')}`",
        f"- Initial seconds remaining: `{gate.get('initial_seconds_remaining')}`",
        f"- Packet match: `{str(bool(gate.get('packet_match'))).lower()}`",
        f"- Template match: `{str(bool(gate.get('template_match'))).lower()}`",
        f"- Packet filter hardening ready: `{str(bool(gate.get('packet_filter_hardening_ready'))).lower()}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Packet Filter Hardening",
        "",
    ]
    hardening = gate.get("packet_filter_hardening") if isinstance(gate.get("packet_filter_hardening"), dict) else {}
    lines.extend([
        f"- State: `{hardening.get('state')}`",
        f"- Backend: `{hardening.get('backend')}`",
        f"- Policy: `{hardening.get('policy')}`",
        f"- Apply before: `{hardening.get('apply_before')}`",
        f"- Restore on: `{', '.join(str(item) for item in hardening.get('restore_on') or [])}`",
        "",
        "## Execution Guardrails",
        "",
    ])
    for item in gate.get("execution_guardrails", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## WSTA58 Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "This gate does not run WSTA58 unless the explicit WSTA80 live delegation flags are supplied.",
        "",
    ])
    return "\n".join(lines)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_wsta58_from_status:
        return False, "wsta80-blocked-execute-wsta58-from-status-required"
    if not args.allow_operator_live:
        return False, "wsta80-blocked-operator-live-allow-required"
    if not args.allow_native_reboot:
        return False, "wsta80-blocked-native-reboot-allow-required"
    if not args.allow_public_live:
        return False, "wsta80-blocked-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta80-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta80-blocked-public-exposure-ack-required"
    if not args.ack_packet_filter_mutation:
        return False, "wsta80-blocked-packet-filter-mutation-ack-required"
    if not args.force_packet_filter_restore_proof:
        return False, "wsta80-blocked-packet-filter-restore-proof-required"
    if not args.force_ttl_expiry_proof:
        return False, "wsta80-blocked-ttl-expiry-proof-required"
    if not args.force_manual_stop_proof:
        return False, "wsta80-blocked-manual-stop-proof-required"
    if cloudflared_egress_enabled(args):
        if not args.force_cloudflared_egress_allowlist_proof:
            return False, "wsta80-blocked-cloudflared-egress-allowlist-proof-required"
        if not cloudflared_egress_dns4_values(args) or not cloudflared_egress_tls4_values(args):
            return False, "wsta80-blocked-cloudflared-egress-route-required"
    if args.native_confirm_token != wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta80-blocked-native-confirm-token-required"
    if args.public_confirm_token != wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN:
        return False, "wsta80-blocked-public-confirm-token-required"
    return True, "ok"


def command_with_live_tokens(command: list[Any], args: argparse.Namespace, run_dir: Path) -> argparse.Namespace:
    argv = [str(part) for part in command]
    if len(argv) >= 2 and argv[0].endswith("python3"):
        argv = argv[2:]
    elif argv and argv[0].endswith("run_wsta58_renewal_manual_stop_proof.py"):
        argv = argv[1:]
    replaced: list[str] = []
    skip_next = False
    for part in argv:
        if skip_next:
            skip_next = False
            continue
        if part == "--run-dir":
            skip_next = True
            continue
        if part == "<native-confirm-token>":
            replaced.append(args.native_confirm_token)
        elif part == "<public-confirm-token>":
            replaced.append(args.public_confirm_token)
        else:
            replaced.append(part)
    replaced.extend(["--run-dir", str(run_dir / "wsta58-from-status")])
    for enabled, flag in (
        (args.ack_packet_filter_mutation, "--ack-packet-filter-mutation"),
        (args.force_packet_filter_restore_proof, "--force-packet-filter-restore-proof"),
    ):
        if enabled and flag not in replaced:
            replaced.append(flag)
    if cloudflared_egress_enabled(args):
        for flag in (
            "--enable-cloudflared-egress-allowlist",
            "--force-cloudflared-egress-allowlist-proof",
        ):
            if flag not in replaced:
                replaced.append(flag)
        for value in cloudflared_egress_dns4_values(args):
            replaced.extend(["--cloudflared-egress-dns4", value])
        for value in cloudflared_egress_tls4_values(args):
            replaced.extend(["--cloudflared-egress-tls4", value])
    replaced.extend([
        "--local-image",
        str(args.local_image),
        "--local-image-sha256",
        args.local_image_sha256,
        "--remote-image",
        args.remote_image,
        "--remote-clean-image",
        args.remote_clean_image,
    ])
    return wsta58.build_arg_parser().parse_args(replaced)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta80-persistent-operator-execute-gate-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA80 host-only persistent operator execute gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta80-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(args),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta80-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta80_execute_gate.json"
    out_md = run_dir / "wsta80_execute_gate.md"

    if args.wsta79_operator_packet_status_json is None:
        result["decision"] = "wsta80-blocked-status-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    status_path, path_error = require_private_path(args.wsta79_operator_packet_status_json, "status")
    if path_error or status_path is None:
        result["decision"] = path_error or "wsta80-blocked-status"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    status_ok, status_decision, status_detail = validate_status(status_path)
    if not status_ok:
        result["decision"] = status_decision
        result["gate_decision"] = status_decision
        result["gate_detail"] = status_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    packet_ok, packet_decision, packet_detail = validate_operator_packet(status_detail["packet_path"])
    if not packet_ok:
        result["decision"] = packet_decision
        result["gate_decision"] = packet_decision
        result["gate_detail"] = packet_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    gate = gate_from_status(
        status_path,
        status_detail["status"],
        status_detail["packet_path"],
        packet_detail["packet"],
        out_json,
        out_md,
    )
    result.update({
        "decision": PREFLIGHT_DECISION,
        "gate_decision": "preflight-ready",
        "execute_gate": gate,
        "checks": {
            "wsta79_status_ready": True,
            "wsta78_packet_ready": True,
            "wsta58_template_placeholder_only": True,
            "packet_filter_hardening_ready": True,
            "explicit_live_gate": False,
            "live_execution_requested": False,
            "default_public_off": True,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(gate)
    findings = redaction_findings(public_summary(result)) + redaction_findings({"markdown": md_text})
    if findings:
        result["decision"] = "wsta80-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    if not args.execute_wsta58_from_status:
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        write_text(out_md, md_text)
        return result

    gate_ok, gate_decision = explicit_live_gate(args)
    result["gate_decision"] = gate_decision
    result["safety"] = safety_flags(args, gate_ok)
    result["checks"]["live_execution_requested"] = True
    result["checks"]["explicit_live_gate"] = gate_ok
    result["checks"]["ack_packet_filter_mutation"] = bool(args.ack_packet_filter_mutation)
    result["checks"]["force_packet_filter_restore_proof"] = bool(args.force_packet_filter_restore_proof)
    result["checks"]["cloudflared_egress_allowlist_enabled"] = cloudflared_egress_enabled(args)
    result["checks"]["force_cloudflared_egress_allowlist_proof"] = bool(
        args.force_cloudflared_egress_allowlist_proof
    )
    result["checks"]["cloudflared_egress_dns4_count"] = len(cloudflared_egress_dns4_values(args))
    result["checks"]["cloudflared_egress_tls4_count"] = len(cloudflared_egress_tls4_values(args))
    result["checks"]["cloudflared_egress_route_values_redacted"] = True
    if not gate_ok:
        result["decision"] = gate_decision
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    wsta58_args = command_with_live_tokens(packet_detail["command"], args, run_dir)
    delegated = wsta58.run(wsta58_args)
    result["wsta58_redacted"] = wsta58.public_summary(delegated)
    result["checks"]["wsta58_pass"] = delegated.get("decision") == wsta58.PASS_DECISION
    result["decision"] = PASS_DECISION if result["checks"]["wsta58_pass"] else "wsta80-blocked-wsta58-delegation"
    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta79-operator-packet-status-json", type=Path)
    parser.add_argument("--execute-wsta58-from-status", action="store_true")
    parser.add_argument("--allow-operator-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--ack-packet-filter-mutation", action="store_true")
    parser.add_argument("--force-packet-filter-restore-proof", action="store_true")
    parser.add_argument("--force-ttl-expiry-proof", action="store_true")
    parser.add_argument("--force-manual-stop-proof", action="store_true")
    parser.add_argument("--enable-cloudflared-egress-allowlist", action="store_true")
    parser.add_argument("--force-cloudflared-egress-allowlist-proof", action="store_true")
    parser.add_argument("--cloudflared-egress-dns4", action="append", default=[])
    parser.add_argument("--cloudflared-egress-tls4", action="append", default=[])
    parser.add_argument("--local-image", type=Path, default=wsta58.wsta55.wsta45.wsta43.wsta42.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=wsta58.wsta55.wsta45.wsta43.wsta42.DEFAULT_LOCAL_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=wsta58.wsta55.wsta45.wsta43.wsta42.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta58.wsta55.wsta45.wsta43.wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
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
        payload = {"decision": "wsta80-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
