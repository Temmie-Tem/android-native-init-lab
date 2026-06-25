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

struct gpu_g2_gpuobj_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int alloc_rc;
    int alloc_errno;
    int mmap_attempted;
    int mmap_rc;
    int mmap_errno;
    int mmap_nonnull;
    int mmap_access_attempted;
    int munmap_attempted;
    int munmap_rc;
    int munmap_errno;
    int free_attempted;
    int free_rc;
    int free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int flags_in;
    unsigned int flags_out;
    unsigned int gpuobj_id;
    uint64_t alloc_size_in;
    uint64_t alloc_size_out;
    uint64_t alloc_flags_in;
    uint64_t alloc_flags_out;
    uint64_t alloc_va_len;
    uint64_t alloc_mmapsize;
    uint64_t mmap_len;
    uint64_t mmap_offset;
    long open_elapsed_ms;
    long create_elapsed_ms;
    long alloc_elapsed_ms;
    long mmap_elapsed_ms;
    long munmap_elapsed_ms;
    long free_elapsed_ms;
    long destroy_elapsed_ms;
    long total_elapsed_ms;
};

struct gpu_g3_noop_submit_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int alloc_rc;
    int alloc_errno;
    int info_rc;
    int info_errno;
    int mmap_rc;
    int mmap_errno;
    int mmap_nonnull;
    int mapped_write_attempted;
    int mapped_write_rc;
    int sync_rc;
    int sync_errno;
    int submit_rc;
    int submit_errno;
    int timestamp_event_rc;
    int timestamp_event_errno;
    int wait_rc;
    int wait_errno;
    int readtimestamp_rc;
    int readtimestamp_errno;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int munmap_attempted;
    int munmap_rc;
    int munmap_errno;
    int free_attempted;
    int free_deferred;
    int free_rc;
    int free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int flags_in;
    unsigned int flags_out;
    unsigned int gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int noop_dwords;
    unsigned int noop_header;
    unsigned int noop_payload;
    int fence_fd;
    uint64_t alloc_size_in;
    uint64_t alloc_size_out;
    uint64_t alloc_flags_in;
    uint64_t alloc_flags_out;
    uint64_t alloc_va_len;
    uint64_t alloc_mmapsize;
    uint64_t info_gpuaddr;
    uint64_t info_flags;
    uint64_t info_size;
    uint64_t info_va_len;
    uint64_t mmap_len;
    uint64_t mmap_offset;
    uint64_t cmd_gpuaddr;
    uint64_t cmd_size;
    uint64_t sync_length;
    long open_elapsed_ms;
    long create_elapsed_ms;
    long alloc_elapsed_ms;
    long info_elapsed_ms;
    long mmap_elapsed_ms;
    long sync_elapsed_ms;
    long submit_elapsed_ms;
    long timestamp_event_elapsed_ms;
    long wait_elapsed_ms;
    long readtimestamp_elapsed_ms;
    long munmap_elapsed_ms;
    long free_elapsed_ms;
    long destroy_elapsed_ms;
    long total_elapsed_ms;
};

struct gpu_g4_solid_fill_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int cmd_alloc_rc;
    int cmd_alloc_errno;
    int cmd_info_rc;
    int cmd_info_errno;
    int cmd_mmap_rc;
    int cmd_mmap_errno;
    int cmd_mmap_nonnull;
    int dst_alloc_rc;
    int dst_alloc_errno;
    int dst_info_rc;
    int dst_info_errno;
    int dst_mmap_rc;
    int dst_mmap_errno;
    int dst_mmap_nonnull;
    int event_alloc_rc;
    int event_alloc_errno;
    int event_info_rc;
    int event_info_errno;
    int dst_prefill_attempted;
    int dst_prefill_rc;
    int cmd_write_attempted;
    int cmd_write_rc;
    int cmd_sync_rc;
    int cmd_sync_errno;
    int submit_rc;
    int submit_errno;
    int timestamp_event_rc;
    int timestamp_event_errno;
    int wait_rc;
    int wait_errno;
    int readtimestamp_rc;
    int readtimestamp_errno;
    int readback_sync_rc;
    int readback_sync_errno;
    int readback_verify_attempted;
    int readback_verified;
    int readback_mismatch_count;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int cmd_munmap_attempted;
    int cmd_munmap_rc;
    int cmd_munmap_errno;
    int dst_munmap_attempted;
    int dst_munmap_rc;
    int dst_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int dst_free_attempted;
    int dst_free_deferred;
    int dst_free_rc;
    int dst_free_errno;
    int event_free_attempted;
    int event_free_deferred;
    int event_free_rc;
    int event_free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int flags_in;
    unsigned int flags_out;
    unsigned int cmd_gpuobj_id;
    unsigned int dst_gpuobj_id;
    unsigned int event_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int expected_fill;
    unsigned int sentinel;
    unsigned int readback0;
    unsigned int readback1;
    unsigned int readback2;
    unsigned int readback3;
    unsigned int rb_dbg_eco_skipped;
    int fence_fd;
    uint64_t cmd_alloc_size_in;
    uint64_t cmd_alloc_size_out;
    uint64_t cmd_alloc_flags_in;
    uint64_t cmd_alloc_flags_out;
    uint64_t cmd_alloc_va_len;
    uint64_t cmd_alloc_mmapsize;
    uint64_t cmd_info_gpuaddr;
    uint64_t cmd_info_flags;
    uint64_t cmd_info_size;
    uint64_t cmd_info_va_len;
    uint64_t cmd_mmap_len;
    uint64_t cmd_mmap_offset;
    uint64_t cmd_gpuaddr;
    uint64_t cmd_size;
    uint64_t dst_alloc_size_in;
    uint64_t dst_alloc_size_out;
    uint64_t dst_alloc_flags_in;
    uint64_t dst_alloc_flags_out;
    uint64_t dst_alloc_va_len;
    uint64_t dst_alloc_mmapsize;
    uint64_t dst_info_gpuaddr;
    uint64_t dst_info_flags;
    uint64_t dst_info_size;
    uint64_t dst_info_va_len;
    uint64_t dst_mmap_len;
    uint64_t dst_mmap_offset;
    uint64_t dst_gpuaddr;
    uint64_t dst_base_encoded;
    uint64_t dst_size;
    uint64_t event_alloc_size_in;
    uint64_t event_alloc_size_out;
    uint64_t event_alloc_flags_in;
    uint64_t event_alloc_flags_out;
    uint64_t event_alloc_va_len;
    uint64_t event_alloc_mmapsize;
    uint64_t event_info_gpuaddr;
    uint64_t event_info_flags;
    uint64_t event_info_size;
    uint64_t event_info_va_len;
    uint64_t event_gpuaddr;
    uint64_t cmd_sync_length;
    uint64_t readback_sync_length;
    long open_elapsed_ms;
    long create_elapsed_ms;
    long cmd_alloc_elapsed_ms;
    long cmd_info_elapsed_ms;
    long cmd_mmap_elapsed_ms;
    long dst_alloc_elapsed_ms;
    long dst_info_elapsed_ms;
    long dst_mmap_elapsed_ms;
    long event_alloc_elapsed_ms;
    long event_info_elapsed_ms;
    long cmd_sync_elapsed_ms;
    long submit_elapsed_ms;
    long timestamp_event_elapsed_ms;
    long wait_elapsed_ms;
    long readtimestamp_elapsed_ms;
    long readback_sync_elapsed_ms;
    long cmd_munmap_elapsed_ms;
    long dst_munmap_elapsed_ms;
    long cmd_free_elapsed_ms;
    long dst_free_elapsed_ms;
    long event_free_elapsed_ms;
    long destroy_elapsed_ms;
    long total_elapsed_ms;
};

struct gpu_h1_shader_state_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int cmd_alloc_rc;
    int cmd_alloc_errno;
    int cmd_info_rc;
    int cmd_info_errno;
    int cmd_mmap_rc;
    int cmd_mmap_errno;
    int vs_alloc_rc;
    int vs_alloc_errno;
    int vs_info_rc;
    int vs_info_errno;
    int vs_mmap_rc;
    int vs_mmap_errno;
    int fs_alloc_rc;
    int fs_alloc_errno;
    int fs_info_rc;
    int fs_info_errno;
    int fs_mmap_rc;
    int fs_mmap_errno;
    int shader_write_attempted;
    int shader_write_rc;
    int cmd_write_attempted;
    int cmd_write_rc;
    int sync_rc;
    int sync_errno;
    int submit_rc;
    int submit_errno;
    int timestamp_event_rc;
    int timestamp_event_errno;
    int wait_rc;
    int wait_errno;
    int readtimestamp_rc;
    int readtimestamp_errno;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int cmd_munmap_attempted;
    int cmd_munmap_rc;
    int cmd_munmap_errno;
    int vs_munmap_attempted;
    int vs_munmap_rc;
    int vs_munmap_errno;
    int fs_munmap_attempted;
    int fs_munmap_rc;
    int fs_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int vs_free_attempted;
    int vs_free_deferred;
    int vs_free_rc;
    int vs_free_errno;
    int fs_free_attempted;
    int fs_free_deferred;
    int fs_free_rc;
    int fs_free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int flags_in;
    unsigned int flags_out;
    unsigned int cmd_gpuobj_id;
    unsigned int vs_gpuobj_id;
    unsigned int fs_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int vs_shader_dwords;
    unsigned int fs_shader_dwords;
    unsigned int cp_load_state6_geom;
    unsigned int cp_load_state6_frag;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t vs_info_gpuaddr;
    uint64_t fs_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t vs_mmap_len;
    uint64_t fs_mmap_len;
    uint64_t cmd_sync_length;
    uint64_t vs_sync_length;
    uint64_t fs_sync_length;
    long open_elapsed_ms;
    long create_elapsed_ms;
    long cmd_alloc_elapsed_ms;
    long cmd_info_elapsed_ms;
    long cmd_mmap_elapsed_ms;
    long vs_alloc_elapsed_ms;
    long vs_info_elapsed_ms;
    long vs_mmap_elapsed_ms;
    long fs_alloc_elapsed_ms;
    long fs_info_elapsed_ms;
    long fs_mmap_elapsed_ms;
    long sync_elapsed_ms;
    long submit_elapsed_ms;
    long timestamp_event_elapsed_ms;
    long wait_elapsed_ms;
    long readtimestamp_elapsed_ms;
    long cmd_munmap_elapsed_ms;
    long vs_munmap_elapsed_ms;
    long fs_munmap_elapsed_ms;
    long cmd_free_elapsed_ms;
    long vs_free_elapsed_ms;
    long fs_free_elapsed_ms;
    long destroy_elapsed_ms;
    long total_elapsed_ms;
};

struct gpu_h2_3d_state_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int cmd_alloc_rc;
    int cmd_alloc_errno;
    int cmd_info_rc;
    int cmd_info_errno;
    int cmd_mmap_rc;
    int cmd_mmap_errno;
    int color_alloc_rc;
    int color_alloc_errno;
    int color_info_rc;
    int color_info_errno;
    int color_mmap_rc;
    int color_mmap_errno;
    int color_init_rc;
    int cmd_write_rc;
    int sync_rc;
    int sync_errno;
    int submit_rc;
    int submit_errno;
    int timestamp_event_rc;
    int timestamp_event_errno;
    int wait_rc;
    int wait_errno;
    int readtimestamp_rc;
    int readtimestamp_errno;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int cmd_munmap_attempted;
    int cmd_munmap_rc;
    int cmd_munmap_errno;
    int color_munmap_attempted;
    int color_munmap_rc;
    int color_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int color_free_attempted;
    int color_free_deferred;
    int color_free_rc;
    int color_free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int cmd_gpuobj_id;
    unsigned int color_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int state_reg_writes;
    unsigned int color_width;
    unsigned int color_height;
    unsigned int color_stride;
    unsigned int color_format;
    unsigned int draw_attempted;
    unsigned int shader_execution_attempted;
    unsigned int kms_blit_attempted;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t color_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t color_mmap_len;
    uint64_t color_bytes;
    uint64_t cmd_sync_length;
    uint64_t color_sync_length;
    long total_elapsed_ms;
};

struct gpu_h3_draw_envelope_probe_result {
    int version;
    int open_rc;
    int open_errno;
    int create_rc;
    int create_errno;
    int cmd_alloc_rc;
    int cmd_alloc_errno;
    int cmd_info_rc;
    int cmd_info_errno;
    int cmd_mmap_rc;
    int cmd_mmap_errno;
    int color_alloc_rc;
    int color_alloc_errno;
    int color_info_rc;
    int color_info_errno;
    int color_mmap_rc;
    int color_mmap_errno;
    int event_alloc_rc;
    int event_alloc_errno;
    int event_info_rc;
    int event_info_errno;
    int vs_alloc_rc;
    int vs_alloc_errno;
    int vs_info_rc;
    int vs_info_errno;
    int vs_mmap_rc;
    int vs_mmap_errno;
    int fs_alloc_rc;
    int fs_alloc_errno;
    int fs_info_rc;
    int fs_info_errno;
    int fs_mmap_rc;
    int fs_mmap_errno;
    int vertex_alloc_rc;
    int vertex_alloc_errno;
    int vertex_info_rc;
    int vertex_info_errno;
    int vertex_mmap_rc;
    int vertex_mmap_errno;
    int color_init_rc;
    int shader_write_rc;
    int vertex_write_rc;
    int cmd_write_rc;
    int sync_rc;
    int sync_errno;
    int submit_rc;
    int submit_errno;
    int timestamp_event_rc;
    int timestamp_event_errno;
    int wait_rc;
    int wait_errno;
    int readtimestamp_rc;
    int readtimestamp_errno;
    int readback_sync_rc;
    int readback_sync_errno;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int cmd_munmap_attempted;
    int cmd_munmap_rc;
    int cmd_munmap_errno;
    int color_munmap_attempted;
    int color_munmap_rc;
    int color_munmap_errno;
    int vs_munmap_attempted;
    int vs_munmap_rc;
    int vs_munmap_errno;
    int fs_munmap_attempted;
    int fs_munmap_rc;
    int fs_munmap_errno;
    int vertex_munmap_attempted;
    int vertex_munmap_rc;
    int vertex_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int color_free_attempted;
    int color_free_deferred;
    int color_free_rc;
    int color_free_errno;
    int event_free_attempted;
    int event_free_deferred;
    int event_free_rc;
    int event_free_errno;
    int vs_free_attempted;
    int vs_free_deferred;
    int vs_free_rc;
    int vs_free_errno;
    int fs_free_attempted;
    int fs_free_deferred;
    int fs_free_rc;
    int fs_free_errno;
    int vertex_free_attempted;
    int vertex_free_deferred;
    int vertex_free_rc;
    int vertex_free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int cmd_gpuobj_id;
    unsigned int color_gpuobj_id;
    unsigned int event_gpuobj_id;
    unsigned int vs_gpuobj_id;
    unsigned int fs_gpuobj_id;
    unsigned int vertex_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int state_reg_writes;
    unsigned int vfd_reg_writes;
    unsigned int color_width;
    unsigned int color_height;
    unsigned int color_stride;
    unsigned int color_format;
    unsigned int vertex_stride;
    unsigned int vertex_bytes;
    unsigned int vertex_count;
    unsigned int vertex_format;
    unsigned int cp_draw_packet;
    unsigned int draw_initiator;
    unsigned int num_instances;
    unsigned int num_indices;
    unsigned int draw_attempted;
    unsigned int shader_execution_attempted;
    unsigned int kms_blit_attempted;
    unsigned int readback_changed_count;
    unsigned int readback_first_changed_index;
    uint32_t readback0;
    uint32_t readback_center;
    uint32_t readback_first_changed_value;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t color_info_gpuaddr;
    uint64_t event_info_gpuaddr;
    uint64_t vs_info_gpuaddr;
    uint64_t fs_info_gpuaddr;
    uint64_t vertex_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t color_mmap_len;
    uint64_t event_size;
    uint64_t vs_mmap_len;
    uint64_t fs_mmap_len;
    uint64_t vertex_mmap_len;
    uint64_t color_bytes;
    uint64_t cmd_sync_length;
    uint64_t color_sync_length;
    uint64_t event_sync_length;
    uint64_t vs_sync_length;
    uint64_t fs_sync_length;
    uint64_t vertex_sync_length;
    uint64_t readback_sync_length;
    long total_elapsed_ms;
};

