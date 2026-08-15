#!/usr/bin/env python3
"""Generate the host-only WP-H0-2 one-factor WLAN ablation design.

The design consumes only the canonical WP-H0-1 public inventory.  It defines
future experiment semantics but performs no device, transport, private-input,
candidate, approval, or installation action.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
PARENT_REL = (
    "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
)
PARENT_BYTES = 42264
PARENT_SHA256 = "d4ac9b47de9674995b891e888937969cb34b74d27b1c59e35cb7172fbd3370cb"
PARENT_SCHEMA = "a90-h24-wlan-capsule-dependency-inventory-v1"
DEFAULT_OUTPUT = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    / "design/a90-h24-wlan-one-factor-ablation-design-v1.json"
)

EXPECTED_ROLES = {
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
    "pm_proxy_helper",
    "per_mgr",
    "qrtr_ns",
    "pd_mapper",
    "rmt_storage",
    "tftp_server",
    "cnss_diag",
    "cnss_daemon",
    "property-service-shim",
    "modem-holder",
    "wifi-helper",
}
REMOVABLE_ROLES = EXPECTED_ROLES - {"wifi-helper"}
GLOBAL_BASELINE_GATE_IDS = {"H0D01", "H0D02", "H0D03", "H0D07", "H0D10"}

ROLE_DESIGN = {
    "cnss_diag": {
        "stage": "A4",
        "order": 1,
        "hypothesis": "Diagnostic candidate; no current evidence proves it participates in WCNSS/WMI readiness.",
        "gates": ["H0D02", "H0D03", "H0D07", "H0D09"],
        "positive": "Healthy firmware, Root PD, WMI, station policy, and cleanup with the role absent.",
    },
    "servicemanager": {
        "stage": "A5a",
        "order": 2,
        "hypothesis": "Compatibility context-manager route; hardware necessity is unproved.",
        "gates": ["H0D02", "H0D03", "H0D05"],
        "positive": "All retained Binder transactions and hardware terminals pass without this manager.",
    },
    "hwservicemanager": {
        "stage": "A5b",
        "order": 3,
        "hypothesis": "Compatibility context-manager route; hardware necessity is unproved.",
        "gates": ["H0D02", "H0D03", "H0D05"],
        "positive": "All retained hwBinder transactions and hardware terminals pass without this manager.",
    },
    "vndservicemanager": {
        "stage": "A6a",
        "order": 4,
        "hypothesis": "Vendor compatibility registry; current selected-source reachability is not individual necessity.",
        "gates": ["H0D02", "H0D03", "H0D05"],
        "positive": "All retained vendor Binder transactions and hardware terminals pass without this manager.",
    },
    "pm_proxy_helper": {
        "stage": "A6b",
        "order": 5,
        "hypothesis": "Provider visibility helper; a direct readiness signal may replace it, but that is unproved.",
        "gates": ["H0D02", "H0D03", "H0D05", "H0D09"],
        "positive": "Provider/readiness semantics and all hardware terminals pass without this helper.",
    },
    "per_mgr": {
        "stage": "A6c",
        "order": 6,
        "hypothesis": "Peripheral-manager compatibility role; exact producer-consumer edges are unproved.",
        "gates": ["H0D02", "H0D03", "H0D05", "H0D07", "H0D09"],
        "positive": "Provider/readiness semantics and all hardware terminals pass without per_mgr.",
    },
    "qrtr_ns": {
        "stage": "A7a",
        "order": 7,
        "hypothesis": "Plausible QRTR name-service dependency; the exact selected-route necessity is unproved.",
        "gates": ["H0D02", "H0D03", "H0D06", "H0D07"],
        "positive": "Bound QRTR services, Root PD, WMI, and cleanup pass without qrtr_ns.",
    },
    "pd_mapper": {
        "stage": "A7b",
        "order": 8,
        "hypothesis": "Plausible protection-domain mapping dependency; individual necessity is unproved.",
        "gates": ["H0D02", "H0D03", "H0D06", "H0D07"],
        "positive": "Bound PD service and WMI terminals pass without pd_mapper.",
    },
    "rmt_storage": {
        "stage": "A7c",
        "order": 9,
        "hypothesis": "Plausible RFS/QMI storage role; it is not renamed to rmtfs and its H24 identity remains conflicted.",
        "gates": ["H0D02", "H0D03", "H0D06", "H0D07", "H0D08", "H0D09"],
        "positive": "All observed RFS/QMI requests and hardware terminals pass without rmt_storage.",
    },
    "tftp_server": {
        "stage": "A7d",
        "order": 10,
        "hypothesis": "Plausible firmware/RFS object server; exact served-object necessity is unproved.",
        "gates": ["H0D02", "H0D03", "H0D07", "H0D08", "H0D09"],
        "positive": "Every bound firmware/RFS request and hardware terminal passes without tftp_server.",
    },
    "cnss_daemon": {
        "stage": "A8",
        "order": 11,
        "hypothesis": "Strongest WCNSS/WLFW control-plane candidate, but historical QMI flow is not current H24 necessity proof.",
        "gates": ["H0D01", "H0D02", "H0D03", "H0D04", "H0D06", "H0D07", "H0D09"],
        "positive": "Firmware, Root PD, WMI, station policy, and cold relaunch pass without cnss_daemon.",
    },
    "modem-holder": {
        "stage": "A9",
        "order": 12,
        "hypothesis": "Current /dev/subsys_modem lifetime coupling is source-visible; minimum hardware necessity is unproved.",
        "gates": ["H0D07", "H0D09"],
        "positive": "Root PD, WMI, lifetime accounting, and cleanup pass with no holder or holder FD.",
    },
    "property-service-shim": {
        "stage": "A10",
        "order": 13,
        "hypothesis": "Write-ack compatibility shim; it does not prove the property-area read set or required write semantics.",
        "gates": ["H0D04", "H0D07", "H0D09"],
        "positive": "The full lifecycle has zero required writes/ACKs and passes all hardware and cleanup terminals.",
    },
    "wifi-helper": {
        "stage": None,
        "order": 99,
        "hypothesis": "Topology owner and accumulated supervisor, not a component-removal variable in WP-H0-2.",
        "gates": ["H0D02", "H0D03", "H0D07", "H0D09"],
        "positive": "Replacement belongs to the later reduced-native or Debian-capsule integration, not this ablation program.",
    },
}


def _read_parent() -> tuple[bytes, dict[str, Any]]:
    path = ROOT / PARENT_REL
    if path.is_symlink() or not path.is_file():
        raise ValueError("WP-H0-2 parent must be a lexical regular file")
    raw = path.read_bytes()
    if len(raw) != PARENT_BYTES or hashlib.sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError("WP-H0-2 parent inventory drift")
    return raw, json.loads(raw)


def _validate_parent(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if data.get("schema") != PARENT_SCHEMA:
        raise ValueError("wrong WP-H0-1 parent schema")
    expected_status = {
        "wpH01PublicSourceInventory": "COMPLETE_FROZEN_H24_SELECTED_PATH_ONLY",
        "wpH01Overall": "PARTIAL_RUNTIME_CLOSURE_BLOCKED",
        "wpH01OpaqueRuntimeClosure": "BLOCKED_UNPROVED",
        "optionC": "H0_RESEARCH_ONLY_NOT_IMPLEMENTATION_ELIGIBLE",
    }
    for key, value in expected_status.items():
        if data.get("status", {}).get(key) != value:
            raise ValueError(f"parent inventory status drift: {key}")
    authority = data.get("authority", {})
    if authority.get("tier") != "H0" or any(
        value is not False for key, value in authority.items() if key != "tier"
    ):
        raise ValueError("parent inventory grants authority")
    counts = data.get("counts", {})
    if (
        counts.get("compositeInstances") != 13
        or counts.get("uniqueCompositeRoles") != 11
        or counts.get("sourceAccountedProcessesBeforeStationPolicy") != 16
    ):
        raise ValueError("parent 13/11/16 graph drift")
    components = data.get("components")
    if not isinstance(components, list) or len(components) != 16:
        raise ValueError("parent component inventory drift")
    by_role: dict[str, list[dict[str, Any]]] = {}
    for component in components:
        role = component.get("role")
        if not isinstance(role, str):
            raise ValueError("parent component role missing")
        by_role.setdefault(role, []).append(component)
    if set(by_role) != EXPECTED_ROLES or set(ROLE_DESIGN) != EXPECTED_ROLES:
        raise ValueError("parent role set drift")
    if sorted(item["instanceId"] for item in by_role["servicemanager"]) != [
        "servicemanager#1",
        "servicemanager#2",
    ]:
        raise ValueError("servicemanager duplicate identity drift")
    if sorted(item["instanceId"] for item in by_role["hwservicemanager"]) != [
        "hwservicemanager#1",
        "hwservicemanager#2",
    ]:
        raise ValueError("hwservicemanager duplicate identity drift")
    gates = data.get("dependencyGates", [])
    if [gate.get("gateId") for gate in gates] != [f"H0D{i:02d}" for i in range(1, 11)]:
        raise ValueError("parent dependency gate drift")
    if any(gate.get("status") != "UNPROVED" for gate in gates):
        raise ValueError("parent unexpectedly claims a retired dependency gate")
    h0d10 = gates[-1]
    if h0d10.get("preExecutionHalf", {}).get("requiredTerminal") != (
        "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED"
    ):
        raise ValueError("parent H0D10 bootstrap rule drift")
    return by_role


def _role_argument(role: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    spec = ROLE_DESIGN[role]
    return {
        "role": role,
        "sourceInstances": [item["instanceId"] for item in components],
        "sourceKinds": sorted({item["kind"] for item in components}),
        "sourceExecutables": sorted({item["executable"] for item in components}),
        "sourceAnchors": sorted(
            {anchor for item in components for anchor in item["sourceAnchors"]}
        ),
        "ablationStage": spec["stage"],
        "staticHypothesis": spec["hypothesis"],
        "dependencyGateIds": spec["gates"],
        "positiveEvidenceRequirement": spec["positive"],
        "currentConclusion": "INDIVIDUAL_NECESSITY_UNPROVED",
        "conclusionScope": "FROZEN_H24_SELECTED_SOURCE_GRAPH_ONLY",
    }


def _gate_projection(gate: dict[str, Any]) -> dict[str, Any]:
    requirement = gate["preExecutionRequirement"]
    if requirement == "RETIRE_RELEVANT_ROW_BEFORE_EXECUTION":
        pre_action = "RETIRE_COMPLETE_RETAINED_SET_CLOSURE_BEFORE_EXECUTION"
        execution_role = "NO_RUNTIME_RETIREMENT_CREDIT"
    elif requirement == "RETIRE_STATIC_HALF_FOR_RELEVANT_ROW_BEFORE_EXECUTION":
        pre_action = "RETIRE_STATIC_HALF_FOR_COMPLETE_RETAINED_SET_BEFORE_EXECUTION"
        execution_role = "EXECUTION_MAY_PRODUCE_ONLY_THE_RUNTIME_HALF"
    elif requirement == "BOUNDED_EXECUTION_PRODUCES_RETIREMENT_EVIDENCE_NOT_A_PRECONDITION":
        pre_action = "NO_RETIREMENT_PRECONDITION_OBSERVER_MUST_BE_BOUND"
        execution_role = "EXECUTION_PRODUCES_RETIREMENT_EVIDENCE"
    elif requirement == (
        "PROVE_SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_BEFORE_EXECUTION_THEN_"
        "FREEZE_RETAINED_SET_AFTER_ABLATION"
    ):
        pre_action = "PROVE_SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_BEFORE_EXECUTION"
        execution_role = "EXECUTION_MAY_PRODUCE_POST_ABLATION_MINIMIZATION_EVIDENCE"
    else:
        raise ValueError(f"unknown parent gate requirement: {requirement}")
    return {
        "gateId": gate["gateId"],
        "retirementClass": gate["retirementClass"],
        "parentPreExecutionRequirement": requirement,
        "preExecutionAction": pre_action,
        "executionEvidenceRole": execution_role,
        "status": gate["status"],
    }


def _proof_decision_table() -> list[dict[str, Any]]:
    rows = []
    for observer, evidence, attribution in itertools.product(
        ("VALID_COMPLETE", "INVALID_OR_UNRESOLVED"),
        (
            "ALL_REQUIRED_PASSED",
            "ATTRIBUTABLE_CONTRADICTION",
            "NOT_OBSERVED_OR_AMBIGUOUS",
        ),
        ("MATCHES_PROOF_SUBJECT", "DOES_NOT_MATCH_OR_UNRESOLVED"),
    ):
        if (
            evidence == "ATTRIBUTABLE_CONTRADICTION"
            and attribution == "MATCHES_PROOF_SUBJECT"
        ):
            proof = "REFUTED"
            reason = "DEVICE_CONTRADICTION_WINS_EVEN_WITH_OBSERVER_DEFECT"
        elif (
            observer == "VALID_COMPLETE"
            and evidence == "ALL_REQUIRED_PASSED"
            and attribution == "MATCHES_PROOF_SUBJECT"
        ):
            proof = "PROVED"
            reason = "COMPLETE_MATCHED_SUCCESS"
        else:
            proof = "NO_PROOF_OBSERVER"
            reason = "FAIL_CLOSED_UNRESOLVED_OR_OBSERVER_INVALID"
        rows.append(
            {
                "observerClass": observer,
                "experimentEvidenceClass": evidence,
                "attributionRelation": attribution,
                "experimentProof": proof,
                "decisionReason": reason,
            }
        )
    return rows


def _safety_decision_table() -> list[dict[str, Any]]:
    return [
        {
            "safetyClosureEvidence": "EXACT_BASELINE_HEALTHY",
            "deviceSafetyState": "BASELINE_HEALTHY",
            "workflowState": "TERMINAL",
        },
        {
            "safetyClosureEvidence": "EXACT_RESIDENT_HEALTHY_AFTER_RETURN_OR_RECOVERY",
            "deviceSafetyState": "RESIDENT_HEALTHY",
            "workflowState": "TERMINAL",
        },
        {
            "safetyClosureEvidence": "MISSING_AMBIGUOUS_OR_RECOVERY_REQUIRED",
            "deviceSafetyState": "RECOVERY_REQUIRED",
            "workflowState": "RECOVERY_PARKED",
        },
    ]


def _generation_decision_table() -> list[dict[str, Any]]:
    rows = []
    for subject, proof, safety in itertools.product(
        ("BASELINE", "ROLE_REMOVAL"),
        ("PROVED", "REFUTED", "NO_PROOF_OBSERVER"),
        ("BASELINE_HEALTHY", "RESIDENT_HEALTHY", "RECOVERY_REQUIRED"),
    ):
        if subject == "BASELINE":
            if proof == "REFUTED":
                outcome = "BASELINE_REJECTED"
            elif proof == "NO_PROOF_OBSERVER":
                outcome = "NO_PROOF_OBSERVER"
            elif safety == "RECOVERY_REQUIRED":
                outcome = "BASELINE_PROVED_RECOVERY_PARKED_NO_ADMISSION"
            elif safety == "BASELINE_HEALTHY":
                outcome = "BASELINE_PROVED_FINAL_HEALTH_PENDING_NO_ADMISSION"
            else:
                outcome = "BASELINE_ADMITTED_G0"
        elif proof == "REFUTED":
            outcome = "REMOVAL_REFUTED_FOR_GENERATION"
        elif proof == "NO_PROOF_OBSERVER":
            outcome = "NO_PROOF_OBSERVER"
        elif safety == "RESIDENT_HEALTHY":
            outcome = "REMOVAL_SUPPORTED_FOR_GENERATION"
        elif safety == "RECOVERY_REQUIRED":
            outcome = "REMOVAL_PROVED_RECOVERY_PARKED_NO_PROMOTION"
        else:
            outcome = "REMOVAL_PROVED_FINAL_HEALTH_PENDING_NO_PROMOTION"
        rows.append(
            {
                "proofSubject": subject,
                "experimentProof": proof,
                "deviceSafetyState": safety,
                "generationOutcome": outcome,
                "g0AdmissionEligible": outcome == "BASELINE_ADMITTED_G0",
                "promotionEligible": outcome == "REMOVAL_SUPPORTED_FOR_GENERATION",
            }
        )
    return rows


def _baseline_aggregate_decision_table() -> list[dict[str, Any]]:
    early_id = "B0_EARLY_PAIR"
    adjacent_id = "B0_PROVIDER_ADJACENT_PAIR"
    states = (
        "NOT_RUN",
        "BASELINE_ADMITTED_G0",
        "BASELINE_REJECTED",
        "BASELINE_NON_ADMITTING",
    )
    rows = []
    for early, adjacent in itertools.product(states, repeat=2):
        results = {early_id: early, adjacent_id: adjacent}
        present_ids = [
            variant_id
            for variant_id in (early_id, adjacent_id)
            if results[variant_id] != "NOT_RUN"
        ]
        attempt_orders = (
            [present_ids]
            if len(present_ids) < 2
            else [list(order) for order in itertools.permutations(present_ids)]
        )
        order_decisions = []
        for attempt_order in attempt_orders:
            g0_variant = None
            other_variant_candidate = False
            if not attempt_order:
                outcome = "BASELINE_VARIANTS_NOT_STARTED"
            elif len(attempt_order) == 2 and results[attempt_order[0]] != "BASELINE_REJECTED":
                first_state = results[attempt_order[0]]
                if first_state == "BASELINE_ADMITTED_G0":
                    outcome = "INVALID_EFFECT_AFTER_G0_ADMISSION_NO_SELECTION"
                else:
                    outcome = "INVALID_EFFECT_AFTER_NON_ADMITTING_RESULT_NO_SELECTION"
            else:
                final_id = attempt_order[-1]
                final_state = results[final_id]
                if final_state == "BASELINE_ADMITTED_G0":
                    g0_variant = final_id
                    outcome = (
                        "G0_SELECTED_EARLY_PAIR"
                        if final_id == early_id
                        else "G0_SELECTED_PROVIDER_ADJACENT_PAIR"
                    )
                elif final_state == "BASELINE_NON_ADMITTING":
                    outcome = "BASELINE_AGGREGATE_PENDING_NO_SELECTION"
                elif len(attempt_order) == 2:
                    outcome = "NO_GO_ABLATION_BASELINE"
                else:
                    outcome = "OTHER_VARIANT_PROOF_SEQUENCE_CANDIDATE"
                    other_variant_candidate = True
            order_decisions.append(
                {
                    "attemptOrder": attempt_order,
                    "aggregateOutcome": outcome,
                    "g0VariantId": g0_variant,
                    "otherVariantProofSequenceCandidate": other_variant_candidate,
                }
            )
        rows.append(
            {
                "variantResults": results,
                "attemptOrderDecisions": order_decisions,
            }
        )
    return rows


def _rejected_variant_safety_gate() -> list[dict[str, Any]]:
    return [
        {
            "rejectedVariantDeviceSafetyState": "BASELINE_HEALTHY",
            "gateOutcome": "FINAL_RESIDENT_HEALTH_REQUIRED",
            "freshOtherVariantQualificationMayBegin": False,
            "reason": "Pre-effect safety is not final resident health.",
        },
        {
            "rejectedVariantDeviceSafetyState": "RESIDENT_HEALTHY",
            "gateOutcome": "MAY_ENTER_FRESH_OTHER_VARIANT_QUALIFICATION",
            "freshOtherVariantQualificationMayBegin": True,
            "reason": "Proof sequence may proceed only to fresh qualification; independent review and separate authority remain required before UNIT_PREPARED.",
        },
        {
            "rejectedVariantDeviceSafetyState": "RECOVERY_REQUIRED",
            "gateOutcome": "RECOVERY_PARKED",
            "freshOtherVariantQualificationMayBegin": False,
            "reason": "Exact recovery and final resident health must close before any new non-recovery effect.",
        },
    ]


def _ablation_unit(
    role: str,
    gate_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    spec = ROLE_DESIGN[role]
    relevant_gate_ids = sorted(GLOBAL_BASELINE_GATE_IDS | set(spec["gates"]))
    return {
        "unitId": f"WP-H0-2-{spec['stage']}",
        "order": spec["order"],
        "removedRole": role,
        "deltaCardinality": 1,
        "parentGeneration": "EXACT_HEALTHY_G_N",
        "requiredUnchangedBindings": [
            "component-manifest-except-removed-role",
            "executables-and-transitive-inputs",
            "identities-capabilities-fds-namespaces-cgroups-scheduler",
            "property-and-ipc-input-generation",
            "firmware-rfs-and-device-inputs",
            "observer-metrics-and-budget-receipt",
            "boot-candidate-rollback-target-and-recovery-bindings",
        ],
        "roleSpecificRelevantGateIds": spec["gates"],
        "dependencyGateProjection": [
            _gate_projection(gate_by_id[gate_id]) for gate_id in relevant_gate_ids
        ],
        "effect": "DISABLE_EXACTLY_ONE_ROLE_AT_CONSTRUCTION",
        "replayPolicy": "NEVER_REDISPATCH_AFTER_DURABLE_EFFECT_INTENT",
        "failureChaining": "FORBIDDEN",
        "successPromotion": "ELIGIBLE_ONLY_AFTER_COMPLETE_TERMINAL_AND_FRESH_G_N_PLUS_1_BASELINE_QUALIFICATION",
        "globalNecessityClaimAllowed": False,
    }


def build_design(parent_data: dict[str, Any] | None = None) -> dict[str, Any]:
    if parent_data is None:
        raw, parent_data = _read_parent()
        parent_pin = {
            "path": PARENT_REL,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "schema": parent_data.get("schema"),
        }
    else:
        parent_data = copy.deepcopy(parent_data)
        rendered = json.dumps(parent_data, indent=2, sort_keys=True).encode() + b"\n"
        parent_pin = {
            "path": PARENT_REL,
            "bytes": len(rendered),
            "sha256": hashlib.sha256(rendered).hexdigest(),
            "schema": parent_data.get("schema"),
            "testInjected": True,
        }
    by_role = _validate_parent(parent_data)
    gate_by_id = {
        gate["gateId"]: gate for gate in parent_data["dependencyGates"]
    }
    arguments = [
        _role_argument(role, by_role[role])
        for role in sorted(EXPECTED_ROLES, key=lambda item: ROLE_DESIGN[item]["order"])
    ]
    units = [
        _ablation_unit(role, gate_by_id)
        for role in sorted(REMOVABLE_ROLES, key=lambda item: ROLE_DESIGN[item]["order"])
    ]
    return {
        "schema": "a90-h24-wlan-one-factor-ablation-design-v1",
        "authority": {
            "tier": "H0",
            "deviceContact": False,
            "privateInputRead": False,
            "candidateEligible": False,
            "deviceInstallAuthorized": False,
            "d0Authorized": False,
            "d1Authorized": False,
            "f1Authorized": False,
            "handoffAuthorized": False,
            "ufsMutationAuthorized": False,
            "propertyProvisionAuthorized": False,
            "liveExecutionAuthorized": False,
        },
        "parentInventory": parent_pin,
        "status": {
            "currentState": "H0_DESIGN_ONLY",
            "wpH02Design": "COMPLETE_H0_DESIGN_ONLY",
            "correctedHealthyBaseline": "ABSENT_UNPROVED",
            "executionQualification": "ABSENT",
            "independentExecutionReview": "ABSENT",
            "liveAuthority": False,
            "budgetStatus": "UNSET_REQUIRES_MEASURED_HEALTHY_BASELINE",
            "optionC": "BLOCKED_RESEARCH_ONLY",
        },
        "baselineFormation": {
            "h24IsHealthyAblationBaseline": False,
            "reasons": [
                "H24 never reached the selected helper route live.",
                "The selected source graph contains duplicate servicemanager and hwservicemanager instances.",
                "The selected source route can write global SELinux load and enforce interfaces.",
                "Its SD property snapshot is forbidden for a successor baseline.",
            ],
            "mandatoryCorrectionsBeforeAnyBaseline": [
                {
                    "correctionId": "A1_DEDUPLICATE_SM_HSM",
                    "rule": "Exactly one servicemanager and one hwservicemanager instance; construction, order, health, and cleanup derive from one generated manifest.",
                    "necessityEvidence": False,
                },
                {
                    "correctionId": "A2_ZERO_GLOBAL_SELINUX_MUTATION",
                    "rule": "Zero load-policy or enforce writes and zero read-write bind of global SELinuxFS.",
                    "necessityEvidence": False,
                },
                {
                    "correctionId": "A3_BOUND_OBSERVER_AND_SD_FREE_BOOTSTRAP",
                    "rule": "Bound non-mutating metrics plus SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED before execution.",
                    "necessityEvidence": False,
                },
            ],
            "dependencyGateProjection": [
                _gate_projection(gate_by_id[f"H0D{index:02d}"])
                for index in range(1, 11)
            ],
            "serviceManagerPlacementVariants": [
                {
                    "variantId": "B0_EARLY_PAIR",
                    "retainedInstances": ["servicemanager#1", "hwservicemanager#1"],
                    "removedDuplicateInstances": ["servicemanager#2", "hwservicemanager#2"],
                    "status": "UNPROVED_SEPARATE_FUTURE_BASELINE_UNIT",
                },
                {
                    "variantId": "B0_PROVIDER_ADJACENT_PAIR",
                    "retainedInstances": ["servicemanager#2", "hwservicemanager#2"],
                    "removedDuplicateInstances": ["servicemanager#1", "hwservicemanager#1"],
                    "status": "UNPROVED_SEPARATE_FUTURE_BASELINE_UNIT",
                },
            ],
            "variantRule": "Variants are mutually exclusive fresh units; never switch placement inside one unit or call duplicate correction a necessity result.",
            "selectionRule": "The first independently qualified variant with experimentProof=PROVED, deviceSafetyState=RESIDENT_HEALTHY, complete functional/metric/cleanup/recovery evidence, and generationOutcome=BASELINE_ADMITTED_G0 may become G0; BASELINE_HEALTHY alone is pre-effect safety and never admits G0.",
            "failureRule": "NO_GO_ABLATION_BASELINE requires exact REFUTED proof for both separately bound variants. NO_PROOF_OBSERVER, BASELINE_HEALTHY without final resident health, or RECOVERY_REQUIRED remains non-admitting and must not be collapsed into NO_GO.",
            "aggregateDecisionModel": {
                "requiredVariantIds": [
                    "B0_EARLY_PAIR",
                    "B0_PROVIDER_ADJACENT_PAIR",
                ],
                "normalizedVariantResults": {
                    "NOT_RUN": "No result exists for this exact variant.",
                    "BASELINE_ADMITTED_G0": "The variant result is BASELINE+PROVED+RESIDENT_HEALTHY and g0AdmissionEligible=true.",
                    "BASELINE_REJECTED": "The variant experimentProof is exact REFUTED; its independent device-safety state remains separately recorded.",
                    "BASELINE_NON_ADMITTING": "The variant is NO_PROOF_OBSERVER, final-health pending, recovery-parked, malformed, or otherwise non-admitting and non-refuted.",
                },
                "inputRule": "Bind exactly the two distinct required variant IDs. One result per ID is allowed. Duplicate ID, unknown ID/result, missing device-safety/proof fields for a present result, or attempt-order mismatch is INVALID_BASELINE_AGGREGATE_NO_SELECTION.",
                "resultAxesRule": "The normalized variant result is proof-sequence state only and never authorizes execution. Every present result retains its independent experimentProof, deviceSafetyState, and workflowState.",
                "sequenceRule": "Every normalized result pair enumerates each possible order of its distinct present variant IDs. A rejected result names only the other variant as a proof-sequence candidate. Admission stops variant execution. A non-admitting result freezes new effects. Any later attempt is an explicit INVALID effect-order outcome.",
                "decisionTable": _baseline_aggregate_decision_table(),
                "rejectedVariantSafetyGate": _rejected_variant_safety_gate(),
                "freshOtherVariantRule": "The other variant may begin fresh qualification only when the rejected variant's deviceSafetyState is RESIDENT_HEALTHY. Even then this H0 design grants no UNIT_PREPARED transition, execution review, or live authority; every ordinary prerequisite and fresh binding remains mandatory.",
                "noGoRule": "Exactly one normalized result tuple produces NO_GO_ABLATION_BASELINE: both distinct required variant IDs equal BASELINE_REJECTED; either distinct attempt order reaches the same terminal. Every NOT_RUN or BASELINE_NON_ADMITTING tuple is non-NO_GO.",
                "invalidInputOutcome": "INVALID_BASELINE_AGGREGATE_NO_SELECTION",
            },
        },
        "sdFreeBootstrap": {
            "selectedRule": "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET_OR_NO_GO",
            "beforeAnyExecution": [
                "Derive the superset only from exact public binaries, public defaults/config, and reviewed deterministic generators.",
                "Never read, copy, relocate, or bless the private whole property snapshot.",
                "Bind every bootstrap key, context, value source, generator byte, file identity, digest, and read-only lifetime.",
                "If a required value cannot be derived without the private snapshot, baseline formation is NO_GO.",
            ],
            "notSelectedAlternative": "A temporary SD-backed diagnostic would require a separate design, independent review, identity, and live authority; this design grants none.",
            "afterAblation": {
                "acceptedTerminals": [
                    "PROPERTY_ABSENT_PROVED",
                    "PROPERTY_FINITE_SEED_PROVED",
                ],
                "rule": "Freeze the retained-set minimum; a bootstrap superset is never production-minimality evidence.",
            },
        },
        "necessityArguments": arguments,
        "ablationUnits": units,
        "propertyExperiments": [
            {
                "unitId": "WP-H0-2-A11a",
                "singleVariable": "Remove the complete property read area.",
                "acceptedSuccess": "PROPERTY_ABSENT_PROVED",
                "mutuallyExclusiveWith": "WP-H0-2-A11b",
            },
            {
                "unitId": "WP-H0-2-A11b",
                "singleVariable": "Replace the bootstrap superset with one candidate finite seed.",
                "acceptedSuccess": "PROPERTY_FINITE_SEED_PROVED",
                "mutuallyExclusiveWith": "WP-H0-2-A11a",
            },
        ],
        "generationModel": {
            "initialGeneration": "G0_IS_FIRST_COMPLETE_CORRECTED_HEALTHY_BASELINE_NOT_H24",
            "unitRule": "Every removal unit derives from one exact healthy G_N and changes exactly one role.",
            "failedUnitRule": "Every outcome other than REMOVAL_SUPPORTED_FOR_GENERATION with an independently qualified fresh baseline is non-promotable; REFUTED, NO_PROOF_OBSERVER, health-pending, and recovery-parked outcomes never chain another removal.",
            "promotionRule": "One REMOVAL_SUPPORTED_FOR_GENERATION result may define proposed G_N_PLUS_1 only after a fresh full baseline qualification of those exact bytes and bindings.",
            "interactionRule": "Never promote a multi-removal batch; interactions are tested only by later units derived from a newly qualified generation.",
        },
        "stateMachine": {
            "currentState": "H0_DESIGN_ONLY",
            "futureStates": [
                "STATIC_PREREQUISITES_READY",
                "INDEPENDENTLY_REVIEWED",
                "SEPARATELY_AUTHORIZED",
                "UNIT_PREPARED",
                "EFFECT_INTENT_DURABLE",
                "EFFECT_DISPATCHED_ONCE",
                "OBSERVING",
                "TERMINAL",
            ],
            "currentReachableTransitions": [],
            "futureTransitionRules": [
                "No future live state is reachable from this document alone.",
                "UNIT_PREPARED requires exact target, healthy parent generation, candidate, rollback, recovery, observer, budget, and row-static bindings.",
                "Durably publish one exact effect intent before the first removal effect.",
                "After effect intent, never resend or replay the removal; reconciliation is observation, cleanup, rollback, recovery, and reporting only.",
                "Missing, mixed-run, malformed, stale, or ambiguous observation sets experimentProof=NO_PROOF_OBSERVER; independent safety uncertainty sets deviceSafetyState=RECOVERY_REQUIRED and workflowState=RECOVERY_PARKED.",
            ],
        },
        "outcomeVocabulary": {
            "deviceSafetyState": {
                "BASELINE_HEALTHY": "The exact pre-effect baseline remains controlled and recoverable.",
                "RESIDENT_HEALTHY": "Attended return or recovery closed exact native resident health.",
                "RECOVERY_REQUIRED": "Safety closure is missing, ambiguous, or requires exact recovery.",
            },
            "experimentProof": {
                "PROVED": "The exact proof subject passed with complete same-run evidence.",
                "REFUTED": "Exact same-run device evidence contradicts the proof subject.",
                "NO_PROOF_OBSERVER": "The host could not reach, parse, decide, or attribute the proof; new effects freeze and candidate replay remains forbidden.",
            },
            "workflowState": {
                "TERMINAL": "The device-safety axis is closed.",
                "RECOVERY_PARKED": "Exact recovery is the only device effect allowed; experiment proof remains independently recorded.",
            },
            "generationOutcome": {
                "BASELINE_ADMITTED_G0": "A corrected baseline proof passed and exact final resident health closed; this is the sole G0-admitting outcome.",
                "BASELINE_REJECTED": "Exact device evidence refuted the baseline subject.",
                "BASELINE_PROVED_FINAL_HEALTH_PENDING_NO_ADMISSION": "The baseline proof passed and pre-effect baseline health remains controlled, but final resident health is not closed; no G0 admission.",
                "BASELINE_PROVED_RECOVERY_PARKED_NO_ADMISSION": "The baseline proof passed but safety requires recovery; no G0 admission.",
                "REMOVAL_SUPPORTED_FOR_GENERATION": "The role-removal proof passed and final resident health closed for this generation only.",
                "REMOVAL_REFUTED_FOR_GENERATION": "Exact device evidence refuted this one-role removal for this generation only.",
                "REMOVAL_PROVED_RECOVERY_PARKED_NO_PROMOTION": "The removal proof passed but safety requires recovery; no promotion.",
                "REMOVAL_PROVED_FINAL_HEALTH_PENDING_NO_PROMOTION": "The removal proof passed but final resident health is not closed; no promotion.",
                "NO_PROOF_OBSERVER": "Experiment proof is unresolved; no promotion.",
                "NO_GO_ABLATION_BASELINE": "Both corrected placement variants were separately refuted; ablation stops.",
            },
        },
        "resultContract": {
            "requiredBindings": [
                "schema-and-unit-id",
                "target-resident-candidate-rollback-and-recovery",
                "parent-generation-and-component-manifest-digests",
                "removed-role-and-exact-one-delta-digest",
                "boot-run-nonce-and-durable-journal-chain",
                "observer-and-budget-receipt-digests",
                "original-stage-result-errno-and-separate-cleanup-result",
                "device-safety-experiment-proof-workflow-and-generation-outcome-scope",
            ],
            "functionalProof": [
                "firmware-ready",
                "root-pd-ready",
                "wmi-ready",
                "wlan0-exact-driver",
                "bounded-scan",
                "association",
                "dhcp-and-route",
                "authenticated-service-when-in-scope",
            ],
            "metrics": {
                "latency": ["component-ready", "backend-ready", "scan", "association", "dhcp", "cleanup", "recovery"],
                "footprint": ["process", "thread", "fd", "rss", "pss", "cgroup-memory", "binder-object", "qrtr-endpoint"],
                "runtime": ["cpu-time", "wakeups", "context-switches", "io-bytes", "cache-write", "fsync", "rename"],
                "network": ["throughput", "latency", "loss", "retransmit", "packet", "flow", "final-wifi-state"],
                "dependency": ["property-read-write", "binder-transaction", "qrtr-qmi-event", "firmware-rfs-request"],
                "cleanup": ["pid", "pgid", "cgroup", "namespace-fd", "device-fd", "socket", "property", "binder", "qrtr", "residue"],
            },
            "budgetRule": "No numeric pass budget exists. Derive and independently bind budgets from a measured corrected BASELINE_HEALTHY result before execution qualification.",
            "classificationModel": {
                "requiredRawFields": {
                    "proofSubject": ["BASELINE", "ROLE_REMOVAL"],
                    "observerOutcome": ["VALID_COMPLETE", "UNREACHABLE", "MISSING", "MALFORMED", "STALE", "MIXED_RUN", "AMBIGUOUS"],
                    "experimentEvidence": ["ALL_REQUIRED_PASSED", "REQUIRED_TERMINAL_OR_BUDGET_FAILED", "NOT_OBSERVED_OR_AMBIGUOUS"],
                    "attribution": ["BASELINE", "REMOVED_ROLE", "UNRESOLVED"],
                    "safetyClosureEvidence": ["EXACT_BASELINE_HEALTHY", "EXACT_RESIDENT_HEALTHY_AFTER_RETURN_OR_RECOVERY", "MISSING_AMBIGUOUS_OR_RECOVERY_REQUIRED"],
                },
                "normalizationRules": [
                    "VALID_COMPLETE remains VALID_COMPLETE; every other observerOutcome normalizes to INVALID_OR_UNRESOLVED.",
                    "REQUIRED_TERMINAL_OR_BUDGET_FAILED normalizes to ATTRIBUTABLE_CONTRADICTION only when exact same-run device evidence and attribution match the proof subject; otherwise it normalizes to NOT_OBSERVED_OR_AMBIGUOUS.",
                    "Attribution matches only BASELINE for proofSubject BASELINE or REMOVED_ROLE for proofSubject ROLE_REMOVAL; every other pair is DOES_NOT_MATCH_OR_UNRESOLVED.",
                ],
                "proofDecisionOrder": [
                    "First: matched ATTRIBUTABLE_CONTRADICTION -> REFUTED, regardless of observer defect.",
                    "Second: VALID_COMPLETE plus ALL_REQUIRED_PASSED plus matched attribution -> PROVED.",
                    "Else: NO_PROOF_OBSERVER.",
                ],
                "proofDecisionTable": _proof_decision_table(),
                "safetyDecisionTable": _safety_decision_table(),
                "generationDecisionTable": _generation_decision_table(),
                "coexistenceRule": "deviceSafetyState and experimentProof are never collapsed. REFUTED may coexist with RECOVERY_REQUIRED and workflow RECOVERY_PARKED; recovery uncertainty never erases or downgrades the exact device contradiction.",
                "invalidInputRule": "Unknown enum, missing field, duplicate row, impossible normalization, or unmatched table row is schema failure and closes experimentProof as NO_PROOF_OBSERVER, deviceSafetyState as RECOVERY_REQUIRED, workflowState as RECOVERY_PARKED, with no new effect or replay.",
            },
            "noProofRule": "Observer validity, experiment proof, device safety, and workflow are independent required fields; attributable device contradiction has proof precedence while safety uncertainty independently parks recovery.",
        },
        "promotionAndStopRules": {
            "optionCPromotionRequires": [
                "H0D01-through-H0D10-retired-by-declared-evidence-class",
                "one-property-terminal",
                "finite-retained-component-contract",
                "cold-relaunch-and-complete-shutdown",
                "Debian-owned-scan-association-and-dhcp",
                "capsule-containment-and-remote-workload-separation",
                "measured-budget-pass",
                "independent-security-and-execution-review",
            ],
            "permanentBoundaries": [
                "boot-only-transfer",
                "exact-rollback-and-physical-recovery",
                "target-isolation",
                "durable-no-replay",
                "private-evidence",
                "attended-fresh-authority",
                "final-native-health-after-return-or-recovery",
            ],
            "stop": "Any authority, input, target, graph, baseline, observer, budget, cleanup, rollback, recovery, or health ambiguity remains H0/NO_GO.",
        },
    }


def canonical_text() -> str:
    return json.dumps(build_design(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", type=Path, metavar="PATH")
    group.add_argument("--write", type=Path, nargs="?", const=DEFAULT_OUTPUT, metavar="PATH")
    args = parser.parse_args()
    rendered = canonical_text()
    if args.check is not None:
        if args.check.read_text() != rendered:
            raise SystemExit(f"design drift: {args.check}")
        return 0
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered)
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
