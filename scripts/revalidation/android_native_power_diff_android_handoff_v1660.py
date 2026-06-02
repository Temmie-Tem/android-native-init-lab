#!/usr/bin/env python3
"""V1660 Android-good power/clock/sequence diff reference handoff.

This runner reuses the V1521 Android/Magisk/native-rollback handoff engine and
installs a temporary Android post-fs-data module that records a bounded,
minimal tracefs/dmesg window.  It implements the Android-good half of the V1659/V1662 Android-vs-native
power/clock/sequence diff contract. Only GPIO and IRQ tracefs events are
enabled; regulator state is captured with full read-only snapshots and clocks
are captured through targeted named-clock reads.

It is a reference capture only.  The module does not start Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, ping externally, write
PMIC/GPIO/GDSC/eSoC state, spoof BOOT_DONE, rescan PCI, or bind/unbind
platforms.  Android-side diagnostic writes are limited to temporary tracefs
control writes, a bounded evidence directory under `/data/local/tmp`, and
temporary Magisk module cleanup.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text
from android_hwservice_handoff_v424 import (
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_REMOTE_ANDROID_IMAGE,
)

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521


DEFAULT_OUT_DIR = Path("tmp/wifi/v1660-android-good-power-diff-reference")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1660_ANDROID_GOOD_POWER_DIFF_REFERENCE_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1660-android-good-power-diff-reference.txt")

MODULE_NAME = "a90_v1660_android_power_diff_ref"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1660-android-power-diff-ref"

DMESG_TARGET_RE = (
    r"subsys-restart|__subsystem_get|esoc0|mdm|pm-service|pm_proxy|mdm_helper|"
    r"gpio|msm_pcie|PCIe|RC1|LTSSM|MHI|mhi|icnss|wlfw|WLFW|"
    r"BDF file|bdwlan|regdb|FW ready|WLAN FW is ready|wlan0"
)
TRACE_TARGET_RE = r"gpio[^0-9]*(102|104|135|141|142)|irq=(204|252|289|290)|irq [^0-9]*(204|252|289|290)"


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
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=360)
    parser.add_argument("--sampler-samples", type=int, default=360)
    parser.add_argument("--sampler-delay-us", type=int, default=500000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=260)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.post_fs_data_script = post_fs_data_script
    v1521.module_prop = module_prop
    v1521.analyze_pulled_evidence = analyze_pulled_evidence


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1660 Android-good Power Diff Reference",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary Android-good read-only power/clock/sequence reference for V1659 diff. Remove after capture.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    dmesg_re = DMESG_TARGET_RE.replace("'", "'\"'\"'")
    trace_re = TRACE_TARGET_RE.replace("'", "'\"'\"'")
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
SAMPLES={samples}
DELAY_US={delay_us}
DMESG_RE='{dmesg_re}'
TRACE_RE='{trace_re}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
TRACELOG="$OUT/tracefs-targets.txt"
COUNTS="$OUT/tracefs-counts.txt"
EVENTS="$OUT/tracefs-setup.log"
SAMPLES_LOG="$OUT/samples.log"
DMSG="$OUT/dmesg-filtered.txt"
PROPS="$OUT/props.txt"
FORMATS="$OUT/tracefs-formats.txt"
REGFULL="$OUT/regulator-full.log"
CLKTGT="$OUT/clock-targets.log"
SUBSYS="$OUT/subsys-sequence.log"
write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1660_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}
dump_filtered_dmesg() {{
  dmesg 2>&1 | grep -Ei "$DMESG_RE" > "$DMSG.tmp"
  mv "$DMSG.tmp" "$DMSG" 2>/dev/null || true
}}
dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.per_proxy init.svc.vendor.mdm_helper init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.per_proxy ro.boottime.vendor.mdm_helper ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}
dump_regulator_full() {{
  i="$1"
  uptime="$2"
  echo "A90_V1660_REGULATOR_BEGIN index=$i uptime=$uptime" >> "$REGFULL"
  if [ -r /sys/kernel/debug/regulator/regulator_summary ]; then
    cat /sys/kernel/debug/regulator/regulator_summary >> "$REGFULL" 2>/dev/null || true
  elif [ -r /sys/kernel/debug/regulator_summary ]; then
    cat /sys/kernel/debug/regulator_summary >> "$REGFULL" 2>/dev/null || true
  else
    echo unreadable >> "$REGFULL"
  fi
  echo "A90_V1660_REGULATOR_END index=$i uptime=$uptime" >> "$REGFULL"
}}
dump_target_clocks() {{
  i="$1"
  uptime="$2"
  echo "A90_V1660_CLOCKS_BEGIN index=$i uptime=$uptime" >> "$CLKTGT"
  CLKROOT=/sys/kernel/debug/clk
  for c in \\
    gcc_pcie_1_aux_clk_src \\
    gcc_pcie_1_aux_clk \\
    gcc_pcie_1_cfg_ahb_clk \\
    gcc_pcie_1_mstr_axi_clk \\
    gcc_pcie_1_slv_axi_clk \\
    gcc_pcie_1_clkref_clk \\
    gcc_pcie_1_slv_q2a_axi_clk \\
    gcc_pcie_phy_refgen_clk_src \\
    gcc_pcie1_phy_refgen_clk \\
    gcc_pcie_1_pipe_clk \\
    pcie_1_pipe_clk; do
    d="$CLKROOT/$c"
    if [ -d "$d" ]; then
      printf 'CLOCK %s' "$c" >> "$CLKTGT"
      for f in clk_enable_count clk_prepare_count clk_rate; do
        if [ -r "$d/$f" ]; then
          v="$(cat "$d/$f" 2>/dev/null)"
          printf ' %s=%s' "$f" "$v" >> "$CLKTGT"
        fi
      done
      printf '\\n' >> "$CLKTGT"
    else
      echo "CLOCK $c missing" >> "$CLKTGT"
    fi
  done
  echo "A90_V1660_CLOCKS_END index=$i uptime=$uptime" >> "$CLKTGT"
}}
dump_subsys_sequence() {{
  i="$1"
  uptime="$2"
  echo "A90_V1660_SUBSYS_BEGIN index=$i uptime=$uptime" >> "$SUBSYS"
  for d in /sys/bus/msm_subsys/devices/subsys*; do
    [ -d "$d" ] || continue
    name="$(cat "$d/name" 2>/dev/null)"
    state="$(cat "$d/state" 2>/dev/null)"
    echo "SUBSYS path=$d name=$name state=$state" >> "$SUBSYS"
  done
  echo "A90_V1660_SUBSYS_END index=$i uptime=$uptime" >> "$SUBSYS"
}}
T=/sys/kernel/tracing
[ -d "$T" ] || mkdir -p "$T" 2>/dev/null || true
if ! grep -q " $T tracefs " /proc/mounts 2>/dev/null; then
  mount -t tracefs tracefs "$T" 2>>"$EVENTS" || true
fi
EVENT_LIST="gpio/gpio_value gpio/gpio_direction irq/irq_handler_entry irq/irq_handler_exit"
enable_event() {{
  e="$1"
  if [ -e "$T/events/$e/enable" ]; then
    echo 1 > "$T/events/$e/enable" 2>>"$EVENTS" && echo "enabled $e" >> "$EVENTS" || echo "enable_failed $e" >> "$EVENTS"
  else
    echo "missing $e" >> "$EVENTS"
  fi
}}
disable_event() {{
  e="$1"
  if [ -e "$T/events/$e/enable" ]; then
    echo 0 > "$T/events/$e/enable" 2>/dev/null || true
  fi
}}
dump_formats() {{
  : > "$FORMATS.tmp"
  for e in $EVENT_LIST; do
    echo "== $e ==" >> "$FORMATS.tmp"
    if [ -r "$T/events/$e/format" ]; then
      cat "$T/events/$e/format" >> "$FORMATS.tmp" 2>/dev/null || true
    else
      echo unreadable >> "$FORMATS.tmp"
    fi
  done
  mv "$FORMATS.tmp" "$FORMATS" 2>/dev/null || true
}}
dump_sample() {{
  i="$1"
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1660_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "SRC interrupts" >> "$SAMPLES_LOG"
  cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +142|msmgpio-dc +104|mdm status|errfatal|msm_pcie_wake|mhi|pcie' >> "$SAMPLES_LOG" 2>/dev/null || true
  echo "SRC debug_gpio" >> "$SAMPLES_LOG"
  if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio141|gpio142' /sys/kernel/debug/gpio >> "$SAMPLES_LOG" 2>/dev/null || true; else echo unreadable >> "$SAMPLES_LOG"; fi
  if [ "$((i % 8))" = "0" ]; then
    dump_regulator_full "$i" "$uptime"
    dump_target_clocks "$i" "$uptime"
    dump_subsys_sequence "$i" "$uptime"
  fi
  if [ "$((i % 24))" = "0" ]; then
    echo "SRC pinmux" >> "$SAMPLES_LOG"
    for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
      [ -r "$f" ] || continue
      grep -Ei 'pin 102 |pin 103 |pin 104 |pin 135 |pin 141 |pin 142 ' "$f" >> "$SAMPLES_LOG" 2>/dev/null || true
    done
  fi
  echo "A90_V1660_SAMPLE_END index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$SAMPLES_LOG"
}}
write_status start
echo "A90_V1660_TRACEFS_SETUP_BEGIN" > "$EVENTS"
if grep -q " $T tracefs " /proc/mounts 2>/dev/null; then TRACEFS_MOUNTED=1; else TRACEFS_MOUNTED=0; fi
echo "tracefs_mounted=$TRACEFS_MOUNTED" >> "$EVENTS"
PREV_ON="$(cat "$T/tracing_on" 2>/dev/null)"
echo "prev_tracing_on=$PREV_ON" >> "$EVENTS"
dump_formats
echo 0 > "$T/tracing_on" 2>>"$EVENTS" || true
echo 4096 > "$T/buffer_size_kb" 2>>"$EVENTS" || true
: > "$T/trace" 2>>"$EVENTS" || true
for e in $EVENT_LIST; do enable_event "$e"; done
echo 1 > "$T/tracing_on" 2>>"$EVENTS" || true
(
  echo A90_V1660_TRACEFS_SAMPLER_BEGIN > "$SAMPLES_LOG"
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1660_STATUS sample $i $uptime" > "$STATUS"
    echo "A90_V1521_STATUS sample $i $uptime" >> "$STATUS"
    dump_sample "$i"
    if [ "$((i % 10))" = "0" ]; then
      dump_filtered_dmesg
      dump_props
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  echo A90_V1660_TRACEFS_SAMPLER_END >> "$SAMPLES_LOG"
)
write_status finalizing
sleep 1
grep -Ei "$TRACE_RE" "$T/trace" 2>/dev/null | head -n 3000 > "$TRACELOG.tmp" || true
mv "$TRACELOG.tmp" "$TRACELOG" 2>/dev/null || true
for e in $EVENT_LIST; do disable_event "$e"; done
if [ -n "$PREV_ON" ]; then echo "$PREV_ON" > "$T/tracing_on" 2>/dev/null || true; else echo 0 > "$T/tracing_on" 2>/dev/null || true; fi
dump_filtered_dmesg
dump_props
(
  printf 'target_lines='; grep -Ec '.' "$TRACELOG" 2>/dev/null || true
  printf 'gpio102='; grep -Eic 'gpio[^0-9]*102' "$TRACELOG" 2>/dev/null || true
  printf 'gpio104='; grep -Eic 'gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)' "$TRACELOG" 2>/dev/null || true
  printf 'gpio135='; grep -Eic 'gpio[^0-9]*135' "$TRACELOG" 2>/dev/null || true
  printf 'gpio141='; grep -Eic 'gpio[^0-9]*141|irq=289|irq [^0-9]*289|errfatal' "$TRACELOG" 2>/dev/null || true
  printf 'gpio142='; grep -Eic 'gpio[^0-9]*142|irq=290|irq [^0-9]*290' "$TRACELOG" 2>/dev/null || true
  printf 'l0='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic 'LTSSM.*L0|Current GEN[0-9]|PCIe RC1 Current' || true
  printf 'mhi='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic '\\bmhi\\b|MHI' || true
  printf 'wlfw_bdf_wlan='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic 'wlfw|WLFW|BDF|bdwlan|regdb|FW ready|WLAN FW is ready|wlan0' || true
  printf 'regulator_snapshots='; grep -Ec '^A90_V1660_REGULATOR_BEGIN' "$REGFULL" 2>/dev/null || true
  printf 'clock_snapshots='; grep -Ec '^A90_V1660_CLOCKS_BEGIN' "$CLKTGT" 2>/dev/null || true
  printf 'subsys_snapshots='; grep -Ec '^A90_V1660_SUBSYS_BEGIN' "$SUBSYS" 2>/dev/null || true
) > "$COUNTS.tmp"
mv "$COUNTS.tmp" "$COUNTS" 2>/dev/null || true
write_status done
touch "$OUT/done"
chmod 755 "$OUT" 2>/dev/null
chmod 644 "$OUT"/* 2>/dev/null
exit 0
"""


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1660-android-power-diff-ref"
    return candidate if candidate.is_dir() else root


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in text.splitlines() if regex.search(line))


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def first_trace_time(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
        if match:
            return float(match.group(1))
    return None


def matching_lines(text: str, pattern: str, limit: int = 24) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


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


def sample_uptimes(text: str) -> list[float]:
    return [
        float(match.group(1))
        for match in re.finditer(r"A90_V1660_SAMPLE_BEGIN index=\d+ uptime=([0-9.]+)", text)
    ]


def marker_uptimes(text: str, marker: str) -> list[float]:
    return [
        float(match.group(1))
        for match in re.finditer(rf"^{re.escape(marker)} index=\d+ uptime=([0-9.]+)", text, re.M)
    ]


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    base = evidence_base(store)
    trace_text = read_file(base / "tracefs-targets.txt")
    counts_text = read_file(base / "tracefs-counts.txt")
    samples_text = read_file(base / "samples.log")
    setup_log = read_file(base / "tracefs-setup.log")
    formats = read_file(base / "tracefs-formats.txt")
    module_dmesg = read_file(base / "dmesg-filtered.txt")
    host_dmesg = read_file(v1521.pulled_evidence_dir(store) / "host-dmesg-filtered.txt")
    props_text = read_file(base / "props.txt")
    status_text = read_file(base / "status.txt")
    regulator_text = read_file(base / "regulator-full.log")
    clock_text = read_file(base / "clock-targets.log")
    subsys_text = read_file(base / "subsys-sequence.log")
    dmesg_text = "\n".join(part for part in (module_dmesg, host_dmesg) if part)
    parsed_counts = parse_counts(counts_text)
    uptimes = sample_uptimes(samples_text)
    regulator_uptimes = marker_uptimes(regulator_text, "A90_V1660_REGULATOR_BEGIN")
    clock_uptimes = marker_uptimes(clock_text, "A90_V1660_CLOCKS_BEGIN")
    subsys_uptimes = marker_uptimes(subsys_text, "A90_V1660_SUBSYS_BEGIN")
    wlfw_time = first_ts(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_ts(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    fw_ready_time = first_ts(dmesg_text, r"FW ready|WLAN FW is ready")
    wlan0_time = first_ts(dmesg_text, r"\bwlan0\b")
    l0_time = first_ts(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes")
    esoc0_time = first_ts(dmesg_text, r"__subsystem_get: esoc0")
    first_lower_time = min(
        [value for value in (wlfw_time, bdf_time, fw_ready_time, wlan0_time) if value is not None],
        default=None,
    )
    first_sample = uptimes[0] if uptimes else None
    last_sample = uptimes[-1] if uptimes else None
    android_lower_ok = (
        wlfw_time is not None and bdf_time is not None and fw_ready_time is not None and wlan0_time is not None
    )
    trace_counts = {
        "target_lines": parsed_counts.get("target_lines", count_lines(trace_text, r".")),
        "gpio102": parsed_counts.get("gpio102", count_lines(trace_text, r"gpio[^0-9]*102")),
        "gpio104": parsed_counts.get("gpio104", count_lines(trace_text, r"gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)")),
        "gpio135": parsed_counts.get("gpio135", count_lines(trace_text, r"gpio[^0-9]*135")),
        "gpio141": parsed_counts.get("gpio141", count_lines(trace_text, r"gpio[^0-9]*141|irq=289|irq [^0-9]*289|errfatal")),
        "gpio142": parsed_counts.get("gpio142", count_lines(trace_text, r"gpio[^0-9]*142|irq=290|irq [^0-9]*290")),
        "l0": parsed_counts.get("l0", count_lines(trace_text + "\n" + dmesg_text, r"LTSSM.*L0|Current GEN[0-9]|PCIe RC1 Current")),
        "mhi": parsed_counts.get("mhi", count_lines(trace_text + "\n" + dmesg_text, r"\bmhi\b|MHI")),
        "wlfw_bdf_wlan": parsed_counts.get("wlfw_bdf_wlan", count_lines(trace_text + "\n" + dmesg_text, r"wlfw|WLFW|BDF|bdwlan|regdb|FW ready|WLAN FW is ready|wlan0")),
        "regulator_snapshots": parsed_counts.get("regulator_snapshots", len(regulator_uptimes)),
        "clock_snapshots": parsed_counts.get("clock_snapshots", len(clock_uptimes)),
        "subsys_snapshots": parsed_counts.get("subsys_snapshots", len(subsys_uptimes)),
    }
    power_diff_snapshots_ok = (
        bool(regulator_uptimes)
        and bool(clock_uptimes)
        and bool(subsys_uptimes)
        and bool(regulator_text)
        and bool(clock_text)
        and bool(subsys_text)
    )
    if android_lower_ok and trace_counts["target_lines"] and power_diff_snapshots_ok:
        decision_hint = "android-good-power-diff-reference"
    elif android_lower_ok and power_diff_snapshots_ok:
        decision_hint = "android-good-power-diff-reference-trace-opaque"
    elif android_lower_ok and trace_counts["target_lines"]:
        decision_hint = "android-good-minimal-trace-reference"
    elif android_lower_ok:
        decision_hint = "android-good-lower-ok-trace-opaque"
    elif wlfw_time is not None:
        decision_hint = "android-lower-incomplete-wlfw-only"
    elif trace_counts["target_lines"]:
        decision_hint = "minimal-trace-captured-lower-missing"
    else:
        decision_hint = "minimal-trace-empty-review"
    return {
        "base": str(base),
        "files_present": {
            "samples": bool(samples_text),
            "dmesg": bool(dmesg_text),
            "module_dmesg": bool(module_dmesg),
            "host_dmesg": bool(host_dmesg),
            "props": bool(props_text),
            "status": bool(status_text),
            "done": (base / "done").exists(),
            "trace_targets": bool(trace_text),
            "trace_counts": bool(counts_text),
            "setup": bool(setup_log),
            "formats": bool(formats),
            "regulator_full": bool(regulator_text),
            "clock_targets": bool(clock_text),
            "subsys_sequence": bool(subsys_text),
        },
        "status_text": status_text.strip(),
        "setup_excerpt": setup_log.strip().splitlines()[:60],
        "sample_count": len(uptimes),
        "sample_first_uptime": first_sample,
        "sample_last_uptime": last_sample,
        "dmesg": {
            "esoc0_time": esoc0_time,
            "pcie_l0_time": l0_time,
            "wlfw_time": wlfw_time,
            "bdf_time": bdf_time,
            "fw_ready_time": fw_ready_time,
            "wlan0_time": wlan0_time,
            "pcie_l0_lines": count_lines(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes"),
            "wlfw_lines": count_lines(dmesg_text, r"\bwlfw\b|WLFW"),
            "bdf_lines": count_lines(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "fw_ready_lines": count_lines(dmesg_text, r"FW ready|WLAN FW is ready"),
            "wlan0_lines": count_lines(dmesg_text, r"\bwlan0\b"),
        },
        "matched_window": {
            "first_lower_time": first_lower_time,
            "has_pre_lower_sample": first_sample is not None and first_lower_time is not None and first_sample <= first_lower_time,
            "has_post_lower_sample": last_sample is not None and first_lower_time is not None and last_sample >= first_lower_time,
            "has_pre_l0_sample": first_sample is not None and l0_time is not None and first_sample <= l0_time,
            "has_post_l0_sample": last_sample is not None and l0_time is not None and last_sample >= l0_time,
            "first_sample": {"uptime": first_sample} if first_sample is not None else None,
            "last_sample": {"uptime": last_sample} if last_sample is not None else None,
            "has_pre_esoc_regulator_snapshot": bool(regulator_uptimes and esoc0_time is not None and min(regulator_uptimes) <= esoc0_time),
            "has_post_wlan0_regulator_snapshot": bool(regulator_uptimes and wlan0_time is not None and max(regulator_uptimes) >= wlan0_time),
            "has_pre_esoc_clock_snapshot": bool(clock_uptimes and esoc0_time is not None and min(clock_uptimes) <= esoc0_time),
            "has_post_wlan0_clock_snapshot": bool(clock_uptimes and wlan0_time is not None and max(clock_uptimes) >= wlan0_time),
            "has_pre_esoc_subsys_snapshot": bool(subsys_uptimes and esoc0_time is not None and min(subsys_uptimes) <= esoc0_time),
            "has_post_wlan0_subsys_snapshot": bool(subsys_uptimes and wlan0_time is not None and max(subsys_uptimes) >= wlan0_time),
        },
        "power_diff_reference": {
            "regulator_snapshot_count": len(regulator_uptimes),
            "clock_snapshot_count": len(clock_uptimes),
            "subsys_snapshot_count": len(subsys_uptimes),
            "pcie1_gdsc_lines": count_lines(regulator_text, r"\bpcie_1_gdsc\b"),
            "refgen_or_vdd_lines": count_lines(regulator_text, r"\brefgen\b|PM8150|PMXPRAIRIE|VDD"),
            "target_clock_present_lines": count_lines(clock_text, r"^CLOCK .*clk_.*(enable|prepare|rate)="),
            "target_clock_missing_lines": count_lines(clock_text, r"^CLOCK .* missing$"),
            "subsys_mss_lines": count_lines(subsys_text, r"name=(mss|modem)"),
            "subsys_esoc0_lines": count_lines(subsys_text, r"name=esoc0"),
            "regulator_excerpt": matching_lines(regulator_text, r"pcie_1_gdsc|refgen|PM8150|PMXPRAIRIE|VDD", 24),
            "clock_excerpt": matching_lines(clock_text, r"gcc_pcie|pcie_1|refgen", 24),
            "subsys_excerpt": matching_lines(subsys_text, r"SUBSYS", 24),
        },
        "tracefs_analysis": {
            "decision_hint": decision_hint,
            "trace_counts": trace_counts,
            "first_times": {
                "gpio102": first_trace_time(trace_text, r"gpio[^0-9]*102"),
                "gpio104": first_trace_time(trace_text, r"gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)"),
                "gpio135": first_trace_time(trace_text, r"gpio[^0-9]*135"),
                "gpio141": first_trace_time(trace_text, r"gpio[^0-9]*141|irq=289|irq [^0-9]*289|errfatal"),
                "gpio142": first_trace_time(trace_text, r"gpio[^0-9]*142|irq=290|irq [^0-9]*290"),
            },
            "gpio_irq_excerpt": matching_lines(
                trace_text,
                r"gpio[^0-9]*(102|104|135|141|142)|irq=(204|252|289|290)|irq [^0-9]*(204|252|289|290)|errfatal",
                30,
            ),
            "lower_excerpt": matching_lines(
                dmesg_text,
                r"LTSSM|PCIe RC1|mhi|wlfw|WLFW|BDF|bdwlan|regdb|FW ready|WLAN FW is ready|wlan0",
                36,
            ),
        },
        "android_lower_ok": android_lower_ok,
        "props_text": props_text.strip(),
    }


DECISION_MAP = {
    "v1521-handoff-plan-ready": "v1660-handoff-plan-ready",
    "v1521-handoff-dryrun-ready": "v1660-handoff-dryrun-ready",
    "v1521-magisk-postfs-pre-lower-window-rollback-pass": "v1660-android-good-power-diff-reference-rollback-pass",
    "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass": "v1660-android-good-power-diff-reference-partial-rollback-pass",
    "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass": "v1660-android-good-power-diff-reference-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass": "v1660-android-good-power-diff-reference-partial-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-evidence-captured-rollback-review": "v1660-android-good-power-diff-reference-evidence-rollback-review",
    "v1521-magisk-postfs-partial-evidence-captured-rollback-review": "v1660-android-good-power-diff-reference-partial-evidence-rollback-review",
}


def map_decision(decision: str) -> str:
    return DECISION_MAP.get(decision, decision.replace("v1521", "v1660"))


def classified_decision(command: str, mapped_decision: str, pass_ok: bool, analysis: dict[str, Any]) -> str:
    if command != "run" or not pass_ok:
        return mapped_decision
    hint = ((analysis.get("tracefs_analysis") or {}).get("decision_hint"))
    if hint == "android-good-power-diff-reference":
        return "v1660-android-good-power-diff-reference-pass"
    if hint == "android-good-power-diff-reference-trace-opaque":
        return "v1660-android-good-power-diff-reference-trace-opaque-pass"
    if hint == "android-good-minimal-trace-reference":
        return "v1660-android-good-minimal-only-power-diff-incomplete-review"
    if hint == "android-good-lower-ok-trace-opaque":
        return "v1660-android-good-lower-ok-trace-opaque-pass"
    if hint == "android-lower-incomplete-wlfw-only":
        return "v1660-android-lower-incomplete-wlfw-only-review"
    if hint == "minimal-trace-captured-lower-missing":
        return "v1660-minimal-trace-captured-lower-missing-review"
    return mapped_decision


def reason_for(decision: str, base_decision: str) -> str:
    reasons = {
        "v1660-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1660-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1660-android-good-power-diff-reference-pass": "Android reached BDF/FW-ready/wlan0 and captured regulator/clock/subsystem snapshots under the read-only power-diff observer; native rollback completed",
        "v1660-android-good-power-diff-reference-trace-opaque-pass": "Android reached BDF/FW-ready/wlan0 and captured regulator/clock/subsystem snapshots; GPIO/IRQ tracefs targets were opaque; native rollback completed",
        "v1660-android-good-minimal-only-power-diff-incomplete-review": "Android reached lower Wi-Fi markers, but power-diff regulator/clock/subsystem snapshots were incomplete; native rollback completed",
        "v1660-android-good-lower-ok-trace-opaque-pass": "Android reached BDF/FW-ready/wlan0 under the lower-impact observer, but GPIO/IRQ tracefs targets were opaque; native rollback completed",
        "v1660-android-lower-incomplete-wlfw-only-review": "Android reached only early WLFW markers under the lower-impact observer before rollback; native rollback completed",
        "v1660-minimal-trace-captured-lower-missing-review": "minimal GPIO/IRQ tracefs evidence was captured, but Android lower Wi-Fi markers were missing; native rollback completed",
    }
    return reasons.get(decision) or v1521.reason_for(base_decision)


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    tracefs = analysis.get("tracefs_analysis") or {}
    matched = analysis.get("matched_window") or {}
    power = analysis.get("power_diff_reference") or {}
    return "\n".join(
        [
            "# V1660 Android-good Power Diff Reference Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- base_decision: `{manifest['base_decision']}`",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Analysis",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["sample_count", analysis.get("sample_count")],
                    ["sample_first_uptime", analysis.get("sample_first_uptime")],
                    ["sample_last_uptime", analysis.get("sample_last_uptime")],
                    ["esoc0/L0/wlfw/bdf/fw_ready/wlan0", f"{dmesg.get('esoc0_time')}/{dmesg.get('pcie_l0_time')}/{dmesg.get('wlfw_time')}/{dmesg.get('bdf_time')}/{dmesg.get('fw_ready_time')}/{dmesg.get('wlan0_time')}"],
                    ["tracefs_hint", tracefs.get("decision_hint")],
                    ["trace_counts", json.dumps(tracefs.get("trace_counts"), sort_keys=True)],
                    ["power_diff_reference", json.dumps({k: power.get(k) for k in ("regulator_snapshot_count", "clock_snapshot_count", "subsys_snapshot_count", "pcie1_gdsc_lines", "target_clock_present_lines", "subsys_esoc0_lines")}, sort_keys=True)],
                    ["matched_power_windows", json.dumps({k: matched.get(k) for k in ("has_pre_esoc_regulator_snapshot", "has_post_wlan0_regulator_snapshot", "has_pre_esoc_clock_snapshot", "has_post_wlan0_clock_snapshot", "has_pre_esoc_subsys_snapshot", "has_post_wlan0_subsys_snapshot")}, sort_keys=True)],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
            "",
            "## Power Diff Snapshot Excerpts",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["regulator_excerpt", json.dumps(power.get("regulator_excerpt"), sort_keys=True)],
                    ["clock_excerpt", json.dumps(power.get("clock_excerpt"), sort_keys=True)],
                    ["subsys_excerpt", json.dumps(power.get("subsys_excerpt"), sort_keys=True)],
                ],
            ),
            "",
            "## Tracefs Excerpts",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["first_times", json.dumps(tracefs.get("first_times"), sort_keys=True)],
                    ["gpio_irq_excerpt", json.dumps(tracefs.get("gpio_irq_excerpt"), sort_keys=True)],
                    ["lower_excerpt", json.dumps(tracefs.get("lower_excerpt"), sort_keys=True)],
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
            f"Bounded Android handoff with temporary Magisk module `{MODULE_NAME}` and native rollback. Android-side mutation is limited to GPIO/IRQ tracefs diagnostic controls, `{REMOTE_EVIDENCE_DIR}`, and `{REMOTE_MODULE_DIR}` cleanup. No clk/regulator tracefs events are enabled. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.",
            "",
            "## Next",
            "",
            "- If this run preserves BDF/FW-ready/wlan0 and captures power snapshots, run the matching V1661 native natural-path half.",
            "- Do not diff against native or enter a write gate until the matching native-side observables exist.",
            "",
        ]
    )


def check_forbidden_output(manifest: dict[str, Any], summary: str) -> list[str]:
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n" + summary
    leaks: list[str] = []
    for key in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, pass_ok = v1521.execute_plan(args, store, execute=execute)
    analysis = context.get("analysis") or {}
    decision = classified_decision(args.command, map_decision(base_decision), pass_ok, analysis)
    manifest = {
        "cycle": "V1660",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "base_decision": base_decision,
        "pass": pass_ok,
        "reason": reason_for(decision, base_decision),
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "tracefs_write_executed": execute,
        "clk_regulator_tracefs_executed": False,
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
        "remote_module_dir": REMOTE_MODULE_DIR,
        "remote_evidence_dir": REMOTE_EVIDENCE_DIR,
    }
    summary = render_summary(manifest)
    leaks = check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1660-forbidden-output-hit"
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
