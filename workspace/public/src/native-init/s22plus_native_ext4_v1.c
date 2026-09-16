/* Prospective fixed native_data filesystem endpoint. No live activation here.
 * The generated private seal binds complete GPT, filesystem UUID, tools and
 * native run identity. There is no caller-selected path, option or payload.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/fs.h>
#include <sched.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include "s22plus_native_ext4_core_v1.h"
#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "s22plus_native_ext4_seal_v1.h"

_Static_assert(O_DIRECTORY == 040000 && O_NOFOLLOW == 0100000, "ARM64 path flags");
_Static_assert(O_DIRECT == 0200000 && O_CLOEXEC == 02000000, "ARM64 I/O flags");
_Static_assert(MS_RDONLY == 1 && MS_NOSUID == 2 && MS_NODEV == 4 && MS_NOEXEC == 8,
               "ARM64 mount flags");
_Static_assert(MS_PRIVATE == (1UL << 18) && MS_REC == 16384, "mount propagation flags");
_Static_assert(BLKGETSIZE64 == 0x80081272UL && BLKSSZGET == 0x1268, "ARM64 block ioctls");
_Static_assert(sizeof(off_t) == 8, "64-bit filesystem offsets required");

static const char fs1_node[] = "/dev/.s22-ext4-v1/native";
static const char fs1_disk[] = "/dev/.s22-ext4-v1/lu0";
static const char fs1_root[] = "/s22-root-work/ext4-v1/root";
static const char fs1_formatter[] = "/s22-fs-mke2fs";
static const char fs1_checker[] = "/s22-fs-e2fsck";
static const char fs1_config[] = "/s22-fs-mke2fs.conf";
static uint8_t fs1_gpt_work[FS1_GPT_BYTES];

struct fs1_endpoint {
    dev_t disk, partition;
    char parent[PATH_MAX], sys_partition[PATH_MAX];
    int root_fd, file_fd, work_fd, node_fd;
    unsigned mounted, node_created, disk_created, root_created;
    unsigned helper_reaped, helper_status;
    uint8_t superblock[1024];
};

static int fs1_error(void) { return errno ? errno : EIO; }

static int fs1_read_text(const char *path, char *text, size_t capacity) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return fs1_error();
    struct stat st;
    int error = fstat(fd, &st) ? fs1_error() :
        (!S_ISREG(st.st_mode) || st.st_uid != 0 ? EPROTO : 0);
    size_t used = 0;
    while (!error && used < capacity - 1U) {
        ssize_t count = read(fd, text + used, capacity - 1U - used);
        if (count < 0) { error = fs1_error(); break; }
        if (!count) break;
        used += (size_t)count;
    }
    char extra;
    if (!error && (read(fd, &extra, 1) != 0 || !used)) error = EPROTO;
    if (close(fd) && !error) error = fs1_error();
    text[used] = 0;
    return error;
}

static int fs1_number(const char *directory, const char *name, uint64_t *value) {
    char path[PATH_MAX], text[64];
    int n = snprintf(path, sizeof(path), "%s/%s", directory, name);
    if (n <= 0 || (size_t)n >= sizeof(path)) return EOVERFLOW;
    int error = fs1_read_text(path, text, sizeof(text));
    if (error) return error;
    size_t length = strlen(text);
    if (length < 2 || length > 21 || text[length - 1U] != '\n') return EPROTO;
    uint64_t number = 0;
    for (size_t i = 0; i + 1U < length; ++i) {
        if (text[i] < '0' || text[i] > '9' ||
            number > (UINT64_MAX - (unsigned)(text[i] - '0')) / 10U) return EOVERFLOW;
        number = number * 10U + (unsigned)(text[i] - '0');
    }
    *value = number;
    return 0;
}

static int fs1_device_number(const char *directory, dev_t *value) {
    char path[PATH_MAX], text[64];
    int n = snprintf(path, sizeof(path), "%s/dev", directory);
    if (n <= 0 || (size_t)n >= sizeof(path)) return EOVERFLOW;
    int error = fs1_read_text(path, text, sizeof(text));
    if (error) return error;
    unsigned ma = 0, mi = 0; int end = 0;
    if (sscanf(text, "%4u:%7u\n%n", &ma, &mi, &end) != 2 || text[end] ||
        ma > 4095U || mi > 1048575U) return EPROTO;
    *value = makedev(ma, mi);
    return 0;
}

static int fs1_empty_directory(const char *path) {
    DIR *directory = opendir(path);
    if (!directory) return fs1_error();
    int error = 0; unsigned count = 0;
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) { if (errno) error = errno; break; }
        if (++count > 3U || (strcmp(entry->d_name, ".") && strcmp(entry->d_name, ".."))) {
            error = EBUSY; break;
        }
    }
    if (closedir(directory) && !error) error = fs1_error();
    return error;
}

static int fs1_not_mounted(dev_t device) {
    FILE *file = fopen("/proc/self/mountinfo", "re");
    if (!file) return fs1_error();
    char line[8192]; unsigned rows = 0; int error = 0;
    while (fgets(line, sizeof(line), file)) {
        unsigned ma, mi;
        if (++rows > 1024U || !strchr(line, '\n') ||
            sscanf(line, "%*u %*u %u:%u ", &ma, &mi) != 2) { error = EPROTO; break; }
        if (makedev(ma, mi) == device) { error = EBUSY; break; }
    }
    if (ferror(file) && !error) error = EIO;
    if (fclose(file) && !error) error = fs1_error();
    return error;
}

static int fs1_resolve(struct fs1_endpoint *e) {
    DIR *directory = opendir("/sys/class/block");
    if (!directory) return fs1_error();
    unsigned count = 0, found = 0; int error = 0;
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) { if (errno) error = errno; break; }
        if (++count > 256U) { error = EOVERFLOW; break; }
        const char *name = entry->d_name;
        if (strlen(name) != 5 || strncmp(name, "sd", 2) || name[2] < 'a' ||
            name[2] > 'z' || strcmp(name + 3, "41")) continue;
        char path[PATH_MAX], text[4096], resolved[PATH_MAX];
        int n = snprintf(path, sizeof(path), "/sys/class/block/%s/uevent", name);
        if (n <= 0 || (size_t)n >= sizeof(path)) { error = EOVERFLOW; break; }
        error = fs1_read_text(path, text, sizeof(text));
        if (error) break;
        if (!strstr(text, "\nPARTNAME=native_data\n")) continue;
        if (++found != 1U) { error = EPROTO; break; }
        n = snprintf(path, sizeof(path), "/sys/class/block/%s", name);
        if (n <= 0 || (size_t)n >= sizeof(path) || !realpath(path, resolved)) {
            error = fs1_error(); break;
        }
        const char *tail = NULL;
        const char *prefixes[] = {"/sys/devices/platform/soc/1d84000.ufshc/",
                                  "/sys/devices/platform/soc@0/1d84000.ufshc/"};
        for (unsigned i = 0; i < 2U; ++i)
            if (!strncmp(resolved, prefixes[i], strlen(prefixes[i]))) tail = resolved + strlen(prefixes[i]);
        unsigned host, target, lun; char disk, partition_disk; int end = 0;
        if (!tail || sscanf(tail, "host%8u/target%8u:0:0/%8u:0:0:0/block/sd%c/sd%c41%n",
                &host, &target, &lun, &disk, &partition_disk, &end) != 5 || tail[end] ||
            host != target || host != lun || disk != name[2] || partition_disk != disk) {
            error = EPROTO; break;
        }
        memcpy(e->sys_partition, resolved, strlen(resolved) + 1U);
        char *last = strrchr(resolved, '/');
        if (!last) { error = EPROTO; break; }
        *last = 0;
        memcpy(e->parent, resolved, strlen(resolved) + 1U);
    }
    if (closedir(directory) && !error) error = fs1_error();
    if (error || found != 1U) return error ? error : ENODEV;
    uint64_t index, start, size, total, block, ro;
    if (fs1_number(e->sys_partition, "partition", &index) || index != 41U ||
        fs1_number(e->sys_partition, "start", &start) || start != FS1_FIRST_LBA * 8U ||
        fs1_number(e->sys_partition, "size", &size) || size != FS1_BLOCKS * 8U ||
        fs1_number(e->parent, "size", &total) || total != FS1_GPT_BLOCKS * 8U ||
        fs1_number(e->parent, "queue/logical_block_size", &block) || block != FS1_BLOCK ||
        fs1_number(e->sys_partition, "ro", &ro) || ro != 0) return EPROTO;
    error = fs1_device_number(e->parent, &e->disk);
    if (!error) error = fs1_device_number(e->sys_partition, &e->partition);
    if (error || e->disk == e->partition) return error ? error : EPROTO;
    /* A correct on-disk GPT does not excuse a stale kernel userdata map. */
    const char *disk_name = strrchr(e->parent, '/');
    if (!disk_name || strlen(++disk_name) != 3U) return EPROTO;
    char userdata[PATH_MAX], event[PATH_MAX], text[4096];
    int length = snprintf(userdata, sizeof(userdata), "%s/%s40", e->parent, disk_name);
    if (length <= 0 || (size_t)length >= sizeof(userdata)) return EOVERFLOW;
    if (fs1_number(userdata, "partition", &index) || index != 40U ||
        fs1_number(userdata, "start", &start) || start != 3726848ULL * 8U ||
        fs1_number(userdata, "size", &size) || size != 67108864ULL) return EPROTO;
    length = snprintf(event, sizeof(event), "%s/uevent", userdata);
    if (length <= 0 || (size_t)length >= sizeof(event) || fs1_read_text(event, text, sizeof(text)) ||
        !strstr(text, "\nPARTNAME=userdata\n")) return EPROTO;
    dev_t user_device;
    error = fs1_device_number(userdata, &user_device);
    if (!error && (user_device == e->disk || user_device == e->partition)) error = EPROTO;
    if (!error) error = fs1_not_mounted(user_device);
    if (error) return error;
    char holders[PATH_MAX];
    int n = snprintf(holders, sizeof(holders), "%s/holders", e->sys_partition);
    if (n <= 0 || (size_t)n >= sizeof(holders)) return EOVERFLOW;
    error = fs1_empty_directory(holders);
    return error ? error : fs1_not_mounted(e->partition);
}

