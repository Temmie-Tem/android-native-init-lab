#include "a90_diag.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_exposure.h"
#include "a90_helper.h"
#include "a90_log.h"
#include "a90_netservice.h"
#include "a90_runtime.h"
#include "a90_selftest.h"
#include "a90_service.h"
#include "a90_storage.h"
#include "a90_timeline.h"
#include "a90_userland.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define A90_DIAG_TAIL_BYTES 8192
#define A90_DIAG_BUNDLE_TAIL_BYTES 16384

struct a90_diag_sink {
    int fd;
    bool console;
};

static void diag_emit(struct a90_diag_sink *sink, const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (len < 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
        buf[len] = '\0';
    }

    if (sink->console) {
        a90_console_write(buf, (size_t)len);
    }
    if (sink->fd >= 0) {
        (void)write_all_checked(sink->fd, buf, (size_t)len);
    }
}

static const char *diag_yesno(bool value) {
    return value ? "yes" : "no";
}

static void diag_runtime_state_path(char *out, size_t out_size, const char *name) {
    const char *state_dir = a90_runtime_state_dir();

    if (out == NULL || out_size == 0) {
        return;
    }
    if (state_dir == NULL || state_dir[0] == '\0') {
        state_dir = A90_RUNTIME_CACHE_ROOT "/" A90_RUNTIME_STATE_DIR;
    }
    snprintf(out, out_size, "%s/%s", state_dir, name);
    out[out_size - 1] = '\0';
}

static int diag_file_mode(const char *path, char *out, size_t out_size, bool *owner_only) {
    struct stat st;

    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "missing");
    }
    if (owner_only != NULL) {
        *owner_only = false;
    }
    if (path == NULL || path[0] == '\0') {
        return -EINVAL;
    }
    if (stat(path, &st) < 0) {
        return -errno;
    }
    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "0%03o", (unsigned)(st.st_mode & 0777));
    }
    if (owner_only != NULL) {
        *owner_only = (st.st_mode & 0077) == 0;
    }
    return 0;
}

const char *a90_diag_default_dir(void) {
    const char *runtime_logs = a90_runtime_log_dir();

    if (runtime_logs != NULL && runtime_logs[0] != '\0') {
        return runtime_logs;
    }
    return NATIVE_LOG_FALLBACK_DIR;
}

static void diag_emit_file_tail(struct a90_diag_sink *sink, const char *path, size_t max_bytes) {
    char buf[512];
    struct stat st;
    off_t offset = 0;
    int fd;

    if (path == NULL || path[0] == '\0') {
        diag_emit(sink, "file: missing path\r\n");
        return;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        diag_emit(sink, "file: %s open failed errno=%d error=%s\r\n", path, errno, strerror(errno));
        return;
    }

    if (fstat(fd, &st) == 0 && st.st_size > (off_t)max_bytes) {
        offset = st.st_size - (off_t)max_bytes;
        (void)lseek(fd, offset, SEEK_SET);
        diag_emit(sink, "... tail from byte %ld of %ld ...\r\n", (long)offset, (long)st.st_size);
    }

    for (;;) {
        ssize_t rd = read(fd, buf, sizeof(buf));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            diag_emit(sink, "file: %s read failed errno=%d error=%s\r\n", path, errno, strerror(errno));
            break;
        }
        if (rd == 0) {
            break;
        }
        if (sink->console) {
            a90_console_write(buf, (size_t)rd);
        }
        if (sink->fd >= 0) {
            (void)write_all_checked(sink->fd, buf, (size_t)rd);
        }
    }

    close(fd);
    diag_emit(sink, "\r\n");
}

static void diag_emit_version(struct a90_diag_sink *sink) {
    struct utsname uts;

    diag_emit(sink, "[version]\r\n");
    diag_emit(sink, "banner=%s\r\n", INIT_BANNER);
    diag_emit(sink, "creator=%s\r\n", INIT_CREATOR);
    diag_emit(sink, "version=%s build=%s\r\n", INIT_VERSION, INIT_BUILD);
    if (uname(&uts) == 0) {
        diag_emit(sink, "kernel=%s %s %s\r\n", uts.sysname, uts.release, uts.machine);
    }
}

