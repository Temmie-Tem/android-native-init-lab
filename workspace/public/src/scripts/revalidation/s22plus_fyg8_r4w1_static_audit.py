#!/usr/bin/env python3
"""Run the fail-closed R4W1 static compatibility audit host-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_kernel_r2_audit as r2  # noqa: E402
import s22plus_fyg8_r4w1_build as r4_build  # noqa: E402
import s22plus_fyg8_r4w1_patch_check as patch_check  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1_static_audit_v1"
TARGET = r2.TARGET
VERDICT = "PASS_R4W1_STATIC_COMPATIBILITY"
WITNESS_CONFIG = "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"
DEFAULT_BASELINE_SYMVERS = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/"
    "remote-fx8300-r1-v3-operational/source-clean-final/out/"
    "msm-waipio-waipio-gki/gki_kernel/dist/vmlinux.symvers"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1_static_audit/result.json"
)


class AuditError(ValueError):
    pass


def compare_r4_configs(stock_path: Path, generated_path: Path) -> dict[str, Any]:
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
    return {
        "stock_sha256": r2.sha256_file(stock_path),
        "generated_sha256": r2.sha256_file(generated_path),
        "delta_count": len(deltas),
        "deltas": deltas,
        "unexpected_deltas": unexpected,
        "witness_exact": witness_exact,
        "path_only_valid": path_only_valid,
        "full_lto": full_lto,
        "verified": not unexpected and witness_exact and path_only_valid and full_lto,
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
    vdso_debug = build.get("vdso_debug_control_runtime", {})
    patch_contract = build.get("r4w1_patch_contract", {})
    source_delta = build.get("source_delta", {})
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
        "r4w1_build_pass": build.get("r4w1_build_pass"),
        "source_overlay_verified": build.get("provenance", {})
        .get("source_overlay", {})
        .get("verified"),
        "patch_contract_verdict": patch_contract.get("verdict"),
        "patch_sha256": source_delta.get("patch_sha256"),
        "source_delta_verified": source_delta.get("verified"),
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
            and kmi_path.get("original_sha256") == r4_build.BUILD_SH_SHA256
        ),
        "vdso_debug_control_verified": (
            vdso_debug.get("applied") is True
            and vdso_debug.get("restored") is True
            and vdso_debug.get("patched_content_unchanged") is True
            and vdso_debug.get("verified") is True
            and len(vdso_debug.get("files", []))
            == len(r4_build.VDSO_DEBUG_CONTROLS)
            and all(
                row.get("restored") is True
                and row.get("patched_content_unchanged") is True
                and row.get("original_sha256") == spec["sha256"]
                and row.get("source_map") == "/kernel-src"
                and row.get("object_map") == "/kernel-out"
                for row, spec in zip(
                    vdso_debug.get("files", []), r4_build.VDSO_DEBUG_CONTROLS
                )
            )
        ),
    }
    gate["verified"] = (
        gate["schema"] == r4_build.SCHEMA
        and gate["lto_mode"] == "full"
        and gate["returncode"] == 0
        and gate["r4w1_build_pass"] is True
        and gate["source_overlay_verified"] is True
        and gate["patch_contract_verdict"] == patch_check.VERDICT
        and gate["patch_sha256"] == patch_check.PATCH_SHA256
        and gate["source_delta_verified"] is True
        and gate["work_tree_bound"] is True
        and gate["artifacts_bound"] is True
        and gate["output_gate_verified"] is True
        and gate["module_gate_verified"] is True
        and gate["kernel_banner_gate_verified"] is True
        and gate["witness_output_gate_verified"] is True
        and gate["timestamp_control_verified"] is True
        and gate["kmi_path_control_verified"] is True
        and gate["vdso_debug_control_verified"] is True
    )
    return gate


def run_audit(
    root: Path,
    *,
    work_tree: Path,
    build_result: Path,
    baseline_symvers: Path,
    symvers_paths: list[Path] | None,
    stock_baseline: Path,
    stock_config: Path,
    requirements: list[Path],
    module_map: Path,
    corpus_layout: Path,
) -> dict[str, Any]:
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    image = dist / "Image"
    generated_config = work_tree / (
        "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    )
    candidate_symvers = dist / "vmlinux.symvers"
    vendor_config = work_tree / "out/msm-waipio-waipio-gki/msm-kernel/.config"
    sec_log_buf_module = work_tree / (
        "out/msm-waipio-waipio-gki/dist/sec_log_buf.ko"
    )
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
        generated_config,
        candidate_symvers,
        vendor_config,
        sec_log_buf_module,
        build_result,
        baseline_symvers,
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
        },
    )
    image_gate = r2.image_metadata(image, expected_banner=expected_banner)
    config_gate = compare_r4_configs(stock_config, generated_config)
    consumer_crc = r2.compare_symbol_requirements(requirements, symvers_paths)
    full_symvers = compare_full_symvers(baseline_symvers, candidate_symvers)
    sec_log_buf_gate = check_sec_log_buf_module(vendor_config, sec_log_buf_module)
    partition_capacity = r2.boot_capacity(stock, image_gate["file_bytes"])
    fixed_layout = {
        "capacity": r4_build.FIXED_KERNEL_SLOT_CAPACITY,
        "image_bytes": image_gate["file_bytes"],
        "aligned_image_bytes": r2.aligned(image_gate["file_bytes"]),
        "remaining": r4_build.FIXED_KERNEL_SLOT_CAPACITY - image_gate["file_bytes"],
        "verified": (
            image_gate["file_bytes"] <= r4_build.FIXED_KERNEL_SLOT_CAPACITY
            and r2.aligned(image_gate["file_bytes"])
            == r4_build.FIXED_KERNEL_SLOT_CAPACITY
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
        "image_count": image.read_bytes().count(marker),
        "marker_id": patch_check.MARKER_ID,
    }
    marker_gate["verified"] = marker_gate["image_count"] == 1

    gates = {
        "build": build_gate,
        "image": image_gate,
        "config": config_gate,
        "consumer_crc": consumer_crc,
        "full_symvers": full_symvers,
        "sec_log_buf_single_writer": sec_log_buf_gate,
        "partition_capacity": partition_capacity,
        "fixed_layout": fixed_layout,
        "module_corpus": corpus_gate,
        "marker": marker_gate,
    }
    blockers: list[str] = []
    if not build_gate["verified"]:
        blockers.append("R4W1 Full-LTO build provenance gate failed")
    if not image_gate["exact_banner_match"]:
        blockers.append("Linux banner differs from exact FYG8 baseline")
    if not config_gate["verified"]:
        blockers.append("config delta is not the exact R4W1 contract")
    if not consumer_crc["provider_crc_closed"]:
        blockers.append("stock module-consumer CRC closure failed")
    if not consumer_crc["expected_baseline_shape"]:
        blockers.append("module-consumer requirement baseline shape changed")
    if not full_symvers["verified"]:
        blockers.append("complete exported symbol/CRC mapping changed")
    if not sec_log_buf_gate["verified"]:
        blockers.append("sec_log_buf is not a loadable module for witness timing")
    if not partition_capacity["fits"]:
        blockers.append("Image exceeds boot partition capacity")
    if not fixed_layout["verified"]:
        blockers.append("Image exceeds fixed pre-ramdisk kernel slot")
    if not corpus_gate["verified"]:
        blockers.append("pinned module corpus contract failed")
    if not marker_gate["verified"]:
        blockers.append("Image does not contain exactly one R4W1 marker")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT if not blockers else "BLOCKED_R4W1_STATIC_COMPATIBILITY",
        "gates": gates,
        "symvers_paths": [r2.display_path(root, path) for path in symvers_paths],
        "blockers": blockers,
        "r4w1_static_pass": not blockers,
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
                "result": "pass" if result["r4w1_static_pass"] else "blocked",
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
    return 0 if result["r4w1_static_pass"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, r2.AuditError, OSError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc
