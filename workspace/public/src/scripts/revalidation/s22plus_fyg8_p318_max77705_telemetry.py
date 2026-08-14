#!/usr/bin/env python3
"""P3.18 fixed 128-byte Max77705 envelope-v4 telemetry authority."""

from __future__ import annotations

import binascii
from dataclasses import dataclass
import struct
from typing import Any

import s22plus_fyg8_p317_max77705_telemetry as p317


SCHEMA = "s22plus_fyg8_p318_max77705_telemetry_v4"
ENVELOPE_MAGIC = b"MXD4"
ENVELOPE_VERSION = 4
CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-DIAG-V4\0"
ENVELOPE_SIZE = p317.ENVELOPE_SIZE
PAYLOAD_OFFSET = p317.PAYLOAD_AREA_OFFSET
PAYLOAD_SIZE = p317.PAYLOAD_AREA_SIZE
CRC_OFFSET = p317.CRC_OFFSET
TIMING_SIZE = 26
BANNER_SIZE = 3
PREFIX_SIZE = 29
LOSSLESS_CAPACITY = 47
OVERFLOW_SUMMARY_SIZE = 44
OVERFLOW_USED = 73
OVERFLOW_SPARE = 3
RETENTION_NS = 30_000_000_000

TIME_PRE = 1 << 0
TIME_WRITE = 1 << 1
TIME_POST1 = 1 << 2
TIME_POST2 = 1 << 3
TIME_HOST_EVENT = 1 << 4
TIME_INSTALL = 1 << 5
TIME_EXPOSURE = 1 << 6
TIME_NO_PRE_GATE_EVENT = 1 << 7
TIME_MASK = 0xFF
CAUSAL_NO_EVENT = 0xEF
CAUSAL_WITH_EVENT = 0xFF

HOST_EVENT_KINDS = {"none": 0, "reset": 1, "connect_done": 2, "setup": 3}
HOST_EVENT_KIND_NAMES = {value: key for key, value in HOST_EVENT_KINDS.items()}

BANNER_OUTCOMES = {
    "not_attempted": 0,
    "written": 1,
    "eagain_timeout": 2,
    "failure": 3,
    "partial": 4,
}
BANNER_OUTCOME_NAMES = {value: key for key, value in BANNER_OUTCOMES.items()}
BANNER_ERRORS = {
    "none": 0,
    "eagain_deadline": 1,
    "eintr_deadline": 2,
    "epipe": 3,
    "enodev": 4,
    "etimedout": 5,
    "zero_write": 6,
    "invalid_write": 7,
    "clock": 8,
    "other": 9,
}
BANNER_ERROR_NAMES = {value: key for key, value in BANNER_ERRORS.items()}
OBSERVER_SITES = {
    **p317.OBSERVER_SITES,
    "exposure-gate": 13,
    "timing-latch": 14,
}
OBSERVER_SITE_NAMES = {value: key for key, value in OBSERVER_SITES.items()}
_BASE_OBSERVER_SITE = {
    "exposure-gate": "override-prepare",
    "timing-latch": "result-read",
}


class TelemetryV4Error(ValueError):
    pass


@dataclass(frozen=True)
class TimedDiagnosticResult:
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
    timing_valid_mask: int
    pre_ns: int
    write_ns: int
    post1_ns: int
    post2_ns: int

    def base(self) -> p317.inherited.DiagnosticResult:
        return p317.inherited.DiagnosticResult(
            stage=self.stage,
            rc=self.rc,
            pmic_valid_mask=self.pmic_valid_mask,
            pmic_id=self.pmic_id,
            pmic_rev=self.pmic_rev,
            initial_uic_valid=self.initial_uic_valid,
            initial_uic=self.initial_uic,
            command_issued_mask=self.command_issued_mask,
            response_seen_mask=self.response_seen_mask,
            response_opcode=self.response_opcode,
            response_value=self.response_value,
            poll_bytes=self.poll_bytes,
            write_attempted=self.write_attempted,
            write_ambiguous=self.write_ambiguous,
        )


