#!/usr/bin/env python3
"""Transform the fixed P3.00 userspace into the P3.01 subtype observer."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p300_telemetry_transform as inherited
import s22plus_fyg8_p301_telemetry_spec as spec


base = inherited.base


class TelemetryTransformError(ValueError):
    pass


P301_BIND_RESULT_STRUCT = inherited.P300_BIND_RESULT_STRUCT.replace(
    b"    uint8_t other_device_seen;\n",
    b"    uint8_t other_device_seen;\n"
    b"    uint8_t other_type_mask;\n"
    b"    uint8_t first_other_info;\n"
    b"    uint8_t first_other_info_seen;\n"
    b"    uint8_t unknown_subtype_seen;\n",
).replace(
    b"    uint64_t device_records;\n",
    b"    uint64_t device_records;\n"
    b"    uint64_t other_device_records;\n",
)


P301_DETAIL_DEFINES = b"""#define P301_SUBTYPE_DETAIL_BASE 0x4001U
#define P301_SUBTYPE_DETAIL_MAX 0x4fc0U
#define P301_UNKNOWN_SUBTYPE_DETAIL 0x4fc1U
#define P301_FINAL_DRIFT_DETAIL_BASE 0x5001U
#define P301_FINAL_DRIFT_DETAIL_MAX 0x5084U
#define P301_DETAIL_SUBTYPE_EMPTY_MASK 0x6001U
#define P301_DETAIL_SUBTYPE_EMPTY_COUNT 0x6002U
#define P301_DETAIL_SUBTYPE_INFO_MISSING 0x6003U
#define P301_DETAIL_SUBTYPE_MASK_RANGE 0x6004U
#define P301_DETAIL_FINAL_MISMATCH_BASE 0x6005U
#define P301_DETAIL_STATE_SPEED_CONTRADICTION 0x600cU
#define P301_DETAIL_CONNECT_SPEED_CONTRADICTION 0x600dU
#define P301_DETAIL_TERMINAL_DOMAIN_CONTRADICTION 0x600eU
#define P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION 0x600fU
#define P301_EXPECTED_FINAL_DETAIL 0xe06U
#define P301_KNOWN_OTHER_MASK_MAX 0x3fU

"""


P301_OTHER_EVENT_CAPTURE = b"""    } else {
        if (result->other_device_records == UINT64_MAX) {
            return P300_DETAIL_RAW_EVENT_CONTRADICTION;
        }
        if (result->other_device_records == 0U) {
            result->first_other_info =
                (uint8_t)((record->raw >> 16U) & 0xfU);
            result->first_other_info_seen = 1U;
        }
        ++result->other_device_records;
        result->other_device_seen = 1U;
        switch ((unsigned int)record->type) {
        case 0U: result->other_type_mask |= 1U << 0U; break;
        case 4U: result->other_type_mask |= 1U << 1U; break;
        case 6U: result->other_type_mask |= 1U << 2U; break;
        case 9U: result->other_type_mask |= 1U << 3U; break;
        case 10U: result->other_type_mask |= 1U << 4U; break;
        case 11U: result->other_type_mask |= 1U << 5U; break;
        default: result->unknown_subtype_seen = 1U; break;
        }
    }
"""


P301_FINAL_HELPERS = b"""_Static_assert(
    S22_P294_POSITION_USBLNKST == 105U,
    "P3.01 A must remain ordinal 105");
_Static_assert(
    S22_P294_POSITION_FINAL_STATE == 106U,
    "P3.01 B must remain ordinal 106");

static unsigned int p301_count_bucket(uint64_t count) {
    if (count == 1U) return 0U;
    if (count <= 3U) return 1U;
    if (count <= 7U) return 2U;
    return 3U;
}

static int p301_terminal_detail_allowed(uint16_t detail) {
    return (detail >= P301_SUBTYPE_DETAIL_BASE
            && detail <= P301_SUBTYPE_DETAIL_MAX)
        || detail == P301_UNKNOWN_SUBTYPE_DETAIL
        || (detail >= P301_FINAL_DRIFT_DETAIL_BASE
            && detail <= P301_FINAL_DRIFT_DETAIL_MAX)
        || (detail >= P301_DETAIL_SUBTYPE_EMPTY_MASK
            && detail <= P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION);
}

