#!/usr/bin/env python3
"""Run WSTA124: bounded cloudflared runtime live gate.

WSTA122 defines the ``cloudflared-quick-tunnel`` service model and WSTA123
surfaces that model in operator status.  WSTA124 is the bounded live proof for
that runtime profile:

  * mount the known SD-backed Debian work image as a chroot service surface;
  * start temporary key-only Dropbear using the existing D2/WSTA110 pattern;
  * stage service identities, ``a90-service-launch``, D-public helpers, and
    cloudflared;
  * apply the already-proven loopback default-drop packet filter before public
    exposure;
  * start cloudflared through ``a90-service-launch`` as ``a90tunnel``;
  * prove UID/GID 3902, NoNewPrivs=1, CapEff=0, command shape, outbound-only
    socket posture, private URL artifact capture, syscall trace, and cleanup.

This unit does not build or flash a boot image, reboot native init, associate
Wi-Fi, run DHCP, touch userdata, or switch root.  It can open a short-lived
Cloudflare quick Tunnel only when the explicit live/public/private-artifact
gates are supplied.  The generated public URL is stored only under the private
run directory and is never printed or returned in JSON.
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
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402
import run_wsta114_syscall_trace_chroot_profile as wsta114  # noqa: E402
import run_wsta122_cloudflared_service_model as wsta122  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta124-cloudflared-runtime-live-pass"
RESULT_NAME = "wsta124_result.json"
TRY_DOMAIN = "try" + "cloudflare.com"
REMOTE_TRACE_DIR = "/tmp/a90-wsta124-cloudflared-runtime"
REMOTE_TRACE_RAW = REMOTE_TRACE_DIR + "/cloudflared.strace"
REMOTE_TRACE_SYSCALLS = REMOTE_TRACE_DIR + "/cloudflared.syscalls"
REMOTE_SOCKET_INODES = REMOTE_TRACE_DIR + "/cloudflared.sockinodes"
REMOTE_RUNTIME_SCRIPT = REMOTE_TRACE_DIR + "/runtime_probe.sh"
REMOTE_ENABLE = wsta122.QUICK_ENABLE
REMOTE_RUN_DIR = wsta122.RUN_DIR
REMOTE_CLOUDFLARED = wsta122.BINARY
REMOTE_CLOUDFLARED_PID = wsta122.PID_FILE
REMOTE_CLOUDFLARED_LOG = wsta122.LOG_FILE
REMOTE_URL_FILE = wsta122.URL_FILE
REMOTE_SMOKE_PID = wsta42.REMOTE_SMOKE_PID
REMOTE_SMOKE_LOG = wsta42.REMOTE_SMOKE_LOG
CORE_SYSCALLS = ("execve", "socket", "connect")


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
    if not args.execute_cloudflared_runtime_live:
        return False, "wsta124-blocked-cloudflared-runtime-live-required"
    if not args.allow_cloudflared_runtime_live:
        return False, "wsta124-blocked-cloudflared-runtime-live-allow-required"
    if not args.ack_public_exposure:
        return False, "wsta124-blocked-public-exposure-ack-required"
    if not args.ack_private_url_artifact:
        return False, "wsta124-blocked-private-url-artifact-ack-required"
    if not args.ack_runtime_cleanup:
        return False, "wsta124-blocked-runtime-cleanup-ack-required"
    return True, "ok"


def safety(gate_ok: bool) -> dict[str, Any]:
    return {
        "device_action": gate_ok,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": "explicit-live-gated-short-lived" if gate_ok else False,
        "public_smoke": False,
        "external_ping": False,
        "packet_filter_mutation": "explicit-live-gated-temporary" if gate_ok else False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only" if gate_ok else False,
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "public_url_artifact": "workspace-private-only" if gate_ok else False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA124 bounded cloudflared runtime live gate",
        "default_mode": "inert-until-explicit-live-ack",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--execute-cloudflared-runtime-live",
            "--allow-cloudflared-runtime-live",
            "--ack-public-exposure",
            "--ack-private-url-artifact",
            "--ack-runtime-cleanup",
        ],
        "device_action": "explicit-live-gated",
        "boot_flash": False,
        "public_tunnel": "explicit-live-gated-short-lived",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def cloudflared_runtime_probe_script(runtime_wait_sec: int) -> str:
    origin = wsta122.ORIGIN_URL
    metrics = wsta122.METRICS_BIND
    launcher = wsta110.REMOTE_SERVICE_LAUNCHER
    return f"""
