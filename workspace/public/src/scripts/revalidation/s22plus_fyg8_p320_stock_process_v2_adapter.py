#!/usr/bin/env python3
"""P3.20 stock-observer Process-v2 adapter, host-only.

The outer record remains the reviewed P310 Carrier-v2 record and the
terminal details remain 0x6724-0x6726.  P3.20 is a distinct overlay/decoder
contract: its 76-byte stock payload is ABI-v4 and ends with the observer's
15-byte first-error receipt.  The predecessor P3.19 ABI-v3 payload and
overlay are never reinterpreted here.

This adapter only decodes synthesized or retained bytes.  It does not alter
the common Process-v2 runner, create authority, contact a device, or make a
causal/USB success claim.
"""

from __future__ import annotations

import binascii
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402
import s22plus_fyg8_p310_carrier_model as carrier  # noqa: E402


SCHEMA = "s22plus_fyg8_p320_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
PARENT_SOURCE_CONTRACT_ID = "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
PROFILE = spec.PROFILE
DECODER_ID = "s22plus_fyg8_p320_observer_v4_carrier_v1"
OBSERVER_CONTRACT_ID = "s22plus-fyg8-p320-observer-error-v1"
OBSERVER_CONTRACT_BASE_COMMIT = "b37d630098"
OBSERVER_CONTRACT_COMMIT = OBSERVER_CONTRACT_BASE_COMMIT
LONG_FAMILY = carrier.LONG_FAMILY
UNSAT_FAMILY = carrier.UNSAT_FAMILY
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P320_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "parent=unavailable|w5=unavailable|run=c320f1e0a90b5e6d7c8a9b0c1d2e3f40|"
    "causal=false|usb=false"
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

P320_PAYLOAD_ABI = 4
P319_PAYLOAD_ABI = 3
STATUS_WIDTH = 3
ENCODING = 4
PAYLOAD_SIZE = 76
ENVELOPE_MAGIC = b"MXD5"
ENVELOPE_VERSION = 5
ENVELOPE_SIZE = 128
PAYLOAD_OFFSET = 48
CRC_OFFSET = 124
CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-STOCK-V1\0"
OBSERVER_RECEIPT_OFFSET = 61
OBSERVER_RECEIPT_SIZE = 15

DETAILS = {0x6724: "COMPLETE", 0x6725: "INCOMPLETE", 0x6726: "AMBIGUOUS"}
PROOF_CLASS_BY_STATE = {
    "COMPLETE": "NONCAUSAL_SUCCESS_PATH",
    "INCOMPLETE": "NO_PROOF_EXPERIMENT_PRECONDITION",
    "AMBIGUOUS": "NO_PROOF_OBSERVER",
}
STOCK_DETAIL_COMPLETE = 0x6724
STOCK_DETAIL_INCOMPLETE = 0x6725
STOCK_DETAIL_AMBIGUOUS = 0x6726

