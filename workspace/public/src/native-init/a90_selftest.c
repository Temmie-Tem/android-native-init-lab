#include "a90_selftest.h"

#include "a90_config.h"
#include "a90_helper.h"
#include "a90_kms.h"
#include "a90_log.h"
#include "a90_longsoak.h"
#include "a90_metrics.h"
#include "a90_netservice.h"
#include "a90_runtime.h"
#include "a90_service.h"
#include "a90_storage.h"
#include "a90_timeline.h"
#include "a90_usb_gadget.h"
#include "a90_userland.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

static struct a90_selftest_entry selftest_entries[A90_SELFTEST_MAX_ENTRIES];
static size_t selftest_entry_count = 0;
static unsigned int selftest_pass_count = 0;
static unsigned int selftest_warn_count = 0;
static unsigned int selftest_fail_count = 0;
static long selftest_duration_ms = 0;

const char *a90_selftest_result_name(enum a90_selftest_result result) {
    switch (result) {
    case A90_SELFTEST_PASS:
        return "PASS";
    case A90_SELFTEST_WARN:
        return "WARN";
    case A90_SELFTEST_FAIL:
        return "FAIL";
    default:
        return "?";
    }
}

static void selftest_reset(void) {
    memset(selftest_entries, 0, sizeof(selftest_entries));
    selftest_entry_count = 0;
    selftest_pass_count = 0;
    selftest_warn_count = 0;
    selftest_fail_count = 0;
    selftest_duration_ms = 0;
}

static void selftest_record(const char *name,
                            enum a90_selftest_result result,
                            int code,
                            int saved_errno,
                            long duration_ms,
                            const char *detail) {
    struct a90_selftest_entry *entry;
    size_t index;

    if (selftest_entry_count < A90_SELFTEST_MAX_ENTRIES) {
        index = selftest_entry_count++;
    } else {
        index = A90_SELFTEST_MAX_ENTRIES - 1;
    }

    entry = &selftest_entries[index];
    snprintf(entry->name, sizeof(entry->name), "%s", name);
    entry->result = result;
    entry->code = code;
    entry->saved_errno = saved_errno;
    entry->duration_ms = duration_ms < 0 ? 0 : duration_ms;
    snprintf(entry->detail, sizeof(entry->detail), "%s", detail);

    if (result == A90_SELFTEST_PASS) {
        ++selftest_pass_count;
    } else if (result == A90_SELFTEST_WARN) {
        ++selftest_warn_count;
    } else {
        ++selftest_fail_count;
    }

    a90_logf("selftest", "%s %s rc=%d errno=%d duration=%ldms detail=%s",
             name,
             a90_selftest_result_name(result),
             code,
             saved_errno,
             entry->duration_ms,
             entry->detail);
}

static void selftest_record_elapsed(const char *name,
                                    enum a90_selftest_result result,
                                    int code,
                                    int saved_errno,
                                    long started_ms,
                                    const char *detail) {
    selftest_record(name,
                    result,
                    code,
                    saved_errno,
                    monotonic_millis() - started_ms,
                    detail);
}

static void selftest_log(void) {
    long started_ms = monotonic_millis();
    const char *path = a90_log_path();

    if (!a90_log_ready()) {
        selftest_record_elapsed("log",
                                A90_SELFTEST_WARN,
                                -ENODEV,
                                ENODEV,
                                started_ms,
                                "log not ready");
        return;
    }

    a90_logf("selftest", "log write probe path=%s", path);
    if (access(path, F_OK) == 0) {
        char detail[128];

        snprintf(detail, sizeof(detail), "ready path=%s", path);
        selftest_record_elapsed("log",
                                A90_SELFTEST_PASS,
                                0,
                                0,
                                started_ms,
                                detail);
    } else {
        int saved_errno = errno;
        char detail[128];

        snprintf(detail, sizeof(detail), "path=%s %s", path, strerror(saved_errno));
        selftest_record_elapsed("log",
                                A90_SELFTEST_WARN,
                                -saved_errno,
                                saved_errno,
                                started_ms,
                                detail);
    }
}

