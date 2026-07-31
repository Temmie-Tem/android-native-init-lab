#!/usr/bin/env python3
"""Pure H0 state model for the A90 resident boot-promotion contract."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


SCHEMA = "a90-resident-boot-promotion-v1-model"


class ContractError(RuntimeError):
    """Raised when a transition would weaken the promotion contract."""


class State(str, Enum):
    PREFLIGHT = "PREFLIGHT"
    APPROVED = "APPROVED"
    ROOTFS_STAGE_INTENT = "ROOTFS_STAGE_INTENT"
    ROOTFS_STAGED = "ROOTFS_STAGED"
    ROOTFS_EXISTING_VERIFIED = "ROOTFS_EXISTING_VERIFIED"
    ROOTFS_READY = "ROOTFS_READY"
    CANDIDATE_INTENT = "CANDIDATE_INTENT"
    CANDIDATE_ATTEMPT_STARTED = "CANDIDATE_ATTEMPT_STARTED"
    CANDIDATE_FLASHED = "CANDIDATE_FLASHED"
    CANDIDATE_HEALTH_VERIFIED = "CANDIDATE_HEALTH_VERIFIED"
    RESIDENT_REBOOT_INTENT = "RESIDENT_REBOOT_INTENT"
    RESIDENT_REBOOTED = "RESIDENT_REBOOTED"
    RESIDENT_HEALTH_VERIFIED = "RESIDENT_HEALTH_VERIFIED"
    PROMOTED_CLOSED = "PROMOTED_CLOSED"
    ROLLBACK_INTENT = "ROLLBACK_INTENT"
    ROLLBACK_FLASHED = "ROLLBACK_FLASHED"
    ROLLBACK_HEALTH_VERIFIED = "ROLLBACK_HEALTH_VERIFIED"
    ROLLED_BACK_CLOSED = "ROLLED_BACK_CLOSED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    BLOCKED = "BLOCKED"
    ABORTED = "ABORTED"


ALLOWED: dict[State, frozenset[State]] = {
    State.PREFLIGHT: frozenset({State.APPROVED, State.ABORTED}),
    State.APPROVED: frozenset(
        {State.ROOTFS_STAGE_INTENT, State.ROOTFS_EXISTING_VERIFIED, State.ABORTED}
    ),
    State.ROOTFS_STAGE_INTENT: frozenset(
        {State.ROOTFS_STAGED, State.BLOCKED, State.ABORTED}
    ),
    State.ROOTFS_STAGED: frozenset({State.ROOTFS_READY}),
    State.ROOTFS_EXISTING_VERIFIED: frozenset({State.ROOTFS_READY}),
    State.ROOTFS_READY: frozenset({State.CANDIDATE_INTENT, State.ABORTED}),
    State.CANDIDATE_INTENT: frozenset(
        {State.CANDIDATE_ATTEMPT_STARTED, State.ABORTED}
    ),
    State.CANDIDATE_ATTEMPT_STARTED: frozenset(
        {State.CANDIDATE_FLASHED, State.ROLLBACK_INTENT}
    ),
    State.CANDIDATE_FLASHED: frozenset(
        {State.CANDIDATE_HEALTH_VERIFIED, State.ROLLBACK_INTENT}
    ),
    State.CANDIDATE_HEALTH_VERIFIED: frozenset(
        {State.RESIDENT_REBOOT_INTENT, State.ROLLBACK_INTENT}
    ),
    State.RESIDENT_REBOOT_INTENT: frozenset(
        {State.RESIDENT_REBOOTED, State.ROLLBACK_INTENT}
    ),
    State.RESIDENT_REBOOTED: frozenset(
        {State.RESIDENT_HEALTH_VERIFIED, State.ROLLBACK_INTENT}
    ),
    State.RESIDENT_HEALTH_VERIFIED: frozenset(
        {State.PROMOTED_CLOSED, State.ROLLBACK_INTENT}
    ),
    State.ROLLBACK_INTENT: frozenset(
        {State.ROLLBACK_FLASHED, State.RECOVERY_REQUIRED}
    ),
    State.ROLLBACK_FLASHED: frozenset(
        {State.ROLLBACK_HEALTH_VERIFIED, State.RECOVERY_REQUIRED}
    ),
    State.ROLLBACK_HEALTH_VERIFIED: frozenset({State.ROLLED_BACK_CLOSED}),
    State.PROMOTED_CLOSED: frozenset(),
    State.ROLLED_BACK_CLOSED: frozenset(),
    State.RECOVERY_REQUIRED: frozenset(),
    State.BLOCKED: frozenset(),
    State.ABORTED: frozenset(),
}


POST_ATTEMPT_STATES = frozenset(
    {
        State.CANDIDATE_ATTEMPT_STARTED,
        State.CANDIDATE_FLASHED,
        State.CANDIDATE_HEALTH_VERIFIED,
        State.RESIDENT_REBOOT_INTENT,
        State.RESIDENT_REBOOTED,
        State.RESIDENT_HEALTH_VERIFIED,
    }
)


@dataclass
class PromotionModel:
    state: State = State.PREFLIGHT
    history: list[str] = field(default_factory=lambda: [State.PREFLIGHT.value])
    rootfs_preflight_state: str | None = None
    rootfs_staged: bool = False
    rootfs_existing_verified: bool = False
    rootfs_ready: bool = False
    rootfs_safe_closure: bool = False
    rootfs_final_state: str | None = None
    rootfs_stage_attempts: int = 0
    abort_reason: str | None = None
    candidate_usb_generation: str | None = None
    resident_usb_generation: str | None = None
    candidate_attempts: int = 0
    candidate_flashes: int = 0
    candidate_health_checks: int = 0
    resident_reboots: int = 0
    rollback_attempts: int = 0
    rollback_flashes: int = 0
    rollback_health_checks: int = 0

    def move(self, target: State) -> None:
        if target not in ALLOWED[self.state]:
            raise ContractError(
                f"invalid promotion transition {self.state.value}->{target.value}"
            )
        self.state = target
        self.history.append(target.value)

    def approve(self) -> None:
        if self.rootfs_preflight_state not in {"absent", "exact"}:
            raise ContractError("approval requires absent-or-exact rootfs preflight")
        self.move(State.APPROVED)

    def classify_rootfs(self, state: str) -> None:
        if self.state is not State.PREFLIGHT or state not in {"absent", "exact"}:
            raise ContractError("rootfs preflight state must be absent or exact")
        self.rootfs_preflight_state = state

    def rootfs_stage_intent(self) -> None:
        if self.rootfs_preflight_state != "absent":
            raise ContractError("absent-only staging requires absent preflight")
        self.move(State.ROOTFS_STAGE_INTENT)
        self.rootfs_stage_attempts += 1

    def complete_rootfs_stage(self) -> None:
        self.move(State.ROOTFS_STAGED)
        self.rootfs_staged = True
        self.rootfs_safe_closure = True
        self.rootfs_final_state = "exact"

    def mark_rootfs_ready(self) -> None:
        self.move(State.ROOTFS_READY)
        self.rootfs_ready = True

    def verify_existing_rootfs(self) -> None:
        if self.rootfs_preflight_state != "exact":
            raise ContractError("existing rootfs reuse requires exact preflight")
        self.move(State.ROOTFS_EXISTING_VERIFIED)
        self.rootfs_existing_verified = True
        self.rootfs_safe_closure = True
        self.rootfs_final_state = "exact"
        self.mark_rootfs_ready()

    def prove_rootfs_safe_closure(self, final_state: str) -> None:
        if self.state is not State.ROOTFS_STAGE_INTENT:
            raise ContractError("rootfs safe closure requires staging intent")
        if final_state not in {"absent", "exact"}:
            raise ContractError("rootfs safe closure must be absent or exact")
        self.rootfs_safe_closure = True
        self.rootfs_final_state = final_state

    def candidate_intent(self) -> None:
        self.move(State.CANDIDATE_INTENT)

    def candidate_attempt_started(self) -> None:
        self.move(State.CANDIDATE_ATTEMPT_STARTED)
        self.candidate_attempts += 1

    def candidate_flashed(self) -> None:
        self.move(State.CANDIDATE_FLASHED)
        self.candidate_flashes += 1

    def candidate_health_verified(self, usb_generation: str) -> None:
        if not usb_generation:
            raise ContractError("candidate USB generation is required")
        self.move(State.CANDIDATE_HEALTH_VERIFIED)
        self.candidate_health_checks += 1
        self.candidate_usb_generation = usb_generation

    def resident_reboot_intent(self) -> None:
        self.move(State.RESIDENT_REBOOT_INTENT)

    def resident_rebooted(self) -> None:
        self.move(State.RESIDENT_REBOOTED)
        self.resident_reboots += 1

    def resident_health_verified(self, usb_generation: str) -> None:
        if not usb_generation:
            raise ContractError("resident USB generation is required")
        if usb_generation == self.candidate_usb_generation:
            raise ContractError("resident USB generation must differ from candidate")
        self.move(State.RESIDENT_HEALTH_VERIFIED)
        self.candidate_health_checks += 1
        self.resident_usb_generation = usb_generation

    def close_promoted(self) -> None:
        self.move(State.PROMOTED_CLOSED)
        self.validate_terminal()

    def abort_before_attempt(self, reason: str) -> None:
        allowed_reasons = {
            State.PREFLIGHT: "preflight-rejection",
            State.APPROVED: "preflight-rejection",
            State.ROOTFS_STAGE_INTENT: "rootfs-safe-failure",
            State.ROOTFS_READY: "rootfs-ready-pre-candidate-rejection",
            State.CANDIDATE_INTENT: "candidate-local-parse-proven-no-session",
        }
        if allowed_reasons.get(self.state) != reason:
            raise ContractError("abort reason is not exact for the current state")
        if self.state is State.ROOTFS_STAGE_INTENT and not self.rootfs_safe_closure:
            raise ContractError("staging abort requires exact-or-absent safe closure")
        self.abort_reason = reason
        self.move(State.ABORTED)
        self.validate_terminal()

    def rollback(self, *, flash_ok: bool = True, health_ok: bool = True) -> None:
        if self.state not in POST_ATTEMPT_STATES:
            raise ContractError("rollback requires a started candidate attempt")
        self.move(State.ROLLBACK_INTENT)
        self.rollback_attempts += 1
        if not flash_ok:
            self.move(State.RECOVERY_REQUIRED)
            self.validate_terminal()
            return
        self.move(State.ROLLBACK_FLASHED)
        self.rollback_flashes += 1
        if not health_ok:
            self.move(State.RECOVERY_REQUIRED)
            self.validate_terminal()
            return
        self.move(State.ROLLBACK_HEALTH_VERIFIED)
        self.rollback_health_checks += 1
        self.move(State.ROLLED_BACK_CLOSED)
        self.validate_terminal()

    def validate_terminal(self) -> None:
        if self.state is State.PROMOTED_CLOSED:
            exact = (
                self.rootfs_ready
                and self.rootfs_safe_closure
                and self.rootfs_final_state == "exact"
                and self.rootfs_stage_attempts in {0, 1}
                and (
                    (self.rootfs_stage_attempts == 1 and self.rootfs_staged)
                    or (
                        self.rootfs_stage_attempts == 0
                        and self.rootfs_existing_verified
                    )
                )
                and self.candidate_attempts == 1
                and self.candidate_flashes == 1
                and self.candidate_health_checks == 2
                and self.resident_reboots == 1
                and bool(self.candidate_usb_generation)
                and bool(self.resident_usb_generation)
                and self.candidate_usb_generation != self.resident_usb_generation
                and self.rollback_attempts == 0
                and self.rollback_flashes == 0
            )
            if not exact:
                raise ContractError("promoted close lacks the exact success closure")
            return
        if self.state is State.ROLLED_BACK_CLOSED:
            exact = (
                self.candidate_attempts == 1
                and self.rollback_attempts == 1
                and self.rollback_flashes == 1
                and self.rollback_health_checks == 1
            )
            if not exact:
                raise ContractError("rolled-back close lacks exact recovery health")
            return
        if self.state is State.ABORTED:
            if self.candidate_attempts != 0 or self.rollback_attempts != 0:
                raise ContractError("abort is allowed only before candidate attempt")
            return
        if self.state is State.RECOVERY_REQUIRED:
            if self.candidate_attempts != 1 or self.rollback_attempts != 1:
                raise ContractError("recovery-required counts are not exact")
            return
        if self.state is State.BLOCKED:
            if self.candidate_attempts != 0 or self.rollback_attempts != 0:
                raise ContractError("blocked staging state cannot start a candidate")
            return
        raise ContractError(f"state is not terminal: {self.state.value}")

    def result(self, scenario: str) -> dict[str, Any]:
        self.validate_terminal()
        return {
            "schema": SCHEMA,
            "scenario": scenario,
            "host_only": True,
            "device_action": False,
            "flash": False,
            "live_authority": False,
            "terminal_state": self.state.value,
            "history": self.history,
            "rootfs_safe_closure": self.rootfs_safe_closure,
            "rootfs_preflight_state": self.rootfs_preflight_state,
            "rootfs_final_state": self.rootfs_final_state,
            "rootfs_source_mode": (
                "staged-new"
                if self.rootfs_staged
                else "verified-existing" if self.rootfs_existing_verified else None
            ),
            "abort_reason": self.abort_reason,
            "usb_generations_distinct": bool(
                self.candidate_usb_generation
                and self.resident_usb_generation
                and self.candidate_usb_generation != self.resident_usb_generation
            ),
            "counts": {
                "rootfs_stage_attempts": self.rootfs_stage_attempts,
                "candidate_attempts": self.candidate_attempts,
                "candidate_flashes": self.candidate_flashes,
                "candidate_health_checks": self.candidate_health_checks,
                "resident_reboots": self.resident_reboots,
                "rollback_attempts": self.rollback_attempts,
                "rollback_flashes": self.rollback_flashes,
                "rollback_health_checks": self.rollback_health_checks,
            },
        }


def simulate(scenario: str) -> dict[str, Any]:
    model = PromotionModel()
    if scenario == "preflight-failure":
        model.abort_before_attempt("preflight-rejection")
        return model.result(scenario)
    if scenario == "existing-rootfs-success":
        model.classify_rootfs("exact")
        model.approve()
        model.verify_existing_rootfs()
    else:
        model.classify_rootfs("absent")
        model.approve()
    if scenario == "rootfs-stage-failure":
        model.rootfs_stage_intent()
        model.prove_rootfs_safe_closure("absent")
        model.abort_before_attempt("rootfs-safe-failure")
        return model.result(scenario)
    if scenario == "rootfs-stage-failure-exact":
        model.rootfs_stage_intent()
        model.prove_rootfs_safe_closure("exact")
        model.abort_before_attempt("rootfs-safe-failure")
        return model.result(scenario)
    if scenario == "rootfs-stage-ambiguous":
        model.rootfs_stage_intent()
        model.move(State.BLOCKED)
        return model.result(scenario)
    if scenario != "existing-rootfs-success":
        model.rootfs_stage_intent()
        model.complete_rootfs_stage()
        model.mark_rootfs_ready()
    if scenario == "post-stage-pre-candidate-rejection":
        model.abort_before_attempt("rootfs-ready-pre-candidate-rejection")
        return model.result(scenario)
    model.candidate_intent()
    if scenario == "candidate-local-parse-failure":
        model.abort_before_attempt("candidate-local-parse-proven-no-session")
        return model.result(scenario)
    model.candidate_attempt_started()
    if scenario == "candidate-transfer-ambiguous":
        model.rollback()
        return model.result(scenario)
    model.candidate_flashed()
    if scenario == "candidate-health-failure":
        model.rollback()
        return model.result(scenario)
    model.candidate_health_verified("candidate-usb-generation")
    model.resident_reboot_intent()
    if scenario == "resident-reboot-ambiguous":
        model.rollback()
        return model.result(scenario)
    model.resident_rebooted()
    if scenario == "resident-health-failure":
        model.rollback()
        return model.result(scenario)
    if scenario == "rollback-failure":
        model.rollback(flash_ok=False)
        return model.result(scenario)
    model.resident_health_verified("resident-usb-generation")
    model.close_promoted()
    return model.result(scenario)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=(
            "success",
            "existing-rootfs-success",
            "preflight-failure",
            "rootfs-stage-failure",
            "rootfs-stage-failure-exact",
            "rootfs-stage-ambiguous",
            "post-stage-pre-candidate-rejection",
            "candidate-local-parse-failure",
            "candidate-transfer-ambiguous",
            "candidate-health-failure",
            "resident-reboot-ambiguous",
            "resident-health-failure",
            "rollback-failure",
        ),
        default="success",
    )
    args = parser.parse_args()
    print(json.dumps(simulate(args.scenario), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
