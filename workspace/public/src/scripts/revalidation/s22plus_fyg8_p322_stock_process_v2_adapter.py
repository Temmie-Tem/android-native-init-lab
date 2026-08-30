#!/usr/bin/env python3
"""P3.22 stock-observer Process-v2 adapter, host-only.

The reviewed P3.21 adapter is loaded by exact source identity and rebound to
the fresh P3.22 run ID.  Its P3.20 Carrier implementation remains the
execution-critical delegate, while the public lineage retains P3.19, P3.20,
and P3.21 as rejected predecessors.  Every run-bearing Python default is
rebound explicitly, since defaults are captured before globals are patched.

This adapter decodes host fixtures only.  It creates no authority and never
contacts a device or invokes Odin.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import os
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent

P321_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p321_stock_process_v2_adapter.py"
P321_ADAPTER_IDENTITY = {
    "size": 8_034,
    "sha256": "642a856036ada8f8977163b9faac18b97fd17a38695ea1dc39a166c4d4464625",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)

P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P322_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p322-observer-v4-carrier-v1"
P322_DECODER_ID = "s22plus_fyg8_p322_observer_v4_carrier_v1"
P322_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p322-observer-error-v1"
P322_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P322_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "parent=unavailable|w5=unavailable|run="
    + P322_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P322_POLICY_ID = hashlib.sha256(P322_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The P3.21 delegate or the P3.22 adapter binding is not exact."""


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    """Read one exact regular source file without following an indirect path."""
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(int(expected["size"]) + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError(f"{label} is unavailable") from exc
    before_id = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    inside_id = (
        inside.st_dev,
        inside.st_ino,
        inside.st_mode,
        inside.st_nlink,
        inside.st_uid,
        inside.st_gid,
        inside.st_size,
        inside.st_mtime_ns,
        inside.st_ctime_ns,
    )
    after_id = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_uid,
        after.st_gid,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != inside_id
        or before_id != after_id
        or len(payload) != before.st_size
        or actual != dict(expected)
    ):
        raise AdapterIdentityError(f"{label} identity differs")
    return payload


def _rebind_defaults(module: types.ModuleType, current: bytes) -> None:
    for function_name, keyword in (
        ("classify_observation", "expected_run_id"),
        ("classify_clean_baseline", "expected_run_id"),
        ("_carrier_record_from_envelope", "run_id"),
    ):
        function = getattr(module, function_name, None)
        if function is None:
            raise AdapterIdentityError(f"bound adapter lacks {function_name}")
        defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
        defaults[keyword] = current
        function.__kwdefaults__ = defaults


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P321_ADAPTER_SOURCE,
        "P3.21 Process-v2 adapter source",
        P321_ADAPTER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p321_adapter_bound_for_p322")
    module.__file__ = str(P321_ADAPTER_SOURCE)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P321_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.21 Process-v2 adapter failed to load") from exc

    if (
        getattr(module, "P319_RUN_ID", None) != P319_RUN_ID
        or getattr(module, "PREDECESSOR_P320_RUN_ID", None) != P320_RUN_ID
        or getattr(module, "P321_RUN_ID", None) != P321_RUN_ID
        or getattr(module, "P321_RUN_ID_HEX", None) != P321_RUN_ID_HEX
    ):
        raise AdapterIdentityError("P3.21 adapter predecessor identities differ")
    predecessor_p321_overlay = module.P321_OVERLAY_CONTRACT_ID
    predecessor_p320_overlay = module.P320_OVERLAY_CONTRACT_ID
    inner = module._DELEGATE

    # The P321 wrapper's inner P320 implementation is the execution-critical
    # decoder.  Rebind its current slot and retain P321 as its predecessor.
    replacements = {
        "SCHEMA": "s22plus_fyg8_p322_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P322_OVERLAY_CONTRACT_ID,
        "P319_OVERLAY_CONTRACT_ID": predecessor_p321_overlay,
        "P320_STOCK_RUN_ID": P322_RUN_ID,
        "P320_RUN_ID": P322_RUN_ID,
        "P319_STOCK_RUN_ID": P321_RUN_ID,
        "STOCK_RUN_ID": P322_RUN_ID,
        "RUN_ID": P322_RUN_ID,
        "DECODER_ID": P322_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P322_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P322_POLICY_PREIMAGE,
        "POLICY_ID": P322_POLICY_ID,
    }
    for name, value in replacements.items():
        setattr(inner, name, value)
    _rebind_defaults(inner, P322_RUN_ID)

    # Rebind the outer P321 wrapper's globals too: its public decoder and
    # classifier functions resolve their identity checks in this module.
    outer_replacements = {
        "P321_RUN_ID_HEX": P322_RUN_ID_HEX,
        "P321_RUN_ID": P322_RUN_ID,
        "P322_RUN_ID_HEX": P322_RUN_ID_HEX,
        "P322_RUN_ID": P322_RUN_ID,
        "P320_RUN_ID": P322_RUN_ID,
        "P320_STOCK_RUN_ID": P322_RUN_ID,
        "P319_STOCK_RUN_ID": P321_RUN_ID,
        "PREDECESSOR_P320_RUN_ID": P321_RUN_ID,
        "P321_OVERLAY_CONTRACT_ID": P322_OVERLAY_CONTRACT_ID,
        "P320_OVERLAY_CONTRACT_ID": predecessor_p321_overlay,
        "P319_OVERLAY_CONTRACT_ID": predecessor_p320_overlay,
        "P321_DECODER_ID": P322_DECODER_ID,
        "P321_OBSERVER_CONTRACT_ID": P322_OBSERVER_CONTRACT_ID,
        "P321_POLICY_PREIMAGE": P322_POLICY_PREIMAGE,
        "P321_POLICY_ID": P322_POLICY_ID,
    }
    for name, value in outer_replacements.items():
        setattr(module, name, value)
    _rebind_defaults(module, P322_RUN_ID)
    return module


