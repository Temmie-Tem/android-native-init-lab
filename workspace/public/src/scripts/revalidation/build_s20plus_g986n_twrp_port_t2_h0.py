#!/usr/bin/env python3
"""Build a host-only IYC2-stock-substrate, sanitized y2q TWRP T2 image.

The exact AstroForge V2 image is a binary donor only.  This builder takes only
its ramdisk, neutralizes automatic persistent mutations and broad partition UI
flags, then repacks that ramdisk with the exact G986N IYC2 stock recovery
header, kernel, DTB, and recovery DTBO.  It has no device transport and grants
no live recovery-write authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_s20plus_g986n_recovery_adb_canary_h0 as t0  # noqa: E402


ROOT = t0.ROOT
T0_BUILDER = SCRIPT_DIR / "build_s20plus_g986n_recovery_adb_canary_h0.py"
T0_BUILDER_SHA256 = (
    "811b2f80db822689d716c0de400cea22440af3069d7ea20945ddf0b36908c118"
)
DONOR = ROOT / (
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/"
    "twrp_donors/AstroForge-V2/Twrp_3.7.1_12-AstroForge-V2_y2q.img"
)
DONOR_SIZE = 82_694_144
DONOR_SHA256 = (
    "41d922d2c812256703981c3ce24ea467888d567a7e6c708670632af535787b0d"
)
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/twrp_port_t2_v1"
)

SCHEMA = "s20plus_g986n_twrp_port_t2_build_v1"
VERDICT = "PASS_S20PLUS_G986N_TWRP_PORT_T2_HOST_BUILT_REVIEW_PENDING"
TARGET = dict(t0.TARGET)
TWRP_VERSION = "3.7.1_12-AstroForge_v2"
SOURCE_CLAIM = "BINARY_DONOR_PINNED_SOURCE_REPRODUCTION_UNPROVED"

DONOR_COMPONENTS = {
    "header": {
        "size": 410,
        "sha256": "757c9c645764e3c6aba1dc8e6838037956cbc40bb20dbef452bbe5767c43ab40",
    },
    "kernel": {
        "size": 52_721_688,
        "sha256": "aad5b5f7a182a650c31a40b64bc1748e17e5dc079a9c6055b683f7043796899f",
    },
    "ramdisk.cpio": {
        "size": 71_193_344,
        "sha256": "0a84bf889e04ec97c896daa6de8074ff3cffad8e8cb836fef0ccfd5a0353e07b",
    },
    "recovery_dtbo": {
        "size": 1_143_208,
        "sha256": "ea0b490c4a187d49b67d09aa3ad43328fb319c16323a67d76324dffef2a727e1",
    },
    "dtb": {
        "size": 1_418_018,
        "sha256": "de0b09c7388715b2513d06e185f07ca449080bdf7b3ce71bb2956f9046ca7898",
    },
}

QCOM_RC = "init.recovery.qcom.rc"
POST_HOOK = "system/bin/postrecoveryboot.sh"
REBOOT_HOOK = "system/bin/rebootsystem.sh"
TWRP_FLAGS = "system/etc/twrp.flags"
RECOVERY_FSTAB = "system/etc/recovery.fstab"
RECOVERY_BINARY = "system/bin/recovery"
TWRP_CLI = "system/bin/twrp"
USB_RC = "init.recovery.usb.rc"
PROP_DEFAULT = "prop.default"
MARKER_ENTRY = "init.s20plus_g986n_twrp_port_t2"

DONOR_ENTRY_SHA256 = {
    QCOM_RC: "6c6659eb98cbd4ea97c1af7ba062c72fa72ca7a54d0f94a35d7d4fc22516e240",
    POST_HOOK: "8a4ba36e4671354b942b01f749f3db2e4fa4e5a4875da6ad64bcf3b285a84eb0",
    REBOOT_HOOK: "3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07",
    TWRP_FLAGS: "817229bc30f98660436797ce63fc245c3d3196504a343a3731dae47d21ce39c4",
    RECOVERY_FSTAB: "2fa6cff75f313d64fe974e1c13c52ba8727bc72e2a5cb106cdf5ec90feedf22b",
    RECOVERY_BINARY: "fb95886f109412a583c65b83e1c2adfd4b120115f2507193a42d5ee8969ac89d",
    TWRP_CLI: "c6ee47bce884cdf63751c5424f3083d993f71ba1fe920e90691ecd6602c99ded",
    USB_RC: "bb0116ffe9a39996df210015bb38abf8607489e3dbaaf77c933ec5fd508ca507",
    PROP_DEFAULT: "f3a6cd5d84096de2fb75298ac964f1188b61c6932e0d3d7d840eede948ecb364",
}

POST_HOOK_INERT = (
    b"#!/system/bin/sh\n"
    b"# S20+ G986N T2: stock-recovery restoration files are left untouched.\n"
    b"exit 0\n"
)

SAFE_TWRP_FLAGS = b"""# S20+ G986N T2 lab-safe TWRP UI surface.
# /data and read-only logical partitions remain defined by recovery.fstab.
# Only boot image flash is exposed; recovery rollback stays host-bound.