FIRST_GENERATION = 106
TERMINAL_GENERATION = 107
FIRST_POSITION = 105
TERMINAL_POSITION = 106
TERMINAL_STAGE = spec.TERMINAL_STAGE
CHECKPOINT_SOURCE = "/proc/last_kmsg"
P319_STOCK_RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
P320_STOCK_RUN_ID = bytes.fromhex("c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
P320_RUN_ID = P320_STOCK_RUN_ID
STOCK_RUN_ID = P320_STOCK_RUN_ID
RUN_ID = P320_STOCK_RUN_ID
RAW_SIZE = 2_097_136

P320_OBSERVER_SOURCE = ANALYSIS / "s22plus_fyg8_p320_observer_contract.py"
P310_MODEL_SOURCE = REVALIDATION / "s22plus_fyg8_p310_carrier_model.py"
P308_SPEC_SOURCE = REVALIDATION / "s22plus_fyg8_p308_telemetry_spec.py"
P310_MODEL_IDENTITY = {
    "size": 24_151,
    "sha256": "bc2db7b1aa1c50ac4085fc9c8c35266a51a7401acb5e193f233961edbdeacf8d",
}
P308_SPEC_IDENTITY = {
    "size": 7_405,
    "sha256": "598ef196058d5ae02a43a6885394b84953b12b0cde3c53dfcf14d9bdf67d1d01",
}
P320_OBSERVER_SOURCE_IDENTITY = {
    "size": 78_289,
    "sha256": "efd4b845fb270187f3e17c7ab3f74c8e0dbeb6d190aab9bb23d500b6fbd716a1",
}
SOURCE_PATHS = {
    "p320_observer_contract": "workspace/public/src/scripts/analysis/s22plus_fyg8_p320_observer_contract.py",
    "p310_carrier_model": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p310_carrier_model.py",
    "p308_telemetry_spec": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p308_telemetry_spec.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)

# The P310 model remains the Carrier authority used by the P319 adapter.  It
# is deliberately exposed under the same name for fixture callers, while the
# P320 overlay/decoder identifiers above remain new.
model = carrier


class DecodeError(ValueError):
    """A P320 Carrier or ABI-v4 payload is not exact."""


class ContractError(DecodeError):
    """A P320 overlay/observer contract is not exact."""


ObserverContractError = ContractError


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    expected: dict[str, Any] | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ContractError(f"{label} is unavailable") from exc
    before_id = (
        before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
        before.st_uid, before.st_gid, before.st_size, before.st_mtime_ns,
        before.st_ctime_ns,
    )
    inside_id = (
        inside.st_dev, inside.st_ino, inside.st_mode, inside.st_nlink,
        inside.st_uid, inside.st_gid, inside.st_size, inside.st_mtime_ns,
        inside.st_ctime_ns,
    )
    after_id = (
        after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
        after.st_uid, after.st_gid, after.st_size, after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or before_id != inside_id
        or before_id != after_id
        or expected is not None and identity(payload) != expected
    ):
        raise ContractError(f"{label} identity differs")
    return payload


def _exec_source(payload: bytes, path: Path, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(payload.decode("utf-8"), str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ContractError(f"bound source execution failed: {path.name}") from exc
    return module


_OBSERVER_CACHE: tuple[dict[str, Any], types.ModuleType] | None = None


def load_observer_contract() -> tuple[types.ModuleType, dict[str, Any]]:
    """Load the execution-critical observer source at its finalized identity."""
    global _OBSERVER_CACHE
    payload = _stable_bytes(
        P320_OBSERVER_SOURCE,
        "P320 observer contract source",
        2 * 1024 * 1024,
        P320_OBSERVER_SOURCE_IDENTITY,
    )
    current = identity(payload)
    if _OBSERVER_CACHE is not None and _OBSERVER_CACHE[0] == current:
        return _OBSERVER_CACHE[1], current
    module = _exec_source(payload, P320_OBSERVER_SOURCE, "p320_observer_contract_bound")
    _OBSERVER_CACHE = (current, module)
    return module, current


def _require_public_observer_layout(observer: types.ModuleType) -> None:
    required = (
        "P319_PAYLOAD_ABI", "P320_PAYLOAD_ABI", "STOCK_PAYLOAD_SIZE",
        "OBSERVER_RECEIPT_OFFSET", "OBSERVER_RECEIPT_SIZE",
        "STOCK_DETAIL_COMPLETE", "STOCK_DETAIL_INCOMPLETE",
        "STOCK_DETAIL_AMBIGUOUS", "ObserverError", "ObserverErrorKind",
        "decode_error_receipt", "encode_error_receipt",
        "validate_stock_payload_v4", "encode_stock_payload_v4",
        "bind_exact_sources", "host_fixture_source",
    )
    if any(not hasattr(observer, name) for name in required):
        raise ContractError("P320 observer public ABI is incomplete")
    exact = {
        "P319_PAYLOAD_ABI": 3,
        "P320_PAYLOAD_ABI": 4,
        "STOCK_PAYLOAD_SIZE": PAYLOAD_SIZE,
        "OBSERVER_RECEIPT_OFFSET": OBSERVER_RECEIPT_OFFSET,
        "OBSERVER_RECEIPT_SIZE": OBSERVER_RECEIPT_SIZE,
        "STOCK_DETAIL_COMPLETE": STOCK_DETAIL_COMPLETE,
        "STOCK_DETAIL_INCOMPLETE": STOCK_DETAIL_INCOMPLETE,
        "STOCK_DETAIL_AMBIGUOUS": STOCK_DETAIL_AMBIGUOUS,
    }
    for name, expected in exact.items():
        if getattr(observer, name) != expected or type(getattr(observer, name)) is not int:
            raise ContractError(f"P320 observer layout differs: {name}")
    if getattr(observer, "P319_PAYLOAD_ABI") == getattr(observer, "P320_PAYLOAD_ABI"):
        raise ContractError("P320 and P319 payload ABIs collide")
    if not callable(observer.decode_error_receipt) or not callable(observer.encode_error_receipt):
        raise ContractError("P320 observer receipt API is not callable")
    if not callable(observer.validate_stock_payload_v4) or not callable(observer.encode_stock_payload_v4):
        raise ContractError("P320 observer payload API is not callable")


def _bind_model_spec_sources() -> dict[str, dict[str, Any]]:
    model = _stable_bytes(P310_MODEL_SOURCE, "P310 Carrier model", 512 * 1024, P310_MODEL_IDENTITY)
    telemetry = _stable_bytes(P308_SPEC_SOURCE, "P308 telemetry spec", 512 * 1024, P308_SPEC_IDENTITY)
    return {
        "p310_carrier_model": identity(model),
        "p308_telemetry_spec": identity(telemetry),
    }


def source_bytes(root: Path | None = None) -> dict[str, bytes]:
    """Read the exact P320 observer and P310/P308 parent source closure."""
    base = ROOT if root is None else root.resolve()
    values: dict[str, bytes] = {}
    expected = {
        "p320_observer_contract": P320_OBSERVER_SOURCE_IDENTITY,
        "p310_carrier_model": P310_MODEL_IDENTITY,
        "p308_telemetry_spec": P308_SPEC_IDENTITY,
    }
    for name, logical_path in SOURCE_PATHS.items():
        path = base / logical_path
        values[name] = _stable_bytes(
            path,
            f"P320 source {name}",
            2 * 1024 * 1024,
            expected.get(name),
        )
    return values


def bind_exact_sources() -> dict[str, Any]:
    """Bind current P320 observer bytes and exact P310 Carrier/P308 spec sources."""
    observer, observer_identity = load_observer_contract()
    _require_public_observer_layout(observer)
    try:
        observer_lineage = observer.bind_exact_sources()
    except Exception as exc:
        raise ContractError("P320 observer source lineage cannot be bound") from exc
    if not isinstance(observer_lineage, dict):
        raise ContractError("P320 observer source lineage is not an object")
    if (
        observer_lineage.get("target") != {
            "model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8",
        }
        or observer_lineage.get("runtime_abi") != 2
        or observer_lineage.get("raw_checkpoint_source") != CHECKPOINT_SOURCE
        or observer_lineage.get("exact_runtime_bound") is not True
        or observer_lineage.get("envelope_source_bound") is not True
        or observer_lineage.get("wiring_source_bound") is not True
    ):
        raise ContractError("P320 observer lineage differs")
    model_spec = _bind_model_spec_sources()
    source_identities = {
        "p320_observer_contract": observer_identity,
        **model_spec,
    }
    return {
        "target": dict(observer_lineage["target"]),
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "observer_contract_id": OBSERVER_CONTRACT_ID,
        "observer_contract_base_commit": OBSERVER_CONTRACT_BASE_COMMIT,
        "observer_contract_commit": OBSERVER_CONTRACT_COMMIT,
        "run_id": STOCK_RUN_ID.hex(),
        "predecessor_run_id_rejected": P319_STOCK_RUN_ID.hex(),
        "observer_public_payload_layout": {
            "payload_abi": P320_PAYLOAD_ABI,
            "predecessor_payload_abi_rejected": P319_PAYLOAD_ABI,
            "payload_size": PAYLOAD_SIZE,
            "receipt_offset": OBSERVER_RECEIPT_OFFSET,
            "receipt_size": OBSERVER_RECEIPT_SIZE,
        },
        "sources": source_identities,
        "observer_lineage": observer_lineage,
        "exact_p310_carrier_model_bound": True,
        "exact_p308_telemetry_spec_bound": True,
        "whole_observer_hash_pinned": True,
    }


bind_lineage = bind_exact_sources


def _observer() -> types.ModuleType:
    observer, _identity = load_observer_contract()
    _require_public_observer_layout(observer)
    return observer


def _json_safe(value: Any) -> Any:
    observer = _observer()
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, getattr(observer, "ObserverError", ())):
        return value.as_dict()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _crc(envelope: bytes) -> int:
    return binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF


def _strict_observer_error(error: Any) -> dict[str, Any]:
    observer = _observer()
    error_type = observer.ObserverError
    if not isinstance(error, error_type):
        raise DecodeError("P320 observer receipt object type differs")
    kind_type = observer.ObserverErrorKind
    if not isinstance(error.kind, kind_type):
        raise DecodeError("P320 observer receipt kind type differs")
    if error.kind.name == "NONE":
        raise DecodeError("P320 observer receipt uses reserved NONE kind")
    if error.flag is not None and type(error.flag) is not str:
        raise DecodeError("P320 observer receipt flag type differs")
    if error.flag is not None and error.flag not in ("-", "c"):
        raise DecodeError("P320 observer receipt flag differs")
    module_max = getattr(observer, "MAX_MODULE_INDEX", None)
    if type(module_max) is not int:
        raise DecodeError("P320 observer module bound is not typed")
    for field in ("active_module_index", "record_length", "record_checksum"):
        if type(getattr(error, field)) is not int:
            raise DecodeError(f"P320 observer receipt {field} type differs")
    if error.active_module_index is not None and not 0 <= error.active_module_index <= module_max:
        raise DecodeError("P320 observer receipt module index differs")
    if not 0 <= error.record_length <= 0xFFFF:
        raise DecodeError("P320 observer receipt length differs")
    if error.sequence is not None and type(error.sequence) is not int:
        raise DecodeError("P320 observer receipt sequence type differs")
    if error.sequence is not None and not 0 <= error.sequence <= (1 << 64) - 1:
        raise DecodeError("P320 observer receipt sequence differs")
    if not 0 <= error.record_checksum <= 0xFF:
        raise DecodeError("P320 observer receipt checksum differs")
    if type(error.length_saturated) is not bool:
        raise DecodeError("P320 observer receipt saturation type differs")
    result = error.as_dict()
    if not isinstance(result, dict):
        raise DecodeError("P320 observer receipt mapping differs")
    for field in (
        "kind_value", "active_module_index", "record_length", "record_checksum",
    ):
        if result[field] is not None and type(result[field]) is not int:
            raise DecodeError(f"P320 observer receipt mapping {field} type differs")
    for field in (
        "flag_known", "module_known", "length_saturated", "sequence_known",
    ):
        if type(result[field]) is not bool:
            raise DecodeError(f"P320 observer receipt mapping {field} type differs")
    if result.get("sequence") is not None and type(result["sequence"]) is not int:
        raise DecodeError("P320 observer receipt mapping sequence type differs")
    return result


def decode_error_receipt(receipt: bytes) -> Any:
    """Decode the exact 15-byte P320 receipt through the bound contract."""
    if type(receipt) is not bytes or len(receipt) != OBSERVER_RECEIPT_SIZE:
        raise DecodeError("P320 observer receipt size differs")
    observer = _observer()
    try:
        error = observer.decode_error_receipt(receipt)
    except Exception as exc:
        raise DecodeError("P320 observer receipt is malformed") from exc
    if error is not None:
        _strict_observer_error(error)
        try:
            if observer.encode_error_receipt(error) != receipt:
                raise DecodeError("P320 observer receipt is not canonical")
        except DecodeError:
            raise
        except Exception as exc:
            raise DecodeError("P320 observer receipt cannot be re-encoded") from exc
    return error


decode_receipt = decode_error_receipt


def _decode_payload_v4(payload: bytes, *, detail: int) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) != PAYLOAD_SIZE:
        raise DecodeError("P320 stock payload size differs")
    observer = _observer()
    try:
        summary = observer.validate_stock_payload_v4(payload)
    except Exception as exc:
        raise DecodeError("P320 stock payload ABI/state is invalid") from exc
    if type(summary) is not dict:
        raise DecodeError("P320 stock payload summary is not an object")
    expected_types = {
        "payload_abi": int,
        "chain_stage": int,
        "chain_complete": bool,
        "chain_ambiguous": bool,
        "state": str,
        "terminal_detail": int,
        "observer_receipt_zero": bool,
        "raw_checkpoint_source": str,
    }
    for field, expected in expected_types.items():
        if field not in summary or type(summary[field]) is not expected:
            raise DecodeError(f"P320 payload summary {field} type differs")
    if (
        summary["payload_abi"] != P320_PAYLOAD_ABI
        or summary["raw_checkpoint_source"] != CHECKPOINT_SOURCE
        or summary["state"] not in set(DETAILS.values())
        or summary["terminal_detail"] != next(
            code for code, name in DETAILS.items() if name == summary["state"]
        )
        or summary["terminal_detail"] != detail
    ):
        raise DecodeError("P320 payload state/detail differs")
    receipt_bytes = payload[OBSERVER_RECEIPT_OFFSET:]
    error = decode_error_receipt(receipt_bytes)
    if (error is None) != summary["observer_receipt_zero"]:
        raise DecodeError("P320 payload receipt-zero projection differs")
    if error is not None and summary["state"] != "AMBIGUOUS":
        raise DecodeError("P320 observer receipt does not imply AMBIGUOUS")
    if summary["state"] in {"COMPLETE", "INCOMPLETE"} and error is not None:
        raise DecodeError("clean P320 terminal carries an observer receipt")
    summary_receipt = summary.get("observer_receipt")
    if error is None:
        if summary_receipt is not None:
            raise DecodeError("P320 clean payload summary carries a receipt")
    else:
        if not isinstance(summary_receipt, type(error)) or summary_receipt != error:
            raise DecodeError("P320 payload summary receipt differs")
    value = dict(summary)
    value["payload_abi"] = P320_PAYLOAD_ABI
    value["observer_receipt"] = (
        None if error is None else _strict_observer_error(error)
    )
    value["observer_receipt_bytes"] = identity(receipt_bytes)
    value["observer_error_present"] = error is not None
    value["terminal_detail"] = detail
    return _json_safe(value)


decode_payload_v4 = _decode_payload_v4
decode_stock_payload_v4 = _decode_payload_v4
validate_payload_v4 = _decode_payload_v4


def _decode_stock_envelope(envelope: bytes, *, detail: int) -> dict[str, Any]:
    if type(envelope) is not bytes or len(envelope) != ENVELOPE_SIZE:
        raise DecodeError("P320 stock envelope size differs")
    if envelope[:4] != ENVELOPE_MAGIC or envelope[4] != ENVELOPE_VERSION:
        raise DecodeError("P320 stock envelope magic/version differs")
    if envelope[43] != ENCODING or envelope[46] != PAYLOAD_SIZE:
        raise DecodeError("P320 stock encoding or payload extent differs")
    if (
        envelope[5:7] + envelope[8:43] + envelope[44:46] + envelope[47:48]
        != bytes(2 + 35 + 2 + 1)
    ):
        raise DecodeError("P320 stock envelope reserved fields differ")
    if envelope[7] != (1 << 5):
        raise DecodeError("P320 stock envelope witness flag differs")
    if struct.unpack_from("<I", envelope, CRC_OFFSET)[0] != _crc(envelope):
        raise DecodeError("P320 stock envelope CRC differs")
    payload = envelope[PAYLOAD_OFFSET:CRC_OFFSET]
    stock = _decode_payload_v4(payload, detail=detail)
    # Retain the P319 stock field semantics around the upgraded tail.
    if payload[56] != STATUS_WIDTH or payload[57] != 1 or payload[58] != 1:
        raise DecodeError("P320 parent/W5/status-width evidence differs")
    if payload[3] & 0xC0:
        raise DecodeError("P320 stock chain reserved bits are set")
    stage = payload[3] & 0x07
    complete = bool(payload[3] & (1 << 3))
    ambiguous = bool(payload[3] & (1 << 4))
    if stage > 4 or (complete and stage != 4) or (complete and ambiguous):
        raise DecodeError("P320 stock chain state is inconsistent")
    if stock["chain_stage"] != stage or stock["chain_complete"] is not complete or stock["chain_ambiguous"] is not ambiguous:
        raise DecodeError("P320 stock chain projection differs")
    expected_mask = 0
    for index, bit in ((10, 0), (11, 1), (12, 2), (13, 3), (59, 4), (60, 5)):
        if payload[index]:
            expected_mask |= 1 << bit
    if payload[1] != expected_mask or payload[1] & (1 << 6):
        raise DecodeError("P320 stock witness mask differs")
    expected_validity = (1 << 3) | (1 << 4) | (1 << 5)
    if payload[12]:
        expected_validity |= 1 << 6
    if payload[13]:
        expected_validity |= 1 << 7
    if payload[2] != expected_validity:
        raise DecodeError("P320 stock validity mask differs")
    if stage >= 1 and payload[11] == 0:
        raise DecodeError("P320 IRQ stage count is absent")
    if stage >= 2 and payload[12] == 0:
        raise DecodeError("P320 status stage count is absent")
    if stage >= 3 and payload[13] == 0:
        raise DecodeError("P320 classification stage count is absent")
    if stage >= 4 and payload[10] == 0:
        raise DecodeError("P320 probe stage count is absent")
    if payload[12] == 0 and any(payload[14:17]):
        raise DecodeError("P320 absent status carries bytes")
    module_results = [struct.unpack_from("<h", payload, 4 + i * 2)[0] for i in range(3)]
    irqs = [struct.unpack_from("<h", payload, 17 + i * 2)[0] for i in range(5)]
    if any(value < 0 for value in irqs):
        raise DecodeError("P320 IRQ value is negative")
    record_count = struct.unpack_from("<H", payload, 35)[0]
    record_bytes = int.from_bytes(payload[37:40], "little")
    first_sequence = int.from_bytes(payload[40:48], "little")
    last_sequence = int.from_bytes(payload[48:56], "little")
    if record_count == 0:
        if record_bytes or first_sequence or last_sequence:
            raise DecodeError("P320 empty record accounting is nonzero")
    elif (
        record_bytes < record_count
        or last_sequence < first_sequence
        or last_sequence - first_sequence + 1 != record_count
    ):
        raise DecodeError("P320 record accounting is not monotonic")
    if record_count > 4096 or record_bytes > 1_048_576:
        raise DecodeError("P320 record accounting exceeds source bounds")
    if stock["state"] == "COMPLETE" and (stage != 4 or any(module_results)):
        raise DecodeError("P320 complete state lacks zero module results")
    value = {
        "encoding": ENCODING,
        "payload_abi": P320_PAYLOAD_ABI,
        "status_width": STATUS_WIDTH,
        "parent_unavailable": True,
        "w5_unavailable": True,
        "chain": ["irq", "initial_status", "classification", "probe"],
        "chain_stage": stage,
        "chain_complete": complete,
        "chain_ambiguous": ambiguous,
        "state": stock["state"],
        "terminal_detail": detail,
        "validity_mask": payload[2],
        "module_results": module_results,
        "module_results_all_zero": not any(module_results),
        "probe_count": payload[10],
        "irq_count": payload[11],
        "initial_status_count": payload[12],
        "classification_form1_count": payload[13],
        "initial_status": list(payload[14:17]),
        "irq": irqs,
        "classification_form1_index": int.from_bytes(payload[27:35], "little"),
        "record_count": record_count,
        "record_bytes": record_bytes,
        "first_sequence": first_sequence,
        "last_sequence": last_sequence,
        "classification_form2_count": payload[59],
        "deferred_status_count": payload[60],
        "observer_receipt": stock["observer_receipt"],
        "observer_receipt_bytes": stock["observer_receipt_bytes"],
        "observer_error_present": stock["observer_error_present"],
        "envelope_sha256": sha256(envelope),
    }
    return _json_safe(value)


def _decode_stock_carrier(
    record: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes | None,
) -> dict[str, Any]:
    if type(record) is not bytes or len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P320 Carrier record size differs")
    if expected_profile != PROFILE:
        raise DecodeError("P320 Carrier profile is not bound to E2")
    if expected_run_id is None:
        expected_run_id = STOCK_RUN_ID
    if expected_run_id != STOCK_RUN_ID:
        raise DecodeError("P320 Carrier run ID is not bound to the P320 run")
    try:
        decoded = carrier.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    if decoded.get("slot_status") != ["valid", "valid"]:
        raise DecodeError("P320 Carrier slots are not both CRC-valid")
    slots = decoded.get("valid_slots")
    if type(slots) is not list or len(slots) != 2 or any(type(item) is not dict for item in slots):
        raise DecodeError("P320 Carrier valid-slot shape differs")
    rows = {item.get("generation"): item for item in slots}
    if set(rows) != {FIRST_GENERATION, TERMINAL_GENERATION}:
        raise DecodeError("P320 Carrier generations differ")
    first = rows[FIRST_GENERATION]
    terminal = rows[TERMINAL_GENERATION]
    first_position = spec.POSITIONS[FIRST_POSITION]
    terminal_position = spec.POSITIONS[TERMINAL_POSITION]
    if (
        first.get("slot_id") != 0
        or first.get("stage") != first_position.stage
        or first.get("item_index") != first_position.item_index
        or first.get("outcome") != carrier.OUTCOME_PROGRESS
        or first.get("detail") != 0x0DA3
        or terminal.get("slot_id") != 1
        or terminal.get("stage") != terminal_position.stage
        or terminal.get("item_index") != terminal_position.item_index
        or terminal.get("outcome") != carrier.OUTCOME_FAILURE
        or terminal.get("detail") not in DETAILS
        or first.get("payload_kind") != carrier.PAYLOAD_RAW_EXCERPT
        or terminal.get("payload_kind") != carrier.PAYLOAD_RAW_EXCERPT
        or type(first.get("payload")) is not bytes
        or type(terminal.get("payload")) is not bytes
        or len(first["payload"]) != 64
        or len(terminal["payload"]) != 64
    ):
        raise DecodeError("P320 Carrier slot semantics differ")
    stock = _decode_stock_envelope(
        first["payload"] + terminal["payload"],
        detail=terminal["detail"],
    )
    return {
        "profile": decoded["profile"],
        "run_id": decoded["run_id"],
        "header_crc_valid": True,
        "slot_status": list(decoded["slot_status"]),
        "valid_slots": slots,
        "active": terminal,
        "fallback_used": False,
        "terminal_success": False,
        "stock": stock,
    }


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    """Decode one exact P310 Carrier record containing a P320 stock envelope."""
    if expected_profile != PROFILE:
        raise DecodeError("P320 Carrier profile is not bound to E2")
    if expected_run_id is not None and expected_run_id != STOCK_RUN_ID:
        raise DecodeError("P320 Carrier run ID is not bound to the P320 run")
    bound_run_id = STOCK_RUN_ID if expected_run_id is None else expected_run_id
    return _json_safe({
        "schema": SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": expected_profile,
        "carrier": _decode_stock_carrier(
            record,
            expected_profile=expected_profile,
            expected_run_id=bound_run_id,
        ),
    })


def _base_classification(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != STOCK_RUN_ID:
        raise DecodeError("P320 Carrier classification identity differs")
    try:
        base = carrier.classify_observation(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    shape_valid = (
        base.get("long_record_count") == 1
        and base.get("exact_record_count") == 1
        and base.get("unsat_count") == 0
        and base.get("foreign_count") == 0
        and base.get("minimum_candidate_boots") == 1
        and base.get("integrity_issue") is False
    )
    if not shape_valid:
        base["records"] = []
        base["classification"] = "P320_STOCK_WITNESS_BASE_SHAPE_FAILURE"
        base["accepted"] = False
        base["telemetry_count"] = 0
        base["contradiction_count"] = 0
        base["stock_result_count"] = 0
        return base
    attached: list[dict[str, Any]] = []
    for row in base.get("records", ()):
        if not isinstance(row, dict) or type(row.get("observer_offset")) is not int:
            raise DecodeError("P320 Carrier classifier record shape differs")
        start = row["observer_offset"]
        raw = payload[start : start + carrier.LONG_RECORD_SIZE]
        attached_row = dict(row)
        try:
            attached_row["p320_stock"] = _decode_stock_carrier(
                raw,
                expected_profile=expected_profile,
                expected_run_id=expected_run_id,
            )
        except DecodeError as exc:
            base.setdefault("integrity_issues", []).append("p320-stock-envelope-shape")
            base["integrity_issue"] = True
            attached_row["p320_stock_error"] = str(exc)
        attached.append(attached_row)
    base["records"] = attached
    states = {
        row.get("p320_stock", {}).get("stock", {}).get("state")
        for row in attached
        if isinstance(row, dict)
    }
    complete = sum(state == "COMPLETE" for state in states)
    if base.get("integrity_issue"):
        base["classification"] = "AMBIGUOUS_INTEGRITY_FAILURE"
        base["accepted"] = False
    elif len(attached) != 1:
        base["classification"] = "P320_STOCK_WITNESS_MULTIPLICITY"
        base["accepted"] = False
    elif states == {"COMPLETE"}:
        base["classification"] = "P320_STOCK_WITNESS_COMPLETE"
        base["accepted"] = True
    elif states == {"INCOMPLETE"}:
        base["classification"] = "P320_STOCK_WITNESS_INCOMPLETE_NO_PROOF"
        base["accepted"] = False
    elif states == {"AMBIGUOUS"}:
        base["classification"] = "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
        base["accepted"] = False
    else:
        base["classification"] = "AMBIGUOUS_INTEGRITY_FAILURE"
        base["accepted"] = False
    base["telemetry_count"] = 1 if base.get("accepted") is True else 0
    base["contradiction_count"] = 0 if base.get("accepted") is True else 1
    base["stock_result_count"] = len(attached)
    return base


def _decoded_stock_state(value: dict[str, Any]) -> str:
    records = value.get("records")
    if type(records) is not list or len(records) != 1 or type(records[0]) is not dict:
        raise DecodeError("P320 classification does not contain one Carrier record")
    stock_container = records[0].get("p320_stock")
    if type(stock_container) is not dict:
        raise DecodeError("P320 classification does not contain stock payload")
    stock = stock_container.get("stock")
    if type(stock) is not dict or stock.get("state") not in PROOF_CLASS_BY_STATE:
        raise DecodeError("P320 stock state is unsupported")
    return stock["state"]


def _proof_class_for_value(value: dict[str, Any]) -> str:
    if type(value) is not dict:
        return "NO_PROOF_OBSERVER"
    if (
        value.get("long_record_count") != 1
        or value.get("exact_record_count") != 1
        or value.get("unsat_count") != 0
        or value.get("foreign_count") != 0
        or value.get("minimum_candidate_boots") != 1
        or value.get("integrity_issue") is True
        or type(value.get("accepted")) is not bool
    ):
        return "NO_PROOF_OBSERVER"
    try:
        state = _decoded_stock_state(value)
    except DecodeError:
        return "NO_PROOF_OBSERVER"
    stock = value["records"][0]["p320_stock"]["stock"]
    for field in ("chain_complete", "chain_ambiguous"):
        if type(stock.get(field)) is not bool:
            return "NO_PROOF_OBSERVER"
    for field in ("payload_abi", "chain_stage", "terminal_detail"):
        if type(stock.get(field)) is not int:
            return "NO_PROOF_OBSERVER"
    if state == "COMPLETE" and value.get("accepted") is True:
        return "NONCAUSAL_SUCCESS_PATH"
    if state == "INCOMPLETE" and value.get("accepted") is False:
        return "NO_PROOF_EXPERIMENT_PRECONDITION"
    # Any observer receipt or ambiguous chain state is observer no-proof.
    return "NO_PROOF_OBSERVER"


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    """Derive the noncausal proof class from the decoded P320 state."""
    state = _decoded_stock_state(value)
    result = _proof_class_for_value(value)
    if result != PROOF_CLASS_BY_STATE[state]:
        raise DecodeError("P320 decoded state predicates do not admit its proof class")
    if "proof_class" in value and value["proof_class"] != result:
        raise DecodeError("P320 proof class field differs")
    if expected is not None and result != expected:
        raise DecodeError("P320 proof class does not match expected state")
    return result


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = STOCK_RUN_ID,
) -> dict[str, Any]:
    """Classify one exact retained raw snapshot without causal promotion."""
    if type(payload) is not bytes or len(payload) != RAW_SIZE:
        raise DecodeError("P320 observer payload must be one exact retained raw")
    value = _base_classification(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    value.update({
        "schema": SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": expected_profile,
        "run_id": expected_run_id.hex(),
        "acm_supplemental": True,
        "acm_required_for_acceptance": False,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
    })
    value["proof_class"] = _proof_class_for_value(value)
    return _json_safe(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = STOCK_RUN_ID,
) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) != RAW_SIZE:
        raise DecodeError("P320 baseline size differs")
    try:
        value = carrier.classify_clean_baseline(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    if value.get("classification") != "CLEAN_BASELINE" or value.get("baseline_clean") is not True:
        raise DecodeError("P320 baseline is not clean")
    return {
        "classification": "ZERO_AMBIGUOUS",
        "accepted": False,
        "records": [],
        "baseline_size": len(payload),
        "baseline_clean": True,
        "integrity_issue": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }


def _base_payload(*, state: str) -> bytes:
    if state not in DETAILS.values():
        raise DecodeError("P320 fixture state differs")
    payload = bytearray(PAYLOAD_SIZE)
    payload[0] = P319_PAYLOAD_ABI
    payload[1] = 0x3F
    payload[2] = 0xF8
    payload[3] = {
        "COMPLETE": 0x2C,
        "INCOMPLETE": 0x20,
        "AMBIGUOUS": 0x34,
    }[state]
    payload[10:14] = bytes((1, 1, 1, 1))
    payload[14:17] = bytes((1, 2, 3))
    for index, value in enumerate((22, 23, 26, 0, 0)):
        struct.pack_into("<H", payload, 17 + index * 2, value)
    struct.pack_into("<Q", payload, 27, 7)
    struct.pack_into("<H", payload, 35, 1)
    payload[37:40] = (1).to_bytes(3, "little")
    struct.pack_into("<Q", payload, 40, 1)
    struct.pack_into("<Q", payload, 48, 1)
    payload[56:61] = bytes((STATUS_WIDTH, 1, 1, 2, 1))
    return bytes(payload)


def _envelope_from_payload(payload: bytes) -> bytes:
    if type(payload) is not bytes or len(payload) != PAYLOAD_SIZE:
        raise DecodeError("P320 fixture payload size differs")
    envelope = bytearray(ENVELOPE_SIZE)
    envelope[:4] = ENVELOPE_MAGIC
    envelope[4] = ENVELOPE_VERSION
    envelope[7] = 1 << 5
    envelope[43] = ENCODING
    envelope[46] = PAYLOAD_SIZE
    envelope[PAYLOAD_OFFSET:CRC_OFFSET] = payload
    struct.pack_into("<I", envelope, CRC_OFFSET, _crc(bytes(envelope)))
    return bytes(envelope)


def _carrier_record_from_envelope(
    envelope: bytes, *, detail: int, run_id: bytes = STOCK_RUN_ID
) -> bytes:
    if type(envelope) is not bytes or len(envelope) != ENVELOPE_SIZE:
        raise DecodeError("P320 fixture envelope size differs")
    if detail not in DETAILS:
        raise DecodeError("P320 fixture terminal detail differs")
    if type(run_id) is not bytes or len(run_id) != carrier.RUN_ID_SIZE or not any(run_id):
        raise DecodeError("P320 fixture Carrier run ID differs")
    header = carrier._header(PROFILE, run_id)  # noqa: SLF001
    first_position = spec.POSITIONS[FIRST_POSITION]
    terminal_position = spec.POSITIONS[TERMINAL_POSITION]
    first = carrier.Slot(
        0,
        FIRST_GENERATION,
        first_position.stage,
        carrier.OUTCOME_PROGRESS,
        first_position.item_index,
        0x0DA3,
        carrier.PAYLOAD_RAW_EXCERPT,
        envelope[:64],
    )
    terminal = carrier.Slot(
        1,
        TERMINAL_GENERATION,
        terminal_position.stage,
        carrier.OUTCOME_FAILURE,
        terminal_position.item_index,
        detail,
        carrier.PAYLOAD_RAW_EXCERPT,
        envelope[64:],
    )
    record = header + carrier._encode_slot(header, first) + carrier._encode_slot(header, terminal)  # noqa: SLF001
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P320 fixture Carrier size differs")
    return record


def observer_error_fixture() -> Any:
    """Return one deterministic ABI-v4 WITNESS receipt for C/Python parity."""
    observer = _observer()
    return observer.make_observer_error(
        observer.ObserverErrorKind.WITNESS,
        record=b"6,10,25,c;observer-failure\n",
        flag="c",
        active_module_index=72,
        sequence=10,
    )


_DEFAULT_OBSERVER_ERROR = object()


def encode_fixture(
    *,
    state: str = "COMPLETE",
    observer_error: Any = _DEFAULT_OBSERVER_ERROR,
) -> bytes:
    """Build one full P310 Carrier fixture with a P320 ABI-v4 payload."""
    if state not in DETAILS.values():
        raise DecodeError("P320 fixture state differs")
    if observer_error is _DEFAULT_OBSERVER_ERROR:
        observer_error = observer_error_fixture() if state == "AMBIGUOUS" else None
    elif observer_error is False:
        observer_error = None
    if observer_error is not None and state != "AMBIGUOUS":
        state = "AMBIGUOUS"
    observer = _observer()
    payload = observer.encode_stock_payload_v4(
        _base_payload(state=state), observer_error
    )
    if type(payload) is not bytes or len(payload) != PAYLOAD_SIZE:
        raise DecodeError("P320 observer encoder returned a noncanonical payload")
    # An observer error canonicalizes the terminal state to AMBIGUOUS.  The
    # Carrier detail must follow that public terminal mapping.
    summary = _decode_payload_v4(
        payload,
        detail=STOCK_DETAIL_AMBIGUOUS if observer_error is not None else DETAILS_INV[state],
    )
    del summary
    detail = STOCK_DETAIL_AMBIGUOUS if observer_error is not None else DETAILS_INV[state]
    return _carrier_record_from_envelope(
        _envelope_from_payload(payload), detail=detail
    )


DETAILS_INV = {name: code for code, name in DETAILS.items()}


def _full_fixture(
    *,
    state: str = "COMPLETE",
    observer_error: Any = _DEFAULT_OBSERVER_ERROR,
) -> bytes:
    record = encode_fixture(state=state, observer_error=observer_error)
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P320 fixture Carrier record size differs")
    return bytes(RAW_SIZE - len(record)) + record


def _full_c_fixture(payload: bytes, *, detail: int) -> bytes:
    """Embed a payload obtained from the observer C fixture into Carrier."""
    return bytes(RAW_SIZE - carrier.LONG_RECORD_SIZE) + _carrier_record_from_envelope(
        _envelope_from_payload(payload), detail=detail
    )


def _mutate_terminal_detail(raw: bytes, detail: int) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != RAW_SIZE
        or type(detail) is not int
        or not 0 <= detail <= 0xFFFF
    ):
        raise DecodeError("P320 terminal-detail mutation input differs")
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = bytearray(raw[offset:])
    body_size = carrier.SLOT_SIZE - 4
    slot_offset = carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE
    body = list(carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size]))
    body[7] = detail
    encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
    record[slot_offset:slot_offset + body_size] = encoded
    struct.pack_into(
        "<I",
        record,
        slot_offset + body_size,
        carrier._slot_crc(bytes(record[:carrier.LONG_HEADER_SIZE]), 1, encoded),  # noqa: SLF001
    )
    return raw[:offset] + bytes(record) + raw[offset + carrier.LONG_RECORD_SIZE:]


