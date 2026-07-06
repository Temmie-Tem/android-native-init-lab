#!/usr/bin/env python3
"""Build the S22+ direct-PID1 P3 first-light boot candidate.

Host-only.  This script builds a boot-only Odin AP containing exactly
`boot.img.lz4`; it does not reboot, flash, or touch a connected device.

The LZ4 frame writer intentionally stores raw blocks in a valid LZ4 frame with
content-size metadata.  This avoids depending on a host `lz4` binary while
preserving the package shape Odin4 accepted in the previous S22+ units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/direct_p3_v0_1")
DEFAULT_STOCK_ROOT = Path("workspace/private/outputs/s22plus_native_init/chainload_v0_2/verify-root")
DEFAULT_MKBOOTIMG_ARGS = Path("workspace/private/outputs/s22plus_native_init/repack_nochange/mkbootimg.args0")
DEFAULT_KERNEL = Path("workspace/private/outputs/s22plus_native_init/repack_nochange/unpack/kernel")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_direct_p3.c")
DEFAULT_MKBOOTIMG = Path("workspace/public/src/third_party/mkbootimg/mkbootimg.py")
DEFAULT_ODIN = Path("/usr/bin/odin4")
BOOT_PARTITION_SIZE = 100_663_296
EXPECTED_STOCK_KERNEL_SHA256 = "027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d"
MARKER = "S22_NATIVE_INIT_DIRECT_P3"


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run(argv: list[str | Path], *, cwd: Path | None = None, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(arg) for arg in argv],
        cwd=str(cwd) if cwd else None,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], context: str) -> None:
    if result.returncode != 0:
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise SystemExit(f"{context} failed rc={result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - Samsung Odin tar.md5 trailer compatibility only.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rotl32(value: int, count: int) -> int:
    value &= 0xFFFFFFFF
    return ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def xxh32(data: bytes, seed: int = 0) -> int:
    prime1 = 0x9E3779B1
    prime2 = 0x85EBCA77
    prime3 = 0xC2B2AE3D
    prime4 = 0x27D4EB2F
    prime5 = 0x165667B1

    def round_acc(acc: int, lane: int) -> int:
        acc = (acc + lane * prime2) & 0xFFFFFFFF
        acc = rotl32(acc, 13)
        return (acc * prime1) & 0xFFFFFFFF

    offset = 0
    length = len(data)
    if length >= 16:
        v1 = (seed + prime1 + prime2) & 0xFFFFFFFF
        v2 = (seed + prime2) & 0xFFFFFFFF
        v3 = seed & 0xFFFFFFFF
        v4 = (seed - prime1) & 0xFFFFFFFF
        limit = length - 16
        while offset <= limit:
            v1 = round_acc(v1, struct.unpack_from("<I", data, offset)[0])
            offset += 4
            v2 = round_acc(v2, struct.unpack_from("<I", data, offset)[0])
            offset += 4
            v3 = round_acc(v3, struct.unpack_from("<I", data, offset)[0])
            offset += 4
            v4 = round_acc(v4, struct.unpack_from("<I", data, offset)[0])
            offset += 4
        h32 = (rotl32(v1, 1) + rotl32(v2, 7) + rotl32(v3, 12) + rotl32(v4, 18)) & 0xFFFFFFFF
    else:
        h32 = (seed + prime5) & 0xFFFFFFFF

    h32 = (h32 + length) & 0xFFFFFFFF
    while offset + 4 <= length:
        h32 = (h32 + struct.unpack_from("<I", data, offset)[0] * prime3) & 0xFFFFFFFF
        h32 = (rotl32(h32, 17) * prime4) & 0xFFFFFFFF
        offset += 4
    while offset < length:
        h32 = (h32 + data[offset] * prime5) & 0xFFFFFFFF
        h32 = (rotl32(h32, 11) * prime1) & 0xFFFFFFFF
        offset += 1
    h32 ^= h32 >> 15
    h32 = (h32 * prime2) & 0xFFFFFFFF
    h32 ^= h32 >> 13
    h32 = (h32 * prime3) & 0xFFFFFFFF
    h32 ^= h32 >> 16
    return h32 & 0xFFFFFFFF


def lz4_frame_store(data: bytes, block_size: int = 1 << 20) -> bytes:
    if block_size != 1 << 20:
        raise ValueError("this builder intentionally uses LZ4 block size code B6")
    flg = 0x68  # version=01, block independence, content size present.
    bd = 0x60  # max block size code 6 == 1 MiB.
    descriptor = bytes([flg, bd]) + struct.pack("<Q", len(data))
    header_checksum = (xxh32(descriptor) >> 8) & 0xFF
    out = bytearray(b"\x04\x22\x4d\x18")
    out.extend(descriptor)
    out.append(header_checksum)
    for offset in range(0, len(data), block_size):
        chunk = data[offset : offset + block_size]
        out.extend(struct.pack("<I", len(chunk) | 0x80000000))
        out.extend(chunk)
    out.extend(b"\x00\x00\x00\x00")
    return bytes(out)


def lz4_frame_store_decode(frame: bytes) -> bytes:
    if not frame.startswith(b"\x04\x22\x4d\x18"):
        raise ValueError("bad LZ4 frame magic")
    pos = 4
    flg = frame[pos]
    bd = frame[pos + 1]
    pos += 2
    if flg != 0x68 or bd != 0x60:
        raise ValueError(f"unexpected descriptor flg=0x{flg:02x} bd=0x{bd:02x}")
    expected_size = struct.unpack_from("<Q", frame, pos)[0]
    pos += 8
    descriptor = bytes([flg, bd]) + struct.pack("<Q", expected_size)
    expected_hc = (xxh32(descriptor) >> 8) & 0xFF
    actual_hc = frame[pos]
    pos += 1
    if actual_hc != expected_hc:
        raise ValueError("bad LZ4 header checksum")
    out = bytearray()
    while True:
        block_len = struct.unpack_from("<I", frame, pos)[0]
        pos += 4
        if block_len == 0:
            break
        if (block_len & 0x80000000) == 0:
            raise ValueError("compressed block found in store-only frame")
        raw_len = block_len & 0x7FFFFFFF
        out.extend(frame[pos : pos + raw_len])
        pos += raw_len
    if len(out) != expected_size:
        raise ValueError(f"decoded size mismatch {len(out)} != {expected_size}")
    return bytes(out)


def parse_null_args(path: Path) -> list[str]:
    raw = path.read_bytes()
    parts = raw.split(b"\0")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return [part.decode("utf-8") for part in parts]


def replace_mkbootimg_arg(args: list[str], flag: str, value: Path | str) -> list[str]:
    out: list[str] = []
    idx = 0
    replaced = False
    while idx < len(args):
        if args[idx] == flag:
            out.extend([flag, str(value)])
            idx += 2
            replaced = True
        else:
            out.append(args[idx])
            idx += 1
    if not replaced:
        out.extend([flag, str(value)])
    return out


def copy_stock_ramdisk_root(source_root: Path, target_root: Path, direct_init: Path) -> None:
    shutil.copytree(source_root, target_root, symlinks=True)
    existing_init = target_root / "init"
    if existing_init.exists() or existing_init.is_symlink():
        existing_init.unlink()
    shutil.copy2(direct_init, existing_init)
    existing_init.chmod(0o750)


def normalize_tree_metadata(root_dir: Path) -> None:
    for path in sorted(root_dir.rglob("*")):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(root_dir, (0, 0), follow_symlinks=False)


def pack_cpio(root_dir: Path, out_cpio: Path) -> None:
    command = "find . -print0 | LC_ALL=C sort -z | cpio --null --reproducible -o -H newc --owner=0:0"
    with out_cpio.open("wb") as handle:
        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(root_dir),
            stdout=handle,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise SystemExit(result.stderr.decode("utf-8", errors="replace"))
    (out_cpio.with_suffix(out_cpio.suffix + ".stderr")).write_bytes(result.stderr)


def pad_file(src: Path, dst: Path, size: int) -> None:
    data_size = src.stat().st_size
    if data_size > size:
        raise SystemExit(f"{src} is larger than target partition size: {data_size} > {size}")
    with src.open("rb") as inf, dst.open("wb") as outf:
        shutil.copyfileobj(inf, outf, length=1024 * 1024)
        outf.write(b"\0" * (size - data_size))


def write_boot_lz4(boot_img: Path, out_lz4: Path) -> None:
    data = boot_img.read_bytes()
    frame = lz4_frame_store(data)
    decoded = lz4_frame_store_decode(frame)
    if decoded != data:
        raise SystemExit("internal LZ4 store-frame roundtrip failed")
    out_lz4.write_bytes(frame)


def write_ap_tar(boot_lz4: Path, ap_tar: Path, ap_md5: Path) -> None:
    with tarfile.open(ap_tar, "w") as tar:
        info = tarfile.TarInfo("boot.img.lz4")
        payload = boot_lz4.read_bytes()
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        tar.addfile(info, fileobj=__import__("io").BytesIO(payload))
    trailer = f"{md5_file(ap_tar)}  AP.tar\n".encode("ascii")
    ap_md5.write_bytes(ap_tar.read_bytes() + trailer)


def tar_members(path: Path) -> list[str]:
    with tarfile.open(path) as tar:
        return [member.name for member in tar.getmembers()]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stock-ramdisk-root", type=Path, default=DEFAULT_STOCK_ROOT)
    parser.add_argument("--mkbootimg-args", type=Path, default=DEFAULT_MKBOOTIMG_ARGS)
    parser.add_argument("--kernel", type=Path, default=DEFAULT_KERNEL)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--mkbootimg", type=Path, default=DEFAULT_MKBOOTIMG)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    stock_root = resolve(root, args.stock_ramdisk_root)
    mkbootimg_args_path = resolve(root, args.mkbootimg_args)
    kernel = resolve(root, args.kernel)
    source = resolve(root, args.source)
    mkbootimg = resolve(root, args.mkbootimg)
    odin = resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    root_dir = out_dir / "root"
    odin_dir = out_dir / "odin4"
    build_dir.mkdir(parents=True)
    odin_dir.mkdir(parents=True)

    kernel_sha = sha256_file(kernel)
    if kernel_sha != EXPECTED_STOCK_KERNEL_SHA256:
        raise SystemExit(f"stock kernel SHA mismatch: {kernel_sha}")

    direct_init = build_dir / "s22plus_init_direct_p3"
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-static",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            direct_init,
            source,
        ]
    )
    require_ok(result, "compile direct init")
    strip = run(["aarch64-linux-gnu-strip", direct_init])
    require_ok(strip, "strip direct init")

    copy_stock_ramdisk_root(stock_root, root_dir, direct_init)
    normalize_tree_metadata(root_dir)
    required_init = (root_dir / "init").read_bytes()
    if MARKER.encode("ascii") not in required_init:
        raise SystemExit("direct init marker missing from installed /init")

    ramdisk_cpio = out_dir / "ramdisk_direct_p3.cpio"
    pack_cpio(root_dir, ramdisk_cpio)

    mkargs = parse_null_args(mkbootimg_args_path)
    mkargs = replace_mkbootimg_arg(mkargs, "--kernel", kernel)
    mkargs = replace_mkbootimg_arg(mkargs, "--ramdisk", ramdisk_cpio)
    boot_unpadded = out_dir / "boot_direct_p3_unpadded.img"
    boot_padded = out_dir / "boot.img"
    mkcmd = ["python3", mkbootimg, *mkargs, "--output", boot_unpadded]
    mk = run(mkcmd)
    require_ok(mk, "mkbootimg")
    pad_file(boot_unpadded, boot_padded, BOOT_PARTITION_SIZE)

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_padded, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"AP tar member mismatch: {members}")

    parse_gate_text = ""
    if not args.no_odin_parse_gate and odin.exists():
        gate = run([odin, "-a", ap_md5, "-d", "/dev/bus/usb/999/999"])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "source": sha256_file(source),
        "stock_kernel": kernel_sha,
        "direct_init": sha256_file(direct_init),
        "ramdisk_cpio": sha256_file(ramdisk_cpio),
        "boot_unpadded": sha256_file(boot_unpadded),
        "boot_img": sha256_file(boot_padded),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "direct_init": direct_init.stat().st_size,
        "ramdisk_cpio": ramdisk_cpio.stat().st_size,
        "boot_unpadded": boot_unpadded.stat().st_size,
        "boot_img": boot_padded.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "P3 direct PID1 first-light host-only candidate",
        "safety": {
            "boot_only": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": "recovery",
            "persistent_partition_mount": False,
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "stock_ramdisk_root": display_path(root, stock_root),
            "kernel": display_path(root, kernel),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_gate_text,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    (out_dir / "sizes.txt").write_text(
        "".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())),
        encoding="ascii",
    )
    (out_dir / "required_strings.txt").write_text(
        f"{MARKER}\nrecovery\nno_android_handoff=1\n",
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
