#!/usr/bin/env python3
"""Clean leftover legacy root stage3 native-init build artifacts.

The active source/build layout no longer writes to the repository-root
`stage3/` tree.  Historical tracked source lives under
`workspace/public/archive/stage3/`, and active generated outputs live under
`workspace/private/`.  This tool is retained only to remove a recreated legacy
root `stage3/` scratch tree.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
LEGACY_ROOT_STAGE3 = ROOT / "stage3"
LINUX_INIT = LEGACY_ROOT_STAGE3 / "linux_init"
HELPERS = LINUX_INIT / "helpers"
DEFAULT_KEEP = ("v48", "v724", "v725", "v726")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove old ignored root stage3 artifacts if a legacy tree is recreated."
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=list(DEFAULT_KEEP),
        metavar="vNN",
        help="build tag to keep; may be repeated (default: v48, v724, v725, v726)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually delete files; without this flag the command is a dry run",
    )
    parser.add_argument(
        "--include-boot-init",
        action="store_true",
        help="also remove legacy root stage3/boot_linux_init.img when executing cleanup",
    )
    return parser.parse_args()


def build_tag_from_name(path: Path) -> str | None:
    match = re.search(r"_v([0-9]+[a-z]?)", path.name)
    if not match:
        return None
    return f"v{match.group(1)}"


def candidate_paths(include_boot_init: bool) -> list[Path]:
    candidates: list[Path] = []

    for pattern in ("boot_linux_v*.img", "ramdisk_v*.cpio", "ramdisk_v*"):
        candidates.extend(LEGACY_ROOT_STAGE3.glob(pattern))

    if include_boot_init:
        boot_init = LEGACY_ROOT_STAGE3 / "boot_linux_init.img"
        if boot_init.exists():
            candidates.append(boot_init)

    for path in LINUX_INIT.glob("init_v*"):
        if path.is_file() and path.suffix == "":
            candidates.append(path)

    if HELPERS.exists():
        for path in HELPERS.glob("*_v[0-9]*"):
            if path.is_file() and path.suffix == "":
                candidates.append(path)

    return sorted(set(candidates), key=lambda item: str(item))


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    args = parse_args()
    keep = {tag.lower() for tag in args.keep}
    candidates = candidate_paths(args.include_boot_init)
    removable: list[Path] = []
    kept: list[Path] = []

    for path in candidates:
        tag = build_tag_from_name(path)
        if tag and tag.lower() in keep:
            kept.append(path)
            continue
        removable.append(path)

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"mode: {mode}")
    print(f"legacy_root_stage3_present: {int(LEGACY_ROOT_STAGE3.exists())}")
    print(f"keep: {', '.join(sorted(keep))}")
    print(f"kept: {len(kept)}")
    print(f"remove: {len(removable)}")

    for path in removable:
        print(f"remove {path.relative_to(ROOT)}")
        if args.execute:
            remove_path(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
