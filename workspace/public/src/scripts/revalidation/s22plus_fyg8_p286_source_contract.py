#!/usr/bin/env python3
"""Versioned P2.86 parent-quiescence and bounded-restart source contract."""

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
import s22plus_fyg8_p260_source_contract as p260
import s22plus_fyg8_p280_contract_spec as p280_spec
import s22plus_fyg8_p282_source_contract as p282
import s22plus_fyg8_p284_source_contract as p284
import s22plus_fyg8_p286_contract_spec as spec
import s22plus_fyg8_p286_e1_decoder as decoder
import s22plus_fyg8_p286_trace_contract as trace_contract


CONTRACT_ID = "s22plus-fyg8-p286-parent-tail-bounded-restart-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P286-PARENT-TAIL-BOUNDED-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p286_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p286_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P286_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p286_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P286_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P286_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = (
    "PASS_P286_PARENT_TAIL_BOUNDED_RESTART_IMPLEMENTATION_HOST_ONLY"
)
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P286-SOURCE-CHECK-V1"
).digest()[:16]

DEFAULT_DWC3_MSM_MODULE = p282.DEFAULT_DWC3_MSM_MODULE
DEFAULT_HSPHY_MODULE = p282.DEFAULT_HSPHY_MODULE

MODULE_PLAN_COUNT = p260.MODULE_PLAN_COUNT
GENERATED_KEYS = p260.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p260.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p286_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p286_e3_runtime.c",
    "plan_header": "s22plus_fyg8_p286_e3_plan.h",
    "p286_e3_runtime_include": "s22plus_fyg8_p286_e3_runtime.inc.c",
    "p286_classifier_include": "s22plus_fyg8_p286_classifier.inc.c",
    "classifier_include": "s22plus_fyg8_p282_classifier.inc.c",
    "p260_e3_runtime_include": "s22plus_fyg8_p260_e3_runtime.inc.c",
    "trace_descriptor_header": "s22plus_fyg8_p286_trace_descriptor.h",
}