struct gpu_g4_solid_fill_child_run {
    struct gpu_g4_solid_fill_probe_result result;
    pid_t child_pid;
    bool got_result;
    bool timed_out;
    bool child_killed;
    bool child_reaped;
    int child_status;
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
#define GPU_G2_GPUOBJ_ALLOC_SIZE 4096ULL
#define GPU_G2_GPUOBJ_ALLOC_FLAGS 0ULL
#define GPU_G2_MMAP_PAGE_SIZE 4096ULL
#define GPU_G3_NOOP_ALLOC_SIZE 4096ULL
#define GPU_G3_NOOP_ALLOC_FLAGS 0ULL
#define GPU_G3_NOOP_DWORDS 2U
#define GPU_G3_NOOP_BYTES ((uint64_t)GPU_G3_NOOP_DWORDS * 4ULL)
#define GPU_G3_WAIT_TIMEOUT_MS 1000U
#define GPU_G3_PM4_CP_TYPE7_PKT 0x70000000U
#define GPU_G3_PM4_CP_TYPE4_PKT 0x40000000U
#define GPU_G3_PM4_CP_NOP 0x10U
#define GPU_G4_CMD_ALLOC_SIZE 4096ULL
#define GPU_G4_DST_ALLOC_SIZE 4096ULL
#define GPU_G4_EVENT_ALLOC_SIZE 4096ULL
#define GPU_G4_ALLOC_FLAGS 0ULL
#define GPU_G4_WAIT_TIMEOUT_MS 1000U
#define GPU_G4_CMD_MAX_DWORDS 256U
#define GPU_G4_FILL_BYTES 256ULL
#define GPU_G4_FILL_DWORDS ((unsigned int)(GPU_G4_FILL_BYTES / 4ULL))
#define GPU_G4_READBACK_DWORDS 16U
#define GPU_G5_MIN_PATCH_PIXELS 128U
#define GPU_G4_FILL_PATTERN 0xa5c3f00dU
#define GPU_G4_SENTINEL_PATTERN 0x11111111U
#define GPU_G4_A6XX_FMT6_32_FLOAT 0x4aU
#define GPU_G4_A6XX_FMT6_32_UINT 0x4bU
#define GPU_G4_A6XX_R2D_INT32 0x7U
#define GPU_G4_A6XX_OUTPUT_IFMT_2D_UINT 0x2U
#define GPU_G4_A6XX_TILE6_LINEAR 0x0U
#define GPU_G4_A3XX_COLOR_SWAP_WZYX 0x0U
#define GPU_G4_A6XX_ROTATE_0 0x0U
#define GPU_G4_A6XX_CP_SET_MARKER_RM6_BLIT2DSCALE 12U
#define GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER 1U
#define GPU_G4_A6XX_CP_BLIT_OP_SCALE 3U
#define GPU_G4_EVENT_SEQNO_VALUE 0x32020001U
#define GPU_G4_CP_EVENT_WRITE_TIMESTAMP_BIT (1U << 30)
#define GPU_G4_PM4_CP_WAIT_FOR_IDLE 0x26U
#define GPU_G4_PM4_CP_BLIT 0x2cU
#define GPU_G4_PM4_CP_EVENT_WRITE 0x46U
#define GPU_G4_PM4_CP_SET_MARKER 0x65U
#define GPU_G4_EVENT_CACHE_FLUSH_TS 0x04U
#define GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS 0x1dU
#define GPU_G4_EVENT_CACHE_INVALIDATE 0x31U
#define GPU_G4_EVENT_DEBUG_LABEL 0x3fU
#define GPU_H1_CMD_ALLOC_SIZE 4096ULL
#define GPU_H1_SHADER_ALLOC_SIZE 4096ULL
#define GPU_H1_WAIT_TIMEOUT_MS 1000U
#define GPU_H1_CMD_MAX_DWORDS 96U
#define GPU_H1_VS_SHADER_DWORDS 8U
#define GPU_H1_FS_SHADER_DWORDS 8U
#define GPU_H1_SP_CONFIG_ENABLED (1U << 8)
#define GPU_H1_IR3_END_LO 0x00000000U
#define GPU_H1_IR3_END_HI 0x03000000U
#define GPU_H3_IR3_F32_0_LO 0x00000000U
#define GPU_H3_IR3_F32_1_LO 0x3f800000U
#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO 0x00000000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO 0x00000001U
#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_LO 0x00000000U
#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_LO 0x00000001U
#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI 0x20044000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI 0x20044001U
#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_HI 0x20044004U
#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_HI 0x20044005U
#define GPU_H3_IR3_MOV_F32F32_R0X_HI 0x20444000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_HI 0x20444001U
#define GPU_H3_IR3_MOV_F32F32_R0Z_HI 0x20444002U
#define GPU_H3_IR3_MOV_F32F32_R0W_HI 0x20444003U
#define GPU_H3_IR3_MOV_F32F32_R1X_HI 0x20444004U
#define GPU_H3_IR3_MOV_F32F32_R1Z_HI 0x20444006U
#define GPU_H3_IR3_MOV_F32F32_R1W_HI 0x20444007U
#define GPU_H1_CP_LOAD_STATE6_STATE_SRC_INDIRECT (2U << 16)
#define GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER (8U << 18)
#define GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER (12U << 18)
#define GPU_H1_PM4_CP_LOAD_STATE6_GEOM 0x32U
#define GPU_H1_PM4_CP_LOAD_STATE6_FRAG 0x34U
#define GPU_H2_CMD_ALLOC_SIZE 4096ULL
#define GPU_H2_COLOR_WIDTH 128U
#define GPU_H2_COLOR_HEIGHT 128U
#define GPU_H2_COLOR_BPP 4U
#define GPU_H2_COLOR_STRIDE (GPU_H2_COLOR_WIDTH * GPU_H2_COLOR_BPP)
#define GPU_H2_COLOR_ALLOC_SIZE ((uint64_t)GPU_H2_COLOR_STRIDE * GPU_H2_COLOR_HEIGHT)
#define GPU_H2_CMD_MAX_DWORDS 160U
#define GPU_H2_WAIT_TIMEOUT_MS 1000U
#define GPU_H2_CLEAR_PATTERN 0x20202020U
#define GPU_H3_CMD_ALLOC_SIZE 8192ULL
#define GPU_H3_VERTEX_ALLOC_SIZE 4096ULL
#define GPU_H3_EVENT_ALLOC_SIZE 4096ULL
#define GPU_H3_WAIT_TIMEOUT_MS 1000U
#define GPU_H3_VERTEX_COUNT 3U
#define GPU_H3_VERTEX_STRIDE 8U
#define GPU_H3_VERTEX_DWORDS (GPU_H3_VERTEX_COUNT * 2U)
#define GPU_H3_VERTEX_BYTES ((uint64_t)GPU_H3_VERTEX_DWORDS * 4ULL)
#define GPU_H3_A6XX_FMT6_32_32_FLOAT 0x67U
#define GPU_H3_COLOR_FORMAT GPU_G4_A6XX_FMT6_32_FLOAT
#define GPU_H3_COLOR_OUTPUT_MASK 0xfU
#define GPU_H3_VS_SHADER_DWORDS 12U
#define GPU_H3_FS_SHADER_DWORDS 8U
#define GPU_H3_VS_OUTPUT_REGID 0U
#define GPU_H3_PS_OUTPUT_REGID 0U
#define GPU_H3_SP_VS_OUTPUT_REG0 \
    ((GPU_H3_VS_OUTPUT_REGID & 0xffU) | (0xfU << 8))
#define GPU_H3_PM4_CP_DRAW_INDX_OFFSET 0x38U
#define GPU_H3_DI_PT_TRILIST 4U
#define GPU_H3_DI_SRC_SEL_AUTO_INDEX 2U
#define GPU_H3_IGNORE_VISIBILITY 0U
#define GPU_H3_INDEX_SIZE_IGN 0U
#define GPU_H3_SP_FULLREGFOOTPRINT 2U
#define GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(n) (((n) & 0x3fU) << 7)
#define GPU_H3_SP_VS_CNTL_0_MERGEDREGS (1U << 20)
#define GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP (1U << 24)
#define GPU_H3_SP_PS_CNTL_0_MERGEDREGS (1U << 31)
#define GPU_H3_SP_VS_CNTL_0 \
    (GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(GPU_H3_SP_FULLREGFOOTPRINT) | \
     GPU_H3_SP_VS_CNTL_0_MERGEDREGS)
#define GPU_H3_SP_PS_CNTL_0 \
    (GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(GPU_H3_SP_FULLREGFOOTPRINT) | \
     GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP | \
     GPU_H3_SP_PS_CNTL_0_MERGEDREGS)
#define GPU_H3_GRAS_CL_INTERP_CNTL 0x00000000U
#define GPU_H3_GRAS_LRZ_PS_INPUT_CNTL 0x00000000U
#define GPU_H3_GRAS_LRZ_PS_SAMPLEFREQ_CNTL 0x00000000U
#define GPU_H3_RB_INTERP_CNTL 0x00000000U
#define GPU_H3_RB_PS_INPUT_CNTL 0x00000000U
#define GPU_H3_RB_PS_SAMPLEFREQ_CNTL 0x00000000U
#define GPU_H3_GRAS_SC_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_RENDER_CNTL 0x00000010U
#define GPU_H3_TPL1_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_CCU_CNTL 0x10000000U
#define GPU_H3_RB_CCU_COLOR_OFFSET 0x00020000U
#define GPU_H3_RB_CCU_DEPTH_OFFSET 0x00000000U
#define GPU_H3_VPC_VS_CNTL (4U | (0U << 8) | (0xffU << 16))
#define GPU_H3_VPC_VS_CLIP_CULL_CNTL ((0xffU << 8) | (0xffU << 16))
#define GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE 0U
#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0 0xfffffff0U
#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL1 0xffffffffU
#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL2 0xffffffffU
#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL3 0xffffffffU
#define GPU_H3_VPC_VS_SIV_CNTL 0x0000ffffU
#define GPU_H3_VPC_VS_SIV_CNTL_V2 0x0000ffffU
#define GPU_H3_GRAS_SU_VS_SIV_CNTL 0x00000000U
#define GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL 0x00000000U
#define GPU_H3_VPC_RAST_STREAM_CNTL 0x00000000U
#define GPU_H3_VPC_SO_OVERRIDE 0x00000001U
#define GPU_H3_PC_STEREO_RENDERING_CNTL 0x00000000U
#define GPU_H3_TPL1_PS_SWIZZLE_CNTL 0x00000000U
#define GPU_H3_VPC_UNKNOWN_9210 0x00000000U
#define GPU_H3_SP_INVALID_REG 0xfcU
#define GPU_H3_SP_REG_PROG_ID_3 \
    ((GPU_H3_SP_INVALID_REG << 0) | (GPU_H3_SP_INVALID_REG << 8))
#define GPU_G4_REG_GRAS_A2D_BLT_CNTL 0x8400U
#define GPU_G4_REG_GRAS_A2D_DEST_TL 0x8405U
#define GPU_G4_REG_GRAS_A2D_DEST_BR 0x8406U
#define GPU_G4_REG_RB_A2D_BLT_CNTL 0x8c00U
#define GPU_G4_REG_RB_A2D_PIXEL_CNTL 0x8c01U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_INFO 0x8c17U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_BASE 0x8c18U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_PITCH 0x8c1aU
#define GPU_G4_REG_RB_A2D_CLEAR_COLOR_DW0 0x8c2cU
#define GPU_G4_REG_SP_A2D_OUTPUT_INFO 0xacc0U
#define GPU_H1_REG_SP_VS_CNTL_0 0xa800U
#define GPU_H1_REG_SP_VS_PROGRAM_COUNTER_OFFSET 0xa81bU
#define GPU_H1_REG_SP_VS_BASE 0xa81cU
#define GPU_H1_REG_SP_VS_CONFIG 0xa823U
#define GPU_H1_REG_SP_VS_INSTR_SIZE 0xa824U
#define GPU_H1_REG_SP_PS_CNTL_0 0xa980U
#define GPU_H1_REG_SP_PS_PROGRAM_COUNTER_OFFSET 0xa982U
#define GPU_H1_REG_SP_PS_BASE 0xa983U
#define GPU_H1_REG_SP_PS_CONFIG 0xab04U
#define GPU_H1_REG_SP_PS_INSTR_SIZE 0xab05U
#define GPU_H3_REG_SP_MODE_CNTL 0xab00U
#define GPU_H3_REG_TPL1_MODE_CNTL 0xb309U
#define GPU_H3_SP_MODE_CNTL 0x00000005U
#define GPU_H3_TPL1_MODE_CNTL 0x000000a2U
#define GPU_H2_REG_GRAS_CL_CNTL 0x8000U
#define GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE 0x8001U
#define GPU_H2_REG_GRAS_CL_INTERP_CNTL 0x8005U
#define GPU_H2_REG_GRAS_CL_VIEWPORT 0x8010U
#define GPU_H2_REG_GRAS_CL_GUARDBAND_CLIP_ADJ 0x8006U
#define GPU_H2_REG_GRAS_SU_CNTL 0x8090U
#define GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL 0x8099U
#define GPU_H2_REG_GRAS_SU_VS_SIV_CNTL 0x809bU
#define GPU_H2_REG_GRAS_SC_CNTL 0x80a0U
#define GPU_H2_REG_GRAS_SC_RAS_MSAA_CNTL 0x80a2U
#define GPU_H2_REG_GRAS_SC_DEST_MSAA_CNTL 0x80a3U
#define GPU_H3_REG_GRAS_SC_MSAA_SAMPLE_POS_CNTL 0x80a4U
#define GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_CNTL 0x80afU
#define GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_TL 0x80b0U
#define GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_BR 0x80b1U
#define GPU_H2_REG_GRAS_SC_VIEWPORT_SCISSOR_TL 0x80d0U
#define GPU_H2_REG_GRAS_SC_VIEWPORT_SCISSOR_BR 0x80d1U
#define GPU_H2_REG_GRAS_SC_WINDOW_SCISSOR_TL 0x80f0U
#define GPU_H2_REG_GRAS_SC_WINDOW_SCISSOR_BR 0x80f1U
#define GPU_H2_REG_GRAS_LRZ_CNTL 0x8100U
#define GPU_H2_REG_GRAS_LRZ_PS_INPUT_CNTL 0x8101U
#define GPU_H2_REG_GRAS_LRZ_PS_SAMPLEFREQ_CNTL 0x8109U
#define GPU_H2_REG_GRAS_MODE_CNTL 0x8110U
#define GPU_H2_REG_RB_RENDER_CNTL 0x8801U
#define GPU_H2_REG_RB_RAS_MSAA_CNTL 0x8802U
#define GPU_H2_REG_RB_DEST_MSAA_CNTL 0x8803U
#define GPU_H3_REG_RB_MSAA_SAMPLE_POS_CNTL 0x8804U
#define GPU_H2_REG_RB_INTERP_CNTL 0x8809U
#define GPU_H2_REG_RB_PS_INPUT_CNTL 0x880aU
#define GPU_H2_REG_RB_PS_OUTPUT_CNTL 0x880bU
#define GPU_H2_REG_RB_PS_MRT_CNTL 0x880cU
#define GPU_H2_REG_RB_PS_OUTPUT_MASK 0x880dU
#define GPU_H2_REG_RB_SRGB_CNTL 0x880fU
#define GPU_H2_REG_RB_PS_SAMPLEFREQ_CNTL 0x8810U
#define GPU_H2_REG_RB_MODE_CNTL 0x8811U
#define GPU_H2_REG_RB_MRT0_CONTROL 0x8820U
#define GPU_H2_REG_RB_MRT0_BLEND_CONTROL 0x8821U
#define GPU_H2_REG_RB_MRT0_BUF_INFO 0x8822U
#define GPU_H2_REG_RB_MRT0_PITCH 0x8823U
#define GPU_H2_REG_RB_MRT0_ARRAY_PITCH 0x8824U
#define GPU_H2_REG_RB_MRT0_BASE 0x8825U
#define GPU_H2_REG_RB_MRT0_BASE_GMEM 0x8827U
#define GPU_H2_REG_RB_BLEND_CNTL 0x8865U
#define GPU_H2_REG_RB_DEPTH_CNTL 0x8871U
#define GPU_H2_REG_RB_STENCIL_CNTL 0x8880U
#define GPU_H2_REG_VPC_VARYING_INTERP_MODE_0 0x9200U
#define GPU_H2_REG_VPC_VARYING_REPLACE_MODE_0 0x9208U
#define GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL 0x9101U
#define GPU_H2_REG_VPC_VS_SIV_CNTL 0x9104U
#define GPU_H2_REG_VPC_VARYING_LM_TRANSFER_CNTL0 0x9212U
#define GPU_H3_REG_VPC_UNKNOWN_9210 0x9210U
#define GPU_H2_REG_VPC_REPLACE_MODE_CNTL 0x9236U
#define GPU_H2_REG_VPC_ROTATION_CNTL 0x9300U
#define GPU_H2_REG_VPC_VS_CNTL 0x9301U
#define GPU_H2_REG_VPC_PS_CNTL 0x9304U
#define GPU_H3_REG_VPC_SO_OVERRIDE 0x9306U
#define GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2 0x9311U
#define GPU_H2_REG_VPC_VS_SIV_CNTL_V2 0x9314U
#define GPU_H3_REG_VPC_RAST_STREAM_CNTL 0x9980U
#define GPU_H2_REG_PC_RESTART_INDEX 0x9803U
#define GPU_H2_REG_PC_MODE_CNTL 0x9804U
#define GPU_H2_REG_PC_CNTL 0x9b00U
#define GPU_H2_REG_PC_VS_CNTL 0x9b01U
#define GPU_H3_REG_PC_STEREO_RENDERING_CNTL 0x9b07U
#define GPU_H2_REG_VFD_CNTL_0 0xa000U
#define GPU_H2_REG_VFD_CNTL_1 0xa001U
#define GPU_H2_REG_VFD_MODE_CNTL 0xa009U
#define GPU_H2_REG_VFD_INDEX_OFFSET 0xa00eU
#define GPU_H2_REG_VFD_INSTANCE_START_OFFSET 0xa00fU
#define GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE 0xa010U
#define GPU_H3_REG_VFD_FETCH_INSTR0 0xa090U
#define GPU_H3_REG_VFD_DEST_CNTL0 0xa0d0U
#define GPU_H2_REG_SP_VS_OUTPUT_CNTL 0xa802U
#define GPU_H2_REG_SP_VS_OUTPUT_REG0 0xa803U
#define GPU_H2_REG_SP_VS_VPC_DEST_REG0 0xa813U
#define GPU_H2_REG_SP_BLEND_CNTL 0xa989U
#define GPU_H2_REG_SP_SRGB_CNTL 0xa98aU
#define GPU_H2_REG_SP_PS_OUTPUT_MASK 0xa98bU
#define GPU_H2_REG_SP_PS_OUTPUT_CNTL 0xa98cU
#define GPU_H2_REG_SP_PS_MRT_CNTL 0xa98dU
#define GPU_H2_REG_SP_PS_OUTPUT_REG0 0xa98eU
#define GPU_H2_REG_SP_PS_MRT_REG0 0xa996U
#define GPU_H3_REG_TPL1_MSAA_SAMPLE_POS_CNTL 0xb304U
#define GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL 0xb183U
#define GPU_H3_REG_SP_REG_PROG_ID_3 0xb986U
#define GPU_H3_REG_RB_CCU_CNTL 0x8e07U
#define GPU_KGSL_CMDLIST_IB 0x00000001U
#define GPU_KGSL_OBJLIST_MEMOBJ 0x00000008U
#define GPU_KGSL_GPUMEM_CACHE_TO_GPU (1U << 0)
#define GPU_KGSL_GPUMEM_CACHE_FROM_GPU (1U << 1)
#define GPU_KGSL_GPUMEM_CACHE_RANGE (1U << 31)
#define GPU_KGSL_TIMESTAMP_RETIRED 0x00000002U
#define GPU_KGSL_TIMESTAMP_EVENT_FENCE 2
#define GPU_KGSL_GPUOBJ_FREE_ON_EVENT 1ULL
#define GPU_KGSL_GPU_EVENT_TIMESTAMP 1U

struct gpu_kgsl_drawctxt_create {
    unsigned int flags;
    unsigned int drawctxt_id;
};

struct gpu_kgsl_drawctxt_destroy {
    unsigned int drawctxt_id;
};

struct gpu_kgsl_gpuobj_alloc {
    uint64_t size;
    uint64_t flags;
    uint64_t va_len;
    uint64_t mmapsize;
    unsigned int id;
    unsigned int metadata_len;
    uint64_t metadata;
};

struct gpu_kgsl_gpuobj_free {
    uint64_t flags;
    uint64_t priv;
    unsigned int id;
    unsigned int type;
    unsigned int len;
};

struct gpu_kgsl_gpuobj_info {
    uint64_t gpuaddr;
    uint64_t flags;
    uint64_t size;
    uint64_t va_len;
    uint64_t va_addr;
    unsigned int id;
};

struct gpu_kgsl_gpuobj_sync_obj {
    uint64_t offset;
    uint64_t length;
    unsigned int id;
    unsigned int op;
};

struct gpu_kgsl_gpuobj_sync {
    uint64_t objs;
    unsigned int obj_len;
    unsigned int count;
};

struct gpu_kgsl_command_object {
    uint64_t offset;
    uint64_t gpuaddr;
    uint64_t size;
    unsigned int flags;
    unsigned int id;
};

struct gpu_kgsl_gpu_command {
    uint64_t flags;
    uint64_t cmdlist;
    unsigned int cmdsize;
    unsigned int numcmds;
    uint64_t objlist;
    unsigned int objsize;
    unsigned int numobjs;
    uint64_t synclist;
    unsigned int syncsize;
    unsigned int numsyncs;
    unsigned int context_id;
    unsigned int timestamp;
};

struct gpu_kgsl_device_waittimestamp_ctxtid {
    unsigned int context_id;
    unsigned int timestamp;
    unsigned int timeout;
};

struct gpu_kgsl_cmdstream_readtimestamp_ctxtid {
    unsigned int context_id;
    unsigned int type;
    unsigned int timestamp;
};

struct gpu_kgsl_timestamp_event {
    int type;
    unsigned int timestamp;
    unsigned int context_id;
    void *priv;
    size_t len;
};

struct gpu_kgsl_timestamp_event_fence {
    int fence_fd;
};

struct gpu_kgsl_gpu_event_timestamp {
    unsigned int context_id;
    unsigned int timestamp;
};

#define GPU_IOCTL_KGSL_DRAWCTXT_CREATE \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x13, struct gpu_kgsl_drawctxt_create)
#define GPU_IOCTL_KGSL_DRAWCTXT_DESTROY \
    _IOW(GPU_KGSL_IOC_TYPE, 0x14, struct gpu_kgsl_drawctxt_destroy)
#define GPU_IOCTL_KGSL_GPUOBJ_ALLOC \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x45, struct gpu_kgsl_gpuobj_alloc)
#define GPU_IOCTL_KGSL_GPUOBJ_FREE \
    _IOW(GPU_KGSL_IOC_TYPE, 0x46, struct gpu_kgsl_gpuobj_free)
#define GPU_IOCTL_KGSL_GPUOBJ_INFO \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x47, struct gpu_kgsl_gpuobj_info)
#define GPU_IOCTL_KGSL_GPUOBJ_SYNC \
    _IOW(GPU_KGSL_IOC_TYPE, 0x49, struct gpu_kgsl_gpuobj_sync)
#define GPU_IOCTL_KGSL_GPU_COMMAND \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x4A, struct gpu_kgsl_gpu_command)
#define GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID \
    _IOW(GPU_KGSL_IOC_TYPE, 0x7, struct gpu_kgsl_device_waittimestamp_ctxtid)
#define GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x16, struct gpu_kgsl_cmdstream_readtimestamp_ctxtid)
#define GPU_IOCTL_KGSL_TIMESTAMP_EVENT \
    _IOWR(GPU_KGSL_IOC_TYPE, 0x33, struct gpu_kgsl_timestamp_event)

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

static unsigned int gpu_g3_pm4_odd_parity_bit(unsigned int value) {
    value ^= value >> 16;
    value ^= value >> 8;
    value ^= value >> 4;
    value &= 0xfU;
    return (~0x6996U >> value) & 1U;
}

static uint32_t gpu_g3_pm4_pkt7_hdr(uint8_t opcode, uint16_t count) {
    return GPU_G3_PM4_CP_TYPE7_PKT |
           (uint32_t)count |
           ((uint32_t)gpu_g3_pm4_odd_parity_bit(count) << 15) |
           (((uint32_t)opcode & 0x7fU) << 16) |
           ((uint32_t)gpu_g3_pm4_odd_parity_bit(opcode) << 23);
}

static uint32_t gpu_g4_pm4_pkt4_hdr(uint32_t reg, uint16_t count) {
    return GPU_G3_PM4_CP_TYPE4_PKT |
           (uint32_t)count |
           ((uint32_t)gpu_g3_pm4_odd_parity_bit(count) << 7) |
           ((reg & 0x3ffffU) << 8) |
           ((uint32_t)gpu_g3_pm4_odd_parity_bit(reg) << 27);
}

static bool gpu_g4_pm4_push(uint32_t *words, unsigned int *dwords, uint32_t value) {
    if (*dwords >= GPU_G4_CMD_MAX_DWORDS) {
        return false;
    }
    words[*dwords] = value;
    *dwords += 1;
    return true;
}

static bool gpu_g4_pm4_emit_pkt7(uint32_t *words,
                                 unsigned int *dwords,
                                 uint8_t opcode,
                                 uint16_t count) {
    return gpu_g4_pm4_push(words, dwords, gpu_g3_pm4_pkt7_hdr(opcode, count));
}

static bool gpu_g4_pm4_emit_event_ts(uint32_t *words,
                                     unsigned int *dwords,
                                     uint32_t event,
                                     uint64_t gpuaddr,
                                     uint32_t seqno) {
    return gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_EVENT_WRITE, 4) &&
           gpu_g4_pm4_push(words, dwords, event | GPU_G4_CP_EVENT_WRITE_TIMESTAMP_BIT) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(gpuaddr & 0xffffffffULL)) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(gpuaddr >> 32)) &&
           gpu_g4_pm4_push(words, dwords, seqno);
}

static bool gpu_g4_pm4_emit_pkt4(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint16_t count) {
    return gpu_g4_pm4_push(words, dwords, gpu_g4_pm4_pkt4_hdr(reg, count));
}

static bool gpu_g4_pm4_emit_reg1(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 1) &&
           gpu_g4_pm4_push(words, dwords, value);
}

static bool gpu_g4_pm4_emit_reg2(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value0,
                                 uint32_t value1) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 2) &&
           gpu_g4_pm4_push(words, dwords, value0) &&
           gpu_g4_pm4_push(words, dwords, value1);
}

static bool gpu_g4_pm4_emit_reg4(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value0,
                                 uint32_t value1,
                                 uint32_t value2,
                                 uint32_t value3) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 4) &&
           gpu_g4_pm4_push(words, dwords, value0) &&
           gpu_g4_pm4_push(words, dwords, value1) &&
           gpu_g4_pm4_push(words, dwords, value2) &&
           gpu_g4_pm4_push(words, dwords, value3);
}

static bool gpu_g4_build_solid_fill_pm4(uint32_t *words,
                                        unsigned int *dwords,
                                        uint64_t dst_gpuaddr,
                                        uint64_t event_gpuaddr,
                                        uint32_t fill_value) {
    uint64_t dst_base = dst_gpuaddr & ~0x3fULL;
    uint32_t blit_cntl =
        (GPU_G4_A6XX_ROTATE_0 << 0) |
        (1U << 7) |
        (GPU_G4_A6XX_FMT6_32_UINT << 8) |
        (0xfU << 20) |
        (GPU_G4_A6XX_R2D_INT32 << 24);
    uint32_t output_info =
        (GPU_G4_A6XX_OUTPUT_IFMT_2D_UINT << 1) |
        (GPU_G4_A6XX_FMT6_32_UINT << 3) |
        (0xfU << 12);
    uint32_t dest_info =
        GPU_G4_A6XX_FMT6_32_UINT |
        (GPU_G4_A6XX_TILE6_LINEAR << 8) |
        (GPU_G4_A3XX_COLOR_SWAP_WZYX << 10);
    uint32_t dest_br = GPU_G4_FILL_DWORDS - 1U;

    *dwords = 0;
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_SET_MARKER, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_G4_A6XX_CP_SET_MARKER_RM6_BLIT2DSCALE)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg4(words, dwords, GPU_G4_REG_RB_A2D_CLEAR_COLOR_DW0,
                              fill_value, 0, 0, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_BLT_CNTL, blit_cntl) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_GRAS_A2D_BLT_CNTL, blit_cntl) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_SP_A2D_OUTPUT_INFO, output_info) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_PIXEL_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_INFO, dest_info)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_BASE,
                              (uint32_t)(dst_base & 0xffffffffULL),
                              (uint32_t)(dst_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_PITCH, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_G4_REG_GRAS_A2D_DEST_TL, 0, dest_br)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_BLIT, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_G4_A6XX_CP_BLIT_OP_SCALE) ||
        !gpu_g4_pm4_emit_event_ts(words, dwords,
                                  GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS,
                                  event_gpuaddr,
                                  GPU_G4_EVENT_SEQNO_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    return true;
}

static bool gpu_h1_pm4_emit_load_state6_shader(uint32_t *words,
                                               unsigned int *dwords,
                                               uint8_t opcode,
                                               uint32_t state_block,
                                               uint64_t shader_gpuaddr,
                                               uint32_t shader_dwords) {
    uint32_t load0 =
        GPU_H1_CP_LOAD_STATE6_STATE_SRC_INDIRECT |
        state_block |
        ((shader_dwords & 0x3ffU) << 22);

    return gpu_g4_pm4_emit_pkt7(words, dwords, opcode, 3) &&
           gpu_g4_pm4_push(words, dwords, load0) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(shader_gpuaddr & 0xffffffffULL)) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(shader_gpuaddr >> 32));
}

static bool gpu_h1_build_shader_state_pm4(uint32_t *words,
                                          unsigned int *dwords,
                                          uint64_t vs_gpuaddr,
                                          uint64_t fs_gpuaddr) {
    uint32_t xs_cntl_0 = (1U << 7);

    *dwords = 0;
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_CNTL_0, xs_cntl_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H1_REG_SP_VS_BASE,
                              (uint32_t)(vs_gpuaddr & 0xffffffffULL),
                              (uint32_t)(vs_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_CONFIG,
                              GPU_H1_SP_CONFIG_ENABLED) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_INSTR_SIZE,
                              GPU_H1_VS_SHADER_DWORDS)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CNTL_0, xs_cntl_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H1_REG_SP_PS_BASE,
                              (uint32_t)(fs_gpuaddr & 0xffffffffULL),
                              (uint32_t)(fs_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CONFIG,
                              GPU_H1_SP_CONFIG_ENABLED) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_INSTR_SIZE,
                              GPU_H1_FS_SHADER_DWORDS)) {
        return false;
    }
    if (!gpu_h1_pm4_emit_load_state6_shader(words, dwords,
                                            (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_GEOM,
                                            GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER,
                                            vs_gpuaddr,
                                            GPU_H1_VS_SHADER_DWORDS) ||
        !gpu_h1_pm4_emit_load_state6_shader(words, dwords,
                                            (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
                                            GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER,
                                            fs_gpuaddr,
                                            GPU_H1_FS_SHADER_DWORDS) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    return true;
}

static uint32_t gpu_h2_float_bits(float value) {
    union {
        float f;
        uint32_t u;
    } bits;

    bits.f = value;
    return bits.u;
}

static uint32_t gpu_h2_xy(uint32_t x, uint32_t y) {
    return (x & 0xffffU) | ((y & 0xffffU) << 16);
}

static bool gpu_h2_pm4_emit_reg6(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value0,
                                 uint32_t value1,
                                 uint32_t value2,
                                 uint32_t value3,
                                 uint32_t value4,
                                 uint32_t value5) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 6) &&
           gpu_g4_pm4_push(words, dwords, value0) &&
           gpu_g4_pm4_push(words, dwords, value1) &&
           gpu_g4_pm4_push(words, dwords, value2) &&
           gpu_g4_pm4_push(words, dwords, value3) &&
           gpu_g4_pm4_push(words, dwords, value4) &&
           gpu_g4_pm4_push(words, dwords, value5);
}

