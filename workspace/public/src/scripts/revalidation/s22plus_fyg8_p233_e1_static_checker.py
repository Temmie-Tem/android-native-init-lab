#!/usr/bin/env python3
"""Statically validate the source-only P2.33 compact E1 implementation."""

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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p232_e1_latest_stage_design as model  # noqa: E402
import s22plus_fyg8_p233_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_r4w1e_e1_host_contract as legacy_e1  # noqa: E402


SCHEMA = "s22plus_fyg8_p233_e1_static_checker_v1"
VERDICT = "PASS_P233_E1_SOURCE_IMPLEMENTATION_HOST_ONLY"
TARGET = model.TARGET
SOURCE_CHECK_RUN_IDS = {
    profile: hashlib.sha256(
        f"S22PLUS-FYG8-P233-SOURCE-CHECK:{profile}".encode("ascii")
    ).digest()[: model.RUN_ID_SIZE]
    for profile in model.PROFILE_NUMBERS
}

DEFAULT_SOURCE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_p233_e1_latest_stage.patch"
)
DEFAULT_CLIENT = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p233_checkpoint.c"
)
DEFAULT_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p233_e1_runtime.c"
)
DEFAULT_LEGACY_RUNTIME = legacy_e1.DEFAULT_RUNTIME
DEFAULT_HEADER = legacy_e1.DEFAULT_HEADER
DEFAULT_CHILD = legacy_e1.DEFAULT_CHILD

SOURCE_LIMIT = 2 * 1024 * 1024
PATCH_TARGETS = {
    "kernel_platform/common/init/Kconfig",
    "kernel_platform/common/init/main.c",
}


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    path = value if value.is_absolute() else root / value
    return Path(os.path.abspath(path))


def read_direct(path: Path, label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise CheckError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"{label} is not a direct regular file: {path}")
    if before.st_size <= 0 or before.st_size > SOURCE_LIMIT:
        raise CheckError(f"{label} size outside bound: {before.st_size}")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != before.st_size
    ):
        raise CheckError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def ascii_text(data: bytes, label: str) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CheckError(f"{label} is not ASCII") from exc


def run_checked(
    command: list[str], *, cwd: Path, label: str
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for key in legacy_e1.COMPILER_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment.update({"LANG": "C", "LC_ALL": "C", "SOURCE_DATE_EPOCH": "0"})
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).decode("utf-8", "replace")
        raise CheckError(f"{label} failed: {detail[-2000:]}")
    return result


