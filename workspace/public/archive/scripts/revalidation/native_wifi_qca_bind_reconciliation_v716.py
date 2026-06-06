#!/usr/bin/env python3
"""V716 host-only reconciliation for V715 QCA child-unbound evidence.

V715 captures a real native fact: the QCA6390 platform child has no `driver`
symlink during the service74-positive ICNSS edge window. V703 previously showed
that Android reaches working Wi-Fi netdevs under the ICNSS parent and rejected
`qca6390` bind/unbind as the next target. This classifier reconciles those two
facts so the next live gate stays on the ICNSS-QMI/WLFW readiness edge.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v716-qca-bind-reconciliation")
DEFAULT_V715_SOURCE = Path("tmp/wifi/latest-v715-icnss-edge-surface-classifier.txt")
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
    parser.add_argument("--v715-source", type=Path, default=DEFAULT_V715_SOURCE)
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


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8")


def find_lines(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)]


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def v715_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    surface = manifest.get("surface")
    return surface if isinstance(surface, dict) else {}


def phase_bool(surface: dict[str, Any], phase: str, key: str) -> bool:
    phase_surface = surface.get(phase)
    if not isinstance(phase_surface, dict):
        return False
    return bool(phase_surface.get(key))


def android_reference(report_text: str) -> dict[str, Any]:
    netdev_lines = find_lines(report_text, r"/sys/devices/platform/soc/18800000\.qcom,icnss/net/")
    rejected_lines = find_lines(report_text, r"qca6390.*driver-link.*rejected|bind`/`unbind`|qca6390` bind/unbind")
    wlfw_lines = find_lines(report_text, r"icnss_qmi|wlfw_start|BDF file|WLAN FW is ready")
    return {
        "netdev_lines": netdev_lines,
        "rejected_lines": rejected_lines,
        "wlfw_lines": wlfw_lines,
        "has_icnss_parent_netdevs": bool(netdev_lines),
        "rejects_qca_bind_target": bool(rejected_lines),
        "has_android_wlfw_reference": bool(wlfw_lines),
    }


def build_checks(v715: dict[str, Any], v703: dict[str, Any]) -> list[Check]:
    surface = v715_surface(v715)
    counts = surface.get("counts") if isinstance(surface.get("counts"), dict) else {}
    checks: list[Check] = []
    checks.append(Check(
        "v715-input-qca-child-unbound",
        "pass" if v715.get("decision") == "v715-qca6390-platform-child-unbound" else "blocked",
        "blocker",
        f"decision={v715.get('decision')}",
        [str(v715.get("source_manifest", "")), str(v715.get("arm_manifest", ""))],
        "rerun V715 against V712 ICNSS edge evidence",
    ))
    checks.append(Check(
        "native-icnss-parent-bound",
        "pass" if phase_bool(surface, "service74_open", "icnss_bound") and phase_bool(surface, "window", "icnss_bound") else "blocked",
        "blocker",
        f"service74_open={phase_bool(surface, 'service74_open', 'icnss_bound')} window={phase_bool(surface, 'window', 'icnss_bound')}",
        [],
        "repair ICNSS parent binding before ICNSS-QMI/WLFW work",
    ))
    checks.append(Check(
        "native-qca-child-unbound",
        "pass" if not phase_bool(surface, "service74_open", "qca6390_bound") and not phase_bool(surface, "window", "qca6390_bound") else "warn",
        "info",
        f"service74_open={phase_bool(surface, 'service74_open', 'qca6390_bound')} window={phase_bool(surface, 'window', 'qca6390_bound')}",
        [],
        "do not treat this alone as permission to write bind/unbind",
    ))
    checks.append(Check(
        "native-wlfw-absent",
        "pass" if all(int_value(counts.get(key)) == 0 for key in ("qmi_server_connected", "wlfw_start", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")) else "warn",
        "info",
        json.dumps({key: int_value(counts.get(key)) for key in ("qmi_server_connected", "wlfw_start", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")}, sort_keys=True),
        [],
        "if any marker advanced, move to wlan0 readiness classifier",
    ))
    checks.append(Check(
        "android-icnss-parent-netdev-reference",
        "pass" if v703["has_icnss_parent_netdevs"] else "blocked",
        "blocker",
        f"netdev_line_count={len(v703['netdev_lines'])}",
        v703["netdev_lines"][:6],
        "refresh Android reference if this report is stale",
    ))
    checks.append(Check(
        "android-qca-bind-target-rejected",
        "pass" if v703["rejects_qca_bind_target"] else "blocked",
        "blocker",
        f"rejected_line_count={len(v703['rejected_lines'])}",
        v703["rejected_lines"][:6],
        "do not plan QCA bind/unbind without new Android evidence contradicting V703",
    ))
    checks.append(Check(
        "android-wlfw-reference-present",
        "pass" if v703["has_android_wlfw_reference"] else "blocked",
        "blocker",
        f"wlfw_line_count={len(v703['wlfw_lines'])}",
        v703["wlfw_lines"][:8],
        "refresh Android WLFW reference before changing the next live gate",
    ))
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v716-qca-bind-reconciliation-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only reconciliation against V715 and V703 evidence",
        )
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v716-qca-bind-reconciliation-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair source evidence before choosing next live gate",
        )
    return (
        "v716-qca-child-unbound-not-bind-target",
        True,
        "V715 QCA child-unbound is reproduced, but V703 Android reference shows working netdevs under ICNSS parent and rejects QCA bind/unbind as next target",
        "target ICNSS-QMI/WLFW readiness trigger; keep QCA bind/unbind, HAL, scan/connect, DHCP, and external ping blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    android = manifest.get("android_reference") or {}
    android_rows = [
        ["has_icnss_parent_netdevs", str(android.get("has_icnss_parent_netdevs"))],
        ["rejects_qca_bind_target", str(android.get("rejects_qca_bind_target"))],
        ["has_android_wlfw_reference", str(android.get("has_android_wlfw_reference"))],
        ["netdev_line_count", str(len(android.get("netdev_lines") or []))],
        ["rejected_line_count", str(len(android.get("rejected_lines") or []))],
        ["wlfw_line_count", str(len(android.get("wlfw_lines") or []))],
    ]
    return "\n".join([
        "# V716 QCA Bind Reconciliation",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- v715_manifest: `{manifest.get('v715_manifest', '')}`",
        f"- v703_report: `{manifest.get('v703_report', '')}`",
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
        "## Android Reference",
        "",
        markdown_table(["item", "value"], android_rows),
        "",
        "## Guardrail",
        "",
        "- Do not write `bind`, `unbind`, or `driver_override` for `qca6390` based only on the missing child driver symlink.",
        "- Do not start Wi-Fi HAL, scan/connect, DHCP, route changes, or external ping until WLFW/BDF/fw-ready/`wlan0` advances.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v715_manifest_path = ""
    v703_report_path = ""
    v715: dict[str, Any] = {}
    v703: dict[str, Any] = {
        "netdev_lines": [],
        "rejected_lines": [],
        "wlfw_lines": [],
        "has_icnss_parent_netdevs": False,
        "rejects_qca_bind_target": False,
        "has_android_wlfw_reference": False,
    }
    checks: list[Check] = []
    if args.command == "run":
        v715_path = resolve_manifest(args.v715_source)
        v715_manifest_path = str(v715_path)
        v715 = load_json(v715_path)
        v703_report = repo_path(args.v703_report)
        v703_report_path = str(v703_report)
        v703 = android_reference(read_text(v703_report))
        checks = build_checks(v715, v703)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v716",
        "v715_source": str(args.v715_source),
        "v715_manifest": v715_manifest_path,
        "v703_report": v703_report_path,
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
        "v715_decision": v715.get("decision", ""),
        "android_reference": v703,
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
