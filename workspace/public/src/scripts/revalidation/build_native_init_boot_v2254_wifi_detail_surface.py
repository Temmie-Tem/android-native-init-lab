#!/usr/bin/env python3
"""Build V2254 Wi-Fi detail status-surface test boot.

This source/build wrapper keeps the promoted V2237 WLAN route and only extends
the read-only native Wi-Fi status/menu surface with route/DNS detail labels.
It does not add a live Wi-Fi action, credential path, or helper observer.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2237_supplicant_terminate_poll as v2237
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2254-wifi-detail-surface")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2254_WIFI_DETAIL_SURFACE_SOURCE_BUILD_2026-06-12.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2254_wifi_detail_surface.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2254_wifi_detail_surface"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2254_wifi_detail_surface.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v430_wifi_detail_surface"
REMOTE_PROPERTY_ROOT = v2237.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2237.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2237.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2237.EXTRA_INIT_FLAGS


def base_module():
    return v2237.base_module()


def helper_builder_module():
    return v2237.helper_builder_module()


def configure_base() -> tuple[str, ...]:
    v2237.OUT_DIR = OUT_DIR
    v2237.REPORT_PATH = REPORT_PATH
    v2237.BOOT_IMAGE = BOOT_IMAGE
    v2237.INIT_BINARY = INIT_BINARY
    v2237.RAMDISK_CPIO = RAMDISK_CPIO
    v2237.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2237.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2254",
        "--decision": "v2254-wifi-detail-surface-source-build-pass",
        "--cycle-label": "v2254",
        "--init-version": "0.9.272",
        "--init-build": "v2254-wifi-detail-surface",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2254",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2254.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2254.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2254.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2254-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2254.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2254-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
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
        "# Native Init V2254 Wi-Fi Detail Surface Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2254`",
        "- Track: T2 WLAN native-init surface/cleanup.",
        "- Type: source/build-only rollbackable Wi-Fi detail status-surface test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2253 closed the active T1 firmware_class boundary question; no new independent T1 oracle was selected. Per `GOAL.md`, this iteration records the downgrade trigger and advances the next T2 item: read-only network detail surface.",
        "- Manifest: `workspace/private/builds/native-init/v2254-wifi-detail-surface/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Track Transition",
        "",
        "- Dropped from T1 to T2 for this iteration.",
        "- Trigger: V2253 proved the qcacld/HDD firmware_class stack executes before the `WCNSS_qcom_cfg.ini` userspace feed and closed the V2250 sampler-miss ambiguity. Another generic CPU-clock or same-boundary observer would only re-confirm established facts.",
        "- No kernel-write primitive, RKP bypass, `probe_write_user`, or new live kernel oracle is required for the selected T2 item.",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2237: service-object-visible WLAN route, post-FWREADY `boot_wlan`, firmware_class feeder, strict `wifi connect` validation, and bounded supplicant terminate polling.",
        "- Added for this build: `wifi status` now reports `default_route_present`, redacted `gateway_label`, `gateway_rc`, `resolv_conf.present`, and `resolv_conf.nameserver_count`.",
        "- Added for this build: `NETWORK > WIFI STATUS` renders route/default-DNS state on the device screen without starting scan/connect/DHCP/ping.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The new status fields are read-only `/sys`, `/proc/net/route`, and `/cache/a90-wifi/resolv.conf` observations. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
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
    manifest["candidate_tag"] = "v2254-wifi-detail-surface"
    manifest["parent_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["wifi_detail_surface"] = {
        "status_fields_added": [
            "default_route_present",
            "gateway_label",
            "gateway_rc",
            "resolv_conf.present",
            "resolv_conf.nameserver_count",
        ],
        "ui_surface": "NETWORK > WIFI STATUS",
        "scope": "read-only status/menu surface",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2254-wifi-detail-surface",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2254 keeps the V2237 WLAN baseline and adds read-only route/DNS detail to wifi status and NETWORK > WIFI STATUS.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
