#!/usr/bin/env python3
"""Freeze the P3.17 banner blind spot and the corrected P3.18 design boundary.

P3.17 publishes its retained terminal before calling p260_write_banner() and
discards the return value.  No after-the-fact stage can repair that ordering.
This host-only contract requires a future candidate to perform one bounded
attempt first, retain its outcome and byte count in a new envelope version,
and publish the terminal even when banner delivery fails.  The initial v4
design reserved timing bytes without naming a producer.  This correction
source-binds a module-only producer path through the exported dwc3_event
tracepoint, but deliberately keeps the capability CHANGES_REQUIRED until the
early latch module, late diagnostic consumer, and real encoder are built and
qualified together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p318_envelope_v4_design_contract_v5"
VERDICT = "CHANGES_REQUIRED_P318_HOST_EVENT_PRODUCER_NOT_IMPLEMENTED_H0"
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
DEFAULT_DWC3_TRACE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/trace.c"
)
DEFAULT_DWC3_TRACE_HEADER = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/trace.h"
)
DEFAULT_DWC3_MAKEFILE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/dwc3/Makefile"
)
DEFAULT_TIMEKEEPING_HEADER = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/include/linux/timekeeping.h"
)
DEFAULT_TIMEKEEPING_SOURCE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/kernel/time/timekeeping.c"
)
DEFAULT_KERNEL_CONFIG = Path(
    "workspace/private/outputs/s22plus_fyg8_p310/immutable-a-v6/.config"
)
FIXED_KERNEL_CONFIG_SHA256 = (
    "6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b"
)

OUTCOMES = ("written", "eagain_timeout", "failure", "partial")
HOST_EVENT_KINDS = ("none", "reset", "connect_done", "setup")
TIMING_SAMPLES = (
    "latch_install",
    "gadget_exposure",
    "pre",
    "write",
    "post1",
    "post2",
    "first_host_event",
)

ENVELOPE_SIZE = 128
METADATA_SIZE = 48
CRC_SIZE = 4
PAYLOAD_SIZE = 76
TIMING_VALID_MASK_SIZE = 1
HOST_EVENT_KIND_SIZE = 1
TIMING_DELTA_COUNT = 6
TIMING_DELTA_SIZE = 4
TIMING_PREFIX_SIZE = 26
BANNER_PREFIX_SIZE = 3
V4_PREFIX_SIZE = 29
LOSSLESS_POLL_CAPACITY = 47
OVERFLOW_SUMMARY_SIZE = 44
OVERFLOW_TOTAL_SIZE = 73
OVERFLOW_SPARE_SIZE = 3
SIGNED_DELTA_US_MIN = -(2**31)
SIGNED_DELTA_US_MAX = 2**31 - 1
PROCESS_V2_GUARD_SECONDS = 1200

DWC3_EVENT_TYPE_DEV = 0
DWC3_DEVICE_EVENT_RESET = 1
DWC3_DEVICE_EVENT_CONNECT_DONE = 2
DWC3_DEPEVT_XFERCOMPLETE = 1
EP0_SETUP_PHASE = 1
DWC3_RAW_POSITIVE_PREIMAGES = (
    {"name": "reset-minimal", "raw": 0x00000101, "ep0state": 0, "kind": "reset"},
    {
        "name": "reset-nonzero-event-info",
        "raw": 0x01FF0101,
        "ep0state": 0,
        "kind": "reset",
    },
    {
        "name": "connect-done-minimal",
        "raw": 0x00000201,
        "ep0state": 0,
        "kind": "connect_done",
    },
    {"name": "setup-minimal", "raw": 0x00000040, "ep0state": 1, "kind": "setup"},
    {
        "name": "setup-nonzero-status-parameters",
        "raw": 0xABCD3040,
        "ep0state": 1,
        "kind": "setup",
    },
)
DWC3_RAW_NEGATIVE_PREIMAGES = (
    {"name": "disconnect", "raw": 0x00000001, "ep0state": 0},
    {"name": "carkit-device-specific", "raw": 0x00000007, "ep0state": 0},
    {"name": "i2c-device-specific", "raw": 0x00000009, "ep0state": 0},
    {"name": "ep1-xfercomplete", "raw": 0x00000042, "ep0state": 1},
    {"name": "ep2-xfercomplete", "raw": 0x00000044, "ep0state": 1},
    {"name": "ep0-xfernotready", "raw": 0x000000C0, "ep0state": 1},
    {"name": "ep0-xfercomplete-data-phase", "raw": 0xABCD3040, "ep0state": 2},
)
PREIMAGE_OBLIGATIONS = (
    {"outcome": "written", "bytes_written": 49, "error_class": "none"},
    {
        "outcome": "eagain_timeout",
        "bytes_written": 0,
        "error_class": "eagain_deadline",
    },
    {"outcome": "failure", "bytes_written": 0, "error_class": "epipe"},
    {"outcome": "failure", "bytes_written": 0, "error_class": "enodev"},
    {"outcome": "failure", "bytes_written": 0, "error_class": "etimedout"},
    {"outcome": "failure", "bytes_written": 0, "error_class": "zero_write"},
    {
        "outcome": "failure",
        "bytes_written": 0,
        "error_class": "invalid_short_write",
    },
    {"outcome": "failure", "bytes_written": 0, "error_class": "other_errno"},
    {"outcome": "partial", "bytes_written": 1, "error_class": "epipe"},
    {"outcome": "partial", "bytes_written": 1, "error_class": "zero_write"},
    {
        "outcome": "partial",
        "bytes_written": 48,
        "error_class": "eagain_deadline",
    },
    {
        "outcome": "partial",
        "bytes_written": 48,
        "error_class": "invalid_short_write",
    },
)
ERROR_CLASSES = {
    "none": 0,
    "eagain_deadline": 1,
    "epipe": 2,
    "enodev": 3,
    "etimedout": 4,
    "zero_write": 5,
    "invalid_short_write": 6,
    "other_errno": 7,
}


class BannerContractError(ValueError):
    pass


def classify_banner_terminal(*, bytes_written: int, error_class: str) -> str:
    if not isinstance(bytes_written, int) or not 0 <= bytes_written <= 49:
        raise BannerContractError("banner byte count outside exact domain")
    if error_class not in ERROR_CLASSES:
        raise BannerContractError("banner error class outside exact domain")
    if bytes_written == 49:
        if error_class != "none":
            raise BannerContractError("complete banner has a failure cause")
        return "written"
    if error_class == "none":
        raise BannerContractError("incomplete banner lacks a failure cause")
    if bytes_written == 0:
        return "eagain_timeout" if error_class == "eagain_deadline" else "failure"
    return "partial"


def audit_banner_terminal_domain() -> dict[str, Any]:
    rows = [
        {
            "bytes_written": bytes_written,
            "error_class": error_class,
            "outcome": classify_banner_terminal(
                bytes_written=bytes_written, error_class=error_class
            ),
        }
        for error_class in ERROR_CLASSES
        if error_class != "none"
        for bytes_written in range(49)
    ]
    rows.append(
        {
            "bytes_written": 49,
            "error_class": "none",
            "outcome": classify_banner_terminal(
                bytes_written=49, error_class="none"
            ),
        }
    )
    if len(rows) != 344 or {row["outcome"] for row in rows} != set(OUTCOMES):
        raise BannerContractError("banner terminal domain coverage differs")
    return {
        "valid_terminal_row_count": len(rows),
        "outcome_set": sorted({row["outcome"] for row in rows}),
        "zero_write_at_zero_is_failure": classify_banner_terminal(
            bytes_written=0, error_class="zero_write"
        )
        == "failure",
        "invalid_short_at_zero_is_failure": classify_banner_terminal(
            bytes_written=0, error_class="invalid_short_write"
        )
        == "failure",
        "eagain_at_zero_is_timeout": classify_banner_terminal(
            bytes_written=0, error_class="eagain_deadline"
        )
        == "eagain_timeout",
        "failure_after_progress_is_partial": classify_banner_terminal(
            bytes_written=1, error_class="zero_write"
        )
        == "partial",
    }


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
    if timing_prefix_size != expected_timing or timing_prefix_size != 26:
        raise BannerContractError("Envelope-v4 timing prefix geometry differs")
    if banner_prefix_size != 3:
        raise BannerContractError("Envelope-v4 banner prefix geometry differs")
    prefix_size = timing_prefix_size + banner_prefix_size
    lossless_capacity = payload_size - prefix_size
    overflow_total = prefix_size + overflow_summary_size
    overflow_spare = payload_size - overflow_total
    if (
        prefix_size != 29
        or lossless_capacity != 47
        or overflow_summary_size != 44
        or overflow_total != 73
        or overflow_spare != 3
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


def _braced_block(text: str, signature: str) -> str:
    if text.count(signature) != 1:
        raise BannerContractError(f"expected one braced block {signature!r}")
    start = text.index(signature)
    opening = text.find("{", start)
    if opening < 0:
        raise BannerContractError(f"braced block has no body: {signature}")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise BannerContractError(f"unterminated braced block: {signature}")


def _require_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if text.count(token) != 1]
    if missing:
        raise BannerContractError(f"{label} source seam differs: {missing}")


def _require_ordered_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    ordered = tuple(tokens)
    _require_tokens(text, label, ordered)
    positions = [text.find(token) for token in ordered]
    if positions != sorted(positions):
        raise BannerContractError(f"{label} source field order differs")


def _require_exact_u32_bitfields(
    block: str,
    label: str,
    expected: tuple[tuple[str, int], ...],
) -> None:
    actual = tuple(
        (name, int(width))
        for name, width in re.findall(r"\bu32\s+([A-Za-z0-9_]+):(\d+);", block)
    )
    if actual != expected or sum(width for _, width in actual) != 32:
        raise BannerContractError(f"{label} exact bitfield layout differs")


def decode_dwc3_host_event(raw: int, *, ep0state: int) -> str | None:
    """Decode only the three host-caused anchors from one raw DWC3 word."""

    if not isinstance(raw, int) or not 0 <= raw <= 0xFFFFFFFF:
        raise BannerContractError("DWC3 raw event is outside u32")
    if not isinstance(ep0state, int) or not 0 <= ep0state <= 0xFFFFFFFF:
        raise BannerContractError("DWC3 ep0state is outside u32")
    is_devspec = raw & 0x1
    event_type = (raw >> 1) & 0x7F
    if is_devspec:
        if event_type != DWC3_EVENT_TYPE_DEV:
            return None
        device_event = (raw >> 8) & 0xF
        if device_event == DWC3_DEVICE_EVENT_RESET:
            return "reset"
        if device_event == DWC3_DEVICE_EVENT_CONNECT_DONE:
            return "connect_done"
        return None
    endpoint_number = (raw >> 1) & 0x1F
    endpoint_event = (raw >> 6) & 0xF
    if (
        endpoint_number == 0
        and endpoint_event == DWC3_DEPEVT_XFERCOMPLETE
        and ep0state == EP0_SETUP_PHASE
    ):
        return "setup"
    return None


def audit_dwc3_raw_decoder() -> dict[str, Any]:
    positive = [
        {
            **row,
            "decoded": decode_dwc3_host_event(
                int(row["raw"]), ep0state=int(row["ep0state"])
            ),
        }
        for row in DWC3_RAW_POSITIVE_PREIMAGES
    ]
    negative = [
        {
            **row,
            "decoded": decode_dwc3_host_event(
                int(row["raw"]), ep0state=int(row["ep0state"])
            ),
        }
        for row in DWC3_RAW_NEGATIVE_PREIMAGES
    ]
    if any(row["decoded"] != row["kind"] for row in positive):
        raise BannerContractError("DWC3 positive raw preimage differs")
    if any(row["decoded"] is not None for row in negative):
        raise BannerContractError("DWC3 negative raw preimage differs")
    if (
        decode_dwc3_host_event(0x01FF0101, ep0state=0) != "reset"
        or decode_dwc3_host_event(0xABCD3040, ep0state=1) != "setup"
    ):
        raise BannerContractError("DWC3 decoder compares whole raw words")
    return {
        "decode_rule": {
            "device": (
                "raw.bit0 == 1 and raw.bits1_7 == DWC3_EVENT_TYPE_DEV and "
                "raw.bits8_11 in RESET,CONNECT_DONE"
            ),
            "setup": (
                "raw.bit0 == 0 and raw.bits1_5 == 0 and "
                "raw.bits6_9 == XFERCOMPLETE and ep0state == EP0_SETUP_PHASE"
            ),
        },
        "whole_word_equality_forbidden": True,
        "positive_preimages": positive,
        "negative_preimages": negative,
        "upper_device_event_info_bits_ignored": True,
        "upper_endpoint_status_parameter_bits_ignored": True,
        "non_device_devspec_types_rejected": True,
    }


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
    if (
        write_all.count("p241_timespec_before(&now, &deadline)") != 1
        or write_all.find("if (rc == -P260_EINTR)")
        > write_all.find("if (rc == -EAGAIN && retry_eagain)")
    ):
        raise BannerContractError("P2.60 retry/deadline topology differs")
    banner_array = re.search(r"static char p260_banner\[([0-9]+)\];", p260)
    if (
        banner_array is None
        or int(banner_array.group(1)) - 1 != 49
        or int(banner_array.group(1)) - 1 > 0xFF
        or p260.count("p260_banner, sizeof(p260_banner) - 1U, 1") != 1
    ):
        raise BannerContractError("P2.60 banner length source seam differs")
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
        "p260_write_all_eintr_bypasses_deadline": True,
        "p260_existing_timeout_is_not_an_absolute_attempt_deadline": True,
        "p260_write_all_handles_short_writes": True,
        "p260_write_all_returns_no_byte_count": True,
        "p260_banner_payload_bytes": 49,
        "p260_banner_count_fits_u8": True,
        "historical_envelope_version": 3,
        "historical_envelope_size": 128,
    }


def audit_host_event_sources(
    core_data: bytes,
    gadget_data: bytes,
    ep0_data: bytes,
    trace_data: bytes,
    trace_header_data: bytes,
    makefile_data: bytes,
    timekeeping_header_data: bytes,
    timekeeping_source_data: bytes,
    config_data: bytes,
) -> dict[str, Any]:
    core = _text(core_data, "DWC3 core header")
    gadget = _text(gadget_data, "DWC3 gadget source")
    ep0 = _text(ep0_data, "DWC3 EP0 source")
    trace = _text(trace_data, "DWC3 tracepoint export source")
    trace_header = _text(trace_header_data, "DWC3 tracepoint ABI header")
    makefile = _text(makefile_data, "DWC3 Makefile")
    timekeeping_header = _text(timekeeping_header_data, "timekeeping header")
    timekeeping_source = _text(timekeeping_source_data, "timekeeping source")
    config = _text(config_data, "fixed kernel config")
    if hashlib.sha256(config_data).hexdigest() != FIXED_KERNEL_CONFIG_SHA256:
        raise BannerContractError("fixed kernel config identity differs")
    _require_tokens(
        core,
        "DWC3 event type and host-caused event constants",
        (
            "#define DWC3_EVENT_TYPE_DEV\t0",
            "#define DWC3_EVENT_TYPE_CARKIT\t3",
            "#define DWC3_EVENT_TYPE_I2C\t4",
            "#define DWC3_DEVICE_EVENT_RESET\t\t\t1",
            "#define DWC3_DEVICE_EVENT_CONNECT_DONE\t\t2",
            "#define DWC3_DEPEVT_XFERCOMPLETE\t0x01",
        ),
    )
    event_type = _braced_block(core, "struct dwc3_event_type {")
    _require_exact_u32_bitfields(
        event_type,
        "DWC3 event discriminator layout",
        (("is_devspec", 1), ("type", 7), ("reserved8_31", 24)),
    )
    depevt = _braced_block(core, "struct dwc3_event_depevt {")
    _require_exact_u32_bitfields(
        depevt,
        "DWC3 endpoint-event layout",
        (
            ("one_bit", 1),
            ("endpoint_number", 5),
            ("endpoint_event", 4),
            ("reserved11_10", 2),
            ("status", 4),
            ("parameters", 16),
        ),
    )
    devt = _braced_block(core, "struct dwc3_event_devt {")
    _require_exact_u32_bitfields(
        devt,
        "DWC3 device-event layout",
        (
            ("one_bit", 1),
            ("device_event", 7),
            ("type", 4),
            ("reserved15_12", 4),
            ("event_info", 9),
            ("reserved31_25", 7),
        ),
    )
    event_union = _braced_block(core, "union dwc3_event {")
    _require_ordered_tokens(
        event_union,
        "DWC3 raw-event union",
        (
            "u32\t\t\t\traw;",
            "struct dwc3_event_type\t\ttype;",
            "struct dwc3_event_depevt\tdepevt;",
            "struct dwc3_event_devt\t\tdevt;",
        ),
    )
    ep0_state = _braced_block(core, "enum dwc3_ep0_state {")
    ep0_members = tuple(re.findall(r"\b(EP0_[A-Z0-9_]+)\b", ep0_state))
    if ep0_members != (
        "EP0_UNCONNECTED",
        "EP0_SETUP_PHASE",
        "EP0_DATA_PHASE",
        "EP0_STATUS_PHASE",
    ):
        raise BannerContractError("DWC3 EP0 state exact member sequence differs")
    _require_ordered_tokens(
        ep0_state,
        "DWC3 EP0 state values",
        (
            "EP0_UNCONNECTED\t\t= 0,",
            "EP0_SETUP_PHASE,",
            "EP0_DATA_PHASE,",
            "EP0_STATUS_PHASE,",
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
    event_entry = _function(
        gadget, "static void dwc3_process_event_entry(struct dwc3 *dwc,"
    )
    trace_at = event_entry.find("trace_dwc3_event(event->raw, dwc);")
    endpoint_at = event_entry.find("dwc3_endpoint_interrupt(dwc, &event->depevt);")
    gadget_at = event_entry.find("dwc3_gadget_interrupt(dwc, &event->devt);")
    if min(trace_at, endpoint_at, gadget_at) < 0 or not (
        trace_at < endpoint_at and trace_at < gadget_at
    ):
        raise BannerContractError("DWC3 event tracepoint is not before dispatch")
    _require_tokens(
        event_entry,
        "DWC3 raw-event dispatch discriminator",
        (
            "if (!event->type.is_devspec)",
            "else if (event->type.type == DWC3_EVENT_TYPE_DEV)",
            'dev_err(dwc->dev, "UNKNOWN IRQ type %d\\n", event->raw);',
        ),
    )
    endpoint_interrupt = _function(
        gadget, "static void dwc3_endpoint_interrupt(struct dwc3 *dwc,"
    )
    _require_tokens(
        endpoint_interrupt,
        "DWC3 physical EP0/EP1 dispatch",
        (
            "u8\t\t\tepnum = event->endpoint_number;",
            "if (epnum == 0 || epnum == 1) {",
            "dwc3_ep0_interrupt(dwc, event);",
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
    ep0_out_start = _function(ep0, "void dwc3_ep0_out_start(struct dwc3 *dwc)")
    _require_ordered_tokens(
        ep0_out_start,
        "DWC3 SETUP transfer physical endpoint",
        (
            "dep = dwc->eps[0];",
            "DWC3_TRBCTL_CONTROL_SETUP, false);",
            "ret = dwc3_ep0_start_trans(dep);",
        ),
    )
    _require_tokens(
        trace,
        "DWC3 module-visible event tracepoint",
        ("EXPORT_TRACEPOINT_SYMBOL_GPL(dwc3_event);",),
    )
    trace_header_counts = {
        "#include \"core.h\"": 1,
        "DECLARE_EVENT_CLASS(dwc3_log_event,": 1,
        "TP_PROTO(u32 event, struct dwc3 *dwc),": 2,
        "TP_ARGS(event, dwc)": 2,
        "__field(u32, ep0state)": 1,
        "__entry->ep0state = dwc->ep0state;": 1,
        "DEFINE_EVENT(dwc3_log_event, dwc3_event,": 1,
    }
    if any(
        trace_header.count(token) != count
        for token, count in trace_header_counts.items()
    ):
        raise BannerContractError("DWC3 tracepoint callback ABI differs")
    _require_tokens(
        makefile,
        "DWC3 trace object build selection",
        (
            "ifneq ($(CONFIG_TRACING),)",
            "dwc3-y\t\t\t\t+= trace.o",
        ),
    )
    config_lines = set(config.splitlines())
    for required in (
        "CONFIG_TRACING=y",
        "CONFIG_USB_DWC3=y",
        "CONFIG_USB_DWC3_DUAL_ROLE=y",
    ):
        if required not in config_lines:
            raise BannerContractError(f"fixed kernel config lacks {required}")
    _require_tokens(
        timekeeping_header,
        "same-clock module API",
        (
            "extern ktime_t ktime_get(void);",
            "static inline u64 ktime_get_ns(void)",
            "return ktime_to_ns(ktime_get());",
        ),
    )
    ktime_get_body = _function(timekeeping_source, "ktime_t ktime_get(void)")
    _require_tokens(
        ktime_get_body,
        "monotonic clock implementation",
        (
            "read_seqcount_begin(&tk_core.seq)",
            "timekeeping_get_ns(&tk->tkr_mono)",
            "read_seqcount_retry(&tk_core.seq, seq)",
        ),
    )
    _require_tokens(
        timekeeping_source,
        "module-visible monotonic clock",
        ("EXPORT_SYMBOL_GPL(ktime_get);",),
    )
    return {
        "reset_dispatch_source_bound": True,
        "connect_done_dispatch_source_bound": True,
        "setup_completion_source_bound": True,
        "tracepoint_precedes_device_and_endpoint_dispatch": True,
        "dwc3_event_tracepoint_exported_gpl": True,
        "dwc3_event_callback_proto_source_bound": True,
        "dwc3_event_callback_receives_raw_and_dwc": True,
        "dwc3_event_ep0state_source_bound": True,
        "raw_event_bitfield_layout_source_bound": True,
        "raw_event_dispatch_discriminator_source_bound": True,
        "setup_uses_physical_ep0_source_bound": True,
        "raw_decoder_preimages": audit_dwc3_raw_decoder(),
        "trace_object_enabled_by_fixed_config": True,
        "module_only_producer_feasible": True,
        "kprobe_required": False,
        "tracefs_required": False,
        "trace_clock_used": False,
        "clock_primitive": "ktime_get_ns_via_exported_ktime_get",
        "clock_is_shared_by_latch_and_diagnostic_design": True,
        "producer_implementation_present": False,
        "gadget_ready_used_as_host_event": False,
    }


def successor_contract() -> dict[str, Any]:
    budget = validate_v4_budget()
    return {
        "status": "CHANGES_REQUIRED_PRODUCER_AND_V4_NOT_IMPLEMENTED",
        "ordering": [
            "load_early_dwc3_event_latch_module",
            "prove_tracepoint_registered_and_exact_a600000_dwc3_filter_armed",
            "capture_one_shot_gadget_exposure_gate_in_latch_module",
            "read_back_exposure_gate_then_bind_configfs_udc",
            "only_then_expose_the_gadget_to_the_host",
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
            "deadline_source": "new_once_initialized_absolute_monotonic_deadline",
            "deadline_seconds": 5,
            "deadline_covers_eintr": True,
            "deadline_covers_eagain": True,
            "deadline_covers_every_short_write_iteration": True,
            "deadline_checked_before_every_write_or_retry": True,
            "deadline_never_reinitialized": True,
            "sleep_is_capped_to_remaining_deadline": True,
            "existing_p260_helper_is_not_sufficient": True,
            "terminal_publication_required_for_every_outcome": True,
            "retry_after_terminal_forbidden": True,
        },
        "outcomes": list(OUTCOMES),
        "error_class_encoding": {
            "width_bytes": 1,
            "mapping": ERROR_CLASSES,
            "eagain_epipe_enodev_are_pairwise_distinct": True,
            "unknown_errno_may_only_enter_other_errno": True,
            "silent_saturation_forbidden": True,
        },
        "outcome_rules": {
            "written": "bytes_written == 49 and error_class == none",
            "eagain_timeout": (
                "bytes_written == 0 and final cause is eagain_deadline"
            ),
            "failure": (
                "bytes_written == 0 and final cause preserves epipe, enodev, "
                "etimedout, zero_write, invalid_short_write, or other_errno"
            ),
            "partial": (
                "1 <= bytes_written <= 48; normalized cause separately retains "
                "eagain_deadline, epipe, enodev, etimedout, zero-write, "
                "invalid-short-write, or other-errno"
            ),
        },
        "terminal_domain_audit": audit_banner_terminal_domain(),
        "banner_length_contract": {
            "source_expression": "sizeof(p260_banner) - 1",
            "expected_bytes": 49,
            "encoded_byte_count_max": 255,
            "implementation_static_assert_required": (
                "sizeof(p260_banner) - 1 <= UINT8_MAX"
            ),
            "encoder_rejects_out_of_range_instead_of_saturating": True,
        },
        "retained_fields": [
            "banner_outcome",
            "banner_bytes_written",
            "banner_error_class",
            "timing_valid_mask",
            "first_host_event_kind",
            "latch_install_delta_us_from_pre",
            "gadget_exposure_delta_us_from_pre",
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
                "26_byte_same_clock_timing_prefix",
                "3_byte_banner_result_prefix",
                "packbits_poll_up_to_47_bytes_or_44_byte_overflow_summary",
            ],
        },
        "host_event_producer": {
            "architecture": "early_gpl_module_on_exported_dwc3_event_tracepoint",
            "image_patch_required": False,
            "kprobe_required": False,
            "tracefs_required": False,
            "target_filter": "dev_name(dwc->dev) == a600000.dwc3",
            "event_decode": ["reset", "connect_done", "ep0_setup_complete"],
            "event_decode_rule": (
                "masked core.h bitfields; full raw-word equality is forbidden"
            ),
            "raw_decoder_preimages": audit_dwc3_raw_decoder(),
            "clock_primitive": "ktime_get_ns",
            "publish_rule": (
                "store kind/time then release-publish first-event-seen; "
                "reader acquires before copying"
            ),
            "load_order": (
                "tracepoint registration and exact-target armed readback must "
                "complete before configfs UDC bind exposes the gadget"
            ),
            "module_plan_effect": (
                "one new early custom latch module before the 69 stock early "
                "modules; inherited diagnostic remains late"
            ),
            "implementation_present": False,
            "gadget_exposure_sample_producer": (
                "the early latch module captures ktime_get_ns once through a "
                "write-once pre-UDC gate; runtime proves marker readback then "
                "performs the sole configfs UDC bind"
            ),
            "gadget_exposure_source_binding_present": False,
            "gadget_exposure_sample_is_actual_bind_time": False,
            "gadget_exposure_sample_semantics": (
                "same-clock pre-exposure gate whose source-bound runtime order "
                "plus successful sole UDC bind must prove latch installation "
                "preceded gadget exposure"
            ),
            "gadget_exposure_qualification_obligations": (
                "module-owned write-once gate calls ktime_get_ns, runtime reads "
                "back that exact marker before its only configfs UDC bind, and "
                "the existing gadget-evaluability witness proves that bind "
                "completed"
            ),
            "latched_hot_path": (
                "one acquire/read of first-event state then immediate return; "
                "target filtering, bitfield decode, clock read, and publication "
                "occur only while unlatchable"
            ),
        },
        "timing": {
            "samples": list(TIMING_SAMPLES),
            "encoding": (
                "pre_is_zero_origin_plus_six_signed_int32_microsecond_deltas"
            ),
            "clock_domain": "ktime_get_ns_in_both_kernel_modules",
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
                "bit5": "latch_install",
                "bit6": "gadget_exposure",
            },
            "causal_validity_masks": [111, 127],
            "legacy_0x0f_meaning": (
                "host event not observable because latch-install authority is "
                "absent; never no-host-event"
            ),
            "required_device_sample_order": "pre <= write <= post1 < post2",
            "required_latch_order": (
                "tracepoint_registered <= latch_install <= gadget_exposure "
                "<= pre; armed-before is derived from retained same-clock samples"
            ),
            "host_event_kind_pairing": (
                "mask_0x6f_requires_none; mask_0x7f_requires_"
                "reset_connect_done_or_setup"
            ),
            "host_receipt_cross_check": {
                "endpoint_present_plus_mask_0x6f": (
                    "observer_contradiction_latched_event_missing"
                ),
                "endpoint_absent_plus_mask_0x6f": (
                    "legal_no_host_event_only_when_armed_before_gadget_exposure"
                ),
                "mask_without_bits5_or6": (
                    "host_event_not_observable_no_causal_claim"
                ),
            },
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
                "build and qualify the early latch and late diagnostic with "
                "literal ktime_get_ns calls, source-bound tracepoint register/"
                "unregister, masked raw-event decoding, one-read latched hot-path "
                "early return, derived armed-before-UDC ordering, exact DWC3 "
                "filtering, and host-receipt contradiction preimages"
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
            "lossless_boundary_preimages": [47, 48],
            "overflow_spare_policy": (
                "all 3 spare bytes encode as zero and nonzero is rejected"
            ),
        },
        "arming": {
            "real_encoder_carrier_decoder_required": True,
            "positive_preimages": list(PREIMAGE_OBLIGATIONS),
            "all_outcomes_surjective": True,
            "written_bytes_outside_0_to_49_rejected": True,
            "written_outcome_with_non49_count_rejected": True,
            "partial_outcome_with_boundary_count_rejected": True,
            "only_causal_validity_masks_0x6f_and_0x7f_allowed": True,
            "mask_without_latch_install_or_gadget_exposure_cannot_mean_no_host_event": True,
            "armed_before_gadget_exposure_is_derived_not_asserted": True,
            "gadget_ready_event_kind_rejected": True,
            "lossless_47_and_overflow_48_preimages_required": True,
            "overflow_spare_three_bytes_zero_and_decode_rejected_if_nonzero": True,
            "same_clock_ordering_preimages_required": True,
            "host_receipt_mask_cross_product_required": True,
            "eagain_epipe_enodev_preimages_required": True,
            "zero_and_invalid_short_at_zero_preimages_required": True,
            "eintr_storm_absolute_deadline_preimage_required": True,
            "eagain_storm_absolute_deadline_preimage_required": True,
            "short_write_then_eintr_deadline_preimage_required": True,
            "banner_length_source_bound_and_u8_safe": True,
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
    dwc3_trace_data: bytes,
    dwc3_trace_header_data: bytes,
    dwc3_makefile_data: bytes,
    timekeeping_header_data: bytes,
    timekeeping_source_data: bytes,
    kernel_config_data: bytes,
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
            "dwc3_trace_source": receipt(dwc3_trace_data),
            "dwc3_trace_abi_header": receipt(dwc3_trace_header_data),
            "dwc3_makefile": receipt(dwc3_makefile_data),
            "timekeeping_header": receipt(timekeeping_header_data),
            "timekeeping_source": receipt(timekeeping_source_data),
            "fixed_kernel_config": receipt(kernel_config_data),
            "extractor": receipt(extractor_data),
        },
        "current": audit_current_sources(
            materialized_data, p260_data, envelope_data, base_envelope_data
        ),
        "host_event_source_audit": audit_host_event_sources(
            dwc3_core_data,
            dwc3_gadget_data,
            dwc3_ep0_data,
            dwc3_trace_data,
            dwc3_trace_header_data,
            dwc3_makefile_data,
            timekeeping_header_data,
            timekeeping_source_data,
            kernel_config_data,
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
    parser.add_argument("--dwc3-trace", type=Path, default=DEFAULT_DWC3_TRACE)
    parser.add_argument(
        "--dwc3-trace-header", type=Path, default=DEFAULT_DWC3_TRACE_HEADER
    )
    parser.add_argument("--dwc3-makefile", type=Path, default=DEFAULT_DWC3_MAKEFILE)
    parser.add_argument(
        "--timekeeping-header", type=Path, default=DEFAULT_TIMEKEEPING_HEADER
    )
    parser.add_argument(
        "--timekeeping-source", type=Path, default=DEFAULT_TIMEKEEPING_SOURCE
    )
    parser.add_argument("--kernel-config", type=Path, default=DEFAULT_KERNEL_CONFIG)
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
        dwc3_trace_data=stable_read(
            resolve(args.dwc3_trace), "DWC3 tracepoint export source", 2**20
        ),
        dwc3_trace_header_data=stable_read(
            resolve(args.dwc3_trace_header), "DWC3 tracepoint ABI header", 2**20
        ),
        dwc3_makefile_data=stable_read(
            resolve(args.dwc3_makefile), "DWC3 Makefile", 2**20
        ),
        timekeeping_header_data=stable_read(
            resolve(args.timekeeping_header), "timekeeping header", 2**20
        ),
        timekeeping_source_data=stable_read(
            resolve(args.timekeeping_source), "timekeeping source", 2**24
        ),
        kernel_config_data=stable_read(
            resolve(args.kernel_config), "fixed kernel config", 2**20
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
