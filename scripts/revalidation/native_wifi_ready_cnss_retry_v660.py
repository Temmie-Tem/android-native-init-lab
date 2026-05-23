#!/usr/bin/env python3
"""V660 vndservicemanager-ready fresh cnss-daemon retry proof.

This proof reruns the service-74 gated vndservicemanager readiness sequence
with helper v107, then enables the single fresh cnss-daemon retry tail. It does
not write DSP boot nodes, open esoc0, write qcwlanstate, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_vndservicemanager_cnss_retry_v655 as v655


base = v655.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v660-ready-cnss-retry")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "67776f512c47eb048147c312d5a0a618ff30b4a3bbab7e60af790ce727940995"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v107"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v660-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v660 vndservicemanager-ready cnss-daemon retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

V660_MODE = "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only"
EXPECTED_ORDER = v655.EXPECTED_ORDER

_v655_build_checks = v655.build_checks
_v655_decide = v655.decide
_v655_render_summary = v655.render_summary
_v655_build_manifest = v655.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V655", "V660")
        .replace("v655", "v660")
        .replace("helper v106", "helper v107")
        .replace("helper-v106", "helper-v107")
        .replace("a90_android_execns_probe v106", "a90_android_execns_probe v107")
        .replace("vndservicemanager-readiness plus fresh cnss-daemon retry", "vndservicemanager-ready fresh cnss-daemon retry")
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
            "helper-v107-cnss-retry-contract",
            "pass"
            if (
                args.helper_sha256 in sha_text
                and args.helper_marker in usage
                and V660_MODE in usage
                and "--allow-service-manager-start-only" in usage
                and "--allow-qrtr-ns-readback" in usage
            )
            else "blocked",
            "blocker",
            "remote helper SHA and usage must match V660 service74-gated cnss retry mode",
            [
                line
                for line in (sha_text + "\n" + usage).splitlines()
                if args.helper_sha256 in line
                or args.helper_marker in line
                or V660_MODE in line
                or "--allow-service-manager-start-only" in line
                or "--allow-qrtr-ns-readback" in line
            ][:8],
            "deploy helper v107 before V660",
        )
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, needs_review = _v655_decide(args, checks, live)
    return (
        _rewrite_text(decision),
        pass_ok,
        _rewrite_text(reason),
        _rewrite_text(next_step),
        needs_review,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v655_render_summary(manifest)).replace(
        "# V660 vndservicemanager Readiness + CNSS Retry Proof",
        "# V660 vndservicemanager-ready CNSS Retry Proof",
        1,
    )
    return "\n".join([
        text,
        "",
        "## V660 Contract",
        "",
        f"- helper_version: `v107`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- mode: `{V660_MODE}`",
        "- Wi-Fi HAL/scan/connect/external ping remain blocked.",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v655_build_manifest(args, store)
    live = manifest.get("live") or {}
    surface = live.get("v655_surface") or {}
    manifest["cycle"] = "v660"
    manifest["helper_version"] = "v107"
    manifest["ready_cnss_retry_mode"] = V660_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["service_manager_start_executed"] = (
        bool(live.get("companion_executed"))
        and surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("service_manager_started") == "1"
    )
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "service74-gated vndservicemanager readiness and fresh cnss-daemon binder attempt under V641 clean-DSP state",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
