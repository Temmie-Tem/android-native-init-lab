/* P2.80 parent-worker and pull-up discriminator over the P2.60 E3 path. */

#include "s22plus_fyg8_p260_e3_runtime.inc.c"
#include "s22plus_fyg8_p280_trace_descriptor.h"

#define P280_NR_UNLINKAT 35
#define P280_NR_UMOUNT2 39
#define P280_AT_REMOVEDIR 0x200
#define P280_O_WRONLY 00000001
#define P280_O_TRUNC 00001000
#define P280_S_IFREG 0100000
#define P280_TRACEFS_MAGIC 0x74726163L
#define P280_TRACE_CAPACITY 65536U
#define P280_PROFILE_CAPACITY 65536U
#define P280_DEFINITIONS_CAPACITY 32768U
#define P280_PATH_CAPACITY 256U
#define P280_RECORD_CAPACITY 64U
#define P280_HELPER_MAGIC 0x50323830U
#define P280_HELPER_VERSION 1U
#define P280_HELPER_OPERATION_ROLE_WRITE 1U

static const char p280_trace_root[] = "/sys/kernel/tracing";
static const char p280_instance_root[] =
    "/sys/kernel/tracing/instances/p280";
static const char p280_global_group_root[] =
    "/sys/kernel/tracing/events/p280";
static const char p280_global_events_path[] =
    "/sys/kernel/tracing/kprobe_events";
static const char p280_profile_path[] =
    "/sys/kernel/tracing/kprobe_profile";

static char p280_trace_buffer[P280_TRACE_CAPACITY];
static char p280_profile_buffer[P280_PROFILE_CAPACITY];
static char p280_definitions_buffer[P280_DEFINITIONS_CAPACITY];
static size_t p280_trace_length;
static size_t p280_profile_length;

extern long s22_r4w1e_checkpoint_progress_detail(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t stage,
    uint8_t item_index,
    uint16_t detail);

struct p280_trace_control {
    const struct p280_event_descriptor *events;
    size_t event_count;
    size_t registered_count;
    uint8_t mount_owned;
    uint8_t tracefs_ready;
    uint8_t instance_owned;
    uint8_t active;
};

struct p280_helper_record {
    uint32_t magic;
    uint16_t version;
    uint16_t operation;
    int64_t result;
    uint32_t byte_count;
    uint32_t reserved;
};

_Static_assert(
    sizeof(struct p280_helper_record) == 24U,
    "P2.80 helper record size");

static void (*const p280_p260_compat_anchor)(void)
    __attribute__((used)) = p260_e3_run;

static long p280_unlinkat(const char *path, int flags) {
    return syscall6(
        P280_NR_UNLINKAT,
        AT_FDCWD,
        (long)(uintptr_t)path,
        flags,
        0,
        0,
        0);
}

static long p280_umount2(const char *path, int flags) {
    return syscall6(
        P280_NR_UMOUNT2,
        (long)(uintptr_t)path,
        flags,
        0,
        0,
        0,
        0);
}

static int p280_is_digit(char value) {
    return value >= '0' && value <= '9';
}

static int p280_is_space(char value) {
    return value == ' ' || value == '\t';
}

