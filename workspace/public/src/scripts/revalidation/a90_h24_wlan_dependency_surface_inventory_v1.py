#!/usr/bin/env python3
"""Generate the host-only WP2-3 A90 WLAN dependency-surface inventory.

The inventory separates exact selected-source launch facts, historical-only
observations, identity conflicts, and unproved dependency slots.  It never
reads a device or private input, does not bind current H24 opaque ELF bytes,
retires no H0D gate, and grants no execution authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BASE = "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
DEFAULT_OUTPUT = (
    ROOT
    / BASE
    / "inventory/a90-h24-wlan-dependency-surface-inventory-v1.json"
)

PARENT_REL = f"{BASE}/inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
DESIGN_REL = f"{BASE}/design/a90-h24-wlan-one-factor-ablation-design-v1.json"
POLICY_REL = f"{BASE}/policy/a90-h24-wlan-forbidden-surface-policy-v1.json"
MANIFEST_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h24/manifest.toml"
)
HELPER_REL = "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
MAIN_REL = "workspace/public/src/native-init/v724/90_main.inc.c"
V241_REL = "docs/archive/legacy/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md"
V242_REL = "docs/archive/legacy/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md"
V249_REL = "docs/archive/legacy/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md"
V1692_REL = "docs/archive/legacy/reports/NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md"
V2033_REL = "docs/archive/legacy/reports/NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md"
V2117_REL = "docs/archive/legacy/reports/NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md"

PINNED_INPUTS = {
    PARENT_REL: (42264, "d4ac9b47de9674995b891e888937969cb34b74d27b1c59e35cb7172fbd3370cb"),
    DESIGN_REL: (105900, "0eddec9ba9d637590c82499709179bd6b56a79d646d7967d3049a0bf36136b85"),
    POLICY_REL: (39695, "af4b25c766746a5297c4b7f7f48bec6dba429dac9775e738e758f96ccbae1b58"),
    MANIFEST_REL: (7801, "40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f"),
    HELPER_REL: (3253399, "4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2"),
    MAIN_REL: (277766, "2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f"),
    V241_REL: (5118, "0212b18b2f76a88247300a55f9c670b18de15f69a488c62f1167304b3de1ebc2"),
    V242_REL: (3867, "b6a61a6b259b4dd29606bc29ed3f788c7479b0289a32f8b6e4252e2422aa2821"),
    V249_REL: (4050, "07dac305ae652c451135606d62f69479af756c3958e5e5798574dc6c426f71f3"),
    V1692_REL: (3629, "345428d2284919776b67a3a88c40f9a4986002956a2f9d5488efe2c48dd033e3"),
    V2033_REL: (4757, "caad3e832038f28de2febd4b2dd0742f093ab0b035d4b1d6db59032e595e20d2"),
    V2117_REL: (4291, "a3f7b5b81c9cf9861c1e7a039d6f0f4102726c71cca8585e1228194ab6c59914"),
}

SCHEMA = "a90-h24-wlan-dependency-surface-inventory-v1"
GATE_IDS = tuple(f"H0D{index:02d}" for index in range(1, 11))
SURFACE_GATES = {
    "artifact": ["H0D01"],
    "dynamicDispatch": ["H0D02"],
    "configuration": ["H0D03"],
    "property": ["H0D04"],
    "binder": ["H0D05"],
    "qrtrQmi": ["H0D06"],
    "deviceKernel": ["H0D07"],
    "firmwareRfs": ["H0D08"],
    "writableOutput": ["H0D09"],
    "sdFreeProvenance": ["H0D10"],
}
SURFACE_KEYS = tuple(SURFACE_GATES)
FACT_STATES = {
    "SOURCE_SELECTED_H24_PATH",
    "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
    "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED",
}
OPAQUE_ROLES = (
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
)
AUXILIARY_ROLES = ("property-service-shim", "modem-holder", "wifi-helper")
EXPECTED_ROLE_ORDER = OPAQUE_ROLES + AUXILIARY_ROLES
AUTHORITY_KEYS = {
    "candidateEligible",
    "d0Authorized",
    "d1Authorized",
    "deviceContact",
    "deviceInstallAuthorized",
    "f1Authorized",
    "handoffAuthorized",
    "liveExecutionAuthorized",
    "privateInputRead",
    "propertyProvisionAuthorized",
    "tier",
    "ufsMutationAuthorized",
}


def _lexical_regular(rel: str) -> Path:
    path = ROOT / rel
    cursor = ROOT
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"WP2-3 input contains a symlink: {rel}")
    if not path.is_file():
        raise ValueError(f"WP2-3 input is not a regular file: {rel}")
    return path


def _read_pinned(rel: str) -> bytes:
    raw = _lexical_regular(rel).read_bytes()
    expected_size, expected_sha256 = PINNED_INPUTS[rel]
    if len(raw) != expected_size:
        raise ValueError(f"WP2-3 input size drift: {rel}")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"WP2-3 input digest drift: {rel}")
    return raw


def _load_inputs() -> dict[str, Any]:
    raw = {rel: _read_pinned(rel) for rel in PINNED_INPUTS}
    return {
        "raw": raw,
        "parent": json.loads(raw[PARENT_REL]),
        "design": json.loads(raw[DESIGN_REL]),
        "policy": json.loads(raw[POLICY_REL]),
        "manifest": raw[MANIFEST_REL].decode(),
        "helper": raw[HELPER_REL].decode(),
        "main": raw[MAIN_REL].decode(),
        "reports": {
            rel: raw[rel].decode()
            for rel in (V241_REL, V242_REL, V249_REL, V1692_REL, V2033_REL, V2117_REL)
        },
    }


def _pin(rel: str) -> dict[str, Any]:
    size, sha256 = PINNED_INPUTS[rel]
    return {"path": rel, "bytes": size, "sha256": sha256}


def _require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        if token not in text:
            raise ValueError(f"WP2-3 {label} evidence drift: {token}")


def _require_source_contract(inputs: dict[str, Any]) -> None:
    parent = inputs["parent"]
    design = inputs["design"]
    policy = inputs["policy"]
    if parent.get("schema") != "a90-h24-wlan-capsule-dependency-inventory-v1":
        raise ValueError("WP2-3 parent inventory schema drift")
    if design.get("schema") != "a90-h24-wlan-one-factor-ablation-design-v1":
        raise ValueError("WP2-3 design schema drift")
    if policy.get("schema") != "a90-h24-wlan-forbidden-surface-policy-v1":
        raise ValueError("WP2-3 policy schema drift")
    if parent.get("counts", {}).get("compositeInstances") != 13:
        raise ValueError("WP2-3 parent composite count drift")
    if parent.get("counts", {}).get("uniqueCompositeRoles") != 11:
        raise ValueError("WP2-3 parent role count drift")
    if policy.get("status", {}).get("dependencyGatesRetired") != []:
        raise ValueError("WP2-3 parent policy retired a gate")
    removed_roles = [unit.get("removedRole") for unit in design.get("ablationUnits", [])]
    if set(removed_roles) != set(OPAQUE_ROLES[:-1] + ("cnss_daemon",) + AUXILIARY_ROLES[:2]):
        raise ValueError("WP2-3 ablation-role coverage drift")

    _require_tokens(
        inputs["manifest"],
        (
            '"-DA90_WIFI_PERSISTENT_HANDOFF_V1=1"',
            '"-DA90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER=1"',
            '"-DA90_WIFI_TEST_BOOT_FIRMWARE_MOUNTS=1"',
            "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
        ),
        "manifest",
    )
    _require_tokens(
        inputs["helper"],
        (
            '"/dev/socket/property_service"',
            '"/dev/subsys_modem"',
            '"/dev/vndbinder"',
            "AF_QIPCRTR",
        ),
        "helper",
    )
    _require_tokens(
        inputs["main"],
        (
            '"--property-root"',
            '"--linkerconfig-source"',
            '"--apex-libraries-source"',
            '"--persistent-handoff"',
        ),
        "main",
    )

    reports = inputs["reports"]
    _require_tokens(
        reports[V241_REL],
        (
            "libqmi_cci.so => /vendor/lib64/libqmi_cci.so",
            "libqmi_common_so.so => /vendor/lib64/libqmi_common_so.so",
            "libcld80211.so",
        ),
        "V241",
    )
    _require_tokens(
        reports[V242_REL],
        (
            "`cnss-daemon` | `/system/vendor/bin/cnss-daemon` | `-n -l`",
            "`cnss_diag` | `/system/vendor/bin/cnss_diag` | `-q -f -t HELIUM`",
            "`/dev/diag`",
            "`/dev/qrtr`",
        ),
        "V242",
    )
    _require_tokens(
        reports[V249_REL],
        (
            "property service | missing",
            "property area | missing",
            "was not running after v249",
        ),
        "V249",
    )
    _require_tokens(
        reports[V1692_REL],
        (
            "`95112` bytes",
            "bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc",
            "persist.vendor.cnss-daemon.debug_level",
            "persist.vendor.cnss-daemon.kmsg_logging",
            "wlfw_start",
        ),
        "V1692",
    )
    _require_tokens(
        reports[V2033_REL],
        (
            "readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
            "readonly/vendor/firmware/wlanmdsp.mbn",
            "total-bytes = 4251884",
            "readwrite/mcfg.tmp",
        ),
        "V2033",
    )
    _require_tokens(
        reports[V2117_REL],
        (
            "| rmt_storage | rmt_storage-android-runtime | 9999:1000 | 1000,3010 |",
            "| tftp_server | tftp_server-android-runtime | 2903:2903 | 1000,2903,2904,3010 |",
            "sda29_write': 0",
        ),
        "V2117",
    )


def _fact(
    fact_id: str,
    state: str,
    value: Any,
    sources: list[str],
    *,
    h24_applicability: str = "SOURCE_SELECTED_PATH_ONLY",
) -> dict[str, Any]:
    if state not in FACT_STATES:
        raise ValueError(f"unknown WP2-3 fact state: {state}")
    return {
        "factId": fact_id,
        "state": state,
        "h24Applicability": h24_applicability,
        "value": value,
        "sources": sources,
    }


def _surface(surface: str, facts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "completion": f"UNPROVED_COMPLETE_{surface.upper()}",
        "gateIds": list(SURFACE_GATES[surface]),
        "relevance": "UNKNOWN_UNTIL_PROVED_PRESENT_OR_ABSENT",
        "facts": facts or [],
        "retirementCreditGranted": False,
    }


def _selected_components(parent: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for component in parent["components"]:
        grouped.setdefault(component["role"], []).append(component)
    if set(grouped) != set(EXPECTED_ROLE_ORDER):
        raise ValueError("WP2-3 selected role set drift")
    return grouped


def _design_gate_map(design: dict[str, Any]) -> dict[str, list[str]]:
    result = {
        unit["removedRole"]: list(unit["roleSpecificRelevantGateIds"])
        for unit in design["ablationUnits"]
    }
    result["wifi-helper"] = list(GATE_IDS)
    if set(result) != set(EXPECTED_ROLE_ORDER):
        raise ValueError("WP2-3 design gate projection role drift")
    return result


def _specific_facts(role: str) -> dict[str, list[dict[str, Any]]]:
    facts = {surface: [] for surface in SURFACE_KEYS}
    if role in {"servicemanager", "hwservicemanager", "vndservicemanager"}:
        facts["binder"].append(
            _fact(
                "source-selected-binder-manager-role",
                "SOURCE_SELECTED_H24_PATH",
                {"role": role, "endpointClass": "NATIVE_GLOBAL_REJECTED_BY_WP2_2"},
                [f"{PARENT_REL}#components", POLICY_REL],
            )
        )
    if role in {"pm_proxy_helper", "per_mgr"}:
        facts["binder"].append(
            _fact(
                "source-selected-peripheral-manager-provider-role",
                "SOURCE_SELECTED_H24_PATH",
                {"role": role, "transactionSet": None},
                [f"{PARENT_REL}#components"],
            )
        )
    if role in {"qrtr_ns", "pd_mapper", "rmt_storage", "tftp_server"}:
        facts["qrtrQmi"].append(
            _fact(
                "source-selected-qrtr-pd-rfs-plane-membership",
                "SOURCE_SELECTED_H24_PATH",
                {"role": role, "causalMessages": None},
                [f"{PARENT_REL}#components"],
            )
        )
    if role == "cnss_diag":
        facts["deviceKernel"].append(
            _fact(
                "historical-diag-device-gap",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {"path": "/dev/diag", "availability": "historically-missing"},
                [f"{V242_REL}:64"],
                h24_applicability="UNPROVED",
            )
        )
    if role == "cnss_daemon":
        facts["artifact"].append(
            _fact(
                "historical-cnss-daemon-artifact",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {
                    "bytes": 95112,
                    "sha256": "bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc",
                },
                [f"{V1692_REL}:25"],
                h24_applicability="UNPROVED_NOT_CURRENT_H24_BINDING",
            )
        )
        facts["dynamicDispatch"].append(
            _fact(
                "historical-cnss-daemon-linker-resolution",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {
                    "libraries": [
                        "libcutils.so",
                        "libnl.so",
                        "libc++.so",
                        "libqmi_cci.so",
                        "libqmi_common_so.so",
                        "libcld80211.so",
                    ]
                },
                [f"{V241_REL}:106-148"],
                h24_applicability="UNPROVED_INCOMPLETE_RECURSIVE_CLOSURE",
            )
        )
        facts["property"].append(
            _fact(
                "historical-cnss-daemon-property-reads",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {
                    "keys": [
                        "persist.vendor.cnss-daemon.debug_level",
                        "persist.vendor.cnss-daemon.kmsg_logging",
                    ]
                },
                [f"{V1692_REL}:37-38"],
                h24_applicability="UNPROVED_CURRENT_H24_VALUES_AND_NECESSITY",
            )
        )
        facts["qrtrQmi"].append(
            _fact(
                "historical-cnss-daemon-wlfw-control-flow",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {"entry": "wlfw_start", "qmiMessages": None},
                [f"{V1692_REL}:28-31"],
                h24_applicability="UNPROVED_RUNTIME_MESSAGE_SET",
            )
        )
    if role == "tftp_server":
        facts["firmwareRfs"].append(
            _fact(
                "historical-wlanmdsp-rfs-paths",
                "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                {
                    "paths": [
                        "readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
                        "readonly/vendor/firmware/wlanmdsp.mbn",
                        "readwrite/mcfg.tmp",
                    ],
                    "historicalCompletedBytes": 4251884,
                },
                [f"{V2033_REL}:17-20"],
                h24_applicability="UNPROVED_CURRENT_H24_REQUEST_AND_TRANSFER_SET",
            )
        )
    if role == "property-service-shim":
        facts["property"].append(
            _fact(
                "source-selected-property-ack-shim",
                "SOURCE_SELECTED_H24_PATH",
                {
                    "path": "/dev/socket/property_service",
                    "protocol": "SETPROP_OR_SETPROP2_BOUNDED_ACK",
                    "provesReadSeed": False,
                },
                [f"{PARENT_REL}#property-service-shim"],
            )
        )
        facts["deviceKernel"].append(copy.deepcopy(facts["property"][-1]))
    if role == "modem-holder":
        facts["deviceKernel"].append(
            _fact(
                "source-selected-modem-holder-device",
                "SOURCE_SELECTED_H24_PATH",
                {"path": "/dev/subsys_modem", "access": "open-and-hold"},
                [f"{PARENT_REL}#modem-holder"],
            )
        )
    if role == "wifi-helper":
        facts["configuration"].append(
            _fact(
                "source-selected-helper-compatibility-inputs",
                "SOURCE_SELECTED_H24_PATH",
                {
                    "propertyRoot": "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
                    "linkerConfig": "/cache/bin/a90_real_ld.config.txt",
                    "apexLibrariesConfig": "/cache/bin/a90_real_apex.libraries.config.txt",
                    "vendorBlock": "/dev/block/sda29",
                },
                [f"{PARENT_REL}#wifi-helper"],
            )
        )
        facts["sdFreeProvenance"].append(
            _fact(
                "source-selected-private-sd-property-root",
                "SOURCE_SELECTED_H24_PATH",
                {
                    "path": "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
                    "successorAdmissible": False,
                },
                [MANIFEST_REL, POLICY_REL],
            )
        )
    return facts


def _identity_contract(role: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    selected = copy.deepcopy(components[0]["identity"])
    conflicts: list[dict[str, Any]] = []
    if role == "rmt_storage":
        conflicts.append(
            _fact(
                "historical-rmt-storage-android-identity",
                "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED",
                {"uid": 9999, "gid": 1000, "groups": [1000, 3010], "caps": [10, 36]},
                [f"{V2117_REL}:29"],
                h24_applicability="CONFLICTS_WITH_SELECTED_ROOT_LAUNCH",
            )
        )
    if role == "tftp_server":
        conflicts.append(
            _fact(
                "historical-tftp-server-android-identity",
                "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED",
                {"uid": 2903, "gid": 2903, "groups": [1000, 2903, 2904, 3010], "caps": [10, 36]},
                [f"{V2117_REL}:30"],
                h24_applicability="CONFLICTS_WITH_SELECTED_ROOT_LAUNCH",
            )
        )
    return {
        "currentSelectedSourceIdentity": selected,
        "currentRuntimeAppliedIdentityProved": False,
        "optionCExactIdentityEnvelopeProved": False,
        "historicalConflicts": conflicts,
    }


def _role_record(
    role: str,
    components: list[dict[str, Any]],
    design_gates: dict[str, list[str]],
) -> dict[str, Any]:
    first = components[0]
    kind = (
        "OPAQUE_EXTERNAL_ELF"
        if role in OPAQUE_ROLES
        else "IN_PROCESS_HELPER_BODY"
        if role in AUXILIARY_ROLES[:2]
        else "TOPOLOGY_OWNER_ELF"
    )
    facts = _specific_facts(role)
    surfaces = {
        surface: _surface(surface, facts[surface]) for surface in SURFACE_KEYS
    }
    surfaces["artifact"]["currentH24ExactBinding"] = {
        "path": first["executable"],
        "bytes": None,
        "sha256": None,
        "elfClass": None,
        "interpreter": None,
        "dtNeeded": None,
        "recursiveLibraryClosure": None,
    }
    selected_instances = [
        {
            "instanceId": component["instanceId"],
            "kind": component["kind"],
            "executable": component["executable"],
            "argv": copy.deepcopy(component.get("argv", [])),
            "launchPredicate": component["launchPredicate"],
            "ownershipPlane": component["ownershipPlane"],
            "identity": copy.deepcopy(component["identity"]),
            "environment": copy.deepcopy(component.get("environment")),
            "launchContract": copy.deepcopy(component.get("launchContract")),
            "lifetime": copy.deepcopy(component.get("lifetime")),
            "cleanup": copy.deepcopy(component.get("cleanup")),
            "sourceAnchors": copy.deepcopy(component.get("sourceAnchors", [])),
        }
        for component in components
    ]
    return {
        "role": role,
        "instanceIds": [component["instanceId"] for component in components],
        "artifactClass": kind,
        "sourceSelectedInstances": selected_instances,
        "identityContract": _identity_contract(role, components),
        "dependencySurfaces": surfaces,
        "designRoleSpecificGateIds": design_gates[role],
        "allGateSlotsPresent": list(GATE_IDS),
        "dependencyClosureComplete": False,
        "executionEligible": False,
    }


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
        "privateInputRead": False,
        "deviceContact": False,
    }


def _gate_coverage(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "gateId": gate_id,
            "rolesWithExplicitSlot": [record["role"] for record in records],
            "status": "UNPROVED",
            "retirementCreditGranted": False,
        }
        for gate_id in GATE_IDS
    ]


def _negative_corpus() -> list[dict[str, str]]:
    return [
        {"caseId": "N01", "mutation": "remove-role", "expected": "ROLE_SET_MISMATCH"},
        {"caseId": "N02", "mutation": "duplicate-role", "expected": "ROLE_SET_MISMATCH"},
        {"caseId": "N03", "mutation": "remove-surface-slot", "expected": "SURFACE_SET_MISMATCH"},
        {"caseId": "N04", "mutation": "promote-historical-artifact", "expected": "CURRENT_H24_ARTIFACT_BINDING_FORBIDDEN"},
        {"caseId": "N05", "mutation": "retire-gate", "expected": "GATE_RETIREMENT_FORBIDDEN"},
        {"caseId": "N06", "mutation": "enable-authority", "expected": "AUTHORITY_MISMATCH"},
        {"caseId": "N07", "mutation": "remove-identity-conflict", "expected": "IDENTITY_CONFLICT_MISSING"},
        {"caseId": "N08", "mutation": "claim-dependency-complete", "expected": "DEPENDENCY_COMPLETION_FORBIDDEN"},
        {"caseId": "N09", "mutation": "unknown-fact-state", "expected": "FACT_STATE_MISMATCH"},
        {"caseId": "N10", "mutation": "add-unknown-field", "expected": "TOP_LEVEL_SCHEMA_MISMATCH"},
    ]


def build_inventory() -> dict[str, Any]:
    inputs = _load_inputs()
    _require_source_contract(inputs)
    grouped = _selected_components(inputs["parent"])
    design_gates = _design_gate_map(inputs["design"])
    records = [
        _role_record(role, grouped[role], design_gates) for role in EXPECTED_ROLE_ORDER
    ]
    return {
        "schema": SCHEMA,
        "generatedDeterministically": True,
        "scope": {
            "target": "Samsung Galaxy A90 5G only",
            "workPackage": "WP2-3",
            "purpose": "exact requirement, known-fact, conflict, and unproved-slot inventory",
            "doesNotProve": [
                "current H24 opaque ELF bytes or recursive library closure",
                "complete config, property, Binder, QRTR/QMI, device, firmware/RFS, or output use",
                "individual role necessity",
                "SD-free bootstrap",
                "Option C feasibility",
            ],
        },
        "authority": _authority(),
        "sourcePins": [_pin(rel) for rel in PINNED_INPUTS],
        "status": {
            "wp2_3": "COMPLETE_H0_REQUIREMENT_AND_EVIDENCE_STATE_INVENTORY_ONLY",
            "dependencyClosure": "BLOCKED_UNPROVED_H0D01_THROUGH_H0D10",
            "currentH24ExactOpaqueElfBindings": 0,
            "dependencyGatesRetired": [],
            "futureByteDerivedConsumer": "ABSENT",
            "executionImplementation": "ABSENT",
            "optionC": "BLOCKED_RESEARCH_ONLY",
        },
        "counts": {
            "roleRecords": len(records),
            "sourceSelectedProcessInstances": sum(
                len(record["sourceSelectedInstances"]) for record in records
            ),
            "opaqueExternalElfRoles": len(OPAQUE_ROLES),
            "inProcessHelperBodies": 2,
            "topologyOwnerElfs": 1,
            "dependencySurfaceSlots": len(records) * len(SURFACE_KEYS),
            "identityConflictRoles": 2,
            "negativeCases": len(_negative_corpus()),
        },
        "evidenceStateVocabulary": sorted(FACT_STATES),
        "dependencySurfaceSchema": [
            {"surface": surface, "gateIds": list(SURFACE_GATES[surface])}
            for surface in SURFACE_KEYS
        ],
        "roles": records,
        "gateCoverage": _gate_coverage(records),
        "crossRoleConstraints": {
            "opaqueArtifacts": "Every opaque role requires a current exact regular-file and recursive ELF closure before execution; historical bytes provide zero retirement credit.",
            "identity": "The rmt_storage and tftp_server historical Android identities conflict with the selected H24 root launch and must be resolved, not averaged or chosen by preference.",
            "property": "The current private SD property root and write-ACK shim do not prove any read set or finite seed.",
            "privateSurfaces": "Private Binder/property shapes remain H0D05/H0D04 UNPROVED even if WP2-2 global-surface checks pass.",
            "sdFree": "No row may become executable until the public deterministic SD-free bootstrap superset is separately proved.",
        },
        "missingInputPlan": {
            "offline": [
                "current exact regular opaque ELF bytes and recursive library closure",
                "static executable, dlopen, config/default, and device/syscall read set",
                "public deterministic SD-free bootstrap superset",
            ],
            "runtime": [
                "property reads/writes and semantics",
                "Binder services and transactions",
                "QRTR/QMI services/messages",
                "device/kernel-object lifetime",
                "firmware/RFS requests and transfers",
                "bounded writable outputs and residue",
            ],
            "acquisitionAuthority": "ABSENT_THIS_H0_UNIT",
        },
        "negativeCorpus": _negative_corpus(),
        "nextSequencingConstraint": {
            "wp2_4": "MAY_DESIGN_PROPERTY_OBSERVATION_SCHEMA_FROM_UNPROVED_PROPERTY_SLOTS_H0_ONLY",
            "beforeWp2_5b": "A future byte-derived consumer must fill exact offline slots, preserve historical calibration, and remain blocked on runtime observations.",
            "beforeAnyExecution": "Retire H0D01 and relevant static halves, prove the H0D10 bootstrap superset, independently review instrumentation, bind recovery, and obtain separate authority.",
            "beforeOptionC": "Retire H0D01 through H0D10 by their declared evidence classes.",
        },
    }


TOP_LEVEL_KEYS = {
    "authority",
    "counts",
    "crossRoleConstraints",
    "dependencySurfaceSchema",
    "evidenceStateVocabulary",
    "gateCoverage",
    "generatedDeterministically",
    "missingInputPlan",
    "negativeCorpus",
    "nextSequencingConstraint",
    "roles",
    "schema",
    "scope",
    "sourcePins",
    "status",
}
ROLE_KEYS = {
    "allGateSlotsPresent",
    "artifactClass",
    "dependencyClosureComplete",
    "dependencySurfaces",
    "designRoleSpecificGateIds",
    "executionEligible",
    "identityContract",
    "instanceIds",
    "role",
    "sourceSelectedInstances",
}
SURFACE_RECORD_KEYS = {
    "completion",
    "facts",
    "gateIds",
    "relevance",
    "retirementCreditGranted",
}
ARTIFACT_RECORD_KEYS = SURFACE_RECORD_KEYS | {"currentH24ExactBinding"}
FACT_KEYS = {"factId", "h24Applicability", "sources", "state", "value"}
INSTANCE_KEYS = {
    "argv",
    "cleanup",
    "environment",
    "executable",
    "identity",
    "instanceId",
    "kind",
    "launchContract",
    "launchPredicate",
    "lifetime",
    "ownershipPlane",
    "sourceAnchors",
}
GATE_COVERAGE_KEYS = {
    "gateId",
    "retirementCreditGranted",
    "rolesWithExplicitSlot",
    "status",
}


def validate_inventory(value: Any) -> list[str]:
    findings: set[str] = set()
    if not isinstance(value, dict) or set(value) != TOP_LEVEL_KEYS:
        return ["TOP_LEVEL_SCHEMA_MISMATCH"]
    if value.get("schema") != SCHEMA:
        findings.add("TOP_LEVEL_SCHEMA_MISMATCH")
    if value.get("generatedDeterministically") is not True:
        findings.add("TOP_LEVEL_SCHEMA_MISMATCH")
    if value.get("sourcePins") != [_pin(rel) for rel in PINNED_INPUTS]:
        findings.add("SOURCE_PIN_MISMATCH")
    if value.get("evidenceStateVocabulary") != sorted(FACT_STATES):
        findings.add("FACT_STATE_MISMATCH")
    if value.get("dependencySurfaceSchema") != [
        {"surface": surface, "gateIds": list(SURFACE_GATES[surface])}
        for surface in SURFACE_KEYS
    ]:
        findings.add("SURFACE_SCHEMA_MISMATCH")
    if value.get("negativeCorpus") != _negative_corpus():
        findings.add("NEGATIVE_CORPUS_MISMATCH")
    authority = value.get("authority")
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_KEYS:
        findings.add("AUTHORITY_MISMATCH")
    elif authority.get("tier") != "H0" or any(
        flag is not False for key, flag in authority.items() if key != "tier"
    ):
        findings.add("AUTHORITY_MISMATCH")
    status = value.get("status", {})
    if status.get("dependencyGatesRetired") != []:
        findings.add("GATE_RETIREMENT_FORBIDDEN")
    if status.get("currentH24ExactOpaqueElfBindings") != 0:
        findings.add("CURRENT_H24_ARTIFACT_BINDING_FORBIDDEN")
    roles = value.get("roles")
    if not isinstance(roles, list) or [record.get("role") for record in roles if isinstance(record, dict)] != list(EXPECTED_ROLE_ORDER):
        findings.add("ROLE_SET_MISMATCH")
        return sorted(findings)
    for record in roles:
        if set(record) != ROLE_KEYS:
            findings.add("ROLE_SCHEMA_MISMATCH")
            continue
        if record.get("dependencyClosureComplete") is not False or record.get("executionEligible") is not False:
            findings.add("DEPENDENCY_COMPLETION_FORBIDDEN")
        if record.get("allGateSlotsPresent") != list(GATE_IDS):
            findings.add("GATE_SLOT_MISMATCH")
        instances = record.get("sourceSelectedInstances")
        if (
            not isinstance(instances, list)
            or not instances
            or [item.get("instanceId") for item in instances if isinstance(item, dict)]
            != record.get("instanceIds")
            or any(not isinstance(item, dict) or set(item) != INSTANCE_KEYS for item in instances)
        ):
            findings.add("INSTANCE_LAUNCH_SCHEMA_MISMATCH")
        surfaces = record.get("dependencySurfaces")
        if not isinstance(surfaces, dict) or set(surfaces) != set(SURFACE_KEYS):
            findings.add("SURFACE_SET_MISMATCH")
            continue
        for name, surface in surfaces.items():
            expected_keys = ARTIFACT_RECORD_KEYS if name == "artifact" else SURFACE_RECORD_KEYS
            if not isinstance(surface, dict) or set(surface) != expected_keys:
                findings.add("SURFACE_SCHEMA_MISMATCH")
                continue
            if surface.get("gateIds") != list(SURFACE_GATES[name]):
                findings.add("GATE_SLOT_MISMATCH")
            if surface.get("retirementCreditGranted") is not False:
                findings.add("GATE_RETIREMENT_FORBIDDEN")
            for fact in surface.get("facts", []):
                if not isinstance(fact, dict) or set(fact) != FACT_KEYS:
                    findings.add("FACT_SCHEMA_MISMATCH")
                elif fact.get("state") not in FACT_STATES:
                    findings.add("FACT_STATE_MISMATCH")
                else:
                    fact_id = fact.get("factId", "")
                    if fact_id.startswith("historical-") and fact.get("state") not in {
                        "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
                        "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED",
                    }:
                        findings.add("HISTORICAL_EVIDENCE_PROMOTION")
                    if fact_id.startswith("source-selected-") and fact.get("state") != "SOURCE_SELECTED_H24_PATH":
                        findings.add("FACT_STATE_MISMATCH")
                    if not fact.get("sources"):
                        findings.add("FACT_SCHEMA_MISMATCH")
        binding = surfaces["artifact"].get("currentH24ExactBinding", {})
        if binding.get("path") != instances[0].get("executable"):
            findings.add("CURRENT_H24_ARTIFACT_PATH_MISMATCH")
        if any(binding.get(key) is not None for key in ("bytes", "sha256", "elfClass", "interpreter", "dtNeeded", "recursiveLibraryClosure")):
            findings.add("CURRENT_H24_ARTIFACT_BINDING_FORBIDDEN")
    by_role = {record["role"]: record for record in roles}
    for role in ("rmt_storage", "tftp_server"):
        conflicts = by_role[role]["identityContract"].get("historicalConflicts", [])
        if len(conflicts) != 1 or conflicts[0].get("state") != "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED":
            findings.add("IDENTITY_CONFLICT_MISSING")
    expected_counts = {
        "roleRecords": len(EXPECTED_ROLE_ORDER),
        "sourceSelectedProcessInstances": sum(
            len(record["sourceSelectedInstances"]) for record in roles
        ),
        "opaqueExternalElfRoles": len(OPAQUE_ROLES),
        "inProcessHelperBodies": 2,
        "topologyOwnerElfs": 1,
        "dependencySurfaceSlots": len(EXPECTED_ROLE_ORDER) * len(SURFACE_KEYS),
        "identityConflictRoles": 2,
        "negativeCases": len(_negative_corpus()),
    }
    if value.get("counts") != expected_counts or expected_counts["sourceSelectedProcessInstances"] != 16:
        findings.add("COUNT_MISMATCH")
    coverage = value.get("gateCoverage")
    if not isinstance(coverage, list) or len(coverage) != len(GATE_IDS):
        findings.add("GATE_COVERAGE_MISMATCH")
    else:
        for expected_gate, row in zip(GATE_IDS, coverage):
            if (
                not isinstance(row, dict)
                or set(row) != GATE_COVERAGE_KEYS
                or row.get("gateId") != expected_gate
                or row.get("rolesWithExplicitSlot") != list(EXPECTED_ROLE_ORDER)
                or row.get("status") != "UNPROVED"
                or row.get("retirementCreditGranted") is not False
            ):
                findings.add("GATE_COVERAGE_MISMATCH")
    try:
        canonical_model = build_inventory()
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        findings.add("PINNED_SEMANTIC_MODEL_UNAVAILABLE")
    else:
        # This artifact is generated evidence, not a caller-extensible schema.
        # Structural validity alone must never authorize a source-derived fact,
        # gate projection, launch contract, identity, or readiness value that
        # differs from the exact model rebuilt from the pinned inputs.
        if value != canonical_model:
            findings.add("PINNED_SEMANTIC_MISMATCH")
    return sorted(findings)


def canonical_text() -> str:
    inventory = build_inventory()
    findings = validate_inventory(inventory)
    if findings:
        raise ValueError(f"generated WP2-3 inventory rejected: {findings}")
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", type=Path, metavar="PATH")
    group.add_argument("--write", type=Path, nargs="?", const=DEFAULT_OUTPUT, metavar="PATH")
    args = parser.parse_args()
    rendered = canonical_text()
    if args.check is not None:
        if args.check.read_text() != rendered:
            raise SystemExit(f"inventory drift: {args.check}")
        return 0
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered)
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
