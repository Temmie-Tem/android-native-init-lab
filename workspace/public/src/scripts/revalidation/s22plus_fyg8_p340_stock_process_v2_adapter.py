"""P340 Process-v2 namespace over the exact P339 bounded protocol adapter.

Only this private adapter graph is rebound. The predecessor remains consumed;
its paths and source identities are retained as lineage, never as a new run.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p339_stock_process_v2_adapter as predecessor
import s22plus_fyg8_p340_open_read_branch_acm_observer as observer
import s22plus_fyg8_p340_open_read_branch_runtime as runtime

SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 18140,
    "sha256": "3c9cb020fc9ec32be312bd479b226cdd7e4157db986079550c3c246199fff507",
}
P339_PREDECESSOR_RUN_ID_HEX = predecessor.P339_RUN_ID_HEX
P339_PREDECESSOR_RUN_ID = predecessor.P339_RUN_ID
P340_RUN_ID_HEX = runtime.P340_RUN_ID_HEX
P340_RUN_ID = runtime.P340_RUN_ID
P340_ADAPTER_SOURCE = Path(__file__).resolve()
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p340-open-header-capture-v1"
DECODER_ID = "s22plus_fyg8_p340_open_header_capture_v1"
OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
SCHEMA = "s22plus_fyg8_p340_stock_process_v2_adapter_v1"
LEASE_SCHEMA = "s22plus_fyg8_p340_open_header_capture_lease_v1"
POLICY_PREIMAGE = predecessor.POLICY_PREIMAGE.replace("P339", "P340").replace(
    "p339", "p340"
).replace(P339_PREDECESSOR_RUN_ID_HEX, P340_RUN_ID_HEX) + "|initial-failure-suffix=max96,same-deadline"
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


_payload = SOURCE.read_bytes()
if identity(_payload) != SOURCE_IDENTITY:
    raise ValueError("P340 predecessor adapter source identity differs")
_adapter = types.ModuleType("s22plus_fyg8_p339_adapter_bound_for_p340")
_adapter.__file__ = str(SOURCE)
exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _adapter.__dict__)
_adapter.predecessor = predecessor
_adapter.runtime = runtime
_adapter.observer = observer
_adapter.SOURCE = SOURCE
_adapter.SOURCE_IDENTITY = SOURCE_IDENTITY
_adapter.P338_PREDECESSOR_RUN_ID_HEX = P339_PREDECESSOR_RUN_ID_HEX
_adapter.P338_PREDECESSOR_RUN_ID = P339_PREDECESSOR_RUN_ID
for _key, _value in list(vars(_adapter).items()):
    if _value == P339_PREDECESSOR_RUN_ID_HEX:
        setattr(_adapter, _key, P340_RUN_ID_HEX)
    elif _value == P339_PREDECESSOR_RUN_ID:
        setattr(_adapter, _key, P340_RUN_ID)
# The predecessor guard must continue to describe the consumed original.
_adapter.P338_PREDECESSOR_RUN_ID_HEX = P339_PREDECESSOR_RUN_ID_HEX
_adapter.P338_PREDECESSOR_RUN_ID = P339_PREDECESSOR_RUN_ID
for _key in ("OVERLAY_CONTRACT_ID", "DECODER_ID", "OBSERVER_CONTRACT_ID",
             "SCHEMA", "LEASE_SCHEMA", "POLICY_PREIMAGE", "POLICY_ID"):
    setattr(_adapter, _key, globals()[_key])
_adapter.DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
for _name in ("classify_observation", "classify_clean_baseline"):
    _function = getattr(_adapter, _name)
    _function.__kwdefaults__ = dict(_function.__kwdefaults__) | {"expected_run_id": P340_RUN_ID}

AdapterIdentityError = _adapter.AdapterIdentityError
ContractError = _adapter.ContractError
RUN_ID = STOCK_RUN_ID = P340_RUN_ID
P340_OVERLAY_CONTRACT_ID = OVERLAY_CONTRACT_ID
P340_DECODER_ID = DECODER_ID
P340_POLICY_ID = POLICY_ID
P340_OBSERVER_CONTRACT_ID = OBSERVER_CONTRACT_ID


def audit() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise AdapterIdentityError("P340 predecessor adapter source changed")
    value = _adapter.audit()
    value["verdict"] = "PASS_P340_STOCK_PROCESS_V2_ADAPTER_H0_OPEN_HEADER_CAPTURE"
    value["initial_collector"] = observer.audit_binding()
    return value


def __getattr__(name: str) -> Any:
    if name.endswith("_ADAPTER_SOURCE"):
        return P340_ADAPTER_SOURCE
    return getattr(_adapter, name)
