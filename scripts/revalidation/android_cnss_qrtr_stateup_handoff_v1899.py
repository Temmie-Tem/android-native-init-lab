#!/usr/bin/env python3
"""V1899 autonomous Android-good CNSS QRTR state-up capture.

This runner reuses the proven V1521/V1753 Android boot-image handoff: flash the
known Android boot image, install a temporary Magisk post-fs-data observer, boot
normal Android, capture the internal-modem WLAN-PD trigger window, remove the
module, and roll back to native v724.

The observer is read-only with respect to Wi-Fi and modem control.  It captures
filtered logcat/dmesg/TFTP evidence, pre-arms bounded tracefs uprobes on
cnss-daemon's WLFW start path, keeps the V1897 pm-service msg22 uprobes as a
negative control, and attempts QRTR/service-notifier kprobe visibility.  It does
not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, ping, touch
eSoC/PCIe/GDSC/PMIC/GPIO/regulator state, fake ONLINE, send BOOT_DONE, rescan
PCI, or bind/unbind platforms.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521
import android_wlan_pd_firmware_request_handoff_v1753 as v1753


CYCLE = "V1899"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1899-android-normal-cnss-qrtr-edge-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1899_ANDROID_CNSS_QRTR_STATEUP_HANDOFF_2026-06-03.md"
)
DEFAULT_V1894_REPORT = Path(
    "docs/reports/NATIVE_INIT_V1899_V1894_ANDROID_PENDING_CLIENT_MSG22_PARSER_2026-06-03.md"
)
DEFAULT_V1888_REPORT = Path(
    "docs/reports/NATIVE_INIT_V1899_V1888_PM_MSGID_CAPTURE_DIFF_CLASSIFIER_2026-06-03.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1899-android-cnss-qrtr-stateup-handoff.txt")

MODULE_NAME = "a90_v1899_cnss_qrtr"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1899-cnss-qrtr"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1899_cnss_qrtr"
STRACE_SOURCE = Path("external_tools/userland/bin/strace-aarch64-static")
TRACEFS_GROUP = "a90cnss1899"

REDACT_CMD = "sed -E 's/t[e]mmie[[:alnum:]_@.-]*/[REDACTED]/g'"

FILTER_RE = re.compile(
    r"PerMgrSrv|QMI client|QMI service|peripheral restart|restart indication|"
    r"msg[_ =-]?(?:id)?[_ =-]?(?:0x22|22)|pm_msg22|servreg|SSCTL|ssctl|"
    r"service-notifier|wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|"
    r"WLFW|wlfw|icnss|cnss|tftp|rmt_storage|wlan0|BDF file|regdb\.bin|bdwlan\.bin|"
    r"PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed",
    re.IGNORECASE,
)
REQUEST_RE = re.compile(r"wlanmdsp(?:\.mbn)?|wlan[_/-]?pd|wlan/fw", re.IGNORECASE)
MSG22_RE = re.compile(
    r"QMI service peripheral restart request|QMI service peripheral restart response|"
    r"peripheral restart request|msg[_ =-]?(?:id)?[_ =-]?(?:0x22|22)|pm_msg22",
    re.IGNORECASE,
)
PENDING_CLIENT_RE = re.compile(r"QMI client .* connected|QMI client .* disconnected", re.IGNORECASE)
RESTART_IND_RE = re.compile(
    r"restart indication to QMI client|going on-line because restart request|QMI service peripheral restart",
    re.IGNORECASE,
)
PM_MSG22_NOISE_RE = re.compile(
    r"a90_v1899_cnss_qrtr|SRC cnss_qrtr_observer|SRC pm_edge_observer|"
    r"trace_uprobe: Event .*pm_msg22.*doesn'?t exist|"
    r"event\.pm_msg22|result=.*msg22|armed=|hit_count=|msg22_hit_count=",
    re.IGNORECASE,
)
PM_VOTE_RE = re.compile(r"cnss-daemon voting for modem", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)
DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")


ORIGINAL_BUILD_PLAN = v1521.build_plan


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


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
    return v1753.remote_quote(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1899 CNSS QRTR state-up observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary Android-good internal-modem CNSS/WLFW/QRTR state-up observer. Remove after capture.",
            "",
        ]
    )


def sepolicy_rule() -> str:
    return """# Temporary V1899 diagnostic policy for read-only observation.
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
    filter_expr = (
        "PerMgrSrv|QMI client|QMI service|peripheral restart|restart indication|"
        "msg[_ =-]?(id)?[_ =-]?(0x22|22)|pm_msg22|servreg|SSCTL|ssctl|"
        "service-notifier|qrtr|QRTR|QIPCRTR|qmi_handle|wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|"
        "WLFW|wlfw|icnss|cnss|tftp|rmt_storage|wlan0|BDF file|regdb\\.bin|bdwlan\\.bin|"
        "PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed"
    )
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
MOD={REMOTE_MODULE_DIR}
STRACE="$MOD/a90_strace"
SAMPLES={samples}
DELAY_US={delay_us}
GROUP={TRACEFS_GROUP}
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
UPROBE="$OUT/pm-service-uprobe-trace.txt"
UPROBE_SUMMARY="$OUT/pm-service-uprobe-summary.txt"
CNSS_UPROBE="$OUT/cnss-daemon-uprobe-trace.txt"
CNSS_UPROBE_SUMMARY="$OUT/cnss-daemon-uprobe-summary.txt"
QRTR_TRACE="$OUT/qrtr-kprobe-trace.txt"
QRTR_SUMMARY="$OUT/qrtr-kprobe-summary.txt"
TRACE_EVENTS="$OUT/tracefs-events-filtered.txt"
TRACE_SYMBOLS="$OUT/tracefs-symbols-filtered.txt"
FILTER='{filter_expr}'
TRACE_ROOT=
PM_SERVICE=
CNSS_SERVICE=
UPROBE_ARMED=0
CNSS_UPROBE_ARMED=0
QRTR_KPROBE_ARMED=0
ORIG_TRACING_ON=

