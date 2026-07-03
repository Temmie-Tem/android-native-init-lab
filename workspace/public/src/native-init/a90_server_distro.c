#include "a90_server_distro.h"

#include "a90_console.h"
#include "a90_helper.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define A90_D3_TAG "A90D3B"
#define A90_D3_TOKEN "SERVER-DISTRO-D3B-SWITCHROOT"
#define A90_D3_ALLOWED_IMAGE_ROOT "/mnt/sdext/a90/runtime/"
#define A90_D3_ROOT "/mnt/sdext/a90/runtime/distro-root"
#define A90_D3_LOOP "/dev/loop0"
#define A90_D3_BUSYBOX "/bin/busybox"
#define A90_D3_INIT "/sbin/init"
#define A90_D3_SWITCH_TIMEOUT_MS 30000

static int d3_hex64_valid(const char *s) {
    size_t n = 0;

    if (s == NULL) {
        return 0;
    }
    for (; s[n] != '\0'; ++n) {
        char c = s[n];
        int ok = (c >= '0' && c <= '9') ||
                 (c >= 'a' && c <= 'f') ||
                 (c >= 'A' && c <= 'F');
        if (!ok) {
            return 0;
        }
    }
    return n == 64;
}

static int d3_sha_equal_ci(const char *a, const char *b) {
    int i;

    if (a == NULL || b == NULL) {
        return 0;
    }
    for (i = 0; i < 64; ++i) {
        char ca = a[i];
        char cb = b[i];

        if (ca >= 'A' && ca <= 'Z') {
            ca = (char)(ca + 32);
        }
        if (cb >= 'A' && cb <= 'Z') {
            cb = (char)(cb + 32);
        }
        if (ca == '\0' || ca != cb) {
            return 0;
        }
    }
    return a[64] == '\0' && b[64] == '\0';
}

static int d3_path_clean(const char *path) {
    const char *c;
    size_t root_len;

    if (path == NULL || path[0] == '\0') {
        return 0;
    }
    root_len = strlen(A90_D3_ALLOWED_IMAGE_ROOT);
    if (strncmp(path, A90_D3_ALLOWED_IMAGE_ROOT, root_len) != 0 ||
        path[root_len] == '\0') {
        return 0;
    }
    if (strstr(path, "..") != NULL) {
        return 0;
    }
    for (c = path; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t') {
            return 0;
        }
    }
    return 1;
}

static int d3_mkdir_p(const char *path, mode_t mode) {
    char tmp[PATH_MAX];
    size_t len;
    char *cursor;

    if (path == NULL || path[0] != '/') {
        return -EINVAL;
    }
    len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return -ENAMETOOLONG;
    }
    memcpy(tmp, path, len + 1);
    for (cursor = tmp + 1; *cursor != '\0'; ++cursor) {
        if (*cursor != '/') {
            continue;
        }
        *cursor = '\0';
        if (mkdir(tmp, mode) < 0 && errno != EEXIST) {
            return -errno;
        }
        *cursor = '/';
    }
    if (mkdir(tmp, mode) < 0 && errno != EEXIST) {
        return -errno;
    }
    return 0;
}

static int d3_regular_file_ok(const char *path) {
    int fd;
    struct stat st;
    int saved_errno;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s open=fail path=%s errno=%d (%s)\r\n",
                           A90_D3_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (!S_ISREG(st.st_mode) || st.st_size <= 0) {
        a90_console_printf("%s stop=not-regular-or-empty path=%s\r\n", A90_D3_TAG, path);
        return -EINVAL;
    }
    return 0;
}

static int d3_path_is_mounted(const char *mountpoint) {
    FILE *fp;
    char source[PATH_MAX];
    char target[PATH_MAX];
    char fstype[64];
    int mounted = 0;

    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fscanf(fp, "%1023s %1023s %63s %*s %*d %*d\n", source, target, fstype) == 3) {
        (void)source;
        (void)fstype;
        if (strcmp(target, mountpoint) == 0) {
            mounted = 1;
            break;
        }
    }
    fclose(fp);
    return mounted;
}

static int d3_read_loop_major(unsigned int *major_out) {
    FILE *fp;
    unsigned int major_num = 0;
    char name[64];
    char line[256];

    if (major_out == NULL) {
        return -EINVAL;
    }
    fp = fopen("/proc/devices", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (sscanf(line, " %u %63s", &major_num, name) != 2) {
            continue;
        }
        if (strcmp(name, "loop") == 0) {
            *major_out = major_num;
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    return -ENOENT;
}

static int d3_ensure_loop_node(bool *created_out) {
    struct stat st;
    unsigned int loop_major = 0;
    int rc;

    if (created_out != NULL) {
        *created_out = false;
    }
    if (lstat(A90_D3_LOOP, &st) == 0) {
        if (!S_ISBLK(st.st_mode)) {
            return -EINVAL;
        }
        return 0;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    rc = d3_read_loop_major(&loop_major);
    if (rc < 0) {
        return rc;
    }
    if (mknod(A90_D3_LOOP, S_IFBLK | 0600, makedev(loop_major, 0)) < 0) {
        return -errno;
    }
    if (created_out != NULL) {
        *created_out = true;
    }
    a90_console_printf("%s loop_node_created=1 major=%u node=%s\r\n",
                       A90_D3_TAG, loop_major, A90_D3_LOOP);
    return 0;
}

static int d3_run_busybox(char *const argv[], int timeout_ms) {
    struct a90_run_config config;
    struct a90_run_result result;
    pid_t pid = -1;
    int rc;

    memset(&config, 0, sizeof(config));
    config.tag = "server-distro-d3";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_CONSOLE;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 2000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        return rc;
    }
    return a90_run_result_to_rc(&result);
}

static int d3_attach_loop(const char *image, bool *attached_out) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"losetup",
        (char *)A90_D3_LOOP,
        (char *)image,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    if (rc != 0) {
        a90_console_printf("%s losetup=fail rc=%d\r\n", A90_D3_TAG, rc);
        return rc > 0 ? -EIO : rc;
    }
    if (attached_out != NULL) {
        *attached_out = true;
    }
    a90_console_printf("%s loop=attached node=%s image=%s\r\n",
                       A90_D3_TAG, A90_D3_LOOP, image);
    return 0;
}

static int d3_detach_loop(void) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"losetup",
        (char *)"-d",
        (char *)A90_D3_LOOP,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    return rc == 0 ? 0 : -EIO;
}

