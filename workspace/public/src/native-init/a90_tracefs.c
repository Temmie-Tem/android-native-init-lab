#include "a90_tracefs.h"

#include "a90_console.h"
#include "a90_util.h"

#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static bool path_exists_lstat(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static bool path_is_dir(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

static bool text_file_contains(const char *path, const char *needle) {
    char buf[4096];

    if (read_text_file(path, buf, sizeof(buf)) < 0) {
        return false;
    }
    return strstr(buf, needle) != NULL;
}

static bool proc_filesystems_has(const char *name) {
    return text_file_contains("/proc/filesystems", name);
}

static bool proc_mounts_has_type(const char *type) {
    char buf[4096];
    char needle[96];

    if (read_text_file("/proc/mounts", buf, sizeof(buf)) < 0) {
        return false;
    }
    snprintf(needle, sizeof(needle), " %s ", type);
    needle[sizeof(needle) - 1] = '\0';
    return strstr(buf, needle) != NULL;
}

static int count_words(const char *text) {
    int count = 0;
    bool in_word = false;

    while (*text != '\0') {
        if (*text == ' ' || *text == '\t' || *text == '\r' || *text == '\n') {
            in_word = false;
        } else if (!in_word) {
            in_word = true;
            ++count;
        }
        ++text;
    }
    return count;
}

static int count_lines(const char *text) {
    int count = 0;
    bool has_data = false;

    while (*text != '\0') {
        has_data = true;
        if (*text == '\n') {
            ++count;
        }
        ++text;
    }
    if (has_data && text[-1] != '\n') {
        ++count;
    }
    return count;
}

static const char *trace_root(void) {
    if (path_is_dir("/sys/kernel/tracing")) {
        return "/sys/kernel/tracing";
    }
    if (path_is_dir("/sys/kernel/debug/tracing")) {
        return "/sys/kernel/debug/tracing";
    }
    return "/sys/kernel/tracing";
}

static int read_trace_attr(const char *root, const char *name, char *out, size_t out_size) {
    char path[256];
    int written;

    written = snprintf(path, sizeof(path), "%s/%s", root, name);
    if (written < 0 || (size_t)written >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    return read_trimmed_text_file(path, out, out_size);
}

int a90_tracefs_collect(struct a90_tracefs_snapshot *out) {
    const char *root;
    char buf[4096];

    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));
    out->fs_tracefs = proc_filesystems_has("tracefs");
    out->fs_debugfs = proc_filesystems_has("debugfs");
    out->mount_tracefs = proc_mounts_has_type("tracefs");
    out->mount_debugfs = proc_mounts_has_type("debugfs");
    out->tracing_dir = path_is_dir("/sys/kernel/tracing");
    out->debug_tracing_dir = path_is_dir("/sys/kernel/debug/tracing");

    root = trace_root();
    if (read_trace_attr(root, "current_tracer", out->current_tracer, sizeof(out->current_tracer)) == 0) {
        out->current_tracer_readable = true;
    }
    if (read_trace_attr(root, "tracing_on", out->tracing_on, sizeof(out->tracing_on)) == 0) {
        out->tracing_on_readable = true;
    }
    if (read_trace_attr(root, "available_tracers", buf, sizeof(buf)) == 0) {
        size_t sample_len = strnlen(buf, sizeof(out->available_tracers_sample) - 1);

        out->available_tracers_readable = true;
        out->tracer_count_sample = count_words(buf);
        memcpy(out->available_tracers_sample, buf, sample_len);
        out->available_tracers_sample[sample_len] = '\0';
    }
    if (read_trace_attr(root, "available_events", buf, sizeof(buf)) == 0) {
        out->available_events_readable = true;
        out->event_count_sample = count_lines(buf);
    }

    return 0;
}

void a90_tracefs_summary(char *out, size_t out_size) {
    struct a90_tracefs_snapshot snapshot;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_tracefs_collect(&snapshot) < 0) {
        snprintf(out, out_size, "tracefs=error");
        return;
    }
    snprintf(out, out_size,
             "tracefs=fs=%s mounted=%s dir=%s debugfs=%s current=%s tracing_on=%s tracers=%d events_sample=%d policy=read-only",
             yesno(snapshot.fs_tracefs),
             yesno(snapshot.mount_tracefs),
             yesno(snapshot.tracing_dir || snapshot.debug_tracing_dir),
             yesno(snapshot.mount_debugfs),
             snapshot.current_tracer_readable ? snapshot.current_tracer : "-",
             snapshot.tracing_on_readable ? snapshot.tracing_on : "-",
             snapshot.tracer_count_sample,
             snapshot.event_count_sample);
    out[out_size - 1] = '\0';
}

int a90_tracefs_print_summary(void) {
    char summary[256];

    a90_tracefs_summary(summary, sizeof(summary));
    a90_console_printf("%s\r\n", summary);
    return 0;
}

int a90_tracefs_print_full(void) {
    struct a90_tracefs_snapshot snapshot;

    if (a90_tracefs_collect(&snapshot) < 0) {
        a90_console_printf("tracefs: collect failed\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("[tracefs feasibility]\r\n");
    a90_console_printf("policy: read-only; no tracefs mount, no tracing_on write, no current_tracer write\r\n");
    a90_console_printf("support: fs_tracefs=%s fs_debugfs=%s mount_tracefs=%s mount_debugfs=%s\r\n",
                       yesno(snapshot.fs_tracefs),
                       yesno(snapshot.fs_debugfs),
                       yesno(snapshot.mount_tracefs),
                       yesno(snapshot.mount_debugfs));
    a90_console_printf("paths: sys_tracing=%s debug_tracing=%s root=%s\r\n",
                       yesno(snapshot.tracing_dir),
                       yesno(snapshot.debug_tracing_dir),
                       trace_root());
    a90_console_printf("state: current_tracer=%s tracing_on=%s\r\n",
                       snapshot.current_tracer_readable ? snapshot.current_tracer : "-",
                       snapshot.tracing_on_readable ? snapshot.tracing_on : "-");
    a90_console_printf("available: tracers_readable=%s tracer_sample_count=%d events_readable=%s event_sample_lines=%d\r\n",
                       yesno(snapshot.available_tracers_readable),
                       snapshot.tracer_count_sample,
                       yesno(snapshot.available_events_readable),
                       snapshot.event_count_sample);
    a90_console_printf("tracers_sample: %s\r\n",
                       snapshot.available_tracers_sample[0] ? snapshot.available_tracers_sample : "-");
    return 0;
}

int a90_tracefs_print_paths(void) {
    static const char *const paths[] = {
        "/proc/filesystems",
        "/proc/mounts",
        "/sys/kernel/tracing",
        "/sys/kernel/tracing/current_tracer",
        "/sys/kernel/tracing/tracing_on",
        "/sys/kernel/tracing/available_tracers",
        "/sys/kernel/tracing/available_events",
        "/sys/kernel/debug",
        "/sys/kernel/debug/tracing",
    };
    size_t index;

    a90_console_printf("[tracefs paths]\r\n");
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        a90_console_printf("%s: %s\r\n", paths[index], yesno(path_exists_lstat(paths[index])));
    }
    return 0;
}

int a90_tracefs_cmd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: tracefs [summary|full|paths]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "summary") == 0 || strcmp(mode, "status") == 0) {
        return a90_tracefs_print_summary();
    }
    if (strcmp(mode, "full") == 0) {
        return a90_tracefs_print_full();
    }
    if (strcmp(mode, "paths") == 0) {
        return a90_tracefs_print_paths();
    }

    a90_console_printf("usage: tracefs [summary|full|paths]\r\n");
    return -EINVAL;
}
