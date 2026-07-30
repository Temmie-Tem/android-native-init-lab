#!/usr/bin/env python3
"""Fail-closed pre-intent P2.90 change-closure freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import s22plus_fyg8_p288_change_freeze as inherited_freeze
import s22plus_fyg8_p288_source_contract as p288
import s22plus_fyg8_p290_source_contract as p290


SCHEMA = "s22plus_fyg8_p290_change_closure_freeze_v1"
VERDICT = "PASS_P290_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY"
PROFILE = p290.PROFILE
INHERITED_CONTRACT_ID = p288.CONTRACT_ID
PLANNED_CONTRACT_ID = p290.CONTRACT_ID
P288_FROZEN_RUN_ID = "20bb4d70842fe7ae1a6bd0aec261d722"
P288_FROZEN_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288/"
    "intent/candidate-intent.json"
)
CHANGE_WINDOW_BASE_COMMIT = "277ab77e6f1eeef4b62647f9b3f4dcb77c8e0491"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False

PAYLOAD_SOURCE_PATHS = MappingProxyType(dict(p290.OVERLAY_SOURCE_PATHS))
GENERATED_OVERLAY_KEYS = frozenset(p290.GENERATED_OVERLAY_KEYS)
NON_IDENTITY_SUPPORT_PATHS = MappingProxyType(
    {
        "p290_change_freeze": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_change_freeze.py"
        ),
        "p290_implementation_report": Path(
            "docs/reports/"
            "S22PLUS_FYG8_P290_CHECKED_PARK_ADJACENT_CORRIDOR_H0_"
            "2026-07-31.md"
        ),
        "p290_candidate_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_candidate_contract.py"
        ),
        "p290_source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contracts.py"
        ),
        "p290_build_repro_check": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_build_repro_check.py"
        ),
        "p290_candidate_static_checker": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_candidate_static_checker.py"
        ),
        "p290_e2_stock_closure": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_e2_stock_closure.py"
        ),
        "p290_linked_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_linked_audit.py"
        ),
        "p290_postbuild_linked_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_postbuild_linked_audit.py"
        ),
        "p290_pre_lto_qualification": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_pre_lto_qualification.py"
        ),
        "p290_decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_e1_decoder.py"
        ),
        "p290_latest_stage_model": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_latest_stage_model.py"
        ),
        "p290_predesign_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p290_predesign_audit.py"
        ),
        "p290_typed_evidence": Path(
            "workspace/public/src/scripts/revalidation/"
            "device_action_f1_evidence_v2.py"
        ),
        "p290_process_v2_host_core": Path(
            "workspace/public/src/scripts/revalidation/"
            "device_action_f1_v2.py"
        ),
    }
)
GOVERNANCE_PATHS = frozenset(
    {
        Path("GOAL.md"),
        Path("tests/test_s22plus_fyg8_p290_contract.py"),
        Path("tests/test_s22plus_fyg8_p290_predesign_audit.py"),
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
GENERATED_SOURCE_KEYS = frozenset(
    (
        *inherited_freeze.GENERATED_SOURCE_KEYS,
        *GENERATED_OVERLAY_KEYS,
    )
)
PLANNED_SOURCE_KEYS = frozenset(
    (
        *p288.SOURCE_KEYS,
        *PAYLOAD_SOURCE_PATHS,
        *GENERATED_OVERLAY_KEYS,
    )
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
    paths = inherited_freeze.planned_direct_source_paths()
    expected = p288.SOURCE_KEYS - inherited_freeze.GENERATED_SOURCE_KEYS
    if set(paths) != expected:
        raise FreezeError("P2.88 direct SOURCE_KEY inventory drifted")
    return paths


def validate_inherited_receipts(root: Path) -> dict[str, Any]:
    shared = p290.shared_input_root(root)
    path = shared / P288_FROZEN_INTENT
    if path.is_symlink() or not path.is_file():
        raise FreezeError("frozen P2.88 intent is missing or indirect")
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FreezeError("frozen P2.88 intent is not ASCII JSON") from exc
    preimage = value.get("identity_preimage")
    expected = (
        preimage.get("sources") if isinstance(preimage, dict) else None
    )
    if (
        value.get("run_id") != P288_FROZEN_RUN_ID
        or value.get("source_contract_id") != p288.CONTRACT_ID
        or not isinstance(preimage, dict)
        or preimage.get("source_contract_id") != p288.CONTRACT_ID
        or not isinstance(expected, dict)
        or len(expected) != 83
    ):
        raise FreezeError("frozen P2.88 intent identity is invalid")
    _source, actual = p288.source_receipts(shared)
    changed = tuple(
        sorted(
            key
            for key in set(expected) | set(actual)
            if expected.get(key) != actual.get(key)
        )
    )
    if changed:
        raise FreezeError(
            "frozen P2.88 source receipts changed: "
            + ",".join(changed)
        )
    return {
        "intent_path": P288_FROZEN_INTENT.as_posix(),
        "run_id": P288_FROZEN_RUN_ID,
        "source_contract_id": p288.CONTRACT_ID,
        "receipt_count": len(actual),
        "changed_keys": [],
        "verified": True,
    }


def planned_direct_source_paths() -> dict[str, Path]:
    paths = inherited_direct_source_paths()
    if set(paths) & set(PAYLOAD_SOURCE_PATHS):
        raise FreezeError("planned P2.90 SOURCE_KEY collides with P2.88")
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


def git_derived_changed_paths(
    root: Path, base_commit: str = CHANGE_WINDOW_BASE_COMMIT
) -> tuple[str, ...]:
    try:
        return inherited_freeze.git_derived_changed_paths(root, base_commit)
    except inherited_freeze.FreezeError as exc:
        raise FreezeError(str(exc)) from exc


def validate_declared_change_set(
    *,
    derived_paths: tuple[str, ...],
    declared_paths: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    derived = {_pure(PurePosixPath(path)) for path in derived_paths}
    declared = {_pure(PurePosixPath(path)) for path in declared_paths}
    missing = derived - declared
    overdeclared = declared - derived
    if missing or overdeclared:
        raise FreezeError(
            "declared/Git-derived change set mismatch: "
            f"missing_declarations={sorted(x.as_posix() for x in missing)}; "
            f"overdeclared={sorted(x.as_posix() for x in overdeclared)}"
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
            "Git-derived change is outside the frozen window: "
            f"{sorted(path.as_posix() for path in unexpected)}"
        )
    exact = tuple(sorted(path.as_posix() for path in derived))
    return {"git_derived_paths": exact, "declared_paths": exact}


def validate_freeze(root: Path) -> dict[str, Any]:
    if len(p288.SOURCE_KEYS) != 83:
        raise FreezeError("P2.88 SOURCE_KEY count drifted")
    if p290.SOURCE_KEYS != PLANNED_SOURCE_KEYS:
        raise FreezeError("implemented P2.90 SOURCE_KEYS differ from freeze")
    inherited = inherited_direct_source_paths()
    planned = planned_direct_source_paths()
    if (
        len(inherited_freeze.GENERATED_SOURCE_KEYS) != 9
        or len(GENERATED_OVERLAY_KEYS) != 3
        or len(GENERATED_SOURCE_KEYS) != 12
        or len(inherited) != 74
        or len(PAYLOAD_SOURCE_PATHS) != 8
        or len(NON_IDENTITY_SUPPORT_PATHS) != 15
        or len(PLANNED_SOURCE_KEYS) != 94
        or len(planned) != 82
    ):
        raise FreezeError("P2.90 SOURCE_KEY partition drifted")

    inherited_paths = {_pure(path) for path in inherited.values()}
    payload_paths = {
        _pure(path) for path in PAYLOAD_SOURCE_PATHS.values()
    }
    support_paths = {
        _pure(path) for path in NON_IDENTITY_SUPPORT_PATHS.values()
    }
    if (
        len(payload_paths) != len(PAYLOAD_SOURCE_PATHS)
        or len(support_paths) != len(NON_IDENTITY_SUPPORT_PATHS)
        or inherited_paths & payload_paths
        or support_paths & {_pure(path) for path in planned.values()}
        or payload_paths & support_paths
    ):
        raise FreezeError("P2.90 payload/support/source partition overlaps")

    missing_payload = tuple(
        path.as_posix()
        for path in PAYLOAD_SOURCE_PATHS.values()
        if not (root / path).is_file()
    )
    missing_support = tuple(
        path.as_posix()
        for path in NON_IDENTITY_SUPPORT_PATHS.values()
        if not (root / path).is_file()
    )
    inherited_receipts = validate_inherited_receipts(root)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": PROFILE,
        "inherited_contract_id": INHERITED_CONTRACT_ID,
        "inherited_receipts": inherited_receipts,
        "planned_contract_id": PLANNED_CONTRACT_ID,
        "source_key_counts": {
            "inherited": len(p288.SOURCE_KEYS),
            "inherited_direct": len(inherited),
            "inherited_generated": len(
                inherited_freeze.GENERATED_SOURCE_KEYS
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
        "pre_intent_ready": not missing_payload and not missing_support,
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
    parser.add_argument("--require-pre-intent-ready", action="store_true")
    args = parser.parse_args()
    derived = git_derived_changed_paths(
        args.repo_root, CHANGE_WINDOW_BASE_COMMIT
    )
    exact = validate_declared_change_set(
        derived_paths=derived,
        declared_paths=DECLARED_CHANGED_PATHS,
    )
    result = validate_freeze(args.repo_root.resolve())
    result["change_window"] = {
        "base_commit": CHANGE_WINDOW_BASE_COMMIT,
        **exact,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return (
        1
        if args.require_pre_intent_ready
        and not result["pre_intent_ready"]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
