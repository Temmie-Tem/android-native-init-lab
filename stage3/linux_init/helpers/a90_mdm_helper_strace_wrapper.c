#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#define WRAPPER_VERSION "a90_mdm_helper_strace_wrapper v1157"
#define TRACE_DIR "/data/local/tmp/a90-wifi"
#define TRACE_OUT TRACE_DIR "/mdm_helper.strace.txt"
#define WRAPPER_LOG TRACE_DIR "/mdm_helper.wrapper.log"
#define STRACE_BIN "/vendor/bin/a90_strace"
#define SYSCALL_FILTER "trace=openat,ioctl,read,write,execve"

static const char *const original_candidates[] = {
    "/vendor/bin/mdm_helper.real",
    "/system/vendor/bin/mdm_helper.real",
    "/sbin/.magisk/mirror/vendor/bin/mdm_helper",
    "/debug_ramdisk/.magisk/mirror/vendor/bin/mdm_helper",
    "/data/adb/modules/a90_mdm_trace/original/mdm_helper",
    NULL,
};

static bool is_recursive_path(const char *path, const char *argv0) {
    if (path == NULL || path[0] == '\0') {
        return true;
    }
    if (strcmp(path, "/vendor/bin/mdm_helper") == 0) {
        return true;
    }
    if (strcmp(path, "/system/vendor/bin/mdm_helper") == 0) {
        return true;
    }
    if (argv0 != NULL && argv0[0] != '\0' && strcmp(path, argv0) == 0) {
        return true;
    }
    return false;
}

static int ensure_trace_dir(void) {
    if (mkdir(TRACE_DIR, 0700) == 0) {
        return 0;
    }
    if (errno == EEXIST) {
        return 0;
    }
    return -1;
}

static int open_wrapper_log(void) {
    ensure_trace_dir();
    int log_fd = open(WRAPPER_LOG, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    return log_fd;
}

static void log_printf(int log_fd, const char *format, ...) {
    if (log_fd < 0) {
        return;
    }
    va_list arguments;
    va_start(arguments, format);
    vdprintf(log_fd, format, arguments);
    va_end(arguments);
}

static void log_timestamp(int log_fd, const char *label) {
    time_t now = time(NULL);
    struct tm local_time;
    char time_buffer[64];
    if (localtime_r(&now, &local_time) != NULL &&
        strftime(time_buffer, sizeof(time_buffer), "%Y-%m-%dT%H:%M:%S%z", &local_time) > 0) {
        log_printf(log_fd, "%s=%s\n", label, time_buffer);
    } else {
        log_printf(log_fd, "%s=unknown\n", label);
    }
}

static void log_file_first_line(int log_fd, const char *label, const char *path) {
    char buffer[512];
    int source_fd = open(path, O_RDONLY | O_CLOEXEC);
    if (source_fd < 0) {
        log_printf(log_fd, "%s_read_errno=%d\n", label, errno);
        return;
    }
    ssize_t got = read(source_fd, buffer, sizeof(buffer) - 1);
    int saved_errno = errno;
    close(source_fd);
    if (got <= 0) {
        log_printf(log_fd, "%s_read_errno=%d\n", label, saved_errno);
        return;
    }
    buffer[got] = '\0';
    char *newline = strchr(buffer, '\n');
    if (newline != NULL) {
        *newline = '\0';
    }
    log_printf(log_fd, "%s=%s\n", label, buffer);
}

static const char *find_original(const char *argv0, int log_fd) {
    for (size_t candidate_index = 0; original_candidates[candidate_index] != NULL; candidate_index++) {
        const char *candidate = original_candidates[candidate_index];
        if (is_recursive_path(candidate, argv0)) {
            log_printf(log_fd, "refusing recursive original path: %s\n", candidate);
            continue;
        }
        if (access(candidate, X_OK) == 0) {
            log_printf(log_fd, "original_candidate_selected=%s\n", candidate);
            return candidate;
        }
        log_printf(log_fd, "original_candidate_unavailable=%s errno=%d\n", candidate, errno);
    }
    return NULL;
}

static void log_arguments(int log_fd, int argument_count, char **argument_values) {
    log_printf(log_fd, "argc=%d\n", argument_count);
    for (int argument_index = 0; argument_index < argument_count; argument_index++) {
        log_printf(log_fd, "argv[%d]=%s\n", argument_index, argument_values[argument_index] ? argument_values[argument_index] : "(null)");
    }
}

static char **build_strace_arguments(int argument_count, char **argument_values, const char *original_path) {
    size_t strace_argument_count = 10U + (argument_count > 1 ? (size_t)(argument_count - 1) : 0U);
    char **strace_arguments = calloc(strace_argument_count + 1U, sizeof(char *));
    if (strace_arguments == NULL) {
        return NULL;
    }

    size_t output_index = 0;
    strace_arguments[output_index++] = (char *)STRACE_BIN;
    strace_arguments[output_index++] = "-f";
    strace_arguments[output_index++] = "-tt";
    strace_arguments[output_index++] = "-s";
    strace_arguments[output_index++] = "256";
    strace_arguments[output_index++] = "-e";
    strace_arguments[output_index++] = (char *)SYSCALL_FILTER;
    strace_arguments[output_index++] = "-o";
    strace_arguments[output_index++] = (char *)TRACE_OUT;
    strace_arguments[output_index++] = (char *)original_path;

    for (int argument_index = 1; argument_index < argument_count; argument_index++) {
        strace_arguments[output_index++] = argument_values[argument_index];
    }
    strace_arguments[output_index] = NULL;
    return strace_arguments;
}

int main(int argument_count, char **argument_values) {
    int log_fd = open_wrapper_log();
    log_printf(log_fd, "%s\n", WRAPPER_VERSION);
    log_timestamp(log_fd, "wrapper_start");
    log_printf(log_fd, "pid=%ld uid=%ld gid=%ld\n", (long)getpid(), (long)getuid(), (long)getgid());
    log_arguments(log_fd, argument_count, argument_values);
    log_file_first_line(log_fd, "selinux_context", "/proc/self/attr/current");

    if (access(STRACE_BIN, X_OK) != 0) {
        log_printf(log_fd, "missing executable strace: %s errno=%d\n", STRACE_BIN, errno);
        if (log_fd >= 0) {
            close(log_fd);
        }
        return 127;
    }

    const char *argv0 = argument_count > 0 ? argument_values[0] : NULL;
    const char *original_path = find_original(argv0, log_fd);
    if (original_path == NULL) {
        log_printf(log_fd, "original mdm_helper not found in Magisk mirror/original fallback\n");
        if (log_fd >= 0) {
            close(log_fd);
        }
        return 126;
    }

    char **strace_arguments = build_strace_arguments(argument_count, argument_values, original_path);
    if (strace_arguments == NULL) {
        log_printf(log_fd, "strace argument allocation failed errno=%d\n", errno);
        if (log_fd >= 0) {
            close(log_fd);
        }
        return 125;
    }

    log_printf(log_fd, "exec_strace=%s original=%s out=%s filter=%s\n", STRACE_BIN, original_path, TRACE_OUT, SYSCALL_FILTER);
    if (log_fd >= 0) {
        close(log_fd);
    }

    execv(STRACE_BIN, strace_arguments);
    int exec_errno = errno;
    log_fd = open_wrapper_log();
    log_printf(log_fd, "exec_strace_failed errno=%d\n", exec_errno);
    if (log_fd >= 0) {
        close(log_fd);
    }
    free(strace_arguments);
    return 127;
}
