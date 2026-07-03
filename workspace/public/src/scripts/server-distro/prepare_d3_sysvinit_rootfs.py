#!/usr/bin/env python3
"""Prepare the D3 sysvinit rootfs/image for the server-distro switch_root proof.

This is a host-only private-artifact builder.  It does not touch the device.

It starts from the D0/D1/D2 Debian Bookworm arm64 rootfs, extracts the minimal
sysvinit packages, installs an explicit D3 firstboot/inittab contract, and builds
a new ext4 SD image.  It intentionally runs under fakeroot so the generated ext4
image preserves root ownership and device-node metadata without requiring sudo.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_BASE_ROOTFS = (
    REPO_ROOT / "workspace" / "private" / "builds" / "server-distro"
    / "debian-bookworm-arm64-rootfs"
)
DEFAULT_OUT_DIR = REPO_ROOT / "workspace" / "private" / "builds" / "server-distro"
DEFAULT_APT_WORK = DEFAULT_OUT_DIR / "d3-apt-arm64"
DEFAULT_REMOTE_IMAGE = "/mnt/sdext/a90/runtime/debian-bookworm-arm64-d3-sysvinit.img"
DEFAULT_SUITE = "bookworm"
DEFAULT_ARCH = "arm64"
DEFAULT_MIRROR = "http://deb.debian.org/debian"
DEFAULT_IMAGE_SIZE = "2G"
DEFAULT_AUTOREBOOT_SEC = 120
DEFAULT_NCM_IP = "192.168.7.2"
DEFAULT_NCM_PEER = "192.168.7.1"
SYSV_PACKAGES = ("insserv", "startpar", "initscripts", "sysv-rc", "sysvinit-core")
USR_MERGE_LINKS = (("bin", "usr/bin"), ("sbin", "usr/sbin"), ("lib", "usr/lib"))


def run(cmd: list[str], *, cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, text=True, check=True, timeout=timeout)


def output(cmd: list[str], *, cwd: Path | None = None) -> str:
    print("+ " + " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=cwd or REPO_ROOT, text=True, capture_output=True, check=True)
    return result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)


def require_tools() -> None:
    for tool in ("apt-get", "apt-cache", "dpkg-deb", "mke2fs", "fakeroot", "cp"):
        if shutil.which(tool) is None:
            raise SystemExit(f"missing required host tool: {tool}")


def reexec_under_fakeroot(argv: list[str]) -> None:
    if os.environ.get("FAKEROOTKEY"):
        return
    fakeroot = shutil.which("fakeroot")
    if fakeroot is None:
        raise SystemExit("missing required host tool: fakeroot")
    os.execvp(fakeroot, [fakeroot, "--", sys.executable, str(Path(__file__).resolve()), *argv])


def apt_common_args(args: argparse.Namespace) -> list[str]:
    apt_root = args.apt_work.resolve()
    sources = apt_root / "etc" / "apt" / "sources.list"
    trusted = args.base_rootfs.resolve() / "etc" / "apt" / "trusted.gpg.d"
    return [
        "-o", f"APT::Architecture={args.arch}",
        "-o", f"APT::Architectures={args.arch}",
        "-o", f"Dir::Etc::sourcelist={sources}",
        "-o", "Dir::Etc::sourceparts=-",
        "-o", f"Dir::Etc::trustedparts={trusted}",
        "-o", f"Dir::State={apt_root / 'state'}",
        "-o", f"Dir::Cache={apt_root / 'cache'}",
        "-o", "Debug::NoLocking=1",
    ]


def prepare_apt_state(args: argparse.Namespace) -> None:
    apt_root = args.apt_work.resolve()
    for rel in ("etc/apt", "state/lists/partial", "cache/archives/partial", "downloads"):
        (apt_root / rel).mkdir(parents=True, exist_ok=True)
    (apt_root / "etc" / "apt" / "sources.list").write_text(
        f"deb [arch={args.arch}] {args.mirror} {args.suite} main\n",
        encoding="utf-8",
    )
    run(["apt-get", *apt_common_args(args), "update"], timeout=60.0)


def package_version(args: argparse.Namespace, package: str) -> str:
    text = output(["apt-cache", *apt_common_args(args), "show", package])
    for line in text.splitlines():
        if line.startswith("Version: "):
            return line.split(": ", 1)[1].strip()
    raise RuntimeError(f"no Version field for {package}")


def download_packages(args: argparse.Namespace) -> list[Path]:
    prepare_apt_state(args)
    download_dir = args.apt_work.resolve() / "downloads"
    for old in download_dir.glob("*.deb"):
        old.unlink()
    run(["apt-get", *apt_common_args(args), "download", *SYSV_PACKAGES], cwd=download_dir, timeout=120.0)
    packages = sorted(download_dir.glob("*.deb"))
    missing = [name for name in SYSV_PACKAGES if not any(p.name.startswith(name + "_") for p in packages)]
    if missing:
        raise RuntimeError(f"missing downloaded packages: {missing}")
    return packages


def copy_base_rootfs(base_rootfs: Path, d3_rootfs: Path) -> None:
    if d3_rootfs.exists():
        shutil.rmtree(d3_rootfs)
    d3_rootfs.parent.mkdir(parents=True, exist_ok=True)
    run(["cp", "-a", str(base_rootfs), str(d3_rootfs)])


def extract_packages(d3_rootfs: Path, packages: list[Path]) -> None:
    for pkg in packages:
        run(["dpkg-deb", "-x", str(pkg), str(d3_rootfs)])


def merge_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir(), key=lambda p: p.name):
        target = dst / item.name
        if target.exists() or target.is_symlink():
            if item.is_dir() and not item.is_symlink() and target.is_dir() and not target.is_symlink():
                merge_tree_contents(item, target)
                item.rmdir()
                continue
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))


def restore_usrmerge_links(rootfs: Path) -> None:
    for link_name, target_name in USR_MERGE_LINKS:
        link = rootfs / link_name
        target = rootfs / target_name
        if link.is_symlink():
            if os.readlink(link) != target_name:
                link.unlink()
                link.symlink_to(target_name)
            continue
        if link.exists():
            if not link.is_dir():
                link.unlink()
            else:
                merge_tree_contents(link, target)
                link.rmdir()
        target.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target_name)


def firstboot_script(ncm_ip: str, ncm_peer: str, autoreboot_sec: int, ssh_port: int) -> str:
    return f"""#!/bin/sh
