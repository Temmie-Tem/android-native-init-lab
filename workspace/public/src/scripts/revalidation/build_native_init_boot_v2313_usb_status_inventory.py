#!/usr/bin/env python3
"""Build V2313 USB gadget status inventory test boot.

This wrapper builds on V2312 and adds the read-only `usb status` command for
USB gadget topology inventory before any runtime reconfiguration work.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2312_e1_connect_event_closure as v2312
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2313-usb-status-inventory")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2313_USB_STATUS_INVENTORY_SOURCE_BUILD_2026-06-13.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2313_usb_status_inventory.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2313_usb_status_inventory"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2313_usb_status_inventory.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v432_usb_status_inventory"
REMOTE_PROPERTY_ROOT = v2312.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2312.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2312.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2312.EXTRA_INIT_FLAGS


def base_module():
    return v2312.base_module()


def helper_builder_module():
    return v2312.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2312.OUT_DIR = OUT_DIR
    v2312.REPORT_PATH = REPORT_PATH
    v2312.BOOT_IMAGE = BOOT_IMAGE
    v2312.INIT_BINARY = INIT_BINARY
    v2312.RAMDISK_CPIO = RAMDISK_CPIO
    v2312.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2312.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2313",
        "--decision": "v2313-usb-status-inventory-source-build-pass",
        "--cycle-label": "v2313",
        "--init-version": "0.9.277",
        "--init-build": "v2313-usb-status-inventory",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2313",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2313.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2313.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2313.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2313-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2313.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2313-supervisor.pid",
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
        "# Native Init V2313 USB Status Inventory Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2313`",
        "- Track: active USB gadget runtime-control epic layer 1, U1 inventory.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: U1 must map the live USB gadget topology before any runtime reconfiguration work. This build adds only the read-only `usb status` command.",
        "- Manifest: `workspace/private/builds/native-init/v2313-usb-status-inventory/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Command Scope",
        "",
        "- Added `usb [status]`.",
        "- Reads `/config/usb_gadget/g1`, configs, functions, strings, `UDC`, and `/sys/class/udc`.",
        "- Classifies config links as `control-acm`, `control-ncm`, or `aux` by function name.",
        "- Prints `control.ok=1` only when both ACM and NCM control functions are linked.",
        "- Redacts the raw USB serial string and reports only presence and length.",
        "- Emits `mutation_attempted=0` and performs no configfs/sysfs writes.",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Parent test artifact: `v2312-e1-connect-event-closure`.",
        "- Rollback checkpoint remains: `v2237-supplicant-terminate-poll`.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. U1 is read-only: it does not unbind or rebind the UDC, add or remove USB functions, modify configfs/sysfs, run Wi-Fi scan/connect/DHCP/ping, touch forbidden partitions, or start adb-over-ffs/HID/BadUSB work.",
        "",
        "## Required Device Step",
        "",
        "- Boot-only flash through `native_init_flash.py`.",
        "- `version` / `status` / `selftest fail=0`.",
        "- Run `usb status` over the serial bridge and verify `read_only=1`, `mutation_attempted=0`, UDC bind state, config/function inventory, and `control.ok=1` if the live topology contains both control functions.",
        "- Host-side USB enumeration is not required for U1; it remains parked for U2/U3.",
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
    v2312.v2311.v2310.v2309.v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2313-usb-status-inventory"
    manifest["parent_baseline"] = "v2312-e1-connect-event-closure"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["usb_status_inventory"] = {
        "command": "usb [status]",
        "version": "a90-native-usb-status-v1",
        "reads": ["/config/usb_gadget/g1", "/sys/class/udc"],
        "control_required": ["control-acm", "control-ncm"],
        "mutation_attempted": False,
        "host_enumeration_required": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2313-usb-status-inventory",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2313 adds read-only USB gadget topology inventory via `usb status`.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
