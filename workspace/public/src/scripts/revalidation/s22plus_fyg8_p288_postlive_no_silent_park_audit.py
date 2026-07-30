#!/usr/bin/env python3
"""Audit the P2.88 generation-88-to-89 publication/park corridor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_candidate_intent as intent
import s22plus_fyg8_p288_postbuild_linked_audit as postbuild
import s22plus_fyg8_p288_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p288_postlive_no_silent_park_audit_v1"
VERDICT = "PASS_P288_NO_SILENT_PARK_INVARIANT_REFUTED_H0"
RUN_ID = "20bb4d70842fe7ae1a6bd0aec261d722"
POSTBUILD_COMMIT = "6fc2881e2abe22161a66ce130fc4c10bf430a4bf"

DEFAULT_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/intent/"
    "candidate-intent.json"
)
DEFAULT_CANDIDATE_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/process-v2/"
    "candidate-static.json"
)
DEFAULT_BASE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)

P286_PARK_COUNTS = {
    "p282_progress": 1,
    "p282_fail_classification": 1,
    "p282_publish_classification": 2,
    "p282_set_cycle_warning": 1,
    "p282_cycle_warning_detail": 1,
    "p282_cycle_abort": 2,
    "p282_cycle_abort_condition": 1,
    "p282_restart_exact_failure": 1,
    "p282_cycle_restart": 1,
    "p282_phase_bind": 2,
    "p286_e3_run": 3,
}

CORRIDOR_RELATION = {
    ("p282_progress", 1): (
        "direct: generation-88 write committed but publication returned error"
    ),
    ("p282_cycle_abort", 1): (
        "conditional: deadline failure publication itself returned error"
    ),
    ("p282_cycle_abort", 2): (
        "conditional: deadline failure was already published"
    ),
}

P286_PARK_DURABLE_PREDECESSORS = {
    ("p282_cycle_abort", 2): (
        "failure publication returned success before best-effort cleanup"
    ),
    ("p286_e3_run", 3): (
        "terminal-success publication returned success before final park"
    ),
}


class AuditError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _file_receipt(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"size": size, "sha256": digest.hexdigest()}


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is unavailable or invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value, data


def resolve_shared_input(root: Path, requested: Path) -> Path:
    if requested.is_absolute():
        return requested
    local = root / requested
    if local.is_file():
        return local
    common_dir = subprocess.run(
        (
            "git",
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ),
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    shared = Path(common_dir).resolve().parent / requested
    if not shared.is_file():
        raise AuditError(
            "shared private input is unavailable in both the worktree and "
            f"primary checkout: {requested}"
        )
    return shared


def _function_park_rows(data: bytes, name: str) -> list[dict[str, Any]]:
    body = source_contract._c_function_body(data, name)  # noqa: SLF001
    body_start = data.find(body)
    if body_start < 0 or data.find(body, body_start + 1) >= 0:
        raise AuditError(f"P2.86 function body is not unique: {name}")
    rows = []
    for site_index, match in enumerate(
        re.finditer(rb"(?<!p288_raw_)quiet_park\(\);", body),
        1,
    ):
        absolute = body_start + match.start()
        rows.append(
            {
                "function": name,
                "site_index": site_index,
                "line": data.count(b"\n", 0, absolute) + 1,
                "corridor_relation": CORRIDOR_RELATION.get(
                    (name, site_index),
                    "outside the direct generation-88-to-89 corridor",
                ),
            }
        )
    return rows


def audit_p286_park_inventory(root: Path) -> dict[str, Any]:
    path = (
        root
        / "workspace/public/src/native-init/"
        "s22plus_fyg8_p286_e3_runtime.inc.c"
    )
    data = path.read_bytes()
    rows = []
    actual_counts = {}
    for name, expected in P286_PARK_COUNTS.items():
        function_rows = _function_park_rows(data, name)
        actual_counts[name] = len(function_rows)
        if len(function_rows) != expected:
            raise AuditError(
                f"P2.86 park count differs for {name}: "
                f"{len(function_rows)} != {expected}"
            )
        rows.extend(function_rows)
    for row in rows:
        predecessor = P286_PARK_DURABLE_PREDECESSORS.get(
            (row["function"], row["site_index"])
        )
        row["durable_prepublication_proved"] = predecessor is not None
        row["publication_assessment"] = predecessor or (
            "no successful primary publication dominates this site; "
            "P2.88 only attempts an unclassified fallback and ignores its "
            "return before the raw park"
        )
    direct_count = len(
        re.findall(rb"(?<!p288_raw_)quiet_park\(\);", data)
    )
    if direct_count != 16 or len(rows) != direct_count:
        raise AuditError(
            "P2.86 quiet_park inventory is not exact: "
            f"enumerated={len(rows)} source={direct_count}"
        )
    return {
        "source": _receipt(data),
        "site_count": direct_count,
        "function_counts": actual_counts,
        "sites": rows,
        "all_sites_enumerated": True,
        "durable_prepublication_site_count": sum(
            row["durable_prepublication_proved"] for row in rows
        ),
        "attempt_only_or_unproved_site_count": sum(
            not row["durable_prepublication_proved"] for row in rows
        ),
        "absolute_no_silent_park_invariant_proved": False,
        "verified": True,
    }


def _gate_entries(plan: bytes) -> tuple[str, ...]:
    start = plan.index(
        b"static const struct s22plus_o2_bind_gate_entry "
        b"s22plus_o2_bind_gates[] = {"
    )
    end = plan.index(b"\n};", start)
    return tuple(
        value.decode("ascii")
        for value in re.findall(
            rb'\{\d+U, "([^"]+)", "[^"]+", "[^"]+"\},',
            plan[start:end],
        )
    )


def audit_gate_lineage(
    root: Path, exact_source: dict[str, bytes]
) -> dict[str, Any]:
    historical_plan = (
        root
        / "workspace/public/src/native-init/s22plus_fyg8_p241_e2_plan.h"
    ).read_bytes()
    historical_runtime = (
        root
        / "workspace/public/src/native-init/"
        "s22plus_fyg8_p241_e2_runtime.c"
    ).read_bytes()
    provider = exact_source["p260_provider_sources"]
    exact_plan = exact_source["plan_header"]
    exact_runtime = exact_source["runtime_wrapper"]
    exact_include = exact_source["p288_e3_runtime_include"]

    historical = _gate_entries(historical_plan)
    exact = _gate_entries(exact_plan)
    if (
        len(historical) != 8
        or b"S22PLUS_O2_BIND_GATE_COUNT == 8U" not in historical_runtime
        or len(exact) != 12
        or b"S22PLUS_O2_BIND_GATE_COUNT == 12U" not in exact_runtime
        or provider.count(b"S22PLUS_O2_BIND_GATE_COUNT == 8U") != 1
        or provider.count(b"S22PLUS_O2_BIND_GATE_COUNT == 12U") != 1
    ):
        raise AuditError("P2.41-to-P2.88 gate-count lineage differs")

    driver = source_contract._c_function_body(  # noqa: SLF001
        exact_runtime, "p241_check_driver_symlink"
    )
    udc = source_contract._c_function_body(  # noqa: SLF001
        exact_runtime, "p241_check_udc"
    )
    gate = source_contract._c_function_body(  # noqa: SLF001
        exact_runtime, "p241_check_gate"
    )
    revalidate = source_contract._c_function_body(  # noqa: SLF001
        exact_source["p260_e3_runtime_include"],
        "p260_revalidate_or_fail",
    )
    if (
        b"p241_newfstatat(" not in driver
        or b"p241_readlinkat(" not in driver
        or b"sys_openat(\"/sys/class/udc\"" not in udc
        or b"p241_getdents64(" not in udc
        or b"if (index + 1U < S22PLUS_O2_BIND_GATE_COUNT)" not in gate
        or b"fail_at(frontier_stage, 0U, detail);" not in revalidate
        or b"p260_expect_value(" in driver + udc + gate
        or b"runtime_status" in driver + udc + gate
    ):
        raise AuditError("P2.88 gate operation shape differs")
    return {
        "historical_p241": {
            "gate_count": len(historical),
            "gate_ids": historical,
            "plan": _receipt(historical_plan),
        },
        "exact_p288": {
            "gate_count": len(exact),
            "gate_ids": exact,
            "plan": _receipt(exact_plan),
        },
        "lineage": "P2.44 provider transform expands historical 8 to exact 12",
        "driver_gate_syscalls": ["newfstatat", "readlinkat"],
        "udc_gate_syscalls": ["openat", "getdents64", "close"],
        "device_attribute_reads": [],
        "returned_failure_route": (
            "fail_at -> generation-89 failure detail, then unclassified "
            "fallback if publication fails"
        ),
        "returned_gate_failure_is_independent_silence_cause": False,
        "nonreturning_vfs_syscall_not_statically_excluded": True,
        "runtime_pm_attribute_resume_mechanism_supported": False,
        "verified": True,
    }


def audit_exact_close_return(base_archive: Path) -> dict[str, Any]:
    try:
        with tarfile.open(base_archive, "r:gz") as archive:
            open_file = archive.extractfile("kernel_platform/common/fs/open.c")
            proc_file = archive.extractfile(
                "kernel_platform/common/fs/proc/inode.c"
            )
            if open_file is None or proc_file is None:
                raise AuditError("exact VFS close sources are absent")
            open_source = open_file.read()
            proc_source = proc_file.read()
    except (OSError, tarfile.TarError, KeyError) as exc:
        raise AuditError(f"exact VFS close sources are unavailable: {exc}") from exc

    filp_close = source_contract._c_function_body(  # noqa: SLF001
        open_source, "filp_close"
    )
    proc_release = source_contract._c_function_body(  # noqa: SLF001
        proc_source, "proc_reg_release"
    )
    fops_start = proc_source.index(
        b"static const struct file_operations proc_reg_file_ops = {"
    )
    fops_end = proc_source.index(b"\n};", fops_start)
    fops = proc_source[fops_start:fops_end]
    if (
        b"if (filp->f_op->flush)" not in filp_close
        or b"retval = filp->f_op->flush(filp, id);" not in filp_close
        or b".flush" in fops
        or b"return 0;" not in proc_release
    ):
        raise AuditError("exact procfs close return path differs")
    return {
        "base_archive": _file_receipt(base_archive),
        "common_fs_open": _receipt(open_source),
        "common_fs_proc_inode": _receipt(proc_source),
        "proc_file_operations_has_flush": False,
        "filp_close_nonzero_source": "file_operations.flush only",
        "proc_release_returns_zero_without_custom_proc_release": True,
        "candidate_proc_ops_has_custom_release": False,
        "successful_open_single_close_returns_zero": True,
        "close_error_after_successful_checkpoint_write_rejected": True,
        "verified": True,
    }


def audit_publication_self_failure(
    exact_source: dict[str, bytes],
    close_return: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = exact_source["checkpoint_client"]
    include = exact_source["p288_e3_runtime_include"]
    wrapper = exact_source["runtime_wrapper"]
    patch = exact_source["base_patch"]

    publish = source_contract._c_function_body(  # noqa: SLF001
        client, "p288_publish_next"
    )
    progress = source_contract._c_function_body(  # noqa: SLF001
        include, "p282_progress"
    )
    quiet = source_contract._c_function_body(  # noqa: SLF001
        wrapper, "quiet_park"
    )
    fail = source_contract._c_function_body(  # noqa: SLF001
        wrapper, "fail_at"
    )
    client_order = (
        b"long written = sys_write(",
        b"long closed = sys_close(",
        b"if (written != (long)sizeof(request))",
        b"if (closed != 0)",
        b"client->generation = (uint8_t)(ordinal + 1U);",
    )
    offsets = tuple(publish.index(token) for token in client_order)
    if offsets != tuple(sorted(offsets)):
        raise AuditError("P2.88 client publication update order differs")
    if (
        b"if (rc != 0) {\n        quiet_park();" not in progress
        or b"(void)s22_p288_checkpoint_unclassified_next(&g_checkpoint);"
        not in quiet
        or b"p288_raw_quiet_park();" not in quiet
        or b"if (rc != 0)" not in fail
        or b"(void)s22_p288_checkpoint_unclassified_next(&g_checkpoint);"
        not in fail
        or b"p288_raw_quiet_park();" not in fail
    ):
        raise AuditError("P2.88 publication-error park route differs")

    kernel_order = (
        b"memcpy(&record->slots[next_slot].commit_crc",
        b"memcmp(&record->slots[next_slot], &next, sizeof(next))",
        b"s22_fyg8_e1_state.active_slot = next_slot;",
        b"return count;",
    )
    kernel_offsets = tuple(patch.index(token) for token in kernel_order)
    if kernel_offsets != tuple(sorted(kernel_offsets)):
        raise AuditError("P2.88 kernel post-commit order differs")
    postcommit_to_state = patch[kernel_offsets[1] : kernel_offsets[2]]
    state_to_return = patch[kernel_offsets[2] : kernel_offsets[3]]
    if (
        b"return -ESTALE;" not in postcommit_to_state
        or b"return -" in state_to_return
    ):
        raise AuditError("P2.88 kernel post-commit return surface differs")

    close_error_rejected = (
        close_return is not None
        and close_return.get(
            "close_error_after_successful_checkpoint_write_rejected"
        )
        is True
    )
    return {
        "absolute_invariant_counterexample": (
            "a primary checkpoint publication returns nonzero and the "
            "unclassified fallback publication also returns nonzero; "
            "quiet_park ignores the fallback result and enters the raw park"
        ),
        "exact_postcommit_error_model": (
            "the kernel can return -ESTALE after committing the target CRC "
            "but before advancing its in-kernel generation; a fallback still "
            "targets that same next generation and is not sequence-stale"
        ),
        "kernel_commit_precedes_kernel_state_update": True,
        "kernel_postcommit_estale_precedes_state_update": True,
        "kernel_has_no_error_return_after_state_update": True,
        "client_close_check_precedes_client_generation_update": True,
        "exact_procfs_close_error_instantiates_model": (
            False if close_error_rejected else None
        ),
        "exact_procfs_close_error_rejected": close_error_rejected,
        "successful_write_then_stale_client_divergence_rejected": True,
        "publication_error_reaches_quiet_park": True,
        "quiet_park_ignores_fallback_publication_result": True,
        "retained_shape_implication": (
            "no fallback publication successfully committed generation 89; "
            "it does not distinguish a nonreturn from primary and fallback "
            "publication failures"
        ),
        "proves_live_cause": False,
        "proves_current_no_silent_park_invariant": False,
        "current_no_silent_park_invariant_holds": False,
        "verified": True,
    }


def audit_pre_live_park_gate_scope(
    exact_source: dict[str, bytes],
) -> dict[str, Any]:
    reported = source_contract._audit_park_routes(  # noqa: SLF001
        exact_source
    )
    contract_source = Path(source_contract.__file__).read_bytes()
    start = contract_source.index(b"def _audit_park_routes(")
    end = contract_source.index(b"\ndef _audit_publication_bound(", start)
    gate = contract_source[start:end]
    wrapper = exact_source["runtime_wrapper"]
    direct_pattern = re.compile(rb"(?<!p288_raw_)quiet_park\(\);")
    exact_include_park_count = len(
        direct_pattern.findall(exact_source["p288_e3_runtime_include"])
    )
    if (
        reported.get("raw_sinks_publication_dominated") is not True
        or reported.get("unclassified_before_generic_park") is not True
        or exact_include_park_count != 17
        or b'"raw_sinks_publication_dominated": True' not in gate
        or b'"unclassified_before_generic_park": True' not in gate
        or b"(void)s22_p288_checkpoint_unclassified_next(&g_checkpoint);"
        not in wrapper
        or b"long fallback_rc" in wrapper
        or b"if (fallback_rc" in wrapper
    ):
        raise AuditError("P2.88 pre-live park-route gate shape differs")
    return {
        "reported_claim": reported,
        "mechanically_checked_scope": (
            "all raw park sinks are topologically isolated behind wrappers "
            "that attempt an unclassified publication"
        ),
        "fallback_return_checked": False,
        "durable_fallback_commit_checked": False,
        "proves_publication_attempt_before_raw_park": True,
        "proves_successful_publication_before_raw_park": False,
        "publication_dominance_claim_is_too_strong": True,
        "exact_p288_e3_include_quiet_park_call_count": (
            exact_include_park_count
        ),
        "verified": True,
    }


def audit_postbuild_proof(
    root: Path, candidate_static_path: Path
) -> dict[str, Any]:
    candidate_static, payload = _read_json(
        candidate_static_path, "P2.88 candidate static result"
    )
    checker = (
        root
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_candidate_static_checker.py"
    ).read_bytes()
    required = (
        b"fresh = postbuild_audit.check(check_args)",
        b"result != fresh",
        b'.get("postbuild_audit", {})',
        b'.get("verified")',
    )
    ancestry = subprocess.run(
        ("git", "merge-base", "--is-ancestor", POSTBUILD_COMMIT, "HEAD"),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    build_repro = candidate_static.get("build_repro", {})
    if (
        ancestry.returncode != 0
        or any(token not in checker for token in required)
        or candidate_static.get("verdict")
        != "PASS_P288_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
        or build_repro.get("fresh_reverification") is not True
        or build_repro.get("linked_audit_verified") is not True
    ):
        raise AuditError("P2.88 formal post-build proof chain is incomplete")
    host = postbuild.host_native_exhaustive(root)
    if (
        host.get("checked_pairs") != 6_815_744
        or host.get("accepted_pairs") != 103
        or host.get("verified") is not True
    ):
        raise AuditError("P2.88 host exhaustive validator replay differs")
    return {
        "commit": POSTBUILD_COMMIT,
        "candidate_static": _receipt(payload),
        "candidate_static_verdict": candidate_static["verdict"],
        "formal_result": build_repro.get("result"),
        "fresh_postbuild_replay_required": True,
        "host_native_replay": host,
        "linked_elf_table_proof_transitively_accepted": True,
        "source_or_table_validator_mismatch_strongly_rejected": True,
        "runtime_publication_return_or_state_mismatch_rejected": False,
        "verified": True,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = intent.repo_root()
    intent_path = intent.resolve(root, args.intent)
    candidate_static_path = intent.resolve(
        root, args.candidate_static
    )
    base_archive = resolve_shared_input(root, args.base_archive)
    intent_value, intent_payload = _read_json(
        intent_path, "P2.88 frozen intent"
    )
    exact_source = source_contract.source_bytes(root)
    current_receipts = {
        key: _receipt(value) for key, value in exact_source.items()
    }
    frozen_receipts = intent_value.get("identity_preimage", {}).get("sources")
    if (
        intent_value.get("run_id") != RUN_ID
        or len(exact_source) != 83
        or current_receipts != frozen_receipts
    ):
        raise AuditError("P2.88 frozen 83-key identity differs")

    close_return = audit_exact_close_return(base_archive)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "run_id": RUN_ID,
        "identity": {
            "intent": _receipt(intent_payload),
            "source_key_count": len(exact_source),
            "changed_keys": [],
            "verified": True,
        },
        "postbuild_validator": audit_postbuild_proof(
            root, candidate_static_path
        ),
        "gate_lineage": audit_gate_lineage(root, exact_source),
        "p286_park_inventory": audit_p286_park_inventory(root),
        "exact_close_return": close_return,
        "publication_self_failure": audit_publication_self_failure(
            exact_source, close_return
        ),
        "pre_live_park_gate_scope": audit_pre_live_park_gate_scope(
            exact_source
        ),
        "corridor_conclusion": {
            "ordinary_returned_gate_failure_is_causal_conclusion": False,
            "publication_acceptance_return_and_state_sync_is_priority": True,
            "new_f1_permitted_by_this_h0": False,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument(
        "--candidate-static",
        type=Path,
        default=DEFAULT_CANDIDATE_STATIC,
    )
    parser.add_argument(
        "--base-archive",
        type=Path,
        default=DEFAULT_BASE_ARCHIVE,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = audit(parse_args(argv))
    except (
        AuditError,
        source_contract.SourceContractError,
        intent.IntentError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
