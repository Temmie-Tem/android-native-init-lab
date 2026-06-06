#!/usr/bin/env python3
"""Fail-closed executor for the Android property capture handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from android_capture_handoff_preflight import (
    BOOT_BLOCK_SIZE,
    DEFAULT_NATIVE_IMAGE,
    NATIVE_EXPECT_VERSION,
    choose_android_candidate,
    discover_android_images,
    inspect_image,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v300-android-capture-executor")
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_BOOT_BLOCK = "/dev/block/by-name/boot"
DEFAULT_REMOTE_ANDROID_IMAGE = "/tmp/android_boot.img"


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
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--android-timeout", type=int, default=240)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def display_command(command: list[str] | str) -> str:
    if isinstance(command, str):
        return command
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else part for index, part in enumerate(command)]
    return " ".join(shlex.quote(part) for part in redacted)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remote_quote(path: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"remote path must be absolute: {path}")
    return shlex.quote(path)


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
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - executor evidence preserves failure details
        return None, "", str(exc), time.monotonic() - started


def write_step(store: EvidenceStore,
               name: str,
               command: list[str] | str,
               text: str,
               error: str,
               rc: int | None,
               duration: float,
               skipped: bool = False,
               ok_override: bool | None = None) -> StepResult:
    body = "\n".join([f"$ {display_command(command)}", text.rstrip() if text else error.rstrip(), f"rc={rc}", ""])
    path = store.write_text(f"steps/{name}.txt", body)
    ok = ok_override if ok_override is not None else rc == 0
    return StepResult(name, display_command(command), bool(ok), rc, duration, str(path.relative_to(store.run_dir)), skipped, error)


def execute_step(store: EvidenceStore,
                 name: str,
                 command: list[str],
                 timeout: int,
                 execute: bool) -> StepResult:
    if not execute:
        return write_step(store, name, command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    rc, text, error, duration = run_process(command, timeout)
    return write_step(store, name, command, text, error, rc, duration)


def bridge_command(args: argparse.Namespace, command: str, timeout_sec: int) -> tuple[bool, str, str, float]:
    started = time.monotonic()
    deadline = started + timeout_sec
    last_error = ""
    payload = ("\n" + command + "\n").encode()
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((args.bridge_host, args.bridge_port), timeout=2.0) as sock:
                sock.settimeout(0.5)
                sock.sendall(payload)
                data = bytearray()
                read_deadline = time.monotonic() + 8.0
                while time.monotonic() < read_deadline:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    data.extend(chunk)
                    if b"[done]" in data or b"recovery:" in data or b"[err]" in data or b"[busy]" in data:
                        break
                text = data.decode("utf-8", errors="replace")
                return ("[err]" not in text and "[busy]" not in text), text, "", time.monotonic() - started
        except OSError as exc:
            last_error = str(exc)
            time.sleep(1.0)
    return False, "", last_error or f"bridge command timeout: {command}", time.monotonic() - started


def execute_bridge_step(store: EvidenceStore,
                        args: argparse.Namespace,
                        name: str,
                        command: str,
                        timeout: int,
                        execute: bool) -> StepResult:
    rendered = f"bridge:{args.bridge_host}:{args.bridge_port} {command}"
    if not execute:
        return write_step(store, name, rendered, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    ok, text, error, duration = bridge_command(args, command, timeout)
    return write_step(store, name, rendered, text, error, 0 if ok else 1, duration, ok_override=ok)


def wait_for_adb_state(args: argparse.Namespace, wanted: set[str], timeout: int, execute: bool, store: EvidenceStore, name: str) -> StepResult:
    command = [*adb_base(args), "devices"]
    if not execute:
        return write_step(store, name, command, f"[dry-run] wait for adb state {sorted(wanted)}\n", "", 0, 0.0, skipped=True, ok_override=True)
    started = time.monotonic()
    deadline = started + timeout
    last_text = ""
    while time.monotonic() < deadline:
        rc, text, error, _ = run_process(command, min(10, timeout))
        last_text = text if text else error
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] in wanted:
                return write_step(store, name, command, text, "", rc, time.monotonic() - started, ok_override=True)
        time.sleep(1.0)
    return write_step(store, name, command, last_text, f"timeout waiting for adb states {sorted(wanted)}", None, time.monotonic() - started, ok_override=False)


def require_approval(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_android_boot_flash:
        missing.append("--allow-android-boot-flash")
    if not args.assume_yes:
        missing.append("--assume-yes")
    if not args.i_understand_native_rollback:
        missing.append("--i-understand-native-rollback")
    return not missing, missing


def choose_images(args: argparse.Namespace) -> tuple[Any, Any]:
    native_image = inspect_image(args.native_image, "native-rollback")
    android_images = [inspect_image(path, "android-candidate") for path in discover_android_images(args.android_boot_image)]
    return native_image, choose_android_candidate(android_images)


def build_step_plan(args: argparse.Namespace, android_path: str, native_path: str, android_count: int) -> list[tuple[str, list[str] | str, int]]:
    remote_android = remote_quote(args.remote_android_image)
    boot_block = remote_quote(args.boot_block)
    capture_command = [
        "python3",
        "scripts/revalidation/wifi_android_property_capture.py",
        "--out-dir",
        "tmp/wifi/v297-android-property-capture-android",
        "--adb",
        args.adb,
    ]
    restore_command = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        native_path,
        "--adb",
        args.adb,
        "--expect-version",
        NATIVE_EXPECT_VERSION,
        "--verify-protocol",
        "auto",
    ]
    if args.serial:
        capture_command.extend(["--serial", args.serial])
        restore_command.extend(["--serial", args.serial])
    capture_command.append("run")

    return [
        ("native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], args.timeout),
        ("native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], args.timeout),
        ("hide-menu", f"bridge:{args.bridge_host}:{args.bridge_port} hide", args.timeout),
        ("native-recovery", f"bridge:{args.bridge_host}:{args.bridge_port} recovery", args.recovery_timeout),
        ("wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ("push-android-boot", [*adb_base(args), "push", android_path, args.remote_android_image], args.timeout),
        ("remote-android-sha", [*adb_base(args), "shell", f"sha256sum {remote_android} 2>/dev/null || toybox sha256sum {remote_android}"], args.timeout),
        ("flash-android-boot", [*adb_base(args), "shell", f"dd if={remote_android} of={boot_block} bs=4M conv=fsync && sync"], args.timeout),
        (
            "readback-android-boot",
            [
                *adb_base(args),
                "shell",
                f"dd if={boot_block} bs={BOOT_BLOCK_SIZE} count={android_count} 2>/dev/null | sha256sum 2>/dev/null || "
                f"dd if={boot_block} bs={BOOT_BLOCK_SIZE} count={android_count} 2>/dev/null | toybox sha256sum",
            ],
            args.timeout,
        ),
        ("reboot-android", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
        ("wait-android", [*adb_base(args), "wait-for-device"], args.android_timeout),
        ("capture-android-property", capture_command, args.timeout * 6),
        (
            "compare-property-baseline",
            [
                "python3",
                "scripts/revalidation/wifi_property_baseline_compare.py",
                "--out-dir",
                "tmp/wifi/v298-property-baseline-compare-android",
                "--v297-manifest",
                "tmp/wifi/v297-android-property-capture-android/manifest.json",
                "run",
            ],
            args.timeout,
        ),
        ("reboot-recovery-for-rollback", [*adb_base(args), "reboot", "recovery"], args.timeout),
        ("wait-rollback-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        (
            "restore-native",
            restore_command,
            args.recovery_timeout + args.android_timeout,
        ),
    ]


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_image = choose_images(args)
    approval_ok, missing_flags = require_approval(args)
    context = {
        "native_image": asdict(native_image),
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
    }
    if not native_image.present or not native_image.native_marker:
        return [], context, "android-capture-executor-missing-native-rollback", False
    if android_image is None:
        return [], context, "android-capture-executor-missing-android-boot", False
    if args.command == "run" and not approval_ok:
        return [], context, "android-capture-executor-approval-required", False

    android_path = android_image.path
    native_path = native_image.path
    android_count = android_image.size // BOOT_BLOCK_SIZE
    plan = build_step_plan(args, android_path, native_path, android_count)
    steps: list[StepResult] = []

    if args.command == "plan":
        for name, command, timeout in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "android-capture-executor-plan-ready", True

    live = args.command == "run"
    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            bridge_payload = command.split(" ", 1)[1]
            step = execute_bridge_step(store, args, name, bridge_payload, timeout, execute=live)
        elif name == "wait-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, live, store, name)
        elif name == "wait-android":
            step = wait_for_adb_state(args, {"device"}, timeout, live, store, name)
        elif name == "wait-rollback-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, live, store, name)
        else:
            step = execute_step(store, name, command, timeout, execute=live)
        steps.append(step)
        if live and not step.ok:
            return steps, context, f"android-capture-executor-failed-{name}", False
        if name == "remote-android-sha" and live:
            remote_text = Path(store.run_dir / step.file).read_text(encoding="utf-8", errors="replace")
            if android_image.sha256 not in remote_text:
                return steps, context, "android-capture-executor-remote-sha-mismatch", False
        if name == "readback-android-boot" and live:
            readback_text = Path(store.run_dir / step.file).read_text(encoding="utf-8", errors="replace")
            if android_image.sha256 not in readback_text:
                return steps, context, "android-capture-executor-readback-sha-mismatch", False

    return steps, context, "android-capture-executor-pass" if live else "android-capture-executor-dryrun-ready", True


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
    return "\n".join(
        [
            "# v300 Android Capture Handoff Executor",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            f"- approval_ok: `{manifest['context']['approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
            "",
            "## Images",
            "",
            markdown_table(
                ["role", "path", "present", "size", "sha256 prefix"],
                [
                    [
                        "native",
                        manifest["context"]["native_image"]["path"],
                        str(manifest["context"]["native_image"]["present"]),
                        str(manifest["context"]["native_image"]["size"]),
                        manifest["context"]["native_image"]["sha256"][:16] if manifest["context"]["native_image"]["sha256"] else "",
                    ],
                    [
                        "android",
                        manifest["context"]["android_image"]["path"] if manifest["context"]["android_image"] else "-",
                        str(manifest["context"]["android_image"]["present"]) if manifest["context"]["android_image"] else "False",
                        str(manifest["context"]["android_image"]["size"]) if manifest["context"]["android_image"] else "0",
                        manifest["context"]["android_image"]["sha256"][:16] if manifest["context"]["android_image"] else "",
                    ],
                ],
            ),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- `run` requires explicit approval flags.",
            "- `plan` and `dry-run` do not reboot, enter recovery, or write boot.",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.",
            "- No property mutation or service-manager/HAL/Wi-Fi daemon execution.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    reason = {
        "android-capture-executor-plan-ready": "execution plan generated without device mutation",
        "android-capture-executor-dryrun-ready": "dry-run recorded all steps without device mutation",
        "android-capture-executor-approval-required": "live run refused because approval flags are missing",
        "android-capture-executor-pass": "live handoff and rollback sequence completed",
    }.get(decision, decision)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
