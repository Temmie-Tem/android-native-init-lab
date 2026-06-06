#!/usr/bin/env python3
"""Build the V641 firmware-backed native init boot image.

This builder recompiles the V641 PID1 binary, repacks a ramdisk with the same
trusted helper layout as V319, and reuses the verified V319 boot image header
arguments while replacing only the ramdisk. V641 is disabled by default and
only runs the firmware-backed sibling SSCTL proof when its one-shot flag exists.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
LINUX_INIT = REPO_ROOT / "stage3" / "linux_init"
DEFAULT_BASE_BOOT = REPO_ROOT / "stage3" / "boot_linux_v319.img"
DEFAULT_INIT_SOURCE = LINUX_INIT / "init_v641.c"
DEFAULT_INIT_BINARY = LINUX_INIT / "init_v641"
DEFAULT_RAMDISK_DIR = REPO_ROOT / "stage3" / "ramdisk_v641"
DEFAULT_RAMDISK_CPIO = REPO_ROOT / "stage3" / "ramdisk_v641.cpio"
DEFAULT_BOOT_IMAGE = REPO_ROOT / "stage3" / "boot_linux_v641.img"

RAMDISK_HELPERS = {
    "bin/a90sleep": LINUX_INIT / "a90_sleep",
    "bin/a90_cpustress": LINUX_INIT / "helpers" / "a90_cpustress",
    "bin/a90_longsoak": LINUX_INIT / "helpers" / "a90_longsoak",
    "bin/a90_rshell": LINUX_INIT / "helpers" / "a90_rshell",
}

EXPECTED_MARKERS = (
    "A90 Linux init 0.9.67 (v641)",
    "A90v641: sibling fwssctl proof armed",
    "A90v641: firmware mounts ready",
    "native-init-sibling-fwssctl-v641",
    "wifi-v641-fwssctl",
)
REPRODUCIBLE_MTIME = 0


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + shlex.join(str(item) for item in command), flush=True)
    return subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pid1_sources() -> list[Path]:
    sources = [DEFAULT_INIT_SOURCE]
    for path in sorted(LINUX_INIT.glob("a90_*.c")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "int main(" in text or "int main (" in text:
            continue
        sources.append(path)
    return sources


def build_init(args: argparse.Namespace) -> None:
    command = [
        args.cross_gcc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-o",
        args.init_binary,
        *pid1_sources(),
    ]
    run(command)
    run([args.strip, args.init_binary])
    run(["file", args.init_binary])


def build_ramdisk(args: argparse.Namespace) -> None:
    if args.ramdisk_dir.exists():
        shutil.rmtree(args.ramdisk_dir)
    (args.ramdisk_dir / "bin").mkdir(parents=True, mode=0o755)

    shutil.copy2(args.init_binary, args.ramdisk_dir / "init")
    for relative, source in RAMDISK_HELPERS.items():
        destination = args.ramdisk_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for path in [args.ramdisk_dir / "init", *(args.ramdisk_dir / item for item in RAMDISK_HELPERS)]:
        path.chmod(0o755)

    for path in sorted(args.ramdisk_dir.rglob("*"), key=lambda item: str(item), reverse=True):
        os.utime(path, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)
    os.utime(args.ramdisk_dir, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)

    if args.ramdisk_cpio.exists():
        args.ramdisk_cpio.unlink()
    command = "find . | LC_ALL=C sort | cpio --reproducible -o -H newc > " + shlex.quote(str(args.ramdisk_cpio))
    run(["bash", "-lc", command], cwd=args.ramdisk_dir)


def build_boot_image(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="a90-v641-unpack-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_args = run(
            [
                "python3",
                REPO_ROOT / "mkbootimg" / "unpack_bootimg.py",
                "--boot_img",
                args.base_boot,
                "--out",
                temp_dir,
                "--format=mkbootimg",
            ],
            capture=True,
        ).stdout
        mkboot_args = shlex.split(unpack_args)

        for index, item in enumerate(mkboot_args):
            if item == "--ramdisk":
                mkboot_args[index + 1] = str(args.ramdisk_cpio)
                break
        else:
            raise RuntimeError("base boot image mkbootimg args did not include --ramdisk")

        if args.boot_image.exists():
            args.boot_image.unlink()
        run([
            "python3",
            REPO_ROOT / "mkbootimg" / "mkbootimg.py",
            *mkboot_args,
            "--output",
            args.boot_image,
        ])


def verify_markers(args: argparse.Namespace) -> None:
    strings = run(["strings", args.boot_image], capture=True).stdout
    missing = [marker for marker in EXPECTED_MARKERS if marker not in strings]
    if missing:
        raise RuntimeError("missing boot image markers: " + ", ".join(missing))
    print("markers: pass", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-gcc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--init-binary", type=Path, default=DEFAULT_INIT_BINARY)
    parser.add_argument("--ramdisk-dir", type=Path, default=DEFAULT_RAMDISK_DIR)
    parser.add_argument("--ramdisk-cpio", type=Path, default=DEFAULT_RAMDISK_CPIO)
    parser.add_argument("--boot-image", type=Path, default=DEFAULT_BOOT_IMAGE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_init(args)
    build_ramdisk(args)
    build_boot_image(args)
    verify_markers(args)
    print(f"init_sha256={sha256(args.init_binary)}")
    print(f"ramdisk_sha256={sha256(args.ramdisk_cpio)}")
    print(f"boot_sha256={sha256(args.boot_image)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
