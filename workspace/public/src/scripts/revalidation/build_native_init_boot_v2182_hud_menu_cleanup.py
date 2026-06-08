#!/usr/bin/env python3
"""Build the V2182 HUD/menu cleanup baseline image."""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2178_wifi_profile_autoconnect as v2178
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2182-hud-menu-cleanup-test-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2182_HUD_MENU_CLEANUP_SOURCE_BUILD_2026-06-09.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2182_hud_menu_cleanup.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2182_hud_menu_cleanup"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2182_hud_menu_cleanup.cpio"
REMOTE_PROPERTY_ROOT = v2178.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2178.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2178.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2178.EXTRA_INIT_FLAGS


def base_module():
    return v2178.base_module()


def configure_base() -> None:
    v2178.OUT_DIR = OUT_DIR
    v2178.REPORT_PATH = REPORT_PATH
    v2178.BOOT_IMAGE = BOOT_IMAGE
    v2178.INIT_BINARY = INIT_BINARY
    v2178.RAMDISK_CPIO = RAMDISK_CPIO
    v2178.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2182",
        "--decision": "v2182-hud-menu-cleanup-source-build-pass",
        "--cycle-label": "v2182",
        "--init-version": "0.9.255",
        "--init-build": "v2182-hud-menu-cleanup",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_hud_menu_cleanup"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2182",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2182.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2182.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2182.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2182-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2182.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2182-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2182 HUD/Menu Cleanup Source Build",
        "",
        "## Summary",
        "",
        "- Baseline tag: `v2182-hud-menu-cleanup`",
        "- Parent baseline: `v2178-wifi-profile-autoconnect`",
        "- Type: source/build baseline candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2182 keeps the V2178 Wi-Fi profile/autoconnect baseline and adds HUD storage/Wi-Fi glance improvements, shared HUD layout geometry, and menu navigation cleanup.",
        "- Manifest: `workspace/private/builds/native-init/v2182-hud-menu-cleanup-test-boot/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Included Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Preserved from V2178: Wi-Fi profile inventory, explicit autoconnect controls, boot-background autoconnect worker, V2176 connect/DHCP/cleanup route, V726 lifecycle route, and transport contract fields.",
        "- Added: HUD storage free/free-percent/read-write-rate line and Wi-Fi state/profile/decision surfacing.",
        "- Added: shared HUD status geometry so menu/log/preview layouts follow the six-row HUD height.",
        "- Added: menu cleanup that removes duplicate STATUS/LIVE STATUS navigation and clarifies USB NET STATUS versus Wi-Fi HUD status.",
        "",
        "## Safety Scope",
        "",
        "- Raw SSID/PSK remain private-only; HUD consumes redacted runtime/autoconnect summaries.",
        "- No scan/connect/DHCP/ping is initiated by this UI baseline change.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["baseline_tag"] = "v2182-hud-menu-cleanup"
    manifest["parent_baseline"] = "v2178-wifi-profile-autoconnect"
    manifest["rollback_baseline"] = "v2178-wifi-profile-autoconnect"
    manifest["version_axes"] = {
        "baseline_tag": "v2182-hud-menu-cleanup",
        "parent_baseline": "v2178-wifi-profile-autoconnect",
        "helper_version": "helper-v427",
        "run_id": "V2182",
        "promotion_run_id": "V2183",
        "note": "V2182 is the promoted boot/init baseline tag after V2183 live promotion evidence.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131
        .prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102
        .prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2178.v2176.v2174.v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
