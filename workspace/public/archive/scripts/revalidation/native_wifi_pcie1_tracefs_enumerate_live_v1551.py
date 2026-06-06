#!/usr/bin/env python3
"""V1551 bounded pcie1 tracefs observer around sysfs-client enumerate.

V1550 classified `regulator_summary` as insufficient for deciding whether
`pcie_1_gdsc` was actually enabled in the short RC1 no-L0 window. V1551 enables
only targeted tracefs static events, triggers the already-proven bounded
pcie1 sysfs-client enumerate path once, captures filtered regulator/clock/GPIO
event lines plus dmesg, then disables tracefs events and verifies cleanup.

This live gate does not start Wi-Fi HAL, scan/connect, use credentials, run
DHCP/routes, external ping, write PMIC/GPIO/GDSC directly, issue eSoC notify,
spoof BOOT_DONE, globally rescan PCI, bind/unbind platform devices, flash, or
write partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1551-pcie1-tracefs-enumerate-live")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1551_PCIE1_TRACEFS_ENUMERATE_LIVE_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1551-pcie1-tracefs-enumerate-live.txt")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEBUGFS_ROOT = "/sys/kernel/debug"
TRACEFS_ROOTS = ("/sys/kernel/tracing", "/sys/kernel/debug/tracing")
PCIE1_ENUMERATE = "/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate"

TRACE_EVENTS = (
    ("regulator", "regulator_enable"),
    ("regulator", "regulator_enable_complete"),
    ("regulator", "regulator_disable"),
    ("regulator", "regulator_disable_complete"),
    ("regulator", "regulator_set_voltage"),
    ("regulator", "regulator_set_voltage_complete"),
    ("clk", "clk_prepare"),
    ("clk", "clk_prepare_complete"),
    ("clk", "clk_enable"),
    ("clk", "clk_enable_complete"),
    ("gpio", "gpio_direction"),
    ("gpio", "gpio_value"),
)

TARGET_KEYWORDS = (
    "pcie_1_gdsc",
    "pm8150l_l3",
    "pm8150_l5",
    "VDD_CX",
    "VDD_CX_LEVEL",
    "GCC_PCIE_1",
    "gcc_pcie_1",
    "pcie_1_",
    "PCIE1_PHY_REFGEN",
    "pcie1_phy_refgen",
    "pcie_phy_refgen",
    "pcie_phy_aux",
    "gpio_value: 102",
    "gpio_direction: 102",
    "gpio_value: 104",
    "gpio_direction: 104",
    "gpio_value: 135",
    "gpio_direction: 135",
    "gpio_value: 142",
    "gpio_direction: 142",
)

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("command", choices=("plan", "run", "reclassify"), nargs="?", default="run")
    return parser.parse_args()


def capture_native(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    command: list[str],
    *,
    timeout: float | None = None,
    allow_error: bool = False,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if capture.text else text
    hide_item: dict[str, Any] | None = None
    if capture.status == "busy" or "[busy]" in stripped:
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(timeout or args.timeout, 8.0))
        hide_text = hide_capture.text if hide_capture.text else hide_capture.error + "\n"
        hide_stripped = strip_cmdv1_text(hide_text) if hide_capture.text else hide_text
        hide_item = asdict(hide_capture)
        hide_item["file"] = f"native/{safe_name(name)}-hide-on-busy.txt"
        hide_item["ok"] = bool(hide_capture.ok)
        if len(hide_item["text"]) > 2048:
            hide_item["text_sha256_like"] = "omitted-large-text"
            hide_item["text"] = hide_item["text"][:2048] + "\n[truncated in manifest]\n"
        store.write_text(hide_item["file"], hide_stripped.rstrip() + "\n")
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        text = capture.text if capture.text else capture.error + "\n"
        stripped = strip_cmdv1_text(text) if capture.text else text
    item = asdict(capture)
    item["file"] = f"native/{safe_name(name)}.txt"
    item["ok"] = bool(capture.ok or allow_error)
    item["raw_ok"] = bool(capture.ok)
    if len(item["text"]) > 4096:
        item["text_sha256_like"] = "omitted-large-text"
        item["text"] = item["text"][:4096] + "\n[truncated in manifest]\n"
    if hide_item is not None:
        item["hide_on_busy"] = hide_item
    store.write_text(item["file"], stripped.rstrip() + "\n")
    return item


def run_text(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    *,
    timeout: float = 15.0,
    allow_error: bool = False,
) -> None:
    steps.append(capture_native(args, store, name, ["run", *command], timeout=timeout, allow_error=allow_error))


def run_shell(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    script: str,
    *,
    timeout: float = 15.0,
    allow_error: bool = False,
) -> None:
    run_text(args, store, steps, name, [args.busybox, "sh", "-c", script], timeout=timeout, allow_error=allow_error)


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            path = store.run_dir / str(step.get("file") or "")
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    return any(step.get("name") == name and step.get("ok") for step in steps)


def mount_present(text: str, mountpoint: str, fstype: str) -> bool:
    return re.search(rf"\s{re.escape(mountpoint)}\s+{re.escape(fstype)}\s", text) is not None


def event_label(group: str, event: str) -> str:
    return f"{group}.{event}"


def trace_event_setup_lines(enable: bool, events: tuple[tuple[str, str], ...] = TRACE_EVENTS) -> list[str]:
    value = "1" if enable else "0"
    action = "enable" if enable else "disable"
    lines: list[str] = []
    for group, event in events:
        label = event_label(group, event)
        lines.extend(
            [
                f"if [ -e \"$TRACE/events/{group}/{event}/enable\" ]; then",
                f"  if echo {value} > \"$TRACE/events/{group}/{event}/enable\" 2>/dev/null; then",
                f"    echo event.{label}.{action}=ok",
                "  else",
                f"    echo event.{label}.{action}=failed",
                "  fi",
                "else",
                f"  echo event.{label}.{action}=missing",
                "fi",
            ]
        )
    return lines


def trace_root_assign() -> str:
    return (
        "TRACE=; "
        "for candidate in /sys/kernel/tracing /sys/kernel/debug/tracing; do "
        "if [ -e \"$candidate/tracing_on\" ] && [ -e \"$candidate/trace\" ]; then TRACE=\"$candidate\"; break; fi; "
        "done; "
        "echo trace_root=\"$TRACE\"; "
        "if [ -z \"$TRACE\" ]; then echo result=tracefs-root-missing; exit 7; fi"
    )


def trace_setup_script() -> str:
    return f"""
