#!/usr/bin/env python3
"""Build V2317 USB product-rodata test boot.

V2317 keeps the V2316 native-init userspace and USB control surface, but applies
a fixed-length kernel rodata patch to the Samsung-forced USB product string only:
``SAMSUNG_Android`` -> ``A90 Linux ARM``. Manufacturer is intentionally left as
``SAMSUNG`` for this first kernel-side identity experiment because the
manufacturer literal is merged with another rodata string in the stock kernel.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import tempfile
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import build_native_init_boot_v2316_usb_linux_identity as v2316
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


OUT_DIR = workspace_private_build_path("native-init", "v2317-usb-product-rodata")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2317_USB_PRODUCT_RODATA_SOURCE_BUILD_2026-06-14.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2317_usb_product_rodata.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2317_usb_product_rodata"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2317_usb_product_rodata.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v434_usb_product_rodata"
PATCHED_KERNEL = OUT_DIR / "kernel_v2317_usb_product_rodata"
REMOTE_PROPERTY_ROOT = v2316.REMOTE_PROPERTY_ROOT
EXPECTED_HELPER_MARKER = v2316.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = v2316.EXPECTED_HELPER_SHA256
EXTRA_INIT_FLAGS = v2316.EXTRA_INIT_FLAGS
THIRD_PARTY_MKBOOTIMG = REPO_ROOT / "workspace" / "public" / "src" / "third_party" / "mkbootimg"

EXPECTED_SOURCE_KERNEL_SHA256 = "9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a"
PRODUCT_OFFSET = 0x233C11E
PRODUCT_OLD = b"SAMSUNG_Android\x00"
PRODUCT_NEW = b"A90 Linux ARM\x00\x00\x00"

USB_PRODUCT_RODATA_PATCH = {
    "mode": "product-only",
    "reason": "V2316 proved host iProduct is Samsung-forced by kernel rodata; product literal is unique.",
    "manufacturer": "unchanged-kernel-forced-SAMSUNG",
    "product_old": "SAMSUNG_Android",
    "product_new": "A90 Linux ARM",
    "offset": hex(PRODUCT_OFFSET),
    "old_len": len(PRODUCT_OLD),
    "new_len": len(PRODUCT_NEW),
    "source_kernel_sha256": EXPECTED_SOURCE_KERNEL_SHA256,
}
LAST_PATCH_INFO: dict[str, object] | None = None


def base_module():
    return v2316.base_module()


def helper_builder_module():
    return v2316.helper_builder_module()


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def patch_kernel_product_literal(source_kernel: Path, patched_kernel: Path) -> dict[str, object]:
    source_sha = sha256(source_kernel)
    if source_sha != EXPECTED_SOURCE_KERNEL_SHA256:
        raise RuntimeError(
            f"unexpected source kernel sha256: {source_sha}; "
            f"expected {EXPECTED_SOURCE_KERNEL_SHA256}"
        )

    data = bytearray(source_kernel.read_bytes())
    found = data.count(PRODUCT_OLD)
    if found != 1:
        raise RuntimeError(f"expected exactly one product literal, found {found}")
    actual_offset = data.find(PRODUCT_OLD)
    if actual_offset != PRODUCT_OFFSET:
        raise RuntimeError(f"product literal offset changed: {hex(actual_offset)} != {hex(PRODUCT_OFFSET)}")
    if data[PRODUCT_OFFSET:PRODUCT_OFFSET + len(PRODUCT_OLD)] != PRODUCT_OLD:
        raise RuntimeError("product literal bytes do not match expected old value")
    if len(PRODUCT_OLD) != len(PRODUCT_NEW):
        raise RuntimeError("product replacement must be fixed-length")

    data[PRODUCT_OFFSET:PRODUCT_OFFSET + len(PRODUCT_NEW)] = PRODUCT_NEW
    patched_kernel.parent.mkdir(parents=True, exist_ok=True)
    patched_kernel.write_bytes(data)
    patched_kernel.chmod(0o600)

    post = patched_kernel.read_bytes()
    if post.count(PRODUCT_OLD) != 0:
        raise RuntimeError("old product literal still present after patch")
    if post.count(PRODUCT_NEW.rstrip(b"\x00") + b"\x00") != 1:
        raise RuntimeError("new product literal not uniquely present after patch")
    if post.count(b"SAMSUNG\x00") != 1:
        raise RuntimeError("manufacturer literal unexpectedly changed")

    return {
        **USB_PRODUCT_RODATA_PATCH,
        "patched_kernel_sha256": sha256(patched_kernel),
    }


def configure_base() -> tuple[str, ...]:
    v2316.OUT_DIR = OUT_DIR
    v2316.REPORT_PATH = REPORT_PATH
    v2316.BOOT_IMAGE = BOOT_IMAGE
    v2316.INIT_BINARY = INIT_BINARY
    v2316.RAMDISK_CPIO = RAMDISK_CPIO
    helper_flags = v2316.configure_base()

    base = base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2317",
        "--decision": "v2317-usb-product-rodata-source-build-pass",
        "--cycle-label": "v2317",
        "--init-version": "0.9.281",
        "--init-build": "v2317-usb-product-rodata",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(INIT_BINARY),
        "--helper-binary": str(HELPER_BINARY),
        "--ramdisk-cpio": str(RAMDISK_CPIO),
        "--boot-image": str(BOOT_IMAGE),
        "--wifi-test-klog-prefix": "A90v2317",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2317.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2317.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2317.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2317-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2317.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2317-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        set_arg(args, key, value)
    base.DEFAULT_ARGS = args
    base.base.EXTRA_INIT_FLAGS = EXTRA_INIT_FLAGS
    return helper_flags


def patch_mkbootimg_tools(base_wrapper) -> None:
    build_base = base_wrapper.base

    def build_boot_image(args) -> None:
        global LAST_PATCH_INFO
        with tempfile.TemporaryDirectory(prefix="a90-v2317-unpack-") as temp_name:
            temp_dir = Path(temp_name)
            unpack_args = build_base.run(
                [
                    "python3",
                    THIRD_PARTY_MKBOOTIMG / "unpack_bootimg.py",
                    "--boot_img",
                    args.base_boot,
                    "--out",
                    temp_dir,
                    "--format=mkbootimg",
                ],
                capture=True,
            ).stdout
            mkboot_args = shlex.split(unpack_args)

            patch_info = patch_kernel_product_literal(temp_dir / "kernel", PATCHED_KERNEL)
            LAST_PATCH_INFO = patch_info
            args.product_rodata_patch_info = patch_info

            for index, item in enumerate(mkboot_args):
                if item == "--ramdisk":
                    mkboot_args[index + 1] = str(args.ramdisk_cpio)
                if item == "--kernel":
                    mkboot_args[index + 1] = str(PATCHED_KERNEL)

            if "--ramdisk" not in mkboot_args:
                raise RuntimeError("base boot image mkbootimg args did not include --ramdisk")
            if "--kernel" not in mkboot_args:
                raise RuntimeError("base boot image mkbootimg args did not include --kernel")

            if args.boot_image.exists():
                args.boot_image.unlink()
            args.boot_image.parent.mkdir(parents=True, exist_ok=True)
            build_base.run([
                "python3",
                THIRD_PARTY_MKBOOTIMG / "mkbootimg.py",
                *mkboot_args,
                "--output",
                args.boot_image,
            ])
        args.boot_image.chmod(0o600)

    build_base.build_boot_image = build_boot_image


def render_report(manifest: dict[str, object], helper_flags: tuple[str, ...]) -> str:
    helper_flag_lines = [f"- `{flag}`" for flag in helper_flags]
    patch_info = manifest["usb_product_rodata_patch"]
    return "\n".join([
        "# Native Init V2317 USB Product Rodata Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2317`",
        "- Track: USB identity follow-up after V2316 proved host `iManufacturer`/`iProduct` are kernel-forced.",
        "- Type: source/build-only rollbackable native-init test boot.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: test the lowest-risk kernel-side identity change first: product-only fixed-length rodata patch.",
        "- Manifest: `workspace/private/builds/native-init/v2317-usb-product-rodata/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `{manifest['helper_marker']}`)",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Product Rodata Patch",
        "",
        f"- Source kernel SHA256: `{patch_info['source_kernel_sha256']}`",
        f"- Patched kernel SHA256: `{patch_info['patched_kernel_sha256']}`",
        f"- Offset: `{patch_info['offset']}`",
        "- Old product: `SAMSUNG_Android`.",
        "- New product: `A90 Linux ARM`.",
        "- Manufacturer: unchanged (`SAMSUNG`).",
        "- Constraint: fixed-length replacement only; no section-size or code-layout change.",
        "",
        "## Why Product-Only First",
        "",
        "- The product literal is unique in the extracted V2316 kernel blob.",
        "- The manufacturer literal is not patched in this build because V2317 feasibility found it merged with an unrelated rodata suffix (`Gamepad for SAMSUNG`).",
        "- Expected host descriptor after live boot: `iManufacturer=SAMSUNG`, `iProduct=A90 Linux ARM`, `iSerial=A90NATIVE001`.",
        "",
        "## Command Scope",
        "",
        "- No USB control-surface behavior change. Inherits V2313-V2315 (`usb status`, `usb mass-storage add/remove/expose`) and V2316 serial redaction/userspace configfs identity.",
        "- Keeps `idVendor=0x04e8` and `idProduct=0x6861` for host transport compatibility.",
        "",
        "## Helper Flags",
        "",
        *helper_flag_lines,
        "",
        "## Safety Scope",
        "",
        "This source build performed host-side build work only. It changes only one fixed-length kernel rodata product literal and the native-init run/build identity. It does not change command behavior, USB VID/PID, partitions, adb-over-ffs, HID, BadUSB, Wi-Fi, kernel code flow, or any forbidden subsystem.",
        "",
        "## Required Device Step",
        "",
        "- Boot-only flash through `native_init_flash.py`, pinned SHA, auto-rollback to `v2237` on any failure.",
        "- `version` / `status` / `selftest fail=0`.",
        "- `usb status`: `control.ok=1`, configfs strings still show V2316 userspace identity.",
        "- Host descriptor validation: `iManufacturer=SAMSUNG`, `iProduct=A90 Linux ARM`, `iSerial=A90NATIVE001`.",
        "- USB persona smoke: `usb mass-storage expose` then `remove`; confirm serial control returns and NCM+ACM remain present.",
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
    patch_mkbootimg_tools(base)

    original_render_report = render_report

    def render_with_patch_info(manifest: dict[str, object]) -> str:
        if "usb_product_rodata_patch" not in manifest:
            if LAST_PATCH_INFO is None:
                raise RuntimeError("product rodata patch info missing before report render")
            manifest["usb_product_rodata_patch"] = LAST_PATCH_INFO
        return original_render_report(manifest, helper_flags)

    base.render_report = render_with_patch_info
    rc = base.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    patch_info = {
        **USB_PRODUCT_RODATA_PATCH,
        "patched_kernel_sha256": sha256(PATCHED_KERNEL),
    }
    manifest["candidate_tag"] = "v2317-usb-product-rodata"
    manifest["parent_baseline"] = "v2316-usb-linux-identity"
    manifest["rollback_baseline"] = "v2237-supplicant-terminate-poll"
    manifest["helper_flags"] = list(helper_flags)
    manifest["usb_product_rodata_patch"] = patch_info
    manifest["promotion_intent"] = "product-only-host-descriptor-validation"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, helper_flags), encoding="utf-8")
    promotion_path = OUT_DIR / "promotion-candidate.json"
    promotion_path.write_text(json.dumps({
        "candidate_tag": "v2317-usb-product-rodata",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest["helper_sha256"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "product_rodata_patch": patch_info,
        "note": "V2317 tests the product-only kernel rodata patch: host iProduct should become A90 Linux ARM while manufacturer remains SAMSUNG.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
