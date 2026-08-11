#!/usr/bin/env python3
"""Max77705 diagnostic telemetry over the fixed P3.10 Carrier-v2 record.

The fixed Image retains one 192-byte record with two 64-byte request payloads.
This module therefore defines one fixed 128-byte envelope.  Read-to-clear poll
bytes are PackBits-compressed losslessly.  A result that cannot fit is retained
as an explicit no-proof overflow bucket with a digest; it is never decoded as a
MUX result.
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


SCHEMA = "s22plus_fyg8_max77705_telemetry_v1"
TARGET = surface.TARGET

ENVELOPE_MAGIC = b"MXD1"
ENVELOPE_VERSION = 1
ENVELOPE_SIZE = 128
SLOT_PAYLOAD_SIZE = 64
PAYLOAD_AREA_OFFSET = 48
PAYLOAD_AREA_SIZE = 76
CRC_OFFSET = 124
POLL_ENCODING_PACKBITS = 1
POLL_ENCODING_SHA256_ONLY = 2

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

CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-DIAG-V1\0"


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


def _validate_result(result: DiagnosticResult) -> bytes:
    _u8(result.stage, "diagnostic stage")
    _s32(result.rc, "diagnostic rc")
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
    if result.write_attempted not in {0, 1} or result.write_ambiguous not in {0, 1}:
        raise TelemetryError("write flags are not binary")
    for label, values in (
        ("response opcode", result.response_opcode),
        ("response value", result.response_value),
    ):
        if len(values) != 4:
            raise TelemetryError(f"{label} extent differs")
        for value in values:
            _u8(value, label)
    if len(result.poll_bytes) != 4:
        raise TelemetryError("poll-vector extent differs")
    for value in result.poll_bytes:
        if not isinstance(value, bytes) or len(value) > 100:
            raise TelemetryError("poll vector is outside the source bound")
    return b"".join(result.poll_bytes)


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
) -> bytes:
    _validate_binding(binding)
    detail = terminal_detail(terminal_bucket=terminal_bucket, mux_class=mux_class)
    del detail  # The detail is redundantly checked when the carrier is assembled.
    terminal_code = 0 if terminal_bucket is None else TERMINAL_CODE_BY_KEY[terminal_bucket]
    mux_code = 0 if mux_class is None else MUX_CODE_BY_NAME[mux_class]
    flags = FLAG_BINDING_PRESENT
    raw_poll = b""
    if result is not None:
        raw_poll = _validate_result(result)
        flags |= FLAG_RESULT_PRESENT
    elif mux_class is not None:
        raise TelemetryError("MUX classification requires a diagnostic result")

    encoded_poll = packbits_encode(raw_poll)
    encoding = POLL_ENCODING_PACKBITS
    payload = encoded_poll
    if len(encoded_poll) > PAYLOAD_AREA_SIZE:
        terminal_bucket = "result_payload_unrepresentable"
        terminal_code = TERMINAL_CODE_BY_KEY[terminal_bucket]
        mux_code = 0
        flags |= FLAG_POLL_OVERFLOW
        flags &= ~FLAG_POLL_LOSSLESS
        encoding = POLL_ENCODING_SHA256_ONLY
        payload = hashlib.sha256(raw_poll).digest()
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
    envelope[47] = 0
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
    if envelope[47] or any(envelope[48 + envelope[46] : CRC_OFFSET]):
        raise TelemetryError("Max77705 envelope reserved bytes differ")

    binding_values = tuple(envelope[34:43])
    binding = BindingWitness(*binding_values)
    _validate_binding(binding)
    raw_size = struct.unpack_from("<H", envelope, 44)[0]
    encoded_size = envelope[46]
    if encoded_size > PAYLOAD_AREA_SIZE:
        raise TelemetryError("Max77705 payload length differs")
    encoded = envelope[PAYLOAD_AREA_OFFSET : PAYLOAD_AREA_OFFSET + encoded_size]
    encoding = envelope[43]
    poll_vectors: tuple[bytes, bytes, bytes, bytes] | None = None
    poll_digest: str | None = None
    causal_result_allowed = False
    if flags & FLAG_POLL_OVERFLOW:
        if (
            terminal_bucket != "result_payload_unrepresentable"
            or mux_code != 0
            or flags & FLAG_POLL_LOSSLESS
            or encoding != POLL_ENCODING_SHA256_ONLY
            or encoded_size != hashlib.sha256().digest_size
        ):
            raise TelemetryError("Max77705 overflow envelope is not fail-closed")
        poll_digest = encoded.hex()
    else:
        if not flags & FLAG_POLL_LOSSLESS or encoding != POLL_ENCODING_PACKBITS:
            raise TelemetryError("Max77705 causal envelope is not lossless")
        raw = packbits_decode(encoded, expected_size=raw_size)
        counts = tuple(envelope[30:34])
        if sum(counts) != raw_size:
            raise TelemetryError("Max77705 poll counts differ from raw extent")
        parts: list[bytes] = []
        cursor = 0
        for count in counts:
            parts.append(raw[cursor : cursor + count])
            cursor += count
        poll_vectors = tuple(parts)  # type: ignore[assignment]
        causal_result_allowed = mux_class is not None

    result_present = bool(flags & FLAG_RESULT_PRESENT)
    if mux_class is not None and not result_present:
        raise TelemetryError("Max77705 MUX row lacks a diagnostic result")
    result: dict[str, Any] | None = None
    if result_present:
        result = {
            "stage": envelope[8],
            "rc": struct.unpack_from("<i", envelope, 9)[0],
            "pmic_valid_mask": envelope[13],
            "pmic_id": envelope[14],
            "pmic_rev": envelope[15],
            "initial_uic_valid": envelope[16],
            "initial_uic": envelope[17],
            "command_issued_mask": envelope[18],
            "response_seen_mask": envelope[19],
            "write_attempted": envelope[20],
            "write_ambiguous": envelope[21],
            "response_opcode": tuple(envelope[22:26]),
            "response_value": tuple(envelope[26:30]),
            "poll_count": tuple(envelope[30:34]),
            "poll_bytes": poll_vectors,
            "poll_sha256": poll_digest,
        }
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
            name: value
            for name, value in zip(
                surface.DIAG_EAGAIN_BINDING_WITNESS_FIELDS,
                binding_values,
                strict=True,
            )
        },
        "result": result,
        "poll_raw_size": raw_size,
        "poll_encoded_size": encoded_size,
        "poll_encoding": encoding,
        "poll_lossless": bool(flags & FLAG_POLL_LOSSLESS),
        "payload_overflow": bool(flags & FLAG_POLL_OVERFLOW),
        "causal_result_allowed": causal_result_allowed,
        "envelope_crc32": recorded,
    }
    eagain_buckets = {
        "driver_registered_without_matching_parent",
        "matching_parent_identity_rejected",
        "parent_ownership_conflict",
        "result_not_ready_eagain",
        "synchronous_probe_or_publication_contradiction",
    }
    if result is None and terminal_bucket in eagain_buckets:
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
