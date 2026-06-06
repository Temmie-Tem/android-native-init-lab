/* Included by stage3/linux_init/init_v117.c. Do not compile standalone. */

static void print_shell_intro(void) {
    a90_console_printf("# Type 'help' for commands. Serial input was flushed at attach.\r\n");
}

static int handle_help(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_help();
    return 0;
}

static int handle_cmdv1(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_console_printf("usage: cmdv1 <command> [args...]\r\n");
    a90_console_printf("cmdv1: emits A90P1 BEGIN/END records around one command\r\n");
    return -EINVAL;
}

static int handle_cmdv1x(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_console_printf("usage: cmdv1x <len:hex-utf8-arg>...\r\n");
    a90_console_printf("cmdv1x: cmdv1 with length-prefixed hex argv tokens\r\n");
    return -EINVAL;
}

static int handle_version(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_version();
    return 0;
}

static int handle_status(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_status();
    return 0;
}

static int handle_last(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_shell_print_last_result();
    return 0;
}

static int handle_logpath(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_logpath();
}

static int handle_logcat(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_logcat();
}

static int handle_timeline(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_timeline();
}

static int handle_bootstatus(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_bootstatus();
}

static int handle_selftest(char **argv, int argc) {
    return cmd_selftest(argv, argc);
}

static int handle_uname(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_uname();
}

static int handle_pwd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_pwd();
}

