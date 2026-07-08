#!/usr/bin/env python3
"""Build the S22+ M23 DTS-exact QMP/DWC3 native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M23 is the no-EUD pivot candidate after EUD was proven TrustZone-gated. It
derives the USB QMP/DWC3 runtime module list from the stock vendor DTB
references instead of loading Android's whole first-stage module set:

* /soc/ssusb@a600000
* /soc/ssusb@a600000/dwc3@a600000
* the DT-referenced HS and SS/QMP PHY nodes
* referenced supplies/clocks/resets/interconnects/pinctrl/IOMMU providers
* the non-EUD vendor dwc3_msm softdep PHY preloads
* usb_f_ss_acm.ko for the intended configfs ACM function

The boot ramdisk gets only a generated /init and a small text module list.
Module binaries remain in stock vendor_boot /lib/modules.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_direct_p3_boot import (
    BOOT_PARTITION_SIZE,
    DEFAULT_ODIN,
    display_path,
    repo_root,
    require_ok,
    resolve,
    run,
    sha256_file,
    tar_members,
    write_ap_tar,
    write_boot_lz4,
)
from build_s22plus_inplace_m4t1_magiskboot import (
    DEFAULT_BASE_BOOT,
    DEFAULT_MAGISK_APK,
    DEFAULT_MAGISKBOOT,
    EXPECTED_BASE_BOOT_SHA256,
    EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
    diff_ranges,
    ensure_magiskboot,
    run_in_dir,
)
from build_s22plus_ramoops_dtbo_enable import (
    decode_string_list,
    iter_fdt_blobs,
    parse_fdt_props,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1")
DEFAULT_TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")
DEFAULT_VENDOR_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/"
    "unpack-vendor-boot/dtb"
)
DEFAULT_VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/"
    "unpack-vendor-boot/vendor_ramdisk00"
)
DEFAULT_LZ4 = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")

MARKER = "S22_NATIVE_INIT_USB_ACM_M23_DTS_QMP"
MODULES_RAMDISK = "s22plus_m23_dts_exact_qmp.modules"
GENERATED_SOURCE_NAME = "s22plus_init_usb_acm_m23_dts_exact_qmp.c"
GENERATED_INIT_NAME = "s22plus_init_usb_acm_m23_dts_exact_qmp"

EXPECTED_KO_COUNT = 441
EXPECTED_MODULES_LOAD_COUNT = 140
EXPECTED_MODULES_LOAD_RECOVERY_COUNT = 446
EXPECTED_MODULES_DEP_COUNT = 441
RUNTIME_MODULES_DTS_EXACT_QMP_BUF = 8192
RUNTIME_MODULE_NAME_BUF = 128

MODULES_ALIAS = "lib/modules/modules.alias"
MODULES_LOAD = "lib/modules/modules.load"
MODULES_LOAD_RECOVERY = "lib/modules/modules.load.recovery"
MODULES_SOFTDEP = "lib/modules/modules.softdep"
MODULES_DEP = "lib/modules/modules.dep"

SSUSB_PATH = "/soc/ssusb@a600000"
DWC3_PATH = "/soc/ssusb@a600000/dwc3@a600000"
EUD_PATH = "/soc/qcom,msm-eud@88e0000"

RESET_ANOMALY_BLOCKLIST = {
    "abc.ko",
    "gh_virt_wdt.ko",
    "minidump.ko",
    "qcom_wdt_core.ko",
    "sec_debug.ko",
    "sec_debug_region.ko",
}

MANUAL_COMPAT_MODULES = {
    "qcom,gdsc": "gdsc-regulator.ko",
    "qcom,rpmh-arc-regulator": "rpmh-regulator.ko",
    "qcom,rpmh-vrm-regulator": "rpmh-regulator.ko",
}

DWC3_SOFTDEP_PRE_INCLUDED = [
    "phy-generic.ko",
    "phy-msm-snps-eusb2.ko",
]
DWC3_SOFTDEP_EXCLUDED = [
    "eud.ko",
    "ucsi_glink.ko",
]
RUNTIME_FUNCTION_MODULES = [
    "usb_f_ss_acm.ko",
]

EXPECTED_M23_DTS_EXACT_QMP_SUBSET = [
    "clk-rpmh.ko",
    "gcc-waipio.ko",
    "icc-rpmh.ko",
    "qcom_ipc_logging.ko",
    "rpmh-regulator.ko",
    "clk-dummy.ko",
    "clk-qcom.ko",
    "cmd-db.ko",
    "debug-regulator.ko",
    "gdsc-regulator.ko",
    "icc-bcm-voter.ko",
    "icc-debug.ko",
    "iommu-logger.ko",
    "pinctrl-waipio.ko",
    "qnoc-waipio.ko",
    "phy-generic.ko",
    "pinctrl-msm.ko",
    "proxy-consumer.ko",
    "qcom_iommu_util.ko",
    "qcom_rpmh.ko",
    "qcom-scm.ko",
    "qnoc-qos.ko",
    "sec_class.ko",
    "secure_buffer.ko",
    "smem.ko",
    "socinfo.ko",
    "arm_smmu.ko",
    "phy-msm-ssusb-qmp.ko",
    "phy-msm-snps-hs.ko",
    "phy-msm-snps-eusb2.ko",
    "dwc3-msm.ko",
    "usb_f_ss_mon_gadget.ko",
    "usb_f_ss_acm.ko",
    "repeater.ko",
    "redriver.ko",
    "usb_notify_layer.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "usb_typec_manager.ko",
    "if_cb_manager.ko",
    "pdic_notifier_module.ko",
    "qc_usb_audio.ko",
]


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def module_basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def be_u32_cells(value: bytes) -> list[int]:
    if len(value) % 4 != 0:
        raise SystemExit(f"FDT cell payload is not 4-byte aligned: len={len(value)}")
    return [int.from_bytes(value[idx : idx + 4], byteorder="big") for idx in range(0, len(value), 4)]


def safe_decode_strings(value: bytes) -> list[str]:
    try:
        return decode_string_list(value)
    except Exception:
        return []


def parent_path(path: str) -> str | None:
    if path == "/":
        return None
    parent = path.rsplit("/", 1)[0]
    return parent or "/"


def parse_modules_dep(lines: list[str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for line in lines:
        lhs, sep, rhs = line.partition(":")
        if sep != ":":
            raise SystemExit(f"malformed modules.dep line without colon: {line!r}")
        name = module_basename(lhs.strip())
        dep_names = [module_basename(item) for item in rhs.split()]
        if name in deps:
            raise SystemExit(f"duplicate modules.dep lhs: {name}")
        deps[name] = dep_names
    return deps


def parse_modules_alias(text: str, module_names: set[str]) -> dict[str, list[str]]:
    compat_to_modules: dict[str, set[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("alias of:N*T*C"):
            continue
        rest = line[len("alias of:N*T*C") :]
        parts = rest.split()
        if len(parts) != 2:
            continue
        compat_token, module_token = parts
        compat = compat_token[:-2] if compat_token.endswith("C*") else compat_token
        candidates = [
            f"{module_token}.ko",
            f"{module_token.replace('_', '-')}.ko",
            f"{module_token.replace('-', '_')}.ko",
        ]
        found = [candidate for candidate in candidates if candidate in module_names]
        if found:
            compat_to_modules.setdefault(compat, set()).add(found[0])
    return {compat: sorted(modules) for compat, modules in sorted(compat_to_modules.items())}


def build_path_props(blob_data: bytes) -> tuple[dict[str, dict[str, bytes]], dict[int, str]]:
    blobs = iter_fdt_blobs(blob_data)
    if not blobs:
        raise SystemExit("vendor DTB contains no FDT blobs")
    props = parse_fdt_props(blobs[0])
    path_props: dict[str, dict[str, bytes]] = {}
    phandles: dict[int, str] = {}
    for prop in props:
        path_props.setdefault(prop.path, {})[prop.name] = prop.value
    for path, values in path_props.items():
        phandle_value = values.get("phandle")
        if phandle_value and len(phandle_value) == 4:
            phandles[int.from_bytes(phandle_value, byteorder="big")] = path
    return path_props, phandles


def all_blob_path_props(dtb_image: bytes) -> list[tuple[int, dict[str, dict[str, bytes]], dict[int, str]]]:
    contexts: list[tuple[int, dict[str, dict[str, bytes]], dict[int, str]]] = []
    blobs = iter_fdt_blobs(dtb_image)
    if len(blobs) != 4:
        raise SystemExit(f"unexpected vendor DTB blob count: {len(blobs)} != 4")
    for blob in blobs:
        path_props: dict[str, dict[str, bytes]] = {}
        phandles: dict[int, str] = {}
        for prop in parse_fdt_props(blob):
            path_props.setdefault(prop.path, {})[prop.name] = prop.value
        for path, values in path_props.items():
            phandle_value = values.get("phandle")
            if phandle_value and len(phandle_value) == 4:
                phandles[int.from_bytes(phandle_value, byteorder="big")] = path
        contexts.append((blob.index, path_props, phandles))
    return contexts


def prop_u32(path_props: dict[str, dict[str, bytes]], path: str, name: str) -> int | None:
    value = path_props.get(path, {}).get(name)
    if value is None:
        return None
    cells = be_u32_cells(value)
    if len(cells) != 1:
        raise SystemExit(f"{path}/{name} is not a single u32 cell: {cells}")
    return cells[0]


def parse_phandle_array(
    *,
    path_props: dict[str, dict[str, bytes]],
    phandles: dict[int, str],
    owner_path: str,
    prop_name: str,
    cell_count_prop: str,
) -> list[dict[str, Any]]:
    value = path_props.get(owner_path, {}).get(prop_name)
    if value is None:
        return []
    cells = be_u32_cells(value)
    refs: list[dict[str, Any]] = []
    idx = 0
    while idx < len(cells):
        phandle = cells[idx]
        provider_path = phandles.get(phandle)
        if provider_path is None:
            raise SystemExit(f"{owner_path}/{prop_name} expected phandle 0x{phandle:x}, not found")
        arg_count = prop_u32(path_props, provider_path, cell_count_prop)
        if arg_count is None:
            if cell_count_prop == "#phy-cells":
                arg_count = 0
            else:
                raise SystemExit(f"{owner_path}/{prop_name} provider {provider_path} lacks {cell_count_prop}")
        start = idx + 1
        end = start + arg_count
        if end > len(cells):
            raise SystemExit(f"{owner_path}/{prop_name} truncated specifier for {provider_path}")
        refs.append(
            {
                "prop": prop_name,
                "phandle": f"0x{phandle:x}",
                "provider_path": provider_path,
                "specifier": [f"0x{cell:x}" for cell in cells[start:end]],
                "cell_count_prop": cell_count_prop,
                "cell_count": arg_count,
            }
        )
        idx = end
    return refs


def parse_plain_phandle_list(
    *,
    path_props: dict[str, dict[str, bytes]],
    phandles: dict[int, str],
    owner_path: str,
    prop_name: str,
) -> list[dict[str, Any]]:
    value = path_props.get(owner_path, {}).get(prop_name)
    if value is None:
        return []
    refs: list[dict[str, Any]] = []
    for phandle in be_u32_cells(value):
        provider_path = phandles.get(phandle)
        if provider_path is None:
            raise SystemExit(f"{owner_path}/{prop_name} expected phandle 0x{phandle:x}, not found")
        refs.append(
            {
                "prop": prop_name,
                "phandle": f"0x{phandle:x}",
                "provider_path": provider_path,
                "specifier": [],
                "cell_count_prop": None,
                "cell_count": 0,
            }
        )
    return refs


def parse_single_phandle(
    *,
    path_props: dict[str, dict[str, bytes]],
    phandles: dict[int, str],
    owner_path: str,
    prop_name: str,
) -> list[dict[str, Any]]:
    value = path_props.get(owner_path, {}).get(prop_name)
    if value is None:
        return []
    cells = be_u32_cells(value)
    if len(cells) != 1:
        raise SystemExit(f"{owner_path}/{prop_name} expected single phandle, got {cells}")
    phandle = cells[0]
    provider_path = phandles.get(phandle)
    if provider_path is None:
        raise SystemExit(f"{owner_path}/{prop_name} expected phandle 0x{phandle:x}, not found")
    return [
        {
            "prop": prop_name,
            "phandle": f"0x{phandle:x}",
            "provider_path": provider_path,
            "specifier": [],
            "cell_count_prop": None,
            "cell_count": 0,
        }
    ]


def provider_modules_for_path(
    *,
    path_props: dict[str, dict[str, bytes]],
    compat_to_modules: dict[str, list[str]],
    provider_path: str,
) -> dict[str, Any]:
    cur = provider_path
    chain: list[dict[str, Any]] = []
    while cur is not None:
        compatible = safe_decode_strings(path_props.get(cur, {}).get("compatible", b""))
        modules: set[str] = set()
        for compat in compatible:
            modules.update(compat_to_modules.get(compat, []))
            manual = MANUAL_COMPAT_MODULES.get(compat)
            if manual:
                modules.add(manual)
        chain.append({"path": cur, "compatible": compatible, "modules": sorted(modules)})
        if modules:
            return {
                "requested_path": provider_path,
                "resolved_path": cur,
                "compatible": compatible,
                "modules": sorted(modules),
                "chain": chain,
            }
        cur = parent_path(cur)
    return {
        "requested_path": provider_path,
        "resolved_path": None,
        "compatible": [],
        "modules": [],
        "chain": chain,
    }


def direct_modules_for_node(
    *,
    path_props: dict[str, dict[str, bytes]],
    compat_to_modules: dict[str, list[str]],
    path: str,
) -> dict[str, Any]:
    compatible = safe_decode_strings(path_props.get(path, {}).get("compatible", b""))
    modules: set[str] = set()
    for compat in compatible:
        modules.update(compat_to_modules.get(compat, []))
        manual = MANUAL_COMPAT_MODULES.get(compat)
        if manual:
            modules.add(manual)
    return {"path": path, "compatible": compatible, "modules": sorted(modules)}


def collect_references(
    path_props: dict[str, dict[str, bytes]],
    phandles: dict[int, str],
    owner_path: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for prop_name, cell_count_prop in (
        ("clocks", "#clock-cells"),
        ("resets", "#reset-cells"),
        ("interconnects", "#interconnect-cells"),
        ("iommus", "#iommu-cells"),
        ("usb-phy", "#phy-cells"),
        ("power-domains", "#power-domain-cells"),
    ):
        refs.extend(
            parse_phandle_array(
                path_props=path_props,
                phandles=phandles,
                owner_path=owner_path,
                prop_name=prop_name,
                cell_count_prop=cell_count_prop,
            )
        )
    for prop_name in sorted(name for name in path_props.get(owner_path, {}) if name.endswith("-supply")):
        refs.extend(
            parse_single_phandle(
                path_props=path_props,
                phandles=phandles,
                owner_path=owner_path,
                prop_name=prop_name,
            )
        )
    refs.extend(
        parse_plain_phandle_list(
            path_props=path_props,
            phandles=phandles,
            owner_path=owner_path,
            prop_name="pinctrl-0",
        )
    )
    refs.extend(
        parse_plain_phandle_list(
            path_props=path_props,
            phandles=phandles,
            owner_path=owner_path,
            prop_name="extcon",
        )
    )
    return refs


def transitive_module_closure(
    *,
    seeds: set[str],
    dep_map: dict[str, list[str]],
    recovery_lines: list[str],
) -> dict[str, Any]:
    closure: set[str] = set()
    blocked_edges: set[str] = set()
    missing_modules: set[str] = set()
    stack = sorted(seeds)
    while stack:
        module = stack.pop()
        if module in closure:
            continue
        if module in RESET_ANOMALY_BLOCKLIST:
            blocked_edges.add(module)
            continue
        if module not in dep_map:
            missing_modules.add(module)
            continue
        closure.add(module)
        for dep in dep_map[module]:
            if dep in RESET_ANOMALY_BLOCKLIST:
                blocked_edges.add(dep)
            elif dep not in closure:
                stack.append(dep)
    if missing_modules:
        raise SystemExit(f"module seed/dependency missing from modules.dep: {sorted(missing_modules)}")
    recovery_set = set(recovery_lines)
    closure_not_recovery = sorted(closure - recovery_set)
    if closure_not_recovery:
        raise SystemExit(f"M23 closure is not wholly in recovery order: {closure_not_recovery}")
    ordered = [module for module in recovery_lines if module in closure]
    nonblocked_missing_edges = {
        module: [dep for dep in dep_map[module] if dep not in closure and dep not in RESET_ANOMALY_BLOCKLIST]
        for module in ordered
    }
    nonblocked_missing_edges = {module: deps for module, deps in nonblocked_missing_edges.items() if deps}
    if nonblocked_missing_edges:
        raise SystemExit(f"M23 closure has unresolved non-blocked dependency edges: {nonblocked_missing_edges}")
    if ordered != EXPECTED_M23_DTS_EXACT_QMP_SUBSET:
        raise SystemExit(
            "M23 DTS-exact QMP subset drifted:\n"
            f"actual={ordered!r}\nexpected={EXPECTED_M23_DTS_EXACT_QMP_SUBSET!r}"
        )
    subset_text = "".join(f"{module}\n" for module in ordered)
    if len(subset_text.encode("utf-8")) >= RUNTIME_MODULES_DTS_EXACT_QMP_BUF:
        raise SystemExit(
            "M23 module list does not fit runtime parser buffer: "
            f"{len(subset_text.encode('utf-8'))} >= {RUNTIME_MODULES_DTS_EXACT_QMP_BUF}"
        )
    too_long = [module for module in ordered if len(module) >= RUNTIME_MODULE_NAME_BUF]
    if too_long:
        raise SystemExit(f"M23 module basename exceeds runtime parser buffer: {too_long[:5]}")
    forbidden_present = sorted(set(ordered) & (RESET_ANOMALY_BLOCKLIST | {"eud.ko", "ucsi_glink.ko"}))
    if forbidden_present:
        raise SystemExit(f"forbidden module leaked into M23 subset: {forbidden_present}")
    return {
        "seeds": sorted(seeds),
        "subset": ordered,
        "subset_count": len(ordered),
        "subset_bytes": len(subset_text.encode("utf-8")),
        "subset_max_basename_len": max(len(module) for module in ordered),
        "subset_recovery_positions": {module: recovery_lines.index(module) + 1 for module in ordered},
        "subset_text": subset_text,
        "blocked_dependency_edges": sorted(blocked_edges),
        "blocklist": sorted(RESET_ANOMALY_BLOCKLIST),
    }


def derive_dts_exact_qmp(
    *,
    dtb_image: bytes,
    compat_to_modules: dict[str, list[str]],
    dep_map: dict[str, list[str]],
    recovery_lines: list[str],
) -> dict[str, Any]:
    blob_results: list[dict[str, Any]] = []
    closure_results: list[dict[str, Any]] = []
    for blob_index, path_props, phandles in all_blob_path_props(dtb_image):
        if SSUSB_PATH not in path_props or DWC3_PATH not in path_props:
            raise SystemExit(f"blob {blob_index} lacks required USB target nodes")
        usb_phy_refs = parse_phandle_array(
            path_props=path_props,
            phandles=phandles,
            owner_path=DWC3_PATH,
            prop_name="usb-phy",
            cell_count_prop="#phy-cells",
        )
        phy_paths = [ref["provider_path"] for ref in usb_phy_refs]
        target_paths = [SSUSB_PATH, DWC3_PATH, *phy_paths]

        direct_node_modules = [
            direct_modules_for_node(path_props=path_props, compat_to_modules=compat_to_modules, path=path)
            for path in target_paths
        ]
        seeds: set[str] = set(RUNTIME_FUNCTION_MODULES)
        seed_reasons: dict[str, list[str]] = {module: ["runtime-configfs-acm-function"] for module in RUNTIME_FUNCTION_MODULES}
        for item in direct_node_modules:
            for module in item["modules"]:
                seeds.add(module)
                seed_reasons.setdefault(module, []).append(f"direct-compatible:{item['path']}")
        for module in DWC3_SOFTDEP_PRE_INCLUDED:
            seeds.add(module)
            seed_reasons.setdefault(module, []).append("dwc3_msm-softdep-pre-non-eud")

        references: list[dict[str, Any]] = []
        provider_modules: list[dict[str, Any]] = []
        excluded_references: list[dict[str, Any]] = []
        for owner_path in target_paths:
            for ref in collect_references(path_props, phandles, owner_path):
                references.append({"owner_path": owner_path, **ref})
                provider_path = ref["provider_path"]
                if provider_path == EUD_PATH or ref["prop"] == "extcon":
                    excluded_references.append(
                        {
                            "owner_path": owner_path,
                            **ref,
                            "reason": "EUD/extcon excluded: retail TrustZone-gated EUD attach is closed and this candidate does not open EUD",
                        }
                    )
                    continue
                resolved = provider_modules_for_path(
                    path_props=path_props,
                    compat_to_modules=compat_to_modules,
                    provider_path=provider_path,
                )
                provider_modules.append({"owner_path": owner_path, "ref": ref, "resolved": resolved})
                if not resolved["modules"]:
                    raise SystemExit(f"no provider module resolved for {owner_path}/{ref['prop']} -> {provider_path}")
                for module in resolved["modules"]:
                    seeds.add(module)
                    seed_reasons.setdefault(module, []).append(f"provider:{owner_path}:{ref['prop']}:{provider_path}")

        closure = transitive_module_closure(seeds=seeds, dep_map=dep_map, recovery_lines=recovery_lines)
        blob_result = {
            "blob_index": blob_index,
            "target_paths": target_paths,
            "usb_phy_paths": phy_paths,
            "direct_node_modules": direct_node_modules,
            "references": references,
            "provider_modules": provider_modules,
            "excluded_references": excluded_references,
            "seed_modules_by_reason": {module: sorted(reasons) for module, reasons in sorted(seed_reasons.items())},
            "softdep_included": DWC3_SOFTDEP_PRE_INCLUDED,
            "softdep_excluded": DWC3_SOFTDEP_EXCLUDED,
        }
        blob_results.append(blob_result)
        closure_results.append(closure)

    first_subset = closure_results[0]["subset"]
    first_blocked = closure_results[0]["blocked_dependency_edges"]
    for idx, closure in enumerate(closure_results[1:], start=1):
        if closure["subset"] != first_subset:
            raise SystemExit(f"DTS blob {idx} derives a different M23 module subset")
        if closure["blocked_dependency_edges"] != first_blocked:
            raise SystemExit(f"DTS blob {idx} derives different blocked dependency edges")

    return {
        "dtb_blob_count": len(blob_results),
        "blob_results": blob_results,
        "order_source": "stock modules.load.recovery order after DTS-derived seed transitive modules.dep closure",
        "eud_policy": "EUD extcon observed but excluded; no EUD enable/open because Phase-B proved TZ-gated rc:-22",
        "dts_exact_qmp": {key: value for key, value in closure_results[0].items() if key != "subset_text"},
        "subset_text": str(closure_results[0]["subset_text"]),
    }


def extract_vendor_metadata(vendor_ramdisk: Path, lz4_tool: Path, build_dir: Path) -> dict[str, Any]:
    if not vendor_ramdisk.exists():
        raise SystemExit(f"vendor ramdisk missing: {vendor_ramdisk}")
    if not lz4_tool.exists():
        raise SystemExit(f"lz4 tool missing: {lz4_tool}")
    cpio_result = run([lz4_tool, "-dc", vendor_ramdisk])
    require_ok(cpio_result, "decompress vendor_boot vendor_ramdisk00")
    cpio_bytes = cpio_result.stdout

    list_result = run(["cpio", "-it"], input_bytes=cpio_bytes)
    require_ok(list_result, "list vendor_boot vendor ramdisk cpio")
    listing = list_result.stdout.decode("utf-8", errors="replace").splitlines()
    (build_dir / "vendor_ramdisk_listing.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")

    verbose_result = run(["cpio", "-tv"], input_bytes=cpio_bytes)
    require_ok(verbose_result, "verbose-list vendor_boot vendor ramdisk cpio")
    verbose_listing = verbose_result.stdout.decode("utf-8", errors="replace").splitlines()
    (build_dir / "vendor_ramdisk_listing_verbose.txt").write_text("\n".join(verbose_listing) + "\n", encoding="utf-8")

    metadata_dir = build_dir / "vendor_ramdisk_metadata"
    metadata_dir.mkdir()
    extract_result = run(
        [
            "cpio",
            "-id",
            "--no-absolute-filenames",
            MODULES_ALIAS,
            MODULES_LOAD,
            MODULES_LOAD_RECOVERY,
            MODULES_SOFTDEP,
            MODULES_DEP,
        ],
        cwd=metadata_dir,
        input_bytes=cpio_bytes,
    )
    require_ok(extract_result, "extract vendor_boot module metadata")

    metadata: dict[str, str] = {}
    for rel in (MODULES_ALIAS, MODULES_LOAD, MODULES_LOAD_RECOVERY, MODULES_SOFTDEP, MODULES_DEP):
        path = metadata_dir / rel
        if not path.exists():
            raise SystemExit(f"vendor ramdisk metadata missing after extract: {rel}")
        metadata[rel] = path.read_text(encoding="utf-8", errors="replace")

    ko_paths = sorted(path for path in listing if path.startswith("lib/modules/") and path.endswith(".ko"))
    ko_names = sorted(path.rsplit("/", 1)[-1] for path in ko_paths)
    modules_load_lines = nonempty_lines(metadata[MODULES_LOAD])
    recovery_lines = nonempty_lines(metadata[MODULES_LOAD_RECOVERY])
    modules_dep_lines = nonempty_lines(metadata[MODULES_DEP])
    recovery_basenames = [module_basename(line) for line in recovery_lines]
    if ko_names != sorted(module_basename(line.split(":", 1)[0]) for line in modules_dep_lines):
        raise SystemExit("vendor .ko set and modules.dep lhs set differ")
    if len(ko_paths) != EXPECTED_KO_COUNT:
        raise SystemExit(f"vendor .ko count mismatch: {len(ko_paths)} != {EXPECTED_KO_COUNT}")
    if len(modules_load_lines) != EXPECTED_MODULES_LOAD_COUNT:
        raise SystemExit(f"modules.load count mismatch: {len(modules_load_lines)} != {EXPECTED_MODULES_LOAD_COUNT}")
    if len(recovery_lines) != EXPECTED_MODULES_LOAD_RECOVERY_COUNT:
        raise SystemExit(
            f"modules.load.recovery count mismatch: {len(recovery_lines)} != {EXPECTED_MODULES_LOAD_RECOVERY_COUNT}"
        )
    if len(modules_dep_lines) != EXPECTED_MODULES_DEP_COUNT:
        raise SystemExit(f"modules.dep count mismatch: {len(modules_dep_lines)} != {EXPECTED_MODULES_DEP_COUNT}")
    if any(line.split() != [line] for line in recovery_lines):
        raise SystemExit("modules.load.recovery has inline whitespace tokens")
    if any(not module_basename(line).endswith(".ko") for line in recovery_lines):
        raise SystemExit("modules.load.recovery contains non-.ko entries")
    if any(len(module_basename(line)) >= RUNTIME_MODULE_NAME_BUF for line in recovery_lines):
        raise SystemExit("modules.load.recovery basename exceeds M23 runtime parser buffer")

    dep_map = parse_modules_dep(modules_dep_lines)
    compat_to_modules = parse_modules_alias(metadata[MODULES_ALIAS], set(ko_names))
    expected_softdep = "softdep dwc3_msm pre: phy-generic phy-msm-snps-hs phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud post: ucsi_glink"
    if expected_softdep not in metadata[MODULES_SOFTDEP]:
        raise SystemExit("expected dwc3_msm softdep line missing")

    return {
        "metadata_dir": metadata_dir,
        "cpio_size": len(cpio_bytes),
        "entry_count": len(listing),
        "ko_count": len(ko_paths),
        "ko_names": ko_names,
        "modules_load_lines": modules_load_lines,
        "recovery_lines": recovery_lines,
        "recovery_basenames": recovery_basenames,
        "modules_dep_lines": modules_dep_lines,
        "dep_map": dep_map,
        "compat_to_modules": compat_to_modules,
        "modules_load_count": len(modules_load_lines),
        "modules_load_recovery_count": len(recovery_lines),
        "modules_dep_count": len(modules_dep_lines),
        "modules_load_recovery_bytes": len(metadata[MODULES_LOAD_RECOVERY].encode("utf-8")),
        "modules_load_recovery_max_basename_len": max(len(name) for name in recovery_basenames),
        "modules_softdep_has_dwc3_msm": True,
        "metadata_hashes": {
            "modules.alias": sha256_file(metadata_dir / MODULES_ALIAS),
            "modules.load": sha256_file(metadata_dir / MODULES_LOAD),
            "modules.load.recovery": sha256_file(metadata_dir / MODULES_LOAD_RECOVERY),
            "modules.softdep": sha256_file(metadata_dir / MODULES_SOFTDEP),
            "modules.dep": sha256_file(metadata_dir / MODULES_DEP),
        },
    }


def generate_m23_source(template_source: Path, generated_source: Path, module_count: int) -> str:
    text = template_source.read_text(encoding="utf-8")
    replacements = [
        ("Samsung S22+ native-init M18 full-firststage USB add-back candidate.", "Samsung S22+ native-init M23 DTS-exact QMP/DWC3 add-back candidate."),
        ("M18 starts from the stable M13 no-module floor and reintroduces the vendor\n * first-stage modules.load set minus reset/anomaly modules, then a USB tail.", "M23 derives a narrow DTS-exact QMP/DWC3 module closure from the stock\n * vendor DTB, then attempts the same ACM park milestone."),
        ("S22_NATIVE_INIT_USB_ACM_M18_FULL", MARKER),
        ("s22plus_m18_full_firststage_usb.modules", MODULES_RAMDISK),
        ("MODULES_FULL_FIRSTSTAGE_USB_BUF", "MODULES_DTS_EXACT_QMP_BUF"),
        ("modules_full_firststage_usb", "modules_dts_exact_qmp"),
        ("full_firststage_usb", "dts_exact_qmp"),
        ("M18 Full ACM", "M23 DTS QMP ACM"),
        ("S22M18FULL0001", "S22M23DTSQMP01"),
        ("module_count=141", f"module_count={module_count}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    if "S22_NATIVE_INIT_USB_ACM_M18_FULL" in text or "s22plus_m18_full_firststage_usb" in text:
        raise SystemExit("generated M23 source still contains M18 runtime identifiers")
    if "full_firststage_usb" in text:
        raise SystemExit("generated M23 source still contains full_firststage_usb identifiers")
    generated_source.write_text(text, encoding="utf-8")
    return text


def compile_init(source: Path, out_path: Path, build_dir: Path, module_count: int) -> dict[str, Any]:
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,-e,_start",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile M23 DTS-exact QMP init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M23 DTS-exact QMP init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M23 DTS-exact QMP init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M23 DTS-exact QMP init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M23 DTS-exact QMP init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M23 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M23 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M23 init disassembly does not contain svc")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{MODULES_RAMDISK}",
        "module_list=boot_ramdisk_dts_exact_qmp",
        "module_group=dts_exact_qmp",
        f"module_count={module_count}",
        "watchdog_blocklist=1",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        "S22M23DTSQMP01",
        f"{MARKER} READY",
        f"{MARKER} ACK status park",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M23 /init: {required}")
    reboot_nr_lines = [
        line
        for line in objdump_text.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line and "// #142" in line
    ]
    if reboot_nr_lines:
        raise SystemExit("M23 init unexpectedly contains arm64 __NR_reboot (142)")
    for forbidden in (
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"s22plus-m5",
        b"modules.load.recovery",
        b"download",
        b"M18_FULL",
        b"m18_full",
        b"full_firststage",
    ):
        if forbidden in binary:
            raise SystemExit(f"M23 /init contains forbidden string: {forbidden!r}")

    (build_dir / "M23_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "M23_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "M23_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


def build_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--template-source", type=Path, default=DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-dtb", type=Path, default=DEFAULT_VENDOR_DTB)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    template_source = resolve(root, args.template_source)
    vendor_dtb = resolve(root, args.vendor_dtb)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    odin = resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, odin_dir):
        directory.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)
    if not template_source.exists():
        raise SystemExit(f"template source missing: {template_source}")
    if not vendor_dtb.exists():
        raise SystemExit(f"vendor DTB missing: {vendor_dtb}")

    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    vendor_metadata = extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    dtb_image = vendor_dtb.read_bytes()
    dts_exact_qmp = derive_dts_exact_qmp(
        dtb_image=dtb_image,
        compat_to_modules=vendor_metadata["compat_to_modules"],
        dep_map=vendor_metadata["dep_map"],
        recovery_lines=vendor_metadata["recovery_lines"],
    )
    subset_text = str(dts_exact_qmp["subset_text"])
    module_count = int(dts_exact_qmp["dts_exact_qmp"]["subset_count"])
    subset_file = build_dir / MODULES_RAMDISK
    subset_file.write_text(subset_text, encoding="ascii")
    (build_dir / "m23_dts_exact_qmp.txt").write_text(subset_text, encoding="ascii")

    generated_source = build_dir / GENERATED_SOURCE_NAME
    generate_m23_source(template_source, generated_source, module_count)
    m23_init = build_dir / GENERATED_INIT_NAME
    m23_init_info = compile_init(generated_source, m23_init, build_dir, module_count)

    nochange_unpack = run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "magiskboot no-change unpack")
    nochange_repack = run_in_dir(
        [magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"],
        nochange_dir,
        "magiskboot no-change repack",
    )
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"magiskboot no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "magiskboot unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    extract_text = run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "extract original Magisk init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    ramdisk_before_sha = sha256_file(ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {m23_init}"], work_dir, "replace /init with M23 init")
    patch_subset_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_RAMDISK} {subset_file}"],
        work_dir,
        "add M23 DTS-exact QMP list",
    )
    patch_text = patch_init_text + "\n" + patch_subset_text
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M23 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(m23_init):
        raise SystemExit("replaced /init does not match compiled M23 init")
    extracted_subset = build_dir / f"{MODULES_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {MODULES_RAMDISK} {extracted_subset}"], work_dir, "extract M23 module list")
    if sha256_file(extracted_subset) != sha256_file(subset_file):
        raise SystemExit("replaced M23 module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = sha256_file(ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "magiskboot repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")

    patched_unpack_dir = out_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    patched_unpack = run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"AP tar member mismatch: {members}")

    parse_gate_text = ""
    if not args.no_odin_parse_gate and odin.exists():
        invalid_odin_target = str(Path("/dev") / "bus" / "usb" / "999" / "999")
        gate = run([odin, "-a", ap_md5, "-d", invalid_odin_target])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "template_source": sha256_file(template_source),
        "generated_source": sha256_file(generated_source),
        "base_boot": base_sha,
        "vendor_dtb": sha256_file(vendor_dtb),
        "vendor_ramdisk": sha256_file(vendor_ramdisk),
        "m23_dts_exact_qmp": sha256_file(subset_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m23_init": sha256_file(m23_init),
        "ramdisk_before": ramdisk_before_sha,
        "ramdisk_after": ramdisk_after_sha,
        "kernel": sha256_file(kernel),
        "header": sha256_file(header),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "base_boot": base_boot.stat().st_size,
        "vendor_dtb": vendor_dtb.stat().st_size,
        "vendor_ramdisk_lz4": vendor_ramdisk.stat().st_size,
        "vendor_ramdisk_cpio": int(vendor_metadata["cpio_size"]),
        "m23_dts_exact_qmp": subset_file.stat().st_size,
        "generated_source": generated_source.stat().st_size,
        "m23_init": m23_init.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }

    vendor_summary = {
        "vendor_ramdisk_sha256": sha256_file(vendor_ramdisk),
        "vendor_ramdisk_lz4_size": vendor_ramdisk.stat().st_size,
        "vendor_dtb_sha256": sha256_file(vendor_dtb),
        "vendor_dtb_size": vendor_dtb.stat().st_size,
        "cpio_size": int(vendor_metadata["cpio_size"]),
        "entry_count": int(vendor_metadata["entry_count"]),
        "ko_count": int(vendor_metadata["ko_count"]),
        "modules_load_count": int(vendor_metadata["modules_load_count"]),
        "modules_load_recovery_count": int(vendor_metadata["modules_load_recovery_count"]),
        "modules_load_recovery_bytes": int(vendor_metadata["modules_load_recovery_bytes"]),
        "runtime_modules_dts_exact_qmp_buffer": RUNTIME_MODULES_DTS_EXACT_QMP_BUF,
        "runtime_module_name_buffer": RUNTIME_MODULE_NAME_BUF,
        "modules_load_recovery_max_basename_len": int(vendor_metadata["modules_load_recovery_max_basename_len"]),
        "modules_dep_count": int(vendor_metadata["modules_dep_count"]),
        "modules_softdep_has_dwc3_msm": True,
        "metadata_hashes": vendor_metadata["metadata_hashes"],
    }

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M23 DTS-exact QMP/DWC3 dependency closure native-init park candidate",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one module-list text file",
            "runtime": "freestanding-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "reboot_syscall": False,
            "host_commanded_reboot_download": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_list_path": f"/{MODULES_RAMDISK}",
            "module_subset": "43-module DTS-derived QMP/DWC3/HS-PHY/provider closure plus non-EUD dwc3 softdep PHY preloads and ACM function",
            "configfs_runtime_gadget": "ss_acm.0 only",
            "udc_binding": "a600000.dwc3 only; never dummy_udc.0",
            "usb_role_force": "attempt /sys/class/usb_role/*/role=device",
            "eud": "EUD extcon observed but intentionally not loaded/opened/enabled in this candidate",
            "watchdog": "gh_virt_wdt/qcom_wdt_core reset path blocklisted; sec_debug/minidump/abc also blocklisted",
            "observation_model": "park plus host ACM enumeration; no reboot beacon",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "template_source": display_path(root, template_source),
            "generated_source": display_path(root, generated_source),
            "base_boot": display_path(root, base_boot),
            "vendor_dtb": display_path(root, vendor_dtb),
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "lz4": display_path(root, lz4_tool),
            "magiskboot": display_path(root, magiskboot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m23_init": m23_init_info,
        "vendor": vendor_summary,
        "dts_exact_qmp": {
            key: value for key, value in dts_exact_qmp.items() if key != "subset_text"
        },
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": MODULES_RAMDISK,
            "added_subset_entry_mode": "640",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 1,
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patched_unpack_output": patched_unpack,
            "nochange_unpack_output": nochange_unpack,
            "nochange_repack_output": nochange_repack,
            "extract_output": extract_text,
            "patch_output": patch_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_gate_text,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    (out_dir / "sizes.txt").write_text("".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii")
    (out_dir / "required_strings.txt").write_text("\n".join(m23_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(build_main(sys.argv[1:]))
