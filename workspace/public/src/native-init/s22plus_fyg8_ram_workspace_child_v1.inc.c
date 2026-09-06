/*
 * P349 bounded RAM-workspace ash child boundary.
 *
 * This fragment is deliberately a no-input child setup.  The caller has
 * already made the process group, connected stdin/stdout/stderr and closed
 * the transport TTY.  Every operation below is fixed to this source and
 * view; an error returns before the caller can exec BusyBox ash.
 *
 * The fragment is for the native-init freestanding runtime.  It uses the
 * runtime's syscall6/sys_openat/sys_read/sys_write/sys_close/sys_mount
 * primitives and supplies only the small syscall wrappers needed here.
 * The /work tmpfs survives child actions only in this boot; no device authority.
 */

#ifndef P345_NR_CLOSE_RANGE
#define P345_NR_CLOSE_RANGE 436
#endif
#ifndef P345_NR_UNSHARE
#define P345_NR_UNSHARE 97
#endif
#ifndef P345_NR_MKDIRAT
#define P345_NR_MKDIRAT 34
#endif
#ifndef P345_NR_FCHMOD
#define P345_NR_FCHMOD 52
#endif
#ifndef P345_NR_CHROOT
#define P345_NR_CHROOT 51
#endif
#ifndef P345_NR_CHDIR
#define P345_NR_CHDIR 49
#endif
#ifndef P345_NR_GETCWD
#define P345_NR_GETCWD 17
#endif
#ifndef P345_NR_SETRLIMIT
#define P345_NR_SETRLIMIT 164
#endif
#ifndef P345_NR_SETGROUPS
#define P345_NR_SETGROUPS 159
#endif
#ifndef P345_NR_SETRESUID
#define P345_NR_SETRESUID 147
#endif
#ifndef P345_NR_SETRESGID
#define P345_NR_SETRESGID 149
#endif
#ifndef P345_NR_CAPSET
#define P345_NR_CAPSET 91
#endif
#ifndef P345_NR_PRCTL
#define P345_NR_PRCTL 167
#endif
#ifndef P345_NR_SECCOMP
#define P345_NR_SECCOMP 277
#endif
#ifndef P345_NR_OPENAT
#define P345_NR_OPENAT 56
#endif
#ifndef P345_NR_READ
#define P345_NR_READ 63
#endif
#ifndef P345_NR_WRITE
#define P345_NR_WRITE 64
#endif
#ifndef P345_NR_CLOSE
#define P345_NR_CLOSE 57
#endif
#ifndef P345_NR_FSTAT
#define P345_NR_FSTAT 80
#endif
#ifndef P345_NR_NEWFSTATAT
#define P345_NR_NEWFSTATAT 79
#endif
#ifndef P345_NR_LSEEK
#define P345_NR_LSEEK 62
#endif
#ifndef P345_NR_MMAP
#define P345_NR_MMAP 222
#endif
#ifndef P345_NR_MUNMAP
#define P345_NR_MUNMAP 215
#endif
#ifndef P345_NR_MPROTECT
#define P345_NR_MPROTECT 226
#endif
#ifndef P345_NR_MREMAP
#define P345_NR_MREMAP 216
#endif
#ifndef P345_NR_BRK
#define P345_NR_BRK 214
#endif
#ifndef P345_NR_RT_SIGACTION
#define P345_NR_RT_SIGACTION 134
#endif
#ifndef P345_NR_RT_SIGPROCMASK
#define P345_NR_RT_SIGPROCMASK 135
#endif
#ifndef P345_NR_RT_SIGRETURN
#define P345_NR_RT_SIGRETURN 139
#endif
#ifndef P345_NR_SIGALTSTACK
#define P345_NR_SIGALTSTACK 132
#endif
#ifndef P345_NR_EXIT
#define P345_NR_EXIT 93
#endif
#ifndef P345_NR_EXIT_GROUP
#define P345_NR_EXIT_GROUP 94
#endif
#ifndef P345_NR_EXECVE
#define P345_NR_EXECVE 221
#endif
#ifndef P345_NR_CLONE
#define P345_NR_CLONE 220
#endif
#ifndef P345_NR_WAIT4
#define P345_NR_WAIT4 260
#endif
#ifndef P345_NR_PIPE2
#define P345_NR_PIPE2 59
#endif
#ifndef P345_NR_DUP
#define P345_NR_DUP 23
#endif
#ifndef P345_NR_DUP3
#define P345_NR_DUP3 24
#endif
#ifndef P345_NR_FCNTL
#define P345_NR_FCNTL 25
#endif
#ifndef P345_NR_GETPID
#define P345_NR_GETPID 172
#endif
#ifndef P345_NR_GETPPID
#define P345_NR_GETPPID 173
#endif
#ifndef P345_NR_GETUID
#define P345_NR_GETUID 174
#endif
#ifndef P345_NR_GETEUID
#define P345_NR_GETEUID 175
#endif
#ifndef P345_NR_GETGID
#define P345_NR_GETGID 176
#endif
#ifndef P345_NR_GETEGID
#define P345_NR_GETEGID 177
#endif
#ifndef P345_NR_GETTID
#define P345_NR_GETTID 178
#endif
#ifndef P345_NR_SET_TID_ADDRESS
#define P345_NR_SET_TID_ADDRESS 96
#endif
#ifndef P345_NR_SET_ROBUST_LIST
#define P345_NR_SET_ROBUST_LIST 99
#endif
#ifndef P345_NR_FUTEX
#define P345_NR_FUTEX 98
#endif
#ifndef P345_NR_CLOCK_GETTIME
#define P345_NR_CLOCK_GETTIME 113
#endif
#ifndef P345_NR_CLOCK_NANOSLEEP
#define P345_NR_CLOCK_NANOSLEEP 115
#endif
#ifndef P345_NR_NANOSLEEP
#define P345_NR_NANOSLEEP 101
#endif
#ifndef P345_NR_UNAME
#define P345_NR_UNAME 160
#endif
#ifndef P345_NR_GETRANDOM
#define P345_NR_GETRANDOM 278
#endif
#ifndef P345_NR_STATX
#define P345_NR_STATX 291
#endif
#ifndef P345_NR_READLINKAT
#define P345_NR_READLINKAT 78
#endif
#ifndef P345_NR_GETDENTS64
#define P345_NR_GETDENTS64 61
#endif
#ifndef P345_NR_FACCESSAT
#define P345_NR_FACCESSAT 48
#endif
#ifndef P345_NR_MADVISE
#define P345_NR_MADVISE 233
#endif
#ifndef P345_NR_RSEQ
#define P345_NR_RSEQ 293
#endif
#ifndef P345_NR_SCHED_YIELD
#define P345_NR_SCHED_YIELD 124
#endif
#ifndef P345_NR_PPOLL
#define P345_NR_PPOLL 73
#endif

