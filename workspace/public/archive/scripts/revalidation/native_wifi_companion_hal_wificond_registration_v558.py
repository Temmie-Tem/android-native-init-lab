#!/usr/bin/env python3
"""V558 bounded companion plus HAL plus wificond Samsung registration wait.

This reuses the V557 order proof but switches to helper v83's
registration-query mode. The helper starts the same bounded 11-child window,
then runs only `/system/bin/lshal wait` for Samsung Wi-Fi HAL fqinstances.

The proof does not call IWifi.start, supplicant, hostapd, scan/connect/link-up,
credentials, DHCP, routes, external ping, reboot, or boot partition writes.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_hal_wificond_order_v557 as v557


base = v557.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v558-companion-hal-wificond-registration")
base.DEFAULT_HELPER_SHA256 = "79af5542abe0c2f73641302f82b8e481654844ed983e0e4eb7ae367afb9d0111"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v83"
base.HELPER_MODE = "wifi-companion-hal-wificond-lshal-wait-samsung"
base.PROOF_VERSION = "V558"
base.PROOF_SLUG = "v558-companion-hal-wificond-registration"
base.LIVE_HELPER_STEP_NAME = "v558-helper-run"
base.APPROVAL_PHRASE = (
    "approve v558 companion plus HAL plus wificond Samsung registration wait only; "
    "no IWifi.start, no supplicant, no scan/connect/link-up and no external ping"
)
base.KEY_RE = re.compile(
    r"^(wifi_companion_hal_order|wifi_companion_qrtr_readback|wifi_hal_composite_start|wifi_hal_composite_child|wifi_hal_micro_query|capture)\.([A-Za-z0-9_.-]+)=(.*)$"
)

DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
MAX_CMDV1_COMMAND_ARGS = 30

_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_classify = base.classify


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
        ])
    command.extend([
        "--property-root", DEFAULT_PROPERTY_ROOT,
    ])
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(
            f"V558 helper command has {len(command)} args; cmdv1 safely carries "
            f"at most {MAX_CMDV1_COMMAND_ARGS} command args"
        )
    return command


def _registration_focus_keys(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_companion_hal_order.",
        "wifi_hal_micro_query.",
        "wifi_hal_composite_child.servicemanager.",
        "wifi_hal_composite_child.hwservicemanager.",
        "wifi_hal_composite_child.vndservicemanager.",
        "wifi_hal_composite_child.wifi_hal.",
        "wifi_hal_composite_child.wificond.",
        "wifi_hal_composite_child.cnss_daemon.",
    )
    return [[key, keys[key]] for key in sorted(keys) if key.startswith(prefixes)]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["helper_result"] = keys.get("wifi_companion_hal_order.result", "missing")
    result["service_query_result"] = keys.get("wifi_companion_hal_order.service_query_result", "")
    result["micro_query_result"] = keys.get("wifi_hal_micro_query.result", "")
    result["micro_query_reason"] = keys.get("wifi_hal_micro_query.reason", "")
    result["matched_fqinstance"] = keys.get("wifi_hal_micro_query.matched_fqinstance", "")
    result["registration_focus_keys"] = _registration_focus_keys(keys)
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v557-", "v558-", 1) if decision.startswith("v557-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v558-registration-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in registration wait proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v558-registration-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result.get("helper_result")
    micro_result = live_result.get("micro_query_result")
    matched = live_result.get("matched_fqinstance")
    if readiness_markers:
        return (
            "v558-registration-marker-observed",
            True,
            "registration wait window observed readiness markers: " + ",".join(readiness_markers),
            "move to bounded IWifi.start or scan-only surface; still no credential connect until scan proof",
            live_executed,
        )
    if helper_result == "service-query-pass":
        return (
            "v558-samsung-registration-observed",
            True,
            f"Samsung Wi-Fi HAL registration observed: {matched or micro_result}",
            "move to bounded IWifi.start surface before scan/connect",
            live_executed,
        )
    if helper_result == "service-query-timeout":
        return (
            "v558-samsung-registration-timeout",
            True,
            "Samsung Wi-Fi HAL registration did not appear in the 11-child companion/HAL/wificond window",
            "test whether the missing Android legacy Wi-Fi HAL process is required before retrying IWifi.start",
            live_executed,
        )
    if helper_result in {"service-query-runtime-gap", "start-only-runtime-gap"}:
        return (
            "v558-registration-runtime-gap",
            True,
            f"registration query did not complete cleanly: helper_result={helper_result} micro={micro_result}",
            "inspect lshal stderr/stdout and child lifecycle evidence",
            live_executed,
        )
    return (
        "v558-registration-review-required",
        False,
        f"helper_result={helper_result} micro={micro_result}",
        "inspect V558 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    rows = live.get("registration_focus_keys") or []
    extra = "\n".join([
        "## V558 Samsung Registration Wait",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- service_query_result: `{live.get('service_query_result', '')}`",
        f"- micro_query_result: `{live.get('micro_query_result', '')}`",
        f"- micro_query_reason: `{live.get('micro_query_reason', '')}`",
        f"- matched_fqinstance: `{live.get('matched_fqinstance', '')}`",
        "",
        base.markdown_table(["key", "value"], rows[:180]) if rows else "- none",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
