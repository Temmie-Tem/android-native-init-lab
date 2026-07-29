#!/usr/bin/env python3
"""Deterministic boot-only packaging primitive for P2.86."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier
import s22plus_boot_slice as boot_slice


SCHEMA = "s22plus_fyg8_p286_boot_only_package_v1"
VERDICT = "PASS_P286_DETERMINISTIC_BOOT_ONLY_PACKAGE_HOST_ONLY"


class PackageError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def package(
    *,
    boot_path: Path,
    lz4_path: Path,
    output_dir: Path,
    audit_dir: Path,
) -> dict[str, Any]:
    if boot_path.is_symlink() or not boot_path.is_file():
        raise PackageError("P2.86 boot input is missing or indirect")
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise PackageError("P2.86 output directory is missing or indirect")
    if audit_dir.is_symlink() or not audit_dir.is_dir():
        raise PackageError("P2.86 audit directory is missing or indirect")
    frame_path = output_dir / "boot.img.lz4"
    carrier.require_ok(
        carrier.run(
            [
                lz4_path,
                "--content-size",
                "-B6",
                "-f",
                "-q",
                boot_path,
                frame_path,
            ]
        ),
        "compress P2.86 boot",
    )
    roundtrip = audit_dir / "p286-package-roundtrip.img"
    carrier.require_ok(
        carrier.run(
            [lz4_path, "-d", "-f", "-q", frame_path, roundtrip]
        ),
        "decompress P2.86 boot",
    )
    boot = boot_path.read_bytes()
    if roundtrip.read_bytes() != boot:
        raise PackageError("P2.86 LZ4 roundtrip mismatch")

    odin = output_dir / "odin4"
    odin.mkdir()
    ap_path = odin / "AP.tar.md5"
    frame = frame_path.read_bytes()
    structure = boot_slice.write_deterministic_boot_ap(frame, ap_path)
    if structure.get("members") != ["boot.img.lz4"]:
        raise PackageError("P2.86 AP is not exactly boot-only")
    ap = ap_path.read_bytes()
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "boot_img": _receipt(boot),
        "boot_img_lz4": _receipt(frame),
        "ap_tar_md5": _receipt(ap),
        "ap_structure": structure,
        "paths": {
            "boot_img_lz4": frame_path.name,
            "ap_tar_md5": "odin4/AP.tar.md5",
        },
        "verified": True,
        "safety": {
            "host_only": True,
            "boot_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
