#!/usr/bin/env python3
"""Build the host-only S20+ IYC2 recovery ADB canary T0 artifacts.

This builder has no device transport.  It pins the exact stock IYC2 recovery,
changes only two existing ramdisk files, adds one read-only marker, and emits
separate candidate and exact-stock rollback Odin archives for offline review.
The custom recovery hash is expected to fail the retained stock AVB descriptor;
the output is never live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BASE_RECOVERY = ROOT / (
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/"
    "extracted/recovery.img"
)
BASE_RECOVERY_LZ4 = ROOT / (
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/"
    "extracted/recovery.img.lz4"
)
MAGISKBOOT = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
LZ4 = ROOT / "workspace/private/tools/lz4-local/root/usr/bin/lz4"
AVBTOOL = ROOT / "workspace/private/tools/avb/android13-release/avbtool.py"
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/recovery_adb_canary_t0_v1"
)

SCHEMA = "s20plus_g986n_recovery_adb_canary_t0_build_v1"
VERDICT = "PASS_S20PLUS_G986N_RECOVERY_ADB_CANARY_T0_HOST_BUILT_REVIEW_PENDING"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

BASE_RECOVERY_SIZE = 82_694_144
BASE_RECOVERY_SHA256 = (
    "dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e"
)
BASE_RECOVERY_LZ4_SIZE = 36_600_544
BASE_RECOVERY_LZ4_SHA256 = (
    "6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923"
)
MAGISKBOOT_SIZE = 943_848
MAGISKBOOT_SHA256 = (
    "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
)
LZ4_SIZE = 115_032
LZ4_SHA256 = (
    "4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0"
)
AVBTOOL_SIZE = 200_864
AVBTOOL_SHA256 = (
    "69783733ce5e198317b02a5567cc356e898c891de872f58a963e9d5c082973c6"
)

BASE_COMPONENTS = {
    "header": {
        "size": 373,
        "sha256": "1f948cfa15174ab850d66c2600654aacece5f7c2a5cd871f1b30db153d3baff3",
    },
    "kernel": {
        "size": 51_959_820,
        "sha256": "127d0f43de5e5e5ce5eee9e496b9593cf6ce7f0ce97581ad483e8f76feeb31ca",
    },
    "ramdisk.cpio": {
        "size": 24_184_064,
        "sha256": "9dc6cc9efa7889f339c4e8a98d87b58a3e6ff201d519aadc3a4394ec235482a3",
    },
    "recovery_dtbo": {
        "size": 1_034_509,
        "sha256": "11e0da1564c1e2bbbccfa13f41ceaa105135586a443646980baa421b00137455",
    },
    "dtb": {
        "size": 1_580_275,
        "sha256": "09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883",
    },
}

PROP_ENTRY = "prop.default"
RC_ENTRY = "init.recovery.samsung.rc"
MARKER_ENTRY = "init.s20plus_g986n_recovery_adb_canary"
CHANGED_ENTRIES = (PROP_ENTRY, RC_ENTRY)
ADDED_ENTRIES = (MARKER_ENTRY,)
METADATA_CHANGED_ENTRIES = (RC_ENTRY,)
BASE_PROP_SHA256 = (
    "bd3cf263bbb29315d09ca6f9a5e0ad0d939a386b02a9972980594428d4f3e8a6"
)
BASE_RC_SHA256 = (
    "75a131e499b45f606a45d097412f374be9d877b282ac35f673bcd61655dfd444"
)
RC_APPEND = (
    b"\n\n# S20+ G986N IYC2 recovery ADB canary T0 v1.\n"
    b"on boot\n"
    b"    setprop service.adb.root 1\n"
    b"    setprop sys.usb.config adb\n"
)
MARKER = (
    b"S20PLUS_G986N_RECOVERY_ADB_CANARY_T0_V1\n"
    b"target=SM-G986N/y2q/y2qksx/G986NKSS8IYC2\n"
    b"purpose=custom-recovery-acceptance-and-recovery-adb-only\n"
    b"live_authority=false\n"
)
ENTRY_MODES = {
    PROP_ENTRY: "-rw-r--r--",
    RC_ENTRY: "-rwxr-x---",
    MARKER_ENTRY: "-r--r--r--",
}


class BuildError(RuntimeError):
    """A closed H0 build invariant failed."""


def clean_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "SOURCE_DATE_EPOCH": "0",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt(path: Path) -> dict[str, Any]:
    return {"size": path.stat().st_size, "sha256": sha256_file(path)}


def require_direct_file(path: Path, size: int, digest: str, label: str) -> None:
    try:
        state = path.lstat()
    except FileNotFoundError as exc:
        raise BuildError(f"{label} is absent") from exc
    if path.is_symlink() or not stat.S_ISREG(state.st_mode):
        raise BuildError(f"{label} is not a direct regular file")
    if state.st_uid != os.getuid() or state.st_nlink != 1:
        raise BuildError(f"{label} owner or link count changed")
    if state.st_mode & 0o022:
        raise BuildError(f"{label} is group/world writable")
    if state.st_size != size or sha256_file(path) != digest:
        raise BuildError(f"{label} identity changed")


def run_command(
    command: list[str | Path],
    *,
    cwd: Path | None = None,
    expected: tuple[int, ...] = (0,),
    timeout: int = 300,
) -> bytes:
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        env=clean_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    if len(completed.stdout) > 2 * 1024 * 1024:
        raise BuildError("tool output exceeded the H0 bound")
    if completed.returncode not in expected:
        detail = completed.stdout[:4096].decode("utf-8", errors="replace")
        raise BuildError(
            f"tool failed rc={completed.returncode} expected={expected}: {detail}"
        )
    return completed.stdout


def patch_prop_default(data: bytes) -> bytes:
    if sha256_bytes(data) != BASE_PROP_SHA256:
        raise BuildError("stock prop.default identity changed")
    replacements = (
        (b"ro.secure=1\n", b"ro.secure=0\n", 1),
        (b"ro.adb.secure=1\n", b"ro.adb.secure=0\n", 2),
        (b"ro.debuggable=0\n", b"ro.debuggable=1\n", 1),
    )
    patched = data
    for old, new, count in replacements:
        if patched.count(old) != count or new in patched:
            raise BuildError("stock recovery ADB property grammar changed")
        patched = patched.replace(old, new)
    if len(patched) != len(data):
        raise BuildError("property patch changed byte length")
    return patched


def patch_samsung_rc(data: bytes) -> bytes:
    if sha256_bytes(data) != BASE_RC_SHA256:
        raise BuildError("stock init.recovery.samsung.rc identity changed")
    if b"S20+ G986N IYC2 recovery ADB canary" in data:
        raise BuildError("recovery ADB canary block is already present")
    return data + RC_APPEND


def unpack_recovery(image: Path, directory: Path) -> dict[str, Any]:
    directory.mkdir(mode=0o700)
    output = run_command([MAGISKBOOT, "unpack", "-h", image], cwd=directory)
    required_tokens = (
        b"HEADER_VER      [2]",
        b"NAME            [SRPSK18B008]",
        b"RAMDISK_FMT     [gzip]",
        b"SAMSUNG_SEANDROID",
        b"VBMETA",
    )
    if any(token not in output for token in required_tokens):
        raise BuildError("recovery header or footer shape changed")
    components = {}
    for name in BASE_COMPONENTS:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"unpacked component {name} is absent")
        components[name] = receipt(path)
    return components


def parse_cpio_listing(output: bytes) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for raw in output.decode("utf-8", errors="strict").splitlines():
        if not raw or raw[0] not in "-dl":
            continue
        fields = raw.split("\t")
        if len(fields) != 6:
            raise BuildError("unexpected magiskboot CPIO listing grammar")
        mode, uid, gid, size_text, device, name = fields
        if name.startswith("/") or name in parsed:
            raise BuildError("unsafe or duplicate CPIO listing path")
        parsed[name] = {
            "mode": mode,
            "uid": int(uid),
            "gid": int(gid),
            "size_text": size_text,
            "device": device,
        }
    if not parsed:
        raise BuildError("empty CPIO listing")
    return parsed


def cpio_listing(cpio: Path, cwd: Path) -> dict[str, dict[str, Any]]:
    output = run_command([MAGISKBOOT, "cpio", cpio, "ls -r /"], cwd=cwd)
    return parse_cpio_listing(output)


def extract_cpio_tree(cpio: Path, directory: Path) -> None:
    directory.mkdir(mode=0o700)
    local = directory / "ramdisk.cpio"
    shutil.copyfile(cpio, local)
    run_command([MAGISKBOOT, "cpio", local, "extract"], cwd=directory)
    local.unlink()


def tree_manifest(directory: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        name = path.relative_to(directory).as_posix()
        state = path.lstat()
        mode = stat.S_IMODE(state.st_mode)
        if stat.S_ISREG(state.st_mode):
            result[name] = {
                "type": "file",
                "mode": mode,
                "size": state.st_size,
                "sha256": sha256_file(path),
            }
        elif stat.S_ISDIR(state.st_mode):
            result[name] = {"type": "directory", "mode": mode}
        elif stat.S_ISLNK(state.st_mode):
            result[name] = {
                "type": "symlink",
                "mode": mode,
                "target": os.readlink(path),
            }
        else:
            raise BuildError(f"unsupported extracted CPIO node: {name}")
    return result


def prove_exact_delta(
    base_tree: dict[str, dict[str, Any]],
    candidate_tree: dict[str, dict[str, Any]],
    base_listing: dict[str, dict[str, Any]],
    candidate_listing: dict[str, dict[str, Any]],
    patched_prop: bytes,
    patched_rc: bytes,
) -> dict[str, Any]:
    added = sorted(set(candidate_tree) - set(base_tree))
    removed = sorted(set(base_tree) - set(candidate_tree))
    changed = sorted(
        name
        for name in set(base_tree) & set(candidate_tree)
        if base_tree[name] != candidate_tree[name]
    )
    if added != list(ADDED_ENTRIES) or removed or changed != sorted(CHANGED_ENTRIES):
        raise BuildError(
            f"ramdisk tree delta changed: added={added} removed={removed} "
            f"changed={changed}"
        )

    listing_added = sorted(set(candidate_listing) - set(base_listing))
    listing_removed = sorted(set(base_listing) - set(candidate_listing))
    listing_changed = sorted(
        name
        for name in set(base_listing) & set(candidate_listing)
        if base_listing[name] != candidate_listing[name]
    )
    if (
        listing_added != list(ADDED_ENTRIES)
        or listing_removed
        or listing_changed != sorted(METADATA_CHANGED_ENTRIES)
    ):
        raise BuildError(
            "CPIO metadata delta is not exact: "
            f"added={listing_added} removed={listing_removed} "
            f"changed={listing_changed}"
        )
    for name, expected_mode in ENTRY_MODES.items():
        metadata = candidate_listing.get(name)
        if (
            metadata is None
            or metadata["mode"] != expected_mode
            or metadata["uid"] != 0
            or metadata["gid"] != 0
        ):
            raise BuildError(f"CPIO metadata changed for {name}")

    expected = {
        PROP_ENTRY: patched_prop,
        RC_ENTRY: patched_rc,
        MARKER_ENTRY: MARKER,
    }
    for name, content in expected.items():
        item = candidate_tree[name]
        if item["type"] != "file" or item["sha256"] != sha256_bytes(content):
            raise BuildError(f"patched CPIO content changed for {name}")
    return {
        "base_entry_count": len(base_tree),
        "candidate_entry_count": len(candidate_tree),
        "added_entries": added,
        "removed_entries": removed,
        "changed_entries": changed,
        "all_other_entries_byte_and_mode_identical": True,
    }


def add_cpio_file(cpio: Path, name: str, mode: int, source: Path, cwd: Path) -> None:
    run_command(
        [MAGISKBOOT, "cpio", cpio, f"add {mode:o} {name} {source}"],
        cwd=cwd,
    )


def copy_file(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise BuildError("output collision")
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, 8 * 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())


def lz4_roundtrip(source: Path, frame: Path, scratch: Path) -> None:
    run_command(
        [LZ4, "--content-size", "-B6", "-f", "-q", source, frame],
        timeout=300,
    )
    run_command([LZ4, "-d", "-f", "-q", frame, scratch], timeout=300)
    if receipt(source) != receipt(scratch):
        raise BuildError("candidate LZ4 roundtrip changed recovery bytes")
    scratch.unlink()


def verify_existing_lz4(frame: Path, expected: Path, scratch: Path) -> None:
    run_command([LZ4, "-d", "-f", "-q", frame, scratch], timeout=300)
    if receipt(expected) != receipt(scratch):
        raise BuildError("stock recovery LZ4 frame does not decode exactly")
    scratch.unlink()


def write_recovery_ap(frame: Path, output: Path) -> dict[str, Any]:
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("recovery.img.lz4")
            info.size = frame.stat().st_size
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            with frame.open("rb") as source:
                archive.addfile(info, source)
        handle.flush()
        os.fsync(handle.fileno())
    prefix_md5 = hashlib.md5(output.read_bytes()).hexdigest()
    trailer = f"{prefix_md5}  AP.tar\n".encode("ascii")
    with output.open("ab") as handle:
        handle.write(trailer)
        handle.flush()
        os.fsync(handle.fileno())
    data = output.read_bytes()
    if not data.endswith(trailer):
        raise BuildError("AP MD5 trailer is absent")
    if hashlib.md5(data[: -len(trailer)]).hexdigest() != prefix_md5:
        raise BuildError("AP MD5 trailer does not bind the tar bytes")
    with tarfile.open(output, "r:") as archive:
        members = archive.getmembers()
    if (
        len(members) != 1
        or members[0].name != "recovery.img.lz4"
        or not members[0].isreg()
    ):
        raise BuildError("recovery-only AP membership changed")
    return {
        "members": ["recovery.img.lz4"],
        "tar_md5": prefix_md5,
        **receipt(output),
    }


def verify_avb(image: Path, work: Path, should_pass: bool) -> dict[str, Any]:
    work.mkdir(mode=0o700)
    local = work / "recovery.img"
    copy_file(image, local)
    output = run_command(
        [sys.executable, AVBTOOL, "verify_image", "--image", "recovery.img"],
        cwd=work,
        expected=(0,) if should_pass else (1,),
    )
    local.unlink()
    footer_ok = b"Successfully verified footer and SHA256_RSA4096 vbmeta struct" in output
    hash_ok = b"Successfully verified sha256 hash of recovery.img" in output
    hash_mismatch = b"does not match digest in descriptor" in output
    if should_pass:
        if not footer_ok or not hash_ok or hash_mismatch:
            raise BuildError("stock recovery AVB verification was not exact")
    elif not footer_ok or hash_ok or not hash_mismatch:
        raise BuildError("custom recovery AVB failure class changed")
    return {
        "embedded_vbmeta_signature_verified": footer_ok,
        "recovery_hash_descriptor_verified": hash_ok,
        "recovery_hash_descriptor_mismatch": hash_mismatch,
        "expected_result": "PASS_STOCK" if should_pass else "FAIL_MODIFIED_RAMDISK",
    }


def validate_inputs() -> dict[str, Any]:
    require_direct_file(
        BASE_RECOVERY,
        BASE_RECOVERY_SIZE,
        BASE_RECOVERY_SHA256,
        "stock recovery",
    )
    require_direct_file(
        BASE_RECOVERY_LZ4,
        BASE_RECOVERY_LZ4_SIZE,
        BASE_RECOVERY_LZ4_SHA256,
        "stock recovery LZ4",
    )
    require_direct_file(MAGISKBOOT, MAGISKBOOT_SIZE, MAGISKBOOT_SHA256, "magiskboot")
    require_direct_file(LZ4, LZ4_SIZE, LZ4_SHA256, "lz4")
    require_direct_file(AVBTOOL, AVBTOOL_SIZE, AVBTOOL_SHA256, "avbtool")
    with BASE_RECOVERY.open("rb") as stream:
        if stream.read(8) != b"ANDROID!":
            raise BuildError("stock recovery Android header is absent")
    return {
        "stock_recovery": receipt(BASE_RECOVERY),
        "stock_recovery_lz4": receipt(BASE_RECOVERY_LZ4),
        "magiskboot": receipt(MAGISKBOOT),
        "lz4": receipt(LZ4),
        "avbtool": receipt(AVBTOOL),
    }


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    inputs = validate_inputs()
    if output.exists() or output.is_symlink():
        raise BuildError("output directory already exists")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="s20plus-recovery-adb-canary-t0-", dir=output.parent
    ) as temporary:
        temporary_root = Path(temporary)
        payload = temporary_root / "payload"
        payload.mkdir(mode=0o700)
        candidate_dir = payload / "candidate"
        rollback_dir = payload / "rollback"
        candidate_dir.mkdir(mode=0o700)
        rollback_dir.mkdir(mode=0o700)

        unpack_dir = temporary_root / "stock-unpack"
        base_components = unpack_recovery(BASE_RECOVERY, unpack_dir)
        if base_components != BASE_COMPONENTS:
            raise BuildError("stock recovery component closure changed")
        stock_ramdisk = unpack_dir / "ramdisk.cpio"
        base_listing = cpio_listing(stock_ramdisk, unpack_dir)
        base_tree_dir = temporary_root / "base-tree"
        extract_cpio_tree(stock_ramdisk, base_tree_dir)
        base_tree = tree_manifest(base_tree_dir)

        base_prop = (base_tree_dir / PROP_ENTRY).read_bytes()
        base_rc = (base_tree_dir / RC_ENTRY).read_bytes()
        patched_prop = patch_prop_default(base_prop)
        patched_rc = patch_samsung_rc(base_rc)
        patch_dir = temporary_root / "patch-inputs"
        patch_dir.mkdir(mode=0o700)
        patched_prop_path = patch_dir / "prop.default"
        patched_rc_path = patch_dir / "init.recovery.samsung.rc"
        marker_path = patch_dir / "marker"
        patched_prop_path.write_bytes(patched_prop)
        patched_rc_path.write_bytes(patched_rc)
        marker_path.write_bytes(MARKER)

        add_cpio_file(stock_ramdisk, PROP_ENTRY, 0o644, patched_prop_path, unpack_dir)
        add_cpio_file(stock_ramdisk, RC_ENTRY, 0o750, patched_rc_path, unpack_dir)
        add_cpio_file(stock_ramdisk, MARKER_ENTRY, 0o444, marker_path, unpack_dir)
        candidate_listing = cpio_listing(stock_ramdisk, unpack_dir)
        candidate_tree_dir = temporary_root / "candidate-tree"
        extract_cpio_tree(stock_ramdisk, candidate_tree_dir)
        candidate_tree = tree_manifest(candidate_tree_dir)
        delta = prove_exact_delta(
            base_tree,
            candidate_tree,
            base_listing,
            candidate_listing,
            patched_prop,
            patched_rc,
        )

        candidate_image = candidate_dir / "recovery.img"
        run_command(
            [MAGISKBOOT, "repack", BASE_RECOVERY, candidate_image],
            cwd=unpack_dir,
        )
        if candidate_image.stat().st_size != BASE_RECOVERY_SIZE:
            raise BuildError("candidate recovery partition size changed")

        candidate_unpack = temporary_root / "candidate-unpack"
        candidate_components = unpack_recovery(candidate_image, candidate_unpack)
        for name in ("header", "kernel", "dtb", "recovery_dtbo"):
            if candidate_components[name] != BASE_COMPONENTS[name]:
                raise BuildError(f"candidate changed preserved component {name}")
        if candidate_components["ramdisk.cpio"]["sha256"] != sha256_file(stock_ramdisk):
            raise BuildError("candidate ramdisk does not match patched CPIO")

        stock_avb = verify_avb(BASE_RECOVERY, temporary_root / "stock-avb", True)
        candidate_avb = verify_avb(
            candidate_image, temporary_root / "candidate-avb", False
        )

        candidate_lz4 = candidate_dir / "recovery.img.lz4"
        lz4_roundtrip(
            candidate_image,
            candidate_lz4,
            temporary_root / "candidate-roundtrip.img",
        )
        candidate_ap = candidate_dir / "AP.tar.md5"
        candidate_ap_result = write_recovery_ap(candidate_lz4, candidate_ap)

        rollback_image = rollback_dir / "recovery.img"
        rollback_lz4 = rollback_dir / "recovery.img.lz4"
        copy_file(BASE_RECOVERY, rollback_image)
        copy_file(BASE_RECOVERY_LZ4, rollback_lz4)
        verify_existing_lz4(
            rollback_lz4,
            rollback_image,
            temporary_root / "rollback-roundtrip.img",
        )
        rollback_ap = rollback_dir / "AP.tar.md5"
        rollback_ap_result = write_recovery_ap(rollback_lz4, rollback_ap)

        manifest = {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "tier": "H0",
            "review_state": "REVIEW_PENDING",
            "live_authority": False,
            "target": TARGET,
            "inputs": inputs,
            "components": {
                "stock": base_components,
                "candidate": candidate_components,
                "preserved_exact": ["header", "kernel", "dtb", "recovery_dtbo"],
            },
            "ramdisk": {
                **delta,
                "property_changes": {
                    "ro.secure": "1->0",
                    "ro.adb.secure": "1->0 (two exact source rows)",
                    "ro.debuggable": "0->1",
                },
                "boot_trigger": [
                    "setprop service.adb.root 1",
                    "setprop sys.usb.config adb",
                ],
                "marker": {
                    "path": "/" + MARKER_ENTRY,
                    "size": len(MARKER),
                    "sha256": sha256_bytes(MARKER),
                    "mode": "0444",
                },
            },
            "avb": {
                "stock": stock_avb,
                "candidate": candidate_avb,
                "candidate_runtime_acceptance": "UNKNOWN_REQUIRES_REVIEWED_ATTENDED_T0",
            },
            "candidate": {
                "recovery_img": receipt(candidate_image),
                "recovery_img_lz4": receipt(candidate_lz4),
                "ap_tar_md5": candidate_ap_result,
            },
            "rollback": {
                "recovery_img": receipt(rollback_image),
                "recovery_img_lz4": receipt(rollback_lz4),
                "ap_tar_md5": rollback_ap_result,
                "exact_stock_bytes": True,
                "demonstrated_live_path": False,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "adb_commands": 0,
                "su_commands": 0,
                "reboot_commands": 0,
                "odin_commands": 0,
                "partition_transfers": 0,
                "vbmeta_payload": False,
                "vendor_mutation": False,
                "misc_write": False,
                "data_format": False,
                "live_flash_authorized": False,
                "policy_amendment_complete": False,
                "independent_review_complete": False,
            },
        }
        manifest_path = payload / "manifest.json"
        with manifest_path.open("xb") as handle:
            handle.write(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            )
            handle.flush()
            os.fsync(handle.fileno())

        for path in payload.rglob("*"):
            if path.is_file():
                path.chmod(0o400)
        os.rename(payload, output)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="absent private output directory; defaults to the fixed S20+ T0 path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve(strict=False)
    result = build(output)
    print(result["verdict"])
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