/boot               emmc         /dev/block/bootdevice/by-name/boot              flags=backup=1;display="Boot";flashimg=1
/misc               emmc         /dev/block/bootdevice/by-name/misc
/cache              ext4         /dev/block/bootdevice/by-name/cache
/external_sd        auto         /dev/block/mmcblk0p1   /dev/block/mmcblk0        flags=display="Micro SD card";storage;removable
/usb-otg            auto         /dev/block/sdf1        /dev/block/sdf             flags=display="USB OTG";storage;removable
"""

SAFE_USB_RC = b"""# S20+ G986N T2 first-boot USB: ADB only.

on boot
    mount configfs none /config
    mkdir /config/usb_gadget/g1
    mkdir /config/usb_gadget/g1/strings/0x409 0770
    write /config/usb_gadget/g1/bcdUSB 0x0200
    write /config/usb_gadget/g1/strings/0x409/serialnumber ${ro.serialno}
    write /config/usb_gadget/g1/strings/0x409/manufacturer ${ro.product.manufacturer}
    write /config/usb_gadget/g1/strings/0x409/product ${ro.product.model}
    mkdir /config/usb_gadget/g1/functions/ffs.adb
    mkdir /config/usb_gadget/g1/configs/b.1 0770
    mkdir /config/usb_gadget/g1/configs/b.1/strings/0x409 0770
    write /config/usb_gadget/g1/configs/b.1/MaxPower 900
    mkdir /dev/usb-ffs 0775 shell system
    mkdir /dev/usb-ffs/adb 0770 shell system
    mount functionfs adb /dev/usb-ffs/adb uid=2000,gid=1000,rmode=0770,fmode=0660
    setprop sys.usb.controller ${ro.boot.usbcontroller}
    setprop sys.usb.configfs 1
    setprop sys.usb.config adb

on property:sys.usb.config=none
    write /config/usb_gadget/g1/UDC "none"
    stop adbd
    setprop sys.usb.ffs.ready 0
    setprop sys.usb.state ${sys.usb.config}

on property:sys.usb.config=mtp
    setprop sys.usb.config adb

on property:sys.usb.config=mtp,adb
    start adbd

on property:sys.usb.ffs.ready=1 && property:sys.usb.config=mtp,adb
    write /config/usb_gadget/g1/configs/b.1/strings/0x409/configuration "adb"
    rm /config/usb_gadget/g1/configs/b.1/f*
    write /config/usb_gadget/g1/idVendor 0x04E8
    write /config/usb_gadget/g1/idProduct 0x6860
    symlink /config/usb_gadget/g1/functions/ffs.adb /config/usb_gadget/g1/configs/b.1/f1
    write /config/usb_gadget/g1/UDC ${sys.usb.controller}
    setprop sys.usb.state ${sys.usb.config}

on property:sys.usb.config=adb
    start adbd

