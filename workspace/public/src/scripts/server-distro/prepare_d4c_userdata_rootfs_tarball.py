#!/usr/bin/env python3
"""Prepare and stage the D4C userdata appliance rootfs tarball.

This is non-destructive D4C entry prep.  It creates a SHA-pinned tarball from the
clean D3 sysvinit rootfs source, uploads it to the native-init SD runtime path, and
verifies the remote SHA.  It does not flash, format, mount userdata, or run any D4
mutating command.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90ctl  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402


DEFAULT_RUN_BASE = REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
DEFAULT_ROOTFS = (
    REPO_ROOT
    / "workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-rootfs"
)
DEFAULT_REMOTE_TARBALL = "/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar"
EXPECTED_STAGE_FILE = "etc/a90-server-distro-stage"
EXPECTED_DEBIAN_VERSION = "12.14"
EXPECTED_WIFI_STA_HELPER = "usr/local/bin/a90-dpublic-wifi-sta"
EXPECTED_WIFI_STA_CONFIG_DIR = "etc/a90-dpublic"


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_host(command: list[object], *, timeout: float, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    payload = {
        "command": [str(item) for item in command],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode != 0:
        raise RuntimeError(
            "host command failed rc="
            f"{result.returncode}: {' '.join(str(item) for item in command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return payload


def verify_rootfs(rootfs: Path) -> dict[str, Any]:
    if not rootfs.is_dir():
        raise FileNotFoundError(rootfs)
    required = {
        "init": rootfs / "sbin/init",
        "debian_version": rootfs / "etc/debian_version",
        "stage": rootfs / EXPECTED_STAGE_FILE,
        "inittab": rootfs / "etc/inittab",
        "wifi_sta_helper": rootfs / EXPECTED_WIFI_STA_HELPER,
        "wifi_sta_config_dir": rootfs / EXPECTED_WIFI_STA_CONFIG_DIR,
    }
    for path in required.values():
        if not path.exists():
            raise FileNotFoundError(path)
    if not os.access(required["init"], os.X_OK):
        raise RuntimeError(f"init is not executable: {required['init']}")
    if not os.access(required["wifi_sta_helper"], os.X_OK):
        raise RuntimeError(f"Wi-Fi STA helper is not executable: {required['wifi_sta_helper']}")
    debian_version = required["debian_version"].read_text(encoding="utf-8").strip()
    if debian_version != EXPECTED_DEBIAN_VERSION:
        raise RuntimeError(f"unexpected Debian version: {debian_version}")
    return {
        name: str(path.relative_to(REPO_ROOT))
        for name, path in required.items()
    } | {"debian_version": debian_version}


def create_tarball(rootfs: Path, tarball: Path, timeout: float) -> dict[str, Any]:
    tarball.parent.mkdir(parents=True, exist_ok=True)
    if tarball.exists():
        tarball.unlink()
    command = [
        "tar",
        "--format=gnu",
        "--sort=name",
        "--numeric-owner",
        "--owner=0",
        "--group=0",
        "--mtime=@0",
        "-cpf",
        tarball,
        "-C",
        rootfs,
        ".",
    ]
    record = run_host(command, timeout=timeout)
    sha = d1.sha256_file(tarball)
    size = tarball.stat().st_size
    return {
        "record": record,
        "tarball": str(tarball.relative_to(REPO_ROOT)),
        "sha256": sha,
        "size_bytes": size,
    }


def verify_tarball(tarball: Path, timeout: float) -> dict[str, Any]:
    record = run_host(["tar", "-tf", tarball], timeout=timeout)
    entries = set(record["stdout"].splitlines())
    required_entries = {
        "./sbin",
        "./usr/sbin/init",
        "./etc/debian_version",
        "./" + EXPECTED_STAGE_FILE,
        "./" + EXPECTED_WIFI_STA_HELPER,
        "./etc/inittab",
    }
    missing = sorted(required_entries - entries)
    if missing:
        raise RuntimeError(f"tarball missing required entries: {missing}")
    return {
        "required_entries_present": sorted(required_entries),
        "entry_count": len(entries),
    }


def remote_tarball_sha(args: argparse.Namespace) -> tuple[str | None, dict[str, Any]]:
    script = (
        f"if [ -f {args.remote_tarball} ]; then "
        f"/bin/busybox sha256sum {args.remote_tarball}; "
        "else echo missing; fi"
    )
    record = d1.run_shell(args.host, args.port, args.sha_timeout, script, allow_error=True)
    return d1.parse_sha256(str(record.get("text") or "")), record


def stage_tarball(args: argparse.Namespace, tarball_sha: str) -> dict[str, Any]:
    local_image = args.local_image
    remote_image = args.remote_image
    try:
        args.local_image = args.tarball
        args.remote_image = args.remote_tarball
        return d1.install_image(args, tarball_sha)
    finally:
        args.local_image = local_image
        args.remote_image = remote_image


def collect(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    run_id = args.run_id or "d4c-rootfs-tarball-" + utc_now().replace(":", "").replace("-", "")
    run_dir = d1.normalize_run_dir(args.run_dir or (args.run_base / run_id))
    run_dir.mkdir(parents=True, exist_ok=False)
    args.tarball = run_dir / "a90-d4c-userdata-rootfs.tar"

    steps: dict[str, Any] = {"run_id": run_id, "timestamp_utc": utc_now()}

    def save_step(name: str, payload: Any) -> None:
        steps[name] = payload
        d1.write_json(run_dir / f"{name}.json", payload)
        d1.write_json(run_dir / "summary.json", steps)

    baseline = {
        "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"]),
        "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    if "v2321-usb-clean-identity-rodata" not in baseline["version"]["text"]:
        raise RuntimeError("resident device is not v2321; refusing D4C tarball staging")
    if "fail=0" not in baseline["selftest"]["text"]:
        raise RuntimeError("baseline selftest is not fail=0; refusing D4C tarball staging")
    save_step("baseline", baseline)

    save_step("rootfs", verify_rootfs(args.rootfs))
    tarball = create_tarball(args.rootfs, args.tarball, args.tar_timeout)
    save_step("tarball", tarball)
    save_step("tarball_verify", verify_tarball(args.tarball, args.tar_timeout))

    before_sha, before_record = remote_tarball_sha(args)
    save_step("remote_sha_before", {"sha256": before_sha, "record": before_record})
    if before_sha != tarball["sha256"]:
        save_step("install", stage_tarball(args, str(tarball["sha256"])))
    after_sha, after_record = remote_tarball_sha(args)
    save_step("remote_sha_after", {"sha256": after_sha, "record": after_record})
    if after_sha != tarball["sha256"]:
        raise RuntimeError(f"remote tarball SHA mismatch after staging: {after_sha} != {tarball['sha256']}")

    final = {
        "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"]),
        "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    save_step("final", final)
    if "v2321-usb-clean-identity-rodata" not in final["version"]["text"]:
        raise RuntimeError("final resident device is not v2321")
    if "fail=0" not in final["selftest"]["text"]:
        raise RuntimeError("final selftest is not fail=0")

    result = {
        "decision": "server-distro-d4c-rootfs-tarball-staged",
        "ok": True,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "rootfs": str(args.rootfs.relative_to(REPO_ROOT)),
        "tarball": str(args.tarball.relative_to(REPO_ROOT)),
        "tarball_sha256": tarball["sha256"],
        "tarball_size_bytes": tarball["size_bytes"],
        "remote_tarball": args.remote_tarball,
        "remote_sha256": after_sha,
        "staged_this_run": before_sha != tarball["sha256"],
        "final_v2321": True,
        "final_selftest_fail0": True,
        "flash_performed": False,
        "userdata_touched": False,
        "next": "flash V3375 and run preflight plus formatter-probe only",
    }
    save_step("result", result)
    return steps, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--transfer-timeout", type=float, default=1800.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--sha-timeout", type=float, default=300.0)
    parser.add_argument("--tar-timeout", type=float, default=900.0)
    parser.add_argument("--run-base", type=Path, default=DEFAULT_RUN_BASE)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--rootfs", type=Path, default=DEFAULT_ROOTFS)
    parser.add_argument("--remote-tarball", default=DEFAULT_REMOTE_TARBALL)
    parser.add_argument("--local-image", type=Path, default=DEFAULT_ROOTFS)
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_TARBALL)
    args = parser.parse_args(argv)
    args.rootfs = args.rootfs.resolve()
    _steps, result = collect(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
