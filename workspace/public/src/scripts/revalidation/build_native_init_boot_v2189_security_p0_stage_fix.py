#!/usr/bin/env python3
"""Build the V2189 security P0 staged-artifact fix image."""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2188_security_p0_hardening as v2188
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2189-security-p0-stage-fix-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_SOURCE_BUILD_2026-06-10.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2189_security_p0_stage_fix.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2189_security_p0_stage_fix"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2189_security_p0_stage_fix.cpio"
REMOTE_PROPERTY_ROOT = v2188.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2188.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = "a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44"
EXTRA_INIT_FLAGS = v2188.EXTRA_INIT_FLAGS


def base_module():
    return v2188.base_module()


def configure_base() -> None:
    v2188.OUT_DIR = OUT_DIR
    v2188.REPORT_PATH = REPORT_PATH
    v2188.BOOT_IMAGE = BOOT_IMAGE
    v2188.INIT_BINARY = INIT_BINARY
    v2188.RAMDISK_CPIO = RAMDISK_CPIO
    v2188.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2189",
        "--decision": "v2189-security-p0-stage-fix-source-build-pass",
        "--cycle-label": "v2189",
        "--init-version": "0.9.261",
        "--init-build": "v2189-security-p0-stage-fix",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_security_p0_stage_fix"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2189",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2189.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2189.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2189.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2189-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2189.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2189-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2189 Security P0 Stage Fix Source Build",
        "",
        "## Summary",
        "",
        "- Candidate tag: `v2189-security-p0-stage-fix`",
        "- Parent candidate: `v2188-security-p0-hardening`",
        "- Type: source/build-only test boot candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2189 preserves V2188 P0 hardening, fixes the live validation gap where stale staged Wi-Fi executables remained non-root-owned, and adds the 2026-06-10 active security triage hardening set.",
        "- Manifest: `workspace/private/builds/native-init/v2189-security-p0-stage-fix-boot/manifest.json`",
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
        "- Preserved: V2187 screenapp/UI validation baseline and V2188 flash artifact identity hardening.",
        "- Fixed: generated Wi-Fi runtime files are re-owned as root when rewritten by PID1.",
        "- Fixed: `wifi status` and `wifi connect` report standalone supplicant root-exec verification explicitly.",
        "- Fixed: host Wi-Fi profile/connect staging hardens existing `/cache/a90-wifi/wpa-standalone` ownership before connect.",
        "- Fixed: host bridge repair, unsafe busy replay, NCM listener/repair scope, Wi-Fi identifier redaction, wificfg symlink traversal, bounded evidence reads, and Termux lab auth/limits.",
        "- Fixed: helper temp paths use `mkdtemp()`/`mkstemp()`, private cnss-daemon bind sources are verified, and supplicant helper exec drops to UID/GID 1010 before exec.",
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
    manifest["candidate_tag"] = "v2189-security-p0-stage-fix"
    manifest["parent_baseline"] = "v2187-screenapp-ui-validation"
    manifest["parent_candidate"] = "v2188-security-p0-hardening"
    manifest["rollback_baseline"] = "v2187-screenapp-ui-validation"
    manifest["promoted_baseline"] = False
    manifest["version_axes"] = {
        "candidate_tag": "v2189-security-p0-stage-fix",
        "parent_baseline": "v2187-screenapp-ui-validation",
        "parent_candidate": "v2188-security-p0-hardening",
        "rollback_baseline": "v2187-screenapp-ui-validation",
        "helper_version": "helper-v427",
        "run_id": "V2189",
        "note": "V2189 fixes the V2188 live validation staged-artifact ownership gap without changing the Wi-Fi lower route.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131
        .prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102
        .prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2188.v2187.v2182.v2178.v2176.v2174.v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2188.v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2188.v2187.v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
