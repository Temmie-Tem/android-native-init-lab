#!/usr/bin/env python3
"""Prove P2.92 accept-to-resume, sequence-walk, and errno closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable

import s22plus_fyg8_p288_source_contract as p288_source
import s22plus_fyg8_p290_contract_spec as positions
import s22plus_fyg8_p292_repair_decoder as decoder
import s22plus_fyg8_p292_repair_generator as generator
import s22plus_fyg8_p292_repair_model as model
import s22plus_fyg8_p292_repair_spec as repair
import s22plus_fyg8_p292_sot_zero_delta as zero


SCHEMA = "s22plus_fyg8_p292_accept_to_resume_result_v1"
VERDICT = "PASS_P292_ACCEPT_TO_RESUME_AND_ERRNO_CLOSURE"
PAIR_ADJACENCY_VERDICT = "PASS_ACCEPT_TO_RESUME_PAIR_ADJACENCY"
CANONICAL_LIVE_DETAIL_ORDINAL = 87
CANONICAL_LIVE_DETAIL = 0xC18
CONSECUTIVE_DETAIL_ORDINALS = (86, 87)
CONSECUTIVE_DETAIL = 0xC01
TRACE_RECORD_COUNT = 2 * len(positions.POSITIONS)


class ClosureError(ValueError):
    pass


ArtifactMutator = Callable[[dict[str, bytes]], dict[str, bytes]]


_C_TOKEN = re.compile(
    rb"""
    (?P<space>\s+)
    |(?P<line_comment>//[^\r\n]*(?:\r?\n|$))
    |(?P<block_comment>/\*.*?\*/)
    |(?P<string>"(?:\\.|[^"\\])*")
    |(?P<character>'(?:\\.|[^'\\])*')
    |(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)
    |(?P<number>0[xX][0-9A-Fa-f]+[uUlL]*|[0-9]+[uUlL]*)
    |(?P<operator>
        >>=|<<=|\.\.\.|->|\+\+|--|&&|\|\||==|!=|<=|>=|<<|>>|
        \+=|-=|\*=|/=|%=|&=|\|=|\^=|[{}()\[\];,.*&=+\-/%!<>?:~^|#\\]
    )
    """,
    re.DOTALL | re.VERBOSE,
)


def _c_tokens(source: bytes, label: str) -> tuple[bytes, ...]:
    if not isinstance(source, bytes):
        raise ClosureError(f"{label} is not bytes")
    result: list[bytes] = []
    offset = 0
    while offset < len(source):
        match = _C_TOKEN.match(source, offset)
        if match is None:
            raise ClosureError(
                f"{label} has an unparsed C byte at offset {offset}"
            )
        if match.lastgroup not in {
            "space",
            "line_comment",
            "block_comment",
        }:
            result.append(match.group(0))
        offset = match.end()
    return tuple(result)


def _identifier(value: str, label: str) -> bytes:
    if not isinstance(value, str) or re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*", value
    ) is None:
        raise ClosureError(f"{label} is not one C identifier")
    return value.encode("ascii")


def _subsequence_count(
    values: tuple[bytes, ...], expected: tuple[bytes, ...]
) -> int:
    if not expected or len(expected) > len(values):
        return 0
    return sum(
        values[index : index + len(expected)] == expected
        for index in range(len(values) - len(expected) + 1)
    )


def _call_names(values: tuple[bytes, ...]) -> tuple[bytes, ...]:
    noncalls = {b"if", b"sizeof", b"_Alignof", b"typeof", b"__typeof__"}
    return tuple(
        values[index]
        for index in range(len(values) - 1)
        if re.fullmatch(rb"[A-Za-z_][A-Za-z0-9_]*", values[index])
        and values[index] not in noncalls
        and values[index + 1] == b"("
    )


def audit_pair_publication_adjacency(
    runtime: bytes,
    *,
    helper_name: str,
    first_publish_expression: bytes,
    terminal_publish_expression: bytes,
) -> dict[str, Any]:
    """Require one canonical A-success-to-terminal-B publication helper.

    The first publication failure returns without attempting B. On the only
    path that reaches B, no call, abort, park, or publication can execute
    between A's return and B's invocation.
    """

    helper = _identifier(helper_name, "pair helper name")
    first_tokens = _c_tokens(
        first_publish_expression, "first publication expression"
    )
    terminal_tokens = _c_tokens(
        terminal_publish_expression, "terminal publication expression"
    )
    first_calls = _call_names(first_tokens)
    terminal_calls = _call_names(terminal_tokens)
    if (
        not first_tokens
        or not terminal_tokens
        or len(first_calls) != 1
        or len(terminal_calls) != 1
        or first_tokens[:2] != (first_calls[0], b"(")
        or terminal_tokens[:2] != (terminal_calls[0], b"(")
        or first_tokens.count(b"first_detail") != 1
        or b"terminal_detail" in first_tokens
        or terminal_tokens.count(b"terminal_detail") != 1
        or b"first_detail" in terminal_tokens
        or first_tokens[-1] == b";"
        or terminal_tokens[-1] == b";"
    ):
        raise ClosureError("pair publication expressions are not canonical")

    expected = (
        helper
        + b"(\n"
        b"    uint16_t first_detail, uint16_t terminal_detail) {\n"
        b"    long first_rc = "
        + first_publish_expression.strip()
        + b";\n"
        b"    if (first_rc != 0) {\n"
        b"        return first_rc;\n"
        b"    }\n"
        b"    return "
        + terminal_publish_expression.strip()
        + b";\n"
        b"}\n"
    )
    try:
        actual = p288_source._c_function_body(  # noqa: SLF001
            runtime, helper_name
        )
    except p288_source.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc
    actual_tokens = _c_tokens(actual, "pair helper body")
    expected_tokens = _c_tokens(expected, "expected pair helper body")
    if actual_tokens != expected_tokens:
        raise ClosureError("pair publication adjacency helper body differs")

    runtime_tokens = _c_tokens(runtime, "pair runtime source")
    helper_references = sum(
        runtime_tokens[index : index + 2] == (helper, b"(")
        for index in range(len(runtime_tokens) - 1)
    )
    if helper_references != 2:
        raise ClosureError(
            "pair helper must have one definition and one runtime call"
        )
    if (
        _subsequence_count(runtime_tokens, first_tokens) != 1
        or _subsequence_count(runtime_tokens, terminal_tokens) != 1
    ):
        raise ClosureError("pair publication route is not unique")

    return {
        "verdict": PAIR_ADJACENCY_VERDICT,
        "helper": helper_name,
        "first_publication_count": 1,
        "terminal_publication_count": 1,
        "runtime_call_count": 1,
        "calls_between_first_return_and_terminal_invocation": 0,
        "first_failure_returns_without_terminal_attempt": True,
        "abort_or_park_between_publications": False,
        "verified": True,
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": _sha256(data)}


def _added_source(patch: bytes, begin: bytes, end: bytes) -> bytes:
    if patch.count(begin) != 1 or patch.count(end) != 1:
        raise ClosureError("materialized patch extraction marker differs")
    start = patch.index(begin)
    finish = patch.index(end, start)
    lines = patch[start:finish].splitlines(keepends=True)
    if not lines or any(not line.startswith(b"+") for line in lines):
        raise ClosureError("materialized patch span is not wholly added source")
    return b"".join(line[1:] for line in lines)


def _kernel_production_source(patch: bytes) -> bytes:
    source = _added_source(
        patch,
        b"+#define S22_FYG8_E1_LOG_BASE",
        b"+static const struct proc_ops s22_fyg8_e1_ops",
    )
    parse_start = b"static bool s22_fyg8_e1_parse_reg("
    parse_end = b"static int s22_fyg8_e1_hex_nibble("
    if source.count(parse_start) != 1 or source.count(parse_end) != 1:
        raise ClosureError("materialized OF-only writer span differs")
    start = source.index(parse_start)
    finish = source.index(parse_end, start)
    host_head = b"""static struct s22_fyg8_e1_log_head *s22_fyg8_e1_head(void)
{
	return (struct s22_fyg8_e1_log_head *)p292_log_storage.bytes;
}

"""
    source = source[:start] + host_head + source[finish:]
    required = (
        b"struct s22_fyg8_e1_slot active;",
        b"memcpy(&s22_fyg8_e1_state.active, &record.slots[0],",
        b"memcmp(&record->slots[s22_fyg8_e1_state.active_slot],",
        b"&s22_fyg8_e1_state.active,",
        b"memcpy(&s22_fyg8_e1_state.active, &next,",
        b"static ssize_t s22_fyg8_e1_write(",
    )
    if any(source.count(token) < 1 for token in required):
        raise ClosureError("repaired materialized writer source is incomplete")
    forbidden = (
        b"s22_fyg8_e1_state.generation",
        b"s22_fyg8_e1_state.stage",
        b"s22_fyg8_e1_state.item_index",
        b"s22_fyg8_e1_build_slot(&active",
    )
    if any(token in source for token in forbidden):
        raise ClosureError("repaired writer retains reconstructed active state")
    return source


def _canonical_cases(*, consecutive: bool) -> tuple[tuple[int, int, int, int], ...]:
    values = []
    for ordinal, position in enumerate(positions.POSITIONS):
        terminal = ordinal == len(positions.POSITIONS) - 1
        outcome = model.OUTCOME_SUCCESS if terminal else model.OUTCOME_PROGRESS
        detail = 0
        if not terminal and ordinal == CANONICAL_LIVE_DETAIL_ORDINAL:
            detail = CANONICAL_LIVE_DETAIL
        if not terminal and consecutive and ordinal in CONSECUTIVE_DETAIL_ORDINALS:
            detail = CONSECUTIVE_DETAIL
        values.append(
            (position.stage, position.item_index, outcome, detail)
        )
    return tuple(values)


def _closure_cases() -> tuple[tuple[int, ...], ...]:
    cases: list[tuple[int, ...]] = []
    first = positions.POSITIONS[0]
    cases.append(
        (
            0,
            0,
            0,
            model.OUTCOME_PROGRESS,
            0,
            first.stage,
            first.item_index,
            model.OUTCOME_PROGRESS,
            0,
        )
    )
    for active_ordinal, active_position in enumerate(
        positions.POSITIONS[:-1]
    ):
        generation = active_ordinal + 1
        next_position = positions.POSITIONS[generation]
        next_terminal = generation == len(positions.POSITIONS) - 1
        next_outcome = (
            model.OUTCOME_SUCCESS
            if next_terminal
            else model.OUTCOME_PROGRESS
        )
        for detail in positions.position_progress_details(
            active_position.stage, active_position.item_index
        ):
            cases.append(
                (
                    generation,
                    active_position.stage,
                    active_position.item_index,
                    model.OUTCOME_PROGRESS,
                    detail,
                    next_position.stage,
                    next_position.item_index,
                    next_outcome,
                    0,
                )
            )
    return tuple(cases)


def _c_walk_array(
    name: str, cases: tuple[tuple[int, int, int, int], ...]
) -> str:
    rows = "".join(
        f"    {{0x{stage:02x}U, 0x{item:02x}U, {outcome}U, "
        f"0x{detail:04x}U}},\n"
        for stage, item, outcome, detail in cases
    )
    return (
        f"static const struct p292_walk_case {name}[] = {{\n"
        f"{rows}}};\n"
    )


def _c_closure_array(cases: tuple[tuple[int, ...], ...]) -> str:
    rows = "".join(
        "    {"
        f"{generation}U, 0x{active_stage:02x}U, "
        f"0x{active_item:02x}U, {active_outcome}U, "
        f"0x{active_detail:04x}U, 0x{next_stage:02x}U, "
        f"0x{next_item:02x}U, {next_outcome}U, "
        f"0x{next_detail:04x}U"
        "},\n"
        for (
            generation,
            active_stage,
            active_item,
            active_outcome,
            active_detail,
            next_stage,
            next_item,
            next_outcome,
            next_detail,
        ) in cases
    )
    return (
        "static const struct p292_closure_case p292_closure_cases[] = {\n"
        f"{rows}}};\n"
    )


def _kernel_host_tu(
    patch: bytes, *, run_id_hex: str, unsat_tag_hex: str
) -> bytes:
    production = _kernel_production_source(patch).decode("ascii")
    canonical = _canonical_cases(consecutive=False)
    consecutive = _canonical_cases(consecutive=True)
    closure = _closure_cases()
    prelude = f"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef uint16_t __le16;
typedef uint32_t __le32;
typedef long long p292_loff_t;

#define loff_t p292_loff_t
#define __packed __attribute__((packed))
#define __user
#define noinline __attribute__((noinline))
#define __used __attribute__((used))
#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
#define READ_ONCE(value) (value)
#define cpu_to_le16(value) ((u16)(value))
#define cpu_to_le32(value) ((u32)(value))
#define le16_to_cpu(value) ((u16)(value))
#define le32_to_cpu(value) ((u32)(value))
#define smp_wmb() do {{ }} while (0)
#define CONFIG_S22PLUS_FYG8_E1_PROFILE 3U
#define CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX "{run_id_hex}"
#define CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX "{unsat_tag_hex}"
#define EPERM 1
#define ENODEV 19
#define EINVAL 22
#define EFAULT 14
#define EKEYREJECTED 129
#define EBADMSG 74
#define ERANGE 34
#define ESTALE 116
#define EALREADY 114

struct file {{ int unused; }};
static union {{
    max_align_t alignment;
    unsigned char bytes[0x200000U];
}} p292_log_storage;
static void *current;

static int task_pid_nr(void *task)
{{
    (void)task;
    return 1;
}}

static int copy_from_user(void *target, const void *source, size_t size)
{{
    memcpy(target, source, size);
    return 0;
}}

static void __flush_dcache_area(void *target, size_t size)
{{
    (void)target;
    (void)size;
}}

static u32 crc32_le(u32 crc, const void *source, size_t size)
{{
    const u8 *bytes = (const u8 *)source;
    size_t index;
    for (index = 0; index < size; ++index) {{
        unsigned int bit;
        crc ^= bytes[index];
        for (bit = 0; bit < 8U; ++bit) {{
            u32 mask = 0U - (crc & 1U);
            crc = (crc >> 1U) ^ (0xedb88320U & mask);
        }}
    }}
    return crc;
}}
"""
    declarations = """
struct p292_walk_case {
    u8 stage;
    u8 item;
    u8 outcome;
    u16 detail;
};

struct p292_closure_case {
    u8 generation;
    u8 active_stage;
    u8 active_item;
    u8 active_outcome;
    u16 active_detail;
    u8 next_stage;
    u8 next_item;
    u8 next_outcome;
    u16 next_detail;
};
"""
    arrays = (
        _c_walk_array("p292_canonical", canonical)
        + _c_walk_array("p292_consecutive", consecutive)
        + _c_closure_array(closure)
    )
    main = f"""
static struct s22_fyg8_e1_log_head *p292_head(void)
{{
    return (struct s22_fyg8_e1_log_head *)p292_log_storage.bytes;
}}

static void p292_reset_log(u32 idx, u32 boot_count)
{{
    struct s22_fyg8_e1_log_head *head;
    memset(&p292_log_storage, 0, sizeof(p292_log_storage));
    head = p292_head();
    head->magic = S22_FYG8_E1_LOG_MAGIC;
    head->idx = idx;
    head->boot_cnt = boot_count;
}}

static void p292_fill_header(u8 header[S22_FYG8_E1_HEADER_SIZE])
{{
    u8 run_id[16];
    memset(header, 0, S22_FYG8_E1_HEADER_SIZE);
    memcpy(header, s22_fyg8_e1_long_family,
           sizeof(s22_fyg8_e1_long_family) - 1);
    header[8] = (S22_FYG8_E1_FORMAT_VERSION << 4) |
        S22_FYG8_E1_PROFILE_E2;
    if (!s22_fyg8_e1_parse_hex(
            CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX, run_id))
        return;
    memcpy(&header[9], run_id, sizeof(run_id));
}}

static void p292_make_request(
    struct s22_fyg8_e1_request *request,
    u8 stage, u8 item, u8 outcome, u16 detail)
{{
    u8 run_id[16];
    memset(request, 0, sizeof(*request));
    memcpy(request->magic, "S22Q", 4);
    request->version = S22_FYG8_E1_REQUEST_VERSION;
    request->profile = S22_FYG8_E1_PROFILE_E2;
    request->stage = stage;
    request->outcome = outcome;
    request->detail = cpu_to_le16(detail);
    request->item_index = item;
    if (!s22_fyg8_e1_parse_hex(
            CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX, run_id))
        return;
    memcpy(request->run_id, run_id, sizeof(run_id));
    request->crc32 = cpu_to_le32(s22_fyg8_e1_crc32(
        request, offsetof(struct s22_fyg8_e1_request, crc32)));
}}

static long p292_write_request(const struct p292_walk_case *test)
{{
    struct s22_fyg8_e1_request request;
    p292_loff_t position = 0;
    p292_make_request(
        &request, test->stage, test->item, test->outcome, test->detail);
    return s22_fyg8_e1_write(
        NULL, (const char *)&request, sizeof(request), &position);
}}

static struct s22_fyg8_e1_record *p292_active_record(void)
{{
    struct s22_fyg8_e1_log_head *head = p292_head();
    return (struct s22_fyg8_e1_record *)
        &head->buf[s22_fyg8_e1_state.proof_pos];
}}

static int p292_install_active(
    u8 generation, u8 stage, u8 item, u8 outcome, u16 detail)
{{
    struct s22_fyg8_e1_log_head *head;
    struct s22_fyg8_e1_record *record;
    u8 slot_id = generation & 1U;
    p292_reset_log(8192U, 31U);
    memset(&s22_fyg8_e1_state, 0, sizeof(s22_fyg8_e1_state));
    head = p292_head();
    s22_fyg8_e1_state.seed_idx = head->idx;
    s22_fyg8_e1_state.seed_boot_cnt = head->boot_cnt;
    s22_fyg8_e1_state.proof_pos = 1024U;
    record = p292_active_record();
    memset(record, 0, sizeof(*record));
    p292_fill_header(record->header);
    if (!s22_fyg8_e1_build_slot(
            &record->slots[slot_id], slot_id, generation, stage,
            outcome, item, detail, record->header))
        return 0;
    memcpy(s22_fyg8_e1_state.header, record->header,
           sizeof(record->header));
    memcpy(&s22_fyg8_e1_state.active, &record->slots[slot_id],
           sizeof(s22_fyg8_e1_state.active));
    s22_fyg8_e1_state.active_slot = slot_id;
    s22_fyg8_e1_state.profile = S22_FYG8_E1_PROFILE_E2;
    s22_fyg8_e1_state.ready = true;
    return 1;
}}

static int p292_walk(
    const struct p292_walk_case *cases, size_t count, FILE *trace)
{{
    size_t index;
    struct p292_walk_case extra = {{0x10U, 0U, 0U, 0U}};
    p292_reset_log(4096U, 17U);
    s22_fyg8_e1_record_entry("/init");
    if (!s22_fyg8_e1_state.ready ||
            s22_fyg8_e1_state.active.generation != 0U)
        return 10;
    for (index = 0; index < count; ++index) {{
        struct s22_fyg8_e1_record *record;
        long rc = p292_write_request(&cases[index]);
        if (rc != (long)sizeof(struct s22_fyg8_e1_request))
            return 11;
        if (s22_fyg8_e1_state.active.generation != index + 1U ||
                s22_fyg8_e1_state.active.stage != cases[index].stage ||
                s22_fyg8_e1_state.active.item_index != cases[index].item ||
                s22_fyg8_e1_state.active.outcome != cases[index].outcome ||
                le16_to_cpu(s22_fyg8_e1_state.active.detail) !=
                    cases[index].detail)
            return 12;
        record = p292_active_record();
        if (memcmp(
                &record->slots[s22_fyg8_e1_state.active_slot],
                &s22_fyg8_e1_state.active,
                sizeof(s22_fyg8_e1_state.active)))
            return 13;
        if (fwrite(record, 1, sizeof(*record), trace) != sizeof(*record))
            return 14;
    }}
    if (!s22_fyg8_e1_state.terminal ||
            p292_write_request(&extra) != -EALREADY)
        return 15;
    return 0;
}}

static int p292_test_closure(void)
{{
    size_t index;
    for (index = 0; index < ARRAY_SIZE(p292_closure_cases); ++index) {{
        const struct p292_closure_case *test = &p292_closure_cases[index];
        struct p292_walk_case next = {{
            test->next_stage,
            test->next_item,
            test->next_outcome,
            test->next_detail,
        }};
        if (!p292_install_active(
                test->generation, test->active_stage, test->active_item,
                test->active_outcome, test->active_detail))
            return 20;
        if (p292_write_request(&next) !=
                (long)sizeof(struct s22_fyg8_e1_request))
            return 21;
        if (s22_fyg8_e1_state.active.generation !=
                (u8)(test->generation + 1U))
            return 22;
    }}
    return 0;
}}

static int p292_build_old_record(struct s22_fyg8_e1_record *record)
{{
    memset(record, 0, sizeof(*record));
    p292_fill_header(record->header);
    return s22_fyg8_e1_build_slot(
               &record->slots[1], 1U, 87U, 0x8eU,
               S22_FYG8_E1_PROGRESS, 0U, 0U, record->header) &&
        s22_fyg8_e1_build_slot(
               &record->slots[0], 0U, 88U, 0x8fU,
               S22_FYG8_E1_PROGRESS, 0U, 0xc18U, record->header);
}}

static int p292_test_legacy_resume(void)
{{
    struct s22_fyg8_e1_log_head *head;
    struct s22_fyg8_e1_record *record;
    struct p292_walk_case next = {{0x8fU, 1U, 0U, 0U}};
    p292_reset_log(8192U, 41U);
    memset(&s22_fyg8_e1_state, 0, sizeof(s22_fyg8_e1_state));
    head = p292_head();
    s22_fyg8_e1_state.seed_idx = head->idx;
    s22_fyg8_e1_state.seed_boot_cnt = head->boot_cnt;
    s22_fyg8_e1_state.proof_pos = 2048U;
    record = p292_active_record();
    if (!p292_build_old_record(record))
        return 30;
    memcpy(s22_fyg8_e1_state.header, record->header,
           sizeof(record->header));
    memcpy(&s22_fyg8_e1_state.active, &record->slots[0],
           sizeof(s22_fyg8_e1_state.active));
    s22_fyg8_e1_state.active_slot = 0U;
    s22_fyg8_e1_state.profile = S22_FYG8_E1_PROFILE_E2;
    s22_fyg8_e1_state.ready = true;
    if (p292_write_request(&next) !=
            (long)sizeof(struct s22_fyg8_e1_request))
        return 31;
    if (s22_fyg8_e1_state.active.generation != 89U ||
            s22_fyg8_e1_state.active.stage != 0x8fU ||
            s22_fyg8_e1_state.active.item_index != 1U)
        return 32;
    return 0;
}}

static int p292_test_seed_with_old_record(void)
{{
    struct s22_fyg8_e1_log_head *head;
    struct s22_fyg8_e1_record old_record;
    struct p292_walk_case first = {{0x10U, 0U, 0U, 0U}};
    const size_t old_offset = 512U;
    p292_reset_log(4096U, 53U);
    head = p292_head();
    if (!p292_build_old_record(&old_record))
        return 40;
    memcpy(&head->buf[old_offset], &old_record, sizeof(old_record));
    s22_fyg8_e1_record_entry("/init");
    if (!s22_fyg8_e1_state.ready ||
            s22_fyg8_e1_state.active.generation != 0U)
        return 41;
    if (memcmp(&head->buf[old_offset], &old_record, sizeof(old_record)))
        return 42;
    if (p292_write_request(&first) !=
            (long)sizeof(struct s22_fyg8_e1_request) ||
            s22_fyg8_e1_state.active.generation != 1U)
        return 43;
    return 0;
}}

static int p292_test_corruption(void)
{{
    unsigned int kind;
    for (kind = 0; kind < 2U; ++kind) {{
        struct s22_fyg8_e1_record *record;
        struct s22_fyg8_e1_record before;
        struct s22_fyg8_e1_state state_before;
        struct p292_walk_case next = {{0x8fU, 1U, 0U, 0U}};
        if (!p292_install_active(
                88U, 0x8fU, 0U, S22_FYG8_E1_PROGRESS, 0xc18U))
            return 50;
        record = p292_active_record();
        if (kind == 0U)
            ((u8 *)&record->slots[0].detail)[0] ^= 1U;
        else
            ((u8 *)&record->slots[0].commit_crc)[0] ^= 1U;
        memcpy(&before, record, sizeof(before));
        memcpy(&state_before, &s22_fyg8_e1_state, sizeof(state_before));
        if (p292_write_request(&next) != -ESTALE)
            return 51;
        if (memcmp(&before, record, sizeof(before)) ||
                memcmp(&state_before, &s22_fyg8_e1_state,
                       sizeof(state_before)))
            return 52;
    }}
    return 0;
}}

static int p292_test_publication_failures(void)
{{
    static const u16 details[] = {{0x4002U, 0x5074U, 0x6009U}};
    size_t index;
    for (index = 0; index < ARRAY_SIZE(details); ++index) {{
        struct p292_walk_case failure = {{
            0x10U, 0U, S22_FYG8_E1_FAILURE, details[index]
        }};
        if (!p292_install_active(
                0U, 0U, 0U, S22_FYG8_E1_PROGRESS, 0U))
            return 60;
        if (p292_write_request(&failure) !=
                (long)sizeof(struct s22_fyg8_e1_request))
            return 61;
        if (!s22_fyg8_e1_state.terminal ||
                le16_to_cpu(s22_fyg8_e1_state.active.detail) !=
                    details[index])
            return 62;
    }}
    return 0;
}}

int main(int argc, char **argv)
{{
    FILE *trace;
    int rc;
    if (argc != 2)
        return 2;
    trace = fopen(argv[1], "wb");
    if (trace == NULL)
        return 3;
    rc = p292_walk(
        p292_canonical, ARRAY_SIZE(p292_canonical), trace);
    if (!rc)
        rc = p292_walk(
            p292_consecutive, ARRAY_SIZE(p292_consecutive), trace);
    if (fclose(trace) != 0 && !rc)
        rc = 4;
    if (!rc)
        rc = p292_test_closure();
    if (!rc)
        rc = p292_test_legacy_resume();
    if (!rc)
        rc = p292_test_seed_with_old_record();
    if (!rc)
        rc = p292_test_corruption();
    if (!rc)
        rc = p292_test_publication_failures();
    if (rc)
        return rc;
    printf(
        "walks=2 positions={len(positions.POSITIONS)} "
        "closure={len(closure)} legacy=1 seed=1 corruption=2 "
        "publication=3\\n");
    return 0;
}}
"""
    return (
        prelude + production + declarations + arrays + main
    ).encode("ascii")


def _client_host_source(client: bytes) -> bytes:
    start_marker = b"static inline long syscall6("
    end_marker = b"static void copy_bytes("
    if client.count(start_marker) != 1 or client.count(end_marker) != 1:
        raise ClosureError("materialized client syscall span differs")
    start = client.index(start_marker)
    finish = client.index(end_marker, start)
    host_syscalls = b"""static long p292_open_result = 3;
static long p292_write_result = 32;
static long p292_close_result;
static uint8_t p292_captured_request[32];
static size_t p292_captured_size;

static long sys_openat(const char *path, int flags) {
    (void)path;
    (void)flags;
    return p292_open_result;
}

static long sys_write(int fd, const void *buffer, size_t count) {
    (void)fd;
    if (count == sizeof(p292_captured_request)) {
        for (size_t index = 0; index < count; ++index) {
            p292_captured_request[index] =
                ((const uint8_t *)buffer)[index];
        }
        p292_captured_size = count;
    }
    return p292_write_result;
}

static long sys_close(int fd) {
    (void)fd;
    return p292_close_result;
}

"""
    return client[:start] + host_syscalls + client[finish:]


def _client_host_tu(
    client: bytes,
    canonical: tuple[tuple[int, int, int, int], ...],
    *,
    run_id_hex: str,
) -> bytes:
    source = _client_host_source(client).decode("ascii")
    arrays = _c_walk_array("p292_client_cases", canonical)
    main = f"""
static void p292_reset_syscalls(void)
{{
    p292_open_result = 3;
    p292_write_result = 32;
    p292_close_result = 0;
    p292_captured_size = 0;
    for (size_t index = 0; index < sizeof(p292_captured_request); ++index)
        p292_captured_request[index] = 0;
}}

static int p292_test_error(
    long open_result, long write_result, long close_result,
    uint8_t expected_operation, long expected_error, uint16_t expected_detail)
{{
    struct s22_r4w1e_checkpoint_client client;
    uint8_t run_id[16] = {{
        {", ".join(f"0x{value:02x}" for value in bytes.fromhex(run_id_hex))}
    }};
    uint8_t operation = 0;
    long error = 0;
    long rc;
    if (s22_r4w1e_checkpoint_client_init(&client, run_id) != 0)
        return 20;
    p292_reset_syscalls();
    p292_open_result = open_result;
    p292_write_result = write_result;
    p292_close_result = close_result;
    rc = s22_p290_checkpoint_progress_position(&client, 0U, 0U);
    if (rc != expected_error || client.generation != 0U)
        return 21;
    if (s22_p292_checkpoint_last_publication_error(
            &client, &operation, &error) != 0 ||
            operation != expected_operation || error != expected_error)
        return 22;
    p292_reset_syscalls();
    if (s22_p292_checkpoint_publication_failure_next(
            &client, operation, error) != 0)
        return 23;
    if (p292_captured_size != 32U ||
            p292_captured_request[7] != S22_P233_OUTCOME_FAILURE ||
            (uint16_t)(p292_captured_request[8] |
                ((uint16_t)p292_captured_request[9] << 8)) !=
                expected_detail ||
            !client.terminal)
        return 24;
    return 0;
}}

int main(int argc, char **argv)
{{
    struct s22_r4w1e_checkpoint_client client;
    uint8_t run_id[16] = {{
        {", ".join(f"0x{value:02x}" for value in bytes.fromhex(run_id_hex))}
    }};
    FILE *trace;
    size_t index;
    int rc;
    if (argc != 2)
        return 2;
    trace = fopen(argv[1], "wb");
    if (trace == NULL)
        return 3;
    if (s22_r4w1e_checkpoint_client_init(&client, run_id) != 0)
        return 4;
    for (index = 0; index < ARRAY_SIZE(p292_client_cases); ++index) {{
        const struct p292_walk_case *test = &p292_client_cases[index];
        p292_reset_syscalls();
        rc = test->outcome == S22_P233_OUTCOME_SUCCESS
            ? (int)s22_r4w1e_checkpoint_success(&client)
            : (int)s22_p290_checkpoint_progress_position(
                &client, (uint8_t)index, test->detail);
        if (rc != 0 || p292_captured_size != 32U ||
                p292_captured_request[6] != test->stage ||
                p292_captured_request[7] != test->outcome ||
                p292_captured_request[10] != test->item)
            return 5;
        if ((uint16_t)(p292_captured_request[8] |
                ((uint16_t)p292_captured_request[9] << 8)) !=
                test->detail)
            return 6;
        if (fwrite(p292_captured_request, 1, 32, trace) != 32U)
            return 7;
    }}
    if (fclose(trace) != 0)
        return 8;
    rc = p292_test_error(
        -2, 32, 0, S22_P292_PUBLICATION_OPERATION_OPEN, -2, 0x4002U);
    if (!rc)
        rc = p292_test_error(
            3, -116, 0, S22_P292_PUBLICATION_OPERATION_WRITE,
            -116, 0x5074U);
    if (!rc)
        rc = p292_test_error(
            3, 31, 0, S22_P292_PUBLICATION_OPERATION_WRITE,
            -EIO, 0x5005U);
    if (!rc)
        rc = p292_test_error(
            3, 32, -9, S22_P292_PUBLICATION_OPERATION_CLOSE,
            -9, 0x6009U);
    if (rc)
        return rc;
    printf("client_positions={len(canonical)} errno_cases=4\\n");
    return 0;
}}
"""
    prefix = "#define S22PLUS_FYG8_P233_PROFILE 3\n"
    prelude = """
#include <stdio.h>
#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
struct p292_walk_case {
    uint8_t stage;
    uint8_t item;
    uint8_t outcome;
    uint16_t detail;
};
"""
    return (prefix + source + prelude + arrays + main).encode("ascii")


def _runtime_wrapper_source(wrapper: bytes) -> bytes:
    begin = b"struct p292_checkpoint_errno_evidence {\n"
    end = b"\n\n#include \"s22plus_fyg8_p286_e3_plan.h\""
    if wrapper.count(begin) != 1 or wrapper.count(end) != 1:
        raise ClosureError("materialized errno wrapper span differs")
    start = wrapper.index(begin)
    finish = wrapper.index(end, start)
    source = wrapper[start:finish]
    required = (
        b"g_p292_checkpoint_errno_evidence.valid = 1U;",
        b"p292_checkpoint_channel_failure_sink(",
        b"p292_park_after_checkpoint_error(",
    )
    if any(source.count(token) < 1 for token in required):
        raise ClosureError("materialized errno wrapper is incomplete")
    return source


def _errno_wrapper_tu(wrapper: bytes) -> bytes:
    source = _runtime_wrapper_source(wrapper).decode("ascii")
    prelude = """
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define S22_P292_PUBLICATION_OPERATION_NONE 0U
#define S22_P292_PUBLICATION_OPERATION_OPEN 1U
#define S22_P292_PUBLICATION_OPERATION_WRITE 2U
#define S22_P292_PUBLICATION_OPERATION_CLOSE 3U

struct s22_r4w1e_checkpoint_client {
    uint8_t initialized;
    uint8_t generation;
};
static struct s22_r4w1e_checkpoint_client g_checkpoint;
static jmp_buf p292_park_jump;
static long p292_inspect_rc;
static uint8_t p292_inspect_operation;
static long p292_inspect_errno;
static long p292_fallback_rc;
static long p292_unclassified_rc;

static __attribute__((noreturn)) void p288_raw_quiet_park(void) {
    longjmp(p292_park_jump, 1);
}

static long s22_p292_checkpoint_last_publication_error(
    const struct s22_r4w1e_checkpoint_client *client,
    uint8_t *operation, long *error) {
    (void)client;
    if (p292_inspect_rc == 0) {
        *operation = p292_inspect_operation;
        *error = p292_inspect_errno;
    }
    return p292_inspect_rc;
}

static long s22_p292_checkpoint_publication_failure_next(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t operation, long error) {
    (void)client;
    (void)operation;
    (void)error;
    return p292_fallback_rc;
}

static long s22_p290_checkpoint_unclassified_next(
    struct s22_r4w1e_checkpoint_client *client) {
    (void)client;
    return p292_unclassified_rc;
}

static long s22_p290_checkpoint_failure_next(
    struct s22_r4w1e_checkpoint_client *client, long error) {
    (void)client;
    (void)error;
    return p292_fallback_rc;
}

static long s22_r4w1e_checkpoint_failure(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage, uint8_t item, long error) {
    (void)client;
    (void)stage;
    (void)item;
    (void)error;
    return p292_fallback_rc;
}
"""
    main = """
static int p292_total_failure_case(void) {
    memset(&g_p292_checkpoint_errno_evidence, 0,
           sizeof(g_p292_checkpoint_errno_evidence));
    p292_inspect_rc = 0;
    p292_inspect_operation = S22_P292_PUBLICATION_OPERATION_WRITE;
    p292_inspect_errno = -116;
    p292_fallback_rc = -116;
    if (setjmp(p292_park_jump) == 0)
        p292_park_after_checkpoint_error(-116);
    if (!g_p292_checkpoint_errno_evidence.valid ||
            g_p292_checkpoint_errno_evidence.triggering_rc != -116 ||
            g_p292_checkpoint_errno_evidence.publication_operation !=
                S22_P292_PUBLICATION_OPERATION_WRITE ||
            g_p292_checkpoint_errno_evidence.publication_errno != -116 ||
            g_p292_checkpoint_errno_evidence.fallback_rc != -116)
        return 10;
    return 0;
}

static int p292_fallback_success_case(void) {
    memset(&g_p292_checkpoint_errno_evidence, 0,
           sizeof(g_p292_checkpoint_errno_evidence));
    p292_inspect_rc = 0;
    p292_inspect_operation = S22_P292_PUBLICATION_OPERATION_CLOSE;
    p292_inspect_errno = -9;
    p292_fallback_rc = 0;
    if (setjmp(p292_park_jump) == 0)
        p292_park_after_checkpoint_error(-9);
    return g_p292_checkpoint_errno_evidence.valid ? 11 : 0;
}

static int p292_unclassified_total_failure_case(void) {
    memset(&g_p292_checkpoint_errno_evidence, 0,
           sizeof(g_p292_checkpoint_errno_evidence));
    p292_inspect_rc = -22;
    p292_unclassified_rc = -5;
    if (setjmp(p292_park_jump) == 0)
        p292_park_after_checkpoint_error(-22);
    if (!g_p292_checkpoint_errno_evidence.valid ||
            g_p292_checkpoint_errno_evidence.triggering_rc != -22 ||
            g_p292_checkpoint_errno_evidence.fallback_rc != -5)
        return 12;
    return 0;
}

int main(void) {
    (void)&quiet_park;
    (void)&fail_at;
    int rc = p292_total_failure_case();
    if (!rc)
        rc = p292_fallback_success_case();
    if (!rc)
        rc = p292_unclassified_total_failure_case();
    if (rc)
        return rc;
    printf("wrapper_total_failure=2 wrapper_fallback_success=1\\n");
    return 0;
}
"""
    return (prelude + source + main).encode("ascii")


def _compile_and_run(
    source: bytes,
    *,
    temporary: Path,
    name: str,
    args: tuple[str, ...] = (),
    include_dir: Path | None = None,
) -> dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    source_path = temporary / f"{name}.c"
    executable = temporary / name
    source_path.write_bytes(source)
    command = [
        compiler,
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fno-strict-aliasing",
    ]
    if include_dir is not None:
        command.extend(["-I", str(include_dir)])
    command.extend([str(source_path), "-o", str(executable)])
    compiled = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if compiled.returncode != 0:
        raise ClosureError(
            f"{name} host compile failed: "
            f"{compiled.stderr.decode('utf-8', 'replace')}"
        )
    executed = subprocess.run(
        [str(executable), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if executed.returncode != 0:
        raise ClosureError(
            f"{name} host execution failed rc={executed.returncode}: "
            f"{executed.stderr.decode('utf-8', 'replace')}"
        )
    return {
        "compiler": str(Path(compiler).resolve()),
        "source": _receipt(source),
        "executable": _receipt(executable.read_bytes()),
        "stdout": executed.stdout.decode("ascii").strip(),
        "stderr_empty": not executed.stderr,
        "verified": True,
    }


def _single_slot_record(
    *,
    run_id: bytes,
    generation: int,
    stage: int,
    item: int,
    outcome: int,
    detail: int,
) -> bytes:
    initialized = model.initialize_record(model.PROFILE, run_id)
    if generation == 0:
        return initialized
    header = initialized[: model.LONG_HEADER_SIZE]
    slot = model._encode_slot(  # noqa: SLF001
        header,
        model.Slot(
            generation & 1,
            generation,
            stage,
            outcome,
            item,
            detail,
        ),
    )
    slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
    slots[generation & 1] = slot
    return header + b"".join(slots)


def _verify_python_closure(run_id: bytes) -> dict[str, Any]:
    checked = 0
    for case in _closure_cases():
        (
            generation,
            active_stage,
            active_item,
            active_outcome,
            active_detail,
            next_stage,
            next_item,
            next_outcome,
            next_detail,
        ) = case
        record = _single_slot_record(
            run_id=run_id,
            generation=generation,
            stage=active_stage,
            item=active_item,
            outcome=active_outcome,
            detail=active_detail,
        )
        decoded = decoder.decode_record(record, expected_run_id=run_id)
        if decoded["active"]["generation"] != generation:
            raise ClosureError("decoder active generation differs")
        request = model.encode_request(
            model.PROFILE,
            next_stage,
            run_id=run_id,
            outcome=next_outcome,
            item_index=next_item,
            detail=next_detail,
        )
        updated = model.apply_request(record, request)
        resumed = decoder.decode_record(updated, expected_run_id=run_id)
        if resumed["active"]["generation"] != generation + 1:
            raise ClosureError("model/decoder resume generation differs")
        checked += 1
    return {
        "nonterminal_state_count": checked,
        "accepted_nonterminal_subset_of_resumable": True,
        "model_and_decoder_bidirectional": True,
        "verified": True,
    }


def _verify_trace(
    trace: bytes, *, run_id: bytes
) -> dict[str, Any]:
    expected_size = TRACE_RECORD_COUNT * model.LONG_RECORD_SIZE
    if len(trace) != expected_size:
        raise ClosureError("kernel sequence trace size differs")
    chunks = tuple(
        trace[index : index + model.LONG_RECORD_SIZE]
        for index in range(0, len(trace), model.LONG_RECORD_SIZE)
    )
    offset = 0
    for cases in (
        _canonical_cases(consecutive=False),
        _canonical_cases(consecutive=True),
    ):
        record = model.initialize_record(model.PROFILE, run_id)
        for ordinal, (stage, item, outcome, detail) in enumerate(cases):
            request = model.encode_request(
                model.PROFILE,
                stage,
                run_id=run_id,
                outcome=outcome,
                item_index=item,
                detail=detail,
            )
            record = model.apply_request(record, request)
            if chunks[offset] != record:
                raise ClosureError(
                    f"kernel/model sequence bytes differ at ordinal {ordinal}"
                )
            decoded = decoder.decode_record(
                chunks[offset], expected_run_id=run_id
            )
            active = decoded["active"]
            if (
                active["generation"] != ordinal + 1
                or active["stage"] != stage
                or active["item_index"] != item
                or active["outcome"] != outcome
                or active["detail"] != detail
            ):
                raise ClosureError(
                    f"decoder sequence semantics differ at ordinal {ordinal}"
                )
            offset += 1
    return {
        "walk_count": 2,
        "position_count_per_walk": len(positions.POSITIONS),
        "snapshot_count": len(chunks),
        "kernel_model_byte_identical": True,
        "decoder_exact_at_every_position": True,
        "consecutive_nonzero_detail_ordinals": list(
            CONSECUTIVE_DETAIL_ORDINALS
        ),
        "consecutive_nonzero_detail": CONSECUTIVE_DETAIL,
        "verified": True,
    }


def _verify_client_trace(
    trace: bytes, *, run_id: bytes
) -> dict[str, Any]:
    cases = _canonical_cases(consecutive=False)
    expected = b"".join(
        model.encode_request(
            model.PROFILE,
            stage,
            run_id=run_id,
            outcome=outcome,
            item_index=item,
            detail=detail,
        )
        for stage, item, outcome, detail in cases
    )
    if trace != expected:
        raise ClosureError("client/model request streams differ")
    return {
        "request_count": len(cases),
        "request_size": model.REQUEST_STRUCT.size,
        "client_model_byte_identical": True,
        "verified": True,
    }


def _verify_publication_decoder(run_id: bytes) -> dict[str, Any]:
    cases = (
        (repair.OPERATION_OPEN, -2),
        (repair.OPERATION_WRITE, -116),
        (repair.OPERATION_CLOSE, -9),
    )
    for operation, error in cases:
        detail = repair.encode_publication_error(operation, error)
        record = model.initialize_record(model.PROFILE, run_id)
        first = positions.POSITIONS[0]
        request = model.encode_request(
            model.PROFILE,
            first.stage,
            run_id=run_id,
            outcome=model.OUTCOME_FAILURE,
            item_index=first.item_index,
            detail=detail,
        )
        record = model.apply_request(record, request)
        decoded = decoder.decode_record(record, expected_run_id=run_id)
        publication = decoded["active_semantics"]["publication_error"]
        if publication is None or (
            publication["operation"],
            publication["errno"],
        ) != (operation, error):
            raise ClosureError("decoder publication errno differs")
    return {
        "decoded_publication_error_cases": len(cases),
        "operation_and_exact_errno_preserved": True,
        "verified": True,
    }


def _write_headers(
    directory: Path, artifacts: dict[str, bytes]
) -> None:
    for key in ("p290_checkpoint_header", "p290_position_header"):
        relative = generator.artifact_paths()[key]
        target = directory / Path(relative).name
        target.write_bytes(artifacts[key])


def run_closure(
    root: Path,
    *,
    mutate: ArtifactMutator | None = None,
) -> dict[str, Any]:
    manifest = zero.load_manifest()
    authority = zero.verify_authority(root, manifest)
    run_id = bytes.fromhex(authority["run_id"])
    artifacts = generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=bytes.fromhex(authority["unsat_tag_hex"]),
        profile=authority["profile"],
    )
    if mutate is not None:
        artifacts = mutate(dict(artifacts))
    if set(artifacts) != set(generator.artifact_paths()):
        raise ClosureError("closure artifact inventory differs")
    patch = artifacts["candidate_patch"]
    client = artifacts["checkpoint_client"]
    wrapper = artifacts["runtime_wrapper"]
    runtime = artifacts["p290_e3_runtime_include"]
    descriptor_header = artifacts["trace_descriptor_header"]
    kernel_tu = _kernel_host_tu(
        patch,
        run_id_hex=authority["run_id"],
        unsat_tag_hex=authority["unsat_tag_hex"],
    )
    client_tu = _client_host_tu(
        client,
        _canonical_cases(consecutive=False),
        run_id_hex=authority["run_id"],
    )
    wrapper_tu = _errno_wrapper_tu(wrapper)

    with tempfile.TemporaryDirectory(
        prefix="s22-p292-accept-resume-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        kernel_trace_path = temporary / "kernel.trace"
        kernel_result = _compile_and_run(
            kernel_tu,
            temporary=temporary,
            name="kernel-writer",
            args=(str(kernel_trace_path),),
        )
        kernel_trace = kernel_trace_path.read_bytes()

        include_dir = temporary / "include"
        include_dir.mkdir()
        _write_headers(include_dir, artifacts)
        client_trace_path = temporary / "client.trace"
        client_result = _compile_and_run(
            client_tu,
            temporary=temporary,
            name="checkpoint-client",
            args=(str(client_trace_path),),
            include_dir=include_dir,
        )
        client_trace = client_trace_path.read_bytes()
        wrapper_result = _compile_and_run(
            wrapper_tu,
            temporary=temporary,
            name="errno-wrapper",
        )

    python_closure = _verify_python_closure(run_id)
    sequence_walk = _verify_trace(kernel_trace, run_id=run_id)
    client_coherence = _verify_client_trace(client_trace, run_id=run_id)
    decoder_errno = _verify_publication_decoder(run_id)
    if CONSECUTIVE_DETAIL not in set(
        positions.position_progress_details(
            positions.POSITIONS[CONSECUTIVE_DETAIL_ORDINALS[0]].stage,
            positions.POSITIONS[CONSECUTIVE_DETAIL_ORDINALS[0]].item_index,
        )
    ).intersection(
        positions.position_progress_details(
            positions.POSITIONS[CONSECUTIVE_DETAIL_ORDINALS[1]].stage,
            positions.POSITIONS[CONSECUTIVE_DETAIL_ORDINALS[1]].item_index,
        )
    ):
        raise ClosureError("consecutive nonzero detail is not SoT-derived")
    descriptor = repair.descriptor()
    if (
        tuple(
            (row["stage"], row["item_index"])
            for row in descriptor["positions"]
        )
        != positions.POSITION_SEQUENCE
        or descriptor["active_state"]["representation"]
        != repair.ACTIVE_STATE_REPRESENTATION
    ):
        raise ClosureError("repair SoT and position sequence differ")
    producer_tokens = (
        b"#define P282_DETAIL_CYCLE_TRACE_CONTROL_UNAVAILABLE 0xc01U",
        b"#define P282_DETAIL_CYCLE_TRACE_CONTROL_UNAVAILABLE_OUTCOME 0U",
        b"#define P282_DETAIL_CYCLE_TRACE_CONTROL_UNAVAILABLE_STAGE_MASK 0x0eU",
    )
    if any(descriptor_header.count(token) != 1 for token in producer_tokens):
        raise ClosureError("consecutive detail descriptor route differs")
    stop_route = (
        b"p282_publish_classification(\n"
        b"        P282_STAGE_STOP,\n"
        b"        classified,\n"
        b"        &classification,\n"
        b"        p282_cycle_warning_detail(cycle, P282_STAGE_STOP));"
    )
    suspended_route = (
        b"p282_publish_classification(\n"
        b"        P282_STAGE_SUSPENDED,\n"
        b"        classified,\n"
        b"        &classification,\n"
        b"        p282_cycle_warning_detail(cycle, P282_STAGE_SUSPENDED));"
    )
    if runtime.count(stop_route) != 1 or runtime.count(suspended_route) != 1:
        raise ClosureError("consecutive detail runtime producer route differs")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority": {
            "intent_sha256": authority["intent_sha256"],
            "run_id": authority["run_id"],
            "repair_sot_sha256": repair.descriptor_sha256(),
            "candidate_patch": _receipt(patch),
        },
        "accept_to_resume_closure": {
            "kernel": kernel_result,
            "model_decoder": python_closure,
            "closure_case_count": len(_closure_cases()),
            "accepted_nonterminal_subset_of_resumable": True,
            "corruption_cases": 2,
            "pre_mutation_estale_on_corruption": True,
            "verified": True,
        },
        "accept_to_resume_sequence_walk": sequence_walk,
        "checkpoint_errno_observability": {
            "client": client_result,
            "runtime_wrapper": wrapper_result,
            "decoder": decoder_errno,
            "fallback_success_is_durable_failure_request": True,
            "total_channel_failure_reaches_volatile_sink_before_park": True,
            "verified": True,
        },
        "checkpoint_sot_coherence": {
            "kernel_writer_source": _receipt(
                _kernel_production_source(patch)
            ),
            "client_request_stream": client_coherence,
            "repair_model_schema": model.SCHEMA,
            "repair_decoder_schema": decoder.SCHEMA,
            "position_sequence_shared": True,
            "detail_semantics_shared": True,
            "consecutive_nonzero_detail_runtime_producer_derived": True,
            "exact_active_slot_shared": True,
            "verified": True,
        },
        "legacy_seed_and_prefix": {
            "retained_p290_gen87_gen88_seed_present": True,
            "new_seed_then_generation_one_committed": True,
            "exact_old_generation_88_resumed_to_89": True,
            "stable_live_prefix_generation": 88,
            "stable_live_prefix_stage": 0x8F,
            "stable_live_prefix_outcome": model.OUTCOME_PROGRESS,
            "stable_live_prefix_item_index": 0,
            "stable_live_prefix_detail": CANONICAL_LIVE_DETAIL,
            "detail_zero_prefix_regression": False,
            "verified": True,
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
        raise ClosureError("closure result output already exists")
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
                raise ClosureError("short closure result write")
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
        result = run_closure(root)
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
        ClosureError,
        generator.RepairGeneratorError,
        repair.RepairSpecError,
        OSError,
        subprocess.TimeoutExpired,
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
                "closure_case_count": result[
                    "accept_to_resume_closure"
                ]["closure_case_count"],
                "sequence_walk_snapshots": result[
                    "accept_to_resume_sequence_walk"
                ]["snapshot_count"],
                "errno_observable": result[
                    "checkpoint_errno_observability"
                ]["verified"],
                "legacy_gen88_resumed": result[
                    "legacy_seed_and_prefix"
                ]["exact_old_generation_88_resumed_to_89"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
