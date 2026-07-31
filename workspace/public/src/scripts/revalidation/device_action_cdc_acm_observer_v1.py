#!/usr/bin/env python3
"""Bounded, candidate-bound CDC ACM observer for Device Action Process v2."""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import json
import os
import re
import select
import stat
import subprocess
import termios
import time
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


SCHEMA = "device_action_cdc_acm_observer_v1"
BASELINE_SCHEMA = "device_action_cdc_acm_baseline_v1"
GUARD_SCHEMA = "device_action_modemmanager_guard_v2"
RECEIPT_SCHEMA = "device_action_cdc_acm_receipt_v1"
KIND = "exact_cdc_acm_banner_v1"
SPEC_KEYS = {
    "kind",
    "usb_vendor_id",
    "usb_product_id",
    "usb_serial",
    "usb_driver",
    "usb_interface_number",
    "banner_hex",
}
CLASSIFICATIONS = {
    "accepted",
    "endpoint-timeout",
    "endpoint-ambiguous",
    "identity-mismatch",
    "open-failed",
    "exclusive-failed",
    "guard-lost",
    "read-timeout",
    "byte-mismatch",
    "extra-byte",
    "interrupted-before-receipt",
}
HEX4_RE = re.compile(r"[0-9a-f]{4}")
SERIAL_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
DRIVER_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
INTERFACE_RE = re.compile(r"[0-9a-f]{2}")
TTY_RE = re.compile(r"ttyACM[0-9]+")
TOPOLOGY_RE = re.compile(r"usb:([0-9]+-[0-9]+(?:\.[0-9]+)*)")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
ERROR_TYPE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
MAX_BANNER = 4096
SETTLE_SEC = 0.250
GUARD_ARM_SEC = 30.0
GUARD_DEFAULT_MAX_SEC = 360
GUARD_MAX_SEC_LIMIT = 7200
GUARD_EXPIRED_EXIT = 3
GUARD_UNCOMMANDED_EXIT = 4
GUARD_RUNTIME_RULE_PATH = Path(
    "/run/udev/rules.d/79-device-action-f1-cdc-acm-guard.rules"
)
PKEXEC = "/usr/bin/pkexec"
SETPRIV = "/usr/bin/setpriv"
PYTHON = "/usr/bin/python3"
UDEVADM = "/usr/bin/udevadm"
GUARD_ARM_PREFIX = "device-action udev guard armed sha256="
_ROOT_UDEV_GUARD_TEMPLATE = r'''
import base64
import hashlib
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time

UDEVADM = "/usr/bin/udevadm"
RULE_DIR = "/run/udev/rules.d"
RULE_NAME = "79-device-action-f1-cdc-acm-guard.rules"
OVERRIDE_RULE = "/etc/udev/rules.d/" + RULE_NAME
ARM_PREFIX = "device-action udev guard armed sha256="
MAX_SEC = 360.0
EXPIRED_EXIT = __GUARD_EXPIRED_EXIT__
UNCOMMANDED_EXIT = __GUARD_UNCOMMANDED_EXIT__
RULE_RE = re.compile(
    rb'# Transient Device Action F1 CDC ACM guard; removed after observation\.\n'
    rb'ACTION=="add\|change\|move\|bind", SUBSYSTEM=="usb", '
    rb'KERNEL=="(?P<top>[0-9]+-[0-9]+(?:\.[0-9]+)*)", '
    rb'ATTR\{idVendor\}=="(?P<vid>[0-9a-f]{4})", '
    rb'ATTR\{idProduct\}=="(?P<pid>[0-9a-f]{4})", '
    rb'ATTR\{serial\}=="(?P<serial>[A-Za-z0-9._-]{1,64})", '
    rb'ENV\{ID_MM_DEVICE_IGNORE\}="1"\n'
    rb'ACTION=="add\|change\|move\|bind", SUBSYSTEM=="tty", '
    rb'KERNEL=="ttyACM\*", KERNELS=="(?P=top)", '
    rb'ATTRS\{idVendor\}=="(?P=vid)", ATTRS\{idProduct\}=="(?P=pid)", '
    rb'ATTRS\{serial\}=="(?P=serial)", '
    rb'ENV\{ID_USB_INTERFACE_NUM\}=="[0-9a-f]{2}", '
    rb'ENV\{ID_MM_DEVICE_IGNORE\}="1", ENV\{ID_MM_PORT_IGNORE\}="1"\n'
)


def fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_udevadm(binary, *args):
    completed = subprocess.run(
        [binary, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
        check=False,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    if completed.returncode != 0:
        raise RuntimeError("udevadm operation failed")


def main():
    if len(sys.argv) != 3 or os.geteuid() != 0:
        raise RuntimeError("root udev guard invocation rejected")
    payload = base64.b64decode(sys.argv[1].encode("ascii"), validate=True)
    expected_sha256 = sys.argv[2]
    if (
        re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or hashlib.sha256(payload).hexdigest() != expected_sha256
        or RULE_RE.fullmatch(payload) is None
    ):
        raise RuntimeError("root udev guard payload rejected")
    os.makedirs(RULE_DIR, mode=0o755, exist_ok=True)
    direct = os.path.abspath(RULE_DIR)
    if (
        os.path.islink(direct)
        or not os.path.isdir(direct)
        or os.path.realpath(direct) != direct
    ):
        raise RuntimeError("udev runtime rule directory is indirect")
    path = os.path.join(direct, RULE_NAME)
    if os.path.lexists(OVERRIDE_RULE):
        raise RuntimeError("higher-priority udev guard rule exists")
    installed = False
    stop = False

    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True

    previous = {
        number: signal.signal(number, request_stop)
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
    }
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644,
        )
        try:
            if os.write(descriptor, payload) != len(payload):
                raise RuntimeError("short udev guard rule write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        installed = True
        fsync_dir(direct)
        run_udevadm(UDEVADM, "verify", path)
        run_udevadm(UDEVADM, "control", "--reload")
        print(ARM_PREFIX + expected_sha256, flush=True)
        deadline = time.monotonic() + MAX_SEC
        while True:
            if stop:
                return UNCOMMANDED_EXIT
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return EXPIRED_EXIT
            readable, _, _ = select.select(
                [sys.stdin.buffer], [], [], min(0.2, remaining)
            )
            if stop:
                return UNCOMMANDED_EXIT
            if time.monotonic() >= deadline:
                return EXPIRED_EXIT
            if not readable:
                continue
            command = sys.stdin.buffer.readline()
            if stop:
                return UNCOMMANDED_EXIT
            if time.monotonic() >= deadline:
                return EXPIRED_EXIT
            if command == b"release\n":
                return 0
            if command == b"":
                return UNCOMMANDED_EXIT
            raise RuntimeError("udev guard control command is invalid")
    finally:
        if installed:
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError("udev guard rule changed type")
            with open(path, "rb") as stream:
                if stream.read() != payload:
                    raise RuntimeError("udev guard rule changed content")
            os.unlink(path)
            fsync_dir(direct)
            run_udevadm(UDEVADM, "control", "--reload")
        for number, handler in previous.items():
            signal.signal(number, handler)


try:
    raise SystemExit(main())
except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
    print(f"device-action udev guard error: {exc}", file=sys.stderr)
    raise SystemExit(1)
'''
if (
    _ROOT_UDEV_GUARD_TEMPLATE.count("__GUARD_EXPIRED_EXIT__") != 1
    or _ROOT_UDEV_GUARD_TEMPLATE.count("__GUARD_UNCOMMANDED_EXIT__") != 1
):
    raise RuntimeError("root udev guard exit-code template is invalid")