def _mutate_payload(raw: bytes, mutate) -> bytes:
    if type(raw) is not bytes or len(raw) != RAW_SIZE:
        raise DecodeError("P320 payload mutation input differs")
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = bytearray(raw[offset:])
    body_size = carrier.SLOT_SIZE - 4
    envelope = bytearray(
        carrier.SLOT_BODY_STRUCT.unpack(
            record[carrier.LONG_HEADER_SIZE:carrier.LONG_HEADER_SIZE + body_size]
        )[-1][:64]
        + carrier.SLOT_BODY_STRUCT.unpack(
            record[carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE:carrier.LONG_HEADER_SIZE + 2 * carrier.SLOT_SIZE - 4]
        )[-1][:64]
    )
    mutate(envelope)
    struct.pack_into("<I", envelope, CRC_OFFSET, _crc(bytes(envelope)))
    for slot_id in (0, 1):
        slot_offset = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        body = list(carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size]))
        body[-1] = bytes(envelope[slot_id * 64:(slot_id + 1) * 64])
        encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
        record[slot_offset:slot_offset + body_size] = encoded
        struct.pack_into(
            "<I",
            record,
            slot_offset + body_size,
            carrier._slot_crc(bytes(record[:carrier.LONG_HEADER_SIZE]), slot_id, encoded),  # noqa: SLF001
        )
    return raw[:offset] + bytes(record) + raw[offset + carrier.LONG_RECORD_SIZE:]


