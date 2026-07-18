#!/usr/bin/env python3
"""Independently qualify three host-only FYG8 R4W1-B candidate reproductions."""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

import s22plus_boot_verify as verify


SCHEMA = "s22plus_fyg8_r4w1b_candidate_static_checker_v1"
VERDICT = "PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BOOT_SIZE = 100_663_296
HEADER_END = 4_096
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START
GAP_START = KERNEL_END
GAP_END = 41_496_576
GAP_SIZE = GAP_END - GAP_START

M4T2_BOOT_SHA256 = "8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15"
R4W1B_IMAGE_SHA256 = "350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3"
REPRO_RESULT_SIZE = 314_695
REPRO_RESULT_SHA256 = "1b1124c828243772cb48cf8aa7f6667e88cd9ac5443164e2042243510d833eb1"
M4T2_INIT_SIZE = 544
M4T2_INIT_MODE = 0o750
M4T2_INIT_SHA256 = "b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12"
VENDOR_BOOT_SIZE = 100_663_296
VENDOR_BOOT_SHA256 = "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"
LZ4_SIZE = 218_696
LZ4_SHA256 = "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
AVBTOOL_SIZE = 14_060_849
AVBTOOL_SHA256 = "063d7c7a19744ceeb72553c95962ac98fff977fc27f5f95e6063c2f15f8d3e88"
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
MARKER = (
    b"\n[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|"
    b"phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
MARKER_FAMILY = b"[[S22R4W1B|"
HISTORICAL_FAMILY = b"[[S22R4W1|"

DEFAULT_CARRIER = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/m4t2-carrier/boot.img"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/Image"
)
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_clean_repro_20260719/repro/result.json"
)
DEFAULT_VENDOR_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/vendor_boot.img"
)
DEFAULT_LZ4 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
DEFAULT_AVBTOOL = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/avbtool"
)
DEFAULT_ODIN = Path("/home/temmie/다운로드/odin4")
DEFAULT_REPRO_A = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-a"
)
DEFAULT_REPRO_B = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-b"
)
DEFAULT_REPRO_C = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-c"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/static-check-result.json"
)


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def expected_candidate(carrier: bytes, image: bytes) -> bytes:
    if len(carrier) != BOOT_SIZE or len(image) != KERNEL_SIZE:
        raise CheckError("carrier/Image size does not match independent fixed geometry")
    return carrier[:HEADER_END] + image + carrier[KERNEL_END:]


def classify_marker(data: bytes) -> dict[str, Any]:
    exact_count = data.count(MARKER)
    records: list[bytes] = []
    partial: list[int] = []
    cursor = 0
    while True:
        start = data.find(MARKER_FAMILY, cursor)
        if start < 0:
            break
        end = data.find(b"]]", start + len(MARKER_FAMILY))
        if end < 0:
            partial.append(start)
            cursor = start + len(MARKER_FAMILY)
            continue
        records.append(data[start : end + 2])
        cursor = end + 2
    exact_core = MARKER.strip(b"\n")
    foreign = [record for record in records if record != exact_core]
    return {
        "exact_count": exact_count,
        "family_count": len(records) + len(partial),
        "foreign_count": len(foreign),
        "partial_count": len(partial),
        "historical_family_count": data.count(HISTORICAL_FAMILY),
        "valid_single_exact": (
            exact_count == 1
            and records == [exact_core]
            and not partial
            and data.count(HISTORICAL_FAMILY) == 0
        ),
    }


