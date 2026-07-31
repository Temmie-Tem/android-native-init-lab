#!/usr/bin/env python3
"""Apply the attributed P2.92 exact-slot and errno repair."""

from __future__ import annotations

from typing import Callable

import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p292_repair_spec as spec


class RepairTransformError(ValueError):
    pass


def replace_exact(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    count: int = 1,
    label: str,
) -> bytes:
    actual = data.count(old)
    if actual != count:
        raise RepairTransformError(
            f"{label} replacement count {actual}, expected {count}"
        )
    return data.replace(old, new)


def _transform_patch_state(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"+struct s22_fyg8_e1_state {\n"
        b"+\tbool ready;\n"
        b"+\tbool terminal;\n"
        b"+\tu8 active_slot;\n"
        b"+\tu8 profile;\n"
        b"+\tu8 generation;\n"
        b"+\tu8 stage;\n"
        b"+\tu8 item_index;\n"
        b"+\tu32 seed_idx;\n"
        b"+\tu32 seed_boot_cnt;\n"
        b"+\tsize_t proof_pos;\n"
        b"+\tu8 header[S22_FYG8_E1_HEADER_SIZE];\n"
        b"+};",
        b"+struct s22_fyg8_e1_state {\n"
        b"+\tbool ready;\n"
        b"+\tbool terminal;\n"
        b"+\tu8 active_slot;\n"
        b"+\tu8 profile;\n"
        b"+\tstruct s22_fyg8_e1_slot active;\n"
        b"+\tu32 seed_idx;\n"
        b"+\tu32 seed_boot_cnt;\n"
        b"+\tsize_t proof_pos;\n"
        b"+\tu8 header[S22_FYG8_E1_HEADER_SIZE];\n"
        b"+};",
        label="kernel exact active-slot state",
    )
    value = replace_exact(
        value,
        b"+\tif (profile != S22_FYG8_E1_PROFILE_E2 || ordinal >= count)\n"
        b"+\t\treturn false;\n"
        b"+\tfor (index = 0;",
        b"+\tif (profile != S22_FYG8_E1_PROFILE_E2 || ordinal >= count)\n"
        b"+\t\treturn false;\n"
        b"+\tif (outcome == S22_FYG8_E1_FAILURE &&\n"
        b"+\t\t\t((detail > 0x4000 && detail <= 0x4fff) ||\n"
        b"+\t\t\t (detail > 0x5000 && detail <= 0x5fff) ||\n"
        b"+\t\t\t (detail > 0x6000 && detail <= 0x6fff)))\n"
        b"+\t\treturn true;\n"
        b"+\tfor (index = 0;",
        label="kernel publication-error detail ranges",
    )
    value = replace_exact(
        value,
        b"+\tsize_t ordinal = s22_fyg8_e1_state.generation;",
        b"+\tsize_t ordinal = s22_fyg8_e1_state.active.generation;",
        label="kernel request generation from exact slot",
    )
    value = replace_exact(
        value,
        b"+\tmemcpy(s22_fyg8_e1_state.header, record.header, "
        b"sizeof(record.header));\n"
        b"+\ts22_fyg8_e1_state.profile = CONFIG_S22PLUS_FYG8_E1_PROFILE;",
        b"+\tmemcpy(s22_fyg8_e1_state.header, record.header, "
        b"sizeof(record.header));\n"
        b"+\tmemcpy(&s22_fyg8_e1_state.active, &record.slots[0],\n"
        b"+\t       sizeof(s22_fyg8_e1_state.active));\n"
        b"+\ts22_fyg8_e1_state.profile = CONFIG_S22PLUS_FYG8_E1_PROFILE;",
        label="kernel seed exact-slot capture",
    )
    value = replace_exact(
        value,
        b"+\tstruct s22_fyg8_e1_record *record;\n"
        b"+\tstruct s22_fyg8_e1_slot active;\n"
        b"+\tstruct s22_fyg8_e1_slot next;",
        b"+\tstruct s22_fyg8_e1_record *record;\n"
        b"+\tstruct s22_fyg8_e1_slot next;",
        label="kernel reconstructed active local removal",
    )
    value = replace_exact(
        value,
        b"+\tif (memcmp(record->header, s22_fyg8_e1_state.header,\n"
        b"+\t\t   sizeof(record->header)) ||\n"
        b"+\t\t\t!s22_fyg8_e1_build_slot(&active,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.active_slot,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.generation,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.stage,\n"
        b"+\t\t\t\tS22_FYG8_E1_PROGRESS,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.item_index, 0,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.header) ||\n"
        b"+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],\n"
        b"+\t\t\t       &active, sizeof(active)))\n"
        b"+\t\treturn -ESTALE;",
        b"+\tif (memcmp(record->header, s22_fyg8_e1_state.header,\n"
        b"+\t\t   sizeof(record->header)) ||\n"
        b"+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],\n"
        b"+\t\t\t       &s22_fyg8_e1_state.active,\n"
        b"+\t\t\t       sizeof(s22_fyg8_e1_state.active)))\n"
        b"+\t\treturn -ESTALE;",
        label="kernel exact active-slot precondition",
    )
    value = replace_exact(
        value,
        b"+\t\t\ts22_fyg8_e1_state.generation + 1U,",
        b"+\t\t\ts22_fyg8_e1_state.active.generation + 1U,",
        label="kernel successor generation from exact slot",
    )
    value = replace_exact(
        value,
        b"+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],\n"
        b"+\t\t\t       &active, sizeof(active)))",
        b"+\t\t\tmemcmp(&record->slots[s22_fyg8_e1_state.active_slot],\n"
        b"+\t\t\t       &s22_fyg8_e1_state.active,\n"
        b"+\t\t\t       sizeof(s22_fyg8_e1_state.active)))",
        label="kernel exact active-slot midcommit guard",
    )
    value = replace_exact(
        value,
        b"+\ts22_fyg8_e1_state.active_slot = next_slot;\n"
        b"+\ts22_fyg8_e1_state.generation++;\n"
        b"+\ts22_fyg8_e1_state.stage = request.stage;\n"
        b"+\ts22_fyg8_e1_state.item_index = request.item_index;\n"
        b"+\ts22_fyg8_e1_state.terminal =",
        b"+\ts22_fyg8_e1_state.active_slot = next_slot;\n"
        b"+\tmemcpy(&s22_fyg8_e1_state.active, &next,\n"
        b"+\t       sizeof(s22_fyg8_e1_state.active));\n"
        b"+\ts22_fyg8_e1_state.terminal =",
        label="kernel exact active-slot postcommit update",
    )
    return value


