#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import shlex
import socket
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from a90ctl import ProtocolResult, run_cmdv1_command


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_REMOTE_IMAGE = "/tmp/native_init_boot.img"
BOOT_READBACK_BLOCK_SIZE = 4096
ANDROID_BOOT_MAGIC = b"ANDROID!"
INPUT_MODE_ENV = "A90CTL_INPUT_MODE"
INPUT_CHAR_DELAY_ENV = "A90CTL_INPUT_CHAR_DELAY_SEC"
DEFAULT_SELF_WRITE_STAGING_DIR = "/mnt/sdext/a90/flash-staging"
SELF_WRITE_ALLOWED_STAGING_DIRS = (
    "/mnt/sdext/a90/flash-staging",
    "/cache/a90-runtime/flash-staging",
)
SELF_WRITE_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SELF_WRITE_POLICY_BLOCK = (
    "experimental self-write live path is blocked: F4/production fast-flash is not "
    "authorized by AGENTS.md or design section 12.1"
)


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[native-init-flash {timestamp}] {message}", file=sys.stderr, flush=True)


@contextmanager
def phase_timer(name: str):
    started = time.monotonic()
    ok = False
    try:
        yield
        ok = True
    finally:
        elapsed = time.monotonic() - started
        log(f"phase.native_init_flash.{name}.elapsed_sec={elapsed:.3f} ok={int(ok)}")


def run_command(args: list[str],
                *,
                check: bool = True,
                capture: bool = False) -> subprocess.CompletedProcess:
    log("+ " + shlex.join(args))
    if capture:
        return subprocess.run(
            args,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return subprocess.run(args, check=check)


def adb_base(adb: str, serial: str | None) -> list[str]:
    base = [adb]
    if serial:
        base.extend(["-s", serial])
    return base


def quote_remote_path(path: str, *, label: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"{label} must be an absolute remote path")
    return shlex.quote(path)


def parse_adb_devices(output: str) -> list[tuple[str, str]]:
    devices: list[tuple[str, str]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))

    return devices


