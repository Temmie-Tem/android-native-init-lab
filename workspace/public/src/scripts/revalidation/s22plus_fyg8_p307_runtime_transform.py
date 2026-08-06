#!/usr/bin/env python3
"""Add the P3.07 EUD and QSCRATCH observer to exact P3.05 userspace."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p300_telemetry_transform as inherited
import s22plus_fyg8_p307_telemetry_spec as spec


base = inherited.base


class TransformError(ValueError):
    pass


_QSCRATCH_DESCRIPTOR = (
    b'    {"p307_qscratch", "p:p282/p307_qscratch '
    + spec.DWC3_MODULE_RUNTIME_NAME.encode("ascii")
    + b":"
    + spec.QSCRATCH_SYMBOL.encode("ascii")
    + f'+0x{spec.QSCRATCH_PROBE_OFFSET:x} rc=%w21:s32\\n", '
      '"common_pid >= 0"},\n'.encode("ascii")
)


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_CYCLE_EVENT_COUNT 28U\n",
        b"#define P282_CYCLE_EVENT_COUNT 29U\n",
        label="P3.07 cycle event capacity",
    )
    anchor = b"};\n\nstatic const struct p282_event_descriptor p282_bind_events[]"
    start = value.find(b"static const struct p282_event_descriptor p282_cycle_events[]")
    end = value.find(anchor, start)
    if start < 0 or end < 0 or _QSCRATCH_DESCRIPTOR in value:
        raise TransformError("P3.07 cycle descriptor table differs")
    return value[:end] + _QSCRATCH_DESCRIPTOR + value[end:]


_RESULT_FIELDS = b"""    uint64_t p307_qscratch_hits;
    uint8_t p307_qscratch_vbus_mask;
    uint8_t p307_qscratch_session_mask;
"""


_QSCRATCH_PARSE = b"""    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index != 28U) continue;
        if (!record->has_rc || result->p307_qscratch_hits == UINT64_MAX) {
            return -P260_EPROTO;
        }
        uint32_t raw = (uint32_t)record->rc;
        result->p307_qscratch_vbus_mask |= (uint8_t)(
            1U << ((raw >> 20U) & 1U));
        result->p307_qscratch_session_mask |= (uint8_t)(
            1U << ((raw >> 28U) & 1U));
        ++result->p307_qscratch_hits;
    }

