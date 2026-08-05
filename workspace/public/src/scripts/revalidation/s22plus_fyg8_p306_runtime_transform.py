#!/usr/bin/env python3
"""Add a passive DWC3 MSM IPC-log observer to exact P3.05 userspace."""

from __future__ import annotations


class TransformError(ValueError):
    pass


P306_SUPPORT = br'''
#define P306_DEBUGFS_MAGIC 0x64626720L
#define P306_IPC_PATH \
    "/sys/kernel/debug/ipc_logging/a600000_ssusb/log"
#define P306_READ_CAPACITY 4096U
#define P306_LINE_CAPACITY 512U
#define P306_CHAIN_DETAIL_BASE 0xd01U
#define P306_SUMMARY_DETAIL_BASE 0x4001U
#define P306_DETAIL_MOUNT_FAILED 0x6001U
#define P306_DETAIL_PATH_UNAVAILABLE 0x6002U
#define P306_DETAIL_READ_FAILED 0x6003U
#define P306_DETAIL_FORMAT_CONTRADICTION 0x6004U
#define P306_DETAIL_CLEANUP_FAILED 0x6005U
#define P306_DETAIL_LIFECYCLE_CONTRADICTION 0x6006U

#define P306_MARKER_MODE_DEVICE (1U << 0)
#define P306_MARKER_QRW_ENABLE (1U << 1)
#define P306_MARKER_QRW_DISABLE (1U << 2)
#define P306_MARKER_BSV_SET (1U << 3)
#define P306_MARKER_INPUTS_BSV (1U << 4)
#define P306_MARKER_START_GADGET (1U << 5)
#define P306_MARKER_PERIPHERAL (1U << 6)

#define P306_CONDITION_BSV_CLEAR (1U << 0)
#define P306_CONDITION_CORE_INIT_FAILED (1U << 1)
#define P306_CONDITION_UNDEFINED_NO_BSV (1U << 2)
#define P306_CONDITION_NO_PULLUP (1U << 3)

static __attribute__((noreturn)) void p290_fail_next(long detail);

struct p306_ipc_state {
    int fd;
    uint8_t started;
    uint8_t mount_owned;
    uint8_t final;
    uint8_t marker_mask;
    uint8_t condition_mask;
    uint8_t ordered_stage;
    uint8_t ordered_complete;
    uint32_t bsv_set_count;
    uint32_t start_gadget_count;
    uint32_t peripheral_count;
    size_t line_length;
    char line[P306_LINE_CAPACITY];
};

static struct p306_ipc_state g_p306_ipc = {.fd = -1};

static void p306_count(uint32_t *value) {
    if (*value != UINT32_MAX) ++*value;
}

static int p306_line_has(
    const char *line, size_t length, const char *needle) {
    return p282_find_bytes(line, length, needle) != NULL;
}

static long p306_parse_qrw(
    const char *line, size_t length, unsigned int *enable) {
    const char *end = line + length;
    const char *cursor = p282_find_bytes(line, length, "Q RW (vbus)");
    if (cursor == NULL) return 0;
    cursor += cstr_len("Q RW (vbus)");
    while (cursor < end && p282_is_space(*cursor)) ++cursor;
    if (cursor == end || (*cursor != '0' && *cursor != '1')) {
        return P306_DETAIL_FORMAT_CONTRADICTION;
    }
    *enable = (unsigned int)(*cursor - '0');
    ++cursor;
    if (cursor < end && !p282_is_space(*cursor)) {
        return P306_DETAIL_FORMAT_CONTRADICTION;
    }
    return 1;
}

static long p306_parse_inputs(
    const char *line, size_t length, uint32_t *inputs) {
    const char *end = line + length;
    const char *cursor = p282_find_bytes(
        line, length, "exit: mdwc->inputs:");
    if (cursor == NULL) return 0;
    cursor += cstr_len("exit: mdwc->inputs:");
    while (cursor < end && p282_is_space(*cursor)) ++cursor;
    const char *value_end = cursor;
    while (value_end < end
        && ((*value_end >= '0' && *value_end <= '9')
            || (*value_end >= 'a' && *value_end <= 'f')
            || (*value_end >= 'A' && *value_end <= 'F'))) {
        ++value_end;
    }
    if (cursor == value_end
        || p303_parse_hex(cursor, value_end, inputs) != 0) {
        return P306_DETAIL_FORMAT_CONTRADICTION;
    }
    return 1;
}

static long p306_process_line(const char *line, size_t length) {
    if (p306_line_has(line, length, "mode_request:device")) {
        g_p306_ipc.marker_mask |= P306_MARKER_MODE_DEVICE;
    }
    unsigned int enable = 0;
    long rc = p306_parse_qrw(line, length, &enable);
    if (rc < 0 || rc >= P306_DETAIL_MOUNT_FAILED) return rc;
    if (rc == 1) {
        g_p306_ipc.marker_mask |= enable
            ? P306_MARKER_QRW_ENABLE : P306_MARKER_QRW_DISABLE;
    }
    if (p306_line_has(line, length, "XCVR: BSV set")) {
        g_p306_ipc.marker_mask |= P306_MARKER_BSV_SET;
        p306_count(&g_p306_ipc.bsv_set_count);
        g_p306_ipc.ordered_stage = 1U;
    }
    if (p306_line_has(line, length, "XCVR: BSV clear")) {
        g_p306_ipc.condition_mask |= P306_CONDITION_BSV_CLEAR;
    }
    uint32_t inputs = 0;
    rc = p306_parse_inputs(line, length, &inputs);
    if (rc < 0 || rc >= P306_DETAIL_MOUNT_FAILED) return rc;
    if (rc == 1 && (inputs & (1U << 1)) != 0U) {
        g_p306_ipc.marker_mask |= P306_MARKER_INPUTS_BSV;
    }
    if (p306_line_has(line, length, "FF StrtGdgt gsync")) {
        g_p306_ipc.marker_mask |= P306_MARKER_START_GADGET;
        p306_count(&g_p306_ipc.start_gadget_count);
        if (g_p306_ipc.ordered_stage >= 1U) {
            g_p306_ipc.ordered_stage = 2U;
        }
    }
    if (p306_line_has(line, length, "FF peripheral")) {
        g_p306_ipc.marker_mask |= P306_MARKER_PERIPHERAL;
        p306_count(&g_p306_ipc.peripheral_count);
        if (g_p306_ipc.ordered_stage >= 2U) {
            g_p306_ipc.ordered_stage = 3U;
            g_p306_ipc.ordered_complete = 1U;
        }
    }
    if (p306_line_has(line, length, "core_init failed")) {
        g_p306_ipc.condition_mask |= P306_CONDITION_CORE_INIT_FAILED;
    }
    if (p306_line_has(line, length, "undef_id_!bsv")) {
        g_p306_ipc.condition_mask |= P306_CONDITION_UNDEFINED_NO_BSV;
    }
    if (p306_line_has(line, length, "No Pullup")) {
        g_p306_ipc.condition_mask |= P306_CONDITION_NO_PULLUP;
    }
    return 0;
}

static long p306_feed(const char *buffer, size_t length) {
    for (size_t index = 0; index < length; ++index) {
        char value = buffer[index];
        if (value == '\n') {
            long rc = p306_process_line(
                g_p306_ipc.line, g_p306_ipc.line_length);
            g_p306_ipc.line_length = 0U;
            if (rc != 0) return rc;
            continue;
        }
        if (g_p306_ipc.line_length + 1U >= P306_LINE_CAPACITY) {
            return P306_DETAIL_FORMAT_CONTRADICTION;
        }
        g_p306_ipc.line[g_p306_ipc.line_length++] = value;
    }
    return 0;
}

static long p306_ipc_drain(void) {
    if (!g_p306_ipc.started) return 0;
    if (g_p306_ipc.fd < 0 || g_p306_ipc.final) {
        return P306_DETAIL_LIFECYCLE_CONTRADICTION;
    }
    char buffer[P306_READ_CAPACITY];
    for (;;) {
        long amount = sys_read(g_p306_ipc.fd, buffer, sizeof(buffer));
        if (amount == 0) return 0;
        if (amount < 0 || amount > (long)sizeof(buffer)) {
            return P306_DETAIL_READ_FAILED;
        }
        long rc = p306_feed(buffer, (size_t)amount);
        if (rc != 0) return rc;
    }
}

static long p306_ipc_begin(void) {
    if (g_p306_ipc.started || g_p306_ipc.fd >= 0) {
        return P306_DETAIL_LIFECYCLE_CONTRADICTION;
    }
    struct statfs_probe probe = {0};
    long rc = sys_statfs("/sys/kernel/debug", &probe);
    if (rc != 0 || probe.f_type != P306_DEBUGFS_MAGIC) {
        rc = sys_mount(
            "debugfs", "/sys/kernel/debug", "debugfs",
            MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
        if (rc != 0) return P306_DETAIL_MOUNT_FAILED;
        g_p306_ipc.mount_owned = 1U;
        probe.f_type = 0;
        rc = sys_statfs("/sys/kernel/debug", &probe);
        if (rc != 0 || probe.f_type != P306_DEBUGFS_MAGIC) {
            (void)p282_umount2("/sys/kernel/debug", 0);
            g_p306_ipc.mount_owned = 0U;
            return P306_DETAIL_MOUNT_FAILED;
        }
    }
    if (p282_path_regular(P306_IPC_PATH) != 0) {
        if (g_p306_ipc.mount_owned) {
            (void)p282_umount2("/sys/kernel/debug", 0);
            g_p306_ipc.mount_owned = 0U;
        }
        return P306_DETAIL_PATH_UNAVAILABLE;
    }
    long fd = sys_openat(P306_IPC_PATH, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        if (g_p306_ipc.mount_owned) {
            (void)p282_umount2("/sys/kernel/debug", 0);
            g_p306_ipc.mount_owned = 0U;
        }
        return P306_DETAIL_PATH_UNAVAILABLE;
    }
    g_p306_ipc.fd = (int)fd;
    g_p306_ipc.started = 1U;
    return p306_ipc_drain();
}

static long p306_ipc_finish(void) {
    if (!g_p306_ipc.started || g_p306_ipc.fd < 0 || g_p306_ipc.final) {
        return P306_DETAIL_LIFECYCLE_CONTRADICTION;
    }
    long result = p306_ipc_drain();
    if (result == 0 && g_p306_ipc.line_length != 0U) {
        result = P306_DETAIL_FORMAT_CONTRADICTION;
    }
    long close_rc = sys_close(g_p306_ipc.fd);
    g_p306_ipc.fd = -1;
    if (close_rc != 0 && result == 0) {
        result = P306_DETAIL_CLEANUP_FAILED;
    }
    if (g_p306_ipc.mount_owned) {
        long unmount_rc = p282_umount2("/sys/kernel/debug", 0);
        g_p306_ipc.mount_owned = 0U;
        if (unmount_rc != 0 && result == 0) {
            result = P306_DETAIL_CLEANUP_FAILED;
        }
    }
    if (result == 0) g_p306_ipc.final = 1U;
    return result;
}

static unsigned int p306_count_bucket(uint32_t count) {
    if (count == 0U) return 0U;
    if (count == 1U) return 1U;
    if (count <= 3U) return 2U;
    return 3U;
}

static long p306_ipc_details(uint16_t *chain, uint16_t *summary) {
    if (chain == NULL || summary == NULL || !g_p306_ipc.final
        || g_p306_ipc.marker_mask >= 128U
        || g_p306_ipc.condition_mask >= 16U) {
        return P306_DETAIL_LIFECYCLE_CONTRADICTION;
    }
    *chain = (uint16_t)(
        P306_CHAIN_DETAIL_BASE + g_p306_ipc.marker_mask);
    unsigned int index = g_p306_ipc.condition_mask;
    index = index * 4U + p306_count_bucket(g_p306_ipc.bsv_set_count);
    index = index * 4U + p306_count_bucket(g_p306_ipc.start_gadget_count);
    index = index * 4U + p306_count_bucket(g_p306_ipc.peripheral_count);
    index = index * 2U + (unsigned int)g_p306_ipc.ordered_complete;
    if (index >= 2048U) return P306_DETAIL_LIFECYCLE_CONTRADICTION;
    *summary = (uint16_t)(P306_SUMMARY_DETAIL_BASE + index);
    return 0;
}

static void p306_poll_delay(void) {
    long rc = p306_ipc_drain();
    if (rc != 0) p290_fail_next(rc);
    p282_poll_delay();
}

'''


