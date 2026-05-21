#!/usr/bin/env python3
"""V506 dual-HAL runtime-gap proof.

This bounded proof starts private servicemanager, hwservicemanager, both Wi-Fi
HAL daemons, and CNSS, then runs `/system/bin/lshal wait
android.hardware.wifi@1.0::IWifi/default` inside the same helper-owned
namespace while capturing child SELinux contexts and Wi-Fi runtime path
surfaces.

It does not call IWifi.start(), read credentials, scan, connect, request DHCP,
change routes, ping externally, start supplicant/wificond/hostapd, or persist
any Android service.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_dual_hal_lshal_iwifi_v505 as v505


v503 = v505.v503
v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v506-dual-hal-runtime-gap")
v503.DEFAULT_HELPER_SHA256 = "b4c08bf0e7243996101a4d6ebf10292be1e03d0d9134c210c03dd5be26e5e67e"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v56"
v503.APPROVAL_PHRASE = (
    "approve v506 dual-HAL runtime-gap proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
v503.HELPER_MODE = "wifi-dual-hal-lshal-wait-iwifi"
v503.KEY_RE = re.compile(
    r"^(wifi_hal_composite_start|wifi_hal_micro_query|wifi_hal_service_query|wifi_surface_composite|wifi_runtime_surface)\.([A-Za-z0-9_.-]+)=(.*)$"
)
_BASE_RENDER_SUMMARY = v503.render_summary


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v506-dual-hal-runtime-gap-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v506-dual-hal-runtime-gap-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V506 live proof", False
    if command == "preflight":
        return "v506-dual-hal-runtime-gap-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V506 runtime-gap proof", False
    if not v503.approved(v503.args):
        return "v506-dual-hal-runtime-gap-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V506 approval", False
    if not live_result:
        return "v506-dual-hal-runtime-gap-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v506-dual-hal-runtime-gap-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    micro_result = keys.get("wifi_hal_micro_query.result", "missing")
    attr_captured = any(
        key.endswith(".proc_attr_current_captured") and value == "1"
        for key, value in keys.items()
    )
    runtime_captured = any(key.startswith("wifi_runtime_surface.during.") for key in keys)
    if helper_result == "service-query-pass" and micro_result == "service-query-pass":
        return "v506-dual-hal-runtime-gap-iwifi-present", True, "lshal observed IWifi/default with runtime context captured", "repair raw hwbinder client or advance to IWifi.start proof", True
    if micro_result == "service-query-timeout" and attr_captured and runtime_captured:
        return "v506-dual-hal-runtime-gap-captured", True, "IWifi/default still timed out; child SELinux context and runtime surfaces were captured", "compare missing surfaces/context against Android boot-complete evidence", True
    if attr_captured or runtime_captured:
        return "v506-dual-hal-runtime-gap-review", True, f"helper_result={helper_result} micro_result={micro_result}; runtime diagnostics captured", "inspect runtime surface and child attr/current evidence", True
    return "v506-dual-hal-runtime-gap-review-required", False, f"helper_result={helper_result} micro_result={micro_result}; diagnostics missing", "inspect V506 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    return text.replace("# V503 Dual-HAL IWifi.start Surface Proof", "# V506 Dual-HAL Runtime-Gap Proof", 1)


v503.classify = classify
v503.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v503.main())
