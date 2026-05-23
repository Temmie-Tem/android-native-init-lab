#!/usr/bin/env python3
"""V671 service74-gated Android userspace-order start-only proof.

This proof extends the V668 service74-positive focused capture path by starting
the Android-like userspace surface before the fresh cnss-daemon retry:
service-manager trio, Wi-Fi HAL legacy/ext, and wificond. It still does not
start supplicant, scan/connect, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_cnss2_focused_capture_v668 as v668


base = v668.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v671-service74-android-userspace")
base.DEFAULT_HELPER_SHA256 = "1c65e1b766b85fda7629d9d7067047d8e0322d412447cf731ccab65a70655d88"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v111"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v666-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v671 service74 Android userspace-order start-only proof only; "
    "no supplicant, no scan/connect/link-up, no DHCP and no external ping"
)

V671_MODE = "wifi-companion-service74-gated-android-userspace-cnss-retry-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "wifi_hal_legacy,wifi_hal_ext,wificond,cnss_daemon_retry"
)
MAX_CMDV1_COMMAND_ARGS = 30
V671_TOKENS = (
    "a90_android_execns_probe v111",
    V671_MODE,
    "--allow-wifi-hal-start-only",
    "wifi_companion_start.android_userspace_order.enabled=%d",
    "wifi_hal_legacy",
    "wifi_hal_ext",
    "wificond",
    "wifi_companion_start.supplicant=0",
    "wifi_companion_start.scan_connect_linkup=0",
    "wifi_companion_start.external_ping=0",
)
V671_USAGE_TOKENS = (
    V671_MODE,
    "--allow-wifi-hal-start-only",
)

_v668_build_checks = base.build_checks
_v668_companion_command = base.companion_command
_v668_run_live = base.run_live
_v668_render_summary = base.render_summary
_v668_build_manifest = base.build_manifest


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


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v668.v666._merged_helper_keys(live)


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _android_userspace_surface(keys: dict[str, str]) -> dict[str, Any]:
    children = ("wifi_hal_legacy", "wifi_hal_ext", "wificond", "cnss_daemon_retry")
    return {
        "order": keys.get("wifi_companion_start.order", ""),
        "android_userspace_enabled": keys.get("wifi_companion_start.android_userspace_order.enabled", ""),
        "wifi_hal": keys.get("wifi_companion_start.wifi_hal", ""),
        "wificond": keys.get("wifi_companion_start.wificond", ""),
        "service74_gate": {
            "seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
            "open": keys.get("wifi_companion_start.service74_gate.open", ""),
            "status": keys.get("wifi_companion_start.service74_gate.status", ""),
            "wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
        },
        "vndservicemanager_readiness": {
            "ready": keys.get("wifi_companion_start.vndservicemanager_readiness.ready", ""),
            "observable": keys.get("wifi_companion_start.vndservicemanager_readiness.observable", ""),
        },
        "cnss_retry": {
            "enabled": keys.get("wifi_companion_start.cnss_retry.enabled", ""),
            "initial_cleanup_safe": keys.get("wifi_companion_start.cnss_retry.initial_cleanup_safe", ""),
            "retry_start_order": keys.get("wifi_companion_start.child.cnss_daemon_retry.start_order", ""),
            "retry_observable": keys.get("wifi_companion_start.child.cnss_daemon_retry.observable", ""),
            "retry_postflight_safe": keys.get("wifi_companion_start.child.cnss_daemon_retry.postflight_safe", ""),
        },
        "children": {
            name: {
                "start_order": keys.get(f"wifi_companion_start.child.{name}.start_order", ""),
                "observable": keys.get(f"wifi_companion_start.child.{name}.observable", ""),
                "exited": keys.get(f"wifi_companion_start.child.{name}.exited", ""),
                "exit_code": keys.get(f"wifi_companion_start.child.{name}.exit_code", ""),
                "signal": keys.get(f"wifi_companion_start.child.{name}.signal", ""),
                "postflight_safe": keys.get(f"wifi_companion_start.child.{name}.postflight_safe", ""),
            }
            for name in children
        },
        "result": keys.get("wifi_companion_start.result", ""),
        "reason": keys.get("wifi_companion_start.reason", ""),
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
        "all_observable": keys.get("wifi_companion_start.all_observable", ""),
    }


def _advanced(counts: dict[str, Any]) -> bool:
    return any(_int_count(counts.get(name)) > 0 for name in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ))


def _all_android_userspace_children_started(surface: dict[str, Any]) -> bool:
    children = surface.get("children") or {}
    return all((children.get(name) or {}).get("start_order") for name in (
        "wifi_hal_legacy",
        "wifi_hal_ext",
        "wificond",
        "cnss_daemon_retry",
    ))


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v668_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and all(token in usage for token in V671_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v111-service74-android-userspace-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v111 service74-gated Android userspace-order start-only mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V671_MODE in line
            or "--allow-wifi-hal-start-only" in line
            or "android_userspace_order" in line
            or "wifi_hal_legacy" in line
            or "wifi_hal_ext" in line
            or "wificond" in line
        ][:14],
        "deploy helper v111 before V671 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v668_companion_command(args)
    _set_option(command, "--mode", V671_MODE)
    _remove_option_with_value(command, "--null-device-mode")
    if base.approved(args) and "--allow-wifi-hal-start-only" not in command:
        command.append("--allow-wifi-hal-start-only")
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V671 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v668_run_live(args, store, steps, mount_preflight)
    keys = _keys(live)
    live["v671_android_userspace_surface"] = _android_userspace_surface(keys)
    live["v671_android_userspace_children_started"] = _all_android_userspace_children_started(
        live["v671_android_userspace_surface"]
    )
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v671-service74-android-userspace-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v111, refresh current-boot prerequisites, then run V671 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v671-service74-android-userspace-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V671", False
    if args.command == "preflight":
        return (
            "v671-service74-android-userspace-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V671 live proof",
            False,
        )
    if not base.approved(args):
        return "v671-service74-android-userspace-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V671 approval", False
    if not live:
        return "v671-service74-android-userspace-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v671-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v671-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V671", True
    if not live.get("companion_executed"):
        return "v671-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", True

    surface = live.get("v671_android_userspace_surface") or {}
    counts = live.get("v655_counts") or {}
    service74_gate = surface.get("service74_gate") or {}
    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v671-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "Android userspace-order services were correctly withheld; classify lower service74 regression",
            True,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("android_userspace_enabled") != "1":
        return (
            "v671-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v111 order contract before another live attempt",
            True,
        )
    if not live.get("v671_android_userspace_children_started"):
        return (
            "v671-android-userspace-not-started",
            False,
            f"surface={surface}",
            "inspect helper v111 child startup before retrying live",
            True,
        )
    if not live.get("all_postflight_safe"):
        return (
            "v671-cleanup-review",
            False,
            f"helper_result={live.get('helper_result')} surface={surface}",
            "inspect helper transcript before another live mutation",
            True,
        )
    if _advanced(counts):
        return (
            "v671-android-userspace-wifi-surface-advanced",
            True,
            f"Android userspace-order start-only advanced lower Wi-Fi markers; counts={counts}; surface={surface}",
            "classify WLFW/BDF/wlan0 state before supplicant or scan/connect",
            True,
        )
    return (
        "v671-android-userspace-no-wlfw-advance",
        True,
        f"HAL legacy/ext, wificond, and CNSS retry executed but WLFW/BDF/wlan0 remain absent; counts={counts}; surface={surface}",
        "inspect HAL/wificond runtime output and binder/pm_qos deltas before enabling supplicant or IWifi.start",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V671 Service74 Android Userspace-order Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v671_android_userspace_surface") or {}
    children = surface.get("children") or {}
    child_rows = [
        [
            name,
            values.get("start_order", ""),
            values.get("observable", ""),
            values.get("exit_code", ""),
            values.get("signal", ""),
            values.get("postflight_safe", ""),
        ]
        for name, values in sorted(children.items())
    ]
    return "\n".join([
        text,
        "",
        "## V671 Android Userspace-order Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{V671_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- android_userspace_enabled: `{surface.get('android_userspace_enabled', '')}`",
        f"- wifi_hal_start_requested: `{manifest.get('wifi_hal_start_requested')}`",
        f"- wifi_hal_start_executed: `{manifest.get('wifi_hal_start_executed')}`",
        f"- wificond_start_requested: `{manifest.get('wificond_start_requested')}`",
        f"- wificond_start_executed: `{manifest.get('wificond_start_executed')}`",
        "- Supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(
            ["child", "start_order", "observable", "exit_code", "signal", "postflight_safe"],
            child_rows,
        ) if child_rows else "- no child surface captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v668_build_manifest(args, store)
    live = manifest.get("live") or {}
    surface = live.get("v671_android_userspace_surface") or {}
    children = surface.get("children") or {}
    manifest["cycle"] = "v671"
    manifest["helper_version"] = "v111"
    manifest["android_userspace_mode"] = V671_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["android_userspace_surface"] = surface
    manifest["android_userspace_children_started"] = bool(live.get("v671_android_userspace_children_started")) if live else False
    manifest["wifi_hal_start_requested"] = bool(live and surface.get("wifi_hal") == "2")
    manifest["wificond_start_requested"] = bool(live and surface.get("wificond") == "1")
    manifest["wifi_hal_start_executed"] = bool(
        live
        and (
            (children.get("wifi_hal_legacy") or {}).get("start_order")
            or (children.get("wifi_hal_ext") or {}).get("start_order")
        )
    )
    manifest["wificond_start_executed"] = bool(
        live and (children.get("wificond") or {}).get("start_order")
    )
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v111 service74-gated Android userspace-order start-only mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "Wi-Fi HAL legacy/ext and wificond start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V317 private property root bind and property service shim inside helper namespace",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "sysfs writes or subsystem state writes",
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "supplicant or hostapd start",
        "IWifi.start transaction, qcwlanstate, or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