/* x86-64's static BusyBox uses these ABI-specific setup calls.  They are
 * enabled only by the host smoke fixture; ARM64 has no arch_prctl and uses
 * dup3 for the corresponding descriptor operation.  They never widen the
 * target filter. */
#ifdef P345_HOST_TEST_EXTRA_SYSCALLS
#ifndef P345_NR_ARCH_PRCTL
#define P345_NR_ARCH_PRCTL 158
#endif
#ifndef P345_NR_DUP2
#define P345_NR_DUP2 33
#endif
#endif

#ifndef P345_AUDIT_ARCH
#define P345_AUDIT_ARCH 0xc00000b7U
#endif

#ifndef P345_AT_FDCWD
#define P345_AT_FDCWD (-100)
#endif
#ifndef P345_CLONE_NEWNS
#define P345_CLONE_NEWNS 0x00020000UL
#endif
#ifndef P345_CLONE_NEW_MASK
#define P345_CLONE_NEW_MASK 0x7e020080UL
#endif
#ifndef P345_O_RDONLY
#define P345_O_RDONLY 00000000
#endif
#ifndef P345_O_WRONLY
#define P345_O_WRONLY 00000001
#endif
#ifndef P345_O_RDWR
#define P345_O_RDWR 00000002
#endif
#ifndef P345_O_CREAT
#define P345_O_CREAT 00000100
#endif
#ifndef P345_O_EXCL
#define P345_O_EXCL 00000200
#endif
#ifndef P345_O_TRUNC
#define P345_O_TRUNC 00001000
#endif
#ifndef P345_O_APPEND
#define P345_O_APPEND 00002000
#endif
#ifndef P345_O_CLOEXEC
#define P345_O_CLOEXEC 02000000
#endif
#ifndef P345_O_TMPFILE
#define P345_O_TMPFILE 020000000
#endif

