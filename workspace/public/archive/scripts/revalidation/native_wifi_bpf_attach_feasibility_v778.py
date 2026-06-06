#!/usr/bin/env python3
"""V778 BPF tracepoint attach feasibility classifier.

This does not attach BPF. It classifies whether the V777-selected tracepoint can
move to a future bounded attach proof with an existing device loader, or whether
a custom static loader build gate is required first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v778-bpf-attach-feasibility")
LATEST_POINTER = Path("tmp/wifi/latest-v778-bpf-attach-feasibility.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 30.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V777_MANIFEST = Path("tmp/wifi/v777-tracepoint-format-classifier/manifest.json")
TARGET_TRACEPOINT = "msm_pil_event.pil_notif"


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
    parser.add_argument("--v777-manifest", type=Path, default=DEFAULT_V777_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    import re

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


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    joined = " ".join(command).lower()
    forbidden = ("bpftool prog load", " bpftrace -", "perf record", " trace_marker", " boot_wlan", " qcwlanstate", " ping ")
    for term in forbidden:
        if term in joined:
            raise RuntimeError(f"forbidden V778 command term {term!r}: {' '.join(command)}")
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def bpf_surface_command(args: argparse.Namespace) -> list[str]:
    script = (
        f"BB={args.busybox}; "
        "for p in /cache/bin/bpftool /bin/bpftool /system/bin/bpftool /vendor/bin/bpftool /cache/bin/bpftrace /bin/bpftrace; do "
        "[ -e \"$p\" ] && echo FOUND:$p; "
        "done; "
        "for f in /proc/sys/kernel/perf_event_paranoid /proc/sys/kernel/unprivileged_bpf_disabled; do "
        "[ -r \"$f\" ] && { printf \"%s=\" \"$f\"; $BB cat \"$f\"; } || true; "
        "done; "
        "[ -e /sys/kernel/tracing ] && echo sys_tracing_exists=1 || echo sys_tracing_exists=0; "
        "[ -e /sys/kernel/debug/tracing ] && echo debug_tracing_exists=1 || echo debug_tracing_exists=0"
    )
    return ["run", args.busybox, "sh", "-c", script]


def host_toolchain_surface() -> dict[str, Any]:
    tools = {
        "aarch64_linux_gnu_gcc": shutil.which("aarch64-linux-gnu-gcc") or "",
        "aarch64_linux_gnu_strip": shutil.which("aarch64-linux-gnu-strip") or "",
        "aarch64_linux_gnu_readelf": shutil.which("aarch64-linux-gnu-readelf") or "",
        "clang": shutil.which("clang") or "",
    }
    headers = {
        "linux_bpf_h": Path("/usr/aarch64-linux-gnu/include/linux/bpf.h").exists() or Path("/usr/include/linux/bpf.h").exists(),
        "linux_perf_event_h": Path("/usr/aarch64-linux-gnu/include/linux/perf_event.h").exists() or Path("/usr/include/linux/perf_event.h").exists(),
        "linux_if_link_h": Path("/usr/aarch64-linux-gnu/include/linux/if_link.h").exists() or Path("/usr/include/linux/if_link.h").exists(),
    }
    return {
        "tools": tools,
        "headers": headers,
        "can_build_static_aarch64_c": bool(tools["aarch64_linux_gnu_gcc"] and tools["aarch64_linux_gnu_strip"] and tools["aarch64_linux_gnu_readelf"]),
        "can_compile_bpf_syscall_loader": bool(headers["linux_bpf_h"] and headers["linux_perf_event_h"]),
    }


def parse_device_surface(text: str) -> dict[str, Any]:
    found = [line.removeprefix("FOUND:") for line in text.splitlines() if line.startswith("FOUND:")]
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("/proc/sys/kernel/"):
            key, _, value = line.partition("=")
            values[key.split("/")[-1]] = value.strip()
        elif line.startswith("sys_tracing_exists=") or line.startswith("debug_tracing_exists="):
            key, _, value = line.partition("=")
            values[key] = value.strip()
    return {
        "loaders_found": found,
        "has_existing_loader": bool(found),
        "perf_event_paranoid": values.get("perf_event_paranoid", ""),
        "unprivileged_bpf_disabled": values.get("unprivileged_bpf_disabled", ""),
        "sys_tracing_exists": values.get("sys_tracing_exists") == "1",
        "debug_tracing_exists": values.get("debug_tracing_exists") == "1",
    }


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v777 = load_json(args.v777_manifest)
    events = v777.get("analysis", {}).get("proof", {}).get("events", {})
    target = events.get(TARGET_TRACEPOINT, {})
    device_surface = parse_device_surface(step_payload(steps, "bpf-loader-surface"))
    return {
        "v777": {
            "manifest": str(repo_path(args.v777_manifest)),
            "decision": v777.get("decision", ""),
            "pass": bool(v777.get("pass")),
            "target": TARGET_TRACEPOINT,
            "target_format_readable": bool(target.get("format_readable")),
            "target_non_common_fields": target.get("non_common_fields", []),
        },
        "host_surface": host_toolchain_surface(),
        "device_surface": device_surface,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str],
              next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    add_check(
        checks,
        "v777-input",
        "pass" if analysis["v777"]["decision"] == "v777-tracepoint-format-fields-classified" else "blocked",
        "blocker",
        f"decision={analysis['v777']['decision']} target={analysis['v777']['target']} readable={analysis['v777']['target_format_readable']}",
        [analysis["v777"]["manifest"]],
        "complete V777 before BPF feasibility classification",
    )
    if manifest["command"] == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V778 feasibility classifier")
        return checks
    add_check(
        checks,
        "bridge-native-health",
        "pass" if any(step.get("name") == "version" and step.get("ok") for step in manifest["steps"]) else "blocked",
        "blocker",
        "version command ok" if any(step.get("name") == "version" and step.get("ok") for step in manifest["steps"]) else "version command missing/failed",
        ["native/version.txt"],
        "restore v724 bridge command path",
    )
    add_check(
        checks,
        "existing-device-loader",
        "review" if not analysis["device_surface"]["has_existing_loader"] else "pass",
        "warn",
        f"loaders_found={analysis['device_surface']['loaders_found']}",
        ["native/bpf-loader-surface.txt"],
        "if no loader exists, build a minimal custom static helper before any attach proof",
    )
    add_check(
        checks,
        "host-build-surface",
        "pass" if analysis["host_surface"]["can_build_static_aarch64_c"] and analysis["host_surface"]["can_compile_bpf_syscall_loader"] else "blocked",
        "blocker",
        f"can_build_static={analysis['host_surface']['can_build_static_aarch64_c']} can_compile_bpf_loader={analysis['host_surface']['can_compile_bpf_syscall_loader']}",
        [],
        "install toolchain/headers or use existing helper build path",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v778-bpf-attach-feasibility-plan-ready",
            True,
            "plan-only; no device command, BPF attach, Wi-Fi action, or network action executed",
            "run V778 feasibility classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v778-bpf-attach-feasibility-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blocker before planning a BPF attach proof",
        )
    if not analysis["device_surface"]["has_existing_loader"]:
        return (
            "v778-custom-bpf-loader-build-needed",
            True,
            "target tracepoint is suitable and host can build a helper, but no bpftool/bpftrace loader exists on device",
            "V779 should build a minimal static aarch64 BPF tracepoint loader; no attach proof until the loader is reviewed and deployed",
        )
    return (
        "v778-existing-bpf-loader-candidate",
        True,
        "device has an existing BPF loader candidate",
        "review loader behavior before any attach proof",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V778 BPF Attach Feasibility",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- wifi_action_executed: `{manifest['wifi_action_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Surface",
        "",
        markdown_table(["signal", "value"], [
            ["target", analysis.get("v777", {}).get("target")],
            ["target_format_readable", analysis.get("v777", {}).get("target_format_readable")],
            ["device_loaders_found", analysis.get("device_surface", {}).get("loaders_found")],
            ["perf_event_paranoid", analysis.get("device_surface", {}).get("perf_event_paranoid")],
            ["unprivileged_bpf_disabled", analysis.get("device_surface", {}).get("unprivileged_bpf_disabled")],
            ["host_can_build_static", analysis.get("host_surface", {}).get("can_build_static_aarch64_c")],
            ["host_can_compile_bpf_loader", analysis.get("host_surface", {}).get("can_compile_bpf_syscall_loader")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command == "run":
        run_step(args, store, steps, "version", ["version"], 10.0)
        run_step(args, store, steps, "bpf-loader-surface", bpf_surface_command(args), 20.0)
    analysis = build_analysis(args, steps)
    manifest: dict[str, Any] = {
        "cycle": "v778",
        "generated_at": now_iso(),
        "command": args.command,
        "steps": steps,
        "analysis": analysis,
        "device_commands_executed": args.command == "run",
        "bpf_attach_executed": False,
        "ftrace_control_write_executed": False,
        "wifi_action_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"bpf_attach_executed: {manifest['bpf_attach_executed']}")
    print(f"wifi_action_executed: {manifest['wifi_action_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
