#!/usr/bin/env python3
"""Host-only P3.42 Process-v2 adapter.

This adapter projects the consumed P3.41 host-first contract into a fresh
P3.42 namespace.  It adds only the bounded H0 idle-reuse geometry (three
same-FD sessions, 120 seconds of silent idle, then one close/reopen fourth
session); it creates no device/live authority and no later-action lease.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import types
from typing import Any, Mapping

import s22plus_fyg8_p341_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p342_open_read_branch_acm_observer as observer
import s22plus_fyg8_p342_open_read_branch_runtime as runtime
import s22plus_fyg8_p320_stock_process_v2_adapter as raw_parser_source


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 16_687,
    "sha256": "5bd70e677ce887945c4d8e7ddd288514d7d03a4ee541c692473b829ccdc14774",
}
RAW_PARSER_SOURCE = Path(raw_parser_source.__file__).resolve()
RAW_PARSER_SOURCE_IDENTITY = {
    "size": 56_669,
    "sha256": "92be097287be67867b263e5534996228d275d1d70fa03c38b3a124a948a94d88",
}
_RAW_PARSER = None
P341_PREDECESSOR_RUN_ID_HEX = runtime.P341_PREDECESSOR_RUN_ID_HEX
P341_PREDECESSOR_RUN_ID = runtime.P341_PREDECESSOR_RUN_ID
P342_RUN_ID_HEX = runtime.P342_RUN_ID_HEX
P342_RUN_ID = runtime.P342_RUN_ID
P342_ADAPTER_SOURCE = Path(__file__).resolve()

PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PROFILE = predecessor.PROFILE
INITIAL_SESSION_COUNT = 4
INITIAL_RECONNECT_COUNT = 1
SAME_FD_SESSION_COUNT = 3
IDLE_SECONDS = 120
TOTAL_COMMANDS = INITIAL_SESSION_COUNT * len(runtime.DEFAULT_COMMANDS)
LEASE_DURATION_SEC = predecessor.LEASE_DURATION_SEC
LEASE_ACTION_CAP = predecessor.LEASE_ACTION_CAP
LEASE_SCHEMA = "s22plus_fyg8_p342_idle_reuse_lease_v1"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p342-idle-reuse-v1"
DECODER_ID = "s22plus_fyg8_p342_idle_reuse_v1"
OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
SCHEMA = "s22plus_fyg8_p342_stock_process_v2_adapter_v1"
POLICY_PREIMAGE = (
    predecessor.POLICY_PREIMAGE
    .replace("P341", "P342")
    .replace("p341", "p342")
    .replace(P341_PREDECESSOR_RUN_ID_HEX, P342_RUN_ID_HEX)
    + "|predecessor-run="
    + P341_PREDECESSOR_RUN_ID_HEX
    + "|idle-reuse=same-fd-3,idle-sec-120,reopen-1,sessions-4,commands-12"
    + "|runtime-behavior-unchanged=true"
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
OPEN_READ_BRANCHES = dict(runtime.OPEN_READ_BRANCHES)
RUN_ID = STOCK_RUN_ID = P342_RUN_ID
P342_OVERLAY_CONTRACT_ID = OVERLAY_CONTRACT_ID
P342_DECODER_ID = DECODER_ID
P342_POLICY_ID = POLICY_ID
P342_OBSERVER_CONTRACT_ID = OBSERVER_CONTRACT_ID

# Compatibility labels consumed by the shared Process-v2 loader.  They all
# resolve to the fresh P342 identity; P341 remains named explicitly above as
# the consumed predecessor only.
for _prefix in (
    "P328",
    "P330",
    "P331",
    "P332",
    "P333",
    "P334",
    "P335",
    "P336",
    "P337",
    "P338",
    "P339",
    "P340",
    "P341",
):
    globals()[f"{_prefix}_RUN_ID_HEX"] = P342_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P342_RUN_ID


class AdapterIdentityError(ValueError):
    """The exact P3.41 adapter or fresh P3.42 projection differs."""


class ContractError(ValueError):
    """The public P3.42 overlay contract is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise AdapterIdentityError("P3.41 adapter source identity differs")
if predecessor.P341_RUN_ID_HEX != P341_PREDECESSOR_RUN_ID_HEX:
    raise AdapterIdentityError("P3.41 adapter predecessor binding differs")