OVERLAY_SOURCE_PATHS = {
    "p286_contract_spec": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_contract_spec.py"
    ),
    "p286_source_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_source_contract.py"
    ),
    "p286_candidate_intent": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_candidate_intent.py"
    ),
    "p286_build": Path(
        "workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_build.py"
    ),
    "p286_candidate_builder": Path(
        "workspace/public/src/scripts/revalidation/"
        "build_s22plus_fyg8_p286_candidate.py"
    ),
    "p286_userspace_build": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_userspace_build.py"
    ),
    "p286_boot_only_packager": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_boot_only_packager.py"
    ),
    "p286_trace_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_trace_contract.py"
    ),
    "p286_e3_runtime_include": Path(
        "workspace/public/src/native-init/"
        "s22plus_fyg8_p286_e3_runtime.inc.c"
    ),
    "p286_classifier_include": Path(
        "workspace/public/src/native-init/"
        "s22plus_fyg8_p286_classifier.inc.c"
    ),
}
COMMON_SOURCE_PATHS = dict(p282.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS.update(p284.OVERLAY_SOURCE_PATHS)
COMMON_SOURCE_PATHS.update(OVERLAY_SOURCE_PATHS)
SOURCE_KEYS = frozenset((*p284.SOURCE_KEYS, *OVERLAY_SOURCE_PATHS))
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
BASE_REACHABLE_VARIANTS = 1 + sum(
    1 + len(spec.failure_details(step))
    for step in spec.STEPS
    if step.kind != spec.KIND_TERMINAL
)
PROGRESS_DETAIL_VARIANTS = sum(
    len(detail.stages)
    for detail in spec.DIAGNOSTIC_DETAILS
    if spec.OUTCOME_PROGRESS in detail.outcomes
)
PROGRESS_TUPLE_VARIANTS = 3 * 3
REACHABLE_VARIANTS = (
    BASE_REACHABLE_VARIANTS
    + PROGRESS_DETAIL_VARIANTS
    + PROGRESS_TUPLE_VARIANTS
)
INHERITED_ROLE_DETAILS = tuple(
    detail
    for detail in p280_spec.DIAGNOSTIC_DETAILS
    if p280_spec.ROLE_UDC_STAGE in detail.stages
)


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P286 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p260.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P286


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p260.candidate_observer(run_id)


def _validate_runtime_authority_source(include: bytes) -> None:
    for name, expected_value in spec.RUNTIME_EXTERNAL_CONSTANTS:
        pattern = re.compile(
            rb"^#define[ \t]+"
            + re.escape(name.encode("ascii"))
            + rb"[ \t]+(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)"
            + rb"[lLuU]*[ \t]*$",
            re.MULTILINE,
        )
        matches = pattern.findall(include)
        if len(matches) != 1:
            raise SourceContractError(
                f"P2.86 runtime constant {name} cardinality drifted"
            )
        literal = matches[0].decode("ascii")
        if literal.lower().startswith("0x"):
            actual_value = int(literal, 16)
        elif len(literal) > 1 and literal.startswith("0"):
            actual_value = int(literal, 8)
        else:
            actual_value = int(literal, 10)
        if actual_value != expected_value:
            raise SourceContractError(
                f"P2.86 runtime constant {name} value drifted"
            )

    for forbidden in (
        b'"/sys/kernel/debug/tracing',
        b'"/sys/kernel/tracing/current_tracer"',
        b'"/sys/kernel/tracing/set_ftrace_filter"',
        b'"function_graph"',
        b'"function"',
    ):
        if forbidden in include:
            raise SourceContractError(
                "P2.86 runtime broadened beyond exact Kprobe authority"
            )

    tracefs_paths = {
        value.decode("ascii")
        for value in re.findall(
            rb'"(/sys/kernel/tracing[^"\\]*)"',
            include,
        )
    }
    if tracefs_paths != set(spec.TRACEFS_ABSOLUTE_PATHS):
        raise SourceContractError("P2.86 tracefs absolute path set drifted")

    for name, token, expected_count in spec.RUNTIME_OPERATION_TOKENS:
        count = include.count(token.encode("ascii"))
        if count != expected_count:
            raise SourceContractError(
                f"P2.86 runtime operation {name} cardinality drifted"
            )
    timeout = include.index(b"observation->timed_out = !malformed;")
    kill = include.index(b"(void)sys_kill(pid, SIGKILL);", timeout)
    reap = include.index(
        b"sys_wait4(\n                            "
        b"pid, &child_status, WNOHANG)",
        kill,
    )
    if not timeout < kill < reap:
        raise SourceContractError(
            "P2.86 timeout classification does not precede bounded reap"
        )
    abort = include.index(
        b"static __attribute__((noreturn)) void p282_cycle_abort("
    )
    abort_end = include.index(
        b"static __attribute__((noreturn)) void "
        b"p282_cycle_abort_condition(",
        abort,
    )
    abort_body = include[abort:abort_end]
    publish = abort_body.find(
        b"long publish_rc = s22_r4w1e_checkpoint_failure("
    )
    publish_failure_park = abort_body.find(
        b"if (publish_rc != 0) {\n        quiet_park();\n    }",
    )
    cleanup = abort_body.find(
        b"(void)p282_trace_finish(&cycle->trace, &quality);",
    )
    terminal_park = abort_body.rfind(b"quiet_park();")
    if not publish < publish_failure_park < cleanup < terminal_park:
        raise SourceContractError(
            "P2.86 terminal checkpoint does not precede trace cleanup"
        )
    for forbidden in (
        b"P282_CONTROL_TRACE_CLEANUP_UNVERIFIED",
        b"p282_fail_classification(",
        b"fail_at(stage, 0U, detail);",
    ):
        if forbidden in abort_body:
            raise SourceContractError(
                "P2.86 trace cleanup can override terminal evidence"
            )
    restart = include.index(b"static unsigned int p282_cycle_restart(")
    pre_dispatch_refresh = include.index(
        b"p282_cycle_refresh(cycle, P282_STAGE_RESTART);",
        restart,
    )
    residual_snapshot = include.index(
        b"residual_outer_open = cycle->observed.outer_open;",
        pre_dispatch_refresh,
    )
    peripheral_dispatch = include.index(
        b"p286_run_cycle_role_helper(\n"
        b"        P282_HELPER_OPERATION_PERIPHERAL_WRITE,",
        residual_snapshot,
    )
    if not pre_dispatch_refresh < residual_snapshot < peripheral_dispatch:
        raise SourceContractError(
            "P2.86 residual outer state is not frozen before dispatch"
        )


def _validate_classifier_source(include: bytes) -> None:
    expected = {
        "PARENT_STATUS_NOT_SUSPENDED": 1,
        "PARENT_STATUS_READ_ERROR": 1,
        "HELPER_DISPATCH_FAILED": 1,
        "HELPER_UNREAPED": 1,
        "HELPER_COMPLETION_MALFORMED": 2,
        "NONE_WRITE_TIMEOUT": 1,
        "NONE_WRITE_RETURNED_ERROR": 1,
        "PERIPHERAL_FLUSH_TIMEOUT": 1,
        "RESIDUAL_OUTER_TAIL_TIMEOUT": 1,
        "START_PERIPHERAL_NO_RETURN": 1,
        "PERIPHERAL_WRITE_RETURNED_ERROR": 1,
        "PERIPHERAL_WRITE_COMPLETED_READBACK_FAILED": 1,
    }
    for suffix, count in expected.items():
        token = f"P282_DETAIL_{suffix}".encode("ascii")
        if include.count(token) != count:
            raise SourceContractError(
                f"P2.86 classifier detail {suffix} cardinality drifted"
            )
    for token, count in (
        (b'#include "s22plus_fyg8_p282_classifier.inc.c"', 1),
        (b"static int p286_classify_parent_status(", 1),
        (b"static int p286_classify_helper(", 1),
        (b"static int p286_classify_peripheral_readback(", 1),
        (b"fixture", 0),
        (b"test_mode", 0),
    ):
        if include.count(token) != count:
            raise SourceContractError(
                f"P2.86 classifier token {token!r} cardinality drifted"
            )


def _validate_packager_integration(source: dict[str, bytes]) -> None:
    builder = source["p286_candidate_builder"]
    packager = source["p286_boot_only_packager"]
    for data, token, count, label in (
        (builder, b"packager.package(", 1, "builder dispatch"),
        (
            builder,
            b"write_deterministic_boot_ap(",
            0,
            "builder direct AP creation",
        ),
        (
            packager,
            b"write_deterministic_boot_ap(",
            1,
            "packager AP creation",
        ),
        (packager, b'["boot.img.lz4"]', 1, "packager exact member"),
        (packager, b"device_write", 1, "packager safety declaration"),
        (packager, b"odin_invoked", 1, "packager Odin declaration"),
    ):
        if data.count(token) != count:
            raise SourceContractError(
                f"P2.86 {label} cardinality drifted"
            )


def _validate_trace_descriptor_source(header: bytes) -> None:
    for name, value in spec.RUNTIME_STRING_CONSTANTS:
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        token = f'#define {name} "{escaped}"'.encode("ascii")
        if header.count(token) != 1:
            raise SourceContractError(
                f"P2.86 generated runtime string {name} drifted"
            )
    if b'"host\\n"' in header:
        raise SourceContractError("P2.86 generated a forbidden host role")
    for token in (
        b"#define P282_CLASSIFIER_CONTRACT_DEFINED 1",
        b"#define P282_ROLE_EVENT_COUNT 4U",
        b"#define P282_CYCLE_EVENT_COUNT 16U",
        b"#define P282_BIND_EVENT_COUNT 6U",
        b"#define P282_ROLE_DEADLINE_SEC 30LL",
        b"p282_descriptor_udc_states[]",
        b"p282_descriptor_usb_speeds[]",
    ):
        if header.count(token) != 1:
            raise SourceContractError(
                "P2.86 generated trace/classifier contract drifted"
            )


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


def _checkpoint_exact_detail_table() -> bytes:
    lines = [
        "struct p282_checkpoint_detail_rule {",
        "    uint16_t value;",
        "    uint8_t outcome;",
        "    uint8_t stage_mask;",
        "};",
        "",
        "static const struct p282_checkpoint_detail_rule",
        "k_p282_inherited_role_details[] = {",
    ]
    for detail in INHERITED_ROLE_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError(
                "P2.82 inherited role detail outcome is not singular"
            )
        lines.append(
            "    {"
            f"0x{detail.value:03x}U, {detail.outcomes[0]}U, 0x01U"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static const struct p282_checkpoint_detail_rule",
        "k_p282_checkpoint_details[] = {",
        )
    )
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError("P2.82 detail outcome is not singular")
        lines.append(
            "    {"
            f"0x{detail.value:03x}U, {detail.outcomes[0]}U, "
            f"0x{spec.stage_mask(detail.stages):02x}U"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static int p282_exact_detail_allowed(",
            "    uint8_t stage, uint8_t outcome, uint16_t detail) {",
            "    if (stage == P282_DETAIL_STAGE_BASE) {",
            "        for (size_t index = 0;",
            "             index < sizeof(k_p282_inherited_role_details) /",
            "                 sizeof(k_p282_inherited_role_details[0]);",
            "             ++index) {",
            "            const struct p282_checkpoint_detail_rule *rule =",
            "                &k_p282_inherited_role_details[index];",
            "            if (detail == rule->value &&",
            "                outcome == rule->outcome) {",
            "                return 1;",
            "            }",
            "        }",
            "    }",
            "    for (size_t index = 0;",
            "         index < sizeof(k_p282_checkpoint_details) /",
            "             sizeof(k_p282_checkpoint_details[0]);",
            "         ++index) {",
            "        const struct p282_checkpoint_detail_rule *rule =",
            "            &k_p282_checkpoint_details[index];",
            "        uint8_t offset =",
            "            (uint8_t)(stage - P282_DETAIL_STAGE_BASE);",
            "        if (stage >= P282_DETAIL_STAGE_BASE && offset < 8U &&",
            "            detail == rule->value && outcome == rule->outcome &&",
            "            (rule->stage_mask & (uint8_t)(1U << offset)) != 0U) {",
            "            return 1;",
            "        }",
            "    }",
            "    return 0;",
            "}",
            "",
            "static int p282_tuple_detail_allowed(",
            "    uint8_t stage, uint8_t outcome, uint16_t detail) {",
            "    if (stage != P282_FINAL_STAGE ||",
            "        detail < P282_TUPLE_FIRST || detail > P282_TUPLE_LAST) {",
            "        return 0;",
            "    }",
            "    uint16_t offset = (uint16_t)(detail - P282_TUPLE_FIRST);",
            "    uint8_t speed = (uint8_t)(offset % P282_SPEED_COUNT);",
            "    uint8_t state =",
            "        (uint8_t)((offset / P282_SPEED_COUNT) % P282_STATE_COUNT);",
            "    uint8_t expected =",
            "        state == P282_STATE_CONFIGURED &&",
            "                speed == P282_SPEED_HIGH",
            "            ? S22_P233_OUTCOME_PROGRESS",
            "            : S22_P233_OUTCOME_FAILURE;",
            "    return outcome == expected;",
            "}",
            "",
        )
    )
    prefixes = [
        f"#define P282_DETAIL_STAGE_BASE 0x{spec.ROLE_UDC_STAGE:02x}U",
        f"#define P282_FINAL_STAGE 0x{spec.FINAL_STAGE:02x}U",
        f"#define P282_TUPLE_FIRST 0x{spec.TUPLE_FIRST:03x}U",
        f"#define P282_TUPLE_LAST 0x{spec.TUPLE_LAST:03x}U",
        f"#define P282_STATE_COUNT {len(spec.UDC_STATES)}U",
        f"#define P282_SPEED_COUNT {len(spec.USB_SPEEDS)}U",
        f"#define P282_STATE_CONFIGURED {spec.STATE_CONFIGURED}U",
        f"#define P282_SPEED_HIGH {spec.SPEED_HIGH}U",
        "",
    ]
    return ("\n".join((*prefixes, *lines)) + "\n").encode("ascii")


