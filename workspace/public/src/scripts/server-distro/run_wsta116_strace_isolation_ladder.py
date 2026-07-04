#!/usr/bin/env python3
"""Run WSTA116: isolate the WSTA114 strace timeout inside the Debian chroot.

WSTA115 proved the strace-enabled SD image and WSTA114 setup path, but the full
foreground smoke-service trace timed out before the service-child emitted its
first marker.  WSTA116 keeps the same chroot/dropbear/service-hardening setup
and splits the trace into three bounded probes:

  * ``strace /bin/true`` inside the chroot,
  * ``strace a90-service-launch dpublic-smoke-httpd /bin/true``,
  * background ``strace`` of the smoke service with file polling.

No boot image is built or flashed.  No Wi-Fi association, DHCP, public tunnel,
packet-filter mutation, userdata write, native reboot, or switch-root is
performed.
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


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta116-strace-isolation-ladder-live-pass"
RESULT_NAME = "wsta116_result.json"

REMOTE_ISOLATION_DIR = "/tmp/a90-wsta116-strace-isolation"
REMOTE_DIRECT_TRUE_TRACE = REMOTE_ISOLATION_DIR + "/01-direct-true.strace"
REMOTE_DIRECT_TRUE_SYSCALLS = REMOTE_ISOLATION_DIR + "/01-direct-true.syscalls"
REMOTE_LAUNCHER_TRUE_TRACE = REMOTE_ISOLATION_DIR + "/02-launcher-true.strace"
REMOTE_LAUNCHER_TRUE_SYSCALLS = REMOTE_ISOLATION_DIR + "/02-launcher-true.syscalls"
REMOTE_LAUNCHER_TRUE_LOG = REMOTE_ISOLATION_DIR + "/02-launcher-true.log"
REMOTE_SMOKE_BG_TRACE = REMOTE_ISOLATION_DIR + "/03-smoke-background.strace"
REMOTE_SMOKE_BG_SYSCALLS = REMOTE_ISOLATION_DIR + "/03-smoke-background.syscalls"
REMOTE_SMOKE_BG_LOG = REMOTE_ISOLATION_DIR + "/03-smoke-background.log"
CORE_SYSCALLS = wsta114.CORE_SYSCALLS


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
    if not args.execute_strace_isolation_live:
        return False, "wsta116-blocked-strace-isolation-live-required"
    if not args.allow_strace_isolation_live:
        return False, "wsta116-blocked-strace-isolation-live-allow-required"
    if not args.ack_private_trace_artifact:
        return False, "wsta116-blocked-private-trace-artifact-ack-required"
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
        "syscall_trace_capture": "explicit-live-gated-private-diagnostic-artifact" if gate_ok else False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def isolation_probe_script() -> str:
    launcher = shlex.quote(wsta114.REMOTE_SERVICE_LAUNCHER)
    policy = shlex.quote(wsta114.REMOTE_SERVICE_POLICY)
    smoke = shlex.quote(wsta42.REMOTE_SMOKE)
    http_get = shlex.quote(wsta42.REMOTE_HTTP_GET)
    return f"""