static void selftest_timeline(void) {
    long started_ms = monotonic_millis();
    size_t count = a90_timeline_count();
    char summary[64];
    char detail[128];

    a90_timeline_boot_summary(summary, sizeof(summary));
    snprintf(detail, sizeof(detail), "entries=%ld summary=%s", (long)count, summary);
    selftest_record_elapsed("timeline",
                            count > 0 ? A90_SELFTEST_PASS : A90_SELFTEST_WARN,
                            count > 0 ? 0 : -ENOENT,
                            count > 0 ? 0 : ENOENT,
                            started_ms,
                            detail);
}

static void selftest_storage(void) {
    long started_ms = monotonic_millis();
    struct a90_storage_status status;
    char detail[128];

    if (a90_storage_get_status(&status) < 0) {
        int saved_errno = errno;

        snprintf(detail, sizeof(detail), "status failed %s", strerror(saved_errno));
        selftest_record_elapsed("storage",
                                A90_SELFTEST_FAIL,
                                -saved_errno,
                                saved_errno,
                                started_ms,
                                detail);
        return;
    }

    snprintf(detail,
             sizeof(detail),
             "backend=%s sd=%s rw=%s",
             status.backend,
             status.sd_mounted ? "mounted" : "not-mounted",
             status.sd_rw_ok ? "yes" : "no");
    if (status.fallback) {
        selftest_record_elapsed("storage",
                                A90_SELFTEST_WARN,
                                0,
                                0,
                                started_ms,
                                detail);
    } else {
        selftest_record_elapsed("storage",
                                A90_SELFTEST_PASS,
                                0,
                                0,
                                started_ms,
                                detail);
    }
}

static void selftest_runtime(void) {
    long started_ms = monotonic_millis();
    struct a90_runtime_status status;
    char detail[160];
    bool dirs_ok;

    if (a90_runtime_get_status(&status) < 0) {
        int saved_errno = errno;

        snprintf(detail, sizeof(detail), "status failed %s", strerror(saved_errno));
        selftest_record_elapsed("runtime",
                                A90_SELFTEST_FAIL,
                                -saved_errno,
                                saved_errno,
                                started_ms,
                                detail);
        return;
    }

    dirs_ok = access(status.root, F_OK) == 0 &&
              access(status.bin, F_OK) == 0 &&
              access(status.etc, F_OK) == 0 &&
              access(status.logs, F_OK) == 0 &&
              access(status.tmp, F_OK) == 0 &&
              access(status.state, F_OK) == 0 &&
              access(status.pkg, F_OK) == 0 &&
              access(status.run, F_OK) == 0;
    snprintf(detail,
             sizeof(detail),
             "backend=%s root=%.72s writable=%s fallback=%s",
             status.backend,
             status.root,
             status.writable ? "yes" : "no",
             status.fallback ? "yes" : "no");
    selftest_record_elapsed("runtime",
                            status.initialized && status.writable && dirs_ok ?
                                    (status.fallback ? A90_SELFTEST_WARN : A90_SELFTEST_PASS) :
                                    A90_SELFTEST_FAIL,
                            status.initialized && status.writable && dirs_ok ? 0 : -ENODEV,
                            status.initialized && status.writable && dirs_ok ? 0 : ENODEV,
                            started_ms,
                            detail);
}

static void selftest_helpers(void) {
    long started_ms = monotonic_millis();
    char summary[128];
    int rc;

    rc = a90_helper_scan();
    a90_helper_summary(summary, sizeof(summary));
    if (a90_helper_has_failures()) {
        selftest_record_elapsed("helpers",
                                A90_SELFTEST_FAIL,
                                rc,
                                EIO,
                                started_ms,
                                summary);
        return;
    }
    if (a90_helper_has_warnings()) {
        selftest_record_elapsed("helpers",
                                A90_SELFTEST_WARN,
                                0,
                                0,
                                started_ms,
                                summary);
        return;
    }
    selftest_record_elapsed("helpers",
                            A90_SELFTEST_PASS,
                            0,
                            0,
                            started_ms,
                            summary);
}

static void selftest_userland(void) {
    long started_ms = monotonic_millis();
    char summary[128];
    int rc;

    rc = a90_userland_scan();
    a90_userland_summary(summary, sizeof(summary));
    if (a90_userland_has_any()) {
        selftest_record_elapsed("userland",
                                A90_SELFTEST_PASS,
                                0,
                                0,
                                started_ms,
                                summary);
    } else {
        selftest_record_elapsed("userland",
                                A90_SELFTEST_WARN,
                                rc,
                                ENOENT,
                                started_ms,
                                summary);
    }
}

