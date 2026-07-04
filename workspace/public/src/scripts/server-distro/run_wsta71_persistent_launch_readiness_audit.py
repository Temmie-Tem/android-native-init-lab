#!/usr/bin/env python3
"""WSTA71 host-only persistent launch readiness audit.

WSTA70 emits a private launch manifest for one selected READY session.  WSTA71
is the last default-off freshness check before an operator explicitly chooses
the WSTA58 live gate: it consumes the WSTA70 launch manifest, reruns WSTA65 for
the selected session, revalidates the WSTA58 command template, and writes a
redacted readiness audit.

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
import run_wsta70_persistent_session_launch_manifest as wsta70  # noqa: E402


REPO_ROOT = wsta70.REPO_ROOT
PRIVATE_ROOT = wsta70.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta70.DEFAULT_RUN_BASE
PASS_DECISION = "wsta71-persistent-launch-readiness-audit-pass"


def rel(path: Path) -> str:
    return wsta70.rel(path)


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
    return wsta70.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta70.is_under(path, root)


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
        "scope": "WSTA71 host-only persistent launch readiness audit",
        "default_mode": "host-only-revalidate-launch-manifest",
        "input": "workspace/private/runs/server-distro/<wsta70-run>/wsta70_launch_manifest.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta70-launch-manifest-json",
            "workspace/private/runs/server-distro/<wsta70-run>/wsta70_launch_manifest.json",
        ],
        "live_execution": "not-run-by-wsta71",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "readiness": result.get("readiness", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta70.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta71-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta71-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta71-blocked-{label}-missing"
    return path, None


def validate_launch_manifest(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta71-blocked-launch-manifest-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta70.PASS_DECISION:
        return False, "wsta71-blocked-launch-manifest-not-pass", {"decision": payload.get("decision")}
    manifest = payload.get("launch_manifest")
    if not isinstance(manifest, dict):
        return False, "wsta71-blocked-launch-manifest-missing", {}
    if manifest.get("default_public_off") is not True:
        return False, "wsta71-blocked-default-public-off-missing", {}
    if manifest.get("live_execution_requested") is not False:
        return False, "wsta71-blocked-live-execution-requested", {}
    if manifest.get("ready_for_live") is not True:
        return False, "wsta71-blocked-launch-manifest-not-ready", {}
    if manifest.get("public_url_value_logged") is not False:
        return False, "wsta71-blocked-public-url-logged", {}
    if manifest.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta71-blocked-secret-values-logged", {}
    wsta64_path, path_error = require_private_path(manifest.get("selected_wsta64_result"), "wsta64-result")
    if path_error or wsta64_path is None:
        return False, path_error or "wsta71-blocked-wsta64-result", {}
    return True, "ok", {"payload": payload, "manifest": manifest, "wsta64_path": wsta64_path}


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


def min_remaining_from_args(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    if args.min_initial_seconds_remaining is not None:
        return int(args.min_initial_seconds_remaining)
    value = manifest.get("min_initial_seconds_remaining")
    if value is None:
        return int(wsta65.DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
    return int(value)


def validate_manifest_consistency(manifest: dict[str, Any],
                                  wsta64_path: Path,
                                  status: dict[str, Any],
                                  session: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    if manifest.get("selected_wsta64_result") != rel(wsta64_path):
        return False, "wsta71-blocked-selected-wsta64-drift", {}
    if manifest.get("initial_private_lease_artifact") != status.get("initial_private_lease_artifact"):
        return False, "wsta71-blocked-initial-lease-drift", {}
    if manifest.get("renewal_wsta53_result") != status.get("renewal_wsta53_result"):
        return False, "wsta71-blocked-renewal-source-drift", {}
    if manifest.get("wsta58_preflight_result") != status.get("wsta58_preflight_result"):
        return False, "wsta71-blocked-wsta58-preflight-drift", {}
    if manifest.get("live_command_template") != session.get("live_command_template"):
        return False, "wsta71-blocked-live-template-drift", {}
    return True, "ok", {}


def build_readiness(launch_path: Path,
                    manifest: dict[str, Any],
                    status_result: dict[str, Any],
                    status_path: Path,
                    readiness_json: Path,
                    readiness_md: Path) -> dict[str, Any]:
    status = status_result.get("session_status") or {}
    return {
        "state": "READY_TO_ARM_DEFAULT_OFF",
        "wsta70_launch_manifest": rel(launch_path),
        "source_inventory": manifest.get("source_inventory"),
        "selected_wsta64_result": manifest.get("selected_wsta64_result"),
        "selected_wsta63_result": manifest.get("selected_wsta63_result"),
        "wsta65_revalidation_result": rel(status_path),
        "wsta65_session_state": status.get("session_state"),
        "ready_for_live": bool(status.get("ready_for_live")),
        "initial_seconds_remaining": status.get("initial_seconds_remaining"),
        "min_initial_seconds_remaining": status.get("min_initial_seconds_remaining"),
        "initial_private_lease_artifact": status.get("initial_private_lease_artifact"),
        "renewal_wsta53_result": status.get("renewal_wsta53_result"),
        "wsta58_preflight_result": status.get("wsta58_preflight_result"),
        "live_command_template": manifest.get("live_command_template"),
        "operator_required_replacements": [
            "<native-confirm-token>",
            "<public-confirm-token>",
        ],
        "json_path": rel(readiness_json),
        "markdown_path": rel(readiness_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(readiness: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in readiness.get("live_command_template") or [])
    lines = [
        "# WSTA Persistent Launch Readiness Audit",
        "",
        f"- State: `{readiness.get('state')}`",
        f"- WSTA70 launch manifest: `{readiness.get('wsta70_launch_manifest')}`",
        f"- WSTA65 state: `{readiness.get('wsta65_session_state')}`",
        f"- Initial seconds remaining: `{readiness.get('initial_seconds_remaining')}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Selected Session",
        "",
        f"- WSTA64 result: `{readiness.get('selected_wsta64_result')}`",
        f"- WSTA63 result: `{readiness.get('selected_wsta63_result')}`",
        f"- WSTA65 revalidation: `{readiness.get('wsta65_revalidation_result')}`",
        "",
        "## WSTA58 Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "This audit is not live execution. Replace placeholders only when explicitly running WSTA58.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta71-persistent-launch-readiness-audit-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA71 host-only persistent launch readiness audit",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta71-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta71-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta71_launch_readiness.json"
    out_md = run_dir / "wsta71_launch_readiness.md"

    if args.wsta70_launch_manifest_json is None:
        result["decision"] = "wsta71-blocked-launch-manifest-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    launch_path, path_error = require_private_path(args.wsta70_launch_manifest_json, "launch-manifest")
    if path_error or launch_path is None:
        result["decision"] = path_error or "wsta71-blocked-launch-manifest"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    valid, decision, detail = validate_launch_manifest(launch_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    manifest = detail["manifest"]
    wsta64_path = detail["wsta64_path"]
    min_remaining = min_remaining_from_args(args, manifest)
    status_dir = run_dir / "wsta65-readiness"
    status_result = wsta65.run(wsta65_args(status_dir, wsta64_path, min_remaining, args.now_utc))
    status_path = status_dir / "wsta65_result.json"
    status = status_result.get("session_status") or {}
    if (
        status_result.get("decision") != wsta65.PASS_DECISION
        or status.get("session_state") != "READY"
        or status.get("ready_for_live") is not True
    ):
        result["decision"] = "wsta71-blocked-launch-not-ready"
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
        _, session, _ = wsta70.load_wsta63_session(wsta64_path)
    except Exception as exc:  # noqa: BLE001
        result["decision"] = "wsta71-blocked-session-load-failed"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"error": str(exc)}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    consistent, consistency_decision, consistency_detail = validate_manifest_consistency(
        manifest,
        wsta64_path,
        status,
        session,
    )
    if not consistent:
        result["decision"] = consistency_decision
        result["gate_decision"] = consistency_decision
        result["gate_detail"] = consistency_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    command_ok, command_decision, command_detail = wsta70.validate_command(session, status)
    if not command_ok:
        result["decision"] = command_decision
        result["gate_decision"] = command_decision
        result["gate_detail"] = command_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    readiness = build_readiness(launch_path, manifest, status_result, status_path, out_json, out_md)
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "readiness": readiness,
        "checks": {
            "launch_manifest_private": True,
            "wsta65_revalidated_ready": True,
            "manifest_consistency_ok": True,
            "live_template_placeholders_only": True,
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(readiness)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta71-blocked-redaction-finding"
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
    parser.add_argument("--wsta70-launch-manifest-json", type=Path)
    parser.add_argument("--min-initial-seconds-remaining", type=int)
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
        payload = {"decision": "wsta71-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