set -eu
echo A90WSTA116_ISOLATION_BEGIN
RUN_DIR={shlex.quote(REMOTE_ISOLATION_DIR)}
DIRECT_TRACE={shlex.quote(REMOTE_DIRECT_TRUE_TRACE)}
DIRECT_SYSCALLS={shlex.quote(REMOTE_DIRECT_TRUE_SYSCALLS)}
LAUNCHER_TRACE={shlex.quote(REMOTE_LAUNCHER_TRUE_TRACE)}
LAUNCHER_SYSCALLS={shlex.quote(REMOTE_LAUNCHER_TRUE_SYSCALLS)}
LAUNCHER_LOG={shlex.quote(REMOTE_LAUNCHER_TRUE_LOG)}
SMOKE_TRACE={shlex.quote(REMOTE_SMOKE_BG_TRACE)}
SMOKE_SYSCALLS={shlex.quote(REMOTE_SMOKE_BG_SYSCALLS)}
SMOKE_LOG={shlex.quote(REMOTE_SMOKE_BG_LOG)}
LAUNCHER={launcher}
POLICY={policy}
SMOKE={smoke}
HTTP_GET={http_get}
PROC_MOUNTED=0
cleanup() {{
  set +e
  if [ "$PROC_MOUNTED" = "1" ]; then
    echo A90WSTA116_PROC_UNMOUNT_DEFERRED=1
    PROC_MOUNTED=0
  fi
}}
make_syscalls() {{
  trace="$1"
  out="$2"
  /bin/sed -n 's/^\\([A-Za-z0-9_][A-Za-z0-9_]*\\)(.*/\\1/p; s/^[0-9][0-9]*  *\\([A-Za-z0-9_][A-Za-z0-9_]*\\)(.*/\\1/p' "$trace" | /usr/bin/sort -u > "$out"
}}
emit_syscall_list() {{
  name="$1"
  file="$2"
  echo "A90WSTA116_${{name}}_SYSCALL_LIST_BEGIN"
  /bin/cat "$file"
  echo "A90WSTA116_${{name}}_SYSCALL_LIST_END"
}}
trap cleanup EXIT INT TERM
/bin/mkdir -p /proc "$RUN_DIR"
/bin/mount -t proc proc /proc
PROC_MOUNTED=1
echo A90WSTA116_PROC_MOUNTED=1
if [ ! -e /etc/a90-dpublic/cloudflared-quick-enable ]; then echo A90WSTA116_PUBLIC_ENABLE_ABSENT=1; else echo A90WSTA116_PUBLIC_ENABLE_ABSENT=0; exit 30; fi
[ -x "$LAUNCHER" ] && echo A90WSTA116_LAUNCHER_PRESENT=1 || exit 31
[ -f "$POLICY" ] && echo A90WSTA116_POLICY_PRESENT=1 || exit 32
[ -x "$SMOKE" ] && echo A90WSTA116_SMOKE_PRESENT=1 || exit 33
[ -x "$HTTP_GET" ] && echo A90WSTA116_HTTP_GET_PRESENT=1 || exit 34
if command -v setpriv >/dev/null 2>&1; then echo A90WSTA116_SETPRIV_PRESENT=1; else echo A90WSTA116_SETPRIV_PRESENT=0; exit 35; fi
if command -v strace >/dev/null 2>&1; then STRACE=$(command -v strace); echo A90WSTA116_STRACE_PRESENT=1; else echo A90WSTA116_STRACE_PRESENT=0; exit 36; fi
if [ -x /sbin/ip ]; then /sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /usr/sbin/ip ]; then /usr/sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /bin/busybox ]; then /bin/busybox ip link set lo up >/dev/null 2>&1 || true; fi
/bin/rm -f "$DIRECT_TRACE" "$DIRECT_SYSCALLS" "$LAUNCHER_TRACE" "$LAUNCHER_SYSCALLS" "$LAUNCHER_LOG" "$SMOKE_TRACE" "$SMOKE_SYSCALLS" "$SMOKE_LOG" "$RUN_DIR/service-child.sh" "$RUN_DIR/smoke-server.log"

set +e
/usr/bin/timeout -k 3s 10s "$STRACE" -qq -f -s 96 -o "$DIRECT_TRACE" /bin/true
DIRECT_RC=$?
set -e
echo A90WSTA116_DIRECT_TRUE_RC=$DIRECT_RC
if [ -s "$DIRECT_TRACE" ]; then
  echo A90WSTA116_DIRECT_TRUE_TRACE_NONEMPTY=1
  make_syscalls "$DIRECT_TRACE" "$DIRECT_SYSCALLS"
  if /bin/grep -qx execve "$DIRECT_SYSCALLS"; then echo A90WSTA116_DIRECT_TRUE_HAS_EXECVE=1; else echo A90WSTA116_DIRECT_TRUE_HAS_EXECVE=0; fi
  emit_syscall_list DIRECT_TRUE "$DIRECT_SYSCALLS"
else
  echo A90WSTA116_DIRECT_TRUE_TRACE_NONEMPTY=0
