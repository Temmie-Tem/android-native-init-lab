#include "a90_longsoak.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_runtime.h"
#include "a90_service.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define A90_LONGSOAK_EXPORT_DEFAULT_LINES 200000UL
#define A90_LONGSOAK_EXPORT_MAX_LINES 200000UL
#define A90_LONGSOAK_EXPORT_DEFAULT_BYTES (16UL * 1024UL * 1024UL)
#define A90_LONGSOAK_EXPORT_MAX_BYTES (16UL * 1024UL * 1024UL)

static char longsoak_path[PATH_MAX];
static char longsoak_session[64];
static int longsoak_interval_sec;

static long longsoak_expected_max_age_ms(int interval_sec) {
    if (interval_sec <= 0) {
        interval_sec = A90_LONGSOAK_DEFAULT_INTERVAL_SEC;
    }
    return (long)interval_sec * 3000L + 5000L;
}

static int longsoak_parse_positive_int(const char *text, int *out) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0' || out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return -EINVAL;
    }
    if (value < A90_LONGSOAK_MIN_INTERVAL_SEC ||
        value > A90_LONGSOAK_MAX_INTERVAL_SEC) {
        return -ERANGE;
    }
    *out = (int)value;
    return 0;
}

static int longsoak_parse_bounded_ulong(const char *text,
                                        unsigned long min_value,
                                        unsigned long max_value,
                                        unsigned long *out) {
    char *end = NULL;
    unsigned long value;

    if (text == NULL || text[0] == '\0' || out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return -EINVAL;
    }
    if (value < min_value || value > max_value) {
        return -ERANGE;
    }
    *out = value;
    return 0;
}

static void longsoak_build_session(char *out, size_t out_size) {
    snprintf(out, out_size, "%s-%ld", INIT_BUILD, monotonic_millis());
}