def _project(node: Any) -> Any:
    """Project serialized P3.41 labels without changing bytes or numbers."""

    if isinstance(node, dict):
        return {key: _project(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_project(value) for value in node]
    if isinstance(node, tuple):
        return tuple(_project(value) for value in node)
    if isinstance(node, str):
        return (
            node.replace(P341_PREDECESSOR_RUN_ID_HEX, P342_RUN_ID_HEX)
            .replace("P341", "P342")
            .replace("p341", "p342")
        )
    return node


def _strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, (list, tuple)):
        return len(actual) == len(expected) and all(
            _strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _fresh(value: Any) -> Any:
    result = _project(copy.deepcopy(value))
    if not isinstance(result, dict):
        return result
    result.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P342_RUN_ID_HEX,
            "predecessor_run_id": P341_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P341_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_sessions": INITIAL_SESSION_COUNT,
            "total_commands": TOTAL_COMMANDS,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "per_boot_identity_required": True,
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "no_banner_is_raw_no_proof": True,
            "wire_frames_unchanged": True,
            "authentication_unchanged": True,
            "catalog_unchanged": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_behavior_unchanged": True,
            "idle_listener_unchanged": True,
            "runtime_order_changed": True,
            "console_body_changed": False,
            "retry_added": False,
            "timeout_changed": False,
            "device_contact": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
            "later_action_lease_active": False,
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
                "host_first_open": True,
                "runtime_order_changed": True,
                "runtime_behavior_unchanged": True,
                "same_fd_session_count": SAME_FD_SESSION_COUNT,
                "idle_seconds": IDLE_SECONDS,
                "total_session_count": INITIAL_SESSION_COUNT,
                "total_command_count": TOTAL_COMMANDS,
            }
        )
        result["contract"] = contract
    observer_contract = result.get("observer_contract")
    if isinstance(observer_contract, dict):
        observer_contract = dict(observer_contract)
        observer_contract.update(
            {
                "id": OBSERVER_CONTRACT_ID,
                "observer_contract_id": OBSERVER_CONTRACT_ID,
                "host_first_open": True,
                "host_open_before_banner": True,
                "device_banner_after_open": True,
                "stage_zero_after_banner": True,
                "open_parsed_after_stage_zero": True,
                "no_unsolicited_device_tx": True,
                "silent_no_peer_no_proof": True,
                "consumed_partial_open_no_replay": True,
                "successful_wire_exchange_unchanged": False,
                "runtime_behavior_unchanged": True,
                "idle_listener_unchanged": True,
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "same_fd_session_count": SAME_FD_SESSION_COUNT,
                "idle_seconds": IDLE_SECONDS,
                "total_session_count": INITIAL_SESSION_COUNT,
                "total_command_count": TOTAL_COMMANDS,
                "later_action_lease_active": False,
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
        "run_id": P342_RUN_ID_HEX,
        "predecessor_run_id_rejected": P341_PREDECESSOR_RUN_ID_HEX,
        "idle_reuse": {
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": INITIAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
        },
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
            "verdict": "PASS_P342_STOCK_PROCESS_V2_ADAPTER_H0_IDLE_REUSE",
            "source": {"path": str(SOURCE), **SOURCE_IDENTITY},
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P342_RUN_ID_HEX,
            "predecessor_run_id": P341_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P341_PREDECESSOR_RUN_ID_HEX,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_sessions": INITIAL_SESSION_COUNT,
            "total_commands": TOTAL_COMMANDS,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "no_banner_is_raw_no_proof": True,
            "wire_frames_unchanged": True,
            "authentication_unchanged": True,
            "catalog_unchanged": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_behavior_unchanged": True,
            "idle_listener_unchanged": True,
            "runtime_order_changed": True,
            "console_body_changed": False,
            "later_action_lease_active": False,
            "initial_collector": observer.audit_binding(),
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
            "host_first_open": True,
            "runtime_order_changed": True,
            "runtime_behavior_unchanged": True,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": INITIAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
        }
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P342 overlay contract is not an object")
    expected = {
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "observer_contract_id": OBSERVER_CONTRACT_ID,
        "payload_abi": predecessor.P320_PAYLOAD_ABI,
        "observer_receipt_size": predecessor.OBSERVER_RECEIPT_SIZE,
        "causal_result_allowed": False,
        "candidate_success": False,
        "runtime_behavior_unchanged": True,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "idle_seconds": IDLE_SECONDS,
        "total_session_count": INITIAL_SESSION_COUNT,
        "total_command_count": TOTAL_COMMANDS,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise ContractError("P342 overlay contract identity differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P342 acceptance item is not an object")
    expected = acceptance_fixture()
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if not _strict_equal(value.get(key), expected_value):
            raise ContractError(f"P342 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {
        "candidate_static",
        "run_manifest",
        "static_check",
    }:
        raise ContractError("P342 acceptance contract differs")
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
            raise ContractError(f"P342 acceptance contract {name} differs")
    return value


def _raw_parser() -> Any:
    """Private ABI-v4 parser; bind raw matching before decoding, not afterward."""
    global _RAW_PARSER
    if _RAW_PARSER is None:
        payload = RAW_PARSER_SOURCE.read_bytes()
        if identity(payload) != RAW_PARSER_SOURCE_IDENTITY:
            raise AdapterIdentityError("P342 raw Carrier parser source differs")
        module = types.ModuleType("p320_carrier_parser_bound_for_p342")
        module.__file__ = str(RAW_PARSER_SOURCE)
        exec(compile(payload, str(RAW_PARSER_SOURCE), "exec", dont_inherit=True), module.__dict__)
        module.STOCK_RUN_ID = P342_RUN_ID
        module.RUN_ID = P342_RUN_ID
        module.P320_RUN_ID = P342_RUN_ID
        module.P320_STOCK_RUN_ID = P342_RUN_ID
        _RAW_PARSER = module
    return _RAW_PARSER


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P342_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P342_RUN_ID:
        raise AdapterIdentityError("P342 observation binding differs")
    try:
        value = _raw_parser().classify_observation(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P342_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    result = _fresh(value)
    # Primary arrival still comes only from the authenticated USB receipt;
    # this decoded Carrier list is the noncausal supplemental projection.
    result.update({
        "acm_primary": True, "carrier_supplemental": True,
        "acm_supplemental": False, "acm_required_for_acceptance": True,
        "acm_required_for_arrival_proof": True,
        "p342_stock": [row["p320_stock"]["stock"] for row in value.get("records", ())
                       if isinstance(row, dict) and "p320_stock" in row],
    })
    return result


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P342_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P342_RUN_ID:
        raise AdapterIdentityError("P342 baseline binding differs")
    try:
        value = _raw_parser().classify_clean_baseline(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P342_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _fresh(value)


bind_lineage = bind_exact_sources


def __getattr__(name: str) -> Any:
    if name.endswith("_ADAPTER_SOURCE"):
        return P342_ADAPTER_SOURCE
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AdapterIdentityError",
        "ContractError",
        "DEFAULT_COMMANDS",
        "DECODER_ID",
        "IDLE_SECONDS",
        "INITIAL_RECONNECT_COUNT",
        "INITIAL_SESSION_COUNT",
        "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC",
        "LEASE_SCHEMA",
        "MAX_RECONNECTS",
        "OBSERVER_CONTRACT_ID",
        "OPEN_READ_BRANCHES",
        "OVERLAY_CONTRACT_ID",
        "P341_PREDECESSOR_RUN_ID",
        "P341_PREDECESSOR_RUN_ID_HEX",
        "P342_ADAPTER_SOURCE",
        "P342_DECODER_ID",
        "P342_OBSERVER_CONTRACT_ID",
        "P342_OVERLAY_CONTRACT_ID",
        "P342_POLICY_ID",
        "P342_RUN_ID",
        "P342_RUN_ID_HEX",
        "PARENT_SOURCE_CONTRACT_ID",
        "POLICY_ID",
        "POLICY_PREIMAGE",
        "PROFILE",
        "RUN_ID",
        "SAME_FD_SESSION_COUNT",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STOCK_RUN_ID",
        "TOTAL_COMMANDS",
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
    | {
        f"{prefix}_RUN_ID{suffix}"
        for prefix in (
            "P328",
            "P330",
            "P331",
            "P332",
            "P333",
            "P334",
            "P335",
            "P336",
            "P337",
            "P338",
            "P339",
            "P340",
            "P341",
        )
        for suffix in ("", "_HEX")
    }
)