static bool gpu_h2_append_3d_state_pm4(uint32_t *words,
                                       unsigned int *dwords,
                                       unsigned int *state_reg_writes,
                                       uint64_t color_gpuaddr,
                                       uint32_t color_format,
                                       uint32_t color_output_mask,
                                       bool color_uint,
                                       uint32_t sp_vs_output_reg0,
                                       uint32_t sp_ps_output_reg0) {
    uint64_t color_base = color_gpuaddr & ~0x3fULL;
    uint32_t rb_mrt_control = (color_output_mask & 0xfU) << 7;
    uint32_t rb_mrt_info =
        color_format |
        (GPU_G4_A6XX_TILE6_LINEAR << 8) |
        (GPU_G4_A3XX_COLOR_SWAP_WZYX << 13);
    uint32_t sp_ps_mrt =
        color_format |
        (color_uint ? (1U << 9) : 0U);
    uint32_t pitch_qwords = GPU_H2_COLOR_STRIDE >> 6;
    uint32_t array_pitch_qwords = (uint32_t)(GPU_H2_COLOR_ALLOC_SIZE >> 6);
    uint32_t screen_tl = gpu_h2_xy(0, 0);
    uint32_t screen_br = gpu_h2_xy(GPU_H2_COLOR_WIDTH, GPU_H2_COLOR_HEIGHT);
    unsigned int reg_writes = 0;

    if (state_reg_writes != NULL) {
        *state_reg_writes = 0;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_SET_MARKER, 1) ||
        !gpu_g4_pm4_push(words, dwords,
                         GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_CCU_CNTL,
                              GPU_H3_RB_CCU_CNTL)) {
        return false;
    }
    reg_writes += 1;
    if (!gpu_h2_pm4_emit_reg6(words, dwords, GPU_H2_REG_GRAS_CL_VIEWPORT,
                              gpu_h2_float_bits((float)GPU_H2_COLOR_WIDTH / 2.0f),
                              gpu_h2_float_bits((float)GPU_H2_COLOR_WIDTH / 2.0f),
                              gpu_h2_float_bits((float)GPU_H2_COLOR_HEIGHT / 2.0f),
                              gpu_h2_float_bits((float)GPU_H2_COLOR_HEIGHT / 2.0f),
                              gpu_h2_float_bits(0.0f),
                              gpu_h2_float_bits(1.0f))) {
        return false;
    }
    reg_writes += 6;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE,
                              GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_INTERP_CNTL,
                              GPU_H3_GRAS_CL_INTERP_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_GUARDBAND_CLIP_ADJ, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SU_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL,
                              GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SU_VS_SIV_CNTL,
                              GPU_H3_GRAS_SU_VS_SIV_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SC_CNTL, 2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SC_RAS_MSAA_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SC_DEST_MSAA_CNTL,
                              1U << 2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SC_MSAA_SAMPLE_POS_CNTL,
                              GPU_H3_GRAS_SC_MSAA_SAMPLE_POS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_LRZ_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_LRZ_PS_INPUT_CNTL,
                              GPU_H3_GRAS_LRZ_PS_INPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_LRZ_PS_SAMPLEFREQ_CNTL,
                              GPU_H3_GRAS_LRZ_PS_SAMPLEFREQ_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_MODE_CNTL, 2)) {
        return false;
    }
    reg_writes += 16;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_TL,
                              screen_tl, screen_br) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_VIEWPORT_SCISSOR_TL,
                              screen_tl, screen_br) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_WINDOW_SCISSOR_TL,
                              screen_tl, screen_br)) {
        return false;
    }
    reg_writes += 6;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_RENDER_CNTL,
                              GPU_H3_RB_RENDER_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_RAS_MSAA_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_DEST_MSAA_CNTL, 1U << 2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_MSAA_SAMPLE_POS_CNTL,
                              GPU_H3_RB_MSAA_SAMPLE_POS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_INTERP_CNTL,
                              GPU_H3_RB_INTERP_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_INPUT_CNTL,
                              GPU_H3_RB_PS_INPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_OUTPUT_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_MRT_CNTL, 1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_OUTPUT_MASK,
                              color_output_mask) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_SRGB_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_SAMPLEFREQ_CNTL,
                              GPU_H3_RB_PS_SAMPLEFREQ_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_MODE_CNTL, 0x10) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_BLEND_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_DEPTH_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_STENCIL_CNTL, 0)) {
        return false;
    }
    reg_writes += 15;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_RB_MRT0_CONTROL,
                              rb_mrt_control, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_MRT0_BUF_INFO,
                              rb_mrt_info) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_RB_MRT0_PITCH,
                              pitch_qwords, array_pitch_qwords) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_RB_MRT0_BASE,
                              (uint32_t)(color_base & 0xffffffffULL),
                              (uint32_t)(color_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_MRT0_BASE_GMEM, 0)) {
        return false;
    }
    reg_writes += 8;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VARYING_INTERP_MODE_0, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VARYING_REPLACE_MODE_0, 0) ||
        !gpu_g4_pm4_emit_reg4(words, dwords, GPU_H2_REG_VPC_VARYING_LM_TRANSFER_CNTL0,
                              GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0,
                              GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL1,
                              GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL2,
                              GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL3) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL,
                              GPU_H3_VPC_VS_CLIP_CULL_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_SIV_CNTL,
                              GPU_H3_VPC_VS_SIV_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_UNKNOWN_9210,
                              GPU_H3_VPC_UNKNOWN_9210) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_REPLACE_MODE_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_ROTATION_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_CNTL,
                              GPU_H3_VPC_VS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_PS_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_SO_OVERRIDE,
                              GPU_H3_VPC_SO_OVERRIDE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2,
                              GPU_H3_VPC_VS_CLIP_CULL_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_SIV_CNTL_V2,
                              GPU_H3_VPC_VS_SIV_CNTL_V2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_RAST_STREAM_CNTL,
                              GPU_H3_VPC_RAST_STREAM_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_RESTART_INDEX, 0xffffffffU) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_MODE_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_VS_CNTL, 4) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_PC_STEREO_RENDERING_CNTL,
                              GPU_H3_PC_STEREO_RENDERING_CNTL)) {
        return false;
    }
    reg_writes += 22;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_VFD_CNTL_0, 0, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_MODE_CNTL, 3) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_VFD_INDEX_OFFSET, 0, 0)) {
        return false;
    }
    reg_writes += 5;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_OUTPUT_CNTL, 1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_OUTPUT_REG0,
                              sp_vs_output_reg0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_VPC_DEST_REG0, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_BLEND_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_SRGB_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_MSAA_SAMPLE_POS_CNTL,
                              GPU_H3_TPL1_MSAA_SAMPLE_POS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL,
                              GPU_H3_TPL1_PS_SWIZZLE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_MASK,
                              color_output_mask) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_MRT_CNTL, 1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_REG0,
                              sp_ps_output_reg0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_MRT_REG0, sp_ps_mrt) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_REG_PROG_ID_3,
                              GPU_H3_SP_REG_PROG_ID_3)) {
        return false;
    }
    reg_writes += 13;
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    if (state_reg_writes != NULL) {
        *state_reg_writes = reg_writes;
    }
    return true;
}

static bool gpu_h2_build_3d_state_pm4(uint32_t *words,
                                      unsigned int *dwords,
                                      unsigned int *state_reg_writes,
                                      uint64_t color_gpuaddr) {
    *dwords = 0;
    return gpu_h2_append_3d_state_pm4(words, dwords, state_reg_writes, color_gpuaddr,
                                      GPU_G4_A6XX_FMT6_32_UINT, 0xfU, true,
                                      0x00000f00U, 0U);
}

static bool gpu_h3_append_shader_state_pm4(uint32_t *words,
                                           unsigned int *dwords,
                                           uint64_t vs_gpuaddr,
                                           uint64_t fs_gpuaddr) {
    uint32_t vs_cntl_0 = GPU_H3_SP_VS_CNTL_0;
    uint32_t ps_cntl_0 = GPU_H3_SP_PS_CNTL_0;

    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_MODE_CNTL,
                              GPU_H3_SP_MODE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_MODE_CNTL,
                              GPU_H3_TPL1_MODE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_CNTL_0, vs_cntl_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H1_REG_SP_VS_BASE,
                              (uint32_t)(vs_gpuaddr & 0xffffffffULL),
                              (uint32_t)(vs_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_CONFIG,
                              GPU_H1_SP_CONFIG_ENABLED) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_VS_INSTR_SIZE,
                              GPU_H3_VS_SHADER_DWORDS)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CNTL_0, ps_cntl_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H1_REG_SP_PS_BASE,
                              (uint32_t)(fs_gpuaddr & 0xffffffffULL),
                              (uint32_t)(fs_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CONFIG,
                              GPU_H1_SP_CONFIG_ENABLED) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_INSTR_SIZE,
                              GPU_H3_FS_SHADER_DWORDS)) {
        return false;
    }
    return gpu_h1_pm4_emit_load_state6_shader(words, dwords,
                                              (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_GEOM,
                                              GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER,
                                              vs_gpuaddr,
                                              GPU_H3_VS_SHADER_DWORDS) &&
           gpu_h1_pm4_emit_load_state6_shader(words, dwords,
                                              (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
                                              GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER,
                                              fs_gpuaddr,
                                              GPU_H3_FS_SHADER_DWORDS);
}

static uint32_t gpu_h3_vfd_fetch_instr(uint32_t idx,
                                       uint32_t byte_offset,
                                       uint32_t format) {
    return (idx & 0x1fU) |
           ((byte_offset & 0xfffU) << 5) |
           ((format & 0xffU) << 20) |
           ((GPU_G4_A3XX_COLOR_SWAP_WZYX & 0x3U) << 28) |
           (1U << 31);
}

static uint32_t gpu_h3_vfd_dest_instr(uint32_t regid, uint32_t writemask) {
    return (writemask & 0xfU) | ((regid & 0xffU) << 4);
}

static uint32_t gpu_h3_draw_initiator(void) {
    return (GPU_H3_DI_PT_TRILIST & 0x3fU) |
           ((GPU_H3_DI_SRC_SEL_AUTO_INDEX & 0x3U) << 6) |
           ((GPU_H3_IGNORE_VISIBILITY & 0x3U) << 8) |
           ((GPU_H3_INDEX_SIZE_IGN & 0x3U) << 10);
}

static bool gpu_h3_pm4_emit_draw_indx_offset(uint32_t *words,
                                             unsigned int *dwords,
                                             uint32_t initiator,
                                             uint32_t instances,
                                             uint32_t indices) {
    return gpu_g4_pm4_emit_pkt7(words, dwords,
                                (uint8_t)GPU_H3_PM4_CP_DRAW_INDX_OFFSET, 3) &&
           gpu_g4_pm4_push(words, dwords, initiator) &&
           gpu_g4_pm4_push(words, dwords, instances) &&
           gpu_g4_pm4_push(words, dwords, indices);
}

static bool gpu_h3_build_draw_envelope_pm4(uint32_t *words,
                                           unsigned int *dwords,
                                           unsigned int *state_reg_writes,
                                           unsigned int *vfd_reg_writes,
                                           uint64_t color_gpuaddr,
                                           uint64_t event_gpuaddr,
                                           uint64_t vs_gpuaddr,
                                           uint64_t fs_gpuaddr,
                                           uint64_t vertex_gpuaddr) {
    uint64_t vertex_base = vertex_gpuaddr & ~0x3fULL;
    uint32_t draw_initiator = gpu_h3_draw_initiator();

    *dwords = 0;
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 0;
    }
    if (!gpu_h3_append_shader_state_pm4(words, dwords, vs_gpuaddr, fs_gpuaddr) ||
        !gpu_h2_append_3d_state_pm4(words, dwords, state_reg_writes, color_gpuaddr,
                                    GPU_H3_COLOR_FORMAT, GPU_H3_COLOR_OUTPUT_MASK,
                                    false, GPU_H3_SP_VS_OUTPUT_REG0,
                                    GPU_H3_PS_OUTPUT_REGID)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_CNTL_0, 0x00000101U) ||
        !gpu_g4_pm4_emit_reg4(words, dwords, GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE,
                              (uint32_t)(vertex_base & 0xffffffffULL),
                              (uint32_t)(vertex_base >> 32),
                              (uint32_t)GPU_H3_VERTEX_BYTES,
                              GPU_H3_VERTEX_STRIDE) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H3_REG_VFD_FETCH_INSTR0,
                              gpu_h3_vfd_fetch_instr(0, 0, GPU_H3_A6XX_FMT6_32_32_FLOAT),
                              1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VFD_DEST_CNTL0,
                              gpu_h3_vfd_dest_instr(0, 0x3U))) {
        return false;
    }
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 8;
    }
    if (!gpu_h3_pm4_emit_draw_indx_offset(words, dwords, draw_initiator, 1U,
                                          GPU_H3_VERTEX_COUNT) ||
        !gpu_g4_pm4_emit_event_ts(words, dwords,
                                  GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS,
                                  event_gpuaddr,
                                  GPU_G4_EVENT_SEQNO_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
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
    int prep_rc;
    int rc;

    a90_console_printf("gpu.g0.materialize.fwclass_prepare_attempted=1\r\n");
    prep_rc = gpu_g0_fwclass_prepare();
    a90_console_printf("gpu.g0.materialize.fwclass_prepare_rc=%d\r\n", prep_rc);
    if (prep_rc < 0) {
        return prep_rc;
    }

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

static int gpu_g2_gpuobj_probe_child(int write_fd, bool do_mmap) {
    struct gpu_g2_gpuobj_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    int fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.alloc_rc = -1;
    result.mmap_rc = -1;
    result.munmap_rc = -1;
    result.free_rc = -1;
    result.destroy_rc = -1;
    result.flags_in = GPU_G1_CONTEXT_FLAGS;
    result.flags_out = GPU_G1_CONTEXT_FLAGS;
    result.alloc_size_in = GPU_G2_GPUOBJ_ALLOC_SIZE;
    result.alloc_flags_in = GPU_G2_GPUOBJ_ALLOC_FLAGS;

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
        struct gpu_kgsl_gpuobj_alloc alloc_arg;

        result.create_rc = 0;
        result.create_errno = 0;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.context_id = create_arg.drawctxt_id;
        result.flags_out = create_arg.flags;

        memset(&alloc_arg, 0, sizeof(alloc_arg));
        alloc_arg.size = GPU_G2_GPUOBJ_ALLOC_SIZE;
        alloc_arg.flags = GPU_G2_GPUOBJ_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &alloc_arg) < 0) {
            result.alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            result.alloc_rc = -1;
            result.alloc_errno = errno;
        } else {
            struct gpu_kgsl_gpuobj_free free_arg;

            result.alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            result.alloc_rc = 0;
            result.alloc_errno = 0;
            result.gpuobj_id = alloc_arg.id;
            result.alloc_size_out = alloc_arg.size;
            result.alloc_flags_out = alloc_arg.flags;
            result.alloc_va_len = alloc_arg.va_len;
            result.alloc_mmapsize = alloc_arg.mmapsize;

            if (do_mmap) {
                void *map;

                result.mmap_attempted = 1;
                result.mmap_access_attempted = 0;
                result.mmap_len = alloc_arg.mmapsize;
                result.mmap_offset = (uint64_t)alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
                if (alloc_arg.mmapsize == 0 ||
                    result.mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)alloc_arg.id) {
                    result.mmap_rc = -1;
                    result.mmap_errno = EINVAL;
                } else {
                    errno = 0;
                    stage_started_ms = monotonic_millis();
                    map = mmap(NULL,
                               (size_t)alloc_arg.mmapsize,
                               PROT_READ | PROT_WRITE,
                               MAP_SHARED,
                               fd,
                               (off_t)result.mmap_offset);
                    result.mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
                    if (map == MAP_FAILED) {
                        result.mmap_rc = -1;
                        result.mmap_errno = errno;
                    } else {
                        result.mmap_rc = 0;
                        result.mmap_errno = 0;
                        result.mmap_nonnull = map != NULL ? 1 : 0;
                        result.munmap_attempted = 1;
                        errno = 0;
                        stage_started_ms = monotonic_millis();
                        if (munmap(map, (size_t)alloc_arg.mmapsize) < 0) {
                            result.munmap_rc = -1;
                            result.munmap_errno = errno;
                        } else {
                            result.munmap_rc = 0;
                            result.munmap_errno = 0;
                        }
                        result.munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
                    }
                }
            } else {
                result.mmap_attempted = 0;
                result.mmap_access_attempted = 0;
            }

            memset(&free_arg, 0, sizeof(free_arg));
            free_arg.id = alloc_arg.id;
            result.free_attempted = 1;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
                result.free_rc = -1;
                result.free_errno = errno;
            } else {
                result.free_rc = 0;
                result.free_errno = 0;
            }
            result.free_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_drawctxt_destroy destroy_arg;

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

static int gpu_g2_gpuobj_probe(int timeout_ms, bool materialize_devnode, bool do_mmap) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_g2_gpuobj_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g2.gpuobj.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.g2.gpuobj.version=1\r\n");
    a90_console_printf("gpu.g2.gpuobj.scope=%s\r\n",
                       do_mmap ? "kgsl-gpuobj-mmap-munmap-probe" :
                                 "kgsl-gpuobj-alloc-free-probe");
    a90_console_printf("gpu.g2.gpuobj.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g2.gpuobj.flags=O_RDWR\r\n");
    a90_console_printf("gpu.g2.gpuobj.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g2.gpuobj.parent_enters_open=0\r\n");
    a90_console_printf("gpu.g2.gpuobj.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.g2.gpuobj.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_free,drawctxt_destroy\r\n");
    a90_console_printf("gpu.g2.gpuobj.alloc_size=%llu\r\n",
                       (unsigned long long)GPU_G2_GPUOBJ_ALLOC_SIZE);
    a90_console_printf("gpu.g2.gpuobj.alloc_flags=0x%llx\r\n",
                       (unsigned long long)GPU_G2_GPUOBJ_ALLOC_FLAGS);
    a90_console_printf("gpu.g2.gpuobj.mmap_attempted=%d\r\n", do_mmap ? 1 : 0);
    a90_console_printf("gpu.g2.gpuobj.mmap_offset_rule=id_times_4096\r\n");
    a90_console_printf("gpu.g2.gpuobj.mmap_access_attempted=0\r\n");
    a90_console_printf("gpu.g2.gpuobj.submit_attempted=0\r\n");
    a90_console_printf("gpu.g2.gpuobj.power_write_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g2.gpuobj.materialize_requested=1\r\n");
        a90_console_printf("gpu.g2.gpuobj.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g2.gpuobj.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g2.gpuobj.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.g2.gpuobj.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_g2_gpuobj_probe_child(pipefd[1], do_mmap);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.g2.gpuobj.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.g2.gpuobj.result=%s\r\n",
                       got_result ? (do_mmap ?
                                     ((result.mmap_rc == 0 && result.munmap_rc == 0 &&
                                       result.free_rc == 0) ?
                                      "mapped-unmapped" : "returned-error") :
                                     ((result.alloc_rc == 0 && result.free_rc == 0) ?
                                      "allocated-freed" : "returned-error")) :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g2.gpuobj.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.g2.gpuobj.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.g2.gpuobj.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.g2.gpuobj.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.g2.gpuobj.open_elapsed_ms=%ld\r\n", result.open_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.g2.gpuobj.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.g2.gpuobj.create_elapsed_ms=%ld\r\n", result.create_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.g2.gpuobj.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.g2.gpuobj.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.g2.gpuobj.context_flags_in=0x%x\r\n", result.flags_in);
        a90_console_printf("gpu.g2.gpuobj.context_flags_out=0x%x\r\n", result.flags_out);
        a90_console_printf("gpu.g2.gpuobj.alloc_elapsed_ms=%ld\r\n", result.alloc_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.alloc_rc=%d\r\n", result.alloc_rc);
        a90_console_printf("gpu.g2.gpuobj.alloc_errno=%d\r\n", result.alloc_errno);
        a90_console_printf("gpu.g2.gpuobj.alloc_size_in=%llu\r\n",
                           (unsigned long long)result.alloc_size_in);
        a90_console_printf("gpu.g2.gpuobj.alloc_size_out=%llu\r\n",
                           (unsigned long long)result.alloc_size_out);
        a90_console_printf("gpu.g2.gpuobj.alloc_flags_in=0x%llx\r\n",
                           (unsigned long long)result.alloc_flags_in);
        a90_console_printf("gpu.g2.gpuobj.alloc_flags_out=0x%llx\r\n",
                           (unsigned long long)result.alloc_flags_out);
        a90_console_printf("gpu.g2.gpuobj.alloc_va_len=%llu\r\n",
                           (unsigned long long)result.alloc_va_len);
        a90_console_printf("gpu.g2.gpuobj.alloc_mmapsize=%llu\r\n",
                           (unsigned long long)result.alloc_mmapsize);
        a90_console_printf("gpu.g2.gpuobj.gpuobj_id=%u\r\n", result.gpuobj_id);
        a90_console_printf("gpu.g2.gpuobj.mmap_attempted=%d\r\n", result.mmap_attempted);
        a90_console_printf("gpu.g2.gpuobj.mmap_len=%llu\r\n",
                           (unsigned long long)result.mmap_len);
        a90_console_printf("gpu.g2.gpuobj.mmap_offset=%llu\r\n",
                           (unsigned long long)result.mmap_offset);
        a90_console_printf("gpu.g2.gpuobj.mmap_elapsed_ms=%ld\r\n", result.mmap_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.mmap_rc=%d\r\n", result.mmap_rc);
        a90_console_printf("gpu.g2.gpuobj.mmap_errno=%d\r\n", result.mmap_errno);
        a90_console_printf("gpu.g2.gpuobj.mmap_nonnull=%d\r\n", result.mmap_nonnull);
        a90_console_printf("gpu.g2.gpuobj.mmap_access_attempted=%d\r\n",
                           result.mmap_access_attempted);
        a90_console_printf("gpu.g2.gpuobj.munmap_attempted=%d\r\n", result.munmap_attempted);
        a90_console_printf("gpu.g2.gpuobj.munmap_elapsed_ms=%ld\r\n", result.munmap_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.munmap_rc=%d\r\n", result.munmap_rc);
        a90_console_printf("gpu.g2.gpuobj.munmap_errno=%d\r\n", result.munmap_errno);
        a90_console_printf("gpu.g2.gpuobj.free_attempted=%d\r\n", result.free_attempted);
        a90_console_printf("gpu.g2.gpuobj.free_elapsed_ms=%ld\r\n", result.free_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.free_rc=%d\r\n", result.free_rc);
        a90_console_printf("gpu.g2.gpuobj.free_errno=%d\r\n", result.free_errno);
        a90_console_printf("gpu.g2.gpuobj.destroy_attempted=%d\r\n", result.destroy_attempted);
        a90_console_printf("gpu.g2.gpuobj.destroy_elapsed_ms=%ld\r\n", result.destroy_elapsed_ms);
        a90_console_printf("gpu.g2.gpuobj.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.g2.gpuobj.destroy_errno=%d\r\n", result.destroy_errno);
        a90_console_printf("gpu.g2.gpuobj.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.g2.gpuobj.close_errno=%d\r\n", result.close_errno);
        a90_console_printf("gpu.g2.gpuobj.total_elapsed_ms=%ld\r\n", result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static int gpu_g3_noop_submit_probe_child(int write_fd) {
    struct gpu_g3_noop_submit_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    void *map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.alloc_rc = -1;
    result.info_rc = -1;
    result.mmap_rc = -1;
    result.mapped_write_rc = -1;
    result.sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.munmap_rc = -1;
    result.free_rc = -1;
    result.destroy_rc = -1;
    result.flags_in = GPU_G1_CONTEXT_FLAGS;
    result.flags_out = GPU_G1_CONTEXT_FLAGS;
    result.alloc_size_in = GPU_G3_NOOP_ALLOC_SIZE;
    result.alloc_flags_in = GPU_G3_NOOP_ALLOC_FLAGS;
    result.wait_timeout_ms = GPU_G3_WAIT_TIMEOUT_MS;
    result.noop_dwords = GPU_G3_NOOP_DWORDS;
    result.noop_header = gpu_g3_pm4_pkt7_hdr((uint8_t)GPU_G3_PM4_CP_NOP, 1);
    result.noop_payload = 0;
    result.fence_fd = -1;
    result.cmd_size = GPU_G3_NOOP_BYTES;
    result.sync_length = GPU_G3_NOOP_BYTES;

    errno = 0;
    stage_started_ms = monotonic_millis();
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    result.open_elapsed_ms = monotonic_millis() - stage_started_ms;
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        goto out;
    }
    result.open_rc = 0;

    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    stage_started_ms = monotonic_millis();
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
        goto out;
    }
    result.create_rc = 0;
    result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
    result.context_id = create_arg.drawctxt_id;
    result.flags_out = create_arg.flags;

    {
        struct gpu_kgsl_gpuobj_alloc alloc_arg;
        struct gpu_kgsl_gpuobj_info info_arg;

        memset(&alloc_arg, 0, sizeof(alloc_arg));
        alloc_arg.size = GPU_G3_NOOP_ALLOC_SIZE;
        alloc_arg.flags = GPU_G3_NOOP_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &alloc_arg) < 0) {
            result.alloc_rc = -1;
            result.alloc_errno = errno;
            result.alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.alloc_rc = 0;
        result.alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.gpuobj_id = alloc_arg.id;
        result.alloc_size_out = alloc_arg.size;
        result.alloc_flags_out = alloc_arg.flags;
        result.alloc_va_len = alloc_arg.va_len;
        result.alloc_mmapsize = alloc_arg.mmapsize;

        memset(&info_arg, 0, sizeof(info_arg));
        info_arg.id = alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &info_arg) < 0) {
            result.info_rc = -1;
            result.info_errno = errno;
            result.info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.info_rc = 0;
        result.info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.info_gpuaddr = info_arg.gpuaddr;
        result.info_flags = info_arg.flags;
        result.info_size = info_arg.size;
        result.info_va_len = info_arg.va_len;
        result.cmd_gpuaddr = info_arg.gpuaddr;

        result.mmap_len = alloc_arg.mmapsize;
        result.mmap_offset = (uint64_t)alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (alloc_arg.mmapsize < GPU_G3_NOOP_BYTES ||
            result.mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)alloc_arg.id) {
            result.mmap_rc = -1;
            result.mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        map = mmap(NULL,
                   (size_t)alloc_arg.mmapsize,
                   PROT_READ | PROT_WRITE,
                   MAP_SHARED,
                   fd,
                   (off_t)result.mmap_offset);
        result.mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (map == MAP_FAILED) {
            result.mmap_rc = -1;
            result.mmap_errno = errno;
            goto out;
        }
        result.mmap_rc = 0;
        result.mmap_nonnull = map != NULL ? 1 : 0;

        {
            uint32_t *words = (uint32_t *)map;

            result.mapped_write_attempted = 1;
            words[0] = result.noop_header;
            words[1] = result.noop_payload;
            __sync_synchronize();
            result.mapped_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_obj;
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(&sync_obj, 0, sizeof(sync_obj));
            sync_obj.id = alloc_arg.id;
            sync_obj.offset = 0;
            sync_obj.length = GPU_G3_NOOP_BYTES;
            sync_obj.op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)&sync_obj;
            sync_arg.obj_len = sizeof(sync_obj);
            sync_arg.count = 1;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.sync_rc = -1;
                result.sync_errno = errno;
            } else {
                result.sync_rc = 0;
            }
            result.sync_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.sync_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_command_object cmd_obj;
            struct gpu_kgsl_command_object mem_obj;
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.offset = 0;
            cmd_obj.gpuaddr = info_arg.gpuaddr;
            cmd_obj.size = GPU_G3_NOOP_BYTES;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = alloc_arg.id;

            memset(&mem_obj, 0, sizeof(mem_obj));
            mem_obj.offset = 0;
            mem_obj.gpuaddr = info_arg.gpuaddr;
            mem_obj.size = info_arg.size;
            mem_obj.flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_obj.id = alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)&mem_obj;
            command_arg.objsize = sizeof(mem_obj);
            command_arg.numobjs = 1;
            command_arg.context_id = create_arg.drawctxt_id;

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
                result.submit_rc = -1;
                result.submit_errno = errno;
            } else {
                result.submit_rc = 0;
                result.submit_timestamp = command_arg.timestamp;
            }
            result.submit_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.submit_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_timestamp_event_fence fence_arg;
            struct gpu_kgsl_timestamp_event event_arg;

            memset(&fence_arg, 0, sizeof(fence_arg));
            fence_arg.fence_fd = -1;
            memset(&event_arg, 0, sizeof(event_arg));
            event_arg.type = GPU_KGSL_TIMESTAMP_EVENT_FENCE;
            event_arg.timestamp = result.submit_timestamp;
            event_arg.context_id = create_arg.drawctxt_id;
            event_arg.priv = &fence_arg;
            event_arg.len = sizeof(fence_arg);

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_TIMESTAMP_EVENT, &event_arg) < 0) {
                result.timestamp_event_rc = -1;
                result.timestamp_event_errno = errno;
            } else {
                result.timestamp_event_rc = 0;
                fence_fd = fence_arg.fence_fd;
                result.fence_fd = fence_fd;
            }
            result.timestamp_event_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;

            memset(&wait_arg, 0, sizeof(wait_arg));
            wait_arg.context_id = create_arg.drawctxt_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_G3_WAIT_TIMEOUT_MS;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
                result.wait_rc = -1;
                result.wait_errno = errno;
            } else {
                result.wait_rc = 0;
            }
            result.wait_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

            memset(&read_arg, 0, sizeof(read_arg));
            read_arg.context_id = create_arg.drawctxt_id;
            read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
                result.readtimestamp_rc = -1;
                result.readtimestamp_errno = errno;
            } else {
                result.readtimestamp_rc = 0;
                result.retired_timestamp = read_arg.timestamp;
            }
            result.readtimestamp_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        if (fence_fd >= 0) {
            struct pollfd pfd;

            memset(&pfd, 0, sizeof(pfd));
            pfd.fd = fence_fd;
            pfd.events = POLLIN;
            result.fence_poll_attempted = 1;
            errno = 0;
            result.fence_poll_rc = poll(&pfd, 1, 0);
            result.fence_poll_errno = result.fence_poll_rc < 0 ? errno : 0;
            result.fence_poll_revents = pfd.revents;
            errno = 0;
            if (close(fence_fd) < 0) {
                result.fence_close_rc = -1;
                result.fence_close_errno = errno;
            } else {
                result.fence_close_rc = 0;
                result.fence_close_errno = 0;
            }
            fence_fd = -1;
        }
    }

