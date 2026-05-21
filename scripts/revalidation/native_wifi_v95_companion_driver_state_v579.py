#!/usr/bin/env python3
"""V579 bounded V95 companion + driver-state ON proof."""

from __future__ import annotations

from typing import Any

import native_wifi_v95_broader_iwifi_retry_v577 as v577


base = v577.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v579-v95-companion-driver-state")
base.DEFAULT_HELPER_SHA256 = "97982aa10d61297691ac87688336fb51183d21a70958660697c7462e009b84f0"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v96"
base.PROOF_VERSION = "V579"
base.PROOF_SLUG = "v579-v95-companion-driver-state"
base.LIVE_HELPER_STEP_NAME = "v579-helper-run"
base.APPROVAL_PHRASE = (
    "approve v579 v95 companion driver-state ON proof only; "
    "no QMI payload, no supplicant, no scan/connect/link-up and no external ping"
)

_BASE_HELPER_COMMAND = base.helper_command
_BASE_RUN_LIVE = base.run_live
_BASE_RENDER_SUMMARY = base.render_summary


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _BASE_HELPER_COMMAND(args)
    if "--timeout-sec" in command:
        index = command.index("--timeout-sec")
        del command[index:index + 2]
    if base.approved(args):
        command.append("--allow-wlan-driver-state-on")
    return command


def _int_key(keys: dict[str, str], name: str, default: int = 0) -> int:
    try:
        return int(keys.get(name, str(default)), 0)
    except ValueError:
        return default


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _BASE_RUN_LIVE(args, store)
    keys = result.get("keys") or {}
    result["driver_state_on"] = keys.get("wifi_companion_hal_order.qcwlanstate_write") == "1"
    result["driver_state_write_executed"] = keys.get("wifi_hal_composite_start.wlan_driver_state_on.executed") == "1"
    result["driver_state_write_rc"] = _int_key(keys, "wifi_hal_composite_start.wlan_driver_state_on.write_rc", default=-999)
    result["driver_state_write_errno"] = _int_key(keys, "wifi_hal_composite_start.wlan_driver_state_on.write_errno")
    result["driver_state_write_duration_ms"] = _int_key(keys, "wifi_hal_composite_start.wlan_driver_state_on.duration_ms")
    result["private_dev_wlan_before"] = keys.get("wifi_companion_hal_order.runtime_before.private.dev_wlan.exists")
    result["private_dev_wlan_after_iwifi"] = keys.get("wifi_companion_hal_order.runtime_after_iwifi_start.private.dev_wlan.exists")
    result["wlan_count_window"] = _int_key(keys, "wifi_companion_hal_order.surface_window.wlan_count")
    result["phy_count_window"] = _int_key(keys, "wifi_companion_hal_order.surface_window.phy_count")
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = v577.classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        if decision.startswith("v577-"):
            decision = decision.replace("v577-", "v579-", 1)
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("driver_state_write_executed"):
        return (
            "v579-driver-state-not-executed",
            False,
            "helper v96 did not execute the guarded qcwlanstate ON write",
            "inspect helper command flags before retry",
            live_executed,
        )
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v579-driver-state-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in V579",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v579-driver-state-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )
    if int(live_result.get("qrtr_readback_qmi_attempted") or 0):
        return (
            "v579-driver-state-qmi-guard-failed",
            False,
            "unexpected QMI payload attempt during V579",
            "stop and inspect helper before any further live action",
            live_executed,
        )

    status_name = live_result.get("iwifi_start_wifi_status_name") or "UNDECODED"
    status_code = live_result.get("iwifi_start_wifi_status_code") or ""
    qipcrtr_window = live_result.get("qipcrtr_sockets_window") or "unknown"
    service_events = int(live_result.get("qrtr_readback_service_events") or 0)
    readiness_markers = dmesg.get("readiness_markers") or []
    write_rc = live_result.get("driver_state_write_rc")
    write_errno = live_result.get("driver_state_write_errno")
    wlan_count = live_result.get("wlan_count_window") or 0
    phy_count = live_result.get("phy_count_window") or 0

    if status_name == "SUCCESS" or wlan_count > 0 or phy_count > 0:
        return (
            "v579-driver-state-wifi-surface-advanced",
            True,
            f"IWifi.start={status_name}/{status_code} wlan={wlan_count} phy={phy_count}; scan/connect still blocked",
            "move to separate scan-only proof if postflight remains clean",
            live_executed,
        )
    if readiness_markers:
        return (
            "v579-driver-state-readiness-marker-observed",
            True,
            f"driver-state write rc={write_rc} errno={write_errno}; readiness markers appeared: {readiness_markers}",
            "inspect delayed firmware/netdev surface before scan-only work",
            live_executed,
        )
    if service_events > 0:
        return (
            "v579-driver-state-qrtr-progress",
            True,
            f"driver-state write rc={write_rc} errno={write_errno}; WLFW service_events={service_events}",
            "inspect WLFW/BDF/CNSS surface before scan-only work",
            live_executed,
        )
    return (
        "v579-driver-state-no-readiness-progress",
        True,
        f"guarded qcwlanstate write executed rc={write_rc} errno={write_errno}; IWifi.start={status_name}/{status_code}; QIPCRTR sockets={qipcrtr_window}; no readiness marker",
        "continue below-qcwlanstate ICNSS/QRTR dependency analysis before scan/connect",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        ["driver_state_on", live.get("driver_state_on", "")],
        ["driver_state_write_executed", live.get("driver_state_write_executed", "")],
        ["driver_state_write_rc", live.get("driver_state_write_rc", "")],
        ["driver_state_write_errno", live.get("driver_state_write_errno", "")],
        ["driver_state_write_duration_ms", live.get("driver_state_write_duration_ms", "")],
        ["private_dev_wlan_before", live.get("private_dev_wlan_before", "")],
        ["private_dev_wlan_after_iwifi", live.get("private_dev_wlan_after_iwifi", "")],
        ["wlan_count_window", live.get("wlan_count_window", "")],
        ["phy_count_window", live.get("phy_count_window", "")],
    ]
    extra = "\n".join([
        "## V579 V95 Companion Driver-state ON",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        "- forbidden: QMI payload, `supplicant`, `hostapd`, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
        base.markdown_table(["key", "value"], rows),
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
