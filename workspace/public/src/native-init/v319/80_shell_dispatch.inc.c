/* Included by the current native-init translation unit. Do not compile standalone. */

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

static int handle_cmdmeta(char **argv, int argc);
static int handle_cmdgroups(char **argv, int argc);
static int handle_policycheck(char **argv, int argc);

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

static int handle_hudlog(char **argv, int argc) {
    return cmd_hudlog(argv, argc);
}

static int handle_exposure(char **argv, int argc) {
    return cmd_exposure(argv, argc);
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

static int handle_pid1guard(char **argv, int argc) {
    return cmd_pid1guard(argv, argc);
}

static int handle_reaper(char **argv, int argc) {
    return cmd_reaper(argv, argc);
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

    a90_app_displaytest_cutout_default(&cal);
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
    a90_app_displaytest_cutout_clamp(&cal);
    a90_console_printf("cutoutcal: x=%d y=%d size=%d\r\n",
            cal.center_x,
            cal.center_y,
            cal.size);
    return a90_app_displaytest_draw_cutout_calibration(&cal, false);
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

static int handle_inputscan(char **argv, int argc) {
    return cmd_inputscan(argv, argc);
}

static int handle_readinput(char **argv, int argc) {
    return cmd_readinput(argv, argc);
}

static int handle_doominput(char **argv, int argc) {
    return cmd_doominput(argv, argc);
}

static int handle_doompad(char **argv, int argc) {
    return cmd_doompad(argv, argc);
}

static int handle_doominputmux(char **argv, int argc) {
    return cmd_doominputmux(argv, argc);
}

static int handle_waitkey(char **argv, int argc) {
    return a90_input_cmd_waitkey(argv, argc);
}

static int handle_inputlayout(char **argv, int argc) {
    return a90_input_cmd_inputlayout(argv, argc);
}

static int handle_waitgesture(char **argv, int argc) {
    return a90_input_cmd_waitgesture(argv, argc);
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

static int handle_screenapp(char **argv, int argc) {
    const char *app;
    int rc;

    if (argc != 2) {
        a90_console_printf("usage: screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]\r\n");
        return -EINVAL;
    }

    app = argv[1];
    a90_console_printf("screenapp.app=%s\r\n", app);
    a90_console_printf("screenapp.safety=display-only-explicit\r\n");
    if (strcmp(app, "network") == 0 || strcmp(app, "usb-net") == 0) {
        a90_console_printf("screenapp.title=NETWORK STATUS\r\n");
        rc = a90_app_network_draw_summary();
    } else if (strcmp(app, "wifi-status") == 0 || strcmp(app, "status") == 0) {
        a90_console_printf("screenapp.title=WIFI STATUS\r\n");
        rc = a90_app_wifi_draw_status();
    } else if (strcmp(app, "wifi-profiles") == 0 || strcmp(app, "profiles") == 0) {
        a90_console_printf("screenapp.title=WIFI PROFILES\r\n");
        rc = a90_app_wifi_draw_profiles();
    } else if (strcmp(app, "wifi-scan") == 0 || strcmp(app, "scan") == 0) {
        a90_console_printf("screenapp.title=WIFI SCAN RESULTS\r\n");
        a90_app_wifi_reset(SCREEN_APP_WIFI_SCAN);
        rc = a90_app_wifi_draw_scan();
    } else if (strcmp(app, "wifi-ping") == 0 || strcmp(app, "ping") == 0) {
        a90_console_printf("screenapp.title=WIFI PING RESULTS\r\n");
        a90_app_wifi_reset(SCREEN_APP_WIFI_PING);
        rc = a90_app_wifi_draw_ping();
    } else if (strcmp(app, "audio-status") == 0 || strcmp(app, "audio") == 0) {
        a90_console_printf("screenapp.title=AUDIO STATUS\r\n");
        rc = a90_app_audio_draw_status();
    } else if (strcmp(app, "audio-profile") == 0 || strcmp(app, "profile") == 0) {
        a90_console_printf("screenapp.title=AUDIO PROFILE\r\n");
        rc = a90_app_audio_draw_profile();
    } else if (strcmp(app, "audio-stages") == 0 || strcmp(app, "stages") == 0) {
        a90_console_printf("screenapp.title=AUDIO STAGES\r\n");
        rc = a90_app_audio_draw_stages();
    } else if (strcmp(app, "audio-map") == 0 || strcmp(app, "speaker-map") == 0) {
        a90_console_printf("screenapp.title=AUDIO ROUTE MAP\r\n");
        rc = a90_app_audio_draw_map();
    } else if (strcmp(app, "audio-chime") == 0 || strcmp(app, "chime") == 0) {
        a90_console_printf("screenapp.title=AUDIO CHIME\r\n");
        rc = a90_app_audio_draw_chime();
    } else if (strcmp(app, "about-version") == 0 || strcmp(app, "version") == 0) {
        a90_console_printf("screenapp.title=ABOUT / VERSION\r\n");
        rc = a90_app_about_draw_version();
    } else if (strcmp(app, "about-changelog") == 0 || strcmp(app, "changelog") == 0) {
        a90_console_printf("screenapp.title=ABOUT / CHANGELOG\r\n");
        rc = a90_app_about_draw_changelog();
    } else {
        a90_console_printf("screenapp.valid=0\r\n");
        a90_console_printf("usage: screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]\r\n");
        return -EINVAL;
    }

    a90_console_printf("screenapp.valid=1\r\n");
    a90_console_printf("screenapp.rc=%d\r\n", rc);
    a90_console_printf("screenapp.presented=%d\r\n", rc == 0 ? 1 : 0);
    return rc;
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

static int handle_appendfile(char **argv, int argc) {
    return cmd_appendfile(argv, argc);
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

static int handle_longsoak(char **argv, int argc) {
    return a90_longsoak_cmd(argv, argc);
}

static void service_sync_enabled_states(void) {
    a90_service_set_enabled_state(A90_SERVICE_HUD, false);
    a90_service_set_enabled_state(A90_SERVICE_ADBD, false);
    a90_service_set_enabled_state(A90_SERVICE_LONGSOAK, false);
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
    } else if (service == A90_SERVICE_LONGSOAK) {
        (void)a90_longsoak_status();
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
    case A90_SERVICE_LONGSOAK:
        return a90_longsoak_start(A90_LONGSOAK_DEFAULT_INTERVAL_SEC);
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
    case A90_SERVICE_LONGSOAK:
        return a90_longsoak_stop();
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

static int handle_usb(char **argv, int argc) {
    return a90_usb_gadget_cmd(argv, argc);
}

static int handle_kernelinv(char **argv, int argc) {
    return a90_kernelinv_cmd(argv, argc);
}

static int handle_sensormap(char **argv, int argc) {
    return a90_sensormap_cmd(argv, argc);
}

static int handle_pstore(char **argv, int argc) {
    return a90_pstore_cmd(argv, argc);
}

static int handle_watchdoginv(char **argv, int argc) {
    return a90_watchdoginv_cmd(argv, argc);
}

static int handle_tracefs(char **argv, int argc) {
    return a90_tracefs_cmd(argv, argc);
}

static int handle_wifi(char **argv, int argc) {
    return a90_wifi_cmd(argv, argc);
}

static int handle_wifiinv(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: wifiinv [summary|full|refresh|paths]\r\n");
        return -EINVAL;
    }

    if (strcmp(subcommand, "summary") == 0) {
        return a90_wifiinv_print_summary();
    }
    if (strcmp(subcommand, "full") == 0) {
        return a90_wifiinv_print_full();
    }
    if (strcmp(subcommand, "refresh") == 0) {
        return a90_wifiinv_print_refresh();
    }
    if (strcmp(subcommand, "paths") == 0) {
        return a90_wifiinv_print_paths();
    }

    a90_console_printf("usage: wifiinv [summary|full|refresh|paths]\r\n");
    return -EINVAL;
}

static int handle_wififeas(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: wififeas [summary|full|gate|refresh|paths]\r\n");
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
    if (strcmp(subcommand, "refresh") == 0) {
        return a90_wififeas_print_refresh();
    }
    if (strcmp(subcommand, "paths") == 0) {
        return a90_wififeas_print_paths();
    }

    a90_console_printf("usage: wififeas [summary|full|gate|refresh|paths]\r\n");
    return -EINVAL;
}

struct gpu_g0_open_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int close_rc;
    int close_errno;
    long elapsed_ms;
};

struct gpu_g1_context_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int flags_in;
    unsigned int flags_out;
    long open_elapsed_ms;
    long create_elapsed_ms;
    long destroy_elapsed_ms;
    long total_elapsed_ms;
};

#define GPU_G0_DEVNODE "/dev/kgsl-3d0"
#define GPU_G0_SYSFS_DEV "/sys/class/kgsl/kgsl-3d0/dev"
#define GPU_G0_SYSFS_UEVENT "/sys/class/kgsl/kgsl-3d0/uevent"
#define GPU_G0_FWCLASS_PATH "/sys/module/firmware_class/parameters/path"
#define GPU_G0_RUNTIME_FW_DIR "/cache/a90-runtime/pkg/gpu-g0-fw"
#define GPU_G0_VENDOR_MNT_FW_DIR "/vendor/firmware_mnt/image"
#define GPU_G0_FW_A630_SQE "a630_sqe.fw"
#define GPU_G0_FW_A640_GMU "a640_gmu.bin"
#define GPU_G0_FW_A640_ZAP_MDT "a640_zap.mdt"
#define GPU_G0_FW_A640_ZAP_B00 "a640_zap.b00"
#define GPU_G0_FW_A640_ZAP_B01 "a640_zap.b01"
#define GPU_G0_FW_A640_ZAP_B02 "a640_zap.b02"
#define GPU_G0_FW_A630_SQE_SIZE 32304
#define GPU_G0_FW_A640_GMU_SIZE 37680
#define GPU_G0_FW_A640_ZAP_MDT_SIZE 6860
#define GPU_G0_FW_A640_ZAP_B00_SIZE 148
#define GPU_G0_FW_A640_ZAP_B01_SIZE 6712
#define GPU_G0_FW_A640_ZAP_B02_SIZE 1968
#define GPU_G0_DEFAULT_TIMEOUT_MS 2000
#define GPU_G0_MAX_TIMEOUT_MS 10000
#define GPU_KGSL_IOC_TYPE 0x09
#define GPU_KGSL_CONTEXT_NO_GMEM_ALLOC 0x00000002U
#define GPU_KGSL_CONTEXT_PREAMBLE 0x00000010U
#define GPU_KGSL_CONTEXT_NO_SNAPSHOT 0x00040000U
#define GPU_KGSL_CONTEXT_TYPE_SHIFT 20
#define GPU_KGSL_CONTEXT_TYPE_GL 1U
#define GPU_G1_CONTEXT_FLAGS \
    (GPU_KGSL_CONTEXT_NO_GMEM_ALLOC | \
     GPU_KGSL_CONTEXT_PREAMBLE | \
     GPU_KGSL_CONTEXT_NO_SNAPSHOT | \
     (GPU_KGSL_CONTEXT_TYPE_GL << GPU_KGSL_CONTEXT_TYPE_SHIFT))

struct gpu_kgsl_drawctxt_create {
    unsigned int flags;
    unsigned int drawctxt_id;
};

struct gpu_kgsl_drawctxt_destroy {
    unsigned int drawctxt_id;
};

#define GPU_IOCTL_KGSL_DRAWCTXT_CREATE \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x13, struct gpu_kgsl_drawctxt_create)
#define GPU_IOCTL_KGSL_DRAWCTXT_DESTROY \
    _IOW(GPU_KGSL_IOC_TYPE, 0x14, struct gpu_kgsl_drawctxt_destroy)

static bool gpu_g0_parse_int(const char *text, int *out) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0' || out == NULL) {
        return false;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == NULL || *end != '\0' ||
        value < 0 || value > INT_MAX) {
        return false;
    }
    *out = (int)value;
    return true;
}

static void gpu_g0_print_read_attr(const char *key, const char *path) {
    char value[512];
    int saved_errno;

    errno = 0;
    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        flatten_inline_text(value);
        a90_console_printf("gpu.g0.%s.read_rc=0\r\n", key);
        a90_console_printf("gpu.g0.%s=%s\r\n", key, value);
        return;
    }
    saved_errno = errno;
    a90_console_printf("gpu.g0.%s.read_rc=-1 errno=%d\r\n", key, saved_errno);
}

