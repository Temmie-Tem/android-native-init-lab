// SPDX-License-Identifier: MIT
/*
 * S20+ G986N P1 direct-PID1 exec-handoff witness (V1).
 *
 * Purpose, stated exactly: emit one kernel-timestamped record that ties this
 * candidate's identity, the PID the kernel actually gave this process, the
 * initial PID namespace, and this boot together - and then give control back to
 * the resident Magisk init so the same boot reaches Android and the record can
 * be read.
 *
 * Why this shape rather than the consumed candidates' shapes:
 *
 *   - The three ACM candidates put their evidence at the end of a configfs /
 *     gadget / UDC / ttyGS0 chain. Every link fails silently, and a completed
 *     observation window with no banner is what the whole chain failing looks
 *     like, and also what /init never running looks like. All three returned
 *     NO_PROOF.
 *   - The V4 minimal candidate replaced that chain with a download-mode reboot
 *     request. Independent review then refuted Download arrival as proof: the
 *     transfer command carries its own --reboot, two Download topologies are
 *     allowlisted, and a watchdog, a PMIC reset, a bootloader fallback or an
 *     operator entry all enumerate identically.
 *   - Both of those candidates also wrote a FIXED /dev/kmsg banner. That was
 *     refuted too, and correctly: a constant string is characteristic of this
 *     candidate, not authenticated as coming from it. Resident root can write
 *     the same bytes.
 *
 * What is different here is not the channel but what goes through it and what
 * the kernel guarantees about it:
 *
 *   1. `procself` and `pidns` are not constants this binary chose. They are the
 *      kernel's own answers, read back out of procfs: /proc/self resolves to the
 *      caller's PID, and /proc/self/ns/pid names the nsfs inode of the caller's
 *      PID namespace. The initial PID namespace has one fixed inode,
 *      PROC_PID_INIT_INO, and no other namespace can present it.
 *   2. `bootid` is this boot's kernel-generated UUID, read at PID1 time. A
 *      record retained from any earlier boot carries a different one.
 *   3. The record's timestamp is not ours to choose. devkmsg_write() ignores any
 *      caller timestamp and log_store() stamps every record with local_clock().
 *      That fixes the record's ORDER. It says nothing about who wrote it, and
 *      the first revision of this file claimed more than that. It said the
 *      consumer bounded the window with the first `magiskinit:` or `init:`
 *      record, so no later writer could land before it. Review refuted that: a
 *      body prefix identifies no process, and the check passed on captures
 *      whose whole boot prefix was missing, where nothing showed the observed
 *      `init:` line was the first one.
 *   4. What actually bounds the window is the facility field. devkmsg_write()
 *      starts at `facility = 1` and takes a caller's `<n>` prefix only when
 *      `LOG_FACILITY(u) != 0`, so no userspace writer can claim facility 0 -
 *      the kernel source says that is the point of it. run_init_process() then
 *      prints `Run /init as init process` with pr_info, at facility 0,
 *      immediately before do_execve. The consumer requires a contiguous capture
 *      from sequence zero and this witness as its first userspace-facility
 *      record. This establishes record order, not the writer's identity alone:
 *      attribution also requires the reviewed boot path and operational
 *      assumptions below. Early userspace helpers are not universally excluded.
 *      This binary creates no child process: the builder checks its syscall set.
 *
 * None of that defeats an adversary who can run code before magiskinit or lie
 * to the kernel; root can write /dev/kmsg whenever it likes. That adversary is
 * outside the risk-tier threat model, and this file does not pretend otherwise.
 * The rest of the attribution is operational and is stated in the consumer's
 * ASSUMPTIONS: the pinned artifact digests the transfer journal records, the
 * boot id read in the same session, and one attended boot.
 *
 * The handoff. This candidate's boot ramdisk carries the resident magiskinit at
 * `/init.magisk` and this witness at `/init`. magiskinit MUST see its own bytes
 * at `/init`: prepare_data() copies /init to /data/magiskinit, and on this
 * device's first-stage path hijack_init_with_switch_root() renames /init to
 * /sdcard so the original init's SwitchRoot bind-mounts it onto
 * /system/bin/init. Handing off by exec'ing a magiskinit that is NOT at /init
 * would therefore break second-stage hijacking and the boot with it. So the
 * witness restores the exact resident world before leaving: it renames
 * /init.magisk onto /init and execs /init. After that rename the ramdisk root is
 * membership- and byte-identical to the resident boot's, and magiskinit runs
 * with the argv and envp the kernel handed PID 1.
 *
 * Two failure rules follow from that and are load bearing:
 *
 *   - The exec is reached only when the rename SUCCEEDED. Exec'ing /init after a
 *     failed rename would re-exec this witness as PID 1, forever.
 *   - Evidence return values do not gate handoff: they are discarded and no
 *     result-dependent branch separates evidence from rename. This is not a
 *     liveness guarantee; an evidence syscall could block before handoff.
 *
 * If the handoff is impossible the witness parks. It never exits: PID 1 exiting
 * is a kernel panic. Parking leaves the operator's physical Download entry and
 * the mandatory resident-Magisk rollback available, which is the identical
 * recovery posture the consumed candidates had.
 */