def _checkpoint_detail_helper() -> bytes:
    base = p260._checkpoint_detail_helper()
    base = _replace_exact(
        base,
        b"stage >= 0x88U && stage <= 0x8fU",
        b"stage >= 0x88U && stage <= 0x92U",
        label="P2.82 checkpoint local-stage regression span",
    )
    anchor = (
        b"static int p252_detail_allowed(\n"
        b"    uint8_t stage, uint8_t outcome, uint16_t detail) {\n"
    )
    value = _replace_exact(
        base,
        anchor,
        _checkpoint_exact_detail_table() + anchor,
        label="P2.82 checkpoint exact detail table",
    )
    insertion = (
        b"    if (step == NULL) {\n"
        b"        return 0;\n"
        b"    }\n"
    )
    replacement = insertion + (
        b"    if (p282_exact_detail_allowed(stage, outcome, detail)) {\n"
        b"        return 1;\n"
        b"    }\n"
        b"    if (p282_tuple_detail_allowed(stage, outcome, detail)) {\n"
        b"        return 1;\n"
        b"    }\n"
        b"    if (detail >= 0xc00U) {\n"
        b"        return 0;\n"
        b"    }\n"
    )
    return _replace_exact(
        value,
        insertion,
        replacement,
        label="P2.82 checkpoint exact detail dispatch",
    )


