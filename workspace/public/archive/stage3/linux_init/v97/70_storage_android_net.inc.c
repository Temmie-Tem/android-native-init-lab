/* Included by stage3/linux_init/init_v97.c. Do not compile standalone. */

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
                             char *const envp[]) {
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
    static char *const envp[] = {
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
    static char *const envp[] = {
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
    char *const adbd_argv[] = {
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
        a90_console_printf("netservice: if=%s ip=%s/%s tcp=%s idle=%ss max_clients=%s\r\n",
                status.ifname,
                status.device_ip,
                status.netmask,
                status.tcp_port,
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
        a90_console_printf("netservice: log=%s\r\n", status.log_path);
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
