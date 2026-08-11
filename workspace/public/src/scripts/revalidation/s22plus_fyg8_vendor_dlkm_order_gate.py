#!/usr/bin/env python3
"""Recover the FYG8 vendor_dlkm modules.load authority without materializing super.

This is a host-only, fail-closed extractor.  It authenticates the stock firmware
ZIP, streams the AP tar's ``super.img.lz4`` member through the pinned local lz4
binary, validates the complete Android sparse and expanded super identities,
and writes only the vendor_dlkm linear extent.  The resulting F2FS image is then
used to recover exactly ``/lib/modules/modules.load``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
import threading
import time
import zipfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from s22plus_fyg8_f2fs_module_corpus import (
    CorpusError,
    FILE_TYPE_REGULAR,
    F2FSReader,
    sha256_file,
)


SCHEMA = "s22plus_fyg8_vendor_dlkm_order_gate_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

DEFAULT_FIRMWARE_ZIP = Path(
    "workspace/private/inputs/firmware/"
    "SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac.zip"
)
DEFAULT_LZ4 = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")
DEFAULT_DUMP_F2FS = Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/order-authority-20260811-01"
)

AP_MEMBER = (
    "AP_S906NKSS7FYG8_S906NKSS7FYG8_MQB99315260_REV00_"
    "user_low_ship_MULTI_CERT_meta_OS15.tar.md5"
)
SUPER_MEMBER = "super.img.lz4"

EXPECTED_ZIP_SIZE = 9_680_091_538
EXPECTED_ZIP_SHA256 = "f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8"
EXPECTED_AP_SIZE = 11_499_653_242
EXPECTED_AP_COMPRESSED_SIZE = 9_481_821_857
EXPECTED_AP_CRC32 = 0x36EC7FF8
EXPECTED_SUPER_LZ4_SIZE = 8_875_694_170
EXPECTED_SPARSE_SUPER_SIZE = 10_352_130_812
EXPECTED_SPARSE_SUPER_SHA256 = "f418abff8cf0612d7c145d6f6de0ac6a13bbdd8b5a6458b5ae8c18f2bf8243c8"
EXPECTED_RAW_SUPER_SIZE = 12_475_957_248
EXPECTED_RAW_SUPER_SHA256 = "63061c093dce2e1f0a3df41bf0a960b72f221ecca8277c9f2fcc20a3e8e8f4ae"

VENDOR_DLKM_OFFSET = 20_248_576 * 512
VENDOR_DLKM_SIZE = 112_520 * 512
EXPECTED_VENDOR_DLKM_SHA256 = "e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26"
EXPECTED_MODULES_LOAD_INODE = 144
EXPECTED_MODULES_LOAD_SIZE = 5_843
EXPECTED_MODULES_LOAD_SHA256 = "8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360"

MIN_FREE_MARGIN = 1 << 30
COPY_SIZE = 4 << 20
MAX_SPARSE_HEADER_SIZE = 4096
MAX_TOOL_STDERR = 64 << 10

SPARSE_MAGIC = 0xED26FF3A
CHUNK_RAW = 0xCAC1
CHUNK_FILL = 0xCAC2
CHUNK_DONT_CARE = 0xCAC3
CHUNK_CRC32 = 0xCAC4


class GateError(ValueError):
    """A fail-closed Gate 0 validation failure."""


@dataclass(frozen=True)
class SparseRangeResult:
    major: int
    minor: int
    file_header_size: int
    chunk_header_size: int
    block_size: int
    total_blocks: int
    total_chunks: int
    image_checksum: int
    sparse_size: int
    sparse_sha256: str
    raw_size: int
    raw_sha256: str
    raw_crc32: int
    range_offset: int
    range_size: int
    range_sha256: str
    raw_chunks: int
    fill_chunks: int
    dont_care_chunks: int
    crc32_chunks: int


@dataclass
class ProducerState:
    member_size: int = 0
    member_sha256: str = ""
    error: BaseException | None = None


class CountingSha256:
    def __init__(self) -> None:
        self._digest = hashlib.sha256()
        self.size = 0

    def update(self, data: bytes) -> None:
        self._digest.update(data)
        self.size += len(data)

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise GateError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def absolute_without_symlink_resolution(root: Path, path: Path) -> Path:
    return path.absolute() if path.is_absolute() else (root / path).absolute()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def display_path_without_symlink_resolution(root: Path, path: Path) -> str:
    absolute = path.absolute()
    try:
        return str(absolute.relative_to(root.absolute()))
    except ValueError:
        return str(absolute)


def direct_regular_file(path: Path, label: str, *, allow_symlink: bool = False) -> Path:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise GateError(f"{label} is missing: {path}") from exc
    if stat.S_ISLNK(mode):
        if not allow_symlink:
            raise GateError(f"{label} symlink refused: {path}")
        target = path.resolve()
        if not target.is_file():
            raise GateError(f"{label} symlink target is not a regular file: {path}")
        return target
    if not stat.S_ISREG(mode):
        raise GateError(f"{label} is not a regular file: {path}")
    return path.resolve()


def read_exact(stream: BinaryIO, size: int, digest: Any | None = None) -> bytes:
    if size < 0:
        raise GateError("negative stream read")
    output = bytearray()
    while len(output) < size:
        data = stream.read(size - len(output))
        if not data:
            raise GateError(f"truncated stream: {len(output)} != {size}")
        output.extend(data)
        if digest is not None:
            digest.update(data)
    return bytes(output)


def repeated_bytes(pattern: bytes, size: int) -> bytes:
    if not pattern or size < 0 or size > COPY_SIZE:
        raise GateError("invalid repeated-byte request")
    repeat, tail = divmod(size, len(pattern))
    return pattern * repeat + pattern[:tail]


def update_repeated(
    digest: Any,
    crc: int,
    pattern: bytes,
    size: int,
    *,
    calculate_crc: bool,
) -> int:
    chunk = repeated_bytes(pattern, min(COPY_SIZE, max(len(pattern), size))) if size else b""
    remaining = size
    while remaining:
        data = chunk[:min(len(chunk), remaining)]
        digest.update(data)
        if calculate_crc:
            crc = zlib.crc32(data, crc)
        remaining -= len(data)
    return crc


def write_repeated(output: BinaryIO, pattern: bytes, size: int) -> None:
    chunk = repeated_bytes(pattern, min(COPY_SIZE, max(len(pattern), size))) if size else b""
    remaining = size
    while remaining:
        data = chunk[:min(len(chunk), remaining)]
        output.write(data)
        remaining -= len(data)


def overlap(start: int, size: int, wanted_start: int, wanted_size: int) -> tuple[int, int] | None:
    end = start + size
    wanted_end = wanted_start + wanted_size
    left = max(start, wanted_start)
    right = min(end, wanted_end)
    return None if left >= right else (left - start, right - left)


def extract_sparse_range(
    stream: BinaryIO,
    output: Path,
    *,
    range_offset: int,
    range_size: int,
    expected_sparse_size: int,
    expected_sparse_sha256: str,
    expected_raw_size: int,
    expected_raw_sha256: str,
    expected_range_sha256: str,
) -> SparseRangeResult:
    """Validate a complete sparse stream and materialize one expanded range."""

    if range_offset < 0 or range_size <= 0 or range_offset + range_size > expected_raw_size:
        raise GateError("requested sparse range is outside the expected raw image")
    if output.exists() or output.is_symlink():
        raise GateError(f"range output already exists: {output}")

    sparse_digest = CountingSha256()
    raw_digest = hashlib.sha256()
    header = read_exact(stream, 28, sparse_digest)
    (
        magic,
        major,
        minor,
        file_header_size,
        chunk_header_size,
        block_size,
        total_blocks,
        total_chunks,
        image_checksum,
    ) = struct.unpack("<IHHHHIIII", header)
    if magic != SPARSE_MAGIC:
        raise GateError(f"sparse magic mismatch: 0x{magic:08x}")
    if major != 1:
        raise GateError(f"unsupported sparse major version: {major}")
    if not 28 <= file_header_size <= MAX_SPARSE_HEADER_SIZE:
        raise GateError(f"invalid sparse file-header size: {file_header_size}")
    if not 12 <= chunk_header_size <= MAX_SPARSE_HEADER_SIZE:
        raise GateError(f"invalid sparse chunk-header size: {chunk_header_size}")
    if block_size < 4 or block_size % 4 or block_size & (block_size - 1):
        raise GateError(f"invalid sparse block size: {block_size}")
    if total_blocks * block_size != expected_raw_size:
        raise GateError(
            f"sparse raw-size declaration mismatch: {total_blocks * block_size} != {expected_raw_size}"
        )
    if range_offset % block_size or range_size % block_size:
        raise GateError("requested sparse range is not block aligned")
    if file_header_size > 28:
        read_exact(stream, file_header_size - 28, sparse_digest)

    calculate_crc = bool(image_checksum)
    raw_crc = 0
    logical_offset = 0
    output_written = 0
    counts = {CHUNK_RAW: 0, CHUNK_FILL: 0, CHUNK_DONT_CARE: 0, CHUNK_CRC32: 0}

    try:
        with output.open("xb", buffering=0) as target:
            for index in range(total_chunks):
                chunk = read_exact(stream, 12, sparse_digest)
                chunk_type, _reserved, chunk_blocks, total_size = struct.unpack("<HHII", chunk)
                if total_size < chunk_header_size:
                    raise GateError(f"sparse chunk {index} total size underflows its header")
                if chunk_type not in counts:
                    raise GateError(f"unsupported sparse chunk type at {index}: 0x{chunk_type:04x}")
                if chunk_header_size > 12:
                    read_exact(stream, chunk_header_size - 12, sparse_digest)
                data_size = total_size - chunk_header_size
                expanded_size = chunk_blocks * block_size
                current_overlap = overlap(
                    logical_offset, expanded_size, range_offset, range_size
                ) if chunk_type != CHUNK_CRC32 else None

                if chunk_type == CHUNK_RAW:
                    if data_size != expanded_size:
                        raise GateError(
                            f"raw sparse chunk {index} size mismatch: {data_size} != {expanded_size}"
                        )
                    consumed = 0
                    while consumed < data_size:
                        data = read_exact(
                            stream, min(COPY_SIZE, data_size - consumed), sparse_digest
                        )
                        raw_digest.update(data)
                        if calculate_crc:
                            raw_crc = zlib.crc32(data, raw_crc)
                        if current_overlap is not None:
                            relative, length = current_overlap
                            left = max(consumed, relative)
                            right = min(consumed + len(data), relative + length)
                            if left < right:
                                target.write(data[left - consumed:right - consumed])
                                output_written += right - left
                        consumed += len(data)
                elif chunk_type == CHUNK_FILL:
                    if data_size != 4:
                        raise GateError(f"fill sparse chunk {index} payload is not four bytes")
                    pattern = read_exact(stream, 4, sparse_digest)
                    raw_crc = update_repeated(
                        raw_digest, raw_crc, pattern, expanded_size, calculate_crc=calculate_crc
                    )
                    if current_overlap is not None:
                        relative, length = current_overlap
                        rotated = pattern[relative % len(pattern):] + pattern[:relative % len(pattern)]
                        write_repeated(target, rotated, length)
                        output_written += length
                elif chunk_type == CHUNK_DONT_CARE:
                    if data_size != 0:
                        raise GateError(f"don't-care sparse chunk {index} has a payload")
                    raw_crc = update_repeated(
                        raw_digest, raw_crc, b"\0", expanded_size, calculate_crc=calculate_crc
                    )
                    if current_overlap is not None:
                        _relative, length = current_overlap
                        write_repeated(target, b"\0", length)
                        output_written += length
                else:
                    if chunk_blocks != 0 or data_size != 4:
                        raise GateError(f"CRC32 sparse chunk {index} has invalid geometry")
                    stored_crc = struct.unpack("<I", read_exact(stream, 4, sparse_digest))[0]
                    if calculate_crc and stored_crc != raw_crc & 0xFFFFFFFF:
                        raise GateError(
                            f"CRC32 sparse chunk {index} mismatch: {stored_crc:#x} != {raw_crc & 0xFFFFFFFF:#x}"
                        )

                if chunk_type != CHUNK_CRC32:
                    logical_offset += expanded_size
                counts[chunk_type] += 1

            trailing = stream.read(1)
            if trailing:
                raise GateError("sparse stream has trailing bytes after declared chunks")
    except BaseException:
        output.unlink(missing_ok=True)
        raise

    sparse_size = sparse_digest.size
    sparse_sha256 = sparse_digest.hexdigest()
    raw_sha256 = raw_digest.hexdigest()
    if logical_offset != expected_raw_size:
        output.unlink(missing_ok=True)
        raise GateError(f"expanded sparse size mismatch: {logical_offset} != {expected_raw_size}")
    if sparse_size != expected_sparse_size:
        output.unlink(missing_ok=True)
        raise GateError(f"sparse super size mismatch: {sparse_size} != {expected_sparse_size}")
    if sparse_sha256 != expected_sparse_sha256:
        output.unlink(missing_ok=True)
        raise GateError(f"sparse super SHA-256 mismatch: {sparse_sha256}")
    if raw_sha256 != expected_raw_sha256:
        output.unlink(missing_ok=True)
        raise GateError(f"raw super SHA-256 mismatch: {raw_sha256}")
    if image_checksum and image_checksum != raw_crc & 0xFFFFFFFF:
        output.unlink(missing_ok=True)
        raise GateError(
            f"sparse image checksum mismatch: {image_checksum:#x} != {raw_crc & 0xFFFFFFFF:#x}"
        )
    if output_written != range_size or output.stat().st_size != range_size:
        output.unlink(missing_ok=True)
        raise GateError(
            f"extracted range size mismatch: {output_written}/{output.stat().st_size if output.exists() else 0} != {range_size}"
        )
    range_sha256 = sha256_file(output)
    if range_sha256 != expected_range_sha256:
        output.unlink(missing_ok=True)
        raise GateError(f"extracted range SHA-256 mismatch: {range_sha256}")
    output.chmod(0o600)

    return SparseRangeResult(
        major=major,
        minor=minor,
        file_header_size=file_header_size,
        chunk_header_size=chunk_header_size,
        block_size=block_size,
        total_blocks=total_blocks,
        total_chunks=total_chunks,
        image_checksum=image_checksum,
        sparse_size=sparse_size,
        sparse_sha256=sparse_sha256,
        raw_size=logical_offset,
        raw_sha256=raw_sha256,
        raw_crc32=raw_crc & 0xFFFFFFFF,
        range_offset=range_offset,
        range_size=range_size,
        range_sha256=range_sha256,
        raw_chunks=counts[CHUNK_RAW],
        fill_chunks=counts[CHUNK_FILL],
        dont_care_chunks=counts[CHUNK_DONT_CARE],
        crc32_chunks=counts[CHUNK_CRC32],
    )


def validate_zip(path: Path) -> zipfile.ZipInfo:
    if path.stat().st_size != EXPECTED_ZIP_SIZE:
        raise GateError(f"firmware ZIP size mismatch: {path.stat().st_size}")
    digest = sha256_file(path)
    if digest != EXPECTED_ZIP_SHA256:
        raise GateError(f"firmware ZIP SHA-256 mismatch: {digest}")
    with zipfile.ZipFile(path) as archive:
        matches = [item for item in archive.infolist() if item.filename == AP_MEMBER]
        if len(matches) != 1:
            raise GateError(f"AP member count mismatch: {len(matches)}")
        info = matches[0]
        if info.flag_bits & 0x1:
            raise GateError("encrypted AP member refused")
        if (
            info.file_size != EXPECTED_AP_SIZE
            or info.compress_size != EXPECTED_AP_COMPRESSED_SIZE
            or info.CRC != EXPECTED_AP_CRC32
        ):
            raise GateError("AP member size/compressed-size/CRC authority mismatch")
        return info


def feed_super_member(
    zip_path: Path,
    state: ProducerState,
    destination: BinaryIO,
) -> None:
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(zip_path) as archive, archive.open(AP_MEMBER) as ap_stream:
            with tarfile.open(fileobj=ap_stream, mode="r|") as tar:
                found = False
                for member in tar:
                    if member.name != SUPER_MEMBER:
                        continue
                    if found:
                        raise GateError("duplicate super.img.lz4 member")
                    found = True
                    if not member.isfile() or member.size != EXPECTED_SUPER_LZ4_SIZE:
                        raise GateError("super.img.lz4 type or size mismatch")
                    source = tar.extractfile(member)
                    if source is None:
                        raise GateError("cannot open super.img.lz4 tar member")
                    while True:
                        data = source.read(COPY_SIZE)
                        if not data:
                            break
                        destination.write(data)
                        digest.update(data)
                        state.member_size += len(data)
                    break
                if not found:
                    raise GateError("super.img.lz4 tar member not found")
        if state.member_size != EXPECTED_SUPER_LZ4_SIZE:
            raise GateError(
                f"super.img.lz4 streamed size mismatch: {state.member_size}"
            )
        state.member_sha256 = digest.hexdigest()
    except BaseException as exc:  # delivered to the consuming thread after join
        state.error = exc
    finally:
        try:
            destination.close()
        except (BrokenPipeError, OSError):
            pass


def stream_super_and_extract_range(
    zip_path: Path,
    lz4_bin: Path,
    output: Path,
    stderr_path: Path,
) -> tuple[SparseRangeResult, ProducerState, int]:
    state = ProducerState()
    with stderr_path.open("xb") as stderr:
        process = subprocess.Popen(
            [str(lz4_bin), "-d", "-c"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            raise GateError("cannot create lz4 stream pipes")
        producer = threading.Thread(
            target=feed_super_member,
            args=(zip_path, state, process.stdin),
            name="fyg8-super-member-feed",
            daemon=True,
        )
        producer.start()
        try:
            result = extract_sparse_range(
                process.stdout,
                output,
                range_offset=VENDOR_DLKM_OFFSET,
                range_size=VENDOR_DLKM_SIZE,
                expected_sparse_size=EXPECTED_SPARSE_SUPER_SIZE,
                expected_sparse_sha256=EXPECTED_SPARSE_SUPER_SHA256,
                expected_raw_size=EXPECTED_RAW_SUPER_SIZE,
                expected_raw_sha256=EXPECTED_RAW_SUPER_SHA256,
                expected_range_sha256=EXPECTED_VENDOR_DLKM_SHA256,
            )
        except BaseException:
            process.terminate()
            process.stdout.close()
            producer.join(timeout=30)
            if producer.is_alive():
                process.kill()
                producer.join(timeout=5)
            process.wait(timeout=10)
            raise
        finally:
            process.stdout.close()
        producer.join(timeout=60)
        if producer.is_alive():
            process.kill()
            process.wait(timeout=10)
            output.unlink(missing_ok=True)
            raise GateError("super.img.lz4 producer did not terminate")
        returncode = process.wait(timeout=60)
    if state.error is not None:
        output.unlink(missing_ok=True)
        raise GateError(f"super.img.lz4 producer failed: {state.error}") from state.error
    if returncode != 0:
        output.unlink(missing_ok=True)
        tail = stderr_path.read_bytes()[-MAX_TOOL_STDERR:].decode("utf-8", errors="replace")
        raise GateError(f"lz4 decompression failed rc={returncode}: {tail}")
    stderr_path.chmod(0o600)
    return result, state, returncode


def validate_modules_load_data(data: bytes) -> tuple[str, ...]:
    if len(data) != EXPECTED_MODULES_LOAD_SIZE:
        raise GateError(f"modules.load extracted size mismatch: {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_MODULES_LOAD_SHA256:
        raise GateError(f"modules.load SHA-256 mismatch: {digest}")
    if not data.endswith(b"\n") or b"\r" in data or b"\0" in data:
        raise GateError("modules.load has invalid line termination")
    try:
        lines = tuple(data.decode("ascii").splitlines())
    except UnicodeDecodeError as exc:
        raise GateError("modules.load is not ASCII") from exc
    if not lines or len(lines) != len(set(lines)):
        raise GateError("modules.load is empty or contains duplicate lines")
    if any(not line.endswith(".ko") or PurePosixPath(line).name != line for line in lines):
        raise GateError("modules.load contains a non-basename module entry")
    return lines


def recover_modules_load(image: Path, dump_f2fs: Path, output: Path) -> dict[str, Any]:
    reader = F2FSReader(image, dump_f2fs)
    modules_inode = reader.resolve_directory(PurePosixPath("/lib/modules"))
    matches = [entry for entry in reader.directory(modules_inode) if entry.name == "modules.load"]
    if len(matches) != 1 or matches[0].file_type != FILE_TYPE_REGULAR:
        raise GateError(f"modules.load F2FS dentry mismatch: {len(matches)}")
    entry = matches[0]
    if entry.inode != EXPECTED_MODULES_LOAD_INODE:
        raise GateError(f"modules.load inode mismatch: {entry.inode}")
    info = reader.inode_info(entry.inode)
    if info.size != EXPECTED_MODULES_LOAD_SIZE:
        raise GateError(f"modules.load inode size mismatch: {info.size}")
    data = reader.read_file(info)
    digest = hashlib.sha256(data).hexdigest()
    lines = validate_modules_load_data(data)
    output.write_bytes(data)
    output.chmod(0o600)
    return {
        "path": output.name,
        "inode": entry.inode,
        "size": len(data),
        "sha256": digest,
        "line_count": len(lines),
        "unique_line_count": len(set(lines)),
        "first_line": lines[0],
        "last_line": lines[-1],
    }


def check_output_parent(root: Path, output: Path) -> Path:
    private_root = (root / "workspace/private").resolve()
    absolute = output if output.is_absolute() else (root / output).absolute()
    try:
        absolute.relative_to(private_root)
    except ValueError as exc:
        raise GateError(f"output must remain under workspace/private: {absolute}") from exc
    parent = absolute.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise GateError(f"output parent is not a direct directory: {parent}")
    if absolute.exists() or absolute.is_symlink():
        raise GateError(f"output directory already exists: {absolute}")
    return absolute


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    firmware_zip = direct_regular_file(resolve(root, args.firmware_zip), "firmware ZIP")
    lz4_bin = direct_regular_file(resolve(root, args.lz4), "lz4 binary")
    # f2fs-tools is a multicall binary.  The basename "dump.f2fs" selects the
    # read-only dump mode, so resolving its symlink to "fsck.f2fs" changes the
    # operation rather than merely canonicalizing a path.
    dump_argument = absolute_without_symlink_resolution(root, args.dump_f2fs)
    direct_regular_file(dump_argument, "dump.f2fs", allow_symlink=True)
    output = check_output_parent(root, args.output)

    needed = VENDOR_DLKM_SIZE + MIN_FREE_MARGIN
    available = shutil.disk_usage(output.parent).free
    if available < needed:
        raise GateError(f"insufficient free space: {available} < {needed}")

    started = time.time()
    validate_zip(firmware_zip)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.partial-", dir=output.parent))
    try:
        image = temporary / "vendor_dlkm.img"
        stderr_path = temporary / "lz4.stderr"
        sparse, producer, lz4_returncode = stream_super_and_extract_range(
            firmware_zip, lz4_bin, image, stderr_path
        )
        modules = recover_modules_load(
            image, dump_argument, temporary / "modules.load"
        )
        result = {
            "schema": SCHEMA,
            "target": TARGET,
            "host_only": True,
            "device_contact": False,
            "started_unix": started,
            "completed_unix": time.time(),
            "inputs": {
                "firmware_zip": {
                    "path": display_path(root, firmware_zip),
                    "size": firmware_zip.stat().st_size,
                    "sha256": EXPECTED_ZIP_SHA256,
                },
                "ap_member": {
                    "name": AP_MEMBER,
                    "size": EXPECTED_AP_SIZE,
                    "compressed_size": EXPECTED_AP_COMPRESSED_SIZE,
                    "crc32": f"{EXPECTED_AP_CRC32:08x}",
                },
                "super_lz4_member": {
                    "name": SUPER_MEMBER,
                    "size": producer.member_size,
                    "sha256": producer.member_sha256,
                },
                "lz4": {
                    "path": display_path(root, lz4_bin),
                    "size": lz4_bin.stat().st_size,
                    "sha256": sha256_file(lz4_bin),
                    "returncode": lz4_returncode,
                    "stderr_size": stderr_path.stat().st_size,
                },
                "dump_f2fs": {
                    "path": display_path_without_symlink_resolution(root, dump_argument),
                    "resolved_path": display_path(root, dump_argument.resolve()),
                    "multicall_basename": dump_argument.name,
                    "sha256": sha256_file(dump_argument),
                },
            },
            "space_preflight": {
                "available_bytes": available,
                "range_output_bytes": VENDOR_DLKM_SIZE,
                "explicit_margin_bytes": MIN_FREE_MARGIN,
                "required_bytes": needed,
            },
            "sparse_range": asdict(sparse),
            "vendor_dlkm": {
                "path": image.name,
                "offset_in_raw_super": VENDOR_DLKM_OFFSET,
                "size": image.stat().st_size,
                "sha256": sha256_file(image),
            },
            "modules_load": modules,
            "publication": {
                "atomic_directory_rename": True,
                "partial_output_published": False,
                "expected_output": display_path(root, output),
            },
        }
        result_path = temporary / "result.json"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
        result_path.chmod(0o600)
        os.replace(temporary, output)
        return result
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware-zip", type=Path, default=DEFAULT_FIRMWARE_ZIP)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--dump-f2fs", type=Path, default=DEFAULT_DUMP_F2FS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    try:
        result = run(parse_args())
    except (
        CorpusError,
        GateError,
        OSError,
        subprocess.SubprocessError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
