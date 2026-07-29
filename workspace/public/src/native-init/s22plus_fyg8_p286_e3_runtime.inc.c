/* P2.86 parent-quiescence and bounded restart over the P2.84 E3 path. */

#include "s22plus_fyg8_p260_e3_runtime.inc.c"
#include "s22plus_fyg8_p286_trace_descriptor.h"
#include "s22plus_fyg8_p286_classifier.inc.c"

#define P282_NR_UNLINKAT 35
#define P282_NR_UMOUNT2 39
#define P282_AT_REMOVEDIR 0x200
#define P282_O_WRONLY 00000001
#define P282_O_TRUNC 00001000
#define P282_S_IFREG 0100000
#define P282_TRACEFS_MAGIC 0x74726163L
#define P282_TRACE_CAPACITY 65536U
#define P282_PROFILE_CAPACITY 65536U
#define P282_DEFINITIONS_CAPACITY 32768U
#define P282_PATH_CAPACITY 256U
#define P282_RECORD_CAPACITY 64U
#define P282_HELPER_MAGIC 0x50323830U
#define P282_HELPER_VERSION 1U
#define P282_HELPER_OPERATION_ROLE_WRITE 1U
#define P282_HELPER_OPERATION_NONE_WRITE 2U
#define P282_HELPER_OPERATION_PERIPHERAL_WRITE 3U
#define P282_CYCLE_DEADLINE_SEC 30
#define P282_FINAL_DEADLINE_SEC 30
#define P282_POLL_INTERVAL_MSEC 100
#define P282_PHASE_ROLE 1U
#define P282_PHASE_CYCLE 2U
#define P282_PHASE_BIND 3U
#define P286_REAP_DEADLINE_MSEC 1000
#define P286_PARENT_RUNTIME_STATUS_PATH \
    "/sys/devices/platform/soc/a600000.ssusb/power/runtime_status"
#define P286_PARENT_SUSPENDED_READBACK "suspended"

_Static_assert(
    P282_POLL_INTERVAL_MSEC * 1000000LL == P260_POLL_NS,
    "P2.82 poll interval must preserve the P2.60 cadence");

static void p282_poll_delay(void) {
    (void)sys_nanosleep(
        (int64_t)P282_POLL_INTERVAL_MSEC * 1000000LL);
}

static const char p282_trace_root[] = "/sys/kernel/tracing";
static const char p282_instance_root[] =
    "/sys/kernel/tracing/instances/p282";
static const char p282_global_group_root[] =
    "/sys/kernel/tracing/events/p282";
static const char p282_global_events_path[] =
    "/sys/kernel/tracing/kprobe_events";
static const char p282_profile_path[] =
    "/sys/kernel/tracing/kprobe_profile";

static char p282_trace_buffer[P282_TRACE_CAPACITY];
static char p282_profile_buffer[P282_PROFILE_CAPACITY];
static char p282_definitions_buffer[P282_DEFINITIONS_CAPACITY];
static size_t p282_trace_length;
static size_t p282_profile_length;

extern long s22_r4w1e_checkpoint_progress_detail(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    uint16_t detail);

struct p282_trace_control {
    const struct p282_event_descriptor *events;
    size_t event_count;
    size_t registered_count;
    uint8_t mount_owned;
    uint8_t tracefs_ready;
    uint8_t instance_owned;
    uint8_t active;
};

struct p282_helper_record {
    uint32_t magic;
    uint16_t version;
    uint16_t operation;
    int64_t result;
    uint32_t byte_count;
    uint32_t reserved;
};

_Static_assert(
    sizeof(struct p282_helper_record) == 24U,
    "P2.82 helper record size");

static void (*const p282_p260_compat_anchor)(void)
    __attribute__((used)) = p260_e3_run;

static long p282_unlinkat(const char *path, int flags) {
    return syscall6(
        P282_NR_UNLINKAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        flags,
        0,
        0,
        0);
}

static long p282_umount2(const char *path, int flags) {
    return syscall6(
        P282_NR_UMOUNT2,
        (long)(uintptr_t)path,
        flags,
        0,
        0,
        0,
        0);
}

static int p282_is_digit(char value) {
    return value >= '0' && value <= '9';
}

static int p282_is_space(char value) {
    return value == ' ' || value == '\t';
}

static long p282_copy_path_part(
    char *output,
    size_t capacity,
    size_t *cursor,
    const char *value) {
    size_t length = cstr_len(value);
    if (*cursor > capacity || length >= capacity - *cursor) {
        return -P260_EOVERFLOW;
    }
    memcpy(output + *cursor, value, length);
    *cursor += length;
    output[*cursor] = '\0';
    return 0;
}

static long p282_make_path(
    char *output,
    size_t capacity,
    const char *prefix,
    const char *name,
    const char *suffix) {
    if (capacity == 0U) {
        return -EINVAL;
    }
    size_t cursor = 0;
    output[0] = '\0';
    long rc = p282_copy_path_part(output, capacity, &cursor, prefix);
    if (rc == 0) {
        rc = p282_copy_path_part(output, capacity, &cursor, name);
    }
    if (rc == 0) {
        rc = p282_copy_path_part(output, capacity, &cursor, suffix);
    }
    return rc;
}

static long p282_read_file(
    const char *path,
    char *buffer,
    size_t capacity,
    size_t *length) {
    if (capacity < 2U || length == NULL) {
        return -EINVAL;
    }
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    size_t used = 0;
    long rc = 0;
    while (used < capacity - 1U) {
        long amount = sys_read((int)fd, buffer + used, capacity - 1U - used);
        if (amount == -P260_EINTR) {
            continue;
        }
        if (amount < 0) {
            rc = amount;
            break;
        }
        if (amount == 0) {
            break;
        }
        if ((size_t)amount > capacity - 1U - used) {
            rc = -EIO;
            break;
        }
        used += (size_t)amount;
    }
    if (rc == 0 && used == capacity - 1U) {
        char extra = '\0';
        long amount = sys_read((int)fd, &extra, 1U);
        if (amount == -P260_EINTR) {
            amount = sys_read((int)fd, &extra, 1U);
        }
        if (amount != 0) {
            rc = amount < 0 ? amount : -P260_EOVERFLOW;
        }
    }
    long close_rc = sys_close((int)fd);
    if (rc == 0 && close_rc != 0) {
        rc = close_rc;
    }
    if (rc != 0) {
        return rc;
    }
    buffer[used] = '\0';
    *length = used;
    return 0;
}

static long p282_write_control(const char *path, const char *value) {
    long fd = sys_openat(path, P282_O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long rc = p260_write_all((int)fd, value, cstr_len(value), 0);
    long close_rc = sys_close((int)fd);
    return rc != 0 ? rc : close_rc;
}

static long p282_clear_trace(void) {
    long fd = sys_openat(
        "/sys/kernel/tracing/instances/p282/trace",
        P282_O_WRONLY | P282_O_TRUNC | O_CLOEXEC,
        0);
    if (fd < 0) {
        return fd;
    }
    long amount = sys_write((int)fd, "\n", 1U);
    long close_rc = sys_close((int)fd);
    if (amount != 1) {
        return amount < 0 ? amount : -EIO;
    }
    return close_rc;
}

static long p282_path_absent(const char *path) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(path, &value, AT_SYMLINK_NOFOLLOW);
    if (rc == -ENOENT) {
        return 0;
    }
    return rc == 0 ? -EEXIST : rc;
}

static long p282_path_regular(const char *path) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(path, &value, AT_SYMLINK_NOFOLLOW);
    if (rc != 0) {
        return rc;
    }
    return (value.st_mode & S_IFMT) == P282_S_IFREG ? 0 : -EIO;
}

static const char *p282_find_bytes(
    const char *haystack,
    size_t haystack_length,
    const char *needle) {
    size_t needle_length = cstr_len(needle);
    if (needle_length == 0U || needle_length > haystack_length) {
        return NULL;
    }
    for (
        size_t index = 0;
        index + needle_length <= haystack_length;
        ++index
    ) {
        if (p260_bytes_equal(haystack + index, needle, needle_length)) {
            return haystack + index;
        }
    }
    return NULL;
}

static size_t p282_count_bytes(
    const char *haystack,
    size_t haystack_length,
    const char *needle) {
    size_t needle_length = cstr_len(needle);
    size_t count = 0;
    if (needle_length == 0U) {
        return 0;
    }
    for (
        size_t index = 0;
        index + needle_length <= haystack_length;
        ++index
    ) {
        if (p260_bytes_equal(haystack + index, needle, needle_length)) {
            ++count;
            index += needle_length - 1U;
        }
    }
    return count;
}

static long p282_event_path(
    char *path,
    size_t capacity,
    const char *name,
    const char *suffix) {
    return p282_make_path(
        path,
        capacity,
        "/sys/kernel/tracing/instances/p282/events/p282/",
        name,
        suffix);
}

static long p282_delete_event(const char *name) {
    char command[96];
    size_t cursor = 0;
    long rc = p282_copy_path_part(
        command, sizeof(command), &cursor, "-:p282/");
    if (rc == 0) {
        rc = p282_copy_path_part(
            command, sizeof(command), &cursor, name);
    }
    if (rc == 0) {
        rc = p282_copy_path_part(command, sizeof(command), &cursor, "\n");
    }
    return rc != 0 ? rc : p282_write_control(
        p282_global_events_path, command);
}

static long p282_trace_mount(struct p282_trace_control *control) {
    struct statfs_probe probe = {0};
    long rc = sys_statfs(p282_trace_root, &probe);
    if (rc == 0 && probe.f_type == P282_TRACEFS_MAGIC) {
        return 0;
    }
    rc = sys_mount(
        "tracefs",
        p282_trace_root,
        "tracefs",
        MS_NOSUID | MS_NODEV | MS_NOEXEC,
        "");
    if (rc != 0 && rc != -P260_EBUSY) {
        return rc;
    }
    control->mount_owned = rc == 0;
    probe.f_type = 0;
    rc = sys_statfs(p282_trace_root, &probe);
    return rc != 0
        ? rc
        : (probe.f_type == P282_TRACEFS_MAGIC ? 0 : -EIO);
}

static long p282_event_registration_state(
    const struct p282_trace_control *control,
    size_t index) {
    if (index >= control->event_count) {
        return -EINVAL;
    }
    size_t definitions_length = 0;
    long rc = p282_read_file(
        p282_global_events_path,
        p282_definitions_buffer,
        sizeof(p282_definitions_buffer),
        &definitions_length);
    if (rc != 0) {
        return rc;
    }
    char identity[96];
    size_t cursor = 0;
    rc = p282_copy_path_part(
        identity, sizeof(identity), &cursor, "p282/");
    if (rc == 0) {
        rc = p282_copy_path_part(
            identity,
            sizeof(identity),
            &cursor,
            control->events[index].name);
    }
    if (rc != 0) {
        return rc;
    }
    size_t identity_count = p282_count_bytes(
        p282_definitions_buffer,
        definitions_length,
        identity);
    if (identity_count == 0U) {
        return 0;
    }
    if (identity_count != 1U) {
        return -P260_EPROTO;
    }
    char path[P282_PATH_CAPACITY];
    rc = p282_event_path(
        path,
        sizeof(path),
        control->events[index].name,
        "/enable");
    if (rc != 0 || p282_path_regular(path) != 0) {
        return rc != 0 ? rc : -EIO;
    }
    return 1;
}