static void selftest_metrics(void) {
    long started_ms = monotonic_millis();
    struct a90_metrics_snapshot snapshot;
    char detail[128];
    bool core_ok;

    a90_metrics_read_snapshot(&snapshot);
    core_ok = strcmp(snapshot.memory, "?") != 0 &&
              strcmp(snapshot.loadavg, "?") != 0 &&
              strcmp(snapshot.uptime, "?") != 0;
    snprintf(detail,
             sizeof(detail),
             "mem=%.32s load=%.16s uptime=%.16s",
             snapshot.memory,
             snapshot.loadavg,
             snapshot.uptime);
    selftest_record_elapsed("metrics",
                            core_ok ? A90_SELFTEST_PASS : A90_SELFTEST_WARN,
                            core_ok ? 0 : -ENOENT,
                            core_ok ? 0 : ENOENT,
                            started_ms,
                            detail);
}

static void selftest_kms(void) {
    long started_ms = monotonic_millis();
    struct a90_kms_info info;
    struct a90_fb *fb = a90_kms_framebuffer();
    char detail[128];
    bool ok;

    a90_kms_info(&info);
    ok = info.initialized && fb != NULL && fb->pixels != NULL &&
         fb->width > 0 && fb->height > 0;
    if (ok) {
        snprintf(detail,
                 sizeof(detail),
                 "%ux%u fb=%u crtc=%u",
                 info.width,
                 info.height,
                 info.fb_id,
                 info.crtc_id);
    } else {
        snprintf(detail, sizeof(detail), "kms not initialized");
    }
    selftest_record_elapsed("kms",
                            ok ? A90_SELFTEST_PASS : A90_SELFTEST_FAIL,
                            ok ? 0 : -ENODEV,
                            ok ? 0 : ENODEV,
                            started_ms,
                            detail);
}

static int selftest_open_event(const char *path) {
    int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);

    if (fd < 0) {
        return -1;
    }
    close(fd);
    return 0;
}

static void selftest_input(void) {
    long started_ms = monotonic_millis();
    bool event0_ok = selftest_open_event("/dev/input/event0") == 0;
    bool event3_ok = selftest_open_event("/dev/input/event3") == 0;
    char detail[128];

    snprintf(detail,
             sizeof(detail),
             "event0=%s event3=%s",
             event0_ok ? "ok" : "fail",
             event3_ok ? "ok" : "fail");
    selftest_record_elapsed("input",
                            event0_ok && event3_ok ? A90_SELFTEST_PASS : A90_SELFTEST_FAIL,
                            event0_ok && event3_ok ? 0 : -ENODEV,
                            event0_ok && event3_ok ? 0 : ENODEV,
                            started_ms,
                            detail);
}

static void selftest_service(void) {
    long started_ms = monotonic_millis();
    struct a90_netservice_status net_status;
    char detail[128];

    a90_netservice_status(&net_status);
    snprintf(detail,
             sizeof(detail),
             "hud=%ld tcpctl=%ld adbd=%ld rshell=%ld ncm=%s",
             (long)a90_service_pid(A90_SERVICE_HUD),
             net_status.tcpctl_running ? (long)net_status.tcpctl_pid : -1L,
             (long)a90_service_pid(A90_SERVICE_ADBD),
             (long)a90_service_pid(A90_SERVICE_RSHELL),
             net_status.ncm_present ? "yes" : "no");
    selftest_record_elapsed("service",
                            A90_SELFTEST_PASS,
                            0,
                            0,
                            started_ms,
                            detail);
}

static void selftest_longsoak(void) {
    long started_ms = monotonic_millis();
    struct a90_longsoak_status status;
    enum a90_selftest_result result = A90_SELFTEST_PASS;
    int code = 0;
    int saved_errno = 0;
    char detail[128];

    if (a90_longsoak_get_status(&status) < 0) {
        selftest_record_elapsed("longsoak",
                                A90_SELFTEST_WARN,
                                -EIO,
                                EIO,
                                started_ms,
                                "status unavailable");
        return;
    }
    if (status.stale) {
        result = A90_SELFTEST_WARN;
        code = -ETIMEDOUT;
        saved_errno = ETIMEDOUT;
    }
    snprintf(detail,
             sizeof(detail),
             "health=%s running=%s samples=%u age=%ldms max=%ldms",
             status.health,
             status.running ? "yes" : "no",
             status.samples,
             status.last_age_ms,
             status.expected_max_age_ms);
    selftest_record_elapsed("longsoak",
                            result,
                            code,
                            saved_errno,
                            started_ms,
                            detail);
}

