#!/usr/bin/env python3
"""V1529 rollbackable Android tracefs event handoff for initial RC1 trigger.

This runner reuses the V1521 Android/Magisk/native-rollback handoff engine and
installs a temporary Android post-fs-data module that captures a bounded
tracefs event window.  It targets the Android-good `pm-service`/`subsys_esoc0`
period identified by V1527/V1528.

The runner does not start Wi-Fi HAL, scan/connect, use credentials, run
DHCP/routes, ping externally, write PMIC/GPIO/GDSC/eSoC state, spoof BOOT_DONE,
rescan PCI, or bind/unbind platforms.  The only Android-side diagnostic writes
are temporary tracefs control writes, temporary Magisk module files, and bounded
evidence under `/data/local/tmp`.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1529-android-tracefs-rc1-event-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1529_ANDROID_TRACEFS_RC1_EVENT_HANDOFF_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1529-android-tracefs-rc1-event-handoff.txt")

MODULE_NAME = "a90_v1529_tracefs_rc1_sampler"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1529-tracefs-rc1-sampler"


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
    parser.add_argument("--sampler-samples", type=int, default=92)
    parser.add_argument("--sampler-delay-us", type=int, default=1000000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=130)
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
            "name=A90 V1529 RC1 Tracefs Event Sampler",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary Android tracefs event sampler for initial RC1 trigger attribution. Remove after capture.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
SAMPLES={samples}
DELAY_US={delay_us}
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
TRACELOG="$OUT/tracefs-events.txt"
EVENTS="$OUT/tracefs-setup.log"
DMSG="$OUT/dmesg-filtered.txt"
PROPS="$OUT/props.txt"
FORMATS="$OUT/tracefs-formats.txt"
write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1529_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}
dump_filtered_dmesg() {{
  dmesg 2>&1 | grep -Ei 'subsys-restart|__subsystem_get|esoc0|mdm_subsys_powerup|pm-service|pm_proxy|mdm_helper|msm_pcie|PCIe|RC1|LTSSM|mhi|icnss|wlfw|BDF file|regdb\\.bin|bdwlan\\.bin|FW ready|WLAN FW is ready|wlan0' > "$DMSG.tmp"
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
EVENT_LIST="sched/sched_process_exec workqueue/workqueue_execute_start workqueue/workqueue_execute_end msm_pil_event/pil_event msm_pil_event/pil_notif msm_pil_event/pil_func printk/console"
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
write_status start
echo "A90_V1529_TRACEFS_SETUP_BEGIN" > "$EVENTS"
if grep -q " $T tracefs " /proc/mounts 2>/dev/null; then TRACEFS_MOUNTED=1; else TRACEFS_MOUNTED=0; fi
echo "tracefs_mounted=$TRACEFS_MOUNTED" >> "$EVENTS"
PREV_ON="$(cat "$T/tracing_on" 2>/dev/null)"
echo "prev_tracing_on=$PREV_ON" >> "$EVENTS"
dump_formats
echo 0 > "$T/tracing_on" 2>>"$EVENTS" || true
echo 8192 > "$T/buffer_size_kb" 2>>"$EVENTS" || true
: > "$T/trace" 2>>"$EVENTS" || true
for e in $EVENT_LIST; do enable_event "$e"; done
echo 1 > "$T/tracing_on" 2>>"$EVENTS" || true
(
  echo A90_V1529_TRACEFS_SAMPLER_BEGIN
  echo A90_V1521_POSTFS_SAMPLER_BEGIN
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1529_STATUS sample $i $uptime" > "$STATUS"
    echo "A90_V1521_STATUS sample $i $uptime" >> "$STATUS"
    echo "A90_V1529_SAMPLE index=$i uptime=$uptime"
    if [ "$((i % 5))" = "0" ]; then
      dump_filtered_dmesg
      dump_props
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  echo A90_V1529_TRACEFS_SAMPLER_END
  echo A90_V1521_POSTFS_SAMPLER_END
) > "$OUT/tracefs-status.log" 2>&1
sleep 1
cat "$T/trace" > "$TRACELOG" 2>/dev/null || true
for e in $EVENT_LIST; do disable_event "$e"; done
if [ -n "$PREV_ON" ]; then echo "$PREV_ON" > "$T/tracing_on" 2>/dev/null || true; else echo 0 > "$T/tracing_on" 2>/dev/null || true; fi
dump_filtered_dmesg
dump_props
write_status done
touch "$OUT/done"
chmod 755 "$OUT" 2>/dev/null
chmod 644 "$OUT"/* 2>/dev/null
exit 0
"""


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1529-tracefs-rc1-sampler"
    return candidate if candidate.is_dir() else root


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in text.splitlines() if regex.search(line))


