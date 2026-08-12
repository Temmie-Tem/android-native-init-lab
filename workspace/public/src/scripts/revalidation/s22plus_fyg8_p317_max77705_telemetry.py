#!/usr/bin/env python3
"""P3.17 Max77705 fixed-size envelope-v3 telemetry.

The outer Carrier-v2 record and its two request-v3 payloads are unchanged.
Envelope v3 compacts the P3.16 binding witness and retains the boot-specific
fw_devlink/provider executability evidence without reducing poll capacity.
"""

from __future__ import annotations

import binascii
from dataclasses import dataclass
import hashlib
import struct
from typing import Any

import s22plus_fyg8_max77705_telemetry as inherited


SCHEMA = "s22plus_fyg8_p317_max77705_telemetry_v3"
TARGET = inherited.TARGET
ENVELOPE_MAGIC = b"MXD3"
ENVELOPE_VERSION = 3
ENVELOPE_SIZE = inherited.ENVELOPE_SIZE
SLOT_PAYLOAD_SIZE = inherited.SLOT_PAYLOAD_SIZE
PAYLOAD_AREA_OFFSET = inherited.PAYLOAD_AREA_OFFSET
PAYLOAD_AREA_SIZE = inherited.PAYLOAD_AREA_SIZE
CRC_OFFSET = inherited.CRC_OFFSET
CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-DIAG-V3\0"

FLAG_RESULT_PRESENT = inherited.FLAG_RESULT_PRESENT
FLAG_POLL_OVERFLOW = inherited.FLAG_POLL_OVERFLOW
FLAG_BINDING_PRESENT = inherited.FLAG_BINDING_PRESENT
FLAG_POLL_LOSSLESS = inherited.FLAG_POLL_LOSSLESS
FLAG_EXEC_PRESENT = 1 << 4
FLAG_MASK = inherited.FLAG_MASK | FLAG_EXEC_PRESENT

POLICY_STATE_MASK = 0x07
POLICY_GADGET_READY = 1 << 3
POLICY_VALID = 1 << 7
PROVIDER_MASK = 0x07
PROVIDER_DUPLICATE_SHIFT = 4
PROVIDER_VALID = 1 << 7
WAITING_MASK = 0x03
SUPPLIER_SHIFT = 2
SUPPLIER_MASK = 0x0C
LINK_VALID = 1 << 7

POLICY_STATES = {
    "UNAVAILABLE": 0,
    "DEFAULT_ON_STRICT": 1,
    "FW_DEVLINK_TOKEN_PRESENT": 2,
    "FW_DEVLINK_STRICT_TOKEN_PRESENT": 3,
    "BOTH_OVERRIDE_TOKENS_PRESENT": 4,
}
POLICY_STATE_NAMES = {value: key for key, value in POLICY_STATES.items()}
WAITING_STATES = {
    "UNAVAILABLE": 0,
    "FILE_ABSENT": 1,
    "ZERO": 2,
    "ONE": 3,
}
WAITING_STATE_NAMES = {value: key for key, value in WAITING_STATES.items()}
SUPPLIER_STATES = {
    "UNAVAILABLE": 0,
    "LINK_ABSENT": 1,
    "EXACT_ONE": 2,
    "FOREIGN_OR_MULTIPLE": 3,
}
SUPPLIER_STATE_NAMES = {value: key for key, value in SUPPLIER_STATES.items()}

