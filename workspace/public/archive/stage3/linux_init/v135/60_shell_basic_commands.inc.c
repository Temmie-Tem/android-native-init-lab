/* Included by stage3/linux_init/init_v135.c. Do not compile standalone. */

static int cmd_pwd(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        a90_console_printf("pwd: %s\r\n", strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("%s\r\n", cwd);
    return 0;
}

static void cmd_help(void) {
    a90_console_printf("help\r\n");
    a90_console_printf("version\r\n");
    a90_console_printf("status\r\n");
    a90_console_printf("last\r\n");
    a90_console_printf("cmdmeta [verbose]\r\n");
    a90_console_printf("cmdgroups [verbose]\r\n");
    a90_console_printf("logpath\r\n");
    a90_console_printf("logcat\r\n");
    a90_console_printf("hudlog [status|on|off]\r\n");
    a90_console_printf("exposure [status|verbose|guard]\r\n");
    a90_console_printf("policycheck [status|run|verbose]\r\n");
    a90_console_printf("diag [summary|full|bundle|paths]\r\n");
    a90_console_printf("wifiinv [summary|full|refresh|paths]\r\n");
    a90_console_printf("wififeas [summary|full|gate|refresh|paths]\r\n");
    a90_console_printf("timeline\r\n");
    a90_console_printf("bootstatus\r\n");
    a90_console_printf("selftest [status|run|verbose]\r\n");
    a90_console_printf("pid1guard [status|run|verbose]\r\n");
    a90_console_printf("blocking commands: q or Ctrl-C cancels\r\n");
    a90_console_printf("uname\r\n");
    a90_console_printf("pwd\r\n");
    a90_console_printf("cd <dir>\r\n");
    a90_console_printf("ls [dir]\r\n");
    a90_console_printf("cat <file>\r\n");
    a90_console_printf("stat <path>\r\n");
    a90_console_printf("mounts\r\n");
    a90_console_printf("mountsystem [ro|rw]\r\n");
    a90_console_printf("mountsd [status|ro|rw|off|init]\r\n");
    a90_console_printf("storage\r\n");
    a90_console_printf("runtime\r\n");
    a90_console_printf("helpers [status|verbose|manifest|plan|path <name>|verify [name]]\r\n");
    a90_console_printf("userland [status|verbose|test [busybox|toybox|all]]\r\n");
    a90_console_printf("busybox <applet> [args...]\r\n");
    a90_console_printf("toybox <applet> [args...]\r\n");
    a90_console_printf("prepareandroid\r\n");
    a90_console_printf("inputinfo [eventX]\r\n");
    a90_console_printf("drminfo [entry]\r\n");
    a90_console_printf("fbinfo [fbX]\r\n");
    a90_console_printf("kmsprobe\r\n");
    a90_console_printf("kmssolid [color]\r\n");
    a90_console_printf("kmsframe\r\n");
    a90_console_printf("statusscreen\r\n");
    a90_console_printf("statushud\r\n");
    a90_console_printf("watchhud [sec] [count]\r\n");
    a90_console_printf("autohud [sec]\r\n");
    a90_console_printf("stophud\r\n");
    a90_console_printf("redraw\r\n");
    a90_console_printf("testpattern\r\n");
    a90_console_printf("clear\r\n");
    a90_console_printf("inputcaps <eventX>\r\n");
    a90_console_printf("readinput <eventX> [count]\r\n");
    a90_console_printf("waitkey [count]\r\n");
    a90_console_printf("inputlayout\r\n");
    a90_console_printf("waitgesture [count]\r\n");
    a90_console_printf("inputmonitor [events]\r\n");
    a90_console_printf("displaytest [0-3|colors|font|safe|layout]\r\n");
    a90_console_printf("cutoutcal [x y size]\r\n");
    a90_console_printf("menu\r\n");
    a90_console_printf("screenmenu\r\n");
    a90_console_printf("hide\r\n");
    a90_console_printf("hidemenu\r\n");
    a90_console_printf("cmdv1 <command> [args...]\r\n");
    a90_console_printf("cmdv1x <len:hex-utf8-arg>...\r\n");
    a90_console_printf("blindmenu\r\n");
    a90_console_printf("mkdir <dir>\r\n");
    a90_console_printf("mknodc <path> <major> <minor>\r\n");
    a90_console_printf("mknodb <path> <major> <minor>\r\n");
    a90_console_printf("mountfs <src> <dst> <type> [ro]\r\n");
    a90_console_printf("umount <path>\r\n");
    a90_console_printf("echo <text>\r\n");
    a90_console_printf("writefile <path> <value...>\r\n");
    a90_console_printf("cpustress [sec] [workers]\r\n");
    a90_console_printf("run <path> [args...]\r\n");
    a90_console_printf("runandroid <path> [args...]\r\n");
    a90_console_printf("startadbd\r\n");
    a90_console_printf("stopadbd\r\n");
    a90_console_printf("netservice [status|start|stop|enable|disable]\r\n");
    a90_console_printf("rshell [status|audit|start|stop|enable|disable|token [show]|rotate-token [value]]\r\n");
    a90_console_printf("service [list|status|start|stop|enable|disable] [name]\r\n");
    a90_console_printf("reattach\r\n");
    a90_console_printf("usbacmreset\r\n");
    a90_console_printf("sync\r\n");
    a90_console_printf("reboot\r\n");
    a90_console_printf("recovery\r\n");
    a90_console_printf("poweroff\r\n");
}

static int cmd_uname(void) {
    struct utsname uts;

    if (uname(&uts) < 0) {
        a90_console_printf("uname: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    a90_console_printf("%s %s %s %s %s\r\n",
            uts.sysname, uts.nodename, uts.release, uts.version, uts.machine);
    return 0;
}

static void cmd_version(void) {
    struct utsname uts;
    struct a90_kms_info kms_info;

    a90_console_printf("%s\r\n", INIT_BANNER);
    a90_console_printf("%s\r\n", INIT_CREATOR);
    a90_console_printf("version: %s build=%s\r\n", INIT_VERSION, INIT_BUILD);
    if (uname(&uts) == 0) {
        a90_console_printf("kernel: %s %s %s\r\n", uts.sysname, uts.release, uts.machine);
    }
    a90_kms_info(&kms_info);
    if (kms_info.initialized) {
        a90_console_printf("display: %ux%u connector=%u crtc=%u fb=%u\r\n",
                kms_info.width,
                kms_info.height,
                kms_info.connector_id,
                kms_info.crtc_id,
                kms_info.fb_id);
    } else {
        a90_console_printf("display: not initialized\r\n");
    }
}

static void cmd_status(void) {
    struct a90_metrics_snapshot snapshot;
    char boot_summary[64];
    char selftest_summary[96];
    char pid1guard_summary[96];
    char helper_summary[128];
    char userland_summary[128];
    char exposure_summary[192];
    struct a90_runtime_status runtime_status;
    struct a90_kms_info kms_info;
    struct a90_exposure_snapshot exposure;

    a90_metrics_read_snapshot(&snapshot);
    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));
    a90_selftest_summary(selftest_summary, sizeof(selftest_summary));
    refresh_pid1_guard();
    a90_pid1_guard_summary(pid1guard_summary, sizeof(pid1guard_summary));
    a90_helper_summary(helper_summary, sizeof(helper_summary));
    a90_userland_summary(userland_summary, sizeof(userland_summary));
    a90_runtime_get_status(&runtime_status);
    (void)a90_exposure_collect(&exposure);
    a90_exposure_summary(&exposure, exposure_summary, sizeof(exposure_summary));

    a90_console_printf("init: %s\r\n", INIT_BANNER);
    a90_console_printf("creator: %s\r\n", INIT_CREATOR);
    a90_console_printf("boot: %s\r\n", boot_summary);
    a90_console_printf("selftest: %s\r\n", selftest_summary);
    a90_console_printf("pid1guard: %s\r\n", pid1guard_summary);
    a90_console_printf("helpers: %s\r\n", helper_summary);
    a90_console_printf("userland: %s\r\n", userland_summary);
    a90_console_printf("exposure: %s\r\n", exposure_summary);
    a90_console_printf("runtime: backend=%s root=%s fallback=%s writable=%s\r\n",
            runtime_status.backend,
            runtime_status.root,
            runtime_status.fallback ? "yes" : "no",
            runtime_status.writable ? "yes" : "no");
    a90_console_printf("uptime: %ss  load=%s\r\n", snapshot.uptime, snapshot.loadavg);
    a90_console_printf("battery: %s %s temp=%s voltage=%s\r\n",
            snapshot.battery_pct,
            snapshot.battery_status,
            snapshot.battery_temp,
            snapshot.battery_voltage);
    a90_console_printf("power: now=%s avg=%s\r\n", snapshot.power_now, snapshot.power_avg);
    a90_console_printf("thermal: cpu=%s %s gpu=%s %s\r\n",
            snapshot.cpu_temp,
            snapshot.cpu_usage,
            snapshot.gpu_temp,
            snapshot.gpu_usage);
    a90_console_printf("memory: %s used\r\n", snapshot.memory);
    a90_kms_info(&kms_info);
    if (kms_info.initialized) {
        a90_console_printf("display: %ux%u connector=%u crtc=%u current_buffer=%u\r\n",
                kms_info.width,
                kms_info.height,
                kms_info.connector_id,
                kms_info.crtc_id,
                kms_info.current_buffer);
    } else {
        a90_console_printf("display: not initialized\r\n");
    }
    (void)a90_service_reap(A90_SERVICE_ADBD, NULL);
    a90_console_printf("adbd: %s\r\n",
            a90_service_pid(A90_SERVICE_ADBD) > 0 ? "started" : "stopped");
    reap_hud_child();
    a90_console_printf("autohud: %s\r\n",
            a90_service_pid(A90_SERVICE_HUD) > 0 ? "running" : "stopped");
    {
        struct a90_netservice_status net_status;

        a90_netservice_status(&net_status);
        a90_console_printf("netservice: %s tcpctl=%s\r\n",
                net_status.enabled ? "enabled" : "disabled",
                net_status.tcpctl_running ? "running" : "stopped");
        (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
        a90_console_printf("rshell: %s pid=%ld port=%s\r\n",
                a90_service_pid(A90_SERVICE_RSHELL) > 0 ? "running" : "stopped",
                (long)a90_service_pid(A90_SERVICE_RSHELL),
                A90_RSHELL_PORT);
    }
    a90_storage_cmd_storage();
    a90_storage_cmd_mountsd((char *[]){ "mountsd", "status" }, 2);
}

static int cmd_cpustress(char **argv, int argc) {
    long seconds = 10;
    long workers_long = 4;
    char seconds_arg[16];
    char workers_arg[16];
    const char *helper_path = a90_helper_preferred_path("a90_cpustress", CPUSTRESS_HELPER);
    char *const child_argv[] = {
        (char *)helper_path,
        seconds_arg,
        workers_arg,
        NULL
    };
    struct a90_run_config config = {
        .tag = "cpustress",
        .argv = child_argv,
        .stdio_mode = A90_RUN_STDIO_CONSOLE,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = true,
        .stop_timeout_ms = 2000,
    };
    struct a90_run_result result;
    pid_t pid;
    int rc;

    if (argc > 1) {
        seconds = strtol(argv[1], NULL, 10);
    }
    if (argc > 2) {
        workers_long = strtol(argv[2], NULL, 10);
    }
    if (argc > 3 || seconds < 1 || seconds > 120 || workers_long < 1 || workers_long > 16) {
        a90_console_printf("usage: cpustress [sec 1-120] [workers 1-16]\r\n");
        return -EINVAL;
    }

    snprintf(seconds_arg, sizeof(seconds_arg), "%ld", seconds);
    snprintf(workers_arg, sizeof(workers_arg), "%ld", workers_long);
    config.timeout_ms = (int)(seconds * 1000L + 3000L);

    a90_console_printf("cpustress: helper=%s workers=%ld sec=%ld, q/Ctrl-C cancels\r\n",
            helper_path,
            workers_long,
            seconds);

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        int saved_errno = -rc;
        if (saved_errno <= 0) {
            saved_errno = EAGAIN;
        }
        a90_console_printf("cpustress: spawn helper: %s\r\n", strerror(saved_errno));
        return rc;
    }

    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        if (rc != -ECANCELED) {
            int saved_errno = -rc;
            if (saved_errno <= 0) {
                saved_errno = EIO;
            }
            a90_console_printf("cpustress: wait helper: %s\r\n", strerror(saved_errno));
        }
        return rc;
    }
    if (WIFEXITED(result.status)) {
        int exit_code = WEXITSTATUS(result.status);
        if (exit_code != 0) {
            a90_console_printf("cpustress: helper exit=%d\r\n", exit_code);
        }
        return exit_code;
    }
    if (WIFSIGNALED(result.status)) {
        int signal_num = WTERMSIG(result.status);
        a90_console_printf("cpustress: helper signal=%d\r\n", signal_num);
        return 128 + signal_num;
    }
    return -ECHILD;
}

