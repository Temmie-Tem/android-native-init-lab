#!/usr/bin/env python3
"""V566 bounded hwbinder interface-token compatibility proof in the dual-HAL window."""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_dual_hal_wificond_hwbinder_mmap_v565 as v565


base = v565.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v566-companion-dual-hal-wificond-hwbinder-token-compat")
base.DEFAULT_HELPER_SHA256 = "3246fade6f0a484b6cbc416a64c3884d686dc4f9b2dd35ae8a3f656516893f85"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v91"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V566"
base.PROOF_SLUG = "v566-companion-dual-hal-wificond-hwbinder-token-compat"
base.LIVE_HELPER_STEP_NAME = "v566-helper-run"
base.APPROVAL_PHRASE = (
    "approve v566 hwbinder interface-token compatibility proof only; "
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
        raise RuntimeError(f"V566 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["iwifi_service_token_wire"] = keys.get("iwifi_start.service_token_wire", "")
    result["iwifi_last_reply_status_name"] = keys.get("iwifi_start.get.reply.status_name", "")
    result["iwifi_last_reply_status_value"] = keys.get("iwifi_start.get.reply.status_value", "")
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v565-", "v566-", 1) if decision.startswith("v565-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v566-token-compat-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in token compatibility proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v566-token-compat-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    token_wire = live_result.get("iwifi_service_token_wire") or "none"
    status_name = live_result.get("iwifi_last_reply_status_name") or "unknown"
    status_value = live_result.get("iwifi_last_reply_status_value") or "unknown"
    if helper_result == "iwifi-service-null":
        return (
            "v566-token-compat-raw-get-service-null",
            True,
            f"raw hwbinder get still returned service-null after token compatibility probe status={status_name}/{status_value}",
            "inspect HIDL string/object layout or compare with a native lshal/BpHwServiceManager trace",
            live_executed,
        )
    if helper_result == "iwifi-transaction-failed":
        return (
            "v566-token-compat-start-transaction-failed",
            True,
            f"raw get reached IWifi with token_wire={token_wire}, but IWifi.start did not complete cleanly",
            "inspect start reply/status and HAL stderr before scan-only work",
            live_executed,
        )
    if helper_result == "iwifi-start-transaction-pass":
        return (
            "v566-token-compat-start-transaction-pass",
            True,
            f"raw hwbinder IWifi.start completed with token_wire={token_wire} and cleanup safe",
            "inspect WLAN surface/status evidence, then decide bounded scan-only gate",
            live_executed,
        )
    return (
        "v566-token-compat-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V566 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V566 Hwbinder Token Compatibility Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- service_query_result: `{live.get('service_query_result', '')}`",
        f"- iwifi_start_result: `{live.get('iwifi_start_result', '')}`",
        f"- iwifi_service_token_wire: `{live.get('iwifi_service_token_wire', '')}`",
        f"- iwifi_last_reply_status: `{live.get('iwifi_last_reply_status_name', '')}/{live.get('iwifi_last_reply_status_value', '')}`",
        "- repair: raw hwbinder get tries both String16 strict-mode and legacy C-string interface tokens",
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