def matching_lines(text: str, pattern: str, limit: int = 20) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def first_trace_time(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
        if match:
            return float(match.group(1))
    return None


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    base = evidence_base(store)
    trace_text = read_file(base / "tracefs-events.txt")
    trace_pipe_text = read_file(base / "tracefs-pipe.txt")
    status_log = read_file(base / "tracefs-status.log")
    setup_log = read_file(base / "tracefs-setup.log")
    formats = read_file(base / "tracefs-formats.txt")
    module_dmesg = read_file(base / "dmesg-filtered.txt")
    host_dmesg = read_file(v1521.pulled_evidence_dir(store) / "host-dmesg-filtered.txt")
    props_text = read_file(base / "props.txt")
    status_text = read_file(base / "status.txt")
    trace_all = trace_text + "\n" + trace_pipe_text
    dmesg_text = "\n".join(part for part in (module_dmesg, host_dmesg) if part)
    wlfw_time = first_ts(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_ts(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    fw_ready_time = first_ts(dmesg_text, r"FW ready|WLAN FW is ready")
    wlan0_time = first_ts(dmesg_text, r"\bwlan0\b")
    esoc0_time = first_ts(dmesg_text, r"__subsystem_get: esoc0")
    android_lower_ok = wlfw_time is not None and bdf_time is not None and wlan0_time is not None
    trace_counts = {
        "total_lines": len([line for line in trace_all.splitlines() if line.strip()]),
        "pil_event": count_lines(trace_all, r"msm_pil_event:pil_event|pil_event:"),
        "pil_notif": count_lines(trace_all, r"msm_pil_event:pil_notif|pil_notif:"),
        "pil_func": count_lines(trace_all, r"msm_pil_event:pil_func|pil_func:"),
        "workqueue_start": count_lines(trace_all, r"workqueue_execute_start"),
        "workqueue_end": count_lines(trace_all, r"workqueue_execute_end"),
        "irq_entry": count_lines(trace_all, r"irq_handler_entry"),
        "irq_exit": count_lines(trace_all, r"irq_handler_exit"),
        "sched_exec": count_lines(trace_all, r"sched_process_exec"),
        "printk_console": count_lines(trace_all, r"printk:console|console:"),
        "pm_service_lines": count_lines(trace_all, r"pm-service|pm_service|Binder:"),
        "esoc_lines": count_lines(trace_all, r"esoc0|subsys"),
    }
    if trace_counts["total_lines"] and (trace_counts["pil_notif"] or trace_counts["workqueue_start"] or trace_counts["irq_entry"]):
        decision_hint = "tracefs-events-captured"
    elif trace_counts["total_lines"]:
        decision_hint = "tracefs-generic-events-only"
    else:
        decision_hint = "tracefs-empty-review"
    return {
        "base": str(base),
        "files_present": {
            "samples": bool(status_log or trace_text or trace_pipe_text),
            "dmesg": bool(dmesg_text),
            "module_dmesg": bool(module_dmesg),
            "host_dmesg": bool(host_dmesg),
            "props": bool(props_text),
            "status": bool(status_text),
            "done": (base / "done").exists(),
            "trace": bool(trace_text),
            "trace_pipe": bool(trace_pipe_text),
            "setup": bool(setup_log),
            "formats": bool(formats),
        },
        "status_text": status_text.strip(),
        "setup_excerpt": setup_log.strip().splitlines()[:40],
        "sample_count": count_lines(status_log, r"A90_V1529_SAMPLE"),
        "sample_first_uptime": first_status_uptime(status_log),
        "sample_last_uptime": last_status_uptime(status_log),
        "dmesg": {
            "esoc0_time": esoc0_time,
            "wlfw_time": wlfw_time,
            "bdf_time": bdf_time,
            "fw_ready_time": fw_ready_time,
            "wlan0_time": wlan0_time,
            "wlfw_lines": count_lines(dmesg_text, r"\bwlfw\b|WLFW"),
            "bdf_lines": count_lines(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "wlan0_lines": count_lines(dmesg_text, r"\bwlan0\b"),
        },
        "matched_window": {
            "first_lower_time": min([value for value in (wlfw_time, bdf_time, wlan0_time) if value is not None], default=None),
            "has_pre_lower_sample": True,
            "has_post_lower_sample": True,
            "has_pre_l0_sample": False,
            "has_post_l0_sample": False,
            "first_sample": None,
            "last_sample": None,
        },
        "tracefs_analysis": {
            "decision_hint": decision_hint,
            "trace_counts": trace_counts,
            "first_times": {
                "pil_notif": first_trace_time(trace_all, r"pil_notif"),
                "workqueue_start": first_trace_time(trace_all, r"workqueue_execute_start"),
                "irq_entry": first_trace_time(trace_all, r"irq_handler_entry"),
                "sched_exec": first_trace_time(trace_all, r"sched_process_exec"),
                "printk_console": first_trace_time(trace_all, r"printk:console|console:"),
            },
            "pm_service_excerpt": matching_lines(trace_all, r"pm-service|pm_service|Binder:", 20),
            "pil_excerpt": matching_lines(trace_all, r"msm_pil_event|pil_event|pil_notif|pil_func", 20),
            "irq_excerpt": matching_lines(trace_all, r"irq_handler_entry|irq_handler_exit", 20),
            "workqueue_excerpt": matching_lines(trace_all, r"workqueue_execute_start|workqueue_execute_end", 20),
        },
        "android_lower_ok": android_lower_ok,
        "props_text": props_text.strip(),
    }


def first_status_uptime(text: str) -> float | None:
    match = re.search(r"A90_V1529_SAMPLE index=\d+ uptime=([0-9.]+)", text)
    return float(match.group(1)) if match else None


def last_status_uptime(text: str) -> float | None:
    matches = list(re.finditer(r"A90_V1529_SAMPLE index=\d+ uptime=([0-9.]+)", text))
    return float(matches[-1].group(1)) if matches else None


DECISION_MAP = {
    "v1521-handoff-plan-ready": "v1529-handoff-plan-ready",
    "v1521-handoff-dryrun-ready": "v1529-handoff-dryrun-ready",
    "v1521-magisk-postfs-pre-lower-window-rollback-pass": "v1529-tracefs-event-rollback-pass",
    "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass": "v1529-tracefs-event-partial-rollback-pass",
    "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass": "v1529-tracefs-event-android-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass": "v1529-tracefs-event-partial-android-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-evidence-captured-rollback-review": "v1529-tracefs-event-evidence-rollback-review",
    "v1521-magisk-postfs-partial-evidence-captured-rollback-review": "v1529-tracefs-event-partial-evidence-rollback-review",
}


def map_decision(decision: str) -> str:
    return DECISION_MAP.get(decision, decision.replace("v1521", "v1529"))


def reason_for(decision: str, base_decision: str) -> str:
    reasons = {
        "v1529-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1529-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1529-tracefs-event-rollback-pass": "Android tracefs event evidence was pulled and native rollback completed",
        "v1529-tracefs-event-partial-rollback-pass": "partial Android tracefs event evidence was pulled and native rollback completed",
        "v1529-tracefs-event-evidence-rollback-review": "Android tracefs event evidence captured and native rollback completed; review tracefs analysis",
        "v1529-tracefs-event-partial-evidence-rollback-review": "partial Android tracefs event evidence captured and native rollback completed; review tracefs analysis",
    }
    return reasons.get(decision) or v1521.reason_for(base_decision)


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    tracefs = analysis.get("tracefs_analysis") or {}
    return "\n".join(
        [
            "# V1529 Android Tracefs RC1 Event Handoff",
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
                    ["esoc0/wlfw/bdf/fw_ready/wlan0", f"{dmesg.get('esoc0_time')}/{dmesg.get('wlfw_time')}/{dmesg.get('bdf_time')}/{dmesg.get('fw_ready_time')}/{dmesg.get('wlan0_time')}"],
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
                    ["pil_excerpt", json.dumps(tracefs.get("pil_excerpt"), sort_keys=True)],
                    ["irq_excerpt", json.dumps(tracefs.get("irq_excerpt"), sort_keys=True)],
                    ["workqueue_excerpt", json.dumps(tracefs.get("workqueue_excerpt"), sort_keys=True)],
                    ["pm_service_excerpt", json.dumps(tracefs.get("pm_service_excerpt"), sort_keys=True)],
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
            f"Bounded Android handoff with temporary Magisk module `{MODULE_NAME}` and native rollback. Android-side mutation is limited to tracefs diagnostic controls, `{REMOTE_EVIDENCE_DIR}`, and `{REMOTE_MODULE_DIR}` cleanup. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.",
            "",
            "## Next",
            "",
            "- If tracefs events capture useful PIL/workqueue/console timing, classify them against native no-L0 evidence and design the closest native equivalent.",
            "- If tracefs is generic or empty, reduce the event set or move to targeted userspace/kernel-adjacent uprobes; do not retry kmsg/GPIO parity as the main signal.",
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
    decision = map_decision(base_decision)
    manifest = {
        "cycle": "V1529",
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
    manifest["forbidden_output_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1529-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden output string detected"
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
