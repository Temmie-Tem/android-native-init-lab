#!/usr/bin/env python3
"""P345 fresh Carrier decoder and research-shell qualification metadata.

Carrier evidence is supplemental, never a shell-success or resident grant.
The P320 raw decoder is bound to P345 before parsing; no predecessor relabel.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p320_stock_process_v2_adapter as raw_parser_source
import s22plus_fyg8_p344_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p345_research_shell_runtime as runtime
import s22plus_fyg8_p345_research_shell_observer as observer

ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {"size": 27274, "sha256": "6ba28f6825f2a1302a7b8644ac37db4352c975b9959f69f333f9c96eb4ab01f1"}
RAW_PARSER_SOURCE = Path(raw_parser_source.__file__).resolve()
RAW_PARSER_SOURCE_IDENTITY = {"size": 56669, "sha256": "92be097287be67867b263e5534996228d275d1d70fa03c38b3a124a948a94d88"}
_RAW_PARSER = None
P345_RUN_ID_HEX = runtime.P345_RUN_ID_HEX
P345_RUN_ID = STOCK_RUN_ID = RUN_ID = runtime.P345_RUN_ID
P344_PREDECESSOR_RUN_ID_HEX = runtime.P344_PREDECESSOR_RUN_ID_HEX
P344_PREDECESSOR_RUN_ID = runtime.P344_PREDECESSOR_RUN_ID
P345_ADAPTER_SOURCE = Path(__file__).resolve()
PROFILE = raw_parser_source.PROFILE
PARENT_SOURCE_CONTRACT_ID = raw_parser_source.PARENT_SOURCE_CONTRACT_ID
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p345-readonly-research-shell-v1"
DECODER_ID = "s22plus_fyg8_p345_readonly_research_shell_v1"
OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
SCHEMA = "s22plus_fyg8_p345_stock_process_v2_adapter_v1"
POLICY_PREIMAGE = OVERLAY_CONTRACT_ID + "|" + P345_RUN_ID_HEX + "|five-same-fd|no-idle|no-reopen|no-lease|rollback-required|readonly-child|authenticated-cancel"
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
INITIAL_SESSION_COUNT = SAME_FD_SESSION_COUNT = 5
INITIAL_RECONNECT_COUNT = IDLE_SECONDS = 0
TOTAL_COMMANDS = 15
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
SOURCE_PATHS = dict(raw_parser_source.SOURCE_PATHS)
SOURCE_KEYS = frozenset(SOURCE_PATHS)
for _name in ("LONG_FAMILY", "UNSAT_FAMILY", "TERMINAL_STAGE", "RAW_SIZE", "P320_PAYLOAD_ABI",
              "OBSERVER_RECEIPT_SIZE", "STOCK_DETAIL_COMPLETE", "STOCK_DETAIL_INCOMPLETE",
              "STOCK_DETAIL_AMBIGUOUS", "model", "spec"):
    globals()[_name] = getattr(raw_parser_source, _name)

class ContractError(ValueError):
    pass

AdapterIdentityError = DecodeError = ObserverContractError = ContractError

def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

def _fresh(value: Any) -> Any:
    if type(value) is not dict:
        return value
    return {**value, "schema": SCHEMA, "run_id": P345_RUN_ID_HEX,
            "decoder": DECODER_ID, "policy_id": POLICY_ID,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "raw_parser_bound_run_id": P345_RUN_ID_HEX,
            "predecessor_raw_relabelled": False,
            "causal_result_allowed": False, "candidate_success": False,
            "device_contact": False, "live_authorized": False}

# Reuse only the raw read/decode functions, not inherited lease/catalog claims.
_names = frozenset(("_raw_parser", "source_bytes", "decode_record", "encode_fixture",
                    "classify_observation", "classify_clean_baseline", "_strict_equal",
                    "validate_acceptance_item"))
_payload = SOURCE.read_bytes()
if identity(_payload) != SOURCE_IDENTITY:
    raise ContractError("P344 raw-adapter seam source differs")
_tree = ast.parse(_payload)
_nodes = [n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name in _names]
if {n.name for n in _nodes} != _names:
    raise ContractError("P344 raw-adapter seam functions differ")
_text = ast.unparse(ast.Module(body=_nodes, type_ignores=[])).replace("P344", "P345").replace("p344", "p345")
exec(compile(_text, str(SOURCE) + "#p345-raw", "exec", dont_inherit=True), globals())

def _contract() -> dict[str, Any]:
    return {"userspace_overlay_contract_id": OVERLAY_CONTRACT_ID, "decoder": DECODER_ID,
            "policy_id": POLICY_ID, "profile": PROFILE,
            "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "payload_abi": P320_PAYLOAD_ABI, "observer_receipt_size": OBSERVER_RECEIPT_SIZE,
            "causal_result_allowed": False, "candidate_success": False,
            "runtime_behavior_unchanged": False, "runtime_delta_identity_only": False,
            "read_only_child_required": True, "authenticated_cancel": True,
            "initial_session_count": 5, "same_fd_session_count": 5,
            "initial_reconnect_count": 0, "idle_seconds": 0,
            "later_action_lease_active": False, "mandatory_rollback": True}

def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict or any(not _strict_equal(value.get(k), v) for k, v in _contract().items()):
        raise ContractError("P345 overlay contract differs")
    return value

def acceptance_fixture() -> dict[str, Any]:
    value = raw_parser_source.acceptance_fixture()
    value.update({"decoder": DECODER_ID, "policy_id": POLICY_ID, "run_id": P345_RUN_ID_HEX,
                  "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID})
    value["observer_contract"] = {"id": OBSERVER_CONTRACT_ID, "payload_abi": P320_PAYLOAD_ABI,
                                  "receipt_size": OBSERVER_RECEIPT_SIZE}
    value.update({"observer_contract_id": OBSERVER_CONTRACT_ID,
                  "initial_session_count": 5, "same_fd_session_count": 5,
                  "initial_reconnect_count": 0, "idle_seconds": 0,
                  "later_action_lease_active": False, "mandatory_rollback": True,
                  "qualification_schema": observer.SCHEMA,
                  "qualification_commands": [
                      {"ordinal": step.ordinal, "name": step.name,
                       "command_hex": step.command.hex(), "expected_outcome": step.expected_outcome}
                      for step in observer.QUALIFICATION_COMMANDS]})
    return value

def bind_exact_sources(auth_key: Any = None) -> dict[str, Any]:
    # No authentication key is exposed or implicitly created by this adapter.
    parser = _raw_parser()
    value = parser.bind_exact_sources()
    return {**_fresh(value), "sources": value["sources"],
            "raw_parser_source": {"path": str(RAW_PARSER_SOURCE), **RAW_PARSER_SOURCE_IDENTITY},
            "contract": _contract(), "initial_collector": observer.audit_binding()}

bind_lineage = bind_exact_sources

def audit() -> dict[str, Any]:
    return {**bind_exact_sources(), "schema": SCHEMA,
            "verdict": "PASS_P345_STOCK_PROCESS_V2_ADAPTER_H0",
            "contract": _contract(), "initial_session_count": 5,
            "initial_reconnect_count": 0, "total_commands": 15,
            "runtime_behavior_unchanged": False, "catalog_unchanged": False,
            "later_action_lease_active": False, "mandatory_rollback": True}
