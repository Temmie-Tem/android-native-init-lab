#!/usr/bin/env python3
"""Guarded S22+ sec_debug/debug_level MID sysrq-panic gate.

This is the zero-flash successor to the failed mainline-ramoops path. The
default dry-run requires a future AGENTS.md exception and stops before any
Android/device access while that policy is inactive. Host-only modes are:

  --offline-check   verify the inert policy draft markers;
  --print-plan      print the attended operator plan.

Read-only device mode:

  --read-only-probe read current Android/root sec_debug state without policy;

Live modes, once separately authorized:

  default dry-run          read-only Android/root precheck and sec_debug state;
  --live-panic            write marker/sysrq only, intentionally panic kernel;
  --collect-after-recovery read retained last_kmsg/pstore after operator recovery.

The helper never flashes Odin packages and never writes block partitions.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from s22plus_m3_observable_live_gate import (
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    EXPECTED_BUILD,
    EXPECTED_DEVICE,
    EXPECTED_MODEL,
    adb_exec_out,
    adb_rows,
    adb_shell,
    append_log,
    host_snapshot,
    odin_devices,
    repo_root,
    require_current_android,
    resolve,
    utc_now,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability


EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MAGISK_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_MARKER = "S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL"
LIVE_ACK_TOKEN = "S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE"
DEBUG_LEVEL_CONFIRM_TOKEN = "DEBUG_LEVEL_MID_SET_BY_OPERATOR"
POLICY_DRAFT = Path("docs/operations/S22PLUS_SEC_DEBUG_MID_SYSRQ_PANIC_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")

READ_FILES = (
    "/proc/reset_reason",
    "/proc/reset_rwc",
    "/proc/store_lastkmsg",
    "/proc/cmdline",
    "/proc/bootconfig",
    "/proc/sys/kernel/sysrq",
    "/proc/sys/kernel/panic",
    "/proc/sys/kernel/panic_on_oops",
    "/proc/sysrq-trigger",
    "/sys/module/sec_debug/parameters/debug_level",
    "/sys/module/sec_debug/parameters/enable",
    "/sys/module/sec_debug/parameters/enable_user",
    "/sys/module/sec_debug/parameters/force_upload",
    "/sys/module/sec_debug_region/parameters/debug_level",
    "/sys/module/qcom_dload_mode/parameters/download_mode",
    "/sys/module/kernel/parameters/panic",
    "/sys/module/kernel/parameters/panic_on_warn",
)

LIST_TARGETS = (
    "/proc/sec_debug",
    "/sys/module/sec_debug/parameters",
    "/sys/module/sec_debug_region/parameters",
    "/sys/fs/pstore",
    "/dev/pmsg0",
)

RETAINED_PATTERNS = (
    EXPECTED_MARKER,
    "S22_NATIVE_INIT",
    "sysrq",
    "SysRq",
    "Kernel panic",
    "panic",
    "Oops",
    "SError",
    "watchdog",
    "sec_debug",
    "upload",
    "ramdump",
    "reset",
)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_sec_debug_mid_sysrq_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def run(argv: list[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_bytes(argv: list[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def redact(text: str) -> str:
    text = re.sub(r"RFCT[0-9A-Z]+", "<REDACTED_SERIAL>", text)
    text = re.sub(r'((?:androidboot|sec_debug)\.[A-Za-z0-9_.-]*serial[A-Za-z0-9_.-]*=)"?[^"\s]+"?', r"\1<REDACTED>", text)
    text = re.sub(r'(kernel\.sec_debug\.ap_serial = )"[^"]+"', r'\1"<REDACTED_AP_SERIAL>"', text)
    return text


def safe_name(path: str) -> str:
    cleaned = path.strip("/").replace("/", "__").replace("*", "glob")
    return re.sub(r"[^A-Za-z0-9_.+-]", "_", cleaned) or "root"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def adb_su_text(serial: str, command: str, *, timeout: float = 30.0) -> tuple[int, str]:
    result = adb_exec_out(command, serial=serial, timeout=timeout)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    return result.returncode, redact(text)


def verify_current_boot_hash(log_path: Path, serial: str) -> None:
    result = adb_exec_out(
        "dd if=/dev/block/by-name/boot bs=4096 2>/dev/null | sha256sum",
        serial=serial,
        timeout=60.0,
    )
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    append_log(log_path, f"current_boot_hash_rc={result.returncode}")
    append_log(log_path, redact(text))
    if result.returncode != 0 or EXPECTED_MAGISK_BOOT_SHA256 not in text:
        raise SystemExit("current boot hash does not match known-booting Magisk baseline")


def required_policy_markers() -> list[str]:
    return [
        "S22+ sec_debug debug_level MID sysrq-panic zero-flash",
        "workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py",
        EXPECTED_TARGET,
        EXPECTED_MAGISK_BOOT_SHA256,
        EXPECTED_MARKER,
        LIVE_ACK_TOKEN,
        DEBUG_LEVEL_CONFIRM_TOKEN,
        "debug_level=MID",
        "operator-set SysDump DEBUG LEVEL MID",
        "sysrq-trigger-c",
        "intentional kernel crash",
        "collect /proc/last_kmsg",
        "no Odin flash",
        "no partition write",
        "manual recovery",
    ]


def verify_text_markers(text: str, source: str, log_path: Path) -> None:
    normalized = " ".join(text.split())
    missing = [item for item in required_policy_markers() if item not in normalized]
    append_log(log_path, f"{source}_missing={missing}")
    if missing:
        raise SystemExit(f"{source} missing sec_debug MID sysrq markers: {missing}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    verify_text_markers((root / "AGENTS.md").read_text(encoding="utf-8"), "agents_exception", log_path)


def verify_policy_draft(root: Path, log_path: Path) -> None:
    draft = root / POLICY_DRAFT
    if not draft.is_file():
        raise SystemExit(f"inert policy draft missing: {draft}")
    verify_text_markers(draft.read_text(encoding="utf-8"), "policy_draft", log_path)


def read_remote_file(serial: str, path: str, *, timeout: float = 15.0, head_bytes: int = 131072) -> dict[str, Any]:
    quoted = shlex.quote(path)
    command = (
        f"if [ -e {quoted} ]; then "
        f"ls -ld {quoted} 2>/dev/null; "
        f"cat {quoted} 2>&1 | head -c {int(head_bytes)}; "
        "else echo __MISSING__; fi"
    )
    rc, text = adb_su_text(serial, command, timeout=timeout)
    return {
        "path": path,
        "rc": rc,
        "missing": "__MISSING__" in text,
        "bytes": len(text.encode("utf-8", errors="replace")),
        "text": text,
    }


def decode_numeric_debug_level(text: str) -> dict[str, Any]:
    numbers = re.findall(r"^\s*([0-9]+)\s*$", text, flags=re.MULTILINE)
    if not numbers:
        return {"present": False}
    value = int(numbers[-1], 10)
    low = value & 0xFF
    high = (value >> 8) & 0xFF
    ascii_le = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in (low, high))
    ascii_be = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in (high, low))
    return {
        "present": True,
        "decimal": value,
        "hex": f"0x{value:04x}",
        "ascii_le": ascii_le,
        "ascii_be": ascii_be,
        "likely_low_code": ascii_le.upper().startswith("LO") or ascii_be.upper().startswith("LO"),
    }


def collect_sec_debug_state(run_dir: Path, log_path: Path, serial: str, label: str) -> dict[str, Any]:
    state_dir = run_dir / "sec_debug_state" / label
    state_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "label": label,
        "timestamp_utc": utc_now(),
        "read_files": {},
        "list_targets": {},
    }

    for path in READ_FILES:
        item = read_remote_file(serial, path)
        write_text(state_dir / f"{safe_name(path)}.txt", item["text"])
        summary["read_files"][path] = {key: value for key, value in item.items() if key != "text"}

    sec_debug_debug_level_path = "/sys/module/sec_debug/parameters/debug_level"
    sec_debug_debug_level_file = state_dir / f"{safe_name(sec_debug_debug_level_path)}.txt"
    if sec_debug_debug_level_file.exists():
        summary["sec_debug_debug_level_decoded"] = decode_numeric_debug_level(
            sec_debug_debug_level_file.read_text(encoding="utf-8", errors="replace")
        )

    for path in LIST_TARGETS:
        quoted = shlex.quote(path)
        rc, text = adb_su_text(serial, f"ls -la {quoted} 2>&1 || true", timeout=15.0)
        write_text(state_dir / f"{safe_name(path)}__listing.txt", text)
        summary["list_targets"][path] = {
            "rc": rc,
            "bytes": len(text.encode("utf-8", errors="replace")),
            "exists_or_listed": "__MISSING__" not in text and "No such file" not in text,
        }

    rc, props = adb_su_text(
        serial,
        "getprop | grep -Ei 'debug|reset|panic|upload|ramdump|pstore|pmsg|ramoops|sysrq' | sort || true",
        timeout=20.0,
    )
    write_text(state_dir / "getprop_debug_reset_filtered.txt", props)
    summary["getprop_filtered"] = {
        "rc": rc,
        "bytes": len(props.encode("utf-8", errors="replace")),
        "line_count": len([line for line in props.splitlines() if line.strip()]),
    }

    rc, dmesg = adb_su_text(
        serial,
        "dmesg -T 2>/dev/null | grep -Eai 'sec_debug|debug_level|sysrq|panic|pstore|pmsg|ramoops|ramdump|upload|reset|watchdog|SError' | tail -400 || true",
        timeout=30.0,
    )
    write_text(state_dir / "dmesg_sec_debug_grep.txt", dmesg)
    summary["dmesg_filtered"] = {
        "rc": rc,
        "bytes": len(dmesg.encode("utf-8", errors="replace")),
        "line_count": len([line for line in dmesg.splitlines() if line.strip()]),
    }

    write_text(state_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    append_log(log_path, f"{label}_sec_debug_state={json.dumps(summary, sort_keys=True)}")
    return summary


def collect_read_only_probe(run_dir: Path, log_path: Path, odin: Path, serial: str) -> dict[str, Any]:
    state = collect_sec_debug_state(run_dir, log_path, serial, "read_only_probe")
    sysdump_route = collect_sysdump_route(run_dir, log_path, serial)
    host_snapshot(run_dir, log_path, "read_only_probe_host", odin)
    pstore_listing = adb_shell(
        "su -c 'ls -la /sys/fs/pstore 2>&1 || true'",
        serial=serial,
        timeout=20.0,
    )
    pstore_text = redact(pstore_listing.stdout + pstore_listing.stderr)
    write_text(run_dir / "read_only_probe_pstore_listing.txt", pstore_text)

    last_kmsg = adb_exec_out(
        "cat /proc/last_kmsg 2>/dev/null | grep -Eai 'S22_SECDEBUG|S22_NATIVE_INIT|sysrq|panic|oops|SError|watchdog|sec_debug|upload|ramdump|reset|download|reboot' | head -400 || true",
        serial=serial,
        timeout=60.0,
    )
    last_kmsg_text = redact((last_kmsg.stdout + last_kmsg.stderr).decode("utf-8", errors="replace"))
    write_text(run_dir / "read_only_probe_last_kmsg_grep.txt", last_kmsg_text)

    summary: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "mode": "read-only-probe",
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "sysrq_triggered": False,
        "agents_exception_required": False,
        "target": EXPECTED_TARGET,
        "sec_debug_state_path": "sec_debug_state/read_only_probe/summary.json",
        "pstore_listing": {
            "rc": pstore_listing.returncode,
            "bytes": len(pstore_text.encode("utf-8", errors="replace")),
        },
        "last_kmsg_grep": {
            "rc": last_kmsg.returncode,
            "bytes": len(last_kmsg_text.encode("utf-8", errors="replace")),
            "line_count": len([line for line in last_kmsg_text.splitlines() if line.strip()]),
        },
        "sysdump_route": sysdump_route,
        "state": state,
    }
    write_text(run_dir / "read_only_probe_summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    append_log(log_path, f"read_only_probe_summary={json.dumps(summary, sort_keys=True)}")
    return summary


def collect_sysdump_route(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    package = "com.sec.android.app.servicemodeapp"
    result = adb_shell(
        "dumpsys package com.sec.android.app.servicemodeapp | "
        "grep -E 'SysDump|CPDebugLevel|ServiceModeAppBroadcastReceiver|Authority: \"9900\"|"
        "Action: \"com.samsung.android.action.SECRET_CODE\"|Category: \"android.intent.category.DEVELOPMENT_PREFERENCE\"' -C 3 || true",
        serial=serial,
        timeout=30.0,
    )
    text = redact(result.stdout + result.stderr)
    write_text(run_dir / "read_only_probe_sysdump_route.txt", text)

    path_result = adb_shell(f"pm path {shlex.quote(package)} 2>&1 || true", serial=serial, timeout=10.0)
    path_text = redact(path_result.stdout + path_result.stderr)
    write_text(run_dir / "read_only_probe_sysdump_package_path.txt", path_text)

    summary = {
        "package": package,
        "package_path_rc": path_result.returncode,
        "package_path_present": f"package:" in path_text,
        "route_dump_rc": result.returncode,
        "route_dump_bytes": len(text.encode("utf-8", errors="replace")),
        "sysdump_activity_found": "com.sec.android.app.servicemodeapp/.SysDump" in text,
        "cp_debug_level_activity_found": "com.sec.android.app.servicemodeapp/.CPDebugLevel" in text,
        "secret_code_receiver_found": "ServiceModeAppBroadcastReceiver" in text,
        "secret_code_9900_found": 'Authority: "9900"' in text,
        "secret_code_action_found": 'Action: "com.samsung.android.action.SECRET_CODE"' in text,
        "development_preference_category_found": 'Category: "android.intent.category.DEVELOPMENT_PREFERENCE"' in text,
    }
    append_log(log_path, f"sysdump_route={json.dumps(summary, sort_keys=True)}")
    return summary


def grep_retained_payload(payload: bytes) -> dict[str, Any]:
    text = payload.decode("utf-8", errors="replace")
    hits: dict[str, int] = {}
    for pattern in RETAINED_PATTERNS:
        hits[pattern] = text.lower().count(pattern.lower())
    nonzero = {key: value for key, value in hits.items() if value}
    return {
        "bytes": len(payload),
        "hit_counts": nonzero,
        "marker_found": EXPECTED_MARKER.encode("ascii") in payload,
    }


def collect_retained_evidence(run_dir: Path, log_path: Path, serial: str, label: str) -> dict[str, Any]:
    retained_dir = run_dir / "retained_evidence" / label
    retained_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "label": label,
        "timestamp_utc": utc_now(),
        "pstore": {},
        "last_kmsg": {},
        "marker_found": False,
    }

    listing = adb_shell(
        "su -c 'for f in /sys/fs/pstore/*; do [ -f \"$f\" ] && echo \"${f##*/}\"; done' 2>/dev/null || true",
        serial=serial,
        timeout=20.0,
    )
    raw_names = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
    names = [name for name in raw_names if re.fullmatch(r"[A-Za-z0-9._+-]+", name)]
    append_log(log_path, f"{label}_pstore_files={names}")
    summary["pstore"]["files"] = names
    summary["pstore"]["rejected_files"] = raw_names if raw_names != names else []

    for name in names:
        remote = f"/sys/fs/pstore/{name}"
        result = adb_exec_out(f"cat {shlex.quote(remote)} 2>/dev/null", serial=serial, timeout=20.0)
        payload = result.stdout + result.stderr
        (retained_dir / f"pstore_{safe_name(name)}.bin").write_bytes(payload)
        scan = grep_retained_payload(payload)
        summary["pstore"][name] = {"rc": result.returncode, **scan}
        summary["marker_found"] = bool(summary["marker_found"] or scan["marker_found"])

    last_kmsg = adb_exec_out("cat /proc/last_kmsg 2>/dev/null || true", serial=serial, timeout=60.0)
    payload = last_kmsg.stdout + last_kmsg.stderr
    (retained_dir / "last_kmsg.bin").write_bytes(payload)
    scan = grep_retained_payload(payload)
    summary["last_kmsg"] = {"rc": last_kmsg.returncode, **scan}
    summary["marker_found"] = bool(summary["marker_found"] or scan["marker_found"])

    rc, last_kmsg_lines = adb_su_text(
        serial,
        "cat /proc/last_kmsg 2>/dev/null | grep -Eai 'S22_SECDEBUG|S22_NATIVE_INIT|sysrq|panic|oops|SError|watchdog|sec_debug|upload|ramdump|reset' | head -400 || true",
        timeout=60.0,
    )
    write_text(retained_dir / "last_kmsg_grep.txt", last_kmsg_lines)
    summary["last_kmsg_grep"] = {
        "rc": rc,
        "bytes": len(last_kmsg_lines.encode("utf-8", errors="replace")),
        "line_count": len([line for line in last_kmsg_lines.splitlines() if line.strip()]),
    }

    write_text(retained_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    append_log(log_path, f"{label}_retained_summary={json.dumps(summary, sort_keys=True)}")
    return summary


def trigger_sysrq_panic(serial: str, log_path: Path, delay_sec: int) -> subprocess.CompletedProcess[bytes] | None:
    command = "\n".join(
        [
            "set -u",
            f"printf '%s\\n' {shlex.quote(EXPECTED_MARKER + ' phase=before-sysrq')} > /dev/kmsg 2>/dev/null || true",
            f"if [ -e /dev/pmsg0 ]; then printf '%s\\n' {shlex.quote(EXPECTED_MARKER + ' phase=before-sysrq-pmsg')} > /dev/pmsg0 2>/dev/null || true; fi",
            "if ! printf '1\\n' > /proc/sys/kernel/sysrq 2>/dev/null; then echo sysrq_enable_failed >&2; exit 41; fi",
            "sync",
            f"sleep {int(delay_sec)}",
            f"printf '%s\\n' {shlex.quote(EXPECTED_MARKER + ' phase=sysrq-trigger-c')} > /dev/kmsg 2>/dev/null || true",
            "printf 'c\\n' > /proc/sysrq-trigger",
            f"printf '%s\\n' {shlex.quote(EXPECTED_MARKER + ' phase=sysrq-returned')} > /dev/kmsg 2>/dev/null || true",
        ]
    )
    argv = ["adb", "-s", serial, "exec-out", "su", "-c", command]
    append_log(log_path, "live_panic_command=adb exec-out su -c <redacted-script>")
    try:
        return run_bytes(argv, timeout=max(8.0, float(delay_sec) + 12.0))
    except subprocess.TimeoutExpired:
        append_log(log_path, "live_panic_command_timeout_after_trigger=1")
        return None


def observe_after_trigger(run_dir: Path, log_path: Path, seconds: int, odin: Path, serial: str | None) -> str:
    deadline = time.monotonic() + seconds
    iteration = 0
    result = "no_transport"
    while time.monotonic() < deadline:
        iteration += 1
        label = f"post_sysrq_{iteration:03d}"
        if iteration == 1 or iteration % 5 == 0:
            host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-odin")
        if len(devices) == 1:
            result = "odin"
            break
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices after sysrq: {devices}")
        rows = adb_rows(log_path, f"{label}-adb")
        usable = [row for row in rows if row[1] == "device"]
        if serial and not any(row[0] == serial for row in usable):
            result = "adb_disconnected"
        elif usable:
            result = "adb_still_online"
        time.sleep(1.0)
    append_log(log_path, f"post_sysrq_observe_result={result}")
    return result


def print_operator_plan() -> None:
    script = "workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py"
    print("S22+ sec_debug/debug_level MID sysrq-panic plan")
    print("state: host-only plan; no device action was performed")
    print()
    print("current intended order:")
    print("  1. operator sets Samsung SysDump DEBUG LEVEL to MID, if available")
    print("  2. promote the inert AGENTS policy only after explicit approval")
    print("  3. run default dry-run to collect read-only sec_debug state")
    print("  4. trigger one intentional Android sysrq panic with ack")
    print("  5. operator recovers the phone, then collect retained evidence")
    print()
    print("host-only checks:")
    print(f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --offline-check")
    print(f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --print-plan")
    print()
    print("read-only current-state probe, no policy required:")
    print(f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --read-only-probe")
    print()
    print("default dry-run after active policy:")
    print(f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script}")
    print()
    print("attended panic trigger only after debug_level=MID is operator-confirmed:")
    print(
        f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} "
        f"--live-panic --ack {LIVE_ACK_TOKEN} --confirm-debug-level-mid {DEBUG_LEVEL_CONFIRM_TOKEN}"
    )
    print()
    print("post-recovery retained evidence collection:")
    print(f"  PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --collect-after-recovery")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin")
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--panic-delay-sec", type=int, default=3)
    parser.add_argument("--post-trigger-observe-sec", type=int, default=90)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--read-only-probe", action="store_true")
    parser.add_argument("--collect-after-recovery", action="store_true")
    parser.add_argument("--live-panic", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--confirm-debug-level-mid")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.print_plan,
            args.read_only_probe,
            args.collect_after_recovery,
            args.live_panic,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --print-plan, --read-only-probe, --collect-after-recovery, and --live-panic are mutually exclusive"
        )

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_sec_debug_mid_sysrq_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus sec_debug MID sysrq gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    if args.print_plan:
        append_log(log_path, "print_plan=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print_operator_plan()
        print(f"log={display_path(log_path)}")
        return 0

    if args.offline_check:
        verify_policy_draft(root, log_path)
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: inert sec_debug MID sysrq policy draft markers verified; no device action; log={log_path}")
        return 0

    if args.read_only_probe:
        if not odin.is_file():
            raise SystemExit(f"odin4 missing: {odin}")
        selected_serial = require_current_android(log_path, args.serial)
        verify_android_stability(
            log_path,
            selected_serial,
            args.android_stability_samples,
            args.android_stability_interval_sec,
        )
        verify_current_boot_hash(log_path, selected_serial)
        collect_read_only_probe(run_dir, log_path, odin, selected_serial)
        print(f"read-only probe ok: Android/root, Magisk boot hash, and sec_debug state collected; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)
    collect_sec_debug_state(run_dir, log_path, selected_serial, "precheck")

    if args.collect_after_recovery:
        retained = collect_retained_evidence(run_dir, log_path, selected_serial, "post_recovery")
        found = bool(retained["marker_found"])
        print(f"post-recovery retained evidence collected; marker_found={int(found)}; log={log_path}")
        return 0 if found else 10

    if not args.live_panic:
        print(
            "dry-run ok: AGENTS exception, Android/root stability, Magisk boot hash, "
            f"and sec_debug read-only state collected; log={log_path}"
        )
        return 0

    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live-panic requires --ack {LIVE_ACK_TOKEN}")
    if args.confirm_debug_level_mid != DEBUG_LEVEL_CONFIRM_TOKEN:
        raise SystemExit(f"--live-panic requires --confirm-debug-level-mid {DEBUG_LEVEL_CONFIRM_TOKEN}")

    host_snapshot(run_dir, log_path, "before_sec_debug_sysrq", odin)
    result = trigger_sysrq_panic(selected_serial, log_path, args.panic_delay_sec)
    if result is not None:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        append_log(log_path, f"live_panic_command_rc={result.returncode}")
        append_log(log_path, redact(output))
        if result.returncode == 41:
            print(f"sysrq enable failed before panic trigger; log={log_path}", file=sys.stderr)
            return 41
    observed = observe_after_trigger(run_dir, log_path, args.post_trigger_observe_sec, odin, selected_serial)
    print(
        "sysrq panic trigger sequence finished/was interrupted. "
        f"post_trigger_observed={observed}. Recover the phone, then run --collect-after-recovery. log={log_path}"
    )
    return 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