static void diag_emit_bootstatus(struct a90_diag_sink *sink) {
    char boot_summary[64];
    size_t count;

    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));
    count = a90_timeline_count();
    diag_emit(sink, "[bootstatus]\r\n");
    diag_emit(sink, "boot=%s\r\n", boot_summary);
    diag_emit(sink, "timeline_entries=%ld/%d\r\n", (long)count, BOOT_TIMELINE_MAX);
}

static void diag_emit_timeline(struct a90_diag_sink *sink) {
    size_t count = a90_timeline_count();
    size_t index;

    diag_emit(sink, "[timeline]\r\n");
    for (index = 0; index < count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct a90_timeline_entry *entry = a90_timeline_entry_at(index);

        if (entry == NULL) {
            continue;
        }
        diag_emit(sink,
                  "%02ld %8ldms %-18s rc=%d errno=%d %s\r\n",
                  (long)index,
                  entry->ms,
                  entry->step,
                  entry->code,
                  entry->saved_errno,
                  entry->detail);
    }
}

static void diag_emit_selftest(struct a90_diag_sink *sink, bool verbose) {
    char summary[96];
    size_t count;
    size_t index;

    a90_selftest_summary(summary, sizeof(summary));
    count = a90_selftest_count();
    diag_emit(sink, "[selftest]\r\n");
    diag_emit(sink, "summary=%s entries=%ld\r\n", summary, (long)count);

    if (!verbose) {
        return;
    }

    for (index = 0; index < count; ++index) {
        const struct a90_selftest_entry *entry = a90_selftest_entry_at(index);

        if (entry == NULL) {
            continue;
        }
        diag_emit(sink,
                  "%02ld %-9s %-8s rc=%d errno=%d %ldms %s\r\n",
                  (long)index,
                  a90_selftest_result_name(entry->result),
                  entry->name,
                  entry->code,
                  entry->saved_errno,
                  entry->duration_ms,
                  entry->detail);
    }
}

static void diag_emit_storage(struct a90_diag_sink *sink) {
    struct a90_storage_status storage;

    memset(&storage, 0, sizeof(storage));
    (void)a90_storage_get_status(&storage);
    diag_emit(sink, "[storage]\r\n");
    diag_emit(sink,
              "backend=%s root=%s fallback=%s probed=%s sd_present=%s mounted=%s expected=%s rw=%s\r\n",
              storage.backend,
              storage.root,
              diag_yesno(storage.fallback),
              diag_yesno(storage.probed),
              diag_yesno(storage.sd_present),
              diag_yesno(storage.sd_mounted),
              diag_yesno(storage.sd_expected),
              diag_yesno(storage.sd_rw_ok));
    diag_emit(sink, "sd_uuid=%s\r\n", storage.sd_uuid);
    if (storage.warning[0] != '\0') {
        diag_emit(sink, "warning=%s\r\n", storage.warning);
    }
    diag_emit(sink, "detail=%s\r\n", storage.detail);
}