def adb_devices(adb: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        [adb, "devices"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return parse_adb_devices(result.stdout)


def adb_state(adb: str, serial: str) -> str | None:
    for device_serial, state in adb_devices(adb):
        if device_serial == serial:
            return state
    return None


def wait_for_adb_state(adb: str,
                       serial: str | None,
                       wanted_states: set[str],
                       timeout_sec: float) -> tuple[str, str]:
    deadline = time.monotonic() + timeout_sec
    last_devices: list[tuple[str, str]] = []

    while time.monotonic() < deadline:
        last_devices = adb_devices(adb)
        for device_serial, state in last_devices:
            if serial and device_serial != serial:
                continue
            if state in wanted_states:
                log(f"ADB ready: {device_serial} {state}")
                return device_serial, state
        time.sleep(1.0)

    rendered = ", ".join(f"{device_serial}:{state}" for device_serial, state in last_devices) or "<none>"
    raise RuntimeError(f"ADB state timeout; wanted={sorted(wanted_states)} last={rendered}")


def wait_for_adb_disconnect(adb: str, serial: str, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec

    while time.monotonic() < deadline:
        if adb_state(adb, serial) is None:
            return True
        time.sleep(0.5)

    return False


def local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_sha256(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise RuntimeError(f"{label} must be a 64-character hex SHA256")
    return normalized


def file_contains(path: Path, needle: bytes) -> bool:
    if not needle:
        return True

    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            data = previous + chunk
            if needle in data:
                return True
            previous = data[-overlap:] if overlap else b""

    return False


def inspect_local_image(args: argparse.Namespace) -> tuple[Path, str, int]:
    image_path = Path(args.boot_image)
    try:
        image_stat = image_path.lstat()
    except FileNotFoundError:
        raise FileNotFoundError(image_path)
    if not stat.S_ISREG(image_stat.st_mode):
        raise RuntimeError(f"boot image is not a regular file: {image_path}")
    if image_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError(f"boot image is group/world writable: {image_path}")

    image_size = image_stat.st_size
    if image_size <= 0:
        raise RuntimeError(f"boot image is empty: {image_path}")
    if image_size % BOOT_READBACK_BLOCK_SIZE != 0:
        raise RuntimeError(
            f"boot image size is not {BOOT_READBACK_BLOCK_SIZE}-byte aligned: "
            f"{image_size}"
        )

    if getattr(args, "expect_android_magic", False):
        with image_path.open("rb") as fp:
            magic = fp.read(len(ANDROID_BOOT_MAGIC))
        if magic != ANDROID_BOOT_MAGIC:
            raise RuntimeError("local image does not start with Android boot magic")
        log("local image starts with Android boot magic")

    if args.expect_version:
        needle = args.expect_version.encode()
        if not file_contains(image_path, needle):
            raise RuntimeError(
                f"expected version marker not found in local image before reboot: "
                f"{args.expect_version}"
            )
        log(f"local image contains expected marker: {args.expect_version}")

    local_hash = local_sha256(image_path)
    if args.expect_sha256 and local_hash != args.expect_sha256:
        raise RuntimeError(
            f"local image sha256 mismatch: expected={args.expect_sha256} actual={local_hash}"
        )
    log(f"local image size: {image_size}")
    log(f"local image sha256: {local_hash}")
    return image_path, local_hash, image_size


def validate_self_write_staging_dir(path: str) -> str:
    if "\x00" in path or not path.startswith("/"):
        raise RuntimeError("--self-write-staging-dir must be an absolute device path")
    normalized = posixpath.normpath(path)
    if normalized != path.rstrip("/"):
        raise RuntimeError("--self-write-staging-dir must be normalized")
    if normalized not in SELF_WRITE_ALLOWED_STAGING_DIRS:
        allowed = ", ".join(SELF_WRITE_ALLOWED_STAGING_DIRS)
        raise RuntimeError(f"--self-write-staging-dir must be one of: {allowed}")
    return normalized


def self_write_remote_image_path(args: argparse.Namespace, image_path: Path) -> str:
    staging_dir = validate_self_write_staging_dir(args.self_write_staging_dir)
    basename = image_path.name
    if not basename or not SELF_WRITE_SAFE_BASENAME_RE.fullmatch(basename):
        raise RuntimeError(f"unsafe self-write remote image basename: {basename!r}")
    return posixpath.join(staging_dir, basename)


def build_experimental_self_write_plan(args: argparse.Namespace,
                                       image_path: Path,
                                       local_hash: str,
                                       image_size: int) -> dict[str, object]:
    if not args.expect_sha256:
        raise RuntimeError("experimental self-write requires --expect-sha256")
    if not args.expect_version:
        raise RuntimeError("experimental self-write requires --expect-version")
    if args.allow_unpinned_image:
        raise RuntimeError("experimental self-write does not allow --allow-unpinned-image")
    if not args.expect_android_magic:
        raise RuntimeError("experimental self-write requires --expect-android-magic")

    remote_image = self_write_remote_image_path(args, image_path)
    tcpctl_script = "workspace/public/src/scripts/revalidation/tcpctl_host.py"
    return {
        "mode": "experimental-self-write",
        "policy_state": "plan-only-live-blocked",
        "policy_block": SELF_WRITE_POLICY_BLOCK,
        "local_image": str(image_path),
        "local_sha256": local_hash,
        "image_size": image_size,
        "expected_version": args.expect_version,
        "remote_image": remote_image,
        "staging_dir": posixpath.dirname(remote_image),
        "preflight_commands": [
            "version",
            "status",
            "selftest",
            "pstore summary",
        ],
        "stage_command": [
            "python3",
            tcpctl_script,
            "--bridge-host",
            args.bridge_host,
            "--bridge-port",
            str(args.bridge_port),
            "install",
            "--install-control-channel",
            "tcpctl",
            "--local-binary",
            str(image_path),
            "--device-binary",
            remote_image,
        ],
        "source_plan_command": [
            "boot-flash-plan",
            remote_image,
            local_hash,
            args.expect_version,
        ],
        "self_write_command": [
            "boot-flash-f2",
            "BOOT-FLASH-F2-BOOT-CANDIDATE",
            remote_image,
            local_hash,
            args.expect_version,
        ],
        "system_reboot_command": ["reboot"],
        "required_timeline_events": [
            "candidate_flash_start",
            "candidate_flash_done",
            "candidate_boot_ready",
            "live_session_start",
            "live_session_end",
            "rollback_flash_start",
            "rollback_flash_done",
            "rollback_boot_ready",
        ],
        "fallback_path": "native_init_flash.py rollback to v2321 through checked helper/TWRP",
    }


def run_experimental_self_write(args: argparse.Namespace,
                                image_path: Path,
                                local_hash: str,
                                image_size: int) -> int:
    plan = build_experimental_self_write_plan(args, image_path, local_hash, image_size)
    print(json.dumps(plan, indent=2, sort_keys=True))
    if args.self_write_plan_only:
        return 0
    raise RuntimeError(SELF_WRITE_POLICY_BLOCK)


@contextmanager
def sealed_local_image_copy(image_path: Path, expected_hash: str, expected_size: int):
    with tempfile.TemporaryDirectory(prefix="native-init-flash-") as temp_dir:
        sealed_path = Path(temp_dir) / "boot.img"
        open_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(image_path, open_flags)
        try:
            source_stat = os.fstat(fd)
            if not stat.S_ISREG(source_stat.st_mode):
                raise RuntimeError(f"boot image changed to a non-regular file: {image_path}")
            if source_stat.st_size != expected_size:
                raise RuntimeError(
                    f"boot image size changed before push: expected={expected_size} "
                    f"actual={source_stat.st_size}"
                )
            with os.fdopen(os.dup(fd), "rb") as source, sealed_path.open("xb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
        finally:
            os.close(fd)
        os.chmod(sealed_path, 0o600)
        sealed_size = sealed_path.stat().st_size
        sealed_hash = local_sha256(sealed_path)
        if sealed_size != expected_size:
            raise RuntimeError(f"sealed image size mismatch: expected={expected_size} actual={sealed_size}")
        if sealed_hash != expected_hash:
            raise RuntimeError(f"sealed image sha256 mismatch: expected={expected_hash} actual={sealed_hash}")
        log(f"sealed local image copy: {sealed_path}")
        yield sealed_path


def remote_sha256(adb: str, serial: str | None, remote_path: str) -> str:
    remote = quote_remote_path(remote_path, label="remote image")
    command = adb_base(adb, serial) + [
        "shell",
        f"sha256sum {remote} 2>/dev/null || toybox sha256sum {remote}",
    ]
    result = run_command(command, capture=True)
    first_field = result.stdout.strip().split()[0]
    if len(first_field) != 64:
        raise RuntimeError(f"unexpected remote sha256 output: {result.stdout!r}")
    return first_field


def remote_boot_prefix_sha256(adb: str,
                              serial: str | None,
                              boot_block: str,
                              image_size: int) -> str:
    count = image_size // BOOT_READBACK_BLOCK_SIZE
    block = quote_remote_path(boot_block, label="boot block")
    command = adb_base(adb, serial) + [
        "shell",
        (
            f"dd if={block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} "
            "2>/dev/null | sha256sum 2>/dev/null || "
            f"dd if={block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} "
            "2>/dev/null | toybox sha256sum"
        ),
    ]
    result = run_command(command, capture=True)
    first_field = result.stdout.strip().split()[0]
    if len(first_field) != 64:
        raise RuntimeError(f"unexpected boot prefix sha256 output: {result.stdout!r}")
    return first_field


def bridge_command(host: str,
                   port: int,
                   command: str,
                   timeout_sec: float,
                   markers: tuple[bytes, ...] = (b"[done]", b"[err]")) -> str:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0) as sock:
                sock.settimeout(0.25)
                wire_command = command
                input_mode = os.environ.get(INPUT_MODE_ENV)
                double_input = input_mode == "double"
                if double_input:
                    wire_command = "".join(ch * 2 for ch in command)
                prefix = "" if input_mode in {"double", "slow"} else "\n"
                payload = prefix + wire_command + "\n"
                if input_mode == "slow":
                    delay = float(os.environ.get(INPUT_CHAR_DELAY_ENV, "0.02"))
                    for ch in payload:
                        sock.sendall(ch.encode())
                        time.sleep(delay)
                else:
                    sock.sendall(payload.encode())
                data = bytearray()
                read_deadline = time.monotonic() + 5.0
                while time.monotonic() < read_deadline:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    data.extend(chunk)
                    if any(marker in data for marker in markers):
                        time.sleep(0.2)
                        try:
                            data.extend(sock.recv(8192))
                        except socket.timeout:
                            pass
                        return data.decode("utf-8", errors="replace")
        except OSError as exc:
            last_error = exc

        time.sleep(1.0)

    raise RuntimeError(f"bridge command timeout for {command!r}: {last_error}")


def reboot_native_to_recovery(args: argparse.Namespace) -> None:
    log("requesting recovery from native init bridge")
    for attempt in range(1, 4):
        output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "recovery",
            args.bridge_timeout,
            markers=(b"recovery:", b"[err]", b"[busy]"),
        )
        print(output, end="")

        if "[busy]" not in output:
            return

        log(f"native init menu is active; requesting hide before recovery attempt={attempt}")
        hide_output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "hide",
            args.bridge_timeout,
            markers=(b"[busy]", b"[done]", b"[err]"),
        )
        print(hide_output, end="")
        time.sleep(3.0)

    raise RuntimeError("native init recovery command stayed busy after hide retries")


def flash_boot_image(args: argparse.Namespace,
                     serial: str,
                     image_path: Path,
                     local_hash: str,
                     image_size: int) -> None:
    expected_readback_hash = args.expect_readback_sha256 or local_hash
    remote = quote_remote_path(args.remote_image, label="remote image")
    block = quote_remote_path(args.boot_block, label="boot block")

    with phase_timer("adb_push"):
        run_command(adb_base(args.adb, serial) + ["push", str(image_path), args.remote_image])

    with phase_timer("remote_sha256"):
        remote_hash = remote_sha256(args.adb, serial, args.remote_image)
    log(f"remote image sha256: {remote_hash}")
    if remote_hash != local_hash:
        raise RuntimeError("remote sha256 mismatch after adb push")

    flash_cmd = (
        f"dd if={remote} of={block} "
        "bs=4M conv=fsync && sync"
    )
    with phase_timer("boot_dd_write"):
        run_command(adb_base(args.adb, serial) + ["shell", flash_cmd])

    with phase_timer("boot_readback_sha256"):
        boot_prefix_hash = remote_boot_prefix_sha256(args.adb, serial, args.boot_block, image_size)
    log(f"boot block prefix sha256: {boot_prefix_hash}")
    if boot_prefix_hash != expected_readback_hash:
        raise RuntimeError("boot block prefix sha256 mismatch after flash")


def reboot_twrp_to_system(args: argparse.Namespace, serial: str) -> None:
    time.sleep(1.0)

    for attempt in range(1, 4):
        log(f"requesting system boot through TWRP no-argument reboot attempt={attempt}")
        result = run_command(
            adb_base(args.adb, serial) + ["shell", "twrp reboot"],
            check=False,
            capture=True,
        )
        output = (result.stdout + result.stderr).strip()
        if output:
            for line in output.splitlines():
                log(f"twrp reboot: {line}")

        if wait_for_adb_disconnect(args.adb, serial, 8.0):
            return

        log("TWRP recovery ADB is still present after reboot request; retrying")
        time.sleep(2.0)

    raise RuntimeError("TWRP reboot did not leave recovery ADB")


def verify_native_init(args: argparse.Namespace) -> str:
    if args.verify_protocol == "selftest":
        return verify_native_init_selftest(args)
    if args.verify_protocol == "raw":
        return verify_native_init_raw(args)

    try:
        return verify_native_init_cmdv1(args)
    except RuntimeError as exc:
        if args.verify_protocol == "cmdv1":
            raise
        if "A90P1 END marker not found" not in str(exc):
            raise
        log(f"cmdv1 verify unavailable; falling back to raw version check: {exc}")
        return verify_native_init_raw(args)


def verify_native_init_selftest(args: argparse.Namespace) -> str:
    result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["selftest"],
    )
    print(result.text, end="" if result.text.endswith("\n") else "\n")
    verify_cmdv1_result(result, "selftest")
    if "fail=0" not in result.text:
        raise RuntimeError("native selftest did not report fail=0")
    version_text = ""
    if args.expect_version:
        version_result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout,
            ["version"],
        )
        print(version_result.text, end="" if version_result.text.endswith("\n") else "\n")
        verify_cmdv1_result(version_result, "version")
        if args.expect_version not in version_result.text:
            raise RuntimeError(f"expected version marker not found: {args.expect_version}")
        version_text = version_result.text
    log("cmdv1 verify passed: selftest rc=0 status=ok fail=0")
    return result.text + version_text


