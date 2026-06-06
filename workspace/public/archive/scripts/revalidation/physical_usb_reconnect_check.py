#!/usr/bin/env python3

import argparse
import glob
import time

from netservice_reconnect_soak import (
    add_common_args,
    get_usbnet_status,
    netservice_status,
    start_netservice,
    stop_netservice,
    verify_ncm_and_tcp,
    wait_for_bridge_version,
    wait_for_interface_by_mac,
)


def log(message: str) -> None:
    print(f"[physical-usb] {message}", flush=True)


def acm_devices() -> set[str]:
    return set(sorted(glob.glob("/dev/ttyACM*")))


def wait_for_acm_disconnect(initial_devices: set[str], timeout_sec: float) -> None:
    if not initial_devices:
        log("no initial /dev/ttyACM* device; skipping disconnect detection")
        return

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        current = acm_devices()
        if initial_devices.isdisjoint(current):
            log(f"ACM disconnected; current devices: {sorted(current) or '<none>'}")
            return
        time.sleep(0.5)

    raise RuntimeError(
        f"ACM did not disappear within {timeout_sec:.1f}s; "
        f"still present: {sorted(initial_devices & acm_devices())}"
    )


def wait_for_bridge_after_replug(args: argparse.Namespace) -> str:
    log("waiting for bridge/native init after replug")
    output = wait_for_bridge_version(args)
    if "A90 Linux init" not in output:
        raise RuntimeError(f"bridge returned unexpected output:\n{output}")
    return output


def netservice_is_ready(status_output: str) -> bool:
    return "ncm0=present" in status_output and "tcpctl=running" in status_output


def ensure_netservice_ready(args: argparse.Namespace) -> bool:
    log("checking netservice state")
    status_output = netservice_status(args)
    if netservice_is_ready(status_output):
        log("netservice already running")
        return False

    log("netservice is not running; starting it before physical reconnect")
    start_netservice(args)
    verify_ncm_and_tcp(args)
    return True


def print_replug_instruction(args: argparse.Namespace, initial_devices: set[str]) -> None:
    log("READY: unplug the A90 USB cable now, then plug it back in")
    log(f"initial ACM devices: {sorted(initial_devices) or '<none>'}")
    log(f"disconnect timeout: {args.disconnect_timeout:.0f}s")
    log(f"reconnect timeout: {args.bridge_ready_timeout:.0f}s")


def verify_post_replug(args: argparse.Namespace) -> None:
    log("checking USB NCM status after replug")
    status = get_usbnet_status(args)
    if status.host_addr:
        interface = wait_for_interface_by_mac(status.host_addr, args.interface_timeout)
        log(f"host NCM interface after replug: {interface} ({status.host_addr})")
    verify_ncm_and_tcp(args)


def run_once(args: argparse.Namespace) -> int:
    started_netservice = False
    try:
        print(wait_for_bridge_version(args), end="")
        started_netservice = ensure_netservice_ready(args)

        initial_devices = acm_devices()
        print_replug_instruction(args, initial_devices)
        wait_for_acm_disconnect(initial_devices, args.disconnect_timeout)
        time.sleep(args.post_disconnect_sleep)

        print(wait_for_bridge_after_replug(args), end="")
        time.sleep(args.post_replug_sleep)
        verify_post_replug(args)

        log("PASS: ACM bridge, NCM ping, and tcpctl survived physical reconnect")
        return 0
    finally:
        if started_netservice and not args.leave_running:
            log("restoring ACM-only state because this script started netservice")
            stop_netservice(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate A90 native-init recovery after a real USB cable unplug/replug. "
            "Run this, unplug when READY appears, then plug the cable back in."
        )
    )
    add_common_args(parser)
    parser.add_argument("--disconnect-timeout", type=float, default=120.0)
    parser.add_argument("--post-disconnect-sleep", type=float, default=1.0)
    parser.add_argument("--post-replug-sleep", type=float, default=3.0)
    parser.add_argument(
        "--leave-running",
        action="store_true",
        help="leave netservice running if this script had to start it",
    )
    return parser.parse_args()


def main() -> int:
    return run_once(parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[physical-usb] interrupted")
        raise SystemExit(130)
