#!/usr/bin/env python3
"""Audit the P2.42 RPMh gate failure and derive one bounded replacement.

Host-only. This script reads pinned FYG8 artifacts, source archives, device
trees, module metadata, and the prior E2 plan. It does not build an image,
contact a device, or grant live authority.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import struct
import tarfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p241_dtbo_role_contract as dtbo_contract  # noqa: E402
import s22plus_fyg8_p241_e2_static_checker as p241  # noqa: E402
import s22plus_o2_module_plan as planner  # noqa: E402


SCHEMA = "s22plus_fyg8_p243_rpmh_dependency_audit_v1"
VERDICT = "PASS_P243_RPMH_DEPENDENCY_AUDIT_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

DEFAULT_VENDOR_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/dtb"
)
DEFAULT_DTBO = dtbo_contract.DEFAULT_DTBO
DEFAULT_CANDIDATE_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_p242/candidate-a/boot.img"
)
DEFAULT_VENDOR_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/vendor_boot.img"
)
DEFAULT_CONFIG = Path(
    "workspace/private/outputs/s22plus_fyg8_p242/artifacts-a/.config"
)
DEFAULT_STOCK_LIVE_CMDLINE = Path(
    "workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_"
    "20260709T220014Z/sec_debug_state/pre_o3r1/proc__cmdline.txt"
)
DEFAULT_BASE_SOURCE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DEFAULT_DELTA_SOURCE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz"
)
DEFAULT_PLAN_HEADER = p241.DEFAULT_PLAN_HEADER
DEFAULT_INVENTORY = Path("docs/module-map/s22plus-fyg8/inventory.tsv")
DEFAULT_DEPENDENCIES = Path("docs/module-map/s22plus-fyg8/dependency-edges.tsv")

EXPECTED_SHA256 = {
    "vendor_dtb": "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e",
    "candidate_boot": "5444321f846f2f70b6e9932b5aa119eb53abc91da57d6d7a475a4b14d34fe901",
    "vendor_boot": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
    "config": "cc38a7da8cb6fef8fe5cfc57975c0d4496e10bfde3641fcc604d3e9f59bbeac2",
    "stock_live_cmdline": "a27cc8f2a1fbfecb5b38b28b5678f76f937c2f346421b1fc6a758814572e75c8",
    "base_source": "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
    "delta_source": "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a",
    "plan_header": "2223ed333d6288e25b6ce7b7ae3aaa8dc31108dcc8536b9c582a7576953e7647",
    "inventory": "35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b",
    "dependencies": "ec7292c918270748e9bcfccdea454c2e35965acc202c1648ef215963777c5afa",
}

EXPECTED_MODELS = (
    "Qualcomm Technologies, Inc. Waipio v2 SoC",
    "Qualcomm Technologies, Inc. Waipio SoC",
    "Qualcomm Technologies, Inc. WaipioP v2 SoC",
    "Qualcomm Technologies, Inc. WaipioP SoC",
)
OLD_GATE = "/sys/bus/platform/drivers/rpmh/af20000.rsc"
NEW_GATE = "/sys/bus/platform/drivers/rpmh/17a00000.rsc"
DISPCC_MODULE = "dispcc-waipio.ko"
DISPCC_HARD_DEPS = frozenset(
    {
        "clk-qcom.ko",
        "debug-regulator.ko",
        "gdsc-regulator.ko",
        "proxy-consumer.ko",
    }
)

SOURCE_MEMBERS = {
    "driver_core": "kernel_platform/common/drivers/base/core.c",
    "driver_probe": "kernel_platform/common/drivers/base/dd.c",
    "of_property": "kernel_platform/common/drivers/of/property.c",
    "of_platform": "kernel_platform/common/drivers/of/platform.c",
    "psci_domain": (
        "kernel_platform/common/drivers/cpuidle/cpuidle-psci-domain.c"
    ),
    "rpmh_rsc": "kernel_platform/msm-kernel/drivers/soc/qcom/rpmh-rsc.c",
    "clk_rpmh": "kernel_platform/msm-kernel/drivers/clk/qcom/clk-rpmh.c",
    "rpmh_regulator": "kernel_platform/msm-kernel/drivers/regulator/rpmh-regulator.c",
    "dispcc": "kernel_platform/msm-kernel/drivers/clk/qcom/dispcc-waipio.c",
}


class AuditError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise AuditError("repository root not found")


def identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(
    path: Path, label: str, expected_sha256: str, limit: int
) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise AuditError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise AuditError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    digest = hashlib.sha256(data).hexdigest()
    if identity(before) != identity(after) or len(data) != before.st_size:
        raise AuditError(f"{label} changed while reading")
    if digest != expected_sha256:
        raise AuditError(f"{label} SHA256 mismatch: {digest}")
    return data


def stable_sha256(
    path: Path, label: str, expected_sha256: str, limit: int
) -> dict[str, Any]:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise AuditError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise AuditError(f"{label} is indirect, empty, or outside bound")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    after = path.stat(follow_symlinks=False)
    actual = digest.hexdigest()
    if identity(before) != identity(after):
        raise AuditError(f"{label} changed while hashing")
    if actual != expected_sha256:
        raise AuditError(f"{label} SHA256 mismatch: {actual}")
    return {"size": before.st_size, "sha256": actual}


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def ascii_text(data: bytes, label: str) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError(f"{label} is not ASCII") from exc


def require_tokens(text: str, label: str, tokens: tuple[str, ...]) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AuditError(f"{label} source contract missing: {missing}")


def read_source_members(
    path: Path, expected: dict[str, str]
) -> dict[str, bytes]:
    wanted = set(expected.values())
    found: dict[str, bytes] = {}
    try:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive:
                if member.name not in wanted:
                    continue
                if not member.isfile() or member.name in found or member.size > 2 * 1024 * 1024:
                    raise AuditError(f"invalid source member: {member.name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AuditError(f"source member unreadable: {member.name}")
                data = stream.read()
                if len(data) != member.size:
                    raise AuditError(f"source member truncated: {member.name}")
                found[member.name] = data
    except (OSError, tarfile.TarError) as exc:
        raise AuditError(f"source archive parse failed: {path}") from exc
    missing = wanted - set(found)
    if missing:
        raise AuditError(f"source archive members missing: {sorted(missing)}")
    return {label: found[name] for label, name in expected.items()}


def audit_delta_no_override(path: Path, source_members: dict[str, str]) -> dict[str, Any]:
    selected = set(source_members.values())
    regular: list[str] = []
    try:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                name = member.name
                if name.startswith("Kernel/"):
                    name = name[len("Kernel/") :]
                regular.append(name)
    except (OSError, tarfile.TarError) as exc:
        raise AuditError(f"delta source archive parse failed: {path}") from exc
    overlap = sorted(selected.intersection(regular))
    if overlap:
        raise AuditError(f"FYG8 delta overrides audited source: {overlap}")
    return {
        "regular_file_count": len(regular),
        "audited_member_override_count": 0,
        "verified": True,
    }


def audit_source_contract(members: dict[str, bytes]) -> dict[str, Any]:
    text = {label: ascii_text(data, label) for label, data in members.items()}
    require_tokens(
        text["of_property"],
        "OF supplier",
        (
            'DEFINE_SIMPLE_PROP(clocks, "clocks", "#clock-cells")',
            'DEFINE_SIMPLE_PROP(power_domains, "power-domains",',
            'DEFINE_SUFFIX_PROP(regulators, "-supply", NULL)',
            "{ .parse_prop = parse_clocks, },",
            "{ .parse_prop = parse_power_domains, },",
            "{ .parse_prop = parse_regulators, },",
        ),
    )
    require_tokens(
        text["driver_core"],
        "driver core",
        (
            "static u32 fw_devlink_flags = FW_DEVLINK_FLAGS_ON;",
            "static bool fw_devlink_strict = true;",
            "int device_links_check_suppliers(struct device *dev)",
            "return -EPROBE_DEFER;",
        ),
    )
    require_tokens(
        text["driver_probe"],
        "driver probe",
        (
            "ret = device_links_check_suppliers(dev);",
            "if (ret)\n\t\treturn ret;",
            "if (dev->bus->probe)",
        ),
    )
    if text["driver_probe"].find("device_links_check_suppliers(dev)") > text[
        "driver_probe"
    ].find("if (dev->bus->probe)"):
        raise AuditError("supplier check no longer precedes bus probe")
    require_tokens(
        text["of_platform"],
        "OF platform bus id",
        (
            "static void of_device_make_bus_id(struct device *dev)",
            'dev_set_name(dev, dev_name(dev) ? "%s:%s" : "%s",',
            "kbasename(node->full_name), dev_name(dev));",
        ),
    )
    require_tokens(
        text["psci_domain"],
        "PSCI power domain",
        (
            "static int psci_pd_init(struct device_node *np, bool use_osi)",
            "ret = of_genpd_add_provider_simple(np, pd);",
            '{ .compatible = "arm,psci-1.0" },',
            '.name = "psci-cpuidle-domain",',
            "subsys_initcall(psci_idle_init_domains);",
        ),
    )
    require_tokens(
        text["rpmh_rsc"],
        "RPMh RSC",
        (
            "static int rpmh_rsc_probe(struct platform_device *pdev)",
            "ret = cmd_db_ready();",
            'of_find_property(dn, "power-domains", NULL)',
            "ret = rpmh_rsc_pd_attach(drv);",
            "return devm_of_platform_populate(&pdev->dev);",
            '.name = "rpmh"',
        ),
    )
    rpmh_positions = [
        text["rpmh_rsc"].find(token)
        for token in (
            "ret = cmd_db_ready();",
            'of_find_property(dn, "power-domains", NULL)',
            "return devm_of_platform_populate(&pdev->dev);",
        )
    ]
    if rpmh_positions != sorted(rpmh_positions) or min(rpmh_positions) < 0:
        raise AuditError("RPMh probe order mismatch")
    require_tokens(
        text["clk_rpmh"],
        "RPMh clock",
        (
            '"qcom,waipio-rpmh-clk"',
            '.name\t= "clk-rpmh"',
            "devm_of_clk_add_hw_provider",
        ),
    )
    require_tokens(
        text["rpmh_regulator"],
        "RPMh regulator",
        (
            '"qcom,rpmh-vrm-regulator"',
            '"qcom,rpmh-arc-regulator"',
            '.name\t\t= "qcom,rpmh-regulator"',
            "devm_regulator_register",
        ),
    )
    require_tokens(
        text["dispcc"],
        "display clock",
        (
            '"qcom,waipio-dispcc"',
            '.name = "disp_cc-waipio"',
            "platform_driver_register(&disp_cc_waipio_driver)",
        ),
    )
    return {
        "members": {
            label: {**receipt(data), "archive_path": SOURCE_MEMBERS[label]}
            for label, data in members.items()
        },
        "clocks_are_required_fw_devlink_suppliers": True,
        "power_domains_are_required_fw_devlink_suppliers": True,
        "regulator_supplies_are_required_fw_devlink_suppliers": True,
        "supplier_check_precedes_probe": True,
        "fw_devlink_default": "on",
        "fw_devlink_strict_default": True,
        "psci_cluster_provider_registration": (
            "psci-cpuidle-domain -> of_genpd_add_provider_simple"
        ),
        "psci_platform_bus_id": "soc:psci",
        "rpmh_probe_order": [
            "cmd_db_ready",
            "resource-tcs-irq",
            "power-domain-if-present",
            "populate-children",
        ],
        "verified": True,
    }


def parse_concatenated_fdt(data: bytes) -> tuple[bytes, ...]:
    blobs: list[bytes] = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise AuditError("concatenated FDT header truncated")
        magic, total_size = struct.unpack_from(">II", data, offset)
        if magic != dtbo_contract.FDT_MAGIC or total_size < 40:
            raise AuditError(f"concatenated FDT invalid at offset {offset}")
        end = offset + total_size
        if end > len(data):
            raise AuditError("concatenated FDT escapes input")
        blobs.append(data[offset:end])
        offset = end
    if offset != len(data):
        raise AuditError("concatenated FDT has trailing bytes")
    return tuple(blobs)


def u32_cells(value: bytes, label: str) -> tuple[int, ...]:
    if not value or len(value) % 4:
        raise AuditError(f"{label} is not a non-empty u32 cell list")
    return tuple(
        struct.unpack_from(">I", value, offset)[0]
        for offset in range(0, len(value), 4)
    )


def require_node(
    nodes: tuple[dtbo_contract.FdtNode, ...], path: str
) -> dtbo_contract.FdtNode:
    matches = [node for node in nodes if node.path == path]
    if len(matches) != 1:
        raise AuditError(f"expected one FDT node {path}, found {len(matches)}")
    return matches[0]


def strings(node: dtbo_contract.FdtNode, name: str) -> tuple[str, ...]:
    value = node.properties.get(name)
    if value is None:
        raise AuditError(f"{node.path} missing {name}")
    return dtbo_contract.string_list(value)


def phandle_map(
    nodes: tuple[dtbo_contract.FdtNode, ...],
) -> dict[int, str]:
    result: dict[int, str] = {}
    for node in nodes:
        raw = node.properties.get("phandle") or node.properties.get("linux,phandle")
        if raw is None:
            continue
        values = u32_cells(raw, f"{node.path} phandle")
        if len(values) != 1 or values[0] in result:
            raise AuditError(f"duplicate or malformed phandle at {node.path}")
        result[values[0]] = node.path
    return result


def provider_path(
    node: dtbo_contract.FdtNode,
    property_name: str,
    providers: dict[int, str],
) -> str:
    raw = node.properties.get(property_name)
    if raw is None:
        raise AuditError(f"{node.path} missing {property_name}")
    cells = u32_cells(raw, f"{node.path} {property_name}")
    path = providers.get(cells[0])
    if path is None:
        raise AuditError(f"{node.path} has unresolved {property_name} phandle")
    return path


def audit_vendor_dtb(data: bytes) -> dict[str, Any]:
    blobs = parse_concatenated_fdt(data)
    if len(blobs) != len(EXPECTED_MODELS):
        raise AuditError(f"expected four vendor DTBs, found {len(blobs)}")
    rows: list[dict[str, Any]] = []
    for index, (blob, expected_model) in enumerate(zip(blobs, EXPECTED_MODELS)):
        nodes = dtbo_contract.parse_fdt(blob)
        providers = phandle_map(nodes)
        root = require_node(nodes, "/")
        model = strings(root, "model")
        if model != (expected_model,):
            raise AuditError(f"vendor DTB {index} model mismatch: {model}")

        apps = require_node(nodes, "/soc/rsc@17a00000")
        display = require_node(nodes, "/soc/rsc@af20000")
        psci = require_node(nodes, "/soc/psci")
        psci_pd = require_node(nodes, "/soc/psci/cluster-pd")
        dispcc = require_node(nodes, "/soc/clock-controller@af00000")
        gcc = require_node(nodes, "/soc/clock-controller@100000")
        rpmh_clk = require_node(nodes, "/soc/rsc@17a00000/qcom,rpmhclk")

        if (
            strings(apps, "compatible") != ("qcom,rpmh-rsc",)
            or strings(apps, "label") != ("apps_rsc",)
            or "clocks" in apps.properties
            or provider_path(apps, "power-domains", providers) != psci_pd.path
            or strings(psci, "compatible") != ("arm,psci-1.0",)
            or u32_cells(psci_pd.properties["#power-domain-cells"], "PSCI cells")
            != (0,)
        ):
            raise AuditError(f"vendor DTB {index} apps RSC contract mismatch")
        display_clocks = u32_cells(
            display.properties.get("clocks", b""), "display RSC clocks"
        )
        if (
            strings(display, "compatible") != ("qcom,rpmh-rsc",)
            or strings(display, "label") != ("disp_rsc",)
            or "power-domains" in display.properties
            or provider_path(display, "clocks", providers) != dispcc.path
            or len(display_clocks) != 2
            or display_clocks[1] != 0x48
            or "qcom,waipio-dispcc" not in strings(dispcc, "compatible")
        ):
            raise AuditError(f"vendor DTB {index} display RSC contract mismatch")
        if (
            strings(rpmh_clk, "compatible") != ("qcom,waipio-rpmh-clk",)
            or provider_path(gcc, "clocks", providers) != rpmh_clk.path
            or not provider_path(gcc, "vdd_cx-supply", providers).startswith(
                apps.path + "/rpmh-regulator-cxlvl/"
            )
            or not provider_path(gcc, "vdd_mxa-supply", providers).startswith(
                apps.path + "/rpmh-regulator-mxlvl/"
            )
            or provider_path(dispcc, "clocks", providers) != rpmh_clk.path
            or not provider_path(dispcc, "vdd_mxa-supply", providers).startswith(
                apps.path + "/rpmh-regulator-mxlvl/"
            )
        ):
            raise AuditError(f"vendor DTB {index} RPMh consumer chain mismatch")
        rows.append(
            {
                "index": index,
                "model": expected_model,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "apps_rsc": {
                    "path": apps.path,
                    "power_domain_provider": psci_pd.path,
                    "clock_supplier": None,
                },
                "display_rsc": {
                    "path": display.path,
                    "power_domain_provider": None,
                    "clock_supplier": dispcc.path,
                    "clock_id": display_clocks[1],
                },
                "gcc": {
                    "path": gcc.path,
                    "rpmh_clock_provider": rpmh_clk.path,
                    "rpmh_regulator_supplies": ["cxlvl", "mxlvl"],
                },
            }
        )
    return {
        "identity": receipt(data),
        "blob_count": len(rows),
        "variants": rows,
        "common_facts": {
            "failed_gate_is_display_rsc": True,
            "display_rsc_has_power_domain": False,
            "display_rsc_clock_supplier_compatible": "qcom,waipio-dispcc",
            "apps_rsc_power_domain_provider": "/soc/psci/cluster-pd",
            "psci_parent_compatible": "arm,psci-1.0",
            "gcc_depends_on_apps_rsc_children": True,
        },
        "verified": True,
    }


def audit_dtbo_parent_neutrality(root: Path) -> dict[str, Any]:
    data = dtbo_contract.stable_read(root / DEFAULT_DTBO)
    rows = dtbo_contract.parse_dtbo(data)
    neutral: list[dict[str, Any]] = []
    for row in rows:
        nodes = row["nodes"]
        fixups = require_node(nodes, "/__fixups__")
        targets: dict[str, str] = {}
        for symbol in ("apps_rsc", "disp_rsc"):
            refs = strings(fixups, symbol)
            if len(refs) != 1 or ":target:0" not in refs[0]:
                raise AuditError(f"DTBO {row['index']} {symbol} fixup mismatch")
            fragment = refs[0].split(":", 1)[0]
            overlay = require_node(nodes, fragment + "/__overlay__")
            if overlay.properties:
                raise AuditError(
                    f"DTBO {row['index']} changes {symbol} parent properties"
                )
            targets[symbol] = fragment
        neutral.append({"index": row["index"], "targets": targets})
    if len(neutral) != dtbo_contract.EXPECTED_ENTRY_COUNT:
        raise AuditError("DTBO entry count mismatch")
    return {
        "identity": receipt(data),
        "entry_count": len(neutral),
        "rsc_parent_property_overrides": 0,
        "entries": neutral,
        "verified": True,
    }


def parse_tsv(data: bytes, label: str) -> list[dict[str, str]]:
    text = ascii_text(data, label)
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if reader.fieldnames is None:
        raise AuditError(f"{label} TSV header missing")
    rows = list(reader)
    if not rows:
        raise AuditError(f"{label} TSV is empty")
    return rows


def one_row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise AuditError(f"expected one {key}={value}, found {len(matches)}")
    return matches[0]


def audit_module_closure(
    root: Path, header_data: bytes, inventory_data: bytes, dependencies_data: bytes
) -> dict[str, Any]:
    _metadata, plan, plan_audit = p241.audit_plan(
        root / planner.DEFAULT_METADATA_DIR, header_data
    )
    modules = set(plan.modules)
    old_gate = planner.FUNCTIONAL_BIND_GATES[3]
    if (
        old_gate["id"] != "rpmh"
        or old_gate["path"] != OLD_GATE
        or old_gate["required_runtime_modules"] != ["qcom_rpmh"]
    ):
        raise AuditError("P2.42 RPMh gate contract drifted")
    required = {
        "qcom_rpmh.ko",
        "clk-rpmh.ko",
        "rpmh-regulator.ko",
        "gcc-waipio.ko",
    }
    if not required.issubset(modules) or DISPCC_MODULE in modules:
        raise AuditError("P2.42 RPMh/display module selection mismatch")

    inventory = parse_tsv(inventory_data, "module inventory")
    dispcc = one_row(inventory, "filename", DISPCC_MODULE)
    if (
        dispcc.get("runtime_name") != "dispcc_waipio"
        or dispcc.get("evidence_status") != "STATIC_VERIFIED"
    ):
        raise AuditError("display clock module inventory mismatch")
    dependencies = parse_tsv(dependencies_data, "module dependency edges")
    hard_deps = {
        row["before"]
        for row in dependencies
        if row.get("relation") == "hard" and row.get("after") == DISPCC_MODULE
    }
    if hard_deps != DISPCC_HARD_DEPS:
        raise AuditError(f"display clock hard dependency mismatch: {hard_deps}")
    if not hard_deps.issubset(modules):
        raise AuditError("display clock prerequisites are absent from E2 plan")
    return {
        "module_count": len(plan.modules),
        "constraint_count": plan_audit["constraint_count"],
        "plan_tsv_sha256": plan_audit["tsv_sha256"],
        "old_gate": old_gate,
        "selected_rpmh_chain": sorted(required),
        "missing_display_supplier_module": DISPCC_MODULE,
        "display_supplier_hard_dependencies": sorted(hard_deps),
        "display_supplier_hard_dependencies_already_selected": True,
        "display_supplier_itself_selected": False,
        "verified": True,
    }


def parse_config(data: bytes) -> dict[str, Any]:
    text = ascii_text(data, "P2.42 kernel config")
    required = (
        "CONFIG_PM_GENERIC_DOMAINS=y",
        "CONFIG_PM_GENERIC_DOMAINS_OF=y",
        "CONFIG_ARM_PSCI_CPUIDLE=y",
        "CONFIG_ARM_PSCI_CPUIDLE_DOMAIN=y",
        "CONFIG_ARM_PSCI_FW=y",
        "# CONFIG_COMMON_CLK_QCOM is not set",
        "# CONFIG_QCOM_RPMH is not set",
    )
    require_tokens(text, "P2.42 kernel config", required)
    return {
        **receipt(data),
        "psci_power_domain_support_builtin": True,
        "qcom_clock_and_rpmh_drivers_not_builtin": True,
        "verified": True,
    }


def audit_boot_arguments(
    candidate_data: bytes, vendor_data: bytes, stock_live_cmdline: bytes
) -> dict[str, Any]:
    candidate = boot_verify.parse_boot_v4(candidate_data)
    vendor = boot_verify.parse_vendor_boot_v4(vendor_data)
    try:
        bootconfig = vendor.bootconfig.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError("vendor bootconfig is not ASCII") from exc
    sources = {
        "boot_cmdline": candidate.header["cmdline"],
        "vendor_cmdline": vendor.cmdline,
        "vendor_bootconfig": bootconfig,
        "same_fyg8_bootloader_stock_live_cmdline": ascii_text(
            stock_live_cmdline, "stock live cmdline capture"
        ),
    }
    forbidden = ("fw_devlink=", "fw_devlink.strict=")
    overrides = [
        {"source": source, "token": token}
        for source, value in sources.items()
        for token in forbidden
        if token in value
    ]
    if overrides:
        raise AuditError(f"fw_devlink override present: {overrides}")
    return {
        "candidate_boot": receipt(candidate_data),
        "vendor_boot": receipt(vendor_data),
        "boot_cmdline": sources["boot_cmdline"],
        "vendor_cmdline": sources["vendor_cmdline"],
        "vendor_bootconfig_sha256": hashlib.sha256(vendor.bootconfig).hexdigest(),
        "stock_live_cmdline": receipt(stock_live_cmdline),
        "fw_devlink_overrides": [],
        "effective_source_default": "on-strict",
        "candidate_runtime_cmdline_directly_observed": False,
        "verified": True,
    }


def build_result() -> dict[str, Any]:
    root = repo_root()
    paths = {
        "vendor_dtb": root / DEFAULT_VENDOR_DTB,
        "candidate_boot": root / DEFAULT_CANDIDATE_BOOT,
        "vendor_boot": root / DEFAULT_VENDOR_BOOT,
        "config": root / DEFAULT_CONFIG,
        "stock_live_cmdline": root / DEFAULT_STOCK_LIVE_CMDLINE,
        "base_source": root / DEFAULT_BASE_SOURCE,
        "delta_source": root / DEFAULT_DELTA_SOURCE,
        "plan_header": root / DEFAULT_PLAN_HEADER,
        "inventory": root / DEFAULT_INVENTORY,
        "dependencies": root / DEFAULT_DEPENDENCIES,
    }
    vendor_dtb = stable_read(
        paths["vendor_dtb"], "vendor DTB", EXPECTED_SHA256["vendor_dtb"], 4 * 1024 * 1024
    )
    candidate_boot = stable_read(
        paths["candidate_boot"],
        "P2.42 candidate boot",
        EXPECTED_SHA256["candidate_boot"],
        128 * 1024 * 1024,
    )
    vendor_boot = stable_read(
        paths["vendor_boot"],
        "stock vendor boot",
        EXPECTED_SHA256["vendor_boot"],
        128 * 1024 * 1024,
    )
    config = stable_read(
        paths["config"], "P2.42 kernel config", EXPECTED_SHA256["config"], 1024 * 1024
    )
    stock_live_cmdline = stable_read(
        paths["stock_live_cmdline"],
        "same-FYG8 stock live cmdline",
        EXPECTED_SHA256["stock_live_cmdline"],
        64 * 1024,
    )
    header = stable_read(
        paths["plan_header"],
        "P2.42 plan header",
        EXPECTED_SHA256["plan_header"],
        1024 * 1024,
    )
    inventory = stable_read(
        paths["inventory"],
        "module inventory",
        EXPECTED_SHA256["inventory"],
        2 * 1024 * 1024,
    )
    dependencies = stable_read(
        paths["dependencies"],
        "module dependencies",
        EXPECTED_SHA256["dependencies"],
        2 * 1024 * 1024,
    )
    base_source_identity = stable_sha256(
        paths["base_source"],
        "base source archive",
        EXPECTED_SHA256["base_source"],
        700 * 1024 * 1024,
    )
    delta_source_identity = stable_sha256(
        paths["delta_source"],
        "FYG8 delta source archive",
        EXPECTED_SHA256["delta_source"],
        8 * 1024 * 1024,
    )
    source_members = read_source_members(paths["base_source"], SOURCE_MEMBERS)
    delta_audit = audit_delta_no_override(paths["delta_source"], SOURCE_MEMBERS)

    source = audit_source_contract(source_members)
    vendor_tree = audit_vendor_dtb(vendor_dtb)
    overlays = audit_dtbo_parent_neutrality(root)
    modules = audit_module_closure(root, header, inventory, dependencies)
    kernel_config = parse_config(config)
    boot_arguments = audit_boot_arguments(
        candidate_boot, vendor_boot, stock_live_cmdline
    )

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "inputs": {
            "base_source": base_source_identity,
            "delta_source": delta_source_identity,
            "plan_header": receipt(header),
            "inventory": receipt(inventory),
            "dependencies": receipt(dependencies),
        },
        "source": source,
        "source_delta": delta_audit,
        "vendor_dtb": vendor_tree,
        "dtbo": overlays,
        "kernel_config": kernel_config,
        "boot_arguments": boot_arguments,
        "module_closure": modules,
        "failure_explanation": {
            "classification": "STATIC_MISSING_DISPLAY_CLOCK_SUPPLIER_EXPLANATION",
            "failed_gate": OLD_GATE,
            "failed_node_role": "display-rsc",
            "failed_node_has_power_domain": False,
            "required_clock_supplier": "/soc/clock-controller@af00000",
            "required_supplier_module": DISPCC_MODULE,
            "supplier_module_selected": False,
            "fw_devlink_defers_before_rpmh_rsc_probe": True,
            "source_artifact_closure": True,
            "p242_runtime_supplier_state_observed": False,
            "p242_live_root_cause_proven": False,
            "replacement_live_state": "UNKNOWN",
        },
        "power_domain_provider": {
            "consumer": "/soc/rsc@17a00000",
            "provider": "/soc/psci/cluster-pd",
            "provider_parent": "/soc/psci",
            "provider_parent_compatible": "arm,psci-1.0",
            "provider_driver": "psci-cpuidle-domain",
            "provider_bind_path": (
                "/sys/bus/platform/drivers/psci-cpuidle-domain/soc:psci"
            ),
            "provider_registration": "of_genpd_add_provider_simple",
            "provider_builtin": True,
            "source_artifact_closure": True,
            "p242_live_provider_bind_observed": False,
        },
        "bounded_discriminator": {
            "action": "replace-display-rsc-and-gcc-gates-with-usb-provider-chain",
            "old_gate": OLD_GATE,
            "new_gate": NEW_GATE,
            "new_gate_role": "apps-rsc",
            "replaces_existing_gates": ["rpmh", "gcc-waipio"],
            "ordered_predicates": [
                {
                    "id": "psci-domain",
                    "path": (
                        "/sys/bus/platform/drivers/psci-cpuidle-domain/"
                        "soc:psci"
                    ),
                },
                {
                    "id": "apps-rsc",
                    "path": NEW_GATE,
                },
                {
                    "id": "apps-rpmh-clock",
                    "path": (
                        "/sys/bus/platform/drivers/clk-rpmh/"
                        "17a00000.rsc:qcom,rpmhclk"
                    ),
                },
                {
                    "id": "apps-rpmh-cxlvl",
                    "path": (
                        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
                        "17a00000.rsc:rpmh-regulator-cxlvl"
                    ),
                },
                {
                    "id": "apps-rpmh-mxlvl",
                    "path": (
                        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
                        "17a00000.rsc:rpmh-regulator-mxlvl"
                    ),
                },
                {
                    "id": "gcc-waipio",
                    "path": (
                        "/sys/bus/platform/drivers/gcc-waipio/"
                        "100000.clock-controller"
                    ),
                },
            ],
            "add_modules": [],
            "do_not_add": [DISPCC_MODULE],
            "resulting_gate_count": 12,
            "resulting_stage_range": {
                "first": "0x7b",
                "last": "0x86",
                "success": "0x8f",
            },
            "preserve_unreplaced_gate_order": True,
            "interpretation": {
                "psci-domain": "apps RSC power-domain provider registered",
                "apps-rsc": "USB-relevant RPMh parent bind",
                "apps-rpmh-clock": "GCC RPMh clock provider bind",
                "apps-rpmh-cxlvl": "GCC CX regulator provider bind",
                "apps-rpmh-mxlvl": "GCC MX regulator provider bind",
                "gcc-waipio": "transitive GCC supplier closure and bind",
            },
            "reason": "the display RSC is not on the required USB/GCC proof chain",
        },
        "proof_limits": {
            "apps_rsc_live_bind": False,
            "rpmh_child_provider_live_bind": False,
            "gcc_live_bind": False,
            "usb_live_state": False,
            "candidate_built": False,
            "device_contact": False,
            "live_authority": False,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "image_build": False,
            "flash": False,
            "authority_created": False,
        },
    }


def main() -> int:
    try:
        result = build_result()
    except (
        AuditError,
        OSError,
        p241.CheckError,
        planner.PlanError,
        boot_verify.BootVerifyError,
        dtbo_contract.ContractError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