static long p282_verify_event_registration(
    const struct p282_trace_control *control) {
    for (size_t index = 0; index < control->event_count; ++index) {
        long rc = p282_event_registration_state(control, index);
        if (rc != 1) {
            return rc < 0 ? rc : -EIO;
        }
    }
    return 0;
}

static long p282_parse_unsigned(
    const char *start,
    const char *end,
    uint64_t *result);

static long p282_verify_buffer_size(void) {
    char value[128];
    size_t length = 0;
    long rc = p260_read_value(
        "/sys/kernel/tracing/instances/p282/buffer_size_kb",
        value,
        sizeof(value),
        &length);
    uint64_t actual = 0;
    if (rc == 0) {
        rc = p282_parse_unsigned(value, value + length, &actual);
    }
    if (
        rc != 0
        || actual < P282_TRACE_BUFFER_KB
        || actual > P282_TRACE_BUFFER_KB * 2U
    ) {
        return rc != 0 ? rc : -EIO;
    }
    return 0;
}

static long p282_verify_control_readback(
    const struct p282_trace_control *control) {
    char value[4096];
    size_t length = 0;
    long rc = p282_read_file(
        "/sys/kernel/tracing/instances/p282/trace_clock",
        value,
        sizeof(value),
        &length);
    if (
        rc != 0
        || p282_find_bytes(value, length, "[counter]") == NULL
    ) {
        return rc != 0 ? rc : -EIO;
    }
    rc = p282_verify_buffer_size();
    if (rc != 0) {
        return rc;
    }
    for (size_t index = 0; index < control->event_count; ++index) {
        char path[P282_PATH_CAPACITY];
        rc = p282_event_path(
            path,
            sizeof(path),
            control->events[index].name,
            "/filter");
        if (rc != 0) {
            return rc;
        }
        rc = p260_expect_value(
            path, control->events[index].filter);
        if (rc != 0) {
            return rc;
        }
    }
    return 0;
}

static long p282_trace_cleanup(struct p282_trace_control *control) {
    long result = 0;
    size_t registered = control->registered_count;
    int verify_instance_absent = control->instance_owned;
    if (control->active) {
        long rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/tracing_on", "0\n");
        if (rc == 0) {
            rc = p282_write_control(
                "/sys/kernel/tracing/instances/p282/events/p282/enable",
                "0\n");
        }
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->active = 0;
    }
    while (control->registered_count != 0U) {
        size_t index = control->registered_count - 1U;
        (void)p282_delete_event(control->events[index].name);
        --control->registered_count;
    }
    size_t definitions_length = 0;
    if (registered != 0U && !control->tracefs_ready && result == 0) {
        result = -EIO;
    }
    if (control->tracefs_ready && registered != 0U) {
        long read_rc = p282_read_file(
            p282_global_events_path,
            p282_definitions_buffer,
            sizeof(p282_definitions_buffer),
            &definitions_length);
        if (read_rc != 0 && result == 0) {
            result = read_rc;
        }
        for (
            size_t index = 0;
            read_rc == 0 && index < registered;
            ++index
        ) {
            char identity[96];
            size_t cursor = 0;
            long rc = p282_copy_path_part(
                identity, sizeof(identity), &cursor, "p282/");
            if (rc == 0) {
                rc = p282_copy_path_part(
                    identity,
                    sizeof(identity),
                    &cursor,
                    control->events[index].name);
            }
            if (
                rc != 0
                || p282_find_bytes(
                    p282_definitions_buffer,
                    definitions_length,
                    identity) != NULL
            ) {
                if (result == 0) {
                    result = rc != 0 ? rc : -EIO;
                }
            }
        }
    }
    if (control->instance_owned) {
        long rc = p282_unlinkat(p282_instance_root, P282_AT_REMOVEDIR);
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->instance_owned = 0;
    }
    if (
        verify_instance_absent
        && p282_path_absent(p282_instance_root) != 0
        && result == 0
    ) {
        result = -EIO;
    }
    if (control->mount_owned) {
        long rc = p282_umount2(p282_trace_root, 0);
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->mount_owned = 0;
        struct statfs_probe probe = {0};
        rc = sys_statfs(p282_trace_root, &probe);
        if (
            rc == 0
            && probe.f_type == P282_TRACEFS_MAGIC
            && result == 0
        ) {
            result = -EIO;
        }
    }
    control->tracefs_ready = 0;
    return result;
}

static long (*const p282_cleanup_partial_trace)(
    struct p282_trace_control *) = p282_trace_cleanup;

static long p282_trace_setup(
    unsigned int phase,
    struct p282_trace_control *control) {
    const struct p282_event_descriptor *events = NULL;
    size_t event_count = 0;
    if (phase == P282_PHASE_ROLE) {
        events = p282_role_events;
        event_count = P282_ROLE_EVENT_COUNT;
    } else if (phase == P282_PHASE_CYCLE) {
        events = p282_cycle_events;
        event_count = P282_CYCLE_EVENT_COUNT;
    } else if (phase == P282_PHASE_BIND) {
        events = p282_bind_events;
        event_count = P282_BIND_EVENT_COUNT;
    }
    *control = (struct p282_trace_control){
        .events = events,
        .event_count = event_count,
    };
    if (event_count == 0U || event_count > P282_CYCLE_EVENT_COUNT) {
        return P282_CONTROL_TRACE_CONTROL_UNAVAILABLE;
    }
    long rc = p282_trace_mount(control);
    long warning = P282_CONTROL_TRACE_CONTROL_UNAVAILABLE;
    if (rc == 0) {
        control->tracefs_ready = 1;
        warning = P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE;
        rc = p282_path_absent(p282_global_group_root);
    }
    if (rc == 0) {
        rc = p282_path_absent(p282_instance_root);
    }
    if (rc == 0) {
        rc = sys_mkdirat(p282_instance_root, 0700);
        if (rc == 0) {
            control->instance_owned = 1;
        }
    }
    if (rc == 0) {
        for (size_t index = 0; index < event_count; ++index) {
            long write_rc = p282_write_control(
                p282_global_events_path,
                events[index].definition);
            long state = p282_event_registration_state(control, index);
            if (state != 0) {
                ++control->registered_count;
            }
            if (write_rc != 0) {
                rc = write_rc;
                break;
            }
            if (state != 1) {
                rc = state < 0 ? state : -EIO;
                break;
            }
        }
    }
    if (rc == 0) {
        rc = p282_verify_event_registration(control);
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/tracing_on", "0\n");
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/trace_clock",
            "counter\n");
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/buffer_size_kb",
            "64\n");
    }
    for (size_t index = 0; rc == 0 && index < event_count; ++index) {
        char path[P282_PATH_CAPACITY];
        rc = p282_event_path(
            path,
            sizeof(path),
            events[index].name,
            "/filter");
        if (rc == 0) {
            rc = p282_write_control(path, events[index].filter);
        }
    }
    if (rc == 0) {
        rc = p282_verify_control_readback(control);
    }
    if (rc == 0) {
        rc = p282_clear_trace();
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/events/p282/enable",
            "1\n");
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/tracing_on", "1\n");
    }
    if (rc == 0) {
        control->active = 1;
        return 0;
    }
    long cleanup_rc = p282_cleanup_partial_trace(control);
    return cleanup_rc == 0
        ? warning
        : P282_CONTROL_TRACE_CLEANUP_UNVERIFIED;
}

static long p282_parse_unsigned(
    const char *start,
    const char *end,
    uint64_t *result) {
    if (start >= end || result == NULL || !p282_is_digit(*start)) {
        return -EINVAL;
    }
    uint64_t value = 0;
    for (const char *cursor = start; cursor < end; ++cursor) {
        if (!p282_is_digit(*cursor)) {
            return -EINVAL;
        }
        uint64_t digit = (uint64_t)(*cursor - '0');
        if (value > (UINT64_MAX - digit) / 10U) {
            return -P260_EOVERFLOW;
        }
        value = value * 10U + digit;
    }
    *result = value;
    return 0;
}

static long p282_parse_signed(
    const char *start,
    const char *end,
    int64_t *result) {
    int negative = 0;
    if (start < end && *start == '-') {
        negative = 1;
        ++start;
    }
    uint64_t magnitude = 0;
    long rc = p282_parse_unsigned(start, end, &magnitude);
    if (rc != 0 || magnitude > (uint64_t)INT64_MAX + (uint64_t)negative) {
        return rc != 0 ? rc : -P260_EOVERFLOW;
    }
    *result = negative ? -(int64_t)magnitude : (int64_t)magnitude;
    return 0;
}

struct p282_trace_record {
    uint64_t counter;
    long pid;
    uint8_t event_index;
    uint8_t has_on;
    uint8_t has_suspend;
    uint8_t has_rc;
    int32_t on;
    int32_t suspend;
    int32_t rc;
};

static const char *p282_line_find(
    const char *start,
    const char *end,
    const char *needle) {
    return p282_find_bytes(start, (size_t)(end - start), needle);
}

static long p282_parse_field(
    const char *start,
    const char *end,
    const char *name,
    int32_t *result,
    uint8_t *present) {
    const char *cursor = start;
    size_t name_length = cstr_len(name);
    *present = 0;
    while (cursor < end) {
        const char *found = p282_line_find(cursor, end, name);
        if (found == NULL) {
            return 0;
        }
        if (
            (found == start || p282_is_space(found[-1]))
            && found + name_length < end
        ) {
            const char *value_start = found + name_length;
            const char *value_end = value_start;
            if (value_end < end && *value_end == '-') {
                ++value_end;
            }
            while (value_end < end && p282_is_digit(*value_end)) {
                ++value_end;
            }
            if (
                value_end < end
                && !p282_is_space(*value_end)
            ) {
                return -P260_EPROTO;
            }
            int64_t value = 0;
            long rc = p282_parse_signed(
                value_start, value_end, &value);
            if (
                rc != 0
                || value < (int64_t)INT32_MIN
                || value > (int64_t)INT32_MAX
            ) {
                return rc != 0 ? rc : -P260_EOVERFLOW;
            }
            if (*present) {
                return -P260_EPROTO;
            }
            *present = 1;
            *result = (int32_t)value;
            cursor = value_end;
            continue;
        }
        cursor = found + 1;
    }
    return 0;
}

