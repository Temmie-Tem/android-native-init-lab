#!/usr/bin/env python3
"""V710 host-only classifier for the post-service74 pre-WLFW kernel event gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v710-kernel-event-source-classifier")
DEFAULT_V708_MANIFEST = Path(
    "tmp/wifi/v708-provider-first-cnss-v120-orchestrated-run-2/"
    "arm-v700-v119-provider-first-cnss/live/manifest.json"
)
DEFAULT_V708_DMESG = Path(
    "tmp/wifi/v708-provider-first-cnss-v120-orchestrated-run-2/"
    "arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt"
)
DEFAULT_V708_HELPER = Path(
    "tmp/wifi/v708-provider-first-cnss-v120-orchestrated-run-2/"
    "arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_V709_MANIFEST = Path("tmp/wifi/v709-v708-stall-classifier/manifest.json")
DEFAULT_ANDROID_MANIFEST = Path("tmp/wifi/v703-android-native-binding-compare/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
BLOCK_BEGIN_RE = re.compile(r"^A90_EXECNS_(?:DIR|PATH)_(?P<name>[A-Za-z0-9_]+)_BEGIN\b")
BLOCK_END_RE = re.compile(r"^A90_EXECNS_(?:DIR|PATH)_(?P<name>[A-Za-z0-9_]+)_END\b")

DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi: ssctl_new_server", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier:.*\b180 service\b", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier:.*\b74 service\b", re.I)),
    ("service_notifier_wlan_pd", re.compile(r"service-notifier:.*wlan[_/-]?pd|msm/modem/wlan_pd", re.I)),
    ("pd_notifier", re.compile(r"\bpd[_ -]?notifier\b|\bserver[_ -]?arriv", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*cld80211", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request|kernel/power/qos\.c:616", re.I)),
    ("icnss_qmi_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start|\bwlfw_start\b", re.I)),
    ("wlfw_service_request", re.compile(r"wlfw_.*req|WLFW.*service", re.I)),
    ("qca6390_power_or_bus", re.compile(r"qca6390|cnss.*power|wlan.*power|\bmhi\b|\bpcie\b", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|fw_ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v708-manifest", type=Path, default=DEFAULT_V708_MANIFEST)
    parser.add_argument("--v708-dmesg", type=Path, default=DEFAULT_V708_DMESG)
    parser.add_argument("--v708-helper", type=Path, default=DEFAULT_V708_HELPER)
    parser.add_argument("--v709-manifest", type=Path, default=DEFAULT_V709_MANIFEST)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path | str) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path | str) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_time(line: str) -> float | None:
    match = TS_RE.search(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    counts = {name: 0 for name, _ in DMESG_PATTERNS}
    first_times: dict[str, float | None] = {name: None for name, _ in DMESG_PATTERNS}
    first_lines = {name: "" for name, _ in DMESG_PATTERNS}
    focus_lines: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        matched = False
        for name, pattern in DMESG_PATTERNS:
            if pattern.search(line):
                counts[name] += 1
                if not first_lines[name]:
                    first_lines[name] = line[:360]
                    first_times[name] = line_time(line)
                matched = True
        if matched:
            focus_lines.append(line[:360])
    return {
        "counts": counts,
        "first_times": first_times,
        "first_lines": first_lines,
        "focus_tail": focus_lines[-120:],
    }


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000.0, 3)


def parse_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        begin = BLOCK_BEGIN_RE.match(line)
        if begin:
            current = begin.group("name")
            blocks.setdefault(current, [])
            continue
        end = BLOCK_END_RE.match(line)
        if end and current == end.group("name"):
            current = None
            continue
        if current is not None:
            blocks.setdefault(current, []).append(line)
    return blocks


def dir_entries(blocks: dict[str, list[str]], name: str) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    for line in blocks.get(name, []):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if key.startswith("entry.") and value not in seen:
            entries.append(value)
            seen.add(value)
    return entries


def path_value(blocks: dict[str, list[str]], name: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for line in blocks.get(name, []):
        value = line.strip()
        if value and value not in seen:
            lines.append(value)
            seen.add(value)
    return "\n".join(lines)


def manifest_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = manifest.get("live") or {}
    v655_counts = live.get("v655_counts") or {}
    marker_counts = ((live.get("markers") or {}).get("counts") or {})
    result: dict[str, int] = {}
    for key in (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
        "kernel_warning",
    ):
        try:
            result[key] = int(v655_counts.get(key, 0) or 0)
        except (TypeError, ValueError):
            result[key] = 0
    for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlfw", "bdf"):
        try:
            result[f"marker_{key}"] = int(marker_counts.get(key, 0) or 0)
        except (TypeError, ValueError):
            result[f"marker_{key}"] = 0
    return result


def android_input_dmesg(android_manifest: dict[str, Any]) -> str:
    inputs = android_manifest.get("inputs") or {}
    path = inputs.get("android_dmesg", "")
    return read_text(path) if path else ""


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    v708_manifest = load_json(args.v708_manifest)
    v709_manifest = load_json(args.v709_manifest)
    android_manifest = load_json(args.android_manifest)
    v708_dmesg = parse_dmesg(read_text(args.v708_dmesg))
    android_dmesg = parse_dmesg(android_input_dmesg(android_manifest))
    blocks = parse_blocks(read_text(args.v708_helper))
    qca_entries = dir_entries(blocks, "wifi_cnss2_focus_qca6390_device")
    icnss_entries = dir_entries(blocks, "wifi_cnss2_focus_icnss_device")
    net_entries = dir_entries(blocks, "wifi_cnss2_focus_net_class")
    qca_runtime_status = path_value(blocks, "wifi_cnss2_focus_qca6390_power_runtime_status").strip()
    icnss_runtime_status = path_value(blocks, "wifi_cnss2_focus_icnss_power_runtime_status").strip()
    android_surface = android_manifest.get("android_surface") or {}
    android_counts = ((android_surface.get("dmesg") or {}).get("counts") or {})
    return {
        "inputs": {
            "v708_manifest": str(repo_path(args.v708_manifest)),
            "v708_dmesg": str(repo_path(args.v708_dmesg)),
            "v708_helper": str(repo_path(args.v708_helper)),
            "v709_manifest": str(repo_path(args.v709_manifest)),
            "android_manifest": str(repo_path(args.android_manifest)),
        },
        "v708_decision": v708_manifest.get("decision", ""),
        "v708_pass": v708_manifest.get("pass"),
        "v709_decision": v709_manifest.get("decision", ""),
        "v709_pass": v709_manifest.get("pass"),
        "v709_reason": v709_manifest.get("reason", ""),
        "v708_manifest_counts": manifest_counts(v708_manifest),
        "v708_dmesg": v708_dmesg,
        "android_decision": android_manifest.get("decision", ""),
        "android_pass": android_manifest.get("pass"),
        "android_manifest_counts": android_counts,
        "android_dmesg": android_dmesg,
        "android_icnss_wlfw_positive": bool(android_surface.get("wlfw_progression_positive")),
        "android_wlan0_under_icnss": bool(android_surface.get("wlan0_under_icnss")),
        "android_netdevs": android_surface.get("icnss_wlan_netdevs") or [],
        "qca6390_entries": qca_entries,
        "icnss_entries": icnss_entries,
        "net_entries": net_entries,
        "qca6390_driver_symlink_visible": "driver" in qca_entries,
        "qca6390_node_visible": bool(qca_entries),
        "icnss_driver_symlink_visible": "driver" in icnss_entries,
        "wlan0_visible_native": "wlan0" in net_entries,
        "qca6390_runtime_status": qca_runtime_status,
        "icnss_runtime_status": icnss_runtime_status,
    }


def count(surface: dict[str, Any], bucket: str, key: str) -> int:
    if bucket == "v708_manifest":
        return int((surface.get("v708_manifest_counts") or {}).get(key, 0) or 0)
    return int((((surface.get(bucket) or {}).get("counts") or {}).get(key, 0)) or 0)


def key_deltas(surface: dict[str, Any]) -> dict[str, float | None]:
    native_times = (surface.get("v708_dmesg") or {}).get("first_times") or {}
    android_times = (surface.get("android_dmesg") or {}).get("first_times") or {}
    return {
        "native_service74_to_cnss_netlink": delta_ms(native_times.get("cnss_daemon_netlink"), native_times.get("service_notifier_74")),
        "native_service74_to_icnss_qmi": delta_ms(native_times.get("icnss_qmi_connected"), native_times.get("service_notifier_74")),
        "native_service74_to_wlfw": delta_ms(native_times.get("wlfw_start"), native_times.get("service_notifier_74")),
        "android_wlan_pd_to_icnss_qmi": delta_ms(android_times.get("icnss_qmi_connected"), android_times.get("service_notifier_wlan_pd")),
        "android_icnss_qmi_to_bdf_regdb": delta_ms(android_times.get("bdf_regdb"), android_times.get("icnss_qmi_connected")),
        "android_bdf_to_fw_ready": delta_ms(android_times.get("wlan_fw_ready"), android_times.get("bdf_bdwlan")),
        "android_fw_ready_to_wlan0": delta_ms(android_times.get("wlan0"), android_times.get("wlan_fw_ready")),
    }


def decide(command: str, surface: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v710-kernel-event-source-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only classifier against V708/V709 and Android reference evidence",
        )
    if not surface:
        return (
            "v710-kernel-event-source-input-missing",
            False,
            "required evidence surface was not built",
            "check evidence paths before live work",
        )
    service_gate = count(surface, "v708_manifest", "service_notifier_180") > 0 and count(surface, "v708_manifest", "service_notifier_74") > 0
    cnss_retry_waiting = surface.get("v709_decision") == "v709-cnss-retry-polling-pre-wlfw-kernel-event-gap"
    no_native_wlfw = all(
        count(surface, "v708_manifest", key) == 0
        for key in ("qmi_server_connected", "wlfw_start", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")
    )
    no_native_binder_fail = count(surface, "v708_manifest", "cnss_binder_transaction_failed") == 0
    qca_visible_unbound = bool(surface.get("qca6390_node_visible")) and not bool(surface.get("qca6390_driver_symlink_visible"))
    android_positive = (
        bool(surface.get("android_icnss_wlfw_positive"))
        or count(surface, "android_dmesg", "icnss_qmi_connected") > 0
        or count(surface, "android_dmesg", "wlan_fw_ready") > 0
        or count(surface, "android_dmesg", "wlan0") > 0
    )
    if service_gate and cnss_retry_waiting and no_native_wlfw and no_native_binder_fail and qca_visible_unbound and android_positive:
        return (
            "v710-missing-qca6390-wlfw-kernel-event-source",
            True,
            "native reaches service180/74, provider, and CNSS retry poll wait with no Binder failure, but QCA6390 remains unbound and WLFW/BDF/wlan0 are absent while Android reaches ICNSS-QMI/WLFW",
            "target the QCA6390 bind/power/MHI-or-ICNSS event edge before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        )
    if not service_gate:
        return (
            "v710-service-gate-missing-in-input",
            False,
            "V708 input does not prove both service-notifier 180 and 74",
            "refresh a service74-positive bounded run before classifying the post-service74 edge",
        )
    if not no_native_wlfw:
        return (
            "v710-native-wlfw-progressed-review-required",
            True,
            "native input contains WLFW/BDF/wlan0 progression markers",
            "review netdev and firmware-ready state before any connect path",
        )
    return (
        "v710-kernel-event-source-gap-inconclusive",
        True,
        "post-service74 pre-WLFW gap is present, but one of the attribution checks is missing",
        "capture the missing attribution surface without starting Wi-Fi HAL or connect path",
    )


def table_from_counts(counts: dict[str, Any]) -> list[list[str]]:
    return [[key, str(value)] for key, value in sorted(counts.items())]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    surface = None if args.command == "plan" else build_surface(args)
    decision, pass_ok, reason, next_step = decide(args.command, surface)
    return {
        "cycle": "v710",
        "created_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next": next_step,
        "evidence_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "surface": surface or {},
        "key_deltas_ms": key_deltas(surface) if surface else {},
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "dhcp_or_external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest.get("surface") or {}
    native_counts = surface.get("v708_manifest_counts") or {}
    native_dmesg_counts = ((surface.get("v708_dmesg") or {}).get("counts") or {})
    android_dmesg_counts = ((surface.get("android_dmesg") or {}).get("counts") or {})
    qca_rows = [
        ["qca6390_node_visible", str(surface.get("qca6390_node_visible", ""))],
        ["qca6390_driver_symlink_visible", str(surface.get("qca6390_driver_symlink_visible", ""))],
        ["qca6390_runtime_status", str(surface.get("qca6390_runtime_status", ""))],
        ["icnss_driver_symlink_visible", str(surface.get("icnss_driver_symlink_visible", ""))],
        ["wlan0_visible_native", str(surface.get("wlan0_visible_native", ""))],
        ["native_net_entries", ", ".join(surface.get("net_entries") or [])],
        ["android_netdevs", ", ".join(surface.get("android_netdevs") or [])],
    ]
    lines = [
        "# V710 Kernel Event Source Classifier",
        "",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next: {manifest.get('next')}",
        f"- evidence: `{manifest.get('evidence_dir')}`",
        "",
        "## Scope",
        "",
        "- host-only classification; no device command executed",
        "- no daemon start, Wi-Fi HAL start, scan/connect, DHCP, route change, external ping, sysfs write, or boot image write",
        "",
        "## Version Mapping",
        "",
        "- The V666/V667 pd-notifier question is already consumed by earlier evidence.",
        "- V710 reuses the same causal chain at the current V708/V709 stall point.",
        "- Android logs show BDF activity through `cnss-daemon` after ICNSS-QMI/WLFW readiness, so this classifier targets the missing prerequisite event instead of assuming BDF is kernel-only.",
        "",
        "## Native Manifest Counts",
        "",
        markdown_table(["marker", "count"], table_from_counts(native_counts)) if native_counts else "- not available",
        "",
        "## Native Dmesg Counts",
        "",
        markdown_table(["marker", "count"], table_from_counts(native_dmesg_counts)) if native_dmesg_counts else "- not available",
        "",
        "## Android Reference Counts",
        "",
        markdown_table(["marker", "count"], table_from_counts(android_dmesg_counts)) if android_dmesg_counts else "- not available",
        "",
        "## QCA/ICNSS Surface",
        "",
        markdown_table(["item", "value"], qca_rows),
        "",
        "## Key Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in manifest.get("key_deltas_ms", {}).items()]),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"dhcp_or_external_ping_executed: {manifest['dhcp_or_external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
