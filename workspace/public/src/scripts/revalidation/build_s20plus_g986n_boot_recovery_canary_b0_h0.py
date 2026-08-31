#!/usr/bin/env python3
"""Build a boot-only S20+ carrier for the recovery ADB canary ramdisk.

The resulting AP contains only ``boot.img.lz4``.  It lets a later reviewed
ordinary boot-only F1 test the recovery init/ADB/marker closure without reading
or writing the recovery partition.  The rollback is the exact known-good
resident Magisk boot already demonstrated on this target.  This builder is H0
only and contains no device transport.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import tempfile
from typing import Any


_RECOVERY_BUILDER_PATH = Path(__file__).resolve().with_name(
    "build_s20plus_g986n_recovery_adb_canary_h0.py"
)
_RECOVERY_BUILDER_SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_recovery_adb_canary_h0_bound", _RECOVERY_BUILDER_PATH
)
if _RECOVERY_BUILDER_SPEC is None or _RECOVERY_BUILDER_SPEC.loader is None:
    raise RuntimeError("T0 recovery builder cannot be loaded")
recovery_builder = importlib.util.module_from_spec(_RECOVERY_BUILDER_SPEC)
_RECOVERY_BUILDER_SPEC.loader.exec_module(recovery_builder)


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_boot_recovery_canary_b0_build_v1"
VERDICT = "PASS_S20PLUS_G986N_BOOT_RECOVERY_CANARY_B0_HOST_BUILT_REVIEW_PENDING"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

BASE_BOOT = ROOT / (
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/"
    "extracted/boot.img"
)
BASE_BOOT_SIZE = 67_108_864
BASE_BOOT_SHA256 = "29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab"

RECOVERY_CANARY = ROOT / (
    "workspace/private/outputs/s20plus_g986n/recovery_adb_canary_t0_v1/"
    "candidate/recovery.img"
)
RECOVERY_CANARY_SIZE = 82_694_144
RECOVERY_CANARY_SHA256 = (
    "e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b"
)
RECOVERY_CANARY_MANIFEST = ROOT / (
    "workspace/private/outputs/s20plus_g986n/recovery_adb_canary_t0_v1/"
    "manifest.json"
)
RECOVERY_CANARY_MANIFEST_SIZE = 5_459
RECOVERY_CANARY_MANIFEST_SHA256 = (
    "7c693b4e2e13efa912b5de00a95bbd41bb1651913427461e756225243381e1e3"
)

RESIDENT_ROOT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/candidate"
)
RESIDENT_BOOT = RESIDENT_ROOT / "boot.img"
RESIDENT_BOOT_SIZE = 67_108_864
RESIDENT_BOOT_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)
RESIDENT_BOOT_LZ4 = RESIDENT_ROOT / "boot.img.lz4"
RESIDENT_BOOT_LZ4_SIZE = 25_833_304
RESIDENT_BOOT_LZ4_SHA256 = (
    "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
)
RESIDENT_AP = RESIDENT_ROOT / "AP.tar.md5"
RESIDENT_AP_SIZE = 25_835_561
RESIDENT_AP_SHA256 = (
    "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
)
RESIDENT_AP_MD5 = "0a9fc01c43edc5440bf7ae19a9f4277b"

MAGISKBOOT = recovery_builder.MAGISKBOOT
MAGISKBOOT_SIZE = recovery_builder.MAGISKBOOT_SIZE
MAGISKBOOT_SHA256 = recovery_builder.MAGISKBOOT_SHA256
LZ4 = recovery_builder.LZ4
LZ4_SIZE = recovery_builder.LZ4_SIZE
LZ4_SHA256 = recovery_builder.LZ4_SHA256
AVBTOOL = recovery_builder.AVBTOOL
AVBTOOL_SIZE = recovery_builder.AVBTOOL_SIZE
AVBTOOL_SHA256 = recovery_builder.AVBTOOL_SHA256

RECOVERY_BUILDER_SOURCE = Path(recovery_builder.__file__).resolve()
RECOVERY_BUILDER_SOURCE_SIZE = 25_007
RECOVERY_BUILDER_SOURCE_SHA256 = (
    "811b2f80db822689d716c0de400cea22440af3069d7ea20945ddf0b36908c118"
)

DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/boot_recovery_canary_b0_v1"
)
AP_MEMBER = "boot.img.lz4"
MARKER_PATH = "/init.s20plus_g986n_recovery_adb_canary"
MARKER_SIZE = 159
MARKER_SHA256 = "5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0"

BASE_COMPONENTS = {
    "header": {
        "size": 373,
        "sha256": "1f948cfa15174ab850d66c2600654aacece5f7c2a5cd871f1b30db153d3baff3",
    },
    "kernel": {
        "size": 51_959_820,
        "sha256": "127d0f43de5e5e5ce5eee9e496b9593cf6ce7f0ce97581ad483e8f76feeb31ca",
    },
    "ramdisk.cpio": {
        "size": 1_565_952,
        "sha256": "42432b5d43303497e2953df21661b69ba132b8b748e30f255568d626bcc06990",
    },
    "dtb": {
        "size": 1_580_275,
        "sha256": "09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883",
    },
}
RECOVERY_CANARY_COMPONENTS = {
    "header": BASE_COMPONENTS["header"],
    "kernel": BASE_COMPONENTS["kernel"],
    "ramdisk.cpio": {
        "size": 24_184_404,
        "sha256": "ba9897b2f9e4fadb1aed1d6014f4a7f58c44d625097fb73b4ee6ddfa5935eecd",
    },
    "recovery_dtbo": {
        "size": 1_034_509,
        "sha256": "11e0da1564c1e2bbbccfa13f41ceaa105135586a443646980baa421b00137455",
    },
    "dtb": BASE_COMPONENTS["dtb"],
}
RECOVERY_INIT_RECEIPTS = {
    "system/etc/init/hw/init.rc": {
        "size": 6_427,
        "sha256": "b481ca09497cd1af76c5f8508c5b49f3af936c1edd727aa6359ed4de3058fea0",
    },
    "init.recovery.samsung.rc": {
        "size": 206,
        "sha256": "aec01202cae2831e7166160b7ecd8a04604cc28ee7b5e74c968d5e8f195c74aa",
    },
    "prop.default": {
        "size": 18_400,
        "sha256": "add76de663957054433e94bff4c808dc6a0e0a087d0c845582f3018ca3a84879",
    },
    "init.s20plus_g986n_recovery_adb_canary": {
        "size": MARKER_SIZE,
        "sha256": MARKER_SHA256,
    },
}
RECOVERY_INIT_RC = "system/etc/init/hw/init.rc"
RECOVERY_SERVICE_STANZA = b"service recovery /system/bin/recovery\n"
DISABLED_RECOVERY_SERVICE_STANZA = (
    b"service recovery /system/bin/recovery\n    disabled\n"
)


class BuildError(RuntimeError):
    """A closed boot-carrier build invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def receipt(path: Path) -> dict[str, Any]:
    return {"size": path.stat().st_size, "sha256": sha256_file(path)}


