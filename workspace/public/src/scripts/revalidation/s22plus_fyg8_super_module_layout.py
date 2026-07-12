#!/usr/bin/env python3
"""Prove the FYG8 super-partition module-source layout host-side."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from s22plus_fyg8_f2fs_module_corpus import (
    Dentry,
    F2FSReader,
    FILE_TYPE_DIRECTORY,
    sha256_file,
)


SCHEMA = "s22plus_fyg8_super_module_layout_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
DEFAULT_WORK = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/super-corpus-work"
)
DEFAULT_CORPUS_MANIFEST = Path("docs/module-map/s22plus-fyg8-super/manifest.json")
DEFAULT_OUT = Path("docs/module-map/s22plus-fyg8-super/layout-manifest.json")
DEFAULT_DUMP_F2FS = Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
EXPECTED_RAW_SUPER = (
    12475957248,
    "63061c093dce2e1f0a3df41bf0a960b72f221ecca8277c9f2fcc20a3e8e8f4ae",
)
EXPECTED_PARTITIONS = {
    "system": (
        6669402112,
        "d225ba954bb05f4738c6d5f1e9a3f9dffa38e488ca192aec9563bcbafd111647",
    ),
    "odm": (
        21389312,
        "937e692aff25c4a88d27b2b93e4b23abe39ebe034a95c6b18416b2667c263e76",
    ),
    "product": (1314770944, None),
    "system_ext": (183328768, None),
    "vendor": (
        2175606784,
        "a885cb219d3d21aea87aacb514650857d46f9e2d3b2bfa2fb7a7f1754c5dacf2",
    ),
    "vendor_dlkm": (
        57610240,
        "e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26",
    ),
}
EXPECTED_CORPUS_MANIFEST_SHA256 = "c23077120499012db4d492d5b494c1f69274486e5bbf7a15ec3f192dbdd71092"
EXPECTED_UNION_MODULES = 491


class LayoutError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise LayoutError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def absolute_without_symlink_resolution(root: Path, path: Path) -> Path:
    return path.absolute() if path.is_absolute() else (root / path).absolute()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.absolute().relative_to(root.absolute()))
    except ValueError:
        return str(path.absolute())


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LayoutError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LayoutError(f"JSON root must be object: {path}")
    return data


def parse_super_metadata(path: Path) -> dict[str, Any]:
    if path.stat().st_size != EXPECTED_RAW_SUPER[0] or sha256_file(path) != EXPECTED_RAW_SUPER[1]:
        raise LayoutError("raw super image identity mismatch")
    with path.open("rb") as handle:
        handle.seek(4096)
        geometry_page = bytearray(handle.read(4096))
        magic, geometry_size = struct.unpack_from("<II", geometry_page, 0)
        if magic != 0x616C4467 or geometry_size != 52:
            raise LayoutError("super geometry header mismatch")
        geometry_checksum = bytes(geometry_page[8:40])
        geometry = geometry_page[:geometry_size]
        geometry[8:40] = b"\0" * 32
        if hashlib.sha256(geometry).digest() != geometry_checksum:
            raise LayoutError("super geometry checksum mismatch")
        metadata_max_size, slots, logical_block_size = struct.unpack_from(
            "<III", geometry_page, 40
        )
        handle.seek(4096 + 4096 * 2)
        metadata = bytearray(handle.read(metadata_max_size))
    header_magic, major, minor, header_size = struct.unpack_from("<IHHI", metadata, 0)
    if header_magic != 0x414C5030 or (major, minor) != (10, 0) or header_size != 128:
        raise LayoutError("super metadata header mismatch")
    header_checksum = bytes(metadata[12:44])
    header = metadata[:header_size]
    header[12:44] = b"\0" * 32
    if hashlib.sha256(header).digest() != header_checksum:
        raise LayoutError("super metadata header checksum mismatch")
    tables_size = struct.unpack_from("<I", metadata, 44)[0]
    tables_checksum = bytes(metadata[48:80])
    tables = metadata[header_size:header_size + tables_size]
    if hashlib.sha256(tables).digest() != tables_checksum:
        raise LayoutError("super metadata tables checksum mismatch")
    descriptors = [struct.unpack_from("<III", metadata, 80 + index * 12) for index in range(4)]
    partition_offset, partition_count, partition_size = descriptors[0]
    extent_offset, extent_count, extent_size = descriptors[1]
    extents = [
        struct.unpack_from("<QIQI", tables, extent_offset + index * extent_size)
        for index in range(extent_count)
    ]
    partitions: dict[str, dict[str, Any]] = {}
    for index in range(partition_count):
        entry = tables[
            partition_offset + index * partition_size:
            partition_offset + (index + 1) * partition_size
        ]
        name = entry[:36].split(b"\0", 1)[0].decode("ascii")
        attributes, first_extent, extent_number, group = struct.unpack_from("<IIII", entry, 36)
        owned_extents = extents[first_extent:first_extent + extent_number]
        if any(target_type != 0 or target_source != 0 for _sectors, target_type, _data, target_source in owned_extents):
            raise LayoutError(f"non-linear or multi-device extent for {name}")
        partitions[name] = {
            "attributes": attributes,
            "group": group,
            "bytes": sum(sectors * 512 for sectors, _type, _data, _source in owned_extents),
            "extents": [
                {"sectors": sectors, "target_sector": target_data}
                for sectors, _type, target_data, _source in owned_extents
            ],
        }
    expected_sizes = {name: value[0] for name, value in EXPECTED_PARTITIONS.items()}
    actual_sizes = {name: value["bytes"] for name, value in partitions.items()}
    if actual_sizes != expected_sizes:
        raise LayoutError(f"super partition table mismatch: {actual_sizes}")
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": EXPECTED_RAW_SUPER[1],
        "geometry": {
            "metadata_max_size": metadata_max_size,
            "slot_count": slots,
            "logical_block_size": logical_block_size,
            "checksum_verified": True,
        },
        "metadata": {
            "major": major,
            "minor": minor,
            "header_checksum_verified": True,
            "tables_checksum_verified": True,
        },
        "partitions": partitions,
    }


def walk_filesystem(reader: F2FSReader) -> dict[str, Any]:
    stack: list[tuple[PurePosixPath, int]] = [(PurePosixPath("/"), 3)]
    visited: set[int] = set()
    module_files: list[str] = []
    module_directories: list[str] = []
    directory_count = 0
    file_count = 0
    while stack:
        path, inode = stack.pop()
        if inode in visited:
            continue
        visited.add(inode)
        directory_count += 1
        for entry in reader.directory(inode):
            if entry.name in {".", ".."}:
                continue
            child = path / entry.name
            if entry.file_type == FILE_TYPE_DIRECTORY:
                if entry.name == "modules":
                    module_directories.append(str(child))
                stack.append((child, entry.inode))
            else:
                file_count += 1
                if entry.name.endswith(".ko"):
                    module_files.append(str(child))
    return {
        "directory_count": directory_count,
        "non_directory_entry_count": file_count,
        "module_files": sorted(module_files),
        "module_directories": sorted(module_directories),
    }


def build_layout(
    root: Path,
    work: Path,
    dump_f2fs: Path,
    corpus_manifest_path: Path,
) -> dict[str, Any]:
    super_result = parse_super_metadata(work / "super.img.raw")
    corpus_sha = sha256_file(corpus_manifest_path)
    corpus = load_json(corpus_manifest_path)
    if corpus_sha != EXPECTED_CORPUS_MANIFEST_SHA256:
        raise LayoutError(f"vendor_dlkm corpus manifest SHA256 mismatch: {corpus_sha}")
    if (
        corpus.get("schema") != "s22plus_fyg8_f2fs_module_corpus_v1"
        or corpus.get("target") != TARGET
        or corpus.get("verified_vendor_dlkm_corpus") is not True
        or corpus.get("counts", {}).get("union_unique_module_names") != EXPECTED_UNION_MODULES
    ):
        raise LayoutError("vendor_dlkm corpus manifest contract mismatch")

    scans: dict[str, Any] = {}
    for name in ("system", "vendor", "odm", "vendor_dlkm"):
        image = work / f"{name}.img"
        expected_size, expected_sha = EXPECTED_PARTITIONS[name]
        if image.stat().st_size != expected_size:
            raise LayoutError(f"partition image size mismatch for {name}")
        image_sha = sha256_file(image)
        if image_sha != expected_sha:
            raise LayoutError(f"partition image SHA256 mismatch for {name}: {image_sha}")
        scan = walk_filesystem(F2FSReader(image, dump_f2fs))
        scans[name] = {
            "path": display_path(root, image),
            "size": expected_size,
            "sha256": image_sha,
            **scan,
        }

    non_dlkm_modules = {
        name: scan["module_files"]
        for name, scan in scans.items()
        if name != "vendor_dlkm" and scan["module_files"]
    }
    vendor_dlkm_modules = scans["vendor_dlkm"]["module_files"]
    expected_vendor_paths = {
        f"/lib/modules/{row.split(chr(9), 1)[0]}"
        for row in (root / "docs/module-map/s22plus-fyg8-super/inventory.tsv").read_text(encoding="ascii").splitlines()[1:]
        if row.split("\t", 1)[0].endswith(".ko")
    }
    complete = (
        not non_dlkm_modules
        and set(vendor_dlkm_modules) == expected_vendor_paths
        and len(vendor_dlkm_modules) == 356
        and set(super_result["partitions"]) == set(EXPECTED_PARTITIONS)
        and "system_dlkm" not in super_result["partitions"]
        and "odm_dlkm" not in super_result["partitions"]
    )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "super": super_result,
        "partition_scans": scans,
        "corpus_manifest": {
            "path": display_path(root, corpus_manifest_path),
            "sha256": corpus_sha,
            "verified_vendor_dlkm_corpus": corpus["verified_vendor_dlkm_corpus"],
            "union_unique_module_names": corpus["counts"]["union_unique_module_names"],
        },
        "non_vendor_dlkm_module_files": non_dlkm_modules,
        "complete_on_disk_module_corpus": complete,
        "complete_module_count": EXPECTED_UNION_MODULES if complete else 0,
        "interpretation": (
            "FYG8 on-disk module corpus is the 491-name union of vendor_boot vendor ramdisk and vendor_dlkm"
            if complete
            else "FYG8 on-disk module corpus remains open"
        ),
        "safety": {
            "device_contact": False,
            "mount": False,
            "source_filesystem_write": False,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--dump-f2fs", type=Path, default=DEFAULT_DUMP_F2FS)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    result = build_layout(
        root,
        resolve(root, args.work),
        absolute_without_symlink_resolution(root, args.dump_f2fs),
        resolve(root, args.corpus_manifest),
    )
    out = resolve(root, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({
        "result": "pass" if result["complete_on_disk_module_corpus"] else "fail",
        "complete_module_count": result["complete_module_count"],
        "super_partitions": sorted(result["super"]["partitions"]),
        "out": display_path(root, out),
    }, indent=2, sort_keys=True))
    return 0 if result["complete_on_disk_module_corpus"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LayoutError, OSError, struct.error) as exc:
        raise SystemExit(str(exc)) from exc
