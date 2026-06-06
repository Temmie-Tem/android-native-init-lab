#!/usr/bin/env python3
"""V559 bounded companion plus HAL plus wificond AOSP IWifi registration wait.

V558 proved Samsung `ISehWifi/default` registration in the 11-child window.
V559 uses the same window but waits for `android.hardware.wifi@1.0::IWifi/default`
before any `IWifi.start()`, scan/connect, credentials, DHCP, routes, or
external ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_hal_wificond_registration_v558 as v558


base = v558.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v559-companion-hal-wificond-iwifi-registration")
base.DEFAULT_HELPER_SHA256 = "fd3080cea356958c583b0cb2c78e7d4e40584253041de693709036c396c76a55"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v84"
base.HELPER_MODE = "wifi-companion-hal-wificond-lshal-wait-iwifi"
base.PROOF_VERSION = "V559"
base.PROOF_SLUG = "v559-companion-hal-wificond-iwifi-registration"
base.LIVE_HELPER_STEP_NAME = "v559-helper-run"
base.APPROVAL_PHRASE = (
    "approve v559 companion plus HAL plus wificond IWifi registration wait only; "
    "no IWifi.start, no supplicant, no scan/connect/link-up and no external ping"
)

_orig_classify = base.classify
_orig_render_summary = base.render_summary


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v558-", "v559-", 1) if decision.startswith("v558-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v559-iwifi-registration-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in IWifi registration proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v559-iwifi-registration-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    micro_result = live_result.get("micro_query_result")
    matched = live_result.get("matched_fqinstance")
    readiness_markers = dmesg.get("readiness_markers") or []
    if readiness_markers:
        return (
            "v559-iwifi-registration-marker-observed",
            True,
            "IWifi registration wait window observed readiness markers: " + ",".join(readiness_markers),
            "move to bounded IWifi.start or scan-only surface; still no credential connect until scan proof",
            live_executed,
        )
    if helper_result == "service-query-pass":
        return (
            "v559-iwifi-registration-observed",
            True,
            f"AOSP IWifi registration observed: {matched or micro_result}",
            "move to bounded IWifi.start transaction before scan/connect",
            live_executed,
        )
    if helper_result == "service-query-timeout":
        return (
            "v559-iwifi-registration-timeout",
            True,
            "AOSP IWifi/default did not appear even though V558 observed Samsung ISehWifi registration",
            "test full dual-HAL Android-like window before attempting raw IWifi.start",
            live_executed,
        )
    if helper_result in {"service-query-runtime-gap", "start-only-runtime-gap"}:
        return (
            "v559-iwifi-registration-runtime-gap",
            True,
            f"IWifi registration query did not complete cleanly: helper_result={helper_result} micro={micro_result}",
            "inspect lshal stderr/stdout and child lifecycle evidence",
            live_executed,
        )
    return (
        "v559-iwifi-registration-review-required",
        False,
        f"helper_result={helper_result} micro={micro_result}",
        "inspect V559 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V559 AOSP IWifi Registration Wait",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- micro_query_result: `{live.get('micro_query_result', '')}`",
        f"- micro_query_reason: `{live.get('micro_query_reason', '')}`",
        f"- matched_fqinstance: `{live.get('matched_fqinstance', '')}`",
        "- target: `android.hardware.wifi@1.0::IWifi/default`",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