static int longsoak_build_path(const char *session, char *out, size_t out_size) {
    const char *log_dir = a90_runtime_log_dir();
    int written;

    if (log_dir == NULL || log_dir[0] == '\0') {
        log_dir = NATIVE_LOG_FALLBACK_DIR;
        (void)ensure_dir(log_dir, 0700);
    }
    written = snprintf(out, out_size, "%s/longsoak-%s.jsonl", log_dir, session);
    if (written < 0 || (size_t)written >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static bool longsoak_is_running(void) {
    (void)a90_service_reap(A90_SERVICE_LONGSOAK, NULL);
    return a90_service_pid(A90_SERVICE_LONGSOAK) > 0;
}

static bool longsoak_has_suffix(const char *text, const char *suffix) {
    size_t text_len;
    size_t suffix_len;

    if (text == NULL || suffix == NULL) {
        return false;
    }
    text_len = strlen(text);
    suffix_len = strlen(suffix);
    if (text_len < suffix_len) {
        return false;
    }
    return strcmp(text + text_len - suffix_len, suffix) == 0;
}

static bool longsoak_path_under_dir(const char *path, const char *dir) {
    size_t dir_len;

    if (path == NULL || dir == NULL || path[0] != '/' || dir[0] == '\0') {
        return false;
    }
    dir_len = strlen(dir);
    if (strncmp(path, dir, dir_len) != 0) {
        return false;
    }
    return path[dir_len] == '/';
}

static bool longsoak_path_has_expected_shape(const char *path) {
    const char *basename;
    const char *runtime_log_dir = a90_runtime_log_dir();

    if (path == NULL || path[0] == '\0' || strcmp(path, "-") == 0 || path[0] != '/') {
        return false;
    }
    if (strstr(path, "/../") != NULL || longsoak_has_suffix(path, "/..")) {
        return false;
    }
    basename = strrchr(path, '/');
    if (basename == NULL || basename[1] == '\0') {
        return false;
    }
    ++basename;
    if (strncmp(basename, "longsoak-", strlen("longsoak-")) != 0 ||
        !longsoak_has_suffix(basename, ".jsonl")) {
        return false;
    }
    if (runtime_log_dir != NULL &&
        runtime_log_dir[0] != '\0' &&
        longsoak_path_under_dir(path, runtime_log_dir)) {
        return true;
    }
    return longsoak_path_under_dir(path, NATIVE_LOG_FALLBACK_DIR);
}

static int longsoak_open_log_readonly(const char *path) {
    struct stat st;
    int fd;
    int saved_errno;

    if (!longsoak_path_has_expected_shape(path)) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (!S_ISREG(st.st_mode)) {
        close(fd);
        errno = EINVAL;
        return -1;
    }
    return fd;
}

static unsigned long longsoak_parse_unsigned_field(const char *line,
                                                   const char *name,
                                                   unsigned long fallback) {
    const char *start = strstr(line, name);
    char *end = NULL;
    unsigned long value;

    if (start == NULL) {
        return fallback;
    }
    start += strlen(name);
    errno = 0;
    value = strtoul(start, &end, 10);
    if (errno != 0 || end == start) {
        return fallback;
    }
    return value;
}

static void longsoak_parse_type(const char *line, char *out, size_t out_size) {
    const char *start = strstr(line, "\"type\":\"");
    size_t index = 0;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "-");
    if (start == NULL) {
        return;
    }
    start += strlen("\"type\":\"");
    while (start[index] != '\0' && start[index] != '"' && index + 1 < out_size) {
        out[index] = start[index];
        ++index;
    }
    out[index] = '\0';
}

static void longsoak_scan_file(struct a90_longsoak_status *status) {
    int fd;
    FILE *file;
    char line[768];

    if (status == NULL || status->path[0] == '\0') {
        return;
    }
    fd = longsoak_open_log_readonly(status->path);
    if (fd < 0) {
        return;
    }
    file = fdopen(fd, "r");
    if (file == NULL) {
        close(fd);
        return;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned long seq;
        unsigned long ts_ms;

        longsoak_parse_type(line, status->last_type, sizeof(status->last_type));
        if (strstr(line, "\"type\":\"sample\"") != NULL) {
            ++status->samples;
        }
        seq = longsoak_parse_unsigned_field(line, "\"seq\":", status->last_seq);
        ts_ms = longsoak_parse_unsigned_field(line, "\"ts_ms\":", (unsigned long)status->last_ts_ms);
        status->last_seq = seq;
        status->last_ts_ms = (long)ts_ms;
    }
    fclose(file);
    if (status->last_ts_ms > 0) {
        status->last_age_ms = monotonic_millis() - status->last_ts_ms;
        if (status->last_age_ms < 0) {
            status->last_age_ms = 0;
        }
    }
}

int a90_longsoak_get_status(struct a90_longsoak_status *out) {
    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    out->pid = -1;
    snprintf(out->session, sizeof(out->session), "-");
    snprintf(out->path, sizeof(out->path), "-");
    snprintf(out->last_type, sizeof(out->last_type), "-");
    snprintf(out->health, sizeof(out->health), "stopped");
    out->running = longsoak_is_running();
    out->pid = a90_service_pid(A90_SERVICE_LONGSOAK);
    out->interval_sec = longsoak_interval_sec;
    out->expected_max_age_ms = longsoak_expected_max_age_ms(out->interval_sec);
    if (longsoak_session[0] != '\0') {
        snprintf(out->session, sizeof(out->session), "%s", longsoak_session);
    }
    if (longsoak_path[0] != '\0') {
        snprintf(out->path, sizeof(out->path), "%s", longsoak_path);
    }
    longsoak_scan_file(out);
    if (out->running) {
        if (out->samples == 0) {
            snprintf(out->health, sizeof(out->health), "warming");
        } else if (out->last_age_ms > out->expected_max_age_ms) {
            out->stale = true;
            snprintf(out->health, sizeof(out->health), "stale");
        } else {
            snprintf(out->health, sizeof(out->health), "ok");
        }
    }
    return 0;
}

void a90_longsoak_summary(char *out, size_t out_size) {
    struct a90_longsoak_status status;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_longsoak_get_status(&status) < 0) {
        snprintf(out, out_size, "unavailable");
        return;
    }
    snprintf(out,
             out_size,
             "health=%s running=%s pid=%ld interval=%ds samples=%u last=%s seq=%lu age=%ldms session=%s",
             status.health,
             status.running ? "yes" : "no",
             (long)status.pid,
             status.interval_sec,
             status.samples,
             status.last_type,
             status.last_seq,
             status.last_age_ms,
             status.session);
}

