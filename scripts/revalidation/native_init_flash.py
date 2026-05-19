#!/usr/bin/env python3

import argparse
import hashlib
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

from a90ctl import ProtocolResult, run_cmdv1_command


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_REMOTE_IMAGE = "/tmp/native_init_boot.img"
BOOT_READBACK_BLOCK_SIZE = 4096


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[native-init-flash {timestamp}] {message}", file=sys.stderr, flush=True)


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
    if not image_path.is_file():
        raise FileNotFoundError(image_path)

    image_size = image_path.stat().st_size
    if image_size <= 0:
        raise RuntimeError(f"boot image is empty: {image_path}")
    if image_size % BOOT_READBACK_BLOCK_SIZE != 0:
        raise RuntimeError(
            f"boot image size is not {BOOT_READBACK_BLOCK_SIZE}-byte aligned: "
            f"{image_size}"
        )

    if args.expect_version:
        needle = args.expect_version.encode()
        if not file_contains(image_path, needle):
            raise RuntimeError(
                f"expected version marker not found in local image before reboot: "
                f"{args.expect_version}"
            )
        log(f"local image contains expected marker: {args.expect_version}")

    local_hash = local_sha256(image_path)
    log(f"local image size: {image_size}")
    log(f"local image sha256: {local_hash}")
    return image_path, local_hash, image_size


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
                sock.sendall(("\n" + command + "\n").encode())
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
    remote = quote_remote_path(args.remote_image, label="remote image")
    block = quote_remote_path(args.boot_block, label="boot block")

    run_command(adb_base(args.adb, serial) + ["push", str(image_path), args.remote_image])

    remote_hash = remote_sha256(args.adb, serial, args.remote_image)
    log(f"remote image sha256: {remote_hash}")
    if remote_hash != local_hash:
        raise RuntimeError("remote sha256 mismatch after adb push")

    flash_cmd = (
        f"dd if={remote} of={block} "
        "bs=4M conv=fsync && sync"
    )
    run_command(adb_base(args.adb, serial) + ["shell", flash_cmd])

    boot_prefix_hash = remote_boot_prefix_sha256(args.adb, serial, args.boot_block, image_size)
    log(f"boot block prefix sha256: {boot_prefix_hash}")
    if boot_prefix_hash != local_hash:
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
    parser.add_argument(
        "--verify-protocol",
        choices=("auto", "cmdv1", "raw"),
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
        help="only verify the running native init through the bridge",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.verify_only:
        verify_native_init(args)
        return 0

    if not args.boot_image:
        raise SystemExit("boot_image is required unless --verify-only is used")

    image_path, local_hash, image_size = inspect_local_image(args)

    if args.from_native:
        reboot_native_to_recovery(args)

    serial, state = wait_for_adb_state(args.adb, args.serial, {"recovery"}, args.recovery_timeout)
    if state != "recovery":
        raise RuntimeError(f"expected recovery state, got {state}")

    flash_boot_image(args, serial, image_path, local_hash, image_size)
    reboot_twrp_to_system(args, serial)
    verify_native_init(args)
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
