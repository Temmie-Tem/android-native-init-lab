#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>

#ifndef MNT_DETACH
#define MNT_DETACH 2
#endif

#define EXECNS_VERSION "a90_android_execns_probe v4"
#define MAX_PATH_LEN 512
#define MAX_CAPTURE_SIZE (1024 * 1024)
#define MAX_LINKERCONFIG_SIZE (256 * 1024)

struct config {
    const char *system_root;
    const char *vendor_block;
    const char *vendor_fstype;
    const char *target;
    const char *target_profile;
    const char *linker;
    const char *env_mode;
    const char *mode;
    const char *linkerconfig_mode;
    const char *linkerconfig_source;
    const char *apex_libraries_source;
    int timeout_sec;
};

struct buffer {
    char *data;
    size_t len;
    size_t cap;
    bool truncated;
};

struct paths {
    char base[MAX_PATH_LEN];
    char root[MAX_PATH_LEN];
    char system[MAX_PATH_LEN];
    char vendor[MAX_PATH_LEN];
    char vendor_source[MAX_PATH_LEN];
    char proc[MAX_PATH_LEN];
    char apex[MAX_PATH_LEN];
    char linkerconfig[MAX_PATH_LEN];
};

static void usage(FILE *out) {
    fprintf(out, "%s\n", EXECNS_VERSION);
    fprintf(out,
            "usage: a90_android_execns_probe "
            "--system-root /mnt/system/system "
            "--vendor-block /dev/block/sda29 "
            "--vendor-fstype ext4 "
            "[--target-profile cnss-daemon|system-toybox|system-sh|linker64-self|apex-linker64-self] "
            "[--target /vendor/bin/cnss-daemon] "
            "--linker /system/bin/linker64|/apex/com.android.runtime/bin/linker64 "
            "[--env-mode clean|ld-debug-1|ld-debug-2|auxv] "
            "--mode linker-list "
            "[--linkerconfig-mode none|copy-real|minimal-vendor] "
            "[--linkerconfig-source /cache/path/to/ld.config.txt] "
            "[--apex-libraries-source /cache/path/to/apex.libraries.config.txt] "
            "--timeout-sec <1..30>\n");
}

static bool streq(const char *a, const char *b) {
    return a != NULL && b != NULL && strcmp(a, b) == 0;
}

