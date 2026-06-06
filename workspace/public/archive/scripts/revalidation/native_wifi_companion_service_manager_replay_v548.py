#!/usr/bin/env python3
"""V548 bounded companion replay with private service-manager.

This keeps the V547 bounded companion contract but adds private
`servicemanager` and `hwservicemanager` before QRTR/rmt/tftp/pd-mapper/CNSS.
It does not start Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect,
DHCP, routing, or external ping.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_cleanup_classified_v547 as v547


base = v547.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v548-companion-service-manager-replay")
base.DEFAULT_HELPER_SHA256 = "721f909a698c2b1adcdc4336fd8cd3cc9be15cfe54950d65adc4dfb565d535cd"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v75"
base.HELPER_MODE = "wifi-companion-service-manager-start-only"
base.PROOF_VERSION = "V548"
base.PROOF_SLUG = "v548-companion-service-manager-replay"
base.LIVE_HELPER_STEP_NAME = "v548-helper-run"
base.APPROVAL_PHRASE = (
    "approve v548 companion service-manager replay only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)
base.DMESG_PATTERNS["binder_transaction_failed"] = re.compile(
    r"binder: .*transaction failed", re.IGNORECASE
)
base.DMESG_PATTERNS["binder_oneway_spam_ioctl_unsupported"] = re.compile(
    r"binder: .*ioctl 40046210 .*returned -22", re.IGNORECASE
)

_orig_helper_command = base.helper_command
_orig_run_live = base.run_live
_orig_classify = base.classify


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_helper_command(args)
    if base.approved(args) and "--allow-service-manager-start-only" not in command:
        command.append("--allow-service-manager-start-only")
    return command


def _focus_keys(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_companion_start.",
        "wifi_hal_composite_child.servicemanager.",
        "wifi_hal_composite_child.hwservicemanager.",
        "wifi_hal_composite_child.qrtr_ns.",
        "wifi_hal_composite_child.rmt_storage.",
        "wifi_hal_composite_child.tftp_server.",
        "wifi_hal_composite_child.pd_mapper.",
        "wifi_hal_composite_child.cnss_diag.",
        "wifi_hal_composite_child.cnss_daemon.",
        "wifi_hal_composite_start.property_service_shim.",
    )
    return [[key, keys[key]] for key in sorted(keys) if key.startswith(prefixes)]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    result["focus_keys"] = _focus_keys(result.get("keys") or {})
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    counts = dmesg.get("counts") or {}
    binder_failures = int(counts.get("binder_transaction_failed") or 0)
    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result.get("helper_result")
    if readiness_markers:
        return (
            "v548-companion-service-manager-marker-observed",
            True,
            "service-manager companion replay observed readiness markers: " + ",".join(readiness_markers),
            "advance to bounded HAL/qcwlanstate retry; still no scan/connect",
            live_executed,
        )
    if helper_result == "companion-window-pass" and binder_failures == 0:
        return (
            "v548-companion-service-manager-no-fw-marker-no-binder-fail",
            True,
            "service-manager companion replay cleaned up and binder -22 disappeared, but no FW marker appeared",
            "inspect service-manager registration/fd state, then decide HAL/qcwlanstate bounded retry",
            live_executed,
        )
    if helper_result == "companion-window-pass" and binder_failures > 0:
        return (
            "v548-companion-service-manager-binder-fail-persists",
            True,
            f"service-manager companion replay cleaned up but binder transaction failures persisted: {binder_failures}",
            "inspect servicemanager/hwservicemanager stdout and binder device/context-manager state",
            live_executed,
        )
    return decision, pass_ok, reason, next_step, live_executed


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify


if __name__ == "__main__":
    raise SystemExit(base.main())
