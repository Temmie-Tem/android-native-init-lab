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
DEFAULT_TCP_PORT = 2325
DEFAULT_TOKEN_COMMAND = "netservice token show"

HOST_ADDR_RE = re.compile(r"^ncm\.host_addr:\s*([0-9a-fA-F:]{17})\s*$", re.MULTILINE)
DEV_ADDR_RE = re.compile(r"^ncm\.dev_addr:\s*([0-9a-fA-F:]{17})\s*$", re.MULTILINE)
IFNAME_RE = re.compile(r"^ncm\.ifname:\s*(\S+)\s*$", re.MULTILINE)
CMDV1_END_MISSING_TEXT = "A90P1 END marker not found"
TOKEN_RE = re.compile(r"tcpctl_token=([0-9A-Fa-f]{32})")
HOST_IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass
class UsbnetStatus:
    ifname: str | None
    dev_addr: str | None
    host_addr: str | None
    raw: str


def log(message: str) -> None:
    print(f"[reconnect] {message}", file=sys.stderr, flush=True)


def bridge_command(args: argparse.Namespace,
                   command: str,
                   *,
                   timeout: float | None = None,
                   markers: tuple[bytes, ...] = (b"[done]", b"[err]", b"[busy]"),
                   tolerate_disconnect: bool = False) -> str:
    timeout_sec = args.bridge_timeout if timeout is None else timeout
    deadline = time.monotonic() + timeout_sec
    data = bytearray()
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((args.bridge_host, args.bridge_port), timeout=2.0) as sock:
                sock.settimeout(0.25)
                sock.sendall(("\n" + command.rstrip("\n") + "\n").encode())
                read_deadline = time.monotonic() + min(15.0, max(3.0, timeout_sec))
                while time.monotonic() < read_deadline:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        if tolerate_disconnect and data:
                            return data.decode("utf-8", errors="replace")
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
            if tolerate_disconnect and data:
                return data.decode("utf-8", errors="replace")

        time.sleep(0.5)

    raise RuntimeError(f"bridge command timeout for {command!r}: {last_error}")


def cmdv1_unavailable(exc: Exception) -> bool:
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
                   tolerate_disconnect: bool = False,
                   use_cmdv1: bool = True) -> str:
    timeout_sec = args.bridge_timeout if timeout is None else timeout
    cmdv1_enabled = use_cmdv1 and not tolerate_disconnect and args.device_protocol != "raw"
    cmdv1_failed_open = False

    for attempt in range(1, args.busy_retries + 1):
        if cmdv1_enabled and not cmdv1_failed_open:
            try:
                result = run_device_cmdv1(args, command, timeout_sec)
            except RuntimeError as exc:
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
                try:
                    hide_output = bridge_command(args, "hide", timeout=timeout_sec)
                    print(hide_output, end="" if hide_output.endswith("\n") else "\n")
                except RuntimeError:
                    pass
                time.sleep(args.busy_retry_sleep)
                continue

        output = bridge_command(
            args,
            command,
            timeout=timeout_sec,
            tolerate_disconnect=tolerate_disconnect,
        )
        if "[busy]" not in output:
            if "[err]" in output and "[done]" not in output and not allow_error:
                raise RuntimeError(f"device command failed: {command}\n{output}")
            return output

        print(output, end="" if output.endswith("\n") else "\n")
        log(f"auto menu active; requesting hide before retry {attempt}/{args.busy_retries}")
        try:
            hide_output = bridge_command(args, "hide", timeout=timeout)
            print(hide_output, end="" if hide_output.endswith("\n") else "\n")
        except RuntimeError:
            pass
        time.sleep(args.busy_retry_sleep)

    raise RuntimeError(f"device command stayed busy after retries: {command}")


def parse_usbnet_status(output: str) -> UsbnetStatus:
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
    output = device_command(args, f"run {args.device_helper} status", timeout=20.0)
    print(output, end="" if output.endswith("\n") else "\n")
    return parse_usbnet_status(output)


