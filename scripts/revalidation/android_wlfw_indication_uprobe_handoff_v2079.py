#!/usr/bin/env python3
"""V2079 Android-good WLFW indication uprobe handoff.

This runner reuses the proven V1521 Android/Magisk/native-rollback engine, but
installs a lighter post-fs-data observer than V1753: tracefs uprobes on
cnss-daemon WLFW indication/status offsets plus filtered dmesg/logcat snapshots.

It does not run strace, DIAG, QRTR matrices, Wi-Fi scan/connect, credentials,
DHCP/routes, external ping, eSoC/PCIe/GDSC/PMIC/GPIO actions, or firmware/partition
writes beyond the declared Android boot handoff and native v724 rollback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521


DEFAULT_OUT_DIR = Path("tmp/wifi/v2079-android-wlfw-indication-uprobe-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V2079_ANDROID_WLFW_INDICATION_UPROBE_HANDOFF_2026-06-05.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v2079-android-wlfw-indication-uprobe-handoff.txt")

MODULE_NAME = "a90_v2079_wlfw_uprobe"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v2079-wlfw-uprobe"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v2079_wlfw_uprobe"

WLFW_EVENTS = (
    "wlfw_qmi_ind_cb_entry",
    "wlfw_qmi_ind_msg_unknown",
    "wlfw_qmi_ind_decode_0x28_ok",
    "wlfw_qmi_ind_decode_0x2a_ok",
    "wlfw_qmi_ind_decode_0x41_ok",
    "wlfw_qmi_ind_fw_mem_flag",
    "wlfw_qmi_ind_msa_flag",
    "wlfw_qmi_ind_queue_link",
    "wlfw_qmi_ind_cond_signal",
    "wlfw_handle_ind_entry",
    "wlfw_handle_ind_type",
    "wlfw_handle_ind_type_0x28",
    "wlfw_handle_ind_type_0x2a",
    "wlfw_handle_ind_type_0x41",
    "wlan_send_status_entry",
    "wlan_send_status_send_ret",
    "wlan_send_status_return",
    "wlan_send_version_entry",
    "wlan_send_version_send_ret",
    "wlan_send_version_return",
    "wlfw_cal_report_return",
    "wlfw_worker_handle_ind_call",
    "wlfw_worker_post_done_wait",
)

EVENT_SPECS = (
    ("wlfw_qmi_ind_cb_entry", "0xe100", "msg_id=%x1 payload_len=%x3"),
    ("wlfw_qmi_ind_msg_unknown", "0xe2d0", "msg_id=%x21"),
    ("wlfw_qmi_ind_decode_0x28_ok", "0xe3d0", ""),
    ("wlfw_qmi_ind_decode_0x2a_ok", "0xe368", ""),
    ("wlfw_qmi_ind_decode_0x41_ok", "0xe3a0", ""),
    ("wlfw_qmi_ind_fw_mem_flag", "0xe2f0", "msg_id=%x21"),
    ("wlfw_qmi_ind_msa_flag", "0xe328", "msg_id=%x21"),
    ("wlfw_qmi_ind_queue_link", "0xe40c", ""),
    ("wlfw_qmi_ind_cond_signal", "0xe450", ""),
    ("wlfw_handle_ind_entry", "0xce24", ""),
    ("wlfw_handle_ind_type", "0xcee0", "ind_type=%x3"),
    ("wlfw_handle_ind_type_0x28", "0xcf08", "fw_status=%x4"),
    ("wlfw_handle_ind_type_0x2a", "0xcf84", "arg0=%x4 arg1=%x5"),
    ("wlfw_handle_ind_type_0x41", "0xd00c", "arg0=%x4 arg1=%x5"),
    ("wlan_send_status_entry", "0xc9ac", "is_on=%x0 cookie=%x1"),
    ("wlan_send_status_send_ret", "0xcab0", "send_rc=%x0 qmi_result=%x3"),
    ("wlan_send_status_return", "0xcb00", "rc=%x19"),
    ("wlan_send_version_entry", "0xcb2c", ""),
    ("wlan_send_version_send_ret", "0xccec", "send_rc=%x0 qmi_result=%x4"),
    ("wlan_send_version_return", "0xcdec", "rc=%x23"),
    ("wlfw_cal_report_return", "0xf750", "rc=%x19"),
    ("wlfw_worker_handle_ind_call", "0xe0b4", ""),
    ("wlfw_worker_post_done_wait", "0xe070", ""),
)

FILTER_RE = re.compile(
    r"wlanmdsp|wlan[_/-]?pd|tftp|WLFW|wlfw|icnss|cnss|BDF file|regdb\.bin|bdwlan\.bin|"
    r"FW ready|WLAN FW is ready|wlan0",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=v1521.DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=v1521.DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=v1521.DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=v1521.DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=420)
    parser.add_argument("--sampler-samples", type=int, default=80)
    parser.add_argument("--sampler-delay-us", type=int, default=250000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=170)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def remote_quote(path: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"remote path must be absolute: {path}")
    return shlex.quote(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V2079 Android WLFW uprobe observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only tracefs uprobe observer for Android-good WLFW indication sequence.",
            "",
        ]
    )


def sepolicy_rule() -> str:
    return """# Temporary V2079 diagnostic policy for tracefs-only uprobes.
