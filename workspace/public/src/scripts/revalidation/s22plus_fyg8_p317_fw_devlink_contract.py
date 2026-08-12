#!/usr/bin/env python3
"""Derive the P3.17 fw_devlink supplier contract from exact source.

Host-only. The audit parses the fixed kernel's complete
``of_supplier_bindings[]`` initializer, its fw_devlink defaults and waiting
attribute semantics, and the exact g0q DTS. It never contacts a device and it
does not grant candidate or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p317_fw_devlink_contract_v1"
VERDICT = "PASS_P317_FW_DEVLINK_DT_SUPPLIER_CLOSURE_CONTRACT_H0"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

EXPECTED_BINDING_COUNT = 28
EXPECTED_OPTIONAL_PARSERS = (
    "parse_iommus",
    "parse_iommu_maps",
    "parse_dmas",
)
MAX77705_COMPATIBLE = "maxim,max77705"
MAX77705_REG = 0x66
EXPECTED_PROVIDER_COMPATIBLE = "qcom,pm8350c-gpio"

DEFAULT_SOURCE_ROOT = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common"
)
DEFAULT_PROPERTY_SOURCE = DEFAULT_SOURCE_ROOT / "drivers/of/property.c"
DEFAULT_CORE_SOURCE = DEFAULT_SOURCE_ROOT / "drivers/base/core.c"
DEFAULT_OF_BASE_SOURCE = DEFAULT_SOURCE_ROOT / "drivers/of/base.c"
DEFAULT_DTS = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "S906NKSS7FYG8_osrc/Kernel/kernel_platform/msm-kernel/arch/arm64/"
    "boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts"
)


class ContractError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise ContractError("repository root not found")


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
        raise ContractError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise ContractError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise ContractError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_text(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label} is not UTF-8") from exc


def require_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ContractError(f"{label} source contract missing: {missing}")


def _balanced_region(text: str, declaration: str) -> str:
    starts = [match.start() for match in re.finditer(re.escape(declaration), text)]
    if len(starts) != 1:
        raise ContractError(
            f"expected one {declaration!r} declaration, found {len(starts)}"
        )
    open_index = text.find("{", starts[0] + len(declaration))
    if open_index < 0:
        raise ContractError(f"{declaration!r} has no initializer")
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index]
    raise ContractError(f"{declaration!r} initializer is unterminated")


def _initializer_entries(body: str) -> tuple[str, ...]:
    entries: list[str] = []
    depth = 0
    start: int | None = None
    in_string = False
    escaped = False
    for index, char in enumerate(body):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise ContractError("supplier initializer brace underflow")
            if depth == 0:
                if start is None:
                    raise ContractError("supplier initializer start missing")
                entries.append(body[start:index].strip())
                start = None
    if depth != 0:
        raise ContractError("supplier initializer entry is unterminated")
    return tuple(entries)


def parse_supplier_bindings(property_source: str) -> tuple[dict[str, Any], ...]:
    declaration = (
        "static const struct supplier_bindings of_supplier_bindings[] ="
    )
    entries = _initializer_entries(_balanced_region(property_source, declaration))
    if not entries or entries[-1] != "":
        raise ContractError("supplier table lacks one terminal empty sentinel")
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries[:-1]):
        parsers = re.findall(r"\.parse_prop\s*=\s*(parse_[A-Za-z0-9_]+)", entry)
        if len(parsers) != 1:
            raise ContractError(
                f"supplier row {index} has {len(parsers)} parse_prop entries"
            )
        optionals = re.findall(r"\.optional\s*=\s*(true|false)", entry)
        if len(optionals) > 1:
            raise ContractError(f"supplier row {index} has duplicate optional")
        rows.append(
            {
                "index": index,
                "parse_prop": parsers[0],
                "optional": optionals == ["true"],
            }
        )
    if len(rows) != EXPECTED_BINDING_COUNT:
        raise ContractError(
            f"supplier table count drift: {len(rows)} != {EXPECTED_BINDING_COUNT}"
        )
    optional = tuple(row["parse_prop"] for row in rows if row["optional"])
    if optional != EXPECTED_OPTIONAL_PARSERS:
        raise ContractError(f"supplier optional rows drifted: {optional}")
    require_tokens(
        property_source,
        "OF supplier property parser",
        (
            'DEFINE_SIMPLE_PROP(pinctrl0, "pinctrl-0", NULL)',
            'DEFINE_SUFFIX_PROP(gpio, "-gpio", "#gpio-cells")',
            "if (s->optional && !fw_devlink_is_strict())",
        ),
    )
    return tuple(rows)


def parse_macro_parser_rules(property_source: str) -> dict[str, dict[str, Any]]:
    require_tokens(
        property_source,
        "macro parser helper semantics",
        (
            "static struct device_node *parse_prop_cells(",
            "if (strcmp(prop_name, list_name))",
            "of_parse_phandle_with_args(np, list_name, cells_name, index,",
            "#define DEFINE_SIMPLE_PROP(fname, name, cells)",
            "return parse_prop_cells(np, prop_name, index, name, cells);",
            "static int strcmp_suffix(const char *str, const char *suffix)",
            "if (len <= suffix_len)",
            "return strcmp(str + len - suffix_len, suffix);",
            "static struct device_node *parse_suffix_prop_cells(",
            "if (strcmp_suffix(prop_name, suffix))",
            "of_parse_phandle_with_args(np, prop_name, cells_name, index,",
            "#define DEFINE_SUFFIX_PROP(fname, suffix, cells)",
            "return parse_suffix_prop_cells(np, prop_name, index, suffix, cells);",
        ),
    )
    rules: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"DEFINE_(SIMPLE|SUFFIX)_PROP\(\s*([A-Za-z0-9_]+)\s*,\s*"
        r'"([^"]+)"\s*,\s*(NULL|"[^"]+")\s*\)'
    )
    for kind, name, value, cells in pattern.findall(property_source):
        parser = f"parse_{name}"
        if parser in rules:
            raise ContractError(f"duplicate parser macro rule: {parser}")
        rules[parser] = {
            "kind": kind.lower(),
            "value": value,
            "cells_property": None if cells == "NULL" else cells.strip('"'),
        }
    for parser in ("parse_pinctrl0", "parse_gpio"):
        if parser not in rules:
            raise ContractError(f"required target parser macro missing: {parser}")
    require_tokens(
        property_source,
        "special parser matching semantics",
        (
            'if (strcmp(prop_name, "iommu-map"))',
            'if (!strcmp_suffix(prop_name, ",nr-gpios"))',
            'return parse_suffix_prop_cells(np, prop_name, index, "-gpios",',
            'if (strcmp(prop_name, "gpio") && strcmp(prop_name, "gpios"))',
            'if (of_find_property(np, "gpio-hog", NULL))',
            'if (strcmp(prop_name, "interrupts") &&',
            'strcmp(prop_name, "interrupts-extended"))',
        ),
    )
    rules.update(
        {
            "parse_iommu_maps": {
                "kind": "special_exact",
                "values": ["iommu-map"],
                "cells_property": None,
                "supported_for_target_edge": False,
            },
            "parse_gpios": {
                "kind": "special_suffix",
                "value": "-gpios",
                "excluded_suffix": ",nr-gpios",
                "cells_property": "#gpio-cells",
                "supported_for_target_edge": True,
            },
            "parse_gpio_compat": {
                "kind": "special_exact",
                "values": ["gpio", "gpios"],
                "reject_consumer_property": "gpio-hog",
                "cells_property": "#gpio-cells",
                "supported_for_target_edge": True,
            },
            "parse_interrupts": {
                "kind": "special_exact",
                "values": ["interrupts", "interrupts-extended"],
                "cells_property": None,
                "supported_for_target_edge": False,
            },
        }
    )
    return rules


def audit_of_link_semantics(property_source: str) -> dict[str, Any]:
    require_tokens(
        property_source,
        "OF link-to-phandle semantics",
        (
            "if (!of_device_is_available(sup_np))",
            "if (of_is_ancestor_of(con_np, sup_np))",
            "of_node_check_flag(sup_np, OF_POPULATED)",
            "sup_np->fwnode.flags & FWNODE_FLAG_NOT_DEVICE",
            "fwnode_link_add(of_fwnode_handle(con_np), of_fwnode_handle(sup_np));",
        ),
    )
    return {
        "static_modeled_gates": [
            "supplier_and_compatible_ancestor_availability",
            "consumer_ancestor_rejection",
        ],
        "runtime_only_gate": "OF_POPULATED_or_FWNODE_FLAG_NOT_DEVICE_without_device",
        "runtime_only_gate_authority": "not_derivable_from_static_dts",
    }


def effective_parser_rows(
    rows: tuple[dict[str, Any], ...],
    *,
    mode: str,
    strict: bool,
    mode_assignments: dict[str, str],
) -> tuple[str, ...]:
    if mode not in mode_assignments:
        raise ContractError(f"unsupported fw_devlink mode: {mode}")
    flags = mode_assignments[mode]
    if flags == "0":
        return ()
    effective_strict = strict and flags != "FW_DEVLINK_FLAGS_PERMISSIVE"
    return tuple(
        row["parse_prop"]
        for row in rows
        if not row["optional"] or effective_strict
    )


def audit_core_semantics(core_source: str, of_base_source: str) -> dict[str, Any]:
    require_tokens(
        core_source,
        "driver-core fw_devlink",
        (
            "static u32 fw_devlink_flags = FW_DEVLINK_FLAGS_ON;",
            'early_param("fw_devlink", fw_devlink_setup);',
            "static bool fw_devlink_strict = true;",
            "static int __init fw_devlink_strict_setup(char *arg)",
            "return strtobool(arg, &fw_devlink_strict);",
            'early_param("fw_devlink.strict", fw_devlink_strict_setup);',
            "return fw_devlink_strict && !fw_devlink_is_permissive();",
            "static void fw_devlink_link_device(struct device *dev)",
            "if (!fw_devlink_flags)\n\t\treturn;",
            "fw_devlink_parse_fwtree(fwnode);",
            "static void fw_devlink_parse_fwtree(struct fwnode_handle *fwnode)",
            "while ((child = fwnode_get_next_available_child_node(fwnode, child)))",
            "fw_devlink_parse_fwtree(child);",
            "val = !list_empty(&dev->fwnode->suppliers);",
            'return sysfs_emit(buf, "%u\\n", val);',
            "static DEVICE_ATTR_RO(waiting_for_supplier);",
            "if (fw_devlink_flags && !fw_devlink_is_permissive() && dev->fwnode)",
            "list_for_each_entry(link, &sup->consumers, s_hook)",
            "if (link->consumer == con)\n\t\t\tgoto out;",
        ),
    )
    require_tokens(
        of_base_source,
        "OF availability semantics",
        (
            "Return: True if the status property is absent or set to \"okay\" or \"ok\"",
            'if (!strcmp(status, "okay") || !strcmp(status, "ok"))',
        ),
    )
    setup_body = _balanced_region(
        core_source, "static int __init fw_devlink_setup(char *arg)"
    )
    assignments = dict(
        re.findall(
            r'strcmp\(arg,\s*"([^"]+)"\)\s*==\s*0\)\s*\{\s*'
            r"fw_devlink_flags\s*=\s*([A-Za-z0-9_]+);",
            setup_body,
            flags=re.DOTALL,
        )
    )
    expected_assignments = {
        "off": "0",
        "permissive": "FW_DEVLINK_FLAGS_PERMISSIVE",
        "on": "FW_DEVLINK_FLAGS_ON",
        "rpm": "FW_DEVLINK_FLAGS_RPM",
    }
    if assignments != expected_assignments:
        raise ContractError(f"fw_devlink setup mode mapping drifted: {assignments}")
    if setup_body.count("fw_devlink_flags =") != len(expected_assignments):
        raise ContractError("fw_devlink setup has an unclassified assignment")
    if "return 0;" not in setup_body:
        raise ContractError("fw_devlink setup unknown-mode return drifted")
    return {
        "source_default_mode": "on",
        "source_default_strict": True,
        "mode_assignments": assignments,
        "unknown_mode_behavior": "leave_prior_flags_unchanged_and_return_zero",
        "optional_rows_are_parsed_under_source_default": True,
        "waiting_for_supplier_states": {
            "attribute_absent": "not_authoritatively_exposed",
            "attribute_present_0": "no_unresolved_fwnode_supplier",
            "attribute_present_1": "one_or_more_unresolved_fwnode_suppliers",
        },
        "waiting_for_supplier_names_suppliers": False,
        "consumer_supplier_edges_are_deduplicated": True,
        "available_status_values": ["absent", "ok", "okay"],
    }


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _dts_tokens(text: str) -> tuple[tuple[str, str], ...]:
    tokens: list[tuple[str, str]] = []
    start = 0
    in_string = False
    escaped = False
    angle_depth = 0
    square_depth = 0
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "<":
            angle_depth += 1
        elif char == ">":
            angle_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif angle_depth == 0 and square_depth == 0 and char in "{};":
            value = text[start:index].strip()
            tokens.append((char, value))
            start = index + 1
    if in_string or angle_depth or square_depth:
        raise ContractError("DTS token stream is unterminated")
    if text[start:].strip():
        raise ContractError("DTS has trailing unterminated content")
    return tuple(tokens)


@dataclass
class DtsNode:
    name: str
    path: str
    parent: "DtsNode | None"
    properties: dict[str, str] = field(default_factory=dict)


def parse_dts(dts_source: str) -> tuple[DtsNode, ...]:
    root = DtsNode(name="<translation-unit>", path="", parent=None)
    stack = [root]
    nodes: list[DtsNode] = []
    for kind, value in _dts_tokens(_strip_comments(dts_source)):
        if kind == "{":
            if not value:
                raise ContractError("DTS node name missing")
            name = value.split(":", 1)[-1].strip()
            if not name or "=" in name:
                raise ContractError(f"invalid DTS node declaration: {value!r}")
            parent = stack[-1]
            if name == "/":
                path = "/"
            elif parent.path in {"", "/"}:
                path = "/" + name
            else:
                path = parent.path + "/" + name
            node = DtsNode(name=name, path=path, parent=parent)
            nodes.append(node)
            stack.append(node)
        elif kind == "}":
            if value:
                raise ContractError(f"unexpected content before DTS close: {value!r}")
            if len(stack) == 1:
                raise ContractError("DTS node stack underflow")
            stack.pop()
        elif kind == ";":
            if (
                not value
                or len(stack) == 1
                or (value.startswith("#") and "=" not in value)
            ):
                continue
            if "=" in value:
                name, raw = value.split("=", 1)
                stack[-1].properties[name.strip()] = raw.strip()
            else:
                stack[-1].properties[value.strip()] = ""
    if len(stack) != 1:
        raise ContractError("DTS node stack is unterminated")
    return tuple(nodes)


def _u32_cells(raw: str, label: str) -> tuple[int, ...]:
    matches = re.fullmatch(r"<\s*(.*?)\s*>", raw, flags=re.DOTALL)
    if not matches:
        raise ContractError(f"{label} is not one u32 cell list")
    values: list[int] = []
    for token in matches.group(1).split():
        try:
            values.append(int(token, 0))
        except ValueError as exc:
            raise ContractError(f"{label} has non-numeric cell {token!r}") from exc
    if not values:
        raise ContractError(f"{label} is empty")
    return tuple(values)


def _string_values(raw: str) -> tuple[str, ...]:
    return tuple(re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', raw))


def _compatible(node: DtsNode) -> tuple[str, ...]:
    raw = node.properties.get("compatible")
    return () if raw is None else _string_values(raw)


def _node_available(node: DtsNode) -> bool:
    raw = node.properties.get("status")
    if raw is None:
        return True
    values = _string_values(raw)
    return len(values) == 1 and values[0] in {"ok", "okay"}


def _is_ancestor(ancestor: DtsNode, node: DtsNode) -> bool:
    current: DtsNode | None = node
    while current is not None:
        if current is ancestor:
            return True
        current = current.parent
    return False


def _owning_compatible_node(node: DtsNode, consumer: DtsNode) -> DtsNode:
    current: DtsNode | None = node
    while current is not None:
        if not _node_available(current):
            raise ContractError(
                f"supplier path is unavailable before compatible owner: {current.path}"
            )
        if _compatible(current):
            if _is_ancestor(consumer, current):
                raise ContractError(
                    f"supplier owner is a descendant of consumer: {current.path}"
                )
            return current
        current = current.parent
    raise ContractError(f"supplier {node.path} has no compatible owner")


def _rule_matches_property(rule: dict[str, Any], property_name: str) -> bool:
    if rule["kind"] == "simple":
        return property_name == rule["value"]
    if rule["kind"] == "suffix":
        suffix = rule["value"]
        return len(property_name) > len(suffix) and property_name.endswith(suffix)
    if rule["kind"] == "special_exact":
        return property_name in rule["values"]
    if rule["kind"] == "special_suffix":
        excluded = rule.get("excluded_suffix")
        if excluded and property_name.endswith(excluded):
            return False
        suffix = rule["value"]
        return len(property_name) > len(suffix) and property_name.endswith(suffix)
    raise ContractError(f"unsupported parser rule kind: {rule['kind']}")


def _parse_property_phandles(
    *,
    consumer: DtsNode,
    property_name: str,
    rule: dict[str, Any],
    providers: dict[int, DtsNode],
) -> tuple[DtsNode, ...]:
    raw = consumer.properties.get(property_name)
    if raw is None or not _rule_matches_property(rule, property_name):
        return ()
    rejected_property = rule.get("reject_consumer_property")
    if rejected_property and rejected_property in consumer.properties:
        return ()
    if rule.get("supported_for_target_edge") is False:
        raise ContractError(
            f"matched {property_name} needs a dedicated {rule['kind']} parser model"
        )
    cells = _u32_cells(raw, f"{consumer.path} {property_name}")
    suppliers: list[DtsNode] = []
    index = 0
    while index < len(cells):
        supplier = providers.get(cells[index])
        if supplier is None:
            raise ContractError(
                f"{consumer.path} {property_name} unresolved phandle "
                f"{cells[index]:#x}"
            )
        index += 1
        cells_property = rule["cells_property"]
        argument_count = 0
        if cells_property is not None:
            raw_count = supplier.properties.get(cells_property)
            if raw_count is None:
                raise ContractError(
                    f"{supplier.path} lacks parser cells property {cells_property}"
                )
            count_cells = _u32_cells(
                raw_count, f"{supplier.path} {cells_property}"
            )
            if len(count_cells) != 1:
                raise ContractError(
                    f"{supplier.path} {cells_property} is not one count cell"
                )
            argument_count = count_cells[0]
        if index + argument_count > len(cells):
            raise ContractError(
                f"{consumer.path} {property_name} lacks {argument_count} arguments"
            )
        index += argument_count
        suppliers.append(supplier)
    return tuple(suppliers)


def audit_max77705_edges(
    dts_source: str,
    *,
    rows: tuple[dict[str, Any], ...],
    parser_rules: dict[str, dict[str, Any]],
    effective_parsers: tuple[str, ...],
) -> dict[str, Any]:
    nodes = parse_dts(dts_source)
    providers: dict[int, DtsNode] = {}
    for node in nodes:
        raw = node.properties.get("phandle") or node.properties.get("linux,phandle")
        if raw is None:
            continue
        cells = _u32_cells(raw, f"{node.path} phandle")
        if len(cells) != 1 or cells[0] in providers:
            raise ContractError(f"duplicate or malformed phandle at {node.path}")
        providers[cells[0]] = node

    consumers = []
    for node in nodes:
        if MAX77705_COMPATIBLE not in _compatible(node):
            continue
        raw_reg = node.properties.get("reg")
        if raw_reg is None:
            continue
        if _u32_cells(raw_reg, f"{node.path} reg") == (MAX77705_REG,):
            consumers.append(node)
    if len(consumers) != 1:
        raise ContractError(f"expected one exact Max77705 consumer, found {len(consumers)}")
    consumer = consumers[0]
    current: DtsNode | None = consumer
    while current is not None:
        if not _node_available(current):
            raise ContractError(
                f"consumer path is unavailable to fw_devlink traversal: {current.path}"
            )
        current = current.parent

    effective_set = set(effective_parsers)
    table_order = tuple(row["parse_prop"] for row in rows)
    raw_edges: list[dict[str, Any]] = []
    for property_name in consumer.properties:
        matched_parser: str | None = None
        parsed_suppliers: tuple[DtsNode, ...] = ()
        for parser_name in table_order:
            if parser_name not in effective_set:
                continue
            rule = parser_rules.get(parser_name)
            if rule is None or not _rule_matches_property(rule, property_name):
                continue
            candidates = _parse_property_phandles(
                consumer=consumer,
                property_name=property_name,
                rule=rule,
                providers=providers,
            )
            if candidates:
                matched_parser = parser_name
                parsed_suppliers = candidates
                break
        if matched_parser is None:
            continue
        if len(parsed_suppliers) != 1:
            raise ContractError(f"target property {property_name} has multiple edges")
        supplier = parsed_suppliers[0]
        owner = _owning_compatible_node(supplier, consumer)
        phandle = _u32_cells(
            consumer.properties[property_name],
            f"{consumer.path} {property_name}",
        )[0]
        raw_edges.append(
            {
                "property": property_name,
                "parser": matched_parser,
                "parser_rule": parser_rules[matched_parser],
                "phandle": f"0x{phandle:x}",
                "supplier_node": supplier.path,
                "supplier_available": True,
                "owner_node": owner.path,
                "owner_available": True,
                "owner_compatible": list(_compatible(owner)),
                "consumer_ancestor_rejected": False,
                "static_of_link_eligible": True,
            }
        )

    deduplicated = {
        (consumer.path, edge["owner_node"]): edge["owner_compatible"]
        for edge in raw_edges
    }
    if len(deduplicated) != 1:
        raise ContractError(
            "Max77705 pinctrl and IRQ GPIO resolve to different owner devices"
        )
    owner_compatible = next(iter(deduplicated.values()))
    if EXPECTED_PROVIDER_COMPATIBLE not in owner_compatible:
        raise ContractError(f"unexpected Max77705 supplier owner: {owner_compatible}")
    return {
        "consumer_node": consumer.path,
        "consumer_compatible": MAX77705_COMPATIBLE,
        "consumer_reg": f"0x{MAX77705_REG:x}",
        "raw_property_edge_count": len(raw_edges),
        "raw_property_edges": raw_edges,
        "deduplicated_consumer_supplier_edge_count": len(deduplicated),
        "deduplicated_owner_nodes": sorted(owner for _, owner in deduplicated),
        "both_properties_resolve_to_same_owner": True,
        "runtime_early_device_gate_authority": "not_derivable_from_static_dts",
        "final_runtime_device_link_count_claimed": False,
    }


def build_contract(
    *,
    extractor_data: bytes,
    property_data: bytes,
    core_data: bytes,
    of_base_data: bytes,
    dts_data: bytes,
) -> dict[str, Any]:
    property_source = source_text(property_data, "OF property source")
    core_source = source_text(core_data, "driver-core source")
    of_base_source = source_text(of_base_data, "OF base source")
    dts_source = source_text(dts_data, "exact g0q DTS")
    rows = parse_supplier_bindings(property_source)
    parser_rules = parse_macro_parser_rules(property_source)
    table_parsers = {row["parse_prop"] for row in rows}
    if set(parser_rules) != table_parsers:
        raise ContractError(
            "supplier parser rule coverage drifted: "
            f"missing={sorted(table_parsers - set(parser_rules))}, "
            f"extra={sorted(set(parser_rules) - table_parsers)}"
        )
    of_link = audit_of_link_semantics(property_source)
    core = audit_core_semantics(core_source, of_base_source)
    effective = effective_parser_rows(
        rows,
        mode="on",
        strict=True,
        mode_assignments=core["mode_assignments"],
    )
    if len(effective) != EXPECTED_BINDING_COUNT:
        raise ContractError("source-default strict policy does not parse all rows")
    mode_strict_matrix = []
    for mode in ("off", "permissive", "on", "rpm"):
        for strict in (False, True):
            parsers = effective_parser_rows(
                rows,
                mode=mode,
                strict=strict,
                mode_assignments=core["mode_assignments"],
            )
            flags = core["mode_assignments"][mode]
            mode_strict_matrix.append(
                {
                    "mode": mode,
                    "strict_argument": strict,
                    "source_flag_assignment": flags,
                    "effective_strict": (
                        strict and flags != "FW_DEVLINK_FLAGS_PERMISSIVE"
                    ),
                    "effective_parser_count": len(parsers),
                    "effective_parsers": list(parsers),
                }
            )
    max77705 = audit_max77705_edges(
        dts_source,
        rows=rows,
        parser_rules=parser_rules,
        effective_parsers=effective,
    )
    exact_edge_signature = [
        (edge["property"], edge["parser"], edge["phandle"])
        for edge in max77705["raw_property_edges"]
    ]
    expected_edge_signature = [
        ("pinctrl-0", "parse_pinctrl0", "0x7b"),
        ("max77705,irq-gpio", "parse_gpio", "0x11"),
    ]
    if (
        exact_edge_signature != expected_edge_signature
        or max77705["deduplicated_consumer_supplier_edge_count"] != 1
    ):
        raise ContractError(
            f"exact Max77705 regression drifted: {exact_edge_signature}"
        )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "authority": {
            "extractor_source": receipt(extractor_data),
            "of_property_source": receipt(property_data),
            "driver_core_source": receipt(core_data),
            "of_base_source": receipt(of_base_data),
            "exact_g0q_dts": receipt(dts_data),
        },
        "supplier_parser_table": {
            "entry_count": len(rows),
            "rows": list(rows),
            "optional_entry_count": len(EXPECTED_OPTIONAL_PARSERS),
            "optional_parsers": list(EXPECTED_OPTIONAL_PARSERS),
            "source_default_effective_parser_count": len(effective),
            "source_default_effective_parsers": list(effective),
            "mode_strict_matrix": mode_strict_matrix,
        },
        "fw_devlink": core,
        "of_link_to_phandle": of_link,
        "max77705_regression": max77705,
        "contract": {
            "raw_phandle_scan_is_forbidden": True,
            "parser_table_is_authority": True,
            "optional_requires_mode_and_strict_evaluation": True,
            "must_bind_consumer_scope_is_independent": True,
            "raw_edges_and_deduplicated_edges_are_both_receipted": True,
            "fw_devlink_off_or_permissive_is_rejected": True,
            "candidate_boot_arguments_must_reprove_effective_policy": True,
            "runtime_early_device_gate_must_be_reproved": True,
            "device_contact": False,
            "live_authority": False,
        },
    }


def encode_contract(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--property-source", type=Path, default=root / DEFAULT_PROPERTY_SOURCE)
    parser.add_argument("--core-source", type=Path, default=root / DEFAULT_CORE_SOURCE)
    parser.add_argument("--of-base-source", type=Path, default=root / DEFAULT_OF_BASE_SOURCE)
    parser.add_argument("--dts", type=Path, default=root / DEFAULT_DTS)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_contract(
        extractor_data=stable_read(
            Path(__file__).resolve(), "extractor source", 2 * 1024 * 1024
        ),
        property_data=stable_read(args.property_source, "OF property source", 512 * 1024),
        core_data=stable_read(args.core_source, "driver-core source", 1024 * 1024),
        of_base_data=stable_read(args.of_base_source, "OF base source", 512 * 1024),
        dts_data=stable_read(args.dts, "exact g0q DTS", 8 * 1024 * 1024),
    )
    encoded = encode_contract(result)
    if args.out is None:
        __import__("sys").stdout.buffer.write(encoded)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
