#!/usr/bin/env python3
"""V652 service-74 binder parity proof.

This proof reuses the V644 clean-DSP preflight and current helper v104's
CNSS-first delayed service-manager mode. It does not write DSP boot nodes,
open esoc0, write qcwlanstate, start Wi-Fi HAL, scan/connect, use credentials,
run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_clean_dsp_cnss_wlfw_readback_v644 as v644


base = v644.base

base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v652-service74-binder-parity")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v104"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v652-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v652 service74 binder parity proof only; "
    "no DSP boot-node write, no esoc0 open, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
CNSS_FIRST_DELAYED_MODE = "wifi-companion-cnss-first-delayed-vnd-service-manager-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "servicemanager,hwservicemanager,vndservicemanager"
)
MAX_CMDV1_COMMAND_ARGS = 30

V652_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
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


def v652_counts(text: str) -> dict[str, int]:
    return {name: _count(pattern, text) for name, pattern in V652_PATTERNS}


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
        "helper-v104-cnss-first-service-manager-ready",
        "pass"
        if (
            args.helper_sha256 in base.step_payload(steps, "sha-helper")
            and args.helper_marker in usage
            and CNSS_FIRST_DELAYED_MODE in usage
            and "--allow-service-manager-start-only" in usage
            and "--allow-qrtr-ns-readback" in usage
        )
        else "blocked",
        "blocker",
        "helper must expose v104 CNSS-first delayed service-manager mode",
        [
            line
            for line in usage.splitlines()
            if CNSS_FIRST_DELAYED_MODE in line
            or "a90_android_execns_probe v104" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:8],
        "deploy helper v104 before V652",
    )
    base.add_check(
        checks,
        "real-linkerconfig-present",
        "pass" if "size=134256" in ld_text else "blocked",
        "blocker",
        f"path={REAL_LD_CONFIG}",
        [line for line in ld_text.splitlines() if "size=" in line or REAL_LD_CONFIG in line][:4],
        "restore Android-captured ld.config.txt before V652",
    )
    base.add_check(
        checks,
        "real-apex-libraries-present",
        "pass" if "size=366" in apex_text else "blocked",
        "blocker",
        f"path={REAL_APEX_LIBRARIES}",
        [line for line in apex_text.splitlines() if "size=" in line or REAL_APEX_LIBRARIES in line][:4],
        "restore Android-captured apex.libraries.config.txt before V652",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v644_companion_command(args)
    _set_option(command, "--mode", CNSS_FIRST_DELAYED_MODE)
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
        raise RuntimeError(f"V652 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def _service_manager_summary(keys: dict[str, str], helper_text: str) -> dict[str, Any]:
    children = ("servicemanager", "hwservicemanager", "vndservicemanager")
    return {
        "order": keys.get("wifi_companion_start.order", ""),
        "with_service_manager": keys.get("wifi_companion_start.with_service_manager", ""),
        "with_vnd_service_manager": keys.get("wifi_companion_start.with_vnd_service_manager", ""),
        "linkerconfig_mode": "copy-real" if "linkerconfig_mode=copy-real" in helper_text else "",
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
    result["service_manager"] = _service_manager_summary(keys, helper_text)
    result["v652_counts"] = v652_counts(str(result.get("dmesg_delta") or ""))
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
            "v652-service74-binder-parity-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V490/runtime prerequisites, then run V652 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v652-service74-binder-parity-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V652", False
    if args.command == "preflight":
        return (
            "v652-service74-binder-parity-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V652 live proof",
            False,
        )
    if not base.approved(args):
        return "v652-service74-binder-parity-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V652 approval", False
    if not live:
        return "v652-service74-binder-parity-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v652-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v652-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V652 retry", True
    if not live.get("companion_executed") or not live.get("all_postflight_safe"):
        return "v652-cleanup-review", False, f"helper_result={live.get('helper_result')} all_postflight_safe={live.get('all_postflight_safe')}", "inspect companion transcript before retry", True

    service_manager = live.get("service_manager") or {}
    counts = live.get("v652_counts") or {}
    service_manager_executed = (
        service_manager.get("with_service_manager") == "1"
        and service_manager.get("with_vnd_service_manager") == "1"
        and service_manager.get("order") == EXPECTED_ORDER
    )
    if not service_manager_executed:
        return "v652-service-manager-not-executed", False, f"service_manager={service_manager}", "inspect helper mode and approval propagation", True
    if _int_count(counts.get("service_notifier_74")) == 0:
        return (
            "v652-service74-regressed",
            True,
            f"service_notifier_180={counts.get('service_notifier_180', 0)} service_notifier_74=0",
            "do not widen scope; implement explicit service74-gated helper mode if delayed service-manager regresses lower publication",
            True,
        )
    if _int_count(counts.get("wlfw_start")) > 0 or _int_count(counts.get("wlfw_service_request")) > 0:
        return (
            "v652-service74-binder-parity-wlfw-advanced",
            True,
            f"counts={counts}",
            "classify WLFW/BDF state before any Wi-Fi HAL or scan/connect gate",
            True,
        )
    if _int_count(counts.get("cnss_binder_transaction_failed")) > 0:
        return (
            "v652-binder-loop-persists",
            True,
            f"service74 preserved but cnss binder transaction failures persisted; counts={counts}",
            "inspect service-manager namespace/SELinux/property mismatch before another live retry",
            True,
        )
    if _int_count(counts.get("binder_transaction_failed")) == 0:
        return (
            "v652-service74-binder-clean-wlfw-missing",
            True,
            f"service74 preserved and binder transactions clean but WLFW missing; counts={counts}",
            "classify missing WLFW service registration after binder-clean service74 path",
            True,
        )
    return (
        "v652-service74-binder-parity-review-required",
        False,
        f"unclassified counts={counts}",
        "inspect dmesg and helper transcript before retry",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v644_render_summary(manifest).replace(
        "# V644 Clean-DSP CNSS/WLFW Readback Proof",
        "# V652 Service-74 Binder Parity Proof",
        1,
    )
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    children = service_manager.get("children") or {}
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
    counts = live.get("v652_counts") or {}
    return "\n".join([
        text,
        "",
        "## V652 Service-Manager Surface",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{service_manager.get('order', '')}`",
        f"- with_service_manager: `{service_manager.get('with_service_manager', '')}`",
        f"- with_vnd_service_manager: `{service_manager.get('with_vnd_service_manager', '')}`",
        f"- linkerconfig_mode: `{service_manager.get('linkerconfig_mode', '')}`",
        "",
        base.markdown_table(
            ["child", "observable", "exited", "exit_code", "signal", "postflight_safe"],
            child_rows,
        ) if child_rows else "- none",
        "",
        "## V652 Counts",
        "",
        base.markdown_table(["name", "count"], [[key, str(value)] for key, value in sorted(counts.items())]) if counts else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v644_build_manifest(args, store)
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    service_manager_executed = (
        bool(live.get("companion_executed"))
        and service_manager.get("with_service_manager") == "1"
        and service_manager.get("with_vnd_service_manager") == "1"
    )
    manifest["service_manager_start_executed"] = service_manager_executed
    manifest["copy_real_linkerconfig_executed"] = bool(live) and service_manager.get("linkerconfig_mode") == "copy-real"
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, cnss-daemon start-only inside bounded private namespace",
        "CNSS-first delayed service-manager companion ordering under V641 clean-DSP state",
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
