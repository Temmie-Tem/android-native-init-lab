#!/usr/bin/env python3
"""V1036 PM SELinux domain proof rerun with deployed helper v176."""

from __future__ import annotations

from pathlib import Path

import native_wifi_pm_selinux_domain_proof_v1033 as v1033


base = v1033.base
ORIGINAL_DECIDE = v1033.decide
ORIGINAL_BUILD_MANIFEST = v1033.build_manifest
ORIGINAL_RENDER_SUMMARY = v1033.render_summary

HELPER_SHA256_V176 = "dff34476d956574be59628f1177179cb8ef87a04dda0c68e97cc5afcf5310f2d"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1036-pm-selinux-domain-proof-v176")
base.DEFAULT_HELPER_SHA256 = HELPER_SHA256_V176
base.APPROVAL_PHRASE = (
    "approve v1036 PM SELinux domain proof v176 only; "
    "no daemon start and no Wi-Fi bring-up"
)


def _map_v1036(value: str) -> str:
    return value.replace("v1033", "v1036").replace("V1033", "V1036")


def decide(args, checks, cases):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, cases)
    if decision == "v1033-pm-selinux-domain-handoff-present":
        next_step = (
            "rerun V1032 PM runtime-domain guard with helper v176 while current-boot policy load is fresh; "
            "do not start Wi-Fi HAL or scan/connect yet"
        )
    elif decision == "v1033-pm-selinux-domain-kernel-stuck":
        next_step = "repair PM domain transition before another PM actor live retry"
    return _map_v1036(decision), pass_ok, reason, _map_v1036(next_step)


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("# V1033 PM SELinux Domain Proof", "# V1036 PM SELinux Domain Proof v176")
        .replace("V1033", "V1036")
        .replace("helper v175", "helper v176")
    )


def build_manifest(args, store):
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    manifest["decision"] = _map_v1036(str(manifest.get("decision", "")))
    manifest["next_step"] = _map_v1036(str(manifest.get("next_step", "")))
    manifest["plan"]["helper_version"] = "a90_android_execns_probe v176"
    manifest["helper_sha256"] = args.helper_sha256
    manifest["helper_marker"] = "a90_android_execns_probe v176"
    manifest["rerun_after_v1035_deploy"] = True
    return manifest


v1033.decide = decide
v1033.render_summary = render_summary
v1033.build_manifest = build_manifest
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
