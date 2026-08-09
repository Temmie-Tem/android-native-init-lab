#!/usr/bin/env python3
"""Canonical P3.13 host guard lifetime and wrapper-receipt contract."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


OVERLAY_CONTRACT_ID = (
    "s22plus-fyg8-p313-post-bind-resume-cycle-carrier-v2-observer-v1"
)
DERIVATION_SCHEMA = "s22plus_fyg8_p313_guard_lifetime_derivation_v1"
ARM_SCHEMA = "s22plus_fyg8_p313_guard_lifetime_arm_v1"
RELEASE_SCHEMA = "s22plus_fyg8_p313_guard_lifetime_release_v1"

# These are the bounded host operations not represented by the six live-path
# timeout inputs.  The final allowance is deliberately explicit: expiry still
# fails closed, so it extends observer availability without weakening proof.
OVERHEAD_COMPONENTS_SEC = {
    "guard_arm": 30,
    "usb_trace_arm": 20,
    "usb_trace_close": 40,
    "guard_release": 20,
    "host_scheduling_and_durable_receipts": 210,
}
REVIEWED_OVERHEAD_SEC = 320


class GuardLifetimeError(ValueError):
    pass


_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise GuardLifetimeError(f"P3.13 {label} hash is invalid")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise GuardLifetimeError(f"{label} must be a positive integer")
    return value


def derive(
    *,
    download_request_sec: int,
    download_wait_sec: int,
    endpoint_revalidate_sec: int,
    odin_timeout_sec: int,
    download_departure_wait_sec: int,
    candidate_observation_sec: int,
    guard_default_sec: int,
    guard_limit_sec: int,
) -> dict[str, Any]:
    """Return the only approved P3.13 guard-lifetime derivation."""

    inputs = {
        "download_request_sec": _positive_int(
            download_request_sec, "Download request timeout"
        ),
        "download_wait_sec": _positive_int(
            download_wait_sec, "Download endpoint timeout"
        ),
        "endpoint_revalidate_sec": _positive_int(
            endpoint_revalidate_sec, "endpoint revalidation timeout"
        ),
        "odin_timeout_sec": _positive_int(
            odin_timeout_sec, "Odin timeout"
        ),
        "download_departure_wait_sec": _positive_int(
            download_departure_wait_sec, "Download departure timeout"
        ),
        "candidate_observation_sec": _positive_int(
            candidate_observation_sec, "candidate observation timeout"
        ),
        "guard_default_sec": _positive_int(
            guard_default_sec, "guard default lifetime"
        ),
        "guard_limit_sec": _positive_int(
            guard_limit_sec, "guard maximum lifetime"
        ),
    }
    if sum(OVERHEAD_COMPONENTS_SEC.values()) != REVIEWED_OVERHEAD_SEC:
        raise GuardLifetimeError("P3.13 reviewed overhead components drifted")
    configured_subtotal = sum(
        inputs[key]
        for key in (
            "download_request_sec",
            "download_wait_sec",
            "endpoint_revalidate_sec",
            "odin_timeout_sec",
            "download_departure_wait_sec",
            "candidate_observation_sec",
        )
    )
    max_sec = configured_subtotal + REVIEWED_OVERHEAD_SEC
    if not inputs["guard_default_sec"] <= max_sec <= inputs["guard_limit_sec"]:
        raise GuardLifetimeError("derived P3.13 guard lifetime is outside bounds")
    return {
        "schema": DERIVATION_SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "inputs": inputs,
        "configured_subtotal_sec": configured_subtotal,
        "reviewed_overhead_components_sec": dict(OVERHEAD_COMPONENTS_SEC),
        "reviewed_overhead_sec": REVIEWED_OVERHEAD_SEC,
        "max_sec": max_sec,
    }


def validate_derivation(value: Any, expected: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value != dict(expected):
        raise GuardLifetimeError("P3.13 guard lifetime derivation differs")
    if value.get("schema") != DERIVATION_SCHEMA:
        raise GuardLifetimeError("P3.13 guard lifetime schema differs")
    return value


def arm_value(
    *,
    approval_binding_sha256: str,
    derivation: Mapping[str, Any],
    v2_arm_receipt_sha256: str,
) -> dict[str, Any]:
    for value, label in (
        (approval_binding_sha256, "approval binding"),
        (v2_arm_receipt_sha256, "v2 arm receipt"),
    ):
        _sha256(value, label)
    return {
        "schema": ARM_SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "approval_binding_sha256": approval_binding_sha256,
        "derivation": dict(derivation),
        "derivation_sha256": digest(derivation),
        "v2_arm_receipt_sha256": v2_arm_receipt_sha256,
    }


def validate_arm(
    value: Any,
    *,
    approval_binding_sha256: str,
    derivation: Mapping[str, Any],
    v2_arm_receipt_sha256: str,
) -> dict[str, Any]:
    expected = arm_value(
        approval_binding_sha256=approval_binding_sha256,
        derivation=derivation,
        v2_arm_receipt_sha256=v2_arm_receipt_sha256,
    )
    if not isinstance(value, dict) or value != expected:
        raise GuardLifetimeError("P3.13 guard lifetime arm receipt differs")
    return value


def release_value(
    *,
    lifetime_arm_sha256: str,
    v2_release_receipt_sha256: str,
    elapsed_upper_millis: int,
    max_sec: int,
) -> dict[str, Any]:
    for value, label in (
        (lifetime_arm_sha256, "lifetime arm receipt"),
        (v2_release_receipt_sha256, "v2 release receipt"),
    ):
        _sha256(value, label)
    if type(elapsed_upper_millis) is not int or elapsed_upper_millis < 0:
        raise GuardLifetimeError("P3.13 elapsed upper bound is invalid")
    max_sec = _positive_int(max_sec, "P3.13 guard lifetime")
    return {
        "schema": RELEASE_SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "lifetime_arm_sha256": lifetime_arm_sha256,
        "v2_release_receipt_sha256": v2_release_receipt_sha256,
        "elapsed_upper_millis": elapsed_upper_millis,
        "max_sec": max_sec,
        "released_within_lifetime": elapsed_upper_millis <= max_sec * 1000,
    }


def validate_release(
    value: Any,
    *,
    lifetime_arm_sha256: str,
    v2_release_receipt_sha256: str,
    elapsed_upper_millis: int,
    max_sec: int,
) -> dict[str, Any]:
    expected = release_value(
        lifetime_arm_sha256=lifetime_arm_sha256,
        v2_release_receipt_sha256=v2_release_receipt_sha256,
        elapsed_upper_millis=elapsed_upper_millis,
        max_sec=max_sec,
    )
    if not isinstance(value, dict) or value != expected:
        raise GuardLifetimeError("P3.13 guard lifetime release receipt differs")
    return value
