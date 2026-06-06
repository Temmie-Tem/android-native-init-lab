#!/usr/bin/env python3
"""V1304 host-only AP2MDM/MDM2AP response boundary classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1304-ap2mdm-mdm2ap-response-classifier")
DEFAULT_V1303_MANIFEST = Path("tmp/wifi/v1303-compact-powerup-marker-live/manifest.json")
DEFAULT_V1303_TRANSCRIPT = Path("tmp/wifi/v1303-compact-powerup-marker-live/host/pm-server-wchan-tracefs-observer.txt")
DEFAULT_V1290_REPORT = Path("docs/reports/NATIVE_INIT_V1290_TLMM_PCIE_SAMPLER_LIVE_2026-05-31.md")
DEFAULT_V1303_REPORT = Path("docs/reports/NATIVE_INIT_V1303_COMPACT_POWERUP_MARKER_LIVE_2026-05-31.md")
DEFAULT_V1244_REPORT = Path("docs/reports/NATIVE_INIT_V1244_ANDROID_POWER_SURFACE_CLASSIFIER_2026-05-31.md")
DEFAULT_V914_REPORT = Path("docs/reports/NATIVE_INIT_V914_V913_ANDROID_TIMELINE_RECLASSIFIER_2026-05-26.md")
DEFAULT_V968_REPORT = Path("docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md")
DEFAULT_V1000_REPORT = Path("docs/reports/NATIVE_INIT_V1000_ANDROID_ESOC_GPIO_RECAPTURE_HANDOFF_LIVE_2026-05-26.md")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1304-ap2mdm-mdm2ap-response-classifier.txt")

PHASE_KEY_RE = re.compile(r"^pm_service_trigger_observer\.response_sample\.([A-Za-z0-9_]+)\.([A-Za-z0-9_.-]+)=(.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1303-manifest", type=Path, default=DEFAULT_V1303_MANIFEST)
    parser.add_argument("--v1303-transcript", type=Path, default=DEFAULT_V1303_TRANSCRIPT)
    parser.add_argument("--v1290-report", type=Path, default=DEFAULT_V1290_REPORT)
    parser.add_argument("--v1303-report", type=Path, default=DEFAULT_V1303_REPORT)
    parser.add_argument("--v1244-report", type=Path, default=DEFAULT_V1244_REPORT)
    parser.add_argument("--v914-report", type=Path, default=DEFAULT_V914_REPORT)
    parser.add_argument("--v968-report", type=Path, default=DEFAULT_V968_REPORT)
    parser.add_argument("--v1000-report", type=Path, default=DEFAULT_V1000_REPORT)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    real_path = repo_path(path)
    if not real_path.exists():
        return ""
    return real_path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    real_path = repo_path(path)
    if not real_path.exists():
        return {}
    try:
        data = json.loads(real_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def is_gpio135_low(line: str) -> bool:
    return bool(re.search(r"\bgpio135\s*:\s*out\s+0\b", line))


def is_gpio135_high(line: str) -> bool:
    return bool(re.search(r"\bgpio135\s*:\s*out\s+1\b", line)) or " high " in f" {line.lower()} "


def is_gpio142_low(line: str) -> bool:
    return bool(re.search(r"\bgpio142\s*:\s*in\s+0\b", line))


def is_gpio142_high(line: str) -> bool:
    return bool(re.search(r"\bgpio142\s*:\s*in\s+1\b", line)) or " high " in f" {line.lower()} "


def parse_phase_samples(text: str) -> dict[str, dict[str, str]]:
    samples: dict[str, dict[str, str]] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = PHASE_KEY_RE.match(raw_line.strip())
        if not match:
            continue
        phase, key, value = match.groups()
        samples.setdefault(phase, {})[key] = value.strip()
    return samples


def analyze_native(v1303_manifest: dict[str, Any], transcript: str) -> dict[str, Any]:
    response = v1303_manifest.get("response_sampler") or {}
    phases = parse_phase_samples(transcript)
    powerup_phase_names = [
        phase
        for phase, data in phases.items()
        if int_value(data.get("powerup_marker.powerup_thread_count"), 0) > 0
        or data.get("powerup_marker.first_wchan") == "mdm_subsys_powerup"
        or data.get("powerup_marker.first_syscall.path.value") == "/dev/subsys_esoc0"
    ]
    gpio135_by_phase = {
        phase: data["tlmm_gpio135_debugfs_target_line"]
        for phase, data in phases.items()
        if "tlmm_gpio135_debugfs_target_line" in data
    }
    gpio142_by_phase = {
        phase: data["tlmm_gpio142_debugfs_target_line"]
        for phase, data in phases.items()
        if "tlmm_gpio142_debugfs_target_line" in data
    }
    gpio135_powerup_lines = [gpio135_by_phase[phase] for phase in powerup_phase_names if phase in gpio135_by_phase]
    gpio142_powerup_lines = [gpio142_by_phase[phase] for phase in powerup_phase_names if phase in gpio142_by_phase]
    mdm_status_counts = [
        int_value(data.get("mdm_status_count_total"), 0)
        for data in phases.values()
        if "mdm_status_count_total" in data
    ]
    mhi_bus_counts = [
        int_value(data.get("mhi_bus_count"), 0)
        for data in phases.values()
        if "mhi_bus_count" in data
    ]
    powerup_reached = (
        bool_value(response.get("powerup_subsys_esoc0_inferred_seen"))
        or int_value(response.get("max_powerup_thread_count"), 0) > 0
        or bool(powerup_phase_names)
    )
    gpio135_low_all_powerup = bool(gpio135_powerup_lines) and all(is_gpio135_low(line) for line in gpio135_powerup_lines)
    gpio142_low_all_powerup = bool(gpio142_powerup_lines) and all(is_gpio142_low(line) for line in gpio142_powerup_lines)
    gpio135_high_seen = any(is_gpio135_high(line) for line in gpio135_by_phase.values())
    gpio142_high_seen = any(is_gpio142_high(line) for line in gpio142_by_phase.values())
    max_mdm_status = max(mdm_status_counts or [int_value(response.get("max_mdm_status_count_total"), 0)])
    max_mhi_bus = max(mhi_bus_counts or [int_value(response.get("max_mhi_bus_count"), 0)])
    return {
        "manifest_exists": bool(v1303_manifest),
        "transcript_exists": bool(transcript),
        "v1303_decision": v1303_manifest.get("decision", ""),
        "v1303_pass": bool(v1303_manifest.get("pass")),
        "sample_count": int_value(response.get("sample_count"), 0),
        "phase_count": len(phases),
        "powerup_reached": powerup_reached,
        "powerup_phase_count": len(powerup_phase_names),
        "powerup_first_path_values": response.get("powerup_first_path_values") or [],
        "powerup_first_wchans": response.get("powerup_first_wchans") or [],
        "powerup_first_syscall_names": response.get("powerup_first_syscall_names") or [],
        "gpio135_lines": unique_sorted(list(gpio135_by_phase.values()) + list(response.get("tlmm_gpio135_debugfs_target_lines") or [])),
        "gpio142_lines": unique_sorted(list(gpio142_by_phase.values()) + list(response.get("tlmm_gpio142_debugfs_target_lines") or [])),
        "gpio135_powerup_lines": unique_sorted(gpio135_powerup_lines),
        "gpio142_powerup_lines": unique_sorted(gpio142_powerup_lines),
        "gpio135_low_all_powerup": gpio135_low_all_powerup,
        "gpio142_low_all_powerup": gpio142_low_all_powerup,
        "gpio135_high_seen": gpio135_high_seen,
        "gpio142_high_seen": gpio142_high_seen,
        "max_mdm_status_count_total": max_mdm_status,
        "max_mhi_bus_count": max_mhi_bus,
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")),
        "pcie1_gdsc_seen": bool_value(response.get("pcie1_gdsc_seen")),
        "pcie0_gdsc_seen": bool_value(response.get("pcie0_gdsc_seen")),
        "pmic_soft_reset_seen": bool_value(response.get("pmic_soft_reset_seen")),
        "gpiochip_lineinfo_seen": bool_value(response.get("gpiochip_lineinfo_seen")),
        "gpiochip_lineinfo_kernel_owned_seen": bool_value(response.get("gpiochip_lineinfo_kernel_owned_seen")),
        "gpiochip_lineinfo_ap2mdm_consumer_seen": bool_value(response.get("gpiochip_lineinfo_ap2mdm_consumer_seen")),
        "downstream_absent": (
            max_mdm_status == 0
            and max_mhi_bus == 0
            and not bool_value(response.get("mhi_pipe_seen"))
            and not bool_value(response.get("wlan0_seen"))
        ),
    }


def analyze_reference(texts: dict[str, str]) -> dict[str, Any]:
    mdm3 = texts["mdm3_research"]
    esoc = texts["esoc_research"]
    v1244 = texts["v1244_report"]
    v914 = texts["v914_report"]
    v968 = texts["v968_report"]
    v1000 = texts["v1000_report"]
    v1290 = texts["v1290_report"]
    return {
        "expected_ap2mdm_high": "GPIO 135 → HIGH" in mdm3 or "GPIO 135 → HIGH" in esoc,
        "expected_mdm2ap_status_high": "GPIO 142 HIGH" in esoc or "GPIO 142 (MDM2AP_STATUS)" in mdm3,
        "expected_powerup_function": "mdm_subsys_powerup" in mdm3 and "mdm_subsys_powerup" in esoc,
        "android_pcie_rc1_positive": "PCIe RC1 link initialized" in v1244,
        "android_upper_positive": all(marker in v914 for marker in ("WLFW start", "WLAN-PD", "BDF", "wlan0")),
        "android_wlan_pd_positive": "WLAN-PD indication" in v968 or "WLAN-PD indication" in v1000,
        "android_postboot_low_caution": "gpio135 : out 0" in v1000 and "GPIO142 interrupt count remains `0`" in v1000,
        "native_v1290_same_static_gpio": "gpio135 : out 0 16mA no pull" in v1290 and "gpio142 : in  0 8mA no pull" in v1290,
        "reference_paths": {
            "v1290_report": str(repo_path(DEFAULT_V1290_REPORT)),
            "v1244_report": str(repo_path(DEFAULT_V1244_REPORT)),
            "v914_report": str(repo_path(DEFAULT_V914_REPORT)),
            "v968_report": str(repo_path(DEFAULT_V968_REPORT)),
            "v1000_report": str(repo_path(DEFAULT_V1000_REPORT)),
            "mdm3_research": str(repo_path(DEFAULT_MDM3_RESEARCH)),
            "esoc_research": str(repo_path(DEFAULT_ESOC_RESEARCH)),
        },
    }


def decide(command: str, native: dict[str, Any], reference: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1304-ap2mdm-mdm2ap-response-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1304 host-only classifier",
        )
    if not native["manifest_exists"] or not native["transcript_exists"]:
        return (
            "v1304-input-missing",
            False,
            "V1303 manifest or transcript is missing",
            "restore or rerun V1303 evidence before classifying the GPIO response boundary",
        )
    if not native["v1303_pass"] or not native["powerup_reached"]:
        return (
            "v1304-powerup-trigger-not-proven",
            False,
            "V1303 does not prove pm-service reached /dev/subsys_esoc0/mdm_subsys_powerup",
            "fix powerup trigger evidence before classifying GPIO response",
        )
    if not reference["expected_ap2mdm_high"] or not reference["android_upper_positive"]:
        return (
            "v1304-reference-incomplete",
            False,
            "required AP2MDM contract or Android-positive reference markers are missing",
            "refresh host-only reference extraction before live work",
        )
    if native["gpio135_low_all_powerup"] and not native["gpio135_high_seen"] and native["downstream_absent"]:
        return (
            "v1304-ap2mdm-assertion-visibility-gap-classified",
            True,
            "V1303 reached /dev/subsys_esoc0/mdm_subsys_powerup, but every sampled powerup phase still showed GPIO135 low while GPIO142/PCIe/MHI/WLFW/wlan0 stayed absent; reference docs say the ext-sdx50m powerup contract should assert AP2MDM GPIO135 before MDM2AP/PCIe progress",
            "V1305 should add a tighter read-only AP2MDM/MDM2AP transition sampler or classify the ext-mdm PMIC/pinctrl branch that prevents GPIO135 assertion; do not retry blind eSoC/PM/CNSS actions",
        )
    if native["gpio135_high_seen"] and native["downstream_absent"]:
        return (
            "v1304-mdm2ap-response-gap-after-ap2mdm-classified",
            True,
            "native evidence includes AP2MDM high but no MDM2AP/PCIe/MHI/WLFW/wlan0 progress",
            "classify SDX50M response and MDM2AP IRQ readiness before any new live action",
        )
    return (
        "v1304-response-boundary-inconclusive",
        True,
        "V1303 powerup is proven, but current GPIO samples do not cleanly distinguish AP2MDM assertion from MDM2AP response",
        "add tighter timestamped read-only GPIO transition sampling before mutating lower eSoC state",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    native = manifest["analysis"]["native_v1303"]
    reference = manifest["analysis"]["reference"]
    native_rows = [
        ["V1303 decision", native["v1303_decision"]],
        ["samples/phases", f"{native['sample_count']} / {native['phase_count']}"],
        ["powerup reached", native["powerup_reached"]],
        ["powerup phases", native["powerup_phase_count"]],
        ["first path", ", ".join(native["powerup_first_path_values"])],
        ["first wchan", ", ".join(native["powerup_first_wchans"])],
        ["GPIO135 powerup lines", "; ".join(native["gpio135_powerup_lines"])],
        ["GPIO142 powerup lines", "; ".join(native["gpio142_powerup_lines"])],
        ["GPIO135 high seen", native["gpio135_high_seen"]],
        ["GPIO142 high seen", native["gpio142_high_seen"]],
        ["MDM status count max", native["max_mdm_status_count_total"]],
        ["MHI bus count max", native["max_mhi_bus_count"]],
        ["MHI pipe / wlan0", f"{native['mhi_pipe_seen']} / {native['wlan0_seen']}"],
    ]
    reference_rows = [
        ["AP2MDM contract expects GPIO135 HIGH", reference["expected_ap2mdm_high"]],
        ["MDM2AP status path documented", reference["expected_mdm2ap_status_high"]],
        ["Android PCIe RC1 positive reference", reference["android_pcie_rc1_positive"]],
        ["Android WLAN-PD/WLFW/BDF/wlan0 positive", reference["android_upper_positive"]],
        ["Android postboot-low caution noted", reference["android_postboot_low_caution"]],
        ["V1290 static GPIO corroboration", reference["native_v1290_same_static_gpio"]],
    ]
    return "\n".join([
        "# V1304 AP2MDM/MDM2AP Response Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Native Evidence",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Reference Evidence",
        "",
        markdown_table(["field", "value"], reference_rows),
        "",
        "## Interpretation",
        "",
        "- The live trigger path is no longer the blocker: V1303 shows `pm-service` in `openat(\"/dev/subsys_esoc0\")` and `mdm_subsys_powerup`.",
        "- The observed response boundary is below that trigger: sampled AP2MDM remains low, while MDM2AP IRQ count, PCIe/MHI, WLFW, and `wlan0` remain absent.",
        "- Android post-boot snapshots can also show low GPIO lines, so this classifier treats GPIO135 as an assertion/visibility boundary, not a standalone proof of root cause.",
        "",
        "## Safety",
        "",
        "- host-only classifier; no bridge/device command",
        "- no PMIC write, GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1303_manifest = load_json(args.v1303_manifest)
    transcript = read_text(args.v1303_transcript)
    texts = {
        "v1290_report": read_text(args.v1290_report),
        "v1303_report": read_text(args.v1303_report),
        "v1244_report": read_text(args.v1244_report),
        "v914_report": read_text(args.v914_report),
        "v968_report": read_text(args.v968_report),
        "v1000_report": read_text(args.v1000_report),
        "mdm3_research": read_text(args.mdm3_research),
        "esoc_research": read_text(args.esoc_research),
    }
    native = analyze_native(v1303_manifest, transcript)
    reference = analyze_reference(texts)
    decision, passed, reason, next_step = decide(args.command, native, reference)
    manifest = {
        "cycle": "v1304",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1303_manifest": str(repo_path(args.v1303_manifest)),
            "v1303_transcript": str(repo_path(args.v1303_transcript)),
            "v1290_report": str(repo_path(args.v1290_report)),
            "v1303_report": str(repo_path(args.v1303_report)),
            "v1244_report": str(repo_path(args.v1244_report)),
            "v914_report": str(repo_path(args.v914_report)),
            "v968_report": str(repo_path(args.v968_report)),
            "v1000_report": str(repo_path(args.v1000_report)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "analysis": {
            "native_v1303": native,
            "reference": reference,
        },
        "device_commands_executed": False,
        "live_actor_started": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_or_partition_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
