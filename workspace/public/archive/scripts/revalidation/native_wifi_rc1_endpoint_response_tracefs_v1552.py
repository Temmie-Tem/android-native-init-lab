#!/usr/bin/env python3
"""V1552 bounded RC1 endpoint-response tracefs observer.

V1551 proved that the pcie1 sysfs-client enumerate window enables
`pcie_1_gdsc`, pcie1 refclk/pipe clocks, and GPIO102/PERST activity while the
link still fails before L0. V1552 keeps the same bounded enumerate trigger but
adds IRQ trace events and before/after interrupt snapshots so the remaining
question is narrower: did the endpoint signal WAKE/MDM status/errfatal after
AP-side power/refclk/PERST became active?

This gate does not start Wi-Fi HAL, scan/connect, use credentials, run
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1552_RC1_ENDPOINT_RESPONSE_TRACEFS_LIVE_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1552-rc1-endpoint-response-tracefs-live.txt")

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
    ("clk", "clk_disable"),
    ("clk", "clk_disable_complete"),
    ("gpio", "gpio_direction"),
    ("gpio", "gpio_value"),
    ("irq", "irq_handler_entry"),
    ("irq", "irq_handler_exit"),
)

TARGET_KEYWORDS = (
    "pcie_1_gdsc",
    "regulator_",
    "pm8150",
    "VDD_CX",
    "gcc_pcie_1",
    "pcie_1_",
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
    "irq=204",
    "irq=252",
    "irq=290",
    "mdm errfatal",
    "mdm status",
    "msm_pcie_wake",
    "pcie",
    "mhi",
)

IRQ_NAMES = {
    "mdm_errfatal": ("204", "mdm errfatal"),
    "pcie_wake": ("252", "msm_pcie_wake"),
    "mdm_status": ("290", "mdm status"),
}


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
    if capture.status == "busy" or "[busy]" in stripped:
        hide_capture = run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(timeout or args.timeout, 8.0))
        hide_text = hide_capture.text if hide_capture.text else hide_capture.error + "\n"
        store.write_text(f"native/{safe_name(name)}-hide-on-busy.txt", strip_cmdv1_text(hide_text).rstrip() + "\n")
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


def mount_present(text: str, mountpoint: str, fstype: str) -> bool:
    return re.search(rf"\s{re.escape(mountpoint)}\s+{re.escape(fstype)}\s", text) is not None


def event_label(group: str, event: str) -> str:
    return f"{group}.{event}"


def trace_root_assign() -> str:
    return (
        "TRACE=; "
        "for candidate in /sys/kernel/tracing /sys/kernel/debug/tracing; do "
        "if [ -e \"$candidate/tracing_on\" ] && [ -e \"$candidate/trace\" ]; then TRACE=\"$candidate\"; break; fi; "
        "done; "
        "echo trace_root=\"$TRACE\"; "
        "if [ -z \"$TRACE\" ]; then echo result=tracefs-root-missing; exit 7; fi"
    )


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


def trace_control_script(label: str, events: tuple[tuple[str, str], ...], enable: bool) -> str:
    return "\n".join(["set +e", trace_root_assign(), f"echo trace_control={label}", *trace_event_setup_lines(enable, events)])


def trace_clear_script() -> str:
    return f"""
set +e
{trace_root_assign()}
echo 0 > "$TRACE/tracing_on" 2>/dev/null
echo > "$TRACE/trace" 2>/dev/null
echo trace_clear_done=1
""".strip()


def trace_on_off_script(enable: bool) -> str:
    value = "1" if enable else "0"
    label = "on" if enable else "off"
    return f"""
set +e
{trace_root_assign()}
echo {value} > "$TRACE/tracing_on" 2>/dev/null
echo tracing_{label}_rc=$?
""".strip()


def trigger_script(args: argparse.Namespace) -> str:
    return f"""
