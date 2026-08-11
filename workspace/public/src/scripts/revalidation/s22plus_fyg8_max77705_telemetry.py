#!/usr/bin/env python3
"""Max77705 diagnostic telemetry over the fixed P3.10 Carrier-v2 record.

The fixed Image retains one 192-byte record with two 64-byte request payloads.
This module therefore defines one fixed 128-byte envelope.  Read-to-clear poll
bytes are PackBits-compressed losslessly.  A result that cannot fit is retained
as an explicit no-proof overflow bucket with a digest and bounded per-command
poll summary; it is never decoded as a MUX result.
"""

from __future__ import annotations

import binascii
from dataclasses import dataclass
import hashlib
import struct
from typing import Any, Iterable

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p308_telemetry_spec as fixed_spec


SCHEMA = "s22plus_fyg8_max77705_telemetry_v2"
TARGET = surface.TARGET

ENVELOPE_MAGIC = b"MXD2"
ENVELOPE_VERSION = 2
ENVELOPE_SIZE = 128
SLOT_PAYLOAD_SIZE = 64
PAYLOAD_AREA_OFFSET = 48
PAYLOAD_AREA_SIZE = 76
CRC_OFFSET = 124
POLL_ENCODING_PACKBITS = 1
POLL_ENCODING_SHA256_SUMMARY = 2
POLL_SUMMARY_DIGEST_SIZE = 32
POLL_SUMMARY_VECTOR_SIZE = 4
POLL_SUMMARY_SIZE = 44

UIC_AP_COMMAND_RESPONSE = 0x80
UIC_DETECTION_LATCH_MASK = 0x7B
UIC_BC12_REDETECTION_LATCH_MASK = 0x0A
COM_USB = 0x09
STAGE_PRE = 5
STAGE_WRITE = 6
STAGE_POST1 = 7
STAGE_RETENTION = 8
STAGE_POST2 = 9
STAGE_COMPLETE = 10
RC_ETIMEDOUT = -110
TIMEOUT_SLOT_BY_STAGE = {
    STAGE_PRE: 0,
    STAGE_WRITE: 1,
    STAGE_POST1: 2,
    STAGE_POST2: 3,
}

FLAG_RESULT_PRESENT = 1 << 0
FLAG_POLL_OVERFLOW = 1 << 1
FLAG_BINDING_PRESENT = 1 << 2
FLAG_POLL_LOSSLESS = 1 << 3
FLAG_MASK = (
    FLAG_RESULT_PRESENT
    | FLAG_POLL_OVERFLOW
    | FLAG_BINDING_PRESENT
    | FLAG_POLL_LOSSLESS
)

A_DETAIL = 0xDA3
B_DETAIL_BASE = 0x6701
TERMINAL_BUCKET_KEYS = tuple(surface.DIAG_RUNTIME_TERMINAL_BUCKETS)
TERMINAL_CODE_BY_KEY = {
    key: index + 1 for index, key in enumerate(TERMINAL_BUCKET_KEYS)
}
TERMINAL_KEY_BY_CODE = {
    value: key for key, value in TERMINAL_CODE_BY_KEY.items()
}

MUX_DEVICE_CLASSES = (
    "pre-nonusb-post-stable-usb",
    "pre-usb-post-stable-usb",
    "post-visible-reversion",
    "complete-other-tuple",
    "diagnostic-transaction-failure",
)
MUX_CODE_BY_NAME = {
    name: index + 1 for index, name in enumerate(MUX_DEVICE_CLASSES)
}
MUX_NAME_BY_CODE = {value: key for key, value in MUX_CODE_BY_NAME.items()}

TERMINAL_DETAIL_BY_KEY = {
    key: B_DETAIL_BASE + index for index, key in enumerate(TERMINAL_BUCKET_KEYS)
}
MUX_DETAIL_BY_NAME = {
    name: B_DETAIL_BASE + 0x0F + index
    for index, name in enumerate(MUX_DEVICE_CLASSES)
}

LOADER_STATES = {
    "NOT_STARTED": 0,
    "FINIT_MODULE_IN_PROGRESS": 1,
    "FINIT_MODULE_RETURNED_SUCCESS": 2,
    "FINIT_MODULE_FAILED": 3,
}
LOADER_STATE_NAMES = {value: key for key, value in LOADER_STATES.items()}
DRIVER_STATES = {
    "ABSENT": 0,
    "UNBOUND": 1,
    "OTHER_DRIVER": 2,
    "DIAGNOSTIC": 3,
}
DRIVER_STATE_NAMES = {value: key for key, value in DRIVER_STATES.items()}

OBSERVER_SITES = {
    "none": 0,
    "override-prepare": 1,
    "substrate-verify": 2,
    "pre-topology": 3,
    "late-loader": 4,
    "post-topology": 5,
    "result-policy": 6,
    "result-read": 7,
}
OBSERVER_SITE_NAMES = {value: key for key, value in OBSERVER_SITES.items()}
OBSERVER_ERROR_CLASSES = {
    "none": 0,
    "not-found": 1,
    "busy": 2,
    "timeout-retry": 3,
    "io-format": 4,
    "interrupted": 5,
    "other-negative": 6,
    "nonnegative": 7,
}
OBSERVER_ERROR_CLASS_NAMES = {
    value: key for key, value in OBSERVER_ERROR_CLASSES.items()
}

CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-DIAG-V2\0"


class TelemetryError(ValueError):
    pass


@dataclass(frozen=True)
class BindingWitness:
    loader_state: int
    pre_exact_parent_present: int
    pre_exact_parent_driver_state: int
    pre_matching_unbound_parent_count: int
    pre_wrong_address_compatible_parent_count: int
    post_exact_parent_driver_state: int
    post_diagnostic_bound_parent_count: int
    post_exact_adapter_muic_0x25_client_count: int
    post_foreign_0x25_client_count: int

    def values(self) -> tuple[int, ...]:
        return (
            self.loader_state,
            self.pre_exact_parent_present,
            self.pre_exact_parent_driver_state,
            self.pre_matching_unbound_parent_count,
            self.pre_wrong_address_compatible_parent_count,
            self.post_exact_parent_driver_state,
            self.post_diagnostic_bound_parent_count,
            self.post_exact_adapter_muic_0x25_client_count,
            self.post_foreign_0x25_client_count,
        )