void a90_longsoak_health_summary(char *out, size_t out_size) {
    struct a90_longsoak_status status;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_longsoak_get_status(&status) < 0) {
        snprintf(out, out_size, "health=unavailable");
        return;
    }
    snprintf(out,
             out_size,
             "health=%s stale=%s running=%s samples=%u age=%ldms max_age=%ldms path=%s",
             status.health,
             status.stale ? "yes" : "no",
             status.running ? "yes" : "no",
             status.samples,
             status.last_age_ms,
             status.expected_max_age_ms,
             status.path);
}

int a90_longsoak_start(int interval_sec) {
    char interval_arg[24];
    char *const argv[] = {
        (char *)A90_LONGSOAK_HELPER,
        longsoak_path,
        interval_arg,
        longsoak_session,
        NULL,
    };
    struct a90_run_config config;
    pid_t pid = -1;
    int rc;

    if (interval_sec <= 0) {
        interval_sec = A90_LONGSOAK_DEFAULT_INTERVAL_SEC;
    }
    if (interval_sec < A90_LONGSOAK_MIN_INTERVAL_SEC ||
        interval_sec > A90_LONGSOAK_MAX_INTERVAL_SEC) {
        a90_console_printf("longsoak: interval must be %d..%d seconds\r\n",
                A90_LONGSOAK_MIN_INTERVAL_SEC,
                A90_LONGSOAK_MAX_INTERVAL_SEC);
        return -ERANGE;
    }
    if (longsoak_is_running()) {
        a90_console_printf("longsoak: already running pid=%ld path=%s\r\n",
                (long)a90_service_pid(A90_SERVICE_LONGSOAK),
                longsoak_path[0] != '\0' ? longsoak_path : "-");
        return 0;
    }

    longsoak_build_session(longsoak_session, sizeof(longsoak_session));
    rc = longsoak_build_path(longsoak_session, longsoak_path, sizeof(longsoak_path));
    if (rc < 0) {
        a90_console_printf("longsoak: path build failed rc=%d\r\n", rc);
        return rc;
    }
    snprintf(interval_arg, sizeof(interval_arg), "%d", interval_sec);

    memset(&config, 0, sizeof(config));
    config.tag = "longsoak";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.ignore_hup_pipe = true;
    config.setsid = false;
    config.kill_process_group = false;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        a90_console_printf("longsoak: spawn %s failed rc=%d\r\n",
                A90_LONGSOAK_HELPER, rc);
        return rc;
    }
    longsoak_interval_sec = interval_sec;
    a90_service_set_pid(A90_SERVICE_LONGSOAK, pid);
    a90_logf("longsoak", "started pid=%ld interval=%d path=%s session=%s",
            (long)pid, interval_sec, longsoak_path, longsoak_session);
    a90_console_printf("longsoak: started pid=%ld interval=%ds session=%s\r\n",
            (long)pid, interval_sec, longsoak_session);
    a90_console_printf("longsoak: path=%s\r\n", longsoak_path);
    return 0;
}

int a90_longsoak_stop(void) {
    pid_t pid = a90_service_pid(A90_SERVICE_LONGSOAK);
    int rc;

    if (pid <= 0) {
        a90_console_printf("longsoak: not running\r\n");
        return 0;
    }
    rc = a90_service_stop(A90_SERVICE_LONGSOAK, 3000);
    a90_logf("longsoak", "stop pid=%ld rc=%d path=%s",
            (long)pid, rc, longsoak_path[0] != '\0' ? longsoak_path : "-");
    a90_console_printf("longsoak: stopped pid=%ld rc=%d\r\n", (long)pid, rc);
    return rc;
}