#ifndef P345_MS_RDONLY
#define P345_MS_RDONLY 1UL
#endif
#ifndef P345_MS_NOSUID
#define P345_MS_NOSUID 2UL
#endif
#ifndef P345_MS_NODEV
#define P345_MS_NODEV 4UL
#endif
#ifndef P345_MS_BIND
#define P345_MS_BIND 4096UL
#endif
#ifndef P345_MS_REC
#define P345_MS_REC 16384UL
#endif
#ifndef P345_MS_PRIVATE
#define P345_MS_PRIVATE (1UL << 18)
#endif
#ifndef P345_MS_REMOUNT
#define P345_MS_REMOUNT 32UL
#endif

#ifndef P345_EINTR
#define P345_EINTR 4
#endif
#ifndef P345_EIO
#define P345_EIO 5
#endif
#ifndef P345_EOVERFLOW
#define P345_EOVERFLOW 75
#endif
#ifndef P345_EPERM
#define P345_EPERM 1
#endif

#define P345_ROOT_TMPFS "/dev"
#define P345_ROOT_VIEW "/dev/p349-root"
#define P345_BUSYBOX_SOURCE "/bin/busybox"
#define P345_BUSYBOX_VIEW "/dev/p349-root/bin/busybox"
#define P345_TMPFS_DATA "size=1048576,mode=0755"
#define P349_WORK_SOURCE "/p349-work"
#define P349_WORK_VIEW P345_ROOT_VIEW "/work"
#define P349_WORK_DATA "size=8388608,nr_inodes=256,mode=0700,uid=65534,gid=65534"
#ifndef P349_NR_UNLINKAT
#define P349_NR_UNLINKAT 35
#endif
#ifndef P349_NR_RENAMEAT
#define P349_NR_RENAMEAT 38
#endif
#define P345_TEXT_MODE 0444U
#define P345_BUSYBOX_MODE 0555U
#define P345_COPY_CHUNK 1024U
#define P345_ROOT_UID 65534U
#define P345_ROOT_GID 65534U

#define P345_MEMINFO_MAX 16384U
#define P345_CPUINFO_MAX 16384U
#define P345_UPTIME_MAX 128U
#define P345_VERSION_MAX 1024U
#define P345_MOUNTS_MAX 32768U
#define P345_UDC_STATE_MAX 128U

#define P345_RLIMIT_CPU 0U
#define P345_RLIMIT_FSIZE 1U
#define P345_RLIMIT_NPROC 6U
#define P345_RLIMIT_NOFILE 7U
#define P345_RLIMIT_AS 9U
#define P345_CPU_SECONDS 15ULL
#define P345_FSIZE_BYTES 65536ULL
#define P345_MAX_PROCESSES 16ULL
#define P345_MAX_FDS 32ULL
#define P345_MAX_ADDRESS_SPACE (64ULL * 1024ULL * 1024ULL)

#define P345_PR_SET_KEEPCAPS 8L
#define P345_PR_SET_DUMPABLE 4L
#define P345_PR_SET_NO_NEW_PRIVS 38L
#define P345_SECCOMP_SET_MODE_FILTER 1L
#define P345_LINUX_CAPABILITY_VERSION_3 0x20080522U

#define P345_SECCOMP_RET_KILL_PROCESS 0x80000000U
#define P345_SECCOMP_RET_ALLOW 0x7fff0000U
#define P345_SECCOMP_RET_ERRNO 0x00050000U

#define P345_BPF_LD_W_ABS 0x20U
#define P345_BPF_JMP_JEQ_K 0x15U
#define P345_BPF_JMP_JSET_K 0x45U
#define P345_BPF_RET_K 0x06U
#define P345_SECCOMP_ARCH_OFFSET 4U
#define P345_SECCOMP_NR_OFFSET 0U
#define P345_SECCOMP_ARG0_OFFSET 16U
#define P345_SECCOMP_ARG1_OFFSET 24U
#define P345_SECCOMP_ARG2_OFFSET 32U

struct p345_rlimit {
    uint64_t current;
    uint64_t maximum;
};

struct p345_cap_header {
    uint32_t version;
    int32_t pid;
};

struct p345_cap_data {
    uint32_t effective;
    uint32_t permitted;
    uint32_t inheritable;
};

