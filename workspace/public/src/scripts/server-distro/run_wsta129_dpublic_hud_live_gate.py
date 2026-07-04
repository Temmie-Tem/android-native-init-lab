#!/usr/bin/env python3
"""Run WSTA129: bounded D-public HUD live gate inside the Debian chroot.

WSTA127 defined the HUD hardening model.  WSTA129 is the explicit live gate for
that model:

  * mount the known Debian image as the SD-backed chroot service surface,
  * start temporary key-only dropbear using the existing WSTA110 pattern,
  * stage service hardening assets plus the HUD binary,
  * apply a temporary /dev/dri/card0 group-read/write policy for a90hud,
  * launch ``a90-service-launch dpublic-hud strace ... a90-dpublic-hud``,
  * prove UID/GID 3904, NoNewPrivs=1, CapEff=0, no socket fd, DRM fd present,
  * save private raw trace and compact syscall profile under the run dir,
  * clean HUD processes, trace sidecars, DRM node mode/owner, and chroot state.

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

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta129-dpublic-hud-live-pass"
RESULT_NAME = "wsta129_result.json"
REMOTE_SERVICE_LAUNCHER = wsta110.REMOTE_SERVICE_LAUNCHER
REMOTE_SERVICE_POLICY = wsta110.REMOTE_SERVICE_POLICY
REMOTE_HUD = "/" + str(wsta3.DPUBLIC_BINARY_TARGETS["hud"])
REMOTE_TRACE_DIR = "/tmp/a90-wsta129-dpublic-hud-live"
REMOTE_TRACE_RAW = REMOTE_TRACE_DIR + "/hud.strace"
REMOTE_TRACE_SYSCALLS = REMOTE_TRACE_DIR + "/hud.syscalls"
REMOTE_HUD_LOG = REMOTE_TRACE_DIR + "/hud.log"
REMOTE_DRM_BACKUP = REMOTE_TRACE_DIR + "/card0.before"
CORE_SYSCALLS = ("execve", "openat", "ioctl", "mmap", "munmap")
NETWORK_SYSCALLS = ("socket", "bind", "listen", "accept", "connect")


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
    if not args.execute_hud_live:
        return False, "wsta129-blocked-hud-live-required"
    if not args.allow_hud_live:
        return False, "wsta129-blocked-hud-live-allow-required"
    if not args.ack_drm_control:
        return False, "wsta129-blocked-drm-control-ack-required"
    if not args.ack_private_trace_artifact:
        return False, "wsta129-blocked-private-trace-artifact-ack-required"
    if not args.ack_runtime_cleanup:
        return False, "wsta129-blocked-runtime-cleanup-ack-required"
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
        "drm_open": "explicit-live-gated-temporary" if gate_ok else False,
        "kms_setcrtc": "explicit-live-gated-temporary" if gate_ok else False,
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "runtime_cleanup_required": gate_ok,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def stage_hud_binary(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    if not args.hud.is_file():
        return {
            "staged": False,
            "reason": "hud-binary-missing",
            "local_path": rel(args.hud),
            "remote_path": REMOTE_HUD,
            "secret_values_logged": 0,
        }
    record = wsta42.ssh_write_file(
        args,
        run_dir,
        args.hud,
        REMOTE_HUD,
        timeout=args.hud_stage_timeout,
    )
    record["service"] = "dpublic-hud"
    record["secret_values_logged"] = 0
    return record


def hud_probe_script(runtime_sec: int) -> str:
    runtime = max(1, min(int(runtime_sec), 60))
    return f"""
