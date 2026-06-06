#!/usr/bin/env python3
"""V715 host-only classifier for V712 ICNSS/QCA6390 edge captures."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v715-icnss-edge-surface-classifier")
DEFAULT_SOURCE = Path("tmp/wifi/latest-v714-v712-icnss-edge-live.txt")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_manifest(source: Path) -> tuple[Path, Path]:
    source = repo_path(source)
    if source.is_file() and source.name != "manifest.json":
        text = source.read_text(encoding="utf-8").strip()
        if text:
            source = repo_path(Path(text))
    if source.is_dir():
        run_dir = source
        manifest = run_dir / "manifest.json"
    else:
        manifest = source
        run_dir = manifest.parent
    return run_dir, manifest


def nested_manifest(top_manifest: dict[str, Any], run_dir: Path) -> Path | None:
    for key in ("arm_v712", "arm_v700"):
        arm = top_manifest.get(key)
        if isinstance(arm, dict):
            manifest = arm.get("manifest")
            if manifest and Path(str(manifest)).exists():
                return Path(str(manifest))
    candidates = [
        run_dir / "arm-v700-v119-provider-first-cnss" / "live" / "manifest.json",
        run_dir / "arm-v712-v121-provider-first-cnss" / "live" / "manifest.json",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def edge_value(edge: dict[str, Any], phase: str, name: str) -> str:
    direct = edge.get(f"wifi_icnss_edge.{phase}.{name}")
    if direct is not None:
        return str(direct)
    companion = edge.get(f"wifi_companion_start.icnss_edge_{phase}.{name}")
    return "" if companion is None else str(companion)


def edge_exists(edge: dict[str, Any], phase: str, name: str) -> bool:
    return edge_value(edge, phase, f"{name}.exists") == "1"


def extract_surface(top_manifest: dict[str, Any], arm_manifest: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm_manifest or {}).get("live") or {}
    edge = live.get("v712_icnss_edge_surface")
    if not isinstance(edge, dict):
        edge = top_manifest.get("icnss_edge_surface") if isinstance(top_manifest.get("icnss_edge_surface"), dict) else {}
    counts = live.get("v655_counts") if isinstance(live.get("v655_counts"), dict) else {}
    markers = live.get("markers") if isinstance(live.get("markers"), dict) else {}
    marker_counts = markers.get("counts") if isinstance(markers.get("counts"), dict) else {}
    return {
        "top_decision": top_manifest.get("decision", ""),
        "arm_decision": (arm_manifest or {}).get("decision", ""),
        "icnss_edge_captured": bool((arm_manifest or {}).get("icnss_edge_captured") or top_manifest.get("icnss_edge_captured")),
        "edge": edge,
        "counts": counts,
        "marker_counts": marker_counts,
        "service74_positive": int_value(counts.get("service_notifier_180")) > 0 and int_value(counts.get("service_notifier_74")) > 0,
        "wlfw_or_wlan0": any(
            int_value(counts.get(name)) > 0
            for name in ("wlfw_start", "wlfw_service_request", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")
        ) or any(int_value(marker_counts.get(name)) > 0 for name in ("wlfw", "bdf", "wlan_fw_ready", "wlan0")),
        "service74_open": {
            "icnss_bound": edge_exists(edge, "service74_open", "icnss_driver_link"),
            "qca6390_bound": edge_exists(edge, "service74_open", "qca6390_driver_link"),
            "wlan0_visible": edge_exists(edge, "service74_open", "wlan0_netdev"),
            "shutdown_wlan_visible": edge_exists(edge, "service74_open", "shutdown_wlan"),
            "value_captures": edge_value(edge, "service74_open", "value_captures"),
        },
        "window": {
            "icnss_bound": edge_exists(edge, "window", "icnss_driver_link"),
            "qca6390_bound": edge_exists(edge, "window", "qca6390_driver_link"),
            "wlan0_visible": edge_exists(edge, "window", "wlan0_netdev"),
            "shutdown_wlan_visible": edge_exists(edge, "window", "shutdown_wlan"),
            "value_captures": edge_value(edge, "window", "value_captures"),
        },
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(surface: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    service74_open = surface["service74_open"]
    window = surface["window"]
    add_check(
        checks,
        "service74-positive-input",
        "pass" if surface["service74_positive"] else "blocked",
        "blocker",
        f"service_notifier_180/74 positive={surface['service74_positive']}",
        [],
        "rerun V712 only after lower modem/WLAN-PD readiness is positive",
    )
    add_check(
        checks,
        "icnss-edge-captured",
        "pass" if surface["icnss_edge_captured"] else "blocked",
        "blocker",
        f"edge_key_count={len(surface['edge'])}",
        [],
        "deploy helper v121 and rerun V712 edge capture",
    )
    add_check(
        checks,
        "icnss-bound",
        "pass" if service74_open["icnss_bound"] and window["icnss_bound"] else "blocked",
        "blocker",
        f"service74_open={service74_open['icnss_bound']} window={window['icnss_bound']}",
        ["wifi_icnss_edge.*.icnss_driver_link.exists"],
        "repair ICNSS platform bind before QCA/WLFW work",
    )
    add_check(
        checks,
        "qca6390-bound",
        "pass" if service74_open["qca6390_bound"] or window["qca6390_bound"] else "finding",
        "info",
        f"service74_open={service74_open['qca6390_bound']} window={window['qca6390_bound']}",
        ["wifi_icnss_edge.*.qca6390_driver_link.exists"],
        "classify why QCA6390 platform child remains unbound before WLFW",
    )
    add_check(
        checks,
        "wlfw-or-wlan0-progress",
        "pass" if surface["wlfw_or_wlan0"] else "finding",
        "info",
        f"wlfw_or_wlan0={surface['wlfw_or_wlan0']}",
        [],
        "keep HAL/scan/connect blocked until WLFW/BDF/fw_ready/wlan0 advances",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, surface: dict[str, Any] | None, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v715-icnss-edge-surface-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only classifier on latest V712 edge evidence",
        )
    if surface is None:
        return "v715-icnss-edge-surface-missing", False, "source manifest could not be loaded", "inspect evidence path"
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v715-icnss-edge-surface-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "regenerate V712 edge evidence",
        )
    service74_open = surface["service74_open"]
    window = surface["window"]
    if surface["wlfw_or_wlan0"]:
        return (
            "v715-wlfw-or-wlan0-advanced",
            True,
            "WLFW/BDF/fw_ready/wlan0 advanced in V712 evidence",
            "classify wlan0 readiness before scan/connect",
        )
    if not (service74_open["qca6390_bound"] or window["qca6390_bound"]):
        return (
            "v715-qca6390-platform-child-unbound",
            True,
            "ICNSS parent is bound during service74/window, but QCA6390 child driver link and wlan0 are absent",
            "inspect QCA6390 bind prerequisites/deferred probe before another CNSS/HAL retry",
        )
    return (
        "v715-qca6390-bound-pre-wlfw-gap",
        True,
        "QCA6390 appears bound, but WLFW/BDF/fw_ready/wlan0 did not advance",
        "target ICNSS-QMI/WLFW handoff after QCA6390 bind",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest.get("surface") or {}
    rows = []
    for phase in ("service74_open", "window"):
        phase_surface = surface.get(phase) or {}
        for key in ("icnss_bound", "qca6390_bound", "wlan0_visible", "shutdown_wlan_visible", "value_captures"):
            rows.append([phase, key, str(phase_surface.get(key, ""))])
    counts = surface.get("counts") or {}
    marker_counts = surface.get("marker_counts") or {}
    count_rows = [[key, str(counts.get(key, 0))] for key in sorted(counts)]
    marker_rows = [[key, str(marker_counts.get(key, 0))] for key in sorted(marker_counts)]
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    return "\n".join([
        "# V715 ICNSS Edge Surface Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- source_manifest: `{manifest.get('source_manifest', '')}`",
        f"- arm_manifest: `{manifest.get('arm_manifest', '')}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Edge Surface",
        "",
        markdown_table(["phase", "item", "value"], rows) if rows else "- not captured",
        "",
        "## Counts",
        "",
        markdown_table(["marker", "count"], count_rows) if count_rows else "- no count surface",
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows) if marker_rows else "- no marker count surface",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source_manifest = ""
    arm_manifest_path = ""
    surface: dict[str, Any] | None = None
    checks: list[Check] = []
    if args.command == "run":
        run_dir, top_path = resolve_manifest(args.source)
        source_manifest = str(top_path)
        top_manifest = load_json(top_path)
        arm_path = nested_manifest(top_manifest, run_dir)
        arm_manifest = load_json(arm_path) if arm_path else None
        arm_manifest_path = str(arm_path or "")
        surface = extract_surface(top_manifest, arm_manifest)
        checks = build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, surface, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v715",
        "source": str(args.source),
        "source_manifest": source_manifest,
        "arm_manifest": arm_manifest_path,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "surface": surface or {},
        "evidence_dir": str(store.run_dir),
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