static void selftest_usb(void) {
    long started_ms = monotonic_millis();
    struct a90_usb_gadget_status status;
    bool status_ok = a90_usb_gadget_status(&status) == 0;
    char detail[128];

    snprintf(detail,
             sizeof(detail),
             "acm=%s f1=%s adb=%s udc=%s",
             status_ok && status.acm_function ? "yes" : "no",
             status_ok && status.acm_link ? "yes" : "no",
             status_ok && status.adb_link ? "yes" : "no",
             status_ok && status.udc_bound ? status.udc : "none");
    selftest_record_elapsed("usb",
                            status_ok && status.acm_function &&
                                    status.acm_link && status.udc_bound ?
                                    A90_SELFTEST_PASS : A90_SELFTEST_FAIL,
                            status_ok && status.acm_function &&
                                    status.acm_link && status.udc_bound ? 0 : -ENODEV,
                            status_ok && status.acm_function &&
                                    status.acm_link && status.udc_bound ? 0 : ENODEV,
                            started_ms,
                            detail);
}

static int selftest_run(const struct a90_selftest_boot_hooks *hooks, void *ctx, bool boot) {
    long started_ms = monotonic_millis();
    char summary[96];

    selftest_reset();
    a90_logf("selftest", "%s run start", boot ? "boot" : "manual");
    if (hooks != NULL && hooks->set_line != NULL) {
        hooks->set_line(ctx, 5, "[ SELF  ] RUNNING");
    }
    if (hooks != NULL && hooks->draw_frame != NULL) {
        hooks->draw_frame(ctx);
    }

    selftest_log();
    selftest_timeline();
    selftest_storage();
    selftest_runtime();
    selftest_helpers();
    selftest_userland();
    selftest_metrics();
    selftest_kms();
    selftest_input();
    selftest_service();
    selftest_longsoak();
    selftest_usb();

    selftest_duration_ms = monotonic_millis() - started_ms;
    if (selftest_duration_ms < 0) {
        selftest_duration_ms = 0;
    }
    a90_selftest_summary(summary, sizeof(summary));
    a90_logf("selftest", "%s run end %s", boot ? "boot" : "manual", summary);
    if (boot) {
        a90_timeline_record(0,
                            0,
                            "selftest",
                            "%s",
                            summary);
    }
    if (hooks != NULL && hooks->set_line != NULL) {
        hooks->set_line(ctx, 5, selftest_fail_count > 0 ? "[ SELF  ] FAIL SEE LOG" :
                                (selftest_warn_count > 0 ? "[ SELF  ] WARN SEE LOG" :
                                "[ SELF  ] PASS"));
    }
    if (hooks != NULL && hooks->draw_frame != NULL) {
        hooks->draw_frame(ctx);
    }
    return selftest_fail_count > 0 ? -EIO : 0;
}

int a90_selftest_run_boot(const struct a90_selftest_boot_hooks *hooks, void *ctx) {
    return selftest_run(hooks, ctx, true);
}

int a90_selftest_run_manual(void) {
    return selftest_run(NULL, NULL, false);
}

void a90_selftest_summary(char *out, size_t out_size) {
    if (out_size == 0) {
        return;
    }
    snprintf(out,
             out_size,
             "pass=%u warn=%u fail=%u duration=%ldms",
             selftest_pass_count,
             selftest_warn_count,
             selftest_fail_count,
             selftest_duration_ms);
}

size_t a90_selftest_count(void) {
    return selftest_entry_count;
}

const struct a90_selftest_entry *a90_selftest_entry_at(size_t index) {
    if (index >= selftest_entry_count || index >= A90_SELFTEST_MAX_ENTRIES) {
        return NULL;
    }
    return &selftest_entries[index];
}

bool a90_selftest_has_failures(void) {
    return selftest_fail_count > 0;
}