set +e
PATH=/usr/sbin:/usr/bin:/sbin:/bin

mkdir -p /run /tmp /root/.ssh /etc/dropbear
chmod 700 /root/.ssh 2>/dev/null || true
IP=/usr/bin/ip
[ -x "$IP" ] || IP=/bin/ip

(
  sleep {autoreboot_sec}
  sync
  /sbin/reboot -f || echo b > /proc/sysrq-trigger
) &
echo $! > /run/a90-d3-autoreboot.pid

$IP link set ncm0 up >/dev/null 2>&1 || true
$IP addr replace {ncm_ip}/24 dev ncm0 >/dev/null 2>&1 || true
$IP route replace {ncm_peer} dev ncm0 >/dev/null 2>&1 || true

{{
  echo A90D3_MARKER
  echo stage=D3-sysvinit-switch-root
  echo debian_version=$(cat /etc/debian_version 2>/dev/null)
  echo pid1_comm=$(cat /proc/1/comm 2>/dev/null)
  echo proc1_exe=$(readlink /proc/1/exe 2>/dev/null)
  echo ncm_ip={ncm_ip}
  echo autoreboot_sec={autoreboot_sec}
  test -f /etc/a90-server-distro-stage && cat /etc/a90-server-distro-stage
}} > /run/a90-d3-marker

if [ ! -s /etc/dropbear/dropbear_ed25519_host_key ]; then
  /usr/bin/dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key >/run/a90-d3-dropbearkey.log 2>&1
fi

if [ -s /root/.ssh/authorized_keys ]; then
  /usr/sbin/dropbear -E -r /etc/dropbear/dropbear_ed25519_host_key \\
    -p {ncm_ip}:{ssh_port} -P /run/a90-d3-dropbear.pid -s -j -k \\
    >>/run/a90-d3-dropbear.log 2>&1
  echo dropbear_started=1 >> /run/a90-d3-marker
else
  echo dropbear_started=0 >> /run/a90-d3-marker
fi

