#!/usr/bin/env python3
"""V510 dual-HAL private `/dev/wlan` proof.

This bounded proof repeats the V507 dual-HAL CNSS-context check with helper
v58, which mirrors the host qcwlanstate char device into the private execns
root as `/dev/wlan` when the host node already exists.

It does not call IWifi.start(), read credentials, scan, connect, request DHCP,
change routes, ping externally, start supplicant/wificond/hostapd, or persist
any Android service.
"""

from __future__ import annotations

from typing import Any

import native_wifi_dual_hal_cnss_context_v507 as v507


v503 = v507.v503
v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v510-dual-hal-private-devnode")
v503.DEFAULT_HELPER_SHA256 = "85b241e504426d041f64388408f78bbfc5d955a57ca1c08690c54a9e24116a19"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v58"
v503.APPROVAL_PHRASE = (
    "approve v510 dual-HAL private-devnode proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
_BASE_RENDER_SUMMARY = v503.render_summary


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v510-dual-hal-private-devnode-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v510-dual-hal-private-devnode-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V510 live proof", False
    if command == "preflight":
        return "v510-dual-hal-private-devnode-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V510 private-devnode proof", False
    if not v503.approved(v503.args):
        return "v510-dual-hal-private-devnode-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V510 approval", False
    if not live_result:
        return "v510-dual-hal-private-devnode-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v510-dual-hal-private-devnode-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    micro_result = keys.get("wifi_hal_micro_query.result", "missing")
    private_devnode = (
        keys.get("wifi_runtime_surface.before.private.dev_wlan.exists") == "1" or
        keys.get("wifi_runtime_surface.during.private.dev_wlan.exists") == "1"
    )
    host_devnode = (
        keys.get("wifi_runtime_surface.before.host.dev_wlan.exists") == "1" or
        keys.get("wifi_runtime_surface.during.host.dev_wlan.exists") == "1"
    )
    private_mode = (
        keys.get("wifi_runtime_surface.before.private.dev_wlan.mode") or
        keys.get("wifi_runtime_surface.during.private.dev_wlan.mode") or
        "missing"
    )
    attr_captured = keys.get("wifi_hal_composite_start.child.cnss_daemon.proc_attr_current_captured") == "1"
    cnss_observable = keys.get("wifi_hal_composite_start.child.cnss_daemon.observable") == "1"

    if helper_result == "service-query-pass" and micro_result == "service-query-pass":
        return "v510-dual-hal-private-devnode-iwifi-present", True, "IWifi/default registered after private /dev/wlan reflection", "advance to IWifi.start proof", True
    if private_devnode and attr_captured and cnss_observable:
        return "v510-dual-hal-private-devnode-reflected", True, f"private /dev/wlan reflected mode={private_mode}; IWifi/default still not registered helper_result={helper_result} micro_result={micro_result}", "inspect whether qcwlanstate ON or another runtime surface is still required", True
    if host_devnode and not private_devnode:
        return "v510-dual-hal-private-devnode-missing", False, "host /dev/wlan exists but private root still lacks it", "inspect v58 setup_namespace materialization path", True
    return "v510-dual-hal-private-devnode-review-required", False, f"host_devnode={host_devnode} private_devnode={private_devnode} helper_result={helper_result} micro_result={micro_result}", "inspect V510 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    return text.replace("V507 Dual-HAL CNSS-Context Proof", "V510 Dual-HAL Private-Devnode Proof", 1)


v503.classify = classify
v503.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v503.main())