static void diag_emit_runtime(struct a90_diag_sink *sink) {
    struct a90_runtime_status runtime;

    memset(&runtime, 0, sizeof(runtime));
    (void)a90_runtime_get_status(&runtime);
    diag_emit(sink, "[runtime]\r\n");
    diag_emit(sink,
              "initialized=%s backend=%s root=%s fallback=%s writable=%s\r\n",
              diag_yesno(runtime.initialized),
              runtime.backend,
              runtime.root,
              diag_yesno(runtime.fallback),
              diag_yesno(runtime.writable));
    diag_emit(sink, "bin=%s\r\n", runtime.bin);
    diag_emit(sink, "etc=%s\r\n", runtime.etc);
    diag_emit(sink, "logs=%s\r\n", runtime.logs);
    diag_emit(sink, "tmp=%s\r\n", runtime.tmp);
    diag_emit(sink, "state=%s\r\n", runtime.state);
    diag_emit(sink, "pkg=%s\r\n", runtime.pkg);
    diag_emit(sink, "run=%s\r\n", runtime.run);
    diag_emit(sink, "pkg_bin=%s\r\n", runtime.pkg_bin);
    diag_emit(sink, "pkg_helpers=%s\r\n", runtime.pkg_helpers);
    diag_emit(sink, "pkg_services=%s\r\n", runtime.pkg_services);
    diag_emit(sink, "pkg_manifests=%s\r\n", runtime.pkg_manifests);
    diag_emit(sink, "state_services=%s\r\n", runtime.state_services);
    diag_emit(sink, "helper_manifest=%s\r\n", runtime.helper_manifest);
    diag_emit(sink, "helper_state=%s\r\n", runtime.helper_state);
    diag_emit(sink, "helper_deploy_log=%s\r\n", runtime.helper_deploy_log);
    if (runtime.warning[0] != '\0') {
        diag_emit(sink, "warning=%s\r\n", runtime.warning);
    }
    diag_emit(sink, "detail=%s\r\n", runtime.detail);
}

static void diag_emit_helpers(struct a90_diag_sink *sink, bool verbose) {
    char summary[128];
    int count;
    int index;

    a90_helper_summary(summary, sizeof(summary));
    count = a90_helper_count();
    diag_emit(sink, "[helpers]\r\n");
    diag_emit(sink,
              "summary=%s entries=%d manifest=%s deploy_log=%s\r\n",
              summary,
              count,
              a90_helper_manifest_path(),
              a90_helper_deploy_log_path());

    if (!verbose) {
        return;
    }

    for (index = 0; index < count; ++index) {
        struct a90_helper_entry entry;

        if (a90_helper_entry_at(index, &entry) < 0) {
            continue;
        }
        diag_emit(sink,
                  "%02d name=%s role=%s present=%s exec=%s required=%s manifest=%s preferred=%s fallback=%s size=%lld mode=0%03o expected_sha=%s actual_sha=%s hash_checked=%s hash_match=%s warning=%s\r\n",
                  index,
                  entry.name,
                  entry.role,
                  diag_yesno(entry.present),
                  diag_yesno(entry.executable),
                  diag_yesno(entry.required),
                  diag_yesno(entry.manifest_entry),
                  entry.preferred,
                  entry.fallback,
                  entry.actual_size,
                  entry.actual_mode,
                  entry.expected_sha256[0] != '\0' ? entry.expected_sha256 : "-",
                  entry.actual_sha256[0] != '\0' ? entry.actual_sha256 : "-",
                  diag_yesno(entry.hash_checked),
                  diag_yesno(entry.hash_match),
                  entry.warning);
    }
}

static void diag_emit_userland(struct a90_diag_sink *sink, bool verbose) {
    char summary[128];
    int count;
    int index;

    a90_userland_summary(summary, sizeof(summary));
    count = a90_userland_count();
    diag_emit(sink, "[userland]\r\n");
    diag_emit(sink, "summary=%s entries=%d\r\n", summary, count);

    if (!verbose) {
        return;
    }

    for (index = 0; index < count; ++index) {
        struct a90_userland_entry entry;

        if (a90_userland_entry_at(index, &entry) < 0) {
            continue;
        }
        diag_emit(sink,
                  "%02d name=%s present=%s exec=%s selected=%s runtime=%s fallback=%s size=%lld warning=%s\r\n",
                  index,
                  entry.name,
                  diag_yesno(entry.present),
                  diag_yesno(entry.executable),
                  entry.selected_path,
                  entry.runtime_path,
                  entry.fallback_path,
                  entry.size,
                  entry.warning);
    }
}

