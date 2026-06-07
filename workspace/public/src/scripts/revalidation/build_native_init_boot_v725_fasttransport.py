#!/usr/bin/env python3
"""Build the V725 fasttransport native init image.

V725 is a test-infrastructure baseline, not a Wi-Fi behavior change. It reuses
the V724 native init path and adds ramdisk-local transport helpers so NCM file
staging can be used without repeatedly pushing helper binaries through the slow
serial/base64 path.
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

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path


LINUX_INIT = REPO_ROOT / "workspace" / "public" / "src" / "native-init"
NATIVE_INIT_HELPERS = workspace_private_build_path("native-init", "helpers")
USERLAND_BIN = workspace_private_input_path("external_tools", "userland", "bin")
MKBOOTIMG_DIR = REPO_ROOT / "workspace" / "public" / "src" / "third_party" / "mkbootimg"
DEFAULT_BASE_BOOT = workspace_private_input_path("boot_images", "boot_linux_v724.img")
DEFAULT_INIT_SOURCE = LINUX_INIT / "init_v725_fasttransport.c"
DEFAULT_INIT_BINARY = workspace_private_build_path("native-init", "v725-fasttransport", "init_v725_fasttransport")
DEFAULT_RAMDISK_DIR = workspace_private_build_path("native-init", "v725-fasttransport", "ramdisk")
DEFAULT_RAMDISK_CPIO = workspace_private_build_path("native-init", "v725-fasttransport", "ramdisk.cpio")
DEFAULT_BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v725_fasttransport.img", legacy_fallback=False
)

RAMDISK_HELPERS = {
    "bin/a90sleep": NATIVE_INIT_HELPERS / "a90_sleep",
    "bin/a90_cpustress": NATIVE_INIT_HELPERS / "a90_cpustress",
    "bin/a90_longsoak": NATIVE_INIT_HELPERS / "a90_longsoak",
    "bin/a90_rshell": NATIVE_INIT_HELPERS / "a90_rshell",
    "bin/a90_tcpctl": USERLAND_BIN / "a90_tcpctl-aarch64-static",
    "bin/a90_usbnet": USERLAND_BIN / "a90_usbnet-aarch64-static",
    "bin/busybox": USERLAND_BIN / "busybox-aarch64-static-1.36.1",
    "bin/toybox": USERLAND_BIN / "toybox-aarch64-static-0.8.13",
}
EXTRA_CFLAGS = (
    '-DINIT_VERSION="0.9.244"',
    '-DINIT_BUILD="v725-fasttransport"',
    '-DNETSERVICE_USB_HELPER="/bin/a90_usbnet"',
    '-DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl"',
    '-DNETSERVICE_TOYBOX="/bin/toybox"',
    '-DA90_BUSYBOX_HELPER="/bin/busybox"',
)
EXPECTED_MARKERS = (
    "A90 Linux init 0.9.244 (v725-fasttransport)",
    "v725-fasttransport",
    "/bin/a90_usbnet",
    "/bin/toybox",
    "tcpctl skipped by ncm-only flag",
    "native-init-qrtr-servloc-boot-v724",
)
REPRODUCIBLE_MTIME = 0


def run(command: list[str | Path], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
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


def pid1_sources(args: argparse.Namespace) -> list[Path]:
    sources = [args.init_source]
    for path in sorted(LINUX_INIT.glob("a90_*.c")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "int main(" in text or "int main (" in text:
            continue
        sources.append(path)
    return sources


def build_init(args: argparse.Namespace) -> None:
    args.init_binary.parent.mkdir(parents=True, exist_ok=True)
    command = [
        args.cross_gcc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        *EXTRA_CFLAGS,
        "-o",
        args.init_binary,
        *pid1_sources(args),
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
    args.ramdisk_cpio.parent.mkdir(parents=True, exist_ok=True)
    command = "find . | LC_ALL=C sort | cpio --reproducible -o -H newc > " + shlex.quote(str(args.ramdisk_cpio))
    run(["bash", "-lc", command], cwd=args.ramdisk_dir)


def build_boot_image(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="a90-v725-unpack-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_args = run(
            [
                "python3",
                MKBOOTIMG_DIR / "unpack_bootimg.py",
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
        args.boot_image.parent.mkdir(parents=True, exist_ok=True)
        run([
            "python3",
            MKBOOTIMG_DIR / "mkbootimg.py",
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
    parser.add_argument("--init-source", type=Path, default=DEFAULT_INIT_SOURCE)
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