TERMINAL_BUCKET_KEYS = (
    *inherited.TERMINAL_BUCKET_KEYS,
    "fw_devlink_policy_precondition",
    "provider_preclient_precondition",
    "provider_postclient_precondition",
    "supplier_link_precondition",
    "waiting_for_supplier_precondition",
    "executability_witness_contradiction",
)
TERMINAL_CLASSIFICATIONS = {
    **inherited.surface.DIAG_RUNTIME_TERMINAL_BUCKETS,
    "fw_devlink_policy_precondition": (
        "NO_PROOF_EXPERIMENT_PRECONDITION_FW_DEVLINK_POLICY"
    ),
    "provider_preclient_precondition": (
        "NO_PROOF_EXPERIMENT_PRECONDITION_PROVIDER_PRECLIENT"
    ),
    "provider_postclient_precondition": (
        "NO_PROOF_EXPERIMENT_PRECONDITION_PROVIDER_POSTCLIENT"
    ),
    "supplier_link_precondition": (
        "NO_PROOF_EXPERIMENT_PRECONDITION_SUPPLIER_IDENTITY"
    ),
    "waiting_for_supplier_precondition": (
        "NO_PROOF_EXPERIMENT_PRECONDITION_SUPPLIER_WAIT"
    ),
    "executability_witness_contradiction": (
        "NO_PROOF_OBSERVER_EXECUTABILITY_WITNESS_CONTRADICTION"
    ),
}
TERMINAL_CODE_BY_KEY = {
    key: index + 1 for index, key in enumerate(TERMINAL_BUCKET_KEYS)
}
TERMINAL_KEY_BY_CODE = {
    value: key for key, value in TERMINAL_CODE_BY_KEY.items()
}
TERMINAL_DETAIL_BY_KEY = {
    key: inherited.B_DETAIL_BASE + index
    for index, key in enumerate(TERMINAL_BUCKET_KEYS)
}
MUX_DEVICE_CLASSES = inherited.MUX_DEVICE_CLASSES
MUX_CODE_BY_NAME = inherited.MUX_CODE_BY_NAME
MUX_NAME_BY_CODE = inherited.MUX_NAME_BY_CODE
MUX_DETAIL_BY_NAME = inherited.MUX_DETAIL_BY_NAME
OBSERVER_SITES = {
    **inherited.OBSERVER_SITES,
    "cmdline": 8,
    "provider-pre": 9,
    "provider-post": 10,
    "supplier": 11,
    "waiting": 12,
}
OBSERVER_SITE_NAMES = {value: key for key, value in OBSERVER_SITES.items()}
OBSERVER_ERROR_CLASSES = inherited.OBSERVER_ERROR_CLASSES
OBSERVER_ERROR_CLASS_NAMES = inherited.OBSERVER_ERROR_CLASS_NAMES


class TelemetryError(ValueError):
    pass


@dataclass(frozen=True)
class ExecWitness:
    policy: int
    pre_present: int
    pre_bound: int
    post_present: int
    post_bound: int
    link_waiting: int

    def values(self) -> tuple[int, ...]:
        return (
            self.policy,
            self.pre_present,
            self.pre_bound,
            self.post_present,
            self.post_bound,
            self.link_waiting,
        )


def _count_class(value: int) -> int:
    return 0 if value == 0 else (1 if value == 1 else 2)


def _pack_binding(binding: inherited.BindingWitness) -> bytes:
    inherited._validate_binding(binding)  # noqa: SLF001
    values = binding.values()
    return bytes(
        (
            values[0] | (values[1] << 2) | (values[2] << 3) | (values[5] << 5),
            _count_class(values[3])
            | (_count_class(values[4]) << 2)
            | (_count_class(values[6]) << 4)
            | (_count_class(values[7]) << 6),
            _count_class(values[8]),
        )
    )


def _unpack_binding(value: bytes) -> inherited.BindingWitness:
    if len(value) != 3 or value[0] & 0x80 or value[2] & 0xFC:
        raise TelemetryError("P3.17 compact binding reserved bits differ")
    binding = inherited.BindingWitness(
        loader_state=value[0] & 0x03,
        pre_exact_parent_present=(value[0] >> 2) & 0x01,
        pre_exact_parent_driver_state=(value[0] >> 3) & 0x03,
        pre_matching_unbound_parent_count=value[1] & 0x03,
        pre_wrong_address_compatible_parent_count=(value[1] >> 2) & 0x03,
        post_exact_parent_driver_state=(value[0] >> 5) & 0x03,
        post_diagnostic_bound_parent_count=(value[1] >> 4) & 0x03,
        post_exact_adapter_muic_0x25_client_count=(value[1] >> 6) & 0x03,
        post_foreign_0x25_client_count=value[2] & 0x03,
    )
    if any(item == 3 for item in binding.values()[3:5] + binding.values()[6:]):
        raise TelemetryError("P3.17 compact count class is reserved")
    inherited._validate_binding(binding)  # noqa: SLF001
    return binding


def _validate_exec(exec_witness: ExecWitness) -> None:
    values = exec_witness.values()
    if any(type(value) is not int or not 0 <= value <= 0xFF for value in values):
        raise TelemetryError("P3.17 execution witness byte differs")
    policy_state = exec_witness.policy & POLICY_STATE_MASK
    waiting = exec_witness.link_waiting & WAITING_MASK
    supplier = (exec_witness.link_waiting & SUPPLIER_MASK) >> SUPPLIER_SHIFT
    if (
        exec_witness.policy & 0x70
        or policy_state not in POLICY_STATE_NAMES
        or exec_witness.pre_present & 0x08
        or exec_witness.pre_bound & 0x88
        or exec_witness.post_present & 0x08
        or exec_witness.post_bound & 0x88
        or exec_witness.link_waiting & 0x70
        or waiting not in WAITING_STATE_NAMES
        or supplier not in SUPPLIER_STATE_NAMES
    ):
        raise TelemetryError("P3.17 execution witness reserved state differs")