static int cmd_ls(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int first_error = 0;

    dir = opendir(path);
    if (dir == NULL) {
        a90_console_printf("ls: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[PATH_MAX];
        struct stat st;
        char type = '?';

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        if (snprintf(full, sizeof(full), "%s/%s", path, entry->d_name) >= (int)sizeof(full)) {
            continue;
        }

        if (lstat(full, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                type = 'd';
            } else if (S_ISLNK(st.st_mode)) {
                type = 'l';
            } else if (S_ISCHR(st.st_mode)) {
                type = 'c';
            } else if (S_ISBLK(st.st_mode)) {
                type = 'b';
            } else if (S_ISREG(st.st_mode)) {
                type = '-';
            }
            a90_console_printf("%c %8ld %s\r\n", type, (long)st.st_size, entry->d_name);
        } else {
            a90_console_printf("? ???????? %s\r\n", entry->d_name);
            if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        }
    }

    closedir(dir);
    return first_error;
}

static int cmd_cat(const char *path) {
    char buf[512];
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        a90_console_printf("cat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while (1) {
        ssize_t rd = read(fd, buf, sizeof(buf));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("cat: %s: %s\r\n", path, strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
        if (rd == 0) {
            break;
        }
        a90_console_write(buf, (size_t)rd);
    }

    close(fd);
    a90_console_printf("\r\n");
    return 0;
}

static int cmd_logpath(void) {
    a90_console_printf("log: path=%s ready=%s max=%d\r\n",
            a90_log_path(),
            a90_log_ready() ? "yes" : "no",
            NATIVE_LOG_MAX_BYTES);
    return a90_log_ready() ? 0 : -EIO;
}

static int cmd_logcat(void) {
    if (!a90_log_ready()) {
        a90_console_printf("logcat: log is not ready\r\n");
        return -ENOENT;
    }
    return cmd_cat(a90_log_path());
}

static int cmd_exposure(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    struct a90_exposure_snapshot exposure;
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: exposure [status|verbose|guard]\r\n");
        return -EINVAL;
    }
    rc = a90_exposure_collect(&exposure);
    if (rc < 0) {
        a90_console_printf("exposure: collect failed rc=%d\r\n", rc);
        return rc;
    }
    if (strcmp(subcommand, "status") == 0) {
        a90_exposure_print(&exposure, false);
        return 0;
    }
    if (strcmp(subcommand, "verbose") == 0) {
        a90_exposure_print(&exposure, true);
        return 0;
    }
    if (strcmp(subcommand, "guard") == 0) {
        a90_exposure_print(&exposure, true);
        return a90_exposure_guardrail_ok(&exposure) ? 0 : -EIO;
    }
    a90_console_printf("usage: exposure [status|verbose|guard]\r\n");
    return -EINVAL;
}

static int cmd_hudlog(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: hudlog [status|on|off]\r\n");
        return -EINVAL;
    }
    if (strcmp(subcommand, "status") == 0) {
        a90_console_printf("hudlog: %s path=%s\r\n",
                a90_hud_log_tail_enabled() ? "on" : "off",
                HUD_LOG_TAIL_ENABLE_PATH);
        return 0;
    }
    if (strcmp(subcommand, "on") == 0 || strcmp(subcommand, "enable") == 0) {
        rc = a90_hud_set_log_tail_enabled(true);
        a90_console_printf("hudlog: %s\r\n", rc == 0 ? "on" : "enable failed");
        return rc;
    }
    if (strcmp(subcommand, "off") == 0 || strcmp(subcommand, "disable") == 0) {
        rc = a90_hud_set_log_tail_enabled(false);
        a90_console_printf("hudlog: %s\r\n", rc == 0 ? "off" : "disable failed");
        return rc;
    }

    a90_console_printf("usage: hudlog [status|on|off]\r\n");
    return -EINVAL;
}