set +e
BB={args.busybox}
echo trigger_begin_ms="$($BB date +%s%3N 2>/dev/null || echo 0)"
printf '1\\n' > {PCIE1_ENUMERATE} 2>/dev/null
trigger_rc=$?
echo trigger_rc="$trigger_rc"
echo trigger_end_ms="$($BB date +%s%3N 2>/dev/null || echo 0)"
""".strip()


def dump_script() -> str:
    keyword_pattern = "|".join(re.escape(item) for item in TARGET_KEYWORDS)
    return f"""
set +e
BB={DEFAULT_BUSYBOX}
{trace_root_assign()}
echo target_trace_lines_begin
$BB grep -Ei '{keyword_pattern}' "$TRACE/trace" 2>/dev/null | $BB head -n 2200 || true
echo target_trace_lines_end
echo result=tracefs-endpoint-response-pass
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
echo interrupts_begin
$TOY cat /proc/interrupts 2>/dev/null | $BB grep -iE 'pcie|mhi|mdm|gpio|wake|102|104|135|142' || true
echo interrupts_end
echo link_state_begin
$TOY cat /sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state /sys/devices/platform/soc/1c08000.qcom,pcie/link_state 2>/dev/null || true
echo link_state_end
echo gpio_begin
$BB grep -iE 'gpio-102|gpio102|GPIO102|gpio-104|gpio104|GPIO104|gpio-135|gpio135|GPIO135|gpio-142|gpio142|GPIO142' /sys/kernel/debug/gpio 2>/dev/null || true
echo gpio_end
echo clk_begin
$BB grep -iE 'pcie_1|PCIE_1|pcie1|PCIE1|phy_refgen|clkref|pipe' /sys/kernel/debug/clk/clk_summary 2>/dev/null | $BB head -n 160 || true
echo clk_end
echo regulator_begin
$BB grep -iE 'pcie_1_gdsc|pcie_0_gdsc|pm8150l_l3|pm8150_l5|VDD_CX' /sys/kernel/debug/regulator/regulator_summary /sys/kernel/debug/regulator_summary 2>/dev/null || true
echo regulator_end
echo pci_mhi_begin
$TOY find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true
$TOY ls -l /sys/bus/mhi/devices /dev/mhi* /dev/*mhi* 2>/dev/null || true
echo pci_mhi_end
""".strip()


def dmesg_script(args: argparse.Namespace) -> str:
    return (
        f"{args.toybox} dmesg | {args.busybox} grep -iE "
        "'pci-msm|msm_pcie|pcie|LTSSM|PERST|WAKE|enumerate|mhi|wlfw|bdf|fw ready|wlan0|mdm|gpio' "
        f"| {args.busybox} tail -320 || true"
    )


def extract_block(text: str, begin: str, end: str) -> list[str]:
    out: list[str] = []
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
            out.append(line)
    return out


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
    return "\n".join(
        step_text(store, steps, str(step.get("name") or ""))
        for step in steps
        if str(step.get("name") or "").startswith("tracefs-") or str(step.get("name") or "") == "trigger-enumerate"
    )


def parse_interrupt_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    block = extract_block(text, "interrupts_begin", "interrupts_end")
    for key, (irq, label) in IRQ_NAMES.items():
        total = 0
        for line in block:
            if label.lower() in line.lower() or re.match(rf"\s*{re.escape(irq)}:", line):
                numbers = [int(value) for value in re.findall(r"\b\d+\b", line)]
                if len(numbers) > 1:
                    total = sum(numbers[1:9])
                break
        counts[key] = total
    return counts


def analyze(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    trace_text = combined_trace_text(store, steps)
    trace_lines = extract_block(trace_text, "target_trace_lines_begin", "target_trace_lines_end")
    dmesg = step_text(store, steps, "dmesg-tail")
    before = step_text(store, steps, "snapshot-before")
    after = step_text(store, steps, "snapshot-after")
    mounts_before = step_text(store, steps, "mounts-before")
    mounts_after = step_text(store, steps, "mounts-after")
    kv = parse_key_values(trace_text)
    before_irqs = parse_interrupt_counts(before)
    after_irqs = parse_interrupt_counts(after)
    irq_delta = {key: after_irqs.get(key, 0) - before_irqs.get(key, 0) for key in IRQ_NAMES}
    target_counts = {
        "pcie1_gdsc_enable": count_lines(trace_lines, r"regulator_enable.*pcie_1_gdsc"),
        "pcie1_gdsc_disable": count_lines(trace_lines, r"regulator_disable.*pcie_1_gdsc"),
        "any_regulator": count_lines(trace_lines, r"regulator_"),
        "pm8150_or_vdd": count_lines(trace_lines, r"pm8150|VDD_CX"),
        "refclk_enable": count_lines(trace_lines, r"clk_enable.*(clkref|refgen)"),
        "pipe_clk_enable": count_lines(trace_lines, r"clk_enable.*pipe"),
        "pcie1_clock": count_lines(trace_lines, r"gcc_pcie_1|pcie1_phy_refgen|pcie_phy_refgen|pcie_phy_aux|pcie_1_"),
        "gpio102_set0": count_lines(trace_lines, r"gpio_value:\s+102\s+set\s+0"),
        "gpio102_set1": count_lines(trace_lines, r"gpio_value:\s+102\s+set\s+1"),
        "gpio104": count_lines(trace_lines, r"gpio_(?:value|direction):\s+104"),
        "gpio135": count_lines(trace_lines, r"gpio_(?:value|direction):\s+135"),
        "gpio142": count_lines(trace_lines, r"gpio_(?:value|direction):\s+142"),
        "irq_pcie_wake": count_lines(trace_lines, r"msm_pcie_wake|irq=252"),
        "irq_mdm_status": count_lines(trace_lines, r"mdm status|irq=290"),
        "irq_mdm_errfatal": count_lines(trace_lines, r"mdm errfatal|irq=204"),
        "irq_any": count_lines(trace_lines, r"irq_handler_"),
    }
    event_status = {
        key: value
        for key, value in kv.items()
        if key.startswith("event.") and (key.endswith(".enable") or key.endswith(".disable"))
    }
    enable_failures = {key: value for key, value in event_status.items() if key.endswith(".enable") and value not in {"ok", "missing"}}
    disable_failures = {key: value for key, value in event_status.items() if key.endswith(".disable") and value not in {"ok", "missing"}}
    enabled_ok = sum(1 for key, value in event_status.items() if key.endswith(".enable") and value == "ok")
    return {
        "trace_result": kv.get("result", ""),
        "trace_root": kv.get("trace_root", ""),
        "trigger_rc": kv.get("trigger_rc", ""),
        "enabled_ok": enabled_ok,
        "enable_failures": enable_failures,
        "disable_failures": disable_failures,
        "target_line_count": len(trace_lines),
        "target_counts": target_counts,
        "target_lines": trace_lines[:220],
        "interrupts_before": before_irqs,
        "interrupts_after": after_irqs,
        "interrupt_delta": irq_delta,
        "link_failed": "link initialization failed" in dmesg.lower(),
        "l0_seen": bool(re.search(r"LTSSM_L0|link initialized|Current GEN", dmesg, re.I)),
        "mhi_seen": bool(re.search(r"/dev/mhi|mhi_0305|mhi pipe|mhi channel|mhi_cntrl|mhi-pci|\\bmhi:", dmesg, re.I)),
        "wlfw_or_wlan_seen": bool(re.search(r"wlfw|FW ready|BDF|wlan0", dmesg, re.I)),
        "mounts_clean": (
            (mount_present(mounts_before, DEBUGFS_ROOT, "debugfs") or not mount_present(mounts_after, DEBUGFS_ROOT, "debugfs"))
            and (
                any(mount_present(mounts_before, root, "tracefs") for root in TRACEFS_ROOTS)
                or not any(mount_present(mounts_after, root, "tracefs") for root in TRACEFS_ROOTS)
            )
        ),
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    target = analysis["target_counts"]
    if analysis["trace_result"] != "tracefs-endpoint-response-pass":
        return ("v1552-tracefs-endpoint-observer-failed", False, f"trace result={analysis['trace_result']}", "inspect tracefs setup and cleanup before retry")
    if analysis["trigger_rc"] != "0":
        return ("v1552-sysfs-enumerate-trigger-failed", False, f"trigger_rc={analysis['trigger_rc']}", "verify pcie1 enumerate path before retry")
    if analysis["enable_failures"] or analysis["disable_failures"]:
        return ("v1552-tracefs-event-cleanup-review", False, "tracefs event enable/disable failure present", "cleanup tracefs event state before another live gate")
    endpoint_irq = any(value > 0 for value in analysis["interrupt_delta"].values()) or target["irq_pcie_wake"] or target["irq_mdm_status"] or target["irq_mdm_errfatal"]
    ap_side_ready = target["pcie1_gdsc_enable"] > 0 and target["refclk_enable"] > 0 and target["pipe_clk_enable"] > 0 and target["gpio102_set1"] > 0
    if analysis["l0_seen"]:
        return ("v1552-rc1-l0-progress-observed", True, "RC1 L0/link initialized appeared during endpoint-response trace", "move to PCI/MHI/WLFW/BDF/wlan0 classification before any scan/connect")
    if ap_side_ready and analysis["link_failed"] and not endpoint_irq:
        return (
            "v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0",
            True,
            "pcie1 GDSC/refclk/pipe/PERST release occurred, but WAKE/MDM status/errfatal IRQs stayed silent and RC1 still failed before L0",
            "classify why SDX50M endpoint stays silent after PERST release despite confirmed AP-side RC1 enable",
        )
    if ap_side_ready and analysis["link_failed"] and endpoint_irq:
        return (
            "v1552-endpoint-irq-present-but-no-l0",
            True,
            "endpoint IRQ activity appeared, but RC1 still failed before L0",
            "classify IRQ timing and handler result against LTSSM failure",
        )
    if analysis["link_failed"]:
        return (
            "v1552-link-failed-incomplete-ap-side-proof",
            True,
            "RC1 still failed before L0, but AP-side GDSC/refclk/pipe/PERST proof was incomplete in this trace window",
            "inspect trace formats and choose a narrower AP-side observer",
        )
    return ("v1552-unclassified-endpoint-response-result", False, "trace completed but neither L0 nor expected link-fail marker was observed", "inspect evidence manually before proceeding")


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
    store.write_json("pre_mount_state.json", {"debugfs_mounted_before": debugfs_before, "tracefs_mounted_before": tracefs_before})
    run_shell(args, store, steps, "tracefs-setup", trace_setup_script(), timeout=15.0)
    for group, event in TRACE_EVENTS:
        run_shell(args, store, steps, f"tracefs-disable-initial-{group}-{event}", trace_control_script(f"disable-initial-{group}-{event}", ((group, event),), False), timeout=10.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-clear", trace_clear_script(), timeout=15.0)
    run_shell(args, store, steps, "snapshot-before", snapshot_script(args, "before"), timeout=25.0, allow_error=True)
    for group, event in TRACE_EVENTS:
        run_shell(args, store, steps, f"tracefs-enable-{group}-{event}", trace_control_script(f"enable-{group}-{event}", ((group, event),), True), timeout=10.0)
    run_shell(args, store, steps, "tracefs-on", trace_on_off_script(True), timeout=10.0)
    run_shell(args, store, steps, "trigger-enumerate", trigger_script(args), timeout=20.0)
    run_shell(args, store, steps, "tracefs-settle", f"{args.busybox} sleep 1; true", timeout=5.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-off", trace_on_off_script(False), timeout=10.0, allow_error=True)
    for group, event in TRACE_EVENTS:
        run_shell(args, store, steps, f"tracefs-disable-{group}-{event}", trace_control_script(f"disable-{group}-{event}", ((group, event),), False), timeout=10.0, allow_error=True)
    run_shell(args, store, steps, "tracefs-dump-targets", dump_script(), timeout=20.0, allow_error=True)
    run_shell(args, store, steps, "snapshot-after", snapshot_script(args, "after"), timeout=25.0, allow_error=True)
    run_shell(args, store, steps, "dmesg-tail", dmesg_script(args), timeout=20.0, allow_error=True)
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


def plan_manifest() -> dict[str, Any]:
    return {
        "cycle": "V1552",
        "type": "bounded live RC1 endpoint-response tracefs observer plan",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": "v1552-endpoint-response-tracefs-plan-ready",
        "pass": True,
        "trace_events": [event_label(group, event) for group, event in TRACE_EVENTS],
        "target_irqs": IRQ_NAMES,
        "guardrails": [
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no global PCI rescan or platform bind/unbind",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = analyze(store, steps)
    decision, passed, reason, next_step = decide(analysis)
    return {
        "cycle": "V1552",
        "type": "bounded live RC1 endpoint-response tracefs observer",
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


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    target = analysis["target_counts"]
    return "\n".join(
        [
            "# Native Init V1552 RC1 Endpoint Response Tracefs Live",
            "",
            "## Summary",
            "",
            "- Cycle: `V1552`",
            "- Type: bounded live tracefs observer around pcie1 sysfs-client enumerate with IRQ response sampling",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{rel(Path(manifest['out_dir']) / 'manifest.json')}`",
            "",
            "V1552 extends V1551 with IRQ handler trace events and before/after interrupt snapshots for `msm_pcie_wake`, `mdm status`, and `mdm errfatal`. It keeps the same bounded pcie1 enumerate trigger and preserves the no-HAL/no-connect/no-direct-write guardrails.",
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
                    ["GDSC enable / disable", f"{target['pcie1_gdsc_enable']} / {target['pcie1_gdsc_disable']}"],
                    ["refclk / pipe clk enable", f"{target['refclk_enable']} / {target['pipe_clk_enable']}"],
                    ["GPIO102 set0 / set1", f"{target['gpio102_set0']} / {target['gpio102_set1']}"],
                    ["GPIO104 / GPIO135 / GPIO142 trace", f"{target['gpio104']} / {target['gpio135']} / {target['gpio142']}"],
                    ["IRQ trace wake/status/errfatal", f"{target['irq_pcie_wake']} / {target['irq_mdm_status']} / {target['irq_mdm_errfatal']}"],
                    ["IRQ delta wake/status/errfatal", f"{analysis['interrupt_delta']['pcie_wake']} / {analysis['interrupt_delta']['mdm_status']} / {analysis['interrupt_delta']['mdm_errfatal']}"],
                    ["link failed", analysis["link_failed"]],
                    ["L0 seen", analysis["l0_seen"]],
                    ["MHI seen", analysis["mhi_seen"]],
                    ["WLFW/FW-ready/wlan seen", analysis["wlfw_or_wlan_seen"]],
                    ["mount cleanup", analysis["mounts_clean"]],
                ],
            ),
            "",
            "## Target Trace Lines",
            "",
            "\n".join(f"- `{line}`" for line in analysis["target_lines"][:120]) if analysis["target_lines"] else "- none",
            "",
            "## Safety",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in manifest["safety"].items()]),
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def load_existing_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = repo_path(args.out_dir) / "manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        manifest = plan_manifest()
        if args.write_report:
            write_private_text(
                repo_path(args.report_path),
                "\n".join(
                    [
                        "# Native Init V1552 RC1 Endpoint Response Tracefs Plan",
                        "",
                        "```json",
                        json.dumps(manifest, indent=2, sort_keys=True),
                        "```",
                        "",
                    ]
                ),
            )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "reclassify":
        manifest = load_existing_manifest(args)
        steps = manifest.get("steps", [])
        manifest = build_manifest(args, store, steps)
    else:
        steps = collect_run(args, store)
        manifest = build_manifest(args, store, steps)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), render_report(manifest))
    print(json.dumps({"decision": manifest["decision"], "out_dir": str(store.run_dir), "pass": manifest["pass"]}, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