def require_direct_file(path: Path, size: int, digest: str, label: str) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise BuildError(f"{label} is absent") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BuildError(f"{label} is not a direct single-link regular file")
    if metadata.st_size != size or sha256_file(path) != digest:
        raise BuildError(f"{label} identity changed")
    if metadata.st_mode & 0o022:
        raise BuildError(f"{label} is group/world writable")


def require_tracked_source(path: Path, size: int, digest: str, label: str) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BuildError(f"{label} is not a direct tracked source")
    if metadata.st_size != size or sha256_file(path) != digest:
        raise BuildError(f"{label} source identity changed")


def unpack_image(
    image: Path, directory: Path, *, recovery_dtbo: bool
) -> dict[str, dict[str, Any]]:
    directory.mkdir(mode=0o700)
    output = recovery_builder.run_command(
        [MAGISKBOOT, "unpack", "-h", image], cwd=directory
    )
    required = (
        b"HEADER_VER      [2]",
        b"NAME            [SRPSK18B008]",
        b"RAMDISK_FMT     [gzip]",
        b"SAMSUNG_SEANDROID",
        b"VBMETA",
    )
    if any(token not in output for token in required):
        raise BuildError("boot image header closure changed")
    names = ["header", "kernel", "ramdisk.cpio", "dtb"]
    if recovery_dtbo:
        names.insert(3, "recovery_dtbo")
    actual = sorted(path.name for path in directory.iterdir())
    if actual != sorted(names):
        raise BuildError(f"unpacked component set changed: {actual}")
    return {name: receipt(directory / name) for name in names}


