#!/usr/bin/env python3
"""V567 bounded hwbinder reply-handle retain proof in the dual-HAL window."""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_dual_hal_wificond_hwbinder_token_compat_v566 as v566


base = v566.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v567-companion-dual-hal-wificond-hwbinder-handle-retain")
base.DEFAULT_HELPER_SHA256 = "e7bf6dade5f5f34c0a7489c7490bf11e0534fb1a4afff66134958f1091b89880"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v92"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V567"
base.PROOF_SLUG = "v567-companion-dual-hal-wificond-hwbinder-handle-retain"
base.LIVE_HELPER_STEP_NAME = "v567-helper-run"
base.APPROVAL_PHRASE = (
    "approve v567 hwbinder reply-handle retain proof only; "
    "no supplicant, no scan/connect/link-up and no external ping"
)
base.KEY_RE = re.compile(
    r"^(wifi_companion_hal_order|wifi_companion_qrtr_readback|wifi_hal_composite_start|wifi_hal_composite_child|capture|iwifi_start)\.([A-Za-z0-9_.-]+)=(.*)$"
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
        raise RuntimeError(f"V567 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["iwifi_service_token_wire"] = keys.get("iwifi_start.service_token_wire", "")
    result["iwifi_service_retained"] = keys.get("iwifi_start.service_retained", "")
    result["iwifi_last_reply_status_name"] = keys.get("iwifi_start.get.reply.status_name", "")
    result["iwifi_last_reply_status_value"] = keys.get("iwifi_start.get.reply.status_value", "")
    result["iwifi_start_failed_reply"] = keys.get("iwifi_start.start.failed_reply", "")
    result["iwifi_start_read_rc"] = keys.get("iwifi_start.start.read_rc", "")
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v566-", "v567-", 1) if decision.startswith("v566-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v567-handle-retain-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in handle-retain proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v567-handle-retain-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    token_wire = live_result.get("iwifi_service_token_wire") or "none"
    retained = live_result.get("iwifi_service_retained") or "0"
    if helper_result == "iwifi-service-null":
        return (
            "v567-handle-retain-raw-get-service-null",
            True,
            f"raw get did not produce a retained service handle token_wire={token_wire} retained={retained}",
            "inspect raw reply object layout and retain rc before another start attempt",
            live_executed,
        )
    if helper_result == "iwifi-transaction-failed":
        return (
            "v567-handle-retain-start-transaction-failed",
            True,
            f"raw get retained IWifi with token_wire={token_wire}, but IWifi.start did not complete cleanly",
            "inspect start reply/status and HAL stderr before scan-only work",
            live_executed,
        )
    if helper_result == "iwifi-start-transaction-pass":
        return (
            "v567-handle-retain-start-transaction-pass",
            True,
            f"raw hwbinder IWifi.start completed with token_wire={token_wire} and cleanup safe",
            "inspect WLAN surface/status evidence, then decide bounded scan-only gate",
            live_executed,
        )
    return (
        "v567-handle-retain-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V567 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V567 Hwbinder Handle-Retain Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- service_query_result: `{live.get('service_query_result', '')}`",
        f"- iwifi_start_result: `{live.get('iwifi_start_result', '')}`",
        f"- iwifi_service_token_wire: `{live.get('iwifi_service_token_wire', '')}`",
        f"- iwifi_service_retained: `{live.get('iwifi_service_retained', '')}`",
        f"- iwifi_start_failed_reply: `{live.get('iwifi_start_failed_reply', '')}`",
        "- repair: retain the returned hwbinder service handle before freeing the reply buffer",
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
