#!/usr/bin/env python3
"""Generate and validate the host-only A90 WP2-4 property observation schema.

This unit defines future evidence shapes only.  It does not implement an
observer, contact a target, retire H0D04/H0D10, or authorize execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BASE = "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
DEFAULT_OUTPUT = ROOT / BASE / "schema/a90-h24-wlan-property-observation-schema-v1.json"

DEPENDENCY_REL = f"{BASE}/inventory/a90-h24-wlan-dependency-surface-inventory-v1.json"
POLICY_REL = f"{BASE}/policy/a90-h24-wlan-forbidden-surface-policy-v1.json"
DESIGN_REL = f"{BASE}/design/a90-h24-wlan-one-factor-ablation-design-v1.json"
SOURCE_REPORT_REL = "docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md"
MAC_REPORT_REL = "docs/reports/A90_WLAN_MAC_PROVISIONING_EXISTING_EVIDENCE_H0_2026-08-16.md"

PINNED_INPUTS = {
    DEPENDENCY_REL: (
        111287,
        "23e40105a6bfd9b86ef98897bd22734a66dcd0991af1b87fcd0f380bdd622be8",
    ),
    POLICY_REL: (
        39695,
        "af4b25c766746a5297c4b7f7f48bec6dba429dac9775e738e758f96ccbae1b58",
    ),
    DESIGN_REL: (
        105900,
        "0eddec9ba9d637590c82499709179bd6b56a79d646d7967d3049a0bf36136b85",
    ),
    SOURCE_REPORT_REL: (
        25810,
        "1d1c15850619f278d7d56e0702ffc23197a216602f5d9e4ef6be78fc4db3fffb",
    ),
    MAC_REPORT_REL: (
        14212,
        "14d0d2bf24397520beebf7642b38b218af2ce966678f090e53070049ad9e4ba3",
    ),
}

SCHEMA = "a90-h24-wlan-property-observation-schema-v1"
RESULT_SCHEMA = "a90-h24-wlan-property-observation-result-v1"
PHASES = (
    "CLEAN_LAUNCH",
    "READINESS",
    "SCAN",
    "ASSOCIATION",
    "DHCP_ROUTE",
    "STEADY_STATE",
    "SHUTDOWN",
    "COLD_RELAUNCH",
)
PARENT_ROLE_VOCABULARY = (
    "servicemanager",
    "hwservicemanager",
    "qrtr_ns",
    "pd_mapper",
    "rmt_storage",
    "tftp_server",
    "vndservicemanager",
    "pm_proxy_helper",
    "per_mgr",
    "cnss_diag",
    "cnss_daemon",
    "property-service-shim",
    "modem-holder",
    "wifi-helper",
)
PROPERTY_OPERATIONS = ("READ", "WRITE", "ACK")
PROPERTY_RESULTS = ("SUCCESS", "MISSING", "DENIED", "ERROR")
TERMINALS = ("PROPERTY_ABSENT_PROVED", "PROPERTY_FINITE_SEED_PROVED")
MAC_STATES = ("PRESENT_VALID", "ABSENT_PARSED", "UNREADABLE_OR_MALFORMED")
WLAN_OUTCOMES = (
    "WLAN0_UP_EXACT_DRIVER",
    "MAC_INIT_FAILED_EXACT_SIGNATURE",
    "OTHER_OR_UNPROVED",
)
MAC_DECISIONS = (
    "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
    "MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
    "MAC_PROVISION_VALUE_UNRESOLVED",
    "NO_PROOF_OBSERVER",
)

AUTHORITY_KEYS = {
    "candidateEligible",
    "d0Authorized",
    "d1Authorized",
    "deviceContact",
    "deviceInstallAuthorized",
    "f1Authorized",
    "handoffAuthorized",
    "liveExecutionAuthorized",
    "privateInputAuthorityGranted",
    "propertyProvisionAuthorized",
    "tier",
    "ufsMutationAuthorized",
}
TOP_LEVEL_KEYS = {
    "authority",
    "coverageContract",
    "eventContract",
    "generatedDeterministically",
    "globalKernelObjectRule",
    "macProvisioningEffectObservation",
    "negativeCorpus",
    "observationPhases",
    "resultContract",
    "schema",
    "scope",
    "sequencingConstraint",
    "sourcePins",
    "status",
    "terminals",
}
RESULT_KEYS = {
    "bindings",
    "coldRelaunchRoles",
    "coverage",
    "deviceSafetyState",
    "events",
    "expectedRoles",
    "experimentProof",
    "macProvisioningEffect",
    "processInstances",
    "persistentAcrossRelaunchRoles",
    "schema",
    "seedEntries",
    "seedFilesystem",
    "terminal",
    "trace",
    "workflowState",
}
BINDING_KEYS = {
    "bootIdSha256",
    "candidateSha256",
    "componentManifestSha256",
    "observerSha256",
    "observationBudgetSha256",
    "parentGenerationSha256",
    "qualificationSha256",
    "residentBuild",
    "runNonce",
    "target",
    "traceSha256",
}
QUALIFIED_BINDING_KEYS = BINDING_KEYS - {"traceSha256"}
QUALIFIED_EXPECTATION_KEYS = {
    "bindingProjection",
    "coldRelaunchRoles",
    "eventCountCap",
    "expectedRoles",
    "persistentAcrossRelaunchRoles",
    "seedContractSha256",
    "traceByteCap",
}
COVERAGE_KEYS = {
    "endBoundaryProved",
    "eventLossCount",
    "observerComplete",
    "phase",
    "processInstanceIds",
    "role",
    "startBoundaryProved",
    "state",
}
EVENT_KEYS = {
    "context",
    "errno",
    "key",
    "operation",
    "phase",
    "processInstanceId",
    "requestId",
    "result",
    "returnedDefault",
    "role",
    "sequence",
    "sourceId",
    "valueBytes",
    "valueSha256",
}
PROCESS_INSTANCE_KEYS = {
    "executableSha256",
    "exitReceiptSha256",
    "identitySha256",
    "instanceId",
    "launchEpoch",
    "launchReceiptSha256",
    "lifecycleClosure",
    "pid",
    "role",
    "starttime",
}
TRACE_KEYS = {
    "closed",
    "declaredEventCount",
    "droppedEvents",
    "duplicateEvents",
    "fabricatedDefaultEvents",
    "firstSequence",
    "eventCountCap",
    "lastSequence",
    "malformedEvents",
    "mixedRun",
    "observerOutcome",
    "traceByteCap",
    "traceBytes",
    "truncated",
    "unknownEvents",
}
SEED_KEYS = {
    "context",
    "key",
    "readers",
    "seedId",
    "sourceBytes",
    "sourceGid",
    "sourceKind",
    "sourceMode",
    "sourceNlink",
    "sourcePath",
    "sourceReadOnlyLifetime",
    "sourceSha256",
    "sourceUid",
    "valueBytes",
    "valueSha256",
}
SEED_FS_KEYS = {
    "digestStable",
    "generationMatches",
    "hardlinkAliasCount",
    "memberNames",
    "memberSetSha256",
    "rootPath",
    "rootReadOnly",
    "specialFileCount",
    "state",
    "symlinkCount",
    "unexpectedMembers",
}
MAC_EFFECT_KEYS = {
    "cnssUtilsMacState",
    "debugfsIdentityBound",
    "decision",
    "driverIdentityBound",
    "readComplete",
    "sameBoot",
    "sameRun",
    "sourceIdentityBound",
    "wlanOutcome",
}


def _lexical_regular(rel: str) -> Path:
    path = ROOT / rel
    cursor = ROOT
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"WP2-4 input contains a symlink: {rel}")
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"WP2-4 input is not a single-link regular file: {rel}")
    if ROOT not in path.resolve().parents:
        raise ValueError(f"WP2-4 input escapes repository: {rel}")
    return path


def _read_pinned(rel: str) -> bytes:
    path = _lexical_regular(rel)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError(f"WP2-4 opened input is not a single-link regular file: {rel}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, key) != getattr(after, key) for key in stable_fields):
        raise ValueError(f"WP2-4 input changed while being read: {rel}")
    raw = b"".join(chunks)
    size, sha256 = PINNED_INPUTS[rel]
    if len(raw) != size:
        raise ValueError(f"WP2-4 input size drift: {rel}")
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError(f"WP2-4 input digest drift: {rel}")
    return raw


def _pin(rel: str) -> dict[str, Any]:
    size, sha256 = PINNED_INPUTS[rel]
    return {"path": rel, "bytes": size, "sha256": sha256}


def _load_inputs() -> dict[str, Any]:
    raw = {rel: _read_pinned(rel) for rel in PINNED_INPUTS}
    return {
        "dependency": json.loads(raw[DEPENDENCY_REL]),
        "policy": json.loads(raw[POLICY_REL]),
        "design": json.loads(raw[DESIGN_REL]),
        "sourceReport": raw[SOURCE_REPORT_REL].decode(),
        "macReport": raw[MAC_REPORT_REL].decode(),
    }


def _require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        if token not in text:
            raise ValueError(f"WP2-4 {label} evidence drift: {token}")


def _require_source_contract(inputs: dict[str, Any]) -> None:
    dependency = inputs["dependency"]
    policy = inputs["policy"]
    design = inputs["design"]
    if dependency.get("schema") != "a90-h24-wlan-dependency-surface-inventory-v1":
        raise ValueError("WP2-4 dependency schema drift")
    if dependency.get("status", {}).get("dependencyGatesRetired") != []:
        raise ValueError("WP2-4 parent retired a dependency gate")
    if dependency.get("nextSequencingConstraint", {}).get("wp2_4") != (
        "MAY_DESIGN_PROPERTY_OBSERVATION_SCHEMA_FROM_UNPROVED_PROPERTY_SLOTS_H0_ONLY"
    ):
        raise ValueError("WP2-4 parent sequencing drift")
    roles = dependency.get("roles", [])
    if [row.get("role") for row in roles] != list(PARENT_ROLE_VOCABULARY) or any(
        row.get("dependencySurfaces", {}).get("property", {}).get("gateIds")
        != ["H0D04"]
        for row in roles
    ):
        raise ValueError("WP2-4 parent property-slot coverage drift")
    if policy.get("schema") != "a90-h24-wlan-forbidden-surface-policy-v1":
        raise ValueError("WP2-4 policy schema drift")
    if policy.get("status", {}).get("executionImplementation") != "ABSENT":
        raise ValueError("WP2-4 parent execution status drift")
    if design.get("schema") != "a90-h24-wlan-one-factor-ablation-design-v1":
        raise ValueError("WP2-4 design schema drift")
    experiments = design.get("propertyExperiments")
    if [row.get("acceptedSuccess") for row in experiments or []] != list(TERMINALS):
        raise ValueError("WP2-4 property terminal drift")
    for parent in (dependency, policy, design):
        authority = parent.get("authority", {})
        if authority.get("tier") != "H0" or any(
            flag is not False for key, flag in authority.items() if key != "tier"
        ):
            raise ValueError("WP2-4 parent authority drift")

    _require_tokens(
        inputs["sourceReport"],
        (
            "one global `qrtr_ports` IDR and one global endpoint list",
            "network namespace, `pivot_root`, or mount isolation is **not a proved QRTR",
            "denied the entire `AF_QIPCRTR` socket family",
        ),
        "source report",
    )
    _require_tokens(
        inputs["macReport"],
        (
            "same persistent\n`priv->wlan_mac_addr.no_of_mac_addr_set`",
            "`cnss_utils_mac_show()`",
            "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
            "MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
            "an empty string caused by a\nread error is never “absent.”",
        ),
        "MAC report",
    )


def _authority() -> dict[str, Any]:
    return {
        "tier": "H0",
        "candidateEligible": False,
        "deviceInstallAuthorized": False,
        "d0Authorized": False,
        "d1Authorized": False,
        "f1Authorized": False,
        "handoffAuthorized": False,
        "ufsMutationAuthorized": False,
        "propertyProvisionAuthorized": False,
        "liveExecutionAuthorized": False,
        "privateInputAuthorityGranted": False,
        "deviceContact": False,
    }


def classify_mac_effect(
    mac_state: str,
    wlan_outcome: str,
    observation_bound_complete: bool,
) -> str:
    if (
        mac_state not in MAC_STATES
        or wlan_outcome not in WLAN_OUTCOMES
        or type(observation_bound_complete) is not bool
    ):
        return "NO_PROOF_OBSERVER"
    if not observation_bound_complete:
        return "NO_PROOF_OBSERVER"
    if mac_state == "PRESENT_VALID" and wlan_outcome == "WLAN0_UP_EXACT_DRIVER":
        return "MAC_PROVISION_VALUE_UNRESOLVED"
    if mac_state == "ABSENT_PARSED" and wlan_outcome == "WLAN0_UP_EXACT_DRIVER":
        return "MAC_PROVISION_FALSE_PROVED_EXACT_RUN"
    if (
        mac_state == "ABSENT_PARSED"
        and wlan_outcome == "MAC_INIT_FAILED_EXACT_SIGNATURE"
    ):
        return "MAC_PROVISION_TRUE_PROVED_EXACT_RUN"
    return "NO_PROOF_OBSERVER"


def _mac_decision_table() -> list[dict[str, Any]]:
    return [
        {
            "cnssUtilsMacState": mac_state,
            "wlanOutcome": wlan_outcome,
            "observationBoundComplete": bound,
            "decision": classify_mac_effect(mac_state, wlan_outcome, bound),
        }
        for mac_state in MAC_STATES
        for wlan_outcome in WLAN_OUTCOMES
        for bound in (False, True)
    ]


def _negative_corpus() -> list[dict[str, str]]:
    return [
        {"caseId": "N01", "mutation": "missing-phase-role-coverage", "expected": "COVERAGE_MISMATCH"},
        {"caseId": "N02", "mutation": "dropped-event", "expected": "OBSERVER_INCOMPLETE"},
        {"caseId": "N03", "mutation": "fabricated-default", "expected": "OBSERVER_INCOMPLETE"},
        {"caseId": "N04", "mutation": "mixed-run", "expected": "OBSERVER_INCOMPLETE"},
        {"caseId": "N05", "mutation": "trace-digest-drift", "expected": "TRACE_DIGEST_MISMATCH"},
        {"caseId": "N06", "mutation": "absent-terminal-with-successful-read", "expected": "SUCCESSFUL_READ_PRESENT"},
        {"caseId": "N07", "mutation": "finite-seed-unmapped-read", "expected": "SEED_READ_MAPPING_MISMATCH"},
        {"caseId": "N08", "mutation": "finite-seed-extra-entry", "expected": "SEED_READ_MAPPING_MISMATCH"},
        {"caseId": "N09", "mutation": "duplicate-key-context", "expected": "SEED_SCHEMA_MISMATCH"},
        {"caseId": "N10", "mutation": "writable-seed", "expected": "SEED_SCHEMA_MISMATCH"},
        {"caseId": "N11", "mutation": "symlink-or-hardlink-seed", "expected": "SEED_SCHEMA_MISMATCH"},
        {"caseId": "N12", "mutation": "unexpected-seed-member", "expected": "SEED_SCHEMA_MISMATCH"},
        {"caseId": "N13", "mutation": "recovery-required-terminal", "expected": "SAFETY_PROOF_MISMATCH"},
        {"caseId": "N14", "mutation": "mac-read-error-normalized-to-absent", "expected": "MAC_EFFECT_MISMATCH"},
        {"caseId": "N15", "mutation": "mac-present-up-promoted-to-false", "expected": "MAC_EFFECT_MISMATCH"},
        {"caseId": "N16", "mutation": "namespace-only-global-object-claim", "expected": "PINNED_SEMANTIC_MISMATCH"},
        {"caseId": "N17", "mutation": "enable-live-authority", "expected": "AUTHORITY_MISMATCH"},
        {"caseId": "N18", "mutation": "claim-h0d04-retired", "expected": "STATUS_MISMATCH"},
        {"caseId": "N19", "mutation": "unknown-result-field", "expected": "RESULT_SCHEMA_MISMATCH"},
        {"caseId": "N20", "mutation": "unknown-schema-field", "expected": "TOP_LEVEL_SCHEMA_MISMATCH"},
        {"caseId": "N21", "mutation": "missing-or-misattributed-relaunch-process", "expected": "PROCESS_IDENTITY_MISMATCH"},
        {"caseId": "N22", "mutation": "orphan-duplicate-or-drifted-write-ack", "expected": "WRITE_ACK_MISMATCH"},
        {"caseId": "N23", "mutation": "missing-or-self-nominated-qualified-generation", "expected": "QUALIFIED_EXPECTATION_MISSING"},
        {"caseId": "N24", "mutation": "read-error-or-denial-promoted-to-terminal", "expected": "READ_OUTCOME_INCOMPLETE"},
        {"caseId": "N25", "mutation": "event-phase-regression", "expected": "EVENT_PHASE_ORDER_MISMATCH"},
        {"caseId": "N26", "mutation": "write-ack-crosses-phase-or-lifecycle", "expected": "WRITE_ACK_MISMATCH"},
        {"caseId": "N27", "mutation": "result-raises-qualified-event-or-byte-cap", "expected": "QUALIFIED_EXPECTATION_MISMATCH"},
        {"caseId": "N28", "mutation": "budget-digest-does-not-match-qualified-caps", "expected": "QUALIFIED_EXPECTATION_MISMATCH"},
        {"caseId": "N29", "mutation": "boolean-substituted-for-integer-trace-counter", "expected": "OBSERVER_INCOMPLETE"},
        {"caseId": "N30", "mutation": "unhashable-process-instance-id-container", "expected": "COVERAGE_MISMATCH"},
        {"caseId": "N31", "mutation": "integer-substituted-for-mac-binding-boolean", "expected": "MAC_EFFECT_MISMATCH"},
        {"caseId": "N32", "mutation": "unhashable-launch-epoch", "expected": "PROCESS_IDENTITY_MISMATCH"},
        {"caseId": "N33", "mutation": "unhashable-event-identity-or-result", "expected": "EVENT_SCHEMA_MISMATCH"},
        {"caseId": "N34", "mutation": "declared-seed-reader-not-observed-reading", "expected": "SEED_READ_MAPPING_MISMATCH"},
        {"caseId": "N35", "mutation": "declared-launch-epoch-never-observed-running", "expected": "PROCESS_IDENTITY_MISMATCH"},
    ]


def build_schema() -> dict[str, Any]:
    inputs = _load_inputs()
    _require_source_contract(inputs)
    roles = [row["role"] for row in inputs["dependency"]["roles"]]
    return {
        "schema": SCHEMA,
        "generatedDeterministically": True,
        "scope": {
            "target": "Samsung Galaxy A90 5G only",
            "workPackage": "WP2-4",
            "purpose": "property read/write observation and terminal validation contract",
            "parentRoleVocabulary": roles,
            "doesNotProve": [
                "a successful property observation",
                "property absence or a finite seed",
                "the deployed enable_mac_provision value outside one exact run",
                "H0D04 or H0D10 retirement",
                "Option C feasibility or implementation",
            ],
        },
        "authority": _authority(),
        "sourcePins": [_pin(rel) for rel in PINNED_INPUTS],
        "status": {
            "wp2_4": "COMPLETE_H0_PROPERTY_OBSERVATION_SCHEMA_AND_TERMINAL_VALIDATORS_ONLY",
            "runtimeObserverImplementation": "ABSENT",
            "byteDerivedConsumer": "ABSENT",
            "executionQualification": "ABSENT",
            "independentExecutionReview": "ABSENT",
            "h0d04": "UNPROVED",
            "h0d10": "UNPROVED",
            "macProvisioningValue": "UNPROVED_OUTSIDE_ONE_EXACT_FUTURE_RUN",
            "dependencyGatesRetired": [],
            "optionC": "BLOCKED_RESEARCH_ONLY",
        },
        "observationPhases": list(PHASES),
        "coverageContract": {
            "rule": "The exact retained-role set crossed with every phase appears once; each cell is complete or proves that role not running in that phase, and every event names the bound process instance for that cell.",
            "states": ["RUNNING_OBSERVED", "PROVED_NOT_RUNNING"],
            "lifecycle": "The retained-role set is exactly partitioned into roles relaunched with INITIAL plus COLD_RELAUNCH identities and trusted supervisor roles that persist with one INITIAL identity; at least one role must actually relaunch, every INITIAL identity is observed running before COLD_RELAUNCH, every COLD_RELAUNCH identity is observed running in that phase, and every identity is exit/reap bound before a property terminal.",
            "failure": "Missing, duplicate, lossy, late-attached, or early-detached coverage is NO_PROOF_OBSERVER.",
        },
        "eventContract": {
            "operations": list(PROPERTY_OPERATIONS),
            "results": list(PROPERTY_RESULTS),
            "rules": [
                "Every event is bound to one run, role, phase, request, key, context, source, result, errno, value length, and value digest.",
                "Every event is attributed to one exact launch-epoch process identity already bound by coverage.",
                "Event sequence is monotonic in the frozen phase order; a later phase cannot be followed by an earlier phase.",
                "Raw values are private evidence and never appear in the public schema; exactness is carried by size and SHA-256.",
                "READ, WRITE, and ACK remain distinct; a successful ACK never proves a read value changed.",
                "Every WRITE has exactly one later ACK from the same exact process identity in the same phase with the same request, role, key, context, source, length, and digest; orphan, duplicate, reordered, cross-lifecycle, or drifted ACK is invalid.",
                "A returned or synthesized default is an event and never counts as property absence.",
                "A READ error or denial is NO_PROOF and cannot publish either property terminal; MISSING remains an explicit observed result rather than an observer error.",
            ],
        },
        "terminals": {
            "PROPERTY_ABSENT_PROVED": {
                "requires": [
                    "complete exact-role-by-phase coverage",
                    "zero successful READ events",
                    "zero READ error or denial events",
                    "zero fabricated-default events",
                    "seed filesystem proved absent",
                    "exact final RESIDENT_HEALTHY and experiment PROVED",
                ],
                "writeAckScope": "WRITE and ACK remain separately observed and do not become read-seed evidence.",
            },
            "PROPERTY_FINITE_SEED_PROVED": {
                "requires": [
                    "complete exact-role-by-phase coverage",
                    "every successful READ maps one-to-one to one canonical seed key/context/value/source",
                    "zero READ error or denial events",
                    "every canonical seed entry is used by at least one exact retained reader",
                    "one read-only exact-member regular-file seed with stable generation and digest",
                    "exact final RESIDENT_HEALTHY and experiment PROVED",
                ],
                "rejects": [
                    "unknown or duplicate key/context",
                    "extra or unused seed entry",
                    "writable, symlink, hardlink, special, truncated, wrong-generation, or digest-drifted input",
                ],
            },
        },
        "macProvisioningEffectObservation": {
            "surface": "/sys/kernel/debug/cnss_utils/mac_address",
            "sourceState": "same persistent provisioned-MAC count and bytes as cnss_utils_get_wlan_mac_address; getter does not consume them",
            "bindingRule": "Same boot, run, built-in cnss_utils instance, source, driver, debugfs identity, complete read, and exact driver outcome are all required.",
            "uniqueFailure": "getting MAC address from platform driver failed",
            "decisionTable": _mac_decision_table(),
            "scopeRule": "A proved exact-run value does not prove another build, boot, INI, or future generation.",
        },
        "globalKernelObjectRule": {
            "default": "Namespace membership is never evidence that a global or shared kernel object is contained. Name the object's actual scope and prove its deny, non-nameability, or sole mediated owner individually.",
            "unknownScope": "NO_GO",
            "cases": [
                {
                    "object": "QRTR node, endpoint, and port registries",
                    "ineffectiveBoundary": "network namespace",
                    "requiredControl": "Non-relaxable coupled invariant: remote service/workload direct socket policy denies AF_QIPCRTR on every native ABI, compat socketcall remains denied because its pointed argument vector is not safely filterable, namespace-escape syscalls and legacy clone namespace flags remain denied, and no QRTR FD is inherited; a trusted capsule QRTR role remains separately bounded.",
                },
                {
                    "object": "SELinux loaded policy and enforcing state",
                    "ineffectiveBoundary": "namespace placement; SELinux has no per-capsule policy namespace here",
                    "requiredControl": "Zero read-write bind of native SELinuxFS and zero load/enforce or equivalent global-policy write.",
                },
                {
                    "object": "ancestor task proc magic links including root, fd, and ns",
                    "ineffectiveBoundary": "mount namespace with shared PID visibility/procfs",
                    "requiredControl": "Fresh nested PID namespace with its matching procfs and proved ancestor-task non-nameability; path hiding alone is rejected.",
                },
            ],
        },
        "resultContract": {
            "schema": RESULT_SCHEMA,
            "topLevelFields": sorted(RESULT_KEYS),
            "terminalValidators": [
                "validate_property_absent_result",
                "validate_property_finite_seed_result",
            ],
            "safetyRule": "A property terminal requires PROVED plus final RESIDENT_HEALTHY; observer failure and recovery uncertainty cannot publish it.",
            "qualifiedExpectationRule": "Validation requires a separately qualified pre-effect binding projection (all result bindings except the post-run trace digest), exact retained-role and relaunch-lifecycle partition, exact candidate seed-contract digest, and exact event/byte caps; a result cannot nominate its own generation, role set, seed, or limits.",
            "budgetRule": "Positive event-count and byte caps are canonically hashed together as observationBudgetSha256 before execution; the validator recomputes that digest, and this H0 schema invents no numeric live budget.",
            "noReplayRule": "This H0 validator never dispatches or retries an effect. Future no-replay behavior belongs to WP2-5b and separate review.",
        },
        "negativeCorpus": _negative_corpus(),
        "sequencingConstraint": {
            "next": "WP2-5b may consume this schema only after an exact byte-derived producer/consumer, independent execution review, recovery binding, operator-accepted budget, and separate live authority exist.",
            "h0d04": "Remains UNPROVED until one valid exact-run terminal is independently accepted.",
            "h0d10": "Remains UNPROVED until the retained property input is absent or one deterministic public SD-free seed is frozen.",
            "optionC": "All H0D01-H0D10 and the global-object containment/switch conditions remain blocking.",
        },
    }


def validate_schema(value: Any) -> list[str]:
    findings: set[str] = set()
    if not isinstance(value, dict) or set(value) != TOP_LEVEL_KEYS:
        return ["TOP_LEVEL_SCHEMA_MISMATCH"]
    if value.get("schema") != SCHEMA or value.get("generatedDeterministically") is not True:
        findings.add("TOP_LEVEL_SCHEMA_MISMATCH")
    authority = value.get("authority")
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_KEYS:
        findings.add("AUTHORITY_MISMATCH")
    elif authority.get("tier") != "H0" or any(
        flag is not False for key, flag in authority.items() if key != "tier"
    ):
        findings.add("AUTHORITY_MISMATCH")
    status = value.get("status")
    if (
        not isinstance(status, dict)
        or status.get("dependencyGatesRetired") != []
        or status.get("h0d04") != "UNPROVED"
        or status.get("h0d10") != "UNPROVED"
        or status.get("optionC") != "BLOCKED_RESEARCH_ONLY"
    ):
        findings.add("STATUS_MISMATCH")
    if value.get("sourcePins") != [_pin(rel) for rel in PINNED_INPUTS]:
        findings.add("SOURCE_PIN_MISMATCH")
    if value.get("observationPhases") != list(PHASES):
        findings.add("PHASE_SET_MISMATCH")
    if value.get("negativeCorpus") != _negative_corpus():
        findings.add("NEGATIVE_CORPUS_MISMATCH")
    mac_observation = value.get("macProvisioningEffectObservation")
    table = (
        mac_observation.get("decisionTable")
        if isinstance(mac_observation, dict)
        else None
    )
    if table != _mac_decision_table():
        findings.add("MAC_DECISION_TABLE_MISMATCH")
    try:
        canonical = build_schema()
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        findings.add("PINNED_SEMANTIC_MODEL_UNAVAILABLE")
    else:
        if value != canonical:
            findings.add("PINNED_SEMANTIC_MISMATCH")
    return sorted(findings)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _event_digest(events: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_event_bytes(events)).hexdigest()


def _event_bytes(events: list[dict[str, Any]]) -> bytes:
    return json.dumps(events, sort_keys=True, separators=(",", ":")).encode()


def _member_digest(names: list[str]) -> str:
    aggregate = hashlib.sha256()
    for name in names:
        aggregate.update(name.encode())
        aggregate.update(b"\0")
    return aggregate.hexdigest()


def _seed_contract_digest(value: Any) -> str:
    contract = {
        "seedEntries": value.get("seedEntries") if isinstance(value, dict) else None,
        "seedFilesystem": value.get("seedFilesystem") if isinstance(value, dict) else None,
    }
    return hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _observation_budget_digest(event_count_cap: Any, trace_byte_cap: Any) -> str:
    contract = {
        "eventCountCap": event_count_cap,
        "traceByteCap": trace_byte_cap,
    }
    return hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _validate_common_result(value: Any, qualified_expectation: Any) -> set[str]:
    findings: set[str] = set()
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        return {"RESULT_SCHEMA_MISMATCH"}
    if value.get("schema") != RESULT_SCHEMA or value.get("terminal") not in TERMINALS:
        findings.add("RESULT_SCHEMA_MISMATCH")
    if (
        not isinstance(qualified_expectation, dict)
        or set(qualified_expectation) != QUALIFIED_EXPECTATION_KEYS
    ):
        findings.add("QUALIFIED_EXPECTATION_MISSING")
    else:
        result_bindings = value.get("bindings")
        result_trace = value.get("trace")
        result_projection = (
            {key: result_bindings.get(key) for key in QUALIFIED_BINDING_KEYS}
            if isinstance(result_bindings, dict)
            else None
        )
        if (
            qualified_expectation.get("bindingProjection") != result_projection
            or qualified_expectation.get("expectedRoles")
            != value.get("expectedRoles")
            or qualified_expectation.get("coldRelaunchRoles")
            != value.get("coldRelaunchRoles")
            or qualified_expectation.get("persistentAcrossRelaunchRoles")
            != value.get("persistentAcrossRelaunchRoles")
            or not isinstance(result_trace, dict)
            or qualified_expectation.get("eventCountCap")
            != result_trace.get("eventCountCap")
            or qualified_expectation.get("traceByteCap")
            != result_trace.get("traceByteCap")
            or qualified_expectation.get("seedContractSha256")
            != _seed_contract_digest(value)
            or not isinstance(result_bindings, dict)
            or result_bindings.get("observationBudgetSha256")
            != _observation_budget_digest(
                result_trace.get("eventCountCap"),
                result_trace.get("traceByteCap"),
            )
        ):
            findings.add("QUALIFIED_EXPECTATION_MISMATCH")
    bindings = value.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != BINDING_KEYS:
        findings.add("BINDING_MISMATCH")
    else:
        if bindings.get("target") != "Samsung Galaxy A90 5G" or not all(
            isinstance(bindings.get(key), str) and bindings[key]
            for key in ("residentBuild", "runNonce")
        ):
            findings.add("BINDING_MISMATCH")
        for key in BINDING_KEYS - {"target", "residentBuild", "runNonce"}:
            if not _is_sha256(bindings.get(key)):
                findings.add("BINDING_MISMATCH")

    roles = value.get("expectedRoles")
    if (
        not isinstance(roles, list)
        or not roles
        or any(not isinstance(role, str) or not role for role in roles)
        or roles != sorted(roles)
        or len(roles) != len(set(roles))
    ):
        findings.add("COVERAGE_MISMATCH")
        roles = []
    elif not set(roles) <= set(PARENT_ROLE_VOCABULARY):
        findings.add("ROLE_VOCABULARY_MISMATCH")
    cold_roles = value.get("coldRelaunchRoles")
    persistent_roles = value.get("persistentAcrossRelaunchRoles")
    if (
        not isinstance(cold_roles, list)
        or not cold_roles
        or any(not isinstance(role, str) or not role for role in cold_roles)
        or cold_roles != sorted(set(cold_roles))
        or not isinstance(persistent_roles, list)
        or any(
            not isinstance(role, str) or not role for role in persistent_roles
        )
        or persistent_roles != sorted(set(persistent_roles))
        or set(cold_roles) & set(persistent_roles)
        or set(cold_roles) | set(persistent_roles) != set(roles)
    ):
        findings.add("PROCESS_IDENTITY_MISMATCH")
        cold_roles = []
        persistent_roles = []
    instances = value.get("processInstances")
    by_instance: dict[str, dict[str, Any]] = {}
    pid_start_identities: set[tuple[int, int]] = set()
    role_epochs: dict[str, set[str]] = {role: set() for role in roles}
    instance_order: list[tuple[str, str]] = []
    if not isinstance(instances, list):
        findings.add("PROCESS_IDENTITY_MISMATCH")
    else:
        for instance in instances:
            if not isinstance(instance, dict) or set(instance) != PROCESS_INSTANCE_KEYS:
                findings.add("PROCESS_IDENTITY_MISMATCH")
                continue
            instance_id = instance.get("instanceId")
            role = instance.get("role")
            epoch = instance.get("launchEpoch")
            if (
                not isinstance(instance_id, str)
                or not instance_id
                or instance_id in by_instance
                or role not in roles
                or not isinstance(epoch, str)
                or epoch not in {"INITIAL", "COLD_RELAUNCH"}
                or type(instance.get("pid")) is not int
                or instance["pid"] <= 0
                or type(instance.get("starttime")) is not int
                or instance["starttime"] <= 0
                or (instance["pid"], instance["starttime"])
                in pid_start_identities
                or not all(
                    _is_sha256(instance.get(key))
                    for key in (
                        "executableSha256",
                        "identitySha256",
                        "launchReceiptSha256",
                        "exitReceiptSha256",
                    )
                )
                or instance.get("lifecycleClosure") != "EXITED_REAPED_BOUND"
            ):
                findings.add("PROCESS_IDENTITY_MISMATCH")
                continue
            by_instance[instance_id] = instance
            pid_start_identities.add((instance["pid"], instance["starttime"]))
            role_epochs[role].add(epoch)
            instance_order.append((role, epoch))
        if any(
            epochs
            != (
                {"INITIAL", "COLD_RELAUNCH"}
                if role in cold_roles
                else {"INITIAL"}
            )
            for role, epochs in role_epochs.items()
        ):
            findings.add("PROCESS_IDENTITY_MISMATCH")
        if len(by_instance) != len(roles) + len(cold_roles):
            findings.add("PROCESS_IDENTITY_MISMATCH")
        expected_instance_order = [
            (role, epoch)
            for role in roles
            for epoch in (
                ("INITIAL", "COLD_RELAUNCH")
                if role in cold_roles
                else ("INITIAL",)
            )
        ]
        if instance_order != expected_instance_order:
            findings.add("PROCESS_IDENTITY_MISMATCH")

    coverage = value.get("coverage")
    coverage_states: dict[tuple[str, str], str] = {}
    observed_instance_ids: set[str] = set()
    pre_cold_observed_instance_ids: set[str] = set()
    cold_observed_instance_ids: set[str] = set()
    if not isinstance(coverage, list):
        findings.add("COVERAGE_MISMATCH")
    else:
        seen: set[tuple[str, str]] = set()
        coverage_order: list[tuple[str, str]] = []
        running_roles: set[str] = set()
        for row in coverage:
            if not isinstance(row, dict) or set(row) != COVERAGE_KEYS:
                findings.add("COVERAGE_MISMATCH")
                continue
            row_role = row.get("role")
            row_phase = row.get("phase")
            if not isinstance(row_role, str) or not isinstance(row_phase, str):
                findings.add("COVERAGE_MISMATCH")
                continue
            pair = (row_role, row_phase)
            coverage_order.append(pair)
            if pair in seen:
                findings.add("COVERAGE_MISMATCH")
            seen.add(pair)
            coverage_states[pair] = row.get("state")
            if row.get("state") == "RUNNING_OBSERVED":
                running_roles.add(row_role)
            process_ids = row.get("processInstanceIds")
            expected_epoch = (
                "COLD_RELAUNCH"
                if pair[1] == "COLD_RELAUNCH" and pair[0] in cold_roles
                else "INITIAL"
            )
            if (
                pair[0] not in roles
                or pair[1] not in PHASES
                or row.get("state")
                not in ("RUNNING_OBSERVED", "PROVED_NOT_RUNNING")
                or row.get("observerComplete") is not True
                or row.get("startBoundaryProved") is not True
                or row.get("endBoundaryProved") is not True
                or type(row.get("eventLossCount")) is not int
                or row.get("eventLossCount") != 0
                or not isinstance(process_ids, list)
                or any(
                    not isinstance(process_id, str) or not process_id
                    for process_id in process_ids
                )
                or process_ids != sorted(set(process_ids))
                or (
                    row.get("state") == "RUNNING_OBSERVED"
                    and (
                        not process_ids
                        or any(
                            process_id not in by_instance
                            or by_instance[process_id].get("role") != pair[0]
                            or by_instance[process_id].get("launchEpoch") != expected_epoch
                            for process_id in process_ids
                        )
                    )
                )
                or (
                    row.get("state") == "PROVED_NOT_RUNNING"
                    and process_ids != []
                )
            ):
                findings.add("COVERAGE_MISMATCH")
            elif row.get("state") == "RUNNING_OBSERVED":
                observed_instance_ids.update(process_ids)
                if row_phase == "COLD_RELAUNCH":
                    cold_observed_instance_ids.update(process_ids)
                else:
                    pre_cold_observed_instance_ids.update(process_ids)
        expected = {(role, phase) for role in roles for phase in PHASES}
        expected_order = [(role, phase) for role in roles for phase in PHASES]
        if seen != expected or coverage_order != expected_order:
            findings.add("COVERAGE_MISMATCH")
        if running_roles != set(roles) or any(
            coverage_states.get((role, "COLD_RELAUNCH")) != "RUNNING_OBSERVED"
            for role in roles
        ):
            findings.add("COVERAGE_MISMATCH")
        if observed_instance_ids != set(by_instance) or any(
            (
                instance.get("launchEpoch") == "INITIAL"
                and instance_id not in pre_cold_observed_instance_ids
            )
            or (
                instance.get("launchEpoch") == "COLD_RELAUNCH"
                and instance_id not in cold_observed_instance_ids
            )
            for instance_id, instance in by_instance.items()
        ):
            findings.add("PROCESS_IDENTITY_MISMATCH")

    events = value.get("events")
    if not isinstance(events, list):
        findings.add("EVENT_SCHEMA_MISMATCH")
        events = []
    else:
        writes: dict[str, dict[str, Any]] = {}
        acks: dict[str, dict[str, Any]] = {}
        read_ids: set[str] = set()
        last_phase_index = -1
        for index, event in enumerate(events):
            if not isinstance(event, dict) or set(event) != EVENT_KEYS:
                findings.add("EVENT_SCHEMA_MISMATCH")
                continue
            phase = event.get("phase")
            if phase in PHASES:
                phase_index = PHASES.index(phase)
                if phase_index < last_phase_index:
                    findings.add("EVENT_PHASE_ORDER_MISMATCH")
                last_phase_index = max(last_phase_index, phase_index)
            if (
                event.get("operation") == "READ"
                and isinstance(event.get("result"), str)
                and event.get("result") in {"DENIED", "ERROR"}
            ):
                findings.add("READ_OUTCOME_INCOMPLETE")
            event_schema_invalid = (
                type(event.get("sequence")) is not int
                or event.get("sequence") != index
                or event.get("role") not in roles
                or event.get("phase") not in PHASES
                or not isinstance(event.get("processInstanceId"), str)
                or event.get("processInstanceId") not in by_instance
                or not isinstance(event.get("operation"), str)
                or event.get("operation") not in PROPERTY_OPERATIONS
                or not isinstance(event.get("result"), str)
                or event.get("result") not in PROPERTY_RESULTS
                or not all(
                    isinstance(event.get(key), str) and event[key]
                    for key in ("requestId", "key", "context", "sourceId")
                )
                or type(event.get("returnedDefault")) is not bool
                or type(event.get("errno")) is not int
                or event["errno"] < 0
                or type(event.get("valueBytes")) is not int
                or event["valueBytes"] < 0
                or not _is_sha256(event.get("valueSha256"))
                or (
                    event.get("result") != "SUCCESS"
                    and (
                        event.get("valueBytes") != 0
                        or event.get("valueSha256")
                        != hashlib.sha256(b"").hexdigest()
                    )
                )
                or (event.get("result") == "SUCCESS" and event.get("errno") != 0)
                or (event.get("result") != "SUCCESS" and event.get("errno") == 0)
                or (
                    event.get("operation") != "READ"
                    and event.get("returnedDefault") is not False
                )
            )
            if event_schema_invalid:
                findings.add("EVENT_SCHEMA_MISMATCH")
                continue
            if coverage_states.get((event.get("role"), event.get("phase"))) == "PROVED_NOT_RUNNING":
                findings.add("COVERAGE_MISMATCH")
            coverage_ids = next(
                (
                    row.get("processInstanceIds", [])
                    for row in coverage
                    if isinstance(row, dict)
                    and row.get("role") == event.get("role")
                    and row.get("phase") == event.get("phase")
                ),
                [],
            ) if isinstance(coverage, list) else []
            if (
                not isinstance(coverage_ids, list)
                or event.get("processInstanceId") not in coverage_ids
            ):
                findings.add("PROCESS_IDENTITY_MISMATCH")
            request_id = event.get("requestId")
            if event.get("operation") == "READ":
                if request_id in read_ids or request_id in writes or request_id in acks:
                    findings.add("WRITE_ACK_MISMATCH")
                read_ids.add(request_id)
            elif event.get("operation") == "WRITE":
                if request_id in writes or request_id in acks or request_id in read_ids:
                    findings.add("WRITE_ACK_MISMATCH")
                writes[request_id] = event
            elif event.get("operation") == "ACK":
                if request_id in acks or request_id in read_ids:
                    findings.add("WRITE_ACK_MISMATCH")
                acks[request_id] = event
        if set(writes) != set(acks):
            findings.add("WRITE_ACK_MISMATCH")
        for request_id in set(writes) & set(acks):
            write = writes[request_id]
            ack = acks[request_id]
            if (
                ack.get("sequence", -1) <= write.get("sequence", -1)
                or any(
                    ack.get(key) != write.get(key)
                    for key in (
                        "key",
                        "context",
                        "sourceId",
                        "phase",
                        "role",
                        "processInstanceId",
                        "valueBytes",
                        "valueSha256",
                    )
                )
            ):
                findings.add("WRITE_ACK_MISMATCH")

    trace = value.get("trace")
    if not isinstance(trace, dict) or set(trace) != TRACE_KEYS:
        findings.add("OBSERVER_INCOMPLETE")
    else:
        expected_first = 0 if events else -1
        expected_last = len(events) - 1
        fabricated_defaults = sum(
            isinstance(event, dict) and event.get("returnedDefault") is True
            for event in events
        )
        if (
            trace.get("observerOutcome") != "VALID_COMPLETE"
            or trace.get("closed") is not True
            or trace.get("mixedRun") is not False
            or trace.get("truncated") is not False
            or type(trace.get("fabricatedDefaultEvents")) is not int
            or trace.get("fabricatedDefaultEvents") != fabricated_defaults
            or fabricated_defaults != 0
            or any(
                type(trace.get(key)) is not int or trace.get(key) != 0
                for key in (
                    "droppedEvents",
                    "duplicateEvents",
                    "malformedEvents",
                    "unknownEvents",
                )
            )
            or type(trace.get("declaredEventCount")) is not int
            or trace.get("declaredEventCount") != len(events)
            or type(trace.get("firstSequence")) is not int
            or trace.get("firstSequence") != expected_first
            or type(trace.get("lastSequence")) is not int
            or trace.get("lastSequence") != expected_last
            or type(trace.get("eventCountCap")) is not int
            or trace["eventCountCap"] <= 0
            or len(events) > trace["eventCountCap"]
            or type(trace.get("traceByteCap")) is not int
            or trace["traceByteCap"] <= 0
            or type(trace.get("traceBytes")) is not int
            or trace.get("traceBytes") != len(_event_bytes(events))
            or trace["traceBytes"] > trace["traceByteCap"]
        ):
            findings.add("OBSERVER_INCOMPLETE")
    if isinstance(bindings, dict) and bindings.get("traceSha256") != _event_digest(events):
        findings.add("TRACE_DIGEST_MISMATCH")

    if (
        value.get("deviceSafetyState") != "RESIDENT_HEALTHY"
        or value.get("experimentProof") != "PROVED"
        or value.get("workflowState") != "TERMINAL"
    ):
        findings.add("SAFETY_PROOF_MISMATCH")

    effect = value.get("macProvisioningEffect")
    if not isinstance(effect, dict) or set(effect) != MAC_EFFECT_KEYS:
        findings.add("MAC_EFFECT_MISMATCH")
    else:
        boolean_keys = (
            "sameBoot",
            "sameRun",
            "sourceIdentityBound",
            "driverIdentityBound",
            "debugfsIdentityBound",
            "readComplete",
        )
        if (
            any(type(effect.get(key)) is not bool for key in boolean_keys)
            or effect.get("cnssUtilsMacState") not in MAC_STATES
            or effect.get("wlanOutcome") not in WLAN_OUTCOMES
        ):
            findings.add("MAC_EFFECT_MISMATCH")
        complete = all(
            effect.get(key) is True
            for key in (
                "sameBoot",
                "sameRun",
                "sourceIdentityBound",
                "driverIdentityBound",
                "debugfsIdentityBound",
                "readComplete",
            )
        )
        expected_decision = classify_mac_effect(
            effect.get("cnssUtilsMacState"), effect.get("wlanOutcome"), complete
        )
        if effect.get("decision") != expected_decision:
            findings.add("MAC_EFFECT_MISMATCH")
        if effect.get("readComplete") is not True and effect.get("cnssUtilsMacState") != "UNREADABLE_OR_MALFORMED":
            findings.add("MAC_EFFECT_MISMATCH")

    return findings


def _validate_seed_entries(value: dict[str, Any]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    findings: set[str] = set()
    entries = value.get("seedEntries")
    by_id: dict[str, dict[str, Any]] = {}
    key_contexts: set[tuple[str, str]] = set()
    if not isinstance(entries, list):
        return {"SEED_SCHEMA_MISMATCH"}, by_id
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != SEED_KEYS:
            findings.add("SEED_SCHEMA_MISMATCH")
            continue
        seed_id = entry.get("seedId")
        pair = (entry.get("key"), entry.get("context"))
        if (
            not isinstance(seed_id, str)
            or not seed_id
            or seed_id in {".", ".."}
            or "/" in seed_id
            or seed_id in by_id
            or not all(isinstance(item, str) and item for item in pair)
            or pair in key_contexts
            or not _is_sha256(entry.get("valueSha256"))
            or not _is_sha256(entry.get("sourceSha256"))
            or type(entry.get("valueBytes")) is not int
            or entry["valueBytes"] < 0
            or type(entry.get("sourceBytes")) is not int
            or entry["sourceBytes"] <= 0
            or entry.get("sourceKind") != "REGULAR"
            or entry.get("sourceMode") not in ("0400", "0440", "0444")
            or type(entry.get("sourceNlink")) is not int
            or entry.get("sourceNlink") != 1
            or type(entry.get("sourceUid")) is not int
            or type(entry.get("sourceGid")) is not int
            or entry.get("sourceUid") < 0
            or entry.get("sourceGid") < 0
            or entry.get("sourceReadOnlyLifetime")
            != "BEFORE_FIRST_READER_THROUGH_FINAL_READER"
            or not isinstance(entry.get("sourcePath"), str)
            or not entry["sourcePath"].startswith("/")
            or ".." in Path(entry["sourcePath"]).parts
            or entry["sourcePath"] != str(Path(entry["sourcePath"]))
            or Path(entry["sourcePath"]).name != seed_id
            or not isinstance(entry.get("readers"), list)
            or not entry["readers"]
            or any(
                not isinstance(reader, str) or not reader
                for reader in entry["readers"]
            )
            or entry["readers"] != sorted(set(entry["readers"]))
        ):
            findings.add("SEED_SCHEMA_MISMATCH")
            continue
        by_id[seed_id] = entry
        key_contexts.add(pair)
    if list(by_id) != sorted(by_id):
        findings.add("SEED_SCHEMA_MISMATCH")
    fs = value.get("seedFilesystem")
    if not isinstance(fs, dict) or set(fs) != SEED_FS_KEYS:
        findings.add("SEED_SCHEMA_MISMATCH")
    return findings, by_id


def validate_property_absent_result(
    value: Any, qualified_expectation: Any = None
) -> list[str]:
    findings = _validate_common_result(value, qualified_expectation)
    if not isinstance(value, dict):
        return sorted(findings)
    if value.get("terminal") != "PROPERTY_ABSENT_PROVED":
        findings.add("PROPERTY_TERMINAL_MISMATCH")
    if value.get("seedEntries") != []:
        findings.add("SEED_SCHEMA_MISMATCH")
    fs = value.get("seedFilesystem")
    if (
        not isinstance(fs, dict)
        or set(fs) != SEED_FS_KEYS
        or fs.get("state") != "ABSENT"
        or fs.get("rootPath") is not None
        or fs.get("rootReadOnly") is not None
        or fs.get("memberNames") != []
        or fs.get("memberSetSha256") != _member_digest([])
        or fs.get("unexpectedMembers") != []
        or any(
            type(fs.get(key)) is not int or fs.get(key) != 0
            for key in ("symlinkCount", "hardlinkAliasCount", "specialFileCount")
        )
        or fs.get("generationMatches") is not True
        or fs.get("digestStable") is not True
    ):
        findings.add("SEED_SCHEMA_MISMATCH")
    for event in value.get("events", []) if isinstance(value.get("events"), list) else []:
        if (
            isinstance(event, dict)
            and event.get("operation") == "READ"
            and event.get("result") == "SUCCESS"
        ):
            findings.add("SUCCESSFUL_READ_PRESENT")
    return sorted(findings)


def validate_property_finite_seed_result(
    value: Any, qualified_expectation: Any = None
) -> list[str]:
    findings = _validate_common_result(value, qualified_expectation)
    if not isinstance(value, dict):
        return sorted(findings)
    if value.get("terminal") != "PROPERTY_FINITE_SEED_PROVED":
        findings.add("PROPERTY_TERMINAL_MISMATCH")
    seed_findings, by_id = _validate_seed_entries(value)
    findings.update(seed_findings)
    if not by_id:
        findings.add("SEED_SCHEMA_MISMATCH")
    fs = value.get("seedFilesystem")
    entries = value.get("seedEntries") if isinstance(value.get("seedEntries"), list) else []
    roles = (
        {
            role
            for role in value.get("expectedRoles", [])
            if isinstance(role, str)
        }
        if isinstance(value.get("expectedRoles"), list)
        else set()
    )
    names = sorted(
        entry["sourcePath"].rsplit("/", 1)[-1]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("sourcePath"), str)
    )
    if (
        not isinstance(fs, dict)
        or set(fs) != SEED_FS_KEYS
        or fs.get("state") != "PRESENT_EXACT"
        or not isinstance(fs.get("rootPath"), str)
        or not fs["rootPath"].startswith("/")
        or ".." in Path(fs["rootPath"]).parts
        or fs["rootPath"] != str(Path(fs["rootPath"]))
        or fs.get("rootReadOnly") is not True
        or fs.get("memberNames") != names
        or len(names) != len(set(names))
        or fs.get("memberSetSha256") != _member_digest(names)
        or fs.get("unexpectedMembers") != []
        or any(
            type(fs.get(key)) is not int or fs.get(key) != 0
            for key in ("symlinkCount", "hardlinkAliasCount", "specialFileCount")
        )
        or fs.get("generationMatches") is not True
        or fs.get("digestStable") is not True
    ):
        findings.add("SEED_SCHEMA_MISMATCH")
    elif any(
        not isinstance(entry.get("readers"), list)
        or any(not isinstance(reader, str) for reader in entry.get("readers", []))
        or set(entry.get("readers", [])) - roles
        or not isinstance(entry.get("sourcePath"), str)
        or str(Path(entry.get("sourcePath", "")).parent) != fs.get("rootPath")
        for entry in entries
        if isinstance(entry, dict)
    ):
        findings.add("SEED_SCHEMA_MISMATCH")

    used: set[str] = set()
    observed_readers: dict[str, set[str]] = {}
    for event in value.get("events", []) if isinstance(value.get("events"), list) else []:
        if not isinstance(event, dict) or event.get("operation") != "READ" or event.get("result") != "SUCCESS":
            continue
        source_id = event.get("sourceId")
        entry = by_id.get(source_id) if isinstance(source_id, str) else None
        if (
            entry is None
            or event.get("key") != entry.get("key")
            or event.get("context") != entry.get("context")
            or event.get("valueBytes") != entry.get("valueBytes")
            or event.get("valueSha256") != entry.get("valueSha256")
            or event.get("role") not in entry.get("readers", [])
            or event.get("returnedDefault") is not False
        ):
            findings.add("SEED_READ_MAPPING_MISMATCH")
        else:
            used.add(entry["seedId"])
            observed_readers.setdefault(entry["seedId"], set()).add(event["role"])
    if used != set(by_id):
        findings.add("SEED_READ_MAPPING_MISMATCH")
    if any(
        set(entry.get("readers", [])) != observed_readers.get(seed_id, set())
        for seed_id, entry in by_id.items()
    ):
        findings.add("SEED_READ_MAPPING_MISMATCH")
    return sorted(findings)


def canonical_text() -> str:
    schema = build_schema()
    findings = validate_schema(schema)
    if findings:
        raise ValueError(f"generated WP2-4 schema rejected: {findings}")
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", type=Path, metavar="PATH")
    group.add_argument("--write", type=Path, nargs="?", const=DEFAULT_OUTPUT, metavar="PATH")
    args = parser.parse_args()
    rendered = canonical_text()
    if args.check is not None:
        if args.check.read_text() != rendered:
            raise SystemExit(f"schema drift: {args.check}")
        return 0
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered)
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
