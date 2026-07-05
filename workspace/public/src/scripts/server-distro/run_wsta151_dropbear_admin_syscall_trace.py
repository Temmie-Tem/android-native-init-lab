#!/usr/bin/env python3
"""Run WSTA151: syscall trace the Dropbear admin USB service.

WSTA120 proved the bounded admin login model for ``dropbear-admin-usb``.
WSTA151 keeps that same root-boundary daemon model and captures a syscall
profile for the traced Dropbear daemon while proving:

  * the daemon is bound only to the USB/NCM admin address;
  * SSH as ``a90admin`` reaches UID/GID 3903;
  * root SSH is rejected;
  * trace artifacts are saved privately before cleanup.

No boot image is built or flashed.  No Wi-Fi association, DHCP, public tunnel,
public smoke, packet-filter mutation, userdata write, native reboot, or
switch-root is performed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta119_dropbear_admin_model as wsta119  # noqa: E402
import run_wsta120_dropbear_admin_live_gate as wsta120  # noqa: E402
import run_wsta149_dpublic_hud_intent_syscall_trace as wsta149  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta151-dropbear-admin-syscall-trace-live-pass"
RESULT_NAME = "wsta151_result.json"
REMOTE_ADMIN_TRACE_STAGE_SCRIPT = "/mnt/sdext/a90/runtime/a90_wsta151_admin_trace_stage.sh"
WSTA115_STRACE_IMAGE = wsta149.WSTA115_STRACE_IMAGE
WSTA115_STRACE_IMAGE_SHA256 = wsta149.WSTA115_STRACE_IMAGE_SHA256
REMOTE_TRACE_DIR = "/tmp/a90-wsta151-dropbear-admin-trace"
REMOTE_TRACE_RAW = REMOTE_TRACE_DIR + "/dropbear-admin.strace"
REMOTE_TRACE_RAW_SNAPSHOT = REMOTE_TRACE_DIR + "/dropbear-admin.snapshot.strace"
REMOTE_TRACE_SYSCALLS = REMOTE_TRACE_DIR + "/dropbear-admin.syscalls"
REMOTE_DROPBEAR_LOG = REMOTE_TRACE_DIR + "/dropbear-admin.log"
REMOTE_DROPBEAR_LOG_SNAPSHOT = REMOTE_TRACE_DIR + "/dropbear-admin.snapshot.log"
REMOTE_TRACE_PID = "/tmp/a90_dropbear_admin_trace.pid"
CORE_SYSCALLS = ("execve", "socket", "bind", "listen")
ACCEPT_SYSCALLS = ("accept", "accept4")


def rel(path: Path) -> str:
    return wsta2.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def finish_result(out_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def sha256_file(path: Path) -> str:
    return d1.sha256_file(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_dropbear_admin_syscall_trace_live:
        return False, "wsta151-blocked-dropbear-admin-syscall-trace-live-required"
    if not args.allow_dropbear_admin_trace_live:
        return False, "wsta151-blocked-dropbear-admin-trace-live-allow-required"
    if not args.ack_admin_key_material:
        return False, "wsta151-blocked-admin-key-material-ack-required"
    if not args.ack_root_login_negative_test:
        return False, "wsta151-blocked-root-login-negative-test-ack-required"
    if not args.ack_private_trace_artifact:
        return False, "wsta151-blocked-private-trace-artifact-ack-required"
    if not args.ack_runtime_cleanup:
        return False, "wsta151-blocked-runtime-cleanup-ack-required"
    return True, "ok"


def safety(gate_ok: bool) -> dict[str, Any]:
    return {
        "device_action": gate_ok,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "external_ping": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only" if gate_ok else False,
        "admin_key_material": "explicit-live-gated-private-run-key" if gate_ok else False,
        "root_login_negative_test": gate_ok,
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "runtime_cleanup_required": gate_ok,
        "public_url_value_logged": False,
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def admin_trace_stage_and_start_script(mountpoint: str,
                                       public_key: str,
                                       bind_ip: str,
                                       port: int) -> str:
    command = " ".join(wsta119.dropbear_command(bind_ip, port))
    return f"""
