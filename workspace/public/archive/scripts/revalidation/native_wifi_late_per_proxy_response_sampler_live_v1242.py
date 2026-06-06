#!/usr/bin/env python3
"""V1242: late per_proxy eSoC response sampler.

This follows V1238 and keeps the same bounded actor sequence:

    service managers -> pm_proxy_helper -> per_mgr -> cnss-daemon -> mdm_helper
    -> late per_proxy after mdm_helper holds /dev/esoc-0

It adds the v258 helper response sampler around the late per_proxy trigger.
The sampler records GPIO142 IRQ count, pinctrl ownership/configuration, PCIe,
MHI, and wlan0 observer fields.  It may temporarily mount debugfs for
read-only pinctrl/PCIe observation, then unmount it if this script mounted it.

It must not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, send ESOC_NOTIFY, send ESOC_BOOT_DONE, write
boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_late_per_proxy_only_live_v1238 as v1238


DEFAULT_OUT_DIR = Path("tmp/wifi/v1242-late-per-proxy-response-sampler-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1242-late-per-proxy-response-sampler-live.txt")
HELPER_MARKER = "a90_android_execns_probe v258"
HELPER_SHA256 = "dd9bee9e2c0750c51be2151dd4b192d0612dd9269419c1641b9395d7336b6119"
RESPONSE_SAMPLER_FLAG = "--pm-observer-late-per-proxy-response-sampler"
DEBUGFS_ROOT = "/sys/kernel/debug"
CYCLE_LABEL = "v1242"
CYCLE_NAME = "V1242"
SUMMARY_HEADING = "V1242 Late per_proxy Response Sampler"
EVIDENCE_FILE_PREFIX = "v1242"

SAMPLE_PREFIX = "pm_service_trigger_observer.response_sample."
SAMPLER_PREFIX = "pm_service_trigger_observer.response_sampler."
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def _parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def _decision(suffix: str) -> str:
    return f"{CYCLE_LABEL}-{suffix}"


def _force_response_sampler_child_command(original):
    def command(args: Any) -> list[str]:
        result = original(args)
        if RESPONSE_SAMPLER_FLAG not in result:
            result.append(RESPONSE_SAMPLER_FLAG)
        return result

    return command


def patch_defaults() -> tuple[Any, Any]:
    v1238.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1238.LATEST_POINTER = LATEST_POINTER
    v1238.HELPER_MARKER = HELPER_MARKER
    v1238.HELPER_SHA256 = HELPER_SHA256
    v1165, v1106 = v1238.patch_defaults()
    wrapped = _force_response_sampler_child_command(v1238.v1237.v1106_mod.pm_cnss_child_command)
    v1106.pm_cnss_child_command = wrapped
    v1238.v1237.v1106_mod.pm_cnss_child_command = wrapped
    for module in [v1106, v1238.v1237.v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER
    return v1165, v1106


def _device_step(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float = 20.0,
    allow_error: bool = False,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    hide_item: dict[str, Any] | None = None
    if not capture.ok and "[busy]" in payload:
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(timeout, 8.0))
        hide_payload = strip_cmdv1_text(hide_capture.text) if hide_capture.text else hide_capture.error + "\n"
        hide_item = capture_to_manifest(hide_capture)
        hide_item["payload"] = hide_payload
        hide_item["file"] = f"native/{EVIDENCE_FILE_PREFIX}-{name}-hide-on-busy.txt"
        hide_item["ok"] = hide_capture.ok
        hide_item["raw_ok"] = hide_capture.ok
        store.write_text(hide_item["file"], hide_payload.rstrip() + "\n")
        capture = run_capture(args, name, command, timeout=timeout)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["payload"] = payload
    item["ok"] = bool(capture.ok or allow_error)
    item["raw_ok"] = bool(capture.ok)
    item["file"] = f"native/{EVIDENCE_FILE_PREFIX}-{name}.txt"
    if hide_item is not None:
        item["hide_on_busy"] = hide_item
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def _debugfs_mounted(payload: str) -> bool:
    return " /sys/kernel/debug " in payload and " debugfs " in payload


def _shell_cmd(args: Any, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def prepare_debugfs(args: Any, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    before = _device_step(
        args,
        store,
        steps,
        "debugfs-mounts-before",
        _shell_cmd(args, f"{args.busybox} cat /proc/mounts | {args.busybox} grep ' /sys/kernel/debug ' || true"),
        timeout=12.0,
        allow_error=True,
    )
    mounted_before = _debugfs_mounted(before.get("payload", ""))
    mounted_by_cycle = False
    if not mounted_before:
        mount = _device_step(
            args,
            store,
            steps,
            "debugfs-mount",
            _shell_cmd(args, f"{args.busybox} mkdir -p {DEBUGFS_ROOT}; {args.busybox} mount -t debugfs debugfs {DEBUGFS_ROOT}"),
            timeout=20.0,
            allow_error=False,
        )
        mounted_by_cycle = bool(mount.get("raw_ok"))
    during = _device_step(
        args,
        store,
        steps,
        "debugfs-mounts-during",
        _shell_cmd(args, f"{args.busybox} cat /proc/mounts | {args.busybox} grep ' /sys/kernel/debug ' || true"),
        timeout=12.0,
        allow_error=True,
    )
    return {
        "steps": steps,
        "mounted_before": mounted_before,
        "mounted_by_cycle": mounted_by_cycle,
        "mounted_during": _debugfs_mounted(during.get("payload", "")),
        "cleanup_attempted": False,
        "mounted_after": None,
    }


def cleanup_debugfs(args: Any, store: EvidenceStore, debugfs: dict[str, Any]) -> None:
    steps = debugfs.setdefault("steps", [])
    if debugfs.get("mounted_by_cycle", debugfs.get("mounted_by_v1242")):
        debugfs["cleanup_attempted"] = True
        _device_step(
            args,
            store,
            steps,
            "debugfs-umount",
            _shell_cmd(args, f"{args.busybox} umount {DEBUGFS_ROOT}"),
            timeout=20.0,
            allow_error=True,
        )
    after = _device_step(
        args,
        store,
        steps,
        "debugfs-mounts-after",
        _shell_cmd(args, f"{args.busybox} cat /proc/mounts | {args.busybox} grep ' /sys/kernel/debug ' || true"),
        timeout=12.0,
        allow_error=True,
    )
    debugfs["mounted_after"] = _debugfs_mounted(after.get("payload", ""))


def _read_run_text(manifest: dict[str, Any]) -> str:
    return v1238._read_run_text(manifest)


def _collect_response_samples(text: str) -> dict[str, Any]:
    keys = _parse_keys(text)
    sampler = {
        key[len(SAMPLER_PREFIX):]: value
        for key, value in keys.items()
        if key.startswith(SAMPLER_PREFIX)
    }
    samples: dict[str, dict[str, str]] = {}
    for key, value in keys.items():
        if not key.startswith(SAMPLE_PREFIX):
            continue
        rest = key[len(SAMPLE_PREFIX):]
        if "." not in rest:
            continue
        phase, field = rest.split(".", 1)
        samples.setdefault(phase, {})[field] = value

    phase_rows: list[dict[str, Any]] = []
    for phase in sorted(samples):
        sample = samples[phase]
        phase_rows.append({
            "phase": phase,
            "monotonic_ms": _int_value(sample.get("monotonic_ms"), -1),
            "mdm_status_irq_present": _int_value(sample.get("mdm_status_irq_present"), -1),
            "mdm_status_irq_parsed": _int_value(sample.get("mdm_status_irq_parsed"), -1),
            "mdm_status_gpio": _int_value(sample.get("mdm_status_gpio"), -1),
            "mdm_status_count_total": _int_value(sample.get("mdm_status_count_total"), -1),
            "mdm3_state": sample.get("mdm3_state", ""),
            "mdm3_crash_count": sample.get("mdm3_crash_count", ""),
            "debugfs_pinctrl_present": _int_value(sample.get("debugfs_pinctrl_present"), -1),
            "debugfs_gpio_present": _int_value(sample.get("debugfs_gpio_present"), -1),
            "pin135_seen": _int_value(sample.get("pin135_seen"), -1),
            "pin135_source": sample.get("pin135_source", ""),
            "pin135_line": sample.get("pin135_line", ""),
            "pin142_seen": _int_value(sample.get("pin142_seen"), -1),
            "pin142_source": sample.get("pin142_source", ""),
            "pin142_line": sample.get("pin142_line", ""),
            "pmic9_seen": _int_value(sample.get("pmic9_seen"), -1),
            "pmic9_line": sample.get("pmic9_line", ""),
            "pmic9_source": sample.get("pmic9_source", ""),
            "pmic_soft_reset_seen": _int_value(sample.get("pmic_soft_reset_seen"), -1),
            "pmic_soft_reset_line": sample.get("pmic_soft_reset_line", ""),
            "pmic_soft_reset_source": sample.get("pmic_soft_reset_source", ""),
            "debugfs_regulator_present": _int_value(sample.get("debugfs_regulator_present"), -1),
            "pcie1_gdsc_seen": _int_value(sample.get("pcie1_gdsc_seen"), -1),
            "pcie1_gdsc_line": sample.get("pcie1_gdsc_line", ""),
            "pcie1_gdsc_source": sample.get("pcie1_gdsc_source", ""),
            "pcie0_gdsc_seen": _int_value(sample.get("pcie0_gdsc_seen"), -1),
            "pcie0_gdsc_line": sample.get("pcie0_gdsc_line", ""),
            "pcie0_gdsc_source": sample.get("pcie0_gdsc_source", ""),
            "pmic_gpio1270_debugfs_seen": _int_value(sample.get("pmic_gpio1270_debugfs_seen"), -1),
            "pmic_gpio1270_debugfs_line": sample.get("pmic_gpio1270_debugfs_line", ""),
            "pmic_gpio1270_debugfs_source": sample.get("pmic_gpio1270_debugfs_source", ""),
            "tlmm_gpio135_debugfs_seen": _int_value(sample.get("tlmm_gpio135_debugfs_seen"), -1),
            "tlmm_gpio135_debugfs_line": sample.get("tlmm_gpio135_debugfs_line", ""),
            "tlmm_gpio135_debugfs_source": sample.get("tlmm_gpio135_debugfs_source", ""),
            "tlmm_gpio142_debugfs_seen": _int_value(sample.get("tlmm_gpio142_debugfs_seen"), -1),
            "tlmm_gpio142_debugfs_line": sample.get("tlmm_gpio142_debugfs_line", ""),
            "tlmm_gpio142_debugfs_source": sample.get("tlmm_gpio142_debugfs_source", ""),
            "pmic_gpio1270_debugfs_block_seen": _int_value(sample.get("pmic_gpio1270_debugfs_block_seen"), -1),
            "pmic_gpio1270_debugfs_block": sample.get("pmic_gpio1270_debugfs_block", ""),
            "pmic_gpio1270_debugfs_block_source": sample.get("pmic_gpio1270_debugfs_block_source", ""),
            "tlmm_gpio135_debugfs_block_seen": _int_value(sample.get("tlmm_gpio135_debugfs_block_seen"), -1),
            "tlmm_gpio135_debugfs_block": sample.get("tlmm_gpio135_debugfs_block", ""),
            "tlmm_gpio135_debugfs_block_source": sample.get("tlmm_gpio135_debugfs_block_source", ""),
            "tlmm_gpio142_debugfs_block_seen": _int_value(sample.get("tlmm_gpio142_debugfs_block_seen"), -1),
            "tlmm_gpio142_debugfs_block": sample.get("tlmm_gpio142_debugfs_block", ""),
            "tlmm_gpio142_debugfs_block_source": sample.get("tlmm_gpio142_debugfs_block_source", ""),
            "tlmm_gpio135_debugfs_range_block_seen": _int_value(sample.get("tlmm_gpio135_debugfs_range_block_seen"), -1),
            "tlmm_gpio135_debugfs_range_block": sample.get("tlmm_gpio135_debugfs_range_block", ""),
            "tlmm_gpio135_debugfs_range_block_source": sample.get("tlmm_gpio135_debugfs_range_block_source", ""),
            "tlmm_gpio135_debugfs_range_start": _int_value(sample.get("tlmm_gpio135_debugfs_range_start"), -1),
            "tlmm_gpio135_debugfs_range_end": _int_value(sample.get("tlmm_gpio135_debugfs_range_end"), -1),
            "tlmm_gpio142_debugfs_range_block_seen": _int_value(sample.get("tlmm_gpio142_debugfs_range_block_seen"), -1),
            "tlmm_gpio142_debugfs_range_block": sample.get("tlmm_gpio142_debugfs_range_block", ""),
            "tlmm_gpio142_debugfs_range_block_source": sample.get("tlmm_gpio142_debugfs_range_block_source", ""),
            "tlmm_gpio142_debugfs_range_start": _int_value(sample.get("tlmm_gpio142_debugfs_range_start"), -1),
            "tlmm_gpio142_debugfs_range_end": _int_value(sample.get("tlmm_gpio142_debugfs_range_end"), -1),
            "tlmm_gpio135_debugfs_target_line_seen": _int_value(sample.get("tlmm_gpio135_debugfs_target_line_seen"), -1),
            "tlmm_gpio135_debugfs_target_line": sample.get("tlmm_gpio135_debugfs_target_line", ""),
            "tlmm_gpio142_debugfs_target_line_seen": _int_value(sample.get("tlmm_gpio142_debugfs_target_line_seen"), -1),
            "tlmm_gpio142_debugfs_target_line": sample.get("tlmm_gpio142_debugfs_target_line", ""),
            "tlmm_gpio135_debugfs_target_block_seen": _int_value(sample.get("tlmm_gpio135_debugfs_target_block_seen"), -1),
            "tlmm_gpio135_debugfs_target_block": sample.get("tlmm_gpio135_debugfs_target_block", ""),
            "tlmm_gpio142_debugfs_target_block_seen": _int_value(sample.get("tlmm_gpio142_debugfs_target_block_seen"), -1),
            "tlmm_gpio142_debugfs_target_block": sample.get("tlmm_gpio142_debugfs_target_block", ""),
            "pmic9_pinconf_seen": _int_value(sample.get("pmic9_pinconf_seen"), -1),
            "pmic9_pinconf_line": sample.get("pmic9_pinconf_line", ""),
            "pmic9_pinconf_source": sample.get("pmic9_pinconf_source", ""),
            "pin135_pinconf_seen": _int_value(sample.get("pin135_pinconf_seen"), -1),
            "pin135_pinconf_line": sample.get("pin135_pinconf_line", ""),
            "pin135_pinconf_source": sample.get("pin135_pinconf_source", ""),
            "pin142_pinconf_seen": _int_value(sample.get("pin142_pinconf_seen"), -1),
            "pin142_pinconf_line": sample.get("pin142_pinconf_line", ""),
            "pin142_pinconf_source": sample.get("pin142_pinconf_source", ""),
            "pmic9_pinconf_block_seen": _int_value(sample.get("pmic9_pinconf_block_seen"), -1),
            "pmic9_pinconf_block": sample.get("pmic9_pinconf_block", ""),
            "pmic9_pinconf_block_source": sample.get("pmic9_pinconf_block_source", ""),
            "pin135_pinconf_block_seen": _int_value(sample.get("pin135_pinconf_block_seen"), -1),
            "pin135_pinconf_block": sample.get("pin135_pinconf_block", ""),
            "pin135_pinconf_block_source": sample.get("pin135_pinconf_block_source", ""),
            "pin142_pinconf_block_seen": _int_value(sample.get("pin142_pinconf_block_seen"), -1),
            "pin142_pinconf_block": sample.get("pin142_pinconf_block", ""),
            "pin142_pinconf_block_source": sample.get("pin142_pinconf_block_source", ""),
            "pcie_current_link_state": sample.get("pcie_current_link_state", ""),
            "pcie_link_state": sample.get("pcie_link_state", ""),
            "pcie_runtime_status": sample.get("pcie_runtime_status", ""),
            "pcie_l23_rdy_poll_timeout": sample.get("pcie_l23_rdy_poll_timeout", ""),
            "pci_dev_count": _int_value(sample.get("pci_dev_count"), -1),
            "mhi_bus_count": _int_value(sample.get("mhi_bus_count"), -1),
            "mhi_pipe_exists": _int_value(sample.get("mhi_pipe_exists"), -1),
            "wlan0_exists": _int_value(sample.get("wlan0_exists"), -1),
            "kmsg_open_ok": _int_value(sample.get("kmsg_open_ok"), -1),
            "kmsg_source": sample.get("kmsg_source", ""),
            "kmsg_open_errno": _int_value(sample.get("kmsg_open_errno"), -1),
            "kmsg_lines_read": _int_value(sample.get("kmsg_lines_read"), -1),
            "kmsg_filtered_count": _int_value(sample.get("kmsg_filtered_count"), -1),
            "kmsg_pcie_count": _int_value(sample.get("kmsg_pcie_count"), -1),
            "kmsg_gdsc_count": _int_value(sample.get("kmsg_gdsc_count"), -1),
            "kmsg_mhi_count": _int_value(sample.get("kmsg_mhi_count"), -1),
            "kmsg_esoc_count": _int_value(sample.get("kmsg_esoc_count"), -1),
            "kmsg_mdm_count": _int_value(sample.get("kmsg_mdm_count"), -1),
            "kmsg_sdx50m_count": _int_value(sample.get("kmsg_sdx50m_count"), -1),
            "kmsg_icnss_count": _int_value(sample.get("kmsg_icnss_count"), -1),
            "kmsg_wlfw_count": _int_value(sample.get("kmsg_wlfw_count"), -1),
            "kmsg_subsys_count": _int_value(sample.get("kmsg_subsys_count"), -1),
            "kmsg_filtered_block": sample.get("kmsg_filtered_block", ""),
            "gpiochip_lineinfo_attempted": _int_value(sample.get("gpiochip_lineinfo_attempted"), -1),
            "gpiochip_lineinfo_expected_dev": _int_value(sample.get("gpiochip_lineinfo_expected_dev"), -1),
            "gpiochip_lineinfo_expected_label": _int_value(sample.get("gpiochip_lineinfo_expected_label"), -1),
            "gpiochip_lineinfo_expected_base": _int_value(sample.get("gpiochip_lineinfo_expected_base"), -1),
            "gpiochip_lineinfo_expected_ngpio": _int_value(sample.get("gpiochip_lineinfo_expected_ngpio"), -1),
            "gpiochip_lineinfo_mknod_ok": _int_value(sample.get("gpiochip_lineinfo_mknod_ok"), -1),
            "gpiochip_lineinfo_open_ok": _int_value(sample.get("gpiochip_lineinfo_open_ok"), -1),
            "gpiochip_lineinfo_ok": _int_value(sample.get("gpiochip_lineinfo_ok"), -1),
            "gpiochip_lineinfo_cleanup_ok": _int_value(sample.get("gpiochip_lineinfo_cleanup_ok"), -1),
            "gpiochip_lineinfo_line_offset": _int_value(sample.get("gpiochip_lineinfo_line_offset"), -1),
            "gpiochip_lineinfo_line_flags": sample.get("gpiochip_lineinfo_line_flags", ""),
            "gpiochip_lineinfo_flag_kernel": _int_value(sample.get("gpiochip_lineinfo_flag_kernel"), -1),
            "gpiochip_lineinfo_flag_is_out": _int_value(sample.get("gpiochip_lineinfo_flag_is_out"), -1),
            "gpiochip_lineinfo_line_name": sample.get("gpiochip_lineinfo_line_name", ""),
            "gpiochip_lineinfo_line_consumer": sample.get("gpiochip_lineinfo_line_consumer", ""),
            "gpiochip_line_request_executed": _int_value(sample.get("gpiochip_line_request_executed"), -1),
            "pmic_write_executed": _int_value(sample.get("pmic_write_executed"), -1),
            "esoc_ioctl_executed": _int_value(sample.get("esoc_ioctl_executed"), -1),
        })
    phase_rows.sort(key=lambda row: (row["monotonic_ms"] < 0, row["monotonic_ms"], row["phase"]))

    return {
        "emitted": sampler.get("begin") == "1" or bool(phase_rows),
        "ended": sampler.get("end") == "1",
        "mode": sampler.get("mode", ""),
        "sample_interval_ms": _int_value(sampler.get("sample_interval_ms"), -1),
        "sample_count": len(phase_rows),
        "phases": [row["phase"] for row in phase_rows],
        "max_mdm_status_count_total": max((row["mdm_status_count_total"] for row in phase_rows), default=-1),
        "max_mhi_bus_count": max((row["mhi_bus_count"] for row in phase_rows), default=-1),
        "max_pci_dev_count": max((row["pci_dev_count"] for row in phase_rows), default=-1),
        "mhi_pipe_seen": any(row["mhi_pipe_exists"] > 0 for row in phase_rows),
        "wlan0_seen": any(row["wlan0_exists"] > 0 for row in phase_rows),
        "kmsg_open_seen": any(row["kmsg_open_ok"] > 0 for row in phase_rows),
        "kmsg_sources": sorted({row["kmsg_source"] for row in phase_rows if row["kmsg_source"]}),
        "max_kmsg_lines_read": max((row["kmsg_lines_read"] for row in phase_rows), default=-1),
        "max_kmsg_filtered_count": max((row["kmsg_filtered_count"] for row in phase_rows), default=-1),
        "max_kmsg_pcie_count": max((row["kmsg_pcie_count"] for row in phase_rows), default=-1),
        "max_kmsg_gdsc_count": max((row["kmsg_gdsc_count"] for row in phase_rows), default=-1),
        "max_kmsg_mhi_count": max((row["kmsg_mhi_count"] for row in phase_rows), default=-1),
        "max_kmsg_esoc_count": max((row["kmsg_esoc_count"] for row in phase_rows), default=-1),
        "max_kmsg_mdm_count": max((row["kmsg_mdm_count"] for row in phase_rows), default=-1),
        "max_kmsg_sdx50m_count": max((row["kmsg_sdx50m_count"] for row in phase_rows), default=-1),
        "max_kmsg_icnss_count": max((row["kmsg_icnss_count"] for row in phase_rows), default=-1),
        "max_kmsg_wlfw_count": max((row["kmsg_wlfw_count"] for row in phase_rows), default=-1),
        "max_kmsg_subsys_count": max((row["kmsg_subsys_count"] for row in phase_rows), default=-1),
        "pin135_seen": any(row["pin135_seen"] > 0 for row in phase_rows),
        "pin142_seen": any(row["pin142_seen"] > 0 for row in phase_rows),
        "debugfs_pinctrl_seen": any(row["debugfs_pinctrl_present"] > 0 for row in phase_rows),
        "debugfs_gpio_seen": any(row["debugfs_gpio_present"] > 0 for row in phase_rows),
        "debugfs_regulator_seen": any(row["debugfs_regulator_present"] > 0 for row in phase_rows),
        "pmic_soft_reset_seen": any(row["pmic_soft_reset_seen"] > 0 for row in phase_rows),
        "pcie1_gdsc_seen": any(row["pcie1_gdsc_seen"] > 0 for row in phase_rows),
        "pcie0_gdsc_seen": any(row["pcie0_gdsc_seen"] > 0 for row in phase_rows),
        "pmic_gpio1270_debugfs_seen": any(row["pmic_gpio1270_debugfs_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_seen": any(row["tlmm_gpio135_debugfs_seen"] > 0 for row in phase_rows),
        "tlmm_gpio142_debugfs_seen": any(row["tlmm_gpio142_debugfs_seen"] > 0 for row in phase_rows),
        "pmic_gpio1270_debugfs_block_seen": any(row["pmic_gpio1270_debugfs_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_block_seen": any(row["tlmm_gpio135_debugfs_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio142_debugfs_block_seen": any(row["tlmm_gpio142_debugfs_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_range_block_seen": any(row["tlmm_gpio135_debugfs_range_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio142_debugfs_range_block_seen": any(row["tlmm_gpio142_debugfs_range_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_range_windows": sorted({
            f"{row['tlmm_gpio135_debugfs_range_start']}-{row['tlmm_gpio135_debugfs_range_end']}"
            for row in phase_rows
            if row["tlmm_gpio135_debugfs_range_start"] >= 0 and row["tlmm_gpio135_debugfs_range_end"] >= 0
        }),
        "tlmm_gpio142_debugfs_range_windows": sorted({
            f"{row['tlmm_gpio142_debugfs_range_start']}-{row['tlmm_gpio142_debugfs_range_end']}"
            for row in phase_rows
            if row["tlmm_gpio142_debugfs_range_start"] >= 0 and row["tlmm_gpio142_debugfs_range_end"] >= 0
        }),
        "tlmm_gpio135_debugfs_target_line_seen": any(row["tlmm_gpio135_debugfs_target_line_seen"] > 0 for row in phase_rows),
        "tlmm_gpio142_debugfs_target_line_seen": any(row["tlmm_gpio142_debugfs_target_line_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_target_block_seen": any(row["tlmm_gpio135_debugfs_target_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio142_debugfs_target_block_seen": any(row["tlmm_gpio142_debugfs_target_block_seen"] > 0 for row in phase_rows),
        "tlmm_gpio135_debugfs_target_lines": sorted({
            row["tlmm_gpio135_debugfs_target_line"]
            for row in phase_rows
            if row["tlmm_gpio135_debugfs_target_line"]
        }),
        "tlmm_gpio142_debugfs_target_lines": sorted({
            row["tlmm_gpio142_debugfs_target_line"]
            for row in phase_rows
            if row["tlmm_gpio142_debugfs_target_line"]
        }),
        "pmic9_pinconf_seen": any(row["pmic9_pinconf_seen"] > 0 for row in phase_rows),
        "pin135_pinconf_seen": any(row["pin135_pinconf_seen"] > 0 for row in phase_rows),
        "pin142_pinconf_seen": any(row["pin142_pinconf_seen"] > 0 for row in phase_rows),
        "pmic9_pinconf_block_seen": any(row["pmic9_pinconf_block_seen"] > 0 for row in phase_rows),
        "pin135_pinconf_block_seen": any(row["pin135_pinconf_block_seen"] > 0 for row in phase_rows),
        "pin142_pinconf_block_seen": any(row["pin142_pinconf_block_seen"] > 0 for row in phase_rows),
        "gpiochip_lineinfo_seen": any(row["gpiochip_lineinfo_ok"] > 0 for row in phase_rows),
        "gpiochip_lineinfo_kernel_owned_seen": any(row["gpiochip_lineinfo_flag_kernel"] > 0 for row in phase_rows),
        "gpiochip_lineinfo_ap2mdm_consumer_seen": any(row["gpiochip_lineinfo_line_consumer"] == "AP2MDM_SOFT_RESET" for row in phase_rows),
        "gpiochip_lineinfo_zero_action_ok": all(
            row["gpiochip_line_request_executed"] in {-1, 0} and
            row["pmic_write_executed"] in {-1, 0} and
            row["esoc_ioctl_executed"] in {-1, 0}
            for row in phase_rows
        ),
        "samples": phase_rows,
    }


def decide_v1242(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("response-sampler-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            f"deploy {HELPER_MARKER}, then run {CYCLE_NAME} bounded response sampler",
        )

    pm = manifest.get("pm_service_trigger_observer") or {}
    sampler = manifest.get("response_sampler") or {}
    debugfs = manifest.get("debugfs_observer") or {}
    all_postflight_safe = _int_value(pm.get("all_postflight_safe"), 1)

    if not sampler.get("emitted") or sampler.get("sample_count", 0) <= 0:
        return (
            _decision("response-sampler-missing"),
            False,
            "v258 response sampler did not emit samples",
            "verify helper v258 deploy and command flag injection",
        )
    if not debugfs.get("mounted_during"):
        return (
            _decision("debugfs-not-mounted"),
            False,
            "debugfs was not mounted during the response sampler window",
            f"restore cleanup-safe debugfs mount path before retrying {CYCLE_NAME}",
        )

    progress = (
        sampler.get("max_mdm_status_count_total", 0) > 0 or
        sampler.get("max_mhi_bus_count", 0) > 0 or
        sampler.get("mhi_pipe_seen") or
        sampler.get("wlan0_seen")
    )
    if progress:
        return (
            _decision("pm-esoc0-trigger-response-progress"),
            True,
            "late per_proxy response sampler observed GPIO142/MHI/wlan0 progress",
            "preserve evidence and classify which response surface advanced before any Wi-Fi HAL/connect",
        )

    if pm.get("pm_service_actor_esoc0_attempt"):
        if all_postflight_safe <= 0:
            return (
                _decision("pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"),
                True,
                "pm-service reached /dev/subsys_esoc0 and sampler saw no GPIO142/MHI/wlan0 response; cleanup was not proven safe",
                "reboot/health-check, then classify SDX50M power/GPIO prerequisites",
            )
        return (
            _decision("pm-esoc0-trigger-sampled-mdm2ap-silent"),
            True,
            "pm-service reached /dev/subsys_esoc0 and sampler saw no GPIO142/MHI/wlan0 response",
            "classify SDX50M power/GPIO prerequisites before another trigger",
        )

    return (
        _decision("response-sampled-no-esoc0-trigger"),
        True,
        "response sampler ran, but pm-service /dev/subsys_esoc0 attempt was not observed",
        "inspect late per_proxy and pm-service Binder delivery before retrying response sampling",
    )


def _reanalyze_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest["_run_dir"] = manifest.get("_run_dir") or str(repo_path(DEFAULT_OUT_DIR))
    manifest["cycle"] = CYCLE_LABEL
    manifest["reclassified_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["based_on_cycle"] = "v1238"
    manifest["response_sampler_flag"] = RESPONSE_SAMPLER_FLAG

    base_manifest = v1238._reanalyze_manifest(manifest)
    base_manifest["cycle"] = CYCLE_LABEL
    base_manifest["helper_version"] = HELPER_MARKER
    base_manifest["helper_sha256"] = HELPER_SHA256
    base_manifest["based_on_cycle"] = "v1238"
    base_manifest["response_sampler_flag"] = RESPONSE_SAMPLER_FLAG

    run_text = _read_run_text(base_manifest)
    base_manifest["response_sampler"] = _collect_response_samples(run_text)
    decision, passed, reason, next_step = decide_v1242(base_manifest)
    base_manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return base_manifest


def _sample_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    sampler = manifest.get("response_sampler") or {}
    return [
        ["emitted", sampler.get("emitted")],
        ["ended", sampler.get("ended")],
        ["mode", sampler.get("mode")],
        ["sample_count", sampler.get("sample_count")],
        ["phases", ", ".join(sampler.get("phases") or [])],
        ["max_mdm_status_count_total", sampler.get("max_mdm_status_count_total")],
        ["max_pci_dev_count", sampler.get("max_pci_dev_count")],
        ["max_mhi_bus_count", sampler.get("max_mhi_bus_count")],
        ["mhi_pipe_seen", sampler.get("mhi_pipe_seen")],
        ["wlan0_seen", sampler.get("wlan0_seen")],
        ["kmsg_open_seen", sampler.get("kmsg_open_seen")],
        ["kmsg_sources", ", ".join(sampler.get("kmsg_sources") or [])],
        ["max_kmsg_filtered_count", sampler.get("max_kmsg_filtered_count")],
        ["max_kmsg_pcie_count", sampler.get("max_kmsg_pcie_count")],
        ["max_kmsg_gdsc_count", sampler.get("max_kmsg_gdsc_count")],
        ["max_kmsg_mhi_count", sampler.get("max_kmsg_mhi_count")],
        ["max_kmsg_esoc_count", sampler.get("max_kmsg_esoc_count")],
        ["max_kmsg_mdm_count", sampler.get("max_kmsg_mdm_count")],
        ["max_kmsg_sdx50m_count", sampler.get("max_kmsg_sdx50m_count")],
        ["max_kmsg_icnss_count", sampler.get("max_kmsg_icnss_count")],
        ["max_kmsg_wlfw_count", sampler.get("max_kmsg_wlfw_count")],
        ["max_kmsg_subsys_count", sampler.get("max_kmsg_subsys_count")],
        ["debugfs_pinctrl_seen", sampler.get("debugfs_pinctrl_seen")],
        ["debugfs_gpio_seen", sampler.get("debugfs_gpio_seen")],
        ["debugfs_regulator_seen", sampler.get("debugfs_regulator_seen")],
        ["pin135_seen", sampler.get("pin135_seen")],
        ["pin142_seen", sampler.get("pin142_seen")],
        ["pmic_soft_reset_seen", sampler.get("pmic_soft_reset_seen")],
        ["pcie1_gdsc_seen", sampler.get("pcie1_gdsc_seen")],
        ["pcie0_gdsc_seen", sampler.get("pcie0_gdsc_seen")],
        ["pmic_gpio1270_debugfs_seen", sampler.get("pmic_gpio1270_debugfs_seen")],
        ["tlmm_gpio135_debugfs_seen", sampler.get("tlmm_gpio135_debugfs_seen")],
        ["tlmm_gpio142_debugfs_seen", sampler.get("tlmm_gpio142_debugfs_seen")],
        ["pmic_gpio1270_debugfs_block_seen", sampler.get("pmic_gpio1270_debugfs_block_seen")],
        ["tlmm_gpio135_debugfs_block_seen", sampler.get("tlmm_gpio135_debugfs_block_seen")],
        ["tlmm_gpio142_debugfs_block_seen", sampler.get("tlmm_gpio142_debugfs_block_seen")],
        ["tlmm_gpio135_debugfs_range_block_seen", sampler.get("tlmm_gpio135_debugfs_range_block_seen")],
        ["tlmm_gpio135_debugfs_range_windows", ", ".join(sampler.get("tlmm_gpio135_debugfs_range_windows") or [])],
        ["tlmm_gpio142_debugfs_range_block_seen", sampler.get("tlmm_gpio142_debugfs_range_block_seen")],
        ["tlmm_gpio142_debugfs_range_windows", ", ".join(sampler.get("tlmm_gpio142_debugfs_range_windows") or [])],
        ["tlmm_gpio135_debugfs_target_line_seen", sampler.get("tlmm_gpio135_debugfs_target_line_seen")],
        ["tlmm_gpio135_debugfs_target_lines", " ; ".join(sampler.get("tlmm_gpio135_debugfs_target_lines") or [])],
        ["tlmm_gpio142_debugfs_target_line_seen", sampler.get("tlmm_gpio142_debugfs_target_line_seen")],
        ["tlmm_gpio142_debugfs_target_lines", " ; ".join(sampler.get("tlmm_gpio142_debugfs_target_lines") or [])],
        ["tlmm_gpio135_debugfs_target_block_seen", sampler.get("tlmm_gpio135_debugfs_target_block_seen")],
        ["tlmm_gpio142_debugfs_target_block_seen", sampler.get("tlmm_gpio142_debugfs_target_block_seen")],
        ["pmic9_pinconf_seen", sampler.get("pmic9_pinconf_seen")],
        ["pin135_pinconf_seen", sampler.get("pin135_pinconf_seen")],
        ["pin142_pinconf_seen", sampler.get("pin142_pinconf_seen")],
        ["pmic9_pinconf_block_seen", sampler.get("pmic9_pinconf_block_seen")],
        ["pin135_pinconf_block_seen", sampler.get("pin135_pinconf_block_seen")],
        ["pin142_pinconf_block_seen", sampler.get("pin142_pinconf_block_seen")],
        ["gpiochip_lineinfo_seen", sampler.get("gpiochip_lineinfo_seen")],
        ["gpiochip_lineinfo_kernel_owned_seen", sampler.get("gpiochip_lineinfo_kernel_owned_seen")],
        ["gpiochip_lineinfo_ap2mdm_consumer_seen", sampler.get("gpiochip_lineinfo_ap2mdm_consumer_seen")],
        ["gpiochip_lineinfo_zero_action_ok", sampler.get("gpiochip_lineinfo_zero_action_ok")],
    ]


def _debugfs_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    debugfs = manifest.get("debugfs_observer") or {}
    return [
        ["mounted_before", debugfs.get("mounted_before")],
        ["mounted_by_cycle", debugfs.get("mounted_by_cycle", debugfs.get("mounted_by_v1242"))],
        ["mounted_during", debugfs.get("mounted_during")],
        ["cleanup_attempted", debugfs.get("cleanup_attempted")],
        ["mounted_after", debugfs.get("mounted_after")],
    ]


def _render_summary(manifest: dict[str, Any]) -> str:
    pm = manifest.get("pm_service_trigger_observer") or {}
    safety_rows = [
        ["wifi_hal_start_executed", manifest.get("wifi_hal_start_executed")],
        ["scan_connect_executed", manifest.get("scan_connect_executed")],
        ["credential_use_executed", manifest.get("credential_use_executed")],
        ["dhcp_route_executed", manifest.get("dhcp_route_executed")],
        ["external_ping_executed", manifest.get("external_ping_executed")],
        ["wifi_bringup_executed", manifest.get("wifi_bringup_executed")],
        ["flash_executed", manifest.get("flash_executed")],
        ["partition_write_executed", manifest.get("partition_write_executed")],
    ]
    return "\n".join([
        f"# {SUMMARY_HEADING}",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## Response Sampler",
        "",
        markdown_table(["field", "value"], _sample_rows(manifest)),
        "",
        "## PM Trigger",
        "",
        markdown_table(["field", "value"], [
            ["pm_service_actor_esoc0_attempt", pm.get("pm_service_actor_esoc0_attempt")],
            ["late_per_proxy_started", pm.get("late_per_proxy_started")],
            ["late_per_proxy_poll_count", pm.get("late_per_proxy_poll_count")],
            ["all_postflight_safe", pm.get("all_postflight_safe")],
            ["pm_result", pm.get("result")],
            ["pm_reason", pm.get("reason")],
        ]),
        "",
        "## Debugfs Observer",
        "",
        markdown_table(["field", "value"], _debugfs_rows(manifest)),
        "",
        "## Safety Audit",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def _print_result(manifest: dict[str, Any]) -> None:
    sampler = manifest.get("response_sampler") or {}
    pm = manifest.get("pm_service_trigger_observer") or {}
    debugfs = manifest.get("debugfs_observer") or {}
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print()
    print(f"sample_count:             {sampler.get('sample_count')}")
    print(f"max_mdm_status_count:     {sampler.get('max_mdm_status_count_total')}")
    print(f"max_mhi_bus_count:        {sampler.get('max_mhi_bus_count')}")
    print(f"mhi_pipe_seen:            {sampler.get('mhi_pipe_seen')}")
    print(f"wlan0_seen:               {sampler.get('wlan0_seen')}")
    print(f"kmsg_open_seen:           {sampler.get('kmsg_open_seen')}")
    print(f"max_kmsg_pcie_count:      {sampler.get('max_kmsg_pcie_count')}")
    print(f"max_kmsg_mhi_count:       {sampler.get('max_kmsg_mhi_count')}")
    print(f"max_kmsg_wlfw_count:      {sampler.get('max_kmsg_wlfw_count')}")
    print(f"debugfs_pinctrl_seen:     {sampler.get('debugfs_pinctrl_seen')}")
    print(f"debugfs_gpio_seen:        {sampler.get('debugfs_gpio_seen')}")
    print(f"pmic_gpio1270_seen:       {sampler.get('pmic_gpio1270_debugfs_seen')}")
    print(f"pmic_gpio1270_block_seen: {sampler.get('pmic_gpio1270_debugfs_block_seen')}")
    print(f"tlmm135_range_block_seen: {sampler.get('tlmm_gpio135_debugfs_range_block_seen')}")
    print(f"tlmm142_range_block_seen: {sampler.get('tlmm_gpio142_debugfs_range_block_seen')}")
    print(f"pmic9_pinconf_seen:       {sampler.get('pmic9_pinconf_seen')}")
    print(f"pmic9_pinconf_block_seen: {sampler.get('pmic9_pinconf_block_seen')}")
    print(f"gpiochip_lineinfo_seen:   {sampler.get('gpiochip_lineinfo_seen')}")
    print(f"lineinfo_kernel_owned:    {sampler.get('gpiochip_lineinfo_kernel_owned_seen')}")
    print(f"lineinfo_ap2mdm_consumer: {sampler.get('gpiochip_lineinfo_ap2mdm_consumer_seen')}")
    print(f"lineinfo_zero_action_ok:  {sampler.get('gpiochip_lineinfo_zero_action_ok')}")
    print(f"pm_service_esoc0_attempt: {pm.get('pm_service_actor_esoc0_attempt')}")
    print(f"late_per_proxy_started:   {pm.get('late_per_proxy_started')}")
    print(f"debugfs_mounted_during:   {debugfs.get('mounted_during')}")
    print(f"debugfs_mounted_after:    {debugfs.get('mounted_after')}")
    print(f"evidence: {manifest.get('_run_dir')}")


def reclassify_existing() -> int:
    manifest_path = repo_path(DEFAULT_OUT_DIR / "manifest.json")
    if not manifest_path.exists():
        print(f"error: missing existing {CYCLE_NAME} manifest: {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print(f"error: manifest is not an object: {manifest_path}", file=sys.stderr)
        return 2
    manifest["command"] = "run"
    manifest = _reanalyze_manifest(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (repo_path(DEFAULT_OUT_DIR) / "summary.md").write_text(_render_summary(manifest), encoding="utf-8")
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(DEFAULT_OUT_DIR)) + "\n")
    _print_result(manifest)
    return 0 if manifest.get("pass") else 1


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "reclassify":
        return reclassify_existing()

    v1165, v1106 = patch_defaults()
    args = v1106.parse_args()
    if args.command == "run":
        args.allow_tracefs_mount = True
        args.allow_tracefs_write = True
        args.allow_vendor_mount = True
        args.allow_selinuxfs_mount = True
        args.allow_pm_service_trigger_observer = True
        args.allow_cnss_daemon_start = True
        args.assume_yes = True
    if args.helper_timeout_sec == 4:
        args.helper_timeout_sec = 30
    if args.toybox_timeout_sec == 18:
        args.toybox_timeout_sec = 90
    if args.tracefs_duration_sec == 18:
        args.tracefs_duration_sec = 95
    if args.thread_sample_count == 80:
        args.thread_sample_count = 260
    v1165.v1143.v1139.v1113.set_global_defaults(args)

    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    debugfs: dict[str, Any] = {
        "steps": [],
        "mounted_before": None,
        "mounted_by_cycle": False,
        "mounted_during": None,
        "cleanup_attempted": False,
        "mounted_after": None,
    }
    if args.command == "run":
        debugfs = prepare_debugfs(args, store)

    try:
        manifest = v1106.build_manifest(args, store)
    finally:
        if args.command == "run":
            cleanup_debugfs(args, store, debugfs)

    manifest["command"] = args.command
    manifest["cycle"] = CYCLE_LABEL
    manifest["generated_at"] = _now_iso()
    manifest["_run_dir"] = str(store.run_dir)
    manifest["debugfs_observer"] = debugfs
    manifest = _reanalyze_manifest(manifest)
    manifest["debugfs_observer"] = debugfs

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    _print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
