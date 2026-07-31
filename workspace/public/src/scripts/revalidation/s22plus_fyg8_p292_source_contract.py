#!/usr/bin/env python3
"""P2.92 source contract for resumable checkpoint state and errno evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p290_source_contract as p290
import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_identity_tiers as identity
import s22plus_fyg8_p292_repair_decoder as decoder
import s22plus_fyg8_p292_repair_generator as generator
import s22plus_fyg8_p292_repair_model as model
import s22plus_fyg8_p292_repair_spec as repair


spec = p290.spec
CONTRACT_ID = "s22plus-fyg8-p292-resumable-checkpoint-state-v1"
PROFILE = repair.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P292-RESUMABLE-CHECKPOINT-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p292_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p292_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P292_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p292_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P292_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P292_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = (
    "PASS_P292_RESUMABLE_CHECKPOINT_IMPLEMENTATION_HOST_ONLY"
)
SOURCE_CHECK_RUN_ID = identity.SOURCE_CHECK_RUN_ID
SOURCE_CHECK_UNSAT_TAG = identity.SOURCE_CHECK_UNSAT_TAG
MODULE_PLAN_COUNT = p290.MODULE_PLAN_COUNT
SOURCE_KEYS = identity.TIER1_SOURCE_KEYS
STAGE_SEQUENCE = p290.spec.STAGE_SEQUENCE
MATERIALIZED_FILENAMES = {
    key: path.name
    for key, path in generator.artifact_paths().items()
    if key != "candidate_patch"
}
REACHABLE_VARIANTS = p290.REACHABLE_VARIANTS + (
    (len(p290.spec.POSITIONS) - 1)
    * len(repair.PUBLICATION_OPERATIONS)
    * repair.ERRNO_MAX
)
LINKED_VALIDATOR_SYMBOLS = p290.LINKED_VALIDATOR_SYMBOLS


class SourceContractError(ValueError):
    pass


SourceContract = p290.SourceContract
P292 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=p290.spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P292


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p290.candidate_observer(run_id)


def source_bytes(root: Path) -> dict[str, bytes]:
    result = identity.tier1_materials(root)
    if set(result) != SOURCE_KEYS:
        missing = sorted(SOURCE_KEYS - set(result))
        extra = sorted(set(result) - SOURCE_KEYS)
        raise SourceContractError(
            f"P2.92 source inventory changed: missing={missing}, extra={extra}"
        )
    if result["base_patch"] != generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )["candidate_patch"]:
        raise SourceContractError("P2.92 base patch is not the repaired output")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = (
        p290.p288.p243.repo_root() if root is None else root
    )
    source = source_bytes(repository)
    return {
        "plan": source["plan_header"],
        "runtime": source["runtime_wrapper"],
        "checkpoint": source["checkpoint_client"],
        "patch": source["base_patch"],
    }


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    patch_path = directory / "p292.patch"
    patch_path.write_bytes(patch)
    p290.p288.p252.p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=p290.shared_input_root(root) / p290.p288.p252.p241.DEFAULT_SOURCE,
        label="P2.92 clean-apply check",
    )
    required = (
        b"struct s22_fyg8_e1_slot active;",
        b"memcmp(&record->slots[s22_fyg8_e1_state.active_slot],",
        b"&s22_fyg8_e1_state.active,",
        b"memcpy(&s22_fyg8_e1_state.active, &next,",
        b"detail > 0x4000 && detail <= 0x4fff",
    )
    if any(patch.count(token) < 1 for token in required):
        raise SourceContractError("P2.92 kernel repair source is incomplete")
    forbidden = (
        b"s22_fyg8_e1_state.generation",
        b"s22_fyg8_e1_state.stage",
        b"s22_fyg8_e1_state.item_index",
        b"s22_fyg8_e1_build_slot(&active",
    )
    if any(token in patch for token in forbidden):
        raise SourceContractError("P2.92 patch retains partial active state")
    return {
        **receipt(patch),
        "clean_apply": True,
        "exact_active_slot_state": True,
        "operation_aware_errno_details": True,
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key, filename in MATERIALIZED_FILENAMES.items():
        if key in {"checkpoint_client", "runtime_wrapper", "plan_header"}:
            continue
        (directory / filename).write_bytes(source[key])
    try:
        return p290.p288.p252._audit_userspace(  # noqa: SLF001
            p290.shared_input_root(root),
            generated,
            directory,
            materialized_filenames=MATERIALIZED_FILENAMES,
            source_check_run_id=SOURCE_CHECK_RUN_ID,
        )
    except p290.p288.p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.92 generation is not deterministic")
    source = source_bytes(root)
    identity_result = identity.validate()
    repair_result = repair.validate()
    closure_result = closure.run_closure(root)
    if (
        closure_result.get("verdict") != closure.VERDICT
        or closure_result.get("accept_to_resume_closure", {}).get(
            "closure_case_count"
        )
        != 171
        or closure_result.get("accept_to_resume_sequence_walk", {}).get(
            "snapshot_count"
        )
        != 214
    ):
        raise SourceContractError("P2.92 accept-to-resume closure differs")
    with tempfile.TemporaryDirectory(prefix="s22-p292-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p292_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "patch": patch,
        "linked_userspace": userspace,
        "accept_to_resume": {
            "closure_case_count": 171,
            "sequence_walk_snapshots": 214,
            "exact_old_generation_88_resumed": True,
            "errno_observable": True,
            "verified": True,
        },
        "sot": {
            "repair_descriptor_sha256": repair_result[
                "descriptor_sha256"
            ],
            "identity_descriptor_sha256": identity_result[
                "descriptor_sha256"
            ],
            "verified": True,
        },
        "descriptor": {
            "position_count": len(p290.spec.POSITIONS),
            "terminal_generation": p290.spec.TERMINAL_GENERATION,
            "record_size": model.LONG_RECORD_SIZE,
            "slot_count": model.SLOT_COUNT,
        },
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    if len(run_id) != 16 or not any(run_id):
        raise SourceContractError("P2.92 reachable run ID is invalid")
    inherited = p290.validate_reachable_records(run_id)
    round_trips = 0
    for operation in repair.PUBLICATION_OPERATIONS:
        for number in range(1, repair.ERRNO_MAX + 1):
            detail = repair.encode_publication_error(
                operation.value, -number
            )
            if repair.decode_publication_error(detail) != (
                operation.value,
                -number,
            ):
                raise SourceContractError(
                    "P2.92 publication errno round trip differs"
                )
            round_trips += 1
    checked_positions = 0
    for generation, position in enumerate(p290.spec.POSITIONS[:-1], 1):
        record = model.initialize_record(PROFILE, run_id)
        for prior in p290.spec.POSITIONS[: generation - 1]:
            record = model.apply_request(
                record,
                model.encode_request(
                    PROFILE,
                    prior.stage,
                    run_id=run_id,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=prior.item_index,
                    detail=0,
                ),
            )
        for operation in repair.PUBLICATION_OPERATIONS:
            detail = repair.encode_publication_error(
                operation.value, -116
            )
            request = model.encode_request(
                PROFILE,
                position.stage,
                run_id=run_id,
                outcome=model.OUTCOME_FAILURE,
                detail=detail,
                item_index=position.item_index,
            )
            active = model.decode_record(
                model.apply_request(record, request),
                expected_profile=PROFILE,
                expected_run_id=run_id,
            )["active"]
            if (
                active["generation"] != generation
                or active["stage"] != position.stage
                or active["item_index"] != position.item_index
                or active["outcome"] != model.OUTCOME_FAILURE
                or active["detail"] != detail
            ):
                raise SourceContractError(
                    "P2.92 publication failure record differs"
                )
            checked_positions += 1
    return {
        **inherited,
        "decoder_policy_id": decoder.POLICY_ID,
        "publication_errno_round_trips": round_trips,
        "publication_position_checks": checked_positions,
        "accept_to_resume_required": True,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    return p290.linked_table_bytes()


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    return p290.audit_linked_tables(actual)


def main() -> int:
    try:
        result = implementation_result(p290.p288.p243.repo_root())
    except (
        SourceContractError,
        identity.IdentityTierError,
        closure.ClosureError,
        generator.RepairGeneratorError,
        repair.RepairSpecError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
