#!/usr/bin/env python3
"""Build V2252 firmware_class boundary stack-snapshot test boot.

This source/build wrapper keeps the V2237 Wi-Fi route and adds deterministic
helper-owned /proc/*/stack snapshots immediately before and after each QCACLD
firmware_class fallback feed operation.  It does not add BPF, tracefs writes,
or any Wi-Fi scan/connect action.
"""

from __future__ import annotations

import json
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2237_supplicant_terminate_poll as v2237
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2252-fwclass-boundary-stack")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2252_FWCLASS_BOUNDARY_STACK_SOURCE_BUILD_2026-06-12.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2252_fwclass_boundary_stack.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2252_fwclass_boundary_stack"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2252_fwclass_boundary_stack.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v430_fwclass_boundary_stack"
REMOTE_PROPERTY_ROOT = v2237.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v430"
EXPECTED_HELPER_SHA256 = "7f31ff603a486cf42a026fdfe43e6f9de03a3d6e3883aa2a25bd54b254c88c94"
EXTRA_INIT_FLAGS = v2237.EXTRA_INIT_FLAGS
HELPER_MODE = v2237.HELPER_MODE
HELPER_RUNTIME_MODE = v2237.HELPER_RUNTIME_MODE
BOUNDARY_STACK_FLAG = "-DA90_WIFI_TEST_BOOT_QCACLD_FWCLASS_BOUNDARY_STACK_SAMPLER=1"


def base_module():
    return v2237.base_module()


def helper_chain():
    return v2237.helper_chain()


def helper_builder_module():
    return v2237.helper_builder_module()


def with_boundary_stack_flag(flags: tuple[str, ...]) -> tuple[str, ...]:
    merged = v2237.with_bridge_flag(flags)
    return (*tuple(flag for flag in merged if flag != BOUNDARY_STACK_FLAG), BOUNDARY_STACK_FLAG)


def configure_helper_flags() -> tuple[str, ...]:
    prev2137 = helper_chain()
    helper_flags = with_boundary_stack_flag(prev2137.HELPER_FLAGS)
    prev2137.HELPER_FLAGS = helper_flags
    prev2137.prev2135.HELPER_FLAGS = helper_flags
    prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS = helper_flags
    helper_builder_module().HELPER_FLAGS = helper_flags
    return helper_flags


def configure_base() -> tuple[str, ...]:
    v2237.OUT_DIR = OUT_DIR
    v2237.REPORT_PATH = REPORT_PATH
    v2237.BOOT_IMAGE = BOOT_IMAGE
    v2237.INIT_BINARY = INIT_BINARY
    v2237.RAMDISK_CPIO = RAMDISK_CPIO
    v2237.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v2237.configure_base()
    helper_flags = configure_helper_flags()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2252",
        "--decision": "v2252-fwclass-boundary-stack-source-build-pass",
        "--cycle-label": "v2252",
        "--init-version": "0.9.271",
        "--init-build": "v2252-fwclass-boundary-stack",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2252",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2252.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2252.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2252.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2252-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2252.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2252-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode": HELPER_MODE,
        "--wifi-test-watch-sec": "190",
        "--wifi-test-supervisor-timeout-sec": "245",
    }
    for key, value in replacements.items():
        v2237.v2230.v2189.v2188.v2187.v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    wifi = manifest["wifi_test"]
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    return "\n".join([
        "# Native Init V2252 Firmware Class Boundary Stack Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2252`",
        "- Type: source/build-only rollbackable post-FWREADY firmware_class boundary stack observer test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2251 showed the generic CPU-clock tail sampler missed the short target window, while helper-owned `/proc/*/stack` snapshots still caught QCACLD target functions. This build keeps the V2237 route and adds deterministic stack snapshots at the exact QCACLD firmware_class fallback feed boundaries.",
        "- Manifest: `workspace/private/builds/native-init/v2252-fwclass-boundary-stack/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe v430` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2237: service-object-visible route, post-FWREADY `boot_wlan`, QCACLD firmware_class feeder, and strict supplicant terminate polling.",
        "- Added for this build: `A90_WIFI_TEST_BOOT_QCACLD_FWCLASS_BOUNDARY_STACK_SAMPLER=1`.",
        "- Boundary contract: when `/sys/devices/virtual/firmware/<request>` appears, emit `qcacld_fwclass_boundary_stack_sampler.*.before_feed`, run `icnss_register_probe_stack_sampler.fwclass_reqN_before_feed`, feed the firmware_class request, then emit the matching `after_feed` snapshot.",
        "- Target requests: `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin` under `wlan/qca_cld/`.",
        "- Next live use: V2253 should flash this image and classify whether target functions are present before or after each firmware_class feed edge without relying on generic CPU-clock sampling.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions. The new helper observer reads `/proc/*/stack`; only the pre-existing firmware_class userspace fallback feeder writes to `/sys/devices/virtual/firmware/*/{loading,data}` for the three bounded QCACLD requests.",
        "",
    ])


def main() -> int:
    helper_flags = configure_base()
    helper_builder = helper_builder_module()
    helper_builder.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    helper_builder.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base = base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    helper_builder.patch_helper_builder(base)
    v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2252-fwclass-boundary-stack"
    manifest["helper_flags"] = list(helper_flags)
    manifest["boundary_stack_flag"] = BOUNDARY_STACK_FLAG
    manifest["boundary_stack_contract"] = {
        "prefix": "qcacld_fwclass_boundary_stack_sampler",
        "stack_sampler_prefix": "icnss_register_probe_stack_sampler",
        "points": ["before_feed", "after_feed"],
        "requests": ["WCNSS_qcom_cfg.ini", "bdwlan.bin", "regdb.bin"],
        "live_validation_cycle": "V2253",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2252-fwclass-boundary-stack",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2252 keeps the V2237 WLAN route and adds deterministic QCACLD firmware_class before/after feed stack snapshots for the V2253 live classifier.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
