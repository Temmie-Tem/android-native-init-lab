#!/usr/bin/env python3
"""Fail-closed pre-intent P2.88 change-closure freeze.

This module performs host-only validation.  It derives no intent, performs no
build, creates no candidate, and grants no device authority.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import s22plus_fyg8_p286_change_freeze as p286_freeze
import s22plus_fyg8_p286_source_contract as p286
import s22plus_fyg8_p288_source_contract as p288


SCHEMA = "s22plus_fyg8_p288_change_closure_freeze_v1"
VERDICT = "PASS_P288_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY"
PROFILE = p288.PROFILE
INHERITED_CONTRACT_ID = p286.CONTRACT_ID
PLANNED_CONTRACT_ID = p288.CONTRACT_ID
P286_FROZEN_RUN_ID = "c6cde593033d6f1be93f82c8ff5a81e8"
P286_FROZEN_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p286_v1/"
    "intent/candidate-intent.json"
)
CHANGE_WINDOW_BASE_COMMIT = "e1daa7fe7772c42a8b77830ea7d051a772b47069"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False

# Only these new direct inputs can affect P2.88 boot.img bytes.  The four
# additional generated keys below are also identity inputs, but have no
# repository path of their own.
PAYLOAD_SOURCE_PATHS = MappingProxyType(dict(p288.OVERLAY_SOURCE_PATHS))
GENERATED_OVERLAY_KEYS = frozenset(p288.GENERATED_OVERLAY_KEYS)

# These files validate, decode, register, or report the candidate.  They cannot
# change boot.img bytes and are deliberately excluded from SOURCE_KEYS.  The
# final Process-v2 approval bundle binds their bytes instead.
NON_IDENTITY_SUPPORT_PATHS = MappingProxyType(
    {
        "p288_change_freeze": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_change_freeze.py"
        ),
        "p288_implementation_report": Path(
            "docs/reports/"
            "S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_IMPLEMENTATION_H0_"
            "2026-07-30.md"
        ),
        "p288_candidate_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_candidate_contract.py"
        ),
        "p288_source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contracts.py"
        ),
        "p288_build_repro_check": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_build_repro_check.py"
        ),
        "p288_candidate_static_checker": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_candidate_static_checker.py"
        ),
        "p288_e2_stock_closure": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_e2_stock_closure.py"
        ),
        "p288_linked_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_linked_audit.py"
        ),
        "p288_pre_lto_qualification": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_pre_lto_qualification.py"
        ),
        "p288_decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_e1_decoder.py"
        ),
        "p288_latest_stage_model": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p288_latest_stage_model.py"
        ),
        "p288_typed_evidence": Path(
            "workspace/public/src/scripts/revalidation/"
            "device_action_f1_evidence_v2.py"
        ),
        "p288_process_v2_host_core": Path(
            "workspace/public/src/scripts/revalidation/"
            "device_action_f1_v2.py"
        ),
    }
)

GOVERNANCE_PATHS = frozenset(
    {
        Path("GOAL.md"),
        Path("tests/test_s22plus_fyg8_p288_contract.py"),
    }
)
DECLARED_CHANGED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (
            *GOVERNANCE_PATHS,
            *PAYLOAD_SOURCE_PATHS.values(),
            *NON_IDENTITY_SUPPORT_PATHS.values(),
        )
    )
)

CANDIDATE_CHANGE_REQUIREMENTS = (
    (
        "pair-indexed-generation",
        "bind every generation to one exact stage/item_index pair and preserve "
        "the proven P2.86 prefix through generation 88",
    ),
    (
        "mechanical-publication-order",
        "derive runtime position labels from one descriptor and reject "
        "removed, reordered, duplicated, or renamed publication calls",
    ),
    (
        "early-snapshot-removal",
        "dispatch and classify the bounded restart helper before optional "
        "trace enrichment",
    ),
    (
        "helper-return-attribution",
        "publish helper-returned before child, parent, or UDC readback",
    ),
    (
        "active-producer-route-equality",
        "require exact bidirectional equality between declared diagnostic "
        "tuples and active production routes",
    ),
    (
        "silence-park-prohibition",
        "route every park through exact or reserved unclassified evidence",
    ),
    (
        "finite-publication-bound",
        "make sequence length 103 the exact success-path publication bound "
        "and reject every post-terminal transition",
    ),
    (
        "evidence-multiplicity-preservation",
        "keep one retained record with two adjacent slots equal to one "
        "minimum candidate boot",
    ),
    (
        "full-lto-a-path-gate",
        "reject private or absolute clang-resource path leaks after A and "
        "before starting B",
    ),
)

GENERATED_SOURCE_KEYS = frozenset(
    (*p286_freeze.GENERATED_SOURCE_KEYS, *GENERATED_OVERLAY_KEYS)
)
PLANNED_SOURCE_KEYS = frozenset(
    (*p286.SOURCE_KEYS, *PAYLOAD_SOURCE_PATHS, *GENERATED_OVERLAY_KEYS)
)


class FreezeError(ValueError):
    pass


def _pure(path: Path | PurePosixPath) -> PurePosixPath:
    value = PurePosixPath(path.as_posix())
    if value.is_absolute() or ".." in value.parts or "." in value.parts:
        raise FreezeError(
            f"path is not canonical repository-relative: {value}"
        )
    return value


def inherited_direct_source_paths() -> dict[str, Path]:
    paths = dict(p286.COMMON_SOURCE_PATHS)
    expected = p286.SOURCE_KEYS - p286_freeze.GENERATED_SOURCE_KEYS
    if set(paths) != expected:
        raise FreezeError("P2.86 direct SOURCE_KEY inventory drifted")
    return paths


def validate_inherited_receipts(root: Path) -> dict[str, Any]:
    path = root / P286_FROZEN_INTENT
    if path.is_symlink() or not path.is_file():
        raise FreezeError("frozen P2.86 intent is missing or indirect")
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FreezeError("frozen P2.86 intent is not ASCII JSON") from exc
    preimage = value.get("identity_preimage")
    expected = (
        preimage.get("sources") if isinstance(preimage, dict) else None
    )
    if (
        value.get("run_id") != P286_FROZEN_RUN_ID
        or value.get("source_contract_id") != p286.CONTRACT_ID
        or not isinstance(preimage, dict)
        or preimage.get("source_contract_id") != p286.CONTRACT_ID
        or not isinstance(expected, dict)
        or len(expected) != 70
    ):
        raise FreezeError("frozen P2.86 intent identity is invalid")
    _source, actual = p286.source_receipts(root)
    changed = tuple(
        sorted(
            key
            for key in set(expected) | set(actual)
            if expected.get(key) != actual.get(key)
        )
    )
    if changed:
        raise FreezeError(
            "frozen P2.86 source receipts changed: "
            + ",".join(changed)
        )
    return {
        "intent_path": P286_FROZEN_INTENT.as_posix(),
        "run_id": P286_FROZEN_RUN_ID,
        "source_contract_id": p286.CONTRACT_ID,
        "receipt_count": len(actual),
        "changed_keys": [],
        "verified": True,
    }


def planned_direct_source_paths() -> dict[str, Path]:
    paths = inherited_direct_source_paths()
    if set(paths) & set(PAYLOAD_SOURCE_PATHS):
        raise FreezeError("planned payload SOURCE_KEY collides with P2.86")
    paths.update(PAYLOAD_SOURCE_PATHS)
    expected = PLANNED_SOURCE_KEYS - GENERATED_SOURCE_KEYS
    if set(paths) != expected:
        raise FreezeError("planned direct SOURCE_KEY inventory drifted")
    return paths


def source_key_rows() -> tuple[dict[str, str], ...]:
    direct = planned_direct_source_paths()
    return tuple(
        {
            "source_key": key,
            "path": (
                f"generated://{key}"
                if key in GENERATED_SOURCE_KEYS
                else direct[key].as_posix()
            ),
        }
        for key in sorted(PLANNED_SOURCE_KEYS)
    )


def _missing_paths(root: Path, paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        path.as_posix()
        for path in paths
        if not (root / path).is_file()
    )


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
        stderr = completed.stderr.decode(
            "utf-8", errors="replace"
        ).strip()
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
            raise FreezeError(
                "unexpected git status --porcelain=v1 -z record"
            )
        status = record[:2]
        paths.add(_decode_git_path(record[3:]))
        if b"R" in status or b"C" in status:
            if index >= len(fields) or not fields[index]:
                raise FreezeError("truncated git rename/copy status record")
            paths.add(_decode_git_path(fields[index]))
            index += 1
    return paths


def git_derived_changed_paths(
    root: Path, base_commit: str
) -> tuple[str, ...]:
    root = root.resolve()
    top = Path(
        _decode_git_path(
            _run_git(root, "rev-parse", "--show-toplevel")
        ).strip()
    ).resolve()
    if top != root:
        raise FreezeError(
            f"repo root mismatch: expected {root}, git reports {top}"
        )
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
            *GOVERNANCE_PATHS,
        )
    }
    unexpected = derived - allowed
    if unexpected:
        raise FreezeError(
            "Git-derived change is outside the frozen change window: "
            f"{sorted(path.as_posix() for path in unexpected)}"
        )
    exact = tuple(sorted(path.as_posix() for path in derived))
    return {"git_derived_paths": exact, "declared_paths": exact}


def validate_freeze(root: Path) -> dict[str, Any]:
    if len(p286.SOURCE_KEYS) != 70:
        raise FreezeError("P2.86 SOURCE_KEY count drifted")
    if p288.SOURCE_KEYS != PLANNED_SOURCE_KEYS:
        raise FreezeError("implemented P2.88 SOURCE_KEYS differ from freeze")
    inherited = inherited_direct_source_paths()
    planned = planned_direct_source_paths()
    if len(p286_freeze.GENERATED_SOURCE_KEYS) != 5:
        raise FreezeError("P2.86 generated SOURCE_KEY partition drifted")
    if len(GENERATED_OVERLAY_KEYS) != 4:
        raise FreezeError("P2.88 generated overlay count drifted")
    if len(GENERATED_SOURCE_KEYS) != 9:
        raise FreezeError("P2.88 generated SOURCE_KEY count drifted")
    if len(inherited) != 65:
        raise FreezeError("P2.86 direct SOURCE_KEY count drifted")
    if len(PAYLOAD_SOURCE_PATHS) != 9:
        raise FreezeError("P2.88 direct payload-source count drifted")
    if len(NON_IDENTITY_SUPPORT_PATHS) != 13:
        raise FreezeError("P2.88 non-identity support count drifted")
    if len(PLANNED_SOURCE_KEYS) != 83 or len(planned) != 74:
        raise FreezeError("P2.88 SOURCE_KEY partition drifted")

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
        raise FreezeError("successor would mutate an inherited P2.86 source")
    if support_paths & {_pure(path) for path in planned.values()}:
        raise FreezeError("non-identity support leaked into SOURCE_KEYS")
    if payload_paths & support_paths:
        raise FreezeError("payload/support path partition overlaps")

    missing_payload = _missing_paths(
        root, tuple(PAYLOAD_SOURCE_PATHS.values())
    )
    missing_support = _missing_paths(
        root, tuple(NON_IDENTITY_SUPPORT_PATHS.values())
    )
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
        "source_key_counts": {
            "inherited": len(p286.SOURCE_KEYS),
            "inherited_direct": len(inherited),
            "inherited_generated": len(
                p286_freeze.GENERATED_SOURCE_KEYS
            ),
            "overlay_direct": len(PAYLOAD_SOURCE_PATHS),
            "overlay_generated": len(GENERATED_OVERLAY_KEYS),
            "generated_total": len(GENERATED_SOURCE_KEYS),
            "planned_direct": len(planned),
            "planned_total": len(PLANNED_SOURCE_KEYS),
            "bundle_bound_support": len(NON_IDENTITY_SUPPORT_PATHS),
        },
        "source_keys": list(source_key_rows()),
        "payload_source_paths": sorted(
            path.as_posix() for path in PAYLOAD_SOURCE_PATHS.values()
        ),
        "bundle_bound_support_paths": sorted(
            path.as_posix()
            for path in NON_IDENTITY_SUPPORT_PATHS.values()
        ),
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
        args.repo_root, CHANGE_WINDOW_BASE_COMMIT
    )
    change_window = validate_declared_change_set(
        derived_paths=derived_paths,
        declared_paths=DECLARED_CHANGED_PATHS,
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