@dataclass(frozen=True)
class LatchSnapshot:
    install_valid: int
    gate_valid: int
    event_valid: int
    event_kind: int
    install_ns: int
    gate_ns: int
    event_ns: int
    event_raw: int
    pre_gate_events: int


@dataclass(frozen=True)
class BannerResult:
    outcome: int
    error_class: int
    bytes_written: int


@dataclass(frozen=True)
class TimingWitness:
    valid_mask: int
    first_host_event_kind: int
    latch_install_delta_us: int
    gate_write_delta_us: int
    write_delta_us: int
    post1_delta_us: int
    post2_delta_us: int
    first_host_event_delta_us: int


def _delta_us(sample_ns: int, origin_ns: int) -> int:
    if type(sample_ns) is not int or type(origin_ns) is not int:
        raise TelemetryV4Error("P3.18 time sample is not an integer")
    difference = sample_ns - origin_ns
    value = abs(difference) // 1000
    if difference < 0:
        value = -value
    if not -(2**31) <= value <= 2**31 - 1:
        raise TelemetryV4Error("P3.18 signed microsecond delta overflows")
    return value


def _validate_banner(banner: BannerResult) -> None:
    if (
        banner.outcome not in BANNER_OUTCOME_NAMES
        or banner.error_class not in BANNER_ERROR_NAMES
        or not 0 <= banner.bytes_written <= 49
    ):
        raise TelemetryV4Error("P3.18 banner byte domain differs")
    if banner.outcome == BANNER_OUTCOMES["not_attempted"]:
        valid = banner.error_class == 0 and banner.bytes_written == 0
    elif banner.outcome == BANNER_OUTCOMES["written"]:
        valid = banner.error_class == 0 and banner.bytes_written == 49
    elif banner.outcome == BANNER_OUTCOMES["eagain_timeout"]:
        valid = banner.error_class == BANNER_ERRORS["eagain_deadline"] and banner.bytes_written == 0
    elif banner.outcome == BANNER_OUTCOMES["failure"]:
        valid = banner.error_class not in {0, BANNER_ERRORS["eagain_deadline"]} and banner.bytes_written == 0
    else:
        valid = banner.error_class != 0 and 1 <= banner.bytes_written <= 48
    if not valid:
        raise TelemetryV4Error("P3.18 banner outcome tuple is inconsistent")


def _validate_latch(latch: LatchSnapshot | None) -> None:
    if latch is None:
        return
    if any(value not in {0, 1} for value in (latch.install_valid, latch.gate_valid, latch.event_valid)):
        raise TelemetryV4Error("P3.18 latch validity byte differs")
    if type(latch.pre_gate_events) is not int or not 0 <= latch.pre_gate_events <= 0x3FFFFFFF:
        raise TelemetryV4Error("P3.18 pre-gate event count differs")
    if (
        (not latch.install_valid and latch.install_ns)
        or (not latch.gate_valid and latch.gate_ns)
        or (not latch.event_valid and (latch.event_ns or latch.event_kind or latch.event_raw))
        or (latch.gate_valid and not latch.install_valid)
        or (latch.event_valid and not latch.gate_valid)
        or (latch.event_valid and latch.event_kind not in {1, 2, 3})
        or (latch.install_valid and not latch.install_ns)
        or (latch.gate_valid and not latch.gate_ns)
        or (latch.event_valid and not latch.event_ns)
        or (latch.gate_valid and latch.install_ns > latch.gate_ns)
        or (latch.event_valid and latch.event_ns < latch.gate_ns)
        or (latch.event_valid and not _raw_kind_matches(latch.event_kind, latch.event_raw))
    ):
        raise TelemetryV4Error("P3.18 latch snapshot is inconsistent")


def _raw_kind_matches(kind: int, raw: int) -> bool:
    event_class = (raw >> 1) & 0x7F
    if kind in {1, 2}:
        return bool(raw & 1) and event_class == 0 and (raw >> 8) & 0x0F == kind
    if kind == 3:
        return not raw & 1 and (raw >> 1) & 0x1F == 0 and (raw >> 6) & 0x0F == 1
    return kind == 0 and raw == 0


