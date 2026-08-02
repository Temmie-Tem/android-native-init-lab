#!/usr/bin/env python3
"""Single effects-injected state engine for the reduced A90 workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Mapping
from typing import Any, Protocol

from a90_transition_contract_v2 import (
    ApprovalBinding,
    AttendedSessionBinding,
    ConfirmedRefutation,
    ContractError,
    DisplayProof,
    FailureSignature,
    IDENTITY_RE,
    ObserverRepair,
    ProofState,
    SessionAction,
    SessionPreflight,
    SuccessorContract,
    Workflow,
    repeated_failure_gate,
    validate_attended_session_binding,
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


class SessionActionStatus(str, Enum):
    PROVED = "PROVED"
    REFUTED = "REFUTED"
    NO_PROOF_OBSERVER = "NO_PROOF_OBSERVER"
    EXPERIMENT_BLOCKED = "EXPERIMENT_BLOCKED"
    WINDOW_EXPIRED_NO_EFFECT = "WINDOW_EXPIRED_NO_EFFECT"
    DEVICE_SAFETY_FAILURE = "DEVICE_SAFETY_FAILURE"
    CONTROL_AMBIGUOUS = "CONTROL_AMBIGUOUS"


@dataclass(frozen=True)
class SessionActionResult:
    status: SessionActionStatus
    action_started: bool
    failure_class: str | None = None
    postflight: SessionPreflight | None = None
    independent_safety_check: bool = False

    def validate(self) -> None:
        if not isinstance(self.status, SessionActionStatus):
            raise ContractError("session action status is not exact")
        if type(self.action_started) is not bool:
            raise ContractError("session action_started is not boolean")
        if type(self.independent_safety_check) is not bool:
            raise ContractError("session independent safety check is not boolean")
        if self.failure_class is not None and (
            not isinstance(self.failure_class, str)
            or IDENTITY_RE.fullmatch(self.failure_class) is None
        ):
            raise ContractError("session failure class is not exact")
        continuing = {
            SessionActionStatus.PROVED,
            SessionActionStatus.REFUTED,
            SessionActionStatus.NO_PROOF_OBSERVER,
        }
        if self.status is SessionActionStatus.PROVED:
            if self.failure_class is not None:
                raise ContractError("proved session action has a failure class")
        elif not self.failure_class:
            raise ContractError("non-proved session action lacks a failure class")
        if self.status in continuing:
            if self.action_started is not True:
                raise ContractError("continuing session action was not started")
            if not isinstance(self.postflight, SessionPreflight):
                raise ContractError("continuing session action lacks postflight")
            self.postflight.validate()
        elif self.postflight is not None:
            if self.status is not SessionActionStatus.EXPERIMENT_BLOCKED:
                raise ContractError("unsafe session action cannot claim postflight")
            self.postflight.validate()
        if (
            self.status is SessionActionStatus.NO_PROOF_OBSERVER
            and (
                not str(self.failure_class).endswith("_OBSERVER")
                or self.independent_safety_check is not True
            )
        ):
            raise ContractError("observer no-proof is not independently bounded")
        if (
            self.status is SessionActionStatus.REFUTED
            and not str(self.failure_class).endswith("_REFUTED")
        ):
            raise ContractError("refuted action class is not exact")
        if (
            self.status is SessionActionStatus.EXPERIMENT_BLOCKED
            and (
                self.action_started is not True
                or not str(self.failure_class).endswith("_BLOCKED")
                or not isinstance(self.postflight, SessionPreflight)
            )
        ):
            raise ContractError("blocked experiment lacks exact healthy stop")
        if (
            self.status is SessionActionStatus.WINDOW_EXPIRED_NO_EFFECT
            and (
                self.action_started is not False
                or self.failure_class != "SESSION_WINDOW_EXPIRED"
                or self.postflight is not None
                or self.independent_safety_check is not False
            )
        ):
            raise ContractError("expired session action claims a device effect")
        if (
            self.status is SessionActionStatus.CONTROL_AMBIGUOUS
            and not str(self.failure_class).endswith("_AMBIGUOUS")
        ):
            raise ContractError("control ambiguity class is not exact")


def _validate_attended_preflight(preflight: SessionPreflight) -> None:
    if not isinstance(preflight, SessionPreflight):
        raise ContractError("attended session preflight type is not exact")
    preflight.validate()
    if (
        preflight.operator_attended is not True
        or preflight.unattended_resident_d1_qualified is not False
    ):
        raise ContractError("attended session requires operator attendance")


class SessionEffects(Protocol):
    mode: str

    def consume_session_approval_once(
        self,
        binding: AttendedSessionBinding,
    ) -> bool: ...

    def record_action_intent(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
        observer_no_proof_acknowledged: bool,
    ) -> None: ...

    def invoke_action(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
    ) -> SessionActionResult: ...

    def record_observer_repair(
        self,
        binding: AttendedSessionBinding,
        repair: ObserverRepair,
    ) -> None: ...


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


@dataclass(frozen=True)
class AttendedSessionContract:
    binding: AttendedSessionBinding
    successors: tuple[SuccessorContract, ...]
    consumed_approval_ids: frozenset[str] = frozenset()
    previous_refutations: tuple[ConfirmedRefutation, ...] = ()

    def validate(self) -> None:
        validate_attended_session_binding(self.binding)
        validate_successor_contracts(self.successors)
        if self.binding.approval_id in self.consumed_approval_ids:
            raise ContractError("session approval is not fresh")
        counts: dict[tuple[SessionAction, str], int] = {}
        for item in self.previous_refutations:
            if not isinstance(item, ConfirmedRefutation):
                raise ContractError("previous refutation type is not exact")
            item.validate()
            key = (item.action, item.failure_class)
            counts[key] = counts.get(key, 0) + 1
            if counts[key] >= 2:
                raise ContractError("repeated confirmed refutation stops the live line")


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
    device_safety_state: str = "BASELINE_HEALTHY"

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
            "device_safety_state": self.device_safety_state,
        }


RESIDENT_PHASES = (
    "ROOTFS_STAGE",
    "CANDIDATE_FLASH",
    "CANDIDATE_HEALTH",
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
            state.device_safety_state = "RECOVERY_REQUIRED"
            state.history.append("RECOVERY_REQUIRED")
            return state.result("RECOVERY_REQUIRED")
    state.device_safety_state = "BASELINE_HEALTHY"
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
            if phase == "CANDIDATE_HEALTH":
                state.device_safety_state = "RESIDENT_HEALTHY"
            continue
        state.fail(phase, result)
        if result.status is EffectStatus.AMBIGUOUS:
            state.history.append("STOP_AMBIGUOUS")
        if state.candidate_effect_started:
            return _rollback(state)
        state.history.append("ABORTED_BEFORE_CANDIDATE")
        return state.result("ABORTED_BEFORE_CANDIDATE")
    state.history.append("PASS_A90_RESIDENT_INSTALLED")
    return state.result("PASS_A90_RESIDENT_INSTALLED")


@dataclass
class AttendedSession:
    contract: AttendedSessionContract
    effects: SessionEffects
    history: list[str] = field(
        default_factory=lambda: [
            "SESSION_PREFLIGHT_PROVEN",
            "SESSION_APPROVAL_CONSUMED",
        ]
    )
    opened_at_epoch_sec: int = 0
    actions_used: int = 0
    last_now_epoch_sec: int = 0
    closed_terminal: str | None = None
    device_safety_state: str = "RESIDENT_HEALTHY"
    action_results: list[dict[str, Any]] = field(default_factory=list)
    refutation_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    active_observer_sha256: str = ""
    observer_repair_required: bool = False
    observer_no_proof_acknowledgements: int = 0

    def _snapshot(self, terminal: str) -> dict[str, Any]:
        return {
            "schema": ENGINE_SCHEMA,
            "workflow": self.contract.binding.workflow.value,
            "risk_tier": self.contract.binding.risk_tier.value,
            "effects_mode": self.effects.mode,
            "terminal": terminal,
            "session_open": self.closed_terminal is None,
            "session_active": (
                self.closed_terminal is None and not self.observer_repair_required
            ),
            "observer_repair_required": self.observer_repair_required,
            "observer_no_proof_acknowledgements": (
                self.observer_no_proof_acknowledgements
            ),
            "active_observer_sha256": self.active_observer_sha256,
            "actions_used": self.actions_used,
            "actions_remaining": (
                self.contract.binding.max_actions - self.actions_used
            ),
            "opened_at_epoch_sec": self.opened_at_epoch_sec,
            "expires_at_epoch_sec": self.contract.binding.expires_at_epoch_sec,
            "last_now_epoch_sec": self.last_now_epoch_sec,
            "device_safety_state": self.device_safety_state,
            "candidate_transfer": False,
            "rollback_transfer": False,
            "payload_transfer": False,
            "action_replay": False,
            "history": list(self.history),
            "action_results": list(self.action_results),
        }

    def _close(self, terminal: str) -> dict[str, Any]:
        self.closed_terminal = terminal
        self.history.append(terminal)
        return self._snapshot(terminal)

    def run_action(
        self,
        action: SessionAction,
        *,
        now_epoch_sec: int,
        preflight: SessionPreflight,
        acknowledge_observer_no_proof: bool = False,
    ) -> dict[str, Any]:
        if self.closed_terminal is not None:
            raise ContractError("attended session is already closed")
        if type(acknowledge_observer_no_proof) is not bool:
            raise ContractError("observer no-proof acknowledgement is not boolean")
        if self.observer_repair_required:
            if acknowledge_observer_no_proof is not True:
                raise ContractError(
                    "observer no-proof acknowledgement or repair is required "
                    "before another action"
                )
            if self.observer_no_proof_acknowledgements >= 1:
                return self._close("SESSION_CLOSED_REPEATED_OBSERVER_NO_PROOF")
            self.observer_repair_required = False
            self.observer_no_proof_acknowledgements += 1
            self.history.append("OBSERVER_NO_PROOF_ACKNOWLEDGED_FOR_NEW_ACTION")
        elif acknowledge_observer_no_proof:
            raise ContractError("observer no-proof acknowledgement is unexpected")
        if (
            type(now_epoch_sec) is not int
            or now_epoch_sec < self.last_now_epoch_sec
        ):
            raise ContractError("session time is not monotonic")
        self.last_now_epoch_sec = now_epoch_sec
        if now_epoch_sec >= self.contract.binding.expires_at_epoch_sec:
            return self._close("SESSION_CLOSED_EXPIRED")
        if self.actions_used >= self.contract.binding.max_actions:
            return self._close("SESSION_CLOSED_BUDGET_EXHAUSTED")
        if not isinstance(action, SessionAction) or (
            action not in self.contract.binding.action_allowlist
        ):
            return self._close("SESSION_CLOSED_UNALLOWLISTED_ACTION")
        try:
            _validate_attended_preflight(preflight)
        except Exception:  # noqa: BLE001 - no action before exact safe preflight
            if (
                isinstance(preflight, SessionPreflight)
                and preflight.operator_attended is False
                and all(
                    value is True
                    for value in (
                        preflight.target_identity_matches,
                        preflight.resident_identity_matches,
                        preflight.rollback_ready,
                        preflight.recovery_available,
                    )
                )
            ):
                return self._close("SESSION_CLOSED_OPERATOR_ABSENT")
            self.device_safety_state = "RECOVERY_REQUIRED"
            return self._close("RECOVERY_REQUIRED")

        ordinal = self.actions_used + 1
        try:
            self.effects.record_action_intent(
                self.contract.binding,
                ordinal,
                action,
                self.active_observer_sha256,
                acknowledge_observer_no_proof,
            )
        except Exception:  # noqa: BLE001 - never send without durable intent
            return self._close("SESSION_CLOSED_INTENT_FAILED")
        self.history.append(f"ACTION_{ordinal}_INTENT_{action.value}")
        self.actions_used = ordinal

        try:
            result = self.effects.invoke_action(
                self.contract.binding,
                ordinal,
                action,
                self.active_observer_sha256,
            )
            result.validate()
            if result.postflight is not None:
                _validate_attended_preflight(result.postflight)
        except Exception:  # noqa: BLE001 - action result is control-ambiguous
            self.action_results.append(
                {
                    "ordinal": ordinal,
                    "action": action.value,
                    "status": SessionActionStatus.CONTROL_AMBIGUOUS.value,
                    "failure_class": "ACTION_RESULT_AMBIGUOUS",
                }
            )
            return self._close("RECOVERY_REQUIRED")

        self.action_results.append(
            {
                "ordinal": ordinal,
                "action": action.value,
                "status": result.status.value,
                "failure_class": result.failure_class,
            }
        )
        self.history.append(f"ACTION_{ordinal}_{result.status.value}")
        if result.status is SessionActionStatus.WINDOW_EXPIRED_NO_EFFECT:
            return self._close("SESSION_CLOSED_EXPIRED_BEFORE_DISPATCH")
        if result.status in {
            SessionActionStatus.DEVICE_SAFETY_FAILURE,
            SessionActionStatus.CONTROL_AMBIGUOUS,
        }:
            self.device_safety_state = "RECOVERY_REQUIRED"
            return self._close("RECOVERY_REQUIRED")
        if result.status is SessionActionStatus.EXPERIMENT_BLOCKED:
            return self._close("SESSION_CLOSED_EXPERIMENT_BLOCKED")
        if result.status is SessionActionStatus.REFUTED:
            key = (action.value, str(result.failure_class))
            self.refutation_counts[key] = self.refutation_counts.get(key, 0) + 1
            if self.refutation_counts[key] >= 2:
                return self._close("SESSION_CLOSED_REPEATED_REFUTATION")
        if self.actions_used >= self.contract.binding.max_actions:
            return self._close("SESSION_CLOSED_BUDGET_EXHAUSTED")
        if result.status is SessionActionStatus.NO_PROOF_OBSERVER:
            if self.observer_no_proof_acknowledgements >= 1:
                return self._close("SESSION_CLOSED_REPEATED_OBSERVER_NO_PROOF")
            self.observer_repair_required = True
            self.history.append("SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED")
            return self._snapshot("SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED")
        return self._snapshot("SESSION_ACTIVE")

    def close_by_operator(self) -> dict[str, Any]:
        if self.closed_terminal is not None:
            raise ContractError("attended session is already closed")
        return self._close("SESSION_CLOSED_OPERATOR_STOP")

    def resume_after_observer_repair(
        self,
        repair: ObserverRepair,
        *,
        now_epoch_sec: int,
        preflight: SessionPreflight,
    ) -> dict[str, Any]:
        if self.closed_terminal is not None:
            raise ContractError("attended session is already closed")
        if not self.observer_repair_required:
            raise ContractError("attended session is not waiting for observer repair")
        if (
            type(now_epoch_sec) is not int
            or now_epoch_sec < self.last_now_epoch_sec
        ):
            raise ContractError("session time is not monotonic")
        self.last_now_epoch_sec = now_epoch_sec
        if now_epoch_sec >= self.contract.binding.expires_at_epoch_sec:
            return self._close("SESSION_CLOSED_EXPIRED")
        if not isinstance(repair, ObserverRepair):
            raise ContractError("observer repair type is not exact")
        repair.validate()
        if repair.previous_sha256 != self.active_observer_sha256:
            raise ContractError("observer repair predecessor does not match")
        _validate_attended_preflight(preflight)
        try:
            self.effects.record_observer_repair(self.contract.binding, repair)
        except Exception:  # noqa: BLE001 - no action follows an unrecorded repair
            return self._close("SESSION_CLOSED_OBSERVER_REPAIR_RECORD_FAILED")
        self.active_observer_sha256 = repair.repaired_sha256
        self.observer_repair_required = False
        self.history.append("OBSERVER_REPAIR_VALIDATED")
        return self._snapshot("SESSION_ACTIVE")


def open_attended_session(
    contract: AttendedSessionContract,
    effects: SessionEffects,
    *,
    now_epoch_sec: int,
    preflight: SessionPreflight,
) -> AttendedSession:
    contract.validate()
    if type(now_epoch_sec) is not int or not (
        contract.binding.not_before_epoch_sec
        <= now_epoch_sec
        < contract.binding.expires_at_epoch_sec
    ):
        raise ContractError("session approval window is not active")
    _validate_attended_preflight(preflight)
    try:
        consumed = effects.consume_session_approval_once(contract.binding)
    except Exception as exc:  # noqa: BLE001 - no action before durable consume
        raise ContractError("session approval consumption is unavailable") from exc
    if consumed is not True:
        raise ContractError("session approval was already consumed or not durable")
    prior_refutations: dict[tuple[str, str], int] = {}
    for item in contract.previous_refutations:
        key = (item.action.value, item.failure_class)
        prior_refutations[key] = prior_refutations.get(key, 0) + 1
    return AttendedSession(
        contract=contract,
        effects=effects,
        opened_at_epoch_sec=now_epoch_sec,
        last_now_epoch_sec=now_epoch_sec,
        refutation_counts=prior_refutations,
        active_observer_sha256=contract.binding.observer_sha256,
    )


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


@dataclass
class ScriptedSessionEffects:
    """Deterministic H0 session port; it has no device or persistence backend."""

    outcomes: tuple[SessionActionResult, ...]
    mode: str = "SIMULATED_SESSION_H0"
    events: list[str] = field(default_factory=list)
    consumed_approval_ids: set[str] = field(default_factory=set)
    invoke_count: int = 0

    def consume_session_approval_once(
        self,
        binding: AttendedSessionBinding,
    ) -> bool:
        self.events.append(f"SESSION_APPROVAL_CONSUME:{binding.approval_id}")
        if binding.approval_id in self.consumed_approval_ids:
            return False
        self.consumed_approval_ids.add(binding.approval_id)
        return True

    def record_action_intent(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
        observer_no_proof_acknowledged: bool,
    ) -> None:
        self.events.append(
            f"SESSION_INTENT:{binding.workflow.value}:{ordinal}:{action.value}:"
            f"{observer_sha256}:{int(observer_no_proof_acknowledged)}"
        )

    def invoke_action(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
    ) -> SessionActionResult:
        self.events.append(
            f"SESSION_EFFECT:{binding.workflow.value}:{ordinal}:{action.value}:"
            f"{observer_sha256}"
        )
        index = self.invoke_count
        self.invoke_count += 1
        if index >= len(self.outcomes):
            raise ContractError("scripted session outcome is unavailable")
        return self.outcomes[index]

    def record_observer_repair(
        self,
        binding: AttendedSessionBinding,
        repair: ObserverRepair,
    ) -> None:
        self.events.append(
            "SESSION_OBSERVER_REPAIR:"
            f"{binding.workflow.value}:{repair.previous_sha256}:"
            f"{repair.repaired_sha256}"
        )