def validate_contract(value: Any) -> dict[str, Any]:
    """Validate the distinct P320 overlay metadata without granting authority."""
    if type(value) is not dict:
        raise ContractError("P320 overlay contract is not an object")
    required = {
        "userspace_overlay_contract_id", "decoder", "policy_id", "profile",
        "source_contract_id", "observer_contract_id", "payload_abi",
        "observer_receipt_size", "causal_result_allowed", "candidate_success",
    }
    if not required <= set(value):
        raise ContractError("P320 overlay contract fields are incomplete")
    if (
        value["userspace_overlay_contract_id"] != OVERLAY_CONTRACT_ID
        or value["userspace_overlay_contract_id"] == P319_OVERLAY_CONTRACT_ID
        or value["decoder"] != DECODER_ID
        or value["policy_id"] != POLICY_ID
        or value["profile"] != PROFILE
        or value["source_contract_id"] != PARENT_SOURCE_CONTRACT_ID
        or value["observer_contract_id"] != OBSERVER_CONTRACT_ID
        or type(value["payload_abi"]) is not int
        or value["payload_abi"] != P320_PAYLOAD_ABI
        or type(value["observer_receipt_size"]) is not int
        or value["observer_receipt_size"] != OBSERVER_RECEIPT_SIZE
        or value["causal_result_allowed"] is not False
        or value["candidate_success"] is not False
    ):
        raise ContractError("P320 overlay contract identity differs")
    return _json_safe(value)


