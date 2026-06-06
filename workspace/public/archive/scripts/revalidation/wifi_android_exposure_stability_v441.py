#!/usr/bin/env python3
"""V441 Android Wi-Fi exposure-aware stability orchestrator.

V441 is a bounded end-to-end Wi-Fi stability cycle:

1. use the proven V438 handoff to enable Android framework Wi-Fi;
2. use the proven V439 handoff to observe Android-managed auto-connect for a
   longer window;
3. run cleanup disable through V439;
4. restore native v319 through both handoffs.

This script is an orchestrator.  It does not introduce scan/connect,
credentials, external probes, server exposure, route mutation, sysfs/rfkill
writes, module operations, setprop, or direct daemon starts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_control_gate_v432 import display_command, redact_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v441-android-wifi-exposure-stability")


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    skipped: bool
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--sample-duration", type=float, default=300.0)
    parser.add_argument("--sample-interval", type=float, default=30.0)
    parser.add_argument("--enable-settle-sleep", type=float, default=35.0)
    parser.add_argument("--cleanup-settle-sleep", type=float, default=25.0)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--allow-wifi-enable", action="store_true")
    parser.add_argument("--i-understand-android-wifi-setting-mutation", action="store_true")
    parser.add_argument("--allow-wifi-disable-cleanup", action="store_true")
    parser.add_argument("--i-understand-android-wifi-cleanup-mutation", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for attr, flag in (
        ("allow_android_boot_flash", "--allow-android-boot-flash"),
        ("assume_yes", "--assume-yes"),
        ("i_understand_native_rollback", "--i-understand-native-rollback"),
        ("allow_wifi_enable", "--allow-wifi-enable"),
        ("i_understand_android_wifi_setting_mutation", "--i-understand-android-wifi-setting-mutation"),
        ("allow_wifi_disable_cleanup", "--allow-wifi-disable-cleanup"),
        ("i_understand_android_wifi_cleanup_mutation", "--i-understand-android-wifi-cleanup-mutation"),
    ):
        if not getattr(args, attr):
            missing.append(flag)
    return not missing, missing


def v438_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v438-enable-handoff"


def v439_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v439-stability-handoff"


def base_handoff_flags(args: argparse.Namespace) -> list[str]:
    flags = [
        "--adb",
        args.adb,
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
    ]
    if args.serial:
        flags.extend(["--serial", args.serial])
    if args.allow_android_boot_flash:
        flags.append("--allow-android-boot-flash")
    if args.assume_yes:
        flags.append("--assume-yes")
    if args.i_understand_native_rollback:
        flags.append("--i-understand-native-rollback")
    return flags


def build_steps(args: argparse.Namespace, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    mode = "run" if args.command == "run" else args.command
    v438_command = [
        "python3",
        "scripts/revalidation/android_wifi_reenable_observation_handoff_v438.py",
        "--out-dir",
        str(v438_dir(store)),
        *base_handoff_flags(args),
        "--enable-settle-sleep",
        str(max(0.0, args.enable_settle_sleep)),
    ]
    if args.allow_wifi_enable:
        v438_command.append("--allow-wifi-enable")
    if args.i_understand_android_wifi_setting_mutation:
        v438_command.append("--i-understand-android-wifi-setting-mutation")
    v438_command.append(mode)

    v439_command = [
        "python3",
        "scripts/revalidation/android_wifi_post_reenable_handoff_v439.py",
        "--out-dir",
        str(v439_dir(store)),
        *base_handoff_flags(args),
        "--sample-duration",
        str(max(0.0, args.sample_duration)),
        "--sample-interval",
        str(max(1.0, args.sample_interval)),
        "--cleanup-settle-sleep",
        str(max(0.0, args.cleanup_settle_sleep)),
        "--cleanup-disable",
    ]
    if args.allow_wifi_disable_cleanup:
        v439_command.append("--allow-wifi-disable-cleanup")
    if args.i_understand_android_wifi_cleanup_mutation:
        v439_command.append("--i-understand-android-wifi-cleanup-mutation")
    v439_command.append(mode)
    v438_timeout = max(900, int(args.enable_settle_sleep + 900))
    v439_timeout = max(900, int(args.sample_duration + args.cleanup_settle_sleep + 900))
    return [
        ("v438-enable-handoff", v438_command, v438_timeout),
        ("v439-stability-cleanup-handoff", v439_command, v439_timeout),
    ]


def write_step(store: EvidenceStore, name: str, command: list[str], text: str, error: str, rc: int | None, duration: float, skipped: bool) -> StepResult:
    body = "\n".join(
        [
            f"$ {display_command(command)}",
            redact_text(text if text else error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"steps/{name}.txt", body)
    return StepResult(
        name=name,
        command=display_command(command),
        ok=(rc == 0) if not skipped else True,
        rc=rc,
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        skipped=skipped,
        error=redact_text(error),
    )


def execute_step(store: EvidenceStore, name: str, command: list[str], timeout: int, execute: bool) -> StepResult:
    if not execute:
        return write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return write_step(store, name, command, result.stdout, "", result.returncode, time.monotonic() - started, skipped=False)
    except FileNotFoundError as exc:
        return write_step(store, name, command, "", str(exc), None, time.monotonic() - started, skipped=False)
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return write_step(store, name, command, text, f"timeout after {timeout}s", None, time.monotonic() - started, skipped=False)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path), "pass": False, "decision": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["_path"] = str(path)
    return payload


def exposure_seen(sample: dict[str, Any]) -> bool:
    return any(
        bool(sample.get(key))
        for key in (
            "wifi_connected",
            "wlan0_has_ip",
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
        )
    )


def load_nested_results(store: EvidenceStore) -> dict[str, Any]:
    v438 = load_json(v438_dir(store) / "manifest.json")
    v439 = load_json(v439_dir(store) / "manifest.json")
    v438_collector = load_json(v438_dir(store) / "v438-android-wifi-reenable-observation-run" / "manifest.json")
    v439_collector = load_json(v439_dir(store) / "v439-android-wifi-post-reenable-observation-run" / "manifest.json")
    return {
        "v438": v438,
        "v439": v439,
        "v438_collector": v438_collector,
        "v439_collector": v439_collector,
    }


def classify(nested: dict[str, Any], steps: list[StepResult], executed: bool) -> dict[str, Any]:
    if not executed:
        return {
            "decision": "v441-android-wifi-exposure-stability-plan-ready",
            "pass": True,
            "reason": "V441 exposure-aware stability orchestration plan generated",
            "next_gate": "run V441 live when ready",
            "sample_summary": {},
            "stable_all_samples": None,
            "cleanup_contained": None,
            "listener_safe": None,
        }

    if not all(step.ok for step in steps):
        failed = next((step.name for step in steps if not step.ok), "unknown")
        return {
            "decision": f"v441-android-wifi-exposure-stability-failed-{failed}",
            "pass": False,
            "reason": f"orchestration step failed: {failed}",
            "next_gate": "inspect nested handoff output before retry",
            "sample_summary": {},
            "stable_all_samples": None,
            "cleanup_contained": None,
            "listener_safe": None,
        }

    v438 = nested["v438"]
    v439 = nested["v439"]
    v439_collector = nested["v439_collector"]
    classification = v439_collector.get("classification") or {}
    samples = classification.get("samples") or []
    summary = classification.get("sample_summary") or {}
    cleanup_state = classification.get("cleanup_state") or {}
    cleanup_ok = classification.get("cleanup_ok")
    cleanup_contained = bool(classification.get("cleanup_contained"))
    listener_safe = bool(summary.get("listener_safe"))
    exposure_sample_count = sum(1 for sample in samples if exposure_seen(sample))
    stable_all_samples = bool(samples) and exposure_sample_count == len(samples)
    if not v438.get("pass"):
        decision = "v441-android-wifi-exposure-stability-enable-failed"
        pass_ok = False
        reason = "V438 controlled enable handoff did not pass"
        next_gate = "review V438 nested evidence before retry"
    elif not v439.get("pass"):
        decision = "v441-android-wifi-exposure-stability-observation-failed"
        pass_ok = False
        reason = "V439 stability/cleanup handoff did not pass"
        next_gate = "review V439 nested evidence before retry"
    elif not listener_safe:
        decision = "v441-android-wifi-exposure-stability-listener-observed"
        pass_ok = False
        reason = "global listener surface was observed during Wi-Fi exposure window"
        next_gate = "block server work and inspect listener owner"
    elif not cleanup_contained:
        decision = "v441-android-wifi-exposure-stability-cleanup-not-contained"
        pass_ok = False
        reason = "cleanup containment was not proven after Wi-Fi exposure observation"
        next_gate = "rerun cleanup containment before more Wi-Fi work"
    elif stable_all_samples:
        decision = "v441-android-wifi-exposure-stability-cleanup-pass"
        pass_ok = True
        reason = "Android-managed Wi-Fi stayed connected/exposed across all samples and cleanup containment passed"
        next_gate = "V442 credential/target allowlist design or longer exposure-aware stability run"
    elif summary.get("exposure_seen"):
        decision = "v441-android-wifi-exposure-flap-cleanup-pass"
        pass_ok = True
        reason = "Android-managed Wi-Fi exposure was observed but not stable across all samples; cleanup containment passed"
        next_gate = "repeat longer stability run before explicit scan/connect"
    else:
        decision = "v441-android-wifi-no-exposure-cleanup-pass"
        pass_ok = True
        reason = "Android Wi-Fi enable path ran, but route/DNS/connectivity exposure was not observed in V441"
        next_gate = "repeat controlled Wi-Fi stability observation before scan/connect"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "sample_summary": summary,
        "sample_count": len(samples),
        "exposure_sample_count": exposure_sample_count,
        "stable_all_samples": stable_all_samples,
        "cleanup_ok": cleanup_ok,
        "cleanup_state": cleanup_state,
        "cleanup_contained": cleanup_contained,
        "listener_safe": listener_safe,
        "v438_decision": v438.get("decision"),
        "v439_decision": v439.get("decision"),
    }


def guardrails() -> list[str]:
    return [
        "orchestrates proven V438 enable and V439 observation/cleanup handoffs",
        "no explicit scan/connect, credentials, external packet probes, server exposure, or new listeners",
        "no DHCP/routing mutation, rfkill/sysfs write, module operation, setprop, or direct daemon start",
        "native v319 rollback is required after each nested handoff",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [
            item["name"],
            "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
            str(item["rc"]),
            f"{item['duration_sec']:.3f}s",
            item["file"],
        ]
        for item in manifest["steps"]
    ]
    classification = manifest["classification"]
    summary_rows = [[key, str(value)] for key, value in (classification.get("sample_summary") or {}).items()]
    result_rows = [
        ["sample_count", classification.get("sample_count", "-")],
        ["exposure_sample_count", classification.get("exposure_sample_count", "-")],
        ["stable_all_samples", classification.get("stable_all_samples", "-")],
        ["cleanup_ok", classification.get("cleanup_ok", "-")],
        ["cleanup_contained", classification.get("cleanup_contained", "-")],
        ["listener_safe", classification.get("listener_safe", "-")],
        ["v438_decision", classification.get("v438_decision", "-")],
        ["v439_decision", classification.get("v439_decision", "-")],
    ]
    return "\n".join(
        [
            "# V441 Android Wi-Fi Exposure-aware Stability",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- approval_ok: `{manifest['approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['missing_approval_flags']) or '-'}`",
            f"- sample_duration: `{manifest['sample_duration']}`",
            f"- sample_interval: `{manifest['sample_interval']}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_enable_executed: `{manifest['wifi_enable_executed']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Result",
            "",
            markdown_table(["item", "value"], [[str(a), str(b)] for a, b in result_rows]),
            "",
            "## Sample Summary",
            "",
            markdown_table(["item", "value"], summary_rows if summary_rows else [["-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    approval, missing = approval_ok(args)
    steps: list[StepResult] = []
    if args.command == "run" and not approval:
        classification = {
            "decision": "v441-android-wifi-exposure-stability-approval-required",
            "pass": False,
            "reason": "approval flags for Android boot, Wi-Fi enable, cleanup disable, and native rollback are missing",
            "next_gate": "rerun with explicit approval flags",
            "sample_summary": {},
            "stable_all_samples": None,
            "cleanup_contained": None,
            "listener_safe": None,
        }
        nested: dict[str, Any] = {}
    else:
        execute = args.command in {"dry-run", "run"}
        for name, command, timeout in build_steps(args, store):
            step = execute_step(store, name, command, timeout, execute=execute)
            steps.append(step)
            if args.command == "run" and not step.ok:
                break
        nested = load_nested_results(store) if args.command == "run" else {}
        if args.command == "dry-run":
            classification = {
                "decision": "v441-android-wifi-exposure-stability-dryrun-ready",
                "pass": all(step.ok for step in steps),
                "reason": "nested V438/V439 dry-runs completed without device mutation",
                "next_gate": "run V441 live when ready",
                "sample_summary": {},
                "stable_all_samples": None,
                "cleanup_contained": None,
                "listener_safe": None,
            }
        else:
            classification = classify(nested, steps, executed=execute)

    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "approval_ok": approval,
        "missing_approval_flags": missing,
        "sample_duration": max(0.0, args.sample_duration),
        "sample_interval": max(1.0, args.sample_interval),
        "enable_settle_sleep": max(0.0, args.enable_settle_sleep),
        "cleanup_settle_sleep": max(0.0, args.cleanup_settle_sleep),
        "classification": classification,
        "nested": nested,
        "steps": [asdict(step) for step in steps],
        "guardrails": guardrails(),
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run" and bool(steps),
        "wifi_enable_executed": args.command == "run" and bool(nested.get("v438", {}).get("wifi_enable_executed")),
        "wifi_disable_executed": args.command == "run" and bool(nested.get("v439", {}).get("wifi_disable_executed")),
        "wifi_bringup_executed": args.command == "run" and bool(nested.get("v438", {}).get("wifi_bringup_executed")),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_enable_executed: {manifest['wifi_enable_executed']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