static long p282_parse_line_identity(
    const char *line,
    const char *line_end,
    const char *marker,
    long *pid,
    uint64_t *counter) {
    const char *bracket = p282_line_find(line, marker, "[");
    if (bracket == NULL) {
        return -P260_EPROTO;
    }
    const char *pid_end = bracket;
    while (pid_end > line && p282_is_space(pid_end[-1])) {
        --pid_end;
    }
    const char *pid_start = pid_end;
    while (pid_start > line && p282_is_digit(pid_start[-1])) {
        --pid_start;
    }
    if (pid_start == pid_end || pid_start == line || pid_start[-1] != '-') {
        return -P260_EPROTO;
    }
    uint64_t parsed_pid = 0;
    long rc = p282_parse_unsigned(pid_start, pid_end, &parsed_pid);
    if (rc != 0 || parsed_pid > (uint64_t)INT64_MAX) {
        return rc != 0 ? rc : -P260_EOVERFLOW;
    }
    const char *close = p282_line_find(bracket, marker, "]");
    if (close == NULL) {
        return -P260_EPROTO;
    }
    const char *cursor = close + 1;
    int found_counter = 0;
    uint64_t parsed_counter = 0;
    while (cursor < marker) {
        if (!p282_is_digit(*cursor)) {
            ++cursor;
            continue;
        }
        const char *number_start = cursor;
        while (cursor < marker && p282_is_digit(*cursor)) {
            ++cursor;
        }
        if (cursor <= marker && *cursor == ':') {
            if (found_counter) {
                return -P260_EPROTO;
            }
            rc = p282_parse_unsigned(
                number_start, cursor, &parsed_counter);
            if (rc != 0) {
                return rc;
            }
            found_counter = 1;
        }
    }
    if (!found_counter || marker >= line_end) {
        return -P260_EPROTO;
    }
    *pid = (long)parsed_pid;
    *counter = parsed_counter;
    return 0;
}

static long p282_parse_trace_records(
    const struct p282_trace_control *control,
    struct p282_trace_record records[P282_RECORD_CAPACITY],
    size_t *record_count) {
    size_t count = 0;
    const char *cursor = p282_trace_buffer;
    const char *end = p282_trace_buffer + p282_trace_length;
    uint64_t previous_counter = 0;
    int have_previous = 0;
    while (cursor < end) {
        const char *line_end = cursor;
        while (line_end < end && *line_end != '\n') {
            ++line_end;
        }
        const char *bracket = p282_line_find(cursor, line_end, "[");
        const char *close = bracket == NULL
            ? NULL
            : p282_line_find(bracket, line_end, "]");
        const char *marker = close == NULL
            ? NULL
            : p282_line_find(close, line_end, ": ");
        if (marker != NULL) {
            if (line_end == end) {
                return -P260_EPROTO;
            }
            const char *event_start = marker + cstr_len(": ");
            const char *event_end = event_start;
            while (event_end < line_end && *event_end != ':') {
                ++event_end;
            }
            if (event_end == line_end) {
                return -P260_EPROTO;
            }
            size_t event_index = control->event_count;
            for (size_t index = 0; index < control->event_count; ++index) {
                size_t length = cstr_len(control->events[index].name);
                if (
                    (size_t)(event_end - event_start) == length
                    && p260_bytes_equal(
                        event_start,
                        control->events[index].name,
                        length)
                ) {
                    event_index = index;
                    break;
                }
            }
            if (event_index == control->event_count) {
                return -P260_EPROTO;
            }
            if (count == P282_RECORD_CAPACITY) {
                return -P260_EOVERFLOW;
            }
            struct p282_trace_record record = {
                .event_index = (uint8_t)event_index,
            };
            long rc = p282_parse_line_identity(
                cursor,
                line_end,
                marker,
                &record.pid,
                &record.counter);
            if (rc == 0) {
                rc = p282_parse_field(
                    event_end + 1,
                    line_end,
                    "suspend=",
                    &record.suspend,
                    &record.has_suspend);
            }
            if (rc == 0) {
                rc = p282_parse_field(
                    event_end + 1,
                    line_end,
                    "on=",
                    &record.on,
                    &record.has_on);
            }
            if (rc == 0) {
                rc = p282_parse_field(
                    event_end + 1,
                    line_end,
                    "rc=",
                    &record.rc,
                    &record.has_rc);
            }
            if (rc != 0) {
                return rc;
            }
            if (
                have_previous
                && record.counter <= previous_counter
            ) {
                return -P260_EPROTO;
            }
            have_previous = 1;
            previous_counter = record.counter;
            records[count++] = record;
        }
        cursor = line_end < end ? line_end + 1 : end;
    }
    *record_count = count;
    return 0;
}

static long p282_profile_clean(
    const struct p282_trace_control *control) {
    uint8_t seen[P282_CYCLE_EVENT_COUNT] = {0};
    const char *cursor = p282_profile_buffer;
    const char *end = p282_profile_buffer + p282_profile_length;
    while (cursor < end) {
        const char *line_end = cursor;
        while (line_end < end && *line_end != '\n') {
            ++line_end;
        }
        const char *name_start = cursor;
        while (name_start < line_end && p282_is_space(*name_start)) {
            ++name_start;
        }
        const char *name_end = name_start;
        while (name_end < line_end && !p282_is_space(*name_end)) {
            ++name_end;
        }
        for (size_t index = 0; index < control->event_count; ++index) {
            size_t length = cstr_len(control->events[index].name);
            if (
                (size_t)(name_end - name_start) != length
                || !p260_bytes_equal(
                    name_start, control->events[index].name, length)
            ) {
                continue;
            }
            if (seen[index]) {
                return -P260_EPROTO;
            }
            const char *hits_start = name_end;
            while (hits_start < line_end && p282_is_space(*hits_start)) {
                ++hits_start;
            }
            const char *hits_end = hits_start;
            while (hits_end < line_end && p282_is_digit(*hits_end)) {
                ++hits_end;
            }
            const char *missed_start = hits_end;
            while (
                missed_start < line_end
                && p282_is_space(*missed_start)
            ) {
                ++missed_start;
            }
            const char *missed_end = missed_start;
            while (
                missed_end < line_end
                && p282_is_digit(*missed_end)
            ) {
                ++missed_end;
            }
            uint64_t hits = 0;
            uint64_t missed = 0;
            long rc = p282_parse_unsigned(
                hits_start, hits_end, &hits);
            if (rc == 0) {
                rc = p282_parse_unsigned(
                    missed_start, missed_end, &missed);
            }
            if (rc != 0 || missed != 0U) {
                return rc != 0 ? rc : -EIO;
            }
            (void)hits;
            seen[index] = 1;
        }
        cursor = line_end < end ? line_end + 1 : end;
    }
    for (size_t index = 0; index < control->event_count; ++index) {
        if (!seen[index]) {
            return -EIO;
        }
    }
    return 0;
}

static long p282_trace_disable(
    struct p282_trace_control *control) {
    if (!control->active) {
        return 0;
    }
    long rc = p282_write_control(
        "/sys/kernel/tracing/instances/p282/tracing_on", "0\n");
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/events/p282/enable",
            "0\n");
    }
    if (rc == 0) {
        control->active = 0;
    }
    return rc;
}

static long p282_trace_read_snapshot(
    const struct p282_trace_control *control,
    int require_profile) {
    long rc = p282_read_file(
        "/sys/kernel/tracing/instances/p282/trace",
        p282_trace_buffer,
        sizeof(p282_trace_buffer),
        &p282_trace_length);
    if (rc != 0 || !require_profile) {
        return rc;
    }
    rc = p282_read_file(
        p282_profile_path,
        p282_profile_buffer,
        sizeof(p282_profile_buffer),
        &p282_profile_length);
    return rc != 0 ? rc : p282_profile_clean(control);
}

static long p282_trace_finish(
    struct p282_trace_control *control,
    long *quality) {
    long local_quality = p282_trace_disable(control);
    if (local_quality == 0) {
        local_quality = p282_trace_read_snapshot(control, 1);
    }
    long cleanup_rc = p282_trace_cleanup(control);
    if (cleanup_rc != 0) {
        return P282_CONTROL_TRACE_CLEANUP_UNVERIFIED;
    }
    *quality = local_quality;
    return 0;
}

static void p282_trace_deadline_disable(
    struct p282_trace_control *control) {
    if (!control->active) {
        return;
    }
    (void)p282_write_control(
        "/sys/kernel/tracing/instances/p282/tracing_on", "0\n");
    (void)p282_write_control(
        "/sys/kernel/tracing/instances/p282/events/p282/enable", "0\n");
    control->active = 0;
}

enum p282_role_classification {
    P282_ROLE_NO_START = 0,
    P282_ROLE_START_NO_RETURN = 1,
    P282_ROLE_COMPLETE = 2,
    P282_ROLE_PARENT_PM_NEGATIVE = 3,
    P282_ROLE_CHILD_PM_NEGATIVE = 4,
};

struct p282_role_result {
    enum p282_role_classification classification;
    long pid;
    int32_t parent_pm_rc;
    int32_t child_pm_rc;
};

struct p282_trace_pair {
    uint8_t entered;
    uint8_t returned;
    int32_t rc;
    uint64_t entry_counter;
    uint64_t return_counter;
};

struct p282_cycle_trace_result {
    struct p282_trace_pair stop_worker;
    struct p282_trace_pair child_suspend;
    struct p282_trace_pair power_off;
    struct p282_trace_pair restart_worker;
    struct p282_trace_pair child_resume;
    struct p282_trace_pair power_on;
    struct p282_trace_pair phy_init;
    struct p282_trace_pair notify_connect;
    uint8_t outer_entered;
    uint8_t outer_returned;
    uint8_t outer_open;
};

struct p282_bind_trace_result {
    uint8_t source_consistent;
    uint8_t pullup_returned_zero;
    uint8_t run_stop_seen;
    int32_t run_stop_rc;
    unsigned int branch;
};

static long p282_parse_role_result(
    const struct p282_trace_control *control,
    struct p282_role_result *result) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) {
        return rc;
    }
    size_t first = count;
    for (size_t index = 0; index < count; ++index) {
        if (records[index].event_index != 0U) {
            continue;
        }
        if (!records[index].has_on || records[index].on != 1) {
            return -P260_EPROTO;
        }
        if (first != count) {
            return -P260_EPROTO;
        }
        first = index;
    }
    if (first == count) {
        *result = (struct p282_role_result){
            .classification = P282_ROLE_NO_START,
        };
        return 0;
    }
    long pid = records[first].pid;
    size_t positions[4] = {first, count, count, count};
    for (size_t index = first + 1U; index < count; ++index) {
        if (records[index].pid != pid) {
            continue;
        }
        uint8_t event = records[index].event_index;
        if (event == 0U || event > 3U || positions[event] != count) {
            return -P260_EPROTO;
        }
        positions[event] = index;
    }
    if (positions[3] == count) {
        *result = (struct p282_role_result){
            .classification = P282_ROLE_START_NO_RETURN,
            .pid = pid,
        };
        return 0;
    }
    if (
        positions[1] == count
        || positions[2] == count
        || !(positions[0] < positions[1]
             && positions[1] < positions[2]
             && positions[2] < positions[3])
    ) {
        return -P260_EPROTO;
    }
    const struct p282_trace_record *parent = &records[positions[1]];
    const struct p282_trace_record *child = &records[positions[2]];
    const struct p282_trace_record *stop = &records[positions[3]];
    if (
        !parent->has_rc
        || !child->has_rc
        || !stop->has_rc
        || stop->rc != 0
    ) {
        return -P260_EPROTO;
    }
    enum p282_role_classification classification = P282_ROLE_COMPLETE;
    if (parent->rc < 0) {
        classification = P282_ROLE_PARENT_PM_NEGATIVE;
    } else if (child->rc < 0) {
        classification = P282_ROLE_CHILD_PM_NEGATIVE;
    }
    *result = (struct p282_role_result){
        .classification = classification,
        .pid = pid,
        .parent_pm_rc = parent->rc,
        .child_pm_rc = child->rc,
    };
    return 0;
}

