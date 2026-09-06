#!/usr/bin/env python3
"""P348 Carrier binding and initial-observer/lease metadata.

The raw Carrier decoder remains the P347/P320 parser lineage.  This adapter
adds only fresh P348 identity and the reviewed six-session initial geometry;
Carrier evidence remains supplemental and never grants live authority.
"""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_stock_process_v2_adapter.py"
)
TEMPLATE_IDENTITY = {
    "size": 700,
    "sha256": "4164a62c11f419e2675bb2a65eed8a7b0b4b2f6a2d67a4ac54a4cca97397a5e0",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())


INITIAL_OBSERVATION = "p348_readonly_research_shell_qualification"
INITIAL_SESSION_COUNT = 6
SAME_FD_SESSION_COUNT = 5
INITIAL_RECONNECT_COUNT = 1
IDLE_SECONDS = 120
TOTAL_SESSION_COUNT = 6
TOTAL_COMMANDS = 18
PHYSICAL_REOPEN_COUNT = 1
LEASE_DURATION_SEC = 3600
LEASE_ACTION_CAP = 16
LEASE_SCHEMA = "s22plus_fyg8_p348_shell_lease_v1"
POLICY_PREIMAGE = (
    OVERLAY_CONTRACT_ID
    + "|"
    + P348_RUN_ID_HEX
    + "|five-same-fd|idle-120|one-clean-reopen|"
    + LEASE_SCHEMA
    + "|rollback-required|readonly-child|authenticated-cancel"
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

_base_contract = _contract
_base_acceptance_fixture = acceptance_fixture
_base_audit = audit


def _contract() -> dict[str, Any]:
    value = _base_contract()
    value.update(
        {
            "initial_observation": INITIAL_OBSERVATION,
            "initial_observation_field": observer.INITIAL_OBSERVATION_FIELD,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": TOTAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
            "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "later_action_lease_active": False,
            "later_acceptance_commands": observer.later_acceptance_binding(),
        }
    )
    return value


def acceptance_fixture() -> dict[str, Any]:
    value = _base_acceptance_fixture()
    value.update(
        {
            "initial_observation": INITIAL_OBSERVATION,
            "initial_observation_field": observer.INITIAL_OBSERVATION_FIELD,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": TOTAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
            "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "later_action_lease_active": False,
        }
    )
    value["qualification_commands"] = [
        {
            "ordinal": step.ordinal,
            "name": step.name,
            "command_hex": step.command.hex(),
            "expected_outcome": step.expected_outcome,
        }
        for step in observer.QUALIFICATION_COMMANDS
    ]
    value["later_acceptance_commands"] = observer.later_acceptance_binding()
    return value


def audit() -> dict[str, Any]:
    value = _base_audit()
    value.update(
        {
            "initial_observation": INITIAL_OBSERVATION,
            "initial_observation_field": observer.INITIAL_OBSERVATION_FIELD,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "same_fd_session_count": SAME_FD_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "idle_seconds": IDLE_SECONDS,
            "total_session_count": TOTAL_SESSION_COUNT,
            "total_command_count": TOTAL_COMMANDS,
            "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "later_action_lease_active": False,
            "later_acceptance_commands": observer.later_acceptance_binding(),
        }
    )
    value["contract"] = _contract()
    value["initial_collector"] = observer.audit_binding()
    return value