def copy_file(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise BuildError("output collision")
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, 8 * 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())


def validate_recovery_init_carrier(cpio: Path, root: Path) -> dict[str, Any]:
    listing = recovery_builder.cpio_listing(cpio, root)
    expected_modes = {
        "system/etc/init/hw/init.rc": "-rw-r--r--",
        "init.recovery.samsung.rc": "-rwxr-x---",
        "prop.default": "-rw-r--r--",
        "init.s20plus_g986n_recovery_adb_canary": "-r--r--r--",
    }
    for name, mode in expected_modes.items():
        item = listing.get(name)
        if (
            item is None
            or item["mode"] != mode
            or item["uid"] != 0
            or item["gid"] != 0
        ):
            raise BuildError(f"recovery init CPIO metadata changed for {name}")
    tree = root / "recovery-init-tree"
    recovery_builder.extract_cpio_tree(cpio, tree)
    receipts: dict[str, Any] = {}
    for name, expected in RECOVERY_INIT_RECEIPTS.items():
        path = tree / name
        if path.is_symlink() or not path.is_file() or receipt(path) != expected:
            raise BuildError(f"recovery init carrier file changed: {name}")
        receipts[name] = dict(expected)
    init_rc = (tree / "system/etc/init/hw/init.rc").read_bytes()
    for token, count in (
        (b"on boot\n", 2),
        (b"    class_start default\n", 1),
        (b"service recovery /system/bin/recovery\n", 1),
        (
            b"service adbd /system/bin/adbd --root_seclabel=u:r:su:s0 --device_banner=recovery\n",
            1,
        ),
        (b"on property:sys.usb.config=adb\n    start adbd\n", 1),
    ):
        if init_rc.count(token) != count:
            raise BuildError("recovery init service grammar changed")
    samsung_rc = (tree / "init.recovery.samsung.rc").read_bytes()
    if not samsung_rc.endswith(recovery_builder.RC_APPEND):
        raise BuildError("recovery canary ADB boot trigger changed")
    prop = (tree / "prop.default").read_bytes()
    for token, count in (
        (b"ro.secure=0\n", 1),
        (b"ro.adb.secure=0\n", 2),
        (b"ro.debuggable=1\n", 1),
    ):
        if prop.count(token) != count:
            raise BuildError("recovery canary property closure changed")
    marker = (tree / "init.s20plus_g986n_recovery_adb_canary").read_bytes()
    if marker != recovery_builder.MARKER:
        raise BuildError("recovery canary marker bytes changed")
    return {
        "files": receipts,
        "unconditional_boot_class_start": True,
        "default_class_recovery_service": True,
        "recovery_adbd_banner": "recovery",
        "adb_boot_trigger": True,
        "runtime_from_boot_partition": "UNKNOWN",
    }


