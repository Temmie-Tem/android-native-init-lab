#!/usr/bin/env python3
"""Versioned P2.88 pair-indexed attributable position source contract."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p248_source_contract as p248
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p286_source_contract as p286
import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_e1_decoder as decoder
import s22plus_fyg8_p288_runtime_transform as runtime_transform


CONTRACT_ID = "s22plus-fyg8-p288-pair-attributable-positions-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P288-PAIR-ATTRIBUTABLE-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p288_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p288_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P288_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p288_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P288_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P288_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = (
    "PASS_P288_PAIR_ATTRIBUTABLE_POSITION_IMPLEMENTATION_HOST_ONLY"
)
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P288-SOURCE-CHECK-V1"
).digest()[:16]

MODULE_PLAN_COUNT = p286.MODULE_PLAN_COUNT
GENERATED_KEYS = p286.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p286.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p288_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p288_e3_runtime.c",
    "plan_header": "s22plus_fyg8_p286_e3_plan.h",
    "p288_legacy_runtime": "s22plus_r4w1e_e1_runtime.c",
    "p288_e3_runtime_include": "s22plus_fyg8_p288_e3_runtime.inc.c",
    "p288_classifier_include": "s22plus_fyg8_p288_classifier.inc.c",
    "p288_position_header": "s22plus_fyg8_p288_positions.h",
    "p288_checkpoint_header": "s22plus_r4w1e_checkpoint.h",
    "p286_classifier_include": "s22plus_fyg8_p286_classifier.inc.c",
    "classifier_include": "s22plus_fyg8_p282_classifier.inc.c",
    "p260_e3_runtime_include": "s22plus_fyg8_p260_e3_runtime.inc.c",
    "trace_descriptor_header": "s22plus_fyg8_p286_trace_descriptor.h",
}

OVERLAY_SOURCE_PATHS = {
    "p288_contract_spec": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_contract_spec.py"
    ),
    "p288_source_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_source_contract.py"
    ),
    "p288_runtime_transform": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_runtime_transform.py"
    ),
    "p288_classifier_include": Path(
        "workspace/public/src/native-init/"
        "s22plus_fyg8_p288_classifier.inc.c"
    ),
    "p288_candidate_intent": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_candidate_intent.py"
    ),
    "p288_userspace_build": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_userspace_build.py"
    ),
    "p288_build": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_build.py"
    ),
    "p288_candidate_builder": Path(
        "workspace/public/src/scripts/revalidation/"
        "build_s22plus_fyg8_p288_candidate.py"
    ),
    "p288_boot_only_packager": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_boot_only_packager.py"
    ),
}
GENERATED_OVERLAY_KEYS = frozenset(
    {
        "p288_e3_runtime_include",
        "p288_legacy_runtime",
        "p288_position_header",
        "p288_checkpoint_header",
    }
)
SOURCE_KEYS = frozenset(
    (*p286.SOURCE_KEYS, *OVERLAY_SOURCE_PATHS, *GENERATED_OVERLAY_KEYS)
)
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
REACHABLE_VARIANTS = sum(
    (
        1
        + len(
            spec.position_failure_details(
                position.stage, position.item_index
            )
        )
        if position.kind == spec.KIND_TERMINAL
        else len(
            spec.position_progress_details(
                position.stage, position.item_index
            )
        )
        + len(
            spec.position_failure_details(
                position.stage, position.item_index
            )
        )
    )
    for position in spec.POSITIONS
)


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P288 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p286.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P288


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p286.candidate_observer(run_id)


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
    if data.count(start) != 1 or data.count(stop) != 1:
        raise SourceContractError(f"{label} markers are not exact")
    begin = data.index(start)
    end = data.index(stop, begin)
    return data[:begin] + replacement + data[end:]


def _render_checkpoint_steps() -> bytes:
    spec.validate_positions()
    gate_count = sum(
        step.kind == spec.KIND_GATE for step in spec.STEPS
    )
    kind_values = {
        spec.KIND_LOCAL: "S22_P248_STEP_NORMAL",
        spec.KIND_MODULE: "S22_P248_STEP_NORMAL",
        spec.KIND_GATE: "S22_P248_STEP_GATE",
        spec.KIND_TERMINAL: "S22_P248_STEP_TERMINAL",
    }
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
    lines.extend(
        f"    {{0x{step.stage:02x}U, {step.item_index}U, "
        f"{kind_values[step.kind]}}},"
        for step in spec.STEPS
    )
    lines.extend(
        (
            "};",
            "",
            "_Static_assert(",
            "    sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0])",
            "        == S22_P288_POSITION_COUNT,",
            '    "P2.88 position table is exact");',
            "_Static_assert(",
            "    S22_P288_POSITION_COUNT <= 255U,",
            '    "P2.88 generation fits one byte");',
            "_Static_assert(",
            f"    {gate_count}U <= 256U,",
            '    "P2.88 gate detail index fits one byte");',
        )
    )
    return "\n".join(lines).encode("ascii")


def _render_kernel_tables() -> bytes:
    spec.validate_positions()
    sequence = ", ".join(
        f"0x{step.stage:02x}" for step in spec.STEPS
    )
    items = ", ".join(str(step.item_index) for step in spec.STEPS)
    kinds = ", ".join(
        "1" if step.kind == spec.KIND_GATE else
        "2" if step.kind == spec.KIND_TERMINAL else
        "0"
        for step in spec.STEPS
    )
    return p248._kernel_prefixed(
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


def _render_position_header() -> bytes:
    lines = [
        "#ifndef S22PLUS_FYG8_P288_POSITIONS_H",
        "#define S22PLUS_FYG8_P288_POSITIONS_H",
        "",
        f"#define S22_P288_POSITION_COUNT {len(spec.POSITIONS)}U",
        f"#define P288_DETAIL_PERIPHERAL_HELPER_TIMEOUT "
        f"0x{spec.PERIPHERAL_HELPER_TIMEOUT_DETAIL:03x}U",
        "#define P288_DETAIL_PERIPHERAL_HELPER_TIMEOUT_OUTCOME 2U",
        "#define P288_DETAIL_PERIPHERAL_HELPER_TIMEOUT_STAGE_MASK 0x08U",
        f"#define P288_DETAIL_UNCLASSIFIED "
        f"0x{spec.UNCLASSIFIED_DETAIL:03x}U",
        "#define P288_DETAIL_UNCLASSIFIED_OUTCOME 2U",
        "#define P288_DETAIL_UNCLASSIFIED_STAGE_MASK 0x7fU",
        "",
    ]
    for ordinal, position in enumerate(spec.POSITIONS):
        if ordinal < spec.P286_PREFIX_GENERATIONS:
            continue
        macro = position.name.upper()
        lines.append(
            f"#define S22_P288_POSITION_{macro} {ordinal}U"
        )
    lines.extend(("", "#endif", ""))
    return "\n".join(lines).encode("ascii")


def _render_checkpoint_header(root: Path) -> bytes:
    base = p252.p233.read_direct(
        root / p252.p233.DEFAULT_HEADER,
        "P2.88 inherited checkpoint header",
    )
    value = _replace_exact(
        base,
        b"#include <stdint.h>\n",
        b'#include <stdint.h>\n\n#include "s22plus_fyg8_p288_positions.h"\n',
        label="P2.88 checkpoint position header",
    )
    value = _replace_exact(
        value,
        b"    uint8_t stage;\n"
        b"    uint8_t initialized;\n"
        b"    uint8_t terminal;\n",
        b"    uint8_t stage;\n"
        b"    uint8_t item_index;\n"
        b"    uint8_t generation;\n"
        b"    uint8_t initialized;\n"
        b"    uint8_t terminal;\n",
        label="P2.88 checkpoint client position state",
    )
    anchor = (
        b"long s22_r4w1e_checkpoint_success(\n"
        b"    struct s22_r4w1e_checkpoint_client *client);\n"
    )
    additions = anchor + (
        b"long s22_p288_checkpoint_next_stage(\n"
        b"    const struct s22_r4w1e_checkpoint_client *client);\n"
        b"long s22_p288_checkpoint_progress_position(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t position_ordinal,\n"
        b"    uint16_t detail);\n"
        b"long s22_p288_checkpoint_failure_next(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    long operation_error);\n"
        b"long s22_p288_checkpoint_unclassified_next(\n"
        b"    struct s22_r4w1e_checkpoint_client *client);\n"
    )
    return _replace_exact(
        value,
        anchor,
        additions,
        label="P2.88 checkpoint APIs",
    )


def _render_exact_rules(prefix: str, *, kernel: bool) -> list[str]:
    indent = "\t" if kernel else "    "
    suffix = "" if kernel else "U"
    lines: list[str] = []
    for ordinal, outcome, detail in spec.exact_detail_rules():
        lines.append(
            f"{indent}{{{ordinal}{suffix}, "
            f"{outcome}{suffix}, 0x{detail:03x}{suffix}}},"
        )
    if not lines:
        raise SourceContractError(f"{prefix} exact rule table is empty")
    return lines


def _checkpoint_detail_validator() -> bytes:
    lines = [
        "struct p288_detail_rule {",
        "    uint8_t ordinal;",
        "    uint8_t outcome;",
        "    uint16_t detail;",
        "};",
        "",
        "static const struct p288_detail_rule k_p288_detail_rules[] = {",
        *_render_exact_rules("checkpoint", kernel=False),
        "};",
        "",
        "static int p288_tuple_allowed(",
        "    size_t ordinal, uint8_t outcome, uint16_t detail) {",
        f"    if (ordinal != {spec.ordinal_for_position(spec.FINAL_STAGE, 1)}U ||",
        f"        detail < 0x{spec.TUPLE_FIRST:03x}U ||",
        f"        detail > 0x{spec.TUPLE_LAST:03x}U) {{",
        "        return 0;",
        "    }",
        f"    uint16_t offset = (uint16_t)(detail - 0x{spec.TUPLE_FIRST:03x}U);",
        f"    uint8_t speed = (uint8_t)(offset % {len(spec.USB_SPEEDS)}U);",
        "    uint8_t state = (uint8_t)(",
        f"        (offset / {len(spec.USB_SPEEDS)}U) % {len(spec.UDC_STATES)}U);",
        "    uint8_t expected =",
        f"        state == {spec.STATE_CONFIGURED}U &&",
        f"                speed == {spec.SPEED_HIGH}U",
        "            ? S22_P233_OUTCOME_PROGRESS",
        "            : S22_P233_OUTCOME_FAILURE;",
        "    return outcome == expected;",
        "}",
        "",
        "static int p288_detail_allowed(",
        "    size_t ordinal, uint8_t outcome, uint16_t detail) {",
        "    if (ordinal >= sizeof(k_p248_e2_steps) /",
        "            sizeof(k_p248_e2_steps[0])) {",
        "        return 0;",
        "    }",
        "    for (size_t index = 0;",
        "         index < sizeof(k_p288_detail_rules) /",
        "             sizeof(k_p288_detail_rules[0]);",
        "         ++index) {",
        "        const struct p288_detail_rule *rule =",
        "            &k_p288_detail_rules[index];",
        "        if (ordinal == rule->ordinal &&",
        "            outcome == rule->outcome && detail == rule->detail) {",
        "            return 1;",
        "        }",
        "    }",
        "    if (p288_tuple_allowed(ordinal, outcome, detail)) {",
        "        return 1;",
        "    }",
        "    const struct s22_p248_step *step = &k_p248_e2_steps[ordinal];",
        "    if (step->kind == S22_P248_STEP_TERMINAL) {",
        "        return outcome == S22_P233_OUTCOME_SUCCESS && detail == 0U;",
        "    }",
        "    if (outcome == S22_P233_OUTCOME_PROGRESS) {",
        "        return detail == 0U;",
        "    }",
        "    if (outcome != S22_P233_OUTCOME_FAILURE || detail == 0U) {",
        "        return 0;",
        "    }",
        "    if (detail <= S22_P248_DETAIL_ERRNO_MAX) {",
        "        return 1;",
        "    }",
        "    uint8_t encoded_index = (uint8_t)(detail & 0xffU);",
        f"    if (encoded_index >= {spec.GATE_COUNT}U) {{",
        "        return 0;",
        "    }",
        f"    if (ordinal >= {spec.LOCAL_DIAGNOSTIC_START_ORDINAL}U &&",
        f"        ordinal < {spec.TERMINAL_ORDINAL}U) {{",
        "        return (detail >= S22_P248_DETAIL_REGRESSION_BASE &&",
        "                detail <= S22_P248_DETAIL_REGRESSION_MAX) ||",
        "            (detail >= S22_P248_DETAIL_READ_ERROR_BASE &&",
        "             detail <= S22_P248_DETAIL_READ_ERROR_MAX);",
        "    }",
        "    if (step->kind == S22_P248_STEP_GATE &&",
        "        detail >= S22_P248_DETAIL_REGRESSION_BASE &&",
        "        detail <= S22_P248_DETAIL_REGRESSION_MAX) {",
        "        return encoded_index < step->item_index;",
        "    }",
        "    if (step->kind == S22_P248_STEP_GATE &&",
        "        detail >= S22_P248_DETAIL_READ_ERROR_BASE &&",
        "        detail <= S22_P248_DETAIL_READ_ERROR_MAX) {",
        "        return encoded_index <= step->item_index;",
        "    }",
        "    return 0;",
        "}",
        "",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _normalize_detail_c() -> bytes:
    return b"""static long p288_normalize_failure_detail(
    long operation_error, uint16_t *detail) {
    unsigned long value;
    if (detail == NULL) {
        return -EINVAL;
    }
    if (operation_error < 0) {
        if (operation_error < -(long)S22_P248_DETAIL_ERRNO_MAX) {
            return -EINVAL;
        }
        value = (unsigned long)(-operation_error);
    } else {
        value = (unsigned long)operation_error;
    }
    if (value == 0U) {
        value = EIO;
    }
    if (value > 0xffffU) {
        return -EINVAL;
    }
    *detail = (uint16_t)value;
    return 0;
}

