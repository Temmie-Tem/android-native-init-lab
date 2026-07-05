#!/usr/bin/env python3
"""Run the server-distro D2 SSH-in-chroot proof.

D2 is non-destructive and SD-only:
  * reuse/stage the prebuilt Debian ext4 image under /mnt/sdext/a90/runtime,
  * loop-mount it and configure temporary key-only root SSH access,
  * start dropbear directly inside the chroot on the native-init NCM path,
  * authenticate from the host with a per-run temporary key,
  * stop dropbear, restore the rootfs files touched for the proof, unmount, detach loop,
  * confirm resident v2321 selftest still passes.

The script writes raw evidence and temporary SSH keys under workspace/private.
It never flashes and never touches userdata.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shlex
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
DEFAULT_SSH_PORT = 2222


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def generate_ssh_key(run_dir: Path, run_id: str) -> dict[str, Any]:
    key_path = run_dir / "d2_ssh_key_ed25519"
    command = [
        "ssh-keygen",
        "-q",
        "-t",
        "ed25519",
        "-N",
        "",
        "-C",
        f"a90-d2-{run_id}",
        "-f",
        str(key_path),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=False,
    )
    payload = {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "private_key_path": str(key_path.relative_to(REPO_ROOT)),
        "public_key_path": str(key_path.with_suffix(".pub").relative_to(REPO_ROOT)),
    }
    if result.returncode != 0:
        raise RuntimeError(f"ssh-keygen failed rc={result.returncode}\n{result.stderr}")
    return payload


def read_public_key(run_dir: Path) -> str:
    return (run_dir / "d2_ssh_key_ed25519.pub").read_text(encoding="utf-8").strip()


def d2_mount_script(remote_image: str, mountpoint: str, port: int) -> str:
    return f"""
set -eu
IMG={shell_quote(remote_image)}
MNT={shell_quote(mountpoint)}
LOOP=/dev/loop0
STATE=/tmp/a90_d2_loop_created
STARTED=0
cleanup_partial() {{
  set +e
  if [ "$STARTED" != "1" ]; then
    if /bin/busybox grep -q " $MNT " /proc/mounts; then
      /bin/busybox umount "$MNT" || /bin/busybox umount -l "$MNT"
    fi
    if [ -e "$LOOP" ]; then /bin/busybox losetup -d "$LOOP" >/dev/null 2>&1; fi
    if [ -f "$STATE" ] && /bin/busybox grep -q '^1$' "$STATE"; then /bin/busybox rm -f "$LOOP"; fi
    /bin/busybox rm -f "$STATE"
    /bin/busybox rmdir "$MNT" >/dev/null 2>&1
  fi
}}
trap cleanup_partial EXIT
echo A90D2_BEGIN
echo A90D2 image=$IMG
echo A90D2 mountpoint=$MNT
[ -f "$IMG" ]
if /bin/busybox netstat -ltn 2>/dev/null | /bin/busybox grep -q ":{port} "; then echo A90D2 port_busy=1; exit 31; else echo A90D2 port_busy=0; fi
LOOP_MAJOR=$(/bin/busybox grep ' loop$' /proc/devices | while read major name; do echo "$major"; done | /bin/busybox head -n 1)
echo A90D2 loop_major=$LOOP_MAJOR
[ -n "$LOOP_MAJOR" ]
/bin/busybox mkdir -p "$MNT"
if [ ! -e "$LOOP" ]; then
  /bin/busybox mknod "$LOOP" b "$LOOP_MAJOR" 0
  echo 1 > "$STATE"
else
  echo 0 > "$STATE"
fi
echo A90D2 loop_node_created=$(/bin/busybox cat "$STATE")
/bin/busybox losetup "$LOOP" "$IMG"
/bin/busybox mount -t ext4 -o rw "$LOOP" "$MNT"
echo A90D2 mounted=1
echo A90D2_MOUNT_READY
STARTED=1
trap - EXIT
""".strip()


def d2_start_dropbear_script(mountpoint: str, public_key: str, bind_ip: str, port: int) -> str:
    pubkey_q = shell_quote(public_key)
    bind_q = shell_quote(f"{bind_ip}:{port}")
    return f"""
