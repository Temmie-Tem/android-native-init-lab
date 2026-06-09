#!/usr/bin/env python3
"""Build the V2185 network ping test image."""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2182_hud_menu_cleanup as v2182
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2185-network-ping-test-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2185_NETWORK_PING_TEST_SOURCE_BUILD_2026-06-10.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2185_network_ping_test.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2185_network_ping_test"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2185_network_ping_test.cpio"
REMOTE_PROPERTY_ROOT = v2182.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2182.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2182.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2182.EXTRA_INIT_FLAGS


def base_module():
    return v2182.base_module()


def configure_base() -> None:
    v2182.OUT_DIR = OUT_DIR
    v2182.REPORT_PATH = REPORT_PATH
    v2182.BOOT_IMAGE = BOOT_IMAGE
    v2182.INIT_BINARY = INIT_BINARY
    v2182.RAMDISK_CPIO = RAMDISK_CPIO
    v2182.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2185",
        "--decision": "v2185-network-ping-test-source-build-pass",
        "--cycle-label": "v2185",
        "--init-version": "0.9.257",
        "--init-build": "v2185-network-ping-test",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_network_ping_test"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2185",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2185.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2185.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2185.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2185-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2185.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2185-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2185 Network Ping Test Source Build",
        "",
        "## Summary",
        "",
        "- Candidate tag: `v2185-network-ping-test`",
        "- Parent baseline: `v2182-hud-menu-cleanup`",
        "- Type: source/build-only test boot candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2185 keeps the V2182 HUD/menu baseline and adds network menu Wi-Fi ping test screen and bounded ping primitive.",
        "- Manifest: `workspace/private/builds/native-init/v2185-network-ping-test-boot/manifest.json`",
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
        "- Added: `NETWORK > WIFI STATUS` read-only wlan0/link/IP/autoconnect screen.",
        "- Added: `NETWORK > WIFI PROFILES` redacted profile/autoconnect inventory screen.",
        "- Added: `NETWORK > WIFI SCAN` one-shot bounded nl80211 scan screen.",
        "- Added: `NETWORK > PING TEST` explicit bounded gateway plus `1.1.1.1` ping screen.",
        "- Added: `wifi ping [gateway|internet|all]` CLI primitive for dev/test validation.",
        "- Preserved: V2182 HUD storage/Wi-Fi glance, V2178 profile/autoconnect commands, and V2169 transport contract.",
        "",
        "## Safety Scope",
        "",
        "- Wi-Fi status and profile screens are read-only.",
        "- Wi-Fi scan is bounded and credential-free; it does not associate, run DHCP, install routes/DNS, or ping.",
        "- Wi-Fi ping is explicit user/test action only; it does not connect, run DHCP, change routes, or read credentials.",
        "- Gateway target is redacted in command output; public reports must redact private LAN details.",
        "- Scan result SSID/frequency/RSSI/security is rendered on screen only; raw BSSID/SSID results are not written to serial logs or public artifacts.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_tag"] = "v2185-network-ping-test"
    manifest["parent_baseline"] = "v2182-hud-menu-cleanup"
    manifest["rollback_baseline"] = "v2185-network-ping-test"
    manifest["promoted_baseline"] = True
    manifest["version_axes"] = {
        "candidate_tag": "v2185-network-ping-test",
        "parent_baseline": "v2182-hud-menu-cleanup",
        "rollback_baseline": "v2185-network-ping-test",
        "helper_version": "helper-v427",
        "run_id": "V2185",
        "note": "V2185 is promoted as the current network-ping baseline after live validation.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2182.v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131
        .prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102
        .prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2182.v2178.v2176.v2174.v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2182.v2178.v2176.v2174.v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