static void gpu_g0_print_stat(const char *key, const char *path) {
    struct stat st;
    int saved_errno;

    errno = 0;
    if (lstat(path, &st) < 0) {
        saved_errno = errno;
        a90_console_printf("gpu.g0.%s.path=%s\r\n", key, path);
        a90_console_printf("gpu.g0.%s.exists=0 errno=%d\r\n", key, saved_errno);
        return;
    }
    a90_console_printf("gpu.g0.%s.path=%s\r\n", key, path);
    a90_console_printf("gpu.g0.%s.exists=1\r\n", key);
    a90_console_printf("gpu.g0.%s.mode=0%o\r\n", key, (unsigned int)(st.st_mode & 07777));
    a90_console_printf("gpu.g0.%s.is_chr=%d\r\n", key, S_ISCHR(st.st_mode) ? 1 : 0);
    a90_console_printf("gpu.g0.%s.is_reg=%d\r\n", key, S_ISREG(st.st_mode) ? 1 : 0);
    if (S_ISCHR(st.st_mode)) {
        a90_console_printf("gpu.g0.%s.major=%u\r\n", key, (unsigned int)major(st.st_rdev));
        a90_console_printf("gpu.g0.%s.minor=%u\r\n", key, (unsigned int)minor(st.st_rdev));
    }
}

