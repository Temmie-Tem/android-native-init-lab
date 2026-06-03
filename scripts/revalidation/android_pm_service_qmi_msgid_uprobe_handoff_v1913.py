#!/usr/bin/env python3
"""V1913 Android-good pm-service QMI msg-id uprobe handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521
import android_service_notifier_symbol_owner_handoff_v1912 as common


CYCLE = "V1913"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1913-android-pm-service-qmi-msgid-uprobe-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1913_ANDROID_PM_SERVICE_QMI_MSGID_UPROBE_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1913-android-pm-service-qmi-msgid-uprobe-handoff.txt")

MODULE_NAME = "a90_v1913_pm_msgid_uprobe"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1913-pm-msgid-uprobe"
PM_SERVICE = "/vendor/bin/pm-service"

DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
TRACE_LABEL_RE = re.compile(r":\s+(?P<label>pm_qmi_[A-Za-z0-9_]+):")
MSGID_RE = re.compile(r"\bmsgid=(?P<value>0x[0-9a-fA-F]+|\d+)\b")
SERVICE74_RE = re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE)
SERVICE180_RE = re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0|\bwlan0\b", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)


EVENT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("pm_qmi_dispatch", "733c", "service=%x0 txn=%x1 msgid=%x2 req=%x3 extra4=%x4 extra5=%x5"),
    ("pm_qmi_msg20_entry", "6ebc", "service=%x0 txn=%x1 msgid=%x2 req=%x3"),
    ("pm_qmi_msg21_entry", "7014", "service=%x0 txn=%x1 msgid=%x2 req=%x3"),
    ("pm_qmi_msg22_entry", "716c", "service=%x0 txn=%x1 msgid=%x2 req=%x3 list=%x4 extra5=%x5"),
    ("pm_qmi_msg20_ind_send", "6f88", "service=%x0 ind_msg=%x1 payload=%x2 len=%x3"),
    ("pm_qmi_msg21_ind_send", "70dc", "service=%x0 ind_msg=%x1 payload=%x2 len=%x3"),
    ("pm_qmi_msg22_resp_send", "725c", "service=%x0 txn=%x1 payload=%x2 len=%x3"),
    ("pm_qmi_unknown", "7380", "msgid=%x8"),
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
    parser.add_argument("--sampler-samples", type=int, default=1)
    parser.add_argument("--sampler-delay-us", type=int, default=0)
    parser.add_argument("--sampler-wait-timeout", type=int, default=100)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1913 pm-service QMI msg-id uprobe observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary Android-good tracefs uprobe observer for pm-service QMI msg-id dispatch. Remove after capture.",
            "",
        ]
    )


def event_shell_lines() -> tuple[str, str, str, str]:
    labels = " ".join(label for label, _offset, _fetch in EVENT_SPECS)
    register_calls = "\n".join(
        f"register_event {label} {offset} {fetch!r}"
        for label, offset, fetch in EVENT_SPECS
    )
    enable_calls = "\n".join(f"enable_event {label}" for label, _offset, _fetch in EVENT_SPECS)
    count_calls = "\n".join(f"count_event {label}" for label, _offset, _fetch in EVENT_SPECS)
    return labels, register_calls, enable_calls, count_calls


def post_fs_data_script(samples: int, delay_us: int) -> str:
    del samples, delay_us
    labels, register_calls, enable_calls, count_calls = event_shell_lines()
    filter_expr = (
        "PerMgrSrv|PerMgrLib|QMI service|QMI client|peripheral restart|system restart|"
        "system shutdown|cnss-daemon|wlfw_service_request|WLFW service connected|wlanmdsp|"
        "tftp_server|service-notifier|servloc|sysmon-qmi|icnss_qmi|icnss|wlan_pd|wlan0|"
        "PCIe|MHI|esoc0.*boot.*fail|boot_failed"
    )
    grep_labels = "|".join(label for label, _offset, _fetch in EVENT_SPECS)
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
BIN={PM_SERVICE}
GROUP=a90pm1913
LABELS='{labels}'
FILTER='{filter_expr}'
GREP_LABELS='{grep_labels}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
SAMPLES_LOG="$OUT/samples.log"
SETUP="$OUT/tracefs-setup.log"
TRACELOG="$OUT/tracefs-pm-msgid.txt"
COUNTS="$OUT/tracefs-counts.txt"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
REQUEST="$OUT/request-lines.txt"
PROC="$OUT/process-targets.txt"
TRACE=
ORIG_TRACING_ON=

uptime_now() {{
  cat /proc/uptime 2>/dev/null | awk '{{print $1}}'
}}

write_status() {{
  now="$(uptime_now)"
  echo "A90_V1913_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

pick_tracefs() {{
  for candidate in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    [ -d "$candidate" ] && {{ TRACE="$candidate"; return 0; }}
  done
  mkdir -p /sys/kernel/tracing 2>/dev/null || true
  mount -t tracefs tracefs /sys/kernel/tracing 2>>"$SETUP" || true
  [ -d /sys/kernel/tracing ] && TRACE=/sys/kernel/tracing && return 0
  return 1
}}

cleanup() {{
  [ -n "$TRACE" ] || return 0
  for label in $LABELS; do
    [ -e "$TRACE/events/$GROUP/$label/enable" ] && echo 0 > "$TRACE/events/$GROUP/$label/enable" 2>/dev/null || true
  done
  for label in $LABELS; do
    echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null || true
  done
  [ -n "$ORIG_TRACING_ON" ] && echo "$ORIG_TRACING_ON" > "$TRACE/tracing_on" 2>/dev/null || true
}}
trap cleanup EXIT INT TERM

dump_logs() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 3000 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -b all -d -v threadtime 2>/dev/null | grep -Ei "$FILTER" | tail -n 3000 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
  ps -A -o USER,PID,PPID,STAT,COMM,ARGS 2>/dev/null | grep -Ei 'pm-service|per_mgr|cnss-daemon|tftp_server|rmt_storage|servloc|sysmon' > "$PROC.tmp" || true
  mv "$PROC.tmp" "$PROC" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

register_event() {{
  label="$1"
  offset="$2"
  fetch="$3"
  echo "-:$GROUP/$label" >> "$TRACE/uprobe_events" 2>/dev/null || true
  event_line="p:$GROUP/$label $BIN:0x$offset $fetch"
  if echo "$event_line" >> "$TRACE/uprobe_events" 2>>"$SETUP"; then
    echo "event.$label.register=ok offset=0x$offset fetch=$fetch" >> "$SETUP"
  else
    echo "event.$label.register=failed offset=0x$offset fetch=$fetch" >> "$SETUP"
  fi
}}

enable_event() {{
  label="$1"
  if [ -e "$TRACE/events/$GROUP/$label/enable" ]; then
    if echo 1 > "$TRACE/events/$GROUP/$label/enable" 2>>"$SETUP"; then
      echo "event.$label.enable=ok" >> "$SETUP"
    else
      echo "event.$label.enable=failed" >> "$SETUP"
    fi
  else
    echo "event.$label.enable=missing" >> "$SETUP"
  fi
}}

count_event() {{
  label="$1"
  printf 'event.%s.count=' "$label" >> "$COUNTS.tmp"
  grep -Ec ": $label:" "$TRACELOG" 2>/dev/null >> "$COUNTS.tmp" || echo 0 >> "$COUNTS.tmp"
}}

(
  umask 022
  : > "$SAMPLES_LOG"
  : > "$SETUP"
  echo "A90_V1913_POSTFS_BEGIN uptime=$(uptime_now)" >> "$SAMPLES_LOG"
  write_status start
  if ! pick_tracefs; then
    echo "tracefs=missing" >> "$SETUP"
    write_status tracefs-missing
    dump_logs
    dump_props
    touch "$OUT/done"
    exit 0
  fi
  echo "tracefs=$TRACE" >> "$SETUP"
  echo "binary=$BIN" >> "$SETUP"
  echo "group=$GROUP" >> "$SETUP"
  ORIG_TRACING_ON="$(cat "$TRACE/tracing_on" 2>/dev/null)"
  echo 0 > "$TRACE/tracing_on" 2>>"$SETUP" || true
  echo 4096 > "$TRACE/buffer_size_kb" 2>>"$SETUP" || true
  : > "$TRACE/trace" 2>>"$SETUP" || true
{register_calls}
{enable_calls}
  echo 1 > "$TRACE/tracing_on" 2>>"$SETUP" || true
  echo "A90_V1913_TRACE_ARMED uptime=$(uptime_now)" >> "$SAMPLES_LOG"
  dump_logs
  dump_props
  write_status armed
  sleep 26
  write_status finalizing
  dump_logs
  dump_props
  grep -Ei "$GREP_LABELS" "$TRACE/trace" 2>/dev/null | head -n 3000 > "$TRACELOG.tmp" || true
  mv "$TRACELOG.tmp" "$TRACELOG" 2>/dev/null || true
  : > "$COUNTS.tmp"
{count_calls}
  printf 'dispatch_msgid_0x20=' >> "$COUNTS.tmp"; grep -E 'pm_qmi_dispatch: .*msgid=0x20\\b' "$TRACELOG" 2>/dev/null | wc -l >> "$COUNTS.tmp"
  printf 'dispatch_msgid_0x21=' >> "$COUNTS.tmp"; grep -E 'pm_qmi_dispatch: .*msgid=0x21\\b' "$TRACELOG" 2>/dev/null | wc -l >> "$COUNTS.tmp"
  printf 'dispatch_msgid_0x22=' >> "$COUNTS.tmp"; grep -E 'pm_qmi_dispatch: .*msgid=0x22\\b' "$TRACELOG" 2>/dev/null | wc -l >> "$COUNTS.tmp"
  mv "$COUNTS.tmp" "$COUNTS" 2>/dev/null || true
  {{
    cat "$TRACELOG" 2>/dev/null | grep -Ei 'pm_qmi|msgid=0x20|msgid=0x21|msgid=0x22' || true
    if grep -Eq 'pm_qmi_msg22_entry|pm_qmi_dispatch: .*msgid=0x22\\b' "$TRACELOG" 2>/dev/null; then
      echo "A90_V1913_PM_UPROBE msg0x22 observed"
    fi
  }} > "$REQUEST.tmp"
  mv "$REQUEST.tmp" "$REQUEST" 2>/dev/null || true
  cleanup
  echo "A90_V1913_POSTFS_END uptime=$(uptime_now)" >> "$SAMPLES_LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def read_pulled(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / Path(REMOTE_EVIDENCE_DIR).name
    return candidate if candidate.is_dir() else root


def parse_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            counts[key.strip()] = int(value.strip())
        except ValueError:
            counts[key.strip()] = 0
    return counts


def first_dmesg_time(lines: list[str], regex: re.Pattern[str]) -> float | None:
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_lines(lines: list[str] | str, regex: re.Pattern[str]) -> int:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    return sum(1 for line in iterable if regex.search(line))


def first_line(lines: list[str] | str, regex: re.Pattern[str]) -> str:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    for line in iterable:
        if regex.search(line):
            return line.strip()
    return ""


def count_dmesg_before(lines: list[str], regex: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def trace_labels(trace_text: str) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line in trace_text.splitlines():
        match = TRACE_LABEL_RE.search(line)
        if not match:
            continue
        label = match.group("label")
        labels[label] = labels.get(label, 0) + 1
    return labels


def trace_msgids(trace_text: str) -> list[str]:
    values: list[str] = []
    for line in trace_text.splitlines():
        if "pm_qmi_dispatch:" not in line:
            continue
        match = MSGID_RE.search(line)
        if match:
            values.append(match.group("value").lower())
    return values


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    samples = read_pulled(base / "samples.log")
    trace_text = read_pulled(base / "tracefs-pm-msgid.txt")
    counts_text = read_pulled(base / "tracefs-counts.txt")
    setup = read_pulled(base / "tracefs-setup.log")
    dmesg = read_pulled(base / "dmesg-filtered.txt") + "\n" + read_pulled(root / "host-dmesg-filtered.txt")
    logcat = read_pulled(base / "logcat-filtered.txt")
    request = read_pulled(base / "request-lines.txt")
    props = read_pulled(base / "props.txt")
    status = read_pulled(base / "status.txt")
    process = read_pulled(base / "process-targets.txt")
    parsed_counts = parse_counts(counts_text)
    labels = trace_labels(trace_text)
    msgids = trace_msgids(trace_text)
    dmesg_lines = dmesg.splitlines()
    logcat_lines = logcat.splitlines()
    all_lines = dmesg_lines + logcat_lines
    wlan0_time = first_dmesg_time(dmesg_lines, WLAN0_RE)
    pcie_mhi_before = count_dmesg_before(dmesg_lines, PCIE_MHI_RE, wlan0_time)
    esoc_failed_before = count_dmesg_before(dmesg_lines, ESOC_BOOT_FAILED_RE, wlan0_time)
    return {
        "base": common.rel(base),
        "files_present": {
            "samples": bool(samples),
            "dmesg": bool(dmesg.strip()),
            "props": bool(props),
            "status": bool(status),
            "done": (base / "done").exists(),
            "trace": bool(trace_text.strip()),
            "counts": bool(counts_text.strip()),
            "setup": bool(setup.strip()),
            "request_lines": bool(request.strip()),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1913_POSTFS_BEGIN"),
        "setup_excerpt": setup.strip().splitlines()[:120],
        "trace_counts": parsed_counts,
        "trace_label_counts": labels,
        "trace_msgids": msgids,
        "trace_line_count": len(trace_text.splitlines()) if trace_text else 0,
        "dispatch_count": labels.get("pm_qmi_dispatch", 0),
        "dispatch_msgid_0x20": parsed_counts.get("dispatch_msgid_0x20", msgids.count("0x20")),
        "dispatch_msgid_0x21": parsed_counts.get("dispatch_msgid_0x21", msgids.count("0x21")),
        "dispatch_msgid_0x22": parsed_counts.get("dispatch_msgid_0x22", msgids.count("0x22")),
        "msg20_entry_count": labels.get("pm_qmi_msg20_entry", 0),
        "msg21_entry_count": labels.get("pm_qmi_msg21_entry", 0),
        "msg22_entry_count": labels.get("pm_qmi_msg22_entry", 0),
        "msg22_observed": labels.get("pm_qmi_msg22_entry", 0) > 0 or "0x22" in msgids,
        "trace_excerpt": trace_text.splitlines()[:80],
        "request_lines_excerpt": request.splitlines()[:80],
        "process_text": process.strip(),
        "dmesg": {
            "wlfw_lines": count_lines(all_lines, re.compile(r"\bwlfw\b|WLFW", re.IGNORECASE)),
            "bdf_lines": count_lines(all_lines, re.compile(r"BDF file|regdb\.bin|bdwlan\.bin", re.IGNORECASE)),
            "wlan0_lines": count_lines(all_lines, re.compile(r"\bwlan0\b", re.IGNORECASE)),
            "wlan0_time_s": wlan0_time,
            "pcie_mhi_before_wlan0": pcie_mhi_before,
            "esoc_boot_failed_before_wlan0": esoc_failed_before,
            "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        },
        "service74_count": count_lines(dmesg_lines, SERVICE74_RE),
        "service180_count": count_lines(dmesg_lines, SERVICE180_RE),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlfw_service_request_count": count_lines(all_lines, WLFW_REQUEST_RE),
        "wlanmdsp_count": count_lines(all_lines, WLANMDSP_RE),
        "first_service74_line": first_line(dmesg_lines, SERVICE74_RE),
        "first_service180_line": first_line(dmesg_lines, SERVICE180_RE),
        "first_wlan_pd_line": first_line(dmesg_lines, WLAN_PD_RE),
        "first_wlanmdsp_line": first_line(all_lines, WLANMDSP_RE),
        "props_text": props.strip(),
        "matched_window": {"first_lower_time": wlan0_time},
    }


def classify_result(base_decision: str, base_pass: bool, analysis: dict[str, Any], selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return ("v1913-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed")
    if not base_pass:
        return (f"v1913-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed")
    files = analysis.get("files_present") or {}
    if not files.get("setup"):
        return ("v1913-android-pm-msgid-uprobe-setup-missing", False, "Android capture completed but tracefs setup evidence is missing", "android-pm-msgid-uprobe-setup-missing")
    dmesg = analysis.get("dmesg") or {}
    contaminated = common.boolish(dmesg.get("degraded_257s_like")) or common.intish(dmesg.get("pcie_mhi_before_wlan0")) > 0 or common.intish(dmesg.get("esoc_boot_failed_before_wlan0")) > 0
    if contaminated:
        return ("v1913-android-capture-rejected-degraded-or-pcie-mhi", False, "Android capture was degraded or had pre-wlan0 PCIe/MHI/eSoC contamination", "android-capture-rejected-degraded-or-pcie-mhi")
    stateup = (
        common.intish(analysis.get("service74_count")) > 0
        and common.intish(analysis.get("service180_count")) > 0
        and common.intish(analysis.get("wlan_pd_indication_count")) > 0
        and common.intish(analysis.get("wlanmdsp_count")) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    if not stateup:
        return ("v1913-android-normal-stateup-incomplete-rollback-pass", False, "Android capture did not prove normal service74/180 -> wlan_pd -> wlan0 state-up", "android-normal-stateup-incomplete")
    if common.intish(analysis.get("dispatch_count")) == 0:
        return (
            "v1913-android-pm-msgid-uprobe-no-dispatch-hit-rollback-pass",
            True,
            "normal Android state-up was captured, but pm-service QMI dispatch uprobe had no hits",
            "android-pm-msgid-uprobe-no-dispatch-hit",
        )
    if common.boolish(analysis.get("msg22_observed")):
        return (
            "v1913-android-pm-service-qmi-msg0x22-dispatch-observed-pass",
            True,
            "normal Android state-up captured and pm-service QMI dispatch hit msgid 0x22 / msg22 branch",
            "android-pm-service-qmi-msg0x22-dispatch-observed",
        )
    return (
        "v1913-android-pm-service-qmi-dispatch-without-msg0x22-pass",
        True,
        "normal Android state-up captured and pm-service QMI dispatch hit, but msgid 0x22 branch was not observed in the bounded window",
        "android-pm-service-qmi-dispatch-without-msg0x22",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    return "\n".join(
        [
            "# Native Init V1913 Android pm-service QMI Msg-id Uprobe Handoff",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            f"- Type: rollbackable Android-good tracefs uprobe capture for `/vendor/bin/pm-service` QMI msg-id dispatch",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Android-good State-up",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["service74/service180/wlan_pd/wlanmdsp/wlan0", f"{analysis.get('service74_count')}/{analysis.get('service180_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}"],
                    ["wlfw service request", analysis.get("wlfw_service_request_count")],
                    ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
                    ["first service74", analysis.get("first_service74_line", "")],
                    ["first wlan_pd", analysis.get("first_wlan_pd_line", "")],
                ],
            ),
            "",
            "## pm-service Uprobes",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["dispatch/msg20/msg21/msg22", f"{analysis.get('dispatch_count')}/{analysis.get('msg20_entry_count')}/{analysis.get('msg21_entry_count')}/{analysis.get('msg22_entry_count')}"],
                    ["dispatch msgid 0x20/0x21/0x22", f"{analysis.get('dispatch_msgid_0x20')}/{analysis.get('dispatch_msgid_0x21')}/{analysis.get('dispatch_msgid_0x22')}"],
                    ["trace msgids", json.dumps(analysis.get("trace_msgids") or [])],
                    ["trace label counts", json.dumps(analysis.get("trace_label_counts") or {}, sort_keys=True)],
                    ["trace line count", analysis.get("trace_line_count")],
                ],
            ),
            "",
            "## Evidence Files",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["base", analysis.get("base")],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                    ["rollback selftest fail=0", manifest.get("rollback_selftest_fail0")],
                    ["base decision", manifest.get("base_decision")],
                    ["setup excerpt", json.dumps(analysis.get("setup_excerpt") or [])],
                ],
            ),
            "",
            "## Trace Excerpt",
            "",
            "```text",
            "\n".join(analysis.get("trace_excerpt") or []),
            "```",
            "",
            "## Safety Scope",
            "",
            "Rollbackable Android-handoff to native v724 only. Android-side diagnostic writes are limited to temporary tracefs uprobe controls, the temporary Magisk module, and a bounded evidence directory. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, or partition write beyond the declared boot-image handoff/rollback.",
            "",
            "## Next",
            "",
            "- Feed this Android-good `android/`-style evidence directory back through V1894/V1888 to keep the pending-client/msg22 comparison labels current.",
            "- Keep native follow-up on internal-modem pm-service/QMI/servreg only; do not pivot to SDX50M/PCIe/GDSC.",
            "",
        ]
    )


def configure_engine() -> None:
    common.CYCLE = CYCLE
    common.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    common.DEFAULT_NATIVE_IMAGE = DEFAULT_NATIVE_IMAGE
    common.DEFAULT_NATIVE_EXPECT_VERSION = DEFAULT_NATIVE_EXPECT_VERSION
    common.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    common.LATEST_POINTER = LATEST_POINTER
    common.MODULE_NAME = MODULE_NAME
    common.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    common.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
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
    v1521.analyze_pulled_evidence = analyze_pulled_evidence
    v1521.build_plan = common.build_plan_v1912


def main() -> int:
    configure_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    analysis = context.get("analysis") or {}
    selftest_ok = common.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, analysis, selftest_ok)
    else:
        decision = "v1913-android-pm-service-qmi-msgid-uprobe-plan-ready" if args.command == "plan" else "v1913-android-pm-service-qmi-msgid-uprobe-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-pm-service-qmi-msgid-uprobe-handoff-ready"
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
        "out_dir": common.rel(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "tracefs_write_executed": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "restart_pd_request_executed": False,
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
    sys.exit(main())
