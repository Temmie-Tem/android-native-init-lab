#!/usr/bin/env python3
"""Run WSTA114: smoke service syscall trace profile inside the Debian chroot.

WSTA113 stages opt-in ``strace`` tooling in the private rootfs prep path.
WSTA114 is the bounded live gate for that tooling:

  * mount the known Debian image as the chroot service surface,
  * start temporary key-only dropbear using the existing D2/WSTA110 pattern,
  * stage WSTA109 service hardening assets plus D-public smoke helpers,
  * run ``strace`` around ``a90-service-launch dpublic-smoke-httpd ...``,
  * drive one loopback HTTP GET against the smoke server,
  * save a private raw trace and compact syscall-name profile under the run dir.

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
PASS_DECISION = "wsta114-syscall-trace-smoke-chroot-live-pass"
RESULT_NAME = "wsta114_result.json"
REMOTE_SERVICE_LAUNCHER = wsta110.REMOTE_SERVICE_LAUNCHER
REMOTE_SERVICE_POLICY = wsta110.REMOTE_SERVICE_POLICY
REMOTE_STAGE_MARKER = wsta110.REMOTE_STAGE_MARKER
REMOTE_TRACE_DIR = "/tmp/a90-wsta114-syscall-trace"
REMOTE_TRACE_RAW = REMOTE_TRACE_DIR + "/smoke.strace"
REMOTE_TRACE_SYSCALLS = REMOTE_TRACE_DIR + "/smoke.syscalls"
REMOTE_SMOKE_LOG = REMOTE_TRACE_DIR + "/smoke.log"
CORE_SYSCALLS = ("execve", "socket", "bind", "listen")


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
    if not args.execute_syscall_trace_chroot_live:
        return False, "wsta114-blocked-syscall-trace-chroot-live-required"
    if not args.allow_syscall_trace_live:
        return False, "wsta114-blocked-syscall-trace-live-allow-required"
    if not args.ack_private_trace_artifact:
        return False, "wsta114-blocked-private-trace-artifact-ack-required"
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
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def syscall_trace_marker_stage_script() -> str:
    marker_keys = "|".join(item.split("=", 1)[0] for item in wsta3.SYSCALL_TRACE_STAGE_MARKERS)
    lines = [
        "set -eu",
        "echo A90WSTA114_SYSCALL_TRACE_MARKER_STAGE_BEGIN",
        f"MARKER={shlex.quote(REMOTE_STAGE_MARKER)}",
        "TMP=\"${MARKER}.wsta114-tmp.$$\"",
        "/bin/mkdir -p \"$(/usr/bin/dirname \"$MARKER\")\"",
        f"if [ -f \"$MARKER\" ]; then /bin/grep -v -E '^({marker_keys})=' \"$MARKER\" > \"$TMP\" || true; else : > \"$TMP\"; fi",
    ]
    for marker in wsta3.SYSCALL_TRACE_STAGE_MARKERS:
        lines.append(f"/bin/printf '%s\\n' {shlex.quote(marker)} >> \"$TMP\"")
    lines.extend([
        "/bin/mv -f \"$TMP\" \"$MARKER\"",
        "/bin/chmod 0644 \"$MARKER\"",
        "echo A90WSTA114_SYSCALL_TRACE_MARKER_STAGE_DONE",
    ])
    return "\n".join(lines)


def stage_syscall_trace_markers(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, syscall_trace_marker_stage_script(), timeout=args.ssh_timeout)
    text = str(record.get("stdout") or "")
    record["staged"] = record.get("returncode") == 0 and "A90WSTA114_SYSCALL_TRACE_MARKER_STAGE_DONE" in text
    return record


def trace_probe_script() -> str:
    return f"""
