#!/usr/bin/env python3
"""V1346 host-only Android-only SDX50M response prerequisite reclassifier.

Reconciles the current V1345 no-response route against the Android-positive
and native-negative evidence that led to the provider/SDX50M route. This script
does not execute device commands or broaden into Wi-Fi bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1346-android-only-response-prereq-reclassifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1346-android-only-response-prereq-reclassifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1346_ANDROID_ONLY_RESPONSE_PREREQ_RECLASSIFIER_2026-06-01.md")

DEFAULT_V1329 = Path("tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/manifest.json")
DEFAULT_V1331 = Path("tmp/wifi/v1331-android-sdx50m-timing-handoff/manifest.json")
DEFAULT_V1332 = Path("tmp/wifi/v1332-wlfw-before-esoc-classifier/manifest.json")
DEFAULT_V1335 = Path("tmp/wifi/v1335-early-cnss-wlfw-parity-observer-live/manifest.json")
DEFAULT_V1341 = Path("tmp/wifi/v1341-android-pre-cnss-provider-policy-ready-live/manifest.json")
DEFAULT_V1343 = Path("tmp/wifi/v1343-provider-ready-sdx50m-route-live/manifest.json")
DEFAULT_V1345 = Path("tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live/manifest.json")

FORBIDDEN_FLAGS = (
    "wifi_hal_start_executed",
    "scan_connect_executed",
    "credential_use_executed",
    "dhcp_route_executed",
    "external_ping_executed",
    "wifi_bringup_executed",
    "flash_executed",
    "partition_write_executed",
    "boot_image_write_executed",
    "pmic_write_executed",
    "gpio_line_request_executed",
    "gdsc_write_executed",
    "direct_esoc_ioctl_executed",
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
    "manual_esoc_open_executed",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    if not isinstance(value, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not object"}
    value["_exists"] = True
    value["_path"] = str(path)
    return value


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


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def forbidden_hits(named_manifests: dict[str, dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for name, manifest in named_manifests.items():
        route = ((manifest.get("analysis") or {}).get("v1221_route") or {})
        for flag in FORBIDDEN_FLAGS:
            if bool_value(manifest.get(flag)) or bool_value(route.get(flag)):
                hits.append(f"{name}.{flag}")
    return hits


def summarize_v1329(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "reason": str(manifest.get("reason", "")),
    }


def summarize_v1331(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "reason": str(manifest.get("reason", "")),
        "handoff_wifi": bool_value(manifest.get("wifi_bringup_executed")),
        "external_ping": bool_value(manifest.get("external_ping_executed")),
    }


def summarize_v1332(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("v1331") or {}
    native = manifest.get("v1328") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "android_response_present": bool_value(android.get("response_present")),
        "android_wlfw_count": int_value(android.get("wlfw_count")),
        "android_wlfw_time": float_value(android.get("wlfw_time")),
        "android_esoc_time": float_value(android.get("esoc_time")),
        "android_bdf_count": int_value(android.get("bdf_count")),
        "android_bdf_time": float_value(android.get("bdf_time")),
        "android_wlan0_count": int_value(android.get("wlan0_count")),
        "android_wlan0_time": float_value(android.get("wlan0_time")),
        "android_pcie_count": int_value(android.get("pcie_count")),
        "android_mhi_count": int_value(android.get("mhi_count")),
        "native_powerup_seen": bool_value(native.get("powerup_seen")),
        "native_sample_count": int_value(native.get("sample_count")),
        "native_wlfw_kmsg_max": int_value(native.get("wlfw_kmsg_max")),
        "native_mhi_bus_max": int_value(native.get("mhi_bus_max")),
        "native_ks_process_max": int_value(native.get("ks_process_max")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
    }


def summarize_v1335(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "observe_only_gate": bool_value(manifest.get("observe_only_gate")),
        "wlfw_precondition_observed": bool_value(manifest.get("wlfw_precondition_observed")),
        "wlfw_trigger_ready": bool_value(manifest.get("wlfw_trigger_ready")),
        "subsys_esoc0_open_attempted": bool_value(manifest.get("subsys_esoc0_open_attempted")),
        "all_postflight_safe": bool_value((analysis.get("helper") or {}).get("contract", {}).get("all_postflight_safe")),
    }


def summarize_v1341(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = ((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {}
    keys = ((manifest.get("analysis") or {}).get("helper") or {}).get("keys") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "policy_load_executed": bool_value(manifest.get("policy_load_executed")),
        "provider_after_per_mgr": str(keys.get("wifi_companion_start.android_pre_cnss_provider.per_mgr.provider_seen", "")),
        "provider_after_per_proxy": str(keys.get("wifi_companion_start.android_pre_cnss_provider.per_proxy.provider_seen", "")),
        "per_mgr_domain": str(keys.get("wifi_hal_composite_child.per_mgr.selinux_current.after", "")),
        "per_proxy_domain": str(keys.get("wifi_hal_composite_child.per_proxy.selinux_current.after", "")),
        "helper_result": str(contract.get("result", "")),
        "all_postflight_safe": bool_value(contract.get("all_postflight_safe")),
        "per_mgr_subsys_esoc0_window": int_value(contract.get("per_mgr_subsys_esoc0_window"), -1),
        "mdm_helper_esoc0_window": int_value(contract.get("mdm_helper_esoc0_window"), -1),
        "ks_window": int_value(contract.get("ks_window"), -1),
        "mhi_cmdline_window": int_value(contract.get("mhi_cmdline_window"), -1),
    }


def summarize_v1343(manifest: dict[str, Any]) -> dict[str, Any]:
    route = ((manifest.get("analysis") or {}).get("v1221_route") or {})
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "route_decision": str(route.get("decision", "")),
        "sdx50m_registered": bool_value(route.get("sdx50m_registered")),
        "per_mgr_esoc0_any": bool_value(route.get("per_mgr_esoc0_any")),
        "wlfw_or_wlan_dmesg_seen": bool_value(route.get("wlfw_or_wlan_dmesg_seen")),
        "wlan0_up": bool_value(route.get("wlan0_up")),
    }


def summarize_v1345(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    current_route = manifest.get("current_route") or {}
    thread = manifest.get("thread_analysis") or {}
    return {
        "exists": bool_value(manifest.get("_exists")),
        "decision": str(manifest.get("decision", "")),
        "pass": bool_value(manifest.get("pass")),
        "private_route": bool_value(current_route.get("private_flag_in_child_script")),
        "private_cnss_bind_rc": str((manifest.get("private_cnss_daemon") or {}).get("bind_rc", "")),
        "private_cnss_expected": str((manifest.get("private_cnss_daemon") or {}).get("expected_c_string", "")),
        "cnss_registered_sdx50m": bool_value(thread.get("cnss_registered_sdx50m")),
        "powerup_seen": bool_value(sampler.get("timing_pm_service_powerup_seen")),
        "sample_count": int_value(sampler.get("timing_sample_count")),
        "gpio142_delta": int_value(sampler.get("timing_gpio142_irq_delta")),
        "errfatal_delta": int_value(sampler.get("timing_errfatal_irq_delta")),
        "pcie_transition": bool_value(sampler.get("timing_pcie_rc1_transition_seen")),
        "pci_dev_max": int_value(sampler.get("timing_pci_dev_max")),
        "mhi_bus_max": int_value(sampler.get("timing_mhi_bus_max")),
        "mhi_pipe_seen": bool_value(sampler.get("timing_mhi_pipe_seen")),
        "ks_process_max": int_value(sampler.get("timing_ks_process_max")),
        "wlfw_kmsg_max": int_value(sampler.get("timing_wlfw_kmsg_max")),
        "wlan0_seen": bool_value(sampler.get("timing_wlan0_seen")),
        "safety_clear": bool_value(current_route.get("timing_safety_clear")),
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw = {
        "v1329": read_json(args.v1329_manifest),
        "v1331": read_json(args.v1331_manifest),
        "v1332": read_json(args.v1332_manifest),
        "v1335": read_json(args.v1335_manifest),
        "v1341": read_json(args.v1341_manifest),
        "v1343": read_json(args.v1343_manifest),
        "v1345": read_json(args.v1345_manifest),
    }
    v1329 = summarize_v1329(raw["v1329"])
    v1331 = summarize_v1331(raw["v1331"])
    v1332 = summarize_v1332(raw["v1332"])
    v1335 = summarize_v1335(raw["v1335"])
    v1341 = summarize_v1341(raw["v1341"])
    v1343 = summarize_v1343(raw["v1343"])
    v1345 = summarize_v1345(raw["v1345"])

    forbidden = forbidden_hits(raw)
    current_route_no_transition = (
        v1345["exists"]
        and v1345["pass"]
        and v1345["decision"] == "v1345-current-route-mdm2ap-full-window-no-transition"
        and v1345["private_route"]
        and v1345["private_cnss_bind_rc"] == "0"
        and v1345["private_cnss_expected"] == "SDX50M"
        and v1345["cnss_registered_sdx50m"]
        and v1345["powerup_seen"]
        and v1345["sample_count"] >= 120
        and v1345["gpio142_delta"] == 0
        and v1345["errfatal_delta"] == 0
        and not v1345["pcie_transition"]
        and v1345["pci_dev_max"] == 0
        and v1345["mhi_bus_max"] == 0
        and not v1345["mhi_pipe_seen"]
        and v1345["ks_process_max"] == 0
        and v1345["wlfw_kmsg_max"] == 0
        and not v1345["wlan0_seen"]
        and v1345["safety_clear"]
    )
    android_positive_but_timing_coarse = (
        v1332["exists"]
        and v1332["pass"]
        and v1332["decision"] == "v1332-native-missing-early-wlfw-provider-state"
        and v1332["android_response_present"]
        and v1332["android_wlfw_count"] > 0
        and v1332["android_bdf_count"] > 0
        and v1332["android_wlan0_count"] > 0
        and v1332["android_wlfw_time"] > 0
        and v1332["android_esoc_time"] > 0
        and v1332["android_wlfw_time"] < v1332["android_esoc_time"]
        and (v1332["android_pcie_count"] == 0 or v1332["android_mhi_count"] == 0)
    )
    native_early_negative = (
        v1335["exists"]
        and v1335["pass"]
        and v1335["decision"] == "v1335-native-early-cnss-no-wlfw-observe-only"
        and v1335["observe_only_gate"]
        and not v1335["wlfw_precondition_observed"]
        and not v1335["wlfw_trigger_ready"]
        and not v1335["subsys_esoc0_open_attempted"]
    )
    provider_route_repaired = (
        v1341["exists"]
        and v1341["pass"]
        and v1341["decision"] == "v1341-provider-positive-no-lower-transition"
        and v1341["provider_after_per_mgr"] == "1"
        and v1341["provider_after_per_proxy"] == "1"
        and v1343["exists"]
        and v1343["pass"]
        and v1343["decision"] == "v1343-sdx50m-route-esoc-powerup-observed"
        and v1343["route_decision"] == "v1221-sdx50m-per-mgr-esoc0"
        and v1343["sdx50m_registered"]
        and v1343["per_mgr_esoc0_any"]
        and not v1343["wlfw_or_wlan_dmesg_seen"]
        and not v1343["wlan0_up"]
    )
    prior_android_prereq_branch = (
        v1329["exists"]
        and v1329["pass"]
        and v1329["decision"] == "v1329-android-prereq-is-earlier-sdx50m-response-sequence"
        and v1331["exists"]
        and v1331["pass"]
        and v1331["decision"] == "v1331-android-wlfw-before-subsys-esoc0"
    )

    checks = [
        check(
            "v1345-current-route-no-transition",
            current_route_no_transition,
            f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} gpio142={v1345['gpio142_delta']} pcie={v1345['pcie_transition']} mhi={v1345['mhi_bus_max']} ks={v1345['ks_process_max']} wlfw={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}",
        ),
        check(
            "android-positive-timing-coarse",
            android_positive_but_timing_coarse,
            f"wlfw={v1332['android_wlfw_time']} esoc={v1332['android_esoc_time']} pcie_count={v1332['android_pcie_count']} mhi_count={v1332['android_mhi_count']}",
        ),
        check(
            "native-early-cnss-negative",
            native_early_negative,
            f"observe_only={v1335['observe_only_gate']} wlfw_precondition={v1335['wlfw_precondition_observed']} trigger_ready={v1335['wlfw_trigger_ready']} esoc_open={v1335['subsys_esoc0_open_attempted']}",
        ),
        check(
            "provider-route-repaired-but-no-lower",
            provider_route_repaired,
            f"provider_mgr={v1341['provider_after_per_mgr']} provider_proxy={v1341['provider_after_per_proxy']} sdx50m={v1343['sdx50m_registered']} esoc={v1343['per_mgr_esoc0_any']} wlan0={v1343['wlan0_up']}",
        ),
        check(
            "prior-android-prereq-branch-present",
            prior_android_prereq_branch,
            f"v1329={v1329['decision']} v1331={v1331['decision']}",
        ),
        check(
            "guardrails-clear",
            not forbidden,
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, partition write, PMIC/GPIO/GDSC write, or direct eSoC mutation in reconciled inputs",
        ),
    ]

    if forbidden:
        decision = "v1346-forbidden-action-detected"
        passed = False
        reason = "forbidden actions were present in reconciled evidence: " + ", ".join(forbidden)
        next_step = "stop and audit evidence before another Wi-Fi or lower-path gate"
    elif not all(item["pass"] for item in checks[:1] + checks[2:]):
        decision = "v1346-evidence-incomplete"
        passed = False
        reason = "required current-route, native-negative, provider-route, or prior-prereq evidence is missing or inconsistent"
        next_step = "refresh the failed host-only evidence source before live work"
    elif android_positive_but_timing_coarse:
        decision = "v1346-need-android-earliest-response-recapture"
        passed = True
        reason = (
            "current native route reaches mdm_subsys_powerup with no lower transition, but the Android-positive "
            "timeline still lacks enough PCIe/MHI ordering detail on the same monotonic record as the early WLFW marker"
        )
        next_step = (
            "V1347 should perform an Android read-only recapture for earliest GPIO142/PCIe RC1/LTSSM/MHI/ks/WLFW/BDF/wlan0 "
            "relative to PM/provider/CNSS markers, then roll back to native"
        )
    else:
        decision = "v1346-current-route-missing-android-only-prepower-prereq"
        passed = True
        reason = "current route and Android-positive evidence are sufficient to keep the blocker on an Android-only prerequisite before or around mdm_subsys_powerup"
        next_step = "design the narrowest native read-only parity observer for the missing Android-only prerequisite"

    if args.command == "plan":
        decision = "v1346-android-only-response-prereq-plan-ready"
        passed = True
        reason = "plan-only; no device command or live action executed"
        next_step = "run the V1346 host-only reclassifier against existing evidence"

    return {
        "cycle": "v1346",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {name: str(repo_path(getattr(args, f"{name}_manifest"))) for name in raw},
        "v1329": v1329,
        "v1331": v1331,
        "v1332": v1332,
        "v1335": v1335,
        "v1341": v1341,
        "v1343": v1343,
        "v1345": v1345,
        "checks": checks,
        "forbidden_hits": forbidden,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "helper_deploy_executed": False,
        "daemon_start_executed": False,
        "pm_actor_executed": False,
        "tracefs_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "direct_esoc_ioctl_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "gdsc_write_executed": False,
        "wifi_hal_start_executed": False,
        "wificond_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]
    v1332 = manifest["v1332"]
    v1345 = manifest["v1345"]
    decision_rows = [
        ["current native route", f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} GPIO142={v1345['gpio142_delta']} PCIe={v1345['pcie_transition']} MHI={v1345['mhi_bus_max']} WLFW={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}"],
        ["Android-positive ordering", f"WLFW={v1332['android_wlfw_time']}s eSoC={v1332['android_esoc_time']}s PCIe_count={v1332['android_pcie_count']} MHI_count={v1332['android_mhi_count']} BDF={v1332['android_bdf_time']}s wlan0={v1332['android_wlan0_time']}s"],
        ["next safe branch", manifest["next_step"]],
    ]
    return "\n".join([
        "# V1346 Android-only Response Prerequisite Reclassifier",
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
        markdown_table(["check", "pass", "detail"], check_rows),
        "",
        "## Decision Basis",
        "",
        markdown_table(["surface", "value"], decision_rows),
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, flash, boot image write, or partition write was executed.",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    v1332 = manifest["v1332"]
    v1345 = manifest["v1345"]
    return "\n".join([
        "# Native Init V1346 Android-only Response Prerequisite Reclassifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1346`",
        "- Type: host-only evidence reclassifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1346-android-only-response-prereq-reclassifier/manifest.json`",
        "  - `tmp/wifi/v1346-android-only-response-prereq-reclassifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_android_only_response_prereq_reclassifier_v1346.py`",
        "",
        "## Key Facts",
        "",
        markdown_table(["fact", "value"], [
            ["current native lower window", f"powerup={v1345['powerup_seen']} samples={v1345['sample_count']} GPIO142={v1345['gpio142_delta']} errfatal={v1345['errfatal_delta']} PCIe={v1345['pcie_transition']} MHI={v1345['mhi_bus_max']} ks={v1345['ks_process_max']} WLFW={v1345['wlfw_kmsg_max']} wlan0={v1345['wlan0_seen']}"],
            ["Android-positive lower chain", f"WLFW={v1332['android_wlfw_time']}s eSoC={v1332['android_esoc_time']}s BDF={v1332['android_bdf_time']}s wlan0={v1332['android_wlan0_time']}s"],
            ["Android timing gap", f"PCIe_count={v1332['android_pcie_count']} MHI_count={v1332['android_mhi_count']}"],
            ["provider/SDX50M route", f"provider-positive={manifest['v1341']['provider_after_per_mgr']}/{manifest['v1341']['provider_after_per_proxy']} sdx50m={manifest['v1343']['sdx50m_registered']} esoc={manifest['v1343']['per_mgr_esoc0_any']}"],
        ]),
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "Do not proceed to PMIC/GPIO/GDSC/eSoC mutation or Wi-Fi HAL/scan/connect from V1345 alone. The next safest branch is an Android read-only recapture that puts the first SDX50M response markers on one timeline.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1329-manifest", type=Path, default=DEFAULT_V1329)
    parser.add_argument("--v1331-manifest", type=Path, default=DEFAULT_V1331)
    parser.add_argument("--v1332-manifest", type=Path, default=DEFAULT_V1332)
    parser.add_argument("--v1335-manifest", type=Path, default=DEFAULT_V1335)
    parser.add_argument("--v1341-manifest", type=Path, default=DEFAULT_V1341)
    parser.add_argument("--v1343-manifest", type=Path, default=DEFAULT_V1343)
    parser.add_argument("--v1345-manifest", type=Path, default=DEFAULT_V1345)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
