#!/usr/bin/env python3
"""Fail-closed pre-intent P2.96 identity and change-window freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

import s22plus_fyg8_p290_change_freeze as git_freeze
import s22plus_fyg8_p296_identity_tiers as identity
import s22plus_fyg8_p296_source_contract as p296


SCHEMA = "s22plus_fyg8_p296_change_closure_freeze_v1"
VERDICT = "PASS_P296_PRE_INTENT_IDENTITY_FREEZE_HOST_ONLY"
CHANGE_WINDOW_BASE_COMMIT = "8419e59b5657d1ed0ef74bd627ef3459ed219aa9"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False
P = "workspace/public/src/scripts/revalidation/"
FINAL_WINDOW_CHANGED_PATHS = frozenset(
    {
        "GOAL.md",
        "docs/archive/roadmaps/GOAL_THROUGH_P294_MODULE_DELIVERY_2026-08-02.md",
        "docs/reports/S22PLUS_FYG8_P296_BUILTIN_DWC3_TELEMETRY_IMPLEMENTATION_H0_2026-08-02.md",
        "tests/test_s22plus_fyg8_p296_contract.py",
        P + "build_s22plus_fyg8_p296_candidate.py",
        P + "s22plus_fyg8_p286_source_contracts.py",
        P + "s22plus_fyg8_p296_boot_only_packager.py",
        P + "s22plus_fyg8_p296_build.py",
        P + "s22plus_fyg8_p296_build_repro_check.py",
        P + "s22plus_fyg8_p296_candidate_contract.py",
        P + "s22plus_fyg8_p296_candidate_intent.py",
        P + "s22plus_fyg8_p296_candidate_static_checker.py",
        P + "s22plus_fyg8_p296_change_freeze.py",
        P + "s22plus_fyg8_p296_e2_stock_closure.py",
        P + "s22plus_fyg8_p296_identity_tiers.py",
        P + "s22plus_fyg8_p296_linked_audit.py",
        P + "s22plus_fyg8_p296_postbuild_linked_audit.py",
        P + "s22plus_fyg8_p296_pre_lto_qualification.py",
        P + "s22plus_fyg8_p296_source_contract.py",
        P + "s22plus_fyg8_p296_telemetry_closure.py",
        P + "s22plus_fyg8_p296_telemetry_decoder.py",
        P + "s22plus_fyg8_p296_telemetry_generator.py",
        P + "s22plus_fyg8_p296_telemetry_model.py",
        P + "s22plus_fyg8_p296_telemetry_spec.py",
        P + "s22plus_fyg8_p296_telemetry_transform.py",
        P + "s22plus_fyg8_p296_userspace_build.py",
        P + "test_s22plus_fyg8_p296_telemetry.py",
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
        raise FreezeError(f"path is not canonical repository-relative: {value}")
    return value


def git_derived_changed_paths(root: Path) -> tuple[str, ...]:
    try:
        return git_freeze.git_derived_changed_paths(root, CHANGE_WINDOW_BASE_COMMIT)
    except git_freeze.FreezeError as exc:
        raise FreezeError(str(exc)) from exc


def validate_declared_change_set(derived_paths: tuple[str, ...]) -> dict[str, Any]:
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
        for artifact, source_key in identity.GENERATED_PAYLOAD_SOURCE_KEYS.items()
    }
    rows = []
    for key in sorted(identity.TIER1_SOURCE_KEYS):
        if key in identity.INHERITED_PAYLOAD_SOURCE_KEYS:
            path = "inherited://p294/" + identity.INHERITED_PAYLOAD_SOURCE_KEYS[key]
        elif key in identity.TIER1_DIRECT_PATHS:
            path = identity.TIER1_DIRECT_PATHS[key].as_posix()
        else:
            try:
                artifact = generated_by_source[key]
            except KeyError as exc:
                raise FreezeError(f"P2.96 SOURCE_KEY has no route: {key}") from exc
            path = f"generated://p296/{artifact}"
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
    before, before_receipts = p296.source_receipts(root)
    identity_result = identity.validate()
    tier2 = identity.tier2_materials(root)
    tier3 = identity.tier3_materials(root)
    after, after_receipts = p296.source_receipts(root)
    changed_keys = sorted(
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    )
    missing = _missing_direct_paths(root)
    expected_count = len(identity.TIER1_SOURCE_KEYS)
    if (
        set(before) != set(p296.SOURCE_KEYS)
        or before != after
        or before_receipts != after_receipts
        or p296.SOURCE_KEYS != identity.TIER1_SOURCE_KEYS
        or len(before) != expected_count
        or identity_result.get("tier1_source_key_count") != expected_count
        or changed_keys
    ):
        raise FreezeError("P2.96 Tier-1 identity closure differs")
    rows = source_key_rows()
    if len(rows) != len(before) or {row["source_key"] for row in rows} != set(before):
        raise FreezeError("P2.96 SOURCE_KEY route rows differ")
    pre_intent_ready = not missing
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": p296.PROFILE,
        "planned_contract_id": p296.CONTRACT_ID,
        "source_key_count": len(before),
        "source_keys": list(rows),
        "source_receipts": before_receipts,
        "identity_descriptor_sha256": identity_result["descriptor_sha256"],
        "tier_receipt_counts": {
            "tier1": len(before),
            "tier2": len(tier2),
            "tier3": len(tier3),
        },
        "missing_direct_paths": missing,
        "changed_keys": changed_keys,
        "pre_intent_ready": pre_intent_ready,
        "full_lto_ready": pre_intent_ready,
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
        change_window = validate_declared_change_set(git_derived_changed_paths(root))
        result = validate_freeze(root)
        result["change_window"] = change_window
    except (FreezeError, identity.IdentityTierError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_pre_intent_ready and not result["pre_intent_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
