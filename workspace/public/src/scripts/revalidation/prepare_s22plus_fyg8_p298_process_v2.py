#!/usr/bin/env python3
"""Promote one independently checked P2.98 candidate into offline evidence."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import prepare_s22plus_fyg8_p234_process_v2 as base
import s22plus_fyg8_p298_candidate_static_checker as static_checker
import s22plus_fyg8_p298_e2_stock_closure as e2_closure_selector


SCHEMA = "s22plus_fyg8_p298_process_v2_promotion_v1"
VERDICT = base.VERDICT
TARGET = static_checker.TARGET
DEFAULT_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p298/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_p298/"
    "candidate-a/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p298/process-v2"
)
_BASE_VALIDATE_STATIC = base.validate_static
_CONFIGURATION_FIELDS = (
    "static_checker",
    "e2_closure_selector",
    "SCHEMA",
    "VERDICT",
    "TARGET",
    "DEFAULT_STATIC",
    "DEFAULT_CANDIDATE_AP",
    "DEFAULT_OUT",
)
_INDIRECT_MODULE_NAMES = (
    "build_s22plus_fyg8_p286_candidate",
    "s22plus_fyg8_p286_boot_only_packager",
    "s22plus_fyg8_p286_build",
    "s22plus_fyg8_p286_build_repro_check",
    "s22plus_fyg8_p286_candidate_contract",
    "s22plus_fyg8_p286_candidate_static_checker",
    "s22plus_fyg8_p286_source_contracts",
    "s22plus_fyg8_p286_userspace_build",
    "s22plus_fyg8_p290_build_repro_check",
)


def _apply_configuration() -> None:
    static_checker._configure()
    base.static_checker = static_checker
    base.e2_closure_selector = e2_closure_selector
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_STATIC = DEFAULT_STATIC
    base.DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_AP
    base.DEFAULT_OUT = DEFAULT_OUT


def _snapshot_indirect_modules() -> dict[ModuleType, dict[str, Any]]:
    return {
        module: dict(vars(module))
        for module in (
            importlib.import_module(name) for name in _INDIRECT_MODULE_NAMES
        )
    }


def _restore_indirect_modules(
    snapshots: dict[ModuleType, dict[str, Any]],
) -> None:
    for module, saved in snapshots.items():
        current = vars(module)
        for name in set(current) - set(saved):
            del current[name]
        current.update(saved)


def _historical_build_repair(result: dict[str, Any]) -> dict[str, Any]:
    build = result.get("build_repro")
    expected_build_keys = {
        "fresh_reverification",
        "image",
        "immutable_build_time_proof_revalidated",
        "linked_audit_verified",
        "result",
        "tier2_repair",
        "two_clean_builds_byte_identical",
    }
    if (
        not isinstance(build, dict)
        or set(build) != expected_build_keys
        or build.get("fresh_reverification") is not False
        or build.get("immutable_build_time_proof_revalidated") is not True
        or build.get("linked_audit_verified") is not True
        or build.get("two_clean_builds_byte_identical") is not True
        or build.get("result") != static_checker.HISTORICAL_POSTBUILD_RESULT
    ):
        raise base.PromotionError(
            "P2.98 immutable build-time proof contract is incomplete"
        )

    repair = build.get("tier2_repair")
    expected_repair_keys = {
        "schema",
        "historical_postbuild_result",
        "historical_pre_lto_qualification",
        "a_b_artifacts_reopened",
        "a_b_artifact_inodes_distinct",
        "byte_identical_artifacts_reverified",
        "tier1_candidate_identity_changed",
        "tier2_repair_files",
        "fresh_full_lto_claimed",
        "verified",
    }
    expected_equal = sorted(
        set(static_checker.repro.ARTIFACT_LIMITS) - {"build-result.json"}
    )
    if (
        not isinstance(repair, dict)
        or set(repair) != expected_repair_keys
        or repair.get("schema")
        != "s22plus_fyg8_p298_postbuild_tier2_repair_v1"
        or repair.get("historical_postbuild_result")
        != static_checker.HISTORICAL_POSTBUILD_RESULT
        or repair.get("historical_pre_lto_qualification")
        != static_checker.HISTORICAL_QUALIFICATION
        or repair.get("a_b_artifact_inodes_distinct") is not True
        or repair.get("byte_identical_artifacts_reverified") != expected_equal
        or repair.get("tier1_candidate_identity_changed") is not False
        or repair.get("fresh_full_lto_claimed") is not False
        or repair.get("verified") is not True
    ):
        raise base.PromotionError("P2.98 historical Tier-2 repair contract differs")

    reopened = repair.get("a_b_artifacts_reopened")
    expected_artifacts = set(static_checker.repro.ARTIFACT_LIMITS)
    if not isinstance(reopened, dict) or set(reopened) != {"build_a", "build_b"}:
        raise base.PromotionError("P2.98 reopened A/B artifact proof is incomplete")
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for build_name in ("build_a", "build_b"):
        artifacts = reopened.get(build_name)
        if not isinstance(artifacts, dict) or set(artifacts) != expected_artifacts:
            raise base.PromotionError(
                f"P2.98 reopened {build_name} artifact inventory differs"
            )
        normalized[build_name] = {
            name: base.exact_identity(value, f"P2.98 {build_name} {name}")
            for name, value in artifacts.items()
        }
    for name in expected_equal:
        if normalized["build_a"][name] != normalized["build_b"][name]:
            raise base.PromotionError(f"P2.98 historical A/B {name} receipt differs")
    image = base.exact_identity(build.get("image"), "P2.98 build Image")
    if (
        normalized["build_a"]["Image"] != image
        or normalized["build_b"]["Image"] != image
    ):
        raise base.PromotionError("P2.98 historical A/B Image identity differs")

    root = base.repo_root()
    current_repair_files = {}
    for path in static_checker.TIER2_REPAIR_PATHS:
        payload = static_checker.stable_read(
            root / path,
            f"P2.98 Tier-2 promotion input {path.name}",
            2 * 1024 * 1024,
        )
        current_repair_files[path.as_posix()] = base.receipt(payload)
    if repair.get("tier2_repair_files") != current_repair_files:
        raise base.PromotionError("P2.98 Tier-2 repair files changed after static audit")
    return repair


def validate_static(
    result: dict[str, Any],
    static_receipt: dict[str, Any],
    ap_receipt: dict[str, Any],
):
    with _validation_context():
        return _validate_static_configured(result, static_receipt, ap_receipt)


def _validate_static_configured(
    result: dict[str, Any],
    static_receipt: dict[str, Any],
    ap_receipt: dict[str, Any],
):
    _historical_build_repair(result)
    adapted = copy.deepcopy(result)
    adapted["build_repro"]["fresh_reverification"] = True
    return _BASE_VALIDATE_STATIC(adapted, static_receipt, ap_receipt)


@contextmanager
def _validation_context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _CONFIGURATION_FIELDS}
    previous_validate = base.validate_static
    indirect = _snapshot_indirect_modules()
    try:
        _apply_configuration()
        base.validate_static = _validate_static_configured
        yield
    finally:
        base.validate_static = previous_validate
        for name, value in previous.items():
            setattr(base, name, value)
        _restore_indirect_modules(indirect)


def __getattr__(name: str):
    return getattr(base, name)


def parse_args(argv: list[str] | None = None):
    with _validation_context():
        return base.parse_args(argv)


def derive(
    static_result: dict[str, Any],
    static_receipt: dict[str, Any],
    candidate_ap: dict[str, Any],
):
    with _validation_context():
        return base.derive(static_result, static_receipt, candidate_ap)


def main(argv: list[str] | None = None) -> int:
    with _validation_context():
        return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
