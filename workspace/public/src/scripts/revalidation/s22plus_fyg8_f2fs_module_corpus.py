#!/usr/bin/env python3
"""Extract and compare the FYG8 vendor_dlkm F2FS module corpus host-side."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA = "s22plus_fyg8_f2fs_module_corpus_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_VENDOR_DLKM_SHA256 = "e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26"
EXPECTED_VENDOR_DLKM_MODULES = 356
EXPECTED_REFERENCE_MODULES = 441
EXPECTED_VERMAGIC = (
    "5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 "
    "SMP preempt mod_unload modversions aarch64"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/"
    "super-corpus-work/vendor_dlkm.img"
)
DEFAULT_REFERENCE_DIR = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
DEFAULT_DUMP_F2FS = Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
DEFAULT_OUT = Path("docs/module-map/s22plus-fyg8-super")
BLOCK_SIZE = 4096
NR_DENTRY_IN_BLOCK = 214
DENTRY_BITMAP_BYTES = 27
DENTRY_RESERVED_BYTES = 3
DENTRY_BYTES = 11
FILENAME_OFFSET = DENTRY_BITMAP_BYTES + DENTRY_RESERVED_BYTES + DENTRY_BYTES * NR_DENTRY_IN_BLOCK
FILENAME_SLOT_BYTES = 8
FILE_TYPE_REGULAR = 1
FILE_TYPE_DIRECTORY = 2
HOST_TOOL_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"


class CorpusError(ValueError):
    pass


@dataclass(frozen=True)
class Dentry:
    inode: int
    file_type: int
    name: str


@dataclass(frozen=True)
class InodeInfo:
    inode: int
    mode: int
    size: int
    name: str
    flags: int
    inline_flags: int
    compression_algorithm: int
    log_cluster_size: int
    extra_isize: int
    inode_addresses: tuple[int, ...]
    direct_nids: tuple[int, int]


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CorpusError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def absolute_without_symlink_resolution(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.absolute()
    return (root / path).absolute()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.absolute().relative_to(root.absolute()))
    except ValueError:
        return str(path.absolute())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dentry_block(data: bytes) -> tuple[Dentry, ...]:
    if len(data) != BLOCK_SIZE:
        raise CorpusError(f"dentry block size mismatch: {len(data)}")
    entries: list[Dentry] = []
    slot = 0
    while slot < NR_DENTRY_IN_BLOCK:
        valid = bool(data[slot // 8] & (1 << (slot % 8)))
        if not valid:
            slot += 1
            continue
        _hash_code, inode, name_len, file_type = struct.unpack_from(
            "<IIHB", data, DENTRY_BITMAP_BYTES + DENTRY_RESERVED_BYTES + slot * DENTRY_BYTES
        )
        if name_len == 0 or name_len > 255:
            slot += 1
            continue
        slot_count = (name_len + FILENAME_SLOT_BYTES - 1) // FILENAME_SLOT_BYTES
        name_start = FILENAME_OFFSET + slot * FILENAME_SLOT_BYTES
        name_bytes = data[name_start:name_start + name_len]
        try:
            name = name_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CorpusError(f"invalid UTF-8 dentry at slot {slot}") from exc
        if inode:
            entries.append(Dentry(inode=inode, file_type=file_type, name=name))
        slot += max(slot_count, 1)
    return tuple(entries)


class F2FSReader:
    def __init__(self, image: Path, dump_f2fs: Path):
        self.image = image
        self.dump_f2fs = dump_f2fs
        self._inode_cache: dict[int, InodeInfo] = {}

    def dump_inode_text(self, inode: int, *, answer: str = "N\n", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.dump_f2fs), "-i", str(inode), str(self.image)],
            input=answer,
            text=True,
            capture_output=True,
            cwd=cwd,
            check=False,
            env={"PATH": HOST_TOOL_PATH, "LC_ALL": "C"},
        )

    def inode_info(self, inode: int) -> InodeInfo:
        if inode in self._inode_cache:
            return self._inode_cache[inode]
        completed = self.dump_inode_text(inode)
        text = completed.stdout + completed.stderr

        def one(pattern: str, field: str, default: str | None = None) -> str:
            matches = re.findall(pattern, text, flags=re.MULTILINE)
            if len(matches) == 1:
                return matches[0]
            if not matches and default is not None:
                return default
            raise CorpusError(f"cannot parse {field} for inode {inode}: {len(matches)} matches")

        mode = int(one(r"^i_mode\s+\[0x\s*([0-9a-fA-F]+)\s*:", "mode"), 16)
        size = int(one(r"^i_size\s+\[0x\s*[0-9a-fA-F]+\s*:\s*([0-9]+)\]", "size"))
        name = one(r"^i_name\s+\[([^]]*)\]", "name", "")
        flags_value = int(one(r"^i_flags\s+\[0x\s*([0-9a-fA-F]+)\s*:", "flags"), 16)
        inline_flags = int(one(r"^i_inline\s+\[0x\s*([0-9a-fA-F]+)\s*:", "inline flags"), 16)
        compression_algorithm = int(
            one(r"^i_compress_algrithm\s+\[0x\s*([0-9a-fA-F]+)\s*:", "compression algorithm", "0"),
            16,
        )
        log_cluster_size = int(
            one(r"^i_log_cluster_size\s+\[0x\s*([0-9a-fA-F]+)\s*:", "cluster size", "0"),
            16,
        )
        extra_isize = int(
            one(r"^i_extra_isize\s+\[0x\s*([0-9a-fA-F]+)\s*:", "extra inode size", "0"),
            16,
        )
        inline_xattr_addresses = 50 if inline_flags & 0x1 else 0
        address_slots = 923 - extra_isize // 4 - inline_xattr_addresses
        if flags_value & 0x4:
            address_slots = address_slots // (1 << log_cluster_size) * (1 << log_cluster_size)
        addresses = [0] * address_slots
        for index_text, value_text in re.findall(
            r"^i_addr\[0x([0-9a-fA-F]+)\](?:\s+cluster flag)?\s+\[0x\s*([0-9a-fA-F]+)\s*:",
            text,
            flags=re.MULTILINE,
        ):
            index = int(index_text, 16) - extra_isize // 4
            if index < 0 or index >= address_slots:
                raise CorpusError(f"inode address index out of range for inode {inode}: {index_text}")
            addresses[index] = int(value_text, 16)
        nids = {
            int(index): int(value, 16)
            for index, value in re.findall(
                r"^i_nid\[([0-4])\]\s+\[0x\s*([0-9a-fA-F]+)\s*:",
                text,
                flags=re.MULTILINE,
            )
        }
        if any(nids.get(index, 0) for index in (2, 3, 4)):
            raise CorpusError(f"indirect F2FS node layout is outside this bounded reader: inode {inode}")
        result = InodeInfo(
            inode=inode,
            mode=mode,
            size=size,
            name=name,
            flags=flags_value,
            inline_flags=inline_flags,
            compression_algorithm=compression_algorithm,
            log_cluster_size=log_cluster_size,
            extra_isize=extra_isize,
            inode_addresses=tuple(addresses),
            direct_nids=(nids.get(0, 0), nids.get(1, 0)),
        )
        self._inode_cache[inode] = result
        return result

    def directory(self, inode: int) -> tuple[Dentry, ...]:
        info = self.inode_info(inode)
        if not (info.mode & 0x4000):
            raise CorpusError(f"inode is not a directory: {inode}")
        entries: list[Dentry] = []
        with self.image.open("rb") as handle:
            for block in info.inode_addresses:
                if not block:
                    continue
                if block in {0xFFFFFFFE, 0xFFFFFFFF}:
                    raise CorpusError(f"compressed or new address in directory inode {inode}")
                handle.seek(block * BLOCK_SIZE)
                data = handle.read(BLOCK_SIZE)
                entries.extend(parse_dentry_block(data))
        names: set[str] = set()
        for entry in entries:
            if entry.name in names:
                raise CorpusError(f"duplicate dentry name in inode {inode}: {entry.name}")
            names.add(entry.name)
        return tuple(entries)

    def resolve_directory(self, path: PurePosixPath) -> int:
        if not path.is_absolute():
            raise CorpusError(f"module directory must be absolute: {path}")
        inode = 3
        for component in path.parts[1:]:
            candidates = [entry for entry in self.directory(inode) if entry.name == component]
            if len(candidates) != 1 or candidates[0].file_type != FILE_TYPE_DIRECTORY:
                raise CorpusError(f"directory component not found uniquely: {path}: {component}")
            inode = candidates[0].inode
        return inode

    def direct_node_addresses(self, nid: int, *, cluster_size: int) -> tuple[int, ...]:
        completed = self.dump_inode_text(nid)
        text = completed.stdout + completed.stderr
        if completed.returncode != 0 or "is direct node or indirect node" not in text:
            raise CorpusError(f"cannot read direct node nid={nid}")
        values = {
            int(index): int(value, 16)
            for index, value in re.findall(
                r"^\[([0-9]+)\]\s+\[0x\s*([0-9a-fA-F]+)\s*:",
                text,
                flags=re.MULTILINE,
            )
        }
        if len(values) != 1018 or set(values) != set(range(1018)):
            raise CorpusError(f"direct node shape mismatch nid={nid}: {len(values)} entries")
        address_count = 1018 // cluster_size * cluster_size
        return tuple(values[index] for index in range(address_count))

    def file_addresses(self, info: InodeInfo) -> tuple[int, ...]:
        page_count = (info.size + BLOCK_SIZE - 1) // BLOCK_SIZE
        cluster_size = 1 << info.log_cluster_size if info.flags & 0x4 else 1
        needed = (page_count + cluster_size - 1) // cluster_size * cluster_size
        addresses = list(info.inode_addresses)
        for nid in info.direct_nids:
            if nid:
                addresses.extend(self.direct_node_addresses(nid, cluster_size=cluster_size))
        if len(addresses) < needed:
            raise CorpusError(
                f"not enough F2FS addresses for inode {info.inode}: {len(addresses)} < {needed}"
            )
        return tuple(addresses[:needed])

    @staticmethod
    def lz4_decompress(data: bytes, output_size: int) -> bytes:
        library_name = ctypes.util.find_library("lz4") or "liblz4.so.1"
        library = ctypes.CDLL(library_name)
        decompress = library.LZ4_decompress_safe
        decompress.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        decompress.restype = ctypes.c_int
        source = ctypes.create_string_buffer(data)
        destination = ctypes.create_string_buffer(output_size)
        result = decompress(source, destination, len(data), output_size)
        if result != output_size:
            raise CorpusError(f"LZ4 decompression size mismatch: {result} != {output_size}")
        return destination.raw[:output_size]

    def read_file(self, info: InodeInfo) -> bytes:
        addresses = self.file_addresses(info)
        compressed_file = bool(info.flags & 0x4)
        cluster_size = 1 << info.log_cluster_size if compressed_file else 1
        if compressed_file and info.compression_algorithm != 1:
            raise CorpusError(
                f"unsupported F2FS compression algorithm for inode {info.inode}: {info.compression_algorithm}"
            )
        output = bytearray()
        with self.image.open("rb") as handle:
            for cluster_start in range(0, len(addresses), cluster_size):
                cluster = addresses[cluster_start:cluster_start + cluster_size]
                if cluster[0] == 0xFFFFFFFE:
                    compressed_pages = bytearray()
                    for block in cluster[1:]:
                        if block in {0, 0xFFFFFFFF}:
                            continue
                        if block == 0xFFFFFFFE:
                            raise CorpusError(f"nested compressed marker in inode {info.inode}")
                        handle.seek(block * BLOCK_SIZE)
                        compressed_pages.extend(handle.read(BLOCK_SIZE))
                    if len(compressed_pages) < 24:
                        raise CorpusError(f"compressed cluster has no header in inode {info.inode}")
                    compressed_length = struct.unpack_from("<I", compressed_pages, 0)[0]
                    if compressed_length > len(compressed_pages) - 24:
                        raise CorpusError(
                            f"compressed length outside physical pages in inode {info.inode}: {compressed_length}"
                        )
                    output.extend(
                        self.lz4_decompress(
                            bytes(compressed_pages[24:24 + compressed_length]),
                            cluster_size * BLOCK_SIZE,
                        )
                    )
                    continue
                for block in cluster:
                    if block == 0:
                        output.extend(b"\0" * BLOCK_SIZE)
                    elif block in {0xFFFFFFFE, 0xFFFFFFFF}:
                        raise CorpusError(f"invalid F2FS data address in inode {info.inode}: {block:#x}")
                    else:
                        handle.seek(block * BLOCK_SIZE)
                        page = handle.read(BLOCK_SIZE)
                        if len(page) != BLOCK_SIZE:
                            raise CorpusError(f"short F2FS data block in inode {info.inode}: {block:#x}")
                        output.extend(page)
        return bytes(output[:info.size])

    def extract_file(self, entry: Dentry, destination: Path) -> None:
        if entry.file_type != FILE_TYPE_REGULAR:
            raise CorpusError(f"refusing to extract non-regular dentry: {entry}")
        if PurePosixPath(entry.name).name != entry.name or entry.name in {"", ".", ".."}:
            raise CorpusError(f"unsafe F2FS filename: {entry.name!r}")
        info = self.inode_info(entry.inode)
        data = self.read_file(info)
        if len(data) != info.size:
            raise CorpusError(f"extracted size mismatch for {entry.name}: {len(data)} != {info.size}")
        destination.write_bytes(data)


def render_inventory(rows: list[dict[str, Any]]) -> str:
    header = (
        "filename\tinode\tsize_bytes\tsha256\treference_sha256\t"
        "reference_status\tvermagic\tsrcversion\trequired_symbol_version_count\n"
    )
    return header + "".join(
        f"{row['filename']}\t{row['inode']}\t{row['size_bytes']}\t{row['sha256']}\t"
        f"{row['reference_sha256']}\t{row['reference_status']}\t{row['vermagic']}\t"
        f"{row['srcversion']}\t{row['required_symbol_version_count']}\n"
        for row in rows
    )


def module_metadata(path: Path) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    modinfo = subprocess.run(
        ["modinfo", str(path)], text=True, capture_output=True, check=False,
        env={"PATH": HOST_TOOL_PATH, "LC_ALL": "C"},
    )
    if modinfo.returncode != 0:
        raise CorpusError(f"modinfo failed for {path.name}: {modinfo.stderr.strip()}")
    fields: dict[str, list[str]] = {}
    for raw in modinfo.stdout.splitlines():
        key, separator, value = raw.partition(":")
        if separator:
            fields.setdefault(key.strip(), []).append(value.strip())
    vermagic_values = fields.get("vermagic", [])
    if vermagic_values != [EXPECTED_VERMAGIC]:
        raise CorpusError(f"vermagic mismatch for {path.name}: {vermagic_values}")
    srcversion_values = fields.get("srcversion", [])
    srcversion = srcversion_values[0] if len(srcversion_values) == 1 else ""

    versions_result = subprocess.run(
        ["modprobe", "--dump-modversions", str(path)],
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": HOST_TOOL_PATH, "LC_ALL": "C"},
    )
    if versions_result.returncode != 0:
        raise CorpusError(
            f"modprobe --dump-modversions failed for {path.name}: {versions_result.stderr.strip()}"
        )
    versions: dict[str, str] = {}
    for raw in versions_result.stdout.splitlines():
        fields_row = raw.split()
        if len(fields_row) != 2 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", fields_row[0]):
            raise CorpusError(f"malformed modversion row for {path.name}: {raw!r}")
        crc, symbol = fields_row[0].lower(), fields_row[1]
        if symbol in versions:
            raise CorpusError(f"duplicate modversion symbol for {path.name}: {symbol}")
        versions[symbol] = crc
    return EXPECTED_VERMAGIC, srcversion, tuple(sorted(versions.items()))


def render_vendor_only_requirements(rows: list[tuple[str, str, str]]) -> str:
    return "module\tsymbol\trequired_crc\tprovider_status\n" + "".join(
        f"{module}\t{symbol}\t{crc}\tkernel-or-module-unresolved\n"
        for module, symbol, crc in sorted(rows)
    )


def build_corpus(
    root: Path,
    image: Path,
    dump_f2fs: Path,
    reference_dir: Path,
    module_dir: PurePosixPath,
    out_dir: Path,
) -> dict[str, Any]:
    if not image.is_file() or not dump_f2fs.is_file() or not reference_dir.is_dir():
        raise CorpusError("image, dump.f2fs, or reference module directory is missing")
    image_sha = sha256_file(image)
    if image_sha != EXPECTED_VENDOR_DLKM_SHA256:
        raise CorpusError(f"vendor_dlkm image SHA256 mismatch: {image_sha}")
    reference_modules = {path.name: path for path in reference_dir.glob("*.ko") if path.is_file()}
    if len(reference_modules) != EXPECTED_REFERENCE_MODULES:
        raise CorpusError(
            f"reference module count mismatch: {len(reference_modules)} != {EXPECTED_REFERENCE_MODULES}"
        )

    reader = F2FSReader(image, dump_f2fs)
    module_inode = reader.resolve_directory(module_dir)
    entries = [entry for entry in reader.directory(module_inode) if entry.name not in {".", ".."}]
    module_entries = sorted((entry for entry in entries if entry.name.endswith(".ko")), key=lambda item: item.name)
    metadata_entries = sorted((entry for entry in entries if not entry.name.endswith(".ko")), key=lambda item: item.name)
    if len(module_entries) != EXPECTED_VENDOR_DLKM_MODULES:
        raise CorpusError(
            f"vendor_dlkm module count mismatch: {len(module_entries)} != {EXPECTED_VENDOR_DLKM_MODULES}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    vendor_only_requirements: list[tuple[str, str, str]] = []
    with tempfile.TemporaryDirectory(prefix="vendor-dlkm-files-", dir=out_dir) as extracted_temp:
        extracted_dir = Path(extracted_temp)
        for entry in [*module_entries, *metadata_entries]:
            destination = extracted_dir / entry.name
            reader.extract_file(entry, destination)
            actual_sha = sha256_file(destination)
            reference = reference_modules.get(entry.name)
            reference_sha = sha256_file(reference) if reference is not None else ""
            if not entry.name.endswith(".ko"):
                status = "metadata"
                vermagic = ""
                srcversion = ""
                required_versions: tuple[tuple[str, str], ...] = ()
            elif reference is None:
                status = "vendor-dlkm-only"
                vermagic, srcversion, required_versions = module_metadata(destination)
                vendor_only_requirements.extend(
                    (entry.name, symbol, crc) for symbol, crc in required_versions
                )
            elif actual_sha == reference_sha:
                status = "byte-identical"
                vermagic, srcversion, required_versions = module_metadata(destination)
            else:
                status = "content-mismatch"
                vermagic, srcversion, required_versions = module_metadata(destination)
            rows.append(
                {
                    "filename": entry.name,
                    "inode": entry.inode,
                    "size_bytes": destination.stat().st_size,
                    "sha256": actual_sha,
                    "reference_sha256": reference_sha,
                    "reference_status": status,
                    "vermagic": vermagic,
                    "srcversion": srcversion,
                    "required_symbol_version_count": len(required_versions),
                }
            )

    rows.sort(key=lambda row: row["filename"])
    inventory = render_inventory(rows)
    module_rows = [row for row in rows if row["filename"].endswith(".ko")]
    vendor_only = [row["filename"] for row in module_rows if row["reference_status"] == "vendor-dlkm-only"]
    content_mismatch = [row["filename"] for row in module_rows if row["reference_status"] == "content-mismatch"]
    byte_identical = [row["filename"] for row in module_rows if row["reference_status"] == "byte-identical"]
    reference_only = sorted(set(reference_modules) - {row["filename"] for row in module_rows})
    overlap_count = len(set(reference_modules) & {row["filename"] for row in module_rows})
    verified = not content_mismatch and len(byte_identical) == overlap_count
    requirements_text = render_vendor_only_requirements(vendor_only_requirements)
    manifest = {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "inputs": {
            "vendor_dlkm_image": {
                "path": display_path(root, image),
                "size": image.stat().st_size,
                "sha256": image_sha,
            },
            "reference_directory": display_path(root, reference_dir),
            "dump_f2fs": {
                "path": display_path(root, dump_f2fs),
                "sha256": sha256_file(dump_f2fs),
            },
        },
        "module_directory": str(module_dir),
        "counts": {
            "vendor_dlkm_modules": len(module_rows),
            "vendor_dlkm_metadata_files": len(metadata_entries),
            "reference_modules": len(reference_modules),
            "byte_identical_modules": len(byte_identical),
            "overlap_modules": overlap_count,
            "vendor_dlkm_only_modules": len(vendor_only),
            "content_mismatch_modules": len(content_mismatch),
            "reference_only_modules": len(reference_only),
            "union_unique_module_names": len(set(reference_modules) | {row["filename"] for row in module_rows}),
        },
        "vendor_dlkm_only_sample": vendor_only[:50],
        "content_mismatch_sample": content_mismatch[:50],
        "reference_only_sample": reference_only[:50],
        "inventory": {
            "path": "inventory.tsv",
            "bytes": len(inventory.encode("ascii")),
            "sha256": hashlib.sha256(inventory.encode("ascii")).hexdigest(),
        },
        "vendor_dlkm_only_symbol_crc_requirements": {
            "path": "vendor-dlkm-only-symbol-crc-requirements.tsv",
            "rows": len(vendor_only_requirements),
            "unique_symbols": len({symbol for _module, symbol, _crc in vendor_only_requirements}),
            "bytes": len(requirements_text.encode("ascii")),
            "sha256": hashlib.sha256(requirements_text.encode("ascii")).hexdigest(),
        },
        "verified_vendor_dlkm_corpus": verified,
        "interpretation": (
            "all overlapping vendor_dlkm/vendor-ramdisk modules are byte-identical; vendor_dlkm-only modules are separately inventoried"
            if verified
            else "vendor_dlkm differs from the pinned vendor-ramdisk corpus"
        ),
        "safety": {
            "device_contact": False,
            "mount": False,
            "source_filesystem_write": False,
            "host_output_write": True,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }
    expected_outputs = {
        "inventory.tsv",
        "manifest.json",
        "vendor-dlkm-only-symbol-crc-requirements.tsv",
    }
    stale = [path.name for path in out_dir.iterdir() if path.is_file() and path.name not in expected_outputs]
    if stale:
        raise CorpusError(f"refusing to leave stale corpus outputs: {sorted(stale)}")
    (out_dir / "inventory.tsv").write_text(inventory, encoding="ascii")
    (out_dir / "vendor-dlkm-only-symbol-crc-requirements.tsv").write_text(
        requirements_text, encoding="ascii"
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--dump-f2fs", type=Path, default=DEFAULT_DUMP_F2FS)
    parser.add_argument("--module-dir", type=PurePosixPath, default=PurePosixPath("/lib/modules"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    manifest = build_corpus(
        root,
        resolve(root, args.image),
        absolute_without_symlink_resolution(root, args.dump_f2fs),
        resolve(root, args.reference_dir),
        args.module_dir,
        resolve(root, args.out),
    )
    print(json.dumps({
        "result": "pass" if manifest["verified_vendor_dlkm_corpus"] else "fail",
        "vendor_dlkm_modules": manifest["counts"]["vendor_dlkm_modules"],
        "byte_identical_modules": manifest["counts"]["byte_identical_modules"],
        "union_unique_module_names": manifest["counts"]["union_unique_module_names"],
        "out": display_path(root, resolve(root, args.out)),
    }, indent=2, sort_keys=True))
    return 0 if manifest["verified_vendor_dlkm_corpus"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CorpusError, OSError, struct.error) as exc:
        raise SystemExit(str(exc)) from exc