def sysfs_mac_for(interface: str) -> str | None:
    try:
        with open(f"/sys/class/net/{interface}/address", "r", encoding="utf-8") as fp:
            return fp.read().strip().lower()
    except OSError:
        return None


def find_interface_by_mac(mac: str) -> str | None:
    try:
        names = sorted(os.listdir("/sys/class/net"))
    except OSError:
        return None

    for name in names:
        if name == "lo":
            continue
        if sysfs_mac_for(name) == mac.lower():
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
    return wait_for_interface_by_mac(status.host_addr, args.interface_timeout)


def prefix_to_netmask(prefix: int) -> str:
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)


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


def sudo_command(args: argparse.Namespace, command: list[str]) -> list[str]:
    if os.geteuid() == 0 or args.no_sudo:
        return command
    return shlex.split(args.sudo) + command


def configure_host_interface(args: argparse.Namespace, interface: str) -> None:
    cidr = f"{args.host_ip}/{args.prefix}"
    if interface_has_addr(interface, cidr):
        log(f"host {interface} already has {cidr}")
        return

    commands = [
        ["ip", "addr", "replace", cidr, "dev", interface],
        ["ip", "link", "set", interface, "up"],
    ]

    if args.no_configure_host:
        print_required_host_commands(interface, cidr)
        raise RuntimeError(f"host interface {interface} does not have {cidr}")

    for command in commands:
        full_command = sudo_command(args, command)
        print("+ " + shlex.join(full_command), flush=True)
        result = subprocess.run(full_command, check=False)
        if result.returncode != 0:
            print_required_host_commands(interface, cidr)
            if args.manual_host_config:
                log(
                    "waiting for manual host IP setup; run the commands above in another terminal"
                )
                wait_for_host_addr(interface, cidr, args.manual_host_timeout)
                return
            raise RuntimeError(
                f"host command failed rc={result.returncode}: {shlex.join(full_command)}"
            )


def print_required_host_commands(interface: str, cidr: str) -> None:
    print("\nHost IP setup required:", file=sys.stderr)
    print(f"  sudo ip addr replace {cidr} dev {interface}", file=sys.stderr)
    print(f"  sudo ip link set {interface} up", file=sys.stderr)


def host_ping(args: argparse.Namespace) -> str:
    result = subprocess.run(
        ["ping", "-c", str(args.ping_count), "-W", str(args.ping_timeout), args.device_ip],
        text=True,
        capture_output=True,
        check=False,
        timeout=max(5.0, args.ping_count * (args.ping_timeout + 1.0)),
    )
    output = result.stdout
    if result.stderr:
        output += result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"ping failed rc={result.returncode}\n{output}")
    return output


def tcpctl_request(args: argparse.Namespace, command: str, timeout: float | None = None) -> str:
    timeout_sec = args.tcp_timeout if timeout is None else timeout
    payload = command.rstrip("\n") + "\n"
    if not args.no_auth and tcpctl_command_requires_auth(command):
        payload = f"auth {get_tcpctl_token(args)}\n{payload}"
    with socket.create_connection((args.device_ip, args.tcp_port), timeout=timeout_sec) as sock:
        sock.settimeout(0.5)
        sock.sendall(payload.encode())
        data = bytearray()
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                continue
            if not chunk:
                break
            data.extend(chunk)
    return data.decode("utf-8", errors="replace")


def parse_tcpctl_token(output: str) -> str:
    match = TOKEN_RE.search(output)
    if not match:
        raise RuntimeError(f"tcpctl token was not found in output:\n{output}")
    return match.group(1)


def tcpctl_command_requires_auth(command: str) -> bool:
    word = command.lstrip().split(maxsplit=1)[0] if command.strip() else ""
    return word in {"run", "shutdown"}


def get_tcpctl_token(args: argparse.Namespace) -> str:
    cached = getattr(args, "_tcpctl_token", None)
    if cached:
        return cached
    if args.token:
        args._tcpctl_token = args.token
        return args.token
    output = device_command(args, args.token_command, timeout=args.bridge_timeout)
    token = parse_tcpctl_token(output)
    args._tcpctl_token = token
    return token