def _validate_timed_result(result: TimedDiagnosticResult) -> None:
    p317.inherited._validate_result(result.base())  # noqa: SLF001
    mask = result.timing_valid_mask
    if mask & 0xF0:
        raise TelemetryV4Error("P3.18 diagnostic timing mask differs")
    samples = (result.pre_ns, result.write_ns, result.post1_ns, result.post2_ns)
    for index, sample in enumerate(samples):
        if ((mask >> index) & 1) != bool(sample):
            raise TelemetryV4Error("P3.18 diagnostic timing validity differs")
    if bool(mask & TIME_WRITE) != bool(result.write_attempted):
        raise TelemetryV4Error("P3.18 write timing and attempt differ")
    if mask & TIME_WRITE and result.pre_ns > result.write_ns:
        raise TelemetryV4Error("P3.18 pre/write ordering differs")
    if mask & TIME_POST1 and result.pre_ns > result.post1_ns:
        raise TelemetryV4Error("P3.18 pre/post1 ordering differs")
    if mask & TIME_WRITE and mask & TIME_POST1 and result.write_ns > result.post1_ns:
        raise TelemetryV4Error("P3.18 write/post1 ordering differs")
    if mask & TIME_POST1 and mask & TIME_POST2 and (
        result.post1_ns > result.post2_ns
        or result.post2_ns - result.post1_ns < RETENTION_NS
    ):
        raise TelemetryV4Error("P3.18 post2 retention ordering differs")
    expected_masks = {
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0x03,
        7: 0x03 if result.write_attempted else 0x01,
        9: 0x07 if result.write_attempted else 0x05,
        10: 0x0F if result.write_attempted else 0x0D,
    }
    if result.stage == 8 or expected_masks.get(result.stage) != mask:
        raise TelemetryV4Error("P3.18 source-reachable timing mask differs")


def derive_timing(
    result: TimedDiagnosticResult | None,
    latch: LatchSnapshot | None,
) -> TimingWitness:
    _validate_latch(latch)
    if result is None:
        if latch is not None:
            raise TelemetryV4Error("P3.18 latch lacks a diagnostic time origin")
        return TimingWitness(0, 0, 0, 0, 0, 0, 0, 0)
    _validate_timed_result(result)
    if not result.timing_valid_mask & TIME_PRE:
        if latch is not None:
            raise TelemetryV4Error("P3.18 latch lacks a retained pre origin")
        return TimingWitness(result.timing_valid_mask, 0, 0, 0, 0, 0, 0, 0)
    mask = result.timing_valid_mask
    origin = result.pre_ns
    values = {
        "install": 0,
        "exposure": 0,
        "write": _delta_us(result.write_ns, origin) if mask & TIME_WRITE else 0,
        "post1": _delta_us(result.post1_ns, origin) if mask & TIME_POST1 else 0,
        "post2": _delta_us(result.post2_ns, origin) if mask & TIME_POST2 else 0,
        "event": 0,
    }
    event_kind = 0
    if latch is not None:
        if latch.install_valid:
            mask |= TIME_INSTALL
            values["install"] = _delta_us(latch.install_ns, origin)
        if latch.gate_valid:
            mask |= TIME_EXPOSURE
            values["exposure"] = _delta_us(latch.gate_ns, origin)
        if latch.gate_valid and latch.pre_gate_events == 0:
            mask |= TIME_NO_PRE_GATE_EVENT
        if latch.event_valid:
            mask |= TIME_HOST_EVENT
            event_kind = latch.event_kind
            values["event"] = _delta_us(latch.event_ns, origin)
    timing = TimingWitness(
        mask, event_kind, values["install"], values["exposure"],
        values["write"], values["post1"], values["post2"], values["event"],
    )
    _validate_timing(timing)
    return timing