set -eu
M={d2.shell_quote(mountpoint)}
B={d2.shell_quote(f"{bind_ip}:{port}")}
PUBKEY={d2.shell_quote(public_key)}
ADMIN_USER=a90admin
ADMIN_GROUP=a90admin
ADMIN_UID=3903
ADMIN_GID=3903
ADMIN_HOME=/home/a90admin
ADMIN_KEYS=/home/a90admin/.ssh/authorized_keys
ROOT_KEYS=/root/.ssh/authorized_keys
PASSWD_LINE={d2.shell_quote(wsta119.admin_passwd_line())}
PLACEHOLDER_LINE={d2.shell_quote(wsta119.admin_placeholder_passwd_line())}
GROUP_LINE={d2.shell_quote(wsta119.admin_group_line())}
SHADOW_LINE={d2.shell_quote(wsta120.admin_shadow_line())}
HOSTKEY=/tmp/a90_dropbear_admin_hostkey
PIDFILE=/tmp/a90_dropbear_admin.pid
TRACE_PID={d2.shell_quote(REMOTE_TRACE_PID)}
TRACE_DIR={d2.shell_quote(REMOTE_TRACE_DIR)}
TRACE={d2.shell_quote(REMOTE_TRACE_RAW)}
SYSCALLS={d2.shell_quote(REMOTE_TRACE_SYSCALLS)}
LOG={d2.shell_quote(REMOTE_DROPBEAR_LOG)}
echo A90WSTA151_ADMIN_TRACE_STAGE_BEGIN
/bin/busybox grep -q " $M " /proc/mounts
replace_or_append_line() {{
  file=$1
  name=$2
  expected=$3
  placeholder=$4
  /bin/busybox touch "$file"
  if /bin/busybox grep -q "^${{name}}:" "$file"; then
    existing=$(/bin/busybox grep "^${{name}}:" "$file" | /bin/busybox head -n 1)
    if [ "$existing" = "$expected" ]; then
      return 0
    fi
    if [ "$existing" = "$placeholder" ]; then
      /bin/busybox grep -v "^${{name}}:" "$file" > "$file.wsta151"
      /bin/busybox printf '%s\\n' "$expected" >> "$file.wsta151"
      /bin/busybox mv -f "$file.wsta151" "$file"
      return 0
    fi
    echo "A90WSTA151_ACCOUNT_CONFLICT name=$name"
    exit 64
  fi
  /bin/busybox printf '%s\\n' "$expected" >> "$file"
}}
/bin/busybox mkdir -p "$M/etc" "$M$ADMIN_HOME/.ssh" "$M/root/.ssh" "$M/tmp" "$M$TRACE_DIR"
/bin/busybox touch "$M/etc/shadow"
/bin/busybox cp "$M/etc/shadow" "$M/tmp/a90_d2_shadow.bak"
replace_or_append_line "$M/etc/group" "$ADMIN_GROUP" "$GROUP_LINE" "$GROUP_LINE"
replace_or_append_line "$M/etc/passwd" "$ADMIN_USER" "$PASSWD_LINE" "$PLACEHOLDER_LINE"
replace_or_append_line "$M/etc/shadow" "$ADMIN_USER" "$SHADOW_LINE" "$SHADOW_LINE"
/bin/busybox chmod 0644 "$M/etc/passwd" "$M/etc/group"
/bin/busybox chmod 0600 "$M/etc/shadow"
/bin/busybox chown "$ADMIN_UID:$ADMIN_GID" "$M$ADMIN_HOME" "$M$ADMIN_HOME/.ssh"
/bin/busybox chmod 0700 "$M$ADMIN_HOME" "$M$ADMIN_HOME/.ssh"
/bin/busybox printf '%s\\n' "$PUBKEY" > "$M$ADMIN_KEYS"
/bin/busybox chown "$ADMIN_UID:$ADMIN_GID" "$M$ADMIN_KEYS"
/bin/busybox chmod 0600 "$M$ADMIN_KEYS"
/bin/busybox rm -f "$M$ROOT_KEYS" "$M$HOSTKEY" "$M$PIDFILE" "$M$TRACE_PID" "$M$TRACE" "$M$SYSCALLS" "$M$LOG" "$M{REMOTE_TRACE_RAW_SNAPSHOT}" "$M{REMOTE_DROPBEAR_LOG_SNAPSHOT}"
if [ -e "$M$ROOT_KEYS" ]; then echo A90WSTA151_ROOT_AUTHORIZED_KEYS_ABSENT=0; exit 65; else echo A90WSTA151_ROOT_AUTHORIZED_KEYS_ABSENT=1; fi
if /bin/busybox grep -Fqx "$PASSWD_LINE" "$M/etc/passwd"; then echo A90WSTA151_ADMIN_PASSWD_LINE=1; else echo A90WSTA151_ADMIN_PASSWD_LINE=0; exit 66; fi
if /bin/busybox grep -Fqx "$GROUP_LINE" "$M/etc/group"; then echo A90WSTA151_ADMIN_GROUP_LINE=1; else echo A90WSTA151_ADMIN_GROUP_LINE=0; exit 67; fi
if /bin/busybox grep -Fqx "$SHADOW_LINE" "$M/etc/shadow"; then echo A90WSTA151_ADMIN_SHADOW_LINE=1; else echo A90WSTA151_ADMIN_SHADOW_LINE=0; exit 68; fi
[ -s "$M$ADMIN_KEYS" ] && echo A90WSTA151_ADMIN_AUTHORIZED_KEYS=1 || {{ echo A90WSTA151_ADMIN_AUTHORIZED_KEYS=0; exit 69; }}
[ -x "$M/usr/sbin/dropbear" ] && echo A90WSTA151_DROPBEAR_PRESENT=1 || {{ echo A90WSTA151_DROPBEAR_PRESENT=0; exit 70; }}
if /bin/busybox chroot "$M" /usr/bin/test -x /usr/bin/strace; then echo A90WSTA151_STRACE_PRESENT=1; else echo A90WSTA151_STRACE_PRESENT=0; exit 71; fi
if /bin/busybox chroot "$M" /usr/bin/dropbearkey -t ed25519 -f "$HOSTKEY" >/tmp/a90_wsta151_dropbearkey.log 2>&1; then
  echo A90WSTA151_HOSTKEY_TYPE=ed25519
