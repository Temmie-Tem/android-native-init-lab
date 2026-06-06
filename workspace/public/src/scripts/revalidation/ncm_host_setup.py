#!/usr/bin/env python3

import argparse
import ipaddress
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import dataclass

from a90ctl import ProtocolResult, run_cmdv1_command, shell_command_to_argv


DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_DEVICE_HELPER = "/cache/bin/a90_usbnet"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_HOST_IP = "192.168.7.1"
DEFAULT_PREFIX = 24

HOST_ADDR_RE = re.compile(r"^ncm\.host_addr:\s*([0-9a-fA-F:]{17})\s*$", re.MULTILINE)
DEV_ADDR_RE = re.compile(r"^ncm\.dev_addr:\s*([0-9a-fA-F:]{17})\s*$", re.MULTILINE)
IFNAME_RE = re.compile(r"^ncm\.ifname:\s*(\S+)\s*$", re.MULTILINE)
CMDV1_END_MISSING_TEXT = "A90P1 END marker not found"
HOST_IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass
class UsbnetStatus:
    ifname: str | None
    dev_addr: str | None
    host_addr: str | None
    raw: str


def log(message: str) -> None:
    print(f"[ncm] {message}", file=sys.stderr, flush=True)


def bridge_command(host: str,
                   port: int,
                   command: str,
                   timeout_sec: float,
                   markers: tuple[bytes, ...] = (b"[done]", b"[err]", b"[busy]")) -> str:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0) as sock:
                sock.settimeout(0.25)
                sock.sendall(("\n" + command + "\n").encode())
                data = bytearray()
                read_deadline = time.monotonic() + min(10.0, max(3.0, timeout_sec))
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


def cmdv1_unavailable(exc: Exception) -> bool:
    if isinstance(exc, OSError):
        return True
    text = str(exc)
    return CMDV1_END_MISSING_TEXT in text or "cmdv1 cannot safely encode command" in text


def run_device_cmdv1(args: argparse.Namespace,
                     command: str,
                     timeout_sec: float) -> ProtocolResult:
    argv = shell_command_to_argv(command)
    if argv is None:
        raise RuntimeError(f"cmdv1 cannot parse shell command: {command!r}")
    return run_cmdv1_command(args.bridge_host, args.bridge_port, timeout_sec, argv)


def device_command(args: argparse.Namespace,
                   command: str,
                   *,
                   timeout: float | None = None,
                   allow_error: bool = False,
                   use_cmdv1: bool = True) -> str:
    timeout_sec = args.bridge_timeout if timeout is None else timeout
    cmdv1_enabled = use_cmdv1 and args.device_protocol != "raw"
    cmdv1_failed_open = False

    for attempt in range(1, args.busy_retries + 1):
        if cmdv1_enabled and not cmdv1_failed_open:
            try:
                result = run_device_cmdv1(args, command, timeout_sec)
            except (RuntimeError, OSError) as exc:
                if args.device_protocol == "cmdv1" or not cmdv1_unavailable(exc):
                    raise
                log(f"cmdv1 unavailable for {command!r}; falling back to raw bridge")
                cmdv1_failed_open = True
            else:
                output = result.text
                if result.status != "busy":
                    if (result.rc != 0 or result.status != "ok") and not allow_error:
                        raise RuntimeError(
                            f"device command failed: {command} "
                            f"rc={result.rc} status={result.status}\n{output}"
                        )
                    return output

                print(output, end="" if output.endswith("\n") else "\n")
                log(f"auto menu active; requesting hide before retry {attempt}/{args.busy_retries}")
                hide_output = bridge_command(
                    args.bridge_host,
                    args.bridge_port,
                    "hide",
                    timeout_sec,
                    markers=(b"[busy]", b"[done]", b"[err]"),
                )
                print(hide_output, end="" if hide_output.endswith("\n") else "\n")
                time.sleep(args.busy_retry_sleep)
                continue

        output = bridge_command(args.bridge_host, args.bridge_port, command, timeout_sec)
        if "[busy]" not in output:
            if "[err]" in output and not allow_error:
                raise RuntimeError(f"device command failed: {command}\n{output}")
            return output

        print(output, end="" if output.endswith("\n") else "\n")
        log(f"auto menu active; requesting hide before retry {attempt}/{args.busy_retries}")
        hide_output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "hide",
            timeout_sec,
            markers=(b"[busy]", b"[done]", b"[err]"),
        )
        print(hide_output, end="" if hide_output.endswith("\n") else "\n")
        time.sleep(args.busy_retry_sleep)

    raise RuntimeError(f"device command stayed busy after retries: {command}")


