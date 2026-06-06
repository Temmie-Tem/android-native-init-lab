/* Included by stage3/linux_init/init_v150.c. Do not compile standalone. */

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

static int report_run_result(const char *tag, const struct a90_run_result *result) {
    if (result == NULL) {
        return -EINVAL;
    }
    if (result->rc < 0) {
        return result->rc;
    }
    if (WIFEXITED(result->status)) {
        int exit_code = WEXITSTATUS(result->status);

        a90_console_printf("[exit %d]\r\n", exit_code);
        return exit_code;
    }
    if (WIFSIGNALED(result->status)) {
        int signal_num = WTERMSIG(result->status);

        a90_console_printf("[signal %d]\r\n", signal_num);
        return 128 + signal_num;
    }

    a90_console_printf("%s: unknown child status\r\n", tag);
    return -ECHILD;
}

static int run_console_child(const char *tag,
                             char **child_argv,
                             char *envp[]) {
    struct a90_run_config config = {
        .tag = tag,
        .argv = child_argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_CONSOLE,
        .cancelable = true,
        .stop_timeout_ms = 2000,
    };
    struct a90_run_result result;
    pid_t pid;
    int rc;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        int saved_errno = -rc;
        if (saved_errno <= 0) {
            saved_errno = EAGAIN;
        }
        a90_console_printf("%s: fork: %s\r\n", tag, strerror(saved_errno));
        return rc;
    }

    a90_console_printf("%s: pid=%ld, q/Ctrl-C cancels\r\n", tag, (long)pid);
    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        if (rc != -ECANCELED) {
            int saved_errno = -rc;
            if (saved_errno <= 0) {
                saved_errno = EIO;
            }
            a90_console_printf("%s: wait: %s\r\n", tag, strerror(saved_errno));
        }
        return rc;
    }

    return report_run_result(tag, &result);
}

static int cmd_run(char **argv, int argc) {
    static char *envp[] = {
        "PATH=/cache:/cache/bin:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        "LD_LIBRARY_PATH=/cache/adb/lib",
        NULL
    };
    if (argc < 2) {
        a90_console_printf("usage: run <path> [args...]\r\n");
        return -EINVAL;
    }

    return run_console_child("run", &argv[1], envp);
}

