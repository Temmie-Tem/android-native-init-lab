/* Included by stage3/linux_init/init_v83.c. Do not compile standalone. */

static void boot_storage_use_cache(const char *reason, int rc, int saved_errno) {
    const char *fallback_root = cache_mount_ready ? CACHE_STORAGE_ROOT : TMP_STORAGE_ROOT;

    boot_storage.probed = true;
    boot_storage.fallback = true;
    snprintf(boot_storage.backend,
             sizeof(boot_storage.backend),
             "%s",
             cache_mount_ready ? "cache" : "tmp");
    snprintf(boot_storage.root,
             sizeof(boot_storage.root),
             "%s",
             fallback_root);
    snprintf(boot_storage.warning,
             sizeof(boot_storage.warning),
             "%s; fallback %s",
             reason,
             fallback_root);
    snprintf(boot_storage.detail,
             sizeof(boot_storage.detail),
             "rc=%d errno=%d %s",
             rc,
             saved_errno,
             saved_errno != 0 ? strerror(saved_errno) : "ok");
    boot_splash_set_line(3, "[ STORAGE] WARN FALLBACK %s", boot_storage.root);
    a90_logf("storage", "fallback root=%s reason=%s detail=%s",
                boot_storage.root,
                reason,
                boot_storage.detail);
    a90_timeline_record(rc, saved_errno, "storage", "%s", boot_storage.warning);
}

static void boot_storage_use_sd(void) {
    boot_storage.probed = true;
    boot_storage.fallback = false;
    boot_storage.sd_present = true;
    boot_storage.sd_mounted = true;
    boot_storage.sd_expected = true;
    boot_storage.sd_rw_ok = true;
    snprintf(boot_storage.backend, sizeof(boot_storage.backend), "%s", "sd");
    snprintf(boot_storage.root, sizeof(boot_storage.root), "%s", SD_WORKSPACE_DIR);
    boot_storage.warning[0] = '\0';
    snprintf(boot_storage.detail,
             sizeof(boot_storage.detail),
             "uuid=%s workspace=%s",
             boot_storage.sd_uuid,
             SD_WORKSPACE_DIR);
    boot_splash_set_line(3, "[ STORAGE] SD MAIN READY");
    if (a90_log_set_path(SD_NATIVE_LOG_PATH) < 0 && cache_mount_ready) {
        a90_log_select_or_fallback(NATIVE_LOG_PRIMARY);
    }
    a90_timeline_replay_to_log("sd-storage");
    a90_logf("storage", "sd main root=%s uuid=%s", boot_storage.root, boot_storage.sd_uuid);
    a90_timeline_record(0, 0, "storage", "sd main root=%s uuid=%s",
                    boot_storage.root,
                    boot_storage.sd_uuid);
}

