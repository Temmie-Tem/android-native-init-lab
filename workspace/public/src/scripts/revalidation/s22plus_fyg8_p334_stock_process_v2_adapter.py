#!/usr/bin/env python3
"""P3.34 Process-v2 adapter for the first console return receipt."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import struct
import types
from typing import Any

import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p334_first_read_rc_runtime as return_runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 10_410,
    "sha256": "4af184bb2a6003e8dca9159b2c430721fe0843ece6dec8749032de26aa3d5393",
}
P333_PREDECESSOR_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_PREDECESSOR_RUN_ID = bytes.fromhex(P333_PREDECESSOR_RUN_ID_HEX)
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_RUN_ID = bytes.fromhex(P334_RUN_ID_HEX)

P334_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p334-first-console-return-v1"
P334_DECODER_ID = "s22plus_fyg8_p334_first_console_return_v1"
P334_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p334-first-read-rc-acm-observer-v1"
P334_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P334_STOCK_OBSERVER_V1|protocol=p334-first-console-return-v1|"
    "entry-diagnostic=stage0,before-each-console-call|"
    "first-console-return=checkpoint-detail-b000-errno,bfff-sentinel|"
    "resident=sessions-2,reconnects-0,fixed-p330-commands,same-tty|"
    "transport=one-open-fd,no-close-reopen|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P334_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P334_POLICY_ID = hashlib.sha256(P334_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.33 adapter or fresh P3.34 binding differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _load() -> types.ModuleType:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.33 adapter source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise AdapterIdentityError("P3.33 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p333_adapter_bound_for_p334")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.33 adapter source failed to load") from exc
    if getattr(module, "P333_RUN_ID_HEX", None) != P333_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.33 adapter binding differs")
    return module


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for name, value in vars(module).items():
            if name.startswith("_P") and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


_P333 = _load()
for _module in _modules(_P333):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P333_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P334_RUN_ID)
        elif _value == P333_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P334_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P333_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P334_RUN_ID
                    _changed = True
                elif _default == P333_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P334_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults

SCHEMA = "s22plus_fyg8_p334_stock_process_v2_adapter_v1"
for _module in _modules(_P333):
    for _name, _value in {
        "SCHEMA": SCHEMA,
        "OVERLAY_CONTRACT_ID": P334_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P334_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P334_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P334_POLICY_PREIMAGE,
        "POLICY_ID": P334_POLICY_ID,
        "RUN_ID": P334_RUN_ID,
        "STOCK_RUN_ID": P334_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_base = getattr(_P333, "_base", None) or getattr(_P333, "_P331", None)
for _module in _modules(_P333):
    if hasattr(_module, "_STALE_IDS"):
        _module._STALE_IDS = tuple(  # noqa: SLF001
            dict.fromkeys((*_module._STALE_IDS, P333_PREDECESSOR_RUN_ID))  # noqa: SLF001
        )

_ORIGINAL_PUBLIC = _P333._public


def _public(value: Any) -> Any:
    result = _ORIGINAL_PUBLIC(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": P334_OVERLAY_CONTRACT_ID,
            "decoder": P334_DECODER_ID,
            "policy_id": P334_POLICY_ID,
            "run_id": P334_RUN_ID_HEX,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "authenticated_exec": True,
            "authentication_required": True,
            "caller_selected_command": False,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_p330_commands": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_detail_prefix": return_runtime.P334_DETAIL_PREFIX,
            "first_console_return_detail_sentinel": return_runtime.P334_DETAIL_SENTINEL,
            "first_read_attribution_requires_stage0_without_stage1": True,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in {
            "P333_STOCK_ENCODER_FAILURE",
            "P331_STOCK_ENCODER_FAILURE",
            "P330_STOCK_ENCODER_FAILURE",
        }:
            item[key] = "P334_STOCK_ENCODER_FAILURE"
    return item


_P333._public = _public
for _name in getattr(_P333, "__all__", ()):
    globals()[_name] = getattr(_P333, _name)

SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 10_410,
    "sha256": "4af184bb2a6003e8dca9159b2c430721fe0843ece6dec8749032de26aa3d5393",
}
OVERLAY_CONTRACT_ID = P334_OVERLAY_CONTRACT_ID
DECODER_ID = P334_DECODER_ID
OBSERVER_CONTRACT_ID = P334_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P334_POLICY_PREIMAGE
POLICY_ID = P334_POLICY_ID
RUN_ID = P334_RUN_ID
STOCK_RUN_ID = P334_RUN_ID
P333_RUN_ID = P334_RUN_ID
P333_RUN_ID_HEX = P334_RUN_ID_HEX
P334_ADAPTER_SOURCE = Path(__file__).resolve()
P333_ADAPTER_SOURCE = P334_ADAPTER_SOURCE


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P333.acceptance_fixture())
    predecessors = list(value.get("predecessor_run_ids_rejected", []))
    if P333_PREDECESSOR_RUN_ID_HEX not in predecessors:
        predecessors.append(P333_PREDECESSOR_RUN_ID_HEX)
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P334_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id_rejected": P333_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": predecessors,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_detail_prefix": return_runtime.P334_DETAIL_PREFIX,
            "first_console_return_detail_sentinel": return_runtime.P334_DETAIL_SENTINEL,
            "first_read_attribution_requires_stage0_without_stage1": True,
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p334-first-console-return-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P333.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P334_RUN_ID_HEX,
            "predecessor_run_id_rejected": P333_PREDECESSOR_RUN_ID_HEX,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_detail_prefix": return_runtime.P334_DETAIL_PREFIX,
            "first_console_return_detail_sentinel": return_runtime.P334_DETAIL_SENTINEL,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P333.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P334_STOCK_PROCESS_V2_ADAPTER_H0_FIRST_CONSOLE_RETURN",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P334_RUN_ID_HEX,
            "predecessor_run_id": P333_PREDECESSOR_RUN_ID_HEX,
            "encoder_failure_class": "P334_STOCK_ENCODER_FAILURE",
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_detail_prefix": return_runtime.P334_DETAIL_PREFIX,
            "first_console_return_detail_sentinel": return_runtime.P334_DETAIL_SENTINEL,
            "first_read_attribution_requires_stage0_without_stage1": True,
            "lineage": bind_exact_sources(),
        }
    )
    return value


_ORIGINAL_CLASSIFY_OBSERVATION = classify_observation
_ORIGINAL_CLASSIFY_CLEAN_BASELINE = classify_clean_baseline


def _replace_terminal_detail(
    payload: bytes, offset: int, detail: int
) -> bytes:
    record = bytearray(payload[offset : offset + carrier.LONG_RECORD_SIZE])
    header = bytes(record[: carrier.LONG_HEADER_SIZE])
    slot_offset = carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE
    body_size = carrier.SLOT_BODY_STRUCT.size
    body = list(
        carrier.SLOT_BODY_STRUCT.unpack(
            record[slot_offset : slot_offset + body_size]
        )
    )
    body[7] = detail
    encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
    record[slot_offset : slot_offset + body_size] = encoded
    struct.pack_into(
        "<I",
        record,
        slot_offset + body_size,
        carrier._slot_crc(header, 1, encoded),  # noqa: SLF001
    )
    return (
        payload[:offset]
        + bytes(record)
        + payload[offset + carrier.LONG_RECORD_SIZE :]
    )


def _return_receipt(payload: bytes) -> tuple[dict[str, Any], int]:
    if type(payload) is not bytes:
        raise AdapterIdentityError("P3.34 raw observation is not bytes")
    matches: list[tuple[dict[str, Any], int]] = []
    start = 0
    while True:
        offset = payload.find(carrier.LONG_FAMILY, start)
        if offset < 0:
            break
        start = offset + 1
        record = payload[offset : offset + carrier.LONG_RECORD_SIZE]
        if len(record) != carrier.LONG_RECORD_SIZE:
            continue
        header = record[: carrier.LONG_HEADER_SIZE]
        try:
            profile, run_id = carrier._decode_header(  # noqa: SLF001
                header, PROFILE, P334_RUN_ID
            )
        except Exception:
            continue
        slot0, status0 = carrier._decode_slot(  # noqa: SLF001
            header,
            0,
            record[
                carrier.LONG_HEADER_SIZE :
                carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE
            ],
            profile,
        )
        slot_offset = carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE
        raw_slot = record[slot_offset : slot_offset + carrier.SLOT_SIZE]
        body = raw_slot[: carrier.SLOT_BODY_STRUCT.size]
        recorded_crc = struct.unpack("<I", raw_slot[-4:])[0]
        if recorded_crc != carrier._slot_crc(header, 1, body):  # noqa: SLF001
            continue
        (
            generation,
            stage,
            outcome,
            item_index,
            payload_kind,
            length,
            reserved,
            detail,
            padded,
        ) = carrier.SLOT_BODY_STRUCT.unpack(body)
        if (
            status0 != "valid"
            or slot0 is None
            or slot0.generation != 106
            or generation != 107
            or stage != 147
            or outcome != carrier.OUTCOME_FAILURE
            or item_index != 0
            or payload_kind != carrier.PAYLOAD_RAW_EXCERPT
            or length != carrier.REQUEST_PAYLOAD_SIZE
            or reserved != 0
            or any(padded[length:])
            or run_id != P334_RUN_ID
        ):
            continue
        decoded = return_runtime.decode_first_read_detail(detail)
        matches.append(
            (
                {
                    **decoded,
                    "encoded_detail": detail,
                    "observer_offset": offset,
                    "receipt_present": True,
                    "attribution_requires_stage0_without_stage1": True,
                },
                offset,
            )
        )
    if len(matches) != 1:
        raise AdapterIdentityError("P3.34 first-console return record is not exact")
    return matches[0]


def _classify_return_observation(payload: bytes) -> dict[str, Any]:
    receipt, offset = _return_receipt(payload)
    candidates: list[dict[str, Any]] = []
    for detail in (
        STOCK_DETAIL_COMPLETE,
        STOCK_DETAIL_INCOMPLETE,
        STOCK_DETAIL_AMBIGUOUS,
    ):
        normalized = _replace_terminal_detail(payload, offset, detail)
        value = _ORIGINAL_CLASSIFY_OBSERVATION(
            normalized,
            expected_profile=PROFILE,
            expected_run_id=P334_RUN_ID,
        )
        if (
            isinstance(value, dict)
            and value.get("integrity_issue") is False
            and value.get("exact_record_count") == 1
            and value.get("foreign_count") == 0
        ):
            candidates.append(value)
    if len(candidates) != 1:
        raise AdapterIdentityError("P3.34 stock envelope normalization is ambiguous")
    result = _public(candidates[0])
    result["first_console_return"] = receipt
    result["first_console_return_receipt_present"] = True
    result["first_console_return_code_valid"] = receipt["valid"]
    return result


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P334_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P334_RUN_ID:
        raise AdapterIdentityError("P3.34 observation binding differs")
    return _classify_return_observation(payload)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P334_RUN_ID,
) -> dict[str, Any]:
    return _public(
        _ORIGINAL_CLASSIFY_CLEAN_BASELINE(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


bind_lineage = bind_exact_sources

__all__ = [name for name in globals() if not name.startswith("_")]
