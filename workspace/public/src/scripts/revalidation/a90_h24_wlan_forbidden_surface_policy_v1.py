#!/usr/bin/env python3
"""Generate the host-only WP2-2 A90 WLAN forbidden-surface policy.

This unit binds the frozen H24 source hazards and defines a fail-closed schema
for future corrected-baseline or Option C inputs.  It does not inspect a
device or private input, build a candidate, retire a dependency gate, or grant
execution authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[5]
BASE = "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
DEFAULT_OUTPUT = ROOT / BASE / "policy/a90-h24-wlan-forbidden-surface-policy-v1.json"

PARENT_REL = f"{BASE}/inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
DESIGN_REL = f"{BASE}/design/a90-h24-wlan-one-factor-ablation-design-v1.json"
HELPER_REL = "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
MAIN_REL = "workspace/public/src/native-init/v724/90_main.inc.c"
MANIFEST_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h24/manifest.toml"
)

PINNED_INPUTS = {
    PARENT_REL: (42264, "d4ac9b47de9674995b891e888937969cb34b74d27b1c59e35cb7172fbd3370cb"),
    DESIGN_REL: (105900, "0eddec9ba9d637590c82499709179bd6b56a79d646d7967d3049a0bf36136b85"),
    HELPER_REL: (3253399, "4e68735fa2acc06fa4c101d8dbab6380d7785c4d9c7edfe47448ab26031b57e2"),
    MAIN_REL: (277766, "2a6863c0fd5f1dc2559ccee45031e389c956d6e094d8602364fd1875b919128f"),
    MANIFEST_REL: (7801, "40c26c5878db21737600bc29864db9123cc4650ec39d7f0d7395209c2df70a8f"),
}

SURFACE_SCHEMA = "a90-wlan-successor-surface-declaration-v1"
POLICY_SCHEMA = "a90-h24-wlan-forbidden-surface-policy-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GLOBAL_BINDER_PATHS = {"/dev/binder", "/dev/hwbinder", "/dev/vndbinder"}
GLOBAL_BINDER_RDEVS = {(10, 79), (10, 80), (10, 81)}
LEGACY_SNAPSHOT_PREFIXES = (
    "/mnt/sdext",
    "/cache/a90-wifi-property-v2167",
)
MANAGER_ROLES = ("servicemanager", "hwservicemanager")
CONSUMERS = ("construction", "order", "health", "cleanup", "evidence")
KNOWN_BACKEND_ROLES = {
    "servicemanager", "hwservicemanager", "vndservicemanager",
    "pm_proxy_helper", "per_mgr", "qrtr_ns", "pd_mapper", "rmt_storage",
    "tftp_server", "cnss_diag", "cnss_daemon", "property-service-shim",
    "modem-holder", "wifi-helper",
}
GRAPH_VARIANTS = {
    "B0_EARLY_PAIR", "B0_PROVIDER_ADJACENT_PAIR", "G_N_ROLE_ABLATION",
    "REDUCED_NATIVE_INTEGRATION", "DEBIAN_CAPSULE_INTEGRATION",
}
B0_REMOVALS = {
    "B0_EARLY_PAIR": ("servicemanager#2", "hwservicemanager#2"),
    "B0_PROVIDER_ADJACENT_PAIR": ("servicemanager#1", "hwservicemanager#1"),
}
LINEAGE_KEYS = {
    "kind", "parentManifestSha256", "parentInstances", "ablationUnitId",
    "removedRole", "removedInstanceIds",
}


def _lexical_regular(rel: str) -> Path:
    path = ROOT / rel
    cursor = ROOT
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"pinned input contains a symlink: {rel}")
    if not path.is_file():
        raise ValueError(f"pinned input is not a regular file: {rel}")
    return path


def _read_pinned(rel: str) -> bytes:
    path = _lexical_regular(rel)
    raw = path.read_bytes()
    expected_size, expected_sha = PINNED_INPUTS[rel]
    if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"WP2-2 pinned input drift: {rel}")
    return raw


def _load_inputs() -> dict[str, Any]:
    raw = {rel: _read_pinned(rel) for rel in PINNED_INPUTS}
    return {
        "raw": raw,
        "parent": json.loads(raw[PARENT_REL]),
        "design": json.loads(raw[DESIGN_REL]),
        "helper": raw[HELPER_REL].decode(),
        "main": raw[MAIN_REL].decode(),
        "manifest": raw[MANIFEST_REL].decode(),
    }


def _source_pin(rel: str) -> dict[str, Any]:
    size, sha256 = PINNED_INPUTS[rel]
    return {"path": rel, "bytes": size, "sha256": sha256}


def _require_once(text: str, token: str, label: str) -> None:
    if text.count(token) != 1:
        raise ValueError(f"{label} source contract drift: {token}")


def _require_source_contract(inputs: dict[str, Any]) -> None:
    parent = inputs["parent"]
    design = inputs["design"]
    helper = inputs["helper"]
    main = inputs["main"]
    manifest = inputs["manifest"]

    if parent.get("schema") != "a90-h24-wlan-capsule-dependency-inventory-v1":
        raise ValueError("WP2-2 parent schema drift")
    counts = parent.get("counts", {})
    if (
        counts.get("compositeInstances") != 13
        or counts.get("uniqueCompositeRoles") != 11
        or counts.get("sourceAccountedProcessesBeforeStationPolicy") != 16
    ):
        raise ValueError("WP2-2 parent 13/11/16 drift")
    components = parent.get("components", [])
    if len(components) != 16:
        raise ValueError("WP2-2 parent component count drift")
    role_counts: dict[str, int] = {}
    for component in components:
        role = component.get("role")
        role_counts[role] = role_counts.get(role, 0) + 1
    if role_counts.get("servicemanager") != 2 or role_counts.get("hwservicemanager") != 2:
        raise ValueError("WP2-2 parent duplicate-manager drift")
    if any(gate.get("status") != "UNPROVED" for gate in parent.get("dependencyGates", [])):
        raise ValueError("WP2-2 must not consume retired dependency gates")

    if design.get("schema") != "a90-h24-wlan-one-factor-ablation-design-v1":
        raise ValueError("WP2-2 design schema drift")
    if design.get("status", {}).get("wpH02Design") != "COMPLETE_H0_DESIGN_ONLY":
        raise ValueError("WP2-2 upstream design status drift")
    variants = design.get("baselineFormation", {}).get("serviceManagerPlacementVariants", [])
    if [item.get("variantId") for item in variants] != [
        "B0_EARLY_PAIR",
        "B0_PROVIDER_ADJACENT_PAIR",
    ]:
        raise ValueError("WP2-2 placement variants drift")
    if len(design.get("ablationUnits", [])) != 13:
        raise ValueError("WP2-2 ablation-unit count drift")
    if any(unit.get("deltaCardinality") != 1 for unit in design["ablationUnits"]):
        raise ValueError("WP2-2 exact-one delta drift")

    for token in (
        '-DA90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER=1',
        '-DA90_V1393_WIFI_TEST_PROPERTY_ROOT="/mnt/sdext/a90/private-property-v317/v726/dev/__properties__"',
    ):
        _require_once(manifest, token, "H24 manifest")
    for token in (
        '"--property-root",\n        A90_V1393_WIFI_TEST_PROPERTY_ROOT,',
        '"--allow-service-manager-start-only",\n        "--allow-wlan-pd-service-object-visible-trigger",',
    ):
        _require_once(main, token, "H24 launcher")
    for token in (
        'bind_rw("/sys/fs/selinux", paths->sys_fs_selinux)',
        'load_precompiled_policy_for_pm_observer(paths, stdout_buf)',
        'write_file_once_to_fd(policy_path, load_fd, &load_bytes, &load_hash)',
        'write(enforce_fd, "0", 1)',
        'materialize_one_binder_device(paths->dev_binder, 81, "binder"',
        'materialize_one_binder_device(paths->dev_hwbinder, 80, "hwbinder"',
        'materialize_one_binder_device(paths->dev_vndbinder, 79, "vndbinder"',
        'mknod(path, S_IFCHR | 0666, makedev(10, minor_no))',
        'path_has_prefix_component(path, "/mnt/sdext/a90/private-property-v317")',
        'path_has_prefix_component(path, "/cache/a90-wifi-property-v2167")',
        'bind_ro(cfg->property_root, paths->dev_properties)',
    ):
        if token not in helper:
            raise ValueError(f"H24 helper source contract drift: {token}")
    selected = helper[
        helper.index("static int run_wifi_companion_start_only_guarded") :
        helper.index("static int run_wifi_companion_hal_order_start_only_guarded")
    ]
    first = selected[
        selected.index("if (!android_order_pre_cnss_provider_observer &&\n        with_service_manager") :
        selected.index("if (!android_order_pre_cnss_provider_observer &&\n        !peripheral_manager_node_parity")
    ]
    second = selected[
        selected.index("if (wlan_pd_service_window_trigger || wlan_pd_service_object_visible_trigger)") :
        selected.index("if (wlan_pd_pm_service_window_trigger || wlan_pd_service_object_visible_trigger)")
    ]
    for executable in ('"/system/bin/servicemanager"', '"/system/bin/hwservicemanager"'):
        if first.count(executable) != 1 or second.count(executable) != 1:
            raise ValueError("H24 selected duplicate construction drift")


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _parent_instances(parent: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"instanceId": item["instanceId"], "role": item["role"]}
        for item in parent["components"]
    ]


def _reference_instances(parent: dict[str, Any], variant_id: str) -> list[dict[str, str]]:
    if variant_id not in B0_REMOVALS:
        raise ValueError("unknown reference placement variant")
    removed = set(B0_REMOVALS[variant_id])
    return [
        item for item in _parent_instances(parent)
        if item["instanceId"] not in removed
    ]


@lru_cache(maxsize=1)
def _pinned_parent() -> dict[str, Any]:
    return json.loads(_read_pinned(PARENT_REL))


@lru_cache(maxsize=1)
def _pinned_ablation_role_map() -> dict[str, str]:
    design = json.loads(_read_pinned(DESIGN_REL))
    return {
        unit["unitId"]: unit["removedRole"]
        for unit in design["ablationUnits"]
    }


def _baseline_lineage(parent: dict[str, Any], variant_id: str) -> dict[str, Any]:
    parent_instances = _parent_instances(parent)
    return {
        "kind": "CORRECTED_BASELINE_PLACEMENT",
        "parentManifestSha256": _canonical_digest(parent_instances),
        "parentInstances": parent_instances,
        "ablationUnitId": None,
        "removedRole": None,
        "removedInstanceIds": list(B0_REMOVALS[variant_id]),
    }


def _reference_surface(parent: dict[str, Any], variant_id: str) -> dict[str, Any]:
    instances = _reference_instances(parent, variant_id)
    manifest_digest = _canonical_digest(instances)
    return {
        "schema": SURFACE_SCHEMA,
        "target": "Samsung Galaxy A90 5G",
        "scope": "H0_STRUCTURAL_REFERENCE_ONLY_NOT_CANDIDATE_INPUT",
        "componentGraph": {
            "variantId": variant_id,
            "generationSource": "ONE_CANONICAL_GENERATED_MANIFEST",
            "instances": instances,
            "lineage": _baseline_lineage(parent, variant_id),
            "manifestSha256": manifest_digest,
            "consumerManifestSha256": {
                consumer: manifest_digest for consumer in CONSUMERS
            },
        },
        "selinuxSurface": {"operations": []},
        "binderSurface": {
            "endpointMode": "NONE",
            "proofTerminal": "NOT_APPLICABLE",
            "proofBindingSha256": None,
            "endpoints": [],
        },
        "propertyInput": {
            "sourceClass": "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET_UNBUILT",
            "preExecutionTerminal": "UNPROVED_H0D10",
            "finalTerminal": "UNPROVED_H0D04_H0D10",
            "wholeSnapshotAccepted": False,
            "privateSnapshotBytesUsed": False,
            "sources": [],
        },
        "propertyService": {
            "endpointMode": "ABSENT",
            "proofTerminal": "NOT_APPLICABLE",
            "proofBindingSha256": None,
            "endpoints": [],
        },
    }


def _is_canonical_absolute(path: Any) -> bool:
    return (
        isinstance(path, str)
        and path.startswith("/")
        and "\x00" not in path
        and "\n" not in path
        and "//" not in path
        and str(PurePosixPath(path)) == path
        and ".." not in PurePosixPath(path).parts
    )


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _is_reduced_component_graph(instances: Any) -> bool:
    if not isinstance(instances, list) or not instances:
        return False
    ids: list[str] = []
    roles: list[str] = []
    for item in instances:
        if not _exact_keys(item, {"instanceId", "role"}) or not all(
            isinstance(item.get(key), str) and item[key]
            for key in ("instanceId", "role")
        ):
            return False
        ids.append(item["instanceId"])
        roles.append(item["role"])
    return (
        all(role in KNOWN_BACKEND_ROLES for role in roles)
        and len(ids) == len(set(ids))
        and len(roles) == len(set(roles))
    )


def _validate_component_lineage(
    variant_id: Any,
    instances: Any,
    lineage: Any,
    findings: set[str],
    pending: set[str],
) -> None:
    if (
        not _exact_keys(lineage, LINEAGE_KEYS)
        or not isinstance(lineage.get("parentInstances"), list)
        or not isinstance(lineage.get("removedInstanceIds"), list)
    ):
        findings.add("COMPONENT_LINEAGE_SCHEMA_MISMATCH")
        return
    if isinstance(variant_id, str) and variant_id in B0_REMOVALS:
        parent = _pinned_parent()
        if instances != _reference_instances(parent, variant_id):
            findings.add("BASELINE_COMPONENT_GRAPH_MISMATCH")
        if lineage != _baseline_lineage(parent, variant_id):
            findings.add("BASELINE_LINEAGE_MISMATCH")
        return
    if variant_id == "G_N_ROLE_ABLATION":
        parent_sha = lineage["parentManifestSha256"]
        parent_instances = lineage["parentInstances"]
        unit_id = lineage["ablationUnitId"]
        removed_role = lineage["removedRole"]
        removed_ids = lineage["removedInstanceIds"]
        unit_roles = _pinned_ablation_role_map()
        parent_valid = _is_reduced_component_graph(parent_instances)
        removed_parent_entries = (
            [
                item for item in parent_instances
                if item["instanceId"] == removed_ids[0]
            ]
            if parent_valid
            and len(removed_ids) == 1
            and isinstance(removed_ids[0], str)
            else []
        )
        expected_child = (
            [
                item for item in parent_instances
                if item["instanceId"] != removed_ids[0]
            ]
            if len(removed_parent_entries) == 1
            else None
        )
        if (
            lineage["kind"] != "WP_H0_2_ONE_ROLE_REMOVAL"
            or not isinstance(parent_sha, str)
            or not SHA256_RE.fullmatch(parent_sha)
            or not parent_valid
            or parent_sha != _canonical_digest(parent_instances)
            or not isinstance(unit_id, str)
            or unit_roles.get(unit_id) != removed_role
            or not isinstance(removed_role, str)
            or len(removed_ids) != 1
            or not isinstance(removed_ids[0], str)
            or not removed_ids[0].startswith(removed_role + "#")
            or len(removed_parent_entries) != 1
            or removed_parent_entries[0]["role"] != removed_role
            or instances != expected_child
        ):
            findings.add("ROLE_REMOVAL_LINEAGE_MISMATCH")
        pending.add("WP_H0_2_GENERATION_LINEAGE_CONSUMER_ABSENT")
        return
    if isinstance(variant_id, str) and variant_id in {
        "REDUCED_NATIVE_INTEGRATION", "DEBIAN_CAPSULE_INTEGRATION"
    }:
        parent_instances = lineage["parentInstances"]
        if (
            lineage["kind"] != "TOPOLOGY_INTEGRATION"
            or not isinstance(lineage["parentManifestSha256"], str)
            or not SHA256_RE.fullmatch(lineage["parentManifestSha256"])
            or not _is_reduced_component_graph(parent_instances)
            or lineage["parentManifestSha256"] != _canonical_digest(parent_instances)
            or instances != parent_instances
            or lineage["ablationUnitId"] is not None
            or lineage["removedRole"] is not None
            or lineage["removedInstanceIds"] != []
        ):
            findings.add("TOPOLOGY_INTEGRATION_LINEAGE_MISMATCH")
        pending.add("TOPOLOGY_INTEGRATION_LINEAGE_CONSUMER_ABSENT")


def validate_surface_contract(surface: Any) -> dict[str, Any]:
    """Validate only the WP2-2 static surface boundary.

    A static pass never makes a declaration execution- or candidate-eligible.
    Future consumers must derive the declaration from exact linked bytes and
    independently bind every still-unproved dependency gate.
    """

    findings: set[str] = set()
    pending: set[str] = {
        "FUTURE_BYTE_DERIVED_DECLARATION_CONSUMER_ABSENT"
    }
    top_keys = {
        "schema", "target", "scope", "componentGraph", "selinuxSurface",
        "binderSurface", "propertyInput", "propertyService",
    }
    if not _exact_keys(surface, top_keys):
        findings.add("SCHEMA_KEY_MISMATCH")
        return _validation_result(findings, pending)
    if (
        surface["schema"] != SURFACE_SCHEMA
        or surface["target"] != "Samsung Galaxy A90 5G"
        or surface["scope"] != "H0_STRUCTURAL_REFERENCE_ONLY_NOT_CANDIDATE_INPUT"
    ):
        findings.add("SCHEMA_IDENTITY_MISMATCH")

    graph = surface["componentGraph"]
    if not _exact_keys(
        graph,
        {
            "variantId", "generationSource", "instances", "lineage",
            "manifestSha256", "consumerManifestSha256",
        },
    ):
        findings.add("COMPONENT_GRAPH_SCHEMA_MISMATCH")
    else:
        variant_id = graph["variantId"]
        if not isinstance(variant_id, str) or variant_id not in GRAPH_VARIANTS:
            findings.add("UNKNOWN_BASELINE_VARIANT")
        if graph["generationSource"] != "ONE_CANONICAL_GENERATED_MANIFEST":
            findings.add("HAND_MAINTAINED_COMPONENT_GRAPH_FORBIDDEN")
        instances = graph["instances"]
        if not isinstance(instances, list) or not instances:
            findings.add("COMPONENT_INSTANCE_SCHEMA_MISMATCH")
        else:
            ids: list[str] = []
            roles: list[str] = []
            for item in instances:
                if not _exact_keys(item, {"instanceId", "role"}) or not all(
                    isinstance(item.get(key), str) and item[key]
                    for key in ("instanceId", "role")
                ):
                    findings.add("COMPONENT_INSTANCE_SCHEMA_MISMATCH")
                    continue
                ids.append(item["instanceId"])
                roles.append(item["role"])
                if item["role"] not in KNOWN_BACKEND_ROLES:
                    findings.add("UNKNOWN_COMPONENT_ROLE_FORBIDDEN")
            if len(ids) != len(set(ids)):
                findings.add("DUPLICATE_COMPONENT_INSTANCE_FORBIDDEN")
            if any(roles.count(role) > 1 for role in set(roles)):
                findings.add("DUPLICATE_COMPONENT_ROLE_FORBIDDEN")
            for role in MANAGER_ROLES:
                if roles.count(role) > 1:
                    findings.add(f"DUPLICATE_{role.upper()}_FORBIDDEN")
                if (
                    isinstance(variant_id, str)
                    and variant_id.startswith("B0_")
                    and roles.count(role) != 1
                ):
                    findings.add(f"BASELINE_EXACT_ONE_{role.upper()}_REQUIRED")
            expected_pair = {
                "B0_EARLY_PAIR": {
                    "servicemanager#1": "servicemanager",
                    "hwservicemanager#1": "hwservicemanager",
                },
                "B0_PROVIDER_ADJACENT_PAIR": {
                    "servicemanager#2": "servicemanager",
                    "hwservicemanager#2": "hwservicemanager",
                },
            }.get(variant_id) if isinstance(variant_id, str) else None
            if expected_pair is not None:
                actual_by_id = {
                    item["instanceId"]: item["role"]
                    for item in instances
                    if _exact_keys(item, {"instanceId", "role"})
                    and isinstance(item.get("instanceId"), str)
                    and isinstance(item.get("role"), str)
                }
                if any(
                    actual_by_id.get(instance_id) != role
                    for instance_id, role in expected_pair.items()
                ):
                    findings.add("BASELINE_MANAGER_PLACEMENT_IDENTITY_MISMATCH")
            expected_digest = _canonical_digest(instances)
            if graph["manifestSha256"] != expected_digest:
                findings.add("COMPONENT_MANIFEST_DIGEST_MISMATCH")
            consumers = graph["consumerManifestSha256"]
            if not _exact_keys(consumers, set(CONSUMERS)) or any(
                consumers.get(name) != expected_digest for name in CONSUMERS
            ):
                findings.add("COMPONENT_CONSUMER_DIGEST_DRIFT")
            _validate_component_lineage(
                variant_id,
                instances,
                graph["lineage"],
                findings,
                pending,
            )

    selinux = surface["selinuxSurface"]
    if not _exact_keys(selinux, {"operations"}) or not isinstance(selinux.get("operations"), list):
        findings.add("SELINUX_SURFACE_SCHEMA_MISMATCH")
    else:
        for operation in selinux["operations"]:
            if not _exact_keys(operation, {"kind", "source", "target", "access", "scope"}):
                findings.add("SELINUX_OPERATION_SCHEMA_MISMATCH")
                continue
            if not isinstance(operation["kind"], str) or operation["kind"] not in {
                "BIND_MOUNT", "OPEN", "WRITE"
            }:
                findings.add("SELINUX_OPERATION_SCHEMA_MISMATCH")
                continue
            if (
                not isinstance(operation["access"], str)
                or operation["access"] not in {"READ", "WRITE", "RW"}
                or not isinstance(operation["scope"], str)
                or operation["scope"] not in {"GLOBAL_KERNEL", "CAPSULE_PRIVATE"}
                or (operation["source"] is None and operation["target"] is None)
            ):
                findings.add("SELINUX_OPERATION_SCHEMA_MISMATCH")
                continue
            if (
                (operation["kind"] == "WRITE" and operation["access"] != "WRITE")
                or (
                    operation["kind"] == "BIND_MOUNT"
                    and (
                        operation["source"] is None
                        or operation["target"] is None
                        or operation["access"] not in {"READ", "RW"}
                    )
                )
            ):
                findings.add("SELINUX_OPERATION_SCHEMA_MISMATCH")
                continue
            for field in ("source", "target"):
                if operation[field] is not None and not _is_canonical_absolute(operation[field]):
                    findings.add("NONCANONICAL_PATH_FORBIDDEN")
            paths = [operation["source"], operation["target"]]
            global_selinux = operation["scope"] == "GLOBAL_KERNEL" or any(
                isinstance(path, str)
                and (path == "/sys/fs/selinux" or path.startswith("/sys/fs/selinux/"))
                for path in paths
            )
            if global_selinux and operation["access"] in {"RW", "WRITE"}:
                findings.add("GLOBAL_SELINUX_MUTATION_FORBIDDEN")

    _validate_binder(surface["binderSurface"], findings, pending)
    _validate_property_input(surface["propertyInput"], findings, pending)
    _validate_property_service(surface["propertyService"], findings, pending)
    return _validation_result(findings, pending)


def _validate_binder(value: Any, findings: set[str], pending: set[str]) -> None:
    expected = {"endpointMode", "proofTerminal", "proofBindingSha256", "endpoints"}
    if not _exact_keys(value, expected) or not isinstance(value.get("endpoints"), list):
        findings.add("BINDER_SURFACE_SCHEMA_MISMATCH")
        return
    modes = {
        "NONE",
        "CAPSULE_PRIVATE_BINDERFS_PENDING_H0D05",
        "CAPSULE_PRIVATE_BINDERFS_BOUND_PROOF",
    }
    if not isinstance(value["endpointMode"], str) or value["endpointMode"] not in modes:
        findings.add("BINDER_SURFACE_SCHEMA_MISMATCH")
        return
    if value["endpointMode"] == "NONE":
        if value["endpoints"] or value["proofTerminal"] != "NOT_APPLICABLE" or value["proofBindingSha256"] is not None:
            findings.add("BINDER_MODE_ENDPOINT_CONTRADICTION")
    else:
        if not value["endpoints"]:
            findings.add("BINDER_MODE_ENDPOINT_CONTRADICTION")
        if value["endpointMode"].endswith("PENDING_H0D05"):
            if value["proofTerminal"] != "UNPROVED_H0D05" or value["proofBindingSha256"] is not None:
                findings.add("BINDER_PROOF_BINDING_MISMATCH")
            pending.add("H0D05_PRIVATE_BINDERFS_PROOF_REQUIRED")
        elif value["proofTerminal"] != "PRIVATE_BINDERFS_PROVED" or not (
            isinstance(value["proofBindingSha256"], str)
            and SHA256_RE.fullmatch(value["proofBindingSha256"])
        ):
            findings.add("BINDER_PROOF_BINDING_MISMATCH")
    for endpoint in value["endpoints"]:
        if not _exact_keys(
            endpoint,
            {"path", "backingClass", "major", "minor", "namespaceScope"},
        ):
            findings.add("BINDER_ENDPOINT_SCHEMA_MISMATCH")
            continue
        path = endpoint["path"]
        major = endpoint["major"]
        minor = endpoint["minor"]
        if (
            (major is not None and (not isinstance(major, int) or isinstance(major, bool)))
            or (minor is not None and (not isinstance(minor, int) or isinstance(minor, bool)))
            or not isinstance(endpoint["backingClass"], str)
            or endpoint["backingClass"] not in {
                "NATIVE_GLOBAL_BINDER_CHARDEV", "FRESH_CAPSULE_PRIVATE_BINDERFS"
            }
            or not isinstance(endpoint["namespaceScope"], str)
            or endpoint["namespaceScope"] not in {"NATIVE_GLOBAL", "CAPSULE_PRIVATE"}
        ):
            findings.add("BINDER_ENDPOINT_SCHEMA_MISMATCH")
            continue
        canonical_path = _is_canonical_absolute(path)
        if not canonical_path:
            findings.add("NONCANONICAL_PATH_FORBIDDEN")
        if canonical_path and path in GLOBAL_BINDER_PATHS:
            findings.add("GLOBAL_BINDER_PATH_FORBIDDEN")
        if endpoint["backingClass"] == "NATIVE_GLOBAL_BINDER_CHARDEV":
            findings.add("GLOBAL_BINDER_BACKING_FORBIDDEN")
        if (major, minor) in GLOBAL_BINDER_RDEVS:
            findings.add("GLOBAL_BINDER_RDEV_FORBIDDEN")
        if endpoint["namespaceScope"] != "CAPSULE_PRIVATE":
            findings.add("GLOBAL_BINDER_NAMESPACE_FORBIDDEN")
        if value["endpointMode"] != "NONE" and not (
            isinstance(path, str)
            and path.startswith("/run/a90-wlan-capsule/binderfs/")
            and endpoint["backingClass"] == "FRESH_CAPSULE_PRIVATE_BINDERFS"
            and major is None
            and minor is None
        ):
            findings.add("PRIVATE_BINDERFS_SHAPE_MISMATCH")


def _validate_property_input(value: Any, findings: set[str], pending: set[str]) -> None:
    expected = {
        "sourceClass", "preExecutionTerminal", "finalTerminal",
        "wholeSnapshotAccepted", "privateSnapshotBytesUsed", "sources",
    }
    if not _exact_keys(value, expected) or not isinstance(value.get("sources"), list):
        findings.add("PROPERTY_INPUT_SCHEMA_MISMATCH")
        return
    classes = {
        "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET_UNBUILT",
        "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET",
        "PROPERTY_ABSENT",
        "PUBLIC_DETERMINISTIC_FINITE_SEED",
    }
    source_class = value["sourceClass"]
    if not isinstance(source_class, str) or source_class not in classes:
        findings.add("PROPERTY_INPUT_SCHEMA_MISMATCH")
    if value["wholeSnapshotAccepted"] is not False:
        findings.add("WHOLE_PROPERTY_SNAPSHOT_FORBIDDEN")
    if value["privateSnapshotBytesUsed"] is not False:
        findings.add("PRIVATE_SNAPSHOT_BYTES_FORBIDDEN")
    if source_class == "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET_UNBUILT":
        if value["sources"]:
            findings.add("PROPERTY_SOURCE_CLASS_CONTRADICTION")
        if value["preExecutionTerminal"] != "UNPROVED_H0D10":
            findings.add("PROPERTY_TERMINAL_MISMATCH")
        pending.add("H0D10_PUBLIC_BOOTSTRAP_SUPERSET_UNPROVED")
    elif source_class == "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET":
        if (
            not value["sources"]
            or value["preExecutionTerminal"] != "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED"
            or value["finalTerminal"] != "UNPROVED_H0D04_POST_ABLATION"
        ):
            findings.add("PROPERTY_TERMINAL_MISMATCH")
        pending.add("H0D04_PROPERTY_TERMINAL_UNPROVED")
    elif source_class == "PROPERTY_ABSENT":
        if (
            value["sources"]
            or value["preExecutionTerminal"] != "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED"
            or value["finalTerminal"] != "PROPERTY_ABSENT_PROVED"
        ):
            findings.add("PROPERTY_TERMINAL_MISMATCH")
    elif source_class == "PUBLIC_DETERMINISTIC_FINITE_SEED":
        if (
            not value["sources"]
            or value["preExecutionTerminal"] != "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED"
            or value["finalTerminal"] != "PROPERTY_FINITE_SEED_PROVED"
        ):
            findings.add("PROPERTY_TERMINAL_MISMATCH")
    final_terminal = value["finalTerminal"]
    if isinstance(final_terminal, str) and final_terminal in {
        "UNPROVED_H0D04_H0D10", "UNPROVED_H0D04_POST_ABLATION"
    }:
        pending.add("H0D04_PROPERTY_TERMINAL_UNPROVED")
    elif not isinstance(final_terminal, str) or final_terminal not in {
        "PROPERTY_ABSENT_PROVED", "PROPERTY_FINITE_SEED_PROVED"
    }:
        findings.add("PROPERTY_TERMINAL_MISMATCH")
    for source in value["sources"]:
        if not _exact_keys(source, {"path", "kind", "provenance", "originalSourceClass"}):
            findings.add("PROPERTY_SOURCE_SCHEMA_MISMATCH")
            continue
        path = source["path"]
        if not _is_canonical_absolute(path):
            findings.add("NONCANONICAL_PATH_FORBIDDEN")
        if not isinstance(source["kind"], str) or source["kind"] not in {
            "DETERMINISTIC_BOOTSTRAP_INPUT", "FINITE_PROPERTY_SEED",
            "WHOLE_PROPERTY_SNAPSHOT",
        } or not isinstance(source["provenance"], str) or source["provenance"] not in {
            "PUBLIC_DETERMINISTIC_GENERATOR", "PUBLIC_IMMUTABLE_FILE",
            "PRIVATE_WHOLE_SNAPSHOT", "RELOCATED_PRIVATE_WHOLE_SNAPSHOT",
        } or not isinstance(source["originalSourceClass"], str) or source["originalSourceClass"] not in {
            "PUBLIC_SOURCE", "PRIVATE_WHOLE_SNAPSHOT"
        }:
            findings.add("PROPERTY_SOURCE_SCHEMA_MISMATCH")
            continue
        expected_kind = {
            "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET": "DETERMINISTIC_BOOTSTRAP_INPUT",
            "PUBLIC_DETERMINISTIC_FINITE_SEED": "FINITE_PROPERTY_SEED",
        }.get(source_class) if isinstance(source_class, str) else None
        if expected_kind is not None and source["kind"] != expected_kind:
            findings.add("PROPERTY_SOURCE_CLASS_CONTRADICTION")
        if isinstance(path, str) and any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in LEGACY_SNAPSHOT_PREFIXES
        ):
            findings.add("SD_OR_LEGACY_SNAPSHOT_PATH_FORBIDDEN")
        if source["kind"] == "WHOLE_PROPERTY_SNAPSHOT":
            findings.add("WHOLE_PROPERTY_SNAPSHOT_FORBIDDEN")
        if source["provenance"] in {
            "PRIVATE_WHOLE_SNAPSHOT", "RELOCATED_PRIVATE_WHOLE_SNAPSHOT"
        } or source["originalSourceClass"] == "PRIVATE_WHOLE_SNAPSHOT":
            findings.add("PRIVATE_SNAPSHOT_PROVENANCE_FORBIDDEN")


def _validate_property_service(value: Any, findings: set[str], pending: set[str]) -> None:
    expected = {"endpointMode", "proofTerminal", "proofBindingSha256", "endpoints"}
    if not _exact_keys(value, expected) or not isinstance(value.get("endpoints"), list):
        findings.add("PROPERTY_SERVICE_SCHEMA_MISMATCH")
        return
    modes = {
        "ABSENT",
        "CAPSULE_PRIVATE_FILESYSTEM_UNIX_PENDING_H0D04",
        "CAPSULE_PRIVATE_FILESYSTEM_UNIX_BOUND_PROOF",
    }
    if not isinstance(value["endpointMode"], str) or value["endpointMode"] not in modes:
        findings.add("PROPERTY_SERVICE_SCHEMA_MISMATCH")
        return
    if value["endpointMode"] == "ABSENT":
        if value["endpoints"] or value["proofTerminal"] != "NOT_APPLICABLE" or value["proofBindingSha256"] is not None:
            findings.add("PROPERTY_SERVICE_MODE_CONTRADICTION")
    else:
        if not value["endpoints"]:
            findings.add("PROPERTY_SERVICE_MODE_CONTRADICTION")
        if value["endpointMode"].endswith("PENDING_H0D04"):
            if value["proofTerminal"] != "UNPROVED_H0D04" or value["proofBindingSha256"] is not None:
                findings.add("PROPERTY_SERVICE_PROOF_BINDING_MISMATCH")
            pending.add("H0D04_PRIVATE_PROPERTY_SERVICE_PROOF_REQUIRED")
        elif value["proofTerminal"] != "PRIVATE_PROPERTY_SERVICE_PROVED" or not (
            isinstance(value["proofBindingSha256"], str)
            and SHA256_RE.fullmatch(value["proofBindingSha256"])
        ):
            findings.add("PROPERTY_SERVICE_PROOF_BINDING_MISMATCH")
    for endpoint in value["endpoints"]:
        if not _exact_keys(
            endpoint,
            {"path", "namespaceScope", "backingClass", "abstract", "scmRights", "inherited"},
        ):
            findings.add("PROPERTY_SERVICE_ENDPOINT_SCHEMA_MISMATCH")
            continue
        path = endpoint["path"]
        if (
            not isinstance(endpoint["namespaceScope"], str)
            or endpoint["namespaceScope"] not in {"NATIVE_GLOBAL", "CAPSULE_PRIVATE"}
            or not isinstance(endpoint["backingClass"], str)
            or endpoint["backingClass"] not in {
                "INHERITED_NATIVE_FILESYSTEM_SOCKET",
                "FRESH_CAPSULE_PRIVATE_FILESYSTEM_SOCKET",
            }
            or type(endpoint["abstract"]) is not bool
            or type(endpoint["scmRights"]) is not bool
            or type(endpoint["inherited"]) is not bool
        ):
            findings.add("PROPERTY_SERVICE_ENDPOINT_SCHEMA_MISMATCH")
            continue
        if not _is_canonical_absolute(path):
            findings.add("NONCANONICAL_PATH_FORBIDDEN")
        if (
            not isinstance(path, str)
            or not path.startswith("/run/a90-wlan-capsule/")
            or endpoint["namespaceScope"] != "CAPSULE_PRIVATE"
            or endpoint["backingClass"] != "FRESH_CAPSULE_PRIVATE_FILESYSTEM_SOCKET"
            or endpoint["abstract"] is not False
            or endpoint["scmRights"] is not False
            or endpoint["inherited"] is not False
        ):
            findings.add("GLOBAL_OR_CAPABILITY_PROPERTY_ENDPOINT_FORBIDDEN")


def _validation_result(findings: set[str], pending: set[str]) -> dict[str, Any]:
    accepted = not findings
    return {
        "outcome": (
            "STATIC_REINTRODUCTION_GUARDS_PASS_H0_ONLY"
            if accepted
            else "REJECTED_FORBIDDEN_OR_MALFORMED_SURFACE"
        ),
        "surfacePolicySatisfied": accepted,
        "findingCodes": sorted(findings),
        "pendingProofs": sorted(pending),
        "candidateEligible": False,
        "executionEligible": False,
        "authorityGranted": False,
    }


def _finite_seed_source(
    path: str,
    *,
    kind: str = "FINITE_PROPERTY_SEED",
    provenance: str = "PUBLIC_DETERMINISTIC_GENERATOR",
    original: str = "PUBLIC_SOURCE",
) -> dict[str, str]:
    return {
        "path": path,
        "kind": kind,
        "provenance": provenance,
        "originalSourceClass": original,
    }


def _as_finite_seed(surface: dict[str, Any], source: dict[str, str]) -> None:
    surface["propertyInput"] = {
        "sourceClass": "PUBLIC_DETERMINISTIC_FINITE_SEED",
        "preExecutionTerminal": "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
        "finalTerminal": "PROPERTY_FINITE_SEED_PROVED",
        "wholeSnapshotAccepted": False,
        "privateSnapshotBytesUsed": False,
        "sources": [source],
    }


def _binder_endpoint(
    path: str,
    backing: str,
    major: int | None,
    minor: int | None,
    scope: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "backingClass": backing,
        "major": major,
        "minor": minor,
        "namespaceScope": scope,
    }


def _negative_cases(base: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[tuple[str, str, Callable[[dict[str, Any]], None], set[str]]] = []

    def add_instance(role: str, instance_id: str) -> Callable[[dict[str, Any]], None]:
        def mutate(value: dict[str, Any]) -> None:
            value["componentGraph"]["instances"].append({"instanceId": instance_id, "role": role})
            digest = _canonical_digest(value["componentGraph"]["instances"])
            value["componentGraph"]["manifestSha256"] = digest
            value["componentGraph"]["consumerManifestSha256"] = {
                consumer: digest for consumer in CONSUMERS
            }
        return mutate

    cases.extend([
        (
            "duplicate-servicemanager",
            "Reintroduce the removed servicemanager instance through the canonical manifest.",
            add_instance("servicemanager", "servicemanager#2"),
            {"DUPLICATE_SERVICEMANAGER_FORBIDDEN"},
        ),
        (
            "duplicate-hwservicemanager",
            "Reintroduce the removed hwservicemanager instance through the canonical manifest.",
            add_instance("hwservicemanager", "hwservicemanager#2"),
            {"DUPLICATE_HWSERVICEMANAGER_FORBIDDEN"},
        ),
    ])

    def remove_baseline_role(value: dict[str, Any]) -> None:
        value["componentGraph"]["instances"] = [
            item
            for item in value["componentGraph"]["instances"]
            if item["role"] != "cnss_daemon"
        ]
        digest = _canonical_digest(value["componentGraph"]["instances"])
        value["componentGraph"]["manifestSha256"] = digest
        value["componentGraph"]["consumerManifestSha256"] = {
            consumer: digest for consumer in CONSUMERS
        }

    cases.append((
        "baseline-nonplacement-role-removal",
        "Delete cnss_daemon while falsely retaining the corrected-baseline identity.",
        remove_baseline_role,
        {"BASELINE_COMPONENT_GRAPH_MISMATCH"},
    ))

    def multi_role_removal_disguised_as_one(value: dict[str, Any]) -> None:
        parent_instances = copy.deepcopy(value["componentGraph"]["instances"])
        removed_id = next(
            item["instanceId"]
            for item in parent_instances
            if item["role"] == "cnss_daemon"
        )
        value["componentGraph"]["variantId"] = "G_N_ROLE_ABLATION"
        value["componentGraph"]["instances"] = [
            item
            for item in parent_instances
            if item["role"] not in {"cnss_daemon", "tftp_server"}
        ]
        value["componentGraph"]["lineage"] = {
            "kind": "WP_H0_2_ONE_ROLE_REMOVAL",
            "parentManifestSha256": _canonical_digest(parent_instances),
            "parentInstances": parent_instances,
            "ablationUnitId": "WP-H0-2-A8",
            "removedRole": "cnss_daemon",
            "removedInstanceIds": [removed_id],
        }
        digest = _canonical_digest(value["componentGraph"]["instances"])
        value["componentGraph"]["manifestSha256"] = digest
        value["componentGraph"]["consumerManifestSha256"] = {
            consumer: digest for consumer in CONSUMERS
        }

    cases.append((
        "multi-role-removal-disguised-as-one",
        "Delete cnss_daemon and tftp_server while declaring only the A8 cnss_daemon transition.",
        multi_role_removal_disguised_as_one,
        {"ROLE_REMOVAL_LINEAGE_MISMATCH"},
    ))

    def consumer_drift(value: dict[str, Any]) -> None:
        value["componentGraph"]["consumerManifestSha256"]["cleanup"] = "0" * 64

    cases.append((
        "component-consumer-digest-drift",
        "Let cleanup consume a graph different from construction/order/health/evidence.",
        consumer_drift,
        {"COMPONENT_CONSUMER_DIGEST_DRIFT"},
    ))

    def selinux_operation(kind: str, source: str | None, target: str, access: str) -> Callable[[dict[str, Any]], None]:
        def mutate(value: dict[str, Any]) -> None:
            value["selinuxSurface"]["operations"].append({
                "kind": kind,
                "source": source,
                "target": target,
                "access": access,
                "scope": "GLOBAL_KERNEL",
            })
        return mutate

    cases.extend([
        (
            "global-selinuxfs-rw-bind",
            "Bind the native SELinuxFS read-write into the capsule.",
            selinux_operation("BIND_MOUNT", "/sys/fs/selinux", "/run/a90-wlan-capsule/sys/fs/selinux", "RW"),
            {"GLOBAL_SELINUX_MUTATION_FORBIDDEN"},
        ),
        (
            "global-selinux-load-write",
            "Write a vendor policy to the global SELinux load interface.",
            selinux_operation("WRITE", None, "/sys/fs/selinux/load", "WRITE"),
            {"GLOBAL_SELINUX_MUTATION_FORBIDDEN"},
        ),
        (
            "global-selinux-enforce-write",
            "Write permissive state to the global SELinux enforce interface.",
            selinux_operation("WRITE", None, "/sys/fs/selinux/enforce", "WRITE"),
            {"GLOBAL_SELINUX_MUTATION_FORBIDDEN"},
        ),
    ])

    def set_binder(value: dict[str, Any], endpoint: dict[str, Any]) -> None:
        value["binderSurface"] = {
            "endpointMode": "CAPSULE_PRIVATE_BINDERFS_PENDING_H0D05",
            "proofTerminal": "UNPROVED_H0D05",
            "proofBindingSha256": None,
            "endpoints": [endpoint],
        }

    cases.extend([
        (
            "native-global-binder-path",
            "Expose the native /dev/binder character device.",
            lambda value: set_binder(value, _binder_endpoint(
                "/dev/binder", "NATIVE_GLOBAL_BINDER_CHARDEV", 10, 81, "NATIVE_GLOBAL"
            )),
            {
                "GLOBAL_BINDER_PATH_FORBIDDEN", "GLOBAL_BINDER_BACKING_FORBIDDEN",
                "GLOBAL_BINDER_RDEV_FORBIDDEN", "GLOBAL_BINDER_NAMESPACE_FORBIDDEN",
                "PRIVATE_BINDERFS_SHAPE_MISMATCH",
            },
        ),
        (
            "relocated-native-global-binder-rdev",
            "Rename the native binder rdev under a capsule-looking path.",
            lambda value: set_binder(value, _binder_endpoint(
                "/run/a90-wlan-capsule/binderfs/binder",
                "NATIVE_GLOBAL_BINDER_CHARDEV", 10, 81, "CAPSULE_PRIVATE",
            )),
            {
                "GLOBAL_BINDER_BACKING_FORBIDDEN", "GLOBAL_BINDER_RDEV_FORBIDDEN",
                "PRIVATE_BINDERFS_SHAPE_MISMATCH",
            },
        ),
    ])

    cases.extend([
        (
            "sd-property-source",
            "Read a finite-seed declaration from the removable-card namespace.",
            lambda value: _as_finite_seed(value, _finite_seed_source(
                "/mnt/sdext/a90/property-seed-v1.json"
            )),
            {"SD_OR_LEGACY_SNAPSHOT_PATH_FORBIDDEN"},
        ),
        (
            "cache-relocated-whole-snapshot",
            "Move the private whole snapshot to the historical cache alias.",
            lambda value: _as_finite_seed(value, _finite_seed_source(
                "/cache/a90-wifi-property-v2167/dev/__properties__",
                kind="WHOLE_PROPERTY_SNAPSHOT",
                provenance="RELOCATED_PRIVATE_WHOLE_SNAPSHOT",
                original="PRIVATE_WHOLE_SNAPSHOT",
            )),
            {
                "SD_OR_LEGACY_SNAPSHOT_PATH_FORBIDDEN",
                "WHOLE_PROPERTY_SNAPSHOT_FORBIDDEN",
                "PRIVATE_SNAPSHOT_PROVENANCE_FORBIDDEN",
            },
        ),
        (
            "private-snapshot-provenance-under-benign-path",
            "Rename private snapshot bytes under a nonlegacy cache path.",
            lambda value: _as_finite_seed(value, _finite_seed_source(
                "/cache/a90-public-looking/seed.json",
                provenance="RELOCATED_PRIVATE_WHOLE_SNAPSHOT",
                original="PRIVATE_WHOLE_SNAPSHOT",
            )),
            {"PRIVATE_SNAPSHOT_PROVENANCE_FORBIDDEN"},
        ),
        (
            "publicly-named-whole-snapshot",
            "Call a complete property-area copy public deterministic input.",
            lambda value: _as_finite_seed(value, _finite_seed_source(
                "/cache/a90-public-looking/seed.json",
                kind="WHOLE_PROPERTY_SNAPSHOT",
            )),
            {"WHOLE_PROPERTY_SNAPSHOT_FORBIDDEN"},
        ),
    ])

    def global_property_service(value: dict[str, Any]) -> None:
        value["propertyService"] = {
            "endpointMode": "CAPSULE_PRIVATE_FILESYSTEM_UNIX_PENDING_H0D04",
            "proofTerminal": "UNPROVED_H0D04",
            "proofBindingSha256": None,
            "endpoints": [{
                "path": "/dev/socket/property_service",
                "namespaceScope": "NATIVE_GLOBAL",
                "backingClass": "INHERITED_NATIVE_FILESYSTEM_SOCKET",
                "abstract": False,
                "scmRights": True,
                "inherited": True,
            }],
        }

    cases.append((
        "native-global-property-service",
        "Expose or inherit the native property-service endpoint.",
        global_property_service,
        {"GLOBAL_OR_CAPABILITY_PROPERTY_ENDPOINT_FORBIDDEN"},
    ))

    def extra_field(value: dict[str, Any]) -> None:
        value["unreviewedException"] = True

    cases.append((
        "unknown-authority-exception-field",
        "Add an unreviewed exception to the exact declaration schema.",
        extra_field,
        {"SCHEMA_KEY_MISMATCH"},
    ))

    rendered = []
    for case_id, description, mutate, expected in cases:
        value = copy.deepcopy(base)
        mutate(value)
        result = validate_surface_contract(value)
        if result["surfacePolicySatisfied"] or not expected.issubset(result["findingCodes"]):
            raise ValueError(f"WP2-2 negative corpus failed: {case_id}")
        rendered.append({
            "caseId": case_id,
            "mutation": description,
            "expectedFindingCodes": sorted(expected),
            "actualFindingCodes": result["findingCodes"],
            "expectedOutcome": "REJECTED_FORBIDDEN_OR_MALFORMED_SURFACE",
        })
    return rendered


def _private_pending_examples(base: dict[str, Any]) -> list[dict[str, Any]]:
    binder = copy.deepcopy(base)
    binder["binderSurface"] = {
        "endpointMode": "CAPSULE_PRIVATE_BINDERFS_PENDING_H0D05",
        "proofTerminal": "UNPROVED_H0D05",
        "proofBindingSha256": None,
        "endpoints": [
            _binder_endpoint(
                "/run/a90-wlan-capsule/binderfs/binder",
                "FRESH_CAPSULE_PRIVATE_BINDERFS", None, None, "CAPSULE_PRIVATE",
            )
        ],
    }
    prop = copy.deepcopy(base)
    prop["propertyService"] = {
        "endpointMode": "CAPSULE_PRIVATE_FILESYSTEM_UNIX_PENDING_H0D04",
        "proofTerminal": "UNPROVED_H0D04",
        "proofBindingSha256": None,
        "endpoints": [{
            "path": "/run/a90-wlan-capsule/dev/socket/property_service",
            "namespaceScope": "CAPSULE_PRIVATE",
            "backingClass": "FRESH_CAPSULE_PRIVATE_FILESYSTEM_SOCKET",
            "abstract": False,
            "scmRights": False,
            "inherited": False,
        }],
    }
    return [
        {
            "exampleId": "private-binderfs-still-unproved",
            "declaration": binder,
            "validation": validate_surface_contract(binder),
        },
        {
            "exampleId": "private-property-service-still-unproved",
            "declaration": prop,
            "validation": validate_surface_contract(prop),
        },
    ]


def _execution_economy(design: dict[str, Any]) -> dict[str, Any]:
    baseline_variants = len(
        design["baselineFormation"]["serviceManagerPlacementVariants"]
    )
    removals = len(design["ablationUnits"])
    promotion_requalifications = removals
    property_terminals = len(design["propertyExperiments"])
    total = baseline_variants + removals + promotion_requalifications + property_terminals
    if (baseline_variants, removals, promotion_requalifications, property_terminals, total) != (2, 13, 13, 2, 30):
        raise ValueError("WP2-2 execution-economy derivation drift")
    return {
        "classification": "H0_PLANNING_ESTIMATE_NOT_LIVE_BUDGET_OR_AUTHORITY",
        "logicalFutureUnitProjection": {
            "correctedBaselineVariantAttemptsMax": baseline_variants,
            "oneRoleRemovalUnits": removals,
            "successfulRemovalFreshBaselineRequalificationsMax": promotion_requalifications,
            "mutuallyExclusivePropertyTerminalAttemptsMax": property_terminals,
            "oneToOneSerialUnitProjection": total,
            "formula": "2 + 13 + 13 + 2 = 30",
        },
        "seriality": {
            "parallelExecutionAllowed": False,
            "reason": "Each removal branches from one exact healthy G_N; a supported removal requires a fresh G_N_PLUS_1 baseline before another removal.",
        },
        "calibration": {
            "wp2_2HostOnlyDeviceOrdinalConsumed": 0,
            "exactAttendedSessionCount": "UNPROVED_UNTIL_WP2_5B_EXECUTION_PROCESS_EXISTS",
            "exactOrdinalBudget": "UNSET_BLOCKS_EXECUTION_QUALIFICATION",
            "oneToOneInterpretation": "If each logical unit maps to one attended no-replay session, the current maximum projection is 30; the implementation may require more than one attended session per logical unit.",
            "performancePassBudgets": "SEPARATE_AND_STILL_UNSET_PENDING_MEASURED_CORRECTED_G0",
            "operatorAcceptanceRequiredBeforeExecutionQualification": True,
        },
        "resultScope": {
            "claim": "ORDER_CONDITIONED_REDUCED_GENERATION_ONLY",
            "globalMinimumProved": False,
            "terminalOneMinimalProved": False,
            "reason": "Earlier refuted removals are not retested after later successful removals; non-monotonic interactions remain possible.",
            "terminalRetestSweepIncludedInThirty": False,
        },
        "earlyStopValue": [
            {"after": "CORRECTED_G0", "retainedEvidence": "One manager placement can form a corrected healthy baseline; no role minimality follows."},
            {"after": "A4_CNSS_DIAG", "retainedEvidence": "The first scoped diagnostic-role necessity result remains generation-bound."},
            {"after": "A5_A6_MANAGER_PROVIDER", "retainedEvidence": "Scoped Binder manager/provider removal results remain generation-bound."},
            {"after": "A7_QRTR_PD_RFS", "retainedEvidence": "Scoped QRTR, PD, storage, and firmware-serving results remain generation-bound."},
            {"after": "A8_A10_CNSS_HOLDER_SHIM", "retainedEvidence": "Scoped CNSS, modem-holder, and property-write-shim results remain generation-bound."},
            {"after": "A11_PROPERTY_TERMINAL", "retainedEvidence": "One exact property absence or finite-seed terminal may be frozen if independently proved."},
        ],
        "stopRule": "Stopping early preserves only completed exact-generation results. It never grants a global necessity claim, Option C eligibility, or permission to skip remaining H0D gates.",
    }


def build_policy() -> dict[str, Any]:
    inputs = _load_inputs()
    _require_source_contract(inputs)
    parent = inputs["parent"]
    design = inputs["design"]
    early = _reference_surface(parent, "B0_EARLY_PAIR")
    adjacent = _reference_surface(parent, "B0_PROVIDER_ADJACENT_PAIR")
    early_result = validate_surface_contract(early)
    adjacent_result = validate_surface_contract(adjacent)
    if not early_result["surfacePolicySatisfied"] or not adjacent_result["surfacePolicySatisfied"]:
        raise ValueError("WP2-2 corrected reference variants must satisfy static guards")
    return {
        "schema": POLICY_SCHEMA,
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
        "status": {
            "wp2_2": "COMPLETE_H0_STATIC_POLICY_AND_NEGATIVE_CORPUS_ONLY",
            "currentH24": "REJECTED_AS_CORRECTED_BASELINE_BY_STATIC_SOURCE_EVIDENCE",
            "futureByteDerivationConsumer": "ABSENT",
            "correctedHealthyBaseline": "ABSENT_UNPROVED",
            "dependencyGatesRetired": [],
            "executionImplementation": "ABSENT",
            "executionQualification": "ABSENT",
            "independentExecutionReview": "ABSENT",
            "optionC": "BLOCKED_RESEARCH_ONLY",
        },
        "sourcePins": [_source_pin(rel) for rel in PINNED_INPUTS],
        "currentH24SourceDisposition": {
            "sourceReachableHazards": [
                "DUPLICATE_SERVICEMANAGER_AND_HWSERVICEMANAGER_CONSTRUCTION",
                "GLOBAL_SELINUXFS_RW_BIND_POLICY_LOAD_AND_ENFORCE_WRITE",
                "NATIVE_GLOBAL_BINDER_CHARDEV_MATERIALIZATION_10_79_80_81",
                "SD_WHOLE_PROPERTY_SNAPSHOT_AND_ACCEPTED_CACHE_RELOCATION_CLASS",
            ],
            "h24LiveExecutionOfSelectedRoute": False,
            "liveEffectClaim": "UNPROVED_H24_D1_STOPPED_BEFORE_WIFI_HELPER_ROUTE",
            "baselineAdmissible": False,
        },
        "policyBoundary": {
            "appliesTo": [
                "future-corrected-baseline-input",
                "future-reduced-native-backend-input",
                "future-debian-supervised-capsule-input",
            ],
            "forbidden": [
                "duplicate-servicemanager-or-hwservicemanager-role",
                "different-component-digests-across-construction-order-health-cleanup-evidence",
                "global-selinuxfs-rw-bind-load-write-or-enforce-write",
                "native-global-binder-path-backing-rdev-or-namespace",
                "sd-path-whole-property-snapshot-or-relocated-private-snapshot-provenance",
                "native-global-inherited-abstract-or-scm-rights-property-service-endpoint",
            ],
            "conditionalNotProved": [
                "fresh-capsule-private-binderfs-requires-H0D05-bound-proof",
                "fresh-capsule-private-filesystem-property-service-requires-H0D04-bound-proof",
            ],
            "consumerRequirement": "A future qualified byte-derived extractor must produce this exact declaration from the complete linked candidate/config/input closure. A hand-authored declaration is never execution evidence.",
        },
        "referenceVariants": [
            {"variantId": "B0_EARLY_PAIR", "declaration": early, "validation": early_result},
            {"variantId": "B0_PROVIDER_ADJACENT_PAIR", "declaration": adjacent, "validation": adjacent_result},
        ],
        "conditionalPrivateSurfaceExamples": _private_pending_examples(early),
        "negativeCorpus": _negative_cases(early),
        "executionEconomy": _execution_economy(design),
        "remainingGates": {
            "H0D01ThroughH0D10": "ALL_UNPROVED",
            "wp2_3": "NOT_STARTED",
            "wp2_4": "NOT_STARTED",
            "wp2_5b": "ABSENT_UNAUTHORIZED",
            "optionCImplementation": "BLOCKED",
        },
    }


def canonical_text() -> str:
    return json.dumps(build_policy(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", type=Path, metavar="PATH")
    group.add_argument("--write", type=Path, nargs="?", const=DEFAULT_OUTPUT, metavar="PATH")
    args = parser.parse_args()
    rendered = canonical_text()
    if args.check is not None:
        if args.check.read_text() != rendered:
            raise SystemExit(f"policy drift: {args.check}")
        return 0
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered)
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