def _kernel_detail_validator() -> bytes:
    lines = [
        f"#define S22_FYG8_P282_DETAIL_STAGE_BASE 0x{spec.ROLE_UDC_STAGE:02x}",
        f"#define S22_FYG8_P282_FINAL_STAGE 0x{spec.FINAL_STAGE:02x}",
        f"#define S22_FYG8_P282_TUPLE_FIRST 0x{spec.TUPLE_FIRST:03x}",
        f"#define S22_FYG8_P282_TUPLE_LAST 0x{spec.TUPLE_LAST:03x}",
        f"#define S22_FYG8_P282_STATE_COUNT {len(spec.UDC_STATES)}",
        f"#define S22_FYG8_P282_SPEED_COUNT {len(spec.USB_SPEEDS)}",
        f"#define S22_FYG8_P282_STATE_CONFIGURED {spec.STATE_CONFIGURED}",
        f"#define S22_FYG8_P282_SPEED_HIGH {spec.SPEED_HIGH}",
        "",
        "struct s22_fyg8_p282_detail_rule {",
        "\tu16 value;",
        "\tu8 outcome;",
        "\tu8 stage_mask;",
        "};",
        "",
        "static const struct s22_fyg8_p282_detail_rule",
        "s22_fyg8_p282_inherited_role_details[] __used = {",
    ]
    for detail in INHERITED_ROLE_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError(
                "P2.82 inherited kernel role detail outcome drifted"
            )
        lines.append(
            "\t{"
            f"0x{detail.value:03x}, {detail.outcomes[0]}, 0x01"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static const struct s22_fyg8_p282_detail_rule",
        "s22_fyg8_p282_details[] __used = {",
        )
    )
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError("P2.82 kernel detail outcome drifted")
        lines.append(
            "\t{"
            f"0x{detail.value:03x}, {detail.outcomes[0]}, "
            f"0x{spec.stage_mask(detail.stages):02x}"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static noinline __used bool s22_fyg8_p282_detail_allowed(",
            "\t\tu8 stage, u8 outcome, u16 detail)",
            "{",
            "\tsize_t index;",
            "\tu8 offset;",
            "",
            "\tif (stage < S22_FYG8_P282_DETAIL_STAGE_BASE)",
            "\t\treturn false;",
            "\toffset = stage - S22_FYG8_P282_DETAIL_STAGE_BASE;",
            "\tif (offset >= 8)",
            "\t\treturn false;",
            "\tif (!offset) {",
            "\t\tfor (index = 0;",
            "\t\t\t\tindex < ARRAY_SIZE(",
            "\t\t\t\t\ts22_fyg8_p282_inherited_role_details);",
            "\t\t\t\t++index) {",
            "\t\t\tconst struct s22_fyg8_p282_detail_rule *rule =",
            "\t\t\t\t&s22_fyg8_p282_inherited_role_details[index];",
            "\t\t\tif (detail == READ_ONCE(rule->value) &&",
            "\t\t\t\t\toutcome == READ_ONCE(rule->outcome))",
            "\t\t\t\treturn true;",
            "\t\t}",
            "\t}",
            "\tfor (index = 0; index < ARRAY_SIZE(s22_fyg8_p282_details);",
            "\t\t\t++index) {",
            "\t\tconst struct s22_fyg8_p282_detail_rule *rule =",
            "\t\t\t&s22_fyg8_p282_details[index];",
            "\t\tif (detail == READ_ONCE(rule->value) &&",
            "\t\t\toutcome == READ_ONCE(rule->outcome) &&",
            "\t\t\t(READ_ONCE(rule->stage_mask) & (1U << offset)))",
            "\t\t\treturn true;",
            "\t}",
            "\treturn false;",
            "}",
            "",
            "static noinline __used bool s22_fyg8_p282_tuple_allowed(",
            "\t\tu8 stage, u8 outcome, u16 detail)",
            "{",
            "\tu16 offset;",
            "\tu8 state;",
            "\tu8 speed;",
            "\tu8 expected;",
            "",
            "\tif (stage != S22_FYG8_P282_FINAL_STAGE ||",
            "\t\t\tdetail < S22_FYG8_P282_TUPLE_FIRST ||",
            "\t\t\tdetail > S22_FYG8_P282_TUPLE_LAST)",
            "\t\treturn false;",
            "\toffset = detail - S22_FYG8_P282_TUPLE_FIRST;",
            "\tspeed = offset % S22_FYG8_P282_SPEED_COUNT;",
            "\tstate = (offset / S22_FYG8_P282_SPEED_COUNT) %",
            "\t\tS22_FYG8_P282_STATE_COUNT;",
            "\texpected = state == S22_FYG8_P282_STATE_CONFIGURED &&",
            "\t\t\tspeed == S22_FYG8_P282_SPEED_HIGH",
            "\t\t? S22_FYG8_E1_PROGRESS : S22_FYG8_E1_FAILURE;",
            "\treturn outcome == expected;",
            "}",
            "",
            "static noinline __used bool s22_fyg8_e1_detail_allowed(",
            "\t\tu8 profile, size_t ordinal, size_t count,",
            "\t\tu8 outcome, u16 detail)",
            "{",
            "\tu8 gate_index;",
            "\tu8 encoded_index;",
            "\tsize_t index;",
            "\tbool e3_local;",
            "",
            "\tif (profile == S22_FYG8_E1_PROFILE_E2 && ordinal < count &&",
            "\t\t\ts22_fyg8_p282_detail_allowed(",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_sequence[ordinal]),",
            "\t\t\t\toutcome, detail))",
            "\t\treturn true;",
            "\tif (profile == S22_FYG8_E1_PROFILE_E2 && ordinal < count &&",
            "\t\t\ts22_fyg8_p282_tuple_allowed(",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_sequence[ordinal]),",
            "\t\t\t\toutcome, detail))",
            "\t\treturn true;",
            "\tif (detail >= 0xc00)",
            "\t\treturn false;",
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
            "\tif (ordinal >= count)",
            "\t\treturn false;",
            "\te3_local = ordinal >= 80 &&",
            f"\t\tordinal < {spec.TERMINAL_ORDINAL};",
            "\tencoded_index = detail & 0xff;",
            f"\tif (encoded_index >= {spec.GATE_COUNT})",
            "\t\treturn false;",
            "\tif (e3_local)",
            "\t\treturn (detail >= 0x800 && detail <= 0x8ff) ||",
            "\t\t\t(detail >= 0x900 && detail <= 0x9ff);",
            "\tif (s22_fyg8_e2_kinds[ordinal] == 1) {",
            "\t\tgate_index = s22_fyg8_e2_items[ordinal];",
            "\t\tif (detail >= 0x800 && detail <= 0x8ff)",
            "\t\t\treturn encoded_index < gate_index;",
            "\t\tif (detail >= 0x900 && detail <= 0x9ff)",
            "\t\t\treturn encoded_index <= gate_index;",
            "\t}",
            "\tfor (index = 0;",
            "\t\t\tindex < ARRAY_SIZE(s22_fyg8_e2_classifier_stages);",
            "\t\t\t++index) {",
            "\t\tif (s22_fyg8_e2_sequence[ordinal] ==",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_classifier_stages[index]) &&",
            "\t\t\t\tdetail ==",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_classifier_details[index]))",
            "\t\t\treturn true;",
            "\t}",
            "\treturn false;",
            "}",
            "",
        )
    )
    return p252._kernel_prefixed(lines)


