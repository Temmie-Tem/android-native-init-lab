#!/usr/bin/env python3
"""Fail-closed pre-intent P2.98 identity and worktree freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

import s22plus_fyg8_p298_identity_tiers as identity
import s22plus_fyg8_p298_source_contract as p298


SCHEMA = "s22plus_fyg8_p298_change_closure_freeze_v1"
VERDICT = "PASS_P298_PRE_INTENT_IDENTITY_FREEZE_HOST_ONLY"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False
P = "workspace/public/src/scripts/revalidation/"
FINAL_WINDOW_CHANGED_PATHS = frozenset(
    {
        "GOAL.md",
        "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md",
        "docs/reports/S22PLUS_FYG8_P298_GADGET_START_EVENT_IMPLEMENTATION_H0_2026-08-03.md",
        "docs/reports/S22PLUS_FYG8_P298_EXECUTION_CRITICAL_INDEPENDENT_REVIEW_2026-08-03.json",
        "tests/test_s22plus_fyg8_p298_contract.py",
        P + "build_s22plus_fyg8_p298_candidate.py",
        P + "s22plus_fyg8_p298_boot_only_packager.py",
        P + "s22plus_fyg8_p298_build.py",
        P + "s22plus_fyg8_p298_build_repro_check.py",
        P + "s22plus_fyg8_p298_candidate_contract.py",
        P + "s22plus_fyg8_p298_candidate_intent.py",
        P + "s22plus_fyg8_p298_candidate_static_checker.py",
        P + "s22plus_fyg8_p298_change_freeze.py",
        P + "s22plus_fyg8_p298_e2_stock_closure.py",
        P + "s22plus_fyg8_p298_identity_tiers.py",
        P + "s22plus_fyg8_p298_linked_audit.py",
        P + "s22plus_fyg8_p298_postbuild_linked_audit.py",
        P + "s22plus_fyg8_p298_pre_lto_qualification.py",
        P + "s22plus_fyg8_p298_source_contract.py",
        P + "s22plus_fyg8_p298_telemetry_closure.py",
        P + "s22plus_fyg8_p298_telemetry_decoder.py",
        P + "s22plus_fyg8_p298_telemetry_generator.py",
        P + "s22plus_fyg8_p298_telemetry_model.py",
        P + "s22plus_fyg8_p298_telemetry_spec.py",
        P + "s22plus_fyg8_p298_telemetry_transform.py",
        P + "s22plus_fyg8_p298_userspace_build.py",
        P + "test_s22plus_fyg8_p298_telemetry.py",
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


def _foreign_target_path(path: str) -> bool:
    return (
        path == "GOAL_A90.md"
        or "A90" in Path(path).name
        or path.startswith("workspace/public/src/scripts/server-distro/a90_")
        or path.startswith("tests/test_a90_")
        or path.startswith("tests/test_server_distro_a90_")
    )


def git_derived_changed_paths(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise FreezeError(
            completed.stderr.decode("utf-8", "replace").strip()
        )
    paths = []
    for item in completed.stdout.split(b"\0"):
        if not item:
            continue
        text = item.decode("utf-8", "surrogateescape")
        path = text[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if not _foreign_target_path(path):
            paths.append(path)
    return tuple(sorted(set(paths)))


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
        "git_derived_paths": exact,
        "declared_paths": exact,
        "foreign_target_paths_excluded": True,
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
            path = "inherited://p296/" + identity.INHERITED_PAYLOAD_SOURCE_KEYS[key]
        elif key in identity.TIER1_DIRECT_PATHS:
            path = identity.TIER1_DIRECT_PATHS[key].as_posix()
        else:
            try:
                artifact = generated_by_source[key]
            except KeyError as exc:
                raise FreezeError(f"P2.98 SOURCE_KEY has no route: {key}") from exc
            path = f"generated://p298/{artifact}"
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
    before, before_receipts = p298.source_receipts(root)
    identity_result = identity.validate()
    tier2 = identity.tier2_materials(root)
    tier3 = identity.tier3_materials(root)
    after, after_receipts = p298.source_receipts(root)
    changed_keys = sorted(
        key for key in set(before) | set(after) if before.get(key) != after.get(key)
    )
    missing = _missing_direct_paths(root)
    expected_count = len(identity.TIER1_SOURCE_KEYS)
    if (
        set(before) != set(p298.SOURCE_KEYS)
        or before != after
        or before_receipts != after_receipts
        or p298.SOURCE_KEYS != identity.TIER1_SOURCE_KEYS
        or len(before) != expected_count
        or identity_result.get("tier1_source_key_count") != expected_count
        or changed_keys
    ):
        raise FreezeError("P2.98 Tier-1 identity closure differs")
    rows = source_key_rows()
    if len(rows) != len(before) or {row["source_key"] for row in rows} != set(before):
        raise FreezeError("P2.98 SOURCE_KEY route rows differ")
    pre_intent_ready = not missing
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": p298.PROFILE,
        "planned_contract_id": p298.CONTRACT_ID,
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
