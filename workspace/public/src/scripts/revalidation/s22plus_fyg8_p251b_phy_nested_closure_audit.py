#!/usr/bin/env python3
"""Audit the exact nested FYG8 supplier graph below the SSUSB PHYs.

Host-only. The checker reuses the pinned P2.51 result, then verifies the
remaining PHY/GDSC DT, source, module, and ELF closure. It does not build,
contact a device, or grant live authority.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p241_dtbo_role_contract as dtbo_contract  # noqa: E402
import s22plus_fyg8_p243_rpmh_dependency_audit as p243  # noqa: E402
import s22plus_fyg8_p251_ssusb_dependency_audit as p251  # noqa: E402
import s22plus_fyg8_usb_role_static_re as usb_static_re  # noqa: E402


SCHEMA = "s22plus_fyg8_p251b_phy_nested_closure_audit_v1"
VERDICT = "PASS_P251B_PHY_NESTED_CLOSURE_HOST_ONLY"
TARGET = p251.TARGET

DEFAULT_VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
DEFAULT_P249_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p249/static-check-result.json"
)
DEFAULT_INVENTORY = Path("docs/module-map/s22plus-fyg8/inventory.tsv")
DEFAULT_DEPENDENCIES = Path(
    "docs/module-map/s22plus-fyg8/dependency-edges.tsv"
)

EXPECTED_SHA256 = {
    "vendor_ramdisk": "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193",
    "p249_static": "80d85c7bb7475c6eba784364f505079c0f16914254b86c6fdd815d3c1070954d",
    "inventory": "35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b",
    "dependencies": "ec7292c918270748e9bcfccdea454c2e35965acc202c1648ef215963777c5afa",
    "p251_helper": "3578b3df7da5e5c2dd98add8231fd0b16f69b21679f397380f406977786ad926",
    "boot_verify_helper": "e19d604039a744d14bcdbb495951e95f86666b6927061529e440aacb4b63381d",
    "base_source": p251.EXPECTED_SHA256["base_source"],
    "delta_source": p251.EXPECTED_SHA256["delta_source"],
}

SOURCE_MEMBERS = {
    "of_property": "kernel_platform/common/drivers/of/property.c",
    "of_platform": "kernel_platform/common/drivers/of/platform.c",
    "gdsc": "kernel_platform/msm-kernel/drivers/clk/qcom/gdsc-regulator.c",
    "rpmh_regulator": "kernel_platform/msm-kernel/drivers/regulator/rpmh-regulator.c",
    "pinctrl": "kernel_platform/msm-kernel/drivers/pinctrl/qcom/pinctrl-waipio.c",
    "hsphy": "kernel_platform/msm-kernel/drivers/usb/phy/phy-msm-snps-hs.c",
    "ssphy": "kernel_platform/msm-kernel/drivers/usb/phy/phy-msm-ssusb-qmp.c",
}

HS_PHY = "/soc/hsphy@88e3000"
SS_PHY = "/soc/ssphy@88e8000"
GDSC = "/soc/qcom,gdsc@149004"
TLMM = "/soc/pinctrl@f000000"
RPMH = "/soc/rsc@17a00000"
GCC = "/soc/clock-controller@100000"
RPMH_CLK = f"{RPMH}/qcom,rpmhclk"

# label, consumer, property, RPMh wrapper, leaf node, regulator-name, detail
SUPPLY_SPECS = (
    ("ssphy-vdd", SS_PHY, "vdd-supply", "ldob1", "regulator-pm8350-l1", "pm8350_l1", "0xa09"),
    ("ssphy-core", SS_PHY, "core-supply", "ldob6", "regulator-pm8350-l6", "pm8350_l6", "0xa0a"),
    ("hsphy-vdd", HS_PHY, "vdd-supply", "ldob5", "regulator-pm8350-l5", "pm8350_l5", "0xa0b"),
    (
        "hsphy-vdda18",
        HS_PHY,
        "vdda18-supply",
        "ldoc1",
        "regulator-pm8350c-l1",
        "pm8350c_l1",
        "0xa0c",
    ),
    (
        "hsphy-vdda33",
        HS_PHY,
        "vdda33-supply",
        "ldob2",
        "regulator-pm8350-l2",
        "pm8350_l2",
        "0xa0d",
    ),
)

MODULES = {
    "clk-rpmh.ko",
    "gcc-waipio.ko",
    "gdsc-regulator.ko",
    "phy-msm-snps-hs.ko",
    "phy-msm-ssusb-qmp.ko",
    "pinctrl-waipio.ko",
    "rpmh-regulator.ko",
}

# Exact probe symbol plus the minimum relocation set needed by this audit.
PROBES = {
    "gdsc-regulator.ko": (
        "gdsc_probe",
        {"devm_regulator_register", "devm_regulator_debug_register"},
    ),
    "phy-msm-snps-hs.ko": (
        "msm_hsphy_probe",
        {
            "__devm_reset_control_get",
            "devm_clk_get",
            "devm_regulator_get",
            "usb_add_phy_dev",
            "usb_remove_phy",
        },
    ),
    "phy-msm-ssusb-qmp.ko": (
        "msm_ssphy_qmp_probe",
        {
            "__devm_reset_control_get",
            "devm_clk_get",
            "devm_regulator_get",
            "usb_add_phy_dev",
        },
    ),
    "pinctrl-waipio.ko": ("waipio_pinctrl_probe", {"msm_pinctrl_probe"}),
    "rpmh-regulator.ko": (
        "rpmh_regulator_probe",
        {"cmd_db_read_addr", "devm_regulator_register", "of_platform_populate"},
    ),
}


class AuditError(ValueError):
    pass


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value


def require_tokens(text: str, label: str, tokens: tuple[str, ...]) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AuditError(f"{label} source contract missing: {missing}")


def read_source_members(
    archive_data: bytes, expected: dict[str, str]
) -> dict[str, bytes]:
    wanted = set(expected.values())
    found: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:gz") as archive:
            for member in archive:
                if member.name not in wanted:
                    continue
                if (
                    not member.isfile()
                    or member.name in found
                    or member.size > 2 * 1024 * 1024
                ):
                    raise AuditError(f"invalid source member: {member.name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AuditError(f"source member unreadable: {member.name}")
                payload = stream.read()
                if len(payload) != member.size:
                    raise AuditError(f"source member truncated: {member.name}")
                found[member.name] = payload
    except tarfile.TarError as exc:
        raise AuditError("base source archive parse failed") from exc
    missing = wanted - set(found)
    if missing:
        raise AuditError(f"source archive members missing: {sorted(missing)}")
    return {label: found[path] for label, path in expected.items()}


def audit_delta_no_override(
    archive_data: bytes, source_members: dict[str, str]
) -> dict[str, Any]:
    selected = set(source_members.values())
    regular: list[str] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                name = member.name.removeprefix("Kernel/")
                regular.append(name)
    except tarfile.TarError as exc:
        raise AuditError("delta source archive parse failed") from exc
    overlap = sorted(selected.intersection(regular))
    if overlap:
        raise AuditError(f"FYG8 delta overrides audited source: {overlap}")
    return {
        "regular_file_count": len(regular),
        "audited_member_override_count": 0,
        "verified": True,
    }


def wrapper_path(resource: str) -> str:
    return f"{RPMH}/rpmh-regulator-{resource}"


def wrapper_bind_path(resource: str) -> str:
    return (
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        f"17a00000.rsc:rpmh-regulator-{resource}"
    )


def audit_vendor_dtb(data: bytes) -> dict[str, Any]:
    blobs = p243.parse_concatenated_fdt(data)
    if len(blobs) != len(p251.EXPECTED_MODELS):
        raise AuditError("vendor DTB count mismatch")
    variants: list[dict[str, Any]] = []
    common: dict[str, Any] | None = None

    for index, (blob, model) in enumerate(zip(blobs, p251.EXPECTED_MODELS)):
        nodes = dtbo_contract.parse_fdt(blob)
        phandles = p243.phandle_map(nodes)
        root = p243.require_node(nodes, "/")
        hsphy = p243.require_node(nodes, HS_PHY)
        ssphy = p243.require_node(nodes, SS_PHY)
        gdsc = p243.require_node(nodes, GDSC)
        if p243.strings(root, "model") != (model,):
            raise AuditError(f"vendor DTB {index} model mismatch")

        hs_clocks = p251.parse_phandle_array(
            nodes, phandles, hsphy, "clocks", "#clock-cells"
        )
        ss_clocks = p251.parse_phandle_array(
            nodes, phandles, ssphy, "clocks", "#clock-cells"
        )
        hs_resets = p251.parse_phandle_array(
            nodes, phandles, hsphy, "resets", "#reset-cells"
        )
        ss_resets = p251.parse_phandle_array(
            nodes, phandles, ssphy, "resets", "#reset-cells"
        )
        if (
            p243.strings(hsphy, "compatible")
            != ("qcom,usb-hsphy-snps-femto",)
            or p243.strings(hsphy, "clock-names")
            != ("ref_clk_src", "ref_clk")
            or hs_clocks != (RPMH_CLK, GCC)
            or p243.strings(hsphy, "reset-names") != ("phy_reset",)
            or hs_resets != (GCC,)
        ):
            raise AuditError(f"vendor DTB {index} HS PHY clock/reset mismatch")
        if (
            p243.strings(ssphy, "compatible")
            != ("qcom,usb-ssphy-qmp-dp-combo",)
            or p243.strings(ssphy, "clock-names")
            != (
                "aux_clk",
                "pipe_clk",
                "pipe_clk_mux",
                "pipe_clk_ext_src",
                "ref_clk_src",
                "com_aux_clk",
                "ref_clk",
            )
            or ss_clocks != (GCC, GCC, GCC, GCC, RPMH_CLK, GCC, GCC)
            or p243.strings(ssphy, "reset-names")
            != ("global_phy_reset", "phy_reset")
            or ss_resets != (GCC, GCC)
        ):
            raise AuditError(f"vendor DTB {index} SS PHY clock/reset mismatch")

        supplies: dict[str, Any] = {}
        wrappers: dict[str, Any] = {}
        for (
            label,
            consumer_path,
            property_name,
            resource,
            leaf_name,
            regulator_name,
            detail,
        ) in SUPPLY_SPECS:
            consumer = p243.require_node(nodes, consumer_path)
            parent_path = wrapper_path(resource)
            leaf_path = f"{parent_path}/{leaf_name}"
            if p243.provider_path(consumer, property_name, phandles) != leaf_path:
                raise AuditError(f"vendor DTB {index} {label} supply mismatch")
            parent = p243.require_node(nodes, parent_path)
            leaf = p243.require_node(nodes, leaf_path)
            if (
                p243.strings(parent, "compatible")
                != ("qcom,rpmh-vrm-regulator",)
                or p243.strings(parent, "qcom,resource-name") != (resource,)
                or p243.strings(parent, "qcom,regulator-type")
                != ("pmic5-ldo",)
                or p243.strings(leaf, "regulator-name") != (regulator_name,)
            ):
                raise AuditError(f"vendor DTB {index} {resource} wrapper mismatch")
            supplies[label] = leaf_path
            wrappers[resource] = {
                "leaf": leaf_path,
                "regulator_name": regulator_name,
                "bind_path": wrapper_bind_path(resource),
                "detail": detail,
            }

        pinctrl = p251.parse_plain_phandles(phandles, ssphy, "pinctrl-0")
        expected_state = f"{TLMM}/usb_phy_ps/usb3phy_portselect_default"
        tlmm = p243.require_node(nodes, TLMM)
        if (
            pinctrl != (expected_state,)
            or p243.strings(tlmm, "compatible") != ("qcom,waipio-pinctrl",)
            or p243.provider_path(tlmm, "wakeup-parent", phandles)
            != "/soc/interrupt-controller@b220000"
        ):
            raise AuditError(f"vendor DTB {index} SS PHY pinctrl mismatch")

        external_gdsc = sorted(
            set(gdsc.properties)
            & {
                "clocks",
                "clock-names",
                "interconnects",
                "interconnect-names",
                "power-domains",
                "resets",
                "reset-names",
                "parent-supply",
                "qcom,clk-ctrl",
                "sw-reset",
            }
        )
        if (
            p243.strings(gdsc, "compatible") != ("qcom,gdsc",)
            or p243.provider_path(gdsc, "proxy-supply", phandles) != GDSC
            or external_gdsc
        ):
            raise AuditError(f"vendor DTB {index} GDSC closure mismatch")

        normalized = {
            "hsphy": {
                "clock_providers": hs_clocks,
                "reset_providers": hs_resets,
                "supplies": {
                    key: value
                    for key, value in supplies.items()
                    if key.startswith("hsphy-")
                },
            },
            "ssphy": {
                "clock_providers": ss_clocks,
                "reset_providers": ss_resets,
                "supplies": {
                    key: value
                    for key, value in supplies.items()
                    if key.startswith("ssphy-")
                },
                "pinctrl_state": expected_state,
                "pinctrl_owner": TLMM,
                "pinctrl_wakeup_parent": (
                    "/soc/interrupt-controller@b220000"
                ),
            },
            "gdsc": {
                "proxy_supply": GDSC,
                "external_supplier_properties": [],
            },
            "rpmh_wrappers": wrappers,
        }
        if common is not None and normalized != common:
            raise AuditError("vendor DTB nested closure differs by variant")
        common = normalized
        variants.append(
            {
                "index": index,
                "model": model,
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )

    assert common is not None
    return {
        "identity": receipt(data),
        "blob_count": len(variants),
        "variants": variants,
        "common": {"closure": common},
        "verified": True,
    }


def audit_source(members: dict[str, bytes]) -> dict[str, Any]:
    text = {name: p251.source_text(data, name) for name, data in members.items()}
    require_tokens(
        text["of_property"],
        "OF property",
        (
            'DEFINE_SIMPLE_PROP(pinctrl0, "pinctrl-0", NULL)',
            'DEFINE_SIMPLE_PROP(wakeup_parent, "wakeup-parent", NULL)',
            'DEFINE_SUFFIX_PROP(regulators, "-supply", NULL)',
            "{ .parse_prop = parse_pinctrl0, },",
            "{ .parse_prop = parse_wakeup_parent, },",
            "{ .parse_prop = parse_regulators, },",
            "if (of_is_ancestor_of(con_np, sup_np))",
        ),
    )
    require_tokens(
        text["of_platform"],
        "OF platform naming",
        (
            "static void of_device_make_bus_id(struct device *dev)",
            'dev_set_name(dev, dev_name(dev) ? "%s:%s" : "%s",',
            "kbasename(node->full_name), dev_name(dev));",
        ),
    )
    require_tokens(
        text["rpmh_regulator"],
        "RPMh regulator",
        (
            "static int rpmh_regulator_probe(struct platform_device *pdev)",
            "cmd_db_read_addr(aggr_vreg->resource_name)",
            "devm_regulator_register",
            '.name\t\t= "qcom,rpmh-regulator"',
        ),
    )
    require_tokens(
        text["pinctrl"],
        "Waipio pinctrl",
        (
            '"qcom,waipio-pinctrl"',
            '.name = "waipio-pinctrl"',
            "return msm_pinctrl_probe(pdev, pinctrl_data);",
        ),
    )
    require_tokens(
        text["gdsc"],
        "GDSC",
        (
            "static int gdsc_probe(struct platform_device *pdev)",
            "devm_regulator_register",
            "devm_regulator_debug_register",
        ),
    )
    for label, signature, ordered, remove_expected in (
        (
            "hsphy",
            "static int msm_hsphy_probe(struct platform_device *pdev)",
            (
                'devm_clk_get(dev, "ref_clk_src")',
                'devm_reset_control_get(dev, "phy_reset")',
                "ret = usb_add_phy_dev(&phy->phy);",
                "ret = msm_hsphy_regulator_init(phy);",
                "usb_remove_phy(&phy->phy);",
            ),
            True,
        ),
        (
            "ssphy",
            "static int msm_ssphy_qmp_probe(struct platform_device *pdev)",
            (
                "ret = msm_ssphy_qmp_get_clks(phy, dev);",
                'devm_reset_control_get(dev, "phy_reset")',
                "ret = usb_add_phy_dev(&phy->phy);",
                "ret = usb3_get_regulators(phy);",
            ),
            False,
        ),
    ):
        start = text[label].index(signature)
        end = text[label].index(
            "static int msm_hsphy_remove"
            if label == "hsphy"
            else "static int msm_ssphy_qmp_remove"
        )
        probe = text[label][start:end]
        positions = [probe.index(token) for token in ordered]
        if positions != sorted(positions):
            raise AuditError(f"{label} acquisition/cleanup order mismatch")
        if ("usb_remove_phy(&phy->phy);" in probe) != remove_expected:
            raise AuditError(f"{label} failed-probe cleanup mismatch")

    return {
        "members": {
            name: {**receipt(data), "archive_path": SOURCE_MEMBERS[name]}
            for name, data in members.items()
        },
        "fw_devlink_parses_pinctrl_and_supplies": True,
        "gdsc_self_proxy_link_rejected_as_self_ancestor": True,
        "hsphy_regulator_failure_removes_registered_phy": True,
        "ssphy_regulator_failure_after_usb_add_has_no_probe_cleanup": True,
        "verified": True,
    }


def hard_closure(target: str, parents: dict[str, set[str]]) -> set[str]:
    result: set[str] = set()
    pending = [target]
    while pending:
        for dependency in parents.get(pending.pop(), set()):
            if dependency not in result:
                result.add(dependency)
                pending.append(dependency)
    return result


def audit_modules(
    ramdisk: bytes,
    static_data: bytes,
    inventory_data: bytes,
    dependencies_data: bytes,
    plan_data: bytes,
) -> dict[str, Any]:
    static = json_object(static_data, "P2.49 static result")
    try:
        static_modules = static["candidate"]["module_closure"]["modules"]
        effective = static["candidate"]["effective_rootfs"]
    except (KeyError, TypeError) as exc:
        raise AuditError("P2.49 static result shape mismatch") from exc
    if (
        static.get("verdict")
        != "PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
        or len(static_modules) != 59
        or effective.get("module_count") != 59
        or effective.get("verified") is not True
    ):
        raise AuditError("P2.49 static closure did not pass")

    selected = {
        match.group(1)
        for match in p251.MODULE_RE.finditer(
            p251.ascii_text(plan_data, "P2.49 plan")
        )
    }
    if len(selected) != 59 or not MODULES.issubset(selected):
        raise AuditError("P2.49 selected-module closure mismatch")

    cpio = boot_verify.decompress_lz4_stream_python(
        ramdisk, expected_size=63_974_144, maximum=80 * 1024 * 1024
    )
    entries = boot_verify.parse_newc(cpio)
    by_name = {entry.name: entry for entry in entries}
    if len(entries) != 452 or len(by_name) != len(entries):
        raise AuditError("vendor ramdisk newc shape mismatch")

    inventory = {
        row["filename"]: row
        for row in p243.parse_tsv(inventory_data, "module inventory")
    }
    parents: dict[str, set[str]] = {}
    for row in p243.parse_tsv(dependencies_data, "module dependencies"):
        if row.get("relation") == "hard":
            parents.setdefault(row["after"], set()).add(row["before"])
    static_by_name = {row["file"]: row for row in static_modules}

    identities: dict[str, Any] = {}
    closures: dict[str, Any] = {}
    module_bytes: dict[str, bytes] = {}
    for name in sorted(MODULES):
        entry = by_name.get(f"lib/modules/{name}")
        expected = static_by_name.get(name)
        metadata = inventory.get(name)
        if entry is None or expected is None or metadata is None:
            raise AuditError(f"exact module missing: {name}")
        actual = receipt(entry.data)
        if (
            entry.file_type != "regular"
            or actual
            != {"size": expected.get("size"), "sha256": expected.get("sha256")}
            or int(metadata["size_bytes"]) != actual["size"]
            or metadata["sha256"] != actual["sha256"]
        ):
            raise AuditError(f"exact module identity mismatch: {name}")
        closure = hard_closure(name, parents)
        missing = sorted(closure - selected)
        if missing:
            raise AuditError(f"hard closure missing for {name}: {missing}")
        identities[name] = actual
        closures[name] = {
            "direct": sorted(parents.get(name, set())),
            "recursive": sorted(closure),
            "missing_from_plan": [],
        }
        module_bytes[name] = entry.data

    elf: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="s22plus-p251b-") as temp_dir:
        for name, (probe, required_calls) in PROBES.items():
            path = Path(temp_dir) / name
            path.write_bytes(module_bytes[name])
            symbols, by_address = usb_static_re.parse_symbols(path)
            if probe not in symbols:
                raise AuditError(f"exact probe symbol missing: {name}")
            calls = {
                callee
                for caller, callee in usb_static_re.parse_call_edges(
                    path, by_address
                )
                if caller == probe
            }
            if not required_calls.issubset(calls):
                raise AuditError(f"exact probe call closure mismatch: {name}")
            undefined = usb_static_re.parse_undefined(path)
            tuning_imports = sorted(
                {"sysfs_create_group", "sysfs_remove_group"} & undefined
            )
            elf[name] = {
                "probe_symbol": probe,
                "required_calls": sorted(required_calls),
                "tuning_sysfs_imports": tuning_imports,
                "tuning_sysfs_import": bool(tuning_imports),
            }
    if any(
        elf[name]["tuning_sysfs_import"]
        for name in ("phy-msm-snps-hs.ko", "phy-msm-ssusb-qmp.ko")
    ):
        raise AuditError("exact PHY module contains tuning sysfs")

    return {
        "vendor_ramdisk": receipt(ramdisk),
        "vendor_newc": {"size": len(cpio), "entry_count": len(entries)},
        "p249_static": receipt(static_data),
        "selected_module_count": len(selected),
        "effective_rootfs_module_count": effective["module_count"],
        "identities": identities,
        "hard_closures": closures,
        "elf": elf,
        "exact_phy_modules_compile_tuning_sysfs": False,
        "verified": True,
    }


def nested_checks() -> list[dict[str, str]]:
    checks = [
        {
            "id": "ssphy-tlmm",
            "path": "/sys/bus/platform/drivers/waipio-pinctrl/f000000.pinctrl",
            "detail": "0xa08",
        }
    ]
    checks.extend(
        {
            "id": label,
            "path": wrapper_bind_path(resource),
            "detail": detail,
        }
        for label, _consumer, _property, resource, _leaf, _name, detail in SUPPLY_SPECS
    )
    return checks


def build_result() -> dict[str, Any]:
    root = p251.repo_root()
    prerequisite = p251.build_result()
    if prerequisite.get("verdict") != p251.VERDICT:
        raise AuditError("P2.51 prerequisite did not pass")

    paths = {
        "vendor_ramdisk": root / DEFAULT_VENDOR_RAMDISK,
        "p249_static": root / DEFAULT_P249_STATIC,
        "inventory": root / DEFAULT_INVENTORY,
        "dependencies": root / DEFAULT_DEPENDENCIES,
        "p251_helper": SCRIPT_DIR / "s22plus_fyg8_p251_ssusb_dependency_audit.py",
        "boot_verify_helper": SCRIPT_DIR / "s22plus_boot_verify.py",
        "base_source": root / p251.DEFAULT_BASE_SOURCE,
        "delta_source": root / p251.DEFAULT_DELTA_SOURCE,
    }
    limits = {
        "vendor_ramdisk": 128 * 1024 * 1024,
        "p249_static": 4 * 1024 * 1024,
        "inventory": 2 * 1024 * 1024,
        "dependencies": 2 * 1024 * 1024,
        "p251_helper": 2 * 1024 * 1024,
        "boot_verify_helper": 2 * 1024 * 1024,
        "base_source": 700 * 1024 * 1024,
        "delta_source": 8 * 1024 * 1024,
    }
    data = {
        label: p243.stable_read(
            path, label, EXPECTED_SHA256[label], limits[label]
        )
        for label, path in paths.items()
    }
    vendor_dtb = p243.stable_read(
        root / p251.DEFAULT_VENDOR_DTB,
        "vendor DTB",
        p251.EXPECTED_SHA256["vendor_dtb"],
        4 * 1024 * 1024,
    )
    plan = p243.stable_read(
        root / p251.DEFAULT_PLAN,
        "P2.49 plan",
        p251.EXPECTED_SHA256["plan"],
        1024 * 1024,
    )
    base_source = data.pop("base_source")
    delta_source = data.pop("delta_source")
    base_source_receipt = receipt(base_source)
    delta_source_receipt = receipt(delta_source)
    source_members = read_source_members(base_source, SOURCE_MEMBERS)
    source_delta = audit_delta_no_override(delta_source, SOURCE_MEMBERS)
    del base_source, delta_source

    tree = audit_vendor_dtb(vendor_dtb)
    source = audit_source(source_members)
    modules = audit_modules(
        data["vendor_ramdisk"],
        data["p249_static"],
        data["inventory"],
        data["dependencies"],
        plan,
    )
    classifier = {
        "frontier_stage": "0x84",
        "frontier_item_index": 9,
        "add_modules": [],
        "add_stages": [],
        "direct_checks": [
            {"id": name, "path": path, "detail": detail}
            for name, path, detail in p251.PROVIDER_CHECKS
        ],
        "nested_branch_checks": nested_checks(),
        "phy_checks": [
            {"id": name, "path": path, "detail": detail}
            for name, path, detail in p251.PHY_CHECKS
        ],
        "terminal_details": {
            "0xa10": "all enumerated providers bound; waiting_for_supplier=1",
            "0xa30": "all dependencies ready; parent unbound after grace",
        },
        "maximum_added_runtime_sec": 5,
        "single_source_requirement": (
            "define the exact accepted details once in the P2.52 descriptor SoT"
        ),
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "prerequisite": {
            "p251_verdict": prerequisite["verdict"],
            "p251_helper": receipt(data["p251_helper"]),
            "boot_verify_helper": receipt(data["boot_verify_helper"]),
            "base_source": base_source_receipt,
            "delta_source": delta_source_receipt,
            "source_delta": source_delta,
        },
        "vendor_dtb": tree,
        "source": source,
        "modules": modules,
        "bounded_classifier_refinement": classifier,
        "reasoning_ledger": [
            {
                "evidence": "four DTBs have one lower supplier closure",
                "inference": "variant selection is not the P2.50 cause",
                "limit": "candidate bind state is unobserved",
            },
            {
                "evidence": "GDSC has only a rejected self supply link",
                "inference": "missing GDSC is an internal probe branch",
                "limit": "probe return is unobserved",
            },
            {
                "evidence": "exact modules and hard closures are selected",
                "inference": "module growth is unjustified",
                "limit": "module presence is not bind proof",
            },
            {
                "evidence": "exact PHY ELF has no tuning sysfs import",
                "inference": "PHY tuning config is not the bind blocker",
                "limit": "other probe errors remain open",
            },
            {
                "evidence": "HS cleans failed registration; SS does not",
                "inference": "SS cleanup is a conditional later lead",
                "limit": "no leak was observed live",
            },
        ],
        "conclusion": {
            "exact_live_root_cause_identified": False,
            "variant_or_missing_module_explanation": False,
            "nested_runtime_unknowns": [
                "five exact RPMh LDO wrapper binds",
                "Waipio TLMM bind",
                "HS PHY bind",
                "SS PHY bind",
                "GDSC probe result",
            ],
            "next_action": "implement the existing-stage P2.52 branch-only classifier",
            "another_unchanged_live_candidate_justified": False,
        },
        "proof_limits": {
            "nested_provider_live_bind": False,
            "phy_live_bind": False,
            "gdsc_probe_return": False,
            "ssphy_failed_probe_leak_observed": False,
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
        p243.AuditError,
        p251.AuditError,
        boot_verify.BootVerifyError,
        usb_static_re.StaticReError,
        dtbo_contract.ContractError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