def _provider_ready(present: int, bound: int) -> bool:
    return (
        bool(present & PROVIDER_VALID)
        and present & PROVIDER_MASK == PROVIDER_MASK
        and (present >> PROVIDER_DUPLICATE_SHIFT) & PROVIDER_MASK == 0
        and bound & PROVIDER_MASK == PROVIDER_MASK
        and (bound >> PROVIDER_DUPLICATE_SHIFT) & PROVIDER_MASK == 0
    )


def exec_causal_ready(exec_witness: ExecWitness) -> bool:
    _validate_exec(exec_witness)
    waiting = exec_witness.link_waiting & WAITING_MASK
    supplier = (exec_witness.link_waiting & SUPPLIER_MASK) >> SUPPLIER_SHIFT
    return (
        bool(exec_witness.policy & POLICY_VALID)
        and exec_witness.policy & POLICY_STATE_MASK
        == POLICY_STATES["DEFAULT_ON_STRICT"]
        and bool(exec_witness.policy & POLICY_GADGET_READY)
        and _provider_ready(exec_witness.pre_present, exec_witness.pre_bound)
        and _provider_ready(exec_witness.post_present, exec_witness.post_bound)
        and bool(exec_witness.link_waiting & LINK_VALID)
        and waiting == WAITING_STATES["ZERO"]
        and supplier in {
            SUPPLIER_STATES["LINK_ABSENT"],
            SUPPLIER_STATES["EXACT_ONE"],
        }
    )


def _terminal_witness_consistent(key: str, exec_witness: ExecWitness) -> bool:
    _validate_exec(exec_witness)
    state = exec_witness.policy & POLICY_STATE_MASK
    waiting = exec_witness.link_waiting & WAITING_MASK
    supplier = (exec_witness.link_waiting & SUPPLIER_MASK) >> SUPPLIER_SHIFT
    if key == "fw_devlink_policy_precondition":
        return bool(exec_witness.policy & POLICY_VALID) and state != POLICY_STATES[
            "DEFAULT_ON_STRICT"
        ]
    if key == "provider_preclient_precondition":
        return bool(exec_witness.pre_present & PROVIDER_VALID) and not _provider_ready(
            exec_witness.pre_present, exec_witness.pre_bound
        )
    if key == "provider_postclient_precondition":
        return (
            _provider_ready(exec_witness.pre_present, exec_witness.pre_bound)
            and bool(exec_witness.post_present & PROVIDER_VALID)
            and not _provider_ready(exec_witness.post_present, exec_witness.post_bound)
        )
    if key == "supplier_link_precondition":
        return bool(exec_witness.link_waiting & LINK_VALID) and supplier not in {
            SUPPLIER_STATES["LINK_ABSENT"],
            SUPPLIER_STATES["EXACT_ONE"],
        }
    if key == "waiting_for_supplier_precondition":
        return bool(exec_witness.link_waiting & LINK_VALID) and waiting != WAITING_STATES[
            "ZERO"
        ]
    return True


def terminal_detail(*, terminal_bucket: str | None, mux_class: str | None) -> int:
    if (terminal_bucket is None) == (mux_class is None):
        raise TelemetryError("exactly one P3.17 terminal semantic is required")
    if terminal_bucket is not None:
        try:
            return TERMINAL_DETAIL_BY_KEY[terminal_bucket]
        except KeyError as exc:
            raise TelemetryError("P3.17 terminal bucket is undeclared") from exc
    try:
        return MUX_DETAIL_BY_NAME[str(mux_class)]
    except KeyError as exc:
        raise TelemetryError("P3.17 MUX class is undeclared") from exc