set -eu
MNT={shell_quote(mountpoint)}
PORT_BIND={bind_q}
echo A90D2_START_BEGIN
echo A90D2 port=$PORT_BIND
/bin/busybox grep -q " $MNT " /proc/mounts
/bin/busybox mkdir -p "$MNT/root/.ssh" "$MNT/tmp"
/bin/busybox chown 0:0 "$MNT/root" "$MNT/root/.ssh"
/bin/busybox chmod 700 "$MNT/root"
/bin/busybox chmod 700 "$MNT/root/.ssh"
/bin/busybox printf '%s\\n' {pubkey_q} > "$MNT/root/.ssh/authorized_keys"
/bin/busybox chown 0:0 "$MNT/root/.ssh/authorized_keys"
/bin/busybox chmod 600 "$MNT/root/.ssh/authorized_keys"
/bin/busybox cp "$MNT/etc/shadow" "$MNT/tmp/a90_d2_shadow.bak"
/bin/busybox sed 's/^root:![^:]*:/root:*:/' "$MNT/etc/shadow" > "$MNT/tmp/a90_d2_shadow.new"
/bin/busybox cp "$MNT/tmp/a90_d2_shadow.new" "$MNT/etc/shadow"
/bin/busybox chmod 600 "$MNT/etc/shadow"
echo A90D2 authorized_keys=1
echo A90D2 shadow_temp_key_only=1
if /bin/busybox chroot "$MNT" /usr/bin/dropbearkey -t ed25519 -f /tmp/a90_d2_dropbear_hostkey >/tmp/a90_d2_dropbearkey.log 2>&1; then
  echo A90D2 hostkey_type=ed25519
else
  /bin/busybox chroot "$MNT" /usr/bin/dropbearkey -t rsa -s 2048 -f /tmp/a90_d2_dropbear_hostkey >/tmp/a90_d2_dropbearkey.log 2>&1
  echo A90D2 hostkey_type=rsa
fi
    /bin/busybox chroot "$MNT" /usr/sbin/dropbear -E -F -r /tmp/a90_d2_dropbear_hostkey -p "$PORT_BIND" -P /tmp/a90_d2_dropbear.pid -s -j -k >"$MNT/tmp/a90_d2_dropbear.log" 2>&1 &
    PID=$!
    /bin/busybox printf '%s\\n' "$PID" > "$MNT/tmp/a90_d2_dropbear.pid"
    /bin/busybox sleep 1
    if ! /bin/busybox kill -0 "$PID" >/dev/null 2>&1; then
      echo A90D2 dropbear_alive=0
      /bin/busybox cat "$MNT/tmp/a90_d2_dropbear.log" 2>/dev/null || true
      exit 34
    fi
echo A90D2 dropbear_foreground=1
echo A90D2 dropbear_pid=$PID
echo A90D2_DROPBEAR_STARTED
""".strip()


def d2_setup_script(remote_image: str, mountpoint: str, public_key: str, bind_ip: str, port: int) -> str:
    return d2_mount_script(remote_image, mountpoint, port) + "\n" + d2_start_dropbear_script(
        mountpoint,
        public_key,
        bind_ip,
        port,
    )


def d2_cleanup_script(mountpoint: str) -> str:
    return f"""
set +e
MNT={shell_quote(mountpoint)}
LOOP=/dev/loop0
STATE=/tmp/a90_d2_loop_created
echo A90D2_CLEANUP_BEGIN
if [ -f "$MNT/tmp/a90_d2_dropbear.pid" ]; then
  PID=$(/bin/busybox cat "$MNT/tmp/a90_d2_dropbear.pid")
  echo A90D2 cleanup_pid=$PID
  /bin/busybox kill "$PID" >/dev/null 2>&1
else
  echo A90D2 cleanup_pid=missing
fi
/bin/busybox killall dropbear >/dev/null 2>&1 || true
for i in 1 2 3 4 5; do
  if ! /bin/busybox pidof dropbear >/dev/null 2>&1; then break; fi
  /bin/busybox killall dropbear >/dev/null 2>&1 || true
  /bin/busybox sleep 1
