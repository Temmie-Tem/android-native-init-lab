#!/usr/bin/env python3
"""V562 bounded lshal-then-raw IWifi.start proof in the dual-HAL window."""

from __future__ import annotations

from typing import Any

import native_wifi_companion_dual_hal_wificond_iwifi_start_v561 as v561


base = v561.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v562-companion-dual-hal-wificond-lshal-then-iwifi-start")
base.DEFAULT_HELPER_SHA256 = "44fbabd9a67ea27625711bfff3ce564ca551e77acc42ad7c68f2a06836ca089c"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v87"
base.HELPER_MODE = "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.PROOF_VERSION = "V562"
base.PROOF_SLUG = "v562-companion-dual-hal-wificond-lshal-then-iwifi-start"
base.LIVE_HELPER_STEP_NAME = "v562-helper-run"
base.APPROVAL_PHRASE = (
    "approve v562 companion dual HAL lshal-then-IWifi.start proof only; "
    "no supplicant, no scan/connect/link-up and no external ping"
)

_orig_helper_command = base.helper_command
_orig_classify = base.classify
_orig_render_summary = base.render_summary


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", base.HELPER_MODE,
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if base.approved(args):
        command.extend([
            "--allow-cnss-start-only",
            "--allow-wifi-companion-start-only",
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-hal-service-query",
            "--allow-iwifi-start-only",
        ])
    command.extend([
        "--property-root", "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__",
    ])
    if len(command) > 30:
        raise RuntimeError(f"V562 helper command has {len(command)} args; cmdv1 safely carries at most 30 command args")
    return command


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision.replace("v561-", "v562-", 1) if decision.startswith("v561-") else decision, pass_ok, reason, next_step, live_executed
    helper_result = live_result.get("helper_result")
    if helper_result == "iwifi-start-registration-query-failed":
        return (
            "v562-lshal-precheck-failed",
            True,
            "same-window lshal wait did not confirm IWifi/default, so raw IWifi.start was skipped",
            "inspect lshal wait evidence before retry",
            live_executed,
        )
    if helper_result == "iwifi-service-null":
        return (
            "v562-lshal-pass-raw-get-service-null",
            True,
            "same-window lshal wait passed but raw hwbinder get still returned service-null",
            "repair raw hwbinder IServiceManager.get parcel/object contract before IWifi.start",
            live_executed,
        )
    return decision.replace("v561-", "v562-", 1) if decision.startswith("v561-") else decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    extra = "\n".join([
        "## V562 Lshal Then IWifi.start Proof",
        "",
        f"- helper: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{base.HELPER_MODE}`",
        f"- helper_result: `{live.get('helper_result', '')}`",
        f"- service_query_result: `{live.get('service_query_result', '')}`",
        f"- iwifi_start_result: `{live.get('iwifi_start_result', '')}`",
        "- order: `lshal wait IWifi/default` then raw hwbinder get/start",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


base.helper_command = helper_command
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
