#!/usr/bin/env python3
"""Build and audit the P3.18 timed Max77705 diagnostic twice."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import s22plus_fyg8_max77705_mux_diag_build as base
import s22plus_fyg8_p318_max77705_runtime_parser_fixture as parser_fixture


SCHEMA = "s22plus_fyg8_p318_max77705_diag_build_v1"
VERDICT = "PASS_P318_TIMED_MAX77705_DIAG_AB_ABI_QUALIFIED_H0"
MODULE_NAME = "s22plus_max77705_mux_diag_p318"
MODULE_SOURCE_DIR = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag_p318"
)
PREPARED_BUILD = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "dwc3-event-latch-build-20260814-01"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "max77705-timed-diag-build-20260814-01"
)
SOURCE_IDENTITIES = {
    "Makefile": (
        64,
        "3b245348388a8385dcc149c0d8ffa4d4ab892833c5a1eba0986fbf52d99fae06",
    ),
    "s22plus_max77705_mux_diag_p318.c": (
        12_145,
        "bcfca1632dfd6bb7792f68eaddd7a184f9cf48a6c106077539cbaf8db27dea11",
    ),
}
EXPECTED_UNDEFINED = base.EXPECTED_UNDEFINED | {"ktime_get"}
EXPECTED_CALLS = {**base.EXPECTED_CALL_RELOCATIONS, "ktime_get": 4}
EXPECTED_MODINFO = {
    "description": ["Bounded S22+ P3.18 timed Max77705 CONTROL1 diagnostic"],
    "license": ["GPL v2"],
    "depends": [""],
    "name": [MODULE_NAME],
    "vermagic": [base.EXPECTED_VERMAGIC],
    "parm": ["result:cached bounded P3.18 Max77705 MUX diagnostic result"],
}


class TimedDiagBuildError(RuntimeError):
    pass


def _sources(root: Path) -> dict[str, Any]:
    directory = base.resolve(root, MODULE_SOURCE_DIR)
    return {
        name: base.validate_file(
            directory / name, identity, f"P3.18 timed diagnostic source {name}"
        )
        for name, identity in SOURCE_IDENTITIES.items()
    }


def _prepared(root: Path) -> dict[str, Any]:
    directory = base.resolve(root, PREPARED_BUILD)
    audit_path = directory / "build-audit.json"
    if not audit_path.is_file() or audit_path.is_symlink():
        raise TimedDiagBuildError("prepared P3.10 ABI build receipt is missing")
    value = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        value.get("verdict")
        != "PASS_P318_DWC3_EVENT_LATCH_AB_ABI_QUALIFIED_H0"
        or value.get("a_b_byte_identical") is not True
    ):
        raise TimedDiagBuildError("prepared P3.10 ABI receipt differs")
    config = base.validate_file(
        directory / "kernel-out/.config",
        base.FIXED_ABI_IDENTITIES[".config"],
        "P3.18 prepared .config",
    )
    symvers = base.validate_file(
        directory / "kernel-out/Module.symvers",
        base.FIXED_ABI_IDENTITIES["vmlinux.symvers"],
        "P3.18 prepared Module.symvers",
    )
    common = directory / "source/kernel_platform/common"
    if not common.is_dir() or common.is_symlink():
        raise TimedDiagBuildError("prepared exact common source is unavailable")
    for relative, (_, expected) in base.BASE_PATCHED_FILES.items():
        if base.sha256_file(common / relative) != expected:
            raise TimedDiagBuildError(
                f"prepared exact common source differs: {relative}"
            )
    return {
        "path": str(directory),
        "receipt": {
            "size": audit_path.stat().st_size,
            "sha256": base.sha256_file(audit_path),
        },
        "config": config,
        "module_symvers": symvers,
        "exact_patched_source": True,
    }


def _audit_module(root: Path, ko: Path, symvers_path: Path) -> dict[str, Any]:
    toolchain = base.resolve(root, base.TOOLCHAIN) / "bin"
    llvm_nm = toolchain / "llvm-nm"
    llvm_readobj = toolchain / "llvm-readobj"
    header = base.run_checked(
        [str(llvm_readobj), "--file-headers", str(ko)], cwd=root
    ).stdout
    for token in (
        "Format: elf64-littleaarch64", "Arch: aarch64",
        "Type: Relocatable", "Machine: EM_AARCH64",
    ):
        if token not in header:
            raise TimedDiagBuildError(f"timed module ELF lacks {token!r}")
    undefined = base.parse_undefined_symbols(
        base.run_checked([str(llvm_nm), "--undefined-only", str(ko)], cwd=root).stdout
    )
    if undefined != EXPECTED_UNDEFINED:
        raise TimedDiagBuildError(
            "timed module import surface differs: "
            f"missing={sorted(EXPECTED_UNDEFINED - undefined)} "
            f"extra={sorted(undefined - EXPECTED_UNDEFINED)}"
        )
    defined = base.parse_defined_symbols(
        base.run_checked(
            [str(llvm_nm), "--defined-only", "--format=posix", str(ko)], cwd=root
        ).stdout
    )
    required_cfi = {
        "__cfi_check",
        "s22plus_max77705_result_get.cfi_jt",
        "s22plus_max77705_diag_probe.cfi_jt",
    }
    if not required_cfi.issubset(defined):
        raise TimedDiagBuildError("timed module CFI surface differs")
    relocations = base.run_checked(
        [str(llvm_readobj), "--relocations", str(ko)], cwd=root
    ).stdout
    calls = base.call_relocation_counts(relocations)
    actual_calls = {name: calls.get(name, 0) for name in EXPECTED_CALLS}
    if actual_calls != EXPECTED_CALLS:
        raise TimedDiagBuildError(f"timed module call surface differs: {actual_calls}")
    result_ops = base.relocation_section(
        relocations, ".rela.rodata.s22plus_max77705_result_ops"
    )
    driver = base.relocation_section(
        relocations, ".rela.data.s22plus_max77705_diag_driver"
    )
    if not re.search(
        rf"R_AARCH64_ABS64\s+\.text\s+0x{defined['s22plus_max77705_result_get.cfi_jt']:X}\b",
        result_ops,
    ) or not re.search(
        rf"R_AARCH64_ABS64\s+\.text\s+0x{defined['s22plus_max77705_diag_probe.cfi_jt']:X}\b",
        driver,
    ):
        raise TimedDiagBuildError("timed module callbacks bypass CFI jump tables")
    sections = base.run_checked(
        [str(llvm_readobj), "--sections", str(ko)], cwd=root
    ).stdout
    if "Name: __versions" not in sections or re.search(
        r"Name: _{2,3}ksymtab", sections
    ):
        raise TimedDiagBuildError("timed module version/export surface differs")
    fields = base.parse_modinfo(
        base.run_checked(["/usr/sbin/modinfo", str(ko)], cwd=root).stdout
    )
    for key, expected in EXPECTED_MODINFO.items():
        if fields.get(key) != expected:
            raise TimedDiagBuildError(
                f"timed module modinfo differs for {key}: {fields.get(key)}"
            )
    if set(fields) & {"alias", "firmware", "softdep"}:
        raise TimedDiagBuildError("timed module has forbidden metadata")
    versions = base.parse_modversions(
        base.run_checked(
            ["/usr/sbin/modprobe", "--dump-modversions", str(ko)], cwd=root
        ).stdout
    )
    if set(versions) != EXPECTED_UNDEFINED | {"module_layout"}:
        raise TimedDiagBuildError("timed module modversion set differs")
    symvers = base.parse_symvers(symvers_path.read_text(encoding="ascii"))
    mismatch = {
        symbol: (crc, symvers.get(symbol))
        for symbol, crc in versions.items()
        if symvers.get(symbol) != crc
    }
    if mismatch:
        raise TimedDiagBuildError(f"timed module modversion CRC differs: {mismatch}")
    return {
        "path": str(ko),
        "size": ko.stat().st_size,
        "sha256": base.sha256_file(ko),
        "undefined_imports": sorted(undefined),
        "call_relocations": actual_calls,
        "modversions": dict(sorted(versions.items())),
        "cfi": sorted(required_cfi),
        "exports": [],
        "modinfo": {key: fields[key] for key in EXPECTED_MODINFO},
        "verified": True,
    }


def _source_semantics(root: Path) -> dict[str, Any]:
    source = (
        base.resolve(root, MODULE_SOURCE_DIR)
        / "s22plus_max77705_mux_diag_p318.c"
    ).read_text(encoding="utf-8")
    ordered = (
        "result->pre_ns = ktime_get_ns();",
        "result->write_ns = ktime_get_ns();",
        "result->post1_ns = ktime_get_ns();",
        "msleep(S22PLUS_MAX77705_RETENTION_MS);",
        "result->post2_ns = ktime_get_ns();",
    )
    cursor = -1
    for token in ordered:
        cursor = source.find(token, cursor + 1)
        if cursor < 0:
            raise TimedDiagBuildError(f"timed source lacks ordered {token!r}")
    if source.count("ktime_get_ns()") != 4:
        raise TimedDiagBuildError("timed source clock sample count differs")
    if source.count("#define S22PLUS_MAX77705_RETENTION_MS 30000U") != 1:
        raise TimedDiagBuildError("timed source retention constant differs")
    parser = parser_fixture.audit(root)
    if (
        parser.get("verdict") != parser_fixture.VERDICT
        or parser.get("source_identities", {}).get("module", {}).get("sha256")
        != SOURCE_IDENTITIES["s22plus_max77705_mux_diag_p318.c"][1]
        or parser.get("timing_mask_and_value_bijection") is not True
        or parser.get("monotonic_sample_order_enforced") is not True
        or parser.get("retention_minimum_ns") != 30_000_000_000
    ):
        raise TimedDiagBuildError("timed module/parser fields differ")
    return {
        "clock": "ktime_get_ns_via_ktime_get",
        "sample_count": 4,
        "ordered_pre_write_post1_sleep_post2": True,
        "ambiguous_write_not_retried": source.count("write_ambiguous") >= 3,
        "actual_runtime_parser": parser,
        "verified": True,
    }


def audit_build(root: Path, output: Path) -> dict[str, Any]:
    prepared = _prepared(root)
    sources = _sources(root)
    symvers = base.resolve(root, base.P310_FIXED_A) / "vmlinux.symvers"
    paths = {
        side: output / f"immutable-{side}/{MODULE_NAME}.ko"
        for side in ("a", "b")
    }
    for side, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise TimedDiagBuildError(f"timed module {side} is missing")
    modules = {side: _audit_module(root, path, symvers) for side, path in paths.items()}
    if paths["a"].read_bytes() != paths["b"].read_bytes():
        raise TimedDiagBuildError("timed diagnostic A/B differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": base.TARGET,
        "host_only": True,
        "device_contact": False,
        "prepared_fixed_abi": prepared,
        "module_sources": sources,
        "source_semantics": _source_semantics(root),
        "modules": modules,
        "a_b_byte_identical": True,
        "linked_surface_delta_from_p317": {
            "added_undefined_imports": ["ktime_get"],
            "ktime_get_call_relocations": 4,
            "firmware_update": False,
            "reset": False,
            "irq": False,
            "workqueue": False,
            "notifier": False,
            "conditional_control1_write_maximum": 1,
        },
        "candidate_packaged": False,
        "live_authority": False,
        "verified": True,
    }


def run_build(root: Path, output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise TimedDiagBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < base.MIN_FREE_BYTES:
        raise TimedDiagBuildError("less than 4 GiB free before timed module build")
    output.mkdir()
    _prepared(root)
    _sources(root)
    base.validate_tools(root)
    prepared = base.resolve(root, PREPARED_BUILD)
    common = prepared / "source/kernel_platform/common"
    kernel_out = output / "kernel-out"
    kernel_out.mkdir()
    shutil.copy2(prepared / "kernel-out/.config", kernel_out / ".config")
    environment = base.build_environment(root, output)
    make_base = [
        "/usr/bin/make", "-C", str(common), f"O={kernel_out}", "-j2",
    ]
    base.run_checked(
        [*make_base, "modules_prepare"], cwd=root, env=environment,
        stdout_path=output / "modules-prepare.stdout.log",
        stderr_path=output / "modules-prepare.stderr.log",
    )
    base.validate_file(
        kernel_out / ".config", base.FIXED_ABI_IDENTITIES[".config"],
        "P3.18 prepared output .config",
    )
    shutil.copy2(
        prepared / "kernel-out/Module.symvers", kernel_out / "Module.symvers"
    )
    base.validate_file(
        kernel_out / "Module.symvers",
        base.FIXED_ABI_IDENTITIES["vmlinux.symvers"],
        "P3.18 prepared output Module.symvers",
    )
    stage = output / "module-stage"
    stage.mkdir()
    for name in SOURCE_IDENTITIES:
        shutil.copy2(base.resolve(root, MODULE_SOURCE_DIR) / name, stage / name)
    command = [
        *make_base, f"M={stage}", "modules",
    ]
    for side in ("a", "b"):
        base.run_checked(
            command, cwd=root, env=environment,
            stdout_path=output / f"module-{side}.stdout.log",
            stderr_path=output / f"module-{side}.stderr.log",
        )
        built = stage / f"{MODULE_NAME}.ko"
        if not built.is_file():
            raise TimedDiagBuildError(f"timed diagnostic build {side} emitted no module")
        immutable = output / f"immutable-{side}"
        immutable.mkdir()
        shutil.copy2(built, immutable / built.name)
        if side == "a":
            base.run_checked(
                command[:-1] + ["clean"], cwd=root, env=environment,
                stdout_path=output / "module-clean.stdout.log",
                stderr_path=output / "module-clean.stderr.log",
            )
            _sources(root)
    value = audit_build(root, output)
    base.atomic_json(output / "build-audit.json", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    audit = sub.add_parser("audit")
    audit.add_argument("--build-dir", type=Path, required=True)
    audit.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = base.repo_root()
    try:
        if args.command == "build":
            output = base.resolve(root, args.output)
            value = run_build(root, output)
        else:
            output = base.resolve(root, args.build_dir)
            value = audit_build(root, output)
            if args.output:
                base.atomic_json(base.resolve(root, args.output), value)
    except (base.BuildError, TimedDiagBuildError, OSError,
            subprocess.SubprocessError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
