#!/usr/bin/env python3
"""Inactive runtime primitives for the exact S20+ public-health campaign.

This is a review candidate, not a connected executor.  Its public CLI only
renders a static plan and every operational gate is deliberately false.  The
classes below make the proposed ownership checks testable through an injected
environment, while the POSIX exact-file exec primitive remains unreachable
behind the same all-false operational gate.

No durable byte string is a command capability.  The only opening-to-read
capability in this module is process-local, descriptor-backed, nonserializable,
and created from already-held owners.  Python naming and object seals are not
an authority boundary: an importer can reach these H0 fixture methods.  A
future no-input owner must keep construction in its reviewed closed call graph
and would still require separate exact-byte review, cross-runner coordination,
activation, and a fresh attended request.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import json
import os
import re
import selectors
import signal
import socket
import stat
import sys
import threading
import time
from types import MappingProxyType
from typing import Any, Final, Mapping, Protocol, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_RUNTIME_PRIMITIVES_V1_PASS_GO_NOT_ACTIVE"
SCHEMA = "s20plus_g986n_autonomous_public_health_runtime_primitives_v1_h0"
EXPECTED_SELF_NORMALIZED_SHA256 = "12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2"

# These are operational gates.  They are intentionally all false, and this
# file is not to be activated by changing them in place.
RUNTIME_PRIMITIVES_REVIEWED = False
PHASE_A_EXACT_BOUND = False
ADB_CLIENT_FD_EXEC_REVIEWED = False
ADB_SERVER_OWNER_REVIEWED = False
HOST_CLOCK_OWNER_REVIEWED = False
USB_GENERATION_OWNER_REVIEWED = False
OPENING_READ_CAPABILITY_REVIEWED = False
EXECUTOR_IMPLEMENTED = False
SAME_PROCESS_HANDOFF_IMPLEMENTED = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

NORMALIZED_GATE_NAMES = (
    "RUNTIME_PRIMITIVES_REVIEWED",
    "PHASE_A_EXACT_BOUND",
    "ADB_CLIENT_FD_EXEC_REVIEWED",
    "ADB_SERVER_OWNER_REVIEWED",
    "HOST_CLOCK_OWNER_REVIEWED",
    "USB_GENERATION_OWNER_REVIEWED",
    "OPENING_READ_CAPABILITY_REVIEWED",
    "EXECUTOR_IMPLEMENTED",
    "SAME_PROCESS_HANDOFF_IMPLEMENTED",
    "TARGET_COORDINATION_ACTIVE",
    "CROSS_CODE_COORDINATION_ACTIVE",
    "CONTRACT_ACTIVE",
    "MECHANICAL_ACTIVATION",
    "LIVE_AUTHORITY",
)

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

PHASE_A_PATH = (
    "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
    "revalidation/s20plus_g986n_autonomous_public_health_campaign_v1.py"
)
PHASE_A_SIZE = 92_607
PHASE_A_SHA256 = "43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2"
PHASE_A_NORMALIZED_SHA256 = (
    "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773"
)

ADB_PATH = "/usr/lib/android-sdk/platform-tools/adb"
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
ADB_SERVER_SOCKET = "tcp:127.0.0.1:5037"
ADB_LISTEN_HEX = "0100007F:13AD"
AT_EMPTY_PATH = 0x1000
PR_SET_PDEATHSIG = 1

MAX_OUTPUT_BYTES = 65_536
OPENING_CHAIN_MAX_NS = 300 * 1_000_000_000
HANDOFF_MAX_NS = 30 * 1_000_000_000
TOTAL_OWNER_MAX_NS = 600 * 1_000_000_000
REALTIME_PROJECTION_SKEW_MAX_NS = 5 * 1_000_000_000
CLOCK_AXIS_SAMPLE_JITTER_MAX_NS = 1_000_000
TERM_GRACE_NS = 1 * 1_000_000_000
POST_CHILD_DRAIN_NS = 250 * 1_000_000
FIXED_TIMEOUTS = (10, 10, 10, 20, 20, 10)
FIXED_ENV = (
    "ADB_SERVER_SOCKET=tcp:127.0.0.1:5037",
    "LANG=C",
    "LC_ALL=C",
)

HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
DEVPATH_RE = re.compile(r"usb:([0-9]+-[0-9]+(?:\.[0-9]+)*)\Z")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
USB_NODE_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*\Z")
USB_EVENT_ACTIONS = frozenset({"add", "remove", "bind", "unbind", "change"})

SELF_MAX_BYTES = 128 * 1024
PROC_NET_TCP_MAX_BYTES = 256 * 1024
PROC_NET_TCP_MAX_ROWS = 4_096
PROC_ROOT_MAX_ENTRIES = 32_768
PROC_FD_MAX_ENTRIES = 4_096
SYSFS_USB_MAX_ENTRIES = 4_096
NETLINK_PACKET_MAX_BYTES = 16 * 1024
NETLINK_ANCILLARY_MAX_BYTES = 256
NETLINK_DRAIN_MAX_EVENTS = 256
NETLINK_DRAIN_MAX_BYTES = 1 * 1024 * 1024
NETLINK_FIELD_MAX_COUNT = 128
UINT_MAX = (1 << 32) - 1
USBFS_MAJOR = 189
USBFS_DEVICES_PER_BUS = 128
USBFS_MAX_DEVICE_NUMBER = 127
PROC_TOTAL_PROBES_MAX = 65_536

REMOTE_SNAPSHOT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop build_product ro.build.product
emit_prop fingerprint ro.build.fingerprint
emit_prop incremental ro.build.version.incremental
emit_prop build_id ro.build.id
emit_prop android_release ro.build.version.release
emit_prop sdk ro.build.version.sdk
emit_prop security_patch ro.build.version.security_patch
emit_prop build_type ro.build.type
emit_prop build_tags ro.build.tags
emit_prop build_characteristics ro.build.characteristics
emit_prop bootloader ro.bootloader
emit_prop boot_bootloader ro.boot.bootloader
emit_prop verified_boot_state ro.boot.verifiedbootstate
emit_prop flash_locked ro.boot.flash.locked
emit_prop vbmeta_device_state ro.boot.vbmeta.device_state
emit_prop warranty_bit ro.boot.warranty_bit
emit_prop boot_mode ro.bootmode
emit_prop slot_suffix ro.boot.slot_suffix
emit_prop hardware ro.hardware
emit_prop board_platform ro.board.platform
emit_prop soc_manufacturer ro.soc.manufacturer
emit_prop soc_model ro.soc.model
emit_prop cpu_abilist ro.product.cpu.abilist
emit_prop first_api_level ro.product.first_api_level
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'kernel_release='; uname -r
printf 'machine='; uname -m
printf 'selinux='; getenforce
printf 'shell_identity='; id
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
"""


class RuntimePrimitiveError(RuntimeError):
    """Any ambiguity or attempted activation stops the candidate."""


@dataclass(frozen=True)
class StatSnapshot:
    device: int
    inode: int
    mode: int
    links: int
    uid: int
    gid: int
    size: int
    mtime_ns: int
    ctime_ns: int
    rdev: int = 0

    @classmethod
    def from_os(cls, value: os.stat_result) -> "StatSnapshot":
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            links=value.st_nlink,
            uid=value.st_uid,
            gid=value.st_gid,
            size=value.st_size,
            mtime_ns=value.st_mtime_ns,
            ctime_ns=value.st_ctime_ns,
            rdev=value.st_rdev,
        )


@dataclass(frozen=True)
class ExactFileExpectation:
    path: str
    size: int
    sha256: str
    executable: bool


PHASE_A_EXPECTATION = ExactFileExpectation(
    PHASE_A_PATH, PHASE_A_SIZE, PHASE_A_SHA256, False
)
ADB_EXPECTATION = ExactFileExpectation(ADB_PATH, ADB_SIZE, ADB_SHA256, True)


@dataclass(frozen=True)
class ListenerCandidate:
    socket_inode: int
    pid: int


@dataclass(frozen=True)
class ClockSnapshot:
    boot_id: str
    realtime_ns: int
    boottime_ns: int
    monotonic_ns: int


@dataclass(frozen=True)
class ProcessThreadIdentity:
    pid: int
    thread_ident: int
    thread_object: object
    thread_alive: bool


@dataclass(frozen=True)
class CapabilityDescriptor:
    read_fd: int
    write_fd: int
    read_identity: StatSnapshot
    write_identity: StatSnapshot
    read_access_mode: int
    write_access_mode: int
    token: object


@dataclass(frozen=True)
class UsbCandidate:
    topology: str
    topology_sha256: str
    sysfs_path: str
    usbfs_path: str
    busnum: int
    devnum: int


@dataclass(frozen=True)
class UsbEvent:
    action: str
    topology_sha256: str | None


@dataclass(frozen=True)
class MonitorBatch:
    events: tuple[UsbEvent, ...]
    overflow: bool
    alive: bool


@dataclass(frozen=True)
class CommandCapture:
    argv: tuple[str, ...]
    timeout_sec: int
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    term_sent: bool
    kill_sent: bool
    post_child_drain_expired: bool


