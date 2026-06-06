#!/usr/bin/env python3
"""V659 service-74 gated vndservicemanager readiness-only proof.

This proof reuses the V657 service-74 gate and service-manager trio, then
checks vndservicemanager readiness without running the V655 fresh cnss-daemon
retry tail. It does not write DSP boot nodes, open esoc0, write qcwlanstate,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_vndservicemanager_cnss_retry_v655 as v655


base = v655.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v659-vndservicemanager-readiness-only")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "67776f512c47eb048147c312d5a0a618ff30b4a3bbab7e60af790ce727940995"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v107"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v659-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v659 vndservicemanager readiness-only proof only; "
    "no CNSS retry, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

V659_MODE = "wifi-companion-service74-gated-vnd-service-manager-readiness-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready"
)

v655.V655_MODE = V659_MODE
v655.EXPECTED_ORDER = EXPECTED_ORDER

_v655_build_checks = v655.build_checks
_v655_run_live = v655.run_live
_v655_render_summary = v655.render_summary
_v655_build_manifest = v655.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V655", "V659")
        .replace("v655", "v659")
        .replace("helper v106", "helper v107")
        .replace("helper-v106", "helper-v107")
        .replace("a90_android_execns_probe v106", "a90_android_execns_probe v107")
        .replace("vndservicemanager-readiness CNSS retry", "vndservicemanager-readiness only")
        .replace("vndservicemanager-readiness plus fresh cnss-daemon retry", "vndservicemanager-readiness only")
        .replace("CNSS retry", "readiness-only")
        .replace("cnss retry", "readiness-only")
    )


def _rename_check(check: base.Check) -> base.Check:
    return base.Check(
        _rewrite_text(check.name),
        check.status,
        check.severity,
        _rewrite_text(check.detail),
        [_rewrite_text(item) for item in check.evidence],
        _rewrite_text(check.next_step),
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [_rename_check(check) for check in _v655_build_checks(args, steps, mount_preflight, v490, v525)]
    if args.command != "plan":
        usage = base.step_payload(steps, "helper-usage")
        sha_text = base.step_payload(steps, "sha-helper")
        base.add_check(
            checks,
            "helper-v107-readiness-only-contract",
            "pass"
            if (
                args.helper_sha256 in sha_text
                and args.helper_marker in usage
                and V659_MODE in usage
            )
            else "blocked",
            "blocker",
            "remote helper SHA and usage must match V659 readiness-only mode; internal printf tokens are covered by local build strings",
            [
                line
                for line in (sha_text + "\n" + usage).splitlines()
                if args.helper_sha256 in line
                or args.helper_marker in line
                or V659_MODE in line
            ][:8],
            "build and deploy helper v107 before V659",
        )
    return checks


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _v655_run_live(args, store, steps, mount_preflight)
    helper_text = base.step_payload(steps, "companion-start-only-with-holder")
    keys = result.get("companion_keys") or {}
    surface = result.get("v655_surface") or {}
    surface["initial_cnss_daemon"] = {
        "index": keys.get("wifi_companion_start.initial_cnss_daemon.index", ""),
        "observable": keys.get("wifi_companion_start.initial_cnss_daemon.observable", ""),
        "cleanup_safe": keys.get("wifi_companion_start.initial_cnss_daemon.cleanup_safe", ""),
    }
    result["v659_surface"] = surface
    result["v659_counts"] = result.get("v655_counts") or {}
    result["v659_helper_stdout_stderr"] = helper_text
    return result


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v659-vndservicemanager-readiness-only-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V641/V490 prerequisites, then run V659 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v659-vndservicemanager-readiness-only-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V659", False
    if args.command == "preflight":
        return (
            "v659-vndservicemanager-readiness-only-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V659 live proof",
            False,
        )
    if not base.approved(args):
        return "v659-vndservicemanager-readiness-only-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V659 approval", False
    if not live:
        return "v659-vndservicemanager-readiness-only-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v659-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v659-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V659 retry", True
    if not live.get("companion_executed") or not live.get("all_postflight_safe"):
        return "v659-cleanup-review", False, f"helper_result={live.get('helper_result')} all_postflight_safe={live.get('all_postflight_safe')}", "inspect companion transcript before retry", True

    surface = live.get("v659_surface") or {}
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    initial_cnss = surface.get("initial_cnss_daemon") or {}
    cnss_retry = surface.get("cnss_retry") or {}
    counts = live.get("v659_counts") or {}
    service_manager_executed = (
        surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("order") == EXPECTED_ORDER
        and surface.get("service_manager_started") == "1"
    )
    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v659-service74-gate-timeout",
            True,
            (
                f"gate_status={service74_gate.get('status')} "
                f"baseline_74={service74_gate.get('baseline_count_74')} "
                f"final_74={service74_gate.get('final_count_74')} "
                f"wait_ms={service74_gate.get('wait_ms')}"
            ),
            "readiness-only tail was correctly withheld; classify lower service74 regression before retry",
            True,
        )
    if not service_manager_executed:
        return "v659-service-manager-not-executed", False, f"surface={surface}", "inspect helper mode and approval propagation", True
    if cnss_retry.get("enabled") != "0" or cnss_retry.get("retry_start_order"):
        return (
            "v659-cnss-retry-guard-failed",
            False,
            f"cnss_retry={cnss_retry}",
            "stop; V659 must not run the fresh cnss-daemon retry tail",
            True,
        )
    if vnd_ready.get("ready") != "1":
        return (
            "v659-vndservicemanager-readiness-blocked",
            True,
            f"vndservicemanager_readiness={vnd_ready} initial_cnss={initial_cnss}",
            "inspect vndservicemanager fd/process capture before any fresh cnss-daemon retry",
            True,
        )
    if initial_cnss.get("cleanup_safe") != "1":
        return (
            "v659-initial-cnss-cleanup-blocked",
            True,
            f"initial_cnss={initial_cnss}",
            "do not retry cnss-daemon until initial process cleanup is proven safe",
            True,
        )
    return (
        "v659-vndservicemanager-readiness-pass",
        True,
        f"vndservicemanager_readiness={vnd_ready} initial_cnss={initial_cnss} counts={counts}",
        "plan fresh cnss-daemon binder attempt after proven vndservicemanager readiness; still block Wi-Fi HAL and scan/connect",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v655_render_summary(manifest)
    text = _rewrite_text(text).replace(
        "# V659 vndservicemanager Readiness + readiness-only Proof",
        "# V659 vndservicemanager Readiness-Only Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v659_surface") or {}
    counts = live.get("v659_counts") or {}
    return "\n".join([
        text,
        "",
        "## V659 Readiness-Only Contract",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- cnss_retry_enabled: `{(surface.get('cnss_retry') or {}).get('enabled', '')}`",
        "",
        "## V659 Initial CNSS Cleanup",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted((surface.get("initial_cnss_daemon") or {}).items())],
        ) if surface.get("initial_cnss_daemon") else "- none",
        "",
        "## V659 Counts",
        "",
        base.markdown_table(["name", "count"], [[key, str(value)] for key, value in sorted(counts.items())]) if counts else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v655_build_manifest(args, store)
    live = manifest.get("live") or {}
    surface = live.get("v659_surface") or live.get("v655_surface") or {}
    manifest["cycle"] = "v659"
    manifest["helper_version"] = "v107"
    manifest["readiness_only_mode"] = V659_MODE
    manifest["v655_retry_tail_executed"] = bool((surface.get("cnss_retry") or {}).get("retry_start_order"))
    manifest["service_manager_start_executed"] = (
        bool(live.get("companion_executed"))
        and surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("service_manager_started") == "1"
    )
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, and initial cnss-daemon start-only inside bounded private namespace",
        "service74-gated vndservicemanager readiness-only proof under V641 clean-DSP state",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "fresh cnss-daemon retry tail",
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
