#!/usr/bin/env python3
"""Run the server-distro D1 chroot MVP on the resident native-init device.

D1 is non-destructive and SD-only:
  * stage the prebuilt Debian ext4 image under /mnt/sdext/a90/runtime,
  * materialize a runtime /dev/loop0 node if needed,
  * losetup + mount the image,
  * chroot and run known Debian binaries,
  * unmount/detach/remove the runtime loop node,
  * confirm resident v2321 selftest still passes.

The script writes raw evidence under workspace/private and prints a redacted
summary.  It never flashes and never touches userdata.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

import a90ctl  # noqa: E402


DEFAULT_RUN_BASE = REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
DEFAULT_LOCAL_IMAGE = (
    REPO_ROOT / "workspace" / "private" / "builds" / "server-distro"
    / "debian-bookworm-arm64-20260701-024412.img"
)
DEFAULT_REMOTE_IMAGE = "/mnt/sdext/a90/runtime/debian-bookworm-arm64-20260701-024412.img"
DEFAULT_MOUNTPOINT = "/mnt/sdext/a90/runtime/distro-root"
EXPECTED_IMAGE_SHA256 = "210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc"


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
        json.dump(payload, fp, indent=2, sort_keys=True, ensure_ascii=False)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)


def normalize_run_dir(run_dir: Path) -> Path:
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    return run_dir.resolve()


def run_cmd(host: str,
            port: int,
            timeout: float,
            command: list[str],
            *,
            retry_unsafe: bool = False,
            allow_error: bool = False) -> dict[str, Any]:
    result = a90ctl.run_cmdv1_command(
        host,
        port,
        timeout,
        command,
        retry_unsafe=retry_unsafe,
        require_prompt_after_end=True,
    )
    payload = {
        "command": command,
        "rc": result.rc,
        "status": result.status,
        "begin": result.begin,
        "end": result.end,
        "text": result.text,
    }
    if not allow_error and result.rc != 0:
        raise RuntimeError(f"device command failed rc={result.rc}: {command}\n{result.text}")
    return payload


def run_shell(host: str,
              port: int,
              timeout: float,
              script: str,
              *,
              allow_error: bool = False) -> dict[str, Any]:
    return run_cmd(
        host,
        port,
        timeout,
        ["run", "/bin/busybox", "sh", "-c", script],
        retry_unsafe=True,
        allow_error=allow_error,
    )


def parse_sha256(text: str) -> str | None:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
    return match.group(1).lower() if match else None


def remote_image_sha(host: str, port: int, timeout: float, remote_image: str) -> tuple[str | None, dict[str, Any]]:
    script = f"if [ -f {remote_image} ]; then /bin/busybox sha256sum {remote_image}; else echo missing; fi"
    record = run_shell(host, port, timeout, script, allow_error=True)
    return parse_sha256(str(record.get("text") or "")), record


def install_image(args: argparse.Namespace, local_sha: str) -> dict[str, Any]:
    tcpctl_host = REVAL_DIR / "tcpctl_host.py"
    command = [
        sys.executable,
        str(tcpctl_host),
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--device-ip",
        args.device_ip,
        "--bridge-timeout",
        str(args.bridge_timeout),
        "--connect-timeout",
        str(args.connect_timeout),
        "--tcp-timeout",
        str(args.tcp_timeout),
        "--toybox",
        args.toybox,
        "--device-binary",
        args.remote_image,
        "install",
        "--local-binary",
        str(args.local_image),
        "--transfer-timeout",
        str(args.transfer_timeout),
        "--transfer-delay",
        str(args.transfer_delay),
        "--install-control-channel",
        "bridge",
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", "/tmp/a90_pycache")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=args.transfer_timeout + args.bridge_timeout + 120.0,
        env=env,
        check=False,
    )
    payload = {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "expected_sha256": local_sha,
    }
    if result.returncode != 0:
        raise RuntimeError(f"image install failed rc={result.returncode}\n{result.stdout}\n{result.stderr}")
    return payload


def d1_proof_script(remote_image: str, mountpoint: str) -> str:
    return f"""
set -eu
IMG={remote_image}
MNT={mountpoint}
LOOP=/dev/loop0
CREATED_LOOP=0
cleanup() {{
  set +e
  if /bin/busybox grep -q " $MNT " /proc/mounts; then
    /bin/busybox umount "$MNT" || /bin/busybox umount -l "$MNT"
  fi
  if [ -e "$LOOP" ]; then /bin/busybox losetup -d "$LOOP" >/dev/null 2>&1; fi
  /bin/busybox rmdir "$MNT" >/dev/null 2>&1
  if [ "$CREATED_LOOP" = "1" ]; then /bin/busybox rm -f "$LOOP"; fi
}}
trap cleanup EXIT
echo A90D1_BEGIN
echo A90D1 image=$IMG
echo A90D1 mountpoint=$MNT
[ -f "$IMG" ]
LOOP_MAJOR=$(/bin/busybox grep ' loop$' /proc/devices | while read major name; do echo "$major"; done | /bin/busybox head -n 1)
echo A90D1 loop_major=$LOOP_MAJOR
[ -n "$LOOP_MAJOR" ]
/bin/busybox mkdir -p "$MNT"
if [ ! -e "$LOOP" ]; then
  /bin/busybox mknod "$LOOP" b "$LOOP_MAJOR" 0
  CREATED_LOOP=1