class RuntimeEnvironment(Protocol):
    """Narrow OS surface injected only into internal owner construction."""

    def open_file(self, path: str, flags: int) -> int: ...

    def close(self, descriptor: int) -> None: ...

    def fstat(self, descriptor: int) -> StatSnapshot: ...

    def pread_all(self, descriptor: int, maximum: int) -> bytes: ...

    def effective_uid(self) -> int: ...

    def listener_candidates(self, socket_spec: str) -> tuple[ListenerCandidate, ...]: ...

    def process_start_ticks(self, pid: int) -> int: ...

    def process_uid(self, pid: int) -> int: ...

    def pidfd_open(self, pid: int) -> int: ...

    def pidfd_alive(self, descriptor: int) -> bool: ...

    def open_process_executable(self, pid: int) -> int: ...

    def clock_snapshot(self) -> ClockSnapshot: ...

    def open_usb_monitor(self) -> int: ...

    def drain_usb_monitor(self, descriptor: int) -> MonitorBatch: ...

    def usb_candidates(self, topology_sha256: str) -> tuple[UsbCandidate, ...]: ...

    def process_identity(self) -> ProcessThreadIdentity: ...

    def new_capability_descriptor(self) -> CapabilityDescriptor: ...

    def capability_alive(self, descriptor: CapabilityDescriptor) -> bool: ...

    def close_capability(self, descriptor: CapabilityDescriptor) -> None: ...

    def execute_fixed_adb(
        self, descriptor: int, ordinal: int, serial: str
    ) -> CommandCapture: ...


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalized_source_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RuntimePrimitiveError("source normalization requires bytes")
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        payload,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if (status_count, anchor_count) != (1, 1):
        raise RuntimePrimitiveError("source normalization anchors are ambiguous")
    for name in NORMALIZED_GATE_NAMES:
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RuntimePrimitiveError("source gate normalization is ambiguous")
    return _sha256(normalized)


def _read_self_bytes() -> bytes:
    descriptor = os.open(
        __file__,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > SELF_MAX_BYTES
        ):
            raise RuntimePrimitiveError("runtime source identity differs")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1 << 20))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(payload) != before.st_size
            or os.read(descriptor, 1)
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise RuntimePrimitiveError("runtime source changed while read")
        return payload
    finally:
        os.close(descriptor)


def _topology_sha256(topology: str) -> str:
    if DEVPATH_RE.fullmatch(topology) is None:
        raise RuntimePrimitiveError("USB topology grammar differs")
    return _sha256(topology.encode("ascii"))


def _expected_usbfs_rdev(busnum: int, devnum: int) -> int:
    if (
        type(busnum) is not int
        or not 1 <= busnum <= 999
        or type(devnum) is not int
        or not 1 <= devnum <= USBFS_MAX_DEVICE_NUMBER
    ):
        raise RuntimePrimitiveError("USB bus/device number is outside reviewed mapping")
    minor = (busnum - 1) * USBFS_DEVICES_PER_BUS + (devnum - 1)
    return os.makedev(USBFS_MAJOR, minor)


def _fixed_argv(ordinal: int, serial: str) -> tuple[str, ...]:
    if type(ordinal) is not int or not 1 <= ordinal <= 6:
        raise RuntimePrimitiveError("ADB transcript ordinal differs")
    if type(serial) is not str or SERIAL_RE.fullmatch(serial) is None:
        raise RuntimePrimitiveError("bound serial grammar differs")
    values = (
        (ADB_PATH, "version"),
        (ADB_PATH, "devices", "-l"),
        (ADB_PATH, "-s", serial, "get-devpath"),
        (ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT),
        (ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT),
        (ADB_PATH, "devices", "-l"),
    )
    return values[ordinal - 1]


def _validate_stat_shape(value: StatSnapshot, label: str) -> None:
    if type(value) is not StatSnapshot:
        raise RuntimePrimitiveError(f"{label} stat receipt is not exact")
    for field in (
        value.device,
        value.inode,
        value.mode,
        value.links,
        value.uid,
        value.gid,
        value.size,
        value.mtime_ns,
        value.ctime_ns,
        value.rdev,
    ):
        if type(field) is not int or field < 0:
            raise RuntimePrimitiveError(f"{label} stat receipt is malformed")


class HeldExactFile:
    """One exact held regular file, rechecked against its canonical path."""

    __slots__ = ("_environment", "_expectation", "_fd", "_identity", "_closed")

    def __init__(
        self,
        environment: RuntimeEnvironment,
        expectation: ExactFileExpectation,
        descriptor: int,
        identity: StatSnapshot,
    ) -> None:
        self._environment = environment
        self._expectation = expectation
        self._fd = descriptor
        self._identity = identity
        self._closed = False

    @classmethod
    def bind(
        cls,
        environment: RuntimeEnvironment,
        expectation: ExactFileExpectation,
    ) -> "HeldExactFile":
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = environment.open_file(expectation.path, flags)
        try:
            identity = cls._measure(environment, descriptor, expectation)
        except BaseException:
            environment.close(descriptor)
            raise
        return cls(environment, expectation, descriptor, identity)

    @staticmethod
    def _measure(
        environment: RuntimeEnvironment,
        descriptor: int,
        expectation: ExactFileExpectation,
    ) -> StatSnapshot:
        before = environment.fstat(descriptor)
        _validate_stat_shape(before, expectation.path)
        payload = environment.pread_all(descriptor, expectation.size + 1)
        after = environment.fstat(descriptor)
        if (
            before != after
            or not stat.S_ISREG(before.mode)
            or before.links != 1
            or before.size != expectation.size
            or len(payload) != expectation.size
            or _sha256(payload) != expectation.sha256
            or (expectation.executable and before.mode & 0o111 == 0)
        ):
            raise RuntimePrimitiveError(f"{expectation.path} exact identity differs")
        return before

    @classmethod
    def bind_open_descriptor(
        cls,
        environment: RuntimeEnvironment,
        descriptor: int,
        expectation: ExactFileExpectation,
    ) -> "HeldExactFile":
        identity = cls._measure(environment, descriptor, expectation)
        return cls(environment, expectation, descriptor, identity)

    @property
    def descriptor(self) -> int:
        if self._closed:
            raise RuntimePrimitiveError("held exact file is closed")
        return self._fd

    @property
    def identity(self) -> StatSnapshot:
        return self._identity

    def verify(self, *, reopen_path: bool) -> None:
        if self._closed:
            raise RuntimePrimitiveError("held exact file is closed")
        current = self._measure(self._environment, self._fd, self._expectation)
        if current != self._identity:
            raise RuntimePrimitiveError("held exact file identity changed")
        if reopen_path:
            reopened = HeldExactFile.bind(self._environment, self._expectation)
            try:
                if reopened.identity != self._identity:
                    raise RuntimePrimitiveError("canonical exact-file path was replaced")
            finally:
                reopened.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._environment.close(self._fd)


class PhaseASourceOwner:
    """Exact held Phase-A source receipt for a future closed runtime owner."""

    __slots__ = ("_file",)

    def __init__(self, held: HeldExactFile) -> None:
        self._file = held

    @classmethod
    def bind(cls, environment: RuntimeEnvironment) -> "PhaseASourceOwner":
        return cls(HeldExactFile.bind(environment, PHASE_A_EXPECTATION))

    def verify(self) -> None:
        self._file.verify(reopen_path=True)

    def close(self) -> None:
        self._file.close()


class AdbClientOwner:
    """Held ADB H0 fixture; it grants no authority when imported.

    A future closed executor, not a caller of this class, would own the bound
    serial and ordinal.  The concrete execution transition checks the all-live
    gate again before fork.
    """

    __slots__ = ("_environment", "_file")

    def __init__(self, environment: RuntimeEnvironment, held: HeldExactFile) -> None:
        self._environment = environment
        self._file = held

    @classmethod
    def bind(cls, environment: RuntimeEnvironment) -> "AdbClientOwner":
        return cls(environment, HeldExactFile.bind(environment, ADB_EXPECTATION))

    @property
    def identity(self) -> StatSnapshot:
        return self._file.identity

    def verify(self) -> None:
        self._file.verify(reopen_path=True)

    def capture(self, ordinal: int, serial: str) -> CommandCapture:
        _require_operational_gate()
        argv = _fixed_argv(ordinal, serial)
        self.verify()
        capture = self._environment.execute_fixed_adb(
            self._file.descriptor, ordinal, serial
        )
        self.verify()
        if (
            type(capture) is not CommandCapture
            or capture.argv != argv
            or capture.timeout_sec != FIXED_TIMEOUTS[ordinal - 1]
            or type(capture.returncode) is not int
            or type(capture.stdout) is not bytes
            or type(capture.stderr) is not bytes
            or type(capture.timed_out) is not bool
            or type(capture.term_sent) is not bool
            or type(capture.kill_sent) is not bool
            or type(capture.post_child_drain_expired) is not bool
            or len(capture.stdout) + len(capture.stderr) > MAX_OUTPUT_BYTES
        ):
            raise RuntimePrimitiveError("fixed ADB child capture receipt differs")
        if capture.timed_out or capture.post_child_drain_expired:
            raise RuntimePrimitiveError(
                "child deadline or pipe drain expired; capture is mandatory non-success"
            )
        return capture

    def close(self) -> None:
        self._file.close()