static bool parse_int_range(const char *value, int min_value, int max_value, int *out) {
    char *end = NULL;
    long parsed;

    if (value == NULL || value[0] == '\0') {
        return false;
    }
    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return false;
    }
    if (parsed < min_value || parsed > max_value) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static int parse_args(int argc, char **argv, struct config *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    cfg->timeout_sec = 10;
    cfg->linkerconfig_mode = "none";
    cfg->target_profile = "cnss-daemon";
    cfg->target = "/vendor/bin/cnss-daemon";
    cfg->env_mode = "clean";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            usage(stdout);
            exit(0);
        }
        if (i + 1 >= argc) {
            fprintf(stderr, "missing value for %s\n", argv[i]);
            return 2;
        }
        if (strcmp(argv[i], "--system-root") == 0) {
            cfg->system_root = argv[++i];
        } else if (strcmp(argv[i], "--vendor-block") == 0) {
            cfg->vendor_block = argv[++i];
        } else if (strcmp(argv[i], "--vendor-fstype") == 0) {
            cfg->vendor_fstype = argv[++i];
        } else if (strcmp(argv[i], "--target") == 0) {
            cfg->target = argv[++i];
            cfg->target_profile = "custom-allowlisted";
        } else if (strcmp(argv[i], "--target-profile") == 0) {
            cfg->target_profile = argv[++i];
        } else if (strcmp(argv[i], "--linker") == 0) {
            cfg->linker = argv[++i];
        } else if (strcmp(argv[i], "--env-mode") == 0) {
            cfg->env_mode = argv[++i];
        } else if (strcmp(argv[i], "--mode") == 0) {
            cfg->mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-mode") == 0) {
            cfg->linkerconfig_mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-source") == 0) {
            cfg->linkerconfig_source = argv[++i];
        } else if (strcmp(argv[i], "--apex-libraries-source") == 0) {
            cfg->apex_libraries_source = argv[++i];
        } else if (strcmp(argv[i], "--timeout-sec") == 0) {
            if (!parse_int_range(argv[++i], 1, 30, &cfg->timeout_sec)) {
                fprintf(stderr, "invalid --timeout-sec\n");
                return 2;
            }
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            return 2;
        }
    }

    if (streq(cfg->target_profile, "cnss-daemon")) {
        cfg->target = "/vendor/bin/cnss-daemon";
    } else if (streq(cfg->target_profile, "system-toybox")) {
        cfg->target = "/system/bin/toybox";
    } else if (streq(cfg->target_profile, "system-sh")) {
        cfg->target = "/system/bin/sh";
    } else if (streq(cfg->target_profile, "linker64-self")) {
        cfg->target = "/system/bin/linker64";
    } else if (streq(cfg->target_profile, "apex-linker64-self")) {
        cfg->target = "/apex/com.android.runtime/bin/linker64";
    } else if (streq(cfg->target_profile, "custom-allowlisted")) {
        if (!(streq(cfg->target, "/vendor/bin/cnss-daemon") ||
              streq(cfg->target, "/system/bin/toybox") ||
              streq(cfg->target, "/system/bin/sh") ||
              streq(cfg->target, "/system/bin/linker64") ||
              streq(cfg->target, "/apex/com.android.runtime/bin/linker64"))) {
            fprintf(stderr, "--target must match a v235 allowlisted profile path\n");
            return 2;
        }
    } else {
        fprintf(stderr, "unknown --target-profile\n");
        return 2;
    }

    if (!streq(cfg->system_root, "/mnt/system/system") ||
        !streq(cfg->vendor_block, "/dev/block/sda29") ||
        !streq(cfg->vendor_fstype, "ext4") ||
        !(streq(cfg->linker, "/system/bin/linker64") ||
          streq(cfg->linker, "/apex/com.android.runtime/bin/linker64")) ||
        !streq(cfg->mode, "linker-list") ||
        !(streq(cfg->env_mode, "clean") ||
          streq(cfg->env_mode, "ld-debug-1") ||
          streq(cfg->env_mode, "ld-debug-2") ||
          streq(cfg->env_mode, "auxv")) ||
        !(streq(cfg->linkerconfig_mode, "none") ||
          streq(cfg->linkerconfig_mode, "copy-real") ||
          streq(cfg->linkerconfig_mode, "minimal-vendor"))) {
        fprintf(stderr, "arguments do not match v235 allowlist\n");
        return 2;
    }
    if (streq(cfg->linkerconfig_mode, "copy-real")) {
        if (cfg->linkerconfig_source == NULL ||
            strncmp(cfg->linkerconfig_source, "/cache/", 7) != 0 ||
            strstr(cfg->linkerconfig_source, "..") != NULL) {
            fprintf(stderr, "--linkerconfig-source must be an absolute /cache path for copy-real\n");
            return 2;
        }
        if (cfg->apex_libraries_source != NULL &&
            (strncmp(cfg->apex_libraries_source, "/cache/", 7) != 0 ||
             strstr(cfg->apex_libraries_source, "..") != NULL)) {
            fprintf(stderr, "--apex-libraries-source must be an absolute /cache path for copy-real\n");
            return 2;
        }
    } else if (cfg->linkerconfig_source != NULL || cfg->apex_libraries_source != NULL) {
        fprintf(stderr, "--linkerconfig-source and --apex-libraries-source are only valid with --linkerconfig-mode copy-real\n");
        return 2;
    }
    return 0;
}