#include <stddef.h>
#include <stdint.h>

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
#define P1W_KMSG_PATH "/dev/kmsg"
#define P1W_KMSG_MAJOR 1U
#define P1W_KMSG_MINOR 11U

#define P1W_DEV_DIR "/dev"
#define P1W_PROC_DIR "/proc"
#define P1W_PROC_SELF "/proc/self"
#define P1W_PROC_SELF_NS_PID "/proc/self/ns/pid"
#define P1W_BOOT_ID_PATH "/proc/sys/kernel/random/boot_id"

/* The resident magiskinit, parked here by the builder, and its restored name. */
#define P1W_MAGISK_INIT_STAGED "/init.magisk"
#define P1W_INIT_PATH "/init"

/*
 * Candidate identity. Fixed, not random: the builder must be reproducible and
 * the owner pins this value in the manifest alongside the artifact digests, so
 * a record naming it is a record naming this exact candidate build. It is not a
 * secret and not an authenticator. Completeness and first-record checks
 * constrain ordering; producer attribution additionally depends on the reviewed
 * path and operational assumptions above.
 */
#define P1W_CANDIDATE_ID "6f3a1c7d0b45e29840d17ac6e5b93f21"

#define P1W_MAGIC "S20PLUS_P1_PID1_WITNESS_V1"
#define P1W_STAGE "PRE_EXEC_HANDOFF"
/* Emitted in place of any kernel value this witness could not read, so a
 * partial emission stays well formed and is still refused by the consumer. */
#define P1W_UNAVAILABLE "unavailable"

#define P1W_RECORD_MAX 256U
#define P1W_FIELD_MAX 48U
#define P1W_PID_DIGITS 10U

struct p1w_timespec {
    int64_t tv_sec;
    int64_t tv_nsec;
};

#ifdef S20PLUS_P1_WITNESS_FAULT_HARNESS

/*
 * Host-only fault-injection seam, and the only difference between what the host
 * tests execute and what the device executes. Everything below it - the gate,
 * the record, the rename, the exec, the park - is the same source either way,
 * so the failure paths the tests drive are the device's own control flow rather
 * than a second implementation of it.
 *
 * It cannot reach a device build. The device link is -nostdlib -static, so an
 * unresolved p1w_harness_syscall would fail the link, and the builder also
 * refuses a source whose seam is not guarded by this macro.
 */
long p1w_harness_syscall(long number, long a0, long a1, long a2, long a3, long a4);

static long p1w_syscall5(long number, long a0, long a1, long a2, long a3, long a4) {
    return p1w_harness_syscall(number, a0, a1, a2, a3, a4);
}

#else

