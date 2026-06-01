#!/usr/bin/env python3
"""V1554 Android-good pcie1 power/clock/GPIO/IRQ tracefs reference handoff.

This runner reuses the V1521 Android/Magisk/native-rollback handoff engine and
installs a temporary Android post-fs-data module that records a bounded,
filtered tracefs window around the Android-good first RC1/L0/lower-Wi-Fi path.

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1554-android-good-power-trace-reference")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1554_ANDROID_GOOD_POWER_TRACE_REFERENCE_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1554-android-good-power-trace-reference.txt")

MODULE_NAME = "a90_v1554_android_power_trace_ref"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1554-android-power-trace-ref"

TRACE_TARGET_RE = (
    r"pcie_1_gdsc|pcie1|pcie_1|pcie_phy|pipe|refgen|gcc_pcie|"
    r"gpio[^0-9]*(102|104|135|142)|irq=(204|252|290)|irq [^0-9]*(204|252|290)|"
    r"msm_pcie|PCIe|RC1|LTSSM|MHI|mhi|icnss|wlfw|BDF|bdwlan|regdb|FW ready|wlan0|"
    r"subsys|esoc0|mdm|pm-service|pm_proxy|mdm_helper"
)


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.post_fs_data_script = post_fs_data_script
    v1521.module_prop = module_prop
    v1521.analyze_pulled_evidence = analyze_pulled_evidence


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
    parser.add_argument("--sampler-samples", type=int, default=120)
    parser.add_argument("--sampler-delay-us", type=int, default=250000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=180)
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
            "name=A90 V1554 Android-good Power Trace Reference",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary bounded Android tracefs reference for pcie1 power/clock/GPIO/IRQ first-L0 attribution. Remove after capture.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    target_re = TRACE_TARGET_RE.replace("'", "'\"'\"'")
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
SAMPLES={samples}
DELAY_US={delay_us}
TARGET_RE='{target_re}'
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
write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1554_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}
dump_filtered_dmesg() {{
  dmesg 2>&1 | grep -Ei "$TARGET_RE" > "$DMSG.tmp"
  mv "$DMSG.tmp" "$DMSG" 2>/dev/null || true
}}
dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.per_proxy init.svc.vendor.mdm_helper init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.per_proxy ro.boottime.vendor.mdm_helper ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}
T=/sys/kernel/tracing
[ -d "$T" ] || mkdir -p "$T" 2>/dev/null || true
if ! grep -q " $T tracefs " /proc/mounts 2>/dev/null; then
  mount -t tracefs tracefs "$T" 2>>"$EVENTS" || true
fi
EVENT_LIST="regulator/regulator_enable regulator/regulator_enable_complete regulator/regulator_disable regulator/regulator_disable_complete regulator/regulator_set_voltage regulator/regulator_set_voltage_complete clk/clk_prepare clk/clk_prepare_complete clk/clk_enable clk/clk_enable_complete clk/clk_disable clk/clk_disable_complete gpio/gpio_value gpio/gpio_direction irq/irq_handler_entry irq/irq_handler_exit printk/console"
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
  echo "A90_V1554_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "SRC interrupts" >> "$SAMPLES_LOG"
  cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +142|msmgpio-dc +104|mdm status|errfatal|msm_pcie_wake|mhi|pcie' >> "$SAMPLES_LOG" 2>/dev/null || true
  echo "SRC debug_gpio" >> "$SAMPLES_LOG"
  if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio >> "$SAMPLES_LOG" 2>/dev/null || true; else echo unreadable >> "$SAMPLES_LOG"; fi
  if [ "$((i % 8))" = "0" ]; then
    echo "SRC regulator" >> "$SAMPLES_LOG"
    if [ -r /sys/kernel/debug/regulator/regulator_summary ]; then grep -Ei 'pcie_1_gdsc|pcie_0_gdsc|pm8150_l5|pm8150l_l3|pm8150l_s[0-9]+|vdd' /sys/kernel/debug/regulator/regulator_summary >> "$SAMPLES_LOG" 2>/dev/null || true; else echo unreadable >> "$SAMPLES_LOG"; fi
    echo "SRC clk" >> "$SAMPLES_LOG"
    if [ -r /sys/kernel/debug/clk/clk_summary ]; then grep -Ei 'pcie|pipe|refgen|gcc_pcie_1' /sys/kernel/debug/clk/clk_summary >> "$SAMPLES_LOG" 2>/dev/null || true; else echo unreadable >> "$SAMPLES_LOG"; fi
  fi
  if [ "$((i % 24))" = "0" ]; then
    echo "SRC pinmux" >> "$SAMPLES_LOG"
    for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
      [ -r "$f" ] || continue
      grep -Ei 'pin 102 |pin 103 |pin 104 |pin 135 |pin 142 ' "$f" >> "$SAMPLES_LOG" 2>/dev/null || true
    done
  fi
  echo "A90_V1554_SAMPLE_END index=$i uptime=$uptime" >> "$SAMPLES_LOG"
  echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$SAMPLES_LOG"
}}
write_status start
echo "A90_V1554_TRACEFS_SETUP_BEGIN" > "$EVENTS"
if grep -q " $T tracefs " /proc/mounts 2>/dev/null; then TRACEFS_MOUNTED=1; else TRACEFS_MOUNTED=0; fi
echo "tracefs_mounted=$TRACEFS_MOUNTED" >> "$EVENTS"
PREV_ON="$(cat "$T/tracing_on" 2>/dev/null)"
echo "prev_tracing_on=$PREV_ON" >> "$EVENTS"
dump_formats
echo 0 > "$T/tracing_on" 2>>"$EVENTS" || true
echo 16384 > "$T/buffer_size_kb" 2>>"$EVENTS" || true
: > "$T/trace" 2>>"$EVENTS" || true
for e in $EVENT_LIST; do enable_event "$e"; done
echo 1 > "$T/tracing_on" 2>>"$EVENTS" || true
(
  echo A90_V1554_TRACEFS_SAMPLER_BEGIN > "$SAMPLES_LOG"
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1554_STATUS sample $i $uptime" > "$STATUS"
    echo "A90_V1521_STATUS sample $i $uptime" >> "$STATUS"
    dump_sample "$i"
    if [ "$((i % 8))" = "0" ]; then
      dump_filtered_dmesg
      dump_props
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  echo A90_V1554_TRACEFS_SAMPLER_END >> "$SAMPLES_LOG"
)
write_status finalizing
sleep 1
grep -Ei "$TARGET_RE" "$T/trace" 2>/dev/null | head -n 5000 > "$TRACELOG.tmp" || true
mv "$TRACELOG.tmp" "$TRACELOG" 2>/dev/null || true
for e in $EVENT_LIST; do disable_event "$e"; done
if [ -n "$PREV_ON" ]; then echo "$PREV_ON" > "$T/tracing_on" 2>/dev/null || true; else echo 0 > "$T/tracing_on" 2>/dev/null || true; fi
dump_filtered_dmesg
dump_props
(
  printf 'target_lines='; grep -Ec '.' "$TRACELOG" 2>/dev/null || true
  printf 'pcie1_gdsc='; grep -Eic 'pcie_1_gdsc' "$TRACELOG" 2>/dev/null || true
  printf 'refclk_pipe='; grep -Eic 'refgen|pipe|gcc_pcie_1' "$TRACELOG" 2>/dev/null || true
  printf 'gpio102='; grep -Eic 'gpio[^0-9]*102' "$TRACELOG" 2>/dev/null || true
  printf 'gpio104='; grep -Eic 'gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)' "$TRACELOG" 2>/dev/null || true
  printf 'gpio135='; grep -Eic 'gpio[^0-9]*135' "$TRACELOG" 2>/dev/null || true
  printf 'gpio142='; grep -Eic 'gpio[^0-9]*142|irq=290|irq [^0-9]*290' "$TRACELOG" 2>/dev/null || true
  printf 'l0='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic 'LTSSM.*L0|Current GEN[0-9]|PCIe RC1 Current' || true
  printf 'mhi='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic '\\bmhi\\b|MHI' || true
  printf 'wlfw_bdf_wlan='; cat "$TRACELOG" "$DMSG" 2>/dev/null | grep -Eic 'wlfw|WLFW|BDF|bdwlan|regdb|FW ready|wlan0' || true
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
    candidate = root / "a90-v1554-android-power-trace-ref"
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


def matching_lines(text: str, pattern: str, limit: int = 20) -> list[str]:
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


def first_status_uptime(text: str) -> float | None:
    match = re.search(r"A90_V1554_SAMPLE_BEGIN index=\d+ uptime=([0-9.]+)", text)
    return float(match.group(1)) if match else None


def last_status_uptime(text: str) -> float | None:
    matches = list(re.finditer(r"A90_V1554_SAMPLE_BEGIN index=\d+ uptime=([0-9.]+)", text))
    return float(matches[-1].group(1)) if matches else None


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
    dmesg_text = "\n".join(part for part in (module_dmesg, host_dmesg) if part)
    parsed_counts = parse_counts(counts_text)
    wlfw_time = first_ts(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_ts(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    fw_ready_time = first_ts(dmesg_text, r"FW ready|WLAN FW is ready")
    wlan0_time = first_ts(dmesg_text, r"\bwlan0\b")
    l0_time = first_ts(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes")
    esoc0_time = first_ts(dmesg_text, r"__subsystem_get: esoc0")
    android_lower_ok = wlfw_time is not None and bdf_time is not None and wlan0_time is not None
    trace_counts = {
        "target_lines": parsed_counts.get("target_lines", count_lines(trace_text, r".")),
        "pcie1_gdsc": parsed_counts.get("pcie1_gdsc", count_lines(trace_text, r"pcie_1_gdsc")),
        "refclk_pipe": parsed_counts.get("refclk_pipe", count_lines(trace_text, r"refgen|pipe|gcc_pcie_1")),
        "gpio102": parsed_counts.get("gpio102", count_lines(trace_text, r"gpio[^0-9]*102")),
        "gpio104": parsed_counts.get("gpio104", count_lines(trace_text, r"gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)")),
        "gpio135": parsed_counts.get("gpio135", count_lines(trace_text, r"gpio[^0-9]*135")),
        "gpio142": parsed_counts.get("gpio142", count_lines(trace_text, r"gpio[^0-9]*142|irq=290|irq [^0-9]*290")),
        "l0": parsed_counts.get("l0", count_lines(trace_text + "\n" + dmesg_text, r"LTSSM.*L0|Current GEN[0-9]|PCIe RC1 Current")),
        "mhi": parsed_counts.get("mhi", count_lines(trace_text + "\n" + dmesg_text, r"\bmhi\b|MHI")),
        "wlfw_bdf_wlan": parsed_counts.get("wlfw_bdf_wlan", count_lines(trace_text + "\n" + dmesg_text, r"wlfw|WLFW|BDF|bdwlan|regdb|FW ready|wlan0")),
    }
    if android_lower_ok and trace_counts["pcie1_gdsc"] and trace_counts["refclk_pipe"] and trace_counts["gpio102"]:
        decision_hint = "android-good-power-trace-reference"
    elif android_lower_ok and trace_counts["target_lines"]:
        decision_hint = "android-good-target-trace-opaque"
    elif android_lower_ok:
        decision_hint = "android-good-lower-ok-trace-empty"
    elif trace_counts["target_lines"]:
        decision_hint = "target-trace-captured-lower-missing"
    else:
        decision_hint = "trace-empty-review"
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
        },
        "status_text": status_text.strip(),
        "setup_excerpt": setup_log.strip().splitlines()[:80],
        "sample_count": count_lines(samples_text, r"A90_V1554_SAMPLE_BEGIN"),
        "sample_first_uptime": first_status_uptime(samples_text),
        "sample_last_uptime": last_status_uptime(samples_text),
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
            "wlan0_lines": count_lines(dmesg_text, r"\bwlan0\b"),
        },
        "tracefs_analysis": {
            "decision_hint": decision_hint,
            "trace_counts": trace_counts,
            "first_times": {
                "pcie1_gdsc": first_trace_time(trace_text, r"pcie_1_gdsc"),
                "refclk_pipe": first_trace_time(trace_text, r"refgen|pipe|gcc_pcie_1"),
                "gpio102": first_trace_time(trace_text, r"gpio[^0-9]*102"),
                "gpio104": first_trace_time(trace_text, r"gpio[^0-9]*104|irq=(204|252)|irq [^0-9]*(204|252)"),
                "gpio135": first_trace_time(trace_text, r"gpio[^0-9]*135"),
                "gpio142": first_trace_time(trace_text, r"gpio[^0-9]*142|irq=290|irq [^0-9]*290"),
                "l0": first_trace_time(trace_text, r"LTSSM.*L0|Current GEN[0-9]|PCIe RC1 Current"),
                "mhi": first_trace_time(trace_text, r"\bmhi\b|MHI"),
            },
            "pcie_excerpt": matching_lines(trace_text, r"pcie_1_gdsc|refgen|pipe|gcc_pcie_1|msm_pcie|PCIe|RC1|LTSSM", 30),
            "gpio_irq_excerpt": matching_lines(trace_text, r"gpio[^0-9]*(102|104|135|142)|irq=(204|252|290)|irq [^0-9]*(204|252|290)", 30),
            "lower_excerpt": matching_lines(trace_text + "\n" + dmesg_text, r"mhi|wlfw|WLFW|BDF|bdwlan|regdb|FW ready|wlan0", 30),
        },
        "android_lower_ok": android_lower_ok,
        "props_text": props_text.strip(),
    }


DECISION_MAP = {
    "v1521-handoff-plan-ready": "v1554-handoff-plan-ready",
    "v1521-handoff-dryrun-ready": "v1554-handoff-dryrun-ready",
    "v1521-magisk-postfs-pre-lower-window-rollback-pass": "v1554-android-good-reference-rollback-pass",
    "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass": "v1554-android-good-reference-partial-rollback-pass",
    "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass": "v1554-android-good-reference-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass": "v1554-android-good-reference-partial-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-evidence-captured-rollback-review": "v1554-android-good-reference-evidence-rollback-review",
    "v1521-magisk-postfs-partial-evidence-captured-rollback-review": "v1554-android-good-reference-partial-evidence-rollback-review",
}


def map_decision(decision: str) -> str:
    return DECISION_MAP.get(decision, decision.replace("v1521", "v1554"))


def classified_decision(command: str, mapped_decision: str, pass_ok: bool, analysis: dict[str, Any]) -> str:
    if command != "run" or not pass_ok:
        return mapped_decision
    tracefs = analysis.get("tracefs_analysis") or {}
    hint = tracefs.get("decision_hint")
    if hint == "android-good-power-trace-reference":
        return "v1554-android-good-power-trace-reference-pass"
    if hint == "android-good-target-trace-opaque":
        return "v1554-android-good-target-trace-opaque-pass"
    if hint == "android-good-lower-ok-trace-empty":
        return "v1554-android-good-lower-ok-trace-empty-review"
    if hint == "target-trace-captured-lower-missing":
        return "v1554-target-trace-captured-lower-missing-review"
    return mapped_decision


def reason_for(decision: str, base_decision: str) -> str:
    reasons = {
        "v1554-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1554-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1554-android-good-power-trace-reference-pass": "Android-good lower Wi-Fi path and bounded pcie1 power/refclk/PERST trace reference were captured; native rollback completed",
        "v1554-android-good-target-trace-opaque-pass": "Android-good lower Wi-Fi path and target tracefs evidence were captured, but key pcie1 power signals need event-set refinement; native rollback completed",
        "v1554-android-good-lower-ok-trace-empty-review": "Android-good lower Wi-Fi path was observed, but bounded tracefs target output was empty; native rollback completed",
        "v1554-target-trace-captured-lower-missing-review": "target tracefs evidence was captured, but Android lower Wi-Fi markers were missing; native rollback completed",
        "v1554-android-good-reference-rollback-pass": "Android-good reference evidence was pulled and native rollback completed",
        "v1554-android-good-reference-partial-rollback-pass": "partial Android-good reference evidence was pulled and native rollback completed",
    }
    return reasons.get(decision) or v1521.reason_for(base_decision)


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    tracefs = analysis.get("tracefs_analysis") or {}
    return "\n".join(
        [
            "# V1554 Android-good Power Trace Reference Handoff",
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
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
            "",
            "## Tracefs Excerpts",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["first_times", json.dumps(tracefs.get("first_times"), sort_keys=True)],
                    ["pcie_excerpt", json.dumps(tracefs.get("pcie_excerpt"), sort_keys=True)],
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
            f"Bounded Android handoff with temporary Magisk module `{MODULE_NAME}` and native rollback. Android-side mutation is limited to tracefs diagnostic controls, `{REMOTE_EVIDENCE_DIR}`, and `{REMOTE_MODULE_DIR}` cleanup. The module stores filtered target trace output only; it does not persist a full raw trace. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.",
            "",
            "## Next",
            "",
            "- If this run captured Android-good lower Wi-Fi and key target traces, compare it against V1552 native endpoint-silent evidence.",
            "- If lower Wi-Fi markers are missing under this tracefs event set, reduce the Android-good reference to console/dmesg plus minimal GPIO/IRQ or extend the hold before treating it as a good reference.",
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
        "cycle": "V1554",
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
        manifest["decision"] = "v1554-forbidden-output-hit"
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