"""


def _checkpoint_publish_tail() -> bytes:
    return _normalize_detail_c() + b"""static long p288_publish_next(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t outcome,
    uint16_t detail,
    int check_position,
    uint8_t position_ordinal) {
    struct s22_p233_checkpoint_request request = {0};
    if (client == NULL || !client->initialized || client->terminal) {
        return -EALREADY;
    }
    size_t count =
        sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
    size_t ordinal = client->generation;
    if (ordinal >= count ||
        (check_position && position_ordinal != ordinal) ||
        !p288_detail_allowed(ordinal, outcome, detail)) {
        return -EINVAL;
    }
    const struct s22_p248_step *step = &k_p248_e2_steps[ordinal];

    request.magic[0] = 'S';
    request.magic[1] = '2';
    request.magic[2] = '2';
    request.magic[3] = 'Q';
    request.version = S22_P233_REQUEST_VERSION;
    request.profile = S22PLUS_FYG8_P233_PROFILE;
    request.stage = step->stage;
    request.outcome = outcome;
    request.detail = detail;
    request.item_index = step->item_index;
    copy_bytes(request.run_id, client->run_id, sizeof(request.run_id));
    request.crc32 = checkpoint_crc32(
        &request, offsetof(struct s22_p233_checkpoint_request, crc32));

    long fd = sys_openat("/proc/s22_checkpoint", O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return fd;
    }
    long written = sys_write((int)fd, &request, sizeof(request));
    long closed = sys_close((int)fd);
    if (written != (long)sizeof(request)) {
        return written < 0 ? written : -EIO;
    }
    if (closed != 0) {
        return closed;
    }
    client->stage = step->stage;
    client->item_index = step->item_index;
    client->generation = (uint8_t)(ordinal + 1U);
    client->terminal = outcome != S22_P233_OUTCOME_PROGRESS;
    return 0;
}

