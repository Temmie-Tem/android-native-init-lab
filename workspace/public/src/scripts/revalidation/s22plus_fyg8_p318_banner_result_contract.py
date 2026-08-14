#!/usr/bin/env python3
"""Freeze the P3.17 banner blind spot and the P3.18 successor contract.

P3.17 publishes its retained terminal before calling p260_write_banner() and
discards the return value.  No after-the-fact stage can repair that ordering.
This host-only contract requires a future candidate to perform one bounded
attempt first, retain its outcome and byte count in a new envelope version,
and publish the terminal even when banner delivery fails.  Envelope-v4 also
retains five same-clock timing samples and the first actual host-caused USB
event without pretending that gadget readiness is a host/time-axis anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p318_envelope_v4_design_contract_v2"
VERDICT = (
    "PASS_P318_ENVELOPE_V4_TIMING_BANNER_BUDGET_DESIGN_H0_"
    "IMPLEMENTATION_REQUIRED"
)
DEFAULT_MATERIALIZED = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/intent/materialized-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)
DEFAULT_P260_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
DEFAULT_P317_ENVELOPE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p317_max77705_envelope.inc.c"
)
DEFAULT_BASE_ENVELOPE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_max77705_envelope.inc.c"
)
DEFAULT_DWC3_CORE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/core.h"
)
DEFAULT_DWC3_GADGET = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/gadget.c"
)
DEFAULT_DWC3_EP0 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/ep0.c"
)

OUTCOMES = ("written", "eagain_timeout", "errno", "partial")
HOST_EVENT_KINDS = ("none", "reset", "connect_done", "setup")
TIMING_SAMPLES = ("pre", "write", "post1", "post2", "first_host_event")

ENVELOPE_SIZE = 128
METADATA_SIZE = 48
CRC_SIZE = 4
PAYLOAD_SIZE = 76
TIMING_VALID_MASK_SIZE = 1
HOST_EVENT_KIND_SIZE = 1
TIMING_DELTA_COUNT = 4
TIMING_DELTA_SIZE = 4
TIMING_PREFIX_SIZE = 18
BANNER_PREFIX_SIZE = 3
V4_PREFIX_SIZE = 21
LOSSLESS_POLL_CAPACITY = 55
OVERFLOW_SUMMARY_SIZE = 44
OVERFLOW_TOTAL_SIZE = 65
OVERFLOW_SPARE_SIZE = 11
SIGNED_DELTA_US_MIN = -(2**31)
SIGNED_DELTA_US_MAX = 2**31 - 1
PROCESS_V2_GUARD_SECONDS = 1200
PREIMAGE_OBLIGATIONS = (
    {"outcome": "written", "bytes_written": 49, "error_class": "none"},
    {"outcome": "eagain_timeout", "bytes_written": 0, "error_class": "timeout"},
    {"outcome": "errno", "bytes_written": 0, "error_class": "normalized_errno"},
    {"outcome": "partial", "bytes_written": 1, "error_class": "normalized_cause"},
    {"outcome": "partial", "bytes_written": 48, "error_class": "normalized_cause"},
)


class BannerContractError(ValueError):
    pass


def validate_v4_budget(
    *,
    envelope_size: int = ENVELOPE_SIZE,
    metadata_size: int = METADATA_SIZE,
    crc_size: int = CRC_SIZE,
    payload_size: int = PAYLOAD_SIZE,
    timing_prefix_size: int = TIMING_PREFIX_SIZE,
    banner_prefix_size: int = BANNER_PREFIX_SIZE,
    overflow_summary_size: int = OVERFLOW_SUMMARY_SIZE,
) -> dict[str, int]:
    derived_payload = envelope_size - metadata_size - crc_size
    expected_timing = (
        TIMING_VALID_MASK_SIZE
        + HOST_EVENT_KIND_SIZE
        + TIMING_DELTA_COUNT * TIMING_DELTA_SIZE
    )
    if envelope_size != 128 or derived_payload != payload_size or payload_size != 76:
        raise BannerContractError("Envelope-v4 fixed Carrier geometry differs")
    if timing_prefix_size != expected_timing or timing_prefix_size != 18:
        raise BannerContractError("Envelope-v4 timing prefix geometry differs")
    if banner_prefix_size != 3:
        raise BannerContractError("Envelope-v4 banner prefix geometry differs")
    prefix_size = timing_prefix_size + banner_prefix_size
    lossless_capacity = payload_size - prefix_size
    overflow_total = prefix_size + overflow_summary_size
    overflow_spare = payload_size - overflow_total
    if (
        prefix_size != 21
        or lossless_capacity != 55
        or overflow_summary_size != 44
        or overflow_total != 65
        or overflow_spare != 11
    ):
        raise BannerContractError("Envelope-v4 timing/poll budget differs")
    guard_us = PROCESS_V2_GUARD_SECONDS * 1_000_000
    if SIGNED_DELTA_US_MAX < guard_us or SIGNED_DELTA_US_MIN > -guard_us:
        raise BannerContractError("Envelope-v4 signed delta cannot span guard")
    return {
        "envelope_size": envelope_size,
        "metadata_size": metadata_size,
        "payload_size": payload_size,
        "crc_size": crc_size,
        "timing_prefix_size": timing_prefix_size,
        "banner_prefix_size": banner_prefix_size,
        "v4_prefix_size": prefix_size,
        "lossless_poll_capacity": lossless_capacity,
        "overflow_summary_size": overflow_summary_size,
        "overflow_total_size": overflow_total,
        "overflow_spare_size": overflow_spare,
        "signed_delta_us_min": SIGNED_DELTA_US_MIN,
        "signed_delta_us_max": SIGNED_DELTA_US_MAX,
        "process_v2_guard_us": guard_us,
    }


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise BannerContractError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise BannerContractError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise BannerContractError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise BannerContractError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _text(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise BannerContractError(f"{label} is not UTF-8") from exc


def _function(text: str, signature: str) -> str:
    starts: list[int] = []
    cursor = 0
    while True:
        found = text.find(signature, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + len(signature)
    if len(starts) != 1:
        raise BannerContractError(
            f"expected one function signature {signature!r}, found {len(starts)}"
        )
    opening = text.find("{", starts[0] + len(signature))
    if opening < 0:
        raise BannerContractError(f"function has no body: {signature}")
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[starts[0] : index + 1]
    raise BannerContractError(f"unterminated function: {signature}")


def _require_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if text.count(token) != 1]
    if missing:
        raise BannerContractError(f"{label} source seam differs: {missing}")


def audit_current_sources(
    materialized_data: bytes,
    p260_data: bytes,
    envelope_data: bytes,
    base_envelope_data: bytes,
) -> dict[str, Any]:
    materialized = _text(materialized_data, "P3.17 materialized runtime")
    p260 = _text(p260_data, "P2.60 banner helper")
    envelope = _text(envelope_data, "P3.17 envelope")
    base_envelope = _text(base_envelope_data, "Max77705 base envelope")
    publish = _function(
        materialized,
        "static __attribute__((noreturn)) void p317_publish(",
    )
    run = _function(
        materialized,
        "static __attribute__((noreturn)) void p317_run(void)",
    )
    entry = _function(
        materialized,
        "static __attribute__((noreturn)) void p290_e3_run(void)",
    )
    terminal = "s22_max77705_checkpoint_payload_terminal_position("
    banner = "if (tty_fd >= 0) (void)p260_write_banner(tty_fd);"
    park = "p290_park_after_confirmed_publication();"
    _require_tokens(publish, "P3.17 active publisher", (terminal, banner, park))
    if not publish.find(terminal) < publish.find(banner) < publish.find(park):
        raise BannerContractError("P3.17 publish/banner/park order differs")
    if run.count("p317_publish(tty_fd, &observation);") != 1:
        raise BannerContractError("P3.17 success publisher call differs")
    if entry.count("p317_run();") != 1:
        raise BannerContractError("P3.17 materialized entrypoint differs")
    if materialized.count("(void)p260_write_banner(tty_fd);") != 3:
        raise BannerContractError("materialized discarded banner callers drifted")
    write_all = _function(p260, "static long p260_write_all(")
    _require_tokens(
        write_all,
        "P2.60 write helper",
        (
            "if (rc == -P260_EINTR)",
            "if (rc == -EAGAIN && retry_eagain)",
            "return -ETIMEDOUT;",
            "if (rc <= 0 || (size_t)rc > size - written)",
            "written += (size_t)rc;",
        ),
    )
    _require_tokens(
        envelope,
        "P3.17 envelope identity",
        (
            "#define S22PLUS_MAX77705_P317_ENVELOPE_VERSION 3U",
            "memset(envelope, 0, S22PLUS_MAX77705_ENVELOPE_SIZE);",
            "envelope[4] = S22PLUS_MAX77705_P317_ENVELOPE_VERSION;",
        ),
    )
    _require_tokens(
        base_envelope,
        "Max77705 fixed envelope geometry",
        (
            "#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U",
            "#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U",
            "#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U",
            "#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE 76U",
            "#define S22PLUS_MAX77705_ENVELOPE_OVERFLOW_SIZE 44U",
        ),
    )
    return {
        "active_entrypoint": "p290_e3_run -> p317_run -> p317_publish",
        "terminal_before_banner": True,
        "banner_return_discarded": True,
        "active_banner_attempt_count": 1,
        "materialized_discarded_banner_call_count": 3,
        "terminal_can_retain_banner_result": False,
        "p260_write_all_retries_eintr": True,
        "p260_write_all_bounds_eagain": True,
        "p260_write_all_handles_short_writes": True,
        "p260_write_all_returns_no_byte_count": True,
        "historical_envelope_version": 3,
        "historical_envelope_size": 128,
    }


def audit_host_event_sources(
    core_data: bytes, gadget_data: bytes, ep0_data: bytes
) -> dict[str, Any]:
    core = _text(core_data, "DWC3 core header")
    gadget = _text(gadget_data, "DWC3 gadget source")
    ep0 = _text(ep0_data, "DWC3 EP0 source")
    _require_tokens(
        core,
        "DWC3 host-caused device-event constants",
        (
            "#define DWC3_DEVICE_EVENT_RESET\t\t\t1",
            "#define DWC3_DEVICE_EVENT_CONNECT_DONE\t\t2",
        ),
    )
    interrupt = _function(
        gadget,
        "static void dwc3_gadget_interrupt(struct dwc3 *dwc,",
    )
    _require_tokens(
        interrupt,
        "DWC3 device-event dispatch",
        (
            "case DWC3_DEVICE_EVENT_RESET:",
            "dwc3_gadget_reset_interrupt(dwc);",
            "case DWC3_DEVICE_EVENT_CONNECT_DONE:",
            "dwc3_gadget_conndone_interrupt(dwc);",
        ),
    )
    ep0_interrupt = _function(ep0, "void dwc3_ep0_interrupt(struct dwc3 *dwc,")
    ep0_complete = _function(
        ep0, "static void dwc3_ep0_xfer_complete(struct dwc3 *dwc,"
    )
    _require_tokens(
        ep0_interrupt,
        "DWC3 EP0 completion dispatch",
        (
            "case DWC3_DEPEVT_XFERCOMPLETE:",
            "dwc3_ep0_xfer_complete(dwc, event);",
        ),
    )
    _require_tokens(
        ep0_complete,
        "DWC3 SETUP completion seam",
        (
            "case EP0_SETUP_PHASE:",
            "dwc3_ep0_inspect_setup(dwc, event);",
        ),
    )
    return {
        "reset_dispatch_source_bound": True,
        "connect_done_dispatch_source_bound": True,
        "setup_completion_source_bound": True,
        "gadget_ready_used_as_host_event": False,
    }


def successor_contract() -> dict[str, Any]:
    budget = validate_v4_budget()
    return {
        "status": "DESIGN_ONLY_NOT_IMPLEMENTED",
        "ordering": [
            "gadget_and_observer_evaluability_preconditions",
            "one_bounded_banner_attempt",
            "capture_outcome_error_class_and_bytes_written",
            "encode_new_terminal_envelope",
            "publish_retained_terminal",
            "park_without_second_banner_attempt",
        ],
        "attempt": {
            "count": 1,
            "banner_size": 49,
            "deadline_source": "existing_P260_SHORT_TIMEOUT_SEC",
            "deadline_seconds": 5,
            "terminal_publication_required_for_every_outcome": True,
            "retry_after_terminal_forbidden": True,
        },
        "outcomes": list(OUTCOMES),
        "outcome_rules": {
            "written": "bytes_written == 49 and error_class == none",
            "eagain_timeout": "bytes_written == 0 and final cause is EAGAIN deadline",
            "errno": "bytes_written == 0 and final cause is another normalized errno",
            "partial": (
                "1 <= bytes_written <= 48; normalized cause separately retains "
                "timeout, errno, zero-write, or invalid-short-write"
            ),
        },
        "retained_fields": [
            "banner_outcome",
            "banner_bytes_written",
            "banner_error_class",
            "timing_valid_mask",
            "first_host_event_kind",
            "write_delta_us_from_pre",
            "post1_delta_us_from_pre",
            "post2_delta_us_from_pre",
            "first_host_event_delta_us_from_pre",
        ],
        "schema": {
            "carrier_size": 128,
            "carrier_resize_forbidden": True,
            "envelope_version": 4,
            "new_envelope_version_required": True,
            "v3_reserved_byte_reinterpretation_forbidden": True,
            "registered_terminal_details_required": True,
            "budget": budget,
            "payload_layout": [
                "18_byte_same_clock_timing_prefix",
                "3_byte_banner_result_prefix",
                "packbits_poll_up_to_55_bytes_or_44_byte_overflow_summary",
            ],
        },
        "timing": {
            "samples": list(TIMING_SAMPLES),
            "encoding": (
                "pre_is_zero_origin_plus_four_signed_int32_microsecond_deltas"
            ),
            "clock_domain": "one_kernel_monotonic_clock_domain",
            "cross_clock_synchronization_required": False,
            "first_host_event_kinds": list(HOST_EVENT_KINDS),
            "host_event_latched_once": True,
            "gadget_ready_is_host_event_forbidden": True,
            "absent_host_event_has_validity_bit_zero": True,
            "validity_bits": {
                "bit0": "pre",
                "bit1": "write",
                "bit2": "post1",
                "bit3": "post2",
                "bit4": "first_host_event",
            },
            "allowed_validity_masks": [15, 31],
            "required_device_sample_order": "pre <= write <= post1 < post2",
            "host_event_kind_pairing": (
                "mask_0x0f_requires_none; mask_0x1f_requires_"
                "reset_connect_done_or_setup"
            ),
            "clock_read_failure": (
                "observer_failure_distinct_from_device_result_and_no_causal_claim"
            ),
            "guard_budget": {
                "design_value_seconds": PROCESS_V2_GUARD_SECONDS,
                "signed_delta_max_seconds": SIGNED_DELTA_US_MAX / 1_000_000,
                "design_value_is_execution_authority": False,
                "qualification_must_source_bind_actual_guard": True,
                "actual_guard_must_not_exceed_signed_delta_range": True,
            },
            "event_before_write": (
                "first_host_event_delta_us < write_delta_us; host traffic "
                "preceded the MUX write"
            ),
            "write_before_event": (
                "write_delta_us < first_host_event_delta_us; MUX write "
                "preceded first host traffic but causation is not proven"
            ),
            "equal_or_absent": "ambiguous ordering; no MUX causation claim",
            "implementation_gate": (
                "diagnostic samples and DWC3 RESET/CONNECT_DONE/SETUP latch "
                "must prove the exact same monotonic clock primitive"
            ),
        },
        "poll_evidence": {
            "lossless_encoding": "PackBits",
            "lossless_capacity": budget["lossless_poll_capacity"],
            "overflow_summary_size": budget["overflow_summary_size"],
            "overflow_summary_fields": [
                "sha256_32",
                "or_mask_4",
                "poll0_4",
                "nonzero_count_4",
            ],
            "overflow_causal_result_allowed": False,
            "lossless_boundary_preimages": [55, 56],
        },
        "arming": {
            "real_encoder_carrier_decoder_required": True,
            "positive_preimages": list(PREIMAGE_OBLIGATIONS),
            "all_outcomes_surjective": True,
            "written_bytes_outside_0_to_49_rejected": True,
            "written_outcome_with_non49_count_rejected": True,
            "partial_outcome_with_boundary_count_rejected": True,
            "only_validity_masks_0x0f_and_0x1f_allowed": True,
            "gadget_ready_event_kind_rejected": True,
            "lossless_55_and_overflow_56_preimages_required": True,
            "same_clock_ordering_preimages_required": True,
        },
        "interpretation": {
            "written": "device accepted all 49 bytes into the gadget write path",
            "not_proven_by_written": [
                "host selected or opened the endpoint",
                "host received all 49 bytes",
            ],
            "failed_attempt": (
                "device-side banner delivery failure; retained Max77705 facts "
                "remain independently interpretable"
            ),
        },
    }


def build_contract(
    *,
    materialized_data: bytes,
    p260_data: bytes,
    envelope_data: bytes,
    base_envelope_data: bytes,
    dwc3_core_data: bytes,
    dwc3_gadget_data: bytes,
    dwc3_ep0_data: bytes,
    extractor_data: bytes,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inputs": {
            "p317_materialized_runtime": receipt(materialized_data),
            "p260_banner_helper": receipt(p260_data),
            "p317_envelope": receipt(envelope_data),
            "max77705_base_envelope": receipt(base_envelope_data),
            "dwc3_core_header": receipt(dwc3_core_data),
            "dwc3_gadget_source": receipt(dwc3_gadget_data),
            "dwc3_ep0_source": receipt(dwc3_ep0_data),
            "extractor": receipt(extractor_data),
        },
        "current": audit_current_sources(
            materialized_data, p260_data, envelope_data, base_envelope_data
        ),
        "host_event_source_audit": audit_host_event_sources(
            dwc3_core_data, dwc3_gadget_data, dwc3_ep0_data
        ),
        "successor": successor_contract(),
        "scope": {
            "host_only": True,
            "device_actions": 0,
            "p317_historical_bytes_unchanged": True,
            "p318_candidate_ready": False,
            "live_authority": False,
        },
    }


def encode_contract(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--materialized", type=Path, default=DEFAULT_MATERIALIZED)
    parser.add_argument("--p260-runtime", type=Path, default=DEFAULT_P260_RUNTIME)
    parser.add_argument("--p317-envelope", type=Path, default=DEFAULT_P317_ENVELOPE)
    parser.add_argument("--base-envelope", type=Path, default=DEFAULT_BASE_ENVELOPE)
    parser.add_argument("--dwc3-core", type=Path, default=DEFAULT_DWC3_CORE)
    parser.add_argument("--dwc3-gadget", type=Path, default=DEFAULT_DWC3_GADGET)
    parser.add_argument("--dwc3-ep0", type=Path, default=DEFAULT_DWC3_EP0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    extractor_path = Path(__file__).resolve()
    value = build_contract(
        materialized_data=stable_read(
            resolve(args.materialized), "P3.17 materialized runtime", 2**24
        ),
        p260_data=stable_read(
            resolve(args.p260_runtime), "P2.60 banner helper", 2**20
        ),
        envelope_data=stable_read(
            resolve(args.p317_envelope), "P3.17 envelope", 2**20
        ),
        base_envelope_data=stable_read(
            resolve(args.base_envelope), "Max77705 base envelope", 2**20
        ),
        dwc3_core_data=stable_read(
            resolve(args.dwc3_core), "DWC3 core header", 2**20
        ),
        dwc3_gadget_data=stable_read(
            resolve(args.dwc3_gadget), "DWC3 gadget source", 2**24
        ),
        dwc3_ep0_data=stable_read(
            resolve(args.dwc3_ep0), "DWC3 EP0 source", 2**24
        ),
        extractor_data=stable_read(extractor_path, "banner result contract", 2**20),
    )
    payload = encode_contract(value)
    if args.output is None:
        print(payload.decode(), end="")
    else:
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