def disable_automatic_recovery_service(cpio: Path, root: Path) -> dict[str, Any]:
    before_listing = recovery_builder.cpio_listing(cpio, root)
    before_tree_path = root / "carrier-before-tree"
    recovery_builder.extract_cpio_tree(cpio, before_tree_path)
    before_tree = recovery_builder.tree_manifest(before_tree_path)
    init_path = before_tree_path / RECOVERY_INIT_RC
    source = init_path.read_bytes()
    if (
        hashlib.sha256(source).hexdigest()
        != RECOVERY_INIT_RECEIPTS[RECOVERY_INIT_RC]["sha256"]
        or source.count(RECOVERY_SERVICE_STANZA) != 1
        or DISABLED_RECOVERY_SERVICE_STANZA in source
    ):
        raise BuildError("source recovery service stanza changed")
    patched = source.replace(
        RECOVERY_SERVICE_STANZA, DISABLED_RECOVERY_SERVICE_STANZA
    )
    patch_root = root / "carrier-patch"
    patch_root.mkdir(mode=0o700)
    patched_path = patch_root / "init.rc"
    patched_path.write_bytes(patched)
    recovery_builder.add_cpio_file(
        cpio, RECOVERY_INIT_RC, 0o644, patched_path, root
    )
    after_listing = recovery_builder.cpio_listing(cpio, root)
    after_tree_path = root / "carrier-after-tree"
    recovery_builder.extract_cpio_tree(cpio, after_tree_path)
    after_tree = recovery_builder.tree_manifest(after_tree_path)
    changed = sorted(
        name
        for name in set(before_tree) & set(after_tree)
        if before_tree[name] != after_tree[name]
    )
    listing_changed = sorted(
        name
        for name in set(before_listing) & set(after_listing)
        if before_listing[name] != after_listing[name]
    )
    before_init_listing = before_listing.get(RECOVERY_INIT_RC, {})
    after_init_listing = after_listing.get(RECOVERY_INIT_RC, {})
    if (
        set(before_tree) != set(after_tree)
        or changed != [RECOVERY_INIT_RC]
        or set(before_listing) != set(after_listing)
        or listing_changed not in ([], [RECOVERY_INIT_RC])
        or any(
            before_init_listing.get(key) != after_init_listing.get(key)
            for key in ("mode", "uid", "gid", "device")
        )
        or (after_tree_path / RECOVERY_INIT_RC).read_bytes() != patched
    ):
        raise BuildError("boot carrier safety delta is not one content-only change")
    for name in RECOVERY_INIT_RECEIPTS:
        if name == RECOVERY_INIT_RC:
            continue
        if before_tree[name] != after_tree[name]:
            raise BuildError(f"boot carrier changed protected recovery entry {name}")
    if patched.count(DISABLED_RECOVERY_SERVICE_STANZA) != 1:
        raise BuildError("recovery service was not disabled exactly once")
    return {
        "changed_entries": [RECOVERY_INIT_RC],
        "added_entries": [],
        "removed_entries": [],
        "metadata_changes": [],
        "source_init_rc": RECOVERY_INIT_RECEIPTS[RECOVERY_INIT_RC],
        "carrier_init_rc": {
            "size": len(patched),
            "sha256": hashlib.sha256(patched).hexdigest(),
        },
        "automatic_recovery_service_started": False,
        "recovery_service_disabled": True,
        "adbd_trigger_unchanged": True,
        "marker_unchanged": True,
        "ramdisk_cpio": receipt(cpio),
    }


def replace_file(source: Path, destination: Path) -> None:
    metadata = destination.lstat()
    if destination.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BuildError("ramdisk replacement target is not direct")
    with source.open("rb") as reader, destination.open("wb") as writer:
        shutil.copyfileobj(reader, writer, 8 * 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())


