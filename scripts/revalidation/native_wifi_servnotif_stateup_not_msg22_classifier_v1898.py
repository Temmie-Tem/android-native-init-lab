#!/usr/bin/env python3
"""V1898 host-only classifier for the internal service-notifier state-up gap."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1898-servnotif-stateup-not-msg22-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1898_SERVNOTIF_STATEUP_NOT_MSG22_CLASSIFIER_2026-06-03.md"
)
DEFAULT_ANDROID_DIR = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1897-android-normal-pm-msg22-edge-handoff-live3-20260603-193411"
    / "android-postfs-evidence"
    / "a90-v1897-pm-edge"
)
DEFAULT_V1897_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1897-android-normal-pm-msg22-edge-handoff-live3-20260603-193411" / "manifest.json"
)
DEFAULT_V1888_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1897-live3-v1888-validate" / "manifest.json"
DEFAULT_V1894_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1897-live3-v1894-validate" / "manifest.json"
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_V1816_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1816-lower-publication-precondition-handoff" / "manifest.json"
DEFAULT_V1826_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1826-qipcrtr-bind-target-classifier" / "manifest.json"


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
PM_MSG22_RE = re.compile(
    r"QMI service peripheral restart request|QMI service peripheral restart response|"
    r"peripheral restart request|msg(?:_| |id)?0x22|msg(?:_| |id)?22|pm_msg22",
    re.IGNORECASE,
)
PM_MSG22_NOISE_RE = re.compile(
    r"a90_v1897_pm_(?:edge|msg22)|SRC pm_edge_observer|"
    r"trace_uprobe: Event .*pm_msg22.*doesn'?t exist|"
    r"event\\.pm_msg22|result=.*msg22|armed=|hit_count=|msg22_hit_count=",
    re.IGNORECASE,
)


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


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def positive_count_list(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return any(intish(part) > 0 for part in parts)


def zero_count_list(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def count_lines(lines: list[str], pattern: str | re.Pattern[str]) -> int:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    return sum(1 for line in lines if regex.search(line))


def first_line(lines: list[str], pattern: str | re.Pattern[str]) -> str:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def first_dmesg_time(lines: list[str], pattern: str | re.Pattern[str]) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_dmesg_before(lines: list[str], pattern: str | re.Pattern[str], before_time: float | None) -> int:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
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


def key_order(times: dict[str, float | None]) -> bool:
    required = [
        times["ssctl_modem"],
        times["service74"],
        times["service180"],
        times["wlfw_request"],
        times["wlan_pd"],
        times["wlan0"],
    ]
    if not all(value is not None for value in required):
        return False
    ssctl_modem = times["ssctl_modem"]
    service74 = times["service74"]
    service180 = times["service180"]
    wlfw_request = times["wlfw_request"]
    wlan_pd = times["wlan_pd"]
    wlan0 = times["wlan0"]
    assert ssctl_modem is not None
    assert service74 is not None
    assert service180 is not None
    assert wlfw_request is not None
    assert wlan_pd is not None
    assert wlan0 is not None
    return ssctl_modem <= min(service74, service180) <= max(service74, service180) <= wlfw_request <= wlan_pd <= wlan0


def parse_uprobe_summary(text: str) -> dict[str, Any]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return {
        "armed": values.get("armed", "0"),
        "hit_count": intish(values.get("hit_count")),
        "msg22_hit_count": intish(values.get("msg22_hit_count")),
        "pm_service": values.get("pm_service", ""),
        "result": values.get("result", ""),
    }


def android_summary(android_dir: Path, v1897_manifest_path: Path, v1888_manifest_path: Path,
                    v1894_manifest_path: Path) -> dict[str, Any]:
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    request_lines = read_text(android_dir / "request-lines.txt").splitlines()
    uprobe = parse_uprobe_summary(read_text(android_dir / "pm-service-uprobe-summary.txt"))
    v1897 = read_json(v1897_manifest_path)
    v1888 = read_json(v1888_manifest_path)
    v1894 = read_json(v1894_manifest_path)
    signal_lines = [line for line in logcat_lines + dmesg_lines + request_lines if not PM_MSG22_NOISE_RE.search(line)]
    wlan0_time = first_dmesg_time(dmesg_lines, r"\bdev : wlan0\b|\bicnss .*wlan0")
    times = {
        "ssctl_modem": first_dmesg_time(dmesg_lines, r"sysmon-qmi: ssctl_new_server: .*modem's SSCTL service"),
        "service74": first_dmesg_time(dmesg_lines, r"service-notifier: service_notifier_new_server: .* 74 service"),
        "service180": first_dmesg_time(dmesg_lines, r"service-notifier: service_notifier_new_server: .* 180 service"),
        "wlfw_request": first_dmesg_time(dmesg_lines, r"cnss-daemon wlfw_service_request"),
        "wlan_pd": first_dmesg_time(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlan0": wlan0_time,
    }
    pcie_mhi_before_wlan0 = count_dmesg_before(
        dmesg_lines,
        r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable",
        wlan0_time,
    )
    esoc_boot_failed_before_wlan0 = count_dmesg_before(dmesg_lines, r"esoc0.*boot.*fail|boot_failed", wlan0_time)
    return {
        "android_dir": rel(android_dir),
        "v1897_decision": v1897.get("decision", ""),
        "v1897_label": v1897.get("label", ""),
        "v1897_pass": boolish(v1897.get("pass")),
        "v1897_rollback_selftest_fail0": boolish(v1897.get("rollback_selftest_fail0")),
        "v1888_label": v1888.get("label", ""),
        "v1888_pass": boolish(v1888.get("pass")),
        "v1894_label": v1894.get("label", ""),
        "v1894_pass": boolish(v1894.get("pass")),
        "logcat_lines": len(logcat_lines),
        "dmesg_lines": len(dmesg_lines),
        "request_lines": len(request_lines),
        "pm_vote_count": count_lines(logcat_lines, r"cnss-daemon voting for modem"),
        "wlfw_request_count": count_lines(logcat_lines + dmesg_lines, r"wlfw_service_request"),
        "wlan_pd_count": count_lines(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlanmdsp_count": count_lines(logcat_lines + request_lines, r"wlanmdsp\.mbn"),
        "wlan0_time_s": wlan0_time,
        "times_s": times,
        "ordered_internal_stateup": key_order(times),
        "service74_count": count_lines(dmesg_lines, r"service_notifier_new_server: .* 74 service"),
        "service180_count": count_lines(dmesg_lines, r"service_notifier_new_server: .* 180 service"),
        "icnss_qmi_connected_count": count_lines(dmesg_lines + logcat_lines, r"QMI Server Connected|WLFW service connected"),
        "pm_msg22_hits": count_lines(signal_lines, PM_MSG22_RE),
        "pm_msg22_first_line": first_line(signal_lines, PM_MSG22_RE),
        "uprobe": uprobe,
        "pcie_mhi_before_wlan0": pcie_mhi_before_wlan0,
        "esoc_boot_failed_before_wlan0": esoc_boot_failed_before_wlan0,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "first_ssctl_modem_line": first_line(
            dmesg_lines, r"sysmon-qmi: ssctl_new_server: .*modem's SSCTL service"
        ),
        "first_service74_line": first_line(dmesg_lines, r"service_notifier_new_server: .* 74 service"),
        "first_service180_line": first_line(dmesg_lines, r"service_notifier_new_server: .* 180 service"),
        "first_wlfw_request_line": first_line(dmesg_lines + logcat_lines, r"wlfw_service_request"),
        "first_wlan_pd_line": first_line(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "first_wlanmdsp_line": first_line(logcat_lines + request_lines, r"wlanmdsp\.mbn"),
    }


def native_summary(v1885_manifest_path: Path, v1816_manifest_path: Path, v1826_manifest_path: Path) -> dict[str, Any]:
    v1885 = read_json(v1885_manifest_path)
    v1816 = read_json(v1816_manifest_path)
    v1826 = read_json(v1826_manifest_path)
    post_open = v1885.get("native_post_open") or {}
    gate = v1816.get("gate") or {}
    qipcrtr = v1826.get("details") or {}
    return {
        "v1885_manifest": rel(v1885_manifest_path),
        "v1885_decision": v1885.get("decision", ""),
        "v1885_label": v1885.get("label", ""),
        "v1885_pass": boolish(v1885.get("pass")),
        "v1816_decision": v1816.get("decision", ""),
        "v1816_pass": boolish(v1816.get("pass")),
        "v1826_decision": v1826.get("decision", ""),
        "v1826_pass": boolish(v1826.get("pass")),
        "pm_client_register_rc": str(post_open.get("pm_client_register_rc", "")),
        "pm_client_connect_rc": str(post_open.get("pm_client_connect_rc", "")),
        "open_context_path": post_open.get("open_context_path", ""),
        "open_context_fd": post_open.get("open_context_fd", ""),
        "open_context_power_state": post_open.get("open_context_power_state", ""),
        "post_ack_open_call_hits": intish(post_open.get("post_ack_open_call_hits")),
        "post_ack_msg22_ind_hits": intish(post_open.get("post_ack_qmi_restart_ind_hits")),
        "wlfw_service_request_hits": intish(post_open.get("wlfw_service_request_hits")),
        "wlfw_ind_register_hits": intish(post_open.get("wlfw_ind_register_qmi_hits")),
        "wlfw_cap_hits": intish(post_open.get("wlfw_cap_qmi_hits")),
        "requested_wlanmdsp": str(post_open.get("requested_wlanmdsp", "")),
        "wlfw_service69_seen": str(post_open.get("wlfw_service69_seen", "")),
        "wlan0_present": str(post_open.get("wlan0_present", "")),
        "early_servnotif_state": post_open.get("early_servnotif_state", ""),
        "late_servnotif_state": post_open.get("late_servnotif_state", ""),
        "v1885_sysmon_qmi_counts": post_open.get("klog_sysmon_qmi_counts", ""),
        "v1885_service180_counts": post_open.get("klog_service180_counts", ""),
        "v1885_wlan_pd_counts": post_open.get("raw_wlan_pd_text_counts", ""),
        "v1816_service180_counts": gate.get("raw_service180_text_counts", ""),
        "v1816_service74_counts": gate.get("raw_service74_text_counts", ""),
        "v1816_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "v1816_servnotif_state_early": gate.get("service_notifier_early_state", ""),
        "v1816_servnotif_state_late": gate.get("service_notifier_late_state", ""),
        "v1816_wlfw_service69_seen": str(gate.get("wlfw_service69_seen", "")),
        "v1816_wlan0_present": str(gate.get("wlan0_present", "")),
        "v1826_service180_counts": qipcrtr.get("native_service180_counts", ""),
        "v1826_service74_counts": qipcrtr.get("native_service74_counts", ""),
        "v1826_wlan_pd_counts": qipcrtr.get("native_wlan_pd_counts", ""),
        "v1826_qipcrtr_port": qipcrtr.get("native_qipcrtr_getsockname_port", ""),
        "v1826_no_lookup_send": str(qipcrtr.get("native_qipcrtr_no_lookup_send", "")),
        "v1826_no_control_payload": str(qipcrtr.get("native_qipcrtr_no_control_payload", "")),
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_normal_stateup = (
        android["v1897_pass"]
        and android["v1897_rollback_selftest_fail0"]
        and android["ordered_internal_stateup"]
        and android["pm_vote_count"] > 0
        and android["wlfw_request_count"] > 0
        and android["service74_count"] > 0
        and android["service180_count"] > 0
        and android["wlan_pd_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["wlan0_time_s"] is not None
    )
    android_clean = (
        not android["degraded_257s_like"]
        and android["pcie_mhi_before_wlan0"] == 0
        and android["esoc_boot_failed_before_wlan0"] == 0
    )
    msg22_absent = (
        android["pm_msg22_hits"] == 0
        and android["uprobe"]["armed"] == "1"
        and android["uprobe"]["hit_count"] == 0
        and android["uprobe"]["msg22_hit_count"] == 0
        and android["v1888_label"] == "android-stateup-without-msg22-log-observability-gap"
        and android["v1894_label"] == "android-stateup-pending-client-observability-gap"
    )
    native_open_ok = (
        native["v1885_pass"]
        and native["pm_client_register_rc"] == "0"
        and native["pm_client_connect_rc"] == "0"
        and native["open_context_path"] == "/dev/subsys_modem"
        and native["post_ack_open_call_hits"] > 0
    )
    native_service180_present = positive_count_list(native["v1885_service180_counts"]) or positive_count_list(
        native["v1816_service180_counts"]
    ) or positive_count_list(native["v1826_service180_counts"])
    native_service74_absent = zero_count_list(native["v1816_service74_counts"]) and zero_count_list(
        native["v1826_service74_counts"]
    )
    native_wlan_pd_absent = (
        zero_count_list(native["v1885_wlan_pd_counts"])
        and zero_count_list(native["v1816_wlan_pd_counts"])
        and zero_count_list(native["v1826_wlan_pd_counts"])
    )
    native_stateup_gap = (
        native_open_ok
        and native["post_ack_msg22_ind_hits"] == 0
        and native["wlfw_service_request_hits"] > 0
        and native["wlfw_ind_register_hits"] == 0
        and native["wlfw_cap_hits"] == 0
        and native["requested_wlanmdsp"] == "0"
        and native["wlfw_service69_seen"] == "0"
        and native["wlan0_present"] == "0"
        and native["late_servnotif_state"] == "uninit"
        and native["v1816_servnotif_state_late"] == "uninit"
        and native_service180_present
        and native_service74_absent
        and native_wlan_pd_absent
    )
    if not android_clean:
        return (
            "v1898-android-normal-capture-contaminated-host-pass",
            True,
            "Android capture is rejected because it is degraded or has PCIe/MHI/eSoC contamination before wlan0",
            "android-normal-capture-contaminated",
        )
    if not android_normal_stateup:
        return (
            "v1898-android-stateup-window-incomplete",
            False,
            "Android normal capture does not prove the ordered internal SSCTL/service-notifier 74+180/WLFW/wlan_pd/wlan0 phase sequence",
            "android-stateup-window-incomplete",
        )
    if not msg22_absent:
        return (
            "v1898-msg22-not-ruled-out",
            False,
            "pm-service msg22/pending-client absence was not proven by the V1897/V1888/V1894 chain",
            "msg22-not-ruled-out",
        )
    if not native_stateup_gap:
        return (
            "v1898-native-service-notifier-gap-mismatch",
            False,
            "native post-open evidence does not match the service180-present/service74-wlan_pd-absent gap",
            "native-service-notifier-gap-mismatch",
        )
    return (
        "v1898-service180-present-wlan-pd-stateup-gap-host-pass",
        True,
        "Normal Android reaches ordered internal service-notifier state-up without pm-service msg22 hits; native post-open has service180 visible but remains service74/wlan_pd absent, service-notifier uninit, and no WLFW69/wlanmdsp/wlan0",
        "service180-present-wlan-pd-stateup-gap",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    return "\n".join(
        [
            "# Native Init V1898 Service-notifier State-up Not Msg22 Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1898`",
            "- Type: host-only classifier over autonomous Android-good V1897 and native post-open evidence",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Android Normal Internal Path",
            "",
            f"- Evidence: `{android['android_dir']}`",
            f"- V1897 decision/label/pass/rollback fail=0: `{android['v1897_decision']}` / `{android['v1897_label']}` / `{android['v1897_pass']}` / `{android['v1897_rollback_selftest_fail0']}`",
            f"- ordered SSCTL/service-notifier 74+180/WLFW request/wlan_pd/wlan0 phase: `{android['ordered_internal_stateup']}`",
            f"- times seconds: `{json.dumps(android['times_s'], sort_keys=True)}`",
            f"- PM vote/WLFW request/service74/service180/wlan_pd/wlanmdsp counts: `{android['pm_vote_count']}` / `{android['wlfw_request_count']}` / `{android['service74_count']}` / `{android['service180_count']}` / `{android['wlan_pd_count']}` / `{android['wlanmdsp_count']}`",
            f"- contamination pre-wlan0 PCIe-MHI/eSoC/degraded257: `{android['pcie_mhi_before_wlan0']}` / `{android['esoc_boot_failed_before_wlan0']}` / `{android['degraded_257s_like']}`",
            f"- pm-service msg22 log/uprobe hits: `{android['pm_msg22_hits']}` / `{android['uprobe']['hit_count']}` / msg22 `{android['uprobe']['msg22_hit_count']}`",
            f"- V1888/V1894 labels: `{android['v1888_label']}` / `{android['v1894_label']}`",
            f"- first service180 line: `{android['first_service180_line']}`",
            f"- first wlan_pd line: `{android['first_wlan_pd_line']}`",
            "",
            "## Native Post-open Gap",
            "",
            f"- V1885 decision/label/pass: `{native['v1885_decision']}` / `{native['v1885_label']}` / `{native['v1885_pass']}`",
            f"- PM register/connect/open: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}` / `{native['open_context_path']}` fd `{native['open_context_fd']}` state `{native['open_context_power_state']}`",
            f"- post-open/msg22/WLFW request/ind-register/cap: `{native['post_ack_open_call_hits']}` / `{native['post_ack_msg22_ind_hits']}` / `{native['wlfw_service_request_hits']}` / `{native['wlfw_ind_register_hits']}` / `{native['wlfw_cap_hits']}`",
            f"- service180/service74/wlan_pd counts V1885: `{native['v1885_service180_counts']}` / n/a / `{native['v1885_wlan_pd_counts']}`",
            f"- service180/service74/wlan_pd counts V1816: `{native['v1816_service180_counts']}` / `{native['v1816_service74_counts']}` / `{native['v1816_wlan_pd_counts']}`",
            f"- service180/service74/wlan_pd counts V1826: `{native['v1826_service180_counts']}` / `{native['v1826_service74_counts']}` / `{native['v1826_wlan_pd_counts']}`",
            f"- service-notifier state and lower gates: `{native['early_servnotif_state']}` -> `{native['late_servnotif_state']}` / WLFW69 `{native['wlfw_service69_seen']}` / wlanmdsp `{native['requested_wlanmdsp']}` / wlan0 `{native['wlan0_present']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- V1897 was the rollbackable autonomous Android handoff path, not the no-flash V1890 runner.",
            "- Normal Android proves the internal modem path: SSCTL modem, service-notifier 74/180, CNSS WLFW request, `msm/modem/wlan_pd`, `wlanmdsp.mbn`, then `wlan0` near 15s.",
            "- The same normal window has zero pm-service msg22 log hits and zero hits on the known msg22 dispatch uprobes, so msg22 is not the selected trigger label.",
            "- Native already opens `/dev/subsys_modem` and sees service180/SSCTL preconditions, but service74 and `msm/modem/wlan_pd` never publish and service-notifier remains `uninit`.",
            "",
            "## Safety Scope",
            "",
            "V1898 is host-only. It parses retained manifests/logs and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.",
            "",
            "## Next",
            "",
            "- If another live comparison is needed, use the same V1753/V1897 autonomous Android-handoff and pre-arm CNSS/QRTR/service-notifier observability before `cnss-daemon` starts.",
            "- Keep the target on internal modem service-notifier/WLFW state-up; do not use SDX50M, PCIe/MHI, eSoC, GDSC, PMIC, GPIO, or regulator gates.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--v1897-manifest", type=Path, default=DEFAULT_V1897_MANIFEST)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888_MANIFEST)
    parser.add_argument("--v1894-manifest", type=Path, default=DEFAULT_V1894_MANIFEST)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    parser.add_argument("--v1816-manifest", type=Path, default=DEFAULT_V1816_MANIFEST)
    parser.add_argument("--v1826-manifest", type=Path, default=DEFAULT_V1826_MANIFEST)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    android = android_summary(args.android_dir, args.v1897_manifest, args.v1888_manifest, args.v1894_manifest)
    native = native_summary(args.v1885_manifest, args.v1816_manifest, args.v1826_manifest)
    decision, passed, reason, label = classify(android, native)
    result = {
        "cycle": "V1898",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "android": android,
        "native": native,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_regulator_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/android-servnotif-stateup-parse.json", json.dumps(android, indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-servnotif-gap-parse.json", json.dumps(native, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
