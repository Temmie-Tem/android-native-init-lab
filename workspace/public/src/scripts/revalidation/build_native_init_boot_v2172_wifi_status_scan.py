#!/usr/bin/env python3
"""Build the V2172 Wi-Fi status/scan test image.

V2172 is a test-boot candidate on top of the promoted V2169 transport contract.
It adds native-init `wifi status` and bounded credential-free `wifi scan
[delay_ms]` commands without enabling boot autoconnect, association, DHCP,
routes, or ping.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2169_transport_contract as v2169
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2172-wifi-status-scan-test-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2172_WIFI_STATUS_SCAN_SOURCE_BUILD_2026-06-08.md"
)
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__"
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2172_wifi_status_scan.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2172_wifi_status_scan"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2172_wifi_status_scan.cpio"
EXPECTED_HELPER_MARKER = v2169.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2169.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2169.EXTRA_INIT_FLAGS


def base_module():
    return v2169.base_module()


def configure_base() -> None:
    v2169.OUT_DIR = OUT_DIR
    v2169.REPORT_PATH = REPORT_PATH
    v2169.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2169.BOOT_IMAGE = BOOT_IMAGE
    v2169.INIT_BINARY = INIT_BINARY
    v2169.RAMDISK_CPIO = RAMDISK_CPIO
    v2169.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    v2169.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    v2169.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v2169.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2172",
        "--decision": "v2172-wifi-status-scan-source-build-pass",
        "--cycle-label": "v2172",
        "--init-version": "0.9.249",
        "--init-build": "v2172-wifi-status-scan",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_wifi_status_scan"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2172",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2172.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2172.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2172.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2172-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2172.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2172-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2172 Wi-Fi Status/Scan Source Build",
        "",
        "## Summary",
        "",
        "- Candidate tag: `v2172-wifi-status-scan`",
        "- Parent baseline: `v2169-transport-contract`",
        "- Type: source/build-only test boot candidate.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2172 keeps the V2169 transport contract and adds native-init `wifi status` plus bounded credential-free `wifi scan [delay_ms]`.",
        "- Manifest: `workspace/private/builds/native-init/v2172-wifi-status-scan-test-boot/manifest.json`",
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
        "- Preserved from V2169: V726 Wi-Fi lifecycle route, PID1 modem lifecycle holder, fasttransport ramdisk, and device-side `transport.contract=1` status fields.",
        "- Property root intentionally reuses the verified V726 snapshot; no V2172 private-property tree is required on the SD workspace.",
        "- Added: `wifi status` read-only status/UI primitive and `wifi scan [delay_ms]` direct nl80211 scan primitive.",
        "- Not added: boot autoconnect, association, DHCP, route installation, external ping, or credential logging.",
        "",
        "## Safety Scope",
        "",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "- The live validation must remain credential-free, scan-only, and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["candidate_tag"] = "v2172-wifi-status-scan"
    manifest["parent_baseline"] = "v2169-transport-contract"
    manifest["version_axes"] = {
        "candidate_tag": "v2172-wifi-status-scan",
        "parent_baseline": "v2169-transport-contract",
        "helper_version": "helper-v427",
        "run_id": "V2172",
        "note": "V2172 is a test-boot candidate for Wi-Fi status and scan, not a promoted baseline.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v2169.v726.v2168.prev2137.prev2135.prev2133.prev2131.prev2129
        .prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100
        .prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = v2169.ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and v2169.LEGACY_MKBOOTIMG_DIR.is_symlink():
            v2169.LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