def audit_patch(source: Path, patch_path: Path, patch_data: bytes) -> dict[str, Any]:
    text = ascii_text(patch_data, "P2.33 kernel patch")
    targets = set(re.findall(r"^diff --git a/(\S+) b/\1$", text, re.MULTILINE))
    if targets != PATCH_TARGETS:
        raise CheckError(f"P2.33 patch target set changed: {sorted(targets)}")
    run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=source,
        label="P2.33 clean-apply check",
    )

    required = (
        "config S22PLUS_FYG8_E1_LATEST_STAGE",
        "default n",
        "CONFIG_S22PLUS_FYG8_E1_PROFILE",
        "CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX",
        "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX",
        "#define S22_FYG8_E1_LONG_SIZE",
        "#define S22_FYG8_E1_SLOT_SIZE",
        "#define S22_FYG8_E1_REQUEST_VERSION",
        "S22PLUS-FYG8-P232-SLOT-V1",
        "__flush_dcache_area",
        "s22_fyg8_e1_header_matches",
        "s22_fyg8_e1_record_families_allowed",
        "s22_fyg8_e1_unsat_families_allowed",
        "s22_fyg8_e1_state.item_index, 0,",
        "s22_fyg8_e1_state.item_index = request.item_index;",
        "s22_fyg8_e1_record_entry(ramdisk_execute_command);",
        "proc_create(\"s22_checkpoint\", 0200",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"P2.33 patch contract missing: {missing}")
    exact_defines = {
        "S22_FYG8_E1_LONG_SIZE": "45U",
        "S22_FYG8_E1_HEADER_SIZE": "25U",
        "S22_FYG8_E1_SLOT_SIZE": "10U",
        "S22_FYG8_E1_UNSAT_SIZE": "24U",
        "S22_FYG8_E1_REQUEST_SIZE": "32U",
        "S22_FYG8_E1_REQUEST_VERSION": "2U",
    }
    for name, value in exact_defines.items():
        if re.search(rf"^\+#define {name}\s+{value}$", text, re.MULTILINE) is None:
            raise CheckError(f"P2.33 patch define mismatch: {name}")
    forbidden = (
        "kernel_restart(",
        "emergency_restart(",
        "panic(",
        "call_usermodehelper(",
        "head->idx =",
        "head->magic =",
        "head->boot_cnt =",
        "sec_log_buf.ko",
        "gki_defconfig",
        "struct s22_fyg8_e1_slot current;",
    )
    present = [token for token in forbidden if token in text]
    if present:
        raise CheckError(f"P2.33 patch contains forbidden behavior: {present}")
    if text.count("__flush_dcache_area") < 4:
        raise CheckError("P2.33 patch lacks required cache flush points")
    if text.count("s22_fyg8_e1_header_matches(head)") < 6:
        raise CheckError("P2.33 patch lacks repeated frozen-header checks")
    hook = "+\t\t\ts22_fyg8_e1_record_entry(ramdisk_execute_command);"
    hook_position = text.find(hook)
    hook_context = text[max(0, hook_position - 240) : hook_position]
    if (
        hook_position < 0
        or text.count(hook) != 1
        or "ret = run_init_process(ramdisk_execute_command);" not in hook_context
        or "if (!ret) {" not in hook_context
    ):
        raise CheckError("P2.33 entry hook is not dominated by successful exec")
    return {
        **receipt(patch_data),
        "targets": sorted(targets),
        "clean_apply": True,
        "default_disabled": True,
        "defconfig_untouched": True,
        "frozen_header_rechecks": text.count("s22_fyg8_e1_header_matches(head)"),
        "cache_flush_call_sites": text.count("__flush_dcache_area"),
        "verified": True,
    }


def audit_sources(
    client_data: bytes,
    runtime_data: bytes,
    legacy_runtime_data: bytes,
    header_data: bytes,
    child_data: bytes,
) -> dict[str, Any]:
    client = ascii_text(client_data, "P2.33 checkpoint client")
    runtime = ascii_text(runtime_data, "P2.33 E1 runtime")
    legacy_runtime = ascii_text(legacy_runtime_data, "pinned E1 runtime")

    pins = {
        "legacy_runtime": hashlib.sha256(legacy_runtime_data).hexdigest(),
        "header": hashlib.sha256(header_data).hexdigest(),
        "child": hashlib.sha256(child_data).hexdigest(),
    }
    expected = {
        "legacy_runtime": legacy_e1.EXPECTED_SOURCE_SHA256["runtime"],
        "header": legacy_e1.EXPECTED_SOURCE_SHA256["header"],
        "child": legacy_e1.EXPECTED_SOURCE_SHA256["child"],
    }
    if pins != expected:
        raise CheckError(f"pinned legacy E1 source changed: {pins}")

    required_client = (
        "S22_P233_REQUEST_VERSION 2U",
        "S22PLUS_FYG8_P233_PROFILE",
        "S22_P233_STAGE_E1A_SUCCESS 0x2fU",
        "S22_P233_STAGE_E1B_SUCCESS 0x3fU",
        "request.profile = S22PLUS_FYG8_P233_PROFILE;",
        "request.crc32 = checkpoint_crc32(",
        'sys_openat("/proc/s22_checkpoint"',
    )
    required_runtime = (
        '#include "s22plus_r4w1e_e1_runtime.c"',
        "S22PLUS_FYG8_P233_PROFILE == 1",
        "s22_p233_included_e1b_run();",
        "s22_r4w1e_checkpoint_success(&g_checkpoint)",
        "s22_p233_run();",
    )
    missing = [token for token in required_client if token not in client]
    missing += [token for token in required_runtime if token not in runtime]
    if missing:
        raise CheckError(f"P2.33 userspace source contract missing: {missing}")
    if "sec_log_buf.ko" in runtime + legacy_runtime + client:
        raise CheckError("P2.33 userspace references the forbidden log writer")

    e1a_block = runtime.split(
        "#if S22PLUS_FYG8_P233_PROFILE == 1", 1
    )[1].split("#else", 1)[0]
    expected_operations = (
        "mount_proc()",
        "mount_sys()",
        "mount_dev()",
        "mount_run()",
        "setup_and_verify_dev_null()",
        "child_start(&child)",
        "child_verify_token(&child)",
        "child_reap(&child)",
        "s22_r4w1e_checkpoint_success(&g_checkpoint)",
    )
    positions = [e1a_block.find(token) for token in expected_operations]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise CheckError("E1A terminal is not dominated by every required operation")

    legacy_positions = [
        legacy_runtime.find(operation)
        for _, _, operation in legacy_e1.E1_STEPS
    ]
    legacy_terminal = legacy_runtime.find(
        "s22_r4w1e_checkpoint_success(&g_checkpoint)"
    )
    if (
        any(position < 0 for position in legacy_positions)
        or legacy_positions != sorted(legacy_positions)
        or legacy_terminal <= legacy_positions[-1]
    ):
        raise CheckError("pinned E1B terminal dominance changed")
    if len(legacy_e1.MODULE_SPECS) != 5 or any(
        spec[0] == "sec_log_buf.ko" for spec in legacy_e1.MODULE_SPECS
    ):
        raise CheckError("E1B watchdog module closure changed")
    return {
        "client": receipt(client_data),
        "runtime_wrapper": receipt(runtime_data),
        "pinned_runtime": receipt(legacy_runtime_data),
        "pinned_header": receipt(header_data),
        "pinned_child": receipt(child_data),
        "e1a_operation_count": 8,
        "e1b_operation_count": len(legacy_e1.E1_STEPS),
        "watchdog_module_count": len(legacy_e1.MODULE_SPECS),
        "terminal_dominance_verified": True,
        "sec_log_buf_absent": True,
        "verified": True,
    }