"""


_SUPPORT = br'''
#define P307_EUD_CACHE_PATH "/sys/module/eud/parameters/enable"
#define P307_EUD_MODULE_INDEX 37U
#define P307_QSCRATCH_EVENT_INDEX 28U
#define P307_ATTR_DETAIL_BASE 0xd00U
#define P307_ATTR_INIT_STATES 3U
#define P307_ATTR_DPDM_STATES 5U
#define P307_ATTR_PRECLOCK_STATES 5U
#define P307_SUMMARY_DETAIL_BASE 0x4001U
#define P307_QSCRATCH_STATE_COUNT 25U

#define P307_DETAIL_EUD_CACHE_READ_FAILED 0x6010U
#define P307_DETAIL_EUD_CACHE_FORMAT_CONTRADICTION 0x6011U
#define P307_DETAIL_EUD_CACHE_LIFECYCLE_CONTRADICTION 0x6012U
#define P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION 0x6013U
#define P307_DETAIL_KMSG_ATTRIBUTION_ORDER_CONTRADICTION 0x6014U
#define P307_DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION 0x6015U
#define P307_DETAIL_QSCRATCH_PROFILE_RECORD_MISMATCH 0x6016U
#define P307_DETAIL_QSCRATCH_RECORD_CONTRADICTION 0x6017U
#define P307_DETAIL_QSCRATCH_VALUE_DOMAIN_CONTRADICTION 0x6018U
#define P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION 0x6019U

struct p307_attribution_capture {
    uint8_t cache_attempted;
    uint8_t cache_valid;
    uint8_t cache_value;
    uint8_t init_count;
    uint8_t first_init_csr;
    uint8_t dpdm_state;
    uint8_t preclock_state;
};

struct p307_qscratch_capture {
    uint64_t hits;
    uint8_t vbus_mask;
    uint8_t session_mask;
    uint8_t final;
};

static struct p307_attribution_capture g_p307_attr;
static struct p307_qscratch_capture g_p307_qscratch;

static long p307_read_eud_cache(void) {
    if (g_p307_attr.cache_attempted) {
        return P307_DETAIL_EUD_CACHE_LIFECYCLE_CONTRADICTION;
    }
    g_p307_attr.cache_attempted = 1U;
    long fd = sys_openat(P307_EUD_CACHE_PATH, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) return P307_DETAIL_EUD_CACHE_READ_FAILED;
    char value[4] = {0};
    long amount = sys_read((int)fd, value, sizeof(value));
    long close_rc = sys_close((int)fd);
    if (amount < 0 || close_rc != 0) {
        return P307_DETAIL_EUD_CACHE_READ_FAILED;
    }
    if (amount != 2 || (value[0] != '0' && value[0] != '1')
        || value[1] != '\n') {
        return P307_DETAIL_EUD_CACHE_FORMAT_CONTRADICTION;
    }
    g_p307_attr.cache_value = (uint8_t)(value[0] - '0');
    g_p307_attr.cache_valid = 1U;
    return 0;
}

static long p307_parse_binary_after(
    const char *message,
    size_t length,
    const char *prefix,
    uint8_t *value,
    const char **after) {
    const char *found = p282_find_bytes(message, length, prefix);
    if (found == NULL) return 0;
    size_t prefix_length = cstr_len(prefix);
    const char *cursor = found + prefix_length;
    const char *end = message + length;
    if (cursor >= end || (cursor[0] != '0' && cursor[0] != '1')) {
        return P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION;
    }
    if (cursor + 1 < end && !p282_is_space(cursor[1])) {
        return P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION;
    }
    *value = (uint8_t)(cursor[0] - '0');
    if (after != NULL) *after = cursor + 1;
    return 1;
}

static long p307_kmsg_observe(const char *message, size_t length) {
    const char *init = p282_find_bytes(
        message, length, "msm_hsphy_init phy_flags:");
    const char *csr = p282_find_bytes(message, length, "csr:0x");
    const char *csr_tail = p282_find_bytes(
        message, length, " eud is enabled");
    int csr_line = csr != NULL && csr_tail != NULL && csr < csr_tail;

    uint8_t dpdm = 0;
    long dpdm_rc = p307_parse_binary_after(
        message,
        length,
        "msm_hsphy_dpdm_regulator_enable dpdm_enable:",
        &dpdm,
        NULL);
    if (dpdm_rc < 0 || dpdm_rc >= P307_DETAIL_EUD_CACHE_READ_FAILED) {
        return dpdm_rc;
    }

    uint8_t clocks_enabled = 0;
    const char *after_clock = NULL;
    long clock_rc = p307_parse_binary_after(
        message,
        length,
        "msm_hsphy_enable_clocks(): clocks_enabled:",
        &clocks_enabled,
        &after_clock);
    if (clock_rc < 0 || clock_rc >= P307_DETAIL_EUD_CACHE_READ_FAILED) {
        return clock_rc;
    }
    uint8_t on = 0;
    if (clock_rc == 1) {
        size_t remaining = (size_t)((message + length) - after_clock);
        long on_rc = p307_parse_binary_after(
            after_clock, remaining, " on:", &on, NULL);
        if (on_rc != 1) {
            return on_rc >= P307_DETAIL_EUD_CACHE_READ_FAILED
                ? on_rc : P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION;
        }
    }

    unsigned int kinds = (init != NULL) + (unsigned int)csr_line
        + (unsigned int)(dpdm_rc == 1) + (unsigned int)(clock_rc == 1);
    if (kinds > 1U) {
        return P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION;
    }
    if (init != NULL) {
        if (g_p307_attr.init_count < 2U) ++g_p307_attr.init_count;
        return 0;
    }
    if (csr_line) {
        if (g_p307_attr.init_count == 0U) {
            return P307_DETAIL_KMSG_ATTRIBUTION_ORDER_CONTRADICTION;
        }
        if (g_p307_attr.init_count == 1U) {
            if (g_p307_attr.first_init_csr) {
                return P307_DETAIL_KMSG_ATTRIBUTION_ORDER_CONTRADICTION;
            }
            g_p307_attr.first_init_csr = 1U;
        }
        return 0;
    }
    if (dpdm_rc == 1 && g_p307_attr.dpdm_state == 0U) {
        g_p307_attr.dpdm_state = (uint8_t)(
            g_p307_attr.init_count == 0U ? 1U + dpdm : 3U + dpdm);
    }
    if (clock_rc == 1 && g_p307_attr.init_count == 0U
        && g_p307_attr.preclock_state == 0U) {
        g_p307_attr.preclock_state = (uint8_t)(
            1U + clocks_enabled * 2U + on);
    }
    return 0;
}

static long p307_attribution_detail(uint16_t *detail) {
    if (detail == NULL || !g_p303_kmsg.final
        || !g_p307_attr.cache_attempted || !g_p307_attr.cache_valid) {
        return P307_DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION;
    }
    if (g_p307_attr.init_count > 2U || g_p307_attr.dpdm_state >= 5U
        || g_p307_attr.preclock_state >= 5U) {
        return P307_DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION;
    }
    unsigned int init_state = g_p307_attr.init_count == 0U
        ? 0U : (g_p307_attr.first_init_csr ? 2U : 1U);
    unsigned int index = g_p307_attr.cache_value;
    index = index * P307_ATTR_INIT_STATES + init_state;
    index = index * P307_ATTR_DPDM_STATES + g_p307_attr.dpdm_state;
    index = index * P307_ATTR_PRECLOCK_STATES
        + g_p307_attr.preclock_state;
    if (index >= 150U) {
        return P307_DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION;
    }
    *detail = (uint16_t)(P307_ATTR_DETAIL_BASE + index);
    return 0;
}

static long p307_capture_qscratch(
    const struct p282_trace_control *control,
    const struct p282_cycle_trace_result *result) {
    if (control == NULL || result == NULL || g_p307_qscratch.final) {
        return P307_DETAIL_QSCRATCH_RECORD_CONTRADICTION;
    }
    if (control->event_count != 29U
        || control->profile_hits[P307_QSCRATCH_EVENT_INDEX]
            != result->p307_qscratch_hits) {
        return P307_DETAIL_QSCRATCH_PROFILE_RECORD_MISMATCH;
    }
    if (result->p307_qscratch_vbus_mask > 3U
        || result->p307_qscratch_session_mask > 3U) {
        return P307_DETAIL_QSCRATCH_VALUE_DOMAIN_CONTRADICTION;
    }
    g_p307_qscratch.hits = result->p307_qscratch_hits;
    g_p307_qscratch.vbus_mask = result->p307_qscratch_vbus_mask;
    g_p307_qscratch.session_mask = result->p307_qscratch_session_mask;
    g_p307_qscratch.final = 1U;
    return 0;
}

static unsigned int p307_qscratch_state(void) {
    if (!g_p307_qscratch.final) return UINT32_MAX;
    if (g_p307_qscratch.hits == 0U) {
        return (g_p307_qscratch.vbus_mask == 0U
            && g_p307_qscratch.session_mask == 0U) ? 0U : UINT32_MAX;
    }
    if (g_p307_qscratch.vbus_mask == 0U
        || g_p307_qscratch.session_mask == 0U) return UINT32_MAX;
    unsigned int bucket = g_p307_qscratch.hits == 1U ? 0U
        : (g_p307_qscratch.hits <= 3U ? 1U
            : (g_p307_qscratch.hits <= 7U ? 2U : 3U));
    unsigned int category = 0U;
    if (g_p307_qscratch.vbus_mask == 3U) {
        category = 5U;
    } else if (g_p307_qscratch.vbus_mask == 1U) {
        category = g_p307_qscratch.session_mask == 1U ? 0U : 1U;
    } else if (g_p307_qscratch.session_mask == 1U) {
        category = 2U;
    } else if (g_p307_qscratch.session_mask == 2U) {
        category = 3U;
    } else {
        category = 4U;
    }
    return 1U + bucket * 6U + category;
}

static long p307_summary_detail(
    uint16_t clock_detail, unsigned int qscratch_state, uint16_t *detail) {
    if (detail == NULL
        || clock_detail < P303_CLOCK_DETAIL_BASE
        || clock_detail >= P303_CLOCK_DETAIL_BASE + 163U
        || qscratch_state >= P307_QSCRATCH_STATE_COUNT) {
        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;
    }
    unsigned int index =
        (clock_detail - P303_CLOCK_DETAIL_BASE) * P307_QSCRATCH_STATE_COUNT
        + qscratch_state;
    if (index >= 4075U) {
        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;
    }
    *detail = (uint16_t)(P307_SUMMARY_DETAIL_BASE + index);
    return 0;
}

'''


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"    int32_t p303_clock_rc[12];\n};\n",
        b"    int32_t p303_clock_rc[12];\n" + _RESULT_FIELDS + b"};\n",
        label="P3.07 QSCRATCH cycle result fields",
    )
    anchor = b"    long stop_pid = 0;\n"
    value = base.replace_exact(
        value,
        anchor,
        _QSCRATCH_PARSE + anchor,
        label="P3.07 QSCRATCH trace parsing",
    )
    support_anchor = b"static long p303_kmsg_record("
    if value.count(support_anchor) != 1 or _SUPPORT in value:
        raise TransformError("P3.07 support anchor differs")
    value = value.replace(support_anchor, _SUPPORT + support_anchor, 1)
    value = base.replace_exact(
        value,
        b"    const char *message = semicolon + 1;\n"
        b"    size_t message_length = (size_t)(end - message);\n",
        b"    const char *message = semicolon + 1;\n"
        b"    size_t message_length = (size_t)(end - message);\n"
        b"    rc = p307_kmsg_observe(message, message_length);\n"
        b"    if (rc != 0) return rc;\n",
        label="P3.07 ordered kmsg attribution",
    )
    value = base.replace_exact(
        value,
        b"    long p303_clock_capture_rc = p303_capture_clock(\n"
        b"        &cycle->trace, &final_result);\n"
        b"    if (p303_clock_capture_rc != 0) {\n"
        b"        p290_fail_next(p303_clock_capture_rc);\n"
        b"    }\n",
        b"    long p303_clock_capture_rc = p303_capture_clock(\n"
        b"        &cycle->trace, &final_result);\n"
        b"    if (p303_clock_capture_rc != 0) {\n"
        b"        p290_fail_next(p303_clock_capture_rc);\n"
        b"    }\n"
        b"    long p307_qscratch_capture_rc = p307_capture_qscratch(\n"
        b"        &cycle->trace, &final_result);\n"
        b"    if (p307_qscratch_capture_rc != 0) {\n"
        b"        p290_fail_next(p307_qscratch_capture_rc);\n"
        b"    }\n",
        label="P3.07 final QSCRATCH capture",
    )
    old = (
        b"            uint16_t p303_clock = 0;\n"
        b"            uint16_t p303_log = 0;\n"
        b"            rc = p303_clock_detail(&p303_clock);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_log_detail(&p303_log);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(p303_clock, p303_log);\n"
    )
    new = (
        b"            (void)p303_log_detail;\n"
        b"            uint16_t p303_clock = 0;\n"
        b"            uint16_t p307_attr = 0;\n"
        b"            uint16_t p307_summary = 0;\n"
        b"            rc = p303_clock_detail(&p303_clock);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p307_attribution_detail(&p307_attr);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            unsigned int p307_qscratch = p307_qscratch_state();\n"
        b"            rc = p307_summary_detail(\n"
        b"                p303_clock, p307_qscratch, &p307_summary);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(p307_attr, p307_summary);\n"
    )
    return base.replace_exact(
        value, old, new, label="P3.07 final attribution and summary publication"
    )


def transform_runtime_wrapper(data: bytes) -> bytes:
    old = b"""    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {
        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
    }
"""
    new = b"""    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {
        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
        if (index == P307_EUD_MODULE_INDEX) {
            long p307_eud_cache_rc = p307_read_eud_cache();
            if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);
        }
    }
"""
    return base.replace_exact(
        data, old, new, label="P3.07 EUD cache read after exact module load"
    )


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["trace_descriptor_header"] = transform_trace_descriptor(
        source["trace_descriptor_header"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    result["runtime_wrapper"] = transform_runtime_wrapper(
        source["runtime_wrapper"]
    )
    return result
