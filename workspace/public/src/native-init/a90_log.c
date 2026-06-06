#include "a90_log.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static bool log_ready = false;
static char log_path[PATH_MAX] = NATIVE_LOG_FALLBACK;

static void a90_log_prepare_private_fallback_dir(const char *path) {
    if (path == NULL || strncmp(path, NATIVE_LOG_FALLBACK_DIR, strlen(NATIVE_LOG_FALLBACK_DIR)) != 0) {
        return;
    }
    if (ensure_dir(NATIVE_LOG_FALLBACK_DIR, 0700) == 0) {
        (void)chmod(NATIVE_LOG_FALLBACK_DIR, 0700);
    }
}

static void a90_log_rotate_if_needed(const char *path) {
    struct stat st;
    char rotated_path[PATH_MAX];

    if (lstat(path, &st) < 0 || S_ISLNK(st.st_mode) || st.st_size <= NATIVE_LOG_MAX_BYTES) {
        return;
    }

    if (snprintf(rotated_path, sizeof(rotated_path), "%s.1", path) >= (int)sizeof(rotated_path)) {
        return;
    }

    unlink(rotated_path);
    rename(path, rotated_path);
}

int a90_log_set_path(const char *path) {
    int fd;

    a90_log_prepare_private_fallback_dir(path);
    a90_log_rotate_if_needed(path);
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -1;
    }
    close(fd);

    snprintf(log_path, sizeof(log_path), "%s", path);
    log_ready = true;
    return 0;
}

void a90_log_select_or_fallback(const char *preferred_path) {
    if (a90_log_set_path(preferred_path) == 0) {
        return;
    }
    if (strcmp(preferred_path, NATIVE_LOG_FALLBACK) != 0) {
        a90_log_set_path(NATIVE_LOG_FALLBACK);
    }
}

const char *a90_log_path(void) {
    return log_ready ? log_path : "<none>";
}

bool a90_log_ready(void) {
    return log_ready;
}

void a90_logf(const char *tag, const char *fmt, ...) {
    char message[768];
    char line[1024];
    va_list ap;
    int saved_errno = errno;
    int fd;
    int len;

    if (!log_ready) {
        a90_log_select_or_fallback(NATIVE_LOG_FALLBACK);
    }
    if (!log_ready) {
        errno = saved_errno;
        return;
    }

    va_start(ap, fmt);
    len = vsnprintf(message, sizeof(message), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        errno = saved_errno;
        return;
    }
    if ((size_t)len >= sizeof(message)) {
        message[sizeof(message) - 1] = '\0';
    }

    fd = open(log_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0 && strcmp(log_path, NATIVE_LOG_FALLBACK) != 0) {
        a90_log_select_or_fallback(NATIVE_LOG_FALLBACK);
        fd = open(log_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    }
    if (fd < 0) {
        errno = saved_errno;
        return;
    }

    len = snprintf(line, sizeof(line), "[%ldms] %s: %s\n",
                   monotonic_millis(), tag, message);
    if (len > 0) {
        if ((size_t)len >= sizeof(line)) {
            len = (int)sizeof(line) - 1;
            line[len] = '\n';
        }
        write_all(fd, line, (size_t)len);
    }
    close(fd);
    errno = saved_errno;
}
