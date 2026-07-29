#!/usr/bin/env python3
"""Pre-intent P2.86 candidate/D1 change-closure freeze.

This module is host-only data and validation.  It creates no candidate,
derives no intent, performs no build, and grants no device authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import s22plus_fyg8_p282_source_contract as p282
import s22plus_fyg8_p284_source_contract as p284


SCHEMA = "s22plus_fyg8_p286_change_closure_freeze_v1"
VERDICT = "PASS_P286_PRE_INTENT_CHANGE_CLOSURE_FROZEN_HOST_ONLY"
PROFILE = p284.PROFILE
INHERITED_CONTRACT_ID = p284.CONTRACT_ID
PLANNED_CONTRACT_ID = "s22plus-fyg8-p286-parent-tail-bounded-restart-v1"
INTENT_DERIVED = False
BUILD_EXECUTED = False
DEVICE_CONTACT = False
LIVE_AUTHORIZED = False

# Every file created or changed for the successor candidate must be one of
# these new versioned overlays and must become a SOURCE_KEY before intent
# derivation.  Existing P2.84 direct sources are inherited byte-for-byte and
# are forbidden mutation targets.
PLANNED_OVERLAY_SOURCE_PATHS = MappingProxyType(
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
        "p286_contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_contract_spec.py"
        ),
        "p286_source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contract.py"
        ),
        "p286_source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_source_contracts.py"
        ),
        "p286_candidate_intent": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_candidate_intent.py"
        ),
        "p286_candidate_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_candidate_contract.py"
        ),
        "p286_build": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_build.py"
        ),
        "p286_build_repro_check": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_build_repro_check.py"
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

CANDIDATE_CHANGE_REQUIREMENTS = (
    (
        "parent-runtime-status-gate",
        "wait for exact parent suspended on the existing stop deadline",
    ),
    (
        "bounded-helper-reap",
        "publish before reap; use WNOHANG plus an auxiliary deadline and "
        "classify an unreaped child",
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
        "bind every candidate implementation, verifier, decoder, builder, "
        "packager, static checker, and freeze document before intent",
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
    (*p284.SOURCE_KEYS, *PLANNED_OVERLAY_SOURCE_PATHS)
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


def planned_direct_source_paths() -> dict[str, Path]:
    paths = inherited_direct_source_paths()
    if set(paths) & set(PLANNED_OVERLAY_SOURCE_PATHS):
        raise FreezeError("planned overlay SOURCE_KEY collides with P2.84")
    paths.update(PLANNED_OVERLAY_SOURCE_PATHS)
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


def missing_planned_overlays(root: Path) -> tuple[str, ...]:
    return tuple(
        path.as_posix()
        for path in PLANNED_OVERLAY_SOURCE_PATHS.values()
        if not (root / path).is_file()
    )


def validate_declared_mutations(
    *,
    candidate_paths: tuple[str, ...] = (),
    d1_paths: tuple[str, ...] = (),
) -> dict[str, tuple[str, ...]]:
    allowed_candidate = {
        _pure(path) for path in PLANNED_OVERLAY_SOURCE_PATHS.values()
    }
    allowed_d1 = {_pure(path) for path in D1_PRIVATE_MUTATION_PATHS}
    actual_candidate = {_pure(PurePosixPath(path)) for path in candidate_paths}
    actual_d1 = {_pure(PurePosixPath(path)) for path in d1_paths}
    unexpected_candidate = actual_candidate - allowed_candidate
    unexpected_d1 = actual_d1 - allowed_d1
    if unexpected_candidate:
        raise FreezeError(
            "candidate mutation is outside frozen overlays: "
            f"{sorted(path.as_posix() for path in unexpected_candidate)}"
        )
    if unexpected_d1:
        raise FreezeError(
            "D1 mutation is outside frozen private files: "
            f"{sorted(path.as_posix() for path in unexpected_d1)}"
        )
    overlaps = tuple(
        (candidate.as_posix(), d1.as_posix())
        for candidate in actual_candidate
        for d1 in actual_d1
        if _overlap(candidate, d1)
    )
    if overlaps:
        raise FreezeError(f"declared candidate/D1 mutation overlap: {overlaps}")
    return {
        "candidate_paths": tuple(
            sorted(path.as_posix() for path in actual_candidate)
        ),
        "d1_paths": tuple(sorted(path.as_posix() for path in actual_d1)),
    }


def validate_freeze(root: Path) -> dict[str, Any]:
    if len(p284.SOURCE_KEYS) != 60:
        raise FreezeError("P2.84 SOURCE_KEY count drifted")
    inherited = inherited_direct_source_paths()
    planned = planned_direct_source_paths()
    if len(GENERATED_SOURCE_KEYS) != 5 or len(inherited) != 55:
        raise FreezeError("P2.84 generated/direct partition drifted")
    if len(PLANNED_OVERLAY_SOURCE_PATHS) != 20:
        raise FreezeError("planned overlay count drifted")
    if len(PLANNED_SOURCE_KEYS) != 80 or len(planned) != 75:
        raise FreezeError("planned SOURCE_KEY count drifted")

    inherited_paths = {_pure(path) for path in inherited.values()}
    mutation_paths = {
        _pure(path) for path in PLANNED_OVERLAY_SOURCE_PATHS.values()
    }
    if inherited_paths & mutation_paths:
        raise FreezeError("successor would mutate an inherited P2.84 source")

    d1_paths = tuple(_pure(path) for path in D1_PRIVATE_MUTATION_PATHS)
    private_root = _pure(D1_PRIVATE_ROOT)
    if any(path.parts[: len(private_root.parts)] != private_root.parts for path in d1_paths):
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

    missing = missing_planned_overlays(root)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": PROFILE,
        "inherited_contract_id": INHERITED_CONTRACT_ID,
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
            "planned_overlay": len(PLANNED_OVERLAY_SOURCE_PATHS),
            "planned_total": len(PLANNED_SOURCE_KEYS),
        },
        "source_keys": list(source_key_rows()),
        "candidate_mutation_paths": sorted(
            path.as_posix()
            for path in PLANNED_OVERLAY_SOURCE_PATHS.values()
        ),
        "d1_private_mutation_paths": [
            path.as_posix() for path in D1_PRIVATE_MUTATION_PATHS
        ],
        "candidate_d1_overlap_count": 0,
        "missing_planned_overlay_paths": list(missing),
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
    parser.add_argument(
        "--candidate-changed-path",
        action="append",
        default=[],
        help="assert one actual candidate mutation is in the frozen overlays",
    )
    parser.add_argument(
        "--d1-changed-path",
        action="append",
        default=[],
        help="assert one actual D1 mutation is in the frozen private file set",
    )
    args = parser.parse_args()
    validate_declared_mutations(
        candidate_paths=tuple(args.candidate_changed_path),
        d1_paths=tuple(args.d1_changed_path),
    )
    result = validate_freeze(args.repo_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_pre_intent_ready and not result["pre_intent_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
