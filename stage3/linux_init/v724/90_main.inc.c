/* Included by stage3/linux_init/init_v724.c. Do not compile standalone. */

static void storage_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void storage_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}

static void selftest_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void selftest_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}


#define A90_V641_SIBLING_SSCTL_FLAG "/cache/native-init-sibling-fwssctl-v641"
#define A90_V641_SIBLING_SSCTL_LOG "/cache/native-init-sibling-fwssctl-v641.log"
#define A90_V641_SIBLING_SSCTL_TIMEOUT_MS 5000
#define A90_V641_VENDOR_DIR "/vendor"
#define A90_V641_FW_MNT_DIR "/vendor/firmware_mnt"
#define A90_V641_FW_MODEM_DIR "/vendor/firmware-modem"
#define A90_V724_QRTR_BOOT_FLAG "/cache/native-init-qrtr-servloc-boot-v724"
#define A90_V724_QRTR_BOOT_LOG "/cache/native-init-qrtr-servloc-boot-v724.log"
#define A90_V724_QRTR_BOOT_PID "/cache/native-init-qrtr-servloc-boot-v724.pid"
#define A90_V724_QRTR_HELPER "/cache/bin/a90_android_execns_probe"
#define A90_V724_QRTR_TIMEOUT_SEC "8"
#define A90_V724_QRTR_MODE "wifi-companion-android-order-post-sysmon-observer-start-only"
#ifdef A90_WIFI_TEST_BOOT
#ifndef A90_WIFI_TEST_BOOT_LABEL
#define A90_WIFI_TEST_BOOT_LABEL "v1393"
#endif
#ifndef A90_WIFI_TEST_BOOT_KLOG_PREFIX
#define A90_WIFI_TEST_BOOT_KLOG_PREFIX "A90v1393"
#endif
#ifndef A90_WIFI_TEST_BOOT_DISABLE
#define A90_WIFI_TEST_BOOT_DISABLE "/cache/native-init-wifi-test-boot-v1393.disable"
#endif
#ifndef A90_WIFI_TEST_BOOT_LOG
#define A90_WIFI_TEST_BOOT_LOG "/cache/native-init-wifi-test-boot-v1393.log"
#endif
#ifndef A90_WIFI_TEST_BOOT_SUMMARY
#define A90_WIFI_TEST_BOOT_SUMMARY "/cache/native-init-wifi-test-boot-v1393.summary"
#endif
#ifndef A90_WIFI_TEST_BOOT_PID
#define A90_WIFI_TEST_BOOT_PID "/cache/native-init-wifi-test-boot-v1393.pid"
#endif
#ifndef A90_WIFI_TEST_BOOT_WATCHER_PID
#define A90_WIFI_TEST_BOOT_WATCHER_PID "/cache/native-init-wifi-test-boot-v1393-watcher.pid"
#endif
#ifndef A90_WIFI_TEST_BOOT_WATCH_SEC
#define A90_WIFI_TEST_BOOT_WATCH_SEC 35
#endif
#ifndef A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
#define A90_WIFI_TEST_BOOT_SUPERVISE_HELPER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC
#define A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC 40
#endif
#ifndef A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
#define A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
#define A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC 45
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT "/cache/native-init-wifi-test-boot-v1393-rc1-watcher.result"
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT
#define A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT "/cache/native-init-wifi-test-boot-v1393-rc1-window.result"
#endif
#define A90_V1393_WIFI_TEST_DISABLE A90_WIFI_TEST_BOOT_DISABLE
#define A90_V1393_WIFI_TEST_LOG A90_WIFI_TEST_BOOT_LOG
#define A90_V1393_WIFI_TEST_SUMMARY A90_WIFI_TEST_BOOT_SUMMARY
#define A90_V1393_WIFI_TEST_PID A90_WIFI_TEST_BOOT_PID
#define A90_V1393_WIFI_TEST_WATCHER_PID A90_WIFI_TEST_BOOT_WATCHER_PID
#define A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT
#define A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT
#define A90_V1393_WIFI_TEST_HELPER "/bin/a90_android_execns_probe"
#define A90_V1393_WIFI_TEST_TIMEOUT_SEC "30"
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-post-pm-mdm-helper-esoc-observer"
#define A90_V1393_WIFI_TEST_PROPERTY_ROOT "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
#define A90_V1393_WIFI_TEST_REAL_LD_CONFIG "/cache/bin/a90_real_ld.config.txt"
#define A90_V1393_WIFI_TEST_REAL_APEX_LIBRARIES "/cache/bin/a90_real_apex.libraries.config.txt"
#define A90_V1393_WIFI_TEST_PRIVATE_CNSS "/cache/bin/cnss-daemon.sdx50m"
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
static int v1393_wifi_test_debugfs_mounted_by_pid1;
#endif
#endif

