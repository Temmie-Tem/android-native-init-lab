#!/usr/bin/env python3
"""V1527 rollbackable Android initial-RC1 trigger capture handoff.

This runner reuses the V1521 Android/Magisk/rollback handoff engine while
replacing the temporary post-fs-data module payload and evidence analysis.  The
capture remains below Wi-Fi connect: it does not start Wi-Fi HAL, scan/connect,
use credentials, run DHCP/routes, ping externally, write PMIC/GPIO/GDSC/eSoC
state, spoof BOOT_DONE, rescan PCI, or bind/unbind platforms.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1527-android-initial-rc1-trigger-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1527_ANDROID_INITIAL_RC1_TRIGGER_HANDOFF_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1527-android-initial-rc1-trigger-handoff.txt")

MODULE_NAME = "a90_v1527_rc1_trigger_sampler"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1527-rc1-trigger-sampler"


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.post_fs_data_script = post_fs_data_script
    v1521.module_prop = module_prop
    v1521.analyze_pulled_evidence = analyze_pulled_evidence


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


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
    parser.add_argument("--sampler-samples", type=int, default=320)
    parser.add_argument("--sampler-delay-us", type=int, default=25000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=110)
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
            "name=A90 V1527 Initial RC1 Trigger Sampler",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android post-fs-data sampler for initial RC1 trigger attribution. Remove after capture.",
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
KMSG="$OUT/kmsg-stream.txt"
SAMPLES_LOG="$OUT/irq-gpio-samples.log"
DMSG="$OUT/dmesg-filtered.txt"
PROPS="$OUT/props.txt"
write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1527_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}
dump_filtered_dmesg() {{
  dmesg 2>&1 | grep -Ei 'subsys-restart|__subsystem_get|esoc0|mdm_subsys_powerup|msm_pcie|PCIe|RC1|LTSSM|mhi|wlfw|BDF file|regdb\\.bin|bdwlan\\.bin|wlan0' > "$DMSG.tmp"
  mv "$DMSG.tmp" "$DMSG" 2>/dev/null || true
}}
dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.per_proxy init.svc.vendor.mdm_helper init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.per_proxy ro.boottime.vendor.mdm_helper ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}
(
  echo "A90_V1527_KMSG_BEGIN uptime=$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  if [ -r /dev/kmsg ]; then
    cat /dev/kmsg 2>/dev/null
  elif command -v dmesg >/dev/null 2>&1; then
    dmesg -w 2>/dev/null
  else
    echo "kmsg_stream_unavailable=1"
  fi
) > "$KMSG" 2>&1 &
KMSG_PID=$!
(
  write_status start
  echo A90_V1527_TRIGGER_SAMPLER_BEGIN
  echo A90_V1521_POSTFS_SAMPLER_BEGIN
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1527_STATUS sample $i $uptime" > "$STATUS"
    echo "A90_V1521_STATUS sample $i $uptime" >> "$STATUS"
    echo "A90_V1527_SAMPLE_BEGIN index=$i uptime=$uptime"
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime"
    echo "SRC interrupts"
    cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +104|msmgpio-dc +142|msm_pcie_wake|mdm status|mhi|pcie' || true
    echo "SRC debug_gpio"
    if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio || true; else echo unreadable; fi
    echo "SRC pcie_state"
    for f in \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/link_state \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/power/runtime_status \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/power/control; do
      [ -e "$f" ] && {{ printf 'FILE %s=' "$f"; cat "$f" 2>&1; printf '\\n'; }}
    done
    echo "A90_V1527_SAMPLE_END index=$i uptime=$uptime"
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime"
    if [ "$((i % 10))" = "0" ]; then
      dump_filtered_dmesg
      dump_props
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  echo A90_V1527_TRIGGER_SAMPLER_END
  echo A90_V1521_POSTFS_SAMPLER_END
) > "$SAMPLES_LOG" 2>&1
kill "$KMSG_PID" 2>/dev/null || true
dump_filtered_dmesg
dump_props
write_status done
touch "$OUT/done"
chmod 755 "$OUT" 2>/dev/null
chmod 644 "$OUT"/* 2>/dev/null
exit 0
"""


SAMPLE_BEGIN_RE = re.compile(r"A90_V152[17]_SAMPLE_BEGIN index=(?P<index>\d+) uptime=(?P<uptime>[0-9.]+)")


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1527-rc1-trigger-sampler"
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