fi
echo A90D1 loop_node_created=$CREATED_LOOP
/bin/busybox losetup "$LOOP" "$IMG"
/bin/busybox mount -t ext4 -o rw "$LOOP" "$MNT"
echo A90D1 mounted=1
/bin/busybox chroot "$MNT" /bin/sh -c 'echo A90D1_CHROOT_BEGIN; echo debian_version=$(cat /etc/debian_version); echo kernel=$(uname -a); test -f /etc/a90-server-distro-stage && echo stage_marker=present; /bin/ls /bin/sh /etc/debian_version >/dev/null; echo A90D1_CHROOT_DONE'
cleanup
trap - EXIT
if /bin/busybox grep -q " $MNT " /proc/mounts; then echo A90D1 cleanup_mount_absent=0; exit 21; else echo A90D1 cleanup_mount_absent=1; fi
if [ -e "$LOOP" ]; then echo A90D1 cleanup_loop_node_absent=0; exit 22; else echo A90D1 cleanup_loop_node_absent=1; fi
echo A90D1_DONE
""".strip()


def parse_proof(text: str) -> dict[str, Any]:
    return {
        "chroot_begin": "A90D1_CHROOT_BEGIN" in text,
        "chroot_done": "A90D1_CHROOT_DONE" in text,
        "done": "A90D1_DONE" in text,
        "mount_cleanup_ok": "A90D1 cleanup_mount_absent=1" in text,
        "loop_cleanup_ok": "A90D1 cleanup_loop_node_absent=1" in text,
        "stage_marker_present": "stage_marker=present" in text,
        "debian_version": (re.search(r"debian_version=([^\s\r\n]+)", text) or [None, None])[1],
        "loop_major": (re.search(r"A90D1 loop_major=([0-9]+)", text) or [None, None])[1],
        "loop_node_created": "A90D1 loop_node_created=1" in text,
    }


def collect(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    now_utc = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    run_id = args.run_id or "d1-chroot-mvp-" + now_utc.strftime("%Y%m%dT%H%M%SZ")
    run_dir = normalize_run_dir(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    if not args.local_image.is_file():
        raise FileNotFoundError(args.local_image)
    local_sha = sha256_file(args.local_image)
    if local_sha != EXPECTED_IMAGE_SHA256:
        raise RuntimeError(f"unexpected local image SHA256: {local_sha}")

    baseline = {
        "version": run_cmd(args.host, args.port, args.timeout, ["version"]),
        "status": run_cmd(args.host, args.port, args.timeout, ["status"]),
        "selftest": run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    if "v2321-usb-clean-identity-rodata" not in baseline["version"]["text"]:
        raise RuntimeError("resident device is not v2321; refusing D1")
    if "fail=0" not in baseline["selftest"]["text"]:
        raise RuntimeError("baseline selftest is not fail=0; refusing D1")

    before_sha, before_record = remote_image_sha(args.host, args.port, args.sha_timeout, args.remote_image)
    install_record: dict[str, Any] | None = None
    if before_sha != local_sha:
        install_record = install_image(args, local_sha)
    after_sha, after_record = remote_image_sha(args.host, args.port, args.sha_timeout, args.remote_image)
    if after_sha != local_sha:
        raise RuntimeError(f"remote image SHA mismatch after staging: {after_sha} != {local_sha}")

    proof_record = run_shell(
        args.host,
        args.port,
        args.proof_timeout,
        d1_proof_script(args.remote_image, args.mountpoint),
        allow_error=False,
    )
    proof = parse_proof(str(proof_record.get("text") or ""))
    if not all(proof[key] for key in ("chroot_begin", "chroot_done", "done", "mount_cleanup_ok", "loop_cleanup_ok")):
        raise RuntimeError(f"D1 proof markers incomplete: {proof}\n{proof_record.get('text')}")

    final = {
        "version": run_cmd(args.host, args.port, args.timeout, ["version"]),
        "selftest": run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    if "v2321-usb-clean-identity-rodata" not in final["version"]["text"]:
        raise RuntimeError("final resident device is not v2321")
    if "fail=0" not in final["selftest"]["text"]:
        raise RuntimeError("final selftest is not fail=0")

    private = {
        "run_id": run_id,
        "timestamp_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "scope": "server-distro D1 chroot MVP",
        "safety": {
            "non_destructive": True,
            "sd_only": True,
            "no_flash": True,
            "no_userdata_touch": True,
            "runtime_loop_node_only": True,
        },
        "local_image": str(args.local_image.relative_to(REPO_ROOT)),
        "local_image_sha256": local_sha,
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "baseline": baseline,
        "remote_sha_before": before_record,
        "install": install_record,
        "remote_sha_after": after_record,
        "proof": proof_record,
        "final": final,
    }
    summary = {
        "decision": "server-distro-d1-chroot-mvp-pass",
        "ok": True,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "local_image_sha256": local_sha,
        "remote_image": args.remote_image,
        "remote_sha256": after_sha,
        "image_staged_this_run": install_record is not None,
        "mountpoint": args.mountpoint,
        "debian_version": proof.get("debian_version"),
        "loop_major": proof.get("loop_major"),
        "loop_node_created": proof.get("loop_node_created"),
        "chroot_debian_binary_executed": True,
        "stage_marker_present": proof.get("stage_marker_present"),
        "cleanup_mount_absent": proof.get("mount_cleanup_ok"),
        "cleanup_loop_node_absent": proof.get("loop_cleanup_ok"),
        "final_v2321": True,
        "final_selftest_fail0": True,
        "userdata_touched": False,
        "flash_performed": False,
        "next": "D2 dropbear SSH inside the same SD-backed chroot",
    }
    write_json(run_dir / "d1_private.json", private)
    write_json(run_dir / "d1_summary.json", summary)
    return private, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--proof-timeout", type=float, default=120.0)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--local-image", type=Path, default=DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--mountpoint", default=DEFAULT_MOUNTPOINT)
    args = parser.parse_args(argv)
    _private, summary = collect(args)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