def parse_status(output: str) -> UsbnetStatus:
    ifname_match = IFNAME_RE.search(output)
    dev_match = DEV_ADDR_RE.search(output)
    host_match = HOST_ADDR_RE.search(output)
    return UsbnetStatus(
        ifname=ifname_match.group(1) if ifname_match else None,
        dev_addr=dev_match.group(1).lower() if dev_match else None,
        host_addr=host_match.group(1).lower() if host_match else None,
        raw=output,
    )


def get_usbnet_status(args: argparse.Namespace) -> UsbnetStatus:
    output = device_command(args, f"run {args.device_helper} status")
    print(output, end="" if output.endswith("\n") else "\n")
    return parse_status(output)


def prefix_to_netmask(prefix: int) -> str:
    network = ipaddress.IPv4Network(f"0.0.0.0/{prefix}")
    return str(network.netmask)


def sysfs_mac_for(interface: str) -> str | None:
    path = f"/sys/class/net/{interface}/address"
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return fp.read().strip().lower()
    except OSError:
        return None


def find_interface_by_mac(mac: str) -> str | None:
    mac = mac.lower()
    try:
        names = sorted(os.listdir("/sys/class/net"))
    except OSError:
        return None

    for name in names:
        if name == "lo":
            continue
        if sysfs_mac_for(name) == mac:
            return name
    return None


def wait_for_interface_by_mac(mac: str, timeout_sec: float) -> str:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        interface = find_interface_by_mac(mac)
        if interface is not None:
            return interface
        time.sleep(0.5)
    raise RuntimeError(f"host interface with MAC {mac} was not found")


def validate_host_interface_name(interface: str) -> None:
    if not HOST_IFACE_RE.fullmatch(interface) or interface in {".", ".."}:
        raise RuntimeError(f"unsafe host interface name: {interface!r}")
    if not os.path.exists(f"/sys/class/net/{interface}"):
        raise RuntimeError(f"host interface does not exist: {interface}")


def select_host_interface(args: argparse.Namespace, status: UsbnetStatus) -> str:
    if args.interface:
        validate_host_interface_name(args.interface)
        actual_mac = sysfs_mac_for(args.interface)
        if status.host_addr and actual_mac and actual_mac != status.host_addr:
            raise RuntimeError(
                f"host interface {args.interface} MAC {actual_mac} does not match "
                f"device-reported NCM host_addr {status.host_addr}"
            )
        return args.interface

    if not args.allow_auto_interface:
        raise RuntimeError(
            "refusing sudo host NIC configuration from device-reported MAC; "
            "pass --interface <ifname> or opt in with --allow-auto-interface"
        )

    if not status.host_addr:
        raise RuntimeError("device NCM host_addr was not reported")
    log(f"waiting for host interface with MAC {status.host_addr}")
    return wait_for_interface_by_mac(status.host_addr, args.interface_timeout)


def sudo_prefix(args: argparse.Namespace) -> list[str]:
    if args.no_sudo or os.geteuid() == 0:
        return []
    return shlex.split(args.sudo)


def run_host_command(args: argparse.Namespace,
                     command: list[str],
                     *,
                     use_sudo: bool = False) -> None:
    full_command = (sudo_prefix(args) if use_sudo else []) + command
    print("+ " + shlex.join(full_command), flush=True)
    result = subprocess.run(full_command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"host command failed rc={result.returncode}: {shlex.join(full_command)}")


def interface_has_addr(interface: str, cidr: str) -> bool:
    result = subprocess.run(
        ["ip", "-4", "-o", "addr", "show", "dev", interface],
        text=True,
        capture_output=True,
        check=False,
    )
    return cidr in result.stdout


