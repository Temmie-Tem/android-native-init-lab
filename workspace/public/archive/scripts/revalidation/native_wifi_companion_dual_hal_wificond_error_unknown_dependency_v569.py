#!/usr/bin/env python3
"""V569 bounded IWifi.start ERROR_UNKNOWN dependency classifier."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_iwifi_start_status_v568 as v568


base = v568.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v569-companion-dual-hal-wificond-error-unknown-dependency")
base.DEFAULT_HELPER_SHA256 = "1e9e60c937de8930f87ea62849824d15ab0efba689da8b5fa26a3ebd83095902"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v93"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V569"
base.PROOF_SLUG = "v569-companion-dual-hal-wificond-error-unknown-dependency"
base.LIVE_HELPER_STEP_NAME = "v569-helper-run"
base.APPROVAL_PHRASE = (
    "approve v569 IWifi.start ERROR_UNKNOWN dependency classifier only; "
    "no QMI payload, no supplicant, no scan/connect/link-up and no external ping"
)

_orig_run_live = base.run_live
_orig_classify = base.classify
_orig_render_summary = base.render_summary

MAX_CMDV1_COMMAND_ARGS = 30
QRTR_CASES = (0, 1)
CAPTURE_LABELS = (
    "wifi_hal_composite_qrtr_ns",
    "wifi_hal_composite_rmt_storage",
    "wifi_hal_composite_tftp_server",
    "wifi_hal_composite_pd_mapper",
    "wifi_hal_composite_wifi_hal_legacy",
    "wifi_hal_composite_wifi_hal_ext",
    "wifi_hal_composite_cnss_diag",
    "wifi_hal_composite_cnss_daemon",
)


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = v568.helper_command(args)
    if base.approved(args):
        command.append("--allow-qrtr-ns-readback")
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(
            f"V569 helper command has {len(command)} args; cmdv1 safely carries "
            f"at most {MAX_CMDV1_COMMAND_ARGS} command args"
        )
    return command


def _int_value(keys: dict[str, str], key: str) -> int:
    try:
        return int(keys.get(key, "0"), 0)
    except ValueError:
        return 0


def _qrtr_readback_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in QRTR_CASES:
        prefix = f"wifi_companion_qrtr_readback.case_{index}"
        rows.append({
            "case": str(index),
            "service": keys.get(f"{prefix}.service", ""),
            "instance": keys.get(f"{prefix}.instance", ""),
            "socket_rc": keys.get(f"{prefix}.socket.rc", ""),
            "new_lookup_rc": keys.get(f"{prefix}.new_lookup_send.rc", ""),
            "del_lookup_rc": keys.get(f"{prefix}.del_lookup_send.rc", ""),
            "events": keys.get(f"{prefix}.readback.events", ""),
            "service_events": keys.get(f"{prefix}.readback.service_events", ""),
            "end_of_list": keys.get(f"{prefix}.readback.end_of_list", ""),
            "timeout": keys.get(f"{prefix}.readback.timeout", ""),
            "qmi_attempted": keys.get(f"{prefix}.qmi_attempted", ""),
            "status": keys.get(f"{prefix}.status", ""),
        })
    return rows


def _capture_socket_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label in CAPTURE_LABELS:
        prefix = f"capture.{label}.fd_links"
        rows.append({
            "label": label.replace("wifi_hal_composite_", ""),
            "fd_count": keys.get(f"{prefix}.count", ""),
            "socket_count": keys.get(f"{prefix}.socket_count", ""),
            "anon_inode_count": keys.get(f"{prefix}.anon_inode_count", ""),
            "truncated": keys.get(f"{prefix}.truncated", ""),
        })
    return rows


def _runtime_focus_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    paths = (
        "dev_socket_wifihal",
        "dev_socket_wifihal_ctrlsock",
        "data_vendor_wifi",
        "data_vendor_wifi_sockets",
        "data_vendor_wifi_sockets_wlan0",
        "sys_class_net_wlan0",
    )
    for label in ("runtime_before", "runtime_after_iwifi_start", "runtime_window"):
        for path_key in paths:
            host_prefix = f"wifi_companion_hal_order.{label}.host.{path_key}"
            private_prefix = f"wifi_companion_hal_order.{label}.private.{path_key}"
            rows.append({
                "phase": label,
                "path": path_key,
                "host_exists": keys.get(f"{host_prefix}.exists", ""),
                "private_exists": keys.get(f"{private_prefix}.exists", ""),
                "private_mode": keys.get(f"{private_prefix}.mode", ""),
                "private_uid": keys.get(f"{private_prefix}.uid", ""),
                "private_gid": keys.get(f"{private_prefix}.gid", ""),
            })
    return rows


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    result["qrtr_readback_send_attempted"] = keys.get("wifi_companion_qrtr_readback.send_attempted", "")
    result["qrtr_readback_result"] = keys.get("wifi_companion_qrtr_readback.result", "")
    result["qrtr_readback_rows"] = _qrtr_readback_rows(keys)
    result["qrtr_readback_service_events"] = sum(
        _int_value(keys, f"wifi_companion_qrtr_readback.case_{index}.readback.service_events")
        for index in QRTR_CASES
    )
    result["qrtr_readback_timeouts"] = sum(
        _int_value(keys, f"wifi_companion_qrtr_readback.case_{index}.readback.timeout")
        for index in QRTR_CASES
    )
    result["qrtr_readback_end_of_list"] = sum(
        _int_value(keys, f"wifi_companion_qrtr_readback.case_{index}.readback.end_of_list")
        for index in QRTR_CASES
    )
    result["qrtr_readback_qmi_attempted"] = sum(
        _int_value(keys, f"wifi_companion_qrtr_readback.case_{index}.qmi_attempted")
        for index in QRTR_CASES
    )
    result["qipcrtr_sockets_before"] = keys.get("wifi_companion_hal_order.net_before.qipcrtr_sockets", "")
    result["qipcrtr_sockets_after_spawn"] = keys.get("wifi_companion_hal_order.net_after_spawn.qipcrtr_sockets", "")
    result["qipcrtr_sockets_window"] = keys.get("wifi_companion_hal_order.net_window.qipcrtr_sockets", "")
    result["qipcrtr_sockets_after_cleanup"] = keys.get("wifi_companion_hal_order.net_after_cleanup.qipcrtr_sockets", "")
    result["runtime_data_vendor_wifi_exists"] = keys.get(
        "wifi_companion_hal_order.runtime_after_iwifi_start.private.data_vendor_wifi.exists", ""
    )
    result["runtime_data_vendor_wifi_sockets_exists"] = keys.get(
        "wifi_companion_hal_order.runtime_after_iwifi_start.private.data_vendor_wifi_sockets.exists", ""
    )
    result["runtime_wlan0_socket_exists"] = keys.get(
        "wifi_companion_hal_order.runtime_after_iwifi_start.private.data_vendor_wifi_sockets_wlan0.exists", ""
    )
    result["runtime_sys_wlan0_exists"] = keys.get(
        "wifi_companion_hal_order.runtime_after_iwifi_start.private.sys_class_net_wlan0.exists", ""
    )
    result["capture_socket_rows"] = _capture_socket_rows(keys)
    result["runtime_focus_rows"] = _runtime_focus_rows(keys)
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v568-", "v569-", 1) if decision.startswith("v568-") else decision, pass_ok, reason, next_step, live_executed
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v569-error-unknown-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in dependency classifier",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v569-error-unknown-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )
    if int(live_result.get("qrtr_readback_qmi_attempted") or 0):
        return (
            "v569-error-unknown-qmi-guard-failed",
            False,
            "unexpected QMI payload attempt during QRTR dependency classifier",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if live_result.get("qrtr_readback_send_attempted") != "1":
        return (
            "v569-error-unknown-qrtr-readback-not-sent",
            False,
            "WLFW QRTR nameservice readback did not execute",
            "inspect approval flag and helper command length before retry",
            live_executed,
        )

    status_name = live_result.get("iwifi_start_wifi_status_name") or "UNDECODED"
    status_code = live_result.get("iwifi_start_wifi_status_code") or ""
    service_events = int(live_result.get("qrtr_readback_service_events") or 0)
    qipcrtr_window = live_result.get("qipcrtr_sockets_window") or "unknown"
    readiness_markers = dmesg.get("readiness_markers") or []
    if status_name == "SUCCESS":
        return (
            "v569-iwifi-start-success-before-scan",
            True,
            "IWifi.start returned SUCCESS; scan/connect was still blocked",
            "move to separate bounded scan-only proof",
            live_executed,
        )
    if readiness_markers:
        return (
            "v569-error-unknown-readiness-marker-observed",
            True,
            f"IWifi.start={status_name}/{status_code} but readiness markers appeared: {readiness_markers}",
            "inspect firmware/netdev surface and decide whether a delayed retry is justified",
            live_executed,
        )
    if status_name == "ERROR_UNKNOWN" and service_events == 0 and qipcrtr_window in {"0", "unknown"}:
        return (
            "v569-error-unknown-qrtr-wlfw-missing",
            True,
            f"IWifi.start returned ERROR_UNKNOWN/{status_code}; WLFW readback had no service events and QIPCRTR sockets={qipcrtr_window}",
            "compare Android-vs-native QRTR/modem readiness and repair companion/modem dependency before scan-only work",
            live_executed,
        )
    if status_name == "ERROR_UNKNOWN" and service_events > 0:
        return (
            "v569-error-unknown-non-qrtr-runtime-gap",
            True,
            f"IWifi.start returned ERROR_UNKNOWN/{status_code} despite WLFW service_events={service_events}",
            "inspect firmware/BDF, /data/vendor/wifi, HAL logs, and CNSS logs before scan-only work",
            live_executed,
        )
    return (
        "v569-error-unknown-review-required",
        False,
        f"IWifi.start status={status_name}/{status_code} service_events={service_events} qipcrtr_sockets={qipcrtr_window}",
        "inspect V569 transcript before further live action",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    qrtr_rows = [
        [
            row["case"],
            row["service"],
            row["instance"],
            row["socket_rc"],
            row["new_lookup_rc"],
            row["del_lookup_rc"],
            row["events"],
            row["service_events"],
            row["end_of_list"],
            row["timeout"],
            row["qmi_attempted"],
            row["status"],
        ]
        for row in (live.get("qrtr_readback_rows") or [])
    ]
    socket_rows = [
        [
            row["label"],
            row["fd_count"],
            row["socket_count"],
            row["anon_inode_count"],
            row["truncated"],
        ]
        for row in (live.get("capture_socket_rows") or [])
    ]
    runtime_rows = [
        [
            row["phase"],
            row["path"],
            row["host_exists"],
            row["private_exists"],
            row["private_mode"],
            row["private_uid"],
            row["private_gid"],
        ]
        for row in (live.get("runtime_focus_rows") or [])
    ]
    extra = "\n".join([
        "## V569 ERROR_UNKNOWN Dependency Classifier",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- iwifi_start_wifi_status: `{live.get('iwifi_start_wifi_status_name', '')}/{live.get('iwifi_start_wifi_status_code', '')}`",
        f"- qrtr_readback_result: `{live.get('qrtr_readback_result', '')}`",
        f"- qrtr_readback_service_events: `{live.get('qrtr_readback_service_events', 0)}`",
        f"- qrtr_readback_timeouts: `{live.get('qrtr_readback_timeouts', 0)}`",
        f"- qipcrtr_sockets: `before={live.get('qipcrtr_sockets_before', '')} after_spawn={live.get('qipcrtr_sockets_after_spawn', '')} window={live.get('qipcrtr_sockets_window', '')} cleanup={live.get('qipcrtr_sockets_after_cleanup', '')}`",
        f"- data_vendor_wifi_private: `{live.get('runtime_data_vendor_wifi_exists', '')}`",
        f"- data_vendor_wifi_sockets_private: `{live.get('runtime_data_vendor_wifi_sockets_exists', '')}`",
        f"- wlan0_socket_private: `{live.get('runtime_wlan0_socket_exists', '')}`",
        f"- sys_wlan0_private: `{live.get('runtime_sys_wlan0_exists', '')}`",
        "- forbidden: QMI payload, `supplicant`, `hostapd`, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
        "### V569 QRTR WLFW Readback",
        "",
        base.markdown_table(
            ["case", "service", "instance", "socket_rc", "new_lookup_rc", "del_lookup_rc", "events", "service_events", "end_of_list", "timeout", "qmi_attempted", "status"],
            qrtr_rows,
        ) if qrtr_rows else "- none",
        "",
        "### V569 Process Socket Summary",
        "",
        base.markdown_table(
            ["label", "fd_count", "socket_count", "anon_inode_count", "truncated"],
            socket_rows,
        ) if socket_rows else "- none",
        "",
        "### V569 Runtime Surface Focus",
        "",
        base.markdown_table(
            ["phase", "path", "host_exists", "private_exists", "private_mode", "private_uid", "private_gid"],
            runtime_rows,
        ) if runtime_rows else "- none",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
