#!/usr/bin/env python3
"""V557 bounded companion plus HAL plus wificond order proof.

This reuses the V556 companion plus Wi-Fi HAL order harness but switches the
helper to v82's wificond-inclusive order mode:

servicemanager -> hwservicemanager -> vndservicemanager -> qrtr-ns ->
rmt_storage -> tftp_server -> pd-mapper -> Wi-Fi HAL -> cnss_diag ->
wificond -> cnss-daemon.

The proof is still start-only. It does not start supplicant, hostapd,
IWifi.start, scan/connect/link-up, credentials, DHCP, routes, external ping,
reboot, or boot partition writes.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_hal_order_v556 as v556


base = v556.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v557-companion-hal-wificond-order")
base.DEFAULT_HELPER_SHA256 = "643a40aa3e0bd2108f5417e30c704d490ec1c237cadfd005650732621f82a881"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v82"
base.HELPER_MODE = "wifi-companion-hal-wificond-order-start-only"
base.PROOF_VERSION = "V557"
base.PROOF_SLUG = "v557-companion-hal-wificond-order"
base.LIVE_HELPER_STEP_NAME = "v557-helper-run"
base.APPROVAL_PHRASE = (
    "approve v557 companion plus HAL plus wificond order start-only proof only; "
    "no supplicant, no scan/connect/link-up and no external ping"
)

_orig_render_summary = base.render_summary
_orig_classify = base.classify


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v556-", "v557-", 1) if decision.startswith("v556-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v557-wificond-order-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in start-only proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v557-wificond-order-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result.get("helper_result")
    if readiness_markers:
        return (
            "v557-wificond-order-marker-observed",
            True,
            "companion plus HAL plus wificond order window observed readiness markers: " + ",".join(readiness_markers),
            "move to bounded scan-only or IWifi.start surface; still no credential connect until scan proof",
            live_executed,
        )
    if helper_result == "order-window-pass":
        return (
            "v557-wificond-order-no-fw-marker",
            True,
            "companion plus HAL plus wificond order window stayed alive and cleaned, but no WLFW/QMI/BDF/wlan0 marker appeared",
            "inspect wificond/HAL stderr and service registration; next boundary is likely IWifi.start or framework registration",
            live_executed,
        )
    if helper_result == "start-only-runtime-gap":
        return (
            "v557-wificond-order-runtime-gap",
            True,
            "one wificond-order child exited before the observe window",
            "inspect child stdout/stderr, SELinux, property, and linker surfaces",
            live_executed,
        )
    return (
        "v557-wificond-order-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V557 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    wificond_flag = ""
    for key, value in live.get("order_focus_keys") or []:
        if key == "wifi_companion_hal_order.wificond":
            wificond_flag = str(value)
            break
    extra = "\n".join([
        "## V557 Wificond Boundary",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- wificond_included: `{wificond_flag or 'missing'}`",
        "- forbidden: `supplicant`, `hostapd`, `scan/connect/link-up`, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
