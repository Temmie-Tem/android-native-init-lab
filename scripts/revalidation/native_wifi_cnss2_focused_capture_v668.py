#!/usr/bin/env python3
"""V668 service-74 gated cnss2 focused capture proof.

This proof reruns the V666 repaired private runtime fresh cnss-daemon retry
path with helper v110. Helper v110 adds focused icnss/QCA6390 sysfs captures
immediately after service `74` opens and again during the active window. It
does not write sysfs, open esoc0, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_repaired_private_cnss_retry_v666 as v666


base = v666.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v668-cnss2-focused-capture")
base.DEFAULT_HELPER_SHA256 = "a9e2d9dd414389f676f3055725c7203a9d47ce708b0abbb60010935074768549"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v110"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v666-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v668 service74 cnss2 focused capture proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

V668_FOCUS_PREFIX = "wifi_companion_start.cnss2_focus_"
FOCUS_PHASES = ("service74_open", "window")
V668_TOKENS = (
    "a90_android_execns_probe v110",
    "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only",
    "--property-root",
    "--allow-qrtr-ns-readback",
)

_v666_build_checks = base.build_checks
_v666_run_live = base.run_live
_v666_decide = base.decide
_v666_render_summary = base.render_summary
_v666_build_manifest = base.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V666", "V668")
        .replace("v666", "v668")
        .replace("helper v109", "helper v110")
        .replace("helper-v109", "helper-v110")
        .replace("a90_android_execns_probe v109", "a90_android_execns_probe v110")
        .replace("Repaired Private Runtime CNSS Retry", "cnss2 Focused Capture")
        .replace("repaired private cnss-daemon retry", "cnss2 focused capture")
    )


def _focus_surface(keys: dict[str, str]) -> dict[str, dict[str, str]]:
    surface: dict[str, dict[str, str]] = {}
    for phase in FOCUS_PHASES:
        prefix = f"{V668_FOCUS_PREFIX}{phase}."
        surface[phase] = {
            "begin": keys.get(f"{prefix}begin", ""),
            "end": keys.get(f"{prefix}end", ""),
            "icnss_driver_captured": keys.get(f"{prefix}icnss_driver_captured", ""),
            "icnss_device_captured": keys.get(f"{prefix}icnss_device_captured", ""),
            "qca6390_device_captured": keys.get(f"{prefix}qca6390_device_captured", ""),
            "net_class_captured": keys.get(f"{prefix}net_class_captured", ""),
            "wlan0_captured": keys.get(f"{prefix}wlan0_captured", ""),
            "debug_icnss_captured": keys.get(f"{prefix}debug_icnss_captured", ""),
            "value_captures": keys.get(f"{prefix}value_captures", ""),
        }
    return surface


def _focus_ready(surface: dict[str, dict[str, str]]) -> bool:
    for phase in FOCUS_PHASES:
        item = surface.get(phase) or {}
        if (
            item.get("begin") != "1"
            or item.get("end") != "1"
            or item.get("icnss_device_captured") != "1"
            or item.get("qca6390_device_captured") != "1"
        ):
            return False
    return True


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v666_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and all(token in usage for token in V668_TOKENS[1:])
    )
    base.add_check(
        checks,
        "helper-v110-cnss2-focused-capture-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v110 cnss2 focused capture strings and V666-compatible service74 CNSS retry mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or "cnss2_focus" in line
            or "wifi_cnss2_focus" in line
            or "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only" in line
        ][:14],
        "deploy helper v110 before V668 live proof",
    )
    return checks


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v666_run_live(args, store, steps, mount_preflight)
    keys = v666._merged_helper_keys(live)
    surface = _focus_surface(keys)
    live["v668_cnss2_focus_surface"] = surface
    live["v668_cnss2_focus_ready"] = _focus_ready(surface)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v666_decide(args, checks, live)
    decision = _rewrite_text(decision)
    reason = _rewrite_text(reason)
    next_step = _rewrite_text(next_step)

    if args.command == "plan":
        return (
            "v668-cnss2-focused-capture-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v110, refresh current-boot prerequisites, then run V668 preflight/live",
            False,
        )
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    focus_surface = live.get("v668_cnss2_focus_surface") or {}
    focus_ready = bool(live.get("v668_cnss2_focus_ready"))
    counts = (live.get("v655_counts") or {})
    advanced = any(int(counts.get(name, 0) or 0) > 0 for name in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ))
    if not focus_ready:
        return (
            "v668-cnss2-focused-capture-missing",
            True,
            f"V668 live ran but focused cnss2 capture was incomplete: {focus_surface}",
            "fix helper focused capture before changing Wi-Fi runtime behavior",
            live_executed,
        )
    if advanced:
        return (
            "v668-cnss2-focused-capture-wifi-surface-advanced",
            pass_ok,
            f"focused capture ready and lower Wi-Fi markers advanced; counts={counts}; focus={focus_surface}",
            "classify WLFW/BDF/wlan0 state before Wi-Fi HAL or scan/connect",
            live_executed,
        )
    return (
        "v668-cnss2-focused-capture-gap-classified",
        pass_ok,
        f"focused capture ready but WLFW/BDF/wlan0 markers remain absent; counts={counts}; focus={focus_surface}",
        "compare focused service74/window sysfs captures and choose the next cnss2 kernel progression gate",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v666_render_summary(manifest))
    live = manifest.get("live") or {}
    surface = live.get("v668_cnss2_focus_surface") or {}
    rows: list[list[str]] = []
    for phase, item in surface.items():
        for key, value in sorted(item.items()):
            rows.append([phase, key, str(value)])
    return "\n".join([
        text,
        "",
        "## V668 cnss2 Focused Capture",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- focused_capture_ready: `{live.get('v668_cnss2_focus_ready', '')}`",
        "- Wi-Fi HAL/scan/connect/DHCP/routing/external ping remain blocked.",
        "",
        base.markdown_table(["phase", "key", "value"], rows) if rows else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v666_build_manifest(args, store)
    live = manifest.get("live") or {}
    manifest["cycle"] = "v668"
    manifest["helper_version"] = "v110"
    manifest["cnss2_focused_capture_ready"] = bool(live.get("v668_cnss2_focus_ready")) if live else False
    manifest["explicitly_approved"] = [
        "helper v110 focused icnss/QCA6390 read-only capture during service74/CNSS retry window",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V317 private property root bind and property service shim inside helper namespace",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "sysfs writes or subsystem state writes",
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
