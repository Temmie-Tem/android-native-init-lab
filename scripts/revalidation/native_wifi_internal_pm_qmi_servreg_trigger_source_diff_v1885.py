#!/usr/bin/env python3
"""V1885 host-only source/trace-gap diff for the internal WLAN guest-PD trigger."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1885_INTERNAL_PM_QMI_SERVREG_TRIGGER_SOURCE_DIFF_2026-06-03.md"
)
DEFAULT_PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
DEFAULT_LIBPERIPHERAL = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1073-host-only"
    / "vendor-extract"
    / "files"
    / "libperipheral_client.so"
)
DEFAULT_ANDROID_DIR = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
)
DEFAULT_V1755_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1755-wlan-pd-pm-vote-contract-classifier" / "manifest.json"
DEFAULT_V1802_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1802-post-pm-success-wlfw-classifier" / "manifest.json"
DEFAULT_V1803_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1803-wlfw-qmi-readiness-classifier" / "manifest.json"
DEFAULT_V1847_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1847-pm-service-open-context-handoff" / "manifest.json"
DEFAULT_V1884_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1884-internal-post-vote-trigger-diff-gate" / "manifest.json"


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
LOGCAT_TIME_RE = re.compile(r"^\d\d-\d\d\s+(?P<time>\d\d:\d\d:\d\d\.\d+)")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def command_text(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def first_line(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def count_lines(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in lines if regex.search(line))


def first_logcat_time(lines: list[str], pattern: str) -> str:
    line = first_line(lines, pattern)
    match = LOGCAT_TIME_RE.search(line)
    return match.group("time") if match else ""


def first_dmesg_time(lines: list[str], pattern: str) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_dmesg_before(lines: list[str], pattern: str, before_time: float | None) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def event_hit_count(details: dict[str, Any], name: str) -> int:
    event = details.get(name) or {}
    if not isinstance(event, dict):
        return 0
    return intish(event.get("hit_count"))


def artifact_text(store: EvidenceStore, name: str, command: list[str]) -> str:
    text = command_text(command)
    store.write_text(f"host/{name}", text)
    return text


def source_summary(store: EvidenceStore, pm_service: Path, libperipheral: Path) -> dict[str, Any]:
    artifacts: dict[str, str] = {}
    disassembly_specs = {
        "pm-service-qmi-msgid-dispatch-0x6ebc-0x7380.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            "--start-address=0x6ebc",
            "--stop-address=0x7380",
            str(pm_service),
        ],
        "pm-service-qmi-loop-0x73b0-0x761c.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            "--start-address=0x73b0",
            "--stop-address=0x761c",
            str(pm_service),
        ],
        "pm-service-post-ack-msg22-ind-0x8950-0x8a80.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            "--start-address=0x8950",
            "--stop-address=0x8a80",
            str(pm_service),
        ],
        "pm-service-peripheral-restart-handler-0x716c-0x72e0.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            "--start-address=0x716c",
            "--stop-address=0x72e0",
            str(pm_service),
        ],
        "libperipheral-pm-register-connect-0x612c-0x6700.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            "--start-address=0x612c",
            "--stop-address=0x6700",
            str(libperipheral),
        ],
    }
    disassembly_texts: dict[str, str] = {}
    for name, command in disassembly_specs.items():
        disassembly_texts[name] = artifact_text(store, name, command)
        artifacts[name] = f"host/{name}"

    pm_strings = command_text(["strings", "-a", "-tx", str(pm_service)])
    pm_filtered = "\n".join(
        line
        for line in pm_strings.splitlines()
        if re.search(
            r"QMI service|peripheral restart|system restart|system shutdown|vendor\.peripheral|"
            r"going on-line|going off-line|subsys|modem|WCNSS|MPSS|SDX50M|service",
            line,
            re.IGNORECASE,
        )
    )
    lib_strings = command_text(["strings", "-a", "-tx", str(libperipheral)])
    lib_filtered = "\n".join(
        line
        for line in lib_strings.splitlines()
        if re.search(r"pm_client|pm_register|PeripheralManager|vndbinder|binder|modem|service", line, re.IGNORECASE)
    )
    pm_symbols = command_text(["aarch64-linux-gnu-readelf", "-Ws", str(pm_service)])
    lib_symbols = command_text(["bash", "-lc", f"aarch64-linux-gnu-readelf -Ws {str(libperipheral)!r} | c++filt"])
    store.write_text("host/pm-service-qmi-servreg-strings.txt", pm_filtered + "\n")
    store.write_text("host/libperipheral-binder-strings.txt", lib_filtered + "\n")
    artifacts["pm-service-qmi-servreg-strings.txt"] = "host/pm-service-qmi-servreg-strings.txt"
    artifacts["libperipheral-binder-strings.txt"] = "host/libperipheral-binder-strings.txt"

    dispatch = disassembly_texts["pm-service-qmi-msgid-dispatch-0x6ebc-0x7380.S"]
    post_ack = disassembly_texts["pm-service-post-ack-msg22-ind-0x8950-0x8a80.S"]
    handler = disassembly_texts["pm-service-peripheral-restart-handler-0x716c-0x72e0.S"]
    lib_register = disassembly_texts["libperipheral-pm-register-connect-0x612c-0x6700.S"]
    return {
        "pm_service": rel(pm_service),
        "libperipheral_client": rel(libperipheral),
        "artifacts": artifacts,
        "pm_qmi_imports": all(
            symbol in pm_symbols
            for symbol in ("qmi_csi_register_with_options", "qmi_csi_handle_event", "qmi_csi_send_resp", "qmi_csi_send_ind")
        ),
        "pm_msgid_0x20_dispatch": "cmp\tw8, #0x20" in dispatch or "mov\tw2, #0x20" in dispatch,
        "pm_msgid_0x21_dispatch": "cmp\tw2, #0x21" in dispatch or "mov\tw2, #0x21" in dispatch,
        "pm_msgid_0x22_dispatch": "cmp\tw2, #0x22" in dispatch,
        "pm_msg22_request_string": "QMI service peripheral restart request from %s" in pm_filtered,
        "pm_msg22_response_call": "qmi_csi_send_resp" in handler,
        "pm_post_ack_msg22_indication": "mov\tw1, #0x22" in post_ack and "qmi_csi_send_ind" in post_ack,
        "pm_post_ack_pending_restart_client_slot": "[x20, #200]" in post_ack,
        "libperipheral_binder_descriptor": "vendor.qcom.PeripheralManager" in lib_filtered,
        "libperipheral_vndbinder": "/dev/vndbinder" in lib_filtered,
        "libperipheral_pm_register_connect": "pm_register_connect" in lib_filtered or "pm_register_connect" in lib_symbols,
        "libperipheral_qmi_imports": "qmi_" in lib_symbols,
        "libperipheral_register_uses_binder_transact": "transact" in lib_register and "writeStrongBinder" in lib_symbols,
    }


def android_normal_summary(android_dir: Path, v1755_manifest_path: Path) -> dict[str, Any]:
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    request_lines = read_text(android_dir / "request-lines.txt").splitlines()
    v1755 = read_json(v1755_manifest_path)
    wlan0_time = first_dmesg_time(dmesg_lines, r"\bdev : wlan0\b|\bicnss .*wlan0")
    all_text = "\n".join(
        read_text(android_dir / name)
        for name in ("logcat-filtered.txt", "dmesg-filtered.txt", "request-lines.txt")
    )
    qmi_log_hits = len(
        re.findall(
            r"QMI service peripheral restart|QMI service system restart|msg(?:_| )?0x22|peripheral restart request",
            all_text,
            re.IGNORECASE,
        )
    )
    return {
        "android_dir": rel(android_dir),
        "v1755_manifest": rel(v1755_manifest_path),
        "v1755_decision": v1755.get("decision", ""),
        "v1755_pass": bool(v1755.get("pass")),
        "pm_register_count": count_lines(logcat_lines, r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered"),
        "pm_vote_count": count_lines(logcat_lines, r"cnss-daemon voting for modem"),
        "pm_vote_first_time": first_logcat_time(logcat_lines, r"cnss-daemon voting for modem"),
        "wlfw_service_request_count": count_lines(logcat_lines, r"wlfw_service_request: Start the pthread"),
        "wlfw_service_request_first_time": first_logcat_time(logcat_lines, r"wlfw_service_request: Start the pthread"),
        "wlanmdsp_count": count_lines(logcat_lines, r"wlanmdsp\.mbn"),
        "wlanmdsp_first_time": first_logcat_time(logcat_lines, r"wlanmdsp\.mbn"),
        "wlan_pd_indication_time_s": first_dmesg_time(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlan0_time_s": wlan0_time,
        "pcie_or_mhi_before_wlan0": count_dmesg_before(
            dmesg_lines,
            r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b",
            wlan0_time,
        ),
        "servnotif_wlan_pd_line": first_line(request_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlfw_connected_line": first_line(logcat_lines, r"WLFW service connected"),
        "pm_qmi_msg22_log_hits": qmi_log_hits,
        "pm_qmi_trace_observability": qmi_log_hits > 0,
    }


def native_post_vote_summary(v1847_manifest_path: Path,
                             v1802_manifest_path: Path,
                             v1803_manifest_path: Path,
                             v1884_manifest_path: Path) -> dict[str, Any]:
    v1847 = read_json(v1847_manifest_path)
    v1802 = read_json(v1802_manifest_path)
    v1803 = read_json(v1803_manifest_path)
    v1884 = read_json(v1884_manifest_path)
    gate1847 = v1847.get("gate") or {}
    details1802 = v1802.get("details") or {}
    details1803 = v1803.get("details") or {}
    early_listener = details1803.get("service_notifier_listener") or {}
    late_listener = details1803.get("service_notifier_late_listener") or {}
    post_ack_counts = gate1847.get("post_ack_hit_counts") or {}
    return {
        "v1884_manifest": rel(v1884_manifest_path),
        "v1884_decision": v1884.get("decision", ""),
        "v1884_label": v1884.get("label", ""),
        "v1884_pass": bool(v1884.get("pass")),
        "v1847_manifest": rel(v1847_manifest_path),
        "v1847_decision": v1847.get("decision", ""),
        "v1847_pass": bool(v1847.get("pass")),
        "pm_client_register_rc": gate1847.get("pm_client_register_rc", ""),
        "pm_client_connect_rc": gate1847.get("pm_client_connect_rc", ""),
        "open_context_path": gate1847.get("open_context_path", ""),
        "open_context_fd": gate1847.get("open_context_fd", ""),
        "open_context_power_state": gate1847.get("open_context_power_state", ""),
        "post_ack_label": gate1847.get("post_ack_label", ""),
        "post_ack_qmi_restart_ind_hits": intish(post_ack_counts.get("pm_service_post_ack_qmi_restart_ind_call")),
        "post_ack_open_call_hits": intish(post_ack_counts.get("pm_service_post_ack_power_on_open_call")),
        "post_ack_open_ret_hits": intish(post_ack_counts.get("pm_service_post_ack_power_on_open_ret")),
        "klog_sysmon_qmi_counts": gate1847.get("klog_sysmon_qmi_counts", ""),
        "klog_service180_counts": gate1847.get("klog_service180_counts", ""),
        "raw_wlan_pd_text_counts": gate1847.get("raw_wlan_pd_text_counts", ""),
        "servnotif_label": gate1847.get("servnotif_label", ""),
        "lower_service69_progress": bool(gate1847.get("lower_service69_progress")),
        "lower_wlan0_present": bool(gate1847.get("lower_wlan0_present")),
        "lower_mhi_present": bool(gate1847.get("lower_mhi_present")),
        "wlfw_service_request_hits": event_hit_count(details1802, "wlfw_service_request"),
        "dms_service_request_hits": event_hit_count(details1802, "dms_service_request"),
        "wlfw_ind_register_qmi_hits": event_hit_count(details1802, "wlfw_ind_register_qmi"),
        "wlfw_cap_qmi_hits": event_hit_count(details1802, "wlfw_cap_qmi"),
        "requested_wlanmdsp": details1803.get("requested_wlanmdsp", ""),
        "wlfw_service69_seen": details1803.get("wlfw_service69_seen", ""),
        "wlan0_present": details1803.get("wlan0_present", ""),
        "early_servnotif_state": early_listener.get("response_curr_state_name", ""),
        "late_servnotif_state": late_listener.get("response_curr_state_name", ""),
    }


def classify(source: dict[str, Any],
             android: dict[str, Any],
             native: dict[str, Any]) -> tuple[str, bool, str, str]:
    source_msg22_ready = (
        source["pm_qmi_imports"]
        and source["pm_msgid_0x20_dispatch"]
        and source["pm_msgid_0x21_dispatch"]
        and source["pm_msgid_0x22_dispatch"]
        and source["pm_msg22_request_string"]
        and source["pm_msg22_response_call"]
        and source["pm_post_ack_msg22_indication"]
        and source["pm_post_ack_pending_restart_client_slot"]
    )
    lib_binder_only = (
        source["libperipheral_binder_descriptor"]
        and source["libperipheral_vndbinder"]
        and source["libperipheral_pm_register_connect"]
        and not source["libperipheral_qmi_imports"]
    )
    android_normal_good = (
        android["v1755_pass"]
        and android["pm_vote_count"] > 0
        and android["wlfw_service_request_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["wlan_pd_indication_time_s"] is not None
        and android["pcie_or_mhi_before_wlan0"] == 0
    )
    native_post_open_gap = (
        native["v1884_pass"]
        and native["v1847_pass"]
        and native["open_context_path"] == "/dev/subsys_modem"
        and native["pm_client_register_rc"] == "0"
        and native["pm_client_connect_rc"] == "0"
        and native["post_ack_open_call_hits"] > 0
        and native["post_ack_qmi_restart_ind_hits"] == 0
        and native["wlfw_service_request_hits"] > 0
        and native["wlfw_ind_register_qmi_hits"] == 0
        and native["wlfw_cap_qmi_hits"] == 0
        and native["requested_wlanmdsp"] == "0"
        and native["wlfw_service69_seen"] == "0"
        and native["early_servnotif_state"] == "uninit"
        and native["late_servnotif_state"] == "uninit"
    )
    if not source_msg22_ready:
        return (
            "v1885-pm-service-msg22-source-map-incomplete",
            False,
            "pm-service QMI msg 0x22 peripheral-restart source map is incomplete",
            "pm-msg22-source-map-missing",
        )
    if not lib_binder_only:
        return (
            "v1885-libperipheral-pm-surface-ambiguous",
            False,
            "libperipheral_client is not proven Binder-only for PM register/vote",
            "libperipheral-surface-ambiguous",
        )
    if not android_normal_good:
        return (
            "v1885-android-normal-trigger-window-incomplete",
            False,
            "normal Android trigger window is not complete or is PCIe/MHI-contaminated",
            "android-normal-trigger-window-missing",
        )
    if not native_post_open_gap:
        return (
            "v1885-native-post-open-gap-mismatch",
            False,
            "native post-open evidence does not match the expected no-msg22/no-WLFW69/no-wlanmdsp gap",
            "native-post-open-gap-mismatch",
        )
    return (
        "v1885-internal-pm-qmi-servreg-trigger-source-diff-host-pass",
        True,
        "pm-service exposes QMI msg 0x22 peripheral-restart request/indication and libperipheral is Binder-only; Android normal reaches wlanmdsp after PM vote, but the retained normal trace lacks pm-service QMI observability while native post-open has zero msg22 indication and stays wlan_pd uninit",
        "pm-msg22-servreg-trigger-trace-gap",
    )


def render_report(result: dict[str, Any]) -> str:
    source = result["source"]
    android = result["android_normal"]
    native = result["native_post_open"]
    return "\n".join(
        [
            "# Native Init V1885 Internal PM QMI/servreg Trigger Source Diff",
            "",
            "## Summary",
            "",
            "- Cycle: `V1885`",
            "- Type: host-only source/retained-trace classifier for the internal-modem guest-PD trigger gap",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Source Map",
            "",
            f"- pm-service binary: `{source['pm_service']}`",
            f"- QMI imports present: `{source['pm_qmi_imports']}`",
            f"- QMI msg dispatch 0x20/0x21/0x22: `{source['pm_msgid_0x20_dispatch']}` / `{source['pm_msgid_0x21_dispatch']}` / `{source['pm_msgid_0x22_dispatch']}`",
            f"- msg 0x22 request string: `{source['pm_msg22_request_string']}`",
            f"- msg 0x22 response/indication paths: `{source['pm_msg22_response_call']}` / `{source['pm_post_ack_msg22_indication']}`",
            f"- msg 0x22 pending-client slot seen: `{source['pm_post_ack_pending_restart_client_slot']}`",
            f"- libperipheral Binder/vndbinder/PM-register/QMI-imports: `{source['libperipheral_binder_descriptor']}` / `{source['libperipheral_vndbinder']}` / `{source['libperipheral_pm_register_connect']}` / `{source['libperipheral_qmi_imports']}`",
            f"- source artifacts: `{json.dumps(source['artifacts'], sort_keys=True)}`",
            "",
            "## Android Normal Window",
            "",
            f"- Evidence: `{android['android_dir']}`",
            f"- PM register/vote counts: `{android['pm_register_count']}` / `{android['pm_vote_count']}`",
            f"- PM vote / WLFW request / wlanmdsp first times: `{android['pm_vote_first_time']}` / `{android['wlfw_service_request_first_time']}` / `{android['wlanmdsp_first_time']}`",
            f"- wlan_pd indication / wlan0 seconds: `{android['wlan_pd_indication_time_s']}` / `{android['wlan0_time_s']}`",
            f"- PCIe-or-MHI lines before wlan0: `{android['pcie_or_mhi_before_wlan0']}`",
            f"- Retained pm-service msg22 log hits: `{android['pm_qmi_msg22_log_hits']}`",
            f"- service-notifier line: `{android['servnotif_wlan_pd_line']}`",
            f"- WLFW connected line: `{android['wlfw_connected_line']}`",
            "",
            "## Native Post-open State",
            "",
            f"- V1884 decision/label/pass: `{native['v1884_decision']}` / `{native['v1884_label']}` / `{native['v1884_pass']}`",
            f"- PM client register/connect rc: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}`",
            f"- open context path/fd/state: `{native['open_context_path']}` / `{native['open_context_fd']}` / `{native['open_context_power_state']}`",
            f"- post-ack open call/return/msg22-ind hits: `{native['post_ack_open_call_hits']}` / `{native['post_ack_open_ret_hits']}` / `{native['post_ack_qmi_restart_ind_hits']}`",
            f"- SSCTL/service180/wlan_pd raw counts: `{native['klog_sysmon_qmi_counts']}` / `{native['klog_service180_counts']}` / `{native['raw_wlan_pd_text_counts']}`",
            f"- WLFW request/DMS/ind-register/cap hits: `{native['wlfw_service_request_hits']}` / `{native['dms_service_request_hits']}` / `{native['wlfw_ind_register_qmi_hits']}` / `{native['wlfw_cap_qmi_hits']}`",
            f"- requested wlanmdsp / WLFW service69 / wlan0: `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}` / `{native['wlan0_present']}`",
            f"- service-notifier early/late state: `{native['early_servnotif_state']}` / `{native['late_servnotif_state']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- pm-service has a concrete modem-facing QMI msg `0x22` peripheral-restart request/indication path; libperipheral_client only covers the Binder PM register/vote surface.",
            "- Android-normal retained evidence proves the correct internal sequence through PM vote, `wlanmdsp.mbn`, `msm/modem/wlan_pd`, and `wlan0` with no PCIe/MHI contamination.",
            "- Native proves PM vote/open now succeeds but no msg `0x22` indication path fires, service-notifier remains `uninit`, WLFW service 69 is absent, and no `wlanmdsp.mbn` request occurs.",
            "- The next useful live comparison is a read-only normal-Android pm-service QMI/servreg/SSCTL trace around PM vote to `wlanmdsp`, then the same native post-open trace; do not infer this from SDX50M, PCIe, or GDSC evidence.",
            "",
            "## Safety Scope",
            "",
            "V1885 is host-only. It reads retained evidence and local binaries, runs local disassembly/string extraction, and writes local reports only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Capture normal Android boot, not the degraded 257s boot, with read-only pm-service QMI msg-id/servreg/SSCTL visibility from PM vote through the first `wlanmdsp.mbn` request.",
            "- Diff that against native post-`/dev/subsys_modem` open; expected discriminator is msg `0x22`/servreg transition observed on Android and absent on native, or proof that another servreg/SSCTL request is the actual trigger.",
            "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present in native init.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--libperipheral", type=Path, default=DEFAULT_LIBPERIPHERAL)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--v1755-manifest", type=Path, default=DEFAULT_V1755_MANIFEST)
    parser.add_argument("--v1802-manifest", type=Path, default=DEFAULT_V1802_MANIFEST)
    parser.add_argument("--v1803-manifest", type=Path, default=DEFAULT_V1803_MANIFEST)
    parser.add_argument("--v1847-manifest", type=Path, default=DEFAULT_V1847_MANIFEST)
    parser.add_argument("--v1884-manifest", type=Path, default=DEFAULT_V1884_MANIFEST)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    source = source_summary(store, args.pm_service, args.libperipheral)
    android = android_normal_summary(args.android_dir, args.v1755_manifest)
    native = native_post_vote_summary(
        args.v1847_manifest,
        args.v1802_manifest,
        args.v1803_manifest,
        args.v1884_manifest,
    )
    decision, passed, reason, label = classify(source, android, native)

    result = {
        "cycle": "V1885",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "source": source,
        "android_normal": android,
        "native_post_open": native,
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
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
