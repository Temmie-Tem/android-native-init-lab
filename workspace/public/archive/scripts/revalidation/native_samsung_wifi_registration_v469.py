#!/usr/bin/env python3
"""V469 Samsung ISehWifi/default registration proof.

This runner starts only the private service-manager/HAL/CNSS trio with the
Samsung Wi-Fi HAL target, then asks `/system/bin/lshal wait` for the Android
boot-complete Samsung `ISehWifi/default` fqinstances. It does not call Wi-Fi
HAL methods, read credentials, scan, connect, request DHCP, change routes, or
send packets.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_iwifi_registration_v467 as v467


base = v467.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v469-samsung-wifi-registration")
base.DEFAULT_HELPER_SHA256 = "867a38a1cf55baeb30d7d15150d02e2fbcff3e491b64c3fb11bc8ba26b9430a1"
base.DEFAULT_V404 = Path("tmp/wifi/v425-settled-handoff-live-20260520-134752/v423-android-hwservice-bootcomplete-run/manifest.json")
base.HELPER_LABEL = "v35"
base.APPROVAL_PHRASE = (
    "approve v469 Samsung ISehWifi/default registration proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

SAMSUNG_TARGETS = (
    "vendor.samsung.hardware.wifi@2.0::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.1::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.2::ISehWifi/default",
)


def parse_args() -> base.argparse.Namespace:
    args = v467.parse_args()
    args.target_profile = "vendor-wifi-hal-ext"
    if args.max_runtime_sec < 12:
        args.max_runtime_sec = 12
    return args


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = False) -> list[str]:
    del include_data_wifi
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-surface-composite-lshal-wait-samsung",
        "--target-profile",
        "vendor-wifi-hal-ext",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        args.property_root,
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if base.approved(args):
        argv.extend([
            "--allow-service-manager-start-only",
            "--allow-wifi-hal-start-only",
            "--allow-cnss-start-only",
            "--allow-hal-service-query",
        ])
    return argv


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = v467.build_plan(args)
    plan["helper_mode"] = "wifi-surface-composite-lshal-wait-samsung"
    plan["helper_version"] = base.HELPER_LABEL
    plan["target_profile_default"] = "vendor-wifi-hal-ext"
    plan["android_reference_manifest"] = str(base.DEFAULT_V404)
    plan["registration_query"] = {
        "tool": "/system/bin/lshal",
        "command": "lshal wait <Samsung ISehWifi/default>",
        "targets": list(SAMSUNG_TARGETS),
        "scope": "private helper namespace after private servicemanager/hwservicemanager/Samsung HAL/CNSS start",
        "per_target_timeout_ms": args.max_runtime_sec * 1000,
    }
    plan["surface_attempt"] = {
        "starts": ["servicemanager", "hwservicemanager", "vendor.samsung.hardware.wifi@2.0-service", "cnss-daemon -n -l"],
        "calls": ["lshal wait for Samsung ISehWifi/default targets"],
        "observes": ["wlan* netdev", "phy* wiphy", "/proc/net/wireless", "Wi-Fi rfkill"],
        "blocks": ["Wi-Fi HAL methods", "credentials", "scan/connect", "DHCP", "route changes", "external ping"],
    }
    return plan


def _android_reference_ready(manifest: dict[str, Any]) -> bool:
    if manifest.get("decision") != "v423-android-hwservice-targets-present" or not manifest.get("pass"):
        return False
    matched = manifest.get("matched_targets") or manifest.get("targets_present") or []
    text = "\n".join(str(item) for item in matched)
    if not text:
        text = str(manifest)
    return all(target in text for target in SAMSUNG_TARGETS)


def build_checks(args: base.argparse.Namespace, store: base.EvidenceStore, steps: list[base.Step],
                 android_manifest: dict[str, Any]) -> list[base.Check]:
    checks = v467.build_checks(args, store, steps, android_manifest)
    if args.command == "plan":
        return checks
    for check in checks:
        if check.name == "v466-service-null-ready":
            check.name = "android-samsung-targets-ready"
            ready = _android_reference_ready(android_manifest)
            check.status = "pass" if ready else "warn"
            check.detail = f"decision={android_manifest.get('decision')} pass={android_manifest.get('pass')}"
            check.next_step = "refresh Android boot-complete hwservice inventory if Samsung targets are missing"
        elif check.name.startswith("helper-"):
            check.next_step = "deploy helper v35 before V469 live run"
        elif check.name == "approval-gate":
            check.next_step = "exact phrase and flags required before bounded Samsung registration proof"
    return checks


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = v467.decide(args, checks, live_result, post)
    decision = decision.replace("v467-iwifi-registration", "v469-samsung-wifi-registration")
    if live_result and live_result.get("micro_query_result") == "service-query-pass":
        return (
            "v469-samsung-wifi-registration-present",
            True,
            f"lshal saw {live_result.get('matched_fqinstance')} in the private namespace",
            "advance to bounded Samsung HAL method/readiness gate; still block scan/connect",
            daemon_started,
        )
    if live_result and live_result.get("micro_query_result") == "service-query-timeout":
        return (
            "v469-samsung-wifi-registration-timeout",
            True,
            "Samsung ISehWifi/default did not register within bounded wait while cleanup stayed clean",
            "triage native HAL registration prerequisites before Wi-Fi methods or scan/connect",
            daemon_started,
        )
    next_step = (
        next_step
        .replace("V467", "V469")
        .replace("v33", "v35")
        .replace("IWifi", "Samsung ISehWifi")
    )
    return decision, pass_ok, reason, next_step, daemon_started


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": "v469-samsung-wifi-registration-approval-required",
        "pass": True,
        "reason": "exact approval phrase required; no live command executed",
        "next_step": "rerun with exact approval only after helper v35 deploy and preflight",
        "host": base.collect_host_metadata(),
        "android_reference": {
            "path": android_manifest.get("path"),
            "decision": android_manifest.get("decision"),
            "pass": android_manifest.get("pass"),
        },
        "plan": build_plan(args),
        "steps": [],
        "checks": [
            asdict(
                base.Check(
                    "approval-gate",
                    "needs-operator",
                    "approval",
                    base.APPROVAL_PHRASE,
                    [base.APPROVAL_PHRASE],
                    "approve before bounded Samsung registration proof",
                )
            )
        ],
        "live_result": None,
        "postflight": None,
        "required_approval_phrase": base.APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == base.APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_hal_method_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    android_manifest = base.load_json(args.v404_manifest)
    if args.command == "run" and not base.approved(args):
        return refusal_manifest(args, android_manifest)
    steps: list[base.Step] = []
    live_result: dict[str, Any] | None = None
    post: dict[str, Any] | None = None
    if args.command != "plan":
        steps = base.run_preflight(args, store)
    checks = build_checks(args, store, steps, android_manifest)
    if args.command == "run" and base.approved(args) and not base.blockers(checks):
        live_result = v467.run_live(args, store)
        post = base.postflight(args, store)
    decision, pass_ok, reason, next_step, daemon_started = decide(args, checks, live_result, post)
    manifest = {
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": base.collect_host_metadata(),
        "android_reference": {
            "path": android_manifest.get("path"),
            "decision": android_manifest.get("decision"),
            "pass": android_manifest.get("pass"),
        },
        "samsung_targets": list(SAMSUNG_TARGETS),
        "plan": build_plan(args),
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
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
        "iwifi_start_executed": False,
        "wifi_hal_method_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "Wi-Fi HAL method calls",
            "wificond, supplicant, or hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation, Android partition write",
            "unbounded daemon persistence or boot autostart",
        ],
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return v467.render_summary(manifest).replace(
        "# V467 IWifi/default Registration Proof",
        "# V469 Samsung ISehWifi/default Registration Proof",
        1,
    ).replace("## Lshal Wait Keys", "## Samsung Lshal Wait Keys")


base.parse_args = parse_args
base.build_helper_argv = build_helper_argv
base.build_plan = build_plan
base.build_checks = build_checks
base.decide = decide
base.refusal_manifest = refusal_manifest
base.build_manifest = build_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
