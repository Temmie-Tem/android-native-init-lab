#!/usr/bin/env python3
"""Versioned P2.48 E2 source contract and bounded source adapter."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
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
import s22plus_fyg8_p245_source_contract as p245  # noqa: E402
import s22plus_fyg8_p248_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p248_e1_decoder as decoder  # noqa: E402


CONTRACT_ID = "s22plus-fyg8-p248-e2-derived-validator-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P248-E2-DERIVED-VALIDATOR-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p248_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p248_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P248_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p248_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P248_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P248_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P248_DERIVED_CONTRACT_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P248-DERIVED-CONTRACT-SOURCE-CHECK-V1"
).digest()[:16]

GENERATED_KEYS = p245.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p245.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p248_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p248_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p244_e2_plan.h",
}
COMMON_SOURCE_PATHS = {
    name: path
    for name, path in p245.COMMON_SOURCE_PATHS.items()
    if name
    not in {
        "source_contract",
        "decoder_adapter",
        "source_checker",
        "provider_sources",
        "stock_closure_adapter",
    }
}
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p248_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p248_contract_spec.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p248_e1_decoder.py"
        ),
        "decoder_layout_delegate": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p245_e1_decoder.py"
        ),
        "provider_sources": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p244_e2_provider_sources.py"
        ),
        "historical_source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p245_source_contract.py"
        ),
        "stock_closure_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p245_e2_stock_closure.py"
        ),
        "source_contract_selector": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_source_contracts.py"
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


P248 = SourceContract(
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
    return P248


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


def _replace_span(
    data: bytes,
    start: bytes,
    stop: bytes,
    replacement: bytes,
    *,
    label: str,
) -> bytes:
    if data.count(start) != 1:
        raise SourceContractError(f"{label} start marker is not unique")
    begin = data.index(start)
    end = data.find(stop, begin)
    if end < 0:
        raise SourceContractError(f"{label} stop marker is absent")
    return data[:begin] + replacement + data[end:]


def _render_checkpoint_steps(
    steps: tuple[spec.Step, ...] = spec.STEPS,
) -> bytes:
    spec.validate_steps(steps)
    gate_count = sum(step.kind == spec.KIND_GATE for step in steps)
    lines = [
        "#define S22_P248_STEP_NORMAL 0U",
        "#define S22_P248_STEP_GATE 1U",
        "#define S22_P248_STEP_TERMINAL 2U",
        "#define S22_P248_DETAIL_ERRNO_MAX 0x7ffU",
        "#define S22_P248_DETAIL_REGRESSION_BASE 0x800U",
        "#define S22_P248_DETAIL_REGRESSION_MAX 0x8ffU",
        "#define S22_P248_DETAIL_READ_ERROR_BASE 0x900U",
        "#define S22_P248_DETAIL_READ_ERROR_MAX 0x9ffU",
        "",
        "struct s22_p248_step {",
        "    uint8_t stage;",
        "    uint8_t item_index;",
        "    uint8_t kind;",
        "};",
        "",
        "static const struct s22_p248_step k_p248_e2_steps[] = {",
    ]
    kind_values = {
        spec.KIND_LOCAL: "S22_P248_STEP_NORMAL",
        spec.KIND_MODULE: "S22_P248_STEP_NORMAL",
        spec.KIND_GATE: "S22_P248_STEP_GATE",
        spec.KIND_TERMINAL: "S22_P248_STEP_TERMINAL",
    }
    lines.extend(
        f"    {{0x{step.stage:02x}U, {step.item_index}U, "
        f"{kind_values[step.kind]}}},"
        for step in steps
    )
    lines.extend(
        (
            "};",
            "",
            "_Static_assert(",
            "    sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]) <= 255U,",
            '    "P2.48 generation fits one byte");',
            "_Static_assert(",
            f"    {gate_count}U <= 256U,",
            '    "P2.48 gate detail index fits one byte");',
        )
    )
    return "\n".join(lines).encode("ascii")


def _render_checkpoint_next_stage() -> bytes:
    return (
        """#if S22PLUS_FYG8_P233_PROFILE == 3
    if (stage == 0U) {
        return k_p248_e2_steps[0].stage;
    }
    for (size_t index = 0;
         index + 1U < sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
         ++index) {
        if (k_p248_e2_steps[index].stage == stage) {
            return k_p248_e2_steps[index + 1U].stage;
        }
    }
    return 0U;
