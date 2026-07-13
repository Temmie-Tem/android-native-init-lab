#!/usr/bin/env python3
"""Run the fail-closed R4W1-B static compatibility audit host-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_kernel_r2_audit as r2  # noqa: E402
import s22plus_fyg8_r4w1b_elf_audit as elf_audit  # noqa: E402
import s22plus_fyg8_r4w1b_build as r4w1b_build  # noqa: E402
import s22plus_fyg8_r4w1b_patch_check as patch_check  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1b_static_audit_v1"
TARGET = r2.TARGET
VERDICT = "PASS_R4W1B_STATIC_COMPATIBILITY"
WITNESS_CONFIG = "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"
DEFAULT_BASELINE_SYMVERS = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/"
    "remote-fx8300-r1-v3-operational/source-clean-final/out/"
    "msm-waipio-waipio-gki/gki_kernel/dist/vmlinux.symvers"
)
DEFAULT_BASELINE_ABI = DEFAULT_BASELINE_SYMVERS.with_name("abi.xml")
BASELINE_SYMVERS_SHA256 = (
    "fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19"
)
BASELINE_ABI_SHA256 = (
    "3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c"
)
CRITICAL_SECURITY_CONFIGS = (
    "CONFIG_UH",
    "CONFIG_RKP",
    "CONFIG_KDP",
    "CONFIG_SECURITY_DEFEX",
    "CONFIG_FIVE",
    "CONFIG_PROCA",
    "CONFIG_CRYPTO_FIPS",
    "CONFIG_CRYPTO_FIPS140",
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_static_audit/result.json"
)


class AuditError(ValueError):
    pass


def compare_r4w1b_configs(stock_path: Path, generated_path: Path) -> dict[str, Any]:
    stock = r2.parse_config(stock_path)
    generated = r2.parse_config(generated_path)
    deltas = [
        {
            "key": key,
            "stock": stock.get(key, "<missing>"),
            "generated": generated.get(key, "<missing>"),
        }
        for key in sorted(set(stock) | set(generated))
        if stock.get(key) != generated.get(key)
    ]
    allowed = {r2.PATH_ONLY_CONFIG, WITNESS_CONFIG}
    unexpected = [delta for delta in deltas if delta["key"] not in allowed]
    witness = [delta for delta in deltas if delta["key"] == WITNESS_CONFIG]
    witness_exact = (
        len(witness) == 1
        and witness[0]["stock"] in ("<missing>", "n")
        and witness[0]["generated"] == "y"
    )
    path_deltas = [delta for delta in deltas if delta["key"] == r2.PATH_ONLY_CONFIG]
    path_only_valid = len(path_deltas) <= 1 and all(
        delta["stock"].startswith('"')
        and delta["stock"].endswith('"')
        and delta["generated"].startswith('"')
        and delta["generated"].endswith('"')
        for delta in path_deltas
    )
    full_lto = (
        generated.get("CONFIG_LTO_CLANG_FULL") == "y"
        and generated.get("CONFIG_LTO_CLANG_THIN") == "n"
    )
    security = {
        key: {
            "stock": stock.get(key, "<missing>"),
            "generated": generated.get(key, "<missing>"),
        }
        for key in CRITICAL_SECURITY_CONFIGS
    }
    security_preserved = all(
        row["stock"] == "y" and row["generated"] == "y"
        for row in security.values()
    )
    return {
        "stock_sha256": r2.sha256_file(stock_path),
        "generated_sha256": r2.sha256_file(generated_path),
        "delta_count": len(deltas),
        "deltas": deltas,
        "unexpected_deltas": unexpected,
        "witness_exact": witness_exact,
        "path_only_valid": path_only_valid,
        "full_lto": full_lto,
        "critical_security": security,
        "critical_security_preserved": security_preserved,
        "verified": (
            not unexpected
            and witness_exact
            and path_only_valid
            and full_lto
            and security_preserved
        ),
    }


def compare_full_symvers(baseline: Path, candidate: Path) -> dict[str, Any]:
    baseline_map, baseline_conflicts = r2.parse_symvers([baseline])
    candidate_map, candidate_conflicts = r2.parse_symvers([candidate])
    missing = sorted(set(baseline_map) - set(candidate_map))
    added = sorted(set(candidate_map) - set(baseline_map))
    mismatched = [
        {
            "symbol": symbol,
            "baseline": baseline_map[symbol],
            "candidate": candidate_map[symbol],
        }
        for symbol in sorted(set(baseline_map) & set(candidate_map))
        if baseline_map[symbol] != candidate_map[symbol]
    ]
    return {
        "baseline_sha256": r2.sha256_file(baseline),
        "candidate_sha256": r2.sha256_file(candidate),
        "baseline_symbols": len(baseline_map),
        "candidate_symbols": len(candidate_map),
        "baseline_conflicts": baseline_conflicts,
        "candidate_conflicts": candidate_conflicts,
        "missing_count": len(missing),
        "missing_sample": missing[:50],
        "added_count": len(added),
        "added_sample": added[:50],
        "mismatched_count": len(mismatched),
        "mismatched_sample": mismatched[:50],
        "verified": (
            not baseline_conflicts
            and not candidate_conflicts
            and not missing
            and not added
            and not mismatched
        ),
    }


def compare_abi_definition(baseline: Path, candidate: Path) -> dict[str, Any]:
    baseline_sha256 = r2.sha256_file(baseline)
    candidate_sha256 = r2.sha256_file(candidate)
    return {
        "baseline_path": str(baseline),
        "candidate_path": str(candidate),
        "baseline_sha256": baseline_sha256,
        "candidate_sha256": candidate_sha256,
        "baseline_size": baseline.stat().st_size,
        "candidate_size": candidate.stat().st_size,
        "verified": (
            baseline_sha256 == candidate_sha256
            and baseline.stat().st_size == candidate.stat().st_size
        ),
    }


def check_sec_log_buf_module(config_path: Path, module_path: Path) -> dict[str, Any]:
    config = r2.parse_config(config_path)
    module_regular = module_path.is_file() and not module_path.is_symlink()
    result = {
        "config_path": str(config_path),
        "config_value": config.get("CONFIG_SEC_LOG_BUF", "<missing>"),
        "module_path": str(module_path),
        "module_regular": module_regular,
        "module_sha256": r2.sha256_file(module_path) if module_regular else None,
    }
    result["verified"] = result["config_value"] == "m" and module_regular
    return result


def count_file_occurrences(path: Path, needle: bytes) -> int:
    if not needle:
        raise AuditError("empty byte pattern is not countable")
    count = 0
    overlap = len(needle) - 1
    tail = b""
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            data = tail + chunk
            count += data.count(needle)
            tail = data[-overlap:] if overlap else b""
    return count


def check_system_map(path: Path, symbols: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = {
        name: int(row["value"])
        for name, row in symbols.items()
        if name in {"kernel_init", "run_init_process", "strcmp"}
    }
    found: dict[str, list[int]] = {name: [] for name in expected}
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in found:
            try:
                found[fields[2]].append(int(fields[0], 16))
            except ValueError as exc:
                raise AuditError(f"invalid System.map address: {line}") from exc
    details = {
        name: {
            "vmlinux_address": address,
            "system_map_addresses": found[name],
            "verified": found[name] == [address],
        }
        for name, address in expected.items()
    }
    return {
        "path": str(path),
        "sha256": r2.sha256_file(path),
        "symbols": details,
        "verified": len(details) == 3 and all(
            row["verified"] for row in details.values()
        ),
    }


def check_final_binary_contract(
    *,
    image: Path,
    vmlinux: Path,
    system_map: Path,
    generated_config: Path,
    build_stdout: Path,
) -> dict[str, Any]:
    marker = patch_check.MARKER.encode("ascii")
    elf = elf_audit.inspect_final_vmlinux(vmlinux, marker)
    hmac = bytes.fromhex(elf["fips"]["hmac_hex"])
    image_hmac_count = count_file_occurrences(image, hmac)
    image_marker_count = count_file_occurrences(image, marker)
    image_family_count = count_file_occurrences(
        image, r4w1b_build.R4W1B_MARKER_FAMILY
    )
    historical_image_count = count_file_occurrences(
        image, r4w1b_build.HISTORICAL_R4W1_MARKER_FAMILY
    )
    historical_vmlinux_count = count_file_occurrences(
        vmlinux, r4w1b_build.HISTORICAL_R4W1_MARKER_FAMILY
    )
    config = r2.parse_config(generated_config)
    stdout = build_stdout.read_text(encoding="utf-8", errors="strict")
    fips_log = {
        "generate_count": stdout.count(
            "FIPS : Generating hmac of crypto and updating vmlinux"
        ),
        "complete_count": stdout.count(
            "FIPS integrity procedure has been finished for crypto"
        ),
    }
    fips_log["verified"] = (
        fips_log["generate_count"] == 1 and fips_log["complete_count"] == 1
    )
    system_map_gate = check_system_map(system_map, elf["symbols"])
    result = {
        "elf": elf,
        "system_map": system_map_gate,
        "image_hmac_count": image_hmac_count,
        "image_marker_count": image_marker_count,
        "image_family_count": image_family_count,
        "historical_image_family_count": historical_image_count,
        "historical_vmlinux_family_count": historical_vmlinux_count,
        "fips_config": config.get("CONFIG_CRYPTO_FIPS", "<missing>"),
        "fips140_config": config.get("CONFIG_CRYPTO_FIPS140", "<missing>"),
        "fips_log": fips_log,
    }
    result["verified"] = (
        elf["verified"]
        and system_map_gate["verified"]
        and image_hmac_count == 1
        and image_marker_count == 1
        and image_family_count == 1
        and historical_image_count == 0
        and historical_vmlinux_count == 0
        and result["fips_config"] == "y"
        and result["fips140_config"] == "y"
        and fips_log["verified"]
    )
    return result


def audit_build_result(
    path: Path,
    *,
    recorded_root: Path | None = None,
    expected_work_tree: Path | None = None,
    expected_artifacts: dict[str, Path] | None = None,
) -> dict[str, Any]:
    build = r2.load_json(path)
    timestamp = build.get("timestamp_control_runtime", {})
    kmi_path = build.get("kmi_path_control_runtime", {})
    kernel_debug = build.get("kernel_debug_control_runtime", {})
    vdso_debug = build.get("vdso_debug_control_runtime", {})
    patch_contract = build.get("r4w1b_patch_contract", {})
    source_delta = build.get("source_delta", {})
    effective_tools = build.get("provenance", {}).get("effective_tools", {})
    recorded_work_tree = build.get("work_tree")
    if isinstance(recorded_work_tree, str):
        recorded_path = Path(recorded_work_tree)
        if not recorded_path.is_absolute() and recorded_root is not None:
            recorded_path = recorded_root / recorded_path
        recorded_path = recorded_path.resolve()
    else:
        recorded_path = None
    work_tree_bound = expected_work_tree is None or (
        recorded_path == expected_work_tree.resolve()
    )
    output_rows = {
        row.get("name"): row
        for row in build.get("outputs", [])
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }
    artifact_bindings: dict[str, dict[str, Any]] = {}
    if expected_artifacts is not None:
        for name, artifact_path in expected_artifacts.items():
            row = output_rows.get(name, {})
            artifact_bindings[name] = {
                "path_match": (
                    isinstance(row.get("path"), str)
                    and Path(row["path"]).resolve() == artifact_path.resolve()
                ),
                "sha256_match": (
                    artifact_path.is_file()
                    and not artifact_path.is_symlink()
                    and row.get("sha256") == r2.sha256_file(artifact_path)
                ),
                "size_match": (
                    artifact_path.is_file()
                    and row.get("size") == artifact_path.stat().st_size
                ),
            }
            artifact_bindings[name]["verified"] = all(
                artifact_bindings[name].values()
            )
    artifacts_bound = expected_artifacts is None or (
        set(artifact_bindings) == set(expected_artifacts)
        and all(item["verified"] for item in artifact_bindings.values())
    )
    gate = {
        "path": str(path),
        "sha256": r2.sha256_file(path),
        "schema": build.get("schema"),
        "lto_mode": build.get("lto_mode"),
        "returncode": build.get("returncode"),
        "r4w1b_build_pass": build.get("r4w1b_build_pass"),
        "source_overlay_verified": build.get("provenance", {})
        .get("source_overlay", {})
        .get("verified"),
        "patch_contract_verdict": patch_contract.get("verdict"),
        "patch_sha256": source_delta.get("patch_sha256"),
        "source_delta_verified": source_delta.get("verified"),
        "effective_tools_verified": (
            effective_tools.get("verified") is True
            and effective_tools.get("expected_count")
            == len(r4w1b_build.base.EFFECTIVE_TOOL_NAMES)
            and len(effective_tools.get("tools", []))
            == len(r4w1b_build.base.EFFECTIVE_TOOL_NAMES)
            and all(row.get("verified") is True for row in effective_tools.get("tools", []))
        ),
        "recorded_work_tree": recorded_work_tree,
        "work_tree_bound": work_tree_bound,
        "artifact_bindings": artifact_bindings,
        "artifacts_bound": artifacts_bound,
        "output_gate_verified": build.get("output_gate", {}).get("verified"),
        "module_gate_verified": build.get("module_gate", {}).get("verified"),
        "kernel_banner_gate_verified": build.get("kernel_banner_gate", {}).get(
            "verified"
        ),
        "witness_output_gate_verified": build.get("witness_output_gate", {}).get(
            "verified"
        ),
        "timestamp_control_verified": (
            timestamp.get("applied") is True
            and timestamp.get("restored") is True
            and timestamp.get("patched_content_unchanged") is True
            and timestamp.get("restored_sha256") == timestamp.get("original_sha256")
        ),
        "kmi_path_control_verified": (
            kmi_path.get("applied") is True
            and kmi_path.get("restored") is True
            and kmi_path.get("patched_content_unchanged") is True
            and kmi_path.get("restored_sha256") == kmi_path.get("original_sha256")
            and kmi_path.get("original_sha256") == r4w1b_build.BUILD_SH_SHA256
        ),
        "kernel_debug_control_verified": (
            kernel_debug.get("applied") is True
            and kernel_debug.get("restored") is True
            and kernel_debug.get("patched_content_unchanged") is True
            and kernel_debug.get("restored_sha256")
            == kernel_debug.get("original_sha256")
            and kernel_debug.get("original_sha256")
            == r4w1b_build.KERNEL_MAKEFILE_SHA256
            and kernel_debug.get("object_map") == "/kernel-out"
        ),
        "vdso_debug_control_verified": (
            vdso_debug.get("applied") is True
            and vdso_debug.get("restored") is True
            and vdso_debug.get("patched_content_unchanged") is True
            and vdso_debug.get("verified") is True
            and len(vdso_debug.get("files", []))
            == len(r4w1b_build.VDSO_DEBUG_CONTROLS)
            and all(
                row.get("restored") is True
                and row.get("patched_content_unchanged") is True
                and row.get("original_sha256") == spec["sha256"]
                and row.get("source_map") == "/kernel-src"
                and row.get("object_map") == "/kernel-out"
                for row, spec in zip(
                    vdso_debug.get("files", []), r4w1b_build.VDSO_DEBUG_CONTROLS
                )
            )
        ),
    }
    gate["verified"] = (
        gate["schema"] == r4w1b_build.SCHEMA
        and gate["lto_mode"] == "full"
        and gate["returncode"] == 0
        and gate["r4w1b_build_pass"] is True
        and gate["source_overlay_verified"] is True
        and gate["patch_contract_verdict"] == patch_check.VERDICT
        and gate["patch_sha256"] == patch_check.PATCH_SHA256
        and gate["source_delta_verified"] is True
        and gate["effective_tools_verified"] is True
        and gate["work_tree_bound"] is True
        and gate["artifacts_bound"] is True
        and gate["output_gate_verified"] is True
        and gate["module_gate_verified"] is True
        and gate["kernel_banner_gate_verified"] is True
        and gate["witness_output_gate_verified"] is True
        and gate["timestamp_control_verified"] is True
        and gate["kmi_path_control_verified"] is True
        and gate["kernel_debug_control_verified"] is True
        and gate["vdso_debug_control_verified"] is True
    )
    return gate


def run_audit(
    root: Path,
    *,
    work_tree: Path,
    build_result: Path,
    baseline_symvers: Path,
    baseline_abi: Path,
    symvers_paths: list[Path] | None,
    stock_baseline: Path,
    stock_config: Path,
    requirements: list[Path],
    module_map: Path,
    corpus_layout: Path,
) -> dict[str, Any]:
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    image = dist / "Image"
    vmlinux = dist / "vmlinux"
    system_map = dist / "System.map"
    generated_config = work_tree / (
        "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    )
    candidate_symvers = dist / "vmlinux.symvers"
    candidate_abi = dist / "abi.xml"
    vendor_config = work_tree / "out/msm-waipio-waipio-gki/msm-kernel/.config"
    sec_log_buf_module = work_tree / (
        "out/msm-waipio-waipio-gki/dist/sec_log_buf.ko"
    )
    build_stdout = build_result.parent / "stdout.log"
    build_data = r2.load_json(build_result)
    if symvers_paths is None:
        symvers_items = build_data.get("symvers_files", [])
        symvers_paths = [Path(item["path"]) for item in symvers_items]
        if not symvers_paths:
            raise AuditError("build result contains no symvers files")
        for item, path in zip(symvers_items, symvers_paths):
            if not path.is_file() or r2.sha256_file(path) != item.get("sha256"):
                raise AuditError(f"build-result symvers identity mismatch: {path}")
    required = [
        image,
        vmlinux,
        system_map,
        generated_config,
        candidate_symvers,
        candidate_abi,
        vendor_config,
        sec_log_buf_module,
        build_result,
        build_stdout,
        baseline_symvers,
        baseline_abi,
        stock_baseline,
        stock_config,
        module_map,
        corpus_layout,
        *symvers_paths,
        *requirements,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise AuditError(f"required inputs missing: {missing}")

    stock = r2.load_json(stock_baseline)
    module_manifest = r2.load_json(module_map)
    corpus = r2.load_json(corpus_layout)
    if any(item.get("target") != TARGET for item in (stock, module_manifest, corpus)):
        raise AuditError("target mismatch in pinned baseline")
    expected_banner = stock.get("linux_banner")
    if not isinstance(expected_banner, str) or not expected_banner:
        raise AuditError("stock baseline has no Linux banner")

    build_gate = audit_build_result(
        build_result,
        recorded_root=root,
        expected_work_tree=work_tree,
        expected_artifacts={
            "Image": image,
            ".config": generated_config,
            "vmlinux.symvers": candidate_symvers,
            "abi.xml": candidate_abi,
            "vmlinux": vmlinux,
            "System.map": system_map,
        },
    )
    image_gate = r2.image_metadata(image, expected_banner=expected_banner)
    config_gate = compare_r4w1b_configs(stock_config, generated_config)
    consumer_crc = r2.compare_symbol_requirements(requirements, symvers_paths)
    full_symvers = compare_full_symvers(baseline_symvers, candidate_symvers)
    abi_definition = compare_abi_definition(baseline_abi, candidate_abi)
    baseline_identity = {
        "symvers_sha256": r2.sha256_file(baseline_symvers),
        "expected_symvers_sha256": BASELINE_SYMVERS_SHA256,
        "abi_sha256": r2.sha256_file(baseline_abi),
        "expected_abi_sha256": BASELINE_ABI_SHA256,
    }
    baseline_identity["verified"] = (
        baseline_identity["symvers_sha256"] == BASELINE_SYMVERS_SHA256
        and baseline_identity["abi_sha256"] == BASELINE_ABI_SHA256
    )
    sec_log_buf_gate = check_sec_log_buf_module(vendor_config, sec_log_buf_module)
    partition_capacity = r2.boot_capacity(stock, image_gate["file_bytes"])
    fixed_layout = {
        "capacity": r4w1b_build.FIXED_KERNEL_SLOT_CAPACITY,
        "image_bytes": image_gate["file_bytes"],
        "aligned_image_bytes": r2.aligned(image_gate["file_bytes"]),
        "remaining": r4w1b_build.FIXED_KERNEL_SLOT_CAPACITY - image_gate["file_bytes"],
        "absolute_ramdisk_start": r4w1b_build.ABSOLUTE_RAMDISK_START,
        "verified": (
            image_gate["file_bytes"] == r4w1b_build.STOCK_IMAGE_SIZE
            and r2.aligned(image_gate["file_bytes"])
            == r4w1b_build.FIXED_KERNEL_SLOT_CAPACITY
            and 4096 + r4w1b_build.FIXED_KERNEL_SLOT_CAPACITY
            == r4w1b_build.ABSOLUTE_RAMDISK_START
        ),
    }
    corpus_gate = {
        "vendor_ramdisk_modules": module_manifest.get("inputs", {}).get(
            "module_count"
        ),
        "layout_sha256": r2.sha256_file(corpus_layout),
        "complete_modules": corpus.get("complete_module_count"),
    }
    corpus_gate["verified"] = (
        corpus_gate["vendor_ramdisk_modules"] == r2.EXPECTED_VENDOR_RAMDISK_MODULES
        and corpus_gate["layout_sha256"] == r2.EXPECTED_CORPUS_LAYOUT_SHA256
        and corpus.get("schema") == "s22plus_fyg8_super_module_layout_v1"
        and corpus.get("complete_on_disk_module_corpus") is True
        and corpus_gate["complete_modules"] == 491
    )
    marker = patch_check.MARKER.encode("ascii")
    marker_gate = {
        "image_count": count_file_occurrences(image, marker),
        "image_family_count": count_file_occurrences(
            image, r4w1b_build.R4W1B_MARKER_FAMILY
        ),
        "image_historical_family_count": count_file_occurrences(
            image, r4w1b_build.HISTORICAL_R4W1_MARKER_FAMILY
        ),
        "vmlinux_count": count_file_occurrences(vmlinux, marker),
        "vmlinux_family_count": count_file_occurrences(
            vmlinux, r4w1b_build.R4W1B_MARKER_FAMILY
        ),
        "vmlinux_historical_family_count": count_file_occurrences(
            vmlinux, r4w1b_build.HISTORICAL_R4W1_MARKER_FAMILY
        ),
        "marker_id": patch_check.MARKER_ID,
    }
    marker_gate["verified"] = (
        marker_gate["image_count"] == 1
        and marker_gate["image_family_count"] == 1
        and marker_gate["image_historical_family_count"] == 0
        and marker_gate["vmlinux_count"] == 1
        and marker_gate["vmlinux_family_count"] == 1
        and marker_gate["vmlinux_historical_family_count"] == 0
    )
    final_binary = check_final_binary_contract(
        image=image,
        vmlinux=vmlinux,
        system_map=system_map,
        generated_config=generated_config,
        build_stdout=build_stdout,
    )

    gates = {
        "build": build_gate,
        "image": image_gate,
        "config": config_gate,
        "consumer_crc": consumer_crc,
        "baseline_identity": baseline_identity,
        "full_symvers": full_symvers,
        "abi_definition": abi_definition,
        "sec_log_buf_single_writer": sec_log_buf_gate,
        "partition_capacity": partition_capacity,
        "fixed_layout": fixed_layout,
        "module_corpus": corpus_gate,
        "marker": marker_gate,
        "final_binary": final_binary,
    }
    blockers: list[str] = []
    if not build_gate["verified"]:
        blockers.append("R4W1-B Full-LTO build provenance gate failed")
    if not image_gate["exact_banner_match"]:
        blockers.append("Linux banner differs from exact FYG8 baseline")
    if not config_gate["verified"]:
        blockers.append("config delta is not the exact R4W1-B contract")
    if not consumer_crc["provider_crc_closed"]:
        blockers.append("stock module-consumer CRC closure failed")
    if not consumer_crc["expected_baseline_shape"]:
        blockers.append("module-consumer requirement baseline shape changed")
    if not baseline_identity["verified"]:
        blockers.append("pinned R4W1 KMI/ABI baseline identity changed")
    if not full_symvers["verified"]:
        blockers.append("complete exported symbol/CRC mapping changed")
    if not abi_definition["verified"]:
        blockers.append("generated GKI ABI definition differs from baseline")
    if not sec_log_buf_gate["verified"]:
        blockers.append("sec_log_buf is not a loadable module for witness timing")
    if not partition_capacity["fits"]:
        blockers.append("Image exceeds boot partition capacity")
    if not fixed_layout["verified"]:
        blockers.append("Image does not match exact R4W1-B kernel geometry")
    if not corpus_gate["verified"]:
        blockers.append("pinned module corpus contract failed")
    if not marker_gate["verified"]:
        blockers.append("Image/vmlinux R4W1-B marker-family contract failed")
    if not final_binary["verified"]:
        blockers.append("final vmlinux control-flow/FIPS/System.map contract failed")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT if not blockers else "BLOCKED_R4W1B_STATIC_COMPATIBILITY",
        "gates": gates,
        "symvers_paths": [r2.display_path(root, path) for path in symvers_paths],
        "blockers": blockers,
        "r4w1b_static_pass": not blockers,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_packaging": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-tree", type=Path, required=True)
    parser.add_argument("--build-result", type=Path, required=True)
    parser.add_argument("--baseline-symvers", type=Path, default=DEFAULT_BASELINE_SYMVERS)
    parser.add_argument("--baseline-abi", type=Path, default=DEFAULT_BASELINE_ABI)
    parser.add_argument("--symvers", type=Path, action="append")
    parser.add_argument("--stock-baseline", type=Path, default=r2.DEFAULT_STOCK_BASELINE)
    parser.add_argument("--stock-config", type=Path, default=r2.DEFAULT_STOCK_CONFIG)
    parser.add_argument("--requirements", type=Path, action="append")
    parser.add_argument("--module-map", type=Path, default=r2.DEFAULT_MODULE_MAP)
    parser.add_argument("--corpus-layout", type=Path, default=r2.DEFAULT_CORPUS_LAYOUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = r2.repo_root()
    requirements = args.requirements or [
        r2.DEFAULT_REQUIREMENTS,
        r2.DEFAULT_EXTRA_REQUIREMENTS,
    ]
    result = run_audit(
        root,
        work_tree=r2.resolve(root, args.work_tree),
        build_result=r2.resolve(root, args.build_result),
        baseline_symvers=r2.resolve(root, args.baseline_symvers),
        baseline_abi=r2.resolve(root, args.baseline_abi),
        symvers_paths=(
            [r2.resolve(root, path) for path in args.symvers]
            if args.symvers
            else None
        ),
        stock_baseline=r2.resolve(root, args.stock_baseline),
        stock_config=r2.resolve(root, args.stock_config),
        requirements=[r2.resolve(root, path) for path in requirements],
        module_map=r2.resolve(root, args.module_map),
        corpus_layout=r2.resolve(root, args.corpus_layout),
    )
    out = r2.resolve(root, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(
        json.dumps(
            {
                "result": "pass" if result["r4w1b_static_pass"] else "blocked",
                "out": r2.display_path(root, out),
                "blocker_count": len(result["blockers"]),
                "fixed_layout_remaining": result["gates"]["fixed_layout"][
                    "remaining"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["r4w1b_static_pass"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, r2.AuditError, OSError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc
