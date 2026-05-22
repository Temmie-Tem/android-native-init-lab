#!/usr/bin/env python3
"""V587 bounded companion start-only with in-window QRTR/modem surface capture."""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_firmware_mount_start_only_v585 as v585


base = v585.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v587-qrtr-modem-window-surface")
base.DEFAULT_HELPER_SHA256 = "be9b59f20af3013e996266e35c225487d266d789455a4f656dfaa2efeacd7f23"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v98"
base.PROOF_VERSION = "V587"
base.PROOF_SLUG = "v587-qrtr-modem-window-surface"
base.LIVE_HELPER_STEP_NAME = "v587-helper-run"
base.APPROVAL_PHRASE = (
    "approve v587 QRTR modem window surface proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_BASE_RUN_LIVE = base.run_live
_BASE_CLASSIFY = base.classify
_BASE_RENDER_SUMMARY = base.render_summary

SURFACE_KEYS = (
    "wifi_companion_start.surface_window.proc_qrtr_captured",
    "wifi_companion_start.surface_window.dev_filtered_captured",
    "wifi_companion_start.surface_window.msm_subsys_captured",
    "wifi_companion_start.surface_window.rpmsg_captured",
    "wifi_companion_start.surface_window.remoteproc_captured",
    "wifi_companion_start.surface_window.service_notifier_captured",
    "wifi_companion_start.surface_window.mdm3_captured",
    "wifi_companion_start.surface_window.mss_captured",
)

SURFACE_CAPTURE_RE = re.compile(r"^A90_EXECNS_(?:DIR|PATH)_(wifi_window_[A-Za-z0-9_]+)_BEGIN", re.MULTILINE)
LOWER_MARKERS = (
    "qrtr_modem_readiness",
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wcnss_cfg_request",
    "wma_service_ready",
    "wlan0_event",
)


def _surface_labels(text: str) -> list[str]:
    labels = []
    for match in SURFACE_CAPTURE_RE.finditer(text):
        label = match.group(1)
        if label not in labels:
            labels.append(label)
    return labels


def _surface_rows(keys: dict[str, str]) -> list[list[str]]:
    rows = []
    for key in SURFACE_KEYS:
        rows.append([key, keys.get(key, "<missing>")])
    return rows


def _present_lower_markers(dmesg: dict[str, Any]) -> list[str]:
    counts = dmesg.get("counts") or {}
    return [name for name in LOWER_MARKERS if int(counts.get(name, 0) or 0) > 0]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _BASE_RUN_LIVE(args, store)
    live_text = base.step_payload([result["live"]], base.LIVE_HELPER_STEP_NAME)
    keys = result.get("keys") or {}
    result["window_surface_labels"] = _surface_labels(live_text)
    result["window_surface_summary"] = {key: keys.get(key, "") for key in SURFACE_KEYS}
    result["window_surface_ready"] = all(keys.get(key) in {"0", "1"} for key in SURFACE_KEYS)
    result["window_proc_qrtr_captured"] = keys.get("wifi_companion_start.surface_window.proc_qrtr_captured") == "1"
    result["window_msm_subsys_captured"] = keys.get("wifi_companion_start.surface_window.msm_subsys_captured") == "1"
    result["window_rpmsg_captured"] = keys.get("wifi_companion_start.surface_window.rpmsg_captured") == "1"
    result["window_service_notifier_captured"] = keys.get("wifi_companion_start.surface_window.service_notifier_captured") == "1"
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _BASE_CLASSIFY(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        if decision.startswith("v585-"):
            decision = decision.replace("v585-", "v587-", 1)
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("window_surface_ready"):
        return (
            "v587-window-surface-missing",
            False,
            "helper v98 did not emit all expected in-window QRTR/modem surface capture keys",
            "inspect helper v98 transcript before any further live Wi-Fi retry",
            live_executed,
        )
    markers = _present_lower_markers(dmesg)
    if markers:
        return (
            "v587-window-surface-marker-observed",
            True,
            "in-window surface proof observed lower readiness markers: " + ",".join(markers),
            "advance to bounded qcwlanstate/HAL retry; still no scan/connect until next gate",
            live_executed,
        )
    if live_result.get("helper_result") == "companion-window-pass":
        return (
            "v587-window-surface-no-readiness-delta",
            True,
            "helper v98 captured in-window QRTR/modem surfaces and cleaned companions, but no QRTR/QMI/WLFW/BDF/FW-ready marker appeared",
            "compare Android/native modem/rpmsg/subsys inputs or plan the smallest host-controlled QRTR readiness input proof before qcwlanstate/HAL retry",
            live_executed,
        )
    if decision.startswith("v585-"):
        decision = decision.replace("v585-", "v587-", 1)
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    live = manifest.get("live_result") or {}
    keys = live.get("keys") or {}
    surface_rows = _surface_rows(keys)
    labels = live.get("window_surface_labels") or []
    extra = "\n".join([
        "## V587 Window Surface Captures",
        "",
        base.markdown_table(["key", "value"], surface_rows),
        "",
        "captured labels: " + (", ".join(labels) if labels else "<none>"),
        "",
        "- forbidden: service-manager, Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