def encode_envelope(
    *,
    binding: inherited.BindingWitness,
    exec_witness: ExecWitness,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: inherited.DiagnosticResult | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> bytes:
    packed_binding = _pack_binding(binding)
    _validate_exec(exec_witness)
    terminal_detail(terminal_bucket=terminal_bucket, mux_class=mux_class)
    terminal_code = 0 if terminal_bucket is None else TERMINAL_CODE_BY_KEY[
        terminal_bucket
    ]
    mux_code = 0 if mux_class is None else MUX_CODE_BY_NAME[mux_class]
    if (observer_site is None) != (observer_error_class is None):
        raise TelemetryError("P3.17 observer tag is incomplete")
    site_code = 0
    error_code = 0
    if observer_site is not None:
        try:
            site_code = OBSERVER_SITES[observer_site]
            error_code = OBSERVER_ERROR_CLASSES[str(observer_error_class)]
        except KeyError as exc:
            raise TelemetryError("P3.17 observer tag is undeclared") from exc
        if (
            site_code == 0
            or error_code == 0
            or terminal_bucket != "synchronous_probe_or_publication_contradiction"
            or result is not None
        ):
            raise TelemetryError("P3.17 observer tag lacks contradiction semantics")
    if terminal_code >= 10 and (
        result is not None
        or observer_site is not None
        or not _terminal_witness_consistent(str(terminal_bucket), exec_witness)
    ):
        raise TelemetryError("P3.17 precondition terminal and witness disagree")
    flags = FLAG_BINDING_PRESENT | FLAG_EXEC_PRESENT
    raw_poll = b""
    summary: inherited.PollSummary | None = None
    if result is not None:
        raw_poll = inherited._validate_result(result)  # noqa: SLF001
        summary = inherited.summarize_poll_vectors(result.poll_bytes)
        flags |= FLAG_RESULT_PRESENT
        expected_terminal, expected_mux = inherited.classify_diagnostic_result(
            binding, result
        )
        if (terminal_bucket, mux_class) != (expected_terminal, expected_mux):
            raise TelemetryError("P3.17 diagnostic semantic differs")
    elif mux_class is not None:
        raise TelemetryError("P3.17 MUX row lacks a result")
    if mux_class is not None and (
        not inherited._binding_causal_ready(binding)  # noqa: SLF001
        or not exec_causal_ready(exec_witness)
    ):
        raise TelemetryError("P3.17 MUX row lacks causal executability")

    encoded_poll = inherited.packbits_encode(raw_poll)
    encoding = inherited.POLL_ENCODING_PACKBITS
    payload = encoded_poll
    if len(encoded_poll) > PAYLOAD_AREA_SIZE:
        terminal_bucket = "result_payload_unrepresentable"
        terminal_code = TERMINAL_CODE_BY_KEY[terminal_bucket]
        mux_code = 0
        flags |= FLAG_POLL_OVERFLOW
        flags &= ~FLAG_POLL_LOSSLESS
        if summary is None:
            raise TelemetryError("P3.17 overflow lacks summary")
        encoding = inherited.POLL_ENCODING_SHA256_SUMMARY
        payload = summary.payload()
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
    envelope[34:37] = packed_binding
    envelope[37:43] = bytes(exec_witness.values())
    envelope[43] = encoding
    struct.pack_into("<H", envelope, 44, len(raw_poll))
    envelope[46] = len(payload)
    envelope[47] = (site_code << 4) | error_code
    envelope[PAYLOAD_AREA_OFFSET : PAYLOAD_AREA_OFFSET + len(payload)] = payload
    crc = binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF
    struct.pack_into("<I", envelope, CRC_OFFSET, crc)
    return bytes(envelope)


def _exec_authority(
    *, observer_site: str | None, terminal_bucket: str | None
) -> frozenset[str]:
    if observer_site is not None:
        by_site = {
            "override-prepare": (),
            "provider-pre": (),
            "cmdline": ("gadget", "pre"),
            "substrate-verify": ("policy", "gadget", "pre"),
            "pre-topology": ("policy", "gadget", "pre"),
            "provider-post": ("policy", "gadget", "pre"),
            "waiting": ("policy", "gadget", "pre", "post"),
            "supplier": ("policy", "gadget", "pre", "post", "waiting"),
            "late-loader": (
                "policy", "gadget", "pre", "post", "waiting", "supplier"
            ),
            "post-topology": (
                "policy", "gadget", "pre", "post", "waiting", "supplier"
            ),
            "result-policy": (
                "policy", "gadget", "pre", "post", "waiting", "supplier"
            ),
            "result-read": (
                "policy", "gadget", "pre", "post", "waiting", "supplier"
            ),
        }
        return frozenset(by_site[observer_site])
    if terminal_bucket == "provider_preclient_precondition":
        return frozenset({"pre"})
    if terminal_bucket == "fw_devlink_policy_precondition":
        return frozenset({"policy", "gadget", "pre"})
    if terminal_bucket == "provider_postclient_precondition":
        return frozenset({"policy", "gadget", "pre", "post"})
    if terminal_bucket in {
        "supplier_link_precondition",
        "waiting_for_supplier_precondition",
    }:
        return frozenset(
            {"policy", "gadget", "pre", "post", "waiting", "supplier"}
        )
    if terminal_bucket == "executability_witness_contradiction":
        return frozenset({"policy", "gadget", "pre"})
    return frozenset(
        {"policy", "gadget", "pre", "post", "waiting", "supplier"}
    )


def _exec_dict(
    exec_witness: ExecWitness,
    *,
    observer_site: str | None,
    terminal_bucket: str | None,
) -> tuple[dict[str, Any], dict[str, bool]]:
    pre_present = exec_witness.pre_present & PROVIDER_MASK
    pre_bound = exec_witness.pre_bound & PROVIDER_MASK
    post_present = exec_witness.post_present & PROVIDER_MASK
    post_bound = exec_witness.post_bound & PROVIDER_MASK
    groups = _exec_authority(
        observer_site=observer_site, terminal_bucket=terminal_bucket
    )
    raw_authority = {
        "policy": bool(exec_witness.policy & POLICY_VALID),
        "gadget": True,
        "pre": bool(exec_witness.pre_present & PROVIDER_VALID),
        "post": bool(exec_witness.post_present & PROVIDER_VALID),
        "waiting": bool(exec_witness.link_waiting & LINK_VALID)
        or "waiting" in groups,
        "supplier": bool(exec_witness.link_waiting & LINK_VALID),
    }
    authority = {
        name: name in groups and raw_authority[name]
        for name in ("policy", "gadget", "pre", "post", "waiting", "supplier")
    }
    value = {
        "policy_state": (
            POLICY_STATE_NAMES[exec_witness.policy & POLICY_STATE_MASK]
            if authority["policy"] else None
        ),
        "gadget_path_ready": (
            bool(exec_witness.policy & POLICY_GADGET_READY)
            if authority["gadget"] else None
        ),
        "pre_present_mask": pre_present if authority["pre"] else None,
        "pre_bound_mask": pre_bound if authority["pre"] else None,
        "pre_duplicate_mask": ((
            exec_witness.pre_present >> PROVIDER_DUPLICATE_SHIFT
        ) & PROVIDER_MASK) if authority["pre"] else None,
        "pre_wrong_driver_mask": ((
            exec_witness.pre_bound >> PROVIDER_DUPLICATE_SHIFT
        ) & PROVIDER_MASK) if authority["pre"] else None,
        "post_present_mask": post_present if authority["post"] else None,
        "post_bound_mask": post_bound if authority["post"] else None,
        "post_duplicate_mask": ((
            exec_witness.post_present >> PROVIDER_DUPLICATE_SHIFT
        ) & PROVIDER_MASK) if authority["post"] else None,
        "post_wrong_driver_mask": ((
            exec_witness.post_bound >> PROVIDER_DUPLICATE_SHIFT
        ) & PROVIDER_MASK) if authority["post"] else None,
        "waiting_for_supplier": (
            WAITING_STATE_NAMES[exec_witness.link_waiting & WAITING_MASK]
            if authority["waiting"] else None
        ),
        "supplier_identity": (
            SUPPLIER_STATE_NAMES[
                (exec_witness.link_waiting & SUPPLIER_MASK) >> SUPPLIER_SHIFT
            ] if authority["supplier"] else None
        ),
        "provider_order": ("spmi-controller", "pmic-mfd", "pm8350c-gpio"),
        "causal_ready": all(authority.values()) and exec_causal_ready(exec_witness),
    }
    return value, authority


def decode_envelope(envelope: bytes) -> dict[str, Any]:
    if len(envelope) != ENVELOPE_SIZE or envelope[:4] != ENVELOPE_MAGIC:
        raise TelemetryError("P3.17 envelope identity differs")
    if envelope[4] != ENVELOPE_VERSION:
        raise TelemetryError("P3.17 envelope version differs")
    recorded = struct.unpack_from("<I", envelope, CRC_OFFSET)[0]
    expected = binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF
    if recorded != expected:
        raise TelemetryError("P3.17 envelope CRC differs")
    terminal_code, mux_code, flags = envelope[5], envelope[6], envelope[7]
    if (
        flags & ~FLAG_MASK
        or not flags & FLAG_BINDING_PRESENT
        or not flags & FLAG_EXEC_PRESENT
        or (terminal_code == 0) == (mux_code == 0)
    ):
        raise TelemetryError("P3.17 envelope flags or semantics differ")
    terminal_bucket = TERMINAL_KEY_BY_CODE.get(terminal_code)
    mux_class = MUX_NAME_BY_CODE.get(mux_code)
    if terminal_code and terminal_bucket is None:
        raise TelemetryError("P3.17 terminal code is undeclared")
    if mux_code and mux_class is None:
        raise TelemetryError("P3.17 MUX code is undeclared")
    observer_tag = envelope[47]
    observer_site_code = observer_tag >> 4
    observer_error_code = observer_tag & 0x0F
    observer_site = OBSERVER_SITE_NAMES.get(observer_site_code)
    observer_error = OBSERVER_ERROR_CLASS_NAMES.get(observer_error_code)
    if (
        observer_site is None
        or observer_error is None
        or ((observer_site_code == 0) != (observer_error_code == 0))
    ):
        raise TelemetryError("P3.17 observer tag differs")
    result_present = bool(flags & FLAG_RESULT_PRESENT)
    if not result_present and any(envelope[8:34]):
        raise TelemetryError("P3.17 result-absent row carries result bytes")
    if observer_site_code != 0 and (
        result_present
        or terminal_bucket != "synchronous_probe_or_publication_contradiction"
    ):
        raise TelemetryError("P3.17 observer tag lacks contradiction semantics")

    binding = _unpack_binding(envelope[34:37])
    exec_witness = ExecWitness(*tuple(envelope[37:43]))
    _validate_exec(exec_witness)
    if terminal_code >= 10 and not _terminal_witness_consistent(
        str(terminal_bucket), exec_witness
    ):
        raise TelemetryError("P3.17 terminal and execution witness disagree")
    raw_size = struct.unpack_from("<H", envelope, 44)[0]
    counts = tuple(envelope[30:34])
    if sum(counts) != raw_size:
        raise TelemetryError("P3.17 poll counts differ")
    encoded_size = envelope[46]
    if encoded_size > PAYLOAD_AREA_SIZE or any(
        envelope[PAYLOAD_AREA_OFFSET + encoded_size : CRC_OFFSET]
    ):
        raise TelemetryError("P3.17 payload extent differs")
    encoded = envelope[PAYLOAD_AREA_OFFSET : PAYLOAD_AREA_OFFSET + encoded_size]
    encoding = envelope[43]
    poll_vectors: tuple[bytes, bytes, bytes, bytes] | None = None
    poll_summary: inherited.PollSummary | None = None
    if flags & FLAG_POLL_OVERFLOW:
        if (
            terminal_bucket != "result_payload_unrepresentable"
            or mux_code != 0
            or not result_present
            or flags & FLAG_POLL_LOSSLESS
            or encoding != inherited.POLL_ENCODING_SHA256_SUMMARY
            or encoded_size != inherited.POLL_SUMMARY_SIZE
        ):
            raise TelemetryError("P3.17 overflow row is not fail-closed")
        poll_summary = inherited.PollSummary(
            sha256=encoded[:32],
            or_mask=tuple(encoded[32:36]),
            poll0=tuple(encoded[36:40]),
            nonzero_count=tuple(encoded[40:44]),
        )
    else:
        if not flags & FLAG_POLL_LOSSLESS or encoding != inherited.POLL_ENCODING_PACKBITS:
            raise TelemetryError("P3.17 causal poll payload is not lossless")
        raw = inherited.packbits_decode(encoded, expected_size=raw_size)
        parts: list[bytes] = []
        cursor = 0
        for count in counts:
            parts.append(raw[cursor : cursor + count])
            cursor += count
        poll_vectors = tuple(parts)  # type: ignore[assignment]
        poll_summary = inherited.summarize_poll_vectors(poll_vectors)

    result: dict[str, Any] | None = None
    if result_present:
        if poll_summary is None:
            raise TelemetryError("P3.17 result lacks poll authority")
        fixed = inherited.DiagnosticResult(
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
            inherited._validate_result_fixed(fixed)  # noqa: SLF001
            inherited._validate_poll_summary(  # noqa: SLF001
                poll_summary,
                counts=counts,
                command_issued_mask=fixed.command_issued_mask,
                response_seen_mask=fixed.response_seen_mask,
                stage=fixed.stage,
                rc=fixed.rc,
            )
        else:
            inherited._validate_result(fixed)  # noqa: SLF001
        expected_terminal, expected_mux = inherited.classify_diagnostic_result(
            binding, fixed
        )
        if flags & FLAG_POLL_OVERFLOW:
            if expected_mux is None:
                raise TelemetryError("P3.17 overflow does not wrap MUX result")
        elif (terminal_bucket, mux_class) != (expected_terminal, expected_mux):
            raise TelemetryError("P3.17 result and semantic disagree")
        result = {
            "stage": fixed.stage,
            "rc": fixed.rc,
            "pmic_valid_mask": fixed.pmic_valid_mask,
            "pmic_id": fixed.pmic_id,
            "pmic_rev": fixed.pmic_rev,
            "initial_uic_valid": fixed.initial_uic_valid,
            "initial_uic": fixed.initial_uic,
            "command_issued_mask": fixed.command_issued_mask,
            "response_seen_mask": fixed.response_seen_mask,
            "write_attempted": fixed.write_attempted,
            "write_ambiguous": fixed.write_ambiguous,
            "response_opcode": fixed.response_opcode,
            "response_value": fixed.response_value,
            "poll_count": counts,
            "poll_bytes": poll_vectors,
            "poll_sha256": poll_summary.sha256.hex(),
            "poll_or": poll_summary.or_mask,
            "poll0": poll_summary.poll0,
            "poll_nonzero_count": poll_summary.nonzero_count,
        }
        result["post2_retention"] = inherited._post2_retention_interpretation(  # noqa: SLF001
            result
        )

    binding_names = inherited.surface.DIAG_EAGAIN_BINDING_WITNESS_FIELDS
    encoded_binding = dict(zip(binding_names, binding.values(), strict=True))
    authoritative_binding_fields = set(binding_names)
    if observer_site_code == 0 and terminal_code >= 10:
        authoritative_binding_fields = {"loader_state"}
    elif observer_site_code == 0 and (
        binding.loader_state
        != inherited.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]
    ):
        authoritative_binding_fields = set(binding_names[:5])
    elif observer_site_code != 0:
        authoritative_binding_fields = {"loader_state"}
        if observer_site in {
            "late-loader", "post-topology", "result-policy", "result-read"
        }:
            authoritative_binding_fields.update(binding_names[:5])
        if observer_site in {"result-policy", "result-read"}:
            authoritative_binding_fields.update(binding_names)
    causal = (
        mux_class is not None
        and not bool(flags & FLAG_POLL_OVERFLOW)
        and inherited._binding_causal_ready(binding)  # noqa: SLF001
        and exec_causal_ready(exec_witness)
    )
    if mux_class is not None and not (
        inherited._binding_causal_ready(binding)  # noqa: SLF001
        and exec_causal_ready(exec_witness)
    ):
        raise TelemetryError("P3.17 MUX row lacks exact causal authority")
    exec_value, exec_authority = _exec_dict(
        exec_witness,
        observer_site=None if observer_site_code == 0 else observer_site,
        terminal_bucket=terminal_bucket,
    )
    decoded = {
        "schema": SCHEMA,
        "terminal_bucket": terminal_bucket,
        "terminal_classification": (
            None if terminal_bucket is None else TERMINAL_CLASSIFICATIONS[terminal_bucket]
        ),
        "mux_class": mux_class,
        "binding": {
            name: value if name in authoritative_binding_fields else None
            for name, value in encoded_binding.items()
        },
        "binding_encoded": encoded_binding,
        "binding_authority": {
            name: name in authoritative_binding_fields for name in binding_names
        },
        "binding_count_semantics": "0_1_many",
        "executability": exec_value,
        "executability_authority": exec_authority,
        "executability_encoded": {
            name: value
            for name, value in zip(
                (
                    "policy", "pre_present", "pre_bound", "post_present",
                    "post_bound", "link_waiting",
                ),
                exec_witness.values(),
                strict=True,
            )
        },
        "result": result,
        "poll_raw_size": raw_size,
        "poll_encoded_size": encoded_size,
        "poll_encoding": encoding,
        "poll_lossless": bool(flags & FLAG_POLL_LOSSLESS),
        "payload_overflow": bool(flags & FLAG_POLL_OVERFLOW),
        "causal_result_allowed": causal,
        "observer_site": None if observer_site_code == 0 else observer_site,
        "observer_error_class": None if observer_error_code == 0 else observer_error,
        "diagnostic_probe_entry": None if result is None else result["stage"] >= 1,
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
        decoded["eagain_row"] = None
    elif result is None and terminal_bucket in eagain_buckets:
        if (
            terminal_bucket
            == "synchronous_probe_or_publication_contradiction"
            and binding.loader_state == inherited.LOADER_STATES["NOT_STARTED"]
        ):
            decoded["eagain_row"] = None
        else:
            row = inherited.classify_eagain_binding(binding)
            if inherited.eagain_terminal_bucket(row) != terminal_bucket:
                raise TelemetryError("P3.17 EAGAIN row and terminal bucket disagree")
            row_contract = inherited.surface.DIAG_EAGAIN_OBSERVABLE_ROWS[row]
            decoded["eagain_row"] = row
            decoded["eagain_terminal"] = bool(row_contract.get("terminal", True))
            decoded["eagain_next_action"] = (
                row_contract.get("investigation_scope")
                or row_contract.get("bounded_continuation")
                or row
            )
    return decoded


def expected_b_detail(decoded: dict[str, Any]) -> int:
    return terminal_detail(
        terminal_bucket=decoded.get("terminal_bucket"),
        mux_class=decoded.get("mux_class"),
    )


def encode_carrier_record(envelope: bytes, *, run_id: bytes) -> bytes:
    decoded = decode_envelope(envelope)
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
            payload=envelope[:SLOT_PAYLOAD_SIZE],
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
            payload=envelope[SLOT_PAYLOAD_SIZE:],
            version=inherited.carrier.REQUEST_VERSION_V3,
        ),
    )