@dataclass(frozen=True)
class DiagnosticResult:
    stage: int
    rc: int
    pmic_valid_mask: int
    pmic_id: int
    pmic_rev: int
    initial_uic_valid: int
    initial_uic: int
    command_issued_mask: int
    response_seen_mask: int
    response_opcode: tuple[int, int, int, int]
    response_value: tuple[int, int, int, int]
    poll_bytes: tuple[bytes, bytes, bytes, bytes]
    write_attempted: int
    write_ambiguous: int


@dataclass(frozen=True)
class PollSummary:
    sha256: bytes
    or_mask: tuple[int, int, int, int]
    poll0: tuple[int, int, int, int]
    nonzero_count: tuple[int, int, int, int]

    def payload(self) -> bytes:
        return self.sha256 + bytes(self.or_mask + self.poll0 + self.nonzero_count)


def _u8(value: int, label: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise TelemetryError(f"{label} is outside one byte")
    return value


def _s32(value: int, label: str) -> int:
    if not isinstance(value, int) or not -(1 << 31) <= value < (1 << 31):
        raise TelemetryError(f"{label} is outside signed 32 bits")
    return value


def _validate_binding(binding: BindingWitness) -> None:
    values = binding.values()
    if len(values) != len(surface.DIAG_EAGAIN_BINDING_WITNESS_FIELDS):
        raise TelemetryError("binding witness extent differs")
    for index, value in enumerate(values):
        _u8(value, f"binding witness {index}")
    if binding.loader_state not in LOADER_STATE_NAMES:
        raise TelemetryError("loader state is not declared")
    if binding.pre_exact_parent_present not in {0, 1}:
        raise TelemetryError("pre parent presence is not binary")
    if binding.pre_exact_parent_driver_state not in DRIVER_STATE_NAMES:
        raise TelemetryError("pre driver state is not declared")
    if binding.post_exact_parent_driver_state not in DRIVER_STATE_NAMES:
        raise TelemetryError("post driver state is not declared")


def _binding_causal_ready(binding: BindingWitness) -> bool:
    _validate_binding(binding)
    return (
        binding.loader_state == LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]
        and binding.pre_exact_parent_present == 1
        and binding.pre_exact_parent_driver_state == DRIVER_STATES["UNBOUND"]
        and binding.pre_matching_unbound_parent_count == 1
        and binding.pre_wrong_address_compatible_parent_count == 0
        and binding.post_exact_parent_driver_state == DRIVER_STATES["DIAGNOSTIC"]
        and binding.post_diagnostic_bound_parent_count == 1
        and binding.post_exact_adapter_muic_0x25_client_count == 1
        and binding.post_foreign_0x25_client_count == 0
    )


def classify_eagain_binding(binding: BindingWitness) -> str:
    """Classify one EAGAIN witness by the contract's fail-closed priority."""

    _validate_binding(binding)
    if binding.loader_state == LOADER_STATES["FINIT_MODULE_IN_PROGRESS"]:
        return "probe_in_progress"
    if binding.loader_state != LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]:
        raise TelemetryError("EAGAIN loader state is not classifiable")
    if (
        binding.pre_exact_parent_driver_state == DRIVER_STATES["OTHER_DRIVER"]
        and binding.post_exact_parent_driver_state == DRIVER_STATES["OTHER_DRIVER"]
    ):
        return "exact_parent_owned_by_other_driver"
    if (
        binding.post_exact_parent_driver_state == DRIVER_STATES["DIAGNOSTIC"]
        and binding.post_diagnostic_bound_parent_count == 1
        and binding.post_exact_adapter_muic_0x25_client_count == 1
        and binding.post_foreign_0x25_client_count == 0
    ):
        return "diagnostic_binding_ready_but_result_eagain"
    if (
        binding.pre_exact_parent_present == 1
        and binding.post_exact_parent_driver_state == DRIVER_STATES["UNBOUND"]
    ):
        return "exact_parent_unbound_after_sync_return"
    if (
        binding.pre_exact_parent_present == 0
        and binding.pre_wrong_address_compatible_parent_count >= 1
    ):
        return "wrong_address_compatible_parent"
    if (
        binding.pre_exact_parent_present == 0
        and binding.pre_matching_unbound_parent_count == 0
        and binding.pre_wrong_address_compatible_parent_count == 0
        and binding.post_diagnostic_bound_parent_count == 0
        and binding.post_exact_adapter_muic_0x25_client_count == 0
    ):
        return "no_matching_parent"
    raise TelemetryError("EAGAIN binding witnesses do not match a declared row")


def eagain_terminal_bucket(row_name: str) -> str:
    try:
        row = surface.DIAG_EAGAIN_OBSERVABLE_ROWS[row_name]
    except KeyError as exc:
        raise TelemetryError("EAGAIN row is not declared") from exc
    bucket = row.get("terminal_bucket_key")
    if bucket is None:
        if row_name != "probe_in_progress":
            raise TelemetryError("EAGAIN continuation row lacks a terminal policy")
        return "result_not_ready_eagain"
    return str(bucket)


def summarize_poll_vectors(
    poll_vectors: tuple[bytes, bytes, bytes, bytes],
) -> PollSummary:
    if len(poll_vectors) != POLL_SUMMARY_VECTOR_SIZE:
        raise TelemetryError("poll-vector extent differs")
    if any(not isinstance(value, bytes) or len(value) > 100 for value in poll_vectors):
        raise TelemetryError("poll vector is outside the source bound")
    raw = b"".join(poll_vectors)
    return PollSummary(
        sha256=hashlib.sha256(raw).digest(),
        or_mask=tuple(_poll_or(values) for values in poll_vectors),
        poll0=tuple(values[0] if values else 0 for values in poll_vectors),
        nonzero_count=tuple(
            sum(value != 0 for value in values) for values in poll_vectors
        ),
    )


