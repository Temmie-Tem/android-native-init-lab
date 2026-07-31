#!/usr/bin/env python3
"""Single effects-injected state engine for the reduced A90 workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Mapping
from typing import Any, Protocol

from a90_transition_contract_v2 import (
    ApprovalBinding,
    ContractError,
    DisplayProof,
    FailureSignature,
    IDENTITY_RE,
    ProofState,
    SuccessorContract,
    Workflow,
    repeated_failure_gate,
    validate_successor_contracts,
)


ENGINE_SCHEMA = "a90-transition-engine-v2"


class EffectStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class EffectResult:
    status: EffectStatus
    effect_started: bool
    failure_class: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.status, EffectStatus):
            raise ContractError("effect status is not an exact enum")
        if type(self.effect_started) is not bool:
            raise ContractError("effect_started is not an exact boolean")
        if not isinstance(self.evidence, Mapping):
            raise ContractError("effect evidence is not a mapping")
        if self.failure_class is not None and (
            not isinstance(self.failure_class, str)
            or IDENTITY_RE.fullmatch(self.failure_class) is None
        ):
            raise ContractError("effect failure class is not exact")
        if self.status is EffectStatus.PASS and self.failure_class is not None:
            raise ContractError("passing effect has a failure class")
        if self.status is not EffectStatus.PASS and not self.failure_class:
            raise ContractError("failed effect lacks a failure class")
        if (
            self.status is EffectStatus.AMBIGUOUS
            and not str(self.failure_class).endswith("_AMBIGUOUS")
        ):
            raise ContractError("ambiguous effect class lacks exact suffix")


class Effects(Protocol):
    mode: str

    def consume_approval_once(self, approval: ApprovalBinding) -> bool: ...

    def record_intent(self, workflow: Workflow, phase: str) -> None: ...

    def invoke(self, workflow: Workflow, phase: str) -> EffectResult: ...


@dataclass(frozen=True)
class RunContract:
    approval: ApprovalBinding
    successors: tuple[SuccessorContract, ...]
    consumed_approval_ids: frozenset[str] = frozenset()
    previous_failure_signatures: tuple[FailureSignature, ...] = ()

    def validate(self) -> None:
        self.approval.validate()
        validate_successor_contracts(self.successors)
        if self.approval.approval_id in self.consumed_approval_ids:
            raise ContractError("approval is not fresh for this run")
        gate = repeated_failure_gate(self.previous_failure_signatures)
        if gate != "ALLOW_FRESH_PREPARATION":
            raise ContractError(f"fresh preparation refused: {gate}")


@dataclass
class _RunState:
    contract: RunContract
    effects: Effects
    history: list[str] = field(default_factory=lambda: ["PREFLIGHT"])
    counts: dict[str, int] = field(default_factory=dict)
    last_proven: str = "PREFLIGHT"
    candidate_effect_started: bool = False
    failure_signature: FailureSignature | None = None
    secondary_failure_signatures: list[FailureSignature] = field(default_factory=list)
    visibility: str = "NOT_APPLICABLE"

    def run_effect(self, phase: str) -> EffectResult:
        try:
            self.effects.record_intent(self.contract.approval.workflow, phase)
        except Exception:  # noqa: BLE001 - never perform an unjournaled effect
            self.history.append(f"{phase}_INTENT_AMBIGUOUS")
            key = f"{phase}_INTENT_FAILURE"
            self.counts[key] = self.counts.get(key, 0) + 1
            return EffectResult(
                EffectStatus.AMBIGUOUS,
                effect_started=False,
                failure_class="INTENT_RECORD_AMBIGUOUS",
            )
        self.history.append(f"{phase}_INTENT")
        result: EffectResult | None = None
        try:
            result = self.effects.invoke(self.contract.approval.workflow, phase)
            result.validate()
        except Exception:  # noqa: BLE001 - uncertain candidate effects recover
            result = EffectResult(
                EffectStatus.AMBIGUOUS,
                effect_started=True,
                failure_class="EFFECT_EXCEPTION_AMBIGUOUS",
            )
        self.counts[phase] = self.counts.get(phase, 0) + 1
        if phase == "CANDIDATE_FLASH" and (
            result.effect_started or result.status is EffectStatus.PASS
        ):
            self.candidate_effect_started = True
        if result.status is EffectStatus.PASS:
            self.history.append(f"{phase}_PROVEN")
            self.last_proven = f"{phase}_PROVEN"
        return result

    def fail(self, phase: str, result: EffectResult) -> None:
        self.failure_signature = FailureSignature(
            workflow=self.contract.approval.workflow.value,
            phase=phase,
            failure_class=str(result.failure_class),
            effect_started=result.effect_started,
            last_proven_boundary=self.last_proven,
        )

    def result(self, terminal: str) -> dict[str, Any]:
        return {
            "schema": ENGINE_SCHEMA,
            "terminal": terminal,
            "workflow": self.contract.approval.workflow.value,
            "risk_tier": self.contract.approval.risk_tier.value,
            "effects_mode": self.effects.mode,
            "history": self.history,
            "counts": dict(sorted(self.counts.items())),
            "candidate_replay": False,
            "failure_signature": (
                self.failure_signature.to_dict()
                if self.failure_signature is not None
                else None
            ),
            "secondary_failure_signatures": [
                signature.to_dict()
                for signature in self.secondary_failure_signatures
            ],
            "display_visibility": self.visibility,
        }


RESIDENT_PHASES = (
    "ROOTFS_STAGE",
    "CANDIDATE_FLASH",
    "CANDIDATE_HEALTH",
    "RESIDENT_REBOOT",
    "RESIDENT_HEALTH",
)
ROLLBACK_PHASES = ("ROLLBACK_FLASH", "ROLLBACK_HEALTH")
D1_PHASES = (
    "GUARD_ARM",
    "HANDOFF",
    "DEBIAN_OBSERVATION",
    "NATIVE_RETURN",
    "WORK_CLEANUP",
    "FINAL_HEALTH",
)


def _start_run(contract: RunContract, effects: Effects) -> _RunState:
    contract.validate()
    state = _RunState(contract, effects)
    try:
        consumed = effects.consume_approval_once(contract.approval)
    except Exception as exc:  # noqa: BLE001 - no effect before durable consume
        raise ContractError("approval consumption is unavailable") from exc
    if consumed is not True:
        raise ContractError("approval was already consumed or not durable")
    state.history.append("APPROVAL_CONSUMED")
    state.counts["APPROVAL_CONSUME"] = 1
    state.last_proven = "APPROVAL_CONSUMED"
    return state


def _rollback(state: _RunState) -> dict[str, Any]:
    for phase in ROLLBACK_PHASES:
        result = state.run_effect(phase)
        if result.status is not EffectStatus.PASS:
            state.fail(phase, result)
            state.history.append("RECOVERY_REQUIRED")
            return state.result("RECOVERY_REQUIRED")
    state.history.append("ROLLED_BACK_CLOSED")
    return state.result("ROLLED_BACK_CLOSED")


def run_resident_install(
    contract: RunContract,
    effects: Effects,
) -> dict[str, Any]:
    if contract.approval.workflow is not Workflow.RESIDENT_INSTALL_F1:
        raise ContractError("resident engine requires the F1 install workflow")
    state = _start_run(contract, effects)
    for phase in RESIDENT_PHASES:
        result = state.run_effect(phase)
        if result.status is EffectStatus.PASS:
            continue
        state.fail(phase, result)
        if result.status is EffectStatus.AMBIGUOUS:
            state.history.append("STOP_AMBIGUOUS")
        if state.candidate_effect_started:
            return _rollback(state)
        state.history.append("ABORTED_BEFORE_CANDIDATE")
        return state.result("ABORTED_BEFORE_CANDIDATE")
    state.history.append("PROMOTED_CLOSED")
    return state.result("PROMOTED_CLOSED")


def _proof_state(value: Any, *, label: str) -> ProofState:
    try:
        return ProofState(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} proof state is not exact") from exc


def _display_proof(evidence: Mapping[str, Any]) -> DisplayProof:
    required = {
        "native_release",
        "debian_pid1",
        "dropbear",
        "drm_master_acquired",
        "connector_connected",
        "modeset_committed",
        "backlight_enabled",
        "dpms_on",
        "visible_confirmed",
        "visibility_source",
    }
    if set(evidence) != required:
        raise ContractError("display observation evidence key set is not exact")
    return DisplayProof(
        **{
            key: _proof_state(evidence[key], label=key)
            for key in required - {"visibility_source"}
        },
        visibility_source=evidence["visibility_source"],
    )


def run_switchroot_experiment(
    contract: RunContract,
    effects: Effects,
) -> dict[str, Any]:
    if contract.approval.workflow is not Workflow.SWITCHROOT_EXPERIMENT_D1:
        raise ContractError("switch-root engine requires the D1 workflow")
    state = _start_run(contract, effects)
    deferred_terminal: str | None = None
    deferred_signature: FailureSignature | None = None

    def defer(terminal: str) -> None:
        nonlocal deferred_terminal, deferred_signature
        if deferred_terminal == "STOP_AMBIGUOUS":
            if (
                state.failure_signature is not None
                and state.failure_signature != deferred_signature
            ):
                state.secondary_failure_signatures.append(state.failure_signature)
            return
        if deferred_terminal is None or terminal == "STOP_AMBIGUOUS":
            if (
                terminal == "STOP_AMBIGUOUS"
                and deferred_signature is not None
                and deferred_signature != state.failure_signature
            ):
                state.secondary_failure_signatures.append(deferred_signature)
            deferred_terminal = terminal
            deferred_signature = state.failure_signature

    for phase in D1_PHASES:
        result = state.run_effect(phase)
        if result.status is not EffectStatus.PASS:
            state.fail(phase, result)
            terminal = (
                "STOP_AMBIGUOUS"
                if result.status is EffectStatus.AMBIGUOUS
                else "STOPPED_NO_RETRY"
            )
            if (
                (phase == "HANDOFF" and result.effect_started)
                or phase in {"DEBIAN_OBSERVATION", "WORK_CLEANUP"}
            ):
                defer(terminal)
                continue
            if deferred_terminal == "STOP_AMBIGUOUS":
                if (
                    state.failure_signature is not None
                    and state.failure_signature != deferred_signature
                ):
                    state.secondary_failure_signatures.append(
                        state.failure_signature
                    )
                state.failure_signature = deferred_signature
                terminal = "STOP_AMBIGUOUS"
            state.history.append(terminal)
            return state.result(terminal)
        if phase != "DEBIAN_OBSERVATION":
            continue
        state.history[-1] = "DEBIAN_OBSERVATION_CAPTURED"
        state.last_proven = "DEBIAN_OBSERVATION_CAPTURED"
        try:
            proof = _display_proof(result.evidence)
            missing = proof.first_nonproven()
        except Exception:  # noqa: BLE001 - malformed evidence is ambiguous
            failure = EffectResult(
                EffectStatus.AMBIGUOUS,
                effect_started=False,
                failure_class="OBSERVATION_EVIDENCE_AMBIGUOUS",
            )
            state.fail(phase, failure)
            defer("STOP_AMBIGUOUS")
            continue
        if missing is not None:
            name, proof_state = missing
            failure = EffectResult(
                EffectStatus.FAIL,
                effect_started=True,
                failure_class=f"{name.upper()}_{proof_state.value}",
            )
            state.fail(phase, failure)
            defer("STOPPED_NO_RETRY")
            continue
        state.history.append("DISPLAY_MECHANICAL_PROVEN")
        state.last_proven = "DISPLAY_MECHANICAL_PROVEN"
        if proof.visible_confirmed is ProofState.PROVEN:
            state.visibility = "PROVEN"
            state.history.append("DISPLAY_VISIBILITY_PROVEN")
            state.last_proven = "DISPLAY_VISIBILITY_PROVEN"
        elif proof.visible_confirmed is ProofState.UNAVAILABLE:
            state.visibility = "NO_PROOF_DISPLAY_VISIBILITY"
        else:
            failure = EffectResult(
                EffectStatus.FAIL,
                effect_started=True,
                failure_class="VISIBLE_CONFIRMED_REFUTED",
            )
            state.fail(phase, failure)
            defer("STOPPED_NO_RETRY")
            continue
    if deferred_terminal is not None:
        state.failure_signature = deferred_signature
        state.history.append(deferred_terminal)
        return state.result(deferred_terminal)
    terminal = (
        "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY"
        if state.visibility == "NO_PROOF_DISPLAY_VISIBILITY"
        else "PASS_SWITCHROOT_RETURN_VISIBLE"
    )
    state.history.append(terminal)
    return state.result(terminal)


def execute_workflow(contract: RunContract, effects: Effects) -> dict[str, Any]:
    """Use one state path for injected simulation or future reviewed effects."""

    if contract.approval.workflow is Workflow.RESIDENT_INSTALL_F1:
        return run_resident_install(contract, effects)
    if contract.approval.workflow is Workflow.SWITCHROOT_EXPERIMENT_D1:
        return run_switchroot_experiment(contract, effects)
    raise ContractError("workflow is not implemented")


@dataclass
class ScriptedEffects:
    """Deterministic H0 adapter; it implements the same port as live effects."""

    outcomes: Mapping[str, EffectResult]
    mode: str = "SIMULATED_H0"
    events: list[str] = field(default_factory=list)
    consumed_approval_ids: set[str] = field(default_factory=set)

    def consume_approval_once(self, approval: ApprovalBinding) -> bool:
        self.events.append(f"APPROVAL_CONSUME:{approval.approval_id}")
        if approval.approval_id in self.consumed_approval_ids:
            return False
        self.consumed_approval_ids.add(approval.approval_id)
        return True

    def record_intent(self, workflow: Workflow, phase: str) -> None:
        self.events.append(f"INTENT:{workflow.value}:{phase}")

    def invoke(self, workflow: Workflow, phase: str) -> EffectResult:
        self.events.append(f"EFFECT:{workflow.value}:{phase}")
        return self.outcomes.get(
            phase,
            EffectResult(EffectStatus.PASS, effect_started=True),
        )
