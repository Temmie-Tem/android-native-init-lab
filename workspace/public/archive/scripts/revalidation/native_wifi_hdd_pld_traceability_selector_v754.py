#!/usr/bin/env python3
"""V754 read-only HDD/PLD traceability selector.

V753 narrowed the Wi-Fi blocker to missing observability between HDD entry and
driver-loaded / ICNSS-QMI. This selector checks whether the current kernel can
support a bounded ftrace/kallsyms-based observer before any active tracing,
tracefs mount, boot image change, or Wi-Fi trigger is attempted.

It performs read-only captures only. It does not mount tracefs/debugfs, write
ftrace controls, write boot_wlan/qcwlanstate, start daemons, scan/connect, use
credentials, mutate routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v754-hdd-pld-traceability-selector")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V753_MANIFEST = Path("tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json")

TARGET_FUNCTIONS = (
    "__hdd_module_init",
    "wlan_boot_cb",
    "wlan_hdd_state_ctrl_param_create",
    "pld_init",
    "hdd_init",
    "wlan_hdd_register_driver",
    "cds_is_driver_loaded",
    "icnss_register_driver",
    "icnss_wlan_enable",
    "icnss_qmi",
)

SOURCE_REFS = [
    {
        "name": "linux-ftrace-doc",
        "url": "https://docs.kernel.org/next/trace/ftrace.html",
        "signal": "ftrace uses tracefs controls such as current_tracer, available_filter_functions, and set_ftrace_filter",
    },
    {
        "name": "android-qcacld-module-init",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341",
        "signal": "__hdd_module_init orders qcwlanstate, pld_init, hdd_init, register-driver, and driver-loaded markers",
    },
    {
        "name": "android-qcacld-driver-ops",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
        "signal": "wlan_hdd_register_driver is the source-level PLD registration boundary",
    },
]

FORBIDDEN_TERMS = (
    "mount -t",
    " echo ",
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
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
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
        if term in joined:
            raise RuntimeError(f"forbidden V754 command term {term!r}: {' '.join(command)}")


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


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    grep_targets = "|".join(re.escape(name) for name in TARGET_FUNCTIONS)
    config_regex = "CONFIG_(FUNCTION_TRACER|FUNCTION_GRAPH_TRACER|DYNAMIC_FTRACE|KPROBES|KPROBE_EVENTS|KALLSYMS|DEBUG_FS|TRACEFS|FTRACE)"
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 20.0)
    run_step(args, store, steps, "tracefs-full", ["tracefs", "full"], 30.0)
    run_step(
        args,
        store,
        steps,
        "tracefs-kernel-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== filesystems ==\\n'; \"$BB\" cat /proc/filesystems 2>&1 | \"$BB\" grep -Ei 'tracefs|debugfs' || true; "
                "printf '== mounts ==\\n'; \"$BB\" cat /proc/mounts 2>&1 | \"$BB\" grep -Ei 'tracefs|debugfs|tracing' || true; "
                "for p in /sys/kernel/tracing /sys/kernel/debug/tracing; do "
                "printf '== %s ==\\n' \"$p\"; \"$BB\" ls -la \"$p\" 2>&1 || true; "
                "for f in available_tracers current_tracer available_filter_functions set_ftrace_filter set_graph_function tracing_on trace; do "
                "printf '== %s/%s ==\\n' \"$p\" \"$f\"; "
                "if [ -r \"$p/$f\" ]; then \"$BB\" head -n 20 \"$p/$f\" 2>&1; else printf 'not-readable\\n'; fi; "
                "done; "
                "done; "
                "printf '== config ==\\n'; "
                "if [ -r /proc/config.gz ]; then \"$BB\" zcat /proc/config.gz 2>&1 | \"$BB\" grep -E '" + config_regex + "' || true; else printf 'config-gz-not-readable\\n'; fi"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "target-kallsyms",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "printf '== target kallsyms ==\\n'; "
                "\"$BB\" cat /proc/kallsyms 2>&1 | "
                "\"$BB\" grep -Ei '" + grep_targets + "' | "
                "\"$BB\" head -n 220 || true"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "target-filter-functions-if-mounted",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "for f in /sys/kernel/tracing/available_filter_functions /sys/kernel/debug/tracing/available_filter_functions; do "
                "printf '== %s ==\\n' \"$f\"; "
                "if [ -r \"$f\" ]; then \"$BB\" grep -Ei '" + grep_targets + "' \"$f\" | \"$BB\" head -n 220 || true; else printf 'not-readable\\n'; fi; "
                "done"
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


def extract_function_hits(text: str) -> dict[str, int]:
    return {name: len(re.findall(re.escape(name), text, re.IGNORECASE)) for name in TARGET_FUNCTIONS}


def config_enabled(text: str, name: str) -> bool:
    return has(text, rf"^{re.escape(name)}=(y|m|1)$")


def load_v753(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v753_manifest)
    return {
        "manifest": str(repo_path(args.v753_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "device_mutations": bool(manifest.get("device_mutations")),
        "next_step": manifest.get("next_step", ""),
    }


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    tracefs_full = step_payload(steps, "tracefs-full")
    surface = step_payload(steps, "tracefs-kernel-surface")
    kallsyms = step_payload(steps, "target-kallsyms")
    filter_functions = step_payload(steps, "target-filter-functions-if-mounted")
    combined = "\n".join([tracefs_full, surface])
    kallsyms_hits = extract_function_hits(kallsyms)
    filter_hits = extract_function_hits(filter_functions)
    target_core = ("__hdd_module_init", "wlan_boot_cb", "wlan_hdd_register_driver", "pld_init", "hdd_init")
    return {
        "v753": load_v753(args),
        "current": {
            "version_ok": "A90 Linux init" in step_payload(steps, "version"),
            "status_ok": "BOOT OK" in step_payload(steps, "status"),
        },
        "tracefs": {
            "fs_tracefs": has(combined, r"\btracefs\b|fs_tracefs=yes|tracefs=fs=yes"),
            "fs_debugfs": has(combined, r"\bdebugfs\b|fs_debugfs=yes|debugfs=yes"),
            "tracefs_mounted": has(combined, r"\s/sys/kernel/tracing\s+tracefs\s|\s/sys/kernel/debug/tracing\s+tracefs\s|mount_tracefs=yes|mounted=yes"),
            "debugfs_mounted": has(combined, r"\s/sys/kernel/debug\s+debugfs\s|mount_debugfs=yes"),
            "available_tracers_readable": has(surface, r"== .*/available_tracers ==\n(?!not-readable)"),
            "available_filter_functions_readable": has(surface, r"== .*/available_filter_functions ==\n(?!not-readable)"),
            "current_tracer_readable": has(surface, r"== .*/current_tracer ==\n(?!not-readable)"),
            "function_tracer_config": config_enabled(surface, "CONFIG_FUNCTION_TRACER"),
            "function_graph_config": config_enabled(surface, "CONFIG_FUNCTION_GRAPH_TRACER"),
            "dynamic_ftrace_config": config_enabled(surface, "CONFIG_DYNAMIC_FTRACE"),
            "kprobes_config": config_enabled(surface, "CONFIG_KPROBES"),
            "kprobe_events_config": config_enabled(surface, "CONFIG_KPROBE_EVENTS"),
            "kallsyms_config": config_enabled(surface, "CONFIG_KALLSYMS"),
            "debug_fs_config": config_enabled(surface, "CONFIG_DEBUG_FS"),
        },
        "targets": {
            "kallsyms_hits": kallsyms_hits,
            "filter_function_hits": filter_hits,
            "core_kallsyms_present": all(kallsyms_hits.get(name, 0) > 0 for name in target_core),
            "any_kallsyms_present": any(value > 0 for value in kallsyms_hits.values()),
            "core_filter_present": all(filter_hits.get(name, 0) > 0 for name in target_core),
            "any_filter_present": any(value > 0 for value in filter_hits.values()),
        },
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


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    v753 = analysis["v753"]
    tracefs = analysis["tracefs"]
    targets = analysis["targets"]
    current = analysis["current"]
    checks: list[Check] = []
    add_check(
        checks,
        "v753-input",
        "pass" if v753["decision"] == "v753-hdd-pld-register-driver-gap-needs-instrumentation" and v753["pass"] else "blocked",
        "blocker",
        f"decision={v753['decision']} pass={v753['pass']} mutations={v753['device_mutations']}",
        [v753["manifest"]],
        "complete V753 before selecting instrumentation",
    )
    add_check(
        checks,
        "current-native-healthy",
        "pass" if current["version_ok"] and current["status_ok"] else "blocked",
        "blocker",
        f"version_ok={current['version_ok']} status_ok={current['status_ok']}",
        [],
        "restore native bridge/device health before V754",
    )
    add_check(
        checks,
        "tracefs-support-present",
        "pass" if tracefs["fs_tracefs"] else "blocked",
        "blocker",
        f"tracefs={tracefs['fs_tracefs']} debugfs={tracefs['fs_debugfs']} mounted={tracefs['tracefs_mounted']} debugfs_mounted={tracefs['debugfs_mounted']}",
        ["native/tracefs-kernel-surface.txt", "native/tracefs-full.txt"],
        "without tracefs support, V754 must route to boot-image/kernel-log instrumentation",
    )
    add_check(
        checks,
        "target-symbols-visible",
        "pass" if targets["any_kallsyms_present"] else "blocked",
        "blocker",
        f"core_kallsyms_present={targets['core_kallsyms_present']} hits={targets['kallsyms_hits']}",
        ["native/target-kallsyms.txt"],
        "if symbols are hidden, ftrace filters cannot be planned from names",
    )
    add_check(
        checks,
        "tracefs-not-active-yet",
        "pass" if not tracefs["tracefs_mounted"] else "review",
        "finding",
        f"tracefs_mounted={tracefs['tracefs_mounted']} current_tracer_readable={tracefs['current_tracer_readable']} available_filter_functions={tracefs['available_filter_functions_readable']}",
        ["native/tracefs-kernel-surface.txt"],
        "if already mounted, route directly to bounded filter dry-run",
    )
    add_check(
        checks,
        "ftrace-config-surface",
        "pass" if tracefs["function_tracer_config"] or tracefs["dynamic_ftrace_config"] or tracefs["available_tracers_readable"] else "review",
        "finding",
        f"function={tracefs['function_tracer_config']} graph={tracefs['function_graph_config']} dynamic={tracefs['dynamic_ftrace_config']} kprobes={tracefs['kprobes_config']} kprobe_events={tracefs['kprobe_events_config']} kallsyms={tracefs['kallsyms_config']} debug_fs={tracefs['debug_fs_config']}",
        ["native/tracefs-kernel-surface.txt"],
        "if config is incomplete, use kallsyms/dmesg instrumentation instead",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v754-hdd-pld-traceability-selector-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only traceability selector",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v754-hdd-pld-traceability-selector-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before choosing instrumentation",
        )
    tracefs = analysis["tracefs"]
    targets = analysis["targets"]
    if tracefs["tracefs_mounted"] and targets["any_filter_present"]:
        return (
            "v754-ftrace-filter-ready",
            True,
            "tracefs is mounted and target functions are visible in available_filter_functions",
            "V755 can run a bounded ftrace filter dry-run before pairing with boot_wlan",
        )
    if tracefs["fs_tracefs"] and targets["any_kallsyms_present"] and not tracefs["tracefs_mounted"]:
        return (
            "v754-tracefs-mount-gated-observer-needed",
            True,
            "tracefs support and target kallsyms exist, but tracefs is not mounted; active ftrace readiness needs an explicit bounded mount/filter proof",
            "V755 should mount tracefs with cleanup, verify target available_filter_functions, then stop before boot_wlan",
        )
    return (
        "v754-traceability-classified-review",
        True,
        "read-only traceability completed but needs manual review",
        "inspect manifest before selecting V755",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs") or {}
    targets = analysis.get("targets") or {}
    return "\n".join([
        "# V754 HDD/PLD Traceability Selector",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- tracefs_mount_executed: `{manifest['tracefs_mount_executed']}`",
        f"- ftrace_write_executed: `{manifest['ftrace_write_executed']}`",
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
        "## Tracefs Surface",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in tracefs.items()]) if tracefs else "- plan only",
        "",
        "## Target Function Surface",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in targets.items()]) if targets else "- plan only",
        "",
        "## Source References",
        "",
        markdown_table(["name", "signal", "url"], [
            [item["name"], item["signal"], item["url"]]
            for item in SOURCE_REFS
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    checks: list[Check] = []
    if args.command != "plan":
        steps = collect_steps(args, store)
        analysis = build_analysis(args, steps)
        checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v754",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "tracefs_mount_executed": False,
        "ftrace_write_executed": False,
        "debugfs_mount_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "source_refs": SOURCE_REFS,
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
    latest = repo_path("tmp/wifi/latest-v754-hdd-pld-traceability-selector.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"tracefs_mount_executed: {manifest['tracefs_mount_executed']}")
    print(f"ftrace_write_executed: {manifest['ftrace_write_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
