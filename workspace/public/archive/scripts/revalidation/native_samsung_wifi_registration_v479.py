#!/usr/bin/env python3
"""V479 Samsung ISehWifi/default registration retry with Android SELinux context handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_samsung_wifi_registration_v473 as v473


base = v473.base
V478_PROOF = Path("tmp/wifi/v478-native-selinux-domain-proof-run-20260521-031935/manifest.json")

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v479-samsung-wifi-registration-selinux-context")
base.DEFAULT_HELPER_SHA256 = "0a0c01c6978fb602e0716b4cd0960272a4257f608844d80b547c519cb6e93224"
base.HELPER_LABEL = "v41"
base.APPROVAL_PHRASE = (
    "approve v479 Samsung ISehWifi/default registration with SELinux context handoff only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

_BASE_BUILD_HELPER_ARGV = base.build_helper_argv
_BASE_BUILD_PLAN = base.build_plan
_BASE_DECIDE = base.decide
_BASE_REFUSAL_MANIFEST = base.refusal_manifest
_BASE_RENDER_SUMMARY = base.render_summary


def build_helper_argv(args: base.argparse.Namespace, *, include_data_wifi: bool = False) -> list[str]:
    argv = _BASE_BUILD_HELPER_ARGV(args, include_data_wifi=include_data_wifi)
    return argv


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["android_selinux_context_mode"] = "auto"
    plan["v478_selinux_domain_proof"] = str(V478_PROOF)
    plan["context_handoff"] = {
        "servicemanager": "u:r:servicemanager:s0",
        "hwservicemanager": "u:r:hwservicemanager:s0",
        "wifi_hal": "u:r:hal_wifi_default:s0",
        "cnss_daemon": "no default context handoff in v479",
    }
    return plan


def _v479_label(decision: str) -> str:
    return decision.replace(
        "v473-samsung-wifi-registration-v471-property",
        "v479-samsung-wifi-registration-selinux-context",
    )


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    return (
        _v479_label(decision),
        pass_ok,
        reason,
        next_step.replace("V473", "V479").replace("v36", "v38"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, android_manifest)
    manifest["decision"] = _v479_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V479 approval after helper v38 deploy"
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V473 Samsung ISehWifi/default Registration Retry With V471 Property Root",
        "# V479 Samsung ISehWifi/default Registration With SELinux Context Handoff",
        1,
    )


base.build_helper_argv = build_helper_argv
base.build_plan = build_plan
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary
v473.v469.build_helper_argv = build_helper_argv
v473.v469.build_plan = build_plan
v473.v469.decide = decide
v473.v469.refusal_manifest = refusal_manifest
v473.v469.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