_TAIL_OLD = b"""    for (size_t index = P305_FOLDED_MODULE_INDEX;
         index < S22PLUS_O2_MODULE_PLAN_COUNT;
         ++index) {
        long p305_folded_load_rc = p241_load_and_verify_module(index);
        if (p305_folded_load_rc != 0) {
            fail_at(
                S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
                P305_FOLDED_MODULE_INDEX,
                (long)(P305_FOLDED_FAILURE_BASE + index));
        }
    }
"""

_TAIL_NEW = b"""    long p306_ipc_begin_rc = p306_ipc_begin();
    if (p306_ipc_begin_rc != 0) p290_fail_next(p306_ipc_begin_rc);
    for (size_t index = P305_FOLDED_MODULE_INDEX;
         index < S22PLUS_O2_MODULE_PLAN_COUNT;
         ++index) {
        long p305_folded_load_rc = p241_load_and_verify_module(index);
        if (p305_folded_load_rc != 0) {
            fail_at(
                S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
                P305_FOLDED_MODULE_INDEX,
                (long)(P305_FOLDED_FAILURE_BASE + index));
        }
        long p306_ipc_tail_rc = p306_ipc_drain();
        if (p306_ipc_tail_rc != 0) p290_fail_next(p306_ipc_tail_rc);
    }
"""