__attribute__((always_inline)) static inline long p1w_syscall5(
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

__attribute__((always_inline)) static inline long p1w_syscall4(long number, long a0, long a1, long a2, long a3) {
    return p1w_syscall5(number, a0, a1, a2, a3, 0);
}

__attribute__((always_inline)) static inline long p1w_syscall3(long number, long a0, long a1, long a2) {
    return p1w_syscall5(number, a0, a1, a2, 0, 0);
}

__attribute__((always_inline)) static inline long p1w_syscall2(long number, long a0, long a1) {
    return p1w_syscall5(number, a0, a1, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p1w_syscall1(long number, long a0) {
    return p1w_syscall5(number, a0, 0, 0, 0, 0);
}

__attribute__((always_inline)) static inline long p1w_syscall0(long number) {
    return p1w_syscall5(number, 0, 0, 0, 0, 0);
}

static long p1w_getpid(void) {
    return p1w_syscall0(NR_GETPID);
}

/* Same encoding the consumed candidates used, kept so a regression in it is
 * visible in the host self-test rather than as a wrong node on the device. */
static uint64_t p1w_make_dev(unsigned int major_number, unsigned int minor_number) {
    return ((uint64_t)(minor_number & 0xffU)) |
           ((uint64_t)(major_number & 0xfffU) << 8) |
           ((uint64_t)(minor_number & ~0xffU) << 12) |
           ((uint64_t)(major_number & ~0xfffU) << 32);
}

static void p1w_sleep_ms(int64_t milliseconds) {
    struct p1w_timespec request;
    request.tv_sec = milliseconds / 1000;
    request.tv_nsec = (milliseconds % 1000) * 1000000;
    (void)p1w_syscall2(NR_NANOSLEEP, (long)(uintptr_t)&request, 0);
}

__attribute__((noreturn)) static void p1w_park(void) {
    for (;;) {
        p1w_sleep_ms(60000);
    }
}

/*
 * The record is parsed by the consumer on ';' and '=', and /dev/kmsg escapes
 * anything outside printable ASCII as \xNN. Kernel-supplied values are therefore
 * reduced to one closed alphabet before they enter the record: a surprising byte
 * becomes '_' rather than a separator, an escape, or a torn field.
 */
static int p1w_value_byte_allowed(unsigned char value) {
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

static size_t p1w_copy_literal(char *destination, size_t offset, size_t limit, const char *source) {
    size_t index = 0;
    while (source[index] != '\0' && offset < limit) {
        destination[offset] = source[index];
        offset++;
        index++;
    }
    return offset;
}

static size_t p1w_copy_sanitized(char *destination, size_t offset, size_t limit, const char *source, size_t length) {
    size_t index = 0;
    while (index < length && offset < limit) {
        unsigned char value = (unsigned char)source[index];
        if (value == '\0' || value == '\n') {
            break;
        }
        destination[offset] = p1w_value_byte_allowed(value) ? (char)value : '_';
        offset++;
        index++;
    }
    return offset;
}

static size_t p1w_copy_decimal(char *destination, size_t offset, size_t limit, uint64_t value) {
    char digits[P1W_PID_DIGITS];
    size_t index = P1W_PID_DIGITS;
    while (index > 0) {
        index--;
        digits[index] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    for (index = 0; index < P1W_PID_DIGITS && offset < limit; index++) {
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
static size_t p1w_read_link(const char *path, char *buffer, size_t limit) {
    long result = p1w_syscall4(
        NR_READLINKAT, AT_FDCWD, (long)(uintptr_t)path, (long)(uintptr_t)buffer, (long)limit
    );
    if (result <= 0 || (size_t)result > limit) {
        return 0;
    }
    return (size_t)result;
}

static size_t p1w_read_file(const char *path, char *buffer, size_t limit) {
    long descriptor = p1w_syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, O_RDONLY | O_CLOEXEC, 0);
    long result;
    if (descriptor < 0) {
        return 0;
    }
    result = p1w_syscall3(NR_READ, descriptor, (long)(uintptr_t)buffer, (long)limit);
    (void)p1w_syscall1(NR_CLOSE, descriptor);
    if (result <= 0 || (size_t)result > limit) {
        return 0;
    }
    return (size_t)result;
}

static size_t p1w_append_field(
    char *record,
    size_t offset,
    size_t limit,
    const char *name,
    const char *value,
    size_t value_length
) {
    offset = p1w_copy_literal(record, offset, limit, name);
    offset = p1w_copy_literal(record, offset, limit, "=");
    if (value_length == 0) {
        offset = p1w_copy_literal(record, offset, limit, P1W_UNAVAILABLE);
    } else {
        offset = p1w_copy_sanitized(record, offset, limit, value, value_length);
    }
    return p1w_copy_literal(record, offset, limit, ";");
}

static size_t p1w_build_record(char *record, size_t limit, uint64_t pid) {
    char procself[P1W_FIELD_MAX];
    char pidns[P1W_FIELD_MAX];
    char bootid[P1W_FIELD_MAX];
    size_t procself_length = p1w_read_link(P1W_PROC_SELF, procself, sizeof(procself));
    size_t pidns_length = p1w_read_link(P1W_PROC_SELF_NS_PID, pidns, sizeof(pidns));
    size_t bootid_length = p1w_read_file(P1W_BOOT_ID_PATH, bootid, sizeof(bootid));
    size_t offset = 0;

    offset = p1w_copy_literal(record, offset, limit, P1W_MAGIC ";cand=" P1W_CANDIDATE_ID ";pid=");
    offset = p1w_copy_decimal(record, offset, limit, pid);
    offset = p1w_copy_literal(record, offset, limit, ";");
    offset = p1w_append_field(record, offset, limit, "procself", procself, procself_length);
    offset = p1w_append_field(record, offset, limit, "pidns", pidns, pidns_length);
    offset = p1w_append_field(record, offset, limit, "bootid", bootid, bootid_length);
    offset = p1w_copy_literal(record, offset, limit, "stage=" P1W_STAGE "\n");
    return offset;
}

/*
 * Everything below is best effort in the strict sense. No result is inspected
 * for anything but the local bookkeeping of the next step, and no result reaches
 * the caller. `/proc` and the `/dev/kmsg` node are both removed again so the
 * ramdisk and mount table magiskinit inherits are the ones it would have
 * inherited from the kernel: magiskinit mounts /proc itself when /proc/cmdline
 * is absent, and its setup_klog() falls back to a /kmsg node when /dev/kmsg does
 * not exist. Leaving either behind would change its behaviour.
 */
static void p1w_emit_evidence_best_effort(uint64_t pid) {
    char record[P1W_RECORD_MAX];
    size_t length;
    long descriptor;
    long mounted;
    long created;

    (void)p1w_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)P1W_PROC_DIR, 0755);
    mounted = p1w_syscall5(
        NR_MOUNT,
        (long)(uintptr_t) "proc",
        (long)(uintptr_t)P1W_PROC_DIR,
        (long)(uintptr_t) "proc",
        0,
        0
    );

    length = p1w_build_record(record, sizeof(record), pid);

    (void)p1w_syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)P1W_DEV_DIR, 0755);
    created = p1w_syscall4(
        NR_MKNODAT,
        AT_FDCWD,
        (long)(uintptr_t)P1W_KMSG_PATH,
        (long)(S_IFCHR | 0600),
        (long)p1w_make_dev(P1W_KMSG_MAJOR, P1W_KMSG_MINOR)
    );
    descriptor = p1w_syscall4(NR_OPENAT, AT_FDCWD, (long)(uintptr_t)P1W_KMSG_PATH, O_WRONLY | O_CLOEXEC, 0);
    if (descriptor >= 0) {
        /* One write. /dev/kmsg is record oriented, so a short write is not
         * retried: a torn record is worse evidence than none. */
        (void)p1w_syscall3(NR_WRITE, descriptor, (long)(uintptr_t)record, (long)length);
        (void)p1w_syscall1(NR_CLOSE, descriptor);
    }
    /* Only a node this witness created is removed. An mknod that failed because
     * something already owned /dev/kmsg means the node is not ours, and
     * unlinking it would hand magiskinit a world it did not have. */
    if (created == 0) {
        (void)p1w_syscall3(NR_UNLINKAT, AT_FDCWD, (long)(uintptr_t)P1W_KMSG_PATH, 0);
    }

    /* Both unmounts can fail. If they do, magiskinit inherits a /proc this
     * witness mounted, sees /proc/cmdline, and skips mounting it itself - which
     * is a real behavioural difference and is why this is tested rather than
     * asserted. It still does not gate the handoff: a device that cannot tidy
     * up must still boot. */
    if (mounted == 0) {
        if (p1w_syscall2(NR_UMOUNT2, (long)(uintptr_t)P1W_PROC_DIR, 0) != 0) {
            (void)p1w_syscall2(NR_UMOUNT2, (long)(uintptr_t)P1W_PROC_DIR, MNT_DETACH);
        }
    }
}

/*
 * Restore the resident world and leave. The rename is atomic: on success
 * `/init` is the resident magiskinit inode and `/init.magisk` no longer exists,
 * so the exec cannot land back on this witness. On failure the exec is not
 * attempted at all.
 */
static long p1w_restore_resident_init(void) {
    return p1w_syscall4(
        NR_RENAMEAT,
        AT_FDCWD,
        (long)(uintptr_t)P1W_MAGISK_INIT_STAGED,
        AT_FDCWD,
        (long)(uintptr_t)P1W_INIT_PATH
    );
}

static void p1w_handoff(char **argv, char **envp) {
    (void)p1w_syscall3(NR_EXECVE, (long)(uintptr_t)P1W_INIT_PATH, (long)(uintptr_t)argv, (long)(uintptr_t)envp);
}

#ifdef S20PLUS_P1_WITNESS_SELFTEST_ONLY

/*
 * Host self-test. It runs under qemu-aarch64 as an ordinary process, so it must
 * exercise only the pure record machinery: the PID1 gate, the rename and the
 * exec are device behaviour and are covered by the focused host tests and by
 * the builder's disassembly checks instead.
 */
static int p1w_selftest_equal(const char *left, const char *right, size_t length) {
    size_t index;
    for (index = 0; index < length; index++) {
        if (left[index] != right[index]) {
            return 0;
        }
    }
    return 1;
}

__attribute__((noreturn)) void _start(void) {
    char record[P1W_RECORD_MAX];
    /* rodata, not a stack copy: a local initialised array would make the
     * freestanding link depend on a synthesised memcpy. */
    static const char expected_prefix[] = P1W_MAGIC ";cand=" P1W_CANDIDATE_ID ";pid=0000000001;";
    size_t prefix_length = sizeof(expected_prefix) - 1U;
    size_t offset;
    int ok = 1;

    ok = ok && p1w_make_dev(1U, 11U) == 0x10bULL;
    ok = ok && p1w_make_dev(240U, 7U) == 0xf007ULL;
    ok = ok && p1w_make_dev(0U, 0U) == 0ULL;

    /* Decimal formatting is fixed width and must not depend on the value. */
    offset = p1w_copy_decimal(record, 0, sizeof(record), 1U);
    ok = ok && offset == P1W_PID_DIGITS && p1w_selftest_equal(record, "0000000001", 10U);
    offset = p1w_copy_decimal(record, 0, sizeof(record), 4294967295U);
    ok = ok && offset == P1W_PID_DIGITS && p1w_selftest_equal(record, "4294967295", 10U);

    /* A separator or an escape in a kernel value must not survive into the
     * record, or the consumer's field split would be attacker-shaped. */
    offset = p1w_copy_sanitized(record, 0, sizeof(record), "a;b=c\\d e", 9U);
    ok = ok && offset == 9U && p1w_selftest_equal(record, "a_b_c_d_e", 9U);
    offset = p1w_copy_sanitized(record, 0, sizeof(record), "pid:[4026531836]", 16U);
    ok = ok && offset == 16U && p1w_selftest_equal(record, "pid:[4026531836]", 16U);
    /* A value stops at the first NUL or newline rather than absorbing it. */
    offset = p1w_copy_sanitized(record, 0, sizeof(record), "ab\ncd", 5U);
    ok = ok && offset == 2U;

    /* An unavailable value becomes the fixed placeholder, never an empty field. */
    offset = p1w_append_field(record, 0, sizeof(record), "pidns", record, 0U);
    ok = ok && p1w_selftest_equal(record, "pidns=" P1W_UNAVAILABLE ";", offset);

    /* Built against whatever this host's procfs answers - which are not the
     * device's - so only the structural properties are asserted: the identity
     * and PID prefix are exact, the record is bounded, and it ends in the
     * newline that makes it one /dev/kmsg record. */
    offset = p1w_build_record(record, sizeof(record), 1U);
    ok = ok && offset > prefix_length && offset < P1W_RECORD_MAX;
    ok = ok && p1w_selftest_equal(record, expected_prefix, prefix_length);
    ok = ok && record[offset - 1U] == '\n';

    /* Truncation is bounded rather than overrunning the record buffer. */
    offset = p1w_build_record(record, 16U, 1U);
    ok = ok && offset == 16U;

    (void)p1w_syscall1(NR_EXIT_GROUP, ok ? 0 : 1);
    for (;;) {
    }
}

#else

/*
 * The kernel enters PID 1 with the stack laid out as argc, argv[], NULL,
 * envp[], NULL, so `_start` hands the raw stack pointer to the body and the
 * body forwards the kernel's own argv and envp to magiskinit unchanged. Nothing
 * is reconstructed: magiskinit reads argv[0] and argv[1], and the original
 * Samsung init receives whatever the bootloader appended to either vector.
 */
__attribute__((noreturn)) void p1w_main(unsigned long *stack);

#ifndef S20PLUS_P1_WITNESS_FAULT_HARNESS
__asm__(
    ".globl _start\n"
    ".type _start, %function\n"
    "_start:\n"
    "\tmov x0, sp\n"
    "\tb p1w_main\n"
    ".size _start, .-_start\n"
);
#endif

__attribute__((noreturn)) void p1w_main(unsigned long *stack) {
    long pid = p1w_getpid();
    unsigned long argc;
    char **argv;
    char **envp;

    if (pid != 1) {
        /* Never act anywhere but as PID1. */
        p1w_park();
    }

    p1w_emit_evidence_best_effort((uint64_t)pid);

    /* No branch may separate the evidence from the handoff. */
    if (p1w_restore_resident_init() != 0) {
        /* Exec'ing /init now would re-enter this witness as PID 1 forever. */
        p1w_park();
    }

    argc = stack[0];
    argv = (char **)&stack[1];
    envp = argv + argc + 1;
    p1w_handoff(argv, envp);

    /* Only reached if the exec failed. Park so the operator's physical Download
     * entry and the mandatory resident rollback stay available. */
    p1w_park();
}

#endif
