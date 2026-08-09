// SPDX-License-Identifier: MIT
/*
 * Generic-arm64 control for delayed module-local tracefs Kprobe arming.
 *
 * This is not an S22+ USB emulation.  It registers and enables one symbol
 * probe and one instruction-offset probe while dummy_hcd is absent, loads the
 * module, and proves that MODULE_STATE_COMING arms both probes before the
 * synchronous dummy_hcd_probe() call made by module initialization.
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

#define P311_TRACE_ROOT "/sys/kernel/tracing"
#define P311_INSTANCE_ROOT P311_TRACE_ROOT "/instances/p311delay"
#define P311_GROUP "p282"
#define P311_ENTRY "p311_delayed_entry"
#define P311_OFFSET "p311_delayed_offset"
#define P311_MODULE "dummy_hcd"
#define P311_SYMBOL "dummy_hcd_probe"
#define P311_SYMBOL_OFFSET "+0x4c"
#define P311_SYMBOL_OFFSET_READBACK "+76"
#define P311_TRACE_CAPACITY (64U * 1024U)

static __attribute__((noreturn)) void p311_park(void) {
    for (;;) {
        pause();
    }
}

static __attribute__((noreturn)) void p311_fail(
    const char *stage, int detail) {
    dprintf(
        STDOUT_FILENO,
        "P311_DELAYED_MODULE_KPROBE result=FAIL stage=%s detail=%d\n",
        stage,
        detail);
    sync();
    p311_park();
}

static void p311_mkdir(const char *path) {
    if (mkdir(path, 0700) != 0 && errno != EEXIST) {
        p311_fail(path, errno);
    }
}

static void p311_write_exact(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        p311_fail(path, errno);
    }
    size_t length = strlen(value);
    ssize_t amount = write(fd, value, length);
    int saved_errno = errno;
    close(fd);
    if (amount != (ssize_t)length) {
        p311_fail(path, amount < 0 ? saved_errno : EIO);
    }
}

static size_t p311_read_bounded(
    const char *path, char *buffer, size_t capacity) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        p311_fail(path, errno);
    }
    ssize_t amount = read(fd, buffer, capacity - 1U);
    int saved_errno = errno;
    close(fd);
    if (amount < 0) {
        p311_fail(path, saved_errno);
    }
    buffer[amount] = '\0';
    return (size_t)amount;
}

static size_t p311_count(const char *text, const char *needle) {
    size_t count = 0;
    size_t length = strlen(needle);
    const char *cursor = text;
    while ((cursor = strstr(cursor, needle)) != NULL) {
        ++count;
        cursor += length;
    }
    return count;
}

static bool p311_profile_read(
    const char *profile,
    const char *name,
    unsigned long *hits,
    unsigned long *missed) {
    const char *cursor = profile;
    while (*cursor != '\0') {
        char event[128] = {0};
        unsigned long observed_hits = 0;
        unsigned long observed_missed = 0;
        if (sscanf(
                cursor,
                " %127s %lu %lu",
                event,
                &observed_hits,
                &observed_missed) == 3
            && strcmp(event, name) == 0) {
            *hits = observed_hits;
            *missed = observed_missed;
            return true;
        }
        const char *newline = strchr(cursor, '\n');
        if (newline == NULL) {
            break;
        }
        cursor = newline + 1;
    }
    return false;
}

static bool p311_kallsyms_has_exact(const char *wanted) {
    FILE *stream = fopen("/proc/kallsyms", "re");
    if (stream == NULL) {
        p311_fail("open-kallsyms", errno);
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
        p311_fail("read-kallsyms", saved_errno);
    }
    fclose(stream);
    return found;
}

static bool p311_module_loaded(const char *wanted) {
    FILE *stream = fopen("/proc/modules", "re");
    if (stream == NULL) {
        p311_fail("open-modules", errno);
    }
    char line[512];
    bool found = false;
    while (fgets(line, sizeof(line), stream) != NULL) {
        char name[256] = {0};
        if (sscanf(line, "%255s", name) == 1 && strcmp(name, wanted) == 0) {
            found = true;
            break;
        }
    }
    if (ferror(stream)) {
        int saved_errno = errno;
        fclose(stream);
        p311_fail("read-modules", saved_errno);
    }
    fclose(stream);
    return found;
}

static void p311_require_regular(const char *path) {
    struct stat value;
    if (stat(path, &value) != 0) {
        p311_fail(path, errno);
    }
    if (!S_ISREG(value.st_mode)) {
        p311_fail(path, EPROTO);
    }
}

static void p311_mount_filesystems(void) {
    p311_mkdir("/proc");
    p311_mkdir("/sys");
    if (mount("proc", "/proc", "proc", 0, NULL) != 0 && errno != EBUSY) {
        p311_fail("mount-proc", errno);
    }
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) != 0 && errno != EBUSY) {
        p311_fail("mount-sysfs", errno);
    }
    p311_mkdir("/sys/kernel");
    p311_mkdir(P311_TRACE_ROOT);
    if (mount(
            "tracefs",
            P311_TRACE_ROOT,
            "tracefs",
            MS_NOSUID | MS_NODEV | MS_NOEXEC,
            NULL) != 0) {
        p311_fail("mount-tracefs", errno);
    }
    struct statfs value;
    if (statfs(P311_TRACE_ROOT, &value) != 0
        || (unsigned long)value.f_type != TRACEFS_MAGIC) {
        p311_fail("tracefs-magic", EPROTO);
    }
}

static void p311_load_module(const char *name) {
    char path[256];
    int length = snprintf(path, sizeof(path), "/modules/%s.ko", name);
    if (length < 0 || (size_t)length >= sizeof(path)) {
        p311_fail("module-path", EOVERFLOW);
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        p311_fail(path, errno);
    }
    errno = 0;
    long rc = syscall(SYS_finit_module, fd, "", 0);
    int saved_errno = errno;
    close(fd);
    if (rc != 0) {
        p311_fail(name, saved_errno);
    }
}

static void p311_verify_pending_registration(void) {
    p311_require_regular(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_ENTRY "/enable");
    p311_require_regular(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_OFFSET "/enable");
    char definitions[16384];
    p311_read_bounded(
        P311_TRACE_ROOT "/kprobe_events", definitions, sizeof(definitions));
    if (strstr(definitions, P311_GROUP "/" P311_ENTRY) == NULL
        || strstr(definitions, P311_GROUP "/" P311_OFFSET) == NULL
        || p311_count(definitions, P311_MODULE ":" P311_SYMBOL) != 2U
        || p311_count(definitions, P311_SYMBOL_OFFSET_READBACK) != 1U) {
        dprintf(
            STDOUT_FILENO,
            "P311_DELAYED_MODULE_KPROBE definitions_begin\n%s"
            "P311_DELAYED_MODULE_KPROBE definitions_end\n",
            definitions);
        p311_fail("pending-registration-readback", EPROTO);
    }
}

static void p311_verify_control_readback(void) {
    char value[4096];
    p311_read_bounded(
        P311_INSTANCE_ROOT "/trace_clock", value, sizeof(value));
    if (strstr(value, "[counter]") == NULL) {
        p311_fail("trace-clock-readback", EPROTO);
    }
    p311_read_bounded(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_ENTRY "/filter",
        value,
        sizeof(value));
    if (strcmp(value, "common_pid > 0\n") != 0) {
        p311_fail("entry-filter-readback", EPROTO);
    }
    p311_read_bounded(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_OFFSET "/filter",
        value,
        sizeof(value));
    if (strcmp(value, "common_pid > 0\n") != 0) {
        p311_fail("offset-filter-readback", EPROTO);
    }
}

static void p311_cleanup(void) {
    p311_write_exact(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/enable", "0\n");
    p311_write_exact(
        P311_TRACE_ROOT "/kprobe_events",
        "-:" P311_GROUP "/" P311_ENTRY "\n");
    p311_write_exact(
        P311_TRACE_ROOT "/kprobe_events",
        "-:" P311_GROUP "/" P311_OFFSET "\n");
    if (rmdir(P311_INSTANCE_ROOT) != 0) {
        p311_fail("instance-remove", errno);
    }
    char definitions[16384];
    p311_read_bounded(
        P311_TRACE_ROOT "/kprobe_events", definitions, sizeof(definitions));
    errno = 0;
    int instance_rc = access(P311_INSTANCE_ROOT, F_OK);
    int instance_errno = errno;
    if (strstr(definitions, P311_ENTRY) != NULL
        || strstr(definitions, P311_OFFSET) != NULL
        || instance_rc == 0
        || instance_errno != ENOENT) {
        p311_fail("cleanup-readback", EPROTO);
    }
    if (umount(P311_TRACE_ROOT) != 0) {
        p311_fail("unmount-tracefs", errno);
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    p311_mount_filesystems();
    p311_load_module("usb-common");
    p311_load_module("usbcore");
    p311_load_module("udc-core");
    if (p311_module_loaded(P311_MODULE)
        || p311_kallsyms_has_exact(P311_SYMBOL)) {
        p311_fail("target-present-before-registration", EEXIST);
    }

    p311_mkdir(P311_TRACE_ROOT "/instances");
    if (mkdir(P311_INSTANCE_ROOT, 0700) != 0) {
        p311_fail("instance-create", errno);
    }
    p311_write_exact(
        P311_TRACE_ROOT "/kprobe_events",
        "p:" P311_GROUP "/" P311_ENTRY " "
        P311_MODULE ":" P311_SYMBOL "\n");
    p311_write_exact(
        P311_TRACE_ROOT "/kprobe_events",
        "p:" P311_GROUP "/" P311_OFFSET " "
        P311_MODULE ":" P311_SYMBOL P311_SYMBOL_OFFSET "\n");
    p311_verify_pending_registration();

    p311_write_exact(P311_INSTANCE_ROOT "/tracing_on", "0\n");
    p311_write_exact(P311_INSTANCE_ROOT "/trace_clock", "counter\n");
    p311_write_exact(P311_INSTANCE_ROOT "/buffer_size_kb", "64\n");
    p311_write_exact(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_ENTRY "/filter",
        "common_pid > 0\n");
    p311_write_exact(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/" P311_OFFSET "/filter",
        "common_pid > 0\n");
    p311_verify_control_readback();
    p311_write_exact(P311_INSTANCE_ROOT "/trace", "\n");
    p311_write_exact(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/enable", "1\n");
    p311_write_exact(P311_INSTANCE_ROOT "/tracing_on", "1\n");

    char before[P311_TRACE_CAPACITY];
    p311_read_bounded(P311_INSTANCE_ROOT "/trace", before, sizeof(before));
    if (strstr(before, P311_ENTRY) != NULL
        || strstr(before, P311_OFFSET) != NULL) {
        p311_fail("record-before-module-load", EPROTO);
    }

    p311_load_module(P311_MODULE);
    p311_write_exact(P311_INSTANCE_ROOT "/tracing_on", "0\n");
    p311_write_exact(
        P311_INSTANCE_ROOT "/events/" P311_GROUP "/enable", "0\n");
    if (!p311_module_loaded(P311_MODULE)
        || !p311_kallsyms_has_exact(P311_SYMBOL)) {
        p311_fail("target-absent-after-load", ENOENT);
    }

    char trace[P311_TRACE_CAPACITY];
    p311_read_bounded(P311_INSTANCE_ROOT "/trace", trace, sizeof(trace));
    size_t entry_records = p311_count(trace, ": " P311_ENTRY ":");
    size_t offset_records = p311_count(trace, ": " P311_OFFSET ":");
    const char *entry = strstr(trace, ": " P311_ENTRY ":");
    const char *offset = strstr(trace, ": " P311_OFFSET ":");
    if (entry_records == 0U
        || entry_records != offset_records
        || entry == NULL
        || offset == NULL
        || entry >= offset) {
        dprintf(
            STDOUT_FILENO,
            "P311_DELAYED_MODULE_KPROBE trace_begin\n%s"
            "P311_DELAYED_MODULE_KPROBE trace_end\n",
            trace);
        p311_fail("delayed-arm-records", ENODATA);
    }

    char profile[65536];
    unsigned long entry_hits = 0;
    unsigned long entry_missed = 0;
    unsigned long offset_hits = 0;
    unsigned long offset_missed = 0;
    p311_read_bounded(
        P311_TRACE_ROOT "/kprobe_profile", profile, sizeof(profile));
    if (!p311_profile_read(
            profile, P311_ENTRY, &entry_hits, &entry_missed)
        || !p311_profile_read(
            profile, P311_OFFSET, &offset_hits, &offset_missed)
        || entry_hits != entry_records
        || offset_hits != offset_records
        || entry_missed != 0U
        || offset_missed != 0U) {
        p311_fail("delayed-arm-profile", ENODATA);
    }

    p311_cleanup();
    dprintf(
        STDOUT_FILENO,
        "P311_DELAYED_MODULE_KPROBE result=PASS module=%s symbol=%s "
        "entry_hits=%lu offset_hits=%lu nmissed=0 cleanup=ok\n",
        P311_MODULE,
        P311_SYMBOL,
        entry_hits,
        offset_hits);
    sync();
    p311_park();
}