static void diag_emit_services(struct a90_diag_sink *sink) {
    int count;
    int index;

    a90_service_reap_all();
    count = a90_service_count();
    diag_emit(sink, "[service]\r\n");
    for (index = 0; index < count; ++index) {
        enum a90_service_id id = a90_service_id_at(index);
        struct a90_service_info info;

        if (a90_service_info(id, &info) < 0) {
            continue;
        }
        diag_emit(sink,
                  "name=%s kind=%s running=%s pid=%ld enabled=%s flags=0x%x enable_path=%s desc=%s\r\n",
                  info.name,
                  a90_service_kind_name(info.kind),
                  diag_yesno(info.running),
                  (long)info.pid,
                  diag_yesno(info.enabled),
                  info.flags,
                  info.enable_path != NULL ? info.enable_path : "-",
                  info.description);
    }
}

static void diag_emit_network(struct a90_diag_sink *sink) {
    struct a90_netservice_status status;

    memset(&status, 0, sizeof(status));
    (void)a90_netservice_status(&status);
    diag_emit(sink, "[network]\r\n");
    diag_emit(sink,
              "netservice enabled=%s ncm=%s if=%s ip=%s/%s tcpctl=%s pid=%ld port=%s flag=%s log=%s\r\n",
              diag_yesno(status.enabled),
              diag_yesno(status.ncm_present),
              status.ifname,
              status.device_ip,
              status.netmask,
              diag_yesno(status.tcpctl_running),
              (long)status.tcpctl_pid,
              status.tcp_port,
              status.flag_path,
              status.log_path);
    diag_emit(sink,
              "helpers usbnet=%s tcpctl=%s toybox=%s idle=%ss max_clients=%s\r\n",
              diag_yesno(status.usbnet_helper),
              diag_yesno(status.tcpctl_helper),
              diag_yesno(status.toybox_helper),
              status.tcp_idle_seconds,
              status.tcp_max_clients);
}

static void diag_emit_rshell(struct a90_diag_sink *sink) {
    struct a90_service_info info;
    struct a90_netservice_status net_status;
    char flag_path[PATH_MAX];
    char token_path[PATH_MAX];
    char token_mode[16];
    const char *helper_path;
    const char *busybox_path;
    bool token_owner_only = false;
    bool token_present;

    memset(&info, 0, sizeof(info));
    memset(&net_status, 0, sizeof(net_status));
    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    (void)a90_service_info(A90_SERVICE_RSHELL, &info);
    (void)a90_netservice_status(&net_status);
    diag_runtime_state_path(flag_path, sizeof(flag_path), A90_RSHELL_FLAG_NAME);
    diag_runtime_state_path(token_path, sizeof(token_path), A90_RSHELL_TOKEN_NAME);
    token_present = diag_file_mode(token_path,
                                   token_mode,
                                   sizeof(token_mode),
                                   &token_owner_only) == 0;
    helper_path = a90_helper_preferred_path("a90_rshell", A90_RSHELL_RAMDISK_HELPER);
    busybox_path = a90_userland_path("busybox");
    if (busybox_path == NULL || busybox_path[0] == '\0') {
        busybox_path = a90_helper_preferred_path("busybox", A90_BUSYBOX_HELPER);
    }

    diag_emit(sink, "[rshell]\r\n");
    diag_emit(sink,
              "running=%s pid=%ld enabled=%s bind=%s port=%s idle=%ss helper=%s helper_present=%s busybox=%s busybox_present=%s token=%s token_mode=%s token_owner_only=%s flag_path=%s token_path=%s ncm=%s tcpctl=%s log=%s token_value=hidden\r\n",
              diag_yesno(info.running),
              (long)info.pid,
              diag_yesno(info.enabled),
              A90_RSHELL_BIND_ADDR,
              A90_RSHELL_PORT,
              A90_RSHELL_IDLE_SECONDS,
              helper_path != NULL && helper_path[0] != '\0' ? helper_path : "-",
              diag_yesno(helper_path != NULL && helper_path[0] != '\0' && access(helper_path, X_OK) == 0),
              busybox_path != NULL && busybox_path[0] != '\0' ? busybox_path : "-",
              diag_yesno(busybox_path != NULL && busybox_path[0] != '\0' && access(busybox_path, X_OK) == 0),
              token_present ? "present" : "missing",
              token_mode,
              diag_yesno(token_owner_only),
              flag_path,
              token_path,
              diag_yesno(net_status.ncm_present),
              diag_yesno(net_status.tcpctl_running),
              A90_RSHELL_LOG_PATH);
}

