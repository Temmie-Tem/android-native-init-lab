#!/usr/bin/env python3
"""Host-only P3.41 Process-v2 adapter.

The P340 adapter is retained as the semantic classifier and source validator;
this wrapper projects it into a distinct P341 overlay/decoder/policy
namespace and adds the host-first OPEN ordering facts.  The same three
initial sessions, HMAC/catalog, bounded deadlines, raw evidence path, and
mandatory rollback remain in force.  No later-action lease is activated by
this module and no device/live authority is exposed.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import types
from typing import Any, Mapping

import s22plus_fyg8_p340_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p341_open_read_branch_acm_observer as observer
import s22plus_fyg8_p341_open_read_branch_runtime as runtime


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 3_930,
    "sha256": "3eb8d636497cad744eb55731cdfc1e1a0610840afc32e30d5b1762f55fe4d8cb",
}
P340_PREDECESSOR_RUN_ID_HEX = runtime.P340_PREDECESSOR_RUN_ID_HEX
P340_PREDECESSOR_RUN_ID = runtime.P340_PREDECESSOR_RUN_ID
P341_RUN_ID_HEX = runtime.P341_RUN_ID_HEX
P341_RUN_ID = runtime.P341_RUN_ID
P341_ADAPTER_SOURCE = Path(__file__).resolve()

PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PROFILE = predecessor.PROFILE
INITIAL_SESSION_COUNT = predecessor.INITIAL_SESSION_COUNT
INITIAL_RECONNECT_COUNT = predecessor.INITIAL_RECONNECT_COUNT
LEASE_DURATION_SEC = predecessor.LEASE_DURATION_SEC
LEASE_ACTION_CAP = predecessor.LEASE_ACTION_CAP
LEASE_SCHEMA = "s22plus_fyg8_p341_host_first_open_lease_v1"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p341-host-first-open-v1"
DECODER_ID = "s22plus_fyg8_p341_host_first_open_v1"
OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
SCHEMA = "s22plus_fyg8_p341_stock_process_v2_adapter_v1"
POLICY_PREIMAGE = (
    predecessor.POLICY_PREIMAGE
    .replace("P340", "P341")
    .replace("p340", "p341")
    .replace(P340_PREDECESSOR_RUN_ID_HEX, P341_RUN_ID_HEX)
    + "|host-first-open=host-open-before-banner,banner-stage0-open-parsed"
    + ",no-unsolicited-device-tx,silent-no-peer-no-proof,partial-open-consumed"
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
OPEN_READ_BRANCHES = dict(runtime.OPEN_READ_BRANCHES)
RUN_ID = STOCK_RUN_ID = P341_RUN_ID
P341_OVERLAY_CONTRACT_ID = OVERLAY_CONTRACT_ID
P341_DECODER_ID = DECODER_ID
P341_POLICY_ID = POLICY_ID
P341_OBSERVER_CONTRACT_ID = OBSERVER_CONTRACT_ID

# Compatibility labels consumed by the shared Process-v2 loader.  They all
# resolve to the fresh P341 identity; P340 remains named explicitly above as
# the consumed predecessor only.
for _prefix in (
    "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
    "P337", "P338", "P339", "P340",
):
    globals()[f"{_prefix}_RUN_ID_HEX"] = P341_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P341_RUN_ID


class AdapterIdentityError(ValueError):
    """The exact P340 adapter or fresh P341 projection differs."""


class ContractError(ValueError):
    """The public P341 contract projection is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise AdapterIdentityError("P340 adapter source identity differs")
if predecessor.P340_RUN_ID_HEX != P340_PREDECESSOR_RUN_ID_HEX:
    raise AdapterIdentityError("P340 adapter predecessor binding differs")


