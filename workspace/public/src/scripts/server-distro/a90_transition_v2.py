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
    DISPLAY_SUCCESSOR,
    FailureSignature,
    ProofState,
    RiskTier,
    Workflow,
    repeated_failure_gate,
)
from a90_transition_engine_v2 import (  # noqa: E402
    EffectResult,
    EffectStatus,
    RunContract,
    ScriptedEffects,
    execute_workflow,
)


CLI_SCHEMA = "a90-transition-v2-h0-cli"
SIMULATIONS = (
    "resident-success",
    "resident-post-flash-failure",
    "resident-ambiguous-flash",
    "d1-visible",
    "d1-unattended",
    "d1-display-failure",
    "d1-return-ambiguous",
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


def simulate(name: str) -> dict[str, Any]:
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