out:
    if (fence_fd >= 0) {
        errno = 0;
        if (close(fence_fd) < 0) {
            result.fence_close_rc = -1;
            result.fence_close_errno = errno;
        } else {
            result.fence_close_rc = 0;
            result.fence_close_errno = 0;
        }
    }
    if (map != MAP_FAILED) {
        result.munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(map, (size_t)result.mmap_len) < 0) {
            result.munmap_rc = -1;
            result.munmap_errno = errno;
        } else {
            result.munmap_rc = 0;
            result.munmap_errno = 0;
        }
        result.munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.free_deferred = 1;
        }
        result.free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.free_rc = -1;
            result.free_errno = errno;
        } else {
            result.free_rc = 0;
            result.free_errno = 0;
        }
        result.free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.context_id != 0) {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = result.context_id;
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
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
            result.close_errno = 0;
        }
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_g3_noop_submit_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_g3_noop_submit_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g3.noop.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.g3.noop.version=1\r\n");
    a90_console_printf("gpu.g3.noop.scope=kgsl-noop-submit-fence-probe\r\n");
    a90_console_printf("gpu.g3.noop.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g3.noop.flags=O_RDWR\r\n");
    a90_console_printf("gpu.g3.noop.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g3.noop.wait_timeout_ms=%u\r\n", GPU_G3_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.g3.noop.parent_enters_open=0\r\n");
    a90_console_printf("gpu.g3.noop.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.g3.noop.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy\r\n");
    a90_console_printf("gpu.g3.noop.pm4_source=mesa-freedreno-pkt7-cp-nop\r\n");
    a90_console_printf("gpu.g3.noop.pm4_cp_type7=0x%x\r\n", GPU_G3_PM4_CP_TYPE7_PKT);
    a90_console_printf("gpu.g3.noop.pm4_cp_nop=0x%x\r\n", GPU_G3_PM4_CP_NOP);
    a90_console_printf("gpu.g3.noop.noop_dwords=%u\r\n", GPU_G3_NOOP_DWORDS);
    a90_console_printf("gpu.g3.noop.noop_bytes=%llu\r\n",
                       (unsigned long long)GPU_G3_NOOP_BYTES);
    a90_console_printf("gpu.g3.noop.alloc_size=%llu\r\n",
                       (unsigned long long)GPU_G3_NOOP_ALLOC_SIZE);
    a90_console_printf("gpu.g3.noop.alloc_flags=0x%llx\r\n",
                       (unsigned long long)GPU_G3_NOOP_ALLOC_FLAGS);
    a90_console_printf("gpu.g3.noop.mapped_write_attempted=1\r\n");
    a90_console_printf("gpu.g3.noop.cache_sync_attempted=1\r\n");
    a90_console_printf("gpu.g3.noop.submit_attempted=1\r\n");
    a90_console_printf("gpu.g3.noop.fence_attempted=1\r\n");
    a90_console_printf("gpu.g3.noop.render_attempted=0\r\n");
    a90_console_printf("gpu.g3.noop.power_write_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g3.noop.materialize_requested=1\r\n");
        a90_console_printf("gpu.g3.noop.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g3.noop.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g3.noop.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.g3.noop.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_g3_noop_submit_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.g3.noop.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.g3.noop.result=%s\r\n",
                       got_result ? ((result.submit_rc == 0 &&
                                      result.timestamp_event_rc == 0 &&
                                      result.fence_fd >= 0 &&
                                      result.wait_rc == 0 &&
                                      result.readtimestamp_rc == 0 &&
                                      result.retired_timestamp >= result.submit_timestamp &&
                                      result.free_rc == 0 &&
                                      result.destroy_rc == 0) ?
                                     "submitted-fenced-retired" : "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g3.noop.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.g3.noop.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.g3.noop.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.g3.noop.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.g3.noop.open_elapsed_ms=%ld\r\n", result.open_elapsed_ms);
        a90_console_printf("gpu.g3.noop.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.g3.noop.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.g3.noop.create_elapsed_ms=%ld\r\n", result.create_elapsed_ms);
        a90_console_printf("gpu.g3.noop.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.g3.noop.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.g3.noop.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.g3.noop.context_flags_in=0x%x\r\n", result.flags_in);
        a90_console_printf("gpu.g3.noop.context_flags_out=0x%x\r\n", result.flags_out);
        a90_console_printf("gpu.g3.noop.alloc_elapsed_ms=%ld\r\n", result.alloc_elapsed_ms);
        a90_console_printf("gpu.g3.noop.alloc_rc=%d\r\n", result.alloc_rc);
        a90_console_printf("gpu.g3.noop.alloc_errno=%d\r\n", result.alloc_errno);
        a90_console_printf("gpu.g3.noop.alloc_size_in=%llu\r\n",
                           (unsigned long long)result.alloc_size_in);
        a90_console_printf("gpu.g3.noop.alloc_size_out=%llu\r\n",
                           (unsigned long long)result.alloc_size_out);
        a90_console_printf("gpu.g3.noop.alloc_flags_in=0x%llx\r\n",
                           (unsigned long long)result.alloc_flags_in);
        a90_console_printf("gpu.g3.noop.alloc_flags_out=0x%llx\r\n",
                           (unsigned long long)result.alloc_flags_out);
        a90_console_printf("gpu.g3.noop.alloc_va_len=%llu\r\n",
                           (unsigned long long)result.alloc_va_len);
        a90_console_printf("gpu.g3.noop.alloc_mmapsize=%llu\r\n",
                           (unsigned long long)result.alloc_mmapsize);
        a90_console_printf("gpu.g3.noop.gpuobj_id=%u\r\n", result.gpuobj_id);
        a90_console_printf("gpu.g3.noop.info_elapsed_ms=%ld\r\n", result.info_elapsed_ms);
        a90_console_printf("gpu.g3.noop.info_rc=%d\r\n", result.info_rc);
        a90_console_printf("gpu.g3.noop.info_errno=%d\r\n", result.info_errno);
        a90_console_printf("gpu.g3.noop.info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.info_gpuaddr);
        a90_console_printf("gpu.g3.noop.info_flags=0x%llx\r\n",
                           (unsigned long long)result.info_flags);
        a90_console_printf("gpu.g3.noop.info_size=%llu\r\n",
                           (unsigned long long)result.info_size);
        a90_console_printf("gpu.g3.noop.info_va_len=%llu\r\n",
                           (unsigned long long)result.info_va_len);
        a90_console_printf("gpu.g3.noop.mmap_elapsed_ms=%ld\r\n", result.mmap_elapsed_ms);
        a90_console_printf("gpu.g3.noop.mmap_rc=%d\r\n", result.mmap_rc);
        a90_console_printf("gpu.g3.noop.mmap_errno=%d\r\n", result.mmap_errno);
        a90_console_printf("gpu.g3.noop.mmap_nonnull=%d\r\n", result.mmap_nonnull);
        a90_console_printf("gpu.g3.noop.mmap_len=%llu\r\n",
                           (unsigned long long)result.mmap_len);
        a90_console_printf("gpu.g3.noop.mmap_offset=%llu\r\n",
                           (unsigned long long)result.mmap_offset);
        a90_console_printf("gpu.g3.noop.mapped_write_attempted=%d\r\n",
                           result.mapped_write_attempted);
        a90_console_printf("gpu.g3.noop.mapped_write_rc=%d\r\n",
                           result.mapped_write_rc);
        a90_console_printf("gpu.g3.noop.noop_header=0x%x\r\n", result.noop_header);
        a90_console_printf("gpu.g3.noop.noop_payload=0x%x\r\n", result.noop_payload);
        a90_console_printf("gpu.g3.noop.cmd_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_gpuaddr);
        a90_console_printf("gpu.g3.noop.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.g3.noop.sync_elapsed_ms=%ld\r\n", result.sync_elapsed_ms);
        a90_console_printf("gpu.g3.noop.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.g3.noop.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.g3.noop.sync_length=%llu\r\n",
                           (unsigned long long)result.sync_length);
        a90_console_printf("gpu.g3.noop.submit_elapsed_ms=%ld\r\n", result.submit_elapsed_ms);
        a90_console_printf("gpu.g3.noop.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.g3.noop.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.g3.noop.submit_timestamp=%u\r\n", result.submit_timestamp);
        a90_console_printf("gpu.g3.noop.timestamp_event_elapsed_ms=%ld\r\n",
                           result.timestamp_event_elapsed_ms);
        a90_console_printf("gpu.g3.noop.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.g3.noop.timestamp_event_errno=%d\r\n",
                           result.timestamp_event_errno);
        a90_console_printf("gpu.g3.noop.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.g3.noop.wait_elapsed_ms=%ld\r\n", result.wait_elapsed_ms);
        a90_console_printf("gpu.g3.noop.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.g3.noop.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.g3.noop.readtimestamp_elapsed_ms=%ld\r\n",
                           result.readtimestamp_elapsed_ms);
        a90_console_printf("gpu.g3.noop.readtimestamp_rc=%d\r\n", result.readtimestamp_rc);
        a90_console_printf("gpu.g3.noop.readtimestamp_errno=%d\r\n",
                           result.readtimestamp_errno);
        a90_console_printf("gpu.g3.noop.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.g3.noop.fence_poll_attempted=%d\r\n",
                           result.fence_poll_attempted);
        a90_console_printf("gpu.g3.noop.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.g3.noop.fence_poll_errno=%d\r\n",
                           result.fence_poll_errno);
        a90_console_printf("gpu.g3.noop.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.g3.noop.fence_close_rc=%d\r\n", result.fence_close_rc);
        a90_console_printf("gpu.g3.noop.fence_close_errno=%d\r\n",
                           result.fence_close_errno);
        a90_console_printf("gpu.g3.noop.munmap_attempted=%d\r\n", result.munmap_attempted);
        a90_console_printf("gpu.g3.noop.munmap_elapsed_ms=%ld\r\n", result.munmap_elapsed_ms);
        a90_console_printf("gpu.g3.noop.munmap_rc=%d\r\n", result.munmap_rc);
        a90_console_printf("gpu.g3.noop.munmap_errno=%d\r\n", result.munmap_errno);
        a90_console_printf("gpu.g3.noop.free_attempted=%d\r\n", result.free_attempted);
        a90_console_printf("gpu.g3.noop.free_deferred=%d\r\n", result.free_deferred);
        a90_console_printf("gpu.g3.noop.free_elapsed_ms=%ld\r\n", result.free_elapsed_ms);
        a90_console_printf("gpu.g3.noop.free_rc=%d\r\n", result.free_rc);
        a90_console_printf("gpu.g3.noop.free_errno=%d\r\n", result.free_errno);
        a90_console_printf("gpu.g3.noop.destroy_attempted=%d\r\n", result.destroy_attempted);
        a90_console_printf("gpu.g3.noop.destroy_elapsed_ms=%ld\r\n", result.destroy_elapsed_ms);
        a90_console_printf("gpu.g3.noop.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.g3.noop.destroy_errno=%d\r\n", result.destroy_errno);
        a90_console_printf("gpu.g3.noop.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.g3.noop.close_errno=%d\r\n", result.close_errno);
        a90_console_printf("gpu.g3.noop.total_elapsed_ms=%ld\r\n", result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static int gpu_g4_solid_fill_probe_child(int write_fd) {
    struct gpu_g4_solid_fill_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    void *cmd_map = MAP_FAILED;
    void *dst_map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.dst_alloc_rc = -1;
    result.dst_info_rc = -1;
    result.dst_mmap_rc = -1;
    result.event_alloc_rc = -1;
    result.event_info_rc = -1;
    result.dst_prefill_rc = -1;
    result.cmd_write_rc = -1;
    result.cmd_sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.readback_sync_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.cmd_munmap_rc = -1;
    result.dst_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.dst_free_rc = -1;
    result.event_free_rc = -1;
    result.destroy_rc = -1;
    result.flags_in = GPU_G1_CONTEXT_FLAGS;
    result.flags_out = GPU_G1_CONTEXT_FLAGS;
    result.cmd_alloc_size_in = GPU_G4_CMD_ALLOC_SIZE;
    result.cmd_alloc_flags_in = GPU_G4_ALLOC_FLAGS;
    result.dst_alloc_size_in = GPU_G4_DST_ALLOC_SIZE;
    result.dst_alloc_flags_in = GPU_G4_ALLOC_FLAGS;
    result.event_alloc_size_in = GPU_G4_EVENT_ALLOC_SIZE;
    result.event_alloc_flags_in = GPU_G4_ALLOC_FLAGS;
    result.dst_size = GPU_G4_FILL_BYTES;
    result.wait_timeout_ms = GPU_G4_WAIT_TIMEOUT_MS;
    result.expected_fill = GPU_G4_FILL_PATTERN;
    result.sentinel = GPU_G4_SENTINEL_PATTERN;
    result.rb_dbg_eco_skipped = 1;
    result.fence_fd = -1;

    errno = 0;
    stage_started_ms = monotonic_millis();
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    result.open_elapsed_ms = monotonic_millis() - stage_started_ms;
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        goto out;
    }
    result.open_rc = 0;

    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    stage_started_ms = monotonic_millis();
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
        goto out;
    }
    result.create_rc = 0;
    result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
    result.context_id = create_arg.drawctxt_id;
    result.flags_out = create_arg.flags;

    {
        struct gpu_kgsl_gpuobj_alloc cmd_alloc_arg;
        struct gpu_kgsl_gpuobj_info cmd_info_arg;
        struct gpu_kgsl_gpuobj_alloc dst_alloc_arg;
        struct gpu_kgsl_gpuobj_info dst_info_arg;
        struct gpu_kgsl_gpuobj_alloc event_alloc_arg;
        struct gpu_kgsl_gpuobj_info event_info_arg;

        memset(&cmd_alloc_arg, 0, sizeof(cmd_alloc_arg));
        cmd_alloc_arg.size = GPU_G4_CMD_ALLOC_SIZE;
        cmd_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &cmd_alloc_arg) < 0) {
            result.cmd_alloc_rc = -1;
            result.cmd_alloc_errno = errno;
            result.cmd_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.cmd_alloc_rc = 0;
        result.cmd_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.cmd_gpuobj_id = cmd_alloc_arg.id;
        result.cmd_alloc_size_out = cmd_alloc_arg.size;
        result.cmd_alloc_flags_out = cmd_alloc_arg.flags;
        result.cmd_alloc_va_len = cmd_alloc_arg.va_len;
        result.cmd_alloc_mmapsize = cmd_alloc_arg.mmapsize;

        memset(&cmd_info_arg, 0, sizeof(cmd_info_arg));
        cmd_info_arg.id = cmd_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &cmd_info_arg) < 0) {
            result.cmd_info_rc = -1;
            result.cmd_info_errno = errno;
            result.cmd_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.cmd_info_rc = 0;
        result.cmd_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.cmd_info_gpuaddr = cmd_info_arg.gpuaddr;
        result.cmd_info_flags = cmd_info_arg.flags;
        result.cmd_info_size = cmd_info_arg.size;
        result.cmd_info_va_len = cmd_info_arg.va_len;
        result.cmd_gpuaddr = cmd_info_arg.gpuaddr;

        result.cmd_mmap_len = cmd_alloc_arg.mmapsize;
        result.cmd_mmap_offset = (uint64_t)cmd_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (cmd_alloc_arg.mmapsize < (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL ||
            result.cmd_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)cmd_alloc_arg.id) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        cmd_map = mmap(NULL,
                       (size_t)cmd_alloc_arg.mmapsize,
                       PROT_READ | PROT_WRITE,
                       MAP_SHARED,
                       fd,
                       (off_t)result.cmd_mmap_offset);
        result.cmd_mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (cmd_map == MAP_FAILED) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = errno;
            goto out;
        }
        result.cmd_mmap_rc = 0;
        result.cmd_mmap_nonnull = cmd_map != NULL ? 1 : 0;

        memset(&dst_alloc_arg, 0, sizeof(dst_alloc_arg));
        dst_alloc_arg.size = GPU_G4_DST_ALLOC_SIZE;
        dst_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &dst_alloc_arg) < 0) {
            result.dst_alloc_rc = -1;
            result.dst_alloc_errno = errno;
            result.dst_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.dst_alloc_rc = 0;
        result.dst_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.dst_gpuobj_id = dst_alloc_arg.id;
        result.dst_alloc_size_out = dst_alloc_arg.size;
        result.dst_alloc_flags_out = dst_alloc_arg.flags;
        result.dst_alloc_va_len = dst_alloc_arg.va_len;
        result.dst_alloc_mmapsize = dst_alloc_arg.mmapsize;

        memset(&dst_info_arg, 0, sizeof(dst_info_arg));
        dst_info_arg.id = dst_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &dst_info_arg) < 0) {
            result.dst_info_rc = -1;
            result.dst_info_errno = errno;
            result.dst_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.dst_info_rc = 0;
        result.dst_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.dst_info_gpuaddr = dst_info_arg.gpuaddr;
        result.dst_info_flags = dst_info_arg.flags;
        result.dst_info_size = dst_info_arg.size;
        result.dst_info_va_len = dst_info_arg.va_len;
        result.dst_gpuaddr = dst_info_arg.gpuaddr;
        result.dst_base_encoded = dst_info_arg.gpuaddr & ~0x3fULL;

        result.dst_mmap_len = dst_alloc_arg.mmapsize;
        result.dst_mmap_offset = (uint64_t)dst_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (dst_alloc_arg.mmapsize < GPU_G4_FILL_BYTES ||
            result.dst_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)dst_alloc_arg.id) {
            result.dst_mmap_rc = -1;
            result.dst_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        dst_map = mmap(NULL,
                       (size_t)dst_alloc_arg.mmapsize,
                       PROT_READ | PROT_WRITE,
                       MAP_SHARED,
                       fd,
                       (off_t)result.dst_mmap_offset);
        result.dst_mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (dst_map == MAP_FAILED) {
            result.dst_mmap_rc = -1;
            result.dst_mmap_errno = errno;
            goto out;
        }
        result.dst_mmap_rc = 0;
        result.dst_mmap_nonnull = dst_map != NULL ? 1 : 0;

        memset(&event_alloc_arg, 0, sizeof(event_alloc_arg));
        event_alloc_arg.size = GPU_G4_EVENT_ALLOC_SIZE;
        event_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &event_alloc_arg) < 0) {
            result.event_alloc_rc = -1;
            result.event_alloc_errno = errno;
            result.event_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.event_alloc_rc = 0;
        result.event_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.event_gpuobj_id = event_alloc_arg.id;
        result.event_alloc_size_out = event_alloc_arg.size;
        result.event_alloc_flags_out = event_alloc_arg.flags;
        result.event_alloc_va_len = event_alloc_arg.va_len;
        result.event_alloc_mmapsize = event_alloc_arg.mmapsize;

        memset(&event_info_arg, 0, sizeof(event_info_arg));
        event_info_arg.id = event_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &event_info_arg) < 0) {
            result.event_info_rc = -1;
            result.event_info_errno = errno;
            result.event_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.event_info_rc = 0;
        result.event_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.event_info_gpuaddr = event_info_arg.gpuaddr;
        result.event_info_flags = event_info_arg.flags;
        result.event_info_size = event_info_arg.size;
        result.event_info_va_len = event_info_arg.va_len;
        result.event_gpuaddr = event_info_arg.gpuaddr;

        {
            uint32_t *dst_words = (uint32_t *)dst_map;
            unsigned int index;

            result.dst_prefill_attempted = 1;
            for (index = 0; index < GPU_G4_FILL_DWORDS; ++index) {
                dst_words[index] = GPU_G4_SENTINEL_PATTERN;
            }
            __sync_synchronize();
            result.dst_prefill_rc = 0;
        }

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            result.cmd_write_attempted = 1;
            if (!gpu_g4_build_solid_fill_pm4(cmd_words,
                                             &pm4_dwords,
                                             dst_info_arg.gpuaddr,
                                             event_info_arg.gpuaddr,
                                             GPU_G4_FILL_PATTERN)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_obj;
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(&sync_obj, 0, sizeof(sync_obj));
            sync_obj.id = cmd_alloc_arg.id;
            sync_obj.offset = 0;
            sync_obj.length = result.cmd_size;
            sync_obj.op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_obj.length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)&sync_obj;
            sync_arg.obj_len = sizeof(sync_obj);
            sync_arg.count = 1;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.cmd_sync_rc = -1;
                result.cmd_sync_errno = errno;
            } else {
                result.cmd_sync_rc = 0;
            }
            result.cmd_sync_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.cmd_sync_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_command_object cmd_obj;
            struct gpu_kgsl_command_object mem_objs[3];
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.offset = 0;
            cmd_obj.gpuaddr = cmd_info_arg.gpuaddr;
            cmd_obj.size = result.cmd_size;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = cmd_alloc_arg.id;

            memset(mem_objs, 0, sizeof(mem_objs));
            mem_objs[0].offset = 0;
            mem_objs[0].gpuaddr = cmd_info_arg.gpuaddr;
            mem_objs[0].size = cmd_info_arg.size;
            mem_objs[0].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[0].id = cmd_alloc_arg.id;
            mem_objs[1].offset = 0;
            mem_objs[1].gpuaddr = dst_info_arg.gpuaddr;
            mem_objs[1].size = dst_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = dst_alloc_arg.id;
            mem_objs[2].offset = 0;
            mem_objs[2].gpuaddr = event_info_arg.gpuaddr;
            mem_objs[2].size = event_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = event_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 3;
            command_arg.context_id = create_arg.drawctxt_id;

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
                result.submit_rc = -1;
                result.submit_errno = errno;
            } else {
                result.submit_rc = 0;
                result.submit_timestamp = command_arg.timestamp;
            }
            result.submit_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.submit_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_timestamp_event_fence fence_arg;
            struct gpu_kgsl_timestamp_event event_arg;

            memset(&fence_arg, 0, sizeof(fence_arg));
            fence_arg.fence_fd = -1;
            memset(&event_arg, 0, sizeof(event_arg));
            event_arg.type = GPU_KGSL_TIMESTAMP_EVENT_FENCE;
            event_arg.timestamp = result.submit_timestamp;
            event_arg.context_id = create_arg.drawctxt_id;
            event_arg.priv = &fence_arg;
            event_arg.len = sizeof(fence_arg);

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_TIMESTAMP_EVENT, &event_arg) < 0) {
                result.timestamp_event_rc = -1;
                result.timestamp_event_errno = errno;
            } else {
                result.timestamp_event_rc = 0;
                fence_fd = fence_arg.fence_fd;
                result.fence_fd = fence_fd;
            }
            result.timestamp_event_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;

            memset(&wait_arg, 0, sizeof(wait_arg));
            wait_arg.context_id = create_arg.drawctxt_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_G4_WAIT_TIMEOUT_MS;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
                result.wait_rc = -1;
                result.wait_errno = errno;
            } else {
                result.wait_rc = 0;
            }
            result.wait_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

            memset(&read_arg, 0, sizeof(read_arg));
            read_arg.context_id = create_arg.drawctxt_id;
            read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
                result.readtimestamp_rc = -1;
                result.readtimestamp_errno = errno;
            } else {
                result.readtimestamp_rc = 0;
                result.retired_timestamp = read_arg.timestamp;
            }
            result.readtimestamp_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        if (result.wait_rc == 0) {
            struct gpu_kgsl_gpuobj_sync_obj sync_obj;
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(&sync_obj, 0, sizeof(sync_obj));
            sync_obj.id = dst_alloc_arg.id;
            sync_obj.offset = 0;
            sync_obj.length = GPU_G4_FILL_BYTES;
            sync_obj.op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.readback_sync_length = sync_obj.length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)&sync_obj;
            sync_arg.obj_len = sizeof(sync_obj);
            sync_arg.count = 1;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.readback_sync_rc = -1;
                result.readback_sync_errno = errno;
            } else {
                result.readback_sync_rc = 0;
            }
            result.readback_sync_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        if (result.readback_sync_rc == 0) {
            uint32_t *dst_words = (uint32_t *)dst_map;
            unsigned int index;

            __sync_synchronize();
            result.readback_verify_attempted = 1;
            result.readback0 = dst_words[0];
            result.readback1 = dst_words[1];
            result.readback2 = dst_words[2];
            result.readback3 = dst_words[3];
            for (index = 0; index < GPU_G4_READBACK_DWORDS; ++index) {
                if (dst_words[index] != GPU_G4_FILL_PATTERN) {
                    result.readback_mismatch_count += 1;
                }
            }
            result.readback_verified = result.readback_mismatch_count == 0 ? 1 : 0;
        }

        if (fence_fd >= 0) {
            struct pollfd pfd;

            memset(&pfd, 0, sizeof(pfd));
            pfd.fd = fence_fd;
            pfd.events = POLLIN;
            result.fence_poll_attempted = 1;
            errno = 0;
            result.fence_poll_rc = poll(&pfd, 1, 0);
            result.fence_poll_errno = result.fence_poll_rc < 0 ? errno : 0;
            result.fence_poll_revents = pfd.revents;
            errno = 0;
            if (close(fence_fd) < 0) {
                result.fence_close_rc = -1;
                result.fence_close_errno = errno;
            } else {
                result.fence_close_rc = 0;
                result.fence_close_errno = 0;
            }
            fence_fd = -1;
        }
    }