def acceptance_fixture() -> dict[str, Any]:
    """Return a non-authorizing Process-v2 acceptance description."""
    artifact = {
        "path": "p320-stock-observer-v4-fixture",
        "size": 1,
        "sha256": "0" * 64,
    }
    return {
        "kind": "retained_e1_latest_stage_multiboot_after_rollback",
        "source": CHECKPOINT_SOURCE,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "run_id": STOCK_RUN_ID.hex(),
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "long_family_hex": LONG_FAMILY.hex(),
        "unsat_family_hex": UNSAT_FAMILY.hex(),
        "terminal_stage": TERMINAL_STAGE,
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "observer_contract": {
            "id": OBSERVER_CONTRACT_ID,
            "base_commit": OBSERVER_CONTRACT_BASE_COMMIT,
            "commit": OBSERVER_CONTRACT_COMMIT,
            "payload_abi": P320_PAYLOAD_ABI,
            "receipt_offset": OBSERVER_RECEIPT_OFFSET,
            "receipt_size": OBSERVER_RECEIPT_SIZE,
        },
        "contract": {
            "candidate_static": artifact,
            "run_manifest": artifact,
            "static_check": artifact,
        },
        "causal_result_allowed": False,
        "candidate_success": False,
    }


def validate_acceptance_item(item: Any) -> dict[str, Any]:
    """Validate the P320 acceptance identity used by a future runner."""
    if type(item) is not dict:
        raise ContractError("P320 acceptance item is not an object")
    required = {
        "kind", "source", "decoder", "policy_id", "profile",
        "run_id", "source_contract_id", "userspace_overlay_contract_id",
        "long_family_hex", "unsat_family_hex", "terminal_stage",
        "minimum_success_count", "clean_baseline_required", "observer_contract",
        "contract", "causal_result_allowed", "candidate_success",
    }
    if not required <= set(item):
        raise ContractError("P320 acceptance fields are incomplete")
    if (
        item["kind"] != "retained_e1_latest_stage_multiboot_after_rollback"
        or item["source"] != CHECKPOINT_SOURCE
        or item["decoder"] != DECODER_ID
        or item["policy_id"] != POLICY_ID
        or item["profile"] != PROFILE
        or item["run_id"] != STOCK_RUN_ID.hex()
        or item["source_contract_id"] != PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != OVERLAY_CONTRACT_ID
        or item["userspace_overlay_contract_id"] == P319_OVERLAY_CONTRACT_ID
        or item["long_family_hex"] != LONG_FAMILY.hex()
        or item["unsat_family_hex"] != UNSAT_FAMILY.hex()
        or type(item["terminal_stage"]) is not int
        or item["terminal_stage"] != TERMINAL_STAGE
        or type(item["minimum_success_count"]) is not int
        or item["minimum_success_count"] != 1
        or item["clean_baseline_required"] is not True
        or item["causal_result_allowed"] is not False
        or item["candidate_success"] is not False
    ):
        raise ContractError("P320 acceptance identity differs")
    observer = item["observer_contract"]
    if type(observer) is not dict or (
        observer.get("id") != OBSERVER_CONTRACT_ID
        or observer.get("base_commit") != OBSERVER_CONTRACT_BASE_COMMIT
        or observer.get("commit") != OBSERVER_CONTRACT_COMMIT
        or observer.get("payload_abi") != P320_PAYLOAD_ABI
        or observer.get("receipt_offset") != OBSERVER_RECEIPT_OFFSET
        or observer.get("receipt_size") != OBSERVER_RECEIPT_SIZE
    ):
        raise ContractError("P320 observer acceptance identity differs")
    if type(item["contract"]) is not dict:
        raise ContractError("P320 acceptance contract is not an object")
    return _json_safe(item)


