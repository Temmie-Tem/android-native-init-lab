#!/usr/bin/env python3
"""Build a Debian aarch64 rootfs + ext4 loop image for the native-init server endgame (D0/B.1).

Reproducible host-side builder. Produces a private, gitignored rootfs tree and an ext4 image
suitable for SD-card loop staging in D1 (chroot MVP). NO device action; NO Android touch.

Pipeline (single sudo invocation):
  1. debootstrap --arch=arm64 <suite> into the rootfs dir (qemu-aarch64 binfmt handles arm64).
  2. customize inside the rootfs (chroot, via binfmt): install dropbear (MVP SSH) + minimal tools,
     install the opt-in D-public Wi-Fi STA helpers and native Wi-Fi service client, set hostname,
     LOCK the root password, and disable password SSH defaults.
  3. pack the rootfs into an ext4 image with `mke2fs -d` (no loop mount / no root-mount needed).
  4. report image size + SHA-256; chown outputs back to the invoking user.

Run as root (sudo). Requires: debootstrap, qemu-user-binfmt (aarch64 F-flag), mke2fs (e2fsprogs).

Example:
  sudo python3 workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py

Design ref: docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md (B=Debian, C.1=SD),
            docs/plans/NATIVE_INIT_SERVER_DISTRO_D0_INVENTORY_CHARTER_2026-07-01.md (B.1).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = REPO_ROOT / "workspace/private/builds/server-distro"
DEFAULT_SUITE = "bookworm"  # Debian 12, glibc 2.36 — conservative for the stock 4.14.190 kernel.
DEFAULT_MIRROR = "http://deb.debian.org/debian"
DEFAULT_ARCH = "arm64"
# minbase + the bring-up tools we actually need for the chroot/SSH MVP.
INCLUDE_PKGS = ",".join((
    "dropbear-bin",
    "openssh-client",
    "ca-certificates",
    "iproute2",
    "iputils-ping",
    "wpasupplicant",
    "isc-dhcp-client",
    "netcat-openbsd",
    "nano",
    "less",
    "procps",
))
DPUBLIC_WIFI_STA_HELPER = SCRIPT_DIR / "a90_dpublic_wifi_sta.sh"
DPUBLIC_WIFI_STA_TARGET = Path("usr/local/bin/a90-dpublic-wifi-sta")
NATIVE_WIFI_SERVICE_CLIENT = SCRIPT_DIR / "a90_native_wifi_service_client.sh"
NATIVE_WIFI_SERVICE_CLIENT_TARGET = Path("usr/local/bin/a90-native-wifi-service-client")
NATIVE_WIFI_UPLINK_CLIENT = SCRIPT_DIR / "a90_native_wifi_uplink_client.sh"
NATIVE_WIFI_UPLINK_CLIENT_TARGET = Path("usr/local/bin/a90-native-wifi-uplink-client")
DPUBLIC_NATIVE_UPLINK_PROFILE = SCRIPT_DIR / "a90_dpublic_native_uplink_profile.sh"
DPUBLIC_NATIVE_UPLINK_PROFILE_TARGET = Path("usr/local/bin/a90-dpublic-native-uplink-profile")


def run(cmd: list[str], **kw) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, **kw)


def require_tools() -> None:
    for tool in ("debootstrap", "mke2fs"):
        if shutil.which(tool) is None:
            sys.exit(f"missing required tool: {tool} (install debootstrap / e2fsprogs)")
    binfmt = Path("/proc/sys/fs/binfmt_misc/qemu-aarch64")
    if not binfmt.exists():
        sys.exit("aarch64 binfmt not registered (install qemu-user-binfmt + binfmt-support)")


def stage_debootstrap(rootfs: Path, suite: str, arch: str, mirror: str) -> None:
    if (rootfs / "etc/os-release").exists():
        print(f"= rootfs already bootstrapped at {rootfs}, skipping debootstrap")
        return
    rootfs.parent.mkdir(parents=True, exist_ok=True)
    run([
        "debootstrap", "--arch", arch, "--variant=minbase",
        f"--include={INCLUDE_PKGS}", suite, str(rootfs), mirror,
    ])


def chroot_run(rootfs: Path, script: str) -> None:
    run(["chroot", str(rootfs), "/bin/sh", "-c", script])


def stage_server_distro_helpers(rootfs: Path) -> None:
    helper_targets = (
        (DPUBLIC_WIFI_STA_HELPER, rootfs / DPUBLIC_WIFI_STA_TARGET),
        (NATIVE_WIFI_SERVICE_CLIENT, rootfs / NATIVE_WIFI_SERVICE_CLIENT_TARGET),
        (NATIVE_WIFI_UPLINK_CLIENT, rootfs / NATIVE_WIFI_UPLINK_CLIENT_TARGET),
        (DPUBLIC_NATIVE_UPLINK_PROFILE, rootfs / DPUBLIC_NATIVE_UPLINK_PROFILE_TARGET),
    )
    for source, helper_target in helper_targets:
        helper_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, helper_target)
        helper_target.chmod(0o755)
    (rootfs / "etc/a90-dpublic").mkdir(parents=True, exist_ok=True)


def stage_customize(rootfs: Path, hostname: str) -> None:
    # Provide DNS for any in-chroot apt step; harmless leftover removed at the end.
    resolv = rootfs / "etc/resolv.conf"
    resolv.write_text("nameserver 1.1.1.1\nnameserver 8.8.8.8\n")
    (rootfs / "etc/hostname").write_text(hostname + "\n")

    # Hygiene (design E.6): LOCK root password, no default-credential rootfs leaves this build.
    # dropbear MVP runs key-only; an operator sets a real password / installs keys before D1 use.
    chroot_run(rootfs, "passwd -l root")
    stage_server_distro_helpers(rootfs)
    # Mark the build provenance so an operator can tell staged-but-unconfigured rootfs apart.
    (rootfs / "etc/a90-server-distro-stage").write_text(
        "stage=D0/B.1 unconfigured\n"
        "root-password=LOCKED\n"
        "ssh=dropbear key-only, NO keys installed yet\n"
        "wifi-sta=opt-in via /etc/a90-dpublic/wifi-sta-enable, private config not included\n"
        "wifi-sta-helper=/usr/local/bin/a90-dpublic-wifi-sta\n"
        "native-wifi-service-client=/usr/local/bin/a90-native-wifi-service-client\n"
        "native-wifi-uplink-client=/usr/local/bin/a90-native-wifi-uplink-client\n"
        "native-uplink-profile=/usr/local/bin/a90-dpublic-native-uplink-profile\n"
        "native-uplink=operator-controlled via /etc/a90-dpublic/native-uplink-enable\n"
        "public-exposure-default=off; quick-tunnel requires /etc/a90-dpublic/cloudflared-quick-enable\n"
        "WARNING: configure credentials/keys before any network/public exposure (design E.6)\n"
    )
    resolv.unlink(missing_ok=True)


def stage_image(rootfs: Path, image: Path, size: str, label: str) -> None:
    if image.exists():
        image.unlink()
    # mke2fs -d builds a populated ext4 image from a directory WITHOUT mounting / loop / root-mount.
    run([
        "mke2fs", "-q", "-t", "ext4", "-L", label,
        "-d", str(rootfs), str(image), size,
    ])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chown_back(paths: list[Path]) -> None:
    uid = os.environ.get("SUDO_UID")
    gid = os.environ.get("SUDO_GID")
    if not (uid and gid):
        return
    for p in paths:
        if p.exists():
            run(["chown", "-R", f"{uid}:{gid}", str(p)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", default=DEFAULT_SUITE)
    ap.add_argument("--arch", default=DEFAULT_ARCH)
    ap.add_argument("--mirror", default=DEFAULT_MIRROR)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hostname", default="a90-server")
    ap.add_argument("--image-size", default="2G")
    ap.add_argument("--skip-image", action="store_true", help="bootstrap+customize only, no ext4 image")
    args = ap.parse_args()

    if os.geteuid() != 0:
        sys.exit("must run as root (sudo): debootstrap creates device nodes / sets ownership")
    require_tools()

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    rootfs = args.out_dir / f"debian-{args.suite}-{args.arch}-rootfs"
    image = args.out_dir / f"debian-{args.suite}-{args.arch}-{ts}.img"
    label = "A90ROOT"

    stage_debootstrap(rootfs, args.suite, args.arch, args.mirror)
    stage_customize(rootfs, args.hostname)
    outputs = [rootfs]
    if not args.skip_image:
        stage_image(rootfs, image, args.image_size, label)
        outputs.append(image)
    # Include out_dir so the parent dir created under sudo is not left root-owned.
    chown_back([args.out_dir, *outputs])

    print("\n=== build complete ===")
    print(f"rootfs : {rootfs}")
    if not args.skip_image:
        sz = image.stat().st_size
        print(f"image  : {image}")
        print(f"size   : {sz} bytes ({sz / (1 << 20):.1f} MiB)")
        print(f"sha256 : {sha256(image)}")
        print(f"label  : {label}")
    print("NOTE: root password LOCKED, no SSH keys installed — configure before D1 network use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