def _validate_timing(timing: TimingWitness) -> None:
    if timing.valid_mask & ~TIME_MASK or timing.first_host_event_kind not in HOST_EVENT_KIND_NAMES:
        raise TelemetryV4Error("P3.18 timing prefix reserved value differs")
    if bool(timing.valid_mask & TIME_HOST_EVENT) != bool(timing.first_host_event_kind):
        raise TelemetryV4Error("P3.18 host-event kind and validity differ")
    if timing.valid_mask & TIME_NO_PRE_GATE_EVENT and (
        timing.valid_mask & (TIME_INSTALL | TIME_EXPOSURE)
        != (TIME_INSTALL | TIME_EXPOSURE)
    ):
        raise TelemetryV4Error("P3.18 pre-gate absence lacks latch/gate authority")
    bit_values = (
        (TIME_INSTALL, timing.latch_install_delta_us),
        (TIME_EXPOSURE, timing.gate_write_delta_us),
        (TIME_WRITE, timing.write_delta_us),
        (TIME_POST1, timing.post1_delta_us),
        (TIME_POST2, timing.post2_delta_us),
        (TIME_HOST_EVENT, timing.first_host_event_delta_us),
    )
    if any(not timing.valid_mask & bit and value != 0 for bit, value in bit_values):
        raise TelemetryV4Error("P3.18 invalid timing field is nonzero")
    for _, value in bit_values:
        if not -(2**31) <= value <= 2**31 - 1:
            raise TelemetryV4Error("P3.18 timing delta overflows int32")
    required = TIME_PRE | TIME_INSTALL | TIME_EXPOSURE
    if timing.valid_mask & required == required and (
        timing.latch_install_delta_us > timing.gate_write_delta_us
        or timing.gate_write_delta_us > 0
    ):
        raise TelemetryV4Error("P3.18 structural install/gate/pre order differs")


def _timing_bytes(timing: TimingWitness) -> bytes:
    _validate_timing(timing)
    return bytes((timing.valid_mask, timing.first_host_event_kind)) + struct.pack(
        "<6i",
        timing.latch_install_delta_us,
        timing.gate_write_delta_us,
        timing.write_delta_us,
        timing.post1_delta_us,
        timing.post2_delta_us,
        timing.first_host_event_delta_us,
    )


def _crc(envelope: bytes | bytearray) -> int:
    return binascii.crc32(CRC_DOMAIN + bytes(envelope[:CRC_OFFSET])) & 0xFFFFFFFF


