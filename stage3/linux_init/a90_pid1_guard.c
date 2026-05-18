#include "a90_pid1_guard.h"

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_log.h"
#include "a90_netservice.h"
#include "a90_reaper.h"
#include "a90_runtime.h"
#include "a90_selftest.h"
#include "a90_service.h"
#include "a90_storage.h"
#include "a90_timeline.h"
#include "a90_usb_gadget.h"
#include "a90_util.h"

static struct a90_pid1_guard_entry guard_entries[A90_PID1_GUARD_MAX_ENTRIES];
static size_t guard_count;
static long guard_duration_ms;

const char *a90_pid1_guard_result_name(enum a90_pid1_guard_result result) {
    switch (result) {
    case A90_PID1_GUARD_PASS:
        return "PASS";
    case A90_PID1_GUARD_WARN:
        return "WARN";
    case A90_PID1_GUARD_FAIL:
        return "FAIL";
    default:
        return "UNKNOWN";
    }
}

static void guard_add(const char *name,
                      enum a90_pid1_guard_result result,
                      int code,
                      int saved_errno,
                      const char *fmt,
                      ...) {
    struct a90_pid1_guard_entry *entry;
    va_list ap;

    if (guard_count >= A90_PID1_GUARD_MAX_ENTRIES) {
        return;
    }

    entry = &guard_entries[guard_count++];
    memset(entry, 0, sizeof(*entry));
    snprintf(entry->name, sizeof(entry->name), "%s", name);
    entry->result = result;
    entry->code = code;
    entry->saved_errno = saved_errno;

    va_start(ap, fmt);
    vsnprintf(entry->detail, sizeof(entry->detail), fmt, ap);
    va_end(ap);
}

static void guard_add_shell(const struct shell_command *commands, size_t command_count) {
    struct a90_shell_group_stats group_stats;
    size_t missing_groups = 0;
    int group;

    if (commands == NULL || command_count == 0) {
        guard_add("shell", A90_PID1_GUARD_FAIL, -EINVAL, EINVAL,
                "command table missing");
        return;
    }

    a90_shell_collect_group_stats(commands, command_count, &group_stats);
    for (group = 0; group < A90_CMD_GROUP_COUNT; ++group) {
        if (group_stats.count[group] == 0) {
            missing_groups++;
        }
    }

    guard_add("shell",
            missing_groups == 0 ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_WARN,
            0,
            0,
            "commands=%zu groups=%d missing_groups=%zu",
            group_stats.total,
            A90_CMD_GROUP_COUNT,
            missing_groups);
}