int a90_longsoak_status(void) {
    struct a90_longsoak_status status;

    a90_longsoak_get_status(&status);
    a90_console_printf("longsoak: health=%s running=%s stale=%s pid=%ld interval=%ds session=%s samples=%u last=%s seq=%lu age=%ldms max_age=%ldms\r\n",
            status.health,
            status.running ? "yes" : "no",
            status.stale ? "yes" : "no",
            (long)status.pid,
            status.interval_sec,
            status.session,
            status.samples,
            status.last_type,
            status.last_seq,
            status.last_age_ms,
            status.expected_max_age_ms);
    a90_console_printf("longsoak: path=%s\r\n", status.path);
    return 0;
}

int a90_longsoak_status_verbose(void) {
    int rc = a90_longsoak_status();

    if (longsoak_path[0] != '\0') {
        (void)a90_longsoak_tail(1);
    }
    return rc;
}

int a90_longsoak_path(void) {
    a90_console_printf("%s\r\n", longsoak_path[0] != '\0' ? longsoak_path : "-");
    return longsoak_path[0] != '\0' ? 0 : -ENOENT;
}

int a90_longsoak_tail(int lines) {
    char ring[A90_LONGSOAK_TAIL_MAX_LINES][512];
    int fd;
    FILE *file;
    size_t count = 0;
    size_t index;

    if (lines <= 0) {
        lines = A90_LONGSOAK_TAIL_DEFAULT_LINES;
    }
    if (lines > A90_LONGSOAK_TAIL_MAX_LINES) {
        lines = A90_LONGSOAK_TAIL_MAX_LINES;
    }
    if (longsoak_path[0] == '\0') {
        a90_console_printf("longsoak: no path yet\r\n");
        return -ENOENT;
    }
    fd = longsoak_open_log_readonly(longsoak_path);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("longsoak: open %s: %s\r\n",
                longsoak_path, strerror(saved_errno));
        return -saved_errno;
    }
    file = fdopen(fd, "r");
    if (file == NULL) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("longsoak: fdopen %s: %s\r\n",
                longsoak_path, strerror(saved_errno));
        return -saved_errno;
    }
    while (fgets(ring[count % (size_t)lines], sizeof(ring[0]), file) != NULL) {
        ++count;
    }
    fclose(file);

    index = count > (size_t)lines ? count - (size_t)lines : 0;
    a90_console_printf("longsoak: tail path=%s lines=%d total=%u\r\n",
            longsoak_path, lines, (unsigned int)count);
    for (; index < count; ++index) {
        char *line = ring[index % (size_t)lines];

        trim_newline(line);
        a90_console_printf("%s\r\n", line);
    }
    return 0;
}

static int a90_longsoak_export(unsigned long max_lines, unsigned long max_bytes) {
    char line[768];
    int fd;
    FILE *file;
    unsigned long lines = 0;
    unsigned long bytes = 0;
    bool truncated = false;

    if (max_lines == 0 || max_lines > A90_LONGSOAK_EXPORT_MAX_LINES) {
        max_lines = A90_LONGSOAK_EXPORT_DEFAULT_LINES;
    }
    if (max_bytes == 0 || max_bytes > A90_LONGSOAK_EXPORT_MAX_BYTES) {
        max_bytes = A90_LONGSOAK_EXPORT_DEFAULT_BYTES;
    }
    if (longsoak_path[0] == '\0') {
        a90_console_printf("longsoak: no path yet\r\n");
        return -ENOENT;
    }
    fd = longsoak_open_log_readonly(longsoak_path);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("longsoak: open %s: %s\r\n",
                longsoak_path, strerror(saved_errno));
        return -saved_errno;
    }
    file = fdopen(fd, "r");
    if (file == NULL) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("longsoak: fdopen %s: %s\r\n",
                longsoak_path, strerror(saved_errno));
        return -saved_errno;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        size_t line_len = strlen(line);

        if (lines >= max_lines || bytes + (unsigned long)line_len > max_bytes) {
            truncated = true;
            break;
        }
        bytes += (unsigned long)line_len;
        trim_newline(line);
        a90_console_printf("%s\r\n", line);
        ++lines;
    }
    if (ferror(file)) {
        int saved_errno = errno;

        fclose(file);
        a90_console_printf("longsoak: read %s: %s\r\n",
                longsoak_path, strerror(saved_errno));
        return -saved_errno;
    }
    fclose(file);
    a90_console_printf("longsoak: export path=%s lines=%lu bytes=%lu truncated=%s\r\n",
            longsoak_path,
            lines,
            bytes,
            truncated ? "yes" : "no");
    return 0;
}

