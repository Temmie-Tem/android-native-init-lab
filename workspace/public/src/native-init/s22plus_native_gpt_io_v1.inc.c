/* Prospective fixed FYG8 LU0 endpoint for the GPT core. Not activated.
 * Generated code supplies gpt1_original/proposed[GPT1_BYTES] and the exact
 * gpt1_target_run_id. No command accepts a path, LBA, size or payload.
 */
#include <dirent.h>
#include <limits.h>
#include <linux/fs.h>
#include <sys/statfs.h>
#include <sys/sysmacros.h>
#include "s22plus_native_gpt_core_v1.h"

/* Exact FYG8 arch/arm64/include/uapi/asm/fcntl.h overrides generic values. */
_Static_assert(O_DIRECTORY == 040000, "ARM64 O_DIRECTORY differs");
_Static_assert(O_NOFOLLOW == 0100000, "ARM64 O_NOFOLLOW differs");
_Static_assert(O_DIRECT == 0200000, "ARM64 O_DIRECT differs");
_Static_assert(O_DSYNC == 00010000, "ARM64 O_DSYNC differs");
_Static_assert(O_EXCL == 00000200 && O_CLOEXEC == 02000000, "ARM64 open flags differ");
_Static_assert(BLKSSZGET == 0x1268 && BLKGETSIZE64 == 0x80081272UL,
               "ARM64 geometry ioctls differ");
_Static_assert(sizeof(off_t) == 8, "64-bit I/O offsets required");

