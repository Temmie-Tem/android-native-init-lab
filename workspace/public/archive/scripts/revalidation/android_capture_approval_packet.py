#!/usr/bin/env python3
"""Generate the final approval packet for Android property capture handoff."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v302-android-capture-approval-packet")
DEFAULT_V299_MANIFEST = Path("tmp/wifi/v299-android-capture-handoff-preflight/manifest.json")
DEFAULT_V300_DRYRUN = Path("tmp/wifi/v300-android-capture-executor-dryrun/manifest.json")
DEFAULT_V300_REFUSE = Path("tmp/wifi/v300-android-capture-executor-refuse/manifest.json")
DEFAULT_V300_TARGET_AUDIT = Path("tmp/wifi/v300-android-capture-executor-dryrun-target-audit/manifest.json")
EXPECTED_NATIVE_VERSION = "A90 Linux init 0.9.60 (v261)"
LIVE_COMMAND = (
    "python3 scripts/revalidation/android_capture_handoff_execute.py "
    "--out-dir tmp/wifi/v300-android-capture-executor-live "
    "--allow-android-boot-flash "
    "--assume-yes "
    "--i-understand-native-rollback "
    "run"
)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str


@dataclass
class CommandCapture:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v299-manifest", type=Path, default=DEFAULT_V299_MANIFEST)
    parser.add_argument("--v300-dryrun-manifest", type=Path, default=DEFAULT_V300_DRYRUN)
    parser.add_argument("--v300-refuse-manifest", type=Path, default=DEFAULT_V300_REFUSE)
    parser.add_argument("--v300-target-audit-manifest", type=Path, default=DEFAULT_V300_TARGET_AUDIT)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--no-live-native-check", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
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
    except Exception as exc:  # noqa: BLE001 - approval packet preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CommandCapture:
    rc, text, error, duration = run_process(command, timeout)
    body = "\n".join([f"$ {display_command(command)}", text.rstrip() if text else error.rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"commands/{name}.txt", body)
    return CommandCapture(name, display_command(command), rc == 0, rc, duration, str(path.relative_to(store.run_dir)), text[:4096], error)


def current_native_checks(store: EvidenceStore, timeout: int, skip: bool) -> list[CommandCapture]:
    if skip:
        return []
    return [
        capture_command(store, "native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], timeout),
        capture_command(store, "native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], timeout),
    ]


def manifest_decision(manifest: dict[str, Any]) -> str:
    return str(manifest.get("decision", "missing"))


def step_command(manifest: dict[str, Any], name: str) -> str:
    for step in manifest.get("steps", []):
        if isinstance(step, dict) and step.get("name") == name:
            return str(step.get("command", ""))
    return ""


def build_checks(v299: dict[str, Any],
                 v300_dryrun: dict[str, Any],
                 v300_refuse: dict[str, Any],
                 v300_target_audit: dict[str, Any],
                 captures: list[CommandCapture]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(
        "v299-handoff-preflight",
        "pass" if v299.get("present") and manifest_decision(v299) == "android-capture-handoff-ready-needs-operator" else "fail",
        "blocker",
        f"decision={manifest_decision(v299)}",
    ))
    checks.append(Check(
        "v300-dryrun",
        "pass" if v300_dryrun.get("present") and manifest_decision(v300_dryrun) == "android-capture-executor-dryrun-ready" and len(v300_dryrun.get("steps", [])) >= 12 else "fail",
        "blocker",
        f"decision={manifest_decision(v300_dryrun)} steps={len(v300_dryrun.get('steps', [])) if isinstance(v300_dryrun.get('steps'), list) else 0}",
    ))
    checks.append(Check(
        "v300-approval-refusal",
        "pass" if v300_refuse.get("present") and manifest_decision(v300_refuse) == "android-capture-executor-approval-required" and not bool(v300_refuse.get("pass")) else "fail",
        "blocker",
        f"decision={manifest_decision(v300_refuse)} pass={v300_refuse.get('pass')}",
    ))
    capture_command = step_command(v300_target_audit, "capture-android-property")
    restore_command = step_command(v300_target_audit, "restore-native")
    target_audit_ok = (
        v300_target_audit.get("present")
        and manifest_decision(v300_target_audit) == "android-capture-executor-dryrun-ready"
        and "--adb adb" in capture_command
        and "--serial TESTSER" in capture_command
        and "--adb adb" in restore_command
        and "--serial TESTSER" in restore_command
    )
    checks.append(Check(
        "v300-target-propagation",
        "pass" if target_audit_ok else "fail",
        "blocker",
        f"decision={manifest_decision(v300_target_audit)} capture_target={'--serial TESTSER' in capture_command} restore_target={'--serial TESTSER' in restore_command}",
    ))
    if captures:
        version_ok = any(
            capture.ok and capture.name == "native-version" and EXPECTED_NATIVE_VERSION in capture.text
            for capture in captures
        )
        status_ok = any(
            capture.ok and capture.name == "native-status" and "init: A90 Linux init" in capture.text
            for capture in captures
        )
        checks.append(Check(
            "current-native-control",
            "pass" if version_ok and status_ok else "fail",
            "blocker",
            f"version_ok={version_ok} status_ok={status_ok}",
        ))
    else:
        checks.append(Check(
            "current-native-control",
            "skipped",
            "warning",
            "live native check skipped by operator flag",
        ))
    checks.append(Check(
        "approval-command",
        "pass",
        "info",
        "live command requires three explicit approval flags",
    ))
    return checks


def decide(checks: list[Check]) -> tuple[str, bool, str]:
    blockers = [check for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "android-capture-approval-stale-or-blocked", False, "blocked checks: " + ", ".join(check.name for check in blockers)
    return "android-capture-approval-ready", True, "all approval prerequisites are present; live execution still requires explicit operator command"


def render_packet(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    image = manifest["recommended_android_boot_image"] or {}
    native = manifest["native_rollback_image"] or {}
    return "\n".join(
        [
            "# Android Property Capture Approval Packet",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            "",
            "## Live Command",
            "",
            "```bash",
            manifest["live_command"],
            "```",
            "",
            "## Images",
            "",
            markdown_table(
                ["role", "path", "sha256 prefix"],
                [
                    ["android", str(image.get("path", "-")), str(image.get("sha256", ""))[:16]],
                    ["native rollback", str(native.get("path", "-")), str(native.get("sha256", ""))[:16]],
                ],
            ),
            "",
            "## Checks",
            "",
            markdown_table(["check", "status", "severity", "detail"], check_rows),
            "",
            "## Abort Conditions",
            "",
            "- ADB recovery state does not appear after native `recovery` request.",
            "- Remote Android boot image SHA-256 differs from local candidate.",
            "- Boot partition readback SHA-256 differs from local candidate.",
            "- Android ADB does not reach `device` state.",
            "- v297 capture does not produce `android-property-capture-pass`.",
            "- v298 compare does not produce `property-baseline-compare-ready`.",
            "- Native rollback restore does not verify `A90 Linux init 0.9.60 (v261)`.",
            "",
            "## Expected Artifacts",
            "",
            "- `tmp/wifi/v300-android-capture-executor-live/`",
            "- `tmp/wifi/v297-android-property-capture-android/`",
            "- `tmp/wifi/v298-property-baseline-compare-android/`",
            "- follow-up v301 Android-backed seed run",
            "",
            "## Safety Boundary",
            "",
            "- This packet does not execute the live command.",
            "- The live command writes the boot partition and must be operator-approved.",
            "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v299 = load_manifest(args.v299_manifest)
    v300_dryrun = load_manifest(args.v300_dryrun_manifest)
    v300_refuse = load_manifest(args.v300_refuse_manifest)
    v300_target_audit = load_manifest(args.v300_target_audit_manifest)
    captures = current_native_checks(store, args.timeout, args.no_live_native_check)
    checks = build_checks(v299, v300_dryrun, v300_refuse, v300_target_audit, captures)
    decision, pass_ok, reason = decide(checks)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "v299": {"path": v299.get("path"), "present": bool(v299.get("present")), "decision": v299.get("decision")},
            "v300_dryrun": {"path": v300_dryrun.get("path"), "present": bool(v300_dryrun.get("present")), "decision": v300_dryrun.get("decision")},
            "v300_refuse": {"path": v300_refuse.get("path"), "present": bool(v300_refuse.get("present")), "decision": v300_refuse.get("decision")},
            "v300_target_audit": {
                "path": v300_target_audit.get("path"),
                "present": bool(v300_target_audit.get("present")),
                "decision": v300_target_audit.get("decision"),
            },
        },
        "recommended_android_boot_image": (v299.get("recommended_android_boot_image") or {}),
        "native_rollback_image": (v299.get("native_image") or {}),
        "live_command": LIVE_COMMAND,
        "checks": [asdict(check) for check in checks],
        "captures": [asdict(capture) for capture in captures],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("approval-packet.md", render_packet(manifest))
    store.write_text("live-command.txt", LIVE_COMMAND + "\n")
    store.write_text("summary.md", render_packet(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