#else
"""
    ).encode("ascii")


def _render_checkpoint_item_validation() -> bytes:
    return (
        """#if S22PLUS_FYG8_P233_PROFILE == 3
    for (size_t index = 0;
         index < sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
         ++index) {
        if (k_p248_e2_steps[index].stage == stage) {
            return item_index == k_p248_e2_steps[index].item_index;
        }
    }
    return 0;
"""
    ).encode("ascii")


def _checkpoint_detail_helper(gate_count: int = spec.GATE_COUNT) -> bytes:
    template = """static int p248_detail_allowed(
    uint8_t stage, uint8_t outcome, uint16_t detail) {
#if S22PLUS_FYG8_P233_PROFILE == 3
    const struct s22_p248_step *step = NULL;
    for (size_t index = 0;
         index < sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
         ++index) {
        if (k_p248_e2_steps[index].stage == stage) {
            step = &k_p248_e2_steps[index];
            break;
        }
    }
    if (step == NULL) {
        return 0;
    }
    if (step->kind == S22_P248_STEP_TERMINAL) {
        return outcome == S22_P233_OUTCOME_SUCCESS && detail == 0U;
    }
    if (outcome == S22_P233_OUTCOME_PROGRESS) {
        return detail == 0U;
    }
    if (outcome != S22_P233_OUTCOME_FAILURE || detail == 0U) {
        return 0;
    }
    if (detail <= S22_P248_DETAIL_ERRNO_MAX) {
        return 1;
    }
    if (step->kind != S22_P248_STEP_GATE) {
        return 0;
    }
    uint8_t encoded_index = (uint8_t)(detail & 0xffU);
    if (encoded_index >= __GATE_COUNT__U) {
        return 0;
    }
    if (detail >= S22_P248_DETAIL_REGRESSION_BASE &&
        detail <= S22_P248_DETAIL_REGRESSION_MAX) {
        return encoded_index < step->item_index;
    }
    if (detail >= S22_P248_DETAIL_READ_ERROR_BASE &&
        detail <= S22_P248_DETAIL_READ_ERROR_MAX) {
        return encoded_index <= step->item_index;
    }
    return 0;
#else
    uint8_t terminal = terminal_stage();
    return (outcome == S22_P233_OUTCOME_PROGRESS &&
            stage != terminal && detail == 0U) ||
        (outcome == S22_P233_OUTCOME_SUCCESS &&
         stage == terminal && detail == 0U) ||
        (outcome == S22_P233_OUTCOME_FAILURE &&
         stage != terminal && detail != 0U);
#endif
}

