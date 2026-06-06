#include "a90_storage.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_timeline.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static bool cache_ready = false;

static struct a90_storage_status storage_state = {
    .probed = false,
    .sd_present = false,
    .sd_mounted = false,
    .sd_expected = false,
    .sd_rw_ok = false,
    .fallback = true,
    .backend = "cache",
    .root = CACHE_STORAGE_ROOT,
    .sd_uuid = "<none>",
    .warning = "SD not probed; using /cache",
    .detail = "boot storage probe pending",
};

static int parse_dev_numbers(const char *dev_info,
                             unsigned int *major_num,
                             unsigned int *minor_num) {
    if (sscanf(dev_info, "%u:%u", major_num, minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int ensure_block_node_exact(const char *path,
                                   unsigned int major_num,
                                   unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);

    if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
        return 0;
    }
    if (errno == EEXIST) {
        struct stat st;

        if (lstat(path, &st) == 0 &&
            S_ISBLK(st.st_mode) &&
            st.st_rdev == wanted) {
            return 0;
        }
        if (unlink(path) < 0) {
            return -1;
        }
        if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
            return 0;
        }
    }
    return -1;
}

static int storage_get_block_device_path(const char *block_name,
                                         char *out,
                                         size_t out_size) {
    char dev_info_path[PATH_MAX];
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/block/%s/dev", block_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (read_trimmed_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }
    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }
    if (ensure_dir("/dev/block", 0755) < 0) {
        return -1;
    }
    if (snprintf(out, out_size, "/dev/block/%s", block_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (ensure_block_node_exact(out, major_num, minor_num) < 0) {
        return -1;
    }
    return 0;
}

static bool mount_line_for_path(const char *path,
                                char *out,
                                size_t out_size,
                                bool *read_only_out) {
    FILE *fp;
    char line[512];

    if (out_size > 0) {
        out[0] = '\0';
    }
    if (read_only_out != NULL) {
        *read_only_out = false;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return false;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char src[160];
        char dst[160];
        char type[64];
        char opts[192];

        if (sscanf(line, "%159s %159s %63s %191s", src, dst, type, opts) != 4) {
            continue;
        }
        if (strcmp(dst, path) == 0) {
            if (out_size > 0) {
                snprintf(out, out_size, "%s", line);
            }
            if (read_only_out != NULL) {
                char opt_copy[192];
                char *token;
                char *saveptr = NULL;

                snprintf(opt_copy, sizeof(opt_copy), "%s", opts);
                for (token = strtok_r(opt_copy, ",", &saveptr);
                     token != NULL;
                     token = strtok_r(NULL, ",", &saveptr)) {
                    if (strcmp(token, "ro") == 0) {
                        *read_only_out = true;
                        break;
                    }
                }
            }
            fclose(fp);
            return true;
        }
    }
    fclose(fp);
    return false;
}

static int read_ext4_uuid(const char *node_path, char *out, size_t out_size) {
    unsigned char uuid[16];
    ssize_t rd;
    int fd;

    if (out_size < 37) {
        errno = ENOSPC;
        return -1;
    }
    fd = open(node_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    rd = pread(fd, uuid, sizeof(uuid), 1024 + 0x68);
    close(fd);
    if (rd != (ssize_t)sizeof(uuid)) {
        errno = EIO;
        return -1;
    }
    snprintf(out,
             out_size,
             "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
             uuid[0], uuid[1], uuid[2], uuid[3],
             uuid[4], uuid[5],
             uuid[6], uuid[7],
             uuid[8], uuid[9],
             uuid[10], uuid[11], uuid[12], uuid[13], uuid[14], uuid[15]);
    return 0;
}

static int write_text_file_sync(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);

    if (fd < 0) {
        return -1;
    }
    if (write_all_checked(fd, value, strlen(value)) < 0 ||
        fsync(fd) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        return -1;
    }
    return 0;
}

static int ensure_sd_workspace(void) {
    static const char *dirs[] = {
        SD_WORKSPACE_DIR,
        SD_WORKSPACE_DIR "/bin",
        SD_WORKSPACE_DIR "/logs",
        SD_WORKSPACE_DIR "/tmp",
        SD_WORKSPACE_DIR "/rootfs",
        SD_WORKSPACE_DIR "/images",
        SD_WORKSPACE_DIR "/backups",
    };
    size_t index;

    for (index = 0; index < sizeof(dirs) / sizeof(dirs[0]); ++index) {
        if (ensure_dir(dirs[index], 0755) < 0) {
            int saved_errno = errno;

            a90_console_printf("mountsd: mkdir %s: %s\r\n", dirs[index], strerror(saved_errno));
            return -saved_errno;
        }
    }
    return 0;
}

static int ensure_sd_identity_marker(const char *uuid) {
    char marker[96];
    int saved_errno;

    if (read_trimmed_text_file(SD_ID_FILE, marker, sizeof(marker)) == 0) {
        if (strcmp(marker, uuid) == 0) {
            return 0;
        }
        errno = ESTALE;
        return -1;
    }
    saved_errno = errno;
    if (saved_errno != ENOENT) {
        errno = saved_errno;
        return -1;
    }
    if (write_text_file_sync(SD_ID_FILE, uuid) < 0) {
        return -1;
    }
    return 0;
}

static int sd_write_read_probe(void) {
    char payload[128];
    char readback[128];

    snprintf(payload,
             sizeof(payload),
             "boot-rw-test %s %s %ld",
             INIT_VERSION,
             INIT_BUILD,
             monotonic_millis());
    if (write_text_file_sync(SD_BOOT_RW_TEST_FILE, payload) < 0) {
        return -1;
    }
    sync();
    if (read_trimmed_text_file(SD_BOOT_RW_TEST_FILE, readback, sizeof(readback)) < 0) {
        return -1;
    }
    unlink(SD_BOOT_RW_TEST_FILE);
    if (strcmp(payload, readback) != 0) {
        errno = EIO;
        return -1;
    }
    return 0;
}

static void storage_hook_line(const struct a90_storage_boot_hooks *hooks,
                              void *ctx,
                              int line,
                              const char *fmt,
                              ...) {
    char text[BOOT_SPLASH_LINE_MAX];
    va_list ap;

    if (hooks == NULL || hooks->set_line == NULL) {
        return;
    }
    va_start(ap, fmt);
    vsnprintf(text, sizeof(text), fmt, ap);
    va_end(ap);
    hooks->set_line(ctx, line, text);
}

static void storage_hook_frame(const struct a90_storage_boot_hooks *hooks, void *ctx) {
    if (hooks != NULL && hooks->draw_frame != NULL) {
        hooks->draw_frame(ctx);
    }
}

static void storage_use_cache(const struct a90_storage_boot_hooks *hooks,
                              void *ctx,
                              const char *reason,
                              int rc,
                              int saved_errno) {
    const char *fallback_root = cache_ready ? CACHE_STORAGE_ROOT : TMP_STORAGE_ROOT;

    storage_state.probed = true;
    storage_state.fallback = true;
    snprintf(storage_state.backend,
             sizeof(storage_state.backend),
             "%s",
             cache_ready ? "cache" : "tmp");
    snprintf(storage_state.root,
             sizeof(storage_state.root),
             "%s",
             fallback_root);
    snprintf(storage_state.warning,
             sizeof(storage_state.warning),
             "%s; fallback %s",
             reason,
             fallback_root);
    snprintf(storage_state.detail,
             sizeof(storage_state.detail),
             "rc=%d errno=%d %s",
             rc,
             saved_errno,
             saved_errno != 0 ? strerror(saved_errno) : "ok");
    storage_hook_line(hooks, ctx, 3, "[ STORAGE] WARN FALLBACK %s", storage_state.root);
    a90_logf("storage", "fallback root=%s reason=%s detail=%s",
                storage_state.root,
                reason,
                storage_state.detail);
    a90_timeline_record(rc, saved_errno, "storage", "%s", storage_state.warning);
}

static void storage_use_sd(const struct a90_storage_boot_hooks *hooks, void *ctx) {
    storage_state.probed = true;
    storage_state.fallback = false;
    storage_state.sd_present = true;
    storage_state.sd_mounted = true;
    storage_state.sd_expected = true;
    storage_state.sd_rw_ok = true;
    snprintf(storage_state.backend, sizeof(storage_state.backend), "%s", "sd");
    snprintf(storage_state.root, sizeof(storage_state.root), "%s", SD_WORKSPACE_DIR);
    storage_state.warning[0] = '\0';
    snprintf(storage_state.detail,
             sizeof(storage_state.detail),
             "uuid=%s workspace=%s",
             storage_state.sd_uuid,
             SD_WORKSPACE_DIR);
    storage_hook_line(hooks, ctx, 3, "[ STORAGE] SD MAIN READY");
    if (a90_log_set_path(SD_NATIVE_LOG_PATH) < 0 && cache_ready) {
        a90_log_select_or_fallback(NATIVE_LOG_PRIMARY);
    }
    a90_timeline_replay_to_log("sd-storage");
    a90_logf("storage", "sd main root=%s uuid=%s", storage_state.root, storage_state.sd_uuid);
    a90_timeline_record(0, 0, "storage", "sd main root=%s uuid=%s",
                    storage_state.root,
                    storage_state.sd_uuid);
}

int a90_storage_mount_cache(void) {
    char node_path[PATH_MAX];

    cache_ready = false;
    if (storage_get_block_device_path("sda31", node_path, sizeof(node_path)) < 0) {
        return -1;
    }
    if (mount(node_path, CACHE_STORAGE_ROOT, "ext4", 0, NULL) == 0) {
        cache_ready = true;
        return 0;
    }
    return -1;
}

void a90_storage_set_cache_ready(bool ready) {
    cache_ready = ready;
}

int a90_storage_probe_boot(const struct a90_storage_boot_hooks *hooks, void *ctx) {
    char node_path[PATH_MAX];
    char line[512];
    bool read_only = false;

    storage_hook_line(hooks, ctx, 2, "[ SD     ] PROBE %s", SD_BLOCK_NAME);
    storage_hook_frame(hooks, ctx);
    a90_logf("storage", "boot sd probe start expected_uuid=%s", SD_EXPECTED_UUID);

    if (storage_get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        int saved_errno = errno;

        storage_state.sd_present = false;
        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN BLOCK MISSING");
        storage_hook_frame(hooks, ctx);
        storage_use_cache(hooks, ctx, "sd block missing", -saved_errno, saved_errno);
        return -saved_errno;
    }
    storage_state.sd_present = true;
    storage_hook_line(hooks, ctx, 2, "[ SD     ] BLOCK OK");
    storage_hook_frame(hooks, ctx);

    if (read_ext4_uuid(node_path, storage_state.sd_uuid, sizeof(storage_state.sd_uuid)) < 0) {
        int saved_errno = errno;

        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN UUID READ FAIL");
        storage_hook_frame(hooks, ctx);
        storage_use_cache(hooks, ctx, "sd uuid read failed", -saved_errno, saved_errno);
        return -saved_errno;
    }
    if (strcmp(storage_state.sd_uuid, SD_EXPECTED_UUID) != 0) {
        storage_state.sd_expected = false;
        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN UUID MISMATCH");
        storage_hook_frame(hooks, ctx);
        storage_use_cache(hooks, ctx, "sd uuid mismatch", -ESTALE, ESTALE);
        return -ESTALE;
    }
    storage_state.sd_expected = true;
    storage_hook_line(hooks, ctx, 2, "[ SD     ] UUID OK");
    storage_hook_frame(hooks, ctx);

    ensure_dir("/mnt", 0755);
    ensure_dir(SD_MOUNT_POINT, 0755);
    if (mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN REMOUNT FAIL");
            storage_hook_frame(hooks, ctx);
            storage_use_cache(hooks, ctx, "sd remount failed", -saved_errno, saved_errno);
            return -saved_errno;
        }
    }
    if (mount(node_path, SD_MOUNT_POINT, SD_FS_TYPE, 0, NULL) < 0) {
        int saved_errno = errno;

        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN MOUNT FAIL");
        storage_hook_frame(hooks, ctx);
        storage_use_cache(hooks, ctx, "sd mount failed", -saved_errno, saved_errno);
        return -saved_errno;
    }
    storage_state.sd_mounted = true;
    storage_hook_line(hooks, ctx, 2, "[ SD     ] MOUNT RW OK");
    storage_hook_frame(hooks, ctx);

    if (ensure_sd_workspace() < 0) {
        int saved_errno = errno;

        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN WORKSPACE FAIL");
        storage_hook_frame(hooks, ctx);
        umount(SD_MOUNT_POINT);
        storage_state.sd_mounted = false;
        storage_use_cache(hooks, ctx, "sd workspace failed", -saved_errno, saved_errno);
        return -saved_errno;
    }
    if (ensure_sd_identity_marker(storage_state.sd_uuid) < 0) {
        int saved_errno = errno;

        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN ID MARKER FAIL");
        storage_hook_frame(hooks, ctx);
        umount(SD_MOUNT_POINT);
        storage_state.sd_mounted = false;
        storage_use_cache(hooks, ctx, "sd identity marker failed", -saved_errno, saved_errno);
        return -saved_errno;
    }
    if (sd_write_read_probe() < 0) {
        int saved_errno = errno;

        storage_hook_line(hooks, ctx, 2, "[ SD     ] WARN RW TEST FAIL");
        storage_hook_frame(hooks, ctx);
        umount(SD_MOUNT_POINT);
        storage_state.sd_mounted = false;
        storage_use_cache(hooks, ctx, "sd rw test failed", -saved_errno, saved_errno);
        return -saved_errno;
    }
    storage_state.sd_rw_ok = true;
    storage_hook_line(hooks, ctx, 2, "[ SD     ] RW TEST OK");
    storage_hook_frame(hooks, ctx);
    storage_use_sd(hooks, ctx);
    storage_hook_frame(hooks, ctx);
    return 0;
}