static int d3_mount_root(void) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"mount",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-o",
        (char *)"rw",
        (char *)A90_D3_LOOP,
        (char *)A90_D3_ROOT,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    if (rc != 0) {
        a90_console_printf("%s mount=fail rc=%d root=%s\r\n", A90_D3_TAG, rc, A90_D3_ROOT);
        return rc > 0 ? -EIO : rc;
    }
    a90_console_printf("%s rootfs=mounted root=%s loop=%s\r\n",
                       A90_D3_TAG, A90_D3_ROOT, A90_D3_LOOP);
    return 0;
}

static int d3_join(char *out, size_t out_size, const char *root, const char *leaf) {
    int n = snprintf(out, out_size, "%s/%s", root, leaf);

    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int d3_check_distro_init(void) {
    char init_path[PATH_MAX];
    struct stat st;
    int rc = d3_join(init_path, sizeof(init_path), A90_D3_ROOT, "sbin/init");

    if (rc < 0) {
        return rc;
    }
    if (stat(init_path, &st) < 0) {
        return -errno;
    }
    if (!S_ISREG(st.st_mode) || (st.st_mode & 0111) == 0) {
        return -EINVAL;
    }
    a90_console_printf("%s distro_init=ok path=%s mode=%o\r\n",
                       A90_D3_TAG, init_path, (unsigned int)(st.st_mode & 0777));
    return 0;
}

static int d3_move_mount_one(const char *src, const char *leaf) {
    char dst[PATH_MAX];
    int rc = d3_join(dst, sizeof(dst), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount(src, dst, NULL, MS_MOVE, NULL) < 0) {
        return -errno;
    }
    a90_console_printf("%s mount_move=%s->%s ok=1\r\n", A90_D3_TAG, src, dst);
    return 0;
}

static int d3_ensure_char_node_at(const char *path, mode_t mode, unsigned int maj, unsigned int min) {
    struct stat st;
    dev_t dev = makedev(maj, min);

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == dev) {
            (void)chmod(path, mode);
            return 0;
        }
        if (unlink(path) < 0) {
            return -errno;
        }
    } else if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(path, S_IFCHR | mode, dev) < 0) {
        return -errno;
    }
    (void)chmod(path, mode);
    return 0;
}

static int d3_prepare_dev_node(const char *leaf, mode_t mode, unsigned int maj, unsigned int min) {
    char path[PATH_MAX];
    int rc = d3_join(path, sizeof(path), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    return d3_ensure_char_node_at(path, mode, maj, min);
}

static int d3_prepare_optional_ttygs0(void) {
    struct stat st;

    if (stat("/dev/ttyGS0", &st) < 0) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 missing errno=%d\r\n",
                           A90_D3_TAG, errno);
        return 0;
    }
    if (!S_ISCHR(st.st_mode)) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 not-char\r\n", A90_D3_TAG);
        return 0;
    }
    return d3_prepare_dev_node("dev/ttyGS0", 0600, major(st.st_rdev), minor(st.st_rdev));
}

static int d3_prepare_new_dev(bool *mounted_devpts) {
    char dev_dir[PATH_MAX];
    char pts_dir[PATH_MAX];
    int rc;

    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    rc = d3_join(dev_dir, sizeof(dev_dir), A90_D3_ROOT, "dev");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dev_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/console", 0600, 5, 1);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/tty", 0666, 5, 0);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/ptmx", 0666, 5, 2);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/null", 0666, 1, 3);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/zero", 0666, 1, 5);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/random", 0666, 1, 8);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/urandom", 0666, 1, 9);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_optional_ttygs0();
    if (rc < 0) {
        return rc;
    }
    rc = d3_join(pts_dir, sizeof(pts_dir), A90_D3_ROOT, "dev/pts");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(pts_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount("devpts", pts_dir, "devpts", 0, "mode=620,ptmxmode=666") == 0) {
        if (mounted_devpts != NULL) {
            *mounted_devpts = true;
        }
        a90_console_printf("%s devpts=mounted path=%s\r\n", A90_D3_TAG, pts_dir);
    } else {
        a90_console_printf("%s devpts=warn rc=-%d (%s)\r\n",
                           A90_D3_TAG, errno, strerror(errno));
    }
    a90_console_printf("%s dev_mountpoint=0 dev_nodes=prepared root=%s\r\n",
                       A90_D3_TAG, dev_dir);
    return 0;
}

static void d3_restore_mount_one(const char *leaf, const char *dst) {
    char src[PATH_MAX];

    if (d3_join(src, sizeof(src), A90_D3_ROOT, leaf) < 0) {
        return;
    }
    (void)mount(src, dst, NULL, MS_MOVE, NULL);
}

static void d3_unmount_leaf(const char *leaf) {
    char path[PATH_MAX];

    if (d3_join(path, sizeof(path), A90_D3_ROOT, leaf) < 0) {
        return;
    }
    (void)umount2(path, MNT_DETACH);
}

static int d3_move_core_mounts(bool *moved_proc,
                               bool *moved_sys,
                               bool *moved_dev,
                               bool *mounted_devpts) {
    int dev_mounted;
    int rc;

    if (moved_proc != NULL) {
        *moved_proc = false;
    }
    if (moved_sys != NULL) {
        *moved_sys = false;
    }
    if (moved_dev != NULL) {
        *moved_dev = false;
    }
    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    dev_mounted = d3_path_is_mounted("/dev");
    if (dev_mounted < 0) {
        return dev_mounted;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        return -errno;
    }
    rc = d3_move_mount_one("/proc", "proc");
    if (rc < 0) {
        return rc;
    }
    if (moved_proc != NULL) {
        *moved_proc = true;
    }
    rc = d3_move_mount_one("/sys", "sys");
    if (rc < 0) {
        d3_restore_mount_one("proc", "/proc");
        return rc;
    }
    if (moved_sys != NULL) {
        *moved_sys = true;
    }
    if (dev_mounted) {
        rc = d3_move_mount_one("/dev", "dev");
        if (rc < 0) {
            d3_restore_mount_one("sys", "/sys");
            d3_restore_mount_one("proc", "/proc");
            return rc;
        }
        if (moved_dev != NULL) {
            *moved_dev = true;
        }
    } else {
        rc = d3_prepare_new_dev(mounted_devpts);
        if (rc < 0) {
            d3_restore_mount_one("sys", "/sys");
            d3_restore_mount_one("proc", "/proc");
            return rc;
        }
    }
    return 0;
}

static void d3_restore_core_mounts(bool moved_proc, bool moved_sys, bool moved_dev, bool mounted_devpts) {
    if (mounted_devpts) {
        d3_unmount_leaf("dev/pts");
    }
    if (moved_dev) {
        d3_restore_mount_one("dev", "/dev");
    }
    if (moved_sys) {
        d3_restore_mount_one("sys", "/sys");
    }
    if (moved_proc) {
        d3_restore_mount_one("proc", "/proc");
    }
}

