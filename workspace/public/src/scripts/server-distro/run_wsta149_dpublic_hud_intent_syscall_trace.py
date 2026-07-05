#!/usr/bin/env python3
"""Run WSTA149: syscall trace the split D-public HUD intent producer.

This is the post-WSTA148 optional HUD syscall profile gate.  The traced process
is the Debian-side, non-root ``a90-dpublic-hud-intent`` producer launched via
``a90-service-launch dpublic-hud``.  Native init remains the KMS presenter owner.

No boot image is built or flashed.  No native reboot, Wi-Fi association, DHCP,
public tunnel, packet-filter mutation, userdata write, switch-root, DRM open, or
KMS operation is performed.
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
import run_wsta114_syscall_trace_chroot_profile as wsta114  # noqa: E402
import run_wsta132_dpublic_hud_split_prototype as wsta132  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta149-dpublic-hud-intent-syscall-trace-live-pass"
RESULT_NAME = "wsta149_result.json"
WSTA115_STRACE_IMAGE = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta115-strace-rootfs-20260705T0309KST"
    / "debian-bookworm-arm64-wsta115-strace.img"
)
WSTA115_STRACE_IMAGE_SHA256 = "40a01268ae6f77d1548dd71f9ef30f4d31fdce437d90a6edcc7721f0e26dd159"
REMOTE_SERVICE_LAUNCHER = wsta110.REMOTE_SERVICE_LAUNCHER
REMOTE_SERVICE_POLICY = wsta110.REMOTE_SERVICE_POLICY
REMOTE_STAGE_MARKER = wsta110.REMOTE_STAGE_MARKER
REMOTE_HUD_INTENT = "/" + str(wsta3.TARGET_HUD_INTENT)
REMOTE_TRACE_DIR = "/tmp/a90-wsta149-dpublic-hud-intent-trace"
REMOTE_TRACE_RAW = REMOTE_TRACE_DIR + "/hud-intent.strace"
REMOTE_TRACE_SYSCALLS = REMOTE_TRACE_DIR + "/hud-intent.syscalls"
REMOTE_HUD_LOG = REMOTE_TRACE_DIR + "/hud-intent.log"
REMOTE_INTENT_JSON = "/run/a90-dpublic/hud-intent.json"
INTENT_SEQUENCE = 14901
CORE_SYSCALLS = ("execve", "openat", "write", "fsync", "close")
ATOMIC_RENAME_SYSCALLS = ("rename", "renameat", "renameat2")
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
    if not args.execute_hud_intent_syscall_trace_live:
        return False, "wsta149-blocked-hud-intent-syscall-trace-live-required"
    if not args.allow_hud_intent_trace_live:
        return False, "wsta149-blocked-hud-intent-trace-live-allow-required"
    if not args.ack_private_trace_artifact:
        return False, "wsta149-blocked-private-trace-artifact-ack-required"
    if not args.ack_runtime_cleanup:
        return False, "wsta149-blocked-runtime-cleanup-ack-required"
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
        "drm_open": False,
        "kms_setcrtc": False,
        "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only" if gate_ok else False,
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "runtime_cleanup_required": gate_ok,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def build_hud_intent_binary(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    output = run_dir / "a90-dpublic-hud-intent"
    record = wsta132.compile_c(args.arm64_cc, wsta132.INTENT_SOURCE, output, timeout=args.build_timeout)
    record["source"] = rel(wsta132.INTENT_SOURCE)
    record["output"] = rel(output)
    if output.is_file():
        record["output_sha256"] = sha256_file(output)
        record["output_size_bytes"] = output.stat().st_size
    record["secret_values_logged"] = 0
    return record


def stage_hud_intent_binary(args: argparse.Namespace, run_dir: Path, local_binary: Path) -> dict[str, Any]:
    if not local_binary.is_file():
        return {
            "staged": False,
            "reason": "hud-intent-binary-missing",
            "local_path": rel(local_binary),
            "remote_path": REMOTE_HUD_INTENT,
            "secret_values_logged": 0,
        }
    record = wsta42.ssh_write_file(
        args,
        run_dir,
        local_binary,
        REMOTE_HUD_INTENT,
        timeout=args.ssh_timeout,
    )
    record["service"] = "dpublic-hud"
    record["secret_values_logged"] = 0
    return record


def hud_split_marker_stage_script() -> str:
    marker_keys = "|".join(item.split("=", 1)[0] for item in wsta3.HUD_SPLIT_STAGE_MARKERS)
    lines = [
        "set -eu",
        "echo A90WSTA149_HUD_SPLIT_MARKER_STAGE_BEGIN",
        f"MARKER={shlex.quote(REMOTE_STAGE_MARKER)}",
        "TMP=\"${MARKER}.wsta149-tmp.$$\"",
        "/bin/mkdir -p \"$(/usr/bin/dirname \"$MARKER\")\"",
        f"if [ -f \"$MARKER\" ]; then /bin/grep -v -E '^({marker_keys})=' \"$MARKER\" > \"$TMP\" || true; else : > \"$TMP\"; fi",
    ]
    for marker in wsta3.HUD_SPLIT_STAGE_MARKERS:
        lines.append(f"/bin/printf '%s\\n' {shlex.quote(marker)} >> \"$TMP\"")
    lines.extend([
        "/bin/mv -f \"$TMP\" \"$MARKER\"",
        "/bin/chmod 0644 \"$MARKER\"",
        "echo A90WSTA149_HUD_SPLIT_MARKER_STAGE_DONE",
    ])
    return "\n".join(lines)


def stage_hud_split_markers(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, hud_split_marker_stage_script(), timeout=args.ssh_timeout)
    text = str(record.get("stdout") or "")
    record["staged"] = record.get("returncode") == 0 and "A90WSTA149_HUD_SPLIT_MARKER_STAGE_DONE" in text
    return record


def syscall_names_from_stdout(stdout: str) -> list[str]:
    inside = False
    names: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line == "A90WSTA149_SYSCALL_LIST_BEGIN":
            inside = True
            continue
        if line == "A90WSTA149_SYSCALL_LIST_END":
            inside = False
            continue
        if inside and re.fullmatch(r"[A-Za-z0-9_]+", line):
            names.add(line)
    return sorted(names)


def trace_probe_script() -> str:
    network_pattern = "|".join(NETWORK_SYSCALLS)
    rename_pattern = "|".join(ATOMIC_RENAME_SYSCALLS)
    return f"""
