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
    int color_flag_alloc_rc;
    int color_flag_alloc_errno;
    int color_flag_info_rc;
    int color_flag_info_errno;
    int color_flag_mmap_rc;
    int color_flag_mmap_errno;
    int linear_alloc_rc;
    int linear_alloc_errno;
    int linear_info_rc;
    int linear_info_errno;
    int linear_mmap_rc;
    int linear_mmap_errno;
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
    int sampler_alloc_rc;
    int sampler_alloc_errno;
    int sampler_info_rc;
    int sampler_info_errno;
    int sampler_mmap_rc;
    int sampler_mmap_errno;
    int texmem_alloc_rc;
    int texmem_alloc_errno;
    int texmem_info_rc;
    int texmem_info_errno;
    int texmem_mmap_rc;
    int texmem_mmap_errno;
    int texture_alloc_rc;
    int texture_alloc_errno;
    int texture_info_rc;
    int texture_info_errno;
    int texture_mmap_rc;
    int texture_mmap_errno;
    int color_init_rc;
    int shader_write_rc;
    int vertex_write_rc;
    int texture_write_rc;
    int texture_desc_write_rc;
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
    int color_flag_munmap_attempted;
    int color_flag_munmap_rc;
    int color_flag_munmap_errno;
    int linear_munmap_attempted;
    int linear_munmap_rc;
    int linear_munmap_errno;
    int vs_munmap_attempted;
    int vs_munmap_rc;
    int vs_munmap_errno;
    int fs_munmap_attempted;
    int fs_munmap_rc;
    int fs_munmap_errno;
    int vertex_munmap_attempted;
    int vertex_munmap_rc;
    int vertex_munmap_errno;
    int sampler_munmap_attempted;
    int sampler_munmap_rc;
    int sampler_munmap_errno;
    int texmem_munmap_attempted;
    int texmem_munmap_rc;
    int texmem_munmap_errno;
    int texture_munmap_attempted;
    int texture_munmap_rc;
    int texture_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int color_free_attempted;
    int color_free_deferred;
    int color_free_rc;
    int color_free_errno;
    int color_flag_free_attempted;
    int color_flag_free_deferred;
    int color_flag_free_rc;
    int color_flag_free_errno;
    int linear_free_attempted;
    int linear_free_deferred;
    int linear_free_rc;
    int linear_free_errno;
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
    int sampler_free_attempted;
    int sampler_free_deferred;
    int sampler_free_rc;
    int sampler_free_errno;
    int texmem_free_attempted;
    int texmem_free_deferred;
    int texmem_free_rc;
    int texmem_free_errno;
    int texture_free_attempted;
    int texture_free_deferred;
    int texture_free_rc;
    int texture_free_errno;
    int destroy_attempted;
    int destroy_rc;
    int destroy_errno;
    int close_rc;
    int close_errno;
    unsigned int context_id;
    unsigned int cmd_gpuobj_id;
    unsigned int color_gpuobj_id;
    unsigned int color_flag_gpuobj_id;
    unsigned int linear_gpuobj_id;
    unsigned int event_gpuobj_id;
    unsigned int vs_gpuobj_id;
    unsigned int fs_gpuobj_id;
    unsigned int vertex_gpuobj_id;
    unsigned int sampler_gpuobj_id;
    unsigned int texmem_gpuobj_id;
    unsigned int texture_gpuobj_id;
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
    unsigned int color_flag_pitch;
    unsigned int color_flag_changed_count;
    unsigned int color_flag_first_changed_index;
    unsigned int vertex_stride;
    unsigned int vertex_bytes;
    unsigned int vertex_count;
    unsigned int vertex_format;
    unsigned int texture_width;
    unsigned int texture_height;
    unsigned int texture_stride;
    unsigned int texture_bytes;
    unsigned int texture_format;
    unsigned int texture_desc_dwords;
    unsigned int sampler_desc_dwords;
    unsigned int texture_sample_grid;
    unsigned int texture_sample_count;
    unsigned int texture_sample_match_count;
    unsigned int texture_sample_mismatch_count;
    unsigned int texture_bbox_sample_count;
    unsigned int texture_bbox_sample_match_count;
    unsigned int texture_bbox_sample_mismatch_count;
    unsigned int texture_dark_count;
    unsigned int texture_light_count;
    unsigned int texture_other_count;
    unsigned int texture_first_mismatch_index;
    unsigned int texture_bbox_first_mismatch_index;
    uint32_t texture_first_mismatch_expected;
    uint32_t texture_first_mismatch_value;
    uint32_t texture_bbox_first_mismatch_expected;
    uint32_t texture_bbox_first_mismatch_value;
    int realframe_manifest_rc;
    int realframe_open_rc;
    int realframe_open_errno;
    int realframe_header_rc;
    int realframe_record_rc;
    int realframe_read_rc;
    int realframe_close_rc;
    int realframe_close_errno;
    unsigned int realframe_requested_frame_index;
    unsigned int realframe_record_index;
    unsigned int realframe_payload_bytes;
    unsigned int realframe_width;
    unsigned int realframe_height;
    unsigned int realframe_stride;
    unsigned int realframe_frame_bytes;
    unsigned int realframe_source_dark_count;
    unsigned int realframe_source_light_count;
    unsigned int realframe_source_other_count;
    unsigned int realframe_bbox_sample_count;
    unsigned int realframe_bbox_sample_match_count;
    unsigned int realframe_bbox_sample_mismatch_count;
    unsigned int realframe_bbox_first_mismatch_index;
    uint32_t realframe_bbox_first_mismatch_expected;
    uint32_t realframe_bbox_first_mismatch_value;
    unsigned int cp_draw_packet;
    unsigned int draw_initiator;
    unsigned int num_instances;
    unsigned int num_indices;
    unsigned int draw_attempted;
    unsigned int shader_execution_attempted;
    unsigned int kms_blit_attempted;
    unsigned int linear_blit_attempted;
    unsigned int readback_changed_count;
    unsigned int readback_first_changed_index;
    unsigned int linear_readback_changed_count;
    unsigned int linear_readback_first_changed_index;
    unsigned int linear_readback_nonzero_count;
    unsigned int linear_readback_first_nonzero_index;
    unsigned int linear_center_nonzero;
    unsigned int linear_exterior_corners_zero;
    unsigned int linear_readback_bbox_found;
    unsigned int linear_readback_bbox_min_x;
    unsigned int linear_readback_bbox_min_y;
    unsigned int linear_readback_bbox_max_x;
    unsigned int linear_readback_bbox_max_y;
    uint32_t readback0;
    uint32_t readback_center;
    uint32_t readback_first_changed_value;
    uint32_t linear_readback0;
    uint32_t linear_readback_center;
    uint32_t linear_readback_first_changed_value;
    uint32_t linear_readback_first_nonzero_value;
    uint32_t linear_readback_corner_tr;
    uint32_t linear_readback_corner_bl;
    uint32_t linear_readback_corner_br;
    uint32_t color_flag0;
    uint32_t color_flag_first_changed_value;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t color_info_gpuaddr;
    uint64_t color_flag_info_gpuaddr;
    uint64_t linear_info_gpuaddr;
    uint64_t event_info_gpuaddr;
    uint64_t vs_info_gpuaddr;
    uint64_t fs_info_gpuaddr;
    uint64_t vertex_info_gpuaddr;
    uint64_t sampler_info_gpuaddr;
    uint64_t texmem_info_gpuaddr;
    uint64_t texture_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t color_mmap_len;
    uint64_t color_flag_mmap_len;
    uint64_t linear_mmap_len;
    uint64_t event_size;
    uint64_t vs_mmap_len;
    uint64_t fs_mmap_len;
    uint64_t vertex_mmap_len;
    uint64_t sampler_mmap_len;
    uint64_t texmem_mmap_len;
    uint64_t texture_mmap_len;
    uint64_t color_bytes;
    uint64_t cmd_sync_length;
    uint64_t color_sync_length;
    uint64_t color_flag_sync_length;
    uint64_t linear_sync_length;
    uint64_t event_sync_length;
    uint64_t vs_sync_length;
    uint64_t fs_sync_length;
    uint64_t vertex_sync_length;
    uint64_t sampler_sync_length;
    uint64_t texmem_sync_length;
    uint64_t texture_sync_length;
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

struct gpu_c1_compute_invocationid_probe_result {
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
    int shader_alloc_rc;
    int shader_alloc_errno;
    int shader_info_rc;
    int shader_info_errno;
    int shader_mmap_rc;
    int shader_mmap_errno;
    int uav_alloc_rc;
    int uav_alloc_errno;
    int uav_info_rc;
    int uav_info_errno;
    int uav_mmap_rc;
    int uav_mmap_errno;
    int descriptor_alloc_rc;
    int descriptor_alloc_errno;
    int descriptor_info_rc;
    int descriptor_info_errno;
    int descriptor_mmap_rc;
    int descriptor_mmap_errno;
    int event_alloc_rc;
    int event_alloc_errno;
    int event_info_rc;
    int event_info_errno;
    int uav_init_rc;
    int shader_write_rc;
    int descriptor_write_rc;
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
    int shader_munmap_attempted;
    int shader_munmap_rc;
    int shader_munmap_errno;
    int uav_munmap_attempted;
    int uav_munmap_rc;
    int uav_munmap_errno;
    int descriptor_munmap_attempted;
    int descriptor_munmap_rc;
    int descriptor_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int shader_free_attempted;
    int shader_free_deferred;
    int shader_free_rc;
    int shader_free_errno;
    int uav_free_attempted;
    int uav_free_deferred;
    int uav_free_rc;
    int uav_free_errno;
    int descriptor_free_attempted;
    int descriptor_free_deferred;
    int descriptor_free_rc;
    int descriptor_free_errno;
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
    unsigned int cmd_gpuobj_id;
    unsigned int shader_gpuobj_id;
    unsigned int uav_gpuobj_id;
    unsigned int descriptor_gpuobj_id;
    unsigned int event_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int shader_dwords;
    unsigned int descriptor_dwords;
    unsigned int uav_words;
    unsigned int cp_exec_cs_packet;
    unsigned int expected_match_count;
    unsigned int mismatch_count;
    unsigned int first_mismatch_index;
    unsigned int first_mismatch_expected;
    unsigned int first_mismatch_value;
    unsigned int changed_count;
    unsigned int pass;
    uint32_t readback0;
    uint32_t readback1;
    uint32_t readback2;
    uint32_t readback3;
    uint32_t readback31;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t shader_info_gpuaddr;
    uint64_t uav_info_gpuaddr;
    uint64_t descriptor_info_gpuaddr;
    uint64_t event_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t shader_mmap_len;
    uint64_t uav_mmap_len;
    uint64_t descriptor_mmap_len;
    uint64_t event_size;
    uint64_t cmd_sync_length;
    uint64_t shader_sync_length;
    uint64_t uav_sync_length;
    uint64_t descriptor_sync_length;
    uint64_t event_sync_length;
    uint64_t readback_sync_length;
    long total_elapsed_ms;
};

struct gpu_c1_compute_child_run {
    struct gpu_c1_compute_invocationid_probe_result result;
    pid_t child_pid;
    bool got_result;
    bool timed_out;
    bool child_killed;
    bool child_reaped;
    int child_status;
};

struct gpu_c2_compute_pattern_probe_result {
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
    int shader_alloc_rc;
    int shader_alloc_errno;
    int shader_info_rc;
    int shader_info_errno;
    int shader_mmap_rc;
    int shader_mmap_errno;
    int uav_alloc_rc;
    int uav_alloc_errno;
    int uav_info_rc;
    int uav_info_errno;
    int uav_mmap_rc;
    int uav_mmap_errno;
    int descriptor_alloc_rc;
    int descriptor_alloc_errno;
    int descriptor_info_rc;
    int descriptor_info_errno;
    int descriptor_mmap_rc;
    int descriptor_mmap_errno;
    int event_alloc_rc;
    int event_alloc_errno;
    int event_info_rc;
    int event_info_errno;
    int uav_init_rc;
    int shader_write_rc;
    int descriptor_write_rc;
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
    int snapshot_write_rc;
    int snapshot_write_errno;
    int fence_poll_attempted;
    int fence_poll_rc;
    int fence_poll_errno;
    int fence_poll_revents;
    int fence_close_rc;
    int fence_close_errno;
    int cmd_munmap_attempted;
    int cmd_munmap_rc;
    int cmd_munmap_errno;
    int shader_munmap_attempted;
    int shader_munmap_rc;
    int shader_munmap_errno;
    int uav_munmap_attempted;
    int uav_munmap_rc;
    int uav_munmap_errno;
    int descriptor_munmap_attempted;
    int descriptor_munmap_rc;
    int descriptor_munmap_errno;
    int cmd_free_attempted;
    int cmd_free_deferred;
    int cmd_free_rc;
    int cmd_free_errno;
    int shader_free_attempted;
    int shader_free_deferred;
    int shader_free_rc;
    int shader_free_errno;
    int uav_free_attempted;
    int uav_free_deferred;
    int uav_free_rc;
    int uav_free_errno;
    int descriptor_free_attempted;
    int descriptor_free_deferred;
    int descriptor_free_rc;
    int descriptor_free_errno;
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
    unsigned int cmd_gpuobj_id;
    unsigned int shader_gpuobj_id;
    unsigned int uav_gpuobj_id;
    unsigned int descriptor_gpuobj_id;
    unsigned int event_gpuobj_id;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    unsigned int wait_timeout_ms;
    unsigned int pm4_dwords;
    unsigned int shader_dwords;
    unsigned int descriptor_dwords;
    unsigned int uav_words;
    unsigned int pattern_width;
    unsigned int pattern_height;
    unsigned int local_size_x;
    unsigned int group_x;
    unsigned int global_x;
    unsigned int cp_exec_cs_packet;
    unsigned int expected_match_count;
    unsigned int mismatch_count;
    unsigned int first_mismatch_index;
    unsigned int first_mismatch_expected;
    unsigned int first_mismatch_value;
    unsigned int changed_count;
    unsigned int pass;
    uint32_t readback0;
    uint32_t readback1;
    uint32_t readback2;
    uint32_t readback3;
    uint32_t readback31;
    uint32_t readback127;
    uint32_t readback128;
    uint32_t readback4096;
    uint32_t readback8192;
    uint32_t readback16383;
    int fence_fd;
    uint64_t cmd_info_gpuaddr;
    uint64_t shader_info_gpuaddr;
    uint64_t uav_info_gpuaddr;
    uint64_t descriptor_info_gpuaddr;
    uint64_t event_info_gpuaddr;
    uint64_t cmd_size;
    uint64_t cmd_mmap_len;
    uint64_t shader_mmap_len;
    uint64_t uav_mmap_len;
    uint64_t descriptor_mmap_len;
    uint64_t event_size;
    uint64_t cmd_sync_length;
    uint64_t shader_sync_length;
    uint64_t uav_sync_length;
    uint64_t descriptor_sync_length;
    uint64_t event_sync_length;
    uint64_t readback_sync_length;
    uint64_t snapshot_write_bytes;
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
#define GPU_G4_CMD_MAX_DWORDS 512U
#define GPU_G4_FILL_BYTES 256ULL
#define GPU_G4_FILL_DWORDS ((unsigned int)(GPU_G4_FILL_BYTES / 4ULL))
#define GPU_G4_READBACK_DWORDS 16U
#define GPU_G5_MIN_PATCH_PIXELS 128U
#define GPU_G4_FILL_PATTERN 0xa5c3f00dU
#define GPU_G4_SENTINEL_PATTERN 0x11111111U
#define GPU_G4_A6XX_FMT6_32_FLOAT 0x4aU
#define GPU_G4_A6XX_FMT6_32_UINT 0x4bU
#define GPU_G4_A6XX_FMT6_8_8_8_8_UNORM 0x30U
#define GPU_G4_A6XX_R2D_INT32 0x7U
#define GPU_G4_A6XX_OUTPUT_IFMT_2D_UINT 0x2U
#define GPU_G4_A6XX_TILE6_LINEAR 0x0U
#define GPU_G4_A3XX_COLOR_SWAP_WZYX 0x0U
#define GPU_G4_A6XX_ROTATE_0 0x0U
#define GPU_G4_A6XX_CP_SET_MARKER_RM6_BLIT2DSCALE 12U
#define GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER 1U
#define GPU_H3_A6XX_POLYMODE6_TRIANGLES 3U
#define GPU_H3_A6XX_BUFFERS_IN_SYSMEM 3U
#define GPU_H3_A6XX_LRZ_FEEDBACK_EARLY_Z_LATE_Z 2U
#define GPU_H3_A6XX_BIN_CNTL_BUFFERS_LOCATION_SHIFT 22U
#define GPU_H3_A6XX_BIN_CNTL_LRZ_FEEDBACK_ZMODE_SHIFT 24U
#define GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING \
    ((GPU_H3_A6XX_BUFFERS_IN_SYSMEM << GPU_H3_A6XX_BIN_CNTL_BUFFERS_LOCATION_SHIFT) | \
     (GPU_H3_A6XX_LRZ_FEEDBACK_EARLY_Z_LATE_Z << GPU_H3_A6XX_BIN_CNTL_LRZ_FEEDBACK_ZMODE_SHIFT))
#define GPU_G4_A6XX_CP_BLIT_OP_SCALE 3U
#define GPU_G4_EVENT_SEQNO_VALUE 0x32020001U
#define GPU_G4_CP_EVENT_WRITE_TIMESTAMP_BIT (1U << 30)
#define GPU_G4_PM4_CP_WAIT_FOR_IDLE 0x26U
#define GPU_G4_PM4_CP_BLIT 0x2cU
#define GPU_G4_PM4_CP_EVENT_WRITE 0x46U
#define GPU_H3_PM4_CP_SET_MODE 0x63U
#define GPU_G4_PM4_CP_SET_MARKER 0x65U
#define GPU_C1_PM4_CP_EXEC_CS 0x33U
#define GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL 0x1dU
#define GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL 0x23U
#define GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE 0x64U
#define GPU_G4_EVENT_CACHE_FLUSH_TS 0x04U
#define GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH 0x18U
#define GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR 0x19U
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
#define GPU_H3_IR3_MOV_U32U32_R0Z_HI 0x204cc002U
#define GPU_H3_IR3_MOV_U32U32_R0W_HI 0x204cc003U
#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO 0x00000000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO 0x00000001U
#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_LO 0x00000000U
#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_LO 0x00000001U
#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI 0x20044000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI 0x20044001U
#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_HI 0x20044004U
#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_HI 0x20044005U
#define GPU_H3_IR3_MOV_F32F32_R2X_R1X_HI 0x20044008U
#define GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_HI 0x20044009U
#define GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_HI 0x2004400aU
#define GPU_H3_IR3_MOV_F32F32_R2W_R1W_HI 0x2004400bU
#define GPU_H3_IR3_MOV_F32F32_R0X_HI 0x20444000U
#define GPU_H3_IR3_MOV_F32F32_R0Y_HI 0x20444001U
#define GPU_H3_IR3_MOV_F32F32_R0Z_HI 0x20444002U
#define GPU_H3_IR3_MOV_F32F32_R0W_HI 0x20444003U
#define GPU_H3_IR3_MOV_F32F32_R1X_HI 0x20444004U
#define GPU_H3_IR3_MOV_F32F32_R1Z_HI 0x20444006U
#define GPU_H3_IR3_MOV_F32F32_R1W_HI 0x20444007U
#define GPU_H3_IR3_MOV_U32U32_R2Z_HI 0x204cc00aU
#define GPU_H3_IR3_MOV_U32U32_R2W_HI 0x204cc00bU
#define GPU_H3_IR3_MOV_F32F32_R2X_R1X_LO 0x00000004U
#define GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_LO 0x00000005U
#define GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_LO 0x00000006U
#define GPU_H3_IR3_MOV_F32F32_R2W_R1W_LO 0x00000007U
#define GPU_H3_IR3_BARY_F_R0Z_IJ0_LO 0x00002000U
#define GPU_H3_IR3_BARY_F_R0Z_IJ0_HI 0x47300002U
#define GPU_H3_IR3_BARY_F_R0W_IJ1_LO 0x00002001U
#define GPU_H3_IR3_BARY_F_R0W_IJ1_HI 0x47300003U
#define GPU_H3_IR3_BARY_F_R1X_IJ2_LO 0x00002002U
#define GPU_H3_IR3_BARY_F_R1X_IJ2_HI 0x47300004U
#define GPU_H3_IR3_BARY_F_R1Y_IJ3_EI_LO 0x00002003U
#define GPU_H3_IR3_BARY_F_R1Y_IJ3_EI_HI 0x47308005U
#define GPU_H1_CP_LOAD_STATE6_STATE_SRC_INDIRECT (2U << 16)
#define GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER (8U << 18)
#define GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER (12U << 18)
#define GPU_H1_PM4_CP_LOAD_STATE6_GEOM 0x32U
#define GPU_H1_PM4_CP_LOAD_STATE6_FRAG 0x34U
#define GPU_C1_CMD_ALLOC_SIZE 4096ULL
#define GPU_C1_SHADER_ALLOC_SIZE 4096ULL
#define GPU_C1_UAV_ALLOC_SIZE 4096ULL
#define GPU_C1_DESCRIPTOR_ALLOC_SIZE 4096ULL
#define GPU_C1_EVENT_ALLOC_SIZE 4096ULL
#define GPU_C1_WAIT_TIMEOUT_MS 1000U
#define GPU_C1_SHADER_DWORDS 32U
#define GPU_C1_SHADER_INSTRLEN 1U
#define GPU_C1_SHADER_CONSTLEN 4U
#define GPU_C1_UAV_WORDS 32U
#define GPU_C1_UAV_BYTES ((uint64_t)GPU_C1_UAV_WORDS * 4ULL)
#define GPU_C1_DESCRIPTOR_DWORDS 16U
#define GPU_C1_CP_SET_MARKER_RM6_COMPUTE 8U
#define GPU_C1_CP_LOAD_STATE6_STATE_TYPE_SHADER (0U << 14)
#define GPU_C1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS (1U << 14)
#define GPU_C1_CP_LOAD_STATE6_STATE_TYPE_UAV (3U << 14)
#define GPU_C1_CP_LOAD_STATE6_STATE_SRC_DIRECT (0U << 16)
#define GPU_C1_CP_LOAD_STATE6_STATE_SRC_INDIRECT (2U << 16)
#define GPU_C1_CP_LOAD_STATE6_SB_CS_SHADER (13U << 18)
#define GPU_D1_CP_LOAD_STATE6_STATE_TYPE_SHADER (0U << 14)
#define GPU_D1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS (1U << 14)
#define GPU_D1_CP_LOAD_STATE6_SB_FS_TEX (4U << 18)
#define GPU_C1_REG_SP_CS_CNTL_0 0xa9b0U
#define GPU_C1_REG_SP_CS_CNTL_1 0xa9b1U
#define GPU_C1_REG_SP_CS_PROGRAM_COUNTER_OFFSET 0xa9b3U
#define GPU_C1_REG_SP_CS_BASE 0xa9b4U
#define GPU_C1_REG_SP_CS_CONFIG 0xa9bbU
#define GPU_C1_REG_SP_CS_INSTR_SIZE 0xa9bcU
#define GPU_C1_REG_SP_CS_UAV_BASE 0xa9f2U
#define GPU_C1_REG_SP_CS_USIZE 0xaa00U
#define GPU_C1_REG_SP_CS_CONST_CONFIG 0xb987U
#define GPU_C1_REG_SP_CS_NDRANGE_0 0xb990U
#define GPU_C1_REG_SP_CS_CONST_CONFIG_0 0xb997U
#define GPU_C1_REG_SP_CS_WGE_CNTL 0xb998U
#define GPU_C1_REG_SP_CS_KERNEL_GROUP_X 0xb999U
#define GPU_C1_REG_HLSQ_CS_CTRL_REG1 0xb9d0U
#define GPU_C1_SP_CS_CNTL_0 0x80000080U
#define GPU_C1_SP_CS_CNTL_1 0x00000001U
#define GPU_C1_SP_CS_CONFIG 0x00400100U
#define GPU_C1_SP_CS_CONST_CONFIG 0x00000101U
#define GPU_C1_SP_CS_CONST_CONFIG_0 0x00fcfcc0U
#define GPU_C1_SP_CS_WGE_CNTL 0x000000fcU
#define GPU_C1_SP_UPDATE_CNTL 0x000000bfU
#define GPU_C1_HLSQ_CS_CTRL_REG1 0x00000001U
#define GPU_C1_SP_CS_NDRANGE_0 0x0000007fU
#define GPU_C1_SP_CS_GLOBAL_X 32U
#define GPU_C1_SP_CS_GLOBAL_Y 1U
#define GPU_C1_SP_CS_GLOBAL_Z 1U
#define GPU_C1_SP_CS_GROUP_X 1U
#define GPU_C1_SP_CS_GROUP_Y 1U
#define GPU_C1_SP_CS_GROUP_Z 1U
#define GPU_C1_DESC0_R32_UINT_LINEAR 0x12c0a880U
#define GPU_C1_DESC1_WIDTH_32 0x00000020U
#define GPU_C1_DESC2_BUFFER_STRUCT1 0x80000010U
#define GPU_C1_UAV_INIT_PATTERN 0xdead0000U
#define GPU_C2_PATTERN_WIDTH 128U
#define GPU_C2_PATTERN_HEIGHT 128U
#define GPU_C2_CMD_ALLOC_SIZE 4096ULL
#define GPU_C2_SHADER_ALLOC_SIZE 4096ULL
#define GPU_C2_UAV_WORDS (GPU_C2_PATTERN_WIDTH * GPU_C2_PATTERN_HEIGHT)
#define GPU_C2_UAV_ALLOC_SIZE ((uint64_t)GPU_C2_UAV_WORDS * 4ULL)
#define GPU_C2_DESCRIPTOR_ALLOC_SIZE 4096ULL
#define GPU_C2_EVENT_ALLOC_SIZE 4096ULL
#define GPU_C2_WAIT_TIMEOUT_MS 1000U
#define GPU_C2_SHADER_DWORDS 32U
#define GPU_C2_SHADER_INSTRLEN 1U
#define GPU_C2_SHADER_CONSTLEN 4U
#define GPU_C2_UAV_BYTES ((uint64_t)GPU_C2_UAV_WORDS * 4ULL)
#define GPU_C2_DESC1_WIDTH 0x00004000U
#define GPU_C2_SP_CS_NDRANGE_0 0x00000003U
#define GPU_C2_SP_CS_GLOBAL_X GPU_C2_UAV_WORDS
#define GPU_C2_SP_CS_GLOBAL_Y 1U
#define GPU_C2_SP_CS_GLOBAL_Z 1U
#define GPU_C2_SP_CS_GROUP_X GPU_C2_UAV_WORDS
#define GPU_C2_SP_CS_GROUP_Y 1U
#define GPU_C2_SP_CS_GROUP_Z 1U
#define GPU_C2_UAV_INIT_PATTERN 0xbeef0000U
#define GPU_C2_SAMPLE_127 127U
#define GPU_C2_SAMPLE_128 128U
#define GPU_C2_SAMPLE_4096 4096U
#define GPU_C2_SAMPLE_8192 8192U
#define GPU_C2_SAMPLE_LAST (GPU_C2_UAV_WORDS - 1U)
#define GPU_C2_SNAPSHOT_PATH "/tmp/a90-gpu-c2-pattern-snapshot-v3302.u32"
#define GPU_C3_VISUAL_FILL_BG 0x050505U
#define GPU_C3_VISUAL_PANEL_BG 0x080c10U
#define GPU_H2_CMD_ALLOC_SIZE 4096ULL
#define GPU_H2_COLOR_WIDTH 128U
#define GPU_H2_COLOR_HEIGHT 128U
#define GPU_H2_COLOR_BPP 4U
#define GPU_H2_COLOR_STRIDE (GPU_H2_COLOR_WIDTH * GPU_H2_COLOR_BPP)
#define GPU_H2_COLOR_ALLOC_SIZE ((uint64_t)GPU_H2_COLOR_STRIDE * GPU_H2_COLOR_HEIGHT)
#define GPU_H2_CMD_MAX_DWORDS 160U
#define GPU_H2_WAIT_TIMEOUT_MS 1000U
#define GPU_H2_CLEAR_PATTERN 0x20202020U
#define GPU_H5_H3_SNAPSHOT_WORDS (GPU_H2_COLOR_WIDTH * GPU_H2_COLOR_HEIGHT)
#define GPU_H5_H3_PRESENT_MARGIN_X 28U
#define GPU_H5_H3_PRESENT_TOP 176U
#define GPU_H5_LINEAR_CLEAR_PATTERN 0x00000000U
#define GPU_H5_VISUAL_HOLD_DEFAULT_MS 30000
#define GPU_H5_VISUAL_HOLD_MAX_MS 60000
#define GPU_H5_VISUAL_MIN_PANEL_MARGIN 60U
#define GPU_H5_VISUAL_TOP_TEXT_Y 48U
#define GPU_H5_VISUAL_BOTTOM_RESERVED 260U
#define GPU_H5_VISUAL_FILL_COLOR 0x00ff40U
#define GPU_H5_VISUAL_BG_COLOR 0x050505U
#define GPU_H5_A2D_BLT_CNTL_SCALE_RGBA8 0x10f03000U
#define GPU_H5_A2D_OUTPUT_INFO_RGBA8 0x0000f180U
#define GPU_H5_A2D_SRC_TEXTURE_INFO_TILE6_3_FLAGS \
    (GPU_H3_COLOR_FORMAT | \
     (GPU_G4_A6XX_TILE6_3 << 8) | \
     (GPU_G4_A3XX_COLOR_SWAP_WZYX << 10) | \
     (1U << 12) | \
     (1U << 20) | \
     (1U << 22))
#define GPU_H5_A2D_DEST_BUFFER_INFO_LINEAR GPU_H3_COLOR_FORMAT
#define GPU_H5_A2D_SRC_TEXTURE_SIZE \
    (GPU_H2_COLOR_WIDTH | (GPU_H2_COLOR_HEIGHT << 15))
#define GPU_H5_A2D_SRC_TEXTURE_PITCH ((GPU_H2_COLOR_STRIDE >> 6) << 9)
#define GPU_H5_A2D_DEST_BUFFER_PITCH (GPU_H2_COLOR_STRIDE >> 6)
#define GPU_H5_A2D_SRC_MAX_X ((GPU_H2_COLOR_WIDTH - 1U) << 8)
#define GPU_H5_A2D_SRC_MAX_Y ((GPU_H2_COLOR_HEIGHT - 1U) << 8)
#define GPU_H3_CMD_ALLOC_SIZE 8192ULL
#define GPU_H3_VERTEX_ALLOC_SIZE 4096ULL
#define GPU_H3_EVENT_ALLOC_SIZE 4096ULL
#define GPU_H3_COLOR_FLAG_ALLOC_SIZE 4096ULL
#define GPU_H3_WAIT_TIMEOUT_MS 1000U
#define GPU_H3_VERTEX_COUNT 3U
#define GPU_H3_VERTEX_STRIDE 36U
#define GPU_H3_VERTEX_DWORDS (GPU_H3_VERTEX_COUNT * 9U)
#define GPU_H3_VERTEX_BYTES ((uint64_t)GPU_H3_VERTEX_DWORDS * 4ULL)
#define GPU_D1_TEXTURE_WIDTH 128U
#define GPU_D1_TEXTURE_HEIGHT 128U
#define GPU_D1_TEXTURE_BPP 4U
#define GPU_D1_TEXTURE_STRIDE (GPU_D1_TEXTURE_WIDTH * GPU_D1_TEXTURE_BPP)
#define GPU_D1_TEXTURE_BYTES ((uint64_t)GPU_D1_TEXTURE_STRIDE * GPU_D1_TEXTURE_HEIGHT)
#define GPU_D1_TEXTURE_ALLOC_SIZE GPU_D1_TEXTURE_BYTES
#define GPU_D1_DESCRIPTOR_ALLOC_SIZE 4096ULL
#define GPU_D1_SAMPLER_DESC_DWORDS 4U
#define GPU_D1_TEXMEMOBJ_DESC_DWORDS 16U
#define GPU_D1_VERTEX_COUNT 6U
#define GPU_D1_VERTEX_STRIDE GPU_H3_VERTEX_STRIDE
#define GPU_D1_VERTEX_DWORDS (GPU_D1_VERTEX_COUNT * 9U)
#define GPU_D1_VERTEX_BYTES ((uint64_t)GPU_D1_VERTEX_DWORDS * 4ULL)
#define GPU_D1_CHECKER_BLOCK 16U
#define GPU_D1_CHECKER_SAMPLE_GRID 8U
#define GPU_D1_CHECKER_SAMPLE_COUNT \
    (GPU_D1_CHECKER_SAMPLE_GRID * GPU_D1_CHECKER_SAMPLE_GRID)
#define GPU_D1_CHECKER_DARK_RGB 0x303030U
#define GPU_D1_CHECKER_LIGHT_RGB 0xd0d0d0U
#define GPU_D1_CHECKER_DARK_WORD 0xff303030U
#define GPU_D1_CHECKER_LIGHT_WORD 0xffd0d0d0U
#define GPU_D2_REALFRAME_DEFAULT_FRAME_INDEX 515U
#define GPU_D2_REALFRAME_MAX_TEXTURE_BYTES (4ULL * 1024ULL * 1024ULL)
#define GPU_D2_REALFRAME_DARK_RGB 0x000000U
#define GPU_D2_REALFRAME_LIGHT_RGB 0xffffffU
#define GPU_D2_REALFRAME_DARK_WORD 0xff000000U
#define GPU_D2_REALFRAME_LIGHT_WORD 0xffffffffU
#define GPU_D2_REALFRAME_BADAPPLE_MANIFEST_PATH \
    VIDEO_STREAM_CACHE_ROOT "/" VIDEO_STREAM_CACHE_DIR_PREFIX VIDEO_CACHE_PRESET_BADAPPLE_SHA256 "/manifest.json"
#define GPU_D3_VIDEO_DEFAULT_FRAMES 60U
#define GPU_D3_VIDEO_MAX_FRAMES 300U
#define GPU_D3_VIDEO_MAX_TIMEOUT_MS 120000
#define GPU_D3_VIDEO_TARGET_WIDTH (480U * VIDEO_PLAYER_HUD_SCALE)
#define GPU_D3_VIDEO_TARGET_HEIGHT (360U * VIDEO_PLAYER_HUD_SCALE)
#define GPU_D3_VIDEO_TARGET_BPP 4U
#define GPU_D3_VIDEO_TARGET_STRIDE (GPU_D3_VIDEO_TARGET_WIDTH * GPU_D3_VIDEO_TARGET_BPP)
#define GPU_D3_VIDEO_TARGET_BYTES \
    ((uint64_t)GPU_D3_VIDEO_TARGET_STRIDE * GPU_D3_VIDEO_TARGET_HEIGHT)
#define GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE 65536ULL
#define GPU_D3_VIDEO_SEMANTIC_EDGE_RADIUS 1U
#define GPU_D3_VIDEO_LABEL "GPU D3 VIDEO TEXTURE"
#define GPU_D3_VIDEO_SCOPE "gpu-2d-d3-demo-player-texture-blit-present"
#define GPU_H3_A6XX_FMT6_32_32_FLOAT 0x67U
#define GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT 0x82U
#define GPU_H3_A6XX_FMT6_32_SINT 0x4cU
#define GPU_H3_COLOR_FORMAT GPU_G4_A6XX_FMT6_8_8_8_8_UNORM
#define GPU_H3_COLOR_OUTPUT_MASK 0xfU
#define GPU_G4_A6XX_TILE6_3 0x3U
#define GPU_H3_RB_MRT0_BUF_INFO \
    (GPU_H3_COLOR_FORMAT | \
     (GPU_G4_A6XX_TILE6_3 << 8) | \
     (GPU_G4_A3XX_COLOR_SWAP_WZYX << 13))
#define GPU_H3_SP_PS_MRT_REG0 GPU_H3_COLOR_FORMAT
#define GPU_H3_COLOR_FLAG_BUFFER_PITCH 0x00004001U
#define GPU_H3_IR3_INSTR_ALIGN 16U
#define GPU_H3_SHADER_ALIGNED_DWORDS (GPU_H3_IR3_INSTR_ALIGN * 2U)
#define GPU_H3_VS_SHADER_INSTR_COUNT 5U
#define GPU_H3_FS_SHADER_INSTR_COUNT 5U
#define GPU_H3_VS_SHADER_INSTRLEN 1U
#define GPU_H3_FS_SHADER_INSTRLEN 1U
#define GPU_H3_VS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS
#define GPU_H3_FS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS
#define GPU_D1_FS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS
#define GPU_D1_FS_SHADER_INSTRLEN 1U
#define GPU_D1_VIEWPORT_SCALE_X (GPU_H2_COLOR_WIDTH / 2U)
#define GPU_D1_VIEWPORT_SCALE_Y (GPU_H2_COLOR_HEIGHT / 2U)
#define GPU_D1_VIEWPORT_OFFSET_X (GPU_H2_COLOR_WIDTH / 2U)
#define GPU_D1_VIEWPORT_OFFSET_Y (GPU_H2_COLOR_HEIGHT / 2U)
#define GPU_D1_SP_PS_CONFIG_TEXTURED \
    (GPU_H1_SP_CONFIG_ENABLED | (1U << 9) | (1U << 17))
#define GPU_H3_SP_UPDATE_CNTL_DRAW_STATE 0x0000009fU
#define GPU_H3_VS_POSITION_OUTPUT_REGID 8U
#define GPU_H3_VS_VARYING_OUTPUT_REGID 0U
#define GPU_H3_PS_OUTPUT_REGID 2U
#define GPU_D1_TEXTURED_FS_SHA256 \
    "4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3"

struct gpu_h3_draw_snapshot_payload {
    struct gpu_h3_draw_envelope_probe_result result;
    uint32_t color_words[GPU_H5_H3_SNAPSHOT_WORDS];
};

struct gpu_h3_draw_snapshot_child_run {
    struct gpu_h3_draw_snapshot_payload payload;
    pid_t child_pid;
    bool got_result;
    bool timed_out;
    bool child_killed;
    bool child_reaped;
    int child_status;
    size_t payload_bytes_read;
};

#define GPU_H3_SP_VS_OUTPUT_CNTL 2U
#define GPU_H3_SP_VS_OUTPUT_REG0 \
    ((GPU_H3_VS_POSITION_OUTPUT_REGID & 0xffU) | (0xfU << 8) | \
     ((GPU_H3_VS_VARYING_OUTPUT_REGID & 0xffU) << 16) | (0xfU << 24))
#define GPU_H3_SP_VS_VPC_DEST_REG0 0x00000400U
#define GPU_H3_PM4_CP_DRAW_INDX_OFFSET 0x38U
#define GPU_H3_CP_SKIP_IB2_ENABLE_GLOBAL_VALUE 0x00000000U
#define GPU_H3_CP_SKIP_IB2_ENABLE_LOCAL_VALUE 0x00000001U
#define GPU_H3_CP_SET_VISIBILITY_OVERRIDE_VALUE 0x00000001U
#define GPU_H3_CP_SET_MODE_RESTORE_VALUE 0x00000000U
#define GPU_H3_DI_PT_TRILIST 4U
#define GPU_H3_DI_SRC_SEL_AUTO_INDEX 2U
#define GPU_H3_IGNORE_VISIBILITY 0U
#define GPU_H3_INDEX_SIZE_IGN 0U
#define GPU_H3_SP_VS_FULLREGFOOTPRINT 3U
#define GPU_H3_SP_PS_FULLREGFOOTPRINT 2U
#define GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(n) (((n) & 0x3fU) << 7)
#define GPU_H3_SP_VS_CNTL_0_MERGEDREGS (1U << 20)
#define GPU_H3_SP_VS_CNTL_0_UNKNOWN31 (1U << 31)
#define GPU_H3_SP_PS_CNTL_0_THREADSIZE (1U << 20)
#define GPU_H3_SP_PS_CNTL_0_VARYING (1U << 22)
#define GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP (1U << 24)
#define GPU_H3_SP_PS_CNTL_0_MERGEDREGS (1U << 31)
#define GPU_H3_SP_VS_CNTL_0 \
    (GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(GPU_H3_SP_VS_FULLREGFOOTPRINT) | \
     GPU_H3_SP_VS_CNTL_0_MERGEDREGS | \
     GPU_H3_SP_VS_CNTL_0_UNKNOWN31)
#define GPU_H3_SP_PS_CNTL_0 \
    (GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(GPU_H3_SP_PS_FULLREGFOOTPRINT) | \
     GPU_H3_SP_PS_CNTL_0_THREADSIZE | \
     GPU_H3_SP_PS_CNTL_0_VARYING | \
     GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP | \
     GPU_H3_SP_PS_CNTL_0_MERGEDREGS)
#define GPU_D1_SP_PS_CNTL_0 \
    (GPU_H3_SP_PS_CNTL_0 | (1U << 23) | (1U << 26))
#define GPU_H3_GRAS_CL_CNTL 0x000000c0U
#define GPU_H3_GRAS_CL_INTERP_CNTL 0x00000001U
#define GPU_H3_GRAS_CL_GUARDBAND_CLIP_ADJ 0x0007fdffU
#define GPU_H3_GRAS_SU_CNTL 0x00000814U
#define GPU_H3_GRAS_SU_POINT_MINMAX 0xffc00001U
#define GPU_H3_GRAS_SU_POINT_SIZE 0x00000010U
#define GPU_H3_GRAS_SU_POLY_OFFSET_SCALE 0x00000000U
#define GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET 0x00000000U
#define GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP 0x00000000U
#define GPU_H3_GRAS_LRZ_PS_INPUT_CNTL 0x00000000U
#define GPU_H3_GRAS_LRZ_PS_SAMPLEFREQ_CNTL 0x00000000U
#define GPU_H3_RB_INTERP_CNTL 0x00000401U
#define GPU_H3_RB_PS_INPUT_CNTL 0x00000000U
#define GPU_H3_RB_PS_SAMPLEFREQ_CNTL 0x00000000U
#define GPU_H3_RB_PS_OUTPUT_CNTL 0x00000000U
#define GPU_H3_RB_PS_MRT_CNTL 0x00000001U
#define GPU_H3_GRAS_SC_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_RENDER_CNTL_BASE 0x00000010U
#define GPU_H3_RB_RENDER_CNTL_FLAG_MRT0 \
    (GPU_H3_RB_RENDER_CNTL_BASE | (1U << 16))
#define GPU_H3_RB_RENDER_CNTL GPU_H3_RB_RENDER_CNTL_FLAG_MRT0
#define GPU_H3_TPL1_MSAA_SAMPLE_POS_CNTL 0x00000000U
#define GPU_H3_RB_CCU_CNTL 0x10000000U
#define GPU_H3_GRAS_SC_BIN_CNTL GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING
#define GPU_H3_RB_CNTL GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING
#define GPU_H3_RB_CCU_COLOR_OFFSET 0x00020000U
#define GPU_H3_RB_CCU_DEPTH_OFFSET 0x00000000U
#define GPU_H3_VPC_VS_CNTL (8U | (4U << 8) | (0xffU << 16))
#define GPU_H3_VPC_PS_CNTL (4U | (0xffU << 8) | (1U << 16) | (0xffU << 24))
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
#define GPU_H3_VPC_RAST_CNTL GPU_H3_A6XX_POLYMODE6_TRIANGLES
#define GPU_H3_VPC_RAST_STREAM_CNTL 0x00000000U
#define GPU_H3_PC_DGEN_RAST_CNTL GPU_H3_A6XX_POLYMODE6_TRIANGLES
#define GPU_H3_VPC_SO_OVERRIDE 0x00000000U
#define GPU_H3_PC_STEREO_RENDERING_CNTL 0x00000000U
#define GPU_H3_TPL1_PS_SWIZZLE_CNTL 0x00000000U
#define GPU_H3_VPC_UNKNOWN_9210 0x00000000U
#define GPU_H3_SP_INVALID_REG 0xfcU
#define GPU_H3_SP_PS_INITIAL_TEX_LOAD_CNTL 0x00007fc0U
#define GPU_H3_SP_PS_WAVE_CNTL 0x00000003U
#define GPU_H3_SP_LB_PARAM_LIMIT 0x00000007U
#define GPU_H3_SP_PS_OUTPUT_CNTL \
    ((GPU_H3_SP_INVALID_REG << 8) | \
     (GPU_H3_SP_INVALID_REG << 16) | \
     (GPU_H3_SP_INVALID_REG << 24))
#define GPU_H3_SP_PS_MRT_CNTL 0x00000001U
#define GPU_H3_SP_REG_PROG_ID_0 \
    ((GPU_H3_SP_INVALID_REG << 0) | \
     (GPU_H3_SP_INVALID_REG << 8) | \
     (GPU_H3_SP_INVALID_REG << 16) | \
     (GPU_H3_SP_INVALID_REG << 24))
#define GPU_H3_SP_REG_PROG_ID_1 \
    ((0U << 0) | \
     (GPU_H3_SP_INVALID_REG << 8) | \
     (GPU_H3_SP_INVALID_REG << 16) | \
     (GPU_H3_SP_INVALID_REG << 24))
#define GPU_H3_SP_REG_PROG_ID_2 GPU_H3_SP_REG_PROG_ID_0
#define GPU_H3_SP_REG_PROG_ID_3 \
    ((GPU_H3_SP_INVALID_REG << 0) | (GPU_H3_SP_INVALID_REG << 8))
#define GPU_H3_SP_BLEND_CNTL 0x00000100U
#define GPU_H3_RB_BLEND_CNTL 0xffff0100U
#define GPU_H3_RB_MRT0_BLEND_CONTROL 0x08040804U
#define GPU_H3_PC_MODE_CNTL 0x0000001fU
#define GPU_H3_PC_VS_CNTL 0x00000008U
#define GPU_H3_VFD_CNTL_0 0x00000303U
#define GPU_H3_VFD_CNTL_1 0xfcfcfc09U
#define GPU_H3_VFD_CNTL_2 \
    ((GPU_H3_SP_INVALID_REG << 0) | (GPU_H3_SP_INVALID_REG << 8))
#define GPU_H3_VFD_CNTL_3 GPU_H3_SP_REG_PROG_ID_0
#define GPU_H3_VFD_CNTL_4 GPU_H3_SP_INVALID_REG
#define GPU_H3_VFD_CNTL_5 \
    ((GPU_H3_SP_INVALID_REG << 0) | (GPU_H3_SP_INVALID_REG << 8))
#define GPU_H3_VFD_CNTL_6 0x00000000U
#define GPU_H3_VFD_FETCH_INSTR0 0xc8200000U
#define GPU_H3_VFD_FETCH_INSTR1 0xc8200200U
#define GPU_H3_VFD_FETCH_INSTR2 0x44c00400U
#define GPU_H3_VFD_FETCH_STEP_RATE 0x00000001U
#define GPU_H3_VFD_DEST_CNTL0 0x0000000fU
#define GPU_H3_VFD_DEST_CNTL1 0x0000004fU
#define GPU_H3_VFD_DEST_CNTL2 0x00000081U
#define GPU_G4_REG_GRAS_A2D_BLT_CNTL 0x8400U
#define GPU_H5_REG_GRAS_A2D_SRC_XMIN 0x8401U
#define GPU_H5_REG_GRAS_A2D_SRC_XMAX 0x8402U
#define GPU_H5_REG_GRAS_A2D_SRC_YMIN 0x8403U
#define GPU_H5_REG_GRAS_A2D_SRC_YMAX 0x8404U
#define GPU_G4_REG_GRAS_A2D_DEST_TL 0x8405U
#define GPU_G4_REG_GRAS_A2D_DEST_BR 0x8406U
#define GPU_H5_REG_GRAS_A2D_SCISSOR_TL 0x840aU
#define GPU_H5_REG_GRAS_A2D_SCISSOR_BR 0x840bU
#define GPU_G4_REG_RB_A2D_BLT_CNTL 0x8c00U
#define GPU_G4_REG_RB_A2D_PIXEL_CNTL 0x8c01U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_INFO 0x8c17U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_BASE 0x8c18U
#define GPU_G4_REG_RB_A2D_DEST_BUFFER_PITCH 0x8c1aU
#define GPU_H5_REG_RB_A2D_DEST_FLAG_BUFFER_BASE 0x8c20U
#define GPU_H5_REG_RB_A2D_DEST_FLAG_BUFFER_PITCH 0x8c22U
#define GPU_G4_REG_RB_A2D_CLEAR_COLOR_DW0 0x8c2cU
#define GPU_G4_REG_SP_A2D_OUTPUT_INFO 0xacc0U
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_INFO 0xb4c0U
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_SIZE 0xb4c1U
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_BASE 0xb4c2U
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_PITCH 0xb4c4U
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_FLAG_BASE 0xb4caU
#define GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_FLAG_PITCH 0xb4ccU
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
#define GPU_H3_REG_SP_VS_CONST_CONFIG 0xb800U
#define GPU_H3_REG_SP_PS_CONST_CONFIG 0xbb10U
#define GPU_H3_REG_SP_MODE_CNTL 0xab00U
#define GPU_H3_REG_SP_UPDATE_CNTL 0xbb08U
#define GPU_H3_REG_TPL1_MODE_CNTL 0xb309U
#define GPU_H3_SP_CONST_CONFIG_ENABLED 0x00000100U
#define GPU_H3_SP_MODE_CNTL 0x00000005U
#define GPU_H3_TPL1_MODE_CNTL 0x000000a2U
#define GPU_H3_WINDOW_OFFSET 0x00000000U
#define GPU_H2_REG_GRAS_CL_CNTL 0x8000U
#define GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE 0x8001U
#define GPU_H2_REG_GRAS_CL_INTERP_CNTL 0x8005U
#define GPU_H2_REG_GRAS_CL_VIEWPORT 0x8010U
#define GPU_H2_REG_GRAS_CL_GUARDBAND_CLIP_ADJ 0x8006U
#define GPU_H2_REG_GRAS_SU_CNTL 0x8090U
#define GPU_H3_REG_GRAS_SU_POINT_MINMAX 0x8091U
#define GPU_H3_REG_GRAS_SU_POINT_SIZE 0x8092U
#define GPU_H3_REG_GRAS_SU_POLY_OFFSET_SCALE 0x8095U
#define GPU_H3_REG_GRAS_SU_POLY_OFFSET_OFFSET 0x8096U
#define GPU_H3_REG_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP 0x8097U
#define GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL 0x8099U
#define GPU_H2_REG_GRAS_SU_VS_SIV_CNTL 0x809bU
#define GPU_H2_REG_GRAS_SC_CNTL 0x80a0U
#define GPU_H3_REG_GRAS_SC_BIN_CNTL 0x80a1U
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
#define GPU_H3_REG_RB_CNTL 0x8800U
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
#define GPU_H3_REG_RB_WINDOW_OFFSET 0x8890U
#define GPU_H3_REG_RB_RESOLVE_WINDOW_OFFSET 0x88d4U
#define GPU_H3_REG_RB_COLOR_FLAG_BUFFER0_ADDR 0x8903U
#define GPU_H3_REG_RB_COLOR_FLAG_BUFFER0_PITCH 0x8905U
#define GPU_A640_REG_RB_DBG_ECO_CNTL 0x8e04U
#define GPU_A640_REG_RB_RBP_CNTL 0x8e01U
#define GPU_A640_RB_DBG_ECO_CNTL 0x04100000U
#define GPU_A640_RB_RBP_CNTL 0x00000001U
#define GPU_H2_REG_VPC_VARYING_INTERP_MODE_0 0x9200U
#define GPU_H2_REG_VPC_VARYING_REPLACE_MODE_0 0x9208U
#define GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL 0x9101U
#define GPU_H2_REG_VPC_VS_SIV_CNTL 0x9104U
#define GPU_H2_REG_VPC_VARYING_LM_TRANSFER_CNTL0 0x9212U
#define GPU_H3_REG_VPC_UNKNOWN_9210 0x9210U
#define GPU_H2_REG_VPC_REPLACE_MODE_CNTL 0x9236U
#define GPU_H2_REG_VPC_ROTATION_CNTL 0x9300U
#define GPU_H3_REG_VPC_RAST_CNTL 0x9108U
#define GPU_H2_REG_VPC_VS_CNTL 0x9301U
#define GPU_H2_REG_VPC_PS_CNTL 0x9304U
#define GPU_H3_REG_VPC_SO_OVERRIDE 0x9306U
#define GPU_A640_REG_VPC_DBG_ECO_CNTL 0x9600U
#define GPU_A640_VPC_DBG_ECO_CNTL 0x02000000U
#define GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2 0x9311U
#define GPU_H2_REG_VPC_VS_SIV_CNTL_V2 0x9314U
#define GPU_H3_REG_VPC_RAST_STREAM_CNTL 0x9980U
#define GPU_H3_REG_PC_DGEN_RAST_CNTL 0x9981U
#define GPU_H2_REG_PC_RESTART_INDEX 0x9803U
#define GPU_H2_REG_PC_MODE_CNTL 0x9804U
#define GPU_A640_REG_PC_MODE_CNTL 0x9804U
#define GPU_A640_REG_PC_POWER_CNTL 0x9805U
#define GPU_A640_PC_MODE_CNTL 0x0000001fU
#define GPU_A640_PC_POWER_CNTL 0x00000001U
#define GPU_H2_REG_PC_CNTL 0x9b00U
#define GPU_H2_REG_PC_VS_CNTL 0x9b01U
#define GPU_H3_REG_PC_STEREO_RENDERING_CNTL 0x9b07U
#define GPU_H2_REG_VFD_CNTL_0 0xa000U
#define GPU_H2_REG_VFD_CNTL_1 0xa001U
#define GPU_A640_REG_VFD_POWER_CNTL 0xa0f8U
#define GPU_A640_VFD_POWER_CNTL 0x00000001U
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
#define GPU_A640_REG_SP_CHICKEN_BITS 0xae03U
#define GPU_A640_SP_CHICKEN_BITS 0x00000420U
#define GPU_H3_REG_TPL1_WINDOW_OFFSET 0xb307U
#define GPU_H3_REG_TPL1_MSAA_SAMPLE_POS_CNTL 0xb304U
#define GPU_D1_REG_TPL1_GFX_BORDER_COLOR_BASE 0xb302U
#define GPU_A640_REG_TPL1_DBG_ECO_CNTL 0xb600U
#define GPU_A640_TPL1_DBG_ECO_CNTL 0x00008000U
#define GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL 0xb183U
#define GPU_H3_REG_SP_WINDOW_OFFSET 0xb4d1U
#define GPU_H3_REG_SP_PS_INITIAL_TEX_LOAD_CNTL 0xa99eU
#define GPU_D1_REG_SP_PS_TSIZE 0xa9a7U
#define GPU_H3_REG_SP_PS_WAVE_CNTL 0xb980U
#define GPU_H3_REG_SP_LB_PARAM_LIMIT 0xb982U
#define GPU_H3_REG_SP_REG_PROG_ID_0 0xb983U
#define GPU_H3_REG_SP_REG_PROG_ID_1 0xb984U
#define GPU_H3_REG_SP_REG_PROG_ID_2 0xb985U
#define GPU_H3_REG_SP_REG_PROG_ID_3 0xb986U
#define GPU_D1_REG_SP_PS_SAMPLER_BASE 0xa9e0U
#define GPU_D1_REG_SP_PS_TEXMEMOBJ_BASE 0xa9e4U
#define GPU_A640_REG_UCHE_UNKNOWN_0E12 0x0e12U
#define GPU_A640_UCHE_UNKNOWN_0E12 0x00000001U
#define GPU_H3_A640_INIT_MAGIC_REG_WRITES 9U
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

static bool gpu_g4_pm4_emit_event(uint32_t *words,
                                  unsigned int *dwords,
                                  uint32_t event) {
    return gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_EVENT_WRITE, 1) &&
           gpu_g4_pm4_push(words, dwords, event);
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

static bool gpu_h3_pm4_emit_reg3(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value0,
                                 uint32_t value1,
                                 uint32_t value2) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 3) &&
           gpu_g4_pm4_push(words, dwords, value0) &&
           gpu_g4_pm4_push(words, dwords, value1) &&
           gpu_g4_pm4_push(words, dwords, value2);
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

static bool gpu_h5_append_tile6_3_to_linear_a2d_pm4_ex(uint32_t *words,
                                                       unsigned int *dwords,
                                                       uint64_t src_gpuaddr,
                                                       uint64_t src_flag_gpuaddr,
                                                       uint64_t dst_gpuaddr,
                                                       uint64_t event_gpuaddr,
                                                       uint32_t width,
                                                       uint32_t height,
                                                       uint32_t stride,
                                                       uint32_t flag_pitch) {
    uint64_t src_base = src_gpuaddr & ~0x3fULL;
    uint64_t src_flag_base = src_flag_gpuaddr & ~0x3fULL;
    uint64_t dst_base = dst_gpuaddr & ~0x3fULL;
    uint32_t pitch_qwords;
    uint32_t texture_size;
    uint32_t src_max_x;
    uint32_t src_max_y;
    uint32_t src_br;

    if (width == 0U || height == 0U || stride == 0U ||
        (stride & 63U) != 0U || width > 8192U || height > 8192U) {
        return false;
    }
    pitch_qwords = stride >> 6;
    texture_size = width | (height << 15);
    src_max_x = (width - 1U) << 8;
    src_max_y = (height - 1U) << 8;
    src_br = ((height - 1U) << 16) | (width - 1U);
    if (!gpu_g4_pm4_emit_event_ts(words, dwords,
                                  GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS,
                                  event_gpuaddr,
                                  GPU_G4_EVENT_SEQNO_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_SET_MARKER, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_G4_A6XX_CP_SET_MARKER_RM6_BLIT2DSCALE)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_BLT_CNTL,
                              GPU_H5_A2D_BLT_CNTL_SCALE_RGBA8) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_GRAS_A2D_BLT_CNTL,
                              GPU_H5_A2D_BLT_CNTL_SCALE_RGBA8) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_SP_A2D_OUTPUT_INFO,
                              GPU_H5_A2D_OUTPUT_INFO_RGBA8) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_PIXEL_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_INFO,
                              GPU_H5_A2D_DEST_BUFFER_INFO_LINEAR)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_BASE,
                              (uint32_t)(dst_base & 0xffffffffULL),
                              (uint32_t)(dst_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_G4_REG_RB_A2D_DEST_BUFFER_PITCH,
                              pitch_qwords) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H5_REG_RB_A2D_DEST_FLAG_BUFFER_BASE,
                              (uint32_t)(dst_base & 0xffffffffULL),
                              (uint32_t)(dst_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H5_REG_RB_A2D_DEST_FLAG_BUFFER_PITCH,
                              0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg4(words, dwords, GPU_H5_REG_GRAS_A2D_SRC_XMIN,
                              0,
                              src_max_x,
                              0,
                              src_max_y) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_G4_REG_GRAS_A2D_DEST_TL,
                              0,
                              src_br) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H5_REG_GRAS_A2D_SCISSOR_TL,
                              0,
                              src_br)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_INFO,
                              GPU_H5_A2D_SRC_TEXTURE_INFO_TILE6_3_FLAGS) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_SIZE,
                              texture_size) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_BASE,
                              (uint32_t)(src_base & 0xffffffffULL),
                              (uint32_t)(src_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_PITCH,
                              (pitch_qwords << 9)) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_FLAG_BASE,
                              (uint32_t)(src_flag_base & 0xffffffffULL),
                              (uint32_t)(src_flag_base >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_FLAG_PITCH,
                              flag_pitch)) {
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

static bool gpu_h5_append_tile6_3_to_linear_a2d_pm4(uint32_t *words,
                                                    unsigned int *dwords,
                                                    uint64_t src_gpuaddr,
                                                    uint64_t src_flag_gpuaddr,
                                                    uint64_t dst_gpuaddr,
                                                    uint64_t event_gpuaddr) {
    return gpu_h5_append_tile6_3_to_linear_a2d_pm4_ex(words,
                                                      dwords,
                                                      src_gpuaddr,
                                                      src_flag_gpuaddr,
                                                      dst_gpuaddr,
                                                      event_gpuaddr,
                                                      GPU_H2_COLOR_WIDTH,
                                                      GPU_H2_COLOR_HEIGHT,
                                                      GPU_H2_COLOR_STRIDE,
                                                      GPU_H3_COLOR_FLAG_BUFFER_PITCH);
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

static bool gpu_h3_pm4_emit_load_state6_shader_units(uint32_t *words,
                                                     unsigned int *dwords,
                                                     uint8_t opcode,
                                                     uint32_t state_block,
                                                     uint64_t shader_gpuaddr,
                                                     uint32_t shader_units) {
    uint32_t load0 =
        GPU_H1_CP_LOAD_STATE6_STATE_SRC_INDIRECT |
        state_block |
        ((shader_units & 0x3ffU) << 22);

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

static bool gpu_h3_pm4_emit_reg8(uint32_t *words,
                                 unsigned int *dwords,
                                 uint32_t reg,
                                 uint32_t value0,
                                 uint32_t value1,
                                 uint32_t value2,
                                 uint32_t value3,
                                 uint32_t value4,
                                 uint32_t value5,
                                 uint32_t value6,
                                 uint32_t value7) {
    return gpu_g4_pm4_emit_pkt4(words, dwords, reg, 8) &&
           gpu_g4_pm4_push(words, dwords, value0) &&
           gpu_g4_pm4_push(words, dwords, value1) &&
           gpu_g4_pm4_push(words, dwords, value2) &&
           gpu_g4_pm4_push(words, dwords, value3) &&
           gpu_g4_pm4_push(words, dwords, value4) &&
           gpu_g4_pm4_push(words, dwords, value5) &&
           gpu_g4_pm4_push(words, dwords, value6) &&
           gpu_g4_pm4_push(words, dwords, value7);
}

static bool gpu_h2_append_3d_state_pm4_ex(uint32_t *words,
                                          unsigned int *dwords,
                                          unsigned int *state_reg_writes,
                                          uint64_t color_gpuaddr,
                                          uint64_t color_flag_gpuaddr,
                                          uint32_t color_width,
                                          uint32_t color_height,
                                          uint32_t color_stride,
                                          uint64_t color_alloc_size,
                                          uint32_t color_flag_pitch,
                                          uint32_t color_format,
                                          uint32_t color_output_mask,
                                          bool color_uint,
                                          bool color_flag_mrt,
                                          uint32_t sp_vs_output_reg0,
                                          uint32_t sp_ps_output_reg0) {
    uint64_t color_base = color_gpuaddr & ~0x3fULL;
    uint64_t color_flag_base = color_flag_gpuaddr & ~0x3fULL;
    uint32_t rb_mrt_control = (color_output_mask & 0xfU) << 7;
    uint32_t rb_render_cntl =
        color_flag_mrt ? GPU_H3_RB_RENDER_CNTL_FLAG_MRT0 : GPU_H3_RB_RENDER_CNTL_BASE;
    uint32_t rb_tile_mode =
        color_flag_mrt ? GPU_G4_A6XX_TILE6_3 : GPU_G4_A6XX_TILE6_LINEAR;
    uint32_t rb_mrt_info =
        color_format |
        (rb_tile_mode << 8) |
        (GPU_G4_A3XX_COLOR_SWAP_WZYX << 13);
    uint32_t sp_ps_mrt =
        color_format |
        (color_uint ? (1U << 9) : 0U);
    uint32_t pitch_qwords;
    uint32_t array_pitch_qwords;
    uint32_t screen_tl = gpu_h2_xy(0, 0);
    uint32_t screen_br;
    unsigned int reg_writes = 0;

    if (state_reg_writes != NULL) {
        *state_reg_writes = 0;
    }
    if (color_width == 0U || color_height == 0U || color_stride == 0U ||
        (color_stride & 63U) != 0U || color_alloc_size == 0U ||
        color_alloc_size < (uint64_t)color_stride * color_height ||
        color_alloc_size > UINT32_MAX ||
        color_width > 8192U || color_height > 8192U) {
        return false;
    }
    pitch_qwords = color_stride >> 6;
    array_pitch_qwords = (uint32_t)(color_alloc_size >> 6);
    screen_br = gpu_h2_xy(color_width, color_height);
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_SET_MARKER, 1) ||
        !gpu_g4_pm4_push(words, dwords,
                         GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_WINDOW_OFFSET,
                              GPU_H3_WINDOW_OFFSET) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_RESOLVE_WINDOW_OFFSET,
                              GPU_H3_WINDOW_OFFSET) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_WINDOW_OFFSET,
                              GPU_H3_WINDOW_OFFSET) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_WINDOW_OFFSET,
                              GPU_H3_WINDOW_OFFSET)) {
        return false;
    }
    reg_writes += 4;
    if (!gpu_g4_pm4_emit_pkt7(words, dwords,
                              (uint8_t)GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL, 1) ||
        !gpu_g4_pm4_push(words, dwords,
                         GPU_H3_CP_SKIP_IB2_ENABLE_GLOBAL_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords,
                              (uint8_t)GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL, 1) ||
        !gpu_g4_pm4_push(words, dwords,
                         GPU_H3_CP_SKIP_IB2_ENABLE_LOCAL_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords,
                              (uint8_t)GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE, 1) ||
        !gpu_g4_pm4_push(words, dwords,
                         GPU_H3_CP_SET_VISIBILITY_OVERRIDE_VALUE)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_CCU_CNTL,
                              GPU_H3_RB_CCU_CNTL)) {
        return false;
    }
    reg_writes += 1;
    if (!gpu_h2_pm4_emit_reg6(words, dwords, GPU_H2_REG_GRAS_CL_VIEWPORT,
                              gpu_h2_float_bits((float)color_width / 2.0f),
                              gpu_h2_float_bits((float)color_width / 2.0f),
                              gpu_h2_float_bits((float)color_height / 2.0f),
                              gpu_h2_float_bits((float)color_height / 2.0f),
                              gpu_h2_float_bits(0.0f),
                              gpu_h2_float_bits(1.0f))) {
        return false;
    }
    reg_writes += 6;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_CNTL,
                              GPU_H3_GRAS_CL_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE,
                              GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_INTERP_CNTL,
                              GPU_H3_GRAS_CL_INTERP_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_CL_GUARDBAND_CLIP_ADJ,
                              GPU_H3_GRAS_CL_GUARDBAND_CLIP_ADJ) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SU_CNTL,
                              GPU_H3_GRAS_SU_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_POINT_MINMAX,
                              GPU_H3_GRAS_SU_POINT_MINMAX) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_POINT_SIZE,
                              GPU_H3_GRAS_SU_POINT_SIZE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_POLY_OFFSET_SCALE,
                              GPU_H3_GRAS_SU_POLY_OFFSET_SCALE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_POLY_OFFSET_OFFSET,
                              GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET) ||
        !gpu_g4_pm4_emit_reg1(words, dwords,
                              GPU_H3_REG_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP,
                              GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL,
                              GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SU_VS_SIV_CNTL,
                              GPU_H3_GRAS_SU_VS_SIV_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_GRAS_SC_CNTL, 2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_GRAS_SC_BIN_CNTL,
                              GPU_H3_GRAS_SC_BIN_CNTL) ||
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
    reg_writes += 22;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_TL,
                              screen_tl, screen_br) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_VIEWPORT_SCISSOR_TL,
                              screen_tl, screen_br) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_GRAS_SC_WINDOW_SCISSOR_TL,
                              screen_tl, screen_br)) {
        return false;
    }
    reg_writes += 6;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_CNTL,
                              GPU_H3_RB_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_RENDER_CNTL,
                              rb_render_cntl) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_RAS_MSAA_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_DEST_MSAA_CNTL, 1U << 2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_RB_MSAA_SAMPLE_POS_CNTL,
                              GPU_H3_RB_MSAA_SAMPLE_POS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_INTERP_CNTL,
                              GPU_H3_RB_INTERP_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_INPUT_CNTL,
                              GPU_H3_RB_PS_INPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_OUTPUT_CNTL,
                              GPU_H3_RB_PS_OUTPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_MRT_CNTL,
                              GPU_H3_RB_PS_MRT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_OUTPUT_MASK,
                              color_output_mask) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_SRGB_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_PS_SAMPLEFREQ_CNTL,
                              GPU_H3_RB_PS_SAMPLEFREQ_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_MODE_CNTL, 0x10) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_BLEND_CNTL,
                              GPU_H3_RB_BLEND_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_DEPTH_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_RB_STENCIL_CNTL, 0)) {
        return false;
    }
    reg_writes += 16;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_RB_MRT0_CONTROL,
                              rb_mrt_control, GPU_H3_RB_MRT0_BLEND_CONTROL) ||
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
    if (color_flag_mrt) {
        if (!gpu_g4_pm4_emit_reg2(words, dwords,
                                  GPU_H3_REG_RB_COLOR_FLAG_BUFFER0_ADDR,
                                  (uint32_t)(color_flag_base & 0xffffffffULL),
                                  (uint32_t)(color_flag_base >> 32)) ||
            !gpu_g4_pm4_emit_reg1(words, dwords,
                                  GPU_H3_REG_RB_COLOR_FLAG_BUFFER0_PITCH,
                                  color_flag_pitch)) {
            return false;
        }
        reg_writes += 3;
    }
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
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_RAST_CNTL,
                              GPU_H3_VPC_RAST_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_REPLACE_MODE_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_ROTATION_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_CNTL,
                              GPU_H3_VPC_VS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_PS_CNTL,
                              GPU_H3_VPC_PS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_SO_OVERRIDE,
                              GPU_H3_VPC_SO_OVERRIDE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2,
                              GPU_H3_VPC_VS_CLIP_CULL_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VPC_VS_SIV_CNTL_V2,
                              GPU_H3_VPC_VS_SIV_CNTL_V2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_VPC_RAST_STREAM_CNTL,
                              GPU_H3_VPC_RAST_STREAM_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_PC_DGEN_RAST_CNTL,
                              GPU_H3_PC_DGEN_RAST_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_RESTART_INDEX, 0xffffffffU) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_MODE_CNTL,
                              GPU_H3_PC_MODE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_PC_VS_CNTL,
                              GPU_H3_PC_VS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_PC_STEREO_RENDERING_CNTL,
                              GPU_H3_PC_STEREO_RENDERING_CNTL)) {
        return false;
    }
    reg_writes += 24;
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_VFD_CNTL_0, 0, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_MODE_CNTL, 3) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H2_REG_VFD_INDEX_OFFSET, 0, 0)) {
        return false;
    }
    reg_writes += 5;
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_OUTPUT_CNTL,
                              GPU_H3_SP_VS_OUTPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_OUTPUT_REG0,
                              sp_vs_output_reg0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_VS_VPC_DEST_REG0,
                              GPU_H3_SP_VS_VPC_DEST_REG0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_BLEND_CNTL,
                              GPU_H3_SP_BLEND_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_SRGB_CNTL, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_MSAA_SAMPLE_POS_CNTL,
                              GPU_H3_TPL1_MSAA_SAMPLE_POS_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL,
                              GPU_H3_TPL1_PS_SWIZZLE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_MASK,
                              color_output_mask) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_CNTL,
                              GPU_H3_SP_PS_OUTPUT_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_MRT_CNTL,
                              GPU_H3_SP_PS_MRT_CNTL) ||
        !gpu_h3_pm4_emit_reg8(words, dwords, GPU_H2_REG_SP_PS_OUTPUT_REG0,
                              sp_ps_output_reg0,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG,
                              GPU_H3_SP_INVALID_REG) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_SP_PS_MRT_REG0, sp_ps_mrt) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_PS_INITIAL_TEX_LOAD_CNTL,
                              GPU_H3_SP_PS_INITIAL_TEX_LOAD_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_PS_WAVE_CNTL,
                              GPU_H3_SP_PS_WAVE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_LB_PARAM_LIMIT,
                              GPU_H3_SP_LB_PARAM_LIMIT) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_REG_PROG_ID_0,
                              GPU_H3_SP_REG_PROG_ID_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_REG_PROG_ID_1,
                              GPU_H3_SP_REG_PROG_ID_1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_REG_PROG_ID_2,
                              GPU_H3_SP_REG_PROG_ID_2) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_REG_PROG_ID_3,
                              GPU_H3_SP_REG_PROG_ID_3)) {
        return false;
    }
    reg_writes += 26;
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

static bool gpu_h2_append_3d_state_pm4(uint32_t *words,
                                       unsigned int *dwords,
                                       unsigned int *state_reg_writes,
                                       uint64_t color_gpuaddr,
                                       uint64_t color_flag_gpuaddr,
                                       uint32_t color_format,
                                       uint32_t color_output_mask,
                                       bool color_uint,
                                       bool color_flag_mrt,
                                       uint32_t sp_vs_output_reg0,
                                       uint32_t sp_ps_output_reg0) {
    return gpu_h2_append_3d_state_pm4_ex(words,
                                         dwords,
                                         state_reg_writes,
                                         color_gpuaddr,
                                         color_flag_gpuaddr,
                                         GPU_H2_COLOR_WIDTH,
                                         GPU_H2_COLOR_HEIGHT,
                                         GPU_H2_COLOR_STRIDE,
                                         GPU_H2_COLOR_ALLOC_SIZE,
                                         GPU_H3_COLOR_FLAG_BUFFER_PITCH,
                                         color_format,
                                         color_output_mask,
                                         color_uint,
                                         color_flag_mrt,
                                         sp_vs_output_reg0,
                                         sp_ps_output_reg0);
}

static bool gpu_h2_build_3d_state_pm4(uint32_t *words,
                                      unsigned int *dwords,
                                      unsigned int *state_reg_writes,
                                      uint64_t color_gpuaddr) {
    *dwords = 0;
    return gpu_h2_append_3d_state_pm4(words, dwords, state_reg_writes, color_gpuaddr,
                                      0, GPU_G4_A6XX_FMT6_32_UINT, 0xfU, true, false,
                                      0x00000f00U, 0U);
}

static bool gpu_h3_append_shader_state_pm4_ex(uint32_t *words,
                                              unsigned int *dwords,
                                              uint64_t vs_gpuaddr,
                                              uint64_t fs_gpuaddr,
                                              uint32_t ps_config,
                                              uint32_t ps_cntl_0) {
    uint32_t vs_cntl_0 = GPU_H3_SP_VS_CNTL_0;

    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_UPDATE_CNTL,
                              GPU_H3_SP_UPDATE_CNTL_DRAW_STATE) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_MODE_CNTL,
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
                              GPU_H3_VS_SHADER_INSTRLEN) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_VS_CONST_CONFIG,
                              GPU_H3_SP_CONST_CONFIG_ENABLED)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CNTL_0, ps_cntl_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_H1_REG_SP_PS_BASE,
                              (uint32_t)(fs_gpuaddr & 0xffffffffULL),
                              (uint32_t)(fs_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_CONFIG,
                              ps_config) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H1_REG_SP_PS_INSTR_SIZE,
                              GPU_H3_FS_SHADER_INSTRLEN) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_PS_CONST_CONFIG,
                              GPU_H3_SP_CONST_CONFIG_ENABLED)) {
        return false;
    }
    return gpu_h3_pm4_emit_load_state6_shader_units(words, dwords,
                                                    (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_GEOM,
                                                    GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER,
                                                    vs_gpuaddr,
                                                    GPU_H3_VS_SHADER_INSTRLEN) &&
           gpu_h3_pm4_emit_load_state6_shader_units(words, dwords,
                                                    (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
                                                    GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER,
                                                    fs_gpuaddr,
                                                    GPU_H3_FS_SHADER_INSTRLEN);
}

static bool gpu_h3_append_shader_state_pm4(uint32_t *words,
                                           unsigned int *dwords,
                                           uint64_t vs_gpuaddr,
                                           uint64_t fs_gpuaddr) {
    return gpu_h3_append_shader_state_pm4_ex(words, dwords, vs_gpuaddr, fs_gpuaddr,
                                             GPU_H1_SP_CONFIG_ENABLED,
                                             GPU_H3_SP_PS_CNTL_0);
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

static bool gpu_h3_append_a640_init_magic_pm4(uint32_t *words,
                                              unsigned int *dwords) {
    return gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_RB_DBG_ECO_CNTL,
                                GPU_A640_RB_DBG_ECO_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_SP_CHICKEN_BITS,
                                GPU_A640_SP_CHICKEN_BITS) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_TPL1_DBG_ECO_CNTL,
                                GPU_A640_TPL1_DBG_ECO_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_VPC_DBG_ECO_CNTL,
                                GPU_A640_VPC_DBG_ECO_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_RB_RBP_CNTL,
                                GPU_A640_RB_RBP_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_PC_MODE_CNTL,
                                GPU_A640_PC_MODE_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_PC_POWER_CNTL,
                                GPU_A640_PC_POWER_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_VFD_POWER_CNTL,
                                GPU_A640_VFD_POWER_CNTL) &&
           gpu_g4_pm4_emit_reg1(words, dwords,
                                GPU_A640_REG_UCHE_UNKNOWN_0E12,
                                GPU_A640_UCHE_UNKNOWN_0E12);
}

static uint32_t gpu_c1_pm4_load_state6_0(uint32_t state_type,
                                         uint32_t state_src,
                                         uint32_t state_block,
                                         uint32_t num_units,
                                         uint32_t dst_off) {
    return (dst_off & 0x3fffU) |
           state_type |
           state_src |
           state_block |
           ((num_units & 0x3ffU) << 22);
}

static bool gpu_c1_pm4_emit_load_state6_indirect(uint32_t *words,
                                                 unsigned int *dwords,
                                                 uint8_t opcode,
                                                 uint32_t state_type,
                                                 uint32_t state_block,
                                                 uint64_t gpuaddr,
                                                 uint32_t num_units) {
    uint32_t load0 = gpu_c1_pm4_load_state6_0(
        state_type,
        GPU_C1_CP_LOAD_STATE6_STATE_SRC_INDIRECT,
        state_block,
        num_units,
        0);

    return gpu_g4_pm4_emit_pkt7(words, dwords, opcode, 3) &&
           gpu_g4_pm4_push(words, dwords, load0) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(gpuaddr & 0xffffffffULL)) &&
           gpu_g4_pm4_push(words, dwords, (uint32_t)(gpuaddr >> 32));
}

static bool gpu_c1_pm4_emit_load_state6_direct(uint32_t *words,
                                               unsigned int *dwords,
                                               uint8_t opcode,
                                               uint32_t state_type,
                                               uint32_t state_block,
                                               const uint32_t *payload,
                                               uint32_t payload_dwords,
                                               uint32_t num_units) {
    uint32_t load0 = gpu_c1_pm4_load_state6_0(
        state_type,
        GPU_C1_CP_LOAD_STATE6_STATE_SRC_DIRECT,
        state_block,
        num_units,
        0);
    uint32_t index;

    if (!gpu_g4_pm4_emit_pkt7(words, dwords, opcode, (uint16_t)(3U + payload_dwords)) ||
        !gpu_g4_pm4_push(words, dwords, load0) ||
        !gpu_g4_pm4_push(words, dwords, 0) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    for (index = 0; index < payload_dwords; ++index) {
        if (!gpu_g4_pm4_push(words, dwords, payload[index])) {
            return false;
        }
    }
    return true;
}

static void gpu_c1_write_uav_descriptor(uint32_t *desc, uint64_t uav_gpuaddr) {
    uint64_t uav_base = uav_gpuaddr & ~0x3fULL;
    unsigned int index;

    for (index = 0; index < GPU_C1_DESCRIPTOR_DWORDS; ++index) {
        desc[index] = 0;
    }
    desc[0] = GPU_C1_DESC0_R32_UINT_LINEAR;
    desc[1] = GPU_C1_DESC1_WIDTH_32;
    desc[2] = GPU_C1_DESC2_BUFFER_STRUCT1;
    desc[4] = (uint32_t)(uav_base & 0xffffffffULL);
    desc[5] = (uint32_t)(uav_base >> 32);
}

static void gpu_c2_write_uav_descriptor(uint32_t *desc, uint64_t uav_gpuaddr) {
    uint64_t uav_base = uav_gpuaddr & ~0x3fULL;
    unsigned int index;

    for (index = 0; index < GPU_C1_DESCRIPTOR_DWORDS; ++index) {
        desc[index] = 0;
    }
    desc[0] = GPU_C1_DESC0_R32_UINT_LINEAR;
    desc[1] = GPU_C2_DESC1_WIDTH;
    desc[2] = GPU_C1_DESC2_BUFFER_STRUCT1;
    desc[4] = (uint32_t)(uav_base & 0xffffffffULL);
    desc[5] = (uint32_t)(uav_base >> 32);
}

enum gpu_d1_texture_source_kind {
    GPU_D1_TEXTURE_SOURCE_CHECKERBOARD = 0,
    GPU_D1_TEXTURE_SOURCE_REALFRAME_MONO1 = 1,
};

struct gpu_d1_texture_source_config {
    enum gpu_d1_texture_source_kind kind;
    const char *manifest_path;
    uint32_t frame_index;
};

struct gpu_d3_video_frame_stats {
    int rc;
    int sync_rc;
    int submit_rc;
    int wait_rc;
    int readback_sync_rc;
    int copy_rc;
    unsigned int submit_timestamp;
    unsigned int retired_timestamp;
    uint64_t texture_write_us;
    uint64_t gpu_wait_us;
    uint64_t readback_sync_us;
    uint64_t kms_copy_us;
    uint64_t changed_count;
    uint32_t first_word;
    uint32_t center_word;
    uint32_t semantic_sample_count;
    uint32_t semantic_sample_match_count;
    uint32_t semantic_exact_match_count;
    uint32_t semantic_edge_tolerant_match_count;
    uint32_t semantic_sample_mismatch_count;
    uint32_t semantic_first_mismatch_index;
    uint32_t semantic_first_mismatch_expected;
    uint32_t semantic_first_mismatch_value;
    uint32_t semantic_source_dark_count;
    uint32_t semantic_source_light_count;
    uint32_t semantic_output_dark_count;
    uint32_t semantic_output_light_count;
    uint32_t semantic_output_other_count;
};

struct gpu_d3_video_summary {
    int result_rc;
    int manifest_rc;
    int stream_open_rc;
    int stream_open_errno;
    int header_rc;
    int gpu_create_rc;
    int kms_begin_rc;
    int present_rc;
    int close_rc;
    int close_errno;
    uint32_t requested_frames;
    uint32_t start_frame;
    uint32_t presented_frames;
    uint32_t failed_frame;
    uint32_t skipped_frames;
    uint32_t last_frame_index;
    uint32_t source_width;
    uint32_t source_height;
    uint32_t source_stride;
    uint32_t source_frame_bytes;
    uint32_t target_width;
    uint32_t target_height;
    uint32_t target_stride;
    uint32_t target_bytes;
    uint32_t pm4_dwords;
    uint64_t stream_bytes;
    uint64_t elapsed_ns;
    uint64_t fps_milli;
    uint64_t read_avg_us;
    uint64_t read_max_us;
    uint64_t texture_avg_us;
    uint64_t texture_max_us;
    uint64_t gpu_wait_avg_us;
    uint64_t gpu_wait_max_us;
    uint64_t readback_avg_us;
    uint64_t readback_max_us;
    uint64_t copy_avg_us;
    uint64_t copy_max_us;
    uint64_t present_avg_us;
    uint64_t present_max_us;
    uint64_t total_avg_us;
    uint64_t total_max_us;
    uint64_t changed_total;
    uint32_t last_first_word;
    uint32_t last_center_word;
    uint32_t semantic_sample_count;
    uint32_t semantic_sample_match_count;
    uint32_t semantic_exact_match_count;
    uint32_t semantic_edge_tolerant_match_count;
    uint32_t semantic_sample_mismatch_count;
    uint32_t semantic_first_mismatch_index;
    uint32_t semantic_first_mismatch_expected;
    uint32_t semantic_first_mismatch_value;
    uint32_t semantic_source_dark_count;
    uint32_t semantic_source_light_count;
    uint32_t semantic_output_dark_count;
    uint32_t semantic_output_light_count;
    uint32_t semantic_output_other_count;
};

static uint64_t gpu_d1_round_up_u64(uint64_t value, uint64_t alignment) {
    if (alignment == 0U) {
        return value;
    }
    return ((value + alignment - 1ULL) / alignment) * alignment;
}

static uint32_t gpu_d1_checker_word(unsigned int x, unsigned int y) {
    return (((x / GPU_D1_CHECKER_BLOCK) ^ (y / GPU_D1_CHECKER_BLOCK)) & 1U) != 0U ?
        GPU_D1_CHECKER_LIGHT_WORD : GPU_D1_CHECKER_DARK_WORD;
}

static uint32_t gpu_d1_checker_expected_rgb(unsigned int x, unsigned int y) {
    return (((x / GPU_D1_CHECKER_BLOCK) ^ (y / GPU_D1_CHECKER_BLOCK)) & 1U) != 0U ?
        GPU_D1_CHECKER_LIGHT_RGB : GPU_D1_CHECKER_DARK_RGB;
}

static void gpu_d1_write_checker_texture(uint32_t *texture_words) {
    unsigned int y;

    if (texture_words == NULL) {
        return;
    }
    for (y = 0; y < GPU_D1_TEXTURE_HEIGHT; ++y) {
        unsigned int x;

        for (x = 0; x < GPU_D1_TEXTURE_WIDTH; ++x) {
            texture_words[(y * GPU_D1_TEXTURE_WIDTH) + x] =
                gpu_d1_checker_word(x, y);
        }
    }
}

static bool gpu_d2_mono1_bit(const uint8_t *frame,
                             const struct video_stream_manifest *manifest,
                             uint32_t x,
                             uint32_t y) {
    const uint8_t *row;
    uint8_t byte;

    if (frame == NULL || manifest == NULL ||
        x >= manifest->width || y >= manifest->height ||
        manifest->stride < (manifest->width + 7U) / 8U) {
        return false;
    }
    row = frame + ((size_t)y * manifest->stride);
    byte = row[x / 8U];
    return ((byte >> (7U - (x % 8U))) & 1U) != 0U;
}

static uint32_t gpu_d2_realframe_expected_rgb(const uint8_t *frame,
                                              const struct video_stream_manifest *manifest,
                                              uint32_t x,
                                              uint32_t y) {
    return gpu_d2_mono1_bit(frame, manifest, x, y) ?
        GPU_D2_REALFRAME_LIGHT_RGB : GPU_D2_REALFRAME_DARK_RGB;
}

static int gpu_d2_parse_realframe_manifest(const struct gpu_d1_texture_source_config *config,
                                           struct video_stream_manifest *manifest,
                                           struct gpu_h3_draw_envelope_probe_result *result) {
    uint64_t texture_bytes;
    int rc;

    if (config == NULL || config->manifest_path == NULL ||
        manifest == NULL || result == NULL) {
        return -EINVAL;
    }
    rc = video_parse_manifest(config->manifest_path, manifest);
    result->realframe_manifest_rc = rc;
    if (rc < 0) {
        return rc;
    }
    if (manifest->stream_version != VIDEO_STREAM_VERSION_A90VSTR1 ||
        manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 ||
        manifest->width == 0U || manifest->height == 0U ||
        manifest->width > 4096U || manifest->height > 4096U ||
        manifest->stride < (manifest->width + 7U) / 8U ||
        config->frame_index >= manifest->frame_count) {
        result->realframe_manifest_rc = -EINVAL;
        return -EINVAL;
    }
    texture_bytes = (uint64_t)manifest->width * (uint64_t)manifest->height *
                    GPU_D1_TEXTURE_BPP;
    if (texture_bytes == 0U || texture_bytes > GPU_D2_REALFRAME_MAX_TEXTURE_BYTES ||
        texture_bytes / GPU_D1_TEXTURE_BPP / manifest->height != manifest->width) {
        result->realframe_manifest_rc = -EFBIG;
        return -EFBIG;
    }
    result->realframe_requested_frame_index = config->frame_index;
    result->realframe_width = manifest->width;
    result->realframe_height = manifest->height;
    result->realframe_stride = manifest->stride;
    result->realframe_frame_bytes = manifest->frame_bytes;
    result->texture_width = manifest->width;
    result->texture_height = manifest->height;
    result->texture_stride = manifest->width * GPU_D1_TEXTURE_BPP;
    result->texture_bytes = (unsigned int)texture_bytes;
    return 0;
}

static int gpu_d2_read_realframe_mono1(const struct video_stream_manifest *manifest,
                                       uint32_t frame_index,
                                       uint8_t **frame_out,
                                       struct gpu_h3_draw_envelope_probe_result *result) {
    struct video_stream_header_v1 header;
    uint8_t *frame = NULL;
    int fd = -1;
    uint32_t index;
    int rc;

    if (manifest == NULL || frame_out == NULL || result == NULL ||
        frame_index >= manifest->frame_count) {
        return -EINVAL;
    }
    *frame_out = NULL;
    frame = (uint8_t *)malloc(manifest->frame_bytes);
    if (frame == NULL) {
        result->realframe_read_rc = -ENOMEM;
        return -ENOMEM;
    }
    errno = 0;
    fd = open(manifest->stream_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        result->realframe_open_rc = -1;
        result->realframe_open_errno = errno;
        free(frame);
        return negative_errno_or(EIO);
    }
    result->realframe_open_rc = 0;
    rc = video_read_exact_fd(fd, &header, sizeof(header));
    if (rc < 0) {
        result->realframe_header_rc = rc;
        goto out;
    }
    rc = video_validate_stream_header(manifest, &header);
    result->realframe_header_rc = rc;
    if (rc < 0) {
        goto out;
    }
    for (index = 0; index <= frame_index; ++index) {
        struct video_stream_frame_record_v1 record;

        rc = video_read_exact_fd(fd, &record, sizeof(record));
        if (rc < 0) {
            result->realframe_record_rc = rc;
            goto out;
        }
        if (record.index != index || record.payload_bytes != manifest->frame_bytes) {
            result->realframe_record_rc = -EINVAL;
            rc = -EINVAL;
            goto out;
        }
        if (index == frame_index) {
            rc = video_read_exact_fd(fd, frame, manifest->frame_bytes);
            result->realframe_read_rc = rc;
            if (rc < 0) {
                goto out;
            }
            result->realframe_record_rc = 0;
            result->realframe_record_index = record.index;
            result->realframe_payload_bytes = record.payload_bytes;
            *frame_out = frame;
            frame = NULL;
            rc = 0;
            goto out;
        }
        rc = video_skip_exact_fd(fd, record.payload_bytes);
        if (rc < 0) {
            result->realframe_read_rc = rc;
            goto out;
        }
    }
    rc = -EINVAL;
    result->realframe_record_rc = -EINVAL;

out:
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            result->realframe_close_rc = -1;
            result->realframe_close_errno = errno;
            if (rc == 0) {
                rc = negative_errno_or(EIO);
            }
        } else {
            result->realframe_close_rc = 0;
            result->realframe_close_errno = 0;
        }
    }
    free(frame);
    return rc;
}

static void gpu_d2_write_realframe_texture(uint32_t *texture_words,
                                           const uint8_t *frame,
                                           const struct video_stream_manifest *manifest,
                                           struct gpu_h3_draw_envelope_probe_result *result) {
    uint32_t y;

    if (texture_words == NULL || frame == NULL || manifest == NULL || result == NULL) {
        return;
    }
    for (y = 0; y < manifest->height; ++y) {
        uint32_t x;

        for (x = 0; x < manifest->width; ++x) {
            bool bit = gpu_d2_mono1_bit(frame, manifest, x, y);
            texture_words[((size_t)y * manifest->width) + x] =
                bit ? GPU_D2_REALFRAME_LIGHT_WORD : GPU_D2_REALFRAME_DARK_WORD;
            if (bit) {
                result->realframe_source_light_count += 1U;
            } else {
                result->realframe_source_dark_count += 1U;
            }
        }
    }
}

static void gpu_d1_write_sampler_descriptor(uint32_t *desc) {
    unsigned int index;

    if (desc == NULL) {
        return;
    }
    for (index = 0; index < GPU_D1_SAMPLER_DESC_DWORDS; ++index) {
        desc[index] = 0;
    }
    desc[0] = (1U << 5) | (1U << 8) | (1U << 11);
    desc[1] = (1U << 4) | (1U << 6);
}

static void gpu_d1_write_texture_descriptor_ex(uint32_t *desc,
                                               uint64_t texture_gpuaddr,
                                               uint32_t texture_width,
                                               uint32_t texture_height,
                                               uint32_t texture_stride,
                                               uint64_t texture_bytes) {
    uint64_t texture_base = texture_gpuaddr & ~0x3fULL;
    unsigned int index;

    if (desc == NULL) {
        return;
    }
    for (index = 0; index < GPU_D1_TEXMEMOBJ_DESC_DWORDS; ++index) {
        desc[index] = 0;
    }
    desc[0] =
        ((uint32_t)GPU_H3_COLOR_FORMAT << 22) |
        (0U << 30) |
        (0U << 4) |
        (1U << 7) |
        (2U << 10) |
        (3U << 13);
    desc[1] = texture_width | (texture_height << 15);
    desc[2] = (texture_stride << 7) | (1U << 29);
    desc[3] = (uint32_t)((texture_bytes + 4095ULL) >> 12);
    desc[4] = (uint32_t)(texture_base & 0xffffffffULL);
    desc[5] = (uint32_t)(texture_base >> 32) | (1U << 17);
    desc[6] = 0;
}

static bool gpu_d1_pm4_emit_texture_state(uint32_t *words,
                                          unsigned int *dwords,
                                          uint64_t sampler_gpuaddr,
                                          uint64_t texmem_gpuaddr) {
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_D1_REG_SP_PS_SAMPLER_BASE,
                              (uint32_t)(sampler_gpuaddr & 0xffffffffULL),
                              (uint32_t)(sampler_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_D1_REG_SP_PS_TEXMEMOBJ_BASE,
                              (uint32_t)(texmem_gpuaddr & 0xffffffffULL),
                              (uint32_t)(texmem_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_D1_REG_SP_PS_TSIZE, 1U)) {
        return false;
    }
    if (!gpu_c1_pm4_emit_load_state6_indirect(
            words, dwords, (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
            GPU_D1_CP_LOAD_STATE6_STATE_TYPE_SHADER,
            GPU_D1_CP_LOAD_STATE6_SB_FS_TEX,
            sampler_gpuaddr,
            1U) ||
        !gpu_c1_pm4_emit_load_state6_indirect(
            words, dwords, (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
            GPU_D1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS,
            GPU_D1_CP_LOAD_STATE6_SB_FS_TEX,
            texmem_gpuaddr,
            1U)) {
        return false;
    }
    return true;
}

static bool gpu_compute_build_pm4(uint32_t *words,
                                  unsigned int *dwords,
                                  uint64_t shader_gpuaddr,
                                  uint64_t uav_descriptor_gpuaddr,
                                  uint64_t event_gpuaddr,
                                  uint32_t shader_instrlen,
                                  uint32_t ndrange0,
                                  uint32_t global_x,
                                  uint32_t global_y,
                                  uint32_t global_z,
                                  uint32_t group_x,
                                  uint32_t group_y,
                                  uint32_t group_z) {
    uint32_t const_payload[12] = {
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x3f800000U, 0x40000000U, 0x40400000U, 0x40800000U,
        0x00000001U, 0x00000001U, 0x00000001U, 0x00000000U,
    };

    const_payload[8] = group_x;
    const_payload[9] = group_y;
    const_payload[10] = group_z;

    *dwords = 0;
    if (!gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_CACHE_INVALIDATE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_H3_PM4_CP_SET_MODE, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_H3_CP_SET_MODE_RESTORE_VALUE) ||
        !gpu_h3_append_a640_init_magic_pm4(words, dwords)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_MODE_CNTL,
                              GPU_H3_SP_MODE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_H3_REG_SP_UPDATE_CNTL,
                              GPU_C1_SP_UPDATE_CNTL) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_CONST_CONFIG,
                              GPU_C1_SP_CS_CONST_CONFIG) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_CONFIG,
                              GPU_C1_SP_CS_CONFIG) ||
        !gpu_g4_pm4_emit_reg1(words, dwords,
                              GPU_C1_REG_SP_CS_PROGRAM_COUNTER_OFFSET, 0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_INSTR_SIZE,
                              shader_instrlen) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_CNTL_0,
                              GPU_C1_SP_CS_CNTL_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_CNTL_1,
                              GPU_C1_SP_CS_CNTL_1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_HLSQ_CS_CTRL_REG1,
                              GPU_C1_HLSQ_CS_CTRL_REG1) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_CONST_CONFIG_0,
                              GPU_C1_SP_CS_CONST_CONFIG_0) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_WGE_CNTL,
                              GPU_C1_SP_CS_WGE_CNTL) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_C1_REG_SP_CS_BASE,
                              (uint32_t)(shader_gpuaddr & 0xffffffffULL),
                              (uint32_t)(shader_gpuaddr >> 32))) {
        return false;
    }
    if (!gpu_c1_pm4_emit_load_state6_indirect(
            words, dwords, (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
            GPU_C1_CP_LOAD_STATE6_STATE_TYPE_SHADER,
            GPU_C1_CP_LOAD_STATE6_SB_CS_SHADER,
            shader_gpuaddr,
            shader_instrlen) ||
        !gpu_c1_pm4_emit_load_state6_direct(
            words, dwords, (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
            GPU_C1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS,
            GPU_C1_CP_LOAD_STATE6_SB_CS_SHADER,
            const_payload,
            12U,
            3U) ||
        !gpu_c1_pm4_emit_load_state6_indirect(
            words, dwords, (uint8_t)GPU_H1_PM4_CP_LOAD_STATE6_FRAG,
            GPU_C1_CP_LOAD_STATE6_STATE_TYPE_UAV,
            GPU_C1_CP_LOAD_STATE6_SB_CS_SHADER,
            uav_descriptor_gpuaddr,
            1U)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg2(words, dwords, GPU_C1_REG_SP_CS_UAV_BASE,
                              (uint32_t)(uav_descriptor_gpuaddr & 0xffffffffULL),
                              (uint32_t)(uav_descriptor_gpuaddr >> 32)) ||
        !gpu_g4_pm4_emit_reg1(words, dwords, GPU_C1_REG_SP_CS_USIZE, 1U) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_SET_MARKER, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_C1_CP_SET_MARKER_RM6_COMPUTE)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg4(words, dwords, GPU_C1_REG_SP_CS_NDRANGE_0,
                              ndrange0,
                              global_x,
                              0U,
                              global_y) ||
        !gpu_h3_pm4_emit_reg3(words, dwords, GPU_C1_REG_SP_CS_NDRANGE_0 + 4U,
                              0U,
                              global_z,
                              0U) ||
        !gpu_h3_pm4_emit_reg3(words, dwords, GPU_C1_REG_SP_CS_KERNEL_GROUP_X,
                              group_x,
                              group_y,
                              group_z)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_C1_PM4_CP_EXEC_CS, 4) ||
        !gpu_g4_pm4_push(words, dwords, 0) ||
        !gpu_g4_pm4_push(words, dwords, group_x) ||
        !gpu_g4_pm4_push(words, dwords, group_y) ||
        !gpu_g4_pm4_push(words, dwords, group_z) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0) ||
        !gpu_g4_pm4_emit_event_ts(words, dwords,
                                  GPU_G4_EVENT_CACHE_FLUSH_TS,
                                  event_gpuaddr,
                                  GPU_G4_EVENT_SEQNO_VALUE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    return true;
}

static bool gpu_c1_build_compute_pm4(uint32_t *words,
                                     unsigned int *dwords,
                                     uint64_t shader_gpuaddr,
                                     uint64_t uav_descriptor_gpuaddr,
                                     uint64_t event_gpuaddr) {
    return gpu_compute_build_pm4(words, dwords, shader_gpuaddr,
                                 uav_descriptor_gpuaddr, event_gpuaddr,
                                 GPU_C1_SHADER_INSTRLEN,
                                 GPU_C1_SP_CS_NDRANGE_0,
                                 GPU_C1_SP_CS_GLOBAL_X,
                                 GPU_C1_SP_CS_GLOBAL_Y,
                                 GPU_C1_SP_CS_GLOBAL_Z,
                                 GPU_C1_SP_CS_GROUP_X,
                                 GPU_C1_SP_CS_GROUP_Y,
                                 GPU_C1_SP_CS_GROUP_Z);
}

static bool gpu_c2_build_compute_pm4(uint32_t *words,
                                     unsigned int *dwords,
                                     uint64_t shader_gpuaddr,
                                     uint64_t uav_descriptor_gpuaddr,
                                     uint64_t event_gpuaddr) {
    return gpu_compute_build_pm4(words, dwords, shader_gpuaddr,
                                 uav_descriptor_gpuaddr, event_gpuaddr,
                                 GPU_C2_SHADER_INSTRLEN,
                                 GPU_C2_SP_CS_NDRANGE_0,
                                 GPU_C2_SP_CS_GLOBAL_X,
                                 GPU_C2_SP_CS_GLOBAL_Y,
                                 GPU_C2_SP_CS_GLOBAL_Z,
                                 GPU_C2_SP_CS_GROUP_X,
                                 GPU_C2_SP_CS_GROUP_Y,
                                 GPU_C2_SP_CS_GROUP_Z);
}

static bool gpu_h3_build_draw_envelope_pm4(uint32_t *words,
                                           unsigned int *dwords,
                                           unsigned int *state_reg_writes,
                                           unsigned int *vfd_reg_writes,
                                           uint64_t color_gpuaddr,
                                           uint64_t color_flag_gpuaddr,
                                           uint64_t linear_gpuaddr,
                                           uint64_t event_gpuaddr,
                                           uint64_t vs_gpuaddr,
                                           uint64_t fs_gpuaddr,
                                           uint64_t vertex_gpuaddr,
                                           bool linearize_to_linear_buffer) {
    uint64_t vertex_base = vertex_gpuaddr & ~0x3fULL;
    uint32_t draw_initiator = gpu_h3_draw_initiator();

    *dwords = 0;
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 0;
    }
    if (!gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_CACHE_INVALIDATE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_H3_PM4_CP_SET_MODE, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_H3_CP_SET_MODE_RESTORE_VALUE)) {
        return false;
    }
    if (!gpu_h3_append_a640_init_magic_pm4(words, dwords) ||
        !gpu_h3_append_shader_state_pm4(words, dwords, vs_gpuaddr, fs_gpuaddr) ||
        !gpu_h2_append_3d_state_pm4(words, dwords, state_reg_writes, color_gpuaddr,
                                    color_flag_gpuaddr,
                                    GPU_H3_COLOR_FORMAT, GPU_H3_COLOR_OUTPUT_MASK,
                                    false, true, GPU_H3_SP_VS_OUTPUT_REG0,
                                    GPU_H3_PS_OUTPUT_REGID)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_CNTL_0,
                              GPU_H3_VFD_CNTL_0) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H2_REG_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_2,
                              GPU_H3_VFD_CNTL_3,
                              GPU_H3_VFD_CNTL_4,
                              GPU_H3_VFD_CNTL_5,
                              GPU_H3_VFD_CNTL_6) ||
        !gpu_g4_pm4_emit_reg4(words, dwords, GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE,
                              (uint32_t)(vertex_base & 0xffffffffULL),
                              (uint32_t)(vertex_base >> 32),
                              (uint32_t)GPU_H3_VERTEX_BYTES,
                              GPU_H3_VERTEX_STRIDE) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H3_REG_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR1,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR2,
                              GPU_H3_VFD_FETCH_STEP_RATE) ||
        !gpu_h3_pm4_emit_reg3(words, dwords, GPU_H3_REG_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL1,
                              GPU_H3_VFD_DEST_CNTL2)) {
        return false;
    }
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 20;
    }
    if (!gpu_h3_pm4_emit_draw_indx_offset(words, dwords, draw_initiator, 1U,
                                          GPU_H3_VERTEX_COUNT)) {
        return false;
    }
    if (linearize_to_linear_buffer) {
        if (!gpu_h5_append_tile6_3_to_linear_a2d_pm4(words, dwords,
                                                     color_gpuaddr,
                                                     color_flag_gpuaddr,
                                                     linear_gpuaddr,
                                                     event_gpuaddr)) {
            return false;
        }
    } else if (!gpu_g4_pm4_emit_event_ts(words, dwords,
                                         GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS,
                                         event_gpuaddr,
                                         GPU_G4_EVENT_SEQNO_VALUE) ||
               !gpu_g4_pm4_emit_pkt7(words, dwords,
                                     (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    return true;
}

static bool gpu_d1_build_texture_checkerboard_pm4(uint32_t *words,
                                                  unsigned int *dwords,
                                                  unsigned int *state_reg_writes,
                                                  unsigned int *vfd_reg_writes,
                                                  uint64_t color_gpuaddr,
                                                  uint64_t color_flag_gpuaddr,
                                                  uint64_t linear_gpuaddr,
                                                  uint64_t event_gpuaddr,
                                                  uint64_t vs_gpuaddr,
                                                  uint64_t fs_gpuaddr,
                                                  uint64_t vertex_gpuaddr,
                                                  uint64_t sampler_gpuaddr,
                                                  uint64_t texmem_gpuaddr) {
    uint64_t vertex_base = vertex_gpuaddr & ~0x3fULL;
    uint32_t draw_initiator = gpu_h3_draw_initiator();

    *dwords = 0;
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 0;
    }
    if (!gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_CACHE_INVALIDATE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_H3_PM4_CP_SET_MODE, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_H3_CP_SET_MODE_RESTORE_VALUE)) {
        return false;
    }
    if (!gpu_h3_append_a640_init_magic_pm4(words, dwords) ||
        !gpu_h3_append_shader_state_pm4_ex(words, dwords, vs_gpuaddr, fs_gpuaddr,
                                           GPU_D1_SP_PS_CONFIG_TEXTURED,
                                           GPU_D1_SP_PS_CNTL_0) ||
        !gpu_d1_pm4_emit_texture_state(words, dwords, sampler_gpuaddr, texmem_gpuaddr) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_D1_REG_TPL1_GFX_BORDER_COLOR_BASE,
                              0, 0) ||
        !gpu_h2_append_3d_state_pm4(words, dwords, state_reg_writes, color_gpuaddr,
                                    color_flag_gpuaddr,
                                    GPU_H3_COLOR_FORMAT, GPU_H3_COLOR_OUTPUT_MASK,
                                    false, true, GPU_H3_SP_VS_OUTPUT_REG0,
                                    GPU_H3_PS_OUTPUT_REGID)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_CNTL_0,
                              GPU_H3_VFD_CNTL_0) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H2_REG_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_2,
                              GPU_H3_VFD_CNTL_3,
                              GPU_H3_VFD_CNTL_4,
                              GPU_H3_VFD_CNTL_5,
                              GPU_H3_VFD_CNTL_6) ||
        !gpu_g4_pm4_emit_reg4(words, dwords, GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE,
                              (uint32_t)(vertex_base & 0xffffffffULL),
                              (uint32_t)(vertex_base >> 32),
                              (uint32_t)GPU_D1_VERTEX_BYTES,
                              GPU_D1_VERTEX_STRIDE) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H3_REG_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR1,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR2,
                              GPU_H3_VFD_FETCH_STEP_RATE) ||
        !gpu_h3_pm4_emit_reg3(words, dwords, GPU_H3_REG_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL1,
                              GPU_H3_VFD_DEST_CNTL2)) {
        return false;
    }
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 20;
    }
    if (!gpu_h3_pm4_emit_draw_indx_offset(words, dwords, draw_initiator, 1U,
                                          GPU_D1_VERTEX_COUNT) ||
        !gpu_h5_append_tile6_3_to_linear_a2d_pm4(words, dwords,
                                                 color_gpuaddr,
                                                 color_flag_gpuaddr,
                                                 linear_gpuaddr,
                                                 event_gpuaddr) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G3_PM4_CP_NOP, 1) ||
        !gpu_g4_pm4_push(words, dwords, 0)) {
        return false;
    }
    return true;
}

static bool gpu_d3_build_texture_video_pm4(uint32_t *words,
                                           unsigned int *dwords,
                                           unsigned int *state_reg_writes,
                                           unsigned int *vfd_reg_writes,
                                           uint64_t color_gpuaddr,
                                           uint64_t color_flag_gpuaddr,
                                           uint64_t linear_gpuaddr,
                                           uint64_t event_gpuaddr,
                                           uint64_t vs_gpuaddr,
                                           uint64_t fs_gpuaddr,
                                           uint64_t vertex_gpuaddr,
                                           uint64_t sampler_gpuaddr,
                                           uint64_t texmem_gpuaddr,
                                           uint32_t target_width,
                                           uint32_t target_height,
                                           uint32_t target_stride,
                                           uint64_t target_bytes) {
    uint64_t vertex_base = vertex_gpuaddr & ~0x3fULL;
    uint32_t draw_initiator = gpu_h3_draw_initiator();

    *dwords = 0;
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 0;
    }
    if (!gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH) ||
        !gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_CACHE_INVALIDATE) ||
        !gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_G4_PM4_CP_WAIT_FOR_IDLE, 0)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_pkt7(words, dwords, (uint8_t)GPU_H3_PM4_CP_SET_MODE, 1) ||
        !gpu_g4_pm4_push(words, dwords, GPU_H3_CP_SET_MODE_RESTORE_VALUE)) {
        return false;
    }
    if (!gpu_h3_append_a640_init_magic_pm4(words, dwords) ||
        !gpu_h3_append_shader_state_pm4_ex(words, dwords, vs_gpuaddr, fs_gpuaddr,
                                           GPU_D1_SP_PS_CONFIG_TEXTURED,
                                           GPU_D1_SP_PS_CNTL_0) ||
        !gpu_d1_pm4_emit_texture_state(words, dwords, sampler_gpuaddr, texmem_gpuaddr) ||
        !gpu_g4_pm4_emit_reg2(words, dwords, GPU_D1_REG_TPL1_GFX_BORDER_COLOR_BASE,
                              0, 0) ||
        !gpu_h2_append_3d_state_pm4_ex(words,
                                       dwords,
                                       state_reg_writes,
                                       color_gpuaddr,
                                       color_flag_gpuaddr,
                                       target_width,
                                       target_height,
                                       target_stride,
                                       target_bytes,
                                       GPU_H3_COLOR_FLAG_BUFFER_PITCH,
                                       GPU_H3_COLOR_FORMAT,
                                       GPU_H3_COLOR_OUTPUT_MASK,
                                       false,
                                       true,
                                       GPU_H3_SP_VS_OUTPUT_REG0,
                                       GPU_H3_PS_OUTPUT_REGID)) {
        return false;
    }
    if (!gpu_g4_pm4_emit_reg1(words, dwords, GPU_H2_REG_VFD_CNTL_0,
                              GPU_H3_VFD_CNTL_0) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H2_REG_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_1,
                              GPU_H3_VFD_CNTL_2,
                              GPU_H3_VFD_CNTL_3,
                              GPU_H3_VFD_CNTL_4,
                              GPU_H3_VFD_CNTL_5,
                              GPU_H3_VFD_CNTL_6) ||
        !gpu_g4_pm4_emit_reg4(words, dwords, GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE,
                              (uint32_t)(vertex_base & 0xffffffffULL),
                              (uint32_t)(vertex_base >> 32),
                              (uint32_t)GPU_D1_VERTEX_BYTES,
                              GPU_D1_VERTEX_STRIDE) ||
        !gpu_h2_pm4_emit_reg6(words, dwords, GPU_H3_REG_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_INSTR0,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR1,
                              GPU_H3_VFD_FETCH_STEP_RATE,
                              GPU_H3_VFD_FETCH_INSTR2,
                              GPU_H3_VFD_FETCH_STEP_RATE) ||
        !gpu_h3_pm4_emit_reg3(words, dwords, GPU_H3_REG_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL0,
                              GPU_H3_VFD_DEST_CNTL1,
                              GPU_H3_VFD_DEST_CNTL2)) {
        return false;
    }
    if (vfd_reg_writes != NULL) {
        *vfd_reg_writes = 20;
    }
    if (!gpu_h3_pm4_emit_draw_indx_offset(words, dwords, draw_initiator, 1U,
                                          GPU_D1_VERTEX_COUNT) ||
        !gpu_h5_append_tile6_3_to_linear_a2d_pm4_ex(words,
                                                    dwords,
                                                    color_gpuaddr,
                                                    color_flag_gpuaddr,
                                                    linear_gpuaddr,
                                                    event_gpuaddr,
                                                    target_width,
                                                    target_height,
                                                    target_stride,
                                                    GPU_H3_COLOR_FLAG_BUFFER_PITCH) ||
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

static int gpu_c1_compute_invocationid_probe_child(int write_fd) {
    static const uint32_t compute_shader[GPU_C1_SHADER_DWORDS] = {
        0x00000000U, 0x200cc001U, 0x00000000U, 0x00000500U,
        0x01674000U, 0xc0260000U, 0x00000000U, 0x03000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
    };
    struct gpu_c1_compute_invocationid_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *shader_map = MAP_FAILED;
    void *uav_map = MAP_FAILED;
    void *descriptor_map = MAP_FAILED;
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
    result.shader_alloc_rc = -1;
    result.shader_info_rc = -1;
    result.shader_mmap_rc = -1;
    result.uav_alloc_rc = -1;
    result.uav_info_rc = -1;
    result.uav_mmap_rc = -1;
    result.descriptor_alloc_rc = -1;
    result.descriptor_info_rc = -1;
    result.descriptor_mmap_rc = -1;
    result.event_alloc_rc = -1;
    result.event_info_rc = -1;
    result.uav_init_rc = -1;
    result.shader_write_rc = -1;
    result.descriptor_write_rc = -1;
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
    result.shader_munmap_rc = -1;
    result.uav_munmap_rc = -1;
    result.descriptor_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.shader_free_rc = -1;
    result.uav_free_rc = -1;
    result.descriptor_free_rc = -1;
    result.event_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_C1_WAIT_TIMEOUT_MS;
    result.shader_dwords = GPU_C1_SHADER_DWORDS;
    result.descriptor_dwords = GPU_C1_DESCRIPTOR_DWORDS;
    result.uav_words = GPU_C1_UAV_WORDS;
    result.cp_exec_cs_packet = GPU_C1_PM4_CP_EXEC_CS;
    result.first_mismatch_index = UINT_MAX;
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
        struct gpu_kgsl_gpuobj_alloc shader_alloc_arg;
        struct gpu_kgsl_gpuobj_info shader_info_arg;
        struct gpu_kgsl_gpuobj_alloc uav_alloc_arg;
        struct gpu_kgsl_gpuobj_info uav_info_arg;
        struct gpu_kgsl_gpuobj_alloc descriptor_alloc_arg;
        struct gpu_kgsl_gpuobj_info descriptor_info_arg;
        struct gpu_kgsl_gpuobj_alloc event_alloc_arg;
        struct gpu_kgsl_gpuobj_info event_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t shader_mmap_offset;
        uint64_t uav_mmap_offset;
        uint64_t descriptor_mmap_offset;

#define GPU_C1_ALLOC_INFO_MMAP(name, size_value, min_size_value) \
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

        GPU_C1_ALLOC_INFO_MMAP(cmd, GPU_C1_CMD_ALLOC_SIZE,
                               (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL);
        GPU_C1_ALLOC_INFO_MMAP(shader, GPU_C1_SHADER_ALLOC_SIZE,
                               sizeof(compute_shader));
        GPU_C1_ALLOC_INFO_MMAP(uav, GPU_C1_UAV_ALLOC_SIZE,
                               GPU_C1_UAV_BYTES);
        GPU_C1_ALLOC_INFO_MMAP(descriptor, GPU_C1_DESCRIPTOR_ALLOC_SIZE,
                               (uint64_t)GPU_C1_DESCRIPTOR_DWORDS * 4ULL);
#undef GPU_C1_ALLOC_INFO_MMAP

        memset(&event_alloc_arg, 0, sizeof(event_alloc_arg));
        event_alloc_arg.size = GPU_C1_EVENT_ALLOC_SIZE;
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

        {
            uint32_t *uav_words = (uint32_t *)uav_map;
            unsigned int index;

            for (index = 0; index < GPU_C1_UAV_WORDS; ++index) {
                uav_words[index] = GPU_C1_UAV_INIT_PATTERN | index;
            }
            __sync_synchronize();
            result.uav_init_rc = 0;
        }

        memcpy(shader_map, compute_shader, sizeof(compute_shader));
        __sync_synchronize();
        result.shader_write_rc = 0;

        gpu_c1_write_uav_descriptor((uint32_t *)descriptor_map, uav_info_arg.gpuaddr);
        __sync_synchronize();
        result.descriptor_write_rc = 0;

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            if (!gpu_c1_build_compute_pm4(cmd_words,
                                          &pm4_dwords,
                                          shader_info_arg.gpuaddr,
                                          descriptor_info_arg.gpuaddr,
                                          event_info_arg.gpuaddr)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[5];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = shader_alloc_arg.id;
            sync_objs[1].length = sizeof(compute_shader);
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = uav_alloc_arg.id;
            sync_objs[2].length = GPU_C1_UAV_BYTES;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[3].id = descriptor_alloc_arg.id;
            sync_objs[3].length = (uint64_t)GPU_C1_DESCRIPTOR_DWORDS * 4ULL;
            sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[4].id = event_alloc_arg.id;
            sync_objs[4].length = GPU_C1_EVENT_ALLOC_SIZE;
            sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.shader_sync_length = sync_objs[1].length;
            result.uav_sync_length = sync_objs[2].length;
            result.descriptor_sync_length = sync_objs[3].length;
            result.event_sync_length = sync_objs[4].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 5;
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
            struct gpu_kgsl_command_object mem_objs[5];
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
            mem_objs[1].gpuaddr = shader_info_arg.gpuaddr;
            mem_objs[1].size = shader_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = shader_alloc_arg.id;
            mem_objs[2].gpuaddr = uav_info_arg.gpuaddr;
            mem_objs[2].size = uav_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = uav_alloc_arg.id;
            mem_objs[3].gpuaddr = descriptor_info_arg.gpuaddr;
            mem_objs[3].size = descriptor_info_arg.size;
            mem_objs[3].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[3].id = descriptor_alloc_arg.id;
            mem_objs[4].gpuaddr = event_info_arg.gpuaddr;
            mem_objs[4].size = event_info_arg.size;
            mem_objs[4].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[4].id = event_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 5;
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
            wait_arg.timeout = GPU_C1_WAIT_TIMEOUT_MS;
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
            sync_obj.id = uav_alloc_arg.id;
            sync_obj.length = GPU_C1_UAV_BYTES;
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
                uint32_t *uav_words = (uint32_t *)uav_map;
                unsigned int index;

                __sync_synchronize();
                result.readback_sync_rc = 0;
                result.readback0 = uav_words[0];
                result.readback1 = uav_words[1];
                result.readback2 = uav_words[2];
                result.readback3 = uav_words[3];
                result.readback31 = uav_words[31];
                for (index = 0; index < GPU_C1_UAV_WORDS; ++index) {
                    uint32_t expected = index;
                    if (uav_words[index] == expected) {
                        result.expected_match_count += 1U;
                    } else {
                        if (result.mismatch_count == 0U) {
                            result.first_mismatch_index = index;
                            result.first_mismatch_expected = expected;
                            result.first_mismatch_value = uav_words[index];
                        }
                        result.mismatch_count += 1U;
                    }
                    if (uav_words[index] != (GPU_C1_UAV_INIT_PATTERN | index)) {
                        result.changed_count += 1U;
                    }
                }
            }
        }

        result.pass =
            (result.submit_rc == 0 &&
             result.wait_rc == 0 &&
             result.readtimestamp_rc == 0 &&
             result.readback_sync_rc == 0 &&
             result.expected_match_count == GPU_C1_UAV_WORDS &&
             result.mismatch_count == 0U) ? 1U : 0U;

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
    if (descriptor_map != MAP_FAILED) {
        result.descriptor_munmap_attempted = 1;
        errno = 0;
        result.descriptor_munmap_rc =
            munmap(descriptor_map, (size_t)result.descriptor_mmap_len) < 0 ? -1 : 0;
        result.descriptor_munmap_errno = result.descriptor_munmap_rc < 0 ? errno : 0;
    }
    if (uav_map != MAP_FAILED) {
        result.uav_munmap_attempted = 1;
        errno = 0;
        result.uav_munmap_rc =
            munmap(uav_map, (size_t)result.uav_mmap_len) < 0 ? -1 : 0;
        result.uav_munmap_errno = result.uav_munmap_rc < 0 ? errno : 0;
    }
    if (shader_map != MAP_FAILED) {
        result.shader_munmap_attempted = 1;
        errno = 0;
        result.shader_munmap_rc =
            munmap(shader_map, (size_t)result.shader_mmap_len) < 0 ? -1 : 0;
        result.shader_munmap_errno = result.shader_munmap_rc < 0 ? errno : 0;
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        result.cmd_munmap_rc =
            munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0 ? -1 : 0;
        result.cmd_munmap_errno = result.cmd_munmap_rc < 0 ? errno : 0;
    }

#define GPU_C1_FREE_FIELD(name) \
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

    GPU_C1_FREE_FIELD(event);
    GPU_C1_FREE_FIELD(descriptor);
    GPU_C1_FREE_FIELD(uav);
    GPU_C1_FREE_FIELD(shader);
    GPU_C1_FREE_FIELD(cmd);
#undef GPU_C1_FREE_FIELD

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

static uint32_t gpu_c2_pattern_expected_value(unsigned int index) {
    return index;
}

static int gpu_c2_write_snapshot_file(const uint32_t *words,
                                      uint64_t *bytes_written,
                                      int *snapshot_errno) {
    int fd;
    int close_rc;

    if (bytes_written != NULL) {
        *bytes_written = 0ULL;
    }
    if (snapshot_errno != NULL) {
        *snapshot_errno = 0;
    }
    if (words == NULL) {
        if (snapshot_errno != NULL) {
            *snapshot_errno = EINVAL;
        }
        return -1;
    }

    errno = 0;
    fd = open(GPU_C2_SNAPSHOT_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        if (snapshot_errno != NULL) {
            *snapshot_errno = errno;
        }
        return -1;
    }
    errno = 0;
    if (write_all_checked(fd, (const char *)words, (size_t)GPU_C2_UAV_BYTES) < 0) {
        if (snapshot_errno != NULL) {
            *snapshot_errno = errno;
        }
        close(fd);
        return -1;
    }
    close_rc = close(fd);
    if (close_rc < 0) {
        if (snapshot_errno != NULL) {
            *snapshot_errno = errno;
        }
        return -1;
    }
    if (bytes_written != NULL) {
        *bytes_written = GPU_C2_UAV_BYTES;
    }
    return 0;
}

static int gpu_c2_compute_pattern_probe_child(int write_fd) {
    static const uint32_t compute_shader[GPU_C2_SHADER_DWORDS] = {
        0x000000c0U, 0x200cc000U, 0x000000c0U, 0x200cc001U,
        0x00000000U, 0x00000500U, 0x01674000U, 0xc0260000U,
        0x00000000U, 0x03000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x00000000U,
    };
    struct gpu_c2_compute_pattern_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *shader_map = MAP_FAILED;
    void *uav_map = MAP_FAILED;
    void *descriptor_map = MAP_FAILED;
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
    result.shader_alloc_rc = -1;
    result.shader_info_rc = -1;
    result.shader_mmap_rc = -1;
    result.uav_alloc_rc = -1;
    result.uav_info_rc = -1;
    result.uav_mmap_rc = -1;
    result.descriptor_alloc_rc = -1;
    result.descriptor_info_rc = -1;
    result.descriptor_mmap_rc = -1;
    result.event_alloc_rc = -1;
    result.event_info_rc = -1;
    result.uav_init_rc = -1;
    result.shader_write_rc = -1;
    result.descriptor_write_rc = -1;
    result.cmd_write_rc = -1;
    result.sync_rc = -1;
    result.submit_rc = -1;
    result.timestamp_event_rc = -1;
    result.wait_rc = -1;
    result.readtimestamp_rc = -1;
    result.readback_sync_rc = -1;
    result.snapshot_write_rc = -1;
    result.fence_poll_rc = -1;
    result.fence_close_rc = -1;
    result.cmd_munmap_rc = -1;
    result.shader_munmap_rc = -1;
    result.uav_munmap_rc = -1;
    result.descriptor_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.shader_free_rc = -1;
    result.uav_free_rc = -1;
    result.descriptor_free_rc = -1;
    result.event_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_C2_WAIT_TIMEOUT_MS;
    result.shader_dwords = GPU_C2_SHADER_DWORDS;
    result.descriptor_dwords = GPU_C1_DESCRIPTOR_DWORDS;
    result.uav_words = GPU_C2_UAV_WORDS;
    result.pattern_width = GPU_C2_PATTERN_WIDTH;
    result.pattern_height = GPU_C2_PATTERN_HEIGHT;
    result.local_size_x = 1U;
    result.group_x = GPU_C2_SP_CS_GROUP_X;
    result.global_x = GPU_C2_SP_CS_GLOBAL_X;
    result.cp_exec_cs_packet = GPU_C1_PM4_CP_EXEC_CS;
    result.first_mismatch_index = UINT_MAX;
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
        struct gpu_kgsl_gpuobj_alloc shader_alloc_arg;
        struct gpu_kgsl_gpuobj_info shader_info_arg;
        struct gpu_kgsl_gpuobj_alloc uav_alloc_arg;
        struct gpu_kgsl_gpuobj_info uav_info_arg;
        struct gpu_kgsl_gpuobj_alloc descriptor_alloc_arg;
        struct gpu_kgsl_gpuobj_info descriptor_info_arg;
        struct gpu_kgsl_gpuobj_alloc event_alloc_arg;
        struct gpu_kgsl_gpuobj_info event_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t shader_mmap_offset;
        uint64_t uav_mmap_offset;
        uint64_t descriptor_mmap_offset;

#define GPU_C2_ALLOC_INFO_MMAP(name, size_value, min_size_value) \
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

        GPU_C2_ALLOC_INFO_MMAP(cmd, GPU_C2_CMD_ALLOC_SIZE,
                               (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL);
        GPU_C2_ALLOC_INFO_MMAP(shader, GPU_C2_SHADER_ALLOC_SIZE,
                               sizeof(compute_shader));
        GPU_C2_ALLOC_INFO_MMAP(uav, GPU_C2_UAV_ALLOC_SIZE,
                               GPU_C2_UAV_BYTES);
        GPU_C2_ALLOC_INFO_MMAP(descriptor, GPU_C2_DESCRIPTOR_ALLOC_SIZE,
                               (uint64_t)GPU_C1_DESCRIPTOR_DWORDS * 4ULL);
#undef GPU_C2_ALLOC_INFO_MMAP

        memset(&event_alloc_arg, 0, sizeof(event_alloc_arg));
        event_alloc_arg.size = GPU_C2_EVENT_ALLOC_SIZE;
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

        {
            uint32_t *uav_words = (uint32_t *)uav_map;
            unsigned int index;

            for (index = 0; index < GPU_C2_UAV_WORDS; ++index) {
                uav_words[index] = GPU_C2_UAV_INIT_PATTERN | index;
            }
            __sync_synchronize();
            result.uav_init_rc = 0;
        }

        memcpy(shader_map, compute_shader, sizeof(compute_shader));
        __sync_synchronize();
        result.shader_write_rc = 0;

        gpu_c2_write_uav_descriptor((uint32_t *)descriptor_map, uav_info_arg.gpuaddr);
        __sync_synchronize();
        result.descriptor_write_rc = 0;

        {
            uint32_t *cmd_words = (uint32_t *)cmd_map;
            unsigned int pm4_dwords = 0;

            memset(cmd_words, 0, (size_t)cmd_alloc_arg.mmapsize);
            if (!gpu_c2_build_compute_pm4(cmd_words,
                                          &pm4_dwords,
                                          shader_info_arg.gpuaddr,
                                          descriptor_info_arg.gpuaddr,
                                          event_info_arg.gpuaddr)) {
                result.cmd_write_rc = -1;
                goto out;
            }
            __sync_synchronize();
            result.pm4_dwords = pm4_dwords;
            result.cmd_size = (uint64_t)pm4_dwords * 4ULL;
            result.cmd_write_rc = 0;
        }

        {
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[5];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = shader_alloc_arg.id;
            sync_objs[1].length = sizeof(compute_shader);
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = uav_alloc_arg.id;
            sync_objs[2].length = GPU_C2_UAV_BYTES;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[3].id = descriptor_alloc_arg.id;
            sync_objs[3].length = (uint64_t)GPU_C1_DESCRIPTOR_DWORDS * 4ULL;
            sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[4].id = event_alloc_arg.id;
            sync_objs[4].length = GPU_C2_EVENT_ALLOC_SIZE;
            sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.shader_sync_length = sync_objs[1].length;
            result.uav_sync_length = sync_objs[2].length;
            result.descriptor_sync_length = sync_objs[3].length;
            result.event_sync_length = sync_objs[4].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 5;
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
            struct gpu_kgsl_command_object mem_objs[5];
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
            mem_objs[1].gpuaddr = shader_info_arg.gpuaddr;
            mem_objs[1].size = shader_info_arg.size;
            mem_objs[1].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[1].id = shader_alloc_arg.id;
            mem_objs[2].gpuaddr = uav_info_arg.gpuaddr;
            mem_objs[2].size = uav_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = uav_alloc_arg.id;
            mem_objs[3].gpuaddr = descriptor_info_arg.gpuaddr;
            mem_objs[3].size = descriptor_info_arg.size;
            mem_objs[3].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[3].id = descriptor_alloc_arg.id;
            mem_objs[4].gpuaddr = event_info_arg.gpuaddr;
            mem_objs[4].size = event_info_arg.size;
            mem_objs[4].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[4].id = event_alloc_arg.id;

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 5;
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
            wait_arg.context_id = result.context_id;
            wait_arg.timestamp = result.submit_timestamp;
            wait_arg.timeout = GPU_C2_WAIT_TIMEOUT_MS;
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
            struct gpu_kgsl_gpuobj_sync_obj readback_obj;
            struct gpu_kgsl_gpuobj_sync readback_sync;

            memset(&readback_obj, 0, sizeof(readback_obj));
            readback_obj.id = uav_alloc_arg.id;
            readback_obj.length = GPU_C2_UAV_BYTES;
            readback_obj.op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            memset(&readback_sync, 0, sizeof(readback_sync));
            readback_sync.objs = (uint64_t)(uintptr_t)&readback_obj;
            readback_sync.obj_len = sizeof(readback_obj);
            readback_sync.count = 1;
            result.readback_sync_length = readback_obj.length;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &readback_sync) < 0) {
                result.readback_sync_rc = -1;
                result.readback_sync_errno = errno;
            } else {
                result.readback_sync_rc = 0;
            }

            {
                uint32_t *uav_words = (uint32_t *)uav_map;
                unsigned int index;

                __sync_synchronize();
                result.readback0 = uav_words[0];
                result.readback1 = uav_words[1];
                result.readback2 = uav_words[2];
                result.readback3 = uav_words[3];
                result.readback31 = uav_words[31];
                result.readback127 = uav_words[GPU_C2_SAMPLE_127];
                result.readback128 = uav_words[GPU_C2_SAMPLE_128];
                result.readback4096 = uav_words[GPU_C2_SAMPLE_4096];
                result.readback8192 = uav_words[GPU_C2_SAMPLE_8192];
                result.readback16383 = uav_words[GPU_C2_SAMPLE_LAST];

                for (index = 0; index < GPU_C2_UAV_WORDS; ++index) {
                    uint32_t expected = gpu_c2_pattern_expected_value(index);

                    if (uav_words[index] == expected) {
                        result.expected_match_count += 1U;
                    } else {
                        if (result.first_mismatch_index == UINT_MAX) {
                            result.first_mismatch_index = index;
                            result.first_mismatch_expected = expected;
                            result.first_mismatch_value = uav_words[index];
                        }
                        result.mismatch_count += 1U;
                    }
                    if (uav_words[index] != (GPU_C2_UAV_INIT_PATTERN | index)) {
                        result.changed_count += 1U;
                    }
                }
                result.snapshot_write_rc =
                    gpu_c2_write_snapshot_file(uav_words,
                                               &result.snapshot_write_bytes,
                                               &result.snapshot_write_errno);
            }
        }

        result.pass =
            (result.submit_rc == 0 &&
             result.wait_rc == 0 &&
             result.readtimestamp_rc == 0 &&
             result.readback_sync_rc == 0 &&
             result.expected_match_count == GPU_C2_UAV_WORDS &&
             result.mismatch_count == 0U) ? 1U : 0U;

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
    if (descriptor_map != MAP_FAILED) {
        result.descriptor_munmap_attempted = 1;
        errno = 0;
        result.descriptor_munmap_rc =
            munmap(descriptor_map, (size_t)result.descriptor_mmap_len) < 0 ? -1 : 0;
        result.descriptor_munmap_errno = result.descriptor_munmap_rc < 0 ? errno : 0;
    }
    if (uav_map != MAP_FAILED) {
        result.uav_munmap_attempted = 1;
        errno = 0;
        result.uav_munmap_rc =
            munmap(uav_map, (size_t)result.uav_mmap_len) < 0 ? -1 : 0;
        result.uav_munmap_errno = result.uav_munmap_rc < 0 ? errno : 0;
    }
    if (shader_map != MAP_FAILED) {
        result.shader_munmap_attempted = 1;
        errno = 0;
        result.shader_munmap_rc =
            munmap(shader_map, (size_t)result.shader_mmap_len) < 0 ? -1 : 0;
        result.shader_munmap_errno = result.shader_munmap_rc < 0 ? errno : 0;
    }
    if (cmd_map != MAP_FAILED) {
        result.cmd_munmap_attempted = 1;
        errno = 0;
        result.cmd_munmap_rc =
            munmap(cmd_map, (size_t)result.cmd_mmap_len) < 0 ? -1 : 0;
        result.cmd_munmap_errno = result.cmd_munmap_rc < 0 ? errno : 0;
    }

#define GPU_C2_FREE_FIELD(name) \
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

    GPU_C2_FREE_FIELD(event);
    GPU_C2_FREE_FIELD(descriptor);
    GPU_C2_FREE_FIELD(uav);
    GPU_C2_FREE_FIELD(shader);
    GPU_C2_FREE_FIELD(cmd);
#undef GPU_C2_FREE_FIELD

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

static bool gpu_c1_compute_result_ok(
    const struct gpu_c1_compute_invocationid_probe_result *result) {
    return result != NULL &&
           result->pass == 1U &&
           result->cmd_free_rc == 0 &&
           result->shader_free_rc == 0 &&
           result->uav_free_rc == 0 &&
           result->descriptor_free_rc == 0 &&
           result->event_free_rc == 0 &&
           result->destroy_rc == 0 &&
           result->close_rc == 0;
}

static int gpu_c1_compute_invocationid_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_c1_compute_invocationid_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.c1.compute.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.c1.compute.version=1\r\n");
    a90_console_printf("gpu.c1.compute.scope=visible-compute-c1-invocationid-uav-readback\r\n");
    a90_console_printf("gpu.c1.compute.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.c1.compute.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.c1.compute.wait_timeout_ms=%u\r\n", GPU_C1_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.c1.compute.parent_enters_open=0\r\n");
    a90_console_printf("gpu.c1.compute.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.c1.compute.source=mesa-computerator-a6xx-kern_invocationid\r\n");
    a90_console_printf("gpu.c1.compute.label=INVOCATIONID UAV READBACK\r\n");
    a90_console_printf("gpu.c1.compute.shader_sha256=7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a\r\n");
    a90_console_printf("gpu.c1.compute.kernel_sha256=1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a\r\n");
    a90_console_printf("gpu.c1.compute.shader_dwords=%u\r\n", GPU_C1_SHADER_DWORDS);
    a90_console_printf("gpu.c1.compute.shader_instrlen=%u\r\n", GPU_C1_SHADER_INSTRLEN);
    a90_console_printf("gpu.c1.compute.shader_constlen=%u\r\n", GPU_C1_SHADER_CONSTLEN);
    a90_console_printf("gpu.c1.compute.local_size=32,1,1\r\n");
    a90_console_printf("gpu.c1.compute.uav_words=%u\r\n", GPU_C1_UAV_WORDS);
    a90_console_printf("gpu.c1.compute.uav_bytes=%llu\r\n",
                       (unsigned long long)GPU_C1_UAV_BYTES);
    a90_console_printf("gpu.c1.compute.descriptor_dwords=%u\r\n",
                       GPU_C1_DESCRIPTOR_DWORDS);
    a90_console_printf("gpu.c1.compute.cp_exec_cs=0x%x\r\n", GPU_C1_PM4_CP_EXEC_CS);
    a90_console_printf("gpu.c1.compute.cp_set_marker=0x%x\r\n",
                       GPU_C1_CP_SET_MARKER_RM6_COMPUTE);
    a90_console_printf("gpu.c1.compute.sp_cs_cntl0=0x%x\r\n", GPU_C1_SP_CS_CNTL_0);
    a90_console_printf("gpu.c1.compute.sp_cs_config=0x%x\r\n", GPU_C1_SP_CS_CONFIG);
    a90_console_printf("gpu.c1.compute.sp_cs_const_config=0x%x\r\n",
                       GPU_C1_SP_CS_CONST_CONFIG);
    a90_console_printf("gpu.c1.compute.sp_cs_const_config0=0x%x\r\n",
                       GPU_C1_SP_CS_CONST_CONFIG_0);
    a90_console_printf("gpu.c1.compute.sp_update_cntl=0x%x\r\n",
                       GPU_C1_SP_UPDATE_CNTL);
    a90_console_printf("gpu.c1.compute.hlsq_cs_ctrl_reg1=0x%x\r\n",
                       GPU_C1_HLSQ_CS_CTRL_REG1);
    a90_console_printf("gpu.c1.compute.ndrange0=0x%x\r\n", GPU_C1_SP_CS_NDRANGE_0);
    a90_console_printf("gpu.c1.compute.expected_readback=0..31\r\n");
    a90_console_printf("gpu.c1.compute.power_write_attempted=0\r\n");
    a90_console_printf("gpu.c1.compute.proprietary_blob_attempted=0\r\n");
    a90_console_printf("gpu.c1.compute.kms_blit_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.c1.compute.materialize_requested=1\r\n");
        a90_console_printf("gpu.c1.compute.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.c1.compute.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.c1.compute.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.c1.compute.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_c1_compute_invocationid_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.c1.compute.child_pid=%ld\r\n", (long)pid);

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

    if (got_result && gpu_c1_compute_result_ok(&result)) {
        a90_console_printf("gpu.c1.compute.result=invocationid-uav-readback-pass\r\n");
    } else if (got_result) {
        a90_console_printf("gpu.c1.compute.result=invocationid-uav-readback-failed\r\n");
    } else if (timed_out) {
        a90_console_printf("gpu.c1.compute.result=timeout\r\n");
    } else {
        a90_console_printf("gpu.c1.compute.result=no-result\r\n");
    }
    a90_console_printf("gpu.c1.compute.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.c1.compute.child_killed=%d\r\n",
                       child_killed ? 1 : 0);
    a90_console_printf("gpu.c1.compute.child_reaped=%d\r\n",
                       child_reaped ? 1 : 0);
    a90_console_printf("gpu.c1.compute.child_status=0x%x\r\n", child_status);
    a90_console_printf("gpu.c1.compute.child_got_result=%d\r\n",
                       got_result ? 1 : 0);
    if (got_result) {
        a90_console_printf("gpu.c1.compute.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.c1.compute.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.c1.compute.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.c1.compute.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.c1.compute.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.c1.compute.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.c1.compute.shader_alloc_rc=%d\r\n",
                           result.shader_alloc_rc);
        a90_console_printf("gpu.c1.compute.uav_alloc_rc=%d\r\n", result.uav_alloc_rc);
        a90_console_printf("gpu.c1.compute.descriptor_alloc_rc=%d\r\n",
                           result.descriptor_alloc_rc);
        a90_console_printf("gpu.c1.compute.event_alloc_rc=%d\r\n",
                           result.event_alloc_rc);
        a90_console_printf("gpu.c1.compute.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.c1.compute.shader_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.shader_info_gpuaddr);
        a90_console_printf("gpu.c1.compute.uav_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.uav_info_gpuaddr);
        a90_console_printf("gpu.c1.compute.descriptor_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.descriptor_info_gpuaddr);
        a90_console_printf("gpu.c1.compute.event_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.event_info_gpuaddr);
        a90_console_printf("gpu.c1.compute.uav_init_rc=%d\r\n", result.uav_init_rc);
        a90_console_printf("gpu.c1.compute.shader_write_rc=%d\r\n",
                           result.shader_write_rc);
        a90_console_printf("gpu.c1.compute.descriptor_write_rc=%d\r\n",
                           result.descriptor_write_rc);
        a90_console_printf("gpu.c1.compute.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.c1.compute.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.c1.compute.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.c1.compute.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.c1.compute.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.c1.compute.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.c1.compute.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.c1.compute.submit_timestamp=%u\r\n",
                           result.submit_timestamp);
        a90_console_printf("gpu.c1.compute.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.c1.compute.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.c1.compute.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.c1.compute.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.c1.compute.readtimestamp_rc=%d\r\n",
                           result.readtimestamp_rc);
        a90_console_printf("gpu.c1.compute.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.c1.compute.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.c1.compute.readback_sync_errno=%d\r\n",
                           result.readback_sync_errno);
        a90_console_printf("gpu.c1.compute.readback0=%u\r\n", result.readback0);
        a90_console_printf("gpu.c1.compute.readback1=%u\r\n", result.readback1);
        a90_console_printf("gpu.c1.compute.readback2=%u\r\n", result.readback2);
        a90_console_printf("gpu.c1.compute.readback3=%u\r\n", result.readback3);
        a90_console_printf("gpu.c1.compute.readback31=%u\r\n", result.readback31);
        a90_console_printf("gpu.c1.compute.changed_count=%u\r\n",
                           result.changed_count);
        a90_console_printf("gpu.c1.compute.expected_match_count=%u\r\n",
                           result.expected_match_count);
        a90_console_printf("gpu.c1.compute.mismatch_count=%u\r\n",
                           result.mismatch_count);
        a90_console_printf("gpu.c1.compute.first_mismatch_index=%u\r\n",
                           result.first_mismatch_index);
        a90_console_printf("gpu.c1.compute.first_mismatch_expected=%u\r\n",
                           result.first_mismatch_expected);
        a90_console_printf("gpu.c1.compute.first_mismatch_value=%u\r\n",
                           result.first_mismatch_value);
        a90_console_printf("gpu.c1.compute.pass=%u\r\n", result.pass);
        a90_console_printf("gpu.c1.compute.fence_poll_rc=%d\r\n",
                           result.fence_poll_rc);
        a90_console_printf("gpu.c1.compute.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.c1.compute.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.c1.compute.shader_free_rc=%d\r\n",
                           result.shader_free_rc);
        a90_console_printf("gpu.c1.compute.uav_free_rc=%d\r\n", result.uav_free_rc);
        a90_console_printf("gpu.c1.compute.descriptor_free_rc=%d\r\n",
                           result.descriptor_free_rc);
        a90_console_printf("gpu.c1.compute.event_free_rc=%d\r\n",
                           result.event_free_rc);
        a90_console_printf("gpu.c1.compute.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.c1.compute.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.c1.compute.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    if (timed_out) {
        return -ETIMEDOUT;
    }
    if (!got_result || !gpu_c1_compute_result_ok(&result)) {
        return -EIO;
    }
    return 0;
}

static bool gpu_c2_compute_pattern_result_ok(
    const struct gpu_c2_compute_pattern_probe_result *result) {
    return result != NULL &&
           result->pass == 1U &&
           result->cmd_free_rc == 0 &&
           result->shader_free_rc == 0 &&
           result->uav_free_rc == 0 &&
           result->descriptor_free_rc == 0 &&
           result->event_free_rc == 0 &&
           result->destroy_rc == 0 &&
           result->close_rc == 0;
}

static int gpu_c2_compute_pattern_probe(int timeout_ms, bool materialize_devnode) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_c2_compute_pattern_probe_result result;

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.c2.compute.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.c2.compute.version=1\r\n");
    a90_console_printf("gpu.c2.compute.scope=visible-compute-c2-128x128-workgroup-id-pattern\r\n");
    a90_console_printf("gpu.c2.compute.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.c2.compute.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.c2.compute.wait_timeout_ms=%u\r\n", GPU_C2_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.c2.compute.parent_enters_open=0\r\n");
    a90_console_printf("gpu.c2.compute.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.c2.compute.source=mesa-ir3-assembler-fd640-workgroup-id-pattern\r\n");
    a90_console_printf("gpu.c2.compute.label=128X128 GPU COMPUTE PATTERN\r\n");
    a90_console_printf("gpu.c2.compute.shader_sha256=9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1\r\n");
    a90_console_printf("gpu.c2.compute.asm_sha256=1f7f223c66a97975e416dce96b0a960933b7fa21b7bf4c6d380b3eb63e31b0d6\r\n");
    a90_console_printf("gpu.c2.compute.shader_dwords=%u\r\n", GPU_C2_SHADER_DWORDS);
    a90_console_printf("gpu.c2.compute.shader_instrlen=%u\r\n", GPU_C2_SHADER_INSTRLEN);
    a90_console_printf("gpu.c2.compute.shader_constlen=%u\r\n", GPU_C2_SHADER_CONSTLEN);
    a90_console_printf("gpu.c2.compute.local_size=1,1,1\r\n");
    a90_console_printf("gpu.c2.compute.pattern=workgroup-id-u32-128x128\r\n");
    a90_console_printf("gpu.c2.compute.pattern_width=%u\r\n", GPU_C2_PATTERN_WIDTH);
    a90_console_printf("gpu.c2.compute.pattern_height=%u\r\n", GPU_C2_PATTERN_HEIGHT);
    a90_console_printf("gpu.c2.compute.uav_words=%u\r\n", GPU_C2_UAV_WORDS);
    a90_console_printf("gpu.c2.compute.uav_bytes=%llu\r\n",
                       (unsigned long long)GPU_C2_UAV_BYTES);
    a90_console_printf("gpu.c2.compute.descriptor_dwords=%u\r\n",
                       GPU_C1_DESCRIPTOR_DWORDS);
    a90_console_printf("gpu.c2.compute.cp_exec_cs=0x%x\r\n", GPU_C1_PM4_CP_EXEC_CS);
    a90_console_printf("gpu.c2.compute.cp_set_marker=0x%x\r\n",
                       GPU_C1_CP_SET_MARKER_RM6_COMPUTE);
    a90_console_printf("gpu.c2.compute.sp_cs_cntl0=0x%x\r\n", GPU_C1_SP_CS_CNTL_0);
    a90_console_printf("gpu.c2.compute.sp_cs_config=0x%x\r\n", GPU_C1_SP_CS_CONFIG);
    a90_console_printf("gpu.c2.compute.sp_cs_const_config=0x%x\r\n",
                       GPU_C1_SP_CS_CONST_CONFIG);
    a90_console_printf("gpu.c2.compute.sp_cs_const_config0=0x%x\r\n",
                       GPU_C1_SP_CS_CONST_CONFIG_0);
    a90_console_printf("gpu.c2.compute.sp_update_cntl=0x%x\r\n",
                       GPU_C1_SP_UPDATE_CNTL);
    a90_console_printf("gpu.c2.compute.hlsq_cs_ctrl_reg1=0x%x\r\n",
                       GPU_C1_HLSQ_CS_CTRL_REG1);
    a90_console_printf("gpu.c2.compute.ndrange0=0x%x\r\n", GPU_C2_SP_CS_NDRANGE_0);
    a90_console_printf("gpu.c2.compute.global_size=%u,1,1\r\n", GPU_C2_SP_CS_GLOBAL_X);
    a90_console_printf("gpu.c2.compute.group_count=%u,1,1\r\n", GPU_C2_SP_CS_GROUP_X);
    a90_console_printf("gpu.c2.compute.expected_samples=0,1,2,3,31,127,128,4096,8192,16383\r\n");
    a90_console_printf("gpu.c2.compute.power_write_attempted=0\r\n");
    a90_console_printf("gpu.c2.compute.proprietary_blob_attempted=0\r\n");
    a90_console_printf("gpu.c2.compute.kms_blit_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.c2.compute.materialize_requested=1\r\n");
        a90_console_printf("gpu.c2.compute.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.c2.compute.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.c2.compute.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.c2.compute.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_c2_compute_pattern_probe_child(pipefd[1]);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.c2.compute.child_pid=%ld\r\n", (long)pid);

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

    if (got_result && gpu_c2_compute_pattern_result_ok(&result)) {
        a90_console_printf("gpu.c2.compute.result=pattern-readback-pass\r\n");
    } else if (got_result) {
        a90_console_printf("gpu.c2.compute.result=pattern-readback-failed\r\n");
    } else if (timed_out) {
        a90_console_printf("gpu.c2.compute.result=timeout\r\n");
    } else {
        a90_console_printf("gpu.c2.compute.result=no-result\r\n");
    }
    a90_console_printf("gpu.c2.compute.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.c2.compute.child_killed=%d\r\n",
                       child_killed ? 1 : 0);
    a90_console_printf("gpu.c2.compute.child_reaped=%d\r\n",
                       child_reaped ? 1 : 0);
    a90_console_printf("gpu.c2.compute.child_status=0x%x\r\n", child_status);
    a90_console_printf("gpu.c2.compute.child_got_result=%d\r\n",
                       got_result ? 1 : 0);
    if (got_result) {
        a90_console_printf("gpu.c2.compute.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.c2.compute.open_errno=%d\r\n", result.open_errno);
        a90_console_printf("gpu.c2.compute.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.c2.compute.create_errno=%d\r\n", result.create_errno);
        a90_console_printf("gpu.c2.compute.context_id=%u\r\n", result.context_id);
        a90_console_printf("gpu.c2.compute.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.c2.compute.shader_alloc_rc=%d\r\n",
                           result.shader_alloc_rc);
        a90_console_printf("gpu.c2.compute.uav_alloc_rc=%d\r\n", result.uav_alloc_rc);
        a90_console_printf("gpu.c2.compute.descriptor_alloc_rc=%d\r\n",
                           result.descriptor_alloc_rc);
        a90_console_printf("gpu.c2.compute.event_alloc_rc=%d\r\n",
                           result.event_alloc_rc);
        a90_console_printf("gpu.c2.compute.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.c2.compute.shader_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.shader_info_gpuaddr);
        a90_console_printf("gpu.c2.compute.uav_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.uav_info_gpuaddr);
        a90_console_printf("gpu.c2.compute.descriptor_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.descriptor_info_gpuaddr);
        a90_console_printf("gpu.c2.compute.event_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.event_info_gpuaddr);
        a90_console_printf("gpu.c2.compute.uav_init_rc=%d\r\n", result.uav_init_rc);
        a90_console_printf("gpu.c2.compute.shader_write_rc=%d\r\n",
                           result.shader_write_rc);
        a90_console_printf("gpu.c2.compute.descriptor_write_rc=%d\r\n",
                           result.descriptor_write_rc);
        a90_console_printf("gpu.c2.compute.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.c2.compute.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.c2.compute.cmd_size=%llu\r\n",
                           (unsigned long long)result.cmd_size);
        a90_console_printf("gpu.c2.compute.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.c2.compute.sync_errno=%d\r\n", result.sync_errno);
        a90_console_printf("gpu.c2.compute.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.c2.compute.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.c2.compute.submit_timestamp=%u\r\n",
                           result.submit_timestamp);
        a90_console_printf("gpu.c2.compute.timestamp_event_rc=%d\r\n",
                           result.timestamp_event_rc);
        a90_console_printf("gpu.c2.compute.fence_fd=%d\r\n", result.fence_fd);
        a90_console_printf("gpu.c2.compute.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.c2.compute.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.c2.compute.readtimestamp_rc=%d\r\n",
                           result.readtimestamp_rc);
        a90_console_printf("gpu.c2.compute.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.c2.compute.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.c2.compute.readback_sync_errno=%d\r\n",
                           result.readback_sync_errno);
        a90_console_printf("gpu.c2.compute.snapshot_path=%s\r\n",
                           GPU_C2_SNAPSHOT_PATH);
        a90_console_printf("gpu.c2.compute.snapshot_write_rc=%d\r\n",
                           result.snapshot_write_rc);
        a90_console_printf("gpu.c2.compute.snapshot_write_errno=%d\r\n",
                           result.snapshot_write_errno);
        a90_console_printf("gpu.c2.compute.snapshot_write_bytes=%llu\r\n",
                           (unsigned long long)result.snapshot_write_bytes);
        a90_console_printf("gpu.c2.compute.readback0=%u\r\n", result.readback0);
        a90_console_printf("gpu.c2.compute.readback1=%u\r\n", result.readback1);
        a90_console_printf("gpu.c2.compute.readback2=%u\r\n", result.readback2);
        a90_console_printf("gpu.c2.compute.readback3=%u\r\n", result.readback3);
        a90_console_printf("gpu.c2.compute.readback31=%u\r\n", result.readback31);
        a90_console_printf("gpu.c2.compute.readback127=%u\r\n", result.readback127);
        a90_console_printf("gpu.c2.compute.readback128=%u\r\n", result.readback128);
        a90_console_printf("gpu.c2.compute.readback4096=%u\r\n",
                           result.readback4096);
        a90_console_printf("gpu.c2.compute.readback8192=%u\r\n",
                           result.readback8192);
        a90_console_printf("gpu.c2.compute.readback16383=%u\r\n",
                           result.readback16383);
        a90_console_printf("gpu.c2.compute.changed_count=%u\r\n",
                           result.changed_count);
        a90_console_printf("gpu.c2.compute.expected_match_count=%u\r\n",
                           result.expected_match_count);
        a90_console_printf("gpu.c2.compute.mismatch_count=%u\r\n",
                           result.mismatch_count);
        a90_console_printf("gpu.c2.compute.first_mismatch_index=%u\r\n",
                           result.first_mismatch_index);
        a90_console_printf("gpu.c2.compute.first_mismatch_expected=%u\r\n",
                           result.first_mismatch_expected);
        a90_console_printf("gpu.c2.compute.first_mismatch_value=%u\r\n",
                           result.first_mismatch_value);
        a90_console_printf("gpu.c2.compute.pass=%u\r\n", result.pass);
        a90_console_printf("gpu.c2.compute.fence_poll_rc=%d\r\n",
                           result.fence_poll_rc);
        a90_console_printf("gpu.c2.compute.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.c2.compute.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.c2.compute.shader_free_rc=%d\r\n",
                           result.shader_free_rc);
        a90_console_printf("gpu.c2.compute.uav_free_rc=%d\r\n", result.uav_free_rc);
        a90_console_printf("gpu.c2.compute.descriptor_free_rc=%d\r\n",
                           result.descriptor_free_rc);
        a90_console_printf("gpu.c2.compute.event_free_rc=%d\r\n",
                           result.event_free_rc);
        a90_console_printf("gpu.c2.compute.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.c2.compute.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.c2.compute.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    if (timed_out) {
        return -ETIMEDOUT;
    }
    if (!got_result || !gpu_c2_compute_pattern_result_ok(&result)) {
        return -EIO;
    }
    return 0;
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
           result->color_flag_free_rc == 0 &&
           result->event_free_rc == 0 &&
           result->vs_free_rc == 0 &&
           result->fs_free_rc == 0 &&
           result->vertex_free_rc == 0 &&
           result->destroy_rc == 0;
}

static int gpu_h3_draw_envelope_probe_child(int write_fd,
                                            bool include_snapshot,
                                            bool linearize_snapshot) {
    static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS] = {
        GPU_H3_IR3_MOV_F32F32_R2X_R1X_LO, GPU_H3_IR3_MOV_F32F32_R2X_R1X_HI,
        GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_LO, GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_HI,
        GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_LO, GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_HI,
        GPU_H3_IR3_MOV_F32F32_R2W_R1W_LO, GPU_H3_IR3_MOV_F32F32_R2W_R1W_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t fs_shader[GPU_H3_FS_SHADER_DWORDS] = {
        GPU_H3_IR3_BARY_F_R0Z_IJ0_LO, GPU_H3_IR3_BARY_F_R0Z_IJ0_HI,
        GPU_H3_IR3_BARY_F_R0W_IJ1_LO, GPU_H3_IR3_BARY_F_R0W_IJ1_HI,
        GPU_H3_IR3_BARY_F_R1X_IJ2_LO, GPU_H3_IR3_BARY_F_R1X_IJ2_HI,
        GPU_H3_IR3_BARY_F_R1Y_IJ3_EI_LO, GPU_H3_IR3_BARY_F_R1Y_IJ3_EI_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t vertex_words[GPU_H3_VERTEX_DWORDS] = {
        0x3f800000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0xbf400000U, 0xbf400000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x00000000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x3f400000U, 0xbf400000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x00000000U, 0x00000000U, 0x3f800000U, 0x3f800000U,
        0x00000000U, 0x3f400000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
    };
    struct gpu_h3_draw_envelope_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *color_map = MAP_FAILED;
    void *color_flag_map = MAP_FAILED;
    void *linear_map = MAP_FAILED;
    void *vs_map = MAP_FAILED;
    void *fs_map = MAP_FAILED;
    void *vertex_map = MAP_FAILED;
    int fd = -1;
    int fence_fd = -1;
    uint32_t snapshot_words[GPU_H5_H3_SNAPSHOT_WORDS];
    bool snapshot_valid = false;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    memset(snapshot_words, 0, sizeof(snapshot_words));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.color_alloc_rc = -1;
    result.color_info_rc = -1;
    result.color_mmap_rc = -1;
    result.color_flag_alloc_rc = -1;
    result.color_flag_info_rc = -1;
    result.color_flag_mmap_rc = -1;
    result.linear_alloc_rc = -1;
    result.linear_info_rc = -1;
    result.linear_mmap_rc = -1;
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
    result.sampler_alloc_rc = -1;
    result.sampler_info_rc = -1;
    result.sampler_mmap_rc = -1;
    result.texmem_alloc_rc = -1;
    result.texmem_info_rc = -1;
    result.texmem_mmap_rc = -1;
    result.texture_alloc_rc = -1;
    result.texture_info_rc = -1;
    result.texture_mmap_rc = -1;
    result.color_init_rc = -1;
    result.shader_write_rc = -1;
    result.vertex_write_rc = -1;
    result.texture_write_rc = -1;
    result.texture_desc_write_rc = -1;
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
    result.color_flag_munmap_rc = -1;
    result.linear_munmap_rc = -1;
    result.vs_munmap_rc = -1;
    result.fs_munmap_rc = -1;
    result.vertex_munmap_rc = -1;
    result.sampler_munmap_rc = -1;
    result.texmem_munmap_rc = -1;
    result.texture_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.color_free_rc = -1;
    result.color_flag_free_rc = -1;
    result.linear_free_rc = -1;
    result.event_free_rc = -1;
    result.vs_free_rc = -1;
    result.fs_free_rc = -1;
    result.vertex_free_rc = -1;
    result.sampler_free_rc = -1;
    result.texmem_free_rc = -1;
    result.texture_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_H3_WAIT_TIMEOUT_MS;
    result.color_width = GPU_H2_COLOR_WIDTH;
    result.color_height = GPU_H2_COLOR_HEIGHT;
    result.color_stride = GPU_H2_COLOR_STRIDE;
    result.color_format = GPU_H3_COLOR_FORMAT;
    result.color_flag_pitch = GPU_H3_COLOR_FLAG_BUFFER_PITCH;
    result.color_bytes = GPU_H2_COLOR_ALLOC_SIZE;
    result.vertex_stride = GPU_H3_VERTEX_STRIDE;
    result.vertex_bytes = (unsigned int)GPU_H3_VERTEX_BYTES;
    result.vertex_count = GPU_H3_VERTEX_COUNT;
    result.vertex_format = GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT;
    result.texture_first_mismatch_index = UINT_MAX;
    result.cp_draw_packet = GPU_H3_PM4_CP_DRAW_INDX_OFFSET;
    result.draw_initiator = gpu_h3_draw_initiator();
    result.num_instances = 1U;
    result.num_indices = GPU_H3_VERTEX_COUNT;
    result.draw_attempted = 1;
    result.shader_execution_attempted = 1;
    result.kms_blit_attempted = 0;
    result.linear_blit_attempted = linearize_snapshot ? 1U : 0U;
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
        struct gpu_kgsl_gpuobj_alloc color_flag_alloc_arg;
        struct gpu_kgsl_gpuobj_info color_flag_info_arg;
        struct gpu_kgsl_gpuobj_alloc linear_alloc_arg;
        struct gpu_kgsl_gpuobj_info linear_info_arg;
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
        uint64_t color_flag_mmap_offset;
        uint64_t linear_mmap_offset;
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
        GPU_H3_ALLOC_INFO_MMAP(color_flag, GPU_H3_COLOR_FLAG_ALLOC_SIZE,
                               GPU_H3_COLOR_FLAG_ALLOC_SIZE);
        if (linearize_snapshot) {
            GPU_H3_ALLOC_INFO_MMAP(linear, GPU_H2_COLOR_ALLOC_SIZE,
                                   GPU_H2_COLOR_ALLOC_SIZE);
        }

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
            uint32_t *color_flag_words = (uint32_t *)color_flag_map;
            uint32_t *linear_words = (uint32_t *)linear_map;
            unsigned int index;

            for (index = 0; index < (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL); ++index) {
                color_words[index] = GPU_H2_CLEAR_PATTERN;
            }
            if (linear_map != MAP_FAILED) {
                for (index = 0; index < (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL); ++index) {
                    linear_words[index] = GPU_H5_LINEAR_CLEAR_PATTERN;
                }
            }
            for (index = 0; index < (unsigned int)(GPU_H3_COLOR_FLAG_ALLOC_SIZE / 4ULL); ++index) {
                color_flag_words[index] = 0;
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
                                                color_flag_info_arg.gpuaddr,
                                                linearize_snapshot ?
                                                linear_info_arg.gpuaddr : 0ULL,
                                                event_info_arg.gpuaddr,
                                                vs_info_arg.gpuaddr,
                                                fs_info_arg.gpuaddr,
                                                vertex_info_arg.gpuaddr,
                                                linearize_snapshot)) {
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
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[8];
            struct gpu_kgsl_gpuobj_sync sync_arg;
            unsigned int sync_count = 7U;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_alloc_arg.id;
            sync_objs[1].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = color_flag_alloc_arg.id;
            sync_objs[2].length = GPU_H3_COLOR_FLAG_ALLOC_SIZE;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[3].id = event_alloc_arg.id;
            sync_objs[3].length = GPU_H3_EVENT_ALLOC_SIZE;
            sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[4].id = vs_alloc_arg.id;
            sync_objs[4].length = sizeof(vs_shader);
            sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[5].id = fs_alloc_arg.id;
            sync_objs[5].length = sizeof(fs_shader);
            sync_objs[5].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[6].id = vertex_alloc_arg.id;
            sync_objs[6].length = GPU_H3_VERTEX_BYTES;
            sync_objs[6].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            if (linearize_snapshot) {
                sync_objs[7].id = linear_alloc_arg.id;
                sync_objs[7].length = GPU_H2_COLOR_ALLOC_SIZE;
                sync_objs[7].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
                result.linear_sync_length = sync_objs[7].length;
                sync_count = 8U;
            }
            result.cmd_sync_length = sync_objs[0].length;
            result.color_sync_length = sync_objs[1].length;
            result.color_flag_sync_length = sync_objs[2].length;
            result.event_sync_length = sync_objs[3].length;
            result.vs_sync_length = sync_objs[4].length;
            result.fs_sync_length = sync_objs[5].length;
            result.vertex_sync_length = sync_objs[6].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = sync_count;
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
            struct gpu_kgsl_command_object mem_objs[8];
            struct gpu_kgsl_gpu_command command_arg;
            unsigned int mem_count = 7U;

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
            mem_objs[2].gpuaddr = color_flag_info_arg.gpuaddr;
            mem_objs[2].size = color_flag_info_arg.size;
            mem_objs[2].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[2].id = color_flag_alloc_arg.id;
            mem_objs[3].gpuaddr = event_info_arg.gpuaddr;
            mem_objs[3].size = event_info_arg.size;
            mem_objs[3].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[3].id = event_alloc_arg.id;
            mem_objs[4].gpuaddr = vs_info_arg.gpuaddr;
            mem_objs[4].size = vs_info_arg.size;
            mem_objs[4].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[4].id = vs_alloc_arg.id;
            mem_objs[5].gpuaddr = fs_info_arg.gpuaddr;
            mem_objs[5].size = fs_info_arg.size;
            mem_objs[5].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[5].id = fs_alloc_arg.id;
            mem_objs[6].gpuaddr = vertex_info_arg.gpuaddr;
            mem_objs[6].size = vertex_info_arg.size;
            mem_objs[6].flags = GPU_KGSL_OBJLIST_MEMOBJ;
            mem_objs[6].id = vertex_alloc_arg.id;
            if (linearize_snapshot) {
                mem_objs[7].gpuaddr = linear_info_arg.gpuaddr;
                mem_objs[7].size = linear_info_arg.size;
                mem_objs[7].flags = GPU_KGSL_OBJLIST_MEMOBJ;
                mem_objs[7].id = linear_alloc_arg.id;
                mem_count = 8U;
            }

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = mem_count;
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
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[3];
            struct gpu_kgsl_gpuobj_sync sync_arg;
            unsigned int sync_count = 2U;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = color_alloc_arg.id;
            sync_objs[0].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_flag_alloc_arg.id;
            sync_objs[1].length = GPU_H3_COLOR_FLAG_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.readback_sync_length = sync_objs[0].length + sync_objs[1].length;
            if (linearize_snapshot) {
                sync_objs[2].id = linear_alloc_arg.id;
                sync_objs[2].length = GPU_H2_COLOR_ALLOC_SIZE;
                sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
                result.readback_sync_length += sync_objs[2].length;
                sync_count = 3U;
            }
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = sync_count;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.readback_sync_rc = -1;
                result.readback_sync_errno = errno;
            } else {
                uint32_t *color_words = (uint32_t *)color_map;
                uint32_t *color_flag_words = (uint32_t *)color_flag_map;
                uint32_t *linear_words = (uint32_t *)linear_map;
                unsigned int word_count = (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL);
                unsigned int flag_word_count =
                    (unsigned int)(GPU_H3_COLOR_FLAG_ALLOC_SIZE / 4ULL);
                unsigned int index;
                unsigned int center_index =
                    (GPU_H2_COLOR_HEIGHT / 2U) * GPU_H2_COLOR_WIDTH +
                    (GPU_H2_COLOR_WIDTH / 2U);
                unsigned int corner_tr_index = GPU_H2_COLOR_WIDTH - 1U;
                unsigned int corner_bl_index =
                    (GPU_H2_COLOR_HEIGHT - 1U) * GPU_H2_COLOR_WIDTH;
                unsigned int corner_br_index =
                    (GPU_H2_COLOR_HEIGHT * GPU_H2_COLOR_WIDTH) - 1U;

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
                result.color_flag0 = color_flag_words[0];
                result.color_flag_first_changed_index = UINT_MAX;
                for (index = 0; index < flag_word_count; ++index) {
                    if (color_flag_words[index] != 0) {
                        if (result.color_flag_changed_count == 0) {
                            result.color_flag_first_changed_index = index;
                            result.color_flag_first_changed_value = color_flag_words[index];
                        }
                        result.color_flag_changed_count += 1U;
                    }
                }
                result.linear_readback_first_changed_index = UINT_MAX;
                result.linear_readback_first_nonzero_index = UINT_MAX;
                if (linearize_snapshot && linear_map != MAP_FAILED) {
                    result.linear_readback0 = linear_words[0];
                    result.linear_readback_center = linear_words[center_index];
                    result.linear_readback_corner_tr = linear_words[corner_tr_index];
                    result.linear_readback_corner_bl = linear_words[corner_bl_index];
                    result.linear_readback_corner_br = linear_words[corner_br_index];
                    result.linear_center_nonzero =
                        result.linear_readback_center != GPU_H5_LINEAR_CLEAR_PATTERN ? 1U : 0U;
                    result.linear_exterior_corners_zero =
                        (result.linear_readback0 == GPU_H5_LINEAR_CLEAR_PATTERN &&
                         result.linear_readback_corner_tr == GPU_H5_LINEAR_CLEAR_PATTERN &&
                         result.linear_readback_corner_bl == GPU_H5_LINEAR_CLEAR_PATTERN &&
                         result.linear_readback_corner_br == GPU_H5_LINEAR_CLEAR_PATTERN) ? 1U : 0U;
                    for (index = 0; index < word_count; ++index) {
                        if (linear_words[index] != GPU_H5_LINEAR_CLEAR_PATTERN) {
                            if (result.linear_readback_changed_count == 0) {
                                result.linear_readback_first_changed_index = index;
                                result.linear_readback_first_changed_value = linear_words[index];
                            }
                            result.linear_readback_changed_count += 1U;
                        }
                        if (linear_words[index] != 0U) {
                            if (result.linear_readback_nonzero_count == 0) {
                                result.linear_readback_first_nonzero_index = index;
                                result.linear_readback_first_nonzero_value = linear_words[index];
                            }
                            result.linear_readback_nonzero_count += 1U;
                        }
                    }
                }
                if (include_snapshot) {
                    if (linearize_snapshot && linear_map != MAP_FAILED) {
                        memcpy(snapshot_words, linear_words, sizeof(snapshot_words));
                    } else {
                        memcpy(snapshot_words, color_words, sizeof(snapshot_words));
                    }
                    snapshot_valid = true;
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
    if (color_flag_map != MAP_FAILED) {
        result.color_flag_munmap_attempted = 1;
        errno = 0;
        result.color_flag_munmap_rc =
            munmap(color_flag_map, (size_t)result.color_flag_mmap_len) < 0 ? -1 : 0;
        result.color_flag_munmap_errno = result.color_flag_munmap_rc < 0 ? errno : 0;
    }
    if (linear_map != MAP_FAILED) {
        result.linear_munmap_attempted = 1;
        errno = 0;
        result.linear_munmap_rc =
            munmap(linear_map, (size_t)result.linear_mmap_len) < 0 ? -1 : 0;
        result.linear_munmap_errno = result.linear_munmap_rc < 0 ? errno : 0;
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
    GPU_H3_FREE_FIELD(linear);
    GPU_H3_FREE_FIELD(color_flag);
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
    if (include_snapshot) {
        struct gpu_h3_draw_snapshot_payload payload;

        memset(&payload, 0, sizeof(payload));
        payload.result = result;
        if (snapshot_valid) {
            memcpy(payload.color_words, snapshot_words, sizeof(payload.color_words));
        }
        (void)write_all_checked(write_fd, (const char *)&payload, sizeof(payload));
    } else {
        (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    }
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
    a90_console_printf("gpu.h3.draw.scope=first-triangle-h3-blend-output-state-vfd-vs-contract-replay-a640-nonzero-init-magic-block-flag-mrt-cffdump-color-target-varying-ij-vpc-linkage-clip-guardband-su-rasterizer-a6xx-output-routing-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl\r\n");
    a90_console_printf("gpu.h3.draw.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.h3.draw.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.h3.draw.wait_timeout_ms=%u\r\n", GPU_H3_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.h3.draw.parent_enters_open=0\r\n");
    a90_console_printf("gpu.h3.draw.parent_enters_ioctl=0\r\n");
    a90_console_printf("gpu.h3.draw.source=mesa-freedreno-a6xx-fd6-draw-plus-vfd-fetch-dest\r\n");
    a90_console_printf("gpu.h3.draw.shader_payload=verified-ir3-vs-r1xyzw-to-r2-position-preserve-r0-varying-and-cffdump-bary-fs\r\n");
    a90_console_printf("gpu.h3.draw.shader_payload_source=constant-free-cffdump-shaped-vfd-vs-contract-plus-a640-cffdump-bary-f-frag-shader\r\n");
    a90_console_printf("gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map\r\n");
    a90_console_printf("gpu.h3.draw.vs_shader_dwords=%u\r\n", GPU_H3_VS_SHADER_DWORDS);
    a90_console_printf("gpu.h3.draw.fs_shader_dwords=%u\r\n", GPU_H3_FS_SHADER_DWORDS);
    a90_console_printf("gpu.h3.draw.vs_shader_instr_count=%u\r\n", GPU_H3_VS_SHADER_INSTR_COUNT);
    a90_console_printf("gpu.h3.draw.fs_shader_instr_count=%u\r\n", GPU_H3_FS_SHADER_INSTR_COUNT);
    a90_console_printf("gpu.h3.draw.vs_shader_instrlen=%u\r\n", GPU_H3_VS_SHADER_INSTRLEN);
    a90_console_printf("gpu.h3.draw.fs_shader_instrlen=%u\r\n", GPU_H3_FS_SHADER_INSTRLEN);
    a90_console_printf("gpu.h3.draw.ir3_instr_align=%u\r\n", GPU_H3_IR3_INSTR_ALIGN);
    a90_console_printf("gpu.h3.draw.vs_position_output_regid=0x%x\r\n",
                       GPU_H3_VS_POSITION_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.vs_varying_output_regid=0x%x\r\n",
                       GPU_H3_VS_VARYING_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.ps_output_regid=0x%x\r\n", GPU_H3_PS_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.sp_vs_output_cntl=0x%x\r\n",
                       GPU_H3_SP_VS_OUTPUT_CNTL);
    a90_console_printf("gpu.h3.draw.sp_vs_output_reg0=0x%x\r\n", GPU_H3_SP_VS_OUTPUT_REG0);
    a90_console_printf("gpu.h3.draw.sp_vs_vpc_dest_reg0=0x%x\r\n",
                       GPU_H3_SP_VS_VPC_DEST_REG0);
    a90_console_printf("gpu.h3.draw.shader_mode_source=mesa-freedreno-a6xx-fd6-emit-shader-regs-sp-tpl1-mode\r\n");
    a90_console_printf("gpu.h3.draw.sp_const_config_source=mesa-freedreno-a6xx-fd6-program-config-stateobj\r\n");
    a90_console_printf("gpu.h3.draw.sp_vs_const_config=0x%x\r\n",
                       GPU_H3_SP_CONST_CONFIG_ENABLED);
    a90_console_printf("gpu.h3.draw.sp_ps_const_config=0x%x\r\n",
                       GPU_H3_SP_CONST_CONFIG_ENABLED);
    a90_console_printf("gpu.h3.draw.sp_vs_const_config_reference_deferred=0x101-requires-vs-constant-buffer\r\n");
    a90_console_printf("gpu.h3.draw.sp_update_cntl_source=mesa-freedreno-a6xx-fd6-program-and-draw-stateobj\r\n");
    a90_console_printf("gpu.h3.draw.sp_update_cntl=0x%x\r\n",
                       GPU_H3_SP_UPDATE_CNTL_DRAW_STATE);
    a90_console_printf("gpu.h3.draw.sp_vs_fullregfootprint=%u\r\n",
                       GPU_H3_SP_VS_FULLREGFOOTPRINT);
    a90_console_printf("gpu.h3.draw.sp_ps_fullregfootprint=%u\r\n",
                       GPU_H3_SP_PS_FULLREGFOOTPRINT);
    a90_console_printf("gpu.h3.draw.sp_mode_cntl=0x%x\r\n", GPU_H3_SP_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_mode_cntl=0x%x\r\n", GPU_H3_TPL1_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-cffdump-varying-ij\r\n");
    a90_console_printf("gpu.h3.draw.clip_guardband_su_source=mesa-freedreno-a6xx-fd6-rasterizer-plus-guardband-state\r\n");
    a90_console_printf("gpu.h3.draw.gras_cl_cntl=0x%x\r\n",
                       GPU_H3_GRAS_CL_CNTL);
    a90_console_printf("gpu.h3.draw.gras_cl_interp_cntl=0x%x\r\n",
                       GPU_H3_GRAS_CL_INTERP_CNTL);
    a90_console_printf("gpu.h3.draw.gras_cl_guardband_clip_adj=0x%x\r\n",
                       GPU_H3_GRAS_CL_GUARDBAND_CLIP_ADJ);
    a90_console_printf("gpu.h3.draw.gras_su_cntl=0x%x\r\n",
                       GPU_H3_GRAS_SU_CNTL);
    a90_console_printf("gpu.h3.draw.gras_su_point_minmax=0x%x\r\n",
                       GPU_H3_GRAS_SU_POINT_MINMAX);
    a90_console_printf("gpu.h3.draw.gras_su_point_size=0x%x\r\n",
                       GPU_H3_GRAS_SU_POINT_SIZE);
    a90_console_printf("gpu.h3.draw.gras_su_poly_offset_scale=0x%x\r\n",
                       GPU_H3_GRAS_SU_POLY_OFFSET_SCALE);
    a90_console_printf("gpu.h3.draw.gras_su_poly_offset_offset=0x%x\r\n",
                       GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET);
    a90_console_printf("gpu.h3.draw.gras_su_poly_offset_offset_clamp=0x%x\r\n",
                       GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP);
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
    a90_console_printf("gpu.h3.draw.window_offset_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-window-offset-zero\r\n");
    a90_console_printf("gpu.h3.draw.rb_window_offset=0x%x\r\n",
                       GPU_H3_WINDOW_OFFSET);
    a90_console_printf("gpu.h3.draw.rb_resolve_window_offset=0x%x\r\n",
                       GPU_H3_WINDOW_OFFSET);
    a90_console_printf("gpu.h3.draw.sp_window_offset=0x%x\r\n",
                       GPU_H3_WINDOW_OFFSET);
    a90_console_printf("gpu.h3.draw.tpl1_window_offset=0x%x\r\n",
                       GPU_H3_WINDOW_OFFSET);
    a90_console_printf("gpu.h3.draw.visibility_packet_source=mesa-freedreno-a6xx-fd6-sysmem-prep-visibility-override\r\n");
    a90_console_printf("gpu.h3.draw.cp_skip_ib2_enable_global=0x%x\r\n",
                       GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL);
    a90_console_printf("gpu.h3.draw.cp_skip_ib2_enable_local=0x%x\r\n",
                       GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL);
    a90_console_printf("gpu.h3.draw.cp_set_visibility_override=0x%x\r\n",
                       GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE);
    a90_console_printf("gpu.h3.draw.cp_skip_ib2_enable_global_value=0x%x\r\n",
                       GPU_H3_CP_SKIP_IB2_ENABLE_GLOBAL_VALUE);
    a90_console_printf("gpu.h3.draw.cp_skip_ib2_enable_local_value=0x%x\r\n",
                       GPU_H3_CP_SKIP_IB2_ENABLE_LOCAL_VALUE);
    a90_console_printf("gpu.h3.draw.cp_set_visibility_override_value=0x%x\r\n",
                       GPU_H3_CP_SET_VISIBILITY_OVERRIDE_VALUE);
    a90_console_printf("gpu.h3.draw.cache_invalidate_source=mesa-freedreno-a6xx-fd6-emit-restore-fd6-cache-inv\r\n");
    a90_console_printf("gpu.h3.draw.pre_draw_cache_invalidate=ccu-color,ccu-depth,cache\r\n");
    a90_console_printf("gpu.h3.draw.pre_draw_cache_invalidate_events=0x%x,0x%x,0x%x\r\n",
                       GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR,
                       GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH,
                       GPU_G4_EVENT_CACHE_INVALIDATE);
    a90_console_printf("gpu.h3.draw.cp_set_mode_source=mesa-freedreno-a6xx-fd6-emit-restore-cp-set-mode-zero\r\n");
    a90_console_printf("gpu.h3.draw.cp_set_mode=0x%x\r\n",
                       GPU_H3_PM4_CP_SET_MODE);
    a90_console_printf("gpu.h3.draw.cp_set_mode_value=0x%x\r\n",
                       GPU_H3_CP_SET_MODE_RESTORE_VALUE);
    a90_console_printf("gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-nonzero-magic-regs\r\n");
    a90_console_printf("gpu.h3.draw.a640_magic_mode=nonzero-block\r\n");
    a90_console_printf("gpu.h3.draw.a640_magic_nonzero_block=rb_dbg_eco,sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_mode,pc_power,vfd_power,uche_unknown_0e12\r\n");
    a90_console_printf("gpu.h3.draw.rb_dbg_eco_cntl=0x%x\r\n",
                       GPU_A640_RB_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.rb_dbg_eco_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_RB_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.sp_chicken_bits=0x%x\r\n",
                       GPU_A640_SP_CHICKEN_BITS);
    a90_console_printf("gpu.h3.draw.sp_chicken_bits_reg=0x%x\r\n",
                       GPU_A640_REG_SP_CHICKEN_BITS);
    a90_console_printf("gpu.h3.draw.tpl1_dbg_eco_cntl=0x%x\r\n",
                       GPU_A640_TPL1_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_dbg_eco_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_TPL1_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_dbg_eco_cntl=0x%x\r\n",
                       GPU_A640_VPC_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_dbg_eco_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_VPC_DBG_ECO_CNTL);
    a90_console_printf("gpu.h3.draw.rb_rbp_cntl=0x%x\r\n",
                       GPU_A640_RB_RBP_CNTL);
    a90_console_printf("gpu.h3.draw.rb_rbp_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_RB_RBP_CNTL);
    a90_console_printf("gpu.h3.draw.pc_mode_cntl_magic=0x%x\r\n",
                       GPU_A640_PC_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.pc_mode_cntl_magic_reg=0x%x\r\n",
                       GPU_A640_REG_PC_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.pc_power_cntl=0x%x\r\n",
                       GPU_A640_PC_POWER_CNTL);
    a90_console_printf("gpu.h3.draw.pc_power_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_PC_POWER_CNTL);
    a90_console_printf("gpu.h3.draw.vfd_power_cntl=0x%x\r\n",
                       GPU_A640_VFD_POWER_CNTL);
    a90_console_printf("gpu.h3.draw.vfd_power_cntl_reg=0x%x\r\n",
                       GPU_A640_REG_VFD_POWER_CNTL);
    a90_console_printf("gpu.h3.draw.uche_unknown_0e12=0x%x\r\n",
                       GPU_A640_UCHE_UNKNOWN_0E12);
    a90_console_printf("gpu.h3.draw.uche_unknown_0e12_reg=0x%x\r\n",
                       GPU_A640_REG_UCHE_UNKNOWN_0E12);
    a90_console_printf("gpu.h3.draw.a640_init_magic_reg_writes=%u\r\n",
                       GPU_H3_A640_INIT_MAGIC_REG_WRITES);
    a90_console_printf("gpu.h3.draw.rb_render_cntl_source=mesa-freedreno-a640-cffdump-draw2-rb-render-cntl-flag-mrt0\r\n");
    a90_console_printf("gpu.h3.draw.rb_render_cntl=0x%x\r\n", GPU_H3_RB_RENDER_CNTL);
    a90_console_printf("gpu.h3.draw.blend_output_state_source=mesa-freedreno-a640-cffdump-draw2-direct-sysmem-compatible-blend-output-group\r\n");
    a90_console_printf("gpu.h3.draw.sp_blend_cntl=0x%x\r\n", GPU_H3_SP_BLEND_CNTL);
    a90_console_printf("gpu.h3.draw.rb_blend_cntl=0x%x\r\n", GPU_H3_RB_BLEND_CNTL);
    a90_console_printf("gpu.h3.draw.rb_mrt0_blend_control=0x%x\r\n",
                       GPU_H3_RB_MRT0_BLEND_CONTROL);
    a90_console_printf("gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs\r\n");
    a90_console_printf("gpu.h3.draw.fs_output_cntl_source=mesa-freedreno-a6xx-fd6-program-invalid-depth-sampmask-stencil-regids-and-rb-sp-mrt-count-one\r\n");
    a90_console_printf("gpu.h3.draw.rb_ps_output_cntl=0x%x\r\n",
                       GPU_H3_RB_PS_OUTPUT_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ps_mrt_cntl=0x%x\r\n",
                       GPU_H3_RB_PS_MRT_CNTL);
    a90_console_printf("gpu.h3.draw.sp_ps_output_cntl=0x%x\r\n",
                       GPU_H3_SP_PS_OUTPUT_CNTL);
    a90_console_printf("gpu.h3.draw.sp_ps_mrt_cntl=0x%x\r\n",
                       GPU_H3_SP_PS_MRT_CNTL);
    a90_console_printf("gpu.h3.draw.sp_ps_output_reg0=0x%x\r\n",
                       GPU_H3_PS_OUTPUT_REGID);
    a90_console_printf("gpu.h3.draw.sp_ps_output_reg1_7=0x%x\r\n",
                       GPU_H3_SP_INVALID_REG);
    a90_console_printf("gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-varying-ij-persp-pixel\r\n");
    a90_console_printf("gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x%x\r\n",
                       GPU_H3_SP_PS_INITIAL_TEX_LOAD_CNTL);
    a90_console_printf("gpu.h3.draw.sp_ps_wave_cntl=0x%x\r\n",
                       GPU_H3_SP_PS_WAVE_CNTL);
    a90_console_printf("gpu.h3.draw.sp_lb_param_limit=0x%x\r\n",
                       GPU_H3_SP_LB_PARAM_LIMIT);
    a90_console_printf("gpu.h3.draw.sp_reg_prog_id_0=0x%x\r\n",
                       GPU_H3_SP_REG_PROG_ID_0);
    a90_console_printf("gpu.h3.draw.sp_reg_prog_id_1=0x%x\r\n",
                       GPU_H3_SP_REG_PROG_ID_1);
    a90_console_printf("gpu.h3.draw.sp_reg_prog_id_2=0x%x\r\n",
                       GPU_H3_SP_REG_PROG_ID_2);
    a90_console_printf("gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2\r\n");
    a90_console_printf("gpu.h3.draw.rb_ccu_cntl=0x%x\r\n", GPU_H3_RB_CCU_CNTL);
    a90_console_printf("gpu.h3.draw.rb_ccu_color_offset=0x%x\r\n",
                       GPU_H3_RB_CCU_COLOR_OFFSET);
    a90_console_printf("gpu.h3.draw.rb_ccu_depth_offset=0x%x\r\n",
                       GPU_H3_RB_CCU_DEPTH_OFFSET);
    a90_console_printf("gpu.h3.draw.bin_control_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-bin-size\r\n");
    a90_console_printf("gpu.h3.draw.bin_control_decode=rendering-pass-buffers-in-sysmem-lrz-feedback-early-z-late-z\r\n");
    a90_console_printf("gpu.h3.draw.gras_sc_bin_cntl=0x%x\r\n",
                       GPU_H3_GRAS_SC_BIN_CNTL);
    a90_console_printf("gpu.h3.draw.rb_cntl=0x%x\r\n", GPU_H3_RB_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_linkage_source=mesa-freedreno-a6xx-position-psizeloc-clip-cull-linkage\r\n");
    a90_console_printf("gpu.h3.draw.vpc_vs_cntl=0x%x\r\n", GPU_H3_VPC_VS_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_ps_cntl=0x%x\r\n", GPU_H3_VPC_PS_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x\r\n",
                       GPU_H3_VPC_VS_CLIP_CULL_CNTL);
    a90_console_printf("gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x\r\n",
                       GPU_H3_VPC_VS_CLIP_CULL_CNTL);
    a90_console_printf("gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x\r\n",
                       GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE);
    a90_console_printf("gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-cffdump-vpc-position-plus-four-varyings\r\n");
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
    a90_console_printf("gpu.h3.draw.vpc_so_override_source=mesa-freedreno-a6xx-fd6-sysmem-prep-enable-streamout-false\r\n");
    a90_console_printf("gpu.h3.draw.vpc_so_override=0x%x\r\n",
                       GPU_H3_VPC_SO_OVERRIDE);
    a90_console_printf("gpu.h3.draw.vpc_rast_stream_cntl=0x%x\r\n",
                       GPU_H3_VPC_RAST_STREAM_CNTL);
    a90_console_printf("gpu.h3.draw.raster_mode_source=mesa-freedreno-a6xx-fd6-rasterizer-polymode-triangles\r\n");
    a90_console_printf("gpu.h3.draw.vpc_rast_cntl=0x%x\r\n",
                       GPU_H3_VPC_RAST_CNTL);
    a90_console_printf("gpu.h3.draw.pc_dgen_rast_cntl=0x%x\r\n",
                       GPU_H3_PC_DGEN_RAST_CNTL);
    a90_console_printf("gpu.h3.draw.pc_mode_cntl=0x%x\r\n",
                       GPU_H3_PC_MODE_CNTL);
    a90_console_printf("gpu.h3.draw.pc_vs_cntl=0x%x\r\n",
                       GPU_H3_PC_VS_CNTL);
    a90_console_printf("gpu.h3.draw.pc_stereo_rendering_cntl=0x%x\r\n",
                       GPU_H3_PC_STEREO_RENDERING_CNTL);
    a90_console_printf("gpu.h3.draw.tpl1_ps_swizzle_cntl=0x%x\r\n",
                       GPU_H3_TPL1_PS_SWIZZLE_CNTL);
    a90_console_printf("gpu.h3.draw.sp_reg_prog_id_3=0x%x\r\n",
                       GPU_H3_SP_REG_PROG_ID_3);
    a90_console_printf("gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0\r\n");
    a90_console_printf("gpu.h3.draw.ir3_end_opcode_hi=0x%x\r\n", GPU_H1_IR3_END_HI);
    a90_console_printf("gpu.h3.draw.vfd_contract_source=mesa-freedreno-a640-cffdump-draw2-vfd-fetch-decode-shape\r\n");
    a90_console_printf("gpu.h3.draw.vfd_cntl_0=0x%x\r\n", GPU_H3_VFD_CNTL_0);
    a90_console_printf("gpu.h3.draw.vfd_cntl_1=0x%x\r\n", GPU_H3_VFD_CNTL_1);
    a90_console_printf("gpu.h3.draw.vfd_cntl_2=0x%x\r\n", GPU_H3_VFD_CNTL_2);
    a90_console_printf("gpu.h3.draw.vfd_cntl_3=0x%x\r\n", GPU_H3_VFD_CNTL_3);
    a90_console_printf("gpu.h3.draw.vfd_cntl_4=0x%x\r\n", GPU_H3_VFD_CNTL_4);
    a90_console_printf("gpu.h3.draw.vfd_cntl_5=0x%x\r\n", GPU_H3_VFD_CNTL_5);
    a90_console_printf("gpu.h3.draw.vfd_cntl_6=0x%x\r\n", GPU_H3_VFD_CNTL_6);
    a90_console_printf("gpu.h3.draw.ir3_mov_f32f32_r2x_r1x_hi=0x%x\r\n",
                       GPU_H3_IR3_MOV_F32F32_R2X_R1X_HI);
    a90_console_printf("gpu.h3.draw.ir3_mov_f32f32_r2y_r1y_hi=0x%x\r\n",
                       GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_HI);
    a90_console_printf("gpu.h3.draw.ir3_mov_f32f32_r2z_r1z_hi=0x%x\r\n",
                       GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_HI);
    a90_console_printf("gpu.h3.draw.ir3_mov_f32f32_r2w_r1w_hi=0x%x\r\n",
                       GPU_H3_IR3_MOV_F32F32_R2W_R1W_HI);
    a90_console_printf("gpu.h3.draw.ir3_bary_f_r0z_ij0_hi=0x%x\r\n",
                       GPU_H3_IR3_BARY_F_R0Z_IJ0_HI);
    a90_console_printf("gpu.h3.draw.ir3_bary_f_r1y_ij3_ei_hi=0x%x\r\n",
                       GPU_H3_IR3_BARY_F_R1Y_IJ3_EI_HI);
    a90_console_printf("gpu.h3.draw.color_output_mask=0x%x\r\n",
                       GPU_H3_COLOR_OUTPUT_MASK);
    a90_console_printf("gpu.h3.draw.vertex_format=cffdump-shaped-r0-vec4-r1-vec4-r2x-sint\r\n");
    a90_console_printf("gpu.h3.draw.vertex_fetch0_format=0x%x\r\n",
                       GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT);
    a90_console_printf("gpu.h3.draw.vertex_fetch1_format=0x%x\r\n",
                       GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT);
    a90_console_printf("gpu.h3.draw.vertex_fetch2_format=0x%x\r\n",
                       GPU_H3_A6XX_FMT6_32_SINT);
    a90_console_printf("gpu.h3.draw.vfd_fetch_instr0=0x%x\r\n",
                       GPU_H3_VFD_FETCH_INSTR0);
    a90_console_printf("gpu.h3.draw.vfd_fetch_instr1=0x%x\r\n",
                       GPU_H3_VFD_FETCH_INSTR1);
    a90_console_printf("gpu.h3.draw.vfd_fetch_instr2=0x%x\r\n",
                       GPU_H3_VFD_FETCH_INSTR2);
    a90_console_printf("gpu.h3.draw.vfd_dest_cntl0=0x%x\r\n",
                       GPU_H3_VFD_DEST_CNTL0);
    a90_console_printf("gpu.h3.draw.vfd_dest_cntl1=0x%x\r\n",
                       GPU_H3_VFD_DEST_CNTL1);
    a90_console_printf("gpu.h3.draw.vfd_dest_cntl2=0x%x\r\n",
                       GPU_H3_VFD_DEST_CNTL2);
    a90_console_printf("gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-tile6-3-flag-mrt0\r\n");
    a90_console_printf("gpu.h3.draw.sp_ps_mrt_reg0=0x%x\r\n",
                       GPU_H3_SP_PS_MRT_REG0);
    a90_console_printf("gpu.h3.draw.rb_mrt0_buf_info=0x%x\r\n",
                       GPU_H3_RB_MRT0_BUF_INFO);
    a90_console_printf("gpu.h3.draw.color_flag_buffer_source=mesa-freedreno-a640-cffdump-rb-color-flag-buffer0\r\n");
    a90_console_printf("gpu.h3.draw.color_flag_buffer_pitch=0x%x\r\n",
                       GPU_H3_COLOR_FLAG_BUFFER_PITCH);
    a90_console_printf("gpu.h3.draw.offscreen=rgba8-tile6-3-flag-mrt0-128x128\r\n");
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
        return gpu_h3_draw_envelope_probe_child(pipefd[1], false, false);
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
        a90_console_printf("gpu.h3.draw.color_flag_alloc_rc=%d\r\n",
                           result.color_flag_alloc_rc);
        a90_console_printf("gpu.h3.draw.event_alloc_rc=%d\r\n", result.event_alloc_rc);
        a90_console_printf("gpu.h3.draw.vs_alloc_rc=%d\r\n", result.vs_alloc_rc);
        a90_console_printf("gpu.h3.draw.fs_alloc_rc=%d\r\n", result.fs_alloc_rc);
        a90_console_printf("gpu.h3.draw.vertex_alloc_rc=%d\r\n", result.vertex_alloc_rc);
        a90_console_printf("gpu.h3.draw.cmd_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.cmd_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.color_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.color_info_gpuaddr);
        a90_console_printf("gpu.h3.draw.color_flag_info_gpuaddr=0x%llx\r\n",
                           (unsigned long long)result.color_flag_info_gpuaddr);
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
        a90_console_printf("gpu.h3.draw.color_flag_pitch=0x%x\r\n",
                           result.color_flag_pitch);
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
        a90_console_printf("gpu.h3.draw.color_flag_changed_count=%u\r\n",
                           result.color_flag_changed_count);
        a90_console_printf("gpu.h3.draw.color_flag_first_changed_index=%u\r\n",
                           result.color_flag_first_changed_index);
        a90_console_printf("gpu.h3.draw.color_flag_first_changed_value=0x%x\r\n",
                           result.color_flag_first_changed_value);
        a90_console_printf("gpu.h3.draw.color_flag0=0x%x\r\n", result.color_flag0);
        a90_console_printf("gpu.h3.draw.fence_poll_rc=%d\r\n", result.fence_poll_rc);
        a90_console_printf("gpu.h3.draw.fence_poll_revents=0x%x\r\n",
                           result.fence_poll_revents);
        a90_console_printf("gpu.h3.draw.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.h3.draw.color_free_rc=%d\r\n", result.color_free_rc);
        a90_console_printf("gpu.h3.draw.color_flag_free_rc=%d\r\n",
                           result.color_flag_free_rc);
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

static int gpu_h3_draw_snapshot_collect_child(int timeout_ms,
                                              struct gpu_h3_draw_snapshot_child_run *run) {
    int pipefd[2];
    long deadline_ms;
    uint8_t *payload_bytes;
    size_t payload_size;

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
        return gpu_h3_draw_envelope_probe_child(pipefd[1], true, true);
    }
    close(pipefd[1]);
    {
        int flags = fcntl(pipefd[0], F_GETFL, 0);

        if (flags >= 0) {
            (void)fcntl(pipefd[0], F_SETFL, flags | O_NONBLOCK);
        }
    }

    payload_bytes = (uint8_t *)&run->payload;
    payload_size = sizeof(run->payload);
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
            while (run->payload_bytes_read < payload_size) {
                ssize_t rd = read(pipefd[0],
                                  payload_bytes + run->payload_bytes_read,
                                  payload_size - run->payload_bytes_read);

                if (rd > 0) {
                    run->payload_bytes_read += (size_t)rd;
                    continue;
                }
                if (rd == 0 || (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)) {
                    break;
                }
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    break;
                }
            }
            if (run->payload_bytes_read == payload_size) {
                run->got_result = true;
                break;
            }
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

static bool gpu_d1_texture_checkerboard_result_passed(
    const struct gpu_h3_draw_envelope_probe_result *result) {
    return result != NULL &&
           result->color_init_rc == 0 &&
           result->shader_write_rc == 0 &&
           result->vertex_write_rc == 0 &&
           result->texture_write_rc == 0 &&
           result->texture_desc_write_rc == 0 &&
           result->cmd_write_rc == 0 &&
           result->sync_rc == 0 &&
           result->submit_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->readback_sync_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->linear_readback_changed_count > 0U &&
           result->linear_readback_bbox_found == 1U &&
           result->linear_readback_bbox_max_x >= result->linear_readback_bbox_min_x &&
           result->linear_readback_bbox_max_y >= result->linear_readback_bbox_min_y &&
           result->texture_bbox_sample_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->texture_bbox_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->texture_bbox_sample_mismatch_count == 0U &&
           result->texture_dark_count > 0U &&
           result->texture_light_count > 0U;
}

static bool gpu_d2_realframe_texture_result_passed(
    const struct gpu_h3_draw_envelope_probe_result *result) {
    return result != NULL &&
           result->realframe_manifest_rc == 0 &&
           result->realframe_open_rc == 0 &&
           result->realframe_header_rc == 0 &&
           result->realframe_record_rc == 0 &&
           result->realframe_read_rc == 0 &&
           result->realframe_close_rc == 0 &&
           result->color_init_rc == 0 &&
           result->shader_write_rc == 0 &&
           result->vertex_write_rc == 0 &&
           result->texture_write_rc == 0 &&
           result->texture_desc_write_rc == 0 &&
           result->cmd_write_rc == 0 &&
           result->sync_rc == 0 &&
           result->submit_rc == 0 &&
           result->wait_rc == 0 &&
           result->readtimestamp_rc == 0 &&
           result->readback_sync_rc == 0 &&
           result->retired_timestamp >= result->submit_timestamp &&
           result->linear_readback_changed_count > 0U &&
           result->linear_readback_bbox_found == 1U &&
           result->texture_bbox_sample_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->texture_bbox_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->texture_bbox_sample_mismatch_count == 0U &&
           result->realframe_bbox_sample_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->realframe_bbox_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           result->realframe_bbox_sample_mismatch_count == 0U &&
           result->realframe_source_dark_count > 0U &&
           result->realframe_source_light_count > 0U &&
           result->texture_dark_count > 0U &&
           result->texture_light_count > 0U;
}

static int gpu_d1_texture_probe_child(int write_fd,
                                      const struct gpu_d1_texture_source_config *config) {
    static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS] = {
        GPU_H3_IR3_MOV_F32F32_R2X_R1X_LO, GPU_H3_IR3_MOV_F32F32_R2X_R1X_HI,
        GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_LO, GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_HI,
        GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_LO, GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_HI,
        GPU_H3_IR3_MOV_F32F32_R2W_R1W_LO, GPU_H3_IR3_MOV_F32F32_R2W_R1W_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t fs_shader[GPU_D1_FS_SHADER_DWORDS] = {
        0x00002000U, 0x47300000U,
        0x00002001U, 0x47300001U,
        0x00000001U, 0xa0c01f02U,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t vertex_words[GPU_D1_VERTEX_DWORDS] = {
        0xbf800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0xbf800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0xbf800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
    };
    struct gpu_h3_draw_envelope_probe_result result;
    struct gpu_kgsl_drawctxt_create create_arg;
    long total_started_ms = monotonic_millis();
    void *cmd_map = MAP_FAILED;
    void *color_map = MAP_FAILED;
    void *color_flag_map = MAP_FAILED;
    void *linear_map = MAP_FAILED;
    void *vs_map = MAP_FAILED;
    void *fs_map = MAP_FAILED;
    void *vertex_map = MAP_FAILED;
    void *sampler_map = MAP_FAILED;
    void *texmem_map = MAP_FAILED;
    void *texture_map = MAP_FAILED;
    struct video_stream_manifest realframe_manifest;
    uint8_t *realframe_frame = NULL;
    bool realframe_mode = config != NULL &&
        config->kind == GPU_D1_TEXTURE_SOURCE_REALFRAME_MONO1;
    uint32_t texture_width = GPU_D1_TEXTURE_WIDTH;
    uint32_t texture_height = GPU_D1_TEXTURE_HEIGHT;
    uint32_t texture_stride = GPU_D1_TEXTURE_STRIDE;
    uint64_t texture_bytes = GPU_D1_TEXTURE_BYTES;
    uint64_t texture_alloc_size = GPU_D1_TEXTURE_ALLOC_SIZE;
    int fd = -1;
    int fence_fd = -1;

    memset(&result, 0, sizeof(result));
    memset(&create_arg, 0, sizeof(create_arg));
    memset(&realframe_manifest, 0, sizeof(realframe_manifest));
    result.version = 1;
    result.close_rc = -1;
    result.create_rc = -1;
    result.cmd_alloc_rc = -1;
    result.cmd_info_rc = -1;
    result.cmd_mmap_rc = -1;
    result.color_alloc_rc = -1;
    result.color_info_rc = -1;
    result.color_mmap_rc = -1;
    result.color_flag_alloc_rc = -1;
    result.color_flag_info_rc = -1;
    result.color_flag_mmap_rc = -1;
    result.linear_alloc_rc = -1;
    result.linear_info_rc = -1;
    result.linear_mmap_rc = -1;
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
    result.sampler_alloc_rc = -1;
    result.sampler_info_rc = -1;
    result.sampler_mmap_rc = -1;
    result.texmem_alloc_rc = -1;
    result.texmem_info_rc = -1;
    result.texmem_mmap_rc = -1;
    result.texture_alloc_rc = -1;
    result.texture_info_rc = -1;
    result.texture_mmap_rc = -1;
    result.color_init_rc = -1;
    result.shader_write_rc = -1;
    result.vertex_write_rc = -1;
    result.texture_write_rc = -1;
    result.texture_desc_write_rc = -1;
    result.realframe_manifest_rc = realframe_mode ? -1 : 0;
    result.realframe_open_rc = realframe_mode ? -1 : 0;
    result.realframe_header_rc = realframe_mode ? -1 : 0;
    result.realframe_record_rc = realframe_mode ? -1 : 0;
    result.realframe_read_rc = realframe_mode ? -1 : 0;
    result.realframe_close_rc = realframe_mode ? -1 : 0;
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
    result.color_flag_munmap_rc = -1;
    result.linear_munmap_rc = -1;
    result.vs_munmap_rc = -1;
    result.fs_munmap_rc = -1;
    result.vertex_munmap_rc = -1;
    result.sampler_munmap_rc = -1;
    result.texmem_munmap_rc = -1;
    result.texture_munmap_rc = -1;
    result.cmd_free_rc = -1;
    result.color_free_rc = -1;
    result.color_flag_free_rc = -1;
    result.linear_free_rc = -1;
    result.event_free_rc = -1;
    result.vs_free_rc = -1;
    result.fs_free_rc = -1;
    result.vertex_free_rc = -1;
    result.sampler_free_rc = -1;
    result.texmem_free_rc = -1;
    result.texture_free_rc = -1;
    result.destroy_rc = -1;
    result.wait_timeout_ms = GPU_H3_WAIT_TIMEOUT_MS;
    result.color_width = GPU_H2_COLOR_WIDTH;
    result.color_height = GPU_H2_COLOR_HEIGHT;
    result.color_stride = GPU_H2_COLOR_STRIDE;
    result.color_format = GPU_H3_COLOR_FORMAT;
    result.color_flag_pitch = GPU_H3_COLOR_FLAG_BUFFER_PITCH;
    result.color_bytes = GPU_H2_COLOR_ALLOC_SIZE;
    result.vertex_stride = GPU_D1_VERTEX_STRIDE;
    result.vertex_bytes = (unsigned int)GPU_D1_VERTEX_BYTES;
    result.vertex_count = GPU_D1_VERTEX_COUNT;
    result.vertex_format = GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT;
    result.texture_width = GPU_D1_TEXTURE_WIDTH;
    result.texture_height = GPU_D1_TEXTURE_HEIGHT;
    result.texture_stride = GPU_D1_TEXTURE_STRIDE;
    result.texture_bytes = (unsigned int)GPU_D1_TEXTURE_BYTES;
    result.texture_format = GPU_H3_COLOR_FORMAT;
    result.texture_desc_dwords = GPU_D1_TEXMEMOBJ_DESC_DWORDS;
    result.sampler_desc_dwords = GPU_D1_SAMPLER_DESC_DWORDS;
    result.texture_sample_grid = GPU_D1_CHECKER_SAMPLE_GRID;
    result.texture_sample_count = GPU_D1_CHECKER_SAMPLE_COUNT;
    result.texture_first_mismatch_index = UINT_MAX;
    result.texture_bbox_first_mismatch_index = UINT_MAX;
    result.realframe_bbox_first_mismatch_index = UINT_MAX;
    result.linear_readback_bbox_min_x = UINT_MAX;
    result.linear_readback_bbox_min_y = UINT_MAX;
    result.linear_readback_bbox_max_x = 0U;
    result.linear_readback_bbox_max_y = 0U;
    result.cp_draw_packet = GPU_H3_PM4_CP_DRAW_INDX_OFFSET;
    result.draw_initiator = gpu_h3_draw_initiator();
    result.num_instances = 1U;
    result.num_indices = GPU_D1_VERTEX_COUNT;
    result.draw_attempted = 1;
    result.shader_execution_attempted = 1;
    result.kms_blit_attempted = 0;
    result.linear_blit_attempted = 1U;
    result.fence_fd = -1;

    if (realframe_mode) {
        int rc = gpu_d2_parse_realframe_manifest(config, &realframe_manifest, &result);

        if (rc < 0) {
            goto out;
        }
        rc = gpu_d2_read_realframe_mono1(&realframe_manifest,
                                         config->frame_index,
                                         &realframe_frame,
                                         &result);
        if (rc < 0) {
            goto out;
        }
        texture_width = realframe_manifest.width;
        texture_height = realframe_manifest.height;
        texture_stride = texture_width * GPU_D1_TEXTURE_BPP;
        texture_bytes = (uint64_t)texture_stride * texture_height;
        texture_alloc_size = gpu_d1_round_up_u64(texture_bytes, 4096ULL);
    }

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
        struct gpu_kgsl_gpuobj_alloc color_flag_alloc_arg;
        struct gpu_kgsl_gpuobj_info color_flag_info_arg;
        struct gpu_kgsl_gpuobj_alloc linear_alloc_arg;
        struct gpu_kgsl_gpuobj_info linear_info_arg;
        struct gpu_kgsl_gpuobj_alloc event_alloc_arg;
        struct gpu_kgsl_gpuobj_info event_info_arg;
        struct gpu_kgsl_gpuobj_alloc vs_alloc_arg;
        struct gpu_kgsl_gpuobj_info vs_info_arg;
        struct gpu_kgsl_gpuobj_alloc fs_alloc_arg;
        struct gpu_kgsl_gpuobj_info fs_info_arg;
        struct gpu_kgsl_gpuobj_alloc vertex_alloc_arg;
        struct gpu_kgsl_gpuobj_info vertex_info_arg;
        struct gpu_kgsl_gpuobj_alloc sampler_alloc_arg;
        struct gpu_kgsl_gpuobj_info sampler_info_arg;
        struct gpu_kgsl_gpuobj_alloc texmem_alloc_arg;
        struct gpu_kgsl_gpuobj_info texmem_info_arg;
        struct gpu_kgsl_gpuobj_alloc texture_alloc_arg;
        struct gpu_kgsl_gpuobj_info texture_info_arg;
        uint64_t cmd_mmap_offset;
        uint64_t color_mmap_offset;
        uint64_t color_flag_mmap_offset;
        uint64_t linear_mmap_offset;
        uint64_t vs_mmap_offset;
        uint64_t fs_mmap_offset;
        uint64_t vertex_mmap_offset;
        uint64_t sampler_mmap_offset;
        uint64_t texmem_mmap_offset;
        uint64_t texture_mmap_offset;

#define GPU_D1_ALLOC_INFO_MMAP(name, size_value, min_size_value) \
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

        GPU_D1_ALLOC_INFO_MMAP(cmd, GPU_H3_CMD_ALLOC_SIZE,
                               (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL);
        GPU_D1_ALLOC_INFO_MMAP(color, GPU_H2_COLOR_ALLOC_SIZE,
                               GPU_H2_COLOR_ALLOC_SIZE);
        GPU_D1_ALLOC_INFO_MMAP(color_flag, GPU_H3_COLOR_FLAG_ALLOC_SIZE,
                               GPU_H3_COLOR_FLAG_ALLOC_SIZE);
        GPU_D1_ALLOC_INFO_MMAP(linear, GPU_H2_COLOR_ALLOC_SIZE,
                               GPU_H2_COLOR_ALLOC_SIZE);
        GPU_D1_ALLOC_INFO_MMAP(vs, GPU_H1_SHADER_ALLOC_SIZE, sizeof(vs_shader));
        GPU_D1_ALLOC_INFO_MMAP(fs, GPU_H1_SHADER_ALLOC_SIZE, sizeof(fs_shader));
        GPU_D1_ALLOC_INFO_MMAP(vertex, GPU_H3_VERTEX_ALLOC_SIZE, GPU_D1_VERTEX_BYTES);
        GPU_D1_ALLOC_INFO_MMAP(sampler, GPU_D1_DESCRIPTOR_ALLOC_SIZE,
                               GPU_D1_SAMPLER_DESC_DWORDS * 4ULL);
        GPU_D1_ALLOC_INFO_MMAP(texmem, GPU_D1_DESCRIPTOR_ALLOC_SIZE,
                               GPU_D1_TEXMEMOBJ_DESC_DWORDS * 4ULL);
        GPU_D1_ALLOC_INFO_MMAP(texture, texture_alloc_size, texture_bytes);
#undef GPU_D1_ALLOC_INFO_MMAP

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

        {
            uint32_t *color_words = (uint32_t *)color_map;
            uint32_t *color_flag_words = (uint32_t *)color_flag_map;
            uint32_t *linear_words = (uint32_t *)linear_map;
            unsigned int index;

            for (index = 0; index < (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL); ++index) {
                color_words[index] = GPU_H2_CLEAR_PATTERN;
                linear_words[index] = GPU_H5_LINEAR_CLEAR_PATTERN;
            }
            for (index = 0; index < (unsigned int)(GPU_H3_COLOR_FLAG_ALLOC_SIZE / 4ULL); ++index) {
                color_flag_words[index] = 0;
            }
            __sync_synchronize();
            result.color_init_rc = 0;
        }

        if (realframe_mode) {
            gpu_d2_write_realframe_texture((uint32_t *)texture_map,
                                           realframe_frame,
                                           &realframe_manifest,
                                           &result);
        } else {
            gpu_d1_write_checker_texture((uint32_t *)texture_map);
        }
        gpu_d1_write_sampler_descriptor((uint32_t *)sampler_map);
        gpu_d1_write_texture_descriptor_ex((uint32_t *)texmem_map,
                                           texture_info_arg.gpuaddr,
                                           texture_width,
                                           texture_height,
                                           texture_stride,
                                           texture_bytes);
        __sync_synchronize();
        result.texture_write_rc = 0;
        result.texture_desc_write_rc = 0;

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
            if (!gpu_d1_build_texture_checkerboard_pm4(cmd_words,
                                                       &pm4_dwords,
                                                       &state_reg_writes,
                                                       &vfd_reg_writes,
                                                       color_info_arg.gpuaddr,
                                                       color_flag_info_arg.gpuaddr,
                                                       linear_info_arg.gpuaddr,
                                                       event_info_arg.gpuaddr,
                                                       vs_info_arg.gpuaddr,
                                                       fs_info_arg.gpuaddr,
                                                       vertex_info_arg.gpuaddr,
                                                       sampler_info_arg.gpuaddr,
                                                       texmem_info_arg.gpuaddr)) {
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
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[11];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = cmd_alloc_arg.id;
            sync_objs[0].length = result.cmd_size;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_alloc_arg.id;
            sync_objs[1].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = color_flag_alloc_arg.id;
            sync_objs[2].length = GPU_H3_COLOR_FLAG_ALLOC_SIZE;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[3].id = linear_alloc_arg.id;
            sync_objs[3].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[4].id = event_alloc_arg.id;
            sync_objs[4].length = GPU_H3_EVENT_ALLOC_SIZE;
            sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[5].id = vs_alloc_arg.id;
            sync_objs[5].length = sizeof(vs_shader);
            sync_objs[5].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[6].id = fs_alloc_arg.id;
            sync_objs[6].length = sizeof(fs_shader);
            sync_objs[6].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[7].id = vertex_alloc_arg.id;
            sync_objs[7].length = GPU_D1_VERTEX_BYTES;
            sync_objs[7].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[8].id = sampler_alloc_arg.id;
            sync_objs[8].length = GPU_D1_SAMPLER_DESC_DWORDS * 4ULL;
            sync_objs[8].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[9].id = texmem_alloc_arg.id;
            sync_objs[9].length = GPU_D1_TEXMEMOBJ_DESC_DWORDS * 4ULL;
            sync_objs[9].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[10].id = texture_alloc_arg.id;
            sync_objs[10].length = texture_bytes;
            sync_objs[10].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.cmd_sync_length = sync_objs[0].length;
            result.color_sync_length = sync_objs[1].length;
            result.color_flag_sync_length = sync_objs[2].length;
            result.linear_sync_length = sync_objs[3].length;
            result.event_sync_length = sync_objs[4].length;
            result.vs_sync_length = sync_objs[5].length;
            result.fs_sync_length = sync_objs[6].length;
            result.vertex_sync_length = sync_objs[7].length;
            result.sampler_sync_length = sync_objs[8].length;
            result.texmem_sync_length = sync_objs[9].length;
            result.texture_sync_length = sync_objs[10].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 11U;
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
            struct gpu_kgsl_command_object mem_objs[11];
            struct gpu_kgsl_gpu_command command_arg;

            memset(&cmd_obj, 0, sizeof(cmd_obj));
            cmd_obj.gpuaddr = cmd_info_arg.gpuaddr;
            cmd_obj.size = result.cmd_size;
            cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
            cmd_obj.id = cmd_alloc_arg.id;

            memset(mem_objs, 0, sizeof(mem_objs));
#define GPU_D1_MEMOBJ(slot, info, alloc) \
            do { \
                mem_objs[(slot)].gpuaddr = info##_arg.gpuaddr; \
                mem_objs[(slot)].size = info##_arg.size; \
                mem_objs[(slot)].flags = GPU_KGSL_OBJLIST_MEMOBJ; \
                mem_objs[(slot)].id = alloc##_arg.id; \
            } while (0)
            GPU_D1_MEMOBJ(0, cmd_info, cmd_alloc);
            GPU_D1_MEMOBJ(1, color_info, color_alloc);
            GPU_D1_MEMOBJ(2, color_flag_info, color_flag_alloc);
            GPU_D1_MEMOBJ(3, linear_info, linear_alloc);
            GPU_D1_MEMOBJ(4, event_info, event_alloc);
            GPU_D1_MEMOBJ(5, vs_info, vs_alloc);
            GPU_D1_MEMOBJ(6, fs_info, fs_alloc);
            GPU_D1_MEMOBJ(7, vertex_info, vertex_alloc);
            GPU_D1_MEMOBJ(8, sampler_info, sampler_alloc);
            GPU_D1_MEMOBJ(9, texmem_info, texmem_alloc);
            GPU_D1_MEMOBJ(10, texture_info, texture_alloc);
#undef GPU_D1_MEMOBJ

            memset(&command_arg, 0, sizeof(command_arg));
            command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
            command_arg.cmdsize = sizeof(cmd_obj);
            command_arg.numcmds = 1;
            command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
            command_arg.objsize = sizeof(mem_objs[0]);
            command_arg.numobjs = 11U;
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
            struct gpu_kgsl_gpuobj_sync_obj sync_objs[3];
            struct gpu_kgsl_gpuobj_sync sync_arg;

            memset(sync_objs, 0, sizeof(sync_objs));
            sync_objs[0].id = color_alloc_arg.id;
            sync_objs[0].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[1].id = color_flag_alloc_arg.id;
            sync_objs[1].length = GPU_H3_COLOR_FLAG_ALLOC_SIZE;
            sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            sync_objs[2].id = linear_alloc_arg.id;
            sync_objs[2].length = GPU_H2_COLOR_ALLOC_SIZE;
            sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
            result.readback_sync_length =
                sync_objs[0].length + sync_objs[1].length + sync_objs[2].length;
            memset(&sync_arg, 0, sizeof(sync_arg));
            sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
            sync_arg.obj_len = sizeof(sync_objs[0]);
            sync_arg.count = 3U;
            errno = 0;
            if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
                result.readback_sync_rc = -1;
                result.readback_sync_errno = errno;
            } else {
                uint32_t *color_words = (uint32_t *)color_map;
                uint32_t *color_flag_words = (uint32_t *)color_flag_map;
                uint32_t *linear_words = (uint32_t *)linear_map;
                unsigned int word_count = (unsigned int)(GPU_H2_COLOR_ALLOC_SIZE / 4ULL);
                unsigned int flag_word_count =
                    (unsigned int)(GPU_H3_COLOR_FLAG_ALLOC_SIZE / 4ULL);
                unsigned int index;
                unsigned int center_index =
                    (GPU_H2_COLOR_HEIGHT / 2U) * GPU_H2_COLOR_WIDTH +
                    (GPU_H2_COLOR_WIDTH / 2U);

                result.readback_sync_rc = 0;
                result.readback0 = color_words[0];
                result.readback_center = color_words[center_index];
                result.readback_first_changed_index = UINT_MAX;
                result.color_flag_first_changed_index = UINT_MAX;
                result.linear_readback_first_changed_index = UINT_MAX;
                result.linear_readback_first_nonzero_index = UINT_MAX;
                for (index = 0; index < word_count; ++index) {
                    uint32_t rgb = linear_words[index] & 0x00ffffffU;
                    unsigned int x = index % GPU_H2_COLOR_WIDTH;
                    unsigned int y = index / GPU_H2_COLOR_WIDTH;

                    if (color_words[index] != GPU_H2_CLEAR_PATTERN) {
                        if (result.readback_changed_count == 0U) {
                            result.readback_first_changed_index = index;
                            result.readback_first_changed_value = color_words[index];
                        }
                        result.readback_changed_count += 1U;
                    }
                    if (linear_words[index] != GPU_H5_LINEAR_CLEAR_PATTERN) {
                        if (result.linear_readback_changed_count == 0U) {
                            result.linear_readback_first_changed_index = index;
                            result.linear_readback_first_changed_value = linear_words[index];
                        }
                        result.linear_readback_changed_count += 1U;
                    }
                    if (linear_words[index] != 0U) {
                        if (result.linear_readback_nonzero_count == 0U) {
                            result.linear_readback_first_nonzero_index = index;
                            result.linear_readback_first_nonzero_value = linear_words[index];
                        }
                        result.linear_readback_nonzero_count += 1U;
                    }
                    if (linear_words[index] != GPU_H5_LINEAR_CLEAR_PATTERN) {
                        if (result.linear_readback_bbox_found == 0U) {
                            result.linear_readback_bbox_min_x = x;
                            result.linear_readback_bbox_min_y = y;
                            result.linear_readback_bbox_max_x = x;
                            result.linear_readback_bbox_max_y = y;
                            result.linear_readback_bbox_found = 1U;
                        } else {
                            if (x < result.linear_readback_bbox_min_x) {
                                result.linear_readback_bbox_min_x = x;
                            }
                            if (y < result.linear_readback_bbox_min_y) {
                                result.linear_readback_bbox_min_y = y;
                            }
                            if (x > result.linear_readback_bbox_max_x) {
                                result.linear_readback_bbox_max_x = x;
                            }
                            if (y > result.linear_readback_bbox_max_y) {
                                result.linear_readback_bbox_max_y = y;
                            }
                        }
                    }
                    if (realframe_mode) {
                        if (rgb == GPU_D2_REALFRAME_DARK_RGB) {
                            result.texture_dark_count += 1U;
                        } else if (rgb == GPU_D2_REALFRAME_LIGHT_RGB) {
                            result.texture_light_count += 1U;
                        } else {
                            result.texture_other_count += 1U;
                        }
                    } else {
                        if (rgb == GPU_D1_CHECKER_DARK_RGB) {
                            result.texture_dark_count += 1U;
                        } else if (rgb == GPU_D1_CHECKER_LIGHT_RGB) {
                            result.texture_light_count += 1U;
                        } else {
                            result.texture_other_count += 1U;
                        }
                    }
                }
                result.color_flag0 = color_flag_words[0];
                for (index = 0; index < flag_word_count; ++index) {
                    if (color_flag_words[index] != 0) {
                        if (result.color_flag_changed_count == 0U) {
                            result.color_flag_first_changed_index = index;
                            result.color_flag_first_changed_value = color_flag_words[index];
                        }
                        result.color_flag_changed_count += 1U;
                    }
                }
                result.linear_readback0 = linear_words[0];
                result.linear_readback_center = linear_words[center_index];
                result.linear_center_nonzero =
                    result.linear_readback_center != GPU_H5_LINEAR_CLEAR_PATTERN ? 1U : 0U;
                result.linear_exterior_corners_zero =
                    (linear_words[0] != GPU_H5_LINEAR_CLEAR_PATTERN &&
                     linear_words[GPU_H2_COLOR_WIDTH - 1U] != GPU_H5_LINEAR_CLEAR_PATTERN &&
                     linear_words[(GPU_H2_COLOR_HEIGHT - 1U) * GPU_H2_COLOR_WIDTH] !=
                         GPU_H5_LINEAR_CLEAR_PATTERN &&
                     linear_words[(GPU_H2_COLOR_HEIGHT * GPU_H2_COLOR_WIDTH) - 1U] !=
                         GPU_H5_LINEAR_CLEAR_PATTERN) ? 1U : 0U;
                if (!realframe_mode) {
                    for (index = 0; index < GPU_D1_CHECKER_SAMPLE_COUNT; ++index) {
                        unsigned int sx = index % GPU_D1_CHECKER_SAMPLE_GRID;
                        unsigned int sy = index / GPU_D1_CHECKER_SAMPLE_GRID;
                        unsigned int x = (sx * GPU_D1_CHECKER_BLOCK) + (GPU_D1_CHECKER_BLOCK / 2U);
                        unsigned int y = (sy * GPU_D1_CHECKER_BLOCK) + (GPU_D1_CHECKER_BLOCK / 2U);
                        uint32_t expected = gpu_d1_checker_expected_rgb(x, y);
                        uint32_t value = linear_words[(y * GPU_D1_TEXTURE_WIDTH) + x] & 0x00ffffffU;

                        if (value == expected) {
                            result.texture_sample_match_count += 1U;
                        } else {
                            if (result.texture_sample_mismatch_count == 0U) {
                                result.texture_first_mismatch_index = index;
                                result.texture_first_mismatch_expected = expected;
                                result.texture_first_mismatch_value = value;
                            }
                            result.texture_sample_mismatch_count += 1U;
                        }
                    }
                }
                if (result.linear_readback_bbox_found == 1U &&
                    result.linear_readback_bbox_max_x >= result.linear_readback_bbox_min_x &&
                    result.linear_readback_bbox_max_y >= result.linear_readback_bbox_min_y) {
                    unsigned int bbox_width =
                        result.linear_readback_bbox_max_x - result.linear_readback_bbox_min_x + 1U;
                    unsigned int bbox_height =
                        result.linear_readback_bbox_max_y - result.linear_readback_bbox_min_y + 1U;

                    for (index = 0; index < GPU_D1_CHECKER_SAMPLE_COUNT; ++index) {
                        unsigned int sx = index % GPU_D1_CHECKER_SAMPLE_GRID;
                        unsigned int sy = index / GPU_D1_CHECKER_SAMPLE_GRID;
                        unsigned int x_offset = (unsigned int)(
                            (((uint64_t)((sx * 2U) + 1U)) * bbox_width) /
                            (2ULL * GPU_D1_CHECKER_SAMPLE_GRID));
                        unsigned int y_offset = (unsigned int)(
                            (((uint64_t)((sy * 2U) + 1U)) * bbox_height) /
                            (2ULL * GPU_D1_CHECKER_SAMPLE_GRID));
                        unsigned int x;
                        unsigned int y;
                        unsigned int tex_x;
                        unsigned int tex_y;
                        uint32_t expected;
                        uint32_t value;

                        if (x_offset >= bbox_width) {
                            x_offset = bbox_width - 1U;
                        }
                        if (y_offset >= bbox_height) {
                            y_offset = bbox_height - 1U;
                        }
                        x = result.linear_readback_bbox_min_x + x_offset;
                        y = result.linear_readback_bbox_min_y + y_offset;
                        tex_x = (unsigned int)(
                            (((uint64_t)x_offset) * texture_width +
                             (bbox_width / 2U)) / bbox_width);
                        tex_y = (unsigned int)(
                            (((uint64_t)y_offset) * texture_height +
                             (bbox_height / 2U)) / bbox_height);
                        if (tex_x >= texture_width) {
                            tex_x = texture_width - 1U;
                        }
                        if (tex_y >= texture_height) {
                            tex_y = texture_height - 1U;
                        }
                        expected = realframe_mode ?
                            gpu_d2_realframe_expected_rgb(realframe_frame,
                                                          &realframe_manifest,
                                                          tex_x,
                                                          tex_y) :
                            gpu_d1_checker_expected_rgb(tex_x, tex_y);
                        value = linear_words[(y * GPU_H2_COLOR_WIDTH) + x] & 0x00ffffffU;

                        result.texture_bbox_sample_count += 1U;
                        if (realframe_mode) {
                            result.realframe_bbox_sample_count += 1U;
                        }
                        if (value == expected) {
                            result.texture_bbox_sample_match_count += 1U;
                            if (realframe_mode) {
                                result.realframe_bbox_sample_match_count += 1U;
                            }
                        } else {
                            if (result.texture_bbox_sample_mismatch_count == 0U) {
                                result.texture_bbox_first_mismatch_index = index;
                                result.texture_bbox_first_mismatch_expected = expected;
                                result.texture_bbox_first_mismatch_value = value;
                            }
                            result.texture_bbox_sample_mismatch_count += 1U;
                            if (realframe_mode) {
                                if (result.realframe_bbox_sample_mismatch_count == 0U) {
                                    result.realframe_bbox_first_mismatch_index = index;
                                    result.realframe_bbox_first_mismatch_expected = expected;
                                    result.realframe_bbox_first_mismatch_value = value;
                                }
                                result.realframe_bbox_sample_mismatch_count += 1U;
                            }
                        }
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
#define GPU_D1_MUNMAP_FIELD(name) \
    do { \
        if (name##_map != MAP_FAILED) { \
            result.name##_munmap_attempted = 1; \
            errno = 0; \
            result.name##_munmap_rc = \
                munmap(name##_map, (size_t)result.name##_mmap_len) < 0 ? -1 : 0; \
            result.name##_munmap_errno = result.name##_munmap_rc < 0 ? errno : 0; \
        } \
    } while (0)
    GPU_D1_MUNMAP_FIELD(texture);
    GPU_D1_MUNMAP_FIELD(texmem);
    GPU_D1_MUNMAP_FIELD(sampler);
    GPU_D1_MUNMAP_FIELD(vertex);
    GPU_D1_MUNMAP_FIELD(fs);
    GPU_D1_MUNMAP_FIELD(vs);
    GPU_D1_MUNMAP_FIELD(linear);
    GPU_D1_MUNMAP_FIELD(color_flag);
    GPU_D1_MUNMAP_FIELD(color);
    GPU_D1_MUNMAP_FIELD(cmd);
#undef GPU_D1_MUNMAP_FIELD

#define GPU_D1_FREE_FIELD(name) \
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
    GPU_D1_FREE_FIELD(texture);
    GPU_D1_FREE_FIELD(texmem);
    GPU_D1_FREE_FIELD(sampler);
    GPU_D1_FREE_FIELD(vertex);
    GPU_D1_FREE_FIELD(fs);
    GPU_D1_FREE_FIELD(vs);
    GPU_D1_FREE_FIELD(event);
    GPU_D1_FREE_FIELD(linear);
    GPU_D1_FREE_FIELD(color_flag);
    GPU_D1_FREE_FIELD(color);
    GPU_D1_FREE_FIELD(cmd);
#undef GPU_D1_FREE_FIELD

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
    free(realframe_frame);
    result.total_elapsed_ms = monotonic_millis() - total_started_ms;
    (void)write_all_checked(write_fd, (const char *)&result, sizeof(result));
    close(write_fd);
    _exit(0);
}

static int gpu_d1_texture_checkerboard_probe(int timeout_ms, bool materialize_devnode) {
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
        a90_console_printf("gpu.d1.texture.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.d1.texture.version=1\r\n");
    a90_console_printf("gpu.d1.texture.scope=gpu-2d-d1-static-checkerboard-texture-readback\r\n");
    a90_console_printf("gpu.d1.texture.label=GPU BBOX CHECKERBOARD\r\n");
    a90_console_printf("gpu.d1.texture.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.d1.texture.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.d1.texture.wait_timeout_ms=%u\r\n", GPU_H3_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.d1.texture.source=v3304-fd6-texture-reference-plus-v3305-verified-textured-fs\r\n");
    a90_console_printf("gpu.d1.texture.shader_sha256=%s\r\n", GPU_D1_TEXTURED_FS_SHA256);
    a90_console_printf("gpu.d1.texture.command=gpu d1-texture-checkerboard-probe --timeout-ms 5000 --materialize-devnode\r\n");
    a90_console_printf("gpu.d1.texture.texture_size=%ux%u\r\n",
                       GPU_D1_TEXTURE_WIDTH, GPU_D1_TEXTURE_HEIGHT);
    a90_console_printf("gpu.d1.texture.texture_stride=%u\r\n", GPU_D1_TEXTURE_STRIDE);
    a90_console_printf("gpu.d1.texture.checker_block=%u\r\n", GPU_D1_CHECKER_BLOCK);
    a90_console_printf("gpu.d1.texture.sampler_desc_dwords=%u\r\n",
                       GPU_D1_SAMPLER_DESC_DWORDS);
    a90_console_printf("gpu.d1.texture.texmem_desc_dwords=%u\r\n",
                       GPU_D1_TEXMEMOBJ_DESC_DWORDS);
    a90_console_printf("gpu.d1.texture.sp_ps_config=0x%x\r\n",
                       GPU_D1_SP_PS_CONFIG_TEXTURED);
    a90_console_printf("gpu.d1.texture.sp_ps_cntl0=0x%x\r\n",
                       GPU_D1_SP_PS_CNTL_0);
    a90_console_printf("gpu.d1.texture.sp_ps_sampler_base_reg=0x%x\r\n",
                       GPU_D1_REG_SP_PS_SAMPLER_BASE);
    a90_console_printf("gpu.d1.texture.sp_ps_texmemobj_base_reg=0x%x\r\n",
                       GPU_D1_REG_SP_PS_TEXMEMOBJ_BASE);
    a90_console_printf("gpu.d1.texture.sp_ps_tsize_reg=0x%x\r\n",
                       GPU_D1_REG_SP_PS_TSIZE);
    a90_console_printf("gpu.d1.texture.viewport_scale_mode=inherited-default-clip-space-bbox\r\n");
    a90_console_printf("gpu.d1.texture.viewport_scale_xy=%u,%u\r\n",
                       GPU_D1_VIEWPORT_SCALE_X, GPU_D1_VIEWPORT_SCALE_Y);
    a90_console_printf("gpu.d1.texture.viewport_offset_xy=%u,%u\r\n",
                       GPU_D1_VIEWPORT_OFFSET_X, GPU_D1_VIEWPORT_OFFSET_Y);
    a90_console_printf("gpu.d1.texture.load_state6_sampler=frag-st6-shader-sb6-fs-tex-indirect\r\n");
    a90_console_printf("gpu.d1.texture.load_state6_texmem=frag-st6-constants-sb6-fs-tex-indirect\r\n");
    a90_console_printf("gpu.d1.texture.draw=clip-space-quad-6-auto-indexed-vertices\r\n");
    a90_console_printf("gpu.d1.texture.readback_gate=linearized-bbox-local-64-checker-samples\r\n");
    a90_console_printf("gpu.d1.texture.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.d1.texture.power_write_attempted=0\r\n");
    a90_console_printf("gpu.d1.texture.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.d1.texture.materialize_requested=1\r\n");
        a90_console_printf("gpu.d1.texture.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.d1.texture.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.d1.texture.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.d1.texture.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        const struct gpu_d1_texture_source_config config = {
            GPU_D1_TEXTURE_SOURCE_CHECKERBOARD,
            NULL,
            0U,
        };

        close(pipefd[0]);
        return gpu_d1_texture_probe_child(pipefd[1], &config);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.d1.texture.child_pid=%ld\r\n", (long)pid);

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

    a90_console_printf("gpu.d1.texture.result=%s\r\n",
                       got_result ? (gpu_d1_texture_checkerboard_result_passed(&result) ?
                                     "bbox-checkerboard-readback-pass" :
                                     "bbox-checkerboard-readback-failed") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.d1.texture.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.d1.texture.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.d1.texture.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.d1.texture.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.d1.texture.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.d1.texture.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.d1.texture.cmd_alloc_rc=%d\r\n", result.cmd_alloc_rc);
        a90_console_printf("gpu.d1.texture.color_alloc_rc=%d\r\n", result.color_alloc_rc);
        a90_console_printf("gpu.d1.texture.linear_alloc_rc=%d\r\n", result.linear_alloc_rc);
        a90_console_printf("gpu.d1.texture.sampler_alloc_rc=%d\r\n", result.sampler_alloc_rc);
        a90_console_printf("gpu.d1.texture.texmem_alloc_rc=%d\r\n", result.texmem_alloc_rc);
        a90_console_printf("gpu.d1.texture.texture_alloc_rc=%d\r\n", result.texture_alloc_rc);
        a90_console_printf("gpu.d1.texture.color_init_rc=%d\r\n", result.color_init_rc);
        a90_console_printf("gpu.d1.texture.shader_write_rc=%d\r\n", result.shader_write_rc);
        a90_console_printf("gpu.d1.texture.vertex_write_rc=%d\r\n", result.vertex_write_rc);
        a90_console_printf("gpu.d1.texture.texture_write_rc=%d\r\n", result.texture_write_rc);
        a90_console_printf("gpu.d1.texture.texture_desc_write_rc=%d\r\n",
                           result.texture_desc_write_rc);
        a90_console_printf("gpu.d1.texture.cmd_write_rc=%d\r\n", result.cmd_write_rc);
        a90_console_printf("gpu.d1.texture.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.d1.texture.state_reg_writes=%u\r\n",
                           result.state_reg_writes);
        a90_console_printf("gpu.d1.texture.vfd_reg_writes=%u\r\n",
                           result.vfd_reg_writes);
        a90_console_printf("gpu.d1.texture.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.d1.texture.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.d1.texture.submit_errno=%d\r\n", result.submit_errno);
        a90_console_printf("gpu.d1.texture.submit_timestamp=%u\r\n",
                           result.submit_timestamp);
        a90_console_printf("gpu.d1.texture.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.d1.texture.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.d1.texture.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.d1.texture.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.d1.texture.readback_sync_errno=%d\r\n",
                           result.readback_sync_errno);
        a90_console_printf("gpu.d1.texture.readback_changed_count=%u\r\n",
                           result.readback_changed_count);
        a90_console_printf("gpu.d1.texture.linear_readback_changed_count=%u\r\n",
                           result.linear_readback_changed_count);
        a90_console_printf("gpu.d1.texture.linear_readback_nonzero_count=%u\r\n",
                           result.linear_readback_nonzero_count);
        a90_console_printf("gpu.d1.texture.linear_readback0=0x%x\r\n",
                           result.linear_readback0);
        a90_console_printf("gpu.d1.texture.linear_readback_center=0x%x\r\n",
                           result.linear_readback_center);
        a90_console_printf("gpu.d1.texture.linear_readback_bbox_found=%u\r\n",
                           result.linear_readback_bbox_found);
        a90_console_printf("gpu.d1.texture.linear_readback_bbox=%u,%u,%u,%u\r\n",
                           result.linear_readback_bbox_min_x,
                           result.linear_readback_bbox_min_y,
                           result.linear_readback_bbox_max_x,
                           result.linear_readback_bbox_max_y);
        a90_console_printf("gpu.d1.texture.texture_dark_count=%u\r\n",
                           result.texture_dark_count);
        a90_console_printf("gpu.d1.texture.texture_light_count=%u\r\n",
                           result.texture_light_count);
        a90_console_printf("gpu.d1.texture.texture_other_count=%u\r\n",
                           result.texture_other_count);
        a90_console_printf("gpu.d1.texture.texture_sample_count=%u\r\n",
                           result.texture_sample_count);
        a90_console_printf("gpu.d1.texture.texture_sample_match_count=%u\r\n",
                           result.texture_sample_match_count);
        a90_console_printf("gpu.d1.texture.texture_sample_mismatch_count=%u\r\n",
                           result.texture_sample_mismatch_count);
        a90_console_printf("gpu.d1.texture.texture_first_mismatch_index=%u\r\n",
                           result.texture_first_mismatch_index);
        a90_console_printf("gpu.d1.texture.texture_first_mismatch_expected=0x%x\r\n",
                           result.texture_first_mismatch_expected);
        a90_console_printf("gpu.d1.texture.texture_first_mismatch_value=0x%x\r\n",
                           result.texture_first_mismatch_value);
        a90_console_printf("gpu.d1.texture.texture_bbox_sample_count=%u\r\n",
                           result.texture_bbox_sample_count);
        a90_console_printf("gpu.d1.texture.texture_bbox_sample_match_count=%u\r\n",
                           result.texture_bbox_sample_match_count);
        a90_console_printf("gpu.d1.texture.texture_bbox_sample_mismatch_count=%u\r\n",
                           result.texture_bbox_sample_mismatch_count);
        a90_console_printf("gpu.d1.texture.texture_bbox_first_mismatch_index=%u\r\n",
                           result.texture_bbox_first_mismatch_index);
        a90_console_printf("gpu.d1.texture.texture_bbox_first_mismatch_expected=0x%x\r\n",
                           result.texture_bbox_first_mismatch_expected);
        a90_console_printf("gpu.d1.texture.texture_bbox_first_mismatch_value=0x%x\r\n",
                           result.texture_bbox_first_mismatch_value);
        a90_console_printf("gpu.d1.texture.cmd_free_rc=%d\r\n", result.cmd_free_rc);
        a90_console_printf("gpu.d1.texture.color_free_rc=%d\r\n", result.color_free_rc);
        a90_console_printf("gpu.d1.texture.linear_free_rc=%d\r\n", result.linear_free_rc);
        a90_console_printf("gpu.d1.texture.sampler_free_rc=%d\r\n", result.sampler_free_rc);
        a90_console_printf("gpu.d1.texture.texmem_free_rc=%d\r\n", result.texmem_free_rc);
        a90_console_printf("gpu.d1.texture.texture_free_rc=%d\r\n", result.texture_free_rc);
        a90_console_printf("gpu.d1.texture.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.d1.texture.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.d1.texture.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    if (timed_out) {
        return -ETIMEDOUT;
    }
    return got_result && gpu_d1_texture_checkerboard_result_passed(&result) ? 0 : -EIO;
}

static int gpu_d2_realframe_texture_probe(int timeout_ms,
                                          bool materialize_devnode,
                                          const char *manifest_path,
                                          uint32_t frame_index) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_h3_draw_envelope_probe_result result;
    const char *effective_manifest =
        manifest_path != NULL ? manifest_path : GPU_D2_REALFRAME_BADAPPLE_MANIFEST_PATH;
    struct gpu_d1_texture_source_config config = {
        GPU_D1_TEXTURE_SOURCE_REALFRAME_MONO1,
        effective_manifest,
        frame_index,
    };

    memset(&result, 0, sizeof(result));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.d2.realframe.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    a90_console_printf("gpu.d2.realframe.version=1\r\n");
    a90_console_printf("gpu.d2.realframe.scope=gpu-2d-d2-realframe-sd-cache-texture-readback\r\n");
    a90_console_printf("gpu.d2.realframe.label=GPU REALFRAME BADAPPLE\r\n");
    a90_console_printf("gpu.d2.realframe.path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.d2.realframe.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.d2.realframe.wait_timeout_ms=%u\r\n", GPU_H3_WAIT_TIMEOUT_MS);
    a90_console_printf("gpu.d2.realframe.source=sd-cache-badapple-mono1-v2903-frame-to-rgba8-texture\r\n");
    a90_console_printf("gpu.d2.realframe.shader_sha256=%s\r\n", GPU_D1_TEXTURED_FS_SHA256);
    a90_console_printf("gpu.d2.realframe.command=gpu d2-realframe-texture-probe --preset badapple --frame-index %u --timeout-ms 5000 --materialize-devnode\r\n",
                       frame_index);
    a90_console_printf("gpu.d2.realframe.preset=badapple\r\n");
    a90_console_printf("gpu.d2.realframe.manifest=%s\r\n", effective_manifest);
    a90_console_printf("gpu.d2.realframe.frame_index=%u\r\n", frame_index);
    a90_console_printf("gpu.d2.realframe.output_size=%ux%u\r\n",
                       GPU_H2_COLOR_WIDTH, GPU_H2_COLOR_HEIGHT);
    a90_console_printf("gpu.d2.realframe.sampler_desc_dwords=%u\r\n",
                       GPU_D1_SAMPLER_DESC_DWORDS);
    a90_console_printf("gpu.d2.realframe.texmem_desc_dwords=%u\r\n",
                       GPU_D1_TEXMEMOBJ_DESC_DWORDS);
    a90_console_printf("gpu.d2.realframe.sp_ps_config=0x%x\r\n",
                       GPU_D1_SP_PS_CONFIG_TEXTURED);
    a90_console_printf("gpu.d2.realframe.sp_ps_cntl0=0x%x\r\n",
                       GPU_D1_SP_PS_CNTL_0);
    a90_console_printf("gpu.d2.realframe.viewport_scale_mode=inherited-default-clip-space-bbox\r\n");
    a90_console_printf("gpu.d2.realframe.load_state6_sampler=frag-st6-shader-sb6-fs-tex-indirect\r\n");
    a90_console_printf("gpu.d2.realframe.load_state6_texmem=frag-st6-constants-sb6-fs-tex-indirect\r\n");
    a90_console_printf("gpu.d2.realframe.draw=clip-space-quad-6-auto-indexed-vertices\r\n");
    a90_console_printf("gpu.d2.realframe.readback_gate=linearized-bbox-local-64-realframe-samples\r\n");
    a90_console_printf("gpu.d2.realframe.kms_blit_attempted=0\r\n");
    a90_console_printf("gpu.d2.realframe.power_write_attempted=0\r\n");
    a90_console_printf("gpu.d2.realframe.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.d2.realframe.materialize_requested=1\r\n");
        a90_console_printf("gpu.d2.realframe.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.d2.realframe.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.d2.realframe.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.d2.realframe.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        close(pipefd[0]);
        return gpu_d1_texture_probe_child(pipefd[1], &config);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.d2.realframe.child_pid=%ld\r\n", (long)pid);

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

    a90_console_printf("gpu.d2.realframe.result=%s\r\n",
                       got_result ? (gpu_d2_realframe_texture_result_passed(&result) ?
                                     "realframe-texture-readback-pass" :
                                     "realframe-texture-readback-failed") :
                       (timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.d2.realframe.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.d2.realframe.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.d2.realframe.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.d2.realframe.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.d2.realframe.manifest_rc=%d\r\n",
                           result.realframe_manifest_rc);
        a90_console_printf("gpu.d2.realframe.open_stream_rc=%d errno=%d\r\n",
                           result.realframe_open_rc,
                           result.realframe_open_errno);
        a90_console_printf("gpu.d2.realframe.header_rc=%d\r\n",
                           result.realframe_header_rc);
        a90_console_printf("gpu.d2.realframe.record_rc=%d\r\n",
                           result.realframe_record_rc);
        a90_console_printf("gpu.d2.realframe.read_rc=%d\r\n",
                           result.realframe_read_rc);
        a90_console_printf("gpu.d2.realframe.close_stream_rc=%d errno=%d\r\n",
                           result.realframe_close_rc,
                           result.realframe_close_errno);
        a90_console_printf("gpu.d2.realframe.requested_frame_index=%u\r\n",
                           result.realframe_requested_frame_index);
        a90_console_printf("gpu.d2.realframe.record_index=%u\r\n",
                           result.realframe_record_index);
        a90_console_printf("gpu.d2.realframe.payload_bytes=%u\r\n",
                           result.realframe_payload_bytes);
        a90_console_printf("gpu.d2.realframe.source_size=%ux%u\r\n",
                           result.realframe_width,
                           result.realframe_height);
        a90_console_printf("gpu.d2.realframe.source_stride=%u\r\n",
                           result.realframe_stride);
        a90_console_printf("gpu.d2.realframe.source_frame_bytes=%u\r\n",
                           result.realframe_frame_bytes);
        a90_console_printf("gpu.d2.realframe.source_dark_count=%u\r\n",
                           result.realframe_source_dark_count);
        a90_console_printf("gpu.d2.realframe.source_light_count=%u\r\n",
                           result.realframe_source_light_count);
        a90_console_printf("gpu.d2.realframe.source_other_count=%u\r\n",
                           result.realframe_source_other_count);
        a90_console_printf("gpu.d2.realframe.open_rc=%d\r\n", result.open_rc);
        a90_console_printf("gpu.d2.realframe.create_rc=%d\r\n", result.create_rc);
        a90_console_printf("gpu.d2.realframe.texture_alloc_rc=%d\r\n",
                           result.texture_alloc_rc);
        a90_console_printf("gpu.d2.realframe.texture_size=%ux%u\r\n",
                           result.texture_width,
                           result.texture_height);
        a90_console_printf("gpu.d2.realframe.texture_stride=%u\r\n",
                           result.texture_stride);
        a90_console_printf("gpu.d2.realframe.texture_bytes=%u\r\n",
                           result.texture_bytes);
        a90_console_printf("gpu.d2.realframe.texture_write_rc=%d\r\n",
                           result.texture_write_rc);
        a90_console_printf("gpu.d2.realframe.texture_desc_write_rc=%d\r\n",
                           result.texture_desc_write_rc);
        a90_console_printf("gpu.d2.realframe.cmd_write_rc=%d\r\n",
                           result.cmd_write_rc);
        a90_console_printf("gpu.d2.realframe.pm4_dwords=%u\r\n", result.pm4_dwords);
        a90_console_printf("gpu.d2.realframe.sync_rc=%d\r\n", result.sync_rc);
        a90_console_printf("gpu.d2.realframe.submit_rc=%d\r\n", result.submit_rc);
        a90_console_printf("gpu.d2.realframe.submit_errno=%d\r\n",
                           result.submit_errno);
        a90_console_printf("gpu.d2.realframe.submit_timestamp=%u\r\n",
                           result.submit_timestamp);
        a90_console_printf("gpu.d2.realframe.wait_rc=%d\r\n", result.wait_rc);
        a90_console_printf("gpu.d2.realframe.wait_errno=%d\r\n", result.wait_errno);
        a90_console_printf("gpu.d2.realframe.retired_timestamp=%u\r\n",
                           result.retired_timestamp);
        a90_console_printf("gpu.d2.realframe.readback_sync_rc=%d\r\n",
                           result.readback_sync_rc);
        a90_console_printf("gpu.d2.realframe.linear_readback_changed_count=%u\r\n",
                           result.linear_readback_changed_count);
        a90_console_printf("gpu.d2.realframe.linear_readback_bbox_found=%u\r\n",
                           result.linear_readback_bbox_found);
        a90_console_printf("gpu.d2.realframe.linear_readback_bbox=%u,%u,%u,%u\r\n",
                           result.linear_readback_bbox_min_x,
                           result.linear_readback_bbox_min_y,
                           result.linear_readback_bbox_max_x,
                           result.linear_readback_bbox_max_y);
        a90_console_printf("gpu.d2.realframe.output_dark_count=%u\r\n",
                           result.texture_dark_count);
        a90_console_printf("gpu.d2.realframe.output_light_count=%u\r\n",
                           result.texture_light_count);
        a90_console_printf("gpu.d2.realframe.output_other_count=%u\r\n",
                           result.texture_other_count);
        a90_console_printf("gpu.d2.realframe.texture_bbox_sample_count=%u\r\n",
                           result.texture_bbox_sample_count);
        a90_console_printf("gpu.d2.realframe.texture_bbox_sample_match_count=%u\r\n",
                           result.texture_bbox_sample_match_count);
        a90_console_printf("gpu.d2.realframe.texture_bbox_sample_mismatch_count=%u\r\n",
                           result.texture_bbox_sample_mismatch_count);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_sample_count=%u\r\n",
                           result.realframe_bbox_sample_count);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_sample_match_count=%u\r\n",
                           result.realframe_bbox_sample_match_count);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_sample_mismatch_count=%u\r\n",
                           result.realframe_bbox_sample_mismatch_count);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_first_mismatch_index=%u\r\n",
                           result.realframe_bbox_first_mismatch_index);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_first_mismatch_expected=0x%x\r\n",
                           result.realframe_bbox_first_mismatch_expected);
        a90_console_printf("gpu.d2.realframe.realframe_bbox_first_mismatch_value=0x%x\r\n",
                           result.realframe_bbox_first_mismatch_value);
        a90_console_printf("gpu.d2.realframe.destroy_rc=%d\r\n", result.destroy_rc);
        a90_console_printf("gpu.d2.realframe.close_rc=%d\r\n", result.close_rc);
        a90_console_printf("gpu.d2.realframe.total_elapsed_ms=%ld\r\n",
                           result.total_elapsed_ms);
    }
    if (timed_out) {
        return -ETIMEDOUT;
    }
    return got_result && gpu_d2_realframe_texture_result_passed(&result) ? 0 : -EIO;
}

struct gpu_d3_bo {
    struct gpu_kgsl_gpuobj_alloc alloc;
    struct gpu_kgsl_gpuobj_info info;
    void *map;
};

struct gpu_d3_session {
    int fd;
    unsigned int context_id;
    struct gpu_d3_bo cmd;
    struct gpu_d3_bo color;
    struct gpu_d3_bo color_flag;
    struct gpu_d3_bo linear;
    struct gpu_d3_bo event;
    struct gpu_d3_bo vs;
    struct gpu_d3_bo fs;
    struct gpu_d3_bo vertex;
    struct gpu_d3_bo sampler;
    struct gpu_d3_bo texmem;
    struct gpu_d3_bo texture;
    uint64_t cmd_size;
    uint32_t pm4_dwords;
    uint32_t target_width;
    uint32_t target_height;
    uint32_t target_stride;
    uint64_t target_bytes;
    uint32_t texture_width;
    uint32_t texture_height;
    uint32_t texture_stride;
    uint64_t texture_bytes;
};

static void gpu_d3_bo_init(struct gpu_d3_bo *bo) {
    if (bo == NULL) {
        return;
    }
    memset(bo, 0, sizeof(*bo));
    bo->map = MAP_FAILED;
}

static void gpu_d3_session_init(struct gpu_d3_session *session) {
    if (session == NULL) {
        return;
    }
    memset(session, 0, sizeof(*session));
    session->fd = -1;
    gpu_d3_bo_init(&session->cmd);
    gpu_d3_bo_init(&session->color);
    gpu_d3_bo_init(&session->color_flag);
    gpu_d3_bo_init(&session->linear);
    gpu_d3_bo_init(&session->event);
    gpu_d3_bo_init(&session->vs);
    gpu_d3_bo_init(&session->fs);
    gpu_d3_bo_init(&session->vertex);
    gpu_d3_bo_init(&session->sampler);
    gpu_d3_bo_init(&session->texmem);
    gpu_d3_bo_init(&session->texture);
}

static int gpu_d3_alloc_map_bo(int fd,
                               struct gpu_d3_bo *bo,
                               uint64_t size,
                               uint64_t min_size) {
    uint64_t mmap_offset;

    if (fd < 0 || bo == NULL || size == 0U || min_size == 0U) {
        return -EINVAL;
    }
    memset(&bo->alloc, 0, sizeof(bo->alloc));
    bo->alloc.size = size;
    bo->alloc.flags = GPU_G4_ALLOC_FLAGS;
    errno = 0;
    if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_ALLOC, &bo->alloc) < 0) {
        return negative_errno_or(EIO);
    }
    memset(&bo->info, 0, sizeof(bo->info));
    bo->info.id = bo->alloc.id;
    errno = 0;
    if (ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_INFO, &bo->info) < 0) {
        return negative_errno_or(EIO);
    }
    mmap_offset = (uint64_t)bo->alloc.id * GPU_G2_MMAP_PAGE_SIZE;
    if (bo->alloc.mmapsize < min_size ||
        mmap_offset / GPU_G2_MMAP_PAGE_SIZE != (uint64_t)bo->alloc.id) {
        return -EINVAL;
    }
    errno = 0;
    bo->map = mmap(NULL,
                   (size_t)bo->alloc.mmapsize,
                   PROT_READ | PROT_WRITE,
                   MAP_SHARED,
                   fd,
                   (off_t)mmap_offset);
    if (bo->map == MAP_FAILED) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void gpu_d3_unmap_free_bo(int fd, struct gpu_d3_bo *bo) {
    if (bo == NULL) {
        return;
    }
    if (bo->map != NULL && bo->map != MAP_FAILED && bo->alloc.mmapsize > 0U) {
        (void)munmap(bo->map, (size_t)bo->alloc.mmapsize);
        bo->map = MAP_FAILED;
    }
    if (fd >= 0 && bo->alloc.id != 0U) {
        struct gpu_kgsl_gpuobj_free free_arg;

        memset(&free_arg, 0, sizeof(free_arg));
        free_arg.id = bo->alloc.id;
        (void)ioctl(fd, GPU_IOCTL_KGSL_GPUOBJ_FREE, &free_arg);
        bo->alloc.id = 0U;
    }
}

static void gpu_d3_destroy_session(struct gpu_d3_session *session) {
    if (session == NULL) {
        return;
    }
    if (session->fd >= 0) {
        gpu_d3_unmap_free_bo(session->fd, &session->texture);
        gpu_d3_unmap_free_bo(session->fd, &session->texmem);
        gpu_d3_unmap_free_bo(session->fd, &session->sampler);
        gpu_d3_unmap_free_bo(session->fd, &session->vertex);
        gpu_d3_unmap_free_bo(session->fd, &session->fs);
        gpu_d3_unmap_free_bo(session->fd, &session->vs);
        gpu_d3_unmap_free_bo(session->fd, &session->event);
        gpu_d3_unmap_free_bo(session->fd, &session->linear);
        gpu_d3_unmap_free_bo(session->fd, &session->color_flag);
        gpu_d3_unmap_free_bo(session->fd, &session->color);
        gpu_d3_unmap_free_bo(session->fd, &session->cmd);
        if (session->context_id != 0U) {
            struct gpu_kgsl_drawctxt_destroy destroy_arg;

            memset(&destroy_arg, 0, sizeof(destroy_arg));
            destroy_arg.drawctxt_id = session->context_id;
            (void)ioctl(session->fd, GPU_IOCTL_KGSL_DRAWCTXT_DESTROY, &destroy_arg);
            session->context_id = 0U;
        }
        (void)close(session->fd);
        session->fd = -1;
    }
}

static int gpu_d3_create_session(struct gpu_d3_session *session,
                                 const struct video_stream_manifest *manifest,
                                 struct gpu_d3_video_summary *summary) {
    static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS] = {
        GPU_H3_IR3_MOV_F32F32_R2X_R1X_LO, GPU_H3_IR3_MOV_F32F32_R2X_R1X_HI,
        GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_LO, GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_HI,
        GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_LO, GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_HI,
        GPU_H3_IR3_MOV_F32F32_R2W_R1W_LO, GPU_H3_IR3_MOV_F32F32_R2W_R1W_HI,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t fs_shader[GPU_D1_FS_SHADER_DWORDS] = {
        0x00002000U, 0x47300000U,
        0x00002001U, 0x47300001U,
        0x00000001U, 0xa0c01f02U,
        GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI,
    };
    static const uint32_t vertex_words[GPU_D1_VERTEX_DWORDS] = {
        0xbf800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0xbf800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0xbf800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x00000000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0x3f800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x3f800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
        0xbf800000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U, 0x3f800000U, 0x00000000U, 0x3f800000U,
        0x00000000U,
    };
    struct gpu_kgsl_drawctxt_create create_arg;
    unsigned int state_reg_writes = 0;
    unsigned int vfd_reg_writes = 0;
    int rc;

    if (session == NULL || manifest == NULL || summary == NULL ||
        manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 ||
        manifest->width == 0U || manifest->height == 0U ||
        manifest->stride < (manifest->width + 7U) / 8U) {
        return -EINVAL;
    }
    gpu_d3_session_init(session);
    session->texture_width = manifest->width;
    session->texture_height = manifest->height;
    session->texture_stride = manifest->width * GPU_D1_TEXTURE_BPP;
    session->texture_bytes = (uint64_t)session->texture_stride * session->texture_height;
    session->target_width = manifest->width * VIDEO_PLAYER_HUD_SCALE;
    session->target_height = manifest->height * VIDEO_PLAYER_HUD_SCALE;
    session->target_stride = session->target_width * GPU_D3_VIDEO_TARGET_BPP;
    session->target_bytes = (uint64_t)session->target_stride * session->target_height;
    if (session->texture_bytes == 0U ||
        session->texture_bytes > GPU_D2_REALFRAME_MAX_TEXTURE_BYTES ||
        session->target_width != GPU_D3_VIDEO_TARGET_WIDTH ||
        session->target_height != GPU_D3_VIDEO_TARGET_HEIGHT ||
        session->target_stride != GPU_D3_VIDEO_TARGET_STRIDE ||
        session->target_bytes != GPU_D3_VIDEO_TARGET_BYTES) {
        return -EINVAL;
    }

    errno = 0;
    session->fd = open(GPU_G0_DEVNODE, O_RDWR | O_CLOEXEC);
    if (session->fd < 0) {
        return negative_errno_or(EIO);
    }
    memset(&create_arg, 0, sizeof(create_arg));
    create_arg.flags = GPU_G1_CONTEXT_FLAGS;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_DRAWCTXT_CREATE, &create_arg) < 0) {
        return negative_errno_or(EIO);
    }
    session->context_id = create_arg.drawctxt_id;

    rc = gpu_d3_alloc_map_bo(session->fd, &session->cmd, GPU_H3_CMD_ALLOC_SIZE,
                             (uint64_t)GPU_G4_CMD_MAX_DWORDS * 4ULL);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->color,
                             session->target_bytes, session->target_bytes);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->color_flag,
                             GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE,
                             GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->linear,
                             session->target_bytes, session->target_bytes);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->event,
                             GPU_H3_EVENT_ALLOC_SIZE, GPU_H3_EVENT_ALLOC_SIZE);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->vs,
                             GPU_H1_SHADER_ALLOC_SIZE, sizeof(vs_shader));
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->fs,
                             GPU_H1_SHADER_ALLOC_SIZE, sizeof(fs_shader));
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->vertex,
                             GPU_H3_VERTEX_ALLOC_SIZE, GPU_D1_VERTEX_BYTES);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->sampler,
                             GPU_D1_DESCRIPTOR_ALLOC_SIZE,
                             GPU_D1_SAMPLER_DESC_DWORDS * 4ULL);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->texmem,
                             GPU_D1_DESCRIPTOR_ALLOC_SIZE,
                             GPU_D1_TEXMEMOBJ_DESC_DWORDS * 4ULL);
    if (rc < 0) return rc;
    rc = gpu_d3_alloc_map_bo(session->fd, &session->texture,
                             gpu_d1_round_up_u64(session->texture_bytes, 4096ULL),
                             session->texture_bytes);
    if (rc < 0) return rc;

    memset(session->color.map, 0, (size_t)session->target_bytes);
    memset(session->color_flag.map, 0, (size_t)GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE);
    memset(session->linear.map, 0, (size_t)session->target_bytes);
    memcpy(session->vs.map, vs_shader, sizeof(vs_shader));
    memcpy(session->fs.map, fs_shader, sizeof(fs_shader));
    memcpy(session->vertex.map, vertex_words, sizeof(vertex_words));
    gpu_d1_write_sampler_descriptor((uint32_t *)session->sampler.map);
    gpu_d1_write_texture_descriptor_ex((uint32_t *)session->texmem.map,
                                       session->texture.info.gpuaddr,
                                       session->texture_width,
                                       session->texture_height,
                                       session->texture_stride,
                                       session->texture_bytes);
    memset(session->cmd.map, 0, (size_t)session->cmd.alloc.mmapsize);
    if (!gpu_d3_build_texture_video_pm4((uint32_t *)session->cmd.map,
                                        &session->pm4_dwords,
                                        &state_reg_writes,
                                        &vfd_reg_writes,
                                        session->color.info.gpuaddr,
                                        session->color_flag.info.gpuaddr,
                                        session->linear.info.gpuaddr,
                                        session->event.info.gpuaddr,
                                        session->vs.info.gpuaddr,
                                        session->fs.info.gpuaddr,
                                        session->vertex.info.gpuaddr,
                                        session->sampler.info.gpuaddr,
                                        session->texmem.info.gpuaddr,
                                        session->target_width,
                                        session->target_height,
                                        session->target_stride,
                                        session->target_bytes)) {
        return -EIO;
    }
    session->cmd_size = (uint64_t)session->pm4_dwords * 4ULL;
    summary->gpu_create_rc = 0;
    summary->pm4_dwords = session->pm4_dwords;
    summary->target_width = session->target_width;
    summary->target_height = session->target_height;
    summary->target_stride = session->target_stride;
    summary->target_bytes = (uint32_t)session->target_bytes;
    __sync_synchronize();
    return 0;
}

static void gpu_d3_write_mono1_texture(uint32_t *texture_words,
                                       const uint8_t *frame,
                                       const struct video_stream_manifest *manifest,
                                       struct gpu_d3_video_frame_stats *stats) {
    uint32_t y;

    if (texture_words == NULL || frame == NULL || manifest == NULL) {
        return;
    }
    for (y = 0; y < manifest->height; ++y) {
        uint32_t x;

        for (x = 0; x < manifest->width; ++x) {
            bool bit = gpu_d2_mono1_bit(frame, manifest, x, y);

            texture_words[((size_t)y * manifest->width) + x] =
                bit ? GPU_D2_REALFRAME_LIGHT_WORD : GPU_D2_REALFRAME_DARK_WORD;
            if (stats != NULL) {
                if (bit) {
                    stats->semantic_source_light_count += 1U;
                } else {
                    stats->semantic_source_dark_count += 1U;
                }
            }
        }
    }
}

static int gpu_d3_sync_to_gpu(struct gpu_d3_session *session) {
    struct gpu_kgsl_gpuobj_sync_obj sync_objs[11];
    struct gpu_kgsl_gpuobj_sync sync_arg;

    if (session == NULL || session->fd < 0) {
        return -EINVAL;
    }
    memset(sync_objs, 0, sizeof(sync_objs));
    sync_objs[0].id = session->cmd.alloc.id;
    sync_objs[0].length = session->cmd_size;
    sync_objs[0].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[1].id = session->color.alloc.id;
    sync_objs[1].length = session->target_bytes;
    sync_objs[1].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[2].id = session->color_flag.alloc.id;
    sync_objs[2].length = GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE;
    sync_objs[2].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[3].id = session->linear.alloc.id;
    sync_objs[3].length = session->target_bytes;
    sync_objs[3].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[4].id = session->event.alloc.id;
    sync_objs[4].length = GPU_H3_EVENT_ALLOC_SIZE;
    sync_objs[4].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[5].id = session->vs.alloc.id;
    sync_objs[5].length = GPU_H1_SHADER_ALLOC_SIZE;
    sync_objs[5].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[6].id = session->fs.alloc.id;
    sync_objs[6].length = GPU_H1_SHADER_ALLOC_SIZE;
    sync_objs[6].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[7].id = session->vertex.alloc.id;
    sync_objs[7].length = GPU_D1_VERTEX_BYTES;
    sync_objs[7].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[8].id = session->sampler.alloc.id;
    sync_objs[8].length = GPU_D1_SAMPLER_DESC_DWORDS * 4ULL;
    sync_objs[8].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[9].id = session->texmem.alloc.id;
    sync_objs[9].length = GPU_D1_TEXMEMOBJ_DESC_DWORDS * 4ULL;
    sync_objs[9].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    sync_objs[10].id = session->texture.alloc.id;
    sync_objs[10].length = session->texture_bytes;
    sync_objs[10].op = GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    memset(&sync_arg, 0, sizeof(sync_arg));
    sync_arg.objs = (uint64_t)(uintptr_t)sync_objs;
    sync_arg.obj_len = sizeof(sync_objs[0]);
    sync_arg.count = 11U;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int gpu_d3_sync_linear_from_gpu(struct gpu_d3_session *session) {
    struct gpu_kgsl_gpuobj_sync_obj sync_obj;
    struct gpu_kgsl_gpuobj_sync sync_arg;

    if (session == NULL || session->fd < 0) {
        return -EINVAL;
    }
    memset(&sync_obj, 0, sizeof(sync_obj));
    sync_obj.id = session->linear.alloc.id;
    sync_obj.length = session->target_bytes;
    sync_obj.op = GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE;
    memset(&sync_arg, 0, sizeof(sync_arg));
    sync_arg.objs = (uint64_t)(uintptr_t)&sync_obj;
    sync_arg.obj_len = sizeof(sync_obj);
    sync_arg.count = 1U;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_GPUOBJ_SYNC, &sync_arg) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int gpu_d3_submit_wait(struct gpu_d3_session *session,
                              struct gpu_d3_video_frame_stats *stats) {
    struct gpu_kgsl_command_object cmd_obj;
    struct gpu_kgsl_command_object mem_objs[11];
    struct gpu_kgsl_gpu_command command_arg;
    struct gpu_kgsl_device_waittimestamp_ctxtid wait_arg;
    struct gpu_kgsl_cmdstream_readtimestamp_ctxtid read_arg;

    if (session == NULL || stats == NULL || session->fd < 0) {
        return -EINVAL;
    }
    memset(&cmd_obj, 0, sizeof(cmd_obj));
    cmd_obj.gpuaddr = session->cmd.info.gpuaddr;
    cmd_obj.size = session->cmd_size;
    cmd_obj.flags = GPU_KGSL_CMDLIST_IB;
    cmd_obj.id = session->cmd.alloc.id;

    memset(mem_objs, 0, sizeof(mem_objs));
#define GPU_D3_MEMOBJ(slot, field) \
    do { \
        mem_objs[(slot)].gpuaddr = session->field.info.gpuaddr; \
        mem_objs[(slot)].size = session->field.info.size; \
        mem_objs[(slot)].flags = GPU_KGSL_OBJLIST_MEMOBJ; \
        mem_objs[(slot)].id = session->field.alloc.id; \
    } while (0)
    GPU_D3_MEMOBJ(0, cmd);
    GPU_D3_MEMOBJ(1, color);
    GPU_D3_MEMOBJ(2, color_flag);
    GPU_D3_MEMOBJ(3, linear);
    GPU_D3_MEMOBJ(4, event);
    GPU_D3_MEMOBJ(5, vs);
    GPU_D3_MEMOBJ(6, fs);
    GPU_D3_MEMOBJ(7, vertex);
    GPU_D3_MEMOBJ(8, sampler);
    GPU_D3_MEMOBJ(9, texmem);
    GPU_D3_MEMOBJ(10, texture);
#undef GPU_D3_MEMOBJ

    memset(&command_arg, 0, sizeof(command_arg));
    command_arg.cmdlist = (uint64_t)(uintptr_t)&cmd_obj;
    command_arg.cmdsize = sizeof(cmd_obj);
    command_arg.numcmds = 1;
    command_arg.objlist = (uint64_t)(uintptr_t)mem_objs;
    command_arg.objsize = sizeof(mem_objs[0]);
    command_arg.numobjs = 11U;
    command_arg.context_id = session->context_id;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_GPU_COMMAND, &command_arg) < 0) {
        stats->submit_rc = negative_errno_or(EIO);
        return stats->submit_rc;
    }
    stats->submit_rc = 0;
    stats->submit_timestamp = command_arg.timestamp;

    memset(&wait_arg, 0, sizeof(wait_arg));
    wait_arg.context_id = session->context_id;
    wait_arg.timestamp = command_arg.timestamp;
    wait_arg.timeout = GPU_H3_WAIT_TIMEOUT_MS;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID, &wait_arg) < 0) {
        stats->wait_rc = negative_errno_or(EIO);
        return stats->wait_rc;
    }
    stats->wait_rc = 0;

    memset(&read_arg, 0, sizeof(read_arg));
    read_arg.context_id = session->context_id;
    read_arg.type = GPU_KGSL_TIMESTAMP_RETIRED;
    errno = 0;
    if (ioctl(session->fd, GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID, &read_arg) < 0) {
        return negative_errno_or(EIO);
    }
    stats->retired_timestamp = read_arg.timestamp;
    return 0;
}

static int gpu_d3_copy_linear_to_kms(struct gpu_d3_session *session,
                                     struct a90_fb *fb,
                                     uint32_t dst_x,
                                     uint32_t dst_y,
                                     struct gpu_d3_video_frame_stats *stats) {
    const uint8_t *src;
    uint32_t y;

    if (session == NULL || fb == NULL || fb->pixels == NULL ||
        fb->pixels == MAP_FAILED || stats == NULL ||
        dst_x > fb->width || dst_y > fb->height ||
        session->target_width > fb->width - dst_x ||
        session->target_height > fb->height - dst_y ||
        fb->stride < (uint64_t)fb->width * 4ULL) {
        return -EINVAL;
    }
    src = (const uint8_t *)session->linear.map;
    for (y = 0; y < session->target_height; ++y) {
        void *dst = (char *)fb->pixels +
                    ((uint64_t)(dst_y + y) * fb->stride) +
                    ((uint64_t)dst_x * sizeof(uint32_t));

        memcpy(dst, src + ((uint64_t)y * session->target_stride),
               (size_t)session->target_width * sizeof(uint32_t));
    }
    {
        const uint32_t *words = (const uint32_t *)session->linear.map;
        uint32_t center =
            (session->target_height / 2U) * session->target_width +
            (session->target_width / 2U);
        uint64_t count = (uint64_t)session->target_width * session->target_height;
        uint64_t index;

        stats->first_word = words[0];
        stats->center_word = words[center];
        for (index = 0; index < count; ++index) {
            uint32_t rgb = words[index] & 0x00ffffffU;

            if (words[index] != GPU_H5_LINEAR_CLEAR_PATTERN) {
                stats->changed_count += 1U;
            }
            if (rgb == GPU_D2_REALFRAME_DARK_RGB) {
                stats->semantic_output_dark_count += 1U;
            } else if (rgb == GPU_D2_REALFRAME_LIGHT_RGB) {
                stats->semantic_output_light_count += 1U;
            } else {
                stats->semantic_output_other_count += 1U;
            }
        }
    }
    __sync_synchronize();
    return 0;
}

static bool gpu_d3_source_neighborhood_matches(const struct video_stream_manifest *manifest,
                                               const uint8_t *frame,
                                               uint32_t source_x,
                                               uint32_t source_y,
                                               uint32_t value) {
    int radius = (int)GPU_D3_VIDEO_SEMANTIC_EDGE_RADIUS;
    int base_x = (int)source_x;
    int base_y = (int)source_y;
    int dy;

    if (manifest == NULL || frame == NULL || manifest->width == 0U ||
        manifest->height == 0U) {
        return false;
    }
    for (dy = -radius; dy <= radius; ++dy) {
        int dx;
        int ny = base_y + dy;

        if (ny < 0 || ny >= (int)manifest->height) {
            continue;
        }
        for (dx = -radius; dx <= radius; ++dx) {
            int nx = base_x + dx;

            if (nx < 0 || nx >= (int)manifest->width) {
                continue;
            }
            if (gpu_d2_realframe_expected_rgb(frame,
                                              manifest,
                                              (uint32_t)nx,
                                              (uint32_t)ny) == value) {
                return true;
            }
        }
    }
    return false;
}

static void gpu_d3_validate_linear_semantics(const struct gpu_d3_session *session,
                                             const struct video_stream_manifest *manifest,
                                             const uint8_t *frame,
                                             struct gpu_d3_video_frame_stats *stats) {
    const uint32_t *words;
    uint32_t index;

    if (session == NULL || manifest == NULL || frame == NULL || stats == NULL ||
        session->linear.map == NULL || session->linear.map == MAP_FAILED ||
        session->target_width == 0U || session->target_height == 0U ||
        manifest->width == 0U || manifest->height == 0U) {
        return;
    }
    words = (const uint32_t *)session->linear.map;
    stats->semantic_first_mismatch_index = UINT_MAX;
    for (index = 0; index < GPU_D1_CHECKER_SAMPLE_COUNT; ++index) {
        uint32_t sx = index % GPU_D1_CHECKER_SAMPLE_GRID;
        uint32_t sy = index / GPU_D1_CHECKER_SAMPLE_GRID;
        uint32_t target_x = (uint32_t)(
            (((uint64_t)((sx * 2U) + 1U)) * session->target_width) /
            (2ULL * GPU_D1_CHECKER_SAMPLE_GRID));
        uint32_t target_y = (uint32_t)(
            (((uint64_t)((sy * 2U) + 1U)) * session->target_height) /
            (2ULL * GPU_D1_CHECKER_SAMPLE_GRID));
        uint32_t source_x;
        uint32_t source_y;
        uint32_t expected;
        uint32_t value;

        if (target_x >= session->target_width) {
            target_x = session->target_width - 1U;
        }
        if (target_y >= session->target_height) {
            target_y = session->target_height - 1U;
        }
        source_x = (uint32_t)(
            (((uint64_t)target_x) * manifest->width + (session->target_width / 2U)) /
            session->target_width);
        source_y = (uint32_t)(
            (((uint64_t)target_y) * manifest->height + (session->target_height / 2U)) /
            session->target_height);
        if (source_x >= manifest->width) {
            source_x = manifest->width - 1U;
        }
        if (source_y >= manifest->height) {
            source_y = manifest->height - 1U;
        }
        expected = gpu_d2_realframe_expected_rgb(frame, manifest, source_x, source_y);
        value = words[((size_t)target_y * session->target_width) + target_x] & 0x00ffffffU;
        stats->semantic_sample_count += 1U;
        if (value == expected) {
            stats->semantic_exact_match_count += 1U;
            stats->semantic_sample_match_count += 1U;
        } else if (gpu_d3_source_neighborhood_matches(manifest,
                                                       frame,
                                                       source_x,
                                                       source_y,
                                                       value)) {
            stats->semantic_edge_tolerant_match_count += 1U;
            stats->semantic_sample_match_count += 1U;
        } else {
            if (stats->semantic_sample_mismatch_count == 0U) {
                stats->semantic_first_mismatch_index = index;
                stats->semantic_first_mismatch_expected = expected;
                stats->semantic_first_mismatch_value = value;
            }
            stats->semantic_sample_mismatch_count += 1U;
        }
    }
}

static int gpu_d3_render_frame_to_kms(struct gpu_d3_session *session,
                                      const struct video_stream_manifest *manifest,
                                      const uint8_t *frame,
                                      struct a90_fb *fb,
                                      uint32_t dst_x,
                                      uint32_t dst_y,
                                      struct gpu_d3_video_frame_stats *stats) {
    uint64_t started_ns;
    uint64_t after_texture_ns;
    uint64_t before_wait_ns;
    uint64_t after_wait_ns;
    uint64_t before_readback_ns;
    uint64_t after_readback_ns;
    uint64_t before_copy_ns;
    uint64_t after_copy_ns;
    int rc;

    if (session == NULL || manifest == NULL || frame == NULL || stats == NULL) {
        return -EINVAL;
    }
    memset(stats, 0, sizeof(*stats));
    stats->rc = -EIO;
    memset(session->color.map, 0, (size_t)session->target_bytes);
    memset(session->color_flag.map, 0, (size_t)GPU_D3_VIDEO_COLOR_FLAG_ALLOC_SIZE);
    memset(session->linear.map, 0, (size_t)session->target_bytes);
    started_ns = video_monotonic_ns();
    stats->semantic_first_mismatch_index = UINT_MAX;
    gpu_d3_write_mono1_texture((uint32_t *)session->texture.map, frame, manifest, stats);
    __sync_synchronize();
    after_texture_ns = video_monotonic_ns();
    stats->texture_write_us = (after_texture_ns - started_ns) / 1000ULL;

    rc = gpu_d3_sync_to_gpu(session);
    stats->sync_rc = rc;
    if (rc < 0) {
        stats->rc = rc;
        return rc;
    }
    before_wait_ns = video_monotonic_ns();
    rc = gpu_d3_submit_wait(session, stats);
    after_wait_ns = video_monotonic_ns();
    stats->gpu_wait_us = (after_wait_ns - before_wait_ns) / 1000ULL;
    if (rc < 0) {
        stats->rc = rc;
        return rc;
    }

    before_readback_ns = video_monotonic_ns();
    rc = gpu_d3_sync_linear_from_gpu(session);
    after_readback_ns = video_monotonic_ns();
    stats->readback_sync_us = (after_readback_ns - before_readback_ns) / 1000ULL;
    stats->readback_sync_rc = rc;
    if (rc < 0) {
        stats->rc = rc;
        return rc;
    }

    before_copy_ns = video_monotonic_ns();
    rc = gpu_d3_copy_linear_to_kms(session, fb, dst_x, dst_y, stats);
    after_copy_ns = video_monotonic_ns();
    stats->kms_copy_us = (after_copy_ns - before_copy_ns) / 1000ULL;
    stats->copy_rc = rc;
    if (rc == 0) {
        gpu_d3_validate_linear_semantics(session, manifest, frame, stats);
    }
    stats->rc = rc;
    return rc;
}

static void gpu_d3_add_us(uint64_t value,
                          uint64_t *sum,
                          uint64_t *max_value) {
    if (sum != NULL) {
        *sum += value;
    }
    if (max_value != NULL && value > *max_value) {
        *max_value = value;
    }
}

static int gpu_d3_video_texture_present_child(int write_fd,
                                              uint32_t requested_frames,
                                              int hold_ms,
                                              uint32_t start_frame) {
    struct gpu_d3_video_summary summary;
    struct video_stream_manifest manifest;
    struct video_stream_header_v1 header;
    struct gpu_d3_session session;
    struct a90_fb *fb;
    uint8_t *frame = NULL;
    int fd = -1;
    uint64_t interval_ns;
    uint64_t started_ns;
    uint64_t finished_ns;
    uint64_t read_sum_us = 0;
    uint64_t texture_sum_us = 0;
    uint64_t gpu_wait_sum_us = 0;
    uint64_t readback_sum_us = 0;
    uint64_t copy_sum_us = 0;
    uint64_t present_sum_us = 0;
    uint64_t total_sum_us = 0;
    uint32_t limit_frames;
    uint32_t frame_index;
    uint32_t display_index;
    uint32_t dst_x = 0U;
    uint32_t dst_y = 48U;
    int rc = 0;

    memset(&summary, 0, sizeof(summary));
    memset(&manifest, 0, sizeof(manifest));
    gpu_d3_session_init(&session);
    summary.result_rc = -EIO;
    summary.gpu_create_rc = -1;
    summary.kms_begin_rc = -1;
    summary.present_rc = -1;
    summary.close_rc = -1;
    summary.requested_frames = requested_frames;
    summary.start_frame = start_frame;
    summary.target_width = GPU_D3_VIDEO_TARGET_WIDTH;
    summary.target_height = GPU_D3_VIDEO_TARGET_HEIGHT;
    summary.target_stride = GPU_D3_VIDEO_TARGET_STRIDE;
    summary.target_bytes = (uint32_t)GPU_D3_VIDEO_TARGET_BYTES;
    summary.failed_frame = UINT_MAX;
    summary.last_frame_index = UINT_MAX;
    summary.semantic_first_mismatch_index = UINT_MAX;

    summary.manifest_rc = video_parse_manifest(GPU_D2_REALFRAME_BADAPPLE_MANIFEST_PATH, &manifest);
    if (summary.manifest_rc < 0) {
        rc = summary.manifest_rc;
        goto out;
    }
    if (manifest.stream_version != VIDEO_STREAM_VERSION_A90VSTR1 ||
        manifest.pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 ||
        manifest.width != 480U || manifest.height != 360U ||
        manifest.stride < (manifest.width + 7U) / 8U) {
        rc = -EINVAL;
        summary.manifest_rc = -EINVAL;
        goto out;
    }
    summary.source_width = manifest.width;
    summary.source_height = manifest.height;
    summary.source_stride = manifest.stride;
    summary.source_frame_bytes = manifest.frame_bytes;
    if (start_frame >= manifest.frame_count) {
        summary.manifest_rc = -EINVAL;
        rc = -EINVAL;
        goto out;
    }
    interval_ns = video_frame_interval_ns(manifest.fps_num, manifest.fps_den);
    if (interval_ns == 0U) {
        rc = -EINVAL;
        goto out;
    }
    limit_frames = requested_frames > 0U &&
        requested_frames < manifest.frame_count - start_frame ?
        requested_frames : manifest.frame_count - start_frame;
    if (limit_frames > GPU_D3_VIDEO_MAX_FRAMES) {
        limit_frames = GPU_D3_VIDEO_MAX_FRAMES;
    }

    errno = 0;
    fd = open(manifest.stream_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        summary.stream_open_rc = -1;
        summary.stream_open_errno = errno;
        rc = negative_errno_or(EIO);
        goto out;
    }
    summary.stream_open_rc = 0;
    rc = video_read_exact_fd(fd, &header, sizeof(header));
    summary.header_rc = rc < 0 ? rc : video_validate_stream_header(&manifest, &header);
    if (summary.header_rc < 0) {
        rc = summary.header_rc;
        goto out;
    }

    frame = (uint8_t *)malloc(manifest.frame_bytes);
    if (frame == NULL) {
        rc = -ENOMEM;
        goto out;
    }
    rc = gpu_d3_create_session(&session, &manifest, &summary);
    if (rc < 0) {
        summary.gpu_create_rc = rc;
        goto out;
    }
    for (frame_index = 0; frame_index < start_frame; ++frame_index) {
        struct video_stream_frame_record_v1 record;

        rc = video_read_exact_fd(fd, &record, sizeof(record));
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        if (record.index != frame_index || record.payload_bytes != manifest.frame_bytes) {
            summary.failed_frame = frame_index;
            rc = -EINVAL;
            goto out;
        }
        rc = video_skip_exact_fd(fd, record.payload_bytes);
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        summary.skipped_frames += 1U;
    }
    stop_auto_hud(false);
    started_ns = video_monotonic_ns();
    for (display_index = 0; display_index < limit_frames; ++display_index) {
        struct video_stream_frame_record_v1 record;
        struct gpu_d3_video_frame_stats stats;
        uint64_t frame_start_ns = video_monotonic_ns();
        uint64_t after_read_ns;
        uint64_t before_present_ns;
        uint64_t after_present_ns;
        uint64_t deadline_ns = started_ns + ((uint64_t)display_index * interval_ns);
        uint64_t read_us;
        char line[96];

        frame_index = start_frame + display_index;
        rc = video_read_exact_fd(fd, &record, sizeof(record));
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        if (record.index != frame_index || record.payload_bytes != manifest.frame_bytes) {
            summary.failed_frame = frame_index;
            rc = -EINVAL;
            goto out;
        }
        rc = video_read_exact_fd(fd, frame, record.payload_bytes);
        after_read_ns = video_monotonic_ns();
        read_us = (after_read_ns - frame_start_ns) / 1000ULL;
        gpu_d3_add_us(read_us, &read_sum_us, &summary.read_max_us);
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        summary.stream_bytes += record.payload_bytes;

        summary.kms_begin_rc = a90_kms_begin_frame(0x05070c);
        if (summary.kms_begin_rc < 0) {
            rc = negative_errno_or(ENODEV);
            summary.failed_frame = frame_index;
            goto out;
        }
        fb = a90_kms_framebuffer();
        if (fb == NULL || fb->pixels == NULL) {
            rc = -ENODEV;
            summary.failed_frame = frame_index;
            goto out;
        }
        dst_x = fb->width > session.target_width ?
            (fb->width - session.target_width) / 2U : 0U;
        dst_y = 48U;
        rc = gpu_d3_render_frame_to_kms(&session, &manifest, frame, fb, dst_x, dst_y, &stats);
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        gpu_d3_add_us(stats.texture_write_us, &texture_sum_us, &summary.texture_max_us);
        gpu_d3_add_us(stats.gpu_wait_us, &gpu_wait_sum_us, &summary.gpu_wait_max_us);
        gpu_d3_add_us(stats.readback_sync_us, &readback_sum_us, &summary.readback_max_us);
        gpu_d3_add_us(stats.kms_copy_us, &copy_sum_us, &summary.copy_max_us);
        summary.changed_total += stats.changed_count;
        summary.last_first_word = stats.first_word;
        summary.last_center_word = stats.center_word;
        summary.last_frame_index = frame_index;
        summary.semantic_sample_count = stats.semantic_sample_count;
        summary.semantic_sample_match_count = stats.semantic_sample_match_count;
        summary.semantic_exact_match_count = stats.semantic_exact_match_count;
        summary.semantic_edge_tolerant_match_count =
            stats.semantic_edge_tolerant_match_count;
        summary.semantic_sample_mismatch_count = stats.semantic_sample_mismatch_count;
        summary.semantic_first_mismatch_index = stats.semantic_first_mismatch_index;
        summary.semantic_first_mismatch_expected = stats.semantic_first_mismatch_expected;
        summary.semantic_first_mismatch_value = stats.semantic_first_mismatch_value;
        summary.semantic_source_dark_count = stats.semantic_source_dark_count;
        summary.semantic_source_light_count = stats.semantic_source_light_count;
        summary.semantic_output_dark_count = stats.semantic_output_dark_count;
        summary.semantic_output_light_count = stats.semantic_output_light_count;
        summary.semantic_output_other_count = stats.semantic_output_other_count;

        snprintf(line, sizeof(line), "GPU D3 TEXTURE FRAME %u/%u",
                 display_index + 1U, limit_frames);
        a90_draw_rect(fb, 0, 0, fb->width, 44U, 0x05070c);
        a90_draw_text(fb, 48U, 12U, line, 0x66ddff, 2U);
        a90_draw_text(fb, fb->width > 360U ? fb->width - 350U : 48U,
                      12U, "BAD APPLE GPU BLIT", 0xbbbbbb, 2U);
        snprintf(line, sizeof(line), "TARGET %ux%u  PM4 %u",
                 session.target_width, session.target_height, session.pm4_dwords);
        a90_draw_text(fb, 48U, dst_y + session.target_height + 20U,
                      line, 0xffffff, 2U);

        rc = video_wait_until_ns(deadline_ns);
        if (rc < 0) {
            summary.failed_frame = frame_index;
            goto out;
        }
        before_present_ns = video_monotonic_ns();
        summary.present_rc = a90_kms_present("gpu-d3-video-texture", false);
        after_present_ns = video_monotonic_ns();
        gpu_d3_add_us((after_present_ns - before_present_ns) / 1000ULL,
                      &present_sum_us,
                      &summary.present_max_us);
        gpu_d3_add_us((after_present_ns - frame_start_ns) / 1000ULL,
                      &total_sum_us,
                      &summary.total_max_us);
        if (summary.present_rc < 0) {
            rc = negative_errno_or(EIO);
            summary.failed_frame = frame_index;
            goto out;
        }
        summary.presented_frames += 1U;
        if (a90_console_poll_cancel(0) != CANCEL_NONE) {
            rc = 0;
            break;
        }
    }
    finished_ns = video_monotonic_ns();
    summary.elapsed_ns = finished_ns > started_ns ? finished_ns - started_ns : 1ULL;
    summary.result_rc = rc;
    if (summary.presented_frames > 0U) {
        summary.fps_milli =
            ((uint64_t)summary.presented_frames * 1000000000000ULL) / summary.elapsed_ns;
        summary.read_avg_us = read_sum_us / summary.presented_frames;
        summary.texture_avg_us = texture_sum_us / summary.presented_frames;
        summary.gpu_wait_avg_us = gpu_wait_sum_us / summary.presented_frames;
        summary.readback_avg_us = readback_sum_us / summary.presented_frames;
        summary.copy_avg_us = copy_sum_us / summary.presented_frames;
        summary.present_avg_us = present_sum_us / summary.presented_frames;
        summary.total_avg_us = total_sum_us / summary.presented_frames;
    }
    if (hold_ms > 0 && summary.presented_frames > 0U) {
        usleep((useconds_t)hold_ms * 1000U);
    }

out:
    if (summary.elapsed_ns == 0U) {
        summary.elapsed_ns = 1U;
    }
    if (fd >= 0) {
        errno = 0;
        if (close(fd) < 0) {
            summary.close_rc = -1;
            summary.close_errno = errno;
        } else {
            summary.close_rc = 0;
            summary.close_errno = 0;
        }
    }
    free(frame);
    gpu_d3_destroy_session(&session);
    if (summary.result_rc == 0 && rc < 0) {
        summary.result_rc = rc;
    } else if (summary.result_rc == -EIO && rc == 0 && summary.presented_frames > 0U) {
        summary.result_rc = 0;
    }
    if (write_fd >= 0) {
        ssize_t written = write(write_fd, &summary, sizeof(summary));

        (void)written;
        (void)close(write_fd);
    }
    return summary.result_rc;
}

static bool gpu_d3_video_summary_passed(const struct gpu_d3_video_summary *summary) {
    /* Legacy V3313 gate kept for source-contract compatibility: summary.changed_total > 0ULL. */
    return summary != NULL &&
           summary->result_rc == 0 &&
           summary->presented_frames > 0U &&
           summary->changed_total > 0ULL &&
           summary->semantic_sample_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           summary->semantic_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT &&
           summary->semantic_sample_match_count ==
               summary->semantic_exact_match_count +
               summary->semantic_edge_tolerant_match_count &&
           summary->semantic_sample_mismatch_count == 0U &&
           summary->semantic_output_other_count == 0U;
}

static int gpu_d3_video_texture_present_probe(int timeout_ms,
                                              bool materialize_devnode,
                                              uint32_t requested_frames,
                                              int hold_ms,
                                              uint32_t start_frame) {
    int pipefd[2];
    pid_t pid;
    long deadline_ms;
    bool got_result = false;
    bool timed_out = false;
    bool child_killed = false;
    bool child_reaped = false;
    int child_status = 0;
    struct gpu_d3_video_summary summary;

    memset(&summary, 0, sizeof(summary));
    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_D3_VIDEO_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.d3.video.error=timeout-too-large max_ms=%d\r\n",
                           GPU_D3_VIDEO_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    if (requested_frames == 0U) {
        requested_frames = GPU_D3_VIDEO_DEFAULT_FRAMES;
    }
    if (requested_frames > GPU_D3_VIDEO_MAX_FRAMES) {
        a90_console_printf("gpu.d3.video.error=frames-too-large max=%u\r\n",
                           GPU_D3_VIDEO_MAX_FRAMES);
        return -EINVAL;
    }
    if (hold_ms < 0 || hold_ms > GPU_H5_VISUAL_HOLD_MAX_MS) {
        a90_console_printf("gpu.d3.video.error=bad-hold max_ms=%d\r\n",
                           GPU_H5_VISUAL_HOLD_MAX_MS);
        return -EINVAL;
    }

    a90_console_printf("gpu.d3.video.version=1\r\n");
    a90_console_printf("gpu.d3.video.scope=" GPU_D3_VIDEO_SCOPE "\r\n");
    a90_console_printf("gpu.d3.video.label=" GPU_D3_VIDEO_LABEL "\r\n");
    a90_console_printf("gpu.d3.video.command=gpu d3-video-texture-present-probe --preset badapple --frames %u --timeout-ms %d --materialize-devnode\r\n",
                       requested_frames, timeout_ms);
    a90_console_printf("gpu.d3.video.kgsl_path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.d3.video.drm_path=/dev/dri/card0\r\n");
    a90_console_printf("gpu.d3.video.preset=badapple\r\n");
    a90_console_printf("gpu.d3.video.manifest=%s\r\n", GPU_D2_REALFRAME_BADAPPLE_MANIFEST_PATH);
    a90_console_printf("gpu.d3.video.frames_requested=%u\r\n", requested_frames);
    a90_console_printf("gpu.d3.video.start_frame=%u\r\n", start_frame);
    a90_console_printf("gpu.d3.video.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.d3.video.hold_ms=%d\r\n", hold_ms);
    a90_console_printf("gpu.d3.video.texture_source=sd-cache-mono1-expanded-to-rgba8-texture-per-frame\r\n");
    a90_console_printf("gpu.d3.video.blit_mode=kgsl-textured-quad-scale-to-960x720-linear-readback-kms-copy\r\n");
    a90_console_printf("gpu.d3.video.target=%ux%u stride=%u\r\n",
                       GPU_D3_VIDEO_TARGET_WIDTH,
                       GPU_D3_VIDEO_TARGET_HEIGHT,
                       GPU_D3_VIDEO_TARGET_STRIDE);
    a90_console_printf("gpu.d3.video.shader_sha256=%s\r\n", GPU_D1_TEXTURED_FS_SHA256);
    a90_console_printf("gpu.d3.video.power_write_attempted=0\r\n");
    a90_console_printf("gpu.d3.video.proprietary_blob_attempted=0\r\n");
    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.d3.video.materialize_requested=1\r\n");
        a90_console_printf("gpu.d3.video.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.d3.video.materialize_requested=0\r\n");
    }
    if (pipe(pipefd) < 0) {
        int saved_errno = errno;
        a90_console_printf("gpu.d3.video.pipe_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(pipefd[0]);
        close(pipefd[1]);
        a90_console_printf("gpu.d3.video.fork_rc=-1 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        int child_rc;

        close(pipefd[0]);
        child_rc = gpu_d3_video_texture_present_child(pipefd[1],
                                                      requested_frames,
                                                      hold_ms,
                                                      start_frame);
        _exit(child_rc == 0 ? 0 : 1);
    }
    close(pipefd[1]);
    deadline_ms = monotonic_millis() + timeout_ms;
    a90_console_printf("gpu.d3.video.child_pid=%ld\r\n", (long)pid);

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
            rd = read(pipefd[0], &summary, sizeof(summary));
            if (rd == (ssize_t)sizeof(summary)) {
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

    a90_console_printf("gpu.d3.video.result=%s\r\n",
                       got_result && gpu_d3_video_summary_passed(&summary) ?
                           "video-texture-present-pass" :
                       (timed_out ? "timeout" : "video-texture-present-failed"));
    a90_console_printf("gpu.d3.video.timed_out=%d\r\n", timed_out ? 1 : 0);
    a90_console_printf("gpu.d3.video.child_killed=%d\r\n", child_killed ? 1 : 0);
    a90_console_printf("gpu.d3.video.child_reaped=%d\r\n", child_reaped ? 1 : 0);
    a90_console_printf("gpu.d3.video.child_status=0x%x\r\n", child_status);
    if (got_result) {
        a90_console_printf("gpu.d3.video.result_rc=%d\r\n", summary.result_rc);
        a90_console_printf("gpu.d3.video.manifest_rc=%d\r\n", summary.manifest_rc);
        a90_console_printf("gpu.d3.video.stream_open_rc=%d errno=%d\r\n",
                           summary.stream_open_rc, summary.stream_open_errno);
        a90_console_printf("gpu.d3.video.header_rc=%d\r\n", summary.header_rc);
        a90_console_printf("gpu.d3.video.gpu_create_rc=%d\r\n", summary.gpu_create_rc);
        a90_console_printf("gpu.d3.video.source_size=%ux%u\r\n",
                           summary.source_width, summary.source_height);
        a90_console_printf("gpu.d3.video.source_stride=%u\r\n", summary.source_stride);
        a90_console_printf("gpu.d3.video.source_frame_bytes=%u\r\n",
                           summary.source_frame_bytes);
        a90_console_printf("gpu.d3.video.target_size=%ux%u\r\n",
                           summary.target_width, summary.target_height);
        a90_console_printf("gpu.d3.video.target_stride=%u\r\n", summary.target_stride);
        a90_console_printf("gpu.d3.video.target_bytes=%u\r\n", summary.target_bytes);
        a90_console_printf("gpu.d3.video.pm4_dwords=%u\r\n", summary.pm4_dwords);
        a90_console_printf("gpu.d3.video.start_frame_actual=%u\r\n",
                           summary.start_frame);
        a90_console_printf("gpu.d3.video.skipped_frames=%u\r\n",
                           summary.skipped_frames);
        a90_console_printf("gpu.d3.video.last_frame_index=%u\r\n",
                           summary.last_frame_index);
        a90_console_printf("gpu.d3.video.presented=%u\r\n", summary.presented_frames);
        a90_console_printf("gpu.d3.video.failed_frame=%u\r\n", summary.failed_frame);
        a90_console_printf("gpu.d3.video.stream_bytes=%llu\r\n",
                           (unsigned long long)summary.stream_bytes);
        a90_console_printf("gpu.d3.video.elapsed_ns=%llu\r\n",
                           (unsigned long long)summary.elapsed_ns);
        a90_console_printf("gpu.d3.video.fps_milli=%llu\r\n",
                           (unsigned long long)summary.fps_milli);
        a90_console_printf("gpu.d3.video.timing.unit=us\r\n");
        a90_console_printf("gpu.d3.video.timing.read.avg_us=%llu\r\n",
                           (unsigned long long)summary.read_avg_us);
        a90_console_printf("gpu.d3.video.timing.read.max_us=%llu\r\n",
                           (unsigned long long)summary.read_max_us);
        a90_console_printf("gpu.d3.video.timing.texture.avg_us=%llu\r\n",
                           (unsigned long long)summary.texture_avg_us);
        a90_console_printf("gpu.d3.video.timing.texture.max_us=%llu\r\n",
                           (unsigned long long)summary.texture_max_us);
        a90_console_printf("gpu.d3.video.timing.gpu_wait.avg_us=%llu\r\n",
                           (unsigned long long)summary.gpu_wait_avg_us);
        a90_console_printf("gpu.d3.video.timing.gpu_wait.max_us=%llu\r\n",
                           (unsigned long long)summary.gpu_wait_max_us);
        a90_console_printf("gpu.d3.video.timing.readback.avg_us=%llu\r\n",
                           (unsigned long long)summary.readback_avg_us);
        a90_console_printf("gpu.d3.video.timing.readback.max_us=%llu\r\n",
                           (unsigned long long)summary.readback_max_us);
        a90_console_printf("gpu.d3.video.timing.copy.avg_us=%llu\r\n",
                           (unsigned long long)summary.copy_avg_us);
        a90_console_printf("gpu.d3.video.timing.copy.max_us=%llu\r\n",
                           (unsigned long long)summary.copy_max_us);
        a90_console_printf("gpu.d3.video.timing.present.avg_us=%llu\r\n",
                           (unsigned long long)summary.present_avg_us);
        a90_console_printf("gpu.d3.video.timing.present.max_us=%llu\r\n",
                           (unsigned long long)summary.present_max_us);
        a90_console_printf("gpu.d3.video.timing.total.avg_us=%llu\r\n",
                           (unsigned long long)summary.total_avg_us);
        a90_console_printf("gpu.d3.video.timing.total.max_us=%llu\r\n",
                           (unsigned long long)summary.total_max_us);
        a90_console_printf("gpu.d3.video.changed_total=%llu\r\n",
                           (unsigned long long)summary.changed_total);
        a90_console_printf("gpu.d3.video.last_first_word=0x%x\r\n",
                           summary.last_first_word);
        a90_console_printf("gpu.d3.video.last_center_word=0x%x\r\n",
                           summary.last_center_word);
        a90_console_printf("gpu.d3.video.semantic.sample_count=%u\r\n",
                           summary.semantic_sample_count);
        a90_console_printf("gpu.d3.video.semantic.match_count=%u\r\n",
                           summary.semantic_sample_match_count);
        a90_console_printf("gpu.d3.video.semantic.exact_match_count=%u\r\n",
                           summary.semantic_exact_match_count);
        a90_console_printf("gpu.d3.video.semantic.edge_tolerant_match_count=%u\r\n",
                           summary.semantic_edge_tolerant_match_count);
        a90_console_printf("gpu.d3.video.semantic.edge_tolerance_radius=%u\r\n",
                           GPU_D3_VIDEO_SEMANTIC_EDGE_RADIUS);
        a90_console_printf("gpu.d3.video.semantic.mismatch_count=%u\r\n",
                           summary.semantic_sample_mismatch_count);
        a90_console_printf("gpu.d3.video.semantic.first_mismatch_index=%u\r\n",
                           summary.semantic_first_mismatch_index);
        a90_console_printf("gpu.d3.video.semantic.first_mismatch_expected=0x%x\r\n",
                           summary.semantic_first_mismatch_expected);
        a90_console_printf("gpu.d3.video.semantic.first_mismatch_value=0x%x\r\n",
                           summary.semantic_first_mismatch_value);
        a90_console_printf("gpu.d3.video.semantic.source_dark_count=%u\r\n",
                           summary.semantic_source_dark_count);
        a90_console_printf("gpu.d3.video.semantic.source_light_count=%u\r\n",
                           summary.semantic_source_light_count);
        a90_console_printf("gpu.d3.video.semantic.output_dark_count=%u\r\n",
                           summary.semantic_output_dark_count);
        a90_console_printf("gpu.d3.video.semantic.output_light_count=%u\r\n",
                           summary.semantic_output_light_count);
        a90_console_printf("gpu.d3.video.semantic.output_other_count=%u\r\n",
                           summary.semantic_output_other_count);
        a90_console_printf("gpu.d3.video.kms_begin_rc=%d\r\n", summary.kms_begin_rc);
        a90_console_printf("gpu.d3.video.present_rc=%d\r\n", summary.present_rc);
        a90_console_printf("gpu.d3.video.close_rc=%d errno=%d\r\n",
                           summary.close_rc, summary.close_errno);
    }
    if (timed_out) {
        return -ETIMEDOUT;
    }
    return got_result && gpu_d3_video_summary_passed(&summary) ?
        0 : -EIO;
}

static uint32_t gpu_h5_pack_rgb_for_xbgr8888(uint32_t color) {
    uint32_t red = (color >> 16) & 0xffU;
    uint32_t green = (color >> 8) & 0xffU;
    uint32_t blue = color & 0xffU;

    return (blue << 16) | (green << 8) | red;
}

static uint32_t gpu_h5_h3_readback_word_to_xbgr8888(uint32_t word) {
    if (word == GPU_H2_CLEAR_PATTERN || word == GPU_H5_LINEAR_CLEAR_PATTERN) {
        return gpu_h5_pack_rgb_for_xbgr8888(0x101010U);
    }
    return word & 0x00ffffffU;
}

static bool gpu_h5_find_linear_nonzero_bounds(const uint32_t *source,
                                              uint32_t *min_x,
                                              uint32_t *min_y,
                                              uint32_t *max_x,
                                              uint32_t *max_y) {
    uint32_t found_min_x = GPU_H2_COLOR_WIDTH;
    uint32_t found_min_y = GPU_H2_COLOR_HEIGHT;
    uint32_t found_max_x = 0U;
    uint32_t found_max_y = 0U;
    uint32_t y;
    bool found = false;

    if (source == NULL) {
        return false;
    }

    for (y = 0; y < GPU_H2_COLOR_HEIGHT; ++y) {
        uint32_t x;

        for (x = 0; x < GPU_H2_COLOR_WIDTH; ++x) {
            if (source[(y * GPU_H2_COLOR_WIDTH) + x] == GPU_H5_LINEAR_CLEAR_PATTERN) {
                continue;
            }
            if (!found || x < found_min_x) {
                found_min_x = x;
            }
            if (!found || y < found_min_y) {
                found_min_y = y;
            }
            if (!found || x > found_max_x) {
                found_max_x = x;
            }
            if (!found || y > found_max_y) {
                found_max_y = y;
            }
            found = true;
        }
    }

    if (!found) {
        return false;
    }
    if (min_x != NULL) {
        *min_x = found_min_x;
    }
    if (min_y != NULL) {
        *min_y = found_min_y;
    }
    if (max_x != NULL) {
        *max_x = found_max_x;
    }
    if (max_y != NULL) {
        *max_y = found_max_y;
    }
    return true;
}

static int gpu_h5_blit_h3_readback_to_kms(const uint32_t *source,
                                          const struct gpu_h3_draw_envelope_probe_result *h3,
                                          uint32_t *rect_x,
                                          uint32_t *rect_y,
                                          uint32_t *rect_w,
                                          uint32_t *rect_h,
                                          uint32_t *scale_out) {
    struct a90_fb *fb = a90_kms_framebuffer();
    uint32_t min_x = 0U;
    uint32_t min_y = 0U;
    uint32_t max_x = 0U;
    uint32_t max_y = 0U;
    uint32_t src_w;
    uint32_t src_h;
    uint32_t usable_w;
    uint32_t usable_h;
    uint32_t scale;
    uint32_t dst_w;
    uint32_t dst_h;
    uint32_t x;
    uint32_t y;
    uint32_t sy;
    char line[96];

    if (source == NULL || h3 == NULL ||
        fb == NULL || fb->pixels == NULL || fb->pixels == MAP_FAILED ||
        fb->width == 0U || fb->height == 0U || fb->stride < fb->width * 4U) {
        return -ENODEV;
    }
    if (!gpu_h5_find_linear_nonzero_bounds(source, &min_x, &min_y, &max_x, &max_y)) {
        return -EIO;
    }

    src_w = (max_x - min_x) + 1U;
    src_h = (max_y - min_y) + 1U;
    a90_console_printf("gpu.h5.vis.source_bbox=%u,%u,%u,%u\r\n",
                       min_x, min_y, max_x, max_y);
    a90_console_printf("gpu.h5.vis.visual_shape=solid-mask-centered\r\n");
    usable_w = fb->width > (GPU_H5_VISUAL_MIN_PANEL_MARGIN * 2U) ?
        fb->width - (GPU_H5_VISUAL_MIN_PANEL_MARGIN * 2U) : fb->width;
    usable_h = fb->height > (GPU_H5_VISUAL_TOP_TEXT_Y + GPU_H5_VISUAL_BOTTOM_RESERVED) ?
        fb->height - GPU_H5_VISUAL_TOP_TEXT_Y - GPU_H5_VISUAL_BOTTOM_RESERVED : fb->height;
    scale = usable_w / src_w;
    if (src_h > 0U && usable_h / src_h < scale) {
        scale = usable_h / src_h;
    }
    if (scale == 0U) {
        return -ENOSPC;
    }
    dst_w = src_w * scale;
    dst_h = src_h * scale;
    x = (fb->width - dst_w) / 2U;
    y = (fb->height - dst_h) / 2U;
    if (y < GPU_H5_H3_PRESENT_TOP) {
        y = GPU_H5_H3_PRESENT_TOP;
    }
    if (y + dst_h > fb->height) {
        y = (fb->height - dst_h) / 2U;
    }

    a90_draw_text(fb, 36U, 48U, "GPU H5 VISUAL CLOSE", 0xffffff, 4U);
    a90_draw_text(fb, 36U, 104U, "RECOGNIZABLE TRIANGLE HOLD", 0x80ff80, 3U);
    a90_draw_rect_outline(fb,
                          x > 8U ? x - 8U : x,
                          y > 8U ? y - 8U : y,
                          dst_w + 16U < fb->width ? dst_w + 16U : dst_w,
                          dst_h + 16U < fb->height ? dst_h + 16U : dst_h,
                          4U,
                          0xffffff);
    a90_draw_rect(fb, x, y, dst_w, dst_h, 0x000000);

    for (sy = min_y; sy <= max_y; ++sy) {
        uint32_t sx;

        for (sx = min_x; sx <= max_x; ++sx) {
            uint32_t raw = source[(sy * GPU_H2_COLOR_WIDTH) + sx];
            uint32_t pixel = raw == GPU_H5_LINEAR_CLEAR_PATTERN ?
                gpu_h5_h3_readback_word_to_xbgr8888(raw) :
                gpu_h5_pack_rgb_for_xbgr8888(GPU_H5_VISUAL_FILL_COLOR);
            uint32_t src_rel_y = sy - min_y;
            uint32_t src_rel_x = sx - min_x;
            uint32_t dy;

            for (dy = 0; dy < scale; ++dy) {
                uint32_t *row =
                    (uint32_t *)((char *)fb->pixels + ((y + (src_rel_y * scale) + dy) * fb->stride));
                uint32_t dx;

                for (dx = 0; dx < scale; ++dx) {
                    row[x + (src_rel_x * scale) + dx] = pixel;
                }
            }
        }
    }
    __sync_synchronize();

    snprintf(line, sizeof(line), "NONZERO %u FIRST %u",
             h3->linear_readback_nonzero_count,
             h3->linear_readback_first_nonzero_index);
    a90_draw_text(fb, 36U, y + dst_h + 28U, line, 0xffcc33, 3U);
    snprintf(line, sizeof(line), "BBOX %u,%u-%u,%u SCALE %u",
             min_x, min_y, max_x, max_y, scale);
    a90_draw_text(fb, 36U, y + dst_h + 72U, line, 0xbbbbbb, 3U);
    snprintf(line, sizeof(line), "CENTER %08X CORNERS %u",
             h3->linear_readback_center,
             h3->linear_exterior_corners_zero);
    a90_draw_text(fb, 36U, y + dst_h + 116U, line, 0xbbbbbb, 3U);

    if (rect_x != NULL) {
        *rect_x = x;
    }
    if (rect_y != NULL) {
        *rect_y = y;
    }
    if (rect_w != NULL) {
        *rect_w = dst_w;
    }
    if (rect_h != NULL) {
        *rect_h = dst_h;
    }
    if (scale_out != NULL) {
        *scale_out = scale;
    }
    return 0;
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

static int gpu_c3_read_c2_snapshot(uint32_t *words,
                                   uint64_t *bytes_read,
                                   int *read_errno) {
    int fd;
    uint64_t total = 0ULL;

    if (bytes_read != NULL) {
        *bytes_read = 0ULL;
    }
    if (read_errno != NULL) {
        *read_errno = 0;
    }
    if (words == NULL) {
        if (read_errno != NULL) {
            *read_errno = EINVAL;
        }
        return -1;
    }

    errno = 0;
    fd = open(GPU_C2_SNAPSHOT_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        if (read_errno != NULL) {
            *read_errno = errno;
        }
        return -1;
    }
    while (total < GPU_C2_UAV_BYTES) {
        ssize_t nread;

        errno = 0;
        nread = read(fd,
                     ((char *)words) + total,
                     (size_t)(GPU_C2_UAV_BYTES - total));
        if (nread < 0) {
            if (read_errno != NULL) {
                *read_errno = errno;
            }
            close(fd);
            return -1;
        }
        if (nread == 0) {
            if (read_errno != NULL) {
                *read_errno = EIO;
            }
            close(fd);
            return -1;
        }
        total += (uint64_t)nread;
    }
    if (close(fd) < 0) {
        if (read_errno != NULL) {
            *read_errno = errno;
        }
        return -1;
    }
    if (bytes_read != NULL) {
        *bytes_read = total;
    }
    return 0;
}

static uint32_t gpu_c3_c2_word_to_rgb(uint32_t word, uint32_t x, uint32_t y) {
    uint32_t expected = (y * GPU_C2_PATTERN_WIDTH) + x;
    uint32_t red = (x * 255U) / (GPU_C2_PATTERN_WIDTH - 1U);
    uint32_t green = (y * 255U) / (GPU_C2_PATTERN_HEIGHT - 1U);
    uint32_t blue = ((word ^ (word >> 7)) & 0x7fU) * 2U;

    if (word != expected) {
        return 0xff0040U;
    }
    return (red << 16) | (green << 8) | blue;
}

static int gpu_c3_blit_c2_snapshot_to_kms(const uint32_t *source,
                                          uint32_t mismatch_count,
                                          uint32_t *rect_x,
                                          uint32_t *rect_y,
                                          uint32_t *rect_w,
                                          uint32_t *rect_h,
                                          uint32_t *scale_out) {
    struct a90_fb *fb = a90_kms_framebuffer();
    uint32_t usable_w;
    uint32_t usable_h;
    uint32_t scale;
    uint32_t dst_w;
    uint32_t dst_h;
    uint32_t x;
    uint32_t y;
    uint32_t sy;
    char line[96];

    if (source == NULL ||
        fb == NULL || fb->pixels == NULL || fb->pixels == MAP_FAILED ||
        fb->width == 0U || fb->height == 0U || fb->stride < fb->width * 4U) {
        return -ENODEV;
    }

    usable_w = fb->width > (GPU_H5_VISUAL_MIN_PANEL_MARGIN * 2U) ?
        fb->width - (GPU_H5_VISUAL_MIN_PANEL_MARGIN * 2U) : fb->width;
    usable_h = fb->height > (GPU_H5_VISUAL_TOP_TEXT_Y + GPU_H5_VISUAL_BOTTOM_RESERVED) ?
        fb->height - GPU_H5_VISUAL_TOP_TEXT_Y - GPU_H5_VISUAL_BOTTOM_RESERVED : fb->height;
    scale = usable_w / GPU_C2_PATTERN_WIDTH;
    if (usable_h / GPU_C2_PATTERN_HEIGHT < scale) {
        scale = usable_h / GPU_C2_PATTERN_HEIGHT;
    }
    if (scale == 0U) {
        return -ENOSPC;
    }
    dst_w = GPU_C2_PATTERN_WIDTH * scale;
    dst_h = GPU_C2_PATTERN_HEIGHT * scale;
    x = (fb->width - dst_w) / 2U;
    y = (fb->height - dst_h) / 2U;
    if (y < GPU_H5_H3_PRESENT_TOP) {
        y = GPU_H5_H3_PRESENT_TOP;
    }
    if (y + dst_h > fb->height) {
        y = (fb->height - dst_h) / 2U;
    }

    a90_draw_text(fb, 36U, 48U, "GPU C3 COMPUTE VISUAL", 0xffffff, 4U);
    a90_draw_text(fb, 36U, 104U, "128X128 UAV PATTERN FROM GPU", 0x80ff80, 3U);
    a90_draw_rect(fb, x, y, dst_w, dst_h, GPU_C3_VISUAL_PANEL_BG);
    a90_draw_rect_outline(fb,
                          x > 8U ? x - 8U : x,
                          y > 8U ? y - 8U : y,
                          dst_w + 16U < fb->width ? dst_w + 16U : dst_w,
                          dst_h + 16U < fb->height ? dst_h + 16U : dst_h,
                          4U,
                          mismatch_count == 0U ? 0xffffffU : 0xff0040U);

    for (sy = 0; sy < GPU_C2_PATTERN_HEIGHT; ++sy) {
        uint32_t sx;

        for (sx = 0; sx < GPU_C2_PATTERN_WIDTH; ++sx) {
            uint32_t raw = source[(sy * GPU_C2_PATTERN_WIDTH) + sx];
            uint32_t pixel = gpu_h5_pack_rgb_for_xbgr8888(
                gpu_c3_c2_word_to_rgb(raw, sx, sy));
            uint32_t dy;

            for (dy = 0; dy < scale; ++dy) {
                uint32_t *row =
                    (uint32_t *)((char *)fb->pixels + ((y + (sy * scale) + dy) * fb->stride));
                uint32_t dx;

                for (dx = 0; dx < scale; ++dx) {
                    row[x + (sx * scale) + dx] = pixel;
                }
            }
        }
    }
    __sync_synchronize();

    snprintf(line, sizeof(line), "WORDS %u  MISMATCH %u",
             GPU_C2_UAV_WORDS, mismatch_count);
    a90_draw_text(fb, 36U, y + dst_h + 28U, line, 0xffcc33, 3U);
    snprintf(line, sizeof(line), "SAMPLES 0 1 127 128 4096 8192 16383 OK");
    a90_draw_text(fb, 36U, y + dst_h + 72U, line, 0xbbbbbb, 3U);
    snprintf(line, sizeof(line), "SCALE %u  RECT %u,%u %ux%u",
             scale, x, y, dst_w, dst_h);
    a90_draw_text(fb, 36U, y + dst_h + 116U, line, 0xbbbbbb, 3U);

    if (rect_x != NULL) {
        *rect_x = x;
    }
    if (rect_y != NULL) {
        *rect_y = y;
    }
    if (rect_w != NULL) {
        *rect_w = dst_w;
    }
    if (rect_h != NULL) {
        *rect_h = dst_h;
    }
    if (scale_out != NULL) {
        *scale_out = scale;
    }
    return 0;
}

static int gpu_c3_compute_kms_probe(int timeout_ms,
                                    bool materialize_devnode,
                                    int hold_ms) {
    struct a90_kms_info kms_info;
    uint32_t *snapshot = NULL;
    long total_started_ms = monotonic_millis();
    long stage_started_ms;
    int compute_rc;
    int read_rc = -1;
    int read_errno = 0;
    int begin_rc = -1;
    int blit_rc = -1;
    int present_rc = -1;
    uint64_t bytes_read = 0ULL;
    uint32_t expected_match_count = 0U;
    uint32_t mismatch_count = 0U;
    uint32_t first_mismatch_index = UINT_MAX;
    uint32_t first_mismatch_expected = 0U;
    uint32_t first_mismatch_value = 0U;
    uint32_t rect_x = 0U;
    uint32_t rect_y = 0U;
    uint32_t rect_w = 0U;
    uint32_t rect_h = 0U;
    uint32_t scale = 0U;
    long begin_elapsed_ms = 0;
    long blit_elapsed_ms = 0;
    long present_elapsed_ms = 0;
    unsigned int index;

    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.c3.kms.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    if (hold_ms < 0 || hold_ms > GPU_H5_VISUAL_HOLD_MAX_MS) {
        a90_console_printf("gpu.c3.vis.error=bad-hold max_ms=%d\r\n",
                           GPU_H5_VISUAL_HOLD_MAX_MS);
        return -EINVAL;
    }

    a90_console_printf("gpu.c3.kms.version=1\r\n");
    a90_console_printf("gpu.c3.kms.scope=visible-compute-c3-c2-uav-pattern-to-kms-held\r\n");
    a90_console_printf("gpu.c3.kms.kgsl_path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.c3.kms.drm_path=/dev/dri/card0\r\n");
    a90_console_printf("gpu.c3.kms.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.c3.vis.version=1\r\n");
    a90_console_printf("gpu.c3.vis.mode=c2-uav-r32-pattern-gradient-expanded\r\n");
    a90_console_printf("gpu.c3.vis.hold_ms=%d\r\n", hold_ms);
    a90_console_printf("gpu.c3.vis.hold_max_ms=%d\r\n", GPU_H5_VISUAL_HOLD_MAX_MS);
    a90_console_printf("gpu.c3.kms.compute_source=c2-workgroup-id-uav-readback-snapshot\r\n");
    a90_console_printf("gpu.c3.kms.snapshot_path=%s\r\n", GPU_C2_SNAPSHOT_PATH);
    a90_console_printf("gpu.c3.kms.blit_mode=c2-private-uav-snapshot-to-kms-dumb-framebuffer\r\n");
    a90_console_printf("gpu.c3.kms.zero_copy_attempted=0\r\n");
    a90_console_printf("gpu.c3.kms.scaled_plane_attempted=0\r\n");
    a90_console_printf("gpu.c3.kms.kms_blit_attempted=1\r\n");
    a90_console_printf("gpu.c3.kms.power_write_attempted=0\r\n");
    a90_console_printf("gpu.c3.kms.proprietary_blob_attempted=0\r\n");
    stop_auto_hud(false);
    a90_console_printf("gpu.c3.vis.autohud_stop_attempted=1\r\n");

    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.c3.kms.materialize_requested=1\r\n");
        a90_console_printf("gpu.c3.kms.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.c3.kms.materialize_requested=0\r\n");
    }

    unlink(GPU_C2_SNAPSHOT_PATH);
    stage_started_ms = monotonic_millis();
    compute_rc = gpu_c2_compute_pattern_probe(timeout_ms, false);
    a90_console_printf("gpu.c3.kms.c2_compute_elapsed_ms=%ld\r\n",
                       monotonic_millis() - stage_started_ms);
    a90_console_printf("gpu.c3.kms.c2_compute_rc=%d\r\n", compute_rc);
    if (compute_rc < 0) {
        a90_console_printf("gpu.c3.kms.result=c2-compute-failed\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return compute_rc;
    }

    snapshot = (uint32_t *)malloc((size_t)GPU_C2_UAV_BYTES);
    if (snapshot == NULL) {
        a90_console_printf("gpu.c3.kms.result=oom\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -ENOMEM;
    }

    read_rc = gpu_c3_read_c2_snapshot(snapshot, &bytes_read, &read_errno);
    a90_console_printf("gpu.c3.kms.snapshot_read_rc=%d\r\n", read_rc);
    a90_console_printf("gpu.c3.kms.snapshot_read_errno=%d\r\n", read_errno);
    a90_console_printf("gpu.c3.kms.snapshot_read_bytes=%llu\r\n",
                       (unsigned long long)bytes_read);
    if (read_rc < 0 || bytes_read != GPU_C2_UAV_BYTES) {
        free(snapshot);
        a90_console_printf("gpu.c3.kms.result=snapshot-read-failed\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -EIO;
    }

    for (index = 0; index < GPU_C2_UAV_WORDS; ++index) {
        uint32_t expected = gpu_c2_pattern_expected_value(index);

        if (snapshot[index] == expected) {
            expected_match_count += 1U;
        } else {
            if (first_mismatch_index == UINT_MAX) {
                first_mismatch_index = index;
                first_mismatch_expected = expected;
                first_mismatch_value = snapshot[index];
            }
            mismatch_count += 1U;
        }
    }
    a90_console_printf("gpu.c3.kms.snapshot_readback0=%u\r\n", snapshot[0]);
    a90_console_printf("gpu.c3.kms.snapshot_readback1=%u\r\n", snapshot[1]);
    a90_console_printf("gpu.c3.kms.snapshot_readback127=%u\r\n",
                       snapshot[GPU_C2_SAMPLE_127]);
    a90_console_printf("gpu.c3.kms.snapshot_readback128=%u\r\n",
                       snapshot[GPU_C2_SAMPLE_128]);
    a90_console_printf("gpu.c3.kms.snapshot_readback4096=%u\r\n",
                       snapshot[GPU_C2_SAMPLE_4096]);
    a90_console_printf("gpu.c3.kms.snapshot_readback8192=%u\r\n",
                       snapshot[GPU_C2_SAMPLE_8192]);
    a90_console_printf("gpu.c3.kms.snapshot_readback16383=%u\r\n",
                       snapshot[GPU_C2_SAMPLE_LAST]);
    a90_console_printf("gpu.c3.kms.snapshot_expected_match_count=%u\r\n",
                       expected_match_count);
    a90_console_printf("gpu.c3.kms.snapshot_mismatch_count=%u\r\n",
                       mismatch_count);
    a90_console_printf("gpu.c3.kms.snapshot_first_mismatch_index=%u\r\n",
                       first_mismatch_index);
    a90_console_printf("gpu.c3.kms.snapshot_first_mismatch_expected=%u\r\n",
                       first_mismatch_expected);
    a90_console_printf("gpu.c3.kms.snapshot_first_mismatch_value=%u\r\n",
                       first_mismatch_value);
    if (expected_match_count != GPU_C2_UAV_WORDS || mismatch_count != 0U) {
        free(snapshot);
        a90_console_printf("gpu.c3.kms.result=snapshot-contract-failed\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -EIO;
    }

    stage_started_ms = monotonic_millis();
    begin_rc = a90_kms_begin_frame(GPU_C3_VISUAL_FILL_BG);
    begin_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_kms_info(&kms_info);
    a90_console_printf("gpu.c3.kms.begin_frame_elapsed_ms=%ld\r\n", begin_elapsed_ms);
    a90_console_printf("gpu.c3.kms.begin_frame_rc=%d\r\n", begin_rc);
    a90_console_printf("gpu.c3.kms.fb_initialized=%d\r\n", kms_info.initialized ? 1 : 0);
    a90_console_printf("gpu.c3.kms.fb_width=%u\r\n", kms_info.width);
    a90_console_printf("gpu.c3.kms.fb_height=%u\r\n", kms_info.height);
    a90_console_printf("gpu.c3.kms.fb_stride=%u\r\n", kms_info.stride);
    a90_console_printf("gpu.c3.kms.fb_id=%u\r\n", kms_info.fb_id);
    a90_console_printf("gpu.c3.kms.current_buffer=%u\r\n", kms_info.current_buffer);
    if (begin_rc < 0) {
        free(snapshot);
        a90_console_printf("gpu.c3.kms.result=kms-begin-frame-failed\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -EIO;
    }

    stage_started_ms = monotonic_millis();
    blit_rc = gpu_c3_blit_c2_snapshot_to_kms(snapshot,
                                            mismatch_count,
                                            &rect_x,
                                            &rect_y,
                                            &rect_w,
                                            &rect_h,
                                            &scale);
    blit_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.c3.kms.blit_elapsed_ms=%ld\r\n", blit_elapsed_ms);
    a90_console_printf("gpu.c3.kms.blit_rc=%d\r\n", blit_rc);
    a90_console_printf("gpu.c3.kms.blit_rect=%u,%u,%u,%u\r\n",
                       rect_x, rect_y, rect_w, rect_h);
    a90_console_printf("gpu.c3.kms.blit_scale=%u\r\n", scale);
    free(snapshot);
    snapshot = NULL;
    if (blit_rc < 0) {
        a90_console_printf("gpu.c3.kms.result=kms-blit-failed\r\n");
        a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return blit_rc;
    }

    stage_started_ms = monotonic_millis();
    present_rc = a90_kms_present("gpu-c3-compute-kms", true);
    present_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.c3.kms.present_elapsed_ms=%ld\r\n", present_elapsed_ms);
    a90_console_printf("gpu.c3.kms.present_rc=%d\r\n", present_rc);
    if (present_rc == 0) {
        a90_console_printf("gpu.c3.kms.result=compute-pattern-presented\r\n");
    } else {
        a90_console_printf("gpu.c3.kms.result=kms-present-failed\r\n");
    }
    if (present_rc == 0 && hold_ms > 0) {
        long hold_started_ms = monotonic_millis();

        a90_console_printf("gpu.c3.vis.hold_begin=1\r\n");
        usleep((useconds_t)hold_ms * 1000U);
        a90_console_printf("gpu.c3.vis.hold_elapsed_ms=%ld\r\n",
                           monotonic_millis() - hold_started_ms);
        a90_console_printf("gpu.c3.vis.result=compute-pattern-presented-held\r\n");
    } else if (present_rc == 0) {
        a90_console_printf("gpu.c3.vis.result=compute-pattern-presented-no-hold\r\n");
    } else {
        a90_console_printf("gpu.c3.vis.result=kms-present-failed\r\n");
    }
    a90_console_printf("gpu.c3.kms.total_elapsed_ms=%ld\r\n",
                       monotonic_millis() - total_started_ms);
    return present_rc == 0 ? 0 : -EIO;
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

static int gpu_h5_triangle_kms_probe(int timeout_ms,
                                     bool materialize_devnode,
                                     int hold_ms) {
    struct gpu_h3_draw_snapshot_child_run run;
    struct a90_kms_info kms_info;
    const struct gpu_h3_draw_envelope_probe_result *h3;
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
    uint32_t scale = 0U;
    long begin_elapsed_ms = 0;
    long blit_elapsed_ms = 0;
    long present_elapsed_ms = 0;

    if (timeout_ms <= 0) {
        timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    }
    if (timeout_ms > GPU_G0_MAX_TIMEOUT_MS) {
        a90_console_printf("gpu.h5.kms.error=timeout-too-large max_ms=%d\r\n",
                           GPU_G0_MAX_TIMEOUT_MS);
        return -EINVAL;
    }
    if (hold_ms < 0 || hold_ms > GPU_H5_VISUAL_HOLD_MAX_MS) {
        a90_console_printf("gpu.h5.vis.error=bad-hold max_ms=%d\r\n",
                           GPU_H5_VISUAL_HOLD_MAX_MS);
        return -EINVAL;
    }

    a90_console_printf("gpu.h5.kms.version=1\r\n");
    a90_console_printf("gpu.h5.kms.scope=first-triangle-h5-visual-close-held-kms-probe\r\n");
    a90_console_printf("gpu.h5.kms.kgsl_path=%s\r\n", GPU_G0_DEVNODE);
    a90_console_printf("gpu.h5.kms.drm_path=/dev/dri/card0\r\n");
    a90_console_printf("gpu.h5.kms.timeout_ms=%d\r\n", timeout_ms);
    a90_console_printf("gpu.h5.vis.version=1\r\n");
    a90_console_printf("gpu.h5.vis.mode=linear-nonzero-mask-solid-fill-centered\r\n");
    a90_console_printf("gpu.h5.vis.hold_ms=%d\r\n", hold_ms);
    a90_console_printf("gpu.h5.vis.hold_max_ms=%d\r\n", GPU_H5_VISUAL_HOLD_MAX_MS);
    a90_console_printf("gpu.h5.kms.kgsl_source=h3-blend-output-readback-changed\r\n");
    a90_console_printf("gpu.h5.kms.blit_mode=h3-private-linear-snapshot-solid-triangle-mask-to-kms-dumb-framebuffer\r\n");
    a90_console_printf("gpu.h5.kms.raw_tile_order_visualization=0\r\n");
    a90_console_printf("gpu.h5.kms.linearized_tile6_3_a2d_blit=1\r\n");
    a90_console_printf("gpu.h5.kms.zero_copy_attempted=0\r\n");
    a90_console_printf("gpu.h5.kms.scaled_plane_attempted=0\r\n");
    a90_console_printf("gpu.h5.kms.kms_blit_attempted=1\r\n");
    a90_console_printf("gpu.h5.kms.power_write_attempted=0\r\n");
    a90_console_printf("gpu.h5.kms.proprietary_blob_attempted=0\r\n");
    stop_auto_hud(false);
    a90_console_printf("gpu.h5.vis.autohud_stop_attempted=1\r\n");

    if (materialize_devnode) {
        int mat_rc = gpu_g0_materialize_devnode();

        a90_console_printf("gpu.h5.kms.materialize_requested=1\r\n");
        a90_console_printf("gpu.h5.kms.materialize_rc=%d\r\n", mat_rc);
        if (mat_rc < 0) {
            return mat_rc;
        }
    } else {
        a90_console_printf("gpu.h5.kms.materialize_requested=0\r\n");
    }

    collect_rc = gpu_h3_draw_snapshot_collect_child(timeout_ms, &run);
    h3 = &run.payload.result;
    a90_console_printf("gpu.h5.kms.child_pid=%ld\r\n", (long)run.child_pid);
    a90_console_printf("gpu.h5.kms.child_collect_rc=%d\r\n", collect_rc);
    a90_console_printf("gpu.h5.kms.child_payload_bytes_read=%u\r\n",
                       (unsigned int)run.payload_bytes_read);
    a90_console_printf("gpu.h5.kms.child_payload_bytes_expected=%u\r\n",
                       (unsigned int)sizeof(run.payload));
    a90_console_printf("gpu.h5.kms.h3_result=%s\r\n",
                       run.got_result ? (gpu_h3_draw_envelope_result_retired(h3) ?
                                         (h3->readback_changed_count > 0 ?
                                          "draw-retired-readback-changed" :
                                          "draw-retired-readback-unchanged") :
                                         "returned-error") :
                       (run.timed_out ? "timeout" : "no-result"));
    a90_console_printf("gpu.h5.kms.h3_timed_out=%d\r\n", run.timed_out ? 1 : 0);
    a90_console_printf("gpu.h5.kms.h3_child_killed=%d\r\n", run.child_killed ? 1 : 0);
    a90_console_printf("gpu.h5.kms.h3_child_reaped=%d\r\n", run.child_reaped ? 1 : 0);
    a90_console_printf("gpu.h5.kms.h3_child_status=0x%x\r\n", run.child_status);
    if (run.got_result) {
        a90_console_printf("gpu.h5.kms.h3_submit_rc=%d\r\n", h3->submit_rc);
        a90_console_printf("gpu.h5.kms.h3_wait_rc=%d\r\n", h3->wait_rc);
        a90_console_printf("gpu.h5.kms.h3_readback_sync_rc=%d\r\n", h3->readback_sync_rc);
        a90_console_printf("gpu.h5.kms.h3_readback_changed_count=%u\r\n",
                           h3->readback_changed_count);
        a90_console_printf("gpu.h5.kms.h3_readback_first_changed_index=%u\r\n",
                           h3->readback_first_changed_index);
        a90_console_printf("gpu.h5.kms.h3_readback_first_changed_value=0x%x\r\n",
                           h3->readback_first_changed_value);
        a90_console_printf("gpu.h5.kms.h3_color_flag_changed_count=%u\r\n",
                           h3->color_flag_changed_count);
        a90_console_printf("gpu.h5.kms.h3_linear_blit_attempted=%u\r\n",
                           h3->linear_blit_attempted);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_changed_count=%u\r\n",
                           h3->linear_readback_changed_count);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_first_changed_index=%u\r\n",
                           h3->linear_readback_first_changed_index);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_first_changed_value=0x%x\r\n",
                           h3->linear_readback_first_changed_value);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_nonzero_count=%u\r\n",
                           h3->linear_readback_nonzero_count);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_first_nonzero_index=%u\r\n",
                           h3->linear_readback_first_nonzero_index);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_first_nonzero_value=0x%x\r\n",
                           h3->linear_readback_first_nonzero_value);
        a90_console_printf("gpu.h5.kms.h3_linear_readback0=0x%x\r\n",
                           h3->linear_readback0);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_center=0x%x\r\n",
                           h3->linear_readback_center);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_corner_tr=0x%x\r\n",
                           h3->linear_readback_corner_tr);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_corner_bl=0x%x\r\n",
                           h3->linear_readback_corner_bl);
        a90_console_printf("gpu.h5.kms.h3_linear_readback_corner_br=0x%x\r\n",
                           h3->linear_readback_corner_br);
        a90_console_printf("gpu.h5.kms.h3_linear_center_nonzero=%u\r\n",
                           h3->linear_center_nonzero);
        a90_console_printf("gpu.h5.kms.h3_linear_exterior_corners_zero=%u\r\n",
                           h3->linear_exterior_corners_zero);
        a90_console_printf("gpu.h5.kms.strict_linear_triangle_sample_proof=%u\r\n",
                           (h3->linear_readback_nonzero_count > 0U &&
                            h3->linear_center_nonzero != 0U &&
                            h3->linear_exterior_corners_zero != 0U) ? 1U : 0U);
        a90_console_printf("gpu.h5.kms.h3_total_elapsed_ms=%ld\r\n",
                           h3->total_elapsed_ms);
    }

    if (!run.got_result ||
        !gpu_h3_draw_envelope_result_retired(h3) ||
        h3->readback_changed_count == 0U ||
        h3->linear_blit_attempted == 0U ||
        h3->linear_readback_nonzero_count == 0U ||
        h3->linear_center_nonzero == 0U ||
        h3->linear_exterior_corners_zero == 0U) {
        a90_console_printf("gpu.h5.kms.result=h3-linear-readback-failed\r\n");
        a90_console_printf("gpu.h5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return collect_rc < 0 ? collect_rc : -EIO;
    }

    stage_started_ms = monotonic_millis();
    begin_rc = a90_kms_begin_frame(0x050505);
    begin_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_kms_info(&kms_info);
    a90_console_printf("gpu.h5.kms.begin_frame_elapsed_ms=%ld\r\n", begin_elapsed_ms);
    a90_console_printf("gpu.h5.kms.begin_frame_rc=%d\r\n", begin_rc);
    a90_console_printf("gpu.h5.kms.fb_initialized=%d\r\n", kms_info.initialized ? 1 : 0);
    a90_console_printf("gpu.h5.kms.fb_width=%u\r\n", kms_info.width);
    a90_console_printf("gpu.h5.kms.fb_height=%u\r\n", kms_info.height);
    a90_console_printf("gpu.h5.kms.fb_stride=%u\r\n", kms_info.stride);
    a90_console_printf("gpu.h5.kms.fb_id=%u\r\n", kms_info.fb_id);
    a90_console_printf("gpu.h5.kms.current_buffer=%u\r\n", kms_info.current_buffer);
    if (begin_rc < 0) {
        a90_console_printf("gpu.h5.kms.result=kms-begin-frame-failed\r\n");
        a90_console_printf("gpu.h5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return -EIO;
    }

    stage_started_ms = monotonic_millis();
    blit_rc = gpu_h5_blit_h3_readback_to_kms(run.payload.color_words,
                                             h3,
                                             &rect_x,
                                             &rect_y,
                                             &rect_w,
                                             &rect_h,
                                             &scale);
    blit_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.h5.kms.blit_elapsed_ms=%ld\r\n", blit_elapsed_ms);
    a90_console_printf("gpu.h5.kms.blit_rc=%d\r\n", blit_rc);
    a90_console_printf("gpu.h5.kms.blit_rect=%u,%u,%u,%u\r\n",
                       rect_x, rect_y, rect_w, rect_h);
    a90_console_printf("gpu.h5.kms.blit_scale=%u\r\n", scale);
    if (blit_rc < 0) {
        a90_console_printf("gpu.h5.kms.result=kms-blit-failed\r\n");
        a90_console_printf("gpu.h5.kms.total_elapsed_ms=%ld\r\n",
                           monotonic_millis() - total_started_ms);
        return blit_rc;
    }

    stage_started_ms = monotonic_millis();
    present_rc = a90_kms_present("gpu-h5-triangle-kms", true);
    present_elapsed_ms = monotonic_millis() - stage_started_ms;
    a90_console_printf("gpu.h5.kms.present_elapsed_ms=%ld\r\n", present_elapsed_ms);
    a90_console_printf("gpu.h5.kms.present_rc=%d\r\n", present_rc);
    a90_console_printf("gpu.h5.kms.result=%s\r\n",
                       present_rc == 0 ? "h3-visual-triangle-kms-presented" :
                       "kms-present-failed");
    if (present_rc == 0 && hold_ms > 0) {
        long hold_started_ms = monotonic_millis();

        a90_console_printf("gpu.h5.vis.hold_begin=1\r\n");
        usleep((useconds_t)hold_ms * 1000U);
        a90_console_printf("gpu.h5.vis.hold_elapsed_ms=%ld\r\n",
                           monotonic_millis() - hold_started_ms);
        a90_console_printf("gpu.h5.vis.result=triangle-presented-held\r\n");
    } else if (present_rc == 0) {
        a90_console_printf("gpu.h5.vis.result=triangle-presented-no-hold\r\n");
    } else {
        a90_console_printf("gpu.h5.vis.result=kms-present-failed\r\n");
    }
    a90_console_printf("gpu.h5.kms.total_elapsed_ms=%ld\r\n",
                       monotonic_millis() - total_started_ms);
    return present_rc == 0 ? 0 : -EIO;
}

static int handle_gpu(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "g0-status";
    int timeout_ms = GPU_G0_DEFAULT_TIMEOUT_MS;
    int hold_ms = GPU_H5_VISUAL_HOLD_DEFAULT_MS;
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
    if (strcmp(subcommand, "c1-compute-invocationid-probe") == 0 ||
        strcmp(subcommand, "compute-invocationid-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.c1.compute.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu c1-compute-invocationid-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_c1_compute_invocationid_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "c2-compute-pattern-probe") == 0 ||
        strcmp(subcommand, "compute-pattern-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.c2.compute.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu c2-compute-pattern-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_c2_compute_pattern_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "c3-compute-kms-probe") == 0 ||
        strcmp(subcommand, "compute-kms-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.c3.kms.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--hold-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &hold_ms)) {
                    a90_console_printf("gpu.c3.vis.error=bad-hold\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu c3-compute-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_c3_compute_kms_probe(timeout_ms, materialize_devnode, hold_ms);
    }
    if (strcmp(subcommand, "d1-texture-checkerboard-probe") == 0 ||
        strcmp(subcommand, "texture-checkerboard-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.d1.texture.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu d1-texture-checkerboard-probe [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_d1_texture_checkerboard_probe(timeout_ms, materialize_devnode);
    }
    if (strcmp(subcommand, "d2-realframe-texture-probe") == 0 ||
        strcmp(subcommand, "realframe-texture-probe") == 0) {
        const char *manifest_path = NULL;
        uint32_t frame_index = GPU_D2_REALFRAME_DEFAULT_FRAME_INDEX;

        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.d2.realframe.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--frame-index") == 0) {
                if (index + 1 >= argc ||
                    !parse_u32_arg(argv[index + 1], 0, VIDEO_STREAM_MAX_FRAMES - 1U,
                                   &frame_index)) {
                    a90_console_printf("gpu.d2.realframe.error=bad-frame-index\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--preset") == 0) {
                if (index + 1 >= argc ||
                    strcmp(argv[index + 1], VIDEO_CACHE_PRESET_BADAPPLE_NAME) != 0) {
                    a90_console_printf("gpu.d2.realframe.error=unsupported-preset\r\n");
                    return -EINVAL;
                }
                manifest_path = GPU_D2_REALFRAME_BADAPPLE_MANIFEST_PATH;
                ++index;
            } else if (strcmp(argv[index], "--manifest") == 0) {
                if (index + 1 >= argc || argv[index + 1][0] != '/') {
                    a90_console_printf("gpu.d2.realframe.error=bad-manifest\r\n");
                    return -EINVAL;
                }
                manifest_path = argv[index + 1];
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu d2-realframe-texture-probe [--preset badapple|--manifest PATH] [--frame-index N] [--timeout-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_d2_realframe_texture_probe(timeout_ms,
                                              materialize_devnode,
                                              manifest_path,
                                              frame_index);
    }
    if (strcmp(subcommand, "d3-video-texture-present-probe") == 0 ||
        strcmp(subcommand, "video-texture-present-probe") == 0) {
        uint32_t requested_frames = GPU_D3_VIDEO_DEFAULT_FRAMES;
        uint32_t start_frame = 0U;
        int hold_ms = 0;

        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.d3.video.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--frames") == 0) {
                if (index + 1 >= argc ||
                    !parse_u32_arg(argv[index + 1], 1, GPU_D3_VIDEO_MAX_FRAMES,
                                   &requested_frames)) {
                    a90_console_printf("gpu.d3.video.error=bad-frames\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--start-frame") == 0) {
                if (index + 1 >= argc ||
                    !parse_u32_arg(argv[index + 1], 0, VIDEO_STREAM_MAX_FRAMES - 1U,
                                   &start_frame)) {
                    a90_console_printf("gpu.d3.video.error=bad-start-frame\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--hold-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &hold_ms)) {
                    a90_console_printf("gpu.d3.video.error=bad-hold\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--preset") == 0) {
                if (index + 1 >= argc ||
                    strcmp(argv[index + 1], VIDEO_CACHE_PRESET_BADAPPLE_NAME) != 0) {
                    a90_console_printf("gpu.d3.video.error=unsupported-preset\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu d3-video-texture-present-probe [--preset badapple] [--start-frame N] [--frames N] [--timeout-ms N] [--hold-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_d3_video_texture_present_probe(timeout_ms,
                                                 materialize_devnode,
                                                 requested_frames,
                                                 hold_ms,
                                                 start_frame);
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
    if (strcmp(subcommand, "h5-triangle-kms-probe") == 0 ||
        strcmp(subcommand, "triangle-kms-probe") == 0) {
        for (index = 2; index < argc; ++index) {
            if (strcmp(argv[index], "--timeout-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &timeout_ms)) {
                    a90_console_printf("gpu.h5.kms.error=bad-timeout\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--hold-ms") == 0) {
                if (index + 1 >= argc || !gpu_g0_parse_int(argv[index + 1], &hold_ms)) {
                    a90_console_printf("gpu.h5.vis.error=bad-hold\r\n");
                    return -EINVAL;
                }
                ++index;
            } else if (strcmp(argv[index], "--materialize-devnode") == 0) {
                materialize_devnode = true;
            } else {
                a90_console_printf("usage: gpu h5-triangle-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]\r\n");
                return -EINVAL;
            }
        }
        return gpu_h5_triangle_kms_probe(timeout_ms, materialize_devnode, hold_ms);
    }
    if (strcmp(subcommand, "g0-open-probe") != 0) {
        a90_console_printf("usage: gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]|g2-gpuobj-probe [--timeout-ms N] [--materialize-devnode]|g2-mmap-probe [--timeout-ms N] [--materialize-devnode]|g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]|h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]|h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]|h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]|c1-compute-invocationid-probe [--timeout-ms N] [--materialize-devnode]|c2-compute-pattern-probe [--timeout-ms N] [--materialize-devnode]|c3-compute-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]|d1-texture-checkerboard-probe [--timeout-ms N] [--materialize-devnode]|d2-realframe-texture-probe [--preset badapple|--manifest PATH] [--frame-index N] [--timeout-ms N] [--materialize-devnode]|d3-video-texture-present-probe [--preset badapple] [--start-frame N] [--frames N] [--timeout-ms N] [--hold-ms N] [--materialize-devnode]|g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]|g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]|h5-triangle-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]]\r\n");
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
    { "gpu", handle_gpu, "gpu [g0-status|g0-fwclass-prepare|g0-open-probe [--timeout-ms N] [--rdwr] [--materialize-devnode]|g1-context-probe [--timeout-ms N] [--materialize-devnode]|g2-gpuobj-probe [--timeout-ms N] [--materialize-devnode]|g2-mmap-probe [--timeout-ms N] [--materialize-devnode]|g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]|h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]|h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]|h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]|c1-compute-invocationid-probe [--timeout-ms N] [--materialize-devnode]|c2-compute-pattern-probe [--timeout-ms N] [--materialize-devnode]|c3-compute-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]|d1-texture-checkerboard-probe [--timeout-ms N] [--materialize-devnode]|d2-realframe-texture-probe [--preset badapple|--manifest PATH] [--frame-index N] [--timeout-ms N] [--materialize-devnode]|d3-video-texture-present-probe [--preset badapple] [--start-frame N] [--frames N] [--timeout-ms N] [--hold-ms N] [--materialize-devnode]|g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]|g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]|h5-triangle-kms-probe [--timeout-ms N] [--hold-ms N] [--materialize-devnode]]", CMD_NONE, A90_CMD_GROUP_CORE },
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