out:
    if (fence_fd >= 0) {
        errno = 0;
        if (close(fence_fd) < 0) {
            result.fence_close_rc = -1;
            result.fence_close_errno = errno;
        } else {
            result.fence_close_rc = 0;
            result.fence_close_errno = 0;
        }
    }
    if (dst_map != MAP_FAILED) {
        result.dst_munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(dst_map, (size_t)result.dst_mmap_len) < 0) {
            result.dst_munmap_rc = -1;
            result.dst_munmap_errno = errno;
        } else {
            result.dst_munmap_rc = 0;
            result.dst_munmap_errno = 0;
        }
        result.dst_munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0) {
            result.cmd_munmap_rc = -1;
            result.cmd_munmap_errno = errno;
        } else {
            result.cmd_munmap_rc = 0;
            result.cmd_munmap_errno = 0;
        }
        result.cmd_munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.event_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.event_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.event_free_deferred = 1;
        }
        result.event_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.event_free_rc = -1;
            result.event_free_errno = errno;
        } else {
            result.event_free_rc = 0;
            result.event_free_errno = 0;
        }
        result.event_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.dst_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.dst_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.dst_free_deferred = 1;
        }
        result.dst_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.dst_free_rc = -1;
            result.dst_free_errno = errno;
        } else {
            result.dst_free_rc = 0;
            result.dst_free_errno = 0;
        }
        result.dst_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.cmd_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.cmd_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.cmd_free_deferred = 1;
        }
        result.cmd_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.cmd_free_rc = -1;
            result.cmd_free_errno = errno;
        } else {
            result.cmd_free_rc = 0;
            result.cmd_free_errno = 0;
        }
        result.cmd_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.context_id != 0) {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = result.context_id;
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
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
            result.close_errno = 0;
        }
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static bool gpu_g4_solid_fill_result_ok(const struct gpu_g4_solid_fill_probe_result *result) {
    return result != NULL &&
           result->submit_rc == 0 &&
           result->timestamp_event_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->readback_sync_rc == 0 &&
           result->readback_verified == 1 &&
           result->cmd_free_rc == 0 &&
           result->dst_free_rc == 0 &&
           result->event_free_rc == 0 &&
           result->destroy_rc == 0;
}

static int gpu_g4_solid_fill_collect_child(int timeout_ms,
                                           struct gpu_g4_solid_fill_child_run *run) {
    int pipefd[2];
    long deadline_ms;

    if (run == NULL) {
        return -EINVAL;
    }
    memset(run, 0, sizeof(*run));
    if (pipe(pipefd) < 0) {
        return -errno;
    }
    run->child_pid = fork();
    if (run->child_pid < 0) {
        int saved_errno = errno;

        close(pipefd[0]);
        close(pipefd[1]);
        return -saved_errno;
    }
    if (run->child_pid == 0) {
        close(pipefd[0]);
        return gpu_g4_solid_fill_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;

    while (monotonic_millis() <= deadline_ms) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        int remaining_ms = (int)(deadline_ms > now_ms ? deadline_ms - now_ms : 0);
        int poll_ms = remaining_ms > 50 ? 50 : remaining_ms;
        pid_t wait_rc;

        if (poll_ms < 0) {
            poll_ms = 0;
        }
        pfd.fd = pipefd[0];
        pfd.events = POLLIN | POLLHUP;
        pfd.revents = 0;
        if (poll(&pfd, 1, poll_ms) > 0 && (pfd.revents & (POLLIN | POLLHUP)) != 0) {
            ssize_t rd = read(pipefd[0], &run->result, sizeof(run->result));

            if (rd == (ssize_t)sizeof(run->result)) {
                run->got_result = true;
            }
            break;
        }
        wait_rc = waitpid(run->child_pid, &run->child_status, WNOHANG);
        if (wait_rc == run->child_pid) {
            run->child_reaped = true;
            break;
        }
    }

    if (!run->got_result && !run->child_reaped) {
        run->timed_out = true;
        if (kill(run->child_pid, SIGKILL) == 0) {
            run->child_killed = true;
        }
        if (waitpid(run->child_pid, &run->child_status, 0) == run->child_pid) {
            run->child_reaped = true;
        }
    } else if (!run->child_reaped) {
        if (waitpid(run->child_pid, &run->child_status, 0) == run->child_pid) {
            run->child_reaped = true;
        }
    }
    close(pipefd[0]);
    return run->timed_out ? -ETIMEDOUT : 0;
}

static int gpu_g4_solid_fill_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_g4_solid_fill_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g4.fill.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.g4.fill.version=1\r\n");
    a90_console_printf("gpu.g4.fill.scope=kgsl-a2d-solid-fill-readback-probe\r\n");
    a90_console_printf("gpu.g4.fill.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g4.fill.flags=O_RDWR\r\n");
    a90_console_printf("gpu.g4.fill.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g4.fill.wait_timeout_ms=%u\r\n", GPU_G4_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.g4.fill.parent_enters_open=0\r\n");
    a90_console_printf("gpu.g4.fill.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.g4.fill.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy\r\n");
    a90_console_printf("gpu.g4.fill.pm4_source=mesa-freedreno-a6xx-fd6-clear-buffer-cp-blit-a2d-ccu-color-flush-seqno\r\n");
    a90_console_printf("gpu.g4.fill.post_blit_event=pc_ccu_flush_color_ts_seqno\r\n");
    a90_console_printf("gpu.g4.fill.post_blit_event_payload_dwords=4\r\n");
    a90_console_printf("gpu.g4.fill.event_seqno=0x%x\r\n", GPU_G4_EVENT_SEQNO_VALUE);
    a90_console_printf("gpu.g4.fill.cache_invalidate_event=excluded-after-v3197-incident\r\n");
    a90_console_printf("gpu.g4.fill.pm4_cp_type4=0x%x\r\n", GPU_G3_PM4_CP_TYPE4_PKT);
    a90_console_printf("gpu.g4.fill.pm4_cp_type7=0x%x\r\n", GPU_G3_PM4_CP_TYPE7_PKT);
    a90_console_printf("gpu.g4.fill.fmt6_32_uint=0x%x\r\n", GPU_G4_A6XX_FMT6_32_UINT);
    a90_console_printf("gpu.g4.fill.r2d_int32=0x%x\r\n", GPU_G4_A6XX_R2D_INT32);
    a90_console_printf("gpu.g4.fill.tile6_linear=0x%x\r\n", GPU_G4_A6XX_TILE6_LINEAR);
    a90_console_printf("gpu.g4.fill.fill_bytes=%llu\r\n",
                       (unsigned long long)GPU_G4_FILL_BYTES);
    a90_console_printf("gpu.g4.fill.expected_fill=0x%x\r\n", GPU_G4_FILL_PATTERN);
    a90_console_printf("gpu.g4.fill.sentinel=0x%x\r\n", GPU_G4_SENTINEL_PATTERN);
    a90_console_printf("gpu.g4.fill.cmd_alloc_size=%llu\r\n",
                       (unsigned long long)GPU_G4_CMD_ALLOC_SIZE);
    a90_console_printf("gpu.g4.fill.dst_alloc_size=%llu\r\n",
                       (unsigned long long)GPU_G4_DST_ALLOC_SIZE);
    a90_console_printf("gpu.g4.fill.event_alloc_size=%llu\r\n",
                       (unsigned long long)GPU_G4_EVENT_ALLOC_SIZE);
    a90_console_printf("gpu.g4.fill.rb_dbg_eco_mode=skipped-source-magic-not-in-this-unit\r\n");
    a90_console_printf("gpu.g4.fill.render_attempted=1\r\n");
    a90_console_printf("gpu.g4.fill.triangle_attempted=0\r\n");
    a90_console_printf("gpu.g4.fill.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.g4.fill.power_write_attempted=0\r\n");
    a90_console_printf("gpu.g4.fill.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g4.fill.materialize_requested=1\r\n");
        a90_console_printf("gpu.g4.fill.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g4.fill.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.g4.fill.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.g4.fill.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_g4_solid_fill_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.g4.fill.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.g4.fill.result=%s\r\n",
                       got_result ? (gpu_g4_solid_fill_result_ok(&result) ?
                                     "solid-fill-readback-ok" : "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g4.fill.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.g4.fill.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.g4.fill.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.g4.fill.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.g4.fill.open_elapsed_ms=%ld\r\n", result.open_elapsed_ms);
        a90_console_printf("gpu.g4.fill.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.g4.fill.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.g4.fill.create_elapsed_ms=%ld\r\n", result.create_elapsed_ms);
        a90_console_printf("gpu.g4.fill.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.g4.fill.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.g4.fill.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.g4.fill.context_flags_in=0x%x\r\n", result.flags_in);
        a90_console_printf("gpu.g4.fill.context_flags_out=0x%x\r\n", result.flags_out);
        a90_console_printf("gpu.g4.fill.cmd_alloc_elapsed_ms=%ld\r\n", result.cmd_alloc_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.g4.fill.cmd_alloc_errno=%d\r\n", result.cmd_alloc_errno);
        a90_console_printf("gpu.g4.fill.cmd_gpuobj_id=%u\r\n", result.cmd_gpuobj_id);
        a90_console_printf("gpu.g4.fill.cmd_alloc_size_out=%llu\r\n",
                           (unsigned long long)result.cmd_alloc_size_out);
        a90_console_printf("gpu.g4.fill.cmd_alloc_mmapsize=%llu\r\n",
                           (unsigned long long)result.cmd_alloc_mmapsize);
        a90_console_printf("gpu.g4.fill.cmd_info_elapsed_ms=%ld\r\n", result.cmd_info_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_info_rc=%d\r\n", result.cmd_info_rc);
        a90_console_printf("gpu.g4.fill.cmd_info_errno=%d\r\n", result.cmd_info_errno);
        a90_console_printf("gpu.g4.fill.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.g4.fill.cmd_mmap_elapsed_ms=%ld\r\n", result.cmd_mmap_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_mmap_rc=%d\r\n", result.cmd_mmap_rc);
        a90_console_printf("gpu.g4.fill.cmd_mmap_errno=%d\r\n", result.cmd_mmap_errno);
        a90_console_printf("gpu.g4.fill.cmd_mmap_nonnull=%d\r\n", result.cmd_mmap_nonnull);
        a90_console_printf("gpu.g4.fill.dst_alloc_elapsed_ms=%ld\r\n", result.dst_alloc_elapsed_ms);
        a90_console_printf("gpu.g4.fill.dst_alloc_rc=%d\r\n", result.dst_alloc_rc);
        a90_console_printf("gpu.g4.fill.dst_alloc_errno=%d\r\n", result.dst_alloc_errno);
        a90_console_printf("gpu.g4.fill.dst_gpuobj_id=%u\r\n", result.dst_gpuobj_id);
        a90_console_printf("gpu.g4.fill.dst_alloc_size_out=%llu\r\n",
                           (unsigned long long)result.dst_alloc_size_out);
        a90_console_printf("gpu.g4.fill.dst_alloc_mmapsize=%llu\r\n",
                           (unsigned long long)result.dst_alloc_mmapsize);
        a90_console_printf("gpu.g4.fill.dst_info_elapsed_ms=%ld\r\n", result.dst_info_elapsed_ms);
        a90_console_printf("gpu.g4.fill.dst_info_rc=%d\r\n", result.dst_info_rc);
        a90_console_printf("gpu.g4.fill.dst_info_errno=%d\r\n", result.dst_info_errno);
        a90_console_printf("gpu.g4.fill.dst_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.dst_info_gpuaddr);
        a90_console_printf("gpu.g4.fill.dst_base_encoded=0x%llx\r\n",
                           (unsigned long long)result.dst_base_encoded);
        a90_console_printf("gpu.g4.fill.dst_mmap_elapsed_ms=%ld\r\n", result.dst_mmap_elapsed_ms);
        a90_console_printf("gpu.g4.fill.dst_mmap_rc=%d\r\n", result.dst_mmap_rc);
        a90_console_printf("gpu.g4.fill.dst_mmap_errno=%d\r\n", result.dst_mmap_errno);
        a90_console_printf("gpu.g4.fill.dst_mmap_nonnull=%d\r\n", result.dst_mmap_nonnull);
        a90_console_printf("gpu.g4.fill.event_alloc_elapsed_ms=%ld\r\n",
                           result.event_alloc_elapsed_ms);
        a90_console_printf("gpu.g4.fill.event_alloc_rc=%d\r\n", result.event_alloc_rc);
        a90_console_printf("gpu.g4.fill.event_alloc_errno=%d\r\n",
                           result.event_alloc_errno);
        a90_console_printf("gpu.g4.fill.event_gpuobj_id=%u\r\n", result.event_gpuobj_id);
        a90_console_printf("gpu.g4.fill.event_alloc_size_out=%llu\r\n",
                           (unsigned long long)result.event_alloc_size_out);
        a90_console_printf("gpu.g4.fill.event_alloc_mmapsize=%llu\r\n",
                           (unsigned long long)result.event_alloc_mmapsize);
        a90_console_printf("gpu.g4.fill.event_info_elapsed_ms=%ld\r\n",
                           result.event_info_elapsed_ms);
        a90_console_printf("gpu.g4.fill.event_info_rc=%d\r\n", result.event_info_rc);
        a90_console_printf("gpu.g4.fill.event_info_errno=%d\r\n",
                           result.event_info_errno);
        a90_console_printf("gpu.g4.fill.event_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.event_info_gpuaddr);
        a90_console_printf("gpu.g4.fill.dst_prefill_attempted=%d\r\n",
                           result.dst_prefill_attempted);
        a90_console_printf("gpu.g4.fill.dst_prefill_rc=%d\r\n", result.dst_prefill_rc);
        a90_console_printf("gpu.g4.fill.cmd_write_attempted=%d\r\n",
                           result.cmd_write_attempted);
        a90_console_printf("gpu.g4.fill.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.g4.fill.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.g4.fill.cmd_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_gpuaddr);
        a90_console_printf("gpu.g4.fill.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.g4.fill.cmd_sync_elapsed_ms=%ld\r\n", result.cmd_sync_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_sync_rc=%d\r\n", result.cmd_sync_rc);
        a90_console_printf("gpu.g4.fill.cmd_sync_errno=%d\r\n", result.cmd_sync_errno);
        a90_console_printf("gpu.g4.fill.cmd_sync_length=%llu\r\n",
                           (unsigned long long)result.cmd_sync_length);
        a90_console_printf("gpu.g4.fill.submit_elapsed_ms=%ld\r\n", result.submit_elapsed_ms);
        a90_console_printf("gpu.g4.fill.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.g4.fill.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.g4.fill.submit_timestamp=%u\r\n", result.submit_timestamp);
        a90_console_printf("gpu.g4.fill.timestamp_event_elapsed_ms=%ld\r\n",
                           result.timestamp_event_elapsed_ms);
        a90_console_printf("gpu.g4.fill.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.g4.fill.timestamp_event_errno=%d\r\n",
                           result.timestamp_event_errno);
        a90_console_printf("gpu.g4.fill.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.g4.fill.wait_elapsed_ms=%ld\r\n", result.wait_elapsed_ms);
        a90_console_printf("gpu.g4.fill.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.g4.fill.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.g4.fill.readtimestamp_elapsed_ms=%ld\r\n",
                           result.readtimestamp_elapsed_ms);
        a90_console_printf("gpu.g4.fill.readtimestamp_rc=%d\r\n", result.readtimestamp_rc);
        a90_console_printf("gpu.g4.fill.readtimestamp_errno=%d\r\n",
                           result.readtimestamp_errno);
        a90_console_printf("gpu.g4.fill.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.g4.fill.readback_sync_elapsed_ms=%ld\r\n",
                           result.readback_sync_elapsed_ms);
        a90_console_printf("gpu.g4.fill.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.g4.fill.readback_sync_errno=%d\r\n",
                           result.readback_sync_errno);
        a90_console_printf("gpu.g4.fill.readback_sync_length=%llu\r\n",
                           (unsigned long long)result.readback_sync_length);
        a90_console_printf("gpu.g4.fill.readback_verify_attempted=%d\r\n",
                           result.readback_verify_attempted);
        a90_console_printf("gpu.g4.fill.readback_verified=%d\r\n",
                           result.readback_verified);
        a90_console_printf("gpu.g4.fill.readback_mismatch_count=%d\r\n",
                           result.readback_mismatch_count);
        a90_console_printf("gpu.g4.fill.readback0=0x%x\r\n", result.readback0);
        a90_console_printf("gpu.g4.fill.readback1=0x%x\r\n", result.readback1);
        a90_console_printf("gpu.g4.fill.readback2=0x%x\r\n", result.readback2);
        a90_console_printf("gpu.g4.fill.readback3=0x%x\r\n", result.readback3);
        a90_console_printf("gpu.g4.fill.fence_poll_attempted=%d\r\n",
                           result.fence_poll_attempted);
        a90_console_printf("gpu.g4.fill.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.g4.fill.fence_poll_errno=%d\r\n",
                           result.fence_poll_errno);
        a90_console_printf("gpu.g4.fill.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.g4.fill.fence_close_rc=%d\r\n", result.fence_close_rc);
        a90_console_printf("gpu.g4.fill.fence_close_errno=%d\r\n",
                           result.fence_close_errno);
        a90_console_printf("gpu.g4.fill.dst_munmap_attempted=%d\r\n",
                           result.dst_munmap_attempted);
        a90_console_printf("gpu.g4.fill.dst_munmap_elapsed_ms=%ld\r\n",
                           result.dst_munmap_elapsed_ms);
        a90_console_printf("gpu.g4.fill.dst_munmap_rc=%d\r\n", result.dst_munmap_rc);
        a90_console_printf("gpu.g4.fill.dst_munmap_errno=%d\r\n",
                           result.dst_munmap_errno);
        a90_console_printf("gpu.g4.fill.cmd_munmap_attempted=%d\r\n",
                           result.cmd_munmap_attempted);
        a90_console_printf("gpu.g4.fill.cmd_munmap_elapsed_ms=%ld\r\n",
                           result.cmd_munmap_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_munmap_rc=%d\r\n", result.cmd_munmap_rc);
        a90_console_printf("gpu.g4.fill.cmd_munmap_errno=%d\r\n",
                           result.cmd_munmap_errno);
        a90_console_printf("gpu.g4.fill.dst_free_attempted=%d\r\n",
                           result.dst_free_attempted);
        a90_console_printf("gpu.g4.fill.dst_free_deferred=%d\r\n",
                           result.dst_free_deferred);
        a90_console_printf("gpu.g4.fill.dst_free_elapsed_ms=%ld\r\n",
                           result.dst_free_elapsed_ms);
        a90_console_printf("gpu.g4.fill.dst_free_rc=%d\r\n", result.dst_free_rc);
        a90_console_printf("gpu.g4.fill.dst_free_errno=%d\r\n",
                           result.dst_free_errno);
        a90_console_printf("gpu.g4.fill.cmd_free_attempted=%d\r\n",
                           result.cmd_free_attempted);
        a90_console_printf("gpu.g4.fill.cmd_free_deferred=%d\r\n",
                           result.cmd_free_deferred);
        a90_console_printf("gpu.g4.fill.cmd_free_elapsed_ms=%ld\r\n",
                           result.cmd_free_elapsed_ms);
        a90_console_printf("gpu.g4.fill.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.g4.fill.cmd_free_errno=%d\r\n",
                           result.cmd_free_errno);
        a90_console_printf("gpu.g4.fill.event_free_attempted=%d\r\n",
                           result.event_free_attempted);
        a90_console_printf("gpu.g4.fill.event_free_deferred=%d\r\n",
                           result.event_free_deferred);
        a90_console_printf("gpu.g4.fill.event_free_elapsed_ms=%ld\r\n",
                           result.event_free_elapsed_ms);
        a90_console_printf("gpu.g4.fill.event_free_rc=%d\r\n", result.event_free_rc);
        a90_console_printf("gpu.g4.fill.event_free_errno=%d\r\n",
                           result.event_free_errno);
        a90_console_printf("gpu.g4.fill.destroy_attempted=%d\r\n",
                           result.destroy_attempted);
        a90_console_printf("gpu.g4.fill.destroy_elapsed_ms=%ld\r\n",
                           result.destroy_elapsed_ms);
        a90_console_printf("gpu.g4.fill.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.g4.fill.destroy_errno=%d\r\n", result.destroy_errno);
        a90_console_printf("gpu.g4.fill.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.g4.fill.close_errno=%d\r\n", result.close_errno);
        a90_console_printf("gpu.g4.fill.total_elapsed_ms=%ld\r\n", result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static bool gpu_h1_shader_state_result_ok(const struct gpu_h1_shader_state_probe_result *result) {
    return result != NULL &&
           result->shader_write_rc == 0 &&
           result->cmd_write_rc == 0 &&
           result->sync_rc == 0 &&
           result->submit_rc == 0 &&
           result->timestamp_event_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->cmd_free_rc == 0 &&
           result->vs_free_rc == 0 &&
           result->fs_free_rc == 0 &&
           result->destroy_rc == 0;
}

static int gpu_h1_shader_state_probe_child(int write_fd) {
    static const uint32_t vs_shader[GPU_H1_VS_SHADER_DWORDS] = {
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
    };
    static const uint32_t fs_shader[GPU_H1_FS_SHADER_DWORDS] = {
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
    };
    struct gpu_h1_shader_state_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    void *cmd_map = MAP_FAILED;
    void *vs_map = MAP_FAILED;
    void *fs_map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.vs_alloc_rc = -1;
    result.vs_info_rc = -1;
    result.vs_mmap_rc = -1;
    result.fs_alloc_rc = -1;
    result.fs_info_rc = -1;
    result.fs_mmap_rc = -1;
    result.shader_write_rc = -1;
    result.cmd_write_rc = -1;
    result.sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.cmd_munmap_rc = -1;
    result.vs_munmap_rc = -1;
    result.fs_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.vs_free_rc = -1;
    result.fs_free_rc = -1;
    result.destroy_rc = -1;
    result.flags_in = GPU_G1_CONTEXT_FLAGS;
    result.flags_out = GPU_G1_CONTEXT_FLAGS;
    result.wait_timeout_ms = GPU_H1_WAIT_TIMEOUT_MS;
    result.vs_shader_dwords = GPU_H1_VS_SHADER_DWORDS;
    result.fs_shader_dwords = GPU_H1_FS_SHADER_DWORDS;
    result.cp_load_state6_geom = GPU_H1_PM4_CP_LOAD_STATE6_GEOM;
    result.cp_load_state6_frag = GPU_H1_PM4_CP_LOAD_STATE6_FRAG;
    result.fence_fd = -1;

    errno = 0;
    stage_started_ms = monotonic_millis();
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    result.open_elapsed_ms = monotonic_millis() - stage_started_ms;
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        goto out;
    }
    result.open_rc = 0;

    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    stage_started_ms = monotonic_millis();
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
        goto out;
    }
    result.create_rc = 0;
    result.create_elapsed_ms = monotonic_millis() - stage_started_ms;
    result.context_id = create_arg.drawctxt_id;
    result.flags_out = create_arg.flags;

    {
        struct gpu_kgsl_gpuobj_alloc cmd_alloc_arg;
        struct gpu_kgsl_gpuobj_info cmd_info_arg;
        struct gpu_kgsl_gpuobj_alloc vs_alloc_arg;
        struct gpu_kgsl_gpuobj_info vs_info_arg;
        struct gpu_kgsl_gpuobj_alloc fs_alloc_arg;
        struct gpu_kgsl_gpuobj_info fs_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t vs_mmap_offset;
        uint64_t fs_mmap_offset;

        memset(&cmd_alloc_arg, 0, sizeof(cmd_alloc_arg));
        cmd_alloc_arg.size = GPU_H1_CMD_ALLOC_SIZE;
        cmd_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &cmd_alloc_arg) < 0) {
            result.cmd_alloc_rc = -1;
            result.cmd_alloc_errno = errno;
            result.cmd_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.cmd_alloc_rc = 0;
        result.cmd_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.cmd_gpuobj_id = cmd_alloc_arg.id;

        memset(&cmd_info_arg, 0, sizeof(cmd_info_arg));
        cmd_info_arg.id = cmd_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &cmd_info_arg) < 0) {
            result.cmd_info_rc = -1;
            result.cmd_info_errno = errno;
            result.cmd_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.cmd_info_rc = 0;
        result.cmd_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.cmd_info_gpuaddr = cmd_info_arg.gpuaddr;
        result.cmd_mmap_len = cmd_alloc_arg.mmapsize;

        cmd_mmap_offset = (uint64_t)cmd_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (cmd_alloc_arg.mmapsize < (uint64_t)GPU_H1_CMD_MAX_DWORDS * 4ULL ||
            cmd_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)cmd_alloc_arg.id) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        cmd_map = mmap(NULL, (size_t)cmd_alloc_arg.mmapsize,
                       PROT_READ | PROT_WRITE, MAP_SHARED, fd,
                       (off_t)cmd_mmap_offset);
        result.cmd_mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (cmd_map == MAP_FAILED) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = errno;
            goto out;
        }
        result.cmd_mmap_rc = 0;

        memset(&vs_alloc_arg, 0, sizeof(vs_alloc_arg));
        vs_alloc_arg.size = GPU_H1_SHADER_ALLOC_SIZE;
        vs_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &vs_alloc_arg) < 0) {
            result.vs_alloc_rc = -1;
            result.vs_alloc_errno = errno;
            result.vs_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.vs_alloc_rc = 0;
        result.vs_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.vs_gpuobj_id = vs_alloc_arg.id;

        memset(&vs_info_arg, 0, sizeof(vs_info_arg));
        vs_info_arg.id = vs_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &vs_info_arg) < 0) {
            result.vs_info_rc = -1;
            result.vs_info_errno = errno;
            result.vs_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.vs_info_rc = 0;
        result.vs_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.vs_info_gpuaddr = vs_info_arg.gpuaddr;
        result.vs_mmap_len = vs_alloc_arg.mmapsize;

        vs_mmap_offset = (uint64_t)vs_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (vs_alloc_arg.mmapsize < sizeof(vs_shader) ||
            vs_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)vs_alloc_arg.id) {
            result.vs_mmap_rc = -1;
            result.vs_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        vs_map = mmap(NULL, (size_t)vs_alloc_arg.mmapsize,
                      PROT_READ | PROT_WRITE, MAP_SHARED, fd,
                      (off_t)vs_mmap_offset);
        result.vs_mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (vs_map == MAP_FAILED) {
            result.vs_mmap_rc = -1;
            result.vs_mmap_errno = errno;
            goto out;
        }
        result.vs_mmap_rc = 0;

        memset(&fs_alloc_arg, 0, sizeof(fs_alloc_arg));
        fs_alloc_arg.size = GPU_H1_SHADER_ALLOC_SIZE;
        fs_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &fs_alloc_arg) < 0) {
            result.fs_alloc_rc = -1;
            result.fs_alloc_errno = errno;
            result.fs_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.fs_alloc_rc = 0;
        result.fs_alloc_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.fs_gpuobj_id = fs_alloc_arg.id;

        memset(&fs_info_arg, 0, sizeof(fs_info_arg));
        fs_info_arg.id = fs_alloc_arg.id;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &fs_info_arg) < 0) {
            result.fs_info_rc = -1;
            result.fs_info_errno = errno;
            result.fs_info_elapsed_ms = monotonic_millis() - stage_started_ms;
            goto out;
        }
        result.fs_info_rc = 0;
        result.fs_info_elapsed_ms = monotonic_millis() - stage_started_ms;
        result.fs_info_gpuaddr = fs_info_arg.gpuaddr;
        result.fs_mmap_len = fs_alloc_arg.mmapsize;

        fs_mmap_offset = (uint64_t)fs_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (fs_alloc_arg.mmapsize < sizeof(fs_shader) ||
            fs_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)fs_alloc_arg.id) {
            result.fs_mmap_rc = -1;
            result.fs_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        stage_started_ms = monotonic_millis();
        fs_map = mmap(NULL, (size_t)fs_alloc_arg.mmapsize,
                      PROT_READ | PROT_WRITE, MAP_SHARED, fd,
                      (off_t)fs_mmap_offset);
        result.fs_mmap_elapsed_ms = monotonic_millis() - stage_started_ms;
        if (fs_map == MAP_FAILED) {
            result.fs_mmap_rc = -1;
            result.fs_mmap_errno = errno;
            goto out;
        }
        result.fs_mmap_rc = 0;

        result.shader_write_attempted = 1;
        memcpy(vs_map, vs_shader, sizeof(vs_shader));
        memcpy(fs_map, fs_shader, sizeof(fs_shader));
        __sync_synchronize();
        result.shader_write_rc = 0;

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            result.cmd_write_attempted = 1;
            if (!gpu_h1_build_shader_state_pm4(cmd_words,
                                               &pm4_dwords,
                                               vs_info_arg.gpuaddr,
                                               fs_info_arg.gpuaddr)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[3];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = vs_alloc_arg.id;
            sync_objs[1].length = sizeof(vs_shader);
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = fs_alloc_arg.id;
            sync_objs[2].length = sizeof(fs_shader);
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.vs_sync_length = sync_objs[1].length;
            result.fs_sync_length = sync_objs[2].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 3;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.sync_rc = -1;
                result.sync_errno = errno;
            } else {
                result.sync_rc = 0;
            }
            result.sync_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.sync_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_command_object cmd_obj;
            struct gpu_kgsl_command_object mem_objs[3];
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.gpuaddr = cmd_info_arg.gpuaddr;
            cmd_obj.size = result.cmd_size;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = cmd_alloc_arg.id;

            memset(mem_objs, 0, sizeof(mem_objs));
            mem_objs[0].gpuaddr = cmd_info_arg.gpuaddr;
            mem_objs[0].size = cmd_info_arg.size;
            mem_objs[0].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[0].id = cmd_alloc_arg.id;
            mem_objs[1].gpuaddr = vs_info_arg.gpuaddr;
            mem_objs[1].size = vs_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = vs_alloc_arg.id;
            mem_objs[2].gpuaddr = fs_info_arg.gpuaddr;
            mem_objs[2].size = fs_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = fs_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 3;
            command_arg.context_id = create_arg.drawctxt_id;

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
                result.submit_rc = -1;
                result.submit_errno = errno;
            } else {
                result.submit_rc = 0;
                result.submit_timestamp = command_arg.timestamp;
            }
            result.submit_elapsed_ms = monotonic_millis() - stage_started_ms;
            if (result.submit_rc < 0) {
                goto out;
            }
        }

        {
            struct gpu_kgsl_timestamp_event_fence fence_arg;
            struct gpu_kgsl_timestamp_event event_arg;

            memset(&fence_arg, 0, sizeof(fence_arg));
            fence_arg.fence_fd = -1;
            memset(&event_arg, 0, sizeof(event_arg));
            event_arg.type = GPU_KGSL_TIMESTAMP_EVENT_FENCE;
            event_arg.timestamp = result.submit_timestamp;
            event_arg.context_id = create_arg.drawctxt_id;
            event_arg.priv = &fence_arg;
            event_arg.len = sizeof(fence_arg);

            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_TIMESTAMP_EVENT, &event_arg) < 0) {
                result.timestamp_event_rc = -1;
                result.timestamp_event_errno = errno;
            } else {
                result.timestamp_event_rc = 0;
                fence_fd = fence_arg.fence_fd;
                result.fence_fd = fence_fd;
            }
            result.timestamp_event_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;

            memset(&wait_arg, 0, sizeof(wait_arg));
            wait_arg.context_id = create_arg.drawctxt_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_H1_WAIT_TIMEOUT_MS;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
                result.wait_rc = -1;
                result.wait_errno = errno;
            } else {
                result.wait_rc = 0;
            }
            result.wait_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        {
            struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

            memset(&read_arg, 0, sizeof(read_arg));
            read_arg.context_id = create_arg.drawctxt_id;
            read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
            errno = 0;
            stage_started_ms = monotonic_millis();
            if (ioctl(fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
                result.readtimestamp_rc = -1;
                result.readtimestamp_errno = errno;
            } else {
                result.readtimestamp_rc = 0;
                result.retired_timestamp = read_arg.timestamp;
            }
            result.readtimestamp_elapsed_ms = monotonic_millis() - stage_started_ms;
        }

        if (fence_fd >= 0) {
            struct pollfd pfd;

            memset(&pfd, 0, sizeof(pfd));
            pfd.fd = fence_fd;
            pfd.events = POLLIN;
            result.fence_poll_attempted = 1;
            errno = 0;
            result.fence_poll_rc = poll(&pfd, 1, 0);
            result.fence_poll_errno = result.fence_poll_rc < 0 ? errno : 0;
            result.fence_poll_revents = pfd.revents;
            errno = 0;
            if (close(fence_fd) < 0) {
                result.fence_close_rc = -1;
                result.fence_close_errno = errno;
            } else {
                result.fence_close_rc = 0;
                result.fence_close_errno = 0;
            }
            fence_fd = -1;
        }
    }