static void boot_storage_probe(void) {
    char node_path[PATH_MAX];
    char line[512];
    bool read_only = false;

    boot_splash_set_line(2, "[ SD     ] PROBE %s", SD_BLOCK_NAME);
    boot_auto_frame();
    a90_logf("storage", "boot sd probe start expected_uuid=%s", SD_EXPECTED_UUID);

    if (get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        int saved_errno = errno;

        boot_storage.sd_present = false;
        boot_splash_set_line(2, "[ SD     ] WARN BLOCK MISSING");
        boot_auto_frame();
        boot_storage_use_cache("sd block missing", -saved_errno, saved_errno);
        return;
    }
    boot_storage.sd_present = true;
    boot_splash_set_line(2, "[ SD     ] BLOCK OK");
    boot_auto_frame();

    if (read_ext4_uuid(node_path, boot_storage.sd_uuid, sizeof(boot_storage.sd_uuid)) < 0) {
        int saved_errno = errno;

        boot_splash_set_line(2, "[ SD     ] WARN UUID READ FAIL");
        boot_auto_frame();
        boot_storage_use_cache("sd uuid read failed", -saved_errno, saved_errno);
        return;
    }
    if (strcmp(boot_storage.sd_uuid, SD_EXPECTED_UUID) != 0) {
        boot_storage.sd_expected = false;
        boot_splash_set_line(2, "[ SD     ] WARN UUID MISMATCH");
        boot_auto_frame();
        boot_storage_use_cache("sd uuid mismatch", -ESTALE, ESTALE);
        return;
    }
    boot_storage.sd_expected = true;
    boot_splash_set_line(2, "[ SD     ] UUID OK");
    boot_auto_frame();

    ensure_dir("/mnt", 0755);
    ensure_dir(SD_MOUNT_POINT, 0755);
    if (mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            boot_splash_set_line(2, "[ SD     ] WARN REMOUNT FAIL");
            boot_auto_frame();
            boot_storage_use_cache("sd remount failed", -saved_errno, saved_errno);
            return;
        }
    }
    if (mount(node_path, SD_MOUNT_POINT, SD_FS_TYPE, 0, NULL) < 0) {
        int saved_errno = errno;

        boot_splash_set_line(2, "[ SD     ] WARN MOUNT FAIL");
        boot_auto_frame();
        boot_storage_use_cache("sd mount failed", -saved_errno, saved_errno);
        return;
    }
    boot_storage.sd_mounted = true;
    boot_splash_set_line(2, "[ SD     ] MOUNT RW OK");
    boot_auto_frame();

    if (ensure_sd_workspace() < 0) {
        int saved_errno = errno;

        boot_splash_set_line(2, "[ SD     ] WARN WORKSPACE FAIL");
        boot_auto_frame();
        umount(SD_MOUNT_POINT);
        boot_storage.sd_mounted = false;
        boot_storage_use_cache("sd workspace failed", -saved_errno, saved_errno);
        return;
    }
    if (ensure_sd_identity_marker(boot_storage.sd_uuid) < 0) {
        int saved_errno = errno;

        boot_splash_set_line(2, "[ SD     ] WARN ID MARKER FAIL");
        boot_auto_frame();
        umount(SD_MOUNT_POINT);
        boot_storage.sd_mounted = false;
        boot_storage_use_cache("sd identity marker failed", -saved_errno, saved_errno);
        return;
    }
    if (sd_write_read_probe() < 0) {
        int saved_errno = errno;

        boot_splash_set_line(2, "[ SD     ] WARN RW TEST FAIL");
        boot_auto_frame();
        umount(SD_MOUNT_POINT);
        boot_storage.sd_mounted = false;
        boot_storage_use_cache("sd rw test failed", -saved_errno, saved_errno);
        return;
    }
    boot_storage.sd_rw_ok = true;
    boot_splash_set_line(2, "[ SD     ] RW TEST OK");
    boot_auto_frame();
    boot_storage_use_sd();
    boot_auto_frame();
}

