#!/usr/bin/env python3
"""Audit FYG8 rebuilt-kernel static compatibility without packaging or device I/O.

The audit can inspect an incomplete diagnostic build, but only an R1 Full-LTO
result plus a complete shipped-module corpus can produce an R2 PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_kernel_r2_audit_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
STOCK_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
STOCK_COMPILER_MARKER = "Android (7284624, based on r416183b) clang version 12.0.5"
EXPECTED_VENDOR_RAMDISK_MODULES = 441
EXPECTED_REQUIREMENT_ROWS = 25864
EXPECTED_REQUIREMENT_SYMBOLS = 4619
DEFAULT_WORK_TREE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_STOCK_BASELINE = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/"
    "stock-kernel-baseline.json"
)
DEFAULT_STOCK_CONFIG = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/stock-ikconfig"
)
DEFAULT_REQUIREMENTS = Path(
    "docs/module-map/s22plus-fyg8/symbol-crc-requirements.tsv"
)
DEFAULT_EXTRA_REQUIREMENTS = Path(
    "docs/module-map/s22plus-fyg8-super/vendor-dlkm-only-symbol-crc-requirements.tsv"
)
DEFAULT_MODULE_MAP = Path("docs/module-map/s22plus-fyg8/manifest.json")
DEFAULT_CORPUS_LAYOUT = Path("docs/module-map/s22plus-fyg8-super/layout-manifest.json")
EXPECTED_CORPUS_LAYOUT_SHA256 = "89d97fd7215ca1e830a983de61779baa13d4ecba3573bc2778ba98c5c26bca3e"
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/r2-diagnostic/result.json"
)
PATH_ONLY_CONFIG = "CONFIG_UNUSED_KSYMS_WHITELIST"


class AuditError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise AuditError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be an object: {path}")
    return value


def parse_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
        else:
            match = re.fullmatch(r"# (CONFIG_[A-Za-z0-9_]+) is not set", raw)
            if not match:
                continue
            key, value = match.group(1), "n"
        if key in values:
            raise AuditError(f"duplicate config key at {path}:{line_number}: {key}")
        values[key] = value
    return values


def compare_configs(stock_path: Path, generated_path: Path, *, mode: str) -> dict[str, Any]:
    stock = parse_config(stock_path)
    generated = parse_config(generated_path)
    deltas = [
        {"key": key, "stock": stock.get(key, "<missing>"), "generated": generated.get(key, "<missing>")}
        for key in sorted(set(stock) | set(generated))
        if stock.get(key) != generated.get(key)
    ]
    allowed_keys = {PATH_ONLY_CONFIG}
    if mode == "diagnostic":
        allowed_keys.update({"CONFIG_LTO_CLANG_FULL", "CONFIG_LTO_CLANG_THIN"})
    unexpected = [delta for delta in deltas if delta["key"] not in allowed_keys]
    full_lto = generated.get("CONFIG_LTO_CLANG_FULL") == "y" and generated.get("CONFIG_LTO_CLANG_THIN") == "n"
    path_only_valid = all(
        delta["key"] != PATH_ONLY_CONFIG
        or (
            delta["stock"].startswith('"')
            and delta["stock"].endswith('"')
            and delta["generated"].startswith('"')
            and delta["generated"].endswith('"')
        )
        for delta in deltas
    )
    return {
        "stock_sha256": sha256_file(stock_path),
        "generated_sha256": sha256_file(generated_path),
        "delta_count": len(deltas),
        "deltas": deltas,
        "unexpected_deltas": unexpected,
        "path_only_delta_valid": path_only_valid,
        "full_lto": full_lto,
        "compatible_for_mode": not unexpected and path_only_valid and (mode == "diagnostic" or full_lto),
    }


def image_metadata(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 0x40:
        raise AuditError(f"ARM64 Image is too short: {path}")
    magic = data[0x38:0x3C]
    if magic != b"ARM\x64":
        raise AuditError(f"ARM64 Image magic mismatch: {path}: {magic!r}")
    banner_match = re.search(rb"Linux version ([^\x00\s]+).*?#1 SMP PREEMPT[^\x00]*", data)
    banner = banner_match.group(0).decode("ascii", errors="replace") if banner_match else ""
    release = banner_match.group(1).decode("ascii") if banner_match else ""
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "file_bytes": len(data),
        "header_image_size": struct.unpack_from("<Q", data, 0x10)[0],
        "text_offset": struct.unpack_from("<Q", data, 0x08)[0],
        "magic": "ARM64",
        "release": release,
        "banner": banner,
        "release_match": release == STOCK_RELEASE,
        "compiler_match": STOCK_COMPILER_MARKER in banner,
    }


def parse_symvers(paths: Iterable[Path]) -> tuple[dict[str, str], list[dict[str, str]]]:
    symbols: dict[str, str] = {}
    conflicts: list[dict[str, str]] = []
    for path in paths:
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            fields = raw.split()
            if len(fields) < 2 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", fields[0]):
                raise AuditError(f"malformed symvers row at {path}:{line_number}")
            crc, symbol = fields[0].lower(), fields[1]
            previous = symbols.get(symbol)
            if previous is not None and previous != crc:
                conflicts.append({"symbol": symbol, "first_crc": previous, "other_crc": crc, "path": str(path)})
            else:
                symbols[symbol] = crc
    return symbols, conflicts


def compare_symbol_requirements(requirements_paths: list[Path], symvers_paths: list[Path]) -> dict[str, Any]:
    providers, conflicts = parse_symvers(symvers_paths)
    missing: dict[str, int] = {}
    mismatched: dict[str, dict[str, Any]] = {}
    rows = 0
    required_symbols: set[str] = set()
    rows_by_provider_status: dict[str, int] = {}
    missing_rows_by_provider_status: dict[str, int] = {}
    mismatched_rows_by_provider_status: dict[str, int] = {}
    seen_module_symbols: set[tuple[str, str]] = set()
    for requirements_path in requirements_paths:
        with requirements_path.open("r", encoding="ascii") as handle:
            header = handle.readline().rstrip("\n").split("\t")
            if header != ["module", "symbol", "required_crc", "provider_status"]:
                raise AuditError(f"unexpected requirement TSV header: {header}")
            for line_number, raw in enumerate(handle, 2):
                fields = raw.rstrip("\n").split("\t")
                if len(fields) != 4:
                    raise AuditError(f"malformed requirement row at {requirements_path}:{line_number}")
                module, symbol, expected, provider_status = fields
                identity = (module, symbol)
                if identity in seen_module_symbols:
                    raise AuditError(f"duplicate module/symbol requirement across inputs: {identity}")
                seen_module_symbols.add(identity)
                expected = expected.lower()
                rows += 1
                required_symbols.add(symbol)
                rows_by_provider_status[provider_status] = rows_by_provider_status.get(provider_status, 0) + 1
                actual = providers.get(symbol)
                if actual is None:
                    missing[symbol] = missing.get(symbol, 0) + 1
                    missing_rows_by_provider_status[provider_status] = missing_rows_by_provider_status.get(provider_status, 0) + 1
                elif actual != expected:
                    mismatched_rows_by_provider_status[provider_status] = mismatched_rows_by_provider_status.get(provider_status, 0) + 1
                    entry = mismatched.setdefault(symbol, {"expected": expected, "actual": actual, "consumers": []})
                    if len(entry["consumers"]) < 20:
                        entry["consumers"].append(module)
    return {
        "requirements": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in requirements_paths
        ],
        "requirement_rows": rows,
        "required_unique_symbols": len(required_symbols),
        "provider_unique_symbols": len(providers),
        "matched_requirement_rows": rows - sum(missing.values()) - sum(
            mismatched_rows_by_provider_status.values()
        ),
        "rows_by_provider_status": dict(sorted(rows_by_provider_status.items())),
        "missing_rows_by_provider_status": dict(sorted(missing_rows_by_provider_status.items())),
        "mismatched_rows_by_provider_status": dict(sorted(mismatched_rows_by_provider_status.items())),
        "symvers_conflict_count": len(conflicts),
        "symvers_conflict_sample": conflicts[:20],
        "missing_unique_symbols": len(missing),
        "missing_requirement_rows": sum(missing.values()),
        "missing_sample": sorted(missing)[:50],
        "mismatched_unique_symbols": len(mismatched),
        "mismatched_sample": [
            {"symbol": symbol, **mismatched[symbol]}
            for symbol in sorted(mismatched)[:50]
        ],
        "expected_baseline_shape": rows == EXPECTED_REQUIREMENT_ROWS and len(required_symbols) == EXPECTED_REQUIREMENT_SYMBOLS,
        "provider_crc_closed": not conflicts and not missing and not mismatched,
    }


def aligned(value: int, alignment: int = 4096) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def boot_capacity(stock: dict[str, Any], image_bytes: int) -> dict[str, Any]:
    inputs = stock["inputs"]
    header = stock["boot_header"]
    partition_bytes = inputs["boot_img"]["size"]
    fixed_bytes = 4096 + aligned(header["ramdisk_size"]) + aligned(header["signature_size"])
    max_kernel_bytes = partition_bytes - fixed_bytes
    return {
        "boot_partition_bytes": partition_bytes,
        "fixed_non_kernel_bytes": fixed_bytes,
        "max_kernel_bytes": max_kernel_bytes,
        "generated_kernel_bytes": image_bytes,
        "fits": image_bytes <= max_kernel_bytes,
    }


def audit(
    root: Path,
    *,
    mode: str,
    image: Path,
    generated_config: Path,
    symvers_paths: list[Path],
    stock_baseline_path: Path,
    stock_config: Path,
    requirements: list[Path],
    module_map_path: Path,
    corpus_layout_path: Path,
    r1_result_path: Path | None,
) -> dict[str, Any]:
    required_files = [image, generated_config, stock_baseline_path, stock_config, *requirements, module_map_path, corpus_layout_path, *symvers_paths]
    missing_files = [display_path(root, path) for path in required_files if not path.is_file()]
    if missing_files:
        raise AuditError(f"required input missing: {missing_files}")
    stock = load_json(stock_baseline_path)
    module_map = load_json(module_map_path)
    corpus_layout = load_json(corpus_layout_path)
    if stock.get("target") != TARGET or module_map.get("target") != TARGET or corpus_layout.get("target") != TARGET:
        raise AuditError("target mismatch in pinned baseline")
    module_count = module_map.get("inputs", {}).get("module_count")
    module_shape_ok = module_count == EXPECTED_VENDOR_RAMDISK_MODULES
    image_result = image_metadata(image)
    config_result = compare_configs(stock_config, generated_config, mode=mode)
    symbols_result = compare_symbol_requirements(requirements, symvers_paths)
    capacity_result = boot_capacity(stock, image_result["file_bytes"])
    corpus_layout_verified = (
        sha256_file(corpus_layout_path) == EXPECTED_CORPUS_LAYOUT_SHA256
        and corpus_layout.get("schema") == "s22plus_fyg8_super_module_layout_v1"
        and corpus_layout.get("complete_on_disk_module_corpus") is True
        and corpus_layout.get("complete_module_count") == 491
    )

    r1_gate: dict[str, Any] = {"required": mode == "r2", "verified": mode == "diagnostic"}
    if r1_result_path is not None:
        if not r1_result_path.is_file():
            raise AuditError(f"R1 result missing: {r1_result_path}")
        r1 = load_json(r1_result_path)
        r1_gate = {
            "required": mode == "r2",
            "path": display_path(root, r1_result_path),
            "sha256": sha256_file(r1_result_path),
            "schema": r1.get("schema"),
            "lto_mode": r1.get("lto_mode"),
            "returncode": r1.get("returncode"),
            "r1_buildability_pass": r1.get("r1_buildability_pass"),
            "source_overlay_verified": r1.get("provenance", {}).get("source_overlay", {}).get("verified"),
            "output_gate_verified": r1.get("output_gate", {}).get("verified"),
            "module_gate_verified": r1.get("module_gate", {}).get("verified"),
            "modules_builtin_present": {
                "modules.builtin",
                "modules.builtin.modinfo",
            }.issubset(set(r1.get("output_gate", {}).get("present", []))),
        }
        r1_gate["verified"] = (
            r1_gate["schema"] == "s22plus_fyg8_kernel_build_v2"
            and r1_gate["lto_mode"] == "full"
            and r1_gate["returncode"] == 0
            and r1_gate["r1_buildability_pass"] is True
            and r1_gate["source_overlay_verified"] is True
            and r1_gate["output_gate_verified"] is True
            and r1_gate["module_gate_verified"] is True
            and r1_gate["modules_builtin_present"] is True
        )

    blockers: list[str] = []
    if mode == "r2" and not r1_gate.get("verified"):
        blockers.append("pinned Full-LTO R1 PASS result is absent or invalid")
    if not image_result["release_match"] or not image_result["compiler_match"]:
        blockers.append("generated Image release/compiler metadata differs from FYG8")
    if not config_result["compatible_for_mode"]:
        blockers.append("generated config has non-allowlisted stock delta or is not Full LTO")
    if not capacity_result["fits"]:
        blockers.append("generated Image does not fit the stock boot partition layout")
    if not symbols_result["provider_crc_closed"]:
        blockers.append("declared module-consumed symbol CRCs are not closed by supplied symvers files")
    if not symbols_result["expected_baseline_shape"] or not module_shape_ok:
        blockers.append("pinned 441-module vendor-ramdisk baseline shape changed")
    if not corpus_layout_verified:
        blockers.append("complete on-disk module corpus layout manifest is absent or invalid")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "mode": mode,
        "inputs": {
            "image": display_path(root, image),
            "generated_config": display_path(root, generated_config),
            "symvers": [display_path(root, path) for path in symvers_paths],
            "stock_baseline": display_path(root, stock_baseline_path),
            "stock_config": display_path(root, stock_config),
            "requirements": [display_path(root, path) for path in requirements],
            "module_map": display_path(root, module_map_path),
            "corpus_layout": display_path(root, corpus_layout_path),
        },
        "r1_gate": r1_gate,
        "image": image_result,
        "config": config_result,
        "module_provider_crc": symbols_result,
        "boot_capacity": capacity_result,
        "module_corpus": {
            "declared_scope": "vendor-ramdisk-plus-vendor-dlkm-complete-on-disk-union",
            "vendor_ramdisk_module_count": module_count,
            "expected_vendor_ramdisk_modules": EXPECTED_VENDOR_RAMDISK_MODULES,
            "vendor_ramdisk_shape_ok": module_shape_ok,
            "complete_on_disk_corpus": corpus_layout_verified,
            "complete_unique_module_names": corpus_layout.get("complete_module_count", 0),
            "layout_manifest_sha256": sha256_file(corpus_layout_path),
        },
        "blockers": blockers,
        "r2_static_pass": not blockers,
        "interpretation": "diagnostic evidence only" if mode == "diagnostic" else "R2 fail-closed static compatibility verdict",
        "safety": {
            "device_contact": False,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("diagnostic", "r2"), default="r2")
    parser.add_argument("--work-tree", type=Path, default=DEFAULT_WORK_TREE)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--symvers", type=Path, action="append")
    parser.add_argument("--stock-baseline", type=Path, default=DEFAULT_STOCK_BASELINE)
    parser.add_argument("--stock-config", type=Path, default=DEFAULT_STOCK_CONFIG)
    parser.add_argument("--requirements", type=Path, action="append")
    parser.add_argument("--module-map", type=Path, default=DEFAULT_MODULE_MAP)
    parser.add_argument("--corpus-layout", type=Path, default=DEFAULT_CORPUS_LAYOUT)
    parser.add_argument("--r1-result", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    work_tree = resolve(root, args.work_tree)
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    image = resolve(root, args.image) if args.image else dist / "Image"
    config = resolve(root, args.config) if args.config else work_tree / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    if args.symvers:
        symvers = [resolve(root, path) for path in args.symvers]
    elif args.r1_result:
        r1_for_paths = load_json(resolve(root, args.r1_result))
        symvers = [Path(item["path"]) for item in r1_for_paths.get("symvers_files", [])]
        if not symvers:
            raise AuditError("R1 result contains no symvers files")
        for item, path in zip(r1_for_paths["symvers_files"], symvers):
            if not path.is_file() or sha256_file(path) != item.get("sha256"):
                raise AuditError(f"R1 symvers identity mismatch: {path}")
    else:
        symvers = [dist / "vmlinux.symvers"]
    result = audit(
        root,
        mode=args.mode,
        image=image,
        generated_config=config,
        symvers_paths=symvers,
        stock_baseline_path=resolve(root, args.stock_baseline),
        stock_config=resolve(root, args.stock_config),
        requirements=[
            resolve(root, path)
            for path in (
                args.requirements
                if args.requirements
                else [DEFAULT_REQUIREMENTS, DEFAULT_EXTRA_REQUIREMENTS]
            )
        ],
        module_map_path=resolve(root, args.module_map),
        corpus_layout_path=resolve(root, args.corpus_layout),
        r1_result_path=resolve(root, args.r1_result) if args.r1_result else None,
    )
    out = resolve(root, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({
        "result": "pass" if result["r2_static_pass"] else "blocked",
        "mode": args.mode,
        "out": display_path(root, out),
        "blocker_count": len(result["blockers"]),
        "missing_crc_symbols": result["module_provider_crc"]["missing_unique_symbols"],
        "mismatched_crc_symbols": result["module_provider_crc"]["mismatched_unique_symbols"],
    }, indent=2, sort_keys=True))
    return 0 if (args.mode == "diagnostic" or result["r2_static_pass"]) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, KeyError, OSError, struct.error) as exc:
        raise SystemExit(str(exc)) from exc