else
  /bin/busybox chroot "$M" /usr/bin/dropbearkey -t rsa -s 2048 -f "$HOSTKEY" >/tmp/a90_wsta151_dropbearkey.log 2>&1
  echo A90WSTA151_HOSTKEY_TYPE=rsa
fi
/bin/busybox touch "$M$TRACE" "$M$SYSCALLS" "$M$LOG"
/bin/busybox chmod 0644 "$M$TRACE" "$M$SYSCALLS" "$M$LOG"
echo A90WSTA151_DROPBEAR_COMMAND={d2.shell_quote(command)}
echo A90WSTA151_TRACE_COMMAND=/usr/bin/strace -qq -f -s 96 -o "$TRACE" {d2.shell_quote(command)}
/bin/busybox chroot "$M" /usr/bin/strace -qq -f -s 96 -o "$TRACE" /usr/sbin/dropbear -F -E -r "$HOSTKEY" -p "$B" -P "$PIDFILE" -s -w -j -k </dev/null >"$M$LOG" 2>&1 &
PID=$!
/bin/busybox printf '%s\\n' "$PID" > "$M$TRACE_PID"
/bin/busybox sleep 1
if ! /bin/busybox kill -0 "$PID" >/dev/null 2>&1; then
  echo A90WSTA151_TRACE_ALIVE=0
  /bin/busybox tail -n 12 "$M$LOG" 2>/dev/null || true
  exit 72
fi
echo A90WSTA151_TRACE_ALIVE=1
if /bin/busybox netstat -ltn 2>/dev/null | /bin/busybox grep -q ":{port} "; then echo A90WSTA151_DROPBEAR_LISTEN=1; else echo A90WSTA151_DROPBEAR_LISTEN=0; /bin/busybox tail -n 12 "$M$LOG" 2>/dev/null || true; exit 73; fi
echo A90WSTA151_ADMIN_TRACE_STAGE_DONE
""".strip()


def parse_stage(record: dict[str, Any]) -> dict[str, bool]:
    text = str(record.get("text") or "")
    return {
        "stage_begin": "A90WSTA151_ADMIN_TRACE_STAGE_BEGIN" in text,
        "stage_done": "A90WSTA151_ADMIN_TRACE_STAGE_DONE" in text,
        "root_authorized_keys_absent": "A90WSTA151_ROOT_AUTHORIZED_KEYS_ABSENT=1" in text,
        "admin_passwd_line": "A90WSTA151_ADMIN_PASSWD_LINE=1" in text,
        "admin_group_line": "A90WSTA151_ADMIN_GROUP_LINE=1" in text,
        "admin_shadow_line": "A90WSTA151_ADMIN_SHADOW_LINE=1" in text,
        "admin_authorized_keys": "A90WSTA151_ADMIN_AUTHORIZED_KEYS=1" in text,
        "dropbear_present": "A90WSTA151_DROPBEAR_PRESENT=1" in text,
        "strace_present": "A90WSTA151_STRACE_PRESENT=1" in text,
        "dropbear_key_generated": "A90WSTA151_HOSTKEY_TYPE=" in text,
        "dropbear_command_safe": " -s -w -j -k" in text,
        "trace_alive": "A90WSTA151_TRACE_ALIVE=1" in text,
        "dropbear_listen": "A90WSTA151_DROPBEAR_LISTEN=1" in text,
        "secret_values_logged": False,
    }


def syscall_names_from_stdout(stdout: str) -> list[str]:
    inside = False
    names: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == "A90WSTA151_SYSCALL_LIST_BEGIN":
            inside = True
            continue
        if line == "A90WSTA151_SYSCALL_LIST_END":
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def snapshot_trace_script(mountpoint: str) -> str:
    core = " ".join(CORE_SYSCALLS)
    accept_pattern = "|".join(ACCEPT_SYSCALLS)
    return f"""
set -eu
M={d2.shell_quote(mountpoint)}
TRACE={d2.shell_quote(REMOTE_TRACE_RAW)}
SNAP_TRACE={d2.shell_quote(REMOTE_TRACE_RAW_SNAPSHOT)}
SYSCALLS={d2.shell_quote(REMOTE_TRACE_SYSCALLS)}
LOG={d2.shell_quote(REMOTE_DROPBEAR_LOG)}
SNAP_LOG={d2.shell_quote(REMOTE_DROPBEAR_LOG_SNAPSHOT)}
echo A90WSTA151_TRACE_SNAPSHOT_BEGIN
[ -s "$M$TRACE" ] && echo A90WSTA151_TRACE_FILE_NONEMPTY=1 || {{ echo A90WSTA151_TRACE_FILE_NONEMPTY=0; exit 80; }}
/bin/busybox awk '{{ line=$0; sub(/^[0-9]+ +/, "", line); if (match(line, /^[A-Za-z0-9_]+\\(/)) {{ name=substr(line, 1, index(line, "(")-1); seen[name]=1 }} }} END {{ for (name in seen) print name }}' "$M$TRACE" | /bin/busybox sort > "$M$SYSCALLS"
[ -s "$M$SYSCALLS" ] && echo A90WSTA151_SYSCALL_PROFILE_NONEMPTY=1 || {{ echo A90WSTA151_SYSCALL_PROFILE_NONEMPTY=0; exit 81; }}
COUNT=$(/bin/busybox wc -l < "$M$SYSCALLS" | /bin/busybox awk '{{print $1}}')
echo A90WSTA151_SYSCALL_COUNT=$COUNT
for name in {core}; do
  if /bin/busybox grep -qx "$name" "$M$SYSCALLS"; then echo "A90WSTA151_SYSCALL_HAS_$name=1"; else echo "A90WSTA151_SYSCALL_HAS_$name=0"; exit 82; fi
