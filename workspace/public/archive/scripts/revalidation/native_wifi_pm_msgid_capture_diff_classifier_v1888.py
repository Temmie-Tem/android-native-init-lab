#!/usr/bin/env python3
"""V1888 host-only parser for PM msg-id/servreg trigger capture diffs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1888-pm-msgid-capture-diff-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1888_PM_MSGID_CAPTURE_DIFF_CLASSIFIER_2026-06-03.md"
)
DEFAULT_ANDROID_DIR = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
)
DEFAULT_NATIVE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_CONTRACT_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1887-normal-android-pm-msgid-capture-contract" / "manifest.json"
)


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
LOGCAT_TIME_RE = re.compile(r"^\d\d-\d\d\s+(?P<time>\d\d:\d\d:\d\d\.\d+)")
MSG22_RE = re.compile(
    r"QMI service peripheral restart request|QMI service peripheral restart response|"
    r"peripheral restart request|msg(?:_| |id)?0x22|msg(?:_| |id)?22|pm_msg22",
    re.IGNORECASE,
)
MSG20_RE = re.compile(r"QMI service system restart request|msg(?:_| |id)?0x20|pm_msg20", re.IGNORECASE)
MSG21_RE = re.compile(r"QMI service system shutdown request|msg(?:_| |id)?0x21|pm_msg21", re.IGNORECASE)
MSG22_NOISE_RE = re.compile(
    r"a90_v1897_pm_(?:edge|msg22)|SRC pm_edge_observer|"
    r"trace_uprobe: Event .*pm_msg22.*doesn'?t exist|"
    r"event\.pm_msg22|result=.*msg22|armed=|hit_count=|msg22_hit_count=",
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


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def count_lines(lines: list[str], pattern: str | re.Pattern[str]) -> int:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    return sum(1 for line in lines if regex.search(line))


def first_line(lines: list[str], pattern: str | re.Pattern[str]) -> str:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def first_logcat_time(lines: list[str], pattern: str | re.Pattern[str]) -> str:
    line = first_line(lines, pattern)
    match = LOGCAT_TIME_RE.search(line)
    return match.group("time") if match else ""


def first_dmesg_time(lines: list[str], pattern: str | re.Pattern[str]) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
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
        line_time = float(match.group("time"))
        if before_time is not None and line_time > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def android_capture_summary(android_dir: Path) -> dict[str, Any]:
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    request_lines = read_text(android_dir / "request-lines.txt").splitlines()
    all_lines = logcat_lines + dmesg_lines + request_lines
    signal_lines = [line for line in all_lines if not MSG22_NOISE_RE.search(line)]
    wlan0_time = first_dmesg_time(dmesg_lines, r"\bdev : wlan0\b|\bicnss .*wlan0")
    wlan_pd_time = first_dmesg_time(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd")
    pcie_mhi_before_wlan0 = count_dmesg_before(
        dmesg_lines,
        r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable",
        wlan0_time,
    )
    esoc_boot_failed_before_wlan0 = count_dmesg_before(dmesg_lines, r"esoc0.*boot.*fail|boot_failed", wlan0_time)
    wlanmdsp_count = count_lines(logcat_lines, r"wlanmdsp\.mbn")
    return {
        "android_dir": rel(android_dir),
        "logcat_lines": len(logcat_lines),
        "dmesg_lines": len(dmesg_lines),
        "request_lines": len(request_lines),
        "pm_register_count": count_lines(logcat_lines, r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered"),
        "pm_vote_count": count_lines(logcat_lines, r"cnss-daemon voting for modem"),
        "pm_vote_first_time": first_logcat_time(logcat_lines, r"cnss-daemon voting for modem"),
        "wlfw_service_request_count": count_lines(logcat_lines, r"wlfw_service_request"),
        "wlfw_service_request_first_time": first_logcat_time(logcat_lines, r"wlfw_service_request"),
        "wlan_pd_indication_count": count_lines(dmesg_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlan_pd_indication_time_s": wlan_pd_time,
        "wlan_pd_ack_count": count_lines(dmesg_lines, r"send_ind_ack: .*msm/modem/wlan_pd"),
        "icnss_qmi_connected_count": count_lines(dmesg_lines + logcat_lines, r"QMI Server Connected|WLFW service connected"),
        "wlanmdsp_count": wlanmdsp_count,
        "wlanmdsp_first_time": first_logcat_time(logcat_lines, r"wlanmdsp\.mbn"),
        "wlan0_time_s": wlan0_time,
        "pcie_mhi_before_wlan0": pcie_mhi_before_wlan0,
        "esoc_boot_failed_before_wlan0": esoc_boot_failed_before_wlan0,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "pm_msg20_hits": count_lines(signal_lines, MSG20_RE),
        "pm_msg21_hits": count_lines(signal_lines, MSG21_RE),
        "pm_msg22_hits": count_lines(signal_lines, MSG22_RE),
        "pm_msg22_first_line": first_line(signal_lines, MSG22_RE),
        "servnotif_first_line": first_line(dmesg_lines + request_lines, r"service-notifier: .*msm/modem/wlan_pd"),
        "wlanmdsp_first_line": first_line(logcat_lines, r"wlanmdsp\.mbn"),
    }


def native_post_open_summary(native_manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(native_manifest_path)
    native = manifest.get("native_post_open") or {}
    source = manifest.get("source") or {}
    return {
        "manifest": rel(native_manifest_path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "pm_msg22_source_ready": bool(source.get("pm_msgid_0x22_dispatch"))
        and bool(source.get("pm_msg22_request_string"))
        and bool(source.get("pm_msg22_response_call"))
        and bool(source.get("pm_post_ack_msg22_indication")),
        "pm_client_register_rc": native.get("pm_client_register_rc", ""),
        "pm_client_connect_rc": native.get("pm_client_connect_rc", ""),
        "open_context_path": native.get("open_context_path", ""),
        "open_context_fd": native.get("open_context_fd", ""),
        "open_context_power_state": native.get("open_context_power_state", ""),
        "post_ack_open_call_hits": intish(native.get("post_ack_open_call_hits")),
        "post_ack_msg22_ind_hits": intish(native.get("post_ack_qmi_restart_ind_hits")),
        "wlfw_service_request_hits": intish(native.get("wlfw_service_request_hits")),
        "wlfw_ind_register_hits": intish(native.get("wlfw_ind_register_qmi_hits")),
        "wlfw_cap_hits": intish(native.get("wlfw_cap_qmi_hits")),
        "requested_wlanmdsp": native.get("requested_wlanmdsp", ""),
        "wlfw_service69_seen": native.get("wlfw_service69_seen", ""),
        "wlan0_present": native.get("wlan0_present", ""),
        "early_servnotif_state": native.get("early_servnotif_state", ""),
        "late_servnotif_state": native.get("late_servnotif_state", ""),
    }


def contract_summary(contract_manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(contract_manifest_path)
    return {
        "manifest": rel(contract_manifest_path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "fixed_labels": ((manifest.get("capture_contract") or {}).get("fixed_labels") or []),
    }


def classify(android: dict[str, Any],
             native: dict[str, Any],
             contract: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not contract["pass"] or contract["label"] != "normal-android-pm-msgid-capture-contract-ready":
        return (
            "v1888-capture-contract-not-ready",
            False,
            "V1887 normal-Android capture contract is not ready",
            "capture-contract-not-ready",
        )
    android_has_stateup = (
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
        native["pass"]
        and native["open_context_path"] == "/dev/subsys_modem"
        and native["pm_client_register_rc"] == "0"
        and native["pm_client_connect_rc"] == "0"
        and native["post_ack_open_call_hits"] > 0
        and native["post_ack_msg22_ind_hits"] == 0
        and native["wlfw_service_request_hits"] > 0
        and native["wlfw_ind_register_hits"] == 0
        and native["wlfw_cap_hits"] == 0
        and native["requested_wlanmdsp"] == "0"
        and native["wlfw_service69_seen"] == "0"
        and native["wlan0_present"] == "0"
        and native["late_servnotif_state"] == "uninit"
    )
    if android_contaminated:
        return (
            "v1888-android-normal-capture-contaminated-host-pass",
            True,
            "Android capture is rejected because it matches a degraded/PCIe/MHI-contaminated path",
            "android-normal-capture-contaminated",
        )
    if not android_has_stateup:
        return (
            "v1888-capture-incomplete-host-pass",
            True,
            "capture does not contain PM vote, WLAN-PD indication, wlanmdsp, and wlan0 in one normal window",
            "capture-incomplete",
        )
    if android["pm_msg22_hits"] > 0 and native_gap:
        return (
            "v1888-android-msg22-stateup-native-absent-host-pass",
            True,
            "Android normal capture contains msg22/state-up evidence and native post-open lacks the msg22/WLFW/wlanmdsp edge",
            "android-msg22-stateup-observed-native-absent",
        )
    if android["pm_msg22_hits"] == 0 and native_gap:
        return (
            "v1888-android-stateup-msg22-observability-gap-host-pass",
            True,
            "Android normal state-up is present but retained capture has zero pm-service msg22 observability; native post-open still lacks msg22/WLFW/wlanmdsp",
            "android-stateup-without-msg22-log-observability-gap",
        )
    if native["post_ack_msg22_ind_hits"] == 0:
        return (
            "v1888-native-post-open-msg22-still-absent-host-pass",
            True,
            "native post-open evidence still lacks pm-service msg22 indication",
            "native-post-open-msg22-still-absent",
        )
    return (
        "v1888-capture-incomplete-host-pass",
        True,
        "capture did not select a stronger fixed discriminator",
        "capture-incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android_capture"]
    native = result["native_post_open"]
    contract = result["contract"]
    return "\n".join(
        [
            "# Native Init V1888 PM Msg-id Capture Diff Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1888`",
            "- Type: host-only parser/classifier for normal-Android PM msg-id capture versus native post-open evidence",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Android Capture Parse",
            "",
            f"- Evidence dir: `{android['android_dir']}`",
            f"- logcat/dmesg/request lines: `{android['logcat_lines']}` / `{android['dmesg_lines']}` / `{android['request_lines']}`",
            f"- PM register/vote count/time: `{android['pm_register_count']}` / `{android['pm_vote_count']}` / `{android['pm_vote_first_time']}`",
            f"- WLFW request count/time: `{android['wlfw_service_request_count']}` / `{android['wlfw_service_request_first_time']}`",
            f"- wlan_pd indication/ack/time: `{android['wlan_pd_indication_count']}` / `{android['wlan_pd_ack_count']}` / `{android['wlan_pd_indication_time_s']}`",
            f"- wlanmdsp count/time: `{android['wlanmdsp_count']}` / `{android['wlanmdsp_first_time']}`",
            f"- wlan0 time and contamination counts: `{android['wlan0_time_s']}` / PCIe-MHI `{android['pcie_mhi_before_wlan0']}` / esoc-boot-failed `{android['esoc_boot_failed_before_wlan0']}` / degraded257 `{android['degraded_257s_like']}`",
            f"- pm msg20/msg21/msg22 hits: `{android['pm_msg20_hits']}` / `{android['pm_msg21_hits']}` / `{android['pm_msg22_hits']}`",
            f"- first msg22 line: `{android['pm_msg22_first_line']}`",
            f"- first wlan_pd line: `{android['servnotif_first_line']}`",
            f"- first wlanmdsp line: `{android['wlanmdsp_first_line']}`",
            "",
            "## Native Post-open Parse",
            "",
            f"- Manifest decision/label/pass: `{native['decision']}` / `{native['label']}` / `{native['pass']}`",
            f"- PM register/connect/open: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}` / `{native['open_context_path']}` fd `{native['open_context_fd']}` state `{native['open_context_power_state']}`",
            f"- post-ack open/msg22 hits: `{native['post_ack_open_call_hits']}` / `{native['post_ack_msg22_ind_hits']}`",
            f"- WLFW request/ind-register/cap hits: `{native['wlfw_service_request_hits']}` / `{native['wlfw_ind_register_hits']}` / `{native['wlfw_cap_hits']}`",
            f"- wlanmdsp/WLFW69/wlan0/states: `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}` / `{native['wlan0_present']}` / `{native['early_servnotif_state']}` -> `{native['late_servnotif_state']}`",
            "",
            "## Contract",
            "",
            f"- Contract decision/label/pass: `{contract['decision']}` / `{contract['label']}` / `{contract['pass']}`",
            f"- Fixed labels: `{json.dumps(contract['fixed_labels'])}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The retained normal Android sample proves PM vote, WLAN-PD state indication, `wlanmdsp.mbn`, and `wlan0` with zero PCIe/MHI contamination.",
            "- The same retained sample has zero pm-service msg22 observability, so it cannot prove or disprove msg22 as the Android trigger.",
            "- Native post-open still proves the missing edge: `/dev/subsys_modem` open succeeds, but msg22 indication, WLFW service 69, `wlanmdsp.mbn`, and `wlan0` stay absent.",
            "",
            "## Safety Scope",
            "",
            "V1888 is host-only. It parses retained files/manifests and writes local classifier artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Feed this parser a fresh normal-Android capture with pm-service msg-id visibility; the expected stronger label is `android-msg22-stateup-observed-native-absent` if msg22 appears before `wlanmdsp.mbn`.",
            "- Reject degraded 257s boots or any capture with PCIe/MHI before `wlan0`.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--contract-manifest", type=Path, default=DEFAULT_CONTRACT_MANIFEST)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    android = android_capture_summary(args.android_dir)
    native = native_post_open_summary(args.native_manifest)
    contract = contract_summary(args.contract_manifest)
    decision, passed, reason, label = classify(android, native, contract)
    result = {
        "cycle": "V1888",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "android_capture": android,
        "native_post_open": native,
        "contract": contract,
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
    store.write_text("host/android-capture-parse.json", json.dumps(android, indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-post-open-parse.json", json.dumps(native, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
