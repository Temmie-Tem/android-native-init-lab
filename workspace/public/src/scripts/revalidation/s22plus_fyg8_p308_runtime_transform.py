#!/usr/bin/env python3
"""Repair P3.07 kmsg attribution without changing its Image or probes."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p307_runtime_transform as parent


base = parent.base


class TransformError(ValueError):
    pass


_PARSER_STATE = br'''
#define P308_SUMMARY_DETAIL_MAX 0x4febU
#define P308_DEGRADED_DETAIL_BASE 0x6100U
#define P308_DEGRADED_DETAIL_MAX 0x673fU
#define P308_FAILURE_SITE_LINE 0U
#define P308_FAILURE_SITE_CSR 1U
#define P308_FAILURE_SITE_DPDM 2U
#define P308_FAILURE_SITE_CLOCK 3U
#define P308_FAILURE_SITE_COUNT 4U
#define P308_PREFIX_INIT (1U << 0U)
#define P308_PREFIX_CSR (1U << 1U)
#define P308_PREFIX_DPDM (1U << 2U)
#define P308_PREFIX_CLOCK (1U << 3U)
#define P308_PREFIX_MASK_MAX 0xfU

_Static_assert(
    P308_SUMMARY_DETAIL_MAX
        == P307_SUMMARY_DETAIL_BASE + 4075U - 1U,
    "P3.08 normal summary extent");
_Static_assert(
    P308_DEGRADED_DETAIL_MAX
        == P308_DEGRADED_DETAIL_BASE
            + P308_FAILURE_SITE_COUNT * (P308_PREFIX_MASK_MAX + 1U)
                * P307_QSCRATCH_STATE_COUNT
            - 1U,
    "P3.08 degraded summary extent");

struct p308_parser_capture {
    uint8_t prefix_mask;
    uint8_t failure_latched;
    uint8_t failure_site;
};

static struct p308_parser_capture g_p308_parser;

static void p308_latch_failure(unsigned int site) {
    if (!g_p308_parser.failure_latched) {
        g_p308_parser.failure_latched = 1U;
        g_p308_parser.failure_site = (uint8_t)site;
    }
}

static long p308_degraded_detail(
    unsigned int qscratch_state, uint16_t *detail) {
    if (detail == NULL || !g_p308_parser.failure_latched
        || g_p308_parser.failure_site >= P308_FAILURE_SITE_COUNT
        || g_p308_parser.prefix_mask > P308_PREFIX_MASK_MAX
        || qscratch_state >= P307_QSCRATCH_STATE_COUNT) {
        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;
    }
    unsigned int witness =
        (unsigned int)g_p308_parser.failure_site
            * (P308_PREFIX_MASK_MAX + 1U)
        + (unsigned int)g_p308_parser.prefix_mask;
    unsigned int index = witness * P307_QSCRATCH_STATE_COUNT
        + qscratch_state;
    unsigned int encoded = P308_DEGRADED_DETAIL_BASE + index;
    if (encoded > P308_DEGRADED_DETAIL_MAX) {
        return P307_DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION;
    }
    *detail = (uint16_t)encoded;
    return 0;
}

'''


_KMSG_OBSERVER = br'''static long p308_kmsg_observe(
    const char *message, size_t length) {
    const char *init = p282_find_bytes(
        message, length, "msm_hsphy_init phy_flags:");
    const char *csr = p282_find_bytes(message, length, "csr:0x");
    const char *csr_tail = p282_find_bytes(
        message, length, " eud is enabled");
    const char *dpdm_prefix = p282_find_bytes(
        message,
        length,
        "msm_hsphy_dpdm_regulator_enable dpdm_enable:");
    const char *clock_prefix = p282_find_bytes(
        message,
        length,
        "msm_hsphy_enable_clocks(): clocks_enabled:");

    if (init != NULL) g_p308_parser.prefix_mask |= P308_PREFIX_INIT;
    if (csr != NULL) g_p308_parser.prefix_mask |= P308_PREFIX_CSR;
    if (dpdm_prefix != NULL) g_p308_parser.prefix_mask |= P308_PREFIX_DPDM;
    if (clock_prefix != NULL) g_p308_parser.prefix_mask |= P308_PREFIX_CLOCK;

    int line_failed = 0;
    int csr_line = 0;
    if (csr != NULL || csr_tail != NULL) {
        if (csr == NULL || csr_tail == NULL || csr >= csr_tail) {
            p308_latch_failure(P308_FAILURE_SITE_CSR);
            line_failed = 1;
        } else {
            csr_line = 1;
        }
    }

    uint8_t dpdm = 0;
    long dpdm_rc = p307_parse_binary_after(
        message,
        length,
        "msm_hsphy_dpdm_regulator_enable dpdm_enable:",
        &dpdm,
        NULL);
    if (dpdm_rc < 0 || dpdm_rc >= P307_DETAIL_EUD_CACHE_READ_FAILED) {
        p308_latch_failure(P308_FAILURE_SITE_DPDM);
        line_failed = 1;
    }

    uint8_t clocks_enabled = 0;
    const char *after_clock = NULL;
    long clock_rc = p307_parse_binary_after(
        message,
        length,
        "msm_hsphy_enable_clocks(): clocks_enabled:",
        &clocks_enabled,
        &after_clock);
    uint8_t on = 0;
    if (clock_rc < 0 || clock_rc >= P307_DETAIL_EUD_CACHE_READ_FAILED) {
        p308_latch_failure(P308_FAILURE_SITE_CLOCK);
        line_failed = 1;
    } else if (clock_rc == 1) {
        size_t remaining = (size_t)((message + length) - after_clock);
        long on_rc = p307_parse_binary_after(
            after_clock, remaining, " on:", &on, NULL);
        if (on_rc != 1) {
            p308_latch_failure(P308_FAILURE_SITE_CLOCK);
            line_failed = 1;
        }
    }

    unsigned int kinds = (init != NULL) + (unsigned int)csr_line
        + (unsigned int)(dpdm_rc == 1) + (unsigned int)(clock_rc == 1);
    if (kinds > 1U) {
        p308_latch_failure(P308_FAILURE_SITE_LINE);
        line_failed = 1;
    }
    if (line_failed) return 0;

    if (init != NULL) {
        if (g_p307_attr.init_count < 2U) ++g_p307_attr.init_count;
        return 0;
    }
    if (csr_line) {
        if (g_p307_attr.init_count == 0U
            || (g_p307_attr.init_count == 1U
                && g_p307_attr.first_init_csr)) {
            p308_latch_failure(P308_FAILURE_SITE_CSR);
            return 0;
        }
        if (g_p307_attr.init_count == 1U) {
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
'''


_TERMINAL_GUARD = br'''static int p301_terminal_detail_allowed(uint16_t detail) {
    return (detail >= P307_SUMMARY_DETAIL_BASE
            && detail <= P308_SUMMARY_DETAIL_MAX)
        || (detail >= P301_FINAL_DRIFT_DETAIL_BASE
            && detail <= P301_FINAL_DRIFT_DETAIL_MAX)
        || (detail >= P301_DETAIL_SUBTYPE_EMPTY_MASK
            && detail <= P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION)
        || (detail >= P308_DEGRADED_DETAIL_BASE
            && detail <= P308_DEGRADED_DETAIL_MAX);
}
'''


def transform_runtime_include(data: bytes) -> bytes:
    globals_anchor = (
        b"static struct p307_attribution_capture g_p307_attr;\n"
        b"static struct p307_qscratch_capture g_p307_qscratch;\n"
    )
    value = base.replace_exact(
        data,
        globals_anchor,
        globals_anchor + _PARSER_STATE,
        label="P3.08 parser state",
    )
    value = base.replace_function(
        value, b"p307_kmsg_observe", _KMSG_OBSERVER
    )
    old = (
        b"    const char *message = semicolon + 1;\n"
        b"    size_t message_length = (size_t)(end - message);\n"
        b"    rc = p307_kmsg_observe(message, message_length);\n"
        b"    if (rc != 0) return rc;\n"
    )
    new = (
        b"    const char *message = semicolon + 1;\n"
        b"    size_t message_length = (size_t)(end - message);\n"
        b"    const char *body_end = p282_find_bytes(\n"
        b"        message, message_length, \"\\n\");\n"
        b"    if (body_end == NULL) {\n"
        b"        p308_latch_failure(P308_FAILURE_SITE_LINE);\n"
        b"    } else {\n"
        b"        rc = p308_kmsg_observe(\n"
        b"            message, (size_t)(body_end - message));\n"
        b"        if (rc != 0) return rc;\n"
        b"    }\n"
    )
    value = base.replace_exact(
        value, old, new, label="P3.08 printk extended-record line split"
    )
    value = base.replace_function(
        value, b"p301_terminal_detail_allowed", _TERMINAL_GUARD
    )
    old_final = (
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
    new_final = (
        b"            (void)p303_log_detail;\n"
        b"            uint16_t p303_clock = 0;\n"
        b"            uint16_t p308_first = 0;\n"
        b"            uint16_t p308_terminal = 0;\n"
        b"            rc = p303_clock_detail(&p303_clock);\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p303_kmsg_finish();\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            unsigned int p307_qscratch = p307_qscratch_state();\n"
        b"            if (g_p308_parser.failure_latched) {\n"
        b"                p308_first = p303_clock;\n"
        b"                rc = p308_degraded_detail(\n"
        b"                    p307_qscratch, &p308_terminal);\n"
        b"            } else {\n"
        b"                rc = p307_attribution_detail(&p308_first);\n"
        b"                if (rc == 0) {\n"
        b"                    rc = p307_summary_detail(\n"
        b"                        p303_clock, p307_qscratch,\n"
        b"                        &p308_terminal);\n"
        b"                }\n"
        b"            }\n"
        b"            if (rc != 0) p290_fail_next(rc);\n"
        b"            rc = p294_publish_final_pair(\n"
        b"                p308_first, p308_terminal);\n"
    )
    return base.replace_exact(
        value,
        old_final,
        new_final,
        label="P3.08 normal-or-degraded final publication",
    )


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    return result