set -eu
echo A90WSTA114_TRACE_BEGIN
RUN_DIR={shlex.quote(REMOTE_TRACE_DIR)}
TRACE={shlex.quote(REMOTE_TRACE_RAW)}
SYSCALLS={shlex.quote(REMOTE_TRACE_SYSCALLS)}
SMOKE_LOG={shlex.quote(REMOTE_SMOKE_LOG)}
LAUNCHER={shlex.quote(REMOTE_SERVICE_LAUNCHER)}
POLICY={shlex.quote(REMOTE_SERVICE_POLICY)}
SMOKE={shlex.quote(wsta42.REMOTE_SMOKE)}
HTTP_GET={shlex.quote(wsta42.REMOTE_HTTP_GET)}
PROC_MOUNTED=0
TRACE_PID=""
cleanup() {{
  set +e
  if [ -n "$TRACE_PID" ]; then /bin/kill "$TRACE_PID" >/dev/null 2>&1 || true; fi
  /usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' >/dev/null 2>&1 || true
  /bin/sleep 1
  /usr/bin/pkill -9 -f '[a]90-dpublic-smoke-httpd' >/dev/null 2>&1 || true
  if [ "$PROC_MOUNTED" = "1" ]; then
    /bin/umount /proc
    echo A90WSTA114_PROC_UNMOUNTED=1
    PROC_MOUNTED=0
  fi
}}
fail() {{
  echo "A90WSTA114_FAIL reason=$1 rc=$2"
  exit "$2"
}}
trap cleanup EXIT INT TERM
/bin/mkdir -p /proc "$RUN_DIR"
/bin/mount -t proc proc /proc
PROC_MOUNTED=1
echo A90WSTA114_PROC_MOUNTED=1
if [ ! -e /etc/a90-dpublic/cloudflared-quick-enable ]; then echo A90WSTA114_PUBLIC_ENABLE_ABSENT=1; else echo A90WSTA114_PUBLIC_ENABLE_ABSENT=0; fail public-enabled 30; fi
[ -x "$LAUNCHER" ] && echo A90WSTA114_LAUNCHER_PRESENT=1 || fail launcher-missing 31
[ -f "$POLICY" ] && echo A90WSTA114_POLICY_PRESENT=1 || fail policy-missing 32
[ -x "$SMOKE" ] && echo A90WSTA114_SMOKE_PRESENT=1 || fail smoke-missing 33
[ -x "$HTTP_GET" ] && echo A90WSTA114_HTTP_GET_PRESENT=1 || fail http-get-missing 34
if command -v setpriv >/dev/null 2>&1; then echo A90WSTA114_SETPRIV_PRESENT=1; else echo A90WSTA114_SETPRIV_PRESENT=0; fail setpriv-missing 35; fi
if command -v strace >/dev/null 2>&1; then STRACE=$(command -v strace); echo A90WSTA114_STRACE_PRESENT=1; else echo A90WSTA114_STRACE_PRESENT=0; fail strace-missing 36; fi
if [ -x /sbin/ip ]; then /sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /usr/sbin/ip ]; then /usr/sbin/ip link set lo up >/dev/null 2>&1 || true; fi
if [ -x /bin/busybox ]; then /bin/busybox ip link set lo up >/dev/null 2>&1 || true; fi
/bin/rm -f "$TRACE" "$SYSCALLS" "$SMOKE_LOG"
"$STRACE" -qq -f -s 96 -o "$TRACE" "$LAUNCHER" dpublic-smoke-httpd "$SMOKE" 127.0.0.1 8080 >"$SMOKE_LOG" 2>&1 &
TRACE_PID=$!
/bin/sleep 1
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then echo A90WSTA114_TRACE_PROCESS_STARTED=1; else [ -s "$SMOKE_LOG" ] && /bin/cat "$SMOKE_LOG"; fail trace-start 37; fi
SMOKE_PID=$(/bin/pidof a90-dpublic-smoke-httpd 2>/dev/null | /usr/bin/awk '{{print $1; exit}}')
if [ -n "$SMOKE_PID" ]; then echo A90WSTA114_SMOKE_PID_FOUND=1; else [ -s "$SMOKE_LOG" ] && /bin/cat "$SMOKE_LOG"; fail smoke-pid 38; fi
/usr/bin/awk '/^NoNewPrivs:/{{print "A90WSTA114_SMOKE_NO_NEW_PRIVS=" $2}}' "/proc/$SMOKE_PID/status"
/usr/bin/awk '/^CapEff:/{{print "A90WSTA114_SMOKE_CAP_EFF=" $2}}' "/proc/$SMOKE_PID/status"
HTTP_OUTPUT=$(/usr/bin/timeout 10s "$HTTP_GET" 127.0.0.1 8080 2>&1)
HTTP_RC=$?
/bin/printf '%s\\n' "$HTTP_OUTPUT"
if /bin/printf '%s\\n' "$HTTP_OUTPUT" | /bin/grep -q 'A90_DPUBLIC_SMOKE_OK'; then
  echo A90WSTA114_LOOPBACK_GET_OK=1
else
  echo A90WSTA114_LOOPBACK_GET_OK=0 rc=$HTTP_RC
  fail loopback-get 39