int a90_server_distro_switch_root_cmd(char **argv, int argc) {
    const char *image;
    const char *expected_sha;
    char actual_sha[65];
    int rc;
    bool loop_created = false;
    bool loop_attached = false;
    bool root_mounted = false;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_devpts = false;
    int mounted;
    char *const newenv[] = {
        (char *)"HOME=/root",
        (char *)"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
        (char *)"TERM=linux",
        NULL,
    };
    char *const switch_argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"switch_root",
        (char *)A90_D3_ROOT,
        (char *)A90_D3_INIT,
        NULL,
    };

    if (argc != 4 || strcmp(argv[1], A90_D3_TOKEN) != 0) {
        a90_console_printf("usage: switch-root-to-distro %s <image> <sha256>\r\n",
                           A90_D3_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D3_TAG, argc);
        return -EPERM;
    }
    image = argv[2];
    expected_sha = argv[3];
    if (!d3_path_clean(image)) {
        a90_console_printf("%s refused=path-outside-approved-sd-runtime image=%s\r\n",
                           A90_D3_TAG, image);
        return -EPERM;
    }
    if (!d3_hex64_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", A90_D3_TAG);
        return -EINVAL;
    }

    a90_console_printf("%s begin image=%s root=%s\r\n", A90_D3_TAG, image, A90_D3_ROOT);
    rc = d3_regular_file_ok(image);
    if (rc < 0) {
        return rc;
    }
    if (a90_helper_sha256_file(image, actual_sha, sizeof(actual_sha)) != 0) {
        a90_console_printf("%s sha=compute-fail\r\n", A90_D3_TAG);
        return -EIO;
    }
    if (!d3_sha_equal_ci(actual_sha, expected_sha)) {
        a90_console_printf("%s sha=%s expected_sha_match=0 stop=sha-mismatch\r\n",
                           A90_D3_TAG, actual_sha);
        return -EPERM;
    }
    a90_console_printf("%s sha=%s expected_sha_match=1\r\n", A90_D3_TAG, actual_sha);

    rc = d3_mkdir_p(A90_D3_ROOT, 0755);
    if (rc < 0) {
        a90_console_printf("%s mkdir_root=fail rc=%d root=%s\r\n", A90_D3_TAG, rc, A90_D3_ROOT);
        return rc;
    }
    mounted = d3_path_is_mounted(A90_D3_ROOT);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s stop=root-already-mounted root=%s\r\n", A90_D3_TAG, A90_D3_ROOT);
        return -EBUSY;
    }
    rc = d3_ensure_loop_node(&loop_created);
    if (rc < 0) {
        a90_console_printf("%s loop_node=fail rc=%d\r\n", A90_D3_TAG, rc);
        return rc;
    }
    rc = d3_attach_loop(image, &loop_attached);
    if (rc < 0) {
        goto fail_before_move;
    }
    rc = d3_mount_root();
    if (rc < 0) {
        goto fail_before_move;
    }
    root_mounted = true;
    rc = d3_check_distro_init();
    if (rc < 0) {
        a90_console_printf("%s stop=distro-init-invalid rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }
    rc = d3_move_core_mounts(&moved_proc, &moved_sys, &moved_dev, &mounted_devpts);
    if (rc < 0) {
        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s console=reuse-stdio\r\n",
                       A90_D3_TAG, A90_D3_BUSYBOX, A90_D3_ROOT, A90_D3_INIT);
    a90_logf("server-distro", "D3 switch_root exec image=%s root=%s", image, A90_D3_ROOT);
    sync();
    usleep(200000);
    execve(A90_D3_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D3_TAG, rc, -rc, strerror(-rc));
    d3_restore_core_mounts(moved_proc, moved_sys, moved_dev, mounted_devpts);
    return rc;

fail_before_move:
    if (root_mounted) {
        if (umount2(A90_D3_ROOT, MNT_DETACH) == 0) {
            a90_console_printf("%s rootfs=unmounted-after-fail root=%s\r\n",
                               A90_D3_TAG, A90_D3_ROOT);
        }
    }
    if (loop_attached) {
        (void)d3_detach_loop();
    }
    if (loop_created) {
        (void)unlink(A90_D3_LOOP);
    }
    return rc;
}

#define A90_D4_TAG "A90D4"
#define A90_D4_TOKEN "SERVER-DISTRO-D4-USERDATA-APPLIANCE"
#define A90_D4_ALLOWED_SOURCE_ROOT "/mnt/sdext/a90/runtime/"
#define A90_D4_NODE "/dev/block/a90-userdata"
#define A90_D4_ROOT "/mnt/a90-userdata-root"
#define A90_D4_BUSYBOX "/bin/busybox"
#define A90_D4_INIT "/sbin/init"
#define A90_D4_MARKER_LEAF "etc/a90-appliance-stage"
#define A90_D4_MARKER_VALUE "userdata=appliance-root"
#define A90_D4_MIN_BYTES 100000000000ULL
#define A90_D4_MAX_BYTES 140000000000ULL
#define A90_D4_EXPECTED_PARTNAME "userdata"
#define A90_D4_FORMAT_TIMEOUT_MS 120000
#define A90_D4_POPULATE_TIMEOUT_MS 300000
#define A90_D4_SWITCH_TIMEOUT_MS 30000
#define A90_D4_FORMATTER_PROBE_MIN_BYTES 4194304ULL
#define A90_D4_FORMATTER_PROBE_MAX_BYTES 67108864ULL
#define A90_D4_EXT4_MAGIC_OFFSET 1080

struct d4_userdata_target {
    char sysname[64];
    char devname[128];
    unsigned int major_num;
    unsigned int minor_num;
    unsigned long long sectors;
    unsigned long long bytes;
    int ro;
    int mounted;
    int node_exists;
    int byname_exists;
    int byname_matches;
};

static const char *const d4_forbidden_names[] = {
    "efs",
    "sec_efs",
    "modem",
    "rpmb",
    "keymaster",
    "vbmeta",
    "dsp",
    "keydata",
    "keyrefuge",
    "bootloader",
    "persist",
    "gpt",
    NULL,
};

static int d4_has_forbidden_name(const char *s) {
    int i;

    if (s == NULL) {
        return 0;
    }
    for (i = 0; d4_forbidden_names[i] != NULL; ++i) {
        if (strstr(s, d4_forbidden_names[i]) != NULL) {
            return 1;
        }
    }
    return 0;
}

static int d4_copy_value(char *dst, size_t dst_size, const char *src) {
    size_t len;

    if (dst == NULL || dst_size == 0 || src == NULL) {
        return -EINVAL;
    }
    len = strlen(src);
    while (len > 0 && (src[len - 1] == '\n' || src[len - 1] == '\r')) {
        --len;
    }
    if (len >= dst_size) {
        return -ENAMETOOLONG;
    }
    memcpy(dst, src, len);
    dst[len] = '\0';
    return 0;
}

static int d4_parse_uint(const char *s, unsigned int *out) {
    char *end = NULL;
    unsigned long value;

    if (s == NULL || out == NULL || s[0] == '\0') {
        return -EINVAL;
    }
    errno = 0;
    value = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || value > 0xffffffffUL) {
        return -EINVAL;
    }
    *out = (unsigned int)value;
    return 0;
}