def transform_patch(data: bytes) -> bytes:
    value = _transform_patch_state(data)
    forbidden = (
        b"s22_fyg8_e1_state.generation",
        b"s22_fyg8_e1_state.stage",
        b"s22_fyg8_e1_state.item_index",
        b"s22_fyg8_e1_build_slot(&active",
    )
    if any(token in value for token in forbidden):
        raise RepairTransformError("kernel reconstructed active state remains")
    return p252._recount_kernel_patch_hunks(value)  # noqa: SLF001


def transform_checkpoint_header(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"#include \"s22plus_fyg8_p290_positions.h\"\n",
        b"#include \"s22plus_fyg8_p290_positions.h\"\n\n"
        b"#define S22_P292_PUBLICATION_OPERATION_NONE 0U\n"
        b"#define S22_P292_PUBLICATION_OPERATION_OPEN 1U\n"
        b"#define S22_P292_PUBLICATION_OPERATION_WRITE 2U\n"
        b"#define S22_P292_PUBLICATION_OPERATION_CLOSE 3U\n"
        b"#define S22_P292_PUBLICATION_ERRNO_MAX 0xfffL\n"
        b"#define S22_P292_PUBLICATION_OPEN_BASE 0x4000U\n"
        b"#define S22_P292_PUBLICATION_WRITE_BASE 0x5000U\n"
        b"#define S22_P292_PUBLICATION_CLOSE_BASE 0x6000U\n",
        label="client publication-error constants",
    )
    value = replace_exact(
        value,
        b"    uint8_t initialized;\n"
        b"    uint8_t terminal;\n"
        b"};",
        b"    uint8_t initialized;\n"
        b"    uint8_t terminal;\n"
        b"    uint8_t publication_error_operation;\n"
        b"    long publication_error_errno;\n"
        b"};",
        label="client publication-error state",
    )
    value = replace_exact(
        value,
        b"long s22_p290_checkpoint_unclassified_next(\n"
        b"    struct s22_r4w1e_checkpoint_client *client);\n",
        b"long s22_p290_checkpoint_unclassified_next(\n"
        b"    struct s22_r4w1e_checkpoint_client *client);\n"
        b"long s22_p292_checkpoint_last_publication_error(\n"
        b"    const struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t *operation,\n"
        b"    long *error);\n"
        b"long s22_p292_checkpoint_publication_failure_next(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t operation,\n"
        b"    long error);\n",
        label="client publication-error API",
    )
    return value


