#!/usr/bin/env python3
"""Guest-side dummy_hcd -> real Python CDC-ACM observer positive control."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import select
import stat
import sys
import termios
import time
import tty
from pathlib import Path
from typing import Any


CONFIG = Path("/p318-qemu-config.json")
OBSERVER = Path("/device_action_cdc_acm_observer_v1.py")
RAW_CAPTURE = Path("/device_action_raw_capture_v1.py")
RUN_DIR = Path("/run/p318-observer")
UDC = "dummy_udc.0"
UDC_ROOT = Path("/sys/class/udc") / UDC
TOPOLOGY = "usb:1-1"
TIMEOUT_SEC = 10


class GuestError(RuntimeError):
    pass


class HealthyFixtureGuard:
    """The kernel transport is real; only the root udev guard is synthetic."""

    def healthy(self, *, recheck: bool = False) -> bool:
        del recheck
        return True

    def matches_node(self, _node: Path) -> bool:
        return True


def load_observer():
    # init runs the interpreter with -I, so the script directory is not on
    # sys.path.  The observer is loaded by absolute path, but its own
    # module-scope import of the common raw-capture module is resolved through
    # sys.path, so the rootfs root has to be reachable for exactly that import.
    if str(RAW_CAPTURE.parent) not in sys.path:
        sys.path.insert(0, str(RAW_CAPTURE.parent))
    if not RAW_CAPTURE.is_file():
        raise GuestError("observer raw-capture dependency is absent")
    spec = importlib.util.spec_from_file_location("p318_qemu_real_observer", OBSERVER)
    if spec is None or spec.loader is None:
        raise GuestError("observer import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_config() -> dict[str, str]:
    value = json.loads(CONFIG.read_bytes())
    expected = {
        "banner_hex",
        "manufacturer",
        "product",
        "serial",
        "usb_product_id",
        "usb_vendor_id",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise GuestError("guest config shape mismatch")
    if (
        value["usb_vendor_id"] != "04e8"
        or value["usb_product_id"] != "6861"
        or value["manufacturer"] != "Android Native Init Lab"
        or value["product"] != "S22+ E3 ACM"
        or len(bytes.fromhex(value["banner_hex"])) != 49
        or len(value["serial"]) != 37
    ):
        raise GuestError("guest config identity mismatch")
    return value


def write_verify(path: Path, value: str) -> None:
    with path.open("w", encoding="ascii", newline="") as stream:
        amount = stream.write(value)
        stream.flush()
    if amount != len(value) or path.read_text(encoding="ascii").strip() != value:
        raise GuestError(f"configfs readback differs: {path.name}")


def create_gadget(config: dict[str, str]) -> None:
    root = Path("/config/usb_gadget/g1")
    directories = (
        root,
        root / "strings/0x409",
        root / "configs/b.1",
        root / "configs/b.1/strings/0x409",
        root / "functions/acm.usb0",
    )
    for path in directories:
        path.mkdir()
    attributes = (
        (root / "idVendor", "0x" + config["usb_vendor_id"]),
        (root / "idProduct", "0x" + config["usb_product_id"]),
        (root / "bcdUSB", "0x0200"),
        (root / "bcdDevice", "0x0003"),
        (root / "max_speed", "high-speed"),
        (root / "strings/0x409/manufacturer", config["manufacturer"]),
        (root / "strings/0x409/product", config["product"]),
        (root / "strings/0x409/serialnumber", config["serial"]),
        (root / "configs/b.1/bmAttributes", "0x80"),
        (root / "configs/b.1/MaxPower", "500"),
        (root / "configs/b.1/strings/0x409/configuration", "acm"),
    )
    for path, value in attributes:
        write_verify(path, value)
    link = root / "configs/b.1/acm.usb0"
    link.symlink_to(root / "functions/acm.usb0")
    if os.readlink(link) != "../../../../usb_gadget/g1/functions/acm.usb0":
        raise GuestError("configfs function link differs")


def wait_for(path: Path, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.01)
    raise GuestError(f"path timeout: {path}")


def open_ttygs0() -> int:
    dev_value = Path("/sys/class/tty/ttyGS0/dev")
    wait_for(dev_value, 5)
    match = dev_value.read_text(encoding="ascii").strip().split(":")
    if len(match) != 2 or any(not part.isdecimal() for part in match):
        raise GuestError("ttyGS0 device identity invalid")
    node = Path("/dev/ttyGS0")
    expected = os.makedev(int(match[0]), int(match[1]))
    if not node.exists():
        os.mknod(node, stat.S_IFCHR | 0o600, expected)
    if node.stat().st_rdev != expected:
        raise GuestError("ttyGS0 node identity mismatch")
    descriptor = os.open(
        node,
        os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
    )
    tty.setraw(descriptor, termios.TCSANOW)
    return descriptor


def write_all(descriptor: int, payload: bytes) -> None:
    deadline = time.monotonic() + 5.0
    offset = 0
    while offset < len(payload):
        if time.monotonic() >= deadline:
            raise GuestError("pre-bind banner deadline")
        try:
            amount = os.write(descriptor, payload[offset:])
        except (BlockingIOError, InterruptedError):
            amount = 0
        if amount < 0 or amount > len(payload) - offset:
            raise GuestError("pre-bind banner write invalid")
        offset += amount
        if amount == 0:
            select.select([], [descriptor], [], min(0.01, deadline - time.monotonic()))


def persist_session(observer: Any, config: dict[str, str]):
    spec = {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": config["usb_vendor_id"],
        "usb_product_id": config["usb_product_id"],
        "usb_serial": config["serial"],
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": config["banner_hex"],
    }
    RUN_DIR.mkdir()
    baseline = observer.capture_baseline(spec, TOPOLOGY)
    baseline_receipt = observer.persist_json(
        RUN_DIR / "candidate-observer-baseline.json", baseline
    )
    guard_value = {
        "schema": observer.GUARD_SCHEMA,
        "status": "armed",
        "spec_sha256": observer.digest(spec),
        "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
        "rule_sha256": hashlib.sha256(observer._guard_rule(spec, TOPOLOGY)).hexdigest(),
        "instance_sha256": "5" * 64,
        "output_sha256": "4" * 64,
        "child_alive": True,
    }
    guard_receipt = observer.persist_json(
        RUN_DIR / "candidate-observer-guard.json", guard_value
    )
    binding = {
        "approval_binding_sha256": "a" * 64,
        "bundle_sha256": "b" * 64,
        "manifest_id": "p318-qemu-e2e-positive-control",
        "candidate_ap_sha256": "c" * 64,
    }
    session = observer.ObserverSession(
        spec,
        TOPOLOGY,
        RUN_DIR,
        binding,
        baseline,
        baseline_receipt,
        HealthyFixtureGuard(),
        guard_receipt,
        Path("/sys/class/tty"),
        Path("/dev"),
    )
    return spec, binding, session


def child_observe(
    observer: Any,
    spec: dict[str, str],
    binding: dict[str, str],
    session: Any,
    ready: int,
    tty_descriptor: int,
) -> None:
    os.close(tty_descriptor)
    os.write(ready, b"R")
    os.close(ready)
    value = session.observe(
        timeout_sec=TIMEOUT_SEC,
        download_departure={
            "download_endpoint_absent": True,
            "absence_timed_out": False,
            "sequence": 1,
        },
    )
    reopened = observer.validate_receipt(
        RUN_DIR / "candidate-observer.json",
        spec=spec,
        binding=binding,
        topology=TOPOLOGY,
    )
    raw = (RUN_DIR / "candidate-observer.raw").read_bytes()
    expected = bytes.fromhex(spec["banner_hex"])
    if (
        value.get("classification") != "accepted"
        or reopened.get("accepted") is not True
        or raw != expected
    ):
        raise GuestError("real observer did not accept exact banner")
    print(
        "P318_QEMU observer=PASS classification=accepted "
        f"banner_bytes={len(raw)} banner_sha256={hashlib.sha256(raw).hexdigest()}",
        flush=True,
    )


def wait_ready(descriptor: int, child: int) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        readable, _, _ = select.select([descriptor], [], [], 0.05)
        if readable:
            if os.read(descriptor, 1) == b"R":
                return
            raise GuestError("observer ready pipe closed")
        status = os.waitpid(child, os.WNOHANG)
        if status != (0, 0):
            raise GuestError("observer exited before ready")
    raise GuestError("observer ready timeout")


def wait_configured() -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            state = (UDC_ROOT / "state").read_text(encoding="ascii").strip()
            speed = (UDC_ROOT / "current_speed").read_text(encoding="ascii").strip()
        except OSError:
            state = ""
            speed = ""
        if state == "configured" and speed == "high-speed":
            return
        time.sleep(0.01)
    raise GuestError("dummy UDC configuration timeout")


def wait_child(child: int) -> None:
    deadline = time.monotonic() + TIMEOUT_SEC + 2.0
    while time.monotonic() < deadline:
        pid, status = os.waitpid(child, os.WNOHANG)
        if pid == child:
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                raise GuestError("observer child failed")
            return
        time.sleep(0.02)
    os.kill(child, 9)
    os.waitpid(child, 0)
    raise GuestError("observer child timeout")


def run() -> None:
    config = load_config()
    observer = load_observer()
    create_gadget(config)
    tty_descriptor = open_ttygs0()
    banner = bytes.fromhex(config["banner_hex"])
    write_all(tty_descriptor, banner)
    print("P318_QEMU stage=pre-bind-banner status=PASS banner_bytes=49", flush=True)

    spec, binding, session = persist_session(observer, config)
    ready_read, ready_write = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(ready_read)
        try:
            child_observe(
                observer,
                spec,
                binding,
                session,
                ready_write,
                tty_descriptor,
            )
        except BaseException as exc:
            # The type alone cannot distinguish a missing guest tool from a real
            # classification failure, which cost one full control cycle to find.
            detail = str(exc).replace("\n", " ")[:200] or "(no detail)"
            print(
                f"P318_QEMU observer=FAIL error={type(exc).__name__} detail={detail}",
                flush=True,
            )
            os._exit(1)
        os._exit(0)

    os.close(ready_write)
    try:
        wait_ready(ready_read, child)
    finally:
        os.close(ready_read)
    write_verify(Path("/config/usb_gadget/g1/UDC"), UDC)
    wait_configured()
    print("P318_QEMU stage=dummy-configured status=PASS", flush=True)
    wait_child(child)
    os.close(tty_descriptor)
    print(
        "P318_QEMU result=PASS "
        "verdict=PASS_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0 banner_bytes=49",
        flush=True,
    )
    while True:
        time.sleep(3600.0)


if __name__ == "__main__":
    try:
        run()
    except BaseException as exc:
        detail = str(exc).replace("\n", " ")[:200] or "(no detail)"
        print(
            f"P318_QEMU result=FAIL error={type(exc).__name__} detail={detail}",
            flush=True,
        )
        raise SystemExit(1)
