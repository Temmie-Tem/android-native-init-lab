#!/usr/bin/env python3
"""V719 host-only reconciliation of service-positive and current-boot CNSS2 evidence."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v719-cnss2-service-positive-reconcile")
DEFAULT_SERVICE_SOURCE = Path("tmp/wifi/latest-v717-icnss-edge-long-observe.txt")
DEFAULT_CURRENT_SOURCE = Path("tmp/wifi/latest-v718-cnss2-pd-notifier-readonly-current.txt")
DMESG_NAME_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0", re.I)),
    ("service_locator", re.compile(r"service[-_ ]?locator|servreg", re.I)),
    ("service_state_up", re.compile(r"SERVICE_STATE_UP|service.*state.*up|servreg.*up", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("pd_notifier", re.compile(r"\bpd[_ -]?notifier\b|\bserver[_ -]?arrive\b", re.I)),
    (
        "qca6390_power",
        re.compile(
            r"(icnss|cnss2|cnss|qca6390|wlan).*(power[_ -]?on|power on|powering)|"
            r"(power[_ -]?on|power on|powering).*(icnss|cnss2|cnss|qca6390|wlan)",
            re.I,
        ),
    ),
    (
        "qca6390_mhi_pcie",
        re.compile(
            r"(icnss|cnss2|cnss|qca6390|wlan).*(MHI|PCIe|pcie)|"
            r"(MHI|PCIe|pcie).*(icnss|cnss2|cnss|qca6390|wlan)",
            re.I,
        ),
    ),
    ("icnss_qmi", re.compile(r"icnss[_ -]?qmi|QMI Server Connected", re.I)),
    ("wlfw", re.compile(r"\bWLFW\b|wlfw", re.I)),
    ("bdf", re.compile(r"BDF file|bdwlan\.bin|regdb\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|fw_ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request|Reference count mismatch|subsystem_put", re.I)),
)
KERNEL_PROGRESSION = (
    "pd_notifier",
    "qca6390_power",
    "qca6390_mhi_pcie",
    "icnss_qmi",
    "wlfw",
    "bdf",
    "wlan_fw_ready",
    "wlan0",
)


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
    parser.add_argument("--service-source", type=Path, default=DEFAULT_SERVICE_SOURCE)
    parser.add_argument("--current-source", type=Path, default=DEFAULT_CURRENT_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def resolve_pointer(source: Path) -> Path:
    resolved = repo_path(source)
    if resolved.is_file() and resolved.name != "manifest.json":
        text = resolved.read_text(encoding="utf-8").strip()
        if text:
            return repo_path(Path(text))
    return resolved


def resolve_manifest(source: Path) -> tuple[Path, Path]:
    target = resolve_pointer(source)
    if target.is_dir():
        return target, target / "manifest.json"
    if target.name == "manifest.json":
        return target.parent, target
    return target.parent, target


def nested_service_manifest(run_dir: Path, top_manifest: dict[str, Any]) -> Path:
    for key in ("arm_v700", "arm_v712"):
        value = top_manifest.get(key)
        if isinstance(value, dict) and value.get("manifest"):
            manifest = repo_path(Path(str(value["manifest"])))
            if manifest.exists():
                return manifest
    candidates = sorted(run_dir.glob("arm-*/live/manifest.json"))
    return candidates[0] if candidates else run_dir / "manifest.json"


def service_dmesg_path(service_manifest: Path) -> Path:
    return service_manifest.parent / "native" / "dmesg-delta.txt"


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_ts(line: str) -> float | None:
    match = DMESG_NAME_RE.search(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in MARKERS}
    focus: list[str] = []
    for index, raw_line in enumerate(text.splitlines()):
        line = clean_line(raw_line)
        if not line:
            continue
        matched = False
        for name, pattern in MARKERS:
            if pattern.search(line):
                events[name].append({"index": index, "ts": line_ts(line), "line": line[:360]})
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "focus_tail": focus[-160:],
    }


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def live_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = manifest.get("live") if isinstance(manifest.get("live"), dict) else {}
    counts = live.get("v655_counts") if isinstance(live.get("v655_counts"), dict) else {}
    return {key: int_value(value) for key, value in counts.items()}


def companion_keys(manifest: dict[str, Any]) -> dict[str, str]:
    live = manifest.get("live") if isinstance(manifest.get("live"), dict) else {}
    keys = live.get("companion_keys") if isinstance(live.get("companion_keys"), dict) else {}
    return {str(key): str(value) for key, value in keys.items()}


def service_surface(top_source: Path) -> dict[str, Any]:
    run_dir, top_path = resolve_manifest(top_source)
    top = load_json(top_path)
    nested = nested_service_manifest(run_dir, top)
    arm = load_json(nested)
    keys = companion_keys(arm)
    dmesg_path = service_dmesg_path(nested)
    dmesg = parse_dmesg(read_text(dmesg_path))
    counts = dmesg["counts"]
    helper_counts = live_counts(arm)
    service180 = counts.get("service_notifier_180", 0) > 0 or helper_counts.get("service_notifier_180", 0) > 0
    service74 = counts.get("service_notifier_74", 0) > 0 or helper_counts.get("service_notifier_74", 0) > 0
    kernel_progression = any(int_value(counts.get(name)) > 0 for name in KERNEL_PROGRESSION)
    return {
        "run_dir": str(run_dir),
        "top_manifest": str(top_path),
        "arm_manifest": str(nested),
        "dmesg_delta": str(dmesg_path),
        "top_decision": top.get("decision"),
        "top_pass": top.get("pass"),
        "arm_decision": arm.get("decision"),
        "arm_pass": arm.get("pass"),
        "helper_counts": helper_counts,
        "companion_order": keys.get("wifi_companion_start.order", ""),
        "qrtr_ns_observable": keys.get("wifi_companion_start.child.qrtr_ns.observable") == "1",
        "qrtr_ns_postflight_safe": keys.get("wifi_companion_start.child.qrtr_ns.postflight_safe") == "1",
        "qrtr_ns_start_order": keys.get("wifi_companion_start.child.qrtr_ns.start_order", ""),
        "service74_gate_status": keys.get("wifi_companion_start.service74_gate.status", ""),
        "service74_gate_open": keys.get("wifi_companion_start.service74_gate.open", ""),
        "dmesg": dmesg,
        "service180": service180,
        "service74": service74,
        "service_positive": service180 and service74,
        "kernel_progression": kernel_progression,
        "wlfw_or_wlan0": any(int_value(counts.get(name)) > 0 for name in ("wlfw", "bdf", "wlan_fw_ready", "wlan0"))
        or any(helper_counts.get(name, 0) > 0 for name in ("wlfw_start", "wlfw_service_request", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")),
    }


def current_surface(current_source: Path) -> dict[str, Any]:
    run_dir, manifest_path = resolve_manifest(current_source)
    manifest = load_json(manifest_path)
    surface = manifest.get("surface") if isinstance(manifest.get("surface"), dict) else {}
    dmesg = surface.get("dmesg") if isinstance(surface.get("dmesg"), dict) else {}
    counts = dmesg.get("counts") if isinstance(dmesg.get("counts"), dict) else {}
    busy_steps = surface.get("busy_steps") if isinstance(surface.get("busy_steps"), list) else []
    failed_steps = surface.get("failed_steps") if isinstance(surface.get("failed_steps"), list) else []
    return {
        "run_dir": str(run_dir),
        "manifest": str(manifest_path),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "busy_steps": busy_steps,
        "failed_steps": failed_steps,
        "mss_state": surface.get("mss_state", ""),
        "mdm3_state": surface.get("mdm3_state", ""),
        "wlan0_visible": bool(surface.get("wlan0_visible")),
        "qrtr_service69_visible": bool(surface.get("qrtr_service69_visible")),
        "dmesg_counts": {key: int_value(value) for key, value in counts.items()},
        "capture_clean": not busy_steps and not failed_steps,
        "service_positive": int_value(counts.get("service_notifier_180")) > 0 and int_value(counts.get("service_notifier_74")) > 0,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(service: dict[str, Any], current: dict[str, Any]) -> list[Check]:
    service_counts = service["dmesg"]["counts"]
    current_counts = current["dmesg_counts"]
    checks: list[Check] = []
    add_check(
        checks,
        "service-positive-window",
        "pass" if service["service_positive"] else "blocked",
        "blocker",
        f"service180={service['service180']} service74={service['service74']}",
        [service["arm_manifest"], service["dmesg_delta"]],
        "refresh provider-first service74-positive evidence before interpreting CNSS2 trigger",
    )
    add_check(
        checks,
        "qrtr-ns-observable",
        "pass" if service.get("qrtr_ns_observable") else "finding",
        "info",
        (
            f"observable={service.get('qrtr_ns_observable')} "
            f"postflight_safe={service.get('qrtr_ns_postflight_safe')} "
            f"start_order={service.get('qrtr_ns_start_order')}"
        ),
        [service["arm_manifest"]],
        "if false, service-locator cannot be trusted; repair QRTR nameservice startup first",
    )
    add_check(
        checks,
        "service-locator-servreg-visible",
        "pass" if service_counts.get("service_locator", 0) > 0 or service_counts.get("service_state_up", 0) > 0 else "finding",
        "info",
        f"service_locator={service_counts.get('service_locator', 0)} service_state_up={service_counts.get('service_state_up', 0)} wlan_pd={service_counts.get('wlan_pd', 0)}",
        [service["dmesg_delta"]],
        "if absent with service 180/74 present, target SERVREG/service-locator indication path before HAL/connect",
    )
    add_check(
        checks,
        "service-positive-no-kernel-progression",
        "finding" if not service["kernel_progression"] else "pass",
        "info",
        "; ".join(f"{name}={service_counts.get(name, 0)}" for name in KERNEL_PROGRESSION),
        [service["dmesg_delta"]],
        "next live gate must instrument CNSS2 notifier-to-QCA transition",
    )
    add_check(
        checks,
        "service-positive-no-wlfw-or-wlan0",
        "finding" if not service["wlfw_or_wlan0"] else "pass",
        "info",
        f"wlfw_or_wlan0={service['wlfw_or_wlan0']}",
        [service["arm_manifest"]],
        "keep scan/connect blocked until WLFW/BDF/fw_ready/wlan0 advances",
    )
    add_check(
        checks,
        "current-readonly-clean",
        "pass" if current["capture_clean"] else "blocked",
        "blocker",
        f"busy={current['busy_steps']} failed={current['failed_steps']}",
        [current["manifest"]],
        "rerun hardened V706 before using current-boot negative evidence",
    )
    add_check(
        checks,
        "current-boot-lower-not-ready",
        "finding" if not current["service_positive"] else "pass",
        "info",
        (
            f"current_service180={current_counts.get('service_notifier_180', 0)} "
            f"current_service74={current_counts.get('service_notifier_74', 0)} "
            f"mss={current['mss_state']} mdm3={current['mdm3_state']}"
        ),
        [current["manifest"]],
        "reproduce lower modem/WLAN-PD readiness in the same boot before another connect attempt",
    )
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, service: dict[str, Any] | None, current: dict[str, Any] | None, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v719-cnss2-service-positive-reconcile-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only reconciliation on V717 service-positive and V718 current-boot evidence",
        )
    if service is None or current is None:
        return "v719-input-missing", False, "required input manifest/evidence missing", "refresh V717/V718 evidence"
    blocked = blockers(checks)
    if blocked:
        return "v719-cnss2-reconcile-blocked", False, "blocked by " + ", ".join(blocked), "refresh missing evidence"
    if (
        service["service_positive"]
        and service.get("qrtr_ns_observable")
        and not service["kernel_progression"]
        and not current["service_positive"]
    ):
        return (
            "v719-qrtr-ns-present-servreg-cnss2-trigger-gap-classified",
            True,
            "service-positive evidence has qrtr-ns observable and 180/74, but no SERVREG/WLAN-PD/CNSS2/QCA/WLFW/wlan0 progression; current boot is lower-not-ready",
            "build next live gate around SERVREG/service-locator indication and CNSS2 notifier instrumentation in the same lower-ready window",
        )
    if service["service_positive"] and not service["kernel_progression"] and not current["service_positive"]:
        return (
            "v719-service-positive-cnss2-trigger-gap-classified",
            True,
            "service-positive evidence has 180/74 but no pd_notifier/QCA power/MHI/WLFW/wlan0; current boot is lower-not-ready",
            "build next live gate around same-window CNSS2 notifier instrumentation after lower readiness is reproduced",
        )
    if service["service_positive"] and service["kernel_progression"] and not service["wlfw_or_wlan0"]:
        return (
            "v719-kernel-progressed-pre-wlfw-gap",
            True,
            "kernel progression markers exist but WLFW/BDF/wlan0 are still absent",
            "target QCA6390 WLFW boot/BDF transfer before Wi-Fi HAL/scan/connect",
        )
    if service["wlfw_or_wlan0"]:
        return (
            "v719-wlfw-or-wlan0-progressed",
            True,
            "WLFW/BDF/fw_ready/wlan0 progressed in service-positive evidence",
            "move to wlan0 readiness classifier before scan/connect",
        )
    return (
        "v719-cnss2-reconcile-review",
        True,
        "inputs are valid but do not match the canonical V717/V718 shape",
        "inspect summary and choose next bounded gate manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    service = manifest.get("service_positive") or {}
    current = manifest.get("current_boot") or {}
    service_counts = ((service.get("dmesg") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    service_rows = [
        ["service_source", service.get("run_dir", "")],
        ["arm_manifest", service.get("arm_manifest", "")],
        ["dmesg_delta", service.get("dmesg_delta", "")],
        ["arm_decision", service.get("arm_decision", "")],
        ["service_positive", str(service.get("service_positive"))],
        ["companion_order", service.get("companion_order", "")],
        ["qrtr_ns_observable", str(service.get("qrtr_ns_observable"))],
        ["qrtr_ns_postflight_safe", str(service.get("qrtr_ns_postflight_safe"))],
        ["service74_gate_status", service.get("service74_gate_status", "")],
        ["kernel_progression", str(service.get("kernel_progression"))],
        ["wlfw_or_wlan0", str(service.get("wlfw_or_wlan0"))],
    ]
    current_rows = [
        ["current_source", current.get("run_dir", "")],
        ["decision", current.get("decision", "")],
        ["capture_clean", str(current.get("capture_clean"))],
        ["mss_state", current.get("mss_state", "")],
        ["mdm3_state", current.get("mdm3_state", "")],
        ["current_service180", str((current.get("dmesg_counts") or {}).get("service_notifier_180", 0))],
        ["current_service74", str((current.get("dmesg_counts") or {}).get("service_notifier_74", 0))],
        ["wlan0_visible", str(current.get("wlan0_visible"))],
        ["qrtr_service69_visible", str(current.get("qrtr_service69_visible"))],
    ]
    marker_rows = [[name, str(service_counts.get(name, 0))] for name, _ in MARKERS]
    return "\n".join([
        "# V719 CNSS2 Service-positive Reconciliation",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Service-positive Input",
        "",
        markdown_table(["key", "value"], service_rows),
        "",
        "## Service-positive Dmesg Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Current-boot Read-only Input",
        "",
        markdown_table(["key", "value"], current_rows),
        "",
        "## Interpretation",
        "",
        "- Service `180/74` visibility and kernel CNSS2 progression are separate gates.",
        "- Post-reboot current-boot absence of service `180/74` must not overwrite same-window service-positive evidence.",
        "- The next live step must reproduce lower readiness and instrument the notifier-to-QCA edge in that same window.",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    service: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    checks: list[Check] = []
    if args.command == "run":
        service = service_surface(args.service_source)
        current = current_surface(args.current_source)
        checks = build_checks(service, current)
    decision, pass_ok, reason, next_step = decide(args.command, service, current, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v719",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "service_source": str(repo_path(args.service_source)),
            "current_source": str(repo_path(args.current_source)),
        },
        "service_positive": service or {},
        "current_boot": current or {},
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
