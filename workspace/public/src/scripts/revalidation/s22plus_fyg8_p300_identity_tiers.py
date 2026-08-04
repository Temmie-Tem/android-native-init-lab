#!/usr/bin/env python3
"""P3.00 three-tier identity for event-ingress/IRQ attribution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping

import s22plus_fyg8_p298_identity_tiers as inherited_identity
import s22plus_fyg8_p298_source_contract as inherited_contract
import s22plus_fyg8_p300_telemetry_generator as generator
import s22plus_fyg8_p300_telemetry_model as model
import s22plus_fyg8_p300_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p300_three_tier_identity_v1"
PROFILE = spec.PROFILE
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P300-SOURCE-CHECK-V1"
).digest()[:16]
SOURCE_CHECK_UNSAT_TAG = model.unsat_record(
    PROFILE, SOURCE_CHECK_RUN_ID
)[len(model.UNSAT_FAMILY) :]

PREFIX = Path("workspace/public/src/scripts/revalidation")
TIER1_DIRECT_PATHS = {
    "p300_identity_tiers": PREFIX / "s22plus_fyg8_p300_identity_tiers.py",
    "p300_telemetry_spec": PREFIX / "s22plus_fyg8_p300_telemetry_spec.py",
    "p300_telemetry_transform": PREFIX / "s22plus_fyg8_p300_telemetry_transform.py",
    "p300_telemetry_generator": PREFIX / "s22plus_fyg8_p300_telemetry_generator.py",
    "p300_source_contract": PREFIX / "s22plus_fyg8_p300_source_contract.py",
    "p300_candidate_intent": PREFIX / "s22plus_fyg8_p300_candidate_intent.py",
    "p300_userspace_build": PREFIX / "s22plus_fyg8_p300_userspace_build.py",
    "p300_build": PREFIX / "s22plus_fyg8_p300_build.py",
    "p300_candidate_builder": PREFIX / "build_s22plus_fyg8_p300_candidate.py",
    "p300_boot_only_packager": PREFIX / "s22plus_fyg8_p300_boot_only_packager.py",
}
TIER2_DIRECT_PATHS = {
    "p300_telemetry_model": PREFIX / "s22plus_fyg8_p300_telemetry_model.py",
    "p300_telemetry_decoder": PREFIX / "s22plus_fyg8_p300_telemetry_decoder.py",
    "p300_telemetry_closure": PREFIX / "s22plus_fyg8_p300_telemetry_closure.py",
    "p300_telemetry_test": PREFIX / "test_s22plus_fyg8_p300_telemetry.py",
    "p300_contract_test": Path("tests/test_s22plus_fyg8_p300_contract.py"),
    "p300_change_freeze": PREFIX / "s22plus_fyg8_p300_change_freeze.py",
    "p300_candidate_contract": PREFIX / "s22plus_fyg8_p300_candidate_contract.py",
    "p300_build_repro_check": PREFIX / "s22plus_fyg8_p300_build_repro_check.py",
    "p300_candidate_static_checker": PREFIX / "s22plus_fyg8_p300_candidate_static_checker.py",
    "p300_e2_stock_closure": PREFIX / "s22plus_fyg8_p300_e2_stock_closure.py",
    "p300_linked_audit": PREFIX / "s22plus_fyg8_p300_linked_audit.py",
    "p300_postbuild_linked_audit": PREFIX / "s22plus_fyg8_p300_postbuild_linked_audit.py",
    "p300_pre_lto_qualification": PREFIX / "s22plus_fyg8_p300_pre_lto_qualification.py",
}
TIER3_DIRECT_PATHS = {
    **inherited_identity.TIER3_DIRECT_PATHS,
    "usb_trace_sidecar": PREFIX / "device_action_usb_trace_sidecar_v1.py",
    "p300_usb_trace_binding": PREFIX / "s22plus_fyg8_p300_usb_trace_binding.py",
}
PAYLOAD_GENERATED_KEYS = frozenset(generator.artifact_paths())
INHERITED_PAYLOAD_SOURCE_KEYS = {
    f"p298_input__{key}": key for key in sorted(inherited_contract.SOURCE_KEYS)
}
GENERATED_PAYLOAD_SOURCE_KEYS = {
    key: ("base_patch" if key == "candidate_patch" else key)
    for key in sorted(PAYLOAD_GENERATED_KEYS)
}
TIER1_SOURCE_KEYS = frozenset(
    (
        *INHERITED_PAYLOAD_SOURCE_KEYS,
        *TIER1_DIRECT_PATHS,
        *GENERATED_PAYLOAD_SOURCE_KEYS.values(),
    )
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
) -> dict[str, Any]:
    if tuple(tiers) != TIER_NAMES:
        raise IdentityTierError("identity tier names or order differ")
    rows = []
    for name in TIER_NAMES:
        values = tuple(tiers[name])
        if len(set(values)) != len(values):
            raise IdentityTierError(f"duplicate path within {name}")
        rows.extend((name, value) for value in values)
    if len({value for _name, value in rows}) != len(rows):
        raise IdentityTierError("one path occurs in multiple identity tiers")
    return {
        "tier_counts": {name: len(tuple(tiers[name])) for name in TIER_NAMES},
        "path_count": len(rows),
        "zero_tier_path_count": 0,
        "multi_tier_path_count": 0,
        "verified": True,
    }


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "tier1": {
            "purpose": "kernel-embedded P3.00 payload identity",
            "inherited_source_keys": dict(INHERITED_PAYLOAD_SOURCE_KEYS),
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER1_DIRECT_PATHS.items())
            },
            "generated_artifact_keys": dict(GENERATED_PAYLOAD_SOURCE_KEYS),
            "source_keys": sorted(TIER1_SOURCE_KEYS),
            "source_check_run_id": SOURCE_CHECK_RUN_ID.hex(),
            "source_check_unsat_tag": SOURCE_CHECK_UNSAT_TAG.hex(),
        },
        "tier2": {
            "purpose": "qualification and provenance closure",
            "inherited": "P2.98 tier-2 receipt closure",
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER2_DIRECT_PATHS.items())
            },
            "changes_payload_identity": False,
            "approval_bundle_bound": False,
            "candidate_qualification_adapter_complete": True,
        },
        "tier3": {
            "purpose": "future live inputs and exact passive-sidecar source",
            "direct_paths": {
                key: _canonical_relative(path)
                for key, path in sorted(TIER3_DIRECT_PATHS.items())
            },
            "same_f1_binding_adapter_complete": True,
            "same_f1_runtime_binding_complete": False,
        },
        "path_validation": validate_path_tiers(path_tiers()),
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
    inherited = inherited_contract.source_bytes(root)
    generated = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )
    result = {
        **{
            source_key: inherited[legacy_key]
            for source_key, legacy_key in sorted(INHERITED_PAYLOAD_SOURCE_KEYS.items())
        },
        **{
            key: _read_direct(root, path, f"Tier-1 {key}")
            for key, path in sorted(TIER1_DIRECT_PATHS.items())
        },
        **{
            GENERATED_PAYLOAD_SOURCE_KEYS[key]: value
            for key, value in sorted(generated.items())
        },
    }
    if set(result) != TIER1_SOURCE_KEYS:
        raise IdentityTierError("P3.00 Tier-1 source key set differs")
    return result


def tier2_materials(root: Path) -> dict[str, bytes]:
    result = {
        f"inherited:{key}": value
        for key, value in inherited_identity.tier2_materials(root).items()
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
                "domain": "S22PLUS-FYG8-P300-PAYLOAD-IDENTITY-V1",
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
                "domain": "S22PLUS-FYG8-P300-QUALIFICATION-IDENTITY-V1",
                "payload_identity": payload_id,
                "receipts": receipt_set(materials),
            }
        )
    )


def validate() -> dict[str, Any]:
    path_result = validate_path_tiers(path_tiers())
    expected = (
        len(INHERITED_PAYLOAD_SOURCE_KEYS)
        + len(TIER1_DIRECT_PATHS)
        + len(PAYLOAD_GENERATED_KEYS)
    )
    if (
        len(PAYLOAD_GENERATED_KEYS) != 13
        or len(TIER1_SOURCE_KEYS) != expected
        or spec.validate().get("verified") is not True
        or "usb_trace_sidecar" not in TIER3_DIRECT_PATHS
        or "p300_usb_trace_binding" not in TIER3_DIRECT_PATHS
    ):
        raise IdentityTierError("P3.00 identity descriptor scope differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "inherited_payload_key_count": len(INHERITED_PAYLOAD_SOURCE_KEYS),
        "tier1_direct_count": len(TIER1_DIRECT_PATHS),
        "tier1_source_key_count": len(TIER1_SOURCE_KEYS),
        "generated_payload_count": len(PAYLOAD_GENERATED_KEYS),
        "tier2_direct_count": len(TIER2_DIRECT_PATHS),
        "tier3_direct_count": len(TIER3_DIRECT_PATHS),
        "path_validation": path_result,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
