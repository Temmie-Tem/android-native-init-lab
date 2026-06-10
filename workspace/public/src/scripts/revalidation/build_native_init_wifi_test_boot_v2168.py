#!/usr/bin/env python3
"""Build V2168 QCACLD firmware_class feeder test boot on v725-fasttransport."""

from __future__ import annotations

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT, include_archive=True)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

import build_native_init_wifi_test_boot_v2137 as prev2137


OUT_DIR = workspace_private_build_path("native-init", "v2168-qcacld-fwclass-fasttransport-test-boot")
BASE_BOOT = workspace_private_input_path("boot_images", "boot_linux_v725_fasttransport.img")
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2168/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v427"
EXPECTED_HELPER_SHA256 = "f99c65676762e4a17c14efa9ff14770db77741d8ff9078f1690581298aebfb16"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2168_QCACLD_FWCLASS_FASTTRANSPORT_SOURCE_BUILD_2026-06-06.md"
)
FASTTRANSPORT_INIT_FLAGS = (
    '-DNETSERVICE_USB_HELPER="/bin/a90_usbnet"',
    '-DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl"',
    '-DNETSERVICE_TOYBOX="/bin/toybox"',
    '-DA90_BUSYBOX_HELPER="/bin/busybox"',
)
EXTRA_INIT_FLAGS = (*prev2137.EXTRA_INIT_FLAGS, *FASTTRANSPORT_INIT_FLAGS)
USERLAND_BIN = workspace_private_input_path("external_tools", "userland", "bin")


def base_module():
    return prev2137.base_module()


def configure_base() -> None:
    prev2137.OUT_DIR = OUT_DIR
    prev2137.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2137.REPORT_PATH = REPORT_PATH
    prev2137.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2137.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2137.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    prev2137.prev2135.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    prev2137.prev2135.prev2133.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS = prev2137.HELPER_FLAGS
    prev2137.configure_base()
    helper_builder_module = prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
    helper_builder_module.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder_module.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256

    base = base_module()
    base.REPORT_PATH = REPORT_PATH
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2168",
        "--decision": "v2168-qcacld-fwclass-fasttransport-source-build-pass",
        "--cycle-label": "v2168",
        "--init-version": "0.9.245",
        "--init-build": "v2168-qcacld-fwclass-fasttransport",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2168_qcacld_fwclass_fasttransport"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v427_qcacld_fwclass_fasttransport"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2168_qcacld_fwclass_fasttransport.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2168_qcacld_fwclass_fasttransport.img"),
        "--wifi-test-klog-prefix": "A90v2168",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2168.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2168.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2168.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2168-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2168.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2168-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    setter = prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg
    for key, value in replacements.items():
        setter(args, key, value)
    args.extend(["--base-boot", str(BASE_BOOT)])
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256

    original_ramdisk_helpers = base.base.ramdisk_helpers

    def ramdisk_helpers_with_fasttransport(args):
        helpers = dict(original_ramdisk_helpers(args))
        helpers.update({
            "bin/a90_usbnet": USERLAND_BIN / "a90_usbnet-aarch64-static",
            "bin/busybox": USERLAND_BIN / "busybox-aarch64-static-1.36.1",
            "bin/toybox": USERLAND_BIN / "toybox-aarch64-static-0.8.13",
        })
        return helpers

    base.base.ramdisk_helpers = ramdisk_helpers_with_fasttransport


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V2168 QCACLD Firmware Class Fasttransport Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2168`",
        "- Type: source/build-only v725-fasttransport based QCACLD firmware_class feeder test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2168 keeps the V2137 QCACLD firmware_class feeder route but bumps the test boot above v725 and adds the v725 fasttransport ramdisk/PID1 transport contract.",
        "- Manifest: `workspace/private/builds/native-init/v2168-qcacld-fwclass-fasttransport-test-boot/manifest.json`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Transport Baseline",
        "",
        "- Test boot version is `0.9.245`, above `0.9.244 (v725-fasttransport)`.",
        "- PID1 uses `/bin/a90_usbnet`, `/bin/a90_tcpctl`, `/bin/toybox`, and `/bin/busybox` fasttransport paths.",
        "- Ramdisk includes `a90_usbnet`, `a90_tcpctl`, `toybox`, `busybox`, and the QCACLD feeder helper.",
        "",
        "## Wi-Fi Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2137: firmware mounts, `firmware_class.path` vendor path, RFS bridges, post-FW_READY `boot_wlan`, firmware_class sampler, and bounded userspace feeder for observed QCACLD request nodes.",
        "",
        "## Safety Scope",
        "",
        "This build script performs host-side source/build work only. The eventual handoff remains rollbackable to `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`.",
        "",
    ])


def main() -> int:
    configure_base()
    base = base_module()
    prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
