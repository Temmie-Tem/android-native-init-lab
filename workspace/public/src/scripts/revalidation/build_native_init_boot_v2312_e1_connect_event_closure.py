#!/usr/bin/env python3
"""Build V2312 E1 connect-event closure test boot.

This wrapper builds on V2311 and adds the device-side `wifi connect-event`
combined capture command needed when the serial console cannot run the event
monitor and connect command concurrently.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2311_wifi_event_module as v2311
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2312-e1-connect-event-closure")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2312_E1_CONNECT_EVENT_CLOSURE_SOURCE_BUILD_2026-06-13.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2312_e1_connect_event_closure.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2312_e1_connect_event_closure"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2312_e1_connect_event_closure.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v431_e1_connect_event_closure"
REMOTE_PROPERTY_ROOT = v2311.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2311.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2311.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2311.EXTRA_INIT_FLAGS


def base_module():
    return v2311.base_module()


def helper_builder_module():
    return v2311.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2311.OUT_DIR = OUT_DIR
    v2311.REPORT_PATH = REPORT_PATH
    v2311.BOOT_IMAGE = BOOT_IMAGE
    v2311.INIT_BINARY = INIT_BINARY
    v2311.RAMDISK_CPIO = RAMDISK_CPIO
    v2311.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2311.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2312",
        "--decision": "v2312-e1-connect-event-closure-source-build-pass",
        "--cycle-label": "v2312",
        "--init-version": "0.9.276",
        "--init-build": "v2312-e1-connect-event-closure",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2312",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2312.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2312.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2312.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2312-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2312.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2312-supervisor.pid",
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
        "# Native Init V2312 E1 Connect-Event Closure Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2312`",
        "- Track: active epic final closure — E1 nl80211 connect-event assertion.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: Wi-Fi credentials are now present, but the host lacks a configured second NCM/tcpctl channel. This build adds a device-side `wifi connect-event [profile] [timeout_ms]` combined capture so nl80211 `CONNECT` and carrier can be validated in one bounded command.",
        "- Manifest: `workspace/private/builds/native-init/v2312-e1-connect-event-closure/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Command Scope",
        "",
        "- Added `wifi connect-event [profile] [timeout_ms]`.",
        "- The command subscribes to nl80211 multicast groups before forking a silenced child that runs the existing `wifi connect [profile]` path.",
        "- The parent records redacted nl80211 event counters, waits for the bounded connect child, samples `wifi status`, and passes only when `NL80211_CMD_CONNECT` is observed and final carrier is up.",
        "- It does not run DHCP, install routes, set DNS, ping, print raw SSID/PSK/BSSID/MAC/IP, or enable boot autoconnect.",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Parent test artifact: `v2311-wifi-event-module`.",
        "- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. The new command is a bounded Wi-Fi association/event assertion only. It does not run DHCP, configure routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.",
        "",
        "## Required Device Step",
        "",
        "- Boot-only flash through `native_init_flash.py`.",
        "- `version` / `status` / `selftest fail=0`.",
        "- Stage private Wi-Fi profile from `workspace/private/secrets/a90-wifi-test.env` without logging secrets.",
        "- Run one bounded `wifi connect-event` cycle.",
        "- Run `wifi cleanup` afterward.",
        "- Commit only redacted metadata and the closure report.",
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
    v2311.v2310.v2309.v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2312-e1-connect-event-closure"
    manifest["parent_baseline"] = "v2311-wifi-event-module"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["wifi_connect_event_closure"] = {
        "command": "wifi connect-event [profile] [timeout_ms]",
        "event_assertion": "NL80211_CMD_CONNECT observed and final carrier is up",
        "uses_existing_connect_path": True,
        "dhcp_attempted": False,
        "external_ping_attempted": False,
        "secret_values_logged": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2312-e1-connect-event-closure",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2312 adds bounded device-side E1 connect-event closure capture.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