static int cmd_timeline(void) {
    size_t count = a90_timeline_count();
    size_t index;

    a90_console_printf("timeline: count=%ld max=%d\r\n",
            (long)count,
            BOOT_TIMELINE_MAX);

    for (index = 0; index < count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct a90_timeline_entry *entry = a90_timeline_entry_at(index);

        if (entry == NULL) {
            continue;
        }

        a90_console_printf("%02ld %8ldms %-18s rc=%d errno=%d %s\r\n",
                (long)index,
                entry->ms,
                entry->step,
                entry->code,
                entry->saved_errno,
                entry->detail);
    }

    return count > 0 ? 0 : -ENOENT;
}

static int cmd_bootstatus(void) {
    char summary[64];
    char selftest_summary[96];
    char pid1guard_summary[96];
    char helper_summary[128];
    char userland_summary[128];
    char exposure_summary[192];
    struct a90_runtime_status runtime_status;
    struct a90_exposure_snapshot exposure;
    size_t count = a90_timeline_count();

    a90_timeline_boot_summary(summary, sizeof(summary));
    a90_selftest_summary(selftest_summary, sizeof(selftest_summary));
    refresh_pid1_guard();
    a90_pid1_guard_summary(pid1guard_summary, sizeof(pid1guard_summary));
    a90_helper_summary(helper_summary, sizeof(helper_summary));
    a90_userland_summary(userland_summary, sizeof(userland_summary));
    a90_runtime_get_status(&runtime_status);
    (void)a90_exposure_collect(&exposure);
    a90_exposure_summary(&exposure, exposure_summary, sizeof(exposure_summary));
    a90_console_printf("boot: %s\r\n", summary);
    a90_console_printf("selftest: %s\r\n", selftest_summary);
    a90_console_printf("pid1guard: %s\r\n", pid1guard_summary);
    a90_console_printf("helpers: %s\r\n", helper_summary);
    a90_console_printf("userland: %s\r\n", userland_summary);
    a90_console_printf("exposure: %s\r\n", exposure_summary);
    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    a90_console_printf("rshell: %s pid=%ld port=%s\r\n",
            a90_service_pid(A90_SERVICE_RSHELL) > 0 ? "running" : "stopped",
            (long)a90_service_pid(A90_SERVICE_RSHELL),
            A90_RSHELL_PORT);
    a90_console_printf("runtime: backend=%s root=%s fallback=%s writable=%s\r\n",
            runtime_status.backend,
            runtime_status.root,
            runtime_status.fallback ? "yes" : "no",
            runtime_status.writable ? "yes" : "no");
    a90_console_printf("timeline_entries: %ld/%d\r\n",
            (long)count,
            BOOT_TIMELINE_MAX);
    return count > 0 ? 0 : -ENOENT;
}

