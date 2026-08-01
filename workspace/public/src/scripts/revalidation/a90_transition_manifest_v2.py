#!/usr/bin/env python3
"""Pure H0 route contract for the future A90 transition-v2 adapter."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


BLUEPRINT_SCHEMA = "a90-transition-adapter-blueprint-v2"
BLUEPRINT_STATUS = "HOST_DESIGN_ONLY"
AUDIT_SCHEMA = "a90-transition-adapter-blueprint-v2-audit"
TARGET_PROFILE = "galaxy-a90-5g-native-init"
UNBOUND = "UNBOUND"

F1_WORKFLOW = "A90_F1_RESIDENT_INSTALL_V1"
D1_WORKFLOW = "A90_D1_ATTENDED_SESSION_V1"
F1_TIER = "F1_BOOT_ONLY_WITH_EXACT_ROLLBACK"
D1_TIER = "TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL"
D1_APPROVAL_SCOPE = "ATTENDED_SESSION_MAX_8H_32_ACTIONS"
D1_ACTION_ALLOWLIST = ("SWITCHROOT_EXPERIMENT",)
D1_MAX_DURATION_SEC = 8 * 60 * 60
D1_MAX_ACTIONS = 32
LEGACY_CLEANUP_SCOPE = "LEGACY_SEPARATE_CLEANUP_APPROVAL"

# This is a symbol inventory, not an immutable or semantic source proof.
# Exact source identity is deliberately deferred to the future activation
# manifest and its reviewed preflight consumer.
SOURCE_INVENTORY = {
    "transition_contract": {
        "path": (
            "workspace/public/src/scripts/revalidation/"
            "a90_transition_contract_v2.py"
        ),
        "callables": [
            "validate_attended_session_binding",
            "validate_successor_contracts",
        ],
    },
    "transition_engine": {
        "path": (
            "workspace/public/src/scripts/server-distro/"
            "a90_transition_engine_v2.py"
        ),
        "callables": ["execute_workflow", "open_attended_session"],
    },
    "resident_promotion": {
        "path": (
            "workspace/public/src/scripts/server-distro/"
            "a90_resident_promotion_v1.py"
        ),
        "callables": ["main"],
    },
    "f1_orchestrator": {
        "path": (
            "workspace/public/src/scripts/server-distro/"
            "a90_v3403_f1_orchestrator.py"
        ),
        "callables": [
            "arm_candidate_return_modemmanager_guard",
            "run_handoff",
            "wait_for_candidate_return_attended_once",
            "rebind_host_ncm_after_reenumeration",
            "verify_candidate_health",
        ],
    },
    "observation_pipeline": {
        "path": (
            "workspace/public/src/scripts/revalidation/"
            "a90_observation_pipeline.py"
        ),
        "callables": ["decide_phase2_display_run"],
    },
    "legacy_cleanup": {
        "path": (
            "workspace/public/src/scripts/server-distro/"
            "a90_v3405_retained_work_cleanup.py"
        ),
        "callables": ["execute_cleanup"],
    },
}

F1_BLOCKERS = (
    "CONNECTED_IMMUTABLE_MANIFEST_ABSENT",
    "FRESH_F1_APPROVAL_ABSENT",
    "F1_RESIDENT_TERMINAL_ADAPTER_UNIMPLEMENTED",
)
D1_BLOCKERS = (
    "D1_DURABLE_SESSION_JOURNAL_OWNER_ABSENT",
    "D1_DURABLE_REFUTATION_HISTORY_ABSENT",
    "D1_OBSERVER_REPAIR_RECORD_OWNER_ABSENT",
    "D1_SESSION_APPROVAL_CONSUMER_ABSENT",
    "D1_SESSION_EFFECTS_BACKEND_UNIMPLEMENTED",
    "D1_CLEANUP_APPROVAL_SCOPE_MISMATCH",
    "D1_CLEANUP_BASELINE_IDENTITY_MISMATCH",
)
GLOBAL_BLOCKERS = (
    "EXACT_LIVE_TARGET_UNBOUND",
    "REAL_EFFECTS_BACKEND_UNIMPLEMENTED",
    "IMMUTABLE_SOURCE_BINDING_DEFERRED_TO_ACTIVATION_MANIFEST",
    *F1_BLOCKERS,
    *D1_BLOCKERS,
)

_D1_ROUTES = (
    (
        "STATIC_SUCCESSOR_GATE",
        "transition_contract",
        "validate_successor_contracts",
        "none",
        "READY_FOR_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "PREFLIGHT",
        "f1_orchestrator",
        "verify_candidate_health",
        "read_only",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "GUARD_ARMED",
        "f1_orchestrator",
        "arm_candidate_return_modemmanager_guard",
        "transient_host_guard",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "HANDOFF_STARTED",
        "f1_orchestrator",
        "run_handoff",
        "transient_no_payload_control",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "DEBIAN_OBSERVED",
        "observation_pipeline",
        "decide_phase2_display_run",
        "read_only",
        "READY_FOR_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "NATIVE_RETURNED",
        "f1_orchestrator",
        "wait_for_candidate_return_attended_once",
        "read_only",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "NCM_REBOUND",
        "f1_orchestrator",
        "rebind_host_ncm_after_reenumeration",
        "transient_host_control",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
    (
        "WORK_CLEANED",
        "legacy_cleanup",
        "execute_cleanup",
        "fixed_path_unlink",
        "BLOCKED_LEGACY_APPROVAL_AND_BASELINE_CONTRACT",
        LEGACY_CLEANUP_SCOPE,
    ),
    (
        "HEALTH_VERIFIED",
        "f1_orchestrator",
        "verify_candidate_health",
        "read_only",
        "NEEDS_D1_ADAPTER",
        D1_APPROVAL_SCOPE,
    ),
)


class ManifestError(RuntimeError):
    """Raised when the non-live route contract is changed or widened."""


def _routes() -> list[dict[str, str]]:
    keys = ("phase", "source", "callable", "effect_kind", "status", "approval_scope")
    return [dict(zip(keys, row, strict=True)) for row in _D1_ROUTES]


def expected_blueprint() -> dict[str, Any]:
    """Return a fresh copy of the one reviewed H0 route table."""

    return {
        "schema": BLUEPRINT_SCHEMA,
        "status": BLUEPRINT_STATUS,
        "host_only": True,
        "live_ready": False,
        "device_authority": False,
        "approval_preparation": False,
        "source_identity_bound": False,
        "target": {
            "profile": TARGET_PROFILE,
            "live_identity": UNBOUND,
            "exact_target_required": True,
            "other_targets_untouched_required": True,
        },
        "workflows": {
            F1_WORKFLOW: {
                "risk_tier": F1_TIER,
                "live_ready": False,
                "execution_model": "delegate_whole_transaction",
                "delegated_owner": "resident_promotion.main",
                "phases_owned_by_adapter": [],
                "approval_owner": "f1_orchestrator",
                "journal_owner": "f1_orchestrator",
                "rollback_owner": "f1_orchestrator",
                "blockers": list(F1_BLOCKERS),
            },
            D1_WORKFLOW: {
                "risk_tier": D1_TIER,
                "live_ready": False,
                "execution_model": "bounded_attended_session_injected_effects",
                "approval_scope": D1_APPROVAL_SCOPE,
                "session_limits": {
                    "max_duration_sec": D1_MAX_DURATION_SEC,
                    "max_actions": D1_MAX_ACTIONS,
                },
                "action_allowlist": list(D1_ACTION_ALLOWLIST),
                "journal_owner": UNBOUND,
                "approval_consumer": UNBOUND,
                "routes": _routes(),
                "blockers": list(D1_BLOCKERS),
            },
        },
        "source_inventory": deepcopy(SOURCE_INVENTORY),
        "blockers": list(GLOBAL_BLOCKERS),
    }


def validate_blueprint(value: Any) -> dict[str, Any]:
    """Reject any widening of the exact host-only route table."""

    if not isinstance(value, dict):
        raise ManifestError("blueprint is not an object")
    if (
        value.get("host_only") is not True
        or value.get("live_ready") is not False
        or value.get("device_authority") is not False
        or value.get("approval_preparation") is not False
        or value.get("source_identity_bound") is not False
    ):
        raise ManifestError("blueprint attempted to leave H0 design posture")
    try:
        f1 = value["workflows"][F1_WORKFLOW]
        d1 = value["workflows"][D1_WORKFLOW]
    except (KeyError, TypeError) as exc:
        raise ManifestError("workflow set is not exact") from exc
    if not isinstance(f1, dict) or not isinstance(d1, dict):
        raise ManifestError("workflow entries are not exact")
    if f1.get("phases_owned_by_adapter") != []:
        raise ManifestError("resident F1 must remain a whole-owner delegation")
    routes = d1.get("routes")
    if not isinstance(routes, list):
        raise ManifestError("D1 routes are not exact")
    for route in routes:
        if not isinstance(route, dict):
            raise ManifestError("D1 route is not exact")
        effect = route.get("effect_kind")
        if not isinstance(effect, str):
            raise ManifestError("D1 route effect is not exact")
        if effect in {"flash", "payload_transfer", "partition_write"}:
            raise ManifestError("D1 route contains a payload or flash effect")
    expected = expected_blueprint()
    if value != expected:
        raise ManifestError("blueprint left the exact H0 route contract")
    return value