set -eu
echo A90WSTA149_TRACE_BEGIN
RUN_DIR={shlex.quote(REMOTE_TRACE_DIR)}
TRACE={shlex.quote(REMOTE_TRACE_RAW)}
SYSCALLS={shlex.quote(REMOTE_TRACE_SYSCALLS)}
HUD_LOG={shlex.quote(REMOTE_HUD_LOG)}
LAUNCHER={shlex.quote(REMOTE_SERVICE_LAUNCHER)}
POLICY={shlex.quote(REMOTE_SERVICE_POLICY)}
HUD_INTENT={shlex.quote(REMOTE_HUD_INTENT)}
INTENT={shlex.quote(REMOTE_INTENT_JSON)}
PROC_MOUNTED=0
cleanup() {{
  set +e
  if [ "$PROC_MOUNTED" = "1" ]; then
    if /bin/umount /proc >/dev/null 2>&1; then
      echo A90WSTA149_PROC_UNMOUNTED=1
    else
      echo A90WSTA149_PROC_UNMOUNT_DEFERRED=1
    fi
    PROC_MOUNTED=0
  fi
}}
fail() {{
  echo "A90WSTA149_FAIL reason=$1 rc=$2"
  exit "$2"
}}
trap cleanup EXIT INT TERM
/bin/mkdir -p /proc "$RUN_DIR" /run/a90-dpublic
if [ ! -r /proc/self/status ]; then
  /bin/mount -t proc proc /proc
  PROC_MOUNTED=1
  echo A90WSTA149_PROC_MOUNTED=1
