#!/usr/bin/env python3
"""Versioned P2.52 SSUSB classifier source contract."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p232_e1_latest_stage_design as model
import s22plus_fyg8_p233_e1_static_checker as p233
import s22plus_fyg8_p241_e2_static_checker as p241
import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p245_source_contract as p245
import s22plus_fyg8_p248_source_contract as p248
import s22plus_fyg8_p251_ssusb_dependency_audit as p251
import s22plus_fyg8_p251b_phy_nested_closure_audit as p251b
import s22plus_fyg8_p252_contract_spec as spec
import s22plus_fyg8_p252_e1_decoder as decoder


CONTRACT_ID = "s22plus-fyg8-p252-e2-ssusb-classifier-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P252-E2-SSUSB-CLASSIFIER-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p252_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p252_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P252_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p252_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P252_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P252_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P252_SSUSB_CLASSIFIER_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P252-SSUSB-CLASSIFIER-SOURCE-CHECK-V1"
).digest()[:16]

GENERATED_KEYS = p248.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p248.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p252_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p252_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p244_e2_plan.h",
}

COMMON_SOURCE_PATHS = dict(p248.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS["p248_source_contract"] = COMMON_SOURCE_PATHS.pop(
    "source_contract"
)
COMMON_SOURCE_PATHS["p248_contract_spec"] = COMMON_SOURCE_PATHS.pop(
    "contract_spec"
)
COMMON_SOURCE_PATHS["p248_decoder_adapter"] = COMMON_SOURCE_PATHS.pop(
    "decoder_adapter"
)
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p252_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p252_contract_spec.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p252_e1_decoder.py"
        ),
        "p251_dependency_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p251_ssusb_dependency_audit.py"
        ),
        "p251b_nested_audit": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p251b_phy_nested_closure_audit.py"
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


SourceContract = p248.SourceContract
P252 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p248.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P252


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


def _classifier_rows() -> tuple[spec.ClassifierDetail, ...]:
    spec.validate_classifier_details()
    return spec.CLASSIFIER_DETAILS


def _render_checkpoint_classifier_tables() -> bytes:
    rows = _classifier_rows()
    stages = ", ".join(f"0x{spec.SSUSB_STAGE:02x}U" for _row in rows)
    details = ", ".join(f"0x{row.value:03x}U" for row in rows)
    return (
        "static const uint8_t k_p252_classifier_stages[] = {\n"
        f"    {stages},\n"
        "};\n"
        "static const uint16_t k_p252_classifier_details[] = {\n"
        f"    {details},\n"
        "};\n"
        "_Static_assert(\n"
        "    sizeof(k_p252_classifier_stages) ==\n"
        "        sizeof(k_p252_classifier_details) /\n"
        "            sizeof(k_p252_classifier_details[0]),\n"
        '    "P2.52 classifier stage/detail count");\n\n'
    ).encode("ascii")


def _render_checkpoint_detail_helper() -> bytes:
    return f"""static int p252_detail_allowed(
    uint8_t stage, uint8_t outcome, uint16_t detail) {{
#if S22PLUS_FYG8_P233_PROFILE == 3
    const struct s22_p248_step *step = NULL;
    for (size_t index = 0;
         index < sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
         ++index) {{
        if (k_p248_e2_steps[index].stage == stage) {{
            step = &k_p248_e2_steps[index];
            break;
        }}
    }}
    if (step == NULL) {{
        return 0;
    }}
    if (step->kind == S22_P248_STEP_TERMINAL) {{
        return outcome == S22_P233_OUTCOME_SUCCESS && detail == 0U;
    }}
    if (outcome == S22_P233_OUTCOME_PROGRESS) {{
        return detail == 0U;
    }}
    if (outcome != S22_P233_OUTCOME_FAILURE || detail == 0U) {{
        return 0;
    }}
    if (detail <= S22_P248_DETAIL_ERRNO_MAX) {{
        return 1;
    }}
    if (step->kind == S22_P248_STEP_GATE &&
        detail >= S22_P248_DETAIL_REGRESSION_BASE &&
        detail <= S22_P248_DETAIL_REGRESSION_MAX) {{
        uint8_t encoded_index = (uint8_t)(detail & 0xffU);
        return encoded_index < {spec.GATE_COUNT}U &&
            encoded_index < step->item_index;
    }}
    if (step->kind == S22_P248_STEP_GATE &&
        detail >= S22_P248_DETAIL_READ_ERROR_BASE &&
        detail <= S22_P248_DETAIL_READ_ERROR_MAX) {{
        uint8_t encoded_index = (uint8_t)(detail & 0xffU);
        return encoded_index < {spec.GATE_COUNT}U &&
            encoded_index <= step->item_index;
    }}
    for (size_t index = 0;
         index < sizeof(k_p252_classifier_stages); ++index) {{
        if (stage == k_p252_classifier_stages[index] &&
            detail == k_p252_classifier_details[index]) {{
            return 1;
        }}
    }}
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
}}

