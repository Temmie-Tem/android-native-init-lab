#!/usr/bin/env python3
"""Independently verify two candidate-bound P2.34 clean kernel builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p234_build as build  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_build_repro_check_v1"
VERDICT = "PASS_P234_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY"
TARGET = candidate_contract.TARGET
DEFAULT_BUILD_A = Path("workspace/private/outputs/s22plus_fyg8_p234/artifacts-a")
DEFAULT_BUILD_B = Path("workspace/private/outputs/s22plus_fyg8_p234/artifacts-b")
DEFAULT_INTENT = candidate_contract.DEFAULT_INTENT
DEFAULT_PATCH = candidate_contract.DEFAULT_PATCH
DEFAULT_SOURCE = candidate_contract.DEFAULT_SOURCE
DEFAULT_NM = Path("/usr/bin/aarch64-linux-gnu-nm")
DEFAULT_OBJDUMP = Path("/usr/bin/aarch64-linux-gnu-objdump")

ARTIFACT_LIMITS = {
    "Image": 64 * 1024 * 1024,
    "vmlinux": 1024 * 1024 * 1024,
    ".config": 1024 * 1024,
    "System.map": 32 * 1024 * 1024,
    "vmlinux.symvers": 4 * 1024 * 1024,
    "abi.xml": 64 * 1024 * 1024,
    "build-result.json": 8 * 1024 * 1024,
}
REQUIRED_GATES = (
    "clean_output_precondition",
    "exclusive_output_root",
    "source_symlink_control_runtime",
    "output_gate",
    "module_gate",
    "kernel_banner_gate",
    "witness_output_gate",
    "sec_log_buf_timing_gate",
)
REQUIRED_SYMBOLS = (
    "__pi___flush_dcache_area",
    "kernel_init",
    "s22_fyg8_e1_head",
    "s22_fyg8_e1_record_families_allowed",
    "s22_fyg8_e1_write",
)
RANDOM_PRIVATE_PATH_PREFIX = b"/tmp/s22-r4w1b-private-"


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    return candidate_contract.intent.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return candidate_contract.intent.resolve(root, path)


def stable_receipt(path: Path, label: str, maximum: int) -> dict[str, Any]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= maximum:
            raise CheckError(f"{label} is not a bounded regular file")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if size != before.st_size or any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in fields
    ):
        raise CheckError(f"{label} changed while hashing")
    return {"size": size, "sha256": digest.hexdigest()}


def _load_result(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    data = candidate_contract.stable_read(
        path,
        "P2.34 build result",
        ARTIFACT_LIMITS["build-result.json"],
    )
    receipt = candidate_contract.intent.receipt(data)
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("P2.34 build result is not valid ASCII JSON") from exc
    if not isinstance(value, dict):
        raise CheckError("P2.34 build result root is not an object")
    return value, receipt


def _output_rows(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    outputs = result.get("outputs")
    if not isinstance(outputs, list):
        raise CheckError("P2.34 build output inventory is missing")
    for row in outputs:
        if not isinstance(row, dict) or row.get("name") not in ARTIFACT_LIMITS:
            continue
        name = row["name"]
        if name == "build-result.json":
            continue
        if name in rows:
            raise CheckError(f"duplicate P2.34 build output: {name}")
        rows[name] = row
    required = set(ARTIFACT_LIMITS) - {"build-result.json"}
    if set(rows) != required:
        raise CheckError(
            f"P2.34 build output set mismatch: {sorted(rows)}"
        )
    return rows


def _source_delta_hashes(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise CheckError(f"P2.34 source delta {label} is missing")
    result = {}
    for name, row in value.items():
        if (
            not isinstance(name, str)
            or not isinstance(row, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256")))
        ):
            raise CheckError(f"P2.34 source delta {label} is malformed")
        result[name] = row["sha256"]
    return result


def _classify_wrapper_result(result: dict[str, Any]) -> str:
    witness = result.get("witness_output_gate")
    if not isinstance(witness, dict):
        raise CheckError("P2.34 witness output gate is missing")
    if (
        result.get("returncode") == 0
        and result.get("p234_build_pass") is True
        and witness.get("verified") is True
    ):
        return "final-wrapper-pass"

    inactive = {
        family.decode("ascii"): {"image": 0, "vmlinux": 0}
        for family in build.HISTORICAL_FAMILIES
    }
    inert = {
        family.decode("ascii"): {"image": 1, "vmlinux": 1}
        for family in build.INERT_REJECTION_FAMILIES
    }
    exact_binary_counts = {
        "long_family": 1,
        "unsat_family": 1,
        "request_magic": 1,
        "run_id_hex": 1,
        "unsat_tag_hex": 1,
        "model_run_id": 0,
        "source_check_run_id": 0,
    }
    legacy_false_negative = (
        result.get("returncode") == 7
        and result.get("p234_build_pass") is False
        and witness.get("verified") is False
        and witness.get("historical_family_counts") == {**inactive, **inert}
        and "inert_rejection_family_counts" not in witness
        and witness.get("candidate_binary_counts")
        == {"image": exact_binary_counts, "vmlinux": exact_binary_counts}
        and isinstance(witness.get("candidate_config_counts"), dict)
        and witness["candidate_config_counts"]
        and all(value == 1 for value in witness["candidate_config_counts"].values())
        and isinstance(witness.get("historical_config_enable_counts"), dict)
        and all(
            value == 0
            for value in witness["historical_config_enable_counts"].values()
        )
        and witness.get("exact_stock_image_size") is True
        and witness.get("fits_fixed_ramdisk_layout") is True
        and witness.get("preserves_fixed_ramdisk_start") is True
        and witness.get("image_proof_count") == 1
        and witness.get("vmlinux_proof_count") == 1
        and witness.get("image_proof_family_count") == 1
        and witness.get("vmlinux_proof_family_count") == 1
        and witness.get("config_enable_count") == 1
        and witness.get("fips_enable_count") == 1
    )
    if legacy_false_negative:
        return "legacy-inert-literal-false-negative-requalified"
    raise CheckError("P2.34 build wrapper did not pass an accepted result class")


def _verify_final_candidate_output(
    directory: Path, exact_contract: dict[str, Any]
) -> dict[str, Any]:
    image = candidate_contract.stable_read(
        directory / "Image", "P2.34 Image", ARTIFACT_LIMITS["Image"]
    )
    vmlinux = candidate_contract.stable_read(
        directory / "vmlinux", "P2.34 vmlinux", ARTIFACT_LIMITS["vmlinux"]
    )
    config = candidate_contract.stable_read(
        directory / ".config", "P2.34 .config", ARTIFACT_LIMITS[".config"]
    ).decode("utf-8").splitlines()
    run_id = exact_contract["run_id"].encode("ascii")
    unsat_tag = exact_contract["unsat_tag_hex"].encode("ascii")
    profile = exact_contract["profile"]
    source_check_run_id = build.candidate_contract.intent.source_check_run_id(
        profile, exact_contract.get("source_contract_id")
    )
    expected_counts = {
        "long_family": 1,
        "unsat_family": 1,
        "request_magic": 1,
        "run_id_hex": 1,
        "unsat_tag_hex": 1,
        "model_run_id": 0,
        "source_check_run_id": 0,
    }
    binary_counts = {}
    for name, data in (("image", image), ("vmlinux", vmlinux)):
        row = {
            "long_family": data.count(build.LONG_FAMILY),
            "unsat_family": data.count(build.UNSAT_FAMILY),
            "request_magic": data.count(build.REQUEST_MAGIC),
            "run_id_hex": data.count(run_id),
            "unsat_tag_hex": data.count(unsat_tag),
            "model_run_id": data.count(
                build.candidate_contract.intent.decoder.model.model_run_id(
                    profile
                ).hex().encode("ascii")
            ),
            "source_check_run_id": data.count(
                source_check_run_id.hex().encode("ascii")
            ),
        }
        if row != expected_counts:
            raise CheckError(f"P2.34 final candidate identity mismatch: {name}")
        binary_counts[name] = row
    inactive_counts = {
        family.decode("ascii"): {
            "image": image.count(family),
            "vmlinux": vmlinux.count(family),
        }
        for family in build.HISTORICAL_FAMILIES
    }
    inert_counts = {
        family.decode("ascii"): {
            "image": image.count(family),
            "vmlinux": vmlinux.count(family),
        }
        for family in build.INERT_REJECTION_FAMILIES
    }
    random_private_path_counts = {
        name: data.count(RANDOM_PRIVATE_PATH_PREFIX)
        for name, data in (("image", image), ("vmlinux", vmlinux))
    }
    if any(row != {"image": 0, "vmlinux": 0} for row in inactive_counts.values()):
        raise CheckError("P2.34 final output contains an active retired family")
    if any(row != {"image": 1, "vmlinux": 1} for row in inert_counts.values()):
        raise CheckError("P2.34 inert rejection-family cardinality mismatch")
    if any(random_private_path_counts.values()):
        raise CheckError("P2.34 output leaks a random private build path")
    if any(config.count(line) != 1 for line in exact_contract["config_lines"]):
        raise CheckError("P2.34 final output config identity mismatch")
    if any(config.count(f"{name}=y") for name in build.HISTORICAL_CONFIGS):
        raise CheckError("P2.34 final output enables a retired witness config")
    if config.count("CONFIG_CRYPTO_FIPS=y") != 1:
        raise CheckError("P2.34 final output FIPS config cardinality mismatch")
    stock_size = build.engine.engine.STOCK_IMAGE_SIZE
    capacity = build.engine.engine.FIXED_KERNEL_SLOT_CAPACITY
    if len(image) != stock_size or (len(image) + 4095) & ~4095 != capacity:
        raise CheckError("P2.34 final Image violates the fixed ramdisk boundary")
    return {
        "binary_counts": binary_counts,
        "inactive_retired_family_counts": inactive_counts,
        "inert_rejection_family_counts": inert_counts,
        "random_private_path_counts": random_private_path_counts,
        "random_private_path_absent": True,
        "image_size": len(image),
        "fixed_kernel_slot_capacity": capacity,
        "verified": True,
    }


def verify_bundle(
    directory: Path, exact_contract: dict[str, Any]
) -> dict[str, Any]:
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError(f"build artifact directory missing or indirect: {directory}")
    expected = set(ARTIFACT_LIMITS)
    observed = {path.name for path in directory.iterdir()}
    if observed != expected:
        raise CheckError(
            f"build artifact directory inventory mismatch: {sorted(observed)}"
        )
    result, result_receipt = _load_result(directory / "build-result.json")
    for name, expected_value in {
        "schema": build.SCHEMA,
        "target": TARGET,
        "mode": "build",
        "build_command_returncode": 0,
    }.items():
        if result.get(name) != expected_value:
            raise CheckError(f"P2.34 build result mismatch: {name}")
    wrapper_result_class = _classify_wrapper_result(result)
    if result.get("p234_candidate_contract") != exact_contract:
        raise CheckError("P2.34 build does not embed the exact candidate contract")
    source_delta = result.get("source_delta")
    if (
        not isinstance(source_delta, dict)
        or source_delta.get("patch_sha256") != exact_contract["patch"]["sha256"]
        or source_delta.get("restored") is not True
        or source_delta.get("verified") is not True
    ):
        raise CheckError("P2.34 source patch/restoration contract mismatch")
    if _source_delta_hashes(source_delta.get("before"), "before") != exact_contract[
        "base_files"
    ] or _source_delta_hashes(source_delta.get("after"), "after") != exact_contract[
        "patched_files"
    ]:
        raise CheckError("P2.34 source patch/restoration hash mismatch")
    for name in REQUIRED_GATES:
        gate = result.get(name)
        if (
            name == "witness_output_gate"
            and wrapper_result_class
            == "legacy-inert-literal-false-negative-requalified"
        ):
            continue
        if not isinstance(gate, dict) or gate.get("verified") is not True:
            raise CheckError(f"P2.34 build gate not verified: {name}")
    safety = result.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(name) is not expected_value
        for name, expected_value in {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "packaging_outputs_promoted": False,
        }.items()
    ):
        raise CheckError("P2.34 build safety contract mismatch")

    output_rows = _output_rows(result)
    receipts = {"build-result.json": result_receipt}
    for name in sorted(set(ARTIFACT_LIMITS) - {"build-result.json"}):
        artifact = directory / name
        receipt = stable_receipt(artifact, f"P2.34 {name}", ARTIFACT_LIMITS[name])
        row = output_rows[name]
        if any(row.get(field) != receipt[field] for field in ("size", "sha256")):
            raise CheckError(f"P2.34 build receipt mismatch: {name}")
        receipts[name] = receipt
    config_data = candidate_contract.stable_read(
        directory / ".config", "P2.34 .config", ARTIFACT_LIMITS[".config"]
    )
    try:
        config_lines = config_data.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise CheckError("P2.34 compiled config is not UTF-8") from exc
    if any(config_lines.count(line) != 1 for line in exact_contract["config_lines"]):
        raise CheckError("P2.34 compiled candidate config binding mismatch")
    if any(
        config_lines.count(f"{name}=y") != 0 for name in build.HISTORICAL_CONFIGS
    ):
        raise CheckError("P2.34 compiled config enables a retired witness")
    final_candidate_output_gate = _verify_final_candidate_output(
        directory, exact_contract
    )
    return {
        "directory": str(directory),
        "wrapper_result_class": wrapper_result_class,
        "build_result": result_receipt,
        "artifacts": receipts,
        "final_candidate_output_gate": final_candidate_output_gate,
        "run_id": exact_contract["run_id"],
        "verified": True,
    }


def _run(command: list[str], label: str) -> str:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise CheckError(f"{label} failed: {completed.stdout[-2000:]}")
    return completed.stdout


def _symbol_ranges(symbols: str) -> dict[str, tuple[int, int]]:
    entries: list[tuple[int, str]] = []
    for line in symbols.splitlines():
        match = re.match(r"^([0-9a-fA-F]+)\s+\S\s+(\S+)$", line)
        if match:
            entries.append((int(match.group(1), 16), match.group(2)))
    addresses = sorted({address for address, _name in entries})
    following = dict(zip(addresses, addresses[1:]))
    return {
        name: (address, following[address])
        for address, name in entries
        if address in following
    }


def _disassemble(
    objdump: Path,
    vmlinux: Path,
    ranges: dict[str, tuple[int, int]],
    symbol: str,
) -> str:
    if symbol not in ranges:
        raise CheckError(f"required linked symbol missing: {symbol}")
    start, stop = ranges[symbol]
    return _run(
        [
            str(objdump),
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(vmlinux),
        ],
        f"objdump {symbol}",
    )


def _calls(disassembly: str) -> list[str]:
    result: list[str] = []
    for target in re.findall(r"\bbl\s+(?:0x)?[0-9a-fA-F]+\s+<([^>]+)>", disassembly):
        name = target.split("+", 1)[0]
        if name.startswith("__pi_"):
            name = name[5:]
        if name == "__memcpy":
            name = "memcpy"
        result.append(name)
    return result


def _dump_symbol_bytes(
    objdump: Path,
    vmlinux: Path,
    ranges: dict[str, tuple[int, int]],
    symbol: str,
    size: int,
) -> bytes:
    if symbol not in ranges:
        raise CheckError(f"required linked data symbol missing: {symbol}")
    start = ranges[symbol][0]
    text = _run(
        [
            str(objdump),
            "-s",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{start + size:x}",
            str(vmlinux),
        ],
        f"objdump data {symbol}",
    )
    addressed: dict[int, int] = {}
    for line in text.splitlines():
        match = re.match(
            r"^\s*([0-9a-fA-F]+)\s+(.+)$", line
        )
        if match is None:
            continue
        cursor = int(match.group(1), 16)
        hex_columns = re.split(r"\s{2,}", match.group(2), maxsplit=1)[0]
        for token in hex_columns.split():
            if (
                re.fullmatch(r"[0-9a-fA-F]{2,8}", token) is None
                or len(token) % 2
            ):
                break
            for value in bytes.fromhex(token):
                addressed[cursor] = value
                cursor += 1
    try:
        return bytes(addressed[start + offset] for offset in range(size))
    except KeyError as exc:
        raise CheckError(
            f"linked data symbol dump is short: {symbol}"
        ) from exc


def _subsequence(actual: list[str], expected: tuple[str, ...], label: str) -> None:
    cursor = 0
    for name in actual:
        if cursor < len(expected) and name == expected[cursor]:
            cursor += 1
    if cursor != len(expected):
        raise CheckError(
            f"{label} linked call order mismatch: expected={expected} actual={actual}"
        )


def audit_linked(
    vmlinux: Path,
    nm: Path,
    objdump: Path,
    expected_vmlinux: dict[str, Any],
    source_contract_id: str | None = None,
) -> dict[str, Any]:
    captured = {
        "vmlinux": candidate_contract.stable_read(
            vmlinux, "P2.34 linked vmlinux", ARTIFACT_LIMITS["vmlinux"]
        ),
        "nm": candidate_contract.stable_read(nm, "P2.34 nm", 16 * 1024 * 1024),
        "objdump": candidate_contract.stable_read(
            objdump, "P2.34 objdump", 16 * 1024 * 1024
        ),
    }
    captured_receipts = {
        name: candidate_contract.intent.receipt(data)
        for name, data in captured.items()
    }
    if captured_receipts["vmlinux"] != expected_vmlinux:
        raise CheckError("P2.34 linked audit vmlinux changed after build hashing")
    linked_contract_audit = None
    linked_validator_audit = None
    selected_contract_module = None
    with tempfile.TemporaryDirectory(prefix="s22-p234-linked-") as temporary:
        staged = {}
        for name, data in captured.items():
            path = Path(temporary) / name
            path.write_bytes(data)
            path.chmod(0o700 if name in {"nm", "objdump"} else 0o600)
            staged[name] = path
        ranges = _symbol_ranges(
            _run([str(staged["nm"]), "-n", str(staged["vmlinux"])], "nm")
        )
        disassembly = {
            symbol: _disassemble(
                staged["objdump"], staged["vmlinux"], ranges, symbol
            )
            for symbol in REQUIRED_SYMBOLS
        }
        if source_contract_id is not None:
            selected = candidate_contract.intent.selected_source_contract(
                source_contract_id, "E2"
            )
            selected_contract_module = selected.module
            if hasattr(selected.module, "linked_table_bytes"):
                expected_tables = selected.module.linked_table_bytes()
                actual_tables = {
                    symbol: _dump_symbol_bytes(
                        staged["objdump"],
                        staged["vmlinux"],
                        ranges,
                        symbol,
                        len(expected),
                    )
                    for symbol, expected in expected_tables.items()
                }
                try:
                    linked_contract_audit = (
                        selected.module.audit_linked_tables(actual_tables)
                    )
                except selected.module.SourceContractError as exc:
                    raise CheckError(str(exc)) from exc
            for symbol in getattr(
                selected.module, "LINKED_VALIDATOR_SYMBOLS", ()
            ):
                disassembly[symbol] = _disassemble(
                    staged["objdump"], staged["vmlinux"], ranges, symbol
                )
    calls = {symbol: _calls(text) for symbol, text in disassembly.items()}
    if (
        selected_contract_module is not None
        and hasattr(selected_contract_module, "audit_linked_validator")
    ):
        try:
            linked_validator_audit = (
                selected_contract_module.audit_linked_validator(
                    disassembly,
                    calls,
                    {
                        symbol: ranges[symbol][0]
                        for symbol in selected_contract_module.linked_table_bytes()
                    },
                )
            )
        except selected_contract_module.SourceContractError as exc:
            raise CheckError(str(exc)) from exc
    _subsequence(
        calls["kernel_init"],
        (
            "run_init_process",
            "strcmp",
            "s22_fyg8_e1_head",
            "__flush_dcache_area",
            "crc32_le",
            "s22_fyg8_e1_record_families_allowed",
            "__flush_dcache_area",
        ),
        "kernel entry hook",
    )
    _subsequence(
        calls["s22_fyg8_e1_write"],
        (
            "_copy_from_user",
            "crc32_le",
            "s22_fyg8_e1_head",
            "crc32_le",
            "s22_fyg8_e1_record_families_allowed",
            "__flush_dcache_area",
        ),
        "proc write",
    )
    flush_calls = {
        "kernel_init": calls["kernel_init"].count("__flush_dcache_area"),
        "proc_write": calls["s22_fyg8_e1_write"].count("__flush_dcache_area"),
    }
    if flush_calls != {"kernel_init": 2, "proc_write": 3}:
        raise CheckError(f"retained flush cardinality mismatch: {flush_calls}")
    flush = disassembly["__pi___flush_dcache_area"]
    if not re.search(r"\bdc\s+civac\b", flush) or not re.search(r"\bdsb\s+sy\b", flush):
        raise CheckError("linked cache flush helper lacks dc civac plus dsb sy")
    result = {
        "required_symbols": list(REQUIRED_SYMBOLS),
        "call_chains": calls,
        "retained_flush_calls": flush_calls,
        "full_lto_inlined_helpers": [
            "s22_fyg8_e1_record_entry",
            "s22_fyg8_e1_request_allowed",
            "s22_fyg8_e1_slot_crc",
            "s22_fyg8_e1_store",
        ],
        "flush_helper_dc_civac_dsb_sy": True,
        "staged_input_receipts": captured_receipts,
        "verified": True,
    }
    if linked_contract_audit is not None:
        result["source_contract_semantics"] = linked_contract_audit
    if linked_validator_audit is not None:
        result["source_contract_validator"] = linked_validator_audit
    return result


def check(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    exact_contract = candidate_contract.verify(
        root,
        resolve(root, args.source),
        resolve(root, args.intent),
        resolve(root, args.patch),
    )
    directory_a = resolve(root, args.build_a)
    directory_b = resolve(root, args.build_b)
    if directory_a.resolve() == directory_b.resolve():
        raise CheckError("P2.34 reproducibility inputs must be distinct directories")
    build_a = verify_bundle(directory_a, exact_contract)
    build_b = verify_bundle(directory_b, exact_contract)
    compared = {}
    for name in sorted(set(ARTIFACT_LIMITS) - {"build-result.json"}):
        equal = build_a["artifacts"][name] == build_b["artifacts"][name]
        compared[name] = equal
        if not equal:
            raise CheckError(f"P2.34 clean build reproducibility mismatch: {name}")
    linked = audit_linked(
        directory_a / "vmlinux",
        resolve(root, args.nm),
        resolve(root, args.objdump),
        build_a["artifacts"]["vmlinux"],
        exact_contract.get("source_contract_id"),
    )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact_contract,
        "build_a": build_a,
        "build_b": build_b,
        "byte_identical_artifacts": compared,
        "linked_audit": linked,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-a", type=Path, default=DEFAULT_BUILD_A)
    parser.add_argument("--build-b", type=Path, default=DEFAULT_BUILD_B)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--nm", type=Path, default=DEFAULT_NM)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = check(parse_args(argv))
    except (
        CheckError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