static int cmd_runandroid(char **argv, int argc) {
    static char *envp[] = {
        "PATH=/system/bin:/system/xbin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    if (argc < 2) {
        a90_console_printf("usage: runandroid <path> [args...]\r\n");
        return -EINVAL;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    return run_console_child("runandroid", &argv[1], envp);
}

static char *userland_envp[] = {
    "PATH=/mnt/sdext/a90/bin:/cache/a90-runtime/bin:/cache/bin:/bin:/system/bin",
    "HOME=/",
    "TERM=vt100",
    NULL
};

static int run_userland_child(const char *tag,
                              const char *name,
                              char **argv,
                              int argc) {
    enum { MAX_USERLAND_ARGS = CMDV1X_MAX_ARGS + 2 };
    char *child_argv[MAX_USERLAND_ARGS];
    const char *path;
    int index;

    if (argc < 2) {
        a90_console_printf("usage: %s <applet> [args...]\r\n", name);
        return -EINVAL;
    }
    if (argc + 1 > MAX_USERLAND_ARGS) {
        a90_console_printf("%s: too many args\r\n", name);
        return -E2BIG;
    }
    path = a90_userland_path(name);
    if (path == NULL || path[0] == '\0') {
        a90_console_printf("%s: not installed\r\n", name);
        return -ENOENT;
    }
    child_argv[0] = (char *)path;
    for (index = 1; index < argc; ++index) {
        child_argv[index] = argv[index];
    }
    child_argv[argc] = NULL;
    return run_console_child(tag, child_argv, userland_envp);
}

static int run_userland_test_command(const char *tag, char **child_argv) {
    return run_console_child(tag, child_argv, userland_envp);
}

static int cmd_userland_test_one(const char *name) {
    const char *path = a90_userland_path(name);
    int first_error = 0;
    int rc;

    if (path == NULL || path[0] == '\0') {
        a90_console_printf("userland-test: %s not installed\r\n", name);
        return -ENOENT;
    }

    a90_console_printf("userland-test: %s path=%s\r\n", name, path);
    if (strcmp(name, "busybox") == 0) {
        char *help_argv[] = { (char *)path, "--help", NULL };
        char *shell_argv[] = {
            (char *)path,
            "sh",
            "-c",
            "echo A90_BUSYBOX_OK",
            NULL
        };
        char *ls_argv[] = { (char *)path, "ls", "/proc", NULL };
        char *cat_argv[] = { (char *)path, "cat", "/proc/version", NULL };
        char *kill_argv[] = { (char *)path, "kill", "-0", "1", NULL };

        rc = run_userland_test_command("busybox-help", help_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("busybox-sh", shell_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("busybox-ls", ls_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("busybox-cat", cat_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("busybox-kill", kill_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        return first_error;
    }
    if (strcmp(name, "toybox") == 0) {
        char *help_argv[] = { (char *)path, "--help", NULL };
        char *uname_argv[] = { (char *)path, "uname", "-a", NULL };
        char *ifconfig_argv[] = { (char *)path, "ifconfig", "-a", NULL };

        rc = run_userland_test_command("toybox-help", help_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("toybox-uname", uname_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        rc = run_userland_test_command("toybox-ifconfig", ifconfig_argv);
        if (rc != 0 && first_error == 0) {
            first_error = rc;
        }
        return first_error;
    }

    a90_console_printf("userland-test: unknown target %s\r\n", name);
    return -EINVAL;
}

static int cmd_userland(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    const char *target;
    int rc = 0;
    int target_rc;
    bool any_success = false;

    if (strcmp(subcommand, "status") == 0) {
        return a90_userland_print_inventory(false);
    }
    if (strcmp(subcommand, "verbose") == 0) {
        return a90_userland_print_inventory(true);
    }
    if (strcmp(subcommand, "test") != 0) {
        a90_console_printf("usage: userland [status|verbose|test [busybox|toybox|all]]\r\n");
        return -EINVAL;
    }
    if (argc > 3) {
        a90_console_printf("usage: userland test [busybox|toybox|all]\r\n");
        return -EINVAL;
    }

    target = argc > 2 ? argv[2] : "all";
    if (strcmp(target, "busybox") == 0) {
        return cmd_userland_test_one("busybox");
    }
    if (strcmp(target, "toybox") == 0) {
        return cmd_userland_test_one("toybox");
    }
    if (strcmp(target, "all") != 0) {
        a90_console_printf("usage: userland test [busybox|toybox|all]\r\n");
        return -EINVAL;
    }

    target_rc = cmd_userland_test_one("busybox");
    if (target_rc == 0) {
        any_success = true;
    } else if (target_rc != -ENOENT && rc == 0) {
        rc = target_rc;
    }
    target_rc = cmd_userland_test_one("toybox");
    if (target_rc == 0) {
        any_success = true;
    } else if (target_rc != -ENOENT && rc == 0) {
        rc = target_rc;
    }
    if (!any_success && rc == 0) {
        rc = -ENOENT;
    }
    return rc;
}

static int cmd_busybox(char **argv, int argc) {
    return run_userland_child("busybox", "busybox", argv, argc);
}

static int cmd_toybox(char **argv, int argc) {
    return run_userland_child("toybox", "toybox", argv, argc);
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
    static char *envp[] = {
        "PATH=/system/bin:/system/xbin:/apex/com.android.adbd/bin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/apex/com.android.adbd/lib64:/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    char *adbd_argv[] = {
        "/apex/com.android.adbd/bin/adbd",
        "--root_seclabel=u:r:su:s0",
        NULL
    };
    struct a90_run_config config = {
        .tag = "startadbd",
        .argv = adbd_argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_CONSOLE,
        .stop_timeout_ms = 2000,
    };
    bool needs_rebind = false;
    pid_t pid;
    int status = 0;
    int rc;

    (void)a90_service_reap(A90_SERVICE_ADBD, NULL);
    if (a90_service_pid(A90_SERVICE_ADBD) > 0) {
        a90_console_printf("startadbd: already running pid=%ld\r\n",
                (long)a90_service_pid(A90_SERVICE_ADBD));
        return 0;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    if (ensure_adb_function(&needs_rebind) < 0) {
        a90_console_printf("startadbd: functionfs setup failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        int saved_errno = -rc;
        if (saved_errno <= 0) {
            saved_errno = EAGAIN;
        }
        a90_console_printf("startadbd: fork failed: %s\r\n", strerror(saved_errno));
        return rc;
    }
    a90_service_set_pid(A90_SERVICE_ADBD, pid);

    if (needs_rebind) {
        a90_console_printf("startadbd: rebinding USB, serial may reconnect\r\n");
        usleep(1000000);
        a90_usb_gadget_unbind();
        usleep(200000);
        a90_usb_gadget_bind_default_udc();
        usleep(500000);
        a90_console_reattach("startadbd-rebind", true);
    }

    usleep(200000);
    if (a90_service_reap(A90_SERVICE_ADBD, &status) > 0) {
        struct a90_run_result result = {
            .pid = pid,
            .status = status,
        };
        int child_rc = a90_run_result_to_rc(&result);

        a90_console_printf("startadbd: exited immediately rc=%d\r\n", child_rc);
        return child_rc == 0 ? -EIO : child_rc;
    }

    a90_console_printf("startadbd: pid=%ld\r\n", (long)pid);
    return 0;
}

static int cmd_stopadbd(void) {
    (void)a90_service_reap(A90_SERVICE_ADBD, NULL);
    if (a90_service_pid(A90_SERVICE_ADBD) <= 0) {
        a90_console_printf("stopadbd: not running\r\n");
        return 0;
    }

    (void)a90_service_stop(A90_SERVICE_ADBD, 2000);
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    umount("/dev/usb-ffs/adb");
    a90_usb_gadget_unbind();
    usleep(200000);
    a90_usb_gadget_bind_default_udc();
    usleep(500000);
    a90_console_reattach("stopadbd-rebind", true);
    a90_console_printf("stopadbd: done\r\n");
    return 0;
}

static int cmd_netservice(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "status";
    struct a90_netservice_status status;
    int rc;

    a90_netservice_status(&status);

    if (strcmp(subcommand, "status") == 0) {
        a90_console_printf("netservice: flag=%s enabled=%s\r\n",
                status.flag_path, status.enabled ? "yes" : "no");
        a90_console_printf("netservice: if=%s ip=%s/%s tcp=%s bind=%s idle=%ss max_clients=%s auth=required\r\n",
                status.ifname,
                status.device_ip,
                status.netmask,
                status.tcp_port,
                status.tcp_bind_addr,
                status.tcp_idle_seconds,
                status.tcp_max_clients);
        a90_console_printf("netservice: helpers usbnet=%s tcpctl=%s toybox=%s\r\n",
                status.usbnet_helper ? "yes" : "no",
                status.tcpctl_helper ? "yes" : "no",
                status.toybox_helper ? "yes" : "no");
        a90_console_printf("netservice: ncm0=%s tcpctl=%s",
                status.ncm_present ? "present" : "absent",
                status.tcpctl_running ? "running" : "stopped");
        if (status.tcpctl_running) {
            a90_console_printf(" pid=%ld", (long)status.tcpctl_pid);
        }
        a90_console_printf("\r\n");
        a90_console_printf("netservice: log=%s token=%s token_path=%s\r\n",
                status.log_path,
                status.tcp_token_present ? "present" : "missing",
                status.tcp_token_path);
        return 0;
    }

    if (strcmp(subcommand, "token") == 0) {
        char token[64];
        bool rotate = argc >= 3 && strcmp(argv[2], "rotate") == 0;

        if (argc >= 3 &&
            strcmp(argv[2], "show") != 0 &&
            strcmp(argv[2], "rotate") != 0) {
            a90_console_printf("usage: netservice token [show|rotate]\r\n");
            return -EINVAL;
        }
        rc = rotate ?
            a90_netservice_rotate_token(token, sizeof(token)) :
            a90_netservice_token(token, sizeof(token));
        if (rc < 0) {
            a90_console_printf("netservice: token failed rc=%d\r\n", rc);
            return rc;
        }
        a90_console_printf("netservice: tcpctl_token=%s path=%s rotated=%s\r\n",
                token,
                NETSERVICE_TCP_TOKEN_PATH,
                rotate ? "yes" : "no");
        return 0;
    }

    if (strcmp(subcommand, "start") == 0) {
        rc = a90_netservice_start();
        a90_console_printf("netservice: start %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "stop") == 0) {
        rc = a90_netservice_stop();
        a90_console_printf("netservice: stop %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "enable") == 0) {
        rc = a90_netservice_set_enabled(true);
        if (rc < 0) {
            return rc;
        }
        rc = a90_netservice_start();
        a90_console_printf("netservice: enable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "disable") == 0) {
        int flag_rc = a90_netservice_set_enabled(false);
        rc = a90_netservice_stop();
        if (flag_rc < 0) {
            return flag_rc;
        }
        a90_console_printf("netservice: disable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    a90_console_printf("usage: netservice [status|start|stop|enable|disable|token [show|rotate]]\r\n");
    return -EINVAL;
}


static void rshell_state_path(char *out, size_t out_size, const char *name) {
    const char *state_dir = a90_runtime_state_dir();

    if (out == NULL || out_size == 0) {
        return;
    }
    if (state_dir == NULL || state_dir[0] == '\0') {
        state_dir = A90_RUNTIME_CACHE_ROOT "/" A90_RUNTIME_STATE_DIR;
    }
    snprintf(out, out_size, "%s/%s", state_dir, name);
    out[out_size - 1] = '\0';
}

static bool rshell_enabled(void) {
    char path[PATH_MAX];
    char state[64];

    rshell_state_path(path, sizeof(path), A90_RSHELL_FLAG_NAME);
    if (read_trimmed_text_file(path, state, sizeof(state)) < 0) {
        return false;
    }
    return strcmp(state, "1") == 0 ||
           strcmp(state, "on") == 0 ||
           strcmp(state, "enable") == 0 ||
           strcmp(state, "enabled") == 0 ||
           strcmp(state, "rshell") == 0;
}

static int rshell_set_enabled(bool enabled) {
    char path[PATH_MAX];
    int fd;

    rshell_state_path(path, sizeof(path), A90_RSHELL_FLAG_NAME);
    if (!enabled) {
        if (unlink(path) < 0 && errno != ENOENT) {
            int saved_errno = errno;

            a90_console_printf("rshell: unlink %s: %s\r\n", path, strerror(saved_errno));
            return -saved_errno;
        }
        a90_logf("rshell", "disabled flag removed path=%s", path);
        return 0;
    }

    ensure_dir(a90_runtime_state_dir(), 0755);
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("rshell: open %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    if (write_all_checked(fd, "enabled\n", 8) < 0) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("rshell: write %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;

        a90_console_printf("rshell: close %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    a90_logf("rshell", "enabled flag written path=%s", path);
    return 0;
}

static int rshell_read_token(char *out, size_t out_size) {
    char path[PATH_MAX];

    rshell_state_path(path, sizeof(path), A90_RSHELL_TOKEN_NAME);
    if (read_trimmed_text_file(path, out, out_size) < 0 || out[0] == '\0') {
        return -ENOENT;
    }
    return 0;
}

static int rshell_token_file_mode(char *out, size_t out_size, bool *strict) {
    char path[PATH_MAX];
    struct stat st;

    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "missing");
    }
    if (strict != NULL) {
        *strict = false;
    }
    rshell_state_path(path, sizeof(path), A90_RSHELL_TOKEN_NAME);
    if (lstat(path, &st) < 0) {
        return -errno;
    }
    if (S_ISLNK(st.st_mode)) {
        return -ELOOP;
    }
    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "0%03o", (unsigned)(st.st_mode & 0777));
    }
    if (strict != NULL) {
        *strict = (st.st_mode & 0077) == 0;
    }
    return 0;
}

static int rshell_write_token(const char *token) {
    char path[PATH_MAX];
    int fd;

    if (token == NULL || token[0] == '\0') {
        return -EINVAL;
    }
    rshell_state_path(path, sizeof(path), A90_RSHELL_TOKEN_NAME);
    ensure_dir(a90_runtime_state_dir(), 0755);
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("rshell: open token %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    fchmod(fd, 0600);
    if (write_all_checked(fd, token, strlen(token)) < 0 ||
        write_all_checked(fd, "\n", 1) < 0) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("rshell: write token %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;

        a90_console_printf("rshell: close token %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }
    a90_logf("rshell", "token written path=%s", path);
    return 0;
}

static void rshell_generate_token(char *out, size_t out_size) {
    unsigned char random_bytes[16];
    int fd;
    size_t index;
    static const char hex[] = "0123456789abcdef";

    if (out == NULL || out_size < 33) {
        return;
    }
    memset(random_bytes, 0, sizeof(random_bytes));
    fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
    if (fd >= 0) {
        ssize_t rd = read(fd, random_bytes, sizeof(random_bytes));

        close(fd);
        if (rd != (ssize_t)sizeof(random_bytes)) {
            memset(random_bytes, 0, sizeof(random_bytes));
        }
    }
    if (random_bytes[0] == 0 && random_bytes[1] == 0) {
        unsigned long seed = (unsigned long)monotonic_millis() ^ (unsigned long)getpid();

        for (index = 0; index < sizeof(random_bytes); ++index) {
            seed = seed * 1103515245UL + 12345UL;
            random_bytes[index] = (unsigned char)(seed >> 16);
        }
    }
    for (index = 0; index < sizeof(random_bytes); ++index) {
        out[index * 2] = hex[random_bytes[index] >> 4];
        out[index * 2 + 1] = hex[random_bytes[index] & 0x0f];
    }
    out[32] = '\0';
}

static int rshell_ensure_token(char *out, size_t out_size, bool print_created) {
    char token[64];
    int rc;

    rc = rshell_read_token(token, sizeof(token));
    if (rc == 0) {
        if (out != NULL && out_size > 0) {
            snprintf(out, out_size, "%s", token);
        }
        return 0;
    }

    rshell_generate_token(token, sizeof(token));
    rc = rshell_write_token(token);
    if (rc < 0) {
        return rc;
    }
    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "%s", token);
    }
    if (print_created) {
        a90_console_printf("rshell: generated token=%s\r\n", token);
    }
    return 0;
}

static int rshell_stop_service(void) {
    pid_t pid;
    int status = 0;
    int rc;

    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    pid = a90_service_pid(A90_SERVICE_RSHELL);
    if (pid <= 0) {
        return 0;
    }
    rc = a90_run_stop_pid_ex(pid, "rshell", 2000, true, &status);
    a90_service_clear(A90_SERVICE_RSHELL);
    a90_logf("rshell", "stopped pid=%ld rc=%d status=0x%x", (long)pid, rc, status);
    return rc;
}

static int rshell_start_service(bool print_token) {
    char token[64];
    char token_path[PATH_MAX];
    const char *helper_path;
    const char *busybox_path;
    struct a90_netservice_status net_status;
    char *const envp[] = {
        "PATH=/cache/bin:/cache:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    char *child_argv[7];
    struct a90_run_config config;
    pid_t pid;
    int status = 0;
    int rc;

    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    if (a90_service_pid(A90_SERVICE_RSHELL) > 0) {
        a90_console_printf("rshell: already running pid=%ld port=%s\r\n",
                (long)a90_service_pid(A90_SERVICE_RSHELL), A90_RSHELL_PORT);
        return 0;
    }

    helper_path = a90_helper_preferred_path("a90_rshell", A90_RSHELL_RAMDISK_HELPER);
    busybox_path = a90_userland_path("busybox");
    if (busybox_path == NULL || busybox_path[0] == '\0') {
        busybox_path = a90_helper_preferred_path("busybox", A90_BUSYBOX_HELPER);
    }
    if (helper_path == NULL || helper_path[0] == '\0' || access(helper_path, X_OK) < 0) {
        a90_console_printf("rshell: helper missing: %s\r\n",
                helper_path != NULL && helper_path[0] != '\0' ? helper_path : "a90_rshell");
        return -ENOENT;
    }
    if (busybox_path == NULL || busybox_path[0] == '\0' || access(busybox_path, X_OK) < 0) {
        a90_console_printf("rshell: busybox shell missing\r\n");
        return -ENOENT;
    }

    rc = rshell_ensure_token(token, sizeof(token), print_token);
    if (rc < 0) {
        return rc;
    }
    rshell_state_path(token_path, sizeof(token_path), A90_RSHELL_TOKEN_NAME);

    a90_netservice_status(&net_status);
    if (!net_status.ncm_present) {
        a90_console_printf("rshell: starting NCM netservice first\r\n");
        rc = a90_netservice_start();
        if (rc < 0) {
            a90_console_printf("rshell: netservice start failed rc=%d\r\n", rc);
            return rc;
        }
    }

    child_argv[0] = (char *)helper_path;
    child_argv[1] = (char *)A90_RSHELL_BIND_ADDR;
    child_argv[2] = (char *)A90_RSHELL_PORT;
    child_argv[3] = token_path;
    child_argv[4] = (char *)busybox_path;
    child_argv[5] = (char *)A90_RSHELL_IDLE_SECONDS;
    child_argv[6] = NULL;
    memset(&config, 0, sizeof(config));
    config.tag = "rshell";
    config.argv = child_argv;
    config.envp = envp;
    config.stdio_mode = A90_RUN_STDIO_LOG_APPEND;
    config.log_path = A90_RSHELL_LOG_PATH;
    config.setsid = true;
    config.ignore_hup_pipe = true;
    config.kill_process_group = true;
    config.stop_timeout_ms = 2000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    a90_service_set_pid(A90_SERVICE_RSHELL, pid);
    usleep(250000);
    if (a90_service_reap(A90_SERVICE_RSHELL, &status) > 0) {
        a90_console_printf("rshell: helper exited immediately status=0x%x log=%s\r\n",
                status, A90_RSHELL_LOG_PATH);
        return -EIO;
    }

    a90_logf("rshell", "started pid=%ld bind=%s port=%s shell=%s token=%s",
                (long)pid,
                A90_RSHELL_BIND_ADDR,
                A90_RSHELL_PORT,
                busybox_path,
                token_path);
    a90_timeline_record(0, 0, "rshell", "tcp=%s:%s", A90_RSHELL_BIND_ADDR, A90_RSHELL_PORT);
    a90_console_printf("rshell: started bind=%s port=%s pid=%ld\r\n",
            A90_RSHELL_BIND_ADDR, A90_RSHELL_PORT, (long)pid);
    if (print_token) {
        a90_console_printf("rshell: token=%s\r\n", token);
    }
    return 0;
}

static int rshell_print_audit(const char *helper_path,
                              const char *busybox_path,
                              const char *flag_path,
                              const char *token_path,
                              bool token_present,
                              const char *token_mode,
                              bool token_strict,
                              const struct a90_netservice_status *net_status,
                              pid_t pid) {
    int warnings = 0;
    bool helper_present = helper_path != NULL && helper_path[0] != '\0' &&
                          access(helper_path, X_OK) == 0;
    bool busybox_present = busybox_path != NULL && busybox_path[0] != '\0' &&
                           access(busybox_path, X_OK) == 0;

    if (!helper_present) {
        warnings++;
    }
    if (!busybox_present) {
        warnings++;
    }
    if (token_present && !token_strict) {
        warnings++;
    }

    a90_console_printf("rshell-audit: enabled=%s running=%s pid=%ld\r\n",
            rshell_enabled() ? "yes" : "no",
            pid > 0 ? "yes" : "no",
            (long)pid);
    a90_console_printf("rshell-audit: bind=%s port=%s idle=%ss usb_only=yes opt_in=yes\r\n",
            A90_RSHELL_BIND_ADDR,
            A90_RSHELL_PORT,
            A90_RSHELL_IDLE_SECONDS);
    a90_console_printf("rshell-audit: helper=%s present=%s busybox=%s present=%s\r\n",
            helper_path != NULL && helper_path[0] != '\0' ? helper_path : "-",
            helper_present ? "yes" : "no",
            busybox_path != NULL && busybox_path[0] != '\0' ? busybox_path : "-",
            busybox_present ? "yes" : "no");
    a90_console_printf("rshell-audit: token=%s mode=%s strict=%s token_path=%s\r\n",
            token_present ? "present" : "missing",
            token_mode != NULL && token_mode[0] != '\0' ? token_mode : "-",
            token_strict ? "yes" : "no",
            token_path != NULL ? token_path : "-");
    a90_console_printf("rshell-audit: flag_path=%s log=%s ncm=%s tcpctl=%s\r\n",
            flag_path != NULL ? flag_path : "-",
            A90_RSHELL_LOG_PATH,
            net_status != NULL && net_status->ncm_present ? "present" : "absent",
            net_status != NULL && net_status->tcpctl_running ? "running" : "stopped");
    a90_console_printf("rshell-audit: result=%s warnings=%d\r\n",
            warnings == 0 ? "ok" : "warn",
            warnings);
    return 0;
}

static int cmd_rshell(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "status";
    char flag_path[PATH_MAX];
    char token_path[PATH_MAX];
    char token[64];
    char token_mode[16];
    const char *helper_path;
    const char *busybox_path;
    bool token_present;
    bool token_strict = false;
    struct a90_netservice_status net_status;
    pid_t pid;
    int rc;

    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    helper_path = a90_helper_preferred_path("a90_rshell", A90_RSHELL_RAMDISK_HELPER);
    busybox_path = a90_userland_path("busybox");
    if (busybox_path == NULL || busybox_path[0] == '\0') {
        busybox_path = a90_helper_preferred_path("busybox", A90_BUSYBOX_HELPER);
    }
    rshell_state_path(flag_path, sizeof(flag_path), A90_RSHELL_FLAG_NAME);
    rshell_state_path(token_path, sizeof(token_path), A90_RSHELL_TOKEN_NAME);
    token_present = rshell_read_token(token, sizeof(token)) == 0;
    (void)rshell_token_file_mode(token_mode, sizeof(token_mode), &token_strict);
    a90_netservice_status(&net_status);
    pid = a90_service_pid(A90_SERVICE_RSHELL);

    if (strcmp(subcommand, "status") == 0) {
        a90_console_printf("rshell: enabled=%s running=%s pid=%ld bind=%s port=%s idle=%ss\r\n",
                rshell_enabled() ? "yes" : "no",
                pid > 0 ? "yes" : "no",
                (long)pid,
                A90_RSHELL_BIND_ADDR,
                A90_RSHELL_PORT,
                A90_RSHELL_IDLE_SECONDS);
        a90_console_printf("rshell: helper=%s present=%s busybox=%s present=%s\r\n",
                helper_path != NULL && helper_path[0] != '\0' ? helper_path : "-",
                helper_path != NULL && helper_path[0] != '\0' && access(helper_path, X_OK) == 0 ? "yes" : "no",
                busybox_path != NULL && busybox_path[0] != '\0' ? busybox_path : "-",
                busybox_path != NULL && busybox_path[0] != '\0' && access(busybox_path, X_OK) == 0 ? "yes" : "no");
        a90_console_printf("rshell: token=%s token_mode=%s token_strict=%s token_path=%s flag_path=%s\r\n",
                token_present ? "present" : "missing",
                token_mode,
                token_strict ? "yes" : "no",
                token_path,
                flag_path);
        a90_console_printf("rshell: ncm=%s tcpctl=%s log=%s\r\n",
                net_status.ncm_present ? "present" : "absent",
                net_status.tcpctl_running ? "running" : "stopped",
                A90_RSHELL_LOG_PATH);
        return 0;
    }

    if (strcmp(subcommand, "audit") == 0) {
        return rshell_print_audit(helper_path,
                                  busybox_path,
                                  flag_path,
                                  token_path,
                                  token_present,
                                  token_mode,
                                  token_strict,
                                  &net_status,
                                  pid);
    }

    if (strcmp(subcommand, "start") == 0) {
        return rshell_start_service(true);
    }

    if (strcmp(subcommand, "stop") == 0) {
        rc = rshell_stop_service();
        a90_console_printf("rshell: stop %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "enable") == 0) {
        rc = rshell_set_enabled(true);
        if (rc < 0) {
            return rc;
        }
        rc = rshell_start_service(true);
        a90_console_printf("rshell: enable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "disable") == 0) {
        int flag_rc = rshell_set_enabled(false);

        rc = rshell_stop_service();
        if (flag_rc < 0) {
            return flag_rc;
        }
        a90_console_printf("rshell: disable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "token") == 0) {
        if (argc >= 3 && strcmp(argv[2], "show") == 0) {
            if (!token_present) {
                a90_console_printf("rshell: token missing\r\n");
                return -ENOENT;
            }
            a90_console_printf("rshell: token=%s\r\n", token);
            return 0;
        }
        if (argc > 2) {
            a90_console_printf("usage: rshell token [show]\r\n");
            return -EINVAL;
        }
        a90_console_printf("rshell: token=%s path=%s\r\n",
                token_present ? "present" : "missing",
                token_path);
        return token_present ? 0 : -ENOENT;
    }

    if (strcmp(subcommand, "rotate-token") == 0) {
        if (argc >= 3) {
            snprintf(token, sizeof(token), "%s", argv[2]);
        } else {
            rshell_generate_token(token, sizeof(token));
        }
        if (token[0] == '\0') {
            return -EINVAL;
        }
        rc = rshell_write_token(token);
        if (rc < 0) {
            return rc;
        }
        a90_console_printf("rshell: token=%s\r\n", token);
        if (pid > 0) {
            a90_console_printf("rshell: restart required for active clients to use new token\r\n");
        }
        return 0;
    }

    a90_console_printf("usage: rshell [status|audit|start|stop|enable|disable|token [show]|rotate-token [value]]\r\n");
    return -EINVAL;
}

static int cmd_reattach(void) {
    if (a90_console_reattach("command", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_usbacmreset(void) {
    int rc;

    a90_console_printf("usbacmreset: rebinding ACM, serial may reconnect\r\n");
    rc = a90_usb_gadget_reset_acm();
    if (rc < 0) {
        a90_console_printf("usbacmreset: failed rc=%d\r\n", rc);
        return rc;
    }
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
