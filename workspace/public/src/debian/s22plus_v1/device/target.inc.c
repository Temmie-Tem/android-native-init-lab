/* Included only in the prospective FYG8 PID 1. No formatter is reachable. */
#define FS1_READONLY_BINDING_ONLY
#ifdef S22_DEBIAN_VIRT_TEST
#define fs1_resolve fs1_unused_device_resolve
#endif
#include "../../../native-init/s22plus_native_ext4_v1.c"
#ifdef S22_DEBIAN_VIRT_TEST
#undef fs1_resolve
#include "virt-binding.inc.c"
#endif
#include <sys/utsname.h>
#include <time.h>
#include "target-plan.h"
#ifdef S22_DEBIAN_PREFLIGHT
static void bp_protect(struct fs1_endpoint *);
static void bp_module_done(unsigned);
/* Only this variant accounts for and releases its own mounts. */
#define TARGET_UMOUNT bp_umount
#else
#define TARGET_UMOUNT umount
#endif

static void target_event(const char *message) {
    dprintf(1, "%s\n", message);
#ifdef S22_DEBIAN_VIRT_TEST
    if (diagnostic_console >= 0) dprintf(diagnostic_console, "%s\n", message);
#endif
}

static void target_child_fd(int executable, int input, int output, int jailed,
                            char *const argv[]) {
#ifdef S22_DEBIAN_PREFLIGHT
    if (output >= 0 || jailed) stop("unexpected-preflight-child");
    bp_run_child(1, argv, NULL, 0, executable, input, 0);
#else
    pid_t pid = fork();
    if (pid < 0) stop("target-fork");
    if (!pid) {
        if ((input >= 0 && dup2(input, 0) < 0) ||
            (output >= 0 && dup2(output, 1) < 0) ||
            (jailed && (chdir("/newroot") || chroot(".") || chdir("/")))) _exit(121);
        char *env[] = {"PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL=C", NULL};
        fexecve(executable, argv, env);
        _exit(122);
    }
    int status = 0;
    pid_t result;
    do { result = waitpid(pid, &status, 0); } while (result < 0 && errno == EINTR);
    if (result != pid || !WIFEXITED(status) || WEXITSTATUS(status)) {
        dprintf(2, "TARGET_CHILD_STATUS raw=%d\n", status);
        stop("target-child");
    }
#endif
}

static void target_hash_fd(int fd, uint64_t size, const uint8_t expected[32]) {
    struct s22plus_max77705_runtime_sha256 hash;
    s22plus_max77705_runtime_sha256_init(&hash);
    uint8_t buffer[65536], actual[32];
    uint64_t count = 0;
    if (lseek(fd, 0, SEEK_SET)) stop("archive-seek");
    while (count < size) {
        size_t amount = size - count < sizeof(buffer) ? size - count : sizeof(buffer);
        ssize_t n = read(fd, buffer, amount);
        if (n <= 0) stop("archive-read");
        count += (uint64_t)n;
        s22plus_max77705_runtime_sha256_update(&hash, buffer, (size_t)n);
    }
    if (read(fd, buffer, 1) != 0) stop("archive-tail");
    s22plus_max77705_runtime_sha256_final(&hash, actual);
    if (memcmp(actual, expected, 32) || lseek(fd, 0, SEEK_SET)) stop("archive-digest");
}

static void target_witness(void) {
    uint8_t expected[FS1_BLOCK], actual[FS1_BLOCK];
    fs1_witness(expected);
    int fd = open("/newroot/" FS1_WITNESS_NAME, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
        st.st_nlink != 1 || st.st_size != FS1_BLOCK || (st.st_mode & 07777) != 0400 ||
        read(fd, actual, sizeof(actual)) != sizeof(actual) || memcmp(actual, expected, sizeof(actual)) ||
        close(fd)) stop("retained-witness");
}

