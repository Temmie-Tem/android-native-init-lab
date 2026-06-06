#!/usr/bin/env python3
"""V1884 host-only selector for the internal-modem post-vote WLAN guest-PD trigger diff."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1884-internal-post-vote-trigger-diff-gate"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1884_INTERNAL_POST_VOTE_TRIGGER_DIFF_GATE_2026-06-03.md"
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
DEFAULT_V1883_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1883-internal-guest-pd-trigger-source-reanchor" / "manifest.json"


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


def count_lines(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in lines if regex.search(line))


def first_line(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


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


def event_first_hit(details: dict[str, Any], name: str) -> str:
    event = details.get(name) or {}
    if not isinstance(event, dict):
        return ""
    return str(event.get("first_hit_line") or "")


def android_normal_summary(android_dir: Path, v1755_manifest_path: Path) -> dict[str, Any]:
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    v1755_manifest = read_json(v1755_manifest_path)
    v1755_android = v1755_manifest.get("android") or {}
    wlan0_time = first_dmesg_time(dmesg_lines, r"\bdev : wlan0\b|\bicnss .*wlan0")
    return {
        "android_dir": rel(android_dir),
        "v1755_manifest": rel(v1755_manifest_path),
        "v1755_decision": v1755_manifest.get("decision", ""),
        "v1755_label": v1755_manifest.get("label", ""),
        "v1755_pass": bool(v1755_manifest.get("pass")),
        "pm_register_count": count_lines(logcat_lines, r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered"),
        "pm_vote_count": count_lines(logcat_lines, r"cnss-daemon voting for modem"),
        "pm_vote_first_time": first_logcat_time(logcat_lines, r"cnss-daemon voting for modem"),
        "wlfw_service_request_count": count_lines(logcat_lines, r"wlfw_service_request: Start the pthread"),
        "wlfw_service_request_first_time": first_logcat_time(logcat_lines, r"wlfw_service_request: Start the pthread"),
        "wlanmdsp_count": count_lines(logcat_lines, r"wlanmdsp\.mbn"),
        "wlanmdsp_first_time": first_logcat_time(logcat_lines, r"wlanmdsp\.mbn"),
        "wlfw_start_time_s": first_dmesg_time(dmesg_lines, r"wlfw_start"),
        "wlan_pd_indication_time_s": first_dmesg_time(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlan0_time_s": wlan0_time,
        "pcie_or_mhi_before_wlan0": count_dmesg_before(
            dmesg_lines,
            r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b",
            wlan0_time,
        ),
        "v1755_android_counts": v1755_android.get("counts") or {},
    }


def native_post_vote_summary(v1847_manifest_path: Path,
                             v1802_manifest_path: Path,
                             v1803_manifest_path: Path) -> dict[str, Any]:
    v1847_manifest = read_json(v1847_manifest_path)
    v1802_manifest = read_json(v1802_manifest_path)
    v1803_manifest = read_json(v1803_manifest_path)
    v1847_gate = v1847_manifest.get("gate") or {}
    v1802_details = v1802_manifest.get("details") or {}
    v1803_details = v1803_manifest.get("details") or {}
    service_notifier_early = v1803_details.get("service_notifier_listener") or {}
    service_notifier_late = v1803_details.get("service_notifier_late_listener") or {}
    qrtr_case_0 = v1803_details.get("qrtr_case_0") or {}
    qrtr_case_1 = v1803_details.get("qrtr_case_1") or {}
    return {
        "v1847_manifest": rel(v1847_manifest_path),
        "v1847_decision": v1847_manifest.get("decision", ""),
        "v1847_pass": bool(v1847_manifest.get("pass")),
        "pm_client_register_rc": v1847_gate.get("pm_client_register_rc", ""),
        "pm_client_connect_rc": v1847_gate.get("pm_client_connect_rc", ""),
        "open_context_path": v1847_gate.get("open_context_path", ""),
        "open_context_fd": v1847_gate.get("open_context_fd", ""),
        "open_context_power_state": v1847_gate.get("open_context_power_state", ""),
        "service_notifier_label": v1847_gate.get("servnotif_label", ""),
        "lower_service69_progress": bool(v1847_gate.get("lower_service69_progress")),
        "lower_wlan0_present": bool(v1847_gate.get("lower_wlan0_present")),
        "lower_mhi_present": bool(v1847_gate.get("lower_mhi_present")),
        "v1802_manifest": rel(v1802_manifest_path),
        "v1802_decision": v1802_manifest.get("decision", ""),
        "v1802_pass": bool(v1802_manifest.get("pass")),
        "v1802_reason": v1802_manifest.get("reason", ""),
        "v1802_source_decision": v1802_details.get("source_decision", ""),
        "source_pm_server_label": v1802_details.get("source_pm_server_label", ""),
        "source_pm_register_success_hits": v1802_details.get("source_pm_register_success_hits", ""),
        "source_list_commit_hits": v1802_details.get("source_list_commit_hits", ""),
        "pm_register_hit_count": event_hit_count(v1802_details, "pm_init_pm_client_register_call"),
        "pm_connect_hit_count": event_hit_count(v1802_details, "pm_init_pm_client_connect_call"),
        "wlfw_start_hit_count": event_hit_count(v1802_details, "wlfw_start"),
        "wlfw_service_request_hit_count": event_hit_count(v1802_details, "wlfw_service_request"),
        "dms_service_request_hit_count": event_hit_count(v1802_details, "dms_service_request"),
        "wlfw_ind_register_qmi_hit_count": event_hit_count(v1802_details, "wlfw_ind_register_qmi"),
        "wlfw_cap_qmi_hit_count": event_hit_count(v1802_details, "wlfw_cap_qmi"),
        "wlfw_service_request_first_hit": event_first_hit(v1802_details, "wlfw_service_request"),
        "v1803_manifest": rel(v1803_manifest_path),
        "v1803_decision": v1803_manifest.get("decision", ""),
        "v1803_pass": bool(v1803_manifest.get("pass")),
        "v1803_reason": v1803_manifest.get("reason", ""),
        "requested_wlanmdsp": v1803_details.get("requested_wlanmdsp", ""),
        "wlfw_service69_seen": v1803_details.get("wlfw_service69_seen", ""),
        "wlan0_present": v1803_details.get("wlan0_present", ""),
        "early_servnotif_state": service_notifier_early.get("response_curr_state_name", ""),
        "early_servnotif_indication_seen": service_notifier_early.get("indication_seen", ""),
        "late_servnotif_state": service_notifier_late.get("response_curr_state_name", ""),
        "late_servnotif_indication_seen": service_notifier_late.get("indication_seen", ""),
        "qrtr_wlfw_case0_service_events": qrtr_case_0.get("readback.service_events", ""),
        "qrtr_wlfw_case0_end_of_list": qrtr_case_0.get("readback.end_of_list", ""),
        "qrtr_wlfw_case1_service_events": qrtr_case_1.get("readback.service_events", ""),
        "qrtr_wlfw_case1_end_of_list": qrtr_case_1.get("readback.end_of_list", ""),
    }


def source_surface_summary(v1883_manifest_path: Path) -> dict[str, Any]:
    v1883_manifest = read_json(v1883_manifest_path)
    source = v1883_manifest.get("source") or {}
    return {
        "v1883_manifest": rel(v1883_manifest_path),
        "v1883_decision": v1883_manifest.get("decision", ""),
        "v1883_label": v1883_manifest.get("label", ""),
        "v1883_pass": bool(v1883_manifest.get("pass")),
        "pm_service_has_qmi_restart_strings": bool(source.get("pm_service_has_qmi_restart_strings")),
        "pm_service_has_qmi_imports": bool(source.get("pm_service_has_qmi_imports")),
        "pm_service_has_vote_strings": bool(source.get("pm_service_has_vote_strings")),
        "libperipheral_has_pm_register_connect": bool(source.get("libperipheral_has_pm_register_connect")),
        "libperipheral_has_binder_descriptor": bool(source.get("libperipheral_has_binder_descriptor")),
        "artifacts": source.get("artifacts") or {},
    }


def classify(android: dict[str, Any],
             native: dict[str, Any],
             source: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_normal_trigger = (
        android["v1755_pass"]
        and android["pm_vote_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["wlan_pd_indication_time_s"] is not None
        and android["pcie_or_mhi_before_wlan0"] == 0
    )
    native_post_vote_gap = (
        native["v1847_pass"]
        and native["open_context_path"] == "/dev/subsys_modem"
        and native["pm_client_register_rc"] == "0"
        and native["pm_client_connect_rc"] == "0"
        and native["v1802_pass"]
        and native["pm_register_hit_count"] > 0
        and native["pm_connect_hit_count"] > 0
        and native["wlfw_service_request_hit_count"] > 0
        and native["dms_service_request_hit_count"] > 0
        and native["wlfw_ind_register_qmi_hit_count"] == 0
        and native["wlfw_cap_qmi_hit_count"] == 0
        and native["v1803_pass"]
        and native["requested_wlanmdsp"] == "0"
        and native["wlfw_service69_seen"] == "0"
        and native["early_servnotif_state"] == "uninit"
        and native["late_servnotif_state"] == "uninit"
    )
    source_ready = (
        source["v1883_pass"]
        and source["pm_service_has_qmi_restart_strings"]
        and source["pm_service_has_qmi_imports"]
        and source["pm_service_has_vote_strings"]
        and source["libperipheral_has_pm_register_connect"]
        and source["libperipheral_has_binder_descriptor"]
    )
    if android_normal_trigger and native_post_vote_gap and source_ready:
        return (
            "v1884-post-pm-success-guest-pd-trigger-diff-selected-host-pass",
            True,
            "Android normal reaches PM vote, wlan_pd indication, and wlanmdsp request without PCIe/MHI; native reaches PM success and /dev/subsys_modem open but stops before WLFW QMI indication/capability sends, WLFW service 69, and wlanmdsp request.",
            "post-pm-success-wlfw-qmi-servreg-trigger-gap",
        )
    return (
        "v1884-internal-trigger-diff-prereq-review",
        False,
        "one or more internal post-vote diff prerequisites were not proven by retained evidence",
        "review",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android_normal"]
    native = result["native_post_vote"]
    source = result["source_surface"]
    return "\n".join([
        "# Native Init V1884 Internal Post-vote Trigger Diff Gate",
        "",
        "## Summary",
        "",
        "- Cycle: `V1884`",
        "- Type: host-only selector for the internal-modem post-vote QMI/servreg guest-PD trigger diff",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1884-internal-post-vote-trigger-diff-gate`",
        "",
        "## Android Normal Trigger",
        "",
        f"- Evidence: `{android['android_dir']}`",
        f"- PM register/vote counts: `{android['pm_register_count']}` / `{android['pm_vote_count']}`",
        f"- PM vote / WLFW request / wlanmdsp first times: `{android['pm_vote_first_time']}` / `{android['wlfw_service_request_first_time']}` / `{android['wlanmdsp_first_time']}`",
        f"- wlfw_start / wlan_pd / wlan0 seconds: `{android['wlfw_start_time_s']}` / `{android['wlan_pd_indication_time_s']}` / `{android['wlan0_time_s']}`",
        f"- wlanmdsp lines: `{android['wlanmdsp_count']}`",
        f"- PCIe-or-MHI lines before wlan0: `{android['pcie_or_mhi_before_wlan0']}`",
        "",
        "## Native Post-vote State",
        "",
        f"- V1847 decision/pass: `{native['v1847_decision']}` / `{native['v1847_pass']}`",
        f"- PM client register/connect rc: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}`",
        f"- open context path/fd/power-state: `{native['open_context_path']}` / `{native['open_context_fd']}` / `{native['open_context_power_state']}`",
        f"- V1802 decision/pass: `{native['v1802_decision']}` / `{native['v1802_pass']}`",
        f"- source PM server/list/register labels: `{native['source_pm_server_label']}` / `{native['source_list_commit_hits']}` / `{native['source_pm_register_success_hits']}`",
        f"- PM register/connect/WLFW request/DMS hits: `{native['pm_register_hit_count']}` / `{native['pm_connect_hit_count']}` / `{native['wlfw_service_request_hit_count']}` / `{native['dms_service_request_hit_count']}`",
        f"- WLFW ind-register/capability QMI hits: `{native['wlfw_ind_register_qmi_hit_count']}` / `{native['wlfw_cap_qmi_hit_count']}`",
        f"- V1803 decision/pass: `{native['v1803_decision']}` / `{native['v1803_pass']}`",
        f"- requested wlanmdsp / WLFW service69 / wlan0: `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}` / `{native['wlan0_present']}`",
        f"- service-notifier early/late state: `{native['early_servnotif_state']}` / `{native['late_servnotif_state']}`",
        f"- QRTR WLFW case0/case1 service events: `{native['qrtr_wlfw_case0_service_events']}` / `{native['qrtr_wlfw_case1_service_events']}`",
        "",
        "## Source Surface",
        "",
        f"- V1883 decision/label/pass: `{source['v1883_decision']}` / `{source['v1883_label']}` / `{source['v1883_pass']}`",
        f"- pm-service QMI restart/imports/vote strings: `{source['pm_service_has_qmi_restart_strings']}` / `{source['pm_service_has_qmi_imports']}` / `{source['pm_service_has_vote_strings']}`",
        f"- libperipheral PM register/Binder descriptor: `{source['libperipheral_has_pm_register_connect']}` / `{source['libperipheral_has_binder_descriptor']}`",
        f"- source artifacts: `{json.dumps(source['artifacts'], sort_keys=True)}`",
        "",
        "## Selected Diff",
        "",
        "- Label: `post-pm-success-wlfw-qmi-servreg-trigger-gap`.",
        "- The next useful unit is a read-only Android-normal versus native-post-vote diff for the QMI/servreg/SSCTL request that moves `msm/modem/wlan_pd` from `uninit` to an indication state and causes the `wlanmdsp.mbn` request.",
        "- The SDX50M/PCIe/eSoC/GDSC path remains rejected for wlan0; do not optimize against degraded 257s boots.",
        "",
        "## Safety Scope",
        "",
        "V1884 is host-only. It reads retained evidence and local source/disassembly summaries only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
        "",
        "## Next",
        "",
        "- Build the constrained read-only comparator around Android normal `per_mgr_vote`/pm-service QMI/servreg/SSCTL and native post-`/dev/subsys_modem` open absence.",
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present in native init.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--v1755-manifest", type=Path, default=DEFAULT_V1755_MANIFEST)
    parser.add_argument("--v1802-manifest", type=Path, default=DEFAULT_V1802_MANIFEST)
    parser.add_argument("--v1803-manifest", type=Path, default=DEFAULT_V1803_MANIFEST)
    parser.add_argument("--v1847-manifest", type=Path, default=DEFAULT_V1847_MANIFEST)
    parser.add_argument("--v1883-manifest", type=Path, default=DEFAULT_V1883_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    android = android_normal_summary(args.android_dir, args.v1755_manifest)
    native = native_post_vote_summary(args.v1847_manifest, args.v1802_manifest, args.v1803_manifest)
    source = source_surface_summary(args.v1883_manifest)
    decision, pass_ok, reason, label = classify(android, native, source)
    result = {
        "cycle": "V1884",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "android_normal": android,
        "native_post_vote": native,
        "source_surface": source,
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
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