struct p345_sock_filter {
    uint16_t code;
    uint8_t jump_true;
    uint8_t jump_false;
    uint32_t constant;
};

struct p345_sock_fprog {
    uint16_t length;
    uint16_t padding;
    struct p345_sock_filter *filter;
};

static long p345_call(
    long nr,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5) {
    return syscall6(nr, a0, a1, a2, a3, a4, a5);
}

static long p345_mkdir(const char *path, unsigned int mode) {
    return p345_call(
        P345_NR_MKDIRAT,
        P345_AT_FDCWD,
        (long)(uintptr_t)path,
        (long)mode,
        0,
        0,
        0);
}

static long p345_fchmod(int fd, unsigned int mode) {
    return p345_call(P345_NR_FCHMOD, fd, (long)mode, 0, 0, 0, 0);
}

static long p345_chroot(const char *path) {
    return p345_call(P345_NR_CHROOT, (long)(uintptr_t)path, 0, 0, 0, 0, 0);
}

static long p345_chdir(const char *path) {
    return p345_call(P345_NR_CHDIR, (long)(uintptr_t)path, 0, 0, 0, 0, 0);
}

static long p345_setrlimit(unsigned int resource, uint64_t value) {
    struct p345_rlimit limit = {value, value};
    return p345_call(
        P345_NR_SETRLIMIT,
        (long)resource,
        (long)(uintptr_t)&limit,
        0,
        0,
        0,
        0);
}

static long p345_prctl(
    long option, long argument, long argument2, long argument3, long argument4) {
    return p345_call(
        P345_NR_PRCTL, option, argument, argument2, argument3, argument4, 0);
}

static long p345_close_extra_fds(void) {
    /* close_range is required; silently falling back to an unbounded loop is
     * not acceptable for a child that must fail closed. */
    return p345_call(
        P345_NR_CLOSE_RANGE,
        3,
        0xffffffffL,
        0,
        0,
        0,
        0);
}

static long p345_write_exact(int fd, const uint8_t *data, size_t size) {
    size_t written = 0U;
    while (written < size) {
        long amount = sys_write(fd, data + written, size - written);
        if (amount == -P345_EINTR) {
            continue;
        }
        if (amount <= 0 || (size_t)amount > size - written) {
            return amount < 0 ? amount : -P345_EIO;
        }
        written += (size_t)amount;
    }
    return 0;
}

static long p345_copy_text(
    const char *source, const char *destination, size_t capacity) {
    uint8_t buffer[P345_COPY_CHUNK];
    long input = sys_openat(source, P345_O_RDONLY | P345_O_CLOEXEC, 0);
    if (input < 0) {
        return input;
    }
    long output = sys_openat(
        destination,
        P345_O_WRONLY | P345_O_CREAT | P345_O_EXCL | P345_O_CLOEXEC,
        P345_TEXT_MODE);
    if (output < 0) {
        (void)sys_close((int)input);
        return output;
    }
    size_t used = 0U;
    long result = 0;
    for (;;) {
        if (used == capacity) {
            long extra;
            do {
                extra = sys_read((int)input, buffer, 1U);
            } while (extra == -P345_EINTR);
            result = extra == 0 ? 0 :
                (extra < 0 ? extra : -P345_EOVERFLOW);
            break;
        }
        size_t request = capacity - used;
        if (request > sizeof(buffer)) {
            request = sizeof(buffer);
        }
        long amount;
        do {
            amount = sys_read((int)input, buffer, request);
        } while (amount == -P345_EINTR);
        if (amount == 0) {
            result = 0;
            break;
        }
        if (amount < 0 || (size_t)amount > request) {
            result = amount < 0 ? amount : -P345_EIO;
            break;
        }
        result = p345_write_exact((int)output, buffer, (size_t)amount);
        if (result != 0) {
            break;
        }
        used += (size_t)amount;
    }
    long mode_result = result == 0 ? p345_fchmod((int)output, P345_TEXT_MODE) : 0;
    long close_output = sys_close((int)output);
    long close_input = sys_close((int)input);
    if (result != 0) {
        return result;
    }
    if (mode_result != 0) {
        return mode_result;
    }
    return close_output != 0 ? close_output : close_input;
}

static long p345_create_busybox_placeholder(void) {
    long fd = sys_openat(
        P345_BUSYBOX_VIEW,
        P345_O_WRONLY | P345_O_CREAT | P345_O_EXCL | P345_O_CLOEXEC,
        P345_BUSYBOX_MODE);
    if (fd < 0) {
        return fd;
    }
    return sys_close((int)fd);
}

