#!/usr/bin/env python3
"""V561 bounded companion plus dual-HAL plus wificond IWifi.start proof."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_iwifi_registration_v560 as v560


base = v560.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v561-companion-dual-hal-wificond-iwifi-start")
base.DEFAULT_HELPER_SHA256 = "7564fa10547f4d5208a2062785dea34ea9d30bd116f08daf4ce289266cfa6314"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v86"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-iwifi-start"
base.PROOF_VERSION = "V561"
base.PROOF_SLUG = "v561-companion-dual-hal-wificond-iwifi-start"
base.LIVE_HELPER_STEP_NAME = "v561-helper-run"
base.APPROVAL_PHRASE = (
    "approve v561 companion plus dual HAL plus wificond IWifi.start proof only; "
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
            "--allow-iwifi-start-only",
        ])
    command.extend([
        "--property-root", "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__",
    ])
    if len(command) > 30:
        raise RuntimeError(f"V561 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["helper_result"] = keys.get("wifi_companion_hal_order.result", "missing")
    result["iwifi_start_result"] = keys.get("wifi_companion_hal_order.iwifi_start_result", "")
    result["iwifi_status"] = keys.get("iwifi_start.status", "")
    result["iwifi_reason"] = keys.get("iwifi_start.reason", "")
    result["surface_after_iwifi_wlan_count"] = keys.get("wifi_companion_hal_order.surface_after_iwifi_start.wlan_count", "")
    result["surface_after_iwifi_phy_count"] = keys.get("wifi_companion_hal_order.surface_after_iwifi_start.phy_count", "")
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v560-", "v561-", 1) if decision.startswith("v560-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v561-iwifi-start-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in IWifi.start proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v561-iwifi-start-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    readiness_markers = dmesg.get("readiness_markers") or []
    wlan_count = live_result.get("surface_after_iwifi_wlan_count") or "0"
    phy_count = live_result.get("surface_after_iwifi_phy_count") or "0"
    if readiness_markers or wlan_count != "0" or phy_count != "0":
        return (
            "v561-iwifi-start-surface-observed",
            True,
            f"IWifi.start produced readiness/surface evidence markers={readiness_markers} wlan={wlan_count} phy={phy_count}",
            "move to bounded scan-only proof before credentials/connect",
            live_executed,
        )
    if helper_result == "iwifi-start-transaction-pass":
        return (
            "v561-iwifi-start-transaction-pass-no-surface",
            True,
            "IWifi.start transaction completed and cleanup was safe, but no WLAN/firmware surface appeared",
            "inspect HAL return/status and dmesg; scan/connect remains blocked",
            live_executed,
        )
    if helper_result == "iwifi-service-null":
        return (
            "v561-iwifi-start-service-null",
            True,
            "IWifi/default handle was not returned despite V560 registration proof",
            "inspect raw hwbinder get contract against lshal registration evidence",
            live_executed,
        )
    if helper_result == "iwifi-transaction-failed":
        return (
            "v561-iwifi-start-transaction-failed",
            True,
            "IWifi.start transaction did not complete cleanly",
            "inspect iwifi_start transcript and HAL stderr before retry",
            live_executed,
        )
    return (
        "v561-iwifi-start-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V561 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V561 IWifi.start Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- iwifi_start_result: `{live.get('iwifi_start_result', '')}`",
        f"- iwifi_status: `{live.get('iwifi_status', '')}`",
        f"- iwifi_reason: `{live.get('iwifi_reason', '')}`",
        f"- wlan_after_iwifi: `{live.get('surface_after_iwifi_wlan_count', '')}`",
        f"- phy_after_iwifi: `{live.get('surface_after_iwifi_phy_count', '')}`",
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
