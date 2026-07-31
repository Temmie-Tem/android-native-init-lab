#!/usr/bin/env python3
"""Authoritative conservative P2.92 three-tier identity descriptor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping

import s22plus_fyg8_p290_source_contract as p290
import s22plus_fyg8_p292_repair_generator as repair_generator
import s22plus_fyg8_p292_repair_spec as repair_spec


SCHEMA = "s22plus_fyg8_p292_three_tier_identity_v1"
PROFILE = repair_spec.PROFILE
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P292-SOURCE-CHECK-V1"
).digest()[:16]
SOURCE_CHECK_UNSAT_TAG = hashlib.sha256(
    b"S22PLUS-FYG8-P292-SOURCE-CHECK-UNSAT-V1"
).digest()[:16]

TIER1_DIRECT_PATHS = {
    "p292_identity_tiers": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_identity_tiers.py"
    ),
    "p292_checkpoint_sot": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_checkpoint_sot.py"
    ),
    "p292_sot_generator": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_sot_generator.py"
    ),
    "p292_repair_spec": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_spec.py"
    ),
    "p292_repair_transform": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_transform.py"
    ),
    "p292_repair_generator": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_generator.py"
    ),
}

TIER2_DIRECT_PATHS = {
    "p292_zero_delta_baseline": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_sot_zero_delta_baseline.json"
    ),
    "p292_zero_delta_gate": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_sot_zero_delta.py"
    ),
    "p292_zero_delta_test": Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p292_sot_zero_delta.py"
    ),
    "p292_repair_delta_gate": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_delta.py"
    ),
    "p292_repair_delta_test": Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p292_repair_delta.py"
    ),
    "p292_repair_model": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_model.py"
    ),
    "p292_repair_decoder": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_repair_decoder.py"
    ),
    "p292_accept_to_resume": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_accept_to_resume.py"
    ),
    "p292_accept_to_resume_test": Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p292_accept_to_resume.py"
    ),
    "p292_identity_mutation_matrix": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p292_identity_mutation_matrix.py"
    ),
    "p292_identity_mutation_matrix_test": Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p292_identity_mutation_matrix.py"
    ),
    "p292_zero_delta_report": Path(
        "docs/reports/"
        "S22PLUS_FYG8_P292_CHECKPOINT_SOT_ZERO_DELTA_H0_2026-07-31.md"
    ),
    "p292_repair_delta_report": Path(
        "docs/reports/"
        "S22PLUS_FYG8_P292_CHECKPOINT_REPAIR_DELTA_ATTRIBUTION_H0_"
        "2026-07-31.md"
    ),
    "p264_identity_split_report": Path(
        "docs/reports/"
        "S22PLUS_FYG8_P264_QUALIFICATION_LATENCY_POSTMORTEM_AND_"
        "IDENTITY_SPLIT_H0_2026-07-25.md"
    ),
    "p292_closure_and_stage_c_report": Path(
        "docs/reports/"
        "S22PLUS_FYG8_P292_ACCEPT_TO_RESUME_AND_STAGE_C_H0_"
        "2026-07-31.md"
    ),
}

TIER3_DIRECT_PATHS = {
    "process_v2_runner": Path(
        "workspace/public/src/scripts/revalidation/device_action_f1_v2.py"
    ),
    "process_v2_evidence": Path(
        "workspace/public/src/scripts/revalidation/"
        "device_action_f1_evidence_v2.py"
    ),
    "process_v2_contract": Path(
        "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
    ),
}

PAYLOAD_GENERATED_KEYS = frozenset(repair_generator.artifact_paths())
TIER2_INHERITED_KEYS = frozenset(
    {
        "decoder_adapter",
        "p260_candidate_repro_enforcement",
        "p260_decoder_adapter",
        "p260_decoder_layout_delegate",
        "p260_dependency_audit",
        "p260_legacy_decoder",
        "p260_legacy_stock_closure",
        "p260_linked_adapter_dispatch",
        "p260_linked_validator_adapter",
        "p260_p245_stock_closure_adapter",
        "p260_p248_decoder_adapter",
        "p260_p251_dependency_audit",
        "p260_p251b_nested_audit",
        "p260_p252_decoder_adapter",
        "p260_p253_linked_validator_adapter",
        "p260_p253_stock_closure_adapter",
        "p260_p254_decoder_adapter",
        "p260_p257_linked_validator_adapter",
        "p260_p257_stock_closure_adapter",
        "p260_p258_linked_validator_adapter",
        "p260_p258_stock_closure_adapter",
        "p260_source_contract_selector",
        "p260_stock_closure_adapter",
        "p260_stock_topology_evidence",
        "p260_stock_topology_oracle",
        "p260_userspace_plan_enforcement",
    }
)
TIER1_INHERITED_KEYS = frozenset(
    p290.SOURCE_KEYS - TIER2_INHERITED_KEYS
)
TIER_NAMES = ("tier1_payload", "tier2_qualification", "tier3_live")


class IdentityTierError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_relative(path: Path) -> str:
    value = PurePosixPath(path.as_posix())
    if value.is_absolute() or "." in value.parts or ".." in value.parts:
        raise IdentityTierError(f"identity path is not canonical: {value}")
    return value.as_posix()


def path_tiers() -> dict[str, tuple[str, ...]]:
    return {
        "tier1_payload": tuple(
            sorted(_canonical_relative(path) for path in TIER1_DIRECT_PATHS.values())
        ),
        "tier2_qualification": tuple(
            sorted(_canonical_relative(path) for path in TIER2_DIRECT_PATHS.values())
        ),
        "tier3_live": tuple(
            sorted(_canonical_relative(path) for path in TIER3_DIRECT_PATHS.values())
        ),
    }


def validate_path_tiers(
    tiers: Mapping[str, tuple[str, ...] | list[str] | set[str]],
    *,
    expected_universe: set[str] | None = None,
) -> dict[str, Any]:
    if tuple(tiers) != TIER_NAMES:
        raise IdentityTierError("identity tier names or order differ")
    normalized: dict[str, set[str]] = {}
    for name in TIER_NAMES:
        values = set(tiers[name])
        if len(values) != len(tuple(tiers[name])):
            raise IdentityTierError(f"duplicate path within {name}")
        for value in values:
            if _canonical_relative(Path(value)) != value:
                raise IdentityTierError(f"noncanonical path in {name}: {value}")
        normalized[name] = values
    all_rows = [
        (name, value)
        for name in TIER_NAMES
        for value in sorted(normalized[name])
    ]
    path_count = len({value for _, value in all_rows})
    if path_count != len(all_rows):
        raise IdentityTierError("one path occurs in multiple identity tiers")
    universe = (
        set().union(*normalized.values())
        if expected_universe is None
        else set(expected_universe)
    )
    assigned = set().union(*normalized.values())
    if assigned != universe:
        raise IdentityTierError(
            "identity tier assignment has an unassigned or extra path"
        )
    return {
        "tier_counts": {
            name: len(normalized[name]) for name in TIER_NAMES
        },
        "path_count": path_count,
        "zero_tier_path_count": 0,
        "multi_tier_path_count": 0,
        "verified": True,
    }


def descriptor() -> dict[str, Any]:
    tiers = path_tiers()
    validation = validate_path_tiers(tiers)
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "stage_c": "conservative-three-tier-split",
        "tier1": {
            "purpose": "kernel-embedded payload identity",
            "inherited_source_keys": sorted(TIER1_INHERITED_KEYS),
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER1_DIRECT_PATHS.items())
            },
            "generated_artifact_keys": sorted(PAYLOAD_GENERATED_KEYS),
            "source_check_run_id": SOURCE_CHECK_RUN_ID.hex(),
            "source_check_unsat_tag": SOURCE_CHECK_UNSAT_TAG.hex(),
        },
        "tier2": {
            "purpose": "qualification and provenance closure",
            "inherited_nonpayload_keys": sorted(TIER2_INHERITED_KEYS),
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER2_DIRECT_PATHS.items())
            },
            "changes_payload_identity": False,
            "approval_bundle_bound": True,
        },
        "tier3": {
            "purpose": "package and live approval closure",
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER3_DIRECT_PATHS.items())
            },
            "dynamic_receipts": (
                "candidate_ap",
                "rollback_ap",
                "manifest",
                "target_profile",
            ),
        },
        "path_validation": validation,
    }


def descriptor_sha256() -> str:
    return _sha256(_canonical(descriptor()))


def _read_direct(root: Path, path: Path, label: str) -> bytes:
    target = root / path
    metadata = target.lstat()
    if target.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise IdentityTierError(f"{label} is missing or indirect")
    value = target.read_bytes()
    if not value:
        raise IdentityTierError(f"{label} is empty")
    return value


def tier1_materials(root: Path) -> dict[str, bytes]:
    inherited = p290.source_bytes(root)
    if set(inherited) != set(p290.SOURCE_KEYS):
        raise IdentityTierError("inherited P2.90 source key set differs")
    direct = {
        f"direct:{key}": _read_direct(root, path, f"Tier-1 {key}")
        for key, path in sorted(TIER1_DIRECT_PATHS.items())
    }
    generated = repair_generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )
    if set(generated) != PAYLOAD_GENERATED_KEYS:
        raise IdentityTierError("generated Tier-1 artifact set differs")
    result = {
        **{
            f"inherited:{key}": inherited[key]
            for key in sorted(TIER1_INHERITED_KEYS)
        },
        **direct,
        **{f"generated:{key}": value for key, value in generated.items()},
    }
    return result


def tier2_materials(root: Path) -> dict[str, bytes]:
    inherited = p290.source_bytes(root)
    if set(inherited) != set(p290.SOURCE_KEYS):
        raise IdentityTierError("inherited P2.90 source key set differs")
    result = {
        f"inherited:{key}": inherited[key]
        for key in sorted(TIER2_INHERITED_KEYS)
    }
    result.update(
        {
            f"direct:{key}": _read_direct(root, path, f"Tier-2 {key}")
            for key, path in sorted(TIER2_DIRECT_PATHS.items())
        }
    )
    return result


def tier3_materials(root: Path) -> dict[str, bytes]:
    return {
        f"direct:{key}": _read_direct(root, path, f"Tier-3 {key}")
        for key, path in sorted(TIER3_DIRECT_PATHS.items())
    }


def receipt_set(materials: Mapping[str, bytes]) -> dict[str, dict[str, Any]]:
    return {
        key: {"size": len(value), "sha256": _sha256(value)}
        for key, value in sorted(materials.items())
    }


def payload_identity(materials: Mapping[str, bytes]) -> str:
    return _sha256(
        _canonical(
            {
                "domain": "S22PLUS-FYG8-P292-PAYLOAD-IDENTITY-V1",
                "descriptor_sha256": descriptor_sha256(),
                "receipts": receipt_set(materials),
            }
        )
    )


def qualification_identity(
    payload_id: str, materials: Mapping[str, bytes]
) -> str:
    return _sha256(
        _canonical(
            {
                "domain": "S22PLUS-FYG8-P292-QUALIFICATION-IDENTITY-V1",
                "payload_identity": payload_id,
                "receipts": receipt_set(materials),
            }
        )
    )


def live_identity(
    payload_id: str,
    qualification_id: str,
    materials: Mapping[str, bytes],
    *,
    candidate_ap: bytes,
    rollback_ap: bytes,
    manifest: bytes,
    target_profile: str,
) -> str:
    if not target_profile:
        raise IdentityTierError("target profile is empty")
    dynamic = {
        "candidate_ap": candidate_ap,
        "rollback_ap": rollback_ap,
        "manifest": manifest,
        "target_profile": target_profile.encode("ascii"),
    }
    if any(not value for value in dynamic.values()):
        raise IdentityTierError("dynamic live receipt is empty")
    return _sha256(
        _canonical(
            {
                "domain": "S22PLUS-FYG8-P292-LIVE-IDENTITY-V1",
                "payload_identity": payload_id,
                "qualification_identity": qualification_id,
                "static_receipts": receipt_set(materials),
                "dynamic_receipts": receipt_set(dynamic),
            }
        )
    )


def derive_identities(
    tier1: Mapping[str, bytes],
    tier2: Mapping[str, bytes],
    tier3: Mapping[str, bytes],
    *,
    candidate_ap: bytes,
    rollback_ap: bytes,
    manifest: bytes,
    target_profile: str,
) -> dict[str, str]:
    payload = payload_identity(tier1)
    qualification = qualification_identity(payload, tier2)
    live = live_identity(
        payload,
        qualification,
        tier3,
        candidate_ap=candidate_ap,
        rollback_ap=rollback_ap,
        manifest=manifest,
        target_profile=target_profile,
    )
    return {
        "payload_identity": payload,
        "qualification_identity": qualification,
        "live_identity": live,
    }


def validate() -> dict[str, Any]:
    path_result = validate_path_tiers(path_tiers())
    if (
        TIER1_INHERITED_KEYS | TIER2_INHERITED_KEYS
        != frozenset(p290.SOURCE_KEYS)
        or TIER1_INHERITED_KEYS & TIER2_INHERITED_KEYS
        or len(PAYLOAD_GENERATED_KEYS) != 13
        or repair_spec.ACTIVE_STATE_REPRESENTATION
        != "exact-committed-active-slot"
    ):
        raise IdentityTierError("P2.92 identity descriptor scope differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "inherited_payload_key_count": len(TIER1_INHERITED_KEYS),
        "inherited_nonpayload_key_count": len(TIER2_INHERITED_KEYS),
        "tier1_direct_count": len(TIER1_DIRECT_PATHS),
        "generated_payload_count": len(PAYLOAD_GENERATED_KEYS),
        "tier2_direct_count": len(TIER2_DIRECT_PATHS),
        "tier3_direct_count": len(TIER3_DIRECT_PATHS),
        "path_validation": path_result,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