int a90_pid1_guard_run(const struct shell_command *commands, size_t command_count) {
    long start_ms = monotonic_millis();
    struct a90_storage_status storage_status;
    struct a90_runtime_status runtime_status;
    struct a90_usb_gadget_status usb_status;
    struct a90_netservice_status net_status;
    int rc;

    guard_count = 0;
    guard_duration_ms = 0;

    guard_add("pid1",
            getpid() == 1 ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
            getpid() == 1 ? 0 : -EINVAL,
            getpid() == 1 ? 0 : EINVAL,
            "pid=%ld ppid=%ld",
            (long)getpid(),
            (long)getppid());

    guard_add("config",
            INIT_VERSION[0] != '\0' && INIT_BUILD[0] != '\0' ?
                    A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
            0,
            0,
            "version=%s build=%s",
            INIT_VERSION,
            INIT_BUILD);

    guard_add("log",
            a90_log_ready() ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
            a90_log_ready() ? 0 : -ENOENT,
            a90_log_ready() ? 0 : ENOENT,
            "ready=%s path=%s",
            a90_log_ready() ? "yes" : "no",
            a90_log_path());

    guard_add("timeline",
            a90_timeline_count() > 0 ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
            a90_timeline_count() > 0 ? 0 : -ENOENT,
            a90_timeline_count() > 0 ? 0 : ENOENT,
            "entries=%zu/%d",
            a90_timeline_count(),
            BOOT_TIMELINE_MAX);

    guard_add("selftest",
            a90_selftest_count() == 0 ? A90_PID1_GUARD_WARN :
                    (a90_selftest_has_failures() ? A90_PID1_GUARD_FAIL : A90_PID1_GUARD_PASS),
            a90_selftest_has_failures() ? -EIO : 0,
            a90_selftest_has_failures() ? EIO : 0,
            "entries=%zu failures=%s",
            a90_selftest_count(),
            a90_selftest_has_failures() ? "yes" : "no");

    rc = a90_storage_get_status(&storage_status);
    if (rc == 0) {
        guard_add("storage",
                storage_status.fallback ? A90_PID1_GUARD_WARN : A90_PID1_GUARD_PASS,
                0,
                0,
                "backend=%s root=%s fallback=%s warning=%s",
                storage_status.backend,
                storage_status.root,
                storage_status.fallback ? "yes" : "no",
                storage_status.warning[0] != '\0' ? storage_status.warning : "none");
    } else {
        guard_add("storage", A90_PID1_GUARD_FAIL, rc, -rc,
                "status unavailable");
    }

    rc = a90_runtime_get_status(&runtime_status);
    if (rc == 0) {
        enum a90_pid1_guard_result result = A90_PID1_GUARD_PASS;

        if (!runtime_status.initialized || !runtime_status.writable) {
            result = A90_PID1_GUARD_FAIL;
        } else if (runtime_status.fallback) {
            result = A90_PID1_GUARD_WARN;
        }
        guard_add("runtime",
                result,
                result == A90_PID1_GUARD_FAIL ? -EIO : 0,
                result == A90_PID1_GUARD_FAIL ? EIO : 0,
                "backend=%s root=%s fallback=%s writable=%s",
                runtime_status.backend,
                runtime_status.root,
                runtime_status.fallback ? "yes" : "no",
                runtime_status.writable ? "yes" : "no");
    } else {
        guard_add("runtime", A90_PID1_GUARD_FAIL, rc, -rc,
                "status unavailable");
    }

    guard_add("services",
            a90_service_count() >= A90_SERVICE_COUNT ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
            a90_service_count() >= A90_SERVICE_COUNT ? 0 : -EINVAL,
            a90_service_count() >= A90_SERVICE_COUNT ? 0 : EINVAL,
            "registered=%d expected=%d",
            a90_service_count(),
            A90_SERVICE_COUNT);

    {
        char reaper_summary[128];

        (void)a90_reaper_reap_orphans("pid1guard");
        a90_reaper_summary(reaper_summary, sizeof(reaper_summary));
        guard_add("reaper",
                A90_PID1_GUARD_PASS,
                0,
                0,
                "%s",
                reaper_summary);
    }

    rc = a90_usb_gadget_status(&usb_status);
    if (rc == 0) {
        bool ready = usb_status.configfs_mounted &&
                     usb_status.gadget_dir &&
                     usb_status.acm_function &&
                     usb_status.acm_link &&
                     usb_status.udc_bound;

        guard_add("usb",
                ready ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_FAIL,
                ready ? 0 : -ENODEV,
                ready ? 0 : ENODEV,
                "configfs=%s gadget=%s acm=%s link=%s udc=%s",
                usb_status.configfs_mounted ? "yes" : "no",
                usb_status.gadget_dir ? "yes" : "no",
                usb_status.acm_function ? "yes" : "no",
                usb_status.acm_link ? "yes" : "no",
                usb_status.udc_bound ? usb_status.udc : "none");
    } else {
        guard_add("usb", A90_PID1_GUARD_FAIL, rc, -rc,
                "status unavailable");
    }

    rc = a90_netservice_status(&net_status);
    if (rc == 0) {
        bool helpers_ready = net_status.usbnet_helper &&
                             net_status.tcpctl_helper &&
                             net_status.toybox_helper;

        guard_add("netservice",
                helpers_ready ? A90_PID1_GUARD_PASS : A90_PID1_GUARD_WARN,
                0,
                0,
                "enabled=%s ncm=%s tcpctl=%s helpers=%s",
                net_status.enabled ? "yes" : "no",
                net_status.ncm_present ? "yes" : "no",
                net_status.tcpctl_running ? "running" : "stopped",
                helpers_ready ? "ready" : "partial");
    } else {
        guard_add("netservice", A90_PID1_GUARD_WARN, rc, -rc,
                "status unavailable");
    }

    guard_add_shell(commands, command_count);

    guard_duration_ms = monotonic_millis() - start_ms;
    a90_logf("pid1guard", "%s", a90_pid1_guard_has_failures() ? "failures detected" : "ok");
    return a90_pid1_guard_has_failures() ? -EIO : 0;
}

void a90_pid1_guard_summary(char *out, size_t out_size) {
    size_t index;
    size_t pass = 0;
    size_t warn = 0;
    size_t fail = 0;

    if (out == NULL || out_size == 0) {
        return;
    }

    for (index = 0; index < guard_count; ++index) {
        switch (guard_entries[index].result) {
        case A90_PID1_GUARD_PASS:
            pass++;
            break;
        case A90_PID1_GUARD_WARN:
            warn++;
            break;
        case A90_PID1_GUARD_FAIL:
            fail++;
            break;
        default:
            warn++;
            break;
        }
    }

    snprintf(out, out_size, "pass=%zu warn=%zu fail=%zu duration=%ldms",
            pass,
            warn,
            fail,
            guard_duration_ms);
}

size_t a90_pid1_guard_count(void) {
    return guard_count;
}

const struct a90_pid1_guard_entry *a90_pid1_guard_entry_at(size_t index) {
    if (index >= guard_count) {
        return NULL;
    }
    return &guard_entries[index];
}

bool a90_pid1_guard_has_failures(void) {
    size_t index;

    for (index = 0; index < guard_count; ++index) {
        if (guard_entries[index].result == A90_PID1_GUARD_FAIL) {
            return true;
        }
    }
    return false;
}