int a90_storage_get_status(struct a90_storage_status *out) {
    if (out == NULL) {
        errno = EINVAL;
        return -1;
    }
    *out = storage_state;
    return 0;
}

const char *a90_storage_root(void) {
    return storage_state.root;
}

const char *a90_storage_backend(void) {
    return storage_state.backend;
}

const char *a90_storage_warning(void) {
    return storage_state.warning;
}

bool a90_storage_using_fallback(void) {
    return storage_state.fallback;
}

int a90_storage_cmd_storage(void) {
    a90_console_printf("storage: backend=%s root=%s fallback=%s\r\n",
            storage_state.backend,
            storage_state.root,
            storage_state.fallback ? "yes" : "no");
    a90_console_printf("storage: sd present=%s mounted=%s expected=%s rw=%s uuid=%s\r\n",
            storage_state.sd_present ? "yes" : "no",
            storage_state.sd_mounted ? "yes" : "no",
            storage_state.sd_expected ? "yes" : "no",
            storage_state.sd_rw_ok ? "yes" : "no",
            storage_state.sd_uuid);
    a90_console_printf("storage: expected_uuid=%s id_file=%s\r\n", SD_EXPECTED_UUID, SD_ID_FILE);
    a90_console_printf("storage: detail=%s\r\n", storage_state.detail);
    if (storage_state.warning[0] != '\0') {
        a90_console_printf("storage: warning=%s\r\n", storage_state.warning);
    }
    a90_console_printf("storage: log=%s\r\n", a90_log_path());
    return 0;
}

