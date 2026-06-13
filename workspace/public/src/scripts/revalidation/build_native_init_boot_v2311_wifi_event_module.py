#!/usr/bin/env python3
"""Build V2311 Wi-Fi event module split test boot.

This wrapper builds on V2310 and keeps the same `wifi events` / `wifi netevents`
behavior while moving the event monitor implementation out of `a90_wifi.c`.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2310_nl80211_events as v2310
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2311-wifi-event-module")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2311_WIFI_EVENT_MODULE_SOURCE_BUILD_2026-06-13.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2311_wifi_event_module.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2311_wifi_event_module"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2311_wifi_event_module.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v430_wifi_event_module"
REMOTE_PROPERTY_ROOT = v2310.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2310.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2310.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2310.EXTRA_INIT_FLAGS


def base_module():
    return v2310.base_module()


def helper_builder_module():
    return v2310.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2310.OUT_DIR = OUT_DIR
    v2310.REPORT_PATH = REPORT_PATH
    v2310.BOOT_IMAGE = BOOT_IMAGE
    v2310.INIT_BINARY = INIT_BINARY
    v2310.RAMDISK_CPIO = RAMDISK_CPIO
    v2310.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2310.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2311",
        "--decision": "v2311-wifi-event-module-source-build-pass",
        "--cycle-label": "v2311",
        "--init-version": "0.9.275",
        "--init-build": "v2311-wifi-event-module",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2311",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2311.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2311.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2311.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2311-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2311.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2311-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    wifi = manifest["wifi_test"]
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    return "\n".join([
        "# Native Init V2311 Wi-Fi Event Module Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2311`",
        "- Track: T2 native-init / WLAN baseline improvement.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: the active E1/E2 event epic is implemented to the no-creds validation ceiling; this iteration reduces the now-grown `a90_wifi.c` surface by splitting rtnetlink/nl80211 event monitors into `a90_wifi_events.c` without changing command behavior.",
        "- Manifest: `workspace/private/builds/native-init/v2311-wifi-event-module/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Refactor Scope",
        "",
        "- Moved the read-only `wifi netevents [timeout_ms]` rtnetlink monitor implementation out of `a90_wifi.c`.",
        "- Moved the read-only `wifi events [timeout_ms]` nl80211 multicast monitor implementation out of `a90_wifi.c`.",
        "- Kept command routing and public prototypes in `a90_wifi.h` unchanged.",
        "- Kept V2310 event behavior: `mlme`/`scan`/`config` group subscription, redacted output, and no scan/connect/DHCP/ping side effects.",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Parent test artifact: `v2310-nl80211-events`.",
        "- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. The refactor changes native-init code organization but does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.",
        "",
        "## Parked Validation",
        "",
        "- Full Wi-Fi connect/DHCP/ping validation remains parked until Wi-Fi credentials are present.",
        "- This V2311 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi events` / `wifi netevents` validation without scan/connect.",
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
    v2310.v2309.v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2311-wifi-event-module"
    manifest["parent_baseline"] = "v2310-nl80211-events"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["wifi_event_module"] = {
        "moved_from": "workspace/public/src/native-init/a90_wifi.c",
        "moved_to": "workspace/public/src/native-init/a90_wifi_events.c",
        "commands": ["wifi events [timeout_ms]", "wifi netevents [timeout_ms]"],
        "behavior_change_intended": False,
        "credential_free_validation": ["wifi status", "wifi events 1000", "wifi netevents 1000"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2311-wifi-event-module",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2311 keeps V2310 event behavior and moves Wi-Fi event monitors into a dedicated module.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