out:
    if (fence_fd >= 0) {
        errno = 0;
        if (close(fence_fd) < 0) {
            result.fence_close_rc = -1;
            result.fence_close_errno = errno;
        } else {
            result.fence_close_rc = 0;
            result.fence_close_errno = 0;
        }
    }
    if (fs_map != MAP_FAILED) {
        result.fs_munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(fs_map, (size_t)result.fs_mmap_len) < 0) {
            result.fs_munmap_rc = -1;
            result.fs_munmap_errno = errno;
        } else {
            result.fs_munmap_rc = 0;
        }
        result.fs_munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (vs_map != MAP_FAILED) {
        result.vs_munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(vs_map, (size_t)result.vs_mmap_len) < 0) {
            result.vs_munmap_rc = -1;
            result.vs_munmap_errno = errno;
        } else {
            result.vs_munmap_rc = 0;
        }
        result.vs_munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0) {
            result.cmd_munmap_rc = -1;
            result.cmd_munmap_errno = errno;
        } else {
            result.cmd_munmap_rc = 0;
        }
        result.cmd_munmap_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.fs_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.fs_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.fs_free_deferred = 1;
        }
        result.fs_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.fs_free_rc = -1;
            result.fs_free_errno = errno;
        } else {
            result.fs_free_rc = 0;
        }
        result.fs_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.vs_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.vs_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.vs_free_deferred = 1;
        }
        result.vs_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.vs_free_rc = -1;
            result.vs_free_errno = errno;
        } else {
            result.vs_free_rc = 0;
        }
        result.vs_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.cmd_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.cmd_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.cmd_free_deferred = 1;
        }
        result.cmd_free_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.cmd_free_rc = -1;
            result.cmd_free_errno = errno;
        } else {
            result.cmd_free_rc = 0;
        }
        result.cmd_free_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0 && result.context_id != 0) {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = result.context_id;
        result.destroy_attempted = 1;
        errno = 0;
        stage_started_ms = monotonic_millis();
        if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_DESTROY, &destroy_arg) < 0) {
            result.destroy_rc = -1;
            result.destroy_errno = errno;
        } else {
            result.destroy_rc = 0;
        }
        result.destroy_elapsed_ms = monotonic_millis() - stage_started_ms;
    }
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
        }
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_h1_shader_state_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_h1_shader_state_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.h1.shader.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.h1.shader.version=1\r\n");
    a90_console_printf("gpu.h1.shader.scope=first-triangle-h1-shader-upload-sp-state-no-draw\r\n");
    a90_console_printf("gpu.h1.shader.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.h1.shader.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.h1.shader.wait_timeout_ms=%u\r\n", GPU_H1_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.h1.shader.parent_enters_open=0\r\n");
    a90_console_printf("gpu.h1.shader.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.h1.shader.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy\r\n");
    a90_console_printf("gpu.h1.shader.source=mesa-freedreno-a6xx-fd6-program-sp-state-plus-adreno-pm4-cp-load-state6\r\n");
    a90_console_printf("gpu.h1.shader.shader_source=hand-assembled-ir3-placeholder-no-full-compiler-no-execute\r\n");
    a90_console_printf("gpu.h1.shader.shader_execution_attempted=0\r\n");
    a90_console_printf("gpu.h1.shader.draw_attempted=0\r\n");
    a90_console_printf("gpu.h1.shader.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.h1.shader.power_write_attempted=0\r\n");
    a90_console_printf("gpu.h1.shader.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.h1.shader.materialize_requested=1\r\n");
        a90_console_printf("gpu.h1.shader.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.h1.shader.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.h1.shader.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.h1.shader.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_h1_shader_state_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.h1.shader.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.h1.shader.result=%s\r\n",
                       got_result ? (gpu_h1_shader_state_result_ok(&result) ?
                                     "shader-state-retired-no-draw" : "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.h1.shader.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.h1.shader.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.h1.shader.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.h1.shader.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.h1.shader.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.h1.shader.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.h1.shader.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.h1.shader.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.h1.shader.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.h1.shader.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.h1.shader.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.h1.shader.cmd_mmap_len=%llu\r\n",
                           (unsigned long long)result.cmd_mmap_len);
        a90_console_printf("gpu.h1.shader.vs_alloc_rc=%d\r\n", result.vs_alloc_rc);
        a90_console_printf("gpu.h1.shader.vs_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.vs_info_gpuaddr);
        a90_console_printf("gpu.h1.shader.vs_mmap_len=%llu\r\n",
                           (unsigned long long)result.vs_mmap_len);
        a90_console_printf("gpu.h1.shader.fs_alloc_rc=%d\r\n", result.fs_alloc_rc);
        a90_console_printf("gpu.h1.shader.fs_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.fs_info_gpuaddr);
        a90_console_printf("gpu.h1.shader.fs_mmap_len=%llu\r\n",
                           (unsigned long long)result.fs_mmap_len);
        a90_console_printf("gpu.h1.shader.vs_shader_dwords=%u\r\n", result.vs_shader_dwords);
        a90_console_printf("gpu.h1.shader.fs_shader_dwords=%u\r\n", result.fs_shader_dwords);
        a90_console_printf("gpu.h1.shader.cp_load_state6_geom=0x%x\r\n", result.cp_load_state6_geom);
        a90_console_printf("gpu.h1.shader.cp_load_state6_frag=0x%x\r\n", result.cp_load_state6_frag);
        a90_console_printf("gpu.h1.shader.shader_write_rc=%d\r\n", result.shader_write_rc);
        a90_console_printf("gpu.h1.shader.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.h1.shader.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.h1.shader.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.h1.shader.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.h1.shader.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.h1.shader.cmd_sync_length=%llu\r\n",
                           (unsigned long long)result.cmd_sync_length);
        a90_console_printf("gpu.h1.shader.vs_sync_length=%llu\r\n",
                           (unsigned long long)result.vs_sync_length);
        a90_console_printf("gpu.h1.shader.fs_sync_length=%llu\r\n",
                           (unsigned long long)result.fs_sync_length);
        a90_console_printf("gpu.h1.shader.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.h1.shader.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.h1.shader.submit_timestamp=%u\r\n", result.submit_timestamp);
        a90_console_printf("gpu.h1.shader.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.h1.shader.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.h1.shader.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.h1.shader.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.h1.shader.readtimestamp_rc=%d\r\n",
                           result.readtimestamp_rc);
        a90_console_printf("gpu.h1.shader.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.h1.shader.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.h1.shader.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.h1.shader.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.h1.shader.vs_free_rc=%d\r\n", result.vs_free_rc);
        a90_console_printf("gpu.h1.shader.fs_free_rc=%d\r\n", result.fs_free_rc);
        a90_console_printf("gpu.h1.shader.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.h1.shader.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.h1.shader.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static bool gpu_h2_3d_state_result_ok(const struct gpu_h2_3d_state_probe_result *result) {
    return result != NULL &&
           result->color_init_rc == 0 &&
           result->cmd_write_rc == 0 &&
           result->sync_rc == 0 &&
           result->submit_rc == 0 &&
           result->timestamp_event_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->cmd_free_rc == 0 &&
           result->color_free_rc == 0 &&
           result->destroy_rc == 0;
}

static int gpu_h2_3d_state_probe_child(int write_fd) {
    struct gpu_h2_3d_state_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *color_map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.color_alloc_rc = -1;
    result.color_info_rc = -1;
    result.color_mmap_rc = -1;
    result.color_init_rc = -1;
    result.cmd_write_rc = -1;
    result.sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.cmd_munmap_rc = -1;
    result.color_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.color_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_H2_WAIT_TIMEOUT_MS;
    result.color_width = GPU_H2_COLOR_WIDTH;
    result.color_height = GPU_H2_COLOR_HEIGHT;
    result.color_stride = GPU_H2_COLOR_STRIDE;
    result.color_format = GPU_G4_A6XX_FMT6_32_UINT;
    result.color_bytes = GPU_H2_COLOR_ALLOC_SIZE;
    result.draw_attempted = 0;
    result.shader_execution_attempted = 0;
    result.kms_blit_attempted = 0;
    result.fence_fd = -1;

    errno = 0;
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        goto out;
    }
    result.open_rc = 0;

    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        goto out;
    }
    result.create_rc = 0;
    result.context_id = create_arg.drawctxt_id;

    {
        struct gpu_kgsl_gpuobj_alloc cmd_alloc_arg;
        struct gpu_kgsl_gpuobj_info cmd_info_arg;
        struct gpu_kgsl_gpuobj_alloc color_alloc_arg;
        struct gpu_kgsl_gpuobj_info color_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t color_mmap_offset;

        memset(&cmd_alloc_arg, 0, sizeof(cmd_alloc_arg));
        cmd_alloc_arg.size = GPU_H2_CMD_ALLOC_SIZE;
        cmd_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &cmd_alloc_arg) < 0) {
            result.cmd_alloc_rc = -1;
            result.cmd_alloc_errno = errno;
            goto out;
        }
        result.cmd_alloc_rc = 0;
        result.cmd_gpuobj_id = cmd_alloc_arg.id;

        memset(&cmd_info_arg, 0, sizeof(cmd_info_arg));
        cmd_info_arg.id = cmd_alloc_arg.id;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &cmd_info_arg) < 0) {
            result.cmd_info_rc = -1;
            result.cmd_info_errno = errno;
            goto out;
        }
        result.cmd_info_rc = 0;
        result.cmd_info_gpuaddr = cmd_info_arg.gpuaddr;
        result.cmd_mmap_len = cmd_alloc_arg.mmapsize;

        cmd_mmap_offset = (uint64_t)cmd_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (cmd_alloc_arg.mmapsize < (uint64_t)GPU_H2_CMD_MAX_DWORDS * 4ULL ||
            cmd_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)cmd_alloc_arg.id) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        cmd_map = mmap(NULL, (size_t)cmd_alloc_arg.mmapsize,
                       PROT_READ | PROT_WRITE, MAP_SHARED, fd,
                       (off_t)cmd_mmap_offset);
        if (cmd_map == MAP_FAILED) {
            result.cmd_mmap_rc = -1;
            result.cmd_mmap_errno = errno;
            goto out;
        }
        result.cmd_mmap_rc = 0;

        memset(&color_alloc_arg, 0, sizeof(color_alloc_arg));
        color_alloc_arg.size = GPU_H2_COLOR_ALLOC_SIZE;
        color_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &color_alloc_arg) < 0) {
            result.color_alloc_rc = -1;
            result.color_alloc_errno = errno;
            goto out;
        }
        result.color_alloc_rc = 0;
        result.color_gpuobj_id = color_alloc_arg.id;

        memset(&color_info_arg, 0, sizeof(color_info_arg));
        color_info_arg.id = color_alloc_arg.id;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &color_info_arg) < 0) {
            result.color_info_rc = -1;
            result.color_info_errno = errno;
            goto out;
        }
        result.color_info_rc = 0;
        result.color_info_gpuaddr = color_info_arg.gpuaddr;
        result.color_mmap_len = color_alloc_arg.mmapsize;

        color_mmap_offset = (uint64_t)color_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE;
        if (color_alloc_arg.mmapsize < GPU_H2_COLOR_ALLOC_SIZE ||
            color_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)color_alloc_arg.id) {
            result.color_mmap_rc = -1;
            result.color_mmap_errno = EINVAL;
            goto out;
        }
        errno = 0;
        color_map = mmap(NULL, (size_t)color_alloc_arg.mmapsize,
                         PROT_READ | PROT_WRITE, MAP_SHARED, fd,
                         (off_t)color_mmap_offset);
        if (color_map == MAP_FAILED) {
            result.color_mmap_rc = -1;
            result.color_mmap_errno = errno;
            goto out;
        }
        result.color_mmap_rc = 0;

        {
            uint32_t *color_words = (uint32_t *)color_map;
            unsigned int index;

            for (index = 0; index < (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL); ++index) {
                color_words[index] = GPU_H2_CLEAR_PATTERN;
            }
            __sync_synchronize();
            result.color_init_rc = 0;
        }

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;
            unsigned int state_reg_writes = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            if (!gpu_h2_build_3d_state_pm4(cmd_words,
                                           &pm4_dwords,
                                           &state_reg_writes,
                                           color_info_arg.gpuaddr)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.state_reg_writes = state_reg_writes;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[2];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_alloc_arg.id;
            sync_objs[1].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.color_sync_length = sync_objs[1].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 2;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.sync_rc = -1;
                result.sync_errno = errno;
                goto out;
            }
            result.sync_rc = 0;
        }

        {
            struct gpu_kgsl_command_object cmd_obj;
            struct gpu_kgsl_command_object mem_objs[2];
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.gpuaddr = cmd_info_arg.gpuaddr;
            cmd_obj.size = result.cmd_size;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = cmd_alloc_arg.id;

            memset(mem_objs, 0, sizeof(mem_objs));
            mem_objs[0].gpuaddr = cmd_info_arg.gpuaddr;
            mem_objs[0].size = cmd_info_arg.size;
            mem_objs[0].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[0].id = cmd_alloc_arg.id;
            mem_objs[1].gpuaddr = color_info_arg.gpuaddr;
            mem_objs[1].size = color_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = color_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 2;
            command_arg.context_id = create_arg.drawctxt_id;

            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
                result.submit_rc = -1;
                result.submit_errno = errno;
                goto out;
            }
            result.submit_rc = 0;
            result.submit_timestamp = command_arg.timestamp;
        }

        {
            struct gpu_kgsl_timestamp_event_fence fence_arg;
            struct gpu_kgsl_timestamp_event event_arg;

            memset(&fence_arg, 0, sizeof(fence_arg));
            fence_arg.fence_fd = -1;
            memset(&event_arg, 0, sizeof(event_arg));
            event_arg.type = GPU_KGSL_TIMESTAMP_EVENT_FENCE;
            event_arg.timestamp = result.submit_timestamp;
            event_arg.context_id = create_arg.drawctxt_id;
            event_arg.priv = &fence_arg;
            event_arg.len = sizeof(fence_arg);
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_TIMESTAMP_EVENT, &event_arg) < 0) {
                result.timestamp_event_rc = -1;
                result.timestamp_event_errno = errno;
            } else {
                result.timestamp_event_rc = 0;
                fence_fd = fence_arg.fence_fd;
                result.fence_fd = fence_fd;
            }
        }

        {
            struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;

            memset(&wait_arg, 0, sizeof(wait_arg));
            wait_arg.context_id = create_arg.drawctxt_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_H2_WAIT_TIMEOUT_MS;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
                result.wait_rc = -1;
                result.wait_errno = errno;
            } else {
                result.wait_rc = 0;
            }
        }

        {
            struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

            memset(&read_arg, 0, sizeof(read_arg));
            read_arg.context_id = create_arg.drawctxt_id;
            read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
                result.readtimestamp_rc = -1;
                result.readtimestamp_errno = errno;
            } else {
                result.readtimestamp_rc = 0;
                result.retired_timestamp = read_arg.timestamp;
            }
        }

        if (fence_fd >= 0) {
            struct pollfd pfd;

            memset(&pfd, 0, sizeof(pfd));
            pfd.fd = fence_fd;
            pfd.events = POLLIN;
            result.fence_poll_attempted = 1;
            errno = 0;
            result.fence_poll_rc = poll(&pfd, 1, 0);
            result.fence_poll_errno = result.fence_poll_rc < 0 ? errno : 0;
            result.fence_poll_revents = pfd.revents;
            errno = 0;
            if (close(fence_fd) < 0) {
                result.fence_close_rc = -1;
                result.fence_close_errno = errno;
            } else {
                result.fence_close_rc = 0;
                result.fence_close_errno = 0;
            }
            fence_fd = -1;
        }
    }