static int storage_cmd_mountsd_status(void) {
    char node_path[PATH_MAX];
    char line[512];
    char uuid[40];
    bool read_only = false;
    struct statvfs vfs;

    if (storage_get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        a90_console_printf("mountsd: block=%s missing: %s\r\n", SD_BLOCK_NAME, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    a90_console_printf("mountsd: block=%s path=%s fs=%s mount=%s\r\n",
            SD_BLOCK_NAME,
            node_path,
            SD_FS_TYPE,
            SD_MOUNT_POINT);
    if (read_ext4_uuid(node_path, uuid, sizeof(uuid)) == 0) {
        a90_console_printf("mountsd: uuid=%s expected=%s match=%s\r\n",
                uuid,
                SD_EXPECTED_UUID,
                strcmp(uuid, SD_EXPECTED_UUID) == 0 ? "yes" : "no");
    }
    if (!mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        a90_console_printf("mountsd: state=unmounted workspace=%s\r\n", SD_WORKSPACE_DIR);
        return 0;
    }
    a90_console_printf("mountsd: state=mounted mode=%s workspace=%s\r\n",
            read_only ? "ro" : "rw",
            SD_WORKSPACE_DIR);
    a90_console_printf("mountsd: %s", line);
    if (statvfs(SD_MOUNT_POINT, &vfs) == 0 && vfs.f_frsize > 0) {
        unsigned long long total = (unsigned long long)vfs.f_blocks *
                                   (unsigned long long)vfs.f_frsize;
        unsigned long long avail = (unsigned long long)vfs.f_bavail *
                                   (unsigned long long)vfs.f_frsize;

        a90_console_printf("mountsd: size=%lluMB avail=%lluMB\r\n",
                total / (1024ULL * 1024ULL),
                avail / (1024ULL * 1024ULL));
    }
    return 0;
}

int a90_storage_cmd_mountsd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "ro";
    char node_path[PATH_MAX];
    char line[512];
    char uuid[40];
    bool read_only = false;
    bool wants_write;
    unsigned long flags;
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "status") == 0) {
        return storage_cmd_mountsd_status();
    }
    if (strcmp(mode, "off") == 0) {
        if (!mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
            a90_console_printf("mountsd: already unmounted\r\n");
            return 0;
        }
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            a90_console_printf("mountsd: umount %s: %s\r\n",
                    SD_MOUNT_POINT,
                    strerror(saved_errno));
            return -saved_errno;
        }
        storage_state.sd_mounted = false;
        a90_console_printf("mountsd: unmounted %s\r\n", SD_MOUNT_POINT);
        return 0;
    }
    if (strcmp(mode, "ro") != 0 &&
        strcmp(mode, "rw") != 0 &&
        strcmp(mode, "init") != 0) {
        a90_console_printf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }
    wants_write = strcmp(mode, "rw") == 0 || strcmp(mode, "init") == 0;

    ensure_dir("/mnt", 0755);
    ensure_dir(SD_MOUNT_POINT, 0755);
    if (storage_get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        a90_console_printf("mountsd: block=%s missing: %s\r\n", SD_BLOCK_NAME, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    flags = strcmp(mode, "ro") == 0 ? MS_RDONLY : 0;
    if (mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            a90_console_printf("mountsd: remount umount %s: %s\r\n",
                    SD_MOUNT_POINT,
                    strerror(saved_errno));
            return -saved_errno;
        }
    }
    if (mount(node_path, SD_MOUNT_POINT, SD_FS_TYPE, flags, NULL) < 0) {
        int saved_errno = errno;

        a90_console_printf("mountsd: mount %s on %s as %s: %s\r\n",
                node_path,
                SD_MOUNT_POINT,
                SD_FS_TYPE,
                strerror(saved_errno));
        return -saved_errno;
    }
    storage_state.sd_present = true;
    storage_state.sd_mounted = true;
    if (read_ext4_uuid(node_path, uuid, sizeof(uuid)) == 0) {
        snprintf(storage_state.sd_uuid, sizeof(storage_state.sd_uuid), "%s", uuid);
        storage_state.sd_expected = strcmp(uuid, SD_EXPECTED_UUID) == 0;
    } else {
        snprintf(storage_state.sd_uuid, sizeof(storage_state.sd_uuid), "%s", "<read-failed>");
        storage_state.sd_expected = false;
    }
    if (wants_write && !storage_state.sd_expected) {
        (void)umount(SD_MOUNT_POINT);
        storage_state.sd_mounted = false;
        a90_console_printf("mountsd: refused %s uuid=%s expected=%s\r\n",
                mode,
                storage_state.sd_uuid,
                SD_EXPECTED_UUID);
        return -ESTALE;
    }
    a90_console_printf("mountsd: %s ready (%s)\r\n",
            SD_MOUNT_POINT,
            flags & MS_RDONLY ? "ro" : "rw");
    if (wants_write) {
        rc = ensure_sd_workspace();
        if (rc < 0) {
            (void)umount(SD_MOUNT_POINT);
            storage_state.sd_mounted = false;
            return rc;
        }
        if (ensure_sd_identity_marker(storage_state.sd_uuid) < 0) {
            int saved_errno = errno;

            (void)umount(SD_MOUNT_POINT);
            storage_state.sd_mounted = false;
            a90_console_printf("mountsd: identity marker refused: %s\r\n", strerror(saved_errno));
            return -saved_errno;
        }
        if (sd_write_read_probe() < 0) {
            int saved_errno = errno;

            (void)umount(SD_MOUNT_POINT);
            storage_state.sd_mounted = false;
            a90_console_printf("mountsd: rw probe failed: %s\r\n", strerror(saved_errno));
            return -saved_errno;
        }
        storage_state.sd_rw_ok = true;
        (void)a90_log_set_path(SD_NATIVE_LOG_PATH);
        a90_console_printf("mountsd: workspace ready %s\r\n", SD_WORKSPACE_DIR);
    }
    return 0;
}