def verify_native_init_raw(args: argparse.Namespace) -> str:
    output = bridge_command(
        args.bridge_host,
        args.bridge_port,
        "version",
        args.bridge_timeout,
        markers=(b"[done] version", b"[err] version"),
    )
    print(output, end="")
    if args.expect_version and args.expect_version not in output:
        raise RuntimeError(f"expected version marker not found: {args.expect_version}")
    return output


def verify_cmdv1_result(result: ProtocolResult, command: str) -> None:
    if result.rc != 0 or result.status != "ok":
        raise RuntimeError(
            f"cmdv1 {command} failed rc={result.rc} status={result.status}\n"
            f"{result.text}"
        )


def verify_native_init_cmdv1(args: argparse.Namespace) -> str:
    version_result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["version"],
    )
    print(version_result.text, end="" if version_result.text.endswith("\n") else "\n")
    verify_cmdv1_result(version_result, "version")
    if args.expect_version and args.expect_version not in version_result.text:
        raise RuntimeError(f"expected version marker not found: {args.expect_version}")

    status_result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["status"],
    )
    print(status_result.text, end="" if status_result.text.endswith("\n") else "\n")
    verify_cmdv1_result(status_result, "status")

    log("cmdv1 verify passed: version/status rc=0 status=ok")
    return version_result.text + status_result.text


