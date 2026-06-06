#include "a90_userland.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_helper.h"
#include "a90_log.h"
#include "a90_runtime.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static struct a90_userland_entry userland_entries[A90_USERLAND_MAX_ENTRIES];
static int userland_count;
static bool userland_scanned;
static int userland_warn_count;
static char userland_summary_text[160];

static bool userland_stat_exec(const char *path, long long *size_out) {
    struct stat st;

    if (path == NULL || path[0] == '\0' || stat(path, &st) < 0) {
        return false;
    }
    if (!S_ISREG(st.st_mode) || (st.st_mode & 0111) == 0) {
        return false;
    }
    if (size_out != NULL) {
        *size_out = (long long)st.st_size;
    }
    return true;
}

static void userland_join_runtime_path(char *out, size_t out_size, const char *name) {
    struct a90_runtime_status runtime;
    size_t used;

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (name == NULL || name[0] == '\0') {
        return;
    }
    if (a90_runtime_get_status(&runtime) == 0 && runtime.bin[0] != '\0') {
        snprintf(out, out_size, "%s", runtime.bin);
    } else {
        snprintf(out, out_size, "%s/%s", A90_RUNTIME_CACHE_ROOT, A90_RUNTIME_BIN_DIR);
    }
    out[out_size - 1] = '\0';
    used = strlen(out);
    if (used + 1 < out_size) {
        out[used++] = '/';
        out[used] = '\0';
    }
    if (used < out_size) {
        strncat(out, name, out_size - used - 1);
    }
}

static struct a90_userland_entry *userland_add(enum a90_userland_kind kind,
                                               const char *name,
                                               const char *fallback) {
    struct a90_userland_entry *entry;

    if (userland_count >= A90_USERLAND_MAX_ENTRIES ||
        name == NULL ||
        name[0] == '\0') {
        return NULL;
    }
    entry = &userland_entries[userland_count++];
    memset(entry, 0, sizeof(*entry));
    entry->kind = kind;
    snprintf(entry->name, sizeof(entry->name), "%s", name);
    userland_join_runtime_path(entry->runtime_path, sizeof(entry->runtime_path), name);
    if (fallback != NULL) {
        snprintf(entry->fallback_path, sizeof(entry->fallback_path), "%s", fallback);
    }
    return entry;
}

static void userland_finalize_busybox(struct a90_userland_entry *entry) {
    struct a90_helper_entry helper;
    long long size = 0;

    if (a90_helper_find("busybox", &helper) == 0) {
        snprintf(entry->runtime_path, sizeof(entry->runtime_path), "%s", helper.path);
        snprintf(entry->fallback_path, sizeof(entry->fallback_path), "%s", helper.fallback);
        if (helper.preferred[0] != '\0') {
            snprintf(entry->selected_path, sizeof(entry->selected_path), "%s", helper.preferred);
            entry->present = true;
            entry->executable = true;
            entry->fallback_present = helper.fallback_present;
            entry->size = helper.actual_size > 0 ? helper.actual_size : 0;
            if (helper.warning[0] != '\0') {
                snprintf(entry->warning, sizeof(entry->warning), "%s", helper.warning);
                ++userland_warn_count;
            }
            return;
        }
    }

    if (userland_stat_exec(A90_BUSYBOX_HELPER, &size)) {
        snprintf(entry->selected_path, sizeof(entry->selected_path), "%s", A90_BUSYBOX_HELPER);
        entry->present = true;
        entry->executable = true;
        entry->fallback_present = true;
        entry->size = size;
        return;
    }
    if (userland_stat_exec(A90_BUSYBOX_RAMDISK_HELPER, &size)) {
        snprintf(entry->selected_path,
                 sizeof(entry->selected_path),
                 "%s",
                 A90_BUSYBOX_RAMDISK_HELPER);
        entry->present = true;
        entry->executable = true;
        entry->fallback_present = true;
        entry->size = size;
        return;
    }
    snprintf(entry->warning, sizeof(entry->warning), "busybox not installed");
}

static void userland_finalize_toybox(struct a90_userland_entry *entry) {
    struct a90_helper_entry helper;
    long long size = 0;

    if (a90_helper_find("toybox", &helper) == 0) {
        snprintf(entry->runtime_path, sizeof(entry->runtime_path), "%s", helper.path);
        snprintf(entry->fallback_path, sizeof(entry->fallback_path), "%s", helper.fallback);
        if (helper.preferred[0] != '\0') {
            snprintf(entry->selected_path, sizeof(entry->selected_path), "%s", helper.preferred);
            entry->present = true;
            entry->executable = true;
            entry->fallback_present = helper.fallback_present;
            entry->size = helper.actual_size > 0 ? helper.actual_size : 0;
            if (helper.warning[0] != '\0') {
                snprintf(entry->warning, sizeof(entry->warning), "%s", helper.warning);
                ++userland_warn_count;
            }
            return;
        }
    }

    if (userland_stat_exec(NETSERVICE_TOYBOX, &size)) {
        snprintf(entry->selected_path, sizeof(entry->selected_path), "%s", NETSERVICE_TOYBOX);
        entry->present = true;
        entry->executable = true;
        entry->fallback_present = true;
        entry->size = size;
        return;
    }
    snprintf(entry->warning, sizeof(entry->warning), "toybox not installed");
}