def _publication_error_helpers() -> bytes:
    return b"""static long p292_remember_publication_error(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t operation,
    long error) {
    if (client == NULL ||
        operation < S22_P292_PUBLICATION_OPERATION_OPEN ||
        operation > S22_P292_PUBLICATION_OPERATION_CLOSE ||
        error >= 0 || error < -S22_P292_PUBLICATION_ERRNO_MAX) {
        return -EINVAL;
    }
    client->publication_error_operation = operation;
    client->publication_error_errno = error;
    return error;
}

static long p292_publication_error_detail(
    uint8_t operation, long error, uint16_t *detail) {
    uint16_t base;
    if (detail == NULL || error >= 0 ||
        error < -S22_P292_PUBLICATION_ERRNO_MAX) {
        return -EINVAL;
    }
    if (operation == S22_P292_PUBLICATION_OPERATION_OPEN) {
        base = S22_P292_PUBLICATION_OPEN_BASE;
    } else if (operation == S22_P292_PUBLICATION_OPERATION_WRITE) {
        base = S22_P292_PUBLICATION_WRITE_BASE;
    } else if (operation == S22_P292_PUBLICATION_OPERATION_CLOSE) {
        base = S22_P292_PUBLICATION_CLOSE_BASE;
    } else {
        return -EINVAL;
    }
    *detail = (uint16_t)(base + (uint16_t)(-error));
    return 0;
}

"""