static int append_path(char *out, size_t out_size, const char *a, const char *b) {
    int rc = snprintf(out, out_size, "%s/%s", a, b);

    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int mkdir_one(const char *path, mode_t mode) {
    if (mkdir(path, mode) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int mkdir_p(const char *path, mode_t mode) {
    char tmp[MAX_PATH_LEN];
    size_t len;

    len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memcpy(tmp, path, len + 1);
    for (char *p = tmp + 1; *p != '\0'; p++) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir_one(tmp, mode) < 0) {
                return -1;
            }
            *p = '/';
        }
    }
    return mkdir_one(tmp, mode);
}

static int init_paths(struct paths *paths) {
    int rc;

    rc = snprintf(paths->base, sizeof(paths->base), "/tmp/a90-v231-%ld", (long)getpid());
    if (rc < 0 || (size_t)rc >= sizeof(paths->base)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (append_path(paths->root, sizeof(paths->root), paths->base, "root") < 0 ||
        append_path(paths->system, sizeof(paths->system), paths->root, "system") < 0 ||
        append_path(paths->vendor, sizeof(paths->vendor), paths->root, "vendor") < 0 ||
        append_path(paths->vendor_source, sizeof(paths->vendor_source), paths->base, "vendor-block-sda29") < 0 ||
        append_path(paths->proc, sizeof(paths->proc), paths->root, "proc") < 0 ||
        append_path(paths->apex, sizeof(paths->apex), paths->root, "apex") < 0 ||
        append_path(paths->linkerconfig, sizeof(paths->linkerconfig), paths->root, "linkerconfig") < 0) {
        return -1;
    }
    if (mkdir_p(paths->base, 0700) < 0 ||
        mkdir_p(paths->root, 0755) < 0 ||
        mkdir_p(paths->system, 0755) < 0 ||
        mkdir_p(paths->vendor, 0755) < 0 ||
        mkdir_p(paths->proc, 0755) < 0 ||
        mkdir_p(paths->apex, 0755) < 0 ||
        mkdir_p(paths->linkerconfig, 0755) < 0) {
        return -1;
    }
    return 0;
}

static int bind_ro(const char *source, const char *target) {
    if (mount(source, target, NULL, MS_BIND | MS_REC, NULL) < 0) {
        return -1;
    }
    if (mount(NULL, target, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL) < 0) {
        return -1;
    }
    return 0;
}

static uint64_t fnv1a64_update(uint64_t hash, const void *data, size_t len) {
    const unsigned char *bytes = data;

    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static int write_all_fd(int fd, const void *data, size_t len) {
    const unsigned char *bytes = data;
    size_t done = 0;

    while (done < len) {
        ssize_t nwritten = write(fd, bytes + done, len - done);

        if (nwritten < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nwritten == 0) {
            errno = EIO;
            return -1;
        }
        done += (size_t)nwritten;
    }
    return 0;
}

static const char minimal_vendor_linkerconfig[] =
    "# A90 v232 synthetic private linkerconfig for linker64 --list only\n"
    "dir.vendor = /vendor/bin/\n"
    "\n"
    "[vendor]\n"
    "namespace.default.isolated = false\n"
    "namespace.default.search.paths = /vendor/${LIB}\n"
    "namespace.default.search.paths += /system/${LIB}\n"
    "namespace.default.search.paths += /apex/com.android.runtime/${LIB}/bionic\n"
    "namespace.default.permitted.paths = /vendor/${LIB}\n"
    "namespace.default.permitted.paths += /system/${LIB}\n"
    "namespace.default.permitted.paths += /apex/com.android.runtime/${LIB}/bionic\n";

static int append_linkerconfig_file(const char *dest,
                                    const char *data,
                                    size_t len,
                                    size_t *total_bytes,
                                    uint64_t *hash) {
    int fd = open(dest, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);

    if (fd < 0) {
        return -1;
    }
    if (write_all_fd(fd, data, len) < 0) {
        int saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    close(fd);
    *hash = fnv1a64_update(*hash, data, len);
    *total_bytes += len;
    return 0;
}

static int copy_linkerconfig_file(const char *source,
                                  const char *dest,
                                  size_t *total_bytes,
                                  uint64_t *hash) {
    char tmp[4096];
    int in_fd = open(source, O_RDONLY | O_CLOEXEC);
    int out_fd;

    if (in_fd < 0) {
        return -1;
    }
    out_fd = open(dest, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (out_fd < 0) {
        int saved_errno = errno;
        close(in_fd);
        errno = saved_errno;
        return -1;
    }
    for (;;) {
        ssize_t nread = read(in_fd, tmp, sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            goto fail;
        }
        if (nread == 0) {
            break;
        }
        if (*total_bytes + (size_t)nread > MAX_LINKERCONFIG_SIZE) {
            errno = EFBIG;
            goto fail;
        }
        if (write_all_fd(out_fd, tmp, (size_t)nread) < 0) {
            goto fail;
        }
        *hash = fnv1a64_update(*hash, tmp, (size_t)nread);
        *total_bytes += (size_t)nread;
    }
    close(out_fd);
    close(in_fd);
    return 0;

fail:
    {
        int saved_errno = errno;
        close(out_fd);
        close(in_fd);
        errno = saved_errno;
        return -1;
    }
}

static int materialize_linkerconfig(const struct config *cfg,
                                    const struct paths *paths,
                                    size_t *total_bytes,
                                    uint64_t *hash,
                                    char *error_buf,
                                    size_t error_size) {
    char dest[MAX_PATH_LEN];

    *total_bytes = 0;
    *hash = UINT64_C(1469598103934665603);
    if (append_path(dest, sizeof(dest), paths->linkerconfig, "ld.config.txt") < 0) {
        snprintf(error_buf, error_size, "linkerconfig path: %s", strerror(errno));
        return -1;
    }
    if (unlink(dest) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink linkerconfig: %s", strerror(errno));
        return -1;
    }
    if (streq(cfg->linkerconfig_mode, "minimal-vendor")) {
        if (append_linkerconfig_file(dest,
                                     minimal_vendor_linkerconfig,
                                     strlen(minimal_vendor_linkerconfig),
                                     total_bytes,
                                     hash) < 0) {
            snprintf(error_buf, error_size, "write minimal linkerconfig: %s", strerror(errno));
            return -1;
        }
        return 0;
    }
    if (streq(cfg->linkerconfig_mode, "copy-real")) {
        if (copy_linkerconfig_file(cfg->linkerconfig_source, dest, total_bytes, hash) < 0) {
            snprintf(error_buf, error_size, "copy linkerconfig: %s", strerror(errno));
            return -1;
        }
        if (cfg->apex_libraries_source != NULL) {
            if (append_path(dest, sizeof(dest), paths->linkerconfig, "apex.libraries.config.txt") < 0) {
                snprintf(error_buf, error_size, "apex libraries path: %s", strerror(errno));
                return -1;
            }
            if (unlink(dest) < 0 && errno != ENOENT) {
                snprintf(error_buf, error_size, "unlink apex libraries: %s", strerror(errno));
                return -1;
            }
            if (copy_linkerconfig_file(cfg->apex_libraries_source, dest, total_bytes, hash) < 0) {
                snprintf(error_buf, error_size, "copy apex libraries: %s", strerror(errno));
                return -1;
            }
        }
        return 0;
    }
    errno = EINVAL;
    snprintf(error_buf, error_size, "invalid linkerconfig mode");
    return -1;
}

static void cleanup_paths(const struct paths *paths) {
    char linkerconfig_file[MAX_PATH_LEN];

    if (paths->apex[0] != '\0') {
        umount2(paths->apex, MNT_DETACH);
    }
    if (paths->linkerconfig[0] != '\0') {
        umount2(paths->linkerconfig, MNT_DETACH);
        if (append_path(linkerconfig_file,
                        sizeof(linkerconfig_file),
                        paths->linkerconfig,
                        "ld.config.txt") == 0) {
            unlink(linkerconfig_file);
        }
        if (append_path(linkerconfig_file,
                        sizeof(linkerconfig_file),
                        paths->linkerconfig,
                        "apex.libraries.config.txt") == 0) {
            unlink(linkerconfig_file);
        }
    }
    umount2(paths->proc, MNT_DETACH);
    umount2(paths->vendor, MNT_DETACH);
    umount2(paths->system, MNT_DETACH);
    if (paths->apex[0] != '\0') {
        rmdir(paths->apex);
    }
    if (paths->linkerconfig[0] != '\0') {
        rmdir(paths->linkerconfig);
    }
    rmdir(paths->proc);
    rmdir(paths->vendor);
    rmdir(paths->system);
    rmdir(paths->root);
    unlink(paths->vendor_source);
    rmdir(paths->base);
}

static int buffer_init(struct buffer *buf) {
    buf->data = calloc(1, 1);
    if (buf->data == NULL) {
        return -1;
    }
    buf->len = 0;
    buf->cap = 1;
    buf->truncated = false;
    return 0;
}

static void buffer_free(struct buffer *buf) {
    free(buf->data);
    buf->data = NULL;
    buf->len = 0;
    buf->cap = 0;
}

static int buffer_append(struct buffer *buf, const char *data, size_t len) {
    size_t allowed = len;

    if (buf->len >= MAX_CAPTURE_SIZE) {
        buf->truncated = true;
        return 0;
    }
    if (buf->len + allowed > MAX_CAPTURE_SIZE) {
        allowed = MAX_CAPTURE_SIZE - buf->len;
        buf->truncated = true;
    }
    if (buf->len + allowed + 1 > buf->cap) {
        size_t new_cap = buf->cap;
        char *new_data;

        while (new_cap < buf->len + allowed + 1) {
            new_cap *= 2;
        }
        new_data = realloc(buf->data, new_cap);
        if (new_data == NULL) {
            return -1;
        }
        buf->data = new_data;
        buf->cap = new_cap;
    }
    memcpy(buf->data + buf->len, data, allowed);
    buf->len += allowed;
    buf->data[buf->len] = '\0';
    return 0;
}

static int set_nonblock(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);

    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int drain_fd(int fd, struct buffer *buf, bool *open_flag) {
    char tmp[4096];

    for (;;) {
        ssize_t nread = read(fd, tmp, sizeof(tmp));

        if (nread > 0) {
            if (buffer_append(buf, tmp, (size_t)nread) < 0) {
                return -1;
            }
            continue;
        }
        if (nread == 0) {
            close(fd);
            *open_flag = false;
            return 0;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;
        }
        close(fd);
        *open_flag = false;
        return -1;
    }
}

static long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}


static int path_in_root(char *out, size_t out_size, const struct paths *paths, const char *absolute_path) {
    const char *relative = absolute_path;
    int rc;

    if (absolute_path == NULL || absolute_path[0] != '/') {
        errno = EINVAL;
        return -1;
    }
    while (*relative == '/') {
        relative++;
    }
    rc = snprintf(out, out_size, "%s/%s", paths->root, relative);
    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int fnv1a64_file(const char *path, uint64_t *hash, size_t *bytes) {
    char tmp[4096];
    int fd = open(path, O_RDONLY | O_CLOEXEC);

    *hash = UINT64_C(1469598103934665603);
    *bytes = 0;
    if (fd < 0) {
        return -1;
    }
    for (;;) {
        ssize_t nread = read(fd, tmp, sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return -1;
        }
        if (nread == 0) {
            break;
        }
        *hash = fnv1a64_update(*hash, tmp, (size_t)nread);
        *bytes += (size_t)nread;
        if (*bytes > MAX_LINKERCONFIG_SIZE * 4U) {
            break;
        }
    }
    close(fd);
    return 0;
}

static void print_context_path(const struct paths *paths, const char *label, const char *absolute_path) {
    char host_path[MAX_PATH_LEN];
    char link_target[MAX_PATH_LEN];
    struct stat st;
    ssize_t nreadlink;
    uint64_t hash;
    size_t bytes;

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        printf("context.%s.path=%s\n", label, absolute_path);
        printf("context.%s.error=path-too-long\n", label);
        return;
    }
    printf("context.%s.path=%s\n", label, absolute_path);
    printf("context.%s.host_path=%s\n", label, host_path);
    if (lstat(host_path, &st) < 0) {
        printf("context.%s.exists=0\n", label);
        printf("context.%s.errno=%d\n", label, errno);
        return;
    }
    printf("context.%s.exists=1\n", label);
    printf("context.%s.mode=%o\n", label, st.st_mode & 07777);
    printf("context.%s.type=%s\n", label,
           S_ISREG(st.st_mode) ? "regular" :
           S_ISDIR(st.st_mode) ? "directory" :
           S_ISLNK(st.st_mode) ? "symlink" :
           S_ISBLK(st.st_mode) ? "block" : "other");
    printf("context.%s.size=%lld\n", label, (long long)st.st_size);
    nreadlink = readlink(host_path, link_target, sizeof(link_target) - 1);
    if (nreadlink >= 0) {
        link_target[nreadlink] = '\0';
        printf("context.%s.readlink=%s\n", label, link_target);
    }
    printf("context.%s.access_r=%d\n", label, access(host_path, R_OK) == 0 ? 1 : 0);
    printf("context.%s.access_x=%d\n", label, access(host_path, X_OK) == 0 ? 1 : 0);
    if (S_ISREG(st.st_mode) && fnv1a64_file(host_path, &hash, &bytes) == 0) {
        printf("context.%s.bytes=%zu\n", label, bytes);
        printf("context.%s.hash=0x%016llx\n", label, (unsigned long long)hash);
    }
}

static void print_preexec_context(const struct config *cfg, const struct paths *paths) {
    print_context_path(paths, "linker", cfg->linker);
    print_context_path(paths, "target", cfg->target);
    print_context_path(paths, "ld_config", "/linkerconfig/ld.config.txt");
    print_context_path(paths, "apex_libraries", "/linkerconfig/apex.libraries.config.txt");
    print_context_path(paths, "apex_runtime", "/apex/com.android.runtime");
    print_context_path(paths, "system_lib64", "/system/lib64");
    print_context_path(paths, "vendor_lib64", "/vendor/lib64");
    print_context_path(paths, "proc_self_exe", "/proc/self/exe");
}

static void apply_child_env(const struct config *cfg) {
    clearenv();
    setenv("PATH", "/system/bin:/vendor/bin:/bin", 1);
    setenv("ANDROID_ROOT", "/system", 1);
    setenv("ANDROID_DATA", "/data", 1);
    if (streq(cfg->env_mode, "ld-debug-1")) {
        setenv("LD_DEBUG", "1", 1);
    } else if (streq(cfg->env_mode, "ld-debug-2")) {
        setenv("LD_DEBUG", "2", 1);
    } else if (streq(cfg->env_mode, "auxv")) {
        setenv("LD_SHOW_AUXV", "1", 1);
    }
}

static int run_linker_list(const struct config *cfg,
                           const struct paths *paths,
                           struct buffer *stdout_buf,
                           struct buffer *stderr_buf,
                           int *child_exit_code,
                           int *child_signal,
                           bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    long deadline;
    pid_t pid;
    int status = 0;
    bool child_done = false;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        char *const child_argv[] = {
            (char *)cfg->linker,
            (char *)"--list",
            (char *)cfg->target,
            NULL,
        };

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        execv(cfg->linker, child_argv);
        perror("execv linker");
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 100;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(100000);
        }

        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            }
        }
    }
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int setup_namespace(const struct config *cfg,
                           struct paths *paths,
                           size_t *linkerconfig_bytes,
                           uint64_t *linkerconfig_hash,
                           char *error_buf,
                           size_t error_size) {
    char system_apex[MAX_PATH_LEN];
    const char *vendor_mount_source = cfg->vendor_block;
    const char *linkerconfig_source = "/mnt/system/linkerconfig";

    if (unshare(CLONE_NEWNS) < 0) {
        snprintf(error_buf, error_size, "unshare: %s", strerror(errno));
        return -1;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        snprintf(error_buf, error_size, "make-rprivate: %s", strerror(errno));
        return -1;
    }
    if (init_paths(paths) < 0) {
        snprintf(error_buf, error_size, "init paths: %s", strerror(errno));
        return -1;
    }
    if (bind_ro(cfg->system_root, paths->system) < 0) {
        snprintf(error_buf, error_size, "bind system: %s", strerror(errno));
        return -1;
    }
    if (access(cfg->vendor_block, F_OK) < 0) {
        FILE *dev_file;
        unsigned int major_no;
        unsigned int minor_no;

        if (errno != ENOENT) {
            snprintf(error_buf, error_size, "stat vendor block: %s", strerror(errno));
            return -1;
        }
        dev_file = fopen("/sys/class/block/sda29/dev", "re");
        if (dev_file == NULL) {
            snprintf(error_buf, error_size, "open sda29 dev: %s", strerror(errno));
            return -1;
        }
        if (fscanf(dev_file, "%u:%u", &major_no, &minor_no) != 2) {
            fclose(dev_file);
            snprintf(error_buf, error_size, "parse sda29 dev: invalid");
            return -1;
        }
        fclose(dev_file);
        if (mknod(paths->vendor_source, S_IFBLK | 0600, makedev(major_no, minor_no)) < 0) {
            snprintf(error_buf, error_size, "mknod vendor block: %s", strerror(errno));
            return -1;
        }
        vendor_mount_source = paths->vendor_source;
    }
    if (mount(vendor_mount_source,
              paths->vendor,
              cfg->vendor_fstype,
              MS_RDONLY | MS_NOSUID | MS_NODEV,
              "noload") < 0) {
        snprintf(error_buf, error_size, "mount vendor: %s", strerror(errno));
        return -1;
    }
    if (mount("proc", paths->proc, "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) < 0) {
        snprintf(error_buf, error_size, "mount proc: %s", strerror(errno));
        return -1;
    }
    if (append_path(system_apex, sizeof(system_apex), cfg->system_root, "apex") < 0) {
        snprintf(error_buf, error_size, "system apex path: %s", strerror(errno));
        return -1;
    }
    if (access(system_apex, R_OK | X_OK) == 0) {
        if (bind_ro(system_apex, paths->apex) < 0) {
            snprintf(error_buf, error_size, "bind apex: %s", strerror(errno));
            return -1;
        }
    } else {
        rmdir(paths->apex);
        paths->apex[0] = '\0';
    }
    if (!streq(cfg->linkerconfig_mode, "none")) {
        if (materialize_linkerconfig(cfg,
                                     paths,
                                     linkerconfig_bytes,
                                     linkerconfig_hash,
                                     error_buf,
                                     error_size) < 0) {
            return -1;
        }
    } else if (access(linkerconfig_source, R_OK | X_OK) == 0) {
        if (bind_ro(linkerconfig_source, paths->linkerconfig) < 0) {
            snprintf(error_buf, error_size, "bind linkerconfig: %s", strerror(errno));
            return -1;
        }
    } else {
        rmdir(paths->linkerconfig);
        paths->linkerconfig[0] = '\0';
    }
    return 0;
}

static void print_section(const char *name, const struct buffer *buf) {
    printf("A90_EXECNS_%s_BEGIN\n", name);
    if (buf->data != NULL && buf->len > 0) {
        fwrite(buf->data, 1, buf->len, stdout);
        if (buf->data[buf->len - 1] != '\n') {
            putchar('\n');
        }
    }
    printf("A90_EXECNS_%s_END truncated=%d bytes=%zu\n", name, buf->truncated ? 1 : 0, buf->len);
}

int main(int argc, char **argv) {
    struct config cfg;
    struct paths paths;
    struct buffer stdout_buf;
    struct buffer stderr_buf;
    char setup_error[256] = "";
    int child_exit_code = -1;
    int child_signal = 0;
    size_t linkerconfig_bytes = 0;
    uint64_t linkerconfig_hash = 0;
    bool timed_out = false;
    int parse_rc;
    int run_rc;

    memset(&paths, 0, sizeof(paths));
    parse_rc = parse_args(argc, argv, &cfg);
    if (parse_rc != 0) {
        usage(stderr);
        return parse_rc;
    }
    if (buffer_init(&stdout_buf) < 0 || buffer_init(&stderr_buf) < 0) {
        perror("buffer init");
        return 20;
    }

    printf("A90_EXECNS_BEGIN version=\"%s\"\n", EXECNS_VERSION);
    printf("mode=%s\n", cfg.mode);
    printf("linkerconfig_mode=%s\n", cfg.linkerconfig_mode);
    printf("target_profile=%s\n", cfg.target_profile);
    printf("env_mode=%s\n", cfg.env_mode);
    printf("linkerconfig_source=%s\n",
           cfg.linkerconfig_source != NULL ? cfg.linkerconfig_source : "<none>");
    printf("apex_libraries_source=%s\n",
           cfg.apex_libraries_source != NULL ? cfg.apex_libraries_source : "<none>");
    printf("system_root=%s\n", cfg.system_root);
    printf("vendor_block=%s\n", cfg.vendor_block);
    printf("vendor_fstype=%s\n", cfg.vendor_fstype);
    printf("target=%s\n", cfg.target);
    printf("linker=%s\n", cfg.linker);
    printf("timeout_sec=%d\n", cfg.timeout_sec);

    if (setup_namespace(&cfg,
                        &paths,
                        &linkerconfig_bytes,
                        &linkerconfig_hash,
                        setup_error,
                        sizeof(setup_error)) < 0) {
        printf("helper_status=setup-error\n");
        printf("setup_error=%s\n", setup_error);
        cleanup_paths(&paths);
        printf("cleanup_status=attempted\n");
        printf("A90_EXECNS_END rc=20\n");
        buffer_free(&stdout_buf);
        buffer_free(&stderr_buf);
        return 20;
    }

    printf("helper_status=namespace-ready\n");
    printf("temp_base=%s\n", paths.base);
    printf("temp_root=%s\n", paths.root);
    printf("vendor_mount_source=%s\n",
           access(paths.vendor_source, F_OK) == 0 ? paths.vendor_source : cfg.vendor_block);
    printf("linkerconfig_mount_source=%s\n",
           streq(cfg.linkerconfig_mode, "none")
               ? (paths.linkerconfig[0] != '\0' ? "/mnt/system/linkerconfig" : "<absent>")
               : "<private-materialized>");
    printf("linkerconfig_bytes=%zu\n", linkerconfig_bytes);
    printf("linkerconfig_hash=0x%016llx\n", (unsigned long long)linkerconfig_hash);
    print_preexec_context(&cfg, &paths);
    run_rc = run_linker_list(&cfg, &paths, &stdout_buf, &stderr_buf, &child_exit_code, &child_signal, &timed_out);
    printf("probe_run_rc=%d\n", run_rc);
    printf("child_exit_code=%d\n", child_exit_code);
    printf("child_signal=%d\n", child_signal);
    printf("timed_out=%d\n", timed_out ? 1 : 0);
    print_section("STDOUT", &stdout_buf);
    print_section("STDERR", &stderr_buf);
    cleanup_paths(&paths);
    printf("cleanup_status=attempted\n");
    printf("A90_EXECNS_END rc=0\n");

    buffer_free(&stdout_buf);
    buffer_free(&stderr_buf);
    return 0;
}