def encode_envelope(
    *,
    binding: p317.inherited.BindingWitness,
    exec_witness: p317.ExecWitness,
    banner: BannerResult,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: TimedDiagnosticResult | None = None,
    latch: LatchSnapshot | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> bytes:
    _validate_banner(banner)
    timing = derive_timing(result, latch)
    base_result = None if result is None else result.base()
    if observer_site is not None and observer_site not in OBSERVER_SITES:
        raise TelemetryV4Error("P3.18 observer site is undeclared")
    base_observer_site = _BASE_OBSERVER_SITE.get(observer_site, observer_site)
    base = p317.encode_envelope(
        binding=binding,
        exec_witness=exec_witness,
        terminal_bucket=terminal_bucket,
        mux_class=mux_class,
        result=base_result,
        observer_site=base_observer_site,
        observer_error_class=observer_error_class,
    )
    envelope = bytearray(base)
    raw_poll = b"" if result is None else b"".join(result.poll_bytes)
    summary = None if result is None else p317.inherited.summarize_poll_vectors(result.poll_bytes)
    encoded_poll = p317.inherited.packbits_encode(raw_poll)
    flags = envelope[7] & (
        p317.FLAG_RESULT_PRESENT | p317.FLAG_BINDING_PRESENT | p317.FLAG_EXEC_PRESENT
    )
    envelope[0:4] = ENVELOPE_MAGIC
    envelope[4] = ENVELOPE_VERSION
    envelope[PAYLOAD_OFFSET:CRC_OFFSET] = b"\0" * PAYLOAD_SIZE
    prefix = _timing_bytes(timing) + bytes((banner.outcome, banner.error_class, banner.bytes_written))
    if len(prefix) != PREFIX_SIZE:
        raise TelemetryV4Error("P3.18 prefix geometry differs")
    envelope[PAYLOAD_OFFSET:PAYLOAD_OFFSET + PREFIX_SIZE] = prefix
    if len(encoded_poll) > LOSSLESS_CAPACITY:
        if summary is None:
            raise TelemetryV4Error("P3.18 overflow lacks a result summary")
        envelope[5] = p317.TERMINAL_CODE_BY_KEY["result_payload_unrepresentable"]
        envelope[6] = 0
        flags |= p317.FLAG_POLL_OVERFLOW
        envelope[43] = p317.inherited.POLL_ENCODING_SHA256_SUMMARY
        envelope[46] = OVERFLOW_USED
        envelope[PAYLOAD_OFFSET + PREFIX_SIZE:PAYLOAD_OFFSET + OVERFLOW_USED] = summary.payload()
    else:
        flags |= p317.FLAG_POLL_LOSSLESS
        envelope[43] = p317.inherited.POLL_ENCODING_PACKBITS
        envelope[46] = PREFIX_SIZE + len(encoded_poll)
        envelope[PAYLOAD_OFFSET + PREFIX_SIZE:PAYLOAD_OFFSET + PREFIX_SIZE + len(encoded_poll)] = encoded_poll
    envelope[7] = flags
    site_code = 0 if observer_site is None else OBSERVER_SITES[observer_site]
    error_code = 0 if observer_error_class is None else p317.OBSERVER_ERROR_CLASSES[observer_error_class]
    envelope[47] = (site_code << 4) | error_code
    struct.pack_into("<I", envelope, CRC_OFFSET, _crc(envelope))
    return bytes(envelope)


def _decode_timing(value: bytes) -> TimingWitness:
    if len(value) != TIMING_SIZE:
        raise TelemetryV4Error("P3.18 timing prefix extent differs")
    fields = struct.unpack("<6i", value[2:])
    timing = TimingWitness(value[0], value[1], *fields)
    _validate_timing(timing)
    return timing


def decode_envelope(envelope: bytes) -> dict[str, Any]:
    if len(envelope) != ENVELOPE_SIZE or envelope[:4] != ENVELOPE_MAGIC or envelope[4] != ENVELOPE_VERSION:
        raise TelemetryV4Error("P3.18 envelope identity differs")
    if struct.unpack_from("<I", envelope, CRC_OFFSET)[0] != _crc(envelope):
        raise TelemetryV4Error("P3.18 envelope CRC differs")
    used = envelope[46]
    if not PREFIX_SIZE <= used <= PAYLOAD_SIZE or any(envelope[PAYLOAD_OFFSET + used:CRC_OFFSET]):
        raise TelemetryV4Error("P3.18 payload extent or zero spare differs")
    timing = _decode_timing(envelope[PAYLOAD_OFFSET:PAYLOAD_OFFSET + TIMING_SIZE])
    banner = BannerResult(*envelope[PAYLOAD_OFFSET + TIMING_SIZE:PAYLOAD_OFFSET + PREFIX_SIZE])
    _validate_banner(banner)
    overflow = bool(envelope[7] & p317.FLAG_POLL_OVERFLOW)
    if overflow:
        if used != OVERFLOW_USED:
            raise TelemetryV4Error("P3.18 overflow extent differs")
        poll_size = OVERFLOW_SUMMARY_SIZE
    else:
        poll_size = used - PREFIX_SIZE
        if poll_size > LOSSLESS_CAPACITY:
            raise TelemetryV4Error("P3.18 lossless poll capacity differs")
    poll = envelope[PAYLOAD_OFFSET + PREFIX_SIZE:PAYLOAD_OFFSET + PREFIX_SIZE + poll_size]

    site_code = envelope[47] >> 4
    error_code = envelope[47] & 0x0F
    observer_site = OBSERVER_SITE_NAMES.get(site_code)
    if observer_site is None:
        raise TelemetryV4Error("P3.18 observer site differs")
    base_site = _BASE_OBSERVER_SITE.get(observer_site, observer_site)
    base = bytearray(envelope)
    base[0:4] = p317.ENVELOPE_MAGIC
    base[4] = p317.ENVELOPE_VERSION
    base[PAYLOAD_OFFSET:CRC_OFFSET] = b"\0" * PAYLOAD_SIZE
    base[PAYLOAD_OFFSET:PAYLOAD_OFFSET + poll_size] = poll
    base[46] = poll_size
    base[47] = (p317.OBSERVER_SITES[base_site] << 4) | error_code
    crc = binascii.crc32(p317.CRC_DOMAIN + base[:CRC_OFFSET]) & 0xFFFFFFFF
    struct.pack_into("<I", base, CRC_OFFSET, crc)
    decoded = p317.decode_envelope(bytes(base))
    decoded["observer_site"] = None if site_code == 0 else observer_site
    mask_causal = timing.valid_mask in {CAUSAL_NO_EVENT, CAUSAL_WITH_EVENT}
    gate_write_before_pre = mask_causal and timing.gate_write_delta_us <= 0
    diagnostic_ready = bool(decoded["causal_result_allowed"])
    decoded["schema"] = SCHEMA
    decoded["timing"] = {
        "valid_mask": timing.valid_mask,
        "first_host_event_kind": HOST_EVENT_KIND_NAMES[timing.first_host_event_kind],
        "latch_install_delta_us": timing.latch_install_delta_us,
        "gate_write_delta_us": timing.gate_write_delta_us,
        "write_delta_us": timing.write_delta_us,
        "post1_delta_us": timing.post1_delta_us,
        "post2_delta_us": timing.post2_delta_us,
        "first_host_event_delta_us": timing.first_host_event_delta_us,
        "gate_write_before_pre": gate_write_before_pre,
        "latch_install_before_gate_write_structurally_enforced": (
            timing.latch_install_delta_us <= timing.gate_write_delta_us
        ),
        "no_pre_gate_qualifying_event": bool(
            timing.valid_mask & TIME_NO_PRE_GATE_EVENT
        ),
        "causal_mask": mask_causal,
    }
    decoded["banner"] = {
        "outcome": BANNER_OUTCOME_NAMES[banner.outcome],
        "error_class": BANNER_ERROR_NAMES[banner.error_class],
        "bytes_written": banner.bytes_written,
    }
    decoded["diagnostic_causal_prerequisites_ready"] = diagnostic_ready
    decoded["causal_pending_complete_host_receipt"] = (
        diagnostic_ready and gate_write_before_pre and not overflow
    )
    decoded["causal_result_allowed"] = False
    decoded["poll_encoded_size"] = poll_size
    decoded["payload_used_size"] = used
    decoded["overflow_spare_zero"] = True
    return decoded


def correlate_host_receipt(
    decoded: dict[str, Any], *, receipt_complete: bool, endpoint_present: bool
) -> dict[str, Any]:
    result = dict(decoded)
    timing = decoded["timing"]
    result["host_receipt_complete"] = receipt_complete
    result["host_endpoint_present"] = endpoint_present
    result["causal_result_allowed"] = False
    if not receipt_complete:
        result["correlation_class"] = "NO_PROOF_OBSERVER_HOST_RECEIPT_INCOMPLETE"
        return result
    if not decoded["causal_pending_complete_host_receipt"]:
        result["correlation_class"] = "NO_PROOF_OBSERVER_TIMING_NOT_CAUSAL"
        return result
    mask = timing["valid_mask"]
    if mask == CAUSAL_NO_EVENT:
        if endpoint_present:
            result["correlation_class"] = "NO_PROOF_OBSERVER_LATCHED_EVENT_MISSING"
        else:
            result["correlation_class"] = "DEVICE_RESULT_HOST_SILENT"
            result["causal_result_allowed"] = True
    elif mask == CAUSAL_WITH_EVENT:
        if endpoint_present:
            result["correlation_class"] = "DEVICE_RESULT_HOST_EVENT_AND_ENDPOINT"
            result["causal_result_allowed"] = True
        else:
            result["correlation_class"] = "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT"
    else:
        raise TelemetryV4Error("P3.18 causal mask branch is unreachable")
    return result


def expected_b_detail(decoded: dict[str, Any]) -> int:
    return p317.terminal_detail(
        terminal_bucket=decoded.get("terminal_bucket"),
        mux_class=decoded.get("mux_class"),
    )


def encode_carrier_record(envelope: bytes, *, run_id: bytes) -> bytes:
    decoded = decode_envelope(envelope)
    inherited = p317.inherited
    value = inherited._progress_prefix(run_id)  # noqa: SLF001
    first_generation = inherited.fixed_spec.ATTR_ORDINAL + 1
    first = inherited.fixed_spec.position_for_generation(first_generation)
    value = inherited.carrier.apply_request(
        value,
        inherited.carrier.encode_request(
            inherited.fixed_spec.PROFILE,
            first.stage,
            run_id=run_id,
            outcome=inherited.carrier.OUTCOME_PROGRESS,
            item_index=first.item_index,
            detail=inherited.A_DETAIL,
            payload_kind=inherited.carrier.PAYLOAD_RAW_EXCERPT,
            payload=envelope[: p317.SLOT_PAYLOAD_SIZE],
            version=inherited.carrier.REQUEST_VERSION_V3,
        ),
    )
    second_generation = inherited.fixed_spec.SUMMARY_ORDINAL + 1
    second = inherited.fixed_spec.position_for_generation(second_generation)
    return inherited.carrier.apply_request(
        value,
        inherited.carrier.encode_request(
            inherited.fixed_spec.PROFILE,
            second.stage,
            run_id=run_id,
            outcome=inherited.carrier.OUTCOME_FAILURE,
            item_index=second.item_index,
            detail=expected_b_detail(decoded),
            payload_kind=inherited.carrier.PAYLOAD_RAW_EXCERPT,
            payload=envelope[p317.SLOT_PAYLOAD_SIZE :],
            version=inherited.carrier.REQUEST_VERSION_V3,
        ),
    )


def decode_carrier_record(record: bytes, *, run_id: bytes) -> dict[str, Any]:
    inherited = p317.inherited
    decoded_record = inherited.carrier.decode_record(
        record,
        expected_profile=inherited.fixed_spec.PROFILE,
        expected_run_id=run_id,
    )
    slots = {slot["generation"]: slot for slot in decoded_record["valid_slots"]}
    first_generation = inherited.fixed_spec.ATTR_ORDINAL + 1
    second_generation = inherited.fixed_spec.SUMMARY_ORDINAL + 1
    if set(slots) != {first_generation, second_generation}:
        raise TelemetryV4Error("P3.18 Carrier-v2 pair differs")
    first = slots[first_generation]
    second = slots[second_generation]
    if (
        first["outcome"] != inherited.carrier.OUTCOME_PROGRESS
        or first["detail"] != inherited.A_DETAIL
        or len(first["payload"]) != p317.SLOT_PAYLOAD_SIZE
        or second["outcome"] != inherited.carrier.OUTCOME_FAILURE
        or len(second["payload"]) != p317.SLOT_PAYLOAD_SIZE
    ):
        raise TelemetryV4Error("P3.18 Carrier-v2 slot shape differs")
    result = decode_envelope(first["payload"] + second["payload"])
    if second["detail"] != expected_b_detail(result):
        raise TelemetryV4Error("P3.18 Carrier detail and v4 semantics disagree")
    return {
        **result,
        "carrier_family": inherited.carrier.LONG_FAMILY.decode("ascii"),
        "record_count": 1,
        "slot_payload_sizes": [p317.SLOT_PAYLOAD_SIZE, p317.SLOT_PAYLOAD_SIZE],
        "a_detail": first["detail"],
        "b_detail": second["detail"],
        "adjacent_terminal_pair": True,
    }
