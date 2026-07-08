#!/usr/bin/env python3
"""Build the S22+ M25 HS-only USB2 ACM native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M25 is the fault-avoidance pivot after the QMP/USB3 path repeatedly looped.
It builds:

* a boot-only native-init candidate that loads the DTS-derived HS/USB2 DWC3
  substrate while excluding the SS/QMP PHY module; and
* a DTBO candidate that caps the DWC3 child overlay maximum-speed from
  "super-speed" to equal-length "high-speed".

The intended future live gate must be separately SHA-pinned in AGENTS.md before
either artifact can be flashed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_s22plus_inplace_m23_dts_exact_qmp_park as m23
import build_s22plus_ramoops_dtbo_enable as dtbo_base


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1")
DEFAULT_DTBO = dtbo_base.DEFAULT_DTBO

MARKER = "S22_NATIVE_INIT_USB_ACM_M25_HS_ONLY"
MODULES_RAMDISK = "s22plus_m25_hs_only_usb2.modules"
GENERATED_SOURCE_NAME = "s22plus_init_usb_acm_m25_hs_only.c"
GENERATED_INIT_NAME = "s22plus_init_usb_acm_m25_hs_only"
USB_SERIAL = "S22M25HSONLY01"
USB_PRODUCT = "S22 Native Init M25 HS ACM"

SUPER_SPEED_VALUE = b"super-speed\0"
HIGH_SPEED_SAME_LEN_VALUE = b"high-speed\0" + b"\0" * (len(SUPER_SPEED_VALUE) - len(b"high-speed\0"))
MAX_SPEED_TARGET_PATHS = {
    "/fragment@155/__overlay__/dwc3@a600000",
    "/fragment@156/__overlay__/dwc3@a600000",
}
EXPECTED_DTBO_BLOB_COUNT = 11
EXPECTED_MAX_SPEED_PATCH_COUNT = 11

HS_ONLY_BLOCKLIST = m23.RESET_ANOMALY_BLOCKLIST | {
    "eud.ko",
    "phy-msm-ssusb-qmp.ko",
    "ucsi_glink.ko",
}

DWC3_HS_SOFTDEP_PRE_INCLUDED = [
    "phy-generic.ko",
    "phy-msm-snps-hs.ko",
    "phy-msm-snps-eusb2.ko",
]

EXPECTED_M25_HS_ONLY_SUBSET = [
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
    "qnoc-waipio.ko",
    "phy-generic.ko",
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


def is_ss_qmp_path(path_props: dict[str, dict[str, bytes]], provider_path: str) -> bool:
    compatible = m23.safe_decode_strings(path_props.get(provider_path, {}).get("compatible", b""))
    return any("usb-ssphy-qmp" in item for item in compatible)


def transitive_hs_only_module_closure(
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
        if module in HS_ONLY_BLOCKLIST:
            blocked_edges.add(module)
            continue
        if module not in dep_map:
            missing_modules.add(module)
            continue
        closure.add(module)
        for dep in dep_map[module]:
            if dep in HS_ONLY_BLOCKLIST:
                blocked_edges.add(dep)
            elif dep not in closure:
                stack.append(dep)
    if missing_modules:
        raise SystemExit(f"M25 module seed/dependency missing from modules.dep: {sorted(missing_modules)}")

    recovery_set = set(recovery_lines)
    closure_not_recovery = sorted(closure - recovery_set)
    if closure_not_recovery:
        raise SystemExit(f"M25 closure is not wholly in recovery order: {closure_not_recovery}")
    ordered = [module for module in recovery_lines if module in closure]
    nonblocked_missing_edges = {
        module: [dep for dep in dep_map[module] if dep not in closure and dep not in HS_ONLY_BLOCKLIST]
        for module in ordered
    }
    nonblocked_missing_edges = {module: deps for module, deps in nonblocked_missing_edges.items() if deps}
    if nonblocked_missing_edges:
        raise SystemExit(f"M25 closure has unresolved non-blocked dependency edges: {nonblocked_missing_edges}")
    if ordered != EXPECTED_M25_HS_ONLY_SUBSET:
        raise SystemExit(
            "M25 HS-only subset drifted:\n"
            f"actual={ordered!r}\nexpected={EXPECTED_M25_HS_ONLY_SUBSET!r}"
        )

    subset_text = "".join(f"{module}\n" for module in ordered)
    if len(subset_text.encode("utf-8")) >= m23.RUNTIME_MODULES_DTS_EXACT_QMP_BUF:
        raise SystemExit("M25 module list does not fit runtime parser buffer")
    too_long = [module for module in ordered if len(module) >= m23.RUNTIME_MODULE_NAME_BUF]
    if too_long:
        raise SystemExit(f"M25 module basename exceeds runtime parser buffer: {too_long[:5]}")
    forbidden_present = sorted(set(ordered) & HS_ONLY_BLOCKLIST)
    if forbidden_present:
        raise SystemExit(f"forbidden module leaked into M25 subset: {forbidden_present}")
    return {
        "seeds": sorted(seeds),
        "subset": ordered,
        "subset_count": len(ordered),
        "subset_bytes": len(subset_text.encode("utf-8")),
        "subset_max_basename_len": max(len(module) for module in ordered),
        "subset_recovery_positions": {module: recovery_lines.index(module) + 1 for module in ordered},
        "subset_text": subset_text,
        "blocked_dependency_edges": sorted(blocked_edges),
        "blocklist": sorted(HS_ONLY_BLOCKLIST),
    }


def derive_dts_hs_only(
    *,
    dtb_image: bytes,
    compat_to_modules: dict[str, list[str]],
    dep_map: dict[str, list[str]],
    recovery_lines: list[str],
) -> dict[str, Any]:
    blob_results: list[dict[str, Any]] = []
    closure_results: list[dict[str, Any]] = []
    for blob_index, path_props, phandles in m23.all_blob_path_props(dtb_image):
        if m23.SSUSB_PATH not in path_props or m23.DWC3_PATH not in path_props:
            raise SystemExit(f"blob {blob_index} lacks required USB target nodes")
        usb_phy_refs = m23.parse_phandle_array(
            path_props=path_props,
            phandles=phandles,
            owner_path=m23.DWC3_PATH,
            prop_name="usb-phy",
            cell_count_prop="#phy-cells",
        )
        hs_phy_paths: list[str] = []
        ss_qmp_phy_paths: list[str] = []
        for ref in usb_phy_refs:
            provider_path = ref["provider_path"]
            if is_ss_qmp_path(path_props, provider_path):
                ss_qmp_phy_paths.append(provider_path)
            else:
                hs_phy_paths.append(provider_path)
        if hs_phy_paths != ["/soc/hsphy@88e3000"]:
            raise SystemExit(f"blob {blob_index} HS PHY path drift: {hs_phy_paths}")
        if ss_qmp_phy_paths != ["/soc/ssphy@88e8000"]:
            raise SystemExit(f"blob {blob_index} SS/QMP PHY path drift: {ss_qmp_phy_paths}")

        target_paths = [m23.SSUSB_PATH, m23.DWC3_PATH, *hs_phy_paths]
        direct_node_modules = [
            m23.direct_modules_for_node(path_props=path_props, compat_to_modules=compat_to_modules, path=path)
            for path in target_paths
        ]
        seeds: set[str] = set(m23.RUNTIME_FUNCTION_MODULES)
        seed_reasons: dict[str, list[str]] = {
            module: ["runtime-configfs-acm-function"] for module in m23.RUNTIME_FUNCTION_MODULES
        }
        for item in direct_node_modules:
            for module in item["modules"]:
                seeds.add(module)
                seed_reasons.setdefault(module, []).append(f"direct-compatible:{item['path']}")
        for module in DWC3_HS_SOFTDEP_PRE_INCLUDED:
            seeds.add(module)
            seed_reasons.setdefault(module, []).append("dwc3_msm-softdep-pre-hs-only")

        references: list[dict[str, Any]] = []
        provider_modules: list[dict[str, Any]] = []
        excluded_references: list[dict[str, Any]] = []
        for owner_path in target_paths:
            for ref in m23.collect_references(path_props, phandles, owner_path):
                references.append({"owner_path": owner_path, **ref})
                provider_path = ref["provider_path"]
                if provider_path == m23.EUD_PATH or ref["prop"] == "extcon":
                    excluded_references.append(
                        {
                            "owner_path": owner_path,
                            **ref,
                            "reason": "EUD/extcon excluded: retail TrustZone-gated EUD attach is closed",
                        }
                    )
                    continue
                if is_ss_qmp_path(path_props, provider_path):
                    excluded_references.append(
                        {
                            "owner_path": owner_path,
                            **ref,
                            "reason": "SS/QMP PHY excluded: M25 caps DWC3 to high-speed and avoids the M15 loop module",
                        }
                    )
                    continue
                resolved = m23.provider_modules_for_path(
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

        closure = transitive_hs_only_module_closure(
            seeds=seeds,
            dep_map=dep_map,
            recovery_lines=recovery_lines,
        )
        blob_results.append(
            {
                "blob_index": blob_index,
                "target_paths": target_paths,
                "hs_phy_paths": hs_phy_paths,
                "ss_qmp_phy_paths_excluded": ss_qmp_phy_paths,
                "direct_node_modules": direct_node_modules,
                "references": references,
                "provider_modules": provider_modules,
                "excluded_references": excluded_references,
                "seed_modules_by_reason": {module: sorted(reasons) for module, reasons in sorted(seed_reasons.items())},
                "softdep_included": DWC3_HS_SOFTDEP_PRE_INCLUDED,
                "softdep_excluded": ["phy-msm-ssusb-qmp.ko", "eud.ko", "ucsi_glink.ko"],
            }
        )
        closure_results.append(closure)

    first_subset = closure_results[0]["subset"]
    first_blocked = closure_results[0]["blocked_dependency_edges"]
    for idx, closure in enumerate(closure_results[1:], start=1):
        if closure["subset"] != first_subset:
            raise SystemExit(f"DTS blob {idx} derives a different M25 HS-only subset")
        if closure["blocked_dependency_edges"] != first_blocked:
            raise SystemExit(f"DTS blob {idx} derives different blocked dependency edges")

    return {
        "dtb_blob_count": len(blob_results),
        "blob_results": blob_results,
        "order_source": "stock modules.load.recovery order after HS-only DTS-derived seed transitive modules.dep closure",
        "speed_policy": "DTBO maximum-speed overlay capped to high-speed; SS/QMP PHY path intentionally excluded",
        "eud_policy": "EUD extcon observed but excluded; no EUD enable/open because Phase-B proved TZ-gated rc:-22",
        "dts_hs_only": {key: value for key, value in closure_results[0].items() if key != "subset_text"},
        "subset_text": str(closure_results[0]["subset_text"]),
    }


def summarize_dtbo_max_speed(image: bytes) -> dict[str, Any]:
    blobs = dtbo_base.iter_fdt_blobs(image)
    blob_summaries: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for blob in blobs:
        speed_props = []
        for prop in dtbo_base.parse_fdt_props(blob):
            if prop.name != "maximum-speed":
                continue
            strings = dtbo_base.decode_string_list(prop.value)
            item = {
                "blob_index": prop.blob_index,
                "path": prop.path,
                "length": prop.length,
                "value_offset_hex": f"0x{prop.value_offset:x}",
                "value_hex": prop.value.hex(),
                "strings": strings,
            }
            speed_props.append(item)
            if prop.path in MAX_SPEED_TARGET_PATHS and prop.value == SUPER_SPEED_VALUE:
                targets.append(item)
        blob_summaries.append(
            {
                "index": blob.index,
                "offset_hex": f"0x{blob.offset:x}",
                "totalsize": blob.totalsize,
                "maximum_speed_props": speed_props,
            }
        )
    return {
        "blob_count": len(blobs),
        "blobs": blob_summaries,
        "patch_targets": targets,
    }


def patch_dtbo_high_speed(image: bytes, summary: dict[str, Any]) -> tuple[bytes, list[dict[str, Any]]]:
    targets = summary["patch_targets"]
    if len(targets) != EXPECTED_MAX_SPEED_PATCH_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_MAX_SPEED_PATCH_COUNT} maximum-speed patch targets, found {len(targets)}"
        )
    patched = bytearray(image)
    applied: list[dict[str, Any]] = []
    for target in targets:
        offset = int(str(target["value_offset_hex"]), 16)
        if bytes(patched[offset : offset + len(SUPER_SPEED_VALUE)]) != SUPER_SPEED_VALUE:
            raise SystemExit(f"DTBO target bytes drift at 0x{offset:x}")
        patched[offset : offset + len(SUPER_SPEED_VALUE)] = HIGH_SPEED_SAME_LEN_VALUE
        applied.append(
            {
                "blob_index": target["blob_index"],
                "path": target["path"],
                "value_offset_hex": target["value_offset_hex"],
                "old_value_hex": SUPER_SPEED_VALUE.hex(),
                "new_value_hex": HIGH_SPEED_SAME_LEN_VALUE.hex(),
            }
        )
    return bytes(patched), applied


def build_dtbo_artifacts(*, root: Path, stock_dtbo: Path, odin: Path, out_dir: Path, no_odin_parse_gate: bool) -> dict[str, Any]:
    if m23.sha256_file(stock_dtbo) != dtbo_base.EXPECTED_DTBO_SHA256:
        raise SystemExit(f"stock dtbo SHA mismatch: {m23.sha256_file(stock_dtbo)}")
    stock_image = stock_dtbo.read_bytes()
    stock_summary = summarize_dtbo_max_speed(stock_image)
    if stock_summary["blob_count"] != EXPECTED_DTBO_BLOB_COUNT:
        raise SystemExit(f"unexpected DTBO blob count: {stock_summary['blob_count']} != {EXPECTED_DTBO_BLOB_COUNT}")
    patched_image, applied = patch_dtbo_high_speed(stock_image, stock_summary)
    patched_summary = summarize_dtbo_max_speed(patched_image)
    if patched_summary["patch_targets"]:
        raise SystemExit(f"patched DTBO still has super-speed targets: {patched_summary['patch_targets']}")

    diff = dtbo_base.diff_ranges(stock_image, patched_image)
    value_diff = dtbo_base.diff_ranges(SUPER_SPEED_VALUE, HIGH_SPEED_SAME_LEN_VALUE)
    expected_diff_ranges = EXPECTED_MAX_SPEED_PATCH_COUNT * len(value_diff)
    if len(diff) != expected_diff_ranges:
        raise SystemExit(f"expected {expected_diff_ranges} diff ranges, found {len(diff)}")
    changed = dtbo_base.changed_byte_count(stock_image, patched_image)
    expected_changed = EXPECTED_MAX_SPEED_PATCH_COUNT * sum(
        1 for left, right in zip(SUPER_SPEED_VALUE, HIGH_SPEED_SAME_LEN_VALUE) if left != right
    )
    if changed != expected_changed:
        raise SystemExit(f"unexpected DTBO changed-byte count: {changed} != {expected_changed}")

    build_dir = out_dir / "dtbo_build"
    candidate_dir = out_dir / "dtbo_candidate_odin4"
    rollback_dir = out_dir / "dtbo_stock_rollback_odin4"
    for directory in (build_dir, candidate_dir, rollback_dir):
        directory.mkdir(parents=True)

    stock_raw = build_dir / "stock_dtbo.img"
    patched_raw = build_dir / "dtbo.img"
    stock_raw.write_bytes(stock_image)
    patched_raw.write_bytes(patched_image)
    candidate_lz4 = candidate_dir / "dtbo.img.lz4"
    rollback_lz4 = rollback_dir / "dtbo.img.lz4"
    dtbo_base.write_lz4_store(patched_raw, candidate_lz4)
    dtbo_base.write_lz4_store(stock_raw, rollback_lz4)

    candidate_ap_tar = candidate_dir / "AP.tar"
    candidate_ap_md5 = candidate_dir / "AP.tar.md5"
    rollback_ap_tar = rollback_dir / "AP.tar"
    rollback_ap_md5 = rollback_dir / "AP.tar.md5"
    dtbo_base.write_single_member_tar_md5(candidate_lz4, "dtbo.img.lz4", candidate_ap_tar, candidate_ap_md5)
    dtbo_base.write_single_member_tar_md5(rollback_lz4, "dtbo.img.lz4", rollback_ap_tar, rollback_ap_md5)
    candidate_members = m23.tar_members(candidate_ap_md5)
    rollback_members = m23.tar_members(rollback_ap_md5)
    if candidate_members != ["dtbo.img.lz4"] or rollback_members != ["dtbo.img.lz4"]:
        raise SystemExit(f"DTBO AP tar member mismatch: {candidate_members=} {rollback_members=}")

    candidate_parse_gate = ""
    rollback_parse_gate = ""
    if not no_odin_parse_gate and odin.exists():
        candidate_parse_gate = dtbo_base.run_odin_parse_gate(odin, candidate_ap_md5)
        rollback_parse_gate = dtbo_base.run_odin_parse_gate(odin, rollback_ap_md5)
        (candidate_dir / "parse_dry_run_invalid_device.txt").write_text(candidate_parse_gate, encoding="utf-8")
        (rollback_dir / "parse_dry_run_invalid_device.txt").write_text(rollback_parse_gate, encoding="utf-8")

    stock_avb_digest = dtbo_base.dtbo_avb_digest(stock_image)
    patched_avb_digest = dtbo_base.dtbo_avb_digest(patched_image)
    if stock_avb_digest != dtbo_base.DTBO_AVB_DESCRIPTOR_DIGEST_HEX:
        raise SystemExit(f"stock DTBO AVB descriptor digest mismatch: {stock_avb_digest}")

    return {
        "paths": {
            "stock_dtbo": m23.display_path(root, stock_dtbo),
            "patched_dtbo_raw": m23.display_path(root, patched_raw),
            "candidate_ap_tar_md5": m23.display_path(root, candidate_ap_md5),
            "rollback_ap_tar_md5": m23.display_path(root, rollback_ap_md5),
        },
        "hashes": {
            "stock_dtbo_raw": m23.sha256_file(stock_raw),
            "patched_dtbo_raw": m23.sha256_file(patched_raw),
            "candidate_dtbo_lz4": m23.sha256_file(candidate_lz4),
            "candidate_ap_tar": m23.sha256_file(candidate_ap_tar),
            "candidate_ap_tar_md5": m23.sha256_file(candidate_ap_md5),
            "rollback_dtbo_lz4": m23.sha256_file(rollback_lz4),
            "rollback_ap_tar": m23.sha256_file(rollback_ap_tar),
            "rollback_ap_tar_md5": m23.sha256_file(rollback_ap_md5),
            "stock_dtbo_avb_hash_descriptor_digest": stock_avb_digest,
            "patched_dtbo_avb_hash_descriptor_recomputed_digest": patched_avb_digest,
        },
        "sizes": {
            "dtbo_raw": len(stock_image),
            "patched_dtbo_raw": len(patched_image),
            "candidate_dtbo_lz4": candidate_lz4.stat().st_size,
            "candidate_ap_tar_md5": candidate_ap_md5.stat().st_size,
            "rollback_dtbo_lz4": rollback_lz4.stat().st_size,
            "rollback_ap_tar_md5": rollback_ap_md5.stat().st_size,
        },
        "evidence": {
            "stock_dtbo": stock_summary,
            "patched_dtbo": patched_summary,
            "applied_patches": applied,
            "diff_ranges": diff,
            "changed_byte_count": changed,
            "expected_changed_byte_count": expected_changed,
            "old_value": "super-speed",
            "new_value": "high-speed",
            "candidate_tar_members": candidate_members,
            "rollback_tar_members": rollback_members,
            "odin_parse_gate_candidate": candidate_parse_gate,
            "odin_parse_gate_rollback": rollback_parse_gate,
            "dtbo_avb_hash_descriptor": {
                "partition_name": "dtbo",
                "stock_matches_descriptor": True,
                "patched_matches_descriptor": patched_avb_digest == dtbo_base.DTBO_AVB_DESCRIPTOR_DIGEST_HEX,
            },
        },
    }


def generate_m25_source(template_source: Path, generated_source: Path, module_count: int) -> str:
    text = template_source.read_text(encoding="utf-8")
    replacements = [
        (
            "Samsung S22+ native-init M18 full-firststage USB add-back candidate.",
            "Samsung S22+ native-init M25 HS-only USB2 ACM candidate.",
        ),
        (
            "M18 starts from the stable M13 no-module floor and reintroduces the vendor\n"
            " * first-stage modules.load set minus reset/anomaly modules, then a USB tail.",
            "M25 derives a high-speed-only DWC3 module closure and avoids the\n"
            " * SS/QMP PHY module that repeatedly boot-looped.",
        ),
        ("S22_NATIVE_INIT_USB_ACM_M18_FULL", MARKER),
        ("s22plus_m18_full_firststage_usb.modules", MODULES_RAMDISK),
        ("MODULES_FULL_FIRSTSTAGE_USB_BUF", "MODULES_HS_ONLY_USB2_BUF"),
        ("modules_full_firststage_usb", "modules_hs_only_usb2"),
        ("full_firststage_usb", "hs_only_usb2"),
        ("M18 Full ACM", USB_PRODUCT),
        ("S22M18FULL0001", USB_SERIAL),
        ("module_count=141", f"module_count={module_count}"),
        ("watchdog_blocklist=1 ", "watchdog_blocklist=1 hs_only=1 qmp_excluded=1 maximum_speed_dtbo=high-speed dtbo_patch_required=1 "),
        ('write_attr("/config/usb_gadget/g1/bcdUSB", "0x0320")', 'write_attr("/config/usb_gadget/g1/bcdUSB", "0x0200")'),
        ("static void M18_FULL_main(void)", "static void M25_main(void)"),
        ("M18_FULL_main();", "M25_main();"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    for forbidden in ("S22_NATIVE_INIT_USB_ACM_M18_FULL", "s22plus_m18_full_firststage_usb", "full_firststage_usb"):
        if forbidden in text:
            raise SystemExit(f"generated M25 source still contains {forbidden}")
    for required in (MARKER, MODULES_RAMDISK, USB_SERIAL, "maximum_speed_dtbo=high-speed", "qmp_excluded=1"):
        if required not in text:
            raise SystemExit(f"generated M25 source missing required marker: {required}")
    generated_source.write_text(text, encoding="utf-8")
    return text


def compile_init(source: Path, out_path: Path, build_dir: Path, module_count: int) -> dict[str, Any]:
    result = m23.run(
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
    m23.require_ok(result, "compile M25 HS-only init")
    strip = m23.run(["aarch64-linux-gnu-strip", "-s", out_path])
    m23.require_ok(strip, "strip M25 HS-only init")

    file_info = m23.run(["file", out_path])
    m23.require_ok(file_info, "file M25 HS-only init")
    readelf = m23.run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    m23.require_ok(readelf, "readelf M25 HS-only init")
    objdump = m23.run(["aarch64-linux-gnu-objdump", "-d", out_path])
    m23.require_ok(objdump, "objdump M25 HS-only init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M25 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M25 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M25 init disassembly does not contain svc")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{MODULES_RAMDISK}",
        "module_list=boot_ramdisk_hs_only_usb2",
        "module_group=hs_only_usb2",
        f"module_count={module_count}",
        "watchdog_blocklist=1",
        "hs_only=1",
        "qmp_excluded=1",
        "maximum_speed_dtbo=high-speed",
        "dtbo_patch_required=1",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        "0x0200",
        USB_SERIAL,
        f"{MARKER} READY",
        f"{MARKER} ACK status park",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M25 /init: {required}")
    reboot_nr_lines = [
        line
        for line in objdump_text.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line and "// #142" in line
    ]
    if reboot_nr_lines:
        raise SystemExit("M25 init unexpectedly contains arm64 __NR_reboot (142)")
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
        b"phy-msm-ssusb-qmp.ko",
        b"super-speed",
    ):
        if forbidden in binary:
            raise SystemExit(f"M25 /init contains forbidden string: {forbidden!r}")

    (build_dir / "M25_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "M25_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "M25_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


def build_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=m23.DEFAULT_BASE_BOOT)
    parser.add_argument("--template-source", type=Path, default=m23.DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-dtb", type=Path, default=m23.DEFAULT_VENDOR_DTB)
    parser.add_argument("--vendor-ramdisk", type=Path, default=m23.DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--dtbo", type=Path, default=DEFAULT_DTBO)
    parser.add_argument("--lz4", type=Path, default=m23.DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=m23.DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=m23.DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=m23.DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = m23.repo_root()
    out_dir = m23.resolve(root, args.out)
    base_boot = m23.resolve(root, args.base_boot)
    template_source = m23.resolve(root, args.template_source)
    vendor_dtb = m23.resolve(root, args.vendor_dtb)
    vendor_ramdisk = m23.resolve(root, args.vendor_ramdisk)
    stock_dtbo = m23.resolve(root, args.dtbo)
    lz4_tool = m23.resolve(root, args.lz4)
    magiskboot = m23.resolve(root, args.magiskboot)
    magisk_apk = m23.resolve(root, args.magisk_apk)
    odin = m23.resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    boot_odin_dir = out_dir / "boot_odin4"
    for directory in (build_dir, work_dir, nochange_dir, boot_odin_dir):
        directory.mkdir(parents=True)

    m23.ensure_magiskboot(magiskboot, magisk_apk)
    for required_path, label in (
        (template_source, "template source"),
        (vendor_dtb, "vendor DTB"),
        (vendor_ramdisk, "vendor ramdisk"),
        (stock_dtbo, "stock dtbo"),
        (base_boot, "base boot"),
    ):
        if not required_path.exists():
            raise SystemExit(f"{label} missing: {required_path}")

    base_sha = m23.sha256_file(base_boot)
    if base_sha != m23.EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != m23.BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {m23.BOOT_PARTITION_SIZE}")

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    dtb_image = vendor_dtb.read_bytes()
    dts_hs_only = derive_dts_hs_only(
        dtb_image=dtb_image,
        compat_to_modules=vendor_metadata["compat_to_modules"],
        dep_map=vendor_metadata["dep_map"],
        recovery_lines=vendor_metadata["recovery_lines"],
    )
    subset_text = str(dts_hs_only["subset_text"])
    module_count = int(dts_hs_only["dts_hs_only"]["subset_count"])
    subset_file = build_dir / MODULES_RAMDISK
    subset_file.write_text(subset_text, encoding="ascii")
    (build_dir / "m25_hs_only_usb2.txt").write_text(subset_text, encoding="ascii")

    generated_source = build_dir / GENERATED_SOURCE_NAME
    generate_m25_source(template_source, generated_source, module_count)
    m25_init = build_dir / GENERATED_INIT_NAME
    m25_init_info = compile_init(generated_source, m25_init, build_dir, module_count)

    nochange_unpack = m23.run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "magiskboot no-change unpack")
    nochange_repack = m23.run_in_dir(
        [magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"],
        nochange_dir,
        "magiskboot no-change repack",
    )
    nochange_sha = m23.sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"magiskboot no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = m23.run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "magiskboot unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    extract_text = m23.run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract init {original_init}"],
        work_dir,
        "extract original Magisk init",
    )
    original_init_sha = m23.sha256_file(original_init)
    if original_init_sha != m23.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    ramdisk_before_sha = m23.sha256_file(ramdisk_before)
    cpio_test_before = m23.run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = m23.run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 750 init {m25_init}"],
        work_dir,
        "replace /init with M25 init",
    )
    patch_subset_text = m23.run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_RAMDISK} {subset_file}"],
        work_dir,
        "add M25 HS-only module list",
    )
    patch_text = patch_init_text + "\n" + patch_subset_text
    cpio_test_after = m23.run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M25 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    m23.run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if m23.sha256_file(extracted_replaced) != m23.sha256_file(m25_init):
        raise SystemExit("replaced /init does not match compiled M25 init")
    extracted_subset = build_dir / f"{MODULES_RAMDISK}.extracted"
    m23.run_in_dir([magiskboot, "cpio", ramdisk, f"extract {MODULES_RAMDISK} {extracted_subset}"], work_dir, "extract M25 module list")
    if m23.sha256_file(extracted_subset) != m23.sha256_file(subset_file):
        raise SystemExit("replaced M25 module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = m23.sha256_file(ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = m23.run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "magiskboot repack patched boot")
    if boot_img.stat().st_size != m23.BOOT_PARTITION_SIZE:
        raise SystemExit(f"patched boot size mismatch: {boot_img.stat().st_size} != {m23.BOOT_PARTITION_SIZE}")

    patched_unpack_dir = out_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    patched_unpack = m23.run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "unpack patched boot")
    if m23.sha256_file(patched_unpack_dir / "kernel") != m23.sha256_file(kernel):
        raise SystemExit("patched boot kernel changed")

    boot_lz4 = boot_odin_dir / "boot.img.lz4"
    m23.write_boot_lz4(boot_img, boot_lz4)
    boot_ap_tar = boot_odin_dir / "AP.tar"
    boot_ap_md5 = boot_odin_dir / "AP.tar.md5"
    m23.write_ap_tar(boot_lz4, boot_ap_tar, boot_ap_md5)
    boot_members = m23.tar_members(boot_ap_md5)
    if boot_members != ["boot.img.lz4"]:
        raise SystemExit(f"boot AP tar member mismatch: {boot_members}")

    boot_parse_gate_text = ""
    if not args.no_odin_parse_gate and odin.exists():
        invalid_odin_target = str(Path("/dev") / "bus" / "usb" / "999" / "999")
        gate = m23.run([odin, "-a", boot_ap_md5, "-d", invalid_odin_target])
        boot_parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (boot_odin_dir / "parse_dry_run_invalid_device.txt").write_text(boot_parse_gate_text, encoding="utf-8")

    dtbo_artifacts = build_dtbo_artifacts(
        root=root,
        stock_dtbo=stock_dtbo,
        odin=odin,
        out_dir=out_dir,
        no_odin_parse_gate=args.no_odin_parse_gate,
    )

    hashes = {
        "template_source": m23.sha256_file(template_source),
        "generated_source": m23.sha256_file(generated_source),
        "base_boot": base_sha,
        "vendor_dtb": m23.sha256_file(vendor_dtb),
        "vendor_ramdisk": m23.sha256_file(vendor_ramdisk),
        "stock_dtbo_raw": m23.sha256_file(stock_dtbo),
        "m25_hs_only_usb2": m23.sha256_file(subset_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m25_init": m23.sha256_file(m25_init),
        "ramdisk_before": ramdisk_before_sha,
        "ramdisk_after": ramdisk_after_sha,
        "kernel": m23.sha256_file(kernel),
        "header": m23.sha256_file(header),
        "boot_img": m23.sha256_file(boot_img),
        "boot_img_lz4": m23.sha256_file(boot_lz4),
        "boot_ap_tar": m23.sha256_file(boot_ap_tar),
        "boot_ap_tar_md5": m23.sha256_file(boot_ap_md5),
    }
    sizes = {
        "base_boot": base_boot.stat().st_size,
        "vendor_dtb": vendor_dtb.stat().st_size,
        "vendor_ramdisk_lz4": vendor_ramdisk.stat().st_size,
        "vendor_ramdisk_cpio": int(vendor_metadata["cpio_size"]),
        "m25_hs_only_usb2": subset_file.stat().st_size,
        "generated_source": generated_source.stat().st_size,
        "m25_init": m25_init.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "boot_ap_tar": boot_ap_tar.stat().st_size,
        "boot_ap_tar_md5": boot_ap_md5.stat().st_size,
    }

    vendor_summary = {
        "vendor_ramdisk_sha256": m23.sha256_file(vendor_ramdisk),
        "vendor_ramdisk_lz4_size": vendor_ramdisk.stat().st_size,
        "vendor_dtb_sha256": m23.sha256_file(vendor_dtb),
        "vendor_dtb_size": vendor_dtb.stat().st_size,
        "cpio_size": int(vendor_metadata["cpio_size"]),
        "entry_count": int(vendor_metadata["entry_count"]),
        "ko_count": int(vendor_metadata["ko_count"]),
        "modules_load_count": int(vendor_metadata["modules_load_count"]),
        "modules_load_recovery_count": int(vendor_metadata["modules_load_recovery_count"]),
        "modules_dep_count": int(vendor_metadata["modules_dep_count"]),
        "metadata_hashes": vendor_metadata["metadata_hashes"],
    }

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M25 HS-only USB2 ACM native-init park candidate plus DTBO maximum-speed cap",
        "safety": {
            "host_only_build": True,
            "touches_connected_device": False,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "boot_candidate": {
                "boot_only": True,
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
                "module_subset": "40-module DTS-derived HS-only DWC3/HS-PHY/provider closure",
                "configfs_runtime_gadget": "ss_acm.0 only; bcdUSB forced to 0x0200",
                "udc_binding": "a600000.dwc3 only; never dummy_udc.0",
                "usb_role_force": "attempt /sys/class/usb_role/*/role=device",
                "qmp": "phy-msm-ssusb-qmp.ko intentionally excluded",
                "eud": "EUD extcon observed but intentionally not loaded/opened/enabled",
                "watchdog": "gh_virt_wdt/qcom_wdt_core reset path blocklisted; sec_debug/minidump/abc also blocklisted",
                "observation_model": "park plus host ACM enumeration; no reboot beacon",
            },
            "dtbo_candidate": {
                "partition_scope_if_later_authorized": "dtbo only",
                "patch_model": "equal-length string replacement in all 11 DTBO overlay blobs",
                "old_value": "super-speed",
                "new_value": "high-speed",
                "rollback_ap_built": True,
                "patched_dtbo_requires_disabled_vbmeta_or_resigning_before_live": True,
            },
        },
        "paths": {
            "out_dir": m23.display_path(root, out_dir),
            "template_source": m23.display_path(root, template_source),
            "generated_source": m23.display_path(root, generated_source),
            "base_boot": m23.display_path(root, base_boot),
            "vendor_dtb": m23.display_path(root, vendor_dtb),
            "vendor_ramdisk": m23.display_path(root, vendor_ramdisk),
            "stock_dtbo": m23.display_path(root, stock_dtbo),
            "lz4": m23.display_path(root, lz4_tool),
            "magiskboot": m23.display_path(root, magiskboot),
            "boot_img": m23.display_path(root, boot_img),
            "boot_ap_tar_md5": m23.display_path(root, boot_ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m25_init": m25_init_info,
        "vendor": vendor_summary,
        "dts_hs_only": {key: value for key, value in dts_hs_only.items() if key != "subset_text"},
        "dtbo": dtbo_artifacts,
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
        "boot_diff_vs_base": m23.diff_ranges(base_boot, boot_img),
        "boot_tar_members": boot_members,
        "boot_odin_invalid_device_parse_gate": boot_parse_gate_text,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    combined_hashes = dict(hashes)
    combined_hashes.update({f"dtbo_{key}": value for key, value in dtbo_artifacts["hashes"].items()})
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(combined_hashes.items())),
        encoding="ascii",
    )
    combined_sizes = dict(sizes)
    combined_sizes.update({f"dtbo_{key}": value for key, value in dtbo_artifacts["sizes"].items()})
    (out_dir / "sizes.txt").write_text(
        "".join(f"{value:12d}  {key}\n" for key, value in sorted(combined_sizes.items())),
        encoding="ascii",
    )
    (out_dir / "required_strings.txt").write_text("\n".join(m25_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(build_main(sys.argv[1:]))
