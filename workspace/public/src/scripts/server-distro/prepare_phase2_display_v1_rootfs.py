#!/usr/bin/env python3
"""Build an A/B-reproducible A90 Phase 2 Debian display host profile.

The builder clones the exact clean V3405 return-diagnostic ext4 image and adds
only the tracked VT-less display presenter, bounded sysvinit launcher, account
entries, inittab line, and stage description. It is host-only and grants no
candidate or device authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_DIR = SCRIPT_DIR / "phase2_display_v1"
MANIFEST_PATH = PROFILE_DIR / "manifest.toml"
PRIVATE_OUTPUTS = REPO_ROOT / "workspace/private/outputs"
SCHEMA = "a90-phase2-display-v1-rootfs"
PROFILE = "phase2-display-v1"
DISPLAY_UID = 3904
DISPLAY_GID = 3904
IMAGE_BYTES = 2 * 1024 * 1024 * 1024
TARGETS = {
    "presenter": "/usr/local/sbin/a90-debian-display-v1",
    "launcher": "/usr/local/sbin/a90-debian-display-launcher-v1",
    "inittab": "/etc/inittab",
    "stage": "/etc/a90-server-distro-stage",
    "passwd": "/etc/passwd",
    "group": "/etc/group",
}
HEX_DIGITS = frozenset("0123456789abcdef")


class ContractError(RuntimeError):
    """The Phase 2 display host profile is not closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in HEX_DIGITS for char in value)
    ):
        raise ContractError(f"{label} is not one lowercase SHA256")
    return value


def resolve_repo_file(relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ContractError(f"{label} path is empty")
    path = (REPO_ROOT / relative).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as error:
        raise ContractError(f"{label} escapes repository") from error
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"{label} is not one regular file: {path}")
    return path


def require_pinned_file(
    table: dict[str, Any],
    path_key: str,
    sha_key: str,
    label: str,
) -> Path:
    path = resolve_repo_file(table.get(path_key), label)
    expected = require_sha256(table.get(sha_key), f"{label} pin")
    actual = sha256_file(path)
    if actual != expected:
        raise ContractError(
            f"{label} changed: got {actual}, expected {expected}"
        )
    return path