def _progress_detail_api() -> bytes:
    return (
        b"long s22_r4w1e_checkpoint_progress_detail(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t stage,\n"
        b"    uint8_t item_index,\n"
        b"    uint16_t detail) {\n"
        b"    return publish(\n"
        b"        client, stage, S22_P233_OUTCOME_PROGRESS, "
        b"item_index, detail);\n"
        b"}\n\n"
    )


def _transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_checkpoint_steps(p260.spec.STEPS),
        p248._render_checkpoint_steps(spec.STEPS),
        label="P2.86 checkpoint descriptor table",
    )
    value = _replace_exact(
        value,
        p260._checkpoint_detail_helper(),
        _checkpoint_detail_helper(),
        label="P2.86 checkpoint detail validator",
    )
    anchor = (
        b"long s22_r4w1e_checkpoint_failure(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
    )
    return _replace_exact(
        value,
        anchor,
        _progress_detail_api() + anchor,
        label="P2.86 progress-detail publisher",
    )


def _transform_patch(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_kernel_tables(p260.spec.STEPS),
        p248._render_kernel_tables(spec.STEPS),
        label="P2.86 kernel descriptor tables",
    )
    value = _replace_exact(
        value,
        p260._kernel_detail_validator(),
        _kernel_detail_validator(),
        label="P2.86 kernel detail validator",
    )
    return p252._recount_kernel_patch_hunks(value)