else
  echo A90WSTA149_PROC_ALREADY_MOUNTED=1
fi
if [ ! -e /etc/a90-dpublic/cloudflared-quick-enable ]; then echo A90WSTA149_PUBLIC_ENABLE_ABSENT=1; else echo A90WSTA149_PUBLIC_ENABLE_ABSENT=0; fail public-enabled 30; fi
[ -x "$LAUNCHER" ] && echo A90WSTA149_LAUNCHER_PRESENT=1 || fail launcher-missing 31
[ -f "$POLICY" ] && echo A90WSTA149_POLICY_PRESENT=1 || fail policy-missing 32
[ -x "$HUD_INTENT" ] && echo A90WSTA149_HUD_INTENT_PRESENT=1 || fail hud-intent-missing 33
if command -v setpriv >/dev/null 2>&1; then echo A90WSTA149_SETPRIV_PRESENT=1; else echo A90WSTA149_SETPRIV_PRESENT=0; fail setpriv-missing 34; fi
if command -v strace >/dev/null 2>&1; then STRACE=$(command -v strace); echo A90WSTA149_STRACE_PRESENT=1; else echo A90WSTA149_STRACE_PRESENT=0; fail strace-missing 35; fi
/bin/chown a90hud:a90hud "$RUN_DIR" /run/a90-dpublic
/bin/chmod 0700 "$RUN_DIR"
/bin/chmod 1770 /run/a90-dpublic
/bin/rm -f "$TRACE" "$SYSCALLS" "$HUD_LOG" "$INTENT" "$INTENT".tmp.*
: > "$TRACE"
/bin/chown a90hud:a90hud "$TRACE"
/bin/chmod 0600 "$TRACE"
echo A90WSTA149_RUN_DIR_READY=1
"$LAUNCHER" dpublic-hud /bin/sh -c 'echo A90WSTA149_IDENTITY_UID=$(id -u); echo A90WSTA149_IDENTITY_GID=$(id -g); awk "/^NoNewPrivs:/{{print \\"A90WSTA149_IDENTITY_NO_NEW_PRIVS=\\" \\$2}}" /proc/self/status; awk "/^CapEff:/{{print \\"A90WSTA149_IDENTITY_CAP_EFF=\\" \\$2}}" /proc/self/status'
set +e
"$LAUNCHER" dpublic-hud "$STRACE" -qq -f -s 96 -o "$TRACE" "$HUD_INTENT" --output "$INTENT" --sequence {INTENT_SEQUENCE} >"$HUD_LOG" 2>&1
TRACE_RC=$?
set -e
echo A90WSTA149_TRACE_PROCESS_RC=$TRACE_RC
/bin/cat "$HUD_LOG" || true
[ "$TRACE_RC" = "0" ] || fail trace-run 36
if /bin/grep -q 'a90_service_launcher_decision=exec' "$HUD_LOG"; then echo A90WSTA149_LAUNCHER_EXEC_LOGGED=1; else fail launcher-exec 37; fi
if /bin/grep -q 'a90_service_launcher_service=dpublic-hud' "$HUD_LOG"; then echo A90WSTA149_LAUNCHER_SERVICE_LOGGED=1; else fail launcher-service 38; fi
if /bin/grep -q 'A90WSTA132_INTENT_WRITTEN=1' "$HUD_LOG"; then echo A90WSTA149_INTENT_WRITTEN=1; else fail intent-written 39; fi
[ -s "$INTENT" ] && echo A90WSTA149_INTENT_FILE_NONEMPTY=1 || fail intent-empty 40
if /bin/grep -q '"schema":"a90-dpublic-hud-intent-v1"' "$INTENT"; then echo A90WSTA149_INTENT_SCHEMA_OK=1; else fail intent-schema 41; fi
if /bin/grep -q '"sequence":{INTENT_SEQUENCE}' "$INTENT"; then echo A90WSTA149_INTENT_SEQUENCE_OK=1; else fail intent-sequence 42; fi
if /bin/grep -q '"public_state":"PUBLIC_OFF"' "$INTENT"; then echo A90WSTA149_INTENT_PUBLIC_OFF=1; else fail intent-public 43; fi
if /bin/grep -E -q 'public_url|secret|token|password' "$INTENT"; then echo A90WSTA149_INTENT_FORBIDDEN_FIELDS_ABSENT=0; fail intent-forbidden 44; else echo A90WSTA149_INTENT_FORBIDDEN_FIELDS_ABSENT=1; fi
[ -s "$TRACE" ] && echo A90WSTA149_TRACE_FILE_NONEMPTY=1 || fail trace-empty 45
/usr/bin/awk '{{ line=$0; sub(/^[0-9]+ +/, "", line); if (match(line, /^[A-Za-z0-9_]+\\(/)) {{ name=substr(line, 1, index(line, "(")-1); seen[name]=1 }} }} END {{ for (name in seen) print name }}' "$TRACE" | /usr/bin/sort > "$SYSCALLS"
[ -s "$SYSCALLS" ] && echo A90WSTA149_SYSCALL_PROFILE_NONEMPTY=1 || fail syscalls-empty 46
COUNT=$(/usr/bin/wc -l < "$SYSCALLS" | /usr/bin/awk '{{print $1}}')
echo A90WSTA149_SYSCALL_COUNT=$COUNT
for name in {' '.join(CORE_SYSCALLS)}; do
  if /bin/grep -qx "$name" "$SYSCALLS"; then echo "A90WSTA149_SYSCALL_HAS_$name=1"; else echo "A90WSTA149_SYSCALL_HAS_$name=0"; fail "syscall-$name" 47; fi
