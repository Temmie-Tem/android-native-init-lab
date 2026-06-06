#!/usr/bin/env python3
"""V504 dual-HAL IWifi.start proof with legacy property shim support.

This reuses the bounded V503 surface proof against helper v54, whose private
property-service shim accepts both the legacy `PROP_MSG_SETPROP` frame and the
newer `PROP_MSG_SETPROP2` frame for `hwservicemanager.ready=true`.

It does not read credentials, scan, connect, request DHCP, change routes, ping
externally, start supplicant/wificond/hostapd, or persist any Android service.
"""

from __future__ import annotations

from typing import Any

import native_wifi_dual_hal_iwifi_surface_v503 as v503


v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v504-dual-hal-legacy-property-shim")
v503.DEFAULT_HELPER_SHA256 = "4253d2babfb40f42cc0c2aaac3e1bfa322447c375a9e89e980cd81a840082740"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v54"
v503.APPROVAL_PHRASE = (
    "approve v504 dual-HAL legacy property shim proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v504-dual-hal-legacy-property-shim-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v504-dual-hal-legacy-property-shim-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V504 live proof", False
    if command == "preflight":
        return "v504-dual-hal-legacy-property-shim-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V504 dual-HAL proof", False
    if not v503.approved(v503.args):
        return "v504-dual-hal-legacy-property-shim-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V504 approval", False
    if not live_result:
        return "v504-dual-hal-legacy-property-shim-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v504-dual-hal-legacy-property-shim-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True
    if live_result["iwifi_start_transaction_ok"]:
        return "v504-dual-hal-iwifi-start-transaction-pass", True, "dual-HAL namespace returned IWifi/default and IWifi.start completed with legacy property shim support", "advance to scan-only proof with dual-HAL mode", True
    if live_result["service_null"]:
        return "v504-dual-hal-iwifi-service-null", True, "dual-HAL namespace still did not return IWifi/default after legacy property shim support", "triage remaining Android runtime prerequisites", True
    return "v504-dual-hal-legacy-property-shim-review-required", False, f"helper_result={live_result['helper_result']} iwifi={live_result['iwifi_result']}", "inspect dual-HAL transcript before widening scope", True


v503.classify = classify


if __name__ == "__main__":
    raise SystemExit(v503.main())
