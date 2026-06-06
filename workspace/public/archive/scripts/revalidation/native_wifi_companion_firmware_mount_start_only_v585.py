#!/usr/bin/env python3
"""V585 bounded companion start-only with private firmware/modem mounts."""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_start_only_v534 as v534


base = v534.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v585-companion-firmware-mount-start-only")
base.DEFAULT_HELPER_SHA256 = "82ef904d6fdadbd0954b0fdc016d64f733f802cbca954b143970f86a044bf812"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v97"
base.PROOF_VERSION = "V585"
base.PROOF_SLUG = "v585-companion-firmware-mount-start-only"
base.LIVE_HELPER_STEP_NAME = "v585-helper-run"
base.APPROVAL_PHRASE = (
    "approve v585 companion firmware mount start-only proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_BASE_RUN_LIVE = base.run_live
_BASE_CLASSIFY = base.classify
_BASE_RENDER_SUMMARY = base.render_summary


def _helper_line_value(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _BASE_RUN_LIVE(args, store)
    live_text = base.step_payload([result["live"]], base.LIVE_HELPER_STEP_NAME)
    result["firmware_mnt_mount_source"] = _helper_line_value(live_text, "firmware_mnt_mount_source")
    result["firmware_modem_mount_source"] = _helper_line_value(live_text, "firmware_modem_mount_source")
    result["private_firmware_mounts_ready"] = (
        result["firmware_mnt_mount_source"] not in {"", "<not-mounted>"}
        and result["firmware_modem_mount_source"] not in {"", "<not-mounted>"}
    )
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _BASE_CLASSIFY(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        if decision.startswith("v534-"):
            decision = decision.replace("v534-", "v585-", 1)
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("private_firmware_mounts_ready"):
        return (
            "v585-private-firmware-mounts-missing",
            False,
            f"helper v97 did not materialize both private firmware mounts: firmware_mnt={live_result.get('firmware_mnt_mount_source')} firmware_modem={live_result.get('firmware_modem_mount_source')}",
            "inspect helper setup_error and V584 partition mapping before retry",
            live_executed,
        )
    if decision.startswith("v534-"):
        decision = decision.replace("v534-", "v585-", 1)
    if decision == "v585-companion-start-only-no-fw-marker":
        return (
            "v585-private-firmware-mounts-no-readiness-marker",
            pass_ok,
            "helper v97 mounted apnhlos/modem inside the private namespace, companions ran/cleaned, but no readiness marker appeared",
            "inspect companion stdout/stderr and QRTR delta before qcwlanstate or HAL retry",
            live_executed,
        )
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        ["helper", base.DEFAULT_HELPER_MARKER],
        ["private_firmware_mounts_ready", live.get("private_firmware_mounts_ready", "")],
        ["firmware_mnt_mount_source", live.get("firmware_mnt_mount_source", "")],
        ["firmware_modem_mount_source", live.get("firmware_modem_mount_source", "")],
    ]
    extra = "\n".join([
        "## V585 Private Firmware Mounts",
        "",
        base.markdown_table(["key", "value"], rows),
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