static int cmd_selftest(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    bool verbose = false;
    char summary[96];
    size_t count;
    size_t index;

    if (argc > 2) {
        a90_console_printf("usage: selftest [status|run|verbose]\r\n");
        return -EINVAL;
    }

    if (strcmp(subcommand, "run") == 0) {
        (void)a90_selftest_run_manual();
        verbose = true;
    } else if (strcmp(subcommand, "verbose") == 0) {
        verbose = true;
    } else if (strcmp(subcommand, "status") != 0) {
        a90_console_printf("usage: selftest [status|run|verbose]\r\n");
        return -EINVAL;
    }

    a90_selftest_summary(summary, sizeof(summary));
    count = a90_selftest_count();
    a90_console_printf("selftest: %s entries=%ld\r\n", summary, (long)count);

    if (verbose) {
        for (index = 0; index < count; ++index) {
            const struct a90_selftest_entry *entry = a90_selftest_entry_at(index);

            if (entry == NULL) {
                continue;
            }
            a90_console_printf("%02ld %-9s %-8s rc=%d errno=%d %ldms %s\r\n",
                    (long)index,
                    a90_selftest_result_name(entry->result),
                    entry->name,
                    entry->code,
                    entry->saved_errno,
                    entry->duration_ms,
                    entry->detail);
        }
    }

    if (count == 0) {
        return -ENOENT;
    }
    return a90_selftest_has_failures() ? -EIO : 0;
}

