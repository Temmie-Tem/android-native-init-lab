#!/usr/bin/env python3
"""Inactive pure H0 transcript model for the S20+ restricted ADB proxy.

This file is not a socket owner, proxy, ADB launcher, connected executor, or
wire-evidence collector. A caller may select an exact immutable transcript of
typed downstream/upstream/EOF/timeout fragments. One function call first
validates all caller-supplied model input without constructing relay emissions,
then derives a fresh frozen emission tuple only after complete acceptance.
Acceptance proves only that the supplied bytes satisfy this deterministic
model; it does not authenticate real wire observation.

There is no caller-supplied sink, callback, backend, mutable ledger, import-
visible reducer, or reusable session. No partial result is exposed: the only
rejecting pass constructs no ``RelayEmission`` object or accumulator. A modeled
upstream request is derived only in the success-only second pass after one
complete frame exactly matches the ordinal closure. All operational gates
remain false, and the CLI only renders a static plan.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping, NamedTuple, Sequence


STATUS = (
    "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_INCREMENTAL_V1_"
    "MODEL_PASS_GO_NOT_ACTIVE"
)
SCHEMA = "s20plus_g986n_autonomous_public_health_adb_proxy_incremental_v1_h0"
EXPECTED_SELF_NORMALIZED_SHA256 = "ec1dcd8236f6778bdf6994b5d1a9a26132e95d92d9ce8955cfba08122c95a2cc"

INCREMENTAL_V1_REVIEWED = False
PROXY_AUDIT_EXACT_BOUND = False
PHASE_A_EXACT_BOUND = False
RUNTIME_EXACT_BOUND = False
ADB_EXACT_BOUND = False
POSIX_SOCKET_OWNER_IMPLEMENTED = False
AF_UNIX_ACCEPTOR_IMPLEMENTED = False
CHILD_PEER_CREDENTIALS_ENFORCED = False
UPSTREAM_SERVER_BINDING_ENFORCED = False
INCREMENTAL_FIREWALL_ENFORCED = False
OUTPUT_RELAY_ENFORCED = False
NO_RECONNECT_ENFORCED = False
CHILD_SECCOMP_FILTER_REVIEWED = False
CHILD_SECCOMP_FILTER_INSTALLED = False
EXECUTOR_IMPLEMENTED = False
JOURNAL_EVIDENCE_INTEGRATED = False
SAME_PROCESS_HANDOFF_IMPLEMENTED = False
RECOVERY_INTEGRATED = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

NORMALIZED_GATE_NAMES = (
    "INCREMENTAL_V1_REVIEWED",
    "PROXY_AUDIT_EXACT_BOUND",
    "PHASE_A_EXACT_BOUND",
    "RUNTIME_EXACT_BOUND",
    "ADB_EXACT_BOUND",
    "POSIX_SOCKET_OWNER_IMPLEMENTED",
    "AF_UNIX_ACCEPTOR_IMPLEMENTED",
    "CHILD_PEER_CREDENTIALS_ENFORCED",
    "UPSTREAM_SERVER_BINDING_ENFORCED",
    "INCREMENTAL_FIREWALL_ENFORCED",
    "OUTPUT_RELAY_ENFORCED",
    "NO_RECONNECT_ENFORCED",
    "CHILD_SECCOMP_FILTER_REVIEWED",
    "CHILD_SECCOMP_FILTER_INSTALLED",
    "EXECUTOR_IMPLEMENTED",
    "JOURNAL_EVIDENCE_INTEGRATED",
    "SAME_PROCESS_HANDOFF_IMPLEMENTED",
    "RECOVERY_INTEGRATED",
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
PROXY_AUDIT_IDENTITY = MappingProxyType(
    {
        "commit": "d561226f108869614128db9e46ea050c4a94b58c",
        "path": (
            "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
            "revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py"
        ),
        "size": 46_477,
        "sha256": "18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92",
        "normalized_sha256": (
            "8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9"
        ),
        "status": (
            "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_"
            "PASS_GO_NOT_ACTIVE"
        ),
    }
)

LOCAL_VERSION_SERVICE = "host:version"
LOCAL_VERSION_RESPONSE = b"OKAY00040029"
DEVICES_LONG_SERVICE = "host:devices-l"
MAX_SERVICE_BYTES = 4_096
MAX_REQUEST_FRAME_BYTES = 4 + MAX_SERVICE_BYTES
MAX_DOWNSTREAM_FRAGMENTS_PER_CONNECTION = 4_096
MAX_UPSTREAM_FRAGMENTS_PER_CONNECTION = 256
MAX_PROTOCOL_PAYLOAD_BYTES = 65_535
MAX_RELAY_OUTPUT_BYTES = 65_536
MAX_CONNECTIONS = 2
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
HEX_LENGTH_RE = re.compile(rb"[0-9a-f]{4}\Z")
EVENT_KINDS = frozenset(
    {"downstream", "upstream", "downstream-eof", "upstream-eof", "timeout"}
)


class IncrementalProxyV1Error(RuntimeError):
    """Any ambiguity, unexpected byte, or attempted activation stops."""


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
    if type(value) is not str or "\x00" in value:
        raise IncrementalProxyV1Error("fixed ADB exec argument differs")
    return "'" + value.replace("'", "'\\''") + "'"


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


class TranscriptFragment(NamedTuple):
    """One exact caller-selected model input fragment."""

    kind: str
    connection: int
    payload: bytes = b""


@dataclass(frozen=True, slots=True)
class RelayEmission:
    channel: str
    connection: int
    component: str
    frame: int | None
    payload: bytes


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    index: int
    role: str
    request_frames: int
    upstream_request_frames: int
    local_response: bool
    output_bytes: int


@dataclass(frozen=True, slots=True)
class ValidationResult:
    schema: str
    ordinal: int
    accepted: bool
    connections: int
    upstream_request_frames: int
    local_version_forwarded: bool
    reconnects: int
    results: tuple[ConnectionResult, ...]
    emissions: tuple[RelayEmission, ...]

    @property
    def upstream_bytes(self) -> bytes:
        return b"".join(
            item.payload for item in self.emissions if item.channel == "upstream"
        )

    @property
    def downstream_bytes(self) -> bytes:
        return b"".join(
            item.payload for item in self.emissions if item.channel == "downstream"
        )

    def upstream_bytes_for_frame(self, connection: int, frame: int) -> bytes:
        if type(connection) is not int or connection <= 0:
            raise IncrementalProxyV1Error("connection selector differs")
        if type(frame) is not int or frame <= 0:
            raise IncrementalProxyV1Error("frame selector differs")
        return b"".join(
            item.payload
            for item in self.emissions
            if item.channel == "upstream"
            and item.connection == connection
            and item.frame == frame
        )


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise IncrementalProxyV1Error("digest input is not exact bytes")
    return hashlib.sha256(payload).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _validate_serial(serial: str) -> None:
    if type(serial) is not str or SERIAL_RE.fullmatch(serial) is None:
        raise IncrementalProxyV1Error("bound serial grammar differs")


def encode_request(service: str) -> bytes:
    if type(service) is not str:
        raise IncrementalProxyV1Error("ADB service is not exact text")
    try:
        payload = service.encode("utf-8")
    except UnicodeError as exc:
        raise IncrementalProxyV1Error("ADB service encoding differs") from exc
    if not payload or len(payload) > MAX_SERVICE_BYTES or b"\x00" in payload:
        raise IncrementalProxyV1Error("ADB service exceeds the fixed request bound")
    return f"{len(payload):04x}".encode("ascii") + payload


def _validate_fixed_exec() -> None:
    snapshot = REMOTE_SNAPSHOT.encode("utf-8")
    service = EXEC_SERVICE.encode("utf-8")
    if (
        len(snapshot) != REMOTE_SNAPSHOT_SIZE
        or sha256_bytes(snapshot) != REMOTE_SNAPSHOT_SHA256
        or len(service) != EXEC_SERVICE_SIZE
        or sha256_bytes(service) != EXEC_SERVICE_SHA256
    ):
        raise IncrementalProxyV1Error("fixed Phase-A exec service bytes differ")


def _services_for_ordinal(ordinal: int, serial: str) -> tuple[tuple[str, ...], ...]:
    if type(ordinal) is not int or not 1 <= ordinal <= 6:
        raise IncrementalProxyV1Error("opening command ordinal differs")
    _validate_serial(serial)
    _validate_fixed_exec()
    if ordinal == 1:
        return ()
    if ordinal in (2, 6):
        service = (DEVICES_LONG_SERVICE,)
    elif ordinal == 3:
        service = (f"host-serial:{serial}:get-devpath",)
    else:
        service = (f"host:tport:serial:{serial}", EXEC_SERVICE)
    return ((LOCAL_VERSION_SERVICE,), service)


def _validate_transcript_shape(transcript: tuple[TranscriptFragment, ...]) -> None:
    if type(transcript) is not tuple:
        raise IncrementalProxyV1Error("transcript is not an exact immutable tuple")
    for item in transcript:
        if type(item) is not TranscriptFragment:
            raise IncrementalProxyV1Error("transcript fragment type differs")
        if type(item.kind) is not str or item.kind not in EVENT_KINDS:
            raise IncrementalProxyV1Error("transcript fragment kind differs")
        if type(item.connection) is not int or item.connection <= 0:
            raise IncrementalProxyV1Error("transcript connection differs")
        if type(item.payload) is not bytes:
            raise IncrementalProxyV1Error("transcript payload is not exact bytes")
        if item.kind in ("downstream", "upstream"):
            if not item.payload:
                raise IncrementalProxyV1Error("byte fragment is empty")
        elif item.payload != b"":
            raise IncrementalProxyV1Error("terminal fragment payload differs")


def validate_transcript(
    ordinal: int,
    serial: str,
    transcript: tuple[TranscriptFragment, ...],
) -> ValidationResult:
    """Validate one caller-selected transcript without exposing partial state."""

    closure = _services_for_ordinal(ordinal, serial)
    _validate_transcript_shape(transcript)
    if not closure:
        if transcript:
            raise IncrementalProxyV1Error("ordinal one accepts no connection event")
        return ValidationResult(
            f"{SCHEMA}_validation_result", ordinal, True, 0, 0, False, 0, (), ()
        )
    boundary = None
    previous_connection = 1
    for position, event in enumerate(transcript):
        if event.connection > MAX_CONNECTIONS:
            raise IncrementalProxyV1Error("extra proxy connection is forbidden")
        if event.connection not in (1, 2):
            raise IncrementalProxyV1Error("connection index is reordered or reconnects")
        if event.connection < previous_connection:
            raise IncrementalProxyV1Error("connection index is reordered or reconnects")
        if event.connection > previous_connection:
            if event.connection != 2 or boundary is not None:
                raise IncrementalProxyV1Error("connection index is reordered or reconnects")
            boundary = position
            previous_connection = event.connection
    if boundary is None or boundary == 0:
        raise IncrementalProxyV1Error("connection transcript is incomplete")
    event_groups = (transcript[:boundary], transcript[boundary:])

    def validate_connection(
        events: tuple[TranscriptFragment, ...], index: int, services: tuple[str, ...]
    ) -> ConnectionResult:
        """First pass: validate with scalar/bytes state and create no emissions."""

        role = "local-version" if services == (LOCAL_VERSION_SERVICE,) else (
            "transport-exec" if len(services) == 2 else "query"
        )
        state = "WAIT_DOWNSTREAM_FRAME"
        downstream_buffer = b""
        upstream_buffer = b""
        downstream_fragments = 0
        upstream_fragments = 0
        next_frame = 1
        upstream_request_frames = 0
        output_bytes = 0
        complete = False

        for event in events:
            if event.connection != index:
                raise IncrementalProxyV1Error("connection index is reordered or reconnects")
            if complete:
                raise IncrementalProxyV1Error("event follows completed connection")
            if event.kind == "downstream":
                downstream_fragments += 1
                if downstream_fragments > MAX_DOWNSTREAM_FRAGMENTS_PER_CONNECTION:
                    raise IncrementalProxyV1Error("downstream fragment count exceeds bound")
                if state != "WAIT_DOWNSTREAM_FRAME":
                    raise IncrementalProxyV1Error(
                        "downstream request is reordered before its response"
                    )
                if next_frame > len(services):
                    raise IncrementalProxyV1Error("extra downstream request frame is forbidden")
                expected = encode_request(services[next_frame - 1])
                if len(downstream_buffer) + len(event.payload) > MAX_REQUEST_FRAME_BYTES:
                    raise IncrementalProxyV1Error("downstream request frame exceeds bound")
                downstream_buffer += event.payload
                if not expected.startswith(downstream_buffer):
                    raise IncrementalProxyV1Error(
                        "downstream bytes differ from the exact ordinal frame"
                    )
                if len(downstream_buffer) < len(expected):
                    continue
                downstream_buffer = b""
                if role == "local-version":
                    next_frame += 1
                    complete = True
                    state = "COMPLETE"
                    continue
                upstream_request_frames += 1
                frame = next_frame
                next_frame += 1
                if role == "transport-exec" and frame == 1:
                    state = "WAIT_TPORT_STATUS"
                elif role == "query":
                    state = "WAIT_QUERY_STATUS"
                else:
                    state = "WAIT_EXEC_STATUS"
                continue

            if event.kind == "upstream":
                upstream_fragments += 1
                if upstream_fragments > MAX_UPSTREAM_FRAGMENTS_PER_CONNECTION:
                    raise IncrementalProxyV1Error("upstream fragment count exceeds bound")
                if state in ("WAIT_DOWNSTREAM_FRAME", "WAIT_QUERY_EOF"):
                    raise IncrementalProxyV1Error("upstream bytes are reordered or extra")
                if state == "RELAY_EXEC_OUTPUT":
                    if output_bytes + len(event.payload) > MAX_RELAY_OUTPUT_BYTES:
                        raise IncrementalProxyV1Error("exec output exceeds the relay bound")
                    output_bytes += len(event.payload)
                    continue
                if len(upstream_buffer) + len(event.payload) > (
                    4 + 8 + MAX_PROTOCOL_PAYLOAD_BYTES
                ):
                    raise IncrementalProxyV1Error(
                        "upstream response buffering exceeds bound"
                    )
                upstream_buffer += event.payload
                while upstream_buffer:
                    if state in ("WAIT_TPORT_STATUS", "WAIT_QUERY_STATUS", "WAIT_EXEC_STATUS"):
                        common = min(len(upstream_buffer), 4)
                        if upstream_buffer[:common] != b"OKAY"[:common]:
                            label = {
                                "WAIT_TPORT_STATUS": "tport status",
                                "WAIT_QUERY_STATUS": "query status",
                                "WAIT_EXEC_STATUS": "exec status",
                            }[state]
                            raise IncrementalProxyV1Error(f"upstream {label} differs")
                        if len(upstream_buffer) < 4:
                            break
                        upstream_buffer = upstream_buffer[4:]
                        if state == "WAIT_TPORT_STATUS":
                            state = "WAIT_TPORT_ID"
                        elif state == "WAIT_QUERY_STATUS":
                            state = "WAIT_QUERY_PROTOCOL_STRING"
                        else:
                            state = "RELAY_EXEC_OUTPUT"
                            if upstream_buffer:
                                if output_bytes + len(upstream_buffer) > MAX_RELAY_OUTPUT_BYTES:
                                    raise IncrementalProxyV1Error(
                                        "exec output exceeds the relay bound"
                                    )
                                output_bytes += len(upstream_buffer)
                                upstream_buffer = b""
                        continue
                    if state == "WAIT_TPORT_ID":
                        if len(upstream_buffer) < 8:
                            break
                        transport_id = upstream_buffer[:8]
                        upstream_buffer = upstream_buffer[8:]
                        if int.from_bytes(transport_id, "little", signed=False) == 0:
                            raise IncrementalProxyV1Error("transport ID is zero")
                        state = "WAIT_DOWNSTREAM_FRAME"
                        if upstream_buffer:
                            raise IncrementalProxyV1Error(
                                "upstream bytes arrived before the exec request"
                            )
                        break
                    if state == "WAIT_QUERY_PROTOCOL_STRING":
                        if len(upstream_buffer) < 4:
                            if any(
                                value not in b"0123456789abcdef"
                                for value in upstream_buffer
                            ):
                                raise IncrementalProxyV1Error(
                                    "upstream protocol length encoding differs"
                                )
                            break
                        header = upstream_buffer[:4]
                        if HEX_LENGTH_RE.fullmatch(header) is None:
                            raise IncrementalProxyV1Error(
                                "upstream protocol length encoding differs"
                            )
                        length = int(header, 16)
                        if length > MAX_PROTOCOL_PAYLOAD_BYTES:
                            raise IncrementalProxyV1Error(
                                "upstream protocol payload exceeds bound"
                            )
                        total = 4 + length
                        if len(upstream_buffer) < total:
                            break
                        if len(upstream_buffer) > total:
                            raise IncrementalProxyV1Error(
                                "extra upstream bytes follow the protocol response"
                            )
                        upstream_buffer = b""
                        state = "WAIT_QUERY_EOF"
                        break
                    raise IncrementalProxyV1Error(
                        "upstream parser entered an impossible state"
                    )
                continue

            if event.kind == "upstream-eof":
                if upstream_buffer:
                    raise IncrementalProxyV1Error(
                        "upstream EOF left an incomplete response component"
                    )
                if state not in ("WAIT_QUERY_EOF", "RELAY_EXEC_OUTPUT"):
                    raise IncrementalProxyV1Error("upstream EOF is reordered")
                if downstream_buffer:
                    raise IncrementalProxyV1Error(
                        "connection completion retained unparsed bytes"
                    )
                complete = True
                state = "COMPLETE"
                continue
            if event.kind == "downstream-eof":
                if downstream_buffer:
                    raise IncrementalProxyV1Error(
                        "downstream EOF left an incomplete request frame"
                    )
                raise IncrementalProxyV1Error(
                    "downstream EOF preceded exact proxy completion"
                )
            if downstream_buffer:
                raise IncrementalProxyV1Error(
                    "timeout left an incomplete downstream request frame"
                )
            if upstream_buffer:
                raise IncrementalProxyV1Error(
                    "timeout left an incomplete upstream response component"
                )
            raise IncrementalProxyV1Error("timeout preceded exact proxy completion")

        if not complete:
            raise IncrementalProxyV1Error("transcript ended before exact completion")
        return ConnectionResult(
            index,
            role,
            len(services),
            upstream_request_frames,
            role == "local-version",
            output_bytes,
        )

    # First pass is the only rejecting pass. It stores no RelayEmission and no
    # mutable emission accumulator, so a failure traceback cannot expose one.
    immutable_results = tuple(
        validate_connection(events, index, services)
        for index, (events, services) in enumerate(zip(event_groups, closure), 1)
    )

    def derive_connection_emissions(
        events: tuple[TranscriptFragment, ...], index: int, services: tuple[str, ...]
    ) -> tuple[RelayEmission, ...]:
        """Second pass over an already accepted connection; has no reject path."""

        if services == (LOCAL_VERSION_SERVICE,):
            return (
                RelayEmission(
                    "downstream", index, "exact-local-version-response", 1, LOCAL_VERSION_RESPONSE
                ),
                RelayEmission(
                    "downstream-eof", index, "proxy-close-after-exact-transcript", None, b""
                ),
            )

        derived: tuple[RelayEmission, ...] = ()
        state = "WAIT_DOWNSTREAM_FRAME"
        downstream_buffer = b""
        upstream_buffer = b""
        next_frame = 1
        for event in events:
            if event.kind == "downstream":
                downstream_buffer += event.payload
                expected = encode_request(services[next_frame - 1])
                if len(downstream_buffer) != len(expected):
                    continue
                frame = next_frame
                derived += (
                    RelayEmission(
                        "upstream", index, "complete-request-frame", frame, downstream_buffer
                    ),
                )
                downstream_buffer = b""
                next_frame += 1
                if len(services) == 2 and frame == 1:
                    state = "WAIT_TPORT_STATUS"
                elif len(services) == 1:
                    state = "WAIT_QUERY_STATUS"
                else:
                    state = "WAIT_EXEC_STATUS"
                continue
            if event.kind == "upstream-eof":
                derived += (
                    RelayEmission(
                        "downstream-eof", index, "proxy-close-after-exact-transcript", None, b""
                    ),
                )
                continue
            if event.kind != "upstream":
                continue
            if state == "RELAY_EXEC_OUTPUT":
                derived += (
                    RelayEmission("downstream", index, "bounded-exec-output", 2, event.payload),
                )
                continue
            upstream_buffer += event.payload
            while upstream_buffer:
                if state in ("WAIT_TPORT_STATUS", "WAIT_QUERY_STATUS", "WAIT_EXEC_STATUS"):
                    if len(upstream_buffer) < 4:
                        break
                    upstream_buffer = upstream_buffer[4:]
                    component = {
                        "WAIT_TPORT_STATUS": "exact-tport-status",
                        "WAIT_QUERY_STATUS": "exact-query-status",
                        "WAIT_EXEC_STATUS": "exact-exec-status",
                    }[state]
                    frame = 2 if state == "WAIT_EXEC_STATUS" else 1
                    derived += (RelayEmission("downstream", index, component, frame, b"OKAY"),)
                    if state == "WAIT_TPORT_STATUS":
                        state = "WAIT_TPORT_ID"
                    elif state == "WAIT_QUERY_STATUS":
                        state = "WAIT_QUERY_PROTOCOL_STRING"
                    else:
                        state = "RELAY_EXEC_OUTPUT"
                        if upstream_buffer:
                            derived += (
                                RelayEmission(
                                    "downstream", index, "bounded-exec-output", 2, upstream_buffer
                                ),
                            )
                            upstream_buffer = b""
                    continue
                if state == "WAIT_TPORT_ID":
                    if len(upstream_buffer) < 8:
                        break
                    transport_id = upstream_buffer[:8]
                    upstream_buffer = upstream_buffer[8:]
                    derived += (
                        RelayEmission(
                            "downstream", index, "exact-u64le-transport-id", 1, transport_id
                        ),
                    )
                    state = "WAIT_DOWNSTREAM_FRAME"
                    break
                if state == "WAIT_QUERY_PROTOCOL_STRING":
                    if len(upstream_buffer) < 4:
                        break
                    total = 4 + int(upstream_buffer[:4], 16)
                    if len(upstream_buffer) < total:
                        break
                    derived += (
                        RelayEmission(
                            "downstream", index, "exact-protocol-string", 1, upstream_buffer
                        ),
                    )
                    upstream_buffer = b""
                    state = "WAIT_QUERY_EOF"
                    break
        return derived

    immutable_emissions = tuple(
        emission
        for index, (events, services) in enumerate(zip(event_groups, closure), 1)
        for emission in derive_connection_emissions(events, index, services)
    )
    return ValidationResult(
        f"{SCHEMA}_validation_result",
        ordinal,
        True,
        len(immutable_results),
        sum(item.upstream_request_frames for item in immutable_results),
        False,
        0,
        immutable_results,
        immutable_emissions,
    )


def _operational_gates() -> dict[str, bool]:
    return {name.lower(): globals()[name] for name in NORMALIZED_GATE_NAMES}


def _require_operational_gate() -> None:
    if not all(value is True for value in _operational_gates().values()):
        raise IncrementalProxyV1Error("incremental ADB proxy candidate is inactive")


def attended_open_and_read() -> None:
    _require_operational_gate()
    raise IncrementalProxyV1Error("incremental ADB proxy executor is not implemented")


def normalized_source_sha256(source: bytes) -> str:
    if type(source) is not bytes or not source:
        raise IncrementalProxyV1Error("source bytes are absent")
    normalized, status_count = re.subn(
        rb'^STATUS = \(\n    "[A-Z0-9_]+"\n    "[A-Z0-9_]+"\n\)$',
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
        raise IncrementalProxyV1Error("source identity normalization is ambiguous")
    for name in NORMALIZED_GATE_NAMES:
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode("ascii"),
            f"{name} = <REVIEWED_BOOLEAN>".encode("ascii"),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise IncrementalProxyV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _self_bytes() -> bytes:
    payload = Path(__file__).read_bytes()
    if not payload or len(payload) > 128 * 1024:
        raise IncrementalProxyV1Error("incremental model source identity differs")
    return payload


def render_plan() -> dict[str, Any]:
    source = _self_bytes()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": _plain(TARGET),
        "self": {
            "path": str(Path(__file__).resolve()),
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_source_sha256(source),
            "expected_normalized_sha256": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "pins": {"committed_proxy_audit": _plain(PROXY_AUDIT_IDENTITY)},
        "model": {
            "input": "exact-immutable-tuple-of-exact-TranscriptFragment",
            "caller_selects_transcript": True,
            "wire_observation_authenticated": False,
            "derivation": "one-call-two-pass-fresh-deterministic-functional-validation",
            "first_pass": "full-validation-without-relay-emission-construction",
            "second_pass": "success-only-frozen-relay-emission-derivation",
            "partial_results_exposed": False,
            "caller_sink": None,
            "caller_callback": None,
            "caller_backend": None,
            "mutable_ledger": None,
            "import_visible_reducer": None,
            "reusable_session": None,
            "connections": {
                "ordinal_1": [],
                "ordinals_2_to_6": ["local-host-version", "one-service"],
            },
            "local_version_response_hex": LOCAL_VERSION_RESPONSE.hex(),
            "upstream_emit_rule": (
                "derived-only-after-one-complete-exact-ordinal-request-frame"
            ),
            "ordinal_services": {
                "2_and_6": [DEVICES_LONG_SERVICE],
                "3": ["host-serial:<bound-serial>:get-devpath"],
                "4_and_5": [
                    "host:tport:serial:<bound-serial>",
                    "exact-fixed-Phase-A-exec-service",
                ],
            },
            "no_reconnect": True,
        },
        "limits": {
            "service_bytes": MAX_SERVICE_BYTES,
            "request_frame_bytes": MAX_REQUEST_FRAME_BYTES,
            "downstream_fragments_per_connection": (
                MAX_DOWNSTREAM_FRAGMENTS_PER_CONNECTION
            ),
            "upstream_fragments_per_connection": (
                MAX_UPSTREAM_FRAGMENTS_PER_CONNECTION
            ),
            "protocol_payload_bytes": MAX_PROTOCOL_PAYLOAD_BYTES,
            "relay_output_bytes": MAX_RELAY_OUTPUT_BYTES,
            "connections": MAX_CONNECTIONS,
        },
        "gates": _operational_gates(),
        "cli": ["--render-plan"],
        "device_commands": [],
        "connected_backends": [],
        "authority": {
            "device_contact": False,
            "adb_executed": False,
            "su_executed": False,
            "odin_executed": False,
            "port_5037_opened": False,
            "posix_socket_owned": False,
            "executor_present": False,
            "live_authority": False,
        },
    }


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan is implemented")
    print(json.dumps(render_plan(), sort_keys=True, indent=2))
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