static int d4_parse_u64(const char *s, unsigned long long *out) {
    char *end = NULL;
    unsigned long long value;

    if (s == NULL || out == NULL || s[0] == '\0') {
        return -EINVAL;
    }
    errno = 0;
    value = strtoull(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0') {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static int d4_read_trimmed_file(const char *path, char *out, size_t out_size) {
    FILE *fp;
    char line[256];

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -errno;
    }
    if (fgets(line, sizeof(line), fp) == NULL) {
        int rc = ferror(fp) ? -errno : -EINVAL;
        fclose(fp);
        return rc;
    }
    fclose(fp);
    return d4_copy_value(out, out_size, line);
}

static int d4_join_root(char *out, size_t out_size, const char *leaf) {
    int n = snprintf(out, out_size, "%s/%s", A90_D4_ROOT, leaf);

    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int d4_source_path_clean(const char *path) {
    const char *c;
    size_t root_len;

    if (path == NULL || path[0] == '\0') {
        return 0;
    }
    root_len = strlen(A90_D4_ALLOWED_SOURCE_ROOT);
    if (strncmp(path, A90_D4_ALLOWED_SOURCE_ROOT, root_len) != 0 ||
        path[root_len] == '\0') {
        return 0;
    }
    if (strstr(path, "..") != NULL) {
        return 0;
    }
    for (c = path; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t') {
            return 0;
        }
    }
    return 1;
}

static int d4_regular_file_ok(const char *path) {
    int fd;
    struct stat st;
    int saved_errno;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s open=fail path=%s errno=%d (%s)\r\n",
                           A90_D4_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (!S_ISREG(st.st_mode) || st.st_size <= 0) {
        a90_console_printf("%s stop=not-regular-or-empty path=%s\r\n", A90_D4_TAG, path);
        return -EINVAL;
    }
    return 0;
}