static int cmd_pid1guard(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    bool verbose = false;
    char summary[96];
    size_t count;
    size_t index;

    if (argc > 2) {
        a90_console_printf("usage: pid1guard [status|run|verbose]\r\n");
        return -EINVAL;
    }

    if (strcmp(subcommand, "run") == 0) {
        refresh_pid1_guard();
        verbose = true;
    } else if (strcmp(subcommand, "verbose") == 0) {
        refresh_pid1_guard();
        verbose = true;
    } else if (strcmp(subcommand, "status") == 0) {
        refresh_pid1_guard();
    } else {
        a90_console_printf("usage: pid1guard [status|run|verbose]\r\n");
        return -EINVAL;
    }

    a90_pid1_guard_summary(summary, sizeof(summary));
    count = a90_pid1_guard_count();
    a90_console_printf("pid1guard: %s entries=%ld\r\n", summary, (long)count);

    if (verbose) {
        for (index = 0; index < count; ++index) {
            const struct a90_pid1_guard_entry *entry = a90_pid1_guard_entry_at(index);

            if (entry == NULL) {
                continue;
            }
            a90_console_printf("%02ld %-5s %-10s rc=%d errno=%d %s\r\n",
                    (long)index,
                    a90_pid1_guard_result_name(entry->result),
                    entry->name,
                    entry->code,
                    entry->saved_errno,
                    entry->detail);
        }
    }

    if (count == 0) {
        return -ENOENT;
    }
    return a90_pid1_guard_has_failures() ? -EIO : 0;
}

