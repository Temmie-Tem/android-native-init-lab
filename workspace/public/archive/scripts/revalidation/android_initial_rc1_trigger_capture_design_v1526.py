#!/usr/bin/env python3
"""V1526 host-only design for Android initial RC1 trigger capture."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1526-android-initial-rc1-trigger-capture-design")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1526_ANDROID_INITIAL_RC1_TRIGGER_CAPTURE_DESIGN_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1526-android-initial-rc1-trigger-capture-design.txt")

V1525_MANIFEST = Path("tmp/wifi/v1525-mhi-pm-resume-position-classifier/manifest.json")
V1521_HANDOFF_SCRIPT = Path("scripts/revalidation/android_rc1_magisk_postfs_sampler_handoff_v1521.py")
V1521_SAMPLES = Path(
    "tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/"
    "android-postfs-evidence/a90-v1521-rc1-postfs-sampler/samples.log"
)
V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
V1517_NATIVE_DMESG = Path(
    "tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def irq_total_range(samples: str, gpio: int) -> dict[str, Any]:
    totals: list[int] = []
    for line in samples.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(numbers) > 1:
            totals.append(sum(numbers[1:]))
    return {
        "sample_count": len(totals),
        "min": min(totals) if totals else None,
        "max": max(totals) if totals else None,
        "last": totals[-1] if totals else None,
        "all_zero": bool(totals and max(totals) == 0),
    }


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def module_script_preview() -> str:
    return """#!/system/bin/sh
OUT=/data/local/tmp/a90-v1527-rc1-trigger-sampler
mkdir -p "$OUT"
chmod 755 "$OUT"

# Background raw kernel-log capture. Prefer non-destructive /dev/kmsg over
# /proc/kmsg, and fall back to dmesg snapshots if neither stream works.
(
  echo "A90_V1527_KMSG_BEGIN uptime=$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
  if [ -r /dev/kmsg ]; then
    cat /dev/kmsg 2>/dev/null
  elif command -v dmesg >/dev/null 2>&1; then
    dmesg -w 2>/dev/null
  else
    echo "kmsg_stream_unavailable=1"
  fi
) > "$OUT/kmsg-stream.txt" 2>&1 &
KMSG_PID=$!