static int d4_create_probe_file(const char *path, unsigned long long size_bytes) {
    int fd;
    int saved_errno;

    fd = open(path, O_RDWR | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s formatter-probe=create-fail path=%s errno=%d (%s)\r\n",
                           A90_D4_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (ftruncate(fd, (off_t)size_bytes) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    if (fsync(fd) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    a90_console_printf("%s formatter-probe=file-created path=%s size_bytes=%llu\r\n",
                       A90_D4_TAG, path, size_bytes);
    return 0;
}

static int d4_check_ext4_magic(const char *path) {
    unsigned char magic[2] = { 0, 0 };
    int fd;
    int saved_errno;
    ssize_t n;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        return -saved_errno;
    }
    n = pread(fd, magic, sizeof(magic), A90_D4_EXT4_MAGIC_OFFSET);
    if (n < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (n != (ssize_t)sizeof(magic) || magic[0] != 0x53 || magic[1] != 0xef) {
        a90_console_printf("%s formatter-probe=bad-ext4-magic read=%zd magic=%02x%02x\r\n",
                           A90_D4_TAG, n, magic[0], magic[1]);
        return -EINVAL;
    }
    a90_console_printf("%s formatter-probe=ext4-magic-ok magic=53ef offset=%d\r\n",
                       A90_D4_TAG, A90_D4_EXT4_MAGIC_OFFSET);
    return 0;
}

static int d4_marker_clean(const char *value) {
    const char *c;

    if (value == NULL || value[0] == '\0') {
        return 0;
    }
    for (c = value; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t' || *c == '/') {
            return 0;
        }
    }
    return 1;
}

static int d4_run_busybox(char *const argv[], int timeout_ms) {
    struct a90_run_config config;
    struct a90_run_result result;
    pid_t pid = -1;
    int rc;

    memset(&config, 0, sizeof(config));
    config.tag = "server-distro-d4";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_CONSOLE;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 2000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        return rc;
    }
    return a90_run_result_to_rc(&result);
}

static int d4_parse_uevent(const char *path,
                           struct d4_userdata_target *target,
                           int *is_userdata_out) {
    FILE *fp;
    char line[256];
    char partname[128] = "";
    int saw_devname = 0;
    int saw_major = 0;
    int saw_minor = 0;

    if (target == NULL || is_userdata_out == NULL) {
        return -EINVAL;
    }
    *is_userdata_out = 0;
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, "DEVNAME=", 8) == 0) {
            if (d4_copy_value(target->devname, sizeof(target->devname), line + 8) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_devname = 1;
        } else if (strncmp(line, "MAJOR=", 6) == 0) {
            char value[32];
            if (d4_copy_value(value, sizeof(value), line + 6) < 0 ||
                d4_parse_uint(value, &target->major_num) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_major = 1;
        } else if (strncmp(line, "MINOR=", 6) == 0) {
            char value[32];
            if (d4_copy_value(value, sizeof(value), line + 6) < 0 ||
                d4_parse_uint(value, &target->minor_num) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_minor = 1;
        } else if (strncmp(line, "PARTNAME=", 9) == 0) {
            if (d4_copy_value(partname, sizeof(partname), line + 9) < 0) {
                fclose(fp);
                return -EINVAL;
            }
        }
    }
    if (ferror(fp)) {
        int rc = -errno;
        fclose(fp);
        return rc;
    }
    fclose(fp);
    if (strcmp(partname, A90_D4_EXPECTED_PARTNAME) != 0) {
        return 0;
    }
    if (!saw_devname || !saw_major || !saw_minor) {
        return -EINVAL;
    }
    *is_userdata_out = 1;
    return 0;
}

static int d4_read_target_shape(struct d4_userdata_target *target) {
    char path[PATH_MAX];
    char value[64];
    unsigned long long sectors;
    unsigned int ro_value;
    int n;
    int rc;

    n = snprintf(path, sizeof(path), "/sys/class/block/%s/size", target->sysname);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    rc = d4_read_trimmed_file(path, value, sizeof(value));
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_u64(value, &sectors);
    if (rc < 0) {
        return rc;
    }
    n = snprintf(path, sizeof(path), "/sys/class/block/%s/ro", target->sysname);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    rc = d4_read_trimmed_file(path, value, sizeof(value));
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_uint(value, &ro_value);
    if (rc < 0) {
        return rc;
    }
    if (sectors > 0xffffffffffffffffULL / 512ULL) {
        return -EOVERFLOW;
    }
    target->sectors = sectors;
    target->bytes = sectors * 512ULL;
    target->ro = ro_value != 0;
    return 0;
}

static int d4_block_node_matches(const char *path, const struct d4_userdata_target *target, int *matches_out) {
    struct stat st;
    dev_t wanted;

    if (matches_out == NULL || target == NULL) {
        return -EINVAL;
    }
    *matches_out = 0;
    if (stat(path, &st) < 0) {
        return -errno;
    }
    wanted = makedev(target->major_num, target->minor_num);
    if (S_ISBLK(st.st_mode) && st.st_rdev == wanted) {
        *matches_out = 1;
    }
    return 0;
}

static int d4_path_mounted_as_target(const char *source,
                                     const char *mountpoint,
                                     const struct d4_userdata_target *target) {
    int matches = 0;

    if (strcmp(mountpoint, A90_D4_ROOT) == 0) {
        return 1;
    }
    if (strcmp(source, A90_D4_NODE) == 0) {
        return 1;
    }
    if (source[0] == '/' && d4_block_node_matches(source, target, &matches) == 0 && matches) {
        return 1;
    }
    return 0;
}

static int d4_target_is_mounted(const struct d4_userdata_target *target) {
    FILE *fp;
    char source[PATH_MAX];
    char mountpoint[PATH_MAX];
    char fstype[64];
    int mounted = 0;

    if (target == NULL) {
        return -EINVAL;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fscanf(fp, "%1023s %1023s %63s %*s %*d %*d\n", source, mountpoint, fstype) == 3) {
        (void)fstype;
        if (d4_path_mounted_as_target(source, mountpoint, target)) {
            mounted = 1;
            break;
        }
    }
    fclose(fp);
    return mounted;
}

static int d4_check_optional_byname(struct d4_userdata_target *target) {
    struct stat st;
    int rc;
    int matches = 0;

    target->byname_exists = 0;
    target->byname_matches = 0;
    rc = lstat("/dev/block/by-name/userdata", &st);
    if (rc < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    target->byname_exists = 1;
    rc = d4_block_node_matches("/dev/block/by-name/userdata", target, &matches);
    if (rc < 0) {
        return rc;
    }
    target->byname_matches = matches;
    return matches ? 0 : -EPERM;
}

static int d4_check_private_node(struct d4_userdata_target *target) {
    struct stat st;
    dev_t wanted = makedev(target->major_num, target->minor_num);

    target->node_exists = 0;
    if (lstat(A90_D4_NODE, &st) < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    target->node_exists = 1;
    if (!S_ISBLK(st.st_mode) || st.st_rdev != wanted) {
        return -EPERM;
    }
    return 0;
}

static int d4_resolve_userdata(struct d4_userdata_target *target) {
    DIR *dir;
    struct dirent *entry;
    struct d4_userdata_target found;
    int found_count = 0;
    int rc = 0;

    if (target == NULL) {
        return -EINVAL;
    }
    memset(target, 0, sizeof(*target));
    memset(&found, 0, sizeof(found));
    dir = opendir("/sys/class/block");
    if (dir == NULL) {
        return -errno;
    }
    while ((entry = readdir(dir)) != NULL) {
        char uevent_path[PATH_MAX];
        struct d4_userdata_target candidate;
        int is_userdata = 0;
        int n;

        if (entry->d_name[0] == '.') {
            continue;
        }
        memset(&candidate, 0, sizeof(candidate));
        if (d4_copy_value(candidate.sysname, sizeof(candidate.sysname), entry->d_name) < 0) {
            rc = -EINVAL;
            break;
        }
        n = snprintf(uevent_path, sizeof(uevent_path),
                     "/sys/class/block/%s/uevent", entry->d_name);
        if (n < 0 || (size_t)n >= sizeof(uevent_path)) {
            rc = -ENAMETOOLONG;
            break;
        }
        rc = d4_parse_uevent(uevent_path, &candidate, &is_userdata);
        if (rc < 0) {
            break;
        }
        if (!is_userdata) {
            continue;
        }
        ++found_count;
        if (found_count == 1) {
            found = candidate;
        }
    }
    closedir(dir);
    if (rc < 0) {
        return rc;
    }
    if (found_count != 1) {
        a90_console_printf("%s stop=userdata-partname-count count=%d\r\n", A90_D4_TAG, found_count);
        return -ENOENT;
    }
    rc = d4_read_target_shape(&found);
    if (rc < 0) {
        return rc;
    }
    if (found.ro) {
        a90_console_printf("%s stop=target-readonly devname=%s\r\n", A90_D4_TAG, found.devname);
        return -EROFS;
    }
    if (found.bytes < A90_D4_MIN_BYTES || found.bytes > A90_D4_MAX_BYTES) {
        a90_console_printf("%s stop=size-out-of-range bytes=%llu\r\n", A90_D4_TAG, found.bytes);
        return -ERANGE;
    }
    if (d4_has_forbidden_name(found.sysname) || d4_has_forbidden_name(found.devname)) {
        a90_console_printf("%s stop=forbidden-name devname=%s sysname=%s\r\n",
                           A90_D4_TAG, found.devname, found.sysname);
        return -EPERM;
    }
    rc = d4_check_optional_byname(&found);
    if (rc < 0) {
        a90_console_printf("%s stop=byname-mismatch-or-broken rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_check_private_node(&found);
    if (rc < 0) {
        a90_console_printf("%s stop=private-node-mismatch node=%s rc=%d\r\n",
                           A90_D4_TAG, A90_D4_NODE, rc);
        return rc;
    }
    rc = d4_target_is_mounted(&found);
    if (rc < 0) {
        return rc;
    }
    found.mounted = rc;
    *target = found;
    return 0;
}

static void d4_print_target(const struct d4_userdata_target *target, const char *phase) {
    a90_console_printf(
        "%s %s target.source=partname-scan target.devname=%s target.sysname=%s "
        "target.dev=%u:%u target.sectors=%llu target.size_bytes=%llu "
        "target.ro=%d target.mounted=%d target.node=%s target.node_exists=%d "
        "target.byname_exists=%d target.byname_matches=%d\r\n",
        A90_D4_TAG,
        phase,
        target->devname,
        target->sysname,
        target->major_num,
        target->minor_num,
        target->sectors,
        target->bytes,
        target->ro,
        target->mounted,
        A90_D4_NODE,
        target->node_exists,
        target->byname_exists,
        target->byname_matches);
}

static int d4_parse_expected_dev(const char *s, unsigned int *major_out, unsigned int *minor_out) {
    char *end = NULL;
    unsigned long major_value;
    unsigned long minor_value;

    if (s == NULL || major_out == NULL || minor_out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    major_value = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != ':' || major_value > 0xffffffffUL) {
        return -EINVAL;
    }
    ++end;
    errno = 0;
    minor_value = strtoul(end, &end, 10);
    if (errno != 0 || *end != '\0' || minor_value > 0xffffffffUL) {
        return -EINVAL;
    }
    *major_out = (unsigned int)major_value;
    *minor_out = (unsigned int)minor_value;
    return 0;
}

static int d4_compare_expected(const struct d4_userdata_target *target,
                               const char *expected_devname,
                               const char *expected_dev,
                               const char *expected_sectors) {
    unsigned int expected_major = 0;
    unsigned int expected_minor = 0;
    unsigned long long sectors = 0;
    int rc;

    rc = d4_parse_expected_dev(expected_dev, &expected_major, &expected_minor);
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_u64(expected_sectors, &sectors);
    if (rc < 0) {
        return rc;
    }
    if (strcmp(target->devname, expected_devname) != 0 ||
        target->major_num != expected_major ||
        target->minor_num != expected_minor ||
        target->sectors != sectors) {
        a90_console_printf("%s stop=expected-identity-mismatch expected_devname=%s "
                           "expected_dev=%s expected_sectors=%s\r\n",
                           A90_D4_TAG, expected_devname, expected_dev, expected_sectors);
        d4_print_target(target, "actual");
        return -EPERM;
    }
    return 0;
}

static int d4_ensure_userdata_node(const struct d4_userdata_target *target) {
    struct stat st;
    dev_t wanted = makedev(target->major_num, target->minor_num);
    int rc;

    rc = d3_mkdir_p("/dev/block", 0755);
    if (rc < 0) {
        return rc;
    }
    if (lstat(A90_D4_NODE, &st) == 0) {
        if (S_ISBLK(st.st_mode) && st.st_rdev == wanted) {
            (void)chmod(A90_D4_NODE, 0600);
            a90_console_printf("%s node=exists-ok path=%s dev=%u:%u\r\n",
                               A90_D4_TAG, A90_D4_NODE,
                               target->major_num, target->minor_num);
            return 0;
        }
        a90_console_printf("%s stop=node-exists-wrong path=%s\r\n", A90_D4_TAG, A90_D4_NODE);
        return -EPERM;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(A90_D4_NODE, S_IFBLK | 0600, wanted) < 0) {
        return -errno;
    }
    a90_console_printf("%s node=created path=%s dev=%u:%u\r\n",
                       A90_D4_TAG, A90_D4_NODE,
                       target->major_num, target->minor_num);
    return 0;
}

static int d4_mount_userdata_root(void) {
    char *const argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"mount",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-o",
        (char *)"rw",
        (char *)A90_D4_NODE,
        (char *)A90_D4_ROOT,
        NULL,
    };
    int mounted;
    int rc;

    rc = d3_mkdir_p(A90_D4_ROOT, 0755);
    if (rc < 0) {
        return rc;
    }
    mounted = d3_path_is_mounted(A90_D4_ROOT);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s rootfs=already-mounted root=%s\r\n", A90_D4_TAG, A90_D4_ROOT);
        return 0;
    }
    rc = d4_run_busybox(argv, A90_D4_SWITCH_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s mount=fail rc=%d root=%s node=%s\r\n",
                           A90_D4_TAG, rc, A90_D4_ROOT, A90_D4_NODE);
        return rc > 0 ? -EIO : rc;
    }
    a90_console_printf("%s rootfs=mounted root=%s node=%s\r\n",
                       A90_D4_TAG, A90_D4_ROOT, A90_D4_NODE);
    return 0;
}

static int d4_check_userdata_init(void) {
    char init_path[PATH_MAX];
    struct stat st;
    int rc = d4_join_root(init_path, sizeof(init_path), "sbin/init");

    if (rc < 0) {
        return rc;
    }
    if (stat(init_path, &st) < 0) {
        return -errno;
    }
    if (!S_ISREG(st.st_mode) || (st.st_mode & 0111) == 0) {
        return -EINVAL;
    }
    a90_console_printf("%s appliance_init=ok path=%s mode=%o\r\n",
                       A90_D4_TAG, init_path, (unsigned int)(st.st_mode & 0777));
    return 0;
}

static int d4_write_marker(void) {
    char marker_path[PATH_MAX];
    const char payload[] = A90_D4_MARKER_VALUE "\n";
    int fd;
    int rc;

    rc = d4_join_root(marker_path, sizeof(marker_path), A90_D4_MARKER_LEAF);
    if (rc < 0) {
        return rc;
    }
    fd = open(marker_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return -errno;
    }
    if (write(fd, payload, sizeof(payload) - 1) != (ssize_t)(sizeof(payload) - 1)) {
        rc = -errno;
        close(fd);
        return rc == 0 ? -EIO : rc;
    }
    if (fsync(fd) < 0) {
        rc = -errno;
        close(fd);
        return rc;
    }
    close(fd);
    a90_console_printf("%s marker=written path=%s value=%s\r\n",
                       A90_D4_TAG, marker_path, A90_D4_MARKER_VALUE);
    return 0;
}

static int d4_read_marker(char *out, size_t out_size) {
    char marker_path[PATH_MAX];
    int rc = d4_join_root(marker_path, sizeof(marker_path), A90_D4_MARKER_LEAF);

    if (rc < 0) {
        return rc;
    }
    return d4_read_trimmed_file(marker_path, out, out_size);
}

static int d4_move_mount_one(const char *src, const char *leaf) {
    char dst[PATH_MAX];
    int rc = d4_join_root(dst, sizeof(dst), leaf);

    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount(src, dst, NULL, MS_MOVE, NULL) < 0) {
        return -errno;
    }
    a90_console_printf("%s mount_move=%s->%s ok=1\r\n", A90_D4_TAG, src, dst);
    return 0;
}

static int d4_prepare_dev_node(const char *leaf, mode_t mode, unsigned int maj, unsigned int min) {
    char path[PATH_MAX];
    int rc = d4_join_root(path, sizeof(path), leaf);

    if (rc < 0) {
        return rc;
    }
    return d3_ensure_char_node_at(path, mode, maj, min);
}

static int d4_prepare_optional_ttygs0(void) {
    struct stat st;

    if (stat("/dev/ttyGS0", &st) < 0) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 missing errno=%d\r\n",
                           A90_D4_TAG, errno);
        return 0;
    }
    if (!S_ISCHR(st.st_mode)) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 not-char\r\n", A90_D4_TAG);
        return 0;
    }
    return d4_prepare_dev_node("dev/ttyGS0", 0600, major(st.st_rdev), minor(st.st_rdev));
}

