#!/usr/bin/env python3
"""Bind the FYG8 Max77705 writable baseline and the custom-module closure.

This is a host-only authority/contract helper.  Its baseline mode proves what
the pinned stock sources and modules expose.  The custom-source validator is a
future packaging prerequisite; declaring this contract does not claim that a
custom module has already been built or qualified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from s22plus_fyg8_f2fs_module_corpus import FILE_TYPE_REGULAR, F2FSReader


SCHEMA = "s22plus_fyg8_max77705_custom_surface_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
KERNEL_ROOT = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/msm-kernel"
)
MODULE_ROOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
VENDOR_DLKM_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "order-authority-20260811-01/vendor_dlkm.img"
)
LZ4_TOOL = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")
DUMP_F2FS = Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
FIRST_STAGE_INVENTORY = Path("docs/module-map/s22plus-fyg8/inventory.tsv")
VENDOR_DLKM_INVENTORY = Path("docs/module-map/s22plus-fyg8-super/inventory.tsv")
VENDOR_DLKM_MANIFEST = Path("docs/module-map/s22plus-fyg8-super/manifest.json")
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-surface-authority-20260811-01.json"
)

VENDOR_RAMDISK_IDENTITY = (
    21_813_545,
    "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193",
)
VENDOR_RAMDISK_CPIO_IDENTITY = (
    63_974_144,
    "a96c362103eeab52fd639fd1bfc06d5f9a30972a18d8086c26d20a86a0309afd",
)
VENDOR_DLKM_IDENTITY = (
    57_610_240,
    "e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26",
)
LZ4_IDENTITY = (
    115_032,
    "4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0",
)
DUMP_F2FS_SHA256 = "66db38ca0ea8239cab0c335e142ee34751824352eaa494b3654fa7d663b86669"
FIRST_STAGE_INVENTORY_SHA256 = "35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b"
VENDOR_DLKM_INVENTORY_SHA256 = "5ad69e151efbe48ba0348608120da3001f9e11d481b13a498177e080771c6d37"
VENDOR_DLKM_MANIFEST_SHA256 = "c23077120499012db4d492d5b494c1f69274486e5bbf7a15ec3f192dbdd71092"
EXPECTED_FIRST_STAGE_MODULES = 441
EXPECTED_VENDOR_DLKM_MODULES = 356
EXPECTED_VENDOR_DLKM_ONLY_MODULES = 50
EXPECTED_STOCK_UNION_MODULES = 491
MIN_TEMP_FREE_BYTES = 512 << 20

SOURCE_IDENTITIES = {
    "mfd": (
        Path("drivers/mfd/maxim/max77705.c"),
        40_632,
        "523fe8b765f53b775efc9f51a9cc1ddfc67088e8375894fe43d273bbde23db46",
    ),
    "pdic": (
        Path("drivers/usb/typec/maxim/max77705_usbc.c"),
        124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d",
    ),
    "debug": (
        Path("drivers/usb/typec/maxim/max77705_debug.c"),
        10_904,
        "47f423efdf8f6ffde06ce3665f82bfc36fa6f79c5f58f95b2330da5ecdd29210",
    ),
    "pdic_makefile": (
        Path("drivers/usb/typec/maxim/Makefile"),
        450,
        "8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d",
    ),
    "pdic_header": (
        Path("include/linux/usb/typec/maxim/max77705_usbc.h"),
        10_072,
        "1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e",
    ),
    "pdic_misc": (
        Path("drivers/usb/typec/common/pdic_misc.c"),
        16_791,
        "ec24080f7102a52ce94a44ec72b3c51358e3d3f18f4c871a9de1c41bbb8e49f6",
    ),
    "pdic_core": (
        Path("drivers/usb/typec/common/pdic_core.c"),
        4_632,
        "86d256315f7080c3d68f19da40e4c207c8965010934adcb3cd32554fb5e2082f",
    ),
    "pdic_sysfs": (
        Path("drivers/usb/typec/common/pdic_sysfs.c"),
        5_624,
        "18af12002f8e89453feaec33fabc1ce4f024e638152f5110079a03d97127abcf",
    ),
    "firmware": (
        Path("include/linux/mfd/firmware/max77705C_pass2_specific.h"),
        318_415,
        "6c21e9ff8fdc9fdd29f994867bb6bab5a79a024e4c481cbf58c69eb51fb33d96",
    ),
}
MODULE_IDENTITIES = {
    "mfd_max77705.ko": (
        125_840,
        "26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94",
    ),
    "pdic_max77705.ko": (
        423_456,
        "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
    ),
}

MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC = (
    "BOOT_FLASH_FW_PASS2",
    "max77705_usbc_fw_setting",
    "max77705_usbc_fw_update",
)
PDIC_UPDATE_IMPORTS = frozenset(
    {
        "BOOT_FLASH_FW_PASS2",
        "max77705_usbc_fw_setting",
        "max77705_usbc_fw_update",
        "request_firmware",
        "spu_firmware_signature_verify",
    }
)
PDIC_WRITABLE_DEFINED_SYMBOLS = frozenset(
    {
        "max77705_firmware_update_callback",
        "max77705_firmware_update_sysfs",
        "max77705_firmware_update_sysfs_work",
        "max77705_fw_update",
        "mxim_debug_init",
        "mxim_debug_ioctl",
        "mxim_debug_reg_store",
        "mxim_debug_opcode_store",
    }
)

# A future custom builder must import and call validate_custom_source_texts()
# before compiling.  A later linked-artifact validator must independently
# establish the corresponding symbol/import properties.
CUSTOM_PREFERRED_ADDITIONS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
)
CUSTOM_MFD_FORBIDDEN = (
    "BOOT_FLASH_FW_PASS2",
    "linux/mfd/firmware/",
    "max77705_usbc_fw_update",
    "__max77705_usbc_fw_update",
    "max77705_usbc_wait_response",
    "max77705_reset_ic",
)
CUSTOM_PDIC_FORBIDDEN = (
    "BOOT_FLASH_FW_PASS2",
    "MAX77705_SYS_FW_UPDATE",
    "PDIC_SYSFS_PROP_FW_UPDATE",
    "PDIC_SYSFS_PROP_FW_UPDATE_STATUS",
    "max77705_firmware_update_",
    "max77705_usbc_fw_setting",
    "max77705_usbc_fw_update",
    "request_firmware",
    "spu_firmware_signature_verify",
    "pdic_misc_init",
    "max77705_attr_grp",
    "max77705_fw_update",
    "mxim_debug_",
)


class SurfaceError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise SurfaceError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SurfaceError(f"{label} is not a direct regular file: {path}")
    actual = (path.stat().st_size, sha256_file(path))
    if actual != (size, digest):
        raise SurfaceError(f"{label} identity mismatch: {actual}")
    return {"path": str(path), "size": actual[0], "sha256": actual[1]}


def validate_tool(path: Path, size: int | None, digest: str, label: str) -> dict[str, Any]:
    """Validate a pinned host tool while preserving a multicall symlink name."""

    if not path.is_file():
        raise SurfaceError(f"{label} is missing or not a regular-file target: {path}")
    actual_size = path.stat().st_size
    actual_digest = sha256_file(path)
    if (size is not None and actual_size != size) or actual_digest != digest:
        raise SurfaceError(
            f"{label} identity mismatch: {(actual_size, actual_digest)}"
        )
    return {
        "path": str(path),
        "size": actual_size,
        "sha256": actual_digest,
        "symlink_argument_preserved": path.is_symlink(),
    }


def parse_inventory(
    path: Path,
    *,
    expected_sha256: str,
    expected_rows: int,
) -> list[dict[str, str]]:
    if sha256_file(path) != expected_sha256:
        raise SurfaceError(f"inventory identity mismatch: {path}")
    with path.open(encoding="ascii", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != expected_rows or any(not row.get("filename") for row in rows):
        raise SurfaceError(
            f"inventory row mismatch for {path}: {len(rows)} != {expected_rows}"
        )
    names = [row["filename"] for row in rows]
    if len(set(names)) != len(names):
        raise SurfaceError(f"duplicate inventory filename in {path}")
    return rows


def run_checked(command: list[str], *, cwd: Path | None = None, stdin: Any = None) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr[-4096:].decode("utf-8", errors="replace")
        raise SurfaceError(f"host command failed rc={result.returncode}: {command}: {stderr}")
    return result


def extract_first_stage_modules(
    vendor_ramdisk: Path,
    lz4: Path,
    inventory_rows: list[dict[str, str]],
    scratch: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    cpio_path = scratch / "vendor_ramdisk.cpio"
    with cpio_path.open("wb") as output:
        result = subprocess.run(
            [str(lz4), "-dc", str(vendor_ramdisk)],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise SurfaceError(
            "vendor ramdisk decompression failed: "
            + result.stderr[-4096:].decode("utf-8", errors="replace")
        )
    validate_file(
        cpio_path,
        VENDOR_RAMDISK_CPIO_IDENTITY[0],
        VENDOR_RAMDISK_CPIO_IDENTITY[1],
        "vendor ramdisk cpio",
    )

    with cpio_path.open("rb") as archive:
        listing_result = run_checked(["cpio", "-it"], stdin=archive)
    try:
        listing = listing_result.stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SurfaceError("vendor ramdisk listing is not UTF-8") from exc
    for name in listing:
        parsed = PurePosixPath(name)
        if parsed.is_absolute() or ".." in parsed.parts or str(parsed) != name:
            raise SurfaceError(f"unsafe vendor ramdisk member: {name!r}")
    module_members = sorted(
        name for name in listing
        if name.startswith("lib/modules/") and name.endswith(".ko")
    )
    module_names = [PurePosixPath(name).name for name in module_members]
    if (
        len(module_members) != EXPECTED_FIRST_STAGE_MODULES
        or len(set(module_names)) != EXPECTED_FIRST_STAGE_MODULES
    ):
        raise SurfaceError(f"first-stage module geometry mismatch: {len(module_members)}")

    extract_root = scratch / "first-stage"
    extract_root.mkdir()
    with cpio_path.open("rb") as archive:
        run_checked(
            [
                "cpio",
                "-idm",
                "--quiet",
                "--no-absolute-filenames",
                "lib/modules/*.ko",
            ],
            cwd=extract_root,
            stdin=archive,
        )
    module_dir = extract_root / "lib/modules"
    paths = {
        path.name: path
        for path in module_dir.glob("*.ko")
        if path.is_file() and not path.is_symlink()
    }
    if set(paths) != set(module_names):
        raise SurfaceError("first-stage extracted module set differs from cpio listing")

    expected = {row["filename"]: row for row in inventory_rows}
    if set(expected) != set(paths):
        raise SurfaceError("first-stage tracked inventory differs from exact cpio module set")
    rows_for_hash: list[tuple[str, int, str]] = []
    for name, path in sorted(paths.items()):
        size = path.stat().st_size
        digest = sha256_file(path)
        row = expected[name]
        if (str(size), digest) != (row["size_bytes"], row["sha256"]):
            raise SurfaceError(f"first-stage module identity mismatch: {name}")
        rows_for_hash.append((name, size, digest))
    return paths, {
        "module_count": len(paths),
        "inventory_sha256": FIRST_STAGE_INVENTORY_SHA256,
        "corpus_sha256": canonical_hash(rows_for_hash),
        "cpio_size": cpio_path.stat().st_size,
        "cpio_sha256": sha256_file(cpio_path),
    }


def extract_vendor_dlkm_only_modules(
    image: Path,
    dump_f2fs: Path,
    inventory_rows: list[dict[str, str]],
    scratch: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    rows = {
        row["filename"]: row
        for row in inventory_rows
        if row["reference_status"] == "vendor-dlkm-only"
    }
    if len(rows) != EXPECTED_VENDOR_DLKM_ONLY_MODULES:
        raise SurfaceError(f"vendor_dlkm-only inventory mismatch: {len(rows)}")

    reader = F2FSReader(image, dump_f2fs)
    directory_inode = reader.resolve_directory(PurePosixPath("/lib/modules"))
    entries = {
        entry.name: entry
        for entry in reader.directory(directory_inode)
        if entry.name.endswith(".ko")
    }
    if len(entries) != EXPECTED_VENDOR_DLKM_MODULES:
        raise SurfaceError(f"vendor_dlkm module geometry mismatch: {len(entries)}")
    if not set(rows).issubset(entries):
        raise SurfaceError("vendor_dlkm-only inventory has missing image entries")

    extract_root = scratch / "vendor-dlkm-only"
    extract_root.mkdir()
    paths: dict[str, Path] = {}
    rows_for_hash: list[tuple[str, int, str]] = []
    for name, row in sorted(rows.items()):
        entry = entries[name]
        if entry.file_type != FILE_TYPE_REGULAR or entry.inode != int(row["inode"]):
            raise SurfaceError(f"vendor_dlkm dentry mismatch: {name}")
        destination = extract_root / name
        reader.extract_file(entry, destination)
        size = destination.stat().st_size
        digest = sha256_file(destination)
        if (str(size), digest) != (row["size_bytes"], row["sha256"]):
            raise SurfaceError(f"vendor_dlkm-only module identity mismatch: {name}")
        paths[name] = destination
        rows_for_hash.append((name, size, digest))
    return paths, {
        "image_module_count": len(entries),
        "vendor_dlkm_only_count": len(paths),
        "inventory_sha256": VENDOR_DLKM_INVENTORY_SHA256,
        "vendor_dlkm_only_corpus_sha256": canonical_hash(rows_for_hash),
    }


def stock_module_union(root: Path, scratch: Path) -> tuple[dict[str, Path], dict[str, Any]]:
    vendor_ramdisk = root / VENDOR_RAMDISK
    image = root / VENDOR_DLKM_IMAGE
    lz4 = root / LZ4_TOOL
    # Keep the symlink spelling: f2fs-tools selects dump mode from argv[0].
    dump_f2fs = (root / DUMP_F2FS).absolute()
    first_inventory = root / FIRST_STAGE_INVENTORY
    vendor_inventory = root / VENDOR_DLKM_INVENTORY
    vendor_manifest = root / VENDOR_DLKM_MANIFEST

    inputs = {
        "vendor_ramdisk": validate_file(
            vendor_ramdisk, *VENDOR_RAMDISK_IDENTITY, "vendor ramdisk"
        ),
        "vendor_dlkm_image": validate_file(
            image, *VENDOR_DLKM_IDENTITY, "vendor_dlkm image"
        ),
        "lz4": validate_tool(lz4, *LZ4_IDENTITY, "lz4"),
        "dump_f2fs": validate_tool(
            dump_f2fs, None, DUMP_F2FS_SHA256, "dump.f2fs"
        ),
    }
    first_rows = parse_inventory(
        first_inventory,
        expected_sha256=FIRST_STAGE_INVENTORY_SHA256,
        expected_rows=EXPECTED_FIRST_STAGE_MODULES,
    )
    vendor_rows = parse_inventory(
        vendor_inventory,
        expected_sha256=VENDOR_DLKM_INVENTORY_SHA256,
        expected_rows=EXPECTED_VENDOR_DLKM_MODULES + 5,
    )
    if sha256_file(vendor_manifest) != VENDOR_DLKM_MANIFEST_SHA256:
        raise SurfaceError("vendor_dlkm manifest identity mismatch")
    manifest = json.loads(vendor_manifest.read_text(encoding="ascii"))
    counts = manifest.get("counts", {})
    expected_counts = {
        "vendor_dlkm_modules": EXPECTED_VENDOR_DLKM_MODULES,
        "reference_modules": EXPECTED_FIRST_STAGE_MODULES,
        "vendor_dlkm_only_modules": EXPECTED_VENDOR_DLKM_ONLY_MODULES,
        "union_unique_module_names": EXPECTED_STOCK_UNION_MODULES,
        "content_mismatch_modules": 0,
    }
    if any(counts.get(key) != value for key, value in expected_counts.items()):
        raise SurfaceError(f"vendor_dlkm manifest count mismatch: {counts}")
    if manifest.get("verified_vendor_dlkm_corpus") is not True:
        raise SurfaceError("vendor_dlkm overlap corpus is not verified")

    free_bytes = shutil.disk_usage(scratch).free
    if free_bytes < MIN_TEMP_FREE_BYTES:
        raise SurfaceError(f"insufficient temporary free space: {free_bytes}")
    first_paths, first_receipt = extract_first_stage_modules(
        vendor_ramdisk, lz4, first_rows, scratch
    )
    vendor_only_paths, vendor_receipt = extract_vendor_dlkm_only_modules(
        image, dump_f2fs, vendor_rows, scratch
    )
    if set(first_paths) & set(vendor_only_paths):
        raise SurfaceError("stock module corpus source classes unexpectedly overlap")
    union = {**first_paths, **vendor_only_paths}
    if len(union) != EXPECTED_STOCK_UNION_MODULES:
        raise SurfaceError(f"stock module union mismatch: {len(union)}")
    return union, {
        "absence_search_scope": (
            "all 491 unique stock module payload names across the exact 441-module "
            "vendor_ramdisk corpus and the 50 verified vendor_dlkm-only modules"
        ),
        "inputs": inputs,
        "first_stage": first_receipt,
        "vendor_dlkm_only": vendor_receipt,
        "overlap_byte_identical_count": counts["byte_identical_modules"],
        "first_stage_only_count": counts["reference_only_modules"],
        "union_unique_module_count": len(union),
    }


def readelf_symbols(path: Path) -> tuple[set[str], set[str]]:
    result = subprocess.run(
        ["readelf", "-WsW", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    defined: set[str] = set()
    undefined: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":"):
            continue
        ndx, name = fields[6], fields[7]
        if ndx == "UND":
            undefined.add(name)
        else:
            defined.add(name)
    if not defined:
        raise SurfaceError(f"no symbols parsed from {path}")
    return defined, undefined


def parse_firmware_array(text: str) -> list[int]:
    match = re.search(r"BOOT_FLASH_FW_PASS2\s*\[\s*\]\s*=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise SurfaceError("BOOT_FLASH_FW_PASS2 array not found")
    return [int(item, 16) for item in re.findall(r"0x([0-9a-fA-F]+)", match.group(1))]


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SurfaceError(f"{label} is missing required tokens: {missing}")


def validate_custom_source_texts(mfd: str, pdic: str, makefile: str) -> dict[str, Any]:
    """Validate the source-level preferred custom closure.

    Linked output still needs its own symbol, relocation, CFI/modversion, and
    dependency audit.  This function deliberately rejects an effect-free
    updater stub: the preferred closure removes the update ABI and payload
    entirely because the pinned inventory proves that only the replaced PDIC
    consumes it.
    """

    mfd_hits = [token for token in CUSTOM_MFD_FORBIDDEN if token in mfd]
    pdic_hits = [token for token in CUSTOM_PDIC_FORBIDDEN if token in pdic]
    if mfd_hits:
        raise SurfaceError(f"custom MFD retains forbidden update surface: {mfd_hits}")
    if pdic_hits:
        raise SurfaceError(f"custom PDIC retains forbidden writable surface: {pdic_hits}")
    if "max77705_debug.o" in makefile:
        raise SurfaceError("custom PDIC Makefile still links max77705_debug.o")

    require_tokens(
        mfd,
        (
            "store_ccic_bin_version",
            "0x6e",
            "0x40",
            "0x15",
            "max77705_irq_init",
            "mfd_add_devices",
        ),
        "custom MFD",
    )
    require_tokens(
        pdic,
        (
            "PDIC_SYSFS_PROP_CHIP_NAME",
            "pdic_core_register_chip",
            "max77705_muic_probe",
            "max77705_cc_init",
            "max77705_pd_init",
        ),
        "custom PDIC",
    )
    if re.search(r"max77705_sysfs_properties\s*\[\s*\]\s*=\s*\{\s*"
                 r"PDIC_SYSFS_PROP_CHIP_NAME\s*,?\s*\};", pdic, re.S) is None:
        raise SurfaceError("custom PDIC sysfs surface is not CHIP_NAME-only")
    return {
        "source_contract_satisfied": True,
        "preferred_addition_count": len(CUSTOM_PREFERRED_ADDITIONS),
        "preferred_total_module_count": 61 + len(CUSTOM_PREFERRED_ADDITIONS),
        "spu_verify_removed": True,
        "debug_object_removed": True,
        "misc_and_sysfs_update_surfaces_removed": True,
    }


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit(root: Path) -> dict[str, Any]:
    kernel = root / KERNEL_ROOT
    modules = root / MODULE_ROOT
    source_receipts = {
        label: validate_file(kernel / relative, size, digest, label)
        for label, (relative, size, digest) in SOURCE_IDENTITIES.items()
    }
    module_receipts = {
        name: validate_file(modules / name, size, digest, name)
        for name, (size, digest) in MODULE_IDENTITIES.items()
    }

    with tempfile.TemporaryDirectory(prefix="s22plus-max77705-stock-union-") as directory:
        module_paths, corpus_receipt = stock_module_union(root, Path(directory))
        symbol_tables = {
            name: readelf_symbols(path)
            for name, path in sorted(module_paths.items())
        }
        mfd_defined, mfd_undefined = symbol_tables["mfd_max77705.ko"]
        pdic_defined, pdic_undefined = symbol_tables["pdic_max77705.ko"]
        missing_mfd = set(MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC) - mfd_defined
        missing_pdic_imports = PDIC_UPDATE_IMPORTS - pdic_undefined
        missing_pdic_definitions = PDIC_WRITABLE_DEFINED_SYMBOLS - pdic_defined
        if missing_mfd or missing_pdic_imports or missing_pdic_definitions:
            raise SurfaceError(
                "stock linked surface mismatch: "
                f"mfd={sorted(missing_mfd)} imports={sorted(missing_pdic_imports)} "
                f"definitions={sorted(missing_pdic_definitions)}"
            )

        consumers: dict[str, list[str]] = {}
        for symbol in MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC:
            names = sorted(
                name
                for name, (_defined, undefined) in symbol_tables.items()
                if symbol in undefined
            )
            if names != ["pdic_max77705.ko"]:
                raise SurfaceError(f"unexpected {symbol} consumers: {names}")
            consumers[symbol] = names

    mfd_text = (kernel / SOURCE_IDENTITIES["mfd"][0]).read_text(errors="strict")
    pdic_text = (kernel / SOURCE_IDENTITIES["pdic"][0]).read_text(errors="strict")
    debug_text = (kernel / SOURCE_IDENTITIES["debug"][0]).read_text(errors="strict")
    makefile_text = (kernel / SOURCE_IDENTITIES["pdic_makefile"][0]).read_text(errors="strict")
    header_text = (kernel / SOURCE_IDENTITIES["pdic_header"][0]).read_text(errors="strict")
    misc_text = (kernel / SOURCE_IDENTITIES["pdic_misc"][0]).read_text(errors="strict")
    firmware_text = (kernel / SOURCE_IDENTITIES["firmware"][0]).read_text(
        encoding="utf-8-sig", errors="strict"
    )

    require_tokens(
        mfd_text,
        (
            "max77705_usbc_fw_setting(max77705, 0);",
            "EXPORT_SYMBOL_GPL(max77705_usbc_fw_update);",
            "EXPORT_SYMBOL_GPL(max77705_usbc_fw_setting);",
        ),
        "stock MFD source",
    )
    require_tokens(
        pdic_text,
        (
            "max77705_firmware_update_sysfs_work",
            "max77705_firmware_update_callback",
            "ppdic_data->fw_data.firmware_update = max77705_firmware_update_callback;",
            "ret = pdic_misc_init(ppdic_data);",
            "sysfs_create_group(&max77705->dev->kobj, &max77705_attr_grp);",
            "mxim_debug_init();",
        ),
        "stock PDIC source",
    )
    require_tokens(
        debug_text,
        (
            "misc_register(&mxim_debug_miscdev)",
            "mxim_debug_i2c_write",
            "mxim_debug_opcode_store",
            "mxim_debug_reg_store",
        ),
        "stock Max77705 debug source",
    )
    require_tokens(
        misc_text,
        (
            'NODE_OF_UMS "pdic_fwupdate"',
            "fw_data->ic_data->firmware_update(",
            "misc_register(&ums_update_device)",
        ),
        "stock PDIC misc source",
    )
    if "#define MAX77705_SYS_FW_UPDATE" not in header_text:
        raise SurfaceError("stock PDIC update macro is no longer unconditional")
    if "max77705_debug.o" not in makefile_text:
        raise SurfaceError("stock PDIC debug object is no longer linked")

    firmware = parse_firmware_array(firmware_text)
    expected_header = [0xC1, 0x66, 0xF1, 0xCE, 0x6E, 0x40, 0x15, 0x02]
    if len(firmware) != 53_055 or firmware[:8] != expected_header:
        raise SurfaceError(
            f"pinned firmware geometry mismatch: {len(firmware)}/{firmware[:8]}"
        )

    contract = {
        "status": "REGISTERED_NOT_SATISFIED",
        "preferred_total_module_count": 66,
        "preferred_additions": list(CUSTOM_PREFERRED_ADDITIONS),
        "stock_only_removed_addition": "spu_verify.ko",
        "mfd": {
            "firmware_payload_and_update_abi_absent": True,
            "probe_time_metadata_only": {
                "sw_main": [0x6E, 0x40, 0x15],
                "sw_boot": 0,
                "hardware_io": False,
            },
            "ordinary_irq_and_child_creation_retained": True,
        },
        "pdic": {
            "debug_object_absent": True,
            "update_imports_absent": sorted(PDIC_UPDATE_IMPORTS),
            "firmware_worker_absent": True,
            "firmware_misc_callback_absent": True,
            "pdic_misc_registration_absent": True,
            "local_control1_debug_attribute_absent": True,
            "pdic_core_chip_registration_retained": True,
            "visible_common_sysfs_properties": ["PDIC_SYSFS_PROP_CHIP_NAME"],
            "tagged_cached_observer_must_be_separate_and_read_only": True,
        },
        "future_linked_proofs": [
            "source validator called before compilation",
            "no forbidden defined or undefined symbol survives",
            "no firmware payload symbol or 53055-byte payload survives",
            "no pdic_misc_init, mxim_debug_init, request_firmware, or direct local sysfs-group import survives",
            "the retained common PDIC sysfs list is CHIP_NAME-only and read-only",
            "modversion and CFI closure matches the fixed Image",
            "custom module dependency closure is exactly 66 modules",
        ],
    }
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "device_contact": False,
        "source_receipts": source_receipts,
        "module_receipts": module_receipts,
        "stock_module_union": corpus_receipt,
        "stock_surface": {
            "firmware_header": {
                "array_bytes": len(firmware),
                "first_eight": expected_header,
                "source_version": "6E.00",
                "product_id": 1,
            },
            "mfd_exports": list(MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC),
            "exclusive_consumers": consumers,
            "exclusive_consumer_search_scope": corpus_receipt["absence_search_scope"],
            "pdic_update_imports": sorted(PDIC_UPDATE_IMPORTS),
            "pdic_writable_defined_symbols": sorted(PDIC_WRITABLE_DEFINED_SYMBOLS),
            "separate_same_name_surfaces": {
                "common_pdic_fw_update": "firmware update",
                "parent_local_fw_update": "CONTROL1 read/write debug path",
            },
            "raw_debug_misc_and_sysfs": True,
            "pdic_firmware_misc_device": True,
            "pdic_uvdm_misc_device": True,
        },
        "custom_contract": contract,
        "custom_contract_sha256": canonical_hash(contract),
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=repo_root())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    result = audit(root)
    output = args.output or root / DEFAULT_OUTPUT
    atomic_json(output.resolve(), result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
