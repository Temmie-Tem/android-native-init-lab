#include "a90_runtime.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_timeline.h"
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

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static struct a90_runtime_status runtime_state = {
    .initialized = false,
    .fallback = true,
    .writable = false,
    .backend = "unknown",
    .root = A90_RUNTIME_CACHE_ROOT,
    .warning = "runtime not initialized",
};

static void runtime_join_path(char *out, size_t out_size, const char *root, const char *name) {
    if (out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s/%s", root, name);
    out[out_size - 1] = '\0';
}

static void runtime_fill_paths(const char *root) {
    snprintf(runtime_state.root, sizeof(runtime_state.root), "%s", root);
    runtime_join_path(runtime_state.bin, sizeof(runtime_state.bin), root, A90_RUNTIME_BIN_DIR);
    runtime_join_path(runtime_state.etc, sizeof(runtime_state.etc), root, A90_RUNTIME_ETC_DIR);
    runtime_join_path(runtime_state.logs, sizeof(runtime_state.logs), root, A90_RUNTIME_LOGS_DIR);
    runtime_join_path(runtime_state.tmp, sizeof(runtime_state.tmp), root, A90_RUNTIME_TMP_DIR);
    runtime_join_path(runtime_state.state, sizeof(runtime_state.state), root, A90_RUNTIME_STATE_DIR);
    runtime_join_path(runtime_state.pkg, sizeof(runtime_state.pkg), root, A90_RUNTIME_PKG_DIR);
    runtime_join_path(runtime_state.run, sizeof(runtime_state.run), root, A90_RUNTIME_RUN_DIR);
    runtime_join_path(runtime_state.pkg_bin, sizeof(runtime_state.pkg_bin), root, A90_RUNTIME_PKG_BIN_DIR);
    runtime_join_path(runtime_state.pkg_helpers, sizeof(runtime_state.pkg_helpers), root, A90_RUNTIME_PKG_HELPERS_DIR);
    runtime_join_path(runtime_state.pkg_services, sizeof(runtime_state.pkg_services), root, A90_RUNTIME_PKG_SERVICES_DIR);
    runtime_join_path(runtime_state.pkg_manifests, sizeof(runtime_state.pkg_manifests), root, A90_RUNTIME_PKG_MANIFESTS_DIR);
    runtime_join_path(runtime_state.state_services, sizeof(runtime_state.state_services), root, A90_RUNTIME_STATE_SERVICES_DIR);
    runtime_join_path(runtime_state.helper_manifest, sizeof(runtime_state.helper_manifest), runtime_state.pkg_manifests, A90_HELPER_MANIFEST_NAME);
    runtime_join_path(runtime_state.helper_state, sizeof(runtime_state.helper_state), runtime_state.state, A90_HELPER_STATE_NAME);
    runtime_join_path(runtime_state.helper_deploy_log, sizeof(runtime_state.helper_deploy_log), runtime_state.logs, A90_HELPER_DEPLOY_LOG_NAME);
}

static int runtime_ensure_one_dir(const char *path, mode_t mode) {
    if (ensure_dir(path, mode) < 0) {
        return -1;
    }
    if (chmod(path, mode) < 0) {
        return -1;
    }
    return 0;
}

static int runtime_ensure_dirs(void) {
    struct runtime_dir_spec {
        const char *path;
        mode_t mode;
    } dirs[] = {
        { runtime_state.root, 0755 },
        { runtime_state.bin, 0755 },
        { runtime_state.etc, 0755 },
        { runtime_state.logs, 0700 },
        { runtime_state.tmp, 0700 },
        { runtime_state.state, 0700 },
        { runtime_state.pkg, 0755 },
        { runtime_state.run, 0700 },
        { runtime_state.pkg_bin, 0755 },
        { runtime_state.pkg_helpers, 0755 },
        { runtime_state.pkg_services, 0755 },
        { runtime_state.pkg_manifests, 0755 },
        { runtime_state.state_services, 0700 },
    };
    size_t index;

    for (index = 0; index < sizeof(dirs) / sizeof(dirs[0]); ++index) {
        if (runtime_ensure_one_dir(dirs[index].path, dirs[index].mode) < 0) {
            return -1;
        }
    }
    return 0;
}

static int runtime_write_probe(const char *dir) {
    char path[PATH_MAX];
    int fd;
    const char payload[] = "a90-runtime-ok\n";

    runtime_join_path(path, sizeof(path), dir, A90_RUNTIME_RW_TEST_NAME);
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -1;
    }
    if (write_all_checked(fd, payload, strlen(payload)) < 0 ||
        fsync(fd) < 0) {
        int saved_errno = errno;

        close(fd);
        unlink(path);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;

        unlink(path);
        errno = saved_errno;
        return -1;
    }
    if (unlink(path) < 0) {
        return -1;
    }
    return 0;
}