set +e
BB={DEFAULT_BUSYBOX}
mkdir -p /sys/kernel/tracing {DEBUGFS_ROOT} 2>/dev/null || true
$BB grep -q ' /sys/kernel/debug debugfs ' /proc/mounts || $BB mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true
$BB grep -q ' /sys/kernel/tracing tracefs ' /proc/mounts || $BB mount -t tracefs tracefs /sys/kernel/tracing 2>/dev/null || true
{trace_root_assign()}
echo enumerate_path={PCIE1_ENUMERATE}
if [ -w {PCIE1_ENUMERATE} ]; then echo enumerate_writable=1; else echo enumerate_writable=0; ls -l {PCIE1_ENUMERATE} 2>/dev/null || true; fi
""".strip()


def trace_clear_script() -> str:
    return f"""
set +e
{trace_root_assign()}
echo 0 > "$TRACE/tracing_on" 2>/dev/null
trace_off_rc=$?
echo > "$TRACE/trace" 2>/dev/null
trace_clear_rc=$?
echo trace_off_rc="$trace_off_rc"
echo trace_clear_rc="$trace_clear_rc"
""".strip()


def trace_control_script(label: str, events: tuple[tuple[str, str], ...], enable: bool) -> str:
    return "\n".join(["set +e", trace_root_assign(), f"echo trace_control={label}", *trace_event_setup_lines(enable, events)])


def trace_on_off_script(enable: bool) -> str:
    value = "1" if enable else "0"
    label = "on" if enable else "off"
    return f"""
set +e
{trace_root_assign()}
echo {value} > "$TRACE/tracing_on" 2>/dev/null
echo tracing_{label}_rc=$?
""".strip()


def trace_trigger_script(args: argparse.Namespace) -> str:
    return f"""