static int p282_record_argument_matches(
    const struct p282_trace_record *record,
    int argument_kind,
    int argument_value) {
    if (argument_kind == 0) {
        return 1;
    }
    if (argument_kind == 1) {
        return record->has_on && record->on == argument_value;
    }
    if (argument_kind == 2) {
        return record->has_suspend
            && record->suspend == argument_value;
    }
    return 0;
}

static long p282_pair_in_window(
    const struct p282_trace_record *records,
    size_t count,
    uint8_t entry_event,
    uint8_t return_event,
    long pid,
    uint64_t lower,
    uint64_t upper,
    int argument_kind,
    int argument_value,
    struct p282_trace_pair *pair) {
    *pair = (struct p282_trace_pair){0};
    const struct p282_trace_record *entry = NULL;
    const struct p282_trace_record *returned = NULL;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (
            record->pid != pid
            || record->counter <= lower
            || record->counter >= upper
        ) {
            continue;
        }
        if (
            record->event_index == entry_event
            && p282_record_argument_matches(
                record, argument_kind, argument_value)
        ) {
            if (entry != NULL) {
                return -P260_EPROTO;
            }
            entry = record;
        }
    }
    if (entry == NULL) {
        return 0;
    }
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (
            record->pid != pid
            || record->event_index != return_event
            || record->counter <= entry->counter
            || record->counter >= upper
        ) {
            continue;
        }
        if (returned != NULL) {
            return -P260_EPROTO;
        }
        returned = record;
    }
    pair->entered = 1;
    pair->entry_counter = entry->counter;
    if (returned != NULL) {
        if (!returned->has_rc) {
            return -P260_EPROTO;
        }
        pair->returned = 1;
        pair->return_counter = returned->counter;
        pair->rc = returned->rc;
    }
    return 0;
}

static long p282_parent_pair(
    const struct p282_trace_record *records,
    size_t count,
    int on,
    struct p282_trace_pair *pair,
    long *pid) {
    *pair = (struct p282_trace_pair){0};
    *pid = 0;
    const struct p282_trace_record *entry = NULL;
    const struct p282_trace_record *returned = NULL;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (
            record->event_index != 0U
            || !record->has_on
            || record->on != on
        ) {
            continue;
        }
        if (entry != NULL) {
            return -P260_EPROTO;
        }
        entry = record;
    }
    if (entry == NULL) {
        return 0;
    }
    uint64_t upper = UINT64_MAX;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (
            record->event_index == 0U
            && record->pid == entry->pid
            && record->counter > entry->counter
            && record->counter < upper
        ) {
            upper = record->counter;
        }
    }
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (
            record->event_index != 1U
            || record->pid != entry->pid
            || record->counter <= entry->counter
            || record->counter >= upper
        ) {
            continue;
        }
        if (returned != NULL) {
            return -P260_EPROTO;
        }
        returned = record;
    }
    pair->entered = 1;
    pair->entry_counter = entry->counter;
    *pid = entry->pid;
    if (returned != NULL) {
        if (!returned->has_rc) {
            return -P260_EPROTO;
        }
        pair->returned = 1;
        pair->return_counter = returned->counter;
        pair->rc = returned->rc;
    }
    return 0;
}

static long p286_outer_state(
    const struct p282_trace_record *records,
    size_t count,
    struct p282_cycle_trace_result *result) {
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index != 14U && record->event_index != 15U) {
            continue;
        }
        if (record->event_index == 15U && !record->has_rc) {
            return -P260_EPROTO;
        }

        const struct p282_trace_record *previous = NULL;
        const struct p282_trace_record *next = NULL;
        for (size_t other = 0; other < count; ++other) {
            const struct p282_trace_record *candidate = &records[other];
            if (
                candidate->pid != record->pid
                || (
                    candidate->event_index != 14U
                    && candidate->event_index != 15U
                )
            ) {
                continue;
            }
            if (
                candidate->counter < record->counter
                && (
                    previous == NULL
                    || candidate->counter > previous->counter
                )
            ) {
                previous = candidate;
            }
            if (
                candidate->counter > record->counter
                && (next == NULL || candidate->counter < next->counter)
            ) {
                next = candidate;
            }
        }

        if (record->event_index == 15U) {
            if (previous == NULL || previous->event_index != 14U) {
                return -P260_EPROTO;
            }
            result->outer_returned = 1;
            continue;
        }

        result->outer_entered = 1;
        if (next == NULL) {
            result->outer_open = 1;
        } else if (next->event_index != 15U) {
            return -P260_EPROTO;
        }
    }
    return 0;
}

static long p282_parse_cycle_result(
    const struct p282_trace_control *control,
    struct p282_cycle_trace_result *result) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *result = (struct p282_cycle_trace_result){0};
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) {
        return rc;
    }

    long stop_pid = 0;
    long restart_pid = 0;
    rc = p282_parent_pair(
        records, count, 0, &result->stop_worker, &stop_pid);
    if (rc == 0) {
        rc = p282_parent_pair(
            records,
            count,
            1,
            &result->restart_worker,
            &restart_pid);
    }
    if (rc != 0) {
        return rc;
    }

    if (result->stop_worker.entered) {
        uint64_t upper = result->stop_worker.returned
            ? result->stop_worker.return_counter
            : UINT64_MAX;
        struct p282_trace_pair phy_suspend = {0};
        rc = p282_pair_in_window(
            records,
            count,
            2U,
            3U,
            stop_pid,
            result->stop_worker.entry_counter,
            upper,
            0,
            0,
            &result->child_suspend);
        if (rc == 0 && result->child_suspend.entered) {
            uint64_t suspend_upper = result->child_suspend.returned
                ? result->child_suspend.return_counter
                : upper;
            rc = p282_pair_in_window(
                records,
                count,
                6U,
                7U,
                stop_pid,
                result->child_suspend.entry_counter,
                suspend_upper,
                2,
                1,
                &phy_suspend);
            if (rc == 0 && phy_suspend.entered) {
                uint64_t phy_upper = phy_suspend.returned
                    ? phy_suspend.return_counter
                    : suspend_upper;
                rc = p282_pair_in_window(
                    records,
                    count,
                    8U,
                    9U,
                    stop_pid,
                    phy_suspend.entry_counter,
                    phy_upper,
                    1,
                    0,
                    &result->power_off);
            }
            if (
                rc == 0
                && result->child_suspend.returned
                && (
                    !phy_suspend.entered
                    || !phy_suspend.returned
                    || phy_suspend.rc != 0
                )
            ) {
                rc = -P260_EPROTO;
            }
        }
    }

    if (rc == 0 && result->restart_worker.entered) {
        uint64_t upper = result->restart_worker.returned
            ? result->restart_worker.return_counter
            : UINT64_MAX;
        rc = p282_pair_in_window(
            records,
            count,
            4U,
            5U,
            restart_pid,
            result->restart_worker.entry_counter,
            upper,
            0,
            0,
            &result->child_resume);
        if (rc == 0 && result->child_resume.entered) {
            uint64_t resume_upper = result->child_resume.returned
                ? result->child_resume.return_counter
                : upper;
            rc = p282_pair_in_window(
                records,
                count,
                10U,
                11U,
                restart_pid,
                result->child_resume.entry_counter,
                resume_upper,
                0,
                0,
                &result->phy_init);
            if (rc == 0 && result->phy_init.entered) {
                uint64_t init_upper = result->phy_init.returned
                    ? result->phy_init.return_counter
                    : resume_upper;
                rc = p282_pair_in_window(
                    records,
                    count,
                    8U,
                    9U,
                    restart_pid,
                    result->phy_init.entry_counter,
                    init_upper,
                    1,
                    1,
                    &result->power_on);
            }
        }
        if (rc == 0) {
            rc = p282_pair_in_window(
                records,
                count,
                12U,
                13U,
                restart_pid,
                result->restart_worker.entry_counter,
                upper,
                0,
                0,
                &result->notify_connect);
        }
        if (
            rc == 0
            && result->child_resume.returned
            && result->notify_connect.entered
            && result->notify_connect.entry_counter
                <= result->child_resume.return_counter
        ) {
            rc = -P260_EPROTO;
        }
    }
    if (rc == 0) {
        rc = p286_outer_state(records, count, result);
    }
    return rc;
}

static long p282_parse_bind_result(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *result = (struct p282_bind_trace_result){
        .source_consistent = 1,
        .branch = P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) {
        return rc;
    }
    for (size_t index = 0; index < count; ++index) {
        if (records[index].pid != 1) {
            return -P260_EPROTO;
        }
    }
    struct p282_trace_pair pull = {0};
    rc = p282_pair_in_window(
        records,
        count,
        2U,
        3U,
        1,
        0,
        UINT64_MAX,
        1,
        1,
        &pull);
    if (rc != 0) {
        return rc;
    }
    if (!pull.entered || !pull.returned) {
        return 1;
    }
    if (pull.rc != 0) {
        return -P260_EPROTO;
    }
    result->pullup_returned_zero = 1;

    struct p282_trace_pair resume = {0};
    struct p282_trace_pair run = {0};
    rc = p282_pair_in_window(
        records,
        count,
        0U,
        1U,
        1,
        pull.entry_counter,
        pull.return_counter,
        0,
        0,
        &resume);
    if (rc == 0) {
        rc = p282_pair_in_window(
            records,
            count,
            4U,
            5U,
            1,
            pull.entry_counter,
            pull.return_counter,
            1,
            1,
            &run);
    }
    if (rc != 0) {
        return rc;
    }
    if (
        (resume.entered && !resume.returned)
        || (run.entered && !run.returned)
        || (resume.returned && resume.rc < 0)
    ) {
        return -P260_EPROTO;
    }
    if (!run.entered) {
        return 0;
    }
    result->run_stop_seen = 1;
    result->run_stop_rc = run.rc;
    if (resume.returned) {
        if (
            !(
                resume.entry_counter < run.entry_counter
                && run.return_counter < resume.return_counter
            )
        ) {
            return -P260_EPROTO;
        }
        result->branch = P282_BIND_RESUME_NESTED;
    } else {
        if (run.rc != 0) {
            return -P260_EPROTO;
        }
        result->branch = P282_BIND_DIRECT;
    }
    return 0;
}

