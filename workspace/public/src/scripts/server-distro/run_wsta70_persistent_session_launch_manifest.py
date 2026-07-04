#!/usr/bin/env python3
"""WSTA70 host-only persistent session launch manifest.

WSTA67 inventories can contain READY sessions, but a READY row is only a
candidate.  WSTA70 selects one READY candidate, revalidates it through WSTA65 at
the current time, then emits a private operator launch manifest containing the
redacted WSTA58 command template with token placeholders.

It never executes the WSTA58 live gate.  It performs no device action, native
reboot, Wi-Fi association, DHCP, public tunnel, public smoke, userdata action,
switch-root, or flash.
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

import run_wsta65_persistent_session_status as wsta65  # noqa: E402
import run_wsta67_persistent_session_inventory as wsta67  # noqa: E402


REPO_ROOT = wsta67.REPO_ROOT
PRIVATE_ROOT = wsta67.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta67.DEFAULT_RUN_BASE
PASS_DECISION = "wsta70-persistent-session-launch-manifest-pass"


def rel(path: Path) -> str:
    return wsta67.rel(path)


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
    return wsta67.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta67.is_under(path, root)


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA70 host-only persistent session launch manifest",
        "default_mode": "host-only-select-ready-session",
        "input": "workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta67-inventory-json",
            "workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json",
            "--ready-index",
            "0",
        ],
        "live_execution": "not-run-by-wsta70",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "launch_manifest": result.get("launch_manifest", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta67.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta70-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta70-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta70-blocked-{label}-missing"
    return path, None


def validate_inventory(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta70-blocked-inventory-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta67.PASS_DECISION:
        return False, "wsta70-blocked-inventory-not-pass", {"decision": payload.get("decision")}
    inventory = payload.get("inventory")
    if not isinstance(inventory, dict):
        return False, "wsta70-blocked-inventory-missing", {}
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        return False, "wsta70-blocked-inventory-entries-missing", {}
    if inventory.get("invalid_session_count") not in (0, "0", None):
        return False, "wsta70-blocked-inventory-invalid-entries", {
            "invalid_session_count": inventory.get("invalid_session_count"),
        }
    if inventory.get("public_url_value_logged") is not False:
        return False, "wsta70-blocked-public-url-logged", {}
    if inventory.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta70-blocked-secret-values-logged", {}
    return True, "ok", {"payload": payload, "inventory": inventory, "entries": entries}


def ready_entries(entries: list[Any]) -> list[dict[str, Any]]:
    ready: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("session_state") == "READY" and entry.get("ready_for_live") is True:
            ready.append(entry)
    return ready


def wsta65_args(run_dir: Path,
                wsta64_result: Path,
                min_remaining: int,
                now_utc: str | None) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta64-result-json",
        str(wsta64_result),
        "--min-initial-seconds-remaining",
        str(min_remaining),
    ]
    if now_utc:
        argv.extend(["--now-utc", now_utc])
    return wsta65.build_arg_parser().parse_args(argv)


def load_wsta63_session(wsta64_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    wsta64_result = load_json(wsta64_path)
    readiness = wsta64_result.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError("wsta64 readiness object missing")
    wsta63_path, path_error = require_private_path(readiness.get("wsta63_result"), "wsta63-result")
    if path_error or wsta63_path is None:
        raise ValueError(path_error or "wsta63-result-missing")
    wsta63_result = load_json(wsta63_path)
    session = wsta63_result.get("session_redacted")
    if not isinstance(session, dict):
        raise ValueError("wsta63 session_redacted object missing")
    return wsta64_result, session, wsta63_path


def validate_command(session: dict[str, Any],
                     status: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    command = session.get("live_command_template")
    initial, initial_error = wsta65.wsta64.require_private_path(status.get("initial_private_lease_artifact"), "initial-lease")
    if initial_error or initial is None:
        return False, initial_error or "wsta70-blocked-initial-lease", {}
    renewal, renewal_error = wsta65.wsta64.require_private_path(status.get("renewal_wsta53_result"), "renewal-source")
    if renewal_error or renewal is None:
        return False, renewal_error or "wsta70-blocked-renewal-source", {}
    ok, decision, detail = wsta65.wsta64.validate_command_template(command, initial, renewal)
    return ok, decision, detail


def build_launch_manifest(inventory_path: Path,
                          ready_count: int,
                          selected_index: int,
                          selected_entry: dict[str, Any],
                          wsta64_path: Path,
                          wsta63_path: Path,
                          session: dict[str, Any],
                          status_result: dict[str, Any],
                          status_path: Path,
                          manifest_json: Path,
                          manifest_md: Path) -> dict[str, Any]:
    status = status_result.get("session_status") or {}
    return {
        "state": "PUBLIC_OFF",
        "source_inventory": rel(inventory_path),
        "ready_candidate_count": ready_count,
        "selected_ready_index": selected_index,
        "selected_wsta64_result": rel(wsta64_path),
        "selected_wsta63_result": rel(wsta63_path),
        "wsta65_revalidation_result": rel(status_path),
        "wsta65_session_state": status.get("session_state"),
        "ready_for_live": bool(status.get("ready_for_live")),
        "initial_seconds_remaining": status.get("initial_seconds_remaining"),
        "min_initial_seconds_remaining": status.get("min_initial_seconds_remaining"),
        "initial_private_lease_artifact": status.get("initial_private_lease_artifact"),
        "renewal_wsta53_result": status.get("renewal_wsta53_result"),
        "wsta58_preflight_result": status.get("wsta58_preflight_result"),
        "inventory_entry_recommended_next_action": selected_entry.get("recommended_next_action"),
        "live_command_template": session.get("live_command_template"),
        "operator_required_replacements": [
            "<native-confirm-token>",
            "<public-confirm-token>",
        ],
        "json_path": rel(manifest_json),
        "markdown_path": rel(manifest_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(manifest: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in manifest.get("live_command_template") or [])
    lines = [
        "# WSTA Persistent Session Launch Manifest",
        "",
        f"- State: `{manifest.get('state')}`",
        f"- Source inventory: `{manifest.get('source_inventory')}`",
        f"- READY candidates: `{manifest.get('ready_candidate_count')}`",
        f"- Selected READY index: `{manifest.get('selected_ready_index')}`",
        f"- WSTA65 state: `{manifest.get('wsta65_session_state')}`",
        f"- Initial seconds remaining: `{manifest.get('initial_seconds_remaining')}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Selected Session",
        "",
        f"- WSTA64 result: `{manifest.get('selected_wsta64_result')}`",
        f"- WSTA63 result: `{manifest.get('selected_wsta63_result')}`",
        f"- WSTA65 revalidation: `{manifest.get('wsta65_revalidation_result')}`",
        "",
        "## Operator Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "Replace `<native-confirm-token>` and `<public-confirm-token>` only when explicitly running the WSTA58 live gate.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta70-persistent-session-launch-manifest-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA70 host-only persistent session launch manifest",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta70-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta70-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta70_launch_manifest.json"
    out_md = run_dir / "wsta70_launch_manifest.md"

    if args.wsta67_inventory_json is None:
        result["decision"] = "wsta70-blocked-inventory-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    inventory_path, path_error = require_private_path(args.wsta67_inventory_json, "inventory")
    if path_error or inventory_path is None:
        result["decision"] = path_error or "wsta70-blocked-inventory"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    valid, decision, detail = validate_inventory(inventory_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    candidates = ready_entries(detail["entries"])
    result["candidate_summary"] = {
        "ready_candidate_count": len(candidates),
        "selected_ready_index": args.ready_index,
    }
    if not candidates:
        result["decision"] = "wsta70-blocked-no-ready-session"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if args.ready_index < 0 or args.ready_index >= len(candidates):
        result["decision"] = "wsta70-blocked-ready-index-out-of-range"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    selected = candidates[int(args.ready_index)]
    wsta64_path, selected_error = require_private_path(selected.get("wsta64_result"), "wsta64-result")
    if selected_error or wsta64_path is None:
        result["decision"] = selected_error or "wsta70-blocked-wsta64-result"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    status_dir = run_dir / "wsta65-selected"
    status_result = wsta65.run(wsta65_args(
        status_dir,
        wsta64_path,
        int(args.min_initial_seconds_remaining),
        args.now_utc,
    ))
    status_path = status_dir / "wsta65_result.json"
    status = status_result.get("session_status") or {}
    if (
        status_result.get("decision") != wsta65.PASS_DECISION
        or status.get("session_state") != "READY"
        or status.get("ready_for_live") is not True
    ):
        result["decision"] = "wsta70-blocked-selected-not-ready"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {
            "wsta65_decision": status_result.get("decision"),
            "session_state": status.get("session_state"),
            "reason": status.get("reason"),
            "wsta65_result": rel(status_path),
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    try:
        _, session, wsta63_path = load_wsta63_session(wsta64_path)
    except Exception as exc:  # noqa: BLE001
        result["decision"] = "wsta70-blocked-session-load-failed"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"error": str(exc)}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    command_ok, command_decision, command_detail = validate_command(session, status)
    if not command_ok:
        result["decision"] = command_decision
        result["gate_decision"] = command_decision
        result["gate_detail"] = command_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    manifest = build_launch_manifest(
        inventory_path,
        len(candidates),
        int(args.ready_index),
        selected,
        wsta64_path,
        wsta63_path,
        session,
        status_result,
        status_path,
        out_json,
        out_md,
    )
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "launch_manifest": manifest,
        "checks": {
            "inventory_private": True,
            "wsta65_revalidated_ready": True,
            "live_template_placeholders_only": True,
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(manifest)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta70-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings + md_findings))}
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
    parser.add_argument("--wsta67-inventory-json", type=Path)
    parser.add_argument("--ready-index", type=int, default=0)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=wsta65.DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
    parser.add_argument("--now-utc")
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
        payload = {"decision": "wsta70-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