static int fs1_make_node(struct fs1_endpoint *e, const char *name, dev_t number,
                         mode_t mode) {
    if (mknodat(e->node_fd, name, S_IFBLK | mode, number)) return fs1_error();
    if (!strcmp(name, "native")) e->node_created = 1;
    else if (!strcmp(name, "lu0")) e->disk_created = 1;
    struct stat st;
    if (fstatat(e->node_fd, name, &st, AT_SYMLINK_NOFOLLOW)) return fs1_error();
    return S_ISBLK(st.st_mode) && st.st_rdev == number && st.st_uid == 0 && st.st_gid == 0 &&
        st.st_nlink == 1 && (st.st_mode & 07777) == mode ? 0 : EPROTO;
}

static int fs1_open_block(const char *path, dev_t expected, uint64_t bytes) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    struct stat st; uint64_t actual = 0; int block = 0;
    if (fstat(fd, &st) || !S_ISBLK(st.st_mode) || st.st_rdev != expected || st.st_uid ||
        st.st_gid || st.st_nlink != 1 || ioctl(fd, BLKGETSIZE64, &actual) || actual != bytes ||
        ioctl(fd, BLKSSZGET, &block) || block != FS1_BLOCK) {
        (void)close(fd); errno = EPROTO; return -1;
    }
    return fd;
}