done
if /bin/grep -E -qx '{rename_pattern}' "$SYSCALLS"; then echo A90WSTA149_SYSCALL_HAS_ATOMIC_RENAME=1; else echo A90WSTA149_SYSCALL_HAS_ATOMIC_RENAME=0; fail syscall-rename 48; fi
if /bin/grep -E -qx '{network_pattern}' "$SYSCALLS"; then echo A90WSTA149_SYSCALL_NETWORK_ABSENT=0; fail network-syscall 49; else echo A90WSTA149_SYSCALL_NETWORK_ABSENT=1; fi
if /bin/grep -qx ioctl "$SYSCALLS"; then echo A90WSTA149_SYSCALL_IOCTL_ABSENT=0; fail ioctl-syscall 50; else echo A90WSTA149_SYSCALL_IOCTL_ABSENT=1; fi
if /bin/grep -q '/dev/dri\\|DRM_IOCTL' "$TRACE"; then echo A90WSTA149_DRM_TRACE_ABSENT=0; fail drm-trace 51; else echo A90WSTA149_DRM_TRACE_ABSENT=1; fi
echo A90WSTA149_SYSCALL_LIST_BEGIN
/bin/cat "$SYSCALLS"
echo A90WSTA149_SYSCALL_LIST_END
cleanup
trap - EXIT
echo A90WSTA149_TRACE_DONE
""".strip()


def parse_trace_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    syscalls = syscall_names_from_stdout(stdout)
    syscall_set = set(syscalls)
    return {
        "proof_begin": "A90WSTA149_TRACE_BEGIN" in stdout,
        "proof_done": "A90WSTA149_TRACE_DONE" in stdout,
        "proc_mounted": "A90WSTA149_PROC_MOUNTED=1" in stdout,
        "proc_already_mounted": "A90WSTA149_PROC_ALREADY_MOUNTED=1" in stdout,
        "proc_unmounted": "A90WSTA149_PROC_UNMOUNTED=1" in stdout,
        "proc_unmount_deferred": "A90WSTA149_PROC_UNMOUNT_DEFERRED=1" in stdout,
        "public_enable_absent": "A90WSTA149_PUBLIC_ENABLE_ABSENT=1" in stdout,
        "launcher_present": "A90WSTA149_LAUNCHER_PRESENT=1" in stdout,
        "policy_present": "A90WSTA149_POLICY_PRESENT=1" in stdout,
        "hud_intent_present": "A90WSTA149_HUD_INTENT_PRESENT=1" in stdout,
        "setpriv_present": "A90WSTA149_SETPRIV_PRESENT=1" in stdout,
        "strace_present": "A90WSTA149_STRACE_PRESENT=1" in stdout,
        "run_dir_ready": "A90WSTA149_RUN_DIR_READY=1" in stdout,
        "identity_uid": "A90WSTA149_IDENTITY_UID=3904" in stdout,
        "identity_gid": "A90WSTA149_IDENTITY_GID=3904" in stdout,
        "identity_no_new_privs": "A90WSTA149_IDENTITY_NO_NEW_PRIVS=1" in stdout,
        "identity_cap_eff_zero": "A90WSTA149_IDENTITY_CAP_EFF=0000000000000000" in stdout,
        "trace_process_ok": "A90WSTA149_TRACE_PROCESS_RC=0" in stdout,
        "launcher_exec_logged": "A90WSTA149_LAUNCHER_EXEC_LOGGED=1" in stdout,
        "launcher_service_logged": "A90WSTA149_LAUNCHER_SERVICE_LOGGED=1" in stdout,
        "intent_written": "A90WSTA149_INTENT_WRITTEN=1" in stdout,
        "intent_file_nonempty": "A90WSTA149_INTENT_FILE_NONEMPTY=1" in stdout,
        "intent_schema_ok": "A90WSTA149_INTENT_SCHEMA_OK=1" in stdout,
        "intent_sequence_ok": "A90WSTA149_INTENT_SEQUENCE_OK=1" in stdout,
        "intent_public_off": "A90WSTA149_INTENT_PUBLIC_OFF=1" in stdout,
        "intent_forbidden_fields_absent": "A90WSTA149_INTENT_FORBIDDEN_FIELDS_ABSENT=1" in stdout,
        "trace_file_nonempty": "A90WSTA149_TRACE_FILE_NONEMPTY=1" in stdout,
        "syscall_profile_nonempty": "A90WSTA149_SYSCALL_PROFILE_NONEMPTY=1" in stdout,
        "core_syscalls_observed": all(name in syscall_set for name in CORE_SYSCALLS),
        "atomic_rename_observed": any(name in syscall_set for name in ATOMIC_RENAME_SYSCALLS),
        "network_syscalls_absent": "A90WSTA149_SYSCALL_NETWORK_ABSENT=1" in stdout
        and not any(name in syscall_set for name in NETWORK_SYSCALLS),
        "ioctl_syscall_absent": "A90WSTA149_SYSCALL_IOCTL_ABSENT=1" in stdout and "ioctl" not in syscall_set,
        "drm_trace_absent": "A90WSTA149_DRM_TRACE_ABSENT=1" in stdout,
        "syscall_names": syscalls,
        "syscall_count": len(syscalls),
        "secret_values_logged": 0,
    }


def syscall_profile(parsed: dict[str, Any], trace_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "a90-wsta149-dpublic-hud-intent-syscall-profile-v1",
        "service": "dpublic-hud",
        "scope": "hud-intent-producer-only",
        "launcher": REMOTE_SERVICE_LAUNCHER,
        "command_shape": (
            "a90-service-launch dpublic-hud strace -f "
            "a90-dpublic-hud-intent --output /run/a90-dpublic/hud-intent.json"
        ),
        "intent_path": REMOTE_INTENT_JSON,
        "intent_sequence": INTENT_SEQUENCE,
        "native_presenter_owner": True,
        "public_default_off": bool(parsed.get("public_enable_absent") and parsed.get("intent_public_off")),
        "no_new_privs": bool(parsed.get("identity_no_new_privs")),
        "cap_eff_zero": bool(parsed.get("identity_cap_eff_zero")),
        "core_syscalls": list(CORE_SYSCALLS),
        "core_syscalls_observed": bool(parsed.get("core_syscalls_observed")),
        "atomic_rename_observed": bool(parsed.get("atomic_rename_observed")),
        "network_syscalls": list(NETWORK_SYSCALLS),
        "network_syscalls_absent": bool(parsed.get("network_syscalls_absent")),
        "ioctl_syscall_absent": bool(parsed.get("ioctl_syscall_absent")),
        "drm_trace_absent": bool(parsed.get("drm_trace_absent")),
        "syscall_count": int(parsed.get("syscall_count") or 0),
        "syscall_names": list(parsed.get("syscall_names") or []),
        "trace_artifacts": trace_artifacts or {},
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def decode_subprocess_stream(value: str | bytes | None) -> str:
    return wsta114.decode_subprocess_stream(value)


def run_trace_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = [*wsta42.ssh_command(args, run_dir), trace_probe_script()]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.trace_timeout,
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
            "timeout_sec": args.trace_timeout,
        }
    record["parsed"] = parse_trace_probe(record)
    return record


def fetch_trace_artifacts(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    raw = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_RAW,
        run_dir / "wsta149_hud_intent.strace",
        timeout=args.ssh_timeout,
    )
    syscalls = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_TRACE_SYSCALLS,
        run_dir / "wsta149_hud_intent.syscalls",
        timeout=args.ssh_timeout,
    )
    intent = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_INTENT_JSON,
        run_dir / "wsta149_hud_intent.json",
        timeout=args.ssh_timeout,
    )
    log = wsta114.fetch_remote_file(
        args,
        run_dir,
        REMOTE_HUD_LOG,
        run_dir / "wsta149_hud_intent.log",
        timeout=args.ssh_timeout,
    )
    return {
        "raw_trace": raw,
        "syscall_list": syscalls,
        "intent_json": intent,
        "launcher_log": log,
        "all_saved": bool(
            raw.get("saved")
            and syscalls.get("saved")
            and intent.get("saved")
            and log.get("saved")
        ),
        "private_artifact": True,
        "secret_values_logged": 0,
    }


def cleanup_script(mountpoint: str) -> str:
    mnt = shlex.quote(mountpoint)
    return f"""
