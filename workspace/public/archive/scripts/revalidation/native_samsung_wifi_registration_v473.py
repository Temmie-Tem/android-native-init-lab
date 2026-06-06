#!/usr/bin/env python3
"""V473 Samsung ISehWifi/default registration retry with V471 property root."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_samsung_wifi_registration_v469 as v469


base = v469.base
V471_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v471/dev/__properties__"
_OLD_PROPERTY_ROOT = base.DEFAULT_PROPERTY_ROOT

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v473-samsung-wifi-registration-v471-property")
base.DEFAULT_HELPER_SHA256 = "9d219f2c28102a8c56d3b283b37c14af12603d9c89700240f3a3d980b5f7de7f"
base.DEFAULT_PROPERTY_ROOT = V471_PROPERTY_ROOT
base.DEFAULT_V404 = Path("tmp/wifi/v472-extended-property-runtime-live-fixed-20260521-021526/manifest.json")
base.HELPER_LABEL = "v36"
base.APPROVAL_PHRASE = (
    "approve v473 Samsung ISehWifi/default registration retry with V471 property root only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)
base.READ_ONLY_COMMANDS = tuple(
    (
        name,
        [V471_PROPERTY_ROOT if item in (_OLD_PROPERTY_ROOT, "/mnt/sdext/a90/private-property-v317/dev/__properties__") else item for item in command],
        timeout,
    )
    for name, command, timeout in base.READ_ONLY_COMMANDS
)

_BASE_PARSE_ARGS = v469.parse_args
_BASE_BUILD_PLAN = v469.build_plan
_BASE_DECIDE = v469.decide
_BASE_REFUSAL_MANIFEST = v469.refusal_manifest
_BASE_RENDER_SUMMARY = v469.render_summary


def parse_args() -> base.argparse.Namespace:
    args = _BASE_PARSE_ARGS()
    if args.property_root == _OLD_PROPERTY_ROOT:
        args.property_root = V471_PROPERTY_ROOT
    return args


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["property_root"] = args.property_root
    plan["v472_property_lookup"] = str(base.DEFAULT_V404)
    return plan


def _v473_label(decision: str) -> str:
    return decision.replace("v469-samsung-wifi-registration", "v473-samsung-wifi-registration-v471-property")


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    return (
        _v473_label(decision),
        pass_ok,
        reason,
        next_step.replace("V469", "V473").replace("v35", "v36").replace("V471", "V471"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, android_manifest)
    manifest["decision"] = _v473_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V473 approval after V472 property lookup pass"
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V469 Samsung ISehWifi/default Registration Proof",
        "# V473 Samsung ISehWifi/default Registration Retry With V471 Property Root",
        1,
    )


v469.parse_args = parse_args
v469.build_plan = build_plan
v469.decide = decide
v469.refusal_manifest = refusal_manifest
v469.render_summary = render_summary

base.parse_args = parse_args
base.build_plan = build_plan
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
