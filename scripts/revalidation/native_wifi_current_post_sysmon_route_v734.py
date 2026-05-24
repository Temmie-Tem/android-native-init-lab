#!/usr/bin/env python3
"""V734 current-build post-sysmon route classifier.

This host-only classifier compares current V733 with prior Android/native
evidence to choose the next live gate toward native Wi-Fi bring-up.

It does not contact the device, write sysfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v734-current-post-sysmon-route")
DEFAULT_V733_MANIFEST = Path("tmp/wifi/v733-holder-lower-companion/manifest.json")
DEFAULT_V733_DIR = Path("tmp/wifi/v733-holder-lower-companion")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_ANDROID_V622_DIR = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run"
)
DEFAULT_V625_MANIFEST = Path("tmp/wifi/v625-fresh-v598-class-live/manifest.json")
DEFAULT_V625_DIR = Path("tmp/wifi/v625-fresh-v598-class-live")
DEFAULT_V627_MANIFEST = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
DEFAULT_V627_DIR = Path("tmp/wifi/v627-post-180-observer-live-v2")
DEFAULT_V620_MANIFEST = Path("tmp/wifi/v620-dsp-mdm3-safety-classifier-current-request-20260523/manifest.json")
DEFAULT_V623_MANIFEST = Path("tmp/wifi/v623-lower-publication-gap-classifier/manifest.json")
DEFAULT_V624_MANIFEST = Path("tmp/wifi/v624-safe-positive-regression-classifier/manifest.json")
DEFAULT_V626_MANIFEST = Path("tmp/wifi/v626-post-180-publication-classifier/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_esoc0", re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server: Connection established", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("rmt_storage_ready", re.compile(r"rmt_storage:INFO:main: Done with init", re.I)),
    ("rmt_storage_open", re.compile(r"rmt_storage_open_cb: Processing: Open Request", re.I)),
    ("cnss_diag_netlink", re.compile(r"cnss_diag|wlan_cnss.*netlink", re.I)),
    ("cnss_daemon_netlink", re.compile(r"cnss-daemon|cnss_daemon|wlan_cnss.*netlink", re.I)),
    ("binder_failure", re.compile(r"binder.*(?:failed|-22)|transaction failed", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request|WARNING: CPU", re.I)),
)

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "boot_wlan/qcwlanstate write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v733-manifest", type=Path, default=DEFAULT_V733_MANIFEST)
    parser.add_argument("--v733-dir", type=Path, default=DEFAULT_V733_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--android-v622-dir", type=Path, default=DEFAULT_ANDROID_V622_DIR)
    parser.add_argument("--v625-manifest", type=Path, default=DEFAULT_V625_MANIFEST)
    parser.add_argument("--v625-dir", type=Path, default=DEFAULT_V625_DIR)
    parser.add_argument("--v627-manifest", type=Path, default=DEFAULT_V627_MANIFEST)
    parser.add_argument("--v627-dir", type=Path, default=DEFAULT_V627_DIR)
    parser.add_argument("--v620-manifest", type=Path, default=DEFAULT_V620_MANIFEST)
    parser.add_argument("--v623-manifest", type=Path, default=DEFAULT_V623_MANIFEST)
    parser.add_argument("--v624-manifest", type=Path, default=DEFAULT_V624_MANIFEST)
    parser.add_argument("--v626-manifest", type=Path, default=DEFAULT_V626_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path | str) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path | str) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_events(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in MARKERS}
    focus: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line or line.startswith("$ "):
            continue
        matched = False
        for name, pattern in MARKERS:
            if pattern.search(line):
                events[name].append({"ts": line_time(line), "line": line[:360]})
                matched = True
        if matched:
            focus.append(line[:360])
    first = {name: rows[0] for name, rows in events.items() if rows}
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: row["ts"] for name, row in first.items() if row["ts"] is not None},
        "first_lines": {name: row["line"] for name, row in first.items()},
        "focus_tail": focus[-120:],
    }


def delta_ms(events: dict[str, Any], newer: str, older: str) -> float | None:
    times = events.get("first_ts") or {}
    if newer not in times or older not in times:
        return None
    return round((times[newer] - times[older]) * 1000.0, 3)


def marker_count_from_manifest(manifest: dict[str, Any], key: str) -> int:
    counts = (((manifest.get("live") or {}).get("markers") or {}).get("counts") or {})
    value = counts.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def safe_get(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def android_text(android_dir: Path) -> str:
    commands = repo_path(android_dir) / "android" / "commands"
    return "\n".join([
        read_text(commands / "dmesg-lower-surface-tail.txt"),
        read_text(commands / "dmesg-unfiltered-tail.txt"),
    ])


def native_text(run_dir: Path, companion_name: str | None = None) -> str:
    native = repo_path(run_dir) / "native"
    parts = [
        read_text(native / "dmesg-delta.txt"),
        read_text(native / "proc-net-qrtr-after-companion.txt"),
        read_text(native / "rpmsg-after-companion.txt"),
    ]
    if companion_name:
        parts.append(read_text(native / companion_name))
    return "\n".join(parts)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def input_summary(args: argparse.Namespace) -> dict[str, Any]:
    v733 = load_json(args.v733_manifest)
    android = load_json(args.android_v622_manifest)
    v625 = load_json(args.v625_manifest)
    v627 = load_json(args.v627_manifest)
    v620 = load_json(args.v620_manifest)
    v623 = load_json(args.v623_manifest)
    v624 = load_json(args.v624_manifest)
    v626 = load_json(args.v626_manifest)

    android_events = parse_events(android_text(args.android_v622_dir))
    v733_events = parse_events(native_text(args.v733_dir, "lower-companion-start-only.txt"))
    v625_events = parse_events(native_text(args.v625_dir, "companion-start-only.txt"))
    v627_events = parse_events(native_text(args.v627_dir, "companion-start-only.txt"))

    android_summary = android.get("android_summary") or {}
    android_timing = android_summary.get("timing") or {}
    android_deltas = android_summary.get("deltas_ms") or {}
    v733_live = v733.get("live") or {}
    v733_helper = v733_live.get("helper_result") or {}
    v625_live = v625.get("live") or {}
    v627_live = v627.get("live") or {}

    return {
        "v733": {
            "decision": v733.get("decision"),
            "pass": v733.get("pass"),
            "mss": [v733_live.get("mss_before"), v733_live.get("mss_after_holder"), v733_live.get("mss_after_companion")],
            "mdm3": [v733_live.get("mdm3_before"), v733_live.get("mdm3_after_holder"), v733_live.get("mdm3_after_companion")],
            "helper": {
                "mode": v733_helper.get("mode"),
                "order": v733_helper.get("order"),
                "child_started": v733_helper.get("child_started"),
                "all_observable": v733_helper.get("all_observable"),
                "all_postflight_safe": v733_helper.get("all_postflight_safe"),
                "cnss_daemon": v733_helper.get("cnss_daemon"),
                "service_manager": v733_helper.get("service_manager"),
                "wifi_hal": v733_helper.get("wifi_hal"),
                "scan_connect_linkup": v733_helper.get("scan_connect_linkup"),
                "external_ping": v733_helper.get("external_ping"),
                "qmi_attempted": v733_helper.get("qmi_attempted"),
            },
            "manifest_counts": ((v733_live.get("markers") or {}).get("counts") or {}),
            "event_counts": v733_events["counts"],
            "deltas_ms": {
                "qrtr_tx_to_sysmon_modem": delta_ms(v733_events, "sysmon_modem", "qrtr_tx"),
                "sysmon_modem_to_service_notifier_180": delta_ms(v733_events, "service_notifier_180", "sysmon_modem"),
            },
            "first_lines": v733_events["first_lines"],
        },
        "android_v622": {
            "decision": android.get("decision"),
            "pass": android.get("pass"),
            "mss_state": android_summary.get("mss_state"),
            "mdm3_state": android_summary.get("mdm3_state"),
            "counts": {**(android_events["counts"]), **(android_summary.get("counts") or {})},
            "timing_ms": android_timing,
            "deltas_ms": android_deltas,
            "event_deltas_ms": {
                "sysmon_modem_to_service_notifier_180": delta_ms(android_events, "service_notifier_180", "sysmon_modem"),
                "service_notifier_180_to_service_notifier_74": delta_ms(android_events, "service_notifier_74", "service_notifier_180"),
                "service_notifier_180_to_wlan_pd": delta_ms(android_events, "wlan_pd", "service_notifier_180"),
                "service_notifier_180_to_sysmon_esoc0": delta_ms(android_events, "sysmon_esoc0", "service_notifier_180"),
            },
            "first_lines": android_events["first_lines"],
        },
        "v625": {
            "decision": v625.get("decision"),
            "pass": v625.get("pass"),
            "mss_after_companion": v625_live.get("mss_after_companion"),
            "mdm3_after_companion": v625_live.get("mdm3_after_companion"),
            "manifest_counts": ((v625_live.get("markers") or {}).get("counts") or {}),
            "event_counts": v625_events["counts"],
            "deltas_ms": {
                "sysmon_modem_to_service_notifier_180": delta_ms(v625_events, "service_notifier_180", "sysmon_modem"),
                "service_notifier_180_to_service_notifier_74": delta_ms(v625_events, "service_notifier_74", "service_notifier_180"),
            },
            "first_lines": v625_events["first_lines"],
        },
        "v627": {
            "decision": v627.get("decision"),
            "pass": v627.get("pass"),
            "mss_after_companion": v627_live.get("mss_after_companion"),
            "mdm3_after_companion": v627_live.get("mdm3_after_companion"),
            "manifest_counts": ((v627_live.get("markers") or {}).get("counts") or {}),
            "event_counts": v627_events["counts"],
            "post_180_observer": v627_live.get("post_180_observer") or {},
            "deltas_ms": {
                "sysmon_modem_to_service_notifier_180": delta_ms(v627_events, "service_notifier_180", "sysmon_modem"),
                "service_notifier_180_to_service_notifier_74": delta_ms(v627_events, "service_notifier_74", "service_notifier_180"),
            },
            "first_lines": v627_events["first_lines"],
        },
        "prior": {
            "v620": {"decision": v620.get("decision"), "pass": v620.get("pass")},
            "v623": {"decision": v623.get("decision"), "pass": v623.get("pass")},
            "v624": {"decision": v624.get("decision"), "pass": v624.get("pass")},
            "v626": {"decision": v626.get("decision"), "pass": v626.get("pass")},
        },
    }


def evidence_rows(summary: dict[str, Any]) -> list[list[str]]:
    v733 = summary["v733"]
    android = summary["android_v622"]
    v625 = summary["v625"]
    v627 = summary["v627"]
    return [
        [
            "current lower-only V733",
            "safe post-sysmon advance only",
            (
                f"qrtr_rx/tx/sysmon={v733['manifest_counts'].get('qrtr_rx')}/"
                f"{v733['manifest_counts'].get('qrtr_tx')}/{v733['manifest_counts'].get('sysmon_qmi')}; "
                f"service_notifier={v733['manifest_counts'].get('service_notifier')}; "
                f"kernel_warning={v733['manifest_counts'].get('kernel_warning')}"
            ),
            "lower companion alone is insufficient on current V724",
        ],
        [
            "Android lower target",
            "full publication sequence exists",
            (
                f"service180/74={android['counts'].get('service_notifier_180')}/"
                f"{android['counts'].get('service_notifier_74')}; "
                f"wlan_pd={android['counts'].get('wlan_pd')}; "
                f"service180->74={android['deltas_ms'].get('service_notifier_180_to_service_notifier_74')}ms"
            ),
            "native must reach at least service 180/74 before HAL/connect",
        ],
        [
            "safe V625/V627 class",
            "CNSS-only replay can reach service 180",
            (
                f"V625 service_notifier={v625['manifest_counts'].get('service_notifier')}, "
                f"warning={v625['manifest_counts'].get('kernel_warning')}; "
                f"V627 decision={v627['decision']}"
            ),
            "next current-build live gate should replay this class with helper v121",
        ],
        [
            "post-180 blocker",
            "service 74/WLAN-PD still missing in safe positive",
            (
                f"V627 service74={v627['event_counts'].get('service_notifier_74')}; "
                f"wlan_pd={v627['event_counts'].get('wlan_pd')}; "
                f"mdm3={v627['mdm3_after_companion']}"
            ),
            "even if service 180 returns, stop before HAL and classify 74/WLAN-PD next",
        ],
        [
            "unsafe paths",
            "direct DSP/esoc/mdm-helper remain blocked",
            (
                f"V620={summary['prior']['v620']['decision']}; "
                f"V623={summary['prior']['v623']['decision']}; "
                f"V624={summary['prior']['v624']['decision']}"
            ),
            "do not use DSP boot-node, raw esoc0, mdm_helper, or qmiproxy as blind live targets",
        ],
    ]


def classify(summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    v733 = summary["v733"]
    android = summary["android_v622"]
    v625 = summary["v625"]
    v627 = summary["v627"]
    prior = summary["prior"]

    v733_safe_sysmon = (
        v733["decision"] == "v733-holder-lower-companion-sysmon-advance"
        and bool(v733["pass"])
        and int(v733["manifest_counts"].get("qrtr_rx", 0) or 0) > 0
        and int(v733["manifest_counts"].get("qrtr_tx", 0) or 0) > 0
        and int(v733["manifest_counts"].get("sysmon_qmi", 0) or 0) > 0
        and int(v733["manifest_counts"].get("kernel_warning", 0) or 0) == 0
        and int(v733["manifest_counts"].get("service_notifier", 0) or 0) == 0
    )
    android_has_target = (
        bool(android["pass"])
        and int(android["counts"].get("service_notifier_180", 0) or 0) > 0
        and int(android["counts"].get("service_notifier_74", 0) or 0) > 0
        and int(android["counts"].get("wlan_pd", 0) or 0) > 0
    )
    safe_positive_exists = (
        bool(v625["pass"])
        and bool(v627["pass"])
        and int(v625["manifest_counts"].get("service_notifier", 0) or 0) > 0
        and int(v625["manifest_counts"].get("kernel_warning", 0) or 0) == 0
        and int(v627["manifest_counts"].get("service_notifier", 0) or 0) > 0
        and int(v627["manifest_counts"].get("kernel_warning", 0) or 0) == 0
    )
    prior_blocks_blind_targets = all(
        bool(prior[key].get("pass"))
        for key in ("v620", "v623", "v624", "v626")
    )
    if v733_safe_sysmon and android_has_target and safe_positive_exists and prior_blocks_blind_targets:
        return (
            "v734-route-current-build-cnss-only-replay",
            True,
            (
                "Current V733 proves lower companion only reaches QRTR TX/sysmon without service-notifier, "
                "while older safe V625/V627 class reaches service 180 without warnings. "
                "The closest next gate is a current-build V598/V627-class CNSS-only replay with helper v121, still below HAL/connect."
            ),
            "V735 should run current-build CNSS-only post-sysmon observer: firmware mounts, subsys_modem holder, lower companions plus cnss_diag/cnss-daemon, no service-manager/HAL/scan/connect",
        )
    if v733_safe_sysmon and android_has_target:
        return (
            "v734-route-review-safe-positive-staleness",
            True,
            "Current V733 is safe but prior safe-positive evidence is incomplete or stale",
            "refresh V625/V627 evidence classification before live replay",
        )
    return (
        "v734-route-evidence-gap",
        False,
        f"v733_safe_sysmon={v733_safe_sysmon} android_has_target={android_has_target} safe_positive_exists={safe_positive_exists} prior_blocks_blind_targets={prior_blocks_blind_targets}",
        "inspect missing input evidence before selecting a live Wi-Fi gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    summary = input_summary(args)
    rows = evidence_rows(summary)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v734-current-post-sysmon-route-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V734 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v734",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v733_manifest": str(repo_path(args.v733_manifest)),
            "v733_dir": str(repo_path(args.v733_dir)),
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "android_v622_dir": str(repo_path(args.android_v622_dir)),
            "v625_manifest": str(repo_path(args.v625_manifest)),
            "v625_dir": str(repo_path(args.v625_dir)),
            "v627_manifest": str(repo_path(args.v627_manifest)),
            "v627_dir": str(repo_path(args.v627_dir)),
            "v620_manifest": str(repo_path(args.v620_manifest)),
            "v623_manifest": str(repo_path(args.v623_manifest)),
            "v624_manifest": str(repo_path(args.v624_manifest)),
            "v626_manifest": str(repo_path(args.v626_manifest)),
        },
        "summary": summary,
        "evidence_rows": rows,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    v733 = summary["v733"]
    android = summary["android_v622"]
    v625 = summary["v625"]
    v627 = summary["v627"]
    prior_rows = [[key, str(value.get("decision")), str(value.get("pass"))] for key, value in summary["prior"].items()]
    guard_rows = [
        ["device_commands_executed", str(manifest["device_commands_executed"])],
        ["sysfs_writes_executed", str(manifest["sysfs_writes_executed"])],
        ["daemon_start_executed", str(manifest["daemon_start_executed"])],
        ["service_manager_start_executed", str(manifest["service_manager_start_executed"])],
        ["wifi_hal_start_executed", str(manifest["wifi_hal_start_executed"])],
        ["scan_connect_executed", str(manifest["scan_connect_executed"])],
        ["credential_use_executed", str(manifest["credential_use_executed"])],
        ["external_ping_executed", str(manifest["external_ping_executed"])],
    ]
    return "\n".join([
        "# V734 Current Post-Sysmon Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Current V733",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["decision", str(v733["decision"])],
                ["mss", " -> ".join(str(item) for item in v733["mss"])],
                ["mdm3", " -> ".join(str(item) for item in v733["mdm3"])],
                ["helper", json.dumps(v733["helper"], sort_keys=True)],
                ["counts", json.dumps(v733["manifest_counts"], sort_keys=True)],
            ],
        ),
        "",
        "## Android V622 Target",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["decision", str(android["decision"])],
                ["mss_state", str(android["mss_state"])],
                ["mdm3_state", str(android["mdm3_state"])],
                ["counts", json.dumps({key: android["counts"].get(key) for key in ("service_notifier_180", "service_notifier_74", "wlan_pd", "qmi_server_connected", "wlan0")}, sort_keys=True)],
                ["deltas_ms", json.dumps(android["deltas_ms"], sort_keys=True)],
            ],
        ),
        "",
        "## Prior Safe Positives",
        "",
        markdown_table(
            ["cycle", "decision", "counts", "mdm3"],
            [
                ["V625", str(v625["decision"]), json.dumps(v625["manifest_counts"], sort_keys=True), str(v625["mdm3_after_companion"])],
                ["V627", str(v627["decision"]), json.dumps(v627["manifest_counts"], sort_keys=True), str(v627["mdm3_after_companion"])],
            ],
        ),
        "",
        "## Prior Classifiers",
        "",
        markdown_table(["cycle", "decision", "pass"], prior_rows),
        "",
        "## Guardrails",
        "",
        markdown_table(["guard", "value"], guard_rows),
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    latest = repo_path("tmp/wifi/latest-v734-current-post-sysmon-route.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
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
