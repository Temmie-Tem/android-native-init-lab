#!/usr/bin/env python3
"""Bounded, candidate-bound CDC ACM observer for Device Action Process v2."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import select
import signal
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
GUARD_SCHEMA = "device_action_modemmanager_guard_v1"
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
MAX_BANNER = 4096
SETTLE_SEC = 0.250


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


def _udev_properties(sysfs_path: Path) -> dict[str, str]:
    try:
        completed = subprocess.run(
            [
                "udevadm",
                "info",
                "--query=property",
                f"--path={sysfs_path}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
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


def _modemmanager_uid_for_node(node: Path) -> str:
    node = node.resolve(strict=True)
    properties = _udev_properties(node)
    return properties.get("ID_MM_PHYSDEV_UID") or str(node)


def modemmanager_uid(topology: str, usb_root: Path = Path("/sys/bus/usb/devices")) -> str:
    match = TOPOLOGY_RE.fullmatch(topology)
    if match is None:
        raise ObserverError("prepared physical topology is invalid")
    return _modemmanager_uid_for_node(usb_root / match.group(1))


def _modemmanager_active() -> bool:
    try:
        completed = subprocess.run(
            ["systemctl", "is-active", "--quiet", "ModemManager.service"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ObserverError("ModemManager state query failed") from exc
    return completed.returncode == 0


class ModemManagerGuard:
    def __init__(self, uid: str, active: bool):
        self.uid = uid
        self.active = active
        self.process: subprocess.Popen[bytes] | None = None
        self.arm_receipt: dict[str, Any] | None = None

    @classmethod
    def arm(cls, topology: str, usb_root: Path = Path("/sys/bus/usb/devices")):
        active = _modemmanager_active()
        uid = modemmanager_uid(topology, usb_root)
        guard = cls(uid, active)
        if not active:
            if _modemmanager_active():
                raise ObserverError("ModemManager activated during guard setup")
            guard.arm_receipt = {
                "schema": GUARD_SCHEMA,
                "status": "not-required",
                "uid_sha256": hashlib.sha256(uid.encode()).hexdigest(),
                "active_rechecked": True,
            }
            return guard
        process = subprocess.Popen(
            [
                "setpriv",
                "--pdeathsig",
                "SIGKILL",
                "mmcli",
                f"--inhibit-device={uid}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "LC_ALL": "C"},
        )
        guard.process = process
        assert process.stdout is not None
        expected = f"successfully inhibited device with uid '{uid}'".encode()
        deadline = time.monotonic() + 10
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
                            "uid_sha256": hashlib.sha256(uid.encode()).hexdigest(),
                            "output_sha256": hashlib.sha256(output).hexdigest(),
                            "child_alive": process.poll() is None,
                        }
                        if process.poll() is None:
                            armed = True
                            return guard
                        break
            raise ObserverError("ModemManager device inhibition failed")
        finally:
            if not armed:
                try:
                    guard.release()
                except (OSError, subprocess.SubprocessError):
                    pass

    def healthy(self, *, recheck: bool = False) -> bool:
        if not self.active:
            return not _modemmanager_active() if recheck else True
        return self.process is not None and self.process.poll() is None

    def matches_node(self, node: Path) -> bool:
        try:
            return _modemmanager_uid_for_node(node) == self.uid
        except ObserverError:
            return False

    def release(self) -> dict[str, Any]:
        if self.process is None:
            return {
                "schema": GUARD_SCHEMA,
                "status": "not-required",
                "released": True,
            }
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGINT)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        return {
            "schema": GUARD_SCHEMA,
            "status": "released",
            "returncode": self.process.returncode,
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
        if not self.guard.matches_node(endpoint.usb_path):
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
            if not self.guard.healthy(recheck=True):
                return "guard-lost", bytes(payload)
            if not self.guard.matches_node(endpoint.usb_path):
                return "identity-mismatch", bytes(payload)
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
        if classification == "accepted" and not self.guard.healthy(recheck=True):
            classification = "guard-lost"
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
    baseline = capture_baseline(spec, topology, class_tty=class_tty)
    baseline_receipt = persist_json(run_dir / "candidate-observer-baseline.json", baseline)
    guard = ModemManagerGuard.arm(topology, usb_root)
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
                "error_type": type(exc).__name__,
                "released": False,
            }
        release_path = run_dir / "candidate-observer-guard-release.json"
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
    armed = (
        isinstance(guard, dict)
        and set(guard)
        == {
            "schema",
            "status",
            "uid_sha256",
            "output_sha256",
            "child_alive",
        }
        and guard["schema"] == GUARD_SCHEMA
        and guard["status"] == "armed"
        and guard["child_alive"] is True
        and all(
            isinstance(guard[name], str)
            and DIGEST_RE.fullmatch(guard[name]) is not None
            for name in ("uid_sha256", "output_sha256")
        )
    )
    not_required = (
        isinstance(guard, dict)
        and set(guard)
        == {
            "schema",
            "status",
            "uid_sha256",
            "active_rechecked",
        }
        and guard["schema"] == GUARD_SCHEMA
        and guard["status"] == "not-required"
        and guard["active_rechecked"] is True
        and isinstance(guard["uid_sha256"], str)
        and DIGEST_RE.fullmatch(guard["uid_sha256"]) is not None
    )
    if not armed and not not_required:
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