done
if /bin/busybox grep -E -qx '{accept_pattern}' "$M$SYSCALLS"; then echo A90WSTA151_SYSCALL_HAS_ACCEPT=1; else echo A90WSTA151_SYSCALL_HAS_ACCEPT=0; exit 83; fi
if /bin/busybox grep -q 'Password auth succeeded' "$M$LOG"; then echo A90WSTA151_DROPBEAR_LOG_POLICY_CLEAN=0; exit 84; else echo A90WSTA151_DROPBEAR_LOG_POLICY_CLEAN=1; fi
/bin/busybox cp "$M$TRACE" "$M$SNAP_TRACE"
/bin/busybox cp "$M$LOG" "$M$SNAP_LOG"
[ -s "$M$SNAP_TRACE" ] && echo A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=1 || {{ echo A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=0; exit 85; }}
/bin/busybox chmod 0644 "$M$SNAP_TRACE" "$M$SYSCALLS" "$M$SNAP_LOG"
echo A90WSTA151_SYSCALL_LIST_BEGIN
/bin/busybox cat "$M$SYSCALLS"
echo A90WSTA151_SYSCALL_LIST_END
echo A90WSTA151_TRACE_SNAPSHOT_DONE
""".strip()


def parse_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text") or "")
    syscalls = syscall_names_from_stdout(text)
    syscall_set = set(syscalls)
    return {
        "snapshot_begin": "A90WSTA151_TRACE_SNAPSHOT_BEGIN" in text,
        "snapshot_done": "A90WSTA151_TRACE_SNAPSHOT_DONE" in text,
        "trace_file_nonempty": "A90WSTA151_TRACE_FILE_NONEMPTY=1" in text,
        "trace_snapshot_file_nonempty": "A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=1" in text,
        "syscall_profile_nonempty": "A90WSTA151_SYSCALL_PROFILE_NONEMPTY=1" in text,
        "core_syscalls_observed": all(name in syscall_set for name in CORE_SYSCALLS)
        or all(f"A90WSTA151_SYSCALL_HAS_{name}=1" in text for name in CORE_SYSCALLS),
        "accept_observed": any(name in syscall_set for name in ACCEPT_SYSCALLS)
        or "A90WSTA151_SYSCALL_HAS_ACCEPT=1" in text,
        "dropbear_log_policy_clean": "A90WSTA151_DROPBEAR_LOG_POLICY_CLEAN=1" in text,
        "syscall_names": syscalls,
        "syscall_count": len(syscalls),
        "secret_values_logged": 0,
    }


def fetch_remote_file_as_admin(args: argparse.Namespace,
                               run_dir: Path,
                               remote_path: str,
                               local_path: Path,
                               *,
                               timeout: float) -> dict[str, Any]:
    command = [
        *wsta120.ssh_command(args, run_dir, "a90admin"),
        f"set -eu; /usr/bin/test -f {shlex.quote(remote_path)}; /bin/cat {shlex.quote(remote_path)}",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    record = {
        "remote_path": remote_path,
        "local_path": rel(local_path),
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
        "saved": False,
        "secret_values_logged": 0,
    }
    if completed.returncode == 0:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(completed.stdout)
        record.update({
            "saved": True,
            "size_bytes": local_path.stat().st_size,
            "sha256": sha256_file(local_path),
        })
    return record


def fetch_trace_artifacts(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    raw = fetch_remote_file_as_admin(
        args,
        run_dir,
        REMOTE_TRACE_RAW_SNAPSHOT,
        run_dir / "wsta151_dropbear_admin.strace",
        timeout=args.ssh_timeout,
    )
    syscalls = fetch_remote_file_as_admin(
        args,
        run_dir,
        REMOTE_TRACE_SYSCALLS,
        run_dir / "wsta151_dropbear_admin.syscalls",
        timeout=args.ssh_timeout,
    )
    log = fetch_remote_file_as_admin(
        args,
        run_dir,
        REMOTE_DROPBEAR_LOG_SNAPSHOT,
        run_dir / "wsta151_dropbear_admin.log",
        timeout=args.ssh_timeout,
    )
    return {
        "raw_trace": raw,
        "syscall_list": syscalls,
        "dropbear_log": log,
        "all_saved": bool(raw.get("saved") and syscalls.get("saved") and log.get("saved")),
        "private_artifact": True,
        "secret_values_logged": 0,
    }


def syscall_profile(parsed: dict[str, Any],
                    admin_ok: bool,
                    root_rejected: bool,
                    bind: str,
                    trace_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta151-dropbear-admin-syscall-profile-v1",
        "service": wsta119.ADMIN_SERVICE,
        "scope": "dropbear-admin-usb-daemon",
        "daemon": "/usr/sbin/dropbear",
        "daemon_privilege_model": "root-boundary-auth-daemon",
        "bind": bind,
        "network_scope": "usb-ncm-admin-only",
        "password_login_disabled": True,
        "root_login_disabled": True,
        "forwarding_disabled": True,
        "admin_login_uid_gid_proven": bool(admin_ok),
        "root_ssh_rejected": bool(root_rejected),
        "root_authorized_keys_absent": True,
        "core_syscalls": list(CORE_SYSCALLS),
        "accept_syscalls": list(ACCEPT_SYSCALLS),
        "core_syscalls_observed": bool(parsed.get("core_syscalls_observed")),
        "accept_observed": bool(parsed.get("accept_observed")),
        "syscall_count": int(parsed.get("syscall_count") or 0),
        "syscall_names": list(parsed.get("syscall_names") or []),
        "trace_artifacts": trace_artifacts or {},
        "public_url_value_logged": False,
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def trace_cleanup_script(mountpoint: str) -> str:
    return f"""