def _poll_or(values: bytes) -> int:
    result = 0
    for value in values:
        result |= value
    return result


def _validate_poll_summary(
    summary: PollSummary,
    *,
    counts: tuple[int, int, int, int],
    command_issued_mask: int,
    response_seen_mask: int,
    stage: int,
    rc: int,
) -> None:
    if (
        len(summary.sha256) != POLL_SUMMARY_DIGEST_SIZE
        or len(summary.or_mask) != POLL_SUMMARY_VECTOR_SIZE
        or len(summary.poll0) != POLL_SUMMARY_VECTOR_SIZE
        or len(summary.nonzero_count) != POLL_SUMMARY_VECTOR_SIZE
    ):
        raise TelemetryError("poll summary extent differs")
    if command_issued_mask & ~0x0F or response_seen_mask & ~0x0F:
        raise TelemetryError("command or response mask exceeds four slots")
    if response_seen_mask & ~command_issued_mask:
        raise TelemetryError("response mask is not a subset of issued commands")
    for slot, (count, or_mask, poll0, nonzero_count) in enumerate(
        zip(
            counts,
            summary.or_mask,
            summary.poll0,
            summary.nonzero_count,
            strict=True,
        )
    ):
        _u8(count, f"poll count {slot}")
        _u8(or_mask, f"poll OR {slot}")
        _u8(poll0, f"poll0 {slot}")
        _u8(nonzero_count, f"poll nonzero count {slot}")
        if count > 100:
            raise TelemetryError("poll count exceeds the source bound")
        if nonzero_count > count:
            raise TelemetryError("poll nonzero count exceeds poll count")
        if (or_mask == 0) != (nonzero_count == 0):
            raise TelemetryError("poll OR and nonzero count disagree")
        if count == 0 and (or_mask or poll0 or nonzero_count):
            raise TelemetryError("empty poll slot carries a nonempty summary")
        if poll0 & ~or_mask:
            raise TelemetryError("poll0 contains a bit absent from the poll OR")
        if count and not command_issued_mask & (1 << slot):
            raise TelemetryError("poll bytes exist without an issued command")
        if response_seen_mask & (1 << slot) and not (
            or_mask & UIC_AP_COMMAND_RESPONSE
        ):
            raise TelemetryError("response witness lacks APCmdResI in its slot")
    if rc == RC_ETIMEDOUT:
        active_slot = TIMEOUT_SLOT_BY_STAGE.get(stage)
        if active_slot is None:
            raise TelemetryError("timeout result has no command-stage slot")
        if summary.or_mask[active_slot] & UIC_AP_COMMAND_RESPONSE:
            raise TelemetryError("timed-out slot contains APCmdResI")


def _validate_result_fixed(result: DiagnosticResult) -> None:
    _u8(result.stage, "diagnostic stage")
    _s32(result.rc, "diagnostic rc")
    if not 2 <= result.stage <= STAGE_COMPLETE:
        raise TelemetryError("published diagnostic stage is not source-reachable")
    if (result.rc == 0) != (result.stage == STAGE_COMPLETE):
        raise TelemetryError("diagnostic success and complete stage disagree")
    for label, value in (
        ("pmic valid mask", result.pmic_valid_mask),
        ("pmic id", result.pmic_id),
        ("pmic revision", result.pmic_rev),
        ("initial UIC validity", result.initial_uic_valid),
        ("initial UIC", result.initial_uic),
        ("command-issued mask", result.command_issued_mask),
        ("response-seen mask", result.response_seen_mask),
        ("write attempted", result.write_attempted),
        ("write ambiguous", result.write_ambiguous),
    ):
        _u8(value, label)
    if result.initial_uic_valid not in {0, 1}:
        raise TelemetryError("initial UIC validity is not binary")
    if result.pmic_valid_mask > 3:
        raise TelemetryError("PMIC validity mask exceeds its two source bits")
    if result.write_attempted not in {0, 1} or result.write_ambiguous not in {0, 1}:
        raise TelemetryError("write flags are not binary")
    reachable_masks = {0x00, 0x01, 0x03, 0x05, 0x07, 0x0D, 0x0F}
    if (
        result.command_issued_mask not in reachable_masks
        or result.response_seen_mask not in reachable_masks
    ):
        raise TelemetryError("command or response mask is not source-reachable")
    if result.write_attempted != bool(result.command_issued_mask & 0x02):
        raise TelemetryError("write-attempt flag and command mask disagree")
    if result.write_ambiguous and not result.write_attempted:
        raise TelemetryError("ambiguous-write flag lacks a write attempt")
    for label, values in (
        ("response opcode", result.response_opcode),
        ("response value", result.response_value),
    ):
        if len(values) != 4:
            raise TelemetryError(f"{label} extent differs")
        for value in values:
            _u8(value, label)
    issued = result.command_issued_mask
    seen = result.response_seen_mask
    if result.stage in {2, 3, 4}:
        if issued or seen or result.write_attempted:
            raise TelemetryError("pre-command stage carries command state")
    elif result.stage == STAGE_PRE:
        if issued != 0x01 or seen not in {0x00, 0x01} or result.write_attempted:
            raise TelemetryError("pre-read failure shape is not source-reachable")
    elif result.stage == STAGE_WRITE:
        if (
            issued != 0x03
            or seen not in {0x01, 0x03}
            or result.response_opcode[0] != 0x05
            or result.response_value[0] == COM_USB
            or result.write_attempted != 1
            or result.write_ambiguous != 1
        ):
            raise TelemetryError("write failure shape is not source-reachable")
    elif result.stage == STAGE_POST1:
        write_path = result.response_value[0] != COM_USB
        expected_issued = 0x07 if write_path else 0x05
        prefix_seen = 0x03 if write_path else 0x01
        if (
            issued != expected_issued
            or seen not in {prefix_seen, expected_issued}
            or result.response_opcode[0] != 0x05
            or result.write_attempted != int(write_path)
            or result.response_value[1] != 0
            or (not write_path and result.response_opcode[1] != 0)
            or (write_path and (
                result.write_ambiguous != 0 or result.response_opcode[1] != 0x06
            ))
        ):
            raise TelemetryError("post1 failure shape is not source-reachable")
    elif result.stage == STAGE_RETENTION:
        raise TelemetryError("retention sleep cannot publish a terminal result")
    elif result.stage == STAGE_POST2:
        write_path = result.response_value[0] != COM_USB
        expected_issued = 0x0F if write_path else 0x0D
        prefix_seen = 0x07 if write_path else 0x05
        if (
            issued != expected_issued
            or seen not in {prefix_seen, expected_issued}
            or result.response_opcode[0] != 0x05
            or result.response_opcode[2] != 0x05
            or result.write_attempted != int(write_path)
            or result.response_value[1] != 0
            or (not write_path and result.response_opcode[1] != 0)
            or (write_path and (
                result.write_ambiguous != 0 or result.response_opcode[1] != 0x06
            ))
        ):
            raise TelemetryError("post2 failure shape is not source-reachable")
    if result.stage == STAGE_COMPLETE:
        if (
            result.command_issued_mask not in {0x0D, 0x0F}
            or result.response_seen_mask != result.command_issued_mask
            or result.response_opcode[0] != 0x05
            or result.response_opcode[2] != 0x05
            or result.response_opcode[3] != 0x05
            or (
                result.command_issued_mask & 0x02
                and result.response_opcode[1] != 0x06
            )
            or result.response_value[1] != 0
            or (result.response_value[0] == COM_USB) != (not result.write_attempted)
            or result.write_ambiguous != 0
        ):
            raise TelemetryError("complete diagnostic tuple is not source-reachable")


