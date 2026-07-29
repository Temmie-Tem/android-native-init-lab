#!/usr/bin/env python3
"""Pre-intent P2.86 candidate/D1 change-closure freeze.

This module is host-only data and validation.  It creates no candidate,
derives no intent, performs no build, and grants no device authority.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import s22plus_fyg8_p282_source_contract as p282
import s22plus_fyg8_p284_source_contract as p284


SCHEMA = "s22plus_fyg8_p286_change_closure_freeze_v2"
VERDICT = "PASS_P286_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY"
PROFILE = p284.PROFILE
INHERITED_CONTRACT_ID = p284.CONTRACT_ID
PLANNED_CONTRACT_ID = "s22plus-fyg8-p286-parent-tail-bounded-restart-v1"
P284_FROZEN_RUN_ID = "023060c8dd0ab036f8547a816624356f"
P284_FROZEN_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p284_v4/"
    "intent/candidate-intent.json"
)
CHANGE_WINDOW_BASE_COMMIT = "7929e9f7d7fea1eb99ab43dcd841c5a9c3b6ef94"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False

# These overlays can affect candidate boot.img bytes and therefore must become
# SOURCE_KEY inputs before intent derivation. Existing P2.84 direct sources are
# inherited byte-for-byte and are forbidden mutation targets.
PAYLOAD_SOURCE_PATHS = MappingProxyType(
    {
        "p286_contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_contract_spec.py"
        ),
        "p286_source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contract.py"
        ),
        "p286_candidate_intent": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_candidate_intent.py"
        ),
        "p286_build": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_build.py"
        ),
        "p286_candidate_builder": Path(
            "workspace/public/src/scripts/revalidation/"
            "build_s22plus_fyg8_p286_candidate.py"
        ),
        "p286_userspace_build": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_userspace_build.py"
        ),
        "p286_boot_only_packager": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_boot_only_packager.py"
        ),
        "p286_trace_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_trace_contract.py"
        ),
        "p286_e3_runtime_include": Path(
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p286_e3_runtime.inc.c"
        ),
        "p286_classifier_include": Path(
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p286_classifier.inc.c"
        ),
    }
)

# These files verify or document the candidate but cannot alter boot.img
# bytes. They remain outside SOURCE_KEYS and are bound by bundle.sha256 before
# approval, matching the existing retirement-guard separation.
NON_IDENTITY_SUPPORT_PATHS = MappingProxyType(
    {
        "p286_change_freeze": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_change_freeze.py"
        ),
        "p286_freeze_report": Path(
            "docs/reports/"
            "S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_"
            "2026-07-29.md"
        ),
        "p286_candidate_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_candidate_contract.py"
        ),
        "p286_source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contracts.py"
        ),
        "p286_build_repro_check": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_build_repro_check.py"
        ),
        "p286_candidate_static_checker": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_candidate_static_checker.py"
        ),
        "p286_e2_stock_closure": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_e2_stock_closure.py"
        ),
        "p286_linked_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_linked_audit.py"
        ),
        "p286_pre_lto_qualification": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_pre_lto_qualification.py"
        ),
        "p286_decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_e1_decoder.py"
        ),
    }
)

STAGE_A_GOVERNANCE_PATHS = frozenset(
    {
        Path("AGENTS.md"),
        Path("GOAL.md"),
        Path(
            "docs/reports/"
            "S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_"
            "2026-07-29.md"
        ),
        Path(
            "docs/reports/"
            "S22PLUS_FYG8_P286_DEEP_SUSPEND_GUARD_REACHABILITY_H0_"
            "2026-07-29.md"
        ),
        Path(
            "docs/reports/"
            "S22PLUS_FYG8_P286_FULL_LTO_PRIVATE_PATH_REPRO_FAILURE_H0_"
            "2026-07-30.md"
        ),
        Path(
            "docs/reports/"
            "S22PLUS_FYG8_P286_RECOVERY_USB_MODULE_REFERENCE_AUDIT_H0_"
            "2026-07-29.md"
        ),
        Path("tests/test_s22plus_fyg8_p286_change_freeze.py"),
    }
)
STAGE_A_DECLARED_CHANGED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (
            *STAGE_A_GOVERNANCE_PATHS,
            *PAYLOAD_SOURCE_PATHS.values(),
            *NON_IDENTITY_SUPPORT_PATHS.values(),
        )
    )
)

CANDIDATE_CHANGE_REQUIREMENTS = (
    (
        "parent-runtime-status-gate",
        "wait for exact parent suspended on the existing stop deadline",
    ),
    (
        "bounded-helper-reap",
        "fix timeout state before kill/reap; use WNOHANG plus an auxiliary "
        "deadline, classify an unreaped child, and publish the exact terminal "
        "checkpoint before best-effort trace cleanup; on the normal restart "
        "path publish one cleanup-pending progress marker before kprobe "
        "unregister and RCU cleanup",
    ),
    (
        "actual-outer-work-probes",
        "attach outer_sm_work_in/out to dwc3_otg_sm_work",
    ),
    (
        "helper-dispatch-completion-split",
        "distinguish helper dispatch from helper completion",
    ),
    (
        "restart-failure-partition",
        "distinguish flush timeout, write completion, start-peripheral "
        "entry without return, and later readback failure",
    ),
    (
        "residual-outer-tail-bound",
        "retain a bounded classified PERIPHERAL write path after parent "
        "suspended because outer requeue/return may remain",
    ),
    (
        "identity-closure-enforcement",
        "bind every payload-determining implementation/build input in the "
        "source preimage and bind verifier/evidence support in bundle.sha256",
    ),
)

D1_PRIVATE_ROOT = PurePosixPath(
    "workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3"
)
D1_PRIVATE_MUTATION_PATHS = (
    D1_PRIVATE_ROOT / "device_runner.sh",
    D1_PRIVATE_ROOT / "host_runner.sh",
    D1_PRIVATE_ROOT / "control_analyzer.py",
    D1_PRIVATE_ROOT / "runner_manifest.json",
)
D1_CHANGE_REQUIREMENTS = (
    (
        "instance-trace-spelling",
        "parse trace-instance event spelling without a nonexistent group "
        "prefix",
    ),
    (
        "immediate-watchdog-disarm",
        "terminate and reap the watchdog immediately instead of waiting for "
        "its sleep deadline",
    ),
    (
        "comm-newline-removal",
        "write /proc/self/comm without embedding a newline in the trace header",
    ),
    (
        "remove-unapproved-endpoint-count",
        "remove the endpoint-count predicate that was not in the approved "
        "identity contract",
    ),
)

GENERATED_SOURCE_KEYS = frozenset(
    (*p282.GENERATED_KEYS, "trace_descriptor_header")
)
PLANNED_SOURCE_KEYS = frozenset(
    (*p284.SOURCE_KEYS, *PAYLOAD_SOURCE_PATHS)
)


class FreezeError(ValueError):
    pass


def _pure(path: Path | PurePosixPath) -> PurePosixPath:
    value = PurePosixPath(path.as_posix())
    if value.is_absolute() or ".." in value.parts or "." in value.parts:
        raise FreezeError(f"path is not canonical repository-relative: {value}")
    return value


def _overlap(first: PurePosixPath, second: PurePosixPath) -> bool:
    first_parts = first.parts
    second_parts = second.parts
    length = min(len(first_parts), len(second_parts))
    return first_parts[:length] == second_parts[:length]


def inherited_direct_source_paths() -> dict[str, Path]:
    paths = dict(p282.COMMON_SOURCE_PATHS)
    paths.update(p284.OVERLAY_SOURCE_PATHS)
    expected = p284.SOURCE_KEYS - GENERATED_SOURCE_KEYS
    if set(paths) != expected:
        raise FreezeError("P2.84 direct SOURCE_KEY path inventory drifted")
    return paths


def validate_inherited_receipts(root: Path) -> dict[str, Any]:
    path = root / P284_FROZEN_INTENT
    if path.is_symlink() or not path.is_file():
        raise FreezeError("frozen P2.84 intent is missing or indirect")
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FreezeError("frozen P2.84 intent is not ASCII JSON") from exc
    preimage = value.get("identity_preimage")
    expected = (
        preimage.get("sources")
        if isinstance(preimage, dict)
        else None
    )
    if (
        value.get("run_id") != P284_FROZEN_RUN_ID
        or value.get("source_contract_id") != p284.CONTRACT_ID
        or not isinstance(preimage, dict)
        or preimage.get("source_contract_id") != p284.CONTRACT_ID
        or not isinstance(expected, dict)
        or len(expected) != 60
    ):
        raise FreezeError("frozen P2.84 intent identity is invalid")
    _source, actual = p284.source_receipts(root)
    changed = tuple(
        sorted(
            key
            for key in set(expected) | set(actual)
            if expected.get(key) != actual.get(key)
        )
    )
    if changed:
        raise FreezeError(
            "frozen P2.84 source receipts changed: "
            + ",".join(changed)
        )
    return {
        "intent_path": P284_FROZEN_INTENT.as_posix(),
        "run_id": P284_FROZEN_RUN_ID,
        "source_contract_id": p284.CONTRACT_ID,
        "receipt_count": len(actual),
        "changed_keys": [],
        "verified": True,
    }


def planned_direct_source_paths() -> dict[str, Path]:
    paths = inherited_direct_source_paths()
    if set(paths) & set(PAYLOAD_SOURCE_PATHS):
        raise FreezeError("planned payload SOURCE_KEY collides with P2.84")
    paths.update(PAYLOAD_SOURCE_PATHS)
    expected = PLANNED_SOURCE_KEYS - GENERATED_SOURCE_KEYS
    if set(paths) != expected:
        raise FreezeError("planned direct SOURCE_KEY path inventory drifted")
    return paths


def source_key_rows() -> tuple[dict[str, str], ...]:
    direct = planned_direct_source_paths()
    rows = []
    for key in sorted(PLANNED_SOURCE_KEYS):
        path = (
            f"generated://{key}"
            if key in GENERATED_SOURCE_KEYS
            else direct[key].as_posix()
        )
        rows.append({"source_key": key, "path": path})
    return tuple(rows)


def _missing_paths(root: Path, paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        path.as_posix()
        for path in paths
        if not (root / path).is_file()
    )


def missing_payload_paths(root: Path) -> tuple[str, ...]:
    return _missing_paths(root, tuple(PAYLOAD_SOURCE_PATHS.values()))


def missing_support_paths(root: Path) -> tuple[str, ...]:
    return _missing_paths(root, tuple(NON_IDENTITY_SUPPORT_PATHS.values()))


def _run_git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise FreezeError(f"git invocation failed: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise FreezeError(
            f"git {' '.join(args)} failed ({completed.returncode}): {stderr}"
        )
    return completed.stdout


def _decode_git_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def _porcelain_paths(output: bytes) -> set[str]:
    fields = output.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise FreezeError("unexpected git status --porcelain=v1 -z record")
        status = record[:2]
        paths.add(_decode_git_path(record[3:]))
        if b"R" in status or b"C" in status:
            if index >= len(fields) or not fields[index]:
                raise FreezeError("truncated git rename/copy status record")
            paths.add(_decode_git_path(fields[index]))
            index += 1
    return paths


def git_derived_changed_paths(
    root: Path,
    base_commit: str,
) -> tuple[str, ...]:
    root = root.resolve()
    top = Path(
        _decode_git_path(
            _run_git(root, "rev-parse", "--show-toplevel")
        ).strip()
    ).resolve()
    if top != root:
        raise FreezeError(f"repo root mismatch: expected {root}, git reports {top}")
    _run_git(root, "rev-parse", "--verify", f"{base_commit}^{{commit}}")
    _run_git(root, "merge-base", "--is-ancestor", base_commit, "HEAD")
    committed = {
        _decode_git_path(path)
        for path in _run_git(
            root,
            "diff",
            "--name-only",
            "-z",
            f"{base_commit}..HEAD",
            "--",
        ).split(b"\0")
        if path
    }
    worktree = _porcelain_paths(
        _run_git(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        )
    )
    return tuple(sorted(committed | worktree))


def validate_declared_change_set(
    *,
    derived_paths: tuple[str, ...],
    declared_paths: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    derived = {_pure(PurePosixPath(path)) for path in derived_paths}
    declared = {_pure(PurePosixPath(path)) for path in declared_paths}
    missing_declarations = derived - declared
    overdeclared = declared - derived
    if missing_declarations or overdeclared:
        raise FreezeError(
            "declared/Git-derived change set mismatch: "
            "missing_declarations="
            f"{sorted(path.as_posix() for path in missing_declarations)}; "
            "overdeclared="
            f"{sorted(path.as_posix() for path in overdeclared)}"
        )
    allowed = {
        _pure(path)
        for path in (
            *PAYLOAD_SOURCE_PATHS.values(),
            *NON_IDENTITY_SUPPORT_PATHS.values(),
            *STAGE_A_GOVERNANCE_PATHS,
        )
    }
    unexpected = derived - allowed
    if unexpected:
        raise FreezeError(
            "Git-derived change is outside the frozen change window: "
            f"{sorted(path.as_posix() for path in unexpected)}"
        )
    exact = tuple(sorted(path.as_posix() for path in derived))
    return {
        "git_derived_paths": exact,
        "declared_paths": exact,
    }


def validate_freeze(root: Path) -> dict[str, Any]:
    if len(p284.SOURCE_KEYS) != 60:
        raise FreezeError("P2.84 SOURCE_KEY count drifted")
    inherited = inherited_direct_source_paths()
    planned = planned_direct_source_paths()
    if len(GENERATED_SOURCE_KEYS) != 5 or len(inherited) != 55:
        raise FreezeError("P2.84 generated/direct partition drifted")
    if len(PAYLOAD_SOURCE_PATHS) != 10:
        raise FreezeError("planned payload-source count drifted")
    if len(NON_IDENTITY_SUPPORT_PATHS) != 10:
        raise FreezeError("non-identity support count drifted")
    if len(PLANNED_SOURCE_KEYS) != 70 or len(planned) != 65:
        raise FreezeError("planned SOURCE_KEY count drifted")

    inherited_paths = {_pure(path) for path in inherited.values()}
    payload_paths = {
        _pure(path) for path in PAYLOAD_SOURCE_PATHS.values()
    }
    support_paths = {
        _pure(path) for path in NON_IDENTITY_SUPPORT_PATHS.values()
    }
    if len(payload_paths) != len(PAYLOAD_SOURCE_PATHS):
        raise FreezeError("payload SOURCE_KEY paths are not unique")
    if len(support_paths) != len(NON_IDENTITY_SUPPORT_PATHS):
        raise FreezeError("non-identity support paths are not unique")
    if inherited_paths & payload_paths:
        raise FreezeError("successor would mutate an inherited P2.84 source")
    if support_paths & {_pure(path) for path in planned.values()}:
        raise FreezeError("non-identity support leaked into SOURCE_KEYS")
    if payload_paths & support_paths:
        raise FreezeError("payload/support path partition overlaps")

    d1_paths = tuple(_pure(path) for path in D1_PRIVATE_MUTATION_PATHS)
    private_root = _pure(D1_PRIVATE_ROOT)
    if any(
        path.parts[: len(private_root.parts)] != private_root.parts
        for path in d1_paths
    ):
        raise FreezeError("D1 mutation escaped its frozen private root")

    candidate_paths = tuple(_pure(path) for path in planned.values())
    overlaps = tuple(
        (candidate.as_posix(), d1.as_posix())
        for candidate in candidate_paths
        for d1 in d1_paths
        if _overlap(candidate, d1)
    )
    if overlaps:
        raise FreezeError(f"candidate/D1 path overlap: {overlaps}")

    missing_payload = missing_payload_paths(root)
    missing_support = missing_support_paths(root)
    missing = tuple(sorted((*missing_payload, *missing_support)))
    inherited_receipts = validate_inherited_receipts(root)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": PROFILE,
        "inherited_contract_id": INHERITED_CONTRACT_ID,
        "inherited_receipts": inherited_receipts,
        "planned_contract_id": PLANNED_CONTRACT_ID,
        "candidate_requirements": [
            {"id": key, "requirement": value}
            for key, value in CANDIDATE_CHANGE_REQUIREMENTS
        ],
        "d1_requirements": [
            {"id": key, "requirement": value}
            for key, value in D1_CHANGE_REQUIREMENTS
        ],
        "source_key_counts": {
            "inherited": len(p284.SOURCE_KEYS),
            "inherited_direct": len(inherited),
            "generated": len(GENERATED_SOURCE_KEYS),
            "planned_payload": len(PAYLOAD_SOURCE_PATHS),
            "planned_total": len(PLANNED_SOURCE_KEYS),
            "bundle_bound_support": len(NON_IDENTITY_SUPPORT_PATHS),
        },
        "source_keys": list(source_key_rows()),
        "payload_source_paths": sorted(
            path.as_posix()
            for path in PAYLOAD_SOURCE_PATHS.values()
        ),
        "bundle_bound_support_paths": sorted(
            path.as_posix()
            for path in NON_IDENTITY_SUPPORT_PATHS.values()
        ),
        "d1_private_mutation_paths": [
            path.as_posix() for path in D1_PRIVATE_MUTATION_PATHS
        ],
        "candidate_d1_overlap_count": 0,
        "missing_payload_source_paths": list(missing_payload),
        "missing_bundle_bound_support_paths": list(missing_support),
        "missing_planned_paths": list(missing),
        "pre_intent_ready": not missing,
        "intent_derived": INTENT_DERIVED,
        "build_executed": BUILD_EXECUTED,
        "device_contact": DEVICE_CONTACT,
        "live_authorized": LIVE_AUTHORIZED,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[5],
    )
    parser.add_argument(
        "--require-pre-intent-ready",
        action="store_true",
        help="fail until every frozen successor overlay exists",
    )
    args = parser.parse_args()
    derived_paths = git_derived_changed_paths(
        args.repo_root,
        CHANGE_WINDOW_BASE_COMMIT,
    )
    change_window = validate_declared_change_set(
        derived_paths=derived_paths,
        declared_paths=STAGE_A_DECLARED_CHANGED_PATHS,
    )
    result = validate_freeze(args.repo_root.resolve())
    result["change_window"] = {
        "base_commit": CHANGE_WINDOW_BASE_COMMIT,
        **change_window,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_pre_intent_ready and not result["pre_intent_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