def run(
    command: list[object],
    *,
    timeout: float = 120.0,
    check: bool = True,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=REPO_ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ContractError(
            f"command failed rc={result.returncode}: {command}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return result


def debugfs(
    image: Path,
    command: str,
    *,
    writable: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    argv: list[object] = ["debugfs"]
    if writable:
        argv.append("-w")
    argv.extend(("-R", command, image))
    return run(argv, timeout=60.0)


def debugfs_stat(image: Path, target: str) -> dict[str, int] | None:
    result = debugfs(image, f"stat {target}")
    text = (
        result.stdout + result.stderr
    ).decode("utf-8", errors="replace")
    if "Inode:" not in text:
        return None
    mode = re.search(r"\bMode:\s+0([0-7]{3,4})\b", text)
    owner = re.search(r"\bUser:\s+(\d+)\s+Group:\s+(\d+)\b", text)
    size = re.search(r"\bSize:\s+(\d+)\b", text)
    if mode is None or owner is None or size is None:
        raise ContractError(f"cannot parse debugfs stat for {target}")
    return {
        "mode": int(mode.group(1), 8),
        "uid": int(owner.group(1)),
        "gid": int(owner.group(2)),
        "size": int(size.group(1)),
    }


def debugfs_cat(image: Path, target: str) -> bytes:
    result = debugfs(image, f"cat {target}")
    if b"File not found" in result.stderr or b"File not found" in result.stdout:
        raise ContractError(f"ext4 path is absent: {target}")
    return result.stdout


def load_manifest() -> tuple[dict[str, Any], str]:
    if MANIFEST_PATH.is_symlink() or MANIFEST_PATH.parent.is_symlink():
        raise ContractError("manifest path must not use symlinks")
    try:
        raw = MANIFEST_PATH.read_bytes()
        manifest = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ContractError(f"cannot load manifest: {error}") from error
    if manifest.get("schema") != SCHEMA:
        raise ContractError(f"unsupported schema: {manifest.get('schema')!r}")
    if manifest.get("profile") != PROFILE:
        raise ContractError(f"unexpected profile: {manifest.get('profile')!r}")
    if manifest.get("candidate_authority") is not False:
        raise ContractError("display host profile must grant no candidate authority")
    expected_keys = {
        "schema",
        "profile",
        "candidate_authority",
        "base",
        "toolchain",
        "sources",
        "validation",
    }
    unknown = sorted(set(manifest) - expected_keys)
    if unknown:
        raise ContractError(f"unknown manifest keys: {unknown}")
    return manifest, hashlib.sha256(raw).hexdigest()


def validate_presenter_source(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        "validate_native_release_marker()",
        "count_process_state(",
        "initialize_kms(&kms)",
        "ensure_card0_node(&kms->drm_major, &kms->drm_minor)",
        "O_RDWR | O_CLOEXEC | O_NOFOLLOW",
        "fcntl(kms->fd, F_SETFD, fd_flags | FD_CLOEXEC)",
        "if (drm_ioctl_retry(kms->fd, DRM_IOCTL_SET_MASTER, NULL) < 0)",
        "DRM_IOCTL_MODE_CREATE_DUMB",
        "DRM_IOCTL_MODE_ADDFB2",
        "DRM_IOCTL_MODE_MAP_DUMB",
        "DRM_IOCTL_MODE_SETCRTC",
        "drop_privileges(",
        "read_cap_eff(cap_eff, cap_eff_size)",
        "PR_SET_NO_NEW_PRIVS",
        "presenter_cap_eff=%s",
        "drm_node_major_minor=%u:%u",
        'strcmp(cap_eff, "0000000000000000")',
        "self_drm_fds != 1U",
        "other_drm_fds != 0U",
        "native_init_processes != 0U",
        "cleanup_kms(&kms)",
        "DRM_IOCTL_MODE_RMFB",
        "DRM_IOCTL_MODE_DESTROY_DUMB",
        "DRM_IOCTL_DROP_MASTER",
    )
    for token in required:
        if token not in text:
            issues.append(f"presenter missing token: {token}")
    forbidden = (
        "(void)drm_ioctl_retry(kms->fd, DRM_IOCTL_SET_MASTER",
        "socket(",
        "connect(",
        "bind(",
        "listen(",
        "accept(",
        "openvt",
        "chvt",
        "VT_ACTIVATE",
        "KDSETMODE",
        "system(",
        "popen(",
        "/proc/sysrq-trigger",
        "/sbin/reboot",
        "sync();",
    )
    for token in forbidden:
        if token in text:
            issues.append(f"presenter contains forbidden token: {token}")
    marker_pos = text.find("validate_native_release_marker()")
    scan_pos = text.find("count_process_state(", marker_pos)
    init_pos = text.find("initialize_kms(&kms)", scan_pos)
    drop_pos = text.find("drop_privileges(", init_pos)
    present_pos = text.find("present(&kms)", drop_pos)
    if (
        min(marker_pos, scan_pos, init_pos, drop_pos, present_pos) < 0
        or not marker_pos < scan_pos < init_pos < drop_pos < present_pos
    ):
        issues.append(
            "presenter order must be release-marker, zero-owner scan, "
            "KMS init, privilege drop, present"
        )
    return tuple(issues)


def validate_launcher(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        "PRESENTER=/usr/local/sbin/a90-debian-display-v1",
        "DISPLAY_UID=3904",
        "DISPLAY_GID=3904",
        "MAX_ATTEMPTS=3",
        'while [ "$attempt" -le "$MAX_ATTEMPTS" ]',
        'if "$PRESENTER"',
        "schema=a90-debian-display-v1-failure",
        "exit 1",
    )
    for token in required:
        if token not in text:
            issues.append(f"launcher missing token: {token}")
    for token in (
        "while true",
        "respawn",
        "openvt",
        "chvt",
        "socket",
        "curl",
        "wget",
        "dropbear",
        "ncm0",
        "sync",
        "reboot",
        "sysrq",
        "http://",
        "https://",
    ):
        if token in text:
            issues.append(f"launcher contains forbidden token: {token}")
    return tuple(issues)


def validate_inittab(text: str) -> tuple[str, ...]:
    required_lines = (
        "id:2:initdefault:",
        "si::sysinit:/etc/a90-d3-firstboot",
        "ds:2:once:/usr/local/sbin/a90-debian-display-launcher-v1",
        "ca:12345:ctrlaltdel:/sbin/reboot -f",
    )
    lines = tuple(
        line for line in text.splitlines()
        if line and not line.startswith("#")
    )
    if lines != required_lines:
        return (f"inittab lines differ: {lines!r}",)
    if "respawn" in text or "getty" in text or "openvt" in text:
        return ("inittab contains a VT or unbounded-respawn path",)
    return ()


def validate_tools(manifest: dict[str, Any]) -> dict[str, str]:
    toolchain = manifest["toolchain"]
    required = (
        toolchain["cc"],
        toolchain["strip"],
        toolchain["readelf"],
        "cp",
        "debugfs",
        "e2fsck",
        "file",
        "tune2fs",
    )
    for tool in required:
        if shutil.which(tool) is None:
            raise ContractError(f"missing required host tool: {tool}")
    versions = {
        "gcc": run([toolchain["cc"], "--version"]).stdout.decode().splitlines()[0],
        "strip": run([toolchain["strip"], "--version"]).stdout.decode().splitlines()[0],
        "debugfs": run(["debugfs", "-V"]).stderr.decode().splitlines()[0],
    }
    for key in ("gcc", "strip"):
        expected = toolchain[f"{key}_version"]
        if versions[key] != expected:
            raise ContractError(
                f"{key} version changed: got {versions[key]!r}, "
                f"expected {expected!r}"
            )
    return versions


def validate_base(
    manifest: dict[str, Any],
    base_image: Path,
    base_summary: Path,
) -> None:
    if base_image.stat().st_size != IMAGE_BYTES:
        raise ContractError("base image is not exactly 2 GiB")
    summary = json.loads(base_summary.read_text(encoding="utf-8"))
    if summary.get("decision") != "a90-d3-v3405-return-diagnostic-host-pass":
        raise ContractError("base summary decision is not the V3405 host pass")
    image = summary.get("image", {})
    if image.get("sha256") != manifest["base"]["image_sha256"]:
        raise ContractError("base summary does not bind the selected image")
    required = {
        "/sbin/init": (0o755, 0, 0),
        "/etc/inittab": (0o644, 0, 0),
        "/etc/a90-d3-firstboot": (0o755, 0, 0),
        "/usr/local/sbin/a90-d3-return-supervisor-v3405": (0o755, 0, 0),
        "/usr/local/sbin": (0o755, 0, 0),
        "/run": (0o755, 0, 0),
    }
    for target, expected in required.items():
        metadata = debugfs_stat(base_image, target)
        if metadata is None:
            raise ContractError(f"base image lacks {target}")
        actual = (metadata["mode"], metadata["uid"], metadata["gid"])
        if actual != expected:
            raise ContractError(
                f"base metadata changed for {target}: "
                f"got {actual}, expected {expected}"
            )
    for target in (
        TARGETS["presenter"],
        TARGETS["launcher"],
        "/run/a90-native-display-release",
        "/run/a90-display/ready",
    ):
        if debugfs_stat(base_image, target) is not None:
            raise ContractError(f"base image contains Phase 2 runtime path: {target}")


def audit() -> dict[str, Any]:
    manifest, manifest_sha256 = load_manifest()
    base = manifest["base"]
    sources = manifest["sources"]
    base_image = require_pinned_file(
        base, "image", "image_sha256", "base image"
    )
    base_summary = require_pinned_file(
        base, "summary", "summary_sha256", "base summary"
    )
    presenter = require_pinned_file(
        sources, "presenter", "presenter_sha256", "presenter source"
    )
    launcher = require_pinned_file(
        sources, "launcher", "launcher_sha256", "launcher"
    )
    inittab = require_pinned_file(
        sources, "inittab", "inittab_sha256", "inittab"
    )
    stage = require_pinned_file(
        sources, "stage", "stage_sha256", "stage"
    )
    draw_c = require_pinned_file(
        sources, "draw_c", "draw_c_sha256", "draw source"
    )
    draw_h = require_pinned_file(
        sources, "draw_h", "draw_h_sha256", "draw header"
    )
    kms_h = require_pinned_file(
        sources, "kms_h", "kms_h_sha256", "KMS header"
    )
    builder = require_pinned_file(
        sources, "builder", "builder_sha256", "rootfs builder"
    )
    issues = [
        *validate_presenter_source(presenter.read_text(encoding="utf-8")),
        *validate_launcher(launcher.read_text(encoding="utf-8")),
        *validate_inittab(inittab.read_text(encoding="utf-8")),
    ]
    if issues:
        raise ContractError("; ".join(issues))
    versions = validate_tools(manifest)
    validate_base(manifest, base_image, base_summary)
    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "base_image": base_image,
        "base_summary": base_summary,
        "presenter": presenter,
        "launcher": launcher,
        "inittab": inittab,
        "stage": stage,
        "draw_c": draw_c,
        "draw_h": draw_h,
        "kms_h": kms_h,
        "builder": builder,
        "tool_versions": versions,
        "source_sha256": {
            key: sha256_file(path)
            for key, path in (
                ("presenter", presenter),
                ("launcher", launcher),
                ("inittab", inittab),
                ("stage", stage),
                ("draw_c", draw_c),
                ("draw_h", draw_h),
                ("kms_h", kms_h),
                ("builder", builder),
            )
        },
    }


def output_root(requested: Path) -> Path:
    resolved = requested.resolve()
    try:
        relative = resolved.relative_to(PRIVATE_OUTPUTS.resolve())
    except ValueError as error:
        raise ContractError(
            f"output must stay under {PRIVATE_OUTPUTS.resolve()}"
        ) from error
    if not relative.parts:
        raise ContractError("output cannot be the private outputs root")
    if resolved.exists() or resolved.is_symlink():
        raise FileExistsError(f"absent-only output exists: {resolved}")
    return resolved


def build_presenter(
    audit_state: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    manifest = audit_state["manifest"]
    toolchain = manifest["toolchain"]
    native_root = (REPO_ROOT / "workspace/public/src/native-init").resolve()
    profile_root = PROFILE_DIR.resolve()
    command = [
        toolchain["cc"],
        "-std=gnu11",
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wl,--build-id=none",
        "-frandom-seed=a90-phase2-display-v1",
        f"-ffile-prefix-map={native_root}=/usr/src/a90/native-init",
        f"-fmacro-prefix-map={native_root}=/usr/src/a90/native-init",
        f"-fdebug-prefix-map={native_root}=/usr/src/a90/native-init",
        f"-ffile-prefix-map={profile_root}=/usr/src/a90/phase2-display-v1",
        f"-fmacro-prefix-map={profile_root}=/usr/src/a90/phase2-display-v1",
        f"-fdebug-prefix-map={profile_root}=/usr/src/a90/phase2-display-v1",
        f"-I{native_root}",
        audit_state["presenter"],
        audit_state["draw_c"],
        "-o",
        output,
    ]
    run(command)
    run([toolchain["strip"], output])
    output.chmod(0o700)
    file_text = run(["file", output]).stdout.decode().strip()
    if (
        "ELF 64-bit LSB executable, ARM aarch64" not in file_text
        or "statically linked" not in file_text
    ):
        raise ContractError(f"unexpected presenter binary: {file_text}")
    dynamic = run([toolchain["readelf"], "-d", output])
    if b"There is no dynamic section" not in dynamic.stdout + dynamic.stderr:
        raise ContractError("presenter contains a dynamic section")
    program = run([toolchain["readelf"], "-l", output])
    if b"INTERP" in program.stdout:
        raise ContractError("presenter contains an interpreter segment")
    return {
        "sha256": sha256_file(output),
        "bytes": output.stat().st_size,
        "file": file_text,
        "command": [str(item) for item in command],
    }


def generate_accounts(base_image: Path, overlay: Path) -> tuple[Path, Path]:
    passwd_text = debugfs_cat(base_image, "/etc/passwd").decode("utf-8")
    group_text = debugfs_cat(base_image, "/etc/group").decode("utf-8")
    if (
        "a90display:" in passwd_text
        or re.search(rf"^[^:]*:[^:]*:{DISPLAY_UID}:", passwd_text, re.MULTILINE)
        or "a90display:" in group_text
        or re.search(rf"^[^:]*:[^:]*:{DISPLAY_GID}:", group_text, re.MULTILINE)
    ):
        raise ContractError("display identity collides with the base account files")
    if not passwd_text.endswith("\n") or not group_text.endswith("\n"):
        raise ContractError("base account files lack final newline")
    passwd = overlay / "passwd"
    group = overlay / "group"
    passwd.write_text(
        passwd_text
        + "a90display:x:3904:3904:A90 display:/nonexistent:/usr/sbin/nologin\n",
        encoding="utf-8",
    )
    group.write_text(
        group_text + "a90display:x:3904:\n",
        encoding="utf-8",
    )
    passwd.chmod(0o600)
    group.chmod(0o600)
    return passwd, group


def set_inode_metadata(
    image: Path,
    target: str,
    *,
    mode: int,
    uid: int,
    gid: int,
) -> None:
    fields = (
        ("mode", f"0100{mode:03o}"),
        ("uid", str(uid)),
        ("gid", str(gid)),
        ("atime", "0"),
        ("ctime", "0"),
        ("mtime", "0"),
        ("crtime", "0"),
    )
    for field, value in fields:
        debugfs(
            image,
            f"set_inode_field {target} {field} {value}",
            writable=True,
        )


def replace_ext4_file(
    image: Path,
    source: Path,
    target: str,
    *,
    mode: int,
    uid: int = 0,
    gid: int = 0,
) -> dict[str, Any]:
    source_path = str(source.resolve())
    if (
        not source.is_file()
        or source.is_symlink()
        or re.fullmatch(r"/[A-Za-z0-9._/-]+", source_path) is None
        or re.fullmatch(r"/[A-Za-z0-9._/-]+", target) is None
    ):
        raise ContractError(f"unsafe ext4 overlay path: {source} -> {target}")
    if debugfs_stat(image, target) is not None:
        debugfs(image, f"rm {target}", writable=True)
        if debugfs_stat(image, target) is not None:
            raise ContractError(f"debugfs did not remove {target}")
    debugfs(image, f"write {source_path} {target}", writable=True)
    set_inode_metadata(image, target, mode=mode, uid=uid, gid=gid)
    metadata = debugfs_stat(image, target)
    expected = {
        "mode": mode,
        "uid": uid,
        "gid": gid,
        "size": source.stat().st_size,
    }
    if metadata != expected:
        raise ContractError(
            f"metadata mismatch for {target}: got {metadata}, expected {expected}"
        )
    content_sha256 = hashlib.sha256(debugfs_cat(image, target)).hexdigest()
    source_sha256 = sha256_file(source)
    if content_sha256 != source_sha256:
        raise ContractError(f"content mismatch for {target}")
    return {
        "target": target,
        **metadata,
        "sha256": content_sha256,
    }


def normalize_ext4_metadata(image: Path) -> None:
    for target in ("/etc", "/usr/local/sbin"):
        for field in ("atime", "ctime", "mtime", "crtime"):
            debugfs(
                image,
                f"set_inode_field {target} {field} 0",
                writable=True,
            )
    commands = "\n".join(
        (
            "set_current_time 1",
            (
                "set_super_value volume_name "
                f"{PROFILE.upper().replace('-', '')[:16]}"
            ),
            "set_super_value mtime 0",
            "set_super_value lastcheck 0",
            "",
        )
    ).encode("ascii")
    run(
        ["debugfs", "-w", image],
        timeout=60.0,
        input_bytes=commands,
    )


def build_image(
    audit_state: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    root.mkdir(parents=True, mode=0o700)
    overlay = root / "overlay"
    overlay.mkdir(mode=0o700)
    presenter = root / "a90-debian-display-v1"
    presenter_meta = build_presenter(audit_state, presenter)
    launcher_copy = overlay / "a90-debian-display-launcher-v1"
    inittab_copy = overlay / "inittab"
    stage_copy = overlay / "a90-server-distro-stage"
    shutil.copyfile(audit_state["launcher"], launcher_copy)
    shutil.copyfile(audit_state["inittab"], inittab_copy)
    shutil.copyfile(audit_state["stage"], stage_copy)
    launcher_copy.chmod(0o700)
    inittab_copy.chmod(0o600)
    stage_copy.chmod(0o600)
    passwd, group = generate_accounts(audit_state["base_image"], overlay)

    image = root / "phase2-display-v1.img"
    run(
        [
            "cp",
            "--reflink=auto",
            "--sparse=always",
            audit_state["base_image"],
            image,
        ],
        timeout=300.0,
    )
    image.chmod(0o600)
    if sha256_file(image) != audit_state["manifest"]["base"]["image_sha256"]:
        raise ContractError("pre-overlay clone differs from the pinned base")
    overlays = [
        replace_ext4_file(
            image, presenter, TARGETS["presenter"], mode=0o755
        ),
        replace_ext4_file(
            image, launcher_copy, TARGETS["launcher"], mode=0o755
        ),
        replace_ext4_file(
            image, inittab_copy, TARGETS["inittab"], mode=0o644
        ),
        replace_ext4_file(
            image, stage_copy, TARGETS["stage"], mode=0o644
        ),
        replace_ext4_file(
            image, passwd, TARGETS["passwd"], mode=0o644
        ),
        replace_ext4_file(
            image, group, TARGETS["group"], mode=0o644
        ),
    ]
    normalize_ext4_metadata(image)
    fsck = run(["e2fsck", "-fn", image], timeout=300.0, check=False)
    if fsck.returncode != 0:
        raise ContractError(
            "read-only e2fsck failed: "
            + (fsck.stdout + fsck.stderr).decode("utf-8", errors="replace")[-2000:]
        )
    if image.stat().st_size != IMAGE_BYTES:
        raise ContractError("output image size changed")
    for target in (TARGETS["presenter"], TARGETS["launcher"]):
        metadata = debugfs_stat(image, target)
        if metadata is None or metadata["mode"] != 0o755:
            raise ContractError(f"output image lost executable: {target}")
    return {
        "presenter": presenter_meta,
        "image": {
            "path": image,
            "sha256": sha256_file(image),
            "bytes": image.stat().st_size,
        },
        "overlays": overlays,
        "e2fsck_read_only_rc": fsck.returncode,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def serializable_build(value: dict[str, Any], root: Path) -> dict[str, Any]:
    result = json.loads(
        json.dumps(
            value,
            default=lambda item: str(item.relative_to(root)),
        )
    )
    return result


def build_ab(requested: Path) -> dict[str, Any]:
    root = output_root(requested)
    audit_state = audit()
    base_before = sha256_file(audit_state["base_image"])
    root.mkdir(parents=True, mode=0o700)
    build_a = build_image(audit_state, root / "A")
    build_b = build_image(audit_state, root / "B")
    binary_identical = filecmp.cmp(
        root / "A/a90-debian-display-v1",
        root / "B/a90-debian-display-v1",
        shallow=False,
    )
    image_identical = filecmp.cmp(
        root / "A/phase2-display-v1.img",
        root / "B/phase2-display-v1.img",
        shallow=False,
    )
    source_unchanged = all(
        sha256_file(audit_state[key]) == digest
        for key, digest in audit_state["source_sha256"].items()
    )
    base_unchanged = sha256_file(audit_state["base_image"]) == base_before
    receipt = {
        "schema": "a90-phase2-display-v1-ab-receipt",
        "profile": PROFILE,
        "candidate_authority": False,
        "timestamp_utc": (
            dt.datetime.now(dt.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "manifest_sha256": audit_state["manifest_sha256"],
        "source_sha256": audit_state["source_sha256"],
        "base": {
            "image_sha256": audit_state["manifest"]["base"]["image_sha256"],
            "summary_sha256": audit_state["manifest"]["base"]["summary_sha256"],
            "unchanged": base_unchanged,
        },
        "tool_versions": audit_state["tool_versions"],
        "A": serializable_build(build_a, root),
        "B": serializable_build(build_b, root),
        "presenter_byte_identical": binary_identical,
        "image_byte_identical": image_identical,
        "source_unchanged": source_unchanged,
        "host_only": True,
        "device_action": False,
        "flash": False,
    }
    write_json(root / "ab-receipt.json", receipt)
    if not all(
        (
            binary_identical,
            image_identical,
            source_unchanged,
            base_unchanged,
        )
    ):
        raise ContractError("A/B or immutable-input closure failed")
    return receipt


def audit_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "candidate_authority": False,
        "manifest_sha256": state["manifest_sha256"],
        "base_image_sha256": state["manifest"]["base"]["image_sha256"],
        "base_summary_sha256": state["manifest"]["base"]["summary_sha256"],
        "source_sha256": state["source_sha256"],
        "tool_versions": state["tool_versions"],
        "host_only": True,
        "device_action": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--audit-only", action="store_true")
    outputs.add_argument("--ab-root", type=Path)
    args = parser.parse_args(argv)
    os.environ.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    if args.audit_only:
        print(json.dumps(audit_payload(audit()), indent=2, sort_keys=True))
        return 0
    assert args.ab_root is not None
    print(json.dumps(build_ab(args.ab_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