static int d4_prepare_new_dev(bool *mounted_devpts) {
    char dev_dir[PATH_MAX];
    char pts_dir[PATH_MAX];
    int rc;

    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    rc = d4_join_root(dev_dir, sizeof(dev_dir), "dev");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dev_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/console", 0600, 5, 1);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/tty", 0666, 5, 0);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/ptmx", 0666, 5, 2);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/null", 0666, 1, 3);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/zero", 0666, 1, 5);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/random", 0666, 1, 8);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/urandom", 0666, 1, 9);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_optional_ttygs0();
    if (rc < 0) {
        return rc;
    }
    rc = d4_join_root(pts_dir, sizeof(pts_dir), "dev/pts");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(pts_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount("devpts", pts_dir, "devpts", 0, "mode=620,ptmxmode=666") == 0) {
        if (mounted_devpts != NULL) {
            *mounted_devpts = true;
        }
        a90_console_printf("%s devpts=mounted path=%s\r\n", A90_D4_TAG, pts_dir);
    } else {
        a90_console_printf("%s devpts=warn rc=-%d (%s)\r\n",
                           A90_D4_TAG, errno, strerror(errno));
    }
    a90_console_printf("%s dev_mountpoint=0 dev_nodes=prepared root=%s\r\n",
                       A90_D4_TAG, dev_dir);
    return 0;
}