set +e
echo A90WSTA124_RUNTIME_BEGIN
RUN_DIR={shlex.quote(REMOTE_TRACE_DIR)}
TRACE={shlex.quote(REMOTE_TRACE_RAW)}
SYSCALLS={shlex.quote(REMOTE_TRACE_SYSCALLS)}
SOCKET_INODES={shlex.quote(REMOTE_SOCKET_INODES)}
LAUNCHER={shlex.quote(launcher)}
CLOUDFLARED={shlex.quote(REMOTE_CLOUDFLARED)}
SMOKE={shlex.quote(wsta42.REMOTE_SMOKE)}
HTTP_GET={shlex.quote(wsta42.REMOTE_HTTP_GET)}
ENABLE={shlex.quote(REMOTE_ENABLE)}
PIDFILE={shlex.quote(REMOTE_CLOUDFLARED_PID)}
LOG={shlex.quote(REMOTE_CLOUDFLARED_LOG)}
URLFILE={shlex.quote(REMOTE_URL_FILE)}
SMOKE_PIDFILE={shlex.quote(REMOTE_SMOKE_PID)}
SMOKE_LOG={shlex.quote(REMOTE_SMOKE_LOG)}
TRY_DOMAIN={shlex.quote(TRY_DOMAIN)}
ORIGIN={shlex.quote(origin)}
METRICS={shlex.quote(metrics)}
PROC_MOUNTED=0
fail() {{
  echo "A90WSTA124_FAIL reason=$1 rc=$2"
  exit "$2"
}}
cleanup_proc() {{
  set +e
  if [ "$PROC_MOUNTED" = "1" ]; then
    /bin/umount /proc 2>/dev/null || /bin/umount -l /proc 2>/dev/null || true
    echo A90WSTA124_PROC_UNMOUNTED=1
    PROC_MOUNTED=0
  fi
}}
trap cleanup_proc EXIT INT TERM
/bin/mkdir -p /proc "$RUN_DIR" {shlex.quote(REMOTE_RUN_DIR)} "$(/usr/bin/dirname "$ENABLE")"
/bin/mount -t proc proc /proc 2>/dev/null
if /bin/grep -q ' /proc ' /proc/mounts 2>/dev/null; then PROC_MOUNTED=1; echo A90WSTA124_PROC_MOUNTED=1; else fail proc-mount 20; fi
if [ ! -e "$ENABLE" ]; then echo A90WSTA124_PUBLIC_ENABLE_INITIAL_ABSENT=1; else echo A90WSTA124_PUBLIC_ENABLE_INITIAL_ABSENT=0; fail preexisting-enable 21; fi
[ -x "$LAUNCHER" ] && echo A90WSTA124_LAUNCHER_PRESENT=1 || fail launcher-missing 22
[ -x "$CLOUDFLARED" ] && echo A90WSTA124_CLOUDFLARED_PRESENT=1 || fail cloudflared-missing 23
[ -x "$SMOKE" ] && echo A90WSTA124_SMOKE_PRESENT=1 || fail smoke-missing 24
[ -x "$HTTP_GET" ] && echo A90WSTA124_HTTP_GET_PRESENT=1 || fail http-get-missing 25
if command -v setpriv >/dev/null 2>&1; then echo A90WSTA124_SETPRIV_PRESENT=1; else fail setpriv-missing 26; fi
if command -v strace >/dev/null 2>&1; then STRACE=$(command -v strace); echo A90WSTA124_STRACE_PRESENT=1; else fail strace-missing 27; fi
/bin/printf '1\\n' > "$ENABLE"
/bin/chmod 0600 "$ENABLE"
[ -s "$ENABLE" ] && echo A90WSTA124_PUBLIC_ENABLE_STAGED=1 || fail enable-stage 28
if [ -x /sbin/ip ]; then /sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /usr/sbin/ip ]; then /usr/sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /bin/busybox ]; then /bin/busybox ip link set lo up >/dev/null 2>&1 || true; fi
if [ -s "$SMOKE_PIDFILE" ]; then /bin/kill "$(/bin/cat "$SMOKE_PIDFILE")" 2>/dev/null || true; fi
/usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' 2>/dev/null || true
/usr/bin/pkill -f '[c]loudflared tunnel' 2>/dev/null || true
/bin/rm -f "$PIDFILE" "$LOG" "$URLFILE" "$SMOKE_PIDFILE" "$SMOKE_LOG" "$TRACE" "$SYSCALLS" "$SOCKET_INODES"
: > "$TRACE"
/bin/chmod 0666 "$TRACE"
"$LAUNCHER" dpublic-smoke-httpd "$SMOKE" 127.0.0.1 8080 >"$SMOKE_LOG" 2>&1 &
SMOKE_LAUNCH_PID=$!
SMOKE_PID="$SMOKE_LAUNCH_PID"
for _i in 1 2 3 4 5 6 7 8 9 10; do
  if /bin/kill -0 "$SMOKE_PID" 2>/dev/null; then
    if /bin/grep -qi ':1F90 .* 0A ' /proc/net/tcp 2>/dev/null; then break; fi
  else
    SMOKE_PID=""
    break
  fi
  /bin/sleep 1
done
if [ -n "$SMOKE_PID" ] && /bin/kill -0 "$SMOKE_PID" 2>/dev/null; then
  echo "$SMOKE_PID" > "$SMOKE_PIDFILE"
  echo A90WSTA124_SMOKE_PID_FOUND=1
  echo A90WSTA124_SMOKE_PID_SOURCE=launch-pid
else
  /bin/cat "$SMOKE_LOG" || true
  fail smoke-pid 29
fi
HTTP_OUTPUT=$(/usr/bin/timeout 10s "$HTTP_GET" 127.0.0.1 8080 2>&1)
if /bin/printf '%s\\n' "$HTTP_OUTPUT" | /bin/grep -q 'A90_DPUBLIC_SMOKE_OK'; then echo A90WSTA124_LOOPBACK_GET_OK=1; else echo A90WSTA124_LOOPBACK_GET_OK=0; fail loopback-get 30; fi
"$LAUNCHER" cloudflared-quick-tunnel "$STRACE" -qq -f -s 128 -o "$TRACE" "$CLOUDFLARED" tunnel --no-autoupdate --url "$ORIGIN" --metrics "$METRICS" --loglevel info >"$LOG" 2>&1 &
STRACE_PID=$!
echo "$STRACE_PID" > "$PIDFILE"
echo A90WSTA124_CLOUDFLARED_LAUNCH_STARTED=1
CLOUDFLARED_PID=""
URL_OBSERVED=0
for _i in $(/usr/bin/seq 1 {int(runtime_wait_sec)}); do
  CLOUDFLARED_PID=$(/bin/pidof cloudflared 2>/dev/null | /usr/bin/awk '{{print $1; exit}}')
  if [ -n "$CLOUDFLARED_PID" ]; then
    url=$(/bin/grep -Eo "https://[A-Za-z0-9-]+\\.$TRY_DOMAIN" "$LOG" 2>/dev/null | /bin/grep -v "^https://api\\.$TRY_DOMAIN$" | /usr/bin/tail -1)
    if [ -n "$url" ]; then
      /usr/bin/printf '%s\\n' "$url" > "$URLFILE"
      /bin/chmod 0600 "$URLFILE"
      URL_OBSERVED=1
      break
    fi
  fi
  if ! /bin/kill -0 "$STRACE_PID" 2>/dev/null; then break; fi
  /bin/sleep 1