static void runtime_set_failure(const char *reason, int saved_errno) {
    runtime_state.initialized = true;
    runtime_state.fallback = true;
    runtime_state.writable = false;
    snprintf(runtime_state.backend, sizeof(runtime_state.backend), "%s", "cache");
    runtime_fill_paths(A90_RUNTIME_CACHE_ROOT);
    snprintf(runtime_state.warning,
             sizeof(runtime_state.warning),
             "runtime fallback: %s",
             reason);
    snprintf(runtime_state.detail,
             sizeof(runtime_state.detail),
             "%s errno=%d error=%s",
             reason,
             saved_errno,
             strerror(saved_errno));
}

int a90_runtime_init(const struct a90_storage_status *storage) {
    bool use_sd = storage != NULL &&
                  !storage->fallback &&
                  storage->sd_mounted &&
                  storage->sd_expected &&
                  storage->sd_rw_ok;
    int saved_errno = 0;

    memset(&runtime_state, 0, sizeof(runtime_state));
    runtime_state.initialized = true;
    runtime_state.fallback = !use_sd;
    snprintf(runtime_state.backend,
             sizeof(runtime_state.backend),
             "%s",
             use_sd ? "sd" : "cache");
    runtime_fill_paths(use_sd ? A90_RUNTIME_SD_ROOT : A90_RUNTIME_CACHE_ROOT);

    if (!use_sd) {
        snprintf(runtime_state.warning,
                 sizeof(runtime_state.warning),
                 "%s",
                 "runtime using cache fallback");
    }

    if (runtime_ensure_dirs() < 0) {
        saved_errno = errno;
        if (use_sd) {
            runtime_set_failure("sd runtime mkdir failed", saved_errno);
            if (runtime_ensure_dirs() < 0) {
                saved_errno = errno;
                snprintf(runtime_state.detail,
                         sizeof(runtime_state.detail),
                         "cache runtime mkdir failed errno=%d error=%s",
                         saved_errno,
                         strerror(saved_errno));
                a90_logf("runtime", "%s", runtime_state.detail);
                a90_timeline_record(-saved_errno,
                                    saved_errno,
                                    "runtime",
                                    "%s",
                                    runtime_state.detail);
                errno = saved_errno;
                return -saved_errno;
            }
        } else {
            snprintf(runtime_state.detail,
                     sizeof(runtime_state.detail),
                     "cache runtime mkdir failed errno=%d error=%s",
                     saved_errno,
                     strerror(saved_errno));
            a90_logf("runtime", "%s", runtime_state.detail);
            a90_timeline_record(-saved_errno,
                                saved_errno,
                                "runtime",
                                "%s",
                                runtime_state.detail);
            errno = saved_errno;
            return -saved_errno;
        }
    }

    if (runtime_write_probe(runtime_state.tmp) < 0 ||
        runtime_write_probe(runtime_state.state) < 0 ||
        runtime_write_probe(runtime_state.run) < 0) {
        saved_errno = errno;
        if (use_sd) {
            runtime_set_failure("sd runtime rw probe failed", saved_errno);
            if (runtime_ensure_dirs() < 0 ||
                runtime_write_probe(runtime_state.tmp) < 0 ||
                runtime_write_probe(runtime_state.state) < 0 ||
                runtime_write_probe(runtime_state.run) < 0) {
                saved_errno = errno;
                snprintf(runtime_state.detail,
                         sizeof(runtime_state.detail),
                         "cache runtime rw failed errno=%d error=%s",
                         saved_errno,
                         strerror(saved_errno));
                a90_logf("runtime", "%s", runtime_state.detail);
                a90_timeline_record(-saved_errno,
                                    saved_errno,
                                    "runtime",
                                    "%s",
                                    runtime_state.detail);
                errno = saved_errno;
                return -saved_errno;
            }
        } else {
            snprintf(runtime_state.detail,
                     sizeof(runtime_state.detail),
                     "cache runtime rw failed errno=%d error=%s",
                     saved_errno,
                     strerror(saved_errno));
            a90_logf("runtime", "%s", runtime_state.detail);
            a90_timeline_record(-saved_errno,
                                saved_errno,
                                "runtime",
                                "%s",
                                runtime_state.detail);
            errno = saved_errno;
            return -saved_errno;
        }
    }

    runtime_state.writable = true;
    if (runtime_state.detail[0] == '\0') {
        snprintf(runtime_state.detail,
                 sizeof(runtime_state.detail),
                 "root=%.72s bin=%.48s logs=%.48s",
                 runtime_state.root,
                 runtime_state.bin,
                 runtime_state.logs);
    }
    a90_logf("runtime",
             "backend=%s root=%s fallback=%s writable=%s",
             runtime_state.backend,
             runtime_state.root,
             runtime_state.fallback ? "yes" : "no",
             runtime_state.writable ? "yes" : "no");
    a90_timeline_record(0,
                        0,
                        "runtime",
                        "%s root=%s",
                        runtime_state.backend,
                        runtime_state.root);
    return 0;
}

