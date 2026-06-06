#!/usr/bin/env python3
"""V588 bounded companion start-only with modem/subsys value capture."""

from __future__ import annotations

import re
from typing import Any

import native_wifi_qrtr_modem_window_surface_v587 as v587


base = v587.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v588-modem-subsys-window-values")
base.DEFAULT_HELPER_SHA256 = "8e10ad0c72d3893c3e8edd427fd92d674e7ed29c84fdbc57ea9f4ed74409a92d"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v99"
base.PROOF_VERSION = "V588"
base.PROOF_SLUG = "v588-modem-subsys-window-values"
base.LIVE_HELPER_STEP_NAME = "v588-helper-run"
base.APPROVAL_PHRASE = (
    "approve v588 modem subsys window value proof only; "
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
    "wifi_companion_start.surface_window.rpmsg_drivers_captured",
    "wifi_companion_start.surface_window.rpmsg_autoprobe_captured",
    "wifi_companion_start.surface_window.remoteproc_captured",
    "wifi_companion_start.surface_window.service_notifier_captured",
    "wifi_companion_start.surface_window.mdm3_captured",
    "wifi_companion_start.surface_window.mss_captured",
    "wifi_companion_start.surface_window.mss_subsys0_state_captured",
    "wifi_companion_start.surface_window.mdm3_subsys9_state_captured",
    "wifi_companion_start.surface_window.subsys_value_captures",
)

VALUE_LABELS = {
    "mss_uevent": "wifi_window_soc_mss_subsys0_uevent",
    "mss_name": "wifi_window_soc_mss_subsys0_name",
    "mss_state": "wifi_window_soc_mss_subsys0_state",
    "mss_restart_level": "wifi_window_soc_mss_subsys0_restart_level",
    "mss_firmware_name": "wifi_window_soc_mss_subsys0_firmware_name",
    "mss_crash_count": "wifi_window_soc_mss_subsys0_crash_count",
    "mdm3_uevent": "wifi_window_soc_mdm3_subsys9_uevent",
    "mdm3_name": "wifi_window_soc_mdm3_subsys9_name",
    "mdm3_state": "wifi_window_soc_mdm3_subsys9_state",
    "mdm3_restart_level": "wifi_window_soc_mdm3_subsys9_restart_level",
    "mdm3_firmware_name": "wifi_window_soc_mdm3_subsys9_firmware_name",
    "mdm3_crash_count": "wifi_window_soc_mdm3_subsys9_crash_count",
    "rpmsg_drivers_autoprobe": "wifi_window_rpmsg_drivers_autoprobe",
}

SURFACE_CAPTURE_RE = re.compile(r"^A90_EXECNS_(?:DIR|PATH)_(wifi_window_[A-Za-z0-9_]+)_BEGIN", re.MULTILINE)
PATH_CAPTURE_RE_TEMPLATE = r"^A90_EXECNS_PATH_{label}_BEGIN[^\n]*\n(.*?)^A90_EXECNS_PATH_{label}_END[^\n]*$"
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


def _path_value(text: str, label: str) -> str:
    pattern = PATH_CAPTURE_RE_TEMPLATE.format(label=re.escape(label))
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    lines = [line.strip() for line in match.group(1).splitlines()]
    payload = "\n".join(line for line in lines if line)
    if payload.startswith("open-error=") or payload.startswith("read-error="):
        return payload
    return payload


def _surface_rows(keys: dict[str, str]) -> list[list[str]]:
    return [[key, keys.get(key, "<missing>")] for key in SURFACE_KEYS]


def _value_rows(values: dict[str, str]) -> list[list[str]]:
    return [[name, values.get(name, "") or "<missing>"] for name in VALUE_LABELS]


def _present_lower_markers(dmesg: dict[str, Any]) -> list[str]:
    counts = dmesg.get("counts") or {}
    return [name for name in LOWER_MARKERS if int(counts.get(name, 0) or 0) > 0]


def _offline_state(value: str) -> bool:
    return value.strip().upper() in {"OFFLINE", "OFFLINING"}


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _BASE_RUN_LIVE(args, store)
    live_text = base.step_payload([result["live"]], base.LIVE_HELPER_STEP_NAME)
    keys = result.get("keys") or {}
    values = {name: _path_value(live_text, label) for name, label in VALUE_LABELS.items()}
    result["window_surface_labels"] = _surface_labels(live_text)
    result["window_surface_summary"] = {key: keys.get(key, "") for key in SURFACE_KEYS}
    result["window_surface_ready"] = all(keys.get(key) not in {"", None} for key in SURFACE_KEYS)
    result["window_subsys_values"] = values
    result["subsys_values_ready"] = int(keys.get("wifi_companion_start.surface_window.subsys_value_captures", "0") or 0) >= 10
    result["mss_state"] = values.get("mss_state", "")
    result["mdm3_state"] = values.get("mdm3_state", "")
    result["modem_subsys_offline_window"] = _offline_state(result["mss_state"]) or _offline_state(result["mdm3_state"])
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _BASE_CLASSIFY(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        if decision.startswith("v587-"):
            decision = decision.replace("v587-", "v588-", 1)
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("window_surface_ready") or not live_result.get("subsys_values_ready"):
        return (
            "v588-subsys-values-missing",
            False,
            "helper v99 did not emit all expected in-window modem/subsys value captures",
            "inspect helper v99 transcript before any further live Wi-Fi retry",
            live_executed,
        )
    markers = _present_lower_markers(dmesg)
    if markers:
        return (
            "v588-subsys-value-marker-observed",
            True,
            "in-window modem/subsys value proof observed lower readiness markers: " + ",".join(markers),
            "advance to bounded qcwlanstate/HAL retry; still no scan/connect until next gate",
            live_executed,
        )
    if live_result.get("modem_subsys_offline_window"):
        return (
            "v588-modem-subsys-offline-window",
            True,
            f"in-window values captured; modem/esoc states are mss={live_result.get('mss_state')} mdm3={live_result.get('mdm3_state')} and QRTR/QMI/WLFW markers remain absent",
            "compare Android boot-time subsystem state and identify the smallest safe subsystem-readiness trigger before qcwlanstate/HAL retry",
            live_executed,
        )
    if live_result.get("helper_result") == "companion-window-pass":
        return (
            "v588-subsys-values-no-readiness-delta",
            True,
            "in-window modem/subsys values were captured and companions cleaned, but no lower readiness marker appeared",
            "compare Android/native subsystem values and plan the next readiness input proof before qcwlanstate/HAL retry",
            live_executed,
        )
    if decision.startswith("v587-"):
        decision = decision.replace("v587-", "v588-", 1)
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    live = manifest.get("live_result") or {}
    keys = live.get("keys") or {}
    values = live.get("window_subsys_values") or {}
    labels = live.get("window_surface_labels") or []
    extra = "\n".join([
        "## V588 Modem/Subsys Window Values",
        "",
        base.markdown_table(["key", "value"], _surface_rows(keys)),
        "",
        "## V588 Captured Values",
        "",
        base.markdown_table(["name", "value"], _value_rows(values)),
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
