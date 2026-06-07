#!/usr/bin/env python3
"""Build the V2169 native-init transport-contract test image.

V2169 keeps the V726 Wi-Fi lifecycle baseline behavior and adds the device-side
status contract consumed by the host bridge/transport selector.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v726_wifi_lifecycle as v726
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2169-transport-contract-test-boot")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2169_TRANSPORT_CONTRACT_SOURCE_BUILD_2026-06-08.md"
)
LIVE_VALIDATION_REPORT = (
    "docs/reports/"
    "NATIVE_INIT_V2169_TRANSPORT_CONTRACT_LIVE_VALIDATION_2026-06-08.md"
)
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2169/dev/__properties__"
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2169_transport_contract.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2169_transport_contract"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2169_transport_contract.cpio"
EXPECTED_HELPER_MARKER = v726.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v726.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = (
    *v726.EXTRA_INIT_FLAGS,
    "-DA90_TRANSPORT_STATUS_CONTRACT=1",
)
MKBOOTIMG_DIR = REPO_ROOT / "workspace" / "public" / "src" / "third_party" / "mkbootimg"
LEGACY_MKBOOTIMG_DIR = REPO_ROOT / "mkbootimg"


def ensure_legacy_mkbootimg_link() -> bool:
    if LEGACY_MKBOOTIMG_DIR.exists():
        return False
    LEGACY_MKBOOTIMG_DIR.symlink_to(MKBOOTIMG_DIR, target_is_directory=True)
    return True


def base_module():
    return v726.base_module()


def configure_base() -> None:
    v726.OUT_DIR = OUT_DIR
    v726.REPORT_PATH = REPORT_PATH
    v726.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v726.BOOT_IMAGE = BOOT_IMAGE
    v726.INIT_BINARY = INIT_BINARY
    v726.RAMDISK_CPIO = RAMDISK_CPIO
    v726.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    v726.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    v726.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    v726.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2169",
        "--decision": "v2169-transport-contract-source-build-pass",
        "--cycle-label": "v2169",
        "--init-version": "0.9.247",
        "--init-build": "v2169-transport-contract",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_transport_contract"),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2169",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2169.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2169.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2169.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2169-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2169.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2169-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2169 Transport Contract Source Build",
        "",
        "## Summary",
        "",
        "- Baseline tag: `v2169-transport-contract`",
        "- Type: source/build transport-contract baseline.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: the V2169 boot/init candidate keeps the V726 Wi-Fi lifecycle route and enables the native-init status transport contract consumed by the host bridge selector.",
        "- Manifest: `workspace/private/builds/native-init/v2169-transport-contract-test-boot/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Live validation: `{LIVE_VALIDATION_REPORT}`",
        "- Boot SHA verification: source/build output; flash/readback/selftest verification is recorded in the live validation report.",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "- Version axes: `v2169-transport-contract` is the promoted boot/init baseline tag; it is built from the V726 Wi-Fi lifecycle route and helper marker `helper-v427`.",
        "",
        "## Included Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Preserved from V726: V2168 QCACLD firmware_class feeder path, PID1-owned `/dev/subsys_modem` lifecycle holder, Wi-Fi HUD/runtime sampler, and V725 fasttransport ramdisk contract.",
        "- Added: native-init `status` emits `transport.contract=1` plus serial/NCM/tcpctl/preferred/reason fields for the host selector.",
        "- Behavior scope: no Wi-Fi bring-up path change beyond status observability.",
        "",
        "## Safety Scope",
        "",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE path is included.",
        "- The live validation remains credential-redacted and rollbackable to `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`.",
        "",
    ])


def normalize_manifest_axes() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["baseline_tag"] = "v2169-transport-contract"
    manifest["version_axes"] = {
        "baseline_tag": "v2169-transport-contract",
        "boot_init_parent": "v726-wifi-lifecycle",
        "helper_version": "helper-v427",
        "run_id": "V2169",
        "note": "v2169-transport-contract is the promoted boot/init baseline tag for the device-side transport status contract.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> int:
    configure_base()
    base = base_module()
    helper_builder = (
        v726.v2168.prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120
        .prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095
        .prev2082.prev2080.prev2058.prev2038
    )
    helper_builder.patch_helper_builder(base)
    base.render_report = render_report
    created_legacy_link = ensure_legacy_mkbootimg_link()
    try:
        rc = base.main()
        if rc == 0:
            normalize_manifest_axes()
            REPORT_PATH.chmod(0o644)
        return rc
    finally:
        if created_legacy_link and LEGACY_MKBOOTIMG_DIR.is_symlink():
            LEGACY_MKBOOTIMG_DIR.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
