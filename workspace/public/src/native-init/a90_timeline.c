#include "a90_timeline.h"

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_log.h"
#include "a90_util.h"

static struct a90_timeline_entry timeline_entries[BOOT_TIMELINE_MAX];
static size_t timeline_entry_count = 0;

void a90_timeline_record(int code,
                         int saved_errno,
                         const char *step,
                         const char *fmt,
                         ...) {
    struct a90_timeline_entry *entry;
    va_list ap;
    size_t index;

    if (timeline_entry_count < BOOT_TIMELINE_MAX) {
        index = timeline_entry_count++;
    } else {
        index = BOOT_TIMELINE_MAX - 1;
    }

    entry = &timeline_entries[index];
    entry->ms = monotonic_millis();
    entry->code = code;
    entry->saved_errno = saved_errno;
    snprintf(entry->step, sizeof(entry->step), "%s", step);

    va_start(ap, fmt);
    vsnprintf(entry->detail, sizeof(entry->detail), fmt, ap);
    va_end(ap);

    a90_logf("timeline", "%s rc=%d errno=%d detail=%s",
             entry->step,
             entry->code,
             entry->saved_errno,
             entry->detail);
}

void a90_timeline_replay_to_log(const char *reason) {
    size_t index;

    for (index = 0; index < timeline_entry_count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct a90_timeline_entry *entry = &timeline_entries[index];

        a90_logf("timeline", "replay=%s %s rc=%d errno=%d ms=%ld detail=%s",
                 reason,
                 entry->step,
                 entry->code,
                 entry->saved_errno,
                 entry->ms,
                 entry->detail);
    }
}

void a90_timeline_probe_path(const char *step, const char *path) {
    int rc = access(path, F_OK);
    int saved_errno = rc == 0 ? 0 : errno;

    a90_timeline_record(rc == 0 ? 0 : -saved_errno,
                        saved_errno,
                        step,
                        "%s %s",
                        path,
                        rc == 0 ? "ready" : strerror(saved_errno));
}

void a90_timeline_probe_boot_resources(void) {
    a90_timeline_probe_path("resource-drm", "/sys/class/drm/card0");
    a90_timeline_probe_path("resource-input0", "/sys/class/input/event0");
    a90_timeline_probe_path("resource-input3", "/sys/class/input/event3");
    a90_timeline_probe_path("resource-battery", "/sys/class/power_supply/battery");
    a90_timeline_probe_path("resource-thermal", "/sys/class/thermal");
}

void a90_timeline_boot_summary(char *out, size_t out_size) {
    const struct a90_timeline_entry *last = NULL;
    const struct a90_timeline_entry *last_error = NULL;
    size_t index;

    if (out_size == 0) {
        return;
    }

    for (index = 0; index < timeline_entry_count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct a90_timeline_entry *entry = &timeline_entries[index];

        last = entry;
        if (entry->code < 0) {
            last_error = entry;
        }
    }

    if (last_error != NULL) {
        snprintf(out, out_size, "BOOT ERR %.10s E%d",
                 last_error->step,
                 last_error->saved_errno);
        return;
    }

    if (last != NULL) {
        long tenths = (last->ms + 50) / 100;

        snprintf(out, out_size, "BOOT OK %.10s %ld.%lds",
                 last->step,
                 tenths / 10,
                 tenths % 10);
        return;
    }

    snprintf(out, out_size, "BOOT ?");
}

size_t a90_timeline_count(void) {
    return timeline_entry_count;
}

const struct a90_timeline_entry *a90_timeline_entry_at(size_t index) {
    if (index >= timeline_entry_count || index >= BOOT_TIMELINE_MAX) {
        return NULL;
    }
    return &timeline_entries[index];
}