static long p301_terminal_detail(
    const struct p282_bind_trace_result *result,
    unsigned int ingress_class,
    uint16_t legacy_detail,
    uint16_t *detail) {
    if (result == 0 || detail == 0 || ingress_class > 10U) {
        return -P260_EPROTO;
    }
    if (legacy_detail >= P294_FINAL_DETAIL_BASE
        && legacy_detail < P294_FINAL_DETAIL_BASE + 132U) {
        unsigned int state_index =
            (unsigned int)(legacy_detail - P294_FINAL_DETAIL_BASE);
        if (ingress_class != 7U
            || legacy_detail != P301_EXPECTED_FINAL_DETAIL) {
            *detail = (uint16_t)(
                P301_FINAL_DRIFT_DETAIL_BASE + state_index);
            return 0;
        }
        if (result->unknown_subtype_seen) {
            *detail = P301_UNKNOWN_SUBTYPE_DETAIL;
            return 0;
        }
        if (result->other_type_mask == 0U) {
            *detail = P301_DETAIL_SUBTYPE_EMPTY_MASK;
            return 0;
        }
        if (result->other_type_mask > P301_KNOWN_OTHER_MASK_MAX) {
            *detail = P301_DETAIL_SUBTYPE_MASK_RANGE;
            return 0;
        }
        if (result->other_device_records == 0U) {
            *detail = P301_DETAIL_SUBTYPE_EMPTY_COUNT;
            return 0;
        }
        if (!result->first_other_info_seen
            || result->first_other_info > 0xfU) {
            *detail = P301_DETAIL_SUBTYPE_INFO_MISSING;
            return 0;
        }
        unsigned int bucket =
            p301_count_bucket(result->other_device_records);
        unsigned int index = (
            ((unsigned int)result->other_type_mask - 1U) * 16U
            + (unsigned int)result->first_other_info) * 4U
            + bucket;
        unsigned int encoded = P301_SUBTYPE_DETAIL_BASE + index;
        if (encoded > P301_SUBTYPE_DETAIL_MAX) {
            *detail = P301_DETAIL_SUBTYPE_MASK_RANGE;
            return 0;
        }
        *detail = (uint16_t)encoded;
        return 0;
    }
    if (legacy_detail >= P294_MISMATCH_DETAIL_BASE
        && legacy_detail < P294_MISMATCH_DETAIL_BASE + 7U) {
        *detail = (uint16_t)(
            P301_DETAIL_FINAL_MISMATCH_BASE
            + legacy_detail - P294_MISMATCH_DETAIL_BASE);
        return 0;
    }
    if (legacy_detail == P294_STATE_SPEED_CONTRADICTION) {
        *detail = P301_DETAIL_STATE_SPEED_CONTRADICTION;
        return 0;
    }
    if (legacy_detail == P294_CONNECT_SPEED_CONTRADICTION) {
        *detail = P301_DETAIL_CONNECT_SPEED_CONTRADICTION;
        return 0;
    }
    *detail = P301_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
    return 0;
}

"""


P301_PUBLISH_FINAL_PAIR = b"""static long p294_publish_final_pair(
    uint16_t first_detail, uint16_t terminal_detail) {
    if (g_checkpoint.generation != 105U || g_checkpoint.terminal
        || first_detail < P294_LINK_DETAIL_BASE
        || first_detail >= P294_LINK_DETAIL_BASE + 176U) {
        return -P260_EPROTO;
    }
    long first_rc = s22_p294_checkpoint_progress_position(
        &g_checkpoint, S22_P294_POSITION_USBLNKST, first_detail);
    if (first_rc != 0) {
        return first_rc;
    }
    if (g_checkpoint.generation != 106U || g_checkpoint.terminal
        || !p301_terminal_detail_allowed(terminal_detail)) {
        return -P260_EPROTO;
    }
    long terminal_rc = s22_p294_checkpoint_terminal_position(
        &g_checkpoint, S22_P294_POSITION_FINAL_STATE, terminal_detail);
    if (terminal_rc == 0
        && (g_checkpoint.generation != 107U || !g_checkpoint.terminal)) {
        return -P260_EPROTO;
    }
    return terminal_rc;
}
"""


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        inherited.P300_BIND_RESULT_STRUCT,
        P301_BIND_RESULT_STRUCT,
        label="P3.01 subtype result fields",
    )
    value = base.replace_exact(
        value,
        b"#define P300_IRQ_RETURN_MAXACTIVE 32U\n",
        b"#define P300_IRQ_RETURN_MAXACTIVE 32U\n" + P301_DETAIL_DEFINES,
        label="P3.01 terminal detail definitions",
    )
    value = base.replace_exact(
        value,
        b"    } else {\n"
        b"        result->other_device_seen = 1U;\n"
        b"    }\n",
        P301_OTHER_EVENT_CAPTURE,
        label="P3.01 raw other-device subtype capture",
    )
    anchor = b"static long p294_publish_final_pair(\n"
    if value.count(anchor) != 1:
        raise TelemetryTransformError("P3.01 final-pair anchor differs")
    value = value.replace(anchor, P301_FINAL_HELPERS + anchor, 1)
    value = base.replace_function(
        value,
        b"p294_publish_final_pair",
        P301_PUBLISH_FINAL_PAIR,
    )
    value = base.replace_exact(
        value,
        b"            rc = p294_publish_final_pair(first_detail, terminal_detail);\n",
        b"            uint16_t p301_detail = 0;\n"
        b"            rc = p301_terminal_detail(\n"
        b"                &final_result, (unsigned int)ingress_class,\n"
        b"                terminal_detail, &p301_detail);\n"
        b"            if (rc != 0) {\n"
        b"                p290_fail_next(\n"
        b"                    P301_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);\n"
        b"            }\n"
        b"            rc = p294_publish_final_pair(first_detail, p301_detail);\n",
        label="P3.01 terminal B selection",
    )
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    return result
