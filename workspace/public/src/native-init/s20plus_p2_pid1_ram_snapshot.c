// SPDX-License-Identifier: MIT
/* S20+ P2: capture a finite early-kmsg prefix in RAM, then restore Magisk.
 * Field encoding and raw syscall entry derive from the retained P1 producer.
 * No proof is inferred from a file, exit status or token alone. The host joins
 * this source-bound producer with exact transfer, boot, ordering and namespace
 * evidence. Capture/publication failures never gate a returned-call handoff.
 * A blocked syscall or failed exec still requires attended physical recovery.
 */
#include <stddef.h>
#include <stdint.h>
#include "s20plus_p2_ram_snapshot_contract.h"

#define AT_FDCWD (-100L)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MNT_DETACH 2L

#define NR_MKNODAT 33L
#define NR_MKDIRAT 34L
#define NR_UNLINKAT 35L
#define NR_RENAMEAT 38L
#define NR_UMOUNT2 39L
#define NR_MOUNT 40L
#define NR_OPENAT 56L
#define NR_CLOSE 57L
#define NR_READ 63L
#define NR_WRITE 64L
#define NR_READLINKAT 78L
#define NR_EXIT_GROUP 94L
#define NR_NANOSLEEP 101L
#define NR_GETPID 172L
#define NR_EXECVE 221L

/* /dev/kmsg is a fixed character device. Unlike the ttyGS0 node the ACM
 * candidates depended on, it needs no sysfs lookup and no driver to have bound. */
#define P2W_KMSG_PATH "/dev/kmsg"
#define P2W_KMSG_MAJOR 1U
#define P2W_KMSG_MINOR 11U

#define P2W_DEV_DIR "/dev"
#define P2W_PROC_DIR "/proc"
#define P2W_PROC_SELF "/proc/self"
#define P2W_PROC_SELF_NS_PID "/proc/self/ns/pid"
#define P2W_BOOT_ID_PATH "/proc/sys/kernel/random/boot_id"

/* The resident magiskinit, parked here by the builder, and its restored name. */
#define P2W_MAGISK_INIT_STAGED "/init.magisk"
#define P2W_INIT_PATH "/init"

/*
 * Candidate identity. Fixed, not random: the builder must be reproducible and
 * the owner pins this value in the manifest alongside the artifact digests, so
 * a record naming it is a record naming this exact candidate build. It is not a
 * secret and not an authenticator. Completeness and first-record checks
 * constrain ordering; producer attribution additionally depends on the reviewed
 * path and operational assumptions above.
 */
#define P2W_CANDIDATE_ID P2_CANDIDATE_ID

#define P2W_MAGIC P2_MAGIC
#define P2W_STAGE P2_STAGE
/* Emitted in place of any kernel value this witness could not read, so a
 * partial emission stays well formed and is still refused by the consumer. */
#define P2W_UNAVAILABLE "unavailable"

#define P2W_RECORD_MAX 256U
#define P2W_FIELD_MAX 48U
#define P2W_PID_DIGITS 10U

struct p2w_timespec {
    int64_t tv_sec;
    int64_t tv_nsec;
};

#ifdef S20PLUS_P2_WITNESS_FAULT_HARNESS

/*
 * Host-only fault-injection seam, and the only difference between what the host
 * tests execute and what the device executes. Everything below it - the gate,
 * the record, the rename, the exec, the park - is the same source either way,
 * so the failure paths the tests drive are the device's own control flow rather
 * than a second implementation of it.
 *
 * It cannot reach a device build. The device link is -nostdlib -static, so an
 * unresolved p2w_harness_syscall would fail the link, and the builder also
 * refuses a source whose seam is not guarded by this macro.
 */
long p2w_harness_syscall(long number, long a0, long a1, long a2, long a3, long a4);

static long p2w_syscall5(long number, long a0, long a1, long a2, long a3, long a4) {
    return p2w_harness_syscall(number, a0, a1, a2, a3, a4);
}