def _project(node: Any) -> Any:
    """Project serialized P340 labels without changing numeric/byte values."""
    if isinstance(node, dict):
        return {key: _project(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_project(value) for value in node]
    if isinstance(node, tuple):
        return tuple(_project(value) for value in node)
    if isinstance(node, str):
        return (
            node.replace(P340_PREDECESSOR_RUN_ID_HEX, P341_RUN_ID_HEX)
            .replace("P340", "P341")
            .replace("p340", "p341")
        )
    return node


def _strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return (
            set(actual) == set(expected)
            and all(_strict_equal(actual[key], expected[key]) for key in actual)
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
            "run_id": P341_RUN_ID_HEX,
            "predecessor_run_id": P340_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P340_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
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
            "runtime_order_changed": True,
            "console_body_changed": False,
            "open_read_branch_ordinals": {
                str(key): label for key, label in OPEN_READ_BRANCHES.items()
            },
            "open_read_branch_count": len(OPEN_READ_BRANCHES),
            "open_header_word_stages": list(runtime.OPEN_HEADER_WORD_STAGES),
            "open_header_size": runtime.OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "diagnostic_payload_unchanged": True,
            "diagnostic_frame_type_unchanged": True,
            "original_errno_returned_unchanged": True,
            "retry_added": False,
            "timeout_changed": False,
            "device_contact": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
            # P341 does not expose an active later-action lease integration.
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
            }
        )
        result["contract"] = contract
    observer_contract = result.get("observer_contract")
    if isinstance(observer_contract, dict):
        observer_contract = dict(observer_contract)
        observer_contract.update(
            {
                "id": OBSERVER_CONTRACT_ID,
                "host_first_open": True,
                "host_open_before_banner": True,
                "device_banner_after_open": True,
                "stage_zero_after_banner": True,
                "open_parsed_after_stage_zero": True,
                "no_unsolicited_device_tx": True,
                "silent_no_peer_no_proof": True,
                "consumed_partial_open_no_replay": True,
                "successful_wire_exchange_unchanged": False,
                "runtime_order_changed": True,
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
        "run_id": P341_RUN_ID_HEX,
        "predecessor_run_id_rejected": P340_PREDECESSOR_RUN_ID_HEX,
        "host_first_source": dict(runtime.HOST_FIRST_SOURCE_IDENTITY),
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
            "verdict": "PASS_P341_STOCK_PROCESS_V2_ADAPTER_H0_HOST_FIRST_OPEN",
            "source": {"path": str(SOURCE), **SOURCE_IDENTITY},
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P341_RUN_ID_HEX,
            "predecessor_run_id": P340_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P340_PREDECESSOR_RUN_ID_HEX,
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
        }
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P341 overlay contract is not an object")
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
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise ContractError("P341 overlay contract identity differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P341 acceptance item is not an object")
    expected = acceptance_fixture()
    # The contract paths are filled by promotion, so retain the inherited
    # strict shape check while allowing those three path/hash records to vary.
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if not _strict_equal(value.get(key), expected_value):
            raise ContractError(f"P341 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {
        "candidate_static", "run_manifest", "static_check"
    }:
        raise ContractError("P341 acceptance contract differs")
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
            raise ContractError(f"P341 acceptance contract {name} differs")
    return value


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P341_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P341_RUN_ID:
        raise AdapterIdentityError("P341 observation binding differs")
    try:
        value = predecessor.classify_observation(
            payload,
            expected_profile=predecessor.PROFILE,
            expected_run_id=predecessor.P340_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _fresh(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P341_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P341_RUN_ID:
        raise AdapterIdentityError("P341 baseline binding differs")
    try:
        value = predecessor.classify_clean_baseline(
            payload,
            expected_profile=predecessor.PROFILE,
            expected_run_id=predecessor.P340_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _fresh(value)


bind_lineage = bind_exact_sources


def __getattr__(name: str) -> Any:
    if name.endswith("_ADAPTER_SOURCE"):
        return P341_ADAPTER_SOURCE
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AdapterIdentityError", "ContractError", "DEFAULT_COMMANDS", "DECODER_ID",
        "INITIAL_RECONNECT_COUNT", "INITIAL_SESSION_COUNT", "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC", "LEASE_SCHEMA", "OBSERVER_CONTRACT_ID", "OPEN_READ_BRANCHES",
        "OVERLAY_CONTRACT_ID", "PARENT_SOURCE_CONTRACT_ID", "POLICY_ID", "POLICY_PREIMAGE",
        "PROFILE", "P341_ADAPTER_SOURCE", "P341_DECODER_ID", "P341_OBSERVER_CONTRACT_ID",
        "P341_OVERLAY_CONTRACT_ID", "P341_POLICY_ID", "P341_RUN_ID", "P341_RUN_ID_HEX",
        "P340_PREDECESSOR_RUN_ID", "P340_PREDECESSOR_RUN_ID_HEX", "RUN_ID", "SCHEMA",
        "SOURCE", "SOURCE_IDENTITY", "STOCK_RUN_ID", "acceptance_fixture", "audit",
        "bind_exact_sources", "bind_lineage", "classify_clean_baseline", "classify_observation",
        "identity", "validate_acceptance_item", "validate_contract",
    }
    | {
        f"{prefix}_RUN_ID{suffix}"
        for prefix in (
            "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
            "P337", "P338", "P339", "P340",
        )
        for suffix in ("", "_HEX")
    }
)
