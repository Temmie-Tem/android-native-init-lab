#!/usr/bin/env python3
"""Postprocess Android property capture handoff artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v303-android-capture-postprocess")
DEFAULT_V300_LIVE = Path("tmp/wifi/v300-android-capture-executor-live/manifest.json")
DEFAULT_V295_MANIFEST = Path("tmp/wifi/v295-property-snapshot-live-20260519-142740/manifest.json")
DEFAULT_V297_MANIFEST = Path("tmp/wifi/v297-android-property-capture-android/manifest.json")
DEFAULT_V298_MANIFEST = Path("tmp/wifi/v298-property-baseline-compare-android/manifest.json")
DEFAULT_V301_OUT_DIR = Path("tmp/wifi/v301-property-shim-seed-android")


@dataclass
class CommandResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v300-live-manifest", type=Path, default=DEFAULT_V300_LIVE)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295_MANIFEST)
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297_MANIFEST)
    parser.add_argument("--v298-manifest", type=Path, default=DEFAULT_V298_MANIFEST)
    parser.add_argument("--v301-out-dir", type=Path, default=DEFAULT_V301_OUT_DIR)
    parser.add_argument("--timeout", type=int, default=30)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def manifest_decision(manifest: dict[str, Any]) -> str:
    return str(manifest.get("decision", "missing"))


def manifest_pass(manifest: dict[str, Any]) -> bool:
    return bool(manifest.get("pass"))


def step_ok(manifest: dict[str, Any], name: str) -> bool:
    for step in manifest.get("steps", []):
        if isinstance(step, dict) and step.get("name") == name:
            return bool(step.get("ok"))
    return False


def display_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
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
        return result.returncode, result.stdout, "", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - postprocess evidence preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def run_seed(store: EvidenceStore, args: argparse.Namespace) -> CommandResult:
    command = [
        "python3",
        "scripts/revalidation/wifi_property_shim_seed.py",
        "--out-dir",
        str(args.v301_out_dir),
        "--v295-manifest",
        str(args.v295_manifest),
        "--v297-manifest",
        str(args.v297_manifest),
        "--v298-manifest",
        str(args.v298_manifest),
        "run",
    ]
    rc, text, error, duration = run_process(command, args.timeout)
    body = "\n".join([f"$ {display_command(command)}", text.rstrip() if text else error.rstrip(), f"rc={rc}", ""])
    path = store.write_text("commands/run-v301-seed.txt", body)
    return CommandResult("run-v301-seed", display_command(command), rc == 0, rc, duration, str(path.relative_to(store.run_dir)), error)


def seed_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return load_manifest(args.v301_out_dir / "manifest.json")


def decide(v300: dict[str, Any],
           v297: dict[str, Any],
           v298: dict[str, Any],
           v301: dict[str, Any],
           command_results: list[CommandResult]) -> tuple[str, bool, str, str]:
    if not v300.get("present"):
        return "android-capture-postprocess-waiting-for-live", True, "v300 live handoff manifest is missing", "request explicit operator approval for v300 live handoff"
    if manifest_decision(v300) != "android-capture-executor-pass" or not manifest_pass(v300):
        return "android-capture-postprocess-live-failed", False, f"v300 decision is {manifest_decision(v300)}", "inspect v300 live steps and restore native before continuing"
    if not step_ok(v300, "restore-native"):
        return "android-capture-postprocess-live-failed", False, "v300 restore-native step is not confirmed ok", "do not continue Wi-Fi work until native rollback is verified"
    if not v297.get("present") or not v298.get("present"):
        return "android-capture-postprocess-waiting-for-capture", True, "v297/v298 Android property artifacts are missing", "rerun v297 capture and v298 compare after Android handoff"
    if manifest_decision(v297) != "android-property-capture-pass" or manifest_decision(v298) != "property-baseline-compare-ready":
        return "android-capture-postprocess-waiting-for-capture", True, f"input decisions are v297={manifest_decision(v297)} v298={manifest_decision(v298)}", "inspect missing Android property keys before shim planning"
    if command_results and not all(result.ok for result in command_results):
        return "android-capture-postprocess-seed-blocked", False, "v301 seed command failed", "inspect command transcript"
    if not v301.get("present"):
        return "android-capture-postprocess-waiting-for-seed", True, "v301 Android-backed seed manifest is missing", "run this tool with command run"
    if manifest_decision(v301) == "property-shim-seed-ready" and manifest_pass(v301):
        return "android-capture-postprocess-seed-ready", True, "Android-backed property shim seed is ready", "review seed model before designing any runtime property shim"
    return "android-capture-postprocess-seed-blocked", False, f"v301 decision is {manifest_decision(v301)}", "inspect blocked seed keys"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v300 = load_manifest(args.v300_live_manifest)
    v295 = load_manifest(args.v295_manifest)
    v297 = load_manifest(args.v297_manifest)
    v298 = load_manifest(args.v298_manifest)
    command_results: list[CommandResult] = []

    seed = seed_manifest(args)
    if args.command == "run" and manifest_decision(v297) == "android-property-capture-pass" and manifest_decision(v298) == "property-baseline-compare-ready":
        command_results.append(run_seed(store, args))
        seed = seed_manifest(args)

    decision, pass_ok, reason, next_step = decide(v300, v297, v298, seed, command_results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v300_live": {"path": v300.get("path"), "present": bool(v300.get("present")), "decision": v300.get("decision"), "pass": v300.get("pass")},
            "v295": {"path": v295.get("path"), "present": bool(v295.get("present")), "decision": v295.get("decision"), "pass": v295.get("pass")},
            "v297": {"path": v297.get("path"), "present": bool(v297.get("present")), "decision": v297.get("decision"), "pass": v297.get("pass")},
            "v298": {"path": v298.get("path"), "present": bool(v298.get("present")), "decision": v298.get("decision"), "pass": v298.get("pass")},
            "v301_seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "decision": seed.get("decision"), "pass": seed.get("pass")},
        },
        "live_step_checks": {
            "capture_android_property": step_ok(v300, "capture-android-property") if v300.get("present") else False,
            "compare_property_baseline": step_ok(v300, "compare-property-baseline") if v300.get("present") else False,
            "restore_native": step_ok(v300, "restore-native") if v300.get("present") else False,
        },
        "command_results": [asdict(result) for result in command_results],
        "blocked_actions": [
            "execute v300 live handoff",
            "run adb command",
            "reboot/recovery/flash",
            "create /dev/__properties__ or property_service socket",
            "start service-manager/HAL/Wi-Fi daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    input_rows = [
        [name, str(item["present"]), str(item["decision"]), str(item["pass"]), str(item["path"])]
        for name, item in manifest["inputs"].items()
    ]
    step_rows = [[name, str(ok)] for name, ok in manifest["live_step_checks"].items()]
    command_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in manifest["command_results"]
    ]
    return "\n".join(
        [
            "# v303 Android Capture Postprocess",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "present", "decision", "pass", "path"], input_rows),
            "",
            "## Live Step Checks",
            "",
            markdown_table(["step", "ok"], step_rows),
            "",
            "## Command Results",
            "",
            markdown_table(["command", "status", "rc", "duration", "file"], command_rows if command_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Blocked Actions",
            "",
            *[f"- {item}" for item in manifest["blocked_actions"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