done
if [ -f "$MNT/tmp/a90_d2_shadow.bak" ]; then
  /bin/busybox cp "$MNT/tmp/a90_d2_shadow.bak" "$MNT/etc/shadow"
  /bin/busybox chmod 600 "$MNT/etc/shadow"
  echo A90D2 shadow_restored=1
else
  echo A90D2 shadow_restored=0
fi
/bin/busybox rm -f "$MNT/root/.ssh/authorized_keys" "$MNT/tmp/a90_d2_dropbear_hostkey" "$MNT/tmp/a90_d2_dropbear.pid" "$MNT/tmp/a90_d2_shadow.bak" "$MNT/tmp/a90_d2_shadow.new"
if /bin/busybox grep -q " $MNT " /proc/mounts; then
  /bin/busybox umount "$MNT" || /bin/busybox umount -l "$MNT"
fi
if [ -e "$LOOP" ]; then /bin/busybox losetup -d "$LOOP" >/dev/null 2>&1; fi
if [ -f "$STATE" ] && /bin/busybox grep -q '^1$' "$STATE"; then /bin/busybox rm -f "$LOOP"; fi
/bin/busybox rm -f "$STATE"
/bin/busybox rmdir "$MNT" >/dev/null 2>&1
if /bin/busybox grep -q " $MNT " /proc/mounts; then echo A90D2 cleanup_mount_absent=0; exit 41; else echo A90D2 cleanup_mount_absent=1; fi
if [ -e "$LOOP" ]; then echo A90D2 cleanup_loop_node_absent=0; exit 42; else echo A90D2 cleanup_loop_node_absent=1; fi
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90D2 cleanup_dropbear_absent=0; else echo A90D2 cleanup_dropbear_absent=1; fi
echo A90D2_CLEANUP_DONE
""".strip()


def d2_postcheck_script(mountpoint: str) -> str:
    return f"""
