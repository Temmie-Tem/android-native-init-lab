#!/usr/bin/env python3
"""P3.21 stock-observer Process-v2 adapter, host-only.

P3.21 reuses the reviewed P3.20 observer implementation and gives it a new,
explicit run-ID binding.  The wrapper is intentionally small, but the bound
delegate is not a wildcard: Carrier records, retained payloads, acceptance
metadata, and all default decoder calls are pinned to the fresh P3.21 ID and
reject both P3.19 and P3.20 identities.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

P320_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p320_stock_process_v2_adapter.py"
P320_ADAPTER_IDENTITY = {
    "size": 56_669,
    "sha256": "92be097287be67867b263e5534996228d275d1d70fa03c38b3a124a948a94d88",
}

P319_RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
P320_RUN_ID = bytes.fromhex("c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
P321_RUN_ID = bytes.fromhex("c321f1e0a90b5e6d7c8a9b0c1d2e3f4b")
P321_RUN_ID_HEX = P321_RUN_ID.hex()
PREDECESSOR_P320_RUN_ID = P320_RUN_ID

P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_DECODER_ID = "s22plus_fyg8_p321_observer_v4_carrier_v1"
P321_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p321-observer-error-v1"
P321_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P321_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "parent=unavailable|w5=unavailable|run="
    + P321_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P321_POLICY_ID = hashlib.sha256(P321_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The P3.21 adapter delegate or binding is not exact."""


def _stable_source(path: Path, expected: dict[str, Any]) -> bytes:
    try:
        state = path.lstat()
        resolved = path.resolve(strict=True)
        payload = path.read_bytes()
    except OSError as exc:
        raise AdapterIdentityError("P3.20 adapter source is unavailable") from exc
    if (
        resolved != path.absolute()
        or not path.is_file()
        or path.is_symlink()
        or state.st_nlink != 1
        or {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        != expected
    ):
        raise AdapterIdentityError("P3.20 adapter source identity differs")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(P320_ADAPTER_SOURCE, P320_ADAPTER_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p320_adapter_bound_for_p321")
    module.__file__ = str(P320_ADAPTER_SOURCE)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P320_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.20 adapter delegate failed to load") from exc

    replacements = {
        "SCHEMA": "s22plus_fyg8_p321_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P321_OVERLAY_CONTRACT_ID,
        "P319_OVERLAY_CONTRACT_ID": P320_OVERLAY_CONTRACT_ID,
        "P320_STOCK_RUN_ID": P321_RUN_ID,
        "P320_RUN_ID": P321_RUN_ID,
        "P319_STOCK_RUN_ID": P320_RUN_ID,
        "STOCK_RUN_ID": P321_RUN_ID,
        "RUN_ID": P321_RUN_ID,
        "DECODER_ID": P321_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P321_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P321_POLICY_PREIMAGE,
        "POLICY_ID": P321_POLICY_ID,
    }
    for name, value in replacements.items():
        setattr(module, name, value)

    # Several reviewed helper functions captured the old P3.20 default as a
    # keyword default.  Rebind those defaults explicitly; otherwise a caller
    # omitting expected_run_id could silently decode the predecessor run.
    for function_name, keyword in (
        ("classify_observation", "expected_run_id"),
        ("classify_clean_baseline", "expected_run_id"),
        ("_carrier_record_from_envelope", "run_id"),
    ):
        function = getattr(module, function_name, None)
        defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
        defaults[keyword] = P321_RUN_ID
        function.__kwdefaults__ = defaults
    return module


_DELEGATE = _load_delegate()
for _name, _value in _DELEGATE.__dict__.items():
    if not _name.startswith("__"):
        globals()[_name] = _value

# Public P3.21 names are intentionally distinct from the delegate's historical
# P3.20 names.  The delegate globals above are already patched to these bytes.
SCHEMA = "s22plus_fyg8_p321_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P321_OVERLAY_CONTRACT_ID
P319_OVERLAY_CONTRACT_ID = P320_OVERLAY_CONTRACT_ID
P320_STOCK_RUN_ID = P321_RUN_ID
P320_RUN_ID = P321_RUN_ID
P319_STOCK_RUN_ID = PREDECESSOR_P320_RUN_ID
STOCK_RUN_ID = P321_RUN_ID
RUN_ID = P321_RUN_ID
DECODER_ID = P321_DECODER_ID
OBSERVER_CONTRACT_ID = P321_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P321_POLICY_PREIMAGE
POLICY_ID = P321_POLICY_ID


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    """Decode only a Carrier record bound to P3.21."""
    bound = P321_RUN_ID if expected_run_id is None else expected_run_id
    if bound != P321_RUN_ID:
        raise DecodeError("P321 Carrier run ID is not bound to the P321 run")
    return _DELEGATE.decode_record(
        record,
        expected_profile=expected_profile,
        expected_run_id=P321_RUN_ID,
    )


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P321_RUN_ID,
) -> dict[str, Any]:
    if expected_run_id != P321_RUN_ID:
        raise DecodeError("P321 observer run ID is not bound to the P321 run")
    return _DELEGATE.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=P321_RUN_ID,
    )


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P321_RUN_ID,
) -> dict[str, Any]:
    if expected_run_id != P321_RUN_ID:
        raise DecodeError("P321 baseline run ID is not bound to the P321 run")
    return _DELEGATE.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=P321_RUN_ID,
    )


def audit() -> dict[str, Any]:
    """Run the inherited fixture audit under the fresh P3.21 identity."""
    value = dict(_DELEGATE.audit())
    value["schema"] = "s22plus_fyg8_p321_stock_process_v2_adapter_v1"
    value["verdict"] = "PASS_P321_STOCK_PROCESS_V2_ADAPTER_H0"
    value["overlay_contract_id"] = P321_OVERLAY_CONTRACT_ID
    value["p319_overlay_contract_id"] = P320_OVERLAY_CONTRACT_ID
    value["decoder"] = P321_DECODER_ID
    value["policy_id"] = P321_POLICY_ID
    value["predecessor_run_id"] = PREDECESSOR_P320_RUN_ID.hex()
    value["run_id"] = P321_RUN_ID.hex()
    return value


__all__ = [
    "AdapterIdentityError",
    "DECODER_ID",
    "OVERLAY_CONTRACT_ID",
    "P319_OVERLAY_CONTRACT_ID",
    "P319_RUN_ID",
    "P320_ADAPTER_IDENTITY",
    "P320_ADAPTER_SOURCE",
    "P320_OVERLAY_CONTRACT_ID",
    "P320_RUN_ID",
    "PREDECESSOR_P320_RUN_ID",
    "P320_STOCK_RUN_ID",
    "P321_DECODER_ID",
    "P321_OBSERVER_CONTRACT_ID",
    "P321_OVERLAY_CONTRACT_ID",
    "P321_POLICY_ID",
    "P321_POLICY_PREIMAGE",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "POLICY_ID",
    "PROFILE",
    "RUN_ID",
    "SCHEMA",
    "STOCK_RUN_ID",
    "acceptance_fixture",
    "audit",
    "bind_exact_sources",
    "classify_clean_baseline",
    "classify_observation",
    "decode_record",
    "encode_fixture",
    "identity",
    "validate_acceptance_item",
    "validate_contract",
]