def wait_for_host_addr(interface: str, cidr: str, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if interface_has_addr(interface, cidr):
            log(f"host {interface} now has {cidr}")
            return
        time.sleep(1.0)
    raise RuntimeError(f"host interface {interface} did not receive {cidr}")


def print_required_host_commands(interface: str, cidr: str) -> None:
    print("\nHost IP setup required:", file=sys.stderr)
    print(f"  sudo ip addr replace {cidr} dev {interface}", file=sys.stderr)
    print(f"  sudo ip link set {interface} up", file=sys.stderr)


def configure_host_interface(args: argparse.Namespace, interface: str) -> None:
    cidr = f"{args.host_ip}/{args.prefix}"
    if interface_has_addr(interface, cidr):
        log(f"host {interface} already has {cidr}")
        return

    for command in (
        ["ip", "addr", "replace", cidr, "dev", interface],
        ["ip", "link", "set", interface, "up"],
    ):
        try:
            run_host_command(args, command, use_sudo=True)
        except RuntimeError:
            print_required_host_commands(interface, cidr)
            if not args.manual_host_config:
                raise
            log("waiting for manual host IP setup; run the commands above in another terminal")
            wait_for_host_addr(interface, cidr, args.manual_host_timeout)
            return


def run_ping(args: argparse.Namespace) -> None:
    command = [
        "ping",
        "-c",
        str(args.ping_count),
        "-W",
        str(args.ping_timeout),
        args.device_ip,
    ]
    run_host_command(args, command)


def command_setup(args: argparse.Namespace) -> int:
    log("checking device NCM state")
    status = get_usbnet_status(args)
    if status.ifname and status.host_addr:
        log(f"device NCM already active: {status.ifname}")
    else:
        log("enabling persistent NCM on device")
        try:
            output = device_command(args, f"run {args.device_helper} ncm")
            print(output, end="" if output.endswith("\n") else "\n")
        except RuntimeError as exc:
            log(f"NCM enable output was not conclusive; checking status next: {exc}")
        status = get_usbnet_status(args)

    if not status.ifname:
        raise RuntimeError("device NCM ifname was not reported")
    if not status.host_addr:
        raise RuntimeError("device NCM host_addr was not reported")

    netmask = prefix_to_netmask(args.prefix)
    log(f"setting device {status.ifname} to {args.device_ip}/{args.prefix}")
    output = device_command(
        args,
        f"run {args.toybox} ifconfig {status.ifname} {args.device_ip} netmask {netmask} up",
    )
    print(output, end="" if output.endswith("\n") else "\n")

    interface = select_host_interface(args, status)
    log(f"host interface: {interface}")

    configure_host_interface(args, interface)

    log(f"pinging device {args.device_ip}")
    run_ping(args)
    log("NCM setup complete")
    return 0


def command_status(args: argparse.Namespace) -> int:
    status = get_usbnet_status(args)
    if status.host_addr:
        interface = find_interface_by_mac(status.host_addr)
        if interface:
            log(f"host interface: {interface} ({status.host_addr})")
        else:
            log(f"host interface not found for MAC {status.host_addr}")
    else:
        log("NCM host_addr not present in helper status")
    return 0


def command_ping(args: argparse.Namespace) -> int:
    run_ping(args)
    return 0


def command_off(args: argparse.Namespace) -> int:
    log("turning USB network off; ACM serial should come back")
    try:
        output = device_command(
            args,
            f"run {args.device_helper} off",
            timeout=args.bridge_timeout,
            use_cmdv1=False,
        )
        print(output, end="" if output.endswith("\n") else "\n")
    except RuntimeError as exc:
        log(f"off command output was interrupted by USB re-enumeration: {exc}")

    time.sleep(args.reattach_sleep)
    output = device_command(
        args,
        "version",
        timeout=args.bridge_timeout,
        allow_error=False,
    )
    print(output, end="" if output.endswith("\n") else "\n")
    log("ACM serial responded after rollback")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set up and validate the A90 native-init USB NCM host link."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("setup", "status", "ping", "off"),
        default="setup",
    )
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument(
        "--device-protocol",
        choices=("auto", "cmdv1", "raw"),
        default="auto",
        help="device shell command protocol; auto tries cmdv1 then raw fallback",
    )
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--device-helper", default=DEFAULT_DEVICE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--host-ip", default=DEFAULT_HOST_IP)
    parser.add_argument("--prefix", type=int, default=DEFAULT_PREFIX)
    parser.add_argument("--interface-timeout", type=float, default=20.0)
    parser.add_argument("--interface", help="explicit host NCM interface to configure")
    parser.add_argument(
        "--allow-auto-interface",
        action="store_true",
        help=(
            "diagnostic fallback only: allow selecting the sudo target interface "
            "from device-reported NCM MAC; prefer --interface on multi-NIC hosts"
        ),
    )
    parser.add_argument("--ping-count", type=int, default=3)
    parser.add_argument("--ping-timeout", type=int, default=2)
    parser.add_argument("--reattach-sleep", type=float, default=3.0)
    parser.add_argument("--sudo", default="sudo")
    parser.add_argument("--no-sudo", action="store_true")
    parser.add_argument(
        "--manual-host-config",
        action="store_true",
        help="if sudo host IP setup fails, print commands and wait for manual setup",
    )
    parser.add_argument("--manual-host-timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "setup":
        return command_setup(args)
    if args.command == "status":
        return command_status(args)
    if args.command == "ping":
        return command_ping(args)
    if args.command == "off":
        return command_off(args)

    raise AssertionError(args.command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