static int cmd_mountsd_status(void) {
    char node_path[PATH_MAX];
    char line[512];
    char uuid[40];
    bool read_only = false;
    struct statvfs vfs;

    if (get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
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

static int cmd_storage(void) {
    a90_console_printf("storage: backend=%s root=%s fallback=%s\r\n",
            boot_storage.backend,
            boot_storage.root,
            boot_storage.fallback ? "yes" : "no");
    a90_console_printf("storage: sd present=%s mounted=%s expected=%s rw=%s uuid=%s\r\n",
            boot_storage.sd_present ? "yes" : "no",
            boot_storage.sd_mounted ? "yes" : "no",
            boot_storage.sd_expected ? "yes" : "no",
            boot_storage.sd_rw_ok ? "yes" : "no",
            boot_storage.sd_uuid);
    a90_console_printf("storage: expected_uuid=%s id_file=%s\r\n", SD_EXPECTED_UUID, SD_ID_FILE);
    a90_console_printf("storage: detail=%s\r\n", boot_storage.detail);
    if (boot_storage.warning[0] != '\0') {
        a90_console_printf("storage: warning=%s\r\n", boot_storage.warning);
    }
    a90_console_printf("storage: log=%s\r\n", a90_log_path());
    return 0;
}

static int cmd_mountsd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "ro";
    char node_path[PATH_MAX];
    char line[512];
    bool read_only = false;
    unsigned long flags;
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "status") == 0) {
        return cmd_mountsd_status();
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
        a90_console_printf("mountsd: unmounted %s\r\n", SD_MOUNT_POINT);
        return 0;
    }
    if (strcmp(mode, "ro") != 0 &&
        strcmp(mode, "rw") != 0 &&
        strcmp(mode, "init") != 0) {
        a90_console_printf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }

    ensure_dir("/mnt", 0755);
    ensure_dir(SD_MOUNT_POINT, 0755);
    if (get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
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
    a90_console_printf("mountsd: %s ready (%s)\r\n",
            SD_MOUNT_POINT,
            flags & MS_RDONLY ? "ro" : "rw");
    if (strcmp(mode, "init") == 0) {
        rc = ensure_sd_workspace();
        if (rc < 0) {
            return rc;
        }
        a90_console_printf("mountsd: workspace ready %s\r\n", SD_WORKSPACE_DIR);
    }
    return 0;
}

