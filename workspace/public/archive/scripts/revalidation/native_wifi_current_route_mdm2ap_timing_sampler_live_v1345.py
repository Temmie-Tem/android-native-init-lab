#!/usr/bin/env python3
"""V1345 current-route MDM2AP timing sampler.

Runs the V1328 compact no-write MDM2AP/PCIe/MHI timing sampler, but forces the
current V1343 private ``cnss-daemon.sdx50m`` route. This is still a lower
readiness gate only: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import native_wifi_mdm2ap_timing_sampler_live_v1328 as timing
import native_wifi_late_per_proxy_response_sampler_live_v1242 as base

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1345-current-route-mdm2ap-timing-sampler-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1345-current-route-mdm2ap-timing-sampler-plan.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md")

CYCLE_LABEL = "v1345"
CYCLE_NAME = "V1345"
SUMMARY_HEADING = "V1345 Current Route MDM2AP Timing Sampler"
REPORT_TITLE = "Native Init V1345 Current Route MDM2AP Timing Sampler Live"
SCRIPT_PATH = "scripts/revalidation/native_wifi_current_route_mdm2ap_timing_sampler_live_v1345.py"
HELPER_MARKER = "a90_android_execns_probe v279"
HELPER_SHA256 = "2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a"
PRIVATE_CNSS_FLAG = "--pm-observer-private-cnss-daemon-sdx50m"
PRIVATE_CNSS_PATH_FLAG = "--private-cnss-daemon-path"
PRIVATE_CNSS_PATH = "/cache/bin/cnss-daemon.sdx50m"
PRIVATE_CNSS_SHA256 = "784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd"
ESOC_DEV_NODE_FLAG = "--pm-observer-mknod-esoc-dev-node-before-cnss"

_TIMING_FORCE = base._force_response_sampler_child_command


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


def _force_current_route_child_command(original):
    wrapped = _TIMING_FORCE(original)

    def command(args: Any) -> list[str]:
        base_command = wrapped(args)
        result: list[str] = []
        skip_next = False
        for item in base_command:
            if skip_next:
                skip_next = False
                continue
            if item in {"--pm-observer-fake-esoc-name-sdxprairie", "--pm-observer-fake-esoc-name-readback-only"}:
                continue
            if item == PRIVATE_CNSS_PATH_FLAG:
                skip_next = True
                continue
            result.append(item)
        if ESOC_DEV_NODE_FLAG not in result:
            result.append(ESOC_DEV_NODE_FLAG)
        if PRIVATE_CNSS_FLAG not in result:
            result.append(PRIVATE_CNSS_FLAG)
        result.extend([PRIVATE_CNSS_PATH_FLAG, PRIVATE_CNSS_PATH])
        return result

    return command


def configure() -> None:
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.LATEST_POINTER = LATEST_POINTER
    base.HELPER_MARKER = HELPER_MARKER
    base.HELPER_SHA256 = HELPER_SHA256
    base.CYCLE_LABEL = CYCLE_LABEL
    base.CYCLE_NAME = CYCLE_NAME
    base.SUMMARY_HEADING = SUMMARY_HEADING
    base.EVIDENCE_FILE_PREFIX = CYCLE_LABEL
    base._force_response_sampler_child_command = _force_current_route_child_command


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


def _timing_safety_clear(sampler: dict[str, Any]) -> bool:
    safety_keys = (
        "timing_safety_wifi_hal_start",
        "timing_safety_scan_connect",
        "timing_safety_credentials",
        "timing_safety_dhcp_route",
        "timing_safety_external_ping",
        "timing_safety_pmic_write",
        "timing_safety_gpio_request",
        "timing_safety_direct_esoc_ioctl",
    )
    return all(_int_value(sampler.get(key), -1) == 0 for key in safety_keys)


def _field_changed(sampler: dict[str, Any], initial_key: str, last_key: str) -> bool:
    initial = str(sampler.get(initial_key) or "")
    last = str(sampler.get(last_key) or "")
    return bool(initial and last and initial != last)


def _timing_progress(sampler: dict[str, Any]) -> bool:
    return (
        _int_value(sampler.get("timing_gpio142_irq_delta"), 0) > 0
        or _int_value(sampler.get("timing_errfatal_irq_delta"), 0) > 0
        or bool(sampler.get("timing_pcie_rc1_transition_seen"))
        or bool(sampler.get("timing_pcie1_gdsc_nonzero_seen"))
        or _field_changed(sampler, "timing_pcie1_gdsc_initial", "timing_pcie1_gdsc_last")
        or _field_changed(sampler, "timing_pcie1_clkref_initial", "timing_pcie1_clkref_last")
        or _field_changed(sampler, "timing_pcie1_phy_refgen_initial", "timing_pcie1_phy_refgen_last")
        or _field_changed(sampler, "timing_pcie1_pipe_clk_initial", "timing_pcie1_pipe_clk_last")
        or _field_changed(sampler, "timing_gpio102_perst_initial", "timing_gpio102_perst_last")
        or _field_changed(sampler, "timing_gpio103_clkreq_initial", "timing_gpio103_clkreq_last")
        or _field_changed(sampler, "timing_gpio104_wake_initial", "timing_gpio104_wake_last")
        or _int_value(sampler.get("timing_pci_dev_max"), 0) > 0
        or _int_value(sampler.get("timing_mhi_bus_max"), 0) > 0
        or bool(sampler.get("timing_mhi_pipe_seen"))
        or _int_value(sampler.get("timing_mhi_pipe_fd_max"), 0) > 0
        or _int_value(sampler.get("timing_ks_process_max"), 0) > 0
        or _int_value(sampler.get("timing_wlfw_kmsg_max"), 0) > 0
        or bool(sampler.get("timing_wlan0_seen"))
    )


def _pcie1_rc_stayed_off(sampler: dict[str, Any]) -> bool:
    perst_initial = str(sampler.get("timing_gpio102_perst_initial") or "")
    perst_last = str(sampler.get("timing_gpio102_perst_last") or "")
    return (
        bool(sampler.get("timing_pcie1_gdsc_seen"))
        and not bool(sampler.get("timing_pcie1_gdsc_nonzero_seen"))
        and "0mV" in str(sampler.get("timing_pcie1_gdsc_initial") or "")
        and "0mV" in str(sampler.get("timing_pcie1_gdsc_last") or "")
        and "out 0" in perst_initial
        and "out 0" in perst_last
        and _int_value(sampler.get("timing_pci_dev_max"), 0) == 0
        and _int_value(sampler.get("timing_mhi_bus_max"), 0) == 0
    )


def decide_v1345(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    def decision(suffix: str) -> str:
        return f"{CYCLE_LABEL}-{suffix}"

    if manifest.get("command") == "plan":
        return (
            decision("current-route-mdm2ap-timing-plan-ready"),
            True,
            "plan-only; no device command or live action executed",
            f"run {CYCLE_NAME} current-route MDM2AP timing sampler live",
        )

    sampler = manifest.get("response_sampler") or {}
    private_cnss = manifest.get("private_cnss_daemon") or {}
    current_route = manifest.get("current_route") or {}

    if current_route.get("private_flag_in_child_script") != 1:
        return (
            decision("current-route-private-cnss-missing"),
            False,
            "child command did not include private cnss-daemon SDX50M flag",
            f"repair {CYCLE_NAME} child command injection before live retry",
        )
    if private_cnss.get("bind_rc") != "0" or private_cnss.get("expected_c_string") != "SDX50M":
        return (
            decision("current-route-private-cnss-missing"),
            False,
            f"private_cnss={private_cnss}",
            "verify /cache/bin/cnss-daemon.sdx50m identity and private bind markers",
        )
    if not sampler.get("timing_emitted") or not sampler.get("timing_end"):
        return (
            decision("current-route-timing-missing"),
            False,
            "mdm2ap_timing summary did not emit a complete begin/end block",
            "inspect helper stdout before retrying",
        )
    if sampler.get("timing_mode") != "late-per-proxy-mdm2ap-errfatal-pcie-timing":
        return (
            decision("current-route-timing-missing"),
            False,
            f"unexpected timing mode={sampler.get('timing_mode')!r}",
            "verify timing sampler flag injection",
        )
    if _int_value(sampler.get("timing_sample_count"), 0) < timing.EXPECTED_MIN_TIMING_SAMPLE_COUNT:
        return (
            decision("current-route-timing-missing"),
            False,
            f"timing sample_count={sampler.get('timing_sample_count')}",
            "inspect helper timing window before retrying",
        )
    if not _timing_safety_clear(sampler):
        return (
            decision("current-route-safety-violation"),
            False,
            "timing summary reports a forbidden Wi-Fi/network/lower mutation action",
            "stop and audit helper output",
        )
    if _timing_progress(sampler):
        return (
            decision("current-route-mdm2ap-progress"),
            True,
            "current private SDX50M route observed lower response progress",
            "classify the first progressed surface before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        )
    if sampler.get("timing_pm_service_powerup_seen"):
        if _pcie1_rc_stayed_off(sampler):
            return (
                decision("current-route-pcie1-rc-stayed-off"),
                True,
                "current private SDX50M route reached mdm_subsys_powerup, but pcie1 RC stayed off: pcie_1_gdsc remained 0mV, PERST stayed low, and no PCI/MHI/WLFW/wlan0 transition appeared",
                "classify PM8150L GPIO9 PON parity, then design a bounded pcie1 RC enable experiment only if PON parity is healthy",
            )
        return (
            decision("current-route-mdm2ap-full-window-no-transition"),
            True,
            "current private SDX50M route reached mdm_subsys_powerup, but full timing window saw no GPIO142/errfatal/PCIe/MHI/ks/WLFW/wlan0 transition",
            "classify Android-only SDX50M response prerequisite before any PMIC/GPIO/eSoC mutation",
        )
    return (
        decision("current-route-no-powerup"),
        False,
        "current private SDX50M route did not reach mdm_subsys_powerup in timing sampler",
        "repair current route trigger before lower-response sampling",
    )


def augment_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    run_text = _read_run_text(manifest)
    child_script = _read_child_script_text(manifest)
    private_cnss = _parse_prefixed_lines(run_text, "private_cnss_daemon.")
    sampler = manifest.get("response_sampler") or {}
    current_route = {
        "private_flag_in_child_script": 1 if PRIVATE_CNSS_FLAG in child_script else 0,
        "private_path_in_child_script": 1 if PRIVATE_CNSS_PATH in child_script else 0,
        "esoc_dev_node_flag_in_child_script": 1 if ESOC_DEV_NODE_FLAG in child_script else 0,
        "helper_marker": HELPER_MARKER,
        "helper_sha256": HELPER_SHA256,
        "private_cnss_path": PRIVATE_CNSS_PATH,
        "private_cnss_sha256": PRIVATE_CNSS_SHA256,
        "timing_progress": _timing_progress(sampler),
        "timing_safety_clear": _timing_safety_clear(sampler),
    }
    manifest["cycle"] = CYCLE_LABEL
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["private_cnss_daemon"] = private_cnss
    manifest["current_route"] = current_route
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["credential_use_executed"] = False
    manifest["dhcp_route_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["flash_executed"] = False
    manifest["partition_write_executed"] = False
    decision, passed, reason, next_step = decide_v1345(manifest)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    })
    return manifest


def _key_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    sampler = manifest.get("response_sampler") or {}
    private_cnss = manifest.get("private_cnss_daemon") or {}
    route = manifest.get("current_route") or {}
    return [
        ["private_flag_in_child_script", route.get("private_flag_in_child_script")],
        ["private_cnss_bind_rc", private_cnss.get("bind_rc")],
        ["private_cnss_expected_c_string", private_cnss.get("expected_c_string")],
        ["timing_sample_count", sampler.get("timing_sample_count")],
        ["timing_pm_service_powerup_seen", sampler.get("timing_pm_service_powerup_seen")],
        ["timing_gpio142_irq_delta", sampler.get("timing_gpio142_irq_delta")],
        ["timing_errfatal_irq_delta", sampler.get("timing_errfatal_irq_delta")],
        ["timing_pcie_rc1_transition_seen", sampler.get("timing_pcie_rc1_transition_seen")],
        ["timing_pcie1_gdsc_seen", sampler.get("timing_pcie1_gdsc_seen")],
        ["timing_pcie1_gdsc_nonzero_seen", sampler.get("timing_pcie1_gdsc_nonzero_seen")],
        ["timing_pcie1_gdsc_initial", sampler.get("timing_pcie1_gdsc_initial")],
        ["timing_pcie1_gdsc_last", sampler.get("timing_pcie1_gdsc_last")],
        ["timing_pcie1_clkref_seen", sampler.get("timing_pcie1_clkref_seen")],
        ["timing_pcie1_clkref_initial", sampler.get("timing_pcie1_clkref_initial")],
        ["timing_pcie1_clkref_last", sampler.get("timing_pcie1_clkref_last")],
        ["timing_pcie1_phy_refgen_seen", sampler.get("timing_pcie1_phy_refgen_seen")],
        ["timing_pcie1_phy_refgen_initial", sampler.get("timing_pcie1_phy_refgen_initial")],
        ["timing_pcie1_phy_refgen_last", sampler.get("timing_pcie1_phy_refgen_last")],
        ["timing_pcie1_pipe_clk_seen", sampler.get("timing_pcie1_pipe_clk_seen")],
        ["timing_pcie1_pipe_clk_initial", sampler.get("timing_pcie1_pipe_clk_initial")],
        ["timing_pcie1_pipe_clk_last", sampler.get("timing_pcie1_pipe_clk_last")],
        ["timing_gpio102_perst_seen", sampler.get("timing_gpio102_perst_seen")],
        ["timing_gpio102_perst_initial", sampler.get("timing_gpio102_perst_initial")],
        ["timing_gpio102_perst_last", sampler.get("timing_gpio102_perst_last")],
        ["timing_gpio103_clkreq_seen", sampler.get("timing_gpio103_clkreq_seen")],
        ["timing_gpio103_clkreq_initial", sampler.get("timing_gpio103_clkreq_initial")],
        ["timing_gpio103_clkreq_last", sampler.get("timing_gpio103_clkreq_last")],
        ["timing_gpio104_wake_seen", sampler.get("timing_gpio104_wake_seen")],
        ["timing_gpio104_wake_initial", sampler.get("timing_gpio104_wake_initial")],
        ["timing_gpio104_wake_last", sampler.get("timing_gpio104_wake_last")],
        ["timing_pci_dev_max", sampler.get("timing_pci_dev_max")],
        ["timing_mhi_bus_max", sampler.get("timing_mhi_bus_max")],
        ["timing_mhi_pipe_seen", sampler.get("timing_mhi_pipe_seen")],
        ["timing_mhi_pipe_fd_max", sampler.get("timing_mhi_pipe_fd_max")],
        ["timing_ks_process_max", sampler.get("timing_ks_process_max")],
        ["timing_wlfw_kmsg_max", sampler.get("timing_wlfw_kmsg_max")],
        ["timing_wlan0_seen", sampler.get("timing_wlan0_seen")],
        ["timing_safety_clear", route.get("timing_safety_clear")],
    ]


def _cleanup_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    reboot_cleanup = ((manifest.get("analysis") or {}).get("global_firmware") or {}).get("reboot_cleanup") or {}
    selftest = next((step for step in manifest.get("steps", []) if step.get("name") == "global-selftest"), {})
    status = next((step for step in manifest.get("steps", []) if step.get("name") == "global-status"), {})
    debugfs = manifest.get("debugfs_observer") or {}
    return [
        ["debugfs_mounted_before", debugfs.get("mounted_before")],
        ["debugfs_mounted_by_cycle", debugfs.get("mounted_by_cycle")],
        ["debugfs_cleanup_attempted", debugfs.get("cleanup_attempted")],
        ["debugfs_mounted_after", debugfs.get("mounted_after")],
        ["reboot_cleanup_status_healthy", reboot_cleanup.get("status_healthy")],
        ["reboot_cleanup_version_seen", reboot_cleanup.get("version_seen")],
        ["reboot_cleanup_wait_sec", reboot_cleanup.get("wait_sec")],
        ["post_status_ok", status.get("ok")],
        ["post_selftest_ok", selftest.get("ok")],
        ["post_selftest_payload", str(selftest.get("payload", "")).strip()],
    ]


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        f"# {REPORT_TITLE}",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE_NAME}`",
        "- Type: bounded live lower-response timing sampler",
        f"- Decision: `{manifest.get('decision', '')}`",
        f"- Result: {'PASS' if manifest.get('pass') else 'FAIL'}",
        "- Evidence:",
        f"  - `{DEFAULT_OUT_DIR}/manifest.json`",
        f"  - `{DEFAULT_OUT_DIR}/summary.md`",
        f"- Script: `{SCRIPT_PATH}`",
        f"- Helper: `/cache/bin/a90_android_execns_probe` (`{HELPER_MARKER}`)",
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
        "## Cleanup And Health",
        "",
        markdown_table(["field", "value"], _cleanup_rows(manifest)),
        "",
        "## Decision",
        "",
        str(manifest.get("reason", "")),
        "",
        f"{CYCLE_NAME} remains below Wi-Fi bring-up. It does not start Wi-Fi HAL, scan,",
        "connect, credential handling, DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        str(manifest.get("next_step", "")),
        "",
    ])


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        f"# {SUMMARY_HEADING}",
        "",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
    ])


def write_augmented_outputs(manifest: dict[str, Any]) -> None:
    out_dir = _run_dir()
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    if manifest.get("command") == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))


def print_v1345_result(manifest: dict[str, Any]) -> None:
    print(f"{CYCLE_LABEL}_decision: {manifest.get('decision')}")
    print(f"{CYCLE_LABEL}_pass: {manifest.get('pass')}")
    print(f"{CYCLE_LABEL}_reason: {manifest.get('reason')}")
    print(f"{CYCLE_LABEL}_next: {manifest.get('next_step')}")
    print(f"{CYCLE_LABEL}_manifest: {_run_dir() / 'manifest.json'}")


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
    write_augmented_outputs(manifest)
    print_v1345_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