static int gpu_g0_join_path(char *out, size_t out_size, const char *dir, const char *name) {
    if (snprintf(out, out_size, "%s/%s", dir, name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -ENAMETOOLONG;
    }
    return 0;
}

static int gpu_g0_ensure_runtime_fw_dir(void) {
    if (ensure_dir("/cache/a90-runtime", 0700) < 0 ||
        ensure_dir("/cache/a90-runtime/pkg", 0700) < 0 ||
        ensure_dir(GPU_G0_RUNTIME_FW_DIR, 0700) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int gpu_g0_verify_regular_file(const char *key, const char *path, off_t expected_size) {
    struct stat st;
    int saved_errno;

    errno = 0;
    if (lstat(path, &st) < 0) {
        saved_errno = errno;
        a90_console_printf("gpu.g0.fwclass_prepare.%s.path=%s\r\n", key, path);
        a90_console_printf("gpu.g0.fwclass_prepare.%s.exists=0 errno=%d\r\n", key, saved_errno);
        return -saved_errno;
    }
    a90_console_printf("gpu.g0.fwclass_prepare.%s.path=%s\r\n", key, path);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.exists=1\r\n", key);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.is_reg=%d\r\n", key, S_ISREG(st.st_mode) ? 1 : 0);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.size=%ld\r\n", key, (long)st.st_size);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.expected_size=%ld\r\n", key, (long)expected_size);
    if (!S_ISREG(st.st_mode)) {
        a90_console_printf("gpu.g0.fwclass_prepare.%s.rc=%d\r\n", key, -EINVAL);
        return -EINVAL;
    }
    if (st.st_size != expected_size) {
        a90_console_printf("gpu.g0.fwclass_prepare.%s.rc=%d\r\n", key, -EOVERFLOW);
        return -EOVERFLOW;
    }
    a90_console_printf("gpu.g0.fwclass_prepare.%s.rc=0\r\n", key);
    return 0;
}

static int gpu_g0_copy_regular_file(const char *key,
                                    const char *src,
                                    const char *dst,
                                    off_t expected_size) {
    char buf[4096];
    ssize_t nread;
    off_t total = 0;
    int in_fd = -1;
    int out_fd = -1;
    int rc = 0;

    rc = gpu_g0_verify_regular_file(key, src, expected_size);
    if (rc < 0) {
        return rc;
    }
    errno = 0;
    in_fd = open(src, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (in_fd < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g0.fwclass_prepare.%s.open_src_errno=%d\r\n", key, saved_errno);
        return -saved_errno;
    }
    errno = 0;
    out_fd = open(dst, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0644);
    if (out_fd < 0) {
        int saved_errno = errno;
        close(in_fd);
        a90_console_printf("gpu.g0.fwclass_prepare.%s.open_dst_errno=%d\r\n", key, saved_errno);
        return -saved_errno;
    }
    while ((nread = read(in_fd, buf, sizeof(buf))) > 0) {
        total += nread;
        if (total > expected_size) {
            rc = -EOVERFLOW;
            a90_console_printf("gpu.g0.fwclass_prepare.%s.copy_overflow=1\r\n", key);
            break;
        }
        if (write_all_checked(out_fd, buf, (size_t)nread) < 0) {
            rc = negative_errno_or(EIO);
            a90_console_printf("gpu.g0.fwclass_prepare.%s.write_rc=%d\r\n", key, rc);
            break;
        }
    }
    if (nread < 0 && rc == 0) {
        rc = negative_errno_or(EIO);
        a90_console_printf("gpu.g0.fwclass_prepare.%s.read_rc=%d\r\n", key, rc);
    }
    if (rc == 0 && total != expected_size) {
        rc = -EIO;
        a90_console_printf("gpu.g0.fwclass_prepare.%s.copy_short=1\r\n", key);
    }
    if (rc == 0 && fsync(out_fd) < 0) {
        rc = negative_errno_or(EIO);
        a90_console_printf("gpu.g0.fwclass_prepare.%s.fsync_rc=%d\r\n", key, rc);
    }
    if (close(out_fd) < 0 && rc == 0) {
        rc = negative_errno_or(EIO);
        a90_console_printf("gpu.g0.fwclass_prepare.%s.close_dst_rc=%d\r\n", key, rc);
    }
    close(in_fd);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.dst=%s\r\n", key, dst);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.copy_bytes=%ld\r\n", key, (long)total);
    a90_console_printf("gpu.g0.fwclass_prepare.%s.copy_rc=%d\r\n", key, rc);
    if (rc < 0) {
        unlink(dst);
        return rc;
    }
    return gpu_g0_verify_regular_file(key, dst, expected_size);
}

static int gpu_g0_write_fwclass_path(const char *path) {
    char readback[PATH_MAX];
    int fd;
    int rc = 0;

    errno = 0;
    fd = open(GPU_G0_FWCLASS_PATH, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g0.fwclass_prepare.fwpath.open_errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (write_all_checked(fd, path, strlen(path)) < 0) {
        rc = negative_errno_or(EIO);
    }
    if (close(fd) < 0 && rc == 0) {
        rc = negative_errno_or(EIO);
    }
    a90_console_printf("gpu.g0.fwclass_prepare.fwpath.write_rc=%d\r\n", rc);
    if (rc < 0) {
        return rc;
    }
    if (read_trimmed_text_file(GPU_G0_FWCLASS_PATH, readback, sizeof(readback)) < 0) {
        rc = negative_errno_or(EIO);
        a90_console_printf("gpu.g0.fwclass_prepare.fwpath.readback_rc=%d\r\n", rc);
        return rc;
    }
    flatten_inline_text(readback);
    a90_console_printf("gpu.g0.fwclass_prepare.fwpath.readback=%s\r\n", readback);
    if (strcmp(readback, path) != 0) {
        return -EIO;
    }
    return 0;
}

static int gpu_g0_fwclass_prepare(void) {
    struct fw_entry {
        const char *key;
        const char *name;
        off_t size;
    };
    static const struct fw_entry zap_files[] = {
        { "copy_a640_zap_mdt", GPU_G0_FW_A640_ZAP_MDT, GPU_G0_FW_A640_ZAP_MDT_SIZE },
        { "copy_a640_zap_b00", GPU_G0_FW_A640_ZAP_B00, GPU_G0_FW_A640_ZAP_B00_SIZE },
        { "copy_a640_zap_b01", GPU_G0_FW_A640_ZAP_B01, GPU_G0_FW_A640_ZAP_B01_SIZE },
        { "copy_a640_zap_b02", GPU_G0_FW_A640_ZAP_B02, GPU_G0_FW_A640_ZAP_B02_SIZE },
    };
    char src[PATH_MAX];
    char dst[PATH_MAX];
    int rc;

    a90_console_printf("gpu.g0.fwclass_prepare.version=1\r\n");
    a90_console_printf("gpu.g0.fwclass_prepare.runtime_dir=%s\r\n", GPU_G0_RUNTIME_FW_DIR);
    a90_console_printf("gpu.g0.fwclass_prepare.vendor_mnt_dir=%s\r\n", GPU_G0_VENDOR_MNT_FW_DIR);
    a90_console_printf("gpu.g0.fwclass_prepare.requires_private_sqe_gmu_staged=1\r\n");
    a90_console_printf("gpu.g0.fwclass_prepare.no_private_payload_in_ramdisk=1\r\n");
    a90_console_printf("gpu.g0.fwclass_prepare.no_power_writes=1\r\n");
    a90_console_printf("gpu.g0.fwclass_prepare.no_ioctl=1\r\n");
    a90_console_printf("gpu.g0.fwclass_prepare.no_mmap=1\r\n");

    rc = gpu_g0_ensure_runtime_fw_dir();
    a90_console_printf("gpu.g0.fwclass_prepare.mkdir_rc=%d\r\n", rc);
    if (rc < 0) {
        return rc;
    }

    if (gpu_g0_join_path(dst, sizeof(dst), GPU_G0_RUNTIME_FW_DIR, GPU_G0_FW_A630_SQE) < 0) {
        return -ENAMETOOLONG;
    }
    rc = gpu_g0_verify_regular_file("verify_a630_sqe", dst, GPU_G0_FW_A630_SQE_SIZE);
    if (rc < 0) {
        return rc;
    }
    if (gpu_g0_join_path(dst, sizeof(dst), GPU_G0_RUNTIME_FW_DIR, GPU_G0_FW_A640_GMU) < 0) {
        return -ENAMETOOLONG;
    }
    rc = gpu_g0_verify_regular_file("verify_a640_gmu", dst, GPU_G0_FW_A640_GMU_SIZE);
    if (rc < 0) {
        return rc;
    }

    for (size_t index = 0; index < sizeof(zap_files) / sizeof(zap_files[0]); ++index) {
        if (gpu_g0_join_path(src, sizeof(src), GPU_G0_VENDOR_MNT_FW_DIR, zap_files[index].name) < 0 ||
            gpu_g0_join_path(dst, sizeof(dst), GPU_G0_RUNTIME_FW_DIR, zap_files[index].name) < 0) {
            return -ENAMETOOLONG;
        }
        rc = gpu_g0_copy_regular_file(zap_files[index].key, src, dst, zap_files[index].size);
        if (rc < 0) {
            return rc;
        }
    }

    rc = gpu_g0_write_fwclass_path(GPU_G0_RUNTIME_FW_DIR);
    if (rc < 0) {
        return rc;
    }
    gpu_g0_print_stat("fw_cache_a630_sqe", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A630_SQE);
    gpu_g0_print_stat("fw_cache_a640_gmu", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_GMU);
    gpu_g0_print_stat("fw_cache_a640_zap_mdt", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_MDT);
    gpu_g0_print_stat("fw_cache_a640_zap_b00", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B00);
    gpu_g0_print_stat("fw_cache_a640_zap_b01", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B01);
    gpu_g0_print_stat("fw_cache_a640_zap_b02", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B02);
    a90_console_printf("gpu.g0.fwclass_prepare.result=ok\r\n");
    return 0;
}

static int gpu_g0_read_sysfs_dev(unsigned int *major_num, unsigned int *minor_num) {
    char dev_text[64];

    if (major_num == NULL || minor_num == NULL) {
        errno = EINVAL;
        return -EINVAL;
    }
    if (read_trimmed_text_file(GPU_G0_SYSFS_DEV, dev_text, sizeof(dev_text)) < 0) {
        return negative_errno_or(ENOENT);
    }
    if (sscanf(dev_text, "%u:%u", major_num, minor_num) != 2) {
        errno = EINVAL;
        return -EINVAL;
    }
    return 0;
}

static int gpu_g0_materialize_devnode(void) {
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    int rc;

    rc = gpu_g0_read_sysfs_dev(&major_num, &minor_num);
    a90_console_printf("gpu.g0.materialize.sysfs_dev_rc=%d\r\n", rc);
    if (rc < 0) {
        return rc;
    }
    a90_console_printf("gpu.g0.materialize.major=%u\r\n", major_num);
    a90_console_printf("gpu.g0.materialize.minor=%u\r\n", minor_num);
    errno = 0;
    if (ensure_char_node(GPU_G0_DEVNODE, major_num, minor_num) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g0.materialize.rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    a90_console_printf("gpu.g0.materialize.rc=0\r\n");
    return 0;
}

static int gpu_g0_status(void) {
    a90_console_printf("gpu.g0.version=1\r\n");
    a90_console_printf("gpu.g0.scope=kgsl-open-hang-diagnosis\r\n");
    a90_console_printf("gpu.g0.safety=read-only-status-plus-bounded-open-probe\r\n");
    a90_console_printf("gpu.g0.bright_line.no_power_writes=1\r\n");
    a90_console_printf("gpu.g0.bright_line.no_ioctl=1\r\n");
    a90_console_printf("gpu.g0.bright_line.no_mmap=1\r\n");
    gpu_g0_print_stat("sysfs_class", "/sys/class/kgsl/kgsl-3d0");
    gpu_g0_print_read_attr("sysfs_dev", GPU_G0_SYSFS_DEV);
    gpu_g0_print_read_attr("sysfs_uevent", GPU_G0_SYSFS_UEVENT);
    gpu_g0_print_read_attr("fwclass_path", GPU_G0_FWCLASS_PATH);
    gpu_g0_print_stat("devnode", GPU_G0_DEVNODE);
    gpu_g0_print_stat("fw_vendor_a630_sqe", "/vendor/firmware/a630_sqe.fw");
    gpu_g0_print_stat("fw_vendor_a640_gmu", "/vendor/firmware/a640_gmu.bin");
    gpu_g0_print_stat("fw_root_a630_sqe", "/firmware/a630_sqe.fw");
    gpu_g0_print_stat("fw_root_a640_gmu", "/firmware/a640_gmu.bin");
    gpu_g0_print_stat("fw_vendor_a640_zap_mdt", "/vendor/firmware/a640_zap.mdt");
    gpu_g0_print_stat("fw_vendor_mnt_a640_zap_mdt", "/vendor/firmware_mnt/image/a640_zap.mdt");
    gpu_g0_print_stat("fw_vendor_mnt_a640_zap_b00", "/vendor/firmware_mnt/image/a640_zap.b00");
    gpu_g0_print_stat("fw_vendor_mnt_a640_zap_b01", "/vendor/firmware_mnt/image/a640_zap.b01");
    gpu_g0_print_stat("fw_vendor_mnt_a640_zap_b02", "/vendor/firmware_mnt/image/a640_zap.b02");
    gpu_g0_print_stat("fw_mnt_a640_zap_mdt", "/firmware_mnt/image/a640_zap.mdt");
    gpu_g0_print_stat("fw_mnt_a640_zap_b00", "/firmware_mnt/image/a640_zap.b00");
    gpu_g0_print_stat("fw_mnt_a640_zap_b01", "/firmware_mnt/image/a640_zap.b01");
    gpu_g0_print_stat("fw_mnt_a640_zap_b02", "/firmware_mnt/image/a640_zap.b02");
    gpu_g0_print_stat("fw_cache_a630_sqe", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A630_SQE);
    gpu_g0_print_stat("fw_cache_a640_gmu", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_GMU);
    gpu_g0_print_stat("fw_cache_a640_zap_mdt", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_MDT);
    gpu_g0_print_stat("fw_cache_a640_zap_b00", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B00);
    gpu_g0_print_stat("fw_cache_a640_zap_b01", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B01);
    gpu_g0_print_stat("fw_cache_a640_zap_b02", GPU_G0_RUNTIME_FW_DIR "/" GPU_G0_FW_A640_ZAP_B02);
    return 0;
}

static int gpu_g0_open_probe_child(const char *path, int flags, int write_fd) {
    struct gpu_g0_open_probe_result result;
    long started_ms = monotonic_millis();
    int fd;

    memset(&result, 0, sizeof(result));
    result.version = 1;
    result.close_rc = -1;
    errno = 0;
    fd = open(path, flags | O_CLOEXEC);
    result.elapsed_ms = monotonic_millis() - started_ms;
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
    } else {
        result.open_rc = 0;
        result.open_errno = 0;
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
            result.close_errno = 0;
        }
    }
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_g0_open_probe(int timeout_ms, bool open_rdwr, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    int flags = open_rdwr ? O_RDWR : O_RDONLY;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_g0_open_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g0.open.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.g0.open.version=1\r\n");
    a90_console_printf("gpu.g0.open.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g0.open.flags=%s\r\n", open_rdwr ? "O_RDWR" : "O_RDONLY");
    a90_console_printf("gpu.g0.open.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g0.open.parent_enters_open=0\r\n");
    a90_console_printf("gpu.g0.open.ioctl_attempted=0\r\n");
    a90_console_printf("gpu.g0.open.mmap_attempted=0\r\n");
    a90_console_printf("gpu.g0.open.power_write_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g0.open.materialize_requested=1\r\n");
        a90_console_printf("gpu.g0.open.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g0.open.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g0.open.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.g0.open.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_g0_open_probe_child(GPU_G0_DEVNODE, flags, pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.g0.open.child_pid=%ld\r\n", (long)pid);

    while (monotonic_millis() <= deadline_ms) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        int remaining_ms = (int)(deadline_ms > now_ms ? deadline_ms - now_ms : 0);
        int poll_ms = remaining_ms > 50 ? 50 : remaining_ms;
        ssize_t rd;
        pid_t wait_rc;

        if (poll_ms < 0) {
            poll_ms = 0;
        }
        pfd.fd = pipefd[0];
        pfd.events = POLLIN | POLLHUP;
        pfd.revents = 0;
        if (poll(&pfd, 1, poll_ms) > 0 && (pfd.revents & (POLLIN | POLLHUP)) != 0) {
            rd = read(pipefd[0], &result, sizeof(result));
            if (rd == (ssize_t)sizeof(result)) {
                got_result = true;
            }
            break;
        }
        wait_rc = waitpid(pid, &child_status, WNOHANG);
        if (wait_rc == pid) {
            child_reaped = true;
            break;
        }
    }

    if (!got_result && !child_reaped) {
        timed_out = true;
        if (kill(pid, SIGKILL) == 0) {
            child_killed = true;
        }
        if (waitpid(pid, &child_status, WNOHANG) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, WNOHANG) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.g0.open.result=%s\r\n",
                       got_result ? (result.open_rc == 0 ? "returned" : "failed") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g0.open.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.g0.open.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.g0.open.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.g0.open.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.g0.open.child_elapsed_ms=%ld\r\n", result.elapsed_ms);
        a90_console_printf("gpu.g0.open.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.g0.open.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.g0.open.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.g0.open.close_errno=%d\r\n", result.close_errno);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static int gpu_g1_context_probe_child(int write_fd) {
    struct gpu_g1_context_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    int fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.destroy_rc = -1;
    result.flags_in = GPU_G1_CONTEXT_FLAGS;
    result.flags_out = GPU_G1_CONTEXT_FLAGS;

    errno = 0;
    stage_started_ms = monotonic_millis();
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    result.open_elapsed_ms = monotonic_millis() - stage_started_ms;
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        result.total_elapsed_ms = monotonic_millis() - total_started_ms;
        (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
        close(write_fd);
        _exit(0);
    }

    result.open_rc = 0;
    result.open_errno = 0;
    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    stage_started_ms = monotonic_millis();
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
    } else {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        result.create_rc = 0;
        result.create_errno = 0;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.context_id = create_arg.drawctxt_id;
        result.flags_out = create_arg.flags;
        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = create_arg.drawctxt_id;
        result.destroy_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_DESTROY, &destroy_arg) < 0) {
            result.destroy_rc = -1;
            result.destroy_errno = errno;
        } else {
            result.destroy_rc = 0;
            result.destroy_errno = 0;
        }
        result.destroy_elapsed_ms = monotonic_millis() - stage_started_ms;
    }

    errno = 0;
    if (close(fd) < 0) {
        result.close_rc = -1;
        result.close_errno = errno;
    } else {
        result.close_rc = 0;
        result.close_errno = 0;
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_g1_context_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_g1_context_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g1.context.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.g1.context.version=1\r\n");
    a90_console_printf("gpu.g1.context.scope=kgsl-context-create-destroy-probe\r\n");
    a90_console_printf("gpu.g1.context.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g1.context.flags=O_RDWR\r\n");
    a90_console_printf("gpu.g1.context.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g1.context.parent_enters_open=0\r\n");
    a90_console_printf("gpu.g1.context.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.g1.context.ioctl_allowlist=drawctxt_create,drawctxt_destroy\r\n");
    a90_console_printf("gpu.g1.context.mmap_attempted=0\r\n");
    a90_console_printf("gpu.g1.context.gpuobj_alloc_attempted=0\r\n");
    a90_console_printf("gpu.g1.context.submit_attempted=0\r\n");
    a90_console_printf("gpu.g1.context.power_write_attempted=0\r\n");
    a90_console_printf("gpu.g1.context.requested_flags=0x%x\r\n", GPU_G1_CONTEXT_FLAGS);
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g1.context.materialize_requested=1\r\n");
        a90_console_printf("gpu.g1.context.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g1.context.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g1.context.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.g1.context.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_g1_context_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.g1.context.child_pid=%ld\r\n", (long)pid);

    while (monotonic_millis() <= deadline_ms) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        int remaining_ms = (int)(deadline_ms > now_ms ? deadline_ms - now_ms : 0);
        int poll_ms = remaining_ms > 50 ? 50 : remaining_ms;
        ssize_t rd;
        pid_t wait_rc;

        if (poll_ms < 0) {
            poll_ms = 0;
        }
        pfd.fd = pipefd[0];
        pfd.events = POLLIN | POLLHUP;
        pfd.revents = 0;
        if (poll(&pfd, 1, poll_ms) > 0 && (pfd.revents & (POLLIN | POLLHUP)) != 0) {
            rd = read(pipefd[0], &result, sizeof(result));
            if (rd == (ssize_t)sizeof(result)) {
                got_result = true;
            }
            break;
        }
        wait_rc = waitpid(pid, &child_status, WNOHANG);
        if (wait_rc == pid) {
            child_reaped = true;
            break;
        }
    }

    if (!got_result && !child_reaped) {
        timed_out = true;
        if (kill(pid, SIGKILL) == 0) {
            child_killed = true;
        }
        if (waitpid(pid, &child_status, WNOHANG) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, WNOHANG) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.g1.context.result=%s\r\n",
                       got_result ? (result.create_rc == 0 ? "created-destroyed" : "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g1.context.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.g1.context.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.g1.context.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.g1.context.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.g1.context.open_elapsed_ms=%ld\r\n", result.open_elapsed_ms);
        a90_console_printf("gpu.g1.context.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.g1.context.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.g1.context.create_elapsed_ms=%ld\r\n", result.create_elapsed_ms);
        a90_console_printf("gpu.g1.context.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.g1.context.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.g1.context.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.g1.context.flags_in=0x%x\r\n", result.flags_in);
        a90_console_printf("gpu.g1.context.flags_out=0x%x\r\n", result.flags_out);
        a90_console_printf("gpu.g1.context.destroy_attempted=%d\r\n", result.destroy_attempted);
        a90_console_printf("gpu.g1.context.destroy_elapsed_ms=%ld\r\n", result.destroy_elapsed_ms);
        a90_console_printf("gpu.g1.context.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.g1.context.destroy_errno=%d\r\n", result.destroy_errno);
        a90_console_printf("gpu.g1.context.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.g1.context.close_errno=%d\r\n", result.close_errno);
        a90_console_printf("gpu.g1.context.total_elapsed_ms=%ld\r\n", result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static int handle_gpu(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "g0-status";
    int timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    bool rdwr = false;
    bool materialize_devnode = false;
    int index;

    if (strcmp(subcommand, "g0-status") == 0 || strcmp(subcommand, "status") == 0) {
        if (argc != 1 && argc != 2) {
            a90_console_printf("usage: gpu g0-status\r\n");
            return -EINVAL;
        }
        return gpu_g0_status();
    }
    if (strcmp(subcommand, "g0-fwclass-prepare") == 0 ||
        strcmp(subcommand, "fwclass-prepare") == 0) {
        if (argc != 2) {
            a90_console_printf("usage: gpu g0-fwclass-prepare\r\n");
            return -EINVAL;
        }
        return gpu_g0_fwclass_prepare();
    }
    if (strcmp(subcommand, "g1-context-probe") == 0 ||
        strcmp(subcommand, "context-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.g1.context.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu g1-context-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_g1_context_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "g0-open-probe") != 0) {
        a90_console_printf("usage: gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]]\r\n");
        return -EINVAL;
    }
    for (index = 2; index < argc; ++index) {
        if (strcmp(argv[index], "--timeout-ms") == 0) {
            if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                a90_console_printf("gpu.g0.open.error=bad-timeout\r\n");
                return -EINVAL;
            }
            ++index;
        } else if (strcmp(argv[index], "--rdwr") == 0) {
            rdwr = true;
        } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
            materialize_devnode = true;
        } else {
            a90_console_printf("usage: gpu g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]\r\n");
            return -EINVAL;
        }
    }
    return gpu_g0_open_probe(timeout_ms, rdwr, materialize_devnode);
}

static int handle_audio(char **argv, int argc) {
    return a90_audio_cmd(argv, argc);
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
    { "help", handle_help, "help", CMD_NONE, A90_CMD_GROUP_CORE },
    { "cmdv1", handle_cmdv1, "cmdv1 <command> [args...]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "cmdv1x", handle_cmdv1x, "cmdv1x <len:hex-utf8-arg>...", CMD_NONE, A90_CMD_GROUP_CORE },
    { "version", handle_version, "version", CMD_NONE, A90_CMD_GROUP_CORE },
    { "status", handle_status, "status", CMD_NONE, A90_CMD_GROUP_CORE },
    { "last", handle_last, "last", CMD_NONE, A90_CMD_GROUP_CORE },
    { "cmdmeta", handle_cmdmeta, "cmdmeta [verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "cmdgroups", handle_cmdgroups, "cmdgroups [verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "logpath", handle_logpath, "logpath", CMD_NONE, A90_CMD_GROUP_CORE },
    { "logcat", handle_logcat, "logcat", CMD_NONE, A90_CMD_GROUP_CORE },
    { "hudlog", handle_hudlog, "hudlog [status|on|off]", CMD_NONE, A90_CMD_GROUP_DISPLAY },
    { "exposure", handle_exposure, "exposure [status|verbose|guard]", CMD_NONE, A90_CMD_GROUP_NETWORK },
    { "policycheck", handle_policycheck, "policycheck [status|run|verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "diag", handle_diag, "diag [summary|full|bundle|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "usb", handle_usb, "usb [status|mass-storage add|mass-storage expose|mass-storage remove]", CMD_NONE, A90_CMD_GROUP_SERVICE },
    { "kernelinv", handle_kernelinv, "kernelinv [summary|full|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "sensormap", handle_sensormap, "sensormap [summary|thermal|power|full|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "pstore", handle_pstore, "pstore [summary|full|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "watchdoginv", handle_watchdoginv, "watchdoginv [summary|full|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "tracefs", handle_tracefs, "tracefs [summary|full|paths]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "gpu", handle_gpu, "gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "audio", handle_audio, "audio [status|profiles|profile|speaker-map|stages|prereq|app-type|setcal|route|play|chime|play-status|stop|adsp-status|snd-status]", CMD_NONE, A90_CMD_GROUP_ANDROID },
    { "video", handle_video, "video [status|frame [bars|checker|mono|0xRRGGBB]|demo [badapple|badapple-scale|nyan|doom [status|verify|play|frame|engine-probe] [frames] [--wad runtime-private --sha256 EXPECTED]|frame-pattern]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]|flipprobe [frames]|stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status PATH]|cache [status|verify|play] SHA256 [--trust-cache] [--layout full|player-hud]|cache preset [badapple|badapple-scale|nyan] [status|verify|play]]", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "wifi", handle_wifi, "wifi [status|scan [delay_ms]|connect [profile]|dhcp [profile]|ping [gateway|internet|all]|cleanup|config [status|prepare [profile]]]", CMD_NONE, A90_CMD_GROUP_NETWORK },
    { "wifiinv", handle_wifiinv, "wifiinv [summary|full|refresh|paths]", CMD_NONE, A90_CMD_GROUP_NETWORK },
    { "wififeas", handle_wififeas, "wififeas [summary|full|gate|refresh|paths]", CMD_NONE, A90_CMD_GROUP_NETWORK },
    { "timeline", handle_timeline, "timeline", CMD_NONE, A90_CMD_GROUP_CORE },
    { "bootstatus", handle_bootstatus, "bootstatus", CMD_NONE, A90_CMD_GROUP_CORE },
    { "selftest", handle_selftest, "selftest [status|run|verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "pid1guard", handle_pid1guard, "pid1guard [status|run|verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "reaper", handle_reaper, "reaper [status|run|verbose]", CMD_NONE, A90_CMD_GROUP_CORE },
    { "uname", handle_uname, "uname", CMD_NONE, A90_CMD_GROUP_CORE },
    { "pwd", handle_pwd, "pwd", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "cd", handle_cd, "cd <dir>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "ls", handle_ls, "ls [dir]", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "cat", handle_cat, "cat <file>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "stat", handle_stat, "stat <path>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "mounts", handle_mounts, "mounts", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "mountsystem", handle_mountsystem, "mountsystem [ro|rw]", CMD_NONE, A90_CMD_GROUP_STORAGE },
    { "mountsd", handle_mountsd, "mountsd [status|ro|rw|off|init]", CMD_NONE, A90_CMD_GROUP_STORAGE },
    { "storage", handle_storage, "storage", CMD_NONE, A90_CMD_GROUP_STORAGE },
    { "runtime", handle_runtime, "runtime", CMD_NONE, A90_CMD_GROUP_STORAGE },
    { "helpers", handle_helpers, "helpers [status|verbose|manifest|plan|path <name>|verify [name]]", CMD_NONE, A90_CMD_GROUP_STORAGE },
    { "userland", handle_userland, "userland [status|verbose|test [busybox|toybox|all]]", CMD_BLOCKING, A90_CMD_GROUP_STORAGE },
    { "busybox", handle_busybox, "busybox <applet> [args...]", CMD_BLOCKING, A90_CMD_GROUP_STORAGE },
    { "toybox", handle_toybox, "toybox <applet> [args...]", CMD_BLOCKING, A90_CMD_GROUP_STORAGE },
    { "prepareandroid", handle_prepareandroid, "prepareandroid", CMD_NONE, A90_CMD_GROUP_ANDROID },
    { "inputinfo", handle_inputinfo, "inputinfo [eventX]", CMD_NONE, A90_CMD_GROUP_INPUT },
    { "drminfo", handle_drminfo, "drminfo [entry]", CMD_NONE, A90_CMD_GROUP_DISPLAY },
    { "fbinfo", handle_fbinfo, "fbinfo [fbX]", CMD_NONE, A90_CMD_GROUP_DISPLAY },
    { "kmsprobe", handle_kmsprobe, "kmsprobe", CMD_NONE, A90_CMD_GROUP_DISPLAY },
    { "kmssolid", handle_kmssolid, "kmssolid [color]", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "kmsframe", handle_kmsframe, "kmsframe", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "statusscreen", handle_statusscreen, "statusscreen", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "statushud", handle_statushud, "statushud", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "redraw", handle_statushud, "redraw", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "testpattern", handle_statusscreen, "testpattern", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "displaytest", handle_displaytest, "displaytest [0-3|colors|font|safe|layout]", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "cutoutcal", handle_cutoutcal, "cutoutcal [x y size]", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "watchhud", handle_watchhud, "watchhud [sec] [count]", CMD_DISPLAY | CMD_BLOCKING, A90_CMD_GROUP_DISPLAY },
    { "autohud", handle_autohud, "autohud [sec]", CMD_BACKGROUND, A90_CMD_GROUP_DISPLAY },
    { "stophud", handle_stophud, "stophud", CMD_BACKGROUND, A90_CMD_GROUP_DISPLAY },
    { "clear", handle_clear, "clear", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY },
    { "inputscan", handle_inputscan, "inputscan [eventX]", CMD_NONE, A90_CMD_GROUP_INPUT },
    { "inputcaps", handle_inputcaps, "inputcaps <eventX>", CMD_NONE, A90_CMD_GROUP_INPUT },
    { "readinput", handle_readinput, "readinput <eventX> [count] [timeout_ms]", CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "doompad", handle_doompad, "doompad [status|reset|state <seq> <mask>|key <role> <0|1>|tap <role>]", CMD_NONE, A90_CMD_GROUP_INPUT },
    { "doominput", handle_doominput, "doominput <eventX> [count] [timeout_ms]", CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "doominputmux", handle_doominputmux, "doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]", CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "waitkey", handle_waitkey, "waitkey [count]", CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "inputlayout", handle_inputlayout, "inputlayout", CMD_NONE, A90_CMD_GROUP_INPUT },
    { "waitgesture", handle_waitgesture, "waitgesture [count]", CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "inputmonitor", handle_inputmonitor, "inputmonitor [events]", CMD_DISPLAY | CMD_BLOCKING, A90_CMD_GROUP_INPUT },
    { "screenmenu", handle_screenmenu, "screenmenu", CMD_BACKGROUND, A90_CMD_GROUP_MENU },
    { "menu", handle_screenmenu, "menu", CMD_BACKGROUND, A90_CMD_GROUP_MENU },
    { "screenapp", handle_screenapp, "screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]", CMD_DISPLAY, A90_CMD_GROUP_MENU },
    { "hide", handle_hide_menu, "hide", CMD_BACKGROUND, A90_CMD_GROUP_MENU },
    { "hidemenu", handle_hide_menu, "hidemenu", CMD_BACKGROUND, A90_CMD_GROUP_MENU },
    { "resume", handle_hide_menu, "resume", CMD_BACKGROUND, A90_CMD_GROUP_MENU },
    { "blindmenu", handle_blindmenu, "blindmenu", CMD_BLOCKING | CMD_DANGEROUS, A90_CMD_GROUP_MENU },
    { "mkdir", handle_mkdir, "mkdir <dir>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "mknodc", handle_mknodc, "mknodc <path> <major> <minor>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "mknodb", handle_mknodb, "mknodb <path> <major> <minor>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "mountfs", handle_mountfs, "mountfs <src> <dst> <type> [ro]", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "umount", handle_umount, "umount <path>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "echo", handle_echo, "echo <text>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "writefile", handle_writefile, "writefile <path> <value...>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "appendfile", handle_appendfile, "appendfile <path> <value...>", CMD_NONE, A90_CMD_GROUP_FILESYSTEM },
    { "cpustress", handle_cpustress, "cpustress [sec] [workers]", CMD_BLOCKING, A90_CMD_GROUP_PROCESS },
    { "run", handle_run, "run <path> [args...]", CMD_BLOCKING, A90_CMD_GROUP_PROCESS },
    { "runandroid", handle_runandroid, "runandroid <path> [args...]", CMD_BLOCKING, A90_CMD_GROUP_ANDROID },
    { "startadbd", handle_startadbd, "startadbd", CMD_BACKGROUND, A90_CMD_GROUP_ANDROID },
    { "stopadbd", handle_stopadbd, "stopadbd", CMD_BACKGROUND, A90_CMD_GROUP_ANDROID },
    { "netservice", handle_netservice, "netservice [status|start|stop|enable|disable|token [show|rotate]]", CMD_DANGEROUS, A90_CMD_GROUP_NETWORK },
    { "rshell", handle_rshell, "rshell [status|audit|start|stop|enable|disable|token [show]|rotate-token [value]]", CMD_DANGEROUS, A90_CMD_GROUP_NETWORK },
    { "longsoak", handle_longsoak, "longsoak [status [verbose]|start [interval]|stop|path|tail [lines]]", CMD_BACKGROUND, A90_CMD_GROUP_SERVICE },
    { "service", handle_service, "service [list|status|start|stop|enable|disable] [name]", CMD_DANGEROUS, A90_CMD_GROUP_SERVICE },
    { "reattach", handle_reattach, "reattach", CMD_NONE, A90_CMD_GROUP_SERVICE },
    { "usbacmreset", handle_usbacmreset, "usbacmreset", CMD_DANGEROUS, A90_CMD_GROUP_SERVICE },
    { "sync", handle_sync, "sync", CMD_NONE, A90_CMD_GROUP_SERVICE },
    { "reboot", handle_reboot, "reboot", CMD_DANGEROUS | CMD_NO_DONE, A90_CMD_GROUP_POWER },
    { "recovery", handle_recovery, "recovery", CMD_DANGEROUS | CMD_NO_DONE, A90_CMD_GROUP_POWER },
    { "poweroff", handle_poweroff, "poweroff", CMD_DANGEROUS | CMD_NO_DONE, A90_CMD_GROUP_POWER },
};

static void refresh_pid1_guard(void) {
    (void)a90_pid1_guard_run(command_table,
            sizeof(command_table) / sizeof(command_table[0]));
}

static int handle_cmdmeta(char **argv, int argc) {
    if (argc > 2 ||
        (argc == 2 && strcmp(argv[1], "verbose") != 0)) {
        a90_console_printf("usage: cmdmeta [verbose]\r\n");
        return -EINVAL;
    }
    if (argc == 2) {
        a90_shell_print_command_inventory(command_table,
                                          sizeof(command_table) / sizeof(command_table[0]));
    } else {
        a90_shell_print_command_stats(command_table,
                                      sizeof(command_table) / sizeof(command_table[0]));
    }
    return 0;
}

static int handle_cmdgroups(char **argv, int argc) {
    if (argc > 2 ||
        (argc == 2 && strcmp(argv[1], "verbose") != 0)) {
        a90_console_printf("usage: cmdgroups [verbose]\r\n");
        return -EINVAL;
    }
    if (argc == 2) {
        a90_shell_print_group_inventory(command_table,
                                        sizeof(command_table) / sizeof(command_table[0]));
    } else {
        a90_shell_print_group_stats(command_table,
                                    sizeof(command_table) / sizeof(command_table[0]));
    }
    return 0;
}

static const char *policy_reason_name(enum a90_controller_busy_reason reason) {
    switch (reason) {
    case A90_CONTROLLER_BUSY_NONE:
        return "none";
    case A90_CONTROLLER_BUSY_AUTO_MENU:
        return "auto-menu";
    case A90_CONTROLLER_BUSY_DANGEROUS:
        return "dangerous";
    case A90_CONTROLLER_BUSY_POWER:
        return "power";
    default:
        return "unknown";
    }
}

static int handle_policycheck(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";
    char summary[128];
    int rc;

    if (argc > 2) {
        a90_console_printf("usage: policycheck [status|run|verbose]\r\n");
        return -EINVAL;
    }
    if (strcmp(subcommand, "status") != 0 &&
        strcmp(subcommand, "run") != 0 &&
        strcmp(subcommand, "verbose") != 0) {
        a90_console_printf("usage: policycheck [status|run|verbose]\r\n");
        return -EINVAL;
    }

    rc = a90_controller_policy_matrix_run(command_table,
            sizeof(command_table) / sizeof(command_table[0]));
    a90_controller_policy_matrix_summary(summary, sizeof(summary));
    a90_console_printf("policycheck: %s\r\n", summary);

    if (strcmp(subcommand, "verbose") == 0) {
        size_t index;
        size_t count = a90_controller_policy_matrix_count();

        for (index = 0; index < count; ++index) {
            const struct a90_controller_policy_result *entry =
                    a90_controller_policy_matrix_entry_at(index);
            char flags[80];

            if (entry == NULL) {
                continue;
            }
            a90_shell_format_flags(entry->flags, flags, sizeof(flags));
            a90_console_printf("policycheck: %02ld %s scope=%s expect=%s actual=%s reason=%s flags=%s cmd=%s\r\n",
                    (long)index,
                    entry->expected_allowed == entry->actual_allowed ? "PASS" : "FAIL",
                    entry->power_page ? "power" : "menu",
                    entry->expected_allowed ? "allow" : "block",
                    entry->actual_allowed ? "allow" : "block",
                    policy_reason_name(entry->reason),
                    flags,
                    entry->label);
        }
    }

    if (rc < 0) {
        return rc;
    }
    return 0;
}

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
        (void)a90_reaper_reap_orphans("cmd-unknown");
        return result;
    }

    busy_reason = a90_controller_command_busy_reason_ex(argv[0],
                                                        command->flags,
                                                        argc,
                                                        argv,
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
        (void)a90_reaper_reap_orphans("cmd-busy");
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
    (void)a90_reaper_reap_orphans("cmd-end");
    return result;
}

static void shell_loop(void) {
    char line[CONSOLE_LINE_MAX];

    print_shell_intro();

    while (1) {
        char *argv[32];
        int argc;

        (void)a90_reaper_reap_orphans("shell-prompt");
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
