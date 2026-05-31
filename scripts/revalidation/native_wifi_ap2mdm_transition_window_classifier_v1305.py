#!/usr/bin/env python3
"""V1305 host-only AP2MDM transition-window classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1305-ap2mdm-transition-window-classifier")
DEFAULT_V1303_MANIFEST = Path("tmp/wifi/v1303-compact-powerup-marker-live/manifest.json")
DEFAULT_V1303_TRANSCRIPT = Path("tmp/wifi/v1303-compact-powerup-marker-live/host/pm-server-wchan-tracefs-observer.txt")
DEFAULT_V1304_MANIFEST = Path("tmp/wifi/v1304-ap2mdm-mdm2ap-response-classifier/manifest.json")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_V1244_REPORT = Path("docs/reports/NATIVE_INIT_V1244_ANDROID_POWER_SURFACE_CLASSIFIER_2026-05-31.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1305-ap2mdm-transition-window-classifier.txt")

PHASE_KEY_RE = re.compile(r"^pm_service_trigger_observer\.response_sample\.([A-Za-z0-9_]+)\.([A-Za-z0-9_.-]+)=(.*)$")
POLL_PHASE_RE = re.compile(r"^late_per_proxy_poll_(\d+)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1303-manifest", type=Path, default=DEFAULT_V1303_MANIFEST)
    parser.add_argument("--v1303-transcript", type=Path, default=DEFAULT_V1303_TRANSCRIPT)
    parser.add_argument("--v1304-manifest", type=Path, default=DEFAULT_V1304_MANIFEST)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("--v1244-report", type=Path, default=DEFAULT_V1244_REPORT)
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


def phase_sort_key(phase: str) -> tuple[int, int, str]:
    if phase == "pre_late_per_proxy":
        return (0, -1, phase)
    poll_match = POLL_PHASE_RE.match(phase)
    if poll_match:
        return (1, int(poll_match.group(1)), phase)
    if phase == "post_late_per_proxy":
        return (2, 0, phase)
    return (3, 0, phase)


def parse_phase_samples(text: str) -> dict[str, dict[str, str]]:
    samples: dict[str, dict[str, str]] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = PHASE_KEY_RE.match(raw_line.strip())
        if not match:
            continue
        phase, key, value = match.groups()
        samples.setdefault(phase, {})[key] = value.strip()
    return samples


def is_low_gpio135(line: str) -> bool:
    return bool(re.search(r"\bgpio135\s*:\s*out\s+0\b", line))


def is_high_gpio135(line: str) -> bool:
    return bool(re.search(r"\bgpio135\s*:\s*out\s+1\b", line)) or " high " in f" {line.lower()} "


def is_low_gpio142(line: str) -> bool:
    return bool(re.search(r"\bgpio142\s*:\s*in\s+0\b", line))


def is_high_gpio142(line: str) -> bool:
    return bool(re.search(r"\bgpio142\s*:\s*in\s+1\b", line)) or " high " in f" {line.lower()} "


def uniq(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def analyze_window(v1303_manifest: dict[str, Any], transcript: str) -> dict[str, Any]:
    response = v1303_manifest.get("response_sampler") or {}
    phases = parse_phase_samples(transcript)
    ordered_phases = sorted(phases, key=phase_sort_key)
    powerup_samples: list[dict[str, Any]] = []
    all_samples: list[dict[str, Any]] = []
    for phase in ordered_phases:
        data = phases[phase]
        monotonic_ms = int_value(data.get("monotonic_ms"), -1)
        powerup_count = int_value(data.get("powerup_marker.powerup_thread_count"), 0)
        first_wchan = data.get("powerup_marker.first_wchan", "")
        first_path = data.get("powerup_marker.first_syscall.path.value", "")
        sample = {
            "phase": phase,
            "monotonic_ms": monotonic_ms,
            "powerup_thread_count": powerup_count,
            "first_wchan": first_wchan,
            "first_path": first_path,
            "gpio135": data.get("tlmm_gpio135_debugfs_target_line", ""),
            "gpio142": data.get("tlmm_gpio142_debugfs_target_line", ""),
            "mdm_status_count": int_value(data.get("mdm_status_count_total"), 0),
            "mhi_bus_count": int_value(data.get("mhi_bus_count"), 0),
            "mhi_pipe_exists": int_value(data.get("mhi_pipe_exists"), 0),
            "ks_process_count": int_value(data.get("ks_process_count"), 0),
            "wlan0_exists": int_value(data.get("wlan0_exists"), 0),
            "pmic_soft_reset_line": data.get("pmic_soft_reset_line", ""),
            "pcie1_gdsc_line": data.get("pcie1_gdsc_line", ""),
            "pcie0_gdsc_line": data.get("pcie0_gdsc_line", ""),
        }
        all_samples.append(sample)
        if powerup_count > 0 or first_wchan == "mdm_subsys_powerup" or first_path == "/dev/subsys_esoc0":
            powerup_samples.append(sample)

    monotonic_values = [sample["monotonic_ms"] for sample in powerup_samples if sample["monotonic_ms"] >= 0]
    deltas = [
        monotonic_values[index + 1] - monotonic_values[index]
        for index in range(len(monotonic_values) - 1)
    ]
    gpio135_values = [str(sample["gpio135"]) for sample in powerup_samples]
    gpio142_values = [str(sample["gpio142"]) for sample in powerup_samples]
    mdm_status_values = [int(sample["mdm_status_count"]) for sample in powerup_samples]
    mhi_bus_values = [int(sample["mhi_bus_count"]) for sample in powerup_samples]
    return {
        "manifest_exists": bool(v1303_manifest),
        "transcript_exists": bool(transcript),
        "v1303_decision": v1303_manifest.get("decision", ""),
        "v1303_pass": bool(v1303_manifest.get("pass")),
        "manifest_sample_count": int_value(response.get("sample_count"), 0),
        "parsed_phase_count": len(phases),
        "ordered_phase_count": len(ordered_phases),
        "powerup_sample_count": len(powerup_samples),
        "powerup_first_phase": powerup_samples[0]["phase"] if powerup_samples else "",
        "powerup_last_phase": powerup_samples[-1]["phase"] if powerup_samples else "",
        "powerup_first_monotonic_ms": monotonic_values[0] if monotonic_values else -1,
        "powerup_last_monotonic_ms": monotonic_values[-1] if monotonic_values else -1,
        "powerup_window_ms": (monotonic_values[-1] - monotonic_values[0]) if len(monotonic_values) >= 2 else 0,
        "sample_delta_min_ms": min(deltas) if deltas else 0,
        "sample_delta_max_ms": max(deltas) if deltas else 0,
        "sample_delta_avg_ms": round(sum(deltas) / len(deltas), 3) if deltas else 0,
        "gpio135_values": uniq(gpio135_values),
        "gpio142_values": uniq(gpio142_values),
        "gpio135_low_all_powerup": bool(gpio135_values) and all(is_low_gpio135(line) for line in gpio135_values),
        "gpio135_high_seen": any(is_high_gpio135(line) for line in gpio135_values),
        "gpio142_low_all_powerup": bool(gpio142_values) and all(is_low_gpio142(line) for line in gpio142_values),
        "gpio142_high_seen": any(is_high_gpio142(line) for line in gpio142_values),
        "mdm_status_count_max": max(mdm_status_values or [0]),
        "mhi_bus_count_max": max(mhi_bus_values or [0]),
        "mhi_pipe_seen": any(int(sample["mhi_pipe_exists"]) > 0 for sample in powerup_samples),
        "ks_seen": any(int(sample["ks_process_count"]) > 0 for sample in powerup_samples),
        "wlan0_seen": any(int(sample["wlan0_exists"]) > 0 for sample in powerup_samples),
        "pmic_soft_reset_values": uniq([str(sample["pmic_soft_reset_line"]) for sample in powerup_samples]),
        "pcie1_gdsc_values": uniq([str(sample["pcie1_gdsc_line"]) for sample in powerup_samples]),
        "pcie0_gdsc_values": uniq([str(sample["pcie0_gdsc_line"]) for sample in powerup_samples]),
        "first_three_powerup_samples": powerup_samples[:3],
        "last_three_powerup_samples": powerup_samples[-3:],
    }


def analyze_reference(mdm3_research: str, esoc_research: str, v1244_report: str, v1304_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "v1304_decision": v1304_manifest.get("decision", ""),
        "v1304_pass": bool(v1304_manifest.get("pass")),
        "contract_has_150ms_then_gpio135_high": "msleep(150)" in mdm3_research and "GPIO 135 → HIGH" in mdm3_research,
        "contract_has_200ms_after_gpio135": "msleep(200)" in mdm3_research,
        "contract_has_mdm2ap_irq_async": "IRQ로 비동기 처리" in mdm3_research,
        "esoc_model_has_gpio135_high": "GPIO 135 HIGH" in esoc_research,
        "android_positive_pcie_mhi_wlan": all(token in v1244_report for token in ("PCIe RC1", "WLAN-PD", "WLAN FW is ready", "wlan0")),
        "native_pmic_pinctrl_delta_prior": "PM8150L soft-reset GPIO" in v1244_report and "MUX UNCLAIMED" in v1244_report,
    }


def decide(command: str, window: dict[str, Any], reference: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1305-ap2mdm-transition-window-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1305 host-only transition-window classifier",
        )
    if not window["manifest_exists"] or not window["transcript_exists"]:
        return (
            "v1305-input-missing",
            False,
            "V1303 manifest or transcript is missing",
            "restore V1303 evidence before classifying transition timing",
        )
    if not window["v1303_pass"] or window["powerup_sample_count"] <= 0:
        return (
            "v1305-powerup-window-not-proven",
            False,
            "V1303 powerup samples are not proven",
            "rerun or repair V1303 evidence before timing classification",
        )
    if not reference["v1304_pass"] or not reference["contract_has_150ms_then_gpio135_high"]:
        return (
            "v1305-reference-incomplete",
            False,
            "V1304 or ext-sdx50m AP2MDM timing reference is incomplete",
            "refresh host-only reference inputs before live work",
        )
    if (
        window["powerup_window_ms"] >= 1000
        and window["gpio135_low_all_powerup"]
        and not window["gpio135_high_seen"]
        and window["mdm_status_count_max"] == 0
        and window["mhi_bus_count_max"] == 0
        and not window["mhi_pipe_seen"]
        and not window["wlan0_seen"]
    ):
        return (
            "v1305-ap2mdm-low-through-extended-powerup-window",
            True,
            f"V1303 observed mdm_subsys_powerup for {window['powerup_window_ms']}ms across {window['powerup_sample_count']} samples; GPIO135 stayed low throughout and no MDM2AP/PCIe/MHI/WLFW/wlan0 progress appeared, so the V1304 gap is not explained by a short 50ms-sampler blind spot",
            "V1306 should classify why the proprietary ext-mdm powerup branch does not produce visible AP2MDM assertion: PM8150L soft-reset pinctrl, PCIe GDSC, or branch-before-mdm_do_first_power_on",
        )
    return (
        "v1305-transition-window-inconclusive",
        True,
        "V1303 has powerup samples, but the existing window does not close the AP2MDM timing question",
        "add source/build-only support for a tighter read-only GPIO transition sampler before another live lower trigger",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    window = manifest["analysis"]["window"]
    reference = manifest["analysis"]["reference"]
    window_rows = [
        ["V1303 decision", window["v1303_decision"]],
        ["manifest/parsed phases", f"{window['manifest_sample_count']} / {window['parsed_phase_count']}"],
        ["powerup samples", window["powerup_sample_count"]],
        ["first/last phase", f"{window['powerup_first_phase']} / {window['powerup_last_phase']}"],
        ["first/last monotonic ms", f"{window['powerup_first_monotonic_ms']} / {window['powerup_last_monotonic_ms']}"],
        ["powerup window ms", window["powerup_window_ms"]],
        ["sample delta min/avg/max ms", f"{window['sample_delta_min_ms']} / {window['sample_delta_avg_ms']} / {window['sample_delta_max_ms']}"],
        ["GPIO135 values", "; ".join(window["gpio135_values"])],
        ["GPIO142 values", "; ".join(window["gpio142_values"])],
        ["GPIO135 high seen", window["gpio135_high_seen"]],
        ["GPIO142 high seen", window["gpio142_high_seen"]],
        ["MDM status max", window["mdm_status_count_max"]],
        ["MHI bus max", window["mhi_bus_count_max"]],
        ["MHI pipe / ks / wlan0", f"{window['mhi_pipe_seen']} / {window['ks_seen']} / {window['wlan0_seen']}"],
    ]
    reference_rows = [
        ["V1304 pass/decision", f"{reference['v1304_pass']} / {reference['v1304_decision']}"],
        ["contract: 150ms then GPIO135 high", reference["contract_has_150ms_then_gpio135_high"]],
        ["contract: 200ms after GPIO135 high", reference["contract_has_200ms_after_gpio135"]],
        ["contract: GPIO142 async IRQ", reference["contract_has_mdm2ap_irq_async"]],
        ["Android-positive PCIe/WLAN reference", reference["android_positive_pcie_mhi_wlan"]],
        ["prior PMIC pinctrl delta", reference["native_pmic_pinctrl_delta_prior"]],
    ]
    return "\n".join([
        "# V1305 AP2MDM Transition Window Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Window",
        "",
        markdown_table(["field", "value"], window_rows),
        "",
        "## References",
        "",
        markdown_table(["field", "value"], reference_rows),
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
    v1304_manifest = load_json(args.v1304_manifest)
    transcript = read_text(args.v1303_transcript)
    window = analyze_window(v1303_manifest, transcript)
    reference = analyze_reference(
        read_text(args.mdm3_research),
        read_text(args.esoc_research),
        read_text(args.v1244_report),
        v1304_manifest,
    )
    decision, passed, reason, next_step = decide(args.command, window, reference)
    manifest = {
        "cycle": "v1305",
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
            "v1304_manifest": str(repo_path(args.v1304_manifest)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "esoc_research": str(repo_path(args.esoc_research)),
            "v1244_report": str(repo_path(args.v1244_report)),
        },
        "analysis": {
            "window": window,
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
