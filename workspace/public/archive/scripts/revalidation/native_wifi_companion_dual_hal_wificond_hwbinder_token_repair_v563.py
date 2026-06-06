#!/usr/bin/env python3
"""V563 bounded hwbinder interface-token repair proof in the dual-HAL window."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_v562 as v562


base = v562.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v563-companion-dual-hal-wificond-hwbinder-token-repair")
base.DEFAULT_HELPER_SHA256 = "79091d23838d8fa1d98c1ba3868660be4ee25732c34b3bb429993c52772744e4"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v88"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V563"
base.PROOF_SLUG = "v563-companion-dual-hal-wificond-hwbinder-token-repair"
base.LIVE_HELPER_STEP_NAME = "v563-helper-run"
base.APPROVAL_PHRASE = (
    "approve v563 hwbinder interface-token repair proof only; "
    "no supplicant, no scan/connect/link-up and no external ping"
)

_orig_helper_command = base.helper_command
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
        raise RuntimeError(f"V563 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v562-", "v563-", 1) if decision.startswith("v562-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v563-hwbinder-token-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in token repair proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v563-hwbinder-token-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    helper_result = live_result.get("helper_result")
    if helper_result == "iwifi-start-registration-query-failed":
        return (
            "v563-lshal-precheck-failed",
            True,
            "same-window lshal wait did not confirm IWifi/default, so raw IWifi.start was skipped",
            "inspect service registration evidence before retry",
            live_executed,
        )
    if helper_result == "iwifi-service-null":
        return (
            "v563-token-repair-raw-get-service-null",
            True,
            "String16 interface token was used but raw hwbinder get still returned service-null",
            "inspect HIDL string buffer-object layout and returned reply metadata",
            live_executed,
        )
    if helper_result == "iwifi-transaction-failed":
        return (
            "v563-token-repair-start-transaction-failed",
            True,
            "raw hwbinder get reached IWifi/start path but the start transaction did not complete cleanly",
            "inspect start reply/status and HAL stderr before scan-only work",
            live_executed,
        )
    if helper_result == "iwifi-start-transaction-pass":
        return (
            "v563-token-repair-start-transaction-pass",
            True,
            "raw hwbinder IWifi.start transaction completed with cleanup safe",
            "inspect WLAN surface/status evidence, then decide bounded scan-only gate",
            live_executed,
        )
    return (
        "v563-token-repair-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V563 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V563 Hwbinder Token Repair Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- service_query_result: `{live.get('service_query_result', '')}`",
        f"- iwifi_start_result: `{live.get('iwifi_start_result', '')}`",
        "- repair: raw hwbinder interface token now follows `Parcel::writeInterfaceToken` String16 framing",
        "- forbidden: `supplicant`, `hostapd`, `scan/connect/link-up`, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
