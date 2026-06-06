#include "a90_watchdoginv.h"

#include "a90_console.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <limits.h>
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

static bool name_has_prefix(const char *name, const char *prefix) {
    return strncmp(name, prefix, strlen(prefix)) == 0;
}

static int read_attr(const char *device, const char *attr, char *out, size_t out_size) {
    char path[PATH_MAX];
    int written;

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    written = snprintf(path, sizeof(path), "/sys/class/watchdog/%s/%s", device, attr);
    if (written < 0 || (size_t)written >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    return read_trimmed_text_file(path, out, out_size);
}

static int count_watchdogs(struct a90_watchdoginv_snapshot *out) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir("/sys/class/watchdog");
    if (dir == NULL) {
        return 0;
    }

    while ((entry = readdir(dir)) != NULL) {
        char value[128];

        if (!name_has_prefix(entry->d_name, "watchdog")) {
            continue;
        }
        ++count;
        if (read_attr(entry->d_name, "identity", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
        }
        if (read_attr(entry->d_name, "state", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
            if (strstr(value, "active") != NULL || strstr(value, "armed") != NULL) {
                ++out->armed_hint_count;
            }
        }
        if (read_attr(entry->d_name, "status", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
        }
        if (read_attr(entry->d_name, "timeleft", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
        }
        if (read_attr(entry->d_name, "timeout", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
        }
        if (read_attr(entry->d_name, "nowayout", value, sizeof(value)) == 0) {
            ++out->readable_attrs;
            if (strcmp(value, "1") == 0 || strcmp(value, "Y") == 0) {
                ++out->armed_hint_count;
            }
        }
    }

    closedir(dir);
    return count;
}

int a90_watchdoginv_collect(struct a90_watchdoginv_snapshot *out) {
    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));
    out->class_dir = path_is_dir("/sys/class/watchdog");
    out->dev_watchdog = path_exists_lstat("/dev/watchdog");
    out->dev_watchdog0 = path_exists_lstat("/dev/watchdog0");
    out->cmdline_watchdog = text_file_contains("/proc/cmdline", "watchdog");
    out->cmdline_nowayout = text_file_contains("/proc/cmdline", "nowayout");
    out->class_devices = count_watchdogs(out);
    return 0;
}

void a90_watchdoginv_summary(char *out, size_t out_size) {
    struct a90_watchdoginv_snapshot snapshot;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_watchdoginv_collect(&snapshot) < 0) {
        snprintf(out, out_size, "watchdoginv=error");
        return;
    }
    snprintf(out, out_size,
             "watchdoginv=class=%d dev=%s dev0=%s attrs=%d armed_hints=%d policy=read-only-no-open",
             snapshot.class_devices,
             yesno(snapshot.dev_watchdog),
             yesno(snapshot.dev_watchdog0),
             snapshot.readable_attrs,
             snapshot.armed_hint_count);
    out[out_size - 1] = '\0';
}

int a90_watchdoginv_print_summary(void) {
    char summary[192];

    a90_watchdoginv_summary(summary, sizeof(summary));
    a90_console_printf("%s\r\n", summary);
    return 0;
}

static void print_device_attr(const char *device, const char *attr) {
    char value[160];

    if (read_attr(device, attr, value, sizeof(value)) == 0) {
        a90_console_printf(" %s=%s", attr, value);
    }
}

static void print_watchdog_devices(void) {
    static const char *const attrs[] = {
        "identity",
        "state",
        "status",
        "timeleft",
        "timeout",
        "min_timeout",
        "max_timeout",
        "pretimeout",
        "nowayout",
        "bootstatus",
    };
    DIR *dir;
    struct dirent *entry;

    dir = opendir("/sys/class/watchdog");
    if (dir == NULL) {
        a90_console_printf("devices: none or unreadable\r\n");
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        size_t index;

        if (!name_has_prefix(entry->d_name, "watchdog")) {
            continue;
        }
        a90_console_printf("%s:", entry->d_name);
        for (index = 0; index < sizeof(attrs) / sizeof(attrs[0]); ++index) {
            print_device_attr(entry->d_name, attrs[index]);
        }
        a90_console_printf("\r\n");
    }

    closedir(dir);
}

int a90_watchdoginv_print_full(void) {
    struct a90_watchdoginv_snapshot snapshot;

    if (a90_watchdoginv_collect(&snapshot) < 0) {
        a90_console_printf("watchdoginv: collect failed\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("[watchdog feasibility]\r\n");
    a90_console_printf("policy: read-only; /dev/watchdog* is stat-only and never opened\r\n");
    a90_console_printf("summary: class_dir=%s class=%d dev_watchdog=%s dev_watchdog0=%s attrs=%d armed_hints=%d\r\n",
                       yesno(snapshot.class_dir),
                       snapshot.class_devices,
                       yesno(snapshot.dev_watchdog),
                       yesno(snapshot.dev_watchdog0),
                       snapshot.readable_attrs,
                       snapshot.armed_hint_count);
    a90_console_printf("cmdline: watchdog=%s nowayout=%s\r\n",
                       yesno(snapshot.cmdline_watchdog),
                       yesno(snapshot.cmdline_nowayout));
    print_watchdog_devices();
    return 0;
}

int a90_watchdoginv_print_paths(void) {
    static const char *const paths[] = {
        "/sys/class/watchdog",
        "/sys/class/watchdog/watchdog0",
        "/dev/watchdog",
        "/dev/watchdog0",
        "/proc/cmdline",
    };
    size_t index;

    a90_console_printf("[watchdog paths]\r\n");
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        a90_console_printf("%s: %s\r\n", paths[index], yesno(path_exists_lstat(paths[index])));
    }
    return 0;
}

int a90_watchdoginv_cmd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: watchdoginv [summary|full|paths]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "summary") == 0 || strcmp(mode, "status") == 0) {
        return a90_watchdoginv_print_summary();
    }
    if (strcmp(mode, "full") == 0) {
        return a90_watchdoginv_print_full();
    }
    if (strcmp(mode, "paths") == 0) {
        return a90_watchdoginv_print_paths();
    }

    a90_console_printf("usage: watchdoginv [summary|full|paths]\r\n");
    return -EINVAL;
}