on property:sys.usb.ffs.ready=1 && property:sys.usb.config=adb
    write /config/usb_gadget/g1/configs/b.1/strings/0x409/configuration "adb"
    rm /config/usb_gadget/g1/configs/b.1/f*
    write /config/usb_gadget/g1/idVendor 0x04E8
    write /config/usb_gadget/g1/idProduct 0x6860
    symlink /config/usb_gadget/g1/functions/ffs.adb /config/usb_gadget/g1/configs/b.1/f1
    write /config/usb_gadget/g1/UDC ${sys.usb.controller}
    setprop sys.usb.state ${sys.usb.config}

on property:sys.usb.config=sideload
    setprop sys.usb.config adb

on property:sys.usb.config=fastboot
    setprop sys.usb.config adb
"""

MARKER = (
    b"S20PLUS_G986N_TWRP_PORT_T2_V1\n"
    b"target=SM-G986N/y2q/y2qksx/G986NKSS8IYC2\n"
    b"substrate=exact-stock-IYC2-header-kernel-dtb-recovery_dtbo\n"
    b"donor=Twrp_3.7.1_12-AstroForge-V2_y2q.img\n"
    b"postrecoveryboot=inert\n"
    b"efs_persist_automount=ro-noload-nosuid-nodev-noexec\n"
    b"crypto_service_autostart=disabled\n"
    b"usb_first_boot=adb-only\n"
    b"predecessor_t1_observed_usb_config=mtp,adb\n"
    b"source_reproduction=unproved\n"
    b"live_authority=false\n"
)

CHANGED_ENTRIES = (QCOM_RC, USB_RC, POST_HOOK, TWRP_FLAGS)
ADDED_ENTRIES = (MARKER_ENTRY,)
ENTRY_MODES = {
    QCOM_RC: "-rwxr-x---",
    USB_RC: "-rwxr-x---",
    POST_HOOK: "-rwxr-xr-x",
    TWRP_FLAGS: "-rw-r--r--",
    MARKER_ENTRY: "-r--r--r--",
}
FORBIDDEN_UI_TOKENS = (
    b"/modem",
    b"/recovery",
    b"/persist",
    b"/system_image",
    b"/vendor_image",
    b"/product_image",
    b"/odm_image",
    b"/efs",
    b"/sec_efs",
    b"/omr",
    b"/optics",
    b"/prism",
    b"/dtbo",
    b"/vbmeta",
    b"wipeingui",
)


BuildError = t0.BuildError


def replace_exact(data: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if data.count(old) != 1 or new in data:
        raise BuildError(f"{label} grammar changed")
    return data.replace(old, new)


def sanitize_qcom_rc(data: bytes) -> bytes:
    if hashlib.sha256(data).hexdigest() != DONOR_ENTRY_SHA256[QCOM_RC]:
        raise BuildError("donor qcom rc identity changed")
    replacements = (
        (
            b"    mount ext4 /dev/block/bootdevice/by-name/persist /mnt/vendor/persist rw\n",
            b"    mount ext4 /dev/block/bootdevice/by-name/persist /mnt/vendor/persist ro nosuid nodev noexec noload\n",
            "persist automount",
        ),
        (
            b"    mount ext4 /dev/block/bootdevice/by-name/efs /mnt/vendor/efs rw\n",
            b"    mount ext4 /dev/block/bootdevice/by-name/efs /mnt/vendor/efs ro nosuid nodev noexec noload\n",
            "EFS automount",
        ),
        (
            b"    mount vfat /dev/block/bootdevice/by-name/apnhlos /vendor/firmware_mnt ro\n",
            b"    mount vfat /dev/block/bootdevice/by-name/apnhlos /vendor/firmware_mnt ro nosuid nodev noexec\n",
            "firmware automount",
        ),
        (
            b"on post-fs-data\n    mkdir /data/vendor/keymaster\n\n",
            b"# T2 leaves /data/vendor/keymaster untouched during first boot.\n\n",
            "keymaster data directory",
        ),
        (
            b"on property:crypto.ready=1\n"
            b"    start keymaster-sb-4-0\n"
            b"    start spdaemon\n"
            b"    start sec_nvm\n\n",
            b"# T2 does not auto-start keymaster, spdaemon, or sec_nvm.\n\n",
            "crypto service autostart",
        ),
    )
    patched = data
    for old, new, label in replacements:
        patched = replace_exact(patched, old, new, label)
    forbidden = (
        b"/mnt/vendor/persist rw",
        b"/mnt/vendor/efs rw",
        b"mkdir /data/vendor/keymaster",
        b"start keymaster-sb-4-0",
        b"start spdaemon",
        b"start sec_nvm",
    )
    if any(token in patched for token in forbidden):
        raise BuildError("qcom rc retains an automatic persistent mutation")
    required = (
        b"/mnt/vendor/persist ro nosuid nodev noexec noload",
        b"/mnt/vendor/efs ro nosuid nodev noexec noload",
        b"/vendor/firmware_mnt ro nosuid nodev noexec",
        b"start health-hal-2-1",
    )
    if any(token not in patched for token in required):
        raise BuildError("qcom rc lost a required read-only/runtime path")
    return patched


def validate_safe_flags(data: bytes) -> None:
    if data != SAFE_TWRP_FLAGS:
        raise BuildError("safe TWRP flags changed")
    if data.count(b"flashimg=1") != 1 or b"/boot " not in data:
        raise BuildError("safe TWRP flags do not expose exactly boot flash")
    if any(token in data for token in FORBIDDEN_UI_TOKENS):
        raise BuildError("safe TWRP flags expose a forbidden UI surface")


def validate_safe_usb_rc(data: bytes) -> None:
    if data != SAFE_USB_RC:
        raise BuildError("safe USB rc changed")
    required = (
        b"mkdir /config/usb_gadget/g1/functions/ffs.adb",
        b"mount functionfs adb /dev/usb-ffs/adb",
        b"setprop sys.usb.config adb",
        b"start adbd",
        b"idVendor 0x04E8",
        b"idProduct 0x6860",
    )
    forbidden = (
        b"functions/ffs.mtp",
        b"functions/ffs.fastboot",
        b"mount functionfs mtp",
        b"mount functionfs fastboot",
        b"start fastbootd",
    )
    if any(token not in data for token in required):
        raise BuildError("safe USB rc lost required ADB-only behavior")
    if any(token in data for token in forbidden):
        raise BuildError("safe USB rc exposes a non-ADB function")


def unpack_donor(directory: Path) -> dict[str, Any]:
    directory.mkdir(mode=0o700)
    output = t0.run_command([t0.MAGISKBOOT, "unpack", "-h", DONOR], cwd=directory)
    required = (
        b"HEADER_VER      [2]",
        b"KERNEL_FMT      [gzip]",
        b"RAMDISK_FMT     [gzip]",
        b"OS_VERSION      [12.0.0]",
        b"buildvariant=eng",
        b"SAMSUNG_SEANDROID",
        b"VBMETA",
    )
    if any(token not in output for token in required):
        raise BuildError("donor image header shape changed")
    components = {name: t0.receipt(directory / name) for name in DONOR_COMPONENTS}
    if components != DONOR_COMPONENTS:
        raise BuildError("donor component closure changed")
    return components


def critical_receipts(tree: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for name, expected in DONOR_ENTRY_SHA256.items():
        path = tree / name
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"donor critical entry is absent: {name}")
        state = t0.receipt(path)
        if state["sha256"] != expected:
            raise BuildError(f"donor critical entry changed: {name}")
        result[name] = state
    recovery = (tree / RECOVERY_BINARY).read_bytes()
    if TWRP_VERSION.encode("ascii") not in recovery:
        raise BuildError("donor TWRP version string changed")
    return result


def prove_ramdisk_delta(
    donor_tree: dict[str, dict[str, Any]],
    port_tree: dict[str, dict[str, Any]],
    donor_listing: dict[str, dict[str, Any]],
    port_listing: dict[str, dict[str, Any]],
    patched_qcom: bytes,
) -> dict[str, Any]:
    if len(donor_tree) != 3_685:
        raise BuildError("donor ramdisk entry count changed")
    added = sorted(set(port_tree) - set(donor_tree))
    removed = sorted(set(donor_tree) - set(port_tree))
    changed = sorted(
        name
        for name in set(donor_tree) & set(port_tree)
        if donor_tree[name] != port_tree[name]
    )
    if added != list(ADDED_ENTRIES) or removed or changed != sorted(CHANGED_ENTRIES):
        raise BuildError(
            f"TWRP ramdisk delta changed: added={added} removed={removed} "
            f"changed={changed}"
        )

    listing_added = sorted(set(port_listing) - set(donor_listing))
    listing_removed = sorted(set(donor_listing) - set(port_listing))
    listing_changed = sorted(
        name
        for name in set(donor_listing) & set(port_listing)
        if donor_listing[name] != port_listing[name]
    )
    if (
        listing_added != list(ADDED_ENTRIES)
        or listing_removed
        or listing_changed != sorted(CHANGED_ENTRIES)
    ):
        raise BuildError("TWRP ramdisk metadata delta changed")
    for name, mode in ENTRY_MODES.items():
        item = port_listing.get(name)
        if item is None or item["mode"] != mode or item["uid"] != 0 or item["gid"] != 0:
            raise BuildError(f"TWRP port metadata changed for {name}")

    expected_content = {
        QCOM_RC: patched_qcom,
        USB_RC: SAFE_USB_RC,
        POST_HOOK: POST_HOOK_INERT,
        TWRP_FLAGS: SAFE_TWRP_FLAGS,
        MARKER_ENTRY: MARKER,
    }
    for name, data in expected_content.items():
        if port_tree[name].get("sha256") != hashlib.sha256(data).hexdigest():
            raise BuildError(f"TWRP port content changed for {name}")

    for name in (
        REBOOT_HOOK,
        RECOVERY_FSTAB,
        RECOVERY_BINARY,
        TWRP_CLI,
        PROP_DEFAULT,
    ):
        if port_tree[name] != donor_tree[name]:
            raise BuildError(f"TWRP port changed preserved donor entry {name}")
    return {
        "donor_entry_count": len(donor_tree),
        "port_entry_count": len(port_tree),
        "added_entries": added,
        "removed_entries": removed,
        "changed_entries": changed,
        "all_other_entries_byte_and_mode_identical": True,
    }


def validate_inputs() -> dict[str, Any]:
    t0.validate_inputs()
    if t0.sha256_file(T0_BUILDER) != T0_BUILDER_SHA256:
        raise BuildError("T0 utility closure changed")
    t0.require_direct_file(DONOR, DONOR_SIZE, DONOR_SHA256, "TWRP donor image")
    return {
        "stock_recovery": t0.receipt(t0.BASE_RECOVERY),
        "stock_recovery_lz4": t0.receipt(t0.BASE_RECOVERY_LZ4),
        "twrp_donor": t0.receipt(DONOR),
        "t0_builder": t0.receipt(T0_BUILDER),
        "magiskboot": t0.receipt(t0.MAGISKBOOT),
        "lz4": t0.receipt(t0.LZ4),
        "avbtool": t0.receipt(t0.AVBTOOL),
    }


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    inputs = validate_inputs()
    validate_safe_flags(SAFE_TWRP_FLAGS)
    validate_safe_usb_rc(SAFE_USB_RC)
    if output.exists() or output.is_symlink():
        raise BuildError("output directory already exists")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="s20plus-twrp-port-t2-", dir=output.parent
    ) as temporary:
        temporary_root = Path(temporary)
        payload = temporary_root / "payload"
        candidate_dir = payload / "candidate"
        rollback_dir = payload / "rollback"
        candidate_dir.mkdir(mode=0o700, parents=True)
        rollback_dir.mkdir(mode=0o700)

        stock_unpack = temporary_root / "stock-unpack"
        stock_components = t0.unpack_recovery(t0.BASE_RECOVERY, stock_unpack)
        if stock_components != t0.BASE_COMPONENTS:
            raise BuildError("stock recovery component closure changed")
        donor_unpack = temporary_root / "donor-unpack"
        donor_components = unpack_donor(donor_unpack)

        donor_ramdisk = donor_unpack / "ramdisk.cpio"
        donor_listing = t0.cpio_listing(donor_ramdisk, donor_unpack)
        donor_tree_dir = temporary_root / "donor-tree"
        t0.extract_cpio_tree(donor_ramdisk, donor_tree_dir)
        donor_tree = t0.tree_manifest(donor_tree_dir)
        donor_critical = critical_receipts(donor_tree_dir)

        patched_qcom = sanitize_qcom_rc((donor_tree_dir / QCOM_RC).read_bytes())
        patch_dir = temporary_root / "patch-inputs"
        patch_dir.mkdir(mode=0o700)
        patch_inputs = {
            QCOM_RC: (patched_qcom, 0o750),
            USB_RC: (SAFE_USB_RC, 0o750),
            POST_HOOK: (POST_HOOK_INERT, 0o755),
            TWRP_FLAGS: (SAFE_TWRP_FLAGS, 0o644),
            MARKER_ENTRY: (MARKER, 0o444),
        }
        patch_paths = {}
        for index, (name, (data, _mode)) in enumerate(patch_inputs.items()):
            path = patch_dir / f"{index:02d}.payload"
            path.write_bytes(data)
            patch_paths[name] = path

        port_ramdisk = stock_unpack / "ramdisk.cpio"
        port_ramdisk.unlink()
        t0.copy_file(donor_ramdisk, port_ramdisk)
        for name, (_data, mode) in patch_inputs.items():
            t0.add_cpio_file(port_ramdisk, name, mode, patch_paths[name], stock_unpack)

        port_listing = t0.cpio_listing(port_ramdisk, stock_unpack)
        port_tree_dir = temporary_root / "port-tree"
        t0.extract_cpio_tree(port_ramdisk, port_tree_dir)
        port_tree = t0.tree_manifest(port_tree_dir)
        delta = prove_ramdisk_delta(
            donor_tree,
            port_tree,
            donor_listing,
            port_listing,
            patched_qcom,
        )
        validate_safe_flags((port_tree_dir / TWRP_FLAGS).read_bytes())
        validate_safe_usb_rc((port_tree_dir / USB_RC).read_bytes())

        candidate_image = candidate_dir / "recovery.img"
        t0.run_command(
            [t0.MAGISKBOOT, "repack", t0.BASE_RECOVERY, candidate_image],
            cwd=stock_unpack,
        )
        if candidate_image.stat().st_size != t0.BASE_RECOVERY_SIZE:
            raise BuildError("TWRP port partition size changed")

        candidate_unpack = temporary_root / "candidate-unpack"
        candidate_components = t0.unpack_recovery(candidate_image, candidate_unpack)
        for name in ("header", "kernel", "dtb", "recovery_dtbo"):
            if candidate_components[name] != t0.BASE_COMPONENTS[name]:
                raise BuildError(f"TWRP port changed stock substrate {name}")
        if candidate_components["ramdisk.cpio"]["sha256"] != t0.sha256_file(port_ramdisk):
            raise BuildError("TWRP port ramdisk changed during image repack")

        candidate_avb = t0.verify_avb(
            candidate_image, temporary_root / "candidate-avb", False
        )
        stock_avb = t0.verify_avb(
            t0.BASE_RECOVERY, temporary_root / "stock-avb", True
        )

        candidate_lz4 = candidate_dir / "recovery.img.lz4"
        t0.lz4_roundtrip(
            candidate_image,
            candidate_lz4,
            temporary_root / "candidate-roundtrip.img",
        )
        candidate_ap = candidate_dir / "AP.tar.md5"
        candidate_ap_result = t0.write_recovery_ap(candidate_lz4, candidate_ap)

        rollback_image = rollback_dir / "recovery.img"
        rollback_lz4 = rollback_dir / "recovery.img.lz4"
        t0.copy_file(t0.BASE_RECOVERY, rollback_image)
        t0.copy_file(t0.BASE_RECOVERY_LZ4, rollback_lz4)
        t0.verify_existing_lz4(
            rollback_lz4,
            rollback_image,
            temporary_root / "rollback-roundtrip.img",
        )
        rollback_ap = rollback_dir / "AP.tar.md5"
        rollback_ap_result = t0.write_recovery_ap(rollback_lz4, rollback_ap)

        critical_port = {
            name: t0.receipt(port_tree_dir / name)
            for name in (
                QCOM_RC,
                POST_HOOK,
                REBOOT_HOOK,
                TWRP_FLAGS,
                RECOVERY_FSTAB,
                RECOVERY_BINARY,
                TWRP_CLI,
                USB_RC,
                PROP_DEFAULT,
                MARKER_ENTRY,
            )
        }
        manifest = {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "tier": "H0",
            "review_state": "REVIEW_PENDING",
            "live_authority": False,
            "target": TARGET,
            "twrp_version": TWRP_VERSION,
            "source_claim": SOURCE_CLAIM,
            "inputs": inputs,
            "donor_components": donor_components,
            "donor_critical_entries": donor_critical,
            "substrate": {
                "source": "exact G986NKSS8IYC2 stock recovery",
                "components": stock_components,
                "preserved_exact": ["header", "kernel", "dtb", "recovery_dtbo"],
                "donor_components_used": ["ramdisk.cpio"],
            },
            "port_components": candidate_components,
            "ramdisk": {
                **delta,
                "critical_port_entries": critical_port,
                "automatic_vendor_deletion": False,
                "automatic_data_keymaster_mkdir": False,
                "automatic_crypto_service_start": False,
                "efs_persist_automount": "ro,noload,nosuid,nodev,noexec",
                "usb_functions": ["adb"],
                "mtp_enabled": False,
                "fastbootd_enabled": False,
                "twrp_ui_flashimg_partitions": ["boot"],
                "rebootsystem_hook": {
                    "preserved": True,
                    "size": 89,
                    "sha256": DONOR_ENTRY_SHA256[REBOOT_HOOK],
                    "same_as_a90_bound_hook": True,
                    "s20plus_live_exception": False,
                },
            },
            "avb": {
                "stock": stock_avb,
                "candidate": candidate_avb,
                "candidate_runtime_acceptance": "UNKNOWN_REQUIRES_T2_FIRST_ATTEMPT",
            },
            "candidate": {
                "recovery_img": t0.receipt(candidate_image),
                "recovery_img_lz4": t0.receipt(candidate_lz4),
                "ap_tar_md5": candidate_ap_result,
            },
            "rollback": {
                "recovery_img": t0.receipt(rollback_image),
                "recovery_img_lz4": t0.receipt(rollback_lz4),
                "ap_tar_md5": rollback_ap_result,
                "exact_stock_bytes": True,
                "demonstrated_live_path": False,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "adb_commands": 0,
                "su_commands": 0,
                "reboot_commands": 0,
                "odin_commands": 0,
                "partition_transfers": 0,
                "vbmeta_payload": False,
                "vendor_write": False,
                "efs_write": False,
                "persist_write": False,
                "data_write": False,
                "misc_write_during_build": False,
                "live_flash_authorized": False,
                "policy_amendment_complete": False,
                "independent_review_complete": False,
                "t0_runtime_passed": False,
            },
        }
        manifest_path = payload / "manifest.json"
        with manifest_path.open("xb") as handle:
            handle.write(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )
            handle.flush()
            os.fsync(handle.fileno())
        for path in payload.rglob("*"):
            if path.is_file():
                path.chmod(0o400)
        os.rename(payload, output)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="absent private output directory; defaults to the fixed S20+ T2 path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve(strict=False)
    result = build(output)
    print(result["verdict"])
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