exit 0
"""


def install_d3_contract(args: argparse.Namespace, d3_rootfs: Path) -> None:
    (d3_rootfs / "etc").mkdir(parents=True, exist_ok=True)
    (d3_rootfs / "run").mkdir(parents=True, exist_ok=True)
    (d3_rootfs / "root" / ".ssh").mkdir(parents=True, exist_ok=True)
    (d3_rootfs / "etc" / "dropbear").mkdir(parents=True, exist_ok=True)
    (d3_rootfs / "etc" / "inittab").write_text(
        "\n".join([
            "# A90 D3 minimal sysvinit inittab.",
            "id:2:initdefault:",
            "si::sysinit:/etc/a90-d3-firstboot",
            "ca:12345:ctrlaltdel:/sbin/reboot -f",
            "",
        ]),
        encoding="utf-8",
    )
    (d3_rootfs / "etc" / "inittab").chmod(0o644)
    firstboot = d3_rootfs / "etc" / "a90-d3-firstboot"
    firstboot.write_text(
        firstboot_script(args.ncm_ip, args.ncm_peer, args.autoreboot_sec, args.ssh_port),
        encoding="utf-8",
    )
    firstboot.chmod(0o755)
    (d3_rootfs / "root" / ".ssh").chmod(0o700)
    stage = d3_rootfs / "etc" / "a90-server-distro-stage"
    stage.write_text(
        "\n".join([
            "stage=D3 sysvinit switch_root prepared",
            "init=sysvinit-core",
            "ssh=dropbear early by inittab sysinit, key-only, NO keys installed in artifact",
            f"ncm_ip={args.ncm_ip}",
            f"autoreboot_sec={args.autoreboot_sec}",
            "userdata=untouched",
            "",
        ]),
        encoding="utf-8",
    )


def build_image(d3_rootfs: Path, image: Path, image_size: str) -> None:
    if image.exists():
        image.unlink()
    run(["mke2fs", "-q", "-t", "ext4", "-L", "A90D3ROOT", "-d", str(d3_rootfs), str(image), image_size])


def collect_stat(rootfs: Path) -> dict[str, Any]:
    checks = {
        "sbin_init": rootfs / "sbin" / "init",
        "etc_inittab": rootfs / "etc" / "inittab",
        "firstboot": rootfs / "etc" / "a90-d3-firstboot",
        "dropbear": rootfs / "usr" / "sbin" / "dropbear",
        "dropbearkey": rootfs / "usr" / "bin" / "dropbearkey",
        "ip": rootfs / "bin" / "ip",
        "usr_bin_ip": rootfs / "usr" / "bin" / "ip",
        "stage_marker": rootfs / "etc" / "a90-server-distro-stage",
    }
    stats = {name: {"exists": path.exists(), "mode": oct(path.stat().st_mode & 0o777) if path.exists() else None}
             for name, path in checks.items()}
    stats["usrmerge_links"] = {
        link: {
            "is_symlink": (rootfs / link).is_symlink(),
            "target": os.readlink(rootfs / link) if (rootfs / link).is_symlink() else None,
        }
        for link, _target in USR_MERGE_LINKS
    }
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-rootfs", type=Path, default=DEFAULT_BASE_ROOTFS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--apt-work", type=Path, default=DEFAULT_APT_WORK)
    parser.add_argument("--suite", default=DEFAULT_SUITE)
    parser.add_argument("--arch", default=DEFAULT_ARCH)
    parser.add_argument("--mirror", default=DEFAULT_MIRROR)
    parser.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE)
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--ncm-ip", default=DEFAULT_NCM_IP)
    parser.add_argument("--ncm-peer", default=DEFAULT_NCM_PEER)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--autoreboot-sec", type=int, default=DEFAULT_AUTOREBOOT_SEC)
    parser.add_argument("--run-id")
    parser.add_argument("--no-fakeroot-reexec", action="store_true")
    args = parser.parse_args(argv)

    require_tools()
    if not args.no_fakeroot_reexec:
        reexec_under_fakeroot(sys.argv[1:] if argv is None else argv)

    now = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    run_id = args.run_id or "d3-sysvinit-" + now.strftime("%Y%m%dT%H%M%SZ")
    d3_rootfs = args.out_dir / f"{run_id}-rootfs"
    image = args.out_dir / f"{run_id}.img"
    summary_path = args.out_dir / f"{run_id}-summary.json"

    packages = download_packages(args)
    package_meta = []
    for pkg in packages:
        name = pkg.name.split("_", 1)[0]
        package_meta.append({
            "name": name,
            "version": package_version(args, name),
            "path": str(pkg.relative_to(REPO_ROOT)),
            "sha256": sha256_file(pkg),
            "size": pkg.stat().st_size,
        })

    copy_base_rootfs(args.base_rootfs, d3_rootfs)
    extract_packages(d3_rootfs, packages)
    restore_usrmerge_links(d3_rootfs)
    install_d3_contract(args, d3_rootfs)
    build_image(d3_rootfs, image, args.image_size)

    summary = {
        "decision": "server-distro-d3a-sysvinit-rootfs-host-pass",
        "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "base_rootfs": str(args.base_rootfs.relative_to(REPO_ROOT)),
        "d3_rootfs": str(d3_rootfs.relative_to(REPO_ROOT)),
        "image": str(image.relative_to(REPO_ROOT)),
        "image_size": image.stat().st_size,
        "image_sha256": sha256_file(image),
        "remote_image": args.remote_image,
        "label": "A90D3ROOT",
        "packages": package_meta,
        "ncm_ip": args.ncm_ip,
        "ssh_port": args.ssh_port,
        "autoreboot_sec": args.autoreboot_sec,
        "checks": collect_stat(d3_rootfs),
        "safety": {
            "host_only": True,
            "no_device_action": True,
            "no_flash": True,
            "no_userdata_touch": True,
            "no_credentials_in_artifact": True,
            "mandatory_auto_reboot": True,
        },
        "next": "stage this private image to SD and run the checked D3 switch_root handoff",
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