static int fs1_gpt_exact(struct fs1_endpoint *e) {
    int fd = fs1_open_block(fs1_disk, e->disk, FS1_GPT_BLOCKS * FS1_BLOCK);
    if (fd < 0) return fs1_error();
    int error = 0;
    if (pread(fd, fs1_gpt_work, 6U * FS1_BLOCK, 0) != 6U * FS1_BLOCK ||
        pread(fd, fs1_gpt_work + 6U * FS1_BLOCK, 9U * FS1_BLOCK,
              (off_t)((FS1_GPT_BLOCKS - 9U) * FS1_BLOCK)) != 9U * FS1_BLOCK ||
        memcmp(fs1_gpt_work, fs1_sealed_gpt, FS1_GPT_BYTES)) error = EPROTO;
    if (close(fd) && !error) error = fs1_error();
    return error;
}

static int fs1_read_super(struct fs1_endpoint *e, bool validate) {
    int fd = fs1_open_block(fs1_node, e->partition, FS1_BYTES);
    if (fd < 0) return fs1_error();
    int error = pread(fd, e->superblock, sizeof(e->superblock), 1024) == sizeof(e->superblock) ? 0 : EIO;
    if (close(fd) && !error) error = fs1_error();
    if (!error && validate && !fs1_superblock(e->superblock, sizeof(e->superblock),
                                             fs1_uuid, FS1_BLOCKS)) error = EPROTO;
    return error;
}