def _validate_result(result: DiagnosticResult) -> bytes:
    _validate_result_fixed(result)
    if len(result.poll_bytes) != POLL_SUMMARY_VECTOR_SIZE:
        raise TelemetryError("poll-vector extent differs")
    for value in result.poll_bytes:
        if not isinstance(value, bytes) or len(value) > 100:
            raise TelemetryError("poll vector is outside the source bound")
    summary = summarize_poll_vectors(result.poll_bytes)
    _validate_poll_summary(
        summary,
        counts=tuple(len(value) for value in result.poll_bytes),
        command_issued_mask=result.command_issued_mask,
        response_seen_mask=result.response_seen_mask,
        stage=result.stage,
        rc=result.rc,
    )
    return b"".join(result.poll_bytes)


def classify_diagnostic_result(
    binding: BindingWitness, result: DiagnosticResult
) -> tuple[str | None, str | None]:
    """Map one source-reachable cached result to its retained semantic."""

    _validate_binding(binding)
    _validate_result_fixed(result)
    if result.rc > 0:
        return "synchronous_probe_or_publication_contradiction", None
    if result.rc < 0:
        if result.stage == 2 and result.rc == -19:
            return "matching_parent_identity_rejected", None
        if result.stage <= 4:
            return "probe_terminal_failure", None
        if result.stage not in {STAGE_PRE, STAGE_WRITE, STAGE_POST1, STAGE_POST2}:
            raise TelemetryError("negative diagnostic stage is not classifiable")
        if not _binding_causal_ready(binding):
            return "synchronous_probe_or_publication_contradiction", None
        return None, "diagnostic-transaction-failure"
    if result.stage != STAGE_COMPLETE:
        raise TelemetryError("zero diagnostic result is not complete")
    if not _binding_causal_ready(binding):
        return "synchronous_probe_or_publication_contradiction", None
    pre, post1, post2 = (
        result.response_value[0],
        result.response_value[2],
        result.response_value[3],
    )
    if post1 == COM_USB and post2 != COM_USB:
        return None, "post-visible-reversion"
    if pre != COM_USB and post1 == COM_USB and post2 == COM_USB:
        return None, "pre-nonusb-post-stable-usb"
    if pre == COM_USB and post1 == COM_USB and post2 == COM_USB:
        return None, "pre-usb-post-stable-usb"
    return None, "complete-other-tuple"


def _post2_retention_interpretation(result: dict[str, Any]) -> dict[str, Any] | None:
    """Correlate the terminal CONTROL1 value with the retention poll0 latch.

    The first post2 UIC read contains the latch accumulated since post1's last
    UIC read plus events up to that post2 poll.  It is an event-presence
    witness, not proof that the physical switch moved or that a particular
    event caused the terminal CONTROL1 value.
    """

    if (
        result["stage"] != STAGE_COMPLETE
        or result["rc"] != 0
        or result["response_seen_mask"] & 0x0C != 0x0C
        or result["response_opcode"][2] != 0x05
        or result["response_opcode"][3] != 0x05
        or result["response_value"][2] != COM_USB
    ):
        return None
    post2 = result["response_value"][3]
    post2_poll0 = result["poll0"][3]
    detection = post2_poll0 & UIC_DETECTION_LATCH_MASK
    bc12_redetection = post2_poll0 & UIC_BC12_REDETECTION_LATCH_MASK
    if post2 == COM_USB:
        classification = (
            "POST1_USB_POST2_USB_WITH_RETENTION_DETECTION_LATCH"
            if detection
            else "POST1_USB_POST2_USB_WITHOUT_RETENTION_DETECTION_LATCH"
        )
    else:
        classification = (
            "POST1_USB_POST2_NONUSB_WITH_RETENTION_DETECTION_LATCH"
            if detection
            else "POST1_USB_POST2_NONUSB_WITHOUT_RETENTION_DETECTION_LATCH"
        )
    return {
        "classification": classification,
        "post2_control1": post2,
        "post2_poll0": post2_poll0,
        "detection_latch_mask": detection,
        "bc12_redetection_latch_mask": bc12_redetection,
        "event_presence_only": True,
        "physical_switch_movement_proven": False,
        "causal_trigger_proven": False,
    }