static long p280_copy_path_part(
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

static long p280_make_path(
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
    long rc = p280_copy_path_part(output, capacity, &cursor, prefix);
    if (rc == 0) {
        rc = p280_copy_path_part(output, capacity, &cursor, name);
    }
    if (rc == 0) {
        rc = p280_copy_path_part(output, capacity, &cursor, suffix);
    }
    return rc;
}

static long p280_read_file(
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

static long p280_write_control(const char *path, const char *value) {
    long fd = sys_openat(path, P280_O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long rc = p260_write_all((int)fd, value, cstr_len(value), 0);
    long close_rc = sys_close((int)fd);
    return rc != 0 ? rc : close_rc;
}

static long p280_clear_trace(void) {
    long fd = sys_openat(
        "/sys/kernel/tracing/instances/p280/trace",
        P280_O_WRONLY | P280_O_TRUNC | O_CLOEXEC,
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

static long p280_path_absent(const char *path) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(path, &value, AT_SYMLINK_NOFOLLOW);
    if (rc == -ENOENT) {
        return 0;
    }
    return rc == 0 ? -EEXIST : rc;
}

static long p280_path_regular(const char *path) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(path, &value, AT_SYMLINK_NOFOLLOW);
    if (rc != 0) {
        return rc;
    }
    return (value.st_mode & S_IFMT) == P280_S_IFREG ? 0 : -EIO;
}

static const char *p280_find_bytes(
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

static size_t p280_count_bytes(
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

static long p280_event_path(
    char *path,
    size_t capacity,
    const char *name,
    const char *suffix) {
    return p280_make_path(
        path,
        capacity,
        "/sys/kernel/tracing/instances/p280/events/p280/",
        name,
        suffix);
}

static long p280_delete_event(const char *name) {
    char command[96];
    size_t cursor = 0;
    long rc = p280_copy_path_part(
        command, sizeof(command), &cursor, "-:p280/");
    if (rc == 0) {
        rc = p280_copy_path_part(
            command, sizeof(command), &cursor, name);
    }
    if (rc == 0) {
        rc = p280_copy_path_part(command, sizeof(command), &cursor, "\n");
    }
    return rc != 0 ? rc : p280_write_control(
        p280_global_events_path, command);
}

static long p280_trace_mount(struct p280_trace_control *control) {
    struct statfs_probe probe = {0};
    long rc = sys_statfs(p280_trace_root, &probe);
    if (rc == 0 && probe.f_type == P280_TRACEFS_MAGIC) {
        return 0;
    }
    rc = sys_mount(
        "tracefs",
        p280_trace_root,
        "tracefs",
        MS_NOSUID | MS_NODEV | MS_NOEXEC,
        "");
    if (rc != 0 && rc != -P260_EBUSY) {
        return rc;
    }
    control->mount_owned = rc == 0;
    probe.f_type = 0;
    rc = sys_statfs(p280_trace_root, &probe);
    return rc != 0
        ? rc
        : (probe.f_type == P280_TRACEFS_MAGIC ? 0 : -EIO);
}

static long p280_event_registration_state(
    const struct p280_trace_control *control,
    size_t index) {
    if (index >= control->event_count) {
        return -EINVAL;
    }
    size_t definitions_length = 0;
    long rc = p280_read_file(
        p280_global_events_path,
        p280_definitions_buffer,
        sizeof(p280_definitions_buffer),
        &definitions_length);
    if (rc != 0) {
        return rc;
    }
    char identity[96];
    size_t cursor = 0;
    rc = p280_copy_path_part(
        identity, sizeof(identity), &cursor, "p280/");
    if (rc == 0) {
        rc = p280_copy_path_part(
            identity,
            sizeof(identity),
            &cursor,
            control->events[index].name);
    }
    if (rc != 0) {
        return rc;
    }
    size_t identity_count = p280_count_bytes(
        p280_definitions_buffer,
        definitions_length,
        identity);
    if (identity_count == 0U) {
        return 0;
    }
    if (identity_count != 1U) {
        return -P260_EPROTO;
    }
    char path[P280_PATH_CAPACITY];
    rc = p280_event_path(
        path,
        sizeof(path),
        control->events[index].name,
        "/enable");
    if (rc != 0 || p280_path_regular(path) != 0) {
        return rc != 0 ? rc : -EIO;
    }
    return 1;
}

static long p280_verify_event_registration(
    const struct p280_trace_control *control) {
    for (size_t index = 0; index < control->event_count; ++index) {
        long rc = p280_event_registration_state(control, index);
        if (rc != 1) {
            return rc < 0 ? rc : -EIO;
        }
    }
    return 0;
}

static long p280_parse_unsigned(
    const char *start,
    const char *end,
    uint64_t *result);

static long p280_verify_buffer_size(void) {
    char value[128];
    size_t length = 0;
    long rc = p260_read_value(
        "/sys/kernel/tracing/instances/p280/buffer_size_kb",
        value,
        sizeof(value),
        &length);
    uint64_t actual = 0;
    if (rc == 0) {
        rc = p280_parse_unsigned(value, value + length, &actual);
    }
    if (
        rc != 0
        || actual < P280_TRACE_BUFFER_KB
        || actual > P280_TRACE_BUFFER_KB * 2U
    ) {
        return rc != 0 ? rc : -EIO;
    }
    return 0;
}

static long p280_verify_control_readback(
    const struct p280_trace_control *control) {
    char value[4096];
    size_t length = 0;
    long rc = p280_read_file(
        "/sys/kernel/tracing/instances/p280/trace_clock",
        value,
        sizeof(value),
        &length);
    if (
        rc != 0
        || p280_find_bytes(value, length, "[counter]") == NULL
    ) {
        return rc != 0 ? rc : -EIO;
    }
    rc = p280_verify_buffer_size();
    if (rc != 0) {
        return rc;
    }
    for (size_t index = 0; index < control->event_count; ++index) {
        char path[P280_PATH_CAPACITY];
        rc = p280_event_path(
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

static long p280_trace_cleanup(struct p280_trace_control *control) {
    long result = 0;
    size_t registered = control->registered_count;
    int verify_instance_absent = control->instance_owned;
    if (control->active) {
        long rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/tracing_on", "0\n");
        if (rc == 0) {
            rc = p280_write_control(
                "/sys/kernel/tracing/instances/p280/events/p280/enable",
                "0\n");
        }
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->active = 0;
    }
    while (control->registered_count != 0U) {
        size_t index = control->registered_count - 1U;
        (void)p280_delete_event(control->events[index].name);
        --control->registered_count;
    }
    size_t definitions_length = 0;
    if (registered != 0U && !control->tracefs_ready && result == 0) {
        result = -EIO;
    }
    if (control->tracefs_ready && registered != 0U) {
        long read_rc = p280_read_file(
            p280_global_events_path,
            p280_definitions_buffer,
            sizeof(p280_definitions_buffer),
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
            long rc = p280_copy_path_part(
                identity, sizeof(identity), &cursor, "p280/");
            if (rc == 0) {
                rc = p280_copy_path_part(
                    identity,
                    sizeof(identity),
                    &cursor,
                    control->events[index].name);
            }
            if (
                rc != 0
                || p280_find_bytes(
                    p280_definitions_buffer,
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
        long rc = p280_unlinkat(p280_instance_root, P280_AT_REMOVEDIR);
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->instance_owned = 0;
    }
    if (
        verify_instance_absent
        && p280_path_absent(p280_instance_root) != 0
        && result == 0
    ) {
        result = -EIO;
    }
    if (control->mount_owned) {
        long rc = p280_umount2(p280_trace_root, 0);
        if (rc != 0 && result == 0) {
            result = rc;
        }
        control->mount_owned = 0;
        struct statfs_probe probe = {0};
        rc = sys_statfs(p280_trace_root, &probe);
        if (
            rc == 0
            && probe.f_type == P280_TRACEFS_MAGIC
            && result == 0
        ) {
            result = -EIO;
        }
    }
    control->tracefs_ready = 0;
    return result;
}

static long p280_trace_setup(
    struct p280_trace_control *control,
    const struct p280_event_descriptor *events,
    size_t event_count) {
    *control = (struct p280_trace_control){
        .events = events,
        .event_count = event_count,
    };
    if (event_count == 0U || event_count > P280_BIND_EVENT_COUNT) {
        return P280_DETAIL_TRACE_CONTROL_UNAVAILABLE;
    }
    long rc = p280_trace_mount(control);
    long warning = P280_DETAIL_TRACE_CONTROL_UNAVAILABLE;
    if (rc == 0) {
        control->tracefs_ready = 1;
        warning = P280_DETAIL_TRACE_REGISTRATION_UNAVAILABLE;
        rc = p280_path_absent(p280_global_group_root);
    }
    if (rc == 0) {
        rc = p280_path_absent(p280_instance_root);
    }
    if (rc == 0) {
        rc = sys_mkdirat(p280_instance_root, 0700);
        if (rc == 0) {
            control->instance_owned = 1;
        }
    }
    if (rc == 0) {
        for (size_t index = 0; index < event_count; ++index) {
            long write_rc = p280_write_control(
                p280_global_events_path,
                events[index].definition);
            long state = p280_event_registration_state(control, index);
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
        rc = p280_verify_event_registration(control);
    }
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/tracing_on", "0\n");
    }
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/trace_clock",
            "counter\n");
    }
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/buffer_size_kb",
            "64\n");
    }
    for (size_t index = 0; rc == 0 && index < event_count; ++index) {
        char path[P280_PATH_CAPACITY];
        rc = p280_event_path(
            path,
            sizeof(path),
            events[index].name,
            "/filter");
        if (rc == 0) {
            rc = p280_write_control(path, events[index].filter);
        }
    }
    if (rc == 0) {
        rc = p280_verify_control_readback(control);
    }
    if (rc == 0) {
        rc = p280_clear_trace();
    }
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/events/p280/enable",
            "1\n");
    }
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/tracing_on", "1\n");
    }
    if (rc == 0) {
        control->active = 1;
        return 0;
    }
    long cleanup_rc = p280_trace_cleanup(control);
    return cleanup_rc == 0
        ? warning
        : P280_DETAIL_TRACE_CLEANUP_UNVERIFIED;
}

static long p280_parse_unsigned(
    const char *start,
    const char *end,
    uint64_t *result) {
    if (start >= end || result == NULL || !p280_is_digit(*start)) {
        return -EINVAL;
    }
    uint64_t value = 0;
    for (const char *cursor = start; cursor < end; ++cursor) {
        if (!p280_is_digit(*cursor)) {
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

static long p280_parse_signed(
    const char *start,
    const char *end,
    int64_t *result) {
    int negative = 0;
    if (start < end && *start == '-') {
        negative = 1;
        ++start;
    }
    uint64_t magnitude = 0;
    long rc = p280_parse_unsigned(start, end, &magnitude);
    if (rc != 0 || magnitude > (uint64_t)INT64_MAX + (uint64_t)negative) {
        return rc != 0 ? rc : -P260_EOVERFLOW;
    }
    *result = negative ? -(int64_t)magnitude : (int64_t)magnitude;
    return 0;
}

struct p280_trace_record {
    uint64_t counter;
    long pid;
    uint8_t event_index;
    uint8_t has_on;
    uint8_t has_rc;
    int32_t on;
    int32_t rc;
};

static const char *p280_line_find(
    const char *start,
    const char *end,
    const char *needle) {
    return p280_find_bytes(start, (size_t)(end - start), needle);
}

static long p280_parse_field(
    const char *start,
    const char *end,
    const char *name,
    int32_t *result,
    uint8_t *present) {
    const char *cursor = start;
    size_t name_length = cstr_len(name);
    *present = 0;
    while (cursor < end) {
        const char *found = p280_line_find(cursor, end, name);
        if (found == NULL) {
            return 0;
        }
        if (
            (found == start || p280_is_space(found[-1]))
            && found + name_length < end
        ) {
            const char *value_start = found + name_length;
            const char *value_end = value_start;
            if (value_end < end && *value_end == '-') {
                ++value_end;
            }
            while (value_end < end && p280_is_digit(*value_end)) {
                ++value_end;
            }
            if (
                value_end < end
                && !p280_is_space(*value_end)
            ) {
                return -P260_EPROTO;
            }
            int64_t value = 0;
            long rc = p280_parse_signed(
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

static long p280_parse_line_identity(
    const char *line,
    const char *line_end,
    const char *marker,
    long *pid,
    uint64_t *counter) {
    const char *bracket = p280_line_find(line, marker, "[");
    if (bracket == NULL) {
        return -P260_EPROTO;
    }
    const char *pid_end = bracket;
    while (pid_end > line && p280_is_space(pid_end[-1])) {
        --pid_end;
    }
    const char *pid_start = pid_end;
    while (pid_start > line && p280_is_digit(pid_start[-1])) {
        --pid_start;
    }
    if (pid_start == pid_end || pid_start == line || pid_start[-1] != '-') {
        return -P260_EPROTO;
    }
    uint64_t parsed_pid = 0;
    long rc = p280_parse_unsigned(pid_start, pid_end, &parsed_pid);
    if (rc != 0 || parsed_pid > (uint64_t)INT64_MAX) {
        return rc != 0 ? rc : -P260_EOVERFLOW;
    }
    const char *close = p280_line_find(bracket, marker, "]");
    if (close == NULL) {
        return -P260_EPROTO;
    }
    const char *cursor = close + 1;
    int found_counter = 0;
    uint64_t parsed_counter = 0;
    while (cursor < marker) {
        if (!p280_is_digit(*cursor)) {
            ++cursor;
            continue;
        }
        const char *number_start = cursor;
        while (cursor < marker && p280_is_digit(*cursor)) {
            ++cursor;
        }
        if (cursor <= marker && *cursor == ':') {
            if (found_counter) {
                return -P260_EPROTO;
            }
            rc = p280_parse_unsigned(
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

static long p280_parse_trace_records(
    const struct p280_trace_control *control,
    struct p280_trace_record records[P280_RECORD_CAPACITY],
    size_t *record_count) {
    size_t count = 0;
    const char *cursor = p280_trace_buffer;
    const char *end = p280_trace_buffer + p280_trace_length;
    uint64_t previous_counter = 0;
    int have_previous = 0;
    while (cursor < end) {
        const char *line_end = cursor;
        while (line_end < end && *line_end != '\n') {
            ++line_end;
        }
        const char *bracket = p280_line_find(cursor, line_end, "[");
        const char *close = bracket == NULL
            ? NULL
            : p280_line_find(bracket, line_end, "]");
        const char *marker = close == NULL
            ? NULL
            : p280_line_find(close, line_end, ": ");
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
            if (count == P280_RECORD_CAPACITY) {
                return -P260_EOVERFLOW;
            }
            struct p280_trace_record record = {
                .event_index = (uint8_t)event_index,
            };
            long rc = p280_parse_line_identity(
                cursor,
                line_end,
                marker,
                &record.pid,
                &record.counter);
            if (rc == 0) {
                rc = p280_parse_field(
                    event_end + 1,
                    line_end,
                    "on=",
                    &record.on,
                    &record.has_on);
            }
            if (rc == 0) {
                rc = p280_parse_field(
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

static long p280_profile_clean(
    const struct p280_trace_control *control) {
    uint8_t seen[P280_BIND_EVENT_COUNT] = {0};
    const char *cursor = p280_profile_buffer;
    const char *end = p280_profile_buffer + p280_profile_length;
    while (cursor < end) {
        const char *line_end = cursor;
        while (line_end < end && *line_end != '\n') {
            ++line_end;
        }
        const char *name_start = cursor;
        while (name_start < line_end && p280_is_space(*name_start)) {
            ++name_start;
        }
        const char *name_end = name_start;
        while (name_end < line_end && !p280_is_space(*name_end)) {
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
            while (hits_start < line_end && p280_is_space(*hits_start)) {
                ++hits_start;
            }
            const char *hits_end = hits_start;
            while (hits_end < line_end && p280_is_digit(*hits_end)) {
                ++hits_end;
            }
            const char *missed_start = hits_end;
            while (
                missed_start < line_end
                && p280_is_space(*missed_start)
            ) {
                ++missed_start;
            }
            const char *missed_end = missed_start;
            while (
                missed_end < line_end
                && p280_is_digit(*missed_end)
            ) {
                ++missed_end;
            }
            uint64_t hits = 0;
            uint64_t missed = 0;
            long rc = p280_parse_unsigned(
                hits_start, hits_end, &hits);
            if (rc == 0) {
                rc = p280_parse_unsigned(
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

static long p280_trace_disable(
    struct p280_trace_control *control) {
    if (!control->active) {
        return 0;
    }
    long rc = p280_write_control(
        "/sys/kernel/tracing/instances/p280/tracing_on", "0\n");
    if (rc == 0) {
        rc = p280_write_control(
            "/sys/kernel/tracing/instances/p280/events/p280/enable",
            "0\n");
    }
    if (rc == 0) {
        control->active = 0;
    }
    return rc;
}

static long p280_trace_read_snapshot(
    const struct p280_trace_control *control,
    int require_profile) {
    long rc = p280_read_file(
        "/sys/kernel/tracing/instances/p280/trace",
        p280_trace_buffer,
        sizeof(p280_trace_buffer),
        &p280_trace_length);
    if (rc != 0 || !require_profile) {
        return rc;
    }
    rc = p280_read_file(
        p280_profile_path,
        p280_profile_buffer,
        sizeof(p280_profile_buffer),
        &p280_profile_length);
    return rc != 0 ? rc : p280_profile_clean(control);
}

static long p280_trace_finish(
    struct p280_trace_control *control,
    long *quality) {
    long local_quality = p280_trace_disable(control);
    if (local_quality == 0) {
        local_quality = p280_trace_read_snapshot(control, 1);
    }
    long cleanup_rc = p280_trace_cleanup(control);
    if (cleanup_rc != 0) {
        return P280_DETAIL_TRACE_CLEANUP_UNVERIFIED;
    }
    *quality = local_quality;
    return 0;
}

static void p280_trace_deadline_disable(
    struct p280_trace_control *control) {
    if (!control->active) {
        return;
    }
    (void)p280_write_control(
        "/sys/kernel/tracing/instances/p280/tracing_on", "0\n");
    (void)p280_write_control(
        "/sys/kernel/tracing/instances/p280/events/p280/enable", "0\n");
    control->active = 0;
}

enum p280_role_classification {
    P280_ROLE_NO_START = 0,
    P280_ROLE_START_NO_RETURN = 1,
    P280_ROLE_COMPLETE = 2,
    P280_ROLE_PARENT_PM_NEGATIVE = 3,
    P280_ROLE_CHILD_PM_NEGATIVE = 4,
};

struct p280_role_result {
    enum p280_role_classification classification;
    long pid;
    int32_t parent_pm_rc;
    int32_t child_pm_rc;
};

enum p280_bind_classification {
    P280_BIND_PULLUP_WITHOUT_RUN_STOP = 1,
    P280_BIND_NESTED_RUN_STOP_FAILURE = 2,
    P280_BIND_RUN_STOP_ZERO = 3,
};

struct p280_bind_result {
    enum p280_bind_classification classification;
    int32_t resume_rc;
    int32_t run_rc;
    uint8_t has_resume;
    uint8_t has_run;
    uint8_t clean;
};

static long p280_parse_role_result(
    const struct p280_trace_control *control,
    struct p280_role_result *result) {
    struct p280_trace_record records[P280_RECORD_CAPACITY];
    size_t count = 0;
    long rc = p280_parse_trace_records(control, records, &count);
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
        *result = (struct p280_role_result){
            .classification = P280_ROLE_NO_START,
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
        *result = (struct p280_role_result){
            .classification = P280_ROLE_START_NO_RETURN,
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
    const struct p280_trace_record *parent = &records[positions[1]];
    const struct p280_trace_record *child = &records[positions[2]];
    const struct p280_trace_record *stop = &records[positions[3]];
    if (
        !parent->has_rc
        || !child->has_rc
        || !stop->has_rc
        || stop->rc != 0
    ) {
        return -P260_EPROTO;
    }
    enum p280_role_classification classification = P280_ROLE_COMPLETE;
    if (parent->rc < 0) {
        classification = P280_ROLE_PARENT_PM_NEGATIVE;
    } else if (child->rc < 0) {
        classification = P280_ROLE_CHILD_PM_NEGATIVE;
    }
    *result = (struct p280_role_result){
        .classification = classification,
        .pid = pid,
        .parent_pm_rc = parent->rc,
        .child_pm_rc = child->rc,
    };
    return 0;
}

static long p280_one_record(
    const struct p280_trace_record *records,
    size_t count,
    uint8_t event,
    const struct p280_trace_record **result) {
    const struct p280_trace_record *found = NULL;
    for (size_t index = 0; index < count; ++index) {
        if (records[index].event_index != event) {
            continue;
        }
        if (found != NULL) {
            return -P260_EPROTO;
        }
        found = &records[index];
    }
    *result = found;
    return 0;
}

static long p280_parse_bind_result(
    const struct p280_trace_control *control,
    struct p280_bind_result *result) {
    struct p280_trace_record records[P280_RECORD_CAPACITY];
    size_t count = 0;
    long rc = p280_parse_trace_records(control, records, &count);
    if (rc != 0) {
        return rc;
    }
    for (size_t index = 0; index < count; ++index) {
        if (records[index].pid != 1) {
            return -P260_EPROTO;
        }
    }
    const struct p280_trace_record *resume_in = NULL;
    const struct p280_trace_record *resume_out = NULL;
    const struct p280_trace_record *pull_in = NULL;
    const struct p280_trace_record *pull_out = NULL;
    const struct p280_trace_record *run_in = NULL;
    const struct p280_trace_record *run_out = NULL;
    rc = p280_one_record(records, count, 0U, &resume_in);
    if (rc == 0) {
        rc = p280_one_record(records, count, 1U, &resume_out);
    }
    if (rc == 0) {
        rc = p280_one_record(records, count, 2U, &pull_in);
    }
    if (rc == 0) {
        rc = p280_one_record(records, count, 3U, &pull_out);
    }
    if (rc == 0) {
        rc = p280_one_record(records, count, 4U, &run_in);
    }
    if (rc == 0) {
        rc = p280_one_record(records, count, 5U, &run_out);
    }
    if (rc != 0) {
        return rc;
    }
    if (
        pull_in == NULL
        || pull_out == NULL
        || !pull_in->has_on
        || pull_in->on != 1
        || !pull_out->has_rc
        || pull_out->rc != 0
        || pull_in->counter >= pull_out->counter
    ) {
        return -P260_EPROTO;
    }
    if ((resume_in == NULL) != (resume_out == NULL)) {
        return -P260_EPROTO;
    }
    if ((run_in == NULL) != (run_out == NULL)) {
        return -P260_EPROTO;
    }
    int32_t resume_rc = 0;
    if (resume_in != NULL) {
        if (
            !resume_out->has_rc
            || resume_in->counter >= resume_out->counter
            || pull_in->counter >= resume_in->counter
            || resume_out->counter >= pull_out->counter
            || resume_out->rc < 0
        ) {
            return -P260_EPROTO;
        }
        resume_rc = resume_out->rc;
    }
    int32_t run_rc = 0;
    enum p280_bind_classification classification =
        P280_BIND_PULLUP_WITHOUT_RUN_STOP;
    if (run_in != NULL) {
        if (
            !run_in->has_on
            || run_in->on != 1
            || !run_out->has_rc
            || run_in->counter >= run_out->counter
            || pull_in->counter >= run_in->counter
            || run_out->counter >= pull_out->counter
        ) {
            return -P260_EPROTO;
        }
        run_rc = run_out->rc;
        if (
            resume_in != NULL
            && !(
                resume_in->counter < run_in->counter
                && run_out->counter < resume_out->counter
            )
        ) {
            return -P260_EPROTO;
        }
        if (run_rc != 0) {
            if (
                resume_in == NULL
            ) {
                return -P260_EPROTO;
            }
            classification = P280_BIND_NESTED_RUN_STOP_FAILURE;
        } else {
            classification = P280_BIND_RUN_STOP_ZERO;
        }
    }
    *result = (struct p280_bind_result){
        .classification = classification,
        .resume_rc = resume_rc,
        .run_rc = run_rc,
        .has_resume = resume_in != NULL,
        .has_run = run_in != NULL,
        .clean = 1,
    };
    return 0;
}

static long p280_read_role_class(void) {
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
        return P280_DETAIL_INITIAL_ROLE_PERIPHERAL;
    }
    if (
        length == 4U
        && p260_bytes_equal(value, "host", 4U)
    ) {
        return P280_DETAIL_INITIAL_ROLE_HOST;
    }
    return -P260_EPROTO;
}

static long p280_role_write_once(uint32_t *byte_count) {
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

static __attribute__((noreturn)) void p280_role_child(
    int pipe_fd, int unrelated_fd) {
    if (unrelated_fd >= 0 && unrelated_fd != pipe_fd) {
        (void)sys_close(unrelated_fd);
    }
    struct p280_helper_record record = {
        .magic = P280_HELPER_MAGIC,
        .version = P280_HELPER_VERSION,
        .operation = P280_HELPER_OPERATION_ROLE_WRITE,
    };
    uint32_t byte_count = 0;
    record.result = p280_role_write_once(&byte_count);
    record.byte_count = byte_count;
    long amount = sys_write(pipe_fd, &record, sizeof(record));
    (void)sys_close(pipe_fd);
    sys_exit(amount == (long)sizeof(record) ? 0 : 2);
}

static long p280_validate_helper_record(
    const struct p280_helper_record *record) {
    if (
        record->magic != P280_HELPER_MAGIC
        || record->version != P280_HELPER_VERSION
        || record->operation != P280_HELPER_OPERATION_ROLE_WRITE
        || record->reserved != 0U
        || record->result > 0
        || record->byte_count > 10U
    ) {
        return P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    if (record->result == 0 && record->byte_count != 10U) {
        return P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    if (record->result < 0 && record->byte_count != 0U) {
        return P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
    }
    return 0;
}

static void p280_progress(uint8_t stage, uint16_t warning) {
    p260_revalidate_or_fail(stage);
    long rc = warning == 0U
        ? s22_r4w1e_checkpoint_progress(&g_checkpoint, stage, 0U)
        : s22_r4w1e_checkpoint_progress_detail(
            &g_checkpoint, stage, 0U, warning);
    if (rc != 0) {
        quiet_park();
    }
}

static long p280_cleanup_before_action(
    struct p280_trace_control *control) {
    long quality = 0;
    long rc = p280_trace_finish(control, &quality);
    (void)quality;
    return rc;
}

static __attribute__((noreturn)) void p280_fail_role_trace(
    struct p280_trace_control *control,
    int pipe_fd,
    long detail,
    int quiescent) {
    (void)sys_close(pipe_fd);
    if (quiescent) {
        long quality = 0;
        long finish_rc = p280_trace_finish(control, &quality);
        if (finish_rc != 0) {
            fail_at(P260_ROLE_UDC_STAGE, 0U, finish_rc);
        }
    } else {
        p280_trace_deadline_disable(control);
    }
    fail_at(P260_ROLE_UDC_STAGE, 0U, detail);
}

static long p280_phase_role(uint16_t *first_warning, int unrelated_fd) {
    struct p280_trace_control control;
    long setup_rc = p280_trace_setup(
        &control, p280_role_events, P280_ROLE_EVENT_COUNT);
    if (setup_rc == P280_DETAIL_TRACE_CLEANUP_UNVERIFIED) {
        return setup_rc;
    }
    int armed = setup_rc == 0;
    if (!armed) {
        *first_warning = (uint16_t)setup_rc;
    }

    long role_class = p280_read_role_class();
    if (role_class != 0) {
        if (armed) {
            long cleanup_rc = p280_cleanup_before_action(&control);
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
        long cleanup_rc = p280_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : -EIO;
    }
    deadline.tv_sec += P280_ROLE_DEADLINE_SEC;

    int pipe_fds[2] = {-1, -1};
    long rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);
    if (rc != 0) {
        long cleanup_rc = p280_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : rc;
    }
    long pid = sys_clone();
    if (pid < 0) {
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        long cleanup_rc = p280_cleanup_before_action(&control);
        return cleanup_rc != 0 ? cleanup_rc : pid;
    }
    if (pid == 0) {
        (void)sys_close(pipe_fds[0]);
        p280_role_child(pipe_fds[1], unrelated_fd);
    }
    (void)sys_close(pipe_fds[1]);

    struct p280_helper_record record = {0};
    size_t record_bytes = 0;
    int record_complete = 0;
    int record_malformed = 0;
    int child_reaped = 0;
    int child_status = 0;
    struct p280_role_result role_result = {
        .classification = P280_ROLE_NO_START,
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
        long snapshot_rc = p280_trace_read_snapshot(&control, 0);
        long parse_rc = snapshot_rc == 0
            ? p280_parse_role_result(&control, &role_result)
            : snapshot_rc;

        if (record_complete && child_reaped) {
            uint8_t extra = 0;
            long extra_amount = sys_read(pipe_fds[0], &extra, 1U);
            if (extra_amount != 0) {
                record_malformed = 1;
            }
        }
        if (record_complete && child_reaped) {
            long record_rc = p280_validate_helper_record(&record);
            if (record_rc != 0) {
                p280_fail_role_trace(
                    &control,
                    pipe_fds[0],
                    record_rc,
                    parse_rc == 0
                        && role_result.classification >= P280_ROLE_COMPLETE);
            }
            if (record.result < 0) {
                if (
                    parse_rc != 0
                    || role_result.classification != P280_ROLE_NO_START
                ) {
                    p280_fail_role_trace(
                        &control,
                        pipe_fds[0],
                        P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                        parse_rc == 0
                            && role_result.classification
                                >= P280_ROLE_COMPLETE);
                }
                (void)sys_close(pipe_fds[0]);
                long quality = 0;
                long finish_rc = p280_trace_finish(&control, &quality);
                return finish_rc != 0
                    ? finish_rc
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
            p280_fail_role_trace(
                &control,
                pipe_fds[0],
                P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                parse_rc == 0
                    && role_result.classification >= P280_ROLE_COMPLETE);
        }
        if (
            record_complete
            && child_reaped
            && parse_rc == 0
            && role_result.classification >= P280_ROLE_COMPLETE
        ) {
            (void)sys_close(pipe_fds[0]);
            long quality = 0;
            long finish_rc = p280_trace_finish(&control, &quality);
            if (finish_rc != 0) {
                return finish_rc;
            }
            if (quality != 0) {
                return P280_DETAIL_ROLE_WORKER_QUIESCENCE_UNPROVED;
            }
            parse_rc = p280_parse_role_result(&control, &role_result);
            if (parse_rc != 0) {
                return P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
            }
            if (
                role_result.classification
                == P280_ROLE_PARENT_PM_NEGATIVE
            ) {
                return P280_DETAIL_PARENT_RUNTIME_PM_NEGATIVE;
            }
            if (
                role_result.classification
                == P280_ROLE_CHILD_PM_NEGATIVE
            ) {
                return P280_DETAIL_CHILD_RUNTIME_PM_NEGATIVE;
            }
            if (role_result.classification != P280_ROLE_COMPLETE) {
                return P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;
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
                p280_fail_role_trace(
                    &control,
                    pipe_fds[0],
                    P280_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,
                    0);
            }
            (void)sys_close(pipe_fds[0]);
            long detail = P280_DETAIL_ROLE_WRITE_PRE_START_TIMEOUT;
            if (role_result.classification == P280_ROLE_START_NO_RETURN) {
                detail = P280_DETAIL_PARENT_START_NO_RETURN;
            } else if (
                role_result.classification >= P280_ROLE_COMPLETE
                || (record_complete && record.result == 0)
            ) {
                detail = P280_DETAIL_ROLE_WRITE_RETURNED_NO_START;
            }
            p280_trace_deadline_disable(&control);
            fail_at(P260_ROLE_UDC_STAGE, 0U, detail);
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static long p280_phase_bind(
    uint16_t *first_warning,
    struct p280_bind_result *bind_result) {
    *bind_result = (struct p280_bind_result){0};
    struct p280_trace_control control;
    long setup_rc = p280_trace_setup(
        &control, p280_bind_events, P280_BIND_EVENT_COUNT);
    if (setup_rc == P280_DETAIL_TRACE_CLEANUP_UNVERIFIED) {
        return setup_rc;
    }
    int armed = setup_rc == 0;
    if (!armed && *first_warning == 0U) {
        *first_warning = (uint16_t)setup_rc;
    }

    long bind_rc = p260_bind_udc();
    if (!armed) {
        return bind_rc;
    }
    long quality = 0;
    long finish_rc = p280_trace_finish(&control, &quality);
    if (finish_rc != 0) {
        return finish_rc;
    }
    if (bind_rc != 0) {
        return bind_rc;
    }
    if (
        quality != 0
        || p280_parse_bind_result(&control, bind_result) != 0
    ) {
        if (*first_warning == 0U) {
            *first_warning = P280_DETAIL_BIND_TRACE_INCOMPLETE;
        }
        bind_result->clean = 0;
    }
    return 0;
}

static int p280_exact_state(
    const char *state,
    size_t length,
    const char *expected) {
    size_t expected_length = cstr_len(expected);
    return length == expected_length
        && p260_bytes_equal(state, expected, length);
}

static long p280_timeout_detail(
    const char *state,
    size_t state_length,
    const struct p280_bind_result *bind_result) {
    if (
        p280_exact_state(state, state_length, "attached")
        || p280_exact_state(state, state_length, "powered")
    ) {
        return P280_DETAIL_UDC_ATTACHED_OR_POWERED;
    }
    if (p280_exact_state(state, state_length, "default")) {
        return P280_DETAIL_UDC_DEFAULT;
    }
    if (p280_exact_state(state, state_length, "addressed")) {
        return P280_DETAIL_UDC_ADDRESSED;
    }
    if (
        p280_exact_state(state, state_length, "reconnecting")
        || p280_exact_state(state, state_length, "unauthenticated")
        || p280_exact_state(state, state_length, "suspended")
    ) {
        return P280_DETAIL_UDC_LATE_NONCONFIGURED_STATE;
    }
    if (!p280_exact_state(state, state_length, "not attached")) {
        return -P260_EPROTO;
    }
    if (!bind_result->clean) {
        return P280_DETAIL_NOT_ATTACHED_WITHOUT_CLEAN_BIND_TRACE;
    }
    if (
        bind_result->classification
        == P280_BIND_NESTED_RUN_STOP_FAILURE
    ) {
        return P280_DETAIL_NESTED_RUN_STOP_FAILURE_SWALLOWED;
    }
    if (
        bind_result->classification
        == P280_BIND_PULLUP_WITHOUT_RUN_STOP
    ) {
        return P280_DETAIL_PULLUP_ZERO_WITHOUT_RUN_STOP;
    }
    if (bind_result->classification == P280_BIND_RUN_STOP_ZERO) {
        return P280_DETAIL_RUN_STOP_ZERO_NO_BUS_STATE;
    }
    return -P260_EPROTO;
}

static long p280_wait_configured(
    const struct p280_bind_result *bind_result) {
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return -EIO;
    }
    deadline.tv_sec += P260_CONFIGURED_TIMEOUT_SEC;
    for (;;) {
        p260_revalidate_or_fail(P260_CONFIGURED_STAGE);
        char state[32];
        char speed[32];
        size_t state_length = 0;
        size_t speed_length = 0;
        long rc = p260_read_value(
            "/sys/class/udc/a600000.dwc3/state",
            state,
            sizeof(state),
            &state_length);
        if (rc == 0) {
            rc = p260_read_value(
                "/sys/class/udc/a600000.dwc3/current_speed",
                speed,
                sizeof(speed),
                &speed_length);
        }
        p260_revalidate_or_fail(P260_CONFIGURED_STAGE);
        if (rc != 0) {
            return rc;
        }
        int configured = p280_exact_state(
            state, state_length, "configured");
        int high_speed = p280_exact_state(
            speed, speed_length, "high-speed");
        if (configured) {
            return high_speed ? 0 : -P260_EPROTO;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            return -EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            rc = p260_expect_value(p260_role_path, "peripheral");
            if (rc != 0) {
                return rc;
            }
            return p280_timeout_detail(
                state, state_length, bind_result);
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static __attribute__((noreturn)) void p280_e3_run(void) {
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

    rc = p260_write_all(
        tty_fd, p260_banner, sizeof(p260_banner) - 1U, 1);
    if (rc != 0) {
        fail_at(P260_BANNER_STAGE, 0U, rc);
    }
    p260_progress(P260_BANNER_STAGE);

    uint16_t warning = 0;
    rc = p280_phase_role(&warning, tty_fd);
    if (rc != 0) {
        fail_at(P260_ROLE_UDC_STAGE, 0U, rc);
    }
    p280_progress(P260_ROLE_UDC_STAGE, warning);

    struct p280_bind_result bind_result = {0};
    rc = p280_phase_bind(&warning, &bind_result);
    if (rc != 0) {
        fail_at(P260_UDC_BIND_STAGE, 0U, rc);
    }
    p280_progress(P260_UDC_BIND_STAGE, warning);

    rc = p280_wait_configured(&bind_result);
    if (rc != 0) {
        fail_at(P260_CONFIGURED_STAGE, 0U, rc);
    }
    p280_progress(P260_CONFIGURED_STAGE, warning);

    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {
        quiet_park();
    }
    quiet_park();
}