static int fs1_pin_file(const char *path, uint64_t size, const uint8_t digest[32], bool executable) {
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    struct stat st;
    int error = fstat(fd, &st) ? fs1_error() : 0;
    if (!error && (!S_ISREG(st.st_mode) || st.st_uid || st.st_gid || st.st_nlink != 1 ||
        (st.st_mode & 022) || (executable && !(st.st_mode & 0100)) ||
        st.st_size < 0 || (uint64_t)st.st_size != size)) error = EPROTO;
    struct s22plus_max77705_runtime_sha256 hash;
    s22plus_max77705_runtime_sha256_init(&hash);
    uint8_t bytes[4096], actual[32]; uint64_t used = 0;
    while (!error && used < size) {
        size_t amount = size - used < sizeof(bytes) ? (size_t)(size - used) : sizeof(bytes);
        ssize_t n = read(fd, bytes, amount);
        if (n <= 0 || (size_t)n != amount) { error = EIO; break; }
        s22plus_max77705_runtime_sha256_update(&hash, bytes, (size_t)n); used += (size_t)n;
    }
    if (!error && read(fd, bytes, 1) != 0) error = EPROTO;
    s22plus_max77705_runtime_sha256_final(&hash, actual);
    if (!error && memcmp(actual, digest, 32)) error = EPROTO;
    if (!error && lseek(fd, 0, SEEK_SET) != 0) error = fs1_error();
    if (error) { (void)close(fd); errno = error; return -1; }
    return fd;
}