out:
    if (fence_fd >= 0) {
        errno = 0;
        if (close(fence_fd) < 0) {
            result.fence_close_rc = -1;
            result.fence_close_errno = errno;
        } else {
            result.fence_close_rc = 0;
            result.fence_close_errno = 0;
        }
    }
    if (color_map != MAP_FAILED) {
        result.color_munmap_attempted = 1;
        errno = 0;
        if (munmap(color_map, (size_t)result.color_mmap_len) < 0) {
            result.color_munmap_rc = -1;
            result.color_munmap_errno = errno;
        } else {
            result.color_munmap_rc = 0;
        }
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        if (munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0) {
            result.cmd_munmap_rc = -1;
            result.cmd_munmap_errno = errno;
        } else {
            result.cmd_munmap_rc = 0;
        }
    }
    if (fd >= 0 && result.color_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.color_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.color_free_deferred = 1;
        }
        result.color_free_attempted = 1;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.color_free_rc = -1;
            result.color_free_errno = errno;
        } else {
            result.color_free_rc = 0;
        }
    }
    if (fd >= 0 && result.cmd_gpuobj_id != 0) {
        struct gpu_kgsl_gpuobj_free free_arg;
        struct gpu_kgsl_gpu_event_timestamp event_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        memset(&event_arg, 0, sizeof(event_arg));
        free_arg.id = result.cmd_gpuobj_id;
        if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) {
            event_arg.context_id = result.context_id;
            event_arg.timestamp = result.submit_timestamp;
            free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT;
            free_arg.priv = (uint64_t)(uintptr_t)&event_arg;
            free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP;
            free_arg.len = sizeof(event_arg);
            result.cmd_free_deferred = 1;
        }
        result.cmd_free_attempted = 1;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) {
            result.cmd_free_rc = -1;
            result.cmd_free_errno = errno;
        } else {
            result.cmd_free_rc = 0;
        }
    }
    if (fd >= 0 && result.context_id != 0) {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = result.context_id;
        result.destroy_attempted = 1;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_DESTROY, &destroy_arg) < 0) {
            result.destroy_rc = -1;
            result.destroy_errno = errno;
        } else {
            result.destroy_rc = 0;
        }
    }
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
        }
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_h2_3d_state_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_h2_3d_state_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.h2.state.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.h2.state.version=1\r\n");
    a90_console_printf("gpu.h2.state.scope=first-triangle-h2-3d-fixed-function-state-no-draw\r\n");
    a90_console_printf("gpu.h2.state.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.h2.state.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.h2.state.wait_timeout_ms=%u\r\n", GPU_H2_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.h2.state.parent_enters_open=0\r\n");
    a90_console_printf("gpu.h2.state.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.h2.state.source=mesa-freedreno-a6xx-fd6-emit-draw-plus-a6xx-xml\r\n");
    a90_console_printf("gpu.h2.state.offscreen=u32-linear-128x128\r\n");
    a90_console_printf("gpu.h2.state.draw_attempted=0\r\n");
    a90_console_printf("gpu.h2.state.shader_execution_attempted=0\r\n");
    a90_console_printf("gpu.h2.state.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.h2.state.power_write_attempted=0\r\n");
    a90_console_printf("gpu.h2.state.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.h2.state.materialize_requested=1\r\n");
        a90_console_printf("gpu.h2.state.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.h2.state.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.h2.state.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.h2.state.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_h2_3d_state_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.h2.state.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.h2.state.result=%s\r\n",
                       got_result ? (gpu_h2_3d_state_result_ok(&result) ?
                                     "3d-state-retired-no-draw" : "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.h2.state.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.h2.state.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.h2.state.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.h2.state.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.h2.state.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.h2.state.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.h2.state.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.h2.state.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.h2.state.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.h2.state.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.h2.state.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.h2.state.cmd_mmap_len=%llu\r\n",
                           (unsigned long long)result.cmd_mmap_len);
        a90_console_printf("gpu.h2.state.color_alloc_rc=%d\r\n", result.color_alloc_rc);
        a90_console_printf("gpu.h2.state.color_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.color_info_gpuaddr);
        a90_console_printf("gpu.h2.state.color_mmap_len=%llu\r\n",
                           (unsigned long long)result.color_mmap_len);
        a90_console_printf("gpu.h2.state.color_width=%u\r\n", result.color_width);
        a90_console_printf("gpu.h2.state.color_height=%u\r\n", result.color_height);
        a90_console_printf("gpu.h2.state.color_stride=%u\r\n", result.color_stride);
        a90_console_printf("gpu.h2.state.color_bytes=%llu\r\n",
                           (unsigned long long)result.color_bytes);
        a90_console_printf("gpu.h2.state.color_format=0x%x\r\n", result.color_format);
        a90_console_printf("gpu.h2.state.color_init_rc=%d\r\n", result.color_init_rc);
        a90_console_printf("gpu.h2.state.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.h2.state.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.h2.state.state_reg_writes=%u\r\n", result.state_reg_writes);
        a90_console_printf("gpu.h2.state.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.h2.state.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.h2.state.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.h2.state.cmd_sync_length=%llu\r\n",
                           (unsigned long long)result.cmd_sync_length);
        a90_console_printf("gpu.h2.state.color_sync_length=%llu\r\n",
                           (unsigned long long)result.color_sync_length);
        a90_console_printf("gpu.h2.state.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.h2.state.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.h2.state.submit_timestamp=%u\r\n", result.submit_timestamp);
        a90_console_printf("gpu.h2.state.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.h2.state.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.h2.state.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.h2.state.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.h2.state.readtimestamp_rc=%d\r\n",
                           result.readtimestamp_rc);
        a90_console_printf("gpu.h2.state.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.h2.state.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.h2.state.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.h2.state.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.h2.state.color_free_rc=%d\r\n", result.color_free_rc);
        a90_console_printf("gpu.h2.state.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.h2.state.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.h2.state.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static bool gpu_h3_draw_envelope_result_retired(const struct gpu_h3_draw_envelope_probe_result *result) {
    return result != NULL &&
           result->color_init_rc == 0 &&
           result->shader_write_rc == 0 &&
           result->vertex_write_rc == 0 &&
           result->cmd_write_rc == 0 &&
           result->sync_rc == 0 &&
           result->submit_rc == 0 &&
           result->timestamp_event_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->readback_sync_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->cmd_free_rc == 0 &&
           result->color_free_rc == 0 &&
           result->event_free_rc == 0 &&
           result->vs_free_rc == 0 &&
           result->fs_free_rc == 0 &&
           result->vertex_free_rc == 0 &&
           result->destroy_rc == 0;
}

static int gpu_h3_draw_envelope_probe_child(int write_fd) {
    static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS] = {
        GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO, GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI,
        GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO, GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI,
        GPU_H3_IR3_F32_0_LO, GPU_H3_IR3_MOV_F32F32_R0Z_HI,
        GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0W_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
        0x00000000U, 0x00000000U,
    };
    static const uint32_t fs_shader[GPU_H3_FS_SHADER_DWORDS] = {
        GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0X_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
    };
    static const uint32_t vertex_words[GPU_H3_VERTEX_DWORDS] = {
        0xbf400000U, 0xbf400000U,
        0x3f400000U, 0xbf400000U,
        0x00000000U, 0x3f400000U,
    };
    struct gpu_h3_draw_envelope_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *color_map = MAP_FAILED;
    void *vs_map = MAP_FAILED;
    void *fs_map = MAP_FAILED;
    void *vertex_map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.color_alloc_rc = -1;
    result.color_info_rc = -1;
    result.color_mmap_rc = -1;
    result.event_alloc_rc = -1;
    result.event_info_rc = -1;
    result.vs_alloc_rc = -1;
    result.vs_info_rc = -1;
    result.vs_mmap_rc = -1;
    result.fs_alloc_rc = -1;
    result.fs_info_rc = -1;
    result.fs_mmap_rc = -1;
    result.vertex_alloc_rc = -1;
    result.vertex_info_rc = -1;
    result.vertex_mmap_rc = -1;
    result.color_init_rc = -1;
    result.shader_write_rc = -1;
    result.vertex_write_rc = -1;
    result.cmd_write_rc = -1;
    result.sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.readback_sync_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.cmd_munmap_rc = -1;
    result.color_munmap_rc = -1;
    result.vs_munmap_rc = -1;
    result.fs_munmap_rc = -1;
    result.vertex_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.color_free_rc = -1;
    result.event_free_rc = -1;
    result.vs_free_rc = -1;
    result.fs_free_rc = -1;
    result.vertex_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_H3_WAIT_TIMEOUT_MS;
    result.color_width = GPU_H2_COLOR_WIDTH;
    result.color_height = GPU_H2_COLOR_HEIGHT;
    result.color_stride = GPU_H2_COLOR_STRIDE;
    result.color_format = GPU_H3_COLOR_FORMAT;
    result.color_bytes = GPU_H2_COLOR_ALLOC_SIZE;
    result.vertex_stride = GPU_H3_VERTEX_STRIDE;
    result.vertex_bytes = (unsigned int)GPU_H3_VERTEX_BYTES;
    result.vertex_count = GPU_H3_VERTEX_COUNT;
    result.vertex_format = GPU_H3_A6XX_FMT6_32_32_FLOAT;
    result.cp_draw_packet = GPU_H3_PM4_CP_DRAW_INDX_OFFSET;
    result.draw_initiator = gpu_h3_draw_initiator();
    result.num_instances = 1U;
    result.num_indices = GPU_H3_VERTEX_COUNT;
    result.draw_attempted = 1;
    result.shader_execution_attempted = 1;
    result.kms_blit_attempted = 0;
    result.fence_fd = -1;

    errno = 0;
    fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        result.open_rc = -1;
        result.open_errno = errno;
        goto out;
    }
    result.open_rc = 0;

    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        result.create_rc = -1;
        result.create_errno = errno;
        goto out;
    }
    result.create_rc = 0;
    result.context_id = create_arg.drawctxt_id;

    {
        struct gpu_kgsl_gpuobj_alloc cmd_alloc_arg;
        struct gpu_kgsl_gpuobj_info cmd_info_arg;
        struct gpu_kgsl_gpuobj_alloc color_alloc_arg;
        struct gpu_kgsl_gpuobj_info color_info_arg;
        struct gpu_kgsl_gpuobj_alloc event_alloc_arg;
        struct gpu_kgsl_gpuobj_info event_info_arg;
        struct gpu_kgsl_gpuobj_alloc vs_alloc_arg;
        struct gpu_kgsl_gpuobj_info vs_info_arg;
        struct gpu_kgsl_gpuobj_alloc fs_alloc_arg;
        struct gpu_kgsl_gpuobj_info fs_info_arg;
        struct gpu_kgsl_gpuobj_alloc vertex_alloc_arg;
        struct gpu_kgsl_gpuobj_info vertex_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t color_mmap_offset;
        uint64_t vs_mmap_offset;
        uint64_t fs_mmap_offset;
        uint64_t vertex_mmap_offset;

#define GPU_H3_ALLOC_INFO_MMAP(name, size_value, min_size_value) \
        do { \
            memset(&name##_alloc_arg, 0, sizeof(name##_alloc_arg)); \
            name##_alloc_arg.size = (size_value); \
            name##_alloc_arg.flags = GPU_G4_ALLOC_FLAGS; \
            errno = 0; \
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &name##_alloc_arg) < 0) { \
                result.name##_alloc_rc = -1; \
                result.name##_alloc_errno = errno; \
                goto out; \
            } \
            result.name##_alloc_rc = 0; \
            result.name##_gpuobj_id = name##_alloc_arg.id; \
            memset(&name##_info_arg, 0, sizeof(name##_info_arg)); \
            name##_info_arg.id = name##_alloc_arg.id; \
            errno = 0; \
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &name##_info_arg) < 0) { \
                result.name##_info_rc = -1; \
                result.name##_info_errno = errno; \
                goto out; \
            } \
            result.name##_info_rc = 0; \
            result.name##_info_gpuaddr = name##_info_arg.gpuaddr; \
            result.name##_mmap_len = name##_alloc_arg.mmapsize; \
            name##_mmap_offset = (uint64_t)name##_alloc_arg.id * GPU_G2_MMAP_PAGE_SIZE; \
            if (name##_alloc_arg.mmapsize < (uint64_t)(min_size_value) || \
                name##_mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)name##_alloc_arg.id) { \
                result.name##_mmap_rc = -1; \
                result.name##_mmap_errno = EINVAL; \
                goto out; \
            } \
            errno = 0; \
            name##_map = mmap(NULL, (size_t)name##_alloc_arg.mmapsize, \
                              PROT_READ | PROT_WRITE, MAP_SHARED, fd, \
                              (off_t)name##_mmap_offset); \
            if (name##_map == MAP_FAILED) { \
                result.name##_mmap_rc = -1; \
                result.name##_mmap_errno = errno; \
                goto out; \
            } \
            result.name##_mmap_rc = 0; \
        } while (0)

        GPU_H3_ALLOC_INFO_MMAP(cmd, GPU_H3_CMD_ALLOC_SIZE,
                               (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL);
        GPU_H3_ALLOC_INFO_MMAP(color, GPU_H2_COLOR_ALLOC_SIZE,
                               GPU_H2_COLOR_ALLOC_SIZE);

        memset(&event_alloc_arg, 0, sizeof(event_alloc_arg));
        event_alloc_arg.size = GPU_H3_EVENT_ALLOC_SIZE;
        event_alloc_arg.flags = GPU_G4_ALLOC_FLAGS;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &event_alloc_arg) < 0) {
            result.event_alloc_rc = -1;
            result.event_alloc_errno = errno;
            goto out;
        }
        result.event_alloc_rc = 0;
        result.event_gpuobj_id = event_alloc_arg.id;
        result.event_size = event_alloc_arg.size;
        memset(&event_info_arg, 0, sizeof(event_info_arg));
        event_info_arg.id = event_alloc_arg.id;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &event_info_arg) < 0) {
            result.event_info_rc = -1;
            result.event_info_errno = errno;
            goto out;
        }
        result.event_info_rc = 0;
        result.event_info_gpuaddr = event_info_arg.gpuaddr;

        GPU_H3_ALLOC_INFO_MMAP(vs, GPU_H1_SHADER_ALLOC_SIZE, sizeof(vs_shader));
        GPU_H3_ALLOC_INFO_MMAP(fs, GPU_H1_SHADER_ALLOC_SIZE, sizeof(fs_shader));
        GPU_H3_ALLOC_INFO_MMAP(vertex, GPU_H3_VERTEX_ALLOC_SIZE, GPU_H3_VERTEX_BYTES);
#undef GPU_H3_ALLOC_INFO_MMAP

        {
            uint32_t *color_words = (uint32_t *)color_map;
            unsigned int index;

            for (index = 0; index < (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL); ++index) {
                color_words[index] = GPU_H2_CLEAR_PATTERN;
            }
            __sync_synchronize();
            result.color_init_rc = 0;
        }

        memcpy(vs_map, vs_shader, sizeof(vs_shader));
        memcpy(fs_map, fs_shader, sizeof(fs_shader));
        __sync_synchronize();
        result.shader_write_rc = 0;

        memcpy(vertex_map, vertex_words, sizeof(vertex_words));
        __sync_synchronize();
        result.vertex_write_rc = 0;

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;
            unsigned int state_reg_writes = 0;
            unsigned int vfd_reg_writes = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            if (!gpu_h3_build_draw_envelope_pm4(cmd_words,
                                                &pm4_dwords,
                                                &state_reg_writes,
                                                &vfd_reg_writes,
                                                color_info_arg.gpuaddr,
                                                event_info_arg.gpuaddr,
                                                vs_info_arg.gpuaddr,
                                                fs_info_arg.gpuaddr,
                                                vertex_info_arg.gpuaddr)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.state_reg_writes = state_reg_writes;
            result.vfd_reg_writes = vfd_reg_writes;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[6];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_alloc_arg.id;
            sync_objs[1].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = event_alloc_arg.id;
            sync_objs[2].length = GPU_H3_EVENT_ALLOC_SIZE;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[3].id = vs_alloc_arg.id;
            sync_objs[3].length = sizeof(vs_shader);
            sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[4].id = fs_alloc_arg.id;
            sync_objs[4].length = sizeof(fs_shader);
            sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[5].id = vertex_alloc_arg.id;
            sync_objs[5].length = GPU_H3_VERTEX_BYTES;
            sync_objs[5].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.color_sync_length = sync_objs[1].length;
            result.event_sync_length = sync_objs[2].length;
            result.vs_sync_length = sync_objs[3].length;
            result.fs_sync_length = sync_objs[4].length;
            result.vertex_sync_length = sync_objs[5].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 6;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.sync_rc = -1;
                result.sync_errno = errno;
                goto out;
            }
            result.sync_rc = 0;
        }

        {
            struct gpu_kgsl_command_object cmd_obj;
            struct gpu_kgsl_command_object mem_objs[6];
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.gpuaddr = cmd_info_arg.gpuaddr;
            cmd_obj.size = result.cmd_size;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = cmd_alloc_arg.id;

            memset(mem_objs, 0, sizeof(mem_objs));
            mem_objs[0].gpuaddr = cmd_info_arg.gpuaddr;
            mem_objs[0].size = cmd_info_arg.size;
            mem_objs[0].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[0].id = cmd_alloc_arg.id;
            mem_objs[1].gpuaddr = color_info_arg.gpuaddr;
            mem_objs[1].size = color_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = color_alloc_arg.id;
            mem_objs[2].gpuaddr = event_info_arg.gpuaddr;
            mem_objs[2].size = event_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = event_alloc_arg.id;
            mem_objs[3].gpuaddr = vs_info_arg.gpuaddr;
            mem_objs[3].size = vs_info_arg.size;
            mem_objs[3].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[3].id = vs_alloc_arg.id;
            mem_objs[4].gpuaddr = fs_info_arg.gpuaddr;
            mem_objs[4].size = fs_info_arg.size;
            mem_objs[4].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[4].id = fs_alloc_arg.id;
            mem_objs[5].gpuaddr = vertex_info_arg.gpuaddr;
            mem_objs[5].size = vertex_info_arg.size;
            mem_objs[5].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[5].id = vertex_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 6;
            command_arg.context_id = create_arg.drawctxt_id;

            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
                result.submit_rc = -1;
                result.submit_errno = errno;
                goto out;
            }
            result.submit_rc = 0;
            result.submit_timestamp = command_arg.timestamp;
        }

        {
            struct gpu_kgsl_timestamp_event_fence fence_arg;
            struct gpu_kgsl_timestamp_event event_arg;

            memset(&fence_arg, 0, sizeof(fence_arg));
            fence_arg.fence_fd = -1;
            memset(&event_arg, 0, sizeof(event_arg));
            event_arg.type = GPU_KGSL_TIMESTAMP_EVENT_FENCE;
            event_arg.timestamp = result.submit_timestamp;
            event_arg.context_id = create_arg.drawctxt_id;
            event_arg.priv = &fence_arg;
            event_arg.len = sizeof(fence_arg);
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_TIMESTAMP_EVENT, &event_arg) < 0) {
                result.timestamp_event_rc = -1;
                result.timestamp_event_errno = errno;
            } else {
                result.timestamp_event_rc = 0;
                fence_fd = fence_arg.fence_fd;
                result.fence_fd = fence_fd;
            }
        }

        {
            struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;

            memset(&wait_arg, 0, sizeof(wait_arg));
            wait_arg.context_id = create_arg.drawctxt_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_H3_WAIT_TIMEOUT_MS;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
                result.wait_rc = -1;
                result.wait_errno = errno;
            } else {
                result.wait_rc = 0;
            }
        }

        {
            struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

            memset(&read_arg, 0, sizeof(read_arg));
            read_arg.context_id = create_arg.drawctxt_id;
            read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
                result.readtimestamp_rc = -1;
                result.readtimestamp_errno = errno;
            } else {
                result.readtimestamp_rc = 0;
                result.retired_timestamp = read_arg.timestamp;
            }
        }

        if (result.wait_rc == 0) {
            struct gpu_kgsl_gpuobj_sync_obj sync_obj;
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(&sync_obj, 0, sizeof(sync_obj));
            sync_obj.id = color_alloc_arg.id;
            sync_obj.length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_obj.op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.readback_sync_length = sync_obj.length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)&sync_obj;
            sync_arg.obj_len = sizeof(sync_obj);
            sync_arg.count = 1;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.readback_sync_rc = -1;
                result.readback_sync_errno = errno;
            } else {
                uint32_t *color_words = (uint32_t *)color_map;
                unsigned int word_count = (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL);
                unsigned int index;
                unsigned int center_index =
                    (GPU_H2_COLOR_HEIGHT / 2U) * GPU_H2_COLOR_WIDTH +
                    (GPU_H2_COLOR_WIDTH / 2U);

                result.readback_sync_rc = 0;
                result.readback0 = color_words[0];
                result.readback_center = color_words[center_index];
                result.readback_first_changed_index = UINT_MAX;
                for (index = 0; index < word_count; ++index) {
                    if (color_words[index] != GPU_H2_CLEAR_PATTERN) {
                        if (result.readback_changed_count == 0) {
                            result.readback_first_changed_index = index;
                            result.readback_first_changed_value = color_words[index];
                        }
                        result.readback_changed_count += 1U;
                    }
                }
            }
        }

        if (fence_fd >= 0) {
            struct pollfd pfd;

            memset(&pfd, 0, sizeof(pfd));
            pfd.fd = fence_fd;
            pfd.events = POLLIN;
            result.fence_poll_attempted = 1;
            errno = 0;
            result.fence_poll_rc = poll(&pfd, 1, 0);
            result.fence_poll_errno = result.fence_poll_rc < 0 ? errno : 0;
            result.fence_poll_revents = pfd.revents;
            errno = 0;
            if (close(fence_fd) < 0) {
                result.fence_close_rc = -1;
                result.fence_close_errno = errno;
            } else {
                result.fence_close_rc = 0;
                result.fence_close_errno = 0;
            }
            fence_fd = -1;
        }
    }

out:
    if (fence_fd >= 0) {
        errno = 0;
        if (close(fence_fd) < 0) {
            result.fence_close_rc = -1;
            result.fence_close_errno = errno;
        } else {
            result.fence_close_rc = 0;
            result.fence_close_errno = 0;
        }
    }
    if (vertex_map != MAP_FAILED) {
        result.vertex_munmap_attempted = 1;
        errno = 0;
        result.vertex_munmap_rc =
            munmap(vertex_map, (size_t)result.vertex_mmap_len) < 0 ? -1 : 0;
        result.vertex_munmap_errno = result.vertex_munmap_rc < 0 ? errno : 0;
    }
    if (fs_map != MAP_FAILED) {
        result.fs_munmap_attempted = 1;
        errno = 0;
        result.fs_munmap_rc =
            munmap(fs_map, (size_t)result.fs_mmap_len) < 0 ? -1 : 0;
        result.fs_munmap_errno = result.fs_munmap_rc < 0 ? errno : 0;
    }
    if (vs_map != MAP_FAILED) {
        result.vs_munmap_attempted = 1;
        errno = 0;
        result.vs_munmap_rc =
            munmap(vs_map, (size_t)result.vs_mmap_len) < 0 ? -1 : 0;
        result.vs_munmap_errno = result.vs_munmap_rc < 0 ? errno : 0;
    }
    if (color_map != MAP_FAILED) {
        result.color_munmap_attempted = 1;
        errno = 0;
        result.color_munmap_rc =
            munmap(color_map, (size_t)result.color_mmap_len) < 0 ? -1 : 0;
        result.color_munmap_errno = result.color_munmap_rc < 0 ? errno : 0;
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        result.cmd_munmap_rc =
            munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0 ? -1 : 0;
        result.cmd_munmap_errno = result.cmd_munmap_rc < 0 ? errno : 0;
    }

#define GPU_H3_FREE_FIELD(name) \
    do { \
        if (fd >= 0 && result.name##_gpuobj_id != 0) { \
            struct gpu_kgsl_gpuobj_free free_arg; \
            struct gpu_kgsl_gpu_event_timestamp event_arg; \
            memset(&free_arg, 0, sizeof(free_arg)); \
            memset(&event_arg, 0, sizeof(event_arg)); \
            free_arg.id = result.name##_gpuobj_id; \
            if (result.submit_rc == 0 && result.wait_rc != 0 && result.submit_timestamp != 0) { \
                event_arg.context_id = result.context_id; \
                event_arg.timestamp = result.submit_timestamp; \
                free_arg.flags = GPU_KGSL_GPUOBJ_FREE_ON_EVENT; \
                free_arg.priv = (uint64_t)(uintptr_t)&event_arg; \
                free_arg.type = GPU_KGSL_GPU_EVENT_TIMESTAMP; \
                free_arg.len = sizeof(event_arg); \
                result.name##_free_deferred = 1; \
            } \
            result.name##_free_attempted = 1; \
            errno = 0; \
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg) < 0) { \
                result.name##_free_rc = -1; \
                result.name##_free_errno = errno; \
            } else { \
                result.name##_free_rc = 0; \
                result.name##_free_errno = 0; \
            } \
        } \
    } while (0)

    GPU_H3_FREE_FIELD(vertex);
    GPU_H3_FREE_FIELD(fs);
    GPU_H3_FREE_FIELD(vs);
    GPU_H3_FREE_FIELD(event);
    GPU_H3_FREE_FIELD(color);
    GPU_H3_FREE_FIELD(cmd);