static void diag_emit_exposure(struct a90_diag_sink *sink) {
    struct a90_exposure_snapshot exposure;
    char summary[192];

    memset(&exposure, 0, sizeof(exposure));
    if (a90_exposure_collect(&exposure) < 0) {
        diag_emit(sink, "[exposure]\r\nstatus=unavailable\r\n");
        return;
    }
    a90_exposure_summary(&exposure, summary, sizeof(summary));
    diag_emit(sink, "[exposure]\r\n");
    diag_emit(sink, "summary=%s\r\n", summary);
    diag_emit(sink,
              "acm=%s trusted_lab_only=%s bridge_host=127.0.0.1 bridge_identity_pin=expected\r\n",
              diag_yesno(exposure.usb_acm_present),
              diag_yesno(exposure.usb_acm_trusted_local));
    diag_emit(sink,
              "ncm=%s if=%s ip=%s/%s netservice=%s flag=%s\r\n",
              diag_yesno(exposure.ncm_present),
              exposure.ncm_ifname != NULL ? exposure.ncm_ifname : "-",
              exposure.ncm_device_ip != NULL ? exposure.ncm_device_ip : "-",
              exposure.ncm_netmask != NULL ? exposure.ncm_netmask : "-",
              exposure.netservice_enabled ? "enabled" : "disabled",
              exposure.netservice_flag_present ? "present" : "absent");
    diag_emit(sink,
              "tcpctl=%s pid=%ld bind=%s port=%s auth=required token=%s mode=%s owner_only=%s token_path=%s token_value=hidden\r\n",
              exposure.tcpctl_running ? "running" : "stopped",
              (long)exposure.tcpctl_pid,
              exposure.tcpctl_bind_addr != NULL ? exposure.tcpctl_bind_addr : "-",
              exposure.tcpctl_port != NULL ? exposure.tcpctl_port : "-",
              exposure.tcpctl_token_present ? "present" : "missing",
              exposure.tcpctl_token_mode,
              diag_yesno(exposure.tcpctl_token_owner_only),
              exposure.tcpctl_token_path != NULL ? exposure.tcpctl_token_path : "-");
    diag_emit(sink,
              "rshell=%s pid=%ld bind=%s port=%s flag=%s token=%s mode=%s owner_only=%s flag_path=%s token_path=%s token_value=hidden\r\n",
              exposure.rshell_running ? "running" : "stopped",
              (long)exposure.rshell_pid,
              exposure.rshell_bind_addr != NULL ? exposure.rshell_bind_addr : "-",
              exposure.rshell_port != NULL ? exposure.rshell_port : "-",
              exposure.rshell_flag_present ? "present" : "absent",
              exposure.rshell_token_present ? "present" : "missing",
              exposure.rshell_token_mode,
              diag_yesno(exposure.rshell_token_owner_only),
              exposure.rshell_flag_path,
              exposure.rshell_token_path);
}