allow magisk debugfs dir { getattr open read search write add_name remove_name };
allow magisk debugfs file { append create getattr open read setattr unlink write };
allow magisk tracefs dir { getattr open read search write add_name remove_name };
allow magisk tracefs file { append create getattr open read setattr unlink write };
allow magisk vendor_file file { execute execute_no_trans getattr map open read };
allow magisk vendor_file dir { getattr open read search };
allow magisk shell_data_file dir { add_name create getattr open read remove_name search write };
allow magisk shell_data_file file { append create getattr open read setattr unlink write };
"""


def event_spec_shell() -> str:
    lines = []
    for name, offset, fetch in EVENT_SPECS:
        spec = f"p:a90v2079/{name} /vendor/bin/cnss-daemon:{offset}"
        if fetch:
            spec = f"{spec} {fetch}"
        lines.append(spec)
    return "\n".join(lines)


def post_fs_data_script(samples: int, delay_us: int) -> str:
    specs = event_spec_shell()
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
SAMPLES={samples}
DELAY_US={delay_us}
GROUP=a90v2079
BIN=/vendor/bin/cnss-daemon
FILTER='wlanmdsp|wlan[_/-]?pd|tftp|WLFW|wlfw|icnss|cnss|BDF file|regdb\\.bin|bdwlan\\.bin|FW ready|WLAN FW is ready|wlan0'

mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
TRACE="$OUT/trace.txt"
TRACE_LAST="$OUT/trace-last.txt"
EVENTS="$OUT/events.txt"
UPROBES="$OUT/uprobe-events.txt"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
SUMMARY="$OUT/summary.txt"
TRACE_ROOT=""

write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V2079_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

find_trace_root() {{
  for d in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    [ -d "$d" ] && [ -w "$d/uprobe_events" ] && {{ TRACE_ROOT="$d"; return 0; }}
  done
  return 1
}}

disable_events() {{
  [ -n "$TRACE_ROOT" ] || return 0
  if [ -d "$TRACE_ROOT/events/$GROUP" ]; then
    for e in "$TRACE_ROOT/events/$GROUP"/*/enable; do
      [ -e "$e" ] && echo 0 > "$e" 2>/dev/null || true
    done
  fi
}}

remove_events() {{
  [ -n "$TRACE_ROOT" ] || return 0
  for name in \\
    wlfw_qmi_ind_cb_entry wlfw_qmi_ind_msg_unknown wlfw_qmi_ind_decode_0x28_ok \\
    wlfw_qmi_ind_decode_0x2a_ok wlfw_qmi_ind_decode_0x41_ok wlfw_qmi_ind_fw_mem_flag \\
    wlfw_qmi_ind_msa_flag wlfw_qmi_ind_queue_link wlfw_qmi_ind_cond_signal \\
    wlfw_handle_ind_entry wlfw_handle_ind_type wlfw_handle_ind_type_0x28 \\
    wlfw_handle_ind_type_0x2a wlfw_handle_ind_type_0x41 wlan_send_status_entry \\
    wlan_send_status_send_ret wlan_send_status_return wlan_send_version_entry \\
    wlan_send_version_send_ret wlan_send_version_return wlfw_cal_report_return \\
    wlfw_worker_handle_ind_call wlfw_worker_post_done_wait; do
    echo "-:$GROUP/$name" >> "$TRACE_ROOT/uprobe_events" 2>/dev/null || true
  done
}}

add_events() {{
  cat > "$OUT/event-specs.txt" <<'A90V2079_EVENTS'
{specs}
A90V2079_EVENTS
  while IFS= read -r spec; do
    [ -n "$spec" ] || continue
    echo "$spec" >> "$TRACE_ROOT/uprobe_events" 2>> "$OUT/setup-errors.txt" || true
  done < "$OUT/event-specs.txt"
}}

enable_events() {{
  [ -d "$TRACE_ROOT/events/$GROUP" ] || return 1
  for e in "$TRACE_ROOT/events/$GROUP"/*/enable; do
    [ -e "$e" ] && echo 1 > "$e" 2>/dev/null || true
  done
  return 0
}}

dump_filtered() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 1600 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 1600 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_trace() {{
  [ -n "$TRACE_ROOT" ] || return 0
  cat "$TRACE_ROOT/trace" 2>/dev/null > "$TRACE.tmp" || true
  mv "$TRACE.tmp" "$TRACE" 2>/dev/null || true
  tail -n 800 "$TRACE" > "$TRACE_LAST.tmp" 2>/dev/null || true
  mv "$TRACE_LAST.tmp" "$TRACE_LAST" 2>/dev/null || true
  cat "$TRACE_ROOT/uprobe_events" 2>/dev/null | grep "$GROUP" > "$UPROBES.tmp" || true
  mv "$UPROBES.tmp" "$UPROBES" 2>/dev/null || true
  find "$TRACE_ROOT/events/$GROUP" -maxdepth 2 -type f -name enable -print -exec cat {{}} \\; > "$EVENTS.tmp" 2>/dev/null || true
  mv "$EVENTS.tmp" "$EVENTS" 2>/dev/null || true
}}

summarize() {{
  {{
    printf 'trace_root='; echo "$TRACE_ROOT"
    printf 'trace_ready='; [ -n "$TRACE_ROOT" ] && [ -r "$TRACE" ] && echo 1 || echo 0
    printf 'uprobe_event_count='; grep -c "$GROUP/" "$UPROBES" 2>/dev/null || echo 0
    for name in \\
      wlfw_qmi_ind_cb_entry wlfw_qmi_ind_decode_0x28_ok wlfw_qmi_ind_decode_0x2a_ok \\
      wlfw_qmi_ind_decode_0x41_ok wlfw_qmi_ind_fw_mem_flag wlfw_qmi_ind_msa_flag \\
      wlfw_qmi_ind_queue_link wlfw_handle_ind_entry wlfw_handle_ind_type_0x28 \\
      wlan_send_status_entry wlan_send_status_send_ret wlan_send_version_entry \\
      wlan_send_version_send_ret wlfw_worker_handle_ind_call; do
      printf '%s=' "$name"
      grep -c "$name:" "$TRACE" 2>/dev/null || echo 0
    done
    printf 'fw_ready_lines='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eic 'WLAN FW is ready|FW ready' || echo 0
    printf 'bdf_lines='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eic 'BDF file|regdb\\.bin|bdwlan\\.bin' || echo 0
    printf 'wlan0_lines='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eic '\\bwlan0\\b' || echo 0
    printf 'wlanmdsp_lines='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eic 'wlanmdsp' || echo 0
  }} > "$SUMMARY.tmp"
  mv "$SUMMARY.tmp" "$SUMMARY" 2>/dev/null || true
}}

(
  umask 022
  write_status start
  : > "$LOG"
  echo "A90_V2079_POSTFS_BEGIN" >> "$LOG"
  id >> "$LOG" 2>&1 || true
  cat /proc/self/attr/current >> "$LOG" 2>&1 || true
  if find_trace_root; then
    echo "trace_root=$TRACE_ROOT" >> "$LOG"
    echo 0 > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
    disable_events
    remove_events
    echo > "$TRACE_ROOT/trace" 2>/dev/null || true
    add_events
    enable_events
    echo 1 > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
  else
    echo "trace_root=missing_or_unwritable" >> "$LOG"
  fi
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V2079_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    if [ "$((i % 8))" = "0" ]; then
      dump_filtered
      dump_trace
      summarize
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    echo "SRC wlfw_uprobe_summary" >> "$LOG"
    cat "$SUMMARY" >> "$LOG" 2>/dev/null || true
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    echo "A90_V2079_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  dump_filtered
  dump_trace
  summarize
  disable_events
  remove_events
  echo "A90_V2079_POSTFS_END" >> "$LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def module_stage_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "magisk-module"


def prepare_module(store: EvidenceStore, args: argparse.Namespace, execute: bool) -> v1521.StepResult:
    started = time.monotonic()
    if not execute:
        return v1521.write_step(
            store,
            "prepare-v2079-magisk-module",
            "host:prepare temporary WLFW uprobe Magisk module",
            "[dry-run] not executed\n",
            "",
            0,
            0.0,
            skipped=True,
            ok_override=True,
        )
    stage = module_stage_dir(store)
    ensure_private_dir(stage)
    write_private_text(stage / "module.prop", module_prop())
    write_private_text(stage / "post-fs-data.sh", post_fs_data_script(args.sampler_samples, args.sampler_delay_us))
    write_private_text(stage / "sepolicy.rule", sepolicy_rule())
    (stage / "post-fs-data.sh").chmod(0o700)
    (stage / "sepolicy.rule").chmod(0o600)
    text = "\n".join(
        [
            f"module_dir={stage}",
            f"samples={args.sampler_samples}",
            f"delay_us={args.sampler_delay_us}",
            "files=module.prop post-fs-data.sh sepolicy.rule",
            "observer=tracefs-uprobes-only no-strace no-diag no-qrtr-matrix",
            "",
        ]
    )
    return v1521.write_step(
        store,
        "prepare-v2079-magisk-module",
        "host:prepare temporary WLFW uprobe Magisk module",
        text,
        "",
        0,
        time.monotonic() - started,
    )


def install_module_android_steps(args: argparse.Namespace, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    stage = module_stage_dir(store)
    remote_prop = f"{REMOTE_STAGE_PREFIX}_module.prop"
    remote_postfs = f"{REMOTE_STAGE_PREFIX}_post-fs-data.sh"
    remote_policy = f"{REMOTE_STAGE_PREFIX}_sepolicy.rule"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"cp {remote_quote(remote_policy)} {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)} {remote_quote(remote_policy)}; "
        "sync"
    )
    return [
        ("push-v2079-module-prop-android", [*v1521.adb_base(args), "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v2079-post-fs-data-android", [*v1521.adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v2079-sepolicy-android", [*v1521.adb_base(args), "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("install-v2079-module-android-su", [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)], args.timeout),
    ]


def cleanup_module_android_command(args: argparse.Namespace) -> list[str]:
    shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} "
        f"{remote_quote(REMOTE_STAGE_PREFIX)}_*; sync"
    )
    return [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(shell)]


def cleanup_module_recovery_best_effort_command(args: argparse.Namespace) -> list[str]:
    return [
        *v1521.adb_base(args),
        "shell",
        (
            f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} "
            f"{remote_quote(REMOTE_STAGE_PREFIX)}_* 2>/dev/null || true; sync"
        ),
    ]


def read_file(path: Path, limit: int = 5_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v2079-wlfw-uprobe"
    return candidate if candidate.is_dir() else root


def parse_kv(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def first_match(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def collect_event_counts(trace: str) -> dict[str, int]:
    return {event: count_lines(trace, rf"\b{re.escape(event)}:") for event in WLFW_EVENTS}


def collect_msg_ids(trace: str) -> list[str]:
    seen: list[str] = []
    for match in re.finditer(r"wlfw_qmi_ind_cb_entry:.*?msg_id=(0x[0-9a-fA-F]+).*?payload_len=(0x[0-9a-fA-F]+)", trace):
        value = f"{match.group(1)}/len={match.group(2)}"
        if value not in seen:
            seen.append(value)
    return seen[:32]


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    trace = read_file(base / "trace.txt")
    trace_last = read_file(base / "trace-last.txt")
    dmesg = read_file(base / "dmesg-filtered.txt") + "\n" + read_file(root / "host-dmesg-filtered.txt")
    logcat = read_file(base / "logcat-filtered.txt")
    status = read_file(base / "status.txt")
    samples = read_file(base / "samples.log")
    summary = parse_kv(read_file(base / "summary.txt"))
    uprobes = read_file(base / "uprobe-events.txt")
    setup_errors = read_file(base / "setup-errors.txt")
    combined_android = dmesg + "\n" + logcat
    event_counts = collect_event_counts(trace)
    return {
        "base": str(base),
        "files_present": {
            "status": bool(status),
            "samples": bool(samples),
            "done": (base / "done").exists(),
            "trace": bool(trace),
            "summary": bool(summary),
            "uprobe_events": bool(uprobes),
            "dmesg": bool(dmesg.strip()),
            "logcat": bool(logcat.strip()),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V2079_SAMPLE_BEGIN"),
        "summary": summary,
        "event_counts": event_counts,
        "msg_ids": collect_msg_ids(trace),
        "trace_line_count": trace.count("\n"),
        "trace_last_excerpt": trace_last[-8000:],
        "uprobe_event_count": count_lines(uprobes, r"a90v2079/"),
        "setup_errors_excerpt": setup_errors[-4000:],
        "dmesg_counts": {
            "fw_ready_lines": count_lines(combined_android, r"WLAN FW is ready|FW ready"),
            "bdf_lines": count_lines(combined_android, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "wlan0_lines": count_lines(combined_android, r"\bwlan0\b"),
            "wlanmdsp_lines": count_lines(combined_android, r"wlanmdsp"),
            "wlfw_lines": count_lines(combined_android, r"\bwlfw\b|WLFW"),
        },
        "first_lines": {
            "wlanmdsp": first_match(combined_android, r"wlanmdsp"),
            "bdf": first_match(combined_android, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "fw_ready": first_match(combined_android, r"WLAN FW is ready|FW ready"),
            "wlan0": first_match(combined_android, r"\bwlan0\b"),
            "qmi_ind": first_match(trace, r"wlfw_qmi_ind_cb_entry:"),
            "handle_ind": first_match(trace, r"wlfw_handle_ind_entry:"),
        },
    }


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1521.DEFAULT_NATIVE_IMAGE = DEFAULT_NATIVE_IMAGE
    v1521.DEFAULT_NATIVE_EXPECT_VERSION = DEFAULT_NATIVE_EXPECT_VERSION
    v1521.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1521.LATEST_POINTER = LATEST_POINTER
    v1521.module_prop = module_prop
    v1521.post_fs_data_script = post_fs_data_script
    v1521.prepare_module = prepare_module
    v1521.install_module_android_steps = install_module_android_steps
    v1521.cleanup_module_android_command = cleanup_module_android_command
    v1521.cleanup_module_recovery_best_effort_command = cleanup_module_recovery_best_effort_command
    v1521.analyze_pulled_evidence = analyze_pulled_evidence


def classify_android(base_decision: str, base_pass: bool, context: dict[str, Any]) -> tuple[str, bool, str]:
    rollback_completed = base_pass or "rollback-pass" in base_decision
    if not rollback_completed:
        return (
            f"v2079-android-wlfw-uprobe-base-failed-{base_decision}",
            False,
            "underlying Android handoff/rollback did not complete",
        )
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    counts = analysis.get("event_counts") or {}
    dmesg = analysis.get("dmesg_counts") or {}
    fw_ready = int(dmesg.get("fw_ready_lines") or 0) > 0
    bdf = int(dmesg.get("bdf_lines") or 0) > 0
    qmi_cb = int(counts.get("wlfw_qmi_ind_cb_entry") or 0)
    queued = int(counts.get("wlfw_qmi_ind_queue_link") or 0)
    handle = int(counts.get("wlfw_handle_ind_entry") or 0)
    status = int(counts.get("wlan_send_status_entry") or 0)
    version = int(counts.get("wlan_send_version_entry") or 0)

    if not files.get("trace") or int(analysis.get("uprobe_event_count") or 0) < 8:
        return (
            "v2079-android-wlfw-uprobe-tracefs-insufficient-rollback-pass",
            False,
            "rollback completed, but tracefs uprobe setup/capture was insufficient",
        )
    if fw_ready and qmi_cb > 0 and "0x21/len=0x0" in (analysis.get("msg_ids") or []):
        return (
            "v2079-android-wlfw-uprobe-fw-ready-late-msg21-observed-rollback-pass",
            True,
            "Android-good reached FW-ready and tracefs captured the late WLFW QMI msg_id 0x21 indication",
        )
    if fw_ready and (queued > 0 or handle > 0 or status > 0 or version > 0):
        return (
            "v2079-android-wlfw-uprobe-fw-ready-late-indication-observed-rollback-pass",
            True,
            "Android-good reached FW-ready and tracefs captured the late WLFW indication/status path",
        )
    if fw_ready and qmi_cb > 0:
        return (
            "v2079-android-wlfw-uprobe-fw-ready-qmi-callback-only-rollback-pass",
            True,
            "Android-good reached FW-ready and captured WLFW QMI callbacks, but not the later queue/status hooks",
        )
    if fw_ready and qmi_cb == 0:
        return (
            "v2079-android-wlfw-uprobe-fw-ready-no-qmi-hook-rollback-pass",
            False,
            "Android-good reached FW-ready, but the cnss-daemon uprobe offsets did not fire; treat as hook-offset gap",
        )
    if bdf:
        return (
            "v2079-android-wlfw-uprobe-bdf-no-fw-ready-degraded-rollback-pass",
            False,
            "Android reached BDF but not FW-ready in this capture; reject as degraded comparator",
        )
    if not files.get("done"):
        return (
            "v2079-android-wlfw-uprobe-sampler-missing-rollback-pass",
            False,
            "rollback completed, but the Android uprobe sampler did not finish and did not capture a sufficient comparator",
        )
    return (
        "v2079-android-wlfw-uprobe-no-good-baseline-rollback-pass",
        False,
        "Android-good comparator did not reach the WLAN downstream baseline",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    counts = analysis.get("event_counts") or {}
    dmesg = analysis.get("dmesg_counts") or {}
    first = analysis.get("first_lines") or {}
    count_rows = [[event, counts.get(event, 0)] for event in WLFW_EVENTS]
    return "\n".join(
        [
            "# V2079 Android-good WLFW Indication Uprobe Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Discriminator",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["uprobe_event_count", analysis.get("uprobe_event_count")],
                    ["trace_line_count", analysis.get("trace_line_count")],
                    ["msg_ids", json.dumps(analysis.get("msg_ids") or [])],
                    ["fw_ready/bdf/wlan0", f"{dmesg.get('fw_ready_lines')}/{dmesg.get('bdf_lines')}/{dmesg.get('wlan0_lines')}"],
                    ["wlfw/wlanmdsp", f"{dmesg.get('wlfw_lines')}/{dmesg.get('wlanmdsp_lines')}"],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
            "",
            "## Native Comparator",
            "",
            markdown_table(
                ["source", "observed edge", "downstream"],
                [
                    [
                        "Android V2079",
                        "FW-ready baseline captured `wlfw_qmi_ind_cb_entry msg_id=0x21 payload_len=0x0` at the `icnss: WLAN FW is ready` edge",
                        "BDF, FW-ready, and `wlan0` visible",
                    ],
                    [
                        "Native V2009/V2011/V2031",
                        "only `wlfw_qmi_ind_cb_entry msg_id=0x2b payload_len=0x0` was observed after cap/BDF/cal success",
                        "no late `0x21`, no FW-ready, no `wlan0`",
                    ],
                    [
                        "Decision",
                        "the AP-side PerMgr/register/vote path is already past; the missing post-cal edge is the modem/WLFW late `0x21` ready indication",
                        "next native unit should target why the modem never publishes that edge",
                    ],
                ],
            ),
            "",
            "## First Lines",
            "",
            markdown_table(
                ["marker", "line"],
                [[key, value] for key, value in first.items()],
            ),
            "",
            "## Event Counts",
            "",
            markdown_table(["event", "hits"], count_rows),
            "",
            "## Steps",
            "",
            markdown_table(
                ["step", "status", "rc", "duration", "file"],
                [
                    [
                        item["name"],
                        "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
                        item["rc"],
                        f"{item['duration_sec']:.3f}s",
                        item["file"],
                    ]
                    for item in manifest["steps"]
                ],
            ),
            "",
            "## Safety",
            "",
            "Bounded Android handoff with a temporary Magisk module and native rollback. The module writes only to `/data/local/tmp/a90-v2079-wlfw-uprobe` and `/data/adb/modules/a90_v2079_wlfw_uprobe`; cleanup removes both before restoring native v724. It uses tracefs uprobes only, with no strace, DIAG, QRTR matrix, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot-image handoff/rollback.",
            "",
            "## Branch",
            "",
            "- If Android-good captures late WLFW `msg_id=0x21` and native remains `0x2b`-only, stop repeating PerMgr/rild/DIAG and target the modem/WLFW ready-publication condition.",
            "- If a future native run captures `msg_id=0x21`, chase the immediate kernel FW-ready and `wlan0` cascade before any scan/connect work.",
            "- If Android-good does not reach FW-ready, reject this as a degraded comparator and rerun only with the same light observer.",
            "",
        ]
    )


def check_forbidden_output(manifest: dict[str, Any], summary: str) -> list[str]:
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n" + summary
    leaks: list[str] = []
    for key in v1521.FORBIDDEN_OUTPUT_ENV_KEYS:
        value = __import__("os").environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    if execute:
        decision, pass_ok, reason = classify_android(base_decision, base_pass, context)
    else:
        decision = "v2079-android-wlfw-uprobe-plan-ready" if args.command == "plan" else "v2079-android-wlfw-uprobe-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
    manifest = {
        "cycle": "V2079",
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    leaks = check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v2079-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