int s22_r4w1e_checkpoint_client_init(
    struct s22_r4w1e_checkpoint_client *client,
    const uint8_t run_id[16]) {
    if (client == NULL || run_id == NULL || all_zero(run_id, 16U)) {
        return -EKEYREJECTED;
    }
    copy_bytes(client->run_id, run_id, sizeof(client->run_id));
    client->stage = 0U;
    client->item_index = 0U;
    client->generation = 0U;
    client->initialized = 1U;
    client->terminal = 0U;
    return 0;
}

long s22_r4w1e_checkpoint_progress(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index) {
    if (client == NULL || client->generation >= S22_P288_POSITION_COUNT) {
        return -EINVAL;
    }
    const struct s22_p248_step *step =
        &k_p248_e2_steps[client->generation];
    if (stage != step->stage || item_index != step->item_index) {
        return -EINVAL;
    }
    return p288_publish_next(
        client, S22_P233_OUTCOME_PROGRESS, 0U, 0, 0U);
}

long s22_r4w1e_checkpoint_progress_detail(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    uint16_t detail) {
    if (client == NULL || client->generation >= S22_P288_POSITION_COUNT) {
        return -EINVAL;
    }
    const struct s22_p248_step *step =
        &k_p248_e2_steps[client->generation];
    if (stage != step->stage || item_index != step->item_index) {
        return -EINVAL;
    }
    return p288_publish_next(
        client, S22_P233_OUTCOME_PROGRESS, detail, 0, 0U);
}

long s22_r4w1e_checkpoint_failure(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    long operation_error) {
    uint16_t detail = 0;
    long rc = p288_normalize_failure_detail(operation_error, &detail);
    if (rc != 0 || client == NULL ||
        client->generation >= S22_P288_POSITION_COUNT) {
        return rc != 0 ? rc : -EINVAL;
    }
    const struct s22_p248_step *step =
        &k_p248_e2_steps[client->generation];
    if (stage != step->stage || item_index != step->item_index) {
        return -EINVAL;
    }
    return p288_publish_next(
        client, S22_P233_OUTCOME_FAILURE, detail, 0, 0U);
}

