#!/usr/bin/env python3
"""V708 provider-first CNSS retry proof with helper v120 stall capture."""

from __future__ import annotations

from typing import Any

import native_wifi_provider_first_cnss_v700 as v700


base = v700.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v708-provider-first-cnss-v120")
base.DEFAULT_HELPER_SHA256 = "acc43d21f948c88350099e1a652a26c7a5f4f0352e06396c6d30dd6908d1ba28"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v120"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v708-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v708 provider-first CNSS v120 stall capture proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

v700.V700_USAGE_TOKENS = (
    v700.V700_MODE,
    "a90_android_execns_probe v120",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)

_v700_build_checks = v700.build_checks
_v700_decide = v700.decide
_v700_render_summary = v700.render_summary
_v700_build_manifest = v700.build_manifest


def _stall_surface(keys: dict[str, str]) -> dict[str, str]:
    names = (
        "cnss_daemon",
        "cnss_daemon_retry",
        "wifi_hal_composite_cnss_daemon_retry",
    )
    result: dict[str, str] = {}
    for name in names:
        child_prefix = f"wifi_companion_start.child.{name}."
        capture_prefix = f"capture.{name}."
        for key, value in keys.items():
            if key.startswith(child_prefix) and "stall_snapshot" in key:
                result[key] = value
            elif key.startswith(capture_prefix + "stall_snapshot."):
                result[key] = value
            elif key.startswith(capture_prefix + "stall_tasks."):
                result[key] = value
            elif "cnss_daemon_retry.stall_" in key:
                result[key] = value
    return result


def _stall_captured(surface: dict[str, str]) -> bool:
    return (
        surface.get("wifi_companion_start.child.cnss_daemon_retry.stall_snapshot_captured") == "1"
        or surface.get("capture.cnss_daemon_retry.stall_snapshot.begin") == "1"
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v700_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
    )
    base.add_check(
        checks,
        "helper-v120-stall-capture-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must match the helper v120 build that was statically verified for CNSS stall snapshot capture",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_marker in line
            or args.helper_sha256 in line
            or "stall_snapshot" in line
            or "stall_tasks" in line
        ][:20],
        "deploy helper v120 before V708 live proof",
    )
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v700_decide(args, checks, live)
    decision = decision.replace("v700", "v708")
    reason = reason.replace("v119", "v120").replace("V700", "V708")
    next_step = next_step.replace("v119", "v120").replace("V700", "V708")
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    keys = v700._keys(live)
    stall = _stall_surface(keys)
    live["v708_cnss_stall_surface"] = stall
    live["v708_cnss_retry_stall_captured"] = _stall_captured(stall)
    if not live["v708_cnss_retry_stall_captured"]:
        return (
            "v708-provider-first-cnss-stall-capture-missing",
            False,
            f"provider-first path ran but v120 stall snapshot was missing; prior={decision}; stall_keys={sorted(stall)[:12]}",
            "inspect helper v120 capture placement before another live retry",
            live_executed,
        )
    if decision == "v708-provider-first-cnss-gap-persists":
        return (
            "v708-provider-first-cnss-stall-captured-gap-persists",
            True,
            reason + "; cnss_daemon_retry stall snapshot captured",
            "classify captured wchan/syscall/socket state before Wi-Fi HAL or scan/connect",
            live_executed,
        )
    return decision, pass_ok, reason + "; cnss_daemon_retry stall snapshot captured", next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v700_render_summary(manifest).replace("V700", "V708").replace("v119", "v120")
    live = manifest.get("live") or {}
    stall = live.get("v708_cnss_stall_surface") or {}
    rows = [[key, value] for key, value in sorted(stall.items())]
    return "\n".join([
        text,
        "",
        "## V708 CNSS Stall Snapshot",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- retry_stall_captured: `{live.get('v708_cnss_retry_stall_captured', '')}`",
        "",
        base.markdown_table(["key", "value"], rows) if rows else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v700_build_manifest(args, store)
    live = manifest.get("live") or {}
    if isinstance(live, dict):
        keys = v700._keys(live)
        stall = _stall_surface(keys)
        live["v708_cnss_stall_surface"] = stall
        live["v708_cnss_retry_stall_captured"] = _stall_captured(stall)
    manifest["cycle"] = "v708"
    manifest["helper_version"] = "v120"
    manifest["decision"] = str(manifest.get("decision", "")).replace("v700", "v708")
    manifest["reason"] = str(manifest.get("reason", "")).replace("v119", "v120").replace("V700", "V708")
    manifest["next_step"] = str(manifest.get("next_step", "")).replace("v119", "v120").replace("V700", "V708")
    manifest["cnss_retry_stall_captured"] = bool(live.get("v708_cnss_retry_stall_captured")) if isinstance(live, dict) else False
    if (
        manifest["decision"] == "v708-provider-first-cnss-gap-persists"
        and manifest["cnss_retry_stall_captured"]
    ):
        manifest["decision"] = "v708-provider-first-cnss-stall-captured-gap-persists"
        manifest["reason"] = str(manifest.get("reason", "")) + "; cnss_daemon_retry stall snapshot captured"
        manifest["next_step"] = "classify captured wchan/syscall/socket state before Wi-Fi HAL or scan/connect"
    manifest["explicitly_approved"] = [
        str(item).replace("v119", "v120")
        for item in manifest.get("explicitly_approved", [])
    ]
    return manifest


base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
