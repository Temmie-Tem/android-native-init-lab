#!/usr/bin/env python3
"""V577 bounded V95 init-root broader IWifi.start retry."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_rmt_tftp_identity_v570 as v570


base = v570.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v577-v95-broader-iwifi-retry")
base.DEFAULT_HELPER_SHA256 = "d59596a0e951d05db9b4ed7f2099f1043d463f4e3dd1dc5a8fa40887e210f45d"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v95"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V577"
base.PROOF_SLUG = "v577-v95-broader-iwifi-retry"
base.LIVE_HELPER_STEP_NAME = "v577-helper-run"
base.APPROVAL_PHRASE = (
    "approve v577 v95 service-manager dual-hal iwifi start-only retry only; "
    "no QMI payload, no supplicant, no scan/connect/link-up and no external ping"
)

EXPECTED_CONTRACTS = {
    "rmt_storage": {
        "contract": "rmt_storage-init-root",
        "uid": "0",
        "gid": "0",
        "groups": "",
        "capability_mode": "android-init-root",
    },
    "tftp_server": {
        "contract": "tftp_server-init-root",
        "uid": "0",
        "gid": "0",
        "groups": "",
        "capability_mode": "android-init-root",
    },
}


def _identity_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for child, expected in EXPECTED_CONTRACTS.items():
        prefix = f"wifi_hal_composite_child.{child}"
        expected_prefix = f"{prefix}.expected"
        row = {
            "child": child,
            "contract": keys.get(f"{expected_prefix}.contract", ""),
            "uid": keys.get(f"{expected_prefix}.uid", ""),
            "gid": keys.get(f"{expected_prefix}.gid", ""),
            "groups": keys.get(f"{expected_prefix}.groups", ""),
            "capability_mode": keys.get(f"{expected_prefix}.capability_mode", ""),
            "preexec_status": keys.get(f"{prefix}.preexec_status", ""),
            "selinux_exec": keys.get(f"{prefix}.selinux.exec", ""),
        }
        row["match"] = "1" if (
            all(row[key] == value for key, value in expected.items())
            and row["preexec_status"] == "pass"
        ) else "0"
        rows.append(row)
    return rows


def _identity_contracts_ok(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and all(row.get("match") == "1" for row in rows)


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = v570._orig_run_live(args, store)
    keys = result.get("keys") or {}
    rows = _identity_rows(keys)
    result["rmt_tftp_identity_rows"] = rows
    result["rmt_tftp_identity_contracts_ok"] = _identity_contracts_ok(rows)
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = v570._orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        if decision.startswith("v569-"):
            decision = decision.replace("v569-", "v577-", 1)
        elif decision.startswith("v570-"):
            decision = decision.replace("v570-", "v577-", 1)
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("rmt_tftp_identity_contracts_ok"):
        return (
            "v577-init-root-contract-mismatch",
            False,
            "helper v95 did not report the expected Android init-root contracts for rmt_storage/tftp_server",
            "inspect helper stdout before retrying any broader window",
            live_executed,
        )
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v577-v95-broader-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in V95 broader retry",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v577-v95-broader-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )
    if int(live_result.get("qrtr_readback_qmi_attempted") or 0):
        return (
            "v577-v95-broader-qmi-guard-failed",
            False,
            "unexpected QMI payload attempt during V95 broader retry",
            "stop and inspect helper before any further live action",
            live_executed,
        )

    status_name = live_result.get("iwifi_start_wifi_status_name") or "UNDECODED"
    status_code = live_result.get("iwifi_start_wifi_status_code") or ""
    service_events = int(live_result.get("qrtr_readback_service_events") or 0)
    qipcrtr_window = live_result.get("qipcrtr_sockets_window") or "unknown"
    readiness_markers = dmesg.get("readiness_markers") or []
    if status_name == "SUCCESS":
        return (
            "v577-iwifi-start-success-before-scan",
            True,
            "IWifi.start returned SUCCESS with V95 init-root companion contracts; scan/connect was still blocked",
            "move to separate bounded scan-only proof",
            live_executed,
        )
    if readiness_markers:
        return (
            "v577-v95-readiness-marker-observed",
            True,
            f"IWifi.start={status_name}/{status_code} and readiness markers appeared: {readiness_markers}",
            "inspect delayed firmware/netdev surface before scan-only work",
            live_executed,
        )
    if service_events > 0:
        return (
            "v577-v95-qrtr-progress",
            True,
            f"IWifi.start={status_name}/{status_code}; WLFW service_events={service_events} with V95 contracts",
            "inspect WLFW/BDF/CNSS surface before deciding whether scan-only is safe",
            live_executed,
        )
    if status_name == "ERROR_UNKNOWN" and qipcrtr_window in {"0", "unknown"}:
        return (
            "v577-v95-broader-not-sufficient",
            True,
            f"V95 init-root contracts applied, but IWifi.start still returned ERROR_UNKNOWN/{status_code} and QIPCRTR sockets={qipcrtr_window}",
            "continue QRTR/modem readiness dependency analysis before scan/connect",
            live_executed,
        )
    return (
        "v577-v95-broader-review-required",
        False,
        f"IWifi.start status={status_name}/{status_code} service_events={service_events} qipcrtr_sockets={qipcrtr_window}",
        "inspect V577 transcript before further live action",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = v570._orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        [
            row["child"],
            row["contract"],
            row["uid"],
            row["gid"],
            row["groups"],
            row["capability_mode"],
            row["preexec_status"],
            row["selinux_exec"],
            row["match"],
        ]
        for row in (live.get("rmt_tftp_identity_rows") or [])
    ]
    extra = "\n".join([
        "## V577 V95 Init-root Broader Retry",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- identity_contracts_ok: `{live.get('rmt_tftp_identity_contracts_ok', '')}`",
        f"- iwifi_start_wifi_status: `{live.get('iwifi_start_wifi_status_name', '')}/{live.get('iwifi_start_wifi_status_code', '')}`",
        f"- qrtr_readback_service_events: `{live.get('qrtr_readback_service_events', 0)}`",
        f"- qipcrtr_sockets: `before={live.get('qipcrtr_sockets_before', '')} after_spawn={live.get('qipcrtr_sockets_after_spawn', '')} window={live.get('qipcrtr_sockets_window', '')} cleanup={live.get('qipcrtr_sockets_after_cleanup', '')}`",
        "- forbidden: QMI payload, `supplicant`, `hostapd`, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
        "### V577 Init-root Contracts",
        "",
        base.markdown_table(
            ["child", "contract", "uid", "gid", "groups", "capability_mode", "preexec", "selinux_exec", "match"],
            rows,
        ) if rows else "- none",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
