#!/usr/bin/env python3
"""Build the host-only FYG8 R3C0 minimal signer-normalized control.

The builder starts from the exact stock boot image and changes only the
Samsung signer tail plus the AVB footer original-image-size field. The pinned
MagiskBoot binary is provenance for the 16-byte marker behavior, not the image
generator: a real no-change MagiskBoot repack recompresses the stock ramdisk
and is therefore not the R3C0 minimal differential. The builder creates a
deterministic boot-only Odin AP and runs Odin only against a fixed nonexistent
USB path. It never contacts, reboots, or flashes a device.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r3c0_control_build_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SEANDROID_MAGIC = b"SEANDROIDENFORCE"
BOOT_SIZE = 100_663_296
SIGNER_START = 43_483_136
SIGNER_END = 43_483_664
FOOTER_START = 100_663_232
KERNEL_START = 4_096
KERNEL_END = 41_495_040
RAMDISK_START = 41_496_576
RAMDISK_END = 43_475_543
VBMETA_START = 43_487_232
VBMETA_END = 43_489_344
INVALID_ODIN_DEVICE = "/dev/bus/usb/999/999"

EXPECTED_STOCK_BOOT_SHA256 = "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
EXPECTED_STOCK_KERNEL_SHA256 = "027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d"
EXPECTED_STOCK_RAMDISK_SHA256 = "0cb87ca46b876a8765fed95bb0ce047485a14d2ec76de95af4680423b3ed1443"
EXPECTED_STOCK_VBMETA_SHA256 = "2128d4fa64fdbed386f8cf628e1df89b1161a60a59aec985bb28a5770873561d"
EXPECTED_MAGISKBOOT_SIZE = 943_848
EXPECTED_MAGISKBOOT_SHA256 = "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
EXPECTED_LZ4_SIZE = 218_696
EXPECTED_LZ4_SHA256 = "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
EXPECTED_ODIN_SIZE = 3_746_744
EXPECTED_ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"

DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a")
DEFAULT_STOCK_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/boot.img"
)
DEFAULT_MAGISKBOOT = Path("workspace/private/tools/magisk-v30.7/magiskboot")
DEFAULT_LZ4 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
DEFAULT_ODIN = Path("/usr/bin/odin4")


class BuildError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_pinned(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BuildError(f"{label} missing or not a direct regular file: {path}")
    if path.stat().st_size != size:
        raise BuildError(f"{label} size mismatch: {path.stat().st_size} != {size}")
    actual = sha256_file(path)
    if actual != sha256:
        raise BuildError(f"{label} SHA256 mismatch: {actual}")
    return {"size": size, "sha256": actual}


def run(argv: list[str | Path], *, cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], label: str) -> str:
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise BuildError(f"{label} failed rc={result.returncode}: {output}")
    return output


def expected_control_bytes(stock: bytes) -> bytes:
    if len(stock) != BOOT_SIZE:
        raise BuildError(f"stock boot size mismatch: {len(stock)}")
    if stock[SIGNER_START : SIGNER_START + len(SEANDROID_MAGIC)] != SEANDROID_MAGIC:
        raise BuildError("stock SEANDROID marker mismatch")
    expected = bytearray(stock)
    marker_end = SIGNER_START + len(SEANDROID_MAGIC)
    expected[marker_end:SIGNER_END] = bytes(SIGNER_END - marker_end)
    struct.pack_into("!Q", expected, FOOTER_START + 12, marker_end)
    return bytes(expected)


def changed_ranges(before: bytes, after: bytes) -> list[dict[str, int]]:
    if len(before) != len(after):
        raise BuildError("cannot diff images of unequal size")
    ranges: list[dict[str, int]] = []
    start: int | None = None
    for offset, (left, right) in enumerate(zip(before, after)):
        if left != right and start is None:
            start = offset
        elif left == right and start is not None:
            ranges.append({"start": start, "end_exclusive": offset, "length": offset - start})
            start = None
    if start is not None:
        ranges.append({"start": start, "end_exclusive": len(before), "length": len(before) - start})
    return ranges


def write_deterministic_ap(boot_lz4: Path, ap_path: Path) -> dict[str, Any]:
    payload = boot_lz4.read_bytes()
    with ap_path.open("wb") as output:
        with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("boot.img.lz4")
            info.size = len(payload)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(payload))
    tar_size = ap_path.stat().st_size
    tar_md5 = hashlib.md5(ap_path.read_bytes()).hexdigest()
    with ap_path.open("ab") as output:
        output.write(f"{tar_md5}  AP.tar\n".encode("ascii"))
    return {
        "tar_prefix_size": tar_size,
        "tar_md5": tar_md5,
        "trailer": f"{tar_md5}  AP.tar\\n",
        "members": ["boot.img.lz4"],
    }


def run_odin_invalid_device_gate(odin: Path, ap_path: Path) -> dict[str, Any]:
    result = run([odin, "-a", ap_path, "-d", INVALID_ODIN_DEVICE], timeout=30)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    required = ("Check file :", INVALID_ODIN_DEVICE, "No such file or directory", "usb device Fail")
    missing = [marker for marker in required if marker not in output]
    if result.returncode != 1 or missing:
        raise BuildError(f"unexpected Odin invalid-device parse gate rc={result.returncode} missing={missing}: {output}")
    return {
        "returncode": result.returncode,
        "invalid_device": INVALID_ODIN_DEVICE,
        "ap_recognized": True,
        "failed_before_device_open": True,
        "required_markers_present": True,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    out = resolve(root, args.out)
    stock_path = resolve(root, args.stock_boot)
    magiskboot = resolve(root, args.magiskboot)
    lz4 = resolve(root, args.lz4)
    odin = resolve(root, args.odin)
    if out.exists():
        raise BuildError(f"output path already exists: {out}")
    if os.environ.get("PATCHVBMETAFLAG"):
        raise BuildError("PATCHVBMETAFLAG must be unset for R3C0")

    input_pins = {
        "stock_boot": require_pinned(stock_path, BOOT_SIZE, EXPECTED_STOCK_BOOT_SHA256, "stock boot"),
        "magiskboot_provenance": require_pinned(
            magiskboot, EXPECTED_MAGISKBOOT_SIZE, EXPECTED_MAGISKBOOT_SHA256, "magiskboot provenance"
        ),
        "lz4": require_pinned(lz4, EXPECTED_LZ4_SIZE, EXPECTED_LZ4_SHA256, "lz4"),
        "odin": require_pinned(odin, EXPECTED_ODIN_SIZE, EXPECTED_ODIN_SHA256, "odin4"),
    }
    stock = stock_path.read_bytes()
    expected = expected_control_bytes(stock)
    if sha256_bytes(stock[KERNEL_START:KERNEL_END]) != EXPECTED_STOCK_KERNEL_SHA256:
        raise BuildError("stock kernel slice SHA256 mismatch")
    if sha256_bytes(stock[RAMDISK_START:RAMDISK_END]) != EXPECTED_STOCK_RAMDISK_SHA256:
        raise BuildError("stock ramdisk slice SHA256 mismatch")
    if sha256_bytes(stock[VBMETA_START:VBMETA_END]) != EXPECTED_STOCK_VBMETA_SHA256:
        raise BuildError("stock vbmeta slice SHA256 mismatch")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{out.name}.", dir=out.parent) as temporary:
        staging = Path(temporary)
        odin_dir = staging / "odin4"
        odin_dir.mkdir()

        boot_path = staging / "boot.img"
        boot_path.write_bytes(expected)
        control = boot_path.read_bytes()
        if control != expected:
            raise BuildError("staged R3C0 bytes changed after write")

        boot_lz4 = odin_dir / "boot.img.lz4"
        require_ok(run([lz4, "--content-size", "-B6", "-f", "-q", boot_path, boot_lz4]), "LZ4 compression")
        roundtrip = staging / "lz4-roundtrip.img"
        require_ok(run([lz4, "-d", "-f", "-q", boot_lz4, roundtrip]), "LZ4 roundtrip")
        if sha256_file(roundtrip) != sha256_file(boot_path):
            raise BuildError("LZ4 roundtrip raw boot mismatch")
        roundtrip.unlink()

        ap_path = odin_dir / "AP.tar.md5"
        ap_structure = write_deterministic_ap(boot_lz4, ap_path)
        odin_gate = run_odin_invalid_device_gate(odin, ap_path)
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(
            json.dumps(odin_gate, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )

        hashes = {
            "boot_img": sha256_file(boot_path),
            "boot_img_lz4": sha256_file(boot_lz4),
            "ap_tar_md5": sha256_file(ap_path),
            "kernel": sha256_bytes(control[KERNEL_START:KERNEL_END]),
            "ramdisk": sha256_bytes(control[RAMDISK_START:RAMDISK_END]),
            "vbmeta": sha256_bytes(control[VBMETA_START:VBMETA_END]),
        }
        sizes = {
            "boot_img": boot_path.stat().st_size,
            "boot_img_lz4": boot_lz4.stat().st_size,
            "ap_tar_md5": ap_path.stat().st_size,
        }
        manifest = {
            "schema": SCHEMA,
            "target": TARGET,
            "purpose": "R3C0 minimal signer-normalized stock-kernel and stock-ramdisk carrier control",
            "inputs": input_pins,
            "construction": {
                "tool": "direct fixed-offset transformation of pinned stock boot",
                "normalization_reference": "pinned MagiskBoot v30.7 16-byte Samsung marker behavior",
                "magiskboot_executed": False,
                "patch_vbmeta_flag": False,
                "exact_expected_normalization": True,
                "stock_kernel_preserved": hashes["kernel"] == EXPECTED_STOCK_KERNEL_SHA256,
                "stock_ramdisk_preserved": hashes["ramdisk"] == EXPECTED_STOCK_RAMDISK_SHA256,
                "stock_vbmeta_preserved": hashes["vbmeta"] == EXPECTED_STOCK_VBMETA_SHA256,
                "allowed_regions": ["samsung_signer_normalization", "avb_footer_original_image_size"],
                "stock_to_control_changed_ranges": changed_ranges(stock, control),
            },
            "artifacts": {"hashes": hashes, "sizes": sizes, "ap": ap_structure},
            "odin_invalid_device_parse_gate": odin_gate,
            "safety": {
                "host_only": True,
                "boot_only_ap": True,
                "ap_members": ["boot.img.lz4"],
                "device_contact": False,
                "usb_enumeration": False,
                "odin_transfer": False,
                "flash": False,
                "live_authorized": False,
                "r3c1_authorized": False,
            },
            "verdict": "PASS_R3C0_ARTIFACT_BUILT_HOST_ONLY",
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
        os.replace(staging, out)
        return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stock-boot", type=Path, default=DEFAULT_STOCK_BOOT)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = build(args)
    except (BuildError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({
        "schema": SCHEMA,
        "verdict": manifest["verdict"],
        "boot_sha256": manifest["artifacts"]["hashes"]["boot_img"],
        "ap_sha256": manifest["artifacts"]["hashes"]["ap_tar_md5"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