fi

set +e
/usr/bin/timeout -k 3s 15s "$STRACE" -qq -f -s 96 -o "$LAUNCHER_TRACE" "$LAUNCHER" dpublic-smoke-httpd /bin/true >"$LAUNCHER_LOG" 2>&1
LAUNCHER_RC=$?
set -e
echo A90WSTA116_LAUNCHER_TRUE_RC=$LAUNCHER_RC
/bin/cat "$LAUNCHER_LOG" || true
if /bin/grep -q 'a90_service_launcher_decision=exec' "$LAUNCHER_LOG"; then echo A90WSTA116_LAUNCHER_TRUE_EXEC_LOGGED=1; else echo A90WSTA116_LAUNCHER_TRUE_EXEC_LOGGED=0; fi
if [ -s "$LAUNCHER_TRACE" ]; then
  echo A90WSTA116_LAUNCHER_TRUE_TRACE_NONEMPTY=1
  make_syscalls "$LAUNCHER_TRACE" "$LAUNCHER_SYSCALLS"
  if /bin/grep -qx execve "$LAUNCHER_SYSCALLS"; then echo A90WSTA116_LAUNCHER_TRUE_HAS_EXECVE=1; else echo A90WSTA116_LAUNCHER_TRUE_HAS_EXECVE=0; fi
  emit_syscall_list LAUNCHER_TRUE "$LAUNCHER_SYSCALLS"
else
  echo A90WSTA116_LAUNCHER_TRUE_TRACE_NONEMPTY=0
fi

/bin/cat > "$RUN_DIR/service-child.sh" <<'A90WSTA116_CHILD'
#!/bin/sh
set -eu
RUN_DIR=/tmp/a90-wsta116-strace-isolation
SMOKE=/usr/local/bin/a90-dpublic-smoke-httpd
HTTP_GET=/usr/local/bin/a90-dpublic-http-get
SMOKE_SERVER_LOG="$RUN_DIR/smoke-server.log"
echo A90WSTA116_SERVICE_CHILD_BEGIN
NNP=$(/bin/grep '^NoNewPrivs:' /proc/self/status | /bin/sed 's/.*:[[:space:]]*//')
CAP=$(/bin/grep '^CapEff:' /proc/self/status | /bin/sed 's/.*:[[:space:]]*//')
echo A90WSTA116_SMOKE_NO_NEW_PRIVS=$NNP
echo A90WSTA116_SMOKE_CAP_EFF=$CAP
"$SMOKE" 127.0.0.1 8080 >"$SMOKE_SERVER_LOG" 2>&1 &
SMOKE_PID=$!
/bin/sleep 1
if /bin/kill -0 "$SMOKE_PID" >/dev/null 2>&1; then echo A90WSTA116_SMOKE_PID_FOUND=1; else [ -s "$SMOKE_SERVER_LOG" ] && /bin/cat "$SMOKE_SERVER_LOG"; exit 38; fi
HTTP_OUTPUT=$(/usr/bin/timeout 10s "$HTTP_GET" 127.0.0.1 8080 2>&1)
HTTP_RC=$?
/bin/printf '%s\\n' "$HTTP_OUTPUT"
if /bin/printf '%s\\n' "$HTTP_OUTPUT" | /bin/grep -q 'A90_DPUBLIC_SMOKE_OK'; then
  echo A90WSTA116_LOOPBACK_GET_OK=1
else
  echo A90WSTA116_LOOPBACK_GET_OK=0 rc=$HTTP_RC
  /bin/kill "$SMOKE_PID" >/dev/null 2>&1 || true
  wait "$SMOKE_PID" >/dev/null 2>&1 || true
  exit 39
