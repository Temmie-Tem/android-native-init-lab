#!/usr/bin/env python3
"""V1324 host-only provider response delta classifier.

V1323 placed the blocker inside the proprietary ext-mdm provider response path.
V1324 compares existing Android-positive and native-negative evidence to decide
whether the current record already proves a post-AP2MDM MDM2AP/PCIe response gap
or whether another read-only capture is needed before live work.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1324-provider-response-delta-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1324-provider-response-delta-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_CLASSIFIER_2026-05-31.md")
DEFAULT_V1323 = Path("tmp/wifi/v1323-provider-wait-cause-classifier/manifest.json")
DEFAULT_V1318 = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1318_OBSERVER = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/host/pm-server-wchan-tracefs-observer.txt")
DEFAULT_V1319 = Path("tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json")
DEFAULT_V1239 = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_V1240 = Path("tmp/wifi/v1240-sdx50m-response-surface-live/manifest.json")
DEFAULT_V1291 = Path("tmp/wifi/v1291-static-gpio-parity-classifier/manifest.json")
DEFAULT_V852 = Path("tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json")
DEFAULT_V896 = Path("tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_PM_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")

FORBIDDEN_FLAGS = (
    "pm_actor_executed",
    "mdm_helper_executed",
    "tracefs_write_executed",
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
    "pmic_write_executed",
    "gpio_line_request_executed",
    "direct_esoc_ioctl_executed",
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
    "flash_executed",
    "partition_write_executed",
)

INPUT_FORBIDDEN_FLAGS = (
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
    "flash_executed",
    "partition_write_executed",
    "pmic_write_executed",
    "gpio_line_request_executed",
    "direct_esoc_ioctl_executed",
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def float_value(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback


def input_forbidden_clear(manifest: dict[str, Any]) -> bool:
    return all(not bool_value(manifest.get(flag)) for flag in INPUT_FORBIDDEN_FLAGS)


def parse_interrupt_line_count(line: str) -> int:
    if not line:
        return 0
    before_controller = line.split("msmgpio-dc", 1)[0].split("PDC-GIC", 1)[0]
    numbers = re.findall(r"\b\d+\b", before_controller)
    if not numbers:
        return 0
    # First number is IRQ id; following numbers are per-CPU counts.
    return sum(int(value) for value in numbers[1:])


def find_first_line(text: str, pattern: str) -> str:
    for line in text.splitlines():
        if pattern in line:
            return line.strip()
    return ""


def summarize_v1323(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
    }


def summarize_v1318(manifest: dict[str, Any], observer_text: str) -> dict[str, Any]:
    cls = manifest.get("critical_line_classification") or {}
    response = manifest.get("response_sampler") or {}
    gpio_counts = cls.get("gpio_counts") or {}
    mdm_errfatal_line = find_first_line(observer_text, "mdm errfatal")
    mdm_status_line = find_first_line(observer_text, "mdm status")
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "gpio1270_line_count": int_value(cls.get("gpio1270_line_count")),
        "gpio135_high_count": int_value(cls.get("gpio135_high_count")),
        "gpio135_line_count": int_value(cls.get("gpio135_line_count")),
        "gpio141_line_count": int_value(gpio_counts.get("141")),
        "gpio142_line_count": int_value(cls.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float_value(cls.get("post_gpio135_sample_span_sec")),
        "target_keyword_line_count": int_value(cls.get("target_keyword_line_count")),
        "esoc_pil_notif_count": int_value(cls.get("esoc_pil_notif_count")),
        "max_pci_dev_count": int_value(response.get("max_pci_dev_count")),
        "max_mhi_bus_count": int_value(response.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "max_kmsg_pcie_count": int_value(response.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(response.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(response.get("max_kmsg_wlfw_count")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")),
        "mdm_errfatal_irq_line": mdm_errfatal_line,
        "mdm_errfatal_irq_count": parse_interrupt_line_count(mdm_errfatal_line),
        "mdm_status_irq_line": mdm_status_line,
        "mdm_status_irq_count": parse_interrupt_line_count(mdm_status_line),
    }


def summarize_v1319(manifest: dict[str, Any]) -> dict[str, Any]:
    native = manifest.get("native_v1318") or {}
    android = manifest.get("android_reference") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "native_gpio135_high_count": int_value(native.get("gpio135_high_count")),
        "native_gpio142_line_count": int_value(native.get("gpio142_line_count")),
        "native_mhi_pipe_seen": bool_value(native.get("mhi_pipe_seen")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("v1239_gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("v1239_pcie_rc1_lines")),
        "android_pcie_l0_lines": int_value(android.get("v1239_pcie_l0_lines")),
        "android_ks_mhi_pipe": bool_value(android.get("v896_ks_mhi_pipe")),
        "android_mdm3_online": bool_value(android.get("v896_mdm3_online")),
        "android_wlfw_present": bool_value(android.get("v1239_wlfw_present")),
        "android_bdf_present": bool_value(android.get("v1239_bdf_present")),
        "android_wlan0_present": bool_value(android.get("v1239_wlan0_present")),
    }


def summarize_v1239(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "native_pm_service_esoc0_attempt": bool_value(native.get("pm_service_actor_esoc0_attempt")),
        "native_mdm_subsys_powerup_lines": int_value(native.get("pm_service_binder_mdm_subsys_powerup_lines")),
        "native_wlfw_count": int_value(native.get("wlfw_count")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("pcie_rc1_lines")),
        "android_pcie_l0_lines": int_value(android.get("pcie_l0_lines")),
        "android_sysmon_esoc0_lines": int_value(android.get("sysmon_esoc0_lines")),
        "android_ks_mhi_pipe": bool_value(android.get("ks_mhi_pipe")),
        "android_wlfw_present": bool_value(android.get("wlfw_present")),
        "android_bdf_present": bool_value(android.get("bdf_present")),
        "android_wlan0_present": bool_value(android.get("wlan0_present")),
        "android_pcie_reset_time": android.get("pcie_reset_time"),
        "android_pcie_l0_time": android.get("pcie_l0_time"),
        "android_wlan0_time": android.get("wlan0_time"),
    }


def summarize_v1240(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    irq = analysis.get("mdm_status_irq") or {}
    pcie = analysis.get("pcie") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest)
        and not bool_value(manifest.get("gpio_sysfs_write_executed"))
        and not bool_value(manifest.get("raw_esoc_open_executed"))
        and not bool_value(manifest.get("raw_subsys_esoc0_open_executed")),
        "mdm3_state": str(analysis.get("mdm3_state", "")),
        "mdm_status_irq_present": bool_value(irq.get("present")),
        "mdm_status_irq_gpio142_hint": bool_value(irq.get("gpio142_hint")),
        "mdm_status_irq_count": int_value(irq.get("count_total")),
        "pcie_surface_present": bool_value(pcie.get("surface_present")),
        "dmesg_wlfw_count": int_value(analysis.get("dmesg_wlfw_count")),
        "dmesg_wlan0_count": int_value(analysis.get("dmesg_wlan0_count")),
        "dt_mdm3_present": bool_value(analysis.get("dt_mdm3_present")),
        "dt_ap2mdm_gpio_present": bool_value(analysis.get("dt_ap2mdm_gpio_present")),
        "dt_mdm2ap_gpio_present": bool_value(analysis.get("dt_mdm2ap_gpio_present")),
    }


def summarize_v1291(manifest: dict[str, Any]) -> dict[str, Any]:
    v1244 = manifest.get("v1244") or {}
    v1290 = manifest.get("v1290") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "gpio135_static_parity": bool_value(manifest.get("gpio135_static_parity")),
        "gpio142_static_parity": bool_value(manifest.get("gpio142_static_parity")),
        "native_gdsc_zero": bool_value(manifest.get("native_gdsc_zero")),
        "android_pcie_rc1_report_line": str(v1244.get("pcie_rc1_report_line", "")),
        "android_tlmm_gpio135_line": str(v1244.get("tlmm_gpio135_line", "")),
        "android_tlmm_gpio142_line": str(v1244.get("tlmm_gpio142_line", "")),
        "native_tlmm_gpio135_seen": bool_value(v1290.get("tlmm_gpio135_seen")),
        "native_tlmm_gpio142_seen": bool_value(v1290.get("tlmm_gpio142_seen")),
        "native_pcie0_gdsc_seen": bool_value(v1290.get("pcie0_gdsc_seen")),
        "native_pcie1_gdsc_seen": bool_value(v1290.get("pcie1_gdsc_seen")),
        "native_mhi_pipe_seen": bool_value(v1290.get("mhi_pipe_seen")),
        "native_wlan0_seen": bool_value(v1290.get("wlan0_seen")),
    }


def summarize_v852(manifest: dict[str, Any]) -> dict[str, Any]:
    comparison = (manifest.get("context") or {}).get("comparison") or {}
    v852 = comparison.get("v852") or {}
    return {
        "decision": manifest.get("decision", "") or v852.get("decision", ""),
        "pass": bool_value(manifest.get("pass")) or bool_value(v852.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest)
        and not bool_value(manifest.get("gpio_write_executed"))
        and not bool_value(manifest.get("provider_sysfs_write_executed"))
        and not bool_value(manifest.get("wlan_driver_state_write_executed")),
    }


def summarize_v896(manifest: dict[str, Any]) -> dict[str, Any]:
    classification = manifest.get("classification") or {}
    v852 = manifest.get("v852") or {}
    irq = v852.get("irq_mdm_status") or {}
    counts = v852.get("counts") or {}
    timeline = v852.get("timeline") or {}
    v853_flags = manifest.get("v853_actor_flags") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "android_positive_control": str(classification.get("android_positive_control", "")),
        "source_contract": str(classification.get("source_contract", "")),
        "v852_mdm3_state": str(v852.get("mdm3_state", "")),
        "v852_gpio142_irq_count": int_value(irq.get("count_total")),
        "v852_gpio142_irq_present": bool_value(irq.get("present")),
        "v852_counts_pcie": int_value(counts.get("pcie")),
        "v852_counts_mhi": int_value(counts.get("mhi")),
        "v852_counts_wlfw": int_value(counts.get("wlfw")),
        "v852_counts_bdf": int_value(counts.get("bdf")),
        "v852_counts_wlan0": int_value(counts.get("wlan0")),
        "v852_pcie_l0_present": bool_value((timeline.get("pcie_link_l0") or {}).get("present")),
        "v852_pcie_l0_time": (timeline.get("pcie_link_l0") or {}).get("time"),
        "v852_wlan0_present": bool_value((timeline.get("wlan0") or {}).get("present")),
        "v852_symbols_mhi_hook": bool_value((v852.get("symbols") or {}).get("mhi_arch_esoc_ops_power_on")),
        "v853_has_ks_mhi_pipe": bool_value(v853_flags.get("has_ks_mhi_pipe")),
        "v853_has_mdm_helper_esoc_fd": bool_value(v853_flags.get("has_mdm_helper_esoc_fd")),
        "v853_has_per_mgr_subsys_esoc0_fd": bool_value(v853_flags.get("has_per_mgr_subsys_esoc0_fd")),
    }


def summarize_texts(mdm3_text: str, pm_text: str) -> dict[str, Any]:
    return {
        "mdm3_maps_ap2mdm_status_gpio135": "GPIO 135" in mdm3_text and "AP2MDM" in mdm3_text,
        "mdm3_maps_mdm2ap_status_gpio142": "GPIO 142" in mdm3_text and "MDM2AP" in mdm3_text,
        "mdm3_maps_ap2mdm_errfatal_gpio141": "GPIO 141" in mdm3_text and "AP → MDM error fatal" in mdm3_text,
        "mdm3_maps_mdm2ap_errfatal_gpio53": "GPIO 53" in mdm3_text and "MDM → AP error fatal" in mdm3_text,
        "pm_notes_mdm2ap_gpio142_online": "MDM2AP_STATUS GPIO 142" in pm_text and "mdm3 ONLINE" in pm_text,
        "pm_notes_subsys_to_powerup": "/dev/subsys_esoc0" in pm_text and "mdm_subsys_powerup" in pm_text,
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1323 = summarize_v1323(load_json(args.v1323_manifest))
    v1318 = summarize_v1318(load_json(args.v1318_manifest), read_text(args.v1318_observer))
    v1319 = summarize_v1319(load_json(args.v1319_manifest))
    v1239 = summarize_v1239(load_json(args.v1239_manifest))
    v1240 = summarize_v1240(load_json(args.v1240_manifest))
    v1291 = summarize_v1291(load_json(args.v1291_manifest))
    v852 = summarize_v852(load_json(args.v852_manifest))
    v896 = summarize_v896(load_json(args.v896_manifest))
    texts = summarize_texts(read_text(args.mdm3_research), read_text(args.pm_research))

    v1323_ready = (
        v1323["pass"]
        and v1323["decision"] == "v1323-provider-wait-cause-is-proprietary-powerup-response"
        and v1323["forbidden_clear"]
    )
    native_trigger_reaches_ap_side = (
        v1318["pass"]
        and v1318["decision"] == "v1318-target-critical-lines-captured"
        and v1318["target_keyword_line_count"] >= 1
        and v1318["esoc_pil_notif_count"] >= 1
        and v1318["gpio1270_line_count"] > 0
        and v1318["gpio135_high_count"] >= 1
        and v1318["post_gpio135_sample_span_sec"] >= 10.0
    )
    native_mdm_side_silent = (
        v1318["gpio142_line_count"] == 0
        and v1318["mdm_status_irq_count"] == 0
        and v1318["max_pci_dev_count"] == 0
        and v1318["max_mhi_bus_count"] == 0
        and not v1318["mhi_pipe_seen"]
        and v1318["max_kmsg_pcie_count"] == 0
        and v1318["max_kmsg_mhi_count"] == 0
        and v1318["max_kmsg_wlfw_count"] == 0
        and not v1318["wlan0_seen"]
        and v1240["mdm_status_irq_count"] == 0
        and v1240["dmesg_wlfw_count"] == 0
        and v1240["dmesg_wlan0_count"] == 0
    )
    android_downstream_response_present = (
        v852["pass"]
        and v896["pass"]
        and v1239["pass"]
        and v1239["android_gpio142_irq_count"] > 0
        and v1239["android_pcie_rc1_lines"] > 0
        and v1239["android_pcie_l0_lines"] > 0
        and v1239["android_ks_mhi_pipe"]
        and v1239["android_wlfw_present"]
        and v1239["android_bdf_present"]
        and v1239["android_wlan0_present"]
        and v896["v853_has_ks_mhi_pipe"]
        and v896["v852_gpio142_irq_count"] > 0
        and v896["v852_counts_pcie"] > 0
        and v896["v852_counts_wlan0"] > 0
    )
    errfatal_branch_classified = (
        texts["mdm3_maps_ap2mdm_errfatal_gpio141"]
        and texts["mdm3_maps_mdm2ap_errfatal_gpio53"]
        and v1318["gpio141_line_count"] > 0
        and v1318["mdm_errfatal_irq_line"] != ""
        and v1318["mdm_errfatal_irq_count"] == 0
    )
    static_shape_not_primary = (
        v1291["pass"]
        and v1291["gpio135_static_parity"]
        and v1291["gpio142_static_parity"]
        and v1291["native_tlmm_gpio135_seen"]
        and v1291["native_tlmm_gpio142_seen"]
        and v1291["native_gdsc_zero"]
        and not v1291["native_mhi_pipe_seen"]
        and not v1291["native_wlan0_seen"]
    )
    contract_mapped = (
        texts["mdm3_maps_ap2mdm_status_gpio135"]
        and texts["mdm3_maps_mdm2ap_status_gpio142"]
        and texts["pm_notes_mdm2ap_gpio142_online"]
        and texts["pm_notes_subsys_to_powerup"]
        and v1240["dt_mdm3_present"]
        and v1240["dt_ap2mdm_gpio_present"]
        and v1240["dt_mdm2ap_gpio_present"]
        and v1240["mdm_status_irq_present"]
        and v1240["mdm_status_irq_gpio142_hint"]
    )
    guardrails_clear = all(item["forbidden_clear"] for item in (v1323, v1318, v1319, v1239, v1240, v1291, v852, v896))

    checks = [
        check("v1323-branch-ready", v1323_ready, f"decision={v1323['decision']}"),
        check("native-trigger-reaches-ap-side", native_trigger_reaches_ap_side, f"gpio1270={v1318['gpio1270_line_count']} gpio135_high={v1318['gpio135_high_count']} span={v1318['post_gpio135_sample_span_sec']} pil={v1318['esoc_pil_notif_count']}"),
        check("native-mdm-side-silent", native_mdm_side_silent, f"gpio142_lines={v1318['gpio142_line_count']} irq={v1318['mdm_status_irq_count']} pci={v1318['max_pci_dev_count']} mhi={v1318['max_mhi_bus_count']} wlan0={v1318['wlan0_seen']}"),
        check("android-downstream-response-present", android_downstream_response_present, f"gpio142={v1239['android_gpio142_irq_count']} pcie_rc1={v1239['android_pcie_rc1_lines']} ks_mhi={v1239['android_ks_mhi_pipe']} wlan0={v1239['android_wlan0_present']}"),
        check("errfatal-branch-classified", errfatal_branch_classified, f"gpio141_lines={v1318['gpio141_line_count']} mdm_errfatal_irq={v1318['mdm_errfatal_irq_count']} mapped141={texts['mdm3_maps_ap2mdm_errfatal_gpio141']} mapped53={texts['mdm3_maps_mdm2ap_errfatal_gpio53']}"),
        check("static-shape-not-primary", static_shape_not_primary, f"gpio135_parity={v1291['gpio135_static_parity']} gpio142_parity={v1291['gpio142_static_parity']} native_gdsc_zero={v1291['native_gdsc_zero']}"),
        check("provider-contract-mapped", contract_mapped, f"gpio135_map={texts['mdm3_maps_ap2mdm_status_gpio135']} gpio142_map={texts['mdm3_maps_mdm2ap_status_gpio142']} irq_present={v1240['mdm_status_irq_present']}"),
        check("guardrails-clear", guardrails_clear, "host/source-only classifier; no Wi-Fi HAL/connect/credentials/network/flash/PMIC/GPIO/direct-eSoC/GDSC mutation in reconciled inputs"),
    ]

    passed = all(row["pass"] for row in checks)
    if passed:
        decision = "v1324-delta-is-post-ap2mdm-mdm2ap-response-gap"
        reason = (
            "Existing evidence proves native reaches AP-side soft-reset/AP2MDM activity, including GPIO1270/GPIO135 and GPIO141 errfatal-side activity, "
            "but MDM2AP/GPIO142, PCIe RC1/MHI, WLFW/BDF, and wlan0 remain absent while Android receives them"
        )
        next_step = (
            "V1325 should design the next small gate around a bounded read-only or reboot-bounded sampler focused on GPIO142/MDM errfatal/PCIe timing, "
            "or an Android read-only timing recapture if exact Android phase order is required; keep Wi-Fi HAL/connect and all PMIC/GPIO/GDSC/eSoC writes blocked"
        )
    elif v1323_ready and native_trigger_reaches_ap_side and not android_downstream_response_present:
        decision = "v1324-delta-needs-android-provider-timing-recapture"
        reason = "native AP-side trigger evidence is present, but Android downstream timing evidence is incomplete"
        next_step = "perform Android read-only positive-control recapture before native live work"
    elif v1323_ready and android_downstream_response_present and not native_trigger_reaches_ap_side:
        decision = "v1324-delta-needs-native-focused-sampler"
        reason = "Android downstream evidence is present, but native AP-side trigger evidence is incomplete"
        next_step = "design a bounded read-only native sampler for the missing native surface"
    else:
        decision = "v1324-evidence-incomplete"
        reason = "required provider response delta inputs are missing or inconsistent"
        next_step = "refresh the failed host/source evidence before any live gate"

    return {
        "cycle": "v1324",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1323_manifest": str(repo_path(args.v1323_manifest)),
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1318_observer": str(repo_path(args.v1318_observer)),
            "v1319_manifest": str(repo_path(args.v1319_manifest)),
            "v1239_manifest": str(repo_path(args.v1239_manifest)),
            "v1240_manifest": str(repo_path(args.v1240_manifest)),
            "v1291_manifest": str(repo_path(args.v1291_manifest)),
            "v852_manifest": str(repo_path(args.v852_manifest)),
            "v896_manifest": str(repo_path(args.v896_manifest)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "pm_research": str(repo_path(args.pm_research)),
        },
        "v1323": v1323,
        "v1318": v1318,
        "v1319": v1319,
        "v1239": v1239,
        "v1240": v1240,
        "v1291": v1291,
        "v852": v852,
        "v896": v896,
        "text_evidence": texts,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "tracefs_write_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["pass"], row["detail"]] for row in manifest["checks"]]
    v1318 = manifest["v1318"]
    v1239 = manifest["v1239"]
    v896 = manifest["v896"]
    safety_rows = [[key, manifest.get(key)] for key in (
        "device_commands_executed",
        "device_mutations",
        "pm_actor_executed",
        "mdm_helper_executed",
        "tracefs_write_executed",
        "live_esoc_ioctl_executed",
        "live_esoc_notify_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
        "gdsc_write_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    return "\n".join([
        "# V1324 Provider Response Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], rows),
        "",
        "## Delta Summary",
        "",
        markdown_table(["surface", "native", "Android / interpretation"], [
            ["AP-side trigger", f"GPIO1270={v1318['gpio1270_line_count']} GPIO135_high={v1318['gpio135_high_count']} GPIO141={v1318['gpio141_line_count']}", "native reaches AP-side provider activity"],
            ["MDM2AP status", f"GPIO142_lines={v1318['gpio142_line_count']} irq={v1318['mdm_status_irq_count']}", f"Android GPIO142 IRQ={v1239['android_gpio142_irq_count']}"],
            ["PCIe/MHI/WLFW", f"PCI={v1318['max_pci_dev_count']} MHI={v1318['max_mhi_bus_count']} WLFW={v1318['max_kmsg_wlfw_count']}", f"Android PCIe RC1={v1239['android_pcie_rc1_lines']} ks_mhi={v896['v853_has_ks_mhi_pipe']}"],
            ["Wi-Fi netdev", f"wlan0={v1318['wlan0_seen']}", f"Android wlan0={v1239['android_wlan0_present']}"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1324 Provider Response Delta Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1324`",
        "- Type: host/source-only provider response delta classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1324-provider-response-delta-classifier/manifest.json`",
        "  - `tmp/wifi/v1324-provider-response-delta-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py`",
        "",
        "V1324 compares existing native-negative and Android-positive evidence after",
        "V1323. Native reaches the proprietary ext-mdm provider path and AP-side",
        "activity: PMIC soft-reset GPIO1270, GPIO135/AP2MDM high, and GPIO141",
        "AP2MDM_ERRFATAL-side activity. The same record keeps GPIO142/MDM2AP, the",
        "MDM errfatal IRQ, PCIe RC1, MHI/ks, WLFW/BDF, and `wlan0` absent. Android",
        "positive-control evidence reaches GPIO142 IRQ, PCIe RC1/L0, MHI/ks, WLFW/BDF,",
        "and `wlan0`.",
        "",
        "## Decision",
        "",
        "Existing evidence is sufficient to classify the current delta as a",
        "post-AP2MDM MDM2AP/PCIe response gap. The next useful unit is not Wi-Fi HAL,",
        "scan/connect, credentials, DHCP, or external ping. It should be a small",
        "observer/recapture design for GPIO142, MDM errfatal, and PCIe timing, with",
        "any native live sampler kept read-only or explicitly reboot-bounded.",
        "",
        "## Safety",
        "",
        "Host/source-only classifier. No device command, helper deploy, PM actor start,",
        "`mdm_helper` start, tracefs write, live eSoC ioctl/notify, PMIC write, GPIO",
        "line request, direct GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credential",
        "use, DHCP/routes, external ping, flash, boot image write, or partition write",
        "occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"native_gpio135_high: {manifest['v1318']['gpio135_high_count']}")
    print(f"native_gpio142_irq:  {manifest['v1318']['mdm_status_irq_count']}")
    print(f"android_gpio142_irq: {manifest['v1239']['android_gpio142_irq_count']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1323-manifest", type=Path, default=DEFAULT_V1323)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318)
    parser.add_argument("--v1318-observer", type=Path, default=DEFAULT_V1318_OBSERVER)
    parser.add_argument("--v1319-manifest", type=Path, default=DEFAULT_V1319)
    parser.add_argument("--v1239-manifest", type=Path, default=DEFAULT_V1239)
    parser.add_argument("--v1240-manifest", type=Path, default=DEFAULT_V1240)
    parser.add_argument("--v1291-manifest", type=Path, default=DEFAULT_V1291)
    parser.add_argument("--v852-manifest", type=Path, default=DEFAULT_V852)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--pm-research", type=Path, default=DEFAULT_PM_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1324-provider-response-delta-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1324 host/source-only classifier against existing response-delta evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