_DELEGATE = _load_delegate()

# The P321 audit hard-codes its schema/verdict labels.  Keep it as the
# implementation source, then normalize only those presentation fields.
_P321_MODULE = _DELEGATE
_ORIGINAL_AUDIT = _P321_MODULE.audit

for _name, _value in _P321_MODULE.__dict__.items():
    if not _name.startswith("__") and _name != "_DELEGATE":
        globals()[_name] = _value

# Public lineage is truthful even though the loaded delegate uses P3.22 in
# its internal P321-named compatibility slot.
AdapterIdentityError = _P321_MODULE.AdapterIdentityError
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P322_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p322-observer-v4-carrier-v1"
PREDECESSOR_P320_RUN_ID = P320_RUN_ID
PREDECESSOR_P321_RUN_ID = P321_RUN_ID
P319_STOCK_RUN_ID = P320_RUN_ID
P320_STOCK_RUN_ID = P320_RUN_ID
P321_STOCK_RUN_ID = P321_RUN_ID
P322_STOCK_RUN_ID = P322_RUN_ID
P322_DECODER_ID = "s22plus_fyg8_p322_observer_v4_carrier_v1"
P322_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p322-observer-error-v1"
P322_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P322_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "parent=unavailable|w5=unavailable|run="
    + P322_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P322_POLICY_ID = hashlib.sha256(P322_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
RUN_ID = P322_RUN_ID
STOCK_RUN_ID = P322_RUN_ID
SCHEMA = "s22plus_fyg8_p322_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P322_OVERLAY_CONTRACT_ID
DECODER_ID = P322_DECODER_ID
OBSERVER_CONTRACT_ID = P322_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P322_POLICY_PREIMAGE
POLICY_ID = P322_POLICY_ID
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
P321_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p321_stock_process_v2_adapter.py"
P321_ADAPTER_IDENTITY = dict(P321_ADAPTER_IDENTITY)


def acceptance_fixture() -> dict[str, Any]:
    """Return the inherited non-authorizing fixture with a P3.22 path label."""
    value = dict(_DELEGATE.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        artifact = dict(contract.get(key, {}))
        artifact["path"] = "p322-stock-observer-v4-fixture"
        contract[key] = artifact
    value["contract"] = contract
    return value


def audit() -> dict[str, Any]:
    """Run the inherited fixture audit under the fresh P3.22 identity."""
    value = dict(_ORIGINAL_AUDIT())
    value["schema"] = "s22plus_fyg8_p322_stock_process_v2_adapter_v1"
    value["verdict"] = "PASS_P322_STOCK_PROCESS_V2_ADAPTER_H0"
    value["overlay_contract_id"] = P322_OVERLAY_CONTRACT_ID
    value["p319_overlay_contract_id"] = P321_OVERLAY_CONTRACT_ID
    value["decoder"] = P322_DECODER_ID
    value["policy_id"] = P322_POLICY_ID
    value["predecessor_run_id"] = P321_RUN_ID.hex()
    value["run_id"] = P322_RUN_ID.hex()
    return value


__all__ = [
    "AdapterIdentityError",
    "DECODER_ID",
    "OVERLAY_CONTRACT_ID",
    "P319_OVERLAY_CONTRACT_ID",
    "P319_RUN_ID",
    "P319_RUN_ID_HEX",
    "P320_ADAPTER_IDENTITY",
    "P320_ADAPTER_SOURCE",
    "P320_OVERLAY_CONTRACT_ID",
    "P320_RUN_ID",
    "P320_RUN_ID_HEX",
    "P320_STOCK_RUN_ID",
    "P321_ADAPTER_IDENTITY",
    "P321_ADAPTER_SOURCE",
    "P321_DECODER_ID",
    "P321_OBSERVER_CONTRACT_ID",
    "P321_OVERLAY_CONTRACT_ID",
    "P321_POLICY_ID",
    "P321_POLICY_PREIMAGE",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "P321_STOCK_RUN_ID",
    "P322_DECODER_ID",
    "P322_OBSERVER_CONTRACT_ID",
    "P322_OVERLAY_CONTRACT_ID",
    "P322_POLICY_ID",
    "P322_POLICY_PREIMAGE",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P322_STOCK_RUN_ID",
    "PREDECESSOR_P320_RUN_ID",
    "PREDECESSOR_P321_RUN_ID",
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