static int handle_cd(char **argv, int argc) {
    const char *path = argc > 1 ? argv[1] : "/";

    if (chdir(path) < 0) {
        int saved_errno = errno;
        a90_console_printf("cd: %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }

    return 0;
}

static int handle_ls(char **argv, int argc) {
    return cmd_ls(argc > 1 ? argv[1] : ".");
}

static int handle_cat(char **argv, int argc) {
    if (argc < 2) {
        a90_console_printf("usage: cat <file>\r\n");
        return -EINVAL;
    }
    return cmd_cat(argv[1]);
}

static int handle_stat(char **argv, int argc) {
    if (argc < 2) {
        a90_console_printf("usage: stat <path>\r\n");
        return -EINVAL;
    }
    return cmd_stat(argv[1]);
}

static int handle_mounts(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_mounts();
}

static int handle_mountsystem(char **argv, int argc) {
    bool read_only = true;

    if (argc > 1 && strcmp(argv[1], "rw") == 0) {
        read_only = false;
    } else if (argc > 1 && strcmp(argv[1], "ro") != 0) {
        a90_console_printf("usage: mountsystem [ro|rw]\r\n");
        return -EINVAL;
    }
    return cmd_mountsystem(read_only);
}

static int handle_mountsd(char **argv, int argc) {
    return a90_storage_cmd_mountsd(argv, argc);
}

static int handle_storage(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return a90_storage_cmd_storage();
}

static int handle_runtime(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return a90_runtime_cmd_runtime();
}

static int handle_helpers(char **argv, int argc) {
    return a90_helper_cmd_helpers(argv, argc);
}

static int handle_userland(char **argv, int argc) {
    return cmd_userland(argv, argc);
}

static int handle_busybox(char **argv, int argc) {
    return cmd_busybox(argv, argc);
}

static int handle_toybox(char **argv, int argc) {
    return cmd_toybox(argv, argc);
}

static int handle_prepareandroid(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_prepareandroid();
}

static int handle_inputinfo(char **argv, int argc) {
    return cmd_inputinfo(argv, argc);
}

static int handle_drminfo(char **argv, int argc) {
    return cmd_drminfo(argv, argc);
}

static int handle_fbinfo(char **argv, int argc) {
    return cmd_fbinfo(argv, argc);
}

static int handle_kmsprobe(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_kmsprobe();
}

static int handle_kmssolid(char **argv, int argc) {
    return cmd_kmssolid(argv, argc);
}

static int handle_kmsframe(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_kmsframe();
}

static int handle_statusscreen(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_statusscreen();
}

static int handle_statushud(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_statushud();
}

static int handle_displaytest(char **argv, int argc) {
    unsigned int page = 0;

    if (argc >= 2) {
        if (strcmp(argv[1], "colors") == 0 || strcmp(argv[1], "color") == 0) {
            page = 0;
        } else if (strcmp(argv[1], "font") == 0 || strcmp(argv[1], "wrap") == 0) {
            page = 1;
        } else if (strcmp(argv[1], "safe") == 0 || strcmp(argv[1], "grid") == 0) {
            page = 2;
        } else if (strcmp(argv[1], "layout") == 0 || strcmp(argv[1], "hud") == 0) {
            page = 3;
        } else if (sscanf(argv[1], "%u", &page) != 1 ||
                   page >= DISPLAY_TEST_PAGE_COUNT) {
            a90_console_printf("usage: displaytest [0-3|colors|font|safe|layout]\r\n");
            return -EINVAL;
        }
    }

    a90_console_printf("displaytest: drawing page %u/%u %s\r\n",
            page + 1,
            DISPLAY_TEST_PAGE_COUNT,
            a90_app_displaytest_page_title(page));
    return draw_screen_display_test_page(page);
}

static int handle_cutoutcal(char **argv, int argc) {
    struct cutout_calibration_state cal;

    cutout_calibration_init(&cal);
    if (argc == 4) {
        if (sscanf(argv[1], "%d", &cal.center_x) != 1 ||
            sscanf(argv[2], "%d", &cal.center_y) != 1 ||
            sscanf(argv[3], "%d", &cal.size) != 1) {
            a90_console_printf("usage: cutoutcal [x y size]\r\n");
            return -EINVAL;
        }
    } else if (argc != 1) {
        a90_console_printf("usage: cutoutcal [x y size]\r\n");
        return -EINVAL;
    }
    cutout_calibration_clamp(&cal);
    a90_console_printf("cutoutcal: x=%d y=%d size=%d\r\n",
            cal.center_x,
            cal.center_y,
            cal.size);
    return draw_screen_cutout_calibration(&cal, false);
}

static int handle_watchhud(char **argv, int argc) {
    return cmd_watchhud(argv, argc);
}

static int handle_autohud(char **argv, int argc) {
    return cmd_autohud(argv, argc);
}

static int handle_stophud(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_stophud();
}

static int handle_clear(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_clear_display();
}

static int handle_inputcaps(char **argv, int argc) {
    return cmd_inputcaps(argv, argc);
}

static int handle_readinput(char **argv, int argc) {
    return cmd_readinput(argv, argc);
}

static int handle_waitkey(char **argv, int argc) {
    return cmd_waitkey(argv, argc);
}

static int handle_inputlayout(char **argv, int argc) {
    return cmd_inputlayout(argv, argc);
}

static int handle_waitgesture(char **argv, int argc) {
    return cmd_waitgesture(argv, argc);
}

static int handle_inputmonitor(char **argv, int argc) {
    return cmd_inputmonitor(argv, argc);
}

static int handle_blindmenu(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_blindmenu();
}

static int handle_screenmenu(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_screenmenu();
}

static int handle_hide_menu(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_hide_menu();
}

static int handle_mkdir(char **argv, int argc) {
    if (argc < 2) {
        a90_console_printf("usage: mkdir <dir>\r\n");
        return -EINVAL;
    }
    if (mkdir(argv[1], 0755) < 0 && errno != EEXIST) {
        int saved_errno = errno;
        a90_console_printf("mkdir: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mknodc(char **argv, int argc) {
    unsigned int major_num;
    unsigned int minor_num;

    if (argc < 4) {
        a90_console_printf("usage: mknodc <path> <major> <minor>\r\n");
        return -EINVAL;
    }
    if (sscanf(argv[2], "%u", &major_num) != 1 ||
        sscanf(argv[3], "%u", &minor_num) != 1) {
        a90_console_printf("mknodc: invalid major/minor\r\n");
        return -EINVAL;
    }
    if (ensure_char_node(argv[1], major_num, minor_num) < 0) {
        int saved_errno = errno;
        a90_console_printf("mknodc: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mknodb(char **argv, int argc) {
    unsigned int major_num;
    unsigned int minor_num;

    if (argc < 4) {
        a90_console_printf("usage: mknodb <path> <major> <minor>\r\n");
        return -EINVAL;
    }
    if (sscanf(argv[2], "%u", &major_num) != 1 ||
        sscanf(argv[3], "%u", &minor_num) != 1) {
        a90_console_printf("mknodb: invalid major/minor\r\n");
        return -EINVAL;
    }
    if (mknod(argv[1], S_IFBLK | 0600,
              makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        int saved_errno = errno;
        a90_console_printf("mknodb: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mountfs(char **argv, int argc) {
    unsigned long flags = 0;

    if (argc < 4) {
        a90_console_printf("usage: mountfs <src> <dst> <type> [ro]\r\n");
        return -EINVAL;
    }
    if (argc > 4 && strcmp(argv[4], "ro") == 0) {
        flags |= MS_RDONLY;
    } else if (argc > 4) {
        a90_console_printf("usage: mountfs <src> <dst> <type> [ro]\r\n");
        return -EINVAL;
    }
    if (mount(argv[1], argv[2], argv[3], flags, NULL) < 0) {
        int saved_errno = errno;
        a90_console_printf("mountfs: %s\r\n", strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_umount(char **argv, int argc) {
    if (argc < 2) {
        a90_console_printf("usage: umount <path>\r\n");
        return -EINVAL;
    }
    if (umount(argv[1]) < 0) {
        int saved_errno = errno;
        a90_console_printf("umount: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_echo(char **argv, int argc) {
    cmd_echo(argv, argc);
    return 0;
}

static int handle_writefile(char **argv, int argc) {
    return cmd_writefile(argv, argc);
}

static int handle_cpustress(char **argv, int argc) {
    return cmd_cpustress(argv, argc);
}

static int handle_run(char **argv, int argc) {
    return cmd_run(argv, argc);
}

static int handle_runandroid(char **argv, int argc) {
    return cmd_runandroid(argv, argc);
}

static int handle_startadbd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_startadbd();
}

static int handle_stopadbd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_stopadbd();
}

static int handle_netservice(char **argv, int argc) {
    return cmd_netservice(argv, argc);
}

static int handle_rshell(char **argv, int argc) {
    return cmd_rshell(argv, argc);
}

static void service_sync_enabled_states(void) {
    a90_service_set_enabled_state(A90_SERVICE_HUD, false);
    a90_service_set_enabled_state(A90_SERVICE_ADBD, false);
    a90_service_set_enabled_state(A90_SERVICE_TCPCTL, a90_netservice_enabled());
    a90_service_set_enabled_state(A90_SERVICE_RSHELL, rshell_enabled());
}

static void service_flags_to_text(unsigned int flags, char *out, size_t out_size) {
    size_t used = 0;

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
#define A90_APPEND_SERVICE_FLAG(flag_value, label) do { \
        if ((flags & (flag_value)) != 0) { \
            int written = snprintf(out + used, \
                                   used < out_size ? out_size - used : 0, \
                                   "%s%s", \
                                   used > 0 ? "," : "", \
                                   (label)); \
            if (written > 0) { \
                used += (size_t)written; \
                if (used >= out_size) { \
                    used = out_size - 1; \
                } \
            } \
        } \
    } while (0)
    A90_APPEND_SERVICE_FLAG(A90_SERVICE_FLAG_BOOT_OPTIONAL, "boot-optional");
    A90_APPEND_SERVICE_FLAG(A90_SERVICE_FLAG_RAW_CONTROL, "raw-control");
    A90_APPEND_SERVICE_FLAG(A90_SERVICE_FLAG_REQUIRES_NCM, "requires-ncm");
    A90_APPEND_SERVICE_FLAG(A90_SERVICE_FLAG_DANGEROUS, "dangerous");
#undef A90_APPEND_SERVICE_FLAG
    if (out[0] == '\0') {
        snprintf(out, out_size, "none");
    }
}

static int service_resolve_name(const char *name, enum a90_service_id *out) {
    int rc = a90_service_id_from_name(name, out);

    if (rc < 0) {
        a90_console_printf("service: unknown service: %s\r\n",
                name != NULL ? name : "-");
    }
    return rc;
}

static int service_print_one(enum a90_service_id service) {
    struct a90_service_info info;
    char flags[96];
    int rc;

    (void)a90_service_reap(service, NULL);
    service_sync_enabled_states();
    rc = a90_service_info(service, &info);
    if (rc < 0) {
        return rc;
    }
    service_flags_to_text(info.flags, flags, sizeof(flags));
    a90_console_printf("service: %s kind=%s running=%s pid=%ld enabled=%s flags=%s\r\n",
            info.name,
            a90_service_kind_name(info.kind),
            info.running ? "yes" : "no",
            (long)info.pid,
            info.enabled ? "yes" : "no",
            flags);
    a90_console_printf("service: %s desc=%s", info.name, info.description);
    if (info.enable_path != NULL) {
        a90_console_printf(" enable=%s", info.enable_path);
    }
    a90_console_printf("\r\n");
    if (service == A90_SERVICE_TCPCTL) {
        struct a90_netservice_status status;

        a90_netservice_status(&status);
        a90_console_printf("service: tcpctl ncm=%s ip=%s port=%s flag=%s\r\n",
                status.ncm_present ? "present" : "absent",
                status.device_ip,
                status.tcp_port,
                status.flag_path);
    } else if (service == A90_SERVICE_RSHELL) {
        a90_console_printf("service: rshell bind=%s port=%s idle=%ss\r\n",
                A90_RSHELL_BIND_ADDR,
                A90_RSHELL_PORT,
                A90_RSHELL_IDLE_SECONDS);
    }
    return 0;
}

static int service_print_list(void) {
    int index;
    int rc = 0;

    a90_service_reap_all();
    service_sync_enabled_states();
    for (index = 0; index < a90_service_count(); ++index) {
        enum a90_service_id service = a90_service_id_at(index);
        int one_rc = service_print_one(service);

        if (one_rc < 0 && rc == 0) {
            rc = one_rc;
        }
    }
    return rc;
}

static int service_start_one(enum a90_service_id service) {
    switch (service) {
    case A90_SERVICE_HUD:
        return start_auto_hud(BOOT_HUD_REFRESH_SECONDS, true);
    case A90_SERVICE_TCPCTL:
        return a90_netservice_start();
    case A90_SERVICE_ADBD:
        return cmd_startadbd();
    case A90_SERVICE_RSHELL:
        return rshell_start_service(true);
    default:
        return -EINVAL;
    }
}

static int service_stop_one(enum a90_service_id service) {
    switch (service) {
    case A90_SERVICE_HUD:
        return cmd_stophud();
    case A90_SERVICE_TCPCTL:
        return a90_netservice_stop();
    case A90_SERVICE_ADBD:
        return cmd_stopadbd();
    case A90_SERVICE_RSHELL:
        return rshell_stop_service();
    default:
        return -EINVAL;
    }
}

static int service_enable_one(enum a90_service_id service) {
    int rc;

    switch (service) {
    case A90_SERVICE_TCPCTL:
        rc = a90_netservice_set_enabled(true);
        if (rc < 0) {
            return rc;
        }
        return a90_netservice_start();
    case A90_SERVICE_RSHELL:
        rc = rshell_set_enabled(true);
        if (rc < 0) {
            return rc;
        }
        return rshell_start_service(true);
    default:
        a90_console_printf("service: enable unsupported for %s\r\n",
                a90_service_name(service));
        return -EOPNOTSUPP;
    }
}

static int service_disable_one(enum a90_service_id service) {
    int flag_rc;
    int stop_rc;

    switch (service) {
    case A90_SERVICE_TCPCTL:
        flag_rc = a90_netservice_set_enabled(false);
        stop_rc = a90_netservice_stop();
        return flag_rc < 0 ? flag_rc : stop_rc;
    case A90_SERVICE_RSHELL:
        flag_rc = rshell_set_enabled(false);
        stop_rc = rshell_stop_service();
        return flag_rc < 0 ? flag_rc : stop_rc;
    default:
        a90_console_printf("service: disable unsupported for %s\r\n",
                a90_service_name(service));
        return -EOPNOTSUPP;
    }
}

static int cmd_service(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "list";
    enum a90_service_id service;
    int rc;

    if (strcmp(subcommand, "list") == 0) {
        if (argc != 2 && argc != 1) {
            a90_console_printf("usage: service list\r\n");
            return -EINVAL;
        }
        return service_print_list();
    }
    if (strcmp(subcommand, "status") == 0) {
        if (argc == 2) {
            return service_print_list();
        }
        if (argc != 3) {
            a90_console_printf("usage: service status [name]\r\n");
            return -EINVAL;
        }
        rc = service_resolve_name(argv[2], &service);
        if (rc < 0) {
            return rc;
        }
        return service_print_one(service);
    }
    if (strcmp(subcommand, "start") == 0 ||
        strcmp(subcommand, "stop") == 0 ||
        strcmp(subcommand, "enable") == 0 ||
        strcmp(subcommand, "disable") == 0) {
        if (argc != 3) {
            a90_console_printf("usage: service %s <name>\r\n", subcommand);
            return -EINVAL;
        }
        rc = service_resolve_name(argv[2], &service);
        if (rc < 0) {
            return rc;
        }
        if (strcmp(subcommand, "start") == 0) {
            return service_start_one(service);
        }
        if (strcmp(subcommand, "stop") == 0) {
            return service_stop_one(service);
        }
        if (strcmp(subcommand, "enable") == 0) {
            return service_enable_one(service);
        }
        return service_disable_one(service);
    }

    a90_console_printf("usage: service [list|status|start|stop|enable|disable] [name]\r\n");
    return -EINVAL;
}

static int handle_service(char **argv, int argc) {
    return cmd_service(argv, argc);
}

static int handle_diag(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "summary";
    char path[PATH_MAX];
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: diag [summary|full|bundle|paths]\r\n");
        return -EINVAL;
    }

    service_sync_enabled_states();

    if (strcmp(subcommand, "summary") == 0) {
        return a90_diag_print_summary();
    }
    if (strcmp(subcommand, "full") == 0) {
        return a90_diag_print_full();
    }
    if (strcmp(subcommand, "paths") == 0) {
        a90_console_printf("diag: default_dir=%s\r\n", a90_diag_default_dir());
        a90_console_printf("diag: log_path=%s ready=%s\r\n",
                a90_log_path(),
                a90_log_ready() ? "yes" : "no");
        return 0;
    }
    if (strcmp(subcommand, "bundle") == 0) {
        rc = a90_diag_write_bundle(path, sizeof(path));
        if (rc < 0) {
            a90_console_printf("diag: bundle failed path=%s rc=%d\r\n", path, rc);
            return rc;
        }
        a90_console_printf("diag: bundle=%s\r\n", path);
        return 0;
    }

    a90_console_printf("usage: diag [summary|full|bundle|paths]\r\n");
    return -EINVAL;
}

static int handle_wifiinv(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: wifiinv [summary|full|paths]\r\n");
        return -EINVAL;
    }

    if (strcmp(subcommand, "summary") == 0) {
        return a90_wifiinv_print_summary();
    }
    if (strcmp(subcommand, "full") == 0) {
        return a90_wifiinv_print_full();
    }
    if (strcmp(subcommand, "paths") == 0) {
        return a90_wifiinv_print_paths();
    }

    a90_console_printf("usage: wifiinv [summary|full|paths]\r\n");
    return -EINVAL;
}

static int handle_wififeas(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: wififeas [summary|full|gate|paths]\r\n");
        return -EINVAL;
    }

    if (strcmp(subcommand, "summary") == 0) {
        return a90_wififeas_print_summary();
    }
    if (strcmp(subcommand, "full") == 0) {
        return a90_wififeas_print_full();
    }
    if (strcmp(subcommand, "gate") == 0) {
        return a90_wififeas_print_gate();
    }
    if (strcmp(subcommand, "paths") == 0) {
        return a90_wififeas_print_paths();
    }

    a90_console_printf("usage: wififeas [summary|full|gate|paths]\r\n");
    return -EINVAL;
}

static int handle_reattach(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_reattach();
}

static int handle_usbacmreset(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_usbacmreset();
}

static int handle_sync(char **argv, int argc) {
    (void)argv;
    (void)argc;
    sync();
    a90_console_printf("synced\r\n");
    return 0;
}

static int handle_reboot(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_console_printf("reboot: syncing and restarting\r\n");
    stop_auto_hud(false);
    sync();
    reboot(RB_AUTOBOOT);
    wf("/proc/sysrq-trigger", "b");
    return negative_errno_or(EIO);
}

static int handle_recovery(char **argv, int argc) {
    (void)argv;
    (void)argc;
    stop_auto_hud(false);
    return cmd_recovery();
}

static int handle_poweroff(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_console_printf("poweroff: syncing and powering off\r\n");
    stop_auto_hud(false);
    sync();
    reboot(RB_POWER_OFF);
    return negative_errno_or(EIO);
}

static const struct shell_command command_table[] = {
    { "help", handle_help, "help", CMD_NONE },
    { "cmdv1", handle_cmdv1, "cmdv1 <command> [args...]", CMD_NONE },
    { "cmdv1x", handle_cmdv1x, "cmdv1x <len:hex-utf8-arg>...", CMD_NONE },
    { "version", handle_version, "version", CMD_NONE },
    { "status", handle_status, "status", CMD_NONE },
    { "last", handle_last, "last", CMD_NONE },
    { "logpath", handle_logpath, "logpath", CMD_NONE },
    { "logcat", handle_logcat, "logcat", CMD_NONE },
    { "diag", handle_diag, "diag [summary|full|bundle|paths]", CMD_NONE },
    { "wifiinv", handle_wifiinv, "wifiinv [summary|full|paths]", CMD_NONE },
    { "wififeas", handle_wififeas, "wififeas [summary|full|gate|paths]", CMD_NONE },
    { "timeline", handle_timeline, "timeline", CMD_NONE },
    { "bootstatus", handle_bootstatus, "bootstatus", CMD_NONE },
    { "selftest", handle_selftest, "selftest [status|run|verbose]", CMD_NONE },
    { "uname", handle_uname, "uname", CMD_NONE },
    { "pwd", handle_pwd, "pwd", CMD_NONE },
    { "cd", handle_cd, "cd <dir>", CMD_NONE },
    { "ls", handle_ls, "ls [dir]", CMD_NONE },
    { "cat", handle_cat, "cat <file>", CMD_NONE },
    { "stat", handle_stat, "stat <path>", CMD_NONE },
    { "mounts", handle_mounts, "mounts", CMD_NONE },
    { "mountsystem", handle_mountsystem, "mountsystem [ro|rw]", CMD_NONE },
    { "mountsd", handle_mountsd, "mountsd [status|ro|rw|off|init]", CMD_NONE },
    { "storage", handle_storage, "storage", CMD_NONE },
    { "runtime", handle_runtime, "runtime", CMD_NONE },
    { "helpers", handle_helpers, "helpers [status|verbose|manifest|plan|path <name>|verify [name]]", CMD_NONE },
    { "userland", handle_userland, "userland [status|verbose|test [busybox|toybox|all]]", CMD_BLOCKING },
    { "busybox", handle_busybox, "busybox <applet> [args...]", CMD_BLOCKING },
    { "toybox", handle_toybox, "toybox <applet> [args...]", CMD_BLOCKING },
    { "prepareandroid", handle_prepareandroid, "prepareandroid", CMD_NONE },
    { "inputinfo", handle_inputinfo, "inputinfo [eventX]", CMD_NONE },
    { "drminfo", handle_drminfo, "drminfo [entry]", CMD_NONE },
    { "fbinfo", handle_fbinfo, "fbinfo [fbX]", CMD_NONE },
    { "kmsprobe", handle_kmsprobe, "kmsprobe", CMD_NONE },
    { "kmssolid", handle_kmssolid, "kmssolid [color]", CMD_DISPLAY },
    { "kmsframe", handle_kmsframe, "kmsframe", CMD_DISPLAY },
    { "statusscreen", handle_statusscreen, "statusscreen", CMD_DISPLAY },
    { "statushud", handle_statushud, "statushud", CMD_DISPLAY },
    { "redraw", handle_statushud, "redraw", CMD_DISPLAY },
    { "testpattern", handle_statusscreen, "testpattern", CMD_DISPLAY },
    { "displaytest", handle_displaytest, "displaytest [0-3|colors|font|safe|layout]", CMD_DISPLAY },
    { "cutoutcal", handle_cutoutcal, "cutoutcal [x y size]", CMD_DISPLAY },
    { "watchhud", handle_watchhud, "watchhud [sec] [count]", CMD_DISPLAY | CMD_BLOCKING },
    { "autohud", handle_autohud, "autohud [sec]", CMD_BACKGROUND },
    { "stophud", handle_stophud, "stophud", CMD_BACKGROUND },
    { "clear", handle_clear, "clear", CMD_DISPLAY },
    { "inputcaps", handle_inputcaps, "inputcaps <eventX>", CMD_NONE },
    { "readinput", handle_readinput, "readinput <eventX> [count]", CMD_BLOCKING },
    { "waitkey", handle_waitkey, "waitkey [count]", CMD_BLOCKING },
    { "inputlayout", handle_inputlayout, "inputlayout", CMD_NONE },
    { "waitgesture", handle_waitgesture, "waitgesture [count]", CMD_BLOCKING },
    { "inputmonitor", handle_inputmonitor, "inputmonitor [events]", CMD_DISPLAY | CMD_BLOCKING },
    { "screenmenu", handle_screenmenu, "screenmenu", CMD_BACKGROUND },
    { "menu", handle_screenmenu, "menu", CMD_BACKGROUND },
    { "hide", handle_hide_menu, "hide", CMD_BACKGROUND },
    { "hidemenu", handle_hide_menu, "hidemenu", CMD_BACKGROUND },
    { "resume", handle_hide_menu, "resume", CMD_BACKGROUND },
    { "blindmenu", handle_blindmenu, "blindmenu", CMD_BLOCKING | CMD_DANGEROUS },
    { "mkdir", handle_mkdir, "mkdir <dir>", CMD_NONE },
    { "mknodc", handle_mknodc, "mknodc <path> <major> <minor>", CMD_NONE },
    { "mknodb", handle_mknodb, "mknodb <path> <major> <minor>", CMD_NONE },
    { "mountfs", handle_mountfs, "mountfs <src> <dst> <type> [ro]", CMD_NONE },
    { "umount", handle_umount, "umount <path>", CMD_NONE },
    { "echo", handle_echo, "echo <text>", CMD_NONE },
    { "writefile", handle_writefile, "writefile <path> <value...>", CMD_NONE },
    { "cpustress", handle_cpustress, "cpustress [sec] [workers]", CMD_BLOCKING },
    { "run", handle_run, "run <path> [args...]", CMD_BLOCKING },
    { "runandroid", handle_runandroid, "runandroid <path> [args...]", CMD_BLOCKING },
    { "startadbd", handle_startadbd, "startadbd", CMD_BACKGROUND },
    { "stopadbd", handle_stopadbd, "stopadbd", CMD_BACKGROUND },
    { "netservice", handle_netservice, "netservice [status|start|stop|enable|disable]", CMD_DANGEROUS },
    { "rshell", handle_rshell, "rshell [status|audit|start|stop|enable|disable|token [show]|rotate-token [value]]", CMD_DANGEROUS },
    { "service", handle_service, "service [list|status|start|stop|enable|disable] [name]", CMD_NONE },
    { "reattach", handle_reattach, "reattach", CMD_NONE },
    { "usbacmreset", handle_usbacmreset, "usbacmreset", CMD_DANGEROUS },
    { "sync", handle_sync, "sync", CMD_NONE },
    { "reboot", handle_reboot, "reboot", CMD_DANGEROUS | CMD_NO_DONE },
    { "recovery", handle_recovery, "recovery", CMD_DANGEROUS | CMD_NO_DONE },
    { "poweroff", handle_poweroff, "poweroff", CMD_DANGEROUS | CMD_NO_DONE },
};

static void print_cmdv1x_error(int result) {
    int result_errno = -result;
    unsigned long protocol_seq = a90_shell_next_protocol_seq();

    if (result_errno <= 0) {
        result_errno = EINVAL;
        result = -EINVAL;
    }

    a90_cmdproto_begin(protocol_seq, "cmdv1x", 1, CMD_NONE);
    a90_console_printf("[err] cmdv1x decode rc=%d errno=%d (%s)\r\n",
            result,
            result_errno,
            strerror(result_errno));
    a90_shell_save_last_result("cmdv1x", result, result_errno, 0, CMD_NONE);
    a90_logf("cmd", "cmdv1x decode failed rc=%d errno=%d",
                result, result_errno);
    a90_cmdproto_end(protocol_seq,
                     "cmdv1x",
                     result,
                     result_errno,
                     0,
                     CMD_NONE,
                     "error");
}

static int execute_shell_command(char **argv, int argc, bool protocol_v1) {
    const struct shell_command *command;
    enum a90_controller_busy_reason busy_reason;
    unsigned long protocol_seq = 0;
    long started_ms;
    long duration_ms;
    int result;
    int result_errno;

    if (argc == 0) {
        return 0;
    }

    command = a90_shell_find_command(command_table,
                                     sizeof(command_table) / sizeof(command_table[0]),
                                     argv[0]);
    if (command == NULL) {
        result = -ENOENT;
        result_errno = ENOENT;
        if (protocol_v1) {
            protocol_seq = a90_shell_next_protocol_seq();
            a90_cmdproto_begin(protocol_seq, argv[0], argc, CMD_NONE);
        }
        a90_console_printf("[err] unknown command: %s\r\n", argv[0]);
        a90_shell_save_last_result(argv[0], result, result_errno, 0, CMD_NONE);
        a90_logf("cmd", "unknown name=%s rc=%d errno=%d",
                    argv[0], result, result_errno);
        if (protocol_v1) {
            a90_cmdproto_end(protocol_seq,
                             argv[0],
                             result,
                             result_errno,
                             0,
                             CMD_NONE,
                             a90_cmdproto_status(result, true, false));
        }
        return result;
    }

    busy_reason = a90_controller_command_busy_reason(argv[0],
                                                     command->flags,
                                                     a90_controller_menu_is_active(),
                                                     a90_controller_menu_power_is_active());
    if (busy_reason != A90_CONTROLLER_BUSY_NONE) {
        result = -EBUSY;
        result_errno = EBUSY;
        if (protocol_v1) {
            protocol_seq = a90_shell_next_protocol_seq();
            a90_cmdproto_begin(protocol_seq, argv[0], argc, command->flags);
        }
        a90_console_printf("%s\r\n", a90_controller_busy_message(busy_reason));
        a90_shell_save_last_result(argv[0], result, result_errno, 0, command->flags);
        a90_logf("cmd", "busy menu-active name=%s flags=0x%x",
                    argv[0], command->flags);
        if (protocol_v1) {
            a90_cmdproto_end(protocol_seq,
                             argv[0],
                             result,
                             result_errno,
                             0,
                             command->flags,
                             a90_cmdproto_status(result, false, true));
        }
        return result;
    }

    if (protocol_v1) {
        protocol_seq = a90_shell_next_protocol_seq();
        a90_cmdproto_begin(protocol_seq, argv[0], argc, command->flags);
    }

    a90_logf("cmd", "start name=%s argc=%d flags=0x%x",
                argv[0], argc, command->flags);

    if ((command->flags & CMD_DISPLAY) != 0) {
        stop_auto_hud(false);
    }

    errno = 0;
    started_ms = monotonic_millis();
    result = command->handler(argv, argc);
    duration_ms = monotonic_millis() - started_ms;
    if (duration_ms < 0) {
        duration_ms = 0;
    }

    result_errno = a90_shell_result_errno(result);
    a90_shell_save_last_result(argv[0], result, result_errno, duration_ms, command->flags);
    a90_logf("cmd", "end name=%s rc=%d errno=%d duration=%ldms flags=0x%x",
                argv[0],
                result,
                result_errno,
                duration_ms,
                command->flags);

    a90_shell_print_result(command, argv[0], result, result_errno, duration_ms);
    if (protocol_v1) {
        a90_cmdproto_end(protocol_seq,
                         argv[0],
                         result,
                         result_errno,
                         duration_ms,
                         command->flags,
                         a90_cmdproto_status(result, false, false));
    }
    return result;
}

static void shell_loop(void) {
    char line[512];

    print_shell_intro();

    while (1) {
        char *argv[32];
        int argc;

        print_prompt();
        if (a90_console_readline(line, sizeof(line)) < 0) {
            a90_console_printf("read: %s\r\n", strerror(errno));
            sleep(1);
            continue;
        }
        if (strncmp(line, "a90:", 4) == 0) {
            continue;
        }
        if (is_unsolicited_at_fragment_noise(line)) {
            a90_logf("serial", "ignored AT fragment line=%.48s", skip_shell_space(line));
            continue;
        }
        if (is_unsolicited_at_noise(line)) {
            a90_logf("serial", "ignored AT probe line=%.48s", skip_shell_space(line));
            continue;
        }

        argc = split_args(line, argv, 32);
        if (argc == 0) {
            continue;
        }

        if (a90_controller_menu_is_active() && a90_controller_is_hide_word(argv[0])) {
            a90_controller_request_menu_hide();
            a90_controller_set_menu_active(false);
            a90_console_printf("[busy] auto menu active; hide requested\r\n");
            a90_logf("menu", "hide requested by serial word=%s", argv[0]);
            continue;
        }

        if (strcmp(argv[0], "cmdv1") == 0) {
            if (argc < 2) {
                char *usage_argv[] = { "cmdv1", NULL };

                execute_shell_command(usage_argv, 1, false);
            } else {
                execute_shell_command(&argv[1], argc - 1, true);
            }
            continue;
        }

        if (strcmp(argv[0], "cmdv1x") == 0) {
            struct a90_cmdproto_decoded decoded;
            int decoded_argc;

            decoded_argc = a90_cmdproto_decode_v1x(&argv[1],
                                                   argc - 1,
                                                   &decoded);
            if (decoded_argc < 0) {
                print_cmdv1x_error(decoded_argc);
            } else {
                execute_shell_command(decoded.argv, decoded_argc, true);
            }
            continue;
        }

        execute_shell_command(argv, argc, false);
    }
}
