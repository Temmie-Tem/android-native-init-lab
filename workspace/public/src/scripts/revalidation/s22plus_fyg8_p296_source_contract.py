#!/usr/bin/env python3
"""P2.96 source contract for boot-delivered built-in DWC3 telemetry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p292_source_contract as checkpoint_base
import s22plus_fyg8_p294_source_contract as inherited
import s22plus_fyg8_p296_identity_tiers as identity
import s22plus_fyg8_p296_telemetry_closure as closure
import s22plus_fyg8_p296_telemetry_decoder as decoder
import s22plus_fyg8_p296_telemetry_generator as generator
import s22plus_fyg8_p296_telemetry_spec as spec


CONTRACT_ID = "s22plus-fyg8-p296-builtin-dwc3-telemetry-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P296-BUILTIN-DWC3-TELEMETRY-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p296_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p296_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P296_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p296_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P296_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P296_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P296_BUILTIN_DWC3_TELEMETRY_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = identity.SOURCE_CHECK_RUN_ID
SOURCE_CHECK_UNSAT_TAG = identity.SOURCE_CHECK_UNSAT_TAG
MODULE_PLAN_COUNT = inherited.MODULE_PLAN_COUNT
SOURCE_KEYS = identity.TIER1_SOURCE_KEYS
STAGE_SEQUENCE = tuple(position.stage for position in spec.POSITIONS)
MATERIALIZED_FILENAMES = {
    key: path.name
    for key, path in generator.artifact_paths().items()
    if key != "candidate_patch"
}
TELEMETRY_REACHABLE_VARIANTS = 16 + 132 + 7 + 2
REACHABLE_VARIANTS = checkpoint_base.REACHABLE_VARIANTS + TELEMETRY_REACHABLE_VARIANTS
LINKED_VALIDATOR_SYMBOLS = (
    *checkpoint_base.LINKED_VALIDATOR_SYMBOLS,
    "s22_p294_dwc3_state_snapshot",
)
DRIVER_SOURCE_REFERENCE = inherited.DRIVER_SOURCE_REFERENCE
DRIVER_SOURCE_RECEIPTS = {
    "kernel_platform/common/drivers/usb/dwc3/gadget.c": (
        inherited.DRIVER_SOURCE_RECEIPTS[
            "kernel_platform/common/drivers/usb/dwc3/gadget.c"
        ]
    ),
}


class SourceContractError(ValueError):
    pass


SourceContract = inherited.SourceContract
P296 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P296


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return inherited.candidate_observer(run_id)


def source_bytes(root: Path) -> dict[str, bytes]:
    result = identity.tier1_materials(root)
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.96 source inventory changed")
    expected_patch = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )["candidate_patch"]
    if result["base_patch"] != expected_patch:
        raise SourceContractError(
            "P2.96 base patch is not the telemetry generator output"
        )
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = inherited.inherited.p290.p288.p243.repo_root() if root is None else root
    source = source_bytes(repository)
    return {
        "plan": source["plan_header"],
        "runtime": source["runtime_wrapper"],
        "checkpoint": source["checkpoint_client"],
        "patch": source["base_patch"],
    }


def _driver_patch(patch: bytes) -> tuple[bytes, bytes]:
    marker = b"diff --git a/kernel_platform/common/drivers/usb/dwc3/gadget.c "
    if patch.count(marker) != 1:
        raise SourceContractError("P2.96 driver patch boundary differs")
    offset = patch.index(marker)
    return patch[:offset], patch[offset:]


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    inherited_patch, driver_patch = _driver_patch(patch)
    inherited_result = checkpoint_base._audit_patch(  # noqa: SLF001
        root, inherited_patch, directory
    )
    reference = root / DRIVER_SOURCE_REFERENCE
    for relative, expected in DRIVER_SOURCE_RECEIPTS.items():
        path = reference / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise SourceContractError(
                f"P2.96 driver reference differs: {relative}"
            )
    checked = subprocess.run(
        ["git", "apply", "--check", "--unsafe-paths", "-"],
        cwd=reference,
        input=driver_patch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if checked.returncode != 0:
        raise SourceContractError(
            "P2.96 driver patch does not cleanly apply: "
            + checked.stderr.decode("utf-8", "replace")[-2000:]
        )
    required = (
        b"s22_p294_dwc3_state_snapshot",
        b"DWC3_DSTS_USBLNKST(dsts)",
        b"DWC3_DCTL_RUN_STOP",
        b"DWC3_DSTS_DEVCTRLHLT",
    )
    forbidden = (
        b"s22_p294_wrapper_vbus_snapshot",
        b"dwc3-msm-core.c",
    )
    if any(driver_patch.count(token) < 1 for token in required) or any(
        token in driver_patch for token in forbidden
    ):
        raise SourceContractError("P2.96 built-in telemetry source differs")
    return {
        **receipt(patch),
        "inherited_checkpoint_patch": inherited_result,
        "driver_reference_receipts": dict(DRIVER_SOURCE_RECEIPTS),
        "driver_clean_apply": True,
        "external_module_patch_count": 0,
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
        return checkpoint_base.p290.p288.p252._audit_userspace(  # noqa: SLF001
            checkpoint_base.p290.shared_input_root(root),
            generated,
            directory,
            materialized_filenames=MATERIALIZED_FILENAMES,
            source_check_run_id=SOURCE_CHECK_RUN_ID,
        )
    except checkpoint_base.p290.p288.p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.96 generation is not deterministic")
    source = source_bytes(root)
    identity_result = identity.validate()
    telemetry = closure.run_closure(root)
    if telemetry.get("verdict") != closure.VERDICT:
        raise SourceContractError("P2.96 telemetry closure differs")
    with tempfile.TemporaryDirectory(prefix="s22-p296-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p296_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {name: receipt(data) for name, data in sorted(first.items())},
        "patch": patch,
        "linked_userspace": userspace,
        "telemetry_closure": telemetry,
        "identity": identity_result,
        "descriptor": {
            "position_count": len(spec.POSITIONS),
            "terminal_generation": spec.TERMINAL_GENERATION,
            "record_size": 45,
            "slot_count": 2,
            "built_in_snapshot_only": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "boot_image_packaging": False,
            "live_authorized": False,
        },
        "verified": True,
    }


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    if len(run_id) != 16 or not any(run_id):
        raise SourceContractError("P2.96 reachable run ID is invalid")
    inherited_result = checkpoint_base.validate_reachable_records(run_id)
    record = decoder.model.initialize_record(PROFILE, run_id)
    for generation, position in enumerate(spec.POSITIONS[:105], 1):
        detail = 0xC18 if generation == 88 else 0xC40 if generation == 104 else 0
        record = decoder.model.apply_request(
            record,
            decoder.model.encode_request(
                PROFILE,
                position.stage,
                run_id=run_id,
                outcome=decoder.model.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            ),
        )
    link_position = spec.POSITIONS[spec.LINK_STATE_ORDINAL]
    terminal_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
    first = decoder.model.apply_request(
        record,
        decoder.model.encode_request(
            PROFILE,
            link_position.stage,
            run_id=run_id,
            outcome=decoder.model.OUTCOME_PROGRESS,
            item_index=link_position.item_index,
            detail=spec.encode_link_state(0),
        ),
    )
    terminal_details = (
        *(spec.FINAL_STATE_DETAIL_BASE + index for index in range(132)),
        *(spec.encode_fixed_mismatch(mask) for mask in range(1, 8)),
        spec.STATE_SPEED_CONTRADICTION_DETAIL,
        spec.CONNECT_SPEED_CONTRADICTION_DETAIL,
    )
    checked = spec.LINK_STATE_VALUE_COUNT
    for detail in terminal_details:
        outcome = spec.expected_terminal_outcome(detail)
        candidate = decoder.model.apply_request(
            first,
            decoder.model.encode_request(
                PROFILE,
                terminal_position.stage,
                run_id=run_id,
                outcome=outcome,
                item_index=terminal_position.item_index,
                detail=detail,
            ),
        )
        active = decoder.decode_record(
            candidate,
            expected_profile=PROFILE,
            expected_run_id=run_id,
        )["active"]
        if active["detail"] != detail or active["generation"] != 107:
            raise SourceContractError("P2.96 reachable terminal slot differs")
        checked += 1
    if checked != TELEMETRY_REACHABLE_VARIANTS:
        raise SourceContractError("P2.96 telemetry reachable count differs")
    return {
        **inherited_result,
        "reachable_slot_variants": REACHABLE_VARIANTS,
        "decoder_policy_id": decoder.POLICY_ID,
        "telemetry_reachable_variants": checked,
        "position_count": len(spec.POSITIONS),
        "terminal_generation": spec.TERMINAL_GENERATION,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    result = dict(checkpoint_base.linked_table_bytes())
    rules = bytearray()
    for ordinal, outcome, detail in spec.exact_detail_rules():
        rules.append(ordinal)
        rules.append(outcome)
        rules.extend(detail.to_bytes(2, "little"))
    result["s22_fyg8_p290_detail_rules"] = bytes(rules)
    return result


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.96 linked descriptor tables differ")
    return {name: receipt(data) for name, data in sorted(actual.items())} | {
        "descriptor_bytes_verified": True,
        "position_pairs_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(implementation_result(Path.cwd()), indent=2, sort_keys=True))
