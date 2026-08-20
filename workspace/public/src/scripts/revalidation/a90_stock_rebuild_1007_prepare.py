#!/usr/bin/env python3
"""Prepare an extracted A90 OSRC tree for a semantics-zero host rebuild.

The Samsung archive contains three CRLF Makefiles and duplicated audio/ION
headers in versioned locations.  Modern GNU make and the out-of-tree build do
not consume those bytes as Samsung's internal workspace did.  This helper only
normalizes line endings, copies already-present bytes to the paths referenced
by the build, and creates the two expected audio workspace symlinks.  It does
not patch C code, Kconfig, defconfig, compiler flags, or RKP/CFP scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


CRLF_PATHS = (
    "scripts/Makefile.lib",
    "drivers/input/wacom/Makefile",
    "drivers/gpu/drm/msm/samsung_lego/SELF_DISPLAY/Makefile",
)
ION_HEADERS = ("ion.h", "msm_ion.h")
AUDIO_SOC_FILES = (
    "core.h",
    "pinctrl-utils.h",
    "wcd-spi-ac.c",
    "wcd_spi_ctl_v01.c",
    "wcd_spi_ctl_v01.h",
)
AUDIO_INCLUDE_DIRS = ("soc", "dsp", "ipc", "uapi", "asoc")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular_file(path: Path) -> None:
    st = path.lstat()
    if not path.is_file() or path.is_symlink() or st.st_nlink != 1:
        raise ValueError(f"not one direct regular file: {path}")


def copy_exact(
    source: Path,
    target: Path,
    rows: list[dict[str, object]],
    root: Path,
) -> None:
    regular_file(source)
    data = source.read_bytes()
    target_kind = "regular"
    if target.is_symlink():
        resolved = target.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError(f"existing symlink escapes source root: {target}")
        if target.read_bytes() != data:
            raise ValueError(f"existing symlink bytes differ: {target}")
        created = False
        target_kind = "exact-byte-in-root-symlink"
    elif target.exists():
        regular_file(target)
        if target.read_bytes() != data:
            raise ValueError(f"existing target differs: {target}")
        created = False
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
        created = True
    rows.append(
        {
            "source": str(source),
            "target": str(target),
            "sha256": sha256(data),
            "size": len(data),
            "created": created,
            "targetKind": target_kind,
        }
    )


def copy_if_missing(
    source: Path,
    target: Path,
    copied: list[dict[str, object]],
    preserved: list[dict[str, object]],
    root: Path,
) -> None:
    if not target.exists() and not target.is_symlink():
        copy_exact(source, target, copied, root)
        return
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"existing include escapes source root: {target}")
    data = target.read_bytes()
    preserved.append(
        {
            "path": str(target),
            "sha256": sha256(data),
            "size": len(data),
            "kind": "in-root-symlink" if target.is_symlink() else "regular",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve(strict=True)
    if args.source_root.is_symlink() or not root.is_dir():
        raise ValueError("source root must be one direct directory")

    normalized: list[dict[str, object]] = []
    for relative in CRLF_PATHS:
        path = root / relative
        regular_file(path)
        before = path.read_bytes()
        count = before.count(b"\r\n")
        if count == 0 or before.replace(b"\r\n", b"\n").count(b"\r"):
            raise ValueError(f"unexpected line-ending shape: {relative}")
        after = before.replace(b"\r\n", b"\n")
        path.write_bytes(after)
        normalized.append(
            {
                "path": relative,
                "crlfCount": count,
                "beforeSha256": sha256(before),
                "afterSha256": sha256(after),
            }
        )

    copied: list[dict[str, object]] = []
    for name in ION_HEADERS:
        copy_exact(
            root / "drivers/staging/android/uapi" / name,
            root / "include/uapi/linux" / name,
            copied,
            root,
        )

    for name in AUDIO_SOC_FILES:
        copy_exact(
            root / "techpack/audio/4.0/soc" / name,
            root / "techpack/audio/soc" / name,
            copied,
            root,
        )

    preserved: list[dict[str, object]] = []
    for subdir in AUDIO_INCLUDE_DIRS:
        source_dir = root / "techpack/audio/4.0/include" / subdir
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise ValueError(f"missing audio include directory: {source_dir}")
        for source in sorted(source_dir.rglob("*")):
            if source.is_file():
                copy_if_missing(
                    source,
                    root / "techpack/audio/include" / subdir / source.relative_to(source_dir),
                    copied,
                    preserved,
                    root,
                )

    links: list[dict[str, str]] = []
    audio_root = root / "techpack/audio"
    for version in ("msm-4.14", "msm-4.19"):
        link = root / "out/kernel" / version / "techpack/audio"
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            raise ValueError(f"audio link target already exists: {link}")
        relative_target = os.path.relpath(audio_root, link.parent)
        link.symlink_to(relative_target)
        if link.resolve(strict=True) != audio_root:
            raise ValueError(f"audio link resolves incorrectly: {link}")
        links.append({"path": str(link), "target": relative_target})

    receipt = {
        "schema": "a90-stock-rebuild-1007-host-preparation-v1",
        "sourceRoot": str(root),
        "semanticSourceChanges": 0,
        "normalizedLineEndings": normalized,
        "exactByteCopies": copied,
        "existingIncludesPreserved": preserved,
        "workspaceSymlinks": links,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    args.receipt.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