/* Parent-only, once before the first authenticated listener.  No caller
 * pathname or workspace contents are ever consumed by the parent.  A setup
 * failure never reaches the listener; a consumed candidate is not retried. */
static long p349_prepare_workspace(void) {
    long result = p345_mkdir(P349_WORK_SOURCE, 0700U);
    if (result != 0) return result;
    return sys_mount("tmpfs", P349_WORK_SOURCE, "tmpfs",
                     P345_MS_NOSUID | P345_MS_NODEV, P349_WORK_DATA);
}

static long p345_setup_view(void) {
    long result = p345_mkdir(P345_ROOT_VIEW, 0755U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/bin", 0755U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/proc", 0555U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/sys", 0555U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/sys/class", 0555U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/sys/class/udc", 0555U);
    if (result != 0) {
        return result;
    }
    result = p345_mkdir(P345_ROOT_VIEW "/sys/class/udc/a600000.dwc3", 0555U);
    if (result != 0) {
        return result;
    }
    result = p345_create_busybox_placeholder();
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/proc/meminfo", P345_ROOT_VIEW "/proc/meminfo", P345_MEMINFO_MAX);
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/proc/cpuinfo", P345_ROOT_VIEW "/proc/cpuinfo", P345_CPUINFO_MAX);
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/proc/uptime", P345_ROOT_VIEW "/proc/uptime", P345_UPTIME_MAX);
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/proc/version", P345_ROOT_VIEW "/proc/version", P345_VERSION_MAX);
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/proc/mounts", P345_ROOT_VIEW "/proc/mounts", P345_MOUNTS_MAX);
    if (result != 0) {
        return result;
    }
    result = p345_copy_text(
        "/sys/class/udc/a600000.dwc3/state",
        P345_ROOT_VIEW "/sys/class/udc/a600000.dwc3/state",
        P345_UDC_STATE_MAX);
    if (result != 0) {
        return result;
    }
    result = sys_mount(
        P345_BUSYBOX_SOURCE,
        P345_BUSYBOX_VIEW,
        NULL,
        P345_MS_BIND,
        NULL);
    if (result != 0) {
        return result;
    }
    result = sys_mount(
        NULL,
        P345_BUSYBOX_VIEW,
        NULL,
        P345_MS_BIND | P345_MS_REMOUNT | P345_MS_RDONLY |
            P345_MS_NOSUID | P345_MS_NODEV,
        NULL);
    if (result != 0) {
        return result;
    }
    /* Reuse only the fixed current-boot RAM filesystem.  The containing
     * view becomes read-only below; this separately remounted bind stays RW. */
    result = p345_mkdir(P349_WORK_VIEW, 0700U);
    if (result != 0) return result;
    result = sys_mount(P349_WORK_SOURCE, P349_WORK_VIEW, NULL,
                       P345_MS_BIND, NULL);
    if (result != 0) return result;
    result = sys_mount(NULL, P349_WORK_VIEW, NULL,
                       P345_MS_BIND | P345_MS_REMOUNT |
                       P345_MS_NOSUID | P345_MS_NODEV, NULL);
    if (result != 0) return result;
    /* The fixed BusyBox and snapshot layer remains immutable. */
    return sys_mount(
        NULL,
        P345_ROOT_TMPFS,
        NULL,
        P345_MS_REMOUNT | P345_MS_RDONLY | P345_MS_NOSUID | P345_MS_NODEV,
        NULL);
}

static long p345_drop_privileges(void) {
    long result = p345_prctl(P345_PR_SET_KEEPCAPS, 1, 0, 0, 0);
    if (result != 0) {
        return result;
    }
    result = p345_call(P345_NR_SETGROUPS, 0, 0, 0, 0, 0, 0);
    if (result != 0) {
        return result;
    }
    result = p345_call(
        P345_NR_SETRESGID,
        P345_ROOT_GID,
        P345_ROOT_GID,
        P345_ROOT_GID,
        0,
        0,
        0);
    if (result != 0) {
        return result;
    }
    result = p345_call(
        P345_NR_SETRESUID,
        P345_ROOT_UID,
        P345_ROOT_UID,
        P345_ROOT_UID,
        0,
        0,
        0);
    if (result != 0) {
        return result;
    }
    struct p345_cap_header header = {
        P345_LINUX_CAPABILITY_VERSION_3,
        0,
    };
    struct p345_cap_data data[2] = {{0, 0, 0}, {0, 0, 0}};
    result = p345_call(
        P345_NR_CAPSET,
        (long)(uintptr_t)&header,
        (long)(uintptr_t)data,
        0,
        0,
        0,
        0);
    if (result != 0) {
        return result;
    }
    result = p345_prctl(P345_PR_SET_KEEPCAPS, 0, 0, 0, 0);
    if (result != 0) {
        return result;
    }
    return p345_prctl(P345_PR_SET_DUMPABLE, 0, 0, 0, 0);
}

static long p345_apply_limits(void) {
    long result = p345_setrlimit(P345_RLIMIT_CPU, P345_CPU_SECONDS);
    if (result != 0) {
        return result;
    }
    result = p345_setrlimit(P345_RLIMIT_FSIZE, P345_FSIZE_BYTES);
    if (result != 0) {
        return result;
    }
    result = p345_setrlimit(P345_RLIMIT_NPROC, P345_MAX_PROCESSES);
    if (result != 0) {
        return result;
    }
    result = p345_setrlimit(P345_RLIMIT_NOFILE, P345_MAX_FDS);
    if (result != 0) {
        return result;
    }
    return p345_setrlimit(P345_RLIMIT_AS, P345_MAX_ADDRESS_SPACE);
}

#define P345_BPF_ALLOW_SYSCALL(number) \
    {P345_BPF_JMP_JEQ_K, 0, 1, (number)}, \
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_ALLOW}