def verify_reproduction_result(encoded: bytes) -> dict[str, Any]:
    try:
        data = json.loads(encoded.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid kernel reproduction result JSON") from exc
    expected = {
        "schema": "s22plus_fyg8_r4w1b_repro_check_v1",
        "target": TARGET,
        "verdict": "PASS_R4W1B_CLEAN_REPRODUCIBILITY",
        "blockers": [],
        "reproducible": True,
        "image_byte_identical": True,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise CheckError(f"kernel reproduction result {key} mismatch")
    images = data.get("images")
    if not isinstance(images, list) or len(images) != 2:
        raise CheckError("kernel reproduction result does not bind two Images")
    for image in images:
        if (
            image.get("size") != KERNEL_SIZE
            or image.get("sha256") != R4W1B_IMAGE_SHA256
            or image.get("marker_count") != 1
            or image.get("family_count") != 1
            or image.get("historical_family_count") != 0
            or image.get("verified") is not True
        ):
            raise CheckError("kernel reproduction Image binding mismatch")
    safety = data.get("safety", {})
    if safety != {
        "device_contact": False,
        "flash": False,
        "host_only": True,
        "image_packaging": False,
        "live_authorized": False,
    }:
        raise CheckError("kernel reproduction safety mismatch")
    return {
        "schema": data["schema"],
        "verdict": data["verdict"],
        "two_clean_images_verified": True,
    }


def _direct_directory_identity(path: Path, label: str) -> tuple[int, int]:
    if path.is_symlink() or not path.is_dir():
        raise CheckError(f"{label} is missing or indirect: {path}")
    value = path.stat(follow_symlinks=False)
    return value.st_dev, value.st_ino


def _file_identity(path: Path) -> tuple[int, int]:
    value = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(value.st_mode):
        raise CheckError(f"artifact is no longer regular: {path}")
    return value.st_dev, value.st_ino


def validate_manifest(
    encoded: bytes,
    candidate_sha256: str,
    frame_receipt: dict[str, Any],
    ap_receipt: dict[str, Any],
) -> dict[str, Any]:
    try:
        data = json.loads(encoded.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid candidate manifest JSON") from exc
    if data.get("schema") != "s22plus_fyg8_r4w1b_candidate_build_v1":
        raise CheckError("candidate manifest schema mismatch")
    if data.get("target") != TARGET or data.get("rung") != "R4W1-B":
        raise CheckError("candidate manifest target/rung mismatch")
    if data.get("verdict") != "PASS_R4W1B_CANDIDATE_BUILT_HOST_ONLY" or data.get("blockers") != []:
        raise CheckError("candidate manifest verdict mismatch")
    geometry = data.get("geometry", {})
    expected_geometry = {
        "carrier_size": BOOT_SIZE,
        "android_header": [0, HEADER_END],
        "kernel_interval": [KERNEL_START, KERNEL_END],
        "kernel_size": KERNEL_SIZE,
        "alignment_gap": [GAP_START, GAP_END],
        "alignment_gap_size": GAP_SIZE,
        "preserved_tail": [KERNEL_END, BOOT_SIZE],
    }
    if geometry != expected_geometry:
        raise CheckError("candidate manifest geometry mismatch")
    inputs = data.get("inputs", {})
    expected_inputs = {
        "m4t2_carrier": (BOOT_SIZE, M4T2_BOOT_SHA256),
        "r4w1b_image": (KERNEL_SIZE, R4W1B_IMAGE_SHA256),
        "r4w1b_reproduction_result": (REPRO_RESULT_SIZE, REPRO_RESULT_SHA256),
        "lz4": (LZ4_SIZE, LZ4_SHA256),
        "odin4": (ODIN_SIZE, ODIN_SHA256),
    }
    for name, (size, digest) in expected_inputs.items():
        if inputs.get(name, {}).get("size") != size or inputs.get(name, {}).get("sha256") != digest:
            raise CheckError(f"candidate manifest input mismatch: {name}")
    outputs = data.get("outputs", {})
    expected_outputs = {
        "boot_img": (BOOT_SIZE, candidate_sha256),
        "boot_img_lz4": (frame_receipt["size"], frame_receipt["sha256"]),
        "ap_tar_md5": (ap_receipt["size"], ap_receipt["sha256"]),
    }
    for name, (size, digest) in expected_outputs.items():
        if outputs.get(name) != {"size": size, "sha256": digest}:
            raise CheckError(f"candidate manifest output mismatch: {name}")
    construction = data.get("construction", {})
    for key in (
        "carrier_header_preserved",
        "kernel_equals_qualified_image",
        "alignment_gap_preserved",
        "opaque_post_kernel_bytes_preserved",
    ):
        if construction.get(key) is not True:
            raise CheckError(f"candidate manifest invariant false: {key}")
    safety = data.get("safety", {})
    required_safety = {
        "host_only": True,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "device_contact": False,
        "device_write": False,
        "usb_enumeration": False,
        "odin_transfer": False,
        "flash": False,
        "live_authorized": False,
        "stale_carrier_avb_preserved": True,
    }
    if safety != required_safety:
        raise CheckError("candidate manifest safety mismatch")
    return {"schema": data["schema"], "verdict": data["verdict"], "consistent": True}


def inspect_reproduction(
    directory: Path,
    expected_raw: bytes,
    expected_sha256: str,
    lz4_tool: Path,
) -> dict[str, Any]:
    allowed = {
        "boot.img",
        "boot.img.lz4",
        "manifest.json",
        "odin4/AP.tar.md5",
        "odin4/parse_dry_run_invalid_device.txt",
    }
    observed = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if observed != allowed:
        raise CheckError(
            f"candidate reproduction file set mismatch: missing={sorted(allowed - observed)} "
            f"extra={sorted(observed - allowed)}"
        )
    raw_path = directory / "boot.img"
    frame_path = directory / "boot.img.lz4"
    ap_path = directory / "odin4/AP.tar.md5"
    manifest_path = directory / "manifest.json"
    raw_receipt, raw = verify.read_pinned_stable(
        raw_path, BOOT_SIZE, expected_sha256, "candidate raw boot"
    )
    if raw != expected_raw:
        raise CheckError("candidate raw bytes differ from independent reconstruction")
    frame_receipt, frame = verify.read_stable(frame_path, "candidate LZ4")
    frame_info = verify.parse_lz4_frame(frame)
    if frame_info["content_size"] != BOOT_SIZE:
        raise CheckError("candidate LZ4 content-size field mismatch")
    if verify.decompress_lz4(lz4_tool, frame, BOOT_SIZE) != expected_raw:
        raise CheckError("candidate LZ4 does not decode to expected raw boot")
    ap_receipt, ap = verify.read_stable(ap_path, "candidate AP")
    ap_info, ap_frame = verify.parse_ap_tar_md5(ap)
    if ap_frame != frame:
        raise CheckError("AP member differs from standalone candidate LZ4")
    manifest_receipt, manifest = verify.read_stable(manifest_path, "candidate manifest")
    manifest_info = validate_manifest(
        manifest, expected_sha256, frame_receipt, ap_receipt
    )
    return {
        "raw": raw_receipt,
        "frame": {**frame_receipt, "format": frame_info},
        "ap": {**ap_receipt, **ap_info},
        "manifest": {**manifest_receipt, **manifest_info},
        "bytes": {"frame": frame, "ap": ap, "manifest": manifest},
        "identities": {
            "raw": _file_identity(raw_path),
            "frame": _file_identity(frame_path),
            "ap": _file_identity(ap_path),
            "manifest": _file_identity(manifest_path),
        },
    }


def audit_rootfs(
    carrier: bytes, vendor_boot_data: bytes, lz4_tool: Path
) -> dict[str, Any]:
    boot = verify.parse_boot_v4(carrier)
    vendor = verify.parse_vendor_boot_v4(vendor_boot_data)
    generic_cpio = verify.decompress_lz4(lz4_tool, boot.ramdisk)
    layers: list[tuple[str, tuple[verify.CpioEntry, ...], bytes, bytes]] = [
        ("generic", verify.parse_newc(generic_cpio), boot.ramdisk, generic_cpio)
    ]
    for index, fragment in enumerate(vendor.fragments):
        decoded = verify.decompress_lz4(lz4_tool, fragment.data)
        label = f"vendor[{index}]/{fragment.name or '<unnamed>'}"
        layers.append((label, verify.parse_newc(decoded), fragment.data, decoded))
    seen: dict[str, str] = {}
    init_entries: list[tuple[str, verify.CpioEntry]] = []
    summaries: list[dict[str, Any]] = []
    for label, entries, compressed, decoded in layers:
        names: list[str] = []
        for entry in entries:
            if entry.name in seen:
                raise CheckError(
                    f"rootfs path override/duplicate: {entry.name} in {seen[entry.name]} and {label}"
                )
            seen[entry.name] = label
            names.append(entry.name)
            if entry.file_type == "symlink" or entry.nlink != 1:
                raise CheckError(f"rootfs alias/hardlink forbidden: {label}:{entry.name}")
            if entry.name == "init":
                init_entries.append((label, entry))
        summaries.append(
            {
                "layer": label,
                "entry_count": len(entries),
                "entry_names": names,
                "compressed_size": len(compressed),
                "compressed_sha256": verify.sha256_bytes(compressed),
                "cpio_size": len(decoded),
                "cpio_sha256": verify.sha256_bytes(decoded),
            }
        )
    if len(init_entries) != 1:
        raise CheckError(f"effective rootfs requires exactly one /init, got {len(init_entries)}")
    init_layer, init = init_entries[0]
    if (
        init_layer != "generic"
        or init.file_type != "regular"
        or init.uid != 0
        or init.gid != 0
        or stat.S_IMODE(init.mode) != M4T2_INIT_MODE
        or len(init.data) != M4T2_INIT_SIZE
        or verify.sha256_bytes(init.data) != M4T2_INIT_SHA256
    ):
        raise CheckError("effective /init identity or metadata mismatch")
    rdinit_sources = {
        "boot_cmdline": boot.header["cmdline"].encode("ascii"),
        "vendor_cmdline": vendor.cmdline.encode("ascii"),
        "vendor_bootconfig": vendor.bootconfig,
    }
    contaminated = [name for name, data in rdinit_sources.items() if b"rdinit=" in data]
    if contaminated:
        raise CheckError(f"rdinit override found: {contaminated}")
    return {
        "composition_order": [summary["layer"] for summary in summaries],
        "layers": summaries,
        "total_entry_count": len(seen),
        "no_duplicate_or_override": True,
        "no_symlink_or_hardlink_alias": True,
        "rdinit_override_sources": contaminated,
        "effective_init": {
            "layer": init_layer,
            **init.summary(),
            "entrypoint": verify.inspect_aarch64_static_init(init.data),
        },
        "vendor_boot": {
            "header": vendor.header,
            "cmdline": vendor.cmdline,
            "bootconfig_sha256": verify.sha256_bytes(vendor.bootconfig),
            "fragment_count": len(vendor.fragments),
            "fragments": [
                {
                    "index": index,
                    "name": fragment.name,
                    "ramdisk_type": fragment.ramdisk_type,
                    "board_id": list(fragment.board_id),
                    "size": len(fragment.data),
                    "sha256": verify.sha256_bytes(fragment.data),
                }
                for index, fragment in enumerate(vendor.fragments)
            ],
        },
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    carrier_pin, carrier = verify.read_pinned_stable(
        resolve(root, args.carrier), BOOT_SIZE, M4T2_BOOT_SHA256, "M4T2 carrier"
    )
    image_pin, image = verify.read_pinned_stable(
        resolve(root, args.image), KERNEL_SIZE, R4W1B_IMAGE_SHA256, "R4W1-B Image"
    )
    repro_pin, repro_bytes = verify.read_pinned_stable(
        resolve(root, args.repro_result),
        REPRO_RESULT_SIZE,
        REPRO_RESULT_SHA256,
        "kernel reproduction result",
    )
    repro = verify_reproduction_result(repro_bytes)
    vendor_pin, vendor_boot = verify.read_pinned_stable(
        resolve(root, args.vendor_boot),
        VENDOR_BOOT_SIZE,
        VENDOR_BOOT_SHA256,
        "stock vendor_boot",
    )
    lz4_pin, lz4_bytes = verify.read_pinned_stable(
        resolve(root, args.lz4), LZ4_SIZE, LZ4_SHA256, "lz4"
    )
    avbtool_pin, avbtool_bytes = verify.read_pinned_stable(
        resolve(root, args.avbtool), AVBTOOL_SIZE, AVBTOOL_SHA256, "avbtool"
    )
    odin_pin, _odin_bytes = verify.read_pinned_stable(
        resolve(root, args.odin), ODIN_SIZE, ODIN_SHA256, "odin4"
    )
    candidate = expected_candidate(carrier, image)
    candidate_sha256 = verify.sha256_bytes(candidate)
    marker = classify_marker(image)
    if not marker["valid_single_exact"]:
        raise CheckError(f"qualified Image marker mismatch: {marker}")
    if candidate[:HEADER_END] != carrier[:HEADER_END]:
        raise CheckError("independent candidate changed Android header")
    if candidate[GAP_START:GAP_END] != carrier[GAP_START:GAP_END]:
        raise CheckError("independent candidate changed explicit alignment gap")
    if candidate[KERNEL_END:] != carrier[KERNEL_END:]:
        raise CheckError("independent candidate changed opaque carrier tail")
    carrier_boot = verify.parse_boot_v4(carrier)
    candidate_boot = verify.parse_boot_v4(candidate)
    if carrier_boot.header != candidate_boot.header:
        raise CheckError("candidate boot-v4 header fields changed")
    if candidate_boot.kernel != image:
        raise CheckError("candidate boot parser did not recover qualified Image")
    if verify.parse_arm64_header(candidate_boot.kernel) != verify.parse_arm64_header(image):
        raise CheckError("candidate/Image ARM64 headers differ")

    directories = [
        resolve(root, args.reproduction_a),
        resolve(root, args.reproduction_b),
        resolve(root, args.reproduction_c),
    ]
    directory_ids = [_direct_directory_identity(path, f"reproduction {index}") for index, path in enumerate(directories)]
    if len(set(directory_ids)) != 3:
        raise CheckError("reproduction directories are not three distinct directories")
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1b-static-") as temporary:
        tool_dir = Path(temporary)
        lz4_tool = tool_dir / "lz4"
        avbtool = tool_dir / "avbtool"
        lz4_tool.write_bytes(lz4_bytes)
        avbtool.write_bytes(avbtool_bytes)
        lz4_tool.chmod(0o700)
        avbtool.chmod(0o700)
        verify.read_pinned_stable(lz4_tool, LZ4_SIZE, LZ4_SHA256, "staged lz4")
        verify.read_pinned_stable(avbtool, AVBTOOL_SIZE, AVBTOOL_SHA256, "staged avbtool")
        reproductions = [
            inspect_reproduction(path, candidate, candidate_sha256, lz4_tool)
            for path in directories
        ]
        for artifact in ("raw", "frame", "ap", "manifest"):
            identities = [item["identities"][artifact] for item in reproductions]
            if len(set(identities)) != 3:
                raise CheckError(f"reproduction {artifact} artifacts are hardlinked/aliased")
        for artifact in ("frame", "ap", "manifest"):
            values = [item["bytes"][artifact] for item in reproductions]
            if not (values[0] == values[1] == values[2]):
                raise CheckError(f"three reproductions differ: {artifact}")
        carrier_avb = verify.run_avbtool(avbtool, carrier)
        candidate_avb = verify.run_avbtool(avbtool, candidate)
        for label, result in (("carrier", carrier_avb), ("candidate", candidate_avb)):
            if (
                result["returncode"] == 0
                or result["vbmeta_signature_verified"] is not True
                or result["payload_hash_mismatch"] is not True
            ):
                raise CheckError(f"{label} AVB outcome is not the expected stale descriptor")
        rootfs = audit_rootfs(carrier, vendor_boot, lz4_tool)

    carrier_footer = verify.parse_avb_footer(carrier)
    candidate_footer = verify.parse_avb_footer(candidate)
    if candidate_footer != carrier_footer or candidate[-64:] != carrier[-64:]:
        raise CheckError("candidate AVB footer differs from M4T2")
    start = carrier_footer["vbmeta_offset"]
    end = start + carrier_footer["vbmeta_size"]
    if candidate[start:end] != carrier[start:end]:
        raise CheckError("candidate vbmeta differs from M4T2")
    public_reproductions = []
    for index, item in enumerate(reproductions):
        public_reproductions.append(
            {
                "index": index,
                "raw": item["raw"],
                "frame": item["frame"],
                "ap": item["ap"],
                "manifest": item["manifest"],
            }
        )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "inputs": {
            "m4t2_carrier": carrier_pin,
            "r4w1b_image": image_pin,
            "kernel_reproduction_result": {**repro_pin, **repro},
            "stock_vendor_boot": vendor_pin,
            "lz4": lz4_pin,
            "avbtool": avbtool_pin,
            "odin4": odin_pin,
        },
        "independent_construction": {
            "formula": "carrier[:4096] + image + carrier[41495040:]",
            "candidate_size": len(candidate),
            "candidate_sha256": candidate_sha256,
            "android_header_v4_preserved": True,
            "kernel_size_unchanged": carrier_boot.header["kernel_size"] == KERNEL_SIZE,
            "kernel_exact_image": True,
            "arm64_header_exact_image": True,
            "alignment_gap": [GAP_START, GAP_END],
            "alignment_gap_size": GAP_SIZE,
            "alignment_gap_preserved": True,
            "opaque_tail_preserved": True,
            "marker": marker,
        },
        "reproductions": public_reproductions,
        "three_reproductions_byte_identical": True,
        "avb": {
            "footer": candidate_footer,
            "footer_exact_carrier": True,
            "vbmeta_exact_carrier": True,
            "carrier_verification": carrier_avb,
            "candidate_verification": candidate_avb,
            "expected_stale_outcome": True,
        },
        "rootfs": rootfs,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "live_authorized": False,
        },
        "blockers": [],
        "verdict": VERDICT,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--avbtool", type=Path, default=DEFAULT_AVBTOOL)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--reproduction-a", type=Path, default=DEFAULT_REPRO_A)
    parser.add_argument("--reproduction-b", type=Path, default=DEFAULT_REPRO_B)
    parser.add_argument("--reproduction-c", type=Path, default=DEFAULT_REPRO_C)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
        output = resolve(repo_root(), args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, encoded.encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except (CheckError, verify.BootVerifyError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "candidate_sha256": result["independent_construction"]["candidate_sha256"],
                "blockers": [],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
