#!/usr/bin/env python3
"""V1753 Android-good WLAN-PD firmware-request reference handoff.

This runner reuses the V1521 Android/Magisk/native-rollback handoff engine, but
installs a temporary post-fs-data module that observes the Android-good
firmware-request path for `wlanmdsp.mbn` or adjacent WLAN-PD image requests.

The module starts only diagnostic collection: bounded `strace` attach attempts
for already-started `tftp_server`, `rmt_storage`, and `cnss-daemon`, plus
filtered dmesg/logcat/proc snapshots.  It does not enable Wi-Fi, scan/connect,
use credentials, run DHCP/routes, ping externally, write PMIC/GPIO/GDSC/eSoC
state, issue eSoC notify/BOOT_DONE, rescan PCI, bind/unbind platforms, or
modify vendor/system partitions.  The only persistent Android-side writes are a
temporary Magisk module and a bounded evidence directory, both removed before
native v724 rollback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import (
    EvidenceStore,
    ensure_private_dir,
    workspace_private_input_path,
    write_private_text,
)

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521


DEFAULT_OUT_DIR = Path("tmp/wifi/v1753-android-good-wlan-pd-firmware-request")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1753_ANDROID_GOOD_WLAN_PD_FIRMWARE_REQUEST_2026-06-03.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1753-android-good-wlan-pd-firmware-request.txt")

MODULE_NAME = "a90_v1753_fwreq"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1753-wlan-pd-fwreq"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1753_fwreq"
STRACE_SOURCE = workspace_private_input_path("external_tools", "userland", "bin", "strace-aarch64-static")

FIRMWARE_RE = re.compile(
    r"wlanmdsp|wlan[_/-]?pd|wlan/fw|firmware/(?:wlan|image)|tftp|rmt_storage|WLFW|wlfw|icnss|cnss|wlan0",
    re.IGNORECASE,
)
REQUEST_RE = re.compile(r"wlanmdsp(?:\.mbn)?|wlan[_/-]?pd|wlan/fw", re.IGNORECASE)


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
    parser.add_argument("--sampler-samples", type=int, default=260)
    parser.add_argument("--sampler-delay-us", type=int, default=250000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=170)
    parser.add_argument("--strace-binary", type=Path, default=STRACE_SOURCE)
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
            "name=A90 V1753 WLAN-PD firmware request observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good firmware-request observer. Remove after capture.",
            "",
        ]
    )


def sepolicy_rule() -> str:
    return """# Temporary V1753 diagnostic policy for read-only strace attach.