static long p282_read_role_class(void) {
    char value[32];
    size_t length = 0;
    long rc = p260_read_value(
        p260_role_path, value, sizeof(value), &length);
    if (rc != 0) {
        return rc;
    }
    if (
        length == 4U
        && p260_bytes_equal(value, "none", 4U)
    ) {
        return 0;
    }
    if (
        length == 10U
        && p260_bytes_equal(value, "peripheral", 10U)
    ) {
        return P282_DETAIL_INITIAL_ROLE_PERIPHERAL;
    }
    if (
        length == 4U
        && p260_bytes_equal(value, "host", 4U)
    ) {
        return P282_DETAIL_INITIAL_ROLE_HOST;
    }
    return -P260_EPROTO;
}

static long p282_role_write_once(uint32_t *byte_count) {
    *byte_count = 0;
    long fd = sys_openat(p260_role_path, O_RDWR | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    static const char role[] = "peripheral";
    long amount = sys_write((int)fd, role, sizeof(role) - 1U);
    if (amount > 0) {
        *byte_count = (uint32_t)amount;
    }
    long close_rc = sys_close((int)fd);
    if (amount != (long)(sizeof(role) - 1U)) {
        return amount;
    }
    return close_rc;
}

static __attribute__((noreturn)) void p282_role_child(
    int pipe_fd, int unrelated_fd) {
    if (unrelated_fd >= 0 && unrelated_fd != pipe_fd) {
        (void)sys_close(unrelated_fd);
    }
    struct p282_helper_record record = {
        .magic = P282_HELPER_MAGIC,
        .version = P282_HELPER_VERSION,
        .operation = P282_HELPER_OPERATION_ROLE_WRITE,
    };
    uint32_t byte_count = 0;
    record.result = p282_role_write_once(&byte_count);
    record.byte_count = byte_count;
    long amount = sys_write(pipe_fd, &record, sizeof(record));
    (void)sys_close(pipe_fd);
    sys_exit(amount == (long)sizeof(record) ? 0 : 2);
}

static long p282_validate_helper_record(
    const struct p282_helper_record *record) {
    if (
        record->magic != P282_HELPER_MAGIC
        || record->version != P282_HELPER_VERSION
        || record->operation != P282_HELPER_OPERATION_ROLE_WRITE
        || record->reserved != 0U
        || record->result > 0
        || record->byte_count > 10U
    ) {
        return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    if (record->result == 0 && record->byte_count != 10U) {
        return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    if (record->result < 0 && record->byte_count != 0U) {
        return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    return 0;
}

static void p282_progress(uint8_t stage, uint16_t warning) {
    p260_revalidate_or_fail(stage);
    long rc = warning == 0U
        ? s22_r4w1e_checkpoint_progress(&g_checkpoint, stage, 0U)
        : s22_r4w1e_checkpoint_progress_detail(
            &g_checkpoint, stage, 0U, warning);
    if (rc != 0) {
        quiet_park();
    }
}

static long p282_role_trace_detail(long condition) {
    if (condition == P282_CONTROL_TRACE_CONTROL_UNAVAILABLE) {
        return P282_DETAIL_TRACE_CONTROL_UNAVAILABLE;
    }
    if (condition == P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE) {
        return P282_DETAIL_TRACE_REGISTRATION_UNAVAILABLE;
    }
    if (condition == P282_CONTROL_TRACE_INCOMPLETE) {
        return P282_DETAIL_ROLE_WORKER_QUIESCENCE_UNPROVED;
    }
    if (condition == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        return P282_DETAIL_TRACE_CLEANUP_UNVERIFIED;
    }
    return condition == P282_CONTROL_NONE ? 0 : -P260_EPROTO;
}

static long p282_cleanup_before_action(
    struct p282_trace_control *control) {
    long quality = 0;
    long rc = p282_trace_finish(control, &quality);
    (void)quality;
    return p282_role_trace_detail(rc);
}

static __attribute__((noreturn)) void p282_fail_role_trace(
    struct p282_trace_control *control,
    int pipe_fd,
    long detail,
    int quiescent) {
    (void)sys_close(pipe_fd);
    if (quiescent) {
        long quality = 0;
        long finish_rc = p282_trace_finish(control, &quality);
        if (finish_rc != 0) {
            fail_at(
                P260_ROLE_UDC_STAGE,
                0U,
                p282_role_trace_detail(finish_rc));
        }
    } else {
        p282_trace_deadline_disable(control);
    }
    fail_at(P260_ROLE_UDC_STAGE, 0U, detail);
}

static long p282_phase_role(uint16_t *first_warning, int unrelated_fd) {
    struct p282_trace_control control;
    long setup_rc = p282_trace_setup(P282_PHASE_ROLE, &control);
    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        return p282_role_trace_detail(setup_rc);
    }
    int armed = setup_rc == 0;
    if (!armed) {
        *first_warning = (uint16_t)p282_role_trace_detail(setup_rc);
    }

    long role_class = p282_read_role_class();
    if (role_class != 0) {
        if (armed) {
            long cleanup_rc = p282_cleanup_before_action(&control);
            if (cleanup_rc != 0) {
                return cleanup_rc;
            }
        }
        return role_class;
    }

    if (!armed) {
        long rc = p260_wait_role_and_udc();
        if (rc != 0) {
            return rc;
        }
        return p260_expect_value(p260_role_path, "peripheral");
    }

    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        long cleanup_rc = p282_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : -EIO;
    }
    deadline.tv_sec += P282_ROLE_DEADLINE_SEC;

    int pipe_fds[2] = {-1, -1};
    long rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);
    if (rc != 0) {
        long cleanup_rc = p282_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : rc;
    }
    long pid = sys_clone();
    if (pid < 0) {
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        long cleanup_rc = p282_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : pid;
    }
    if (pid == 0) {
        (void)sys_close(pipe_fds[0]);
        p282_role_child(pipe_fds[1], unrelated_fd);
    }
    (void)sys_close(pipe_fds[1]);

    struct p282_helper_record record = {0};
    size_t record_bytes = 0;
    int record_complete = 0;
    int record_malformed = 0;
    int child_reaped = 0;
    int child_status = 0;
    struct p282_role_result role_result = {
        .classification = P282_ROLE_NO_START,
    };
    for (;;) {
        if (!record_complete) {
            long amount = sys_read(
                pipe_fds[0],
                (uint8_t *)&record + record_bytes,
                sizeof(record) - record_bytes);
            if (amount > 0) {
                if ((size_t)amount > sizeof(record) - record_bytes) {
                    record_malformed = 1;
                } else {
                    record_bytes += (size_t)amount;
                    record_complete = record_bytes == sizeof(record);
                }
            } else if (amount == 0) {
                if (!record_complete) {
                    record_malformed = 1;
                }
            } else if (
                amount != -EAGAIN
                && amount != -P260_EINTR
            ) {
                record_malformed = 1;
            }
        }
        if (!child_reaped) {
            long waited = sys_wait4(pid, &child_status, WNOHANG);
            if (waited == pid) {
                child_reaped = 1;
            } else if (waited < 0 && waited != -P260_EINTR) {
                record_malformed = 1;
                child_reaped = 1;
            }
        }
        long snapshot_rc = p282_trace_read_snapshot(&control, 0);
        long parse_rc = snapshot_rc == 0
            ? p282_parse_role_result(&control, &role_result)
            : snapshot_rc;

        if (record_complete && child_reaped) {
            uint8_t extra = 0;
            long extra_amount = sys_read(pipe_fds[0], &extra, 1U);
            if (extra_amount != 0) {
                record_malformed = 1;
            }
        }
        if (record_complete && child_reaped) {
            long record_rc = p282_validate_helper_record(&record);
            if (record_rc != 0) {
                p282_fail_role_trace(
                    &control,
                    pipe_fds[0],
                    record_rc,
                    parse_rc == 0
                        && role_result.classification >= P282_ROLE_COMPLETE);
            }
            if (record.result < 0) {
                if (
                    parse_rc != 0
                    || role_result.classification != P282_ROLE_NO_START
                ) {
                    p282_fail_role_trace(
                        &control,
                        pipe_fds[0],
                        P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                        parse_rc == 0
                            && role_result.classification
                                >= P282_ROLE_COMPLETE);
                }
                (void)sys_close(pipe_fds[0]);
                long quality = 0;
                long finish_rc = p282_trace_finish(&control, &quality);
                return finish_rc != 0
                    ? p282_role_trace_detail(finish_rc)
                    : (long)record.result;
            }
        }
        if (
            child_reaped
            && (
                record_malformed
                || child_status != 0
                || (record_complete && parse_rc != 0)
            )
        ) {
            p282_fail_role_trace(
                &control,
                pipe_fds[0],
                P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                parse_rc == 0
                    && role_result.classification >= P282_ROLE_COMPLETE);
        }
        if (
            record_complete
            && child_reaped
            && parse_rc == 0
            && role_result.classification >= P282_ROLE_COMPLETE
        ) {
            (void)sys_close(pipe_fds[0]);
            long quality = 0;
            long finish_rc = p282_trace_finish(&control, &quality);
            if (finish_rc != 0) {
                return p282_role_trace_detail(finish_rc);
            }
            if (quality != 0) {
                return P282_DETAIL_ROLE_WORKER_QUIESCENCE_UNPROVED;
            }
            parse_rc = p282_parse_role_result(&control, &role_result);
            if (parse_rc != 0) {
                return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
            }
            if (
                role_result.classification
                == P282_ROLE_PARENT_PM_NEGATIVE
            ) {
                return P282_DETAIL_PARENT_RUNTIME_PM_NEGATIVE;
            }
            if (
                role_result.classification
                == P282_ROLE_CHILD_PM_NEGATIVE
            ) {
                return P282_DETAIL_CHILD_RUNTIME_PM_NEGATIVE;
            }
            if (role_result.classification != P282_ROLE_COMPLETE) {
                return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
            }
            rc = p260_expect_value(p260_role_path, "peripheral");
            if (rc == 0) {
                p260_revalidate_or_fail(P260_ROLE_UDC_STAGE);
            }
            return rc;
        }

        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            record.result = -EIO;
            record_complete = 1;
        } else if (!p241_timespec_before(&now, &deadline)) {
            if (!child_reaped) {
                (void)sys_kill(pid, SIGKILL);
            }
            if (
                record_malformed
                || snapshot_rc != 0
                || parse_rc != 0
            ) {
                p282_fail_role_trace(
                    &control,
                    pipe_fds[0],
                    P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                    0);
            }
            (void)sys_close(pipe_fds[0]);
            long detail = P282_DETAIL_ROLE_WRITE_PRE_START_TIMEOUT;
            if (role_result.classification == P282_ROLE_START_NO_RETURN) {
                detail = P282_DETAIL_PARENT_START_NO_RETURN;
            } else if (
                role_result.classification >= P282_ROLE_COMPLETE
                || (record_complete && record.result == 0)
            ) {
                detail = P282_DETAIL_ROLE_WRITE_RETURNED_NO_START;
            }
            p282_trace_deadline_disable(&control);
            fail_at(P260_ROLE_UDC_STAGE, 0U, detail);
        }
        p282_poll_delay();
    }
}

