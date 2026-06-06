#!/usr/bin/env python3
"""V1322 host-only SDX50M response-input classifier.

V1321 moved the blocker below the image-link / PM userspace actor path.  V1322
reconciles the existing response-surface, GPIO, GDSC, and tracefs evidence to
classify which response inputs are already observed and what remains before
Wi-Fi HAL/connect can be justified.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1322-sdx50m-response-input-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1322-sdx50m-response-input-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1322_SDX50M_RESPONSE_INPUT_CLASSIFIER_2026-05-31.md")
DEFAULT_V1321 = Path("tmp/wifi/v1321-image-link-reconciliation-classifier/manifest.json")
DEFAULT_V1240 = Path("tmp/wifi/v1240-sdx50m-response-surface-live/manifest.json")
DEFAULT_V1287 = Path("tmp/wifi/v1287-v1286-sdx50m-power-gap-classifier/manifest.json")
DEFAULT_V1291 = Path("tmp/wifi/v1291-static-gpio-parity-classifier/manifest.json")
DEFAULT_V1314 = Path("tmp/wifi/v1314-dynamic-gdsc-esoc-prereq-classifier/manifest.json")
DEFAULT_V1318 = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1319 = Path("tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json")

FORBIDDEN_FLAGS = (
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


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
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


def all_forbidden_clear(manifest: dict[str, Any]) -> bool:
    return all(not bool_value(manifest.get(flag)) for flag in FORBIDDEN_FLAGS)


def summarize_v1321(manifest: dict[str, Any]) -> dict[str, Any]:
    v1238 = manifest.get("v1238") or {}
    v1239 = manifest.get("v1239") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "late_per_proxy_started": bool_value(v1238.get("late_per_proxy_started")),
        "pm_service_esoc0": bool_value(v1238.get("pm_service_actor_esoc0_attempt")) or bool_value(v1239.get("native_pm_service_esoc0_attempt")),
        "mdm_subsys_powerup": bool_value(v1238.get("mdm_subsys_powerup")) or int_value(v1239.get("native_mdm_subsys_powerup_lines")) > 0,
        "native_powerup_lines": int_value(v1239.get("native_mdm_subsys_powerup_lines")),
        "android_gpio142": int_value(v1239.get("android_gpio142_irq_count")),
        "android_pcie_rc1": int_value(v1239.get("android_pcie_rc1_lines")),
    }


def summarize_v1240(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    irq = analysis.get("mdm_status_irq") or {}
    pcie = analysis.get("pcie") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest)
        and not bool_value(manifest.get("raw_esoc_open_executed"))
        and not bool_value(manifest.get("raw_subsys_esoc0_open_executed"))
        and not bool_value(manifest.get("gpio_sysfs_write_executed")),
        "esoc_name": str(analysis.get("esoc_name", "")),
        "esoc_link": str(analysis.get("esoc_link", "")),
        "esoc_link_info": str(analysis.get("esoc_link_info", "")),
        "mdm3_state": str(analysis.get("mdm3_state", "")),
        "irq_present": bool_value(irq.get("present")),
        "irq_gpio142_hint": bool_value(irq.get("gpio142_hint")),
        "irq_count": int_value(irq.get("count_total")),
        "pcie_surface_present": bool_value(pcie.get("surface_present")),
        "regulator_focus_count": int_value(analysis.get("regulator_focus_count")),
        "dt_mdm3_present": bool_value(analysis.get("dt_mdm3_present")),
        "dt_ap2mdm_gpio_present": bool_value(analysis.get("dt_ap2mdm_gpio_present")),
        "dt_mdm2ap_gpio_present": bool_value(analysis.get("dt_mdm2ap_gpio_present")),
        "dmesg_wlfw_count": int_value(analysis.get("dmesg_wlfw_count")),
        "dmesg_wlan0_count": int_value(analysis.get("dmesg_wlan0_count")),
    }


def summarize_v1287(manifest: dict[str, Any]) -> dict[str, Any]:
    v1286 = manifest.get("v1286") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "pm_service_esoc0": bool_value(v1286.get("pm_service_actor_esoc0_attempt")),
        "native_gdsc_zero": bool_value(manifest.get("native_gdsc_zero")),
        "pcie0_line": str(v1286.get("first_pcie0_gdsc_line", "")),
        "pcie1_line": str(v1286.get("first_pcie1_gdsc_line", "")),
        "gpio142_count": int_value(v1286.get("max_mdm_status_count_total")),
        "mhi_bus_count": int_value(v1286.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool_value(v1286.get("mhi_pipe_seen")),
        "kmsg_pcie_count": int_value(v1286.get("max_kmsg_pcie_count")),
        "kmsg_mhi_count": int_value(v1286.get("max_kmsg_mhi_count")),
        "kmsg_wlfw_count": int_value(v1286.get("max_kmsg_wlfw_count")),
        "wlan0_seen": bool_value(v1286.get("wlan0_seen")),
    }


def summarize_v1291(manifest: dict[str, Any]) -> dict[str, Any]:
    v1290 = manifest.get("v1290") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "gpio135_static_parity": bool_value(manifest.get("gpio135_static_parity")),
        "gpio142_static_parity": bool_value(manifest.get("gpio142_static_parity")),
        "native_gdsc_zero": bool_value(manifest.get("native_gdsc_zero")),
        "tlmm_gpio135_seen": bool_value(v1290.get("tlmm_gpio135_seen")),
        "tlmm_gpio142_seen": bool_value(v1290.get("tlmm_gpio142_seen")),
        "pcie0_gdsc_seen": bool_value(v1290.get("pcie0_gdsc_seen")),
        "pcie1_gdsc_seen": bool_value(v1290.get("pcie1_gdsc_seen")),
        "mhi_pipe_seen": bool_value(v1290.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(v1290.get("wlan0_seen")),
    }


def summarize_v1314(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    contract = analysis.get("contract") or {}
    v1313 = analysis.get("v1313") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "mdm_subsys_powerup_seen": bool_value(v1313.get("mdm_subsys_powerup_seen")) or "mdm_subsys_powerup" in str(v1313),
        "pcie0_gdsc_zero": bool_value(v1313.get("pcie0_gdsc_zero_seen")),
        "pcie1_gdsc_zero": bool_value(v1313.get("pcie1_gdsc_zero_seen")),
        "mhi_pipe_seen": bool_value(v1313.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(v1313.get("wlan0_seen")),
        "first_power_on_asserts_ap2mdm": bool_value(contract.get("first_power_on_asserts_ap2mdm")),
        "first_power_on_deasserts_soft_reset": bool_value(contract.get("first_power_on_deasserts_soft_reset")),
        "mhi_hook_after_esoc_powerup": bool_value(contract.get("mhi_hook_after_esoc_powerup")),
        "userspace_gpio_rejected": bool_value(contract.get("userspace_gpio_rejected")),
    }


def summarize_v1318(manifest: dict[str, Any]) -> dict[str, Any]:
    cls = manifest.get("critical_line_classification") or {}
    events = cls.get("event_counts") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    response = manifest.get("response_sampler") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "critical_line_count": int_value(cls.get("critical_line_count")),
        "gpio135_high_count": int_value(cls.get("gpio135_high_count")),
        "gpio142_line_count": int_value(cls.get("gpio142_line_count")),
        "gpio1270_line_count": int_value(cls.get("gpio1270_line_count")),
        "esoc_pil_notif_count": int_value(cls.get("esoc_pil_notif_count")),
        "post_gpio135_sample_span_sec": float_value(cls.get("post_gpio135_sample_span_sec")),
        "regulator_event_count": int_value(events.get("regulator_enable")) + int_value(events.get("regulator_set_voltage")),
        "gpio_event_count": int_value(events.get("gpio_direction")) + int_value(events.get("gpio_value")),
        "pm_service_esoc0": bool_value(parity.get("pm_service_subsys_esoc0_attempt")),
        "mhi_bus_count": int_value(response.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "kmsg_pcie_count": int_value(response.get("max_kmsg_pcie_count")),
        "kmsg_mhi_count": int_value(response.get("max_kmsg_mhi_count")),
        "kmsg_wlfw_count": int_value(response.get("max_kmsg_wlfw_count")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")),
    }


def summarize_v1319(manifest: dict[str, Any]) -> dict[str, Any]:
    native = manifest.get("native_v1318") or {}
    android = manifest.get("android_reference") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_forbidden_clear(manifest),
        "gpio135_high_count": int_value(native.get("gpio135_high_count")),
        "gpio142_line_count": int_value(native.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float_value(native.get("post_gpio135_sample_span_sec")),
        "native_mhi_pipe_seen": bool_value(native.get("mhi_pipe_seen")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("v1239_gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("v1239_pcie_rc1_lines")),
        "android_wlan0_present": bool_value(android.get("v1239_wlan0_present")),
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1321 = summarize_v1321(load_json(args.v1321_manifest))
    v1240 = summarize_v1240(load_json(args.v1240_manifest))
    v1287 = summarize_v1287(load_json(args.v1287_manifest))
    v1291 = summarize_v1291(load_json(args.v1291_manifest))
    v1314 = summarize_v1314(load_json(args.v1314_manifest))
    v1318 = summarize_v1318(load_json(args.v1318_manifest))
    v1319 = summarize_v1319(load_json(args.v1319_manifest))

    image_link_closed = (
        v1321["pass"]
        and v1321["decision"] == "v1321-image-link-gate-covered-next-sdx50m-response-inputs"
        and v1321["late_per_proxy_started"]
        and v1321["pm_service_esoc0"]
        and v1321["mdm_subsys_powerup"]
    )
    readonly_surfaces_visible = (
        v1240["pass"]
        and v1240["decision"] == "v1240-response-inputs-visible-mdm2ap-silent"
        and v1240["esoc_name"] == "SDX50M"
        and v1240["esoc_link"] == "PCIe"
        and v1240["irq_present"]
        and v1240["irq_gpio142_hint"]
        and v1240["irq_count"] == 0
        and v1240["pcie_surface_present"]
        and v1240["regulator_focus_count"] > 0
    )
    static_gpio_pmic_demoted = (
        v1287["pass"]
        and v1291["pass"]
        and v1287["native_gdsc_zero"]
        and v1291["gpio135_static_parity"]
        and v1291["gpio142_static_parity"]
        and v1291["tlmm_gpio135_seen"]
        and v1291["tlmm_gpio142_seen"]
    )
    dynamic_gdsc_mhi_absent = (
        v1287["pm_service_esoc0"]
        and v1287["gpio142_count"] == 0
        and v1287["mhi_bus_count"] == 0
        and not v1287["mhi_pipe_seen"]
        and v1287["kmsg_pcie_count"] == 0
        and v1287["kmsg_mhi_count"] == 0
        and v1287["kmsg_wlfw_count"] == 0
        and not v1287["wlan0_seen"]
        and v1314["pcie0_gdsc_zero"]
        and v1314["pcie1_gdsc_zero"]
        and not v1314["mhi_pipe_seen"]
    )
    first_power_on_trace_reached_gpio135 = (
        v1318["pass"]
        and v1318["decision"] == "v1318-target-critical-lines-captured"
        and v1318["pm_service_esoc0"]
        and v1318["critical_line_count"] > 0
        and v1318["regulator_event_count"] > 0
        and v1318["gpio_event_count"] > 0
        and v1318["esoc_pil_notif_count"] > 0
        and v1318["gpio1270_line_count"] > 0
        and v1318["gpio135_high_count"] >= 1
        and v1318["gpio142_line_count"] == 0
    )
    post_gpio135_response_absent = (
        v1319["pass"]
        and v1319["decision"] == "v1319-gpio135-asserted-mdm2ap-pcie-response-absent"
        and v1319["gpio135_high_count"] >= 1
        and v1319["gpio142_line_count"] == 0
        and v1319["post_gpio135_sample_span_sec"] >= 10.0
        and not v1319["native_mhi_pipe_seen"]
        and not v1319["native_wlan0_seen"]
        and v1319["android_gpio142_irq_count"] > 0
        and v1319["android_pcie_rc1_lines"] > 0
        and v1319["android_wlan0_present"]
    )
    contract_rejects_direct_mutations = (
        v1314["first_power_on_asserts_ap2mdm"]
        and v1314["first_power_on_deasserts_soft_reset"]
        and v1314["mhi_hook_after_esoc_powerup"]
        and v1314["userspace_gpio_rejected"]
    )
    guardrails_clear = all(item["forbidden_clear"] for item in (v1321, v1240, v1287, v1291, v1314, v1318, v1319))

    checks = [
        check("image-link-gate-closed", image_link_closed, f"v1321={v1321['decision']} late_per_proxy={v1321['late_per_proxy_started']} powerup={v1321['mdm_subsys_powerup']}"),
        check("readonly-response-surfaces-visible", readonly_surfaces_visible, f"esoc={v1240['esoc_name']} link={v1240['esoc_link']} irq={v1240['irq_present']} count={v1240['irq_count']} regulators={v1240['regulator_focus_count']}"),
        check("static-gpio-pmic-demoted", static_gpio_pmic_demoted, f"gpio135_parity={v1291['gpio135_static_parity']} gpio142_parity={v1291['gpio142_static_parity']} gdsc_zero={v1287['native_gdsc_zero']}"),
        check("dynamic-gdsc-mhi-absent", dynamic_gdsc_mhi_absent, f"gdsc0_zero={v1314['pcie0_gdsc_zero']} gdsc1_zero={v1314['pcie1_gdsc_zero']} gpio142={v1287['gpio142_count']} mhi={v1287['mhi_bus_count']}"),
        check("first-power-on-trace-reached-gpio135", first_power_on_trace_reached_gpio135, f"critical={v1318['critical_line_count']} reg_events={v1318['regulator_event_count']} gpio135={v1318['gpio135_high_count']} gpio142={v1318['gpio142_line_count']}"),
        check("post-gpio135-response-absent", post_gpio135_response_absent, f"span={v1319['post_gpio135_sample_span_sec']} native_mhi={v1319['native_mhi_pipe_seen']} android_gpio142={v1319['android_gpio142_irq_count']}"),
        check("direct-mutations-rejected-by-contract", contract_rejects_direct_mutations, f"ap2mdm={v1314['first_power_on_asserts_ap2mdm']} soft_reset={v1314['first_power_on_deasserts_soft_reset']} userspace_gpio_rejected={v1314['userspace_gpio_rejected']}"),
        check("guardrails-clear", guardrails_clear, "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, partition write, PMIC write, GPIO line request, or direct eSoC ioctl in reconciled inputs"),
    ]

    passed = all(row["pass"] for row in checks)
    if passed:
        decision = "v1322-response-inputs-classified-next-provider-wait-cause"
        reason = (
            "SDX50M response inputs are now classified: metadata/IRQ/PCIe/regulator surfaces are visible, "
            "static PMIC/TLMM shape is demoted, first-power-on reaches GPIO135, but GPIO142/PCIe/MHI/WLFW never respond"
        )
        next_step = (
            "V1323 should classify the proprietary provider wait cause around mdm_subsys_powerup/GPIO142/err_ready: "
            "host/source first, then only a bounded read-only or reboot-bounded live gate; do not repeat image-link, "
            "start Wi-Fi HAL/connect, or issue direct PMIC/GPIO/GDSC/eSoC writes"
        )
    else:
        decision = "v1322-response-input-evidence-incomplete"
        reason = "required response-input evidence is missing or inconsistent"
        next_step = "refresh the failed evidence source before another live gate"

    return {
        "cycle": "v1322",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1321_manifest": str(repo_path(args.v1321_manifest)),
            "v1240_manifest": str(repo_path(args.v1240_manifest)),
            "v1287_manifest": str(repo_path(args.v1287_manifest)),
            "v1291_manifest": str(repo_path(args.v1291_manifest)),
            "v1314_manifest": str(repo_path(args.v1314_manifest)),
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1319_manifest": str(repo_path(args.v1319_manifest)),
        },
        "v1321": v1321,
        "v1240": v1240,
        "v1287": v1287,
        "v1291": v1291,
        "v1314": v1314,
        "v1318": v1318,
        "v1319": v1319,
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
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    v1240 = manifest["v1240"]
    v1318 = manifest["v1318"]
    v1319 = manifest["v1319"]
    return "\n".join([
        "# V1322 SDX50M Response-input Classifier",
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
        "## Response Surface",
        "",
        markdown_table(["surface", "native", "reference / interpretation"], [
            ["SDX50M metadata", f"{v1240['esoc_name']} {v1240['esoc_link']} {v1240['esoc_link_info']}", "surface visible"],
            ["GPIO142 IRQ", f"present={v1240['irq_present']} count={v1240['irq_count']}", f"Android count={v1319['android_gpio142_irq_count']}"],
            ["GPIO135 -> response", f"gpio135_high={v1318['gpio135_high_count']} gpio142_lines={v1318['gpio142_line_count']}", f"post_span={v1319['post_gpio135_sample_span_sec']}s"],
            ["PCIe/MHI/WLFW", f"pcie_kmsg={v1318['kmsg_pcie_count']} mhi={v1318['mhi_bus_count']} wlfw={v1318['kmsg_wlfw_count']}", f"Android PCIe RC1 lines={v1319['android_pcie_rc1_lines']}"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1322 SDX50M Response-input Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1322`",
        "- Type: host-only response-input classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1322-sdx50m-response-input-classifier/manifest.json`",
        "  - `tmp/wifi/v1322-sdx50m-response-input-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_sdx50m_response_input_classifier_v1322.py`",
        "",
        "V1322 consolidates the response-input branch after V1321. The native path",
        "already reaches the PM userspace actor and `mdm_subsys_powerup`. Read-only",
        "surfaces for SDX50M metadata, GPIO142 IRQ, PCIe, regulators, GDSC, TLMM,",
        "and tracefs events are available or have been sampled. Static PMIC/TLMM",
        "shape is not the shortest blocker anymore, and V1318 proves GPIO135 high is",
        "visible in the first-power-on trace. The remaining blocker is the provider",
        "wait/response cause: no GPIO142 IRQ, PCIe RC1/MHI, WLFW/BDF, or `wlan0`",
        "follows native GPIO135 / `mdm_subsys_powerup`.",
        "",
        "## Decision",
        "",
        "Do not repeat image-link, PM actor delivery, static GPIO parity, or broad",
        "read-only response-surface gates. V1323 should classify the provider wait",
        "cause around `mdm_subsys_powerup`, GPIO142/MDM2AP, and `err_ready`: source",
        "and host-only first, then only a bounded read-only or reboot-bounded live",
        "gate if needed. Direct PMIC/GPIO/GDSC/eSoC writes and Wi-Fi HAL/connect",
        "remain blocked.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, PM actor start, `mdm_helper` start,",
        "tracefs write, live eSoC ioctl/notify, PMIC write, GPIO line request, direct",
        "GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes,",
        "external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"gpio135_high: {manifest['v1318']['gpio135_high_count']}")
    print(f"gpio142_irq_count: {manifest['v1240']['irq_count']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1321-manifest", type=Path, default=DEFAULT_V1321)
    parser.add_argument("--v1240-manifest", type=Path, default=DEFAULT_V1240)
    parser.add_argument("--v1287-manifest", type=Path, default=DEFAULT_V1287)
    parser.add_argument("--v1291-manifest", type=Path, default=DEFAULT_V1291)
    parser.add_argument("--v1314-manifest", type=Path, default=DEFAULT_V1314)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318)
    parser.add_argument("--v1319-manifest", type=Path, default=DEFAULT_V1319)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1322-sdx50m-response-input-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1322 host-only classifier against existing response-input evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
