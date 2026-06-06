#!/usr/bin/env python3
"""V452 Wi-Fi live cleanup proof gate.

V452 is host-side only.  It verifies that a future V447/V445 live Wi-Fi run
proves cleanup containment and rollback before any post-live stability or server
policy work is allowed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v452-wifi-live-cleanup-proof")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
CLEANUP_FALSE_KEYS = (
    "wlan0_has_ip",
    "default_route_wlan",
    "route_get_wlan",
    "connectivity_validated_wifi",
    "dns_surface_wlan",
    "global_listener_observed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--wifi-root", type=Path, default=DEFAULT_WIFI_ROOT)
    parser.add_argument("--live-manifest", type=Path, default=None)
    parser.add_argument("--include-synthetic", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "invalid", "pass": False, "error": str(exc)}
    payload["_path"] = str(path)
    payload["_run_dir"] = str(path.parent)
    try:
        payload["_mtime"] = path.stat().st_mtime
    except OSError:
        payload["_mtime"] = 0.0
    return payload


def ignored_candidate(path: Path, include_synthetic: bool) -> bool:
    text = str(path)
    if include_synthetic:
        return False
    return any(token in text for token in ("synthetic", "env-missing", "-plan-", "-dryrun-", "missing-policy"))


def latest_manifest(root: Path, pattern: str, include_synthetic: bool) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for path in repo_path(root).glob(pattern):
        if path.name != "manifest.json":
            continue
        if ignored_candidate(path, include_synthetic):
            continue
        rows.append(load_manifest(path))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def live_manifest(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.live_manifest:
        return load_manifest(repo_path(args.live_manifest))
    live = latest_manifest(args.wifi_root, "v447-explicit-connect-flow-live-*/manifest.json", args.include_synthetic)
    preflight = latest_manifest(args.wifi_root, "v447-explicit-connect-flow-private-preflight-*/manifest.json", args.include_synthetic)
    if live and preflight and float(live.get("_mtime") or 0.0) < float(preflight.get("_mtime") or 0.0):
        return None
    return live


def nested_v445(live: dict[str, Any] | None) -> dict[str, Any]:
    if not live:
        return {}
    context = live.get("context") or {}
    nested = context.get("v445") or {}
    if nested.get("_path"):
        return nested
    run_dir = live.get("_run_dir")
    if run_dir:
        candidate = Path(run_dir) / "v445-android-wifi-explicit-connect-live" / "manifest.json"
        if candidate.exists():
            return load_manifest(candidate)
    return nested


def cleanup_state(v445: dict[str, Any]) -> dict[str, Any]:
    classification = v445.get("classification") or {}
    if classification.get("cleanup_state") is not None:
        return classification.get("cleanup_state") or {}
    nested = (v445.get("context") or {}).get("v445") or {}
    nested_classification = nested.get("classification") or {}
    return nested_classification.get("cleanup_state") or {}


def v445_classification(v445: dict[str, Any]) -> dict[str, Any]:
    classification = v445.get("classification") or {}
    if classification:
        return classification
    nested = (v445.get("context") or {}).get("v445") or {}
    return nested.get("classification") or {}


def step_names(live: dict[str, Any]) -> set[str]:
    return {str(step.get("name")) for step in live.get("steps") or []}


def combined_step_names(live: dict[str, Any] | None, v445: dict[str, Any]) -> set[str]:
    names = step_names(live or {})
    names.update(str(step.get("name")) for step in v445.get("steps") or [])
    return names


def cleanup_checks(live: dict[str, Any] | None, v445: dict[str, Any]) -> dict[str, Any]:
    state = cleanup_state(v445)
    names = combined_step_names(live, v445)
    classification = v445_classification(v445)
    checks = {
        "live_present": live is not None,
        "live_pass": bool((live or {}).get("pass")),
        "live_decision_pass": (live or {}).get("decision") == "v447-explicit-connect-flow-live-pass",
        "v445_present": bool(v445),
        "v445_pass": bool(v445.get("pass")),
        "v445_cleanup_decision": v445.get("decision") == "v445-explicit-connect-cleanup-pass",
        "wifi_bringup_executed": bool((live or {}).get("wifi_bringup_executed") or v445.get("wifi_bringup_executed")),
        "device_mutations": bool((live or {}).get("device_mutations") or v445.get("device_mutations")),
        "restore_native_step": "restore-native" in names,
        "cleanup_state_present": bool(state),
        "cleanup_disabled": bool(state.get("disabled_by_status")),
        "cleanup_false_keys_ok": all(not state.get(key) for key in CLEANUP_FALSE_KEYS),
        "exposure_removed": bool(classification.get("exposure_removed")),
        "forget_ok": bool(classification.get("forget_ok")),
        "connected_observed": bool(classification.get("connected_observed")),
    }
    checks["cleanup_contained"] = (
        checks["cleanup_state_present"]
        and checks["cleanup_disabled"]
        and checks["cleanup_false_keys_ok"]
        and checks["exposure_removed"]
        and checks["forget_ok"]
    )
    checks["post_live_ready"] = (
        checks["live_present"]
        and checks["live_pass"]
        and checks["live_decision_pass"]
        and checks["v445_present"]
        and checks["v445_pass"]
        and checks["v445_cleanup_decision"]
        and checks["wifi_bringup_executed"]
        and checks["device_mutations"]
        and checks["restore_native_step"]
        and checks["connected_observed"]
        and checks["cleanup_contained"]
    )
    checks["cleanup_state"] = state
    return checks


def classify(command: str, live: dict[str, Any] | None, v445: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v452-wifi-live-cleanup-proof-plan-ready",
            "pass": True,
            "reason": "live cleanup proof gate plan generated",
            "next_gate": "run V452 after V447 live evidence exists",
            "recommended_command": "",
        }
    if not live:
        return {
            "decision": "v452-wifi-live-cleanup-proof-awaiting-live",
            "pass": True,
            "reason": "no real V447 live evidence exists yet; host preflight/live handoff is still pending",
            "next_gate": "run generated host preflight script, then live script after preflight-ready",
            "recommended_command": "python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py run",
        }
    if checks.get("post_live_ready"):
        return {
            "decision": "v452-wifi-live-cleanup-proof-pass",
            "pass": True,
            "reason": "V447/V445 live evidence proves connection, cleanup containment, and rollback step presence",
            "next_gate": "document live result and plan bounded Wi-Fi stability or server binding policy",
            "recommended_command": "",
        }
    missing = [key for key, value in checks.items() if key != "cleanup_state" and value is False]
    return {
        "decision": "v452-wifi-live-cleanup-proof-blocked",
        "pass": False,
        "reason": "live evidence does not prove cleanup containment and rollback readiness: " + ", ".join(missing[:8]),
        "next_gate": "inspect V447/V445 live evidence and run cleanup/rollback before continuing",
        "recommended_command": "python3 scripts/revalidation/wifi_handoff_result_router_v449.py run",
    }


def check_rows(checks: dict[str, Any]) -> list[list[str]]:
    rows = []
    for key, value in checks.items():
        if key == "cleanup_state":
            continue
        rows.append([key, str(value)])
    return rows


def cleanup_rows(state: dict[str, Any]) -> list[list[str]]:
    if not state:
        return [["-", "-"]]
    return [[key, str(state.get(key))] for key in sorted(state)]


def guardrails() -> list[str]:
    return [
        "host-side live evidence proof only",
        "does not read Wi-Fi secret env values",
        "does not execute cleanup or handoff commands",
        "blocks post-live work unless cleanup containment is proven",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or {}
    return "\n".join(
        [
            "# V452 Wi-Fi Live Cleanup Proof",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- recommended_command: `{manifest['classification'].get('recommended_command') or '-'}`",
            f"- live_manifest: `{(manifest.get('live') or {}).get('_path') or '-'}`",
            f"- v445_manifest: `{(manifest.get('v445') or {}).get('_path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], check_rows(checks) if checks else [["-", "-"]]),
            "",
            "## Cleanup State",
            "",
            markdown_table(["item", "value"], cleanup_rows(checks.get("cleanup_state") or {})),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    live = live_manifest(args) if args.command == "run" else None
    v445 = nested_v445(live)
    checks = cleanup_checks(live, v445) if args.command == "run" else {}
    classification = classify(args.command, live, v445, checks)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "live": live,
        "v445": v445,
        "checks": checks,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {classification['next_gate']}")
    if classification.get("recommended_command"):
        print(f"recommended_command: {classification['recommended_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
