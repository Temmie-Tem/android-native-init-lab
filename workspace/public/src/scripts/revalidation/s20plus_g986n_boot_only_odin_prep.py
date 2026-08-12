#!/usr/bin/env python3
"""Host-only S20+ IYC2 Magisk/stock boot-only Odin artifact preparation."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
PATCHED_AP = ROOT / (
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/patched/"
    "magisk_patched-30700_kFiLC.tar"
)
PATCHED_AP_SIZE = 7_362_972_672
PATCHED_AP_SHA256 = "a025e13cf5665701df2229e07ecdab404a906d816aa7dd93aa3393bf8797b5f6"
PATCHED_MEMBERS = (
    "recovery.img.lz4",
    "dtbo.img.lz4",
    "super.img.lz4",
    "persist.img.lz4",
    "vbmeta.img",
    "vbmeta_samsung.img.lz4",
    "dqmdbg.img.lz4",
    "carrier.img.lz4",
    "misc.bin.lz4",
    "meta-data/",
    "meta-data/fota.zip",
    "boot.img",
)
BOOT_SIZE = 67_108_864
STOCK_BOOT = ROOT / "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/extracted/boot.img"
STOCK_BOOT_SHA256 = "29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab"
STOCK_BOOT_LZ4 = ROOT / "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/extracted/boot.img.lz4"
STOCK_BOOT_LZ4_SIZE = 25_667_811
STOCK_BOOT_LZ4_SHA256 = "c2bb08fcbaf492bb0e9bd5dc119633e17b97539f7cd954d88c20c80d046ca29e"
LZ4 = ROOT / "workspace/private/tools/lz4-local/root/usr/bin/lz4"
LZ4_SIZE = 115_032
LZ4_SHA256 = "4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0"
ODIN4 = Path("/usr/bin/odin4")
ODIN4_SIZE = 3_746_744
ODIN4_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
OUTPUT = ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1"


class PrepError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(path: Path, size: int, sha256: str, label: str) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise PrepError(f"{label} is not an exact regular file")
    if metadata.st_size != size or sha256_file(path) != sha256:
        raise PrepError(f"{label} identity mismatch")


def receipt(path: Path) -> dict[str, Any]:
    return {"size": path.stat().st_size, "sha256": sha256_file(path)}


def exact_members(path: Path) -> tuple[str, ...]:
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
    names = tuple(member.name + ("/" if member.isdir() and not member.name.endswith("/") else "") for member in members)
    if names != PATCHED_MEMBERS:
        raise PrepError("patched AP member list is not exact")
    for member in members:
        expected_directory = member.name.rstrip("/") == "meta-data"
        if expected_directory != member.isdir():
            raise PrepError("patched AP member type is not exact")
        if not expected_directory and not member.isreg():
            raise PrepError("patched AP contains a non-regular payload")
    return names


def extract_boot(path: Path, destination: Path) -> None:
    with tarfile.open(path, "r:") as archive:
        member = archive.getmember("boot.img")
        if not member.isreg() or member.size != BOOT_SIZE:
            raise PrepError("patched boot member is not exact")
        source = archive.extractfile(member)
        if source is None:
            raise PrepError("patched boot member is unreadable")
        with destination.open("xb") as output:
            shutil.copyfileobj(source, output, 8 * 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
    if destination.stat().st_size != BOOT_SIZE:
        raise PrepError("extracted patched boot size mismatch")
    with destination.open("rb") as stream:
        if stream.read(8) != b"ANDROID!":
            raise PrepError("patched boot Android header is absent")


def run_lz4(argv: list[str]) -> None:
    completed = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if completed.returncode != 0 or len(completed.stdout) + len(completed.stderr) > 64 * 1024:
        raise PrepError("pinned lz4 operation failed")


def lz4_roundtrip(source: Path, frame: Path, scratch: Path) -> None:
    run_lz4([str(LZ4), "--content-size", "-B6", "-f", "-q", str(source), str(frame)])
    run_lz4([str(LZ4), "-d", "-f", "-q", str(frame), str(scratch)])
    if source.stat().st_size != scratch.stat().st_size or sha256_file(source) != sha256_file(scratch):
        raise PrepError("lz4 roundtrip mismatch")
    scratch.unlink()


def verify_lz4_frame(frame: Path, expected: Path, scratch: Path) -> None:
    run_lz4([str(LZ4), "-d", "-f", "-q", str(frame), str(scratch)])
    if expected.stat().st_size != scratch.stat().st_size or sha256_file(expected) != sha256_file(scratch):
        raise PrepError("existing lz4 frame roundtrip mismatch")
    scratch.unlink()


def write_boot_ap(frame: Path, output: Path) -> dict[str, Any]:
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("boot.img.lz4")
            info.size = frame.stat().st_size
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            with frame.open("rb") as stream:
                archive.addfile(info, stream)
        handle.flush()
        os.fsync(handle.fileno())
    prefix = output.read_bytes()
    md5 = hashlib.md5(prefix).hexdigest()
    trailer = f"{md5}  AP.tar\n".encode("ascii")
    with output.open("ab") as handle:
        handle.write(trailer)
        handle.flush()
        os.fsync(handle.fileno())
    with tarfile.open(output, "r:") as archive:
        members = archive.getmembers()
    if len(members) != 1 or members[0].name != "boot.img.lz4" or not members[0].isreg():
        raise PrepError("boot-only AP membership mismatch")
    data = output.read_bytes()
    if not data.endswith(trailer) or hashlib.md5(data[:-len(trailer)]).hexdigest() != md5:
        raise PrepError("Samsung AP MD5 trailer mismatch")
    return {"members": ["boot.img.lz4"], "tar_md5": md5, **receipt(output)}


def main() -> int:
    require_file(PATCHED_AP, PATCHED_AP_SIZE, PATCHED_AP_SHA256, "patched AP")
    require_file(STOCK_BOOT, BOOT_SIZE, STOCK_BOOT_SHA256, "stock boot")
    require_file(STOCK_BOOT_LZ4, STOCK_BOOT_LZ4_SIZE, STOCK_BOOT_LZ4_SHA256, "stock boot lz4")
    require_file(LZ4, LZ4_SIZE, LZ4_SHA256, "lz4")
    require_file(ODIN4, ODIN4_SIZE, ODIN4_SHA256, "odin4")
    exact_members(PATCHED_AP)
    OUTPUT.mkdir(mode=0o700, parents=True)
    candidate = OUTPUT / "candidate"
    rollback = OUTPUT / "rollback"
    candidate.mkdir(mode=0o700)
    rollback.mkdir(mode=0o700)
    candidate_boot = candidate / "boot.img"
    candidate_lz4 = candidate / "boot.img.lz4"
    extract_boot(PATCHED_AP, candidate_boot)
    lz4_roundtrip(candidate_boot, candidate_lz4, candidate / ".roundtrip.img")
    candidate_ap = candidate / "AP.tar.md5"
    candidate_structure = write_boot_ap(candidate_lz4, candidate_ap)
    rollback_boot = rollback / "boot.img"
    rollback_lz4 = rollback / "boot.img.lz4"
    shutil.copyfile(STOCK_BOOT, rollback_boot)
    shutil.copyfile(STOCK_BOOT_LZ4, rollback_lz4)
    verify_lz4_frame(rollback_lz4, rollback_boot, rollback / ".roundtrip.img")
    rollback_ap = rollback / "AP.tar.md5"
    rollback_structure = write_boot_ap(rollback_lz4, rollback_ap)
    result = {
        "schema": "s20plus_g986n_boot_only_odin_prep_v1",
        "target": "SM-G986N/y2q/G986NKSS8IYC2",
        "source_patched_ap": {**receipt(PATCHED_AP), "members": list(PATCHED_MEMBERS)},
        "candidate": {
            "boot_img": receipt(candidate_boot),
            "boot_img_lz4": receipt(candidate_lz4),
            "ap_tar_md5": candidate_structure,
        },
        "rollback": {
            "boot_img": receipt(rollback_boot),
            "boot_img_lz4": receipt(rollback_lz4),
            "ap_tar_md5": rollback_structure,
        },
        "tools": {"lz4": receipt(LZ4), "odin4": receipt(ODIN4)},
        "safety": {
            "host_only": True,
            "boot_only_outputs": True,
            "device_contact": False,
            "odin_invoked": False,
            "live_flash_authorized": False,
            "f1_defined": False,
        },
        "verdict": "PASS_S20PLUS_G986N_BOOT_ONLY_ODIN_ARTIFACTS_HOST_PREPARED_NOT_LIVE_AUTHORIZED",
    }
    result_path = OUTPUT / "artifact-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in OUTPUT.rglob("*"):
        if path.is_file():
            path.chmod(0o400)
    print(result["verdict"])
    print(f"result={result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