def wait_for_tcpctl(args: argparse.Namespace) -> str:
    deadline = time.monotonic() + args.tcp_ready_timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            output = tcpctl_request(args, "ping", timeout=2.0)
            if "pong" in output and "OK" in output:
                return output
        except OSError as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"tcpctl did not become ready: {last_error}")


def wait_for_bridge_version(args: argparse.Namespace) -> str:
    deadline = time.monotonic() + args.bridge_ready_timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            output = device_command(args, "version", timeout=5.0)
            if "A90 Linux init" in output:
                return output
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"bridge did not recover: {last_error}")


def netservice_status(args: argparse.Namespace) -> str:
    output = device_command(args, "netservice status", timeout=8.0)
    print(output, end="" if output.endswith("\n") else "\n")
    return output


def start_netservice(args: argparse.Namespace) -> None:
    log("starting netservice; USB may re-enumerate")
    try:
        output = device_command(
            args,
            "netservice start",
            timeout=args.netservice_timeout,
            tolerate_disconnect=True,
            use_cmdv1=False,
        )
        print(output, end="" if output.endswith("\n") else "\n")
    except RuntimeError as exc:
        log(f"netservice start output interrupted; checking state next: {exc}")

    wait_for_bridge_version(args)
    status_output = netservice_status(args)
    if "ncm0=present" not in status_output or "tcpctl=running" not in status_output:
        raise RuntimeError(f"netservice did not report ready:\n{status_output}")


def stop_netservice(args: argparse.Namespace) -> None:
    log("stopping netservice; USB may re-enumerate")
    try:
        output = device_command(
            args,
            "netservice stop",
            timeout=args.netservice_timeout,
            tolerate_disconnect=True,
            allow_error=True,
            use_cmdv1=False,
        )
        print(output, end="" if output.endswith("\n") else "\n")
    except RuntimeError as exc:
        log(f"netservice stop output interrupted; checking bridge next: {exc}")

    wait_for_bridge_version(args)
    status_output = netservice_status(args)
    if "ncm0=absent" not in status_output or "tcpctl=stopped" not in status_output:
        raise RuntimeError(f"netservice did not stop cleanly:\n{status_output}")


def verify_ncm_and_tcp(args: argparse.Namespace) -> None:
    status = get_usbnet_status(args)
    if not status.ifname:
        log("device NCM ifname was not reported; using v60 netservice default ncm0")
        status.ifname = "ncm0"
    if not status.host_addr:
        raise RuntimeError("device NCM host_addr was not reported")

    netmask = prefix_to_netmask(args.prefix)
    output = device_command(
        args,
        f"run {args.toybox} ifconfig {status.ifname} {args.device_ip} netmask {netmask} up",
        timeout=10.0,
    )
    print(output, end="" if output.endswith("\n") else "\n")

    interface = select_host_interface(args, status)
    log(f"host interface: {interface} ({status.host_addr})")
    configure_host_interface(args, interface)

    print("--- ping ---")
    print(host_ping(args), end="")

    print("--- tcpctl ping ---")
    print(wait_for_tcpctl(args), end="")

    print("--- tcpctl status ---")
    status_output = tcpctl_request(args, "status")
    if "OK" not in status_output:
        raise RuntimeError(f"tcpctl status did not end OK:\n{status_output}")
    print(status_output, end="" if status_output.endswith("\n") else "\n")

    print("--- tcpctl run uptime ---")
    run_output = tcpctl_request(args, f"run {args.toybox} uptime")
    if "OK" not in run_output:
        raise RuntimeError(f"tcpctl run did not end OK:\n{run_output}")
    print(run_output, end="" if run_output.endswith("\n") else "\n")


def command_status(args: argparse.Namespace) -> int:
    print(wait_for_bridge_version(args), end="")
    netservice_status(args)
    try:
        get_usbnet_status(args)
    except Exception as exc:
        log(f"usbnet status unavailable: {exc}")
    return 0


