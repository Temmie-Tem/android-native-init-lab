#!/usr/bin/env python3
"""V483 Samsung ISehWifi/default registration with private property-service shim.

This runner keeps the V479 bounded start/query scope, but expects helper v42.
The helper creates a private `/dev/socket/property_service` only inside its
temporary namespace and only returns success for `hwservicemanager.ready=true`.
It still blocks scan/connect/link-up, credentials, DHCP, route changes, and
external ping.
"""

from __future__ import annotations

from typing import Any

import native_samsung_wifi_registration_v479 as v479


base = v479.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v483-samsung-registration-property-service-shim")
base.DEFAULT_HELPER_SHA256 = "1204c44843c90e4b7799c6126abfd6036a6e7fbb2560ba21a9c75b3ff7878ff1"
base.HELPER_LABEL = "v42"
base.APPROVAL_PHRASE = (
    "approve v483 private property-service shim Samsung registration only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

_BASE_BUILD_PLAN = base.build_plan
_BASE_DECIDE = base.decide
_BASE_REFUSAL_MANIFEST = base.refusal_manifest
_BASE_RENDER_SUMMARY = base.render_summary


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["property_service_shim"] = {
        "socket": "/dev/socket/property_service",
        "scope": "helper private root namespace only",
        "protocol": "PROP_MSG_SETPROP2",
        "allowlist": {"hwservicemanager.ready": "true"},
        "success_code": "PROP_SUCCESS",
        "blocked": [
            "global /dev/socket/property_service creation",
            "general setprop/property mutation service",
            "Wi-Fi scan/connect/link-up",
            "credential reads",
            "DHCP, routing, or external ping",
        ],
    }
    plan["aosp_references"] = [
        "https://android.googlesource.com/platform/bionic/+/master/libc/bionic/system_property_set.cpp",
        "https://android.googlesource.com/platform/system/core/+/8908b264f4e6ba7a0e64bfc2a715b6b2b0f944e7/init/property_service.cpp",
        "https://android.googlesource.com/platform/prebuilts/ndk/+/4448347db136fb3d172c0349c32295c6691df3be/headers/sys/_system_properties.h",
    ]
    return plan


def _v483_label(decision: str) -> str:
    return (
        decision
        .replace("v479-samsung-wifi-registration-selinux-context", "v483-samsung-registration-property-shim")
        .replace("v473-samsung-wifi-registration-v471-property", "v483-samsung-registration-property-shim")
        .replace("v469-samsung-wifi-registration", "v483-samsung-registration-property-shim")
    )


def _shim_ready_allowed(keys: dict[str, str]) -> bool:
    for index in range(1, 17):
        prefix = f"property_service_shim.request.{index}"
        if (
            keys.get(f"{prefix}.name") == "hwservicemanager.ready"
            and keys.get(f"{prefix}.value") == "true"
            and keys.get(f"{prefix}.allowed") == "1"
            and keys.get(f"{prefix}.result") == "0x00000000"
        ):
            return True
    return False


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    if args.command == "run" and live_result and post and post.get("clean"):
        keys = live_result.get("keys") or {}
        shim_started = keys.get("property_service_shim.started") == "1"
        shim_postflight_safe = keys.get("property_service_shim.postflight_safe") == "1"
        shim_ready_allowed = _shim_ready_allowed(keys)
        helper_result = live_result.get("helper_result")
        micro_result = live_result.get("micro_query_result")
        if live_result.get("matched_fqinstance"):
            return (
                "v483-samsung-registration-property-shim-present",
                True,
                f"Samsung target registered: {live_result.get('matched_fqinstance')}",
                "advance to bounded no-credential Wi-Fi HAL readiness method gate",
                daemon_started,
            )
        if shim_started and shim_postflight_safe and shim_ready_allowed and helper_result == "service-query-runtime-gap":
            return (
                "v483-samsung-registration-property-shim-negative",
                True,
                "private property_service accepted hwservicemanager.ready=true, but Samsung ISehWifi/default still did not register",
                "next isolate SELinux domain handoff or HAL crash root cause before scan/connect",
                daemon_started,
            )
        if shim_started and shim_postflight_safe and not shim_ready_allowed:
            return (
                "v483-samsung-registration-property-shim-unused",
                True,
                f"property shim started but no allowed hwservicemanager.ready request was observed; helper_result={helper_result} micro={micro_result}",
                "inspect manager stderr and launch ordering before widening scope",
                daemon_started,
            )
    return (
        _v483_label(decision),
        pass_ok,
        reason.replace("V479", "V483").replace("v38", "v42"),
        next_step.replace("V479", "V483").replace("v38", "v42"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, android_manifest)
    manifest["decision"] = _v483_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V483 approval after helper v42 deploy"
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V479 Samsung ISehWifi/default Registration With SELinux Context Handoff",
        "# V483 Samsung ISehWifi/default Registration With Private Property-Service Shim",
        1,
    )


base.build_plan = build_plan
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary
v479.v473.v469.build_plan = build_plan
v479.v473.v469.decide = decide
v479.v473.v469.refusal_manifest = refusal_manifest
v479.v473.v469.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