#else

__attribute__((always_inline)) static inline long p2w_syscall5(
    long number,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4
) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x8 asm("x8") = number;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x8)
        : "memory"
    );
    return x0;
}

#endif

__attribute__((always_inline)) static inline long p2w_syscall4(long number, long a0, long a1, long a2, long a3) {
    return p2w_syscall5(number, a0, a1, a2, a3, 0);
}

__attribute__((always_inline)) static inline long p2w_syscall3(long number, long a0, long a1, long a2) {
    return p2w_syscall5(number, a0, a1, a2, 0, 0);
}

__attribute__((always_inline)) static inline long p2w_syscall2(long number, long a0, long a1) {
    return p2w_syscall5(number, a0, a1, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p2w_syscall1(long number, long a0) {
    return p2w_syscall5(number, a0, 0, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p2w_syscall0(long number) {
    return p2w_syscall5(number, 0, 0, 0, 0, 0);
}

static long p2w_getpid(void) {
    return p2w_syscall0(NR_GETPID);
}

/* Same encoding the consumed candidates used, kept so a regression in it is
 * visible in the host self-test rather than as a wrong node on the device. */
static uint64_t p2w_make_dev(unsigned int major_number, unsigned int minor_number) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static void p2w_sleep_ms(int64_t milliseconds) {
    struct p2w_timespec request;
    request.tv_sec = milliseconds / 1000;
    request.tv_nsec = (milliseconds % 1000) * 1000000;
    (void)p2w_syscall2(NR_NANOSLEEP, (long)(uintptr_t)&request, 0);
}

__attribute__((noreturn)) static void p2w_park(void) {
    for (;;) {
        p2w_sleep_ms(60000);
    }
}

/*
 * The record is parsed by the consumer on ';' and '=', and /dev/kmsg escapes
 * anything outside printable ASCII as \xNN. Kernel-supplied values are therefore
 * reduced to one closed alphabet before they enter the record: a surprising byte
 * becomes '_' rather than a separator, an escape, or a torn field.
 */
static int p2w_value_byte_allowed(unsigned char value) {
    if (value >= '0' && value <= '9') {
        return 1;
    }
    if (value >= 'a' && value <= 'z') {
        return 1;
    }
    if (value >= 'A' && value <= 'Z') {
        return 1;
    }
    return value == ':' || value == '[' || value == ']' || value == '-' || value == '.' || value == '_';
}

static size_t p2w_copy_literal(char *destination, size_t offset, size_t limit, const char *source) {
    size_t index = 0;
    while (source[index] != '\0' && offset < limit) {
        destination[offset] = source[index];
        offset++;
        index++;
    }
    return offset;
}

static size_t p2w_copy_sanitized(char *destination, size_t offset, size_t limit, const char *source, size_t length) {
    size_t index = 0;
    while (index < length && offset < limit) {
        unsigned char value = (unsigned char)source[index];
        if (value == '\0' || value == '\n') {
            break;
        }
        destination[offset] = p2w_value_byte_allowed(value) ? (char)value : '_';
        offset++;
        index++;
    }
    return offset;
}

static size_t p2w_copy_decimal(char *destination, size_t offset, size_t limit, uint64_t value) {
    char digits[P2W_PID_DIGITS];
    size_t index = P2W_PID_DIGITS;
    while (index > 0) {
        index--;
        digits[index] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    for (index = 0; index < P2W_PID_DIGITS && offset < limit; index++) {
        destination[offset] = digits[index];
        offset++;
    }
    return offset;
}

/*
 * Read one bounded kernel-supplied value. `length` is the number of bytes
 * actually produced; zero means unavailable and the caller substitutes the
 * fixed placeholder rather than emitting an empty field.
 */
static size_t p2w_read_link(const char *path, char *buffer, size_t limit) {
    long result = p2w_syscall4(
        NR_READLINKAT, AT_FDCWD, (long)(uintptr_t)path, (long)(uintptr_t)buffer, (long)limit
    );
    if (result <= 0 || (size_t)result > limit) {
        return 0;
    }
    return (size_t)result;
}

static size_t p2w_read_file(const char *path, char *buffer, size_t limit) {
    long descriptor = p2w_syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, O_RDONLY | O_CLOEXEC, 0);
    long result;
    if (descriptor < 0) {
        return 0;
    }
    result = p2w_syscall3(NR_READ, descriptor, (long)(uintptr_t)buffer, (long)limit);
    (void)p2w_syscall1(NR_CLOSE, descriptor);
    if (result <= 0 || (size_t)result > limit) {
        return 0;
    }
    return (size_t)result;
}

static size_t p2w_append_field(
    char *record,
    size_t offset,
    size_t limit,
    const char *name,
    const char *value,
    size_t value_length
) {
    offset = p2w_copy_literal(record, offset, limit, name);
    offset = p2w_copy_literal(record, offset, limit, "=");
    if (value_length == 0) {
        offset = p2w_copy_literal(record, offset, limit, P2W_UNAVAILABLE);
    } else {
        offset = p2w_copy_sanitized(record, offset, limit, value, value_length);
    }
    return p2w_copy_literal(record, offset, limit, ";");
}

static char p2_boot_id[36];

static size_t p2w_build_record(char *record, size_t limit, uint64_t pid) {
    char procself[P2W_FIELD_MAX];
    char pidns[P2W_FIELD_MAX];
    char bootid[P2W_FIELD_MAX];
    size_t procself_length = p2w_read_link(P2W_PROC_SELF, procself, sizeof(procself));
    size_t pidns_length = p2w_read_link(P2W_PROC_SELF_NS_PID, pidns, sizeof(pidns));
    size_t bootid_length = p2w_read_file(P2W_BOOT_ID_PATH, bootid, sizeof(bootid));
    size_t offset = 0;
    for (size_t i = 0; i < 36; ++i) p2_boot_id[i] = bootid_length >= 36 ? bootid[i] : 0;

    offset = p2w_copy_literal(record, offset, limit, P2W_MAGIC ";cand=" P2W_CANDIDATE_ID ";pid=");
    offset = p2w_copy_decimal(record, offset, limit, pid);
    offset = p2w_copy_literal(record, offset, limit, ";");
    offset = p2w_append_field(record, offset, limit, "procself", procself, procself_length);
    offset = p2w_append_field(record, offset, limit, "pidns", pidns, pidns_length);
    offset = p2w_append_field(record, offset, limit, "bootid", bootid, bootid_length);
    offset = p2w_copy_literal(record, offset, limit, "stage=" P2W_STAGE "\n");
    return offset;
}

/* ARM64 UAPI values/layouts; the focused ABI test checks the target headers and
 * executes representative real ARM64 file syscalls through qemu-aarch64. */
#define P2_O_RDWR 2
#define P2_O_CREAT 0100
#define P2_O_EXCL 0200
#define P2_O_NONBLOCK 04000
#define P2_O_DIRECTORY 040000
#define P2_O_NOFOLLOW 0100000
#define P2_NR_FCNTL 25
#define P2_NR_FSTATFS 44
#define P2_NR_LSEEK 62
#define P2_NR_FSTAT 80
#define P2_NR_FSYNC 82
#define P2_NR_CLOCK_GETTIME 113
#define P2_NR_GETUID 174
#define P2_NR_GETEUID 175
#define P2_NR_RENAMEAT2 276
#define P2_TMPFS_MAGIC 0x01021994UL
#define P2_RAMFS_MAGIC 0x858458f6UL
#define P2_PROC_MAGIC 0x9fa0UL
#define P2_DIR_FLAGS (P2_O_DIRECTORY | P2_O_NOFOLLOW | O_CLOEXEC)

struct p2_statfs {
    int64_t type, bsize;
    uint64_t blocks, bfree, bavail, files, ffree;
    int32_t fsid[2];
    int64_t namelen, frsize, flags, spare[4];
};
struct p2_stat {
    uint64_t dev, ino;
    uint32_t mode, nlink, uid, gid;
    uint64_t rdev, pad1;
    int64_t size;
    int32_t blksize, pad2;
    int64_t blocks, atime;
    uint64_t atime_ns;
    int64_t mtime;
    uint64_t mtime_ns;
    int64_t ctime;
    uint64_t ctime_ns;
    uint32_t unused[2];
};
_Static_assert(sizeof(struct p2_statfs) == 120, "ARM64 statfs layout");
_Static_assert(sizeof(struct p2_stat) == 128, "ARM64 stat layout");

static unsigned char p2_data[P2_SNAPSHOT_HEADER + P2_MAX_CAPTURE_BYTES];
static uint64_t p2_deadline;

static int p2_equal(const void *a, const void *b, size_t n) {
    const unsigned char *x = a, *y = b;
    for (size_t i = 0; i < n; ++i) if (x[i] != y[i]) return 0;
    return 1;
}
static void p2_zero(void *a, size_t n) {
    unsigned char *x = a;
    for (size_t i = 0; i < n; ++i) x[i] = 0;
}
static void p2_copy(void *a, const void *b, size_t n) {
    unsigned char *x = a;
    const unsigned char *y = b;
    for (size_t i = 0; i < n; ++i) x[i] = y[i];
}
static void p2_le(unsigned char *p, uint64_t value, unsigned n) {
    for (unsigned i = 0; i < n; ++i) { p[i] = (unsigned char)value; value >>= 8; }
}
static long p2_openat(long directory, const char *name, long flags, long mode) {
    return p2w_syscall4(NR_OPENAT, directory, (long)(uintptr_t)name, flags, mode);
}
static void p2_close(long fd) { if (fd >= 0) (void)p2w_syscall1(NR_CLOSE, fd); }
static int64_t p2_now(void) {
    struct p2w_timespec t;
    if (p2w_syscall2(P2_NR_CLOCK_GETTIME, 1, (long)(uintptr_t)&t) != 0 ||
        t.tv_sec < 0 || t.tv_nsec < 0 || t.tv_nsec >= 1000000000 ||
        t.tv_sec > INT64_MAX / 1000000000 - 10) return -1;
    return t.tv_sec * 1000000000 + t.tv_nsec;
}
static int p2_time_left(void) {
    int64_t now = p2_now();
    return now >= 0 && (uint64_t)now < p2_deadline;
}
static long p2_fs(long fd) {
    struct p2_statfs s;
    if (p2w_syscall2(P2_NR_FSTATFS, fd, (long)(uintptr_t)&s) != 0) return -1;
    return s.type;
}
static int p2_ram(long fd) {
    long type = p2_fs(fd);
    return type == P2_TMPFS_MAGIC || type == P2_RAMFS_MAGIC;
}
static int p2_stat_fd(long fd, struct p2_stat *s) {
    return p2w_syscall2(P2_NR_FSTAT, fd, (long)(uintptr_t)s) == 0;
}
static int p2_stable(const struct p2_stat *a, const struct p2_stat *b) {
    return a->dev == b->dev && a->ino == b->ino && a->mode == b->mode &&
        a->nlink == b->nlink && a->uid == b->uid && a->gid == b->gid &&
        a->size == b->size && a->mtime == b->mtime && a->mtime_ns == b->mtime_ns &&
        a->ctime == b->ctime && a->ctime_ns == b->ctime_ns;
}
static int p2_regular(const struct p2_stat *s) {
    return (s->mode & 0177777U) == 0100600U && s->nlink == 1 &&
        s->uid == 0 && s->gid == 0 && s->size >= 0 &&
        (uint64_t)s->size <= sizeof(p2_data);
}
static int p2_write_full(long fd, const void *buffer, size_t n) {
    const unsigned char *p = buffer;
    size_t done = 0;
    for (unsigned calls = 0; done < n && calls < P2_MAX_IO_CALLS; ++calls) {
        if (!p2_time_left()) return 0;
        long rc = p2w_syscall3(NR_WRITE, fd, (long)(uintptr_t)(p + done), (long)(n - done));
        if (rc == -4) continue;
        if (rc == -11) { p2w_sleep_ms(2); continue; }
        if (rc <= 0 || (size_t)rc > n - done) return 0;
        done += (size_t)rc;
    }
    return done == n;
}
static int p2_read_counted(long fd, void *buffer, size_t n, size_t *produced) {
    unsigned char *p = buffer;
    size_t done = 0;
    *produced = 0;
    for (unsigned calls = 0; done < n && calls < P2_MAX_IO_CALLS; ++calls) {
        if (!p2_time_left()) return 0;
        long rc = p2w_syscall3(NR_READ, fd, (long)(uintptr_t)(p + done), (long)(n - done));
        if (rc == -4) continue;
        if (rc <= 0 || (size_t)rc > n - done) return 0;
        done += (size_t)rc;
        *produced = done;
    }
    return done == n;
}
static int p2_read_full(long fd, void *buffer, size_t n) {
    size_t produced;
    return p2_read_counted(fd, buffer, n, &produced);
}

/* Open the existing ramdisk directory component by component. A persistent
 * filesystem, symlink or absent component never gets a fallback directory. */
static long p2_output_dir(void) {
    long root = p2_openat(AT_FDCWD, "/", P2_DIR_FLAGS, 0), overlay = -1, sbin = -1;
    if (root >= 0 && p2_ram(root)) {
        overlay = p2_openat(root, "overlay.d", P2_DIR_FLAGS, 0);
        if (overlay >= 0 && p2_ram(overlay)) {
            sbin = p2_openat(overlay, "sbin", P2_DIR_FLAGS, 0);
            if (sbin >= 0 && !p2_ram(sbin)) { p2_close(sbin); sbin = -1; }
        }
    }
    p2_close(overlay); p2_close(root);
    return sbin;
}
static int p2_publish(long directory, size_t length) {
    long fd = p2_openat(directory, P2_PARTIAL_NAME,
        P2_O_RDWR | P2_O_CREAT | P2_O_EXCL | P2_O_NOFOLLOW | O_CLOEXEC, 0600);
    struct p2_stat st;
    unsigned char check[4096];
    if (fd < 0) return 0;
    int ok = p2_ram(fd) && p2_write_full(fd, p2_data, length) &&
        p2w_syscall1(P2_NR_FSYNC, fd) == 0 && p2_stat_fd(fd, &st) &&
        p2_regular(&st) && (uint64_t)st.size == length &&
        p2w_syscall3(P2_NR_LSEEK, fd, 0, 0) == 0;
    for (size_t offset = 0; ok && offset < length;) {
        size_t amount = length - offset;
        if (amount > sizeof(check)) amount = sizeof(check);
        ok = p2_read_full(fd, check, amount) && p2_equal(check, p2_data + offset, amount);
        offset += amount;
    }
    /* A failed close leaves only .part as well. A final name never replaces
     * another file, even if an unexpected preexisting name appears. */
    if (p2w_syscall1(NR_CLOSE, fd) != 0) ok = 0;
    if (!ok || !p2_time_left()) return 0;
    return p2w_syscall5(P2_NR_RENAMEAT2, directory, (long)(uintptr_t)P2_PARTIAL_NAME,
        directory, (long)(uintptr_t)P2_SNAPSHOT_NAME, 1) == 0;
}

static int p2_is_witness(const unsigned char *raw, size_t n, const char *body, size_t length) {
    for (size_t i = 0; i < n; ++i) {
        if (raw[i] == ';') return n - i - 1 == length && p2_equal(raw + i + 1, body, length);
    }
    return 0;
}

static void p2_capture(uint64_t pid) {
    char body[P2W_RECORD_MAX];
    unsigned char record[8192];
    uint32_t status = P2_STATUS_SETUP;
    int64_t error = 0, start = p2_now(), end;
    uint64_t length = 0, records = 0;
    long directory = -1, proc = -1, writer = -1, reader = -1, mounted = -1, created = -1;
    if (start < 0) return;
    p2_deadline = (uint64_t)start + P2_MAX_ELAPSED_NS;
    directory = p2_output_dir();
    if (directory < 0) return;
    (void)p2w_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)"/proc", 0755);
    mounted = p2w_syscall5(NR_MOUNT, (long)(uintptr_t)"proc", (long)(uintptr_t)"/proc",
        (long)(uintptr_t)"proc", 0, 0);
    proc = p2_openat(AT_FDCWD, "/proc", P2_DIR_FLAGS, 0);
    if (proc < 0 || p2_fs(proc) != P2_PROC_MAGIC) { error = -19; goto finish; }
    (void)p2w_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)"/dev", 0755);
    created = p2w_syscall4(NR_MKNODAT, AT_FDCWD, (long)(uintptr_t)P2W_KMSG_PATH,
        S_IFCHR | 0600, (long)p2w_make_dev(1, 11));
    writer = p2_openat(AT_FDCWD, P2W_KMSG_PATH, O_WRONLY | P2_O_NONBLOCK | P2_O_NOFOLLOW | O_CLOEXEC, 0);
    struct p2_stat node;
    if (writer < 0 || !p2_stat_fd(writer, &node) ||
        (node.mode & 0170000) != S_IFCHR || node.rdev != p2w_make_dev(1, 11)) {
        error = -19; goto finish;
    }
    size_t body_size = p2w_build_record(body, sizeof(body), pid);
    /* kmsg writes are records: a short write is not repaired by a second
     * write, which would create another record. One EINTR also fails closed. */
    long emitted = p2w_syscall3(NR_WRITE, writer, (long)(uintptr_t)body, (long)body_size);
    if (emitted != (long)body_size) { status = P2_STATUS_EMIT; error = emitted; goto finish; }
    reader = p2_openat(AT_FDCWD, P2W_KMSG_PATH, O_RDONLY | P2_O_NONBLOCK | P2_O_NOFOLLOW | O_CLOEXEC, 0);
    if (reader < 0 || !p2_stat_fd(reader, &node) ||
        (node.mode & 0170000) != S_IFCHR || node.rdev != p2w_make_dev(1, 11)) {
        status = P2_STATUS_READ; error = reader; goto finish;
    }
    status = P2_STATUS_READ;
    for (unsigned calls = 0; calls < P2_MAX_IO_CALLS; ++calls) {
        end = p2_now();
        if (end < start) { status = P2_STATUS_CLOCK; break; }
        if ((uint64_t)end >= p2_deadline) { status = P2_STATUS_DEADLINE; break; }
        if (records == P2_MAX_RECORDS) { status = P2_STATUS_RECORDS; break; }
        long n = p2w_syscall3(NR_READ, reader, (long)(uintptr_t)record, sizeof(record));
        if (n == -4) { status = P2_STATUS_READ; error = n; continue; }
        if (n == -11) { status = P2_STATUS_IDLE; error = n; break; }
        if (n == -32) { status = P2_STATUS_OVERRUN; error = n; break; }
        if (n <= 0 || (size_t)n > sizeof(record)) { status = P2_STATUS_READ; error = n; break; }
        if ((uint64_t)n > P2_MAX_CAPTURE_BYTES - length) { status = P2_STATUS_BYTES; break; }
        p2_copy(p2_data + P2_SNAPSHOT_HEADER + length, record, (size_t)n);
        length += (uint64_t)n; ++records;
        if (p2_is_witness(record, (size_t)n, body, body_size)) {
            status = P2_STATUS_WITNESS; error = 0; break;
        }
    }
finish:
    p2_close(reader); p2_close(writer); p2_close(proc);
    if (created == 0) (void)p2w_syscall3(NR_UNLINKAT, AT_FDCWD, (long)(uintptr_t)P2W_KMSG_PATH, 0);
    if (mounted == 0 && p2w_syscall2(NR_UMOUNT2, (long)(uintptr_t)"/proc", 0) != 0)
        (void)p2w_syscall2(NR_UMOUNT2, (long)(uintptr_t)"/proc", MNT_DETACH);
    end = p2_now();
    if (end < start) { status = P2_STATUS_CLOCK; end = start; }
    if ((uint64_t)(end - start) >= P2_MAX_ELAPSED_NS && status == P2_STATUS_WITNESS)
        status = P2_STATUS_DEADLINE;
    p2_zero(p2_data, P2_SNAPSHOT_HEADER);
    p2_copy(p2_data, P2_SNAPSHOT_MAGIC, sizeof(P2_SNAPSHOT_MAGIC) - 1);
    p2_le(p2_data + 16, 1, 4); p2_le(p2_data + 20, status, 4);
    p2_le(p2_data + 24, length, 8); p2_le(p2_data + 32, records, 8);
    p2_le(p2_data + 40, (uint64_t)error, 8); p2_le(p2_data + 48, (uint64_t)(end - start), 8);
    p2_copy(p2_data + 56, P2_CANDIDATE_ID, 32); p2_copy(p2_data + 88, p2_boot_id, 36);
    /* A capture deadline does not suppress its diagnostic prefix. Publication
     * has a separate finite budget, also checked on every returned I/O call. */
    p2_deadline = (uint64_t)end + P2_MAX_PUBLISH_NS;
    (void)p2_publish(directory, P2_SNAPSHOT_HEADER + (size_t)length);
    p2_close(directory);
}