def write_boot_ap(frame: Path, output: Path) -> dict[str, Any]:
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            member = tarfile.TarInfo(AP_MEMBER)
            member.size = frame.stat().st_size
            member.mode = 0o644
            member.uid = member.gid = member.mtime = 0
            member.uname = member.gname = ""
            with frame.open("rb") as source:
                archive.addfile(member, source)
        handle.flush()
        os.fsync(handle.fileno())
    md5 = hashlib.md5()
    with output.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            md5.update(block)
    tar_md5 = md5.hexdigest()
    trailer = f"{tar_md5}  AP.tar\n".encode("ascii")
    with output.open("ab") as handle:
        handle.write(trailer)
        handle.flush()
        os.fsync(handle.fileno())
    with tarfile.open(output, "r:") as archive:
        members = archive.getmembers()
    if (
        len(members) != 1
        or members[0].name != AP_MEMBER
        or not members[0].isreg()
        or members[0].size != frame.stat().st_size
        or members[0].mode != 0o644
        or members[0].uid != 0
        or members[0].gid != 0
        or members[0].mtime != 0
    ):
        raise BuildError("boot-only AP membership or metadata changed")
    return {"members": [AP_MEMBER], "tar_md5": tar_md5, **receipt(output)}


def validate_boot_ap(
    path: Path,
    *,
    size: int,
    digest: str,
    member_size: int,
    member_digest: str,
    tar_md5: str,
    label: str,
) -> dict[str, Any]:
    require_direct_file(path, size, digest, label)
    data = path.read_bytes()
    trailer = f"{tar_md5}  AP.tar\n".encode("ascii")
    if not data.endswith(trailer) or hashlib.md5(data[: -len(trailer)]).hexdigest() != tar_md5:
        raise BuildError(f"{label} Odin MD5 changed")
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        if len(members) != 1 or members[0].name != AP_MEMBER or not members[0].isreg():
            raise BuildError(f"{label} is not boot-only")
        extracted = archive.extractfile(members[0])
        if extracted is None:
            raise BuildError(f"{label} member is unreadable")
        member = extracted.read(member_size + 1)
    if len(member) != member_size or hashlib.sha256(member).hexdigest() != member_digest:
        raise BuildError(f"{label} member identity changed")
    return {
        "members": [AP_MEMBER],
        "tar_md5": tar_md5,
        "member": {"size": member_size, "sha256": member_digest},
        **receipt(path),
    }


def verify_avb(image: Path, directory: Path, *, stock: bool) -> dict[str, Any]:
    directory.mkdir(mode=0o700)
    local = directory / "boot.img"
    copy_file(image, local)
    output = recovery_builder.run_command(
        [sys.executable, AVBTOOL, "verify_image", "--image", "boot.img"],
        cwd=directory,
        expected=(0,) if stock else (1,),
    )
    signature = b"Successfully verified footer and SHA256_RSA4096 vbmeta struct"
    boot_hash = b"Successfully verified sha256 hash of" in output
    mismatch = b"does not match digest in descriptor" in output
    if signature not in output or (stock and (not boot_hash or mismatch)) or (
        not stock and (boot_hash or not mismatch)
    ):
        raise BuildError("boot AVB verification class changed")
    return {
        "embedded_vbmeta_signature_verified": True,
        "boot_hash_descriptor_verified": boot_hash,
        "boot_hash_descriptor_mismatch": mismatch,
    }


