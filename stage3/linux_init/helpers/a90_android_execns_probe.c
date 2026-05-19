#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <signal.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>
#include <elf.h>
#include <dirent.h>
#include <grp.h>
#include <linux/capability.h>

#ifndef MNT_DETACH
#define MNT_DETACH 2
#endif
#ifndef PTRACE_O_EXITKILL
#define PTRACE_O_EXITKILL 0x00100000
#endif
#ifndef NT_PRSTATUS
#define NT_PRSTATUS 1
#endif
#ifndef PR_CAP_AMBIENT
#define PR_CAP_AMBIENT 47
#endif
#ifndef PR_CAP_AMBIENT_RAISE
#define PR_CAP_AMBIENT_RAISE 2
#endif

#define EXECNS_VERSION "a90_android_execns_probe v18"
#define MAX_PATH_LEN 512
#define MAX_CAPTURE_SIZE (1024 * 1024)
#define MAX_LINKERCONFIG_SIZE (256 * 1024)
#define A90_AID_SYSTEM 1000
#define A90_AID_WIFI 1010
#define A90_AID_INET 3003
#define A90_AID_NET_ADMIN 3005
#define A90_AID_READPROC 3009

struct config {
    const char *system_root;
    const char *vendor_block;
    const char *vendor_fstype;
    const char *target;
    const char *target_profile;
    const char *linker;
    const char *env_mode;
    const char *mode;
    const char *capture_mode;
    const char *null_device_mode;
    const char *data_wifi_mode;
    const char *vndk_apex_alias_mode;
    const char *linkerconfig_mode;
    const char *linkerconfig_source;
    const char *apex_libraries_source;
    const char *property_root;
    const char *property_key;
    int timeout_sec;
    bool allow_cnss_start_only;
    bool allow_service_manager_start_only;
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
    char dev[MAX_PATH_LEN];
    char dev_null[MAX_PATH_LEN];
    char dev_binder[MAX_PATH_LEN];
    char dev_hwbinder[MAX_PATH_LEN];
    char dev_vndbinder[MAX_PATH_LEN];
    char dev_properties[MAX_PATH_LEN];
    char sys[MAX_PATH_LEN];
    char sys_fs[MAX_PATH_LEN];
    char sys_fs_selinux[MAX_PATH_LEN];
    char sys_fs_selinux_null[MAX_PATH_LEN];
    char data[MAX_PATH_LEN];
    char data_vendor[MAX_PATH_LEN];
    char data_vendor_wifi[MAX_PATH_LEN];
    char data_vendor_wifi_sockets[MAX_PATH_LEN];
    char proc[MAX_PATH_LEN];
    char apex[MAX_PATH_LEN];
    char linkerconfig[MAX_PATH_LEN];
    bool apex_synthetic;
};