static int v641_append_ssctl_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V641_SIBLING_SSCTL_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v724_append_qrtr_boot_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V724_QRTR_BOOT_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v724_write_private_file(const char *path, const char *text) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, text, strlen(text));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static int v724_read_qrtr_boot_flag(char *state, size_t state_size) {
    int fd;
    ssize_t rd;

    if (state == NULL || state_size == 0) {
        return -EINVAL;
    }
    fd = open(A90_V724_QRTR_BOOT_FLAG, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rd = read(fd, state, state_size - 1);
    close(fd);
    if (rd < 0) {
        return negative_errno_or(EIO);
    }
    state[rd] = '\0';
    trim_newline(state);
    return 0;
}

static bool v724_qrtr_boot_flag_armed(void) {
    char state[32];
    int rc = v724_read_qrtr_boot_flag(state, sizeof(state));

    if (rc < 0) {
        a90_logf("wifi-v724", "qrtr servloc boot disabled flag=%s errno=%d error=%s",
                 A90_V724_QRTR_BOOT_FLAG,
                 -rc,
                 strerror(-rc));
        klogf("<6>A90v724: qrtr servloc boot disabled flag=%s\n",
              A90_V724_QRTR_BOOT_FLAG);
        return false;
    }

    if (strcmp(state, "run") != 0) {
        a90_logf("wifi-v724", "qrtr servloc boot ignored flag=%s state=%.16s",
                 A90_V724_QRTR_BOOT_FLAG,
                 state);
        klogf("<6>A90v724: qrtr servloc boot ignored state=%.16s\n", state);
        return false;
    }

    if (unlink(A90_V724_QRTR_BOOT_FLAG) < 0 && errno != ENOENT) {
        a90_logf("wifi-v724", "qrtr servloc boot flag unlink warning errno=%d error=%s",
                 errno,
                 strerror(errno));
    }
    sync();
    return true;
}

static int v724_prepare_selinuxfs_surface(void) {
    struct stat st;

    if (stat("/sys/fs/selinux/status", &st) == 0) {
        return 0;
    }
    if (ensure_dir("/sys/fs", 0755) < 0 && errno != EEXIST) {
        return negative_errno_or(EIO);
    }
    if (ensure_dir("/sys/fs/selinux", 0755) < 0 && errno != EEXIST) {
        return negative_errno_or(EIO);
    }
    if (mount("selinuxfs", "/sys/fs/selinux", "selinuxfs", 0, NULL) < 0 &&
        errno != EBUSY) {
        return negative_errno_or(EIO);
    }
    if (stat("/sys/fs/selinux/status", &st) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int v724_spawn_qrtr_servloc_boot_helper(pid_t *pid_out) {
    static char *const envp[] = {
        "PATH=/cache/bin:/bin:/system/bin:/vendor/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    static char *const argv[] = {
        A90_V724_QRTR_HELPER,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        A90_V724_QRTR_MODE,
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "minimal-vendor",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        A90_V724_QRTR_TIMEOUT_SEC,
        "--allow-wifi-companion-start-only",
        "--allow-qrtr-ns-readback",
        NULL
    };
    struct a90_run_config config = {
        .tag = "wifi-v724-qrtr-servloc-boot",
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_V724_QRTR_BOOT_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 1000,
    };

    return a90_run_spawn(&config, pid_out);
}

static void v724_run_qrtr_servloc_boot_once(void) {
    struct stat st;
    pid_t pid = -1;
    int rc;
    char pid_text[32];

    if (!v724_qrtr_boot_flag_armed()) {
        return;
    }

    boot_splash_set_line(5, "[ WIFI   ] V724 QRTR BOOT PROOF");
    boot_auto_frame();
    a90_console_printf("# V724 QRTR/service-locator boot proof: armed one-shot.\r\n");
    a90_logf("wifi-v724", "qrtr servloc boot proof armed timeout_sec=%s",
             A90_V724_QRTR_TIMEOUT_SEC);
    a90_timeline_record(0, 0, "wifi-v724-qrtr-servloc", "armed one-shot");
    klogf("<6>A90v724: qrtr servloc boot proof armed\n");
    (void)v724_append_qrtr_boot_log("armed ms=%ld mode=%s timeout_sec=%s\n",
                                   monotonic_millis(),
                                   A90_V724_QRTR_MODE,
                                   A90_V724_QRTR_TIMEOUT_SEC);

    if (stat(A90_V724_QRTR_HELPER, &st) < 0 || !S_ISREG(st.st_mode)) {
        int saved_errno = errno != 0 ? errno : ENOENT;

        a90_console_printf("# V724 QRTR/service-locator boot proof: helper missing.\r\n");
        a90_logf("wifi-v724", "helper missing path=%s errno=%d error=%s",
                 A90_V724_QRTR_HELPER,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v724-qrtr-servloc", "helper missing");
        klogf("<6>A90v724: qrtr servloc boot helper missing\n");
        (void)v724_append_qrtr_boot_log("helper missing path=%s errno=%d error=%s\n",
                                       A90_V724_QRTR_HELPER,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    if (prepare_android_layout(false) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        a90_console_printf("# V724 QRTR/service-locator boot proof: android layout failed.\r\n");
        a90_logf("wifi-v724", "android layout failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v724-qrtr-servloc", "android layout failed");
        klogf("<6>A90v724: qrtr servloc boot android layout failed rc=-%d\n", saved_errno);
        (void)v724_append_qrtr_boot_log("android layout failed errno=%d error=%s\n",
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    rc = v724_prepare_selinuxfs_surface();
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_console_printf("# V724 QRTR/service-locator boot proof: selinuxfs failed.\r\n");
        a90_logf("wifi-v724", "selinuxfs failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v724-qrtr-servloc", "selinuxfs failed");
        klogf("<6>A90v724: qrtr servloc boot selinuxfs failed rc=%d\n", rc);
        (void)v724_append_qrtr_boot_log("selinuxfs failed rc=%d errno=%d error=%s\n",
                                       rc,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    rc = v724_spawn_qrtr_servloc_boot_helper(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_console_printf("# V724 QRTR/service-locator boot proof: helper spawn failed.\r\n");
        a90_logf("wifi-v724", "helper spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v724-qrtr-servloc", "spawn failed");
        klogf("<6>A90v724: qrtr servloc boot helper spawn failed rc=%d\n", rc);
        (void)v724_append_qrtr_boot_log("spawn failed rc=%d errno=%d error=%s\n",
                                       rc,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V724_QRTR_BOOT_PID, pid_text);
    a90_console_printf("# V724 QRTR/service-locator boot proof: helper pid=%ld.\r\n",
                       (long)pid);
    a90_logf("wifi-v724", "helper spawned pid=%ld mode=%s",
             (long)pid,
             A90_V724_QRTR_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v724-qrtr-servloc",
                        "helper spawned pid=%ld",
                        (long)pid);
    klogf("<6>A90v724: qrtr servloc boot helper spawned pid=%ld\n", (long)pid);
    (void)v724_append_qrtr_boot_log("spawned pid=%ld mode=%s\n",
                                   (long)pid,
                                   A90_V724_QRTR_MODE);
}

#ifdef A90_WIFI_TEST_BOOT
static int v1393_append_wifi_test_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V1393_WIFI_TEST_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v1393_reset_wifi_test_log(void) {
    int fd;
    int rc;

    fd = open(A90_V1393_WIFI_TEST_LOG,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }
    rc = dprintf(fd,
                 "log_reset ms=%ld label=%s log=%s summary=%s\n",
                 monotonic_millis(),
                 A90_WIFI_TEST_BOOT_LABEL,
                 A90_V1393_WIFI_TEST_LOG,
                 A90_V1393_WIFI_TEST_SUMMARY);
    if (close(fd) < 0 && rc >= 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
static int v1393_prepare_wifi_test_debugfs(void) {
    struct stat st;

    if (lstat("/sys/kernel/debug/pci-msm/case", &st) == 0) {
        v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
        return 0;
    }
    if (mkdir("/sys/kernel/debug", 0755) < 0 && errno != EEXIST) {
        return -errno;
    }
    if (mount("debugfs",
              "/sys/kernel/debug",
              "debugfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) < 0) {
        if (errno == EBUSY) {
            v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
            return 0;
        }
        return -errno;
    }
    v1393_wifi_test_debugfs_mounted_by_pid1 = 1;
    return 0;
}

static int v1393_cleanup_wifi_test_debugfs(void) {
    if (!v1393_wifi_test_debugfs_mounted_by_pid1) {
        return 0;
    }
    if (umount("/sys/kernel/debug") < 0) {
        return -errno;
    }
    v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
    return 0;
}
#endif

#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
static int v1393_write_wifi_test_sysfs_string(const char *path, const char *value) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, value, strlen(value));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static int v1393_pid1_rc1_write_corrected_enumerate(void) {
    int rc;

    rc = v1393_write_wifi_test_sysfs_string("/sys/kernel/debug/pci-msm/rc_sel", "2\n");
    if (rc < 0) {
        return rc;
    }
    return v1393_write_wifi_test_sysfs_string("/sys/kernel/debug/pci-msm/case", "11\n");
}

static bool v1393_pid1_rc1_trigger_line(const char *line) {
    if (line == NULL) {
        return false;
    }
    return strstr(line, "__subsystem_get: esoc0 count") != NULL ||
           strstr(line, "mdm_subsys_powerup") != NULL;
}

#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
static bool v1393_rc1_window_line_matches(const char *line, const char *const *needles) {
    size_t index;

    if (line == NULL || needles == NULL) {
        return false;
    }
    for (index = 0; needles[index] != NULL; index++) {
        if (strstr(line, needles[index]) != NULL) {
            return true;
        }
    }
    return false;
}

static void v1393_rc1_window_append_matching_lines(int out_fd,
                                                   const char *sample,
                                                   const char *source_name,
                                                   const char *path,
                                                   const char *const *needles) {
    int in_fd;
    char chunk[512];
    char line[512];
    size_t line_len = 0;
    int matches = 0;
    int truncated = 0;

    in_fd = open(path, O_RDONLY | O_CLOEXEC);
    if (in_fd < 0) {
        dprintf(out_fd,
                "sample=%s source=%s path=%s unreadable_errno=%d\n",
                sample,
                source_name,
                path,
                errno != 0 ? errno : EIO);
        return;
    }

    for (;;) {
        ssize_t rd = read(in_fd, chunk, sizeof(chunk));
        ssize_t offset;

        if (rd == 0) {
            break;
        }
        if (rd < 0) {
            dprintf(out_fd,
                    "sample=%s source=%s path=%s read_errno=%d matches=%d truncated=%d\n",
                    sample,
                    source_name,
                    path,
                    errno != 0 ? errno : EIO,
                    matches,
                    truncated);
            close(in_fd);
            return;
        }

        for (offset = 0; offset < rd; offset++) {
            char ch = chunk[offset];

            if (ch == '\n' || line_len + 1 >= sizeof(line)) {
                line[line_len] = '\0';
                if (v1393_rc1_window_line_matches(line, needles)) {
                    flatten_inline_text(line);
                    dprintf(out_fd,
                            "sample=%s source=%s match_%02d=%s\n",
                            sample,
                            source_name,
                            matches,
                            line);
                    matches++;
                    if (matches >= 16) {
                        close(in_fd);
                        dprintf(out_fd,
                                "sample=%s source=%s matches=%d truncated=1\n",
                                sample,
                                source_name,
                                matches);
                        return;
                    }
                }
                if (line_len + 1 >= sizeof(line) && ch != '\n') {
                    truncated = 1;
                }
                line_len = 0;
                continue;
            }
            line[line_len++] = ch;
        }
    }

    if (line_len > 0) {
        line[line_len] = '\0';
        if (v1393_rc1_window_line_matches(line, needles)) {
            flatten_inline_text(line);
            dprintf(out_fd,
                    "sample=%s source=%s match_%02d=%s\n",
                    sample,
                    source_name,
                    matches,
                    line);
            matches++;
        }
    }
    dprintf(out_fd,
            "sample=%s source=%s matches=%d truncated=%d\n",
            sample,
            source_name,
            matches,
            truncated);
    close(in_fd);
}

static void v1393_rc1_window_sample(const char *sample, long start_ms, long detect_ms, long child_start_ms) {
    static const char *const interrupts_needles[] = {
        "mdm status",
        "gpio",
        "142",
        "pcie",
        "PCIe",
        "mhi",
        "MHI",
        NULL,
    };
    static const char *const gpio_needles[] = {
        "gpio102",
        "gpio104",
        "gpio135",
        "gpio142",
        "gpio-102",
        "gpio-104",
        "gpio-135",
        "gpio-142",
        "GPIO_102",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        " 102",
        " 104",
        " 135",
        " 142",
        NULL,
    };
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "rc1_window_sample label=%s elapsed_ms=%ld detect_elapsed_ms=%ld child_elapsed_ms=%ld\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= child_start_ms ? now_ms - child_start_ms : -1);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "interrupts",
                                           "/proc/interrupts",
                                           interrupts_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "debug_gpio",
                                           "/sys/kernel/debug/gpio",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pins",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pins",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pinmux",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pinconf",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                           gpio_needles);
    close(out_fd);
}

static void v1393_rc1_window_prepare(long start_ms, long detect_ms, const char *line) {
    char header[512];

    snprintf(header,
             sizeof(header),
             "state=armed sampler=read-only-v1420 detect_elapsed_ms=%ld delay_ms=%d line=%.*s\n",
             detect_ms >= start_ms ? detect_ms - start_ms : -1,
             A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS,
             160,
             line != NULL ? line : "");
    flatten_inline_text(header);
    strncat(header, "\n", sizeof(header) - strlen(header) - 1);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT, header);
}

static void v1393_rc1_window_sampler_child(long start_ms, long detect_ms) {
    long child_start_ms = monotonic_millis();

    v1393_rc1_window_sample("pre_rc1", start_ms, detect_ms, child_start_ms);
    usleep(50000);
    v1393_rc1_window_sample("post_rc1_50ms", start_ms, detect_ms, child_start_ms);
    usleep(100000);
    v1393_rc1_window_sample("post_rc1_150ms", start_ms, detect_ms, child_start_ms);
    usleep(350000);
    v1393_rc1_window_sample("post_rc1_500ms", start_ms, detect_ms, child_start_ms);
    _exit(0);
}

static int v1393_spawn_rc1_window_sampler(long start_ms, long detect_ms) {
    pid_t pid = fork();

    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_rc1_window_sampler_child(start_ms, detect_ms);
        _exit(1);
    }
    return 0;
}
#endif

static void v1393_pid1_rc1_watcher_child(void) {
    long start_ms = monotonic_millis();
    long deadline_ms = start_ms + (long)A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC * 1000L;
    int fd;
    int dev_kmsg_errno = 0;
    const char *source = "/dev/kmsg";
    char result[512];

    fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        dev_kmsg_errno = errno != 0 ? errno : EIO;
        source = "/proc/kmsg";
        fd = open("/proc/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) {
            int proc_kmsg_errno = errno != 0 ? errno : EIO;

            snprintf(result,
                     sizeof(result),
                     "state=open-kmsg-failed dev_errno=%d proc_errno=%d elapsed_ms=0\n",
                     dev_kmsg_errno,
                     proc_kmsg_errno);
            (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
            _exit(2);
        }
        for (;;) {
            char drain[768];
            ssize_t rd = read(fd, drain, sizeof(drain) - 1);

            if (rd > 0) {
                continue;
            }
            if (rd == 0 || errno == EAGAIN || errno == EWOULDBLOCK) {
                break;
            }
            {
                int saved_errno = errno != 0 ? errno : EIO;

                snprintf(result,
                         sizeof(result),
                         "state=drain-kmsg-failed source=%s errno=%d elapsed_ms=%ld\n",
                         source,
                         saved_errno,
                         monotonic_millis() - start_ms);
                (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
                close(fd);
                _exit(2);
            }
        }
    } else {
        (void)lseek(fd, 0, SEEK_END);
    }

    while (monotonic_millis() < deadline_ms) {
        char line[768];
        ssize_t rd = read(fd, line, sizeof(line) - 1);

        if (rd > 0) {
            line[rd] = '\0';
            if (v1393_pid1_rc1_trigger_line(line)) {
                long detect_ms = monotonic_millis();
                int write_rc;
                long write_ms;
                int saved_errno;

#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
                v1393_rc1_window_prepare(start_ms, detect_ms, line);
                v1393_rc1_window_sample("pre_delay", start_ms, detect_ms, detect_ms);
#endif
                if (A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS > 0) {
                    usleep((useconds_t)A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS * 1000U);
                }
#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
                (void)v1393_spawn_rc1_window_sampler(start_ms, detect_ms);
#endif
                write_rc = v1393_pid1_rc1_write_corrected_enumerate();
                saved_errno = write_rc < 0 ? -write_rc : 0;
                write_ms = monotonic_millis();

                snprintf(result,
                         sizeof(result),
                         "state=triggered source=%s write_rc=%d errno=%d detect_elapsed_ms=%ld write_elapsed_ms=%ld delay_ms=%d line=%.*s\n",
                         source,
                         write_rc,
                         saved_errno,
                         detect_ms >= start_ms ? detect_ms - start_ms : -1,
                         write_ms >= start_ms ? write_ms - start_ms : -1,
                         A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS,
                         120,
                         line);
                (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
                (void)v1393_append_wifi_test_log("pid1 rc1 watcher triggered source=%s write_rc=%d detect_elapsed_ms=%ld write_elapsed_ms=%ld delay_ms=%d\n",
                                                source,
                                                write_rc,
                                                detect_ms >= start_ms ? detect_ms - start_ms : -1,
                                                write_ms >= start_ms ? write_ms - start_ms : -1,
                                                A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS);
                close(fd);
                _exit(write_rc == 0 ? 0 : 3);
            }
        } else if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
            int saved_errno = errno != 0 ? errno : EIO;

            snprintf(result,
                     sizeof(result),
                     "state=read-kmsg-failed rc=-%d errno=%d elapsed_ms=%ld\n",
                     saved_errno,
                     saved_errno,
                     monotonic_millis() - start_ms);
            (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
            close(fd);
            _exit(4);
        }
        usleep(20000);
    }

    snprintf(result,
             sizeof(result),
             "state=timeout source=%s elapsed_ms=%ld timeout_sec=%d\n",
             source,
             monotonic_millis() - start_ms,
             A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
    close(fd);
    _exit(5);
}

static int v1393_spawn_pid1_rc1_watcher(pid_t *pid_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_pid1_rc1_watcher_child();
        _exit(6);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    return 0;
}
#endif

static void v1393_write_wifi_test_summary(pid_t helper_pid, long spawn_ms) {
    char wchan_path[64];
    char status_path[64];
    char wchan[96] = "unreadable";
    char status[384] = "unreadable";
    struct stat st;
    long now_ms = monotonic_millis();
    int helper_alive;
    int wlan0_present;
    int fd;

    if (helper_pid > 0) {
        snprintf(wchan_path, sizeof(wchan_path), "/proc/%ld/wchan", (long)helper_pid);
        snprintf(status_path, sizeof(status_path), "/proc/%ld/status", (long)helper_pid);
        if (read_trimmed_text_file(wchan_path, wchan, sizeof(wchan)) < 0) {
            snprintf(wchan, sizeof(wchan), "errno=%d", errno != 0 ? errno : EIO);
        }
        if (read_trimmed_text_file(status_path, status, sizeof(status)) < 0) {
            snprintf(status, sizeof(status), "errno=%d", errno != 0 ? errno : EIO);
        }
    } else {
        snprintf(wchan, sizeof(wchan), "invalid-pid");
        snprintf(status, sizeof(status), "invalid-pid");
    }
    flatten_inline_text(status);

    errno = 0;
    helper_alive = (helper_pid > 0 && (kill(helper_pid, 0) == 0 || errno == EPERM)) ? 1 : 0;
    wlan0_present = (lstat("/sys/class/net/wlan0", &st) == 0) ? 1 : 0;

    fd = open(A90_V1393_WIFI_TEST_SUMMARY,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return;
    }
    dprintf(fd, "label=%s\n", A90_WIFI_TEST_BOOT_LABEL);
    dprintf(fd, "watch_sec=%d\n", A90_WIFI_TEST_BOOT_WATCH_SEC);
    dprintf(fd, "spawn_ms=%ld\n", spawn_ms);
    dprintf(fd, "sample_ms=%ld\n", now_ms);
    dprintf(fd, "elapsed_since_spawn_ms=%ld\n", now_ms >= spawn_ms ? now_ms - spawn_ms : -1);
    dprintf(fd, "helper_pid=%ld\n", (long)helper_pid);
    dprintf(fd, "helper_alive=%d\n", helper_alive);
    dprintf(fd, "helper_wchan=%s\n", wchan);
    dprintf(fd, "helper_status=%s\n", status);
    dprintf(fd, "wlan0_present=%d\n", wlan0_present);
    dprintf(fd, "debugfs_mount_requested=%d\n", A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS);
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    dprintf(fd, "debugfs_mounted_by_pid1=%d\n", v1393_wifi_test_debugfs_mounted_by_pid1);
    dprintf(fd,
            "debugfs_pci_msm_case_present=%d\n",
            lstat("/sys/kernel/debug/pci-msm/case", &st) == 0 ? 1 : 0);
#endif
    dprintf(fd, "pid1_rc1_watcher_requested=%d\n", A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER);
#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
    {
        char watcher_result[384] = "missing";

        if (read_trimmed_text_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT,
                                   watcher_result,
                                   sizeof(watcher_result)) < 0) {
            snprintf(watcher_result, sizeof(watcher_result), "errno=%d", errno != 0 ? errno : EIO);
        }
        flatten_inline_text(watcher_result);
        dprintf(fd, "pid1_rc1_watcher_result=%s\n", watcher_result);
        dprintf(fd, "pid1_rc1_watcher_result_path=%s\n", A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT);
    }
#endif
    dprintf(fd, "rc1_window_sampler_requested=%d\n", A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER);
#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
    {
        char window_result[384] = "missing";

        if (read_trimmed_text_file(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                                   window_result,
                                   sizeof(window_result)) < 0) {
            snprintf(window_result, sizeof(window_result), "errno=%d", errno != 0 ? errno : EIO);
        }
        flatten_inline_text(window_result);
        dprintf(fd, "rc1_window_result_head=%s\n", window_result);
        dprintf(fd, "rc1_window_result_path=%s\n", A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT);
    }
#endif
    if (lstat(A90_V1393_WIFI_TEST_LOG, &st) == 0) {
        dprintf(fd, "log_size=%lld\n", (long long)st.st_size);
    } else {
        dprintf(fd, "log_size_errno=%d\n", errno != 0 ? errno : EIO);
    }
    dprintf(fd, "log_path=%s\n", A90_V1393_WIFI_TEST_LOG);
    close(fd);
}

static void v1393_write_wifi_test_supervised_summary(pid_t helper_pid,
                                                     long spawn_ms,
                                                     int wait_rc,
                                                     int status,
                                                     int timed_out) {
    v1393_write_wifi_test_summary(helper_pid, spawn_ms);
    {
        int fd = open(A90_V1393_WIFI_TEST_SUMMARY,
                      O_WRONLY | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                      0600);
        if (fd < 0) {
            return;
        }
        dprintf(fd, "supervised=1\n");
        dprintf(fd, "supervisor_timeout_sec=%d\n", A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC);
        dprintf(fd, "helper_wait_rc=%d\n", wait_rc);
        dprintf(fd, "helper_timed_out=%d\n", timed_out);
        dprintf(fd, "helper_status_raw=%d\n", status);
        if (wait_rc == 0 && WIFEXITED(status)) {
            dprintf(fd, "helper_exited=1\n");
            dprintf(fd, "helper_exit_code=%d\n", WEXITSTATUS(status));
        } else {
            dprintf(fd, "helper_exited=0\n");
        }
        if (wait_rc == 0 && WIFSIGNALED(status)) {
            dprintf(fd, "helper_signaled=1\n");
            dprintf(fd, "helper_signal=%d\n", WTERMSIG(status));
        } else {
            dprintf(fd, "helper_signaled=0\n");
        }
        close(fd);
    }
}

#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
static int v1393_spawn_wifi_test_summary_watcher(pid_t helper_pid, long spawn_ms, pid_t *watcher_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        sleep(A90_WIFI_TEST_BOOT_WATCH_SEC);
        v1393_write_wifi_test_summary(helper_pid, spawn_ms);
        _exit(0);
    }
    if (watcher_out != NULL) {
        *watcher_out = pid;
    }
    return 0;
}
#endif

static int v1393_wait_for_wifi_test_helper(pid_t helper_pid, int *status_out, int *timed_out_out) {
    long deadline_ms = monotonic_millis() + (long)A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC * 1000L;
    int status = 0;

    if (timed_out_out != NULL) {
        *timed_out_out = 0;
    }
    while (monotonic_millis() < deadline_ms) {
        pid_t got = waitpid(helper_pid, &status, WNOHANG);

        if (got == helper_pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;
            if (status_out != NULL) {
                *status_out = status;
            }
            return -saved_errno;
        }
        usleep(100000);
    }

    if (timed_out_out != NULL) {
        *timed_out_out = 1;
    }
    (void)kill(-helper_pid, SIGTERM);
    (void)kill(helper_pid, SIGTERM);
    usleep(500000);
    if (waitpid(helper_pid, &status, WNOHANG) != helper_pid) {
        (void)kill(-helper_pid, SIGKILL);
        (void)kill(helper_pid, SIGKILL);
        if (waitpid(helper_pid, &status, 0) < 0 && errno != ECHILD) {
            int saved_errno = errno;
            if (status_out != NULL) {
                *status_out = status;
            }
            return -saved_errno;
        }
    }
    if (status_out != NULL) {
        *status_out = status;
    }
    return -ETIMEDOUT;
}

static int v1393_spawn_wifi_test_boot_helper(pid_t *pid_out) {
    static char *const envp[] = {
        "PATH=/bin:/cache/bin:/system/bin:/vendor/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    static char *const argv[] = {
        A90_V1393_WIFI_TEST_HELPER,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        A90_V1393_WIFI_TEST_MODE,
        "--allow-pm-service-trigger-observer",
        "--timeout-sec",
        A90_V1393_WIFI_TEST_TIMEOUT_SEC,
        "--property-root",
        A90_V1393_WIFI_TEST_PROPERTY_ROOT,
        "--null-device-mode",
        "dev-null",
        "--android-selinux-context-mode",
        "service-defaults",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        A90_V1393_WIFI_TEST_REAL_LD_CONFIG,
        "--apex-libraries-source",
        A90_V1393_WIFI_TEST_REAL_APEX_LIBRARIES,
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--pm-observer-continue-after-provider",
        "--pm-observer-start-cnss-after-provider",
        "--allow-post-pm-mdm-helper-esoc-observer",
        "--pm-observer-start-mdm-helper-after-cnss",
        "--allow-post-pm-mdm-helper-lower-trace",
        "--pm-observer-zero-delay-per-mgr-probe",
        "--pm-observer-load-precompiled-policy",
        "--pm-observer-start-mdm-helper-before-cnss",
        "--pm-observer-set-mdm3-restart-level-related",
        "--pm-observer-set-mdm-helper-selinux-context",
        "--pm-observer-private-firmware-mounts",
        "--pm-observer-per-proxy-pph-delta-ms",
        "20000",
        "--pm-observer-mknod-esoc-dev-node-before-cnss",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--pm-observer-start-cnss-before-per-proxy",
        "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd",
        "--pm-observer-late-per-proxy-response-sampler",
        "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler",
        "--private-cnss-daemon-path",
        A90_V1393_WIFI_TEST_PRIVATE_CNSS,
        "--pm-observer-current-route-cnss-wlfw-precondition-summary",
#if !A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
        "--pm-observer-early-powerup-corrected-rc1-enumerate",
#endif
        NULL
    };
    struct a90_run_config config = {
        .tag = "wifi-v1393-test-boot",
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_V1393_WIFI_TEST_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 1000,
    };

    return a90_run_spawn(&config, pid_out);
}

static void v1393_wifi_test_supervisor_child(void) {
    pid_t helper_pid = -1;
    long spawn_ms = monotonic_millis();
    int status = 0;
    int timed_out = 0;
    int rc;
    char pid_text[32];

    rc = v1393_spawn_wifi_test_boot_helper(&helper_pid);
    if (rc < 0) {
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
        int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
#endif
        (void)v1393_append_wifi_test_log("supervisor helper spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        -rc,
                                        strerror(-rc));
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
        (void)v1393_append_wifi_test_log("supervisor debugfs cleanup after spawn failure rc=%d\n",
                                        debugfs_cleanup_rc);
#endif
        v1393_write_wifi_test_supervised_summary(helper_pid, spawn_ms, rc, status, 0);
        _exit(1);
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)helper_pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_PID, pid_text);
    (void)v1393_append_wifi_test_log("supervisor spawned helper pid=%ld label=%s mode=%s timeout_sec=%d\n",
                                    (long)helper_pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE,
                                    A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC);
    rc = v1393_wait_for_wifi_test_helper(helper_pid, &status, &timed_out);
    (void)v1393_append_wifi_test_log("supervisor helper done pid=%ld wait_rc=%d status=%d timed_out=%d\n",
                                    (long)helper_pid,
                                    rc,
                                    status,
                                    timed_out);
    v1393_write_wifi_test_supervised_summary(helper_pid, spawn_ms, rc, status, timed_out);
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    {
        int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
        (void)v1393_append_wifi_test_log("supervisor debugfs cleanup rc=%d\n",
                                        debugfs_cleanup_rc);
    }
#endif
    _exit(rc == 0 ? 0 : 1);
}

static int v1393_spawn_wifi_test_supervisor(pid_t *pid_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_wifi_test_supervisor_child();
        _exit(1);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    return 0;
}

static void v1393_run_wifi_test_boot_once(void) {
    struct stat st;
    pid_t pid = -1;
#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    pid_t watcher_pid = -1;
#endif
    int rc;
    char pid_text[32];
#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    long spawn_ms;
#endif

    if (stat(A90_V1393_WIFI_TEST_DISABLE, &st) == 0) {
        a90_logf("wifi-v1393", "test boot disabled by %s", A90_V1393_WIFI_TEST_DISABLE);
        a90_timeline_record(0, 0, "wifi-v1393-test-boot", "disabled by flag");
        klogf("<6>A90v1393: wifi test boot disabled by flag\n");
        return;
    }

    rc = v1393_reset_wifi_test_log();
    if (rc < 0) {
        a90_logf("wifi-v1393", "log reset failed rc=%d errno=%d error=%s",
                 rc,
                 -rc,
                 strerror(-rc));
        klogf("<6>%s: wifi test boot log reset failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
    }
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_SUMMARY, "state=armed\n");

    boot_splash_set_line(5, "[ WIFI   ] %s TEST BOOT", A90_WIFI_TEST_BOOT_LABEL);
    boot_auto_frame();
    a90_logf("wifi-v1393", "test boot armed helper=%s timeout_sec=%s",
             A90_V1393_WIFI_TEST_HELPER,
             A90_V1393_WIFI_TEST_TIMEOUT_SEC);
    a90_timeline_record(0, 0, "wifi-v1393-test-boot", "armed");
    klogf("<6>%s: wifi test boot armed\n", A90_WIFI_TEST_BOOT_KLOG_PREFIX);
    (void)v1393_append_wifi_test_log("armed ms=%ld label=%s mode=%s timeout_sec=%s\n",
                                    monotonic_millis(),
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE,
                                    A90_V1393_WIFI_TEST_TIMEOUT_SEC);

    if (stat(A90_V1393_WIFI_TEST_HELPER, &st) < 0 || !S_ISREG(st.st_mode)) {
        int saved_errno = errno != 0 ? errno : ENOENT;

        a90_logf("wifi-v1393", "helper missing path=%s errno=%d error=%s",
                 A90_V1393_WIFI_TEST_HELPER,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v1393-test-boot", "helper missing");
        klogf("<6>%s: wifi test boot helper missing\n", A90_WIFI_TEST_BOOT_KLOG_PREFIX);
        (void)v1393_append_wifi_test_log("helper missing path=%s errno=%d error=%s\n",
                                        A90_V1393_WIFI_TEST_HELPER,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    if (prepare_android_layout(false) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        a90_logf("wifi-v1393", "android layout failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v1393-test-boot", "android layout failed");
        klogf("<6>%s: wifi test boot android layout failed rc=-%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              saved_errno);
        (void)v1393_append_wifi_test_log("android layout failed errno=%d error=%s\n",
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    rc = v724_prepare_selinuxfs_surface();
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "selinuxfs failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "selinuxfs failed");
        klogf("<6>%s: wifi test boot selinuxfs failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("selinuxfs failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    rc = v1393_prepare_wifi_test_debugfs();
    (void)v1393_append_wifi_test_log("debugfs prepare rc=%d mounted_by_pid1=%d\n",
                                    rc,
                                    v1393_wifi_test_debugfs_mounted_by_pid1);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "debugfs prepare failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "debugfs prepare failed");
        klogf("<6>%s: wifi test boot debugfs prepare failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        return;
    }
#endif

#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
    {
        pid_t rc1_watcher_pid = -1;

        rc = v1393_spawn_pid1_rc1_watcher(&rc1_watcher_pid);
        if (rc < 0) {
            int saved_errno = -rc;

            if (saved_errno <= 0) {
                saved_errno = EIO;
            }
            a90_logf("wifi-v1393", "pid1 rc1 watcher spawn failed rc=%d errno=%d error=%s",
                     rc,
                     saved_errno,
                     strerror(saved_errno));
            a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "pid1 rc1 watcher spawn failed");
            klogf("<6>%s: pid1 rc1 watcher spawn failed rc=%d\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  rc);
            (void)v1393_append_wifi_test_log("pid1 rc1 watcher spawn failed rc=%d errno=%d error=%s\n",
                                            rc,
                                            saved_errno,
                                            strerror(saved_errno));
        } else {
            a90_logf("wifi-v1393", "pid1 rc1 watcher spawned pid=%ld timeout_sec=%d",
                     (long)rc1_watcher_pid,
                     A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC);
            a90_timeline_record(0,
                                0,
                                "wifi-v1393-test-boot",
                                "pid1 rc1 watcher spawned pid=%ld",
                                (long)rc1_watcher_pid);
            klogf("<6>%s: pid1 rc1 watcher spawned pid=%ld\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  (long)rc1_watcher_pid);
            (void)v1393_append_wifi_test_log("pid1 rc1 watcher pid=%ld timeout_sec=%d result=%s\n",
                                            (long)rc1_watcher_pid,
                                            A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC,
                                            A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT);
        }
    }
#endif

#if A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    rc = v1393_spawn_wifi_test_supervisor(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "supervisor spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "supervisor spawn failed");
        klogf("<6>%s: wifi test boot supervisor spawn failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("supervisor spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
        {
            int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
            (void)v1393_append_wifi_test_log("debugfs cleanup after supervisor spawn failure rc=%d\n",
                                            debugfs_cleanup_rc);
        }
#endif
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_WATCHER_PID, pid_text);
    a90_logf("wifi-v1393", "supervisor spawned pid=%ld mode=%s",
             (long)pid,
             A90_V1393_WIFI_TEST_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v1393-test-boot",
                        "supervisor spawned pid=%ld",
                        (long)pid);
    klogf("<6>%s: wifi test boot supervisor spawned pid=%ld\n",
          A90_WIFI_TEST_BOOT_KLOG_PREFIX,
          (long)pid);
    (void)v1393_append_wifi_test_log("supervisor pid=%ld label=%s mode=%s\n",
                                    (long)pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE);
#else
    spawn_ms = monotonic_millis();
    rc = v1393_spawn_wifi_test_boot_helper(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "helper spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "spawn failed");
        klogf("<6>%s: wifi test boot helper spawn failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_PID, pid_text);
    a90_logf("wifi-v1393", "helper spawned pid=%ld mode=%s",
             (long)pid,
             A90_V1393_WIFI_TEST_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v1393-test-boot",
                        "helper spawned pid=%ld",
                        (long)pid);
    klogf("<6>%s: wifi test boot helper spawned pid=%ld\n",
          A90_WIFI_TEST_BOOT_KLOG_PREFIX,
          (long)pid);
    (void)v1393_append_wifi_test_log("spawned pid=%ld label=%s mode=%s\n",
                                    (long)pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE);

    rc = v1393_spawn_wifi_test_summary_watcher(pid, spawn_ms, &watcher_pid);
    if (rc == 0) {
        snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)watcher_pid);
        (void)v724_write_private_file(A90_V1393_WIFI_TEST_WATCHER_PID, pid_text);
        (void)v1393_append_wifi_test_log("watcher pid=%ld watch_sec=%d summary=%s\n",
                                        (long)watcher_pid,
                                        A90_WIFI_TEST_BOOT_WATCH_SEC,
                                        A90_V1393_WIFI_TEST_SUMMARY);
    } else {
        (void)v1393_append_wifi_test_log("watcher spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        -rc,
                                        strerror(-rc));
    }
#endif
}
#endif

static bool v641_sibling_ssctl_flag_armed(void) {
    char state[32];

    if (read_trimmed_text_file(A90_V641_SIBLING_SSCTL_FLAG,
                               state,
                               sizeof(state)) < 0) {
        a90_logf("wifi-v641", "sibling fwssctl disabled flag=%s errno=%d error=%s",
                 A90_V641_SIBLING_SSCTL_FLAG,
                 errno,
                 strerror(errno));
        klogf("<6>A90v641: sibling fwssctl disabled flag=%s\n",
              A90_V641_SIBLING_SSCTL_FLAG);
        return false;
    }

    if (strcmp(state, "run") != 0) {
        a90_logf("wifi-v641", "sibling fwssctl ignored flag=%s state=%.16s",
                 A90_V641_SIBLING_SSCTL_FLAG,
                 state);
        klogf("<6>A90v641: sibling fwssctl ignored state=%.16s\n", state);
        return false;
    }

    if (unlink(A90_V641_SIBLING_SSCTL_FLAG) < 0 && errno != ENOENT) {
        a90_logf("wifi-v641", "sibling fwssctl flag unlink warning errno=%d error=%s",
                 errno,
                 strerror(errno));
    }
    sync();
    return true;
}

static bool v641_uevent_has_partname(const char *text, const char *partname) {
    const char *cursor = text;
    size_t partname_len = strlen(partname);

    while (cursor != NULL && *cursor != '\0') {
        const char *line_end = strchr(cursor, '\n');
        size_t line_len = line_end != NULL ? (size_t)(line_end - cursor) : strlen(cursor);

        if (line_len >= 9 + partname_len &&
            strncmp(cursor, "PARTNAME=", 9) == 0 &&
            strncmp(cursor + 9, partname, partname_len) == 0 &&
            (cursor[9 + partname_len] == '\0' ||
             cursor[9 + partname_len] == '\n' ||
             cursor[9 + partname_len] == '\r')) {
            return true;
        }
        cursor = line_end != NULL ? line_end + 1 : NULL;
    }
    return false;
}

static int v641_find_block_by_partname(const char *partname,
                                       const char *fallback_block,
                                       char *out,
                                       size_t out_size) {
    DIR *dir;
    struct dirent *entry;

    dir = opendir("/sys/class/block");
    if (dir != NULL) {
        while ((entry = readdir(dir)) != NULL) {
            char uevent_path[PATH_MAX];
            char uevent[1024];

            if (entry->d_name[0] == '.') {
                continue;
            }
            if (snprintf(uevent_path,
                         sizeof(uevent_path),
                         "/sys/class/block/%s/uevent",
                         entry->d_name) >= (int)sizeof(uevent_path)) {
                continue;
            }
            if (read_text_file(uevent_path, uevent, sizeof(uevent)) < 0) {
                continue;
            }
            if (v641_uevent_has_partname(uevent, partname)) {
                int rc = get_block_device_path(entry->d_name, out, out_size);

                closedir(dir);
                return rc;
            }
        }
        closedir(dir);
    }

    return get_block_device_path(fallback_block, out, out_size);
}

static int v641_prepare_firmware_mount_one(const char *label,
                                           const char *partname,
                                           const char *fallback_block,
                                           const char *target) {
    char block_path[PATH_MAX];
    int saved_errno;

    if (v641_find_block_by_partname(partname,
                                    fallback_block,
                                    block_path,
                                    sizeof(block_path)) < 0) {
        saved_errno = errno;
        (void)v641_append_ssctl_log("firmware %s resolve failed part=%s fallback=%s errno=%d error=%s\n",
                                   label,
                                   partname,
                                   fallback_block,
                                   saved_errno,
                                   strerror(saved_errno));
        a90_logf("wifi-v641", "firmware %s resolve failed errno=%d error=%s",
                 label,
                 saved_errno,
                 strerror(saved_errno));
        return -saved_errno;
    }

    if (mount(block_path,
              target,
              "vfat",
              MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "utf8,shortname=lower") < 0) {
        saved_errno = errno;
        if (saved_errno != EBUSY) {
            (void)v641_append_ssctl_log("firmware %s mount failed source=%s target=%s errno=%d error=%s\n",
                                       label,
                                       block_path,
                                       target,
                                       saved_errno,
                                       strerror(saved_errno));
            a90_logf("wifi-v641", "firmware %s mount failed errno=%d error=%s",
                     label,
                     saved_errno,
                     strerror(saved_errno));
            return -saved_errno;
        }
    }

    (void)v641_append_ssctl_log("firmware %s mounted source=%s target=%s\n",
                               label,
                               block_path,
                               target);
    a90_logf("wifi-v641", "firmware %s mounted source=%s target=%s",
             label,
             block_path,
             target);
    klogf("<6>A90v641: firmware %s mounted target=%s\n", label, target);
    return 0;
}

static void v641_stat_optional(const char *label, const char *path) {
    struct stat st;

    if (lstat(path, &st) == 0) {
        (void)v641_append_ssctl_log("firmware stat %s path=%s mode=0%o size=%lld\n",
                                   label,
                                   path,
                                   (unsigned int)(st.st_mode & 07777),
                                   (long long)st.st_size);
        a90_logf("wifi-v641", "firmware stat %s ok path=%s", label, path);
        return;
    }

    (void)v641_append_ssctl_log("firmware stat %s missing path=%s errno=%d error=%s\n",
                               label,
                               path,
                               errno,
                               strerror(errno));
    a90_logf("wifi-v641", "firmware stat %s missing path=%s errno=%d error=%s",
             label,
             path,
             errno,
             strerror(errno));
}

static int v641_prepare_firmware_mounts(void) {
    int saved_errno;

    if (ensure_dir(A90_V641_VENDOR_DIR, 0755) < 0 ||
        ensure_dir(A90_V641_FW_MNT_DIR, 0755) < 0 ||
        ensure_dir(A90_V641_FW_MODEM_DIR, 0755) < 0) {
        saved_errno = errno;
        (void)v641_append_ssctl_log("firmware mountpoint setup failed errno=%d error=%s\n",
                                   saved_errno,
                                   strerror(saved_errno));
        a90_logf("wifi-v641", "firmware mountpoint setup failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        return -saved_errno;
    }

    if (v641_prepare_firmware_mount_one("apnhlos",
                                        "apnhlos",
                                        "sda20",
                                        A90_V641_FW_MNT_DIR) < 0) {
        return -EIO;
    }
    if (v641_prepare_firmware_mount_one("modem",
                                        "modem",
                                        "sda21",
                                        A90_V641_FW_MODEM_DIR) < 0) {
        return -EIO;
    }

    v641_stat_optional("firmware_mnt_image", A90_V641_FW_MNT_DIR "/image");
    v641_stat_optional("firmware_modem_image", A90_V641_FW_MODEM_DIR "/image");
    v641_stat_optional("modem_b00", A90_V641_FW_MODEM_DIR "/image/modem.b00");
    v641_stat_optional("cdsp_mdt", A90_V641_FW_MODEM_DIR "/image/cdsp.mdt");
    (void)v641_append_ssctl_log("firmware mounts ready\n");
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "firmware mounts ready");
    klogf("<6>A90v641: firmware mounts ready\n");
    return 0;
}

static int v641_write_sysfs_once(const char *path) {
    int fd;
    int saved_errno;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }

    if (write_all_checked(fd, "1\n", 2) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }

    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

static void v641_sibling_ssctl_child(const char *label, const char *path) {
    int rc;

    (void)v641_append_ssctl_log("node %s child start path=%s\n", label, path);
    rc = v641_write_sysfs_once(path);
    if (rc < 0) {
        (void)v641_append_ssctl_log("node %s write rc=%d errno=%d error=%s\n",
                                   label,
                                   rc,
                                   -rc,
                                   strerror(-rc));
        klogf("<6>A90v641: sibling fwssctl node=%s write failed rc=%d\n",
              label,
              rc);
        _exit(1);
    }

    (void)v641_append_ssctl_log("node %s write rc=0\n", label);
    klogf("<6>A90v641: sibling fwssctl node=%s write ok\n", label);
    _exit(0);
}

static int v641_wait_child_timeout(pid_t pid,
                                   int timeout_ms,
                                   int *status_out,
                                   bool *reaped_out) {
    long deadline = monotonic_millis() + timeout_ms;
    int status;

    if (reaped_out != NULL) {
        *reaped_out = false;
    }
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return 0;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }

    (void)kill(pid, SIGKILL);
    deadline = monotonic_millis() + 1000;
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return -ETIMEDOUT;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }
    return -ETIMEDOUT;
}

static int v641_run_sibling_ssctl_node(const char *label, const char *path) {
    pid_t pid;
    int status = 0;
    int rc;
    bool reaped = false;

    (void)v641_append_ssctl_log("node %s parent start path=%s timeout_ms=%d\n",
                               label,
                               path,
                               A90_V641_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "%s start", label);
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        (void)v641_append_ssctl_log("node %s fork failed errno=%d error=%s\n",
                                   label,
                                   saved_errno,
                                   strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                            saved_errno,
                            "wifi-v641-fwssctl",
                            "%s fork failed",
                            label);
        return -saved_errno;
    }

    if (pid == 0) {
        v641_sibling_ssctl_child(label, path);
    }

    rc = v641_wait_child_timeout(pid,
                                 A90_V641_SIBLING_SSCTL_TIMEOUT_MS,
                                 &status,
                                 &reaped);
    (void)v641_append_ssctl_log("node %s parent rc=%d status=0x%x reaped=%d\n",
                               label,
                               rc,
                               status,
                               reaped ? 1 : 0);
    if (rc == 0) {
        int node_rc = WIFEXITED(status) ? WEXITSTATUS(status) : EIO;

        a90_timeline_record(node_rc == 0 ? 0 : -EIO,
                            node_rc,
                            "wifi-v641-fwssctl",
                            "%s status=0x%x",
                            label,
                            status);
        klogf("<6>A90v641: sibling fwssctl node=%s status=0x%x\n",
              label,
              status);
        return node_rc == 0 ? 0 : -EIO;
    }

    a90_timeline_record(rc,
                        -rc,
                        "wifi-v641-fwssctl",
                        "%s wait failed reaped=%d",
                        label,
                        reaped ? 1 : 0);
    klogf("<6>A90v641: sibling fwssctl node=%s wait failed rc=%d reaped=%d\n",
          label,
          rc,
          reaped ? 1 : 0);
    if (!reaped) {
        return -ECHILD;
    }
    return rc;
}

static void v641_run_sibling_ssctl_once(void) {
    static const struct {
        const char *label;
        const char *path;
    } nodes[] = {
        { "adsp", "/sys/kernel/boot_adsp/boot" },
        { "cdsp", "/sys/kernel/boot_cdsp/boot" },
        { "slpi", "/sys/kernel/boot_slpi/boot" },
    };
    size_t index;
    int failures = 0;
    int timeouts = 0;

    if (!v641_sibling_ssctl_flag_armed()) {
        return;
    }

    boot_splash_set_line(5, "[ WIFI   ] V641 FW SSCTL PROOF");
    boot_auto_frame();
    a90_console_printf("# V641 firmware-backed sibling SSCTL proof: armed one-shot.\r\n");
    a90_logf("wifi-v641", "sibling fwssctl proof armed timeout_ms=%d",
             A90_V641_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "armed one-shot");
    klogf("<6>A90v641: sibling fwssctl proof armed\n");

    if (v641_prepare_firmware_mounts() < 0) {
        a90_console_printf("# V641 firmware-backed sibling SSCTL proof: firmware mount failed.\r\n");
        a90_timeline_record(-EIO, EIO, "wifi-v641-fwssctl", "firmware mount failed");
        klogf("<6>A90v641: sibling fwssctl proof stopped by firmware mount failure\n");
        return;
    }

    for (index = 0; index < sizeof(nodes) / sizeof(nodes[0]); ++index) {
        int node_rc = v641_run_sibling_ssctl_node(nodes[index].label, nodes[index].path);

        if (node_rc != 0) {
            ++failures;
        }
        if (node_rc == -ETIMEDOUT) {
            ++timeouts;
        }
        if (node_rc == -ECHILD) {
            (void)v641_append_ssctl_log("proof stop unreaped node=%s\n",
                                       nodes[index].label);
            break;
        }
    }

    a90_console_printf("# V641 firmware-backed sibling SSCTL proof: failures=%d timeouts=%d.\r\n",
                       failures,
                       timeouts);
    a90_logf("wifi-v641", "sibling fwssctl proof complete failures=%d timeouts=%d",
             failures,
             timeouts);
    a90_timeline_record(failures == 0 ? 0 : -EIO,
                        failures,
                        "wifi-v641-fwssctl",
                        "complete failures=%d timeouts=%d",
                        failures,
                        timeouts);
    klogf("<6>A90v641: sibling fwssctl proof complete failures=%d timeouts=%d\n",
          failures,
          timeouts);
}

int main(void) {
    static const struct a90_storage_boot_hooks storage_hooks = {
        .set_line = storage_boot_set_line,
        .draw_frame = storage_boot_draw_frame,
    };
    static const struct a90_selftest_boot_hooks selftest_hooks = {
        .set_line = selftest_boot_set_line,
        .draw_frame = selftest_boot_draw_frame,
    };

    a90_timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    a90_log_select_or_fallback(NATIVE_LOG_FALLBACK);
    a90_logf("boot", "%s start", INIT_BANNER);
    a90_logf("boot", "base mounts ready");
    a90_timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v724: base mounts ready\n");
    prepare_early_display_environment();
    boot_splash_set_line(1, "[ CACHE  ] MOUNTING /cache");
    boot_splash_set_line(2, "[ SD     ] WAITING FOR PROBE");
    boot_auto_frame();
    a90_logf("boot", "early display/input nodes prepared");
    a90_timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    a90_timeline_probe_boot_resources();
    klogf("<6>A90v724: early display/input nodes prepared\n");

    if (a90_storage_mount_cache() == 0) {
        a90_storage_set_cache_ready(true);
        boot_splash_set_line(1, "[ CACHE  ] OK /cache");
        a90_log_select_or_fallback(NATIVE_LOG_PRIMARY);
        a90_timeline_replay_to_log("cache");
        a90_logf("boot", "%s start", INIT_BANNER);
        a90_logf("boot", "base mounts ready");
        a90_logf("boot", "early display/input nodes prepared");
        a90_logf("boot", "cache mounted log=%s", a90_log_path());
        a90_timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", a90_log_path());
        mark_step("1_cache_ok_v724\n");
        klogf("<6>A90v724: cache mounted\n");
    } else {
        int saved_errno = errno;

        a90_storage_set_cache_ready(false);
        boot_splash_set_line(1, "[ CACHE  ] WARN MOUNT FAIL");
        a90_logf("boot", "cache mount failed errno=%d error=%s log=%s",
                    saved_errno, strerror(saved_errno), a90_log_path());
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "cache-mount",
                        "/cache failed: %s log=%s",
                        strerror(saved_errno),
                        a90_log_path());
        klogf("<6>A90v724: cache mount failed (%d)\n", saved_errno);
    }
    boot_auto_frame();
    a90_storage_probe_boot(&storage_hooks, NULL);
    {
        struct a90_storage_status storage_status;
        int runtime_rc;

        if (a90_storage_get_status(&storage_status) == 0) {
            runtime_rc = a90_runtime_init(&storage_status);
        } else {
            runtime_rc = a90_runtime_init(NULL);
        }

        if (runtime_rc == 0) {
            boot_splash_set_line(4,
                    a90_runtime_using_fallback() ?
                    "[ RUNTIME] CACHE ROOT READY" :
                    "[ RUNTIME] SD ROOT READY");
            klogf("<6>A90v724: runtime root ready %s\n", a90_runtime_root());
        } else {
            int runtime_errno = -runtime_rc;

            if (runtime_errno <= 0) {
                runtime_errno = EIO;
            }
            boot_splash_set_line(4, "[ RUNTIME] WARN FALLBACK");
            klogf("<6>A90v724: runtime root warning (%d)\n", runtime_errno);
        }
        boot_auto_frame();
    }

    if (a90_helper_scan() == 0) {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] INVENTORY READY");
        a90_logf("boot", "helper inventory ready %s", helper_summary);
        klogf("<6>A90v724: helper inventory ready %s\n", helper_summary);
    } else {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] WARN SEE SELFTEST");
        a90_logf("boot", "helper inventory warning %s", helper_summary);
        klogf("<6>A90v724: helper inventory warning %s\n", helper_summary);
    }
    boot_auto_frame();

    if (a90_userland_scan() == 0) {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] INVENTORY READY");
        a90_logf("boot", "userland inventory ready %s", userland_summary);
        klogf("<6>A90v724: userland inventory ready %s\n", userland_summary);
    } else {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] OPTIONAL MISSING");
        a90_logf("boot", "userland inventory warning %s", userland_summary);
        klogf("<6>A90v724: userland inventory warning %s\n", userland_summary);
    }
    boot_auto_frame();

#ifdef A90_WIFI_TEST_BOOT
    v1393_run_wifi_test_boot_once();
    boot_auto_frame();
#endif

    if (a90_usb_gadget_setup_acm() == 0) {
        mark_step("2_gadget_ok_v724\n");
        boot_splash_set_line(4, "[ SERIAL ] ACM GADGET OK");
        a90_logf("boot", "ACM gadget configured");
        a90_timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v724: ACM gadget configured\n");
        (void)a90_selftest_run_boot(&selftest_hooks, NULL);
        {
            char guard_summary[96];

            refresh_pid1_guard();
            a90_pid1_guard_summary(guard_summary, sizeof(guard_summary));
            boot_splash_set_line(5,
                    a90_pid1_guard_has_failures() ?
                    "[ GUARD ] WARN SEE STATUS" :
                    "[ GUARD ] PID1 CHECK OK");
            boot_auto_frame();
            a90_logf("boot", "pid1 guard %s", guard_summary);
            a90_timeline_record(a90_pid1_guard_has_failures() ? -EIO : 0,
                            a90_pid1_guard_has_failures() ? EIO : 0,
                            "pid1-guard",
                            "%s",
                            guard_summary);
            klogf("<6>A90v724: pid1 guard %s\n", guard_summary);
        }
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL ACM GADGET");
        boot_auto_frame();
        a90_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_wait_tty() == 0) {
        mark_step("3_tty_ready_v724\n");
        boot_splash_set_line(4, "[ SERIAL ] TTYGS0 READY");
        boot_splash_set_line(5, "[ RUNTIME] HUD MENU LOADING");
        a90_logf("boot", "ttyGS0 ready");
        a90_timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v724: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_SPLASH_SECONDS);
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL TTYGS0");
        boot_auto_frame();
        a90_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_attach() == 0) {
        mark_step("4_console_attached_v724\n");
        boot_splash_set_line(5, "[ RUNTIME] SHELL READY");
        a90_logf("boot", "console attached");
        a90_timeline_record(0, 0, "console", "serial console attached");
        a90_console_drain_input(250, 1500);
        a90_console_printf("\r\n# %s\r\n", INIT_BANNER);
        a90_console_printf("# USB ACM serial console ready.\r\n");
        v724_run_qrtr_servloc_boot_once();
        v641_run_sibling_ssctl_once();
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            a90_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_console_printf("# Boot display: splash %ds -> autohud %ds.\r\n",
                    BOOT_SPLASH_SECONDS,
                    BOOT_HUD_REFRESH_SECONDS);
        } else {
            int saved_errno = errno;

            a90_logf("boot", "autohud start failed errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            a90_timeline_record(-saved_errno,
                            saved_errno,
                            "autohud",
                            "start failed: %s",
                            strerror(saved_errno));
            a90_console_printf("# Boot display: autohud start failed.\r\n");
        }
        if (a90_netservice_enabled()) {
            int net_rc;

            a90_console_printf("# Netservice: enabled, starting NCM/tcpctl.\r\n");
            net_rc = a90_netservice_start();
            if (net_rc == 0) {
                mark_step("5_netservice_ok_v724\n");
                a90_console_printf("# Netservice: NCM %s %s, tcpctl port %s.\r\n",
                        NETSERVICE_IFNAME,
                        NETSERVICE_DEVICE_IP,
                        NETSERVICE_TCP_PORT);
                klogf("<6>A90v724: netservice started\n");
            } else {
                int net_errno = -net_rc;

                if (net_errno < 0) {
                    net_errno = EIO;
                }
                a90_console_printf("# Netservice: start failed rc=%d errno=%d (%s).\r\n",
                        net_rc,
                        net_errno,
                        strerror(net_errno));
                a90_logf("boot", "netservice failed rc=%d errno=%d error=%s",
                            net_rc, net_errno, strerror(net_errno));
                a90_timeline_record(net_rc,
                                net_errno,
                                "netservice",
                                "start failed: %s",
                                strerror(net_errno));
                klogf("<6>A90v724: netservice failed (%d)\n", net_errno);
            }
        } else {
            a90_logf("boot", "netservice disabled flag=%s", NETSERVICE_FLAG_PATH);
        }
        if (rshell_enabled()) {
            int rshell_rc;

            a90_console_printf("# Remote shell: enabled, starting token TCP shell.\r\n");
            rshell_rc = rshell_start_service(false);
            if (rshell_rc == 0) {
                mark_step("6_rshell_ok_v724\n");
                a90_console_printf("# Remote shell: %s:%s ready.\r\n",
                        A90_RSHELL_BIND_ADDR,
                        A90_RSHELL_PORT);
                klogf("<6>A90v724: rshell started\n");
            } else {
                int rshell_errno = -rshell_rc;

                if (rshell_errno <= 0) {
                    rshell_errno = EIO;
                }
                a90_console_printf("# Remote shell: start failed rc=%d errno=%d (%s).\r\n",
                        rshell_rc,
                        rshell_errno,
                        strerror(rshell_errno));
                a90_logf("boot", "rshell failed rc=%d errno=%d error=%s",
                            rshell_rc, rshell_errno, strerror(rshell_errno));
                a90_timeline_record(rshell_rc,
                                rshell_errno,
                                "rshell",
                                "start failed: %s",
                                strerror(rshell_errno));
                klogf("<6>A90v724: rshell failed (%d)\n", rshell_errno);
            }
        } else {
            a90_logf("boot", "rshell disabled");
        }
        a90_logf("boot", "entering shell");
        a90_timeline_record(0, 0, "shell", "interactive shell ready");
        shell_loop();
    } else {
        int saved_errno = errno;
        a90_logf("boot", "console attach failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "console",
                        "attach failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
