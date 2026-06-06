#!/usr/bin/env python3
"""V560 bounded companion plus dual-HAL plus wificond IWifi registration wait.

V559 showed AOSP `IWifi/default` does not register when only the Samsung Wi-Fi
HAL binary is started. V560 starts both Android-observed Wi-Fi HAL binaries in
the same bounded companion/wificond window, then waits for AOSP IWifi
registration. It still does not call `IWifi.start()` or perform scan/connect.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_hal_wificond_iwifi_registration_v559 as v559


base = v559.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v560-companion-dual-hal-wificond-iwifi-registration")
base.DEFAULT_HELPER_SHA256 = "e98dac60aa3317e86e7ca3053264b7d28257b8c9bd25723bff52438719c148b6"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v85"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-wait-iwifi"
base.PROOF_VERSION = "V560"
base.PROOF_SLUG = "v560-companion-dual-hal-wificond-iwifi-registration"
base.LIVE_HELPER_STEP_NAME = "v560-helper-run"
base.APPROVAL_PHRASE = (
    "approve v560 companion plus dual HAL plus wificond IWifi registration wait only; "
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
        return decision.replace("v559-", "v560-", 1) if decision.startswith("v559-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v560-dual-hal-iwifi-registration-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in dual-HAL IWifi registration proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v560-dual-hal-iwifi-registration-cleanup-review",
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
            "v560-dual-hal-iwifi-registration-marker-observed",
            True,
            "dual-HAL IWifi registration wait observed readiness markers: " + ",".join(readiness_markers),
            "move to bounded IWifi.start or scan-only surface; still no credential connect until scan proof",
            live_executed,
        )
    if helper_result == "service-query-pass":
        return (
            "v560-dual-hal-iwifi-registration-observed",
            True,
            f"AOSP IWifi registration observed in dual-HAL window: {matched or micro_result}",
            "move to bounded IWifi.start transaction before scan/connect",
            live_executed,
        )
    if helper_result == "service-query-timeout":
        return (
            "v560-dual-hal-iwifi-registration-timeout",
            True,
            "AOSP IWifi/default still did not appear in the full dual-HAL Android-like window",
            "inspect legacy HAL lifecycle/stderr and Android framework registration path before IWifi.start",
            live_executed,
        )
    if helper_result in {"service-query-runtime-gap", "start-only-runtime-gap"}:
        return (
            "v560-dual-hal-iwifi-registration-runtime-gap",
            True,
            f"dual-HAL IWifi registration query did not complete cleanly: helper_result={helper_result} micro={micro_result}",
            "inspect lshal stderr/stdout and child lifecycle evidence",
            live_executed,
        )
    return (
        "v560-dual-hal-iwifi-registration-review-required",
        False,
        f"helper_result={helper_result} micro={micro_result}",
        "inspect V560 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V560 Dual-HAL AOSP IWifi Registration Wait",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- micro_query_result: `{live.get('micro_query_result', '')}`",
        f"- micro_query_reason: `{live.get('micro_query_reason', '')}`",
        f"- matched_fqinstance: `{live.get('matched_fqinstance', '')}`",
        "- target: `android.hardware.wifi@1.0::IWifi/default`",
        "- hal_window: `android.hardware.wifi@1.0-service` + `vendor.samsung.hardware.wifi@2.0-service`",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
