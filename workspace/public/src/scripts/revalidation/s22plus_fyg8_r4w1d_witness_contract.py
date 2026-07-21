#!/usr/bin/env python3
"""Validate the host-only FYG8 R4W1-D compact retained PID1 witness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_r4w1b_patch_check as shared  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1d_witness_contract_v1"
TARGET = shared.TARGET
VERDICT = "PASS_R4W1D_COMPACT_WITNESS_HOST_CONTRACT"
CONFIG = "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS"
MARKER_PREIMAGE = (
    "S22PLUS_FYG8_R4W1D_CONTIGUOUS_DIRECT_PID1_EXEC_ACCEPTED|SM-S906N|g0q|"
    "S906NKSS7FYG8|"
    "base-main=7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a|"
    "carrier-boot=fc10d94eb0e41a97b40d657e320f8f815870a41b7a6b6df0bc7a51b540a2fe57|"
    "carrier-init=6bf7c60ca8f9b9561a9d38f0591028b23291595dd224853015807993ce97703d|"
    "semantics=kernel_execve(/init)==0&&task_pid_nr(current)==1|"
    "layout=saturated-ring-pre-cursor-contiguous-backfill-no-index-mutation"
)
MARKER_PREIMAGE_SHA256 = (
    "0e13f28e8558dde01ce3345f164086739be4972b2a01e0e0a9ac474dbd195407"
)
MARKER_ID = MARKER_PREIMAGE_SHA256[:32]
PROOF = f"\n[[S22P1D|{MARKER_ID}]]\n"
PROOF_FAMILY = "[[S22P1D|"
PATCH_SHA256 = "5ad4ad05a290eee74f82bc58822a637ed8e41a830e62241b5e3bd9dc9b95b75a"
BASE_FILES = shared.BASE_FILES
PATCHED_FILES = {
    "kernel_platform/common/init/main.c": (
        "2ac26a8f53d34f9a70d8d287964b78f16c2c0911d86b4cfc3cfdae76e029cf4d"
    ),
    "kernel_platform/common/init/Kconfig": (
        "05905ad7baee5621fef1bf795fbd84f57433692e7b4083f9000f06acfb03389e"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "4e4a8248c47169c1e8a6cc6255f50cf3c78f45f89cb24b55e619d423d03f450d"
    ),
}
DEFAULT_SOURCE = shared.DEFAULT_SOURCE
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_r4w1d_compact_pid1_witness.patch"
)
DEFAULT_INHERITED_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_clean_repro_20260719/"
    "preflight-v6/preflight.json"
)
INHERITED_RESULT_SHA256 = (
    "05da65ef4edfcfc06939f6fc26e6b3c75793615af3e67c9540e5b14463fb3202"
)
DEFAULT_CARRIER_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i/carrier.boot.img"
)
DEFAULT_CARRIER_INIT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i/build/s22plus_init_r4w1c_wdt_carrier"
)
CARRIER_BOOT_SHA256 = (
    "fc10d94eb0e41a97b40d657e320f8f815870a41b7a6b6df0bc7a51b540a2fe57"
)
CARRIER_BOOT_SIZE = 100_663_296
CARRIER_INIT_SHA256 = (
    "6bf7c60ca8f9b9561a9d38f0591028b23291595dd224853015807993ce97703d"
)
CARRIER_INIT_SIZE = 65_984


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    return shared.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return shared.resolve(root, path)


def sha256_file(path: Path) -> str:
    return shared.sha256_file(path)


def _added_patch_lines(patch_text: str) -> list[str]:
    return [
        line[1:]
        for line in patch_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def check_patch_policy(patch: Path) -> dict[str, Any]:
    if patch.is_symlink() or not patch.is_file():
        raise CheckError("R4W1-D patch missing or indirect")
    actual_sha = sha256_file(patch)
    if actual_sha != PATCH_SHA256:
        raise CheckError(f"R4W1-D patch SHA256 mismatch: {actual_sha}")
    text = patch.read_text(encoding="ascii")
    targets = re.findall(r"^\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
    if set(targets) != set(BASE_FILES) or len(targets) != len(BASE_FILES):
        raise CheckError(f"unexpected R4W1-D patch targets: {targets}")
    added = _added_patch_lines(text)
    added_text = "\n".join(added)
    symbols = {
        symbol
        for line in added
        for symbol in re.findall(r"CONFIG_[A-Z0-9_]+", line)
    }
    if symbols != {CONFIG}:
        raise CheckError(f"unexpected R4W1-D config symbols: {sorted(symbols)}")
    forbidden = (
        "panic(",
        "emergency_restart",
        "kernel_restart",
        "reboot(",
        "filp_open",
        "kernel_write",
        "blkdev_get",
        "submit_bio",
        "ioremap(",
        "flush_cache",
    )
    hits = [token for token in forbidden if token in added_text]
    if hits:
        raise CheckError(f"forbidden R4W1-D operations: {hits}")
    derived = hashlib.sha256(MARKER_PREIMAGE.encode("ascii")).hexdigest()
    if derived != MARKER_PREIMAGE_SHA256 or derived[:32] != MARKER_ID:
        raise CheckError("R4W1-D marker derivation mismatch")
    preimage_bindings = (
        f"base-main={BASE_FILES['kernel_platform/common/init/main.c']}|",
        f"carrier-boot={CARRIER_BOOT_SHA256}|",
        f"carrier-init={CARRIER_INIT_SHA256}|",
        "semantics=kernel_execve(/init)==0&&task_pid_nr(current)==1|",
        "layout=saturated-ring-pre-cursor-contiguous-backfill-no-index-mutation",
    )
    if any(binding not in MARKER_PREIMAGE for binding in preimage_bindings):
        raise CheckError("R4W1-D marker preimage is not bound to checked inputs")
    required = (
        PROOF.strip(),
        CONFIG,
        "s22plus_fyg8_backfill_proof",
        "idx < payload_size",
        "payload_size - proof_size",
    )
    missing = [token for token in required if token not in added_text]
    if missing:
        raise CheckError(f"R4W1-D patch tokens missing: {missing}")
    historical = (
        "[[S22R4W1B|",
        "[[S22R4W1|",
        "[[S22R4W1D|",
        "RAMDISK_EXEC_ACCEPTED",
    )
    leaked = [token for token in historical if token in added_text]
    if leaked:
        raise CheckError(f"historical witness leaked into R4W1-D: {leaked}")
    return {
        "path": str(patch),
        "sha256": actual_sha,
        "targets": targets,
        "added_config_symbols": sorted(symbols),
        "forbidden_hits": hits,
        "marker_preimage_sha256": derived,
        "marker_id": MARKER_ID,
        "verified": True,
    }


def apply_patch_to_minimal_tree(source: Path, patch: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1d-check-") as temp_name:
        temp = Path(temp_name)
        for relative in BASE_FILES:
            src = source / relative
            dst = temp / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o644)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=temp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise CheckError(f"R4W1-D patch application failed: {completed.stdout[-2000:]}")
        actual = {
            relative: sha256_file(temp / relative) for relative in BASE_FILES
        }
        if actual != PATCHED_FILES:
            raise CheckError(f"R4W1-D patched file SHA256 mismatch: {actual}")
        return {
            relative: (temp / relative).read_text(encoding="utf-8")
            for relative in BASE_FILES
        }


def check_patched_sources(patched: dict[str, str]) -> dict[str, Any]:
    main = patched["kernel_platform/common/init/main.c"]
    kconfig = patched["kernel_platform/common/init/Kconfig"]
    defconfig = patched[
        "kernel_platform/common/arch/arm64/configs/gki_defconfig"
    ]
    if len(PROOF.encode("ascii")) != 45:
        raise CheckError("R4W1-D proof length contract changed")
    exact_counts = {
        "marker_id": main.count(MARKER_ID),
        "proof": main.count(PROOF.strip()),
        "backfill_definition": main.count(
            "static bool s22plus_fyg8_backfill_proof("
        ),
        "backfill_calls": main.count("s22plus_fyg8_backfill_proof(head,"),
        "record_definition": main.count(
            "static void s22plus_fyg8_record_init_exec(const char *init_filename)"
        ),
        "record_call": main.count(
            "s22plus_fyg8_record_init_exec(ramdisk_execute_command);"
        ),
        "publish_barrier": main.count("smp_wmb();"),
        "index_publish": main.count("WRITE_ONCE(head->idx"),
    }
    expected_counts = {
        "marker_id": 1,
        "proof": 1,
        "backfill_definition": 1,
        "backfill_calls": 1,
        "record_definition": 1,
        "record_call": 1,
        "publish_barrier": 1,
        "index_publish": 0,
    }
    if exact_counts != expected_counts:
        raise CheckError(f"R4W1-D source cardinality mismatch: {exact_counts}")
    required_main = (
        f"0x{shared.LOG_BASE:x}ULL",
        f"0x{shared.LOG_SIZE:x}U",
        f"0x{shared.LOG_MAGIC:08x}U",
        'strcmp(init_filename, "/init")',
        "task_pid_nr(current) != 1",
        "READ_ONCE(head->magic) != S22PLUS_FYG8_LOG_MAGIC",
        "idx < payload_size || proof_size > payload_size",
        "pos = idx % payload_size;",
        "proof_pos = pos >= proof_size ? pos - proof_size :",
        "payload_size - proof_size;",
        "memcpy(&head->buf[proof_pos], proof, proof_size);",
    )
    missing_main = [token for token in required_main if token not in main]
    if missing_main:
        raise CheckError(f"R4W1-D main.c tokens missing: {missing_main}")
    helper_start = main.index("static bool s22plus_fyg8_backfill_proof(")
    helper_end = main.index("static void s22plus_fyg8_record_init_exec(")
    helper = main[helper_start:helper_end]
    expected_helper = (
        "static bool s22plus_fyg8_backfill_proof(struct s22plus_fyg8_log_head *head,\n"
        "\t\tsize_t payload_size, const char *proof, size_t proof_size)\n"
        "{\n"
        "\tu32 idx;\n"
        "\tsize_t pos;\n"
        "\tsize_t proof_pos;\n\n"
        "\tidx = READ_ONCE(head->idx);\n"
        "\tif (idx < payload_size || proof_size > payload_size)\n"
        "\t\treturn false;\n\n"
        "\tpos = idx % payload_size;\n"
        "\tproof_pos = pos >= proof_size ? pos - proof_size :\n"
        "\t\tpayload_size - proof_size;\n"
        "\tmemcpy(&head->buf[proof_pos], proof, proof_size);\n"
        "\tsmp_wmb();\n"
        "\treturn true;\n"
        "}\n\n"
    )
    if helper != expected_helper:
        raise CheckError("R4W1-D backfill helper semantics changed")
    exact_guard = (
        "\tif (strcmp(init_filename, \"/init\") || task_pid_nr(current) != 1)\n"
        "\t\treturn;"
    )
    proof_call = (
        "\tif (!s22plus_fyg8_backfill_proof(head, payload_size, proof,\n"
        "\t\t\tsizeof(proof) - 1)) {\n"
        "\t\tpr_warn(\"S22R4W1D retained witness refused unsaturated log ring\\n\");\n"
        "\t\treturn;\n"
        "\t}"
    )
    if main.count(exact_guard) != 1 or main.count(proof_call) != 1:
        raise CheckError("R4W1-D exact exec guard or proof call changed")
    success_edge = (
        "\tif (ramdisk_execute_command) {\n"
        "\t\tret = run_init_process(ramdisk_execute_command);\n"
        "\t\tif (!ret) {\n"
        "\t\t\ts22plus_fyg8_record_init_exec(ramdisk_execute_command);\n"
        "#ifdef CONFIG_RKP\n"
    )
    if main.count(success_edge) != 1:
        raise CheckError("R4W1-D witness is not on the unique exec-success edge")
    if kconfig.count("config S22PLUS_FYG8_COMPACT_RETAINED_WITNESS") != 1:
        raise CheckError("R4W1-D Kconfig definition mismatch")
    if defconfig.count(f"{CONFIG}=y") != 1:
        raise CheckError("R4W1-D defconfig enable mismatch")
    return {
        "proof": PROOF.strip(),
        "proof_size": len(PROOF.encode("ascii")),
        "proof_family": PROOF_FAMILY,
        "exact_counts": exact_counts,
        "exec_success_edge_count": main.count(success_edge),
        "requires_saturated_ring": True,
        "contiguous_pre_cursor_backfill": True,
        "preexisting_log_bytes_overwritten": len(PROOF.encode("ascii")),
        "index_mutated": False,
        "patched_files": PATCHED_FILES,
        "verified": True,
    }


def backfill_proof(payload: bytes, index: int, proof: bytes) -> tuple[bytes, int]:
    """Model the checked contiguous pre-cursor proof placement."""

    if (
        not payload
        or index < len(payload)
        or index > 0xFFFFFFFF
        or not proof
        or len(proof) > len(payload)
    ):
        raise CheckError("invalid R4W1-D ring model input")
    updated = bytearray(payload)
    position = index % len(updated)
    proof_position = (
        position - len(proof)
        if position >= len(proof)
        else len(updated) - len(proof)
    )
    updated[proof_position : proof_position + len(proof)] = proof
    return bytes(updated), proof_position


def check_inherited_layout(result_path: Path) -> dict[str, Any]:
    if result_path.is_symlink() or not result_path.is_file():
        raise CheckError("R4W1-B inherited layout result missing or indirect")
    actual_sha = sha256_file(result_path)
    if actual_sha != INHERITED_RESULT_SHA256:
        raise CheckError(f"R4W1-B inherited result SHA256 mismatch: {actual_sha}")
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("R4W1-B inherited result is unreadable") from exc
    contract = data.get("r4w1b_patch_contract")
    if not isinstance(contract, dict) or (
        contract.get("schema") != shared.SCHEMA
        or contract.get("target") != TARGET
        or contract.get("verdict") != shared.VERDICT
    ):
        raise CheckError("R4W1-B inherited result identity mismatch")
    dt = contract.get("dt_contract")
    vendor = contract.get("vendor_abi")
    revisions = dt.get("revisions") if isinstance(dt, dict) else None
    if (
        not isinstance(dt, dict)
        or dt.get("base") != f"0x{shared.LOG_BASE:x}"
        or dt.get("size") != shared.LOG_SIZE
        or dt.get("verified") is not True
        or not isinstance(revisions, list)
        or [row.get("revision") for row in revisions]
        != list(shared.EXPECTED_REVISIONS)
        or any(row.get("verified") is not True for row in revisions)
        or not isinstance(vendor, dict)
        or vendor.get("verified") is not True
        or vendor.get("missing") != {}
    ):
        raise CheckError("R4W1-B inherited DT/vendor contract mismatch")
    return {
        "path": str(result_path),
        "sha256": actual_sha,
        "dt_base": dt["base"],
        "dt_size": dt["size"],
        "dt_revisions": [row["revision"] for row in revisions],
        "vendor_files": vendor.get("files"),
        "verified": True,
    }


def check_pinned_artifact(
    path: Path, *, expected_size: int, expected_sha256: str, label: str
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"R4W1-D {label} missing or indirect")
    before = path.stat()
    actual_sha256 = sha256_file(path)
    after = path.stat()
    stable = (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
    )
    result = {
        "path": str(path),
        "size": after.st_size,
        "sha256": actual_sha256,
        "stable_during_read": stable,
    }
    result["verified"] = (
        stable
        and after.st_size == expected_size
        and actual_sha256 == expected_sha256
    )
    if not result["verified"]:
        raise CheckError(f"R4W1-D {label} identity mismatch: {result}")
    return result


def check_current_layout(source: Path) -> dict[str, Any]:
    try:
        dt = shared.check_dt_contract(source)
        vendor = shared.check_vendor_abi(source)
    except (OSError, UnicodeError, shared.CheckError) as exc:
        raise CheckError("R4W1-D current source DT/vendor lineage is incomplete") from exc
    if dt.get("verified") is not True or vendor.get("verified") is not True:
        raise CheckError("R4W1-D current source DT/vendor lineage mismatch")
    return {"dt_contract": dt, "vendor_abi": vendor, "verified": True}


def run_check(
    source: Path,
    patch: Path,
    inherited_result: Path | None = None,
    carrier_boot: Path | None = None,
    carrier_init: Path | None = None,
) -> dict[str, Any]:
    if inherited_result is None:
        inherited_result = resolve(repo_root(), DEFAULT_INHERITED_RESULT)
    if carrier_boot is None:
        carrier_boot = resolve(repo_root(), DEFAULT_CARRIER_BOOT)
    if carrier_init is None:
        carrier_init = resolve(repo_root(), DEFAULT_CARRIER_INIT)
    base = shared.check_base_files(source)
    patch_policy = check_patch_policy(patch)
    patched = apply_patch_to_minimal_tree(source, patch)
    patched_contract = check_patched_sources(patched)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "base": base,
        "patch": patch_policy,
        "patched_contract": patched_contract,
        "carrier_artifacts": {
            "boot": check_pinned_artifact(
                carrier_boot,
                expected_size=CARRIER_BOOT_SIZE,
                expected_sha256=CARRIER_BOOT_SHA256,
                label="carrier boot",
            ),
            "init": check_pinned_artifact(
                carrier_init,
                expected_size=CARRIER_INIT_SIZE,
                expected_sha256=CARRIER_INIT_SHA256,
                label="carrier init",
            ),
            "verified": True,
        },
        "inherited_layout_contract": check_inherited_layout(inherited_result),
        "current_source_layout_contract": check_current_layout(source),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_created": False,
            "flash": False,
            "live_authorized": False,
            "security_config_changed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument(
        "--inherited-result", type=Path, default=DEFAULT_INHERITED_RESULT
    )
    parser.add_argument("--carrier-boot", type=Path, default=DEFAULT_CARRIER_BOOT)
    parser.add_argument("--carrier-init", type=Path, default=DEFAULT_CARRIER_INIT)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    result = run_check(
        resolve(root, args.source),
        resolve(root, args.patch),
        resolve(root, args.inherited_result),
        resolve(root, args.carrier_boot),
        resolve(root, args.carrier_init),
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(json.dumps({"verdict": "BLOCKED_R4W1D_HOST_CONTRACT", "error": str(exc)}))
        raise SystemExit(2) from exc
