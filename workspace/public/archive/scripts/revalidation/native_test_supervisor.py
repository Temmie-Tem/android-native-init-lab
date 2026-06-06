#!/usr/bin/env python3
"""A90 native-init host test supervisor."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a90harness.device import DeviceClient  # noqa: E402
from a90harness.bundle import finalize_bundle  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from a90harness.gate import GateOptions, evaluate_gate  # noqa: E402
from a90harness.modules.cpu_mem_thermal import CpuMemThermalModule  # noqa: E402
from a90harness.modules.cpu_memory_profiles import CpuMemoryProfilesModule  # noqa: E402
from a90harness.modules.kselftest_feasibility import KselftestFeasibilityModule  # noqa: E402
from a90harness.modules.ncm_tcp_preflight import NcmTcpPreflightModule  # noqa: E402
from a90harness.modules.storage_io import StorageIoModule  # noqa: E402
from a90harness.modules.usb_recovery import UsbRecoveryModule  # noqa: E402
from a90harness.observer import run_observer  # noqa: E402
from a90harness.runner import ModuleRunner  # noqa: E402
from a90harness.scheduler import build_schedule, run_mixed_soak_schedule, schedule_document  # noqa: E402
from a90harness.schema import CheckResult, CommandRecord, HarnessResult  # noqa: E402


DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
DEFAULT_BROKER_RUNTIME_DIR = Path("tmp/a90-broker")
DEFAULT_BROKER_SOCKET_NAME = "a90b1.sock"
MODULES = {
    CpuMemoryProfilesModule.name: CpuMemoryProfilesModule,
    CpuMemThermalModule.name: CpuMemThermalModule,
    KselftestFeasibilityModule.name: KselftestFeasibilityModule,
    NcmTcpPreflightModule.name: NcmTcpPreflightModule,
    StorageIoModule.name: StorageIoModule,
    UsbRecoveryModule.name: UsbRecoveryModule,
}


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_run_dir(label: str) -> Path:
    return REPO_ROOT / "tmp" / "soak" / "harness" / f"{label}-{utc_stamp()}"


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def broker_socket_path(args: argparse.Namespace) -> Path | None:
    if args.device_backend != "broker":
        return None
    if args.broker_socket is not None:
        return resolve_repo_path(args.broker_socket)
    return resolve_repo_path(args.broker_runtime_dir) / args.broker_socket_name


def make_device_client(args: argparse.Namespace) -> DeviceClient:
    return DeviceClient(
        args.host,
        args.port,
        args.timeout,
        backend=args.device_backend,
        broker_socket=broker_socket_path(args),
        client_id=args.broker_client_id,
    )


def parse_duration(value: str) -> float | None:
    if value.lower() == "unlimited":
        return None
    duration = float(value)
    if duration <= 0:
        raise argparse.ArgumentTypeError("duration must be positive or 'unlimited'")
    return duration


def run_host_command(command: list[str], timeout: int = 10) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def host_metadata() -> dict[str, Any]:
    rc, head = run_host_command(["git", "rev-parse", "--short", "HEAD"], timeout=5)
    rc_status, status = run_host_command(["git", "status", "--short"], timeout=5)
    return {
        "repo": str(REPO_ROOT),
        "git_head": head.strip() if rc == 0 else "unknown",
        "git_dirty": bool(rc_status == 0 and status.strip()),
        "git_status_short": status.splitlines() if rc_status == 0 and status.strip() else [],
    }


def module_gate_options(args: argparse.Namespace) -> GateOptions:
    return GateOptions(
        allow_ncm=getattr(args, "allow_ncm", False),
        allow_usb_rebind=getattr(args, "allow_usb_rebind", False),
        allow_destructive=getattr(args, "allow_destructive", False),
        assume_yes=getattr(args, "assume_yes", False),
    )


def print_module_plan(name: str, module: Any, gate: Any) -> None:
    metadata = module.metadata()
    print(f"module: {name}")
    print(f"description: {metadata.get('description')}")
    print(f"cycle_label: {metadata.get('cycle_label')}")
    print(f"read_only: {metadata.get('read_only')}")
    print(f"destructive: {metadata.get('destructive')}")
    print(f"requires_ncm: {metadata.get('requires_ncm')}")
    print(f"requires_usb_rebind: {metadata.get('requires_usb_rebind')}")
    print(f"operator_confirm_required: {metadata.get('operator_confirm_required')}")
    print(f"allowed: {gate.allowed}")
    if gate.reasons:
        print("blocked_reasons:")
        for reason in gate.reasons:
            print(f"- {reason}")
    if gate.required_flags:
        print("required_flags:")
        for flag in gate.required_flags:
            print(f"- {flag}")


def transcript_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in name)
    return f"commands/{safe}.txt"


def record_command(store: EvidenceStore,
                   client: DeviceClient,
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None) -> tuple[CommandRecord, str]:
    relative = transcript_name(name)
    record, text = client.run(name, command, timeout=timeout, transcript=str(store.path(relative)))
    store.write_text(relative, text)
    return record, text


def render_summary(result: HarnessResult, manifest: dict[str, Any]) -> str:
    lines = [
        f"# {result.label}\n\n",
        f"- result: `{'PASS' if result.ok else 'FAIL'}`\n",
        f"- run_dir: `{manifest['run_dir']}`\n",
        f"- expect_version: `{manifest['expect_version']}`\n",
        f"- version_matches: `{manifest.get('version_matches')}`\n",
        f"- failed_checks: `{len([check for check in result.checks if not check.ok])}`\n",
        f"- failed_commands: `{len([command for command in result.commands if not command.ok])}`\n\n",
        "## Checks\n\n",
    ]
    for check in result.checks:
        lines.append(f"- {'PASS' if check.ok else 'FAIL'} `{check.name}`: {check.detail}\n")
    lines.append("\n## Commands\n\n")
    for command in result.commands:
        lines.append(
            f"- {'PASS' if command.ok else 'FAIL'} `{ ' '.join(command.command) }` "
            f"rc={command.rc} status={command.status} duration={command.duration_sec:.3f}s "
            f"file=`{command.transcript}`"
        )
        if command.error:
            lines.append(f" error=`{command.error}`")
        lines.append("\n")
    return "".join(lines)


def run_smoke(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir is not None else default_run_dir("v170-smoke")
    run_dir = run_dir if run_dir.is_absolute() else REPO_ROOT / run_dir
    store = EvidenceStore(run_dir)
    store.mkdir("commands")
    client = make_device_client(args)
    started = time.monotonic()

    commands: list[CommandRecord] = []
    checks: list[CheckResult] = []

    version_record, version_text = record_command(store, client, "version", ["version"], timeout=args.timeout)
    commands.append(version_record)
    version_matches = args.expect_version in version_text
    checks.append(CheckResult("version command", version_record.ok, f"rc={version_record.rc} status={version_record.status}"))
    checks.append(CheckResult("version matches", version_matches, args.expect_version))

    status_record, status_text = record_command(store, client, "status", ["status"], timeout=args.timeout)
    commands.append(status_record)
    checks.append(CheckResult("status command", status_record.ok, f"rc={status_record.rc} status={status_record.status}"))
    checks.append(CheckResult("status has selftest", "selftest:" in status_text, "status output contains selftest summary"))

    ok = all(check.ok for check in checks) and all(command.ok for command in commands)
    result = HarnessResult("A90 v170 Harness Foundation Smoke", ok, checks, commands)
    manifest: dict[str, Any] = {
        "label": result.label,
        "pass": ok,
        "run_dir": str(run_dir),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "duration_sec": time.monotonic() - started,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "host": host_metadata(),
        "device_client": client.metadata(),
        "result": result.to_dict(),
        "policy": "host-side smoke; cmdv1 version/status only; no device mutation",
    }
    finalize_bundle(store, manifest, render_summary(result, manifest))
    print(f"{'PASS' if ok else 'FAIL'} run_dir={run_dir}")
    return 0 if ok else 1


def run_observe(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir is not None else default_run_dir("v171-observer")
    run_dir = run_dir if run_dir.is_absolute() else REPO_ROOT / run_dir
    store = EvidenceStore(run_dir)
    client = make_device_client(args)
    started = time.monotonic()

    observer_summary = run_observer(
        client,
        store,
        duration_sec=parse_duration(args.duration_sec),
        interval_sec=args.interval,
        max_cycles=args.max_cycles,
    )
    observer_text = store.path("observer.jsonl").read_text(encoding="utf-8", errors="replace")
    version_matches = args.expect_version in observer_text
    checks = [
        CheckResult("observer samples", observer_summary.samples > 0, f"samples={observer_summary.samples}"),
        CheckResult("observer failures", observer_summary.failures == 0, f"failures={observer_summary.failures}"),
        CheckResult("observer completed", not observer_summary.interrupted, f"stop_reason={observer_summary.stop_reason}"),
        CheckResult("observer version matches", version_matches, args.expect_version),
    ]
    ok = observer_summary.ok and all(check.ok for check in checks)
    result = HarnessResult("A90 v171 Observer API", ok, checks, [])
    manifest: dict[str, Any] = {
        "label": result.label,
        "pass": ok,
        "run_dir": str(run_dir),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "duration_sec": time.monotonic() - started,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "host": host_metadata(),
        "device_client": client.metadata(),
        "observer": observer_summary.to_dict(),
        "result": result.to_dict(),
        "policy": "read-only observer; no device mutation; supports bounded and unlimited duration",
    }
    finalize_bundle(store, manifest, render_summary(result, manifest))
    print(f"{'PASS' if ok else 'FAIL'} run_dir={run_dir} samples={observer_summary.samples} failures={observer_summary.failures}")
    return 0 if ok else 1


def render_module_summary(result: HarnessResult, manifest: dict[str, Any]) -> str:
    lines = [render_summary(result, manifest)]
    module = manifest.get("module", {})
    if module:
        lines.extend([
            "\n## Module\n\n",
            f"- name: `{module.get('name')}`\n",
            f"- result: `{'PASS' if module.get('ok') else 'FAIL'}`\n",
            f"- skipped: `{module.get('skipped')}`\n",
            f"- artifacts: `{len(module.get('artifacts', []))}`\n\n",
            "## Module Steps\n\n",
        ])
        for step in module.get("steps", []):
            lines.append(
                f"- {'PASS' if step.get('ok') else 'FAIL'} `{step.get('name')}`: "
                f"{step.get('detail')} duration={step.get('duration_sec', 0):.3f}s"
            )
            if step.get("error"):
                lines.append(f" error=`{step.get('error')}`")
            lines.append("\n")
        lines.append("\n## Module Artifacts\n\n")
        for artifact in module.get("artifacts", []):
            lines.append(f"- `{artifact}`\n")
    observer = manifest.get("observer")
    if observer:
        lines.extend([
            "\n## Observer\n\n",
            f"- result: `{'PASS' if observer.get('ok') else 'FAIL'}`\n",
            f"- cycles: `{observer.get('cycles')}`\n",
            f"- samples: `{observer.get('samples')}`\n",
            f"- failures: `{observer.get('failures')}`\n",
        ])
    return "".join(lines)


def render_mixed_soak_summary(result: HarnessResult, manifest: dict[str, Any]) -> str:
    lines = [render_summary(result, manifest)]
    mixed = manifest.get("mixed_soak", {})
    if mixed:
        lines.extend([
            "\n## Mixed Soak\n\n",
            f"- seed: `{mixed.get('seed')}`\n",
            f"- profile: `{mixed.get('profile')}`\n",
            f"- duration_sec: `{mixed.get('duration_sec')}`\n",
            f"- workload_count: `{mixed.get('workload_count')}`\n",
            f"- pass_count: `{mixed.get('pass_count')}`\n",
            f"- skip_count: `{mixed.get('skip_count')}`\n",
            f"- blocked_count: `{mixed.get('blocked_count')}`\n",
            f"- fail_count: `{mixed.get('fail_count')}`\n",
            f"- schedule: `{mixed.get('schedule_path')}`\n",
            f"- events: `{mixed.get('events_path')}`\n",
            f"- classification: `{mixed.get('classification_path')}`\n",
            f"- classification_summary: `{mixed.get('classification_summary')}`\n",
        ])
    schedule = manifest.get("schedule", {})
    if schedule:
        lines.extend([
            "\n## Schedule\n\n",
            f"- workload_count: `{schedule.get('workload_count')}`\n",
            f"- observer_interval_sec: `{schedule.get('observer_interval_sec')}`\n",
        ])
        for entry in schedule.get("schedule", []):
            lines.append(
                f"- `{entry.get('workload')}` phase={entry.get('phase')} "
                f"start={entry.get('start_sec')} end={entry.get('end_sec')} "
                f"locks={entry.get('resource_locks')}\n"
            )
    return "".join(lines)


def run_module(args: argparse.Namespace) -> int:
    module_cls = MODULES[args.module]
    module = module_cls()
    gate = evaluate_gate(module, module_gate_options(args))
    if args.dry_run:
        print_module_plan(args.module, module, gate)
        return 0
    if not gate.allowed:
        print_module_plan(args.module, module, gate)
        return 2
    run_dir = args.run_dir if args.run_dir is not None else default_run_dir(f"{module.cycle_label}-{module.name}")
    run_dir = run_dir if run_dir.is_absolute() else REPO_ROOT / run_dir
    store = EvidenceStore(run_dir)
    client = make_device_client(args)
    started = time.monotonic()

    runner = ModuleRunner(
        repo_root=REPO_ROOT,
        store=store,
        client=client,
        expect_version=args.expect_version,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
    )
    module_outcome, observer_summary = runner.run(
        module,
        profile=args.profile,
        observer_duration_sec=args.observer_duration_sec,
        observer_interval_sec=args.observer_interval,
    )
    observer_text = ""
    observer_path = store.path("observer.jsonl")
    if observer_path.exists():
        observer_text = observer_path.read_text(encoding="utf-8", errors="replace")
    version_matches = args.expect_version in observer_text if observer_text else None
    checks = [
        CheckResult("module result", module_outcome.ok, module.name),
        CheckResult("module skip state", True, f"skipped={module_outcome.skipped}"),
        CheckResult(
            "module steps",
            all(step.ok for step in module_outcome.steps),
            ", ".join(f"{step.name}={step.ok}" for step in module_outcome.steps),
        ),
        CheckResult("module artifacts", bool(module_outcome.artifacts), f"artifacts={len(module_outcome.artifacts)}"),
    ]
    if observer_summary is not None:
        checks.append(CheckResult("observer result", observer_summary.ok, f"failures={observer_summary.failures}"))
        checks.append(CheckResult("observer samples", observer_summary.samples > 0, f"samples={observer_summary.samples}"))
    ok = all(check.ok for check in checks) and module_outcome.ok
    result = HarnessResult(f"A90 v172 Module Runner: {module.name}", ok, checks, [])
    manifest: dict[str, Any] = {
        "label": result.label,
        "pass": ok,
        "run_dir": str(run_dir),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "duration_sec": time.monotonic() - started,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "host": host_metadata(),
        "device_client": client.metadata(),
        "module": module_outcome.to_dict(),
        "gate": gate.to_dict(),
        "observer": observer_summary.to_dict() if observer_summary is not None else None,
        "result": result.to_dict(),
        "policy": "module runner; cleanup and verify always attempted; first module is read-only",
    }
    finalize_bundle(store, manifest, render_module_summary(result, manifest))
    print(
        f"{'PASS' if ok else 'FAIL'} run_dir={run_dir} "
        f"module={module.name} observer_failures={observer_summary.failures if observer_summary else 'n/a'}"
    )
    return 0 if ok else 1


def run_mixed_soak(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir is not None else default_run_dir("v179-mixed-soak")
    run_dir = run_dir if run_dir.is_absolute() else REPO_ROOT / run_dir
    store = EvidenceStore(run_dir)
    client = make_device_client(args)
    started = time.monotonic()

    seed = args.seed
    if seed is None:
        seed = int(time.time())
    duration_sec = float(args.duration_sec)
    if duration_sec <= 0:
        raise RuntimeError("duration-sec must be positive")
    schedule = build_schedule(
        modules=MODULES,
        workloads=args.workload,
        profile=args.profile,
        duration_sec=duration_sec,
        seed=seed,
    )
    schedule_payload = schedule_document(
        schedule,
        seed=seed,
        profile=args.profile,
        duration_sec=duration_sec,
        observer_interval_sec=args.observer_interval,
    )
    store.write_json("schedule.json", schedule_payload)

    gates = {
        entry.workload: evaluate_gate(MODULES[entry.workload](), module_gate_options(args)).to_dict()
        for entry in schedule
    }
    if args.dry_run:
        dry_run_payload = {
            "label": "A90 v179 Mixed Soak Scheduler Foundation dry-run",
            "pass": True,
            "run_dir": str(run_dir),
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "expect_version": args.expect_version,
            "schedule": schedule_payload,
            "gates": gates,
            "policy": "dry-run only; no device commands; schedule and gate plan only",
        }
        store.write_json("mixed-soak-dry-run.json", dry_run_payload)
        finalize_bundle(store, dry_run_payload, "# A90 v179 Mixed Soak Dry Run\n\n- result: `PASS`\n")
        print(f"PASS dry-run run_dir={run_dir} workloads={len(schedule)} seed={seed}")
        return 0

    mixed = run_mixed_soak_schedule(
        repo_root=REPO_ROOT,
        store=store,
        client=client,
        modules=MODULES,
        schedule=schedule,
        gate_options=module_gate_options(args),
        expect_version=args.expect_version,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        duration_sec=duration_sec,
        observer_interval_sec=args.observer_interval,
        workload_profile=args.workload_profile,
        stop_on_failure=args.stop_on_failure,
    )
    checks = [
        CheckResult("schedule generated", bool(schedule_payload.get("schedule")) or args.profile == "idle",
                    f"workloads={len(schedule)} seed={seed}"),
        CheckResult("workload failures", mixed.fail_count == 0, f"failures={mixed.fail_count}"),
        CheckResult("observer result", mixed.observer is not None and mixed.observer.ok,
                    f"failures={mixed.observer.failures if mixed.observer else 'missing'}"),
        CheckResult("schedule artifact", store.path("schedule.json").exists(), "schedule.json"),
        CheckResult("workload event artifact", store.path("workload-events.jsonl").exists() or not schedule,
                    "workload-events.jsonl"),
        CheckResult("classification artifact", store.path("failure-classification.json").exists(),
                    "failure-classification.json"),
    ]
    ok = mixed.ok and all(check.ok for check in checks)
    result = HarnessResult("A90 v179 Mixed Soak Scheduler Foundation", ok, checks, [])
    manifest: dict[str, Any] = {
        "label": result.label,
        "pass": ok,
        "run_dir": str(run_dir),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "duration_sec": time.monotonic() - started,
        "expect_version": args.expect_version,
        "host": host_metadata(),
        "device_client": client.metadata(),
        "schedule": schedule_payload,
        "gates": gates,
        "mixed_soak": mixed.to_dict(),
        "result": result.to_dict(),
        "policy": "mixed-soak scheduler; observer runs concurrently; blocked unsafe modules are structured skips",
    }
    finalize_bundle(store, manifest, render_mixed_soak_summary(result, manifest))
    print(
        f"{'PASS' if ok else 'FAIL'} run_dir={run_dir} workloads={mixed.workload_count} "
        f"pass={mixed.pass_count} skipped={mixed.skip_count} blocked={mixed.blocked_count} "
        f"observer_failures={mixed.observer.failures if mixed.observer else 'missing'}"
    )
    return 0 if ok else 1


def run_list(args: argparse.Namespace) -> int:
    options = module_gate_options(args)
    for name in sorted(MODULES):
        module = MODULES[name]()
        gate = evaluate_gate(module, options)
        required = ",".join(gate.required_flags) if gate.required_flags else "-"
        print(
            f"{name}\tallowed={gate.allowed}\tread_only={module.read_only}\t"
            f"requires_ncm={module.requires_ncm}\trequires_usb_rebind={module.requires_usb_rebind}\t"
            f"required_flags={required}"
        )
    return 0


def run_plan(args: argparse.Namespace) -> int:
    module = MODULES[args.module]()
    gate = evaluate_gate(module, module_gate_options(args))
    print_module_plan(args.module, module, gate)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument(
        "--device-backend",
        choices=("direct", "broker"),
        default="direct",
        help="device command backend: direct cmdv1 bridge or A90B1 broker",
    )
    parser.add_argument("--broker-runtime-dir", type=Path, default=DEFAULT_BROKER_RUNTIME_DIR)
    parser.add_argument("--broker-socket-name", default=DEFAULT_BROKER_SOCKET_NAME)
    parser.add_argument("--broker-socket", type=Path)
    parser.add_argument("--broker-client-id", default=f"supervisor:{os.getpid()}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list validation modules and gate state")
    list_parser.add_argument("--allow-ncm", action="store_true")
    list_parser.add_argument("--allow-usb-rebind", action="store_true")
    list_parser.add_argument("--allow-destructive", action="store_true")
    list_parser.add_argument("--assume-yes", action="store_true")

    plan = subparsers.add_parser("plan", help="show one module plan and gate requirements")
    plan.add_argument("module", choices=sorted(MODULES))
    plan.add_argument("--allow-ncm", action="store_true")
    plan.add_argument("--allow-usb-rebind", action="store_true")
    plan.add_argument("--allow-destructive", action="store_true")
    plan.add_argument("--assume-yes", action="store_true")

    smoke = subparsers.add_parser("smoke", help="run v170 harness foundation smoke check")
    smoke.add_argument("--run-dir", type=Path)

    observe = subparsers.add_parser("observe", help="run v171 read-only observer")
    observe.add_argument("--run-dir", type=Path)
    observe.add_argument("--duration-sec", default="60.0")
    observe.add_argument("--interval", type=float, default=10.0)
    observe.add_argument("--max-cycles", type=int)

    run = subparsers.add_parser("run", help="run a v172 validation module")
    run.add_argument("module", choices=sorted(MODULES))
    run.add_argument("--profile", choices=("smoke", "quick"), default="smoke")
    run.add_argument("--run-dir", type=Path)
    run.add_argument("--observer-duration-sec", type=float, default=0.0)
    run.add_argument("--observer-interval", type=float, default=5.0)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--allow-ncm", action="store_true")
    run.add_argument("--allow-usb-rebind", action="store_true")
    run.add_argument("--allow-destructive", action="store_true")
    run.add_argument("--assume-yes", action="store_true")

    mixed = subparsers.add_parser("mixed-soak", help="run v179 mixed-soak scheduler foundation")
    mixed.add_argument("--run-dir", type=Path)
    mixed.add_argument("--duration-sec", type=float, default=120.0)
    mixed.add_argument("--observer-interval", type=float, default=15.0)
    mixed.add_argument("--profile", choices=("idle", "smoke", "balanced"), default="smoke")
    mixed.add_argument("--workload-profile", choices=("smoke", "quick"), default="smoke")
    mixed.add_argument("--workload", action="append", choices=sorted(MODULES), default=[])
    mixed.add_argument("--seed", type=int)
    mixed.add_argument("--dry-run", action="store_true")
    mixed.add_argument("--allow-ncm", action="store_true")
    mixed.add_argument("--allow-usb-rebind", action="store_true")
    mixed.add_argument("--allow-destructive", action="store_true")
    mixed.add_argument("--assume-yes", action="store_true")
    mixed.add_argument("--stop-on-failure", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "list":
        return run_list(args)
    if args.command == "plan":
        return run_plan(args)
    if args.command == "smoke":
        return run_smoke(args)
    if args.command == "observe":
        return run_observe(args)
    if args.command == "run":
        return run_module(args)
    if args.command == "mixed-soak":
        return run_mixed_soak(args)
    raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
