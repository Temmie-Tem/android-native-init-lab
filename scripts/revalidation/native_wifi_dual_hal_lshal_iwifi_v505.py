#!/usr/bin/env python3
"""V505 dual-HAL lshal IWifi/default registration proof.

This bounded proof starts private servicemanager, hwservicemanager, both Wi-Fi
HAL daemons, and CNSS, then runs `/system/bin/lshal wait
android.hardware.wifi@1.0::IWifi/default` inside the same helper-owned
namespace.

It does not call IWifi.start(), read credentials, scan, connect, request DHCP,
change routes, ping externally, start supplicant/wificond/hostapd, or persist
any Android service.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_dual_hal_iwifi_surface_v503 as v503


v503.__doc__ = __doc__
v503.DEFAULT_OUT_DIR = v503.Path("tmp/wifi/v505-dual-hal-lshal-iwifi")
v503.DEFAULT_HELPER_SHA256 = "d3e8fa14e31ee4dfc8152829b86e4549a03e8f693aa7099573eca47e9362cc7a"
v503.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v55"
v503.APPROVAL_PHRASE = (
    "approve v505 dual-HAL lshal IWifi/default proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
v503.HELPER_MODE = "wifi-dual-hal-lshal-wait-iwifi"
v503.KEY_RE = re.compile(
    r"^(wifi_hal_composite_start|wifi_hal_micro_query|wifi_hal_service_query|wifi_surface_composite)\.([A-Za-z0-9_.-]+)=(.*)$"
)


def helper_command(args: v503.argparse.Namespace) -> list[str]:
    command = [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        v503.HELPER_MODE,
        "--target-profile",
        "vendor-wifi-hal-legacy",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        args.property_root,
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if v503.approved(args):
        command.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-cnss-start-only",
            "--allow-hal-service-query",
        ])
    return command


def classify(command: str,
             checks: list[v503.Check],
             live_result: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return "v505-dual-hal-lshal-iwifi-plan-ready", True, "plan-only; no device command executed", "run preflight", False
    blocked = v503.blockers(checks)
    if blocked:
        return "v505-dual-hal-lshal-iwifi-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V505 live proof", False
    if command == "preflight":
        return "v505-dual-hal-lshal-iwifi-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V505 dual-HAL lshal proof", False
    if not v503.approved(v503.args):
        return "v505-dual-hal-lshal-iwifi-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V505 approval", False
    if not live_result:
        return "v505-dual-hal-lshal-iwifi-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v505-dual-hal-lshal-iwifi-cleanup-review", False, "helper-owned children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    micro_result = keys.get("wifi_hal_micro_query.result", "missing")
    matched = keys.get("wifi_hal_micro_query.matched_fqinstance", "")
    if helper_result == "service-query-pass" and micro_result == "service-query-pass" and matched:
        return "v505-dual-hal-lshal-iwifi-present", True, f"lshal observed {matched} in the dual-HAL namespace", "repair or replace raw hwbinder client, then advance to IWifi.start proof", True
    if micro_result == "service-query-timeout":
        return "v505-dual-hal-lshal-iwifi-timeout", True, "lshal wait timed out while bounded cleanup stayed clean", "inspect HAL registration latency and service stderr", True
    if micro_result == "service-query-runtime-gap" or helper_result == "service-query-runtime-gap":
        return "v505-dual-hal-lshal-iwifi-absent", True, "lshal could not observe IWifi/default registration in the dual-HAL namespace", "triage HAL registration/runtime prerequisites before IWifi.start", True
    if helper_result == "service-query-tool-missing":
        return "v505-dual-hal-lshal-iwifi-tool-missing", False, "lshal was unavailable in the private runtime", "restore /system/bin/lshal visibility before retry", True
    return "v505-dual-hal-lshal-iwifi-review-required", False, f"helper_result={helper_result} micro_result={micro_result}", "inspect dual-HAL lshal transcript", True


v503.classify = classify
v503.helper_command = helper_command


if __name__ == "__main__":
    raise SystemExit(v503.main())