static struct p345_sock_filter p345_filter[] = {
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_ARCH_OFFSET},
    {P345_BPF_JMP_JEQ_K, 1, 0, P345_AUDIT_ARCH},
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_KILL_PROCESS},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_NR_OFFSET},
    /* BusyBox libc uses relative CLOCK_REALTIME clock_nanosleep. */
    {P345_BPF_JMP_JEQ_K, 0, 6, P345_NR_CLOCK_NANOSLEEP},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_ARG0_OFFSET},
    {P345_BPF_JMP_JEQ_K, 0, 3, 0U},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_ARG1_OFFSET},
    {P345_BPF_JMP_JEQ_K, 0, 1, 0U},
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_ALLOW},
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_ERRNO | P345_EPERM},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_NR_OFFSET},
    /* Path writes are constrained by chroot, read-only surrounding mounts,
     * no outside descriptors, zero capabilities and the fixed RAM bind. */
    P345_BPF_ALLOW_SYSCALL(P345_NR_OPENAT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MKDIRAT),
    P345_BPF_ALLOW_SYSCALL(P349_NR_UNLINKAT),
    P345_BPF_ALLOW_SYSCALL(P349_NR_RENAMEAT),
    /* Pipelines may fork, but descendants may not create/enter namespaces. */
    {P345_BPF_JMP_JEQ_K, 0, 3, P345_NR_CLONE},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_ARG0_OFFSET},
    {P345_BPF_JMP_JSET_K, 1, 0, P345_CLONE_NEW_MASK},
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_ALLOW},
    {P345_BPF_LD_W_ABS, 0, 0, P345_SECCOMP_NR_OFFSET},
    P345_BPF_ALLOW_SYSCALL(P345_NR_READ),
    P345_BPF_ALLOW_SYSCALL(P345_NR_WRITE),
    P345_BPF_ALLOW_SYSCALL(P345_NR_CLOSE),
    P345_BPF_ALLOW_SYSCALL(P345_NR_FSTAT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_NEWFSTATAT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_LSEEK),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MMAP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MUNMAP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MPROTECT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MREMAP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_BRK),
    P345_BPF_ALLOW_SYSCALL(P345_NR_RT_SIGACTION),
    P345_BPF_ALLOW_SYSCALL(P345_NR_RT_SIGPROCMASK),
    P345_BPF_ALLOW_SYSCALL(P345_NR_RT_SIGRETURN),
    P345_BPF_ALLOW_SYSCALL(P345_NR_SIGALTSTACK),
    P345_BPF_ALLOW_SYSCALL(P345_NR_EXIT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_EXIT_GROUP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_EXECVE),
    P345_BPF_ALLOW_SYSCALL(P345_NR_WAIT4),
    P345_BPF_ALLOW_SYSCALL(P345_NR_PIPE2),
    P345_BPF_ALLOW_SYSCALL(P345_NR_DUP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_DUP3),
