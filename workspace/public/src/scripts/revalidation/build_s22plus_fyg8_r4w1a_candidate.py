#!/usr/bin/env python3
"""Build the host-only FYG8 R4W1-A stock-Android positive-control candidate.

The builder starts from the exact, live-proven R3C0 raw boot bytes and replaces
only the fixed kernel region with the exact R4W1 Full-LTO Image. It preserves the
R3C0 ramdisk, signer normalization, vbmeta bytes, AVB footer, and all padding.
It creates a deterministic boot-only Odin AP and runs Odin only against a fixed
nonexistent USB path. It never enumerates, contacts, reboots, or flashes a
device and grants no live authorization.
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


SCHEMA = "s22plus_fyg8_r4w1a_candidate_build_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BOOT_SIZE = 100_663_296
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START
RAMDISK_START = 41_496_576
RAMDISK_END = 43_475_543
SIGNER_START = 43_483_136
SIGNER_END = 43_483_664
VBMETA_START = 43_487_232
VBMETA_END = 43_489_344
FOOTER_START = 100_663_232
INVALID_ODIN_DEVICE = "/dev/bus/usb/999/999"

EXPECTED_R3C0_BOOT_SHA256 = (
    "384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f"
)
EXPECTED_R3C0_MANIFEST_SIZE = 4_031
EXPECTED_R3C0_MANIFEST_SHA256 = (
    "febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0"
)
EXPECTED_R4W1_IMAGE_SHA256 = (
    "9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c"
)
R4W1_MARKER = b"[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|"
EXPECTED_STOCK_KERNEL_SHA256 = (
    "027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d"
)
EXPECTED_STOCK_RAMDISK_SHA256 = (
    "0cb87ca46b876a8765fed95bb0ce047485a14d2ec76de95af4680423b3ed1443"
)
EXPECTED_STOCK_VBMETA_SHA256 = (
    "2128d4fa64fdbed386f8cf628e1df89b1161a60a59aec985bb28a5770873561d"
)
EXPECTED_R3C0_SIGNER_SHA256 = (
    "a1217a3a4409ffe17750dd15bc242732bca762c9313c45f8672deb400c0c9b94"
)
EXPECTED_LZ4_SIZE = 218_696
EXPECTED_LZ4_SHA256 = (
    "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
)
EXPECTED_ODIN_SIZE = 3_746_744
EXPECTED_ODIN_SHA256 = (
    "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
)

DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-a")
DEFAULT_R3C0_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/boot.img"
)
DEFAULT_R3C0_MANIFEST = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/manifest.json"
)
DEFAULT_R4W1_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1/remote-g-artifacts-final/Image"
)
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


def read_pinned(path: Path, size: int, sha256: str, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise BuildError(f"{label} missing or not a direct regular file: {path}")
    data = path.read_bytes()
    if len(data) != size:
        raise BuildError(f"{label} size mismatch: {len(data)} != {size}")
    actual = sha256_bytes(data)
    if actual != sha256:
        raise BuildError(f"{label} SHA256 mismatch: {actual}")
    return {"size": size, "sha256": actual}, data


def run(
    argv: list[str | Path], *, cwd: Path | None = None, timeout: int = 120
) -> subprocess.CompletedProcess[bytes]:
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


def parse_arm64_header(kernel: bytes) -> tuple[int, ...]:
    if len(kernel) < 64:
        raise BuildError("kernel is too short for ARM64 Image header")
    fields = struct.unpack_from("<IIQQQQQQII", kernel, 0)
    if fields[8] != 0x644D5241:
        raise BuildError(f"kernel ARM64 magic mismatch: 0x{fields[8]:08x}")
    return fields


def verify_r3c0_manifest(path: Path) -> dict[str, Any]:
    pin, encoded = read_pinned(
        path,
        EXPECTED_R3C0_MANIFEST_SIZE,
        EXPECTED_R3C0_MANIFEST_SHA256,
        "R3C0 manifest",
    )
    data = json.loads(encoded.decode("utf-8"))
    if data.get("schema") != "s22plus_fyg8_r3c0_control_build_v1":
        raise BuildError("R3C0 manifest schema mismatch")
    if data.get("verdict") != "PASS_R3C0_ARTIFACT_BUILT_HOST_ONLY":
        raise BuildError("R3C0 manifest verdict mismatch")
    hashes = data.get("artifacts", {}).get("hashes", {})
    if hashes.get("boot_img") != EXPECTED_R3C0_BOOT_SHA256:
        raise BuildError("R3C0 manifest boot SHA mismatch")
    safety = data.get("safety", {})
    if safety.get("host_only") is not True or safety.get("live_authorized") is not False:
        raise BuildError("R3C0 manifest safety mismatch")
    return {**pin, "schema": data["schema"], "verdict": data["verdict"]}


def build_candidate_bytes(control: bytes, r4w1_image: bytes) -> bytes:
    if len(control) != BOOT_SIZE:
        raise BuildError(f"R3C0 boot size mismatch: {len(control)}")
    if len(r4w1_image) != KERNEL_SIZE:
        raise BuildError(f"R4W1 Image size mismatch: {len(r4w1_image)}")
    control_kernel = control[KERNEL_START:KERNEL_END]
    if sha256_bytes(control_kernel) != EXPECTED_STOCK_KERNEL_SHA256:
        raise BuildError("R3C0 kernel slice SHA mismatch")
    if parse_arm64_header(r4w1_image) != parse_arm64_header(control_kernel):
        raise BuildError("R4W1 ARM64 Image header differs from R3C0 kernel header")
    if r4w1_image.count(R4W1_MARKER) != 1:
        raise BuildError("R4W1 Image must contain exactly one build-bound witness marker")
    candidate = bytearray(control)
    candidate[KERNEL_START:KERNEL_END] = r4w1_image
    return bytes(candidate)


def changed_summary(before: bytes, after: bytes) -> dict[str, int]:
    if len(before) != len(after):
        raise BuildError("cannot diff images of unequal size")
    first: int | None = None
    last: int | None = None
    changed = 0
    outside = 0
    for offset, (left, right) in enumerate(zip(before, after)):
        if left == right:
            continue
        if first is None:
            first = offset
        last = offset
        changed += 1
        if offset < KERNEL_START or offset >= KERNEL_END:
            outside += 1
    if first is None or last is None:
        raise BuildError("R4W1A unexpectedly equals R3C0")
    if outside:
        raise BuildError(f"R4W1A changed {outside} bytes outside kernel region")
    return {
        "first_changed_offset": first,
        "last_changed_offset_inclusive": last,
        "changed_byte_count": changed,
        "outside_kernel_changed_byte_count": outside,
    }


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
    # This parse-only gate names an impossible USB path and requires Odin to
    # report failure before opening a device; it does not enumerate USB.
    result = run([odin, "-a", ap_path, "-d", INVALID_ODIN_DEVICE], timeout=30)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    required = (
        "Check file :",
        INVALID_ODIN_DEVICE,
        "No such file or directory",
        "usb device Fail",
    )
    missing = [marker for marker in required if marker not in output]
    if result.returncode != 1 or missing:
        raise BuildError(
            f"unexpected Odin invalid-device parse gate rc={result.returncode} "
            f"missing={missing}: {output}"
        )
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
    control_path = resolve(root, args.r3c0_boot)
    control_manifest_path = resolve(root, args.r3c0_manifest)
    r4w1_path = resolve(root, args.r4w1_image)
    lz4 = resolve(root, args.lz4)
    odin = resolve(root, args.odin)
    if out.exists():
        raise BuildError(f"output path already exists: {out}")
    if os.environ.get("PATCHVBMETAFLAG"):
        raise BuildError("PATCHVBMETAFLAG must be unset for R4W1A")

    control_pin, control = read_pinned(
        control_path, BOOT_SIZE, EXPECTED_R3C0_BOOT_SHA256, "R3C0 boot"
    )
    r4w1_pin, r4w1_image = read_pinned(
        r4w1_path, KERNEL_SIZE, EXPECTED_R4W1_IMAGE_SHA256, "R4W1 Image"
    )
    lz4_pin, lz4_bytes = read_pinned(
        lz4, EXPECTED_LZ4_SIZE, EXPECTED_LZ4_SHA256, "lz4"
    )
    odin_pin, odin_bytes = read_pinned(
        odin, EXPECTED_ODIN_SIZE, EXPECTED_ODIN_SHA256, "odin4"
    )
    input_pins = {
        "r3c0_boot": control_pin,
        "r3c0_manifest": verify_r3c0_manifest(control_manifest_path),
        "r4w1_image": r4w1_pin,
        "lz4": lz4_pin,
        "odin": odin_pin,
    }
    candidate = build_candidate_bytes(control, r4w1_image)
    difference = changed_summary(control, candidate)

    if sha256_bytes(candidate[KERNEL_START:KERNEL_END]) != EXPECTED_R4W1_IMAGE_SHA256:
        raise BuildError("candidate kernel does not equal exact R4W1 Image")
    if sha256_bytes(candidate[RAMDISK_START:RAMDISK_END]) != EXPECTED_STOCK_RAMDISK_SHA256:
        raise BuildError("candidate ramdisk changed from R3C0")
    if sha256_bytes(candidate[SIGNER_START:SIGNER_END]) != EXPECTED_R3C0_SIGNER_SHA256:
        raise BuildError("candidate signer region changed from R3C0")
    if sha256_bytes(candidate[VBMETA_START:VBMETA_END]) != EXPECTED_STOCK_VBMETA_SHA256:
        raise BuildError("candidate vbmeta changed from R3C0")
    if candidate[FOOTER_START:] != control[FOOTER_START:]:
        raise BuildError("candidate AVB footer changed from R3C0")
    if candidate[:KERNEL_START] != control[:KERNEL_START]:
        raise BuildError("candidate boot header changed from R3C0")
    if candidate[KERNEL_END:] != control[KERNEL_END:]:
        raise BuildError("candidate changed outside kernel region")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{out.name}.", dir=out.parent) as temporary:
        staging = Path(temporary)
        tool_dir = staging / ".pinned-tools"
        tool_dir.mkdir()
        pinned_lz4 = tool_dir / "lz4"
        pinned_odin = tool_dir / "odin4"
        pinned_lz4.write_bytes(lz4_bytes)
        pinned_odin.write_bytes(odin_bytes)
        pinned_lz4.chmod(0o700)
        pinned_odin.chmod(0o700)
        require_pinned(pinned_lz4, EXPECTED_LZ4_SIZE, EXPECTED_LZ4_SHA256, "staged lz4")
        require_pinned(pinned_odin, EXPECTED_ODIN_SIZE, EXPECTED_ODIN_SHA256, "staged odin4")
        odin_dir = staging / "odin4"
        odin_dir.mkdir()
        boot_path = staging / "boot.img"
        boot_path.write_bytes(candidate)
        if boot_path.read_bytes() != candidate:
            raise BuildError("staged R4W1A bytes changed after write")

        boot_lz4 = odin_dir / "boot.img.lz4"
        require_ok(
            run([pinned_lz4, "--content-size", "-B6", "-f", "-q", boot_path, boot_lz4]),
            "LZ4 compression",
        )
        roundtrip = staging / "lz4-roundtrip.img"
        require_ok(run([pinned_lz4, "-d", "-f", "-q", boot_lz4, roundtrip]), "LZ4 roundtrip")
        if sha256_file(roundtrip) != sha256_file(boot_path):
            raise BuildError("LZ4 roundtrip raw boot mismatch")
        roundtrip.unlink()

        ap_path = odin_dir / "AP.tar.md5"
        ap_structure = write_deterministic_ap(boot_lz4, ap_path)
        odin_gate = run_odin_invalid_device_gate(pinned_odin, ap_path)
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(
            json.dumps(odin_gate, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )

        hashes = {
            "boot_img": sha256_file(boot_path),
            "boot_img_lz4": sha256_file(boot_lz4),
            "ap_tar_md5": sha256_file(ap_path),
            "kernel": sha256_bytes(candidate[KERNEL_START:KERNEL_END]),
            "ramdisk": sha256_bytes(candidate[RAMDISK_START:RAMDISK_END]),
            "signer": sha256_bytes(candidate[SIGNER_START:SIGNER_END]),
            "vbmeta": sha256_bytes(candidate[VBMETA_START:VBMETA_END]),
            "avb_footer": sha256_bytes(candidate[FOOTER_START:]),
        }
        sizes = {
            "boot_img": boot_path.stat().st_size,
            "boot_img_lz4": boot_lz4.stat().st_size,
            "ap_tar_md5": ap_path.stat().st_size,
        }
        manifest = {
            "schema": SCHEMA,
            "target": TARGET,
            "purpose": "R4W1-A exact retained-witness kernel in live-proven R3C0 stock-Android carrier",
            "inputs": input_pins,
            "construction": {
                "tool": "direct fixed-offset kernel replacement of pinned R3C0 boot",
                "patch_vbmeta_flag": False,
                "kernel_region": {"start": KERNEL_START, "end_exclusive": KERNEL_END},
                "kernel_equals_exact_r4w1_image": hashes["kernel"] == EXPECTED_R4W1_IMAGE_SHA256,
                "r4w1_marker_count": r4w1_image.count(R4W1_MARKER),
                "r3c0_boot_header_preserved": candidate[:KERNEL_START] == control[:KERNEL_START],
                "r3c0_post_kernel_bytes_preserved": candidate[KERNEL_END:] == control[KERNEL_END:],
                "r3c0_ramdisk_preserved": hashes["ramdisk"] == EXPECTED_STOCK_RAMDISK_SHA256,
                "r3c0_signer_preserved": hashes["signer"] == EXPECTED_R3C0_SIGNER_SHA256,
                "r3c0_vbmeta_preserved": hashes["vbmeta"] == EXPECTED_STOCK_VBMETA_SHA256,
                "r3c0_avb_footer_preserved": candidate[FOOTER_START:] == control[FOOTER_START:],
                "arm64_header_exact_r3c0_match": parse_arm64_header(r4w1_image)
                == parse_arm64_header(control[KERNEL_START:KERNEL_END]),
                "difference": difference,
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
                "r4w1a_live_authorized": False,
                "stale_avb_descriptor_semantics_retained": True,
            },
            "verdict": "PASS_R4W1A_ARTIFACT_BUILT_HOST_ONLY",
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
        pinned_lz4.unlink()
        pinned_odin.unlink()
        tool_dir.rmdir()
        os.replace(staging, out)
        return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--r3c0-boot", type=Path, default=DEFAULT_R3C0_BOOT)
    parser.add_argument("--r3c0-manifest", type=Path, default=DEFAULT_R3C0_MANIFEST)
    parser.add_argument("--r4w1-image", type=Path, default=DEFAULT_R4W1_IMAGE)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = build(args)
    except (BuildError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": manifest["verdict"],
                "boot_sha256": manifest["artifacts"]["hashes"]["boot_img"],
                "ap_sha256": manifest["artifacts"]["hashes"]["ap_tar_md5"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
