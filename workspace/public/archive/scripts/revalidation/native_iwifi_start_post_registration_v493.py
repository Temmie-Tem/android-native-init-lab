#!/usr/bin/env python3
"""V493 post-registration IWifi.start surface proof.

This runner reuses the V466 raw hwbinder `IWifi.start()` surface proof, but
requires a V492 manifest proving that Samsung `ISehWifi/default` registered in
the post-policy-load runtime. It keeps the scope bounded to no credentials,
no scan/connect/link-up, no DHCP/routing, and no external ping.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import native_iwifi_start_surface_v466 as v466


base = v466.base
_BASE_PARSE_ARGS = base.parse_args
_BASE_BUILD_PLAN = base.build_plan
_BASE_BUILD_CHECKS = base.build_checks
_BASE_DECIDE = base.decide
_BASE_REFUSAL_MANIFEST = base.refusal_manifest
_BASE_RENDER_SUMMARY = base.render_summary

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v493-iwifi-start-post-registration")
base.DEFAULT_HELPER_SHA256 = "5bc491c7ed0c4da498c6ee16568004dd886df577edd5f8cbebd50fb0740db10c"
base.HELPER_LABEL = "v48"
base.APPROVAL_PHRASE = (
    "approve v493 post-registration IWifi.start surface proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


def _extract_v492_manifest_arg() -> Path | None:
    value: str | None = None
    stripped = [sys.argv[0]]
    index = 1
    while index < len(sys.argv):
        item = sys.argv[index]
        if item == "--v492-manifest":
            if index + 1 >= len(sys.argv):
                raise SystemExit("--v492-manifest requires a path")
            value = sys.argv[index + 1]
            index += 2
            continue
        if item.startswith("--v492-manifest="):
            value = item.split("=", 1)[1]
            index += 1
            continue
        stripped.append(item)
        index += 1
    sys.argv[:] = stripped
    return Path(value) if value else None


def parse_args() -> base.argparse.Namespace:
    v492_manifest = _extract_v492_manifest_arg()
    args = _BASE_PARSE_ARGS()
    args.v492_manifest = v492_manifest
    return args


def _load_v492_manifest(args: base.argparse.Namespace) -> dict[str, Any]:
    path = getattr(args, "v492_manifest", None)
    result: dict[str, Any] = {
        "path": str(path) if path else "",
        "present": False,
        "valid": False,
        "decision": "",
        "matched_fqinstance": "",
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "reason": "missing-v492-manifest",
    }
    if path is None:
        return result
    if not path.exists():
        result["reason"] = "v492-manifest-not-found"
        return result
    result["present"] = True
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve parse issue
        result["reason"] = f"v492-manifest-read-failed-{exc}"
        return result
    live = manifest.get("live_result") or {}
    result["decision"] = str(manifest.get("decision", ""))
    result["matched_fqinstance"] = str(live.get("matched_fqinstance", ""))
    result["daemon_start_executed"] = bool(manifest.get("daemon_start_executed"))
    result["wifi_hal_start_executed"] = bool(manifest.get("wifi_hal_start_executed"))
    result["wifi_bringup_executed"] = bool(manifest.get("wifi_bringup_executed"))
    result["scan_connect_executed"] = bool(manifest.get("scan_connect_executed"))
    result["external_ping_executed"] = bool(manifest.get("external_ping_executed"))
    result["valid"] = (
        manifest.get("decision") == "v492-samsung-registration-post-load-present"
        and manifest.get("pass") is True
        and bool(live.get("matched_fqinstance"))
        and manifest.get("wifi_bringup_executed") is False
        and manifest.get("scan_connect_executed") is False
        and manifest.get("external_ping_executed") is False
    )
    result["reason"] = "v492-registration-ready" if result["valid"] else "v492-registration-present-required"
    return result


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["v492_samsung_registration_manifest"] = str(getattr(args, "v492_manifest", "") or "")
    plan["precondition"] = {
        "decision": "v492-samsung-registration-post-load-present",
        "matched_fqinstance_required": True,
    }
    plan["scope"] = {
        "starts": ["private servicemanager", "private hwservicemanager", "legacy Wi-Fi HAL", "CNSS"],
        "method": "raw hwbinder IWifi.start() once if IWifi/default handle is non-null",
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "blocks": ["credentials", "scan/connect/link-up", "DHCP", "routes", "external ping"],
    }
    return plan


def build_checks(args: base.argparse.Namespace,
                 store: base.EvidenceStore,
                 steps: list[base.Step],
                 v465: dict[str, Any]) -> list[base.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, v465)
    if args.command == "plan":
        return checks
    helper_sha = base.step_text(store, steps, "sha-helper")
    helper_usage = base.step_text(store, steps, "helper-usage")
    helper_marker_ready = any(
        marker in helper_usage
        for marker in ("a90_android_execns_probe v48", "a90_android_execns_probe v52", "a90_android_execns_probe v53")
    )
    helper_ready = (
        args.helper_sha256 in helper_sha
        and helper_marker_ready
        and "wifi-iwifi-start-surface" in helper_usage
        and "--allow-iwifi-start-only" in helper_usage
    )
    for check in checks:
        if check.name == "helper-v32":
            check.name = "helper-v48-iwifi-start"
            check.status = "pass" if helper_ready else "blocked"
            check.detail = f"sha_match={args.helper_sha256 in helper_sha} marker={helper_marker_ready} mode={'wifi-iwifi-start-surface' in helper_usage} allow={'--allow-iwifi-start-only' in helper_usage}"
            check.evidence = [line for line in helper_sha.splitlines() if args.helper in line][:2]
            check.next_step = "deploy helper v48 before V493 live run"
    v492 = _load_v492_manifest(args)
    base.add_check(
        checks,
        "v492-samsung-registration-present",
        "pass" if v492["valid"] else "blocked",
        "blocker",
        f"path={v492['path']} present={v492['present']} decision={v492['decision']} matched={v492['matched_fqinstance']} reason={v492['reason']}",
        [v492["matched_fqinstance"]],
        "run V490/V491/V492 first; pass the V492 registration-present manifest to --v492-manifest",
    )
    return checks


def _v493_label(decision: str) -> str:
    return decision.replace("v466-raw-hwbinder-iwifi-start", "v493-iwifi-start-post-registration")


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    return (
        _v493_label(decision),
        pass_ok,
        reason.replace("V466", "V493").replace("v32", "v48"),
        next_step.replace("V466", "V493").replace("v32", "v48"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, v465: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, v465)
    manifest["decision"] = _v493_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V493 approval after V492 registration-present proof"
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    manifest["v492_samsung_registration"] = _load_v492_manifest(args)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    summary = _BASE_RENDER_SUMMARY(manifest).replace(
        "# V466 Raw hwbinder IWifi.start Surface",
        "# V493 Post-Registration IWifi.start Surface",
        1,
    )
    v492 = manifest.get("v492_samsung_registration")
    if v492:
        summary += "\n\n## V492 Precondition\n\n"
        summary += base.markdown_table(["item", "value"], [
            ["manifest", v492.get("path", "")],
            ["valid", str(v492.get("valid", ""))],
            ["decision", v492.get("decision", "")],
            ["matched_fqinstance", v492.get("matched_fqinstance", "")],
        ])
        summary += "\n"
    return summary


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    v465 = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, v465)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, v465)
    if args.command == "run" and base.approved(args) and not base.blockers(checks):
        live_result = v466.run_live(args, store)
        post = base.postflight(args, store)
    decision, pass_ok, reason, next_step, daemon_started = decide(args, checks, live_result, post)
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "v465": {"path": v465.get("path"), "decision": v465.get("decision"), "pass": v465.get("pass")},
        "v492_samsung_registration": _load_v492_manifest(args),
        "plan": build_plan(args),
        "steps": [base.asdict(step) for step in steps],
        "checks": [base.asdict(check) for check in checks],
        "live_result": live_result,
        "postflight": post,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan" and (args.command != "run" or base.approved(args)),
        "device_mutations": daemon_started,
        "daemon_start_executed": daemon_started,
        "wifi_hal_start_executed": daemon_started,
        "cnss_start_executed": daemon_started,
        "iwifi_start_executed": bool((live_result or {}).get("iwifi_transaction_executed")),
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "wificond, supplicant, or hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }


base.parse_args = parse_args
base.build_plan = build_plan
base.build_checks = build_checks
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