class AdbServerOwner:
    """A unique pre-existing server bound by socket, PID, pidfd, and exact exe."""

    __slots__ = (
        "_environment",
        "_adb_identity",
        "_socket_inode",
        "_pid",
        "_start_ticks",
        "_uid",
        "_pidfd",
        "_executable",
        "_closed",
    )

    def __init__(
        self,
        environment: RuntimeEnvironment,
        adb_identity: StatSnapshot,
        listener: ListenerCandidate,
        start_ticks: int,
        uid: int,
        pidfd: int,
        executable: HeldExactFile,
    ) -> None:
        self._environment = environment
        self._adb_identity = adb_identity
        self._socket_inode = listener.socket_inode
        self._pid = listener.pid
        self._start_ticks = start_ticks
        self._uid = uid
        self._pidfd = pidfd
        self._executable = executable
        self._closed = False

    @classmethod
    def bind(
        cls, environment: RuntimeEnvironment, adb: AdbClientOwner
    ) -> "AdbServerOwner":
        adb.verify()
        listeners = environment.listener_candidates(ADB_SERVER_SOCKET)
        if len(listeners) != 1 or type(listeners[0]) is not ListenerCandidate:
            raise RuntimePrimitiveError("ADB server listener is absent or ambiguous")
        listener = listeners[0]
        if (
            type(listener.socket_inode) is not int
            or listener.socket_inode <= 0
            or type(listener.pid) is not int
            or listener.pid <= 0
        ):
            raise RuntimePrimitiveError("ADB server listener receipt is malformed")
        start_ticks = environment.process_start_ticks(listener.pid)
        uid = environment.process_uid(listener.pid)
        if (
            type(start_ticks) is not int
            or start_ticks <= 0
            or type(uid) is not int
            or uid < 0
            or uid != environment.effective_uid()
        ):
            raise RuntimePrimitiveError("ADB server process provenance differs")
        pidfd = environment.pidfd_open(listener.pid)
        try:
            executable_fd = environment.open_process_executable(listener.pid)
        except BaseException:
            environment.close(pidfd)
            raise
        try:
            executable = HeldExactFile.bind_open_descriptor(
                environment, executable_fd, ADB_EXPECTATION
            )
            if executable.identity != adb.identity:
                raise RuntimePrimitiveError("ADB server executable is not held client inode")
        except BaseException:
            environment.close(executable_fd)
            environment.close(pidfd)
            raise
        owner = cls(
            environment,
            adb.identity,
            listener,
            start_ticks,
            uid,
            pidfd,
            executable,
        )
        try:
            owner.verify()
        except BaseException:
            owner.close()
            raise
        return owner

    def verify(self) -> None:
        if self._closed or not self._environment.pidfd_alive(self._pidfd):
            raise RuntimePrimitiveError("ADB server pidfd is no longer live")
        listeners = self._environment.listener_candidates(ADB_SERVER_SOCKET)
        if listeners != (ListenerCandidate(self._socket_inode, self._pid),):
            raise RuntimePrimitiveError("ADB server listening socket changed")
        if (
            self._environment.process_start_ticks(self._pid) != self._start_ticks
            or self._environment.process_uid(self._pid) != self._uid
            or self._uid != self._environment.effective_uid()
        ):
            raise RuntimePrimitiveError("ADB server PID/start/UID continuity changed")
        self._executable.verify(reopen_path=False)
        reopened_fd = self._environment.open_process_executable(self._pid)
        reopened: HeldExactFile | None = None
        try:
            reopened = HeldExactFile.bind_open_descriptor(
                self._environment, reopened_fd, ADB_EXPECTATION
            )
            if reopened.identity != self._adb_identity:
                raise RuntimePrimitiveError("ADB server executable path changed")
        finally:
            if reopened is None:
                self._environment.close(reopened_fd)
            else:
                reopened.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._executable.close()
            self._environment.close(self._pidfd)


class HostClockOwner:
    """Host boot and three-clock continuity with BOOTTIME-owned limits."""

    __slots__ = (
        "_environment",
        "_origin",
        "_last",
        "_opening_start_ns",
        "_opening_complete_ns",
        "_read_started",
    )

    def __init__(self, environment: RuntimeEnvironment, origin: ClockSnapshot) -> None:
        self._environment = environment
        self._origin = origin
        self._last = origin
        self._opening_start_ns: int | None = None
        self._opening_complete_ns: int | None = None
        self._read_started = False

    @staticmethod
    def _validate_shape(value: ClockSnapshot) -> None:
        if type(value) is not ClockSnapshot or BOOT_ID_RE.fullmatch(value.boot_id) is None:
            raise RuntimePrimitiveError("host clock snapshot shape differs")
        for item in (value.realtime_ns, value.boottime_ns, value.monotonic_ns):
            if type(item) is not int or item < 0:
                raise RuntimePrimitiveError("host clock value is malformed")

    @classmethod
    def bind(cls, environment: RuntimeEnvironment) -> "HostClockOwner":
        origin = environment.clock_snapshot()
        cls._validate_shape(origin)
        return cls(environment, origin)

    @property
    def elapsed_ns(self) -> int:
        return self._last.boottime_ns - self._origin.boottime_ns

    def sample(self) -> ClockSnapshot:
        value = self._environment.clock_snapshot()
        self._validate_shape(value)
        boottime_delta = value.boottime_ns - self._origin.boottime_ns
        monotonic_delta = value.monotonic_ns - self._origin.monotonic_ns
        projected_realtime = self._origin.realtime_ns + boottime_delta
        if (
            value.boot_id != self._origin.boot_id
            or value.realtime_ns < self._last.realtime_ns
            or value.boottime_ns < self._last.boottime_ns
            or value.monotonic_ns < self._last.monotonic_ns
            or boottime_delta < 0
            or monotonic_delta < 0
            or monotonic_delta - boottime_delta > CLOCK_AXIS_SAMPLE_JITTER_MAX_NS
            or abs(value.realtime_ns - projected_realtime)
            > REALTIME_PROJECTION_SKEW_MAX_NS
            or boottime_delta > TOTAL_OWNER_MAX_NS
        ):
            raise RuntimePrimitiveError("host clock reversed, drifted, rebooted, or expired")
        self._last = value
        return value

    def mark_opening_start(self) -> None:
        if self._opening_start_ns is not None:
            raise RuntimePrimitiveError("opening clock window is already started")
        value = self.sample()
        self._opening_start_ns = value.boottime_ns

    def mark_opening_complete(self) -> None:
        if self._opening_start_ns is None or self._opening_complete_ns is not None:
            raise RuntimePrimitiveError("opening clock window state differs")
        value = self.sample()
        if value.boottime_ns - self._opening_start_ns > OPENING_CHAIN_MAX_NS:
            raise RuntimePrimitiveError("opening receipt chain exceeded 300 seconds")
        self._opening_complete_ns = value.boottime_ns

    def mark_read_start(self) -> None:
        if self._opening_complete_ns is None or self._read_started:
            raise RuntimePrimitiveError("read handoff clock window state differs")
        value = self.sample()
        if value.boottime_ns - self._opening_complete_ns > HANDOFF_MAX_NS:
            raise RuntimePrimitiveError("opening-to-read handoff exceeded 30 seconds")
        self._read_started = True