static int cmd_stat(const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        a90_console_printf("stat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("mode=0%o uid=%ld gid=%ld size=%ld\r\n",
            st.st_mode & 07777, (long)st.st_uid, (long)st.st_gid, (long)st.st_size);
    if (S_ISBLK(st.st_mode) || S_ISCHR(st.st_mode)) {
        a90_console_printf("rdev=%u:%u\r\n", major(st.st_rdev), minor(st.st_rdev));
    }
    return 0;
}

static int cmd_mounts(void) {
    return cmd_cat("/proc/mounts");
}

static int cmd_mountsystem(bool read_only) {
    unsigned long flags = read_only ? MS_RDONLY : 0;
    char node_path[PATH_MAX];

    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (get_block_device_path("sda28", node_path, sizeof(node_path)) < 0) {
        a90_console_printf("mountsystem: mknod failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    if (mount(node_path, "/mnt/system", "ext4", flags, NULL) < 0) {
        if (errno == EBUSY) {
            a90_console_printf("mountsystem: already mounted\r\n");
            return 0;
        } else {
            a90_console_printf("mountsystem: %s\r\n", strerror(errno));
        }
        return negative_errno_or(EIO);
    }

    a90_console_printf("mountsystem: /mnt/system ready (%s)\r\n", read_only ? "ro" : "rw");
    return 0;
}