static void d4_restore_mount_one(const char *leaf, const char *dst) {
    char src[PATH_MAX];

    if (d4_join_root(src, sizeof(src), leaf) < 0) {
        return;
    }
    (void)mount(src, dst, NULL, MS_MOVE, NULL);
}

static void d4_unmount_leaf(const char *leaf) {
    char path[PATH_MAX];

    if (d4_join_root(path, sizeof(path), leaf) < 0) {
        return;
    }
    (void)umount2(path, MNT_DETACH);
}

static int d4_move_core_mounts(bool *moved_proc,
                               bool *moved_sys,
                               bool *moved_dev,
                               bool *mounted_devpts) {
    int dev_mounted;
    int rc;

    if (moved_proc != NULL) {
        *moved_proc = false;
    }
    if (moved_sys != NULL) {
        *moved_sys = false;
    }
    if (moved_dev != NULL) {
        *moved_dev = false;
    }
    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    dev_mounted = d3_path_is_mounted("/dev");
    if (dev_mounted < 0) {
        return dev_mounted;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        return -errno;
    }
    rc = d4_move_mount_one("/proc", "proc");
    if (rc < 0) {
        return rc;
    }
    if (moved_proc != NULL) {
        *moved_proc = true;
    }
    rc = d4_move_mount_one("/sys", "sys");
    if (rc < 0) {
        d4_restore_mount_one("proc", "/proc");
        return rc;
    }
    if (moved_sys != NULL) {
        *moved_sys = true;
    }
    if (dev_mounted) {
        rc = d4_move_mount_one("/dev", "dev");
        if (rc < 0) {
            d4_restore_mount_one("sys", "/sys");
            d4_restore_mount_one("proc", "/proc");
            return rc;
        }
        if (moved_dev != NULL) {
            *moved_dev = true;
        }
    } else {
        rc = d4_prepare_new_dev(mounted_devpts);
        if (rc < 0) {
            d4_restore_mount_one("sys", "/sys");
            d4_restore_mount_one("proc", "/proc");
            return rc;
        }
    }
    return 0;
}

static void d4_restore_core_mounts(bool moved_proc, bool moved_sys, bool moved_dev, bool mounted_devpts) {
    if (mounted_devpts) {
        d4_unmount_leaf("dev/pts");
    }
    if (moved_dev) {
        d4_restore_mount_one("dev", "/dev");
    }
    if (moved_sys) {
        d4_restore_mount_one("sys", "/sys");
    }
    if (moved_proc) {
        d4_restore_mount_one("proc", "/proc");
    }
}

int a90_server_distro_userdata_preflight_cmd(char **argv, int argc) {
    struct d4_userdata_target target;
    int rc;

    if (argc != 2 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-preflight %s\r\n", A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        a90_console_printf("%s preflight=fail rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    d4_print_target(&target, "preflight");
    a90_console_printf("%s preflight=ok format_allowed=0 node_materialized=0\r\n", A90_D4_TAG);
    return 0;
}

int a90_server_distro_userdata_formatter_probe_cmd(char **argv, int argc) {
    const char *probe_path;
    unsigned long long size_bytes = 0;
    char *probe_argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"mke2fs",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-F",
        (char *)"-L",
        (char *)"A90D4PROBE",
        NULL,
        NULL,
    };
    int rc;
    int cleanup_rc;

    if (argc != 4 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-formatter-probe %s <probe-image> <size-bytes>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    probe_path = argv[2];
    if (!d4_source_path_clean(probe_path)) {
        a90_console_printf("%s refused=probe-path-outside-approved-sd-runtime path=%s\r\n",
                           A90_D4_TAG, probe_path);
        return -EPERM;
    }
    rc = d4_parse_u64(argv[3], &size_bytes);
    if (rc < 0 ||
        size_bytes < A90_D4_FORMATTER_PROBE_MIN_BYTES ||
        size_bytes > A90_D4_FORMATTER_PROBE_MAX_BYTES) {
        a90_console_printf("%s refused=bad-probe-size size=%s min=%llu max=%llu\r\n",
                           A90_D4_TAG, argv[3],
                           A90_D4_FORMATTER_PROBE_MIN_BYTES,
                           A90_D4_FORMATTER_PROBE_MAX_BYTES);
        return -EINVAL;
    }

    rc = d4_create_probe_file(probe_path, size_bytes);
    if (rc < 0) {
        return rc;
    }
    probe_argv[7] = (char *)probe_path;
    a90_console_printf("%s formatter-probe=begin formatter=busybox-mke2fs-ext4 path=%s size_bytes=%llu\r\n",
                       A90_D4_TAG, probe_path, size_bytes);
    rc = d4_run_busybox(probe_argv, A90_D4_FORMAT_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s formatter-probe=fail stage=mke2fs rc=%d\r\n", A90_D4_TAG, rc);
        (void)unlink(probe_path);
        return rc > 0 ? -EIO : rc;
    }
    rc = d4_check_ext4_magic(probe_path);
    if (rc < 0) {
        (void)unlink(probe_path);
        return rc;
    }
    cleanup_rc = unlink(probe_path);
    if (cleanup_rc < 0) {
        rc = -errno;
        a90_console_printf("%s formatter-probe=cleanup-fail path=%s rc=%d\r\n",
                           A90_D4_TAG, probe_path, rc);
        return rc;
    }
    sync();
    a90_console_printf("%s formatter-probe=done formatter=busybox-mke2fs-ext4 path=%s cleanup=ok userdata_touched=0\r\n",
                       A90_D4_TAG, probe_path);
    return 0;
}

int a90_server_distro_userdata_format_cmd(char **argv, int argc) {
    struct d4_userdata_target target;
    char *const format_argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"mke2fs",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-F",
        (char *)"-L",
        (char *)"A90D4ROOT",
        (char *)A90_D4_NODE,
        NULL,
    };
    int rc;

    if (argc != 5 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-format %s <expected-devname> <expected-dev> <expected-sectors>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=resolve rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    d4_print_target(&target, "format-ready-check");
    if (target.mounted) {
        a90_console_printf("%s stop=target-mounted-before-format\r\n", A90_D4_TAG);
        return -EBUSY;
    }
    rc = d4_compare_expected(&target, argv[2], argv[3], argv[4]);
    if (rc < 0) {
        return rc;
    }
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=node rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    a90_console_printf("%s format=begin formatter=busybox-mke2fs-ext4 node=%s\r\n",
                       A90_D4_TAG, A90_D4_NODE);
    rc = d4_run_busybox(format_argv, A90_D4_FORMAT_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s format=fail formatter=busybox-mke2fs-ext4 rc=%d\r\n",
                           A90_D4_TAG, rc);
        return rc > 0 ? -EIO : rc;
    }
    sync();
    a90_console_printf("%s format=done formatter=busybox-mke2fs-ext4 node=%s label=A90D4ROOT\r\n",
                       A90_D4_TAG, A90_D4_NODE);
    return 0;
}