#ifdef P345_HOST_TEST_EXTRA_SYSCALLS
    P345_BPF_ALLOW_SYSCALL(P345_NR_ARCH_PRCTL),
    P345_BPF_ALLOW_SYSCALL(P345_NR_DUP2),
    /* x86-64 BusyBox uses legacy path syscalls for these same operations. */
    P345_BPF_ALLOW_SYSCALL(P349_NR_HOST_MKDIR),
    P345_BPF_ALLOW_SYSCALL(P349_NR_HOST_UNLINK),
    P345_BPF_ALLOW_SYSCALL(P349_NR_HOST_RENAME),
#endif
    P345_BPF_ALLOW_SYSCALL(P345_NR_FCNTL),
    P345_BPF_ALLOW_SYSCALL(P345_NR_CHDIR),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETCWD),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETPID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETPPID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETUID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETEUID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETGID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETEGID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETTID),
    P345_BPF_ALLOW_SYSCALL(P345_NR_SET_TID_ADDRESS),
    P345_BPF_ALLOW_SYSCALL(P345_NR_SET_ROBUST_LIST),
    P345_BPF_ALLOW_SYSCALL(P345_NR_FUTEX),
    P345_BPF_ALLOW_SYSCALL(P345_NR_CLOCK_GETTIME),
    P345_BPF_ALLOW_SYSCALL(P345_NR_NANOSLEEP),
    P345_BPF_ALLOW_SYSCALL(P345_NR_UNAME),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETRANDOM),
    P345_BPF_ALLOW_SYSCALL(P345_NR_STATX),
    P345_BPF_ALLOW_SYSCALL(P345_NR_READLINKAT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_GETDENTS64),
    P345_BPF_ALLOW_SYSCALL(P345_NR_FACCESSAT),
    P345_BPF_ALLOW_SYSCALL(P345_NR_MADVISE),
    P345_BPF_ALLOW_SYSCALL(P345_NR_RSEQ),
    P345_BPF_ALLOW_SYSCALL(P345_NR_SCHED_YIELD),
    P345_BPF_ALLOW_SYSCALL(P345_NR_PPOLL),
    {P345_BPF_RET_K, 0, 0, P345_SECCOMP_RET_ERRNO | P345_EPERM},
};

static long p345_install_filter(void) {
    struct p345_sock_fprog program = {
        (uint16_t)(sizeof(p345_filter) / sizeof(p345_filter[0])),
        0,
        p345_filter,
    };
    return p345_call(
        P345_NR_SECCOMP,
        P345_SECCOMP_SET_MODE_FILTER,
        0,
        (long)(uintptr_t)&program,
        0,
        0,
        0);
}

/* Fixed no-input API.  Call only after setsid/stdio setup and tty close. */
static long p345_enter_readonly_child(void) {
    long result = p345_call(
        P345_NR_UNSHARE, (long)P345_CLONE_NEWNS, 0, 0, 0, 0, 0);
    if (result != 0) {
        return result;
    }
    result = sys_mount(
        NULL,
        "/",
        NULL,
        P345_MS_REC | P345_MS_PRIVATE,
        NULL);
    if (result != 0) {
        return result;
    }
    result = sys_mount(
        "tmpfs",
        P345_ROOT_TMPFS,
        "tmpfs",
        P345_MS_NOSUID | P345_MS_NODEV,
        P345_TMPFS_DATA);
    if (result != 0) {
        return result;
    }
    result = p345_setup_view();
    if (result != 0) {
        return result;
    }
    result = p345_chroot(P345_ROOT_VIEW);
    if (result != 0) {
        return result;
    }
    result = p345_chdir("/");
    if (result != 0) {
        return result;
    }
    result = p345_apply_limits();
    if (result != 0) {
        return result;
    }
    result = p345_close_extra_fds();
    if (result != 0) {
        return result;
    }
    result = p345_drop_privileges();
    if (result != 0) {
        return result;
    }
    result = p345_prctl(P345_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
    if (result != 0) {
        return result;
    }
    return p345_install_filter();
}

#undef P345_BPF_ALLOW_SYSCALL