int a90_runtime_get_status(struct a90_runtime_status *out) {
    if (out == NULL) {
        errno = EINVAL;
        return -1;
    }
    *out = runtime_state;
    return 0;
}

const char *a90_runtime_root(void) {
    return runtime_state.root;
}

const char *a90_runtime_bin_dir(void) {
    return runtime_state.bin;
}

const char *a90_runtime_log_dir(void) {
    return runtime_state.logs;
}

const char *a90_runtime_tmp_dir(void) {
    return runtime_state.tmp;
}

const char *a90_runtime_state_dir(void) {
    return runtime_state.state;
}

const char *a90_runtime_warning(void) {
    return runtime_state.warning;
}

bool a90_runtime_using_fallback(void) {
    return runtime_state.fallback;
}

int a90_runtime_cmd_runtime(void) {
    a90_console_printf("runtime: backend=%s root=%s fallback=%s writable=%s initialized=%s\r\n",
            runtime_state.backend,
            runtime_state.root,
            runtime_state.fallback ? "yes" : "no",
            runtime_state.writable ? "yes" : "no",
            runtime_state.initialized ? "yes" : "no");
    a90_console_printf("runtime: bin=%s\r\n", runtime_state.bin);
    a90_console_printf("runtime: etc=%s\r\n", runtime_state.etc);
    a90_console_printf("runtime: logs=%s\r\n", runtime_state.logs);
    a90_console_printf("runtime: tmp=%s\r\n", runtime_state.tmp);
    a90_console_printf("runtime: state=%s\r\n", runtime_state.state);
    a90_console_printf("runtime: pkg=%s\r\n", runtime_state.pkg);
    a90_console_printf("runtime: run=%s\r\n", runtime_state.run);
    a90_console_printf("runtime: pkg_bin=%s\r\n", runtime_state.pkg_bin);
    a90_console_printf("runtime: pkg_helpers=%s\r\n", runtime_state.pkg_helpers);
    a90_console_printf("runtime: pkg_services=%s\r\n", runtime_state.pkg_services);
    a90_console_printf("runtime: pkg_manifests=%s\r\n", runtime_state.pkg_manifests);
    a90_console_printf("runtime: state_services=%s\r\n", runtime_state.state_services);
    a90_console_printf("runtime: helper_manifest=%s\r\n", runtime_state.helper_manifest);
    a90_console_printf("runtime: helper_state=%s\r\n", runtime_state.helper_state);
    a90_console_printf("runtime: helper_deploy_log=%s\r\n", runtime_state.helper_deploy_log);
    if (runtime_state.warning[0] != '\0') {
        a90_console_printf("runtime: warning=%s\r\n", runtime_state.warning);
    }
    a90_console_printf("runtime: detail=%s\r\n", runtime_state.detail);
    return runtime_state.writable ? 0 : -EIO;
}
