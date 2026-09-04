#!/usr/bin/env python3
"""Host-only P3.38 Process-v2 adapter over the exact P3.37 ABI.

The adapter preserves P337's target, boot-only rollback, 300-second
observation, three fixed commands, three sessions, one reconnect, and lease
limits.  It changes only the fresh run namespace and the first-OPEN stage-3
four-way branch-ordinal projection.  No device, ADB, Odin, or live authority
operation is exposed here.
"""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p337_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p338_open_read_branch_acm_observer as observer
import s22plus_fyg8_p338_open_read_branch_runtime as runtime


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 29_111,
    "sha256": "16871da4a37372c1ff151e05187f4d4faf3b62b6ba159e4f0ee7f9d817bbd645",
}
P337_PREDECESSOR_RUN_ID_HEX = "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P337_PREDECESSOR_RUN_ID = bytes.fromhex(P337_PREDECESSOR_RUN_ID_HEX)
P338_RUN_ID_HEX = runtime.P338_RUN_ID_HEX
P338_RUN_ID = runtime.P338_RUN_ID

P338_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p338-open-read-branch-v1"
P338_DECODER_ID = "s22plus_fyg8_p338_open_read_branch_v1"
P338_OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
P338_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P338_OPEN_READ_BRANCH_V1|"
    "protocol=p338-open-read-branch-v1|"
    "initial-proof=sessions-3,same-fd,host-close-reopen-1|"
    "first-open=header-read-errno,header-validation,body-read-errno,crc|"
    "original-return=unchanged|commands=fixed-p337-three-commands|"
    "transport=one-open-fd-per-session|per-boot-identity=unchanged-nonzero|"
    "retry=none|usb=bidirectional-primary|run="
    + P338_RUN_ID_HEX
    + "|causal=false"
)
P338_POLICY_ID = hashlib.sha256(P338_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

INITIAL_SESSION_COUNT = predecessor.INITIAL_SESSION_COUNT
INITIAL_RECONNECT_COUNT = predecessor.INITIAL_RECONNECT_COUNT
LEASE_DURATION_SEC = predecessor.LEASE_DURATION_SEC
LEASE_ACTION_CAP = predecessor.LEASE_ACTION_CAP
LEASE_SCHEMA = "s22plus_fyg8_p338_open_read_branch_lease_v1"

SCHEMA = "s22plus_fyg8_p338_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P338_OVERLAY_CONTRACT_ID
DECODER_ID = P338_DECODER_ID
OBSERVER_CONTRACT_ID = P338_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P338_POLICY_PREIMAGE
POLICY_ID = P338_POLICY_ID
RUN_ID = P338_RUN_ID
STOCK_RUN_ID = P338_RUN_ID
P337_RUN_ID_HEX = P338_RUN_ID_HEX
P337_RUN_ID = P338_RUN_ID
P336_RUN_ID_HEX = P338_RUN_ID_HEX
P336_RUN_ID = P338_RUN_ID
P335_RUN_ID_HEX = P338_RUN_ID_HEX
P335_RUN_ID = P338_RUN_ID
P334_RUN_ID_HEX = P338_RUN_ID_HEX
P334_RUN_ID = P338_RUN_ID
P338_ADAPTER_SOURCE = Path(__file__).resolve()
P337_ADAPTER_SOURCE = P338_ADAPTER_SOURCE
P336_ADAPTER_SOURCE = P338_ADAPTER_SOURCE
P335_ADAPTER_SOURCE = P338_ADAPTER_SOURCE
P334_ADAPTER_SOURCE = P338_ADAPTER_SOURCE
PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PROFILE = predecessor.PROFILE
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
P320_PAYLOAD_ABI = predecessor.P320_PAYLOAD_ABI
OBSERVER_RECEIPT_SIZE = predecessor.OBSERVER_RECEIPT_SIZE
P338_DETAIL_BOOT_ID = getattr(runtime, "P337_DETAIL_BOOT_ID", 0xC350)
P338_DETAIL_INITIAL_SESSION = getattr(runtime, "P337_DETAIL_INITIAL_SESSION", 0xC351)
P338_DETAIL_LISTENER_BANNER = getattr(runtime, "P337_DETAIL_LISTENER_BANNER", 0xC352)
P338_DETAIL_LISTENER_PROTOCOL = getattr(runtime, "P337_DETAIL_LISTENER_PROTOCOL", 0xC353)


class AdapterIdentityError(ValueError):
    """The exact P3.37 adapter or fresh P3.38 binding differs."""


class ContractError(ValueError):
    """The public P3.38 contract projection is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _serialized_branch_ordinals() -> dict[str, str]:
    """Return the JSON-visible branch table with canonical string keys."""

    return {
        str(ordinal): label
        for ordinal, label in runtime.OPEN_READ_BRANCHES.items()
    }


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
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.37 adapter source is unavailable") from exc
    if (
        direct != direct.resolve(strict=True)
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or identity(payload) != SOURCE_IDENTITY
        or predecessor.P337_RUN_ID_HEX != P337_PREDECESSOR_RUN_ID_HEX
    ):
        raise AdapterIdentityError("P3.37 adapter binding differs")
    return payload


_PREDECESSOR_PAYLOAD = _stable_source()


def _fresh(value: Any) -> Any:
    """Project an inherited result without retaining P337 authority labels."""

    result = copy.deepcopy(value)
    if not isinstance(result, dict):
        return result
    for key in (
        "schema",
        "overlay_contract_id",
        "decoder",
        "policy_id",
        "run_id",
        "predecessor_run_id",
        "predecessor_run_id_rejected",
        "observer_contract_id",
        "userspace_overlay_contract_id",
    ):
        result.pop(key, None)
    result.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P338_RUN_ID_HEX,
            "predecessor_run_id_rejected": P337_PREDECESSOR_RUN_ID_HEX,
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
            "long_idle_host_resync": True,
            "first_open_failure_diagnostic": True,
            "open_read_diagnostic_stage": runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
            "open_read_failure_diagnostic_best_effort": True,
            "open_read_branch_ordinals": _serialized_branch_ordinals(),
            "open_read_branch_count": 4,
            "original_errno_returned_unchanged": True,
            "successful_wire_exchange_unchanged": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "device_contact": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
    )
    contract = result.get("contract")
    if isinstance(contract, dict):
        contract = dict(contract)
        contract.update(
            {
                "decoder": DECODER_ID,
                "observer_contract_id": OBSERVER_CONTRACT_ID,
                "policy_id": POLICY_ID,
                "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
                "causal_result_allowed": False,
                "candidate_success": False,
            }
        )
        result["contract"] = contract
    observer_contract = result.get("observer_contract")
    if isinstance(observer_contract, dict):
        observer_contract = dict(observer_contract)
        observer_contract.update(
            {
                "id": OBSERVER_CONTRACT_ID,
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "per_boot_identity_required": True,
                "long_idle_host_resync": True,
                "first_open_failure_diagnostic": True,
                "open_read_diagnostic_stage": runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
                "open_read_failure_diagnostic_best_effort": True,
                "open_read_branch_ordinals": _serialized_branch_ordinals(),
                "open_read_branch_count": 4,
                "original_errno_returned_unchanged": True,
                "successful_wire_exchange_unchanged": True,
                "open_before_resync": True,
                "max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
                "max_resync_bytes": observer.MAX_RESYNC_BYTES,
                "resident_lease_schema": LEASE_SCHEMA,
                "listener_wait_after_proof": True,
                "action_retry": False,
            }
        )
        result["observer_contract"] = observer_contract
    return result


def acceptance_fixture() -> dict[str, Any]:
    try:
        value = _fresh(predecessor.acceptance_fixture())
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    contract = value.get("contract")
    if isinstance(contract, dict):
        value["contract"] = {
            key: contract[key]
            for key in ("candidate_static", "run_manifest", "static_check")
            if key in contract
        }
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    try:
        value = _fresh(predecessor.bind_exact_sources(auth_key))
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    value["lineage"] = {
        **dict(value.get("lineage", {})),
        "adapter_source": identity(SOURCE.read_bytes()),
        "run_id": P338_RUN_ID_HEX,
        "predecessor_run_id_rejected": P337_PREDECESSOR_RUN_ID_HEX,
    }
    return value


def audit() -> dict[str, Any]:
    try:
        value = _fresh(predecessor.audit())
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P338_STOCK_PROCESS_V2_ADAPTER_H0_OPEN_READ_BRANCH",
            "source": {"path": str(SOURCE), **SOURCE_IDENTITY},
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P338_RUN_ID_HEX,
            "predecessor_run_id": P337_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P337_PREDECESSOR_RUN_ID_HEX,
            "encoder_failure_class": "P338_STOCK_ENCODER_FAILURE",
            "open_read_branch_ordinals": _serialized_branch_ordinals(),
            "open_read_branch_count": 4,
            "original_errno_returned_unchanged": True,
            "lineage": bind_exact_sources(),
        }
    )
    value["acceptance"] = acceptance_fixture()
    contract = value.get("contract")
    if isinstance(contract, dict):
        value["contract"] = {
            **contract,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P338 overlay contract is not an object")
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
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise ContractError("P338 overlay contract identity differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P338 acceptance item is not an object")
    expected = acceptance_fixture()
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if value.get(key) != expected_value or type(value.get(key)) is not type(expected_value):
            raise ContractError(f"P338 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {"candidate_static", "run_manifest", "static_check"}:
        raise ContractError("P338 acceptance contract differs")
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
            raise ContractError(f"P338 acceptance contract {name} differs")
    return value


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P338_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P338_RUN_ID:
        raise AdapterIdentityError("P338 observation binding differs")
    try:
        value = predecessor.classify_observation(
            payload,
            expected_profile=predecessor.PROFILE,
            expected_run_id=predecessor.P337_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _fresh(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P338_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P338_RUN_ID:
        raise AdapterIdentityError("P338 baseline binding differs")
    try:
        value = predecessor.classify_clean_baseline(
            payload,
            expected_profile=predecessor.PROFILE,
            expected_run_id=predecessor.P337_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _fresh(value)


bind_lineage = bind_exact_sources

__all__ = sorted(
    {
        "AdapterIdentityError",
        "ContractError",
        "DEFAULT_COMMANDS",
        "DECODER_ID",
        "INITIAL_RECONNECT_COUNT",
        "INITIAL_SESSION_COUNT",
        "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC",
        "LEASE_SCHEMA",
        "OBSERVER_CONTRACT_ID",
        "OPEN_READ_BRANCHES",
        "OVERLAY_CONTRACT_ID",
        "P334_ADAPTER_SOURCE",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_ADAPTER_SOURCE",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "P336_ADAPTER_SOURCE",
        "P336_RUN_ID",
        "P336_RUN_ID_HEX",
        "P337_ADAPTER_SOURCE",
        "P337_PREDECESSOR_RUN_ID",
        "P337_PREDECESSOR_RUN_ID_HEX",
        "P337_RUN_ID",
        "P337_RUN_ID_HEX",
        "P338_ADAPTER_SOURCE",
        "P338_POLICY_ID",
        "P338_POLICY_PREIMAGE",
        "P338_RUN_ID",
        "P338_RUN_ID_HEX",
        "POLICY_ID",
        "POLICY_PREIMAGE",
        "PARENT_SOURCE_CONTRACT_ID",
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
        "validate_acceptance_item",
        "validate_contract",
    }
)
