#!/usr/bin/env python3
"""V747 host-only QCA6390 driver-binding delta classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v747-qca6390-driver-binding-delta")
DEFAULT_V746_SOURCE = Path("tmp/wifi/latest-v746-mdm-helper-sysmon-live.txt")
DEFAULT_V715_SOURCE = Path("tmp/wifi/v717-icnss-edge-surface-classifier/manifest.json")
DEFAULT_V716_SOURCE = Path("tmp/wifi/v717-qca-bind-reconciliation/manifest.json")
DEFAULT_V703_REPORT = Path("docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md")


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
    parser.add_argument("--v746-source", type=Path, default=DEFAULT_V746_SOURCE)
    parser.add_argument("--v715-source", type=Path, default=DEFAULT_V715_SOURCE)
    parser.add_argument("--v716-source", type=Path, default=DEFAULT_V716_SOURCE)
    parser.add_argument("--v703-report", type=Path, default=DEFAULT_V703_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_manifest(source: Path) -> Path:
    path = repo_path(source)
    if path.is_file() and path.name != "manifest.json":
        text = path.read_text(encoding="utf-8").strip()
        if text:
            path = repo_path(Path(text))
    if path.is_dir():
        path = path / "manifest.json"
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "pass"}
    return False


def helper_keys(manifest: dict[str, Any]) -> dict[str, Any]:
    base = manifest.get("base_manifest")
    if isinstance(base, dict):
        live = base.get("live")
    else:
        live = manifest.get("live")
    if not isinstance(live, dict):
        return {}
    helper = live.get("helper_result")
    if not isinstance(helper, dict):
        return {}
    keys = helper.get("keys")
    return keys if isinstance(keys, dict) else {}


def v746_live(manifest: dict[str, Any]) -> dict[str, Any]:
    base = manifest.get("base_manifest")
    live = base.get("live") if isinstance(base, dict) else manifest.get("live")
    return live if isinstance(live, dict) else {}


def nested_marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = v746_live(manifest)
    markers = live.get("markers")
    counts = markers.get("counts") if isinstance(markers, dict) else {}
    if not isinstance(counts, dict):
        return {}
    return {str(key): int_value(value) for key, value in counts.items()}


def path_exists_key(keys: dict[str, Any], prefix: str) -> bool | None:
    value = keys.get(f"{prefix}.exists")
    if value is None:
        return None
    return boolish(value)


def find_lines(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)]


def android_reference(report_path: Path) -> dict[str, Any]:
    path = repo_path(report_path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    netdev_lines = find_lines(text, r"/sys/devices/platform/soc/18800000\.qcom,icnss/net/")
    rejected_lines = find_lines(text, r"qca6390.*driver-link.*rejected|bind`/`unbind`|qca6390` bind/unbind")
    wlfw_lines = find_lines(text, r"icnss_qmi|wlfw_start|BDF file|WLAN FW is ready|wlan0")
    return {
        "path": str(path),
        "exists": path.exists(),
        "netdev_lines": netdev_lines,
        "rejected_lines": rejected_lines,
        "wlfw_lines": wlfw_lines,
        "has_icnss_parent_netdevs": bool(netdev_lines),
        "rejects_qca_bind_target": bool(rejected_lines),
        "has_wlfw_or_wlan0_reference": bool(wlfw_lines),
    }


def v715_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    surface = manifest.get("surface")
    return surface if isinstance(surface, dict) else {}


def phase_bool(surface: dict[str, Any], phase: str, key: str) -> bool:
    phase_surface = surface.get(phase)
    if not isinstance(phase_surface, dict):
        return False
    return bool(phase_surface.get(key))


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(v746: dict[str, Any],
                 v715: dict[str, Any],
                 v716: dict[str, Any],
                 android: dict[str, Any]) -> list[Check]:
    keys = helper_keys(v746)
    counts = nested_marker_counts(v746)
    surface = v715_surface(v715)
    qca_service_open = path_exists_key(keys, "wifi_icnss_edge.service74_open.qca6390_driver_link")
    qca_window = path_exists_key(keys, "wifi_icnss_edge.window.qca6390_driver_link")
    wlan0_window = path_exists_key(keys, "wifi_icnss_edge.window.wlan0_netdev")
    mdm_helper_started = boolish(v746.get("mdm_helper_start_executed"))
    mhi_or_wlfw = any(counts.get(name, 0) > 0 for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd"))
    checks: list[Check] = []
    add_check(
        checks,
        "v746-sysmon-mdm-helper-input",
        "pass" if v746.get("decision") == "v746-mdm-helper-started-no-lower-progress" and mdm_helper_started else "blocked",
        "blocker",
        f"decision={v746.get('decision')} mdm_helper_start_executed={mdm_helper_started}",
        [str(v746.get("evidence_dir", ""))],
        "rerun V746 before classifying QCA6390 binding delta",
    )
    add_check(
        checks,
        "v746-qca-child-unbound",
        "pass" if qca_service_open is False and qca_window is False and wlan0_window is False else "blocked",
        "blocker",
        f"service74_open={qca_service_open} window={qca_window} wlan0_window={wlan0_window}",
        [
            "wifi_icnss_edge.service74_open.qca6390_driver_link.exists",
            "wifi_icnss_edge.window.qca6390_driver_link.exists",
            "wifi_icnss_edge.window.wlan0_netdev.exists",
        ],
        "refresh V746 edge capture if QCA fields are missing",
    )
    add_check(
        checks,
        "v746-no-mhi-wlfw-progress",
        "pass" if not mhi_or_wlfw else "blocked",
        "blocker",
        json.dumps({name: counts.get(name, 0) for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd")}, sort_keys=True),
        [],
        "if lower markers advanced, switch to wlan0 readiness classifier",
    )
    add_check(
        checks,
        "v715-consistent-child-unbound",
        "pass" if v715.get("decision") == "v715-qca6390-platform-child-unbound" else "blocked",
        "blocker",
        f"decision={v715.get('decision')}",
        [str(v715.get("source_manifest", ""))],
        "rerun V715 against V717/V746 edge evidence",
    )
    add_check(
        checks,
        "v715-icnss-parent-bound",
        "pass" if phase_bool(surface, "service74_open", "icnss_bound") and phase_bool(surface, "window", "icnss_bound") else "blocked",
        "blocker",
        f"service74_open={phase_bool(surface, 'service74_open', 'icnss_bound')} window={phase_bool(surface, 'window', 'icnss_bound')}",
        [],
        "repair ICNSS parent binding before child binding work",
    )
    add_check(
        checks,
        "v716-bind-action-blocked-by-policy",
        "pass" if v716.get("decision") == "v716-qca-child-unbound-not-bind-target" else "blocked",
        "blocker",
        f"decision={v716.get('decision')}",
        [],
        "do not write bind/unbind until Android evidence contradicts V716",
    )
    add_check(
        checks,
        "android-reference-usable",
        "pass" if android["has_icnss_parent_netdevs"] and android["rejects_qca_bind_target"] and android["has_wlfw_or_wlan0_reference"] else "blocked",
        "blocker",
        f"netdev={len(android['netdev_lines'])} reject={len(android['rejected_lines'])} wlfw_or_wlan0={len(android['wlfw_lines'])}",
        (android["netdev_lines"] + android["rejected_lines"] + android["wlfw_lines"])[:10],
        "capture a narrow Android QCA6390 binding reference if stale or missing",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v747-qca6390-driver-binding-delta-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only QCA6390 binding delta classifier",
        )
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v747-qca6390-driver-binding-delta-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh missing source evidence before selecting a live trigger",
        )
    return (
        "v747-qca-driver-link-gap-not-bind-target",
        True,
        "V746 confirms sysmon-gated mdm_helper is safe but insufficient; QCA6390 child remains unbound, while V716 keeps bind/unbind blocked",
        "classify the non-bind ICNSS/QCA power-up trigger or capture a narrow Android binding reference",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    counts = manifest.get("v746_marker_counts") or {}
    count_rows = [[key, str(counts.get(key, 0))] for key in sorted(counts)]
    android = manifest.get("android_reference") or {}
    android_rows = [
        ["has_icnss_parent_netdevs", str(android.get("has_icnss_parent_netdevs"))],
        ["rejects_qca_bind_target", str(android.get("rejects_qca_bind_target"))],
        ["has_wlfw_or_wlan0_reference", str(android.get("has_wlfw_or_wlan0_reference"))],
        ["netdev_line_count", str(len(android.get("netdev_lines") or []))],
        ["rejected_line_count", str(len(android.get("rejected_lines") or []))],
        ["wlfw_line_count", str(len(android.get("wlfw_lines") or []))],
    ]
    return "\n".join([
        "# V747 QCA6390 Driver-binding Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Source Manifests",
        "",
        markdown_table(["source", "path"], [
            ["v746", str(manifest.get("v746_manifest", ""))],
            ["v715", str(manifest.get("v715_manifest", ""))],
            ["v716", str(manifest.get("v716_manifest", ""))],
            ["v703_report", str(manifest.get("v703_report", ""))],
        ]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## V746 Marker Counts",
        "",
        markdown_table(["marker", "count"], count_rows) if count_rows else "- plan only",
        "",
        "## Android Reference",
        "",
        markdown_table(["item", "value"], android_rows),
        "",
        "## Guardrail",
        "",
        "- No QCA6390 bind/unbind or driver_override is justified by this classification.",
        "- Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked until WLFW/BDF/`wlan0` advances.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v746_manifest = ""
    v715_manifest = ""
    v716_manifest = ""
    v746: dict[str, Any] = {}
    v715: dict[str, Any] = {}
    v716: dict[str, Any] = {}
    android: dict[str, Any] = {
        "path": str(repo_path(args.v703_report)),
        "exists": False,
        "netdev_lines": [],
        "rejected_lines": [],
        "wlfw_lines": [],
        "has_icnss_parent_netdevs": False,
        "rejects_qca_bind_target": False,
        "has_wlfw_or_wlan0_reference": False,
    }
    checks: list[Check] = []
    if args.command == "run":
        v746_path = resolve_manifest(args.v746_source)
        v715_path = resolve_manifest(args.v715_source)
        v716_path = resolve_manifest(args.v716_source)
        v746_manifest = str(v746_path)
        v715_manifest = str(v715_path)
        v716_manifest = str(v716_path)
        v746 = load_json(v746_path)
        v715 = load_json(v715_path)
        v716 = load_json(v716_path)
        android = android_reference(args.v703_report)
        checks = build_checks(v746, v715, v716, android)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v747",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "v746_manifest": v746_manifest,
        "v715_manifest": v715_manifest,
        "v716_manifest": v716_manifest,
        "v703_report": str(repo_path(args.v703_report)),
        "v746_decision": v746.get("decision"),
        "v715_decision": v715.get("decision"),
        "v716_decision": v716.get("decision"),
        "v746_marker_counts": nested_marker_counts(v746) if v746 else {},
        "android_reference": android,
        "checks": [asdict(check) for check in checks],
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v747-qca6390-driver-binding-delta.txt")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(str(store.run_dir.relative_to(repo_path("."))) + "\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
