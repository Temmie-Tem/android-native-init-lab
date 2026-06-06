#!/usr/bin/env python3
"""V1037 PM runtime-domain guard live proof with helper v176."""

from __future__ import annotations

from pathlib import Path

import native_wifi_pm_runtime_domain_guard_live_v1032 as v1032


base = v1032.base
ORIGINAL_DECIDE = v1032.decide
ORIGINAL_BUILD_MANIFEST = v1032.build_manifest
ORIGINAL_RENDER_SUMMARY = v1032.render_summary

HELPER_SHA256_V176 = "dff34476d956574be59628f1177179cb8ef87a04dda0c68e97cc5afcf5310f2d"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1037-pm-runtime-domain-guard-live-v176")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1037-pm-runtime-domain-guard-live-v176.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1034-execns-helper-v176-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = HELPER_SHA256_V176
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v176"


def _map_v1037(value: str) -> str:
    return value.replace("v1032", "v1037").replace("V1032", "V1037").replace("v175", "v176")


def decide(args, local, steps, analysis):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, local, steps, analysis)
    return _map_v1037(decision), pass_ok, _map_v1037(reason), _map_v1037(next_step)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("# V1032 PM Runtime-Domain Guard Live", "# V1037 PM Runtime-Domain Guard Live v176")
        .replace("V1032", "V1037")
        .replace("helper `v175`", "helper `v176`")
        .replace("helper v175", "helper v176")
    )


def build_manifest(args, store):
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    manifest["decision"] = _map_v1037(str(manifest.get("decision", "")))
    manifest["reason"] = _map_v1037(str(manifest.get("reason", "")))
    manifest["next_step"] = _map_v1037(str(manifest.get("next_step", "")))
    manifest["helper_marker"] = args.helper_marker
    manifest["helper_sha256"] = args.helper_sha256
    manifest["rerun_after_v1036_pm_domain_pass"] = True
    return manifest


v1032.decide = decide
v1032.render_summary = render_summary
v1032.build_manifest = build_manifest
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
