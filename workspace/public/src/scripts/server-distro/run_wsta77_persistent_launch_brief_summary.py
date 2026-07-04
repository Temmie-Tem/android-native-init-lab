#!/usr/bin/env python3
"""WSTA77 host-only persistent launch brief summary.

WSTA76 creates one fresh default-off launch brief.  WSTA77 scans a private WSTA
run tree for WSTA76 briefs, reruns WSTA76 for each source inventory, and emits
one redacted operator summary showing which briefs are still READY, stale, or
need regeneration.

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

import run_wsta76_persistent_launch_brief as wsta76  # noqa: E402


REPO_ROOT = wsta76.REPO_ROOT
PRIVATE_ROOT = wsta76.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta76.DEFAULT_RUN_BASE
PASS_DECISION = "wsta77-persistent-launch-brief-summary-pass"
DEFAULT_MAX_BRIEFS = 50
RECHECK_DIR_NAME = "wsta76-recheck"


def rel(path: Path) -> str:
    return wsta76.rel(path)


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
    return wsta76.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta76.is_under(path, root)


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
        "scope": "WSTA77 host-only persistent launch brief summary",
        "default_mode": "host-only-revalidate-brief-summary",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--scan-root",
            "workspace/private/runs/server-distro",
            "--max-briefs",
            str(DEFAULT_MAX_BRIEFS),
        ],
        "live_execution": "not-run-by-wsta77",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "launch_summary": result.get("launch_summary", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta76.redaction_findings(payload)


def newest_first(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda path: (path.stat().st_mtime, str(path)), reverse=True)


def is_recheck_artifact(path: Path) -> bool:
    return RECHECK_DIR_NAME in path.parts


def scan_brief_paths(root: Path, run_dir: Path, limit: int) -> tuple[list[Path], bool]:
    matches: list[Path] = []
    for path in root.rglob("wsta76_launch_brief.json"):
        if not path.is_file():
            continue
        if is_under(path, run_dir):
            continue
        if is_recheck_artifact(path):
            continue
        matches.append(path)
    matches = newest_first(matches)
    truncated = len(matches) > limit
    return matches[:limit], truncated


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta77-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta77-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta77-blocked-{label}-missing"
    return path, None


def validate_brief(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta77-blocked-brief-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta76.PASS_DECISION:
        return False, "wsta77-blocked-brief-not-pass", {"decision": payload.get("decision")}
    brief = payload.get("launch_brief")
    if not isinstance(brief, dict):
        return False, "wsta77-blocked-launch-brief-missing", {}
    if brief.get("state") != "READY_TO_EXECUTE_DEFAULT_OFF":
        return False, "wsta77-blocked-launch-brief-not-ready", {"state": brief.get("state")}
    if brief.get("default_public_off") is not True:
        return False, "wsta77-blocked-default-public-off-missing", {}
    if brief.get("live_execution_requested") is not False:
        return False, "wsta77-blocked-live-execution-requested", {}
    if brief.get("public_url_value_logged") is not False:
        return False, "wsta77-blocked-public-url-logged", {}
    if brief.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta77-blocked-secret-values-logged", {}
    inventory_path, path_error = require_private_path(brief.get("source_wsta75_inventory"), "source-inventory")
    if path_error or inventory_path is None:
        return False, path_error or "wsta77-blocked-source-inventory", {}
    return True, "ok", {"payload": payload, "brief": brief, "inventory_path": inventory_path}


def wsta76_args(run_dir: Path,
                inventory_path: Path,
                ready_index: int,
                max_packets: int,
                min_remaining: int | None,
                now_utc: str | None) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta75-arming-inventory-json",
        str(inventory_path),
        "--ready-index",
        str(ready_index),
        "--max-packets",
        str(max_packets),
    ]
    if min_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(min_remaining)])
    if now_utc:
        argv.extend(["--now-utc", now_utc])
    return wsta76.build_arg_parser().parse_args(argv)


def entry_state(original: dict[str, Any], recheck: dict[str, Any]) -> tuple[str, bool, str]:
    if recheck.get("decision") != wsta76.PASS_DECISION:
        if recheck.get("decision") == "wsta76-blocked-no-ready-packet":
            return "STALE_OR_NOT_READY", False, "rerun-wsta72-through-wsta76"
        return "INVALID_OR_BLOCKED", False, "inspect-brief-and-source-inventory"
    fresh = recheck.get("launch_brief") if isinstance(recheck.get("launch_brief"), dict) else {}
    if original.get("selected_wsta73_arming_packet") != fresh.get("selected_wsta73_arming_packet"):
        return "DRIFT_RECHECK_REQUIRED", False, "use-fresh-wsta76-brief-or-rerun-wsta76"
    if fresh.get("ready_for_live") is True and fresh.get("state") == "READY_TO_EXECUTE_DEFAULT_OFF":
        return "READY_TO_EXECUTE_DEFAULT_OFF", True, "operator-may-run-explicit-wsta58-live-gate-from-selected-brief"
    return "STALE_OR_NOT_READY", False, "rerun-wsta72-through-wsta76"


def summary_entry(index: int,
                  brief_path: Path,
                  original: dict[str, Any],
                  recheck: dict[str, Any],
                  recheck_path: Path) -> dict[str, Any]:
    fresh = recheck.get("launch_brief") if isinstance(recheck.get("launch_brief"), dict) else {}
    state, ready, next_action = entry_state(original, recheck)
    return {
        "index": index,
        "wsta76_launch_brief": rel(brief_path),
        "wsta76_recheck_result": rel(recheck_path),
        "wsta76_recheck_decision": recheck.get("decision"),
        "state": state,
        "ready_for_live": ready,
        "original_selected_wsta73_arming_packet": original.get("selected_wsta73_arming_packet"),
        "fresh_selected_wsta73_arming_packet": fresh.get("selected_wsta73_arming_packet"),
        "initial_seconds_remaining": fresh.get("initial_seconds_remaining"),
        "ready_candidate_count": fresh.get("ready_candidate_count"),
        "ack_count": len(fresh.get("operator_acknowledgements_required") or original.get("operator_acknowledgements_required") or []),
        "abort_condition_count": len(fresh.get("abort_conditions") or original.get("abort_conditions") or []),
        "recommended_next_action": next_action,
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def count_states(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        state = str(entry.get("state") or "UNKNOWN")
        counts[state] = counts.get(state, 0) + 1
    return counts


def ready_sort_key(entry: dict[str, Any]) -> tuple[int, str]:
    seconds = entry.get("initial_seconds_remaining")
    if not isinstance(seconds, int):
        seconds = -1
    return int(seconds), str(entry.get("wsta76_launch_brief") or "")


def selected_ready_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    ready = [entry for entry in entries if entry.get("state") == "READY_TO_EXECUTE_DEFAULT_OFF"]
    if not ready:
        return None
    return sorted(ready, key=ready_sort_key, reverse=True)[0]


def build_summary(scan_root: Path,
                  entries: list[dict[str, Any]],
                  invalid_entries: list[dict[str, Any]],
                  truncated: bool,
                  max_briefs: int) -> dict[str, Any]:
    counts = count_states(entries)
    ready_entry = selected_ready_entry(entries)
    ready_count = counts.get("READY_TO_EXECUTE_DEFAULT_OFF", 0)
    stale_count = counts.get("STALE_OR_NOT_READY", 0)
    drift_count = counts.get("DRIFT_RECHECK_REQUIRED", 0)
    blocked_count = counts.get("INVALID_OR_BLOCKED", 0)
    if ready_count:
        overall_state = "READY_BRIEF_PRESENT_DEFAULT_OFF"
        next_action = "operator-may-run-explicit-wsta58-live-gate-from-selected-brief"
    elif drift_count:
        overall_state = "DRIFT_RECHECK_REQUIRED"
        next_action = "rerun-wsta76-for-current-brief"
    elif entries:
        overall_state = "NO_READY_BRIEF"
        next_action = "rerun-wsta72-through-wsta76"
    else:
        overall_state = "NO_LAUNCH_BRIEFS_FOUND"
        next_action = "run-wsta72-through-wsta76"
    return {
        "scan_root": rel(scan_root),
        "overall_state": overall_state,
        "brief_count": len(entries),
        "invalid_brief_count": len(invalid_entries),
        "state_counts": counts,
        "ready_count": ready_count,
        "stale_count": stale_count,
        "drift_count": drift_count,
        "blocked_count": blocked_count,
        "scan_truncated": truncated,
        "max_briefs": max_briefs,
        "selected_ready_brief": ready_entry,
        "entries": entries,
        "invalid_entries": invalid_entries,
        "recommended_next_action": next_action,
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(summary: dict[str, Any]) -> str:
    selected = summary.get("selected_ready_brief") or {}
    lines = [
        "# WSTA Persistent Launch Brief Summary",
        "",
        f"- Overall state: `{summary.get('overall_state')}`",
        f"- Scan root: `{summary.get('scan_root')}`",
        f"- Briefs: `{summary.get('brief_count')}`",
        f"- READY: `{summary.get('ready_count')}`",
        f"- STALE/NOT_READY: `{summary.get('stale_count')}`",
        f"- DRIFT: `{summary.get('drift_count')}`",
        f"- BLOCKED: `{summary.get('blocked_count')}`",
        f"- Invalid: `{summary.get('invalid_brief_count')}`",
        f"- Selected ready brief: `{selected.get('wsta76_launch_brief')}`",
        f"- Recommended next action: `{summary.get('recommended_next_action')}`",
        "- Default public state: `PUBLIC_OFF`",
        "- Live execution requested: `false`",
        "",
        "## Briefs",
        "",
        "| State | Ready | Seconds Remaining | WSTA76 Recheck | Brief |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for entry in summary.get("entries", []):
        lines.append(
            "| {state} | {ready} | {seconds} | `{recheck}` | `{path}` |".format(
                state=entry.get("state"),
                ready=str(bool(entry.get("ready_for_live"))).lower(),
                seconds=entry.get("initial_seconds_remaining"),
                recheck=entry.get("wsta76_recheck_decision"),
                path=entry.get("wsta76_launch_brief"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta77-persistent-launch-brief-summary-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    scan_root = resolve_path(args.scan_root)
    result: dict[str, Any] = {
        "scope": "WSTA77 host-only persistent launch brief summary",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta77-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta77-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not is_under(scan_root, PRIVATE_ROOT):
        result["decision"] = "wsta77-blocked-nonprivate-scan-root"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not scan_root.exists():
        result["decision"] = "wsta77-blocked-scan-root-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta77_launch_brief_summary.json"
    out_md = run_dir / "wsta77_launch_brief_summary.md"

    brief_paths, truncated = scan_brief_paths(scan_root, run_dir, int(args.max_briefs))
    entries: list[dict[str, Any]] = []
    invalid_entries: list[dict[str, Any]] = []
    for index, brief_path in enumerate(brief_paths):
        valid, decision, detail = validate_brief(brief_path)
        if not valid:
            invalid_entries.append({
                "index": index,
                "wsta76_launch_brief": rel(brief_path),
                "decision": decision,
                "detail": detail,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            })
            continue
        recheck_dir = run_dir / f"brief-{index:03d}" / RECHECK_DIR_NAME
        recheck_path = recheck_dir / "wsta76_launch_brief.json"
        try:
            recheck = wsta76.run(wsta76_args(
                recheck_dir,
                detail["inventory_path"],
                int(args.ready_index),
                int(args.max_packets),
                args.min_initial_seconds_remaining,
                args.now_utc,
            ))
            entries.append(summary_entry(index, brief_path, detail["brief"], recheck, recheck_path))
        except Exception as exc:  # noqa: BLE001
            invalid_entries.append({
                "index": index,
                "wsta76_launch_brief": rel(brief_path),
                "error": str(exc),
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            })

    summary = build_summary(scan_root, entries, invalid_entries, truncated, int(args.max_briefs))
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "launch_summary": summary,
        "checks": {
            "scan_root_private": True,
            "wsta76_rechecked": True,
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(summary)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta77-blocked-redaction-finding"
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
    parser.add_argument("--scan-root", type=Path, default=DEFAULT_RUN_BASE)
    parser.add_argument("--max-briefs", type=int, default=DEFAULT_MAX_BRIEFS)
    parser.add_argument("--max-packets", type=int, default=wsta76.wsta75.DEFAULT_MAX_PACKETS)
    parser.add_argument("--ready-index", type=int, default=0)
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
        payload = {"decision": "wsta77-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