static int target_marker(int root, const char *name, int create) {
    int fd = openat(root, name, (create ? O_WRONLY | O_CREAT | O_EXCL : O_RDONLY) |
                   O_CLOEXEC | O_NOFOLLOW, 0400);
    if (fd < 0) {
        if (!create && errno == ENOENT) return 0;
        stop("install-marker-open");
    }
    struct stat st;
    size_t length = sizeof(target_install_identity) - 1U;
    if (create && (write(fd, target_install_identity, length) != (ssize_t)length || fsync(fd)))
        stop("install-marker-write");
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
        st.st_nlink != 1 || (st.st_mode & 07777) != 0400 || st.st_size != (off_t)length)
        stop("install-marker-metadata");
    char actual[sizeof(target_install_identity)];
    if (!create && (read(fd, actual, length) != (ssize_t)length ||
                    memcmp(actual, target_install_identity, length))) stop("install-marker-content");
    if (close(fd) || (create && fsync(root))) stop("install-marker-sync");
    return 1;
}

static void target_empty_root(void) {
    DIR *directory = opendir("/newroot");
    if (!directory) stop("install-root-open");
    unsigned entries = 0;
    struct dirent *entry;
    errno = 0;
    while ((entry = readdir(directory))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        if (++entries > 2 || (strcmp(entry->d_name, "lost+found") &&
            strcmp(entry->d_name, FS1_WITNESS_NAME))) stop("install-root-not-empty");
    }
    if (errno || entries != 2 || closedir(directory) ||
        fs1_empty_directory("/newroot/lost+found")) stop("install-root-inventory");
}

