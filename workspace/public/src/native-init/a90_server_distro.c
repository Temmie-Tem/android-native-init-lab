#include "a90_server_distro.h"

#include "a90_console.h"
#include "a90_helper.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_util.h"

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
        (char *)"-c",
        (char *)"/dev/console",
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

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s\r\n",
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