static int fs1_tool(struct fs1_endpoint *e, bool formatter) {
    int fd = fs1_pin_file(formatter ? fs1_formatter : fs1_checker,
        formatter ? fs1_formatter_size : fs1_checker_size,
        formatter ? fs1_formatter_sha256 : fs1_checker_sha256, true);
    if (fd < 0) return fs1_error();
    int config = fs1_pin_file(fs1_config, fs1_config_size, fs1_config_sha256, false);
    if (config < 0) { int error = fs1_error(); (void)close(fd); return error; }
    if (close(config)) { int error = fs1_error(); (void)close(fd); return error; }
    char blocks[32];
    if (snprintf(blocks, sizeof(blocks), "%" PRIu64, (uint64_t)FS1_BLOCKS) <= 0) {
        (void)close(fd); return EOVERFLOW;
    }
    char *format_argv[] = {(char *)fs1_formatter, "-q", "-t", "ext4", "-T", "s22root",
        "-b", "4096", "-I", "256", "-i", "65536", "-m", "0", "-e", "remount-ro",
        "-L", "S22DEBIAN", "-U", (char *)fs1_uuid_text,
        "-O", "none,has_journal,ext_attr,dir_index,filetype,extent,64bit,flex_bg,sparse_super,large_file,huge_file,dir_nlink,extra_isize,metadata_csum",
        "-E", "nodiscard,lazy_itable_init=0,lazy_journal_init=0,root_owner=0:0",
        (char *)fs1_node, blocks, NULL};
    char *check_argv[] = {(char *)fs1_checker, "-fn", (char *)fs1_node, NULL};
    char *env[] = {"PATH=/", "LC_ALL=C", "HOME=/", "MKE2FS_CONFIG=/s22-fs-mke2fs.conf", NULL};
    /* Output remains in the authenticated command's bounded raw stdout/stderr.
     * No discard, badblocks, repair, external journal or helper daemon option. */
    if (printf("FS1_TOOL_BEGIN tool=%s\n", formatter ? "format" : "check") < 0 || fflush(stdout)) {
        (void)close(fd); return EIO;
    }
    e->helper_reaped = 0;
    pid_t pid = fork();
    if (pid < 0) { int error = fs1_error(); (void)close(fd); return error; }
    if (!pid) {
        fexecve(fd, formatter ? format_argv : check_argv, env);
        _exit(126);
    }
    int close_error = close(fd) ? fs1_error() : 0;
    int status = 0; pid_t waited;
    do { waited = waitpid(pid, &status, 0); } while (waited < 0 && errno == EINTR);
    if (waited != pid) return fs1_error();
    e->helper_reaped = 1; e->helper_status = (unsigned)status;
    if (printf("FS1_TOOL_END tool=%s status=%u reaped=1\n", formatter ? "format" : "check",
               e->helper_status) < 0 || fflush(stdout)) return EIO;
    if (close_error) return close_error;
    return WIFEXITED(status) && WEXITSTATUS(status) == 0 ? 0 : EIO;
}

static int fs1_mount_root(struct fs1_endpoint *e, enum fs1_mode mode) {
    if (fs1_empty_directory(fs1_root)) return EBUSY;
    unsigned long flags = MS_NOSUID | MS_NODEV | MS_NOEXEC;
    const char *options = "errors=remount-ro,nodiscard,data=ordered";
    if (mode == FS1_VERIFY) { flags |= MS_RDONLY; options = "noload,errors=remount-ro,nodiscard"; }
    if (mount(fs1_node, fs1_root, "ext4", flags, options)) return fs1_error();
    e->mounted = 1;
    return 0;
}

