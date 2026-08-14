#!/usr/bin/env python3
"""Freeze the P3.17 banner blind spot and the P3.18 successor contract.

P3.17 publishes its retained terminal before calling p260_write_banner() and
discards the return value.  No after-the-fact stage can repair that ordering.
This host-only contract requires a future candidate to perform one bounded
attempt first, retain its outcome and byte count in a new envelope version,
and publish the terminal even when banner delivery fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p318_banner_result_contract_v1"
VERDICT = "PASS_P318_BANNER_RESULT_DESIGN_H0_IMPLEMENTATION_REQUIRED"
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

OUTCOMES = ("written", "eagain_timeout", "errno", "partial")
PREIMAGE_OBLIGATIONS = (
    {"outcome": "written", "bytes_written": 49, "error_class": "none"},
    {"outcome": "eagain_timeout", "bytes_written": 0, "error_class": "timeout"},
    {"outcome": "errno", "bytes_written": 0, "error_class": "normalized_errno"},
    {"outcome": "partial", "bytes_written": 1, "error_class": "normalized_cause"},
    {"outcome": "partial", "bytes_written": 48, "error_class": "normalized_cause"},
)


class BannerContractError(ValueError):
    pass


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
    materialized_data: bytes, p260_data: bytes, envelope_data: bytes
) -> dict[str, Any]:
    materialized = _text(materialized_data, "P3.17 materialized runtime")
    p260 = _text(p260_data, "P2.60 banner helper")
    envelope = _text(envelope_data, "P3.17 envelope")
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


def successor_contract() -> dict[str, Any]:
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
        ],
        "schema": {
            "carrier_size": 128,
            "carrier_resize_forbidden": True,
            "new_envelope_version_required": True,
            "v3_reserved_byte_reinterpretation_forbidden": True,
            "registered_terminal_details_required": True,
        },
        "arming": {
            "real_encoder_carrier_decoder_required": True,
            "positive_preimages": list(PREIMAGE_OBLIGATIONS),
            "all_outcomes_surjective": True,
            "written_bytes_outside_0_to_49_rejected": True,
            "written_outcome_with_non49_count_rejected": True,
            "partial_outcome_with_boundary_count_rejected": True,
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
    extractor_data: bytes,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inputs": {
            "p317_materialized_runtime": receipt(materialized_data),
            "p260_banner_helper": receipt(p260_data),
            "p317_envelope": receipt(envelope_data),
            "extractor": receipt(extractor_data),
        },
        "current": audit_current_sources(
            materialized_data, p260_data, envelope_data
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
