#!/usr/bin/env python3
"""Remove P2.94's external-module dependency from materialized telemetry."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p294_telemetry_transform as base
import s22plus_fyg8_p296_telemetry_spec as spec


class TelemetryTransformError(ValueError):
    pass


def _kernel_rule_table() -> bytes:
    rows = b"".join(
        f"+\t{{{ordinal}, {outcome}, 0x{detail:x}}},\n".encode("ascii")
        for ordinal, outcome, detail in spec.exact_detail_rules()
    )
    return (
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n"
        + rows
        + b"+};\n"
    )


def _client_rule_table() -> bytes:
    rows = b"".join(
        f"    {{{ordinal}U, {outcome}U, 0x{detail:x}U}},\n".encode("ascii")
        for ordinal, outcome, detail in spec.exact_detail_rules()
    )
    return (
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n"
        + rows
        + b"};\n"
    )


def transform_checkpoint_client(data: bytes) -> bytes:
    return base._replace_table(  # noqa: SLF001
        data,
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n",
        _client_rule_table(),
        label="P2.96 userspace detail",
    )


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_CYCLE_EVENT_COUNT 17U\n"
        b"#define P282_BIND_EVENT_COUNT 7U\n",
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 7U\n",
        label="P2.96 built-in trace event counts",
    )
    wrapper = (
        b'    {"wrapper_vbus_snapshot", "p:p282/wrapper_vbus_snapshot '
        b'dwc3_msm:s22_p294_wrapper_vbus_snapshot present=%x0:u32 '
        b'vbus=%x1:u32\\n", "common_pid > 0"},\n'
    )
    return base.replace_exact(
        value,
        wrapper,
        b"",
        label="P2.96 external wrapper descriptor removal",
    )


P296_CAPTURE_DECLARATIONS = b"""struct p294_capture_values {
    uint8_t dwc3_seen;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
};

static struct p294_capture_values g_p294_capture;

"""


P296_TERMINAL_DETAIL = b"""static long p294_terminal_detail(
    unsigned int state,
    unsigned int speed,
    uint16_t *detail) {
    unsigned int mismatch = 0;
    if (!g_p294_capture.dwc3_seen) {
        return -P260_EPROTO;
    }
    if (g_p294_capture.run_stop != 1U) mismatch |= 1U;
    if (g_p294_capture.devctrlhlt != 0U) mismatch |= 2U;
    if (g_p294_capture.prtcap != 2U) mismatch |= 4U;
    if (mismatch != 0U) {
        *detail = (uint16_t)(P294_MISMATCH_DETAIL_BASE + mismatch - 1U);
        return 0;
    }
    unsigned int category = 0;
    if (state == 0U) {
        if (speed != 0U) {
            *detail = P294_STATE_SPEED_CONTRADICTION;
            return 0;
        }
    } else {
        if (state >= P282_STATE_COUNT || speed > P282_SPEED_HIGH) {
            *detail = P294_STATE_SPEED_CONTRADICTION;
            return 0;
        }
        category = 1U + (state - 1U) * 4U + speed;
    }
    if (speed != 0U) {
        unsigned int expected = speed == 1U ? 2U : speed == 2U ? 1U : 0U;
        if (g_p294_capture.connect_speed != expected) {
            *detail = P294_CONNECT_SPEED_CONTRADICTION;
            return 0;
        }
    }
    unsigned int index =
        ((category * 2U + g_p294_capture.coreidle) * 2U)
        + g_p294_capture.susphy;
    if (index >= 132U) {
        return -P260_EPROTO;
    }
    *detail = (uint16_t)(P294_FINAL_DETAIL_BASE + index);
    return 0;
}
"""


P294_CYCLE_PARSER_ADDITION = b"""    if (rc == 0 && result->restart_worker.entered) {
        unsigned int matches = 0;
        uint64_t upper = result->restart_worker.returned
            ? result->restart_worker.return_counter : UINT64_MAX;
        for (size_t index = 0; index < count; ++index) {
            const struct p282_trace_record *record = &records[index];
            if (record->event_index != 16U
                || record->pid != restart_pid
                || record->counter <= result->restart_worker.entry_counter
                || record->counter >= upper) {
                continue;
            }
            if (!record->has_present || !record->has_vbus
                || record->present != 1 || record->vbus < 0
                || record->vbus > 1 || matches != 0U) {
                rc = -P260_EPROTO;
                break;
            }
            result->wrapper_seen = 1U;
            result->wrapper_vbus_valid = (uint8_t)record->vbus;
            ++matches;
        }
        if (rc == 0 && matches != 1U) {
            rc = -P260_EPROTO;
        }
    }
    if (rc == 0) {
        rc = p286_outer_state(records, count, result);
    }
"""


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"    uint8_t outer_open;\n"
        b"    uint8_t wrapper_seen;\n"
        b"    uint8_t wrapper_vbus_valid;\n"
        b"};\n\n"
        b"struct p282_bind_trace_result {\n",
        b"    uint8_t outer_open;\n};\n\n"
        b"struct p282_bind_trace_result {\n",
        label="P2.96 wrapper result removal",
    )
    value = base.replace_exact(
        value,
        P294_CYCLE_PARSER_ADDITION,
        b"    if (rc == 0) {\n"
        b"        rc = p286_outer_state(records, count, result);\n"
        b"    }\n",
        label="P2.96 wrapper parser removal",
    )
    value = base.replace_exact(
        value,
        base.CAPTURE_DECLARATIONS,
        P296_CAPTURE_DECLARATIONS,
        label="P2.96 built-in capture state",
    )
    value = base.replace_function(
        value,
        b"p294_terminal_detail",
        P296_TERMINAL_DETAIL,
    )
    value = base.replace_exact(
        value,
        b"    g_p294_capture.wrapper_seen = final_result.wrapper_seen;\n"
        b"    g_p294_capture.vbus_valid = final_result.wrapper_vbus_valid;\n",
        b"",
        label="P2.96 wrapper handoff removal",
    )
    return value


def transform_candidate_patch(data: bytes) -> bytes:
    value = base._replace_table(  # noqa: SLF001
        data,
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n",
        _kernel_rule_table(),
        label="P2.96 kernel detail",
    )
    wrapper_marker = (
        b"diff --git a/kernel_platform/msm-kernel/drivers/usb/dwc3/"
        b"dwc3-msm-core.c "
    )
    if value.count(wrapper_marker) != 1:
        raise TelemetryTransformError(
            "P2.96 external wrapper patch boundary differs"
        )
    value = value[:value.index(wrapper_marker)]
    value = p252._recount_kernel_patch_hunks(value)  # noqa: SLF001
    if not value.endswith(b"\n"):
        raise TelemetryTransformError("P2.96 candidate patch lacks newline")
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["candidate_patch"] = transform_candidate_patch(
        source["candidate_patch"]
    )
    result["checkpoint_client"] = transform_checkpoint_client(
        source["checkpoint_client"]
    )
    result["trace_descriptor_header"] = transform_trace_descriptor(
        source["trace_descriptor_header"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    return result