def format_module_result(result: DiagnosticResult) -> bytes:
    """Emit the exact canonical string produced by the diagnostic getter."""

    _validate_result(result)
    polls = tuple(value.hex() for value in result.poll_bytes)
    return (
        f"v=1 stage={result.stage} rc={result.rc} "
        f"pmic_v={result.pmic_valid_mask:02x} pmic_id={result.pmic_id:02x} "
        f"pmic_rev={result.pmic_rev:02x} uic0_v={result.initial_uic_valid} "
        f"uic0={result.initial_uic:02x} issued={result.command_issued_mask:02x} "
        f"seen={result.response_seen_mask:02x} "
        f"wr_attempt={result.write_attempted} wr_amb={result.write_ambiguous} "
        f"rsp={''.join(f'{value:02x}' for value in result.response_opcode)} "
        f"val={''.join(f'{value:02x}' for value in result.response_value)} "
        f"p0n={len(result.poll_bytes[0])} p0={polls[0]} "
        f"p1n={len(result.poll_bytes[1])} p1={polls[1]} "
        f"p2n={len(result.poll_bytes[2])} p2={polls[2]} "
        f"p3n={len(result.poll_bytes[3])} p3={polls[3]}\n"
    ).encode("ascii")


def packbits_encode(data: bytes) -> bytes:
    """Encode canonical PackBits blocks with repeats selected at length >= 3."""

    output = bytearray()
    cursor = 0
    while cursor < len(data):
        run = 1
        while (
            cursor + run < len(data)
            and data[cursor + run] == data[cursor]
            and run < 128
        ):
            run += 1
        if run >= 3:
            output.extend((0x80 | (run - 1), data[cursor]))
            cursor += run
            continue
        start = cursor
        cursor += run
        while cursor < len(data) and cursor - start < 128:
            next_run = 1
            while (
                cursor + next_run < len(data)
                and data[cursor + next_run] == data[cursor]
                and next_run < 128
            ):
                next_run += 1
            if next_run >= 3:
                break
            if cursor - start + next_run > 128:
                break
            cursor += next_run
        literal = data[start:cursor]
        output.append(len(literal) - 1)
        output.extend(literal)
    return bytes(output)


def packbits_decode(data: bytes, *, expected_size: int) -> bytes:
    output = bytearray()
    cursor = 0
    while cursor < len(data):
        control = data[cursor]
        cursor += 1
        length = (control & 0x7F) + 1
        if control & 0x80:
            if cursor >= len(data):
                raise TelemetryError("PackBits repeat block is truncated")
            output.extend(bytes([data[cursor]]) * length)
            cursor += 1
        else:
            if cursor + length > len(data):
                raise TelemetryError("PackBits literal block is truncated")
            output.extend(data[cursor : cursor + length])
            cursor += length
        if len(output) > expected_size:
            raise TelemetryError("PackBits output exceeds its declared size")
    if len(output) != expected_size:
        raise TelemetryError("PackBits output size differs")
    return bytes(output)


def terminal_detail(*, terminal_bucket: str | None, mux_class: str | None) -> int:
    if (terminal_bucket is None) == (mux_class is None):
        raise TelemetryError("exactly one terminal semantic is required")
    if terminal_bucket is not None:
        try:
            return TERMINAL_DETAIL_BY_KEY[terminal_bucket]
        except KeyError as exc:
            raise TelemetryError("terminal bucket is not declared") from exc
    try:
        return MUX_DETAIL_BY_NAME[str(mux_class)]
    except KeyError as exc:
        raise TelemetryError("MUX device class is not declared") from exc