set -eu
echo A90WSTA129_HUD_PROBE_BEGIN
RUN_DIR={shlex.quote(REMOTE_TRACE_DIR)}
TRACE={shlex.quote(REMOTE_TRACE_RAW)}
SYSCALLS={shlex.quote(REMOTE_TRACE_SYSCALLS)}
HUD_LOG={shlex.quote(REMOTE_HUD_LOG)}
CARD0_BACKUP={shlex.quote(REMOTE_DRM_BACKUP)}
LAUNCHER={shlex.quote(REMOTE_SERVICE_LAUNCHER)}
POLICY={shlex.quote(REMOTE_SERVICE_POLICY)}
HUD={shlex.quote(REMOTE_HUD)}
DRM_NODE=/dev/dri/card0
PROC_MOUNTED=0
TRACE_PID=""
HUD_PID=""
cleanup() {{
  set +e
  if [ -n "$HUD_PID" ]; then /bin/kill "$HUD_PID" >/dev/null 2>&1 || true; fi
  if [ -n "$TRACE_PID" ]; then /bin/kill "$TRACE_PID" >/dev/null 2>&1 || true; fi
  /bin/sleep 1
  if [ -n "$HUD_PID" ]; then /bin/kill -9 "$HUD_PID" >/dev/null 2>&1 || true; fi
  if [ -n "$TRACE_PID" ]; then /bin/kill -9 "$TRACE_PID" >/dev/null 2>&1 || true; fi
  if [ -f "$CARD0_BACKUP" ] && [ -e "$DRM_NODE" ]; then
    IFS=: read -r A90_UID A90_GID A90_MODE < "$CARD0_BACKUP"
    /bin/chown "$A90_UID:$A90_GID" "$DRM_NODE" >/dev/null 2>&1 || true
    /bin/chmod "$A90_MODE" "$DRM_NODE" >/dev/null 2>&1 || true
    echo A90WSTA129_DRM_NODE_RESTORED=1
  fi
  if [ "$PROC_MOUNTED" = "1" ]; then
    if /bin/umount /proc >/dev/null 2>&1; then
      echo A90WSTA129_PROC_UNMOUNTED=1
    else
      echo A90WSTA129_PROC_UNMOUNT_DEFERRED=1
    fi
    PROC_MOUNTED=0
  fi
}}
fail() {{
  echo "A90WSTA129_FAIL reason=$1 rc=$2"
  exit "$2"
}}
find_hud_pid() {{
  for P in /proc/[0-9]*; do
    [ -r "$P/comm" ] || continue
    COMM=$(/bin/cat "$P/comm" 2>/dev/null || true)
    if [ "$COMM" = "a90-dpublic-hud" ]; then /usr/bin/basename "$P"; return 0; fi
  done
  return 1
}}
fd_probe() {{
  SOCKET_COUNT=0
  DRM_PRESENT=0
  for FD in /proc/$HUD_PID/fd/*; do
    TARGET=$(/bin/readlink "$FD" 2>/dev/null || true)
    case "$TARGET" in
      socket:*) SOCKET_COUNT=$((SOCKET_COUNT + 1)) ;;
      */dev/dri/card0|/dev/dri/card0) DRM_PRESENT=1 ;;
    esac
  done
  echo A90WSTA129_SOCKET_FD_COUNT=$SOCKET_COUNT
  if [ "$SOCKET_COUNT" = "0" ]; then echo A90WSTA129_SOCKET_FD_ABSENT=1; else fail socket-fd 47; fi
  if [ "$DRM_PRESENT" = "1" ]; then echo A90WSTA129_DRM_FD_PRESENT=1; else fail drm-fd 48; fi
}}
trap cleanup EXIT INT TERM
/bin/mkdir -p /proc "$RUN_DIR"
/bin/mount -t proc proc /proc
PROC_MOUNTED=1
echo A90WSTA129_PROC_MOUNTED=1
if [ ! -e /etc/a90-dpublic/cloudflared-quick-enable ]; then echo A90WSTA129_PUBLIC_ENABLE_ABSENT=1; else echo A90WSTA129_PUBLIC_ENABLE_ABSENT=0; fail public-enabled 30; fi
[ -x "$LAUNCHER" ] && echo A90WSTA129_LAUNCHER_PRESENT=1 || fail launcher-missing 31
[ -f "$POLICY" ] && echo A90WSTA129_POLICY_PRESENT=1 || fail policy-missing 32
[ -x "$HUD" ] && echo A90WSTA129_HUD_BINARY_PRESENT=1 || fail hud-missing 33
if command -v setpriv >/dev/null 2>&1; then echo A90WSTA129_SETPRIV_PRESENT=1; else echo A90WSTA129_SETPRIV_PRESENT=0; fail setpriv-missing 34; fi
if command -v strace >/dev/null 2>&1; then STRACE=$(command -v strace); echo A90WSTA129_STRACE_PRESENT=1; else echo A90WSTA129_STRACE_PRESENT=0; fail strace-missing 35; fi
if [ ! -r /sys/class/drm/card0/dev ]; then echo A90WSTA129_DRM_SYSFS_PRESENT=0; fail drm-sysfs 36; fi
echo A90WSTA129_DRM_SYSFS_PRESENT=1
DEV_INFO=$(/bin/cat /sys/class/drm/card0/dev)
MAJOR=${{DEV_INFO%:*}}
MINOR=${{DEV_INFO#*:}}
/bin/mkdir -p /dev/dri
if [ ! -e "$DRM_NODE" ]; then /bin/mknod "$DRM_NODE" c "$MAJOR" "$MINOR"; fi
[ -e "$DRM_NODE" ] && echo A90WSTA129_DRM_NODE_PRESENT=1 || fail drm-node 37
/usr/bin/stat -c '%u:%g:%a' "$DRM_NODE" > "$CARD0_BACKUP"
/bin/chgrp a90hud "$DRM_NODE"
/bin/chmod 0660 "$DRM_NODE"
echo A90WSTA129_DRM_NODE_POLICY_APPLIED=1
/bin/rm -f "$TRACE" "$SYSCALLS" "$HUD_LOG"
: > "$TRACE"
/bin/chmod 0666 "$TRACE"
"$LAUNCHER" dpublic-hud "$STRACE" -qq -f -s 96 -o "$TRACE" "$HUD" 1 >"$HUD_LOG" 2>&1 &
TRACE_PID=$!
echo A90WSTA129_TRACE_PROCESS_STARTED=1
for _i in 1 2 3 4 5 6 7 8 9 10; do
  HUD_PID=$(find_hud_pid || true)
  if [ -n "$HUD_PID" ]; then break; fi
  if ! /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then break; fi
  /bin/sleep 1
done
if [ -n "$HUD_PID" ]; then echo A90WSTA129_HUD_PID_FOUND=1; else /bin/cat "$HUD_LOG" || true; fail hud-pid 38; fi
/usr/bin/awk '/^Uid:/{{print "A90WSTA129_HUD_UID_REAL=" $2; print "A90WSTA129_HUD_UID_EFFECTIVE=" $3}}' "/proc/$HUD_PID/status"
/usr/bin/awk '/^Gid:/{{print "A90WSTA129_HUD_GID_REAL=" $2; print "A90WSTA129_HUD_GID_EFFECTIVE=" $3}}' "/proc/$HUD_PID/status"
/usr/bin/awk '/^NoNewPrivs:/{{print "A90WSTA129_HUD_NO_NEW_PRIVS=" $2}}' "/proc/$HUD_PID/status"
/usr/bin/awk '/^CapEff:/{{print "A90WSTA129_HUD_CAP_EFF=" $2}}' "/proc/$HUD_PID/status"
fd_probe
/bin/sleep {runtime}
/bin/kill "$HUD_PID" >/dev/null 2>&1 || true
/bin/sleep 1
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then /bin/kill "$TRACE_PID" >/dev/null 2>&1 || true; fi
/bin/sleep 1
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then /bin/kill -9 "$TRACE_PID" >/dev/null 2>&1 || true; fi
wait "$TRACE_PID" >/dev/null 2>&1 || true
/bin/cat "$HUD_LOG" || true
if /bin/grep -q 'a90_service_launcher_decision=exec' "$HUD_LOG"; then echo A90WSTA129_LAUNCHER_EXEC_LOGGED=1; else fail launcher-exec 39; fi
if /bin/grep -q 'a90_service_launcher_service=dpublic-hud' "$HUD_LOG"; then echo A90WSTA129_LAUNCHER_SERVICE_LOGGED=1; else fail launcher-service 40; fi
if /bin/grep -q 'a90_service_launcher_user=a90hud' "$HUD_LOG"; then echo A90WSTA129_LAUNCHER_USER_LOGGED=1; else fail launcher-user 41; fi
[ -s "$TRACE" ] && echo A90WSTA129_TRACE_FILE_NONEMPTY=1 || fail trace-empty 42
/usr/bin/awk '{{ line=$0; sub(/^\\[pid +[0-9]+\\] +/, "", line); sub(/^[0-9]+ +/, "", line); if (match(line, /^[A-Za-z0-9_]+\\(/)) {{ name=substr(line, 1, index(line, "(")-1); seen[name]=1 }} }} END {{ for (name in seen) print name }}' "$TRACE" | /usr/bin/sort > "$SYSCALLS"
[ -s "$SYSCALLS" ] && echo A90WSTA129_SYSCALL_PROFILE_NONEMPTY=1 || fail syscalls-empty 43
COUNT=$(/usr/bin/wc -l < "$SYSCALLS" | /usr/bin/awk '{{print $1}}')
echo A90WSTA129_SYSCALL_COUNT=$COUNT
if /bin/grep -qx execve "$SYSCALLS"; then echo A90WSTA129_SYSCALL_HAS_EXECVE=1; else echo A90WSTA129_SYSCALL_HAS_EXECVE=0; fail syscall-execve 44; fi
if /bin/grep -qx openat "$SYSCALLS"; then echo A90WSTA129_SYSCALL_HAS_OPENAT=1; else echo A90WSTA129_SYSCALL_HAS_OPENAT=0; fail syscall-openat 45; fi
if /bin/grep -qx ioctl "$SYSCALLS"; then echo A90WSTA129_SYSCALL_HAS_IOCTL=1; else echo A90WSTA129_SYSCALL_HAS_IOCTL=0; fail syscall-ioctl 46; fi
if /bin/grep -qx mmap "$SYSCALLS"; then echo A90WSTA129_SYSCALL_HAS_MMAP=1; else echo A90WSTA129_SYSCALL_HAS_MMAP=0; fail syscall-mmap 49; fi
if /bin/grep -qx munmap "$SYSCALLS"; then echo A90WSTA129_SYSCALL_HAS_MUNMAP=1; else echo A90WSTA129_SYSCALL_HAS_MUNMAP=0; fail syscall-munmap 50; fi
if /bin/grep -Eq '^(socket|bind|listen|accept|connect)$' "$SYSCALLS"; then echo A90WSTA129_SYSCALL_NETWORK_ABSENT=0; fail network-syscall 51; else echo A90WSTA129_SYSCALL_NETWORK_ABSENT=1; fi
echo A90WSTA129_SYSCALL_LIST_BEGIN
/bin/cat "$SYSCALLS"
echo A90WSTA129_SYSCALL_LIST_END
cleanup
trap - EXIT
echo A90WSTA129_HUD_PROBE_DONE
""".strip()


def syscall_names_from_stdout(stdout: str) -> list[str]:
    inside = False
    names: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == "A90WSTA129_SYSCALL_LIST_BEGIN":
            inside = True
            continue
        if line == "A90WSTA129_SYSCALL_LIST_END":
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def parse_hud_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    syscalls = syscall_names_from_stdout(stdout)
    syscall_set = set(syscalls)
    return {
        "proof_begin": "A90WSTA129_HUD_PROBE_BEGIN" in stdout,
        "proof_done": "A90WSTA129_HUD_PROBE_DONE" in stdout,
        "proc_mounted": "A90WSTA129_PROC_MOUNTED=1" in stdout,
        "proc_unmounted": "A90WSTA129_PROC_UNMOUNTED=1" in stdout,
        "proc_unmount_deferred": "A90WSTA129_PROC_UNMOUNT_DEFERRED=1" in stdout,
        "public_enable_absent": "A90WSTA129_PUBLIC_ENABLE_ABSENT=1" in stdout,
        "launcher_present": "A90WSTA129_LAUNCHER_PRESENT=1" in stdout,
        "policy_present": "A90WSTA129_POLICY_PRESENT=1" in stdout,
        "hud_binary_present": "A90WSTA129_HUD_BINARY_PRESENT=1" in stdout,
        "setpriv_present": "A90WSTA129_SETPRIV_PRESENT=1" in stdout,
        "strace_present": "A90WSTA129_STRACE_PRESENT=1" in stdout,
        "drm_sysfs_present": "A90WSTA129_DRM_SYSFS_PRESENT=1" in stdout,
        "drm_node_present": "A90WSTA129_DRM_NODE_PRESENT=1" in stdout,
        "drm_node_policy_applied": "A90WSTA129_DRM_NODE_POLICY_APPLIED=1" in stdout,
        "drm_node_restored": "A90WSTA129_DRM_NODE_RESTORED=1" in stdout,
        "trace_process_started": "A90WSTA129_TRACE_PROCESS_STARTED=1" in stdout,
        "hud_pid_found": "A90WSTA129_HUD_PID_FOUND=1" in stdout,
        "hud_uid_real": "A90WSTA129_HUD_UID_REAL=3904" in stdout,
        "hud_uid_effective": "A90WSTA129_HUD_UID_EFFECTIVE=3904" in stdout,
        "hud_gid_real": "A90WSTA129_HUD_GID_REAL=3904" in stdout,
        "hud_gid_effective": "A90WSTA129_HUD_GID_EFFECTIVE=3904" in stdout,
        "hud_no_new_privs": "A90WSTA129_HUD_NO_NEW_PRIVS=1" in stdout,
        "hud_cap_eff_zero": "A90WSTA129_HUD_CAP_EFF=0000000000000000" in stdout,
        "hud_socket_fd_absent": "A90WSTA129_SOCKET_FD_ABSENT=1" in stdout,
        "hud_drm_fd_present": "A90WSTA129_DRM_FD_PRESENT=1" in stdout,
        "launcher_exec_logged": "A90WSTA129_LAUNCHER_EXEC_LOGGED=1" in stdout,
        "launcher_service_logged": "A90WSTA129_LAUNCHER_SERVICE_LOGGED=1" in stdout,
        "launcher_user_logged": "A90WSTA129_LAUNCHER_USER_LOGGED=1" in stdout,
        "trace_file_nonempty": "A90WSTA129_TRACE_FILE_NONEMPTY=1" in stdout,
        "syscall_profile_nonempty": "A90WSTA129_SYSCALL_PROFILE_NONEMPTY=1" in stdout,
        "network_syscalls_absent": "A90WSTA129_SYSCALL_NETWORK_ABSENT=1" in stdout
        and not any(name in syscall_set for name in NETWORK_SYSCALLS),
        "core_syscalls_observed": all(name in syscall_set for name in CORE_SYSCALLS),
        "syscall_names": syscalls,
        "syscall_count": len(syscalls),
        "secret_values_logged": 0,
    }


def hud_runtime_profile(parsed: dict[str, Any], trace_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta129-dpublic-hud-runtime-profile-v1",
        "service": "dpublic-hud",
        "scope": "hud-drm-runtime-only",
        "launcher": REMOTE_SERVICE_LAUNCHER,
        "command_shape": "a90-service-launch dpublic-hud strace -f a90-dpublic-hud 1",
        "public_default_off": bool(parsed.get("public_enable_absent")),
        "uid_gid_3904": bool(
            parsed.get("hud_uid_real")
            and parsed.get("hud_uid_effective")
            and parsed.get("hud_gid_real")
            and parsed.get("hud_gid_effective")
        ),
        "no_new_privs": bool(parsed.get("hud_no_new_privs")),
        "cap_eff_zero": bool(parsed.get("hud_cap_eff_zero")),
        "no_socket_fd": bool(parsed.get("hud_socket_fd_absent")),
        "no_network_syscalls": bool(parsed.get("network_syscalls_absent")),
        "drm_node_policy_applied": bool(parsed.get("drm_node_policy_applied")),
        "drm_node_restored": bool(parsed.get("drm_node_restored")),
        "drm_fd_present": bool(parsed.get("hud_drm_fd_present")),
        "core_syscalls": list(CORE_SYSCALLS),
        "forbidden_network_syscalls": list(NETWORK_SYSCALLS),
        "core_syscalls_observed": bool(parsed.get("core_syscalls_observed")),
        "syscall_count": int(parsed.get("syscall_count") or 0),
        "syscall_names": list(parsed.get("syscall_names") or []),
        "trace_artifacts": trace_artifacts or {},
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def decode_subprocess_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_hud_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = [*wsta42.ssh_command(args, run_dir), hud_probe_script(args.hud_runtime_sec)]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.hud_timeout,
            check=False,
        )
        record = {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        record = {
            "command": command,
            "returncode": None,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "stdout": decode_subprocess_stream(exc.stdout),
            "stderr": decode_subprocess_stream(exc.stderr),
            "timed_out": True,
            "timeout_sec": args.hud_timeout,
        }
    record["parsed"] = parse_hud_probe(record)
    return record


def fetch_remote_file(args: argparse.Namespace,
                      run_dir: Path,
                      remote_path: str,
                      local_path: Path,
                      *,
                      timeout: float) -> dict[str, Any]:
    command = [
        *wsta42.ssh_command(args, run_dir),
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
    raw = fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_RAW,
        run_dir / "wsta129_hud.strace",
        timeout=args.ssh_timeout,
    )
    syscalls = fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_SYSCALLS,
        run_dir / "wsta129_hud.syscalls",
        timeout=args.ssh_timeout,
    )
    return {
        "raw_trace": raw,
        "syscall_list": syscalls,
        "all_saved": bool(raw.get("saved") and syscalls.get("saved")),
        "private_artifact": True,
        "secret_values_logged": 0,
    }


def hud_runtime_cleanup_script() -> str:
    return f"""
set +e
echo A90WSTA129_RUNTIME_CLEANUP_BEGIN
RUN_DIR={shlex.quote(REMOTE_TRACE_DIR)}
CARD0_BACKUP={shlex.quote(REMOTE_DRM_BACKUP)}
DRM_NODE=/dev/dri/card0
for P in /proc/[0-9]*; do
  [ -r "$P/comm" ] || continue
  COMM=$(/bin/cat "$P/comm" 2>/dev/null || true)
  if [ "$COMM" = "a90-dpublic-hud" ]; then /bin/kill "$(/usr/bin/basename "$P")" >/dev/null 2>&1 || true; fi
done
/bin/sleep 1
for P in /proc/[0-9]*; do
  [ -r "$P/comm" ] || continue
  COMM=$(/bin/cat "$P/comm" 2>/dev/null || true)
  if [ "$COMM" = "a90-dpublic-hud" ]; then /bin/kill -9 "$(/usr/bin/basename "$P")" >/dev/null 2>&1 || true; fi
done
if [ -f "$CARD0_BACKUP" ] && [ -e "$DRM_NODE" ]; then
  IFS=: read -r A90_UID A90_GID A90_MODE < "$CARD0_BACKUP"
  /bin/chown "$A90_UID:$A90_GID" "$DRM_NODE" >/dev/null 2>&1 || true
  /bin/chmod "$A90_MODE" "$DRM_NODE" >/dev/null 2>&1 || true
  echo A90WSTA129_CLEANUP_DRM_NODE_RESTORED=1
else
  echo A90WSTA129_CLEANUP_DRM_NODE_RESTORED=not-needed
fi
/bin/rm -rf "$RUN_DIR" /run/a90-dpublic/dpublic-hud.pid /run/a90-dpublic/dpublic-hud.log
HUD_ABSENT=1
for P in /proc/[0-9]*; do
  [ -r "$P/comm" ] || continue
  COMM=$(/bin/cat "$P/comm" 2>/dev/null || true)
  if [ "$COMM" = "a90-dpublic-hud" ]; then HUD_ABSENT=0; fi
done
echo A90WSTA129_HUD_ABSENT=$HUD_ABSENT
echo A90WSTA129_RUNTIME_CLEANUP_DONE
""".strip()


def cleanup_hud_runtime(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, hud_runtime_cleanup_script(), timeout=args.cleanup_timeout)
    text = str(record.get("stdout") or "")
    record["cleaned"] = (
        record.get("returncode") == 0
        and "A90WSTA129_RUNTIME_CLEANUP_DONE" in text
        and "A90WSTA129_HUD_ABSENT=1" in text
    )
    record["secret_values_logged"] = 0
    return record


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta129-blocked-explicit-live-gate"),
        ("local_image_present", "wsta129-blocked-local-image-missing"),
        ("hud_binary_present_local", "wsta129-blocked-hud-binary-missing"),
        ("baseline_selftest_fail_zero", "wsta129-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta129-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta129-blocked-remote-image"),
        ("chroot_mount_ready", "wsta129-blocked-chroot-mount"),
        ("dropbear_started", "wsta129-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta129-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta129-blocked-service-hardening-stage"),
        ("hud_binary_staged", "wsta129-blocked-hud-binary-stage"),
        ("hud_probe_completed", "wsta129-blocked-hud-probe"),
        ("public_default_off", "wsta129-blocked-public-default-off"),
        ("strace_present", "wsta129-blocked-strace-missing"),
        ("drm_node_policy_applied", "wsta129-blocked-drm-node-policy"),
        ("trace_started", "wsta129-blocked-trace-start"),
        ("hud_uid_gid_pass", "wsta129-blocked-hud-uid-gid"),
        ("hud_no_new_privs_pass", "wsta129-blocked-hud-no-new-privs"),
        ("hud_cap_eff_zero_pass", "wsta129-blocked-hud-cap-eff"),
        ("hud_no_network_pass", "wsta129-blocked-hud-network"),
        ("hud_drm_node_observed", "wsta129-blocked-hud-drm-node"),
        ("trace_file_nonempty", "wsta129-blocked-trace-empty"),
        ("syscall_profile_nonempty", "wsta129-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta129-blocked-core-syscalls-missing"),
        ("trace_artifact_saved", "wsta129-blocked-trace-artifact-save"),
        ("runtime_cleanup_ok", "wsta129-blocked-runtime-cleanup"),
        ("chroot_cleanup_ok", "wsta129-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta129-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA129 D-public HUD live gate",
        "default_mode": "device-inert-until-explicit-live-gates",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--execute-hud-live",
            "--allow-hud-live",
            "--ack-drm-control",
            "--ack-private-trace-artifact",
            "--ack-runtime-cleanup",
        ],
        "device_action": "explicitly gated",
        "boot_flash": False,
        "native_reboot": False,
        "public_tunnel": False,
        "drm_open": "temporary /dev/dri/card0 only",
        "kms_setcrtc": "temporary HUD proof only",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta129-dpublic-hud-live-gate-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA129 D-public HUD live gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "remote_image": args.remote_image,
        "remote_clean_image": args.remote_clean_image if wsta42.remote_clean_image_enabled(args) else None,
        "mountpoint": args.mountpoint,
        "safety": safety(gate_ok),
        "checks": {
            "explicit_live_gate": gate_ok,
            "public_url_value_logged": False,
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
        result["decision"] = classify(result)
        return finish_result(out_path, result)
    local_sha = sha256_file(local_image)
    result["local_image"] = rel(local_image)
    result["local_image_sha256"] = local_sha
    result["checks"]["local_image_present"] = True
    if args.local_image_sha256 and args.local_image_sha256 != local_sha:
        result["local_image_expected_sha256"] = args.local_image_sha256
        result["checks"]["remote_image_ready"] = False
        result["decision"] = "wsta129-blocked-local-image-sha"
        return finish_result(out_path, result)

    result["hud_binary"] = {
        "local_path": rel(args.hud),
        "present": args.hud.is_file(),
        "sha256": sha256_file(args.hud) if args.hud.is_file() else None,
        "remote_path": REMOTE_HUD,
    }
    result["checks"]["hud_binary_present_local"] = bool(args.hud.is_file())
    write_json(out_path, result)
    if not result["checks"]["hud_binary_present_local"]:
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
        write_json(out_path, result)

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

        start_record = wsta19.bridge_shell(
            args,
            wsta94.wsta94_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        result["checks"]["dropbear_started"] = bool(
            result["dropbear_parse"].get("started")
            and result["dropbear_parse"].get("authorized_keys")
            and result["dropbear_parse"].get("shadow_temp_key_only")
        )
        write_json(out_path, result)
        if not result["checks"]["dropbear_started"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        result["checks"]["debian_ssh_marker"] = bool(result["ssh_parse"].get("marker"))
        write_json(out_path, result)
        if not result["checks"]["debian_ssh_marker"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["service_hardening_stage"] = wsta110.stage_service_hardening_assets(args, run_dir)
        result["checks"]["service_hardening_assets_staged"] = wsta110.stage_ok(result["service_hardening_stage"])
        result["hud_binary_stage"] = stage_hud_binary(args, run_dir)
        result["checks"]["hud_binary_staged"] = bool(result["hud_binary_stage"].get("staged"))
        write_json(out_path, result)
        if not (result["checks"]["service_hardening_assets_staged"] and result["checks"]["hud_binary_staged"]):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["hud_probe"] = run_hud_probe(args, run_dir)
        parsed = result["hud_probe"].get("parsed", {})
        result["trace_artifacts"] = (
            fetch_trace_artifacts(args, run_dir)
            if parsed.get("trace_file_nonempty") and parsed.get("syscall_profile_nonempty")
            else {"all_saved": False, "skipped": True, "reason": "trace-not-complete"}
        )
        result["hud_runtime_profile"] = hud_runtime_profile(parsed, result.get("trace_artifacts"))
        result["checks"].update({
            "hud_probe_completed": bool(
                result["hud_probe"].get("returncode") == 0
                and not result["hud_probe"].get("timed_out")
            ),
            "public_default_off": bool(parsed.get("public_enable_absent")),
            "strace_present": bool(parsed.get("strace_present")),
            "drm_node_policy_applied": bool(parsed.get("drm_node_policy_applied")),
            "trace_started": bool(parsed.get("trace_process_started") and parsed.get("hud_pid_found")),
            "hud_uid_gid_pass": bool(
                parsed.get("hud_uid_real")
                and parsed.get("hud_uid_effective")
                and parsed.get("hud_gid_real")
                and parsed.get("hud_gid_effective")
            ),
            "hud_no_new_privs_pass": bool(parsed.get("hud_no_new_privs")),
            "hud_cap_eff_zero_pass": bool(parsed.get("hud_cap_eff_zero")),
            "hud_no_network_pass": bool(parsed.get("hud_socket_fd_absent") and parsed.get("network_syscalls_absent")),
            "hud_drm_node_observed": bool(
                parsed.get("drm_node_present")
                and parsed.get("hud_drm_fd_present")
                and parsed.get("core_syscalls_observed")
            ),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
            "trace_artifact_saved": bool(result["trace_artifacts"].get("all_saved")),
        })
        write_json(out_path, result)
    finally:
        if mounted:
            result["hud_runtime_cleanup"] = cleanup_hud_runtime(args, run_dir)
            result["checks"]["runtime_cleanup_ok"] = bool(result["hud_runtime_cleanup"].get("cleaned"))
            result["service_probe_cleanup"] = wsta19.bridge_shell(
                args,
                wsta110.service_probe_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
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
            result["hud_runtime_cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}

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
    parser.add_argument("--hud-timeout", type=float, default=90.0)
    parser.add_argument("--hud-stage-timeout", type=float, default=45.0)
    parser.add_argument("--hud-runtime-sec", type=int, default=5)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=d1.EXPECTED_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--hud", type=Path, default=wsta3.DEFAULT_HUD)
    parser.add_argument("--execute-hud-live", action="store_true")
    parser.add_argument("--allow-hud-live", action="store_true")
    parser.add_argument("--ack-drm-control", action="store_true")
    parser.add_argument("--ack-private-trace-artifact", action="store_true")
    parser.add_argument("--ack-runtime-cleanup", action="store_true")
    parser.add_argument("--print-template", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta129-dpublic-hud-live-gate-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA129 D-public HUD live gate",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA129 D-public HUD live gate",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta129-runner-error"
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