allow magisk vendor_rfs_access process ptrace;
allow magisk vendor_rmt_storage process ptrace;
allow magisk vendor_wcnss_service process ptrace;
allow magisk vendor_file dir { getattr open read search };
allow magisk vendor_file file { execute execute_no_trans getattr map open read };
allow magisk shell_data_file dir { add_name create getattr open read remove_name search write };
allow magisk shell_data_file file { append create getattr open read setattr unlink write };
allow magisk adb_data_file dir { add_name create getattr open read remove_name search write };
allow magisk adb_data_file file { append create getattr open read setattr unlink write };
"""


def post_fs_data_script(samples: int, delay_us: int) -> str:
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
MOD={REMOTE_MODULE_DIR}
STRACE="$MOD/a90_strace"
SAMPLES={samples}
DELAY_US={delay_us}
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
SNAP="$OUT/proc-snapshots.txt"
FW="$OUT/firmware-snapshot.txt"
PIDS="$OUT/strace-pids.txt"
REQ="$OUT/request-summary.txt"
FILTER='wlanmdsp|wlan[_/-]?pd|wlan/fw|firmware/(wlan|image)|tftp|rmt_storage|WLFW|wlfw|icnss|cnss|wlan0'

write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1753_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

find_pid_by_cmd() {{
  pattern="$1"
  for proc in /proc/[0-9]*; do
    [ -r "$proc/cmdline" ] || continue
    cmd="$(tr '\\0' ' ' < "$proc/cmdline" 2>/dev/null)"
    case "$cmd" in
      *"$pattern"*) echo "${{proc##*/}}"; return 0 ;;
    esac
  done
  return 1
}}

dump_filtered() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 1200 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 1200 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.rmt_storage ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

dump_firmware_snapshot() {{
  {{
    echo "A90_V1753_FIRMWARE_SNAPSHOT_BEGIN"
    for d in /vendor/firmware /vendor/firmware_mnt/image /mnt/vendor/firmware /firmware/image; do
      echo "DIR $d"
      if [ -d "$d" ]; then
        find "$d" -maxdepth 3 -type f 2>/dev/null | grep -Ei 'wlanmdsp|wlan|bdwlan|regdb|modem|mba|mdt|b[0-9][0-9]' | head -n 200
      else
        echo "missing"
      fi
    done
    echo "A90_V1753_FIRMWARE_SNAPSHOT_END"
  }} > "$FW.tmp"
  mv "$FW.tmp" "$FW" 2>/dev/null || true
}}

snapshot_proc() {{
  label="$1"
  pid="$2"
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  {{
    echo "A90_V1753_PROC label=$label pid=$pid uptime=$uptime"
    tr '\\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null; echo
    cat "/proc/$pid/status" 2>/dev/null | grep -E 'Name:|State:|Pid:|PPid:|Uid:|Gid:' || true
    cat "/proc/$pid/wchan" 2>/dev/null || true; echo
    ls -l "/proc/$pid/fd" 2>&1 | head -n 80 || true
  }} >> "$SNAP"
}}

attach_once() {{
  label="$1"
  pattern="$2"
  out="$OUT/$label.strace.txt"
  marker="$OUT/$label.attached"
  [ -e "$marker" ] && return 0
  pid="$(find_pid_by_cmd "$pattern" 2>/dev/null | head -n 1)"
  [ -n "$pid" ] || return 0
  snapshot_proc "$label" "$pid"
  if [ -x "$STRACE" ]; then
    "$STRACE" -f -tt -s 256 -yy -e trace=openat,read,write,sendto,recvfrom,sendmsg,recvmsg,connect,bind,ioctl,close -p "$pid" -o "$out" >> "$OUT/strace-launch.log" 2>&1 &
    spid=$!
    echo "$label $pid $spid" >> "$PIDS"
    echo "attached label=$label pid=$pid strace_pid=$spid" > "$marker"
  else
    echo "missing strace binary $STRACE" >> "$OUT/strace-launch.log"
    echo "missing" > "$marker"
  fi
}}

finish_strace() {{
  if [ -r "$PIDS" ]; then
    while read label pid spid; do
      [ -n "$spid" ] && kill "$spid" 2>/dev/null || true
    done < "$PIDS"
  fi
}}

summarize_requests() {{
  cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" 2>/dev/null | grep -Ei "$FILTER" | tail -n 1000 > "$OUT/request-lines.txt" || true
  {{
    printf 'requested_wlanmdsp='
    grep -Eiq 'wlanmdsp(\\.mbn)?' "$OUT/request-lines.txt" 2>/dev/null && echo 1 || echo 0
    printf 'requested_pd_image='
    grep -Eiq 'wlanmdsp|wlan[_/-]?pd|wlan/fw' "$OUT/request-lines.txt" 2>/dev/null && echo 1 || echo 0
    printf 'tftp_trace_lines='
    grep -Ec '.' "$OUT/tftp_server.strace.txt" 2>/dev/null || echo 0
    printf 'rmt_storage_trace_lines='
    grep -Ec '.' "$OUT/rmt_storage.strace.txt" 2>/dev/null || echo 0
    printf 'cnss_trace_lines='
    grep -Ec '.' "$OUT/cnss_daemon.strace.txt" 2>/dev/null || echo 0
    printf 'wlan0_seen='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eiq '\\bwlan0\\b' && echo 1 || echo 0
    printf 'wlfw_seen='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eiq 'wlfw|WLFW' && echo 1 || echo 0
  }} > "$REQ.tmp"
  mv "$REQ.tmp" "$REQ" 2>/dev/null || true
}}

(
  umask 022
  write_status start
  : > "$LOG"
  : > "$SNAP"
  : > "$PIDS"
  echo "A90_V1753_POSTFS_BEGIN" >> "$LOG"
  id >> "$LOG" 2>&1 || true
  cat /proc/self/attr/current >> "$LOG" 2>&1 || true
  dump_firmware_snapshot
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1753_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    attach_once tftp_server /vendor/bin/tftp_server
    attach_once rmt_storage /vendor/bin/rmt_storage
    attach_once cnss_daemon cnss-daemon
    if [ "$((i % 8))" = "0" ]; then
      dump_filtered
      dump_props
      summarize_requests
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    echo "SRC firmware_request_observer" >> "$LOG"
    cat "$REQ" >> "$LOG" 2>/dev/null || true
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    echo "A90_V1753_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  finish_strace
  sleep 1
  dump_filtered
  dump_props
  summarize_requests
  echo "A90_V1753_POSTFS_END" >> "$LOG"
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
            "prepare-v1753-magisk-module",
            "host:prepare temporary firmware-request Magisk module",
            "[dry-run] not executed\n",
            "",
            0,
            0.0,
            skipped=True,
            ok_override=True,
        )
    stage = module_stage_dir(store)
    ensure_private_dir(stage)
    strace_path = repo_path(args.strace_binary)
    if not strace_path.exists():
        raise RuntimeError(f"missing static strace binary: {strace_path}")
    write_private_text(stage / "module.prop", module_prop())
    write_private_text(stage / "post-fs-data.sh", post_fs_data_script(args.sampler_samples, args.sampler_delay_us))
    write_private_text(stage / "sepolicy.rule", sepolicy_rule())
    shutil.copy2(strace_path, stage / "a90_strace")
    (stage / "post-fs-data.sh").chmod(0o700)
    (stage / "a90_strace").chmod(0o700)
    (stage / "sepolicy.rule").chmod(0o600)
    text = "\n".join(
        [
            f"module_dir={stage}",
            f"strace_binary={strace_path}",
            f"samples={args.sampler_samples}",
            f"delay_us={args.sampler_delay_us}",
            "files=module.prop post-fs-data.sh sepolicy.rule a90_strace",
            "",
        ]
    )
    return v1521.write_step(
        store,
        "prepare-v1753-magisk-module",
        "host:prepare temporary firmware-request Magisk module",
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
    remote_strace = f"{REMOTE_STAGE_PREFIX}_a90_strace"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"cp {remote_quote(remote_policy)} {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"cp {remote_quote(remote_strace)} {remote_quote(REMOTE_MODULE_DIR)}/a90_strace; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh {remote_quote(REMOTE_MODULE_DIR)}/a90_strace; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)} {remote_quote(remote_policy)} {remote_quote(remote_strace)}; "
        "sync"
    )
    return [
        ("push-v1753-module-prop-android", [*v1521.adb_base(args), "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v1753-post-fs-data-android", [*v1521.adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v1753-sepolicy-android", [*v1521.adb_base(args), "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("push-v1753-strace-android", [*v1521.adb_base(args), "push", str(stage / "a90_strace"), remote_strace], args.timeout * 2),
        ("install-v1753-module-android-su", [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)], args.timeout),
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


def read_file(path: Path, limit: int = 3_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1753-wlan-pd-fwreq"
    return candidate if candidate.is_dir() else root


def parse_request_summary(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def extract_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r'"(/[^"]+)"', text):
        value = match.group(1)
        if FIRMWARE_RE.search(value) and value not in paths:
            paths.append(value)
    for match in re.finditer(r"\[(/[^]\s]+(?:wlanmdsp|wlan[_/-]?pd|firmware)[^]\s]*)\]", text, re.IGNORECASE):
        value = match.group(1)
        if value not in paths:
            paths.append(value)
    return paths[:80]


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    samples = read_file(base / "samples.log")
    dmesg = read_file(base / "dmesg-filtered.txt") + "\n" + read_file(root / "host-dmesg-filtered.txt")
    logcat = read_file(base / "logcat-filtered.txt")
    props = read_file(base / "props.txt")
    status = read_file(base / "status.txt")
    request_summary = parse_request_summary(read_file(base / "request-summary.txt"))
    tftp_trace = read_file(base / "tftp_server.strace.txt")
    rmt_trace = read_file(base / "rmt_storage.strace.txt")
    cnss_trace = read_file(base / "cnss_daemon.strace.txt")
    launch = read_file(base / "strace-launch.log")
    request_lines = read_file(base / "request-lines.txt")
    combined = "\n".join([tftp_trace, rmt_trace, cnss_trace, dmesg, logcat, request_lines])
    requested_wlanmdsp = bool(REQUEST_RE.search(combined))
    trace_lines = {
        "tftp_server": tftp_trace.count("\n"),
        "rmt_storage": rmt_trace.count("\n"),
        "cnss_daemon": cnss_trace.count("\n"),
    }
    files_present = {
        "samples": bool(samples),
        "dmesg": bool(dmesg.strip()),
        "props": bool(props),
        "status": bool(status),
        "done": (base / "done").exists(),
        "request_summary": bool(request_summary),
        "tftp_trace": bool(tftp_trace),
        "rmt_storage_trace": bool(rmt_trace),
        "cnss_trace": bool(cnss_trace),
    }
    dmesg_counts = {
        "wlfw_lines": count_lines(dmesg + "\n" + logcat, r"\bwlfw\b|WLFW"),
        "bdf_lines": count_lines(dmesg + "\n" + logcat, r"BDF file|regdb\.bin|bdwlan\.bin"),
        "wlan0_lines": count_lines(dmesg + "\n" + logcat, r"\bwlan0\b"),
    }
    return {
        "base": str(base),
        "files_present": files_present,
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1753_SAMPLE_BEGIN"),
        "sample_first_uptime": None,
        "sample_last_uptime": None,
        "request_summary": request_summary,
        "requested_wlanmdsp": "1" if requested_wlanmdsp else "0",
        "requested_pd_image": request_summary.get("requested_pd_image", "1" if requested_wlanmdsp else "0"),
        "served_path_candidates": extract_paths(combined),
        "trace_lines": trace_lines,
        "strace_launch_excerpt": launch[-4000:],
        "request_lines_excerpt": request_lines[-8000:],
        "dmesg": {
            **dmesg_counts,
            "pcie_l0_time": None,
            "wlfw_time": None,
            "bdf_time": None,
            "wlan0_time": None,
        },
        "matched_window": {
            "first_lower_time": None,
            "has_pre_lower_sample": False,
            "has_post_lower_sample": False,
            "has_pre_l0_sample": False,
            "has_post_l0_sample": False,
            "first_sample": None,
            "last_sample": None,
        },
        "props_text": props.strip(),
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
    if not base_pass:
        return (
            f"v1753-android-good-fwreq-base-failed-{base_decision}",
            False,
            "Android-good firmware-request handoff did not complete the underlying rollbackable handoff",
        )
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    if not files.get("request_summary"):
        return (
            "v1753-android-good-fwreq-capture-insufficient-rollback-pass",
            False,
            "rollback completed, but request-summary evidence was not captured",
        )
    requested = str(analysis.get("requested_wlanmdsp")) == "1" or str(analysis.get("requested_pd_image")) == "1"
    if requested:
        return (
            "v1753-android-good-firmware-request-observed-rollback-pass",
            True,
            "Android-good boot produced visible WLAN-PD firmware-request evidence and native rollback completed",
        )
    dmesg = analysis.get("dmesg") or {}
    if int(dmesg.get("wlan0_lines") or 0) > 0:
        return (
            "v1753-android-good-wlan0-without-visible-fwreq-rollback-pass",
            False,
            "Android reached wlan0 but the observer did not capture a WLAN-PD firmware request; treat as capture gap",
        )
    return (
        "v1753-android-good-no-fwreq-no-wlan0-rollback-pass",
        False,
        "Android-good reference did not capture firmware-request or wlan0 evidence",
    )


def reason_for(decision: str) -> str:
    reasons = {
        "v1753-android-good-firmware-request-observed-rollback-pass": "Android-good boot produced visible WLAN-PD firmware-request evidence and native rollback completed",
        "v1753-android-good-fwreq-capture-insufficient-rollback-pass": "rollback completed, but request-summary evidence was not captured",
        "v1753-android-good-wlan0-without-visible-fwreq-rollback-pass": "Android reached wlan0 but the observer did not capture a WLAN-PD firmware request; treat as capture gap",
        "v1753-android-good-no-fwreq-no-wlan0-rollback-pass": "Android-good reference did not capture firmware-request or wlan0 evidence",
    }
    return reasons.get(decision, decision)


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    request_summary = analysis.get("request_summary") or {}
    dmesg = analysis.get("dmesg") or {}
    trace_lines = analysis.get("trace_lines") or {}
    return "\n".join(
        [
            "# V1753 Android-good WLAN-PD Firmware-request Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Firmware-request Analysis",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["requested_wlanmdsp", analysis.get("requested_wlanmdsp")],
                    ["requested_pd_image", analysis.get("requested_pd_image")],
                    ["request_summary", json.dumps(request_summary, sort_keys=True)],
                    ["trace_lines", json.dumps(trace_lines, sort_keys=True)],
                    ["served_path_candidates", json.dumps(analysis.get("served_path_candidates") or [], sort_keys=True)],
                    ["wlfw/bdf/wlan0 lines", f"{dmesg.get('wlfw_lines')}/{dmesg.get('bdf_lines')}/{dmesg.get('wlan0_lines')}"],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
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
            "Bounded Android handoff with a temporary Magisk module and native rollback. The module writes only to `/data/local/tmp/a90-v1753-wlan-pd-fwreq`; cleanup removes that path and `/data/adb/modules/a90_v1753_fwreq` before restoring native v724. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot image handoff/rollback is performed.",
            "",
            "## Next",
            "",
            "- If this pass captures Android-good firmware-request evidence, diff it against the V1736 service-manager native route.",
            "- Stop after the diff label; do not autonomously patch served paths or trigger restart-PD.",
            "",
        ]
    )


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    decision, pass_ok, reason = classify_android(base_decision, base_pass, context) if execute else (
        "v1753-android-good-fwreq-plan-ready" if args.command == "plan" else "v1753-android-good-fwreq-dryrun-ready",
        bool(base_pass),
        "plan/dry-run completed without Android-good firmware-request live capture",
    )
    manifest = {
        "cycle": "V1753",
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
