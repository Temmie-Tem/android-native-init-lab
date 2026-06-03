#!/usr/bin/env python3
"""V1894 host-only parser for normal-Android pending-client/msg22 evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1894-android-pending-client-msg22-parser"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1894_ANDROID_PENDING_CLIENT_MSG22_PARSER_2026-06-03.md"
)
DEFAULT_ANDROID_DIR = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
)
DEFAULT_V1890_COMMANDS = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1890-android-pm-msgid-log-capture-runner"
    / "host"
    / "android-pm-msgid-log-capture-commands.json"
)
DEFAULT_V1893_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1893-pm-msg22-pending-client-gate" / "manifest.json"

DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
LOGCAT_TIME_RE = re.compile(r"^\d\d-\d\d\s+(?P<time>\d\d:\d\d:\d\d\.\d+)")
PM_MSG22_RE = re.compile(
    r"QMI service peripheral restart request|QMI service peripheral restart response|"
    r"peripheral restart request|msg(?:_| |id)?0x22|msg(?:_| |id)?22|pm_msg22",
    re.IGNORECASE,
)
PM_QMI_CLIENT_RE = re.compile(r"QMI client .* connected|QMI client .* disconnected", re.IGNORECASE)
PM_RESTART_IND_RE = re.compile(
    r"restart indication to QMI client|going on-line because restart request|QMI service peripheral restart",
    re.IGNORECASE,
)
PM_VOTE_RE = re.compile(r"cnss-daemon voting for modem", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def count_lines(lines: list[str], pattern: re.Pattern[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def first_line(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        if pattern.search(line):
            return line.strip()
    return ""


def first_logcat_time(lines: list[str], pattern: re.Pattern[str]) -> str:
    line = first_line(lines, pattern)
    match = LOGCAT_TIME_RE.search(line)
    return match.group("time") if match else ""


def first_dmesg_time(lines: list[str], pattern: re.Pattern[str]) -> float | None:
    for line in lines:
        if not pattern.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_dmesg_before(lines: list[str], pattern: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if pattern.search(line):
            count += 1
    return count


def command_text(commands: Any) -> str:
    if not isinstance(commands, list):
        return ""
    rendered: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        command = item.get("command") or []
        if isinstance(command, list):
            rendered.append(" ".join(str(part) for part in command))
        elif isinstance(command, str):
            rendered.append(command)
    return "\n".join(rendered)


def filter_summary(commands_path: Path) -> dict[str, Any]:
    text = command_text(read_json(commands_path))
    return {
        "commands_path": rel(commands_path),
        "commands_present": bool(text),
        "covers_per_mgr_srv": "PerMgrSrv" in text,
        "covers_qmi_client": "QMI client" in text,
        "covers_qmi_service": "QMI service" in text,
        "covers_peripheral_restart": "peripheral restart" in text,
        "covers_wlanmdsp": "wlanmdsp" in text,
        "covers_wlan_pd": "wlan_pd" in text,
        "covers_service_notifier": "service-notifier" in text,
        "covers_wlfw_service_request": "wlfw_service_request" in text,
    }


def android_capture_summary(android_dir: Path) -> dict[str, Any]:
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    request_lines = read_text(android_dir / "request-lines.txt").splitlines()
    all_lines = logcat_lines + dmesg_lines + request_lines
    wlan0_time = first_dmesg_time(dmesg_lines, WLAN0_RE)
    pcie_mhi_before_wlan0 = count_dmesg_before(dmesg_lines, PCIE_MHI_RE, wlan0_time)
    esoc_boot_failed_before_wlan0 = count_dmesg_before(dmesg_lines, ESOC_BOOT_FAILED_RE, wlan0_time)
    pm_msg22_count = count_lines(all_lines, PM_MSG22_RE)
    pm_qmi_client_count = count_lines(all_lines, PM_QMI_CLIENT_RE)
    pm_restart_ind_count = count_lines(all_lines, PM_RESTART_IND_RE)
    return {
        "android_dir": rel(android_dir),
        "logcat_lines": len(logcat_lines),
        "dmesg_lines": len(dmesg_lines),
        "request_lines": len(request_lines),
        "pm_vote_count": count_lines(logcat_lines, PM_VOTE_RE),
        "pm_vote_first_time": first_logcat_time(logcat_lines, PM_VOTE_RE),
        "wlfw_service_request_count": count_lines(logcat_lines + dmesg_lines, WLFW_REQUEST_RE),
        "wlfw_service_request_first_time": first_logcat_time(logcat_lines, WLFW_REQUEST_RE),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlan_pd_indication_time_s": first_dmesg_time(dmesg_lines, WLAN_PD_RE),
        "wlanmdsp_count": count_lines(logcat_lines, WLANMDSP_RE),
        "wlanmdsp_first_time": first_logcat_time(logcat_lines, WLANMDSP_RE),
        "wlan0_time_s": wlan0_time,
        "pcie_mhi_before_wlan0": pcie_mhi_before_wlan0,
        "esoc_boot_failed_before_wlan0": esoc_boot_failed_before_wlan0,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "pm_msg22_count": pm_msg22_count,
        "pm_msg22_first_line": first_line(all_lines, PM_MSG22_RE),
        "pm_qmi_client_count": pm_qmi_client_count,
        "pm_qmi_client_first_line": first_line(all_lines, PM_QMI_CLIENT_RE),
        "pm_restart_ind_count": pm_restart_ind_count,
        "pm_restart_ind_first_line": first_line(all_lines, PM_RESTART_IND_RE),
        "pending_client_msg22_observed": pm_msg22_count > 0 or pm_restart_ind_count > 0,
    }


def v1893_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    source = manifest.get("source") or {}
    native = manifest.get("native_post_open") or {}
    return {
        "manifest": rel(manifest_path),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "source_pending_client_gate": boolish((manifest.get("checks") or {}).get("source_pending_client_gate")),
        "source_msg22_request_handler": boolish((manifest.get("checks") or {}).get("source_msg22_request_handler")),
        "post_ack_sends_msg22_indication": boolish(source.get("post_ack_sends_msg22_indication")),
        "post_ack_msg22_uses_pending_client": boolish(source.get("post_ack_msg22_uses_pending_client")),
        "native_open_context_path": native.get("open_context_path", ""),
        "native_pm_client_register_rc": str(native.get("pm_client_register_rc", "")),
        "native_pm_client_connect_rc": str(native.get("pm_client_connect_rc", "")),
        "native_post_ack_open_call_hits": intish(native.get("post_ack_open_call_hits")),
        "native_post_ack_msg22_ind_hits": intish(native.get("post_ack_msg22_ind_hits")),
        "native_requested_wlanmdsp": str(native.get("requested_wlanmdsp", "")),
        "native_wlfw_service69_seen": str(native.get("wlfw_service69_seen", "")),
        "native_wlan0_present": str(native.get("wlan0_present", "")),
    }


def classify(android: dict[str, Any], v1893: dict[str, Any], capture_filter: dict[str, Any]) -> tuple[str, bool, str, str]:
    filter_ready = (
        capture_filter["commands_present"]
        and capture_filter["covers_per_mgr_srv"]
        and capture_filter["covers_qmi_client"]
        and capture_filter["covers_qmi_service"]
        and capture_filter["covers_peripheral_restart"]
        and capture_filter["covers_wlanmdsp"]
        and capture_filter["covers_wlan_pd"]
        and capture_filter["covers_wlfw_service_request"]
    )
    if not filter_ready:
        return (
            "v1894-pending-client-capture-filter-incomplete",
            False,
            "V1890 capture filter does not cover the V1893 pending-client/msg22 strings",
            "pending-client-capture-filter-incomplete",
        )
    if not v1893["pass"] or not v1893["source_pending_client_gate"]:
        return (
            "v1894-v1893-source-gate-not-ready",
            False,
            "V1893 pending-client source gate is not ready",
            "pending-client-source-gate-not-ready",
        )
    android_stateup = (
        android["pm_vote_count"] > 0
        and android["wlfw_service_request_count"] > 0
        and android["wlan_pd_indication_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["wlan0_time_s"] is not None
    )
    android_contaminated = (
        android["degraded_257s_like"]
        or android["pcie_mhi_before_wlan0"] > 0
        or android["esoc_boot_failed_before_wlan0"] > 0
    )
    native_gap = (
        v1893["native_open_context_path"] == "/dev/subsys_modem"
        and v1893["native_pm_client_register_rc"] == "0"
        and v1893["native_pm_client_connect_rc"] == "0"
        and v1893["native_post_ack_open_call_hits"] > 0
        and v1893["native_post_ack_msg22_ind_hits"] == 0
        and v1893["native_requested_wlanmdsp"] == "0"
        and v1893["native_wlfw_service69_seen"] == "0"
        and v1893["native_wlan0_present"] == "0"
    )
    if android_contaminated:
        return (
            "v1894-android-pending-client-capture-contaminated-host-pass",
            True,
            "Android capture is rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination",
            "android-pending-client-capture-contaminated",
        )
    if not android_stateup:
        return (
            "v1894-android-pending-client-capture-incomplete-host-pass",
            True,
            "Android capture lacks the normal PM vote -> wlan_pd -> wlanmdsp -> wlan0 state-up sequence",
            "android-pending-client-capture-incomplete",
        )
    if android["pending_client_msg22_observed"] and native_gap:
        return (
            "v1894-android-pending-client-msg22-native-absent-host-pass",
            True,
            "Android normal capture contains pending-client/msg22 evidence while native post-open lacks the msg22/WLFW/wlanmdsp edge",
            "android-pending-client-msg22-observed-native-absent",
        )
    if native_gap:
        return (
            "v1894-android-stateup-pending-client-observability-gap-host-pass",
            True,
            "Android normal state-up is present, but retained capture has zero pending-client/msg22 observability; native post-open still lacks msg22/WLFW/wlanmdsp",
            "android-stateup-pending-client-observability-gap",
        )
    return (
        "v1894-android-pending-client-capture-incomplete-host-pass",
        True,
        "capture did not select a stronger pending-client discriminator",
        "android-pending-client-capture-incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    source = result["v1893"]
    capture_filter = result["capture_filter"]
    return "\n".join(
        [
            "# Native Init V1894 Android Pending Client Msg22 Parser",
            "",
            "## Summary",
            "",
            "- Cycle: `V1894`",
            "- Type: host-only normal-Android pending-client/msg22 parser against native V1893 absence",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Android Parse",
            "",
            f"- Android dir: `{android['android_dir']}`",
            f"- PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0: `{android['pm_vote_count']}` / `{android['wlfw_service_request_count']}` / `{android['wlan_pd_indication_count']}` / `{android['wlanmdsp_count']}` / `{android['wlan0_time_s']}`",
            f"- contamination: PCIe-MHI `{android['pcie_mhi_before_wlan0']}` / esoc-boot-failed `{android['esoc_boot_failed_before_wlan0']}` / degraded257 `{android['degraded_257s_like']}`",
            f"- pending-client/msg22 counts: QMI-client `{android['pm_qmi_client_count']}` / msg22 `{android['pm_msg22_count']}` / restart-ind `{android['pm_restart_ind_count']}`",
            f"- first pending-client/msg22 lines: `{android['pm_qmi_client_first_line']}` / `{android['pm_msg22_first_line']}` / `{android['pm_restart_ind_first_line']}`",
            "",
            "## Source And Native Gate",
            "",
            f"- V1893 label/pass: `{source['label']}` / `{source['pass']}`",
            f"- source pending-client/msg22: `{source['source_pending_client_gate']}` / `{source['source_msg22_request_handler']}`",
            f"- native open/msg22/wlanmdsp/WLFW69/wlan0: `{source['native_post_ack_open_call_hits']}` / `{source['native_post_ack_msg22_ind_hits']}` / `{source['native_requested_wlanmdsp']}` / `{source['native_wlfw_service69_seen']}` / `{source['native_wlan0_present']}`",
            "",
            "## Capture Filter Coverage",
            "",
            f"- commands path: `{capture_filter['commands_path']}`",
            f"- PerMgrSrv/QMI-client/QMI-service/peripheral-restart: `{capture_filter['covers_per_mgr_srv']}` / `{capture_filter['covers_qmi_client']}` / `{capture_filter['covers_qmi_service']}` / `{capture_filter['covers_peripheral_restart']}`",
            f"- wlanmdsp/wlan_pd/WLFW request/service-notifier: `{capture_filter['covers_wlanmdsp']}` / `{capture_filter['covers_wlan_pd']}` / `{capture_filter['covers_wlfw_service_request']}` / `{capture_filter['covers_service_notifier']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The retained V1753 normal Android capture still proves the internal path to `wlanmdsp.mbn` and `wlan0`, but it lacks the V1893 pending-client/msg22 log edge.",
            "- The V1890 capture filter is adequate for the narrowed edge because it includes `PerMgrSrv`, `QMI client`, `QMI service`, and `peripheral restart` lines.",
            "- The next live evidence remains one normal Android ADB/root capture followed by this parser and V1888; reject degraded 257s or pre-wlan0 PCIe/MHI captures.",
            "",
            "## Safety Scope",
            "",
            "- V1894 is host-only. It parses retained/generated text and writes local artifacts only.",
            "- It performs no device command, flash, reboot, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- When normal Android ADB/root is available, run V1890 capture and then V1894/V1888 against the captured `android/` directory.",
            "- Promote only if pending-client/msg22 or another servreg/SSCTL trigger appears before the first `wlanmdsp.mbn` request.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--v1890-commands", type=Path, default=DEFAULT_V1890_COMMANDS)
    parser.add_argument("--v1893-manifest", type=Path, default=DEFAULT_V1893_MANIFEST)
    args = parser.parse_args()

    android = android_capture_summary(args.android_dir)
    capture_filter = filter_summary(args.v1890_commands)
    source = v1893_summary(args.v1893_manifest)
    decision, passed, reason, label = classify(android, source, capture_filter)
    result = {
        "cycle": "V1894",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "android": android,
        "capture_filter": capture_filter,
        "v1893": source,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "esoc_notify_boot_done": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/android-pending-client-parse.json", json.dumps(android, indent=2, sort_keys=True) + "\n")
    store.write_text("host/capture-filter-coverage.json", json.dumps(capture_filter, indent=2, sort_keys=True) + "\n")
    store.write_text("host/v1893-source-native-gate.json", json.dumps(source, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