set +e
echo A90WSTA149_CLEANUP_BEGIN
M={mnt}
/bin/busybox rm -rf "$M{REMOTE_TRACE_DIR}" "$M{REMOTE_INTENT_JSON}" "$M{REMOTE_INTENT_JSON}.tmp."* 2>/dev/null || true
echo A90WSTA149_CLEANUP_DONE
""".strip()


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta149-blocked-explicit-live-gate"),
        ("local_image_present", "wsta149-blocked-local-image-missing"),
        ("local_image_sha_ok", "wsta149-blocked-local-image-sha"),
        ("hud_intent_build_ok", "wsta149-blocked-hud-intent-build"),
        ("baseline_selftest_fail_zero", "wsta149-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta149-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta149-blocked-remote-image"),
        ("chroot_mount_ready", "wsta149-blocked-chroot-mount"),
        ("dropbear_started", "wsta149-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta149-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta149-blocked-service-hardening-stage"),
        ("hud_intent_staged", "wsta149-blocked-hud-intent-stage"),
        ("hud_split_marker_staged", "wsta149-blocked-hud-split-marker-stage"),
        ("trace_probe_completed", "wsta149-blocked-trace-timeout"),
        ("public_default_off", "wsta149-blocked-public-default-off"),
        ("strace_present", "wsta149-blocked-strace-missing"),
        ("hud_intent_present", "wsta149-blocked-hud-intent-missing"),
        ("service_identity_ok", "wsta149-blocked-service-identity"),
        ("launcher_exec_logged", "wsta149-blocked-launcher-exec"),
        ("intent_written", "wsta149-blocked-intent-write"),
        ("intent_schema_ok", "wsta149-blocked-intent-schema"),
        ("trace_file_nonempty", "wsta149-blocked-trace-empty"),
        ("syscall_profile_nonempty", "wsta149-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta149-blocked-core-syscalls-missing"),
        ("atomic_rename_observed", "wsta149-blocked-atomic-rename-missing"),
        ("network_syscalls_absent", "wsta149-blocked-network-syscall-present"),
        ("drm_syscalls_absent", "wsta149-blocked-drm-syscall-present"),
        ("trace_artifact_saved", "wsta149-blocked-trace-artifact-save"),
        ("chroot_cleanup_ok", "wsta149-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta149-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta149-dpublic-hud-intent-syscall-trace-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA149 D-public HUD intent syscall trace",
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

    result["hud_intent_build"] = build_hud_intent_binary(args, run_dir)
    local_hud_intent = run_dir / "a90-dpublic-hud-intent"
    result["checks"]["hud_intent_build_ok"] = bool(result["hud_intent_build"].get("ok") and local_hud_intent.is_file())
    write_json(out_path, result)
    if not result["checks"]["hud_intent_build_ok"]:
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
        result["hud_intent_stage"] = stage_hud_intent_binary(args, run_dir, local_hud_intent)
        result["checks"]["hud_intent_staged"] = bool(result["hud_intent_stage"].get("staged"))
        result["hud_split_marker_stage"] = stage_hud_split_markers(args, run_dir)
        result["checks"]["hud_split_marker_staged"] = bool(result["hud_split_marker_stage"].get("staged"))
        write_json(out_path, result)
        if not (
            result["checks"]["service_hardening_assets_staged"]
            and result["checks"]["hud_intent_staged"]
            and result["checks"]["hud_split_marker_staged"]
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
            "trace_probe_completed": bool(
                result["trace_probe"].get("returncode") == 0
                and not result["trace_probe"].get("timed_out")
            ),
            "public_default_off": bool(parsed.get("public_enable_absent") and parsed.get("intent_public_off")),
            "strace_present": bool(parsed.get("strace_present")),
            "hud_intent_present": bool(parsed.get("hud_intent_present")),
            "service_identity_ok": bool(
                parsed.get("identity_uid")
                and parsed.get("identity_gid")
                and parsed.get("identity_no_new_privs")
                and parsed.get("identity_cap_eff_zero")
            ),
            "launcher_exec_logged": bool(parsed.get("launcher_exec_logged") and parsed.get("launcher_service_logged")),
            "intent_written": bool(parsed.get("intent_written") and parsed.get("intent_file_nonempty")),
            "intent_schema_ok": bool(
                parsed.get("intent_schema_ok")
                and parsed.get("intent_sequence_ok")
                and parsed.get("intent_forbidden_fields_absent")
            ),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
            "atomic_rename_observed": bool(parsed.get("atomic_rename_observed")),
            "network_syscalls_absent": bool(parsed.get("network_syscalls_absent")),
            "drm_syscalls_absent": bool(parsed.get("ioctl_syscall_absent") and parsed.get("drm_trace_absent")),
            "trace_artifact_saved": bool(result["trace_artifacts"].get("all_saved")),
        })
        write_json(out_path, result)
    finally:
        if mounted:
            result["hud_intent_probe_cleanup"] = wsta19.bridge_shell(
                args,
                cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
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
    parser.add_argument("--build-timeout", type=float, default=30.0)
    parser.add_argument("--arm64-cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=WSTA115_STRACE_IMAGE)
    parser.add_argument("--local-image-sha256", default=WSTA115_STRACE_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--execute-hud-intent-syscall-trace-live", action="store_true")
    parser.add_argument("--allow-hud-intent-trace-live", action="store_true")
    parser.add_argument("--ack-private-trace-artifact", action="store_true")
    parser.add_argument("--ack-runtime-cleanup", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta149-dpublic-hud-intent-syscall-trace-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA149 D-public HUD intent syscall trace",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA149 D-public HUD intent syscall trace",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta149-runner-error"
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