def transform_checkpoint(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"static int p288_detail_allowed(\n",
        _publication_error_helpers() + b"static int p288_detail_allowed(\n",
        label="client publication-error helpers",
    )
    value = replace_exact(
        value,
        b"    if (ordinal >= sizeof(k_p248_e2_steps) /\n"
        b"            sizeof(k_p248_e2_steps[0])) {\n"
        b"        return 0;\n"
        b"    }\n"
        b"    for (size_t index = 0;",
        b"    if (ordinal >= sizeof(k_p248_e2_steps) /\n"
        b"            sizeof(k_p248_e2_steps[0])) {\n"
        b"        return 0;\n"
        b"    }\n"
        b"    if (outcome == S22_P233_OUTCOME_FAILURE &&\n"
        b"        ((detail > S22_P292_PUBLICATION_OPEN_BASE &&\n"
        b"          detail <= S22_P292_PUBLICATION_OPEN_BASE +\n"
        b"              S22_P292_PUBLICATION_ERRNO_MAX) ||\n"
        b"         (detail > S22_P292_PUBLICATION_WRITE_BASE &&\n"
        b"          detail <= S22_P292_PUBLICATION_WRITE_BASE +\n"
        b"              S22_P292_PUBLICATION_ERRNO_MAX) ||\n"
        b"         (detail > S22_P292_PUBLICATION_CLOSE_BASE &&\n"
        b"          detail <= S22_P292_PUBLICATION_CLOSE_BASE +\n"
        b"              S22_P292_PUBLICATION_ERRNO_MAX))) {\n"
        b"        return 1;\n"
        b"    }\n"
        b"    for (size_t index = 0;",
        label="client publication-error detail ranges",
    )
    value = replace_exact(
        value,
        b"    long fd = sys_openat(\"/proc/s22_checkpoint\", "
        b"O_WRONLY | O_CLOEXEC);\n"
        b"    if (fd < 0) {\n"
        b"        return fd;\n"
        b"    }\n"
        b"    long written = sys_write((int)fd, &request, sizeof(request));\n"
        b"    long closed = sys_close((int)fd);\n"
        b"    if (written != (long)sizeof(request)) {\n"
        b"        return written < 0 ? written : -EIO;\n"
        b"    }\n"
        b"    if (closed != 0) {\n"
        b"        return closed;\n"
        b"    }\n"
        b"    client->stage = step->stage;",
        b"    long fd = sys_openat(\"/proc/s22_checkpoint\", "
        b"O_WRONLY | O_CLOEXEC);\n"
        b"    if (fd < 0) {\n"
        b"        return p292_remember_publication_error(\n"
        b"            client, S22_P292_PUBLICATION_OPERATION_OPEN, fd);\n"
        b"    }\n"
        b"    long written = sys_write((int)fd, &request, sizeof(request));\n"
        b"    long closed = sys_close((int)fd);\n"
        b"    if (written != (long)sizeof(request)) {\n"
        b"        long error = written < 0 ? written : -EIO;\n"
        b"        return p292_remember_publication_error(\n"
        b"            client, S22_P292_PUBLICATION_OPERATION_WRITE, error);\n"
        b"    }\n"
        b"    if (closed != 0) {\n"
        b"        return p292_remember_publication_error(\n"
        b"            client, S22_P292_PUBLICATION_OPERATION_CLOSE, closed);\n"
        b"    }\n"
        b"    client->publication_error_operation =\n"
        b"        S22_P292_PUBLICATION_OPERATION_NONE;\n"
        b"    client->publication_error_errno = 0;\n"
        b"    client->stage = step->stage;",
        label="client exact syscall errno preservation",
    )
    value = replace_exact(
        value,
        b"    client->terminal = 0U;\n"
        b"    return 0;\n"
        b"}\n\n"
        b"long s22_r4w1e_checkpoint_progress(",
        b"    client->terminal = 0U;\n"
        b"    client->publication_error_operation =\n"
        b"        S22_P292_PUBLICATION_OPERATION_NONE;\n"
        b"    client->publication_error_errno = 0;\n"
        b"    return 0;\n"
        b"}\n\n"
        b"long s22_r4w1e_checkpoint_progress(",
        label="client publication-error initialization",
    )
    value += b"""
long s22_p292_checkpoint_last_publication_error(
    const struct s22_r4w1e_checkpoint_client *client,
    uint8_t *operation,
    long *error) {
    if (client == NULL || operation == NULL || error == NULL ||
        client->publication_error_operation <
            S22_P292_PUBLICATION_OPERATION_OPEN ||
        client->publication_error_operation >
            S22_P292_PUBLICATION_OPERATION_CLOSE ||
        client->publication_error_errno >= 0 ||
        client->publication_error_errno < -S22_P292_PUBLICATION_ERRNO_MAX) {
        return -EINVAL;
    }
    *operation = client->publication_error_operation;
    *error = client->publication_error_errno;
    return 0;
}

long s22_p292_checkpoint_publication_failure_next(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t operation,
    long error) {
    uint16_t detail = 0;
    long rc = p292_publication_error_detail(operation, error, &detail);
    return rc == 0
        ? p288_publish_next(
            client, S22_P233_OUTCOME_FAILURE, detail, 0, 0U)
        : rc;
}
"""
    return value


