#!/usr/bin/env python3
"""V756 read-only non-ftrace HDD/PLD observability classifier.

V755 closed the ftrace/function-filter path for the current kernel state. This
classifier checks the remaining low-risk observability routes before any new
Wi-Fi trigger, daemon start, boot image write, or credential use is attempted.

It captures read-only dynamic-debug, kprobe-event, printk/loglevel, config,
focused dmesg, and WLAN sysfs surfaces. It does not mount tracefs/debugfs, write
dynamic-debug/ftrace/kprobe controls, write boot_wlan/qcwlanstate, start
service-manager or Wi-Fi HAL, scan/connect, use credentials, mutate routes, or
ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v756-nonftrace-hdd-pld-observability")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V753_MANIFEST = Path("tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json")
DEFAULT_V755_MANIFEST = Path("tmp/wifi/v755-tracefs-mount-filter-proof-retry/manifest.json")

TARGET_TERMS = (
    "wlan_boot_cb",
    "wlan_hdd_state_ctrl_param_create",
    "pld_init",
    "hdd_init",
    "wlan_hdd_register_driver",
    "icnss_register_driver",
    "icnss_wlan_enable",
    "icnss_qmi",
    "qcwlanstate",
    "wlan: Loading driver",
    "wlan: driver loaded",
    "Modules not initialized",
)

CONFIG_OPTIONS = (
    "CONFIG_DYNAMIC_DEBUG",
    "CONFIG_DYNAMIC_DEBUG_CORE",
    "CONFIG_KPROBES",
    "CONFIG_KPROBE_EVENTS",
    "CONFIG_UPROBE_EVENTS",
    "CONFIG_EVENT_TRACING",
    "CONFIG_FUNCTION_TRACER",
    "CONFIG_FUNCTION_GRAPH_TRACER",
    "CONFIG_DYNAMIC_FTRACE",
    "CONFIG_FTRACE",
    "CONFIG_TRACEPOINTS",
    "CONFIG_PRINTK",
    "CONFIG_PRINTK_TIME",
    "CONFIG_LOG_BUF_SHIFT",
    "CONFIG_KALLSYMS",
    "CONFIG_KALLSYMS_ALL",
    "CONFIG_DEBUG_FS",
    "CONFIG_TRACEFS_FS",
)

SOURCE_REFS = [
    {
        "name": "linux-dynamic-debug",
        "url": "https://docs.kernel.org/admin-guide/dynamic-debug-howto.html",
        "signal": "dynamic debug exposes a read catalog at /proc/dynamic_debug/control when available; writes enable pr_debug callsites",
    },
    {
        "name": "linux-kprobe-events",
        "url": "https://docs.kernel.org/trace/kprobetrace.html",
        "signal": "kprobe events are created through tracefs kprobe_events and require a writable tracing event surface",
    },
    {
        "name": "linux-printk",
        "url": "https://docs.kernel.org/core-api/printk-basics.html",
        "signal": "printk messages are stored in the kernel log buffer exported to userspace",
    },
]

FORBIDDEN_TERMS = (
    " mount -t ",
    " umount ",
    " echo ",
    "set_ftrace_filter",
    "set_graph_function",
    "current_tracer",
    "tracing_on",
    "trace_marker",
    "dynamic_debug/control +p",
    "kprobe_events",
    "boot_wlan 1",
    "qcwlanstate on",
    "/bind",
    "/unbind",
    "driver_override",
    "insmod",
    "rmmod",
    "modprobe",
    "servicemanager",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--v753-manifest", type=Path, default=DEFAULT_V753_MANIFEST)
    parser.add_argument("--v755-manifest", type=Path, default=DEFAULT_V755_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term == "kprobe_events":
            continue
        if term in joined:
            raise RuntimeError(f"forbidden V756 command term {term!r}: {' '.join(command)}")
    if re.search(r">\s*/(proc|sys|dev|vendor|system|data|cache|mnt)/", joined):
        raise RuntimeError(f"forbidden V756 shell redirect: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def target_regex() -> str:
    return "|".join(re.escape(term) for term in TARGET_TERMS)


def config_regex() -> str:
    return "|".join(re.escape(option) for option in CONFIG_OPTIONS)


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    targets = target_regex()
    configs = config_regex()
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 20.0)
    run_step(args, store, steps, "selftest", ["selftest", "verbose"], 30.0)
    run_step(args, store, steps, "tracefs-full", ["tracefs", "full"], 30.0)
    run_step(
        args,
        store,
        steps,
        "cmdline-printk-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== cmdline ==\\n'; \"$BB\" cat /proc/cmdline 2>&1 || true; "
                "printf '== printk ==\\n'; \"$BB\" cat /proc/sys/kernel/printk 2>&1 || true; "
                "for f in /sys/module/printk/parameters/ignore_loglevel /sys/module/printk/parameters/time; do "
                "printf '== %s ==\\n' \"$f\"; "
                "if [ -r \"$f\" ]; then printf 'readable=1\\n'; \"$BB\" cat \"$f\" 2>&1 || true; else printf 'readable=0\\n'; fi; "
                "done"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "dynamic-debug-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "for p in /proc/dynamic_debug/control /sys/kernel/debug/dynamic_debug/control; do "
                "printf '== %s ==\\n' \"$p\"; "
                "if [ -e \"$p\" ]; then printf 'exists=1\\n'; else printf 'exists=0\\n'; fi; "
                "if [ -r \"$p\" ]; then "
                "printf 'readable=1\\n'; "
                "\"$BB\" wc -l \"$p\" 2>&1 || true; "
                "\"$BB\" grep -Ei 'qcacld|wlan|hdd|pld|icnss|cnss|qdf|cds|wma|ol_' \"$p\" 2>&1 | \"$BB\" head -n 140 || true; "
                "else printf 'readable=0\\n'; fi; "
                "done"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "probe-event-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== filesystems ==\\n'; \"$BB\" cat /proc/filesystems 2>&1 | \"$BB\" grep -Ei 'tracefs|debugfs' || true; "
                "printf '== mounts ==\\n'; \"$BB\" cat /proc/mounts 2>&1 | \"$BB\" grep -Ei 'tracefs|debugfs|tracing' || true; "
                "for p in /sys/kernel/tracing/kprobe_events /sys/kernel/debug/tracing/kprobe_events /sys/kernel/tracing/uprobe_events /sys/kernel/debug/tracing/uprobe_events; do "
                "printf '== %s ==\\n' \"$p\"; "
                "if [ -e \"$p\" ]; then printf 'exists=1\\n'; else printf 'exists=0\\n'; fi; "
                "if [ -r \"$p\" ]; then printf 'readable=1\\n'; \"$BB\" head -n 40 \"$p\" 2>&1 || true; else printf 'readable=0\\n'; fi; "
                "done"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "config-observability",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "if [ -r /proc/config.gz ]; then "
                "\"$BB\" zcat /proc/config.gz 2>&1 | \"$BB\" grep -E '^(" + configs + ")=|^# (" + configs + ") is not set' || true; "
                "else printf 'config-gz-not-readable\\n'; fi"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "focused-dmesg",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "\"$BB\" dmesg 2>&1 | "
                "\"$BB\" grep -Ei 'pld|hdd|qcwlan|wlan|icnss|cnss|qca|qdf|cds|mhi|pci|firmware|driver loaded|driver load|Modules not initialized' | "
                "\"$BB\" tail -n 320 || true"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "wlan-sysfs-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== proc modules ==\\n'; \"$BB\" cat /proc/modules 2>&1 | \"$BB\" grep -Ei 'wlan|cnss|icnss|qca|mhi' || true; "
                "for d in /sys/module/wlan /sys/module/icnss /sys/module/cnss2 /sys/bus/platform/drivers/cnss2 /sys/bus/platform/drivers/icnss /sys/class/ieee80211 /sys/class/net /sys/class/net/wlan0 /sys/devices/virtual/misc/qcwlanstate; do "
                "printf '== %s ==\\n' \"$d\"; "
                "if [ -e \"$d\" ]; then printf 'exists=1\\n'; \"$BB\" ls -la \"$d\" 2>&1 | \"$BB\" head -n 80 || true; else printf 'exists=0\\n'; fi; "
                "done"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "target-kallsyms-confirm",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== target kallsyms ==\\n'; "
                "\"$BB\" cat /proc/kallsyms 2>&1 | \"$BB\" grep -Ei '" + targets + "' | \"$BB\" head -n 220 || true"
            ),
        ],
        args.timeout,
    )
    return steps


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def config_enabled(text: str, name: str) -> bool:
    return has(text, rf"^{re.escape(name)}=(y|m|1)$")


def config_value(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}=(.*)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    if has(text, rf"^# {re.escape(name)} is not set$"):
        return "n"
    return "unset"


def target_hits(text: str) -> dict[str, int]:
    return {term: len(re.findall(re.escape(term), text, re.IGNORECASE)) for term in TARGET_TERMS}


def load_input_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    return {
        "manifest": str(repo_path(path)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "device_mutations": bool(manifest.get("device_mutations")),
        "next_step": manifest.get("next_step", ""),
    }


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    dynamic_debug = step_payload(steps, "dynamic-debug-surface")
    probe_surface = step_payload(steps, "probe-event-surface")
    config = step_payload(steps, "config-observability")
    printk = step_payload(steps, "cmdline-printk-surface")
    dmesg = step_payload(steps, "focused-dmesg")
    sysfs = step_payload(steps, "wlan-sysfs-surface")
    kallsyms = step_payload(steps, "target-kallsyms-confirm")
    tracefs_full = step_payload(steps, "tracefs-full")
    dynamic_hits = target_hits(dynamic_debug)
    dmesg_hits = target_hits(dmesg)
    kallsyms_hits = target_hits(kallsyms)
    return {
        "v753": load_input_manifest(args.v753_manifest),
        "v755": load_input_manifest(args.v755_manifest),
        "current": {
            "version_ok": "A90 Linux init" in step_payload(steps, "version"),
            "status_ok": "BOOT OK" in step_payload(steps, "status"),
            "selftest_ok": "fail=0" in step_payload(steps, "selftest") or "fail: 0" in step_payload(steps, "selftest"),
        },
        "dynamic_debug": {
            "config_dynamic_debug": config_enabled(config, "CONFIG_DYNAMIC_DEBUG"),
            "config_dynamic_debug_core": config_enabled(config, "CONFIG_DYNAMIC_DEBUG_CORE"),
            "control_exists": has(dynamic_debug, r"exists=1"),
            "control_readable": has(dynamic_debug, r"readable=1"),
            "target_hits": dynamic_hits,
            "any_target_hit": any(value > 0 for value in dynamic_hits.values()),
        },
        "kprobe": {
            "config_kprobes": config_enabled(config, "CONFIG_KPROBES"),
            "config_kprobe_events": config_enabled(config, "CONFIG_KPROBE_EVENTS"),
            "config_event_tracing": config_enabled(config, "CONFIG_EVENT_TRACING"),
            "event_file_exists": has(probe_surface, r"== .*/kprobe_events ==\nexists=1"),
            "event_file_readable": has(probe_surface, r"== .*/kprobe_events ==\nexists=1\nreadable=1"),
            "tracefs_mounted": has(probe_surface + "\n" + tracefs_full, r"\s/sys/kernel/tracing\s+tracefs\s|\s/sys/kernel/debug/tracing\s+tracefs\s|mount_tracefs=yes"),
        },
        "printk": {
            "config_printk": config_enabled(config, "CONFIG_PRINTK"),
            "printk_time": config_value(config, "CONFIG_PRINTK_TIME"),
            "log_buf_shift": config_value(config, "CONFIG_LOG_BUF_SHIFT"),
            "ignore_loglevel_readable": has(printk, r"ignore_loglevel.*\nreadable=1"),
            "current_printk": "\n".join(printk.splitlines()[0:18]),
        },
        "dmesg": {
            "target_hits": dmesg_hits,
            "loading_driver": dmesg_hits.get("wlan: Loading driver", 0),
            "driver_loaded": dmesg_hits.get("wlan: driver loaded", 0),
            "modules_not_initialized": dmesg_hits.get("Modules not initialized", 0),
            "any_hdd_pld_marker": any(dmesg_hits.get(term, 0) > 0 for term in ("pld_init", "hdd_init", "wlan_hdd_register_driver")),
        },
        "sysfs": {
            "wlan_module_exists": has(sysfs, r"== /sys/module/wlan ==\nexists=1"),
            "qcwlanstate_exists": has(sysfs, r"== /sys/devices/virtual/misc/qcwlanstate ==\nexists=1"),
            "wiphy_exists": has(sysfs, r"== /sys/class/ieee80211 ==\nexists=1") and not has(sysfs, r"== /sys/class/ieee80211 ==\nexists=1\n.*total 0\b"),
            "wlan0_exists": has(sysfs, r"== /sys/class/net/wlan0 ==\nexists=1"),
            "proc_module_wlan_loaded": has(sysfs, r"^wlan\s"),
        },
        "kallsyms": {
            "target_hits": kallsyms_hits,
            "any_target_hit": any(value > 0 for value in kallsyms_hits.values()),
        },
        "config": {name: config_value(config, name) for name in CONFIG_OPTIONS},
        "source_refs": SOURCE_REFS,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(analysis: dict[str, Any] | None) -> list[Check]:
    if not analysis:
        return []
    v753 = analysis["v753"]
    v755 = analysis["v755"]
    current = analysis["current"]
    dynamic_debug = analysis["dynamic_debug"]
    kprobe = analysis["kprobe"]
    dmesg = analysis["dmesg"]
    sysfs = analysis["sysfs"]
    checks: list[Check] = []
    add_check(
        checks,
        "v753-input",
        "pass" if v753["decision"] == "v753-hdd-pld-register-driver-gap-needs-instrumentation" and v753["pass"] else "blocked",
        "blocker",
        f"decision={v753['decision']} pass={v753['pass']} mutations={v753['device_mutations']}",
        [v753["manifest"]],
        "complete V753 before selecting non-ftrace observability",
    )
    add_check(
        checks,
        "v755-input",
        "pass" if v755["decision"] == "v755-tracefs-mounted-no-target-filter-functions" and v755["pass"] else "blocked",
        "blocker",
        f"decision={v755['decision']} pass={v755['pass']} mutations={v755['device_mutations']}",
        [v755["manifest"]],
        "complete V755 before leaving ftrace route",
    )
    add_check(
        checks,
        "current-native-healthy",
        "pass" if current["version_ok"] and current["status_ok"] and current["selftest_ok"] else "blocked",
        "blocker",
        f"version_ok={current['version_ok']} status_ok={current['status_ok']} selftest_ok={current['selftest_ok']}",
        ["native/version.txt", "native/status.txt", "native/selftest.txt"],
        "restore native health before classifying instrumentation",
    )
    add_check(
        checks,
        "dynamic-debug-route",
        "pass" if dynamic_debug["control_readable"] and dynamic_debug["any_target_hit"] else "review",
        "finding",
        f"config={dynamic_debug['config_dynamic_debug']} core={dynamic_debug['config_dynamic_debug_core']} control_exists={dynamic_debug['control_exists']} readable={dynamic_debug['control_readable']} target_hits={dynamic_debug['target_hits']}",
        ["native/dynamic-debug-surface.txt", "native/config-observability.txt"],
        "if pass, plan a bounded dynamic-debug write/rollback proof; otherwise reject dyndbg route",
    )
    add_check(
        checks,
        "kprobe-route",
        "pass" if kprobe["config_kprobes"] and kprobe["config_kprobe_events"] and kprobe["event_file_readable"] else "review",
        "finding",
        f"kprobes={kprobe['config_kprobes']} kprobe_events={kprobe['config_kprobe_events']} event_tracing={kprobe['config_event_tracing']} event_file_exists={kprobe['event_file_exists']} readable={kprobe['event_file_readable']} tracefs_mounted={kprobe['tracefs_mounted']}",
        ["native/probe-event-surface.txt", "native/config-observability.txt"],
        "if pass, plan a bounded kprobe dry-run; otherwise reject kprobe route",
    )
    add_check(
        checks,
        "existing-dmesg-resolution",
        "review" if not dmesg["any_hdd_pld_marker"] and dmesg["driver_loaded"] == 0 else "pass",
        "finding",
        f"loading={dmesg['loading_driver']} driver_loaded={dmesg['driver_loaded']} modules_not_initialized={dmesg['modules_not_initialized']} hdd_pld_marker={dmesg['any_hdd_pld_marker']}",
        ["native/focused-dmesg.txt"],
        "if only loading/qcwlanstate is visible, existing dmesg is insufficient",
    )
    add_check(
        checks,
        "contained-no-netdev",
        "pass" if not sysfs["wlan0_exists"] else "review",
        "finding",
        f"wlan_module={sysfs['wlan_module_exists']} qcwlanstate={sysfs['qcwlanstate_exists']} wiphy={sysfs['wiphy_exists']} wlan0={sysfs['wlan0_exists']} proc_module_wlan={sysfs['proc_module_wlan_loaded']}",
        ["native/wlan-sysfs-surface.txt"],
        "if wlan0 appears, switch to connection-stage gates",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v756-nonftrace-hdd-pld-observability-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only V756 classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v756-nonftrace-observability-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before continuing",
        )
    if not analysis:
        return (
            "v756-nonftrace-observability-missing-analysis",
            False,
            "analysis missing",
            "rerun V756",
        )
    dynamic_debug = analysis["dynamic_debug"]
    kprobe = analysis["kprobe"]
    if dynamic_debug["control_readable"] and dynamic_debug["any_target_hit"]:
        return (
            "v756-dynamic-debug-route-selected",
            True,
            "dynamic-debug catalog is readable and contains target HDD/PLD callsites",
            "V757 should perform bounded dyndbg enable/observe/rollback without Wi-Fi connect",
        )
    if kprobe["config_kprobes"] and kprobe["config_kprobe_events"] and kprobe["event_file_readable"]:
        return (
            "v756-kprobe-route-selected",
            True,
            "kprobe event surface is readable and configured",
            "V757 should perform bounded kprobe event dry-run before any Wi-Fi trigger",
        )
    return (
        "v756-nonftrace-live-observers-exhausted",
        True,
        "ftrace is closed and current dynamic-debug/kprobe read surfaces do not provide usable HDD/PLD target observability",
        "V757 should plan Android/native dmesg differential expansion or boot-image log instrumentation with rollback",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V756 Non-ftrace HDD/PLD Observability",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- dynamic_debug_write_executed: `{manifest['dynamic_debug_write_executed']}`",
        f"- kprobe_write_executed: `{manifest['kprobe_write_executed']}`",
        f"- tracefs_mount_executed: `{manifest['tracefs_mount_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Route Signals",
        "",
        markdown_table(["signal", "value"], [
            ["dynamic_debug", (analysis.get("dynamic_debug") or {})],
            ["kprobe", (analysis.get("kprobe") or {})],
            ["printk", (analysis.get("printk") or {})],
            ["dmesg", (analysis.get("dmesg") or {})],
            ["sysfs", (analysis.get("sysfs") or {})],
        ]) if analysis else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] | None = None
    if args.command != "plan":
        steps = collect_steps(args, store)
        analysis = build_analysis(args, steps)
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v756",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "tracefs_mount_executed": False,
        "debugfs_mount_executed": False,
        "ftrace_write_executed": False,
        "dynamic_debug_write_executed": False,
        "kprobe_write_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis or {},
        "checks": [asdict(check) for check in checks],
        "steps": steps,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v756-nonftrace-hdd-pld-observability.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"dynamic_debug_write_executed: {manifest['dynamic_debug_write_executed']}")
    print(f"kprobe_write_executed: {manifest['kprobe_write_executed']}")
    print(f"tracefs_mount_executed: {manifest['tracefs_mount_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
