#!/usr/bin/env python3
"""V568 bounded IWifi.start WifiStatus decode proof."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_hwbinder_handle_retain_v567 as v567


base = v567.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v568-companion-dual-hal-wificond-iwifi-start-status")
base.DEFAULT_HELPER_SHA256 = "1e9e60c937de8930f87ea62849824d15ab0efba689da8b5fa26a3ebd83095902"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v93"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V568"
base.PROOF_SLUG = "v568-companion-dual-hal-wificond-iwifi-start-status"
base.LIVE_HELPER_STEP_NAME = "v568-helper-run"
base.APPROVAL_PHRASE = (
    "approve v568 IWifi.start status decode proof only; "
    "no supplicant, no scan/connect/link-up and no external ping"
)

_orig_run_live = base.run_live
_orig_classify = base.classify
_orig_render_summary = base.render_summary


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", base.HELPER_MODE,
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if base.approved(args):
        command.extend([
            "--allow-cnss-start-only",
            "--allow-wifi-companion-start-only",
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-hal-service-query",
            "--allow-iwifi-start-only",
        ])
    command.extend([
        "--property-root", "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__",
    ])
    if len(command) > 30:
        raise RuntimeError(f"V568 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["iwifi_start_wifi_status_decoded"] = keys.get("iwifi_start.start.wifi_status_decoded", "")
    result["iwifi_start_wifi_status_code"] = keys.get("iwifi_start.start.wifi_status_code", "")
    result["iwifi_start_wifi_status_name"] = keys.get("iwifi_start.start.wifi_status_name", "")
    result["iwifi_start_wifi_status_description"] = keys.get("iwifi_start.start.wifi_status.description", "")
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v567-", "v568-", 1) if decision.startswith("v567-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v568-iwifi-status-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in IWifi.start status proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v568-iwifi-status-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    status_name = live_result.get("iwifi_start_wifi_status_name") or "UNDECODED"
    status_code = live_result.get("iwifi_start_wifi_status_code") or ""
    if helper_result == "iwifi-start-transaction-pass" and status_name == "SUCCESS":
        return (
            "v568-iwifi-start-status-success",
            True,
            "IWifi.start transport and WifiStatus both succeeded; no scan/connect/link-up was executed",
            "inspect getChipIds/isStarted or move to bounded scan-only preflight if WLAN surface appears",
            live_executed,
        )
    if helper_result == "iwifi-transaction-failed":
        return (
            "v568-iwifi-start-status-error",
            True,
            f"IWifi.start transport completed but WifiStatus={status_name}/{status_code}",
            "repair the reported HAL/runtime dependency before scan-only work",
            live_executed,
        )
    return (
        "v568-iwifi-start-status-review-required",
        False,
        f"helper_result={helper_result} status={status_name}/{status_code}",
        "inspect V568 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V568 IWifi.start Status Decode Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- iwifi_service_token_wire: `{live.get('iwifi_service_token_wire', '')}`",
        f"- iwifi_service_retained: `{live.get('iwifi_service_retained', '')}`",
        f"- iwifi_start_wifi_status: `{live.get('iwifi_start_wifi_status_name', '')}/{live.get('iwifi_start_wifi_status_code', '')}`",
        f"- iwifi_start_description: `{live.get('iwifi_start_wifi_status_description', '')}`",
        "- repair: decode the HIDL `WifiStatus` returned by `IWifi.start()` instead of treating transport success as HAL success",
        "- forbidden: `supplicant`, `hostapd`, `scan/connect/link-up`, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
