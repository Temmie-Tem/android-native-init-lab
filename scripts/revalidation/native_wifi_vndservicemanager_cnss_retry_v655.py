#!/usr/bin/env python3
"""V655 service-74 gated vndservicemanager readiness + CNSS retry proof.

This proof reuses the V644 clean-DSP preflight and helper v106's service-74
gated vndservicemanager-readiness plus fresh cnss-daemon retry mode. It does
not write DSP boot nodes, open esoc0, write qcwlanstate, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_clean_dsp_cnss_wlfw_readback_v644 as v644


base = v644.base

base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v655-vndservicemanager-cnss-retry")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "5492f3cc32087e4f589b816c8b0757edb5caa2e9b87f8c0fa7f4486f05fb63cb"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v106"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v655-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v655 vndservicemanager readiness plus cnss-daemon retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
V655_MODE = "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,cnss_daemon_retry"
)
MAX_CMDV1_COMMAND_ARGS = 30

V655_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_binder_ioctl_error", re.compile(r"cnss-daemon.*binder:.*ioctl .* returned -22", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("binder_transaction_failed", re.compile(r"binder: .*transaction failed|binder transaction failed", re.I)),
    ("binder_ioctl_unsupported", re.compile(r"binder: .*ioctl .* returned -22", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|\bwlfw_start\b", re.I)),
    ("wlfw_service_request", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put", re.I)),
)

_v644_capture_preflight = base.capture_preflight
_v644_build_checks = base.build_checks
_v644_companion_command = base.companion_command
_v644_run_live = base.run_live
_v644_render_summary = base.render_summary
_v644_build_manifest = base.build_manifest


def _remove_option_with_value(command: list[str], option: str) -> None:
    while True:
        try:
            index = command.index(option)
        except ValueError:
            return
        del command[index:index + 2]


def _set_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        command.extend([option, value])
    else:
        command[index + 1] = value


def _count(pattern: re.Pattern[str], text: str) -> int:
    return len([line for line in text.splitlines() if pattern.search(line)])


def v655_counts(text: str) -> dict[str, int]:
    return {name: _count(pattern, text) for name, pattern in V655_PATTERNS}


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _v644_capture_preflight(args, store, steps)
    if args.command != "plan":
        base.run_step(args, store, steps, "stat-real-ld-config", ["stat", REAL_LD_CONFIG], 10.0)
        base.run_step(args, store, steps, "stat-real-apex-libraries", ["stat", REAL_APEX_LIBRARIES], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v644_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    ld_text = base.step_payload(steps, "stat-real-ld-config")
    apex_text = base.step_payload(steps, "stat-real-apex-libraries")
    base.add_check(
        checks,
        "helper-v106-vndservicemanager-cnss-retry-ready",
        "pass"
        if (
            args.helper_sha256 in base.step_payload(steps, "sha-helper")
            and args.helper_marker in usage
            and V655_MODE in usage
            and "wifi_companion_start.vndservicemanager_readiness.ready" in usage
            and "wifi_companion_start.cnss_retry.initial_cleanup_safe" in usage
            and "--allow-service-manager-start-only" in usage
            and "--allow-qrtr-ns-readback" in usage
        )
        else "blocked",
        "blocker",
        "helper must expose v106 service74-gated vndservicemanager-readiness CNSS retry mode",
        [
            line
            for line in usage.splitlines()
            if V655_MODE in line
            or "a90_android_execns_probe v106" in line
            or "vndservicemanager_readiness" in line
            or "cnss_retry" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:10],
        "deploy helper v106 before V655",
    )
    base.add_check(
        checks,
        "real-linkerconfig-present",
        "pass" if "size=134256" in ld_text else "blocked",
        "blocker",
        f"path={REAL_LD_CONFIG}",
        [line for line in ld_text.splitlines() if "size=" in line or REAL_LD_CONFIG in line][:4],
        "restore Android-captured ld.config.txt before V655",
    )
    base.add_check(
        checks,
        "real-apex-libraries-present",
        "pass" if "size=366" in apex_text else "blocked",
        "blocker",
        f"path={REAL_APEX_LIBRARIES}",
        [line for line in apex_text.splitlines() if "size=" in line or REAL_APEX_LIBRARIES in line][:4],
        "restore Android-captured apex.libraries.config.txt before V655",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v644_companion_command(args)
    _set_option(command, "--mode", V655_MODE)
    _set_option(command, "--linkerconfig-mode", "copy-real")
    _remove_option_with_value(command, "--linkerconfig-source")
    _remove_option_with_value(command, "--apex-libraries-source")
    command.extend([
        "--linkerconfig-source", REAL_LD_CONFIG,
        "--apex-libraries-source", REAL_APEX_LIBRARIES,
    ])
    if base.approved(args) and "--allow-service-manager-start-only" not in command:
        command.append("--allow-service-manager-start-only")
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V655 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def _surface_summary(keys: dict[str, str], helper_text: str) -> dict[str, Any]:
    children = ("servicemanager", "hwservicemanager", "vndservicemanager", "cnss_daemon_retry")
    return {
        "order": keys.get("wifi_companion_start.order", ""),
        "with_service_manager": keys.get("wifi_companion_start.with_service_manager", ""),
        "with_vnd_service_manager": keys.get("wifi_companion_start.with_vnd_service_manager", ""),
        "service_manager_started": keys.get("wifi_companion_start.service_manager_started", ""),
        "linkerconfig_mode": "copy-real" if "linkerconfig_mode=copy-real" in helper_text else "",
        "service74_gate": {
            "enabled": keys.get("wifi_companion_start.service74_gate.enabled", ""),
            "baseline_syslog_available": keys.get("wifi_companion_start.service74_gate.baseline.syslog_available", ""),
            "baseline_count_74": keys.get("wifi_companion_start.service74_gate.baseline.count_74", ""),
            "final_count_74": keys.get("wifi_companion_start.service74_gate.final.count_74", ""),
            "wait_attempts": keys.get("wifi_companion_start.service74_gate.wait_attempts", ""),
            "wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
            "seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
            "status": keys.get("wifi_companion_start.service74_gate.status", ""),
            "open": keys.get("wifi_companion_start.service74_gate.open", ""),
        },
        "vndservicemanager_readiness": {
            "enabled": keys.get("wifi_companion_start.vndservicemanager_readiness.enabled", ""),
            "settle_ms": keys.get("wifi_companion_start.vndservicemanager_readiness.settle_ms", ""),
            "settle_done": keys.get("wifi_companion_start.vndservicemanager_readiness.settle_done", ""),
            "observable": keys.get("wifi_companion_start.vndservicemanager_readiness.observable", ""),
            "fd_summary_captured": keys.get("wifi_companion_start.vndservicemanager_readiness.fd_summary_captured", ""),
            "ready": keys.get("wifi_companion_start.vndservicemanager_readiness.ready", ""),
        },
        "cnss_retry": {
            "enabled": keys.get("wifi_companion_start.cnss_retry.enabled", ""),
            "initial_index": keys.get("wifi_companion_start.cnss_retry.initial_index", ""),
            "initial_observable": keys.get("wifi_companion_start.cnss_retry.initial_observable", ""),
            "initial_cleanup_safe": keys.get("wifi_companion_start.cnss_retry.initial_cleanup_safe", ""),
            "retry_start_order": keys.get("wifi_companion_start.child.cnss_daemon_retry.start_order", ""),
            "retry_observable": keys.get("wifi_companion_start.child.cnss_daemon_retry.observable", ""),
            "retry_postflight_safe": keys.get("wifi_companion_start.child.cnss_daemon_retry.postflight_safe", ""),
        },
        "children": {
            name: {
                "observable": keys.get(f"wifi_companion_start.child.{name}.observable", ""),
                "exited": keys.get(f"wifi_companion_start.child.{name}.exited", ""),
                "exit_code": keys.get(f"wifi_companion_start.child.{name}.exit_code", ""),
                "signal": keys.get(f"wifi_companion_start.child.{name}.signal", ""),
                "postflight_safe": keys.get(f"wifi_companion_start.child.{name}.postflight_safe", ""),
            }
            for name in children
        },
    }


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _v644_run_live(args, store, steps, mount_preflight)
    helper_text = base.step_payload(steps, "companion-start-only-with-holder")
    keys = result.get("companion_keys") or {}
    result["helper_stdout_stderr"] = helper_text
    result["v655_surface"] = _surface_summary(keys, helper_text)
    result["v655_counts"] = v655_counts(str(result.get("dmesg_delta") or ""))
    return result


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v655-vndservicemanager-cnss-retry-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V641/V490 prerequisites, then run V655 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v655-vndservicemanager-cnss-retry-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V655", False
    if args.command == "preflight":
        return (
            "v655-vndservicemanager-cnss-retry-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V655 live proof",
            False,
        )
    if not base.approved(args):
        return "v655-vndservicemanager-cnss-retry-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V655 approval", False
    if not live:
        return "v655-vndservicemanager-cnss-retry-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v655-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v655-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V655 retry", True
    if not live.get("companion_executed") or not live.get("all_postflight_safe"):
        return "v655-cleanup-review", False, f"helper_result={live.get('helper_result')} all_postflight_safe={live.get('all_postflight_safe')}", "inspect companion transcript before retry", True

    surface = live.get("v655_surface") or {}
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    cnss_retry = surface.get("cnss_retry") or {}
    counts = live.get("v655_counts") or {}
    service_manager_executed = (
        surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("order") == EXPECTED_ORDER
        and surface.get("service_manager_started") == "1"
    )
    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v655-service74-gate-timeout",
            True,
            (
                f"gate_status={service74_gate.get('status')} "
                f"baseline_74={service74_gate.get('baseline_count_74')} "
                f"final_74={service74_gate.get('final_count_74')} "
                f"wait_ms={service74_gate.get('wait_ms')}"
            ),
            "service-manager/CNSS retry was correctly withheld; classify lower service74 regression before retry",
            True,
        )
    if not service_manager_executed:
        return "v655-service-manager-not-executed", False, f"surface={surface}", "inspect helper mode and approval propagation", True
    if vnd_ready.get("ready") != "1":
        return (
            "v655-vndservicemanager-readiness-blocked",
            True,
            f"vndservicemanager_readiness={vnd_ready}",
            "vndservicemanager was started but readiness was not proven; inspect helper fd/process capture before retry",
            True,
        )
    if cnss_retry.get("initial_cleanup_safe") != "1" or not cnss_retry.get("retry_start_order"):
        return (
            "v655-cnss-retry-not-executed",
            True,
            f"cnss_retry={cnss_retry}",
            "fresh cnss-daemon retry was withheld; inspect initial cleanup/readiness guard before retry",
            True,
        )
    if _int_count(counts.get("wlfw_start")) > 0 or _int_count(counts.get("wlfw_service_request")) > 0:
        return (
            "v655-cnss-retry-wlfw-advanced",
            True,
            f"counts={counts}",
            "classify WLFW/BDF state before any Wi-Fi HAL or scan/connect gate",
            True,
        )
    if _int_count(counts.get("cnss_binder_transaction_failed")) > 0:
        return (
            "v655-cnss-retry-binder-loop-persists",
            True,
            f"fresh cnss retry executed but binder transaction failure persisted; counts={counts}",
            "classify vndservicemanager context-manager readiness or missing vendor binder service registration before HAL",
            True,
        )
    return (
        "v655-vndservicemanager-cnss-retry-review-required",
        False,
        f"unclassified counts={counts} surface={surface}",
        "inspect dmesg and helper transcript before retry",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v644_render_summary(manifest).replace(
        "# V644 Clean-DSP CNSS/WLFW Readback Proof",
        "# V655 vndservicemanager Readiness + CNSS Retry Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v655_surface") or {}
    children = surface.get("children") or {}
    child_rows = [
        [
            name,
            values.get("observable", ""),
            values.get("exited", ""),
            values.get("exit_code", ""),
            values.get("signal", ""),
            values.get("postflight_safe", ""),
        ]
        for name, values in sorted(children.items())
    ]
    counts = live.get("v655_counts") or {}
    return "\n".join([
        text,
        "",
        "## V655 Gate And Retry Surface",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- with_service_manager: `{surface.get('with_service_manager', '')}`",
        f"- with_vnd_service_manager: `{surface.get('with_vnd_service_manager', '')}`",
        f"- service_manager_started: `{surface.get('service_manager_started', '')}`",
        f"- linkerconfig_mode: `{surface.get('linkerconfig_mode', '')}`",
        "",
        "## V655 Service74 Gate",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted((surface.get("service74_gate") or {}).items())],
        ) if surface.get("service74_gate") else "- none",
        "",
        "## V655 vndservicemanager Readiness",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted((surface.get("vndservicemanager_readiness") or {}).items())],
        ) if surface.get("vndservicemanager_readiness") else "- none",
        "",
        "## V655 CNSS Retry",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted((surface.get("cnss_retry") or {}).items())],
        ) if surface.get("cnss_retry") else "- none",
        "",
        base.markdown_table(
            ["child", "observable", "exited", "exit_code", "signal", "postflight_safe"],
            child_rows,
        ) if child_rows else "- none",
        "",
        "## V655 Counts",
        "",
        base.markdown_table(["name", "count"], [[key, str(value)] for key, value in sorted(counts.items())]) if counts else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v644_build_manifest(args, store)
    live = manifest.get("live") or {}
    surface = live.get("v655_surface") or {}
    service_manager_executed = (
        bool(live.get("companion_executed"))
        and surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("service_manager_started") == "1"
    )
    manifest["service_manager_start_executed"] = service_manager_executed
    manifest["copy_real_linkerconfig_executed"] = bool(live) and surface.get("linkerconfig_mode") == "copy-real"
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and retry cnss-daemon start-only inside bounded private namespace",
        "service74-gated vndservicemanager readiness and fresh cnss-daemon binder attempt under V641 clean-DSP state",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