P292_WRAPPER_PARK = b"""struct p292_checkpoint_errno_evidence {
    volatile long triggering_rc;
    volatile long publication_errno;
    volatile long fallback_rc;
    volatile uint8_t publication_operation;
    volatile uint8_t valid;
};

static struct p292_checkpoint_errno_evidence
g_p292_checkpoint_errno_evidence __attribute__((used));

static __attribute__((noreturn))
void p290_park_after_confirmed_publication(void) {
    p288_raw_quiet_park();
}

static __attribute__((noreturn))
void p292_checkpoint_channel_failure_sink(
    long triggering_rc,
    uint8_t publication_operation,
    long publication_errno,
    long fallback_rc) {
    g_p292_checkpoint_errno_evidence.triggering_rc = triggering_rc;
    g_p292_checkpoint_errno_evidence.publication_operation =
        publication_operation;
    g_p292_checkpoint_errno_evidence.publication_errno =
        publication_errno;
    g_p292_checkpoint_errno_evidence.fallback_rc = fallback_rc;
    g_p292_checkpoint_errno_evidence.valid = 1U;
    __asm__ volatile("" ::: "memory");
    p288_raw_quiet_park();
}

static __attribute__((noreturn))
void p292_park_after_checkpoint_error(long triggering_rc) {
    uint8_t operation = S22_P292_PUBLICATION_OPERATION_NONE;
    long error = 0;
    long inspect_rc = s22_p292_checkpoint_last_publication_error(
        &g_checkpoint, &operation, &error);
    long fallback_rc = inspect_rc == 0
        ? s22_p292_checkpoint_publication_failure_next(
            &g_checkpoint, operation, error)
        : s22_p290_checkpoint_unclassified_next(&g_checkpoint);
    if (fallback_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    p292_checkpoint_channel_failure_sink(
        triggering_rc, operation, error, fallback_rc);
}

__attribute__((noreturn)) static void quiet_park(void) {
    long fallback_rc =
        s22_p290_checkpoint_unclassified_next(&g_checkpoint);
    if (fallback_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    uint8_t operation = S22_P292_PUBLICATION_OPERATION_NONE;
    long error = 0;
    (void)s22_p292_checkpoint_last_publication_error(
        &g_checkpoint, &operation, &error);
    p292_checkpoint_channel_failure_sink(
        0, operation, error, fallback_rc);
}

__attribute__((noreturn)) static void fail_at(
    uint8_t stage, uint8_t item_index, long operation_error) {
    long primary_rc = g_checkpoint.initialized &&
            g_checkpoint.generation >= 88U
        ? s22_p290_checkpoint_failure_next(
            &g_checkpoint, operation_error)
        : s22_r4w1e_checkpoint_failure(
            &g_checkpoint, stage, item_index, operation_error);
    if (primary_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    p292_park_after_checkpoint_error(primary_rc);
}

"""


def transform_runtime_wrapper(data: bytes) -> bytes:
    old_start = data.index(
        b"static __attribute__((noreturn))\n"
        b"void p290_park_after_confirmed_publication(void) {"
    )
    old_end = data.index(
        b"\n\n#include \"s22plus_fyg8_p286_e3_plan.h\"", old_start
    )
    old = data[old_start:old_end] + b"\n\n"
    return replace_exact(
        data,
        old,
        P292_WRAPPER_PARK,
        label="runtime errno-observable park wrappers",
    )


def transform_runtime_include(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"    if (rc != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"}\n\n"
        b"static void p290_progress_position(",
        b"    if (rc != 0) {\n"
        b"        p292_park_after_checkpoint_error(rc);\n"
        b"    }\n"
        b"}\n\n"
        b"static void p290_progress_position(",
        label="legacy progress errno route",
    )
    value = replace_exact(
        value,
        b"    if (rc != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"}\n\n"
        b"static __attribute__((noreturn)) void p290_fail_next(",
        b"    if (rc != 0) {\n"
        b"        p292_park_after_checkpoint_error(rc);\n"
        b"    }\n"
        b"}\n\n"
        b"static __attribute__((noreturn)) void p290_fail_next(",
        label="position progress errno route",
    )
    value = replace_exact(
        value,
        b"    if (primary_rc == 0) {\n"
        b"        p290_park_after_confirmed_publication();\n"
        b"    }\n"
        b"    quiet_park();\n"
        b"}\n\n"
        b"static long p282_role_trace_detail(",
        b"    if (primary_rc == 0) {\n"
        b"        p290_park_after_confirmed_publication();\n"
        b"    }\n"
        b"    p292_park_after_checkpoint_error(primary_rc);\n"
        b"}\n\n"
        b"static long p282_role_trace_detail(",
        label="failure-next errno route",
    )
    return value


TRANSFORMS: dict[str, Callable[[bytes], bytes]] = {
    "candidate_patch": transform_patch,
    "checkpoint_client": transform_checkpoint,
    "runtime_wrapper": transform_runtime_wrapper,
    "p290_e3_runtime_include": transform_runtime_include,
    "p290_checkpoint_header": transform_checkpoint_header,
}


def transform_artifacts(artifacts: dict[str, bytes]) -> dict[str, bytes]:
    if not spec.REPAIR_ARTIFACT_KEYS <= artifacts.keys():
        raise RepairTransformError("repair artifact inventory is incomplete")
    result = dict(artifacts)
    for key, transform in TRANSFORMS.items():
        result[key] = transform(result[key])
    changed = {key for key in result if result[key] != artifacts[key]}
    if changed != spec.REPAIR_ARTIFACT_KEYS:
        raise RepairTransformError(
            f"repair changed unexpected artifacts: {sorted(changed)}"
        )
    return result