fi
/bin/kill "$TRACE_PID" >/dev/null 2>&1 || true
/bin/sleep 1
if /bin/kill -0 "$TRACE_PID" >/dev/null 2>&1; then /bin/kill -9 "$TRACE_PID" >/dev/null 2>&1 || true; fi
wait "$TRACE_PID" >/dev/null 2>&1 || true
TRACE_PID=""
if /bin/grep -q 'a90_service_launcher_decision=exec' "$SMOKE_LOG"; then echo A90WSTA114_LAUNCHER_EXEC_LOGGED=1; else /bin/cat "$SMOKE_LOG"; fail launcher-exec 40; fi
[ -s "$TRACE" ] && echo A90WSTA114_TRACE_FILE_NONEMPTY=1 || fail trace-empty 41
/usr/bin/awk '{{ line=$0; sub(/^[0-9]+ +/, "", line); if (match(line, /^[A-Za-z0-9_]+\\(/)) {{ name=substr(line, 1, index(line, "(")-1); seen[name]=1 }} }} END {{ for (name in seen) print name }}' "$TRACE" | /usr/bin/sort > "$SYSCALLS"
[ -s "$SYSCALLS" ] && echo A90WSTA114_SYSCALL_PROFILE_NONEMPTY=1 || fail syscalls-empty 42
COUNT=$(/usr/bin/wc -l < "$SYSCALLS" | /usr/bin/awk '{{print $1}}')
echo A90WSTA114_SYSCALL_COUNT=$COUNT
if /bin/grep -qx execve "$SYSCALLS"; then echo A90WSTA114_SYSCALL_HAS_EXECVE=1; else echo A90WSTA114_SYSCALL_HAS_EXECVE=0; fail syscall-execve 43; fi
if /bin/grep -qx socket "$SYSCALLS"; then echo A90WSTA114_SYSCALL_HAS_SOCKET=1; else echo A90WSTA114_SYSCALL_HAS_SOCKET=0; fail syscall-socket 44; fi
if /bin/grep -qx bind "$SYSCALLS"; then echo A90WSTA114_SYSCALL_HAS_BIND=1; else echo A90WSTA114_SYSCALL_HAS_BIND=0; fail syscall-bind 45; fi
if /bin/grep -qx listen "$SYSCALLS"; then echo A90WSTA114_SYSCALL_HAS_LISTEN=1; else echo A90WSTA114_SYSCALL_HAS_LISTEN=0; fail syscall-listen 46; fi
echo A90WSTA114_SYSCALL_LIST_BEGIN
/bin/cat "$SYSCALLS"
echo A90WSTA114_SYSCALL_LIST_END
cleanup
trap - EXIT
echo A90WSTA114_TRACE_DONE
""".strip()


def syscall_names_from_stdout(stdout: str) -> list[str]:
    inside = False
    names: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == "A90WSTA114_SYSCALL_LIST_BEGIN":
            inside = True
            continue
        if line == "A90WSTA114_SYSCALL_LIST_END":
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def parse_trace_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    syscalls = syscall_names_from_stdout(stdout)
    syscall_set = set(syscalls)
    return {
        "proof_begin": "A90WSTA114_TRACE_BEGIN" in stdout,
        "proof_done": "A90WSTA114_TRACE_DONE" in stdout,
        "proc_mounted": "A90WSTA114_PROC_MOUNTED=1" in stdout,
        "proc_unmounted": "A90WSTA114_PROC_UNMOUNTED=1" in stdout,
        "public_enable_absent": "A90WSTA114_PUBLIC_ENABLE_ABSENT=1" in stdout,
        "launcher_present": "A90WSTA114_LAUNCHER_PRESENT=1" in stdout,
        "policy_present": "A90WSTA114_POLICY_PRESENT=1" in stdout,
        "smoke_present": "A90WSTA114_SMOKE_PRESENT=1" in stdout,
        "http_get_present": "A90WSTA114_HTTP_GET_PRESENT=1" in stdout,
        "setpriv_present": "A90WSTA114_SETPRIV_PRESENT=1" in stdout,
        "strace_present": "A90WSTA114_STRACE_PRESENT=1" in stdout,
        "trace_process_started": "A90WSTA114_TRACE_PROCESS_STARTED=1" in stdout,
        "smoke_pid_found": "A90WSTA114_SMOKE_PID_FOUND=1" in stdout,
        "smoke_no_new_privs": "A90WSTA114_SMOKE_NO_NEW_PRIVS=1" in stdout,
        "smoke_cap_eff_zero": "A90WSTA114_SMOKE_CAP_EFF=0000000000000000" in stdout,
        "loopback_get_ok": "A90WSTA114_LOOPBACK_GET_OK=1" in stdout,
        "launcher_exec_logged": "A90WSTA114_LAUNCHER_EXEC_LOGGED=1" in stdout,
        "trace_file_nonempty": "A90WSTA114_TRACE_FILE_NONEMPTY=1" in stdout,
        "syscall_profile_nonempty": "A90WSTA114_SYSCALL_PROFILE_NONEMPTY=1" in stdout,
        "core_syscalls_observed": all(name in syscall_set for name in CORE_SYSCALLS),
        "syscall_names": syscalls,
        "syscall_count": len(syscalls),
        "secret_values_logged": 0,
    }


def syscall_profile(parsed: dict[str, Any], trace_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta114-syscall-profile-v1",
        "service": "dpublic-smoke-httpd",
        "scope": "smoke-service-only",
        "launcher": REMOTE_SERVICE_LAUNCHER,
        "command_shape": "a90-service-launch dpublic-smoke-httpd a90-dpublic-smoke-httpd 127.0.0.1 8080",
        "public_default_off": bool(parsed.get("public_enable_absent")),
        "loopback_get_ok": bool(parsed.get("loopback_get_ok")),
        "no_new_privs": bool(parsed.get("smoke_no_new_privs")),
        "cap_eff_zero": bool(parsed.get("smoke_cap_eff_zero")),
        "core_syscalls": list(CORE_SYSCALLS),
        "core_syscalls_observed": bool(parsed.get("core_syscalls_observed")),
        "syscall_count": int(parsed.get("syscall_count") or 0),
        "syscall_names": list(parsed.get("syscall_names") or []),
        "trace_artifacts": trace_artifacts or {},
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run_trace_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, trace_probe_script(), timeout=args.trace_timeout)
    record["parsed"] = parse_trace_probe(record)
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
        run_dir / "wsta114_smoke.strace",
        timeout=args.ssh_timeout,
    )
    syscalls = fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_SYSCALLS,
        run_dir / "wsta114_smoke.syscalls",
        timeout=args.ssh_timeout,
    )
    return {
        "raw_trace": raw,
        "syscall_list": syscalls,
        "all_saved": bool(raw.get("saved") and syscalls.get("saved")),
        "private_artifact": True,
        "secret_values_logged": 0,
    }


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta114-blocked-explicit-live-gate"),
        ("local_image_present", "wsta114-blocked-local-image-missing"),
        ("dpublic_helpers_built", "wsta114-blocked-dpublic-helper-build"),
        ("baseline_selftest_fail_zero", "wsta114-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta114-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta114-blocked-remote-image"),
        ("chroot_mount_ready", "wsta114-blocked-chroot-mount"),
        ("dropbear_started", "wsta114-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta114-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta114-blocked-service-hardening-stage"),
        ("dpublic_helpers_staged", "wsta114-blocked-dpublic-helper-stage"),
        ("syscall_trace_marker_staged", "wsta114-blocked-syscall-trace-marker-stage"),
        ("public_default_off", "wsta114-blocked-public-default-off"),
        ("strace_present", "wsta114-blocked-strace-missing"),
        ("smoke_binaries_present", "wsta114-blocked-smoke-binaries-missing"),
        ("trace_started", "wsta114-blocked-trace-start"),
        ("loopback_get_ok", "wsta114-blocked-loopback-get"),
        ("trace_file_nonempty", "wsta114-blocked-trace-empty"),
        ("syscall_profile_nonempty", "wsta114-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta114-blocked-core-syscalls-missing"),
        ("trace_artifact_saved", "wsta114-blocked-trace-artifact-save"),
        ("chroot_cleanup_ok", "wsta114-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta114-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta114-syscall-trace-chroot-profile-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA114 syscall trace smoke chroot profile",
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
        result["decision"] = "wsta114-blocked-local-image-sha"
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
        result["syscall_trace_marker_stage"] = stage_syscall_trace_markers(args, run_dir)
        result["checks"]["syscall_trace_marker_staged"] = bool(result["syscall_trace_marker_stage"].get("staged"))
        write_json(out_path, result)
        if not (
            result["checks"]["service_hardening_assets_staged"]
            and result["checks"]["dpublic_helpers_staged"]
            and result["checks"]["syscall_trace_marker_staged"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["trace_probe"] = run_trace_probe(args, run_dir)
        parsed = result["trace_probe"].get("parsed", {})
        result["trace_artifacts"] = (
            fetch_trace_artifacts(args, run_dir)
            if parsed.get("trace_file_nonempty") and parsed.get("syscall_profile_nonempty")
            else {"all_saved": False, "skipped": True, "reason": "trace-not-complete"}
        )
        result["syscall_profile"] = syscall_profile(parsed, result.get("trace_artifacts"))
        result["checks"].update({
            "public_default_off": bool(parsed.get("public_enable_absent")),
            "strace_present": bool(parsed.get("strace_present")),
            "smoke_binaries_present": bool(parsed.get("smoke_present") and parsed.get("http_get_present")),
            "trace_started": bool(parsed.get("trace_process_started") and parsed.get("smoke_pid_found")),
            "loopback_get_ok": bool(parsed.get("loopback_get_ok")),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
            "trace_artifact_saved": bool(result["trace_artifacts"].get("all_saved")),
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
    parser.add_argument("--trace-timeout", type=float, default=75.0)
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
    parser.add_argument("--execute-syscall-trace-chroot-live", action="store_true")
    parser.add_argument("--allow-syscall-trace-live", action="store_true")
    parser.add_argument("--ack-private-trace-artifact", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta114-syscall-trace-chroot-profile-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA114 syscall trace smoke chroot profile",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA114 syscall trace smoke chroot profile",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta114-runner-error"
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