set +e
M={d2.shell_quote(mountpoint)}
TRACE_PID={d2.shell_quote(REMOTE_TRACE_PID)}
TRACE_DIR={d2.shell_quote(REMOTE_TRACE_DIR)}
echo A90WSTA151_TRACE_CLEANUP_BEGIN
if [ -s "$M$TRACE_PID" ]; then
  PID=$(/bin/busybox cat "$M$TRACE_PID")
  /bin/busybox kill "$PID" >/dev/null 2>&1 || true
  /bin/busybox sleep 1
  /bin/busybox kill -9 "$PID" >/dev/null 2>&1 || true
fi
for i in 1 2 3 4 5; do
  for p in $(/bin/busybox pidof dropbear 2>/dev/null); do /bin/busybox kill "$p" >/dev/null 2>&1 || true; done
  /bin/busybox sleep 1
  if ! /bin/busybox pidof dropbear >/dev/null 2>&1; then break; fi
  for p in $(/bin/busybox pidof dropbear 2>/dev/null); do /bin/busybox kill -9 "$p" >/dev/null 2>&1 || true; done
  /bin/busybox sleep 1
done
/bin/busybox rm -f "$M/home/a90admin/.ssh/authorized_keys" "$M/tmp/a90_dropbear_admin_hostkey" "$M/tmp/a90_dropbear_admin.pid" "$M$TRACE_PID"
/bin/busybox rm -f {d2.shell_quote(REMOTE_ADMIN_TRACE_STAGE_SCRIPT)}
if [ -e "$M/home/a90admin/.ssh/authorized_keys" ]; then echo A90WSTA151 admin_keys_absent=0; else echo A90WSTA151 admin_keys_absent=1; fi
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90WSTA151 dropbear_absent=0; else echo A90WSTA151 dropbear_absent=1; fi
if [ -d "$M$TRACE_DIR" ]; then /bin/busybox rm -rf "$M$TRACE_DIR"; fi
if [ -d "$M$TRACE_DIR" ]; then echo A90WSTA151 trace_dir_absent=0; else echo A90WSTA151 trace_dir_absent=1; fi
echo A90WSTA151_TRACE_CLEANUP_DONE
""".strip()


def parse_trace_cleanup(record: dict[str, Any]) -> dict[str, bool]:
    text = str(record.get("text") or "")
    return {
        "cleanup_begin": "A90WSTA151_TRACE_CLEANUP_BEGIN" in text,
        "cleanup_done": "A90WSTA151_TRACE_CLEANUP_DONE" in text,
        "admin_keys_absent": "A90WSTA151 admin_keys_absent=1" in text,
        "dropbear_absent": "A90WSTA151 dropbear_absent=1" in text,
        "trace_dir_absent": "A90WSTA151 trace_dir_absent=1" in text,
    }


def trace_cleanup_ok(result: dict[str, Any]) -> bool:
    cleanup = result.get("trace_cleanup_parse", {})
    return bool(
        cleanup.get("cleanup_done")
        and cleanup.get("admin_keys_absent")
        and cleanup.get("trace_dir_absent")
    )


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta120.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta151-blocked-explicit-live-gate"),
        ("local_image_present", "wsta151-blocked-local-image-missing"),
        ("local_image_sha_ok", "wsta151-blocked-local-image-sha"),
        ("baseline_selftest_fail_zero", "wsta151-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta151-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta151-blocked-remote-image"),
        ("admin_trace_stage_script_uploaded", "wsta151-blocked-admin-trace-stage-script-upload"),
        ("chroot_mount_ready", "wsta151-blocked-chroot-mount"),
        ("admin_trace_stage_pass", "wsta151-blocked-admin-trace-stage"),
        ("admin_ssh_pass", "wsta151-blocked-admin-ssh"),
        ("root_ssh_rejected", "wsta151-blocked-root-ssh-not-rejected"),
        ("trace_snapshot_pass", "wsta151-blocked-trace-snapshot"),
        ("trace_file_nonempty", "wsta151-blocked-trace-empty"),
        ("trace_snapshot_file_nonempty", "wsta151-blocked-trace-snapshot-empty"),
        ("syscall_profile_nonempty", "wsta151-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta151-blocked-core-syscalls-missing"),
        ("syscall_accept_observed", "wsta151-blocked-accept-syscall-missing"),
        ("dropbear_log_policy_clean", "wsta151-blocked-dropbear-log-policy"),
        ("trace_artifact_saved", "wsta151-blocked-trace-artifact-save"),
        ("trace_cleanup_ok", "wsta151-blocked-trace-cleanup"),
        ("chroot_cleanup_ok", "wsta151-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta151-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta151-dropbear-admin-syscall-trace-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA151 Dropbear admin syscall trace",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "admin_model": wsta119.dropbear_admin_model(args.device_ip, args.ssh_port),
        "remote_image": args.remote_image,
        "remote_clean_image": args.remote_clean_image if wsta42.remote_clean_image_enabled(args) else None,
        "mountpoint": args.mountpoint,
        "safety": safety(gate_ok),
        "checks": {
            "explicit_live_gate": gate_ok,
            "public_url_value_logged": False,
            "admin_public_key_value_logged": False,
            "secret_values_logged": 0,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        return finish_result(out_path, result)

    local_image = args.local_image
    if not local_image.is_file():
        result["checks"]["local_image_present"] = False
        result["checks"]["local_image_sha_ok"] = False
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    local_sha = sha256_file(local_image)
    result["local_image"] = rel(local_image)
    result["local_image_sha256"] = local_sha
    result["checks"]["local_image_present"] = True
    if args.local_image_sha256:
        result["local_image_expected_sha256"] = args.local_image_sha256
        result["checks"]["local_image_sha_ok"] = local_sha == args.local_image_sha256
    else:
        result["local_image_expected_sha256"] = None
        result["checks"]["local_image_sha_ok"] = True
    if not result["checks"]["local_image_sha_ok"]:
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    mounted = False
    try:
        result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
        result["version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["status"] = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
        result["baseline_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["baseline_selftest_fail_zero"] = wsta2.selftest_passed(result["baseline_selftest"].get("text", ""))
        result["native_stale_cleanup"] = wsta94.native_stale_cleanup(args)
        result["checks"]["native_stale_cleanup_ok"] = bool(result["native_stale_cleanup"].get("cleaned"))
        write_json(out_path, result)
        if not result["checks"]["native_stale_cleanup_ok"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        image_ready = wsta42.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)
        result["checks"]["remote_image_ready"] = bool(image_ready)
        write_json(out_path, result)
        if not image_ready:
            result["decision"] = result.get("decision") or classify(result)
            return finish_result(out_path, result)

        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        public_key = d2.read_public_key(run_dir)
        stage_script_path = run_dir / "wsta151_admin_trace_stage.sh"
        stage_script_path.write_text(
            admin_trace_stage_and_start_script(args.mountpoint, public_key, args.device_ip, args.ssh_port) + "\n",
            encoding="utf-8",
        )
        stage_script_path.chmod(0o700)
        result["admin_trace_stage_script_upload"] = wsta120.install_remote_file(
            args,
            stage_script_path,
            REMOTE_ADMIN_TRACE_STAGE_SCRIPT,
            timeout=args.transfer_timeout + args.bridge_timeout + 120.0,
        )
        result["checks"]["admin_trace_stage_script_uploaded"] = bool(
            result["admin_trace_stage_script_upload"].get("installed")
        )
        write_json(out_path, result)
        if not result["checks"]["admin_trace_stage_script_uploaded"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        mount_record = wsta19.bridge_shell(
            args,
            wsta94.wsta94_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        result["checks"]["chroot_mount_ready"] = bool(
            result["mount_parse"].get("mount_ready") and result["mount_parse"].get("mounted")
        )
        write_json(out_path, result)
        if not result["checks"]["chroot_mount_ready"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        stage_record = wsta120.bridge_run_script_file(
            args,
            REMOTE_ADMIN_TRACE_STAGE_SCRIPT,
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["admin_trace_stage"] = stage_record
        result["admin_trace_stage_parse"] = parse_stage(stage_record)
        stage = result["admin_trace_stage_parse"]
        result["checks"]["admin_trace_stage_pass"] = bool(
            stage.get("stage_done")
            and stage.get("root_authorized_keys_absent")
            and stage.get("admin_passwd_line")
            and stage.get("admin_group_line")
            and stage.get("admin_shadow_line")
            and stage.get("admin_authorized_keys")
            and stage.get("dropbear_present")
            and stage.get("strace_present")
            and stage.get("dropbear_key_generated")
            and stage.get("dropbear_command_safe")
            and stage.get("trace_alive")
            and stage.get("dropbear_listen")
        )
        write_json(out_path, result)
        if not result["checks"]["admin_trace_stage_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        admin_cmd = (
            "echo A90WSTA120_ADMIN_UID=$(id -u); "
            "echo A90WSTA120_ADMIN_GID=$(id -g); "
            "echo A90WSTA120_ADMIN_USER=$(id -un); "
            "echo A90WSTA120_ADMIN_GROUP=$(id -gn)"
        )
        result["admin_ssh"] = wsta120.ssh_probe(args, run_dir, "a90admin", admin_cmd, timeout=args.ssh_timeout)
        result["admin_ssh_parse"] = wsta120.parse_admin_ssh(result["admin_ssh"])
        admin = result["admin_ssh_parse"]
        result["checks"]["admin_ssh_pass"] = bool(
            admin.get("ssh_ok")
            and admin.get("uid_3903")
            and admin.get("gid_3903")
            and admin.get("user_a90admin")
            and admin.get("group_a90admin")
        )
        write_json(out_path, result)
        if not result["checks"]["admin_ssh_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["root_ssh"] = wsta120.ssh_probe(args, run_dir, "root", "id -u", timeout=args.ssh_timeout)
        result["checks"]["root_ssh_rejected"] = result["root_ssh"].get("returncode") != 0
        write_json(out_path, result)
        if not result["checks"]["root_ssh_rejected"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["trace_snapshot"] = wsta19.bridge_shell(
            args,
            snapshot_trace_script(args.mountpoint),
            timeout=args.trace_timeout,
            allow_error=True,
        )
        parsed = parse_snapshot(result["trace_snapshot"])
        result["trace_snapshot_parse"] = parsed
        result["checks"].update({
            "trace_snapshot_pass": bool(
                result["trace_snapshot"].get("rc") == 0 and parsed.get("snapshot_done")
            ),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "trace_snapshot_file_nonempty": bool(parsed.get("trace_snapshot_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
            "syscall_accept_observed": bool(parsed.get("accept_observed")),
            "dropbear_log_policy_clean": bool(parsed.get("dropbear_log_policy_clean")),
        })
        write_json(out_path, result)
        if not result["checks"]["trace_snapshot_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["trace_artifacts"] = (
            fetch_trace_artifacts(args, run_dir)
            if parsed.get("trace_file_nonempty") and parsed.get("syscall_profile_nonempty")
            else {"all_saved": False, "skipped": True, "reason": "trace-not-complete"}
        )
        result["syscall_profile"] = syscall_profile(
            parsed,
            result["checks"].get("admin_ssh_pass", False),
            result["checks"].get("root_ssh_rejected", False),
            f"{args.device_ip}:{args.ssh_port}",
            result.get("trace_artifacts"),
        )
        result["checks"]["trace_artifact_saved"] = bool(result["trace_artifacts"].get("all_saved"))
        write_json(out_path, result)
    finally:
        if mounted:
            result["trace_cleanup"] = wsta19.bridge_shell(
                args,
                trace_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["trace_cleanup_parse"] = parse_trace_cleanup(result["trace_cleanup"])
            result["cleanup"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
        else:
            result["trace_cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["trace_cleanup_parse"] = {}
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}

        result["checks"]["trace_cleanup_ok"] = bool(not mounted or trace_cleanup_ok(result))
        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["chroot_cleanup_ok"] = bool(not mounted or chroot_cleanup_ok(result))
        result["checks"]["final_selftest_fail_zero"] = wsta2.selftest_passed(result["final_selftest"].get("text", ""))
        write_json(out_path, result)

    result["decision"] = classify(result)
    return finish_result(out_path, result)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--trace-timeout", type=float, default=75.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=WSTA115_STRACE_IMAGE)
    parser.add_argument("--local-image-sha256", default=WSTA115_STRACE_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--execute-dropbear-admin-syscall-trace-live", action="store_true")
    parser.add_argument("--allow-dropbear-admin-trace-live", action="store_true")
    parser.add_argument("--ack-admin-key-material", action="store_true")
    parser.add_argument("--ack-root-login-negative-test", action="store_true")
    parser.add_argument("--ack-private-trace-artifact", action="store_true")
    parser.add_argument("--ack-runtime-cleanup", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta151-dropbear-admin-syscall-trace-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA151 Dropbear admin syscall trace",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA151 Dropbear admin syscall trace",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta151-runner-error"
        result["error"] = str(exc)
        finish_result(out_path, result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