write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1899_STATUS $1 $now" > "$STATUS"
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
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 2000 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 2500 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.rmt_storage ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

dump_firmware_snapshot() {{
  {{
    echo "A90_V1899_FIRMWARE_SNAPSHOT_BEGIN"
    for d in /vendor/firmware /vendor/firmware_mnt/image /mnt/vendor/firmware /firmware/image; do
      echo "DIR $d"
      if [ -d "$d" ]; then
        find "$d" -maxdepth 3 -type f 2>/dev/null | grep -Ei 'wlanmdsp|wlan|bdwlan|regdb|modem|mba|mdt|b[0-9][0-9]' | head -n 200
      else
        echo "missing"
      fi
    done
    echo "A90_V1899_FIRMWARE_SNAPSHOT_END"
  }} > "$FW.tmp"
  mv "$FW.tmp" "$FW" 2>/dev/null || true
}}

snapshot_proc() {{
  label="$1"
  pid="$2"
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  {{
    echo "A90_V1899_PROC label=$label pid=$pid uptime=$uptime"
    tr '\\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null; echo
    cat "/proc/$pid/status" 2>/dev/null | grep -E 'Name:|State:|Pid:|PPid:|Uid:|Gid:' || true
    cat "/proc/$pid/wchan" 2>/dev/null || true; echo
    ls -l "/proc/$pid/fd" 2>&1 | head -n 80 || true
  }} >> "$SNAP"
}}