class UsbGenerationOwner:
    """Uevent monitor plus held sysfs/usbfs generation; starts before selection."""

    __slots__ = (
        "_environment",
        "_monitor_fd",
        "_topology_sha256",
        "_candidate",
        "_sysfs_fd",
        "_usbfs_fd",
        "_sysfs_identity",
        "_usbfs_identity",
        "_closed",
    )

    def __init__(self, environment: RuntimeEnvironment, monitor_fd: int) -> None:
        self._environment = environment
        self._monitor_fd = monitor_fd
        self._topology_sha256: str | None = None
        self._candidate: UsbCandidate | None = None
        self._sysfs_fd: int | None = None
        self._usbfs_fd: int | None = None
        self._sysfs_identity: StatSnapshot | None = None
        self._usbfs_identity: StatSnapshot | None = None
        self._closed = False

    @classmethod
    def start(cls, environment: RuntimeEnvironment) -> "UsbGenerationOwner":
        descriptor = environment.open_usb_monitor()
        owner = cls(environment, descriptor)
        try:
            batch = environment.drain_usb_monitor(descriptor)
        except BaseException:
            owner.close()
            raise
        if type(batch) is not MonitorBatch or batch.overflow or not batch.alive or batch.events:
            owner.close()
            raise RuntimePrimitiveError("USB monitor baseline is not empty and lossless")
        return owner

    @property
    def bound(self) -> bool:
        return self._candidate is not None and not self._closed

    def bind(self, topology: str) -> None:
        if self._closed or self._candidate is not None:
            raise RuntimePrimitiveError("USB generation bind is repeated or closed")
        topology_sha256 = _topology_sha256(topology)
        candidates = self._environment.usb_candidates(topology_sha256)
        if len(candidates) != 1 or type(candidates[0]) is not UsbCandidate:
            raise RuntimePrimitiveError("USB generation is absent or ambiguous")
        candidate = candidates[0]
        self._validate_candidate(candidate, topology, topology_sha256)
        sysfs_fd = self._environment.open_file(
            candidate.sysfs_path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            usbfs_fd = self._environment.open_file(
                candidate.usbfs_path,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
        except BaseException:
            self._environment.close(sysfs_fd)
            raise
        try:
            sysfs_identity = self._environment.fstat(sysfs_fd)
            usbfs_identity = self._environment.fstat(usbfs_fd)
            self._validate_descriptor_pair(
                candidate, sysfs_identity, usbfs_identity
            )
        except BaseException:
            self._environment.close(sysfs_fd)
            self._environment.close(usbfs_fd)
            raise
        self._topology_sha256 = topology_sha256
        self._candidate = candidate
        self._sysfs_fd = sysfs_fd
        self._usbfs_fd = usbfs_fd
        self._sysfs_identity = sysfs_identity
        self._usbfs_identity = usbfs_identity
        try:
            self.verify()
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _validate_candidate(
        candidate: UsbCandidate, topology: str, topology_sha256: str
    ) -> None:
        match = DEVPATH_RE.fullmatch(topology)
        assert match is not None
        if (
            candidate.topology != topology
            or candidate.topology_sha256 != topology_sha256
            or type(candidate.busnum) is not int
            or not 1 <= candidate.busnum <= 999
            or type(candidate.devnum) is not int
            or not 1 <= candidate.devnum <= USBFS_MAX_DEVICE_NUMBER
            or not candidate.sysfs_path.startswith("/sys/devices/")
            or candidate.usbfs_path
            != f"/dev/bus/usb/{candidate.busnum:03d}/{candidate.devnum:03d}"
            or not candidate.sysfs_path.rstrip("/").endswith("/" + match.group(1))
        ):
            raise RuntimePrimitiveError("USB generation candidate binding differs")

    @staticmethod
    def _validate_descriptor_pair(
        candidate: UsbCandidate,
        sysfs_identity: StatSnapshot, usbfs_identity: StatSnapshot
    ) -> None:
        _validate_stat_shape(sysfs_identity, "USB sysfs")
        _validate_stat_shape(usbfs_identity, "USB usbfs")
        if (
            not stat.S_ISDIR(sysfs_identity.mode)
            or not stat.S_ISCHR(usbfs_identity.mode)
            or usbfs_identity.rdev
            != _expected_usbfs_rdev(candidate.busnum, candidate.devnum)
        ):
            raise RuntimePrimitiveError("USB held descriptor types differ")

    def verify(self) -> None:
        if (
            self._closed
            or self._candidate is None
            or self._topology_sha256 is None
            or self._sysfs_fd is None
            or self._usbfs_fd is None
            or self._sysfs_identity is None
            or self._usbfs_identity is None
        ):
            raise RuntimePrimitiveError("USB generation is not bound")
        batch = self._environment.drain_usb_monitor(self._monitor_fd)
        if type(batch) is not MonitorBatch or batch.overflow or not batch.alive:
            raise RuntimePrimitiveError("USB monitor overflowed or closed")
        for event in batch.events:
            if (
                type(event) is not UsbEvent
                or event.action not in USB_EVENT_ACTIONS
                or event.topology_sha256 is None
                or HEX64_RE.fullmatch(event.topology_sha256) is None
                or event.topology_sha256 == self._topology_sha256
            ):
                raise RuntimePrimitiveError("USB generation observed a relevant or unknown event")
        candidates = self._environment.usb_candidates(self._topology_sha256)
        if candidates != (self._candidate,):
            raise RuntimePrimitiveError("USB generation mapping changed")
        sysfs_now = self._environment.fstat(self._sysfs_fd)
        usbfs_now = self._environment.fstat(self._usbfs_fd)
        self._validate_descriptor_pair(self._candidate, sysfs_now, usbfs_now)
        if sysfs_now != self._sysfs_identity or usbfs_now != self._usbfs_identity:
            raise RuntimePrimitiveError("USB held descriptor identity changed")
        for path, expected, flags in (
            (
                self._candidate.sysfs_path,
                self._sysfs_identity,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_DIRECTORY", 0),
            ),
            (
                self._candidate.usbfs_path,
                self._usbfs_identity,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            ),
        ):
            reopened = self._environment.open_file(path, flags)
            try:
                if self._environment.fstat(reopened) != expected:
                    raise RuntimePrimitiveError("USB canonical node was replaced")
            finally:
                self._environment.close(reopened)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            errors: list[BaseException] = []
            for descriptor in (self._sysfs_fd, self._usbfs_fd, self._monitor_fd):
                if descriptor is not None:
                    try:
                        self._environment.close(descriptor)
                    except BaseException as exc:
                        errors.append(exc)
            self._sysfs_fd = None
            self._usbfs_fd = None
            if errors:
                raise RuntimePrimitiveError("USB owner descriptor close failed") from errors[0]


_BUNDLE_SEAL: Final[object] = object()
_CAPABILITY_SEAL: Final[object] = object()


class _OwnerBundle:
    __slots__ = ("adb", "server", "clock", "usb", "_seal")

    def __init__(
        self,
        seal: object,
        adb: AdbClientOwner,
        server: AdbServerOwner,
        clock: HostClockOwner,
        usb: UsbGenerationOwner,
    ) -> None:
        if (
            seal is not _BUNDLE_SEAL
            or type(adb) is not AdbClientOwner
            or type(server) is not AdbServerOwner
            or type(clock) is not HostClockOwner
            or type(usb) is not UsbGenerationOwner
            or not usb.bound
            or not (
                adb._environment
                is server._environment
                is clock._environment
                is usb._environment
            )
            or server._adb_identity != adb.identity
        ):
            raise RuntimePrimitiveError("owner bundle requires live exact owner objects")
        self.adb = adb
        self.server = server
        self.clock = clock
        self.usb = usb
        self._seal = seal
        self.verify()

    @classmethod
    def create(
        cls,
        adb: AdbClientOwner,
        server: AdbServerOwner,
        clock: HostClockOwner,
        usb: UsbGenerationOwner,
    ) -> "_OwnerBundle":
        return cls(_BUNDLE_SEAL, adb, server, clock, usb)

    def verify(self) -> None:
        if self._seal is not _BUNDLE_SEAL:
            raise RuntimePrimitiveError("owner bundle seal differs")
        self.adb.verify()
        self.server.verify()
        self.clock.sample()
        self.usb.verify()


class OpeningReadCapability:
    """Process-local one-shot state; Python visibility is not an authority seal."""

    __slots__ = (
        "_seal",
        "_environment",
        "_owners",
        "_descriptor",
        "_process_identity",
        "_state",
        "_next_ordinal",
    )

    def __init__(
        self,
        seal: object,
        environment: RuntimeEnvironment,
        owners: _OwnerBundle,
    ) -> None:
        if (
            seal is not _CAPABILITY_SEAL
            or type(owners) is not _OwnerBundle
            or environment is not owners.adb._environment
        ):
            raise RuntimePrimitiveError(
                "opening-read capability requires a process-local owner bundle"
            )
        owners.verify()
        process_identity = self._validated_process_identity(
            environment.process_identity()
        )
        owners.clock.mark_opening_start()
        descriptor = environment.new_capability_descriptor()
        try:
            after_allocation = self._validated_process_identity(
                environment.process_identity()
            )
            if (
                after_allocation.pid != process_identity.pid
                or after_allocation.thread_ident != process_identity.thread_ident
                or after_allocation.thread_object is not process_identity.thread_object
                or not environment.capability_alive(descriptor)
            ):
                raise RuntimePrimitiveError(
                    "process/thread or capability changed during mint"
                )
            self._seal = seal
            self._environment = environment
            self._owners = owners
            self._descriptor = descriptor
            self._process_identity = process_identity
            self._state = "opening"
            self._next_ordinal = 1
        except BaseException:
            environment.close_capability(descriptor)
            raise

    @classmethod
    def mint(
        cls, environment: RuntimeEnvironment, owners: _OwnerBundle
    ) -> "OpeningReadCapability":
        return cls(_CAPABILITY_SEAL, environment, owners)

    def __repr__(self) -> str:
        return "<OpeningReadCapability process-local>"

    def __reduce__(self) -> Any:
        raise TypeError("opening-read capability is not serializable")

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("opening-read capability is not serializable")

    def __getstate__(self) -> Any:
        raise TypeError("opening-read capability is not serializable")

    def __copy__(self) -> Any:
        raise TypeError("opening-read capability is not copyable")

    def __deepcopy__(self, _memo: object) -> Any:
        raise TypeError("opening-read capability is not copyable")

    @property
    def state(self) -> str:
        return self._state

    @staticmethod
    def _validated_process_identity(
        value: ProcessThreadIdentity,
    ) -> ProcessThreadIdentity:
        if (
            type(value) is not ProcessThreadIdentity
            or type(value.pid) is not int
            or value.pid <= 0
            or type(value.thread_ident) is not int
            or value.thread_ident <= 0
            or value.thread_object is None
            or value.thread_alive is not True
        ):
            raise RuntimePrimitiveError("process/thread identity is not live and exact")
        return value

    def _require_live(self) -> None:
        current = self._validated_process_identity(
            self._environment.process_identity()
        )
        bound = self._process_identity
        if (
            self._seal is not _CAPABILITY_SEAL
            or self._state == "consumed"
            or current.pid != bound.pid
            or current.thread_ident != bound.thread_ident
            or current.thread_object is not bound.thread_object
            or not self._environment.capability_alive(self._descriptor)
        ):
            raise RuntimePrimitiveError("opening-read capability is lost or foreign")
        self._owners.verify()

    def record_opening_ordinal(self, ordinal: int) -> None:
        self._require_live()
        if self._state != "opening" or ordinal != self._next_ordinal:
            raise RuntimePrimitiveError("opening capability ordinal is replayed or reordered")
        self._next_ordinal += 1
        if self._next_ordinal == 7:
            self._owners.clock.mark_opening_complete()
            self._state = "opening-complete"

    def begin_read(self) -> None:
        self._require_live()
        if self._state != "opening-complete" or self._next_ordinal != 7:
            raise RuntimePrimitiveError("read handoff lacks same-process complete opening")
        self._owners.clock.mark_read_start()
        self._state = "read"
        self._next_ordinal = 1

    def record_read_ordinal(self, ordinal: int) -> None:
        self._require_live()
        if self._state != "read" or ordinal != self._next_ordinal:
            raise RuntimePrimitiveError("read capability ordinal is replayed or reordered")
        self._next_ordinal += 1
        if self._next_ordinal == 7:
            self.consume()

    def consume(self) -> None:
        if self._state != "consumed":
            self._state = "consumed"
            self._seal = None
            self._environment.close_capability(self._descriptor)


def _bounded_directory_names(path: str, maximum: int, label: str) -> tuple[str, ...]:
    if type(maximum) is not int or maximum <= 0:
        raise RuntimePrimitiveError(f"{label} enumeration cap differs")
    names: list[str] = []
    try:
        iterator = os.scandir(path)
    except OSError as exc:
        raise RuntimePrimitiveError(f"{label} enumeration is inaccessible") from exc
    try:
        with iterator:
            for entry in iterator:
                if len(names) >= maximum:
                    raise RuntimePrimitiveError(f"{label} enumeration exceeds cap")
                names.append(entry.name)
    except OSError as exc:
        raise RuntimePrimitiveError(f"{label} enumeration failed") from exc
    return tuple(sorted(names))


def _deepest_uevent_topology(devpath: str) -> str | None:
    if type(devpath) is not str or not devpath.startswith("/devices/"):
        return None
    normalized: list[str] = []
    for segment in devpath.split("/"):
        match = re.fullmatch(
            r"([0-9]+-[0-9]+(?:\.[0-9]+)*)(?::[0-9]+\.[0-9]+)?",
            segment,
        )
        if match is not None:
            node = match.group(1)
            if not normalized or node != normalized[-1]:
                normalized.append(node)
    if not normalized:
        return None
    for parent, child in zip(normalized, normalized[1:]):
        if not child.startswith(parent + "."):
            return None
    return "usb:" + normalized[-1]


def _parse_uevent(payload: bytes) -> UsbEvent:
    if (
        type(payload) is not bytes
        or not payload
        or len(payload) > NETLINK_PACKET_MAX_BYTES
    ):
        raise RuntimePrimitiveError("USB uevent packet is malformed or oversized")
    parts = payload.rstrip(b"\0").split(b"\0")
    fields: dict[str, str] = {}
    header: tuple[str, str] | None = None
    field_count = 0
    for index, part in enumerate(parts):
        if b"=" not in part:
            if index == 0 and b"@" in part:
                action_raw, devpath_raw = part.split(b"@", 1)
                try:
                    header = (
                        action_raw.decode("ascii", "strict"),
                        devpath_raw.decode("ascii", "strict"),
                    )
                except UnicodeError as exc:
                    raise RuntimePrimitiveError("USB uevent header is not ASCII") from exc
                continue
            raise RuntimePrimitiveError("USB uevent field grammar differs")
        key_raw, value_raw = part.split(b"=", 1)
        try:
            key = key_raw.decode("ascii", "strict")
            value = value_raw.decode("ascii", "strict")
        except UnicodeError as exc:
            raise RuntimePrimitiveError("USB uevent is not ASCII") from exc
        if not key or key in fields:
            raise RuntimePrimitiveError("USB uevent has an empty or duplicate key")
        field_count += 1
        if field_count > NETLINK_FIELD_MAX_COUNT:
            raise RuntimePrimitiveError("USB uevent field count exceeds cap")
        fields[key] = value
    if "ACTION" not in fields or "DEVPATH" not in fields:
        raise RuntimePrimitiveError("USB uevent lacks ACTION or DEVPATH")
    if header is not None and header != (fields["ACTION"], fields["DEVPATH"]):
        raise RuntimePrimitiveError("USB uevent header and fields differ")
    topology = _deepest_uevent_topology(fields["DEVPATH"])
    return UsbEvent(
        fields["ACTION"],
        None if topology is None else _topology_sha256(topology),
    )


class _PosixEnvironment:
    """Concrete candidate.  Construction is private and no CLI reaches it."""

    def __init__(self) -> None:
        self._monitor_sockets: dict[int, socket.socket] = {}
        self._capabilities: dict[object, CapabilityDescriptor] = {}

    def open_file(self, path: str, flags: int) -> int:
        return os.open(path, flags)

    def close(self, descriptor: int) -> None:
        monitor = self._monitor_sockets.pop(descriptor, None)
        if monitor is not None:
            monitor.close()
            return
        os.close(descriptor)

    def fstat(self, descriptor: int) -> StatSnapshot:
        return StatSnapshot.from_os(os.fstat(descriptor))

    def pread_all(self, descriptor: int, maximum: int) -> bytes:
        if type(maximum) is not int or maximum <= 0:
            raise RuntimePrimitiveError("pread bound differs")
        chunks: list[bytes] = []
        offset = 0
        while offset < maximum:
            chunk = os.pread(descriptor, min(1 << 20, maximum - offset), offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
        return b"".join(chunks)

    def effective_uid(self) -> int:
        return os.geteuid()

    def listener_candidates(self, socket_spec: str) -> tuple[ListenerCandidate, ...]:
        if socket_spec != ADB_SERVER_SOCKET:
            raise RuntimePrimitiveError("ADB server socket is not fixed")
        try:
            tcp_payload = self._read_small(
                "/proc/net/tcp", PROC_NET_TCP_MAX_BYTES
            ).decode("ascii", "strict")
        except (OSError, UnicodeError) as exc:
            raise RuntimePrimitiveError("bounded /proc/net/tcp is inaccessible") from exc
        lines = tcp_payload.splitlines()
        if not lines or "local_address" not in lines[0]:
            raise RuntimePrimitiveError("/proc/net/tcp header differs")
        rows = [line for line in lines[1:] if line.strip()]
        if len(rows) > PROC_NET_TCP_MAX_ROWS:
            raise RuntimePrimitiveError("/proc/net/tcp row count exceeds cap")
        inodes: set[int] = set()
        for line in rows:
            fields = line.split()
            if len(fields) < 10:
                raise RuntimePrimitiveError("/proc/net/tcp row is malformed")
            if fields[1] == ADB_LISTEN_HEX and fields[3] == "0A":
                try:
                    inode = int(fields[9], 10)
                except ValueError as exc:
                    raise RuntimePrimitiveError("ADB listener inode is malformed") from exc
                if inode <= 0:
                    raise RuntimePrimitiveError("ADB listener inode is not positive")
                inodes.add(inode)
        values: set[ListenerCandidate] = set()
        if len(inodes) != 1:
            return ()
        inode = next(iter(inodes))
        needle = f"socket:[{inode}]"
        current_uid = os.geteuid()
        total_probes = 0

        def account_probe() -> None:
            nonlocal total_probes
            if total_probes >= PROC_TOTAL_PROBES_MAX:
                raise RuntimePrimitiveError("aggregate /proc probe count exceeds cap")
            total_probes += 1

        for name in _bounded_directory_names(
            "/proc", PROC_ROOT_MAX_ENTRIES, "/proc"
        ):
            if not name.isdecimal():
                continue
            pid_root = f"/proc/{name}"
            account_probe()
            try:
                pid_metadata = os.stat(pid_root, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise RuntimePrimitiveError("current-UID /proc identity is inaccessible") from exc
            if pid_metadata.st_uid != current_uid:
                continue
            fd_root = f"/proc/{name}/fd"
            try:
                entries = _bounded_directory_names(
                    fd_root, PROC_FD_MAX_ENTRIES, "current-UID /proc fd"
                )
            except RuntimePrimitiveError as exc:
                if isinstance(exc.__cause__, FileNotFoundError):
                    continue
                raise
            for fd_name in entries:
                account_probe()
                try:
                    if os.readlink(f"{fd_root}/{fd_name}") == needle:
                        values.add(ListenerCandidate(inode, int(name)))
                        break
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    raise RuntimePrimitiveError(
                        "current-UID /proc fd link is inaccessible"
                    ) from exc
        return tuple(sorted(values, key=lambda item: (item.socket_inode, item.pid)))

    def process_start_ticks(self, pid: int) -> int:
        payload = self._read_small(f"/proc/{pid}/stat", 4096).decode("ascii", "strict")
        right = payload.rfind(")")
        if right < 0:
            raise RuntimePrimitiveError("ADB server stat grammar differs")
        fields = payload[right + 2 :].split()
        if len(fields) < 20:
            raise RuntimePrimitiveError("ADB server stat is truncated")
        return int(fields[19])

    def process_uid(self, pid: int) -> int:
        return os.stat(f"/proc/{pid}", follow_symlinks=False).st_uid

    def pidfd_open(self, pid: int) -> int:
        if not hasattr(os, "pidfd_open"):
            raise RuntimePrimitiveError("pidfd_open is unavailable")
        return os.pidfd_open(pid, 0)

    def pidfd_alive(self, descriptor: int) -> bool:
        poller = selectors.DefaultSelector()
        try:
            poller.register(descriptor, selectors.EVENT_READ)
            return not bool(poller.select(0))
        finally:
            poller.close()

    def open_process_executable(self, pid: int) -> int:
        return os.open(f"/proc/{pid}/exe", os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))

    def clock_snapshot(self) -> ClockSnapshot:
        boot_id = self._read_small("/proc/sys/kernel/random/boot_id", 64).decode(
            "ascii", "strict"
        ).strip()
        return ClockSnapshot(
            boot_id=boot_id,
            realtime_ns=time.clock_gettime_ns(time.CLOCK_REALTIME),
            boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),
            monotonic_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC),
        )

    def open_usb_monitor(self) -> int:
        monitor: socket.socket | None = None
        try:
            monitor = socket.socket(
                socket.AF_NETLINK,
                socket.SOCK_DGRAM | getattr(socket, "SOCK_CLOEXEC", 0),
                getattr(socket, "NETLINK_KOBJECT_UEVENT", 15),
            )
            monitor.setblocking(False)
            monitor.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
            overflow_option = getattr(socket, "SO_RXQ_OVFL", 40)
            monitor.setsockopt(socket.SOL_SOCKET, overflow_option, 1)
            monitor.bind((0, 0xFFFFFFFF))
            descriptor = monitor.fileno()
            if type(descriptor) is not int or descriptor < 0:
                raise RuntimePrimitiveError("USB monitor descriptor differs")
            self._monitor_sockets[descriptor] = monitor
            return descriptor
        except BaseException as exc:
            if monitor is not None:
                try:
                    monitor.close()
                except OSError:
                    pass
            raise RuntimePrimitiveError("USB monitor setup failed closed") from exc

    def drain_usb_monitor(self, descriptor: int) -> MonitorBatch:
        monitor = self._monitor_sockets.get(descriptor)
        if monitor is None:
            return MonitorBatch((), False, False)
        events: list[UsbEvent] = []
        overflow = False
        total_bytes = 0
        overflow_option = getattr(socket, "SO_RXQ_OVFL", 40)
        while True:
            try:
                payload, ancillary, flags, _address = monitor.recvmsg(
                    NETLINK_PACKET_MAX_BYTES + 1,
                    NETLINK_ANCILLARY_MAX_BYTES,
                )
            except BlockingIOError:
                break
            except OSError as exc:
                if exc.errno == errno.ENOBUFS:
                    overflow = True
                    break
                raise
            if (
                len(payload) > NETLINK_PACKET_MAX_BYTES
                or flags & getattr(socket, "MSG_TRUNC", 0)
                or flags & getattr(socket, "MSG_CTRUNC", 0)
            ):
                overflow = True
            for level, kind, data in ancillary:
                if level == socket.SOL_SOCKET and kind == overflow_option:
                    if len(data) < 4 or int.from_bytes(data[:4], sys.byteorder):
                        overflow = True
            total_bytes += len(payload)
            if (
                len(events) >= NETLINK_DRAIN_MAX_EVENTS
                or total_bytes > NETLINK_DRAIN_MAX_BYTES
            ):
                overflow = True
                break
            events.append(_parse_uevent(payload))
        return MonitorBatch(tuple(events), overflow, True)

    def usb_candidates(self, topology_sha256: str) -> tuple[UsbCandidate, ...]:
        if HEX64_RE.fullmatch(topology_sha256) is None:
            raise RuntimePrimitiveError("USB topology digest differs")
        values: list[UsbCandidate] = []
        for name in _bounded_directory_names(
            "/sys/bus/usb/devices",
            SYSFS_USB_MAX_ENTRIES,
            "USB sysfs",
        ):
            if USB_NODE_RE.fullmatch(name) is None:
                continue
            topology = "usb:" + name
            if _topology_sha256(topology) != topology_sha256:
                continue
            root = os.path.realpath(f"/sys/bus/usb/devices/{name}")
            if not root.startswith("/sys/devices/"):
                raise RuntimePrimitiveError("USB sysfs node escapes /sys/devices")
            busnum = int(self._read_small(root + "/busnum", 16).strip())
            devnum = int(self._read_small(root + "/devnum", 16).strip())
            values.append(
                UsbCandidate(
                    topology=topology,
                    topology_sha256=topology_sha256,
                    sysfs_path=root,
                    usbfs_path=f"/dev/bus/usb/{busnum:03d}/{devnum:03d}",
                    busnum=busnum,
                    devnum=devnum,
                )
            )
        return tuple(values)

    def process_identity(self) -> ProcessThreadIdentity:
        thread = threading.current_thread()
        ident = thread.ident
        if ident is None:
            raise RuntimePrimitiveError("current thread lacks an identity")
        return ProcessThreadIdentity(
            pid=os.getpid(),
            thread_ident=ident,
            thread_object=thread,
            thread_alive=thread.is_alive(),
        )

    def new_capability_descriptor(self) -> CapabilityDescriptor:
        read_fd, write_fd = os.pipe2(getattr(os, "O_CLOEXEC", 0))
        try:
            read_identity = StatSnapshot.from_os(os.fstat(read_fd))
            write_identity = StatSnapshot.from_os(os.fstat(write_fd))
            read_access_mode = fcntl.fcntl(read_fd, fcntl.F_GETFL) & os.O_ACCMODE
            write_access_mode = fcntl.fcntl(write_fd, fcntl.F_GETFL) & os.O_ACCMODE
            if (
                not stat.S_ISFIFO(read_identity.mode)
                or not stat.S_ISFIFO(write_identity.mode)
                or (read_identity.device, read_identity.inode)
                != (write_identity.device, write_identity.inode)
                or read_access_mode != os.O_RDONLY
                or write_access_mode != os.O_WRONLY
            ):
                raise RuntimePrimitiveError("capability pipe relationship differs")
            token = object()
            value = CapabilityDescriptor(
                read_fd=read_fd,
                write_fd=write_fd,
                read_identity=read_identity,
                write_identity=write_identity,
                read_access_mode=read_access_mode,
                write_access_mode=write_access_mode,
                token=token,
            )
            self._capabilities[token] = value
            return value
        except BaseException:
            os.close(read_fd)
            os.close(write_fd)
            raise

    def capability_alive(self, descriptor: CapabilityDescriptor) -> bool:
        if (
            type(descriptor) is not CapabilityDescriptor
            or self._capabilities.get(descriptor.token) is not descriptor
        ):
            return False
        try:
            read_identity = StatSnapshot.from_os(os.fstat(descriptor.read_fd))
            write_identity = StatSnapshot.from_os(os.fstat(descriptor.write_fd))
            read_access_mode = (
                fcntl.fcntl(descriptor.read_fd, fcntl.F_GETFL) & os.O_ACCMODE
            )
            write_access_mode = (
                fcntl.fcntl(descriptor.write_fd, fcntl.F_GETFL) & os.O_ACCMODE
            )
        except OSError:
            return False
        return (
            read_identity == descriptor.read_identity
            and write_identity == descriptor.write_identity
            and stat.S_ISFIFO(read_identity.mode)
            and stat.S_ISFIFO(write_identity.mode)
            and (read_identity.device, read_identity.inode)
            == (write_identity.device, write_identity.inode)
            and read_access_mode == descriptor.read_access_mode == os.O_RDONLY
            and write_access_mode == descriptor.write_access_mode == os.O_WRONLY
        )

    def close_capability(self, descriptor: CapabilityDescriptor) -> None:
        if (
            type(descriptor) is not CapabilityDescriptor
            or self._capabilities.pop(descriptor.token, None) is not descriptor
        ):
            raise RuntimePrimitiveError("capability descriptor is foreign or closed")
        errors: list[OSError] = []
        for fd in (descriptor.read_fd, descriptor.write_fd):
            try:
                os.close(fd)
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise RuntimePrimitiveError("capability pipe close failed") from errors[0]

    def execute_fixed_adb(
        self, descriptor: int, ordinal: int, serial: str
    ) -> CommandCapture:
        _require_operational_gate()
        return _execveat_capture(descriptor, ordinal, serial)

    @staticmethod
    def _read_small(path: str, maximum: int) -> bytes:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            payload = os.read(descriptor, maximum + 1)
            if len(payload) > maximum or os.read(descriptor, 1):
                raise RuntimePrimitiveError(f"fixed host input is oversized: {path}")
            return payload
        finally:
            os.close(descriptor)


def _close_child_fds_from_four(libc: Any) -> None:
    close_range = getattr(libc, "close_range", None)
    if close_range is None:
        raise RuntimePrimitiveError("Linux close_range is unavailable")
    close_range.argtypes = (ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
    close_range.restype = ctypes.c_int
    ctypes.set_errno(0)
    if close_range(4, UINT_MAX, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), "close_range")


def _execveat_child(
    exec_fd: int,
    argv: tuple[str, ...],
    stdout_fd: int,
    stderr_fd: int,
    expected_parent_pid: int,
) -> None:
    """Child-only exact-file transition.  It never returns on success."""

    _require_operational_gate()
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
            os._exit(126)
        if os.getppid() != expected_parent_pid:
            os._exit(126)
        temporary_exec_fd = fcntl.fcntl(
            exec_fd,
            fcntl.F_DUPFD_CLOEXEC,
            4,
        )
        null_fd = os.open(
            "/dev/null",
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        os.dup2(null_fd, 0, inheritable=True)
        os.dup2(stdout_fd, 1, inheritable=True)
        os.dup2(stderr_fd, 2, inheritable=True)
        os.set_inheritable(0, True)
        os.set_inheritable(1, True)
        os.set_inheritable(2, True)
        os.chdir("/")
        os.umask(0o077)
        os.dup2(temporary_exec_fd, 3, inheritable=False)
        exec_fd = 3
        _close_child_fds_from_four(libc)
        argv_bytes = [item.encode("utf-8", "strict") for item in argv]
        env_bytes = [item.encode("ascii", "strict") for item in FIXED_ENV]
        argv_array = (ctypes.c_char_p * (len(argv_bytes) + 1))(
            *argv_bytes, None
        )
        env_array = (ctypes.c_char_p * (len(env_bytes) + 1))(*env_bytes, None)
        libc.execveat.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
        )
        libc.execveat.restype = ctypes.c_int
        libc.execveat(exec_fd, b"", argv_array, env_array, AT_EMPTY_PATH)
    except BaseException:
        pass
    os._exit(127)


class _CaptureSelector(Protocol):
    def register(self, descriptor: int, events: int, data: str) -> Any: ...

    def unregister(self, descriptor: int) -> Any: ...

    def select(self, timeout: float | None = None) -> Sequence[tuple[Any, int]]: ...

    def close(self) -> None: ...


class _CaptureOps(Protocol):
    def pipe2(self) -> tuple[int, int]: ...

    def fork(self) -> int: ...

    def getpid(self) -> int: ...

    def child_exec(
        self,
        exec_fd: int,
        argv: tuple[str, ...],
        stdout_fd: int,
        stderr_fd: int,
        expected_parent_pid: int,
    ) -> None: ...

    def child_exit(self, status: int) -> None: ...

    def close(self, descriptor: int) -> None: ...

    def set_nonblocking(self, descriptor: int) -> None: ...

    def pidfd_open(self, pid: int) -> int: ...

    def pidfd_signal(self, pidfd: int, signum: int) -> None: ...

    def kill(self, pid: int, signum: int) -> None: ...

    def waitpid(self, pid: int, options: int) -> tuple[int, int]: ...

    def selector(self) -> _CaptureSelector: ...

    def read(self, descriptor: int, maximum: int) -> bytes: ...

    def boottime_ns(self) -> int: ...


class _PosixCaptureOps:
    def pipe2(self) -> tuple[int, int]:
        return os.pipe2(os.O_CLOEXEC)

    def fork(self) -> int:
        return os.fork()

    def getpid(self) -> int:
        return os.getpid()

    def child_exec(
        self,
        exec_fd: int,
        argv: tuple[str, ...],
        stdout_fd: int,
        stderr_fd: int,
        expected_parent_pid: int,
    ) -> None:
        _execveat_child(
            exec_fd,
            argv,
            stdout_fd,
            stderr_fd,
            expected_parent_pid,
        )

    def child_exit(self, status: int) -> None:
        os._exit(status)

    def close(self, descriptor: int) -> None:
        os.close(descriptor)

    def set_nonblocking(self, descriptor: int) -> None:
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        fcntl.fcntl(descriptor, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def pidfd_open(self, pid: int) -> int:
        if not hasattr(os, "pidfd_open"):
            raise RuntimePrimitiveError("pidfd_open is unavailable")
        return os.pidfd_open(pid, 0)

    def pidfd_signal(self, pidfd: int, signum: int) -> None:
        sender = getattr(signal, "pidfd_send_signal", None)
        if sender is None:
            raise RuntimePrimitiveError("pidfd_send_signal is unavailable")
        sender(pidfd, signum)

    def kill(self, pid: int, signum: int) -> None:
        os.kill(pid, signum)

    def waitpid(self, pid: int, options: int) -> tuple[int, int]:
        return os.waitpid(pid, options)

    def selector(self) -> _CaptureSelector:
        return selectors.DefaultSelector()

    def read(self, descriptor: int, maximum: int) -> bytes:
        return os.read(descriptor, maximum)

    def boottime_ns(self) -> int:
        return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


_POSIX_CAPTURE_OPS = _PosixCaptureOps()


def _execveat_capture_with_ops(
    descriptor: int,
    ordinal: int,
    serial: str,
    operations: _CaptureOps,
) -> CommandCapture:
    """Bounded direct-child lifecycle used with fake operations in H0 tests."""

    _require_operational_gate()
    argv = _fixed_argv(ordinal, serial)
    timeout_sec = FIXED_TIMEOUTS[ordinal - 1]
    open_descriptors: set[int] = set()
    registered: set[int] = set()
    selector: _CaptureSelector | None = None
    child_pid: int | None = None
    pidfd: int | None = None
    child_reaped = False
    child_reap_observed_ns: int | None = None
    status_value: int | None = None
    timed_out = False
    term_sent = False
    kill_sent = False
    post_child_drain_expired = False
    buffers = {"stdout": bytearray(), "stderr": bytearray()}

    def close_descriptor(value: int | None) -> None:
        if value is None or value not in open_descriptors:
            return
        open_descriptors.remove(value)
        try:
            operations.close(value)
        except OSError:
            pass

    def unregister_and_close(value: int) -> None:
        if value in registered:
            registered.remove(value)
            if selector is not None:
                try:
                    selector.unregister(value)
                except (KeyError, OSError):
                    pass
        close_descriptor(value)

    def mark_reaped(
        waited: int,
        candidate_status: int,
        observed_at_ns: int,
    ) -> bool:
        nonlocal child_reaped, child_reap_observed_ns, status_value, timed_out
        if waited == 0:
            return False
        if child_pid is None or waited != child_pid or child_reaped:
            raise RuntimePrimitiveError("direct child wait identity differs")
        child_reaped = True
        child_reap_observed_ns = observed_at_ns
        status_value = candidate_status
        if observed_at_ns >= execution_deadline:
            timed_out = True
        return True

    def poll_reap() -> bool:
        if child_pid is None or child_reaped:
            return child_reaped
        waited, candidate_status = operations.waitpid(child_pid, os.WNOHANG)
        if waited == 0:
            return False
        observed_after_wait_ns = operations.boottime_ns()
        return mark_reaped(
            waited,
            candidate_status,
            observed_after_wait_ns,
        )

    def send_signal(signum: int) -> None:
        if child_pid is None or child_reaped:
            return
        try:
            if pidfd is None:
                operations.kill(child_pid, signum)
            else:
                operations.pidfd_signal(pidfd, signum)
        except ProcessLookupError:
            # The exact direct child may have exited between poll and signal;
            # it remains unreaped and is handled by the following wait.
            return
        except BaseException:
            # An unreaped direct child PID cannot be reused.  This fallback is
            # cleanup only; pidfd continuity remains required for a receipt.
            try:
                operations.kill(child_pid, signum)
            except ProcessLookupError:
                return

    def kill_and_reap() -> None:
        nonlocal kill_sent
        if child_pid is None or child_reaped:
            return
        send_signal(signal.SIGKILL)
        kill_sent = True
        waited, candidate_status = operations.waitpid(child_pid, 0)
        if not mark_reaped(
            waited,
            candidate_status,
            operations.boottime_ns(),
        ):
            raise RuntimePrimitiveError("direct child blocking reap returned no child")

    execution_started = operations.boottime_ns()
    execution_deadline = execution_started + timeout_sec * 1_000_000_000
    expected_parent_pid = operations.getpid()
    if type(expected_parent_pid) is not int or expected_parent_pid <= 1:
        raise RuntimePrimitiveError("capture parent PID is not exact")
    try:
        stdout_read, stdout_write = operations.pipe2()
        open_descriptors.update((stdout_read, stdout_write))
        stderr_read, stderr_write = operations.pipe2()
        open_descriptors.update((stderr_read, stderr_write))
        child_pid = operations.fork()
        if type(child_pid) is not int or child_pid < 0:
            raise RuntimePrimitiveError("fork returned an invalid PID")
        if child_pid == 0:
            close_descriptor(stdout_read)
            close_descriptor(stderr_read)
            try:
                operations.child_exec(
                    descriptor,
                    argv,
                    stdout_write,
                    stderr_write,
                    expected_parent_pid,
                )
            except BaseException:
                operations.child_exit(127)
            operations.child_exit(127)
        close_descriptor(stdout_write)
        close_descriptor(stderr_write)
        operations.set_nonblocking(stdout_read)
        operations.set_nonblocking(stderr_read)
        candidate_pidfd = operations.pidfd_open(child_pid)
        if type(candidate_pidfd) is not int or candidate_pidfd < 0:
            raise RuntimePrimitiveError("pidfd_open returned an invalid descriptor")
        pidfd = candidate_pidfd
        open_descriptors.add(pidfd)
        selector = operations.selector()
        for stream_fd, stream_name in (
            (stdout_read, "stdout"),
            (stderr_read, "stderr"),
        ):
            selector.register(stream_fd, selectors.EVENT_READ, stream_name)
            registered.add(stream_fd)

        term_deadline: int | None = None
        drain_deadline: int | None = None
        while True:
            now = operations.boottime_ns()
            poll_reap()
            if child_reaped:
                if drain_deadline is None:
                    if child_reap_observed_ns is None:
                        raise RuntimePrimitiveError(
                            "reaped child lacks post-wait observation time"
                        )
                    drain_deadline = (
                        child_reap_observed_ns + POST_CHILD_DRAIN_NS
                    )
                if now >= drain_deadline:
                    post_child_drain_expired = True
                    for value in tuple(registered):
                        unregister_and_close(value)
                    break
                if not registered:
                    break
                next_deadline = drain_deadline
            else:
                if not term_sent and now >= execution_deadline:
                    timed_out = True
                    send_signal(signal.SIGTERM)
                    term_sent = True
                    term_deadline = now + TERM_GRACE_NS
                if term_sent and term_deadline is not None and now >= term_deadline:
                    kill_and_reap()
                    if child_reap_observed_ns is None:
                        raise RuntimePrimitiveError(
                            "killed child lacks reap observation time"
                        )
                    drain_deadline = (
                        child_reap_observed_ns + POST_CHILD_DRAIN_NS
                    )
                    next_deadline = drain_deadline
                else:
                    next_deadline = (
                        term_deadline if term_deadline is not None else execution_deadline
                    )
            wait_seconds = max(
                0.0,
                min(0.05, (next_deadline - now) / 1_000_000_000),
            )
            for key, _mask in selector.select(wait_seconds):
                stream_fd = key.fd
                if stream_fd not in registered or key.data not in buffers:
                    raise RuntimePrimitiveError("selector returned a foreign stream")
                try:
                    chunk = operations.read(stream_fd, MAX_OUTPUT_BYTES + 1)
                except BlockingIOError:
                    continue
                if not chunk:
                    unregister_and_close(stream_fd)
                    continue
                buffers[key.data].extend(chunk)
                if len(buffers["stdout"]) + len(buffers["stderr"]) > MAX_OUTPUT_BYTES:
                    raise RuntimePrimitiveError("fixed ADB output exceeds 64 KiB")
            after_io = operations.boottime_ns()
            if not child_reaped:
                poll_reap()
            if child_reaped:
                if drain_deadline is None:
                    if child_reap_observed_ns is None:
                        raise RuntimePrimitiveError(
                            "reaped child lacks post-wait observation time"
                        )
                    drain_deadline = (
                        child_reap_observed_ns + POST_CHILD_DRAIN_NS
                    )
                if after_io >= drain_deadline:
                    post_child_drain_expired = True
                    for value in tuple(registered):
                        unregister_and_close(value)
                    break
            elif after_io >= execution_deadline and not term_sent:
                timed_out = True
                send_signal(signal.SIGTERM)
                term_sent = True
                term_deadline = after_io + TERM_GRACE_NS

        if (
            not child_reaped
            or child_reap_observed_ns is None
            or status_value is None
        ):
            raise RuntimePrimitiveError("fixed ADB direct child lacks one wait status")
        return CommandCapture(
            argv=argv,
            timeout_sec=timeout_sec,
            returncode=os.waitstatus_to_exitcode(status_value),
            stdout=bytes(buffers["stdout"]),
            stderr=bytes(buffers["stderr"]),
            timed_out=timed_out,
            term_sent=term_sent,
            kill_sent=kill_sent,
            post_child_drain_expired=post_child_drain_expired,
        )
    except BaseException as original:
        cleanup_error: BaseException | None = None
        if child_pid is not None and child_pid > 0 and not child_reaped:
            try:
                kill_and_reap()
            except BaseException as exc:
                cleanup_error = exc
        if cleanup_error is not None:
            raise RuntimePrimitiveError(
                "direct child cleanup failed after capture error"
            ) from cleanup_error
        raise original
    finally:
        if selector is not None:
            try:
                selector.close()
            except BaseException:
                pass
        for value in tuple(open_descriptors):
            close_descriptor(value)


def _execveat_capture(descriptor: int, ordinal: int, serial: str) -> CommandCapture:
    """Concrete reviewed-shape candidate, unreachable while gates are false."""

    _require_operational_gate()
    return _execveat_capture_with_ops(
        descriptor, ordinal, serial, _POSIX_CAPTURE_OPS
    )


def _operational_gates() -> dict[str, bool]:
    return {
        "runtime_primitives_reviewed": RUNTIME_PRIMITIVES_REVIEWED,
        "phase_a_exact_bound": PHASE_A_EXACT_BOUND,
        "adb_client_fd_exec_reviewed": ADB_CLIENT_FD_EXEC_REVIEWED,
        "adb_server_owner_reviewed": ADB_SERVER_OWNER_REVIEWED,
        "host_clock_owner_reviewed": HOST_CLOCK_OWNER_REVIEWED,
        "usb_generation_owner_reviewed": USB_GENERATION_OWNER_REVIEWED,
        "opening_read_capability_reviewed": OPENING_READ_CAPABILITY_REVIEWED,
        "executor_implemented": EXECUTOR_IMPLEMENTED,
        "same_process_handoff_implemented": SAME_PROCESS_HANDOFF_IMPLEMENTED,
        "target_coordination_active": TARGET_COORDINATION_ACTIVE,
        "cross_code_coordination_active": CROSS_CODE_COORDINATION_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }


def _require_operational_gate() -> None:
    # Pure gate: no file, clock, socket, process, USB, or device observation.
    if not all(value is True for value in _operational_gates().values()):
        raise RuntimePrimitiveError("runtime primitives candidate is inactive")


def attended_open_and_read() -> None:
    """No-input future entry.  This candidate is intentionally not an executor."""

    _require_operational_gate()
    raise RuntimePrimitiveError("runtime primitives candidate has no live executor")


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    normalized_sha256 = normalized_source_sha256(source)
    if normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise RuntimePrimitiveError("runtime normalized source identity differs")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "self": {
            "size": len(source),
            "sha256": _sha256(source),
            "normalized_sha256": normalized_sha256,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "target": dict(TARGET),
        "authority": {
            "tier": "H0",
            "device_contact": False,
            "connected_executor": False,
            "same_process_handoff_active": False,
            "durable_bytes_authorize_commands": False,
            "importable_fixture_methods_authorize_commands": False,
            "python_privacy_is_authority_boundary": False,
            "closed_executor_call_graph_implemented": False,
            "live_authority": False,
        },
        "gates": _operational_gates(),
        "phase_a": {
            "path": PHASE_A_PATH,
            "size": PHASE_A_SIZE,
            "sha256": PHASE_A_SHA256,
            "normalized_sha256": PHASE_A_NORMALIZED_SHA256,
            "held_source_owner_candidate": True,
            "operationally_bound": False,
        },
        "adb_client": {
            "path": ADB_PATH,
            "size": ADB_SIZE,
            "sha256": ADB_SHA256,
            "exec_primitive": "execveat(held-fd, empty-path, fixed-argv, fixed-env, AT_EMPTY_PATH)",
            "path_exec": False,
            "proc_self_fd_fallback": False,
        },
        "adb_server": {
            "socket": ADB_SERVER_SOCKET,
            "must_preexist": True,
            "continuity": ["socket_inode", "pid", "pid_start_ticks", "pidfd", "uid", "held_exe"],
            "autostart_policy_permitted": False,
            "autostart_prevention_implemented": False,
            "postcheck_only_cannot_prevent_restart": True,
            "activation_blocker": "reviewed no-autostart transport is absent",
            "bounded_proc": {
                "net_tcp_bytes": PROC_NET_TCP_MAX_BYTES,
                "net_tcp_rows": PROC_NET_TCP_MAX_ROWS,
                "root_entries": PROC_ROOT_MAX_ENTRIES,
                "fd_entries_per_current_uid_pid": PROC_FD_MAX_ENTRIES,
                "aggregate_pid_and_fd_probes": PROC_TOTAL_PROBES_MAX,
            },
        },
        "clock": {
            "owner": "host-process",
            "axes": ["host_boot_id", "CLOCK_BOOTTIME", "CLOCK_MONOTONIC", "CLOCK_REALTIME"],
            "opening_chain_max_sec": 300,
            "handoff_max_sec": 30,
            "total_owner_max_sec": 600,
            "realtime_projection_skew_max_sec": 5,
            "cross_axis_sample_jitter_max_ns": CLOCK_AXIS_SAMPLE_JITTER_MAX_NS,
            "sampling_is_atomic": False,
        },
        "usb_generation": {
            "monitor_starts_before_selection": True,
            "held": ["sysfs_directory", "usbfs_character_device"],
            "overflow_is_terminal": True,
            "relevant_event_is_terminal": True,
            "nested_devpath_uses_deepest_topology": True,
            "sysfs_entry_cap": SYSFS_USB_MAX_ENTRIES,
            "netlink_packet_byte_cap": NETLINK_PACKET_MAX_BYTES,
            "netlink_drain_event_cap": NETLINK_DRAIN_MAX_EVENTS,
            "netlink_drain_byte_cap": NETLINK_DRAIN_MAX_BYTES,
            "usbfs_rdev_mapping": (
                "major-189-minor-(busnum-1)*128+(devnum-1)"
            ),
        },
        "process_capability": {
            "descriptor_backed": True,
            "nonserializable": True,
            "process_and_thread_bound": True,
            "thread_object_identity_bound": True,
            "fd_number_reuse_rejected": True,
            "pipe_endpoint_identity_bound": True,
            "mintable_from_durable_bytes": False,
            "new_process_resume": False,
            "python_factory_inaccessible": False,
            "future_closed_call_graph_required": True,
        },
        "concrete_host_observers_importable": True,
        "concrete_host_observers_are_authority": False,
        "planned_host_adb_invocations": 12,
        "fixed_six_command_timeouts_sec": list(FIXED_TIMEOUTS),
        "maximum_combined_output_bytes_per_command": MAX_OUTPUT_BYTES,
        "post_direct_child_pipe_drain_ms": POST_CHILD_DRAIN_NS // 1_000_000,
        "child_lifecycle": {
            "candidate_direct_child_reap_count": 1,
            "candidate_waits_for_descendants": False,
            "candidate_post_child_pipe_deadline_fixed": True,
            "fresh_boottime_after_each_select_read_batch": True,
            "fresh_boottime_after_successful_waitpid": True,
            "first_completion_observed_at_or_after_deadline_is_timeout": True,
            "drain_deadline_checked_before_eof_acceptance": True,
            "post_child_pipe_deadline_expiry_is_success": False,
            "all_capture_fds_close_required": True,
            "child_fd_close": "linux-close_range-4-through-UINT_MAX",
            "child_fd_close_depends_on_soft_rlimit": False,
            "pipe_creation": "O_CLOEXEC-blocking",
            "parent_read_ends_nonblocking_after_fork": True,
            "child_write_ends_nonblocking": False,
            "execution_qualified": False,
        },
        "device_commands": [],
        "device_writes": [],
        "root_commands": [],
        "odin_invocations": [],
        "partition_transfers": [],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan is available while inactive")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
