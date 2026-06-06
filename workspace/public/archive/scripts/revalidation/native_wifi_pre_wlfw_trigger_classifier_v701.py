#!/usr/bin/env python3
"""V701 host-only pre-WLFW trigger classifier.

This classifier consumes V700 provider-first CNSS evidence. It does not contact
the device, start daemons, mount filesystems, scan/connect, use credentials,
run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v701-pre-wlfw-trigger-classifier")
DEFAULT_V700_MANIFEST = Path("tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json")
DEFAULT_V700_DMESG = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt"
)
DEFAULT_V700_HELPER = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_V700_PROC_NET_DEV = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/proc-net-dev.txt"
)
DEFAULT_V700_RPMSG = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/rpmsg-after-companion.txt"
)
DEFAULT_V700_MSS_STATE = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/mss-state-after-companion.txt"
)
DEFAULT_V700_MDM3_STATE = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/mdm3-state-after-companion.txt"
)

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TS_RE = re.compile(r"\[\s*(?P<ts>\d+\.\d+)\]")
KEY_VALUE_RE = re.compile(r"^(?P<key>[^=\s][^=]*?)=(?P<value>.*)$")

MARKERS: dict[str, re.Pattern[str]] = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_modem": re.compile(r"sysmon-qmi: .*modem's SSCTL service", re.I),
    "service_180": re.compile(r"service-notifier: .* 180 service", re.I),
    "service_74": re.compile(r"service-notifier: .* 74 service", re.I),
    "service_ind_wlan_pd": re.compile(r"service-notifier: root_service_service_ind_cb: .*wlan_pd", re.I),
    "cnss_diag_netlink": re.compile(r"netlink_create\(694\).*comm:\s*cnss_diag", re.I),
    "cnss_daemon_netlink": re.compile(r"netlink_create\(694\).*comm:\s*cnss-daemon", re.I),
    "cnss_cld80211": re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211|ctrl_getfamily.*cld80211.*cnss-daemon", re.I),
    "cnss_binder_fail": re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I),
    "binder_ioctl_fail": re.compile(r"binder: .* ioctl .* returned -22", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "pm_qos_warning": re.compile(r"WARNING: CPU: .*pm_qos_add_request", re.I),
    "pm_qos_asoc_calltrace": re.compile(r"msm_asoc_machine_probe|deferred_probe_work_func|sm8150-asoc-snd", re.I),
    "icnss_qmi_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "icnss_runtime": re.compile(r"\bicnss\b|cnss2|QCA6390", re.I),
    "pcie_mhi_wlan": re.compile(r"\b(MHI|mhi|PCIe|pcie)\b.*\b(wlan|WLAN|QCA|qca|icnss|cnss)\b|\b(wlan|WLAN|QCA|qca|icnss|cnss)\b.*\b(MHI|mhi|PCIe|pcie)\b", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.I),
    "wlfw_service_request": re.compile(r"cnss-daemon wlfw_service_request|\bWLFW\b", re.I),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.I),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v700-manifest", type=Path, default=DEFAULT_V700_MANIFEST)
    parser.add_argument("--v700-dmesg", type=Path, default=DEFAULT_V700_DMESG)
    parser.add_argument("--v700-helper", type=Path, default=DEFAULT_V700_HELPER)
    parser.add_argument("--v700-proc-net-dev", type=Path, default=DEFAULT_V700_PROC_NET_DEV)
    parser.add_argument("--v700-rpmsg", type=Path, default=DEFAULT_V700_RPMSG)
    parser.add_argument("--v700-mss-state", type=Path, default=DEFAULT_V700_MSS_STATE)
    parser.add_argument("--v700-mdm3-state", type=Path, default=DEFAULT_V700_MDM3_STATE)
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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def strip_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_ts(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        match = KEY_VALUE_RE.match(line)
        if match:
            values.setdefault(match.group("key"), []).append(match.group("value"))
    return values


def first_value(values: dict[str, list[str]], key: str) -> str:
    rows = values.get(key) or []
    return rows[0] if rows else ""


def parse_timeline(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in MARKERS}
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        if not line:
            continue
        timestamp = line_ts(line)
        for name, pattern in MARKERS.items():
            if pattern.search(line):
                events[name].append({"ts": timestamp, "line": line[:260]})
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "sample_lines": {name: [row["line"] for row in rows[:4]] for name, rows in events.items() if rows},
    }


def delta(first_ts: dict[str, float], start: str, end: str) -> float | None:
    if start not in first_ts or end not in first_ts:
        return None
    return round((first_ts[end] - first_ts[start]) * 1000.0, 3)


def deltas_for(timeline: dict[str, Any]) -> dict[str, float | None]:
    first_ts = timeline.get("first_ts") or {}
    return {
        "service74_to_pm_qos_warning_ms": delta(first_ts, "service_74", "pm_qos_warning"),
        "service74_to_cnss_diag_netlink_ms": delta(first_ts, "service_74", "cnss_diag_netlink"),
        "service74_to_cnss_daemon_netlink_ms": delta(first_ts, "service_74", "cnss_daemon_netlink"),
        "cnss_daemon_netlink_to_wlfw_start_ms": delta(first_ts, "cnss_daemon_netlink", "wlfw_start"),
        "cnss_daemon_netlink_to_icnss_qmi_ms": delta(first_ts, "cnss_daemon_netlink", "icnss_qmi_connected"),
        "cnss_daemon_netlink_to_bdf_bdwlan_ms": delta(first_ts, "cnss_daemon_netlink", "bdf_bdwlan"),
        "cnss_daemon_netlink_to_wlan0_ms": delta(first_ts, "cnss_daemon_netlink", "wlan0"),
    }


def arm_v700(manifest: dict[str, Any]) -> dict[str, Any]:
    arm = manifest.get("arm_v700")
    return arm if isinstance(arm, dict) else {}


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    v700_manifest = load_json(args.v700_manifest)
    dmesg_text = read_text(args.v700_dmesg)
    helper_text = read_text(args.v700_helper)
    key_values = parse_key_values(helper_text)
    timeline = parse_timeline(dmesg_text)
    arm = arm_v700(v700_manifest)
    counts = arm.get("counts") or {}
    markers = arm.get("markers") or {}
    peripheral = arm.get("peripheral") or {}
    query = arm.get("vndservice_query") or {}
    return {
        "v700": {
            "decision": v700_manifest.get("decision", ""),
            "pass": boolish(v700_manifest.get("pass")),
            "counts": counts,
            "markers": markers,
            "initial_cnss_suppressed": boolish(arm.get("initial_cnss_suppressed")),
            "query_exact_match": boolish(arm.get("query_exact_match")),
            "cnss_retry_started": boolish(arm.get("cnss_retry_started")),
            "peripheral": peripheral,
            "vndservice_query": query,
            "reboot_cleanup": arm.get("reboot_cleanup") or {},
        },
        "helper": {
            "order": first_value(key_values, "wifi_companion_start.order"),
            "initial_suppressed": first_value(key_values, "wifi_companion_start.initial_cnss_daemon.suppressed"),
            "cnss_retry_start_order": first_value(key_values, "wifi_companion_start.child.cnss_daemon_retry.start_order"),
            "cnss_retry_pid": first_value(key_values, "wifi_companion_start.child.cnss_daemon_retry.pid"),
            "cnss_retry_signal": first_value(key_values, "wifi_companion_start.child.cnss_daemon_retry.signal"),
            "scan_connect_linkup": first_value(key_values, "wifi_companion_start.scan_connect_linkup"),
            "external_ping": first_value(key_values, "wifi_companion_start.external_ping"),
        },
        "timeline": timeline,
        "deltas_ms": deltas_for(timeline),
        "state": {
            "mss": read_text(args.v700_mss_state).strip(),
            "mdm3": read_text(args.v700_mdm3_state).strip(),
            "rpmsg_has_modem_ipcrtr": "qcom,glink:modem.IPCRTR" in read_text(args.v700_rpmsg),
            "proc_net_dev_has_wlan0": "wlan0:" in read_text(args.v700_proc_net_dev),
        },
    }


def timeline_count(surface: dict[str, Any], marker: str) -> int:
    return intish(((surface.get("timeline") or {}).get("counts") or {}).get(marker))


def count(surface: dict[str, Any], marker: str) -> int:
    return intish(((surface.get("v700") or {}).get("counts") or {}).get(marker))


def marker_count(surface: dict[str, Any], marker: str) -> int:
    return intish(((surface.get("v700") or {}).get("markers") or {}).get(marker))


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    v700 = surface["v700"]
    timeline = surface["timeline"]
    helper = surface["helper"]
    state = surface["state"]
    return [
        {
            "name": "input-v700-provider-first-gate-ready",
            "status": "pass" if (
                v700["pass"]
                and v700["initial_cnss_suppressed"]
                and v700["query_exact_match"]
                and v700["cnss_retry_started"]
                and count(surface, "service_notifier_180") > 0
                and count(surface, "service_notifier_74") > 0
            ) else "blocked",
            "detail": {
                "decision": v700["decision"],
                "initial_cnss_suppressed": v700["initial_cnss_suppressed"],
                "query_exact_match": v700["query_exact_match"],
                "cnss_retry_started": v700["cnss_retry_started"],
                "service_notifier_180": count(surface, "service_notifier_180"),
                "service_notifier_74": count(surface, "service_notifier_74"),
            },
            "next_step": "refresh V700 provider-first evidence before classifying pre-WLFW gap",
        },
        {
            "name": "cnss-binder-failure-removed",
            "status": "finding" if (
                count(surface, "cnss_binder_transaction_failed") == 0
                and timeline_count(surface, "cnss_binder_fail") == 0
                and count(surface, "binder_transaction_failed") == 0
            ) else "review",
            "detail": {
                "cnss_binder_transaction_failed": count(surface, "cnss_binder_transaction_failed"),
                "cnss_binder_fail_timeline": timeline_count(surface, "cnss_binder_fail"),
                "binder_transaction_failed": count(surface, "binder_transaction_failed"),
            },
            "next_step": "do not route next work to old CNSS Binder -22 unless it reappears",
        },
        {
            "name": "cnss-userspace-reaches-cld80211-only",
            "status": "finding" if (
                count(surface, "cnss_daemon_netlink") > 0
                and count(surface, "cnss_daemon_cld80211") > 0
                and count(surface, "wlfw_start") == 0
                and count(surface, "bdf_bdwlan") == 0
                and count(surface, "wlan0") == 0
            ) else "review",
            "detail": {
                "cnss_daemon_netlink": count(surface, "cnss_daemon_netlink"),
                "cnss_daemon_cld80211": count(surface, "cnss_daemon_cld80211"),
                "wlfw_start": count(surface, "wlfw_start"),
                "bdf_bdwlan": count(surface, "bdf_bdwlan"),
                "wlan0": count(surface, "wlan0"),
                "deltas_ms": surface["deltas_ms"],
            },
            "next_step": "observe kernel-side cnss2/icnss/QCA trigger after retry rather than repeating userspace Binder repair",
        },
        {
            "name": "kernel-wifi-progression-absent",
            "status": "finding" if (
                timeline_count(surface, "icnss_qmi_connected") == 0
                and timeline_count(surface, "pcie_mhi_wlan") == 0
                and marker_count(surface, "wlfw") == 0
                and marker_count(surface, "bdf") == 0
                and marker_count(surface, "wlan0") == 0
            ) else "review",
            "detail": {
                "icnss_qmi_connected": timeline_count(surface, "icnss_qmi_connected"),
                "pcie_mhi_wlan": timeline_count(surface, "pcie_mhi_wlan"),
                "wlfw_marker": marker_count(surface, "wlfw"),
                "bdf_marker": marker_count(surface, "bdf"),
                "wlan0_marker": marker_count(surface, "wlan0"),
            },
            "next_step": "capture cnss2/icnss platform sysfs and dmesg markers in the same retry window",
        },
        {
            "name": "pm-qos-warning-attributed-to-audio-deferred-probe",
            "status": "finding" if (
                timeline_count(surface, "pm_qos_warning") > 0
                and timeline_count(surface, "pm_qos_asoc_calltrace") > 0
            ) else "review",
            "detail": {
                "pm_qos_warning_count": timeline_count(surface, "pm_qos_warning"),
                "pm_qos_asoc_calltrace_count": timeline_count(surface, "pm_qos_asoc_calltrace"),
                "first_warning": (timeline.get("first_lines") or {}).get("pm_qos_warning", ""),
                "first_asoc": (timeline.get("first_lines") or {}).get("pm_qos_asoc_calltrace", ""),
                "deltas_ms": surface["deltas_ms"],
            },
            "next_step": "track pm_qos as secondary noise unless a cnss2/WLAN call trace appears",
        },
        {
            "name": "lower-modem-transport-ready-but-mdm3-offlining",
            "status": "finding" if (
                state["mss"] == "ONLINE"
                and state["rpmsg_has_modem_ipcrtr"]
                and state["mdm3"] == "OFFLINING"
            ) else "review",
            "detail": state,
            "next_step": "treat MPSS transport as sufficient for service 180/74, but inspect mdm3/esoc side effects separately from WLAN WLFW",
        },
        {
            "name": "wifi-bringup-still-not-safe",
            "status": "pass" if (
                helper["scan_connect_linkup"] == "0"
                and helper["external_ping"] == "0"
                and not state["proc_net_dev_has_wlan0"]
            ) else "blocked",
            "detail": {
                "scan_connect_linkup": helper["scan_connect_linkup"],
                "external_ping": helper["external_ping"],
                "proc_net_dev_has_wlan0": state["proc_net_dev_has_wlan0"],
            },
            "next_step": "keep Wi-Fi HAL, scan/connect, DHCP, credentials, and external ping blocked until WLFW/BDF/wlan0 advances",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v701-pre-wlfw-trigger-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V701 host-only classifier over V700 evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v701-pre-wlfw-trigger-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh V700 evidence before planning another live unit",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "cnss-binder-failure-removed",
        "cnss-userspace-reaches-cld80211-only",
        "kernel-wifi-progression-absent",
        "pm-qos-warning-attributed-to-audio-deferred-probe",
        "lower-modem-transport-ready-but-mdm3-offlining",
    }
    if required <= findings:
        return (
            "v701-pre-wlfw-kernel-progression-gap-classified",
            True,
            "V700 removed the initial CNSS Binder confounder and reached provider-confirmed CNSS retry, but only cld80211/netlink moved; no ICNSS/QCA/WLFW/BDF/wlan0 marker followed. The pm_qos warning is audio deferred-probe attributed, not the primary Wi-Fi blocker.",
            "plan V702 as bounded read-only cnss2/icnss/QCA platform-state capture in the provider-first retry window; keep Wi-Fi HAL, scan/connect, DHCP, credentials, and external ping blocked",
        )
    if "cnss-binder-failure-removed" in findings and "cnss-userspace-reaches-cld80211-only" in findings:
        return (
            "v701-pre-wlfw-gap-needs-kernel-observability",
            True,
            "V700 no longer shows the old Binder failure and still stalls before WLFW, but secondary kernel attribution is incomplete",
            "add cnss2/icnss sysfs and dmesg observability before another functional Wi-Fi attempt",
        )
    return (
        "v701-pre-wlfw-trigger-manual-review",
        False,
        "evidence did not match a known pre-WLFW trigger pattern",
        "inspect V700 manifest, helper transcript, and dmesg manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    surface = build_surface(args)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v701",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v700_manifest": str(repo_path(args.v700_manifest)),
            "v700_dmesg": str(repo_path(args.v700_dmesg)),
            "v700_helper": str(repo_path(args.v700_helper)),
            "v700_proc_net_dev": str(repo_path(args.v700_proc_net_dev)),
            "v700_rpmsg": str(repo_path(args.v700_rpmsg)),
            "v700_mss_state": str(repo_path(args.v700_mss_state)),
            "v700_mdm3_state": str(repo_path(args.v700_mdm3_state)),
        },
        "surface": surface,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["surface"]
    timeline = surface["timeline"]
    rows: list[list[str]] = []
    for marker in (
        "service_180",
        "service_74",
        "cnss_diag_netlink",
        "cnss_daemon_netlink",
        "cnss_cld80211",
        "cnss_binder_fail",
        "pm_qos_warning",
        "pm_qos_asoc_calltrace",
        "icnss_qmi_connected",
        "pcie_mhi_wlan",
        "wlfw_start",
        "wlfw_service_request",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ):
        rows.append([
            marker,
            str((timeline.get("counts") or {}).get(marker, 0)),
            str((timeline.get("first_ts") or {}).get(marker, "")),
            (timeline.get("first_lines") or {}).get(marker, ""),
        ])
    count_rows = [
        [key, str(value)]
        for key, value in sorted((surface["v700"].get("counts") or {}).items())
        if key in {
            "service_notifier_180",
            "service_notifier_74",
            "cnss_daemon_netlink",
            "cnss_daemon_cld80211",
            "cnss_binder_transaction_failed",
            "binder_transaction_failed",
            "kernel_warning",
            "qmi_server_connected",
            "wlfw_start",
            "bdf_bdwlan",
            "wlan_fw_ready",
            "wlan0",
        }
    ]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    delta_rows = [[key, "" if value is None else str(value)] for key, value in sorted(surface["deltas_ms"].items())]
    state_rows = [[key, str(value)] for key, value in sorted(surface["state"].items())]
    return "\n".join([
        "# V701 Pre-WLFW Trigger Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## V700 Counts",
        "",
        markdown_table(["count", "value"], count_rows),
        "",
        "## Timeline",
        "",
        markdown_table(["marker", "count", "first_ts", "first_line"], rows),
        "",
        "## Deltas",
        "",
        markdown_table(["delta", "ms"], delta_rows),
        "",
        "## State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