static int p2_read_boot(char value[36]) {
    char buffer[48];
    size_t n = p2w_read_file(P2W_BOOT_ID_PATH, buffer, sizeof(buffer));
    if (n != 37 || buffer[36] != '\n') return 0;
    p2_copy(value, buffer, 36);
    return 1;
}

/* The reader's own executable path selects one of two fixed Magisk RAM
 * locations. There is no command-line path, /data fallback or filesystem write. */
static int p2_read_snapshot(void) {
    unsigned char header[P2_READER_HEADER];
    char executable[128], before_boot[36], after_boot[36];
    struct p2_stat before, after;
    uint32_t status = P2_READ_ABSENT, partial = 0, location = 0;
    long directory = -1, fd = -1, other = -1, type = -1;
    size_t amount = 0;
    int64_t now = p2_now();
    p2_zero(header, sizeof(header)); p2_zero(&before, sizeof(before));
    p2_zero(before_boot, sizeof(before_boot)); p2_zero(after_boot, sizeof(after_boot));
    if (now < 0 || p2w_syscall0(P2_NR_GETUID) != 0 || p2w_syscall0(P2_NR_GETEUID) != 0) return 2;
    p2_deadline = (uint64_t)now + P2_READER_ELAPSED_NS;
    long flags = p2w_syscall3(P2_NR_FCNTL, 1, 3, 0);
    if (flags < 0 || p2w_syscall3(P2_NR_FCNTL, 1, 4, flags | P2_O_NONBLOCK) != 0) return 2;
    size_t n = p2w_read_link("/proc/self/exe", executable, sizeof(executable));
    static const char debug_path[] = "/debug_ramdisk/" P2_READER_NAME;
    static const char sbin_path[] = "/sbin/" P2_READER_NAME;
    if (n == sizeof(debug_path) - 1 && p2_equal(executable, debug_path, n)) {
        directory = p2_openat(AT_FDCWD, "/debug_ramdisk", P2_DIR_FLAGS, 0);
    } else if (n == sizeof(sbin_path) - 1 && p2_equal(executable, sbin_path, n)) {
        location = 1; directory = p2_openat(AT_FDCWD, "/sbin", P2_DIR_FLAGS, 0);
    } else { status = P2_READ_METADATA; goto done; }
    if (directory < 0 || !p2_ram(directory)) { status = P2_READ_FILESYSTEM; goto done; }
    if (!p2_read_boot(before_boot)) { status = P2_READ_BOOT; goto done; }
    fd = p2_openat(directory, P2_SNAPSHOT_NAME, O_RDONLY | P2_O_NOFOLLOW | P2_O_NONBLOCK | O_CLOEXEC, 0);
    other = p2_openat(directory, P2_PARTIAL_NAME, O_RDONLY | P2_O_NOFOLLOW | P2_O_NONBLOCK | O_CLOEXEC, 0);
    if (fd >= 0 && other >= 0) status = P2_READ_COLLISION;
    else if (fd >= 0 && other == -2) status = P2_READ_OK;
    else if (fd == -2 && other >= 0) { fd = other; other = -1; partial = 1; status = P2_READ_PARTIAL; }
    else if (fd == -2 && other == -2) goto done;
    else { status = P2_READ_IO; goto done; }
    type = p2_fs(fd);
    if (!p2_ram(fd)) { status = P2_READ_FILESYSTEM; goto done; }
    if (!p2_stat_fd(fd, &before) || !p2_regular(&before)) { status = P2_READ_METADATA; goto done; }
    amount = (size_t)before.size;
    size_t produced;
    if (!p2_read_counted(fd, p2_data, amount, &produced)) {
        status = P2_READ_IO; amount = produced; goto done;
    }
    if (!p2_stat_fd(fd, &after) || !p2_stable(&before, &after)) status = P2_READ_CHANGED;
    if (!p2_read_boot(after_boot) || !p2_equal(before_boot, after_boot, 36)) status = P2_READ_BOOT;
done:
    p2_close(other); p2_close(fd); p2_close(directory);
    p2_copy(header, P2_READER_MAGIC, sizeof(P2_READER_MAGIC) - 1);
    p2_le(header + 16, 1, 4); p2_le(header + 20, status, 4); p2_le(header + 24, amount, 8);
    p2_le(header + 32, (uint64_t)type, 8); p2_le(header + 40, before.dev, 8);
    p2_le(header + 48, before.ino, 8); p2_le(header + 56, before.mode, 4);
    p2_le(header + 60, before.nlink, 4); p2_le(header + 64, before.uid, 4);
    p2_le(header + 68, before.gid, 4); p2_le(header + 72, partial, 4); p2_le(header + 76, location, 4);
    p2_copy(header + 80, before_boot, 36); p2_copy(header + 116, after_boot, 36);
    if (!p2_write_full(1, header, sizeof(header)) || !p2_write_full(1, p2_data, amount)) return 2;
    return status == P2_READ_OK ? 0 : 2;
}

#if !defined(S20PLUS_P2_WITNESS_FAULT_HARNESS)
__asm__(".global _start\n_start:\nmov x0, sp\nb p2w_main\n");
#endif
__attribute__((noreturn)) void p2w_main(unsigned long *stack) {
    long pid = p2w_getpid();
#ifdef S20PLUS_P2_READER_ONLY
    (void)stack;
    int status = pid == 1 ? 2 : p2_read_snapshot();
    (void)p2w_syscall1(NR_EXIT_GROUP, status);
    p2w_park();
#else
    if (pid != 1) p2w_park();
    p2_capture((uint64_t)pid);
    if (p2w_syscall4(NR_RENAMEAT, AT_FDCWD, (long)(uintptr_t)P2W_MAGISK_INIT_STAGED,
        AT_FDCWD, (long)(uintptr_t)P2W_INIT_PATH) != 0) p2w_park();
    unsigned long argc = stack[0];
    char **argv = (char **)&stack[1], **envp = argv + argc + 1;
    (void)p2w_syscall3(NR_EXECVE, (long)(uintptr_t)P2W_INIT_PATH,
        (long)(uintptr_t)argv, (long)(uintptr_t)envp);
    p2w_park();
#endif
}
