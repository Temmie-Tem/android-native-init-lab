#!/usr/bin/env python3
"""V513 dual-HAL `/dev/wlan` driver-state ON proof.

This bounded proof repeats the V510 private `/dev/wlan` run with helper v59 and
adds one guarded `ON` write through the helper-owned private `/dev/wlan` after
service-manager, both Wi-Fi HAL daemons, and CNSS are launched in the same
private namespace.

It does not read credentials, scan, connect, request DHCP, change routes, ping
externally, start supplicant/wificond/hostapd, or persist any Android service.
"""

from __future__ import annotations

from typing import Any

import native_wifi_dual_hal_private_devnode_v510 as v510


v503 = v510.v503
v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v513-dual-hal-driver-state-on")
v503.DEFAULT_HELPER_SHA256 = "9eb52d625974470427a1dda225e11fb5c1c1dffe18c1839f27626cdca6906100"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v59"
v503.APPROVAL_PHRASE = (
    "approve v513 dual-HAL driver-state ON proof only; "
    "no scan/connect/link-up and no external ping"
)
_BASE_HELPER_COMMAND = v503.helper_command
_BASE_RENDER_SUMMARY = v503.render_summary


def helper_command(args: v503.argparse.Namespace) -> list[str]:
    command = _BASE_HELPER_COMMAND(args)
    if "--timeout-sec" in command:
        index = command.index("--timeout-sec")
        del command[index:index + 2]
    if v503.approved(args):
        command.append("--allow-wlan-driver-state-on")
    return command


def _int_key(keys: dict[str, str], name: str, default: int = 0) -> int:
    try:
        return int(keys.get(name, str(default)), 0)
    except ValueError:
        return default


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v513-dual-hal-driver-state-on-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v513-dual-hal-driver-state-on-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V513 live proof", False
    if command == "preflight":
        return "v513-dual-hal-driver-state-on-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V513 driver-state proof", False
    if not v503.approved(v503.args):
        return "v513-dual-hal-driver-state-on-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V513 approval", False
    if not live_result:
        return "v513-dual-hal-driver-state-on-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v513-dual-hal-driver-state-on-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    micro_result = keys.get("wifi_hal_micro_query.result", "missing")
    write_executed = keys.get("wifi_hal_composite_start.wlan_driver_state_on.executed") == "1"
    write_rc = _int_key(keys, "wifi_hal_composite_start.wlan_driver_state_on.write_rc", default=-999)
    write_errno = _int_key(keys, "wifi_hal_composite_start.wlan_driver_state_on.write_errno", default=0)
    private_devnode = (
        keys.get("wifi_runtime_surface.before.private.dev_wlan.exists") == "1" or
        keys.get("wifi_runtime_surface.during.private.dev_wlan.exists") == "1"
    )
    attr_captured = keys.get("wifi_hal_composite_start.child.cnss_daemon.proc_attr_current_captured") == "1"
    cnss_observable = keys.get("wifi_hal_composite_start.child.cnss_daemon.observable") == "1"
    wlan_count = _int_key(keys, "wifi_surface_composite.during.wlan_count")
    phy_count = _int_key(keys, "wifi_surface_composite.during.phy_count")

    if helper_result == "service-query-pass" and micro_result == "service-query-pass":
        return "v513-dual-hal-driver-state-on-iwifi-present", True, "IWifi/default registered after bounded driver-state ON write", "advance to IWifi.start or scan-only proof", True
    if write_executed and write_rc == 0 and (wlan_count > 0 or phy_count > 0):
        return "v513-dual-hal-driver-state-on-wlan-materialized", True, f"driver-state ON write succeeded and Wi-Fi surface appeared wlan={wlan_count} phy={phy_count}", "advance to scan-only proof without credentials", True
    if write_executed and write_rc == 0:
        return "v513-dual-hal-driver-state-on-write-pass-no-link", True, "driver-state ON write succeeded but wlan/phy surface did not materialize during bounded window", "extend observation window or inspect ICNSS readiness", True
    if write_executed and private_devnode and attr_captured and cnss_observable:
        return "v513-dual-hal-driver-state-on-icnss-timeout-captured", True, f"private /dev/wlan write attempted rc={write_rc} errno={write_errno}; CNSS/HAL context captured without link-up", "triage ICNSS readiness below qcwlanstate before scan/connect", True
    if not write_executed:
        return "v513-dual-hal-driver-state-on-not-executed", False, "helper did not execute guarded driver-state ON write", "inspect V513 helper flags and approval path", True
    return "v513-dual-hal-driver-state-on-review-required", False, f"write_rc={write_rc} write_errno={write_errno} helper_result={helper_result} micro_result={micro_result}", "inspect V513 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    return text.replace("V510 Dual-HAL Private-Devnode Proof", "V513 Dual-HAL Driver-State ON Proof", 1)


v503.helper_command = helper_command
v503.classify = classify
v503.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v503.main())