done
if [ -n "$CLOUDFLARED_PID" ]; then echo A90WSTA124_CLOUDFLARED_PID_FOUND=1; else /usr/bin/tail -n 20 "$LOG" | /bin/sed 's/https:\\/\\/[^ ]*/[redacted-url]/g' || true; fail cloudflared-pid 31; fi
if [ "$URL_OBSERVED" = "1" ]; then echo A90WSTA124_URL_ARTIFACT_PRIVATE=1; else /usr/bin/tail -n 20 "$LOG" | /bin/sed 's/https:\\/\\/[^ ]*/[redacted-url]/g' || true; fail tunnel-url 32; fi
/usr/bin/awk '/^Uid:/{{print "A90WSTA124_CLOUDFLARED_UID=" $2}}' "/proc/$CLOUDFLARED_PID/status"
/usr/bin/awk '/^Gid:/{{print "A90WSTA124_CLOUDFLARED_GID=" $2}}' "/proc/$CLOUDFLARED_PID/status"
/usr/bin/awk '/^NoNewPrivs:/{{print "A90WSTA124_CLOUDFLARED_NO_NEW_PRIVS=" $2}}' "/proc/$CLOUDFLARED_PID/status"
/usr/bin/awk '/^CapEff:/{{print "A90WSTA124_CLOUDFLARED_CAP_EFF=" $2}}' "/proc/$CLOUDFLARED_PID/status"
CMD=$(/usr/bin/tr '\\000' ' ' < "/proc/$CLOUDFLARED_PID/cmdline")
case "$CMD" in *"cloudflared"*"tunnel"* ) echo A90WSTA124_COMMAND_HAS_TUNNEL=1;; *) fail command-tunnel 33;; esac
case "$CMD" in *"--no-autoupdate"* ) echo A90WSTA124_COMMAND_NO_AUTOUPDATE=1;; *) fail command-autoupdate 34;; esac
case "$CMD" in *"--url $ORIGIN"* ) echo A90WSTA124_COMMAND_ORIGIN=1;; *) fail command-origin 35;; esac
case "$CMD" in *"--metrics $METRICS"* ) echo A90WSTA124_COMMAND_METRICS=1;; *) fail command-metrics 36;; esac
/bin/rm -f "$RUN_DIR/socket-posture"
: > "$SOCKET_INODES"
for fd in /proc/$CLOUDFLARED_PID/fd/*; do
  target=$(/usr/bin/readlink "$fd" 2>/dev/null || true)
  case "$target" in socket:\\[*\\]) /bin/printf '%s\\n' "$target" | /usr/bin/sed 's/socket:\\[//;s/\\]//' >> "$SOCKET_INODES";; esac
done
LISTEN_NONLOOP=0
LISTEN_LOOP=0
ESTABLISHED_OUTBOUND=0
for table in /proc/net/tcp /proc/net/tcp6; do
  [ -r "$table" ] || continue
  /usr/bin/tail -n +2 "$table" | while read sl local remote st tx rx tr tm retr uid timeout inode rest; do
    if /bin/grep -qx "$inode" "$SOCKET_INODES" 2>/dev/null; then
      local_addr=${{local%:*}}
      remote_addr=${{remote%:*}}
      if [ "$st" = "0A" ]; then
        case "$local_addr" in
          0100007F|00000000000000000000000001000000|00000000000000000000000000000001) echo loop-listen >> "$RUN_DIR/socket-posture";;
          *) echo nonloop-listen >> "$RUN_DIR/socket-posture";;
        esac
      fi
      if [ "$st" = "01" ]; then
        case "$remote_addr" in
          00000000|00000000000000000000000000000000) :;;
          *) echo established-outbound >> "$RUN_DIR/socket-posture";;
        esac
      fi
    fi
  done
done
if [ -f "$RUN_DIR/socket-posture" ]; then
  LISTEN_NONLOOP=$(/bin/grep -c '^nonloop-listen$' "$RUN_DIR/socket-posture" 2>/dev/null || true)
  LISTEN_LOOP=$(/bin/grep -c '^loop-listen$' "$RUN_DIR/socket-posture" 2>/dev/null || true)
  ESTABLISHED_OUTBOUND=$(/bin/grep -c '^established-outbound$' "$RUN_DIR/socket-posture" 2>/dev/null || true)
fi
echo A90WSTA124_CLOUDFLARED_LISTEN_NONLOOPBACK=$LISTEN_NONLOOP
echo A90WSTA124_CLOUDFLARED_LISTEN_LOOPBACK=$LISTEN_LOOP
if [ "$ESTABLISHED_OUTBOUND" -gt 0 ]; then echo A90WSTA124_CLOUDFLARED_ESTABLISHED_OUTBOUND=1; else echo A90WSTA124_CLOUDFLARED_ESTABLISHED_OUTBOUND=0; fail outbound-socket 37; fi
if [ "$LISTEN_NONLOOP" = "0" ]; then echo A90WSTA124_CLOUDFLARED_OUTBOUND_ONLY=1; else echo A90WSTA124_CLOUDFLARED_OUTBOUND_ONLY=0; fail nonloop-listener 38; fi
/bin/kill "$CLOUDFLARED_PID" 2>/dev/null || true
/bin/sleep 1
if /bin/kill -0 "$STRACE_PID" 2>/dev/null; then /bin/kill "$STRACE_PID" 2>/dev/null || true; fi
/bin/sleep 1
if /bin/kill -0 "$STRACE_PID" 2>/dev/null; then /bin/kill -9 "$STRACE_PID" 2>/dev/null || true; fi
wait "$STRACE_PID" >/dev/null 2>&1 || true
/bin/kill "$SMOKE_PID" 2>/dev/null || true
/bin/kill "$SMOKE_LAUNCH_PID" 2>/dev/null || true
[ -s "$TRACE" ] && echo A90WSTA124_TRACE_FILE_NONEMPTY=1 || fail trace-empty 39
/usr/bin/awk '{{ line=$0; sub(/^[0-9]+ +/, "", line); if (match(line, /^[A-Za-z0-9_]+\\(/)) {{ name=substr(line, 1, index(line, "(")-1); seen[name]=1 }} }} END {{ for (name in seen) print name }}' "$TRACE" | /usr/bin/sort > "$SYSCALLS"
[ -s "$SYSCALLS" ] && echo A90WSTA124_SYSCALL_PROFILE_NONEMPTY=1 || fail syscalls-empty 40
COUNT=$(/usr/bin/wc -l < "$SYSCALLS" | /usr/bin/awk '{{print $1}}')
echo A90WSTA124_SYSCALL_COUNT=$COUNT
for name in execve socket connect; do
  if /bin/grep -qx "$name" "$SYSCALLS"; then echo "A90WSTA124_SYSCALL_HAS_${{name}}=1"; else fail "syscall-$name" 41; fi
done
echo A90WSTA124_SYSCALL_LIST_BEGIN
/bin/cat "$SYSCALLS"
echo A90WSTA124_SYSCALL_LIST_END
cleanup_proc
trap - EXIT
echo A90WSTA124_RUNTIME_DONE
""".strip()


def syscall_names_from_stdout(stdout: str) -> list[str]:
    inside = False
    names: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == "A90WSTA124_SYSCALL_LIST_BEGIN":
            inside = True
            continue
        if line == "A90WSTA124_SYSCALL_LIST_END":
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def parse_runtime_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    syscalls = syscall_names_from_stdout(stdout)
    syscall_set = set(syscalls)
    return {
        "runtime_begin": "A90WSTA124_RUNTIME_BEGIN" in stdout,
        "runtime_done": "A90WSTA124_RUNTIME_DONE" in stdout,
        "proc_mounted": "A90WSTA124_PROC_MOUNTED=1" in stdout,
        "proc_unmounted": "A90WSTA124_PROC_UNMOUNTED=1" in stdout,
        "public_enable_initial_absent": "A90WSTA124_PUBLIC_ENABLE_INITIAL_ABSENT=1" in stdout,
        "public_enable_staged": "A90WSTA124_PUBLIC_ENABLE_STAGED=1" in stdout,
        "launcher_present": "A90WSTA124_LAUNCHER_PRESENT=1" in stdout,
        "cloudflared_present": "A90WSTA124_CLOUDFLARED_PRESENT=1" in stdout,
        "smoke_present": "A90WSTA124_SMOKE_PRESENT=1" in stdout,
        "http_get_present": "A90WSTA124_HTTP_GET_PRESENT=1" in stdout,
        "setpriv_present": "A90WSTA124_SETPRIV_PRESENT=1" in stdout,
        "strace_present": "A90WSTA124_STRACE_PRESENT=1" in stdout,
        "smoke_pid_found": "A90WSTA124_SMOKE_PID_FOUND=1" in stdout,
        "loopback_get_ok": "A90WSTA124_LOOPBACK_GET_OK=1" in stdout,
        "cloudflared_launch_started": "A90WSTA124_CLOUDFLARED_LAUNCH_STARTED=1" in stdout,
        "cloudflared_pid_found": "A90WSTA124_CLOUDFLARED_PID_FOUND=1" in stdout,
        "url_artifact_private": "A90WSTA124_URL_ARTIFACT_PRIVATE=1" in stdout,
        "uid_3902": "A90WSTA124_CLOUDFLARED_UID=3902" in stdout,
        "gid_3902": "A90WSTA124_CLOUDFLARED_GID=3902" in stdout,
        "no_new_privs": "A90WSTA124_CLOUDFLARED_NO_NEW_PRIVS=1" in stdout,
        "cap_eff_zero": "A90WSTA124_CLOUDFLARED_CAP_EFF=0000000000000000" in stdout,
        "command_has_tunnel": "A90WSTA124_COMMAND_HAS_TUNNEL=1" in stdout,
        "command_no_autoupdate": "A90WSTA124_COMMAND_NO_AUTOUPDATE=1" in stdout,
        "command_origin": "A90WSTA124_COMMAND_ORIGIN=1" in stdout,
        "command_metrics": "A90WSTA124_COMMAND_METRICS=1" in stdout,
        "established_outbound": "A90WSTA124_CLOUDFLARED_ESTABLISHED_OUTBOUND=1" in stdout,
        "outbound_only": "A90WSTA124_CLOUDFLARED_OUTBOUND_ONLY=1" in stdout,
        "trace_file_nonempty": "A90WSTA124_TRACE_FILE_NONEMPTY=1" in stdout,
        "syscall_profile_nonempty": "A90WSTA124_SYSCALL_PROFILE_NONEMPTY=1" in stdout,
        "core_syscalls_observed": all(name in syscall_set for name in CORE_SYSCALLS),
        "syscall_names": syscalls,
        "syscall_count": len(syscalls),
        "secret_values_logged": 0,
    }


def run_runtime_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    script_stage = wsta110.write_remote_bytes(
        args,
        run_dir,
        REMOTE_RUNTIME_SCRIPT,
        (cloudflared_runtime_probe_script(args.runtime_wait_sec) + "\n").encode("utf-8"),
        mode="0700",
        timeout=args.ssh_timeout,
    )
    if not script_stage.get("staged"):
        record = {
            "script_stage": script_stage,
            "returncode": script_stage.get("returncode"),
            "elapsed_sec": script_stage.get("elapsed_sec"),
            "stdout": script_stage.get("stdout", ""),
            "stderr": script_stage.get("stderr", ""),
            "timed_out": False,
            "stage_failed": True,
        }
        record["parsed"] = parse_runtime_probe(record)
        return record
    command = [
        *wsta42.ssh_command(args, run_dir),
        f"set -eu; {shlex.quote(REMOTE_RUNTIME_SCRIPT)}",
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.runtime_timeout,
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
            "stdout": wsta114.decode_subprocess_stream(exc.stdout),
            "stderr": wsta114.decode_subprocess_stream(exc.stderr),
            "timed_out": True,
            "timeout_sec": args.runtime_timeout,
        }
    record["script_stage"] = script_stage
    record["parsed"] = parse_runtime_probe(record)
    return record


def ensure_runtime_resolver(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    script = f"""
set -eu
MNT={shlex.quote(args.mountpoint)}
SRC=/cache/a90-wifi/resolv.conf
DST="$MNT/etc/resolv.conf"
usable_count() {{
  path=$1
  if [ ! -s "$path" ]; then echo 0; return; fi
  /bin/busybox awk '
    $1 == "nameserver" {{
      v=$2
      if (v !~ /^(127\\.|0\\.|169\\.254\\.|::1$|::$|fe80:)/) c++
    }}
    END {{ print c + 0 }}
  ' "$path"
}}
COUNT=0
COPIED=0
READY=0
SOURCE=missing
if [ -s "$SRC" ] && [ "$(usable_count "$SRC")" -gt 0 ]; then
  COUNT=$(usable_count "$SRC")
  /bin/busybox cp "$SRC" "$DST"
  /bin/busybox chmod 644 "$DST"
  COPIED=1
  SOURCE=native-dhcp
  READY=1
elif [ -s "$DST" ] && [ "$(usable_count "$DST")" -gt 0 ]; then
  COUNT=$(usable_count "$DST")
  /bin/busybox chmod 644 "$DST"
  SOURCE=chroot-existing
  READY=1
elif [ -s "$DST" ]; then
  COUNT=$(usable_count "$DST")
  SOURCE=chroot-existing-unusable
else
  SOURCE=missing
fi
echo A90WSTA124_RESOLVER_SYNC ready=$READY copied=$COPIED source=$SOURCE nameserver_count=$COUNT
""".strip()
    record = wsta19.bridge_shell(args, script, timeout=args.timeout, allow_error=True)
    text = str(record.get("text") or "")
    record["copied"] = "copied=1" in text
    record["ready"] = "ready=1" in text
    source_match = re.search(r"source=([A-Za-z0-9_.:-]+)", text)
    record["source"] = source_match.group(1) if source_match else "-"
    match = re.search(r"nameserver_count=([0-9]+)", text)
    record["nameserver_count"] = int(match.group(1)) if match else 0
    if resolver_ready(record):
        record["host_fallback_attempted"] = False
        return record

    resolver = wsta42.select_host_resolver(args)
    record["host_fallback_attempted"] = bool(resolver.get("nameserver_count"))
    record["host_fallback_source_path"] = resolver.get("path", "-")
    record["host_fallback_checked_count"] = resolver.get("checked_count", 0)
    record["host_fallback_source_nameserver_count"] = resolver.get("nameserver_count", 0)
    if not resolver.get("nameserver_count"):
        return record
    stage = wsta42.stage_host_resolver(args, run_dir, resolver)
    record["host_fallback_stage"] = stage
    if stage.get("staged"):
        record["ready"] = True
        record["copied"] = False
        record["source"] = "host-resolver"
        record["nameserver_count"] = int(stage.get("nameserver_count") or 0)
    return record


def resolver_ready(record: dict[str, Any]) -> bool:
    return bool(record.get("ready") and int(record.get("nameserver_count") or 0) > 0)


def egress_route_preflight(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    script = """
set -eu
TARGET=$(/usr/bin/awk '$1 == "nameserver" { print $2; exit }' /etc/resolv.conf 2>/dev/null || true)
TARGET_PRESENT=0
ROUTE_OK=0
if [ -n "$TARGET" ]; then
  TARGET_PRESENT=1
  if [ -x /sbin/ip ] && /sbin/ip route get "$TARGET" >/dev/null 2>&1; then
    ROUTE_OK=1
  elif [ -x /usr/sbin/ip ] && /usr/sbin/ip route get "$TARGET" >/dev/null 2>&1; then
    ROUTE_OK=1
  elif [ -x /bin/busybox ] && /bin/busybox ip route get "$TARGET" >/dev/null 2>&1; then
    ROUTE_OK=1
  fi
fi
echo A90WSTA124_EGRESS_ROUTE target_present=$TARGET_PRESENT route_ok=$ROUTE_OK target_redacted=1
""".strip()
    record = wsta42.ssh_exec(args, run_dir, script, timeout=args.ssh_timeout)
    stdout = str(record.get("stdout") or "")
    record["target_present"] = "target_present=1" in stdout
    record["route_ok"] = "route_ok=1" in stdout
    record["target_redacted"] = "target_redacted=1" in stdout
    record["ready"] = bool(record.get("returncode") == 0 and record["target_present"] and record["route_ok"])
    return record


def fetch_private_url(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(
        args,
        run_dir,
        f"set -eu; /usr/bin/test -f {shlex.quote(REMOTE_URL_FILE)}; /bin/cat {shlex.quote(REMOTE_URL_FILE)}",
        timeout=args.ssh_timeout,
    )
    url = str(record.get("stdout") or "").strip()
    ok = bool(re.fullmatch(rf"https://[A-Za-z0-9-]+\.{re.escape(TRY_DOMAIN)}", url))
    private_path = run_dir / "wsta124-cloudflared-public-url.txt"
    if ok:
        private_path.write_text(url + "\n", encoding="utf-8")
        private_path.chmod(0o600)
    return {
        "returncode": record.get("returncode"),
        "url_artifact_saved": ok,
        "url_len": len(url) if ok else 0,
        "private_path": rel(private_path) if ok else "-",
        "stdout_redacted": True,
        "stderr_present": bool(str(record.get("stderr") or "").strip()),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def fetch_trace_artifacts(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    raw = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_RAW,
        run_dir / "wsta124_cloudflared.strace",
        timeout=args.ssh_timeout,
    )
    syscalls = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_SYSCALLS,
        run_dir / "wsta124_cloudflared.syscalls",
        timeout=args.ssh_timeout,
    )
    return {
        "raw_trace": raw,
        "syscall_list": syscalls,
        "all_saved": bool(raw.get("saved") and syscalls.get("saved")),
        "private_artifact": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def cleanup_cloudflared_runtime(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    script = f"""
set +e
echo A90WSTA124_RUNTIME_CLEANUP_BEGIN
if [ -s {shlex.quote(REMOTE_CLOUDFLARED_PID)} ]; then
  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_CLOUDFLARED_PID)})" 2>/dev/null || true
fi
/usr/bin/pkill -f '[c]loudflared tunnel' 2>/dev/null || true
if [ -s {shlex.quote(REMOTE_SMOKE_PID)} ]; then
  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_SMOKE_PID)})" 2>/dev/null || true
fi
/usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' 2>/dev/null || true
/bin/rm -f {shlex.quote(REMOTE_CLOUDFLARED_PID)} {shlex.quote(REMOTE_CLOUDFLARED_LOG)} {shlex.quote(REMOTE_URL_FILE)}
/bin/rm -f {shlex.quote(REMOTE_SMOKE_PID)} {shlex.quote(REMOTE_SMOKE_LOG)} {shlex.quote(REMOTE_ENABLE)}
/bin/rm -rf {shlex.quote(REMOTE_TRACE_DIR)}
if /bin/pidof cloudflared >/dev/null 2>&1; then echo A90WSTA124_CLOUDFLARED_ABSENT=0; else echo A90WSTA124_CLOUDFLARED_ABSENT=1; fi
if /usr/bin/pgrep -f '[a]90-dpublic-smoke-httpd' >/dev/null 2>&1; then echo A90WSTA124_SMOKE_ABSENT=0; else echo A90WSTA124_SMOKE_ABSENT=1; fi
if [ -e {shlex.quote(REMOTE_ENABLE)} ]; then echo A90WSTA124_ENABLE_ABSENT=0; else echo A90WSTA124_ENABLE_ABSENT=1; fi
if [ -e {shlex.quote(REMOTE_URL_FILE)} ]; then echo A90WSTA124_URL_FILE_ABSENT=0; else echo A90WSTA124_URL_FILE_ABSENT=1; fi
echo A90WSTA124_RUNTIME_CLEANUP_DONE
""".strip()
    record = wsta42.ssh_exec(args, run_dir, script, timeout=args.cleanup_timeout)
    stdout = str(record.get("stdout") or "")
    record["cleaned"] = bool(
        record.get("returncode") == 0
        and "A90WSTA124_RUNTIME_CLEANUP_DONE" in stdout
        and "A90WSTA124_CLOUDFLARED_ABSENT=1" in stdout
        and "A90WSTA124_SMOKE_ABSENT=1" in stdout
        and "A90WSTA124_ENABLE_ABSENT=1" in stdout
        and "A90WSTA124_URL_FILE_ABSENT=1" in stdout
    )
    return record


def runtime_profile(parsed: dict[str, Any],
                    trace_artifacts: dict[str, Any] | None = None,
                    url_artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta124-cloudflared-runtime-profile-v1",
        "service": wsta122.SERVICE,
        "scope": "cloudflared-quick-tunnel-runtime",
        "launcher": wsta110.REMOTE_SERVICE_LAUNCHER,
        "command_shape": "a90-service-launch cloudflared-quick-tunnel cloudflared tunnel --no-autoupdate --url loopback-origin --metrics loopback-ephemeral",
        "user": wsta122.USER,
        "uid": 3902,
        "gid": 3902,
        "uid_gid_proven": bool(parsed.get("uid_3902") and parsed.get("gid_3902")),
        "no_new_privs": bool(parsed.get("no_new_privs")),
        "cap_eff_zero": bool(parsed.get("cap_eff_zero")),
        "command_shape_proven": bool(
            parsed.get("command_has_tunnel")
            and parsed.get("command_no_autoupdate")
            and parsed.get("command_origin")
            and parsed.get("command_metrics")
        ),
        "outbound_only": bool(parsed.get("outbound_only") and parsed.get("established_outbound")),
        "private_url_artifact": bool(
            parsed.get("url_artifact_private")
            and (url_artifact or {}).get("url_artifact_saved")
        ),
        "core_syscalls": list(CORE_SYSCALLS),
        "core_syscalls_observed": bool(parsed.get("core_syscalls_observed")),
        "syscall_count": int(parsed.get("syscall_count") or 0),
        "syscall_names": list(parsed.get("syscall_names") or []),
        "trace_artifacts": trace_artifacts or {},
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta124-blocked-explicit-live-gate"),
        ("local_image_present", "wsta124-blocked-local-image-missing"),
        ("cloudflared_binary_present", "wsta124-blocked-cloudflared-binary-missing"),
        ("dpublic_helpers_built", "wsta124-blocked-dpublic-helper-build"),
        ("baseline_selftest_fail_zero", "wsta124-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta124-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta124-blocked-remote-image"),
        ("chroot_mount_ready", "wsta124-blocked-chroot-mount"),
        ("dropbear_started", "wsta124-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta124-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta124-blocked-service-hardening-stage"),
        ("dpublic_binaries_staged", "wsta124-blocked-dpublic-binary-stage"),
        ("default_route_present", "wsta124-blocked-default-route-missing"),
        ("resolver_ready", "wsta124-blocked-resolver-sync"),
        ("egress_route_ready", "wsta124-blocked-egress-route"),
        ("packet_filter_preflight_pass", "wsta124-blocked-packet-filter-preflight"),
        ("packet_filter_apply_pass", "wsta124-blocked-packet-filter-apply"),
        ("runtime_probe_completed", "wsta124-blocked-runtime-probe"),
        ("public_enable_initial_absent", "wsta124-blocked-public-enable-preexisting"),
        ("public_enable_staged", "wsta124-blocked-public-enable-stage"),
        ("cloudflared_launched", "wsta124-blocked-cloudflared-launch"),
        ("cloudflared_uid_gid_pass", "wsta124-blocked-cloudflared-uid-gid"),
        ("cloudflared_no_new_privs_pass", "wsta124-blocked-cloudflared-no-new-privs"),
        ("cloudflared_cap_eff_zero_pass", "wsta124-blocked-cloudflared-cap-eff"),
        ("cloudflared_command_shape_pass", "wsta124-blocked-cloudflared-command-shape"),
        ("cloudflared_outbound_only_pass", "wsta124-blocked-cloudflared-outbound-only"),
        ("private_url_artifact_saved", "wsta124-blocked-private-url-artifact"),
        ("trace_file_nonempty", "wsta124-blocked-trace-empty"),
        ("syscall_profile_nonempty", "wsta124-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta124-blocked-core-syscalls-missing"),
        ("trace_artifact_saved", "wsta124-blocked-trace-artifact-save"),
        ("runtime_cleanup_ok", "wsta124-blocked-runtime-cleanup"),
        ("packet_filter_restore_pass", "wsta124-blocked-packet-filter-restore"),
        ("chroot_cleanup_ok", "wsta124-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta124-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta124-cloudflared-runtime-live-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA124 cloudflared runtime live gate",
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
        result["decision"] = "wsta124-blocked-local-image-sha"
        return finish_result(out_path, result)

    result["cloudflared_binary"] = {
        "path": rel(args.cloudflared),
        "present": args.cloudflared.is_file(),
        "sha256": sha256_file(args.cloudflared) if args.cloudflared.is_file() else None,
    }
    result["checks"]["cloudflared_binary_present"] = bool(args.cloudflared.is_file())
    result["dpublic_helper_build"] = wsta42.build_dpublic_helpers(run_dir)
    result["checks"]["dpublic_helpers_built"] = bool(result["dpublic_helper_build"].get("ok"))
    write_json(out_path, result)
    if not (result["checks"]["cloudflared_binary_present"] and result["checks"]["dpublic_helpers_built"]):
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    mounted = False
    packet_filter_applied = False
    runtime_probe_started = False
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
        result["dpublic_binary_stage"] = wsta42.stage_dpublic_binaries(args, run_dir)
        result["checks"]["dpublic_binaries_staged"] = wsta42.stage_binaries_ok(result["dpublic_binary_stage"])
        write_json(out_path, result)
        if not (
            result["checks"]["service_hardening_assets_staged"]
            and result["checks"]["dpublic_binaries_staged"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["native_default_route"] = wsta42.native_default_route(args)
        result["checks"]["default_route_present"] = result["native_default_route"].get("default_route_dev") != "-"
        result["resolver_sync"] = ensure_runtime_resolver(args, run_dir)
        result["checks"]["resolver_ready"] = resolver_ready(result["resolver_sync"])
        result["egress_route_preflight"] = (
            egress_route_preflight(args, run_dir)
            if result["checks"]["resolver_ready"]
            else {"skipped": True, "reason": "resolver-not-ready"}
        )
        result["checks"]["egress_route_ready"] = bool(result["egress_route_preflight"].get("ready"))
        write_json(out_path, result)
        if not (
            result["checks"]["default_route_present"]
            and result["checks"]["resolver_ready"]
            and result["checks"]["egress_route_ready"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["packet_filter_preflight"] = wsta42.run_packet_filter(args, run_dir, "preflight")
        result["checks"]["packet_filter_preflight_pass"] = wsta42.packet_filter_preflight_ok(
            result["packet_filter_preflight"]
        )
        if not result["checks"]["packet_filter_preflight_pass"]:
            result["packet_filter_apply"] = {"skipped": True, "reason": "preflight-failed"}
            result["checks"]["packet_filter_apply_pass"] = False
            write_json(out_path, result)
            result["decision"] = classify(result)
            return finish_result(out_path, result)
        result["packet_filter_apply"] = wsta42.run_packet_filter(args, run_dir, "apply-loopback-default-drop")
        packet_filter_applied = True
        result["checks"]["packet_filter_apply_pass"] = wsta42.packet_filter_apply_ok(result["packet_filter_apply"])
        write_json(out_path, result)
        if not (result["checks"]["packet_filter_preflight_pass"] and result["checks"]["packet_filter_apply_pass"]):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        runtime_probe_started = True
        result["runtime_probe"] = run_runtime_probe(args, run_dir)
        parsed = result["runtime_probe"].get("parsed", {})
        result["checks"].update({
            "runtime_probe_completed": bool(
                result["runtime_probe"].get("returncode") == 0
                and not result["runtime_probe"].get("timed_out")
                and parsed.get("runtime_done")
            ),
            "public_enable_initial_absent": bool(parsed.get("public_enable_initial_absent")),
            "public_enable_staged": bool(parsed.get("public_enable_staged")),
            "cloudflared_launched": bool(parsed.get("cloudflared_launch_started") and parsed.get("cloudflared_pid_found")),
            "cloudflared_uid_gid_pass": bool(parsed.get("uid_3902") and parsed.get("gid_3902")),
            "cloudflared_no_new_privs_pass": bool(parsed.get("no_new_privs")),
            "cloudflared_cap_eff_zero_pass": bool(parsed.get("cap_eff_zero")),
            "cloudflared_command_shape_pass": bool(
                parsed.get("command_has_tunnel")
                and parsed.get("command_no_autoupdate")
                and parsed.get("command_origin")
                and parsed.get("command_metrics")
            ),
            "cloudflared_outbound_only_pass": bool(parsed.get("outbound_only") and parsed.get("established_outbound")),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
        })
        result["private_url_artifact"] = (
            fetch_private_url(args, run_dir)
            if parsed.get("url_artifact_private")
            else {"url_artifact_saved": False, "skipped": True, "reason": "url-not-observed"}
        )
        result["checks"]["private_url_artifact_saved"] = bool(result["private_url_artifact"].get("url_artifact_saved"))
        result["trace_artifacts"] = (
            fetch_trace_artifacts(args, run_dir)
            if parsed.get("trace_file_nonempty") and parsed.get("syscall_profile_nonempty")
            else {"all_saved": False, "skipped": True, "reason": "trace-not-complete"}
        )
        result["checks"]["trace_artifact_saved"] = bool(result["trace_artifacts"].get("all_saved"))
        result["cloudflared_runtime_profile"] = runtime_profile(
            parsed,
            result.get("trace_artifacts"),
            result.get("private_url_artifact"),
        )
        write_json(out_path, result)
    finally:
        if mounted and runtime_probe_started:
            result["runtime_cleanup"] = cleanup_cloudflared_runtime(args, run_dir)
            result["checks"]["runtime_cleanup_ok"] = bool(result["runtime_cleanup"].get("cleaned"))
        else:
            result["runtime_cleanup"] = {"skipped": True, "reason": "runtime-probe-not-started"}
            result["checks"]["runtime_cleanup_ok"] = not runtime_probe_started
        if mounted and packet_filter_applied:
            result["packet_filter_restore"] = wsta42.run_packet_filter(args, run_dir, "restore")
            result["checks"]["packet_filter_restore_pass"] = wsta42.packet_filter_restore_ok(
                result["packet_filter_restore"]
            )
        else:
            result["packet_filter_restore"] = {"skipped": True, "reason": "packet-filter-not-applied"}
            result["checks"]["packet_filter_restore_pass"] = not packet_filter_applied
        if mounted:
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
    parser.add_argument("--runtime-timeout", type=float, default=150.0)
    parser.add_argument("--runtime-wait-sec", type=int, default=75)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--cloudflared-stage-timeout", type=float, default=180.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=d1.EXPECTED_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--cloudflared", type=Path, default=wsta42.dpublic.DEFAULT_CLOUDFLARED)
    parser.add_argument("--host-resolver-conf", type=Path, action="append", default=[])
    parser.add_argument("--execute-cloudflared-runtime-live", action="store_true")
    parser.add_argument("--allow-cloudflared-runtime-live", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--ack-private-url-artifact", action="store_true")
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
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta124-cloudflared-runtime-live-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {"scope": "WSTA124 cloudflared runtime live gate", "run_dir": rel(run_dir)}
        else:
            result = {"scope": "WSTA124 cloudflared runtime live gate", "run_dir": rel(run_dir)}
        result["decision"] = "wsta124-runner-error"
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
