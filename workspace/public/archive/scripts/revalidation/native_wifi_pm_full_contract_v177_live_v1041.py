#!/usr/bin/env python3
"""V1041 PM full-contract live proof with helper v177."""

from __future__ import annotations

from pathlib import Path

import native_wifi_pm_runtime_domain_guard_live_v1032 as v1032


base = v1032.base
ORIGINAL_DECIDE = v1032.decide
ORIGINAL_BUILD_MANIFEST = v1032.build_manifest
ORIGINAL_RENDER_SUMMARY = v1032.render_summary

HELPER_SHA256_V177 = "d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1041-pm-full-contract-v177-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1041-pm-full-contract-v177-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1039-execns-helper-v177-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = HELPER_SHA256_V177
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v177"


def _map_v1041(value: str) -> str:
    return (
        value.replace("v1032", "v1041")
        .replace("V1032", "V1041")
        .replace("v175", "v177")
        .replace("v176", "v177")
    )


def decide(args, local, steps, analysis):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return _map_v1041(decision), pass_ok, _map_v1041(reason), _map_v1041(next_step)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("# V1032 PM Runtime-Domain Guard Live", "# V1041 PM Full-Contract Live v177")
        .replace("V1032", "V1041")
        .replace("helper `v175`", "helper `v177`")
        .replace("helper v175", "helper v177")
        .replace("v175", "v177")
    )


def build_manifest(args, store):
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    manifest["decision"] = _map_v1041(str(manifest.get("decision", "")))
    manifest["reason"] = _map_v1041(str(manifest.get("reason", "")))
    manifest["next_step"] = _map_v1041(str(manifest.get("next_step", "")))
    manifest["helper_marker"] = args.helper_marker
    manifest["helper_sha256"] = args.helper_sha256
    manifest["rerun_after_v1040_v177_deploy"] = True
    manifest["pm_proxy_context_parity_expected"] = True
    return manifest


v1032.decide = decide
v1032.render_summary = render_summary
v1032.build_manifest = build_manifest
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