int a90_userland_scan(void) {
    struct a90_userland_entry *busybox;
    struct a90_userland_entry *toybox;

    memset(userland_entries, 0, sizeof(userland_entries));
    userland_count = 0;
    userland_warn_count = 0;
    userland_scanned = true;

    busybox = userland_add(A90_USERLAND_BUSYBOX, "busybox", A90_BUSYBOX_HELPER);
    toybox = userland_add(A90_USERLAND_TOYBOX, "toybox", NETSERVICE_TOYBOX);
    if (busybox != NULL) {
        userland_finalize_busybox(busybox);
    }
    if (toybox != NULL) {
        userland_finalize_toybox(toybox);
    }

    a90_userland_summary(userland_summary_text, sizeof(userland_summary_text));
    a90_logf("userland", "%s", userland_summary_text);
    return a90_userland_has_any() ? 0 : -ENOENT;
}

static void userland_scan_if_needed(void) {
    if (!userland_scanned) {
        (void)a90_userland_scan();
    }
}

int a90_userland_count(void) {
    userland_scan_if_needed();
    return userland_count;
}

int a90_userland_entry_at(int index, struct a90_userland_entry *out) {
    userland_scan_if_needed();
    if (out == NULL || index < 0 || index >= userland_count) {
        errno = EINVAL;
        return -EINVAL;
    }
    *out = userland_entries[index];
    return 0;
}

int a90_userland_find(const char *name, struct a90_userland_entry *out) {
    int index;

    userland_scan_if_needed();
    if (name == NULL || out == NULL) {
        errno = EINVAL;
        return -EINVAL;
    }
    for (index = 0; index < userland_count; ++index) {
        if (strcmp(userland_entries[index].name, name) == 0) {
            *out = userland_entries[index];
            return 0;
        }
    }
    errno = ENOENT;
    return -ENOENT;
}

const char *a90_userland_path(const char *name) {
    static char selected[PATH_MAX];
    struct a90_userland_entry entry;

    selected[0] = '\0';
    if (a90_userland_find(name, &entry) == 0 && entry.selected_path[0] != '\0') {
        snprintf(selected, sizeof(selected), "%s", entry.selected_path);
    }
    return selected;
}

void a90_userland_summary(char *out, size_t out_size) {
    struct a90_userland_entry busybox;
    struct a90_userland_entry toybox;
    const char *busybox_state = "missing";
    const char *toybox_state = "missing";

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_userland_find("busybox", &busybox) == 0 && busybox.executable) {
        busybox_state = "ready";
    }
    if (a90_userland_find("toybox", &toybox) == 0 && toybox.executable) {
        toybox_state = "ready";
    }
    snprintf(out,
             out_size,
             "busybox=%s toybox=%s warn=%d",
             busybox_state,
             toybox_state,
             userland_warn_count);
}

bool a90_userland_has_busybox(void) {
    struct a90_userland_entry entry;

    return a90_userland_find("busybox", &entry) == 0 && entry.executable;
}

bool a90_userland_has_any(void) {
    int index;

    userland_scan_if_needed();
    for (index = 0; index < userland_count; ++index) {
        if (userland_entries[index].executable) {
            return true;
        }
    }
    return false;
}

int a90_userland_print_inventory(bool verbose) {
    int index;

    (void)a90_userland_scan();
    a90_console_printf("userland: %s\r\n", userland_summary_text);
    if (!verbose) {
        return a90_userland_has_any() ? 0 : -ENOENT;
    }
    for (index = 0; index < userland_count; ++index) {
        const struct a90_userland_entry *entry = &userland_entries[index];

        a90_console_printf("userland: name=%s present=%s exec=%s selected=%s\r\n",
                entry->name,
                entry->present ? "yes" : "no",
                entry->executable ? "yes" : "no",
                entry->selected_path[0] != '\0' ? entry->selected_path : "-");
        a90_console_printf("userland: name=%s runtime=%s fallback=%s fallback_present=%s size=%lld\r\n",
                entry->name,
                entry->runtime_path[0] != '\0' ? entry->runtime_path : "-",
                entry->fallback_path[0] != '\0' ? entry->fallback_path : "-",
                entry->fallback_present ? "yes" : "no",
                entry->size);
        if (entry->warning[0] != '\0') {
            a90_console_printf("userland: name=%s warning=%s\r\n",
                    entry->name,
                    entry->warning);
        }
    }
    return a90_userland_has_any() ? 0 : -ENOENT;
}
