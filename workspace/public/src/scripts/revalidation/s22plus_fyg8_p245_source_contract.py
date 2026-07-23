#!/usr/bin/env python3
"""Describe the versioned P2.45 E2 provider source contract host-only."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p232_e1_latest_stage_design as model  # noqa: E402
import s22plus_fyg8_p233_e1_static_checker as p233  # noqa: E402
import s22plus_fyg8_p241_e2_static_checker as p241  # noqa: E402
import s22plus_fyg8_p243_rpmh_dependency_audit as p243  # noqa: E402
import s22plus_fyg8_p244_e2_provider_sources as p244_sources  # noqa: E402
import s22plus_fyg8_p244_e2_static_checker as p244_checker  # noqa: E402
import s22plus_fyg8_p245_e1_decoder as decoder  # noqa: E402


CONTRACT_ID = "s22plus-fyg8-p245-e2-provider-v1"
PROFILE = "E2"
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P245-E2-PROVIDER-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p245_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p245_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P245_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p245_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P245_CANDIDATE_CONTRACT_HOST_ONLY"

GENERATED_KEYS = (
    "base_patch",
    "checkpoint_client",
    "runtime_wrapper",
    "plan_header",
)
GENERATED_OUTPUT_NAMES = {
    "base_patch": "patch",
    "checkpoint_client": "checkpoint",
    "runtime_wrapper": "runtime",
    "plan_header": "plan",
}
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p244_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p244_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p244_e2_plan.h",
}
COMMON_SOURCE_PATHS = {
    "source_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p245_source_contract.py"
    ),
    "loader_core": Path(
        "workspace/public/src/native-init/s22plus_o2_loader_core.h"
    ),
    "legacy_runtime": p233.DEFAULT_LEGACY_RUNTIME,
    "legacy_header": p233.DEFAULT_HEADER,
    "child": p241.DEFAULT_CHILD,
    "decoder_adapter": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p245_e1_decoder.py"
    ),
    "legacy_decoder": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p233_e1_decoder.py"
    ),
    "design_model": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p232_e1_latest_stage_design.py"
    ),
    "source_checker": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p244_e2_static_checker.py"
    ),
    "provider_sources": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p244_e2_provider_sources.py"
    ),
    "dependency_audit": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p243_rpmh_dependency_audit.py"
    ),
    "planner": Path(
        "workspace/public/src/scripts/revalidation/s22plus_o2_module_plan.py"
    ),
    "dtbo_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p241_dtbo_role_contract.py"
    ),
    "stock_closure_adapter": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p245_e2_stock_closure.py"
    ),
    "legacy_stock_closure": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p242_e2_stock_closure.py"
    ),
}
SOURCE_KEYS = frozenset((*GENERATED_KEYS, *COMMON_SOURCE_PATHS))
STAGE_SEQUENCE = (
    model.E1_LOCAL_SEQUENCE
    + tuple(range(p244_sources.MODULE_STAGE_FIRST, p244_sources.MODULE_STAGE_LAST + 1))
    + tuple(range(p244_sources.GATE_STAGE_FIRST, p244_sources.GATE_STAGE_LAST + 1))
    + (p244_sources.SUCCESS_STAGE,)
)
REACHABLE_VARIANTS = (len(STAGE_SEQUENCE) - 1) * 4096 + 1


class SourceContractError(ValueError):
    pass


@dataclass(frozen=True)
class SourceContract:
    contract_id: str
    profile: str
    run_id_domain: bytes
    stage_sequence: tuple[int, ...]
    terminal_stage: int
    reachable_variants: int
    source_keys: frozenset[str]


P245 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=p244_sources.SUCCESS_STAGE,
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
    return P245


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = p244_sources.generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p233.read_direct(root / path, f"P2.45 source {name}")
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.45 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def implementation_result(root: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "PYTHONPYCACHEPREFIX": "/tmp/android-native-init-pycache",
        }
    )
    completed = subprocess.run(
        [sys.executable, str(Path(p244_checker.__file__).resolve())],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    try:
        result = json.loads(completed.stdout.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SourceContractError(
            "isolated P2.44 implementation checker returned invalid JSON"
        ) from exc
    if (
        completed.returncode != 0
        or not isinstance(result, dict)
        or result.get("schema") != p244_checker.SCHEMA
        or result.get("verdict") != p244_checker.VERDICT
        or result.get("safety", {}).get("host_only") is not True
        or result.get("safety", {}).get("device_contact") is not False
    ):
        detail = completed.stderr.decode("utf-8", "replace")[-2000:]
        raise SourceContractError(
            f"isolated P2.44 implementation closure failed: {detail}"
        )
    return result


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    if len(run_id) != model.RUN_ID_SIZE or not any(run_id):
        raise SourceContractError("P2.45 run ID must be one nonzero 128-bit value")
    header = (
        model.LONG_FAMILY
        + bytes(
            [
                (model.FORMAT_VERSION << 4)
                | model.PROFILE_NUMBERS[PROFILE]
            ]
        )
        + run_id
    )
    if len(header) != model.LONG_HEADER_SIZE:
        raise SourceContractError("P2.45 record header size changed")

    def item_index(stage: int) -> int:
        if p244_sources.MODULE_STAGE_FIRST <= stage <= p244_sources.MODULE_STAGE_LAST:
            return stage - p244_sources.MODULE_STAGE_FIRST
        if p244_sources.GATE_STAGE_FIRST <= stage <= p244_sources.GATE_STAGE_LAST:
            return stage - p244_sources.GATE_STAGE_FIRST
        return 0

    def encoded_slot(
        generation: int,
        stage: int,
        outcome: int,
        detail: int,
    ) -> bytes:
        try:
            return decoder.encode_slot(
                header,
                generation=generation,
                stage=stage,
                outcome=outcome,
                item_index=item_index(stage),
                detail=detail,
            )
        except decoder.DecodeError as exc:
            raise SourceContractError(str(exc)) from exc

    entry = encoded_slot(
        0,
        model.STAGES["ENTRY"],
        model.OUTCOME_PROGRESS,
        0,
    )
    record = header + entry + bytes(model.SLOT_SIZE)
    model._validate_record_families(record)
    decoder.decode_record(
        record,
        expected_profile=PROFILE,
        expected_run_id=run_id,
    )
    model.unsat_record(PROFILE, run_id)
    checked = 0
    for generation, stage in enumerate(STAGE_SEQUENCE, 1):
        terminal = stage == p244_sources.SUCCESS_STAGE
        cases = (
            ((model.OUTCOME_SUCCESS, 0),)
            if terminal
            else ((model.OUTCOME_PROGRESS, 0),)
            + tuple(
                (model.OUTCOME_FAILURE, detail)
                for detail in range(1, 4096)
            )
        )
        for outcome, detail in cases:
            candidate = bytearray(record)
            start = (
                model.LONG_HEADER_SIZE
                + (generation & 1) * model.SLOT_SIZE
            )
            candidate[start : start + model.SLOT_SIZE] = encoded_slot(
                generation, stage, outcome, detail
            )
            model._validate_record_families(bytes(candidate))
            decoded = decoder.decode_record(
                bytes(candidate),
                expected_profile=PROFILE,
                expected_run_id=run_id,
            )
            if decoded["active"] != {
                "slot_id": generation & 1,
                "generation": generation,
                "stage": stage,
                "outcome": outcome,
                "item_index": item_index(stage),
                "detail": detail,
            }:
                raise SourceContractError(
                    "P2.45 decoder changed a reachable active slot"
                )
            checked += 1
        if not terminal:
            start = (
                model.LONG_HEADER_SIZE
                + (generation & 1) * model.SLOT_SIZE
            )
            updated = bytearray(record)
            updated[start : start + model.SLOT_SIZE] = encoded_slot(
                generation, stage, model.OUTCOME_PROGRESS, 0
            )
            record = bytes(updated)
    if (
        checked != REACHABLE_VARIANTS
        or model.PROFILE_STAGE_SEQUENCES[PROFILE] == STAGE_SEQUENCE
        or model.STAGES["E2_GATE_7"] != 0x82
    ):
        raise SourceContractError("P2.45 pure reachability closure failed")
    return {
        "reachable_slot_variants": checked,
        "profiles": [PROFILE],
        "checked_run_ids": {PROFILE: run_id.hex()},
        "adjacent_slot_combinations_verified": True,
        "zero_crc_count": 0,
        "family_collision_count": 0,
        "decoder_policy_id": decoder.POLICY_ID,
        "verified": True,
    }