def _run_id_define(run_id: bytes) -> str:
    return "{" + ",".join(f"0x{value:02x}" for value in run_id) + "}"


def compile_userspace(
    root: Path,
    client: Path,
    runtime: Path,
    child: Path,
) -> dict[str, Any]:
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    file_tool = shutil.which("file")
    nm_tool = shutil.which("aarch64-linux-gnu-nm")
    if not compiler or not file_tool or not nm_tool:
        raise CheckError("AArch64 compiler, file, or nm is unavailable")
    include_dir = root / "workspace/public/src/native-init"
    flags = list(legacy_e1.COMPILE_FLAGS)
    outputs: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="s22-p233-static-") as temporary:
        temp = Path(temporary)
        for profile in ("E1A", "E1B"):
            number = model.PROFILE_NUMBERS[profile]
            run_id = SOURCE_CHECK_RUN_IDS[profile]
            output = temp / profile.lower()
            command = [
                compiler,
                *flags,
                f"-DS22PLUS_FYG8_P233_PROFILE={number}",
                "-DS22PLUS_FYG8_P233_RUN_ID_BYTES=" + _run_id_define(run_id),
                "-I",
                str(include_dir),
                str(runtime),
                str(client),
                "-o",
                str(output),
            ]
            run_checked(command, cwd=root, label=f"{profile} cross-link")
            data = output.read_bytes()
            file_output = run_checked(
                [file_tool, "-b", str(output)],
                cwd=root,
                label=f"{profile} file inspection",
            ).stdout.decode("ascii", "replace").strip()
            symbols = run_checked(
                [nm_tool, "-n", str(output)],
                cwd=root,
                label=f"{profile} symbol inspection",
            ).stdout.decode("ascii", "replace")
            if (
                "ELF 64-bit LSB executable, ARM aarch64" not in file_output
                or "statically linked" not in file_output
                or len(re.findall(r"\bT _start$", symbols, re.MULTILINE)) != 1
                or data.count(run_id) != 1
                or data.count(b"/proc/s22_checkpoint") != 1
            ):
                raise CheckError(f"{profile} linked output identity mismatch")
            module_counts = {
                name: data.count(name.encode("ascii"))
                for name, _, _, _ in legacy_e1.MODULE_SPECS
            }
            expected_module_count = 0 if profile == "E1A" else 1
            if any(count != expected_module_count for count in module_counts.values()):
                raise CheckError(f"{profile} module closure mismatch: {module_counts}")
            if profile == "E1A" and "load_and_verify_module" in symbols:
                raise CheckError("E1A retained the E1B module loader")
            if profile == "E1B" and "load_and_verify_module" not in symbols:
                raise CheckError("E1B lost the watchdog module loader")
            outputs[profile] = {
                **receipt(data),
                "file": file_output,
                "source_check_run_id": run_id.hex(),
                "module_string_counts": module_counts,
                "verified": True,
            }

        child_output = temp / "child"
        run_checked(
            [compiler, *flags, str(child), "-o", str(child_output)],
            cwd=root,
            label="E1 child cross-link",
        )
        child_data = child_output.read_bytes()
        child_file = run_checked(
            [file_tool, "-b", str(child_output)],
            cwd=root,
            label="E1 child file inspection",
        ).stdout.decode("ascii", "replace").strip()
        if (
            "ELF 64-bit LSB executable, ARM aarch64" not in child_file
            or "statically linked" not in child_file
            or child_data.count(legacy_e1.CHILD_TOKEN) != 1
        ):
            raise CheckError("E1 child linked output mismatch")
        outputs["child"] = {
            **receipt(child_data),
            "file": child_file,
            "verified": True,
        }
    return outputs


