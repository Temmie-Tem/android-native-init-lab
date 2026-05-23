#!/usr/bin/env python3
"""V667 cnss2/WLAN-PD notifier progression classifier.

This classifier consumes V666 evidence and can optionally capture current
device read-only sysfs/dmesg surface. It does not write sysfs, open esoc0,
start daemons, start Wi-Fi HAL, scan, connect, run DHCP, change routes, or ping
externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v667-cnss2-pd-notifier-classifier")
DEFAULT_V666_MANIFEST = Path("tmp/wifi/v666-repaired-private-cnss-retry-live/manifest.json")
DEFAULT_V666_DMESG = Path("tmp/wifi/v666-repaired-private-cnss-retry-live/native/dmesg-delta.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 10.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_SHELL = "/cache/bin/busybox"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi: ssctl_new_server", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("pm_qos_warning", re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616|pm_qos_add_request", re.I)),
    ("cnss2_any", re.compile(r"\bcnss2\b|\bicnss\b|\bcnss_pci\b", re.I)),
    (
        "cnss2_server_arrive",
        re.compile(r"(cnss2|icnss|cnss).*server.*arriv|server_arrive.*(cnss|wlan|wlfw)", re.I),
    ),
    ("cnss2_pd_notifier", re.compile(r"pd_notifier|wlan[_ -]?pd|protection domain", re.I)),
    ("cnss2_power_on", re.compile(r"(cnss2|icnss|wlan|qca6390).*(power[_ -]?on|power on)|power[_ -]?on.*(wlan|cnss|qca6390)", re.I)),
    ("pcie_mhi", re.compile(r"\bpcie\b|\bmhi\b", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start|\bwlfw_start\b|\bWLFW\b", re.I)),
    ("wlfw_service_69", re.compile(r"service\s+69|WLFW.*service|wlfw.*service", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|fw_ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
)

TIMELINE = tuple(name for name, _ in PATTERNS)
PROGRESSION_MARKERS = (
    "cnss2_server_arrive",
    "cnss2_pd_notifier",
    "cnss2_power_on",
    "pcie_mhi",
    "qmi_server_connected",
    "wlfw_start",
    "wlfw_service_69",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
)
FORBIDDEN_ACTIONS = (
    "sysfs write",
    "esoc0 open/hold",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v666-manifest", type=Path, default=DEFAULT_V666_MANIFEST)
    parser.add_argument("--v666-dmesg", type=Path, default=DEFAULT_V666_DMESG)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--shell", default=DEFAULT_SHELL)
    parser.add_argument(
        "--capture-current-readonly",
        action="store_true",
        help="capture current device sysfs/dmesg read-only surface; no writes or daemon starts",
    )
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    counts = {marker: 0 for marker in TIMELINE}
    first_times: dict[str, float | None] = {marker: None for marker in TIMELINE}
    first_lines = {marker: "missing" for marker in TIMELINE}
    focus_lines: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        matched_any = False
        for marker, pattern in PATTERNS:
            if pattern.search(line):
                counts[marker] += 1
                if first_lines[marker] == "missing":
                    first_lines[marker] = line
                    first_times[marker] = line_time(line)
                matched_any = True
        if matched_any and len(focus_lines) < 260:
            focus_lines.append(line)
    return {
        "counts": counts,
        "first_times": first_times,
        "first_lines": first_lines,
        "focus_lines": focus_lines,
    }


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000.0, 3)


def timeline_rows(parsed: dict[str, Any]) -> list[list[str]]:
    counts = parsed["counts"]
    first_times = parsed["first_times"]
    first_lines = parsed["first_lines"]
    return [
        [
            marker,
            str(counts.get(marker, 0)),
            "" if first_times.get(marker) is None else f"{first_times[marker]:.6f}",
            first_lines.get(marker, "missing"),
        ]
        for marker in TIMELINE
    ]


def key_deltas(parsed: dict[str, Any]) -> dict[str, float | None]:
    first_times = parsed["first_times"]
    return {
        "service180_to_service74": delta_ms(first_times["service_notifier_74"], first_times["service_notifier_180"]),
        "service74_to_pm_qos_warning": delta_ms(first_times["pm_qos_warning"], first_times["service_notifier_74"]),
        "service74_to_cnss_daemon_netlink": delta_ms(first_times["cnss_daemon_netlink"], first_times["service_notifier_74"]),
        "service74_to_cnss2_server_arrive": delta_ms(first_times["cnss2_server_arrive"], first_times["service_notifier_74"]),
        "service74_to_pd_notifier": delta_ms(first_times["cnss2_pd_notifier"], first_times["service_notifier_74"]),
        "service74_to_power_on": delta_ms(first_times["cnss2_power_on"], first_times["service_notifier_74"]),
        "service74_to_wlfw": delta_ms(first_times["wlfw_start"], first_times["service_notifier_74"]),
    }


def capture_current_readonly(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    commands = {
        "current-subsys-states": [
            "run",
            args.shell,
            "sh",
            "-c",
            (
                f"BB={args.shell}; "
                "for d in /sys/bus/msm_subsys/devices/*; do "
                "[ -e \"$d\" ] || continue; "
                "printf '== %s ==\\n' \"$d\"; "
                "printf 'name='; \"$BB\" cat \"$d/name\" 2>/dev/null || true; "
                "printf 'state='; \"$BB\" cat \"$d/state\" 2>/dev/null || true; "
                "done"
            ),
        ],
        "current-cnss2-sysfs": [
            "run",
            args.shell,
            "sh",
            "-c",
            (
                f"BB={args.shell}; "
                "for d in /sys/bus/platform/drivers/cnss2 "
                "/sys/bus/platform/drivers/*cnss* "
                "/sys/bus/platform/devices/*cnss* "
                "/sys/class/net/wlan0; do "
                "[ -e \"$d\" ] || continue; "
                "printf '== %s ==\\n' \"$d\"; "
                "\"$BB\" ls -la \"$d\" 2>/dev/null || true; "
                "\"$BB\" ls -la \"$d\"/ 2>/dev/null || true; "
                "done"
            ),
        ],
        "current-cnss-dmesg-tail": [
            "run",
            args.shell,
            "sh",
            "-c",
            (
                f"BB={args.shell}; "
                "\"$BB\" dmesg | \"$BB\" grep -i -E "
                "'cnss|wlan|wlfw|pd_notifier|server_arrive|service-notifier|mhi|pcie|qca6390' "
                "| \"$BB\" tail -220"
            ),
        ],
    }
    captures: dict[str, Any] = {}
    for name, command in commands.items():
        capture = run_capture(args, name, command, timeout=args.timeout)
        store.write_text(f"current/{name}.txt", capture.text or capture.error)
        stripped = strip_cmdv1_text(capture.text) if capture.text else capture.error
        captures[name] = {
            **capture_to_manifest(capture),
            "stripped_text": stripped[:4096],
            "stripped_truncated": len(stripped) > 4096,
        }
    return captures


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v666_manifest = load_json(args.v666_manifest)
    parsed = parse_dmesg(read_text(args.v666_dmesg))
    counts = parsed["counts"]
    service_gate_positive = counts["service_notifier_180"] > 0 and counts["service_notifier_74"] > 0
    progression_positive = any(counts.get(marker, 0) > 0 for marker in PROGRESSION_MARKERS)
    wlfw_positive = any(counts.get(marker, 0) > 0 for marker in ("wlfw_start", "wlfw_service_69", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0"))

    current = capture_current_readonly(args, store) if args.command == "run" and args.capture_current_readonly else {}
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v667-cnss2-pd-notifier-classifier-plan-ready",
            True,
            "plan-only; no evidence classification or device command executed",
            "run V667 host-only classifier, then optionally capture current read-only cnss2/sysfs surface",
        )
    elif service_gate_positive and not progression_positive:
        decision, pass_ok, reason, next_step = (
            "v667-cnss2-pd-notifier-gap-classified",
            True,
            "V666 reached service-notifier 180/74 but no cnss2 pd_notifier, power-on, PCIe/MHI, WLFW, BDF, fw_ready, or wlan0 marker followed",
            "plan the next bounded live gate around cnss2/WLAN-PD kernel progression before another binder-only retry",
        )
    elif service_gate_positive and progression_positive and not wlfw_positive:
        decision, pass_ok, reason, next_step = (
            "v667-cnss2-progression-without-wlfw-classified",
            True,
            "cnss2/WLAN-PD progression markers exist but WLFW/BDF/wlan0 markers are still missing",
            "classify QCA6390/WLFW boot and firmware download gap before Wi-Fi HAL or scan/connect",
        )
    elif service_gate_positive and wlfw_positive:
        decision, pass_ok, reason, next_step = (
            "v667-wlfw-advanced-review-next-gate",
            True,
            "V666 evidence contains WLFW/BDF/fw_ready/wlan0 advancement",
            "review evidence and plan the first tightly bounded Wi-Fi HAL or netdev gate",
        )
    else:
        decision, pass_ok, reason, next_step = (
            "v667-service-notifier-baseline-missing",
            False,
            "V666 evidence does not show both service-notifier 180 and 74, so cnss2 progression cannot be classified from this input",
            "refresh a clean service74-positive live evidence bundle before V667 classification",
        )

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v666_manifest": str(repo_path(args.v666_manifest)),
            "v666_dmesg": str(repo_path(args.v666_dmesg)),
        },
        "source_decision": v666_manifest.get("decision"),
        "source_pass": v666_manifest.get("pass"),
        "source_private_runtime_ready": v666_manifest.get("private_runtime_ready"),
        "parsed": parsed,
        "timeline_rows": timeline_rows(parsed),
        "key_deltas_ms": key_deltas(parsed),
        "service_gate_positive": service_gate_positive,
        "progression_positive": progression_positive,
        "wlfw_positive": wlfw_positive,
        "progression_markers": list(PROGRESSION_MARKERS),
        "current_readonly": current,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": bool(current),
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V667 cnss2/WLAN-PD Notifier Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Source",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["source_decision", str(manifest["source_decision"])],
                ["source_pass", str(manifest["source_pass"])],
                ["source_private_runtime_ready", str(manifest["source_private_runtime_ready"])],
                ["v666_dmesg", manifest["inputs"]["v666_dmesg"]],
            ],
        ),
        "",
        "## Key Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in manifest["key_deltas_ms"].items()]),
        "",
        "## Timeline Counts",
        "",
        markdown_table(["marker", "count", "first_ts", "first_line"], manifest["timeline_rows"]),
        "",
        "## Interpretation",
        "",
        "- V666 is service-notifier positive for both `180` and `74`.",
        "- The classifier separates userspace-visible service publication from cnss2 kernel progression.",
        "- If cnss2 `pd_notifier`/power/PCIe/MHI/WLFW markers are absent, another binder-only retry is not the shortest path.",
        "- The next live gate should target read-only cnss2/sysfs and tightly bounded kernel-progression evidence before Wi-Fi HAL or scan/connect.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
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