struct p282_cycle_context {
    struct p282_trace_control trace;
    struct p282_cycle_trace_result observed;
    unsigned int warning_condition;
    uint8_t armed;
    uint8_t trace_authoritative;
    uint8_t stop_power_off_zero;
};

static long p260_write_banner(int tty_fd) {
    return p260_write_all(
        tty_fd, p260_banner, sizeof(p260_banner) - 1U, 1);
}

static long p282_deadline_after(
    long seconds,
    struct timespec64 *deadline) {
    long rc = p241_clock_gettime(deadline);
    if (rc == 0) {
        deadline->tv_sec += seconds;
    }
    return rc;
}

static int p282_deadline_expired(const struct timespec64 *deadline) {
    struct timespec64 now = {0};
    return p241_clock_gettime(&now) != 0
        || !p241_timespec_before(&now, deadline);
}

static const char *p282_cycle_role_payload(
    uint16_t operation,
    size_t *length) {
    if (operation == P282_HELPER_OPERATION_NONE_WRITE) {
        static const char value[] = P282_ROLE_NONE_WRITE;
        *length = sizeof(value) - 1U;
        return value;
    } else if (operation == P282_HELPER_OPERATION_PERIPHERAL_WRITE) {
        static const char value[] = P282_ROLE_PERIPHERAL_WRITE;
        *length = sizeof(value) - 1U;
        return value;
    }
    *length = 0;
    return NULL;
}

static long p282_cycle_role_write_once(
    uint16_t operation,
    uint32_t *byte_count) {
    size_t length = 0;
    const char *payload = p282_cycle_role_payload(operation, &length);
    if (payload == NULL) {
        return -EINVAL;
    }
    *byte_count = 0;
    long fd = sys_openat(P282_PARENT_MODE_PATH, O_RDWR | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long amount = sys_write((int)fd, payload, length);
    if (amount > 0) {
        *byte_count = (uint32_t)amount;
    }
    long close_rc = sys_close((int)fd);
    if (amount != (long)length) {
        return amount < 0 ? amount : -EIO;
    }
    return close_rc;
}

static __attribute__((noreturn)) void p282_cycle_role_child(
    int pipe_fd,
    int unrelated_fd,
    uint16_t operation) {
    if (unrelated_fd >= 0 && unrelated_fd != pipe_fd) {
        (void)sys_close(unrelated_fd);
    }
    struct p282_helper_record record = {
        .magic = P282_HELPER_MAGIC,
        .version = P282_HELPER_VERSION,
        .operation = operation,
    };
    record.result = p282_cycle_role_write_once(
        operation, &record.byte_count);
    long amount = sys_write(pipe_fd, &record, sizeof(record));
    (void)sys_close(pipe_fd);
    sys_exit(amount == (long)sizeof(record) ? 0 : 2);
}

static long p282_validate_cycle_helper_record(
    const struct p282_helper_record *record,
    uint16_t operation) {
    size_t expected_count = 0;
    const char *payload = p282_cycle_role_payload(
        operation, &expected_count);
    if (
        payload == NULL
        ||
        record->magic != P282_HELPER_MAGIC
        || record->version != P282_HELPER_VERSION
        || record->operation != operation
        || record->reserved != 0U
        || record->result > 0
        || expected_count > UINT32_MAX
    ) {
        return P282_CONTROL_HELPER_SOURCE_CONTRADICTION;
    }
    if (
        (record->result == 0 && record->byte_count != expected_count)
        || (record->result < 0 && record->byte_count != 0U)
    ) {
        return P282_CONTROL_HELPER_SOURCE_CONTRADICTION;
    }
    return 0;
}

static long p286_run_cycle_role_helper(
    uint16_t operation,
    int unrelated_fd,
    const struct timespec64 *deadline,
    struct p286_helper_observation *observation) {
    *observation = (struct p286_helper_observation){0};
    int pipe_fds[2] = {-1, -1};
    long rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);
    if (rc != 0) {
        observation->result = (int)rc;
        return 0;
    }
    long pid = sys_clone();
    if (pid < 0) {
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        observation->result = (int)pid;
        return 0;
    }
    if (pid == 0) {
        (void)sys_close(pipe_fds[0]);
        p282_cycle_role_child(pipe_fds[1], unrelated_fd, operation);
    }
    (void)sys_close(pipe_fds[1]);
    observation->dispatched = 1;

    struct p282_helper_record record = {0};
    size_t record_bytes = 0;
    int child_status = 0;
    int child_reaped = 0;
    int malformed = 0;
    for (;;) {
        if (record_bytes < sizeof(record)) {
            long amount = sys_read(
                pipe_fds[0],
                (uint8_t *)&record + record_bytes,
                sizeof(record) - record_bytes);
            if (amount > 0) {
                if ((size_t)amount > sizeof(record) - record_bytes) {
                    malformed = 1;
                } else {
                    record_bytes += (size_t)amount;
                }
            } else if (amount == 0 && child_reaped) {
                malformed = record_bytes != sizeof(record);
            } else if (
                amount < 0
                && amount != -EAGAIN
                && amount != -P260_EINTR
            ) {
                malformed = 1;
            }
        }
        if (!child_reaped) {
            long waited = sys_wait4(pid, &child_status, WNOHANG);
            if (waited == pid) {
                child_reaped = 1;
            } else if (waited < 0 && waited != -P260_EINTR) {
                malformed = 1;
                child_reaped = 1;
            }
        }
        if (child_reaped && record_bytes == sizeof(record)) {
            uint8_t extra = 0;
            long amount = sys_read(pipe_fds[0], &extra, 1U);
            if (amount != 0 || child_status != 0) {
                malformed = 1;
            }
            break;
        }
        if (malformed || p282_deadline_expired(deadline)) {
            observation->timed_out = !malformed;
            if (!child_reaped) {
                (void)sys_kill(pid, SIGKILL);
                struct timespec64 reap_deadline = {0};
                if (p241_clock_gettime(&reap_deadline) != 0) {
                    observation->unreaped = 1;
                } else {
                    reap_deadline.tv_sec +=
                        P286_REAP_DEADLINE_MSEC / 1000;
                    reap_deadline.tv_nsec +=
                        (P286_REAP_DEADLINE_MSEC % 1000) * 1000000LL;
                    if (reap_deadline.tv_nsec >= 1000000000LL) {
                        reap_deadline.tv_sec += 1;
                        reap_deadline.tv_nsec -= 1000000000LL;
                    }
                    while (!p282_deadline_expired(&reap_deadline)) {
                        long waited = sys_wait4(
                            pid, &child_status, WNOHANG);
                        if (waited == pid) {
                            child_reaped = 1;
                            break;
                        }
                        if (
                            waited < 0
                            && waited != -P260_EINTR
                        ) {
                            malformed = 1;
                            break;
                        }
                        p282_poll_delay();
                    }
                    if (!child_reaped) {
                        observation->unreaped = 1;
                    }
                }
            }
            (void)sys_close(pipe_fds[0]);
            observation->malformed = malformed;
            return 0;
        }
        p282_poll_delay();
    }
    (void)sys_close(pipe_fds[0]);
    rc = p282_validate_cycle_helper_record(&record, operation);
    if (rc != 0) {
        observation->malformed = 1;
        return 0;
    }
    observation->record_complete = 1;
    observation->result = (int)record.result;
    observation->write_completed = (
        record.result == 0
        && record.byte_count != 0U
    );
    return 0;
}

static long p282_wait_exact_value(
    const char *path,
    const char *expected,
    const struct timespec64 *deadline,
    int *matched) {
    *matched = 0;
    for (;;) {
        long rc = p260_expect_value(path, expected);
        if (rc == 0) {
            *matched = 1;
            return 0;
        }
        if (
            rc != -ENOENT
            && rc != -ENODEV
            && rc != -EIO
        ) {
            return rc;
        }
        if (p282_deadline_expired(deadline)) {
            return 0;
        }
        p282_poll_delay();
    }
}

static __attribute__((noreturn)) void p282_fail_classification(
    const struct p282_classification *classification) {
    if (
        classification == NULL
        || classification->outcome != P282_OUTCOME_FAILURE
    ) {
        quiet_park();
    }
    fail_at(
        (uint8_t)classification->stage,
        0U,
        (long)classification->detail);
}

static void p282_publish_classification(
    uint8_t stage,
    int classified,
    const struct p282_classification *classification,
    uint16_t fallback_detail) {
    if (classified < 0) {
        quiet_park();
    }
    if (classified > 0) {
        if (classification->outcome == P282_OUTCOME_FAILURE) {
            p282_fail_classification(classification);
        }
        if (
            classification->outcome != P282_OUTCOME_PROGRESS
            || classification->stage != stage
        ) {
            quiet_park();
        }
        p282_progress(stage, (uint16_t)classification->detail);
        return;
    }
    p282_progress(stage, fallback_detail);
}

static int p282_control_classification(
    uint8_t stage,
    unsigned int condition,
    struct p282_classification *classification) {
    return p282_classify_cycle_control(stage, condition, classification);
}

static void p282_set_cycle_warning(
    struct p282_cycle_context *cycle,
    uint8_t stage,
    unsigned int condition) {
    struct p282_classification classification = {0};
    int classified = p282_control_classification(
        stage, condition, &classification);
    if (
        classified <= 0
        || classification.outcome != P282_OUTCOME_PROGRESS
    ) {
        if (
            classified > 0
            && classification.outcome == P282_OUTCOME_FAILURE
        ) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }
    if (cycle->warning_condition == P282_CONTROL_NONE) {
        cycle->warning_condition = condition;
    }
    cycle->trace_authoritative = 0;
}

static uint16_t p282_cycle_warning_detail(
    const struct p282_cycle_context *cycle,
    uint8_t stage) {
    if (cycle->warning_condition == P282_CONTROL_NONE) {
        return 0;
    }
    struct p282_classification classification = {0};
    int classified = p282_control_classification(
        stage, cycle->warning_condition, &classification);
    if (
        classified <= 0
        || classification.outcome != P282_OUTCOME_PROGRESS
    ) {
        quiet_park();
    }
    return (uint16_t)classification.detail;
}

static __attribute__((noreturn)) void p282_cycle_abort(
    struct p282_cycle_context *cycle,
    uint8_t stage,
    long detail) {
    if (cycle->armed) {
        long quality = 0;
        long finish_rc = p282_trace_finish(&cycle->trace, &quality);
        cycle->armed = 0;
        if (finish_rc != 0) {
            struct p282_classification classification = {0};
            int classified = p282_control_classification(
                P282_STAGE_RESTART,
                P282_CONTROL_TRACE_CLEANUP_UNVERIFIED,
                &classification);
            if (classified > 0) {
                p282_fail_classification(&classification);
            }
            quiet_park();
        }
    }
    fail_at(stage, 0U, detail);
}

