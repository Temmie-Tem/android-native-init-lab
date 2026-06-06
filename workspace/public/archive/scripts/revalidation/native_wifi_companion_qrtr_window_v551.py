#!/usr/bin/env python3
"""V551 bounded QRTR window snapshot.

This reuses the V550 copy-real vndservicemanager companion replay and expects
helper v77, which captures QIPCRTR socket counts and per-child fd links while
the companion daemons are alive. It does not start Wi-Fi HAL, send QRTR
nameservice lookups, send QMI payloads, scan/connect/link-up, or ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_companion_vnd_service_manager_copyreal_v550 as v550


base = v550.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v551-companion-qrtr-window")
base.DEFAULT_HELPER_SHA256 = "905d8edefa0ff02f756a8e0d1d3b1706d15b5001dd7bda4f59d9885fc688d8ba"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v77"
base.PROOF_VERSION = "V551"
base.PROOF_SLUG = "v551-companion-qrtr-window"
base.LIVE_HELPER_STEP_NAME = "v551-helper-run"
base.APPROVAL_PHRASE = (
    "approve v551 companion QRTR window snapshot only; "
    "no QRTR nameservice transmit, no QMI payload, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_classify = base.classify


def _to_int(value: object, default: int = -1) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def _qrtr_window_rows(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "wifi_companion_start.net_",
        "capture.wifi_hal_composite_qrtr_ns.fd_links.",
        "capture.wifi_hal_composite_tftp_server.fd_links.",
        "capture.wifi_hal_composite_pd_mapper.fd_links.",
        "capture.wifi_hal_composite_cnss_diag.fd_links.",
        "capture.wifi_hal_composite_cnss_daemon.fd_links.",
    )
    rows = [[key, keys[key]] for key in sorted(keys) if key.startswith(prefixes)]
    return rows[:160]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    result["qrtr_window_keys"] = _qrtr_window_rows(result.get("keys") or {})
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("all_postflight_safe"):
        return decision, pass_ok, reason, next_step, live_executed

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    readiness_markers = dmesg.get("readiness_markers") or []
    before_sockets = _to_int(keys.get("wifi_companion_start.net_before.qipcrtr_sockets"))
    after_spawn_sockets = _to_int(keys.get("wifi_companion_start.net_after_spawn.qipcrtr_sockets"))
    window_sockets = _to_int(keys.get("wifi_companion_start.net_window.qipcrtr_sockets"))
    after_cleanup_sockets = _to_int(keys.get("wifi_companion_start.net_after_cleanup.qipcrtr_sockets"))
    qipcrtr_present = keys.get("wifi_companion_start.net_window.qipcrtr_present") == "1"
    qrtr_proc_captured = keys.get("wifi_companion_start.net_window.qrtr_captured") == "1"

    if helper_result != "companion-window-pass":
        return decision, pass_ok, reason, next_step, live_executed
    if readiness_markers:
        return (
            "v551-qrtr-window-marker-observed",
            True,
            "QRTR window snapshot observed readiness markers: " + ",".join(readiness_markers),
            "advance to bounded HAL/qcwlanstate retry; still no scan/connect unless explicitly gated",
            live_executed,
        )
    if not qipcrtr_present:
        return (
            "v551-qrtr-window-protocol-missing",
            True,
            "QIPCRTR protocol was not visible in the in-window protocol snapshot",
            "inspect kernel QRTR support and daemon socket failures before HAL retry",
            live_executed,
        )
    if window_sockets <= 0:
        return (
            "v551-qrtr-window-no-qipcrtr-sockets",
            True,
            f"QIPCRTR protocol is present but socket count stayed empty: before={before_sockets} after_spawn={after_spawn_sockets} window={window_sockets} after_cleanup={after_cleanup_sockets}",
            "inspect qrtr-ns/tftp/pd-mapper fd links and SELinux/runtime setup before any QRTR transmit",
            live_executed,
        )
    return (
        "v551-qrtr-window-sockets-visible-no-fw-marker",
        True,
        f"QIPCRTR sockets were visible during companion window: before={before_sockets} after_spawn={after_spawn_sockets} window={window_sockets} after_cleanup={after_cleanup_sockets} proc_qrtr_captured={qrtr_proc_captured}",
        "consider bounded QRTR nameservice readback inside the working companion window; no QMI payload and no Wi-Fi bring-up",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    rows = (manifest.get("live_result") or {}).get("qrtr_window_keys") or []
    return "\n".join([
        text,
        "",
        "## QRTR Window Keys",
        "",
        base.markdown_table(["key", "value"], rows) if rows else "- none",
    ])


base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
