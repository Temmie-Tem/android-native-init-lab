#!/usr/bin/env python3
"""V549 bounded companion replay with vndservicemanager.

This keeps the V548 bounded companion contract but adds Android's
`vndservicemanager /dev/vndbinder` before QRTR/rmt/tftp/pd-mapper/CNSS. It
does not start Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect,
DHCP, routing, or external ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_service_manager_replay_v548 as v548


base = v548.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v549-companion-vnd-service-manager-replay")
base.DEFAULT_HELPER_SHA256 = "ef27bc049fd7cbccb7612df683ad95f94069839bf2b1b146990df7095a4cf66c"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v76"
base.HELPER_MODE = "wifi-companion-vnd-service-manager-start-only"
base.PROOF_VERSION = "V549"
base.PROOF_SLUG = "v549-companion-vnd-service-manager-replay"
base.LIVE_HELPER_STEP_NAME = "v549-helper-run"
base.APPROVAL_PHRASE = (
    "approve v549 companion vnd service-manager replay only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_run_live = base.run_live
_orig_classify = base.classify


def _vnd_focus_keys(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_hal_composite_child.vndservicemanager.",
        "wifi_companion_start.child.vndservicemanager.",
        "wifi_companion_start.with_vnd_service_manager",
        "wifi_companion_start.vndservicemanager_argv",
    )
    return [[key, keys[key]] for key in sorted(keys) if key.startswith(prefixes)]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    result["vnd_focus_keys"] = _vnd_focus_keys(result.get("keys") or {})
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    keys = live_result.get("keys") or {}
    counts = dmesg.get("counts") or {}
    binder_failures = int(counts.get("binder_transaction_failed") or 0)
    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result.get("helper_result")
    vnd_observable = keys.get("wifi_companion_start.child.vndservicemanager.observable") == "1"
    if readiness_markers:
        return (
            "v549-companion-vnd-service-manager-marker-observed",
            True,
            "vnd service-manager replay observed readiness markers: " + ",".join(readiness_markers),
            "advance to bounded HAL/qcwlanstate retry; still no scan/connect",
            live_executed,
        )
    if helper_result == "companion-window-pass" and vnd_observable and binder_failures == 0:
        return (
            "v549-companion-vnd-service-manager-binder-gap-cleared",
            True,
            "vndservicemanager was observable and binder transaction failures disappeared, but no FW marker appeared",
            "inspect QRTR/QMI state, then decide HAL/qcwlanstate bounded retry",
            live_executed,
        )
    if helper_result == "companion-window-pass" and vnd_observable and binder_failures > 0:
        return (
            "v549-companion-vnd-service-manager-binder-fail-persists",
            True,
            f"vndservicemanager was observable but binder transaction failures persisted: {binder_failures}",
            "inspect vndservicemanager registration and cnss-daemon vndbinder transactions",
            live_executed,
        )
    return decision, pass_ok, reason, next_step, live_executed


base.run_live = run_live
base.classify = classify


if __name__ == "__main__":
    raise SystemExit(base.main())