_FINAL_OLD = b"""            uint16_t p303_clock = 0;
            uint16_t p303_log = 0;
            rc = p303_clock_detail(&p303_clock);
            if (rc != 0) p290_fail_next(rc);
            rc = p303_kmsg_finish();
            if (rc != 0) p290_fail_next(rc);
            rc = p303_log_detail(&p303_log);
            if (rc != 0) p290_fail_next(rc);
            rc = p294_publish_final_pair(p303_clock, p303_log);
"""

_FINAL_NEW = b"""            uint16_t p303_clock = 0;
            uint16_t p303_log = 0;
            rc = p303_clock_detail(&p303_clock);
            if (rc != 0) p290_fail_next(rc);
            rc = p303_kmsg_finish();
            if (rc != 0) p290_fail_next(rc);
            rc = p303_log_detail(&p303_log);
            if (rc != 0) p290_fail_next(rc);
            (void)p303_clock;
            (void)p303_log;
            rc = p306_ipc_finish();
            if (rc != 0) p290_fail_next(rc);
            uint16_t p306_chain = 0;
            uint16_t p306_summary = 0;
            rc = p306_ipc_details(&p306_chain, &p306_summary);
            if (rc != 0) p290_fail_next(rc);
            rc = p294_publish_final_pair(p306_chain, p306_summary);
"""


def transform_runtime_wrapper(data: bytes) -> bytes:
    if data.count(_TAIL_OLD) != 1 or _TAIL_NEW in data:
        raise TransformError("P3.05 folded tail shape differs")
    return data.replace(_TAIL_OLD, _TAIL_NEW, 1)


def transform_runtime_include(data: bytes) -> bytes:
    anchor = b"static long p282_parse_role_result(\n"
    if data.count(anchor) != 1 or P306_SUPPORT in data:
        raise TransformError("P3.05 IPC support anchor differs")
    value = data.replace(b"p282_poll_delay();", b"p306_poll_delay();")
    if value == data:
        raise TransformError("P3.05 poll sites differ")
    value = value.replace(anchor, P306_SUPPORT + anchor, 1)
    if value.count(_FINAL_OLD) != 1 or _FINAL_NEW in value:
        raise TransformError("P3.05 final publication shape differs")
    value = value.replace(_FINAL_OLD, _FINAL_NEW, 1)
    return value


def transform_artifacts(source: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["runtime_wrapper"] = transform_runtime_wrapper(
        source["runtime_wrapper"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    return result
