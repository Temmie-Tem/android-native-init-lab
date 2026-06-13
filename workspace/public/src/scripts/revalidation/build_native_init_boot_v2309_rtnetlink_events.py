#!/usr/bin/env python3
"""Build V2309 rtnetlink event-monitor test boot.

This wrapper keeps the V2237 WLAN route and adds the read-only
`wifi netevents [timeout_ms]` rtnetlink monitor surface.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2237_supplicant_terminate_poll as v2237
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2309-rtnetlink-events")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2309_RTNETLINK_EVENTS_SOURCE_BUILD_2026-06-13.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2309_rtnetlink_events.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2309_rtnetlink_events"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2309_rtnetlink_events.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v430_rtnetlink_events"
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
        "--cycle": "V2309",
        "--decision": "v2309-rtnetlink-events-source-build-pass",
        "--cycle-label": "v2309",
        "--init-version": "0.9.273",
        "--init-build": "v2309-rtnetlink-events",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2309",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2309.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2309.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2309.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2309-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2309.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2309-supervisor.pid",
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
        "# Native Init V2309 RTNETLINK Events Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2309`",
        "- Track: Active epic / E2 rtnetlink link-address monitor.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: `GOAL.md` marks T1 saturated and kernel security/observation closed. Wi-Fi credentials are absent, so active-epic ordering selects E2 before E1.",
        "- Manifest: `workspace/private/builds/native-init/v2309-rtnetlink-events/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Kept from V2237: service-object-visible WLAN route, post-FWREADY `boot_wlan`, firmware_class feeder, strict `wifi connect` validation, and bounded supplicant terminate polling.",
        "- Added for this build: `wifi netevents [timeout_ms]` opens `AF_NETLINK` / `NETLINK_ROUTE`, subscribes `RTMGRP_LINK | RTMGRP_IPV4_IFADDR`, and reports `RTM_NEWLINK`, `RTM_DELLINK`, `RTM_NEWADDR`, and `RTM_DELADDR` for `wlan0` and `ncm0`.",
        "- The event surface logs only redacted IPv4 labels (`a.b.c.x`), emits `raw_ip_redacted=1`, and never starts scan/connect/DHCP/ping.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. The new `wifi netevents` command is a read-only rtnetlink monitor. It does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.",
        "",
        "## Parked Validation",
        "",
        "- Full E1 nl80211 connect-event validation remains parked until Wi-Fi credentials are present.",
        "- This V2309 E2 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi netevents` validation.",
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
    manifest["candidate_tag"] = "v2309-rtnetlink-events"
    manifest["parent_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["rtnetlink_events"] = {
        "command": "wifi netevents [timeout_ms]",
        "groups": ["RTMGRP_LINK", "RTMGRP_IPV4_IFADDR"],
        "ifaces": ["wlan0", "ncm0"],
        "events": ["RTM_NEWLINK", "RTM_DELLINK", "RTM_NEWADDR", "RTM_DELADDR"],
        "scope": "read-only rtnetlink monitor",
        "raw_ip_redacted": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2309-rtnetlink-events",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2309 keeps the V2237 WLAN baseline and adds read-only RTNETLINK link/address event monitoring for wlan0/ncm0.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