def _assert_public_types(value: dict[str, Any]) -> None:
    """Reject bool-as-int and other type drift in the adapter result."""
    for field in (
        "accepted", "integrity_issue", "causal_result_allowed",
        "candidate_success", "mux_result_claimable", "host_silent_claimable",
        "acm_supplemental", "acm_required_for_acceptance",
    ):
        if field in value and type(value[field]) is not bool:
            raise DecodeError(f"P320 result {field} type differs")
    for field in (
        "long_record_count", "exact_record_count", "unsat_count", "foreign_count",
        "minimum_candidate_boots", "telemetry_count", "contradiction_count",
        "stock_result_count",
    ):
        if field in value and type(value[field]) is not int:
            raise DecodeError(f"P320 result {field} type differs")


def audit() -> dict[str, Any]:
    """Run the bounded P320 adapter/fixture audit and return its receipt."""
    lineage = bind_exact_sources()
    contract = validate_contract({
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "observer_contract_id": OBSERVER_CONTRACT_ID,
        "payload_abi": P320_PAYLOAD_ABI,
        "observer_receipt_size": OBSERVER_RECEIPT_SIZE,
        "causal_result_allowed": False,
        "candidate_success": False,
    })
    acceptance = validate_acceptance_item(acceptance_fixture())
    results: dict[str, dict[str, Any]] = {}
    for state in ("COMPLETE", "INCOMPLETE", "AMBIGUOUS"):
        raw = _full_fixture(state=state)
        decoded = classify_observation(raw)
        _assert_public_types(decoded)
        expected_class = PROOF_CLASS_BY_STATE[state]
        if proof_class(decoded) != expected_class or decoded["proof_class"] != expected_class:
            raise DecodeError(f"P320 fixture proof class differs: {state}")
        if decoded["accepted"] is not (state == "COMPLETE"):
            raise DecodeError(f"P320 fixture acceptance differs: {state}")
        stock = decoded["records"][0]["p320_stock"]["stock"]
        if state in {"COMPLETE", "INCOMPLETE"} and stock["observer_receipt"] is not None:
            raise DecodeError("P320 clean fixture carries an observer receipt")
        results[state] = {
            "classification": decoded["classification"],
            "proof_class": decoded["proof_class"],
            "accepted": decoded["accepted"],
            "record_sha256": sha256(raw),
            "receipt": stock["observer_receipt"],
        }

    error_raw = _full_fixture(state="AMBIGUOUS")
    error_decoded = classify_observation(error_raw)
    error_stock = error_decoded["records"][0]["p320_stock"]["stock"]
    if (
        error_decoded["proof_class"] != "NO_PROOF_OBSERVER"
        or error_decoded["accepted"] is not False
        or error_stock["observer_receipt"] is None
        or error_decoded["causal_result_allowed"] is not False
        or error_decoded["candidate_success"] is not False
        or error_decoded["mux_result_claimable"] is not False
        or error_decoded["host_silent_claimable"] is not False
    ):
        raise DecodeError("P320 observer-error AMBIGUOUS was promoted")

    abi3 = bytearray(_base_payload(state="COMPLETE"))
    observer = _observer()
    try:
        observer.validate_stock_payload_v4(bytes(abi3))
    except Exception:
        abi3_rejected = True
    else:
        abi3_rejected = False
    if not abi3_rejected:
        raise DecodeError("P319 ABI3 payload was accepted by P320 observer")

    malformed: dict[str, bool] = {}
    malformed["bad_receipt_reserved_flags"] = _rejected_receipt(
        bytes((int(observer.ObserverErrorKind.WITNESS), 0x80, 0, 0xFF)) + bytes(11)
    )
    malformed["bad_receipt_flag"] = _rejected_receipt(
        bytes((int(observer.ObserverErrorKind.WITNESS), 0x04, ord("x"), 0xFF)) + bytes(11)
    )
    malformed["bad_receipt_module"] = _rejected_receipt(
        bytes((int(observer.ObserverErrorKind.WITNESS), 0x02, 0, 0xFF)) + bytes(11)
    )
    malformed["bad_detail_state"] = _rejected_raw(
        _mutate_terminal_detail(_full_fixture(state="COMPLETE"), STOCK_DETAIL_INCOMPLETE)
    )
    malformed["legacy_detail_namespace"] = _rejected_raw(
        _mutate_terminal_detail(_full_fixture(state="COMPLETE"), 0x6020)
    )
    malformed["bad_payload_receipt_relation"] = _rejected_raw(
        _mutate_payload(_full_fixture(state="COMPLETE"), lambda envelope: envelope.__setitem__(PAYLOAD_OFFSET + OBSERVER_RECEIPT_OFFSET, 1))
    )
    if not all(malformed.values()):
        raise DecodeError("P320 hostile malformed/reserved fixture was accepted")
    return {
        "schema": SCHEMA,
        "verdict": "PASS_P320_STOCK_PROCESS_V2_ADAPTER_H0",
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "p319_overlay_contract_id": P319_OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "payload_abi": P320_PAYLOAD_ABI,
        "p319_payload_abi_rejected": abi3_rejected,
        "observer_receipt": {"offset": OBSERVER_RECEIPT_OFFSET, "size": OBSERVER_RECEIPT_SIZE},
        "lineage": lineage,
        "contract": contract,
        "acceptance": acceptance,
        "fixtures": results,
        "observer_error_ambiguous_no_proof": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "malformed_rejected": malformed,
        "device_contact": False,
        "verified": True,
    }


def _rejected_receipt(receipt: bytes) -> bool:
    try:
        decode_error_receipt(receipt)
    except (ContractError, DecodeError, ValueError, TypeError):
        return True
    return False


def _rejected_raw(raw: bytes) -> bool:
    try:
        value = classify_observation(raw)
    except (ContractError, DecodeError, ValueError, TypeError):
        return True
    return (
        value.get("accepted") is False
        and value.get("proof_class") == "NO_PROOF_OBSERVER"
        and value.get("integrity_issue") is True
    )


def main() -> int:
    try:
        value = audit()
    except (ContractError, DecodeError, ValueError, TypeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