def command_once(args: argparse.Namespace) -> int:
    try:
        print("=== stop/acm-only ===")
        stop_netservice(args)

        print("=== start/ncm+tcpctl ===")
        start_netservice(args)
        verify_ncm_and_tcp(args)
    finally:
        if not args.leave_running:
            print("=== final stop/acm-only ===")
            stop_netservice(args)
    return 0


def command_soak(args: argparse.Namespace) -> int:
    failures: list[str] = []
    for cycle in range(1, args.cycles + 1):
        print(f"=== cycle {cycle}/{args.cycles}: stop/acm-only ===", flush=True)
        try:
            stop_netservice(args)
            print(f"=== cycle {cycle}/{args.cycles}: start/ncm+tcpctl ===", flush=True)
            start_netservice(args)
            verify_ncm_and_tcp(args)
        except Exception as exc:
            failures.append(f"cycle {cycle}: {exc}")
            print(f"cycle {cycle}: FAIL {exc}", flush=True)
            if args.stop_on_failure:
                break

        time.sleep(args.cycle_sleep)

    if not args.leave_running:
        print("=== final stop/acm-only ===", flush=True)
        try:
            stop_netservice(args)
        except Exception as exc:
            failures.append(f"final stop: {exc}")

    print("=== summary ===")
    print(f"cycles requested: {args.cycles}")
    print(f"failures: {len(failures)}")
    for failure in failures:
        print(f"- {failure}")

    if failures:
        raise RuntimeError("netservice reconnect soak failed")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--bridge-ready-timeout", type=float, default=45.0)
    parser.add_argument(
        "--device-protocol",
        choices=("auto", "cmdv1", "raw"),
        default="auto",
        help="device shell command protocol; auto tries cmdv1 then raw fallback",
    )
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--netservice-timeout", type=float, default=45.0)
    parser.add_argument("--device-helper", default=DEFAULT_DEVICE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--host-ip", default=DEFAULT_HOST_IP)
    parser.add_argument("--prefix", type=int, default=DEFAULT_PREFIX)
    parser.add_argument("--interface-timeout", type=float, default=25.0)
    parser.add_argument("--interface", help="explicit host NCM interface to configure")
    parser.add_argument(
        "--allow-auto-interface",
        action="store_true",
        help="allow selecting the sudo target interface from device-reported NCM MAC",
    )
    parser.add_argument("--ping-count", type=int, default=3)
    parser.add_argument("--ping-timeout", type=int, default=2)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=8.0)
    parser.add_argument("--tcp-ready-timeout", type=float, default=15.0)
    parser.add_argument("--token", help="tcpctl auth token; defaults to reading it from native init")
    parser.add_argument("--token-command", default=DEFAULT_TOKEN_COMMAND)
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="use legacy unauthenticated tcpctl request mode",
    )
    parser.add_argument("--sudo", default="sudo -n")
    parser.add_argument("--no-sudo", action="store_true")
    parser.add_argument("--no-configure-host", action="store_true")
    parser.add_argument(
        "--manual-host-config",
        action="store_true",
        help="if sudo fails, print the current enx... commands and wait for manual setup",
    )
    parser.add_argument("--manual-host-timeout", type=float, default=120.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate A90 v60 netservice recovery across USB UDC re-enumeration cycles."
    )
    add_common_args(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="show bridge/netservice/usbnet status").set_defaults(
        func=command_status
    )

    once = subparsers.add_parser("once", help="run one stop -> start -> validate cycle")
    once.add_argument("--leave-running", action="store_true")
    once.set_defaults(func=command_once)

    soak = subparsers.add_parser("soak", help="run repeated stop/start validation cycles")
    soak.add_argument("--cycles", type=int, default=3)
    soak.add_argument("--cycle-sleep", type=float, default=2.0)
    soak.add_argument("--leave-running", action="store_true")
    soak.add_argument("--stop-on-failure", action="store_true")
    soak.set_defaults(func=command_soak)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
