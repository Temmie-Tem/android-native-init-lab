#!/usr/bin/env python3
"""Versioned P2.57 proof-bound display-closure source contract."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p244_e2_provider_sources as p244
import s22plus_fyg8_p245_source_contract as p245
import s22plus_fyg8_p248_source_contract as p248
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p254_source_contract as p254
import s22plus_fyg8_p257_contract_spec as spec
import s22plus_fyg8_p257_e1_decoder as decoder


CONTRACT_ID = "s22plus-fyg8-p257-e2-qnoc-display-closure-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P257-E2-DISPLAY-CLOSURE-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p257_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p257_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P257_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p257_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P257_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P257_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P257_DISPLAY_CLOSURE_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P257-DISPLAY-CLOSURE-SOURCE-CHECK-V1"
).digest()[:16]

MODULE_PLAN_COUNT = spec.MODULE_PLAN_COUNT
GENERATED_KEYS = p252.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p252.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p257_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p257_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p257_e2_plan.h",
}
COMMON_SOURCE_PATHS = dict(p254.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS["p254_source_contract"] = COMMON_SOURCE_PATHS.pop(
    "source_contract"
)
COMMON_SOURCE_PATHS["p254_decoder_adapter"] = COMMON_SOURCE_PATHS.pop(
    "decoder_adapter"
)
COMMON_SOURCE_PATHS["p253_linked_validator_adapter"] = (
    COMMON_SOURCE_PATHS.pop("linked_validator_adapter")
)
COMMON_SOURCE_PATHS["p253_stock_closure_adapter"] = COMMON_SOURCE_PATHS.pop(
    "stock_closure_adapter"
)
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p257_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p257_contract_spec.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p257_e1_decoder.py"
        ),
        "stock_closure_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p257_e2_stock_closure.py"
        ),
        "linked_validator_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p257_linked_audit.py"
        ),
        "source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_source_contracts.py"
        ),
        "linked_adapter_dispatch": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p234_build_repro_check.py"
        ),
        "candidate_repro_enforcement": Path(
            "workspace/public/src/scripts/revalidation/"
            "build_s22plus_fyg8_p234_candidate.py"
        ),
        "userspace_plan_enforcement": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p234_userspace_build.py"
        ),
    }
)
SOURCE_KEYS = frozenset((*GENERATED_KEYS, *COMMON_SOURCE_PATHS))
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
REACHABLE_VARIANTS = 1 + sum(
    1 + len(spec.failure_details(step))
    for step in spec.STEPS
    if step.kind != spec.KIND_TERMINAL
)

HISTORICAL_GENERATED_SHA256 = {
    p245.CONTRACT_ID: dict(p244.GENERATED_SHA256),
    p248.CONTRACT_ID: {
        "checkpoint": (
            "bc2ed2ba799830d0f102a0a7f042e272"
            "f611f9789a407fa9e169babe98ae538c"
        ),
        "patch": (
            "5ab7ac478a290f3387e8100b447feb8d"
            "a54c86591128710451b61f201e14cb9b"
        ),
        "plan": (
            "874525283fe7d47ddbbddfa99b789eba"
            "73e283599a349af22c395014dec5f415"
        ),
        "runtime": (
            "be7f994066ed419d0847aece1f96c5d"
            "ae6246af34d52b71132eca62568bbcff5"
        ),
    },
    p252.CONTRACT_ID: {
        "checkpoint": (
            "9440c4264e42c84482bfe162df59c254"
            "1336e5ef4b32baf1abc6b470aca9feb2"
        ),
        "patch": (
            "c55e8a9a653cd2abc6680b56f64c065"
            "09daa857e010f2da81825bf932de0deed"
        ),
        "plan": (
            "874525283fe7d47ddbbddfa99b789eba"
            "73e283599a349af22c395014dec5f415"
        ),
        "runtime": (
            "b69a0b58138427a0196ca356b6a1635"
            "c8a0d3f39ee2afe67ef634c944936a900"
        ),
    },
    p254.CONTRACT_ID: {
        "checkpoint": (
            "9440c4264e42c84482bfe162df59c254"
            "1336e5ef4b32baf1abc6b470aca9feb2"
        ),
        "patch": (
            "c55e8a9a653cd2abc6680b56f64c065"
            "09daa857e010f2da81825bf932de0deed"
        ),
        "plan": (
            "874525283fe7d47ddbbddfa99b789eba"
            "73e283599a349af22c395014dec5f415"
        ),
        "runtime": (
            "b69a0b58138427a0196ca356b6a1635"
            "c8a0d3f39ee2afe67ef634c944936a900"
        ),
    },
}


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P257 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p252.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P257


def _replace_exact(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    count: int = 1,
    label: str,
) -> bytes:
    actual = data.count(old)
    if actual != count:
        raise SourceContractError(
            f"{label} replacement count {actual}, expected {count}"
        )
    return data.replace(old, new)


def _p257_plan(base: bytes) -> bytes:
    value = _replace_exact(
        base,
        b"S22PLUS_FYG8_P244_E2_PLAN_H",
        b"S22PLUS_FYG8_P257_E2_PLAN_H",
        count=2,
        label="P2.57 plan include guard",
    )
    rows = tuple(
        re.finditer(
            rb'^    \{"[^"]+", "[^"]+", "[^"]*"\},\n',
            value,
            re.MULTILINE,
        )
    )
    insertion = spec.DISPCC_INSERTION
    if (
        len(rows) != spec.HISTORICAL_MODULE_PLAN_COUNT
        or not 0 <= insertion.index < len(rows)
    ):
        raise SourceContractError(
            "P2.57 historical plan cannot accept descriptor insertion"
        )
    row = (
        f'    {{"{insertion.file}", "{insertion.runtime_name}", '
        f'"{insertion.params}"}},\n'
    ).encode("ascii")
    offset = rows[insertion.index].start()
    return value[:offset] + row + value[offset:]


def _p257_runtime_base(base: bytes) -> bytes:
    value = _replace_exact(
        base,
        b'#include "s22plus_fyg8_p244_e2_plan.h"',
        b'#include "s22plus_fyg8_p257_e2_plan.h"',
        label="P2.57 runtime plan include",
    )
    value = _replace_exact(
        value,
        b"#define S22_P241_GATE_STAGE_BASE 0x7bU",
        b"#define S22_P241_GATE_STAGE_BASE 0x7cU",
        label="P2.57 gate stage base",
    )
    return _replace_exact(
        value,
        b"S22PLUS_O2_MODULE_PLAN_COUNT == 59U",
        b"S22PLUS_O2_MODULE_PLAN_COUNT == 60U",
        label="P2.57 runtime module count",
    )


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    base = p244.generate(repository)
    derived = {
        "plan": _p257_plan(base["plan"]),
        "runtime": p248.transform_runtime(
            _p257_runtime_base(base["runtime"])
        ),
        "checkpoint": p248.transform_checkpoint(
            base["checkpoint"], spec.STEPS
        ),
        "patch": p248.transform_patch(base["patch"], spec.STEPS),
    }
    return {
        "plan": derived["plan"],
        "runtime": p252.transform_runtime(
            derived["runtime"], contract_spec=spec
        ),
        "checkpoint": p252.transform_checkpoint(
            derived["checkpoint"], contract_spec=spec
        ),
        "patch": p252.transform_patch(
            derived["patch"], contract_spec=spec
        ),
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.57 source {name}"
        )
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.57 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def _module_rows(plan: bytes) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        tuple(value.decode("ascii") for value in match)
        for match in re.findall(
            rb'^\s+\{"([^"]+\.ko)", "([^"]+)", "([^"]*)"\},$',
            plan,
            re.MULTILINE,
        )
    )


def _historical_generation_audit(root: Path) -> dict[str, Any]:
    provider_actual = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in p244.generate(root).items()
    }
    if provider_actual != HISTORICAL_GENERATED_SHA256[p245.CONTRACT_ID]:
        raise SourceContractError("historical P2.45 generated bytes changed")
    result: dict[str, Any] = {
        p245.CONTRACT_ID: provider_actual,
    }
    modules = (p248, p252, p254)
    for module in modules:
        actual = {
            name: hashlib.sha256(data).hexdigest()
            for name, data in module.generate(root).items()
        }
        expected = HISTORICAL_GENERATED_SHA256[module.CONTRACT_ID]
        if actual != expected:
            raise SourceContractError(
                f"historical generated bytes changed: {module.CONTRACT_ID}"
            )
        result[module.CONTRACT_ID] = actual
    return result


def _reserved_detail_audit() -> dict[str, Any]:
    listed = set(spec.CLASSIFIER_VALUES)
    checked = 0
    for step in spec.STEPS:
        for detail in range(0xA00, 0x1000):
            expected = step.stage == spec.SSUSB_STAGE and detail in listed
            if spec.failure_detail_allowed(step, detail) is not expected:
                raise SourceContractError(
                    "P2.57 reserved detail acceptance drifted"
                )
            checked += 1
    return {
        "stage_detail_pairs_checked": checked,
        "unlisted_reserved_rejected": True,
        "verified": True,
    }


def _generated_semantics(
    generated: dict[str, bytes], historical_plan: bytes
) -> dict[str, Any]:
    old_rows = _module_rows(historical_plan)
    rows = _module_rows(generated["plan"])
    insertion = spec.DISPCC_INSERTION
    inserted = (insertion.row,)
    index = insertion.index
    if (
        len(old_rows) != spec.HISTORICAL_MODULE_PLAN_COUNT
        or len(rows) != MODULE_PLAN_COUNT
        or rows[:index] != old_rows[:index]
        or rows[index : index + 1] != inserted
        or rows[index + 1 :] != old_rows[index:]
    ):
        raise SourceContractError("P2.57 plan is not one exact insertion")
    if generated["runtime"].count(
        p252._render_runtime_classifier_table(spec)
    ) != 1:
        raise SourceContractError("P2.57 runtime classifier table drifted")
    if generated["checkpoint"].count(
        p252._render_checkpoint_classifier_tables(spec)
    ) != 1:
        raise SourceContractError("P2.57 checkpoint classifier table drifted")
    if generated["patch"].count(
        p252._render_kernel_classifier_tables(spec)
    ) != 1:
        raise SourceContractError("P2.57 kernel classifier table drifted")
    required_runtime = (
        '#include "s22plus_fyg8_p257_e2_plan.h"',
        "#define S22_P241_GATE_STAGE_BASE 0x7cU",
        "S22PLUS_O2_MODULE_PLAN_COUNT == 60U",
        "#define S22_P252_SSUSB_STAGE 0x85U",
        "sizeof(k_p252_bind_classifiers[0]) == 18U",
    )
    runtime = generated["runtime"].decode("ascii")
    if any(runtime.count(value) != 1 for value in required_runtime):
        raise SourceContractError("P2.57 runtime geometry drifted")
    expected_tables = linked_table_bytes()
    if (
        len(expected_tables["s22_fyg8_e2_sequence"]) != 81
        or len(expected_tables["s22_fyg8_e2_classifier_stages"]) != 20
        or expected_tables["s22_fyg8_e2_sequence"][-1] != 0x8F
    ):
        raise SourceContractError("P2.57 linked descriptor geometry drifted")
    return {
        "module_count": len(rows),
        "dispcc_item_index": insertion.index,
        "dispcc_stage": spec.MODULE_STAGE_FIRST + insertion.index,
        "qnoc_item_index": insertion.index + 1,
        "qnoc_stage": spec.MODULE_STAGE_FIRST + insertion.index + 1,
        "step_count": len(spec.STEPS),
        "classifier_detail_count": len(spec.CLASSIFIER_DETAILS),
        "single_module_insertion": True,
        "descriptor_derived": True,
        "verified": True,
    }


def _registration_audit(root: Path) -> dict[str, Any]:
    sources = source_bytes(root)
    required = {
        "source_contract_selector": (
            b"import s22plus_fyg8_p257_source_contract as p257",
            b"p257.CONTRACT_ID: p257",
        ),
        "stock_closure_adapter": (
            b"EXPECTED_MODULE_COUNT = 60",
            b'source_contract.require(source_contract_id, "E2")',
        ),
        "linked_validator_adapter": (
            b'ADAPTER_ID = "s22plus-fyg8-p257-linked-audit-v1"',
            b"source_contract_module=p257",
        ),
        "linked_adapter_dispatch": (
            CONTRACT_ID.encode("ascii"),
            b"s22plus_fyg8_p257_linked_audit",
        ),
        "candidate_repro_enforcement": (
            CONTRACT_ID.encode("ascii"),
            b"P2.57 linked audit adapter mismatch",
        ),
        "userspace_plan_enforcement": (
            b'getattr(selected.module, "MODULE_PLAN_COUNT", 59)',
        ),
    }
    for name, tokens in required.items():
        if any(token not in sources[name] for token in tokens):
            raise SourceContractError(
                f"P2.57 execution registration is incomplete: {name}"
            )
    return {
        name: receipt(sources[name]) for name in sorted(required)
    } | {"verified": True}


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p254.generate(root)
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.57 generation is not deterministic")
    semantics = _generated_semantics(first, historical["plan"])
    historical_audit = _historical_generation_audit(root)
    with tempfile.TemporaryDirectory(prefix="s22-p257-") as temporary:
        directory = Path(temporary)
        try:
            patch = p252._audit_patch(root, first["patch"], directory)
            userspace = p252._audit_userspace(
                root,
                first,
                directory,
                materialized_filenames=MATERIALIZED_FILENAMES,
                source_check_run_id=SOURCE_CHECK_RUN_ID,
            )
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p257_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "historical_generated_unchanged": historical_audit,
        "generated_semantics": semantics,
        "reserved_details": _reserved_detail_audit(),
        "registrations": _registration_audit(root),
        "patch": patch,
        "linked_userspace": userspace,
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "ssusb_stage": spec.SSUSB_STAGE,
            "ssusb_gate_index": spec.SSUSB_GATE_INDEX,
            "classifier_details": [
                {
                    "value": row.value,
                    "name": row.name,
                    "category": row.category,
                    "path": row.path,
                    "expected_symlink_basename": (
                        row.expected_symlink_basename
                    ),
                }
                for row in spec.CLASSIFIER_DETAILS
            ],
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
    try:
        return p252.validate_reachable_records(
            run_id,
            contract_spec=spec,
            decoder_module=decoder,
            expected_variants=REACHABLE_VARIANTS,
        )
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def linked_table_bytes() -> dict[str, bytes]:
    return p252.linked_table_bytes_for(spec)


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.57 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "classifier_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = p252.LINKED_VALIDATOR_SYMBOLS


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