# High-cadence IRQ/read-only snapshots around first RC1. The important window
# is Android esoc0 -> RC1 assert -> L0, about 8.5s..8.9s in V852.
(
  i=0
  while [ "$i" -lt 320 ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{print $1}')"
    echo "A90_V1527_SAMPLE_BEGIN index=$i uptime=$uptime"
    cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +104|msmgpio-dc +142|msm_pcie_wake|mdm status|mhi|pcie' || true
    if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio || true; fi
    echo "A90_V1527_SAMPLE_END index=$i uptime=$uptime"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep 25000; else sleep 1; fi
  done
) > "$OUT/irq-gpio-samples.log" 2>&1

kill "$KMSG_PID" 2>/dev/null || true
dmesg 2>&1 | grep -Ei 'subsys-restart|__subsystem_get|esoc0|msm_pcie|PCIe|RC1|LTSSM|mhi|wlfw|BDF|wlan0' > "$OUT/dmesg-filtered.txt" 2>&1 || true
touch "$OUT/done"
chmod 644 "$OUT"/* 2>/dev/null || true
exit 0
"""


def classify() -> dict[str, Any]:
    v1525 = read_json(V1525_MANIFEST)
    v852_dmesg = read_text(V852_DMESG)
    v1521_samples = read_text(V1521_SAMPLES)
    v1517_native = read_text(V1517_NATIVE_DMESG)
    v1521_script = read_text(V1521_HANDOFF_SCRIPT)

    android_first_esoc0 = first_ts(v852_dmesg, r"__subsystem_get:\s+esoc0 count:0")
    android_first_assert = first_ts(v852_dmesg, r"msm_pcie_enable: PCIe: Assert the reset of endpoint of RC1")
    android_first_l0 = first_ts(v852_dmesg, r"LTSSM_STATE:\s+LTSSM_L0")
    native_link_failed = first_ts(v1517_native, r"link initialization failed")
    v1525_fixed = (
        v1525.get("pass") is True
        and v1525.get("decision") == "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger"
    )
    v852_has_initial_l0 = android_first_esoc0 is not None and android_first_l0 is not None
    v852_has_no_test_marker = not contains_any(v852_dmesg, (r"PCIe:\s+TEST:", r"msm_pcie_sel_debug_testcase"))
    v1517_has_native_fail = "PCIe: TEST: 11" in v1517_native and native_link_failed is not None
    v1521_irq104 = irq_total_range(v1521_samples, 104)
    v1521_irq142 = irq_total_range(v1521_samples, 142)
    v1521_sampler_reusable = "post_fs_data_script" in v1521_script and "Magisk" in v1521_script

    checks = [
        {
            "name": "v1525-fixed-point",
            "status": "pass" if v1525_fixed else "blocked",
            "detail": "V1525 closes MHI PM-resume as the first-L0 trigger",
        },
        {
            "name": "android-v852-initial-l0-reference",
            "status": "pass" if v852_has_initial_l0 else "blocked",
            "detail": "V852 has Android esoc0 -> RC1 assert -> L0 timing",
        },
        {
            "name": "android-v852-not-test11",
            "status": "pass" if v852_has_no_test_marker else "blocked",
            "detail": "V852 first L0 has no pci-msm TEST/debugfs marker",
        },
        {
            "name": "native-v1517-test11-fail-reference",
            "status": "pass" if v1517_has_native_fail else "blocked",
            "detail": "V1517 has native explicit TEST:11 fail before L0",
        },
        {
            "name": "v1521-postfs-handoff-reusable",
            "status": "pass" if v1521_sampler_reusable else "blocked",
            "detail": "V1521 already provides rollbackable temporary Magisk post-fs-data handoff mechanics",
        },
        {
            "name": "v1521-irq-samples-insufficient",
            "status": "pass" if v1521_irq104["all_zero"] and v1521_irq142["all_zero"] else "blocked",
            "detail": "V1521 reached Android-good lower markers but sampled IRQ totals stayed zero, so V1527 needs raw kmsg plus higher-cadence IRQ samples",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1526-android-initial-rc1-trigger-capture-design-ready"
        if pass_ok
        else "v1526-android-initial-rc1-trigger-capture-design-blocked"
    )
    reason = (
        "existing evidence proves first-L0 trigger attribution is missing, and V1521 handoff can be extended with raw kmsg plus high-cadence IRQ/GPIO capture"
        if pass_ok
        else "required fixed-point evidence is missing or the proposed capture surface is not justified"
    )
    return {
        "cycle": "V1526",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1525": rel(V1525_MANIFEST),
            "v852_dmesg": rel(V852_DMESG),
            "v1521_samples": rel(V1521_SAMPLES),
            "v1517_native_dmesg": rel(V1517_NATIVE_DMESG),
            "v1521_handoff_script": rel(V1521_HANDOFF_SCRIPT),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "evidence_summary": {
            "android_first_esoc0": android_first_esoc0,
            "android_first_assert": android_first_assert,
            "android_first_l0": android_first_l0,
            "android_esoc0_to_assert_ms": round((android_first_assert - android_first_esoc0) * 1000, 3)
            if android_first_esoc0 is not None and android_first_assert is not None
            else None,
            "android_assert_to_l0_ms": round((android_first_l0 - android_first_assert) * 1000, 3)
            if android_first_assert is not None and android_first_l0 is not None
            else None,
            "native_link_failed": native_link_failed,
            "v1521_gpio104_irq": v1521_irq104,
            "v1521_gpio142_irq": v1521_irq142,
        },
        "capture_contract": {
            "next_cycle": "V1527",
            "mechanism": "temporary Magisk post-fs-data module, rollbackable Android handoff copied from V1521",
            "evidence_dir": "/data/local/tmp/a90-v1527-rc1-trigger-sampler",
            "required_files": [
                "kmsg-stream.txt",
                "irq-gpio-samples.log",
                "dmesg-filtered.txt",
                "done",
            ],
            "must_start_before": "Android first RC1 assert (~8.796s in V852); post-fs-data starts early enough in V1521 at uptime 5.72s",
            "sample_window": "320 samples at 25ms target cadence, covering about 8s with usleep available",
            "classification_labels": {
                "raw-kmsg-caller-found": "raw kmsg includes current task/comm for first msm_pcie_enable lines",
                "endpoint-wake-before-l0": "GPIO104 IRQ count increases before first L0",
                "mdm-status-before-l0": "GPIO142 IRQ count increases before or during first L0",
                "kernel-caller-still-opaque-tracefs-needed": "raw kmsg and IRQ samples still do not identify the first-L0 trigger",
            },
            "fallback_if_kmsg_opaque": "V1528 tracefs-only Android read-only/dynamic event design; do not mutate native RC1 again first",
            "module_script_preview": module_script_preview(),
        },
        "safety": {
            "host_only": True,
            "device_commands": False,
            "wifi_hal_start": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes_external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "esoc_notify_boot_done_spoof": False,
            "pci_debugfs_write": False,
            "global_pci_rescan": False,
            "platform_bind_unbind": False,
            "boot_or_partition_write": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["evidence_summary"]
    contract = result["capture_contract"]
    lines = [
        "# Native Init V1526 Android Initial RC1 Trigger Capture Design",
        "",
        "## Summary",
        "",
        "- Cycle: `V1526`",
        "- Type: host-only capture design",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[name, str(path)] for name, path in result["inputs"].items()]),
        "",
        "## Checks",
        "",
        markdown_table(
            ["check", "status", "detail"],
            [[item["name"], item["status"], item["detail"]] for item in result["checks"]],
        ),
        "",
        "## Timing Fixed Point",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["Android first esoc0", summary["android_first_esoc0"]],
                ["Android first RC1 assert", summary["android_first_assert"]],
                ["Android first L0", summary["android_first_l0"]],
                ["Android esoc0 -> assert ms", summary["android_esoc0_to_assert_ms"]],
                ["Android assert -> L0 ms", summary["android_assert_to_l0_ms"]],
                ["Native V1517 link failed", summary["native_link_failed"]],
                ["V1521 GPIO104 IRQ range", summary["v1521_gpio104_irq"]],
                ["V1521 GPIO142 IRQ range", summary["v1521_gpio142_irq"]],
            ],
        ),
        "",
        "## V1527 Capture Contract",
        "",
        markdown_table(
            ["contract", "value"],
            [
                ["mechanism", contract["mechanism"]],
                ["remote evidence dir", contract["evidence_dir"]],
                ["required files", ", ".join(contract["required_files"])],
                ["must start before", contract["must_start_before"]],
                ["sample window", contract["sample_window"]],
                ["fallback", contract["fallback_if_kmsg_opaque"]],
            ],
        ),
        "",
        "## Classification Labels",
        "",
        markdown_table(
            ["label", "meaning"],
            [[name, meaning] for name, meaning in contract["classification_labels"].items()],
        ),
        "",
        "## Module Script Preview",
        "",
        "```sh",
        contract["module_script_preview"].rstrip(),
        "```",
        "",
        "## Interpretation",
        "",
        "V1526 does not start Wi-Fi or mutate native RC1. It defines the next bounded Android-good capture needed to explain the first-L0 trigger. V852 proves Android gets first L0 without a debugfs TEST marker. V1517 proves native explicit TEST:11 fails before L0. V1525 proves MHI PM-resume is post-enumeration and cannot create first L0. Therefore V1527 should capture raw kernel log context and high-cadence GPIO104/GPIO142 IRQ samples from early Android boot using the already proven V1521 temporary Magisk/rollback pattern.",
        "",
        "If raw kmsg includes task context for the first `msm_pcie_enable` lines, V1527 can attribute the Android-only caller. If it does not, the next step should be tracefs/dynamic event design, not another blind native TEST:11 timing retry.",
        "",
        "## Safety Scope",
        "",
        "This cycle is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
        "",
        "## Next",
        "",
        "- V1527 should implement and run the rollbackable Android trigger capture handoff using this contract.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify()
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["capture_contract"]["next_cycle"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
