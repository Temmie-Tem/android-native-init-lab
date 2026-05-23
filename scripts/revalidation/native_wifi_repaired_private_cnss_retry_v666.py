#!/usr/bin/env python3
"""V666 repaired private runtime fresh cnss-daemon retry proof.

This proof reruns the V660/V655 service-74 gated vndservicemanager readiness
plus fresh cnss-daemon retry path with helper v109 and the V665-repaired
private property/runtime surface. It does not write DSP boot nodes, open esoc0,
write qcwlanstate, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_vndservicemanager_cnss_retry_v655 as v655


base = v655.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v666-repaired-private-cnss-retry")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "eda3e88405d15cfa2b12ef3252cef3ff25ba23aae69aeb5075700fa147150030"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v109"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v666-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v666 repaired private cnss-daemon retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
V666_MODE = v655.V655_MODE
EXPECTED_ORDER = v655.EXPECTED_ORDER
MAX_CMDV1_COMMAND_ARGS = 30
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

_v655_capture_preflight = v655.capture_preflight
_v655_build_checks = v655.build_checks
_v655_companion_command = v655.companion_command
_v655_run_live = v655.run_live
_v655_decide = v655.decide
_v655_render_summary = v655.render_summary
_v655_build_manifest = v655.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V655", "V666")
        .replace("v655", "v666")
        .replace("helper v106", "helper v109")
        .replace("helper-v106", "helper-v109")
        .replace("a90_android_execns_probe v106", "a90_android_execns_probe v109")
        .replace("vndservicemanager readiness plus CNSS retry", "repaired private runtime CNSS retry")
        .replace("vndservicemanager Readiness + CNSS Retry", "Repaired Private Runtime CNSS Retry")
        .replace("vndservicemanager readiness plus cnss-daemon retry", "repaired private cnss-daemon retry")
    )


def _rename_check(check: base.Check) -> base.Check:
    return base.Check(
        _rewrite_text(check.name),
        check.status,
        check.severity,
        _rewrite_text(check.detail),
        [_rewrite_text(item) for item in check.evidence],
        _rewrite_text(check.next_step),
    )


def _keys_from_helper_text(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def _merged_helper_keys(live: dict[str, Any]) -> dict[str, str]:
    helper_text = str(live.get("helper_stdout_stderr") or "")
    return {**(live.get("companion_keys") or {}), **_keys_from_helper_text(helper_text)}


def _private_runtime_surface(live: dict[str, Any]) -> dict[str, Any]:
    keys = _merged_helper_keys(live)
    return {
        "property_root": PROPERTY_ROOT,
        "context_dev_properties_exists": keys.get("context.dev_properties.exists", ""),
        "context_dev_properties_access_r": keys.get("context.dev_properties.access_r", ""),
        "context_dev_properties_access_x": keys.get("context.dev_properties.access_x", ""),
        "context_dev_properties_host_path": keys.get("context.dev_properties.host_path", ""),
        "context_dev_socket_exists": keys.get("context.dev_socket.exists", ""),
        "context_dev_socket_access_x": keys.get("context.dev_socket.access_x", ""),
        "property_service_shim_mode": keys.get("wifi_hal_composite_start.property_service_shim.mode", ""),
        "property_service_shim_started": keys.get("wifi_hal_composite_start.property_service_shim.started", ""),
        "property_service_socket": keys.get("wifi_hal_composite_start.property_service_shim.socket", ""),
        "property_service_shim_child_started": keys.get("wifi_hal_composite_start.property_service_shim.child_started", ""),
        "property_service_shim_request_count": keys.get("wifi_hal_composite_start.property_service_shim.request_count", ""),
        "property_service_shim_postflight_safe": keys.get("wifi_hal_composite_start.property_service_shim.postflight_safe", ""),
    }


def _private_runtime_ready(surface: dict[str, Any]) -> bool:
    return (
        surface.get("context_dev_properties_exists") == "1"
        and surface.get("context_dev_properties_access_r") == "1"
        and surface.get("context_dev_properties_access_x") == "1"
        and surface.get("property_service_shim_started") == "1"
        and surface.get("property_service_socket") == "/dev/socket/property_service"
        and surface.get("property_service_shim_postflight_safe") == "1"
    )


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _v655_capture_preflight(args, store, steps)
    if args.command != "plan":
        base.run_step(args, store, steps, "stat-property-root", ["run", args.toybox, "stat", PROPERTY_ROOT], 10.0)
        base.run_step(args, store, steps, "ls-property-root", ["run", args.toybox, "ls", "-ld", PROPERTY_ROOT], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [_rename_check(check) for check in _v655_build_checks(args, steps, mount_preflight, v490, v525)]
    if args.command == "plan":
        return checks

    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    stat_text = base.step_payload(steps, "stat-property-root")
    ls_text = base.step_payload(steps, "ls-property-root")

    base.add_check(
        checks,
        "helper-v109-repaired-private-cnss-retry-contract",
        "pass"
        if (
            args.helper_sha256 in sha_text
            and args.helper_marker in usage
            and V666_MODE in usage
            and "--property-root" in usage
            and "--allow-service-manager-start-only" in usage
            and "--allow-qrtr-ns-readback" in usage
        )
        else "blocked",
        "blocker",
        "remote helper must expose v109 service74-gated CNSS retry mode plus property-root support",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V666_MODE in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:10],
        "deploy helper v109 before V666",
    )
    base.add_check(
        checks,
        "v317-private-property-root-present",
        "pass" if PROPERTY_ROOT in stat_text and "No such file" not in stat_text else "blocked",
        "blocker",
        f"property_root={PROPERTY_ROOT}",
        [line for line in (stat_text + "\n" + ls_text).splitlines() if PROPERTY_ROOT in line or "property" in line][:8],
        "restore V317 private property root before V666",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v655_companion_command(args)
    if "--property-root" not in command:
        command.extend(["--property-root", PROPERTY_ROOT])
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V666 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v655_run_live(args, store, steps, mount_preflight)
    live["v666_private_runtime_surface"] = _private_runtime_surface(live)
    live["v666_private_runtime_ready"] = _private_runtime_ready(live["v666_private_runtime_surface"])
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v666-repaired-private-cnss-retry-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V641/V401/V490 prerequisites, then run V666 preflight",
            False,
        )

    decision, pass_ok, reason, next_step, live_executed = _v655_decide(args, checks, live)
    decision = _rewrite_text(decision)
    reason = _rewrite_text(reason)
    next_step = _rewrite_text(next_step)

    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    private_surface = live.get("v666_private_runtime_surface") or {}
    private_ready = bool(live.get("v666_private_runtime_ready"))
    if decision in {
        "v666-cnss-retry-binder-loop-persists",
        "v666-cnss-retry-review-required",
        "v666-cnss-retry-not-executed",
    } and not private_ready:
        return (
            "v666-private-runtime-surface-missing",
            True,
            f"private_runtime_surface={private_surface}",
            "repair private property/service socket materialization before another CNSS retry",
            live_executed,
        )
    if decision == "v666-cnss-retry-binder-loop-persists":
        return (
            "v666-repaired-private-cnss-retry-binder-loop-persists",
            pass_ok,
            f"private runtime ready but fresh cnss-daemon retry still hit binder transaction loop; surface={private_surface}",
            "classify dynamic vendor binder registration/service context gap before Wi-Fi HAL or scan/connect",
            live_executed,
        )
    if decision == "v666-cnss-retry-wlfw-advanced":
        return (
            "v666-repaired-private-cnss-retry-wlfw-advanced",
            pass_ok,
            f"private runtime ready={private_ready}; {reason}",
            "classify WLFW/BDF/wlan0 state before any Wi-Fi HAL, scan/connect, DHCP, route, or external ping gate",
            live_executed,
        )
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v655_render_summary(manifest)).replace(
        "# V666 Repaired Private Runtime CNSS Retry Proof",
        "# V666 Repaired Private Runtime CNSS Retry Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v666_private_runtime_surface") or {}
    return "\n".join([
        text,
        "",
        "## V666 Repaired Private Runtime Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{PROPERTY_ROOT}`",
        f"- mode: `{V666_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- private_runtime_ready: `{live.get('v666_private_runtime_ready', '')}`",
        "- Wi-Fi HAL/scan/connect/DHCP/routing/external ping remain blocked.",
        "",
        "## V666 Private Runtime Surface",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted(surface.items())],
        ) if surface else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v655_build_manifest(args, store)
    live = manifest.get("live") or {}
    manifest["cycle"] = "v666"
    manifest["helper_version"] = "v109"
    manifest["property_root"] = PROPERTY_ROOT
    manifest["repaired_private_cnss_retry_mode"] = V666_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["private_runtime_ready"] = bool(live.get("v666_private_runtime_ready")) if live else False
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V317 private property root bind into helper private /dev/__properties__",
        "private /dev/socket/property_service shim inside helper namespace",
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
