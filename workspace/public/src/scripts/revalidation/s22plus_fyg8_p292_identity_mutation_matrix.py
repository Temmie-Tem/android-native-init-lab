#!/usr/bin/env python3
"""Exercise the P2.92 conservative three-tier identity mutation matrix."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p292_identity_tiers as tiers
import s22plus_fyg8_p292_sot_zero_delta as zero


SCHEMA = "s22plus_fyg8_p292_identity_mutation_matrix_v1"
VERDICT = "PASS_P292_STAGE_C_IDENTITY_MUTATION_MATRIX"


class MutationMatrixError(ValueError):
    pass


def _mutated(
    materials: Mapping[str, bytes], key: str
) -> dict[str, bytes]:
    if key not in materials:
        raise MutationMatrixError(f"mutation key is absent: {key}")
    result = dict(materials)
    result[key] = result[key] + b"\x00"
    return result


def _derive(
    tier1: Mapping[str, bytes],
    tier2: Mapping[str, bytes],
    tier3: Mapping[str, bytes],
    *,
    candidate_ap: bytes = b"candidate-ap-v1",
    rollback_ap: bytes = b"rollback-ap-v1",
    manifest: bytes = b"manifest-v1",
) -> dict[str, str]:
    return tiers.derive_identities(
        tier1,
        tier2,
        tier3,
        candidate_ap=candidate_ap,
        rollback_ap=rollback_ap,
        manifest=manifest,
        target_profile="s22plus-fyg8",
    )


def _changed(
    baseline: Mapping[str, str], candidate: Mapping[str, str]
) -> set[str]:
    return {
        key for key in baseline if baseline[key] != candidate[key]
    }


def _expect(
    label: str,
    baseline: Mapping[str, str],
    candidate: Mapping[str, str],
    expected: set[str],
) -> dict[str, Any]:
    changed = _changed(baseline, candidate)
    if changed != expected:
        raise MutationMatrixError(
            f"{label} identity impact differs: {sorted(changed)}"
        )
    return {
        "changed_identities": sorted(changed),
        "expected_identities": sorted(expected),
        "verified": True,
    }


def run_matrix(root: Path) -> dict[str, Any]:
    descriptor = tiers.validate()
    tier1 = tiers.tier1_materials(root)
    tier2 = tiers.tier2_materials(root)
    tier3 = tiers.tier3_materials(root)
    baseline = _derive(tier1, tier2, tier3)
    payload_mutation = _derive(
        _mutated(tier1, "direct:p292_repair_spec"), tier2, tier3
    )
    qualification_mutation = _derive(
        tier1, _mutated(tier2, "direct:p292_repair_decoder"), tier3
    )
    documentation_mutation = _derive(
        tier1, _mutated(tier2, "direct:p292_zero_delta_report"), tier3
    )
    tier2_generated_delta = _derive(
        _mutated(tier1, "generated:checkpoint_client"),
        _mutated(tier2, "inherited:decoder_adapter"),
        tier3,
    )
    live_mutation = _derive(
        tier1, tier2, _mutated(tier3, "direct:process_v2_runner")
    )
    candidate_ap_mutation = _derive(
        tier1, tier2, tier3, candidate_ap=b"candidate-ap-v2"
    )
    manifest_mutation = _derive(
        tier1, tier2, tier3, manifest=b"manifest-v2"
    )
    results = {
        "tier1_byte": _expect(
            "Tier-1 byte",
            baseline,
            payload_mutation,
            {
                "payload_identity",
                "qualification_identity",
                "live_identity",
            },
        ),
        "tier2_verifier_byte": _expect(
            "Tier-2 verifier byte",
            baseline,
            qualification_mutation,
            {"qualification_identity", "live_identity"},
        ),
        "tier2_documentation_byte": _expect(
            "Tier-2 documentation byte",
            baseline,
            documentation_mutation,
            {"qualification_identity", "live_identity"},
        ),
        "tier2_origin_with_generated_payload_delta": _expect(
            "Tier-2-originated generated payload delta",
            baseline,
            tier2_generated_delta,
            {
                "payload_identity",
                "qualification_identity",
                "live_identity",
            },
        ),
        "tier3_runner_byte": _expect(
            "Tier-3 runner byte",
            baseline,
            live_mutation,
            {"live_identity"},
        ),
        "candidate_ap_byte": _expect(
            "candidate AP byte",
            baseline,
            candidate_ap_mutation,
            {"live_identity"},
        ),
        "manifest_byte": _expect(
            "manifest byte",
            baseline,
            manifest_mutation,
            {"live_identity"},
        ),
    }

    path_sets = {
        name: list(values)
        for name, values in tiers.path_tiers().items()
    }
    universe = set().union(*(set(values) for values in path_sets.values()))
    moved_path = path_sets["tier2_qualification"][0]
    duplicate = {name: list(values) for name, values in path_sets.items()}
    duplicate["tier1_payload"].append(moved_path)
    try:
        tiers.validate_path_tiers(
            duplicate, expected_universe=universe
        )
    except tiers.IdentityTierError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    missing = {name: list(values) for name, values in path_sets.items()}
    missing["tier2_qualification"].remove(moved_path)
    try:
        tiers.validate_path_tiers(missing, expected_universe=universe)
    except tiers.IdentityTierError:
        missing_rejected = True
    else:
        missing_rejected = False
    if not duplicate_rejected or not missing_rejected:
        raise MutationMatrixError("tier move did not require descriptor change")

    stale_qualification_rejected = (
        baseline["qualification_identity"]
        != qualification_mutation["qualification_identity"]
        and baseline["live_identity"] != qualification_mutation["live_identity"]
    )
    stale_package_rejected = (
        baseline["live_identity"] != candidate_ap_mutation["live_identity"]
    )
    if not stale_qualification_rejected or not stale_package_rejected:
        raise MutationMatrixError("stale downstream closure was accepted")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "descriptor": descriptor,
        "receipt_counts": {
            "tier1": len(tier1),
            "tier2": len(tier2),
            "tier3": len(tier3),
        },
        "baseline_identities": baseline,
        "mutations": results,
        "tier_assignment": {
            "duplicate_path_rejected": duplicate_rejected,
            "zero_tier_path_rejected": missing_rejected,
            "moving_path_requires_descriptor_change": True,
            "verified": True,
        },
        "downstream_rejection": {
            "stale_qualification_rejected": stale_qualification_rejected,
            "stale_package_rejected": stale_package_rejected,
            "verified": True,
        },
        "stage_c": {
            "activated": True,
            "independent_review_required_before_closure": True,
            "independent_review_complete": False,
        },
        "safety": {
            "host_only": True,
            "intent_created": False,
            "kernel_built": False,
            "image_built": False,
            "device_contact": False,
            "live_authorized": False,
        },
    }


def _durable_write(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise MutationMatrixError("mutation-matrix output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise MutationMatrixError("short mutation-matrix write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = zero.repo_root()
    try:
        result = run_matrix(root)
        if args.out is not None:
            output = args.out if args.out.is_absolute() else root / args.out
            _durable_write(
                output,
                json.dumps(
                    result, indent=2, sort_keys=True, allow_nan=False
                ).encode("ascii")
                + b"\n",
            )
    except (
        MutationMatrixError,
        tiers.IdentityTierError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": "FAIL_CLOSED",
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "verdict": result["verdict"],
                "receipt_counts": result["receipt_counts"],
                "mutation_count": len(result["mutations"]),
                "stage_c_review_complete": result["stage_c"][
                    "independent_review_complete"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
