#!/usr/bin/env python3
"""V556 bounded companion plus Wi-Fi HAL order proof.

This reuses the current companion replay harness but switches the helper to
v81's combined order mode:

servicemanager -> hwservicemanager -> vndservicemanager -> qrtr-ns ->
rmt_storage -> tftp_server -> pd-mapper -> Wi-Fi HAL -> cnss_diag ->
cnss-daemon.

The proof is still start-only. It does not start wificond, supplicant, hostapd,
scan/connect/link-up, credentials, DHCP, routes, external ping, reboot, or boot
partition writes.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_qrtr_readback_v554 as v554


base = v554.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v556-companion-hal-order")
base.DEFAULT_HELPER_SHA256 = "b5b72889bca65a69523946afa914979f0ca8b921809f44aebb6de30debcc41c9"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v81"
base.HELPER_MODE = "wifi-companion-hal-order-start-only"
base.PROOF_VERSION = "V556"
base.PROOF_SLUG = "v556-companion-hal-order"
base.LIVE_HELPER_STEP_NAME = "v556-helper-run"
base.APPROVAL_PHRASE = (
    "approve v556 companion plus HAL order start-only proof only; "
    "no wificond, no supplicant, no scan/connect/link-up and no external ping"
)
base.KEY_RE = re.compile(
    r"^(wifi_companion_hal_order|wifi_companion_qrtr_readback|wifi_hal_composite_start|wifi_hal_composite_child|capture)\.([A-Za-z0-9_.-]+)=(.*)$"
)

REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
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
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "copy-real",
        "--android-selinux-context-mode", "service-defaults",
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if base.approved(args):
        command.extend([
            "--allow-cnss-start-only",
            "--allow-wifi-companion-start-only",
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
        ])
    command.extend([
        "--property-root", DEFAULT_PROPERTY_ROOT,
        "--linkerconfig-source", REAL_LD_CONFIG,
        "--apex-libraries-source", REAL_APEX_LIBRARIES,
    ])
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(
            f"V556 helper command has {len(command)} args; cmdv1 safely carries "
            f"at most {MAX_CMDV1_COMMAND_ARGS} command args"
        )
    return command


def _order_focus_keys(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_companion_hal_order.",
        "wifi_hal_composite_child.servicemanager.",
        "wifi_hal_composite_child.hwservicemanager.",
        "wifi_hal_composite_child.vndservicemanager.",
        "wifi_hal_composite_child.qrtr_ns.",
        "wifi_hal_composite_child.rmt_storage.",
        "wifi_hal_composite_child.tftp_server.",
        "wifi_hal_composite_child.pd_mapper.",
        "wifi_hal_composite_child.wifi_hal.",
        "wifi_hal_composite_child.cnss_diag.",
        "wifi_hal_composite_child.cnss_daemon.",
    )
    return [[key, keys[key]] for key in sorted(keys) if key.startswith(prefixes)]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["helper_result"] = keys.get("wifi_companion_hal_order.result", "missing")
    result["all_postflight_safe"] = keys.get("wifi_companion_hal_order.all_postflight_safe") == "1"
    result["all_observable"] = keys.get("wifi_companion_hal_order.all_observable_at_timeout") == "1"
    result["order_focus_keys"] = _order_focus_keys(keys)
    result["wifi_hal_started"] = keys.get("wifi_companion_hal_order.wifi_hal") == "1"
    result["scan_connect_linkup"] = keys.get("wifi_companion_hal_order.scan_connect_linkup") == "1"
    result["external_ping"] = keys.get("wifi_companion_hal_order.external_ping") == "1"
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v554-", "v556-", 1) if decision.startswith("v554-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v556-order-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in start-only proof",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v556-order-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )

    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result.get("helper_result")
    if readiness_markers:
        return (
            "v556-order-marker-observed",
            True,
            "combined companion plus HAL order window observed readiness markers: " + ",".join(readiness_markers),
            "move to bounded scan-only or IWifi.start surface; still no credential connect until scan proof",
            live_executed,
        )
    if helper_result == "order-window-pass":
        return (
            "v556-order-no-fw-marker",
            True,
            "combined companion plus HAL order window stayed alive and cleaned, but no WLFW/QMI/BDF/wlan0 marker appeared",
            "inspect HAL stderr/service registration and consider adding the next Android boundary wificond start-only",
            live_executed,
        )
    if helper_result == "start-only-runtime-gap":
        return (
            "v556-order-runtime-gap",
            True,
            "one combined-order child exited before the observe window",
            "inspect child stdout/stderr, SELinux, property, and linker surfaces",
            live_executed,
        )
    return (
        "v556-order-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V556 transcript",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    order_rows = live.get("order_focus_keys") or []
    extra = "\n".join([
        "## Companion + HAL Order Keys",
        "",
        base.markdown_table(["key", "value"], order_rows[:180]) if order_rows else "- none",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