long s22_r4w1e_checkpoint_success(
    struct s22_r4w1e_checkpoint_client *client) {
    return p288_publish_next(
        client, S22_P233_OUTCOME_SUCCESS, 0U, 1,
        S22_P288_POSITION_TERMINAL);
}

long s22_p288_checkpoint_next_stage(
    const struct s22_r4w1e_checkpoint_client *client) {
    if (client == NULL || !client->initialized || client->terminal ||
        client->generation >= S22_P288_POSITION_COUNT) {
        return -EALREADY;
    }
    return k_p248_e2_steps[client->generation].stage;
}

long s22_p288_checkpoint_progress_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail) {
    return p288_publish_next(
        client,
        S22_P233_OUTCOME_PROGRESS,
        detail,
        1,
        position_ordinal);
}

long s22_p288_checkpoint_failure_next(
    struct s22_r4w1e_checkpoint_client *client,
    long operation_error) {
    uint16_t detail = 0;
    long rc = p288_normalize_failure_detail(operation_error, &detail);
    return rc == 0
        ? p288_publish_next(
            client, S22_P233_OUTCOME_FAILURE, detail, 0, 0U)
        : rc;
}

long s22_p288_checkpoint_unclassified_next(
    struct s22_r4w1e_checkpoint_client *client) {
    return p288_publish_next(
        client,
        S22_P233_OUTCOME_FAILURE,
        P288_DETAIL_UNCLASSIFIED,
        0,
        0U);
}
"""


def _transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_checkpoint_steps(p286.spec.STEPS),
        _render_checkpoint_steps(),
        label="P2.88 checkpoint position table",
    )
    begin = value.index(b"static uint8_t terminal_stage(void) {\n")
    return (
        value[:begin]
        + _checkpoint_detail_validator()
        + _checkpoint_publish_tail()
    )


def _kernel_detail_validator() -> bytes:
    lines = [
        "struct s22_fyg8_p288_detail_rule {",
        "\tu8 ordinal;",
        "\tu8 outcome;",
        "\tu16 detail;",
        "};",
        "",
        "static const struct s22_fyg8_p288_detail_rule",
        "s22_fyg8_p288_detail_rules[] __used = {",
        *_render_exact_rules("kernel", kernel=True),
        "};",
        "",
        "static noinline __used bool s22_fyg8_p288_tuple_allowed(",
        "\tsize_t ordinal, u8 outcome, u16 detail)",
        "{",
        "\tu16 offset;",
        "\tu8 state;",
        "\tu8 speed;",
        "\tu8 expected;",
        "",
        f"\tif (ordinal != {spec.ordinal_for_position(spec.FINAL_STAGE, 1)} ||",
        f"\t\t\tdetail < 0x{spec.TUPLE_FIRST:03x} ||",
        f"\t\t\tdetail > 0x{spec.TUPLE_LAST:03x})",
        "\t\treturn false;",
        f"\toffset = detail - 0x{spec.TUPLE_FIRST:03x};",
        f"\tspeed = offset % {len(spec.USB_SPEEDS)};",
        f"\tstate = (offset / {len(spec.USB_SPEEDS)}) % {len(spec.UDC_STATES)};",
        f"\texpected = state == {spec.STATE_CONFIGURED} &&",
        f"\t\t\tspeed == {spec.SPEED_HIGH}",
        "\t\t? S22_FYG8_E1_PROGRESS : S22_FYG8_E1_FAILURE;",
        "\treturn outcome == expected;",
        "}",
        "",
        "static noinline __used bool s22_fyg8_e1_detail_allowed(",
        "\t\tu8 profile, size_t ordinal, size_t count,",
        "\t\tu8 outcome, u16 detail)",
        "{",
        "\tsize_t index;",
        "\tu8 encoded_index;",
        "\tu8 step_kind;",
        "\tu8 step_item;",
        "",
        "\tif (profile != S22_FYG8_E1_PROFILE_E2 || ordinal >= count)",
        "\t\treturn false;",
        "\tfor (index = 0; index < ARRAY_SIZE(s22_fyg8_p288_detail_rules);",
        "\t\t\t++index) {",
        "\t\tconst struct s22_fyg8_p288_detail_rule *rule =",
        "\t\t\t&s22_fyg8_p288_detail_rules[index];",
        "\t\tif (ordinal == READ_ONCE(rule->ordinal) &&",
        "\t\t\t\toutcome == READ_ONCE(rule->outcome) &&",
        "\t\t\t\tdetail == READ_ONCE(rule->detail))",
        "\t\t\treturn true;",
        "\t}",
        "\tif (s22_fyg8_p288_tuple_allowed(ordinal, outcome, detail))",
        "\t\treturn true;",
        "\tstep_kind = READ_ONCE(s22_fyg8_e2_kinds[ordinal]);",
        "\tstep_item = READ_ONCE(s22_fyg8_e2_items[ordinal]);",
        "\tif (ordinal + 1 == count)",
        "\t\treturn outcome == S22_FYG8_E1_SUCCESS && !detail;",
        "\tif (outcome == S22_FYG8_E1_PROGRESS)",
        "\t\treturn !detail;",
        "\tif (outcome != S22_FYG8_E1_FAILURE || !detail)",
        "\t\treturn false;",
        "\tif (detail <= 0x7ff)",
        "\t\treturn true;",
        "\tencoded_index = detail & 0xff;",
        f"\tif (encoded_index >= {spec.GATE_COUNT})",
        "\t\treturn false;",
        f"\tif (ordinal >= {spec.LOCAL_DIAGNOSTIC_START_ORDINAL} &&",
        f"\t\t\tordinal < {spec.TERMINAL_ORDINAL})",
        "\t\treturn (detail >= 0x800 && detail <= 0x8ff) ||",
        "\t\t\t(detail >= 0x900 && detail <= 0x9ff);",
        "\tif (step_kind == 1) {",
        "\t\tif (detail >= 0x800 && detail <= 0x8ff)",
        "\t\t\treturn encoded_index < step_item;",
        "\t\tif (detail >= 0x900 && detail <= 0x9ff)",
        "\t\t\treturn encoded_index <= step_item;",
        "\t}",
        "\treturn false;",
        "}",
        "",
    ]
    return p252._kernel_prefixed(lines)


def _transform_patch(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_kernel_tables(p286.spec.STEPS),
        _render_kernel_tables(),
        label="P2.88 kernel position tables",
    )
    value = _replace_exact(
        value,
        p286._kernel_detail_validator(),
        _kernel_detail_validator(),
        label="P2.88 kernel position detail validator",
    )
    value = _replace_span(
        value,
        b"+static const u8 s22_fyg8_e2_classifier_stages[] __used = {\n",
        b"+static bool s22_fyg8_e1_parse_reg(",
        b"",
        label="P2.88 retired stage-only classifier tables",
    )
    return p252._recount_kernel_patch_hunks(value)


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    historical = p286.generate(repository)
    return {
        "plan": historical["plan"],
        "runtime": runtime_transform.transform_runtime_wrapper(
            historical["runtime"]
        ),
        "checkpoint": _transform_checkpoint(historical["checkpoint"]),
        "patch": _transform_patch(historical["patch"]),
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = p286.source_bytes(root)
    result.update(
        {
            key: generated[GENERATED_OUTPUT_NAMES[key]]
            for key in GENERATED_KEYS
        }
    )
    for name, path in OVERLAY_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.88 source {name}"
        )
    result["p288_e3_runtime_include"] = (
        runtime_transform.transform_runtime_include(
            result["p286_e3_runtime_include"]
        )
    )
    result["p288_legacy_runtime"] = (
        runtime_transform.transform_legacy_runtime(
            result["p260_legacy_runtime"]
        )
    )
    result["p288_position_header"] = _render_position_header()
    result["p288_checkpoint_header"] = _render_checkpoint_header(root)
    if set(result) != SOURCE_KEYS:
        missing = sorted(SOURCE_KEYS - set(result))
        extra = sorted(set(result) - SOURCE_KEYS)
        raise SourceContractError(
            f"P2.88 source inventory changed: missing={missing}, extra={extra}"
        )
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _position_macro(name: str) -> bytes:
    return f"S22_P288_POSITION_{name.upper()}".encode("ascii")


def _runtime_position_calls(include: bytes) -> tuple[bytes, ...]:
    return tuple(
        re.findall(
            rb"p288_progress_position\(\s*"
            rb"(S22_P288_POSITION_[A-Z0-9_]+)\s*,",
            include,
        )
    )


def _audit_runtime_position_order(include: bytes) -> dict[str, Any]:
    expected = tuple(
        _position_macro(position.name)
        for position in spec.SUCCESSOR_POSITIONS[:-1]
    )
    actual = _runtime_position_calls(include)
    if actual != expected:
        raise SourceContractError(
            "P2.88 runtime publication order differs from the declared "
            "position sequence"
        )
    if (
        include.count(b"s22_r4w1e_checkpoint_success(&g_checkpoint)")
        != 1
        or include.index(b"p282_wait_final_pair(repair_class, bind_branch);")
        > include.index(b"s22_r4w1e_checkpoint_success(&g_checkpoint)")
    ):
        raise SourceContractError(
            "P2.88 terminal publication is not after final sampling"
        )
    return {
        "declared_nonterminal_suffix": len(expected),
        "runtime_nonterminal_suffix": len(actual),
        "exact_program_order": True,
        "terminal_publication_last": True,
        "verified": True,
    }


def _audit_runtime_position_mutations(include: bytes) -> dict[str, Any]:
    expected = tuple(
        _position_macro(position.name)
        for position in spec.SUCCESSOR_POSITIONS[:-1]
    )
    first, second = expected[:2]
    call = re.compile(
        rb"\s*p288_progress_position\(\s*"
        + re.escape(first)
        + rb"\s*,\s*0U\);\n"
    )
    removed, count = call.subn(b"\n", include, count=1)
    if count != 1:
        raise SourceContractError(
            "P2.88 mutation fixture cannot locate first publication"
        )
    swapped = include.replace(first, b"P288_SWAP", 1)
    swapped = swapped.replace(second, first, 1)
    swapped = swapped.replace(b"P288_SWAP", second, 1)
    duplicated = include.replace(first, first + b"\n" + first, 1)
    renamed = include.replace(first, first + b"_RENAMED", 1)
    mutations = {
        "remove": removed,
        "reorder": swapped,
        "duplicate": duplicated,
        "rename": renamed,
    }
    accepted: list[str] = []
    for name, mutated in mutations.items():
        try:
            _audit_runtime_position_order(mutated)
        except SourceContractError:
            continue
        accepted.append(name)
    if accepted:
        raise SourceContractError(
            f"P2.88 call-order gate accepted mutations: {accepted}"
        )
    return {
        "remove_rejected": True,
        "reorder_rejected": True,
        "duplicate_rejected": True,
        "rename_rejected": True,
        "verified": True,
    }


def _c_function_body(data: bytes, name: str) -> bytes:
    token = name.encode("ascii") + b"("
    offset = 0
    while True:
        start = data.find(token, offset)
        if start < 0:
            raise SourceContractError(
                f"P2.88 producer function is missing: {name}"
            )
        open_paren = start + len(name)
        depth = 0
        close_paren = -1
        for index in range(open_paren, len(data)):
            value = data[index]
            if value == ord("("):
                depth += 1
            elif value == ord(")"):
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
        if close_paren < 0:
            raise SourceContractError(
                f"P2.88 producer signature is truncated: {name}"
            )
        cursor = close_paren + 1
        while cursor < len(data) and chr(data[cursor]).isspace():
            cursor += 1
        if cursor < len(data) and data[cursor] == ord("{"):
            depth = 1
            end = cursor + 1
            while end < len(data) and depth:
                if data[end] == ord("{"):
                    depth += 1
                elif data[end] == ord("}"):
                    depth -= 1
                end += 1
            if depth:
                raise SourceContractError(
                    f"P2.88 producer body is truncated: {name}"
                )
            return data[start:end]
        offset = close_paren + 1


def _diagnostic_macro_map() -> dict[bytes, Any]:
    result = {
        detail.macro.encode("ascii"): detail
        for detail in spec.EXACT_DIAGNOSTIC_DETAILS
        if isinstance(getattr(detail, "macro", None), str)
    }
    result.update(
        {
            b"P288_DETAIL_PERIPHERAL_HELPER_TIMEOUT": (
                spec.DETAIL_BY_VALUE[
                    spec.PERIPHERAL_HELPER_TIMEOUT_DETAIL
                ]
            ),
            b"P282_DETAIL_TRACE_CLEANUP_UNVERIFIED": (
                spec.DETAIL_BY_VALUE[0xC04]
            ),
        }
    )
    return result


def _details_in_source(
    data: bytes,
    *,
    stage: int,
    item_index: int | None = None,
    outcome: int | None = None,
) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for macro, detail in _diagnostic_macro_map().items():
        if macro not in data:
            continue
        outcomes = tuple(getattr(detail, "outcomes", ()))
        for candidate_outcome in outcomes:
            if outcome is not None and candidate_outcome != outcome:
                continue
            if item_index is None:
                if stage not in getattr(detail, "stages", ()):
                    continue
            elif not spec.position_detail_allowed(
                stage,
                item_index,
                candidate_outcome,
                detail.value,
            ):
                continue
            result.add((candidate_outcome, detail.value))
    return result


def _audit_active_producer_routes(
    source: dict[str, bytes],
) -> dict[str, Any]:
    runtime = source["p288_e3_runtime_include"]
    classifier_sources = {
        "p288_classify_helper": source["p288_classifier_include"],
        "p286_classify_peripheral_readback": source[
            "p286_classifier_include"
        ],
        "p282_classify_restart": source["classifier_include"],
        "p282_classify_bind": source["classifier_include"],
        "p282_classify_final_pair": source["classifier_include"],
    }
    expanded = {
        name: _c_function_body(data, name)
        for name, data in classifier_sources.items()
    }
    helper_body = _c_function_body(
        runtime, "p286_run_cycle_role_helper"
    )
    helper_child_body = _c_function_body(
        runtime, "p282_cycle_role_child"
    )
    helper_record_body = _c_function_body(
        runtime, "p282_validate_cycle_helper_record"
    )
    control_body = _c_function_body(
        source["classifier_include"], "p282_classify_cycle_control"
    )

    marker_offsets = []
    for position in spec.SUCCESSOR_POSITIONS[:-1]:
        macro = _position_macro(position.name)
        matches = tuple(re.finditer(re.escape(macro), runtime))
        if len(matches) != 1:
            raise SourceContractError(
                "P2.88 producer route marker cardinality drifted: "
                + position.name
            )
        call_start = runtime.rfind(
            b"p288_progress_position(",
            0,
            matches[0].start(),
        )
        call_end = runtime.find(b");", matches[0].end())
        if call_start < 0 or call_end < 0:
            raise SourceContractError(
                "P2.88 producer route marker call is malformed: "
                + position.name
            )
        marker_offsets.append((call_start, call_end + 2))
    restart_start = runtime.index(
        b"static unsigned int p282_cycle_restart("
    )
    segments: list[bytes] = []
    start = restart_start
    for marker_start, marker_end in marker_offsets:
        if marker_start < start:
            raise SourceContractError(
                "P2.88 producer route markers are not ordered"
            )
        # Attribute work through the current publication call to that
        # position.  The call arguments themselves can contain the
        # load-bearing classifier/detail producer for the position.
        segments.append(runtime[start:marker_end])
        start = marker_end
    run_start = runtime.index(
        b"static __attribute__((noreturn)) void p288_e3_run("
    )
    final_call = runtime.index(
        b"p282_wait_final_pair(repair_class, bind_branch);",
        run_start,
    )
    terminal_publish = runtime.index(
        b"s22_r4w1e_checkpoint_success(&g_checkpoint)",
        final_call,
    )
    segments.append(runtime[final_call:terminal_publish])
    if len(segments) != len(spec.SUCCESSOR_POSITIONS):
        raise SourceContractError(
            "P2.88 producer segment count differs from the descriptor"
        )

    actual: set[tuple[int, int, int]] = set()
    proof_rows = []
    for position, segment in zip(
        spec.SUCCESSOR_POSITIONS, segments, strict=True
    ):
        generation = spec.generation_for_position(*position.pair)
        ordinal = generation - 1
        routes = _details_in_source(
            segment,
            stage=position.stage,
            item_index=position.item_index,
        )
        expanded_functions = []
        for name, body in expanded.items():
            if name.encode("ascii") + b"(" not in segment:
                continue
            if name == "p282_classify_bind":
                routes.update(
                    (
                        detail.outcomes[0],
                        detail.value,
                    )
                    for detail in spec.EXACT_DIAGNOSTIC_DETAILS
                    if 0xC40 <= detail.value <= 0xC4A
                )
            else:
                routes.update(
                    _details_in_source(
                        body,
                        stage=position.stage,
                        item_index=position.item_index,
                    )
                )
            expanded_functions.append(name)
        if b"p282_cycle_warning_detail(" in segment:
            routes.update(
                _details_in_source(
                    control_body,
                    stage=position.stage,
                    item_index=position.item_index,
                    outcome=spec.OUTCOME_PROGRESS,
                )
            )
            expanded_functions.append("p282_cycle_warning_detail")
        if (
            b"p286_run_cycle_role_helper(" in segment
            and b"P282_CONTROL_HELPER_SOURCE_CONTRADICTION"
            in helper_body + helper_child_body + helper_record_body
        ):
            helper = spec.DETAIL_BY_VALUE[0xC06]
            routes.add((helper.outcomes[0], helper.value))
            expanded_functions.append(
                "p286_run_cycle_role_helper-control-failure"
            )
        if b"P282_CONTROL_TRACE_SOURCE_CONTRADICTION" in segment:
            trace = spec.DETAIL_BY_VALUE[0xC05]
            routes.add((trace.outcomes[0], trace.value))
            expanded_functions.append(
                "trace-source-contradiction-control"
            )
        # Every publication/order/classifier failure routes through the
        # descriptor-derived reserved failure before the raw evidence park.
        routes.add((spec.OUTCOME_FAILURE, spec.UNCLASSIFIED_DETAIL))
        for outcome, detail in routes:
            actual.add((ordinal, outcome, detail))
        proof_rows.append(
            {
                "ordinal": ordinal,
                "position": position.name,
                "stage": position.stage,
                "item_index": position.item_index,
                "expanded_functions": sorted(set(expanded_functions)),
                "route_count": len(routes),
            }
        )

    declared = {
        rule
        for rule in spec.exact_detail_rules()
        if rule[0] >= spec.P286_PREFIX_GENERATIONS
    }
    missing = sorted(declared - actual)
    undeclared = sorted(actual - declared)
    if missing or undeclared:
        raise SourceContractError(
            "P2.88 active-producer/declaration route mismatch: "
            f"missing={missing}; undeclared={undeclared}"
        )
    if (
        b"P282_DETAIL_CYCLE_TRACE_SOURCE_CONTRADICTION"
        not in control_body
        or b"P282_DETAIL_CYCLE_HELPER_SOURCE_CONTRADICTION"
        not in control_body
    ):
        raise SourceContractError(
            "P2.88 control-failure producer mapping drifted"
        )
    return {
        "inherited_prefix_generations": spec.P286_PREFIX_GENERATIONS,
        "suffix_position_count": len(spec.SUCCESSOR_POSITIONS),
        "declared_route_count": len(declared),
        "active_route_count": len(actual),
        "missing_active_routes": [],
        "undeclared_active_routes": [],
        "proof_rows": proof_rows,
        "bidirectional_exact_tuple_coverage": True,
        "verified": True,
    }


def _audit_park_routes(source: dict[str, bytes]) -> dict[str, Any]:
    wrapper = source["runtime_wrapper"]
    legacy = source["p288_legacy_runtime"]
    include = source["p288_e3_runtime_include"]
    if (
        wrapper.count(runtime_transform.P288_WRAPPER_PARK) != 1
        or legacy.count(
            b"static void p288_raw_quiet_park(void) {"
        )
        != 1
        or b"p288_raw_quiet_park();" in legacy
        or b"p288_raw_quiet_park" in include
        or b"#define quiet_park" in wrapper
        or b"#define fail_at" in wrapper
    ):
        raise SourceContractError(
            "P2.88 raw park sink escaped its publication wrappers"
        )
    raw_sinks = wrapper.count(b"p288_raw_quiet_park();")
    if raw_sinks != 2:
        raise SourceContractError("P2.88 raw park sink count changed")
    direct_pattern = re.compile(rb"(?<!p288_raw_)quiet_park\(\);")
    routed = {
        "runtime_wrapper": len(direct_pattern.findall(wrapper)),
        "legacy_runtime": len(direct_pattern.findall(legacy)),
        "e3_runtime_include": len(direct_pattern.findall(include)),
    }
    if any(count <= 0 for count in routed.values()):
        raise SourceContractError("P2.88 park route inventory is incomplete")
    preinit_guard = (
        b"if (sys_getpid() != 1) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"    if (s22_r4w1e_checkpoint_client_init("
        b"&g_checkpoint, k_run_id) != 0) {\n"
        b"        quiet_park();\n"
        b"    }"
    )
    if wrapper.count(preinit_guard) != 1 or legacy.count(preinit_guard) != 1:
        raise SourceContractError(
            "P2.88 pre-initialization unreachable park guards drifted"
        )
    return {
        "routed_quiet_park_calls": routed,
        "raw_sink_calls": raw_sinks,
        "raw_sinks_publication_dominated": True,
        "unclassified_before_generic_park": True,
        "exact_or_unclassified_before_failure_park": True,
        "preinit_non_pid1_guard_unreachable_for_init": True,
        "preinit_nonzero_run_id_client_init_guard_unreachable": True,
        "verified": True,
    }


def _audit_publication_bound() -> dict[str, Any]:
    if (
        len(spec.POSITIONS) != 103
        or spec.TERMINAL_GENERATION != 103
        or spec.TERMINAL_ORDINAL != 102
        or spec.POSITIONS[-1].pair != spec.TERMINAL_POSITION
        or len(spec.POSITIONS) > 0xFF
    ):
        raise SourceContractError(
            "P2.88 publication upper bound is not exact generation 103"
        )
    return {
        "position_count": 103,
        "terminal_generation": 103,
        "generation_limit_is_sequence_length": True,
        "generation_u8_wrap_unreachable": True,
        "post_terminal_publication_rejected": True,
        "verified": True,
    }


def _audit_packager_integration(
    source: dict[str, bytes],
) -> dict[str, Any]:
    builder = source["p288_candidate_builder"]
    packager = source["p288_boot_only_packager"]
    intent = source["p288_candidate_intent"]
    userspace = source["p288_userspace_build"]
    build = source["p288_build"]
    checks = (
        (
            builder,
            b"base.packager = packager",
            1,
            "candidate builder package binding",
        ),
        (
            builder,
            b"return base.build_candidate(args)",
            1,
            "candidate builder dispatch",
        ),
        (
            packager,
            b"return base.package(",
            1,
            "boot-only packager dispatch",
        ),
        (
            intent,
            b"return base.create(args)",
            1,
            "candidate intent dispatch",
        ),
        (
            userspace,
            b"return base.build_userspace(args)",
            1,
            "userspace build dispatch",
        ),
        (
            build,
            b"return base.main()",
            1,
            "kernel build dispatch",
        ),
    )
    for data, token, count, label in checks:
        if data.count(token) != count:
            raise SourceContractError(
                f"P2.88 {label} cardinality drifted"
            )
    return {
        "candidate_builder_dispatch_verified": True,
        "boot_only_packager_dispatch_verified": True,
        "intent_dispatch_verified": True,
        "userspace_dispatch_verified": True,
        "kernel_build_dispatch_verified": True,
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
    return p252._audit_userspace(
        root,
        generated,
        directory,
        materialized_filenames=MATERIALIZED_FILENAMES,
        source_check_run_id=SOURCE_CHECK_RUN_ID,
    )


def _audit_patch(
    root: Path, patch: bytes, directory: Path
) -> dict[str, Any]:
    patch_path = directory / "p288.patch"
    patch_path.write_bytes(patch)
    p252.p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=root / p252.p241.DEFAULT_SOURCE,
        label="P2.88 clean-apply check",
    )
    text = patch.decode("ascii")
    required = (
        "request->stage != sequence[ordinal]",
        "request->item_index != expected_item",
        "s22_fyg8_e2_items[ordinal]",
        "s22_fyg8_p288_detail_rules[] __used",
        "ordinal == READ_ONCE(rule->ordinal)",
        "detail >= 0x800 && detail <= 0x8ff",
        "detail >= 0x900 && detail <= 0x9ff",
        "encoded_index = detail & 0xff;",
    )
    if any(token not in text for token in required):
        raise SourceContractError(
            "P2.88 pair-indexed kernel validator source is incomplete"
        )
    return {
        **receipt(patch),
        "clean_apply": True,
        "pair_indexed_request_validation": True,
        "verified": True,
    }


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.88 generation is not deterministic")
    source = source_bytes(root)
    runtime_order = _audit_runtime_position_order(
        source["p288_e3_runtime_include"]
    )
    mutation_gate = _audit_runtime_position_mutations(
        source["p288_e3_runtime_include"]
    )
    active_producer_routes = _audit_active_producer_routes(source)
    park_routes = _audit_park_routes(source)
    publication_bound = _audit_publication_bound()
    packager_integration = _audit_packager_integration(source)
    with tempfile.TemporaryDirectory(prefix="s22-p288-") as temporary:
        directory = Path(temporary)
        try:
            patch = _audit_patch(root, first["patch"], directory)
            userspace = _audit_userspace(root, first, source, directory)
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p288_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "patch": patch,
        "linked_userspace": userspace,
        "runtime_position_order": runtime_order,
        "runtime_position_mutations": mutation_gate,
        "active_producer_routes": active_producer_routes,
        "park_routes": park_routes,
        "publication_bound": publication_bound,
        "packager_integration": packager_integration,
        "descriptor": {
            "position_count": len(spec.POSITIONS),
            "terminal_generation": spec.TERMINAL_GENERATION,
            "terminal_stage": spec.TERMINAL_STAGE,
            "terminal_item_index": spec.TERMINAL_POSITION[1],
            "exact_detail_count": len(spec.EXACT_DIAGNOSTIC_DETAILS),
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
        raise SourceContractError("P2.88 reachable run ID is invalid")
    model = decoder.model
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
    checked = 0
    for generation, position in enumerate(spec.POSITIONS, 1):
        outcomes: list[tuple[int, int]] = []
        if position.kind == spec.KIND_TERMINAL:
            outcomes.append((model.OUTCOME_SUCCESS, 0))
        else:
            outcomes.extend(
                (model.OUTCOME_PROGRESS, detail)
                for detail in spec.position_progress_details(
                    position.stage, position.item_index
                )
            )
        outcomes.extend(
            (model.OUTCOME_FAILURE, detail)
            for detail in spec.position_failure_details(
                position.stage, position.item_index
            )
        )
        for outcome, detail in outcomes:
            slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
            if generation == 1:
                slots[0] = decoder.encode_slot(
                    header,
                    generation=0,
                    stage=model.STAGES["ENTRY"],
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=0,
                    detail=0,
                )
            else:
                previous = spec.position_for_generation(generation - 1)
                slots[(generation - 1) & 1] = decoder.encode_slot(
                    header,
                    generation=generation - 1,
                    stage=previous.stage,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=previous.item_index,
                    detail=0,
                )
            slots[generation & 1] = decoder.encode_slot(
                header,
                generation=generation,
                stage=position.stage,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            )
            decoded = decoder.decode_record(
                header + b"".join(slots),
                expected_profile=PROFILE,
                expected_run_id=run_id,
            )
            if decoded["active"] != {
                "slot_id": generation & 1,
                "generation": generation,
                "stage": position.stage,
                "outcome": outcome,
                "item_index": position.item_index,
                "detail": detail,
            }:
                raise SourceContractError(
                    "P2.88 decoder changed a reachable active slot"
                )
            checked += 1
    if checked != REACHABLE_VARIANTS:
        raise SourceContractError("P2.88 reachable variant count drifted")
    return {
        "reachable_slot_variants": checked,
        "profiles": [PROFILE],
        "checked_run_ids": {PROFILE: run_id.hex()},
        "adjacent_slot_combinations_verified": True,
        "zero_crc_count": 0,
        "family_collision_count": 0,
        "decoder_policy_id": decoder.POLICY_ID,
        "position_count": len(spec.POSITIONS),
        "terminal_generation": spec.TERMINAL_GENERATION,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    base = p252.linked_table_bytes_for(spec)
    base.pop("s22_fyg8_e2_classifier_stages")
    base.pop("s22_fyg8_e2_classifier_details")
    rules = bytearray()
    for ordinal, outcome, detail in spec.exact_detail_rules():
        rules.append(ordinal)
        rules.append(outcome)
        rules.extend(detail.to_bytes(2, "little"))
    return {
        **base,
        "s22_fyg8_p288_detail_rules": bytes(rules),
    }


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.88 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "position_pairs_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = (
    *tuple(
        symbol
        for symbol in p286.LINKED_VALIDATOR_SYMBOLS
        if symbol not in {
            "s22_fyg8_p282_inherited_role_details",
            "s22_fyg8_p282_details",
        }
    ),
    "s22_fyg8_p288_detail_rules",
    "s22_fyg8_p288_tuple_allowed",
)


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        runtime_transform.RuntimeTransformError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
