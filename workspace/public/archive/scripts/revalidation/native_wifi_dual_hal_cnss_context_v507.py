#!/usr/bin/env python3
"""V507 dual-HAL CNSS SELinux-context proof.

This bounded proof repeats the V506 runtime-gap check with helper v57, which
adds the Android-observed `u:r:vendor_wcnss_service:s0` exec context for
`cnss-daemon`.

It does not call IWifi.start(), read credentials, scan, connect, request DHCP,
change routes, ping externally, start supplicant/wificond/hostapd, or persist
any Android service.
"""

from __future__ import annotations

from typing import Any

import native_wifi_dual_hal_runtime_gap_v506 as v506


v503 = v506.v503
v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v507-dual-hal-cnss-context")
v503.DEFAULT_HELPER_SHA256 = "9ae5562727682a9811df7216fb522e4e1dd7271b4f5c4ca4ecf6545bb8be9afa"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v57"
v503.APPROVAL_PHRASE = (
    "approve v507 dual-HAL CNSS-context proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
_BASE_RENDER_SUMMARY = v503.render_summary


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v507-dual-hal-cnss-context-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v507-dual-hal-cnss-context-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V507 live proof", False
    if command == "preflight":
        return "v507-dual-hal-cnss-context-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V507 CNSS-context proof", False
    if not v503.approved(v503.args):
        return "v507-dual-hal-cnss-context-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V507 approval", False
    if not live_result:
        return "v507-dual-hal-cnss-context-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v507-dual-hal-cnss-context-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    micro_result = keys.get("wifi_hal_micro_query.result", "missing")
    attr_captured = keys.get("wifi_hal_composite_start.child.cnss_daemon.proc_attr_current_captured") == "1"
    cnss_observable = keys.get("wifi_hal_composite_start.child.cnss_daemon.observable") == "1"
    if helper_result == "service-query-pass" and micro_result == "service-query-pass":
        return "v507-dual-hal-cnss-context-iwifi-present", True, "IWifi/default registered after CNSS context repair", "advance to IWifi.start proof", True
    if attr_captured and cnss_observable:
        return "v507-dual-hal-cnss-context-captured", True, f"IWifi/default still not registered; helper_result={helper_result} micro_result={micro_result}", "inspect CNSS attr/current and remaining runtime surface gaps", True
    return "v507-dual-hal-cnss-context-review-required", False, f"helper_result={helper_result} micro_result={micro_result}; CNSS context evidence missing", "inspect V507 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    return text.replace("V506 Dual-HAL Runtime-Gap Proof", "V507 Dual-HAL CNSS-Context Proof", 1)


v503.classify = classify
v503.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v503.main())
