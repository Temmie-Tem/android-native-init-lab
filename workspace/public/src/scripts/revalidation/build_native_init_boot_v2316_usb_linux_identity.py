#!/usr/bin/env python3
"""Build V2316 USB Linux-identity baseline boot.

This wrapper builds on V2315 and changes only the host-visible USB gadget
identity strings to an honest "ARM Linux computer" identity (manufacturer
``A90 NativeInit`` / product ``A90 Linux (ARM)``), with the device serial
already redacted to a placeholder. The USB ``idVendor``/``idProduct`` are kept
at ``0x04e8``/``0x6861`` so the NCM host-side transport detection and udev
rules continue to bind. No command surface or persona behavior changes; V2316
carries the full V2313-V2315 USB control surface and is promoted as the
resident rollback checkpoint after live both-band Wi-Fi validation.
"""

from __future__ import annotations

import json

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2315_usb_mass_storage_persona as v2315
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2316-usb-linux-identity")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2316_USB_LINUX_IDENTITY_SOURCE_BUILD_2026-06-14.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2316_usb_linux_identity.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2316_usb_linux_identity"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2316_usb_linux_identity.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v434_usb_linux_identity"
REMOTE_PROPERTY_ROOT = v2315.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2315.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2315.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2315.EXTRA_INIT_FLAGS
BACKING_PATH = v2315.BACKING_PATH
BACKING_BYTES = v2315.BACKING_BYTES

USB_IDENTITY = {
    "id_vendor": "0x04e8",
    "id_product": "0x6861",
    "manufacturer": "A90 NativeInit",
    "product": "A90 Linux (ARM)",
    "serialnumber": "A90NATIVE001",
    "vid_pid_kept_for": "ncm-host-transport-and-udev-detection",
}


def base_module():
    return v2315.base_module()


def helper_builder_module():
    return v2315.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def configure_base() -> tuple[str, ...]:
    v2315.OUT_DIR = OUT_DIR
    v2315.REPORT_PATH = REPORT_PATH
    v2315.BOOT_IMAGE = BOOT_IMAGE
    v2315.INIT_BINARY = INIT_BINARY
    v2315.RAMDISK_CPIO = RAMDISK_CPIO
    v2315.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    helper_flags = v2315.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2316",
        "--decision": "v2316-usb-linux-identity-source-build-pass",
        "--cycle-label": "v2316",
        "--init-version": "0.9.280",
        "--init-build": "v2316-usb-linux-identity",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2316",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2316.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2316.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2316.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2316-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2316.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2316-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    return "\n".join([
        "# Native Init V2316 USB Linux Identity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2316`",
        "- Track: active USB gadget runtime-control epic layer 1, identity hygiene + rollback-checkpoint promotion candidate.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: present an honest ARM-Linux USB identity and redacted serial; promote as resident rollback checkpoint after live validation.",
        "- Manifest: `workspace/private/builds/native-init/v2316-usb-linux-identity/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Identity Change",
        "",
        "- `manufacturer`: `samsung` -> `A90 NativeInit`.",
        "- `product`: `SM8150-ACM` -> `A90 Linux (ARM)`.",
        "- `serialnumber`: real device serial -> placeholder `A90NATIVE001`.",
        "- `idVendor`/`idProduct` kept at `0x04e8`/`0x6861` so NCM host-side transport detection and the udev rules continue to bind; only the human-readable strings change.",
        "- Applied in all three identity-write sites: boot ACM setup, the NCM/usbnet boot gadget, and the reconfigure control-base rebuild path (so personas do not revert the identity).",
        "",
        "## Command Scope",
        "",
        "- No command surface change. Inherits the full V2313-V2315 USB control surface (`usb status`, `usb mass-storage add/remove/expose`).",
        "- Reconfigure still uses the V2314 detached worker, NCM+ACM preservation, watchdog, and known-good restore path.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. It changes only USB gadget identity strings; no command behavior, partition write, kernel module/code, adb-over-ffs, HID, or BadUSB change. Wi-Fi both-band validation is performed live at the device step as the rollback-checkpoint promotion bar.",
        "",
        "## Required Device Step (rollback-checkpoint promotion bar)",
        "",
        "- Boot-only flash through `native_init_flash.py`, pinned SHA, auto-rollback to `v2237` on any failure.",
        "- `version` / `status` / `selftest fail=0`.",
        "- `usb status`: host-visible `product` reads `A90 Linux (ARM)`, `manufacturer` reads `A90 NativeInit`, serial is the placeholder, `idVendor=0x04e8`, `control.ok=1`.",
        "- USB persona regression: `usb mass-storage expose` then `remove`; confirm the control channel returns and the identity strings persist across the reconfigure.",
        "- Wi-Fi both-band end-to-end: associate -> DHCP -> external ping on 2.4 GHz and 5 GHz (credentials from `workspace/private/secrets/`; redact SSID/BSSID/IP/MAC; never log PSK).",
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
    v2315.v2314.v2313.v2312.v2311.v2310.v2309.v2237.patch_mkbootimg_tools(base)
    base.render_report = lambda manifest: render_report(manifest, helper_flags)
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_tag"] = "v2316-usb-linux-identity"
    manifest["parent_baseline"] = "v2315-usb-ms-persona"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["usb_identity"] = USB_IDENTITY
    manifest["promotion_intent"] = "resident-rollback-checkpoint-after-live-both-band-wifi"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2316-usb-linux-identity",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "note": "V2316 redacts the device serial and presents an honest ARM-Linux USB identity; rollback-checkpoint promotion candidate.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
