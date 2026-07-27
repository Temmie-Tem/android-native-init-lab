// SPDX-License-Identifier: MIT
/*
 * Generic-arm64 control for the P2.80 tracefs Kprobe mechanism.
 *
 * This does not emulate the S22+ USB stack. It proves that the pinned guest
 * can register one entry/return pair, preserve one exact negative signed
 * PID1 syscall return, report zero missed probes, and clean up all state used
 * by the control.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define P280_TRACE_ROOT "/sys/kernel/tracing"
#define P280_INSTANCE_ROOT P280_TRACE_ROOT "/instances/p280ctrl"
#define P280_GROUP "p280ctrl"
#define P280_ENTRY "p280_ctrl_entry"
#define P280_RETURN "p280_ctrl_return"
#define P280_SYMBOL "__arm64_sys_close"
#define P280_TRACE_CAPACITY (64U * 1024U)

static __attribute__((noreturn)) void p280_park(void) {
    for (;;) {
        pause();
    }
}

static __attribute__((noreturn)) void p280_fail(
    const char *stage, int detail) {
    dprintf(
        STDOUT_FILENO,
        "P280_KPROBE_QEMU result=FAIL stage=%s detail=%d\n",
        stage,
        detail);
    sync();
    p280_park();
}

static void p280_mkdir(const char *path) {
    if (mkdir(path, 0700) != 0 && errno != EEXIST) {
        p280_fail(path, errno);
    }
}

static void p280_write_exact(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        p280_fail(path, errno);
    }
    size_t length = strlen(value);
    ssize_t amount = write(fd, value, length);
    int saved_errno = errno;
    close(fd);
    if (amount != (ssize_t)length) {
        p280_fail(path, amount < 0 ? saved_errno : EIO);
    }
}

static int p280_open_write(const char *path) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        p280_fail(path, errno);
    }
    return fd;
}

static void p280_write_fd_exact(int fd, const char *stage, const char *value) {
    size_t length = strlen(value);
    ssize_t amount = write(fd, value, length);
    if (amount != (ssize_t)length) {
        p280_fail(stage, amount < 0 ? errno : EIO);
    }
}

static size_t p280_read_bounded(
    const char *path, char *buffer, size_t capacity) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        p280_fail(path, errno);
    }
    ssize_t amount = read(fd, buffer, capacity - 1U);
    int saved_errno = errno;
    close(fd);
    if (amount < 0) {
        p280_fail(path, saved_errno);
    }
    buffer[amount] = '\0';
    return (size_t)amount;
}

static size_t p280_count(const char *text, const char *needle) {
    size_t count = 0;
    size_t length = strlen(needle);
    const char *cursor = text;
    while ((cursor = strstr(cursor, needle)) != NULL) {
        ++count;
        cursor += length;
    }
    return count;
}

static bool p280_profile_has_exact(
    const char *profile, const char *name, unsigned long hits) {
    const char *cursor = profile;
    while (*cursor != '\0') {
        char event[128] = {0};
        unsigned long observed_hits = 0;
        unsigned long missed = 0;
        if (sscanf(
                cursor,
                " %127s %lu %lu",
                event,
                &observed_hits,
                &missed) == 3
            && strcmp(event, name) == 0) {
            return observed_hits == hits && missed == 0;
        }
        const char *newline = strchr(cursor, '\n');
        if (newline == NULL) {
            break;
        }
        cursor = newline + 1;
    }
    return false;
}

static bool p280_kallsyms_has_exact(const char *wanted) {
    FILE *stream = fopen("/proc/kallsyms", "re");
    if (stream == NULL) {
        p280_fail("open-kallsyms", errno);
    }
    char line[512];
    bool found = false;
    while (fgets(line, sizeof(line), stream) != NULL) {
        unsigned long address = 0;
        char type = '\0';
        char name[256] = {0};
        if (sscanf(line, "%lx %c %255s", &address, &type, name) == 3
            && (type == 'T' || type == 't')
            && strcmp(name, wanted) == 0) {
            found = true;
            break;
        }
    }
    if (ferror(stream)) {
        int saved_errno = errno;
        fclose(stream);
        p280_fail("read-kallsyms", saved_errno);
    }
    fclose(stream);
    return found;
}

static void p280_require_regular(const char *path) {
    struct stat value;
    if (stat(path, &value) != 0) {
        p280_fail(path, errno);
    }
    if (!S_ISREG(value.st_mode)) {
        p280_fail(path, EPROTO);
    }
}

static void p280_mount_control_filesystems(void) {
    p280_mkdir("/proc");
    p280_mkdir("/sys");
    if (mount("proc", "/proc", "proc", 0, NULL) != 0 && errno != EBUSY) {
        p280_fail("mount-proc", errno);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) != 0 && errno != EBUSY) {
        p280_fail("mount-sysfs", errno);
    }
    p280_mkdir("/sys/kernel");
    p280_mkdir(P280_TRACE_ROOT);
    if (mount(
            "tracefs",
            P280_TRACE_ROOT,
            "tracefs",
            MS_NOSUID | MS_NODEV | MS_NOEXEC,
            NULL) != 0) {
        p280_fail("mount-tracefs", errno);
    }
    struct statfs value;
    if (statfs(P280_TRACE_ROOT, &value) != 0
        || (unsigned long)value.f_type != TRACEFS_MAGIC) {
        p280_fail("tracefs-magic", EPROTO);
    }
}

static void p280_verify_registration(void) {
    p280_require_regular(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_ENTRY "/enable");
    p280_require_regular(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_RETURN "/enable");
    char definitions[16384];
    p280_read_bounded(
        P280_TRACE_ROOT "/kprobe_events",
        definitions,
        sizeof(definitions));
    if (strstr(definitions, P280_GROUP "/" P280_ENTRY) == NULL
        || strstr(definitions, P280_GROUP "/" P280_RETURN) == NULL
        || p280_count(definitions, P280_SYMBOL) != 2U) {
        p280_fail("registration-readback", EPROTO);
    }
}

static void p280_verify_control_readback(void) {
    char value[4096];
    p280_read_bounded(
        P280_INSTANCE_ROOT "/trace_clock", value, sizeof(value));
    if (strstr(value, "[counter]") == NULL) {
        p280_fail("trace-clock-readback", EPROTO);
    }
    p280_read_bounded(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_ENTRY "/filter",
        value,
        sizeof(value));
    if (strcmp(value, "common_pid == 1\n") != 0) {
        p280_fail("entry-filter-readback", EPROTO);
    }
    p280_read_bounded(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_RETURN "/filter",
        value,
        sizeof(value));
    if (strcmp(value, "common_pid == 1\n") != 0) {
        p280_fail("return-filter-readback", EPROTO);
    }
}

static void p280_cleanup(void) {
    p280_write_exact(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/enable", "0\n");
    p280_write_exact(
        P280_TRACE_ROOT "/kprobe_events",
        "-:" P280_GROUP "/" P280_ENTRY "\n");
    p280_write_exact(
        P280_TRACE_ROOT "/kprobe_events",
        "-:" P280_GROUP "/" P280_RETURN "\n");
    if (rmdir(P280_INSTANCE_ROOT) != 0) {
        p280_fail("instance-remove", errno);
    }
    char definitions[16384];
    p280_read_bounded(
        P280_TRACE_ROOT "/kprobe_events",
        definitions,
        sizeof(definitions));
    errno = 0;
    int instance_rc = access(P280_INSTANCE_ROOT, F_OK);
    int instance_errno = errno;
    if (strstr(definitions, P280_ENTRY) != NULL
        || strstr(definitions, P280_RETURN) != NULL
        || instance_rc == 0
        || instance_errno != ENOENT) {
        p280_fail("cleanup-readback", EPROTO);
    }
    if (umount(P280_TRACE_ROOT) != 0) {
        p280_fail("unmount-tracefs", errno);
    }
    struct statfs value;
    if (statfs(P280_TRACE_ROOT, &value) != 0
        || (unsigned long)value.f_type == TRACEFS_MAGIC) {
        p280_fail("unmount-readback", EPROTO);
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    p280_mount_control_filesystems();
    if (!p280_kallsyms_has_exact(P280_SYMBOL)) {
        p280_fail("control-symbol", ENOENT);
    }

    p280_mkdir(P280_TRACE_ROOT "/instances");
    if (mkdir(P280_INSTANCE_ROOT, 0700) != 0) {
        p280_fail("instance-create", errno);
    }

    p280_write_exact(
        P280_TRACE_ROOT "/kprobe_events",
        "p:" P280_GROUP "/" P280_ENTRY " " P280_SYMBOL "\n");
    p280_write_exact(
        P280_TRACE_ROOT "/kprobe_events",
        "r:" P280_GROUP "/" P280_RETURN " " P280_SYMBOL
        " rc=$retval:s32\n");
    p280_verify_registration();

    p280_write_exact(P280_INSTANCE_ROOT "/tracing_on", "0\n");
    p280_write_exact(P280_INSTANCE_ROOT "/trace_clock", "counter\n");
    p280_write_exact(P280_INSTANCE_ROOT "/buffer_size_kb", "64\n");
    p280_write_exact(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_ENTRY "/filter",
        "common_pid == 1\n");
    p280_write_exact(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/" P280_RETURN "/filter",
        "common_pid == 1\n");
    p280_verify_control_readback();
    int event_enable_fd = p280_open_write(
        P280_INSTANCE_ROOT "/events/" P280_GROUP "/enable");
    int tracing_on_fd = p280_open_write(P280_INSTANCE_ROOT "/tracing_on");
    p280_write_fd_exact(event_enable_fd, "event-enable", "1\n");
    p280_write_fd_exact(tracing_on_fd, "tracing-enable", "1\n");
    int clear_fd = open(
        P280_INSTANCE_ROOT "/trace",
        O_WRONLY | O_TRUNC | O_CLOEXEC);
    if (clear_fd < 0) {
        p280_fail("trace-clear-open", errno);
    }
    ssize_t clear_amount = write(clear_fd, "\n", 1);
    if (clear_amount != 1) {
        p280_fail("trace-clear", clear_amount < 0 ? errno : EIO);
    }

    errno = 0;
    long user_result = syscall(SYS_close, -1);
    int user_errno = errno;
    long expected_result = -EBADF;

    p280_write_fd_exact(tracing_on_fd, "tracing-disable", "0\n");
    p280_write_fd_exact(event_enable_fd, "event-disable", "0\n");
    if (close(clear_fd) != 0) {
        p280_fail("trace-clear-close", errno);
    }
    if (close(tracing_on_fd) != 0 || close(event_enable_fd) != 0) {
        p280_fail("control-fd-close", errno);
    }

    char trace[P280_TRACE_CAPACITY];
    p280_read_bounded(P280_INSTANCE_ROOT "/trace", trace, sizeof(trace));
    char retval[64];
    snprintf(retval, sizeof(retval), "rc=%ld", expected_result);
    const char *entry = strstr(trace, ": " P280_ENTRY ":");
    const char *return_event = strstr(trace, ": " P280_RETURN ":");
    if (user_result != -1
        || user_errno != EBADF
        || p280_count(trace, ": " P280_ENTRY ":") != 1U
        || p280_count(trace, ": " P280_RETURN ":") != 1U
        || entry == NULL
        || return_event == NULL
        || entry >= return_event
        || strstr(return_event, retval) == NULL) {
        dprintf(
            STDOUT_FILENO,
            "P280_KPROBE_QEMU trace_begin\n%s"
            "P280_KPROBE_QEMU trace_end\n",
            trace);
        p280_fail("entry-return-pair", ENODATA);
    }

    char profile[65536];
    p280_read_bounded(
        P280_TRACE_ROOT "/kprobe_profile", profile, sizeof(profile));
    if (!p280_profile_has_exact(profile, P280_ENTRY, 1)
        || !p280_profile_has_exact(profile, P280_RETURN, 1)) {
        p280_fail("probe-profile", ENODATA);
    }

    p280_cleanup();
    dprintf(
        STDOUT_FILENO,
        "P280_KPROBE_QEMU result=PASS symbol=%s "
        "entry_hits=1 return_hits=1 retval=%ld nmissed=0 cleanup=ok\n",
        P280_SYMBOL,
        expected_result);
    sync();
    p280_park();
}
