#!/usr/bin/env python3
"""Build V2310 nl80211 event-subscription test boot.

This wrapper builds on V2309 and adds the read-only
`wifi events [timeout_ms]` nl80211 multicast event surface.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2309_rtnetlink_events as v2309
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2310-nl80211-events")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2310_NL80211_EVENTS_SOURCE_BUILD_2026-06-13.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2310_nl80211_events.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2310_nl80211_events"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2310_nl80211_events.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v430_nl80211_events"
REMOTE_PROPERTY_ROOT = v2309.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2309.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2309.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2309.EXTRA_INIT_FLAGS


def base_module():
    return v2309.base_module()


def helper_builder_module():
    return v2309.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2309.OUT_DIR = OUT_DIR
    v2309.REPORT_PATH = REPORT_PATH
    v2309.BOOT_IMAGE = BOOT_IMAGE
    v2309.INIT_BINARY = INIT_BINARY
    v2309.RAMDISK_CPIO = RAMDISK_CPIO
    v2309.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2309.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2310",
        "--decision": "v2310-nl80211-events-source-build-pass",
        "--cycle-label": "v2310",
        "--init-version": "0.9.274",
        "--init-build": "v2310-nl80211-events",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2310",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2310.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2310.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2310.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2310-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2310.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2310-supervisor.pid",
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
        "# Native Init V2310 NL80211 Events Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2310`",
        "- Track: Active epic / E1 nl80211 multicast event subscription.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V2309 completed E2. This iteration implements the remaining E1 surface. Wi-Fi credentials are absent, so connect-event assertion remains parked per `GOAL.md`.",
        "- Manifest: `workspace/private/builds/native-init/v2310-nl80211-events/manifest.json`",
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
        "- Kept from V2309: read-only rtnetlink `wifi netevents` monitor and the V2237 WLAN bring-up route.",
        "- Added for this build: `wifi events [timeout_ms]` reads `CTRL_ATTR_MCAST_GROUPS` from `GETFAMILY nl80211`, subscribes `mlme`, `scan`, and `config` with `NETLINK_ADD_MEMBERSHIP`, and decodes `NL80211_CMD_CONNECT`, `NL80211_CMD_DISCONNECT`, `NL80211_CMD_NEW_SCAN_RESULTS`, `NL80211_CMD_SCAN_ABORTED`, and `NL80211_CMD_ROAM`.",
        "- The event surface emits `raw_bssid_redacted=1`, `raw_ip_redacted=1`, and never starts scan/connect/DHCP/ping.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. The new `wifi events` command is a read-only nl80211 multicast monitor. It does not run Wi-Fi scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/device partitions.",
        "",
        "## Parked Validation",
        "",
        "- Full E1 connect-event assertion remains parked until Wi-Fi credentials are present.",
        "- This V2310 artifact still requires the device step: boot-only flash, `version`/`status`/`selftest fail=0`, and bounded `wifi events` subscription validation without scan/connect.",
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
    v2309.v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2310-nl80211-events"
    manifest["parent_baseline"] = "v2309-rtnetlink-events"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["nl80211_events"] = {
        "command": "wifi events [timeout_ms]",
        "family": "nl80211",
        "groups": ["mlme", "scan", "config"],
        "events": [
            "NL80211_CMD_CONNECT",
            "NL80211_CMD_DISCONNECT",
            "NL80211_CMD_NEW_SCAN_RESULTS",
            "NL80211_CMD_SCAN_ABORTED",
            "NL80211_CMD_ROAM",
        ],
        "scope": "read-only nl80211 multicast monitor",
        "raw_bssid_redacted": True,
        "raw_ip_redacted": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2310-nl80211-events",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2310 builds on V2309 and adds read-only nl80211 multicast event monitoring.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