static __attribute__((noreturn)) void p282_cycle_abort_condition(
    struct p282_cycle_context *cycle,
    uint8_t stage,
    unsigned int condition) {
    struct p282_classification classification = {0};
    int classified = p282_control_classification(
        stage, condition, &classification);
    if (
        classified <= 0
        || classification.outcome != P282_OUTCOME_FAILURE
    ) {
        quiet_park();
    }
    p282_cycle_abort(cycle, stage, (long)classification.detail);
}

static long p282_cycle_refresh(
    struct p282_cycle_context *cycle,
    uint8_t stage) {
    if (!cycle->armed || !cycle->trace_authoritative) {
        return 0;
    }
    long rc = p282_trace_read_snapshot(&cycle->trace, 0);
    if (rc == 0) {
        rc = p282_parse_cycle_result(
            &cycle->trace, &cycle->observed);
    }
    if (rc != 0) {
        p282_set_cycle_warning(
            cycle, stage, P282_CONTROL_TRACE_INCOMPLETE);
    }
    return 0;
}

static long p282_cycle_finish(
    struct p282_cycle_context *cycle,
    struct p282_cycle_trace_result *final_result) {
    *final_result = cycle->observed;
    if (!cycle->armed) {
        return 0;
    }
    long quality = 0;
    long finish_rc = p282_trace_finish(&cycle->trace, &quality);
    cycle->armed = 0;
    if (finish_rc != 0) {
        return P282_CONTROL_TRACE_CLEANUP_UNVERIFIED;
    }
    if (quality != 0) {
        p282_set_cycle_warning(
            cycle,
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_INCOMPLETE);
        return 0;
    }
    long parse_rc = p282_parse_cycle_result(
        &cycle->trace, final_result);
    return parse_rc == 0
        ? 0
        : P282_CONTROL_TRACE_SOURCE_CONTRADICTION;
}

static long p282_exact_udc_present(void) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(P282_EXACT_UDC_PATH, &value, 0);
    if (rc != 0) {
        return rc;
    }
    return p241_check_gate(S22_P258_UDC_GATE_INDEX);
}

static long p282_wait_exact_udc(
    const struct timespec64 *deadline,
    int *matched) {
    *matched = 0;
    for (;;) {
        long rc = p282_exact_udc_present();
        if (rc == 0) {
            *matched = 1;
            return 0;
        }
        if (rc != -ENOENT && rc != -ENODEV) {
            return rc;
        }
        if (p282_deadline_expired(deadline)) {
            return 0;
        }
        p282_poll_delay();
    }
}

static long p282_cycle_stop(
    struct p282_cycle_context *cycle,
    int unrelated_fd,
    const struct timespec64 *deadline) {
    struct p286_helper_observation helper = {0};
    long rc = p286_run_cycle_role_helper(
        P282_HELPER_OPERATION_NONE_WRITE,
        unrelated_fd,
        deadline,
        &helper);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_STOP, rc);
    }
    if (cycle->trace_authoritative) {
        (void)p282_cycle_refresh(cycle, P282_STAGE_STOP);
    }
    helper.start_entered = cycle->observed.stop_worker.entered;
    helper.start_returned = cycle->observed.stop_worker.returned;
    helper.outer_open = cycle->observed.outer_open;
    struct p282_classification helper_classification = {0};
    int helper_classified = p286_classify_helper(
        P282_STAGE_STOP, &helper, &helper_classification);
    if (helper_classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_STOP,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (helper_classified > 0) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_STOP,
            (long)helper_classification.detail);
    }

    int none_readback = 0;
    rc = p282_wait_exact_value(
        P282_PARENT_MODE_PATH,
        P282_ROLE_NONE_READBACK,
        deadline,
        &none_readback);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_STOP, rc);
    }
    if (cycle->trace_authoritative) {
        do {
            (void)p282_cycle_refresh(cycle, P282_STAGE_STOP);
            if (
                !cycle->trace_authoritative
                || cycle->observed.stop_worker.returned
            ) {
                break;
            }
            p282_poll_delay();
        } while (!p282_deadline_expired(deadline));
    }

    struct p282_stop_observation observation = {
        .none_readback = (unsigned int)none_readback,
        .trace_authoritative = cycle->trace_authoritative,
        .worker_entered = cycle->observed.stop_worker.entered,
        .worker_returned = cycle->observed.stop_worker.returned,
        .worker_rc = cycle->observed.stop_worker.rc,
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_stop(
        &observation, &classification);
    if (classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_STOP,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    p282_publish_classification(
        P282_STAGE_STOP,
        classified,
        &classification,
        p282_cycle_warning_detail(cycle, P282_STAGE_STOP));
    return 0;
}

static long p282_cycle_suspend(
    struct p282_cycle_context *cycle,
    const struct timespec64 *deadline) {
    int status_suspended = 0;
    long rc = p282_wait_exact_value(
        P282_CHILD_RUNTIME_STATUS_PATH,
        P282_CHILD_SUSPENDED_READBACK,
        deadline,
        &status_suspended);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_SUSPENDED, rc);
    }
    if (cycle->trace_authoritative) {
        (void)p282_cycle_refresh(cycle, P282_STAGE_SUSPENDED);
    }
    struct p282_suspend_observation observation = {
        .trace_authoritative = cycle->trace_authoritative,
        .suspend_entered = cycle->observed.child_suspend.entered,
        .suspend_returned = cycle->observed.child_suspend.returned,
        .suspend_rc = cycle->observed.child_suspend.rc,
        .status_suspended = (unsigned int)status_suspended,
        .power_off_entered = cycle->observed.power_off.entered,
        .power_off_returned = cycle->observed.power_off.returned,
        .power_off_rc = cycle->observed.power_off.rc,
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_suspend(
        &observation, &classification);
    if (
        cycle->trace_authoritative
        && observation.power_off_returned
        && observation.power_off_rc == 0
    ) {
        cycle->stop_power_off_zero = 1;
    }
    if (classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_SUSPENDED,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (
        classified > 0
        && classification.outcome == P282_OUTCOME_FAILURE
    ) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_SUSPENDED,
            (long)classification.detail);
    }

    int parent_suspended = 0;
    long parent_rc = p282_wait_exact_value(
        P286_PARENT_RUNTIME_STATUS_PATH,
        P286_PARENT_SUSPENDED_READBACK,
        deadline,
        &parent_suspended);
    struct p282_classification parent_classification = {0};
    int parent_classified = p286_classify_parent_status(
        (unsigned int)parent_suspended,
        (int)parent_rc,
        &parent_classification);
    if (parent_classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_SUSPENDED,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (parent_classified > 0) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_SUSPENDED,
            (long)parent_classification.detail);
    }
    p282_publish_classification(
        P282_STAGE_SUSPENDED,
        classified,
        &classification,
        p282_cycle_warning_detail(cycle, P282_STAGE_SUSPENDED));
    return 0;
}

static void p282_restart_exact_failure(
    struct p282_cycle_context *cycle,
    unsigned int detail,
    unsigned int stage_mask) {
    struct p282_classification classification = {0};
    int classified = p282_emit(
        &classification,
        P282_STAGE_RESTART,
        P282_OUTCOME_FAILURE,
        detail,
        stage_mask);
    if (classified <= 0) {
        quiet_park();
    }
    p282_cycle_abort(
        cycle,
        P282_STAGE_RESTART,
        (long)classification.detail);
}