set +e
BB={args.busybox}
echo trigger_begin_ms="$($BB date +%s%3N 2>/dev/null || echo 0)"
printf '1\\n' > {PCIE1_ENUMERATE} 2>/dev/null
trigger_rc=$?
echo trigger_rc="$trigger_rc"
echo trigger_end_ms="$($BB date +%s%3N 2>/dev/null || echo 0)"
""".strip()


def trace_count_script() -> str:
    count_lines = []
    for group, event in TRACE_EVENTS:
        count_lines.append(
            f"count=$($BB grep -c '{event}' \"$TRACE/trace\" 2>/dev/null); "
            "if [ -z \"$count\" ]; then count=0; fi; "
            f"echo event_count.{group}.{event}=\"$count\""
        )
    return "\n".join(["set +e", f"BB={DEFAULT_BUSYBOX}", trace_root_assign(), "echo event_counts_begin", *count_lines, "echo event_counts_end"])


def trace_dump_script() -> str:
    keyword_pattern = "|".join(re.escape(item) for item in TARGET_KEYWORDS)
    return f"""
set +e
BB={DEFAULT_BUSYBOX}
{trace_root_assign()}
echo target_trace_lines_begin
$BB grep -Ei '{keyword_pattern}' "$TRACE/trace" 2>/dev/null | $BB head -n 1600 || true
echo target_trace_lines_end
echo result=tracefs-enumerate-pass
""".strip()


def snapshot_script(args: argparse.Namespace, prefix: str) -> str:
    return f"""