def encode_envelope(
    *,
    binding: BindingWitness,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: DiagnosticResult | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> bytes:
    _validate_binding(binding)
    detail = terminal_detail(terminal_bucket=terminal_bucket, mux_class=mux_class)
    del detail  # The detail is redundantly checked when the carrier is assembled.
    terminal_code = 0 if terminal_bucket is None else TERMINAL_CODE_BY_KEY[terminal_bucket]
    mux_code = 0 if mux_class is None else MUX_CODE_BY_NAME[mux_class]
    if (observer_site is None) != (observer_error_class is None):
        raise TelemetryError("observer site/error tag is incomplete")
    site_code = OBSERVER_SITES["none"]
    error_code = OBSERVER_ERROR_CLASSES["none"]
    if observer_site is not None:
        try:
            site_code = OBSERVER_SITES[observer_site]
            error_code = OBSERVER_ERROR_CLASSES[str(observer_error_class)]
        except KeyError as exc:
            raise TelemetryError("observer site/error tag is undeclared") from exc
        if (
            site_code == 0
            or error_code == 0
            or terminal_bucket
            != "synchronous_probe_or_publication_contradiction"
            or result is not None
        ):
            raise TelemetryError("observer site/error tag lacks contradiction semantics")
    flags = FLAG_BINDING_PRESENT
    raw_poll = b""
    poll_summary: PollSummary | None = None
    if result is not None:
        raw_poll = _validate_result(result)
        poll_summary = summarize_poll_vectors(result.poll_bytes)
        flags |= FLAG_RESULT_PRESENT
    elif mux_class is not None:
        raise TelemetryError("MUX classification requires a diagnostic result")
    if mux_class is not None and not _binding_causal_ready(binding):
        raise TelemetryError("MUX classification lacks exact causal binding")
    if result is not None:
        expected_terminal, expected_mux = classify_diagnostic_result(
            binding, result
        )
        if (terminal_bucket, mux_class) != (expected_terminal, expected_mux):
            raise TelemetryError("diagnostic result and retained semantic disagree")

    encoded_poll = packbits_encode(raw_poll)
    encoding = POLL_ENCODING_PACKBITS
    payload = encoded_poll
    if len(encoded_poll) > PAYLOAD_AREA_SIZE:
        terminal_bucket = "result_payload_unrepresentable"
        terminal_code = TERMINAL_CODE_BY_KEY[terminal_bucket]
        mux_code = 0
        flags |= FLAG_POLL_OVERFLOW
        flags &= ~FLAG_POLL_LOSSLESS
        if poll_summary is None:
            raise TelemetryError("overflow result lacks its poll summary")
        encoding = POLL_ENCODING_SHA256_SUMMARY
        payload = poll_summary.payload()
    else:
        flags |= FLAG_POLL_LOSSLESS

    envelope = bytearray(ENVELOPE_SIZE)
    envelope[0:4] = ENVELOPE_MAGIC
    envelope[4] = ENVELOPE_VERSION
    envelope[5] = terminal_code
    envelope[6] = mux_code
    envelope[7] = flags
    if result is not None:
        envelope[8] = result.stage
        struct.pack_into("<i", envelope, 9, result.rc)
        envelope[13:22] = bytes(
            (
                result.pmic_valid_mask,
                result.pmic_id,
                result.pmic_rev,
                result.initial_uic_valid,
                result.initial_uic,
                result.command_issued_mask,
                result.response_seen_mask,
                result.write_attempted,
                result.write_ambiguous,
            )
        )
        envelope[22:26] = bytes(result.response_opcode)
        envelope[26:30] = bytes(result.response_value)
        envelope[30:34] = bytes(len(value) for value in result.poll_bytes)
    envelope[34:43] = bytes(binding.values())
    envelope[43] = encoding
    struct.pack_into("<H", envelope, 44, len(raw_poll))
    envelope[46] = len(payload)
    envelope[47] = (site_code << 4) | error_code
    envelope[PAYLOAD_AREA_OFFSET : PAYLOAD_AREA_OFFSET + len(payload)] = payload
    crc = binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF
    struct.pack_into("<I", envelope, CRC_OFFSET, crc)
    return bytes(envelope)


def decode_envelope(envelope: bytes) -> dict[str, Any]:
    if len(envelope) != ENVELOPE_SIZE or envelope[:4] != ENVELOPE_MAGIC:
        raise TelemetryError("Max77705 envelope identity differs")
    if envelope[4] != ENVELOPE_VERSION:
        raise TelemetryError("Max77705 envelope version differs")
    recorded = struct.unpack_from("<I", envelope, CRC_OFFSET)[0]
    expected = binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF
    if recorded != expected:
        raise TelemetryError("Max77705 envelope CRC differs")
    terminal_code, mux_code, flags = envelope[5], envelope[6], envelope[7]
    if flags & ~FLAG_MASK or not flags & FLAG_BINDING_PRESENT:
        raise TelemetryError("Max77705 envelope flags differ")
    if (terminal_code == 0) == (mux_code == 0):
        raise TelemetryError("Max77705 envelope terminal semantics are ambiguous")
    terminal_bucket = TERMINAL_KEY_BY_CODE.get(terminal_code)
    mux_class = MUX_NAME_BY_CODE.get(mux_code)
    if terminal_code and terminal_bucket is None:
        raise TelemetryError("Max77705 terminal code is not declared")
    if mux_code and mux_class is None:
        raise TelemetryError("Max77705 MUX code is not declared")
    observer_tag = envelope[47]
    observer_site_code = observer_tag >> 4
    observer_error_code = observer_tag & 0x0F
    observer_site = OBSERVER_SITE_NAMES.get(observer_site_code)
    observer_error_class = OBSERVER_ERROR_CLASS_NAMES.get(observer_error_code)
    if (
        observer_site is None
        or observer_error_class is None
        or ((observer_site_code == 0) != (observer_error_code == 0))
    ):
        raise TelemetryError("Max77705 observer tag differs")
    if any(envelope[48 + envelope[46] : CRC_OFFSET]):
        raise TelemetryError("Max77705 envelope reserved bytes differ")

    result_present = bool(flags & FLAG_RESULT_PRESENT)
    if not result_present and any(envelope[8:34]):
        raise TelemetryError("result-absent envelope carries diagnostic bytes")
    if observer_site_code != 0 and (
        result_present
        or terminal_bucket != "synchronous_probe_or_publication_contradiction"
    ):
        raise TelemetryError("Max77705 observer tag lacks contradiction semantics")

    binding_values = tuple(envelope[34:43])
    binding = BindingWitness(*binding_values)
    _validate_binding(binding)
    raw_size = struct.unpack_from("<H", envelope, 44)[0]
    counts = tuple(envelope[30:34])
    if sum(counts) != raw_size:
        raise TelemetryError("Max77705 poll counts differ from raw extent")
    encoded_size = envelope[46]
    if encoded_size > PAYLOAD_AREA_SIZE:
        raise TelemetryError("Max77705 payload length differs")
    encoded = envelope[PAYLOAD_AREA_OFFSET : PAYLOAD_AREA_OFFSET + encoded_size]
    encoding = envelope[43]
    poll_vectors: tuple[bytes, bytes, bytes, bytes] | None = None
    poll_summary: PollSummary | None = None
    causal_result_allowed = False
    if flags & FLAG_POLL_OVERFLOW:
        if (
            terminal_bucket != "result_payload_unrepresentable"
            or mux_code != 0
            or not result_present
            or flags & FLAG_POLL_LOSSLESS
            or encoding != POLL_ENCODING_SHA256_SUMMARY
            or encoded_size != POLL_SUMMARY_SIZE
        ):
            raise TelemetryError("Max77705 overflow envelope is not fail-closed")
        poll_summary = PollSummary(
            sha256=encoded[:POLL_SUMMARY_DIGEST_SIZE],
            or_mask=tuple(encoded[32:36]),
            poll0=tuple(encoded[36:40]),
            nonzero_count=tuple(encoded[40:44]),
        )
    else:
        if not flags & FLAG_POLL_LOSSLESS or encoding != POLL_ENCODING_PACKBITS:
            raise TelemetryError("Max77705 causal envelope is not lossless")
        raw = packbits_decode(encoded, expected_size=raw_size)
        parts: list[bytes] = []
        cursor = 0
        for count in counts:
            parts.append(raw[cursor : cursor + count])
            cursor += count
        poll_vectors = tuple(parts)  # type: ignore[assignment]
        poll_summary = summarize_poll_vectors(poll_vectors)
        causal_result_allowed = mux_class is not None

    if mux_class is not None and not result_present:
        raise TelemetryError("Max77705 MUX row lacks a diagnostic result")
    if mux_class is not None and not _binding_causal_ready(binding):
        raise TelemetryError("Max77705 MUX row lacks exact causal binding")
    result: dict[str, Any] | None = None
    if result_present:
        if poll_summary is None:
            raise TelemetryError("diagnostic result lacks its poll summary")
        fixed_result = DiagnosticResult(
            stage=envelope[8],
            rc=struct.unpack_from("<i", envelope, 9)[0],
            pmic_valid_mask=envelope[13],
            pmic_id=envelope[14],
            pmic_rev=envelope[15],
            initial_uic_valid=envelope[16],
            initial_uic=envelope[17],
            command_issued_mask=envelope[18],
            response_seen_mask=envelope[19],
            response_opcode=tuple(envelope[22:26]),
            response_value=tuple(envelope[26:30]),
            poll_bytes=(b"", b"", b"", b"") if poll_vectors is None else poll_vectors,
            write_attempted=envelope[20],
            write_ambiguous=envelope[21],
        )
        if poll_vectors is None:
            _validate_result_fixed(fixed_result)
            _validate_poll_summary(
                poll_summary,
                counts=counts,
                command_issued_mask=fixed_result.command_issued_mask,
                response_seen_mask=fixed_result.response_seen_mask,
                stage=fixed_result.stage,
                rc=fixed_result.rc,
            )
        else:
            _validate_result(fixed_result)
        result = {
            "stage": fixed_result.stage,
            "rc": fixed_result.rc,
            "pmic_valid_mask": fixed_result.pmic_valid_mask,
            "pmic_id": fixed_result.pmic_id,
            "pmic_rev": fixed_result.pmic_rev,
            "initial_uic_valid": fixed_result.initial_uic_valid,
            "initial_uic": fixed_result.initial_uic,
            "command_issued_mask": fixed_result.command_issued_mask,
            "response_seen_mask": fixed_result.response_seen_mask,
            "write_attempted": fixed_result.write_attempted,
            "write_ambiguous": fixed_result.write_ambiguous,
            "response_opcode": fixed_result.response_opcode,
            "response_value": fixed_result.response_value,
            "poll_count": counts,
            "poll_bytes": poll_vectors,
            "poll_sha256": poll_summary.sha256.hex(),
            "poll_or": poll_summary.or_mask,
            "poll0": poll_summary.poll0,
            "poll_nonzero_count": poll_summary.nonzero_count,
        }
        result["post2_retention"] = _post2_retention_interpretation(result)
        expected_terminal, expected_mux = classify_diagnostic_result(
            binding, fixed_result
        )
        if flags & FLAG_POLL_OVERFLOW:
            if expected_mux is None:
                raise TelemetryError("overflow summary does not wrap a MUX result")
        elif (terminal_bucket, mux_class) != (expected_terminal, expected_mux):
            raise TelemetryError("retained semantic and diagnostic result disagree")
    binding_field_names = tuple(surface.DIAG_EAGAIN_BINDING_WITNESS_FIELDS)
    encoded_binding = {
        name: value
        for name, value in zip(
            binding_field_names,
            binding_values,
            strict=True,
        )
    }
    authoritative_binding_fields = set(binding_field_names)
    if observer_site_code == 0 and (
        binding.loader_state != LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]
    ):
        # The late loader publishes module-open/helper failures and deadline
        # terminals before post-topology is sampled.  Their zero-filled post
        # bytes are placeholders, not absence witnesses.
        authoritative_binding_fields = set(binding_field_names[:5])
    elif observer_site_code != 0:
        authoritative_binding_fields = {"loader_state"}
        if observer_site in {
            "late-loader", "post-topology", "result-policy", "result-read"
        }:
            authoritative_binding_fields.update(binding_field_names[:5])
        if observer_site in {"result-policy", "result-read"}:
            authoritative_binding_fields.update(binding_field_names)
    decoded = {
        "schema": SCHEMA,
        "terminal_bucket": terminal_bucket,
        "terminal_classification": (
            surface.DIAG_RUNTIME_TERMINAL_BUCKETS.get(terminal_bucket)
            if terminal_bucket is not None
            else None
        ),
        "mux_class": mux_class,
        "binding": {
            name: (
                value if name in authoritative_binding_fields else None
            )
            for name, value in encoded_binding.items()
        },
        "binding_encoded": encoded_binding,
        "binding_authority": {
            name: name in authoritative_binding_fields
            for name in binding_field_names
        },
        "result": result,
        "poll_raw_size": raw_size,
        "poll_encoded_size": encoded_size,
        "poll_encoding": encoding,
        "poll_lossless": bool(flags & FLAG_POLL_LOSSLESS),
        "payload_overflow": bool(flags & FLAG_POLL_OVERFLOW),
        "causal_result_allowed": causal_result_allowed,
        "observer_site": None if observer_site_code == 0 else observer_site,
        "observer_error_class": (
            None if observer_error_code == 0 else observer_error_class
        ),
        "envelope_crc32": recorded,
    }
    eagain_buckets = {
        "driver_registered_without_matching_parent",
        "matching_parent_identity_rejected",
        "parent_ownership_conflict",
        "result_not_ready_eagain",
        "synchronous_probe_or_publication_contradiction",
    }
    if observer_site_code != 0:
        preflight_sites = {
            "override-prepare",
            "substrate-verify",
            "pre-topology",
        }
        decoded["eagain_row"] = None
        decoded["observer_failure_scope"] = (
            "preflight" if observer_site in preflight_sites else "diagnostic"
        )
        decoded["preflight_observer_contradiction"] = (
            observer_site in preflight_sites
        )
    elif result is None and terminal_bucket in eagain_buckets:
        if (
            terminal_bucket
            == "synchronous_probe_or_publication_contradiction"
            and binding.loader_state == LOADER_STATES["NOT_STARTED"]
        ):
            decoded["eagain_row"] = None
            decoded["preflight_observer_contradiction"] = True
        else:
            row = classify_eagain_binding(binding)
            if eagain_terminal_bucket(row) != terminal_bucket:
                raise TelemetryError("EAGAIN row and terminal bucket disagree")
            decoded["eagain_row"] = row
            decoded["eagain_terminal"] = bool(
                surface.DIAG_EAGAIN_OBSERVABLE_ROWS[row].get("terminal", True)
            )
    return decoded


