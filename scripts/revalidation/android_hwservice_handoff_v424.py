#!/usr/bin/env python3
"""V424 bounded Android handoff for V423 read-only hwservice inventory.

The live path temporarily flashes a known Android boot image, boots Android,
runs the V423 read-only hwservice/lshal collector, then restores the native
init boot image.  It does not enable Wi-Fi, scan, connect, link up interfaces,
change credentials, start Wi-Fi daemons directly, or route traffic.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v424-android-hwservice-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v319.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
ANDROID_BOOT_GLOBS = (
    "backups/baseline_*/boot.img",
    "backups/*stock*boot*.img",
    "backups/*android*boot*.img",
)
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_BOOT_BLOCK = "/dev/block/by-name/boot"
DEFAULT_REMOTE_ANDROID_IMAGE = "/tmp/android_boot.img"
BOOT_READBACK_BLOCK_SIZE = 4096
ACTIVE_WIFI_RE = re.compile(
    r"\b(?:svc\s+wifi|cmd\s+wifi|iw\s+(?:scan|connect)|wpa_cli|rfkill\s+(?:un)?block|ip\s+link\s+set\b.*\bup)\b",
    re.IGNORECASE,
)


@dataclass
class ImageInfo:
    path: str
    present: bool
    size: int
    aligned_4k: bool
    sha256: str
    android_magic: bool
    native_marker: bool
    role_hint: str


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
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--android-timeout", type=int, default=300)
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
    return shlex.join(redacted)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_contains(path: Path, needle: bytes) -> bool:
    if not needle or not path.exists():
        return False
    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            data = previous + chunk
            if needle in data:
                return True
            previous = data[-overlap:] if overlap else b""
    return False


def inspect_image(path: Path, role_hint: str, native_marker: bytes = b"A90 Linux init") -> ImageInfo:
    resolved = repo_path(path)
    if not resolved.exists():
        return ImageInfo(str(resolved), False, 0, False, "", False, False, role_hint)
    size = resolved.stat().st_size
    with resolved.open("rb") as file_obj:
        header = file_obj.read(8)
    return ImageInfo(
        path=str(resolved),
        present=True,
        size=size,
        aligned_4k=size > 0 and size % BOOT_READBACK_BLOCK_SIZE == 0,
        sha256=sha256_file(resolved),
        android_magic=header == b"ANDROID!",
        native_marker=file_contains(resolved, native_marker),
        role_hint=role_hint,
    )


def discover_android_images(extra: list[Path]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for item in extra:
        resolved = repo_path(item)
        if resolved not in seen:
            seen.add(resolved)
            paths.append(item)
    for pattern in ANDROID_BOOT_GLOBS:
        for path in sorted(repo_path(".").glob(pattern)):
            if path not in seen:
                seen.add(path)
                paths.append(path)
    return paths


def choose_android_candidate(images: list[ImageInfo]) -> ImageInfo | None:
    valid = [
        image for image in images
        if image.present and image.aligned_4k and image.android_magic and not image.native_marker
    ]
    if not valid:
        return None
    valid.sort(key=lambda image: (image.size != 64 * 1024 * 1024, image.path))
    return valid[0]


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
    except Exception as exc:  # noqa: BLE001 - handoff evidence preserves failure details
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


def execute_step(store: EvidenceStore, name: str, command: list[str], timeout: int, execute: bool) -> StepResult:
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


def execute_bridge_step(store: EvidenceStore, args: argparse.Namespace, name: str, command: str, timeout: int, execute: bool) -> StepResult:
    rendered = f"bridge:{args.bridge_host}:{args.bridge_port} {command}"
    if not execute:
        return write_step(store, name, rendered, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    ok, text, error, duration = bridge_command(args, command, timeout)
    if command == "hide" and "hide requested" in text:
        ok = True
    return write_step(store, name, rendered, text, error, 0 if ok else 1, duration, ok_override=ok)


def wait_for_adb_state(args: argparse.Namespace,
                       wanted: set[str],
                       timeout: int,
                       execute: bool,
                       store: EvidenceStore,
                       name: str) -> StepResult:
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


def image_context(args: argparse.Namespace) -> tuple[ImageInfo, list[ImageInfo], ImageInfo | None]:
    native_marker = args.native_expect_version.encode()
    native_image = inspect_image(args.native_image, "native-rollback", native_marker=native_marker)
    android_images = [inspect_image(path, "android-candidate") for path in discover_android_images(args.android_boot_image)]
    return native_image, android_images, choose_android_candidate(android_images)


def v423_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v423-android-hwservice-run"


def build_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: ImageInfo, native_image: ImageInfo) -> list[tuple[str, list[str] | str, int]]:
    remote_android = remote_quote(args.remote_android_image)
    boot_block = remote_quote(args.boot_block)
    android_count = android_image.size // BOOT_READBACK_BLOCK_SIZE
    v423_command = [
        "python3",
        "scripts/revalidation/wifi_android_hwservice_inventory_v423.py",
        "--out-dir",
        str(v423_out_dir(store)),
        "--adb",
        args.adb,
    ]
    restore_command = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        native_image.path,
        "--adb",
        args.adb,
        "--expect-version",
        args.native_expect_version,
        "--verify-protocol",
        "auto",
    ]
    if args.serial:
        v423_command.extend(["--serial", args.serial])
        restore_command.extend(["--serial", args.serial])
    v423_command.append("run")
    return [
        ("native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], args.timeout),
        ("native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], args.timeout),
        ("hide-menu", f"bridge:{args.bridge_host}:{args.bridge_port} hide", args.timeout),
        ("native-recovery", f"bridge:{args.bridge_host}:{args.bridge_port} recovery", args.recovery_timeout),
        ("wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ("push-android-boot", [*adb_base(args), "push", android_image.path, args.remote_android_image], args.timeout * 4),
        ("remote-android-sha", [*adb_base(args), "shell", f"sha256sum {remote_android} 2>/dev/null || toybox sha256sum {remote_android}"], args.timeout),
        ("flash-android-boot", [*adb_base(args), "shell", f"dd if={remote_android} of={boot_block} bs=4M conv=fsync && sync"], args.timeout * 4),
        (
            "readback-android-boot",
            [
                *adb_base(args),
                "shell",
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={android_count} 2>/dev/null | sha256sum 2>/dev/null || "
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={android_count} 2>/dev/null | toybox sha256sum",
            ],
            args.timeout * 2,
        ),
        ("reboot-android", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
        ("wait-android", [*adb_base(args), "devices"], args.android_timeout),
        ("v423-android-hwservice-inventory", v423_command, args.timeout * 8),
        ("wait-android-before-rollback", [*adb_base(args), "devices"], args.timeout),
        ("reboot-recovery-for-rollback", [*adb_base(args), "reboot", "recovery"], args.timeout),
        ("wait-rollback-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ("restore-native", restore_command, args.recovery_timeout + args.android_timeout),
    ]


def step_text(store: EvidenceStore, step: StepResult) -> str:
    return (store.run_dir / step.file).read_text(encoding="utf-8", errors="replace")


def contains_forbidden_active_wifi(plan: list[tuple[str, list[str] | str, int]]) -> list[str]:
    offenders: list[str] = []
    for name, command, _ in plan:
        rendered = display_command(command)
        if ACTIVE_WIFI_RE.search(rendered):
            offenders.append(name)
    return offenders


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    context = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "v423_out_dir": str(v423_out_dir(store)),
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v424-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v424-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v424-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v424-handoff-approval-required", False

    plan = build_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v424-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v424-handoff-plan-ready", True

    restore_entry = next(item for item in plan if item[0] == "restore-native")
    v423_step_ok = False
    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            bridge_payload = command.split(" ", 1)[1]
            step = execute_bridge_step(store, args, name, bridge_payload, timeout, execute=execute)
        elif name == "wait-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name == "wait-android":
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-android-before-rollback":
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-rollback-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v424-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v424-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v424-handoff-readback-failed-rollback-attempted", False
        if name == "v423-android-hwservice-inventory":
            v423_step_ok = step.ok
            if execute:
                continue
        if execute and not step.ok:
            return steps, context, f"v424-handoff-failed-{name}", False

    if execute and not v423_step_ok:
        return steps, context, "v424-handoff-v423-capture-failed-rollback-complete", False
    return steps, context, "v424-handoff-pass" if execute else "v424-handoff-dryrun-ready", True


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
    image_rows = [
        [
            image["path"],
            str(image["present"]),
            str(image["size"]),
            str(image["android_magic"]),
            str(image["native_marker"]),
            image["sha256"][:16] if image["sha256"] else "",
        ]
        for image in manifest["context"]["android_images"]
    ]
    return "\n".join(
        [
            "# V424 Android hwservice Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- approval_ok: `{manifest['context']['approval_ok']}`",
            f"- missing_approval_flags: `{', '.join(manifest['context']['missing_approval_flags']) or '-'}`",
            f"- v423_out_dir: `{manifest['context']['v423_out_dir']}`",
            "",
            "## Native Rollback Image",
            "",
            markdown_table(
                ["path", "present", "size", "android magic", "native marker", "sha256 prefix"],
                [[
                    manifest["context"]["native_image"]["path"],
                    str(manifest["context"]["native_image"]["present"]),
                    str(manifest["context"]["native_image"]["size"]),
                    str(manifest["context"]["native_image"]["android_magic"]),
                    str(manifest["context"]["native_image"]["native_marker"]),
                    manifest["context"]["native_image"]["sha256"][:16] if manifest["context"]["native_image"]["sha256"] else "",
                ]],
            ),
            "",
            "## Android Boot Candidates",
            "",
            markdown_table(["path", "present", "size", "android magic", "native marker", "sha256 prefix"], image_rows if image_rows else [["-", "-", "-", "-", "-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- `run` requires explicit approval flags.",
            "- `plan` and `dry-run` do not reboot, enter recovery, or write boot.",
            "- Live mode limits Android work to the V423 read-only hwservice/lshal collector.",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.",
            "- No direct Wi-Fi daemon start, rfkill/sysfs write, module load/unload, or property mutation.",
            "",
        ]
    )


def reason_for(decision: str) -> str:
    return {
        "v424-handoff-plan-ready": "execution plan generated without device mutation",
        "v424-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v424-handoff-approval-required": "live run refused because approval flags are missing",
        "v424-handoff-missing-native-rollback": "native rollback image is missing or does not contain the expected version marker",
        "v424-handoff-missing-android-boot": "no Android boot candidate passed local safety checks",
        "v424-handoff-image-collision": "Android and native rollback images unexpectedly have the same hash",
        "v424-handoff-active-wifi-command-blocked": "handoff plan contains a forbidden active Wi-Fi command pattern",
        "v424-handoff-pass": "Android handoff, V423 inventory, and native rollback completed",
        "v424-handoff-v423-capture-failed-rollback-complete": "V423 Android inventory failed, but native rollback steps completed",
        "v424-handoff-flash-failed-rollback-attempted": "Android boot flash failed and native rollback was attempted from recovery",
        "v424-handoff-readback-failed-rollback-attempted": "Android boot readback failed and native rollback was attempted from recovery",
    }.get(decision, decision)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run" and decision not in {
            "v424-handoff-approval-required",
            "v424-handoff-missing-native-rollback",
            "v424-handoff-missing-android-boot",
            "v424-handoff-image-collision",
            "v424-handoff-active-wifi-command-blocked",
        },
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