int a90_server_distro_userdata_populate_cmd(char **argv, int argc) {
    const char *source_tar;
    const char *expected_sha;
    char actual_sha[65];
    struct d4_userdata_target target;
    char *tar_argv[7];
    int rc;

    if (argc != 4 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-populate %s <source-tar> <sha256>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    source_tar = argv[2];
    expected_sha = argv[3];
    if (!d4_source_path_clean(source_tar)) {
        a90_console_printf("%s refused=path-outside-approved-sd-runtime source=%s\r\n",
                           A90_D4_TAG, source_tar);
        return -EPERM;
    }
    if (!d3_hex64_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", A90_D4_TAG);
        return -EINVAL;
    }
    rc = d4_regular_file_ok(source_tar);
    if (rc < 0) {
        return rc;
    }
    if (a90_helper_sha256_file(source_tar, actual_sha, sizeof(actual_sha)) != 0) {
        a90_console_printf("%s sha=compute-fail\r\n", A90_D4_TAG);
        return -EIO;
    }
    if (!d3_sha_equal_ci(actual_sha, expected_sha)) {
        a90_console_printf("%s sha=%s expected_sha_match=0 stop=sha-mismatch\r\n",
                           A90_D4_TAG, actual_sha);
        return -EPERM;
    }
    a90_console_printf("%s sha=%s expected_sha_match=1 source=%s\r\n",
                       A90_D4_TAG, actual_sha, source_tar);
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        return rc;
    }
    d4_print_target(&target, "populate-ready-check");
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        return rc;
    }
    rc = d4_mount_userdata_root();
    if (rc < 0) {
        return rc;
    }
    tar_argv[0] = (char *)A90_D4_BUSYBOX;
    tar_argv[1] = (char *)"tar";
    tar_argv[2] = (char *)"-xpf";
    tar_argv[3] = (char *)source_tar;
    tar_argv[4] = (char *)"-C";
    tar_argv[5] = (char *)A90_D4_ROOT;
    tar_argv[6] = NULL;
    a90_console_printf("%s populate=begin source=%s root=%s\r\n",
                       A90_D4_TAG, source_tar, A90_D4_ROOT);
    rc = d4_run_busybox(tar_argv, A90_D4_POPULATE_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s populate=fail stage=tar rc=%d\r\n", A90_D4_TAG, rc);
        return rc > 0 ? -EIO : rc;
    }
    rc = d4_check_userdata_init();
    if (rc < 0) {
        a90_console_printf("%s populate=fail stage=init rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_write_marker();
    if (rc < 0) {
        a90_console_printf("%s populate=fail stage=marker rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    sync();
    a90_console_printf("%s populate=done root=%s marker=%s\r\n",
                       A90_D4_TAG, A90_D4_ROOT, A90_D4_MARKER_VALUE);
    return 0;
}

int a90_server_distro_switch_root_userdata_cmd(char **argv, int argc) {
    const char *expected_marker;
    char actual_marker[128];
    struct d4_userdata_target target;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_devpts = false;
    int rc;
    char *const newenv[] = {
        (char *)"HOME=/root",
        (char *)"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
        (char *)"TERM=linux",
        NULL,
    };
    char *const switch_argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"switch_root",
        (char *)A90_D4_ROOT,
        (char *)A90_D4_INIT,
        NULL,
    };

    if (argc != 3 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: switch-root-to-userdata %s <expected-marker>\r\n", A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    expected_marker = argv[2];
    if (!d4_marker_clean(expected_marker)) {
        a90_console_printf("%s refused=bad-expected-marker\r\n", A90_D4_TAG);
        return -EINVAL;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        return rc;
    }
    d4_print_target(&target, "switch-ready-check");
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        return rc;
    }
    rc = d4_mount_userdata_root();
    if (rc < 0) {
        return rc;
    }
    rc = d4_read_marker(actual_marker, sizeof(actual_marker));
    if (rc < 0) {
        a90_console_printf("%s stop=marker-read-fail rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    if (strcmp(actual_marker, expected_marker) != 0) {
        a90_console_printf("%s stop=marker-mismatch marker=%s expected=%s\r\n",
                           A90_D4_TAG, actual_marker, expected_marker);
        return -EPERM;
    }
    a90_console_printf("%s marker=ok value=%s\r\n", A90_D4_TAG, actual_marker);
    rc = d4_check_userdata_init();
    if (rc < 0) {
        a90_console_printf("%s stop=appliance-init-invalid rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_move_core_mounts(&moved_proc, &moved_sys, &moved_dev, &mounted_devpts);
    if (rc < 0) {
        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s marker=%s\r\n",
                       A90_D4_TAG, A90_D4_BUSYBOX, A90_D4_ROOT, A90_D4_INIT, actual_marker);
    a90_logf("server-distro", "D4 switch_root exec root=%s marker=%s", A90_D4_ROOT, actual_marker);
    sync();
    usleep(200000);
    execve(A90_D4_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D4_TAG, rc, -rc, strerror(-rc));
    d4_restore_core_mounts(moved_proc, moved_sys, moved_dev, mounted_devpts);
    return rc;
}