def adb_shell_text(adb: str,
                   serial: str | None,
                   shell_command: str,
                   *,
                   check: bool = False) -> str:
    result = run_command(
        adb_base(adb, serial) + ["shell", shell_command],
        check=check,
        capture=True,
    )
    return (result.stdout + result.stderr).strip()


def verify_android_adb(args: argparse.Namespace) -> str:
    serial, state = wait_for_adb_state(
        args.adb,
        args.serial,
        {"device"},
        args.android_timeout,
    )
    if state != "device":
        raise RuntimeError(f"expected Android device ADB state, got {state}")

    deadline = time.monotonic() + args.android_timeout
    last_props = ""
    while time.monotonic() < deadline:
        sys_boot_completed = adb_shell_text(args.adb, serial, "getprop sys.boot_completed")
        dev_bootcomplete = adb_shell_text(args.adb, serial, "getprop dev.bootcomplete")
        last_props = (
            f"sys.boot_completed={sys_boot_completed!r} "
            f"dev.bootcomplete={dev_bootcomplete!r}"
        )
        if sys_boot_completed == "1" or dev_bootcomplete == "1":
            log(f"Android boot-complete observed: {last_props}")
            break
        time.sleep(2.0)
    else:
        raise RuntimeError(f"Android boot-complete timeout: {last_props}")

    root_text = ""
    if args.android_root_check:
        root_text = adb_shell_text(args.adb, serial, "su -c id", check=False)
        if "uid=0" not in root_text:
            raise RuntimeError(f"Android root check failed: {root_text!r}")
        log("Android root check passed: su -c id contains uid=0")

    summary = f"android_adb serial={serial} {last_props}"
    if root_text:
        summary += f" root={root_text}"
    print(summary)
    return summary


