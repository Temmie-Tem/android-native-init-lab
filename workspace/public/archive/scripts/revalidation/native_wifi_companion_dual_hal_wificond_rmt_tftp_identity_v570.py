#!/usr/bin/env python3
"""V570 bounded rmt_storage/tftp_server Android identity retry."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_error_unknown_dependency_v569 as v569


base = v569.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v570-companion-dual-hal-wificond-rmt-tftp-identity")
base.DEFAULT_HELPER_SHA256 = "8030c00267a35581406f6faf487090e081133f5aca1967b6d2edeae737db3948"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v94"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V570"
base.PROOF_SLUG = "v570-companion-dual-hal-wificond-rmt-tftp-identity"
base.LIVE_HELPER_STEP_NAME = "v570-helper-run"
base.APPROVAL_PHRASE = (
    "approve v570 rmt/tftp Android identity retry only; "
    "no QMI payload, no supplicant, no scan/connect/link-up and no external ping"
)

_orig_run_live = base.run_live
_orig_classify = base.classify
_orig_render_summary = base.render_summary

EXPECTED_CONTRACTS = {
    "rmt_storage": {
        "contract": "rmt_storage-android-runtime",
        "uid": "9999",
        "gid": "1000",
        "groups": "1000,3010",
        "cap_count": "2",
        "ambient": "1",
    },
    "tftp_server": {
        "contract": "tftp_server-android-runtime",
        "uid": "2903",
        "gid": "2903",
        "groups": "1000,2903,2904,3010",
        "cap_count": "2",
        "ambient": "1",
    },
}


def _identity_rows(keys: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for child, expected in EXPECTED_CONTRACTS.items():
        prefix = f"wifi_hal_composite_child.{child}.expected"
        row = {
            "child": child,
            "contract": keys.get(f"{prefix}.contract", ""),
            "uid": keys.get(f"{prefix}.uid", ""),
            "gid": keys.get(f"{prefix}.gid", ""),
            "groups": keys.get(f"{prefix}.groups", ""),
            "cap_count": keys.get(f"{prefix}.cap_count", ""),
            "ambient": keys.get(f"{prefix}.ambient", ""),
        }
        row["match"] = "1" if all(row[key] == value for key, value in expected.items()) else "0"
        rows.append(row)
    return rows


def _identity_contracts_ok(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and all(row.get("match") == "1" for row in rows)


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    keys = result.get("keys") or {}
    rows = _identity_rows(keys)
    result["rmt_tftp_identity_rows"] = rows
    result["rmt_tftp_identity_contracts_ok"] = _identity_contracts_ok(rows)
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v569-", "v570-", 1) if decision.startswith("v569-") else decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("rmt_tftp_identity_contracts_ok"):
        return (
            "v570-rmt-tftp-identity-contract-mismatch",
            False,
            "helper v94 did not report the expected Android runtime identities for rmt_storage/tftp_server",
            "inspect helper stdout before retrying any daemon window",
            live_executed,
        )
    if live_result.get("scan_connect_linkup") or live_result.get("external_ping"):
        return (
            "v570-rmt-tftp-identity-guard-failed",
            False,
            "unexpected scan/connect/link-up or external ping flag in identity retry",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if not live_result.get("all_postflight_safe"):
        return (
            "v570-rmt-tftp-identity-cleanup-review",
            False,
            "helper-owned children were not proven cleaned",
            "inspect evidence and consider recovery reboot before further live work",
            live_executed,
        )
    if int(live_result.get("qrtr_readback_qmi_attempted") or 0):
        return (
            "v570-rmt-tftp-identity-qmi-guard-failed",
            False,
            "unexpected QMI payload attempt during identity retry",
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
            "v570-iwifi-start-success-before-scan",
            True,
            "IWifi.start returned SUCCESS after Android runtime identity repair; scan/connect was still blocked",
            "move to separate bounded scan-only proof",
            live_executed,
        )
    if readiness_markers:
        return (
            "v570-rmt-tftp-identity-readiness-marker-observed",
            True,
            f"IWifi.start={status_name}/{status_code} and readiness markers appeared: {readiness_markers}",
            "inspect delayed firmware/netdev surface before scan-only work",
            live_executed,
        )
    if service_events > 0:
        return (
            "v570-rmt-tftp-identity-qrtr-progress",
            True,
            f"IWifi.start={status_name}/{status_code}; WLFW service_events={service_events} after identity repair",
            "inspect WLFW/BDF/CNSS surface before deciding whether start retry or scan-only is safe",
            live_executed,
        )
    if status_name == "ERROR_UNKNOWN" and qipcrtr_window in {"0", "unknown"}:
        return (
            "v570-rmt-tftp-identity-not-sufficient",
            True,
            f"Android runtime identities applied, but IWifi.start still returned ERROR_UNKNOWN/{status_code} and QIPCRTR sockets={qipcrtr_window}",
            "compare Android-vs-native QRTR/modem readiness timing and service-notifier/qmiproxy dependencies",
            live_executed,
        )
    return (
        "v570-rmt-tftp-identity-review-required",
        False,
        f"IWifi.start status={status_name}/{status_code} service_events={service_events} qipcrtr_sockets={qipcrtr_window}",
        "inspect V570 transcript before further live action",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        [
            row["child"],
            row["contract"],
            row["uid"],
            row["gid"],
            row["groups"],
            row["cap_count"],
            row["ambient"],
            row["match"],
        ]
        for row in (live.get("rmt_tftp_identity_rows") or [])
    ]
    extra = "\n".join([
        "## V570 rmt/tftp Android Identity Retry",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- identity_contracts_ok: `{live.get('rmt_tftp_identity_contracts_ok', '')}`",
        f"- iwifi_start_wifi_status: `{live.get('iwifi_start_wifi_status_name', '')}/{live.get('iwifi_start_wifi_status_code', '')}`",
        f"- qrtr_readback_service_events: `{live.get('qrtr_readback_service_events', 0)}`",
        f"- qipcrtr_sockets: `before={live.get('qipcrtr_sockets_before', '')} after_spawn={live.get('qipcrtr_sockets_after_spawn', '')} window={live.get('qipcrtr_sockets_window', '')} cleanup={live.get('qipcrtr_sockets_after_cleanup', '')}`",
        "- forbidden: QMI payload, `supplicant`, `hostapd`, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
        "### V570 Android Runtime Identity Contracts",
        "",
        base.markdown_table(
            ["child", "contract", "uid", "gid", "groups", "cap_count", "ambient", "match"],
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