#undef GPU_H3_FREE_FIELD

    if (fd >= 0 && result.context_id != 0) {
        struct gpu_kgsl_drawctxt_destroy destroy_arg;

        memset(&destroy_arg, 0, sizeof(destroy_arg));
        destroy_arg.drawctxt_id = result.context_id;
        result.destroy_attempted = 1;
        errno = 0;
        if (ioctl(fd, GPU_IOCTL_KGSL_DRAWCTXT_DESTROY, &destroy_arg) < 0) {
            result.destroy_rc = -1;
            result.destroy_errno = errno;
        } else {
            result.destroy_rc = 0;
            result.destroy_errno = 0;
        }
    }
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result.close_rc = -1;
            result.close_errno = errno;
        } else {
            result.close_rc = 0;
            result.close_errno = 0;
        }
    }
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_h3_draw_envelope_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_h3_draw_envelope_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.h3.draw.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.h3.draw.version=1\r\n");
    a90_console_printf("gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader\r\n");
    a90_console_printf("gpu.h3.draw.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.h3.draw.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.h3.draw.wait_timeout_ms=%u\r\n", GPU_H3_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.h3.draw.parent_enters_open=0\r\n");
    a90_console_printf("gpu.h3.draw.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.h3.draw.source=mesa-freedreno-a6xx-fd6-draw-plus-vfd-fetch-dest\r\n");
    a90_console_printf("gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler\r\n");
    a90_console_printf("gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map\r\n");
    a90_console_printf("gpu.h3.draw.vs_shader_dwords=%u\r\n", GPU_H3_VS_SHADER_DWORDS);
    a90_console_printf("gpu.h3.draw.fs_shader_dwords=%u\r\n", GPU_H3_FS_SHADER_DWORDS);
    a90_console_printf("gpu.h3.draw.vs_output_regid=0x%x\r\n", GPU_H3_VS_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.ps_output_regid=0x%x\r\n", GPU_H3_PS_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.sp_vs_output_reg0=0x%x\r\n", GPU_H3_SP_VS_OUTPUT_REG0);
    a90_console_printf("gpu.h3.draw.shader_mode_source=mesa-freedreno-a6xx-fd6-emit-shader-regs-sp-tpl1-mode\r\n");
    a90_console_printf("gpu.h3.draw.sp_fullregfootprint=%u\r\n", GPU_H3_SP_FULLREGFOOTPRINT);
    a90_console_printf("gpu.h3.draw.sp_mode_cntl=0x%x\r\n", GPU_H3_SP_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_mode_cntl=0x%x\r\n", GPU_H3_TPL1_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero\r\n");
    a90_console_printf("gpu.h3.draw.gras_cl_interp_cntl=0x%x\r\n",
                       GPU_H3_GRAS_CL_INTERP_CNTL);
    a90_console_printf("gpu.h3.draw.rb_interp_cntl=0x%x\r\n",
                       GPU_H3_RB_INTERP_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ps_input_cntl=0x%x\r\n",
                       GPU_H3_RB_PS_INPUT_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ps_samplefreq_cntl=0x%x\r\n",
                       GPU_H3_RB_PS_SAMPLEFREQ_CNTL);
    a90_console_printf("gpu.h3.draw.gras_lrz_ps_input_cntl=0x%x\r\n",
                       GPU_H3_GRAS_LRZ_PS_INPUT_CNTL);
    a90_console_printf("gpu.h3.draw.gras_lrz_ps_samplefreq_cntl=0x%x\r\n",
                       GPU_H3_GRAS_LRZ_PS_SAMPLEFREQ_CNTL);
    a90_console_printf("gpu.h3.draw.sp_cntl0_source=mesa-freedreno-a6xx-sp-footprint-mergedregs\r\n");
    a90_console_printf("gpu.h3.draw.sp_vs_cntl0=0x%x\r\n", GPU_H3_SP_VS_CNTL_0);
    a90_console_printf("gpu.h3.draw.sp_ps_cntl0=0x%x\r\n", GPU_H3_SP_PS_CNTL_0);
    a90_console_printf("gpu.h3.draw.raster_coverage_source=mesa-freedreno-a6xx-gras-rb-msaa-defaults\r\n");
    a90_console_printf("gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x\r\n", 0U);
    a90_console_printf("gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x\r\n", 1U << 2);
    a90_console_printf("gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x\r\n", 0U);
    a90_console_printf("gpu.h3.draw.sample_location_source=mesa-freedreno-a6xx-fd6-context-sample-location-disable-stateobj\r\n");
    a90_console_printf("gpu.h3.draw.gras_sc_msaa_sample_pos_cntl=0x%x\r\n",
                       GPU_H3_GRAS_SC_MSAA_SAMPLE_POS_CNTL);
    a90_console_printf("gpu.h3.draw.rb_msaa_sample_pos_cntl=0x%x\r\n",
                       GPU_H3_RB_MSAA_SAMPLE_POS_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_msaa_sample_pos_cntl=0x%x\r\n",
                       GPU_H3_TPL1_MSAA_SAMPLE_POS_CNTL);
    a90_console_printf("gpu.h3.draw.render_marker_source=mesa-freedreno-a6xx-fd6-set-render-mode-rm6-direct-render\r\n");
    a90_console_printf("gpu.h3.draw.cp_set_marker=0x%x\r\n",
                       GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER);
    a90_console_printf("gpu.h3.draw.rb_render_cntl_source=mesa-freedreno-a6xx-fd6-gmem-update-render-cntl-ccu-single-cacheline\r\n");
    a90_console_printf("gpu.h3.draw.rb_render_cntl=0x%x\r\n", GPU_H3_RB_RENDER_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2\r\n");
    a90_console_printf("gpu.h3.draw.rb_ccu_cntl=0x%x\r\n", GPU_H3_RB_CCU_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ccu_color_offset=0x%x\r\n",
                       GPU_H3_RB_CCU_COLOR_OFFSET);
    a90_console_printf("gpu.h3.draw.rb_ccu_depth_offset=0x%x\r\n",
                       GPU_H3_RB_CCU_DEPTH_OFFSET);
    a90_console_printf("gpu.h3.draw.vpc_linkage_source=mesa-freedreno-a6xx-position-psizeloc-clip-cull-linkage\r\n");
    a90_console_printf("gpu.h3.draw.vpc_vs_cntl=0x%x\r\n", GPU_H3_VPC_VS_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x\r\n",
                       GPU_H3_VPC_VS_CLIP_CULL_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x\r\n",
                       GPU_H3_VPC_VS_CLIP_CULL_CNTL);
    a90_console_printf("gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x\r\n",
                       GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE);
    a90_console_printf("gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-emit-vpc-position-only-siv\r\n");
    a90_console_printf("gpu.h3.draw.vpc_varying_lm_transfer_cntl0=0x%x\r\n",
                       GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0);
    a90_console_printf("gpu.h3.draw.vpc_varying_lm_transfer_cntl1=0x%x\r\n",
                       GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL1);
    a90_console_printf("gpu.h3.draw.vpc_varying_lm_transfer_cntl2=0x%x\r\n",
                       GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL2);
    a90_console_printf("gpu.h3.draw.vpc_varying_lm_transfer_cntl3=0x%x\r\n",
                       GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL3);
    a90_console_printf("gpu.h3.draw.vpc_vs_siv_cntl=0x%x\r\n",
                       GPU_H3_VPC_VS_SIV_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_vs_siv_cntl_v2=0x%x\r\n",
                       GPU_H3_VPC_VS_SIV_CNTL_V2);
    a90_console_printf("gpu.h3.draw.gras_su_vs_siv_cntl=0x%x\r\n",
                       GPU_H3_GRAS_SU_VS_SIV_CNTL);
    a90_console_printf("gpu.h3.draw.static_context_source=mesa-freedreno-a6xx-fd6-emit-static-context-regs\r\n");
    a90_console_printf("gpu.h3.draw.gras_su_conservative_ras_cntl=0x%x\r\n",
                       GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_unknown_9210=0x%x\r\n",
                       GPU_H3_VPC_UNKNOWN_9210);
    a90_console_printf("gpu.h3.draw.vpc_so_override=0x%x\r\n",
                       GPU_H3_VPC_SO_OVERRIDE);
    a90_console_printf("gpu.h3.draw.vpc_rast_stream_cntl=0x%x\r\n",
                       GPU_H3_VPC_RAST_STREAM_CNTL);
    a90_console_printf("gpu.h3.draw.pc_stereo_rendering_cntl=0x%x\r\n",
                       GPU_H3_PC_STEREO_RENDERING_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_ps_swizzle_cntl=0x%x\r\n",
                       GPU_H3_TPL1_PS_SWIZZLE_CNTL);
    a90_console_printf("gpu.h3.draw.sp_reg_prog_id_3=0x%x\r\n",
                       GPU_H3_SP_REG_PROG_ID_3);
    a90_console_printf("gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0\r\n");
    a90_console_printf("gpu.h3.draw.ir3_end_opcode_hi=0x%x\r\n", GPU_H1_IR3_END_HI);
    a90_console_printf("gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x%x\r\n",
                       GPU_H3_IR3_MOV_F32F32_R0X_HI);
    a90_console_printf("gpu.h3.draw.fs_color_f32_bits=0x%x\r\n",
                       GPU_H3_IR3_F32_1_LO);
    a90_console_printf("gpu.h3.draw.color_output_mask=0x%x\r\n",
                       GPU_H3_COLOR_OUTPUT_MASK);
    a90_console_printf("gpu.h3.draw.vertex_format=fmt6-32-32-float\r\n");
    a90_console_printf("gpu.h3.draw.offscreen=f32-linear-128x128\r\n");
    a90_console_printf("gpu.h3.draw.draw_attempted=1\r\n");
    a90_console_printf("gpu.h3.draw.shader_execution_attempted=1\r\n");
    a90_console_printf("gpu.h3.draw.readback_change_expected=1\r\n");
    a90_console_printf("gpu.h3.draw.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.h3.draw.power_write_attempted=0\r\n");
    a90_console_printf("gpu.h3.draw.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.h3.draw.materialize_requested=1\r\n");
        a90_console_printf("gpu.h3.draw.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.h3.draw.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.h3.draw.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.h3.draw.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_h3_draw_envelope_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.h3.draw.child_pid=%ld\r\n", (long)pid);

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
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    } else if (!child_reaped) {
        if (waitpid(pid, &child_status, 0) == pid) {
            child_reaped = true;
        }
    }
    close(pipefd[0]);

    a90_console_printf("gpu.h3.draw.result=%s\r\n",
                       got_result ? (gpu_h3_draw_envelope_result_retired(&result) ?
                                     (result.readback_changed_count > 0 ?
                                      "draw-retired-readback-changed" :
                                      "draw-retired-readback-unchanged") :
                                     "returned-error") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.h3.draw.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.h3.draw.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.h3.draw.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.h3.draw.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.h3.draw.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.h3.draw.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.h3.draw.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.h3.draw.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.h3.draw.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.h3.draw.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.h3.draw.color_alloc_rc=%d\r\n", result.color_alloc_rc);
        a90_console_printf("gpu.h3.draw.event_alloc_rc=%d\r\n", result.event_alloc_rc);
        a90_console_printf("gpu.h3.draw.vs_alloc_rc=%d\r\n", result.vs_alloc_rc);
        a90_console_printf("gpu.h3.draw.fs_alloc_rc=%d\r\n", result.fs_alloc_rc);
        a90_console_printf("gpu.h3.draw.vertex_alloc_rc=%d\r\n", result.vertex_alloc_rc);
        a90_console_printf("gpu.h3.draw.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.color_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.color_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.event_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.event_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.vs_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.vs_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.fs_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.fs_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.vertex_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.vertex_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.color_width=%u\r\n", result.color_width);
        a90_console_printf("gpu.h3.draw.color_height=%u\r\n", result.color_height);
        a90_console_printf("gpu.h3.draw.color_stride=%u\r\n", result.color_stride);
        a90_console_printf("gpu.h3.draw.color_bytes=%llu\r\n",
                           (unsigned long long)result.color_bytes);
        a90_console_printf("gpu.h3.draw.color_format=0x%x\r\n", result.color_format);
        a90_console_printf("gpu.h3.draw.vertex_stride=%u\r\n", result.vertex_stride);
        a90_console_printf("gpu.h3.draw.vertex_bytes=%u\r\n", result.vertex_bytes);
        a90_console_printf("gpu.h3.draw.vertex_count=%u\r\n", result.vertex_count);
        a90_console_printf("gpu.h3.draw.vertex_format=0x%x\r\n", result.vertex_format);
        a90_console_printf("gpu.h3.draw.cp_draw_packet=0x%x\r\n", result.cp_draw_packet);
        a90_console_printf("gpu.h3.draw.draw_initiator=0x%x\r\n", result.draw_initiator);
        a90_console_printf("gpu.h3.draw.num_instances=%u\r\n", result.num_instances);
        a90_console_printf("gpu.h3.draw.num_indices=%u\r\n", result.num_indices);
        a90_console_printf("gpu.h3.draw.color_init_rc=%d\r\n", result.color_init_rc);
        a90_console_printf("gpu.h3.draw.shader_write_rc=%d\r\n", result.shader_write_rc);
        a90_console_printf("gpu.h3.draw.vertex_write_rc=%d\r\n", result.vertex_write_rc);
        a90_console_printf("gpu.h3.draw.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.h3.draw.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.h3.draw.state_reg_writes=%u\r\n", result.state_reg_writes);
        a90_console_printf("gpu.h3.draw.vfd_reg_writes=%u\r\n", result.vfd_reg_writes);
        a90_console_printf("gpu.h3.draw.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.h3.draw.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.h3.draw.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.h3.draw.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.h3.draw.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.h3.draw.submit_timestamp=%u\r\n", result.submit_timestamp);
        a90_console_printf("gpu.h3.draw.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.h3.draw.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.h3.draw.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.h3.draw.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.h3.draw.readtimestamp_rc=%d\r\n",
                           result.readtimestamp_rc);
        a90_console_printf("gpu.h3.draw.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.h3.draw.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.h3.draw.readback_sync_errno=%d\r\n",
                           result.readback_sync_errno);
        a90_console_printf("gpu.h3.draw.readback_changed_count=%u\r\n",
                           result.readback_changed_count);
        a90_console_printf("gpu.h3.draw.readback_first_changed_index=%u\r\n",
                           result.readback_first_changed_index);
        a90_console_printf("gpu.h3.draw.readback_first_changed_value=0x%x\r\n",
                           result.readback_first_changed_value);
        a90_console_printf("gpu.h3.draw.readback0=0x%x\r\n", result.readback0);
        a90_console_printf("gpu.h3.draw.readback_center=0x%x\r\n",
                           result.readback_center);
        a90_console_printf("gpu.h3.draw.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.h3.draw.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.h3.draw.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.h3.draw.color_free_rc=%d\r\n", result.color_free_rc);
        a90_console_printf("gpu.h3.draw.event_free_rc=%d\r\n", result.event_free_rc);
        a90_console_printf("gpu.h3.draw.vs_free_rc=%d\r\n", result.vs_free_rc);
        a90_console_printf("gpu.h3.draw.fs_free_rc=%d\r\n", result.fs_free_rc);
        a90_console_printf("gpu.h3.draw.vertex_free_rc=%d\r\n", result.vertex_free_rc);
        a90_console_printf("gpu.h3.draw.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.h3.draw.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.h3.draw.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    return timed_out ? -ETIMEDOUT : 0;
}

static int gpu_g5_blit_gpu_readback_to_kms(uint32_t raw_pixel,
                                           uint32_t *rect_x,
                                           uint32_t *rect_y,
                                           uint32_t *rect_w,
                                           uint32_t *rect_h) {
    struct a90_fb *fb = a90_kms_framebuffer();
    uint32_t patch_w;
    uint32_t patch_h;
    uint32_t x;
    uint32_t y;
    uint32_t row_index;

    if (fb == NULL || fb->pixels == NULL || fb->pixels == MAP_FAILED ||
        fb->width == 0U || fb->height == 0U || fb->stride < fb->width * 4U) {
        return -ENODEV;
    }

    patch_w = (fb->width * 2U) / 3U;
    if (patch_w < GPU_G5_MIN_PATCH_PIXELS) {
        patch_w = fb->width;
    }
    if (patch_w > fb->width) {
        patch_w = fb->width;
    }
    patch_h = patch_w;
    if (patch_h > fb->height / 2U) {
        patch_h = fb->height / 2U;
    }
    if (patch_h < GPU_G5_MIN_PATCH_PIXELS && fb->height >= GPU_G5_MIN_PATCH_PIXELS) {
        patch_h = GPU_G5_MIN_PATCH_PIXELS;
    }
    if (patch_h > fb->height) {
        patch_h = fb->height;
    }
    x = (fb->width - patch_w) / 2U;
    y = (fb->height - patch_h) / 2U;

    a90_draw_text(fb, 36U, 48U, "GPU G5 KGSL TO KMS", 0xffffff, 4U);
    a90_draw_text(fb, 36U, 104U, "RAW A5C3F00D", 0x80ff80, 3U);
    a90_draw_rect_outline(fb,
                          x > 8U ? x - 8U : x,
                          y > 8U ? y - 8U : y,
                          patch_w + 16U < fb->width ? patch_w + 16U : patch_w,
                          patch_h + 16U < fb->height ? patch_h + 16U : patch_h,
                          4U,
                          0xffffff);

    for (row_index = 0; row_index < patch_h; ++row_index) {
        uint32_t *row = (uint32_t *)((char *)fb->pixels + ((y + row_index) * fb->stride));
        uint32_t col;

        for (col = 0; col < patch_w; ++col) {
            row[x + col] = raw_pixel;
        }
    }
    __sync_synchronize();

    if (rect_x != NULL) {
        *rect_x = x;
    }
    if (rect_y != NULL) {
        *rect_y = y;
    }
    if (rect_w != NULL) {
        *rect_w = patch_w;
    }
    if (rect_h != NULL) {
        *rect_h = patch_h;
    }
    return 0;
}

static int gpu_g5_kms_blit_probe(int timeout_ms, bool materialize_devnode) {
    struct gpu_g4_solid_fill_child_run run;
    struct a90_kms_info kms_info;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    int collect_rc;
    int begin_rc = -1;
    int blit_rc = -1;
    int present_rc = -1;
    uint32_t rect_x = 0U;
    uint32_t rect_y = 0U;
    uint32_t rect_w = 0U;
    uint32_t rect_h = 0U;
    long begin_elapsed_ms = 0;
    long blit_elapsed_ms = 0;
    long present_elapsed_ms = 0;

    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.g5.kms.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }

    a90_console_printf("gpu.g5.kms.version=1\r\n");
    a90_console_printf("gpu.g5.kms.scope=kgsl-a2d-solid-fill-readback-to-kms-dumb-blit-probe\r\n");
    a90_console_printf("gpu.g5.kms.kgsl_path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.g5.kms.drm_path=/dev/dri/card0\r\n");
    a90_console_printf("gpu.g5.kms.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.g5.kms.parent_enters_kgsl_open=0\r\n");
    a90_console_printf("gpu.g5.kms.parent_enters_kgsl_ioctl=0\r\n");
    a90_console_printf("gpu.g5.kms.kgsl_source=g4-solid-fill-pc-ccu-flush-color-ts-seqno\r\n");
    a90_console_printf("gpu.g5.kms.blit_mode=kgsl-private-buffer-readback-to-kms-dumb-framebuffer\r\n");
    a90_console_printf("gpu.g5.kms.zero_copy_attempted=0\r\n");
    a90_console_printf("gpu.g5.kms.kms_blit_attempted=1\r\n");
    a90_console_printf("gpu.g5.kms.power_write_attempted=0\r\n");
    a90_console_printf("gpu.g5.kms.proprietary_blob_attempted=0\r\n");

    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.g5.kms.materialize_requested=1\r\n");
        a90_console_printf("gpu.g5.kms.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.g5.kms.materialize_requested=0\r\n");
    }

    collect_rc = gpu_g4_solid_fill_collect_child(timeout_ms, &run);
    a90_console_printf("gpu.g5.kms.child_pid=%ld\r\n", (long)run.child_pid);
    a90_console_printf("gpu.g5.kms.child_collect_rc=%d\r\n", collect_rc);
    a90_console_printf("gpu.g5.kms.g4_result=%s\r\n",
                       run.got_result ? (gpu_g4_solid_fill_result_ok(&run.result) ?
                                         "solid-fill-readback-ok" : "returned-error") :
                       (run.timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.g5.kms.g4_timed_out=%d\r\n", run.timed_out ? 1 : 0);
    a90_console_printf("gpu.g5.kms.g4_child_killed=%d\r\n", run.child_killed ? 1 : 0);
    a90_console_printf("gpu.g5.kms.g4_child_reaped=%d\r\n", run.child_reaped ? 1 : 0);
    a90_console_printf("gpu.g5.kms.g4_child_status=0x%x\r\n", run.child_status);
    if (run.got_result) {
        a90_console_printf("gpu.g5.kms.g4_submit_rc=%d\r\n", run.result.submit_rc);
        a90_console_printf("gpu.g5.kms.g4_wait_rc=%d\r\n", run.result.wait_rc);
        a90_console_printf("gpu.g5.kms.g4_readback_sync_rc=%d\r\n",
                           run.result.readback_sync_rc);
        a90_console_printf("gpu.g5.kms.g4_readback_verified=%d\r\n",
                           run.result.readback_verified);
        a90_console_printf("gpu.g5.kms.g4_readback_mismatch_count=%d\r\n",
                           run.result.readback_mismatch_count);
        a90_console_printf("gpu.g5.kms.g4_readback0=0x%x\r\n", run.result.readback0);
        a90_console_printf("gpu.g5.kms.g4_total_elapsed_ms=%ld\r\n",
                           run.result.total_elapsed_ms);
    }

    if (!run.got_result || !gpu_g4_solid_fill_result_ok(&run.result)) {
        a90_console_printf("gpu.g5.kms.result=kgsl-readback-failed\r\n");
        a90_console_printf("gpu.g5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return collect_rc < 0 ? collect_rc : -EIO;
    }

    stage_started_ms = monotonic_millis();
    begin_rc = a90_kms_begin_frame(0x050505);
    begin_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_kms_info(&kms_info);
    a90_console_printf("gpu.g5.kms.begin_frame_elapsed_ms=%ld\r\n", begin_elapsed_ms);
    a90_console_printf("gpu.g5.kms.begin_frame_rc=%d\r\n", begin_rc);
    a90_console_printf("gpu.g5.kms.fb_initialized=%d\r\n", kms_info.initialized ? 1 : 0);
    a90_console_printf("gpu.g5.kms.fb_width=%u\r\n", kms_info.width);
    a90_console_printf("gpu.g5.kms.fb_height=%u\r\n", kms_info.height);
    a90_console_printf("gpu.g5.kms.fb_stride=%u\r\n", kms_info.stride);
    a90_console_printf("gpu.g5.kms.fb_id=%u\r\n", kms_info.fb_id);
    a90_console_printf("gpu.g5.kms.current_buffer=%u\r\n", kms_info.current_buffer);
    if (begin_rc < 0) {
        a90_console_printf("gpu.g5.kms.result=kms-begin-frame-failed\r\n");
        a90_console_printf("gpu.g5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -EIO;
    }

    stage_started_ms = monotonic_millis();
    blit_rc = gpu_g5_blit_gpu_readback_to_kms(run.result.readback0,
                                              &rect_x,
                                              &rect_y,
                                              &rect_w,
                                              &rect_h);
    blit_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.g5.kms.blit_elapsed_ms=%ld\r\n", blit_elapsed_ms);
    a90_console_printf("gpu.g5.kms.blit_rc=%d\r\n", blit_rc);
    a90_console_printf("gpu.g5.kms.blit_raw_pixel=0x%x\r\n", run.result.readback0);
    a90_console_printf("gpu.g5.kms.blit_rect=%u,%u,%u,%u\r\n",
                       rect_x, rect_y, rect_w, rect_h);
    if (blit_rc < 0) {
        a90_console_printf("gpu.g5.kms.result=kms-blit-failed\r\n");
        a90_console_printf("gpu.g5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return blit_rc;
    }

    stage_started_ms = monotonic_millis();
    present_rc = a90_kms_present("gpu-g5-kms-blit", true);
    present_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.g5.kms.present_elapsed_ms=%ld\r\n", present_elapsed_ms);
    a90_console_printf("gpu.g5.kms.present_rc=%d\r\n", present_rc);
    a90_console_printf("gpu.g5.kms.result=%s\r\n",
                       present_rc == 0 ? "kms-blit-presented" : "kms-present-failed");
    a90_console_printf("gpu.g5.kms.total_elapsed_ms=%ld\r\n",
                       monotonic_millis() - total_started_ms);
    return present_rc == 0 ? 0 : -EIO;
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
    if (strcmp(subcommand, "g2-gpuobj-probe") == 0 ||
        strcmp(subcommand, "gpuobj-probe") == 0 ||
        strcmp(subcommand, "g2-mmap-probe") == 0 ||
        strcmp(subcommand, "mmap-probe") == 0) {
        bool do_mmap = (strcmp(subcommand, "g2-mmap-probe") == 0 ||
                        strcmp(subcommand, "mmap-probe") == 0);

        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.g2.gpuobj.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu [g2-gpuobj-probe|g2-mmap-probe] [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_g2_gpuobj_probe(timeout_ms, materialize_devnode, do_mmap);
    }
    if (strcmp(subcommand, "g3-noop-submit-probe") == 0 ||
        strcmp(subcommand, "noop-submit-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.g3.noop.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_g3_noop_submit_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "h1-shader-state-probe") == 0 ||
        strcmp(subcommand, "shader-state-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.h1.shader.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_h1_shader_state_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "h2-3d-state-probe") == 0 ||
        strcmp(subcommand, "3d-state-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.h2.state.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_h2_3d_state_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "h3-draw-envelope-probe") == 0 ||
        strcmp(subcommand, "draw-envelope-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.h3.draw.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_h3_draw_envelope_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "g4-solid-fill-probe") == 0 ||
        strcmp(subcommand, "solid-fill-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.g4.fill.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_g4_solid_fill_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "g5-kms-blit-probe") == 0 ||
        strcmp(subcommand, "kms-blit-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.g5.kms.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_g5_kms_blit_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "g0-open-probe") != 0) {
        a90_console_printf("usage: gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]|g2-gpuobj-probe [--timeout-ms N] [--materialize-devnode]|g2-mmap-probe [--timeout-ms N] [--materialize-devnode]|g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]|h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]|h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]|h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]|g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]|g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]]\r\n");
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
    { "gpu", handle_gpu, "gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]|g2-gpuobj-probe [--timeout-ms N] [--materialize-devnode]|g2-mmap-probe [--timeout-ms N] [--materialize-devnode]|g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]|h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]|h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]|h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]|g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]|g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]]", CMD_NONE, A90_CMD_GROUP_CORE },
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