count_nonempty_lines() {{
  file="$1"
  if [ -r "$file" ]; then
    count="$(grep -Ec '.' "$file" 2>/dev/null || true)"
    [ -n "$count" ] && echo "$count" || echo 0
  else
    echo 0
  fi
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

select_tracefs() {{
  for t in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    if [ -e "$t/uprobe_events" ]; then
      TRACE_ROOT="$t"
      return 0
    fi
  done
  return 1
}}

select_pm_service() {{
  for p in /vendor/bin/pm-service /mnt/vendor/bin/pm-service; do
    if [ -r "$p" ]; then
      PM_SERVICE="$p"
      return 0
    fi
  done
  return 1
}}

select_cnss_service() {{
  for p in /vendor/bin/cnss-daemon /mnt/vendor/bin/cnss-daemon; do
    if [ -r "$p" ]; then
      CNSS_SERVICE="$p"
      return 0
    fi
  done
  return 1
}}

dump_tracefs_catalog() {{
  if ! select_tracefs; then
    echo "tracefs=missing" > "$TRACE_EVENTS"
    echo "tracefs=missing" > "$TRACE_SYMBOLS"
    return 0
  fi
  {{
    echo "tracefs=$TRACE_ROOT"
    find "$TRACE_ROOT/events" -maxdepth 3 -type d 2>/dev/null | grep -Ei 'qmi|qrtr|sock|service|servreg|cnss|wlfw|subsys|remoteproc|rproc' | head -n 300
  }} > "$TRACE_EVENTS.tmp"
  mv "$TRACE_EVENTS.tmp" "$TRACE_EVENTS" 2>/dev/null || true
  {{
    echo "tracefs=$TRACE_ROOT"
    if [ -r /proc/kallsyms ]; then
      grep -Ei '(^| )qrtr_|qmi_|service_notifier|servreg|subsys|rproc|remoteproc|icnss|wlfw' /proc/kallsyms 2>/dev/null | head -n 400
    else
      echo "kallsyms=unreadable"
    fi
  }} > "$TRACE_SYMBOLS.tmp"
  mv "$TRACE_SYMBOLS.tmp" "$TRACE_SYMBOLS" 2>/dev/null || true
}}

uprobe_cleanup() {{
  [ "$UPROBE_ARMED" = "1" ] || [ "$CNSS_UPROBE_ARMED" = "1" ] || [ "$QRTR_KPROBE_ARMED" = "1" ] || return 0
  for label in pm_msg22_dispatch_entry pm_msg22_dispatch_ssid pm_msg22_pending_helper_call pm_msg22_send_resp; do
    if [ -e "$TRACE_ROOT/events/$GROUP/$label/enable" ]; then
      echo 0 > "$TRACE_ROOT/events/$GROUP/$label/enable" 2>/dev/null || true
    fi
  done
  for label in cnss_wlfw_start_entry cnss_wlfw_dms_init_call cnss_wlfw_worker_create_call cnss_wlfw_worker_create_success cnss_wlfw_service_request_entry; do
    if [ -e "$TRACE_ROOT/events/$GROUP/$label/enable" ]; then
      echo 0 > "$TRACE_ROOT/events/$GROUP/$label/enable" 2>/dev/null || true
    fi
  done
  for label in qrtr_sendmsg qrtr_recvmsg qrtr_connect qrtr_bind qmi_send_message qmi_handle_message servnotif_new_server servnotif_service_ind; do
    if [ -e "$TRACE_ROOT/events/$GROUP/$label/enable" ]; then
      echo 0 > "$TRACE_ROOT/events/$GROUP/$label/enable" 2>/dev/null || true
    fi
  done
  for label in pm_msg22_dispatch_entry pm_msg22_dispatch_ssid pm_msg22_pending_helper_call pm_msg22_send_resp; do
    echo "-:$GROUP/$label" >> "$TRACE_ROOT/uprobe_events" 2>/dev/null || true
  done
  for label in cnss_wlfw_start_entry cnss_wlfw_dms_init_call cnss_wlfw_worker_create_call cnss_wlfw_worker_create_success cnss_wlfw_service_request_entry; do
    echo "-:$GROUP/$label" >> "$TRACE_ROOT/uprobe_events" 2>/dev/null || true
  done
  if [ -e "$TRACE_ROOT/kprobe_events" ]; then
    for label in qrtr_sendmsg qrtr_recvmsg qrtr_connect qrtr_bind qmi_send_message qmi_handle_message servnotif_new_server servnotif_service_ind; do
      echo "-:$GROUP/$label" >> "$TRACE_ROOT/kprobe_events" 2>/dev/null || true
    done
  fi
  if [ -n "$ORIG_TRACING_ON" ]; then
    echo "$ORIG_TRACING_ON" > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
  fi
  echo "cleanup_done=1" >> "$UPROBE_SUMMARY"
  echo "cleanup_done=1" >> "$CNSS_UPROBE_SUMMARY"
  echo "cleanup_done=1" >> "$QRTR_SUMMARY"
}}

register_user_uprobe_event() {{
  label="$1"
  binary="$2"
  offset="$3"
  fetch="$4"
  summary="$5"
  echo "-:$GROUP/$label" >> "$TRACE_ROOT/uprobe_events" 2>/dev/null || true
  if [ -n "$fetch" ]; then
    line="p:$GROUP/$label $binary:0x$offset $fetch"
  else
    line="p:$GROUP/$label $binary:0x$offset"
  fi
  if echo "$line" >> "$TRACE_ROOT/uprobe_events" 2>/dev/null; then
    echo "event.$label.register=ok line=$line" >> "$summary"
  else
    echo "event.$label.register=failed line=$line" >> "$summary"
    return 1
  fi
  if echo 1 > "$TRACE_ROOT/events/$GROUP/$label/enable" 2>/dev/null; then
    echo "event.$label.enable=ok" >> "$summary"
  else
    echo "event.$label.enable=failed" >> "$summary"
    return 1
  fi
  return 0
}}

register_uprobe_event() {{
  register_user_uprobe_event "$1" "$PM_SERVICE" "$2" "$3" "$UPROBE_SUMMARY"
}}

register_cnss_uprobe_event() {{
  label="$1"
  offset="$2"
  fetch="$3"
  register_user_uprobe_event "$label" "$CNSS_SERVICE" "$offset" "$fetch" "$CNSS_UPROBE_SUMMARY"
}}

register_kprobe_event() {{
  label="$1"
  symbol="$2"
  [ -e "$TRACE_ROOT/kprobe_events" ] || return 1
  echo "-:$GROUP/$label" >> "$TRACE_ROOT/kprobe_events" 2>/dev/null || true
  line="p:$GROUP/$label $symbol"
  if echo "$line" >> "$TRACE_ROOT/kprobe_events" 2>/dev/null; then
    echo "event.$label.register=ok line=$line" >> "$QRTR_SUMMARY"
  else
    echo "event.$label.register=failed line=$line" >> "$QRTR_SUMMARY"
    return 1
  fi
  if echo 1 > "$TRACE_ROOT/events/$GROUP/$label/enable" 2>/dev/null; then
    echo "event.$label.enable=ok" >> "$QRTR_SUMMARY"
  else
    echo "event.$label.enable=failed" >> "$QRTR_SUMMARY"
    return 1
  fi
  return 0
}}

arm_uprobe_if_needed() {{
  [ "$UPROBE_ARMED" = "0" ] || return 0
  if cat "$LOGCAT" "$DMESG" "$OUT/request-lines.txt" 2>/dev/null | grep -Eiv 'a90_v1899_cnss_qrtr|Magisk|SRC cnss_qrtr_observer|SRC pm_edge_observer' | grep -Eiq 'QMI service peripheral restart|peripheral restart request|msg[_ =-]?(id)?[_ =-]?(0x22|22)|pm_msg22'; then
    echo "result=logcat_msg22_visible_no_uprobe" > "$UPROBE_SUMMARY"
    return 0
  fi
  : > "$UPROBE_SUMMARY"
  echo "result=uprobe_attempted_after_zero_log_msg22" >> "$UPROBE_SUMMARY"
  if ! select_tracefs; then
    echo "tracefs=missing" >> "$UPROBE_SUMMARY"
    return 0
  fi
  if ! select_pm_service; then
    echo "pm_service=missing" >> "$UPROBE_SUMMARY"
    return 0
  fi
  echo "tracefs=$TRACE_ROOT" >> "$UPROBE_SUMMARY"
  echo "pm_service=$PM_SERVICE" >> "$UPROBE_SUMMARY"
  if [ -r "$TRACE_ROOT/tracing_on" ]; then
    ORIG_TRACING_ON="$(cat "$TRACE_ROOT/tracing_on" 2>/dev/null)"
  fi
  : > "$TRACE_ROOT/trace" 2>/dev/null || true
  echo 1 > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
  register_uprobe_event pm_msg22_dispatch_entry 716c 'msg_id=%x2 client=%x1 req=%x3 mgr=%x4' || return 0
  register_uprobe_event pm_msg22_dispatch_ssid 71ac 'msg_id=%x19 req_ssid=%x22' || return 0
  register_uprobe_event pm_msg22_pending_helper_call 72c0 'pending_client=%x17 req=%x21 mgr=%x15' || return 0
  register_uprobe_event pm_msg22_send_resp 725c 'msg_id=%x1 resp=%x2 client=%x0' || return 0
  UPROBE_ARMED=1
  echo "armed=1" >> "$UPROBE_SUMMARY"
}}

arm_cnss_uprobes() {{
  [ "$CNSS_UPROBE_ARMED" = "0" ] || return 0
  : > "$CNSS_UPROBE_SUMMARY"
  echo "result=cnss_uprobe_attempted_prearmed" >> "$CNSS_UPROBE_SUMMARY"
  if ! select_tracefs; then
    echo "tracefs=missing" >> "$CNSS_UPROBE_SUMMARY"
    return 0
  fi
  if ! select_cnss_service; then
    echo "cnss_service=missing" >> "$CNSS_UPROBE_SUMMARY"
    return 0
  fi
  echo "tracefs=$TRACE_ROOT" >> "$CNSS_UPROBE_SUMMARY"
  echo "cnss_service=$CNSS_SERVICE" >> "$CNSS_UPROBE_SUMMARY"
  if [ -r "$TRACE_ROOT/tracing_on" ] && [ -z "$ORIG_TRACING_ON" ]; then
    ORIG_TRACING_ON="$(cat "$TRACE_ROOT/tracing_on" 2>/dev/null)"
  fi
  echo 1 > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
  register_cnss_uprobe_event cnss_wlfw_start_entry ec00 '' || true
  register_cnss_uprobe_event cnss_wlfw_dms_init_call ecd4 '' || true
  register_cnss_uprobe_event cnss_wlfw_worker_create_call ecf0 '' || true
  register_cnss_uprobe_event cnss_wlfw_worker_create_success eda0 '' || true
  register_cnss_uprobe_event cnss_wlfw_service_request_entry d9fc '' || true
  CNSS_UPROBE_ARMED=1
  echo "armed=1" >> "$CNSS_UPROBE_SUMMARY"
}}

arm_qrtr_kprobes() {{
  [ "$QRTR_KPROBE_ARMED" = "0" ] || return 0
  : > "$QRTR_SUMMARY"
  echo "result=qrtr_kprobe_attempted_prearmed" >> "$QRTR_SUMMARY"
  if ! select_tracefs; then
    echo "tracefs=missing" >> "$QRTR_SUMMARY"
    return 0
  fi
  if [ ! -e "$TRACE_ROOT/kprobe_events" ]; then
    echo "kprobe_events=missing" >> "$QRTR_SUMMARY"
    return 0
  fi
  echo "tracefs=$TRACE_ROOT" >> "$QRTR_SUMMARY"
  if [ -r "$TRACE_ROOT/tracing_on" ] && [ -z "$ORIG_TRACING_ON" ]; then
    ORIG_TRACING_ON="$(cat "$TRACE_ROOT/tracing_on" 2>/dev/null)"
  fi
  echo 1 > "$TRACE_ROOT/tracing_on" 2>/dev/null || true
  register_kprobe_event qrtr_sendmsg qrtr_sendmsg || true
  register_kprobe_event qrtr_recvmsg qrtr_recvmsg || true
  register_kprobe_event qrtr_connect qrtr_connect || true
  register_kprobe_event qrtr_bind qrtr_bind || true
  register_kprobe_event qmi_send_message qmi_send_message || true
  register_kprobe_event qmi_handle_message qmi_handle_message || true
  register_kprobe_event servnotif_new_server service_notifier_new_server || true
  register_kprobe_event servnotif_service_ind root_service_service_ind_cb || true
  QRTR_KPROBE_ARMED=1
  echo "armed=1" >> "$QRTR_SUMMARY"
}}

dump_uprobe_trace() {{
  if [ "$UPROBE_ARMED" = "1" ] && [ -r "$TRACE_ROOT/trace" ]; then
    grep -E "$GROUP/pm_msg22|pm_msg22" "$TRACE_ROOT/trace" > "$UPROBE.tmp" 2>/dev/null || true
    mv "$UPROBE.tmp" "$UPROBE" 2>/dev/null || true
    echo "hit_count=$(count_nonempty_lines "$UPROBE")" >> "$UPROBE_SUMMARY"
    msg22_hits="$(grep -Ec 'msg_id=0x22|msg_id=34|pm_msg22' "$UPROBE" 2>/dev/null || true)"
    echo "msg22_hit_count=${{msg22_hits:-0}}" >> "$UPROBE_SUMMARY"
  else
    : > "$UPROBE"
  fi
}}

dump_cnss_qrtr_trace() {{
  if [ -n "$TRACE_ROOT" ] && [ -r "$TRACE_ROOT/trace" ]; then
    grep -E "$GROUP.*(cnss_|wlfw_)|cnss_wlfw" "$TRACE_ROOT/trace" > "$CNSS_UPROBE.tmp" 2>/dev/null || true
    mv "$CNSS_UPROBE.tmp" "$CNSS_UPROBE" 2>/dev/null || true
    grep -E "$GROUP.*(qrtr_|qmi_|servnotif_)|qrtr_|qmi_|servnotif_" "$TRACE_ROOT/trace" > "$QRTR_TRACE.tmp" 2>/dev/null || true
    mv "$QRTR_TRACE.tmp" "$QRTR_TRACE" 2>/dev/null || true
  else
    : > "$CNSS_UPROBE"
    : > "$QRTR_TRACE"
  fi
  cnss_hits="$(grep -Ec "$GROUP|cnss_wlfw" "$CNSS_UPROBE" 2>/dev/null || true)"
  worker_hits="$(grep -Ec 'cnss_wlfw_service_request_entry' "$CNSS_UPROBE" 2>/dev/null || true)"
  qrtr_hits="$(grep -Ec "$GROUP|qrtr_|qmi_|servnotif_" "$QRTR_TRACE" 2>/dev/null || true)"
  qrtr_only_hits="$(grep -Ec 'qrtr_' "$QRTR_TRACE" 2>/dev/null || true)"
  qmi_hits="$(grep -Ec 'qmi_' "$QRTR_TRACE" 2>/dev/null || true)"
  servnotif_hits="$(grep -Ec 'servnotif_' "$QRTR_TRACE" 2>/dev/null || true)"
  echo "hit_count=${{cnss_hits:-0}}" >> "$CNSS_UPROBE_SUMMARY"
  echo "worker_entry_hit_count=${{worker_hits:-0}}" >> "$CNSS_UPROBE_SUMMARY"
  echo "hit_count=${{qrtr_hits:-0}}" >> "$QRTR_SUMMARY"
  echo "qrtr_hit_count=${{qrtr_only_hits:-0}}" >> "$QRTR_SUMMARY"
  echo "qmi_hit_count=${{qmi_hits:-0}}" >> "$QRTR_SUMMARY"
  echo "servnotif_hit_count=${{servnotif_hits:-0}}" >> "$QRTR_SUMMARY"
}}

summarize_requests() {{
  cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" "$UPROBE" "$CNSS_UPROBE" "$QRTR_TRACE" 2>/dev/null | grep -Eiv 'a90_v1899_cnss_qrtr|SRC cnss_qrtr_observer|SRC pm_edge_observer|trace_uprobe: Event .*pm_msg22.*doesn.?t exist|event\\.pm_msg22|result=.*msg22|armed=|hit_count=|msg22_hit_count=' | grep -Ei "$FILTER|pm_msg22|$GROUP" | tail -n 2000 > "$OUT/request-lines.txt" || true
  {{
    printf 'requested_wlanmdsp='
    grep -Eiq 'wlanmdsp(\\.mbn)?' "$OUT/request-lines.txt" 2>/dev/null && echo 1 || echo 0
    printf 'requested_pd_image='
    grep -Eiq 'wlanmdsp|wlan[_/-]?pd|wlan/fw' "$OUT/request-lines.txt" 2>/dev/null && echo 1 || echo 0
    printf 'pm_msg22_seen='
    grep -Eiv 'a90_v1899_cnss_qrtr|SRC cnss_qrtr_observer|SRC pm_edge_observer|trace_uprobe: Event .*pm_msg22.*doesn.?t exist|event\\.pm_msg22|result=.*msg22|armed=|hit_count=|msg22_hit_count=' "$OUT/request-lines.txt" 2>/dev/null | grep -Eiq 'QMI service peripheral restart|msg[_ =-]?(id)?[_ =-]?(0x22|22)|pm_msg22' && echo 1 || echo 0
    printf 'pending_qmi_client_seen='
    grep -Eiq 'QMI client .* connected|QMI client .* disconnected' "$OUT/request-lines.txt" 2>/dev/null && echo 1 || echo 0
    printf 'tftp_trace_lines='
    count_nonempty_lines "$OUT/tftp_server.strace.txt"
    printf 'rmt_storage_trace_lines='
    count_nonempty_lines "$OUT/rmt_storage.strace.txt"
    printf 'cnss_trace_lines='
    count_nonempty_lines "$OUT/cnss_daemon.strace.txt"
    printf 'uprobe_trace_lines='
    count_nonempty_lines "$UPROBE"
    printf 'cnss_uprobe_trace_lines='
    count_nonempty_lines "$CNSS_UPROBE"
    printf 'qrtr_kprobe_trace_lines='
    count_nonempty_lines "$QRTR_TRACE"
    printf 'wlan0_seen='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eiq '\\bwlan0\\b' && echo 1 || echo 0
    printf 'wlfw_seen='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eiq 'wlfw|WLFW' && echo 1 || echo 0
  }} > "$REQ.tmp"
  mv "$REQ.tmp" "$REQ" 2>/dev/null || true
}}

(
  trap uprobe_cleanup EXIT INT TERM
  umask 022
  write_status start
  : > "$LOG"
  : > "$SNAP"
  : > "$PIDS"
  : > "$UPROBE"
  : > "$UPROBE_SUMMARY"
  : > "$CNSS_UPROBE"
  : > "$CNSS_UPROBE_SUMMARY"
  : > "$QRTR_TRACE"
  : > "$QRTR_SUMMARY"
  echo "A90_V1899_POSTFS_BEGIN" >> "$LOG"
  id >> "$LOG" 2>&1 || true
  cat /proc/self/attr/current >> "$LOG" 2>&1 || true
  arm_uprobe_if_needed
  arm_cnss_uprobes
  arm_qrtr_kprobes
  dump_tracefs_catalog
  dump_firmware_snapshot
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1899_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    attach_once tftp_server /vendor/bin/tftp_server
    attach_once rmt_storage /vendor/bin/rmt_storage
    attach_once cnss_daemon cnss-daemon
    if [ "$((i % 4))" = "0" ]; then
      dump_filtered
      dump_props
      dump_uprobe_trace
      dump_cnss_qrtr_trace
      summarize_requests
      arm_uprobe_if_needed
      arm_cnss_uprobes
      arm_qrtr_kprobes
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    echo "SRC cnss_qrtr_observer" >> "$LOG"
    cat "$REQ" >> "$LOG" 2>/dev/null || true
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    echo "A90_V1899_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  finish_strace
  sleep 1
  dump_filtered
  dump_props
  dump_uprobe_trace
  dump_cnss_qrtr_trace
  summarize_requests
  echo "A90_V1899_POSTFS_END" >> "$LOG"
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
            "prepare-v1899-magisk-module",
            "host:prepare temporary cnss-qrtr Magisk module",
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
        "prepare-v1899-magisk-module",
        "host:prepare temporary cnss-qrtr Magisk module",
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
        ("push-v1899-module-prop-android", [*v1521.adb_base(args), "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v1899-post-fs-data-android", [*v1521.adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v1899-sepolicy-android", [*v1521.adb_base(args), "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("push-v1899-strace-android", [*v1521.adb_base(args), "push", str(stage / "a90_strace"), remote_strace], args.timeout * 2),
        ("install-v1899-module-android-su", [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)], args.timeout),
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


def redacted_a90ctl_command(kind: str) -> list[str]:
    if kind == "version":
        inner = f"python3 scripts/revalidation/a90ctl.py --json version | {REDACT_CMD}"
    elif kind == "status":
        inner = f"python3 scripts/revalidation/a90ctl.py status | {REDACT_CMD}"
    else:
        raise ValueError(kind)
    return ["bash", "-lc", inner]


def redacted_shell_pipeline(command: list[str]) -> list[str]:
    return ["bash", "-lc", f"set -o pipefail; {shlex.join(command)} | {REDACT_CMD}"]


def build_plan_v1899(args: argparse.Namespace,
                     store: EvidenceStore,
                     android_image: Any,
                     native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    plan = ORIGINAL_BUILD_PLAN(args, store, android_image, native_image)
    updated: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in plan:
        if name == "native-version":
            updated.append(("native-version-redacted", redacted_a90ctl_command("version"), timeout))
        elif name == "native-status":
            updated.append(("native-status-redacted", redacted_a90ctl_command("status"), timeout))
        elif name == "restore-native" and isinstance(command, list):
            updated.append((name, redacted_shell_pipeline(command), timeout))
        else:
            updated.append((name, command, timeout))
    updated.append(("post-rollback-native-status-redacted", redacted_a90ctl_command("status"), args.timeout))
    return updated


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
    v1521.build_plan = build_plan_v1899


def read_file(path: Path, limit: int = 4_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / Path(REMOTE_EVIDENCE_DIR).name
    return candidate if candidate.is_dir() else root


def parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def count_lines(lines: list[str] | str, regex: re.Pattern[str]) -> int:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    return sum(1 for line in iterable if regex.search(line))


def first_line(lines: list[str] | str, regex: re.Pattern[str]) -> str:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    for line in iterable:
        if regex.search(line):
            return line.strip()
    return ""


def first_dmesg_time(lines: list[str], regex: re.Pattern[str]) -> float | None:
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_dmesg_before(lines: list[str], regex: re.Pattern[str], before_time: float | None) -> int:
    total = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            total += 1
    return total


def extract_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r'"(/[^"]+)"', text):
        value = match.group(1)
        if FILTER_RE.search(value) and value not in paths:
            paths.append(value)
    for match in re.finditer(r"\[(/[^]\s]+(?:wlanmdsp|wlan[_/-]?pd|firmware)[^]\s]*)\]", text, re.IGNORECASE):
        value = match.group(1)
        if value not in paths:
            paths.append(value)
    return paths[:80]


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    samples = read_file(base / "samples.log")
    dmesg = read_file(base / "dmesg-filtered.txt") + "\n" + read_file(root / "host-dmesg-filtered.txt")
    logcat = read_file(base / "logcat-filtered.txt")
    props = read_file(base / "props.txt")
    status = read_file(base / "status.txt")
    request_summary = parse_key_values(read_file(base / "request-summary.txt"))
    uprobe_summary = parse_key_values(read_file(base / "pm-service-uprobe-summary.txt"))
    cnss_uprobe_summary = parse_key_values(read_file(base / "cnss-daemon-uprobe-summary.txt"))
    qrtr_kprobe_summary = parse_key_values(read_file(base / "qrtr-kprobe-summary.txt"))
    tftp_trace = read_file(base / "tftp_server.strace.txt")
    rmt_trace = read_file(base / "rmt_storage.strace.txt")
    cnss_trace = read_file(base / "cnss_daemon.strace.txt")
    uprobe_trace = read_file(base / "pm-service-uprobe-trace.txt")
    cnss_uprobe_trace = read_file(base / "cnss-daemon-uprobe-trace.txt")
    qrtr_kprobe_trace = read_file(base / "qrtr-kprobe-trace.txt")
    tracefs_events = read_file(base / "tracefs-events-filtered.txt")
    tracefs_symbols = read_file(base / "tracefs-symbols-filtered.txt")
    launch = read_file(base / "strace-launch.log")
    request_lines = read_file(base / "request-lines.txt")
    combined = "\n".join(
        [
            tftp_trace,
            rmt_trace,
            cnss_trace,
            dmesg,
            logcat,
            uprobe_trace,
            cnss_uprobe_trace,
            qrtr_kprobe_trace,
            request_lines,
        ]
    )
    dmesg_lines = dmesg.splitlines()
    logcat_lines = logcat.splitlines()
    request_line_list = request_lines.splitlines()
    all_lines = logcat_lines + dmesg_lines + request_line_list + uprobe_trace.splitlines()
    signal_lines = [line for line in all_lines if not PM_MSG22_NOISE_RE.search(line)]
    wlan0_time = first_dmesg_time(dmesg_lines, WLAN0_RE)
    wlan_pd_time = first_dmesg_time(dmesg_lines, WLAN_PD_RE)
    pcie_before = count_dmesg_before(dmesg_lines, PCIE_MHI_RE, wlan0_time)
    esoc_failed_before = count_dmesg_before(dmesg_lines, ESOC_BOOT_FAILED_RE, wlan0_time)
    requested_wlanmdsp = bool(REQUEST_RE.search(combined))
    pm_msg22_count = count_lines(signal_lines, MSG22_RE)
    pending_client_count = count_lines(signal_lines, PENDING_CLIENT_RE)
    restart_ind_count = count_lines(signal_lines, RESTART_IND_RE)
    trace_lines = {
        "tftp_server": tftp_trace.count("\n"),
        "rmt_storage": rmt_trace.count("\n"),
        "cnss_daemon": cnss_trace.count("\n"),
        "pm_service_uprobe": uprobe_trace.count("\n"),
        "cnss_daemon_uprobe": cnss_uprobe_trace.count("\n"),
        "qrtr_kprobe": qrtr_kprobe_trace.count("\n"),
        "tracefs_event_catalog": tracefs_events.count("\n"),
        "tracefs_symbol_catalog": tracefs_symbols.count("\n"),
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
        "uprobe_trace": bool(uprobe_trace),
        "uprobe_summary": bool(uprobe_summary),
        "cnss_uprobe_trace": bool(cnss_uprobe_trace),
        "cnss_uprobe_summary": bool(cnss_uprobe_summary),
        "qrtr_kprobe_trace": bool(qrtr_kprobe_trace),
        "qrtr_kprobe_summary": bool(qrtr_kprobe_summary),
        "tracefs_events": bool(tracefs_events),
        "tracefs_symbols": bool(tracefs_symbols),
    }
    dmesg_counts = {
        "wlfw_lines": count_lines(dmesg + "\n" + logcat, re.compile(r"\bwlfw\b|WLFW", re.IGNORECASE)),
        "bdf_lines": count_lines(dmesg + "\n" + logcat, re.compile(r"BDF file|regdb\.bin|bdwlan\.bin", re.IGNORECASE)),
        "wlan0_lines": count_lines(dmesg + "\n" + logcat, re.compile(r"\bwlan0\b", re.IGNORECASE)),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlan_pd_indication_time_s": wlan_pd_time,
        "wlan0_time_s": wlan0_time,
        "pcie_mhi_before_wlan0": pcie_before,
        "esoc_boot_failed_before_wlan0": esoc_failed_before,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
    }
    return {
        "base": str(base),
        "android_dir": rel(base),
        "files_present": files_present,
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1899_SAMPLE_BEGIN"),
        "sample_first_uptime": None,
        "sample_last_uptime": None,
        "request_summary": request_summary,
        "uprobe_summary": uprobe_summary,
        "cnss_uprobe_summary": cnss_uprobe_summary,
        "qrtr_kprobe_summary": qrtr_kprobe_summary,
        "requested_wlanmdsp": "1" if requested_wlanmdsp else "0",
        "requested_pd_image": request_summary.get("requested_pd_image", "1" if requested_wlanmdsp else "0"),
        "served_path_candidates": extract_paths(combined),
        "trace_lines": trace_lines,
        "strace_launch_excerpt": launch[-4000:],
        "cnss_uprobe_excerpt": cnss_uprobe_trace[-4000:],
        "qrtr_kprobe_excerpt": qrtr_kprobe_trace[-4000:],
        "tracefs_events_excerpt": tracefs_events[-4000:],
        "tracefs_symbols_excerpt": tracefs_symbols[-4000:],
        "request_lines_excerpt": request_lines[-8000:],
        "pm_msg22_count": pm_msg22_count,
        "pm_msg22_first_line": first_line(signal_lines, MSG22_RE),
        "pending_qmi_client_count": pending_client_count,
        "pending_qmi_client_first_line": first_line(signal_lines, PENDING_CLIENT_RE),
        "restart_ind_count": restart_ind_count,
        "restart_ind_first_line": first_line(signal_lines, RESTART_IND_RE),
        "pm_vote_count": count_lines(logcat_lines, PM_VOTE_RE),
        "wlfw_service_request_count": count_lines(logcat_lines + dmesg_lines, WLFW_REQUEST_RE),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlanmdsp_count": count_lines(logcat_lines + request_line_list, WLANMDSP_RE),
        "dmesg": dmesg_counts,
        "matched_window": {
            "first_lower_time": wlan0_time,
            "has_pre_lower_sample": False,
            "has_post_lower_sample": False,
            "has_pre_l0_sample": False,
            "has_post_l0_sample": False,
            "first_sample": None,
            "last_sample": None,
        },
        "props_text": props.strip(),
    }


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence runner preserves failures
        return None, "", str(exc), time.monotonic() - started


def execute_parser_step(store: EvidenceStore,
                        name: str,
                        command: list[str],
                        timeout: int,
                        execute: bool) -> v1521.StepResult:
    if not execute:
        return v1521.write_step(store, name, command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    rc, text, error, duration = run_process(command, timeout)
    return v1521.write_step(store, name, command, text, error, rc, duration)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parser_commands(store: EvidenceStore, android_dir: Path) -> list[tuple[str, list[str], int, Path]]:
    v1894_out = store.run_dir / "v1894-parser"
    v1888_out = store.run_dir / "v1888-parser"
    return [
        (
            "run-v1894-pending-client-parser",
            [
                "python3",
                "scripts/revalidation/native_wifi_android_pending_client_msg22_parser_v1894.py",
                "--android-dir",
                str(android_dir),
                "--out-dir",
                str(v1894_out),
                "--report",
                str(repo_path(DEFAULT_V1894_REPORT)),
            ],
            60,
            v1894_out / "manifest.json",
        ),
        (
            "run-v1888-msgid-diff-parser",
            [
                "python3",
                "scripts/revalidation/native_wifi_pm_msgid_capture_diff_classifier_v1888.py",
                "--android-dir",
                str(android_dir),
                "--out-dir",
                str(v1888_out),
                "--report",
                str(repo_path(DEFAULT_V1888_REPORT)),
            ],
            60,
            v1888_out / "manifest.json",
        ),
    ]


def step_text(store: EvidenceStore, step: v1521.StepResult) -> str:
    return (store.run_dir / step.file).read_text(encoding="utf-8", errors="replace")


def rollback_selftest_ok(store: EvidenceStore, steps: list[v1521.StepResult]) -> bool:
    for step in reversed(steps):
        if step.name == "post-rollback-native-status-redacted":
            return bool(re.search(r"selftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", step_text(store, step)))
    return False


def classify_result(base_decision: str,
                    base_pass: bool,
                    context: dict[str, Any],
                    parser_results: dict[str, Any],
                    selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return (
            "v1899-rollback-selftest-failed",
            False,
            "native rollback did not prove selftest fail=0",
            "rollback-selftest-failed",
        )
    if not base_pass:
        return (
            f"v1899-base-handoff-failed-{base_decision}",
            False,
            "underlying Android handoff did not complete",
            "android-handoff-failed",
        )
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    if not files.get("request_summary"):
        return (
            "v1899-capture-insufficient-rollback-pass",
            False,
            "rollback completed, but request-summary evidence was not captured",
            "capture-insufficient",
        )
    dmesg = analysis.get("dmesg") or {}
    contaminated = (
        bool(dmesg.get("degraded_257s_like"))
        or int(dmesg.get("pcie_mhi_before_wlan0") or 0) > 0
        or int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) > 0
    )
    if contaminated:
        return (
            "v1899-android-capture-rejected-degraded-or-pcie-mhi",
            False,
            "Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination",
            "android-capture-rejected-degraded-or-pcie-mhi",
        )
    stateup = (
        int(analysis.get("pm_vote_count") or 0) > 0
        and int(analysis.get("wlfw_service_request_count") or 0) > 0
        and int(analysis.get("wlan_pd_indication_count") or 0) > 0
        and int(analysis.get("wlanmdsp_count") or 0) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    if not stateup:
        return (
            "v1899-android-normal-stateup-incomplete-rollback-pass",
            False,
            "capture does not contain the normal PM vote -> wlan_pd -> wlanmdsp -> wlan0 state-up sequence",
            "android-normal-stateup-incomplete",
        )
    v1894 = parser_results.get("v1894") or {}
    v1888 = parser_results.get("v1888") or {}
    parser_ok = bool(v1894.get("pass")) and bool(v1888.get("pass"))
    if not parser_ok:
        return (
            "v1899-parser-chain-failed-rollback-pass",
            False,
            "Android capture succeeded but V1894/V1888 parser chain did not pass",
            "parser-chain-failed",
        )
    pm_msg22_count = int(analysis.get("pm_msg22_count") or 0)
    pending_count = int(analysis.get("pending_qmi_client_count") or 0)
    uprobe_lines = int((analysis.get("trace_lines") or {}).get("pm_service_uprobe") or 0)
    cnss_summary = analysis.get("cnss_uprobe_summary") or {}
    qrtr_summary = analysis.get("qrtr_kprobe_summary") or {}
    cnss_hits = int(cnss_summary.get("hit_count") or 0)
    cnss_worker_hits = int(cnss_summary.get("worker_entry_hit_count") or 0)
    qrtr_hits = int(qrtr_summary.get("hit_count") or 0)
    qrtr_only_hits = int(qrtr_summary.get("qrtr_hit_count") or 0)
    qmi_hits = int(qrtr_summary.get("qmi_hit_count") or 0)
    servnotif_hits = int(qrtr_summary.get("servnotif_hit_count") or 0)
    if pm_msg22_count > 0 and uprobe_lines > 0:
        return (
            "v1899-android-uprobe-msg22-stateup-native-absent-rollback-pass",
            True,
            "normal Android state-up captured pm-service msg22 via same-boot uprobe fallback; native post-open lacks the edge",
            "android-uprobe-msg22-stateup-native-absent",
        )
    if pm_msg22_count > 0:
        return (
            "v1899-android-logcat-msg22-stateup-native-absent-rollback-pass",
            True,
            "normal Android state-up captured pm-service msg22/pending-client evidence in filtered logs; native post-open lacks the edge",
            "android-logcat-msg22-stateup-native-absent",
        )
    if pending_count > 0:
        return (
            "v1899-android-pending-client-without-msg22-stateup-rollback-pass",
            True,
            "normal Android state-up captured QMI client pending-client visibility but no explicit msg22 line",
            "android-pending-client-without-msg22-stateup",
        )
    if cnss_worker_hits > 0 and (qrtr_only_hits > 0 or qmi_hits > 0 or servnotif_hits > 0):
        return (
            "v1899-android-cnss-qrtr-stateup-not-msg22-rollback-pass",
            True,
            "normal Android state-up captured the CNSS WLFW worker and QRTR/QMI/service-notifier tracefs activity while pm-service msg22 remained absent",
            "android-cnss-qrtr-stateup-not-msg22",
        )
    if cnss_worker_hits > 0:
        return (
            "v1899-android-cnss-wlfw-worker-not-msg22-rollback-pass",
            True,
            "normal Android state-up captured the CNSS WLFW worker entry while pm-service msg22 remained absent; QRTR kprobe visibility was incomplete",
            "android-cnss-wlfw-worker-not-msg22",
        )
    if cnss_hits > 0 or qrtr_hits > 0:
        return (
            "v1899-android-cnss-qrtr-partial-not-msg22-rollback-pass",
            True,
            "normal Android state-up captured partial CNSS/QRTR tracefs activity while pm-service msg22 remained absent",
            "android-cnss-qrtr-partial-not-msg22",
        )
    return (
        "v1899-android-stateup-cnss-qrtr-observability-gap-rollback-pass",
        True,
        "normal Android state-up was captured, pm-service msg22/pending-client remained unobserved, and CNSS/QRTR tracefs probes produced no decisive hit",
        "android-stateup-cnss-qrtr-observability-gap",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    trace_lines = analysis.get("trace_lines") or {}
    request_summary = analysis.get("request_summary") or {}
    uprobe_summary = analysis.get("uprobe_summary") or {}
    cnss_uprobe_summary = analysis.get("cnss_uprobe_summary") or {}
    qrtr_kprobe_summary = analysis.get("qrtr_kprobe_summary") or {}
    parser_results = manifest.get("parser_results") or {}
    return "\n".join(
        [
            "# V1899 Android Normal CNSS QRTR State-up Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- label: `{manifest['label']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Android Trigger Window",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["android_dir", analysis.get("android_dir")],
                    ["PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0", f"{analysis.get('pm_vote_count')}/{analysis.get('wlfw_service_request_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}"],
                    ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
                    ["pm_msg22/pending-client/restart-ind", f"{analysis.get('pm_msg22_count')}/{analysis.get('pending_qmi_client_count')}/{analysis.get('restart_ind_count')}"],
                    ["first msg22", analysis.get("pm_msg22_first_line", "")],
                    ["first pending-client", analysis.get("pending_qmi_client_first_line", "")],
                    ["request_summary", json.dumps(request_summary, sort_keys=True)],
                    ["trace_lines", json.dumps(trace_lines, sort_keys=True)],
                    ["uprobe_summary", json.dumps(uprobe_summary, sort_keys=True)],
                    ["cnss_uprobe_summary", json.dumps(cnss_uprobe_summary, sort_keys=True)],
                    ["qrtr_kprobe_summary", json.dumps(qrtr_kprobe_summary, sort_keys=True)],
                ],
            ),
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
            "## Rollback Gate",
            "",
            f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
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
            "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for CNSS/WLFW/QRTR observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.",
            "",
            "## Next",
            "",
            "- Use the selected label as the handoff result; do not pivot to SDX50M/pcie1/eSoC/GDSC.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
            "",
        ]
    )


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    parser_results: dict[str, Any] = {}
    if execute and base_pass:
        android_dir = evidence_base(store)
        for name, command, timeout, manifest_path in parser_commands(store, android_dir):
            step = execute_parser_step(store, name, command, timeout, execute=True)
            steps.append(step)
            key = "v1894" if "v1894" in name else "v1888"
            parser_results[key] = read_json(manifest_path)
    elif not execute:
        for name, command, timeout, _manifest_path in parser_commands(store, evidence_base(store)):
            steps.append(execute_parser_step(store, name, command, timeout, execute=False))

    selftest_ok = rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(
            base_decision,
            base_pass,
            context,
            parser_results,
            selftest_ok,
        )
    else:
        decision = "v1899-android-normal-cnss-qrtr-edge-plan-ready" if args.command == "plan" else "v1899-android-normal-cnss-qrtr-edge-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-normal-cnss-qrtr-edge-handoff-ready"

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