def expected_b_detail(decoded: dict[str, Any]) -> int:
    terminal_bucket = decoded.get("terminal_bucket")
    mux_class = decoded.get("mux_class")
    return terminal_detail(
        terminal_bucket=terminal_bucket,
        mux_class=mux_class,
    )


def _progress_prefix(run_id: bytes) -> bytes:
    value = carrier.initialize_record(fixed_spec.PROFILE, run_id)
    for generation in range(1, fixed_spec.ATTR_ORDINAL + 1):
        position = fixed_spec.position_for_generation(generation)
        value = carrier.apply_request(
            value,
            carrier.encode_request(
                fixed_spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=0,
            ),
        )
    return value


def encode_carrier_record(envelope: bytes, *, run_id: bytes) -> bytes:
    decoded = decode_envelope(envelope)
    if len(envelope) != 2 * SLOT_PAYLOAD_SIZE:
        raise TelemetryError("Max77705 envelope cannot fill two carrier slots")
    value = _progress_prefix(run_id)
    first_generation = fixed_spec.ATTR_ORDINAL + 1
    first = fixed_spec.position_for_generation(first_generation)
    value = carrier.apply_request(
        value,
        carrier.encode_request(
            fixed_spec.PROFILE,
            first.stage,
            run_id=run_id,
            outcome=carrier.OUTCOME_PROGRESS,
            item_index=first.item_index,
            detail=A_DETAIL,
            payload_kind=carrier.PAYLOAD_RAW_EXCERPT,
            payload=envelope[:SLOT_PAYLOAD_SIZE],
            version=carrier.REQUEST_VERSION_V3,
        ),
    )
    second_generation = fixed_spec.SUMMARY_ORDINAL + 1
    second = fixed_spec.position_for_generation(second_generation)
    value = carrier.apply_request(
        value,
        carrier.encode_request(
            fixed_spec.PROFILE,
            second.stage,
            run_id=run_id,
            outcome=carrier.OUTCOME_FAILURE,
            item_index=second.item_index,
            detail=expected_b_detail(decoded),
            payload_kind=carrier.PAYLOAD_RAW_EXCERPT,
            payload=envelope[SLOT_PAYLOAD_SIZE:],
            version=carrier.REQUEST_VERSION_V3,
        ),
    )
    return value


