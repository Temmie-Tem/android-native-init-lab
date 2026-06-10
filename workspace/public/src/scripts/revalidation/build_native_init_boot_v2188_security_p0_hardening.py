#!/usr/bin/env python3
"""Build the V2188 security P0 hardening image."""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2187_screenapp_ui_validation as v2187
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2188-security-p0-hardening-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2188_SECURITY_P0_HARDENING_SOURCE_BUILD_2026-06-10.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2188_security_p0_hardening.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2188_security_p0_hardening"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2188_security_p0_hardening.cpio"
REMOTE_PROPERTY_ROOT = v2187.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2187.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2187.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2187.EXTRA_INIT_FLAGS


def base_module():
    return v2187.base_module()


def configure_base() -> None:
    v2187.OUT_DIR = OUT_DIR
    v2187.REPORT_PATH = REPORT_PATH
    v2187.BOOT_IMAGE = BOOT_IMAGE
    v2187.INIT_BINARY = INIT_BINARY
    v2187.RAMDISK_CPIO = RAMDISK_CPIO
    v2187.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2188",
        "--decision": "v2188-security-p0-hardening-source-build-pass",
        "--cycle-label": "v2188",
        "--init-version": "0.9.260",
        "--init-build": "v2188-security-p0-hardening",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_security_p0_hardening"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2188",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2188.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2188.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2188.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2188-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2188.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2188-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2188 Security P0 Hardening Source Build",
        "",
        "## Summary",
        "",
        "- Candidate tag: `v2188-security-p0-hardening`",
        "- Parent baseline: `v2187-screenapp-ui-validation`",
        "- Type: source/build-only test boot candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2188 preserves the V2187 screenapp/UI baseline and adds P0 hardening for Wi-Fi root-exec paths and flash artifact identity.",
        "- Manifest: `workspace/private/builds/native-init/v2188-security-p0-hardening-boot/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        "- Boot SHA verification: source/build output only; live flash/readback/selftest must be recorded separately before promotion.",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Included Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Preserved: V2187 `screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping]` direct display validation command.",
        "- Added: `/cache/a90-wifi` remains root-owned; only `/cache/a90-wifi/sockets` is Wi-Fi UID/GID writable.",
        "- Added: root-executed Wi-Fi artifacts are checked for non-symlink regular-file/root-owned/not group-or-world-writable state before exec.",
        "- Added: flash handoff tooling requires caller-pinned boot image SHA256 and selftest verification also checks expected version.",
        "",
        "## Safety Scope",
        "",
        "- This source build does not initiate Wi-Fi connect, DHCP, route/DNS changes, or ping.",
        "- Runtime validation should flash this image with `native_init_flash.py --expect-sha256` and then run selftest/status plus bounded Wi-Fi smoke.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_tag"] = "v2188-security-p0-hardening"
    manifest["parent_baseline"] = "v2187-screenapp-ui-validation"
    manifest["rollback_baseline"] = "v2187-screenapp-ui-validation"
    manifest["promoted_baseline"] = False
    manifest["version_axes"] = {
        "candidate_tag": "v2188-security-p0-hardening",
        "parent_baseline": "v2187-screenapp-ui-validation",
        "rollback_baseline": "v2187-screenapp-ui-validation",
        "helper_version": "helper-v427",
        "run_id": "V2188",
        "note": "V2188 is a security P0 hardening test-boot candidate on top of the promoted V2187 baseline.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2187.v2182.v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131
        .prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102
        .prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2187.v2182.v2178.v2176.v2174.v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
