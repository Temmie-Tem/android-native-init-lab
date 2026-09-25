/* Included after the fixed target bindings. A diagnostic-only variant of the
 * existing preparation order, with no writable mount or root transition. */
#include <grp.h>
#include <linux/capability.h>
#include <linux/fs.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/statfs.h>
#include "preflight-plan.h"

_Static_assert(BLKROSET == 0x125d && BLKROGET == 0x125e, "ARM64 partition RO ABI");
_Static_assert(SYS_close_range == 436, "ARM64 descriptor-close ABI");

static struct bp_record bp;
static struct fs1_endpoint bp_endpoint;
static unsigned char bp_initial_super[1024];
static unsigned bp_mounts, bp_unmount_failed, bp_in_cleanup, bp_children_active;
static uint64_t bp_started;
static int bp_proof_fd = -1;
static unsigned char bp_log[BP_LOG_MAX];
static size_t bp_log_size;
static int bp_ro(struct fs1_endpoint *, int);

static uint64_t bp_now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
}
static void bp_park(void) { for (;;) pause(); }
static unsigned bp_mount_bit(const char *path) {
    const char *const names[] = {"/proc", "/sys", "/dev", "/dev/pts", "/run", "/newroot"};
    for (unsigned i = 0; i < 6; ++i) if (!strcmp(path, names[i])) return 1U << i;
    return 0;
}
static void bp_stage(unsigned stage) {
    bp.stage = stage;
    errno = 0;
}
static void bp_module_done(unsigned ordinal) { bp.modules_completed = ordinal; }
static void bp_before_mount(const char *path) {
    if (strcmp(path, "/newroot")) return;
    if (!bp.partition_ro || bp_ro(&bp_endpoint, 0)) stop("root-mount-block-ro");
}
static void bp_mount_done(const char *path) {
    unsigned bit = bp_mount_bit(path);
    if (!bit || (bp_mounts & bit)) { bp.cleanup_error = EPROTO; bp_park(); }
    bp_mounts |= bit;
    if (bit == 32U) {
        ++bp.root_mounts;
        if (!bp.partition_ro || bp.root_mounts > 2) { bp.cleanup_error = EPROTO; bp_park(); }
        struct stat st;
        struct statfs fs;
        struct statvfs vfs;
        unsigned long wanted = ST_RDONLY | ST_NOSUID | ST_NODEV;
        if (bp.root_mounts == 1) wanted |= ST_NOEXEC;
        if (stat(path, &st) || st.st_dev != bp_endpoint.partition || !S_ISDIR(st.st_mode) ||
            statfs(path, &fs) || fs.f_type != 0xef53 || statvfs(path, &vfs) ||
            (vfs.f_flag & (ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC)) != wanted)
            stop("root-mount-protection");
    }
}
static int bp_umount(const char *path) {
    unsigned bit = bp_mount_bit(path);
    if (!bit || !(bp_mounts & bit) || (bp_unmount_failed & bit)) { errno = EPROTO; return -1; }
    int rc = umount(path);
    if (rc) bp_unmount_failed |= bit;
    else bp_mounts &= ~bit;
    return rc;
}
static int bp_ro(struct fs1_endpoint *e, int set) {
    int fd = open(fs1_node, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    struct stat st;
    int one = 1, actual = 0, error = 0;
    if (fd < 0) return fs1_error();
    if (fstat(fd, &st) || !S_ISBLK(st.st_mode) || st.st_rdev != e->partition) error = EPROTO;
    if (!error && set && ioctl(fd, BLKROSET, &one)) error = fs1_error();
    if (!error && (ioctl(fd, BLKROGET, &actual) || actual != 1)) error = EPROTO;
    uint64_t sysfs_ro = 0;
    if (!error) error = fs1_number(e->sys_partition, "ro", &sysfs_ro);
    if (!error && sysfs_ro != 1) error = EPROTO;
    if (close(fd) && !error) error = fs1_error();
    return error;
}
static void bp_protect(struct fs1_endpoint *e) {
    bp_stage(BP_BLOCK_RO);
    bp_endpoint = *e;
    memcpy(bp_initial_super, e->superblock, sizeof(bp_initial_super));
    int error = bp_ro(e, 1);
    if (error) { errno = error; stop("partition-ro"); }
    bp.partition_ro = 1;
}
static void bp_begin(void) {
    memset(&bp, 0, sizeof(bp));
    bp.magic = BP_MAGIC; bp.version = BP_VERSION; bp.header_size = sizeof(bp);
    memcpy(bp.run_id, bp_run_id, 16);
#ifdef S22_DEBIAN_VIRT_TEST
    bp.virtual_board = 1;
#endif
    bp_started = bp_now();
    if (!bp_started) bp_park();
    bp_stage(BP_ENTER);
}
static void bp_boot_identity(void) {
    int fd = open("/proc/sys/kernel/random/boot_id", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    char tail;
    if (fd < 0 || read(fd, bp.boot_id, 37) != 37 || read(fd, &tail, 1) || close(fd))
        stop("boot-identity");
    bp_stage(BP_BASE_MOUNTS);
}
static void bp_log_bytes(const unsigned char *bytes, size_t size) {
    if (size > BP_LOG_MAX - bp_log_size) { bp.output_exceeded = 1; return; }
    memcpy(bp_log + bp_log_size, bytes, size); bp_log_size += size;
}
static void bp_child_fail(int error) {
    unsigned value = error ? (unsigned)error : EPROTO;
    (void)write(3, &value, sizeof(value));
    _exit(126);
}
/* kind: 0 path exec, 1 held ELF exec, 2 fixed metadata callback. */
static void bp_run_child(unsigned kind, char *const argv[], const char *cwd,
                         int jailed, int executable, int input, int unprivileged) {
    int pipes[3][2];
    for (unsigned i = 0; i < 3; ++i) if (pipe2(pipes[i], O_CLOEXEC)) stop("child-pipe");
    uint64_t began = bp_now();
    if (!began || began - bp_started > BP_TOTAL_MS) { bp.timed_out = 1; stop("child-total-time"); }
    pid_t pid = fork();
    if (pid < 0) stop("child-fork");
    if (!pid) {
        if (setpgid(0, 0) || prctl(PR_SET_PDEATHSIG, SIGKILL) || getppid() != 1) _exit(125);
        int held = executable >= 0 ? fcntl(executable, F_DUPFD_CLOEXEC, 16) : -1;
        int report = fcntl(pipes[2][1], F_DUPFD_CLOEXEC, 16);
        int empty = open("/dev/null", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
        if ((executable >= 0 && held < 0) || report < 0 || empty < 0 ||
            dup2(input >= 0 ? input : empty, 0) != 0 ||
            dup2(pipes[0][1], 1) != 1 || dup2(pipes[1][1], 2) != 2 ||
            dup3(report, 3, O_CLOEXEC) != 3) _exit(125);
        if (held >= 0 && dup3(held, 4, O_CLOEXEC) != 4) bp_child_fail(errno);
        if (syscall(SYS_close_range, held >= 0 ? 5U : 4U, ~0U, 0)) bp_child_fail(errno);
        if (cwd && chdir(cwd)) bp_child_fail(errno);
        if (jailed && (chroot(".") || chdir("/"))) bp_child_fail(errno);
        if (unprivileged) {
            struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
            struct __user_cap_data_struct caps[2] = {{0}};
            if (prctl(PR_SET_KEEPCAPS, 0, 0, 0, 0) || setgroups(0, NULL) || setresgid(65534, 65534, 65534) ||
                setresuid(65534, 65534, 65534) || syscall(SYS_capset, &header, caps) ||
                prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) bp_child_fail(errno);
            uid_t ru, eu, su; gid_t rg, eg, sg;
            if (getresuid(&ru,&eu,&su) || getresgid(&rg,&eg,&sg) ||
                ru!=65534 || eu!=65534 || su!=65534 || rg!=65534 || eg!=65534 || sg!=65534 ||
                getgroups(0,NULL) || syscall(SYS_capget,&header,caps) ||
                caps[0].effective || caps[0].permitted || caps[0].inheritable ||
                caps[1].effective || caps[1].permitted || caps[1].inheritable ||
                prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1) bp_child_fail(EPERM);
        }
        struct rlimit limit = {0, 0};
        if (setrlimit(RLIMIT_CORE, &limit)) bp_child_fail(errno);
        unsigned ready = 0;
        if (write(3, &ready, sizeof(ready)) != sizeof(ready)) _exit(125);
        if (kind == 2) _exit(metadata_inside(4));
        char *const env[] = {"PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL=C", NULL};
        if (kind == 1) fexecve(4, argv, env);
        else execve(argv[0], argv, env);
        bp_child_fail(errno);
    }
    ++bp.children_started; bp_children_active = 1;
    if (setpgid(pid, pid) && errno != EACCES && errno != ESRCH) stop("child-group");
    struct pollfd fds[3];
    for (unsigned i = 0; i < 3; ++i) {
        if (close(pipes[i][1]) || fcntl(pipes[i][0], F_SETFL, O_NONBLOCK)) stop("child-parent-pipe");
        fds[i] = (struct pollfd){pipes[i][0], POLLIN, 0};
    }
    unsigned char exec_bytes[8]; size_t exec_used = 0;
    int status = 0, reaped = 0, kill_sent = 0;
    while (!reaped || fds[0].fd >= 0 || fds[1].fd >= 0 || fds[2].fd >= 0) {
        uint64_t now = bp_now();
        if (!now || now - began >= BP_TIMEOUT_MS || now - bp_started >= BP_TOTAL_MS || bp.output_exceeded) {
            bp.timed_out |= !bp.output_exceeded;
            if (!kill_sent) { (void)kill(-pid, SIGKILL); kill_sent = 1; }
            if (!now || now - began >= BP_TIMEOUT_MS + 2000U) bp_park();
        }
        if (poll(fds, 3, 10) < 0 && errno != EINTR) stop("child-poll");
        for (unsigned i = 0; i < 3; ++i) if (fds[i].fd >= 0) {
            unsigned char bytes[4096]; ssize_t n = read(fds[i].fd, bytes, sizeof(bytes));
            if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue;
            if (n < 0) stop("child-read");
            if (!n) { if (close(fds[i].fd)) stop("child-close"); fds[i].fd = -1; continue; }
            if (i < 2) bp_log_bytes(bytes, (size_t)n);
            else if ((size_t)n > sizeof(exec_bytes) - exec_used) { bp.child_error = EPROTO; stop("child-exec-frame"); }
            else { memcpy(exec_bytes + exec_used, bytes, (size_t)n); exec_used += (size_t)n; }
        }
        if (!reaped) {
            pid_t got = waitpid(pid, &status, WNOHANG);
            if (got < 0 && errno != EINTR) stop("child-wait");
            if (got == pid) { reaped = 1; ++bp.children_reaped; }
        }
    }
    bp.child_status = (unsigned)status;
    unsigned ready = ~0U, error = 0;
    if (exec_used >= 4) memcpy(&ready, exec_bytes, 4);
    if (exec_used == 8) memcpy(&error, exec_bytes + 4, 4);
    if (ready || exec_used != 4 || error) bp.child_error = error ? error : EPROTO;
    else if (kind != 2 && WIFEXITED(status)) ++bp.children_executed;
    int extra;
    if (waitpid(-1, &extra, WNOHANG) != -1 || errno != ECHILD || kill(-pid, 0) != -1 || errno != ESRCH)
        stop("child-not-settled");
    bp_children_active = 0;
    if (bp.timed_out || bp.output_exceeded || bp.child_error || !WIFEXITED(status) || WEXITSTATUS(status)) {
        errno = bp.child_error ? (int)bp.child_error : EPROTO;
        stop("preflight-child-result");
    }
    errno = 0;
}

static void bp_loader_inputs(void) {
    struct stat st;
    errno = 0;
    if (!lstat("/newroot/etc/ld.so.preload", &st) || errno != ENOENT) stop("unexpected-loader-preload");
    int fd = fs1_pin_file("/newroot/etc/ld.so.cache", bp_cache_size, bp_cache_sha256, 0);
    if (fd < 0 || close(fd)) stop("loader-cache-binding");
}

static void bp_finish(int complete, const char *why, int error) {
    if (bp_in_cleanup++) bp_park();
    bp.complete = (unsigned)complete;
    if (!complete) {
        bp.error = error > 0 && error <= 4095 ? (unsigned)error : EPROTO;
        size_t n = strlen(why);
        if (n > 62) n = 62;
        memcpy(bp.stop_name, why, n);
    }
    if (bp_children_active || bp.timed_out || bp.output_exceeded || bp_unmount_failed ||
        bp.modules_completed != (bp.virtual_board ? 0U : BP_MODULE_COUNT)) bp_park();
    no_userspace_children(); bp.children_settled = 1;
    /* No open directory, block node or log from the measured phase may keep
     * a mount busy. The proof fd is created only after this release. */
    if (syscall(SYS_close_range, 0U, ~0U, 0)) bp_park();
    if (bp_mounts & 32U) {
        if (bp_umount("/newroot")) bp_park();
    }
    if (bp.partition_ro) {
        if (bp_ro(&bp_endpoint, 0) || fs1_read_super(&bp_endpoint, true) ||
            memcmp(bp_initial_super, bp_endpoint.superblock, sizeof(bp_initial_super)) ||
            fs1_gpt_exact(&bp_endpoint)) bp_park();
        bp.super_unchanged = bp.gpt_unchanged = 1;
    }
    bp_proof_fd = (int)syscall(SYS_memfd_create, "s22-preflight", 3U);
    if (bp_proof_fd < 0 || fchmod(bp_proof_fd, 0400) || dup3(bp_proof_fd, BP_FD, O_CLOEXEC) != BP_FD) bp_park();
    if (bp_proof_fd != BP_FD && close(bp_proof_fd)) bp_park();
    /* Close every borrowed root/device/log descriptor before ordinary unmount. */
    if (syscall(SYS_close_range, 0U, BP_FD - 1U, 0) ||
        syscall(SYS_close_range, BP_FD + 1U, ~0U, 0)) bp_park();
    bp.descriptors_closed = 1;
    const char *const order[] = {"/dev/pts", "/run", "/dev", "/sys", "/proc"};
    for (unsigned i = 0; i < 5; ++i) {
        unsigned bit = bp_mount_bit(order[i]);
        if ((bp_mounts & bit) && bp_umount(order[i])) bp_park();
    }
    if (bp_mounts) bp_park();
    bp.mounts_released = 1; bp.log_size = (unsigned)bp_log_size;
    if (!bp_valid(&bp, bp_run_id, (int)bp.virtual_board) ||
        write(BP_FD, &bp, sizeof(bp)) != sizeof(bp) ||
        write(BP_FD, bp_log, bp_log_size) != (ssize_t)bp_log_size ||
        fcntl(BP_FD, F_ADD_SEALS, BP_SEALS) || fcntl(BP_FD, F_GET_SEALS) != BP_SEALS ||
        fcntl(BP_FD, F_SETFD, 0)) bp_park();
    char *const args[] = {"/init", NULL};
    char *const env[] = {"PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL=C", NULL};
    execve(args[0], args, env);
    bp_park();
}