def decode_carrier_record(record: bytes, *, run_id: bytes) -> dict[str, Any]:
    decoded = carrier.decode_record(
        record,
        expected_profile=fixed_spec.PROFILE,
        expected_run_id=run_id,
    )
    slots = {slot["generation"]: slot for slot in decoded["valid_slots"]}
    first_generation = fixed_spec.ATTR_ORDINAL + 1
    second_generation = fixed_spec.SUMMARY_ORDINAL + 1
    if set(slots) != {first_generation, second_generation}:
        raise TelemetryError("Max77705 carrier does not retain the exact pair")
    first, second = slots[first_generation], slots[second_generation]
    if (
        first["outcome"] != carrier.OUTCOME_PROGRESS
        or first["detail"] != A_DETAIL
        or first["payload_kind"] != carrier.PAYLOAD_RAW_EXCERPT
        or len(first["payload"]) != SLOT_PAYLOAD_SIZE
        or second["outcome"] != carrier.OUTCOME_FAILURE
        or second["payload_kind"] != carrier.PAYLOAD_RAW_EXCERPT
        or len(second["payload"]) != SLOT_PAYLOAD_SIZE
    ):
        raise TelemetryError("Max77705 carrier pair shape differs")
    envelope = first["payload"] + second["payload"]
    result = decode_envelope(envelope)
    if second["detail"] != expected_b_detail(result):
        raise TelemetryError("Max77705 carrier detail and envelope disagree")
    return {
        **result,
        "carrier_family": carrier.LONG_FAMILY.decode("ascii"),
        "record_count": 1,
        "slot_payload_sizes": [len(first["payload"]), len(second["payload"])],
        "a_detail": first["detail"],
        "b_detail": second["detail"],
        "adjacent_terminal_pair": True,
    }


def validate() -> dict[str, Any]:
    if (
        ENVELOPE_SIZE != 2 * SLOT_PAYLOAD_SIZE
        or SLOT_PAYLOAD_SIZE != carrier.REQUEST_PAYLOAD_SIZE
        or PAYLOAD_AREA_OFFSET + PAYLOAD_AREA_SIZE != CRC_OFFSET
        or POLL_SUMMARY_SIZE != 44
        or POLL_SUMMARY_SIZE > PAYLOAD_AREA_SIZE
        or UIC_DETECTION_LATCH_MASK != 0x7B
        or UIC_BC12_REDETECTION_LATCH_MASK != 0x0A
        or len(TERMINAL_BUCKET_KEYS) != 9
        or len(set(TERMINAL_DETAIL_BY_KEY.values())) != 9
        or not all(0x6701 <= value <= 0x673F for value in (
            *TERMINAL_DETAIL_BY_KEY.values(),
            *MUX_DETAIL_BY_NAME.values(),
        ))
        or A_DETAIL != 0xDA3
    ):
        raise TelemetryError("Max77705 telemetry geometry differs")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "carrier": carrier.LONG_FAMILY.decode("ascii"),
        "record_count": 1,
        "retained_slot_count": 2,
        "slot_payload_size": SLOT_PAYLOAD_SIZE,
        "envelope_size": ENVELOPE_SIZE,
        "packbits_payload_capacity": PAYLOAD_AREA_SIZE,
        "overflow_poll_summary_size": POLL_SUMMARY_SIZE,
        "overflow_summary_spare_bytes": PAYLOAD_AREA_SIZE - POLL_SUMMARY_SIZE,
        "post2_poll0_retention_axis": True,
        "terminal_bucket_count": len(TERMINAL_BUCKET_KEYS),
        "mux_device_class_count": len(MUX_DEVICE_CLASSES),
        "negative_invariant_count": len(surface.DIAG_EAGAIN_NEGATIVE_INVARIANTS),
        "claim_busy_decoder_preimage_empty": True,
        "full_lto_required": False,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
