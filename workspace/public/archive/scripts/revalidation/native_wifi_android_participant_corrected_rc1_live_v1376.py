#!/usr/bin/env python3
"""V1376 bounded Android participant parity + corrected RC1 enumerate live gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351 as v1351
import native_wifi_current_route_mdm2ap_timing_sampler_live_v1345 as current
import native_wifi_late_per_proxy_response_sampler_live_v1242 as base

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1376-android-participant-corrected-rc1-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1376-android-participant-corrected-rc1-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1376-android-participant-corrected-rc1-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1376-android-participant-corrected-rc1-plan.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1376_ANDROID_PARTICIPANT_CORRECTED_RC1_LIVE_2026-06-01.md")

HELPER_MARKER = "a90_android_execns_probe v282"
HELPER_SHA256 = "c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418"
CORRECTED_RC1_FLAG = "--pm-observer-late-per-proxy-corrected-rc1-enumerate"
CORRECTED_PREFIX = "pm_service_trigger_observer.corrected_rc1_enumerate."


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _parse_prefixed_lines(text: str, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        line = raw_line.strip()
        if line.startswith(prefix) and "=" in line:
            key, value = line[len(prefix):].split("=", 1)
            result[key] = value
    return result


def _force_v1376_child_command(original):
    wrapped = v1351._force_v1351_child_command(original)

    def command(args: Any) -> list[str]:
        result = wrapped(args)
        if CORRECTED_RC1_FLAG not in result:
            result.append(CORRECTED_RC1_FLAG)
        return result

    return command


def configure() -> None:
    v1351.configure()
    v1351.HELPER_MARKER = HELPER_MARKER
    v1351.HELPER_SHA256 = HELPER_SHA256
    current.HELPER_MARKER = HELPER_MARKER
    current.HELPER_SHA256 = HELPER_SHA256
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.LATEST_POINTER = LATEST_POINTER
    base.HELPER_MARKER = HELPER_MARKER
    base.HELPER_SHA256 = HELPER_SHA256
    base.CYCLE_LABEL = "v1376"
    base.CYCLE_NAME = "V1376"
    base.SUMMARY_HEADING = "V1376 Android Participant Corrected RC1 Live"
    base.EVIDENCE_FILE_PREFIX = "v1376"
    base._force_response_sampler_child_command = _force_v1376_child_command


def _manifest_path() -> Path:
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        return repo_path(PLAN_OUT_DIR / "manifest.json")
    return repo_path(DEFAULT_OUT_DIR / "manifest.json")


def _run_dir() -> Path:
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        return repo_path(PLAN_OUT_DIR)
    return repo_path(DEFAULT_OUT_DIR)


def _read_run_text(manifest: dict[str, Any]) -> str:
    if manifest.get("command") == "plan":
        return ""
    return base._read_run_text(manifest)


def _read_child_script_text(manifest: dict[str, Any]) -> str:
    run_dir = Path(str(manifest.get("_run_dir") or _run_dir()))
    candidate = run_dir / "host/pm-cnss-voter-child-script.txt"
    try:
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _corrected_summary(raw: dict[str, str]) -> dict[str, Any]:
    return {
        "emitted": bool(raw),
        "begin": _int_value(raw.get("begin"), 0) == 1,
        "end": _int_value(raw.get("end"), 0) == 1,
        "triggered": _int_value(raw.get("triggered"), 0) == 1,
        "phase": raw.get("phase", ""),
        "gate_per_mgr_subsys_esoc0_count": _int_value(raw.get("gate_per_mgr_subsys_esoc0_count"), -1),
        "rc_sel_attempted": _int_value(raw.get("rc_sel_attempted"), 0) == 1,
        "rc_sel_rc": _int_value(raw.get("rc_sel_rc"), 999),
        "case_attempted": _int_value(raw.get("case_attempted"), 0) == 1,
        "case_rc": _int_value(raw.get("case_rc"), 999),
        "debugfs_control_write_executed": _int_value(raw.get("debugfs_control_write_executed"), 0) == 1,
        "skip_reason": raw.get("skip_reason", ""),
        "raw": raw,
    }


def _timing_downstream_progress(sampler: dict[str, Any]) -> bool:
    return (
        _int_value(sampler.get("timing_gpio142_irq_delta"), 0) > 0
        or _int_value(sampler.get("timing_errfatal_irq_delta"), 0) > 0
        or _int_value(sampler.get("timing_pci_dev_max"), 0) > 0
        or _int_value(sampler.get("timing_mhi_bus_max"), 0) > 0
        or bool(sampler.get("timing_mhi_pipe_seen"))
        or _int_value(sampler.get("timing_mhi_pipe_fd_max"), 0) > 0
        or _int_value(sampler.get("timing_ks_process_max"), 0) > 0
        or _int_value(sampler.get("timing_wlfw_kmsg_max"), 0) > 0
        or bool(sampler.get("timing_wlan0_seen"))
    )


def _forbidden_safety_clear(manifest: dict[str, Any]) -> bool:
    sampler = manifest.get("response_sampler") or {}
    pre = manifest.get("cnss_wlfw_precondition") or {}
    route = manifest.get("current_route") or {}
    base_safety = all(
        _int_value(sampler.get(key), 0) == 0
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
    )
    return bool(base_safety and pre.get("safety_clear") and route.get("timing_safety_clear"))


def decide_v1376(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1376-android-participant-corrected-rc1-plan-ready",
            True,
            "plan-only; no device command or live action executed",
            "run V1376 bounded live gate with helper v282",
        )

    sampler = manifest.get("response_sampler") or {}
    route = manifest.get("current_route") or {}
    corrected = manifest.get("corrected_rc1_enumerate") or {}

    if route.get("corrected_rc1_flag_in_child_script") != 1:
        return (
            "v1376-corrected-rc1-flag-missing",
            False,
            "child command did not include the corrected RC1 enumerate flag",
            "repair V1376 command injection before live retry",
        )
    if not _forbidden_safety_clear(manifest):
        return (
            "v1376-safety-violation",
            False,
            "one or more forbidden Wi-Fi/network/PMIC/GPIO/eSoC safety markers was nonzero",
            "stop and audit V1376 output before retry",
        )
    if not sampler.get("timing_emitted") or not sampler.get("timing_end"):
        return (
            "v1376-timing-summary-missing",
            False,
            "mdm2ap timing summary did not complete",
            "inspect helper output and cleanup before retry",
        )
    if not corrected.get("emitted") or not corrected.get("end"):
        return (
            "v1376-corrected-rc1-summary-missing",
            False,
            "corrected RC1 enumerate summary did not emit a complete block",
            "inspect helper output and debugfs availability before retry",
        )
    if not corrected.get("triggered"):
        return (
            "v1376-corrected-rc1-not-triggered",
            False,
            f"corrected RC1 enumerate skipped: {corrected.get('skip_reason', 'unknown')}",
            "repair late per_proxy/pm-service /dev/subsys_esoc0 gate before retry",
        )
    if corrected.get("rc_sel_rc") != 0 or corrected.get("case_rc") != 0:
        return (
            "v1376-corrected-rc1-write-failed",
            False,
            f"rc_sel_rc={corrected.get('rc_sel_rc')} case_rc={corrected.get('case_rc')}",
            "verify debugfs pci-msm mount and selector path before retry",
        )
    if _timing_downstream_progress(sampler):
        return (
            "v1376-corrected-rc1-downstream-progress",
            True,
            "corrected RC1 enumerate ran inside the Android participant window and downstream GPIO/PCI/MHI/WLFW/wlan0 progress appeared",
            "classify first progressed surface before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        )
    if bool(sampler.get("timing_pcie_rc1_transition_seen")):
        return (
            "v1376-corrected-rc1-ltssm-no-downstream-clean",
            True,
            "corrected RC1 enumerate ran inside the Android participant window and RC1 transitioned, but no GPIO142/PCI/MHI/WLFW/wlan0 appeared",
            "compare V1376 LTSSM phase against Android and decide whether another Android participant is missing",
        )
    return (
        "v1376-corrected-rc1-no-rc1-transition",
        True,
        "corrected RC1 enumerate write returned inside the Android participant window, but timing summary saw no RC1/downstream transition",
        "inspect pci-msm debugfs write timing and kmsg evidence before another live mutation",
    )


def augment_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = v1351.augment_manifest(manifest)
    run_text = _read_run_text(manifest)
    child_script = _read_child_script_text(manifest)
    corrected = _corrected_summary(_parse_prefixed_lines(run_text, CORRECTED_PREFIX))
    route = manifest.get("current_route") or {}
    route.update({
        "corrected_rc1_flag_in_child_script": 1 if CORRECTED_RC1_FLAG in child_script else 0,
        "helper_marker": HELPER_MARKER,
        "helper_sha256": HELPER_SHA256,
    })
    manifest["cycle"] = "v1376"
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["current_route"] = route
    manifest["corrected_rc1_enumerate"] = corrected
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["credential_use_executed"] = False
    manifest["dhcp_route_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["flash_executed"] = False
    manifest["partition_write_executed"] = False
    decision, passed, reason, next_step = decide_v1376(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def _key_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    sampler = manifest.get("response_sampler") or {}
    pre = manifest.get("cnss_wlfw_precondition") or {}
    corrected = manifest.get("corrected_rc1_enumerate") or {}
    route = manifest.get("current_route") or {}
    return [
        ["private_flag_in_child_script", route.get("private_flag_in_child_script")],
        ["precondition_flag_in_child_script", route.get("precondition_flag_in_child_script")],
        ["corrected_rc1_flag_in_child_script", route.get("corrected_rc1_flag_in_child_script")],
        ["corrected_triggered", corrected.get("triggered")],
        ["corrected_phase", corrected.get("phase")],
        ["corrected_gate_per_mgr_subsys_esoc0_count", corrected.get("gate_per_mgr_subsys_esoc0_count")],
        ["corrected_rc_sel_rc", corrected.get("rc_sel_rc")],
        ["corrected_case_rc", corrected.get("case_rc")],
        ["debugfs_control_write_executed", corrected.get("debugfs_control_write_executed")],
        ["timing_sample_count", sampler.get("timing_sample_count")],
        ["timing_pm_service_powerup_seen", sampler.get("timing_pm_service_powerup_seen")],
        ["timing_pcie_rc1_transition_seen", sampler.get("timing_pcie_rc1_transition_seen")],
        ["timing_gpio142_irq_delta", sampler.get("timing_gpio142_irq_delta")],
        ["timing_errfatal_irq_delta", sampler.get("timing_errfatal_irq_delta")],
        ["timing_pci_dev_max", sampler.get("timing_pci_dev_max")],
        ["timing_mhi_bus_max", sampler.get("timing_mhi_bus_max")],
        ["timing_mhi_pipe_seen", sampler.get("timing_mhi_pipe_seen")],
        ["timing_ks_process_max", sampler.get("timing_ks_process_max")],
        ["timing_wlfw_kmsg_max", sampler.get("timing_wlfw_kmsg_max")],
        ["timing_wlan0_seen", sampler.get("timing_wlan0_seen")],
        ["pre_last_checkpoint", pre.get("last_checkpoint")],
        ["safety_clear", _forbidden_safety_clear(manifest)],
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1376 Android Participant Corrected RC1 Live",
        "",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1376 Android Participant Corrected RC1 Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1376`",
        "- Type: bounded live lower Android participant + corrected RC1 enumerate gate",
        f"- Decision: `{manifest.get('decision', '')}`",
        f"- Result: {'PASS' if manifest.get('pass') else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_android_participant_corrected_rc1_live_v1376.py`",
        f"- Helper: `/cache/bin/a90_android_execns_probe` (`{HELPER_MARKER}`)",
        "- Evidence:",
        "  - `tmp/wifi/v1376-android-participant-corrected-rc1-live/manifest.json`",
        "  - `tmp/wifi/v1376-android-participant-corrected-rc1-live/summary.md`",
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
        "## Decision",
        "",
        str(manifest.get("reason", "")),
        "",
        "## Safety Scope",
        "",
        "V1376 remains below Wi-Fi bring-up. It does not start Wi-Fi HAL, scan, connect, credential handling, DHCP/routes, or external ping. The intentional live mutation is limited to pci-msm debugfs `rc_sel=2` and `case=11` after the Android participant lower gate is observed.",
        "",
        "## Next",
        "",
        str(manifest.get("next_step", "")),
        "",
    ])


def write_outputs(manifest: dict[str, Any]) -> None:
    out_dir = _run_dir()
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    if manifest.get("command") == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    pointer = PLAN_LATEST_POINTER if manifest.get("command") == "plan" else LATEST_POINTER
    write_private_text(repo_path(pointer), str(out_dir) + "\n")


def print_result(manifest: dict[str, Any]) -> None:
    print(f"v1376_decision: {manifest.get('decision')}")
    print(f"v1376_pass: {manifest.get('pass')}")
    print(f"v1376_reason: {manifest.get('reason')}")
    print(f"v1376_next: {manifest.get('next_step')}")
    print(f"v1376_manifest: {_run_dir() / 'manifest.json'}")


def main() -> int:
    configure()
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        base.DEFAULT_OUT_DIR = PLAN_OUT_DIR
        base.LATEST_POINTER = PLAN_LATEST_POINTER
    base_rc = base.main()
    manifest_path = _manifest_path()
    if not manifest_path.exists():
        return base_rc if base_rc != 0 else 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return 1
    manifest = augment_manifest(manifest)
    write_outputs(manifest)
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
