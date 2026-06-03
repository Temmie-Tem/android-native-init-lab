#!/usr/bin/env python3
"""V1883 host-only re-anchor on the internal-modem WLAN guest-PD trigger."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1883-internal-guest-pd-trigger-source-reanchor"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1883_INTERNAL_GUEST_PD_TRIGGER_SOURCE_REANCHOR_2026-06-03.md"
)
DEFAULT_V1753_ANDROID = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1753-android-good-wlan-pd-firmware-request"
    / "android-postfs-evidence"
    / "a90-v1753-wlan-pd-fwreq"
)
DEFAULT_V1847_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1847-pm-service-open-context-handoff" / "manifest.json"
DEFAULT_V1803_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1803-wlfw-qmi-readiness-classifier" / "manifest.json"
DEFAULT_PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
DEFAULT_LIBPERIPHERAL = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "libperipheral_client.so"


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
LOGCAT_TIME_RE = re.compile(r"^\d\d-\d\d\s+(?P<time>\d\d:\d\d:\d\d\.\d+)")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def first_dmesg_time(lines: list[str], pattern: re.Pattern[str]) -> float | None:
    for line in lines:
        if not pattern.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def first_logcat_time(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        if not pattern.search(line):
            continue
        match = LOGCAT_TIME_RE.search(line)
        if match:
            return match.group("time")
    return ""


def count_dmesg_before(lines: list[str], pattern: re.Pattern[str], before: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before is not None and float(match.group("time")) > before:
            continue
        if pattern.search(line):
            count += 1
    return count


def command_text(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def write_source_artifacts(store: EvidenceStore, pm_service: Path, libperipheral: Path) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    objdumps = {
        "libperipheral-client-pm-register-connect-0x612c-0x6700.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x612c",
            "--stop-address=0x6700",
            str(libperipheral),
        ],
        "libperipheral-client-bn-ontransact-0x85bc-0x8860.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x85bc",
            "--stop-address=0x8860",
            str(libperipheral),
        ],
        "pm-service-qmi-main-0x7000-0x7f00.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x7000",
            "--stop-address=0x7f00",
            str(pm_service),
        ],
        "pm-service-qmi-requests-0x8b00-0x9f00.S": [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x8b00",
            "--stop-address=0x9f00",
            str(pm_service),
        ],
    }
    for name, command in objdumps.items():
        text = command_text(command)
        store.write_text(f"host/{name}", text)
        artifacts[name] = f"host/{name}"

    pm_strings = command_text(["strings", "-a", "-tx", str(pm_service)])
    pm_filtered = "\n".join(
        line
        for line in pm_strings.splitlines()
        if re.search(
            r"QMI service .*request|restart request|shutdown request|going on-line|going off-line|voter|vote|power on|subsys_modem|wlan_pd|wlanmdsp|vendor\.peripheral|Peripheral Mananager|modem",
            line,
            re.IGNORECASE,
        )
    )
    lib_strings = command_text(["strings", "-a", "-tx", str(libperipheral)])
    lib_filtered = "\n".join(
        line
        for line in lib_strings.splitlines()
        if re.search(
            r"pm_register_connect|pm_client|PeripheralManager|vendor\.qcom\.PeripheralManager|vote|restart|wlan_pd|wlanmdsp|subsys",
            line,
            re.IGNORECASE,
        )
    )
    store.write_text("host/pm-service-qmi-trigger-strings.txt", pm_filtered + "\n")
    store.write_text("host/libperipheral-client-trigger-strings.txt", lib_filtered + "\n")
    artifacts["pm-service-qmi-trigger-strings.txt"] = "host/pm-service-qmi-trigger-strings.txt"
    artifacts["libperipheral-client-trigger-strings.txt"] = "host/libperipheral-client-trigger-strings.txt"

    pm_symbols = command_text(["aarch64-linux-gnu-readelf", "-Ws", str(pm_service)])
    lib_symbols = command_text(["bash", "-lc", f"aarch64-linux-gnu-readelf -Ws {str(libperipheral)!r} | c++filt"])
    return {
        "artifacts": artifacts,
        "pm_service_has_qmi_restart_strings": "QMI service system restart request" in pm_filtered
        and "QMI service peripheral restart request" in pm_filtered,
        "pm_service_has_vote_strings": "vote" in pm_filtered,
        "pm_service_has_qmi_imports": "qmi_csi_register_with_options" in pm_symbols
        and "qmi_csi_send_ind" in pm_symbols
        and "qmi_csi_send_resp" in pm_symbols,
        "libperipheral_has_pm_register_connect": "pm_register_connect" in lib_filtered,
        "libperipheral_has_binder_descriptor": "vendor.qcom.PeripheralManager" in lib_filtered,
        "libperipheral_has_qmi_imports": "qmi_" in lib_symbols,
    }


def android_normal_summary(android_dir: Path) -> dict[str, Any]:
    dmesg_lines = read_text(android_dir / "dmesg-filtered.txt").splitlines()
    logcat_lines = read_text(android_dir / "logcat-filtered.txt").splitlines()
    request_summary = {}
    for line in read_text(android_dir / "request-summary.txt").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            request_summary[key] = value
    wlan_pd_time = first_dmesg_time(dmesg_lines, re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE))
    wlan0_time = first_dmesg_time(dmesg_lines, re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0", re.IGNORECASE))
    wlfw_start_time = first_dmesg_time(dmesg_lines, re.compile(r"wlfw_start", re.IGNORECASE))
    wlanmdsp_time = first_logcat_time(logcat_lines, re.compile(r"wlanmdsp\.mbn", re.IGNORECASE))
    pcie_before_wlan0 = count_dmesg_before(
        dmesg_lines,
        re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b", re.IGNORECASE),
        wlan0_time,
    )
    return {
        "dir": rel(android_dir),
        "request_summary": request_summary,
        "requested_wlanmdsp": request_summary.get("requested_wlanmdsp") == "1",
        "requested_pd_image": request_summary.get("requested_pd_image") == "1",
        "wlfw_start_time_s": wlfw_start_time,
        "wlan_pd_indication_time_s": wlan_pd_time,
        "wlan0_time_s": wlan0_time,
        "first_wlanmdsp_logcat_time": wlanmdsp_time,
        "wlanmdsp_logcat_lines": sum(1 for line in logcat_lines if "wlanmdsp.mbn" in line),
        "pcie_or_mhi_before_wlan0_lines": pcie_before_wlan0,
    }


def native_pm_summary(v1847_manifest: Path, v1803_manifest: Path) -> dict[str, Any]:
    v1847 = read_json(v1847_manifest)
    v1803 = read_json(v1803_manifest)
    gate1847 = v1847.get("gate") or {}
    details1803 = (v1803.get("details") or v1803.get("gate") or {})
    return {
        "v1847_manifest": rel(v1847_manifest),
        "v1847_decision": v1847.get("decision"),
        "v1847_pass": bool(v1847.get("pass")),
        "open_context_path": gate1847.get("open_context_path"),
        "open_context_fd": gate1847.get("open_context_fd"),
        "pm_client_register_rc": gate1847.get("pm_client_register_rc"),
        "pm_client_connect_rc": gate1847.get("pm_client_connect_rc"),
        "callback_ack_label": gate1847.get("callback_ack_label"),
        "post_ack_label": gate1847.get("post_ack_label"),
        "service_notifier_label": gate1847.get("servnotif_label"),
        "lower_service69_progress": bool(gate1847.get("lower_service69_progress")),
        "lower_wlan0_present": bool(gate1847.get("lower_wlan0_present")),
        "lower_mhi_present": bool(gate1847.get("lower_mhi_present")),
        "v1803_manifest": rel(v1803_manifest),
        "v1803_decision": v1803.get("decision"),
        "v1803_pass": bool(v1803.get("pass")),
        "v1803_reason": v1803.get("reason"),
        "requested_wlanmdsp": details1803.get("requested_wlanmdsp", "0"),
        "wlfw_service69_seen": details1803.get("wlfw_service69_seen", "0"),
        "early_servnotif_state": details1803.get("early_listener_state") or details1803.get("early_listener_response_state"),
        "late_servnotif_state": details1803.get("late_listener_state") or details1803.get("late_listener_response_state"),
    }


def classify(android: dict[str, Any], native: dict[str, Any], source: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not android["requested_wlanmdsp"] or not android["requested_pd_image"]:
        return (
            "v1883-normal-android-wlanmdsp-request-missing",
            False,
            "normal Android-good evidence does not prove wlanmdsp/PD-image request",
            "android-normal-request-missing",
        )
    if android["pcie_or_mhi_before_wlan0_lines"] != 0:
        return (
            "v1883-normal-android-pcie-mhi-contaminated",
            False,
            "normal Android-good evidence has PCIe/MHI before wlan0, so it is not the internal-modem comparison target",
            "android-normal-contaminated",
        )
    if not native["v1847_pass"] or native["open_context_path"] != "/dev/subsys_modem":
        return (
            "v1883-native-subsys-modem-open-missing",
            False,
            "native PM-service evidence does not confirm /dev/subsys_modem open",
            "native-modem-open-missing",
        )
    if native["lower_service69_progress"] or native["lower_wlan0_present"]:
        return (
            "v1883-native-already-has-wlan-prereq",
            False,
            "native evidence already has WLFW service 69 or wlan0, so this re-anchor label is stale",
            "native-prereq-present",
        )
    if not source["pm_service_has_qmi_restart_strings"] or not source["pm_service_has_qmi_imports"]:
        return (
            "v1883-pm-service-qmi-source-incomplete",
            False,
            "pm-service source artifacts do not expose the QMI restart/request surface needed for host/source comparison",
            "pm-service-qmi-source-incomplete",
        )
    if not source["libperipheral_has_pm_register_connect"] or not source["libperipheral_has_binder_descriptor"]:
        return (
            "v1883-libperipheral-client-source-incomplete",
            False,
            "libperipheral_client source artifacts do not expose the Binder PM register/connect surface",
            "libperipheral-source-incomplete",
        )
    return (
        "v1883-internal-guest-pd-trigger-comparison-unrun-host-pass",
        True,
        "Normal Android-good reaches internal wlan_pd/wlanmdsp without PCIe/MHI, while native only opens /dev/subsys_modem and leaves wlan_pd uninit; the next unit is the read-only Android-vs-native per_mgr_vote/QMI/servreg/SSCTL trigger diff.",
        "internal-guest-pd-trigger-comparison-unrun",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android_normal"]
    native = result["native_pm"]
    source = result["source"]
    return "\n".join([
        "# Native Init V1883 Internal Guest-PD Trigger Source Re-anchor",
        "",
        "## Summary",
        "",
        "- Cycle: `V1883`",
        "- Type: host/source-only re-anchor from SDX50M/PCIe back to internal modem WLAN guest-PD trigger",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1883-internal-guest-pd-trigger-source-reanchor`",
        "",
        "## Android Normal Anchor",
        "",
        f"- Evidence: `{android['dir']}`",
        f"- requested wlanmdsp / PD image: `{android['requested_wlanmdsp']}` / `{android['requested_pd_image']}`",
        f"- wlfw_start / wlan_pd indication / wlan0 seconds: `{android['wlfw_start_time_s']}` / `{android['wlan_pd_indication_time_s']}` / `{android['wlan0_time_s']}`",
        f"- first wlanmdsp logcat time / lines: `{android['first_wlanmdsp_logcat_time']}` / `{android['wlanmdsp_logcat_lines']}`",
        f"- PCIe-or-MHI lines before wlan0: `{android['pcie_or_mhi_before_wlan0_lines']}`",
        "",
        "## Native PM-Service Anchor",
        "",
        f"- V1847 decision/pass: `{native['v1847_decision']}` / `{native['v1847_pass']}`",
        f"- PM client register/connect rc: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}`",
        f"- open context path/fd: `{native['open_context_path']}` / `{native['open_context_fd']}`",
        f"- callback/post-ack/service-notifier labels: `{native['callback_ack_label']}` / `{native['post_ack_label']}` / `{native['service_notifier_label']}`",
        f"- lower WLFW69/wlan0/MHI present: `{native['lower_service69_progress']}` / `{native['lower_wlan0_present']}` / `{native['lower_mhi_present']}`",
        f"- V1803 decision/pass: `{native['v1803_decision']}` / `{native['v1803_pass']}`",
        f"- V1803 requested wlanmdsp / WLFW69: `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}`",
        "",
        "## Source Surface",
        "",
        f"- pm-service QMI restart strings/imports: `{source['pm_service_has_qmi_restart_strings']}` / `{source['pm_service_has_qmi_imports']}`",
        f"- pm-service vote strings: `{source['pm_service_has_vote_strings']}`",
        f"- libperipheral_client PM register/Binder descriptor: `{source['libperipheral_has_pm_register_connect']}` / `{source['libperipheral_has_binder_descriptor']}`",
        f"- libperipheral_client QMI imports: `{source['libperipheral_has_qmi_imports']}`",
        f"- Source artifacts: `{json.dumps(source['artifacts'], sort_keys=True)}`",
        "",
        "## Selected Label",
        "",
        "- `internal-guest-pd-trigger-comparison-unrun`: the decisive comparison is not PCIe/GDSC. It is the read-only diff of Android per_mgr_vote to modem-side wlan_pd trigger versus native's post-vote path after `/dev/subsys_modem` opens.",
        "",
        "## Next",
        "",
        "- Run one read-only comparison that captures Android normal `per_mgr_vote` -> QMI/servreg/SSCTL -> `msm/modem/wlan_pd` -> `wlanmdsp.mbn`, and the equivalent native post-open absence.",
        "- Do not run GDSC/PMIC/GPIO/regulator writes, forced RC1/case, `/dev/subsys_esoc0`, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "V1883 is host/source-only. It reads existing artifacts and local binaries, writes local evidence/report files, and performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi operation, partition write, or hardware mutation.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_V1753_ANDROID)
    parser.add_argument("--v1847-manifest", type=Path, default=DEFAULT_V1847_MANIFEST)
    parser.add_argument("--v1803-manifest", type=Path, default=DEFAULT_V1803_MANIFEST)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--libperipheral-client", type=Path, default=DEFAULT_LIBPERIPHERAL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    android = android_normal_summary(args.android_dir)
    native = native_pm_summary(args.v1847_manifest, args.v1803_manifest)
    source = write_source_artifacts(store, args.pm_service, args.libperipheral_client)
    decision, pass_ok, reason, label = classify(android, native, source)
    result = {
        "cycle": "V1883",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "android_normal": android,
        "native_pm": native,
        "source": source,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }
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