def validate_reachable_records() -> dict[str, Any]:
    checked = 0
    for profile, sequence in model.PROFILE_STAGE_SEQUENCES.items():
        run_id = SOURCE_CHECK_RUN_IDS[profile]
        if not any(run_id) or run_id == model.model_run_id(profile):
            raise CheckError(f"{profile} source-check run ID is not independent")
        record = model.initialize_record(profile, run_id)
        model.unsat_record(profile, run_id)
        for stage in sequence:
            item_index = model._expected_item_index(stage)
            terminal = stage == model.PROFILE_TERMINALS[profile]
            cases = (
                [(model.OUTCOME_SUCCESS, 0)]
                if terminal
                else [(model.OUTCOME_PROGRESS, 0)]
                + [(model.OUTCOME_FAILURE, detail) for detail in range(1, 4096)]
            )
            for outcome, detail in cases:
                request = model.encode_request(
                    profile,
                    stage,
                    run_id=run_id,
                    outcome=outcome,
                    item_index=item_index,
                    detail=detail,
                )
                candidate = model.apply_request(record, request)
                model._validate_record_families(candidate)
                checked += 1
            if not terminal:
                record = model.apply_request(
                    record,
                    model.encode_request(
                        profile,
                        stage,
                        run_id=run_id,
                        outcome=model.OUTCOME_PROGRESS,
                        item_index=item_index,
                    ),
                )
    return {
        "reachable_slot_variants": checked,
        "profiles": sorted(model.PROFILE_NUMBERS),
        "source_check_run_ids": {
            profile: value.hex()
            for profile, value in sorted(SOURCE_CHECK_RUN_IDS.items())
        },
        "adjacent_slot_combinations_verified": True,
        "zero_crc_count": 0,
        "family_collision_count": 0,
        "decoder_policy_id": decoder.POLICY_ID,
        "verified": True,
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    source = resolve(root, args.source)
    paths = {
        "patch": resolve(root, args.patch),
        "client": resolve(root, args.client),
        "runtime": resolve(root, args.runtime),
        "legacy_runtime": resolve(root, args.legacy_runtime),
        "header": resolve(root, args.header),
        "child": resolve(root, args.child),
    }
    data = {name: read_direct(path, name) for name, path in paths.items()}
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "patch": audit_patch(source, paths["patch"], data["patch"]),
        "sources": audit_sources(
            data["client"],
            data["runtime"],
            data["legacy_runtime"],
            data["header"],
            data["child"],
        ),
        "linked_userspace": compile_userspace(
            root, paths["client"], paths["runtime"], paths["child"]
        ),
        "reachable_record_contract": validate_reachable_records(),
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "manifest_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
        "next": "candidate-specific build and offline artifact closure",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument(
        "--legacy-runtime", type=Path, default=DEFAULT_LEGACY_RUNTIME
    )
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--child", type=Path, default=DEFAULT_CHILD)
    return parser.parse_args()


def main() -> int:
    try:
        result = build_result(parse_args())
    except (CheckError, model.DesignError) as exc:
        print(json.dumps({"verdict": "BLOCKED_P233_E1_SOURCE", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