def validate_inputs() -> dict[str, Any]:
    require_direct_file(BASE_BOOT, BASE_BOOT_SIZE, BASE_BOOT_SHA256, "stock boot")
    require_direct_file(
        RECOVERY_CANARY,
        RECOVERY_CANARY_SIZE,
        RECOVERY_CANARY_SHA256,
        "T0 recovery canary",
    )
    require_direct_file(
        RECOVERY_CANARY_MANIFEST,
        RECOVERY_CANARY_MANIFEST_SIZE,
        RECOVERY_CANARY_MANIFEST_SHA256,
        "T0 recovery manifest",
    )
    require_direct_file(
        RESIDENT_BOOT,
        RESIDENT_BOOT_SIZE,
        RESIDENT_BOOT_SHA256,
        "resident rollback boot",
    )
    require_direct_file(
        RESIDENT_BOOT_LZ4,
        RESIDENT_BOOT_LZ4_SIZE,
        RESIDENT_BOOT_LZ4_SHA256,
        "resident rollback boot LZ4",
    )
    resident_ap = validate_boot_ap(
        RESIDENT_AP,
        size=RESIDENT_AP_SIZE,
        digest=RESIDENT_AP_SHA256,
        member_size=RESIDENT_BOOT_LZ4_SIZE,
        member_digest=RESIDENT_BOOT_LZ4_SHA256,
        tar_md5=RESIDENT_AP_MD5,
        label="resident rollback AP",
    )
    require_direct_file(MAGISKBOOT, MAGISKBOOT_SIZE, MAGISKBOOT_SHA256, "magiskboot")
    require_direct_file(LZ4, LZ4_SIZE, LZ4_SHA256, "lz4")
    require_direct_file(AVBTOOL, AVBTOOL_SIZE, AVBTOOL_SHA256, "avbtool")
    require_tracked_source(
        RECOVERY_BUILDER_SOURCE,
        RECOVERY_BUILDER_SOURCE_SIZE,
        RECOVERY_BUILDER_SOURCE_SHA256,
        "T0 recovery builder",
    )
    return {
        "stock_boot": receipt(BASE_BOOT),
        "recovery_canary": receipt(RECOVERY_CANARY),
        "recovery_canary_manifest": receipt(RECOVERY_CANARY_MANIFEST),
        "resident_rollback_boot": receipt(RESIDENT_BOOT),
        "resident_rollback_boot_lz4": receipt(RESIDENT_BOOT_LZ4),
        "resident_rollback_ap": resident_ap,
        "magiskboot": receipt(MAGISKBOOT),
        "lz4": receipt(LZ4),
        "avbtool": receipt(AVBTOOL),
        "recovery_builder_source": receipt(RECOVERY_BUILDER_SOURCE),
    }


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    inputs = validate_inputs()
    if output.exists() or output.is_symlink():
        raise BuildError("output directory already exists")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="s20plus-boot-recovery-canary-b0-", dir=output.parent
    ) as temporary:
        root = Path(temporary)
        payload = root / "payload"
        candidate_dir = payload / "candidate"
        rollback_dir = payload / "rollback"
        candidate_dir.mkdir(mode=0o700, parents=True)
        rollback_dir.mkdir(mode=0o700)

        boot_unpack = root / "boot-unpack"
        boot_components = unpack_image(BASE_BOOT, boot_unpack, recovery_dtbo=False)
        if boot_components != BASE_COMPONENTS:
            raise BuildError("stock boot component closure changed")

        recovery_unpack = root / "recovery-unpack"
        recovery_components = unpack_image(
            RECOVERY_CANARY, recovery_unpack, recovery_dtbo=True
        )
        if recovery_components != RECOVERY_CANARY_COMPONENTS:
            raise BuildError("T0 recovery canary component closure changed")
        for name in ("header", "kernel", "dtb"):
            if recovery_components[name] != boot_components[name]:
                raise BuildError(f"boot/recovery common component differs: {name}")
        recovery_init = validate_recovery_init_carrier(
            recovery_unpack / "ramdisk.cpio", root
        )

        replace_file(recovery_unpack / "ramdisk.cpio", boot_unpack / "ramdisk.cpio")
        safety_delta = disable_automatic_recovery_service(
            boot_unpack / "ramdisk.cpio", root
        )
        candidate_image = candidate_dir / "boot.img"
        recovery_builder.run_command(
            [MAGISKBOOT, "repack", BASE_BOOT, candidate_image], cwd=boot_unpack
        )
        if candidate_image.stat().st_size != BASE_BOOT_SIZE:
            raise BuildError("boot carrier partition size changed")

        candidate_unpack = root / "candidate-unpack"
        candidate_components = unpack_image(
            candidate_image, candidate_unpack, recovery_dtbo=False
        )
        for name in ("header", "kernel", "dtb"):
            if candidate_components[name] != BASE_COMPONENTS[name]:
                raise BuildError(f"boot carrier changed preserved component {name}")
        if candidate_components["ramdisk.cpio"] != safety_delta["ramdisk_cpio"]:
            raise BuildError("boot carrier did not preserve the safety-patched ramdisk")

        stock_avb = verify_avb(BASE_BOOT, root / "stock-avb", stock=True)
        candidate_avb = verify_avb(
            candidate_image, root / "candidate-avb", stock=False
        )

        candidate_lz4 = candidate_dir / AP_MEMBER
        recovery_builder.lz4_roundtrip(
            candidate_image, candidate_lz4, root / "candidate-roundtrip.img"
        )
        candidate_ap = candidate_dir / "AP.tar.md5"
        candidate_ap_result = write_boot_ap(candidate_lz4, candidate_ap)

        rollback_boot = rollback_dir / "boot.img"
        rollback_lz4 = rollback_dir / AP_MEMBER
        rollback_ap = rollback_dir / "AP.tar.md5"
        copy_file(RESIDENT_BOOT, rollback_boot)
        copy_file(RESIDENT_BOOT_LZ4, rollback_lz4)
        copy_file(RESIDENT_AP, rollback_ap)
        rollback_boot.chmod(0o400)
        rollback_lz4.chmod(0o400)
        rollback_ap.chmod(0o400)
        rollback_ap_result = validate_boot_ap(
            rollback_ap,
            size=RESIDENT_AP_SIZE,
            digest=RESIDENT_AP_SHA256,
            member_size=RESIDENT_BOOT_LZ4_SIZE,
            member_digest=RESIDENT_BOOT_LZ4_SHA256,
            tar_md5=RESIDENT_AP_MD5,
            label="copied resident rollback AP",
        )

        manifest = {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "tier": "H0",
            "review_state": "REVIEW_PENDING",
            "live_authority": False,
            "target": TARGET,
            "inputs": inputs,
            "components": {
                "stock_boot": boot_components,
                "recovery_canary": recovery_components,
                "boot_carrier": candidate_components,
                "exact_common": ["header", "kernel", "dtb"],
                "carrier_ramdisk_source": (
                    "exact T0 recovery canary ramdisk plus one disabled recovery service"
                ),
                "recovery_dtbo_in_boot_carrier": False,
            },
            "marker": {
                "path": MARKER_PATH,
                "size": MARKER_SIZE,
                "sha256": MARKER_SHA256,
                "mode": "0444",
            },
            "source_recovery_init": recovery_init,
            "boot_carrier_safety_delta": safety_delta,
            "avb": {
                "stock_boot": stock_avb,
                "boot_carrier": candidate_avb,
                "runtime_acceptance": "UNKNOWN_REQUIRES_REVIEWED_ATTENDED_BOOT_ONLY_F1",
            },
            "candidate": {
                "boot_img": receipt(candidate_image),
                "boot_img_lz4": receipt(candidate_lz4),
                "ap_tar_md5": candidate_ap_result,
            },
            "rollback": {
                "boot_img": receipt(rollback_boot),
                "boot_img_lz4": receipt(rollback_lz4),
                "ap_tar_md5": rollback_ap_result,
                "role": "known-good-resident-magisk-boot",
                "previous_live_health_recorded": True,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "boot_only_candidate": True,
                "boot_only_rollback": True,
                "recovery_partition_read": False,
                "recovery_partition_write": False,
                "recovery_partition_transfer": False,
                "other_partition_transfer": False,
                "vbmeta_payload": False,
                "odin_commands": 0,
                "adb_commands": 0,
                "su_commands": 0,
                "live_authority": False,
                "independent_review_complete": False,
            },
        }
        manifest_path = payload / "manifest.json"
        with manifest_path.open("xb") as handle:
            handle.write(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
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
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    result = build(arguments.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