static void diag_emit_proc_files(struct a90_diag_sink *sink, bool include_logs, size_t log_tail_bytes) {
    diag_emit(sink, "[mounts]\r\n");
    diag_emit_file_tail(sink, "/proc/mounts", 16384);
    diag_emit(sink, "[partitions]\r\n");
    diag_emit_file_tail(sink, "/proc/partitions", 16384);
    diag_emit(sink, "[logs]\r\n");
    if (!include_logs) {
        diag_emit(sink, "path=<redacted> ready=%s tail=redacted\r\n", diag_yesno(a90_log_ready()));
        diag_emit(sink, "[helper-deploy-log]\r\npath=<redacted> tail=redacted\r\n");
        diag_emit(sink, "[rshell-log]\r\npath=<redacted> tail=redacted\r\n");
        return;
    }
    diag_emit(sink, "path=%s ready=%s\r\n", a90_log_path(), diag_yesno(a90_log_ready()));
    if (include_logs && a90_log_ready()) {
        diag_emit_file_tail(sink, a90_log_path(), log_tail_bytes);
    }
    diag_emit(sink, "[helper-deploy-log]\r\n");
    diag_emit(sink, "path=%s\r\n", a90_helper_deploy_log_path());
    if (include_logs) {
        diag_emit_file_tail(sink, a90_helper_deploy_log_path(), 4096);
    }
    diag_emit(sink, "[rshell-log]\r\n");
    diag_emit(sink, "path=%s\r\n", A90_RSHELL_LOG_PATH);
    if (include_logs) {
        diag_emit_file_tail(sink, A90_RSHELL_LOG_PATH, 4096);
    }
}

static int diag_emit_report(struct a90_diag_sink *sink, bool verbose, bool include_logs, size_t log_tail_bytes) {
    diag_emit(sink, "[A90 DIAG]\r\n");
    diag_emit(sink, "generated_ms=%ld\r\n", monotonic_millis());
    diag_emit_version(sink);
    diag_emit_bootstatus(sink);
    if (verbose) {
        diag_emit_timeline(sink);
    }
    diag_emit_selftest(sink, verbose);
    diag_emit_storage(sink);
    diag_emit_runtime(sink);
    diag_emit_helpers(sink, verbose);
    diag_emit_userland(sink, verbose);
    diag_emit_services(sink);
    diag_emit_network(sink);
    diag_emit_rshell(sink);
    diag_emit_exposure(sink);
    if (verbose) {
        diag_emit_proc_files(sink, include_logs, log_tail_bytes);
    }
    return 0;
}

int a90_diag_print_summary(void) {
    struct a90_diag_sink sink = { .fd = -1, .console = true };

    return diag_emit_report(&sink, false, false, 0);
}

int a90_diag_print_full(void) {
    struct a90_diag_sink sink = { .fd = -1, .console = true };

    return diag_emit_report(&sink, true, false, 0);
}

int a90_diag_write_bundle(char *out_path, size_t out_size) {
    char path[PATH_MAX];
    const char *dir = a90_diag_default_dir();
    struct a90_diag_sink sink;
    int fd;

    if (out_path == NULL || out_size == 0) {
        errno = EINVAL;
        return -EINVAL;
    }

    (void)ensure_dir(dir, 0700);
    (void)chmod(dir, 0700);
    snprintf(path, sizeof(path), "%s/a90-diag-%ld.txt", dir, monotonic_millis());
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0 && strcmp(dir, CACHE_STORAGE_ROOT) != 0) {
        (void)ensure_dir(NATIVE_LOG_FALLBACK_DIR, 0700);
        (void)chmod(NATIVE_LOG_FALLBACK_DIR, 0700);
        snprintf(path, sizeof(path), "%s/a90-diag-%ld.txt", NATIVE_LOG_FALLBACK_DIR, monotonic_millis());
        fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    }
    if (fd < 0) {
        int saved_errno = errno;
        snprintf(out_path, out_size, "%s", path);
        return -saved_errno;
    }

    sink.fd = fd;
    sink.console = false;
    (void)diag_emit_report(&sink, true, false, 0);
    close(fd);

    snprintf(out_path, out_size, "%s", path);
    a90_logf("diag", "bundle written path=%s", path);
    return 0;
}