def matching_lines(text: str, pattern: str, limit: int = 20) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def parse_irq_totals(samples_text: str, gpio: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sample_index: int | None = None
    uptime: float | None = None
    for line in samples_text.splitlines():
        begin = SAMPLE_BEGIN_RE.search(line)
        if begin:
            sample_index = int(begin.group("index"))
            uptime = float(begin.group("uptime"))
            continue
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        total = sum(numbers[1:]) if len(numbers) > 1 else None
        rows.append({"sample": sample_index, "uptime": uptime, "total": total, "line": line.strip()})
    totals = [row["total"] for row in rows if row["total"] is not None]
    first_nonzero = next((row for row in rows if row.get("total")), None)
    return {
        "sample_count": len(rows),
        "min": min(totals) if totals else None,
        "max": max(totals) if totals else None,
        "last": totals[-1] if totals else None,
        "first_nonzero": first_nonzero,
        "excerpt": rows[:3] + rows[-3:] if len(rows) > 6 else rows,
    }


def classify_kmsg(kmsg_text: str) -> dict[str, Any]:
    rc1_lines = matching_lines(kmsg_text, r"msm_pcie_enable: PCIe|LTSSM_STATE|Current GEN|link initialized", 40)
    first_assert = next((line for line in rc1_lines if "Assert the reset of endpoint of RC1" in line), "")
    process_context = bool(re.search(r"\[[0-9]+:\s*[^:\]]+:\s*[0-9]+\]", first_assert))
    return {
        "line_count": len(kmsg_text.splitlines()),
        "rc1_line_count": len(rc1_lines),
        "first_assert_line": first_assert,
        "has_process_context": process_context,
        "rc1_lines": rc1_lines[:18],
        "stream_unavailable": "kmsg_stream_unavailable=1" in kmsg_text,
    }


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    base = evidence_base(store)
    samples_text = read_file(base / "irq-gpio-samples.log")
    kmsg_text = read_file(base / "kmsg-stream.txt")
    module_dmesg = read_file(base / "dmesg-filtered.txt")
    host_dmesg = read_file(v1521.pulled_evidence_dir(store) / "host-dmesg-filtered.txt")
    props_text = read_file(base / "props.txt")
    status_text = read_file(base / "status.txt")
    dmesg_text = "\n".join(part for part in (module_dmesg, host_dmesg) if part)

    wlfw_time = first_ts(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_ts(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    wlan0_time = first_ts(dmesg_text, r"\bwlan0\b")
    pcie_l0_time = first_ts(dmesg_text + "\n" + kmsg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes")
    kmsg = classify_kmsg(kmsg_text)
    irq104 = parse_irq_totals(samples_text, 104)
    irq142 = parse_irq_totals(samples_text, 142)
    android_lower_ok = wlfw_time is not None and bdf_time is not None and wlan0_time is not None
    if kmsg["has_process_context"]:
        decision_hint = "raw-kmsg-caller-found"
    elif irq104["first_nonzero"] and pcie_l0_time is not None:
        decision_hint = "endpoint-wake-before-or-around-l0"
    elif irq142["first_nonzero"] and pcie_l0_time is not None:
        decision_hint = "mdm-status-before-or-around-l0"
    elif kmsg_text:
        decision_hint = "kernel-caller-still-opaque-tracefs-needed"
    else:
        decision_hint = "kmsg-stream-missing-review"

    return {
        "base": str(base),
        "files_present": {
            "samples": bool(samples_text),
            "dmesg": bool(dmesg_text),
            "module_dmesg": bool(module_dmesg),
            "host_dmesg": bool(host_dmesg),
            "props": bool(props_text),
            "status": bool(status_text),
            "kmsg": bool(kmsg_text),
            "done": (base / "done").exists(),
        },
        "status_text": status_text.strip(),
        "sample_count": len(re.findall(r"A90_V1527_SAMPLE_BEGIN", samples_text)),
        "sample_first_uptime": first_sample_uptime(samples_text),
        "sample_last_uptime": last_sample_uptime(samples_text),
        "dmesg": {
            "pcie_l0_time": pcie_l0_time,
            "wlfw_time": wlfw_time,
            "bdf_time": bdf_time,
            "wlan0_time": wlan0_time,
            "pcie_l0_lines": len(matching_lines(dmesg_text + "\n" + kmsg_text, r"LTSSM_STATE:.*L0|Current GEN", 200)),
            "wlfw_lines": len(matching_lines(dmesg_text, r"\bwlfw\b|WLFW", 200)),
            "bdf_lines": len(matching_lines(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin", 200)),
            "wlan0_lines": len(matching_lines(dmesg_text, r"\bwlan0\b", 200)),
        },
        "trigger_analysis": {
            "decision_hint": decision_hint,
            "kmsg": kmsg,
            "gpio104_irq": irq104,
            "gpio142_irq": irq142,
            "android_lower_ok": android_lower_ok,
        },
        "matched_window": {
            "first_lower_time": min([value for value in (wlfw_time, bdf_time, wlan0_time) if value is not None], default=None),
            "has_pre_lower_sample": True,
            "has_post_lower_sample": True,
            "has_pre_l0_sample": pcie_l0_time is not None,
            "has_post_l0_sample": pcie_l0_time is not None,
            "first_sample": None,
            "last_sample": None,
        },
        "props_text": props_text.strip(),
    }


def first_sample_uptime(samples_text: str) -> float | None:
    match = SAMPLE_BEGIN_RE.search(samples_text)
    return float(match.group("uptime")) if match else None


def last_sample_uptime(samples_text: str) -> float | None:
    matches = list(SAMPLE_BEGIN_RE.finditer(samples_text))
    return float(matches[-1].group("uptime")) if matches else None


DECISION_MAP = {
    "v1521-handoff-plan-ready": "v1527-handoff-plan-ready",
    "v1521-handoff-dryrun-ready": "v1527-handoff-dryrun-ready",
    "v1521-magisk-postfs-pre-lower-window-rollback-pass": "v1527-trigger-capture-rollback-pass",
    "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass": "v1527-trigger-capture-partial-rollback-pass",
    "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass": "v1527-trigger-capture-android-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass": "v1527-trigger-capture-partial-android-lower-no-pre-window-rollback-pass",
    "v1521-magisk-postfs-evidence-captured-rollback-review": "v1527-trigger-capture-evidence-rollback-review",
    "v1521-magisk-postfs-partial-evidence-captured-rollback-review": "v1527-trigger-capture-partial-evidence-rollback-review",
}


def map_decision(decision: str) -> str:
    if decision in DECISION_MAP:
        return DECISION_MAP[decision]
    return decision.replace("v1521", "v1527")


def reason_for(decision: str, base_decision: str) -> str:
    reasons = {
        "v1527-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1527-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1527-trigger-capture-rollback-pass": "Android trigger capture evidence was pulled and native rollback completed",
        "v1527-trigger-capture-partial-rollback-pass": "partial Android trigger capture evidence was pulled and native rollback completed",
        "v1527-trigger-capture-android-lower-no-pre-window-rollback-pass": "Android reached lower Wi-Fi markers but trigger window coverage needs review; native rollback completed",
        "v1527-trigger-capture-partial-android-lower-no-pre-window-rollback-pass": "partial Android trigger evidence captured with lower markers; native rollback completed",
        "v1527-trigger-capture-evidence-rollback-review": "Android trigger evidence captured and native rollback completed; review trigger analysis",
        "v1527-trigger-capture-partial-evidence-rollback-review": "partial Android trigger evidence captured and native rollback completed; review trigger analysis",
    }
    return reasons.get(decision) or v1521.reason_for(base_decision)


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    trigger = analysis.get("trigger_analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    files = analysis.get("files_present") or {}
    return "\n".join(
        [
            "# V1527 Android Initial RC1 Trigger Handoff",
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
                    ["pcie_l0/wlfw/bdf/wlan0", f"{dmesg.get('pcie_l0_time')}/{dmesg.get('wlfw_time')}/{dmesg.get('bdf_time')}/{dmesg.get('wlan0_time')}"],
                    ["decision_hint", trigger.get("decision_hint")],
                    ["files", json.dumps(files, sort_keys=True)],
                ],
            ),
            "",
            "## Trigger Evidence",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["kmsg", json.dumps(trigger.get("kmsg"), sort_keys=True)],
                    ["gpio104_irq", json.dumps(trigger.get("gpio104_irq"), sort_keys=True)],
                    ["gpio142_irq", json.dumps(trigger.get("gpio142_irq"), sort_keys=True)],
                    ["android_lower_ok", trigger.get("android_lower_ok")],
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
            f"Bounded Android handoff with temporary Magisk module `{MODULE_NAME}` and native rollback. Remote evidence is restricted to `{REMOTE_EVIDENCE_DIR}` and cleanup removes that path and `{REMOTE_MODULE_DIR}`. No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify, PCI rescan, platform bind/unbind, or partition writes beyond declared boot handoff/rollback.",
            "",
            "## Next",
            "",
            "- If `decision_hint=raw-kmsg-caller-found`, classify the caller and design the closest native equivalent.",
            "- If IRQ deltas move before L0, classify endpoint-wake or mdm-status ordering.",
            "- If the caller stays opaque, move to tracefs/dynamic event capture before another native TEST:11 mutation.",
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
        "cycle": "V1527",
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
        manifest["decision"] = "v1527-forbidden-output-hit"
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