def verify_post_flash_target(args: argparse.Namespace) -> str:
    if args.post_flash_target == "native-init":
        return verify_native_init(args)
    if args.post_flash_target == "android-adb":
        return verify_android_adb(args)
    raise RuntimeError(f"unknown post-flash target: {args.post_flash_target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flash a native init boot image from TWRP and verify it through the serial bridge."
    )
    parser.add_argument("boot_image", nargs="?", help="boot image to flash")
    parser.add_argument("--adb", default="adb", help="adb executable to use")
    parser.add_argument("--serial", help="ADB serial to target")
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--boot-block", default="/dev/block/by-name/boot")
    parser.add_argument("--bridge-host", default=DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--recovery-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=180.0)
    parser.add_argument("--expect-version", help="string expected in the native init version output")
    parser.add_argument("--expect-sha256", help="expected SHA256 of the local boot image")
    parser.add_argument(
        "--expect-readback-sha256",
        help="expected SHA256 of the flashed boot block prefix; defaults to --expect-sha256",
    )
    parser.add_argument(
        "--allow-unpinned-image",
        action="store_true",
        help="allow flashing without --expect-sha256; intended only for explicit local experiments",
    )
    parser.add_argument(
        "--verify-protocol",
        choices=("auto", "cmdv1", "raw", "selftest"),
        default="auto",
        help="post-boot verification method; auto tries cmdv1 first and falls back to raw version",
    )
    parser.add_argument(
        "--from-native",
        action="store_true",
        help="first ask the currently running native init shell to reboot to recovery",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="only verify the selected --post-flash-target without flashing",
    )
    parser.add_argument(
        "--post-flash-target",
        choices=("native-init", "android-adb"),
        default="native-init",
        help="post-reboot verification target; native-init keeps the historical serial bridge check",
    )
    parser.add_argument(
        "--android-timeout",
        type=float,
        default=300.0,
        help="timeout for Android ADB device and boot-complete checks when --post-flash-target=android-adb",
    )
    parser.add_argument(
        "--android-root-check",
        action="store_true",
        help="after Android boot-complete, require 'adb shell su -c id' to report uid=0",
    )
    parser.add_argument(
        "--expect-android-magic",
        action="store_true",
        help="require the local image to start with the Android boot image magic before flashing",
    )
    parser.add_argument(
        "--experimental-self-write",
        action="store_true",
        help="prepare the post-F3 self-write host path; live writes are fail-closed until F4 is authorized",
    )
    parser.add_argument(
        "--self-write-plan-only",
        action="store_true",
        help="with --experimental-self-write, print the self-write plan and perform no device action",
    )
    parser.add_argument(
        "--self-write-staging-dir",
        default=DEFAULT_SELF_WRITE_STAGING_DIR,
        help="approved device staging directory for the experimental self-write path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.expect_sha256 = normalize_sha256(args.expect_sha256, label="--expect-sha256")
    args.expect_readback_sha256 = normalize_sha256(
        args.expect_readback_sha256,
        label="--expect-readback-sha256",
    )

    with phase_timer("total"):
        if args.verify_only:
            with phase_timer(f"verify_{args.post_flash_target.replace('-', '_')}"):
                verify_post_flash_target(args)
            return 0

        if not args.boot_image:
            raise SystemExit("boot_image is required unless --verify-only is used")
        if not args.expect_sha256 and not args.allow_unpinned_image:
            raise SystemExit("refusing to flash without --expect-sha256")
        if args.allow_unpinned_image:
            log("unsafe override active: flashing without caller-pinned expected sha256")

        with phase_timer("inspect_local_image"):
            image_path, local_hash, image_size = inspect_local_image(args)

        if args.experimental_self_write:
            with phase_timer("experimental_self_write"):
                return run_experimental_self_write(args, image_path, local_hash, image_size)

        if args.from_native:
            with phase_timer("native_to_recovery"):
                reboot_native_to_recovery(args)

        with phase_timer("wait_recovery_adb"):
            serial, state = wait_for_adb_state(args.adb, args.serial, {"recovery"}, args.recovery_timeout)
        if state != "recovery":
            raise RuntimeError(f"expected recovery state, got {state}")

        with sealed_local_image_copy(image_path, local_hash, image_size) as sealed_image_path:
            with phase_timer("flash_boot_image"):
                flash_boot_image(args, serial, sealed_image_path, local_hash, image_size)
        with phase_timer("reboot_twrp_to_system"):
            reboot_twrp_to_system(args, serial)
        with phase_timer(f"verify_{args.post_flash_target.replace('-', '_')}"):
            verify_post_flash_target(args)
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("interrupted")
        raise SystemExit(130)
    except Exception as exc:
        log(f"error: {exc}")
        raise SystemExit(1)
