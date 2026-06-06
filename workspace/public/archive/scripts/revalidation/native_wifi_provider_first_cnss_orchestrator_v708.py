#!/usr/bin/env python3
"""V708 current-boot orchestrator for helper v120 provider-first CNSS proof."""

from __future__ import annotations

from typing import Any

import native_wifi_provider_first_cnss_orchestrator_v700 as v700


v700.DEFAULT_OUT_DIR = v700.Path("tmp/wifi/v708-provider-first-cnss-v120-orchestrated")
v700.V700_SCRIPT = "scripts/revalidation/native_wifi_provider_first_cnss_v708.py"
v700.V700_APPROVAL = (
    "approve v708 provider-first CNSS v120 stall capture proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)
v700.HELPER_SHA256 = "acc43d21f948c88350099e1a652a26c7a5f4f0352e06396c6d30dd6908d1ba28"
v700.HELPER_MARKER = "a90_android_execns_probe v120"

_build_manifest = v700.build_manifest
_render_summary = v700.render_summary


def _replace(value: object) -> object:
    if isinstance(value, str):
        return value.replace("v700", "v708").replace("V700", "V708").replace("v119", "v120")
    if isinstance(value, dict):
        return {key: _replace(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace(item) for item in value]
    return value


def build_manifest(args: v700.argparse.Namespace,
                   prep: dict[str, Any] | None,
                   arm: dict[str, Any] | None) -> dict[str, Any]:
    manifest = _build_manifest(args, prep, arm)
    manifest = _replace(manifest)
    assert isinstance(manifest, dict)
    manifest["cycle"] = "v708"
    manifest["helper_marker"] = v700.HELPER_MARKER
    manifest["helper_sha256"] = v700.HELPER_SHA256
    arm_summary = manifest.get("arm_v708") or manifest.get("arm_v700") or {}
    if isinstance(arm_summary, dict):
        manifest["cnss_retry_stall_captured"] = bool(
            ((arm or {}).get("live") or {}).get("v708_cnss_retry_stall_captured")
        )
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _render_summary(manifest).replace("v700", "v708").replace("V700", "V708").replace("v119", "v120")


v700.build_manifest = build_manifest
v700.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v700.main())