""".encode("ascii")


def _render_checkpoint_failure() -> bytes:
    return b"""long s22_r4w1e_checkpoint_failure(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    long operation_error) {
    unsigned long detail;
    if (operation_error < 0) {
        if (operation_error < -(long)S22_P248_DETAIL_ERRNO_MAX) {
            return -EINVAL;
        }
        detail = (unsigned long)(-operation_error);
    } else {
        detail = (unsigned long)operation_error;
    }
    if (detail == 0U) {
        detail = EIO;
    }
    if (detail > 0xffffU) {
        return -EINVAL;
    }
    return publish(
        client,
        stage,
        S22_P233_OUTCOME_FAILURE,
        item_index,
        (uint16_t)detail);
}

"""


def transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"static int p248_detail_allowed(\n",
        _render_checkpoint_classifier_tables()
        + b"static int p248_detail_allowed(\n",
        label="checkpoint classifier-table insertion",
    )
    value = _replace_span(
        value,
        b"static int p248_detail_allowed(\n",
        b"static long publish(\n",
        _render_checkpoint_detail_helper(),
        label="checkpoint detail validator",
    )
    value = _replace_exact(
        value,
        b"    if (!p248_detail_allowed(stage, outcome, detail)) {\n",
        b"    if (!p252_detail_allowed(stage, outcome, detail)) {\n",
        label="checkpoint validator call",
    )
    return _replace_span(
        value,
        b"long s22_r4w1e_checkpoint_failure(\n",
        b"long s22_r4w1e_checkpoint_success(\n",
        _render_checkpoint_failure(),
        label="checkpoint positive-detail normalization",
    )


def _render_runtime_classifier_table() -> bytes:
    lines = [
        "struct s22_p252_bind_classifier {",
        "    const char *path;",
        "    const char *expected_basename;",
        "    long detail;",
        "};",
        "",
        "static const struct s22_p252_bind_classifier "
        "k_p252_bind_classifiers[] = {",
    ]
    for row in spec.BIND_CLASSIFIERS:
        assert row.path is not None
        assert row.expected_symlink_basename is not None
        lines.extend(
            (
                "    {",
                f'        "{row.path}",',
                f'        "{row.expected_symlink_basename}",',
                f"        0x{row.value:03x}L,",
                "    },",
            )
        )
    lines.extend(
        (
            "};",
            "",
            "_Static_assert(",
            "    sizeof(k_p252_bind_classifiers) /",
            "        sizeof(k_p252_bind_classifiers[0]) == 15U,",
            '    "P2.52 bind classifier count");',
            "",
        )
    )
    return "\n".join(lines).encode("ascii")


def _render_runtime_helpers() -> bytes:
    waiting = spec.CLASSIFIER_BY_VALUE[0xA10].value
    grace = spec.CLASSIFIER_BY_VALUE[0xA30].value
    return f"""static long p252_check_driver_symlink(
    const char *path, const char *expected_basename) {{
    struct s22_p241_kernel_stat stat_buffer = {{0}};
    char target[S22_P241_SYMLINK_TARGET_MAX];
    long stat_rc = p241_newfstatat(path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (stat_rc != 0) {{
        return stat_rc == -ENOENT ? -ENODEV : stat_rc;
    }}
    if ((stat_buffer.st_mode & S_IFMT) != S_IFLNK) {{
        return -ENODEV;
    }}
    long target_size = p241_readlinkat(path, target, sizeof(target));
    if (target_size == -ENOENT) {{
        return -ENODEV;
    }}
    if (target_size <= 0 || target_size >= (long)sizeof(target)) {{
        return target_size < 0 ? target_size : -EIO;
    }}
    return p241_basename_equals(
        target, (size_t)target_size, expected_basename)
        ? 0
        : -ENODEV;
}}

static long p252_read_waiting_for_supplier(int *waiting) {{
    static const char path[] =
        "{spec.WAITING_FOR_SUPPLIER_PATH}";
    char value[3] = {{0}};
    char extra = 0;
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {{
        return fd;
    }}
    long amount = sys_read((int)fd, value, sizeof(value));
    long extra_amount = amount == 2
        ? sys_read((int)fd, &extra, sizeof(extra))
        : 0;
    long close_rc = sys_close((int)fd);
    if (amount < 0) {{
        return amount;
    }}
    if (extra_amount < 0) {{
        return extra_amount;
    }}
    if (close_rc != 0) {{
        return close_rc;
    }}
    if (amount != 2 || extra_amount != 0 || value[1] != '\\n' ||
        (value[0] != '0' && value[0] != '1')) {{
        return -EIO;
    }}
    *waiting = value[0] == '1';
    return 0;
}}

static __attribute__((noreturn)) void p252_fail_prior_gate(
    size_t index, long gate_rc) {{
    long detail = gate_rc == -ENODEV
        ? S22_P248_DETAIL_REGRESSION_BASE + (long)index
        : S22_P248_DETAIL_READ_ERROR_BASE + (long)index;
    fail_at(
        S22_P252_SSUSB_STAGE,
        S22_P252_SSUSB_GATE_INDEX,
        detail);
}}

static void p252_revalidate_prior_or_fail(void) {{
    for (size_t index = 0; index < S22_P252_SSUSB_GATE_INDEX; ++index) {{
        long gate_rc = p241_check_gate(index);
        if (gate_rc != 0) {{
            p252_fail_prior_gate(index, gate_rc);
        }}
    }}
}}

static int p252_finalize_classifier(long proposed_detail) {{
    p252_revalidate_prior_or_fail();
    long parent_rc = p241_check_gate(S22_P252_SSUSB_GATE_INDEX);
    if (parent_rc == 0) {{
        long checkpoint_rc = s22_r4w1e_checkpoint_progress(
            &g_checkpoint,
            S22_P252_SSUSB_STAGE,
            S22_P252_SSUSB_GATE_INDEX);
        if (checkpoint_rc != 0) {{
            quiet_park();
        }}
        return 1;
    }}
    if (parent_rc != -ENODEV) {{
        proposed_detail = S22_P252_SSUSB_READ_ERROR_DETAIL;
    }}
    fail_at(
        S22_P252_SSUSB_STAGE,
        S22_P252_SSUSB_GATE_INDEX,
        proposed_detail);
}}

static int p252_classify_ssusb(int allow_grace);

static int p252_run_grace(void) {{
    struct timespec64 deadline = {{0}};
    if (p241_clock_gettime(&deadline) != 0 ||
        deadline.tv_sec > 0x7fffffffffffffffLL - S22_P252_GRACE_SEC) {{
        return p252_finalize_classifier(
            S22_P252_SSUSB_READ_ERROR_DETAIL);
    }}
    deadline.tv_sec += S22_P252_GRACE_SEC;
    for (;;) {{
        p252_revalidate_prior_or_fail();
        long parent_rc = p241_check_gate(S22_P252_SSUSB_GATE_INDEX);
        if (parent_rc == 0 || parent_rc != -ENODEV) {{
            return p252_finalize_classifier(
                S22_P252_SSUSB_READ_ERROR_DETAIL);
        }}
        struct timespec64 now = {{0}};
        if (p241_clock_gettime(&now) != 0) {{
            return p252_finalize_classifier(
                S22_P252_SSUSB_READ_ERROR_DETAIL);
        }}
        if (!p241_timespec_before(&now, &deadline)) {{
            return p252_classify_ssusb(0);
        }}
        (void)sys_nanosleep(S22_P241_GATE_POLL_NS);
    }}
}}

static int p252_classify_ssusb(int allow_grace) {{
    p252_revalidate_prior_or_fail();
    long parent_rc = p241_check_gate(S22_P252_SSUSB_GATE_INDEX);
    if (parent_rc == 0 || parent_rc != -ENODEV) {{
        return p252_finalize_classifier(
            S22_P252_SSUSB_READ_ERROR_DETAIL);
    }}

    int waiting = 0;
    long waiting_rc = p252_read_waiting_for_supplier(&waiting);
    if (waiting_rc != 0) {{
        return p252_finalize_classifier(
            S22_P252_SSUSB_READ_ERROR_DETAIL);
    }}

    for (size_t index = 0;
         index < sizeof(k_p252_bind_classifiers) /
            sizeof(k_p252_bind_classifiers[0]);
         ++index) {{
        const struct s22_p252_bind_classifier *classifier =
            &k_p252_bind_classifiers[index];
        long bind_rc = p252_check_driver_symlink(
            classifier->path, classifier->expected_basename);
        if (bind_rc == -ENODEV) {{
            return p252_finalize_classifier(classifier->detail);
        }}
        if (bind_rc != 0) {{
            return p252_finalize_classifier(
                S22_P252_SSUSB_READ_ERROR_DETAIL);
        }}
    }}

    parent_rc = p241_check_gate(S22_P252_SSUSB_GATE_INDEX);
    if (parent_rc == 0 || parent_rc != -ENODEV) {{
        return p252_finalize_classifier(
            S22_P252_SSUSB_READ_ERROR_DETAIL);
    }}
    waiting_rc = p252_read_waiting_for_supplier(&waiting);
    if (waiting_rc != 0) {{
        return p252_finalize_classifier(
            S22_P252_SSUSB_READ_ERROR_DETAIL);
    }}
    if (waiting) {{
        return p252_finalize_classifier(0x{waiting:03x}L);
    }}
    if (allow_grace) {{
        return p252_run_grace();
    }}
    return p252_finalize_classifier(0x{grace:03x}L);
}}

""".encode("ascii")


def transform_runtime(data: bytes) -> bytes:
    definitions = (
        f"#define S22_P252_SSUSB_STAGE 0x{spec.SSUSB_STAGE:02x}U\n"
        f"#define S22_P252_SSUSB_GATE_INDEX {spec.SSUSB_GATE_INDEX}U\n"
        f"#define S22_P252_SSUSB_READ_ERROR_DETAIL "
        f"0x{spec.WAITING_READ_ERROR_DETAIL:03x}L\n"
        f"#define S22_P252_GRACE_SEC {spec.GRACE_SECONDS}LL\n"
    ).encode("ascii")
    value = _replace_exact(
        data,
        b"#define S22_P248_DETAIL_READ_ERROR_BASE 0x900L\n",
        b"#define S22_P248_DETAIL_READ_ERROR_BASE 0x900L\n" + definitions,
        label="runtime classifier definitions",
    )
    value = _replace_exact(
        value,
        b"static long p241_check_gate(size_t index) {\n",
        _render_runtime_classifier_table()
        + b"static long p241_check_gate(size_t index) {\n",
        label="runtime classifier table",
    )
    value = _replace_exact(
        value,
        b"static __attribute__((noreturn)) void p241_run(void) {\n",
        _render_runtime_helpers()
        + b"static __attribute__((noreturn)) void p241_run(void) {\n",
        label="runtime classifier helpers",
    )
    value = _replace_exact(
        value,
        b"    size_t completed = 0;\n"
        b"    while (completed < S22PLUS_O2_BIND_GATE_COUNT) {\n",
        b"    size_t completed = 0;\n"
        b"    int post_grace_drain = 0;\n"
        b"    while (completed < S22PLUS_O2_BIND_GATE_COUNT) {\n"
        b"        int advanced = 0;\n",
        label="runtime post-grace drain state",
    )
    value = _replace_exact(
        value,
        b"                ++completed;\n"
        b"            } else if (gate_rc != -ENODEV) {\n",
        b"                ++completed;\n"
        b"                advanced = 1;\n"
        b"            } else if (gate_rc != -ENODEV) {\n",
        label="runtime frontier progress tracking",
    )
    value = _replace_exact(
        value,
        b"        if (completed == S22PLUS_O2_BIND_GATE_COUNT) {\n"
        b"            break;\n"
        b"        }\n"
        b"        struct timespec64 now = {0};\n",
        b"        if (completed == S22PLUS_O2_BIND_GATE_COUNT) {\n"
        b"            break;\n"
        b"        }\n"
        b"        if (post_grace_drain) {\n"
        b"            if (advanced) {\n"
        b"                continue;\n"
        b"            }\n"
        b"            fail_at(\n"
        b"                S22_P241_GATE_STAGE_BASE + (uint8_t)completed,\n"
        b"                (uint8_t)completed,\n"
        b"                -ETIMEDOUT);\n"
        b"        }\n"
        b"        struct timespec64 now = {0};\n",
        label="runtime checked downstream drain",
    )
    old_timeout = (
        b"        if (!p241_timespec_before(&now, &deadline)) {\n"
        b"            fail_at(\n"
        b"                S22_P241_GATE_STAGE_BASE + (uint8_t)completed,\n"
        b"                (uint8_t)completed,\n"
        b"                -ETIMEDOUT);\n"
        b"        }\n"
    )
    new_timeout = (
        b"        if (!p241_timespec_before(&now, &deadline)) {\n"
        b"            if (completed == S22_P252_SSUSB_GATE_INDEX) {\n"
        b"                if (p252_classify_ssusb(1)) {\n"
        b"                    ++completed;\n"
        b"                    post_grace_drain = 1;\n"
        b"                    continue;\n"
        b"                }\n"
        b"                quiet_park();\n"
        b"            }\n"
        b"            fail_at(\n"
        b"                S22_P241_GATE_STAGE_BASE + (uint8_t)completed,\n"
        b"                (uint8_t)completed,\n"
        b"                -ETIMEDOUT);\n"
        b"        }\n"
    )
    return _replace_exact(
        value,
        old_timeout,
        new_timeout,
        label="runtime SSUSB timeout dispatch",
    )


def _kernel_prefixed(lines: list[str]) -> bytes:
    return ("\n".join(f"+{line}" for line in lines) + "\n").encode("ascii")


def _render_kernel_classifier_tables() -> bytes:
    rows = _classifier_rows()
    stages = ", ".join(f"0x{spec.SSUSB_STAGE:02x}" for _row in rows)
    details = ", ".join(f"0x{row.value:03x}" for row in rows)
    return _kernel_prefixed(
        [
            "static const u8 s22_fyg8_e2_classifier_stages[] __used = {",
            f"\t{stages},",
            "};",
            "static const u16 s22_fyg8_e2_classifier_details[] __used = {",
            f"\t{details},",
            "};",
            "",
        ]
    )


def _render_kernel_detail_validator() -> bytes:
    return _kernel_prefixed(
        [
            "static noinline __used bool s22_fyg8_e1_detail_allowed(",
            "\t\tu8 profile, size_t ordinal, size_t count,",
            "\t\tu8 outcome, u16 detail)",
            "{",
            "\tu8 gate_index;",
            "\tu8 encoded_index;",
            "\tsize_t index;",
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
            "\tif (detail >= 0x800 && detail <= 0x8ff) {",
            "\t\tencoded_index = detail & 0xff;",
            f"\t\treturn encoded_index < {spec.GATE_COUNT} &&",
            "\t\t\tencoded_index < gate_index;",
            "\t}",
            "\tif (detail >= 0x900 && detail <= 0x9ff) {",
            "\t\tencoded_index = detail & 0xff;",
            f"\t\treturn encoded_index < {spec.GATE_COUNT} &&",
            "\t\t\tencoded_index <= gate_index;",
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
        ]
    )


def _recount_kernel_patch_hunks(data: bytes) -> bytes:
    lines = data.splitlines(keepends=True)
    main_indices = [
        index
        for index, line in enumerate(lines)
        if line.startswith(b"@@ -1376,6 +1379,")
    ]
    following_indices = [
        index
        for index, line in enumerate(lines)
        if line.startswith(b"@@ -1465,6 +")
        and b"static int __ref kernel_init" in line
    ]
    if len(main_indices) != 1 or len(following_indices) != 1:
        raise SourceContractError("P2.52 kernel patch hunk headers changed")
    main_index = main_indices[0]
    following_index = following_indices[0]
    if following_index <= main_index:
        raise SourceContractError("P2.52 kernel patch hunk order changed")
    main_match = re.match(
        rb"@@ -1376,6 \+1379,(\d+) @@ ", lines[main_index]
    )
    following_match = re.match(
        rb"@@ -1465,6 \+(\d+),7 @@ ", lines[following_index]
    )
    if main_match is None or following_match is None:
        raise SourceContractError("P2.52 kernel patch hunk syntax changed")
    old_count = int(main_match.group(1))
    old_following_start = int(following_match.group(1))
    new_count = sum(
        line.startswith((b"+", b" "))
        for line in lines[main_index + 1 : following_index]
    )
    lines[main_index] = (
        f"@@ -1376,6 +1379,{new_count} @@ "
        "static int run_init_process(const char *init_filename)\n"
    ).encode("ascii")
    lines[following_index] = (
        f"@@ -1465,6 +{old_following_start + new_count - old_count},7 @@ "
        "static int __ref kernel_init(void *unused)\n"
    ).encode("ascii")
    return b"".join(lines)


def transform_patch(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"+\n+static bool s22_fyg8_e1_parse_reg",
        b"+\n"
        + _render_kernel_classifier_tables()
        + b"+static bool s22_fyg8_e1_parse_reg",
        label="kernel classifier-table insertion",
    )
    value = _replace_span(
        value,
        b"+static bool s22_fyg8_e1_detail_allowed(\n",
        b"+static bool s22_fyg8_e1_request_allowed(\n",
        _render_kernel_detail_validator(),
        label="kernel classifier validator",
    )
    value = _replace_exact(
        value,
        b"+static bool s22_fyg8_e1_request_allowed(\n",
        b"+static noinline __used bool s22_fyg8_e1_request_allowed(\n",
        label="kernel request validator retention",
    )
    return _recount_kernel_patch_hunks(value)


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    base = p248.generate(repository)
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
        result[name] = p233.read_direct(root / path, f"P2.52 source {name}")
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.52 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def _audit_path_map() -> dict[str, Any]:
    expected = [
        (int(detail, 16), path)
        for _name, path, detail in p251.PROVIDER_CHECKS
    ]
    expected.extend(
        (int(row["detail"], 16), row["path"])
        for row in p251b.nested_checks()
    )
    expected.extend(
        (int(detail, 16), path)
        for _name, path, detail in p251.PHY_CHECKS
    )
    actual = [(row.value, row.path) for row in spec.BIND_CLASSIFIERS]
    if actual != expected:
        raise SourceContractError("P2.52 classifier differs from P2.51/P2.51b")
    return {
        "bind_classifier_count": len(actual),
        "p251_p251b_exact": True,
        "verified": True,
    }


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    patch_path = directory / "p252.patch"
    patch_path.write_bytes(patch)
    p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=root / p241.DEFAULT_SOURCE,
        label="P2.52 clean-apply check",
    )
    text = patch.decode("ascii")
    required = (
        "s22_fyg8_e2_classifier_stages[] __used",
        "s22_fyg8_e2_classifier_details[] __used",
        "s22_fyg8_e2_sequence[ordinal]",
        "detail >= 0x800 && detail <= 0x8ff",
        "detail >= 0x900 && detail <= 0x9ff",
    )
    if any(token not in text for token in required):
        raise SourceContractError("P2.52 kernel validator source is incomplete")
    if "encoded_index = detail & 0xff;" not in text:
        raise SourceContractError("P2.52 structured gate detail check is absent")
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
            label=f"P2.52 deterministic userspace link {suffix}",
        )
        outputs.append(output.read_bytes())
    if outputs[0] != outputs[1]:
        raise SourceContractError("P2.52 repeated userspace link differs")
    file_text = p233.run_checked(
        ["file", "-b", str(directory / "init-a")],
        cwd=root,
        label="P2.52 userspace file inspection",
    ).stdout.decode("ascii", "replace")
    if "ELF 64-bit LSB executable, ARM aarch64" not in file_text:
        raise SourceContractError("P2.52 userspace output is not AArch64 ELF")
    return {
        **receipt(outputs[0]),
        "static_aarch64": "statically linked" in file_text,
        "two_link_reproducible": True,
        "verified": True,
    }


def audit_generated_semantics(
    generated: dict[str, bytes],
    historical: dict[str, bytes],
) -> dict[str, Any]:
    if set(generated) != {"plan", "runtime", "checkpoint", "patch"}:
        raise SourceContractError("P2.52 generated inventory changed")
    if generated["plan"] != historical["plan"]:
        raise SourceContractError("P2.52 module plan differs from P2.48")

    runtime = generated["runtime"]
    checkpoint = generated["checkpoint"]
    patch = generated["patch"]
    if runtime.count(_render_runtime_classifier_table()) != 1:
        raise SourceContractError("P2.52 runtime classifier table drifted")
    if checkpoint.count(_render_checkpoint_classifier_tables()) != 1:
        raise SourceContractError("P2.52 checkpoint whitelist drifted")
    if patch.count(_render_kernel_classifier_tables()) != 1:
        raise SourceContractError("P2.52 kernel whitelist drifted")

    runtime_text = runtime.decode("ascii")
    checkpoint_text = checkpoint.decode("ascii")
    patch_text = patch.decode("ascii")
    runtime_required_once = (
        f"#define S22_P252_SSUSB_STAGE 0x{spec.SSUSB_STAGE:02x}U",
        f"#define S22_P252_SSUSB_GATE_INDEX {spec.SSUSB_GATE_INDEX}U",
        f"#define S22_P252_SSUSB_READ_ERROR_DETAIL "
        f"0x{spec.WAITING_READ_ERROR_DETAIL:03x}L",
        f"#define S22_P252_GRACE_SEC {spec.GRACE_SECONDS}LL",
        "amount != 2 || extra_amount != 0 || value[1] != '\\n'",
        "p252_classify_ssusb(1)",
        "p252_classify_ssusb(0)",
        "return p252_run_grace();",
        "return p252_finalize_classifier(classifier->detail);",
        "int post_grace_drain = 0;",
        "post_grace_drain = 1;\n                    continue;",
        "if (post_grace_drain) {",
        "if (advanced) {\n                continue;",
    )
    if any(runtime_text.count(token) != 1 for token in runtime_required_once):
        raise SourceContractError("P2.52 runtime bounded semantics drifted")
    if runtime_text.count("#define S22_P241_GATE_TIMEOUT_SEC 20LL") != 1:
        raise SourceContractError("P2.52 global gate timeout changed")
    if runtime_text.count(
        "fail_at(\n        S22_P252_SSUSB_STAGE,"
    ) != 2:
        raise SourceContractError(
            "P2.52 classifier bypasses its prior/parent finalizer"
        )
    drain_state = runtime_text.index("int post_grace_drain = 0;")
    drain_progress = runtime_text.index(
        "advanced = 1;", drain_state
    )
    drain_check = runtime_text.index(
        "if (post_grace_drain) {", drain_progress
    )
    post_drain_clock = runtime_text.index(
        "struct timespec64 now = {0};", drain_check
    )
    if not drain_state < drain_progress < drain_check < post_drain_clock:
        raise SourceContractError(
            "P2.52 checked downstream drain order changed"
        )
    if not (
        runtime_text.index("p252_revalidate_prior_or_fail();")
        < runtime_text.index(
            "long parent_rc = p241_check_gate("
            "S22_P252_SSUSB_GATE_INDEX);"
        )
        < runtime_text.index(
            "fail_at(\n        S22_P252_SSUSB_STAGE,"
            "\n        S22_P252_SSUSB_GATE_INDEX,"
            "\n        proposed_detail);"
        )
    ):
        raise SourceContractError("P2.52 finalizer order changed")
    if not (
        runtime_text.index("p252_read_waiting_for_supplier(&waiting)")
        < runtime_text.index("k_p252_bind_classifiers[index]")
        < runtime_text.rindex("p252_read_waiting_for_supplier(&waiting)")
    ):
        raise SourceContractError("P2.52 waiting/classifier rescan order changed")

    checkpoint_required = (
        "static int p252_detail_allowed(",
        "detail >= S22_P248_DETAIL_REGRESSION_BASE",
        "detail >= S22_P248_DETAIL_READ_ERROR_BASE",
        "detail == k_p252_classifier_details[index]",
        "if (detail > 0xffffU)",
    )
    if any(checkpoint_text.count(token) != 1 for token in checkpoint_required):
        raise SourceContractError("P2.52 checkpoint validator drifted")
    if (
        "detail > S22_P248_DETAIL_READ_ERROR_MAX" in checkpoint_text
        or checkpoint_text.index(
            "detail >= S22_P248_DETAIL_REGRESSION_BASE"
        )
        > checkpoint_text.index(
            "detail == k_p252_classifier_details[index]"
        )
    ):
        raise SourceContractError("P2.52 checkpoint dispatch order changed")

    patch_required = (
        "static noinline __used bool s22_fyg8_e1_detail_allowed(",
        "static noinline __used bool s22_fyg8_e1_request_allowed(",
        "s22_fyg8_e2_sequence[ordinal] ==",
        "READ_ONCE(s22_fyg8_e2_classifier_stages[index])",
        "READ_ONCE(s22_fyg8_e2_classifier_details[index])",
    )
    if any(patch_text.count(token) != 1 for token in patch_required):
        raise SourceContractError("P2.52 kernel validator drifted")
    if patch_text.index("detail >= 0x800 && detail <= 0x8ff") > (
        patch_text.index("s22_fyg8_e2_sequence[ordinal] ==")
    ):
        raise SourceContractError("P2.52 kernel dispatch order changed")
    return {
        "plan_unchanged": True,
        "runtime_from_descriptor": True,
        "checkpoint_from_descriptor": True,
        "kernel_from_descriptor": True,
        "global_timeout_seconds": 20,
        "grace_seconds": spec.GRACE_SECONDS,
        "common_finalizer_enforced": True,
        "verified": True,
    }


def implementation_result(root: Path) -> dict[str, Any]:
    historical_before = p248.generate(root)
    first = generate(root)
    second = generate(root)
    historical_after = p248.generate(root)
    if historical_before != historical_after:
        raise SourceContractError("P2.48 generated output changed")
    if first != second or first["plan"] != historical_before["plan"]:
        raise SourceContractError("P2.52 generation is not deterministic")

    generated_semantics = audit_generated_semantics(first, historical_before)

    with tempfile.TemporaryDirectory(prefix="s22-p252-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, directory)
    return {
        "schema": "s22plus_fyg8_p252_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "historical_p248_unchanged": True,
        "generated_semantics": generated_semantics,
        "path_map": _audit_path_map(),
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
            "grace_seconds": spec.GRACE_SECONDS,
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
        raise SourceContractError("P2.52 run ID must be one nonzero 128-bit value")
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
                    "P2.52 decoder changed a reachable active slot"
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
        raise SourceContractError("P2.52 reachable-record count mismatch")
    return {
        "reachable_slot_variants": checked,
        "classifier_detail_count": len(spec.CLASSIFIER_DETAILS),
        "profiles": [PROFILE],
        "checked_run_ids": {PROFILE: run_id.hex()},
        "adjacent_slot_combinations_verified": True,
        "zero_crc_count": 0,
        "family_collision_count": 0,
        "decoder_policy_id": decoder.POLICY_ID,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    result = dict(p248.linked_table_bytes())
    result["s22_fyg8_e2_classifier_stages"] = bytes(
        spec.SSUSB_STAGE for _row in spec.CLASSIFIER_DETAILS
    )
    result["s22_fyg8_e2_classifier_details"] = b"".join(
        row.value.to_bytes(2, "little") for row in spec.CLASSIFIER_DETAILS
    )
    return result


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.52 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "classifier_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = (
    *p248.LINKED_VALIDATOR_SYMBOLS,
    "s22_fyg8_e1_request_allowed",
    "s22_fyg8_e1_detail_allowed",
)


def _linked_validator_loads_table(
    disassembly: str,
    table_address: int,
    load_mnemonic: str,
) -> bool:
    register_values: dict[str, int] = {}
    for line in disassembly.splitlines():
        instruction = re.search(
            r"^\s*[0-9a-fA-F]+:\s+[0-9a-fA-F]+\s+"
            r"([a-zA-Z0-9_.]+)\s*(.*)$",
            line,
        )
        if instruction is None:
            continue
        mnemonic, operands = instruction.groups()
        address = re.search(
            r"^(x\d+),\s*(?:0x)?([0-9a-fA-F]+)\b", operands
        )
        if mnemonic in {"adr", "adrp"} and address:
            register_values[address.group(1)] = int(address.group(2), 16)
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
            mnemonic == load_mnemonic
            and load is not None
            and register_values.get(load.group(1)) == table_address
        ):
            return True
        no_destination = (
            mnemonic == "b"
            or mnemonic.startswith("b.")
            or mnemonic
            in {
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
    return False


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    expected_item = disassembly.get("s22_fyg8_e1_expected_item")
    request_validator = disassembly.get("s22_fyg8_e1_request_allowed")
    detail_validator = disassembly.get("s22_fyg8_e1_detail_allowed")
    writer = disassembly.get("s22_fyg8_e1_write")
    writer_calls = calls.get("s22_fyg8_e1_write")
    request_calls = calls.get("s22_fyg8_e1_request_allowed")
    if not all(
        isinstance(value, str)
        for value in (
            expected_item,
            request_validator,
            detail_validator,
            writer,
        )
    ) or not isinstance(writer_calls, list) or not isinstance(
        request_calls, list
    ):
        raise SourceContractError(
            "P2.52 linked validator evidence is incomplete"
        )
    if "s22_fyg8_e1_request_allowed" not in writer_calls:
        raise SourceContractError(
            "P2.52 linked writer does not call the request validator"
        )
    if (
        "s22_fyg8_e1_expected_item" not in request_calls
        or "s22_fyg8_e1_detail_allowed" not in request_calls
    ):
        raise SourceContractError(
            "P2.52 linked request validator does not call both validators"
        )
    item_address = symbol_addresses.get("s22_fyg8_e2_items")
    stage_address = symbol_addresses.get(
        "s22_fyg8_e2_classifier_stages"
    )
    detail_address = symbol_addresses.get(
        "s22_fyg8_e2_classifier_details"
    )
    if (
        not isinstance(item_address, int)
        or not isinstance(stage_address, int)
        or not isinstance(detail_address, int)
    ):
        raise SourceContractError(
            "P2.52 linked validator-table addresses are missing"
        )
    if not _linked_validator_loads_table(
        expected_item, item_address, "ldrb"
    ):
        raise SourceContractError(
            "P2.52 linked item validator does not load the item table"
        )
    if not _linked_validator_loads_table(
        detail_validator, stage_address, "ldrb"
    ):
        raise SourceContractError(
            "P2.52 linked detail validator does not load the stage whitelist"
        )
    if not _linked_validator_loads_table(
        detail_validator, detail_address, "ldrh"
    ):
        raise SourceContractError(
            "P2.52 linked detail validator does not load the detail whitelist"
        )
    stale_compare = re.compile(r"\bcmp\s+[wx]\d+,\s*#(?:0x)?8\b")
    if any(
        stale_compare.search(text)
        for text in (expected_item, request_validator, writer)
    ):
        raise SourceContractError(
            "P2.52 linked validator retains the stale eight-item compare"
        )
    return {
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "item_validator_loads_item_table": True,
        "validator_loads_classifier_stage_table": True,
        "validator_loads_classifier_detail_table": True,
        "stale_eight_item_compare_absent": True,
        "verified": True,
    }


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        spec.SpecError,
        p248.SourceContractError,
        p251.AuditError,
        p251b.AuditError,
        p241.CheckError,
        p233.CheckError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
