#!/usr/bin/env python3
"""V603 modem-holder QRTR-first service-manager proof.

This proof reuses V601's global firmware mounts, `subsys_modem` holder,
copy-real linkerconfig, service-manager surface, and WLFW QRTR nameservice
readback. It changes only the bounded companion order so QRTR/modem companion
services start first, service-manager starts after that lower publication
window, and CNSS starts last.

It does not start Wi-Fi HAL, write qcwlanstate, scan, connect, use credentials,
run DHCP, change routing, or ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_modem_holder_service_manager_v601 as v601


base = v601.base

base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v603-modem-holder-qrtr-first-service-manager")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v603-v490-current-run/manifest.json")
base.DEFAULT_HELPER_SHA256 = "a2a089110106a9c2eb6b33eb2c5f0c382fb4fda0e0c7f32e80dbabb9dd281372"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v101"
base.APPROVAL_PHRASE = (
    "approve v603 modem holder qrtr-first service-manager proof only; "
    "no Wi-Fi HAL start, no qcwlanstate, no scan/connect/link-up and no external ping"
)

QRTR_FIRST_MODE = "wifi-companion-qrtr-first-vnd-service-manager-start-only"
QRTR_FIRST_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,"
    "servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon"
)

_v601_build_checks = base.build_checks
_v601_companion_command = base.companion_command
_v601_run_live = base.run_live
_v601_render_summary = base.render_summary
_v601_build_manifest = base.build_manifest


def _set_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        command.extend([option, value])
    else:
        command[index + 1] = value


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v601_build_checks(args, steps, mount_preflight, v490, v525)
    normalized_checks: list[base.Check] = []
    for check in checks:
        if check.name == "helper-v100-ready":
            normalized_checks.append(base.Check(
                "helper-v101-base-ready",
                check.status,
                check.severity,
                check.detail,
                check.evidence,
                "deploy helper v101 before V603",
            ))
        elif check.name == "helper-v100-service-manager-ready":
            normalized_checks.append(base.Check(
                "helper-v101-service-manager-ready",
                check.status,
                check.severity,
                check.detail,
                check.evidence,
                "deploy helper v101 or newer before V603",
            ))
        else:
            normalized_checks.append(check)
    checks = normalized_checks
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    base.add_check(
        checks,
        "helper-v101-qrtr-first-ready",
        "pass"
        if (
            args.helper_sha256 in base.step_payload(steps, "sha-helper")
            and args.helper_marker in usage
            and QRTR_FIRST_MODE in usage
            and "--allow-service-manager-start-only" in usage
            and "--allow-qrtr-ns-readback" in usage
        )
        else "blocked",
        "blocker",
        "helper must expose v101 QRTR-first service-manager companion mode",
        [
            line
            for line in usage.splitlines()
            if QRTR_FIRST_MODE in line
            or "a90_android_execns_probe v101" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:8],
        "deploy helper v101 before V603",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v601_companion_command(args)
    _set_option(command, "--mode", QRTR_FIRST_MODE)
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _v601_run_live(args, store, steps, mount_preflight)
    keys = result.get("companion_keys") or {}
    service_manager = result.get("service_manager") or {}
    service_manager["order"] = keys.get("wifi_companion_start.order", "")
    result["service_manager"] = service_manager
    result["v603_counts"] = result.get("v601_counts") or {}
    return result


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v603-qrtr-first-service-manager-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v101, refresh current-boot V490/runtime prerequisites, then run V603 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v603-qrtr-first-service-manager-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve V603 blockers before live run",
            False,
        )
    if args.command == "preflight":
        return (
            "v603-qrtr-first-service-manager-preflight-ready",
            True,
            "preflight ready; live run uses QRTR-first service-manager order and reboot cleanup",
            "run V603 live proof",
            False,
        )
    if not base.approved(args):
        return (
            "v603-qrtr-first-service-manager-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V603 approval",
            False,
        )
    if not live:
        return (
            "v603-qrtr-first-service-manager-review-required",
            False,
            "missing live result",
            "inspect runner failure",
            True,
        )
    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return (
            "v603-qrtr-first-service-manager-reboot-cleanup-review",
            False,
            f"reboot_cleanup={reboot}",
            "verify device manually before continuing",
            True,
        )
    markers = live.get("markers") or {}
    marker_counts = markers.get("counts") or {}
    if _int_count(marker_counts.get("kernel_warning")) > 0:
        return (
            "v603-qrtr-first-service-manager-kernel-warning",
            False,
            "kernel WARNING/reference mismatch appeared during live window",
            "do not repeat; inspect dmesg and design safer kernel trigger",
            True,
        )
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return (
            "v603-qrtr-first-service-manager-lower-modem-blocked",
            False,
            "subsys_modem holder did not reproduce QRTR RX",
            "restore V596 lower modem readiness before retrying service-manager order",
            True,
        )
    if not live.get("companion_executed") or not live.get("all_postflight_safe"):
        return (
            "v603-qrtr-first-service-manager-cleanup-review",
            False,
            f"helper_result={live.get('helper_result')} all_postflight_safe={live.get('all_postflight_safe')}",
            "inspect companion transcript before retry",
            True,
        )

    service_manager = live.get("service_manager") or {}
    counts = live.get("v603_counts") or {}
    readback = live.get("qrtr_readback") or {}
    if service_manager.get("order") != QRTR_FIRST_ORDER:
        return (
            "v603-qrtr-first-order-not-executed",
            False,
            f"order={service_manager.get('order')}",
            "inspect helper mode and command construction before retry",
            True,
        )
    if service_manager.get("with_service_manager") != "1" or service_manager.get("with_vnd_service_manager") != "1":
        return (
            "v603-service-manager-not-executed",
            False,
            f"service_manager={service_manager}",
            "inspect helper approval propagation before retry",
            True,
        )
    if _int_count(counts.get("linker_symbol_gap")):
        return (
            "v603-qrtr-first-linker-gap",
            True,
            "QRTR-first service-manager reached copy-real mode but linker symbol gap remains",
            "inspect helper stdout/stderr and Android linker namespace delta before retry",
            True,
        )
    service_notifier_180 = _int_count(counts.get("service_notifier_180"))
    binder_failed = _int_count(counts.get("binder_transaction_failed"))
    service_notifier_74 = _int_count(counts.get("service_notifier_74"))
    wlan_pd = _int_count(counts.get("wlan_pd"))
    wlfw = _int_count(counts.get("wlfw_start")) + _int_count(counts.get("wl_fw_qrtr_service_events"))
    bdf = _int_count(counts.get("bdf"))
    wlan_fw_ready = _int_count(counts.get("wlan_fw_ready"))
    wlan0 = _int_count(counts.get("wlan0"))
    readback_services = _int_count(readback.get("service_events"))

    if readback.get("send_attempted") != "1":
        return (
            "v603-wlfw-readback-not-sent",
            False,
            "WLFW QRTR readback send path did not execute",
            "inspect helper approval flags and command contract",
            True,
        )
    if _int_count(readback.get("qmi_attempted")):
        return (
            "v603-wlfw-readback-qmi-guard-failed",
            False,
            f"unexpected qmi_attempted={readback.get('qmi_attempted')}",
            "stop and inspect helper before any further Wi-Fi live action",
            True,
        )
    if service_notifier_180 > 0 and binder_failed == 0 and (
        service_notifier_74 > 0 or wlan_pd > 0 or wlfw > 0 or readback_services > 0 or bdf > 0 or wlan_fw_ready > 0 or wlan0 > 0
    ):
        return (
            "v603-qrtr-first-service-manager-wlan-registration-advance",
            True,
            f"QRTR-first preserved service_notifier_180 and binder clean, and WLAN registration advanced; counts={counts} readback_services={readback_services}",
            "prepare bounded driver-state/HAL gate; keep scan/connect blocked until wlan0/FW-ready is confirmed",
            True,
        )
    if service_notifier_180 > 0 and binder_failed == 0:
        return (
            "v603-qrtr-first-service-manager-intersection-pass",
            True,
            f"QRTR-first preserved service_notifier_180 and cleared binder failures, but WLFW/WLAN-PD did not advance; counts={counts}",
            "classify remaining WLFW/service-registry publication gap before qcwlanstate/HAL retry",
            True,
        )
    if service_notifier_180 == 0 and binder_failed == 0:
        return (
            "v603-qrtr-first-service-notifier-regressed",
            True,
            f"binder clean remained but service_notifier_180 disappeared; counts={counts}",
            "increase service-manager delay or test delayed-CNSS order before qcwlanstate/HAL retry",
            True,
        )
    if service_notifier_180 > 0 and binder_failed > 0:
        return (
            "v603-qrtr-first-binder-gap-persists",
            True,
            f"service_notifier_180 remained but binder failures persisted; counts={counts}",
            "move service-manager earlier or verify binder namespace visibility before retry",
            True,
        )
    return (
        "v603-qrtr-first-no-intersection",
        True,
        f"neither service_notifier_180 nor binder-clean intersection was observed; counts={counts}",
        "inspect dmesg and helper transcript before another live order change",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v601_render_summary(manifest).replace(
        "# V601 Modem Holder Service-Manager Binder Proof",
        "# V603 Modem Holder QRTR-First Service-Manager Proof",
        1,
    )
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    counts = live.get("v603_counts") or {}
    rows = [[key, str(value)] for key, value in sorted(counts.items())]
    return "\n".join([
        text,
        "",
        "## V603 QRTR-First Order",
        "",
        f"- expected_order: `{QRTR_FIRST_ORDER}`",
        f"- observed_order: `{service_manager.get('order', '')}`",
        "",
        "## V603 Counts",
        "",
        base.markdown_table(["name", "count"], rows) if rows else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v601_build_manifest(args, store)
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    manifest["qrtr_first_order_executed"] = bool(
        live.get("companion_executed")
        and service_manager.get("order") == QRTR_FIRST_ORDER
    )
    if args.command == "run" and base.approved(args):
        manifest["explicitly_approved"] = [
            "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
            "QRTR companion services, cnss_diag, cnss-daemon start-only inside bounded private namespace",
            "QRTR-first companion ordering",
            "WLFW QRTR nameservice readback without QMI payload",
            "reboot cleanup boundary after live proof",
        ]
    return manifest


base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