fi
/bin/kill "$SMOKE_PID" >/dev/null 2>&1 || true
wait "$SMOKE_PID" >/dev/null 2>&1 || true
echo A90WSTA116_SERVICE_CHILD_DONE
A90WSTA116_CHILD
/bin/chmod 0755 "$RUN_DIR/service-child.sh"
: > "$RUN_DIR/smoke-server.log"
/bin/chmod 0666 "$RUN_DIR/smoke-server.log"
set +e
"$STRACE" -qq -f -s 96 -o "$SMOKE_TRACE" "$LAUNCHER" dpublic-smoke-httpd /bin/sh "$RUN_DIR/service-child.sh" >"$SMOKE_LOG" 2>&1 &
TRACE_PID=$!
set -e
echo A90WSTA116_SMOKE_BG_SPAWNED=1
echo A90WSTA116_SMOKE_BG_TRACE_PID=$TRACE_PID
SMOKE_DONE=0
for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  if [ -s "$SMOKE_LOG" ] && /bin/grep -q 'A90WSTA116_SERVICE_CHILD_DONE' "$SMOKE_LOG"; then SMOKE_DONE=1; break; fi
  if ! /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then break; fi
  /bin/sleep 1
done
echo A90WSTA116_SMOKE_BG_DONE=$SMOKE_DONE
set +e
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then
  /bin/kill "$TRACE_PID" >/dev/null 2>&1 || true
  /bin/sleep 1
fi
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then /bin/kill -9 "$TRACE_PID" >/dev/null 2>&1 || true; fi
wait "$TRACE_PID" >/dev/null 2>&1
SMOKE_TRACE_WAIT_RC=$?
set -e
echo A90WSTA116_SMOKE_BG_WAIT_RC=$SMOKE_TRACE_WAIT_RC
/bin/cat "$SMOKE_LOG" || true
if /bin/grep -q 'A90WSTA116_LOOPBACK_GET_OK=1' "$SMOKE_LOG"; then echo A90WSTA116_SMOKE_BG_LOOPBACK_GET_OK=1; else echo A90WSTA116_SMOKE_BG_LOOPBACK_GET_OK=0; fi
if /bin/grep -q 'a90_service_launcher_decision=exec' "$SMOKE_LOG"; then echo A90WSTA116_SMOKE_BG_EXEC_LOGGED=1; else echo A90WSTA116_SMOKE_BG_EXEC_LOGGED=0; fi
if [ -s "$SMOKE_TRACE" ]; then
  echo A90WSTA116_SMOKE_BG_TRACE_NONEMPTY=1
  make_syscalls "$SMOKE_TRACE" "$SMOKE_SYSCALLS"
  for name in execve socket bind listen; do
    if /bin/grep -qx "$name" "$SMOKE_SYSCALLS"; then echo "A90WSTA116_SMOKE_BG_HAS_${{name}}=1"; else echo "A90WSTA116_SMOKE_BG_HAS_${{name}}=0"; fi
  done
  emit_syscall_list SMOKE_BG "$SMOKE_SYSCALLS"
else
  echo A90WSTA116_SMOKE_BG_TRACE_NONEMPTY=0
