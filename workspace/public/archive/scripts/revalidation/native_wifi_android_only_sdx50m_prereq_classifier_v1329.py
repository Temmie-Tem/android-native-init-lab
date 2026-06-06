#!/usr/bin/env python3
"""V1329 host-only classifier for Android-only SDX50M response prerequisites.

V1328 proves native can keep pm-service in mdm_subsys_powerup for a full compact
timing window without GPIO142, MDM errfatal, PCIe RC1, MHI/ks, WLFW, or wlan0.
This classifier reconciles that negative window with Android-positive evidence
to select the next non-mutating gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1329-android-only-sdx50m-prereq-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1329-android-only-sdx50m-prereq-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1329_ANDROID_ONLY_SDX50M_PREREQ_CLASSIFIER_2026-05-31.md")
DEFAULT_V1328 = Path("tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json")
DEFAULT_V1324 = Path("tmp/wifi/v1324-provider-response-delta-classifier/manifest.json")
DEFAULT_V1321 = Path("tmp/wifi/v1321-image-link-reconciliation-classifier/manifest.json")
DEFAULT_V1239 = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_V896 = Path("tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json")
DEFAULT_V852 = Path("tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json")
DEFAULT_PM_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")

FORBIDDEN_FLAGS = (
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
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


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


def summarize_v1328(manifest: dict[str, Any]) -> dict[str, Any]:
    sampler = manifest.get("response_sampler") or {}
    post_pm = manifest.get("post_pm_mdm_helper_observer") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    pm = manifest.get("pm_service_trigger_observer") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "sample_count": int_value(sampler.get("timing_sample_count")),
        "powerup_seen": bool_value(sampler.get("timing_pm_service_powerup_seen")),
        "powerup_threads": int_value(sampler.get("timing_max_powerup_thread_count")),
        "gpio142_delta": int_value(sampler.get("timing_gpio142_irq_delta"), -1),
        "errfatal_delta": int_value(sampler.get("timing_errfatal_irq_delta"), -1),
        "pcie_transition": bool_value(sampler.get("timing_pcie_rc1_transition_seen")),
        "pci_dev_max": int_value(sampler.get("timing_pci_dev_max"), -1),
        "mhi_bus_max": int_value(sampler.get("timing_mhi_bus_max"), -1),
        "mhi_pipe_seen": bool_value(sampler.get("timing_mhi_pipe_seen")),
        "mhi_pipe_fd_max": int_value(sampler.get("timing_mhi_pipe_fd_max"), -1),
        "ks_process_max": int_value(sampler.get("timing_ks_process_max"), -1),
        "wlfw_kmsg_max": int_value(sampler.get("timing_wlfw_kmsg_max"), -1),
        "wlan0_seen": bool_value(sampler.get("timing_wlan0_seen")),
        "safety_zero": all(
            int_value(sampler.get(key), -1) == 0
            for key in (
                "timing_safety_wifi_hal_start",
                "timing_safety_scan_connect",
                "timing_safety_credentials",
                "timing_safety_dhcp_route",
                "timing_safety_external_ping",
                "timing_safety_pmic_write",
                "timing_safety_gpio_request",
                "timing_safety_direct_esoc_ioctl",
            )
        ),
        "mdm_helper_esoc_fd": int_value(post_pm.get("fd_esoc0_count_window"), -1),
        "mdm_helper_mhi_fd": int_value(post_pm.get("fd_mhi_pipe_count_window"), -1),
        "ks_count_window": int_value(post_pm.get("ks_count_window"), -1),
        "pm_service_subsys_esoc0_attempt": bool_value(parity.get("pm_service_subsys_esoc0_attempt")),
        "pm_service_subsys_modem_fd": int_value(parity.get("pm_service_subsys_modem_fd_count"), -1),
        "late_per_proxy_started": bool_value(pm.get("late_per_proxy_started")),
        "vndservice_provider_seen": bool_value(pm.get("vndservice_provider_seen")),
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
        "android_gpio142_irq_count": int_value(android.get("gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("pcie_rc1_lines")),
        "android_pcie_l0_lines": int_value(android.get("pcie_l0_lines")),
        "android_pcie_reset_time": float_value(android.get("pcie_reset_time"), -1.0),
        "android_pcie_l0_time": float_value(android.get("pcie_l0_time"), -1.0),
        "android_pm_service_esoc0_time": float_value(android.get("pm_service_esoc0_time"), -1.0),
        "android_ks_mhi_pipe": bool_value(android.get("ks_mhi_pipe")),
        "android_mdm3_online": bool_value(android.get("mdm3_online")),
        "android_wlfw_present": bool_value(android.get("wlfw_present")),
        "android_bdf_present": bool_value(android.get("bdf_present")),
        "android_wlan0_present": bool_value(android.get("wlan0_present")),
        "android_wlan0_time": float_value(android.get("wlan0_time"), -1.0),
    }


def summarize_v896(manifest: dict[str, Any]) -> dict[str, Any]:
    v852 = manifest.get("v852") or {}
    flags = manifest.get("v853_actor_flags") or {}
    timeline = v852.get("timeline") or {}
    counts = v852.get("counts") or {}
    symbols = v852.get("symbols") or {}
    irq = v852.get("irq_mdm_status") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
        "android_positive_control": str((manifest.get("classification") or {}).get("android_positive_control", "")),
        "source_contract": str((manifest.get("classification") or {}).get("source_contract", "")),
        "v852_mdm3_state": str(v852.get("mdm3_state", "")),
        "v852_gpio142_irq_count": int_value(irq.get("count_total")),
        "v852_pcie_count": int_value(counts.get("pcie")),
        "v852_mhi_count": int_value(counts.get("mhi")),
        "v852_wlfw_count": int_value(counts.get("wlfw")),
        "v852_wlan0_count": int_value(counts.get("wlan0")),
        "v852_pcie_l0_present": bool_value((timeline.get("pcie_link_l0") or {}).get("present")),
        "v852_pcie_l0_time": float_value((timeline.get("pcie_link_l0") or {}).get("time"), -1.0),
        "v852_wlan0_present": bool_value((timeline.get("wlan0") or {}).get("present")),
        "v852_mhi_hook_present": bool_value(symbols.get("mhi_arch_esoc_ops_power_on")),
        "v852_mhi_pci_probe_present": bool_value(symbols.get("mhi_pci_probe")),
        "has_mdm_helper_esoc_fd": bool_value(flags.get("has_mdm_helper_esoc_fd")),
        "has_ks_esoc_fd": bool_value(flags.get("has_ks_esoc_fd")),
        "has_ks_mhi_pipe": bool_value(flags.get("has_ks_mhi_pipe")),
        "has_per_mgr_subsys_esoc0_fd": bool_value(flags.get("has_per_mgr_subsys_esoc0_fd")),
        "has_mdm_helper_selinux": bool_value(flags.get("has_mdm_helper_selinux")),
    }


def summarize_v852(manifest: dict[str, Any]) -> dict[str, Any]:
    comparison = (manifest.get("context") or {}).get("comparison") or {}
    nested = comparison.get("v852") or {}
    return {
        "decision": manifest.get("decision", "") or nested.get("decision", ""),
        "pass": bool_value(manifest.get("pass")) or bool_value(nested.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest)
        and not bool_value(manifest.get("gpio_write_executed"))
        and not bool_value(manifest.get("provider_sysfs_write_executed"))
        and not bool_value(manifest.get("wlan_driver_state_write_executed")),
    }


def summarize_simple(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": input_forbidden_clear(manifest),
    }


def summarize_research(pm_text: str, mdm3_text: str) -> dict[str, Any]:
    return {
        "pm_notes_subsys_esoc0": "/dev/subsys_esoc0" in pm_text and "mdm_subsys_powerup" in pm_text,
        "pm_notes_per_mgr": "pm-service" in pm_text or "per_mgr" in pm_text,
        "mdm3_notes_ap2mdm_gpio135": "GPIO 135" in mdm3_text and "AP2MDM" in mdm3_text,
        "mdm3_notes_mdm2ap_gpio142": "GPIO 142" in mdm3_text and "MDM2AP" in mdm3_text,
        "mdm3_notes_ext_sdx50m": "ext-sdx50m" in mdm3_text or "SDX50M" in mdm3_text,
    }


def check(name: str, passed: bool, detail: str, next_step: str = "") -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if passed else "blocked",
        "detail": detail,
        "next_step": next_step,
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1328 = summarize_v1328(load_json(args.v1328_manifest))
    v1324 = summarize_simple(load_json(args.v1324_manifest))
    v1321 = summarize_simple(load_json(args.v1321_manifest))
    v1239 = summarize_v1239(load_json(args.v1239_manifest))
    v896 = summarize_v896(load_json(args.v896_manifest))
    v852 = summarize_v852(load_json(args.v852_manifest))
    research = summarize_research(read_text(args.pm_research), read_text(args.mdm3_research))

    native_full_negative = (
        v1328["pass"]
        and v1328["decision"] == "v1328-mdm2ap-timing-full-window-no-transition"
        and v1328["sample_count"] >= 120
        and v1328["powerup_seen"]
        and v1328["powerup_threads"] >= 1
        and v1328["gpio142_delta"] == 0
        and v1328["errfatal_delta"] == 0
        and not v1328["pcie_transition"]
        and v1328["pci_dev_max"] == 0
        and v1328["mhi_bus_max"] == 0
        and not v1328["mhi_pipe_seen"]
        and v1328["ks_process_max"] == 0
        and v1328["wlfw_kmsg_max"] == 0
        and not v1328["wlan0_seen"]
        and v1328["safety_zero"]
    )
    native_userspace_actor_parity_partial = (
        v1328["late_per_proxy_started"]
        and v1328["vndservice_provider_seen"]
        and v1328["mdm_helper_esoc_fd"] > 0
        and v1328["pm_service_subsys_esoc0_attempt"]
        and v1328["pm_service_subsys_modem_fd"] > 0
    )
    native_missing_android_lower_artifacts = (
        v1328["mdm_helper_mhi_fd"] == 0
        and v1328["ks_count_window"] == 0
        and v1328["mhi_pipe_fd_max"] == 0
    )
    android_positive_chain = (
        v852["pass"]
        and v896["pass"]
        and v1239["pass"]
        and v1239["android_gpio142_irq_count"] > 0
        and v1239["android_pcie_rc1_lines"] > 0
        and v1239["android_pcie_l0_lines"] > 0
        and v1239["android_ks_mhi_pipe"]
        and v1239["android_mdm3_online"]
        and v1239["android_wlfw_present"]
        and v1239["android_bdf_present"]
        and v1239["android_wlan0_present"]
        and v896["has_mdm_helper_esoc_fd"]
        and v896["has_ks_mhi_pipe"]
        and v896["has_per_mgr_subsys_esoc0_fd"]
    )
    android_timing_order_suspicious = (
        v1239["android_pcie_l0_time"] >= 0
        and v1239["android_pm_service_esoc0_time"] >= 0
        and v1239["android_pcie_l0_time"] < v1239["android_pm_service_esoc0_time"]
    )
    prior_branch_closed = (
        v1321["pass"]
        and v1321["decision"] == "v1321-image-link-gate-covered-next-sdx50m-response-inputs"
        and v1324["pass"]
        and v1324["decision"] == "v1324-delta-is-post-ap2mdm-mdm2ap-response-gap"
    )
    research_contract_present = (
        research["pm_notes_subsys_esoc0"]
        and research["pm_notes_per_mgr"]
        and research["mdm3_notes_ap2mdm_gpio135"]
        and research["mdm3_notes_mdm2ap_gpio142"]
        and research["mdm3_notes_ext_sdx50m"]
    )
    guardrails_clear = all(item["forbidden_clear"] for item in (v1328, v1324, v1321, v1239, v896, v852))

    checks = [
        check("v1328-full-negative-window", native_full_negative, f"samples={v1328['sample_count']} powerup={v1328['powerup_seen']} gpio142_delta={v1328['gpio142_delta']} pcie={v1328['pcie_transition']} mhi={v1328['mhi_bus_max']} ks={v1328['ks_process_max']} wlan0={v1328['wlan0_seen']}"),
        check("native-userspace-actor-parity-partial", native_userspace_actor_parity_partial, f"late_per_proxy={v1328['late_per_proxy_started']} mdm_helper_esoc_fd={v1328['mdm_helper_esoc_fd']} pm_service_esoc0={v1328['pm_service_subsys_esoc0_attempt']}"),
        check("native-missing-android-lower-artifacts", native_missing_android_lower_artifacts, f"mdm_helper_mhi_fd={v1328['mdm_helper_mhi_fd']} ks={v1328['ks_count_window']} mhi_pipe_fd={v1328['mhi_pipe_fd_max']}"),
        check("android-positive-chain", android_positive_chain, f"gpio142={v1239['android_gpio142_irq_count']} pcie_l0={v1239['android_pcie_l0_lines']} ks_mhi={v1239['android_ks_mhi_pipe']} wlan0={v1239['android_wlan0_present']}"),
        check("android-timing-order-needs-recapture", android_timing_order_suspicious, f"pcie_l0_time={v1239['android_pcie_l0_time']} pm_service_esoc0_time={v1239['android_pm_service_esoc0_time']}"),
        check("prior-branch-closed", prior_branch_closed, f"v1321={v1321['decision']} v1324={v1324['decision']}"),
        check("research-contract-present", research_contract_present, json.dumps(research, sort_keys=True)),
        check("guardrails-clear", guardrails_clear, "host-only classifier; no live action, Wi-Fi action, network action, flash, or lower mutation"),
    ]

    passed = all(row["status"] == "pass" for row in checks)
    if passed:
        decision = "v1329-android-prereq-is-earlier-sdx50m-response-sequence"
        reason = (
            "V1328 proves native reaches mdm_subsys_powerup with a complete no-transition window, "
            "while Android evidence has GPIO142/PCIe/MHI/ks/WLFW/wlan0 and shows PCIe L0 before the captured pm-service esoc0 timestamp; "
            "the next blocker is an Android-only earlier SDX50M response prerequisite, not Wi-Fi HAL/connect"
        )
        next_step = (
            "V1330 should design a focused Android read-only timing recapture around earliest per_mgr/per_proxy/mdm_helper, "
            "PCIe RC1, GPIO142, and ks/MHI with one monotonic timeline before any native PMIC/GPIO/eSoC mutation"
        )
    elif native_full_negative and android_positive_chain:
        decision = "v1329-android-prereq-needs-timing-recapture"
        reason = "native no-transition and Android positive-control are both proven, but exact Android timing order is insufficient or inconsistent"
        next_step = "run a focused Android read-only timing recapture before native mutation"
    elif not native_full_negative:
        decision = "v1329-native-v1328-window-not-usable"
        reason = "V1328 full negative timing window is missing or incomplete"
        next_step = "rerun or repair V1328 before classification"
    else:
        decision = "v1329-evidence-incomplete"
        reason = "Android-only SDX50M prerequisite evidence is incomplete"
        next_step = "refresh missing host-only inputs before any live gate"

    return {
        "cycle": "v1329",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1328_manifest": str(repo_path(args.v1328_manifest)),
            "v1324_manifest": str(repo_path(args.v1324_manifest)),
            "v1321_manifest": str(repo_path(args.v1321_manifest)),
            "v1239_manifest": str(repo_path(args.v1239_manifest)),
            "v896_manifest": str(repo_path(args.v896_manifest)),
            "v852_manifest": str(repo_path(args.v852_manifest)),
            "pm_research": str(repo_path(args.pm_research)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
        },
        "v1328": v1328,
        "v1324": v1324,
        "v1321": v1321,
        "v1239": v1239,
        "v896": v896,
        "v852": v852,
        "research": research,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        **{flag: False for flag in FORBIDDEN_FLAGS},
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    v1328 = manifest["v1328"]
    v1239 = manifest["v1239"]
    v896 = manifest["v896"]
    return "\n".join([
        "# V1329 Android-only SDX50M Prerequisite Classifier",
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
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
        "## Reconciled Surfaces",
        "",
        markdown_table(["surface", "native V1328", "Android evidence"], [
            ["provider request", f"powerup={v1328['powerup_seen']} threads={v1328['powerup_threads']}", f"per_mgr_subsys_esoc0_fd={v896['has_per_mgr_subsys_esoc0_fd']}"],
            ["MDM2AP status", f"gpio142_delta={v1328['gpio142_delta']}", f"gpio142_irq={v1239['android_gpio142_irq_count']}"],
            ["PCIe RC1", f"transition={v1328['pcie_transition']} pci_max={v1328['pci_dev_max']}", f"rc1_lines={v1239['android_pcie_rc1_lines']} l0_time={v1239['android_pcie_l0_time']}"],
            ["MHI/ks", f"mhi_bus={v1328['mhi_bus_max']} ks={v1328['ks_process_max']}", f"ks_mhi_pipe={v1239['android_ks_mhi_pipe']} actor_ks_mhi={v896['has_ks_mhi_pipe']}"],
            ["WLFW/wlan0", f"wlfw={v1328['wlfw_kmsg_max']} wlan0={v1328['wlan0_seen']}", f"wlfw={v1239['android_wlfw_present']} wlan0={v1239['android_wlan0_present']}"],
        ]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command or mutation",
        "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
        "- no PMIC/GPIO/GDSC/eSoC write, flash, boot image write, or partition write",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1329 Android-only SDX50M Prerequisite Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1329`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/manifest.json`",
        "  - `tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_android_only_sdx50m_prereq_classifier_v1329.py`",
        "",
        "V1329 reconciles V1328 with Android-positive V852/V896/V1239 evidence.",
        "Native reaches `mdm_subsys_powerup` and holds a full compact timing window,",
        "but still gets no GPIO142/MDM2AP response, no MDM errfatal IRQ, no PCIe",
        "RC1, no MHI/ks, no WLFW, and no `wlan0`. Android evidence contains the",
        "complete downstream chain and shows PCIe L0 before the captured",
        "`pm-service` eSoC timestamp, so the next unknown is an earlier Android-only",
        "SDX50M response prerequisite or timing relation.",
        "",
        "## Decision",
        "",
        "The next useful unit is not Wi-Fi HAL, scan/connect, credentials, DHCP,",
        "external ping, or a PMIC/GPIO/eSoC mutation. V1330 should design a focused",
        "Android read-only timing recapture that puts earliest `per_mgr`/`per_proxy`,",
        "`mdm_helper`, GPIO142, PCIe RC1, and `ks`/MHI on one monotonic timeline.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, helper deploy, actor start, tracefs",
        "write, live eSoC ioctl/notify, PMIC write, GPIO request, GDSC/eSoC write,",
        "Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,",
        "flash, boot image write, or partition write occurred.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1328-manifest", type=Path, default=DEFAULT_V1328)
    parser.add_argument("--v1324-manifest", type=Path, default=DEFAULT_V1324)
    parser.add_argument("--v1321-manifest", type=Path, default=DEFAULT_V1321)
    parser.add_argument("--v1239-manifest", type=Path, default=DEFAULT_V1239)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896)
    parser.add_argument("--v852-manifest", type=Path, default=DEFAULT_V852)
    parser.add_argument("--pm-research", type=Path, default=DEFAULT_PM_RESEARCH)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1329-android-only-sdx50m-prereq-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action"
        manifest["next_step"] = "run V1329 host-only classifier"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        repo_path(REPORT_PATH).write_text(render_report(manifest), encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
