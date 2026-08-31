#!/usr/bin/env python3
"""Inactive H0 model for an exact S20+ restricted ADB proxy.

This source is a protocol model, not a proxy, seccomp installer, connected
executor, or activation candidate.  It never creates a socket and its public
CLI only renders a static plan.  The pure trace validator makes the proposed
fail-closed boundary reviewable without executing ADB or contacting a device.

The future design gives the exact held-file ADB child a private AF_UNIX server
socket.  ``host:version`` is answered locally with the pinned ``0029`` server
version, so a client-version mismatch cannot reach the real server as
``host:kill``.  Because ADB treats the private AF_UNIX endpoint as local, an
unavailable proxy can still cause a server-launch attempt; the reviewed filter
must already be installed in the child and deny that attempt.  Every other
accepted frame belongs to one exact ordinal transcript and is forwarded over
one already-proved connection to the already-bound server.

The seccomp description is structural evidence only.  No filter is compiled
or installed here.  In particular, the future child must allow only its
initial held-fd ``execveat`` transition and deny process creation, path exec,
bind, and listen.  Proving that exact filter and its architecture closure is a
separate activation prerequisite.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Final, Mapping, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_PASS_GO_NOT_ACTIVE"
SCHEMA = "s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0"
EXPECTED_SELF_NORMALIZED_SHA256 = "8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9"

# Operational and integration gates.  They are intentionally all false and
# must not be activated by editing this fixture in place.
ADB_PROXY_V1_REVIEWED = False
PHASE_A_EXACT_BOUND = False
RUNTIME_EXACT_BOUND = False
ADB_EXACT_BOUND = False
PRIVATE_AF_UNIX_PROXY_IMPLEMENTED = False
CHILD_PEER_CREDENTIALS_ENFORCED = False
UPSTREAM_SERVER_BINDING_ENFORCED = False
DOWNSTREAM_TRANSCRIPT_ENFORCED = False
CHILD_SECCOMP_FILTER_REVIEWED = False
CHILD_SECCOMP_FILTER_INSTALLED = False
EXECUTOR_IMPLEMENTED = False
SAME_PROCESS_HANDOFF_IMPLEMENTED = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

NORMALIZED_GATE_NAMES = (
    "ADB_PROXY_V1_REVIEWED",
    "PHASE_A_EXACT_BOUND",
    "RUNTIME_EXACT_BOUND",
    "ADB_EXACT_BOUND",
    "PRIVATE_AF_UNIX_PROXY_IMPLEMENTED",
    "CHILD_PEER_CREDENTIALS_ENFORCED",
    "UPSTREAM_SERVER_BINDING_ENFORCED",
    "DOWNSTREAM_TRANSCRIPT_ENFORCED",
    "CHILD_SECCOMP_FILTER_REVIEWED",
    "CHILD_SECCOMP_FILTER_INSTALLED",
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

PHASE_A_IDENTITY = MappingProxyType(
    {
        "path": (
            "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
            "revalidation/s20plus_g986n_autonomous_public_health_campaign_v1.py"
        ),
        "size": 92_607,
        "sha256": (
            "43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2"
        ),
        "normalized_sha256": (
            "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773"
        ),
    }
)
RUNTIME_IDENTITY = MappingProxyType(
    {
        "path": (
            "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
            "revalidation/s20plus_g986n_autonomous_public_health_runtime_v1_h0.py"
        ),
        "size": 85_645,
        "sha256": (
            "f6644edc1f8eee80e6f9fc5e7623c96b8e58de23312e71607e51a4658d67652f"
        ),
        "normalized_sha256": (
            "12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2"
        ),
    }
)
ADB_IDENTITY = MappingProxyType(
    {
        "path": "/usr/lib/android-sdk/platform-tools/adb",
        "canonical_realpath": "/usr/lib/android-sdk/platform-tools/adb",
        "size": 716_968,
        "sha256": (
            "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
        ),
        "server_version_hex": "0029",
    }
)

ADB_PATH = ADB_IDENTITY["path"]
ADB_SERVER_SOCKET = "tcp:127.0.0.1:5037"
ADB_SERVER_LISTEN_HEX = "0100007F:13AD"
PRIVATE_PROXY_FAMILY = "AF_UNIX"
PRIVATE_PROXY_SOCKET_SPEC = "localfilesystem:<held-private-session-dir>/adb-proxy.sock"
PRIVATE_PROXY_PARENT_MODE = 0o700
SO_PEERCRED_SOURCE = "SO_PEERCRED"
LOCAL_VERSION_SERVICE = "host:version"
LOCAL_VERSION_PAYLOAD = "0029"
LOCAL_VERSION_RESPONSE = b"OKAY00040029"
FORBIDDEN_SERVICES = frozenset(
    {
        "host:kill",
        "host:start-server",
        "host:reconnect",
        "host:reconnect-offline",
        "host:track-devices",
        "host:track-devices-l",
    }
)

MAX_SERVICE_BYTES = 4_096
MAX_FRAME_STREAM_BYTES = 16_384
MAX_FRAME_COUNT = 2
MAX_PROXY_CONNECTIONS = 2
MAX_RELAY_OUTPUT_BYTES = 65_536
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
HEX_LENGTH_RE = re.compile(rb"[0-9a-f]{4}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")

class AdbProxyV1Error(RuntimeError):
    """Any ambiguity, protocol drift, or attempted activation stops."""


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

def _adb_escape_arg(value: str) -> str:
    """Model ADB ``escape_arg``: it quotes every non-leading exec argument."""

    if type(value) is not str or "\x00" in value:
        raise AdbProxyV1Error("ADB exec argument differs")
    return "'" + value.replace("'", "'\\''") + "'"


# Exact ADB 34 exec-out construction: argv[1] (``sh``) is copied verbatim and
# every remaining argument is wrapped by ADB's own ``escape_arg``.  This is a
# protocol expectation only; no command is executed by this module.
EXEC_SERVICE = "exec:sh " + _adb_escape_arg("-c") + " " + _adb_escape_arg(
    REMOTE_SNAPSHOT
)
REMOTE_SNAPSHOT_SIZE = 1_472
REMOTE_SNAPSHOT_SHA256 = (
    "a571dc5009eb57952a6230e3ecca8ad342627eb1bf9df38060886ee6382cd17a"
)
EXEC_SERVICE_SIZE = 1_523
EXEC_SERVICE_SHA256 = (
    "c3db3a45d41b3684316c2344c8dad45b23f61b40f03e3d43f6e00d565b9f781e"
)

SECCOMP_POLICY_MODEL = MappingProxyType(
    {
        "implemented": False,
        "installed": False,
        "default_action": "future-reviewed-allowlist-required",
        "initial_transition": MappingProxyType(
            {
                "syscall": "execveat",
                "executable": "exact-held-adb-fd",
                "path": "empty",
                "flags": "AT_EMPTY_PATH",
                "argv": "exact-ordinal-owned",
                "env": (
                    "ADB_SERVER_SOCKET=private-AF_UNIX-proxy",
                    "LANG=C",
                    "LC_ALL=C",
                ),
                "maximum_successes": 1,
            }
        ),
        "required_install_order": (
            "fork-direct-child",
            "install-exact-seccomp-filter",
            "execveat-exact-held-adb-fd",
        ),
        "child_exec_before_filter": False,
        "unconditionally_denied": (
            "clone",
            "clone3",
            "fork",
            "vfork",
            "execve",
            "bind",
            "listen",
        ),
        "filter_installed_before_child_exec": True,
        "classic_filter_is_stateful": False,
        "held_adb_fd_cloexec_close_required": True,
        "followup_execveat_success_impossible": "UNPROVED_REQUIRED_INVARIANT",
        "fd_number_reuse_bypass_closed": False,
        "architecture_and_abi_closure_proved": False,
        "filter_bytes_pinned": False,
    }
)


@dataclass(frozen=True)
class ChildIdentity:
    pid: int
    uid: int
    gid: int
    start_ticks: int


@dataclass(frozen=True)
class PeerCredentials:
    source: str
    pid: int
    uid: int
    gid: int
    process_start_ticks: int
    direct_child_pidfd_bound: bool


@dataclass(frozen=True)
class HeldAdbFileIdentity:
    device: int
    inode: int
    size: int
    sha256: str


@dataclass(frozen=True)
class BoundServerIdentity:
    pid: int
    uid: int
    start_ticks: int
    pidfd_bound: bool
    listener_fd: int
    listener_inode: int
    executable_device: int
    executable_inode: int
    executable_size: int
    executable_sha256: str


@dataclass(frozen=True)
class EstablishedPeerProof:
    family: str
    state: str
    local_address: str
    local_port: int
    peer_address: str
    peer_port: int
    proxy_socket_fd: int
    proxy_socket_inode: int
    held_proxy_fd_inode: int
    server_peer_inode: int
    server_peer_fd: int
    server_local_address: str
    server_local_port: int
    server_observed_peer_address: str
    server_observed_peer_port: int
    server_pid: int
    server_uid: int
    server_start_ticks: int
    server_listener_inode: int
    observed_owner_fd_inodes: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class WireEvent:
    kind: str
    payload: bytes


@dataclass(frozen=True)
class ConnectionTrace:
    index: int
    peer: PeerCredentials
    events: tuple[WireEvent, ...]
    upstream: EstablishedPeerProof | None
    reconnect_count: int


@dataclass(frozen=True)
class ProxyTrace:
    ordinal: int
    child: ChildIdentity
    held_adb: HeldAdbFileIdentity
    connections: tuple[ConnectionTrace, ...]
    command_attempt_count: int
    accepted_connection_count: int
    upstream_connection_count: int


@dataclass(frozen=True)
class ConnectionExpectation:
    role: str
    services: tuple[str, ...]
    upstream: bool
    upstream_statuses: tuple[bytes, ...]
    requires_transport_id: bool
    event_order: tuple[str, ...]
    response_mode: str


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise AdbProxyV1Error("digest input is not exact bytes")
    return hashlib.sha256(payload).hexdigest()


def _require_exact_positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise AdbProxyV1Error(f"{label} is not an exact positive integer")
    return value


def _validate_serial(serial: str) -> None:
    if type(serial) is not str or SERIAL_RE.fullmatch(serial) is None:
        raise AdbProxyV1Error("bound serial grammar differs")


def encode_request(service: str) -> bytes:
    if type(service) is not str:
        raise AdbProxyV1Error("ADB service is not text")
    try:
        payload = service.encode("utf-8")
    except UnicodeError as exc:
        raise AdbProxyV1Error("ADB service encoding differs") from exc
    if not payload or len(payload) > MAX_SERVICE_BYTES or b"\x00" in payload:
        raise AdbProxyV1Error("ADB service payload is outside the reviewed bound")
    return f"{len(payload):04x}".encode("ascii") + payload


def decode_request_stream(chunks: Sequence[bytes]) -> tuple[str, ...]:
    """Decode one bounded, EOF-complete downstream request stream."""

    if type(chunks) not in (tuple, list) or len(chunks) == 0:
        raise AdbProxyV1Error("downstream request chunks are absent")
    if len(chunks) > 64:
        raise AdbProxyV1Error("downstream request chunk count exceeds bound")
    raw_parts: list[bytes] = []
    total = 0
    for chunk in chunks:
        if type(chunk) is not bytes or len(chunk) == 0:
            raise AdbProxyV1Error("downstream request chunk differs")
        total += len(chunk)
        if total > MAX_FRAME_STREAM_BYTES:
            raise AdbProxyV1Error("downstream frame stream exceeds bound")
        raw_parts.append(chunk)
    raw = b"".join(raw_parts)
    services: list[str] = []
    cursor = 0
    while cursor < len(raw):
        if len(raw) - cursor < 4:
            raise AdbProxyV1Error("partial ADB request length at EOF")
        length_raw = raw[cursor : cursor + 4]
        if HEX_LENGTH_RE.fullmatch(length_raw) is None:
            raise AdbProxyV1Error("ADB request length encoding differs")
        length = int(length_raw, 16)
        if length <= 0 or length > MAX_SERVICE_BYTES:
            raise AdbProxyV1Error("ADB request length exceeds reviewed bound")
        cursor += 4
        if len(raw) - cursor < length:
            raise AdbProxyV1Error("partial ADB request payload at EOF")
        payload = raw[cursor : cursor + length]
        cursor += length
        if b"\x00" in payload:
            raise AdbProxyV1Error("ADB request contains NUL")
        try:
            service = payload.decode("utf-8")
        except UnicodeError as exc:
            raise AdbProxyV1Error("ADB request is not UTF-8") from exc
        services.append(service)
        if len(services) > MAX_FRAME_COUNT:
            raise AdbProxyV1Error("repeated or excess ADB request frame")
    if not services:
        raise AdbProxyV1Error("ADB request stream is empty")
    return tuple(services)


def _transport_service(serial: str) -> str:
    _validate_serial(serial)
    return f"host:tport:serial:{serial}"


def _validate_fixed_exec_service() -> None:
    snapshot = REMOTE_SNAPSHOT.encode("utf-8")
    service = EXEC_SERVICE.encode("utf-8")
    if (
        len(snapshot) != REMOTE_SNAPSHOT_SIZE
        or hashlib.sha256(snapshot).hexdigest() != REMOTE_SNAPSHOT_SHA256
        or len(service) != EXEC_SERVICE_SIZE
        or hashlib.sha256(service).hexdigest() != EXEC_SERVICE_SHA256
    ):
        raise AdbProxyV1Error("fixed exec-out protocol bytes differ")


def _serial_service(serial: str, service: str) -> str:
    _validate_serial(serial)
    return f"host-serial:{serial}:{service}"


def expected_connections(ordinal: int, serial: str) -> tuple[ConnectionExpectation, ...]:
    """Return the closed proxy-visible connection sequence for one CLI child."""

    if type(ordinal) is not int or type(ordinal) is bool or not 1 <= ordinal <= 6:
        raise AdbProxyV1Error("opening command ordinal differs")
    _validate_serial(serial)
    _validate_fixed_exec_service()
    if ordinal == 1:
        # ``adb version`` is local-only and must never reach even the proxy.
        return ()
    version = ConnectionExpectation(
        role="local-version",
        services=(LOCAL_VERSION_SERVICE,),
        upstream=False,
        upstream_statuses=(),
        requires_transport_id=False,
        event_order=(
            "downstream-request",
            "proxy-to-downstream-local-version",
            "downstream-eof",
        ),
        response_mode="exact-local-OKAY-0004-0029",
    )
    if ordinal in (2, 6):
        services = ("host:devices-l",)
        mode = "upstream-OKAY-protocol-string-then-EOF"
    elif ordinal == 3:
        services = (_serial_service(serial, "get-devpath"),)
        mode = "upstream-OKAY-protocol-string-then-EOF"
    else:
        services = (_transport_service(serial), EXEC_SERVICE)
        mode = (
            "tport-OKAY-then-u64le-transport-id-then-exec-OKAY-"
            "and-bounded-output"
        )
    service = ConnectionExpectation(
        role="single-upstream-service",
        services=services,
        upstream=True,
        upstream_statuses=tuple(b"OKAY" for _ in services),
        requires_transport_id=ordinal in (4, 5),
        event_order=(
            (
                "downstream-request",
                "proxy-to-upstream-request",
                "upstream-to-proxy-status",
                "proxy-to-downstream-status",
                "upstream-to-proxy-transport-id",
                "proxy-to-downstream-transport-id",
                "downstream-request",
                "proxy-to-upstream-request",
                "upstream-to-proxy-status",
                "proxy-to-downstream-status",
                "upstream-to-proxy-output",
                "proxy-to-downstream-output",
                "upstream-eof",
                "downstream-eof",
            )
            if ordinal in (4, 5)
            else (
                "downstream-request",
                "proxy-to-upstream-request",
                "upstream-to-proxy-status",
                "proxy-to-downstream-status",
                "upstream-to-proxy-protocol-string",
                "proxy-to-downstream-protocol-string",
                "upstream-eof",
                "downstream-eof",
            )
        ),
        response_mode=mode,
    )
    return (version, service)


def upstream_allowlist(ordinal: int, serial: str) -> tuple[str, ...]:
    return tuple(
        service
        for connection in expected_connections(ordinal, serial)
        if connection.upstream
        for service in connection.services
    )


def _validate_child_identity(value: ChildIdentity) -> None:
    if type(value) is not ChildIdentity:
        raise AdbProxyV1Error("child identity receipt differs")
    _require_exact_positive_int(value.pid, "child pid")
    if type(value.uid) is not int or value.uid < 0:
        raise AdbProxyV1Error("child uid differs")
    if type(value.gid) is not int or value.gid < 0:
        raise AdbProxyV1Error("child gid differs")
    _require_exact_positive_int(value.start_ticks, "child start ticks")


def validate_peer_credentials(peer: PeerCredentials, child: ChildIdentity) -> None:
    _validate_child_identity(child)
    if type(peer) is not PeerCredentials or peer.source != SO_PEERCRED_SOURCE:
        raise AdbProxyV1Error("downstream peer is not an exact SO_PEERCRED receipt")
    if (
        type(peer.pid) is not int
        or type(peer.uid) is not int
        or type(peer.gid) is not int
        or peer.pid != child.pid
        or peer.uid != child.uid
        or peer.gid != child.gid
        or type(peer.process_start_ticks) is not int
        or peer.process_start_ticks != child.start_ticks
        or peer.direct_child_pidfd_bound is not True
    ):
        raise AdbProxyV1Error("downstream peer differs from the direct child")


def _validate_held_adb(value: HeldAdbFileIdentity) -> None:
    if type(value) is not HeldAdbFileIdentity:
        raise AdbProxyV1Error("held ADB file identity differs")
    _require_exact_positive_int(value.device, "held ADB device")
    _require_exact_positive_int(value.inode, "held ADB inode")
    if (
        type(value.size) is not int
        or value.size != ADB_IDENTITY["size"]
        or type(value.sha256) is not str
        or value.sha256 != ADB_IDENTITY["sha256"]
    ):
        raise AdbProxyV1Error("held ADB bytes differ")


def _validate_bound_server(
    server: BoundServerIdentity, held_adb: HeldAdbFileIdentity
) -> None:
    _validate_held_adb(held_adb)
    if type(server) is not BoundServerIdentity:
        raise AdbProxyV1Error("bound ADB server identity differs")
    for label, value in (
        ("server pid", server.pid),
        ("server start ticks", server.start_ticks),
        ("server listener fd", server.listener_fd),
        ("server listener inode", server.listener_inode),
        ("server executable device", server.executable_device),
        ("server executable inode", server.executable_inode),
        ("server executable size", server.executable_size),
    ):
        _require_exact_positive_int(value, label)
    if type(server.uid) is not int or server.uid < 0:
        raise AdbProxyV1Error("server uid differs")
    if server.pidfd_bound is not True:
        raise AdbProxyV1Error("bound server pidfd continuity differs")
    if (
        type(server.executable_sha256) is not str
        or HEX64_RE.fullmatch(server.executable_sha256) is None
        or server.executable_sha256 != ADB_IDENTITY["sha256"]
        or server.executable_size != ADB_IDENTITY["size"]
        or server.executable_device != held_adb.device
        or server.executable_inode != held_adb.inode
    ):
        raise AdbProxyV1Error("bound server executable is not the exact ADB")


def validate_established_peer(
    proof: EstablishedPeerProof,
    server: BoundServerIdentity,
    held_adb: HeldAdbFileIdentity,
) -> None:
    """Bind one upstream ESTABLISHED peer inode to the held server owner."""

    _validate_bound_server(server, held_adb)
    if type(proof) is not EstablishedPeerProof:
        raise AdbProxyV1Error("upstream established-peer proof is absent")
    if (
        proof.family != "AF_INET"
        or proof.state != "ESTABLISHED"
        or proof.local_address != "127.0.0.1"
        or type(proof.local_port) is not int
        or not 1 <= proof.local_port <= 65_535
        or proof.local_port == 5037
        or proof.peer_address != "127.0.0.1"
        or type(proof.peer_port) is not int
        or proof.peer_port != 5037
    ):
        raise AdbProxyV1Error("upstream connection tuple differs")
    if (
        type(proof.server_local_address) is not str
        or type(proof.server_local_port) is not int
        or type(proof.server_observed_peer_address) is not str
        or type(proof.server_observed_peer_port) is not int
        or proof.server_local_address != proof.peer_address
        or proof.server_local_port != proof.peer_port
        or proof.server_observed_peer_address != proof.local_address
        or proof.server_observed_peer_port != proof.local_port
    ):
        raise AdbProxyV1Error("upstream established peer tuple is not reciprocal")
    for label, value in (
        ("proxy upstream socket inode", proof.proxy_socket_inode),
        ("proxy upstream socket fd", proof.proxy_socket_fd),
        ("held proxy upstream fd inode", proof.held_proxy_fd_inode),
        ("server accepted-peer inode", proof.server_peer_inode),
        ("server accepted-peer fd", proof.server_peer_fd),
    ):
        _require_exact_positive_int(value, label)
    if (
        proof.proxy_socket_inode == proof.server_peer_inode
        or proof.proxy_socket_inode == server.listener_inode
        or proof.server_peer_inode == server.listener_inode
        or proof.held_proxy_fd_inode != proof.proxy_socket_inode
        or server.listener_fd == proof.server_peer_fd
    ):
        raise AdbProxyV1Error("upstream peer inode roles overlap")
    if (
        type(proof.server_pid) is not int
        or type(proof.server_uid) is not int
        or type(proof.server_start_ticks) is not int
        or type(proof.server_listener_inode) is not int
        or proof.server_pid != server.pid
        or proof.server_uid != server.uid
        or proof.server_start_ticks != server.start_ticks
        or proof.server_listener_inode != server.listener_inode
    ):
        raise AdbProxyV1Error("upstream peer owner drifted from bound server")
    if (
        type(proof.observed_owner_fd_inodes) is not tuple
        or len(proof.observed_owner_fd_inodes) == 0
        or len(proof.observed_owner_fd_inodes) > 4_096
        or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not int
            or item[0] < 0
            or type(item[1]) is not int
            or item[1] <= 0
            for item in proof.observed_owner_fd_inodes
        )
        or len(set(proof.observed_owner_fd_inodes))
        != len(proof.observed_owner_fd_inodes)
        or len({item[0] for item in proof.observed_owner_fd_inodes})
        != len(proof.observed_owner_fd_inodes)
        or (server.listener_fd, server.listener_inode)
        not in proof.observed_owner_fd_inodes
        or (proof.server_peer_fd, proof.server_peer_inode)
        not in proof.observed_owner_fd_inodes
    ):
        raise AdbProxyV1Error("upstream peer inode is not owned by bound server pid")


def _forbidden_service(services: Sequence[str]) -> str | None:
    for service in services:
        if service in FORBIDDEN_SERVICES or service.startswith("host:kill:"):
            return service
        if service.startswith("host:start-server:"):
            return service
    return None


def _event(events: tuple[WireEvent, ...], index: int, kind: str) -> bytes:
    if index >= len(events):
        raise AdbProxyV1Error("ordered wire event is missing")
    value = events[index]
    if type(value) is not WireEvent or value.kind != kind or type(value.payload) is not bytes:
        raise AdbProxyV1Error("ordered wire event kind or bytes differ")
    return value.payload


def _decode_one_request(raw: bytes) -> str:
    services = decode_request_stream((raw,))
    forbidden = _forbidden_service(services)
    if forbidden is not None:
        raise AdbProxyV1Error(f"forbidden ADB service attempted: {forbidden}")
    if len(services) != 1:
        raise AdbProxyV1Error("one ordered request event contains repeated frames")
    return services[0]


def _validate_protocol_string(raw: bytes) -> None:
    if type(raw) is not bytes or len(raw) < 4:
        raise AdbProxyV1Error("partial upstream protocol string")
    header = raw[:4]
    if HEX_LENGTH_RE.fullmatch(header) is None:
        raise AdbProxyV1Error("upstream protocol-string length encoding differs")
    length = int(header, 16)
    if length > 65_535 or len(raw) != 4 + length:
        raise AdbProxyV1Error("partial or oversized upstream protocol string")


def _validate_ordered_events(
    connection: ConnectionTrace, wanted: ConnectionExpectation
) -> tuple[str, ...]:
    """Validate normalized logical events in exact causal wire order.

    This is a post-run H0 audit model.  Socket-read fragmentation and the
    incremental parser that would emit these logical events are not
    implemented by this source.
    """

    if type(connection.events) is not tuple:
        raise AdbProxyV1Error("ordered wire event sequence differs")
    kinds = tuple(
        value.kind if type(value) is WireEvent else "<invalid>"
        for value in connection.events
    )
    if kinds != wanted.event_order:
        raise AdbProxyV1Error("ADB request/response event order differs")

    if not wanted.upstream:
        service = _decode_one_request(_event(connection.events, 0, "downstream-request"))
        if service != LOCAL_VERSION_SERVICE:
            raise AdbProxyV1Error("local host:version request differs")
        if (
            _event(connection.events, 1, "proxy-to-downstream-local-version")
            != LOCAL_VERSION_RESPONSE
            or _event(connection.events, 2, "downstream-eof") != b""
        ):
            raise AdbProxyV1Error("local host:version isolation differs")
        return (service,)

    first_request = _event(connection.events, 0, "downstream-request")
    first_service = _decode_one_request(first_request)
    if _event(connection.events, 1, "proxy-to-upstream-request") != first_request:
        raise AdbProxyV1Error("first upstream request relay bytes differ")
    if (
        _event(connection.events, 2, "upstream-to-proxy-status") != b"OKAY"
        or _event(connection.events, 3, "proxy-to-downstream-status") != b"OKAY"
    ):
        raise AdbProxyV1Error("first upstream status relay differs")

    if wanted.requires_transport_id:
        upstream_id = _event(
            connection.events, 4, "upstream-to-proxy-transport-id"
        )
        downstream_id = _event(
            connection.events, 5, "proxy-to-downstream-transport-id"
        )
        if (
            len(upstream_id) != 8
            or int.from_bytes(upstream_id, "little", signed=False) == 0
            or downstream_id != upstream_id
        ):
            raise AdbProxyV1Error(
                "transport-id is not an exact relayed nonzero uint64le"
            )
        second_request = _event(connection.events, 6, "downstream-request")
        second_service = _decode_one_request(second_request)
        if _event(connection.events, 7, "proxy-to-upstream-request") != second_request:
            raise AdbProxyV1Error("second upstream request relay bytes differ")
        if (
            _event(connection.events, 8, "upstream-to-proxy-status") != b"OKAY"
            or _event(connection.events, 9, "proxy-to-downstream-status") != b"OKAY"
        ):
            raise AdbProxyV1Error("second upstream status relay differs")
        upstream_output = _event(connection.events, 10, "upstream-to-proxy-output")
        downstream_output = _event(connection.events, 11, "proxy-to-downstream-output")
        if len(upstream_output) > MAX_RELAY_OUTPUT_BYTES:
            raise AdbProxyV1Error("upstream output exceeds reviewed relay bound")
        if downstream_output != upstream_output:
            raise AdbProxyV1Error("upstream output relay bytes differ")
        if (
            _event(connection.events, 12, "upstream-eof") != b""
            or _event(connection.events, 13, "downstream-eof") != b""
        ):
            raise AdbProxyV1Error("exec relay EOF choreography differs")
        services = (first_service, second_service)
    else:
        upstream_value = _event(
            connection.events, 4, "upstream-to-proxy-protocol-string"
        )
        downstream_value = _event(
            connection.events, 5, "proxy-to-downstream-protocol-string"
        )
        _validate_protocol_string(upstream_value)
        if downstream_value != upstream_value:
            raise AdbProxyV1Error("protocol-string relay bytes differ")
        if (
            _event(connection.events, 6, "upstream-eof") != b""
            or _event(connection.events, 7, "downstream-eof") != b""
        ):
            raise AdbProxyV1Error("query relay EOF choreography differs")
        services = (first_service,)

    if services != wanted.services:
        raise AdbProxyV1Error("ordinal downstream frame sequence differs")
    return services


def validate_proxy_trace(
    trace: ProxyTrace,
    serial: str,
    server: BoundServerIdentity,
) -> dict[str, Any]:
    """Validate a complete pure-data trace for exactly one command attempt."""

    if type(trace) is not ProxyTrace:
        raise AdbProxyV1Error("proxy trace type differs")
    expected = expected_connections(trace.ordinal, serial)
    _validate_child_identity(trace.child)
    _validate_bound_server(server, trace.held_adb)
    if server.uid != trace.child.uid:
        raise AdbProxyV1Error("ADB server and direct child effective uid differ")
    if server.pid == trace.child.pid:
        raise AdbProxyV1Error("ADB server and direct child pid roles overlap")
    if type(trace.command_attempt_count) is not int or trace.command_attempt_count != 1:
        raise AdbProxyV1Error("command attempt is not exactly one")
    if (
        type(trace.accepted_connection_count) is not int
        or trace.accepted_connection_count != len(expected)
        or trace.accepted_connection_count > MAX_PROXY_CONNECTIONS
    ):
        raise AdbProxyV1Error("accepted proxy connection count differs")
    expected_upstreams = sum(1 for item in expected if item.upstream)
    if (
        type(trace.upstream_connection_count) is not int
        or trace.upstream_connection_count != expected_upstreams
    ):
        raise AdbProxyV1Error("upstream connection or reconnect count differs")
    if type(trace.connections) is not tuple or len(trace.connections) != len(expected):
        raise AdbProxyV1Error("proxy connection sequence differs")

    forwarded: list[str] = []
    for index, (connection, wanted) in enumerate(zip(trace.connections, expected), 1):
        if type(connection) is not ConnectionTrace or connection.index != index:
            raise AdbProxyV1Error("proxy connection index differs")
        validate_peer_credentials(connection.peer, trace.child)
        if type(connection.reconnect_count) is not int or connection.reconnect_count != 0:
            raise AdbProxyV1Error("proxy reconnect is forbidden")
        if wanted.upstream:
            if connection.upstream is None:
                raise AdbProxyV1Error("upstream established-peer proof is absent")
            validate_established_peer(connection.upstream, server, trace.held_adb)
        else:
            if connection.upstream is not None:
                raise AdbProxyV1Error("local host:version isolation differs")
        # The held upstream owner proof is a precondition.  No modeled first
        # upstream request event is accepted before that proof validates.
        services = _validate_ordered_events(connection, wanted)
        if wanted.upstream:
            forwarded.extend(services)

    allowlist = upstream_allowlist(trace.ordinal, serial)
    if tuple(forwarded) != allowlist:
        raise AdbProxyV1Error("forwarded service set differs from ordinal allowlist")
    if LOCAL_VERSION_SERVICE in forwarded or any(
        value in FORBIDDEN_SERVICES for value in forwarded
    ):
        raise AdbProxyV1Error("locally handled or forbidden service was forwarded")
    return {
        "schema": f"{SCHEMA}_trace_result",
        "ordinal": trace.ordinal,
        "accepted": True,
        "command_attempt_count": 1,
        "proxy_connections": len(expected),
        "upstream_connections": expected_upstreams,
        "forwarded_services": list(forwarded),
        "host_version_forwarded": False,
        "upstream_version_frame_forwarded": False,
        "host_kill_forwarded": False,
        "host_start_server_forwarded": False,
        "reconnects": 0,
    }


def _operational_gates() -> dict[str, bool]:
    return {
        "adb_proxy_v1_reviewed": ADB_PROXY_V1_REVIEWED,
        "phase_a_exact_bound": PHASE_A_EXACT_BOUND,
        "runtime_exact_bound": RUNTIME_EXACT_BOUND,
        "adb_exact_bound": ADB_EXACT_BOUND,
        "private_af_unix_proxy_implemented": PRIVATE_AF_UNIX_PROXY_IMPLEMENTED,
        "child_peer_credentials_enforced": CHILD_PEER_CREDENTIALS_ENFORCED,
        "upstream_server_binding_enforced": UPSTREAM_SERVER_BINDING_ENFORCED,
        "downstream_transcript_enforced": DOWNSTREAM_TRANSCRIPT_ENFORCED,
        "child_seccomp_filter_reviewed": CHILD_SECCOMP_FILTER_REVIEWED,
        "child_seccomp_filter_installed": CHILD_SECCOMP_FILTER_INSTALLED,
        "executor_implemented": EXECUTOR_IMPLEMENTED,
        "same_process_handoff_implemented": SAME_PROCESS_HANDOFF_IMPLEMENTED,
        "target_coordination_active": TARGET_COORDINATION_ACTIVE,
        "cross_code_coordination_active": CROSS_CODE_COORDINATION_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }


def _require_operational_gate() -> None:
    # Pure gate: no file, process, socket, network, clock, USB, or device read.
    if not all(value is True for value in _operational_gates().values()):
        raise AdbProxyV1Error("restricted ADB proxy candidate is inactive")


def attended_open_and_read() -> None:
    """Future no-input entrypoint.  This H0 model is never an executor."""

    _require_operational_gate()
    raise AdbProxyV1Error("restricted ADB proxy executor is not implemented")


def normalized_source_sha256(source: bytes) -> str:
    if type(source) is not bytes or not source:
        raise AdbProxyV1Error("source bytes are absent")
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        source,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if status_count != 1 or anchor_count != 1:
        raise AdbProxyV1Error("source identity normalization is ambiguous")
    for name in NORMALIZED_GATE_NAMES:
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode("ascii"),
            f"{name} = <REVIEWED_BOOLEAN>".encode("ascii"),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise AdbProxyV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_self_bytes() -> bytes:
    descriptor = os.open(Path(__file__), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > 128 * 1024
        ):
            raise AdbProxyV1Error("proxy model source identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise AdbProxyV1Error("proxy model source length differs")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise AdbProxyV1Error("proxy model source changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    normalized_sha256 = normalized_source_sha256(source)
    if normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise AdbProxyV1Error("proxy model normalized source identity differs")
    gates = _operational_gates()
    if any(gates.values()):
        raise AdbProxyV1Error("H0 render found an active gate")
    ordinal_protocol = {
        str(ordinal): [
            {
                "role": item.role,
                "downstream_services": list(item.services),
                "upstream": item.upstream,
                "response_mode": item.response_mode,
                "requires_transport_id": item.requires_transport_id,
                "event_order": list(item.event_order),
            }
            for item in expected_connections(ordinal, "BOUND_SERIAL")
        ]
        for ordinal in range(1, 7)
    }
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_sha256,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "target": dict(TARGET),
        "authority": {
            "tier": "H0",
            "device_contact": False,
            "adb_executed": False,
            "real_socket_or_network_used": False,
            "proxy_implemented": False,
            "seccomp_implemented": False,
            "executor_implemented": False,
            "live_authority": False,
        },
        "gates": gates,
        "pinned_identities": {
            "phase_a": _plain(PHASE_A_IDENTITY),
            "runtime": _plain(RUNTIME_IDENTITY),
            "adb": _plain(ADB_IDENTITY),
        },
        "private_proxy": {
            "family": PRIVATE_PROXY_FAMILY,
            "socket_spec_model": PRIVATE_PROXY_SOCKET_SPEC,
            "parent_mode": "0700",
            "caller_supplied_path": False,
            "exact_direct_child_peer": [
                "pid",
                "uid",
                "gid",
                "SO_PEERCRED",
                "process-start-ticks",
                "held-direct-child-pidfd",
            ],
            "effective_uid_axis": "direct-child-SO_PEERCRED-uid-equals-server-uid",
            "runtime-effective-uid-receipt-integrated": False,
            "connection_count_max": MAX_PROXY_CONNECTIONS,
            "reconnects": 0,
            "implemented": False,
        },
        "version_isolation": {
            "request": LOCAL_VERSION_SERVICE,
            "local_response_hex": LOCAL_VERSION_RESPONSE.hex(),
            "version_payload": LOCAL_VERSION_PAYLOAD,
            "forwarded_upstream": False,
            "upstream_version_frame_forwarded": False,
            "separate_upstream_version_connection": False,
            "server_version_basis": (
                "exact-held-ADB-executable-plus-server-pidfd-start-listener-"
                "and-established-accepted-peer-binding"
            ),
            "host_kill_forwarded": False,
            "host_start_server_forwarded": False,
            "unavailable_proxy_can_trigger_local_server_launch_attempt": True,
            "launch_attempt_blocked_only_by_preinstalled_seccomp": (
                "DESIGNED_NOT_IMPLEMENTED_OR_PROVED"
            ),
        },
        "upstream_binding": {
            "server_socket": ADB_SERVER_SOCKET,
            "server_listen_hex": ADB_SERVER_LISTEN_HEX,
            "one_established_connection_per_service_connection": True,
            "one_upstream_connection_per_nonlocal-command": True,
            "upstream_version_preflight_connection": False,
            "peer_owner": [
                "bound-server-pid",
                "bound-server-uid",
                "bound-server-start-ticks",
                "listener-inode",
                "accepted-peer-inode",
                "server-fd-to-listener-and-accepted-inode-map",
                "reciprocal-client-and-server-TCP-tuples",
                "held-proxy-upstream-fd-to-client-inode",
            ],
            "reconnect": False,
            "implemented": False,
            "real-observer-and-event-emitter_implemented": False,
            "peer_proof_validated_before_first_upstream_request": True,
        },
        "ordinal_protocol": ordinal_protocol,
        "wire_event_model": {
            "typed_direction_and_exact_bytes": True,
            "causal_event_order_validated": True,
            "status_transport_id_output_and_eof_relay_validated": True,
            "output_byte_cap": MAX_RELAY_OUTPUT_BYTES,
            "post_run_audit_only": True,
            "incremental_socket_parser_implemented": False,
            "socket_fragmentation_enforcement_proved": False,
        },
        "fixed_exec_out": {
            "snapshot_size": REMOTE_SNAPSHOT_SIZE,
            "snapshot_sha256": REMOTE_SNAPSHOT_SHA256,
            "service_size": EXEC_SERVICE_SIZE,
            "service_sha256": EXEC_SERVICE_SHA256,
            "construction": "argv1-raw-then-ADB-escape_arg-for-each-remaining-argv",
        },
        "upstream_allowlist_templates": {
            str(ordinal): list(upstream_allowlist(ordinal, "BOUND_SERIAL"))
            for ordinal in range(1, 7)
        },
        "forbidden_services": sorted(FORBIDDEN_SERVICES),
        "bounds": {
            "service_bytes": MAX_SERVICE_BYTES,
            "frame_stream_bytes": MAX_FRAME_STREAM_BYTES,
            "relay_output_bytes": MAX_RELAY_OUTPUT_BYTES,
            "frames_per_connection": MAX_FRAME_COUNT,
            "connections_per_command": MAX_PROXY_CONNECTIONS,
            "command_attempts": 1,
        },
        "seccomp_policy_model": _plain(SECCOMP_POLICY_MODEL),
        "cli": ["--render-plan"],
        "caller_inputs": [],
        "callbacks": [],
        "connected_backends": [],
        "device_commands": [],
        "root_commands": [],
        "odin_commands": [],
        "partition_transfers": [],
        "private_writes": [],
        "unresolved_gates": [
            "exact-AF_UNIX-proxy-owner-and-lifecycle",
            "exact-upstream-established-peer-observer",
            "exact-child-SO_PEERCRED-and-start-time-owner",
            "runtime-effective-uid-receipt-composition",
            "exact-ADB-wire-transcript-capture-against-pinned-binary",
            "incremental-fragment-safe-socket-parser-and-event-emitter",
            "architecture-complete-seccomp-BPF-bytes-and-install-order",
            "closed-no-input-executor-call-graph",
            "same-process-runtime-and-campaign-handoff",
            "cross-code-interlock-and-recovery-integration",
            "combined-independent-review",
            "target-contract-and-mechanical-activation",
            "fresh-attended-opening-request",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.render_plan:
        raise AdbProxyV1Error("only the H0 render mode exists")
    print(json.dumps(render_plan(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