fi
echo A90WSTA116_PRE_CLEANUP=1
cleanup
trap - EXIT
echo A90WSTA116_ISOLATION_DONE
""".strip()


def syscall_names_from_stdout(stdout: str, step: str) -> list[str]:
    inside = False
    names: set[str] = set()
    begin = f"A90WSTA116_{step}_SYSCALL_LIST_BEGIN"
    end = f"A90WSTA116_{step}_SYSCALL_LIST_END"
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == begin:
            inside = True
            continue
        if line == end:
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def parse_isolation_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    direct_syscalls = syscall_names_from_stdout(stdout, "DIRECT_TRUE")
    launcher_syscalls = syscall_names_from_stdout(stdout, "LAUNCHER_TRUE")
    smoke_syscalls = syscall_names_from_stdout(stdout, "SMOKE_BG")
    smoke_set = set(smoke_syscalls)
    return {
        "proof_begin": "A90WSTA116_ISOLATION_BEGIN" in stdout,
        "proof_done": "A90WSTA116_ISOLATION_DONE" in stdout,
        "proc_mounted": "A90WSTA116_PROC_MOUNTED=1" in stdout,
        "proc_unmounted": "A90WSTA116_PROC_UNMOUNTED=1" in stdout,
        "proc_unmount_deferred": "A90WSTA116_PROC_UNMOUNT_DEFERRED=1" in stdout,
        "public_enable_absent": "A90WSTA116_PUBLIC_ENABLE_ABSENT=1" in stdout,
        "launcher_present": "A90WSTA116_LAUNCHER_PRESENT=1" in stdout,
        "policy_present": "A90WSTA116_POLICY_PRESENT=1" in stdout,
        "smoke_present": "A90WSTA116_SMOKE_PRESENT=1" in stdout,
        "http_get_present": "A90WSTA116_HTTP_GET_PRESENT=1" in stdout,
        "setpriv_present": "A90WSTA116_SETPRIV_PRESENT=1" in stdout,
        "strace_present": "A90WSTA116_STRACE_PRESENT=1" in stdout,
        "direct_true_rc_zero": "A90WSTA116_DIRECT_TRUE_RC=0" in stdout,
        "direct_true_trace_nonempty": "A90WSTA116_DIRECT_TRUE_TRACE_NONEMPTY=1" in stdout,
        "direct_true_has_execve": "A90WSTA116_DIRECT_TRUE_HAS_EXECVE=1" in stdout,
        "launcher_true_rc_zero": "A90WSTA116_LAUNCHER_TRUE_RC=0" in stdout,
        "launcher_true_exec_logged": "A90WSTA116_LAUNCHER_TRUE_EXEC_LOGGED=1" in stdout,
        "launcher_true_trace_nonempty": "A90WSTA116_LAUNCHER_TRUE_TRACE_NONEMPTY=1" in stdout,
        "launcher_true_has_execve": "A90WSTA116_LAUNCHER_TRUE_HAS_EXECVE=1" in stdout,
        "smoke_bg_spawned": "A90WSTA116_SMOKE_BG_SPAWNED=1" in stdout,
        "smoke_bg_done": "A90WSTA116_SMOKE_BG_DONE=1" in stdout,
        "smoke_bg_loopback_get_ok": "A90WSTA116_SMOKE_BG_LOOPBACK_GET_OK=1" in stdout,
        "smoke_bg_exec_logged": "A90WSTA116_SMOKE_BG_EXEC_LOGGED=1" in stdout,
        "smoke_bg_trace_nonempty": "A90WSTA116_SMOKE_BG_TRACE_NONEMPTY=1" in stdout,
        "smoke_no_new_privs": "A90WSTA116_SMOKE_NO_NEW_PRIVS=1" in stdout,
        "smoke_cap_eff_zero": "A90WSTA116_SMOKE_CAP_EFF=0000000000000000" in stdout,
        "smoke_core_syscalls_observed": all(name in smoke_set for name in CORE_SYSCALLS),
        "direct_true_syscalls": direct_syscalls,
        "launcher_true_syscalls": launcher_syscalls,
        "smoke_bg_syscalls": smoke_syscalls,
        "secret_values_logged": 0,
    }


def decode_subprocess_stream(value: str | bytes | None) -> str:
    return wsta114.decode_subprocess_stream(value)


def run_isolation_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = [*wsta42.ssh_command(args, run_dir), isolation_probe_script()]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.isolation_timeout,
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
            "timeout_sec": args.isolation_timeout,
        }
    record["parsed"] = parse_isolation_probe(record)
    return record


def fetch_isolation_artifacts(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    specs = (
        ("direct_true_trace", REMOTE_DIRECT_TRUE_TRACE, "wsta116_01_direct_true.strace"),
        ("direct_true_syscalls", REMOTE_DIRECT_TRUE_SYSCALLS, "wsta116_01_direct_true.syscalls"),
        ("launcher_true_trace", REMOTE_LAUNCHER_TRUE_TRACE, "wsta116_02_launcher_true.strace"),
        ("launcher_true_syscalls", REMOTE_LAUNCHER_TRUE_SYSCALLS, "wsta116_02_launcher_true.syscalls"),
        ("launcher_true_log", REMOTE_LAUNCHER_TRUE_LOG, "wsta116_02_launcher_true.log"),
        ("smoke_bg_trace", REMOTE_SMOKE_BG_TRACE, "wsta116_03_smoke_background.strace"),
        ("smoke_bg_syscalls", REMOTE_SMOKE_BG_SYSCALLS, "wsta116_03_smoke_background.syscalls"),
        ("smoke_bg_log", REMOTE_SMOKE_BG_LOG, "wsta116_03_smoke_background.log"),
    )
    records = {
        key: wsta114.fetch_remote_file(args, run_dir, remote, run_dir / local, timeout=args.ssh_timeout)
        for key, remote, local in specs
    }
    required = (
        "direct_true_trace",
        "direct_true_syscalls",
        "launcher_true_trace",
        "launcher_true_syscalls",
        "smoke_bg_trace",
        "smoke_bg_syscalls",
    )
    return {
        **records,
        "all_required_saved": all(records[key].get("saved") for key in required),
        "private_artifact": True,
        "secret_values_logged": 0,
    }


def isolation_summary(parsed: dict[str, Any], artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta116-strace-isolation-v1",
        "scope": "smoke-service-strace-timeout-isolation",
        "direct_true": {
            "rc_zero": bool(parsed.get("direct_true_rc_zero")),
            "trace_nonempty": bool(parsed.get("direct_true_trace_nonempty")),
            "has_execve": bool(parsed.get("direct_true_has_execve")),
            "syscall_count": len(parsed.get("direct_true_syscalls") or []),
        },
        "launcher_true": {
            "rc_zero": bool(parsed.get("launcher_true_rc_zero")),
            "exec_logged": bool(parsed.get("launcher_true_exec_logged")),
            "trace_nonempty": bool(parsed.get("launcher_true_trace_nonempty")),
            "has_execve": bool(parsed.get("launcher_true_has_execve")),
            "syscall_count": len(parsed.get("launcher_true_syscalls") or []),
        },
        "smoke_background": {
            "spawned": bool(parsed.get("smoke_bg_spawned")),
            "done": bool(parsed.get("smoke_bg_done")),
            "loopback_get_ok": bool(parsed.get("smoke_bg_loopback_get_ok")),
            "exec_logged": bool(parsed.get("smoke_bg_exec_logged")),
            "trace_nonempty": bool(parsed.get("smoke_bg_trace_nonempty")),
            "no_new_privs": bool(parsed.get("smoke_no_new_privs")),
            "cap_eff_zero": bool(parsed.get("smoke_cap_eff_zero")),
            "core_syscalls_observed": bool(parsed.get("smoke_core_syscalls_observed")),
            "syscall_count": len(parsed.get("smoke_bg_syscalls") or []),
        },
        "trace_artifacts": artifacts or {},
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta116-blocked-explicit-live-gate"),
        ("local_image_present", "wsta116-blocked-local-image-missing"),
        ("dpublic_helpers_built", "wsta116-blocked-dpublic-helper-build"),
        ("baseline_selftest_fail_zero", "wsta116-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta116-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta116-blocked-remote-image"),
        ("chroot_mount_ready", "wsta116-blocked-chroot-mount"),
        ("dropbear_started", "wsta116-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta116-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta116-blocked-service-hardening-stage"),
        ("dpublic_helpers_staged", "wsta116-blocked-dpublic-helper-stage"),
        ("syscall_trace_marker_staged", "wsta116-blocked-syscall-trace-marker-stage"),
        ("isolation_probe_completed", "wsta116-blocked-isolation-timeout"),
        ("public_default_off", "wsta116-blocked-public-default-off"),
        ("strace_present", "wsta116-blocked-strace-missing"),
        ("smoke_binaries_present", "wsta116-blocked-smoke-binaries-missing"),
        ("direct_true_pass", "wsta116-blocked-direct-true-strace"),
        ("launcher_true_pass", "wsta116-blocked-launcher-true-strace"),
        ("smoke_background_pass", "wsta116-blocked-smoke-background-strace"),
        ("trace_artifacts_saved", "wsta116-blocked-trace-artifact-save"),
        ("chroot_cleanup_ok", "wsta116-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta116-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta116-strace-isolation-ladder-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA116 strace isolation ladder",
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
        result["decision"] = "wsta116-blocked-local-image-sha"
        return finish_result(out_path, result)

    result["dpublic_helper_build"] = wsta42.build_dpublic_helpers(run_dir)
    result["checks"]["dpublic_helpers_built"] = bool(result["dpublic_helper_build"].get("ok"))
    write_json(out_path, result)
    if not result["checks"]["dpublic_helpers_built"]:
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
        result["dpublic_helper_stage"] = wsta94.stage_loopback_binaries(args, run_dir)
        result["checks"]["dpublic_helpers_staged"] = wsta94.stage_ok(result["dpublic_helper_stage"])
        result["syscall_trace_marker_stage"] = wsta114.stage_syscall_trace_markers(args, run_dir)
        result["checks"]["syscall_trace_marker_staged"] = bool(result["syscall_trace_marker_stage"].get("staged"))
        write_json(out_path, result)
        if not (
            result["checks"]["service_hardening_assets_staged"]
            and result["checks"]["dpublic_helpers_staged"]
            and result["checks"]["syscall_trace_marker_staged"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["isolation_probe"] = run_isolation_probe(args, run_dir)
        parsed = result["isolation_probe"].get("parsed", {})
        result["trace_artifacts"] = fetch_isolation_artifacts(args, run_dir)
        result["isolation_summary"] = isolation_summary(parsed, result.get("trace_artifacts"))
        result["checks"].update({
            "isolation_probe_completed": bool(
                result["isolation_probe"].get("returncode") == 0
                and not result["isolation_probe"].get("timed_out")
            ),
            "public_default_off": bool(parsed.get("public_enable_absent")),
            "strace_present": bool(parsed.get("strace_present")),
            "smoke_binaries_present": bool(parsed.get("smoke_present") and parsed.get("http_get_present")),
            "direct_true_pass": bool(
                parsed.get("direct_true_rc_zero")
                and parsed.get("direct_true_trace_nonempty")
                and parsed.get("direct_true_has_execve")
            ),
            "launcher_true_pass": bool(
                parsed.get("launcher_true_rc_zero")
                and parsed.get("launcher_true_exec_logged")
                and parsed.get("launcher_true_trace_nonempty")
                and parsed.get("launcher_true_has_execve")
            ),
            "smoke_background_pass": bool(
                parsed.get("smoke_bg_spawned")
                and parsed.get("smoke_bg_done")
                and parsed.get("smoke_bg_loopback_get_ok")
                and parsed.get("smoke_bg_exec_logged")
                and parsed.get("smoke_bg_trace_nonempty")
                and parsed.get("smoke_no_new_privs")
                and parsed.get("smoke_cap_eff_zero")
                and parsed.get("smoke_core_syscalls_observed")
            ),
            "trace_artifacts_saved": bool(result["trace_artifacts"].get("all_required_saved")),
        })
        write_json(out_path, result)
    finally:
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
    parser.add_argument("--isolation-timeout", type=float, default=75.0)
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
    parser.add_argument("--execute-strace-isolation-live", action="store_true")
    parser.add_argument("--allow-strace-isolation-live", action="store_true")
    parser.add_argument("--ack-private-trace-artifact", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta116-strace-isolation-ladder-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA116 strace isolation ladder",
                    "run_dir": rel(run_dir),
                    "checks": {},
                }
        else:
            result = {
                "scope": "WSTA116 strace isolation ladder",
                "started_utc": ts,
                "run_dir": rel(run_dir),
                "checks": {},
            }
        result.update({
            "decision": "wsta116-runner-error",
            "error": str(exc),
            "ended_utc": utc_stamp(),
        })
        write_json(out_path, result)
        print(json.dumps({
            "scope": result.get("scope"),
            "decision": result.get("decision"),
            "error": result.get("error"),
            "run_dir": result.get("run_dir"),
            "ended_utc": result.get("ended_utc"),
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "scope": result.get("scope"),
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "ended_utc": result.get("ended_utc"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main_with_args())
