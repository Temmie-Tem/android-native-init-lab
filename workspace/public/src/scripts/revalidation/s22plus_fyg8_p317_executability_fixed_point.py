#!/usr/bin/env python3
"""Derive the P3.17 executable device/module fixed point from exact inputs.

Host-only.  The extractor merges the two applicable FYG8 vendor DT bases with
the active revision-12 overlay, applies the fixed kernel's fw_devlink parser
table, device-instantiation rules, and the source-bound GENI wrapper reference,
then maps the converged node set to the predecessor P3.16 module plan.  It does
not contact a device and it does not make P3.17 candidate-ready.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_s22plus_v3435_ramoops_console_dtbo as stock_dt  # noqa: E402
from build_s22plus_ramoops_vendor_boot_enable import iter_fdt_blobs  # noqa: E402
import s22plus_fyg8_p225_guard_poc_flush_contract as p225  # noqa: E402
import s22plus_fyg8_p317_fw_devlink_contract as fw  # noqa: E402
import s22plus_fyg8_p317_must_bind_claim_contract as claims  # noqa: E402
import s22plus_o2_module_plan as module_plan  # noqa: E402


SCHEMA = "s22plus_fyg8_p317_executability_fixed_point_v1"
VERDICT = "PASS_P317_EXECUTABILITY_FIXED_POINT_H0_RUNTIME_PENDING"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

DEFAULT_DTBO = p225.DEFAULT_DTBO
DEFAULT_VENDOR_DTB = p225.DEFAULT_VENDOR_DTB
DEFAULT_FDTOVERLAY = p225.DEFAULT_FDTOVERLAY
DEFAULT_LIBFDT = p225.DEFAULT_LIBFDT
DEFAULT_PROPERTY_SOURCE = fw.DEFAULT_PROPERTY_SOURCE
DEFAULT_CORE_SOURCE = fw.DEFAULT_CORE_SOURCE
DEFAULT_OF_BASE_SOURCE = fw.DEFAULT_OF_BASE_SOURCE
DEFAULT_IRQ_SOURCE = (
    claims.DEFAULT_KERNEL_ROOT / "common/drivers/of/irq.c"
)
DEFAULT_RPMH_SOURCE = (
    claims.DEFAULT_KERNEL_ROOT / "common/drivers/soc/qcom/rpmh-rsc.c"
)
DEFAULT_RPMH_REGULATOR_SOURCE = (
    claims.DEFAULT_KERNEL_ROOT
    / "msm-kernel/drivers/regulator/rpmh-regulator.c"
)
DEFAULT_CONFIG = Path(
    "workspace/private/outputs/s22plus_fyg8_p310/immutable-a-v6/.config"
)
DEFAULT_METADATA = module_plan.DEFAULT_METADATA_DIR
DEFAULT_PREDECESSOR = Path(
    "workspace/private/outputs/s22plus_fyg8_p316/"
    "candidate-b/artifact-result.json"
)
DEFAULT_MUST_BIND_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/"
    "must-bind-claim-contract-20260812-01.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/"
    "executability-fixed-point-20260812-01.json"
)

CONFIG_SHA256 = "6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b"
PREDECESSOR_SHA256 = "567987e49cac251d44a0f0c255eb0659b3c5057ca4707cd2343342b913432f2f"
PREDECESSOR_CLOSURE_SHA256 = "c5ee3245957a15d58f91e9a61fa5752f98f0c5f5d0b17f1239c9a0d675b08ef7"
PREDECESSOR_EARLY_COUNT = 64
PREDECESSOR_EFFECTIVE_COUNT = 65
ACTIVE_OVERLAY_INDEX = p225.ACTIVE_OVERLAY_INDEX
APPLICABLE_BASES = p225.APPLICABLE_BASES

ROOT_PATHS = (
    "/soc/qcom,qupv3_0_geni_se@9c0000",
    "/soc/i2c@994000",
    "/soc/i2c@994000/max77705@66",
)
EXPECTED_STATIC_NODE_COUNT = 23
EXPECTED_NEW_MODULES = (
    "spmi-pmic-arb.ko",
    "pinctrl-spmi-gpio.ko",
    "qti-regmap-debugfs.ko",
    "regmap-spmi.ko",
    "qcom-spmi-pmic.ko",
)
EXPECTED_SUCCESSOR_EARLY_COUNT = 69
EXPECTED_SUCCESSOR_EFFECTIVE_COUNT = 70
INSERT_BEFORE_MODULE = "msm-geni-se.ko"

BUILTIN_COMPAT_CONFIG = {
    "arm,gic-v3": "CONFIG_ARM_GIC_V3=y",
    "arm,psci-1.0": "CONFIG_ARM_PSCI_FW=y",
    "fixed-clock": "CONFIG_COMMON_CLK=y",
}
SOURCE_BOUND_MODULES = {
    "qcom,qupv3-geni-se": "msm-geni-se.ko",
    "qcom,rpmh-arc-regulator": "rpmh-regulator.ko",
}
CUSTOM_LATE_COMPAT = "maxim,max77705"
CUSTOM_LATE_MODULE = "s22plus_max77705_mux_diag.ko"

FAMILY_FW = "FW_DEVLINK_DT_SUPPLIER_CLOSURE"
FAMILY_INST = "DEVICE_INSTANTIATION_CLOSURE"
FAMILY_DRIVER = "DRIVER_CONSUMED_DT_REFERENCE_CLOSURE"
FAMILIES = (FAMILY_FW, FAMILY_INST, FAMILY_DRIVER)


class FixedPointError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise FixedPointError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise FixedPointError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise FixedPointError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise FixedPointError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require_sha(data: bytes, expected: str, label: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise FixedPointError(f"{label} identity changed: {actual} != {expected}")


def require_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise FixedPointError(f"{label} source contract missing: {missing}")


def _strings(raw: bytes, label: str) -> tuple[str, ...]:
    if not raw or raw[-1] != 0:
        raise FixedPointError(f"{label} is not a terminated string list")
    try:
        return tuple(part.decode("ascii") for part in raw[:-1].split(b"\0"))
    except UnicodeDecodeError as exc:
        raise FixedPointError(f"{label} contains non-ASCII text") from exc


def _cells(raw: bytes, label: str) -> tuple[int, ...]:
    if not raw or len(raw) % 4:
        raise FixedPointError(f"{label} is not a nonempty u32 cell list")
    return struct.unpack(f">{len(raw) // 4}I", raw)


@dataclass
class Node:
    path: str
    parent: "Node | None" = None
    properties: dict[str, bytes] = field(default_factory=dict)

    @property
    def compatible(self) -> tuple[str, ...]:
        raw = self.properties.get("compatible")
        return () if raw is None else _strings(raw, f"{self.path} compatible")

    @property
    def available(self) -> bool:
        raw = self.properties.get("status")
        if raw is None:
            return True
        values = _strings(raw, f"{self.path} status")
        return len(values) == 1 and values[0] in {"ok", "okay"}


@dataclass
class Tree:
    nodes: dict[str, Node]
    phandles: dict[int, Node]


def parse_tree(blob: bytes) -> Tree:
    roots = iter_fdt_blobs(blob)
    if len(roots) != 1 or roots[0].offset != 0 or roots[0].totalsize != len(blob):
        raise FixedPointError("merged DT is not one exact FDT")
    properties = stock_dt.parse_fdt_props(roots[0])
    paths = {"/"}
    for prop in properties:
        current = prop.path
        while current:
            paths.add(current)
            if current == "/":
                break
            current = current.rsplit("/", 1)[0] or "/"
    nodes = {path: Node(path=path) for path in sorted(paths)}
    for path, node in nodes.items():
        if path != "/":
            parent_path = path.rsplit("/", 1)[0] or "/"
            node.parent = nodes[parent_path]
    for prop in properties:
        node = nodes[prop.path]
        if prop.name in node.properties:
            raise FixedPointError(f"duplicate merged-DT property: {prop.path}:{prop.name}")
        node.properties[prop.name] = prop.value
    phandles: dict[int, Node] = {}
    for node in nodes.values():
        raw = node.properties.get("phandle") or node.properties.get("linux,phandle")
        if raw is None:
            continue
        values = _cells(raw, f"{node.path} phandle")
        if len(values) != 1 or values[0] == 0 or values[0] in phandles:
            raise FixedPointError(f"duplicate or malformed phandle at {node.path}")
        phandles[values[0]] = node
    return Tree(nodes=nodes, phandles=phandles)


def _is_ancestor(ancestor: Node, node: Node) -> bool:
    current: Node | None = node
    while current is not None:
        if current is ancestor:
            return True
        current = current.parent
    return False


def _compatible_owner_or_rejection(
    supplier: Node, consumer: Node
) -> tuple[Node | None, str | None]:
    current: Node | None = supplier
    while current is not None:
        if not current.available:
            return None, f"supplier_or_ancestor_unavailable:{current.path}"
        if current.compatible:
            if _is_ancestor(consumer, current):
                return None, f"consumer_self_or_descendant:{current.path}"
            return current, None
        current = current.parent
    return None, f"no_compatible_owner:{supplier.path}"


def _compatible_owner(supplier: Node, consumer: Node) -> Node:
    owner, rejection = _compatible_owner_or_rejection(supplier, consumer)
    if owner is None:
        raise FixedPointError(
            f"required direct dependency rejected by source gates: {rejection}"
        )
    return owner


def _parse_generic_phandles(
    tree: Tree, node: Node, property_name: str, rule: dict[str, Any]
) -> tuple[Node, ...]:
    raw = node.properties[property_name]
    values = _cells(raw, f"{node.path} {property_name}")
    suppliers: list[Node] = []
    index = 0
    while index < len(values):
        phandle = values[index]
        supplier = tree.phandles.get(phandle)
        if supplier is None:
            raise FixedPointError(
                f"{node.path} {property_name} unresolved phandle {phandle:#x}"
            )
        index += 1
        argument_count = 0
        cells_property = rule.get("cells_property")
        if cells_property is not None:
            raw_count = supplier.properties.get(cells_property)
            if raw_count is None:
                raise FixedPointError(
                    f"{supplier.path} lacks parser cells property {cells_property}"
                )
            counts = _cells(raw_count, f"{supplier.path} {cells_property}")
            if len(counts) != 1:
                raise FixedPointError(
                    f"{supplier.path} {cells_property} is not one count cell"
                )
            argument_count = counts[0]
        if index + argument_count > len(values):
            raise FixedPointError(
                f"{node.path} {property_name} lacks {argument_count} arguments"
            )
        index += argument_count
        suppliers.append(supplier)
    return tuple(suppliers)


def _irq_parent(tree: Tree, node: Node) -> Node:
    current: Node | None = node
    while current is not None:
        raw = current.properties.get("interrupt-parent")
        if raw is not None:
            values = _cells(raw, f"{current.path} interrupt-parent")
            if len(values) != 1 or values[0] not in tree.phandles:
                raise FixedPointError(f"malformed interrupt-parent at {current.path}")
            current = tree.phandles[values[0]]
        else:
            current = current.parent
        if current is not None and "#interrupt-cells" in current.properties:
            return current
    raise FixedPointError(f"{node.path} has interrupts without an IRQ parent")


def _parse_special_phandles(
    tree: Tree, node: Node, property_name: str, parser: str
) -> tuple[Node, ...]:
    values = _cells(node.properties[property_name], f"{node.path} {property_name}")
    if parser == "parse_iommu_maps":
        if len(values) % 4:
            raise FixedPointError(f"{node.path} iommu-map is not four-cell records")
        suppliers = []
        for index in range(1, len(values), 4):
            supplier = tree.phandles.get(values[index])
            if supplier is None:
                raise FixedPointError(f"{node.path} iommu-map phandle is unresolved")
            suppliers.append(supplier)
        return tuple(suppliers)
    if parser != "parse_interrupts":
        raise FixedPointError(f"unsupported special parser reached: {parser}")
    if property_name == "interrupts-extended":
        suppliers: list[Node] = []
        index = 0
        while index < len(values):
            supplier = tree.phandles.get(values[index])
            if supplier is None:
                raise FixedPointError(
                    f"{node.path} interrupts-extended phandle is unresolved"
                )
            index += 1
            counts = _cells(
                supplier.properties.get("#interrupt-cells", b""),
                f"{supplier.path} #interrupt-cells",
            )
            if len(counts) != 1 or index + counts[0] > len(values):
                raise FixedPointError(f"{node.path} interrupts-extended is malformed")
            index += counts[0]
            suppliers.append(supplier)
        return tuple(suppliers)
    parent = _irq_parent(tree, node)
    counts = _cells(
        parent.properties.get("#interrupt-cells", b""),
        f"{parent.path} #interrupt-cells",
    )
    if len(counts) != 1 or not counts[0] or len(values) % counts[0]:
        raise FixedPointError(f"{node.path} interrupts is malformed")
    return tuple(parent for _ in range(len(values) // counts[0]))


def fw_edges(
    tree: Tree,
    node: Node,
    rows: tuple[dict[str, Any], ...],
    rules: dict[str, dict[str, Any]],
    effective: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    current: Node | None = node
    while current is not None:
        if not current.available:
            raise FixedPointError(f"consumer path unavailable: {current.path}")
        current = current.parent
    effective_set = set(effective)
    edges: list[dict[str, Any]] = []
    for property_name in node.properties:
        matched = False
        for row in rows:
            parser = row["parse_prop"]
            if parser not in effective_set:
                continue
            rule = rules[parser]
            if not fw._rule_matches_property(rule, property_name):
                continue
            if rule.get("reject_consumer_property") in node.properties:
                break
            if parser in {"parse_iommu_maps", "parse_interrupts"}:
                suppliers = _parse_special_phandles(tree, node, property_name, parser)
            else:
                suppliers = _parse_generic_phandles(tree, node, property_name, rule)
            if not suppliers:
                continue
            matched = True
            for supplier in suppliers:
                owner, rejection = _compatible_owner_or_rejection(supplier, node)
                row = {
                    "family": FAMILY_FW,
                    "consumer": node.path,
                    "property": property_name,
                    "parser": parser,
                    "supplier_node": supplier.path,
                    "owner": None if owner is None else owner.path,
                    "owner_compatible": [] if owner is None else list(owner.compatible),
                    "kernel_link_created": owner is not None,
                    "kernel_link_rejection": rejection,
                    "runtime_early_device_gate": (
                        "NOT_APPLICABLE_REJECTED_STATIC_EDGE"
                        if owner is None
                        else "PENDING_LIVE_WITNESS"
                    ),
                }
                edges.append(row)
            break
        if matched:
            continue
    return tuple(edges)


def instantiation_edges(tree: Tree, node: Node) -> tuple[dict[str, Any], ...]:
    compatible = set(node.compatible)
    parent = node.parent
    if node.path == ROOT_PATHS[2]:
        if parent is None or "qcom,i2c-geni" not in parent.compatible:
            raise FixedPointError("exact Max77705 parent is not the target GENI I2C")
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": parent.path,
            "mechanism": "i2c_add_adapter_then_of_i2c_register_devices",
        },)
    if "qcom,pm8350c-gpio" in compatible:
        if parent is None or "qcom,spmi-pmic" not in parent.compatible:
            raise FixedPointError("PM8350C GPIO lacks its exact SPMI PMIC parent")
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": parent.path,
            "mechanism": "qcom_spmi_pmic_devm_of_platform_populate",
        },)
    if "qcom,spmi-pmic" in compatible:
        if parent is None or "qcom,spmi-pmic-arb" not in parent.compatible:
            raise FixedPointError("PM8350C PMIC lacks its exact SPMI controller parent")
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": parent.path,
            "mechanism": "spmi_controller_add_then_of_spmi_register_devices",
        },)
    if compatible & {"qcom,rpmh-arc-regulator", "qcom,waipio-rpmh-clk"}:
        if parent is None or "qcom,rpmh-rsc" not in parent.compatible:
            raise FixedPointError(f"RPMh child lacks exact RSC parent: {node.path}")
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": parent.path,
            "mechanism": "rpmh_rsc_devm_of_platform_populate",
        },)
    if node.path.startswith("/soc/clocks/") and "fixed-clock" in compatible:
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": "builtin:of_clk_init",
            "mechanism": "built_in_early_clock_provider",
        },)
    if node.path.startswith("/soc/") and node.path.count("/") == 2:
        return ({
            "family": FAMILY_INST,
            "consumer": node.path,
            "instantiator": "builtin:of_platform_default_populate",
            "mechanism": "arch_initcall_sync_default_platform_population",
        },)
    raise FixedPointError(f"unknown required device creator: {node.path}")


def driver_reference_edges(tree: Tree, node: Node) -> tuple[dict[str, Any], ...]:
    if "qcom,i2c-geni" not in node.compatible:
        return ()
    raw = node.properties.get("qcom,wrapper-core")
    if raw is None:
        raise FixedPointError("target GENI I2C lacks qcom,wrapper-core")
    values = _cells(raw, f"{node.path} qcom,wrapper-core")
    if len(values) != 1 or values[0] not in tree.phandles:
        raise FixedPointError("target GENI wrapper reference is malformed")
    owner = _compatible_owner(tree.phandles[values[0]], node)
    if "qcom,qupv3-geni-se" not in owner.compatible:
        raise FixedPointError("target GENI wrapper reference resolves elsewhere")
    return ({
        "family": FAMILY_DRIVER,
        "consumer": node.path,
        "property": "qcom,wrapper-core",
        "dependency": owner.path,
        "dependency_compatible": list(owner.compatible),
        "mechanism": "driver_of_parse_phandle_then_geni_se_resources_init",
    },)


def derive_fixed_point(
    tree: Tree,
    rows: tuple[dict[str, Any], ...],
    rules: dict[str, dict[str, Any]],
    effective: tuple[str, ...],
) -> dict[str, Any]:
    missing = [path for path in ROOT_PATHS if path not in tree.nodes]
    if missing:
        raise FixedPointError(f"must-bind roots missing from merged DT: {missing}")
    seen = set(ROOT_PATHS)
    frontier = list(ROOT_PATHS)
    all_edges: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []
    while frontier:
        emitted: set[str] = set()
        family_evaluations: list[dict[str, Any]] = []
        iteration_edges: list[dict[str, Any]] = []
        for path in sorted(frontier):
            node = tree.nodes[path]
            outputs = {
                FAMILY_FW: fw_edges(tree, node, rows, rules, effective),
                FAMILY_INST: instantiation_edges(tree, node),
                FAMILY_DRIVER: driver_reference_edges(tree, node),
            }
            for family in FAMILIES:
                edges = outputs[family]
                family_evaluations.append(
                    {"node": path, "family": family, "edge_count": len(edges)}
                )
                for edge in edges:
                    iteration_edges.append(edge)
                    target = edge.get("owner") or edge.get("instantiator") or edge.get("dependency")
                    if isinstance(target, str) and target.startswith("/"):
                        if target not in tree.nodes:
                            raise FixedPointError(f"relationship escaped exact DT: {target}")
                        if target not in seen:
                            emitted.add(target)
        iterations.append(
            {
                "index": len(iterations),
                "frontier": sorted(frontier),
                "family_evaluations": family_evaluations,
                "raw_edges": iteration_edges,
                "new_nodes": sorted(emitted),
            }
        )
        all_edges.extend(iteration_edges)
        seen.update(emitted)
        frontier = sorted(emitted)
        if len(iterations) > len(tree.nodes):
            raise FixedPointError("fixed-point iteration did not converge")
    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in all_edges:
        target = edge.get("owner") or edge.get("instantiator") or edge.get("dependency")
        rejected_identity = (
            f"rejected:{edge.get('property')}:{edge.get('supplier_node')}"
            if target is None
            else str(target)
        )
        key = (edge["family"], edge["consumer"], rejected_identity)
        current = dedup.get(key)
        if current is None:
            stored = copy.deepcopy(edge)
            stored["raw_evidence_count"] = 1
            stored["raw_properties"] = [edge["property"]] if "property" in edge else []
            dedup[key] = stored
        else:
            current["raw_evidence_count"] += 1
            if "property" in edge and edge["property"] not in current["raw_properties"]:
                current["raw_properties"].append(edge["property"])
    result = {
        "roots": list(ROOT_PATHS),
        "relationship_families": list(FAMILIES),
        "iteration_count": len(iterations),
        "iterations": iterations,
        "node_count": len(seen),
        "nodes": sorted(seen),
        "raw_edge_count": len(all_edges),
        "deduplicated_edge_count": len(dedup),
        "deduplicated_edges": [dedup[key] for key in sorted(dedup)],
        "converged": True,
        "every_frontier_node_evaluated_by_every_family": all(
            len(row["family_evaluations"]) == len(row["frontier"]) * len(FAMILIES)
            for row in iterations
        ),
    }
    if result["node_count"] != EXPECTED_STATIC_NODE_COUNT:
        raise FixedPointError(
            f"exact static node count drifted: {result['node_count']} != "
            f"{EXPECTED_STATIC_NODE_COUNT}: {result['nodes']}"
        )
    if not result["every_frontier_node_evaluated_by_every_family"]:
        raise FixedPointError("one family skipped a fixed-point frontier node")
    return result


def _module_for_node(
    node: Node, metadata: module_plan.ModuleMetadata, config_text: str
) -> dict[str, Any]:
    if CUSTOM_LATE_COMPAT in node.compatible:
        return {
            "kind": "custom_late_module",
            "module": CUSTOM_LATE_MODULE,
            "compatible": CUSTOM_LATE_COMPAT,
        }
    for compatible in node.compatible:
        expected_config = BUILTIN_COMPAT_CONFIG.get(compatible)
        if expected_config is not None:
            if expected_config not in config_text:
                raise FixedPointError(f"built-in config missing for {compatible}")
            return {
                "kind": "built_in",
                "config": expected_config,
                "compatible": compatible,
            }
        source_module = SOURCE_BOUND_MODULES.get(compatible)
        if source_module is not None:
            if source_module not in metadata.hard_deps:
                raise FixedPointError(f"source-bound module unavailable: {source_module}")
            return {
                "kind": "source_bound_stock_module",
                "module": source_module,
                "compatible": compatible,
            }
        alias = f"of:N*T*C{compatible}"
        targets = metadata.aliases.get(alias, ())
        if len(targets) == 1:
            return {
                "kind": "modules_alias",
                "module": targets[0],
                "compatible": compatible,
                "alias": alias,
            }
        if len(targets) > 1:
            raise FixedPointError(f"ambiguous module alias: {alias} -> {targets}")
    raise FixedPointError(
        f"no exact built-in/module authority for {node.path}: {node.compatible}"
    )


def derive_module_delta(
    tree: Tree,
    fixed_point: dict[str, Any],
    metadata: module_plan.ModuleMetadata,
    config_text: str,
    predecessor: dict[str, Any],
) -> dict[str, Any]:
    closure = predecessor.get("module_closure")
    if not isinstance(closure, dict):
        raise FixedPointError("P3.16 predecessor lacks module_closure")
    predecessor_files = closure.get("files")
    if (
        closure.get("count") != PREDECESSOR_EARLY_COUNT
        or closure.get("closure_sha256") != PREDECESSOR_CLOSURE_SHA256
        or not isinstance(predecessor_files, list)
        or len(predecessor_files) != PREDECESSOR_EARLY_COUNT
        or len(set(predecessor_files)) != len(predecessor_files)
    ):
        raise FixedPointError("P3.16 predecessor module closure drifted")
    mappings = []
    for path in fixed_point["nodes"]:
        mappings.append({"node": path, **_module_for_node(tree.nodes[path], metadata, config_text)})
    required_stock = sorted(
        {row["module"] for row in mappings if row["kind"] not in {"built_in", "custom_late_module"}}
    )
    plan = module_plan.build_plan(metadata, required_stock)
    predecessor_set = set(predecessor_files)
    additions = [name for name in plan.modules if name not in predecessor_set]
    if tuple(additions) != EXPECTED_NEW_MODULES:
        raise FixedPointError(f"P3.17 module delta drifted: {additions}")
    insertion_index = predecessor_files.index(INSERT_BEFORE_MODULE)
    successor_early = (
        predecessor_files[:insertion_index]
        + additions
        + predecessor_files[insertion_index:]
    )
    positions = {name: index for index, name in enumerate(successor_early)}
    violations = [
        constraint
        for constraint in plan.constraints
        if positions[constraint["before"]] >= positions[constraint["after"]]
    ]
    if violations:
        raise FixedPointError(f"successor insertion violates module metadata: {violations}")
    if [name for name in successor_early if name in predecessor_set] != predecessor_files:
        raise FixedPointError("successor module plan reordered the P3.16 predecessor")
    if len(successor_early) != EXPECTED_SUCCESSOR_EARLY_COUNT:
        raise FixedPointError("successor early module count drifted")
    return {
        "predecessor_early_count": PREDECESSOR_EARLY_COUNT,
        "predecessor_effective_count_with_late_diagnostic": PREDECESSOR_EFFECTIVE_COUNT,
        "required_node_module_mappings": mappings,
        "required_stock_modules": required_stock,
        "dependency_plan_modules": list(plan.modules),
        "dependency_constraints": list(plan.constraints),
        "added_early_modules": additions,
        "added_early_module_count": len(additions),
        "insertion_before": INSERT_BEFORE_MODULE,
        "insertion_index": insertion_index,
        "predecessor_order_preserved_as_subsequence": True,
        "successor_early_modules": successor_early,
        "successor_early_count": len(successor_early),
        "late_custom_module": CUSTOM_LATE_MODULE,
        "early_vs_effective_contract": {
            "early_module_count": EXPECTED_SUCCESSOR_EARLY_COUNT,
            "early_loop_excludes": CUSTOM_LATE_MODULE,
            "late_load_stage": (
                "after all early modules, gadget-path readiness, and "
                "Process-v2 sidecar arming"
            ),
            "late_load_operation": "one dedicated synchronous finit_module",
            "effective_count_includes_late_module": True,
        },
        "successor_effective_total_count": len(successor_early) + 1,
        "effective_count_delta": (
            f"{PREDECESSOR_EFFECTIVE_COUNT}->{len(successor_early) + 1}"
        ),
    }


def _canonical_static_result(result: dict[str, Any]) -> bytes:
    selected = {
        "fixed_point": result["fixed_point"],
        "node_module_kinds": [
            (row["node"], row["kind"], row.get("module"), row.get("config"))
            for row in result["module_delta"]["required_node_module_mappings"]
        ],
        "added": result["module_delta"]["added_early_modules"],
        "successor": result["module_delta"]["successor_early_modules"],
    }
    return json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()


def merge_applicable_bases(
    *, dtbo: bytes, vendor_dtb: bytes, fdtoverlay: Path, libfdt: Path
) -> tuple[dict[str, Any], ...]:
    header, entries = stock_dt.parse_dt_table(dtbo)
    if header.entry_count != 11 or len(entries) != 11:
        raise FixedPointError("stock DTBO entry count changed")
    overlay = stock_dt.entry_blob(dtbo, entries[ACTIVE_OVERLAY_INDEX])
    require_sha(overlay, p225.ACTIVE_OVERLAY_SHA256, "active rev12 overlay")
    roots = iter_fdt_blobs(vendor_dtb)
    selected = [root for root in roots if root.index in APPLICABLE_BASES]
    if [root.index for root in selected] != sorted(APPLICABLE_BASES):
        raise FixedPointError("applicable vendor DT base set changed")
    outputs = []
    with tempfile.TemporaryDirectory(prefix="s22plus-p317-fixed-point-") as temp_name:
        temp = Path(temp_name)
        library = temp / "lib"
        library.mkdir()
        (library / "libfdt.so.1").symlink_to(libfdt)
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = str(library)
        overlay_file = temp / "active-rev12.dtbo"
        overlay_file.write_bytes(overlay)
        for root_blob in selected:
            model, expected_sha = APPLICABLE_BASES[root_blob.index]
            require_sha(root_blob.data, expected_sha, f"vendor base {root_blob.index}")
            base_file = temp / f"base-{root_blob.index}.dtb"
            merged_file = temp / f"merged-{root_blob.index}.dtb"
            base_file.write_bytes(root_blob.data)
            completed = subprocess.run(
                [
                    str(fdtoverlay), "-i", str(base_file), "-o",
                    str(merged_file), str(overlay_file),
                ],
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=45,
                check=False,
            )
            if completed.returncode != 0:
                raise FixedPointError(
                    f"overlay merge failed for base {root_blob.index}: "
                    f"{completed.stdout[-1000:]}"
                )
            merged = merged_file.read_bytes()
            root_model = _strings(
                stock_dt.property_map(merged).get(("/", "model"), b""),
                f"base {root_blob.index} model",
            )
            if root_model != (model,):
                raise FixedPointError(f"merged base {root_blob.index} model changed")
            outputs.append(
                {
                    "base_index": root_blob.index,
                    "base_model": model,
                    "base": receipt(root_blob.data),
                    "overlay": receipt(overlay),
                    "merged": receipt(merged),
                    "blob": merged,
                }
            )
    return tuple(outputs)


def validate_must_bind_receipt(data: bytes) -> dict[str, Any]:
    try:
        result = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixedPointError("must-bind receipt is not canonical JSON") from exc
    if result.get("schema") != claims.SCHEMA:
        raise FixedPointError("must-bind receipt schema differs")
    if result.get("claim_authority_sha256") != claims.CLAIM_AUTHORITY_SHA256:
        raise FixedPointError("must-bind claim authority differs")
    if result.get("human_causal_review") != claims.HUMAN_CAUSAL_REVIEW:
        raise FixedPointError("corrected must-bind authority review state differs")
    source_receipt = result.get("authority", {}).get("extractor_source")
    current_source = stable_read(
        Path(claims.__file__).resolve(), "must-bind extractor", 2 * 1024 * 1024
    )
    if source_receipt != receipt(current_source):
        raise FixedPointError("must-bind receipt is stale relative to its extractor")
    return result


def audit_sources(
    property_text: str,
    core_text: str,
    of_base_text: str,
    irq_text: str,
    rpmh_text: str,
    rpmh_regulator_text: str,
    config_text: str,
) -> tuple[tuple[dict[str, Any], ...], dict[str, dict[str, Any]], tuple[str, ...], dict[str, Any]]:
    rows = fw.parse_supplier_bindings(property_text)
    rules = fw.parse_macro_parser_rules(property_text)
    if set(rules) != {row["parse_prop"] for row in rows}:
        raise FixedPointError("fw_devlink parser-rule coverage differs")
    core = fw.audit_core_semantics(core_text, of_base_text)
    effective = fw.effective_parser_rows(
        rows,
        mode="on",
        strict=True,
        mode_assignments=core["mode_assignments"],
    )
    if len(effective) != fw.EXPECTED_BINDING_COUNT:
        raise FixedPointError("default on+strict policy does not enable all parsers")
    require_tokens(
        property_text,
        "special fw_devlink parsers",
        (
            "return of_parse_phandle(np, prop_name, (index * 4) + 1);",
            "return of_irq_parse_one(np, index, &sup_args) ? NULL : sup_args.np;",
        ),
    )
    require_tokens(
        irq_text,
        "OF IRQ parent resolution",
        (
            "struct device_node *of_irq_find_parent(struct device_node *child)",
            'of_property_read_u32(child, "interrupt-parent", &parent)',
            'of_get_property(p, "#interrupt-cells", NULL)',
        ),
    )
    require_tokens(
        rpmh_text,
        "RPMh RSC instantiation",
        (
            'static const struct of_device_id rpmh_drv_match[] =',
            '{ .compatible = "qcom,rpmh-rsc", },',
            "return devm_of_platform_populate(&pdev->dev);",
        ),
    )
    require_tokens(
        rpmh_regulator_text,
        "RPMh regulator source mapping",
        (
            '.compatible = "qcom,rpmh-arc-regulator"',
            ".of_match_table\t= rpmh_regulator_match_table",
            "arch_initcall(rpmh_regulator_init);",
        ),
    )
    for value in ("CONFIG_OF=y", "CONFIG_SPMI=y", *BUILTIN_COMPAT_CONFIG.values()):
        if value not in config_text:
            raise FixedPointError(f"fixed Image config lacks {value}")
    return rows, rules, effective, core


def build_contract(
    *,
    extractor_data: bytes,
    dtbo_data: bytes,
    vendor_dtb_data: bytes,
    property_data: bytes,
    core_data: bytes,
    of_base_data: bytes,
    irq_data: bytes,
    rpmh_data: bytes,
    rpmh_regulator_data: bytes,
    config_data: bytes,
    predecessor_data: bytes,
    must_bind_data: bytes,
    metadata: module_plan.ModuleMetadata,
    fdtoverlay: Path,
    libfdt: Path,
) -> dict[str, Any]:
    require_sha(config_data, CONFIG_SHA256, "fixed Image .config")
    require_sha(predecessor_data, PREDECESSOR_SHA256, "P3.16 predecessor")
    must_bind = validate_must_bind_receipt(must_bind_data)
    try:
        predecessor = json.loads(predecessor_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixedPointError("P3.16 predecessor is not JSON") from exc
    rows, rules, effective, core = audit_sources(
        property_data.decode("utf-8"),
        core_data.decode("utf-8"),
        of_base_data.decode("utf-8"),
        irq_data.decode("utf-8"),
        rpmh_data.decode("utf-8"),
        rpmh_regulator_data.decode("utf-8"),
        config_data.decode("utf-8"),
    )
    merged = merge_applicable_bases(
        dtbo=dtbo_data,
        vendor_dtb=vendor_dtb_data,
        fdtoverlay=fdtoverlay,
        libfdt=libfdt,
    )
    base_results = []
    for base in merged:
        tree = parse_tree(base["blob"])
        fixed_point = derive_fixed_point(tree, rows, rules, effective)
        module_delta = derive_module_delta(
            tree,
            fixed_point,
            metadata,
            config_data.decode("utf-8"),
            predecessor,
        )
        base_results.append(
            {
                **{key: value for key, value in base.items() if key != "blob"},
                "fixed_point": fixed_point,
                "module_delta": module_delta,
            }
        )
    canonical = [_canonical_static_result(row) for row in base_results]
    if len(set(canonical)) != 1:
        raise FixedPointError("applicable vendor DT bases produce different closures")
    shared = base_results[0]
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "status": "CANDIDATE_NOT_READY",
        "authority": {
            "extractor_source": receipt(extractor_data),
            "dtbo": receipt(dtbo_data),
            "vendor_dtb": receipt(vendor_dtb_data),
            "fdtoverlay": receipt(stable_read(fdtoverlay, "fdtoverlay", 4 * 1024 * 1024)),
            "libfdt": receipt(stable_read(libfdt, "libfdt", 4 * 1024 * 1024)),
            "of_property_source": receipt(property_data),
            "driver_core_source": receipt(core_data),
            "of_base_source": receipt(of_base_data),
            "of_irq_source": receipt(irq_data),
            "rpmh_rsc_source": receipt(rpmh_data),
            "rpmh_regulator_source": receipt(rpmh_regulator_data),
            "fixed_image_config": receipt(config_data),
            "predecessor_artifact": receipt(predecessor_data),
            "must_bind_receipt": receipt(must_bind_data),
            "module_metadata": metadata.metadata_hashes,
        },
        "must_bind": {
            "claim_authority_sha256": must_bind["claim_authority_sha256"],
            "human_causal_review": must_bind["human_causal_review"],
        },
        "fw_devlink_policy": {
            "source_default_mode": core["source_default_mode"],
            "source_default_strict": core["source_default_strict"],
            "effective_parser_count": len(effective),
            "runtime_boot_mode_and_strict_witness": "PENDING",
        },
        "applicable_base_count": len(base_results),
        "applicable_bases": base_results,
        "applicable_bases_static_closure_identical": True,
        "fixed_point": shared["fixed_point"],
        "module_delta": shared["module_delta"],
        "remaining_gates": [
            "runtime_fw_devlink_mode_and_strict_witness",
            "runtime_early_device_gate_witness",
            "retained_waiting_for_supplier_and_binding_witness",
            "successor_packaging_and_process_v2_requalification",
        ],
        "safety": {
            "device_contact": False,
            "device_commands": 0,
            "a90_commands": 0,
            "boot_payload_created": False,
            "live_authority": False,
        },
    }


def encode_contract(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtbo", type=Path, default=root / DEFAULT_DTBO)
    parser.add_argument("--vendor-dtb", type=Path, default=root / DEFAULT_VENDOR_DTB)
    parser.add_argument("--fdtoverlay", type=Path, default=root / DEFAULT_FDTOVERLAY)
    parser.add_argument("--libfdt", type=Path, default=root / DEFAULT_LIBFDT)
    parser.add_argument("--property-source", type=Path, default=root / DEFAULT_PROPERTY_SOURCE)
    parser.add_argument("--core-source", type=Path, default=root / DEFAULT_CORE_SOURCE)
    parser.add_argument("--of-base-source", type=Path, default=root / DEFAULT_OF_BASE_SOURCE)
    parser.add_argument("--irq-source", type=Path, default=root / DEFAULT_IRQ_SOURCE)
    parser.add_argument("--rpmh-source", type=Path, default=root / DEFAULT_RPMH_SOURCE)
    parser.add_argument(
        "--rpmh-regulator-source", type=Path,
        default=root / DEFAULT_RPMH_REGULATOR_SOURCE,
    )
    parser.add_argument("--config", type=Path, default=root / DEFAULT_CONFIG)
    parser.add_argument("--metadata", type=Path, default=root / DEFAULT_METADATA)
    parser.add_argument("--predecessor", type=Path, default=root / DEFAULT_PREDECESSOR)
    parser.add_argument("--must-bind", type=Path, default=root / DEFAULT_MUST_BIND_RECEIPT)
    parser.add_argument("--out", type=Path, default=root / DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = module_plan.load_metadata(args.metadata)
    result = build_contract(
        extractor_data=stable_read(Path(__file__).resolve(), "extractor", 2 * 1024 * 1024),
        dtbo_data=stable_read(args.dtbo, "stock DTBO", 64 * 1024 * 1024),
        vendor_dtb_data=stable_read(args.vendor_dtb, "stock vendor DTB", 64 * 1024 * 1024),
        property_data=stable_read(args.property_source, "OF property source", 512 * 1024),
        core_data=stable_read(args.core_source, "driver core source", 1024 * 1024),
        of_base_data=stable_read(args.of_base_source, "OF base source", 512 * 1024),
        irq_data=stable_read(args.irq_source, "OF IRQ source", 512 * 1024),
        rpmh_data=stable_read(args.rpmh_source, "RPMh RSC source", 512 * 1024),
        rpmh_regulator_data=stable_read(
            args.rpmh_regulator_source, "RPMh regulator source", 512 * 1024
        ),
        config_data=stable_read(args.config, "fixed Image config", 512 * 1024),
        predecessor_data=stable_read(args.predecessor, "P3.16 predecessor", 8 * 1024 * 1024),
        must_bind_data=stable_read(args.must_bind, "must-bind receipt", 512 * 1024),
        metadata=metadata,
        fdtoverlay=args.fdtoverlay,
        libfdt=args.libfdt,
    )
    encoded = encode_contract(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
