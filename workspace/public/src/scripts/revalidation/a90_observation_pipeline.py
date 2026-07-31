#!/usr/bin/env python3
"""Pure byte, frame, and fact contracts for active A90 observations.

This module performs no device, network, subprocess, mount, flash, or reboot
operation.  Raw bytes remain immutable; decoding and classification return new
typed values.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")
UNSIGNED_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
SIGNED_DECIMAL_RE = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
FLAGS_RE = re.compile(r"^0x(?:0|[1-9a-f][0-9a-f]*)$")
STATUS_RE = re.compile(r"^[a-z][a-z0-9-]*$")
CANONICAL_STATUSES = frozenset({"ok", "error", "unknown", "busy"})
MODE_RE = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*@[1-9][0-9]*$")
DEVNO_RE = re.compile(r"^[1-9][0-9]*:[0-9]+$")
NATIVE_RELEASE_SUCCESS_RE = re.compile(
    r"^A90D3DISPLAY native_kms_release rc=0 fd_before=[0-9]+ "
    r"disable_plane_rc=0 disable_crtc_rc=0 "
    r"munmap_failures=0 rmfb_failures=0 destroy_dumb_failures=0 "
    r"drop_master_rc=0 close_rc=0 release_complete=1$"
)
NATIVE_RELEASE_EXACT_LINES = (
    "A90D3DISPLAY native_pid1_drm_fd_count=0 observed=0",
    "A90D3DISPLAY other_drm_fd_count=0 observed=0",
    "A90D3DISPLAY native_kms_initialized=0 observed=0",
    "A90D3DISPLAY display_services_restart_blocked=1 "
    "corridor=synchronous-handoff",
)
NATIVE_RELEASE_MARKER = {
    "schema": "a90-native-display-release-v1",
    "native_pid1_drm_fd_count": "0",
    "other_drm_fd_count": "0",
    "native_kms_initialized": "0",
    "display_services_restart_blocked": "1",
    "release_complete": "1",
}
BEGIN_PREFIX = "A90P1 BEGIN "
END_PREFIX = "A90P1 END "
BEGIN_KEY_ORDER = ("seq", "cmd", "argc", "flags")
END_KEY_ORDER = (
    "seq",
    "cmd",
    "rc",
    "errno",
    "duration_ms",
    "flags",
    "status",
)


class ObservationContractError(RuntimeError):
    """Raised when immutable observation input violates its exact contract."""


class LineEnding(str, Enum):
    LF = "LF"
    CRLF = "CRLF"
    EOF = "EOF"


class FactState(str, Enum):
    PROVEN = "PROVEN"
    REFUTED = "REFUTED"
    UNKNOWN = "UNKNOWN"


class FrameTrust(str, Enum):
    STRUCTURAL_ONLY = "A90P1_V1_STRUCTURAL_ONLY"


class TransitionReason(str, Enum):
    ONE_WAY_EXEC_DISCONTINUITY = "ONE_WAY_EXEC_DISCONTINUITY"


@dataclass(frozen=True)
class DecodedLine:
    text: str
    byte_start: int
    content_end: int
    byte_end: int
    ending: LineEnding


@dataclass(frozen=True)
class DecodedText:
    byte_length: int
    sha256: str
    lines: tuple[DecodedLine, ...]

    def canonical_text(self) -> str:
        return "".join(line.text + "\n" for line in self.lines)


@dataclass(frozen=True)
class A90P1Frame:
    begin_fields: tuple[tuple[str, str], ...]
    end_fields: tuple[tuple[str, str], ...]
    body: tuple[DecodedLine, ...]
    byte_start: int
    byte_end: int
    trust: FrameTrust = FrameTrust.STRUCTURAL_ONLY

    @property
    def begin(self) -> dict[str, str]:
        return dict(self.begin_fields)

    @property
    def end(self) -> dict[str, str]:
        return dict(self.end_fields)


@dataclass(frozen=True)
class A90P1Transition:
    begin_fields: tuple[tuple[str, str], ...]
    body: tuple[DecodedLine, ...]
    byte_start: int
    byte_end: int
    reason: TransitionReason
    trust: FrameTrust = FrameTrust.STRUCTURAL_ONLY

    @property
    def begin(self) -> dict[str, str]:
        return dict(self.begin_fields)


@dataclass(frozen=True)
class A90P1Transcript:
    decoded: DecodedText
    frames: tuple[A90P1Frame, ...]
    transitions: tuple[A90P1Transition, ...]
    outside: tuple[DecodedLine, ...]
    chunk_sizes: tuple[int, ...]


@dataclass(frozen=True)
class ObservationFact:
    name: str
    state: FactState
    evidence_sha256: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "state": self.state.value,
            "evidence_sha256": self.evidence_sha256,
            "error": self.error,
        }


def _as_bytes(value: str | bytes, *, label: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        try:
            return value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ObservationContractError(
                f"{label} is not valid UTF-8 text"
            ) from exc
    raise ObservationContractError(f"{label} must be str or bytes")


def decode_lines(
    value: str | bytes,
    *,
    label: str = "observation",
    allow_unterminated: bool = False,
) -> DecodedText:
    raw = _as_bytes(value, label=label)
    if b"\x00" in raw:
        raise ObservationContractError(f"{label} contains NUL")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ObservationContractError(f"{label} is not valid UTF-8") from exc

    lines: list[DecodedLine] = []
    start = 0
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte not in (0x0A, 0x0D):
            index += 1
            continue
        if byte == 0x0D:
            if index + 1 >= len(raw) or raw[index + 1] != 0x0A:
                raise ObservationContractError(f"{label} contains bare CR")
            content_end = index
            byte_end = index + 2
            ending = LineEnding.CRLF
        else:
            content_end = index
            byte_end = index + 1
            ending = LineEnding.LF
        lines.append(
            DecodedLine(
                text=raw[start:content_end].decode("utf-8"),
                byte_start=start,
                content_end=content_end,
                byte_end=byte_end,
                ending=ending,
            )
        )
        start = byte_end
        index = byte_end

    if start < len(raw):
        if not allow_unterminated:
            raise ObservationContractError(f"{label} is not newline terminated")
        lines.append(
            DecodedLine(
                text=raw[start:].decode("utf-8"),
                byte_start=start,
                content_end=len(raw),
                byte_end=len(raw),
                ending=LineEnding.EOF,
            )
        )
    return DecodedText(
        byte_length=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        lines=tuple(lines),
    )


def _parse_fields(
    payload: str,
    *,
    expected: tuple[str, ...],
    label: str,
) -> dict[str, str]:
    tokens = payload.split(" ")
    if not tokens or any(not token for token in tokens):
        raise ObservationContractError(f"{label} field spacing is not exact")
    fields: dict[str, str] = {}
    for token in tokens:
        if token.count("=") != 1:
            raise ObservationContractError(f"{label} contains a malformed field")
        key, value = token.split("=", 1)
        if not key or not value or key in fields:
            raise ObservationContractError(
                f"{label} fields must be unique and nonempty"
            )
        fields[key] = value
    if set(fields) != set(expected):
        raise ObservationContractError(f"{label} field set is not exact")
    if tuple(fields) != expected:
        raise ObservationContractError(f"{label} field order is not exact")
    return fields


def _validate_begin(fields: dict[str, str]) -> None:
    if (
        UNSIGNED_DECIMAL_RE.fullmatch(fields["seq"]) is None
        or int(fields["seq"]) <= 0
        or COMMAND_NAME_RE.fullmatch(fields["cmd"]) is None
        or UNSIGNED_DECIMAL_RE.fullmatch(fields["argc"]) is None
        or int(fields["argc"]) <= 0
        or FLAGS_RE.fullmatch(fields["flags"]) is None
    ):
        raise ObservationContractError("A90P1 BEGIN field value is not exact")


def _validate_end(fields: dict[str, str]) -> None:
    if (
        UNSIGNED_DECIMAL_RE.fullmatch(fields["seq"]) is None
        or int(fields["seq"]) <= 0
        or COMMAND_NAME_RE.fullmatch(fields["cmd"]) is None
        or SIGNED_DECIMAL_RE.fullmatch(fields["rc"]) is None
        or UNSIGNED_DECIMAL_RE.fullmatch(fields["errno"]) is None
        or UNSIGNED_DECIMAL_RE.fullmatch(fields["duration_ms"]) is None
        or FLAGS_RE.fullmatch(fields["flags"]) is None
        or STATUS_RE.fullmatch(fields["status"]) is None
        or fields["status"] not in CANONICAL_STATUSES
    ):
        raise ObservationContractError("A90P1 END field value is not exact")
    rc = int(fields["rc"])
    errno = int(fields["errno"])
    status = fields["status"]
    if (rc == 0) != (status == "ok"):
        raise ObservationContractError("A90P1 END rc/status coherence failed")
    if (
        (rc >= 0 and errno != 0)
        or (rc > 0 and status != "error")
        or (rc < 0 and errno != -rc)
        or (status in {"unknown", "busy"} and rc >= 0)
        or (status == "unknown" and (rc, errno) != (-2, 2))
        or (status == "busy" and (rc, errno) != (-16, 16))
    ):
        raise ObservationContractError("A90P1 END rc/errno coherence failed")


def parse_a90p1_chunks(
    chunks: Iterable[bytes],
    *,
    expected_command: str | None = None,
    require_frames: bool = True,
    one_way_commands: frozenset[str] = frozenset(),
) -> A90P1Transcript:
    materialized = tuple(chunks)
    if any(not isinstance(chunk, bytes) for chunk in materialized):
        raise ObservationContractError("A90P1 chunks must be bytes")
    if any(
        not isinstance(command, str)
        or COMMAND_NAME_RE.fullmatch(command) is None
        for command in one_way_commands
    ):
        raise ObservationContractError("A90P1 one-way command set is invalid")
    decoded = decode_lines(
        b"".join(materialized),
        label="A90P1 transcript",
        allow_unterminated=True,
    )
    frames: list[A90P1Frame] = []
    transitions: list[A90P1Transition] = []
    outside: list[DecodedLine] = []
    begin_line: DecodedLine | None = None
    begin_fields: dict[str, str] | None = None
    body: list[DecodedLine] = []
    for line in decoded.lines:
        if line.text.startswith(BEGIN_PREFIX):
            if line.ending is LineEnding.EOF:
                raise ObservationContractError(
                    "A90P1 BEGIN is not newline terminated"
                )
            next_fields = _parse_fields(
                line.text[len(BEGIN_PREFIX):],
                expected=BEGIN_KEY_ORDER,
                label="A90P1 BEGIN",
            )
            _validate_begin(next_fields)
            if begin_line is not None:
                assert begin_fields is not None
                if begin_fields["cmd"] not in one_way_commands:
                    raise ObservationContractError(
                        "A90P1 nested BEGIN is ambiguous"
                    )
                if (
                    expected_command is not None
                    and begin_fields["cmd"] != expected_command
                ):
                    raise ObservationContractError(
                        "A90P1 command does not match the issued request"
                    )
                transitions.append(
                    A90P1Transition(
                        begin_fields=tuple(begin_fields.items()),
                        body=tuple(body),
                        byte_start=begin_line.byte_start,
                        byte_end=line.byte_start,
                        reason=TransitionReason.ONE_WAY_EXEC_DISCONTINUITY,
                    )
                )
            begin_fields = next_fields
            begin_line = line
            body = []
            continue
        if line.text.startswith(END_PREFIX):
            if begin_line is None or begin_fields is None:
                raise ObservationContractError("A90P1 END lacks BEGIN")
            if line.ending is LineEnding.EOF:
                raise ObservationContractError(
                    "A90P1 END is not newline terminated"
                )
            end_fields = _parse_fields(
                line.text[len(END_PREFIX):],
                expected=END_KEY_ORDER,
                label="A90P1 END",
            )
            _validate_end(end_fields)
            for key in ("seq", "cmd", "flags"):
                if begin_fields[key] != end_fields[key]:
                    raise ObservationContractError(
                        f"A90P1 BEGIN/END {key} mismatch"
                    )
            if expected_command is not None and end_fields["cmd"] != expected_command:
                raise ObservationContractError(
                    "A90P1 command does not match the issued request"
                )
            frames.append(
                A90P1Frame(
                    begin_fields=tuple(begin_fields.items()),
                    end_fields=tuple(end_fields.items()),
                    body=tuple(body),
                    byte_start=begin_line.byte_start,
                    byte_end=line.byte_end,
                )
            )
            begin_line = None
            begin_fields = None
            body = []
            continue
        if begin_line is None:
            outside.append(line)
        else:
            body.append(line)
    if begin_line is not None:
        assert begin_fields is not None
        if begin_fields["cmd"] not in one_way_commands:
            raise ObservationContractError("A90P1 BEGIN lacks END")
        if expected_command is not None and begin_fields["cmd"] != expected_command:
            raise ObservationContractError(
                "A90P1 command does not match the issued request"
            )
        transitions.append(
            A90P1Transition(
                begin_fields=tuple(begin_fields.items()),
                body=tuple(body),
                byte_start=begin_line.byte_start,
                byte_end=decoded.byte_length,
                reason=TransitionReason.ONE_WAY_EXEC_DISCONTINUITY,
            )
        )
    if require_frames and not frames:
        raise ObservationContractError("A90P1 transcript has no complete frame")
    return A90P1Transcript(
        decoded=decoded,
        frames=tuple(frames),
        transitions=tuple(transitions),
        outside=tuple(outside),
        chunk_sizes=tuple(len(chunk) for chunk in materialized),
    )


def parse_a90p1_transcript(
    value: str | bytes,
    *,
    expected_command: str | None = None,
    require_frames: bool = True,
    one_way_commands: frozenset[str] = frozenset(),
) -> A90P1Transcript:
    return parse_a90p1_chunks(
        (_as_bytes(value, label="A90P1 transcript"),),
        expected_command=expected_command,
        require_frames=require_frames,
        one_way_commands=one_way_commands,
    )


def parse_exact_marker(value: str | bytes) -> dict[str, str]:
    decoded = decode_lines(value, label="marker")
    result: dict[str, str] = {}
    for line in decoded.lines:
        if not line.text or line.text.count("=") != 1:
            raise ObservationContractError("marker contains an invalid line")
        key, item = line.text.split("=", 1)
        if not key or not item or key in result:
            raise ObservationContractError(
                "marker keys must be unique and nonempty"
            )
        result[key] = item
    return result


def validate_native_release_evidence(
    log_text: str | bytes,
    marker_text: str | bytes,
) -> None:
    decoded = decode_lines(
        log_text,
        label="native release log",
        allow_unterminated=True,
    )
    lines = tuple(line.text for line in decoded.lines)
    if sum(NATIVE_RELEASE_SUCCESS_RE.fullmatch(line) is not None for line in lines) != 1:
        raise ObservationContractError(
            "native KMS release success line is not exact"
        )
    for required in NATIVE_RELEASE_EXACT_LINES:
        if lines.count(required) != 1:
            raise ObservationContractError(
                f"native release evidence is not exact: {required}"
            )
    if parse_exact_marker(marker_text) != NATIVE_RELEASE_MARKER:
        raise ObservationContractError("native release marker is not exact")


def _positive_int(value: str, *, label: str) -> int:
    if UNSIGNED_DECIMAL_RE.fullmatch(value) is None or int(value) <= 0:
        raise ObservationContractError(f"{label} must be a positive integer")
    return int(value)


def validate_debian_ready_marker(
    marker_text: str | bytes,
    *,
    display_uid: int = 3904,
    display_gid: int = 3904,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    expected_keys = {
        "schema",
        "pid1_exe",
        "presenter_pid",
        "presenter_uid",
        "presenter_gid",
        "presenter_cap_eff",
        "no_new_privs",
        "controlling_vt",
        "drm_node",
        "drm_node_major_minor",
        "drm_master",
        "connector_id",
        "crtc_id",
        "mode",
        "setcrtc_rc",
        "native_pid1_drm_fd_count",
        "other_native_drm_fd_count",
        "presenter_self_drm_fd_count",
        "other_process_drm_fd_count",
        "native_init_process_count",
    }
    if set(marker) != expected_keys:
        raise ObservationContractError(
            "Debian display-ready marker key set is not exact"
        )
    fixed = {
        "schema": "a90-debian-display-v1",
        "pid1_exe": "/usr/sbin/init",
        "presenter_uid": str(display_uid),
        "presenter_gid": str(display_gid),
        "presenter_cap_eff": "0000000000000000",
        "no_new_privs": "1",
        "controlling_vt": "none",
        "drm_node": "/dev/dri/card0",
        "drm_master": "1",
        "setcrtc_rc": "0",
        "native_pid1_drm_fd_count": "0",
        "other_native_drm_fd_count": "0",
        "presenter_self_drm_fd_count": "1",
        "other_process_drm_fd_count": "0",
        "native_init_process_count": "0",
    }
    for key, expected in fixed.items():
        if marker.get(key) != expected:
            raise ObservationContractError(
                f"Debian display-ready {key} is not exact"
            )
    _positive_int(marker["presenter_pid"], label="presenter_pid")
    _positive_int(marker["connector_id"], label="connector_id")
    _positive_int(marker["crtc_id"], label="crtc_id")
    if DEVNO_RE.fullmatch(marker["drm_node_major_minor"]) is None:
        raise ObservationContractError("DRM major/minor is not exact")
    if MODE_RE.fullmatch(marker["mode"]) is None:
        raise ObservationContractError("display mode is not exact")
    return marker


def validate_bounded_failure_marker(
    marker_text: str | bytes,
    *,
    max_attempts: int = 3,
    ready_absent: bool,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    if set(marker) != {"schema", "attempt", "rc"}:
        raise ObservationContractError(
            "display failure marker key set is not exact"
        )
    if (
        marker["schema"] != "a90-debian-display-v1-failure"
        or marker["attempt"] != str(max_attempts)
        or UNSIGNED_DECIMAL_RE.fullmatch(marker["rc"]) is None
        or int(marker["rc"]) == 0
        or ready_absent is not True
    ):
        raise ObservationContractError(
            "bounded display failure evidence is not terminal"
        )
    return marker


def _fact(
    name: str,
    state: FactState,
    *,
    evidence: str | bytes | None = None,
    error: str | None = None,
) -> ObservationFact:
    digest = None
    if evidence is not None:
        digest = hashlib.sha256(_as_bytes(evidence, label=name)).hexdigest()
    return ObservationFact(
        name=name,
        state=state,
        evidence_sha256=digest,
        error=error,
    )


def classify_phase2_display_facts(
    *,
    handoff_log: str | bytes,
    native_release_marker: str | bytes,
    pid1_comm_init: bool | None,
    proc1_exe_init: bool | None,
    dropbear_started: bool | None,
    display_status: str,
) -> dict[str, ObservationFact]:
    facts: dict[str, ObservationFact] = {}
    try:
        validate_native_release_evidence(handoff_log, native_release_marker)
    except ObservationContractError as exc:
        facts["native_release"] = _fact(
            "native_release",
            FactState.UNKNOWN,
            evidence=handoff_log,
            error=str(exc),
        )
    else:
        facts["native_release"] = _fact(
            "native_release",
            FactState.PROVEN,
            evidence=handoff_log,
        )
    if pid1_comm_init is True and proc1_exe_init is True:
        pid1_state = FactState.PROVEN
    elif pid1_comm_init is False or proc1_exe_init is False:
        pid1_state = FactState.REFUTED
    else:
        pid1_state = FactState.UNKNOWN
    facts["debian_pid1"] = _fact("debian_pid1", pid1_state)
    if dropbear_started is True:
        dropbear_state = FactState.PROVEN
    elif dropbear_started is False:
        dropbear_state = FactState.REFUTED
    else:
        dropbear_state = FactState.UNKNOWN
    facts["dropbear"] = _fact(
        "dropbear",
        dropbear_state,
    )
    if display_status == "ready":
        display_state = FactState.PROVEN
    elif display_status == "bounded-failure":
        display_state = FactState.REFUTED
    else:
        display_state = FactState.UNKNOWN
    facts["display_acquisition"] = _fact(
        "display_acquisition",
        display_state,
    )
    return facts


def facts_to_dict(
    facts: dict[str, ObservationFact],
) -> dict[str, dict[str, str | None]]:
    return {name: fact.to_dict() for name, fact in sorted(facts.items())}
