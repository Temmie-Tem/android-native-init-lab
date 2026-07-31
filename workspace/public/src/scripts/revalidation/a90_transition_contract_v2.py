#!/usr/bin/env python3
"""Pure contracts for the reduced A90 resident and switch-root workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


CONTRACT_SCHEMA = "a90-transition-contract-v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$")


class ContractError(RuntimeError):
    """Raised before an effect when a transition contract is not exact."""


class RiskTier(str, Enum):
    H0_HOST_ONLY = "H0_HOST_ONLY"
    TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL = (
        "TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL"
    )
    F1_BOOT_ONLY_WITH_EXACT_ROLLBACK = "F1_BOOT_ONLY_WITH_EXACT_ROLLBACK"


class Workflow(str, Enum):
    RESIDENT_INSTALL_F1 = "RESIDENT_INSTALL_F1"
    SWITCHROOT_EXPERIMENT_D1 = "SWITCHROOT_EXPERIMENT_D1"


class LegacyStage(str, Enum):
    STAGE_D1_CHROOT_MVP = "STAGE_D1_CHROOT_MVP"


class ProofState(str, Enum):
    PROVEN = "PROVEN"
    REFUTED = "REFUTED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class FailureSignature:
    workflow: str
    phase: str
    failure_class: str
    effect_started: bool
    last_proven_boundary: str

    def __post_init__(self) -> None:
        names = (
            self.workflow,
            self.phase,
            self.failure_class,
            self.last_proven_boundary,
        )
        if any(
            not isinstance(name, str) or IDENTITY_RE.fullmatch(name) is None
            for name in names
        ):
            raise ContractError("failure signature identity is not exact")
        if type(self.effect_started) is not bool:
            raise ContractError("failure signature effect_started is not boolean")

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "workflow": self.workflow,
            "phase": self.phase,
            "failure_class": self.failure_class,
            "effect_started": self.effect_started,
            "last_proven_boundary": self.last_proven_boundary,
        }


@dataclass(frozen=True)
class ApprovalBinding:
    approval_id: str
    workflow: Workflow
    risk_tier: RiskTier
    target_profile: str
    manifest_sha256: str

    def validate(self) -> None:
        if not isinstance(self.workflow, Workflow) or not isinstance(
            self.risk_tier,
            RiskTier,
        ):
            raise ContractError("approval workflow or tier is not an exact enum")
        if not isinstance(self.approval_id, str) or (
            IDENTITY_RE.fullmatch(self.approval_id) is None
        ):
            raise ContractError("approval identity is not exact")
        if not isinstance(self.target_profile, str) or (
            IDENTITY_RE.fullmatch(self.target_profile) is None
        ):
            raise ContractError("target profile identity is not exact")
        if not isinstance(self.manifest_sha256, str) or (
            SHA256_RE.fullmatch(self.manifest_sha256) is None
        ):
            raise ContractError("approval manifest SHA256 is not exact")
        expected = {
            Workflow.RESIDENT_INSTALL_F1: (
                RiskTier.F1_BOOT_ONLY_WITH_EXACT_ROLLBACK
            ),
            Workflow.SWITCHROOT_EXPERIMENT_D1: (
                RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL
            ),
        }[self.workflow]
        if self.risk_tier is not expected:
            raise ContractError("workflow and risk tier are not namespaced exactly")


@dataclass(frozen=True)
class SuccessorContract:
    domain: str
    predecessor_owner: str
    predecessor_release_proof: str
    successor_owner: str
    successor_acquisition_proofs: tuple[str, ...]
    visibility_proof: str | None = None
    no_successor_by_design: bool = False

    def validate(self) -> None:
        identities = (
            self.domain,
            self.predecessor_owner,
            self.predecessor_release_proof,
            self.successor_owner,
            *self.successor_acquisition_proofs,
        )
        if any(
            not isinstance(value, str) or IDENTITY_RE.fullmatch(value) is None
            for value in identities
        ):
            raise ContractError("successor contract identity is not exact")
        if self.visibility_proof is not None and (
            IDENTITY_RE.fullmatch(self.visibility_proof) is None
        ):
            raise ContractError("visibility proof identity is not exact")
        if self.no_successor_by_design:
            if self.successor_owner != "none" or self.successor_acquisition_proofs:
                raise ContractError("by-design no-successor contract is inconsistent")
        elif (
            self.successor_owner == "none"
            or not self.predecessor_release_proof
            or not self.successor_acquisition_proofs
        ):
            raise ContractError("domain lacks release and successor acquisition")


DISPLAY_SUCCESSOR = SuccessorContract(
    domain="display",
    predecessor_owner="native_init",
    predecessor_release_proof="native_release",
    successor_owner="debian_presenter",
    successor_acquisition_proofs=(
        "drm_master_acquired",
        "connector_connected",
        "modeset_committed",
        "backlight_enabled",
        "dpms_on",
    ),
    visibility_proof="visible_confirmed",
)


def validate_successor_contracts(
    contracts: Iterable[SuccessorContract],
) -> tuple[SuccessorContract, ...]:
    selected = tuple(contracts)
    if not selected:
        raise ContractError("at least one handoff domain is required")
    domains: set[str] = set()
    for item in selected:
        item.validate()
        if item.domain in domains:
            raise ContractError("successor domain is duplicated")
        domains.add(item.domain)
    return selected


@dataclass(frozen=True)
class DisplayProof:
    native_release: ProofState
    debian_pid1: ProofState
    dropbear: ProofState
    drm_master_acquired: ProofState
    connector_connected: ProofState
    modeset_committed: ProofState
    backlight_enabled: ProofState
    dpms_on: ProofState
    visible_confirmed: ProofState
    visibility_source: str | None = None

    def mechanical_items(self) -> tuple[tuple[str, ProofState], ...]:
        return (
            ("native_release", self.native_release),
            ("debian_pid1", self.debian_pid1),
            ("dropbear", self.dropbear),
            ("drm_master_acquired", self.drm_master_acquired),
            ("connector_connected", self.connector_connected),
            ("modeset_committed", self.modeset_committed),
            ("backlight_enabled", self.backlight_enabled),
            ("dpms_on", self.dpms_on),
        )

    def validate(self) -> None:
        states = tuple(value for _, value in self.mechanical_items()) + (
            self.visible_confirmed,
        )
        if any(not isinstance(value, ProofState) for value in states):
            raise ContractError("display proof state is not an exact enum")
        if self.visible_confirmed is ProofState.PROVEN:
            if self.visibility_source not in {"operator", "camera"}:
                raise ContractError("visible proof requires operator or camera source")
        elif self.visibility_source is not None:
            raise ContractError("visibility source is present without visible proof")

    def first_nonproven(self) -> tuple[str, ProofState] | None:
        self.validate()
        for item in self.mechanical_items():
            if item[1] is not ProofState.PROVEN:
                return item
        return None


def repeated_failure_gate(
    previous: Iterable[FailureSignature],
) -> str:
    signatures = tuple(previous)
    if any(not isinstance(item, FailureSignature) for item in signatures):
        raise ContractError("previous failure signature is not exact")
    if signatures and signatures[-1].failure_class.endswith("_AMBIGUOUS"):
        return "STOP_AMBIGUOUS_FAILURE_SIGNATURE"
    if len(signatures) >= 2 and signatures[-1] == signatures[-2]:
        return "STOP_REPEATED_FAILURE_SIGNATURE"
    return "ALLOW_FRESH_PREPARATION"
