/* H0 initramfs PID 1, ARM64 Linux 5.10. Hardware preparation is separate.
 * No formatter, flash transport, recovery promise or resident supervisor.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include "binding.h"

_Static_assert(O_DIRECTORY == 16384 && O_NOFOLLOW == 32768 && O_CLOEXEC == 524288,
               "build with the ARM64 Linux UAPI");

#ifdef S22_DEBIAN_VIRT_TEST
static int diagnostic_console = -1;
#endif

static void stop(const char *why) {
    int error = errno;
    dprintf(2, "BOOTSTRAP_STOP stage=%s errno=%d\n", why, error);
#ifdef S22_DEBIAN_VIRT_TEST
    if (diagnostic_console >= 0) dprintf(diagnostic_console, "BOOTSTRAP_STOP stage=%s errno=%d\n", why, error);
#endif
    /* PID 1 must neither exit nor guess a recovery action. */
    if (getpid() != 1) _exit(1);
    for (;;) pause();
}
static void directory(const char *path, mode_t mode) {
    if (mkdir(path, mode) && errno != EEXIST) stop("mkdir");
    struct stat st;
    if (lstat(path, &st) || !S_ISDIR(st.st_mode)) stop("directory-type");
}
static void mount_at(const char *src, const char *dst, const char *type,
                     unsigned long flags, const char *data) {
    if (mount(src, dst, type, flags, data)) stop(dst);
}
static void read_exact(const char *path, char *data, size_t n) {
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0 || read(fd, data, n) != (ssize_t)n || close(fd)) stop(path);
}
static void child(char *const argv[], const char *cwd, int chrooted) {
    pid_t pid = fork();
    if (pid < 0) stop("fork");
    if (!pid) {
        if (cwd && chdir(cwd)) _exit(121);
        if (chrooted && (chroot(".") || chdir("/"))) _exit(122);
        execv(argv[0], argv);
        _exit(123);
    }
    int status;
    if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status) || WEXITSTATUS(status))
        stop("preflight-child");
}
static void no_userspace_children(void) {
    DIR *d = opendir("/proc");
    if (!d) stop("proc-open");
    struct dirent *entry;
    while ((entry = readdir(d))) {
        char *end;
        long pid = strtol(entry->d_name, &end, 10);
        if (*end || pid <= 1) continue;
        char path[128];
        snprintf(path, sizeof(path), "/proc/%ld/exe", pid);
        char buf[4096];
        ssize_t n = readlink(path, buf, sizeof(buf));
        if (n >= 0 || (errno != ENOENT && errno != ESRCH)) stop("leftover-userspace");
    }
    if (closedir(d)) stop("proc-close");
    int status;
    if (waitpid(-1, &status, WNOHANG) != -1 || errno != ECHILD) stop("unreaped-child");
}
static unsigned long long little(const unsigned char *p, unsigned n) {
    unsigned long long value = 0;
    for (unsigned i = 0; i < n; ++i) value |= (unsigned long long)p[i] << (8U * i);
    return value;
}
static int metadata_inside(int fd) {
    if (chdir("/newroot") || chroot(".") || chdir("/")) return 124;
    unsigned char header[24];
    unsigned count = 0;
    for (;;) {
        ssize_t n = read(fd, header, sizeof(header));
        if (!n) return count ? 0 : 125;
        if (n != sizeof(header) || ++count > 65536) return 126;
        unsigned plen = (unsigned)little(header + 20, 2);
        unsigned llen = (unsigned)little(header + 22, 2);
        char path[4096], link[4096], actual[4096];
        if (!plen || plen >= sizeof(path) || llen >= sizeof(link) ||
            read(fd, path, plen) != plen || read(fd, link, llen) != llen) return 127;
        path[plen] = link[llen] = 0;
        if (strlen(path) != plen || path[0] == '/' || strstr(path, "../") ||
            !strcmp(path, "..")) return 128;
        struct stat st;
        if (lstat(path, &st) || st.st_mode != little(header, 4) ||
            st.st_uid != little(header + 4, 4) || st.st_gid != little(header + 8, 4)) {
            dprintf(2, "METADATA_MISMATCH path=%s\n", path); return 129;
        }
        if (S_ISREG(st.st_mode) && (unsigned long long)st.st_size != little(header + 12, 8)) {
            dprintf(2, "METADATA_MISMATCH kind=size path=%s\n", path);
            return 130;
        }
        if (S_ISLNK(st.st_mode) && (readlink(path, actual, sizeof(actual)) != llen ||
                                    memcmp(actual, link, llen))) {
            dprintf(2, "METADATA_MISMATCH kind=link path=%s\n", path);
            return 131;
        }
    }
}
static void verify_metadata_path(const char *path) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) stop("metadata-open");
    pid_t pid = fork();
    if (pid < 0) stop("metadata-fork");
    if (!pid) _exit(metadata_inside(fd));
    int status = 0;
    if (close(fd) || waitpid(pid, &status, 0) != pid) stop("metadata-child-wait");
    if (!WIFEXITED(status) || WEXITSTATUS(status)) {
        dprintf(2, "METADATA_CHILD_STATUS raw=%d\n", status);
        errno = EPROTO;
        stop("root-metadata");
    }
}
static void verify_contents_path(const char *path) {
    int executable = open("/bin/busybox", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    int manifest = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (executable < 0 || manifest < 0) stop("content-open");
    pid_t pid = fork();
    if (pid < 0) stop("content-fork");
    if (!pid) {
        if (dup2(manifest, 0) < 0 || chdir("/newroot") || chroot(".") || chdir("/")) _exit(132);
        char *args[] = {"busybox", "sha256sum", "-cs", "-", NULL};
        char *env[] = {"LC_ALL=C", NULL};
        fexecve(executable, args, env);
        _exit(133);
    }
    int status;
    if (close(executable) || close(manifest) || waitpid(pid, &status, 0) != pid ||
        !WIFEXITED(status) || WEXITSTATUS(status)) stop("root-content");
}
static void verify_metadata(void) { verify_metadata_path("/rootfs.meta"); }
static void verify_contents(void) { verify_contents_path("/rootfs.sha256"); }
#ifdef S22_DEBIAN_DEVICE
#include "device/target.inc.c"

#ifdef S22_DEBIAN_INSTALLED_ONLY
#include "installed-plan.h"
static void installed_shutdown_command(void) {
    /* The retained P401 root key permits shutdown only on boot count two.
     * This fixed tmpfs bind supplies the same restricted command vocabulary
     * with a count-independent orderly shutdown. The ext4 file is unchanged. */
    int source = fs1_pin_file("/p404-lab-qualify", target_qualify_size,
                              target_qualify_sha256, true);
    if (source < 0) stop("installed-shutdown-source");
    int output = open("/run/.p404-lab-qualify", O_WRONLY | O_CREAT | O_EXCL |
                      O_CLOEXEC | O_NOFOLLOW, 0500);
    if (output < 0) stop("installed-shutdown-copy-open");
    unsigned long long copied = 0;
    char buffer[4096];
    while (copied < target_qualify_size) {
        size_t take = sizeof(buffer);
        if (target_qualify_size - copied < take) take = target_qualify_size - copied;
        ssize_t got = read(source, buffer, take);
        if (got <= 0 || write(output, buffer, got) != got)
            stop("installed-shutdown-copy");
        copied += got;
    }
    if (fsync(output) || close(output) || close(source)) stop("installed-shutdown-copy-close");
    const char *destination = "/newroot/usr/local/sbin/lab-qualify";
    if (mount("/run/.p404-lab-qualify", destination, NULL, MS_BIND, NULL) ||
        mount(NULL, destination, NULL, MS_REMOUNT | MS_BIND | MS_RDONLY |
              MS_NOSUID | MS_NODEV, NULL)) stop("installed-shutdown-bind");
    struct statvfs state;
    if (statvfs(destination, &state) ||
        (state.f_flag & (ST_RDONLY | ST_NOSUID | ST_NODEV)) !=
             (ST_RDONLY | ST_NOSUID | ST_NODEV)) stop("installed-shutdown-bind-readback");
}
#endif
#endif
int main(void) {
    if (getpid() != 1) stop("not-pid1");
    umask(022);
    directory("/proc", 0555); directory("/sys", 0555);
    directory("/dev", 0755); directory("/run", 0755); directory("/newroot", 0755);
    mount_at("proc", "/proc", "proc", MS_NOSUID | MS_NOEXEC | MS_NODEV, NULL);
    mount_at("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NOEXEC | MS_NODEV, NULL);
#ifndef S22_DEBIAN_DEVICE
    /* This validation image is deliberately bound to the virt board. */
    char compatible[17];
    read_exact("/sys/firmware/devicetree/base/compatible", compatible, sizeof(compatible));
    if (memcmp(compatible, "linux,dummy-virt", 16)) stop("not-h0-virt");
#endif
    mount_at(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL);
    mount_at("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    if (mknod("/dev/console", S_IFCHR | 0600, makedev(5, 1)) ||
        mknod("/dev/null", S_IFCHR | 0666, makedev(1, 3))) stop("essential-nodes");
    int console = open("/dev/console", O_RDWR | O_NOCTTY | O_CLOEXEC);
#ifdef S22_DEBIAN_DEVICE
    /* FYG8 has no usable early userspace console; SysVinit also supports this
     * headless fallback. Bootstrap diagnostics move to RAM after /run exists. */
    if (console < 0) console = open("/dev/null", O_RDWR | O_CLOEXEC);
#endif
    if (console < 0) stop("console");
    for (int fd = 0; fd < 3; ++fd) if (dup2(console, fd) < 0) stop("console-dup");
#ifdef S22_DEBIAN_VIRT_TEST
    diagnostic_console = fcntl(console, F_DUPFD_CLOEXEC, 3);
    if (diagnostic_console < 0) stop("h0-diagnostic-console");
#endif
    if (console > 2 && close(console)) stop("console-close");
    directory("/dev/pts", 0755); directory("/dev/shm", 01777);
    mount_at("devpts", "/dev/pts", "devpts", MS_NOSUID | MS_NOEXEC,
             "newinstance,ptmxmode=0666,mode=0620,gid=5");
    if (symlink("pts/ptmx", "/dev/ptmx") || symlink("/proc/self/fd", "/dev/fd") ||
        symlink("/proc/self/fd/0", "/dev/stdin") || symlink("/proc/self/fd/1", "/dev/stdout") ||
        symlink("/proc/self/fd/2", "/dev/stderr")) stop("device-links");
    mount_at("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");
#ifdef S22_DEBIAN_DEVICE
    int log = open("/run/lab-bootstrap.log", O_WRONLY | O_CREAT | O_EXCL | O_APPEND | O_CLOEXEC, 0600);
    if (log < 0) stop("bootstrap-log");
    if (dup2(log, 1) < 0 || dup2(log, 2) < 0) stop("bootstrap-log-redirect");
    if (close(log)) stop("bootstrap-log-close");
#ifdef S22_DEBIAN_INSTALLED_ONLY
    dprintf(1, "%s", target_boot_identity);
#endif
    const char *root_device = target_prepare();
#else
    const char *root_device = "/dev/vda";
#endif
    char *scan[] = {"/bin/busybox", "mdev", "-s", NULL};
    child(scan, NULL, 0);
    struct stat block;
    if (lstat(root_device, &block) || !S_ISBLK(block.st_mode)) stop("root-block");
    int fd = open(root_device, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    unsigned char uuid[16];
    if (fd < 0 || pread(fd, uuid, 16, 1024 + 0x68) != 16 ||
        memcmp(uuid, root_uuid, 16) || close(fd)) stop("root-uuid");
    /* Inspect before a writable mount: noload prevents ext4 journal replay. */
    mount_at(root_device, "/newroot", "ext4", MS_RDONLY, "noload");
    char marker[18];
    read_exact("/newroot/etc/lab-rootfs-id", marker, sizeof(marker));
    if (memcmp(marker, "S22PLUS_DEBIAN_V1\n", sizeof(marker))) stop("root-identity");
    verify_metadata();
    verify_contents();
    char *verify[] = {"/lib/ld-linux-aarch64.so.1", "--verify", "/sbin/init", NULL};
    char *libs[] = {"/lib/ld-linux-aarch64.so.1", "--list", "/sbin/init", NULL};
    child(verify, "/newroot", 1); child(libs, "/newroot", 1);
    no_userspace_children();
    /* Do not carry the noload option into the writable lifetime. */
    if (umount("/newroot")) stop("preflight-unmount");
    mount_at(root_device, "/newroot", "ext4", 0, "errors=remount-ro,nodiscard");
#ifdef S22_DEBIAN_INSTALLED_ONLY
    installed_shutdown_command();
#endif
    for (const char **p = (const char *[]){"dev", "proc", "sys", "run", NULL}; *p; ++p) {
        char source[32], target[64];
        snprintf(source, sizeof(source), "/%s", *p);
        snprintf(target, sizeof(target), "/newroot/%s", *p);
        struct stat st;
        if (lstat(target, &st) || !S_ISDIR(st.st_mode)) stop("mount-destination");
        mount_at(source, target, NULL, MS_MOVE, NULL);
    }
    if (syscall(SYS_close_range, 3U, ~0U, 0)) stop("close-extra-fds");
#ifdef S22_DEBIAN_VIRT_TEST
    dprintf(1, "BOOTSTRAP_HANDOFF pid=1 children=0 backend=h0-virt-installer\n");
#elif defined(S22_DEBIAN_DEVICE)
    dprintf(1, "BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n");
#else
    dprintf(1, "BOOTSTRAP_HANDOFF pid=1 children=0 backend=h0-virt\n");
#endif
    char *next[] = {"/bin/busybox", "switch_root", "/newroot", "/sbin/init", NULL};
    execv(next[0], next);
    stop("switch-root-exec");
    return 1;
}