static uint8_t gpt1_work[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t gpt1_expected[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t gpt1_f2fs[2U * GPT1_BLOCK] __attribute__((aligned(GPT1_BLOCK)));
struct gpt1_endpoint { int descriptor, saved_errno; };

static uint64_t gpt1_little64(const uint8_t *p) {
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; i++) value |= (uint64_t)p[i] << (8U * i);
    return value;
}

static uint64_t gpt1_userdata_sectors(const uint8_t *sealed) {
    const uint8_t *entry = sealed + 2U * GPT1_BLOCK + 39U * 128U;
    uint64_t first = gpt1_little64(entry + 32), last = gpt1_little64(entry + 40);
    if (first != 3726848ULL || last < first || last > GPT1_TOTAL_LBAS - 10U) return 0;
    return (last - first + 1U) * 8U;
}

static int gpt1_read_text(const char *path, char *data, size_t capacity) {
    int f = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (f < 0) return -1;
    struct stat st;
    int ok = !fstat(f, &st) && S_ISREG(st.st_mode) && st.st_uid == 0;
    size_t used = 0;
    while (ok && used < capacity - 1U) {
        ssize_t n = read(f, data + used, capacity - 1U - used);
        if (n < 0) { ok = 0; break; }
        if (!n) break;
        used += (size_t)n;
    }
    char extra;
    if (ok && read(f, &extra, 1) != 0) ok = 0;
    if (close(f)) ok = 0;
    data[used] = 0;
    return ok && used ? 0 : -1;
}

static int gpt1_number(const char *parent, const char *name, uint64_t *value) {
    char path[PATH_MAX], text[32];
    int n = snprintf(path, sizeof(path), "%s/%s", parent, name);
    if (n < 0 || (size_t)n >= sizeof(path) || gpt1_read_text(path, text, sizeof(text))) return -1;
    size_t length = strlen(text);
    if (length < 2 || length > 17 || text[length - 1] != '\n') return -1;
    uint64_t v = 0;
    for (size_t i = 0; i < length - 1; i++) {
        if (text[i] < '0' || text[i] > '9') return -1;
        v = v * 10U + (unsigned)(text[i] - '0');
    }
    *value = v;
    return 0;
}

static int gpt1_native_partition(const char *parent, uint64_t user_size, uint64_t *native_size) {
    const char *disk = strrchr(parent, '/');
    if (!disk || strlen(++disk) != 3) return -1;
    char path[PATH_MAX];
    int n = snprintf(path, sizeof(path), "%s/%s41", parent, disk);
    if (n < 0 || (size_t)n >= sizeof(path)) return -1;
    struct stat st;
    *native_size = 0;
    /* The kernel map follows its boot, not the last metadata write. The
     * successor's original map already contains the retained native entry. */
    const uint8_t *sealed = user_size == gpt1_userdata_sectors(gpt1_original)
        ? gpt1_original : gpt1_proposed;
    const uint8_t *entry = sealed + 2U * GPT1_BLOCK + 40U * 128U;
    unsigned present = 0;
    for (unsigned i = 0; i < 128; i++) present |= entry[i];
    if (!present) {
        return lstat(path, &st) == -1 && errno == ENOENT ? 0 : -1;
    }
    if (lstat(path, &st) || !S_ISDIR(st.st_mode) || st.st_uid) return -1;
    uint64_t index, first;
    uint64_t low = gpt1_little64(entry + 32), high = gpt1_little64(entry + 40);
    if (low > high || high >= GPT1_TOTAL_LBAS ||
        gpt1_number(path, "partition", &index) || index != 41 ||
        gpt1_number(path, "start", &first) || first != low * 8U ||
        gpt1_number(path, "size", native_size) || *native_size != (high - low + 1U) * 8U) return -1;
    char event[PATH_MAX], text[4096];
    n = snprintf(event, sizeof(event), "%s/uevent", path);
    return n > 0 && (size_t)n < sizeof(event) &&
        !gpt1_read_text(event, text, sizeof(text)) && strstr(text, "\nPARTNAME=native_data\n") ? 0 : -1;
}

static int gpt1_geometry_pair(uint64_t old_size, uint64_t new_size) {
    const uint64_t stock = (GPT1_TOTAL_LBAS - 9U - 3726848ULL) * 8U;
    const uint64_t reserved128 = (28750592ULL - 3726848ULL) * 8U;
    const uint64_t android32 = (12115456ULL - 3726848ULL) * 8U;
    return (old_size == stock && new_size == reserved128) ||
           (old_size == reserved128 && new_size == android32);
}

static int gpt1_parent(char parent[PATH_MAX], dev_t *number, uint64_t *user_size, uint64_t *native_size) {
    uint64_t old_size = gpt1_userdata_sectors(gpt1_original);
    uint64_t new_size = gpt1_userdata_sectors(gpt1_proposed);
    if (!gpt1_geometry_pair(old_size, new_size)) return -1;
    DIR *directory = opendir("/sys/class/block");
    if (!directory) return -1;
    struct dirent *entry;
    unsigned count = 0, found = 0;
    int ok = 1;
    for (;;) {
        errno = 0;
        entry = readdir(directory);
        if (!entry) { if (errno) ok = 0; break; }
        if (++count > 256) { ok = 0; break; }
        const char *name = entry->d_name;
        if (strlen(name) != 5 || name[0] != 's' || name[1] != 'd' ||
            name[2] < 'a' || name[2] > 'z' || strcmp(name + 3, "40")) continue;
        char path[PATH_MAX], text[4096], resolved[PATH_MAX];
        int n = snprintf(path, sizeof(path), "/sys/class/block/%s/uevent", name);
        if (n < 0 || (size_t)n >= sizeof(path) || gpt1_read_text(path, text, sizeof(text))) { ok = 0; break; }
        if (!strstr(text, "\nPARTNAME=userdata\n")) continue;
        n = snprintf(path, sizeof(path), "/sys/class/block/%s", name);
        if (n < 0 || (size_t)n >= sizeof(path) || !realpath(path, resolved) || ++found != 1) { ok = 0; break; }
        unsigned host, target, lun; char disk, partition_disk; int consumed = 0;
        const char *tail = NULL;
        const char *prefixes[] = {"/sys/devices/platform/soc/1d84000.ufshc/",
                                  "/sys/devices/platform/soc@0/1d84000.ufshc/"};
        for (unsigned i = 0; i < 2; i++)
            if (!strncmp(resolved, prefixes[i], strlen(prefixes[i]))) tail = resolved + strlen(prefixes[i]);
        if (!tail || sscanf(tail, "host%8u/target%8u:0:0/%8u:0:0:0/block/sd%c/sd%c40%n",
                &host, &target, &lun, &disk, &partition_disk, &consumed) != 5 ||
            tail[consumed] || host != target || host != lun || disk != name[2] ||
            partition_disk != disk) { ok = 0; break; }
        uint64_t index, start;
        if (gpt1_number(resolved, "partition", &index) || index != 40 ||
            gpt1_number(resolved, "start", &start) || start != 3726848ULL * 8U ||
            gpt1_number(resolved, "size", user_size) ||
            (*user_size != old_size && *user_size != new_size)) { ok = 0; break; }
        char *last = strrchr(resolved, '/');
        if (!last) { ok = 0; break; }
        *last = 0;
        memcpy(parent, resolved, strlen(resolved) + 1);
    }
    if (closedir(directory)) ok = 0;
    if (!ok || found != 1) return -1;
    uint64_t sectors, block;
    if (gpt1_number(parent, "size", &sectors) || sectors != GPT1_TOTAL_LBAS * 8U ||
        gpt1_number(parent, "queue/logical_block_size", &block) || block != GPT1_BLOCK) return -1;
    char path[PATH_MAX], text[32];
    int n = snprintf(path, sizeof(path), "%s/dev", parent);
    if (n < 0 || (size_t)n >= sizeof(path) || gpt1_read_text(path, text, sizeof(text))) return -1;
    unsigned ma, mi; int consumed = 0;
    if (sscanf(text, "%4u:%7u\n%n", &ma, &mi, &consumed) != 2 || text[consumed] ||
        ma > 4095 || mi > 1048575) return -1;
    *number = makedev(ma, mi);
    return gpt1_native_partition(parent, *user_size, native_size);
}

static int gpt1_open_endpoint(dev_t number, enum gpt1_mode mode) {
    int d = open("/dev", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (d < 0) return -1;
    struct stat directory, node, held;
    struct statfs filesystem;
    if (fstat(d, &directory) || directory.st_uid || !S_ISDIR(directory.st_mode) ||
        fstatfs(d, &filesystem) || filesystem.f_type != 0x01021994L) { close(d); return -1; }
    const char *name = ".s22-gpt-v1";
    mode_t permissions = mode == GPT1_OBSERVE ? 0400 : 0600;
    if (mknodat(d, name, S_IFBLK | permissions, number)) { close(d); return -1; }
    int ok = !fstatat(d, name, &node, AT_SYMLINK_NOFOLLOW) && S_ISBLK(node.st_mode) &&
        node.st_rdev == number && node.st_uid == 0 && node.st_gid == 0 &&
        node.st_nlink == 1 && (node.st_mode & 07777) == permissions;
    int flags = O_CLOEXEC | O_NOFOLLOW | O_EXCL | O_DIRECT;
    flags |= mode == GPT1_OBSERVE ? O_RDONLY : O_RDWR | O_DSYNC;
    int f = ok ? openat(d, name, flags) : -1;
    if (f >= 0 && (fstat(f, &held) || held.st_ino != node.st_ino || held.st_dev != node.st_dev ||
                  held.st_rdev != number || !S_ISBLK(held.st_mode))) ok = 0;
    if (unlinkat(d, name, 0)) ok = 0;
    if (close(d)) ok = 0;
    if (!ok || f < 0) { if (f >= 0) close(f); return -1; }
    uint64_t bytes = 0; int block = 0, read_only = -1;
    if (ioctl(f, BLKGETSIZE64, &bytes) || bytes != GPT1_TOTAL_LBAS * GPT1_BLOCK ||
        ioctl(f, BLKSSZGET, &block) || block != GPT1_BLOCK ||
        ioctl(f, BLKROGET, &read_only) || (mode != GPT1_OBSERVE && read_only)) {
        close(f); return -1;
    }
    return f;
}

static int gpt1_marker(enum gpt1_mode mode) {
    int d = open("/s22-root-work", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (d < 0) return -1;
    struct stat st; struct statfs fs;
    if (fstat(d, &st) || !S_ISDIR(st.st_mode) || st.st_uid || (st.st_mode & 022) ||
        fstatfs(d, &fs) || fs.f_type != 0x01021994L) { close(d); return -1; }
    char name[96];
    int n = snprintf(name, sizeof(name), ".gpt-%s-%s.intent", gpt1_target_run_id,
                     mode == GPT1_APPLY ? "apply" : "restore");
    if (n < 0 || (size_t)n >= sizeof(name)) { close(d); return -1; }
    int f = openat(d, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0400);
    if (f < 0) { close(d); return -1; }
    int ok = write(f, "intent\n", 7) == 7 && !fsync(f);
    if (close(f)) ok = 0;
    if (fsync(d)) ok = 0;
    if (close(d)) ok = 0;
    return ok ? 0 : -1;
}

static int gpt1_device_read(void *context, uint8_t *data) {
    struct gpt1_endpoint *e = context;
    ssize_t n = pread(e->descriptor, data, GPT1_PRIMARY, 0);
    if (n != GPT1_PRIMARY) { e->saved_errno = n < 0 ? errno : EIO; return -1; }
    n = pread(e->descriptor, data + GPT1_PRIMARY, GPT1_BACKUP,
              (off_t)((GPT1_TOTAL_LBAS - 9U) * GPT1_BLOCK));
    if (n != GPT1_BACKUP) { e->saved_errno = n < 0 ? errno : EIO; return -1; }
    return 0;
}

static int gpt1_device_write(void *context, uint64_t lba, const uint8_t *data) {
    struct gpt1_endpoint *e = context;
    unsigned allowed = 0;
    for (unsigned i = 0; i < 4; i++) allowed |= lba == gpt1_lbas[i];
    if (!allowed || (uintptr_t)data % GPT1_BLOCK) { e->saved_errno = EPROTO; return -1; }
    ssize_t n = pwrite(e->descriptor, data, GPT1_BLOCK, (off_t)(lba * GPT1_BLOCK));
    if (n != GPT1_BLOCK) { e->saved_errno = n < 0 ? errno : EIO; return -1; }
    return 0;
}

static int gpt1_device_sync(void *context) {
    struct gpt1_endpoint *e = context;
    if (fsync(e->descriptor)) { e->saved_errno = errno; return -1; }
    return 0;
}

static void gpt1_record(void *context, unsigned event, unsigned ordinal, uint64_t lba) {
    (void)context;
    if (printf("GPT1_STEP event=%u ordinal=%u lba=%" PRIu64 "\n", event, ordinal, lba) < 0 ||
        fflush(stdout)) _exit(110); /* A lost record never permits another write. */
}

static int gpt1_emit(enum gpt1_mode mode, enum gpt1_error status, int io_error,
        int close_error, const struct gpt1_result *result, uint64_t user_size,
        uint64_t native_size, int filesystem_error, int after_reset) {
    if (printf("GPT1_RESULT mode=%u status=%u io_errno=%d close_errno=%d writes=%u completed=%u skipped=%u last_read_kind=%u userdata_sectors=%" PRIu64 " native_sectors=%" PRIu64 " filesystem_errno=%d\n",
            (unsigned)mode, (unsigned)status, io_error, close_error,
            result->writes_attempted, result->writes_completed, result->skipped, result->final_kind,
            user_size, native_size, filesystem_error) < 0 || fflush(stdout)) return 110;
    /* Partial/failed work never labels a stale read snapshot as final media. */
    if (status || io_error || close_error || filesystem_error) return 104;
    if (printf("GPT1_DATA bytes=%u\n", GPT1_BYTES) < 0 || fflush(stdout) ||
        fwrite(gpt1_work, 1, GPT1_BYTES, stdout) != GPT1_BYTES || fflush(stdout)) return 110;
    /* Export only the geometry prefix of each F2FS superblock. UUID, volume
     * name, salts, filesystem contents and the encryption footer stay unread
     * by the host. The aligned 8 KiB device read remains explicitly scoped. */
    if (after_reset && (printf("GPT1_F2FS bytes=216\n") < 0 || fflush(stdout) ||
        fwrite(gpt1_f2fs + 1024U, 1, 108U, stdout) != 108U ||
        fwrite(gpt1_f2fs + GPT1_BLOCK + 1024U, 1, 108U, stdout) != 108U || fflush(stdout))) return 110;
    if (puts("GPT1_END") < 0 || fflush(stdout)) return 110;
    return 0;
}

static int gpt1_entry_full(enum gpt1_mode mode, const char *identity, int after_reset) {
    if (mode < GPT1_OBSERVE || mode > GPT1_RESTORE ||
        (after_reset < 0 || after_reset > 2) || (after_reset && mode != GPT1_OBSERVE)) return 100;
    if (strcmp(identity, gpt1_target_run_id) || getuid() || geteuid() || getgid() || getegid()) return 100;
    char parent[PATH_MAX]; dev_t number; uint64_t user_size, native_size;
    if (gpt1_parent(parent, &number, &user_size, &native_size)) return 101;
    if (after_reset && user_size != gpt1_userdata_sectors(
            after_reset == 1 ? gpt1_proposed : gpt1_original)) return 101;
    struct gpt1_endpoint endpoint = {.descriptor = gpt1_open_endpoint(number, mode), .saved_errno = 0};
    if (endpoint.descriptor < 0) return 102;
    struct gpt1_io io = {&endpoint, gpt1_device_read, gpt1_device_write, gpt1_device_sync, gpt1_record};
    struct gpt1_result result;
    enum gpt1_error status = gpt1_execute(GPT1_OBSERVE, &io, gpt1_original, gpt1_proposed,
                                         gpt1_work, gpt1_expected, &result);
    if (!status && mode == GPT1_APPLY && result.final_kind != 1) status = GPT1_NOT_ORIGINAL;
    if (!status && mode != GPT1_OBSERVE) {
        if (gpt1_marker(mode)) { close(endpoint.descriptor); return 103; }
        status = gpt1_execute(mode, &io, gpt1_original, gpt1_proposed,
                             gpt1_work, gpt1_expected, &result);
    }
    int filesystem_error = 0;
    if (!status && after_reset) {
        if (result.final_kind != (after_reset == 1 ? 2U : 1U)) filesystem_error = EPROTO;
        else {
            ssize_t n = pread(endpoint.descriptor, gpt1_f2fs, sizeof(gpt1_f2fs),
                              (off_t)(3726848ULL * GPT1_BLOCK));
            if (n != (ssize_t)sizeof(gpt1_f2fs)) filesystem_error = n < 0 ? errno : EIO;
        }
    }
    int close_error = close(endpoint.descriptor) ? errno : 0;
    return gpt1_emit(mode,status,endpoint.saved_errno,close_error,&result,user_size,
        native_size,filesystem_error,after_reset);
}

static int gpt1_entry(enum gpt1_mode mode, const char *identity) {
    return gpt1_entry_full(mode, identity, 0);
}