set +e
BB={args.busybox}
TOY={args.toybox}
echo snapshot={prefix}
echo mounts_begin
$TOY cat /proc/mounts 2>/dev/null || true
echo mounts_end
echo regulator_begin
$BB grep -iE 'pcie_1_gdsc|pcie_0_gdsc|pm8150l_l3|pm8150_l5|VDD_CX' /sys/kernel/debug/regulator/regulator_summary /sys/kernel/debug/regulator_summary 2>/dev/null || true
echo regulator_end
echo clk_begin
$BB grep -iE 'pcie_1|PCIE_1|pcie1|PCIE1|phy_refgen|clkref' /sys/kernel/debug/clk/clk_summary 2>/dev/null | $BB head -n 160 || true
echo clk_end
echo gpio_begin
$BB grep -iE 'gpio-102|gpio102|GPIO102|gpio-104|gpio104|GPIO104|gpio-135|gpio135|GPIO135|gpio-142|gpio142|GPIO142|1270|pm8150' /sys/kernel/debug/gpio 2>/dev/null || true
echo gpio_end
echo interrupts_begin
$TOY cat /proc/interrupts 2>/dev/null | $BB grep -iE 'gpio|pcie|mhi|msi|142|102|104|135' || true
echo interrupts_end
echo pci_begin
$TOY find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true
echo pci_end
echo mhi_begin
$TOY ls -l /sys/bus/mhi/devices /dev/mhi* /dev/*mhi* 2>/dev/null || true
echo mhi_end
""".strip()


def dmesg_script(args: argparse.Namespace) -> str:
    return (
        f"{args.toybox} dmesg | {args.busybox} grep -iE "
        "'pci-msm|msm_pcie|pcie|LTSSM|PERST|WAKE|enumerate|mhi|wlfw|bdf|fw ready|wlan0|gpio' "
        f"| {args.busybox} tail -260 || true"
    )


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1551",
        "type": "bounded live pcie1 tracefs enumerate observer plan",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": "v1551-pcie1-tracefs-enumerate-plan-ready",
        "pass": True,
        "live_action": "enable selected tracefs events, write one to pcie1 debug enumerate path, disable events, collect evidence",
        "trace_events": [event_label(group, event) for group, event in TRACE_EVENTS],
        "target_keywords": list(TARGET_KEYWORDS),
        "guardrails": [
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no global PCI rescan or platform bind/unbind",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def collect_run(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "status", ["status"], timeout=15.0),
    ]
    run_text(args, store, steps, "mounts-before", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    mounts_before = step_text(store, steps, "mounts-before")
    debugfs_before = mount_present(mounts_before, DEBUGFS_ROOT, "debugfs")
    tracefs_before = any(mount_present(mounts_before, root, "tracefs") for root in TRACEFS_ROOTS)
    store.write_json(
        "pre_mount_state.json",
        {
            "debugfs_mounted_before": debugfs_before,
            "tracefs_mounted_before": tracefs_before,
        },
    )
    run_shell(args, store, steps, "snapshot-before", snapshot_script(args, "before"), timeout=25.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-setup", trace_setup_script(), timeout=15.0)
    for group, event in TRACE_EVENTS:
        run_shell(
            args,
            store,
            steps,
            f"tracefs-disable-initial-{group}-{event}",
            trace_control_script(f"disable-initial-{group}-{event}", ((group, event),), False),
            timeout=10.0,
            allow_error=True,
        )
    run_shell(args, store, steps, "tracefs-clear", trace_clear_script(), timeout=15.0)
    for group, event in TRACE_EVENTS:
        run_shell(
            args,
            store,
            steps,
            f"tracefs-enable-{group}-{event}",
            trace_control_script(f"enable-{group}-{event}", ((group, event),), True),
            timeout=10.0,
        )
    run_shell(args, store, steps, "tracefs-on", trace_on_off_script(True), timeout=10.0)
    run_shell(args, store, steps, "trigger-enumerate", trace_trigger_script(args), timeout=20.0)
    run_shell(args, store, steps, "tracefs-settle", f"{args.busybox} sleep 1; true", timeout=5.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-off", trace_on_off_script(False), timeout=10.0, allow_error=True)
    for group, event in TRACE_EVENTS:
        run_shell(
            args,
            store,
            steps,
            f"tracefs-disable-{group}-{event}",
            trace_control_script(f"disable-{group}-{event}", ((group, event),), False),
            timeout=10.0,
            allow_error=True,
        )
    run_shell(args, store, steps, "tracefs-event-counts", trace_count_script(), timeout=15.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-dump-targets", trace_dump_script(), timeout=20.0, allow_error=True)
    run_shell(args, store, steps, "snapshot-after", snapshot_script(args, "after"), timeout=25.0, allow_error=True)
    run_shell(args, store, steps, "dmesg-pcie-tail", dmesg_script(args), timeout=20.0, allow_error=True)
    if not tracefs_before:
        run_shell(args, store, steps, "tracefs-umount", f"{args.busybox} umount /sys/kernel/tracing 2>/dev/null || true", timeout=10.0, allow_error=True)
    if not debugfs_before:
        run_shell(args, store, steps, "debugfs-umount", f"{args.busybox} umount /sys/kernel/debug 2>/dev/null || true", timeout=10.0, allow_error=True)
    run_text(args, store, steps, "mounts-after", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    steps.extend(
        [
            capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
            capture_native(args, store, "post-status", ["status"], timeout=15.0),
        ]
    )
    return steps


def extract_block(text: str, begin: str, end: str) -> list[str]:
    lines: list[str] = []
    in_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() == begin:
            in_block = True
            continue
        if line.strip() == end:
            in_block = False
            continue
        if in_block:
            lines.append(line)
    return lines


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key.strip()):
            values[key.strip()] = value.strip()
    return values


def count_lines(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in lines if regex.search(line))


def combined_trace_text(store: EvidenceStore, steps: list[dict[str, Any]]) -> str:
    names = [
        str(step.get("name") or "")
        for step in steps
        if str(step.get("name") or "").startswith("tracefs-") or str(step.get("name") or "") == "trigger-enumerate"
    ]
    return "\n".join(step_text(store, steps, name) for name in names)


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    trace_text = combined_trace_text(store, steps)
    dmesg = step_text(store, steps, "dmesg-pcie-tail")
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_after = step_text(store, steps, "mounts-after")
    trace_lines = extract_block(trace_text, "target_trace_lines_begin", "target_trace_lines_end")
    kv = parse_key_values(trace_text)
    event_status = {
        key: value
        for key, value in kv.items()
        if key.startswith("event.") and (key.endswith(".enable") or key.endswith(".disable"))
    }
    event_counts = {key: int(value) for key, value in kv.items() if key.startswith("event_count.") and value.isdigit()}
    if not event_counts:
        event_counts = {
            f"target_line_count.{group}.{event}": count_lines(trace_lines, rf"\b{re.escape(event)}\b")
            for group, event in TRACE_EVENTS
        }
    enable_failures = {key: value for key, value in event_status.items() if key.endswith(".enable") and value not in {"ok", "missing"}}
    disable_failures = {key: value for key, value in event_status.items() if key.endswith(".disable") and value not in {"ok", "missing"}}
    enabled_ok = sum(1 for key, value in event_status.items() if key.endswith(".enable") and value == "ok")
    target = {
        "pcie1_gdsc": count_lines(trace_lines, r"pcie_1_gdsc"),
        "pcie1_gdsc_enable": count_lines(trace_lines, r"regulator_enable.*pcie_1_gdsc|pcie_1_gdsc.*regulator_enable"),
        "pcie1_gdsc_disable": count_lines(trace_lines, r"regulator_disable.*pcie_1_gdsc|pcie_1_gdsc.*regulator_disable"),
        "pm8150l_l3": count_lines(trace_lines, r"pm8150l_l3"),
        "pm8150_l5": count_lines(trace_lines, r"pm8150_l5"),
        "vdd_cx": count_lines(trace_lines, r"VDD_CX"),
        "pcie1_clock": count_lines(trace_lines, r"GCC_PCIE_1|gcc_pcie_1|pcie_1_|PCIE1_PHY_REFGEN|pcie1_phy_refgen|pcie_phy_refgen|pcie_phy_aux"),
        "gpio102": count_lines(trace_lines, r"gpio_(?:value|direction):\s+102"),
        "gpio104": count_lines(trace_lines, r"gpio_(?:value|direction):\s+104"),
        "gpio135": count_lines(trace_lines, r"gpio_(?:value|direction):\s+135"),
        "gpio142": count_lines(trace_lines, r"gpio_(?:value|direction):\s+142"),
    }
    link_failed = "link initialization failed" in dmesg.lower()
    l0 = bool(re.search(r"LTSSM_L0|link initialized|Current GEN", dmesg, re.I))
    mhi = bool(re.search(r"/dev/mhi|mhi_0305|mhi pipe|mhi channel|mhi_cntrl|mhi-pci|\\bmhi:", dmesg, re.I))
    wlfw = bool(re.search(r"wlfw|FW ready|BDF|wlan0", dmesg, re.I))
    trace_pass = kv.get("result") == "tracefs-enumerate-pass"
    trigger_rc = kv.get("trigger_rc", "")
    mounts_clean = (
        (mount_present(mounts_before, DEBUGFS_ROOT, "debugfs") or not mount_present(mounts_after, DEBUGFS_ROOT, "debugfs"))
        and (
            any(mount_present(mounts_before, root, "tracefs") for root in TRACEFS_ROOTS)
            or not any(mount_present(mounts_after, root, "tracefs") for root in TRACEFS_ROOTS)
        )
    )
    return {
        "trace_result": kv.get("result", ""),
        "trace_root": kv.get("trace_root", ""),
        "trigger_rc": trigger_rc,
        "trace_pass": trace_pass,
        "enabled_ok": enabled_ok,
        "enable_failures": enable_failures,
        "disable_failures": disable_failures,
        "event_counts": event_counts,
        "target_line_count": len(trace_lines),
        "target_counts": target,
        "target_lines": trace_lines[:160],
        "link_failed": link_failed,
        "l0_seen": l0,
        "mhi_seen": mhi,
        "wlfw_or_wlan_seen": wlfw,
        "mounts_clean": mounts_clean,
    }


def decide(analysis: dict[str, Any], steps: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if not analysis["trace_pass"]:
        return (
            "v1551-tracefs-enumerate-observer-failed",
            False,
            f"trace result={analysis['trace_result']}",
            "inspect tracefs-enumerate-observer transcript and cleanup before retry",
        )
    if analysis["trigger_rc"] != "0":
        return (
            "v1551-sysfs-enumerate-trigger-failed",
            False,
            f"trigger_rc={analysis['trigger_rc']}",
            "verify pcie1 enumerate path and do not retry until path state is understood",
        )
    if analysis["enable_failures"] or analysis["disable_failures"]:
        return (
            "v1551-tracefs-event-cleanup-review",
            False,
            f"enable_failures={analysis['enable_failures']} disable_failures={analysis['disable_failures']}",
            "cleanup tracefs event state before another live gate",
        )
    if analysis["target_counts"]["pcie1_gdsc_enable"] > 0 and analysis["link_failed"] and not analysis["l0_seen"]:
        return (
            "v1551-pcie1-gdsc-enable-captured-no-l0",
            True,
            "tracefs captured pcie_1_gdsc enable activity while RC1 still failed before L0",
            "classify PERST/refclk/endpoint response after confirmed RC1 power-domain enable",
        )
    if analysis["target_line_count"] > 0 and analysis["link_failed"] and not analysis["l0_seen"]:
        return (
            "v1551-target-trace-captured-no-gdsc-enable-no-l0",
            True,
            "tracefs captured target PCIe/GPIO/regulator lines but no pcie_1_gdsc enable line; RC1 still failed before L0",
            "inspect event formats/names and consider a narrower tracepoint or source-level timing marker before another enumerate",
        )
    if analysis["link_failed"] and not analysis["l0_seen"]:
        return (
            "v1551-no-target-trace-lines-no-l0",
            True,
            "tracefs observer ran but filtered target lines were empty; RC1 still failed before L0",
            "inspect raw event counts/formats and decide whether names differ from filter assumptions",
        )
    if analysis["l0_seen"]:
        return (
            "v1551-rc1-l0-progress-observed",
            True,
            "RC1 L0/link initialized appeared during tracefs enumerate observer",
            "move to PCI/MHI/WLFW/BDF/wlan0 classification before any scan/connect",
        )
    return (
        "v1551-unclassified-tracefs-enumerate-result",
        False,
        "tracefs observer completed but dmesg did not show expected link-fail or L0 state",
        "inspect evidence manually before proceeding",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = analyze(store, steps)
    decision, passed, reason, next_step = decide(analysis, steps)
    manifest = {
        "cycle": "V1551",
        "type": "bounded live pcie1 tracefs enumerate observer",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "steps": steps,
        "analysis": analysis,
        "safety": {
            "tracefs_write_executed": True,
            "sysfs_client_enumerate_executed": True,
            "pmic_gpio_gdsc_direct_write_executed": False,
            "direct_esoc_ioctl_executed": False,
            "boot_done_spoof_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "flash_executed": False,
            "partition_write_executed": False,
        },
        "out_dir": str(store.run_dir),
    }
    return manifest


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    safety = manifest["safety"]
    target = analysis["target_counts"]
    return "\n".join(
        [
            "# Native Init V1551 PCIe1 Tracefs Enumerate Live",
            "",
            "## Summary",
            "",
            "- Cycle: `V1551`",
            "- Type: bounded live tracefs observer around pcie1 sysfs-client enumerate",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{rel(Path(manifest['out_dir']) / 'manifest.json')}`",
            "",
            "V1551 enables only selected tracefs static events, writes once to the already-proven pcie1 enumerate debugfs endpoint, disables the events, captures filtered trace lines plus dmesg, and verifies post selftest. It does not perform any Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, direct PMIC/GPIO/GDSC write, global PCI rescan, platform bind/unbind, flash, or partition write.",
            "",
            "## Result",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["trace result", analysis["trace_result"]],
                    ["trace root", analysis["trace_root"]],
                    ["trigger rc", analysis["trigger_rc"]],
                    ["enabled events ok", analysis["enabled_ok"]],
                    ["target trace lines", analysis["target_line_count"]],
                    ["pcie_1_gdsc lines", target["pcie1_gdsc"]],
                    ["pcie_1_gdsc enable lines", target["pcie1_gdsc_enable"]],
                    ["pcie_1_gdsc disable lines", target["pcie1_gdsc_disable"]],
                    ["pcie1 clock lines", target["pcie1_clock"]],
                    ["GPIO102 / GPIO104 / GPIO135 / GPIO142", f"{target['gpio102']} / {target['gpio104']} / {target['gpio135']} / {target['gpio142']}"],
                    ["link failed", analysis["link_failed"]],
                    ["L0 seen", analysis["l0_seen"]],
                    ["MHI seen", analysis["mhi_seen"]],
                    ["WLFW/FW-ready/wlan seen", analysis["wlfw_or_wlan_seen"]],
                    ["mount cleanup", analysis["mounts_clean"]],
                ],
            ),
            "",
            "## Event Counts",
            "",
            "```json",
            json.dumps(analysis["event_counts"], indent=2, sort_keys=True),
            "```",
            "",
            "## Target Trace Lines",
            "",
            "\n".join(f"- `{line}`" for line in analysis["target_lines"][:80]) if analysis["target_lines"] else "- none",
            "",
            "## Safety",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in safety.items()]),
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def load_manifest_from_out_dir(out_dir: Path) -> dict[str, Any]:
    path = repo_path(out_dir) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        manifest = plan_manifest()
        store = EvidenceStore(repo_path(args.out_dir))
        manifest["out_dir"] = str(store.run_dir)
        store.write_json("manifest.json", manifest)
        write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": rel(args.out_dir)}, indent=2, sort_keys=True))
        return 0

    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "reclassify":
        existing = load_manifest_from_out_dir(args.out_dir)
        steps = existing.get("steps") if isinstance(existing.get("steps"), list) else []
        manifest = build_manifest(args, store, steps)
    else:
        steps = collect_run(args, store)
        manifest = build_manifest(args, store, steps)
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": manifest["decision"],
                "out_dir": rel(args.out_dir),
                "pass": manifest["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