int a90_longsoak_cmd(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    int value;
    int rc;

    if (strcmp(subcommand, "status") == 0) {
        if (argc == 3 && strcmp(argv[2], "verbose") == 0) {
            return a90_longsoak_status_verbose();
        }
        if (argc != 1 && argc != 2) {
            a90_console_printf("usage: longsoak [status [verbose]|start [interval]|stop|path|tail [lines]|export [max_lines] [max_bytes]]\r\n");
            return -EINVAL;
        }
        return a90_longsoak_status();
    }
    if (strcmp(subcommand, "start") == 0) {
        if (argc > 3) {
            a90_console_printf("usage: longsoak start [interval]\r\n");
            return -EINVAL;
        }
        value = A90_LONGSOAK_DEFAULT_INTERVAL_SEC;
        if (argc == 3) {
            rc = longsoak_parse_positive_int(argv[2], &value);
            if (rc < 0) {
                a90_console_printf("longsoak: invalid interval %s\r\n", argv[2]);
                return rc;
            }
        }
        return a90_longsoak_start(value);
    }
    if (strcmp(subcommand, "stop") == 0) {
        if (argc != 2) {
            a90_console_printf("usage: longsoak stop\r\n");
            return -EINVAL;
        }
        return a90_longsoak_stop();
    }
    if (strcmp(subcommand, "path") == 0) {
        if (argc != 2) {
            a90_console_printf("usage: longsoak path\r\n");
            return -EINVAL;
        }
        return a90_longsoak_path();
    }
    if (strcmp(subcommand, "tail") == 0) {
        if (argc > 3) {
            a90_console_printf("usage: longsoak tail [lines]\r\n");
            return -EINVAL;
        }
        value = A90_LONGSOAK_TAIL_DEFAULT_LINES;
        if (argc == 3) {
            rc = longsoak_parse_positive_int(argv[2], &value);
            if (rc < 0) {
                a90_console_printf("longsoak: invalid tail lines %s\r\n", argv[2]);
                return rc;
            }
        }
        return a90_longsoak_tail(value);
    }
    if (strcmp(subcommand, "export") == 0) {
        unsigned long max_lines = A90_LONGSOAK_EXPORT_DEFAULT_LINES;
        unsigned long max_bytes = A90_LONGSOAK_EXPORT_DEFAULT_BYTES;

        if (argc > 4) {
            a90_console_printf("usage: longsoak export [max_lines] [max_bytes]\r\n");
            return -EINVAL;
        }
        if (argc >= 3) {
            rc = longsoak_parse_bounded_ulong(argv[2], 1, A90_LONGSOAK_EXPORT_MAX_LINES, &max_lines);
            if (rc < 0) {
                a90_console_printf("longsoak: invalid export lines %s\r\n", argv[2]);
                return rc;
            }
        }
        if (argc == 4) {
            rc = longsoak_parse_bounded_ulong(argv[3], 1, A90_LONGSOAK_EXPORT_MAX_BYTES, &max_bytes);
            if (rc < 0) {
                a90_console_printf("longsoak: invalid export bytes %s\r\n", argv[3]);
                return rc;
            }
        }
        return a90_longsoak_export(max_lines, max_bytes);
    }

    a90_console_printf("usage: longsoak [status [verbose]|start [interval]|stop|path|tail [lines]|export [max_lines] [max_bytes]]\r\n");
    return -EINVAL;
}