static void target_install(struct fs1_endpoint *endpoint) {
    PREFLIGHT_STAGE(BP_CHECKER);
    int checker = fs1_pin_file("/s22-fs-e2fsck", fs1_checker_size, fs1_checker_sha256, true);
    if (checker < 0) stop("checker-binding");
    char *check[] = {"e2fsck", "-fn", (char *)fs1_node, NULL};
    target_child_fd(checker, -1, -1, 0, check);
    if (close(checker)) stop("checker-close");
    PREFLIGHT_STAGE(BP_FIRST_ROOT);
    mount_at(fs1_node, "/newroot", "ext4", MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
             "noload,nodiscard");
    target_witness();
    int root = open("/newroot", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (root < 0) stop("install-root-fd");
    int started = target_marker(root, ".s22-debian-start-v1", 0);
    int complete = target_marker(root, ".s22-debian-complete-v1", 0);
    if (complete && !started) stop("install-complete-without-start");
    if (started && !complete) stop("install-consumed-incomplete");
#ifdef S22_DEBIAN_INSTALLED_ONLY
    /* A successor may use the completed P401 root, but cannot acquire a new
     * installation intent or reach an extractor on any filesystem state. */
    if (!complete) stop("installed-root-not-complete");
    verify_metadata();
    verify_contents();
    if (close(root) || TARGET_UMOUNT("/newroot")) stop("installed-root-close");
    return;
#else
    if (complete) {
        verify_metadata();
        verify_contents();
        if (close(root) || umount("/newroot")) stop("installed-root-close");
        return;
    }
    target_empty_root();
    if (close(root) || umount("/newroot")) stop("empty-root-close");
    int packed = fs1_pin_file("/rootfs.tar.xz", target_archive_size, target_archive_sha256, false);
    int busybox = fs1_pin_file("/bin/busybox", target_busybox_size, target_busybox_sha256, true);
    if (packed < 0 || busybox < 0) stop("archive-or-extractor-binding");
    int archive = syscall(SYS_memfd_create, "s22-rootfs", 3U); /* CLOEXEC | ALLOW_SEALING */
    if (archive < 0) stop("archive-memfd");
    char *unpack[] = {"busybox", "unxz", "-c", NULL};
    target_child_fd(busybox, packed, archive, 0, unpack);
    if (close(packed) || fcntl(archive, F_ADD_SEALS,
            F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL)) stop("archive-seal");
    target_hash_fd(archive, target_tar_size, target_tar_sha256);
    mount_at(fs1_node, "/newroot", "ext4", MS_NOSUID | MS_NODEV | MS_NOEXEC,
             "errors=remount-ro,nodiscard,data=ordered");
    root = open("/newroot", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (root < 0) stop("install-write-root");
    target_marker(root, ".s22-debian-start-v1", 1);
    if (syncfs(root)) stop("install-intent-syncfs");
    target_event("DEBIAN_INSTALL_INTENT_DURABLE");
    char *extract[] = {"busybox", "tar", "-xpf", "-", NULL};
    target_child_fd(busybox, archive, -1, 1, extract);
    if (close(archive) || close(busybox)) stop("archive-close");
    verify_metadata_path("/install.meta");
    verify_contents_path("/install.sha256");
    target_witness();
    if (syncfs(root)) stop("install-content-syncfs");
    target_marker(root, ".s22-debian-complete-v1", 1);
    if (syncfs(root) || close(root) || umount("/newroot")) stop("install-clean-unmount");
    if (fs1_read_super(endpoint, true) || fs1_gpt_exact(endpoint)) stop("install-final-binding");
    target_event("DEBIAN_INSTALL_COMPLETE");
#endif
}

static const char *target_prepare(void) {
    PREFLIGHT_STAGE(BP_MODULES);
    struct utsname identity;
#ifdef S22_DEBIAN_VIRT_TEST
    char compatible[17];
    read_exact("/sys/firmware/devicetree/base/compatible", compatible, sizeof(compatible));
    if (memcmp(compatible, "linux,dummy-virt", 16) || geteuid() || uname(&identity) ||
        strcmp(identity.machine, "aarch64")) stop("not-device-installer-h0-virt");
    target_event("DEVICE_INSTALLER_H0_VIRT_ONLY");
#else
    if (geteuid() || uname(&identity) || strcmp(identity.machine, "aarch64") ||
        strcmp(identity.release, "5.10.226-android12-9-30958166-abS906NKSS7FYG8"))
        stop("target-kernel");
    /* Exact physical identity is additionally bound by the full sealed GPT. */
    for (unsigned i = 0; i < sizeof(target_modules) / sizeof(target_modules[0]); ++i) {
        const struct target_module *module = target_modules + i;
        int fd = fs1_pin_file(module->path, module->size, module->sha256, false);
        if (fd < 0 || syscall(SYS_finit_module, fd, module->parameters, 0) || close(fd))
            stop("target-module");
        dprintf(1, "TARGET_MODULE_DONE ordinal=%u\n", i + 1U);
#ifdef S22_DEBIAN_PREFLIGHT
        bp_module_done(i + 1U);
#endif
    }
#endif
    PREFLIGHT_STAGE(BP_ENDPOINT);
    struct fs1_endpoint endpoint = {.root_fd = -1, .file_fd = -1, .work_fd = -1, .node_fd = -1};
    struct timespec pause_time = {.tv_sec = 0, .tv_nsec = 100000000};
    int error = ENODEV;
    for (unsigned i = 0; i < 150 && error == ENODEV; ++i) {
        error = fs1_resolve(&endpoint);
        if (error == ENODEV) nanosleep(&pause_time, NULL);
    }
    if (error) { errno = error; stop("target-partition"); }
    if (mkdir("/dev/.s22-ext4-v1", 0700)) stop("target-node-directory");
    endpoint.node_fd = open("/dev/.s22-ext4-v1", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (endpoint.node_fd < 0 || fs1_make_node(&endpoint, "lu0", endpoint.disk, 0400) ||
        fs1_make_node(&endpoint, "native", endpoint.partition, 0600) ||
        fs1_gpt_exact(&endpoint) || fs1_read_super(&endpoint, true)) stop("target-storage-binding");
#ifdef S22_DEBIAN_PREFLIGHT
    bp_protect(&endpoint);
#endif
    target_install(&endpoint);
    /* No whole-disk node survives the bootstrap. The one root node is private. */
#ifndef S22_DEBIAN_PREFLIGHT
    if (unlinkat(endpoint.node_fd, "lu0", 0) || close(endpoint.node_fd)) stop("target-node-close");
#endif
    no_userspace_children();
    return fs1_node;
}
#ifdef S22_DEBIAN_PREFLIGHT
#include "preflight.inc.c"
#endif