static unsigned int p282_cycle_restart(
    struct p282_cycle_context *cycle,
    int unrelated_fd) {
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(
        P282_CYCLE_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (cycle->trace_authoritative) {
        (void)p282_cycle_refresh(cycle, P282_STAGE_RESTART);
    }
    unsigned int residual_outer_open = cycle->observed.outer_open;
    struct p286_helper_observation helper = {0};
    rc = p286_run_cycle_role_helper(
        P282_HELPER_OPERATION_PERIPHERAL_WRITE,
        unrelated_fd,
        &deadline,
        &helper);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (cycle->trace_authoritative) {
        (void)p282_cycle_refresh(cycle, P282_STAGE_RESTART);
    }
    helper.start_entered = cycle->observed.restart_worker.entered;
    helper.start_returned = cycle->observed.restart_worker.returned;
    helper.outer_open = residual_outer_open;
    struct p282_classification helper_classification = {0};
    int helper_classified = p286_classify_helper(
        P282_STAGE_RESTART, &helper, &helper_classification);
    if (helper_classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (helper_classified > 0) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_RESTART,
            (long)helper_classification.detail);
    }

    int status_active = 0;
    int mode_peripheral = 0;
    int exact_udc = 0;
    rc = p282_wait_exact_value(
        P282_CHILD_RUNTIME_STATUS_PATH,
        P282_CHILD_ACTIVE_READBACK,
        &deadline,
        &status_active);
    if (rc == 0) {
        rc = p282_wait_exact_value(
            P282_PARENT_MODE_PATH,
            P282_ROLE_PERIPHERAL_READBACK,
            &deadline,
            &mode_peripheral);
    }
    if (rc == 0) {
        rc = p282_wait_exact_udc(&deadline, &exact_udc);
    }
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (cycle->trace_authoritative) {
        do {
            (void)p282_cycle_refresh(cycle, P282_STAGE_RESTART);
            if (
                !cycle->trace_authoritative
                || cycle->observed.restart_worker.returned
            ) {
                break;
            }
            p282_poll_delay();
        } while (!p282_deadline_expired(&deadline));
    }

    struct p282_cycle_trace_result final_result = cycle->observed;
    long finish_rc = p282_cycle_finish(cycle, &final_result);
    if (finish_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        struct p282_classification classification = {0};
        int classified = p282_control_classification(
            P282_STAGE_RESTART,
            (unsigned int)finish_rc,
            &classification);
        if (classified > 0) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }
    if (finish_rc == P282_CONTROL_TRACE_SOURCE_CONTRADICTION) {
        struct p282_classification classification = {0};
        int classified = p282_control_classification(
            P282_STAGE_RESTART,
            (unsigned int)finish_rc,
            &classification);
        if (classified > 0) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }
    cycle->observed = final_result;

    if (!status_active) {
        p282_restart_exact_failure(
            cycle,
            P282_DETAIL_CHILD_STATUS_NOT_ACTIVE,
            P282_DETAIL_CHILD_STATUS_NOT_ACTIVE_STAGE_MASK);
    }
    if (!mode_peripheral) {
        struct p282_classification readback_classification = {0};
        int readback_classified = p286_classify_peripheral_readback(
            helper.write_completed,
            (unsigned int)mode_peripheral,
            &readback_classification);
        if (readback_classified <= 0) {
            p282_cycle_abort_condition(
                cycle,
                P282_STAGE_RESTART,
                P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
        }
        p282_cycle_abort(
            cycle,
            P282_STAGE_RESTART,
            (long)readback_classification.detail);
    }
    if (!exact_udc) {
        p282_restart_exact_failure(
            cycle,
            P282_DETAIL_EXACT_UDC_REGRESSION_AFTER_RESTART,
            P282_DETAIL_EXACT_UDC_REGRESSION_AFTER_RESTART_STAGE_MASK);
    }

    struct p282_restart_observation observation = {
        .peripheral_readback = (unsigned int)mode_peripheral,
        .trace_authoritative = cycle->trace_authoritative,
        .worker_entered = final_result.restart_worker.entered,
        .worker_returned = final_result.restart_worker.returned,
        .worker_rc = final_result.restart_worker.rc,
        .resume_entered = final_result.child_resume.entered,
        .resume_returned = final_result.child_resume.returned,
        .resume_rc = final_result.child_resume.rc,
        .init_entered = final_result.phy_init.entered,
        .init_returned = final_result.phy_init.returned,
        .init_rc = final_result.phy_init.rc,
        .power_on_entered = final_result.power_on.entered,
        .power_on_returned = final_result.power_on.returned,
        .power_on_rc = final_result.power_on.rc,
        .notify_connect = final_result.notify_connect.entered,
        .status_active = (unsigned int)status_active,
        .mode_peripheral = (unsigned int)mode_peripheral,
        .exact_udc = (unsigned int)exact_udc,
        .off_on_zero_pair = (
            cycle->stop_power_off_zero
            && final_result.power_on.returned
            && final_result.power_on.rc == 0
        ),
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_restart(
        &observation, &classification);
    unsigned int repair_class = P282_REPAIR_DIAGNOSTIC_DEGRADED;
    if (cycle->trace_authoritative) {
        repair_class = observation.off_on_zero_pair
            ? P282_REPAIR_POWER_HELPER_OFF_ON_ZERO
            : P282_REPAIR_SOFTWARE_REINIT;
    }
    if (classified < 0) {
        struct p282_classification contradiction = {0};
        int contradiction_rc = p282_control_classification(
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION,
            &contradiction);
        if (contradiction_rc > 0) {
            p282_fail_classification(&contradiction);
        }
        quiet_park();
    }
    p282_publish_classification(
        P282_STAGE_RESTART,
        classified,
        &classification,
        p282_cycle_warning_detail(cycle, P282_STAGE_RESTART));
    return repair_class;
}

static unsigned int p282_phase_bind(unsigned int repair_class) {
    struct p282_trace_control control;
    long setup_rc = p282_trace_setup(P282_PHASE_BIND, &control);
    int armed = setup_rc == 0;
    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        struct p282_bind_observation observation = {
            .cleanup_verified = 0,
        };
        struct p282_classification classification = {0};
        int classified = p282_classify_bind(
            &observation, &classification);
        if (classified > 0) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }

    long bind_rc = p260_bind_udc();
    long quality = 0;
    long finish_rc = armed
        ? p282_trace_finish(&control, &quality)
        : 0;
    if (finish_rc != 0) {
        struct p282_bind_observation observation = {
            .cleanup_verified = 0,
        };
        struct p282_classification classification = {0};
        int classified = p282_classify_bind(
            &observation, &classification);
        if (classified > 0) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }
    if (bind_rc != 0) {
        fail_at(P282_STAGE_BIND, 0U, bind_rc);
    }

    struct p282_bind_trace_result trace_result = {
        .source_consistent = 1,
        .branch = P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    int trace_authoritative = armed && quality == 0;
    if (trace_authoritative) {
        long parse_rc = p282_parse_bind_result(
            &control, &trace_result);
        if (parse_rc != 0) {
            trace_result.source_consistent = 0;
        }
    }
    struct p282_bind_observation observation = {
        .cleanup_verified = 1,
        .source_consistent = trace_result.source_consistent,
        .trace_authoritative = (unsigned int)trace_authoritative,
        .pullup_returned_zero = trace_authoritative
            ? trace_result.pullup_returned_zero
            : 1U,
        .run_stop_seen = trace_result.run_stop_seen,
        .run_stop_rc = trace_result.run_stop_rc,
        .repair_class = repair_class,
        .bind_branch = trace_authoritative
            ? trace_result.branch
            : P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_bind(
        &observation, &classification);
    if (classified < 0) {
        observation.source_consistent = 0;
        classified = p282_classify_bind(
            &observation, &classification);
    }
    p282_publish_classification(
        P282_STAGE_BIND, classified, &classification, 0);
    return observation.bind_branch;
}

static long p282_parse_canonical(
    const char *value,
    size_t length,
    const char *const *table,
    size_t table_count,
    unsigned int *index) {
    for (size_t candidate = 0; candidate < table_count; ++candidate) {
        size_t expected_length = cstr_len(table[candidate]);
        if (
            length == expected_length
            && p260_bytes_equal(value, table[candidate], length)
        ) {
            *index = (unsigned int)candidate;
            return 0;
        }
    }
    return -P260_EPROTO;
}

static long p282_read_final_pair(
    unsigned int *state,
    unsigned int *speed) {
    char state_value[32];
    char speed_value[32];
    size_t state_length = 0;
    size_t speed_length = 0;
    long rc = p260_read_value(
        P282_UDC_STATE_PATH,
        state_value,
        sizeof(state_value),
        &state_length);
    if (rc == 0) {
        rc = p260_read_value(
            P282_UDC_SPEED_PATH,
            speed_value,
            sizeof(speed_value),
            &speed_length);
    }
    if (rc == 0) {
        rc = p282_parse_canonical(
            state_value,
            state_length,
            p282_descriptor_udc_states,
            sizeof(p282_descriptor_udc_states)
                / sizeof(p282_descriptor_udc_states[0]),
            state);
    }
    if (rc == 0) {
        rc = p282_parse_canonical(
            speed_value,
            speed_length,
            p282_descriptor_usb_speeds,
            sizeof(p282_descriptor_usb_speeds)
                / sizeof(p282_descriptor_usb_speeds[0]),
            speed);
    }
    return rc;
}

static void p282_wait_final_pair(
    unsigned int repair_class,
    unsigned int bind_branch) {
    _Static_assert(
        sizeof(p282_descriptor_udc_states)
                / sizeof(p282_descriptor_udc_states[0])
            == P282_STATE_COUNT,
        "P2.82 generated UDC state table cardinality");
    _Static_assert(
        sizeof(p282_descriptor_usb_speeds)
                / sizeof(p282_descriptor_usb_speeds[0])
            == P282_SPEED_COUNT,
        "P2.82 generated USB speed table cardinality");

    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(
        P282_FINAL_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        fail_at(P282_STAGE_FINAL, 0U, rc);
    }
    unsigned int previous_state = 0;
    unsigned int previous_speed = 0;
    unsigned int current_state = 0;
    unsigned int current_speed = 0;
    int have_previous = 0;
    for (;;) {
        p260_revalidate_or_fail(P282_STAGE_FINAL);
        rc = p282_read_final_pair(&current_state, &current_speed);
        p260_revalidate_or_fail(P282_STAGE_FINAL);
        if (rc != 0) {
            fail_at(P282_STAGE_FINAL, 0U, rc);
        }
        int stable = have_previous
            && previous_state == current_state
            && previous_speed == current_speed;
        int configured_high = (
            current_state == P282_STATE_CONFIGURED
            && current_speed == P282_SPEED_HIGH
        );
        if (
            (stable && configured_high)
            || p282_deadline_expired(&deadline)
        ) {
            if (!have_previous) {
                struct p282_classification classification = {0};
                int classified = p282_emit(
                    &classification,
                    P282_STAGE_FINAL,
                    P282_OUTCOME_FAILURE,
                    P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE,
                    P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE_STAGE_MASK);
                p282_publish_classification(
                    P282_STAGE_FINAL,
                    classified,
                    &classification,
                    0);
                return;
            }
            struct p282_final_pair_observation observation = {
                .first_state = previous_state,
                .first_speed = previous_speed,
                .second_state = current_state,
                .second_speed = current_speed,
                .repair_class = repair_class,
                .bind_branch = bind_branch,
            };
            struct p282_classification classification = {0};
            int classified = p282_classify_final_pair(
                &observation, &classification);
            if (classified < 0) {
                fail_at(P282_STAGE_FINAL, 0U, -P260_EPROTO);
            }
            p282_publish_classification(
                P282_STAGE_FINAL,
                classified,
                &classification,
                0);
            return;
        }
        previous_state = current_state;
        previous_speed = current_speed;
        have_previous = 1;
        p282_poll_delay();
    }
}

static __attribute__((noreturn)) void p286_e3_run(void) {
    p260_derive_identity();

    long rc = p260_mount_configfs();
    if (rc != 0) {
        fail_at(P260_CONFIG_STAGE, 0U, rc);
    }
    p260_progress(P260_CONFIG_STAGE);

    rc = p260_create_gadget();
    if (rc != 0) {
        fail_at(P260_GADGET_STAGE, 0U, rc);
    }
    p260_progress(P260_GADGET_STAGE);

    unsigned int major_number = 0;
    unsigned int minor_number = 0;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) {
        fail_at(P260_TTY_CLASS_STAGE, 0U, rc);
    }
    p260_progress(P260_TTY_CLASS_STAGE);

    rc = p260_prepare_tty_node(major_number, minor_number);
    int tty_fd = -1;
    if (rc == 0) {
        rc = p260_open_raw_tty(&tty_fd);
    }
    if (rc != 0) {
        fail_at(P260_TTY_RAW_STAGE, 0U, rc);
    }
    p260_progress(P260_TTY_RAW_STAGE);

    rc = p260_write_banner(tty_fd);
    if (rc != 0) {
        fail_at(P260_BANNER_STAGE, 0U, rc);
    }
    p260_progress(P260_BANNER_STAGE);

    uint16_t warning = 0;
    rc = p282_phase_role(&warning, tty_fd);
    if (rc != 0) {
        fail_at(P282_STAGE_ROLE_UDC, 0U, rc);
    }
    p282_progress(P282_STAGE_ROLE_UDC, warning);

    struct p282_cycle_context cycle = {
        .trace_authoritative = 1,
    };
    long setup_rc = p282_trace_setup(P282_PHASE_CYCLE, &cycle.trace);
    if (setup_rc == 0) {
        cycle.armed = 1;
    } else if (
        setup_rc == P282_CONTROL_TRACE_CONTROL_UNAVAILABLE
        || setup_rc == P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE
    ) {
        p282_set_cycle_warning(
            &cycle, P282_STAGE_STOP, (unsigned int)setup_rc);
    } else {
        struct p282_classification classification = {0};
        int classified = p282_control_classification(
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_CLEANUP_UNVERIFIED,
            &classification);
        if (classified > 0) {
            p282_fail_classification(&classification);
        }
        quiet_park();
    }

    struct timespec64 stop_deadline = {0};
    rc = p282_deadline_after(
        P282_CYCLE_DEADLINE_SEC, &stop_deadline);
    if (rc != 0) {
        p282_cycle_abort(&cycle, P282_STAGE_STOP, rc);
    }
    (void)p282_cycle_stop(&cycle, tty_fd, &stop_deadline);
    (void)p282_cycle_suspend(&cycle, &stop_deadline);
    unsigned int repair_class = p282_cycle_restart(&cycle, tty_fd);
    unsigned int bind_branch = p282_phase_bind(repair_class);
    p282_wait_final_pair(repair_class, bind_branch);

    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {
        quiet_park();
    }
    quiet_park();
}