def decode_carrier_record(record: bytes, *, run_id: bytes) -> dict[str, Any]:
    decoded = inherited.carrier.decode_record(
        record,
        expected_profile=inherited.fixed_spec.PROFILE,
        expected_run_id=run_id,
    )
    slots = {slot["generation"]: slot for slot in decoded["valid_slots"]}
    first_generation = inherited.fixed_spec.ATTR_ORDINAL + 1
    second_generation = inherited.fixed_spec.SUMMARY_ORDINAL + 1
    if set(slots) != {first_generation, second_generation}:
        raise TelemetryError("P3.17 carrier pair differs")
    first = slots[first_generation]
    second = slots[second_generation]
    if (
        first["outcome"] != inherited.carrier.OUTCOME_PROGRESS
        or first["detail"] != inherited.A_DETAIL
        or len(first["payload"]) != SLOT_PAYLOAD_SIZE
        or second["outcome"] != inherited.carrier.OUTCOME_FAILURE
        or len(second["payload"]) != SLOT_PAYLOAD_SIZE
    ):
        raise TelemetryError("P3.17 carrier shape differs")
    result = decode_envelope(first["payload"] + second["payload"])
    if second["detail"] != expected_b_detail(result):
        raise TelemetryError("P3.17 carrier detail and envelope disagree")
    return {
        **result,
        "carrier_family": inherited.carrier.LONG_FAMILY.decode("ascii"),
        "record_count": 1,
        "slot_payload_sizes": [SLOT_PAYLOAD_SIZE, SLOT_PAYLOAD_SIZE],
        "a_detail": first["detail"],
        "b_detail": second["detail"],
        "adjacent_terminal_pair": True,
    }


def validate() -> dict[str, Any]:
    if (
        ENVELOPE_SIZE != 128
        or PAYLOAD_AREA_SIZE != 76
        or len(TERMINAL_BUCKET_KEYS) != 15
        or len(inherited.surface.DIAG_EAGAIN_OBSERVABLE_ROWS) != 6
        or max(TERMINAL_DETAIL_BY_KEY.values()) != 0x670F
        or min(inherited.MUX_DETAIL_BY_NAME.values()) != 0x6710
    ):
        raise TelemetryError("P3.17 telemetry geometry differs")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "envelope_version": ENVELOPE_VERSION,
        "envelope_size": ENVELOPE_SIZE,
        "poll_payload_capacity": PAYLOAD_AREA_SIZE,
        "binding_bytes": 3,
        "executability_bytes": 6,
        "terminal_bucket_count": len(TERMINAL_BUCKET_KEYS),
        "observable_eagain_row_count": len(
            inherited.surface.DIAG_EAGAIN_OBSERVABLE_ROWS
        ),
        "mux_device_class_count": len(MUX_DEVICE_CLASSES),
        "full_lto_required": False,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