static int prepare_android_layout(bool verbose) {
    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (!path_exists("/mnt/system/system")) {
        char node_path[PATH_MAX];

        if (get_block_device_path("sda28", node_path, sizeof(node_path)) < 0) {
            if (verbose) {
                a90_console_printf("prepareandroid: sda28 mknod failed: %s\r\n", strerror(errno));
            }
            return -1;
        }
        if (mount(node_path, "/mnt/system", "ext4", MS_RDONLY, NULL) < 0 &&
            errno != EBUSY) {
            if (verbose) {
                a90_console_printf("prepareandroid: mountsystem failed: %s\r\n", strerror(errno));
            }
            return -1;
        }
    }

    ensure_dir("/system", 0755);
    ensure_dir("/apex", 0755);
    ensure_dir("/data", 0755);
    ensure_dir("/dev/usb-ffs", 0755);
    ensure_dir("/dev/usb-ffs/adb", 0755);
    ensure_dir("/dev/socket", 0755);

    if (bind_mount_dir("/mnt/system/system", "/system") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: bind /system failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/linkerconfig") &&
        create_symlink("/mnt/system/linkerconfig", "/linkerconfig") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: linkerconfig symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/vendor") &&
        create_symlink("/mnt/system/vendor", "/vendor") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: vendor symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/product") &&
        create_symlink("/mnt/system/product", "/product") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: product symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/odm") &&
        create_symlink("/mnt/system/odm", "/odm") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: odm symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/system_ext") &&
        create_symlink("/mnt/system/system_ext", "/system_ext") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: system_ext symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.runtime") &&
        create_symlink("/system/apex/com.android.runtime", "/apex/com.android.runtime") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: runtime apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.adbd") &&
        create_symlink("/system/apex/com.android.adbd", "/apex/com.android.adbd") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: adbd apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.tzdata") &&
        create_symlink("/system/apex/com.android.tzdata", "/apex/com.android.tzdata") < 0) {
        if (verbose) {
            a90_console_printf("prepareandroid: tzdata apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    return 0;
}

static int cmd_prepareandroid(void) {
    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }
    a90_console_printf("prepareandroid: ready\r\n");
    return 0;
}

static void cmd_echo(char **argv, int argc) {
    int index;

    for (index = 1; index < argc; ++index) {
        if (index > 1) {
            a90_console_printf(" ");
        }
        a90_console_printf("%s", argv[index]);
    }
    a90_console_printf("\r\n");
}

static int cmd_writefile(char **argv, int argc) {
    const char *path;
    int fd;
    int index;

    if (argc < 3) {
        a90_console_printf("usage: writefile <path> <value...>\r\n");
        return -EINVAL;
    }

    path = argv[1];
    fd = open(path, O_WRONLY);
    if (fd < 0) {
        a90_console_printf("writefile: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    for (index = 2; index < argc; ++index) {
        if (index > 2) {
            if (write_all_checked(fd, " ", 1) < 0) {
                a90_console_printf("writefile: %s: %s\r\n", path, strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
        }
        if (write_all_checked(fd, argv[index], strlen(argv[index])) < 0) {
            a90_console_printf("writefile: %s: %s\r\n", path, strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
    }
    if (close(fd) < 0) {
        a90_console_printf("writefile: %s: close: %s\r\n", path, strerror(errno));
        return negative_errno_or(EIO);
    }
    a90_console_printf("writefile: ok\r\n");
    return 0;
}

static int report_child_status(const char *tag, int status) {
    if (WIFEXITED(status)) {
        int exit_code = WEXITSTATUS(status);

        a90_console_printf("[exit %d]\r\n", exit_code);
        return exit_code;
    } else if (WIFSIGNALED(status)) {
        int signal_num = WTERMSIG(status);

        a90_console_printf("[signal %d]\r\n", signal_num);
        return 128 + signal_num;
    }

    a90_console_printf("%s: unknown child status\r\n", tag);
    return -ECHILD;
}

static void terminate_child_for_cancel(pid_t pid, const char *tag) {
    int attempt;
    int status;

    a90_console_printf("%s: terminating pid=%ld\r\n", tag, (long)pid);
    kill(pid, SIGTERM);
    for (attempt = 0; attempt < 20; ++attempt) {
        pid_t got = waitpid(pid, &status, WNOHANG);

        if (got == pid) {
            return;
        }
        if (got < 0 && errno == ECHILD) {
            return;
        }
        usleep(100000);
    }

    a90_console_printf("%s: SIGTERM timeout, sending SIGKILL\r\n", tag);
    kill(pid, SIGKILL);
    waitpid(pid, &status, 0);
}

static int wait_child_cancelable(pid_t pid, const char *tag, int *status_out) {
    while (1) {
        pid_t got = waitpid(pid, status_out, WNOHANG);
        enum a90_cancel_kind cancel;

        if (got == pid) {
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;

            a90_console_printf("%s: waitpid: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        cancel = a90_console_poll_cancel(100);
        if (cancel != CANCEL_NONE) {
            terminate_child_for_cancel(pid, tag);
            return a90_console_cancelled(tag, cancel);
        }
    }
}

static int cmd_run(char **argv, int argc) {
    static char *const envp[] = {
        "PATH=/cache:/cache/bin:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        "LD_LIBRARY_PATH=/cache/adb/lib",
        NULL
    };
    pid_t pid;
    int status;

    if (argc < 2) {
        a90_console_printf("usage: run <path> [args...]\r\n");
        return -EINVAL;
    }

    pid = fork();
    if (pid < 0) {
        a90_console_printf("run: fork: %s\r\n", strerror(errno));
        return negative_errno_or(EAGAIN);
    }

    if (pid == 0) {
        (void)a90_console_dup_stdio();
        execve(argv[1], &argv[1], envp);
        a90_console_printf("run: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    a90_console_printf("run: pid=%ld, q/Ctrl-C cancels\r\n", (long)pid);

    {
        int wait_rc = wait_child_cancelable(pid, "run", &status);

        if (wait_rc < 0) {
            return wait_rc;
        }
    }

    return report_child_status("run", status);
}

static int cmd_runandroid(char **argv, int argc) {
    static char *const envp[] = {
        "PATH=/system/bin:/system/xbin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    pid_t pid;
    int status;

    if (argc < 2) {
        a90_console_printf("usage: runandroid <path> [args...]\r\n");
        return -EINVAL;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    pid = fork();
    if (pid < 0) {
        a90_console_printf("runandroid: fork: %s\r\n", strerror(errno));
        return negative_errno_or(EAGAIN);
    }

    if (pid == 0) {
        (void)a90_console_dup_stdio();
        execve(argv[1], &argv[1], envp);
        a90_console_printf("runandroid: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    a90_console_printf("runandroid: pid=%ld, q/Ctrl-C cancels\r\n", (long)pid);

    {
        int wait_rc = wait_child_cancelable(pid, "runandroid", &status);

        if (wait_rc < 0) {
            return wait_rc;
        }
    }

    return report_child_status("runandroid", status);
}

static int ensure_adb_function(bool *needs_rebind) {
    int ret;

    ensure_dir("/config/usb_gadget/g1/functions/ffs.adb", 0770);
    ensure_dir("/dev/usb-ffs", 0755);
    ensure_dir("/dev/usb-ffs/adb", 0755);

    if (mount("adb", "/dev/usb-ffs/adb", "functionfs", 0, "uid=2000,gid=2000") < 0 &&
        errno != EBUSY) {
        return -1;
    }

    ret = symlink("/config/usb_gadget/g1/functions/ffs.adb",
                  "/config/usb_gadget/g1/configs/b.1/f2");
    if (ret == 0) {
        *needs_rebind = true;
        return 0;
    }
    if (errno == EEXIST) {
        *needs_rebind = false;
        return 0;
    }

    return -1;
}

static int cmd_startadbd(void) {
    static char *const envp[] = {
        "PATH=/system/bin:/system/xbin:/apex/com.android.adbd/bin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/apex/com.android.adbd/lib64:/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    bool needs_rebind = false;

    if (adbd_pid > 0) {
        a90_console_printf("startadbd: already running pid=%ld\r\n", (long)adbd_pid);
        return 0;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    if (ensure_adb_function(&needs_rebind) < 0) {
        a90_console_printf("startadbd: functionfs setup failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    adbd_pid = fork();
    if (adbd_pid < 0) {
        a90_console_printf("startadbd: fork failed: %s\r\n", strerror(errno));
        adbd_pid = -1;
        return negative_errno_or(EAGAIN);
    }

    if (adbd_pid == 0) {
        (void)a90_console_dup_stdio();
        execve("/apex/com.android.adbd/bin/adbd",
               (char *const[]){
                   "/apex/com.android.adbd/bin/adbd",
                   "--root_seclabel=u:r:su:s0",
                   NULL
               },
               envp);
        a90_console_printf("startadbd: execve failed: %s\r\n", strerror(errno));
        _exit(127);
    }

    if (needs_rebind) {
        a90_console_printf("startadbd: rebinding USB, serial may reconnect\r\n");
        usleep(1000000);
        wf("/config/usb_gadget/g1/UDC", "");
        usleep(200000);
        wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
        usleep(500000);
        a90_console_reattach("startadbd-rebind", true);
    }

    a90_console_printf("startadbd: pid=%ld\r\n", (long)adbd_pid);
    return 0;
}

static int cmd_stopadbd(void) {
    if (adbd_pid <= 0) {
        a90_console_printf("stopadbd: not running\r\n");
        return 0;
    }

    kill(adbd_pid, SIGTERM);
    waitpid(adbd_pid, NULL, 0);
    adbd_pid = -1;
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    umount("/dev/usb-ffs/adb");
    wf("/config/usb_gadget/g1/UDC", "");
    usleep(200000);
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    usleep(500000);
    a90_console_reattach("stopadbd-rebind", true);
    a90_console_printf("stopadbd: done\r\n");
    return 0;
}

static int netservice_log_fd(void) {
    int fd = open(NETSERVICE_LOG_PATH,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC,
                  0644);

    if (fd >= 0) {
        dprintf(fd, "\n[%ldms] %s\n", monotonic_millis(), INIT_BANNER);
    }
    return fd;
}

static void netservice_redirect_stdio(void) {
    int null_fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
    int log_fd = netservice_log_fd();

    if (null_fd >= 0) {
        dup2(null_fd, STDIN_FILENO);
        if (null_fd > STDERR_FILENO) {
            close(null_fd);
        }
    }

    if (log_fd >= 0) {
        dup2(log_fd, STDOUT_FILENO);
        dup2(log_fd, STDERR_FILENO);
        if (log_fd > STDERR_FILENO) {
            close(log_fd);
        }
    }
}

static int netservice_wait_child(pid_t pid,
                                 const char *tag,
                                 int timeout_ms,
                                 int *status_out) {
    long deadline = monotonic_millis() + timeout_ms;

    while (1) {
        pid_t got = waitpid(pid, status_out, WNOHANG);

        if (got == pid) {
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;
            a90_logf("netservice", "%s waitpid failed errno=%d error=%s",
                        tag, saved_errno, strerror(saved_errno));
            return -saved_errno;
        }
        if (monotonic_millis() >= deadline) {
            a90_logf("netservice", "%s timeout; killing pid=%ld",
                        tag, (long)pid);
            kill(pid, SIGKILL);
            waitpid(pid, status_out, 0);
            return -ETIMEDOUT;
        }
        usleep(100000);
    }
}

static int netservice_run_wait(char *const argv[],
                               const char *tag,
                               int timeout_ms) {
    pid_t pid = fork();
    int status = 0;
    int wait_rc;

    if (pid < 0) {
        int saved_errno = errno;
        a90_logf("netservice", "%s fork failed errno=%d error=%s",
                    tag, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    if (pid == 0) {
        static char *const envp[] = {
            "PATH=/cache/bin:/cache:/bin:/system/bin",
            "HOME=/",
            "TERM=vt100",
            NULL
        };

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        netservice_redirect_stdio();
        execve(argv[0], argv, envp);
        dprintf(STDERR_FILENO, "%s: execve(%s): %s\n",
                tag, argv[0], strerror(errno));
        _exit(127);
    }

    wait_rc = netservice_wait_child(pid, tag, timeout_ms, &status);
    if (wait_rc < 0) {
        return wait_rc;
    }

    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        a90_logf("netservice", "%s ok", tag);
        return 0;
    }
    if (WIFEXITED(status)) {
        a90_logf("netservice", "%s exit=%d", tag, WEXITSTATUS(status));
        return -EIO;
    }
    if (WIFSIGNALED(status)) {
        a90_logf("netservice", "%s signal=%d", tag, WTERMSIG(status));
        return -EINTR;
    }

    a90_logf("netservice", "%s unknown status=0x%x", tag, status);
    return -ECHILD;
}

static int netservice_wait_for_ifname(const char *ifname, int timeout_ms) {
    char path[PATH_MAX];
    long deadline = monotonic_millis() + timeout_ms;

    snprintf(path, sizeof(path), "/sys/class/net/%s", ifname);
    while (monotonic_millis() < deadline) {
        if (access(path, F_OK) == 0) {
            return 0;
        }
        usleep(100000);
    }

    a90_logf("netservice", "interface %s did not appear", ifname);
    return -ETIMEDOUT;
}

static void reap_tcpctl_child(void) {
    if (tcpctl_pid > 0 && waitpid(tcpctl_pid, NULL, WNOHANG) == tcpctl_pid) {
        a90_logf("netservice", "tcpctl exited pid=%ld", (long)tcpctl_pid);
        tcpctl_pid = -1;
    }
}

static bool netservice_enabled_flag(void) {
    char state[64];

    if (read_trimmed_text_file(NETSERVICE_FLAG_PATH, state, sizeof(state)) < 0) {
        return false;
    }

    return strcmp(state, "1") == 0 ||
           strcmp(state, "on") == 0 ||
           strcmp(state, "enable") == 0 ||
           strcmp(state, "enabled") == 0 ||
           strcmp(state, "ncm") == 0 ||
           strcmp(state, "tcpctl") == 0;
}

static int netservice_set_flag(bool enabled) {
    int fd;

    if (!enabled) {
        if (unlink(NETSERVICE_FLAG_PATH) < 0 && errno != ENOENT) {
            int saved_errno = errno;
            a90_console_printf("netservice: unlink %s: %s\r\n",
                    NETSERVICE_FLAG_PATH, strerror(saved_errno));
            return -saved_errno;
        }
        a90_logf("netservice", "disabled flag removed");
        return 0;
    }

    fd = open(NETSERVICE_FLAG_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
              0644);
    if (fd < 0) {
        int saved_errno = errno;
        a90_console_printf("netservice: open %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (write_all_checked(fd, "enabled\n", 8) < 0) {
        int saved_errno = errno;
        close(fd);
        a90_console_printf("netservice: write %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;
        a90_console_printf("netservice: close %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }

    a90_logf("netservice", "enabled flag written");
    return 0;
}

static int netservice_spawn_tcpctl(void) {
    pid_t pid;

    reap_tcpctl_child();
    if (tcpctl_pid > 0) {
        a90_logf("netservice", "tcpctl already running pid=%ld", (long)tcpctl_pid);
        return 0;
    }

    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        a90_logf("netservice", "tcpctl fork failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    if (pid == 0) {
        static char *const argv[] = {
            NETSERVICE_TCPCTL_HELPER,
            "listen",
            NETSERVICE_TCP_PORT,
            NETSERVICE_TCP_IDLE_SECONDS,
            NETSERVICE_TCP_MAX_CLIENTS,
            NULL
        };
        static char *const envp[] = {
            "PATH=/cache/bin:/cache:/bin:/system/bin",
            "HOME=/",
            "TERM=vt100",
            NULL
        };

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        netservice_redirect_stdio();
        execve(argv[0], (char *const *)argv, envp);
        dprintf(STDERR_FILENO, "tcpctl: execve(%s): %s\n",
                argv[0], strerror(errno));
        _exit(127);
    }

    usleep(200000);
    if (waitpid(pid, NULL, WNOHANG) == pid) {
        a90_logf("netservice", "tcpctl exited immediately pid=%ld", (long)pid);
        return -EIO;
    }

    tcpctl_pid = pid;
    a90_logf("netservice", "tcpctl started pid=%ld port=%s",
                (long)tcpctl_pid, NETSERVICE_TCP_PORT);
    return 0;
}

static int netservice_start(void) {
    char *const usbnet_argv[] = {
        NETSERVICE_USB_HELPER,
        "ncm",
        NULL
    };
    char *const ifconfig_argv[] = {
        NETSERVICE_TOYBOX,
        "ifconfig",
        NETSERVICE_IFNAME,
        NETSERVICE_DEVICE_IP,
        "netmask",
        NETSERVICE_NETMASK,
        "up",
        NULL
    };
    int rc;

    a90_logf("netservice", "start requested");
    if (access(NETSERVICE_USB_HELPER, X_OK) < 0 ||
        access(NETSERVICE_TCPCTL_HELPER, X_OK) < 0 ||
        access(NETSERVICE_TOYBOX, X_OK) < 0) {
        int saved_errno = errno;
        a90_logf("netservice", "required helper missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        return -ENOENT;
    }

    rc = netservice_run_wait(usbnet_argv, "a90_usbnet ncm", 15000);
    a90_console_reattach("netservice-ncm", false);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_wait_for_ifname(NETSERVICE_IFNAME, 5000);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_run_wait(ifconfig_argv, "ifconfig ncm0", 5000);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_spawn_tcpctl();
    if (rc < 0) {
        return rc;
    }

    a90_timeline_record(0, 0, "netservice", "ncm=%s tcp=%s",
                    NETSERVICE_IFNAME, NETSERVICE_TCP_PORT);
    a90_logf("netservice", "ready if=%s ip=%s port=%s",
                NETSERVICE_IFNAME, NETSERVICE_DEVICE_IP, NETSERVICE_TCP_PORT);
    return 0;
}

static int netservice_stop(void) {
    char *const usbnet_argv[] = {
        NETSERVICE_USB_HELPER,
        "off",
        NULL
    };
    int rc = 0;

    a90_logf("netservice", "stop requested");
    reap_tcpctl_child();
    if (tcpctl_pid > 0) {
        kill(tcpctl_pid, SIGTERM);
        waitpid(tcpctl_pid, NULL, 0);
        a90_logf("netservice", "tcpctl stopped pid=%ld", (long)tcpctl_pid);
        tcpctl_pid = -1;
    }

    if (access(NETSERVICE_USB_HELPER, X_OK) == 0) {
        rc = netservice_run_wait(usbnet_argv, "a90_usbnet off", 15000);
        a90_console_reattach("netservice-off", false);
    }

    return rc;
}

static int cmd_netservice(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "status";
    bool enabled;
    int rc;

    reap_tcpctl_child();
    enabled = netservice_enabled_flag();

    if (strcmp(subcommand, "status") == 0) {
        a90_console_printf("netservice: flag=%s enabled=%s\r\n",
                NETSERVICE_FLAG_PATH, enabled ? "yes" : "no");
        a90_console_printf("netservice: if=%s ip=%s/%s tcp=%s idle=%ss max_clients=%s\r\n",
                NETSERVICE_IFNAME,
                NETSERVICE_DEVICE_IP,
                NETSERVICE_NETMASK,
                NETSERVICE_TCP_PORT,
                NETSERVICE_TCP_IDLE_SECONDS,
                NETSERVICE_TCP_MAX_CLIENTS);
        a90_console_printf("netservice: helpers usbnet=%s tcpctl=%s toybox=%s\r\n",
                access(NETSERVICE_USB_HELPER, X_OK) == 0 ? "yes" : "no",
                access(NETSERVICE_TCPCTL_HELPER, X_OK) == 0 ? "yes" : "no",
                access(NETSERVICE_TOYBOX, X_OK) == 0 ? "yes" : "no");
        a90_console_printf("netservice: ncm0=%s tcpctl=%s",
                access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0 ? "present" : "absent",
                tcpctl_pid > 0 ? "running" : "stopped");
        if (tcpctl_pid > 0) {
            a90_console_printf(" pid=%ld", (long)tcpctl_pid);
        }
        a90_console_printf("\r\n");
        a90_console_printf("netservice: log=%s\r\n", NETSERVICE_LOG_PATH);
        return 0;
    }

    if (strcmp(subcommand, "start") == 0) {
        rc = netservice_start();
        a90_console_printf("netservice: start %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "stop") == 0) {
        rc = netservice_stop();
        a90_console_printf("netservice: stop %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "enable") == 0) {
        rc = netservice_set_flag(true);
        if (rc < 0) {
            return rc;
        }
        rc = netservice_start();
        a90_console_printf("netservice: enable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "disable") == 0) {
        int flag_rc = netservice_set_flag(false);
        rc = netservice_stop();
        if (flag_rc < 0) {
            return flag_rc;
        }
        a90_console_printf("netservice: disable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    a90_console_printf("usage: netservice [status|start|stop|enable|disable]\r\n");
    return -EINVAL;
}

static int cmd_reattach(void) {
    if (a90_console_reattach("command", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_usbacmreset(void) {
    a90_console_printf("usbacmreset: rebinding ACM, serial may reconnect\r\n");
    wf("/config/usb_gadget/g1/UDC", "");
    usleep(300000);
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    setup_acm_gadget();
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    usleep(700000);
    if (a90_console_reattach("usbacmreset", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_recovery(void) {
    a90_console_printf("recovery: syncing and rebooting to recovery\r\n");
    sync();
    syscall(SYS_reboot,
            LINUX_REBOOT_MAGIC1,
            LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2,
            "recovery");
    a90_console_printf("recovery: %s\r\n", strerror(errno));
    return negative_errno_or(EIO);
}

typedef int (*command_handler)(char **argv, int argc);