set -eu
MNT={shell_quote(mountpoint)}
LOOP=/dev/loop0
/bin/busybox sleep 2
echo A90D2_POSTCHECK_BEGIN
if /bin/busybox grep -q " $MNT " /proc/mounts; then echo A90D2 post_mount_absent=0; exit 51; else echo A90D2 post_mount_absent=1; fi
if [ -e "$LOOP" ]; then echo A90D2 post_loop_node_absent=0; exit 52; else echo A90D2 post_loop_node_absent=1; fi
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90D2 post_dropbear_absent=0; exit 53; else echo A90D2 post_dropbear_absent=1; fi
echo A90D2_POSTCHECK_DONE
""".strip()


def parse_setup(text: str) -> dict[str, Any]:
    return {
        "started": "A90D2_DROPBEAR_STARTED" in text,
        "mount_ready": "A90D2_MOUNT_READY" in text,
        "mounted": "A90D2 mounted=1" in text,
        "authorized_keys": "A90D2 authorized_keys=1" in text,
        "shadow_temp_key_only": "A90D2 shadow_temp_key_only=1" in text,
        "port_busy": "A90D2 port_busy=1" in text,
        "loop_major": (re.search(r"A90D2 loop_major=([0-9]+)", text) or [None, None])[1],
        "loop_node_created": "A90D2 loop_node_created=1" in text,
        "hostkey_type": (re.search(r"A90D2 hostkey_type=([A-Za-z0-9_-]+)", text) or [None, None])[1],
        "dropbear_pid": (re.search(r"A90D2 dropbear_pid=([0-9]+)", text) or [None, None])[1],
    }


def parse_ssh_marker(text: str) -> dict[str, Any]:
    return {
        "marker": "A90D2_SSH_MARKER" in text,
        "debian_version": (re.search(r"debian_version=([^\s\r\n]+)", text) or [None, None])[1],
        "stage_marker_present": "stage_marker=present" in text,
    }


def parse_cleanup(text: str) -> dict[str, Any]:
    return {
        "done": "A90D2_CLEANUP_DONE" in text,
        "shadow_restored": "A90D2 shadow_restored=1" in text,
        "mount_cleanup_ok": "A90D2 cleanup_mount_absent=1" in text,
        "loop_cleanup_ok": "A90D2 cleanup_loop_node_absent=1" in text,
        "dropbear_cleanup_ok": "A90D2 cleanup_dropbear_absent=1" in text,
    }


def parse_postcheck(text: str) -> dict[str, Any]:
    return {
        "done": "A90D2_POSTCHECK_DONE" in text,
        "mount_absent": "A90D2 post_mount_absent=1" in text,
        "loop_node_absent": "A90D2 post_loop_node_absent=1" in text,
        "dropbear_absent": "A90D2 post_dropbear_absent=1" in text,
    }


def run_host_ssh(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    key_path = run_dir / "d2_ssh_key_ed25519"
    known_hosts = run_dir / "d2_known_hosts"
    remote_command = (
        "echo A90D2_SSH_MARKER; "
        "echo debian_version=$(cat /etc/debian_version); "
        "test -f /etc/a90-server-distro-stage && echo stage_marker=present; "
        "uname -a"
    )
    command = [
        "ssh",
        "-i",
        str(key_path),
        "-p",
        str(args.ssh_port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        f"ConnectTimeout={args.ssh_connect_timeout}",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "WarnWeakCrypto=no",
        f"root@{args.device_ip}",
        remote_command,
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=args.ssh_timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "marker": parse_ssh_marker(result.stdout),
        "known_hosts_path": str(known_hosts.relative_to(REPO_ROOT)),
    }


def collect(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    now_utc = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    run_id = args.run_id or "d2-ssh-in-chroot-" + now_utc.strftime("%Y%m%dT%H%M%SZ")
    run_dir = d1.normalize_run_dir(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    local_sha = d1.sha256_file(args.local_image)
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        raise RuntimeError(f"unexpected local image SHA256: {local_sha}")

    keygen_record = generate_ssh_key(run_dir, run_id)
    public_key = read_public_key(run_dir)

    baseline = {
        "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"]),
        "status": d1.run_cmd(args.host, args.port, args.timeout, ["status"]),
        "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    if "v2321-usb-clean-identity-rodata" not in baseline["version"]["text"]:
        raise RuntimeError("resident device is not v2321; refusing D2")
    if "fail=0" not in baseline["selftest"]["text"]:
        raise RuntimeError("baseline selftest is not fail=0; refusing D2")

    before_sha, before_record = d1.remote_image_sha(args.host, args.port, args.sha_timeout, args.remote_image)
    install_record: dict[str, Any] | None = None
    if before_sha != local_sha:
        install_record = d1.install_image(args, local_sha)
    after_sha, after_record = d1.remote_image_sha(args.host, args.port, args.sha_timeout, args.remote_image)
    if after_sha != local_sha:
        raise RuntimeError(f"remote image SHA mismatch after staging: {after_sha} != {local_sha}")

    mount_record: dict[str, Any] | None = None
    start_record: dict[str, Any] | None = None
    ssh_record: dict[str, Any] | None = None
    cleanup_record: dict[str, Any] | None = None
    postcheck_record: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    postcheck: dict[str, Any] | None = None
    try:
        mount_record = d1.run_shell(
            args.host,
            args.port,
            args.setup_timeout,
            d2_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            allow_error=False,
        )
        mount = parse_setup(str(mount_record.get("text") or ""))
        if not all(mount[key] for key in ("mount_ready", "mounted")):
            raise RuntimeError(f"D2 mount markers incomplete: {mount}\n{mount_record.get('text')}")

        start_record = d1.run_shell(
            args.host,
            args.port,
            args.setup_timeout,
            d2_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            allow_error=False,
        )
        start = parse_setup(str(start_record.get("text") or ""))
        if not all(start[key] for key in ("started", "authorized_keys", "shadow_temp_key_only")):
            raise RuntimeError(f"D2 start markers incomplete: {start}\n{start_record.get('text')}")

        ssh_record = run_host_ssh(args, run_dir)
        if ssh_record["returncode"] != 0 or not ssh_record["marker"]["marker"]:
            raise RuntimeError(
                "host SSH proof failed rc="
                f"{ssh_record['returncode']}\n{ssh_record['stdout']}\n{ssh_record['stderr']}"
            )
    finally:
        cleanup_record = d1.run_shell(
            args.host,
            args.port,
            args.cleanup_timeout,
            d2_cleanup_script(args.mountpoint),
            allow_error=True,
        )
        cleanup = parse_cleanup(str(cleanup_record.get("text") or ""))

    if not cleanup or not all(cleanup[key] for key in ("done", "shadow_restored", "mount_cleanup_ok", "loop_cleanup_ok")):
        raise RuntimeError(f"D2 cleanup markers incomplete: {cleanup}\n{cleanup_record.get('text') if cleanup_record else ''}")

    postcheck_record = d1.run_shell(
        args.host,
        args.port,
        args.cleanup_timeout,
        d2_postcheck_script(args.mountpoint),
        allow_error=False,
    )
    postcheck = parse_postcheck(str(postcheck_record.get("text") or ""))
    if not all(postcheck[key] for key in ("done", "mount_absent", "loop_node_absent", "dropbear_absent")):
        raise RuntimeError(f"D2 postcheck markers incomplete: {postcheck}\n{postcheck_record.get('text')}")

    final = {
        "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"]),
        "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    if "v2321-usb-clean-identity-rodata" not in final["version"]["text"]:
        raise RuntimeError("final resident device is not v2321")
    if "fail=0" not in final["selftest"]["text"]:
        raise RuntimeError("final selftest is not fail=0")

    setup = parse_setup(
        str(mount_record.get("text") if mount_record else "")
        + "\n"
        + str(start_record.get("text") if start_record else "")
    )
    ssh_marker = ssh_record["marker"] if ssh_record else {}
    private = {
        "run_id": run_id,
        "timestamp_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "scope": "server-distro D2 SSH-in-chroot",
        "safety": {
            "non_destructive": True,
            "sd_only": True,
            "no_flash": True,
            "no_userdata_touch": True,
            "runtime_loop_node_only": True,
            "temporary_key_only": True,
        },
        "keygen": keygen_record,
        "local_image": str(args.local_image.relative_to(REPO_ROOT)),
        "local_image_sha256": local_sha,
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "ssh_port": args.ssh_port,
        "baseline": baseline,
        "remote_sha_before": before_record,
        "install": install_record,
        "remote_sha_after": after_record,
        "mount": mount_record,
        "start": start_record,
        "ssh": ssh_record,
        "cleanup": cleanup_record,
        "postcheck": postcheck_record,
        "final": final,
    }
    summary = {
        "decision": "server-distro-d2-ssh-in-chroot-pass",
        "ok": True,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "remote_image": args.remote_image,
        "remote_sha256": after_sha,
        "image_staged_this_run": install_record is not None,
        "mountpoint": args.mountpoint,
        "ssh_port": args.ssh_port,
        "dropbear_started": setup.get("started"),
        "dropbear_pid_observed": bool(setup.get("dropbear_pid")),
        "hostkey_type": setup.get("hostkey_type"),
        "ssh_marker_returned": ssh_marker.get("marker"),
        "debian_version": ssh_marker.get("debian_version"),
        "stage_marker_present": ssh_marker.get("stage_marker_present"),
        "cleanup_mount_absent": cleanup.get("mount_cleanup_ok") if cleanup else False,
        "cleanup_loop_node_absent": cleanup.get("loop_cleanup_ok") if cleanup else False,
        "cleanup_dropbear_absent": postcheck.get("dropbear_absent") if postcheck else False,
        "postcheck_mount_absent": postcheck.get("mount_absent") if postcheck else False,
        "postcheck_loop_node_absent": postcheck.get("loop_node_absent") if postcheck else False,
        "postcheck_dropbear_absent": postcheck.get("dropbear_absent") if postcheck else False,
        "shadow_restored": cleanup.get("shadow_restored") if cleanup else False,
        "final_v2321": True,
        "final_selftest_fail0": True,
        "userdata_touched": False,
        "flash_performed": False,
        "next": "D3 switch_root PID1 handoff",
    }
    write_json(run_dir / "d2_private.json", private)
    write_json(run_dir / "d2_summary.json", summary)
    return private, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=120.0)
    parser.add_argument("--cleanup-timeout", type=float, default=60.0)
    parser.add_argument("--ssh-timeout", type=float, default=30.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    args = parser.parse_args(argv)
    _private, summary = collect(args)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
