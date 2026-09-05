#!/usr/bin/env python3
"""Host-only P3.43 Process-v2 adapter.

This is a fresh overlay over the consumed P3.42 adapter.  The authenticated
host-first listener and its bounded idle-reuse geometry are retained, while
the device-side middle command has a closed named read-only catalog.  Raw
Carrier bytes are parsed by a private P320 parser bound to the current P343
run ID; predecessor records are never relabeled in place.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import types
from typing import Any, Mapping

import s22plus_fyg8_p342_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p320_stock_process_v2_adapter as raw_parser_source
import s22plus_fyg8_p343_open_read_branch_acm_observer as observer
import s22plus_fyg8_p343_open_read_branch_runtime as runtime


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 20_153,
    "sha256": "5e7d26eb51b181f6314230d6e27d53d7e90a1a2731683c494720319c169bdcf6",
}
RAW_PARSER_SOURCE = Path(predecessor.RAW_PARSER_SOURCE).resolve()
RAW_PARSER_SOURCE_IDENTITY = dict(predecessor.RAW_PARSER_SOURCE_IDENTITY)
_RAW_PARSER: types.ModuleType | None = None

# Stable Carrier-v4 interface expected by the common Process-v2 evidence
# layer.  The parser implementation is still loaded privately below so that
# these names cannot accidentally make the imported P320 module current.
SOURCE_PATHS = dict(raw_parser_source.SOURCE_PATHS)
SOURCE_KEYS = frozenset(SOURCE_PATHS)
LONG_FAMILY = raw_parser_source.LONG_FAMILY
UNSAT_FAMILY = raw_parser_source.UNSAT_FAMILY
TERMINAL_STAGE = raw_parser_source.TERMINAL_STAGE
RAW_SIZE = raw_parser_source.RAW_SIZE
P320_PAYLOAD_ABI = raw_parser_source.P320_PAYLOAD_ABI
OBSERVER_RECEIPT_SIZE = raw_parser_source.OBSERVER_RECEIPT_SIZE
STOCK_DETAIL_COMPLETE = raw_parser_source.STOCK_DETAIL_COMPLETE
STOCK_DETAIL_INCOMPLETE = raw_parser_source.STOCK_DETAIL_INCOMPLETE
STOCK_DETAIL_AMBIGUOUS = raw_parser_source.STOCK_DETAIL_AMBIGUOUS
model = raw_parser_source.model
spec = raw_parser_source.spec

P342_PREDECESSOR_RUN_ID_HEX = runtime.P342_PREDECESSOR_RUN_ID_HEX
P342_PREDECESSOR_RUN_ID = runtime.P342_PREDECESSOR_RUN_ID
P343_RUN_ID_HEX = runtime.P343_RUN_ID_HEX
P343_RUN_ID = runtime.P343_RUN_ID
P343_ADAPTER_SOURCE = Path(__file__).resolve()

PARENT_SOURCE_CONTRACT_ID = predecessor.PARENT_SOURCE_CONTRACT_ID
PROFILE = predecessor.PROFILE
INITIAL_SESSION_COUNT = predecessor.INITIAL_SESSION_COUNT
INITIAL_RECONNECT_COUNT = predecessor.INITIAL_RECONNECT_COUNT
SAME_FD_SESSION_COUNT = predecessor.SAME_FD_SESSION_COUNT
IDLE_SECONDS = predecessor.IDLE_SECONDS
TOTAL_COMMANDS = INITIAL_SESSION_COUNT * len(runtime.DEFAULT_COMMANDS)
LEASE_DURATION_SEC = predecessor.LEASE_DURATION_SEC
LEASE_ACTION_CAP = predecessor.LEASE_ACTION_CAP
LEASE_SCHEMA = "s22plus_fyg8_p343_exploration_lease_v1"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p343-readonly-exploration-v1"
DECODER_ID = "s22plus_fyg8_p343_readonly_exploration_v1"
OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
SCHEMA = "s22plus_fyg8_p343_stock_process_v2_adapter_v1"
CATALOG_ACTIONS = tuple(runtime.CATALOG_ACTIONS)
POLICY_PREIMAGE = (
    predecessor.POLICY_PREIMAGE
    .replace("P342", "P343")
    .replace("p342", "p343")
    .replace(P342_PREDECESSOR_RUN_ID_HEX, P343_RUN_ID_HEX)
    + "|predecessor-run="
    + P342_PREDECESSOR_RUN_ID_HEX
    + "|catalog=kernel,processes,mounts,memory,usb-state"
    + "|middle-command=allowlist"
    + "|default-action=kernel"
    + "|runtime-default-behavior-unchanged=true"
    + "|lease="
    + LEASE_SCHEMA
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
OPEN_READ_BRANCHES = dict(runtime.OPEN_READ_BRANCHES)
RUN_ID = STOCK_RUN_ID = P343_RUN_ID
P343_OVERLAY_CONTRACT_ID = OVERLAY_CONTRACT_ID
P343_DECODER_ID = DECODER_ID
P343_POLICY_ID = POLICY_ID
P343_OBSERVER_CONTRACT_ID = OBSERVER_CONTRACT_ID

# Compatibility labels consumed by inherited Process-v2 projections.  The
# explicit P342 names above remain the consumed predecessor, not aliases.
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
    globals()[f"{_prefix}_RUN_ID_HEX"] = P343_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P343_RUN_ID


class AdapterIdentityError(ValueError):
    """The exact P3.42 adapter or fresh P3.43 projection differs."""


class ContractError(ValueError):
    """The public P3.43 overlay contract is incomplete or changed."""


DecodeError = ContractError
ObserverContractError = ContractError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise AdapterIdentityError("P3.42 adapter source identity differs")
if predecessor.P342_RUN_ID_HEX != P342_PREDECESSOR_RUN_ID_HEX:
    raise AdapterIdentityError("P3.42 adapter predecessor binding differs")


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
    """Project current metadata while leaving opaque/raw predecessor rows intact."""

    result = copy.deepcopy(value)
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
            "run_id": P343_RUN_ID_HEX,
            "predecessor_run_id": P342_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P342_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "resident_lease_schema": LEASE_SCHEMA,
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
            "catalog_unchanged": False,
            "catalog_allowlist_expanded": True,
            # Public contract values are JSON-shaped lists; keep the module
            # constant tuple immutable while avoiding tuple/list drift at the
            # evidence validation boundary.
            "catalog_allowlist_actions": list(CATALOG_ACTIONS),
            "middle_command_allowlist": True,
            "middle_command_allowlist_count": len(CATALOG_ACTIONS),
            "middle_command_default_action": "kernel",
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_behavior_unchanged": False,
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
            "caller_selected_command": False,
            "selected_command_integration": False,
            "initial_proof_default_action": "kernel",
            "raw_parser_bound_run_id": P343_RUN_ID_HEX,
            "predecessor_raw_relabelled": False,
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
                "runtime_behavior_unchanged": False,
                "default_runtime_behavior_unchanged": True,
                "same_fd_session_count": SAME_FD_SESSION_COUNT,
                "idle_seconds": IDLE_SECONDS,
                "total_session_count": INITIAL_SESSION_COUNT,
                "total_command_count": TOTAL_COMMANDS,
                "middle_command_allowlist": True,
                "catalog_allowlist_actions": list(CATALOG_ACTIONS),
                "initial_proof_default_action": "kernel",
                "resident_lease_schema": LEASE_SCHEMA,
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
                "runtime_behavior_unchanged": False,
                "default_runtime_behavior_unchanged": True,
                "idle_listener_unchanged": True,
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "same_fd_session_count": SAME_FD_SESSION_COUNT,
                "idle_seconds": IDLE_SECONDS,
                "total_session_count": INITIAL_SESSION_COUNT,
                "total_command_count": TOTAL_COMMANDS,
                "middle_command_allowlist": True,
                "catalog_allowlist_actions": list(CATALOG_ACTIONS),
                "resident_lease_schema": LEASE_SCHEMA,
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
        "run_id": P343_RUN_ID_HEX,
        "predecessor_run_id_rejected": P342_PREDECESSOR_RUN_ID_HEX,
        "raw_parser_source": {
            "path": str(RAW_PARSER_SOURCE),
            **RAW_PARSER_SOURCE_IDENTITY,
            "bound_run_id": P343_RUN_ID_HEX,
        },
        "catalog": {
            "actions": list(CATALOG_ACTIONS),
            "default_action": "kernel",
            "middle_command_allowlist": True,
        },
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
            "verdict": "PASS_P343_STOCK_PROCESS_V2_ADAPTER_H0_READONLY_EXPLORATION",
            "source": {"path": str(SOURCE), **SOURCE_IDENTITY},
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P343_RUN_ID_HEX,
            "predecessor_run_id": P342_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P342_PREDECESSOR_RUN_ID_HEX,
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
            "catalog_unchanged": False,
            "catalog_allowlist_expanded": True,
            "catalog_allowlist_actions": list(CATALOG_ACTIONS),
            "middle_command_allowlist": True,
            "middle_command_allowlist_count": len(CATALOG_ACTIONS),
            "middle_command_default_action": "kernel",
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_behavior_unchanged": False,
            "idle_listener_unchanged": True,
            "runtime_order_changed": True,
            "console_body_changed": False,
            "later_action_lease_active": False,
            "caller_selected_command": False,
            "selected_command_integration": False,
            "initial_proof_default_action": "kernel",
            "resident_lease_schema": LEASE_SCHEMA,
            "raw_parser_source": {
                "path": str(RAW_PARSER_SOURCE),
                **RAW_PARSER_SOURCE_IDENTITY,
                "bound_run_id": P343_RUN_ID_HEX,
            },
            "raw_parser_bound_run_id": P343_RUN_ID_HEX,
            "predecessor_raw_relabelled": False,
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
            "runtime_behavior_unchanged": False,
            "default_runtime_behavior_unchanged": True,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": INITIAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
            "middle_command_allowlist": True,
            "catalog_allowlist_actions": list(CATALOG_ACTIONS),
            "initial_proof_default_action": "kernel",
        }
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P343 overlay contract is not an object")
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
        "runtime_behavior_unchanged": False,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "idle_seconds": IDLE_SECONDS,
        "total_session_count": INITIAL_SESSION_COUNT,
        "total_command_count": TOTAL_COMMANDS,
    }
    if any(
        key not in value
        or type(value[key]) is not type(expected_value)
        or value[key] != expected_value
        for key, expected_value in expected.items()
    ):
        raise ContractError("P343 overlay contract identity differs")
    for key, expected_value in {
        "default_runtime_behavior_unchanged": True,
        "middle_command_allowlist": True,
        "catalog_allowlist_actions": list(CATALOG_ACTIONS),
        "initial_proof_default_action": "kernel",
    }.items():
        if key in value and value[key] != expected_value:
            raise ContractError("P343 named catalog contract differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P343 acceptance item is not an object")
    expected = acceptance_fixture()
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if not _strict_equal(value.get(key), expected_value):
            raise ContractError(f"P343 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {
        "candidate_static",
        "run_manifest",
        "static_check",
    }:
        raise ContractError("P343 acceptance contract differs")
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
            raise ContractError(f"P343 acceptance contract {name} differs")
    return value


def _raw_parser() -> types.ModuleType:
    """Load the raw parser privately and bind its current run identity."""

    global _RAW_PARSER
    if _RAW_PARSER is None:
        try:
            payload = RAW_PARSER_SOURCE.read_bytes()
        except OSError as exc:
            raise AdapterIdentityError("P343 raw Carrier parser is unavailable") from exc
        if identity(payload) != RAW_PARSER_SOURCE_IDENTITY:
            raise AdapterIdentityError("P343 raw Carrier parser source differs")
        module = types.ModuleType("p320_carrier_parser_bound_for_p343")
        module.__file__ = str(RAW_PARSER_SOURCE)
        try:
            exec(compile(payload, str(RAW_PARSER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
        except Exception as exc:
            raise AdapterIdentityError("P343 raw Carrier parser failed to load") from exc
        module.STOCK_RUN_ID = P343_RUN_ID
        module.RUN_ID = P343_RUN_ID
        module.P320_RUN_ID = P343_RUN_ID
        module.P320_STOCK_RUN_ID = P343_RUN_ID
        module.SCHEMA = SCHEMA
        module.OVERLAY_CONTRACT_ID = OVERLAY_CONTRACT_ID
        module.DECODER_ID = DECODER_ID
        module.POLICY_ID = POLICY_ID
        _RAW_PARSER = module
    return _RAW_PARSER


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    """Decode one Carrier record through the privately P343-bound parser."""

    bound = P343_RUN_ID if expected_run_id is None else expected_run_id
    if expected_profile != PROFILE or bound != P343_RUN_ID:
        raise DecodeError("P343 Carrier binding differs")
    try:
        value = _raw_parser().decode_record(
            record,
            expected_profile=PROFILE,
            expected_run_id=P343_RUN_ID,
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    return _fresh(value)


def source_bytes(root: Path | None = None) -> dict[str, bytes]:
    """Read the exact Carrier model/spec source closure used by P343."""

    base = ROOT if root is None else root.resolve()
    try:
        values = raw_parser_source.source_bytes(base)
    except Exception as exc:
        raise DecodeError("P343 Carrier source closure failed") from exc
    if set(values) != SOURCE_KEYS:
        raise DecodeError("P343 Carrier source closure keys differ")
    return values


def encode_fixture(
    *, state: str = "COMPLETE", observer_error: Any = None
) -> bytes:
    """Build a new P343-bound Carrier fixture without mutating retained bytes."""

    parser = _raw_parser()
    if state not in parser.DETAILS.values():
        raise DecodeError("P343 fixture state differs")
    if observer_error is None and state == "AMBIGUOUS":
        observer_error = parser.observer_error_fixture()
    if observer_error is False:
        observer_error = None
    if observer_error is not None and state != "AMBIGUOUS":
        state = "AMBIGUOUS"
    payload = parser._observer().encode_stock_payload_v4(
        parser._base_payload(state=state), observer_error
    )
    if type(payload) is not bytes or len(payload) != parser.PAYLOAD_SIZE:
        raise DecodeError("P343 observer encoder returned a noncanonical payload")
    detail = (
        parser.STOCK_DETAIL_AMBIGUOUS
        if observer_error is not None
        else parser.DETAILS_INV[state]
    )
    return parser._carrier_record_from_envelope(
        parser._envelope_from_payload(payload),
        detail=detail,
        run_id=P343_RUN_ID,
    )


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P343_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P343_RUN_ID:
        raise AdapterIdentityError("P343 observation binding differs")
    try:
        value = _raw_parser().classify_observation(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P343_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    result = _fresh(value)
    result.update(
        {
            "acm_primary": True,
            "carrier_supplemental": True,
            "acm_supplemental": False,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
            "p343_stock": [
                row["p320_stock"]["stock"]
                for row in value.get("records", ())
                if isinstance(row, dict) and "p320_stock" in row
            ],
            "raw_parser_bound_run_id": P343_RUN_ID_HEX,
            "predecessor_raw_relabelled": False,
        }
    )
    return result


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P343_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P343_RUN_ID:
        raise AdapterIdentityError("P343 baseline binding differs")
    try:
        value = _raw_parser().classify_clean_baseline(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P343_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    result = _fresh(value)
    result.update(
        {
            "raw_parser_bound_run_id": P343_RUN_ID_HEX,
            "predecessor_raw_relabelled": False,
        }
    )
    return result


bind_lineage = bind_exact_sources


def __getattr__(name: str) -> Any:
    if name.endswith("_ADAPTER_SOURCE"):
        return P343_ADAPTER_SOURCE
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AdapterIdentityError",
        "CATALOG_ACTIONS",
        "ContractError",
        "DecodeError",
        "DEFAULT_COMMANDS",
        "DECODER_ID",
        "IDLE_SECONDS",
        "INITIAL_RECONNECT_COUNT",
        "INITIAL_SESSION_COUNT",
        "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC",
        "LEASE_SCHEMA",
        "OBSERVER_CONTRACT_ID",
        "OPEN_READ_BRANCHES",
        "OVERLAY_CONTRACT_ID",
        "P342_PREDECESSOR_RUN_ID",
        "P342_PREDECESSOR_RUN_ID_HEX",
        "P343_ADAPTER_SOURCE",
        "P343_DECODER_ID",
        "P343_OBSERVER_CONTRACT_ID",
        "P343_OVERLAY_CONTRACT_ID",
        "P343_POLICY_ID",
        "P343_RUN_ID",
        "P343_RUN_ID_HEX",
        "PARENT_SOURCE_CONTRACT_ID",
        "POLICY_ID",
        "POLICY_PREIMAGE",
        "PROFILE",
        "RAW_PARSER_SOURCE",
        "RAW_PARSER_SOURCE_IDENTITY",
        "RAW_SIZE",
        "RUN_ID",
        "SAME_FD_SESSION_COUNT",
        "SCHEMA",
        "SOURCE_KEYS",
        "SOURCE_PATHS",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STOCK_RUN_ID",
        "LONG_FAMILY",
        "UNSAT_FAMILY",
        "TERMINAL_STAGE",
        "P320_PAYLOAD_ABI",
        "OBSERVER_RECEIPT_SIZE",
        "STOCK_DETAIL_COMPLETE",
        "STOCK_DETAIL_INCOMPLETE",
        "STOCK_DETAIL_AMBIGUOUS",
        "TOTAL_COMMANDS",
        "acceptance_fixture",
        "audit",
        "bind_exact_sources",
        "bind_lineage",
        "classify_clean_baseline",
        "classify_observation",
        "decode_record",
        "encode_fixture",
        "identity",
        "model",
        "spec",
        "source_bytes",
        "validate_acceptance_item",
        "validate_contract",
    }
)