def _transform_runtime(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b'#include "s22plus_fyg8_p260_e3_plan.h"',
        b'#include "s22plus_fyg8_p286_e3_plan.h"',
        label="P2.86 runtime plan include",
    )
    value = _replace_exact(
        value,
        b'#include "s22plus_fyg8_p260_e3_runtime.inc.c"',
        b'#include "s22plus_fyg8_p286_e3_runtime.inc.c"',
        label="P2.86 runtime include",
    )
    return _replace_exact(
        value,
        b"    p260_e3_run();\n",
        b"    p286_e3_run();\n",
        label="P2.86 runtime handoff",
    )


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    historical = p260.generate(repository)
    return {
        "plan": historical["plan"],
        "runtime": _transform_runtime(historical["runtime"]),
        "checkpoint": _transform_checkpoint(historical["checkpoint"]),
        "patch": _transform_patch(historical["patch"]),
    }


def trace_descriptor_header(root: Path) -> bytes:
    derived = trace_contract.derive_module_contract(
        dwc3_msm_module=root / DEFAULT_DWC3_MSM_MODULE,
        hsphy_module=root / DEFAULT_HSPHY_MODULE,
    )
    return trace_contract.render_c_header(derived)


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.86 source {name}"
        )
    result["trace_descriptor_header"] = trace_descriptor_header(root)
    _validate_runtime_authority_source(result["p286_e3_runtime_include"])
    _validate_classifier_source(result["p286_classifier_include"])
    _validate_packager_integration(result)
    _validate_trace_descriptor_source(result["trace_descriptor_header"])
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.86 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _generated_semantics(
    generated: dict[str, bytes], historical: dict[str, bytes]
) -> dict[str, Any]:
    if generated["plan"] != historical["plan"]:
        raise SourceContractError("P2.86 changed the P2.60 module plan")
    runtime = generated["runtime"]
    checkpoint = generated["checkpoint"]
    patch = generated["patch"]
    required_runtime = (
        b'#include "s22plus_fyg8_p286_e3_runtime.inc.c"',
        b"p286_e3_run();",
    )
    if any(runtime.count(token) != 1 for token in required_runtime):
        raise SourceContractError("P2.86 runtime handoff drifted")
    required_checkpoint = (
        (b"k_p282_checkpoint_details[]", 1),
        (b"s22_r4w1e_checkpoint_progress_detail(", 1),
        (b"p282_tuple_detail_allowed(", 2),
        (b"if (detail >= 0xc00U)", 1),
    )
    if any(
        checkpoint.count(token) != count
        for token, count in required_checkpoint
    ):
        raise SourceContractError("P2.86 checkpoint contract drifted")
    required_patch = (
        (b"s22_fyg8_p282_details[] __used", 1),
        (b"s22_fyg8_p282_detail_allowed(", 2),
        (b"s22_fyg8_p282_tuple_allowed(", 2),
        (b"if (detail >= 0xc00)", 1),
    )
    if any(
        patch.count(token) != count for token, count in required_patch
    ):
        raise SourceContractError("P2.86 kernel contract drifted")
    if b"p260_e3_run();" in runtime:
        raise SourceContractError("P2.86 retained the P2.60 handoff")
    tables = linked_table_bytes()
    if (
        len(tables["s22_fyg8_e2_sequence"]) != len(spec.STEPS)
        or tables["s22_fyg8_e2_sequence"][-7:]
        != bytes(range(0x8D, 0x94))
        or tables["s22_fyg8_e2_items"][-7:] != bytes(7)
    ):
        raise SourceContractError("P2.86 linked stage geometry drifted")
    return {
        "p260_plan_preserved": True,
        "step_count": len(spec.STEPS),
        "terminal_generation": spec.TERMINAL_ORDINAL + 1,
        "runtime_handoff_once": True,
        "exact_detail_count": len(spec.DIAGNOSTIC_DETAILS),
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key in (
        "p286_e3_runtime_include",
        "p286_classifier_include",
        "classifier_include",
        "p260_e3_runtime_include",
        "trace_descriptor_header",
    ):
        (directory / MATERIALIZED_FILENAMES[key]).write_bytes(source[key])
    return p252._audit_userspace(
        root,
        generated,
        directory,
        materialized_filenames=MATERIALIZED_FILENAMES,
        source_check_run_id=SOURCE_CHECK_RUN_ID,
    )


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p260.generate(root)
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.86 generation is not deterministic")
    semantics = _generated_semantics(first, historical)
    source = source_bytes(root)
    with tempfile.TemporaryDirectory(prefix="s22-p286-") as temporary:
        directory = Path(temporary)
        try:
            patch = p252._audit_patch(root, first["patch"], directory)
            userspace = _audit_userspace(root, first, source, directory)
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p286_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "generated_semantics": semantics,
        "patch": patch,
        "linked_userspace": userspace,
        "trace_descriptor": receipt(source["trace_descriptor_header"]),
        "runtime_authority": dict(spec.RUNTIME_AUTHORITY),
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "terminal_ordinal": spec.TERMINAL_ORDINAL,
            "terminal_stage": spec.TERMINAL_STAGE,
            "diagnostic_detail_count": len(spec.DIAGNOSTIC_DETAILS),
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
        result = p252.validate_reachable_records(
            run_id,
            contract_spec=spec,
            decoder_module=decoder,
            expected_variants=BASE_REACHABLE_VARIANTS,
        )
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc
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

    def check_progress(stage: int, detail: int) -> None:
        nonlocal checked
        generation = spec.ordinal_for_stage(stage) + 1
        previous = spec.STEPS[generation - 2]
        slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
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
            stage=stage,
            outcome=model.OUTCOME_PROGRESS,
            item_index=0,
            detail=detail,
        )
        decoded = decoder.decode_record(
            header + b"".join(slots),
            expected_profile=PROFILE,
            expected_run_id=run_id,
        )
        if (
            decoded["active"]["stage"] != stage
            or decoded["active"]["outcome"] != model.OUTCOME_PROGRESS
            or decoded["active"]["detail"] != detail
        ):
            raise SourceContractError(
                "P2.86 progress record decode drifted"
            )
        checked += 1

    for detail in spec.DIAGNOSTIC_DETAILS:
        if spec.OUTCOME_PROGRESS not in detail.outcomes:
            continue
        for stage in detail.stages:
            check_progress(stage, detail.value)
    for repair in range(3):
        for bind in range(3):
            check_progress(
                spec.FINAL_STAGE,
                spec.encode_tuple(
                    repair,
                    bind,
                    spec.STATE_CONFIGURED,
                    spec.SPEED_HIGH,
                ),
            )
    if checked != PROGRESS_DETAIL_VARIANTS + PROGRESS_TUPLE_VARIANTS:
        raise SourceContractError("P2.86 progress variant count mismatch")
    result["reachable_slot_variants"] += checked
    result["progress_detail_variants"] = PROGRESS_DETAIL_VARIANTS
    result["progress_tuple_variants"] = PROGRESS_TUPLE_VARIANTS
    result["exact_diagnostic_detail_count"] = len(
        spec.DIAGNOSTIC_DETAILS
    )
    if result["reachable_slot_variants"] != REACHABLE_VARIANTS:
        raise SourceContractError("P2.86 reachable total drifted")
    return result


def linked_table_bytes() -> dict[str, bytes]:
    base = p252.linked_table_bytes_for(spec)
    inherited = bytearray()
    for detail in INHERITED_ROLE_DETAILS:
        inherited.extend(detail.value.to_bytes(2, "little"))
        inherited.append(detail.outcomes[0])
        inherited.append(0x01)
    rules = bytearray()
    for detail in spec.DIAGNOSTIC_DETAILS:
        rules.extend(detail.value.to_bytes(2, "little"))
        rules.append(detail.outcomes[0])
        rules.append(spec.stage_mask(detail.stages))
    return {
        **base,
        "s22_fyg8_p282_inherited_role_details": bytes(inherited),
        "s22_fyg8_p282_details": bytes(rules),
    }


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.86 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = (
    *p260.LINKED_VALIDATOR_SYMBOLS,
    "s22_fyg8_p282_inherited_role_details",
    "s22_fyg8_p282_details",
)


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        trace_contract.TraceContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
