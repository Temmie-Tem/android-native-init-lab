#!/usr/bin/env python3
"""V1979 Android producer-side QMI strace + QRTR enumeration handoff.

V1979 is the next Lead-A measurement: one rollbackable Android handoff that
captures raw AF_QIPCRTR send/receive payloads from `rild`, `cnss-daemon`, and
`pm-service`, keeps the pre-armed libqmi service lookup/send uprobes, captures
unfiltered dmesg for the wlan_pd UP anchor, and runs a bounded QRTR
nameservice matrix for DMS/NAS/WDS/WLFW without QMI payloads.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import android_ril_qmi_preup_uprobe_handoff_v1974 as v1974
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1979"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1979-android-ril-qmi-strace-qrtr-handoff")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1979_ANDROID_RIL_QMI_STRACE_QRTR_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1979-android-ril-qmi-strace-qrtr.txt")
MODULE_NAME = "a90_v1979_ril_qmi_strace_qrtr"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1979-ril-qmi-strace-qrtr"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1979_ril_qmi_strace_qrtr"
TRACEFS_GROUP = "a90rilqmi1979"
QRTR_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_qrtr_ns_probe.c")
QRTR_HELPER_BINARY = Path("tmp/wifi/v1979-build/a90_qrtr_ns_probe")

V1974_POST_FS_DATA_SCRIPT = v1974.post_fs_data_script
v1934 = v1974.v1934

ATTR_BLOCK_RE = re.compile(
    r"^A90_V1979_PID_BEGIN label=(?P<label>\S+) pid=(?P<pid>\d+) prefix=(?P<prefix>\S+)$"
)
ATTR_END_RE = re.compile(r"^A90_V1979_PID_END pid=(?P<pid>\d+)$")
TRACE_PID_RE = re.compile(r"^\s*.+-(?P<pid>\d+)\s+\[\d+\].*libqmi_")
LEAD_LOOKUP_EVENTS = {"libqmi_get_service_list_lookup_call"}
WLFW_SERVICE = 0x45


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1979 RIL QMI strace QRTR observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good libqmi pre-UP strace QRTR observer. Remove after capture.",
            "",
        ]
    )


def patch_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"post-fs-data patch anchor not found: {old[:120]!r}")
    return text.replace(old, new, 1)


def attribution_shell_functions() -> str:
    return r'''
dump_process_focus_sample() {
  label="$1"
  out="$OUT/process-census-live.txt"
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
  for proc in /proc/[0-9]*; do
    [ -d "$proc" ] || continue
    pid="$(basename "$proc")"
    comm="$(cat "$proc/comm" 2>/dev/null)"
    cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null)"
    case "$comm $cmd" in
      *rild*|*RILD*|*qcril*|*QCRIL*|*cnss-daemon*|*pm-service*|*per_mgr*|*libqmi*|*time_daemon*|*netmgrd*|*qmuxd*|*vendor_ril*|*vendor_qti*)
        attr="$(cat "$proc/attr/current" 2>/dev/null)"
        echo "A90_V1979_FOCUS|label=$label|uptime=$uptime|pid=$pid|comm=$comm|attr=$attr|cmdline=$cmd" >> "$out"
        ;;
    esac
  done
}

dump_task_map_sample() {
  label="$1"
  out="$OUT/process-task-map-live.txt"
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
  for proc in /proc/[0-9]*; do
    [ -d "$proc" ] || continue
    pid="$(basename "$proc")"
    proc_comm="$(cat "$proc/comm" 2>/dev/null)"
    cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null)"
    case "$proc_comm $cmd" in
      *rild*|*RILD*|*qcril*|*QCRIL*|*cnss-daemon*|*pm-service*|*per_mgr*|*libqmi*|*time_daemon*|*netmgrd*|*qmuxd*|*vendor_ril*|*vendor_qti*|*qtidataservices*)
        attr="$(cat "$proc/attr/current" 2>/dev/null)"
        for task in "$proc"/task/[0-9]*; do
          [ -d "$task" ] || continue
          tid="$(basename "$task")"
          task_comm="$(cat "$task/comm" 2>/dev/null)"
          echo "A90_V1979_TASK|label=$label|uptime=$uptime|pid=$pid|tid=$tid|proc_comm=$proc_comm|thread_comm=$task_comm|attr=$attr|cmdline=$cmd" >> "$out"
        done
        ;;
    esac
  done
}

dump_pid_task_map_sample() {
  label="$1"
  pid="$2"
  out="$OUT/process-task-map-live.txt"
  proc="/proc/$pid"
  [ -d "$proc" ] || return 0
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
  proc_comm="$(cat "$proc/comm" 2>/dev/null)"
  cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null)"
  attr="$(cat "$proc/attr/current" 2>/dev/null)"
  for task in "$proc"/task/[0-9]*; do
    [ -d "$task" ] || continue
    tid="$(basename "$task")"
    task_comm="$(cat "$task/comm" 2>/dev/null)"
    echo "A90_V1979_TASK|label=$label|uptime=$uptime|pid=$pid|tid=$tid|proc_comm=$proc_comm|thread_comm=$task_comm|attr=$attr|cmdline=$cmd" >> "$out"
  done
}

dump_named_task_map_sample() {
  label="$1"
  seen=""
  for name in rild cnss-daemon pm-service; do
    for pid in $(pidof "$name" 2>/dev/null); do
      case " $seen " in
        *" $pid "*) ;;
        *) seen="$seen $pid"; dump_pid_task_map_sample "$label" "$pid" ;;
      esac
    done
  done
}

start_process_focus_sampler() {
  (
    j=0
    while [ "$j" -lt 160 ]; do
      dump_named_task_map_sample "early-$j"
      j=$((j + 1))
      sleep 0.050 2>/dev/null || usleep 50000 2>/dev/null || sleep 1
    done
  ) &
  echo "$!" > "$OUT/process-focus-sampler.pid"
}

attach_focus_daemons_once() {
  attach_once rild /vendor/bin/hw/rild
  attach_once cnss_daemon cnss-daemon
  attach_once pm_service /vendor/bin/pm-service
}

start_strace_attach_sampler() {
  (
    j=0
    while [ "$j" -lt 220 ]; do
      attach_focus_daemons_once
      j=$((j + 1))
      sleep 0.050 2>/dev/null || usleep 50000 2>/dev/null || sleep 1
    done
  ) &
  echo "$!" > "$OUT/strace-attach-sampler.pid"
}

run_qrtr_lookup_case() {
  label="$1"
  service="$2"
  instance="$3"
  wildcard="$4"
  out="$OUT/qrtr-lookup-matrix.txt"
  echo "A90_V1979_QRTR_BEGIN label=$label service=$service instance=$instance uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')" >> "$out"
  if [ -x "$MOD/a90_qrtr_ns_probe" ]; then
    if [ "$wildcard" = "1" ]; then
      "$MOD/a90_qrtr_ns_probe" --service "$service" --instance "$instance" --allow-qrtr-ns-transmit --allow-wildcard-lookup --readback-ms 700 --max-events 64 >> "$out" 2>&1 || true
    else
      "$MOD/a90_qrtr_ns_probe" --service "$service" --instance "$instance" --allow-qrtr-ns-transmit --readback-ms 700 --max-events 64 >> "$out" 2>&1 || true
    fi
  else
    echo "qrtr_ns.status=missing-helper" >> "$out"
  fi
  echo "A90_V1979_QRTR_END label=$label uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')" >> "$out"
}

run_qrtr_lookup_matrix_once() {
  marker="$OUT/qrtr-lookup-matrix.done"
  [ -e "$marker" ] && return 0
  : > "$OUT/qrtr-lookup-matrix.txt"
  run_qrtr_lookup_case wildcard 0 0 1
  run_qrtr_lookup_case wds0 1 0 0
  run_qrtr_lookup_case wds1 1 1 0
  run_qrtr_lookup_case dms0 2 0 0
  run_qrtr_lookup_case dms1 2 1 0
  run_qrtr_lookup_case nas0 3 0 0
  run_qrtr_lookup_case nas1 3 1 0
  run_qrtr_lookup_case wlfw0 69 0 0
  run_qrtr_lookup_case wlfw1 69 1 0
  echo done > "$marker"
}

start_qrtr_lookup_matrix_sampler() {
  ( run_qrtr_lookup_matrix_once ) &
  echo "$!" > "$OUT/qrtr-lookup-matrix.pid"
}

dump_process_census() {
  label="$1"
  out="$OUT/process-census-$label.txt"
  {
    echo "A90_V1979_CENSUS label=$label uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
    ps -A -T -o PID,TID,PPID,NAME,CMD 2>&1 || ps -AT 2>&1 || ps -A 2>&1 || true
    echo "A90_V1979_PROC_SCAN"
    for proc in /proc/[0-9]*; do
      [ -d "$proc" ] || continue
      pid="$(basename "$proc")"
      comm="$(cat "$proc/comm" 2>/dev/null)"
      cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null)"
      case "$comm $cmd" in
        *rild*|*RILD*|*qcril*|*QCRIL*|*cnss-daemon*|*pm-service*|*per_mgr*|*libqmi*|*time_daemon*|*netmgrd*|*qmuxd*)
          echo "pid=$pid comm=$comm cmdline=$cmd attr=$(cat "$proc/attr/current" 2>/dev/null)"
          ;;
      esac
    done
  } > "$out.tmp" 2>&1
  mv "$out.tmp" "$out" 2>/dev/null || true
}

dump_one_pid_attr() {
  label="$1"
  pid="$2"
  prefix="$3"
  out="$LIBQMI_ATTR"
  echo "A90_V1979_PID_BEGIN label=$label pid=$pid prefix=$prefix" >> "$out"
  if [ -d "/proc/$pid" ]; then
    echo "exists=1" >> "$out"
    status="$(cat "/proc/$pid/status" 2>/dev/null)"
    echo "$status" | sed -n \
      -e 's/^Name:[[:space:]]*/name=/p' \
      -e 's/^State:[[:space:]]*/state=/p' \
      -e 's/^Tgid:[[:space:]]*/tgid=/p' \
      -e 's/^Pid:[[:space:]]*/pid_status=/p' \
      -e 's/^PPid:[[:space:]]*/ppid=/p' \
      -e 's/^Uid:[[:space:]]*/uid=/p' \
      -e 's/^Gid:[[:space:]]*/gid=/p' >> "$out"
    echo "comm=$(cat "/proc/$pid/comm" 2>/dev/null)" >> "$out"
    echo "cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)" >> "$out"
    echo "attr=$(cat "/proc/$pid/attr/current" 2>/dev/null)" >> "$out"
    echo "wchan=$(cat "/proc/$pid/wchan" 2>/dev/null)" >> "$out"
    echo "exe=$(readlink "/proc/$pid/exe" 2>/dev/null)" >> "$out"
    echo "cgroup=$(tr '\n' ';' < "/proc/$pid/cgroup" 2>/dev/null)" >> "$out"
    echo "maps_focus_begin=1" >> "$out"
    grep -Ei 'libqmi|libsec-ril|rild|cnss|pm-service|per_mgr|qmux|netmgr|time_daemon' "/proc/$pid/maps" 2>/dev/null | head -n 40 | sed 's/^/map=/' >> "$out" || true
    echo "maps_focus_end=1" >> "$out"
  else
    echo "exists=0" >> "$out"
  fi
  if [ -r "$LIBQMI_UPROBE" ]; then
    awk -v pid="$pid" '$0 ~ ("-" pid " +\\[[0-9]+\\].*libqmi_") {print "trace_line=" $0}' "$LIBQMI_UPROBE" 2>/dev/null | tail -n 24 >> "$out" || true
  fi
  echo "A90_V1979_PID_END pid=$pid" >> "$out"
}

dump_libqmi_strace_qrtr() {
  label="$1"
  [ -r "$LIBQMI_UPROBE" ] || return 0
  echo "A90_V1979_ATTR_BEGIN label=$label uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')" >> "$LIBQMI_ATTR"
  awk '/libqmi_/ { split($1, a, "-"); if (a[length(a)] ~ /^[0-9]+$/) print a[length(a)] }' "$LIBQMI_UPROBE" 2>/dev/null | sort -n | uniq | head -n 256 > "$LIBQMI_ALL_PIDS.tmp" || true
  grep -E 'libqmi_get_service_list_lookup_call:.*svc_id=(0x2|2|0x3|3|0x16|22|0x45|69)|libqmi_send_' "$LIBQMI_UPROBE" 2>/dev/null | awk '{ split($1, a, "-"); if (a[length(a)] ~ /^[0-9]+$/) print a[length(a)] }' | sort -n | uniq | head -n 128 > "$LIBQMI_FOCUS_PIDS.tmp" || true
  cat "$LIBQMI_FOCUS_PIDS.tmp" "$LIBQMI_ALL_PIDS.tmp" 2>/dev/null | sort -n | uniq | head -n 256 > "$LIBQMI_ALL_PIDS"
  for pid in $(cat "$LIBQMI_ALL_PIDS" 2>/dev/null); do
    [ -n "$pid" ] || continue
    dump_one_pid_attr "$label" "$pid" thread
    tgid="$(sed -n 's/^Tgid:[[:space:]]*//p' "/proc/$pid/status" 2>/dev/null | head -n 1)"
    if [ -n "$tgid" ] && [ "$tgid" != "$pid" ]; then
      dump_one_pid_attr "$label" "$tgid" tgid
    fi
  done
  rm -f "$LIBQMI_ALL_PIDS.tmp" "$LIBQMI_FOCUS_PIDS.tmp" 2>/dev/null || true
  echo "A90_V1979_ATTR_END label=$label" >> "$LIBQMI_ATTR"
}
'''


def post_fs_data_script(samples: int, delay_us: int) -> str:
    text = V1974_POST_FS_DATA_SCRIPT(samples, delay_us)
    text = text.replace(
        '"$STRACE" -f -tt -s 256 -e trace=openat,read,write,sendto,recvfrom,sendmsg,recvmsg,connect,bind,ioctl,close -p "$pid" -o "$out"',
        '"$STRACE" -f -tt -s 9999 -xx -e trace=sendmsg,recvmsg,sendto,recvfrom -p "$pid" -o "$out"',
        1,
    )
    text = patch_once(
        text,
        'STRACE="$MOD/a90_strace"\n',
        'STRACE="$MOD/a90_strace"\nQRTR_HELPER="$MOD/a90_qrtr_ns_probe"\n',
    )
    text = patch_once(
        text,
        'DMESG="$OUT/dmesg-filtered.txt"\n',
        'DMESG="$OUT/dmesg-filtered.txt"\nDMESG_ALL="$OUT/dmesg-unfiltered.txt"\n',
    )
    text = patch_once(
        text,
        '  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 2000 > "$DMESG.tmp" || true\n',
        '  dmesg 2>&1 > "$DMESG_ALL.tmp" || true\n'
        '  mv "$DMESG_ALL.tmp" "$DMESG_ALL" 2>/dev/null || true\n'
        '  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 2000 > "$DMESG.tmp" || true\n',
    )
    text = patch_once(
        text,
        'LIBQMI_UPROBE_SUMMARY="$OUT/libqmi-uprobe-summary.txt"\nTRACE_EVENTS=',
        'LIBQMI_UPROBE_SUMMARY="$OUT/libqmi-uprobe-summary.txt"\n'
        'LIBQMI_ATTR="$OUT/libqmi-strace-qrtr.txt"\n'
        'LIBQMI_ALL_PIDS="$OUT/libqmi-attribution-pids.txt"\n'
        'TRACE_EVENTS=',
    )
    text = patch_once(
        text,
        "\n(\n  trap uprobe_cleanup EXIT INT TERM\n",
        "\n" + attribution_shell_functions() + "\n(\n  trap uprobe_cleanup EXIT INT TERM\n",
    )
    text = patch_once(
        text,
        '  : > "$LIBQMI_UPROBE"\n  : > "$LIBQMI_UPROBE_SUMMARY"\n',
        '  : > "$LIBQMI_UPROBE"\n  : > "$LIBQMI_UPROBE_SUMMARY"\n  : > "$LIBQMI_ATTR"\n  : > "$LIBQMI_ALL_PIDS"\n  : > "$OUT/process-census-live.txt"\n  : > "$OUT/process-task-map-live.txt"\n',
    )
    text = patch_once(
        text,
        "  arm_qrtr_kprobes\n  dump_tracefs_catalog\n",
        "  arm_qrtr_kprobes\n  start_strace_attach_sampler\n  start_process_focus_sampler\n  start_qrtr_lookup_matrix_sampler\n  dump_process_census early\n  dump_tracefs_catalog\n",
    )
    text = patch_once(
        text,
        "    attach_once tftp_server /vendor/bin/tftp_server\n    attach_once rmt_storage /vendor/bin/rmt_storage\n    attach_once cnss_daemon cnss-daemon\n",
        "    attach_focus_daemons_once\n",
    )
    text = patch_once(
        text,
        "    echo \"A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime\" >> \"$LOG\"\n",
        "    echo \"A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime\" >> \"$LOG\"\n"
        "    dump_named_task_map_sample \"sample-$i\"\n"
        "    dump_libqmi_strace_qrtr \"sample-$i\"\n",
    )
    text = patch_once(
        text,
        "      dump_cnss_qrtr_trace\n      summarize_requests\n",
        "      dump_cnss_qrtr_trace\n      summarize_requests\n",
    )
    text = patch_once(
        text,
        "  dump_cnss_qrtr_trace\n  summarize_requests\n",
        "  dump_cnss_qrtr_trace\n  dump_libqmi_strace_qrtr final\n  dump_process_census late\n  summarize_requests\n",
    )
    text = patch_once(
        text,
        'cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" "$UPROBE" "$CNSS_UPROBE" "$QRTR_TRACE" "$LIBQMI_UPROBE" 2>/dev/null',
        'cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" "$UPROBE" "$CNSS_UPROBE" "$QRTR_TRACE" "$LIBQMI_UPROBE" "$LIBQMI_ATTR" 2>/dev/null',
    )
    text = patch_once(
        text,
        "    printf 'libqmi_uprobe_trace_lines='\n    count_nonempty_lines \"$LIBQMI_UPROBE\"\n",
        "    printf 'libqmi_uprobe_trace_lines='\n    count_nonempty_lines \"$LIBQMI_UPROBE\"\n"
        "    printf 'libqmi_strace_qrtr_lines='\n    count_nonempty_lines \"$LIBQMI_ATTR\"\n",
    )
    return text


def read_file(path: Path, limit: int = 8_000_000) -> str:
    return v1974.read_file(path, limit=limit)


def build_qrtr_helper() -> Path:
    source = repo_path(QRTR_HELPER_SOURCE)
    output = repo_path(QRTR_HELPER_BINARY)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.stat().st_mtime >= source.stat().st_mtime:
        return output
    subprocess.run(
        [
            "aarch64-linux-gnu-gcc",
            "-static",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(output),
            str(source),
        ],
        check=True,
    )
    subprocess.run(["aarch64-linux-gnu-strip", str(output)], check=True)
    return output


def prepare_module(store: EvidenceStore, args: Any, execute: bool) -> Any:
    step = v1934.base.prepare_module(store, args, execute)
    if execute:
        helper = build_qrtr_helper()
        stage = v1934.base.module_stage_dir(store)
        shutil.copy2(helper, stage / "a90_qrtr_ns_probe")
        (stage / "a90_qrtr_ns_probe").chmod(0o700)
    return step


def install_module_android_steps(args: Any, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    stage = v1934.base.module_stage_dir(store)
    remote_quote = v1934.base.remote_quote
    remote_prop = f"{REMOTE_STAGE_PREFIX}_module.prop"
    remote_postfs = f"{REMOTE_STAGE_PREFIX}_post-fs-data.sh"
    remote_policy = f"{REMOTE_STAGE_PREFIX}_sepolicy.rule"
    remote_strace = f"{REMOTE_STAGE_PREFIX}_a90_strace"
    remote_qrtr = f"{REMOTE_STAGE_PREFIX}_a90_qrtr_ns_probe"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"cp {remote_quote(remote_policy)} {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"cp {remote_quote(remote_strace)} {remote_quote(REMOTE_MODULE_DIR)}/a90_strace; "
        f"cp {remote_quote(remote_qrtr)} {remote_quote(REMOTE_MODULE_DIR)}/a90_qrtr_ns_probe; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh {remote_quote(REMOTE_MODULE_DIR)}/a90_strace {remote_quote(REMOTE_MODULE_DIR)}/a90_qrtr_ns_probe; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)} {remote_quote(remote_policy)} {remote_quote(remote_strace)} {remote_quote(remote_qrtr)}; "
        "sync"
    )
    adb_base = v1934.base.v1521.adb_base(args)
    shlex_quote = v1934.base.shlex.quote
    return [
        ("push-v1979-module-prop-android", [*adb_base, "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v1979-post-fs-data-android", [*adb_base, "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v1979-sepolicy-android", [*adb_base, "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("push-v1979-strace-android", [*adb_base, "push", str(stage / "a90_strace"), remote_strace], args.timeout * 2),
        ("push-v1979-qrtr-helper-android", [*adb_base, "push", str(stage / "a90_qrtr_ns_probe"), remote_qrtr], args.timeout * 2),
        ("install-v1979-module-android-su", [*adb_base, "shell", "su", "-c", shlex_quote(install_shell)], args.timeout),
    ]


def configure_v1979_v1521_engine() -> None:
    v1934.base.v1521.prepare_module = prepare_module
    v1934.base.v1521.install_module_android_steps = install_module_android_steps


def parse_attribution_blocks(text: str) -> dict[int, dict[str, Any]]:
    by_pid: dict[int, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        begin = ATTR_BLOCK_RE.match(raw_line)
        if begin:
            current = {
                "pid": int(begin.group("pid")),
                "labels": [begin.group("label")],
                "prefixes": [begin.group("prefix")],
                "trace_lines": [],
            }
            continue
        if current is None:
            continue
        if ATTR_END_RE.match(raw_line):
            pid = int(current["pid"])
            existing = by_pid.get(pid)
            if existing:
                existing["labels"] = sorted(set(existing.get("labels", []) + current.get("labels", [])))
                existing["prefixes"] = sorted(set(existing.get("prefixes", []) + current.get("prefixes", [])))
                existing["trace_lines"] = (existing.get("trace_lines", []) + current.get("trace_lines", []))[-32:]
                for key, value in current.items():
                    if key not in {"pid", "labels", "prefixes", "trace_lines"} and value:
                        existing.setdefault(key, value)
            else:
                by_pid[pid] = current
            current = None
            continue
        if raw_line.startswith("trace_line="):
            current.setdefault("trace_lines", []).append(raw_line[len("trace_line="):])
            continue
        if "=" in raw_line:
            key, value = raw_line.split("=", 1)
            if key == "map":
                current.setdefault("maps", []).append(value)
            else:
                current[key] = value
    return by_pid


def parse_focus_census(text: str) -> dict[int, dict[str, Any]]:
    by_pid: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        if not line.startswith("A90_V1979_FOCUS|"):
            continue
        fields: dict[str, str] = {}
        for part in line.split("|")[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key] = value
        try:
            pid = int(fields.get("pid", "0"))
        except ValueError:
            continue
        if pid <= 0:
            continue
        item = by_pid.setdefault(pid, {"pid": pid, "labels": [], "prefixes": ["live-focus"], "trace_lines": []})
        if fields.get("label"):
            item["labels"] = sorted(set(item.get("labels", []) + [fields["label"]]))
        for key in ("comm", "cmdline", "attr", "uptime"):
            if fields.get(key) and not item.get(key):
                item[key] = fields[key]
    return by_pid


def parse_task_map(text: str) -> dict[int, dict[str, Any]]:
    by_pid: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        if not line.startswith("A90_V1979_TASK|"):
            continue
        fields: dict[str, str] = {}
        for part in line.split("|")[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key] = value
        try:
            pid = int(fields.get("pid", "0"))
            tid = int(fields.get("tid", "0"))
        except ValueError:
            continue
        if pid <= 0 or tid <= 0:
            continue
        label = fields.get("label")
        thread_item = by_pid.setdefault(
            tid,
            {"pid": tid, "labels": [], "prefixes": ["live-task"], "trace_lines": []},
        )
        if label:
            thread_item["labels"] = sorted(set(thread_item.get("labels", []) + [label]))
        thread_item.setdefault("tgid", str(pid))
        if fields.get("thread_comm") and not thread_item.get("comm"):
            thread_item["comm"] = fields["thread_comm"]
        for key in ("cmdline", "attr", "uptime"):
            if fields.get(key) and not thread_item.get(key):
                thread_item[key] = fields[key]

        proc_item = by_pid.setdefault(
            pid,
            {"pid": pid, "labels": [], "prefixes": ["live-task-tgid"], "trace_lines": []},
        )
        if label:
            proc_item["labels"] = sorted(set(proc_item.get("labels", []) + [label]))
        proc_item.setdefault("tgid", str(pid))
        if fields.get("proc_comm") and not proc_item.get("comm"):
            proc_item["comm"] = fields["proc_comm"]
        for key in ("cmdline", "attr", "uptime"):
            if fields.get(key) and not proc_item.get(key):
                proc_item[key] = fields[key]
    return by_pid


def merge_attribution(primary: dict[int, dict[str, Any]],
                      fallback: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    merged = dict(primary)
    for pid, item in fallback.items():
        current = merged.get(pid)
        if not current:
            merged[pid] = item
            continue
        current["labels"] = sorted(set(current.get("labels", []) + item.get("labels", [])))
        current["prefixes"] = sorted(set(current.get("prefixes", []) + item.get("prefixes", [])))
        for key, value in item.items():
            if key not in {"pid", "labels", "prefixes", "trace_lines"} and value and not current.get(key):
                current[key] = value
    return merged


def attr_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "unattributed"
    cmdline = str(item.get("cmdline") or "").strip()
    comm = str(item.get("comm") or item.get("name") or "").strip()
    exe = str(item.get("exe") or "").strip()
    attr = str(item.get("attr") or "").strip()
    if cmdline:
        return cmdline[:140]
    if exe:
        return exe[:140]
    if comm:
        return comm[:80]
    if attr:
        return attr[:100]
    return "unattributed"


def attr_is_rild(item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    joined = " ".join(str(item.get(key) or "") for key in ("cmdline", "comm", "name", "exe", "attr"))
    return bool(v1974.RIL_COMM_RE.search(joined))


def find_tgid_attr(pid: int, attribution: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    item = attribution.get(pid)
    if not item:
        return None
    try:
        tgid = int(str(item.get("tgid") or "0"))
    except ValueError:
        return item
    return attribution.get(tgid) or item


def summarize_strace_qrtr(
    events: list[dict[str, Any]],
    wlan_pd_time: float | None,
    attribution: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    def before_up(event: dict[str, Any]) -> bool:
        return wlan_pd_time is not None and event["time"] < wlan_pd_time

    lead_lookup_pre = [
        event
        for event in events
        if event["event"] in LEAD_LOOKUP_EVENTS
        and event["fields"].get("svc_id") in v1974.LEAD_SERVICES
        and before_up(event)
    ]
    wlfw_lookup_pre = [
        event
        for event in events
        if event["event"] in LEAD_LOOKUP_EVENTS
        and event["fields"].get("svc_id") == WLFW_SERVICE
        and before_up(event)
    ]
    attributed_rows: list[dict[str, Any]] = []
    process_counts: Counter[str] = Counter()
    rild_count = 0
    unresolved_count = 0
    for event in lead_lookup_pre:
        thread_attr = attribution.get(int(event["pid"]))
        process_attr = find_tgid_attr(int(event["pid"]), attribution)
        label = attr_label(process_attr or thread_attr)
        if label == "unattributed":
            unresolved_count += 1
        if attr_is_rild(process_attr) or attr_is_rild(thread_attr):
            rild_count += 1
        process_counts[label] += 1
        attributed_rows.append(
            {
                "time": event["time"],
                "pid": event["pid"],
                "svc_id": event["fields"].get("svc_id"),
                "service": v1974.service_name(event["fields"].get("svc_id", -1)),
                "thread": attr_label(thread_attr),
                "process": label,
                "rild": attr_is_rild(process_attr) or attr_is_rild(thread_attr),
                "line": event["line"],
            }
        )
    first = attributed_rows[0] if attributed_rows else {}
    return {
        "attribution_pid_count": len(attribution),
        "lead_lookup_pre_count": len(lead_lookup_pre),
        "wlfw_lookup_pre_count": len(wlfw_lookup_pre),
        "lead_lookup_pre_rild_count": rild_count,
        "lead_lookup_pre_unresolved_count": unresolved_count,
        "lead_lookup_pre_process_counts": dict(process_counts.most_common(12)),
        "first_lead_lookup_pre": first,
        "lead_lookup_pre_rows": attributed_rows[:24],
    }


def summarize_daemon_strace(evidence_dir: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for label, filename in {
        "rild": "rild.strace.txt",
        "cnss_daemon": "cnss_daemon.strace.txt",
        "pm_service": "pm_service.strace.txt",
    }.items():
        text = read_file(evidence_dir / filename, limit=12_000_000)
        lines = [line for line in text.splitlines() if line.strip()]
        summary[label] = {
            "present": bool(text),
            "lines": len(lines),
            "sendmsg": sum("sendmsg(" in line for line in lines),
            "recvmsg": sum("recvmsg(" in line for line in lines),
            "sendto": sum("sendto(" in line for line in lines),
            "recvfrom": sum("recvfrom(" in line for line in lines),
            "hex_escaped_lines": sum("\\x" in line for line in lines),
            "sockaddr_qrtr_lines": sum("AF_QIPCRTR" in line or "sq_node" in line or "sq_port" in line for line in lines),
            "first_payload_line": next((line[:500] for line in lines if "\\x" in line), ""),
        }
    launch = read_file(evidence_dir / "strace-launch.log")
    summary["launch_lines"] = len([line for line in launch.splitlines() if line.strip()])
    summary["launch_excerpt"] = launch[-2000:]
    return summary


def parse_qrtr_lookup_matrix(text: str) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        begin = re.match(r"^A90_V1979_QRTR_BEGIN label=(\S+) service=(\d+) instance=(\d+) uptime=(\S+)", line)
        if begin:
            current = {
                "label": begin.group(1),
                "service": int(begin.group(2)),
                "instance": int(begin.group(3)),
                "uptime_start": begin.group(4),
                "keys": {},
                "events": [],
            }
            continue
        end = re.match(r"^A90_V1979_QRTR_END label=(\S+) uptime=(\S+)", line)
        if end and current is not None:
            current["uptime_end"] = end.group(2)
            cases.append(current)
            current = None
            continue
        if current is None:
            continue
        if line.startswith("qrtr_ns.event.") and "=" in line:
            key, value = line.split("=", 1)
            current["events"].append((key, value))
        elif line.startswith("qrtr_ns.") and "=" in line:
            key, value = line.split("=", 1)
            current["keys"][key[len("qrtr_ns."):]] = value
    service_events = []
    for case in cases:
        keys = case.get("keys") or {}
        try:
            count = int(keys.get("readback.service_events", "0"), 0)
        except ValueError:
            count = 0
        if count > 0:
            service_events.append(
                {
                    "label": case.get("label"),
                    "service": case.get("service"),
                    "instance": case.get("instance"),
                    "service_events": count,
                }
            )
    return {
        "present": bool(text),
        "case_count": len(cases),
        "service_event_cases": service_events,
        "labels": [str(case.get("label")) for case in cases],
        "all_statuses": {str(case.get("label")): (case.get("keys") or {}).get("status") for case in cases},
    }


def analyze_pulled_evidence(store: v1934.EvidenceStore) -> dict[str, Any]:
    analysis = v1974.analyze_pulled_evidence(store)
    evidence_dir = v1934.base.evidence_base(store)
    libqmi_trace = read_file(evidence_dir / "libqmi-uprobe-trace.txt")
    attribution_text = read_file(evidence_dir / "libqmi-strace-qrtr.txt")
    focus_text = read_file(evidence_dir / "process-census-live.txt")
    task_text = read_file(evidence_dir / "process-task-map-live.txt")
    qrtr_text = read_file(evidence_dir / "qrtr-lookup-matrix.txt", limit=32_000_000)
    dmesg_unfiltered = read_file(evidence_dir / "dmesg-unfiltered.txt", limit=12_000_000)
    dmesg = analysis.get("dmesg") or {}
    wlan_pd_time = dmesg.get("wlan_pd_indication_time_s")
    events = v1974.trace_events(libqmi_trace)
    attribution = merge_attribution(parse_attribution_blocks(attribution_text), parse_task_map(task_text))
    attribution = merge_attribution(attribution, parse_focus_census(focus_text))
    analysis["v1979_attribution"] = summarize_strace_qrtr(events, wlan_pd_time, attribution)
    analysis["v1979_attribution"]["attribution_file_present"] = bool(attribution_text)
    analysis["v1979_attribution"]["focus_census_file_present"] = bool(focus_text)
    analysis["v1979_attribution"]["task_map_file_present"] = bool(task_text)
    analysis["v1979_daemon_strace"] = summarize_daemon_strace(evidence_dir)
    analysis["v1979_qrtr_lookup"] = parse_qrtr_lookup_matrix(qrtr_text)
    analysis["v1979_unfiltered_dmesg"] = {
        "present": bool(dmesg_unfiltered),
        "lines": len(dmesg_unfiltered.splitlines()),
        "wlan_pd_lines": sum("wlan_pd" in line for line in dmesg_unfiltered.splitlines()),
        "wlan0_lines": sum("wlan0" in line for line in dmesg_unfiltered.splitlines()),
    }
    return analysis


def stateup_complete(analysis: dict[str, Any]) -> bool:
    return v1974.stateup_complete(analysis)


def contaminated(analysis: dict[str, Any]) -> bool:
    return v1974.contaminated(analysis)


def classify_result(
    base_decision: str,
    base_pass: bool,
    context: dict[str, Any],
    parser_results: dict[str, Any],
    selftest_ok: bool,
) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return "v1979-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed"
    if not base_pass:
        return f"v1979-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed"
    analysis = context.get("analysis") or {}
    if contaminated(analysis):
        return (
            "v1979-android-capture-rejected-degraded-or-pcie-mhi",
            False,
            "Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination",
            "android-capture-rejected-degraded-or-pcie-mhi",
        )
    if not stateup_complete(analysis):
        return (
            "v1979-android-normal-stateup-incomplete-rollback-pass",
            False,
            "capture does not contain the normal PM vote -> wlan_pd -> wlanmdsp -> wlan0 state-up sequence",
            "android-normal-stateup-incomplete",
        )
    parser_ok = bool((parser_results.get("v1894") or {}).get("pass")) and bool((parser_results.get("v1888") or {}).get("pass"))
    if not parser_ok:
        return "v1979-parser-chain-failed-rollback-pass", False, "Android capture succeeded but V1894/V1888 parser chain did not pass", "parser-chain-failed"

    uprobe = analysis.get("v1974_uprobe") or {}
    attribution = analysis.get("v1979_attribution") or {}
    daemon_strace = analysis.get("v1979_daemon_strace") or {}
    qrtr_lookup = analysis.get("v1979_qrtr_lookup") or {}
    if int(uprobe.get("send_event_count") or 0) <= 0:
        return (
            "v1979-libqmi-uprobe-incomplete-rollback-pass",
            False,
            "normal Android state-up completed, but libqmi uprobes did not produce send events",
            "libqmi-uprobe-incomplete",
        )
    if not all((daemon_strace.get(name) or {}).get("present") for name in ("rild", "cnss_daemon", "pm_service")):
        return (
            "v1979-daemon-strace-incomplete-rollback-pass",
            False,
            "normal Android state-up completed, but one or more rild/cnss-daemon/pm-service strace files were absent",
            "daemon-strace-incomplete",
        )
    if not qrtr_lookup.get("present") or int(qrtr_lookup.get("case_count") or 0) <= 0:
        return (
            "v1979-qrtr-lookup-missing-rollback-pass",
            False,
            "normal Android state-up completed, but the QRTR lookup matrix was absent",
            "qrtr-lookup-missing",
        )
    if int(attribution.get("lead_lookup_pre_count") or 0) <= 0:
        return (
            "v1979-no-preup-dms-nas-wds-lookup-regression-rollback-pass",
            False,
            "normal Android state-up completed, but the V1974 pre-UP DMS/NAS/WDS lookup edge did not reproduce",
            "preup-lead-lookup-regression",
        )
    if int(attribution.get("lead_lookup_pre_rild_count") or 0) > 0:
        return (
            "v1979-ril-strace-qrtr-preup-dms-nas-wds-attributed-rild-rollback-pass",
            True,
            "daemon strace and QRTR lookup captured; pre-UP DMS/NAS/WDS libqmi lookup thread was attributed to rild",
            "ril-strace-qrtr-preup-lead-lookup-attributed-rild",
        )
    if int(attribution.get("lead_lookup_pre_unresolved_count") or 0) < int(attribution.get("lead_lookup_pre_count") or 0):
        return (
            "v1979-ril-strace-qrtr-preup-dms-nas-wds-attributed-non-rild-rollback-pass",
            True,
            "daemon strace and QRTR lookup captured; pre-UP DMS/NAS/WDS libqmi lookup thread was attributed, but not to rild",
            "ril-strace-qrtr-preup-lead-lookup-attributed-non-rild",
        )
    if attribution.get("attribution_file_present"):
        return (
            "v1979-ril-strace-qrtr-preup-dms-nas-wds-attribution-unresolved-rollback-pass",
            True,
            "daemon strace and QRTR lookup captured; pre-UP DMS/NAS/WDS lookup reproduced, but live attribution could not resolve the process",
            "ril-strace-qrtr-preup-lead-lookup-attribution-unresolved",
        )
    return (
        "v1979-strace-qrtr-file-missing-rollback-pass",
        False,
        "normal Android state-up and pre-UP lookup reproduced, but strace QRTR file was absent",
        "strace-qrtr-missing",
    )


def render_attribution_rows(attribution: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in attribution.get("lead_lookup_pre_rows", [])[:8]:
        rows.append(
            [
                str(item.get("time")),
                str(item.get("pid")),
                str(item.get("service")),
                str(item.get("rild")),
                str(item.get("process"))[:160],
            ]
        )
    return rows or [["none", "none", "none", "none", "none"]]


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    uprobe = analysis.get("v1974_uprobe") or {}
    attribution = analysis.get("v1979_attribution") or {}
    daemon_strace = analysis.get("v1979_daemon_strace") or {}
    qrtr_lookup = analysis.get("v1979_qrtr_lookup") or {}
    unfiltered_dmesg = analysis.get("v1979_unfiltered_dmesg") or {}
    parser_results = manifest.get("parser_results") or {}
    rows = [
        ["wlan_pd UP", dmesg.get("wlan_pd_indication_time_s")],
        ["wlan0", dmesg.get("wlan0_time_s")],
        ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
        ["libqmi events/send/rild-send", f"{uprobe.get('libqmi_event_count')}/{uprobe.get('send_event_count')}/{uprobe.get('rild_send_event_count')}"],
        ["daemon strace lines", json.dumps({name: (daemon_strace.get(name) or {}).get("lines") for name in ("rild", "cnss_daemon", "pm_service")}, sort_keys=True)],
        ["daemon strace send/recv", json.dumps({name: {"sendmsg": (daemon_strace.get(name) or {}).get("sendmsg"), "recvmsg": (daemon_strace.get(name) or {}).get("recvmsg")} for name in ("rild", "cnss_daemon", "pm_service")}, sort_keys=True)],
        ["QRTR lookup cases", qrtr_lookup.get("case_count")],
        ["QRTR service cases", json.dumps(qrtr_lookup.get("service_event_cases") or [], sort_keys=True)[:900]],
        ["unfiltered dmesg lines", unfiltered_dmesg.get("lines")],
        ["pre-UP lead lookups", attribution.get("lead_lookup_pre_count")],
        ["pre-UP WLFW lookups", attribution.get("wlfw_lookup_pre_count")],
        ["attributed PIDs", attribution.get("attribution_pid_count")],
        ["pre-UP lead rild count", attribution.get("lead_lookup_pre_rild_count")],
        ["pre-UP lead unresolved count", attribution.get("lead_lookup_pre_unresolved_count")],
        ["task map present", attribution.get("task_map_file_present")],
        ["process counts", json.dumps(attribution.get("lead_lookup_pre_process_counts") or {}, sort_keys=True)],
        ["first lead lookup", json.dumps(attribution.get("first_lead_lookup_pre") or {}, sort_keys=True)[:900]],
    ]
    return "\n".join(
        [
            "# Native Init V1979 Android RIL QMI Strace QRTR",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Producer Attribution",
            "",
            markdown_table(["field", "value"], [[str(cell) for cell in row] for row in rows]),
            "",
            "## Pre-UP Lead Rows",
            "",
            markdown_table(["time", "pid", "service", "rild", "process"], render_attribution_rows(attribution)),
            "",
            "## Parser Chain",
            "",
            markdown_table(
                ["parser", "decision", "label", "pass", "out_dir"],
                [
                    [
                        "V1894",
                        (parser_results.get("v1894") or {}).get("decision"),
                        (parser_results.get("v1894") or {}).get("label"),
                        (parser_results.get("v1894") or {}).get("pass"),
                        (parser_results.get("v1894") or {}).get("out_dir"),
                    ],
                    [
                        "V1888",
                        (parser_results.get("v1888") or {}).get("decision"),
                        (parser_results.get("v1888") or {}).get("label"),
                        (parser_results.get("v1888") or {}).get("pass"),
                        (parser_results.get("v1888") or {}).get("out_dir"),
                    ],
                ],
            ),
            "",
            "## Scope",
            "",
            "- Internal-modem Android-handoff producer measurement only; contaminated captures are explicitly rejected.",
            "- Direct libqmi uprobes are pre-armed before `rild` starts; V1979 also attaches exact `sendmsg`/`recvmsg`/`sendto`/`recvfrom` strace to `rild`, `cnss-daemon`, and `pm-service` as soon as each process appears.",
            "- QRTR enumeration uses only nameservice `NEW_LOOKUP`/`DEL_LOOKUP` control packets with no QMI payload.",
            "- The result is a producer classifier, not a native Wi-Fi bring-up attempt.",
            "",
            "## Safety",
            "",
            "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, bounded tracefs uprobe/kprobe controls, strace attach, and QRTR nameservice lookup/readback controls for observation. No QMI payload replay, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.",
            "",
            "## Rollback Gate",
            "",
            f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
            "",
        ]
    )


def configure_v1979() -> None:
    v1934.CYCLE = CYCLE
    v1934.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1934.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1934.LATEST_POINTER = LATEST_POINTER
    v1934.MODULE_NAME = MODULE_NAME
    v1934.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1934.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1934.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    v1934.TRACEFS_GROUP = TRACEFS_GROUP
    v1934.module_prop = module_prop
    v1934.post_fs_data_script = post_fs_data_script
    v1934.analyze_pulled_evidence = analyze_pulled_evidence
    v1934.classify_result = classify_result
    v1934.render_summary = render_summary


def main() -> int:
    configure_v1979()
    v1934.configure_base()
    args = v1934.base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    v1934.base.configure_v1521_engine()
    configure_v1979_v1521_engine()
    steps, context, base_decision, base_pass = v1934.base.v1521.execute_plan(args, store, execute=execute)
    parser_results: dict[str, Any] = {}
    if execute and base_pass:
        android_dir = v1934.base.evidence_base(store)
        for name, command, timeout, manifest_path in v1934.parser_commands(store, android_dir):
            step = v1934.base.execute_parser_step(store, name, command, timeout, execute=True)
            steps.append(step)
            key = "v1894" if "v1894" in name else "v1888"
            parser_results[key] = v1934.base.read_json(manifest_path)
    elif not execute:
        for name, command, timeout, _manifest_path in v1934.parser_commands(store, v1934.base.evidence_base(store)):
            steps.append(v1934.base.execute_parser_step(store, name, command, timeout, execute=False))

    selftest_ok = v1934.base.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, context, parser_results, selftest_ok)
    else:
        decision = (
            "v1979-android-ril-qmi-strace-qrtr-plan-ready"
            if args.command == "plan"
            else "v1979-android-ril-qmi-strace-qrtr-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-ril-qmi-strace-qrtr-handoff-ready"

    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "parser_results": parser_results,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "tracefs_uprobe_control_executed": execute,
        "tracefs_kprobe_control_executed": execute,
        "strace_attach_executed": execute,
        "qrtr_nameservice_lookup_executed": execute,
        "qmi_payload_replay_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
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
    print(f"label:    {manifest['label']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