static void usage(FILE *out) {
    fprintf(out, "%s\n", EXECNS_VERSION);
    fprintf(out,
            "usage: a90_android_execns_probe "
            "--system-root /mnt/system/system "
            "--vendor-block /dev/block/sda29 "
            "--vendor-fstype ext4 "
            "[--target-profile cnss-daemon|system-toybox|system-sh|linker64-self|apex-linker64-self|system-getprop|system-servicemanager|system-hwservicemanager] "
            "[--target /vendor/bin/cnss-daemon] "
            "[--linker /system/bin/linker64|/apex/com.android.runtime/bin/linker64] "
            "[--env-mode clean|ld-debug-1|ld-debug-2|auxv] "
            "[--capture-mode none|ptrace-lite] "
            "[--null-device-mode none|dev-null|dev-null-selinux] "
            "[--data-wifi-mode none|private-empty] "
            "[--vndk-apex-alias-mode none|v30-to-current] "
            "[--linkerconfig-mode none|copy-real|minimal-vendor] "
            "[--linkerconfig-source /cache/path/to/ld.config.txt] "
            "[--apex-libraries-source /cache/path/to/apex.libraries.config.txt] "
            "[--property-root /mnt/sdext/a90/private-property-v317/.../dev/__properties__] "
            "[--property-key ro.build.version.sdk] "
            "[--allow-cnss-start-only] "
            "[--allow-service-manager-start-only] "
            "--mode linker-list|identity-probe|cnss-start-only|property-lookup|service-manager-start-only "
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

static bool path_has_prefix_component(const char *path, const char *prefix) {
    size_t prefix_len;

    if (path == NULL || prefix == NULL) {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/');
}

static bool property_root_allowed(const char *path) {
    const char *suffix = "/dev/__properties__";
    size_t path_len;
    size_t suffix_len;

    if (path == NULL) {
        return false;
    }
    path_len = strlen(path);
    suffix_len = strlen(suffix);
    return path_has_prefix_component(path, "/mnt/sdext/a90/private-property-v317") &&
           strstr(path, "..") == NULL &&
           path_len >= suffix_len &&
           strcmp(path + path_len - suffix_len, suffix) == 0;
}

static bool property_key_allowed(const char *key) {
    return streq(key, "ro.build.version.sdk") ||
           streq(key, "ro.build.version.release") ||
           streq(key, "ro.product.vendor.device") ||
           streq(key, "ro.board.platform") ||
           streq(key, "ro.product.name") ||
           streq(key, "ro.hardware") ||
           streq(key, "ro.vendor.build.version.sdk");
}

static int parse_args(int argc, char **argv, struct config *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    cfg->timeout_sec = 10;
    cfg->linkerconfig_mode = "none";
    cfg->target_profile = "cnss-daemon";
    cfg->target = "/vendor/bin/cnss-daemon";
    cfg->env_mode = "clean";
    cfg->capture_mode = "none";
    cfg->null_device_mode = "none";
    cfg->data_wifi_mode = "none";
    cfg->vndk_apex_alias_mode = "none";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            usage(stdout);
            exit(0);
        }
        if (strcmp(argv[i], "--allow-cnss-start-only") == 0) {
            cfg->allow_cnss_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-service-manager-start-only") == 0) {
            cfg->allow_service_manager_start_only = true;
            continue;
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
        } else if (strcmp(argv[i], "--capture-mode") == 0) {
            cfg->capture_mode = argv[++i];
        } else if (strcmp(argv[i], "--null-device-mode") == 0) {
            cfg->null_device_mode = argv[++i];
        } else if (strcmp(argv[i], "--data-wifi-mode") == 0) {
            cfg->data_wifi_mode = argv[++i];
        } else if (strcmp(argv[i], "--vndk-apex-alias-mode") == 0) {
            cfg->vndk_apex_alias_mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-mode") == 0) {
            cfg->linkerconfig_mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-source") == 0) {
            cfg->linkerconfig_source = argv[++i];
        } else if (strcmp(argv[i], "--apex-libraries-source") == 0) {
            cfg->apex_libraries_source = argv[++i];
        } else if (strcmp(argv[i], "--property-root") == 0) {
            cfg->property_root = argv[++i];
        } else if (strcmp(argv[i], "--property-key") == 0) {
            cfg->property_key = argv[++i];
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
    } else if (streq(cfg->target_profile, "system-getprop")) {
        cfg->target = "/system/bin/getprop";
    } else if (streq(cfg->target_profile, "system-servicemanager")) {
        cfg->target = "/system/bin/servicemanager";
    } else if (streq(cfg->target_profile, "system-hwservicemanager")) {
        cfg->target = "/system/bin/hwservicemanager";
    } else if (streq(cfg->target_profile, "custom-allowlisted")) {
        if (!(streq(cfg->target, "/vendor/bin/cnss-daemon") ||
              streq(cfg->target, "/system/bin/toybox") ||
              streq(cfg->target, "/system/bin/sh") ||
              streq(cfg->target, "/system/bin/linker64") ||
              streq(cfg->target, "/apex/com.android.runtime/bin/linker64") ||
              streq(cfg->target, "/system/bin/getprop") ||
              streq(cfg->target, "/system/bin/servicemanager") ||
              streq(cfg->target, "/system/bin/hwservicemanager"))) {
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
        !(streq(cfg->mode, "linker-list") ||
          streq(cfg->mode, "identity-probe") ||
          streq(cfg->mode, "cnss-start-only") ||
          streq(cfg->mode, "property-lookup") ||
          streq(cfg->mode, "service-manager-start-only")) ||
        !(streq(cfg->capture_mode, "none") ||
          streq(cfg->capture_mode, "ptrace-lite")) ||
        !(streq(cfg->null_device_mode, "none") ||
          streq(cfg->null_device_mode, "dev-null") ||
          streq(cfg->null_device_mode, "dev-null-selinux")) ||
        !(streq(cfg->data_wifi_mode, "none") ||
          streq(cfg->data_wifi_mode, "private-empty")) ||
        !(streq(cfg->vndk_apex_alias_mode, "none") ||
          streq(cfg->vndk_apex_alias_mode, "v30-to-current")) ||
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
    if (streq(cfg->mode, "linker-list") &&
        !(streq(cfg->linker, "/system/bin/linker64") ||
          streq(cfg->linker, "/apex/com.android.runtime/bin/linker64"))) {
        fprintf(stderr, "--linker is required for linker-list mode\n");
        return 2;
    }
    if (streq(cfg->mode, "identity-probe") && cfg->linker != NULL) {
        fprintf(stderr, "--linker is not used by identity-probe mode\n");
        return 2;
    }
    if (streq(cfg->mode, "identity-probe") && !streq(cfg->capture_mode, "none")) {
        fprintf(stderr, "--capture-mode must be none for identity-probe mode\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && cfg->linker != NULL) {
        fprintf(stderr, "--linker is not used by cnss-start-only mode\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && !streq(cfg->capture_mode, "none")) {
        fprintf(stderr, "--capture-mode must be none for cnss-start-only mode\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && !streq(cfg->target, "/vendor/bin/cnss-daemon")) {
        fprintf(stderr, "cnss-start-only target is fixed to /vendor/bin/cnss-daemon\n");
        return 2;
    }
    if (streq(cfg->mode, "service-manager-start-only")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by service-manager-start-only mode\n");
            return 2;
        }
        if (!(streq(cfg->capture_mode, "none") ||
              streq(cfg->capture_mode, "ptrace-lite"))) {
            fprintf(stderr, "--capture-mode must be none or ptrace-lite for service-manager-start-only mode\n");
            return 2;
        }
        if (!(streq(cfg->target, "/system/bin/servicemanager") ||
              streq(cfg->target, "/system/bin/hwservicemanager"))) {
            fprintf(stderr, "service-manager-start-only target is fixed to system service-manager binaries\n");
            return 2;
        }
        if (streq(cfg->capture_mode, "ptrace-lite") &&
            !cfg->allow_service_manager_start_only) {
            fprintf(stderr, "--capture-mode ptrace-lite requires --allow-service-manager-start-only\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "property-lookup")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by property-lookup mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for property-lookup mode\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/getprop")) {
            fprintf(stderr, "property-lookup target is fixed to /system/bin/getprop\n");
            return 2;
        }
        if (!property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
        if (!property_key_allowed(cfg->property_key)) {
            fprintf(stderr, "--property-key is not in the v321 read-only allowlist\n");
            return 2;
        }
    } else if (streq(cfg->mode, "service-manager-start-only")) {
        if (cfg->property_key != NULL) {
            fprintf(stderr, "--property-key is only valid with property-lookup mode\n");
            return 2;
        }
        if (cfg->property_root != NULL && !property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
    } else if (cfg->property_root != NULL || cfg->property_key != NULL) {
        fprintf(stderr, "--property-root is only valid with property-lookup or service-manager-start-only mode; --property-key is only valid with property-lookup mode\n");
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
        append_path(paths->dev, sizeof(paths->dev), paths->root, "dev") < 0 ||
        append_path(paths->dev_null, sizeof(paths->dev_null), paths->dev, "null") < 0 ||
        append_path(paths->dev_binder, sizeof(paths->dev_binder), paths->dev, "binder") < 0 ||
        append_path(paths->dev_hwbinder, sizeof(paths->dev_hwbinder), paths->dev, "hwbinder") < 0 ||
        append_path(paths->dev_vndbinder, sizeof(paths->dev_vndbinder), paths->dev, "vndbinder") < 0 ||
        append_path(paths->dev_properties,
                    sizeof(paths->dev_properties),
                    paths->dev,
                    "__properties__") < 0 ||
        append_path(paths->sys, sizeof(paths->sys), paths->root, "sys") < 0 ||
        append_path(paths->sys_fs, sizeof(paths->sys_fs), paths->sys, "fs") < 0 ||
        append_path(paths->sys_fs_selinux, sizeof(paths->sys_fs_selinux), paths->sys_fs, "selinux") < 0 ||
        append_path(paths->sys_fs_selinux_null,
                    sizeof(paths->sys_fs_selinux_null),
                    paths->sys_fs_selinux,
                    "null") < 0 ||
        append_path(paths->data, sizeof(paths->data), paths->root, "data") < 0 ||
        append_path(paths->data_vendor, sizeof(paths->data_vendor), paths->data, "vendor") < 0 ||
        append_path(paths->data_vendor_wifi,
                    sizeof(paths->data_vendor_wifi),
                    paths->data_vendor,
                    "wifi") < 0 ||
        append_path(paths->data_vendor_wifi_sockets,
                    sizeof(paths->data_vendor_wifi_sockets),
                    paths->data_vendor_wifi,
                    "sockets") < 0 ||
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

static int materialize_private_properties(const struct config *cfg,
                                          const struct paths *paths,
                                          char *error_buf,
                                          size_t error_size) {
    struct stat st;
    bool wants_private_properties =
        streq(cfg->mode, "property-lookup") ||
        (streq(cfg->mode, "service-manager-start-only") &&
         cfg->allow_service_manager_start_only &&
         cfg->property_root != NULL);

    if (!wants_private_properties) {
        return 0;
    }
    if (lstat(cfg->property_root, &st) < 0) {
        snprintf(error_buf, error_size, "lstat property root: %s", strerror(errno));
        return -1;
    }
    if (S_ISLNK(st.st_mode)) {
        snprintf(error_buf, error_size, "property root is symlink");
        errno = ELOOP;
        return -1;
    }
    if (stat(cfg->property_root, &st) < 0) {
        snprintf(error_buf, error_size, "stat property root: %s", strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "property root is not directory");
        errno = ENOTDIR;
        return -1;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for properties: %s", strerror(errno));
        return -1;
    }
    if (mkdir_p(paths->dev_properties, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev properties: %s", strerror(errno));
        return -1;
    }
    if (bind_ro(cfg->property_root, paths->dev_properties) < 0) {
        snprintf(error_buf, error_size, "bind private properties: %s", strerror(errno));
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

static int materialize_null_devices(const struct config *cfg,
                                    const struct paths *paths,
                                    char *error_buf,
                                    size_t error_size) {
    if (streq(cfg->null_device_mode, "none")) {
        return 0;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev: %s", strerror(errno));
        return -1;
    }
    if (unlink(paths->dev_null) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink dev null: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->dev_null, S_IFCHR | 0666, makedev(1, 3)) < 0) {
        snprintf(error_buf, error_size, "mknod dev null: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->dev_null, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod dev null: %s", strerror(errno));
        return -1;
    }
    if (!streq(cfg->null_device_mode, "dev-null-selinux")) {
        return 0;
    }
    if (mkdir_p(paths->sys_fs_selinux, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir sys fs selinux: %s", strerror(errno));
        return -1;
    }
    if (unlink(paths->sys_fs_selinux_null) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink selinux null: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->sys_fs_selinux_null, S_IFCHR | 0666, makedev(1, 3)) < 0) {
        snprintf(error_buf, error_size, "mknod selinux null: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->sys_fs_selinux_null, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod selinux null: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_one_binder_device(const char *path,
                                         unsigned int minor_no,
                                         const char *name,
                                         char *error_buf,
                                         size_t error_size) {
    if (unlink(path) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink %s: %s", name, strerror(errno));
        return -1;
    }
    if (mknod(path, S_IFCHR | 0666, makedev(10, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod %s: %s", name, strerror(errno));
        return -1;
    }
    if (chmod(path, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod %s: %s", name, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_service_manager_binder_devices(const struct config *cfg,
                                                      const struct paths *paths,
                                                      char *error_buf,
                                                      size_t error_size) {
    if (!streq(cfg->mode, "service-manager-start-only") ||
        !cfg->allow_service_manager_start_only) {
        return 0;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for binder: %s", strerror(errno));
        return -1;
    }
    if (materialize_one_binder_device(paths->dev_binder, 81, "binder", error_buf, error_size) < 0 ||
        materialize_one_binder_device(paths->dev_hwbinder, 80, "hwbinder", error_buf, error_size) < 0 ||
        materialize_one_binder_device(paths->dev_vndbinder, 79, "vndbinder", error_buf, error_size) < 0) {
        return -1;
    }
    return 0;
}

static int materialize_data_wifi(const struct config *cfg,
                                 const struct paths *paths,
                                 char *error_buf,
                                 size_t error_size) {
    if (streq(cfg->data_wifi_mode, "none")) {
        return 0;
    }
    if (!streq(cfg->data_wifi_mode, "private-empty")) {
        snprintf(error_buf, error_size, "invalid data wifi mode");
        errno = EINVAL;
        return -1;
    }
    if (mkdir_p(paths->data_vendor_wifi_sockets, 0770) < 0) {
        snprintf(error_buf, error_size, "mkdir data vendor wifi sockets: %s", strerror(errno));
        return -1;
    }
    (void)chmod(paths->data, 0771);
    (void)chmod(paths->data_vendor, 0771);
    (void)chmod(paths->data_vendor_wifi, 0770);
    (void)chmod(paths->data_vendor_wifi_sockets, 0770);
    if (chown(paths->data_vendor_wifi, A90_AID_SYSTEM, A90_AID_WIFI) < 0) {
        snprintf(error_buf, error_size, "chown data vendor wifi: %s", strerror(errno));
        return -1;
    }
    if (chown(paths->data_vendor_wifi_sockets, A90_AID_SYSTEM, A90_AID_WIFI) < 0) {
        snprintf(error_buf, error_size, "chown data vendor wifi sockets: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static bool safe_apex_name(const char *name) {
    return name != NULL &&
           name[0] != '\0' &&
           strcmp(name, ".") != 0 &&
           strcmp(name, "..") != 0 &&
           strchr(name, '/') == NULL;
}

static int bind_apex_entry(const struct paths *paths,
                           const char *system_apex,
                           const char *name,
                           const char *target_name,
                           char *error_buf,
                           size_t error_size) {
    char mount_path[MAX_PATH_LEN];
    char source_path[MAX_PATH_LEN];
    struct stat st;

    if (!safe_apex_name(name) || !safe_apex_name(target_name)) {
        errno = EINVAL;
        snprintf(error_buf, error_size, "unsafe apex name");
        return -1;
    }
    if (append_path(mount_path, sizeof(mount_path), paths->apex, name) < 0) {
        snprintf(error_buf, error_size, "apex mount path: %s", strerror(errno));
        return -1;
    }
    if (append_path(source_path, sizeof(source_path), system_apex, target_name) < 0) {
        snprintf(error_buf, error_size, "apex source path: %s", strerror(errno));
        return -1;
    }
    if (stat(source_path, &st) < 0) {
        snprintf(error_buf, error_size, "stat apex %s: %s", target_name, strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "apex %s is not a directory", target_name);
        errno = ENOTDIR;
        return -1;
    }
    if (mkdir_p(mount_path, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir apex %s: %s", name, strerror(errno));
        return -1;
    }
    if (bind_ro(source_path, mount_path) < 0) {
        snprintf(error_buf, error_size, "bind apex %s: %s", name, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_apex_bind_farm(const struct config *cfg,
                                      struct paths *paths,
                                      const char *system_apex,
                                      char *error_buf,
                                      size_t error_size) {
    DIR *dir;
    struct dirent *entry;
    char current_source[MAX_PATH_LEN];
    char v30_mount[MAX_PATH_LEN];

    paths->apex_synthetic = true;
    dir = opendir(system_apex);
    if (dir == NULL) {
        snprintf(error_buf, error_size, "opendir system apex: %s", strerror(errno));
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (!safe_apex_name(entry->d_name)) {
            continue;
        }
        if (bind_apex_entry(paths,
                            system_apex,
                            entry->d_name,
                            entry->d_name,
                            error_buf,
                            error_size) < 0) {
            closedir(dir);
            return -1;
        }
    }
    closedir(dir);

    if (!streq(cfg->vndk_apex_alias_mode, "v30-to-current")) {
        return 0;
    }
    if (append_path(current_source,
                    sizeof(current_source),
                    system_apex,
                    "com.android.vndk.current") < 0) {
        snprintf(error_buf, error_size, "vndk current path: %s", strerror(errno));
        return -1;
    }
    if (access(current_source, R_OK | X_OK) < 0) {
        snprintf(error_buf, error_size, "vndk current missing: %s", strerror(errno));
        return -1;
    }
    if (append_path(v30_mount, sizeof(v30_mount), paths->apex, "com.android.vndk.v30") < 0) {
        snprintf(error_buf, error_size, "vndk v30 mount path: %s", strerror(errno));
        return -1;
    }
    if (access(v30_mount, F_OK) == 0) {
        return 0;
    }
    if (errno != ENOENT) {
        snprintf(error_buf, error_size, "stat vndk v30 mount: %s", strerror(errno));
        return -1;
    }
    return bind_apex_entry(paths,
                           system_apex,
                           "com.android.vndk.v30",
                           "com.android.vndk.current",
                           error_buf,
                           error_size);
}

static void cleanup_dir_entries(const char *path) {
    DIR *dir = opendir(path);
    struct dirent *entry;

    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char child[MAX_PATH_LEN];

        if (!safe_apex_name(entry->d_name)) {
            continue;
        }
        if (append_path(child, sizeof(child), path, entry->d_name) == 0) {
            umount2(child, MNT_DETACH);
            if (rmdir(child) < 0) {
                unlink(child);
            }
        }
    }
    closedir(dir);
}

static void cleanup_paths(const struct paths *paths) {
    char linkerconfig_file[MAX_PATH_LEN];

    if (paths->apex[0] != '\0') {
        umount2(paths->apex, MNT_DETACH);
        if (paths->apex_synthetic) {
            cleanup_dir_entries(paths->apex);
        }
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
    if (paths->sys_fs_selinux_null[0] != '\0') {
        unlink(paths->sys_fs_selinux_null);
    }
    if (paths->dev_properties[0] != '\0') {
        umount2(paths->dev_properties, MNT_DETACH);
        rmdir(paths->dev_properties);
    }
    if (paths->dev_null[0] != '\0') {
        unlink(paths->dev_null);
    }
    if (paths->sys_fs_selinux[0] != '\0') {
        rmdir(paths->sys_fs_selinux);
    }
    if (paths->sys_fs[0] != '\0') {
        rmdir(paths->sys_fs);
    }
    if (paths->sys[0] != '\0') {
        rmdir(paths->sys);
    }
    if (paths->dev[0] != '\0') {
        rmdir(paths->dev);
    }
    if (paths->data_vendor_wifi_sockets[0] != '\0') {
        rmdir(paths->data_vendor_wifi_sockets);
    }
    if (paths->data_vendor_wifi[0] != '\0') {
        rmdir(paths->data_vendor_wifi);
    }
    if (paths->data_vendor[0] != '\0') {
        rmdir(paths->data_vendor);
    }
    if (paths->data[0] != '\0') {
        rmdir(paths->data);
    }
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
    printf("context.%s.uid=%u\n", label, (unsigned int)st.st_uid);
    printf("context.%s.gid=%u\n", label, (unsigned int)st.st_gid);
    printf("context.%s.mode=%o\n", label, st.st_mode & 07777);
    printf("context.%s.type=%s\n", label,
           S_ISREG(st.st_mode) ? "regular" :
           S_ISDIR(st.st_mode) ? "directory" :
           S_ISLNK(st.st_mode) ? "symlink" :
           S_ISCHR(st.st_mode) ? "char" :
           S_ISBLK(st.st_mode) ? "block" : "other");
    if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) {
        printf("context.%s.rdev=%u:%u\n",
               label,
               major(st.st_rdev),
               minor(st.st_rdev));
    }
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
    if (cfg->linker != NULL) {
        print_context_path(paths, "linker", cfg->linker);
    }
    if (cfg->target != NULL) {
        print_context_path(paths, "target", cfg->target);
    }
    print_context_path(paths, "dev_null", "/dev/null");
    print_context_path(paths, "dev_binder", "/dev/binder");
    print_context_path(paths, "dev_hwbinder", "/dev/hwbinder");
    print_context_path(paths, "dev_vndbinder", "/dev/vndbinder");
    print_context_path(paths, "dev_properties", "/dev/__properties__");
    print_context_path(paths, "selinux_null", "/sys/fs/selinux/null");
    print_context_path(paths, "data", "/data");
    print_context_path(paths, "data_vendor", "/data/vendor");
    print_context_path(paths, "data_vendor_wifi", "/data/vendor/wifi");
    print_context_path(paths, "data_vendor_wifi_sockets", "/data/vendor/wifi/sockets");
    print_context_path(paths, "ld_config", "/linkerconfig/ld.config.txt");
    print_context_path(paths, "apex_libraries", "/linkerconfig/apex.libraries.config.txt");
    print_context_path(paths, "apex_runtime", "/apex/com.android.runtime");
    print_context_path(paths, "apex_vndk_v30", "/apex/com.android.vndk.v30");
    print_context_path(paths, "apex_vndk_v30_libcutils", "/apex/com.android.vndk.v30/lib64/libcutils.so");
    print_context_path(paths, "apex_vndk_current", "/apex/com.android.vndk.current");
    print_context_path(paths, "apex_vndk_current_libcutils", "/apex/com.android.vndk.current/lib64/libcutils.so");
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

static unsigned int cap_word(int cap) {
    return (unsigned int)cap / 32U;
}

static unsigned int cap_bit(int cap) {
    return 1U << ((unsigned int)cap % 32U);
}

static int capget_current(struct __user_cap_data_struct data[2]) {
    struct __user_cap_header_struct header;

    memset(&header, 0, sizeof(header));
    memset(data, 0, sizeof(struct __user_cap_data_struct) * 2U);
    header.version = _LINUX_CAPABILITY_VERSION_3;
    header.pid = 0;
    return (int)syscall(SYS_capget, &header, data);
}

static int capset_current(const struct __user_cap_data_struct data[2]) {
    struct __user_cap_header_struct header;

    memset(&header, 0, sizeof(header));
    header.version = _LINUX_CAPABILITY_VERSION_3;
    header.pid = 0;
    return (int)syscall(SYS_capset, &header, data);
}

static bool cap_data_has(const struct __user_cap_data_struct data[2],
                         const char *field,
                         int cap) {
    unsigned int word = cap_word(cap);
    unsigned int bit = cap_bit(cap);

    if (word >= 2U) {
        return false;
    }
    if (strcmp(field, "effective") == 0) {
        return (data[word].effective & bit) != 0;
    }
    if (strcmp(field, "permitted") == 0) {
        return (data[word].permitted & bit) != 0;
    }
    if (strcmp(field, "inheritable") == 0) {
        return (data[word].inheritable & bit) != 0;
    }
    return false;
}

static void print_cap_net_admin(const char *prefix) {
    struct __user_cap_data_struct data[2];

    if (capget_current(data) < 0) {
        printf("%s.capget.error=%s\n", prefix, strerror(errno));
        return;
    }
    printf("%s.cap.net_admin.effective=%d\n",
           prefix,
           cap_data_has(data, "effective", CAP_NET_ADMIN) ? 1 : 0);
    printf("%s.cap.net_admin.permitted=%d\n",
           prefix,
           cap_data_has(data, "permitted", CAP_NET_ADMIN) ? 1 : 0);
    printf("%s.cap.net_admin.inheritable=%d\n",
           prefix,
           cap_data_has(data, "inheritable", CAP_NET_ADMIN) ? 1 : 0);
}

static bool groups_contain(const gid_t *groups, int count, gid_t expected) {
    for (int i = 0; i < count; i++) {
        if (groups[i] == expected) {
            return true;
        }
    }
    return false;
}

static int print_identity_snapshot(const char *prefix) {
    uid_t ruid = (uid_t)-1;
    uid_t euid = (uid_t)-1;
    uid_t suid = (uid_t)-1;
    gid_t rgid = (gid_t)-1;
    gid_t egid = (gid_t)-1;
    gid_t sgid = (gid_t)-1;
    gid_t groups[32];
    int group_count;

    if (getresuid(&ruid, &euid, &suid) < 0) {
        printf("%s.getresuid.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    if (getresgid(&rgid, &egid, &sgid) < 0) {
        printf("%s.getresgid.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    group_count = getgroups((int)(sizeof(groups) / sizeof(groups[0])), groups);
    if (group_count < 0) {
        printf("%s.getgroups.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    printf("%s.uid.real=%ld\n", prefix, (long)ruid);
    printf("%s.uid.effective=%ld\n", prefix, (long)euid);
    printf("%s.uid.saved=%ld\n", prefix, (long)suid);
    printf("%s.gid.real=%ld\n", prefix, (long)rgid);
    printf("%s.gid.effective=%ld\n", prefix, (long)egid);
    printf("%s.gid.saved=%ld\n", prefix, (long)sgid);
    printf("%s.groups.count=%d\n", prefix, group_count);
    printf("%s.groups.values=", prefix);
    for (int i = 0; i < group_count; i++) {
        printf("%s%ld", i == 0 ? "" : ",", (long)groups[i]);
    }
    printf("\n");
    printf("%s.groups.has_inet=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_INET) ? 1 : 0);
    printf("%s.groups.has_net_admin=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_NET_ADMIN) ? 1 : 0);
    printf("%s.groups.has_wifi=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_WIFI) ? 1 : 0);
    printf("%s.groups.has_readproc=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_READPROC) ? 1 : 0);
    print_cap_net_admin(prefix);
    return 0;
}

static int ensure_net_admin_inheritable_before_drop(void) {
    struct __user_cap_data_struct data[2];
    unsigned int word = cap_word(CAP_NET_ADMIN);
    unsigned int bit = cap_bit(CAP_NET_ADMIN);

    if (capget_current(data) < 0) {
        return -1;
    }
    if (word >= 2U) {
        errno = EINVAL;
        return -1;
    }
    data[word].inheritable |= bit;
    return capset_current(data);
}

static int restrict_to_net_admin_capability(void) {
    struct __user_cap_data_struct data[2];
    unsigned int word = cap_word(CAP_NET_ADMIN);
    unsigned int bit = cap_bit(CAP_NET_ADMIN);

    memset(data, 0, sizeof(data));
    if (word >= 2U) {
        errno = EINVAL;
        return -1;
    }
    data[word].effective = bit;
    data[word].permitted = bit;
    data[word].inheritable = bit;
    return capset_current(data);
}

static int apply_android_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_INET, A90_AID_NET_ADMIN, A90_AID_WIFI};
    int ambient_rc;
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.groups=%d,%d,%d\n",
           prefix,
           A90_AID_INET,
           A90_AID_NET_ADMIN,
           A90_AID_WIFI);
    printf("%s.expected.cap=CAP_NET_ADMIN\n", prefix);
    if (print_identity_snapshot("cnss.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("%s.pr_set_keepcaps.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pr_set_keepcaps.ok=1\n", prefix);
    }
    if (ensure_net_admin_inheritable_before_drop() < 0) {
        printf("%s.pre_drop_inheritable.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pre_drop_inheritable.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_net_admin_capability() < 0) {
        printf("%s.capset_net_admin.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset_net_admin.ok=1\n", prefix);
    }
    errno = 0;
    ambient_rc = prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_ADMIN, 0, 0);
    if (ambient_rc < 0) {
        printf("%s.ambient_raise.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.ambient_raise.ok=1\n", prefix);
    }
    printf("%s.ambient_raise.rc=%d\n", prefix, ambient_rc);
    printf("%s.ambient_raise.errno=%d\n", prefix, ambient_rc < 0 ? errno : 0);
    if (print_identity_snapshot("cnss.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_service_manager_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_SYSTEM, A90_AID_READPROC};
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.groups=%d,%d\n",
           prefix,
           A90_AID_SYSTEM,
           A90_AID_READPROC);
    printf("%s.expected.cap=none\n", prefix);
    if (print_identity_snapshot("service_manager.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (print_identity_snapshot("service_manager.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int run_identity_probe_child(const struct config *cfg, const struct paths *paths) {
    gid_t groups[] = {A90_AID_INET, A90_AID_NET_ADMIN, A90_AID_WIFI};
    int ambient_rc;
    int ambient_errno = 0;
    bool pass = true;

    if (chroot(paths->root) < 0) {
        perror("chroot");
        return 120;
    }
    if (chdir("/") < 0) {
        perror("chdir");
        return 121;
    }
    apply_child_env(cfg);

    printf("identity_probe.begin=1\n");
    printf("identity_probe.expected.uid=%d\n", A90_AID_SYSTEM);
    printf("identity_probe.expected.gid=%d\n", A90_AID_SYSTEM);
    printf("identity_probe.expected.groups=%d,%d,%d\n",
           A90_AID_INET,
           A90_AID_NET_ADMIN,
           A90_AID_WIFI);
    printf("identity_probe.expected.cap=CAP_NET_ADMIN\n");
    if (print_identity_snapshot("identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("identity_probe.setgroups.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setgroups.ok=1\n");
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("identity_probe.pr_set_keepcaps.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.pr_set_keepcaps.ok=1\n");
    }
    if (ensure_net_admin_inheritable_before_drop() < 0) {
        printf("identity_probe.pre_drop_inheritable.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.pre_drop_inheritable.ok=1\n");
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("identity_probe.setresgid.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setresgid.ok=1\n");
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("identity_probe.setresuid.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setresuid.ok=1\n");
    }
    if (restrict_to_net_admin_capability() < 0) {
        printf("identity_probe.capset_net_admin.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.capset_net_admin.ok=1\n");
    }
    errno = 0;
    ambient_rc = prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_ADMIN, 0, 0);
    if (ambient_rc < 0) {
        ambient_errno = errno;
        printf("identity_probe.ambient_raise.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.ambient_raise.ok=1\n");
    }
    printf("identity_probe.ambient_raise.rc=%d\n", ambient_rc);
    printf("identity_probe.ambient_raise.errno=%d\n", ambient_errno);
    if (print_identity_snapshot("identity.after") < 0) {
        pass = false;
    }
    printf("identity_probe.preexec_status=%s\n", pass ? "pass" : "fail");
    printf("identity_probe.exec_target=/system/bin/toybox cat /proc/self/status\n");
    fflush(stdout);
    if (!pass) {
        printf("identity_probe.end=1\n");
        fflush(stdout);
        return 1;
    }
    {
        char *const child_argv[] = {
            (char *)"/system/bin/toybox",
            (char *)"cat",
            (char *)"/proc/self/status",
            NULL,
        };

        execv("/system/bin/toybox", child_argv);
    }
    printf("identity_probe.exec_error=%s\n", strerror(errno));
    printf("identity_probe.end=1\n");
    fflush(stdout);
    return 127;
}

static void proc_path(char *out, size_t out_size, pid_t pid, const char *name) {
    snprintf(out, out_size, "/proc/%ld/%s", (long)pid, name);
}

static void print_proc_link(pid_t pid, const char *label, const char *name) {
    char path[MAX_PATH_LEN];
    char target[MAX_PATH_LEN];
    ssize_t nread;

    proc_path(path, sizeof(path), pid, name);
    nread = readlink(path, target, sizeof(target) - 1);
    if (nread < 0) {
        printf("capture.%s.%s.error=%s\n", label, name, strerror(errno));
        return;
    }
    target[nread] = '\0';
    printf("capture.%s.%s=%s\n", label, name, target);
}

static void print_proc_text(pid_t pid, const char *label, const char *name, size_t limit) {
    char path[MAX_PATH_LEN];
    char buf[4096];
    size_t total = 0;
    bool truncated = false;
    char last_char = '\0';
    int fd;

    proc_path(path, sizeof(path), pid, name);
    printf("A90_EXECNS_CAPTURE_%s_%s_BEGIN path=%s limit=%zu\n", label, name, path, limit);
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("open-error=%s\n", strerror(errno));
        printf("A90_EXECNS_CAPTURE_%s_%s_END bytes=0 truncated=0\n", label, name);
        return;
    }
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, buf, room < sizeof(buf) ? room : sizeof(buf));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("\nread-error=%s\n", strerror(errno));
            break;
        }
        if (nread == 0) {
            break;
        }
        fwrite(buf, 1, (size_t)nread, stdout);
        last_char = buf[nread - 1];
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    if (total == 0 || last_char != '\n') {
        putchar('\n');
    }
    printf("A90_EXECNS_CAPTURE_%s_%s_END bytes=%zu truncated=%d\n",
           label,
           name,
           total,
           truncated ? 1 : 0);
}

static void print_proc_auxv(pid_t pid, const char *label) {
    char path[MAX_PATH_LEN];
    struct {
        unsigned long key;
        unsigned long value;
    } item;
    int fd;
    int index = 0;

    proc_path(path, sizeof(path), pid, "auxv");
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("capture.%s.auxv.error=%s\n", label, strerror(errno));
        return;
    }
    while (read(fd, &item, sizeof(item)) == (ssize_t)sizeof(item)) {
        printf("capture.%s.auxv.%d.type=%lu\n", label, index, item.key);
        printf("capture.%s.auxv.%d.value=0x%lx\n", label, index, item.value);
        index++;
        if (item.key == 0 || index >= 96) {
            break;
        }
    }
    close(fd);
    printf("capture.%s.auxv.count=%d\n", label, index);
}

static void print_ptrace_siginfo(pid_t pid, const char *label) {
    siginfo_t info;

    memset(&info, 0, sizeof(info));
    if (ptrace(PTRACE_GETSIGINFO, pid, NULL, &info) < 0) {
        printf("capture.%s.siginfo.error=%s\n", label, strerror(errno));
        return;
    }
    printf("capture.%s.siginfo.signo=%d\n", label, info.si_signo);
    printf("capture.%s.siginfo.code=%d\n", label, info.si_code);
    printf("capture.%s.siginfo.errno=%d\n", label, info.si_errno);
    printf("capture.%s.siginfo.addr=%p\n", label, info.si_addr);
}

static void print_ptrace_regs(pid_t pid, const char *label) {
    unsigned long long regs[96];
    struct iovec iov;
    size_t words;

    memset(regs, 0, sizeof(regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, pid, (void *)(long)NT_PRSTATUS, &iov) < 0) {
        printf("capture.%s.regset.nt_prstatus.error=%s\n", label, strerror(errno));
        return;
    }
    printf("capture.%s.regset.nt_prstatus.bytes=%zu\n", label, iov.iov_len);
    words = iov.iov_len / sizeof(regs[0]);
    if (words > 40) {
        words = 40;
    }
    for (size_t i = 0; i < words; i++) {
        printf("capture.%s.regset.word%02zu=0x%016llx\n", label, i, regs[i]);
    }
}

static void print_capture_snapshot(pid_t pid, const char *label, bool include_maps) {
    printf("capture.%s.pid=%ld\n", label, (long)pid);
    print_proc_link(pid, label, "exe");
    print_proc_link(pid, label, "cwd");
    print_proc_auxv(pid, label);
    print_ptrace_regs(pid, label);
    print_proc_text(pid, label, "status", 8192);
    if (include_maps) {
        print_proc_text(pid, label, "maps", 65536);
        print_proc_text(pid, label, "mountinfo", 65536);
    }
}

static int run_linker_list_ptrace(const struct config *cfg,
                                  const struct paths *paths,
                                  struct buffer *stdout_buf,
                                  struct buffer *stderr_buf,
                                  int *child_exit_code,
                                  int *child_signal,
                                  bool *timed_out);

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

    if (streq(cfg->capture_mode, "ptrace-lite")) {
        return run_linker_list_ptrace(cfg,
                                      paths,
                                      stdout_buf,
                                      stderr_buf,
                                      child_exit_code,
                                      child_signal,
                                      timed_out);
    }

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

static int run_linker_list_ptrace(const struct config *cfg,
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
    bool child_done = false;
    bool exec_captured = false;
    bool crash_captured = false;
    long deadline;
    pid_t pid;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    printf("capture.mode=ptrace-lite\n");

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
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) < 0) {
            perror("ptrace-traceme");
            _exit(122);
        }
        raise(SIGSTOP);
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

    if (waitpid(pid, &status, 0) != pid) {
        printf("capture.initial_wait.error=%s\n", strerror(errno));
        goto fail;
    }
    if (!WIFSTOPPED(status)) {
        printf("capture.initial_stop.unexpected_status=0x%x\n", status);
        if (WIFEXITED(status)) {
            *child_exit_code = WEXITSTATUS(status);
        } else if (WIFSIGNALED(status)) {
            *child_signal = WTERMSIG(status);
        }
        child_done = true;
    } else {
        printf("capture.initial_stop.signal=%d\n", WSTOPSIG(status));
        if (ptrace(PTRACE_SETOPTIONS,
                   pid,
                   NULL,
                   (void *)(long)(PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL)) < 0) {
            printf("capture.setoptions.error=%s\n", strerror(errno));
        }
        if (ptrace(PTRACE_CONT, pid, NULL, NULL) < 0) {
            printf("capture.initial_cont.error=%s\n", strerror(errno));
            goto fail;
        }
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            printf("capture.timeout.kill=1\n");
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
            usleep(50000);
        }

        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                if (WIFEXITED(status)) {
                    child_done = true;
                    *child_exit_code = WEXITSTATUS(status);
                    printf("capture.child.exit=%d\n", *child_exit_code);
                } else if (WIFSIGNALED(status)) {
                    child_done = true;
                    *child_signal = WTERMSIG(status);
                    printf("capture.child.signal=%d\n", *child_signal);
                } else if (WIFSTOPPED(status)) {
                    int sig = WSTOPSIG(status);
                    unsigned int event = (unsigned int)status >> 16;
                    int deliver_sig = 0;

                    printf("capture.stop.signal=%d\n", sig);
                    printf("capture.stop.event=%u\n", event);
                    if (sig == SIGTRAP && !exec_captured) {
                        exec_captured = true;
                        printf("capture.exec_stop=1\n");
                        print_capture_snapshot(pid, "exec", true);
                    } else if (sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) {
                        crash_captured = true;
                        printf("capture.crash_stop=1\n");
                        print_ptrace_siginfo(pid, "crash");
                        print_capture_snapshot(pid, "crash", true);
                        deliver_sig = sig;
                    } else if (sig != SIGTRAP) {
                        deliver_sig = sig;
                    }
                    if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)deliver_sig) < 0) {
                        printf("capture.cont.error=%s\n", strerror(errno));
                        kill(-pid, SIGKILL);
                        kill(pid, SIGKILL);
                    }
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("capture.wait.error=%s\n", strerror(errno));
            }
        }
    }
    printf("capture.exec_captured=%d\n", exec_captured ? 1 : 0);
    printf("capture.crash_captured=%d\n", crash_captured ? 1 : 0);
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_identity_probe(const struct config *cfg,
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
    bool child_done = false;
    long deadline;
    pid_t pid;
    int status = 0;

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
        int rc;

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        rc = run_identity_probe_child(cfg, paths);
        _exit(rc);
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
        int poll_timeout = 50;
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
            usleep(50000);
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
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("identity_probe.wait.error=%s\n", strerror(errno));
                child_done = true;
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

static int run_property_lookup(const struct config *cfg,
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
    bool child_done = false;
    long deadline;
    pid_t pid;
    int status = 0;

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
            (char *)"/system/bin/getprop",
            (char *)cfg->property_key,
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
        execv("/system/bin/getprop", child_argv);
        perror("execv getprop");
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
        int poll_timeout = 50;
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
            usleep(50000);
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
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("property_lookup.wait.error=%s\n", strerror(errno));
                child_done = true;
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

static int append_literal(struct buffer *buf, const char *text) {
    return buffer_append(buf, text, strlen(text));
}

static int append_format(struct buffer *buf, const char *fmt, ...) {
    char small[1024];
    char *dynamic_buf = NULL;
    va_list ap;
    va_list copy;
    int needed;
    int rc;

    va_start(ap, fmt);
    va_copy(copy, ap);
    needed = vsnprintf(small, sizeof(small), fmt, ap);
    va_end(ap);
    if (needed < 0) {
        va_end(copy);
        return -1;
    }
    if ((size_t)needed < sizeof(small)) {
        va_end(copy);
        return buffer_append(buf, small, (size_t)needed);
    }
    dynamic_buf = malloc((size_t)needed + 1U);
    if (dynamic_buf == NULL) {
        va_end(copy);
        return -1;
    }
    rc = vsnprintf(dynamic_buf, (size_t)needed + 1U, fmt, copy);
    va_end(copy);
    if (rc < 0) {
        free(dynamic_buf);
        return -1;
    }
    rc = buffer_append(buf, dynamic_buf, (size_t)rc);
    free(dynamic_buf);
    return rc;
}

static int append_proc_file_capture(struct buffer *buf,
                                    pid_t pid,
                                    const char *name,
                                    size_t limit,
                                    bool *captured) {
    char path[MAX_PATH_LEN];
    char tmp[4096];
    size_t total = 0;
    bool truncated = false;
    int fd;

    *captured = false;
    proc_path(path, sizeof(path), pid, name);
    if (append_format(buf, "A90_EXECNS_CNSS_PROC_%s_BEGIN path=%s limit=%zu\n", name, path, limit) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        if (append_format(buf,
                          "open-error=%s\nA90_EXECNS_CNSS_PROC_%s_END bytes=0 truncated=0\n",
                          strerror(errno),
                          name) < 0) {
            return -1;
        }
        return 0;
    }
    *captured = true;
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, tmp, room < sizeof(tmp) ? room : sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_format(buf, "\nread-error=%s\n", strerror(errno));
            break;
        }
        if (nread == 0) {
            break;
        }
        if (buffer_append(buf, tmp, (size_t)nread) < 0) {
            close(fd);
            return -1;
        }
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    if (total == 0 || buf->data[buf->len - 1] != '\n') {
        if (append_literal(buf, "\n") < 0) {
            return -1;
        }
    }
    return append_format(buf,
                         "A90_EXECNS_CNSS_PROC_%s_END bytes=%zu truncated=%d\n",
                         name,
                         total,
                         truncated ? 1 : 0);
}


static pid_t wait_for_child_session_pgid(pid_t pid, long timeout_ms) {
    long deadline = monotonic_ms() + timeout_ms;

    while (monotonic_ms() < deadline) {
        pid_t pgid = getpgid(pid);

        if (pgid == pid) {
            return pgid;
        }
        if (pgid < 0 && errno == ESRCH) {
            break;
        }
        usleep(10000);
    }
    return pid;
}

static int append_proc_fd_summary(struct buffer *buf, pid_t pid, bool *captured) {
    char path[MAX_PATH_LEN];
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    *captured = false;
    proc_path(path, sizeof(path), pid, "fd");
    dir = opendir(path);
    if (dir == NULL) {
        return append_format(buf, "cnss_start.fd_summary.error=%s\n", strerror(errno));
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        count++;
    }
    closedir(dir);
    *captured = true;
    return append_format(buf, "cnss_start.fd_summary.count=%d\n", count);
}

static bool parse_pid_name(const char *text, pid_t *pid) {
    char *end = NULL;
    long value;

    if (text == NULL || *text == '\0') {
        return false;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value <= 0) {
        return false;
    }
    *pid = (pid_t)value;
    return true;
}

static void read_proc_comm(pid_t pid, char *out, size_t out_size) {
    char path[MAX_PATH_LEN];
    FILE *file;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    proc_path(path, sizeof(path), pid, "comm");
    file = fopen(path, "re");
    if (file == NULL) {
        snprintf(out, out_size, "unknown");
        return;
    }
    if (fgets(out, (int)out_size, file) == NULL) {
        snprintf(out, out_size, "unknown");
    } else {
        size_t len = strlen(out);

        while (len > 0 && (out[len - 1] == '\n' || out[len - 1] == '\r')) {
            out[--len] = '\0';
        }
    }
    fclose(file);
}

static char read_proc_state(pid_t pid) {
    char path[MAX_PATH_LEN];
    char line[512];
    FILE *file;
    char *close_paren;

    proc_path(path, sizeof(path), pid, "stat");
    file = fopen(path, "re");
    if (file == NULL) {
        return '?';
    }
    if (fgets(line, sizeof(line), file) == NULL) {
        fclose(file);
        return '?';
    }
    fclose(file);
    close_paren = strrchr(line, ')');
    if (close_paren == NULL || close_paren[1] != ' ' || close_paren[2] == '\0') {
        return '?';
    }
    return close_paren[2];
}

static int append_pgid_scan_summary(struct buffer *buf,
                                    const char *prefix,
                                    const char *phase,
                                    pid_t pgid,
                                    int *match_count) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    *match_count = -1;
    dir = opendir("/proc");
    if (dir == NULL) {
        return append_format(buf,
                             "%s.pgid_scan.%s.error=%s\n",
                             prefix,
                             phase,
                             strerror(errno));
    }
    while ((entry = readdir(dir)) != NULL) {
        pid_t pid;
        pid_t candidate_pgid;
        char comm[128];
        char state;

        if (!parse_pid_name(entry->d_name, &pid)) {
            continue;
        }
        candidate_pgid = getpgid(pid);
        if (candidate_pgid < 0 || candidate_pgid != pgid) {
            continue;
        }
        read_proc_comm(pid, comm, sizeof(comm));
        state = read_proc_state(pid);
        if (append_format(buf,
                          "%s.pgid_scan.%s.entry.%d=pid:%ld state:%c comm:%s\n",
                          prefix,
                          phase,
                          count,
                          (long)pid,
                          state,
                          comm) < 0) {
            closedir(dir);
            return -1;
        }
        count++;
    }
    closedir(dir);
    *match_count = count;
    return append_format(buf,
                         "%s.pgid_scan.%s.count=%d\n",
                         prefix,
                         phase,
                         count);
}

static int append_proc_link_compact(struct buffer *buf,
                                    pid_t pid,
                                    const char *label,
                                    const char *name) {
    char path[MAX_PATH_LEN];
    char target[MAX_PATH_LEN];
    ssize_t nread;

    proc_path(path, sizeof(path), pid, name);
    nread = readlink(path, target, sizeof(target) - 1);
    if (nread < 0) {
        return append_format(buf,
                             "capture.%s.%s.error=%s\n",
                             label,
                             name,
                             strerror(errno));
    }
    target[nread] = '\0';
    return append_format(buf,
                         "capture.%s.%s=%s\n",
                         label,
                         name,
                         target);
}

static int append_proc_text_brief(struct buffer *buf,
                                  pid_t pid,
                                  const char *label,
                                  const char *name,
                                  size_t limit) {
    char path[MAX_PATH_LEN];
    char tmp[4096];
    size_t total = 0;
    size_t lines = 0;
    bool truncated = false;
    int fd;

    proc_path(path, sizeof(path), pid, name);
    if (append_format(buf,
                      "capture.%s.%s.path=%s\n",
                      label,
                      name,
                      path) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return append_format(buf,
                             "capture.%s.%s.error=%s\n",
                             label,
                             name,
                             strerror(errno));
    }
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, tmp, room < sizeof(tmp) ? room : sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "capture.%s.%s.read_error=%s\n",
                                 label,
                                 name,
                                 strerror(errno));
        }
        if (nread == 0) {
            break;
        }
        for (ssize_t i = 0; i < nread; i++) {
            if (tmp[i] == '\n') {
                lines++;
            }
        }
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    return append_format(buf,
                         "capture.%s.%s.bytes=%zu\n"
                         "capture.%s.%s.lines=%zu\n"
                         "capture.%s.%s.truncated=%d\n",
                         label,
                         name,
                         total,
                         label,
                         name,
                         lines,
                         label,
                         name,
                         truncated ? 1 : 0);
}

static int append_proc_auxv_brief(struct buffer *buf, pid_t pid, const char *label) {
    char path[MAX_PATH_LEN];
    struct {
        unsigned long key;
        unsigned long value;
    } item;
    int fd;
    int count = 0;

    proc_path(path, sizeof(path), pid, "auxv");
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return append_format(buf,
                             "capture.%s.auxv.error=%s\n",
                             label,
                             strerror(errno));
    }
    while (read(fd, &item, sizeof(item)) == (ssize_t)sizeof(item)) {
        count++;
        if (item.key == 0 || count >= 96) {
            break;
        }
    }
    close(fd);
    return append_format(buf, "capture.%s.auxv.count=%d\n", label, count);
}

static int append_ptrace_siginfo_compact(struct buffer *buf, pid_t pid, const char *label) {
    siginfo_t info;

    memset(&info, 0, sizeof(info));
    if (ptrace(PTRACE_GETSIGINFO, pid, NULL, &info) < 0) {
        return append_format(buf,
                             "capture.%s.siginfo.error=%s\n",
                             label,
                             strerror(errno));
    }
    return append_format(buf,
                         "capture.%s.siginfo.signo=%d\n"
                         "capture.%s.siginfo.code=%d\n"
                         "capture.%s.siginfo.errno=%d\n"
                         "capture.%s.siginfo.addr=%p\n",
                         label,
                         info.si_signo,
                         label,
                         info.si_code,
                         label,
                         info.si_errno,
                         label,
                         info.si_addr);
}

static int append_ptrace_regs_brief(struct buffer *buf, pid_t pid, const char *label) {
    unsigned long long regs[96];
    struct iovec iov;

    memset(regs, 0, sizeof(regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, pid, (void *)(long)NT_PRSTATUS, &iov) < 0) {
        return append_format(buf,
                             "capture.%s.regset.nt_prstatus.error=%s\n",
                             label,
                             strerror(errno));
    }
    return append_format(buf,
                         "capture.%s.regset.nt_prstatus.bytes=%zu\n",
                         label,
                         iov.iov_len);
}

static int append_capture_snapshot_compact(struct buffer *buf,
                                           pid_t pid,
                                           const char *label,
                                           bool include_maps) {
    if (append_format(buf, "capture.%s.pid=%ld\n", label, (long)pid) < 0 ||
        append_proc_link_compact(buf, pid, label, "exe") < 0 ||
        append_proc_link_compact(buf, pid, label, "cwd") < 0 ||
        append_proc_auxv_brief(buf, pid, label) < 0 ||
        append_ptrace_regs_brief(buf, pid, label) < 0 ||
        append_proc_text_brief(buf, pid, label, "status", 8192) < 0) {
        return -1;
    }
    if (include_maps &&
        (append_proc_text_brief(buf, pid, label, "maps", 8192) < 0 ||
         append_proc_text_brief(buf, pid, label, "mountinfo", 8192) < 0)) {
        return -1;
    }
    return 0;
}

static int wait_traced_child_for_cleanup(pid_t pid,
                                         int cleanup_signal,
                                         const char *phase,
                                         long deadline,
                                         struct buffer *stdout_buf,
                                         bool timed_out_state,
                                         bool *child_done,
                                         bool *reaped,
                                         bool *exited_before_timeout,
                                         int *child_exit_code,
                                         int *child_signal,
                                         int *cleanup_stop_continued,
                                         int *cleanup_stop_last_signal,
                                         int *cleanup_continue_errors) {
    while (!*child_done && monotonic_ms() < deadline) {
        int status = 0;
        pid_t wait_rc = waitpid(pid, &status, WNOHANG);

        if (wait_rc == pid) {
            if (WIFEXITED(status)) {
                *child_done = true;
                *reaped = true;
                *exited_before_timeout = !timed_out_state;
                *child_exit_code = WEXITSTATUS(status);
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.exit=%d\n",
                                     phase,
                                     *child_exit_code);
            }
            if (WIFSIGNALED(status)) {
                *child_done = true;
                *reaped = true;
                *exited_before_timeout = !timed_out_state;
                *child_signal = WTERMSIG(status);
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.signal=%d\n",
                                     phase,
                                     *child_signal);
            }
            if (WIFSTOPPED(status)) {
                int stop_signal = WSTOPSIG(status);
                unsigned int event = (unsigned int)status >> 16;

                (*cleanup_stop_continued)++;
                *cleanup_stop_last_signal = stop_signal;
                if (append_format(stdout_buf,
                                  "service_manager_start.cleanup.%s.stop.signal=%d\n"
                                  "service_manager_start.cleanup.%s.stop.event=%u\n"
                                  "service_manager_start.cleanup.%s.stop.deliver_signal=%d\n",
                                  phase,
                                  stop_signal,
                                  phase,
                                  event,
                                  phase,
                                  cleanup_signal) < 0) {
                    return -1;
                }
                if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)cleanup_signal) < 0) {
                    (*cleanup_continue_errors)++;
                    if (append_format(stdout_buf,
                                      "service_manager_start.cleanup.%s.cont.error=%s\n",
                                      phase,
                                      strerror(errno)) < 0) {
                        return -1;
                    }
                    kill(pid, cleanup_signal);
                }
                continue;
            }
            if (append_format(stdout_buf,
                              "service_manager_start.cleanup.%s.unexpected_status=0x%x\n",
                              phase,
                              status) < 0) {
                return -1;
            }
        } else if (wait_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (errno == ECHILD) {
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.wait.echild=1\n",
                                     phase);
            }
            return append_format(stdout_buf,
                                 "service_manager_start.cleanup.%s.wait.error=%s\n",
                                 phase,
                                 strerror(errno));
        }
        usleep(50000);
    }
    return 0;
}

static int run_cnss_start_only_guarded(const struct config *cfg,
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
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "cnss_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.mode=guarded\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.target=/vendor/bin/cnss-daemon\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.argv=/vendor/bin/cnss-daemon -n -l\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.cnss_diag=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.scan_connect_linkup=0\n") < 0) {
        return -1;
    }

    if (!cfg->allow_cnss_start_only) {
        if (append_literal(stdout_buf, "cnss_start.allowed=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exec_attempted=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.child_started=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.pid=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.pgid=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.observable=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exited=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exit_code=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.signal=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.timed_out=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.term_sent=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.kill_sent=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.reaped=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.proc_status_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.fd_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.maps_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.postflight_safe=1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.result=start-only-blocked\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.reason=missing-allow-cnss-start-only\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.end=1\n") < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf, "cnss_start.allowed=1\n") < 0) {
        return -1;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "cnss_start.exec_attempted=0\n"
                          "cnss_start.child_started=0\n"
                          "cnss_start.pid=-1\n"
                          "cnss_start.pgid=-1\n"
                          "cnss_start.observable=0\n"
                          "cnss_start.exited=0\n"
                          "cnss_start.exit_code=-1\n"
                          "cnss_start.signal=0\n"
                          "cnss_start.timed_out=0\n"
                          "cnss_start.term_sent=0\n"
                          "cnss_start.kill_sent=0\n"
                          "cnss_start.reaped=0\n"
                          "cnss_start.proc_status_captured=0\n"
                          "cnss_start.fd_summary_captured=0\n"
                          "cnss_start.maps_summary_captured=0\n"
                          "cnss_start.postflight_safe=0\n"
                          "cnss_start.result=manual-review-required\n"
                          "cnss_start.reason=pipe-failed-%s\n"
                          "cnss_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "cnss_start.exec_attempted=0\n"
                          "cnss_start.child_started=0\n"
                          "cnss_start.pid=-1\n"
                          "cnss_start.pgid=-1\n"
                          "cnss_start.observable=0\n"
                          "cnss_start.exited=0\n"
                          "cnss_start.exit_code=-1\n"
                          "cnss_start.signal=0\n"
                          "cnss_start.timed_out=0\n"
                          "cnss_start.term_sent=0\n"
                          "cnss_start.kill_sent=0\n"
                          "cnss_start.reaped=0\n"
                          "cnss_start.proc_status_captured=0\n"
                          "cnss_start.fd_summary_captured=0\n"
                          "cnss_start.maps_summary_captured=0\n"
                          "cnss_start.postflight_safe=0\n"
                          "cnss_start.result=manual-review-required\n"
                          "cnss_start.reason=fork-failed-%s\n"
                          "cnss_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const daemon_argv[] = {
            (char *)"/vendor/bin/cnss-daemon",
            (char *)"-n",
            (char *)"-l",
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("cnss_child.begin=1\n");
        if (apply_android_identity_contract("cnss_child") < 0) {
            printf("cnss_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("cnss_child.exec_target=/vendor/bin/cnss-daemon -n -l\n");
        fflush(stdout);
        execv("/vendor/bin/cnss-daemon", daemon_argv);
        printf("cnss_child.exec_error=%s\n", strerror(errno));
        printf("cnss_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "cnss_start.exec_attempted=1\n"
                      "cnss_start.child_started=1\n"
                      "cnss_start.pid=%ld\n"
                      "cnss_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            break;
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
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                exited_before_timeout = !*timed_out;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "cnss_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            struct pollfd fds[2];
            int nfds = 0;

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
            if (nfds > 0 && poll(fds, nfds, 50) > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            } else {
                usleep(50000);
            }
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            }
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);

    if (append_format(stdout_buf,
                      "cnss_start.observable=%d\n"
                      "cnss_start.exited=%d\n"
                      "cnss_start.exit_code=%d\n"
                      "cnss_start.signal=%d\n"
                      "cnss_start.timed_out=%d\n"
                      "cnss_start.term_sent=%d\n"
                      "cnss_start.kill_sent=%d\n"
                      "cnss_start.reaped=%d\n"
                      "cnss_start.proc_status_captured=%d\n"
                      "cnss_start.fd_summary_captured=%d\n"
                      "cnss_start.maps_summary_captured=%d\n"
                      "cnss_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-reboot-required\n"
                       "cnss_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-pass\n"
                       "cnss_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-runtime-gap\n"
                       "cnss_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "cnss_start.result=manual-review-required\n"
                       "cnss_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "cnss_start.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_service_manager_start_only_guarded_ptrace(const struct config *cfg,
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
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    bool exec_captured = false;
    bool crash_captured = false;
    bool residual_kill_sent = false;
    bool residual_cleared = false;
    int cleanup_stop_continued = 0;
    int cleanup_stop_last_signal = 0;
    int cleanup_continue_errors = 0;
    int residual_before_count = -1;
    int residual_after_count = -1;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "service_manager_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.mode=guarded\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.capture_mode=ptrace-lite\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.capture_detail=compact\n") < 0 ||
        append_format(stdout_buf, "service_manager_start.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "service_manager_start.argv=%s\n", cfg->target) < 0 ||
        append_literal(stdout_buf, "service_manager_start.wifi_hal=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.scan_connect_linkup=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.allowed=1\n") < 0) {
        return -1;
    }
    printf("capture.mode=ptrace-lite\n");
    printf("capture.detail=compact\n");
    printf("capture.scope=service-manager-start-only\n");

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.capture_exec=0\n"
                          "service_manager_start.capture_crash=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=pipe-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.capture_exec=0\n"
                          "service_manager_start.capture_crash=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=fork-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const manager_argv[] = {
            (char *)cfg->target,
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("service_manager_child.begin=1\n");
        if (apply_service_manager_identity_contract("service_manager_child") < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("service_manager_child.exec_target=%s\n", cfg->target);
        fflush(stdout);
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) < 0) {
            printf("service_manager_child.ptrace_traceme_error=%s\n", strerror(errno));
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(122);
        }
        raise(SIGSTOP);
        execv(cfg->target, manager_argv);
        printf("service_manager_child.exec_error=%s\n", strerror(errno));
        printf("service_manager_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "service_manager_start.exec_attempted=1\n"
                      "service_manager_start.child_started=1\n"
                      "service_manager_start.pid=%ld\n"
                      "service_manager_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }

    if (waitpid(pid, &status, 0) != pid) {
        printf("capture.initial_wait.error=%s\n", strerror(errno));
        goto fail;
    }
    if (!WIFSTOPPED(status)) {
        printf("capture.initial_stop.unexpected_status=0x%x\n", status);
        if (WIFEXITED(status)) {
            child_done = true;
            reaped = true;
            exited_before_timeout = true;
            *child_exit_code = WEXITSTATUS(status);
        } else if (WIFSIGNALED(status)) {
            child_done = true;
            reaped = true;
            exited_before_timeout = true;
            *child_signal = WTERMSIG(status);
        }
    } else {
        printf("capture.initial_stop.signal=%d\n", WSTOPSIG(status));
        if (ptrace(PTRACE_SETOPTIONS,
                   pid,
                   NULL,
                   (void *)(long)(PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL)) < 0) {
            printf("capture.setoptions.error=%s\n", strerror(errno));
        }
        if (ptrace(PTRACE_CONT, pid, NULL, NULL) < 0) {
            printf("capture.initial_cont.error=%s\n", strerror(errno));
            goto fail;
        }
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            printf("capture.timeout.kill=1\n");
            break;
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
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                if (WIFEXITED(status)) {
                    child_done = true;
                    reaped = true;
                    exited_before_timeout = !*timed_out;
                    *child_exit_code = WEXITSTATUS(status);
                    printf("capture.child.exit=%d\n", *child_exit_code);
                } else if (WIFSIGNALED(status)) {
                    child_done = true;
                    reaped = true;
                    exited_before_timeout = !*timed_out;
                    *child_signal = WTERMSIG(status);
                    printf("capture.child.signal=%d\n", *child_signal);
                } else if (WIFSTOPPED(status)) {
                    int sig = WSTOPSIG(status);
                    unsigned int event = (unsigned int)status >> 16;
                    int deliver_sig = 0;

                    printf("capture.stop.signal=%d\n", sig);
                    printf("capture.stop.event=%u\n", event);
                    if (sig == SIGTRAP && !exec_captured) {
                        exec_captured = true;
                        printf("capture.exec_stop=1\n");
                        if (append_capture_snapshot_compact(stdout_buf, pid, "exec", true) < 0) {
                            goto fail;
                        }
                    } else if (sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) {
                        crash_captured = true;
                        printf("capture.crash_stop=1\n");
                        if (append_ptrace_siginfo_compact(stdout_buf, pid, "crash") < 0 ||
                            append_capture_snapshot_compact(stdout_buf, pid, "crash", true) < 0) {
                            goto fail;
                        }
                        deliver_sig = sig;
                    } else if (sig != SIGTRAP) {
                        deliver_sig = sig;
                    }
                    if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)deliver_sig) < 0) {
                        printf("capture.cont.error=%s\n", strerror(errno));
                        kill(-pgid, SIGKILL);
                        kill(pid, SIGKILL);
                    }
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "service_manager_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        if (wait_traced_child_for_cleanup(pid,
                                          SIGTERM,
                                          "term",
                                          deadline,
                                          stdout_buf,
                                          *timed_out,
                                          &child_done,
                                          &reaped,
                                          &exited_before_timeout,
                                          child_exit_code,
                                          child_signal,
                                          &cleanup_stop_continued,
                                          &cleanup_stop_last_signal,
                                          &cleanup_continue_errors) < 0) {
            goto fail;
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        if (wait_traced_child_for_cleanup(pid,
                                          SIGKILL,
                                          "kill",
                                          deadline,
                                          stdout_buf,
                                          *timed_out,
                                          &child_done,
                                          &reaped,
                                          &exited_before_timeout,
                                          child_exit_code,
                                          child_signal,
                                          &cleanup_stop_continued,
                                          &cleanup_stop_last_signal,
                                          &cleanup_continue_errors) < 0) {
            goto fail;
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    if (reaped && pgid > 1) {
        errno = 0;
        postflight_safe = kill(-pgid, 0) < 0 && errno == ESRCH;
        if (!postflight_safe) {
            if (append_pgid_scan_summary(stdout_buf,
                                         "service_manager_start",
                                         "before_final_kill",
                                         pgid,
                                         &residual_before_count) < 0) {
                goto fail;
            }
            if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
                residual_kill_sent = true;
                kill_sent = true;
            }
            deadline = monotonic_ms() + 1000L;
            while (monotonic_ms() < deadline) {
                errno = 0;
                if (kill(-pgid, 0) < 0 && errno == ESRCH) {
                    residual_cleared = true;
                    break;
                }
                usleep(50000);
            }
            if (append_pgid_scan_summary(stdout_buf,
                                         "service_manager_start",
                                         "after_final_kill",
                                         pgid,
                                         &residual_after_count) < 0) {
                goto fail;
            }
        }
        errno = 0;
        postflight_safe = kill(-pgid, 0) < 0 && errno == ESRCH;
        if (postflight_safe) {
            residual_cleared = true;
        }
    } else {
        postflight_safe = false;
    }

    if (append_format(stdout_buf,
                      "service_manager_start.observable=%d\n"
                      "service_manager_start.exited=%d\n"
                      "service_manager_start.exit_code=%d\n"
                      "service_manager_start.signal=%d\n"
                      "service_manager_start.timed_out=%d\n"
                      "service_manager_start.term_sent=%d\n"
                      "service_manager_start.kill_sent=%d\n"
                      "service_manager_start.reaped=%d\n"
                      "service_manager_start.proc_status_captured=%d\n"
                      "service_manager_start.fd_summary_captured=%d\n"
                      "service_manager_start.maps_summary_captured=%d\n"
                      "service_manager_start.capture_exec=%d\n"
                      "service_manager_start.capture_crash=%d\n"
                      "service_manager_start.cleanup_stop_continued=%d\n"
                      "service_manager_start.cleanup_stop_last_signal=%d\n"
                      "service_manager_start.cleanup_continue_errors=%d\n"
                      "service_manager_start.residual_kill_sent=%d\n"
                      "service_manager_start.residual_cleared=%d\n"
                      "service_manager_start.residual_before_count=%d\n"
                      "service_manager_start.residual_after_count=%d\n"
                      "service_manager_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      exec_captured ? 1 : 0,
                      crash_captured ? 1 : 0,
                      cleanup_stop_continued,
                      cleanup_stop_last_signal,
                      cleanup_continue_errors,
                      residual_kill_sent ? 1 : 0,
                      residual_cleared ? 1 : 0,
                      residual_before_count,
                      residual_after_count,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-reboot-required\n"
                       "service_manager_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-pass\n"
                       "service_manager_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-runtime-gap\n"
                       "service_manager_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "service_manager_start.result=manual-review-required\n"
                       "service_manager_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "service_manager_start.end=1\n");
    printf("capture.exec_captured=%d\n", exec_captured ? 1 : 0);
    printf("capture.crash_captured=%d\n", crash_captured ? 1 : 0);
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        if (pgid > 1) {
            kill(-pgid, SIGKILL);
        }
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_service_manager_start_only_guarded(const struct config *cfg,
                                                  const struct paths *paths,
                                                  struct buffer *stdout_buf,
                                                  struct buffer *stderr_buf,
                                                  int *child_exit_code,
                                                  int *child_signal,
                                                  bool *timed_out) {
    if (streq(cfg->capture_mode, "ptrace-lite")) {
        return run_service_manager_start_only_guarded_ptrace(cfg,
                                                            paths,
                                                            stdout_buf,
                                                            stderr_buf,
                                                            child_exit_code,
                                                            child_signal,
                                                            timed_out);
    }

    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "service_manager_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.mode=guarded\n") < 0 ||
        append_format(stdout_buf, "service_manager_start.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "service_manager_start.argv=%s\n", cfg->target) < 0 ||
        append_literal(stdout_buf, "service_manager_start.wifi_hal=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.scan_connect_linkup=0\n") < 0) {
        return -1;
    }

    if (!cfg->allow_service_manager_start_only) {
        if (append_literal(stdout_buf, "service_manager_start.allowed=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exec_attempted=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.child_started=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.pid=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.pgid=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.observable=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exited=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exit_code=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.signal=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.timed_out=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.term_sent=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.kill_sent=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.reaped=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.proc_status_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.fd_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.maps_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.postflight_safe=1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.result=start-only-blocked\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.reason=missing-allow-service-manager-start-only\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.end=1\n") < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf, "service_manager_start.allowed=1\n") < 0) {
        return -1;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=pipe-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=fork-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const manager_argv[] = {
            (char *)cfg->target,
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("service_manager_child.begin=1\n");
        if (apply_service_manager_identity_contract("service_manager_child") < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("service_manager_child.exec_target=%s\n", cfg->target);
        fflush(stdout);
        execv(cfg->target, manager_argv);
        printf("service_manager_child.exec_error=%s\n", strerror(errno));
        printf("service_manager_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "service_manager_start.exec_attempted=1\n"
                      "service_manager_start.child_started=1\n"
                      "service_manager_start.pid=%ld\n"
                      "service_manager_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            break;
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
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                exited_before_timeout = !*timed_out;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "service_manager_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);

    if (append_format(stdout_buf,
                      "service_manager_start.observable=%d\n"
                      "service_manager_start.exited=%d\n"
                      "service_manager_start.exit_code=%d\n"
                      "service_manager_start.signal=%d\n"
                      "service_manager_start.timed_out=%d\n"
                      "service_manager_start.term_sent=%d\n"
                      "service_manager_start.kill_sent=%d\n"
                      "service_manager_start.reaped=%d\n"
                      "service_manager_start.proc_status_captured=%d\n"
                      "service_manager_start.fd_summary_captured=%d\n"
                      "service_manager_start.maps_summary_captured=%d\n"
                      "service_manager_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-reboot-required\n"
                       "service_manager_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-pass\n"
                       "service_manager_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-runtime-gap\n"
                       "service_manager_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "service_manager_start.result=manual-review-required\n"
                       "service_manager_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "service_manager_start.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
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
    if (materialize_null_devices(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_service_manager_binder_devices(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_private_properties(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_data_wifi(cfg, paths, error_buf, error_size) < 0) {
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
        if (streq(cfg->vndk_apex_alias_mode, "none")) {
            if (bind_ro(system_apex, paths->apex) < 0) {
                snprintf(error_buf, error_size, "bind apex: %s", strerror(errno));
                return -1;
            }
        } else if (materialize_apex_bind_farm(cfg, paths, system_apex, error_buf, error_size) < 0) {
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
    printf("capture_mode=%s\n", cfg.capture_mode);
    printf("null_device_mode=%s\n", cfg.null_device_mode);
    printf("data_wifi_mode=%s\n", cfg.data_wifi_mode);
    printf("vndk_apex_alias_mode=%s\n", cfg.vndk_apex_alias_mode);
    printf("linkerconfig_mode=%s\n", cfg.linkerconfig_mode);
    printf("target_profile=%s\n", cfg.target_profile);
    printf("env_mode=%s\n", cfg.env_mode);
    printf("linkerconfig_source=%s\n",
           cfg.linkerconfig_source != NULL ? cfg.linkerconfig_source : "<none>");
    printf("apex_libraries_source=%s\n",
           cfg.apex_libraries_source != NULL ? cfg.apex_libraries_source : "<none>");
    printf("property_root=%s\n", cfg.property_root != NULL ? cfg.property_root : "<none>");
    printf("property_key=%s\n", cfg.property_key != NULL ? cfg.property_key : "<none>");
    printf("system_root=%s\n", cfg.system_root);
    printf("vendor_block=%s\n", cfg.vendor_block);
    printf("vendor_fstype=%s\n", cfg.vendor_fstype);
    printf("target=%s\n", cfg.target);
    printf("linker=%s\n", cfg.linker != NULL ? cfg.linker : "<none>");
    printf("timeout_sec=%d\n", cfg.timeout_sec);
    printf("allow_cnss_start_only=%d\n", cfg.allow_cnss_start_only ? 1 : 0);
    printf("allow_service_manager_start_only=%d\n",
           cfg.allow_service_manager_start_only ? 1 : 0);

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
    printf("apex_mount_source=%s\n",
           paths.apex[0] == '\0'
               ? "<absent>"
               : (streq(cfg.vndk_apex_alias_mode, "none")
                      ? "/mnt/system/system/apex"
                      : "<private-bind-farm>"));
    printf("linkerconfig_bytes=%zu\n", linkerconfig_bytes);
    printf("linkerconfig_hash=0x%016llx\n", (unsigned long long)linkerconfig_hash);
    print_preexec_context(&cfg, &paths);
    if (streq(cfg.mode, "identity-probe")) {
        run_rc = run_identity_probe(&cfg,
                                    &paths,
                                    &stdout_buf,
                                    &stderr_buf,
                                    &child_exit_code,
                                    &child_signal,
                                    &timed_out);
    } else if (streq(cfg.mode, "property-lookup")) {
        run_rc = run_property_lookup(&cfg,
                                     &paths,
                                     &stdout_buf,
                                     &stderr_buf,
                                     &child_exit_code,
                                     &child_signal,
                                     &timed_out);
    } else if (streq(cfg.mode, "cnss-start-only")) {
        run_rc = run_cnss_start_only_guarded(&cfg,
                                             &paths,
                                             &stdout_buf,
                                             &stderr_buf,
                                             &child_exit_code,
                                             &child_signal,
                                             &timed_out);
    } else if (streq(cfg.mode, "service-manager-start-only")) {
        run_rc = run_service_manager_start_only_guarded(&cfg,
                                                        &paths,
                                                        &stdout_buf,
                                                        &stderr_buf,
                                                        &child_exit_code,
                                                        &child_signal,
                                                        &timed_out);
    } else {
        run_rc = run_linker_list(&cfg,
                                 &paths,
                                 &stdout_buf,
                                 &stderr_buf,
                                 &child_exit_code,
                                 &child_signal,
                                 &timed_out);
    }
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