"""
    return template.replace(
        "__GATE_COUNT__", str(gate_count)
    ).encode("ascii")


def transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"#define S22_P241_STAGE_E2_MODULE_0 0x40U\n",
        b"",
        label="checkpoint module base duplication",
    )
    value = _replace_exact(
        value,
        b"#define S22_P241_STAGE_E2_MODULE_58 0x7aU\n",
        b"",
        label="checkpoint module upper bound",
    )
    value = _replace_exact(
        value,
        b"#define S22_P241_STAGE_E2_GATE_0 0x7bU\n",
        b"",
        label="checkpoint gate base duplication",
    )
    value = _replace_exact(
        value,
        b"#define S22_P244_STAGE_E2_GATE_11 0x86U\n",
        b"",
        label="checkpoint gate upper bound",
    )
    value = _replace_exact(
        value,
        b"#define S22_P241_STAGE_E2_SUCCESS 0x8fU\n",
        _render_checkpoint_steps() + b"\n",
        label="checkpoint descriptor insertion",
    )
    value = _replace_exact(
        value,
        b"#else\n    return S22_P241_STAGE_E2_SUCCESS;\n#endif",
        b"#else\n"
        b"    return k_p248_e2_steps[\n"
        b"        sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]) - 1U\n"
        b"    ].stage;\n"
        b"#endif",
        label="checkpoint terminal derivation",
    )
    value = _replace_span(
        value,
        b"#if S22PLUS_FYG8_P233_PROFILE == 3\n"
        b"    if (stage == 0x00U) {",
        b"#else\n    switch (stage) {",
        _render_checkpoint_next_stage() + b"    switch (stage) {",
        label="checkpoint next-stage descriptor",
    )
    value = _replace_span(
        value,
        b"#if S22PLUS_FYG8_P233_PROFILE == 3\n"
        b"    if (stage >= S22_P241_STAGE_E2_MODULE_0",
        b"#endif\n    if (stage >= S22_R4W1E_STAGE_WDT_MODULE_0",
        _render_checkpoint_item_validation(),
        label="checkpoint item descriptor",
    )
    value = _replace_exact(
        value,
        b"static long publish(\n",
        _checkpoint_detail_helper() + b"static long publish(\n",
        label="checkpoint detail helper",
    )
    old_outcome = (
        b"    if ((outcome == S22_P233_OUTCOME_PROGRESS &&\n"
        b"         (stage == terminal || detail != 0U)) ||\n"
        b"        (outcome == S22_P233_OUTCOME_SUCCESS &&\n"
        b"         (stage != terminal || detail != 0U)) ||\n"
        b"        (outcome == S22_P233_OUTCOME_FAILURE &&\n"
        b"         (stage == terminal || detail == 0U)) ||\n"
        b"        outcome > S22_P233_OUTCOME_FAILURE) {\n"
        b"        return -EINVAL;\n"
        b"    }\n"
    )
    value = _replace_exact(
        value,
        old_outcome,
        b"    if (!p248_detail_allowed(stage, outcome, detail)) {\n"
        b"        return -EINVAL;\n"
        b"    }\n",
        label="checkpoint detail validation",
    )
    value = _replace_exact(
        value,
        b"    struct s22_p233_checkpoint_request request = {0};\n"
        b"    uint8_t terminal = terminal_stage();\n",
        b"    struct s22_p233_checkpoint_request request = {0};\n",
        label="checkpoint obsolete publish terminal",
    )
    old_failure = (
        b"long s22_r4w1e_checkpoint_failure(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t stage,\n"
        b"    uint8_t item_index,\n"
        b"    long operation_error) {\n"
        b"    unsigned long detail = operation_error < 0\n"
        b"        ? (unsigned long)(-operation_error)\n"
        b"        : (unsigned long)operation_error;\n"
        b"    if (detail == 0U) {\n"
        b"        detail = EIO;\n"
        b"    }\n"
        b"    if (detail > 4095U) {\n"
        b"        detail = 4095U;\n"
        b"    }\n"
        b"    return publish(\n"
        b"        client,\n"
        b"        stage,\n"
        b"        S22_P233_OUTCOME_FAILURE,\n"
        b"        item_index,\n"
        b"        (uint16_t)detail);\n"
        b"}"
    )
    new_failure = (
        b"long s22_r4w1e_checkpoint_failure(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t stage,\n"
        b"    uint8_t item_index,\n"
        b"    long operation_error) {\n"
        b"    unsigned long detail;\n"
        b"    if (operation_error < 0) {\n"
        b"        detail = (unsigned long)(-operation_error);\n"
        b"        if (detail > S22_P248_DETAIL_ERRNO_MAX) {\n"
        b"            return -EINVAL;\n"
        b"        }\n"
        b"    } else {\n"
        b"        detail = (unsigned long)operation_error;\n"
        b"    }\n"
        b"    if (detail == 0U) {\n"
        b"        detail = EIO;\n"
        b"    }\n"
        b"    if (detail > S22_P248_DETAIL_READ_ERROR_MAX) {\n"
        b"        return -EINVAL;\n"
        b"    }\n"
        b"    return publish(\n"
        b"        client,\n"
        b"        stage,\n"
        b"        S22_P233_OUTCOME_FAILURE,\n"
        b"        item_index,\n"
        b"        (uint16_t)detail);\n"
        b"}"
    )
    return _replace_exact(
        value,
        old_failure,
        new_failure,
        label="checkpoint raw detail normalization",
    )


def transform_runtime(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"#define S22_P241_DIRENT_BUFFER_SIZE 4096U\n",
        b"#define S22_P241_DIRENT_BUFFER_SIZE 4096U\n"
        b"#define S22_P248_DETAIL_ERRNO_MAX 0x7ffL\n"
        b"#define S22_P248_DETAIL_REGRESSION_BASE 0x800L\n"
        b"#define S22_P248_DETAIL_READ_ERROR_BASE 0x900L\n",
        label="runtime detail bands",
    )
    value = _replace_exact(
        value,
        b"#define S22_P241_SUCCESS_STAGE 0x8fU\n",
        b"",
        label="runtime terminal duplication",
    )
    value = _replace_exact(
        value,
        b"_Static_assert(\n"
        b"    S22_P241_MODULE_STAGE_BASE + "
        b"S22PLUS_O2_MODULE_PLAN_COUNT - 1U == 0x7aU,\n"
        b"    \"E2 module stage range\");\n"
        b"_Static_assert(\n"
        b"    S22_P241_GATE_STAGE_BASE + "
        b"S22PLUS_O2_BIND_GATE_COUNT - 1U == 0x86U,\n"
        b"    \"E2 gate stage range\");\n",
        b"_Static_assert(\n"
        b"    S22PLUS_O2_MODULE_PLAN_COUNT <= 256U,\n"
        b"    \"P2.48 module item index fits one byte\");\n"
        b"_Static_assert(\n"
        b"    S22PLUS_O2_BIND_GATE_COUNT <= 256U,\n"
        b"    \"P2.48 gate item index fits one byte\");\n",
        label="runtime parallel upper bounds",
    )
    old_regression = (
        b"                if (gate_rc != 0) {\n"
        b"                    fail_at(\n"
        b"                        S22_P241_GATE_STAGE_BASE + (uint8_t)index,\n"
        b"                        (uint8_t)index,\n"
        b"                        gate_rc);\n"
        b"                }\n"
    )
    new_regression = (
        b"                if (gate_rc != 0) {\n"
        b"                    long detail = gate_rc == -ENODEV\n"
        b"                        ? S22_P248_DETAIL_REGRESSION_BASE + (long)index\n"
        b"                        : S22_P248_DETAIL_READ_ERROR_BASE + (long)index;\n"
        b"                    fail_at(\n"
        b"                        S22_P241_GATE_STAGE_BASE + (uint8_t)completed,\n"
        b"                        (uint8_t)completed,\n"
        b"                        detail);\n"
        b"                }\n"
    )
    value = _replace_exact(
        value,
        old_regression,
        new_regression,
        label="runtime prior-gate regression",
    )
    old_frontier = (
        b"            } else if (gate_rc != -ENODEV) {\n"
        b"                fail_at(\n"
        b"                    S22_P241_GATE_STAGE_BASE + (uint8_t)index,\n"
        b"                    (uint8_t)index,\n"
        b"                    gate_rc);\n"
        b"            }\n"
    )
    new_frontier = (
        b"            } else if (gate_rc != -ENODEV) {\n"
        b"                long detail = gate_rc < -S22_P248_DETAIL_ERRNO_MAX\n"
        b"                    ? S22_P248_DETAIL_READ_ERROR_BASE + (long)index\n"
        b"                    : gate_rc;\n"
        b"                fail_at(\n"
        b"                    S22_P241_GATE_STAGE_BASE + (uint8_t)index,\n"
        b"                    (uint8_t)index,\n"
        b"                    detail);\n"
        b"            }\n"
    )
    return _replace_exact(
        value,
        old_frontier,
        new_frontier,
        label="runtime frontier read error",
    )


def _kernel_prefixed(lines: list[str]) -> bytes:
    return ("\n".join(f"+{line}" for line in lines) + "\n").encode("ascii")


def _render_kernel_tables(
    steps: tuple[spec.Step, ...] = spec.STEPS,
) -> bytes:
    spec.validate_steps(steps)
    sequence = ", ".join(f"0x{step.stage:02x}" for step in steps)
    items = ", ".join(str(step.item_index) for step in steps)
    kinds = ", ".join(
        "1" if step.kind == spec.KIND_GATE else "2"
        if step.kind == spec.KIND_TERMINAL
        else "0"
        for step in steps
    )
    return _kernel_prefixed(
        [
            "static const u8 s22_fyg8_e2_sequence[] __used = {",
            f"\t{sequence},",
            "};",
            "static const u8 s22_fyg8_e2_items[] __used = {",
            f"\t{items},",
            "};",
            "static const u8 s22_fyg8_e2_kinds[] __used = {",
            f"\t{kinds},",
            "};",
        ]
    )


def _render_kernel_validator(gate_count: int = spec.GATE_COUNT) -> bytes:
    lines = [
        "static noinline __used bool s22_fyg8_e1_expected_item(",
        "\t\tu8 profile, size_t ordinal, size_t count, u8 stage,",
        "\t\tu8 *expected_item)",
        "{",
        "\tif (profile == S22_FYG8_E1_PROFILE_E2) {",
        "\t\tif (count != ARRAY_SIZE(s22_fyg8_e2_items) ||",
        "\t\t\t\tcount != ARRAY_SIZE(s22_fyg8_e2_kinds) ||",
        "\t\t\t\tordinal >= count)",
        "\t\t\treturn false;",
        "\t\t*expected_item = s22_fyg8_e2_items[ordinal];",
        "\t\treturn true;",
        "\t}",
        "\t*expected_item = 0;",
        "\tif (stage >= 0x30 && stage <= 0x34)",
        "\t\t*expected_item = stage - 0x30;",
        "\treturn true;",
        "}",
        "",
        "static bool s22_fyg8_e1_detail_allowed(",
        "\t\tu8 profile, size_t ordinal, size_t count,",
        "\t\tu8 outcome, u16 detail)",
        "{",
        "\tu8 gate_index;",
        "\tu8 encoded_index;",
        "",
        "\tif (ordinal + 1 == count)",
        "\t\treturn outcome == S22_FYG8_E1_SUCCESS && !detail;",
        "\tif (outcome == S22_FYG8_E1_PROGRESS)",
        "\t\treturn !detail;",
        "\tif (outcome != S22_FYG8_E1_FAILURE || !detail)",
        "\t\treturn false;",
        "\tif (profile != S22_FYG8_E1_PROFILE_E2)",
        "\t\treturn detail <= 4095;",
        "\tif (detail <= 0x7ff)",
        "\t\treturn true;",
        "\tif (ordinal >= count || s22_fyg8_e2_kinds[ordinal] != 1)",
        "\t\treturn false;",
        "\tgate_index = s22_fyg8_e2_items[ordinal];",
        "\tencoded_index = detail & 0xff;",
        f"\tif (encoded_index >= {gate_count})",
        "\t\treturn false;",
        "\tif (detail >= 0x800 && detail <= 0x8ff)",
        "\t\treturn encoded_index < gate_index;",
        "\tif (detail >= 0x900 && detail <= 0x9ff)",
        "\t\treturn encoded_index <= gate_index;",
        "\treturn false;",
        "}",
        "",
        "static bool s22_fyg8_e1_request_allowed(",
        "\t\tconst struct s22_fyg8_e1_request *request)",
        "{",
        "\tconst u8 *sequence;",
        "\tsize_t count;",
        "\tsize_t ordinal = s22_fyg8_e1_state.generation;",
        "\tu16 detail = le16_to_cpu(request->detail);",
        "\tu8 expected_item;",
        "",
        "\tsequence = s22_fyg8_e1_sequence(request->profile, &count);",
        "\tif (!sequence || ordinal >= count ||",
        "\t\t\trequest->stage != sequence[ordinal] ||",
        "\t\t\t!s22_fyg8_e1_expected_item(request->profile, ordinal,",
        "\t\t\t\tcount, request->stage, &expected_item) ||",
        "\t\t\trequest->item_index != expected_item)",
        "\t\treturn false;",
        "\treturn s22_fyg8_e1_detail_allowed(",
        "\t\trequest->profile, ordinal, count, request->outcome, detail);",
        "}",
        "",
    ]
    return _kernel_prefixed(lines)


def _recount_kernel_patch_hunks(data: bytes) -> bytes:
    lines = data.splitlines(keepends=True)
    main_prefix = b"@@ -1376,6 +1379,"
    following_prefix = b"@@ -1465,6 +2003,7 @@ static int __ref kernel_init"
    main_indices = [
        index for index, line in enumerate(lines) if line.startswith(main_prefix)
    ]
    following_indices = [
        index
        for index, line in enumerate(lines)
        if line.startswith(following_prefix)
    ]
    if len(main_indices) != 1 or len(following_indices) != 1:
        raise SourceContractError("kernel patch hunk headers changed")
    main_index = main_indices[0]
    following_index = following_indices[0]
    if following_index <= main_index:
        raise SourceContractError("kernel patch hunk order changed")
    new_count = sum(
        line.startswith((b"+", b" "))
        for line in lines[main_index + 1 : following_index]
    )
    old_new_count = 544
    lines[main_index] = (
        f"@@ -1376,6 +1379,{new_count} @@ "
        "static int run_init_process(const char *init_filename)\n"
    ).encode("ascii")
    following_start = 2003 + new_count - old_new_count
    lines[following_index] = (
        f"@@ -1465,6 +{following_start},7 @@ "
        "static int __ref kernel_init(void *unused)\n"
    ).encode("ascii")
    return b"".join(lines)


def transform_patch(
    data: bytes,
    steps: tuple[spec.Step, ...] = spec.STEPS,
) -> bytes:
    spec.validate_steps(steps)
    gate_count = sum(step.kind == spec.KIND_GATE for step in steps)
    value = _replace_span(
        data,
        b"+static const u8 s22_fyg8_e2_sequence[] = {\n",
        b"+\n+static bool s22_fyg8_e1_parse_reg",
        _render_kernel_tables(steps)
        + b"+\n+static bool s22_fyg8_e1_parse_reg",
        label="kernel descriptor tables",
    )
    value = _replace_span(
        value,
        b"+static bool s22_fyg8_e1_request_allowed(\n",
        b"+static void s22_fyg8_e1_record_entry",
        _render_kernel_validator(gate_count)
        + b"+static void s22_fyg8_e1_record_entry",
        label="kernel derived validator",
    )
    return _recount_kernel_patch_hunks(value)


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    base = p244_sources.generate(repository)
    return {
        "plan": base["plan"],
        "runtime": transform_runtime(base["runtime"]),
        "checkpoint": transform_checkpoint(base["checkpoint"]),
        "patch": transform_patch(base["patch"]),
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p233.read_direct(root / path, f"P2.48 source {name}")
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.48 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def _audit_patch(
    root: Path,
    patch: bytes,
    directory: Path,
    steps: tuple[spec.Step, ...] = spec.STEPS,
) -> dict[str, Any]:
    spec.validate_steps(steps)
    gate_count = sum(step.kind == spec.KIND_GATE for step in steps)
    patch_path = directory / "p248.patch"
    patch_path.write_bytes(patch)
    p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=root / p241.DEFAULT_SOURCE,
        label="P2.48 clean-apply check",
    )
    text = patch.decode("ascii")
    if (
        text.count("s22_fyg8_e2_items[] __used") != 1
        or text.count("s22_fyg8_e2_kinds[] __used") != 1
        or text.count(
            "static noinline __used bool s22_fyg8_e1_expected_item"
        )
        != 1
        or "request->stage >= 0x7b && request->stage <= 0x82" in text
        or "request->stage <= 0x86" in text
        or f"encoded_index >= {gate_count}" not in text
    ):
        raise SourceContractError("P2.48 kernel validator source mismatch")
    return {**receipt(patch), "clean_apply": True, "verified": True}


def _audit_userspace(
    root: Path, generated: dict[str, bytes], directory: Path
) -> dict[str, Any]:
    plan = directory / MATERIALIZED_FILENAMES["plan_header"]
    runtime = directory / MATERIALIZED_FILENAMES["runtime_wrapper"]
    checkpoint = directory / MATERIALIZED_FILENAMES["checkpoint_client"]
    plan.write_bytes(generated["plan"])
    runtime.write_bytes(generated["runtime"])
    checkpoint.write_bytes(generated["checkpoint"])
    define = p233._run_id_define(SOURCE_CHECK_RUN_ID)
    outputs: list[bytes] = []
    for suffix in ("a", "b"):
        output = directory / f"init-{suffix}"
        p233.run_checked(
            [
                "aarch64-linux-gnu-gcc",
                *p233.legacy_e1.COMPILE_FLAGS,
                "-DS22PLUS_FYG8_P233_PROFILE=3",
                f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
                "-I",
                str(directory),
                "-I",
                str(root / "workspace/public/src/native-init"),
                str(runtime),
                str(checkpoint),
                "-o",
                str(output),
            ],
            cwd=root,
            label=f"P2.48 deterministic userspace link {suffix}",
        )
        outputs.append(output.read_bytes())
    if outputs[0] != outputs[1]:
        raise SourceContractError("P2.48 repeated userspace link differs")
    file_text = p233.run_checked(
        ["file", "-b", str(directory / "init-a")],
        cwd=root,
        label="P2.48 userspace file inspection",
    ).stdout.decode("ascii", "replace")
    if "ELF 64-bit LSB executable, ARM aarch64" not in file_text:
        raise SourceContractError("P2.48 userspace output is not AArch64 ELF")
    return {
        **receipt(outputs[0]),
        "static_aarch64": "statically linked" in file_text,
        "two_link_reproducible": True,
        "verified": True,
    }


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p244_sources.build_result()
    if historical["verdict"] != p244_sources.VERDICT:
        raise SourceContractError("historical P2.44 generation no longer passes")
    first = generate(root)
    second = generate(root)
    if first != second or first["plan"] != p244_sources.generate(root)["plan"]:
        raise SourceContractError("P2.48 generation is not deterministic")
    runtime = first["runtime"].decode("ascii")
    checkpoint = first["checkpoint"].decode("ascii")
    required = (
        "S22_P248_DETAIL_REGRESSION_BASE",
        "S22_P248_DETAIL_READ_ERROR_BASE",
        "S22_P241_GATE_STAGE_BASE + (uint8_t)completed",
        "k_p248_e2_steps[]",
        "p248_detail_allowed",
        "detail > S22_P248_DETAIL_ERRNO_MAX",
    )
    if any(token not in runtime + checkpoint for token in required):
        raise SourceContractError("P2.48 userspace source semantics are incomplete")
    if (
        "S22_P244_STAGE_E2_GATE_11" in checkpoint
        or "S22_P241_STAGE_E2_MODULE_58" in checkpoint
    ):
        raise SourceContractError("P2.48 checkpoint retains a parallel upper bound")
    with tempfile.TemporaryDirectory(prefix="s22-p248-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, directory)
    return {
        "schema": "s22plus_fyg8_p248_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "historical_p244_generated": historical["generated"],
        "descriptor": {
            "step_count": len(spec.STEPS),
            "module_start_ordinal": spec.MODULE_START_ORDINAL,
            "gate_start_ordinal": spec.GATE_START_ORDINAL,
            "gate_count": spec.GATE_COUNT,
            "terminal_ordinal": spec.TERMINAL_ORDINAL,
            "detail_bands": {
                "errno": [spec.DETAIL_ERRNO_MIN, spec.DETAIL_ERRNO_MAX],
                "regression": [
                    spec.DETAIL_REGRESSION_BASE,
                    spec.DETAIL_REGRESSION_MAX,
                ],
                "read_error": [
                    spec.DETAIL_READ_ERROR_BASE,
                    spec.DETAIL_READ_ERROR_MAX,
                ],
                "reserved": [spec.DETAIL_RESERVED_MIN, spec.DETAIL_MAX],
            },
        },
        "patch": patch,
        "linked_userspace": userspace,
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
    if len(run_id) != model.RUN_ID_SIZE or not any(run_id):
        raise SourceContractError("P2.48 run ID must be one nonzero 128-bit value")
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
    entry = decoder.encode_slot(
        header,
        generation=0,
        stage=model.STAGES["ENTRY"],
        outcome=model.OUTCOME_PROGRESS,
        item_index=0,
        detail=0,
    )
    record = header + entry + bytes(model.SLOT_SIZE)
    checked = 0
    for generation, step in enumerate(spec.STEPS, 1):
        cases = (
            ((model.OUTCOME_SUCCESS, 0),)
            if step.kind == spec.KIND_TERMINAL
            else ((model.OUTCOME_PROGRESS, 0),)
            + tuple(
                (model.OUTCOME_FAILURE, detail)
                for detail in spec.failure_details(step)
            )
        )
        for outcome, detail in cases:
            candidate = bytearray(record)
            start = model.LONG_HEADER_SIZE + (generation & 1) * model.SLOT_SIZE
            candidate[start : start + model.SLOT_SIZE] = decoder.encode_slot(
                header,
                generation=generation,
                stage=step.stage,
                outcome=outcome,
                item_index=step.item_index,
                detail=detail,
            )
            decoded = decoder.decode_record(
                bytes(candidate),
                expected_profile=PROFILE,
                expected_run_id=run_id,
            )
            if decoded["active"] != {
                "slot_id": generation & 1,
                "generation": generation,
                "stage": step.stage,
                "outcome": outcome,
                "item_index": step.item_index,
                "detail": detail,
            }:
                raise SourceContractError(
                    "P2.48 decoder changed a reachable active slot"
                )
            checked += 1
        if step.kind != spec.KIND_TERMINAL:
            start = model.LONG_HEADER_SIZE + (generation & 1) * model.SLOT_SIZE
            updated = bytearray(record)
            updated[start : start + model.SLOT_SIZE] = decoder.encode_slot(
                header,
                generation=generation,
                stage=step.stage,
                outcome=model.OUTCOME_PROGRESS,
                item_index=step.item_index,
                detail=0,
            )
            record = bytes(updated)
    if checked != REACHABLE_VARIANTS:
        raise SourceContractError("P2.48 reachable-record count mismatch")
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


def linked_table_bytes() -> dict[str, bytes]:
    kind_values = {
        spec.KIND_LOCAL: 0,
        spec.KIND_MODULE: 0,
        spec.KIND_GATE: 1,
        spec.KIND_TERMINAL: 2,
    }
    return {
        "s22_fyg8_e2_sequence": bytes(step.stage for step in spec.STEPS),
        "s22_fyg8_e2_items": bytes(step.item_index for step in spec.STEPS),
        "s22_fyg8_e2_kinds": bytes(kind_values[step.kind] for step in spec.STEPS),
    }


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.48 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = ("s22_fyg8_e1_expected_item",)


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    expected_item = disassembly.get("s22_fyg8_e1_expected_item")
    writer_calls = calls.get("s22_fyg8_e1_write")
    if not isinstance(expected_item, str) or not isinstance(writer_calls, list):
        raise SourceContractError("P2.48 linked validator evidence is incomplete")
    if "s22_fyg8_e1_expected_item" not in writer_calls:
        raise SourceContractError(
            "P2.48 linked writer does not call the derived item validator"
        )
    item_address = symbol_addresses.get("s22_fyg8_e2_items")
    if not isinstance(item_address, int):
        raise SourceContractError("P2.48 linked item-table address is missing")
    register_values: dict[str, int] = {}
    loads_item_table = False
    for line in expected_item.splitlines():
        instruction = re.search(
            r"^\s*[0-9a-fA-F]+:\s+[0-9a-fA-F]+\s+"
            r"([a-zA-Z0-9_.]+)\s*(.*)$",
            line,
        )
        if instruction is None:
            continue
        mnemonic, operands = instruction.groups()
        adrp = re.search(
            r"^(x\d+),\s*(?:0x)?([0-9a-fA-F]+)\b", operands
        )
        if mnemonic == "adrp" and adrp:
            register_values[adrp.group(1)] = int(adrp.group(2), 16)
            continue
        add = re.search(
            r"^(x\d+),\s*(x\d+),\s*#(0x[0-9a-fA-F]+|\d+)\b",
            operands,
        )
        if mnemonic == "add" and add and add.group(2) in register_values:
            register_values[add.group(1)] = (
                register_values[add.group(2)] + int(add.group(3), 0)
            )
            continue
        move = re.search(r"^(x\d+),\s*(x\d+)\b", operands)
        if mnemonic == "mov" and move and move.group(2) in register_values:
            register_values[move.group(1)] = register_values[move.group(2)]
            continue
        load = re.search(r"^w\d+,\s*\[(x\d+)(?:,|\])", operands)
        if (
            mnemonic == "ldrb"
            and load is not None
            and register_values.get(load.group(1)) == item_address
        ):
            loads_item_table = True
        no_destination = (
            mnemonic == "b"
            or mnemonic.startswith("b.")
            or mnemonic in {
                "bl",
                "blr",
                "br",
                "cmp",
                "cmn",
                "tst",
                "cbz",
                "cbnz",
                "tbz",
                "tbnz",
                "ret",
                "str",
                "strb",
                "strh",
                "stp",
                "stur",
                "sturb",
                "sturh",
            }
        )
        destination = re.match(r"^([wx])(\d+)\b", operands)
        if not no_destination and destination:
            register_values.pop(f"x{destination.group(2)}", None)
    if not loads_item_table:
        raise SourceContractError(
            "P2.48 linked validator does not load the descriptor item table"
        )
    stale_compare = re.compile(
        r"\bcmp\s+[wx]\d+,\s*#(?:0x)?8\b"
    )
    if stale_compare.search(expected_item) or stale_compare.search(
        disassembly["s22_fyg8_e1_write"]
    ):
        raise SourceContractError(
            "P2.48 linked validator retains the stale eight-item compare"
        )
    return {
        "writer_calls_derived_validator": True,
        "validator_loads_item_table": True,
        "stale_eight_item_compare_absent": True,
        "verified": True,
    }


def main() -> int:
    try:
        root = p243.repo_root()
        result = implementation_result(root)
    except (
        SourceContractError,
        spec.SpecError,
        p244_sources.SourceError,
        p243.AuditError,
        p241.CheckError,
        p233.CheckError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
