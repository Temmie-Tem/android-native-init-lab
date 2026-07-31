#!/usr/bin/env python3
"""Fail-closed pre-intent P2.92 identity and change-window freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

import s22plus_fyg8_p290_change_freeze as git_freeze
import s22plus_fyg8_p292_identity_mutation_matrix as mutation
import s22plus_fyg8_p292_identity_tiers as identity
import s22plus_fyg8_p292_source_contract as p292


SCHEMA = "s22plus_fyg8_p292_change_closure_freeze_v1"
VERDICT = "PASS_P292_PRE_INTENT_IDENTITY_FREEZE_HOST_ONLY"
CHANGE_WINDOW_BASE_COMMIT = "0b994dd9fb0d5f38a546e10d831cd34d5804ca75"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False
STAGE_C_INDEPENDENT_REVIEW_COMPLETE = False
FINAL_WINDOW_CHANGED_PATHS = frozenset(
    {
        "GOAL.md",
        "docs/reports/"
        "S22PLUS_FYG8_P292_FINAL_IDENTITY_FREEZE_H0_2026-07-31.md",
        "tests/test_s22plus_fyg8_p292_contract.py",
        "workspace/public/src/scripts/revalidation/"
        "build_s22plus_fyg8_p292_candidate.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_source_contracts.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_boot_only_packager.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_build.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_build_repro_check.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_candidate_contract.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_candidate_intent.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_candidate_static_checker.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_change_freeze.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_e2_stock_closure.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_identity_mutation_matrix.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_identity_tiers.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_linked_audit.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_postbuild_linked_audit.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_pre_lto_qualification.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_model.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_source_contract.py",
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_userspace_build.py",
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p292_identity_mutation_matrix.py",
    }
)


class FreezeError(ValueError):
    pass


def _pure(path: str | Path | PurePosixPath) -> PurePosixPath:
    value = PurePosixPath(str(path))
    if (
        value.is_absolute()
        or not value.parts
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise FreezeError(
            f"path is not canonical repository-relative: {value}"
        )
    return value


def git_derived_changed_paths(root: Path) -> tuple[str, ...]:
    try:
        return git_freeze.git_derived_changed_paths(
            root, CHANGE_WINDOW_BASE_COMMIT
        )
    except git_freeze.FreezeError as exc:
        raise FreezeError(str(exc)) from exc


def validate_declared_change_set(
    derived_paths: tuple[str, ...],
) -> dict[str, Any]:
    derived = {_pure(path).as_posix() for path in derived_paths}
    declared = {_pure(path).as_posix() for path in FINAL_WINDOW_CHANGED_PATHS}
    missing = sorted(derived - declared)
    overdeclared = sorted(declared - derived)
    if missing or overdeclared:
        raise FreezeError(
            "declared/Git-derived change set mismatch: "
            f"missing_declarations={missing}; overdeclared={overdeclared}"
        )
    exact = sorted(derived)
    return {
        "base_commit": CHANGE_WINDOW_BASE_COMMIT,
        "git_derived_paths": exact,
        "declared_paths": exact,
        "exact_bidirectional_match": True,
        "verified": True,
    }


def source_key_rows() -> tuple[dict[str, str], ...]:
    generated_by_source = {
        source_key: artifact
        for artifact, source_key in (
            identity.GENERATED_PAYLOAD_SOURCE_KEYS.items()
        )
    }
    rows = []
    for key in sorted(identity.TIER1_SOURCE_KEYS):
        if key in identity.INHERITED_PAYLOAD_SOURCE_KEYS:
            path = (
                "inherited://p290/"
                + identity.INHERITED_PAYLOAD_SOURCE_KEYS[key]
            )
        elif key in identity.TIER1_DIRECT_PATHS:
            path = identity.TIER1_DIRECT_PATHS[key].as_posix()
        else:
            try:
                artifact = generated_by_source[key]
            except KeyError as exc:
                raise FreezeError(
                    f"P2.92 SOURCE_KEY has no route: {key}"
                ) from exc
            path = f"generated://p292/{artifact}"
        rows.append({"source_key": key, "path": path})
    return tuple(rows)


def _missing_direct_paths(root: Path) -> list[str]:
    paths = {
        *identity.TIER1_DIRECT_PATHS.values(),
        *identity.TIER2_DIRECT_PATHS.values(),
        *identity.TIER3_DIRECT_PATHS.values(),
    }
    return sorted(
        path.as_posix()
        for path in paths
        if not (root / path).is_file() or (root / path).is_symlink()
    )


def validate_freeze(root: Path) -> dict[str, Any]:
    identity_result = identity.validate()
    source, receipts = p292.source_receipts(root)
    matrix = mutation.run_matrix(root)
    missing = _missing_direct_paths(root)
    if (
        set(source) != set(p292.SOURCE_KEYS)
        or p292.SOURCE_KEYS != identity.TIER1_SOURCE_KEYS
        or len(source) != 93
        or identity_result.get("tier1_source_key_count") != 93
        or matrix.get("receipt_counts", {}).get("tier1") != 93
        or matrix.get("verdict") != mutation.VERDICT
    ):
        raise FreezeError("P2.92 Tier-1 identity closure differs")
    tier_paths = identity.path_tiers()
    all_paths = [
        path
        for name in identity.TIER_NAMES
        for path in tier_paths[name]
    ]
    if len(all_paths) != len(set(all_paths)):
        raise FreezeError("P2.92 direct path occurs in multiple tiers")
    rows = source_key_rows()
    if len(rows) != len(source) or {
        row["source_key"] for row in rows
    } != set(source):
        raise FreezeError("P2.92 SOURCE_KEY route rows differ")
    pre_intent_ready = not missing
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": p292.PROFILE,
        "planned_contract_id": p292.CONTRACT_ID,
        "source_key_count": len(source),
        "source_keys": list(rows),
        "source_receipts": receipts,
        "identity_descriptor_sha256": identity_result[
            "descriptor_sha256"
        ],
        "tier_receipt_counts": matrix["receipt_counts"],
        "tier_path_counts": identity_result["path_validation"][
            "tier_counts"
        ],
        "missing_direct_paths": missing,
        "changed_keys": [],
        "pre_intent_ready": pre_intent_ready,
        "stage_c_independent_review_complete": (
            STAGE_C_INDEPENDENT_REVIEW_COMPLETE
        ),
        "full_lto_ready": (
            pre_intent_ready and STAGE_C_INDEPENDENT_REVIEW_COMPLETE
        ),
        "intent_derived": INTENT_DERIVED,
        "build_executed": BUILD_EXECUTED,
        "device_contact": DEVICE_CONTACT,
        "live_authorized": LIVE_AUTHORIZED,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[5],
    )
    parser.add_argument("--require-pre-intent-ready", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        change_window = validate_declared_change_set(
            git_derived_changed_paths(root)
        )
        result = validate_freeze(root)
        result["change_window"] = change_window
    except (
        FreezeError,
        identity.IdentityTierError,
        mutation.MutationMatrixError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_pre_intent_ready and not result["pre_intent_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