static int fs1_file(struct fs1_endpoint *e, enum fs1_mode mode) {
    e->root_fd = open(fs1_root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (e->root_fd < 0) return fs1_error();
    struct stat st; struct statfs fs;
    if (fstat(e->root_fd, &st) || fstatfs(e->root_fd, &fs)) return fs1_error();
    if (!S_ISDIR(st.st_mode) || st.st_dev != e->partition || st.st_uid || st.st_gid ||
        fs.f_type != 0xef53 || fs.f_bsize != FS1_BLOCK ||
        !!(fs.f_flags & ST_RDONLY) != (mode == FS1_VERIFY) ||
        (fs.f_flags & (ST_NOSUID | ST_NODEV | ST_NOEXEC)) != (ST_NOSUID | ST_NODEV | ST_NOEXEC)) return EPROTO;
    int flags = O_RDONLY | O_NOFOLLOW | O_CLOEXEC;
    if (mode == FS1_INITIALIZE) flags = O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC;
    e->file_fd = openat(e->root_fd, FS1_WITNESS_NAME, flags, 0400);
    if (e->file_fd < 0) return fs1_error();
    uint8_t expected[FS1_BLOCK], actual[FS1_BLOCK]; fs1_witness(expected);
    if (mode == FS1_INITIALIZE && write(e->file_fd, expected, sizeof(expected)) != sizeof(expected)) return EIO;
    if (fstat(e->file_fd, &st)) return fs1_error();
    if (!S_ISREG(st.st_mode) || st.st_dev != e->partition || st.st_uid || st.st_gid ||
        st.st_nlink != 1 || (st.st_mode & 07777) != 0400 || st.st_size != FS1_BLOCK) return EPROTO;
    if (pread(e->file_fd, actual, sizeof(actual), 0) != sizeof(actual) ||
        memcmp(actual, expected, sizeof(actual))) return EPROTO;
    uint8_t extra;
    if (pread(e->file_fd, &extra, 1, FS1_BLOCK) != 0) return EPROTO;
    return 0;
}

static int fs1_unmount(struct fs1_endpoint *e) {
    int error = 0;
    if (e->file_fd >= 0) { if (close(e->file_fd)) error = fs1_error(); e->file_fd = -1; }
    if (e->root_fd >= 0) { if (close(e->root_fd) && !error) error = fs1_error(); e->root_fd = -1; }
    if (!e->mounted) return error ? error : EPROTO;
    /* Never force or lazily detach a filesystem to manufacture a clean close. */
    if (umount2(fs1_root, 0)) { if (!error) error = fs1_error(); }
    else e->mounted = 0;
    return error;
}

static int fs1_step(void *context, enum fs1_step step, enum fs1_mode mode) {
    struct fs1_endpoint *e = context;
    if (step == FS1_BIND) {
        int error = fs1_resolve(e);
        if (!error) {
            error = fs1_make_node(e, "lu0", e->disk, 0400);
            if (!error) e->disk_created = 1;
        }
        if (!error) {
            error = fs1_make_node(e, "native", e->partition, mode == FS1_INITIALIZE ? 0600 : 0400);
            if (!error) e->node_created = 1;
        }
        if (!error) error = fs1_gpt_exact(e);
        if (!error) error = fs1_read_super(e, mode == FS1_VERIFY);
        if (!error && mode == FS1_INITIALIZE && fs1_u16(e->superblock + 0x38) == 0xef53) error = EEXIST;
        return error;
    }
    if (step == FS1_FORMAT) return fs1_tool(e, true);
    if (step == FS1_SUPER) return fs1_read_super(e, true);
    if (step == FS1_CHECK) return fs1_tool(e, false);
    if (step == FS1_MOUNT) return fs1_mount_root(e, mode);
    if (step == FS1_FILE) return fs1_file(e, mode);
    if (step == FS1_SYNC) {
        if (e->file_fd < 0 || e->root_fd < 0) return EPROTO;
        return fsync(e->file_fd) || fsync(e->root_fd) || syncfs(e->root_fd) ? fs1_error() : 0;
    }
    if (step == FS1_UNMOUNT) return fs1_unmount(e);
    if (step == FS1_FINAL) {
        int error = fs1_not_mounted(e->partition);
        if (!error) error = fs1_read_super(e, true);
        if (!error) error = fs1_gpt_exact(e);
        return error;
    }
    return EPROTO;
}

static void fs1_record(void *context, enum fs1_step step, int error) {
    (void)context;
    if (printf("FS1_STEP step=%u errno=%d\n", (unsigned)step, error) < 0 || fflush(stdout)) _exit(120);
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[2], fs1_run_id) || getuid() || geteuid() || getgid() || getegid()) return 100;
    enum fs1_mode mode;
    if (!strcmp(argv[1], "inspect") && !FS1_ALLOW_FORMAT) mode = FS1_INSPECT;
    else if (!strcmp(argv[1], "initialize") && FS1_ALLOW_FORMAT) mode = FS1_INITIALIZE;
    else if (!strcmp(argv[1], "verify") && !FS1_ALLOW_FORMAT) mode = FS1_VERIFY;
    else return 101;
    umask(077);
    int parent = open("/s22-root-work", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st; struct statfs fs;
    if (parent < 0 || fstat(parent, &st) || fstatfs(parent, &fs) || st.st_uid || st.st_gid ||
        !S_ISDIR(st.st_mode) || (st.st_mode & 022) || fs.f_type != 0x01021994L) return 102;
    if (mkdirat(parent, "ext4-v1", 0700)) return 103;
    struct fs1_endpoint e = {.root_fd = -1, .file_fd = -1, .work_fd = -1, .node_fd = -1};
    e.work_fd = openat(parent, "ext4-v1", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (e.work_fd < 0 || fstat(e.work_fd, &st) || !S_ISDIR(st.st_mode) || st.st_uid ||
        st.st_gid || (st.st_mode & 07777) != 0700) return 104;
    if (mkdirat(e.work_fd, "root", 0700)) return 105;
    e.root_created = 1;
    /* The existing workspace is deliberately nodev. Keep that policy and place
     * only our private block aliases in the runtime's checked device tmpfs. */
    int devices = open("/dev", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (devices < 0 || fstat(devices, &st) || fstatfs(devices, &fs) || st.st_uid || st.st_gid ||
        !S_ISDIR(st.st_mode) || (st.st_mode & 022) || fs.f_type != 0x01021994L ||
        (fs.f_flags & ST_NODEV)) return 107;
    if (mkdirat(devices, ".s22-ext4-v1", 0700)) return 108;
    e.node_fd = openat(devices, ".s22-ext4-v1", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (e.node_fd < 0 || fstat(e.node_fd, &st) || !S_ISDIR(st.st_mode) || st.st_uid || st.st_gid ||
        (st.st_mode & 07777) != 0700) return 109;
    if (unshare(CLONE_NEWNS) || mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)) return 106;
    struct fs1_io io = {&e, fs1_step, fs1_record}; struct fs1_result result;
    int rc = fs1_execute(mode, &io, &result), cleanup = 0;
    if (e.file_fd >= 0 || e.root_fd >= 0 || e.mounted) cleanup = EBUSY;
    if (!cleanup && e.node_created && unlinkat(e.node_fd, "native", 0)) cleanup = fs1_error();
    if (!cleanup && e.disk_created && unlinkat(e.node_fd, "lu0", 0)) cleanup = fs1_error();
    if (close(e.node_fd) && !cleanup) cleanup = fs1_error();
    if (!cleanup && unlinkat(devices, ".s22-ext4-v1", AT_REMOVEDIR)) cleanup = fs1_error();
    if (close(devices) && !cleanup) cleanup = fs1_error();
    if (!cleanup && e.root_created && unlinkat(e.work_fd, "root", AT_REMOVEDIR)) cleanup = fs1_error();
    if (close(e.work_fd) && !cleanup) cleanup = fs1_error();
    if (!cleanup && unlinkat(parent, "ext4-v1", AT_REMOVEDIR)) cleanup = fs1_error();
    if (close(parent) && !cleanup) cleanup = fs1_error();
    printf("FS1_RESULT mode=%u status=%u last=%u failed=%u errno=%d formatted=%u "
           "mounted=%u witness=%u synced=%u unmounted=%u cleanup_attempted=%u cleanup_failed=%u "
           "cleanup_errno=%d helper_reaped=%u helper_status=%u blocks=%" PRIu64 "\n",
           (unsigned)mode, (unsigned)(rc != 0 || cleanup != 0), result.last_completed,
           result.failed_step, result.error, result.formatted, result.mounted, result.witness_verified,
           result.synchronized, result.unmounted, result.cleanup_attempted, result.cleanup_failed,
           cleanup, e.helper_reaped, e.helper_status, (uint64_t)FS1_BLOCKS);
    if (fflush(stdout)) return 120;
    return rc || cleanup ? 1 : 0;
}