ROOT_UDEV_GUARD_CODE = _ROOT_UDEV_GUARD_TEMPLATE.replace(
    "__GUARD_EXPIRED_EXIT__", str(GUARD_EXPIRED_EXIT)
).replace("__GUARD_UNCOMMANDED_EXIT__", str(GUARD_UNCOMMANDED_EXIT))


class ObserverError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_spec(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != SPEC_KEYS:
        raise ObserverError("candidate observer shape mismatch")
    if value["kind"] != KIND:
        raise ObserverError("candidate observer kind mismatch")
    for name in ("usb_vendor_id", "usb_product_id"):
        if not isinstance(value[name], str) or HEX4_RE.fullmatch(value[name]) is None:
            raise ObserverError(f"candidate observer {name} is invalid")
    if (
        not isinstance(value["usb_serial"], str)
        or SERIAL_RE.fullmatch(value["usb_serial"]) is None
    ):
        raise ObserverError("candidate observer USB serial is invalid")
    if (
        not isinstance(value["usb_driver"], str)
        or DRIVER_RE.fullmatch(value["usb_driver"]) is None
    ):
        raise ObserverError("candidate observer USB driver is invalid")
    if (
        not isinstance(value["usb_interface_number"], str)
        or INTERFACE_RE.fullmatch(value["usb_interface_number"]) is None
    ):
        raise ObserverError("candidate observer interface number is invalid")
    banner_hex = value["banner_hex"]
    if (
        not isinstance(banner_hex, str)
        or not banner_hex
        or len(banner_hex) % 2
        or len(banner_hex) > MAX_BANNER * 2
        or re.fullmatch(r"[0-9a-f]+", banner_hex) is None
    ):
        raise ObserverError("candidate observer banner is invalid")
    return value


def expected_banner(spec: dict[str, str]) -> bytes:
    validate_spec(spec)
    return bytes.fromhex(spec["banner_hex"])


def _read_text(path: Path, label: str, maximum: int = 512) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ObserverError(f"CDC ACM sysfs read failed: {label}") from exc
    if not payload or len(payload) > maximum:
        raise ObserverError(f"CDC ACM sysfs value is invalid: {label}")
    try:
        return payload.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise ObserverError(f"CDC ACM sysfs value is not UTF-8: {label}") from exc


def _read_optional_text(path: Path, label: str, maximum: int = 512) -> str:
    try:
        return _read_text(path, label, maximum)
    except ObserverError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return ""
        raise


@dataclass(frozen=True)
class Endpoint:
    tty_name: str
    tty_class: Path
    device_path: Path
    interface_path: Path
    usb_path: Path
    topology: str
    identity_sha256: str
    major: int
    minor: int


def _endpoint_identity(
    tty_name: str,
    usb_path: Path,
    interface_path: Path,
    driver: str,
) -> dict[str, str]:
    return {
        "tty_name": tty_name,
        "topology": usb_path.name,
        "vendor": _read_text(usb_path / "idVendor", "idVendor"),
        "product": _read_text(usb_path / "idProduct", "idProduct"),
        "serial": _read_optional_text(usb_path / "serial", "serial"),
        "interface": _read_text(
            interface_path / "bInterfaceNumber", "bInterfaceNumber"
        ),
        "driver": driver,
    }


def _resolve_endpoint(tty_class: Path) -> tuple[dict[str, str], Endpoint]:
    if TTY_RE.fullmatch(tty_class.name) is None:
        raise ObserverError("CDC ACM class entry is not canonical")
    device_link = tty_class / "device"
    try:
        device_path = device_link.resolve(strict=True)
    except OSError as exc:
        raise ObserverError("CDC ACM device link is invalid") from exc
    interface_path: Path | None = None
    for parent in (device_path, *device_path.parents):
        if (parent / "bInterfaceNumber").is_file():
            interface_path = parent
            break
    if interface_path is None or ":" not in interface_path.name:
        raise ObserverError("CDC ACM interface ancestor is absent")
    usb_name = interface_path.name.split(":", 1)[0]
    usb_path = interface_path.parent
    if usb_path.name != usb_name or not usb_path.is_dir():
        raise ObserverError("CDC ACM USB device ancestor is absent")
    driver_link = interface_path / "driver"
    try:
        driver = driver_link.resolve(strict=True).name
    except OSError as exc:
        raise ObserverError("CDC ACM driver link is invalid") from exc
    dev_value = _read_text(tty_class / "dev", "tty dev")
    match = re.fullmatch(r"([0-9]+):([0-9]+)", dev_value)
    if match is None:
        raise ObserverError("CDC ACM character device identity is invalid")
    identity = _endpoint_identity(tty_class.name, usb_path, interface_path, driver)
    endpoint = Endpoint(
        tty_name=tty_class.name,
        tty_class=tty_class,
        device_path=device_path,
        interface_path=interface_path,
        usb_path=usb_path,
        topology=usb_path.name,
        identity_sha256=digest(identity),
        major=int(match.group(1)),
        minor=int(match.group(2)),
    )
    return identity, endpoint


def scan_endpoints(
    class_tty: Path = Path("/sys/class/tty"),
) -> list[tuple[dict[str, str], Endpoint]]:
    try:
        entries = sorted(class_tty.glob("ttyACM*"))
    except OSError as exc:
        raise ObserverError("CDC ACM class scan failed") from exc
    values: list[tuple[dict[str, str], Endpoint]] = []
    for entry in entries:
        try:
            values.append(_resolve_endpoint(entry))
        except ObserverError:
            continue
    return values


def capture_baseline(
    spec: dict[str, str],
    topology: str,
    *,
    class_tty: Path = Path("/sys/class/tty"),
) -> dict[str, Any]:
    validate_spec(spec)
    match = TOPOLOGY_RE.fullmatch(topology)
    if match is None:
        raise ObserverError("prepared physical topology is invalid")
    identities = scan_endpoints(class_tty)
    exact = [
        identity
        for identity, endpoint in identities
        if _matches(spec, match.group(1), identity, endpoint)
    ]
    if exact:
        raise ObserverError("candidate CDC ACM identity is already present")
    return {
        "schema": BASELINE_SCHEMA,
        "spec_sha256": digest(spec),
        "topology_sha256": hashlib.sha256(match.group(1).encode()).hexdigest(),
        "identity_sha256": sorted(endpoint.identity_sha256 for _, endpoint in identities),
        "exact_candidate_absent": True,
    }


def _matches(
    spec: dict[str, str],
    topology: str,
    identity: dict[str, str],
    endpoint: Endpoint,
) -> bool:
    return (
        endpoint.topology == topology
        and identity["vendor"] == spec["usb_vendor_id"]
        and identity["product"] == spec["usb_product_id"]
        and identity["serial"] == spec["usb_serial"]
        and identity["driver"] == spec["usb_driver"]
        and identity["interface"] == spec["usb_interface_number"]
    )


def _candidate_like(
    spec: dict[str, str],
    topology: str,
    identity: dict[str, str],
    endpoint: Endpoint,
) -> bool:
    return (
        endpoint.topology == topology
        and identity["vendor"] == spec["usb_vendor_id"]
        and identity["product"] == spec["usb_product_id"]
    )


def _write_exclusive(path: Path, payload: bytes) -> dict[str, Any]:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        if os.write(descriptor, payload) != len(payload):
            raise ObserverError(f"short durable write: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def persist_json(path: Path, value: Any) -> dict[str, Any]:
    return _write_exclusive(
        path,
        json.dumps(
            value, indent=2, sort_keys=True, allow_nan=False
        ).encode("utf-8")
        + b"\n",
    )


def _guard_identity(
    vendor: str,
    product: str,
    serial: str,
    interface: str,
    topology: str,
) -> tuple[str, str, str, str, str]:
    if (
        HEX4_RE.fullmatch(vendor) is None
        or HEX4_RE.fullmatch(product) is None
        or SERIAL_RE.fullmatch(serial) is None
        or INTERFACE_RE.fullmatch(interface) is None
        or re.fullmatch(r"[0-9]+-[0-9]+(?:\.[0-9]+)*", topology) is None
    ):
        raise ObserverError("udev guard identity is invalid")
    return vendor, product, serial, interface, topology


def _guard_rule(spec: dict[str, str], topology: str) -> bytes:
    validate_spec(spec)
    topology_match = TOPOLOGY_RE.fullmatch(topology)
    if topology_match is None:
        raise ObserverError("prepared physical topology is invalid")
    vendor, product, serial, interface, usb_node = _guard_identity(
        spec["usb_vendor_id"],
        spec["usb_product_id"],
        spec["usb_serial"],
        spec["usb_interface_number"],
        topology_match.group(1),
    )
    return (
        "# Transient Device Action F1 CDC ACM guard; removed after observation.\n"
        f'ACTION=="add|change|move|bind", SUBSYSTEM=="usb", '
        f'KERNEL=="{usb_node}", ATTR{{idVendor}}=="{vendor}", '
        f'ATTR{{idProduct}}=="{product}", ATTR{{serial}}=="{serial}", '
        'ENV{ID_MM_DEVICE_IGNORE}="1"\n'
        f'ACTION=="add|change|move|bind", SUBSYSTEM=="tty", '
        f'KERNEL=="ttyACM*", KERNELS=="{usb_node}", '
        f'ATTRS{{idVendor}}=="{vendor}", ATTRS{{idProduct}}=="{product}", '
        f'ATTRS{{serial}}=="{serial}", '
        f'ENV{{ID_USB_INTERFACE_NUM}}=="{interface}", '
        'ENV{ID_MM_DEVICE_IGNORE}="1", ENV{ID_MM_PORT_IGNORE}="1"\n'
    ).encode("ascii")


def _validate_guard_max_sec(value: int) -> int:
    if (
        type(value) is not int
        or value < GUARD_DEFAULT_MAX_SEC
        or value > GUARD_MAX_SEC_LIMIT
    ):
        raise ObserverError("udev guard lifetime is outside the reviewed bound")
    return value


def _guard_root_code(max_sec: int) -> str:
    lifetime = _validate_guard_max_sec(max_sec)
    if lifetime == GUARD_DEFAULT_MAX_SEC:
        return ROOT_UDEV_GUARD_CODE
    old = "MAX_SEC = 360.0"
    replacement = f"MAX_SEC = {lifetime}.0"
    if ROOT_UDEV_GUARD_CODE.count(old) != 1:
        raise ObserverError("udev guard lifetime template is invalid")
    return ROOT_UDEV_GUARD_CODE.replace(old, replacement)


def _guard_command(
    spec: dict[str, str],
    topology: str,
    *,
    max_sec: int = GUARD_DEFAULT_MAX_SEC,
) -> list[str]:
    payload = _guard_rule(spec, topology)
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    return [
        PKEXEC,
        SETPRIV,
        "--pdeathsig",
        "SIGTERM",
        PYTHON,
        "-I",
        "-B",
        "-c",
        _guard_root_code(max_sec),
        base64.b64encode(payload).decode("ascii"),
        payload_sha256,
    ]


def _persist_guard_arm_failure(
    evidence_dir: Path,
    output: bytes,
    returncode: int | None,
    status: str,
) -> None:
    retained = output[: 16 * 1024]
    raw = _write_exclusive(
        evidence_dir / "candidate-observer-guard-arm.raw", retained
    )
    persist_json(
        evidence_dir / "candidate-observer-guard-arm-failure.json",
        {
            "schema": GUARD_SCHEMA,
            "status": status,
            "returncode": returncode,
            "raw": raw,
            "bounded": len(retained) <= 16 * 1024,
            "truncated": len(retained) != len(output),
        },
    )


def _try_persist_guard_arm_failure(
    evidence_dir: Path | None,
    output: bytes,
    returncode: int | None,
    status: str,
) -> bool:
    if evidence_dir is None:
        return False
    try:
        _persist_guard_arm_failure(evidence_dir, output, returncode, status)
    except (OSError, ObserverError):
        return False
    return True


def _udev_properties(sysfs_path: Path) -> dict[str, str]:
    try:
        completed = subprocess.run(
            [
                UDEVADM,
                "info",
                "--query=property",
                f"--path={sysfs_path}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ObserverError("udev property query failed") from exc
    if completed.returncode != 0 or completed.stderr:
        raise ObserverError("udev property query was rejected")
    values: dict[str, str] = {}
    for raw in completed.stdout.splitlines():
        key, separator, value = raw.partition(b"=")
        if not separator:
            continue
        try:
            values[key.decode("ascii")] = value.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise ObserverError("udev property is invalid") from exc
    return values


class ModemManagerGuard:
    def __init__(
        self,
        spec: dict[str, str],
        topology: str,
        *,
        max_sec: int = GUARD_DEFAULT_MAX_SEC,
    ):
        self.spec = dict(spec)
        self.topology = topology
        self.max_sec = _validate_guard_max_sec(max_sec)
        self.instance_sha256 = hashlib.sha256(os.urandom(32)).hexdigest()
        self.process: subprocess.Popen[bytes] | None = None
        self.arm_receipt: dict[str, Any] | None = None

    @classmethod
    def arm(
        cls,
        spec: dict[str, str],
        topology: str,
        evidence_dir: Path | None = None,
        *,
        max_sec: int = GUARD_DEFAULT_MAX_SEC,
    ):
        validate_spec(spec)
        topology_match = TOPOLOGY_RE.fullmatch(topology)
        if topology_match is None:
            raise ObserverError("prepared physical topology is invalid")
        guard = cls(spec, topology, max_sec=max_sec)
        spec_sha256 = digest(spec)
        topology_sha256 = hashlib.sha256(
            topology_match.group(1).encode()
        ).hexdigest()
        rule_sha256 = hashlib.sha256(_guard_rule(spec, topology)).hexdigest()
        try:
            process = subprocess.Popen(
                _guard_command(spec, topology, max_sec=guard.max_sec),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "LC_ALL": "C"},
            )
        except OSError as exc:
            _try_persist_guard_arm_failure(
                evidence_dir, b"", None, "launch-failed"
            )
            raise ObserverError("ModemManager guard launch failed") from exc
        guard.process = process
        assert process.stdout is not None
        expected = (GUARD_ARM_PREFIX + rule_sha256).encode()
        deadline = time.monotonic() + GUARD_ARM_SEC
        output = bytearray()
        armed = False
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                readable, _, _ = select.select([process.stdout], [], [], 0.1)
                if readable:
                    chunk = os.read(process.stdout.fileno(), 4096)
                    output.extend(chunk)
                    if len(output) > 16 * 1024:
                        break
                    if expected in output:
                        guard.arm_receipt = {
                            "schema": GUARD_SCHEMA,
                            "status": "armed",
                            "spec_sha256": spec_sha256,
                            "topology_sha256": topology_sha256,
                            "rule_sha256": rule_sha256,
                            "instance_sha256": guard.instance_sha256,
                            "output_sha256": hashlib.sha256(output).hexdigest(),
                            "child_alive": process.poll() is None,
                        }
                        if process.poll() is None:
                            armed = True
                            return guard
                        break
            _try_persist_guard_arm_failure(
                evidence_dir,
                bytes(output),
                process.poll(),
                "guard-arm-failed",
            )
            raise ObserverError("ModemManager udev guard failed")
        finally:
            if not armed:
                try:
                    guard.release()
                except (OSError, subprocess.SubprocessError):
                    pass

    def healthy(self, *, recheck: bool = False) -> bool:
        return self.process is not None and self.process.poll() is None

    def matches_node(self, node: Path) -> bool:
        try:
            properties = _udev_properties(node.resolve(strict=True))
            return (
                properties.get("ID_MM_DEVICE_IGNORE") == "1"
                and properties.get("ID_MM_PORT_IGNORE") == "1"
            )
        except (ObserverError, OSError):
            return False

    @staticmethod
    def _uncommanded_exit_status(returncode: int) -> str:
        if returncode == GUARD_EXPIRED_EXIT:
            return "guard-expired"
        if returncode in {0, GUARD_UNCOMMANDED_EXIT}:
            return "guard-exited-uncommanded"
        return "release-failed"

    def _uncommanded_exit_receipt(self, returncode: int) -> dict[str, Any]:
        return {
            "schema": GUARD_SCHEMA,
            "status": self._uncommanded_exit_status(returncode),
            "instance_sha256": self.instance_sha256,
            "returncode": returncode,
            "released": False,
        }

    def release(self) -> dict[str, Any]:
        if self.process is None:
            return {
                "schema": GUARD_SCHEMA,
                "status": "not-armed",
                "instance_sha256": self.instance_sha256,
                "released": True,
            }
        returncode = self.process.poll()
        if returncode is not None:
            return self._uncommanded_exit_receipt(returncode)
        try:
            if self.process.stdin is None:
                raise OSError("ModemManager guard control pipe is absent")
            self.process.stdin.write(b"release\n")
            self.process.stdin.flush()
            self.process.stdin.close()
            self.process.wait(timeout=10)
        except OSError as exc:
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            returncode = self.process.poll()
            if returncode is not None:
                return self._uncommanded_exit_receipt(returncode)
            return {
                "schema": GUARD_SCHEMA,
                "status": "release-failed",
                "instance_sha256": self.instance_sha256,
                "error_type": type(exc).__name__,
                "released": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "schema": GUARD_SCHEMA,
                "status": "release-failed",
                "instance_sha256": self.instance_sha256,
                "error_type": type(exc).__name__,
                "released": False,
            }
        returncode = self.process.returncode
        if returncode != 0:
            return self._uncommanded_exit_receipt(returncode)
        return {
            "schema": GUARD_SCHEMA,
            "status": "released",
            "instance_sha256": self.instance_sha256,
            "returncode": returncode,
            "released": True,
        }


@dataclass
class ObserverSession:
    spec: dict[str, str]
    topology: str
    run_dir: Path
    binding: dict[str, str]
    baseline: dict[str, Any]
    baseline_receipt: dict[str, Any]
    guard: ModemManagerGuard
    guard_receipt: dict[str, Any]
    class_tty: Path = Path("/sys/class/tty")
    dev_root: Path = Path("/dev")

    def _select(self) -> tuple[str, Endpoint | None]:
        topology = TOPOLOGY_RE.fullmatch(self.topology)
        assert topology is not None
        current = scan_endpoints(self.class_tty)
        exact = [
            endpoint
            for identity, endpoint in current
            if _matches(self.spec, topology.group(1), identity, endpoint)
        ]
        if len(exact) > 1:
            return "endpoint-ambiguous", None
        if len(exact) == 1:
            return "accepted", exact[0]
        mismatched = [
            endpoint
            for identity, endpoint in current
            if _candidate_like(
                self.spec, topology.group(1), identity, endpoint
            )
        ]
        return (
            "identity-mismatch" if mismatched else "endpoint-timeout",
            None,
        )

    def _raw_tty(self, descriptor: int) -> None:
        tty.setraw(descriptor, termios.TCSANOW)

    def _read_endpoint(
        self, endpoint: Endpoint, deadline: float
    ) -> tuple[str, bytes]:
        path = self.dev_root / endpoint.tty_name
        if not self.guard.healthy(recheck=True):
            return "guard-lost", b""
        if not self.guard.matches_node(endpoint.device_path):
            return "identity-mismatch", b""
        try:
            info = path.stat()
            if (
                not stat.S_ISCHR(info.st_mode)
                or os.major(info.st_rdev) != endpoint.major
                or os.minor(info.st_rdev) != endpoint.minor
            ):
                return "identity-mismatch", b""
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
        except OSError:
            return "open-failed", b""
        try:
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
            except OSError:
                return "exclusive-failed", b""
            if not self.guard.healthy(recheck=True):
                return "guard-lost", b""
            try:
                self._raw_tty(descriptor)
            except (OSError, termios.error):
                return "open-failed", b""
            expected = expected_banner(self.spec)
            payload = bytearray()
            while len(payload) <= len(expected) and time.monotonic() < deadline:
                readable, _, _ = select.select(
                    [descriptor], [], [], min(0.1, max(0.0, deadline - time.monotonic()))
                )
                if not readable:
                    continue
                try:
                    chunk = os.read(descriptor, len(expected) + 1 - len(payload))
                except BlockingIOError:
                    continue
                if chunk:
                    payload.extend(chunk)
                if len(payload) > len(expected):
                    break
                if bytes(payload) == expected:
                    settle_deadline = time.monotonic() + SETTLE_SEC
                    while time.monotonic() < settle_deadline:
                        readable, _, _ = select.select(
                            [descriptor], [], [], settle_deadline - time.monotonic()
                        )
                        if not readable:
                            break
                        try:
                            extra = os.read(descriptor, 1)
                        except BlockingIOError:
                            continue
                        if extra:
                            payload.extend(extra)
                            break
                    break
            guard_healthy = self.guard.healthy(recheck=True)
            guard_matches = (
                self.guard.matches_node(endpoint.device_path)
                if guard_healthy
                else False
            )
            identity, repeated = _resolve_endpoint(endpoint.tty_class)
            topology = TOPOLOGY_RE.fullmatch(self.topology)
            assert topology is not None
            if (
                repeated.identity_sha256 != endpoint.identity_sha256
                or not _matches(self.spec, topology.group(1), identity, repeated)
                or os.fstat(descriptor).st_rdev != info.st_rdev
            ):
                return "identity-mismatch", bytes(payload)
            if len(payload) > len(expected):
                return "extra-byte", bytes(payload)
            if bytes(payload) == expected:
                return "accepted", bytes(payload)
            if guard_healthy and not guard_matches:
                return "identity-mismatch", bytes(payload)
            if not guard_healthy:
                return "guard-lost", bytes(payload)
            if time.monotonic() >= deadline and not payload:
                return "read-timeout", bytes(payload)
            return "byte-mismatch", bytes(payload)
        finally:
            os.close(descriptor)

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.monotonic()
        deadline = started + timeout_sec
        if (
            not isinstance(download_departure, dict)
            or set(download_departure)
            != {
                "download_endpoint_absent",
                "absence_timed_out",
                "sequence",
            }
            or not isinstance(
                download_departure["download_endpoint_absent"], bool
            )
            or not isinstance(download_departure["absence_timed_out"], bool)
            or isinstance(download_departure["sequence"], bool)
            or not isinstance(download_departure["sequence"], int)
            or download_departure["sequence"] < 0
        ):
            raise ObserverError("candidate observer departure is invalid")
        departure_receipt = persist_json(
            self.run_dir / "candidate-observer-download-departure.json",
            download_departure,
        )
        classification = "endpoint-timeout"
        endpoint: Endpoint | None = None
        mismatch_seen = False
        if download_departure.get("download_endpoint_absent") is True:
            while time.monotonic() < deadline:
                if not self.guard.healthy():
                    classification = "guard-lost"
                    break
                classification, endpoint = self._select()
                if classification == "identity-mismatch":
                    mismatch_seen = True
                if endpoint is not None or classification == "endpoint-ambiguous":
                    break
                time.sleep(0.05)
            if endpoint is None and classification == "endpoint-timeout" and mismatch_seen:
                classification = "identity-mismatch"
        payload = b""
        if endpoint is not None:
            classification, payload = self._read_endpoint(endpoint, deadline)
        raw_path = self.run_dir / "candidate-observer.raw"
        raw_receipt = _write_exclusive(raw_path, payload)
        value = {
            "schema": RECEIPT_SCHEMA,
            "kind": KIND,
            "binding": dict(self.binding),
            "spec_sha256": digest(self.spec),
            "baseline_sha256": self.baseline_receipt["sha256"],
            "download_departure_sha256": departure_receipt["sha256"],
            "download_endpoint_absent": (
                download_departure.get("download_endpoint_absent") is True
            ),
            "topology_sha256": hashlib.sha256(
                TOPOLOGY_RE.fullmatch(self.topology).group(1).encode()  # type: ignore[union-attr]
            ).hexdigest(),
            "endpoint_identity_sha256": (
                endpoint.identity_sha256 if endpoint is not None else None
            ),
            "guard_sha256": self.guard_receipt["sha256"],
            "raw": raw_receipt,
            "expected_size": len(expected_banner(self.spec)),
            "exact": classification == "accepted",
            "extra_byte": classification == "extra-byte",
            "classification": classification,
            "accepted": classification == "accepted",
            "bounded": True,
            "elapsed_sec": round(time.monotonic() - started, 6),
        }
        receipt_path = self.run_dir / "candidate-observer.json"
        persist_json(receipt_path, value)
        return value


@contextlib.contextmanager
def observer_session(
    spec: dict[str, str],
    topology: str,
    run_dir: Path,
    binding: dict[str, str],
    *,
    class_tty: Path = Path("/sys/class/tty"),
    dev_root: Path = Path("/dev"),
    usb_root: Path = Path("/sys/bus/usb/devices"),
) -> Iterator[ObserverSession]:
    validate_spec(spec)
    release_path = run_dir / "candidate-observer-guard-release.json"
    if release_path.exists() or release_path.is_symlink():
        raise ObserverError("candidate observer guard release already exists")
    baseline = capture_baseline(spec, topology, class_tty=class_tty)
    baseline_receipt = persist_json(run_dir / "candidate-observer-baseline.json", baseline)
    guard = ModemManagerGuard.arm(spec, topology, run_dir)
    try:
        guard_receipt = persist_json(
            run_dir / "candidate-observer-guard.json", guard.arm_receipt
        )
        session = ObserverSession(
            spec,
            topology,
            run_dir,
            binding,
            baseline,
            baseline_receipt,
            guard,
            guard_receipt,
            class_tty,
            dev_root,
        )
        yield session
    finally:
        try:
            release = guard.release()
        except (OSError, subprocess.SubprocessError) as exc:
            release = {
                "schema": GUARD_SCHEMA,
                "status": "release-failed",
                "instance_sha256": guard.instance_sha256,
                "error_type": type(exc).__name__,
                "released": False,
            }
        if not release_path.exists():
            try:
                persist_json(release_path, release)
            except (OSError, ObserverError):
                pass


def validate_receipt(
    path: Path,
    *,
    spec: dict[str, str],
    binding: dict[str, str],
    topology: str,
) -> dict[str, Any]:
    validate_spec(spec)
    topology_match = TOPOLOGY_RE.fullmatch(topology)
    if topology_match is None:
        raise ObserverError("candidate observer receipt topology is invalid")
    topology_sha256 = hashlib.sha256(
        topology_match.group(1).encode()
    ).hexdigest()
    def unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ObserverError("candidate observer receipt has duplicate keys")
            value[key] = item
        return value

    try:
        receipt_info = path.lstat()
        if not stat.S_ISREG(receipt_info.st_mode):
            raise ObserverError("candidate observer receipt is not regular")
        payload = path.read_bytes()
        value = json.loads(payload, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ObserverError("candidate observer receipt is unreadable") from exc
    expected_keys = {
        "schema",
        "kind",
        "binding",
        "spec_sha256",
        "baseline_sha256",
        "download_departure_sha256",
        "download_endpoint_absent",
        "topology_sha256",
        "endpoint_identity_sha256",
        "guard_sha256",
        "raw",
        "expected_size",
        "exact",
        "extra_byte",
        "classification",
        "accepted",
        "bounded",
        "elapsed_sec",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ObserverError("candidate observer receipt shape mismatch")
    classification = value["classification"]
    if (
        value["schema"] != RECEIPT_SCHEMA
        or value["kind"] != KIND
        or value["binding"] != binding
        or value["spec_sha256"] != digest(spec)
        or not isinstance(classification, str)
        or classification not in CLASSIFICATIONS - {"interrupted-before-receipt"}
        or value["accepted"] is not (classification == "accepted")
        or not isinstance(value["download_endpoint_absent"], bool)
        or (
            value["accepted"] is True
            and value["download_endpoint_absent"] is not True
        )
        or value["exact"] is not (classification == "accepted")
        or value["extra_byte"] is not (classification == "extra-byte")
        or value["bounded"] is not True
        or value["expected_size"] != len(expected_banner(spec))
        or any(
            not isinstance(value[name], str)
            or DIGEST_RE.fullmatch(value[name]) is None
            for name in (
                "baseline_sha256",
                "download_departure_sha256",
                "topology_sha256",
                "guard_sha256",
            )
        )
        or (
            value["endpoint_identity_sha256"] is not None
            and (
                not isinstance(value["endpoint_identity_sha256"], str)
                or DIGEST_RE.fullmatch(value["endpoint_identity_sha256"])
                is None
            )
        )
        or isinstance(value["elapsed_sec"], bool)
        or not isinstance(value["elapsed_sec"], (int, float))
        or not 0 <= value["elapsed_sec"] <= 600
        or (
            classification == "accepted"
            and value["endpoint_identity_sha256"] is None
        )
    ):
        raise ObserverError("candidate observer receipt semantics mismatch")
    supporting: dict[str, Any] = {}
    for filename, key in (
        ("candidate-observer-baseline.json", "baseline_sha256"),
        ("candidate-observer-download-departure.json", "download_departure_sha256"),
        ("candidate-observer-guard.json", "guard_sha256"),
    ):
        evidence_path = path.parent / filename
        try:
            evidence_info = evidence_path.lstat()
            if not stat.S_ISREG(evidence_info.st_mode):
                raise ObserverError(
                    f"candidate observer supporting evidence is not regular: {filename}"
                )
            evidence_payload = evidence_path.read_bytes()
        except OSError as exc:
            raise ObserverError(
                f"candidate observer supporting evidence is absent: {filename}"
            ) from exc
        if hashlib.sha256(evidence_payload).hexdigest() != value[key]:
            raise ObserverError(
                f"candidate observer supporting evidence changed: {filename}"
            )
        try:
            supporting[filename] = json.loads(
                evidence_payload, object_pairs_hook=unique_object
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ObserverError(
                f"candidate observer supporting evidence is invalid: {filename}"
            ) from exc
    baseline = supporting["candidate-observer-baseline.json"]
    if (
        not isinstance(baseline, dict)
        or set(baseline)
        != {
            "schema",
            "spec_sha256",
            "topology_sha256",
            "identity_sha256",
            "exact_candidate_absent",
        }
        or baseline["schema"] != BASELINE_SCHEMA
        or baseline["spec_sha256"] != digest(spec)
        or baseline["topology_sha256"] != topology_sha256
        or baseline["exact_candidate_absent"] is not True
        or not isinstance(baseline["identity_sha256"], list)
        or len(baseline["identity_sha256"]) > 256
        or any(
            not isinstance(item, str) or DIGEST_RE.fullmatch(item) is None
            for item in baseline["identity_sha256"]
        )
        or baseline["identity_sha256"]
        != sorted(set(baseline["identity_sha256"]))
    ):
        raise ObserverError("candidate observer baseline semantics mismatch")
    departure = supporting["candidate-observer-download-departure.json"]
    if (
        not isinstance(departure, dict)
        or set(departure)
        != {
            "download_endpoint_absent",
            "absence_timed_out",
            "sequence",
        }
        or not isinstance(departure["download_endpoint_absent"], bool)
        or not isinstance(departure["absence_timed_out"], bool)
        or isinstance(departure["sequence"], bool)
        or not isinstance(departure["sequence"], int)
        or departure["sequence"] < 0
        or departure["download_endpoint_absent"]
        is not value["download_endpoint_absent"]
    ):
        raise ObserverError("candidate observer departure semantics mismatch")
    guard = supporting["candidate-observer-guard.json"]
    expected_spec_sha256 = digest(spec)
    expected_rule_sha256 = hashlib.sha256(
        _guard_rule(spec, topology)
    ).hexdigest()
    armed = (
        isinstance(guard, dict)
        and set(guard)
        == {
            "schema",
            "status",
            "spec_sha256",
            "topology_sha256",
            "rule_sha256",
            "instance_sha256",
            "output_sha256",
            "child_alive",
        }
        and guard["schema"] == GUARD_SCHEMA
        and guard["status"] == "armed"
        and guard["child_alive"] is True
        and guard["spec_sha256"] == expected_spec_sha256
        and guard["topology_sha256"] == topology_sha256
        and guard["rule_sha256"] == expected_rule_sha256
        and all(
            isinstance(guard[name], str)
            and DIGEST_RE.fullmatch(guard[name]) is not None
            for name in (
                "spec_sha256",
                "topology_sha256",
                "rule_sha256",
                "instance_sha256",
                "output_sha256",
            )
        )
    )
    if not armed:
        raise ObserverError("candidate observer guard semantics mismatch")
    if value["topology_sha256"] != topology_sha256:
        raise ObserverError("candidate observer topology binding mismatch")
    raw = value["raw"]
    if not isinstance(raw, dict) or set(raw) != {"path", "size", "sha256"}:
        raise ObserverError("candidate observer raw receipt is malformed")
    if (
        not isinstance(raw["path"], str)
        or isinstance(raw["size"], bool)
        or not isinstance(raw["size"], int)
        or raw["size"] < 0
        or raw["size"] > len(expected_banner(spec)) + 1
        or not isinstance(raw["sha256"], str)
        or DIGEST_RE.fullmatch(raw["sha256"]) is None
    ):
        raise ObserverError("candidate observer raw receipt is malformed")
    raw_path = Path(raw["path"])
    try:
        expected_parent = path.parent.resolve(strict=True)
        actual_parent = raw_path.parent.resolve(strict=True)
    except OSError as exc:
        raise ObserverError("candidate observer evidence directory is absent") from exc
    try:
        raw_info = raw_path.lstat()
        if not stat.S_ISREG(raw_info.st_mode):
            raise ObserverError("candidate observer raw evidence is not regular")
        raw_payload = raw_path.read_bytes()
    except OSError as exc:
        raise ObserverError("candidate observer raw evidence is absent") from exc
    if (
        raw_path.name != "candidate-observer.raw"
        or actual_parent != expected_parent
        or raw["size"] != len(raw_payload)
        or raw["sha256"] != hashlib.sha256(raw_payload).hexdigest()
        or (
            classification == "accepted"
            and raw_payload != expected_banner(spec)
        )
    ):
        raise ObserverError("candidate observer raw evidence changed")
    return value


def read_guard_release(path: Path, arm_path: Path) -> dict[str, Any]:
    def unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ObserverError("candidate observer guard release has duplicate keys")
            value[key] = item
        return value

    try:
        arm_info = arm_path.lstat()
        if not stat.S_ISREG(arm_info.st_mode):
            raise ObserverError("candidate observer guard arm is not regular")
        arm = json.loads(
            arm_path.read_bytes(), object_pairs_hook=unique_object
        )
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ObserverError("candidate observer guard release is not regular")
        value = json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ObserverError("candidate observer guard release is unreadable") from exc
    if (
        not isinstance(arm, dict)
        or set(arm)
        != {
            "schema",
            "status",
            "spec_sha256",
            "topology_sha256",
            "rule_sha256",
            "instance_sha256",
            "output_sha256",
            "child_alive",
        }
        or arm["schema"] != GUARD_SCHEMA
        or arm["status"] != "armed"
        or arm["child_alive"] is not True
        or not isinstance(arm["instance_sha256"], str)
        or DIGEST_RE.fullmatch(arm["instance_sha256"]) is None
        or not isinstance(value, dict)
        or not {
            "schema",
            "status",
            "instance_sha256",
            "released",
        }.issubset(value)
        or value["schema"] != GUARD_SCHEMA
        or value["instance_sha256"] != arm["instance_sha256"]
    ):
        raise ObserverError("candidate observer guard release semantics mismatch")
    common = {"schema", "status", "instance_sha256", "released"}
    status = value.get("status")
    if status == "released":
        valid = (
            set(value) == common | {"returncode"}
            and type(value.get("returncode")) is int
            and value["returncode"] == 0
            and value.get("released") is True
        )
    elif status == "guard-expired":
        valid = (
            set(value) == common | {"returncode"}
            and type(value.get("returncode")) is int
            and value["returncode"] == GUARD_EXPIRED_EXIT
            and value.get("released") is False
        )
    elif status == "guard-exited-uncommanded":
        valid = (
            set(value) == common | {"returncode"}
            and type(value.get("returncode")) is int
            and value["returncode"] in {0, GUARD_UNCOMMANDED_EXIT}
            and value.get("released") is False
        )
    elif status == "release-failed" and set(value) == common | {"returncode"}:
        valid = (
            type(value.get("returncode")) is int
            and value["returncode"]
            not in {0, GUARD_EXPIRED_EXIT, GUARD_UNCOMMANDED_EXIT}
            and value.get("released") is False
        )
    elif status == "release-failed" and set(value) == common | {"error_type"}:
        valid = (
            isinstance(value.get("error_type"), str)
            and ERROR_TYPE_RE.fullmatch(value["error_type"]) is not None
            and value.get("released") is False
        )
    else:
        valid = False
    if not valid:
        raise ObserverError("candidate observer guard release semantics mismatch")
    return value


def validate_guard_release(path: Path, arm_path: Path) -> dict[str, Any]:
    value = read_guard_release(path, arm_path)
    if value["status"] != "released" or value["released"] is not True:
        raise ObserverError("candidate observer guard release was not commanded")
    return value
