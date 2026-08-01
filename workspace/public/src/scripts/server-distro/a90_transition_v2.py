#!/usr/bin/env python3
"""Thin H0 simulation CLI for the A90 transition-v2 state engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REVAL_DIR = Path(__file__).resolve().parents[1] / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

from a90_transition_contract_v2 import (  # noqa: E402
    ApprovalBinding,
    AttendedSessionBinding,
    DISPLAY_SUCCESSOR,
    FailureSignature,
    ObserverRepair,
    ProofState,
    RiskTier,
    SessionAction,
    SessionPreflight,
    Workflow,
    repeated_failure_gate,
)
from a90_transition_engine_v2 import (  # noqa: E402
    AttendedSessionContract,
    EffectResult,
    EffectStatus,
    RunContract,
    ScriptedSessionEffects,
    ScriptedEffects,
    SessionActionResult,
    SessionActionStatus,
    execute_workflow,
    open_attended_session,
)


CLI_SCHEMA = "a90-transition-v2-h0-cli"
SESSION_START_EPOCH_SEC = 2_000_000_000
SIMULATIONS = (
    "resident-success",
    "resident-post-flash-failure",
    "resident-ambiguous-flash",
    "d1-visible",
    "d1-unattended",
    "d1-display-failure",
    "d1-return-ambiguous",
    "session-two-actions",
    "session-observer-no-proof",
    "session-control-ambiguous",
    "session-expired",
    "session-unallowlisted",
    "repeat-gate",
)


def _approval(workflow: Workflow, suffix: str) -> ApprovalBinding:
    tier = (
        RiskTier.F1_BOOT_ONLY_WITH_EXACT_ROLLBACK
        if workflow is Workflow.RESIDENT_INSTALL_F1
        else RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL
    )
    return ApprovalBinding(
        approval_id=f"simulation-{suffix}",
        workflow=workflow,
        risk_tier=tier,
        target_profile="A90_SIMULATION_ONLY",
        manifest_sha256="0" * 64,
    )


def _display_evidence(visible: ProofState) -> dict[str, str | None]:
    return {
        "native_release": ProofState.PROVEN.value,
        "debian_pid1": ProofState.PROVEN.value,
        "dropbear": ProofState.PROVEN.value,
        "drm_master_acquired": ProofState.PROVEN.value,
        "connector_connected": ProofState.PROVEN.value,
        "modeset_committed": ProofState.PROVEN.value,
        "backlight_enabled": ProofState.PROVEN.value,
        "dpms_on": ProofState.PROVEN.value,
        "visible_confirmed": visible.value,
        "visibility_source": "operator" if visible is ProofState.PROVEN else None,
    }


def _safe_session_preflight() -> SessionPreflight:
    return SessionPreflight(
        operator_attended=True,
        target_identity_matches=True,
        resident_identity_matches=True,
        rollback_ready=True,
        recovery_available=True,
    )


def _session_binding(name: str) -> AttendedSessionBinding:
    return AttendedSessionBinding(
        approval_id=f"simulation-{name}",
        workflow=Workflow.ATTENDED_SESSION_D1,
        risk_tier=RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
        target_profile="A90_SIMULATION_ONLY",
        manifest_sha256="1" * 64,
        resident_boot_sha256="2" * 64,
        rollback_boot_sha256="3" * 64,
        recovery_profile="A90_SIMULATION_RECOVERY",
        device_effect_runner_sha256="4" * 64,
        observer_sha256="5" * 64,
        return_health_profile="A90_SIMULATION_HEALTH",
        action_allowlist=(SessionAction.SWITCHROOT_EXPERIMENT,),
        not_before_epoch_sec=SESSION_START_EPOCH_SEC,
        expires_at_epoch_sec=SESSION_START_EPOCH_SEC + 8 * 60 * 60,
        max_actions=3,
    )


def _simulate_session(name: str) -> dict[str, Any]:
    safe = _safe_session_preflight()
    if name == "session-two-actions":
        outcomes = (
            SessionActionResult(
                SessionActionStatus.PROVED,
                action_started=True,
                postflight=safe,
            ),
            SessionActionResult(
                SessionActionStatus.REFUTED,
                action_started=True,
                failure_class="DISPLAY_VISIBILITY_REFUTED",
                postflight=safe,
            ),
        )
    elif name == "session-observer-no-proof":
        outcomes = (
            SessionActionResult(
                SessionActionStatus.NO_PROOF_OBSERVER,
                action_started=True,
                failure_class="RETURN_FRAME_OBSERVER",
                postflight=safe,
                independent_safety_check=True,
            ),
        )
    elif name == "session-control-ambiguous":
        outcomes = (
            SessionActionResult(
                SessionActionStatus.CONTROL_AMBIGUOUS,
                action_started=True,
                failure_class="RETURN_CONTROL_AMBIGUOUS",
            ),
        )
    else:
        outcomes = (
            SessionActionResult(
                SessionActionStatus.PROVED,
                action_started=True,
                postflight=safe,
            ),
        )
    effects = ScriptedSessionEffects(outcomes)
    session = open_attended_session(
        AttendedSessionContract(
            binding=_session_binding(name),
            successors=(DISPLAY_SUCCESSOR,),
        ),
        effects,
        now_epoch_sec=SESSION_START_EPOCH_SEC,
        preflight=safe,
    )
    if name == "session-two-actions":
        session.run_action(
            SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe,
        )
        result = session.run_action(
            SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
            preflight=safe,
        )
    elif name == "session-expired":
        result = session.run_action(
            SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=session.contract.binding.expires_at_epoch_sec,
            preflight=safe,
        )
    elif name == "session-unallowlisted":
        result = session.run_action(
            "NATIVE_UI_HIDE",  # type: ignore[arg-type]
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe,
        )
    else:
        result = session.run_action(
            SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe,
        )
    return {
        "schema": CLI_SCHEMA,
        "host_only": True,
        "device_action": False,
        "flash": False,
        "live_backend_present": False,
        "scenario": name,
        "result": result,
        "effect_events": effects.events,
    }


def simulate(name: str) -> dict[str, Any]:
    if name.startswith("session-"):
        return _simulate_session(name)
    if name == "repeat-gate":
        signature = FailureSignature(
            workflow=Workflow.SWITCHROOT_EXPERIMENT_D1.value,
            phase="NATIVE_RETURN",
            failure_class="RETURN_TIMEOUT",
            effect_started=True,
            last_proven_boundary="DEBIAN_OBSERVATION_PROVEN",
        )
        return {
            "schema": CLI_SCHEMA,
            "host_only": True,
            "live_backend_present": False,
            "scenario": name,
            "gate": repeated_failure_gate((signature, signature)),
        }

    resident = name.startswith("resident-")
    workflow = (
        Workflow.RESIDENT_INSTALL_F1
        if resident
        else Workflow.SWITCHROOT_EXPERIMENT_D1
    )
    outcomes: dict[str, EffectResult] = {}
    if name == "resident-post-flash-failure":
        outcomes["CANDIDATE_HEALTH"] = EffectResult(
            EffectStatus.FAIL,
            effect_started=True,
            failure_class="CANDIDATE_HEALTH_FAILED",
        )
    elif name == "resident-ambiguous-flash":
        outcomes["CANDIDATE_FLASH"] = EffectResult(
            EffectStatus.AMBIGUOUS,
            effect_started=True,
            failure_class="CANDIDATE_TRANSFER_AMBIGUOUS",
        )
    elif name in {"d1-visible", "d1-unattended", "d1-display-failure"}:
        visible = (
            ProofState.PROVEN
            if name == "d1-visible"
            else ProofState.UNAVAILABLE
        )
        evidence = _display_evidence(visible)
        if name == "d1-display-failure":
            evidence["modeset_committed"] = ProofState.REFUTED.value
        outcomes["DEBIAN_OBSERVATION"] = EffectResult(
            EffectStatus.PASS,
            effect_started=False,
            evidence=evidence,
        )
    elif name == "d1-return-ambiguous":
        outcomes["DEBIAN_OBSERVATION"] = EffectResult(
            EffectStatus.PASS,
            effect_started=False,
            evidence=_display_evidence(ProofState.UNAVAILABLE),
        )
        outcomes["NATIVE_RETURN"] = EffectResult(
            EffectStatus.AMBIGUOUS,
            effect_started=False,
            failure_class="RETURN_CHANNEL_AMBIGUOUS",
        )

    contract = RunContract(
        approval=_approval(workflow, name),
        successors=(DISPLAY_SUCCESSOR,),
    )
    effects = ScriptedEffects(outcomes)
    result = execute_workflow(contract, effects)
    return {
        "schema": CLI_SCHEMA,
        "host_only": True,
        "device_action": False,
        "flash": False,
        "live_backend_present": False,
        "scenario": name,
        "result": result,
        "effect_events": effects.events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", choices=SIMULATIONS, required=True)
    args = parser.parse_args()
    print(json.dumps(simulate(args.simulate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
