#!/usr/bin/env python3
"""P3.35 Process-v2 adapter for the attended resident lease.

The stock record ABI remains the exact P3.34 ABI.  P3.35 changes the
host-observer lifecycle (three initial sessions, one deliberate host
close/reopen, and a bounded resident lease), so this adapter projects those
facts explicitly while keeping the predecessor parser isolated.
"""

from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
SOURCE = REVALIDATION / "s22plus_fyg8_p334_stock_process_v2_adapter.py"
SOURCE_IDENTITY = {
    "size": 16_667,
    "sha256": "c84974647fceddb8a81a4a3a3335e7c7e9c615ccc1c95570f19c5c8804a2956e",
}
P334_PREDECESSOR_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_PREDECESSOR_RUN_ID = bytes.fromhex(P334_PREDECESSOR_RUN_ID_HEX)
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_RUN_ID = bytes.fromhex(P335_RUN_ID_HEX)

P335_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p335-attended-resident-v1"
P335_DECODER_ID = "s22plus_fyg8_p335_attended_resident_v1"
P335_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p335-retained-listener-acm-observer-v1"
P335_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P335_STOCK_OBSERVER_V1|protocol=p335-attended-resident-v1|"
    "initial-proof=sessions-2,same-fd,host-close-reopen-1|"
    "resident-lease=one-hour,actions-16,one-session-per-action|"
    "commands=fixed-p330-commands|transport=one-open-fd-per-session|"
    "per-boot-identity=unchanged-nonzero|retry=none|usb=bidirectional-primary|run="
    + P335_RUN_ID_HEX
    + "|causal=false"
)
P335_POLICY_ID = hashlib.sha256(P335_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

INITIAL_SESSION_COUNT = 3
INITIAL_RECONNECT_COUNT = 1
LEASE_DURATION_SEC = 3_600
LEASE_ACTION_CAP = 16


class AdapterIdentityError(ValueError):
    """The exact P3.34 adapter or fresh P3.35 binding differs."""


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


def _stable_source() -> bytes:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.34 adapter source is unavailable") from exc
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
        raise AdapterIdentityError("P3.34 adapter source identity differs")
    return payload


def _load_dependency(name: str) -> types.ModuleType | None:
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        return None


# The worker owns these files.  Keeping imports lazy lets the wrapper exist as
# a fail-closed skeleton while those exact sources are being finalized.
return_runtime = _load_dependency("s22plus_fyg8_p335_retained_listener_runtime")
resident_observer = _load_dependency("s22plus_fyg8_p335_retained_listener_acm_observer")


def _legacy_runtime_alias() -> types.ModuleType | None:
    """Expose only legacy names required while loading the P3.34 parser."""
    if return_runtime is None:
        return None
    alias = types.ModuleType("s22plus_fyg8_p334_first_read_rc_runtime_for_p335")
    alias.__dict__.update(vars(return_runtime))
    alias.P334_DETAIL_PREFIX = getattr(return_runtime, "P334_DETAIL_PREFIX", 0xB000)
    alias.P334_DETAIL_SENTINEL = getattr(return_runtime, "P334_DETAIL_SENTINEL", 0xBFFF)
    if not hasattr(alias, "decode_first_read_detail"):
        def decode_first_read_detail(detail: int) -> dict[str, Any]:
            if detail == alias.P334_DETAIL_SENTINEL:
                return {"valid": False, "console_called": None, "return_code": None}
            if detail & 0xF000 != alias.P334_DETAIL_PREFIX or detail & 0x0FFF > 4094:
                raise ValueError("legacy P3.34 terminal detail differs")
            return {
                "valid": True,
                "console_called": True,
                "return_code": -(detail & 0x0FFF),
            }
        alias.decode_first_read_detail = decode_first_read_detail
    return alias


def _load_p334() -> types.ModuleType | None:
    if return_runtime is None:
        return None
    payload = _stable_source()
    module = types.ModuleType("s22plus_fyg8_p334_adapter_bound_for_p335")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    legacy_runtime = _legacy_runtime_alias()
    aliases = {"s22plus_fyg8_p334_first_read_rc_runtime": legacy_runtime}
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.34 adapter source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    if getattr(module, "P334_RUN_ID_HEX", None) != P334_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.34 adapter binding differs")
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


_P334 = _load_p334()
if _P334 is not None:
    for _module in _modules(_P334):
        for _name, _value in tuple(vars(_module).items()):
            if _value == P334_PREDECESSOR_RUN_ID:
                setattr(_module, _name, P335_RUN_ID)
            elif _value == P334_PREDECESSOR_RUN_ID_HEX:
                setattr(_module, _name, P335_RUN_ID_HEX)
            elif callable(_value) and getattr(_value, "__kwdefaults__", None):
                _defaults = dict(_value.__kwdefaults__)
                _changed = False
                for _key, _default in tuple(_defaults.items()):
                    if _default == P334_PREDECESSOR_RUN_ID:
                        _defaults[_key] = P335_RUN_ID
                        _changed = True
                    elif _default == P334_PREDECESSOR_RUN_ID_HEX:
                        _defaults[_key] = P335_RUN_ID_HEX
                        _changed = True
                if _changed:
                    _value.__kwdefaults__ = _defaults
    _P334.return_runtime = _legacy_runtime_alias()


def _require_loaded() -> types.ModuleType:
    if _P334 is None or return_runtime is None or resident_observer is None:
        raise AdapterIdentityError("P3.35 runtime/observer sources are unavailable")
    return _P334


for _name in getattr(_P334, "__all__", ()) if _P334 is not None else ():
    if hasattr(_P334, _name):
        globals()[_name] = getattr(_P334, _name)

# Re-pin after inherited __all__.  P334 aliases remain compatibility labels;
# the exported contract below is the sole P335 identity.
SCHEMA = "s22plus_fyg8_p335_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P335_OVERLAY_CONTRACT_ID
DECODER_ID = P335_DECODER_ID
OBSERVER_CONTRACT_ID = P335_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P335_POLICY_PREIMAGE
POLICY_ID = P335_POLICY_ID
RUN_ID = P335_RUN_ID
STOCK_RUN_ID = P335_RUN_ID
P334_RUN_ID = P335_RUN_ID
P334_RUN_ID_HEX = P335_RUN_ID_HEX
P335_ADAPTER_SOURCE = Path(__file__).resolve()
P334_ADAPTER_SOURCE = P335_ADAPTER_SOURCE
PARENT_SOURCE_CONTRACT_ID = (
    getattr(_P334, "PARENT_SOURCE_CONTRACT_ID", None)
    if _P334 is not None
    else "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
)
PROFILE = getattr(_P334, "PROFILE", "E2") if _P334 is not None else "E2"

if return_runtime is not None:
    DEFAULT_COMMANDS = tuple(return_runtime.DEFAULT_COMMANDS)
    P335_DETAIL_BOOT_ID = getattr(return_runtime, "P335_DETAIL_BOOT_ID", 0xC350)
    P335_DETAIL_INITIAL_SESSION = getattr(
        return_runtime, "P335_DETAIL_INITIAL_SESSION", 0xC351
    )
    P335_DETAIL_LISTENER_BANNER = getattr(
        return_runtime, "P335_DETAIL_LISTENER_BANNER", 0xC352
    )
    P335_DETAIL_LISTENER_PROTOCOL = getattr(
        return_runtime, "P335_DETAIL_LISTENER_PROTOCOL", 0xC353
    )
else:
    DEFAULT_COMMANDS = (
        b"/bin/busybox id",
        b"/bin/busybox uname -a",
        f"/bin/busybox echo P335-NONCE {P335_RUN_ID_HEX}".encode("ascii"),
    )
    P335_DETAIL_BOOT_ID = 0xC350
    P335_DETAIL_INITIAL_SESSION = 0xC351
    P335_DETAIL_LISTENER_BANNER = 0xC352
    P335_DETAIL_LISTENER_PROTOCOL = 0xC353

if resident_observer is not None:
    P335_OBSERVER_CONTRACT_ID = resident_observer.CONTRACT_ID


def _public(value: Any) -> Any:
    module = _require_loaded()
    original = getattr(module, "_ORIGINAL_PUBLIC", None)
    result = original(value) if callable(original) else value
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "run_id": P335_RUN_ID_HEX,
            "authenticated_exec": True,
            "authentication_required": True,
            "caller_selected_command": False,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in {
            "P334_STOCK_ENCODER_FAILURE",
            "P333_STOCK_ENCODER_FAILURE",
            "P332_STOCK_ENCODER_FAILURE",
        }:
            item[key] = "P335_STOCK_ENCODER_FAILURE"
    return item


if _P334 is not None:
    _P334._public = _public


def acceptance_fixture() -> dict[str, Any]:
    module = _require_loaded()
    value = dict(module.acceptance_fixture())
    predecessors = list(value.get("predecessor_run_ids_rejected", []))
    for run_id in (P334_PREDECESSOR_RUN_ID_HEX,):
        if run_id not in predecessors:
            predecessors.append(run_id)
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P335_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id_rejected": P334_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": predecessors,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "logical_same_tty": True,
            "same_tty_fd": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "detail_codes": {
                "boot_id": P335_DETAIL_BOOT_ID,
                "initial_session": P335_DETAIL_INITIAL_SESSION,
                "listener_banner": P335_DETAIL_LISTENER_BANNER,
                "listener_protocol": P335_DETAIL_LISTENER_PROTOCOL,
            },
        }
    )
    observer_contract = value.get("observer_contract")
    if isinstance(observer_contract, dict):
        observer_contract = dict(observer_contract)
        observer_contract.update(
            {
                "id": OBSERVER_CONTRACT_ID,
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "per_boot_identity_required": True,
                "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
                "listener_wait_after_proof": True,
                "action_retry": False,
            }
        )
        value["observer_contract"] = observer_contract
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p335-attended-resident-v1-fixture"
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    module = _require_loaded()
    value = dict(module.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P335_RUN_ID_HEX,
            "predecessor_run_id_rejected": P334_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
        }
    )
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def audit() -> dict[str, Any]:
    module = _require_loaded()
    value = dict(module.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P335_STOCK_PROCESS_V2_ADAPTER_H0_ATTENDED_RESIDENT",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P335_RUN_ID_HEX,
            "predecessor_run_id": P334_PREDECESSOR_RUN_ID_HEX,
            "encoder_failure_class": "P335_STOCK_ENCODER_FAILURE",
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "lineage": bind_exact_sources(),
        }
    )
    value["acceptance"] = acceptance_fixture()
    if isinstance(value.get("contract"), dict):
        value["contract"] = {
            **value["contract"],
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        }
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    """Validate the P3.35 overlay metadata without delegating its identity."""
    if type(value) is not dict:
        raise ContractError("P335 overlay contract is not an object")
    expected = {
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
    }
    if not set(expected) <= set(value) or any(
        type(value.get(key)) is not type(expected_value)
        or value.get(key) != expected_value
        for key, expected_value in expected.items()
    ):
        raise ContractError("P335 overlay contract identity differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    """Validate the complete fresh P3.35 acceptance projection."""
    if type(value) is not dict:
        raise ContractError("P335 acceptance item is not an object")
    expected = acceptance_fixture()
    if not set(expected) <= set(value):
        raise ContractError("P335 acceptance fields are incomplete")
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if type(value.get(key)) is not type(expected_value) or value.get(key) != expected_value:
            raise ContractError(f"P335 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {
        "candidate_static", "run_manifest", "static_check"
    }:
        raise ContractError("P335 acceptance contract differs")
    for name, item in contract.items():
        if (
            type(item) is not dict
            or set(item) != {"path", "size", "sha256"}
            or type(item["path"]) is not str
            or not item["path"]
            or type(item["size"]) is not int
            or item["size"] <= 0
            or type(item["sha256"]) is not str
            or len(item["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in item["sha256"])
        ):
            raise ContractError(f"P335 acceptance contract {name} differs")
    auth_key = value.get("auth_key")
    if auth_key is not None and (
        type(auth_key) is not dict
        or set(auth_key) != {"size", "sha256"}
        or type(auth_key["size"]) is not int
        or auth_key["size"] != 32
        or type(auth_key["sha256"]) is not str
        or len(auth_key["sha256"]) != 64
        or any(char not in "0123456789abcdef" for char in auth_key["sha256"])
    ):
        raise ContractError("P335 acceptance auth-key identity differs")
    return value


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P335_RUN_ID,
) -> dict[str, Any]:
    module = _require_loaded()
    if expected_profile != PROFILE or expected_run_id != P335_RUN_ID:
        raise AdapterIdentityError("P3.35 observation binding differs")
    try:
        # P3.35 retains the P3.34 stock-record ABI but drops its one-shot
        # first-console-return normalization.  Use the exact predecessor
        # classifier directly and project only the new lease identity.
        value = module._ORIGINAL_CLASSIFY_OBSERVATION(  # noqa: SLF001
            payload,
            expected_profile=PROFILE,
            expected_run_id=P335_RUN_ID,
        )
    except Exception as exc:
        if isinstance(exc, AdapterIdentityError):
            raise
        raise AdapterIdentityError(str(exc)) from exc
    return _public(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P335_RUN_ID,
) -> dict[str, Any]:
    module = _require_loaded()
    try:
        value = module.classify_clean_baseline(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _public(value)


bind_lineage = bind_exact_sources

__all__ = sorted(
    {
        *(getattr(_P334, "__all__", ()) if _P334 is not None else ()),
        "AdapterIdentityError",
        "DEFAULT_COMMANDS",
        "INITIAL_RECONNECT_COUNT",
        "INITIAL_SESSION_COUNT",
        "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC",
        "OBSERVER_CONTRACT_ID",
        "OVERLAY_CONTRACT_ID",
        "P334_ADAPTER_SOURCE",
        "P334_AP_IDENTITY" if _P334 is not None else "P334_PREDECESSOR_RUN_ID",
        "P334_PREDECESSOR_RUN_ID",
        "P334_PREDECESSOR_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_ADAPTER_SOURCE",
        "P335_DECODER_ID",
        "P335_DETAIL_BOOT_ID",
        "P335_DETAIL_INITIAL_SESSION",
        "P335_DETAIL_LISTENER_BANNER",
        "P335_DETAIL_LISTENER_PROTOCOL",
        "P335_OBSERVER_CONTRACT_ID",
        "P335_OVERLAY_CONTRACT_ID",
        "P335_POLICY_ID",
        "P335_POLICY_PREIMAGE",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "PARENT_SOURCE_CONTRACT_ID",
        "POLICY_ID",
        "POLICY_PREIMAGE",
        "PROFILE",
        "RUN_ID",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STOCK_RUN_ID",
        "acceptance_fixture",
        "audit",
        "bind_exact_sources",
        "bind_lineage",
        "classify_clean_baseline",
        "classify_observation",
        "identity",
    }
)
