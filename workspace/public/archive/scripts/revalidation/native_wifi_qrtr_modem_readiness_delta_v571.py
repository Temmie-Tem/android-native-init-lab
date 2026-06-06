#!/usr/bin/env python3
"""V571 read-only QRTR/modem readiness delta classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v571-qrtr-modem-readiness-delta")
DEFAULT_V519_MANIFEST = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_V570_MANIFEST = Path("tmp/wifi/v570-companion-dual-hal-wificond-rmt-tftp-identity/manifest.json")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
TOYBOX = "/cache/bin/toybox"

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 15.0),
    ("selftest", ["selftest"], 15.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,ppid,stat,comm,args"], 15.0),
    ("proc-net-protocols", ["cat", "/proc/net/protocols"], 10.0),
    ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
    ("proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("proc-cmdline", ["cat", "/proc/cmdline"], 10.0),
    ("stat-dev-qrtr", ["stat", "/dev/qrtr"], 10.0),
    ("stat-dev-wlan", ["stat", "/dev/wlan"], 10.0),
    ("stat-debugfs-service-notifier", ["stat", "/sys/kernel/debug/service_notifier"], 10.0),
    ("ls-debugfs-service-notifier", ["run", TOYBOX, "ls", "-la", "/sys/kernel/debug/service_notifier"], 10.0),
    ("ls-sys-class-remoteproc", ["run", TOYBOX, "ls", "-la", "/sys/class/remoteproc"], 10.0),
    ("find-remoteproc", ["run", TOYBOX, "find", "/sys/class/remoteproc", "-maxdepth", "3"], 20.0),
    ("ls-msm-subsys", ["run", TOYBOX, "ls", "-la", "/sys/bus/msm_subsys/devices"], 10.0),
    ("ls-rpmsg", ["run", TOYBOX, "ls", "-la", "/sys/bus/rpmsg/devices"], 10.0),
    ("find-sys-qcom-modules", ["run", TOYBOX, "find", "/sys/module", "-maxdepth", "1", "-name", "*qcom*"], 15.0),
    ("find-sys-qrtr-modules", ["run", TOYBOX, "find", "/sys/module", "-maxdepth", "1", "-name", "*qrtr*"], 15.0),
    ("find-sys-cnss-modules", ["run", TOYBOX, "find", "/sys/module", "-maxdepth", "1", "-name", "*cnss*"], 15.0),
    ("find-sys-icnss-modules", ["run", TOYBOX, "find", "/sys/module", "-maxdepth", "1", "-name", "*icnss*"], 15.0),
    ("dmesg", ["run", TOYBOX, "dmesg"], 20.0),
)

PROCESS_RE = re.compile(
    r"\b(qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss_diag|cnss-daemon|"
    r"service-notifier|sysmon-qmi|qmiproxy|ssgqmigd|wificond|wpa_supplicant|"
    r"hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+|mlan\d*)\b", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

DMESG_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_modem_readiness_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE)),
    ("qrtr_modem_readiness_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE)),
    ("sysmon_qmi_ready", re.compile(r"sysmon-qmi: ssctl_new_server: Connection established", re.IGNORECASE)),
    ("service_notifier_ready", re.compile(r"service-notifier: service_notifier_new_server: Connection established", re.IGNORECASE)),
    ("wlan_pd_indication", re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.IGNORECASE)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE)),
    ("cnss_daemon_wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE)),
    ("wlfw_thread", re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE)),
    ("wlan_fw_ready", re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE)),
    ("wlan0_event", re.compile(r"dev\s*:\s*wlan0\s*:\s*event|\bwlan0\b", re.IGNORECASE)),
)

SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c",
    "https://codebrowser.dev/linux/linux/net/qrtr/",
    "https://cateee.net/lkddb/web-lkddb/QCOM_SYSMON.html",
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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519_MANIFEST)
    parser.add_argument("--v570-manifest", type=Path, default=DEFAULT_V570_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def run_read_only_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    store.mkdir("native")
    for name, command, timeout in READ_ONLY_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        item = capture_to_manifest(capture)
        item["file"] = rel
        item["payload"] = text
        records.append(item)
    return records


def step_map(steps: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("name")): item for item in steps}


def payload(steps: dict[str, dict[str, Any]], name: str) -> str:
    return str(steps.get(name, {}).get("payload") or "")


def step_ok(steps: dict[str, dict[str, Any]], name: str) -> bool:
    item = steps.get(name) or {}
    return item.get("rc") == 0 and item.get("status") == "ok"


def count_qipcrtr_sockets(protocols: str) -> int:
    for line in protocols.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "QIPCRTR":
            try:
                return int(parts[2], 0)
            except ValueError:
                return -1
    return -1


def dmesg_counts(text: str) -> dict[str, int]:
    counts = {name: 0 for name, _pattern in DMESG_MARKERS}
    for line in strip_ansi(text).splitlines():
        for name, pattern in DMESG_MARKERS:
            if pattern.search(line):
                counts[name] += 1
    return counts


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dmesg_focus(text: str, limit: int = 160) -> list[str]:
    focus = []
    pattern = re.compile(
        r"qrtr|qmi|sysmon|service-notifier|servreg|wlan_pd|cnss|icnss|wlfw|bdf|bdwlan|regdb|wlan0|remoteproc|subsys|modem",
        re.IGNORECASE,
    )
    for line in strip_ansi(text).splitlines():
        stripped = line.strip()
        if stripped and pattern.search(stripped):
            focus.append(stripped)
    return focus[-limit:]


def android_marker_count(v519: dict[str, Any], name: str) -> int:
    summary = v519.get("android_summary") if isinstance(v519.get("android_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    value = counts.get(name)
    return value if isinstance(value, int) else 0


def v570_live_summary(v570: dict[str, Any]) -> dict[str, Any]:
    live = v570.get("live_result") if isinstance(v570.get("live_result"), dict) else {}
    dmesg = v570.get("dmesg_summary") if isinstance(v570.get("dmesg_summary"), dict) else {}
    return {
        "exists": bool(v570.get("exists")) and not v570.get("invalid"),
        "decision": v570.get("decision"),
        "pass": v570.get("pass"),
        "reason": v570.get("reason"),
        "iwifi_status": f"{live.get('iwifi_start_wifi_status_name', '')}/{live.get('iwifi_start_wifi_status_code', '')}",
        "qipcrtr_sockets_before": live.get("qipcrtr_sockets_before"),
        "qipcrtr_sockets_after_spawn": live.get("qipcrtr_sockets_after_spawn"),
        "qipcrtr_sockets_window": live.get("qipcrtr_sockets_window"),
        "qipcrtr_sockets_after_cleanup": live.get("qipcrtr_sockets_after_cleanup"),
        "qrtr_readback_service_events": live.get("qrtr_readback_service_events"),
        "qrtr_readback_qmi_attempted": live.get("qrtr_readback_qmi_attempted"),
        "identity_contracts_ok": live.get("rmt_tftp_identity_contracts_ok"),
        "all_postflight_safe": live.get("all_postflight_safe"),
        "readiness_markers": dmesg.get("readiness_markers") or [],
    }


def current_surface(steps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    protocols = payload(steps, "proc-net-protocols")
    ps = payload(steps, "ps")
    netdev = payload(steps, "proc-net-dev")
    dmesg = payload(steps, "dmesg")
    return {
        "qipcrtr_protocol_present": "QIPCRTR" in protocols,
        "qipcrtr_sockets": count_qipcrtr_sockets(protocols),
        "proc_net_qrtr_present": step_ok(steps, "proc-net-qrtr"),
        "dev_qrtr_present": step_ok(steps, "stat-dev-qrtr"),
        "dev_wlan_present": step_ok(steps, "stat-dev-wlan"),
        "debugfs_service_notifier_present": step_ok(steps, "stat-debugfs-service-notifier"),
        "remoteproc_present": step_ok(steps, "ls-sys-class-remoteproc"),
        "msm_subsys_present": step_ok(steps, "ls-msm-subsys"),
        "rpmsg_present": step_ok(steps, "ls-rpmsg"),
        "process_hits": [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)],
        "wifi_hits": [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)],
        "dmesg_counts": dmesg_counts(dmesg),
        "dmesg_focus_tail": dmesg_focus(dmesg),
        "remoteproc_lines": [line.strip() for line in payload(steps, "find-remoteproc").splitlines() if line.strip()][:120],
        "msm_subsys_lines": [line.strip() for line in payload(steps, "ls-msm-subsys").splitlines() if line.strip()][:80],
        "rpmsg_lines": [line.strip() for line in payload(steps, "ls-rpmsg").splitlines() if line.strip()][:80],
        "qcom_module_lines": [line.strip() for line in (
            payload(steps, "find-sys-qcom-modules") +
            payload(steps, "find-sys-qrtr-modules") +
            payload(steps, "find-sys-cnss-modules") +
            payload(steps, "find-sys-icnss-modules")
        ).splitlines() if line.strip()][:120],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 steps: dict[str, dict[str, Any]],
                 surface: dict[str, Any],
                 v519: dict[str, Any],
                 v570_summary: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    version = payload(steps, "version")
    status = payload(steps, "status")
    selftest = payload(steps, "selftest")
    android_required = {
        "qrtr_modem_readiness_rx": android_marker_count(v519, "qrtr_modem_readiness_rx"),
        "qrtr_modem_readiness_tx": android_marker_count(v519, "qrtr_modem_readiness_tx"),
        "sysmon_qmi_ready": android_marker_count(v519, "sysmon_qmi_ready"),
        "service_notifier_ready": android_marker_count(v519, "service_notifier_ready"),
        "wlan_pd_indication": android_marker_count(v519, "wlan_pd_indication"),
        "qmi_server_connected": android_marker_count(v519, "qmi_server_connected"),
    }
    add_check(
        checks,
        "native-clean",
        "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:2],
        "restore native baseline before readiness delta",
    )
    add_check(
        checks,
        "v519-android-reference",
        "pass" if v519.get("decision") == "v519-qrtr-companion-service-gap-classified" and all(value > 0 for value in android_required.values()) else "blocked",
        "blocker",
        " ".join(f"{key}={value}" for key, value in android_required.items()),
        [str(args.v519_manifest)],
        "refresh Android QRTR/modem sequence evidence",
    )
    add_check(
        checks,
        "v570-current-baseline",
        "pass" if v570_summary["decision"] == "v570-rmt-tftp-identity-not-sufficient" and v570_summary["pass"] is True else "blocked",
        "blocker",
        f"decision={v570_summary['decision']} pass={v570_summary['pass']} identity={v570_summary['identity_contracts_ok']}",
        [str(args.v570_manifest)],
        "rerun V570 after helper v94 deploy",
    )
    add_check(
        checks,
        "no-active-target-processes",
        "pass" if not surface["process_hits"] else "blocked",
        "blocker",
        f"process_hits={len(surface['process_hits'])}",
        surface["process_hits"][:8],
        "cleanup residual Wi-Fi/companion process before further live action",
    )
    add_check(
        checks,
        "no-wifi-link-surface",
        "pass" if not surface["wifi_hits"] else "blocked",
        "blocker",
        f"wifi_hits={len(surface['wifi_hits'])}",
        surface["wifi_hits"][:8],
        "if wlan0/wiphy exists, move to scan-only gate instead",
    )
    add_check(
        checks,
        "native-qrtr-kernel-surface",
        "pass" if surface["qipcrtr_protocol_present"] else "blocked",
        "blocker",
        f"protocol={surface['qipcrtr_protocol_present']} sockets={surface['qipcrtr_sockets']} proc_net_qrtr={surface['proc_net_qrtr_present']} dev_qrtr={surface['dev_qrtr_present']}",
        [],
        "restore QRTR kernel surface before companion replay",
    )
    add_check(
        checks,
        "native-modem-readiness-markers",
        "warn" if surface["dmesg_counts"].get("qrtr_modem_readiness_rx", 0) == 0 else "pass",
        "warning",
        f"counts={surface['dmesg_counts']}",
        surface["dmesg_focus_tail"][-12:],
        "do not retry scan/connect until modem/QMI readiness markers appear",
    )
    add_check(
        checks,
        "service-notifier-surface",
        "warn" if not surface["debugfs_service_notifier_present"] else "pass",
        "warning",
        f"debugfs_service_notifier={surface['debugfs_service_notifier_present']} android_service_notifier={android_required['service_notifier_ready']}",
        [],
        "classify whether service-notifier is kernel-only, debugfs-hidden, or timing-gated",
    )
    add_check(
        checks,
        "remoteproc-rpmsg-surface",
        "pass" if surface["remoteproc_present"] or surface["msm_subsys_present"] or surface["rpmsg_present"] else "warn",
        "warning",
        f"remoteproc={surface['remoteproc_present']} msm_subsys={surface['msm_subsys_present']} rpmsg={surface['rpmsg_present']}",
        surface["remoteproc_lines"][:6] + surface["msm_subsys_lines"][:6] + surface["rpmsg_lines"][:6],
        "compare modem/subsystem state to Android if QRTR readiness remains absent",
    )
    return checks


def classify(checks: list[Check],
             surface: dict[str, Any],
             v570_summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v571-qrtr-modem-readiness-blocked", False, "blocked by " + ", ".join(blockers), "resolve blockers before further live proof"
    counts = surface["dmesg_counts"]
    if counts.get("qmi_server_connected", 0) > 0 or counts.get("wlan_fw_ready", 0) > 0:
        return (
            "v571-qrtr-modem-readiness-advanced",
            True,
            "native dmesg now contains QMI/FW readiness markers",
            "rerun bounded IWifi.start and prepare scan-only gate if wlan surface appears",
        )
    if surface["qipcrtr_sockets"] == 0 and str(v570_summary["qipcrtr_sockets_window"]) == "0":
        return (
            "v571-modem-readiness-not-entered",
            True,
            "Android reference has QRTR/service-notifier/WLAN-PD/QMI markers, but current native and V570 both have QIPCRTR sockets=0 and no readiness markers",
            "focus next on modem QRTR readiness timing or missing service-notifier/sysmon trigger before another HAL start retry",
        )
    if counts.get("qrtr_modem_readiness_rx", 0) > 0 and counts.get("qmi_server_connected", 0) == 0:
        return (
            "v571-modem-readiness-no-cnss-qmi",
            True,
            "native sees modem QRTR readiness but CNSS QMI still does not connect",
            "inspect service-notifier/sysmon and CNSS ordering before IWifi.start retry",
        )
    return (
        "v571-qrtr-modem-readiness-review-required",
        False,
        f"unclassified QRTR surface sockets={surface['qipcrtr_sockets']} counts={counts}",
        "inspect V571 evidence before further live action",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    surface = manifest["current_surface"]
    surface_rows = [
        ["qipcrtr_protocol_present", surface["qipcrtr_protocol_present"]],
        ["qipcrtr_sockets", surface["qipcrtr_sockets"]],
        ["proc_net_qrtr_present", surface["proc_net_qrtr_present"]],
        ["dev_qrtr_present", surface["dev_qrtr_present"]],
        ["debugfs_service_notifier_present", surface["debugfs_service_notifier_present"]],
        ["remoteproc_present", surface["remoteproc_present"]],
        ["msm_subsys_present", surface["msm_subsys_present"]],
        ["rpmsg_present", surface["rpmsg_present"]],
        ["process_hits", len(surface["process_hits"])],
        ["wifi_hits", len(surface["wifi_hits"])],
    ]
    marker_rows = [[name, count] for name, count in surface["dmesg_counts"].items()]
    v570 = manifest["v570_summary"]
    return "\n".join([
        "# V571 QRTR/Modem Readiness Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- evidence: `{manifest['out_dir']}`",
        "- device_mutations: `False`",
        "- daemon_start_executed: `False`",
        "- wifi_bringup_executed: `False`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## V570 Baseline",
        "",
        f"- decision: `{v570['decision']}`",
        f"- iwifi_status: `{v570['iwifi_status']}`",
        f"- qipcrtr_sockets_window: `{v570['qipcrtr_sockets_window']}`",
        f"- qrtr_readback_service_events: `{v570['qrtr_readback_service_events']}`",
        f"- identity_contracts_ok: `{v570['identity_contracts_ok']}`",
        f"- all_postflight_safe: `{v570['all_postflight_safe']}`",
        "",
        "## Current Native Surface",
        "",
        markdown_table(["key", "value"], surface_rows),
        "",
        "## Current Dmesg Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Current Dmesg Focus Tail",
        "",
        "```text",
        "\n".join(surface["dmesg_focus_tail"][-80:]) if surface["dmesg_focus_tail"] else "<empty>",
        "```",
        "",
        "## References",
        "",
        *[f"- {url}" for url in SOURCE_REFERENCES],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v519 = load_json(args.v519_manifest)
    v570 = load_json(args.v570_manifest)
    v570_summary = v570_live_summary(v570)
    if args.command == "plan":
        checks = [Check("plan-only", "pass", "info", "no device command executed", [], "run V571 read-only classifier")]
        surface = {
            "qipcrtr_protocol_present": False,
            "qipcrtr_sockets": -1,
            "proc_net_qrtr_present": False,
            "dev_qrtr_present": False,
            "dev_wlan_present": False,
            "debugfs_service_notifier_present": False,
            "remoteproc_present": False,
            "msm_subsys_present": False,
            "rpmsg_present": False,
            "process_hits": [],
            "wifi_hits": [],
            "dmesg_counts": {name: 0 for name, _pattern in DMESG_MARKERS},
            "dmesg_focus_tail": [],
            "remoteproc_lines": [],
            "msm_subsys_lines": [],
            "rpmsg_lines": [],
            "qcom_module_lines": [],
        }
        decision, pass_ok, reason, next_step = (
            "v571-qrtr-modem-readiness-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V571 read-only QRTR/modem readiness delta",
        )
        steps: list[dict[str, Any]] = []
    else:
        steps = run_read_only_commands(args, store)
        mapped = step_map(steps)
        surface = current_surface(mapped)
        checks = build_checks(args, mapped, surface, v519, v570_summary)
        decision, pass_ok, reason, next_step = classify(checks, surface, v570_summary)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "v519_manifest": str(repo_path(args.v519_manifest)),
        "v570_manifest": str(repo_path(args.v570_manifest)),
        "v570_summary": v570_summary,
        "current_surface": surface,
        "source_references": SOURCE_REFERENCES,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_executed": [
            "daemon/service start",
            "Wi-Fi HAL start",
            "QMI payload",
            "supplicant/hostapd",
            "scan/connect/link-up",
            "credential use, DHCP, route change, external ping",
            "boot image flash, reboot, Android partition write",
        ],
    }


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
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
