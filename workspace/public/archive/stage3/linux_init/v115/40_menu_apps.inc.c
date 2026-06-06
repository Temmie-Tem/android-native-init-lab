/* Included by stage3/linux_init/init_v115.c. Do not compile standalone. */

static void kms_draw_menu_section(struct a90_fb *fb,
                                  const struct screen_menu_page *page,
                                  size_t selected);
static int cmd_statushud(void);
static int cmd_recovery(void);
static int draw_screen_log_summary(void);
static int draw_screen_network_summary(void);
static int draw_screen_input_monitor_app(void);
static int draw_screen_display_test_page(unsigned int page_index);
static void cutout_calibration_init(struct cutout_calibration_state *cal);
static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms);
static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive);
static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms);
static uint32_t shrink_text_scale(const char *text, uint32_t scale, uint32_t max_width);
static void restore_auto_hud_if_needed(bool restore_hud);
static void input_monitor_app_reset(void);
static void input_monitor_app_tick(void);
static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index);

static int draw_screen_about_app(enum screen_app_id app_id) {
    return a90_app_about_draw(app_id);
}


static int screen_app_start_cpu_stress(pid_t *pid_out,
                                       long seconds,
                                       unsigned int workers) {
    char seconds_arg[16];
    char workers_arg[16];
    char *const argv[] = {
        CPUSTRESS_HELPER,
        seconds_arg,
        workers_arg,
        NULL
    };
    struct a90_run_config config = {
        .tag = "cpustress-app",
        .argv = argv,
        .stdio_mode = A90_RUN_STDIO_NULL,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .stop_timeout_ms = 2000,
    };

    snprintf(seconds_arg, sizeof(seconds_arg), "%ld", seconds);
    snprintf(workers_arg, sizeof(workers_arg), "%u", workers);
    return a90_run_spawn(&config, pid_out);
}

static bool screen_app_reap_cpu_stress(pid_t *pid,
                                       bool *failed) {
    int status = 0;
    int rc;

    if (*pid <= 0) {
        return true;
    }

    rc = a90_run_reap_pid(*pid, &status);
    if (rc == 1) {
        struct a90_run_result result = {
            .pid = *pid,
            .status = status,
        };

        *pid = -1;
        if (a90_run_result_to_rc(&result) != 0) {
            *failed = true;
        }
        return true;
    }
    if (rc < 0) {
        *pid = -1;
        *failed = true;
        return true;
    }
    return false;
}

static void screen_app_stop_cpu_stress(pid_t *pid) {
    if (*pid > 0) {
        (void)a90_run_stop_pid_ex(*pid, "cpustress-app", 2000, true, NULL);
        *pid = -1;
    }
}

static void auto_hud_loop(unsigned int refresh_sec) {
    struct a90_input_context ctx;
    bool menu_active = true;
    enum screen_app_id active_app = SCREEN_APP_NONE;
    struct a90_menu_state menu_state;
    pid_t app_stress_pid = -1;
    unsigned int app_stress_workers = 8;
    long app_stress_deadline_ms = 0;
    long app_stress_duration_ms = 10000L;
    bool app_stress_done = false;
    bool app_stress_failed = false;
    unsigned int display_test_page = 0;
    struct cutout_calibration_state cutout_cal;
    unsigned int cutout_down_mask = 0;
    long cutout_power_down_ms = 0;
    long cutout_last_power_up_ms = 0;
    bool has_input;
    int timeout_ms;

    signal(SIGTERM, SIG_DFL);
    has_input = (a90_input_open(&ctx, "autohud") == 0);
    timeout_ms = (refresh_sec > 0 && refresh_sec <= 60) ? (int)(refresh_sec * 1000) : 2000;
    a90_menu_state_init(&menu_state);
    cutout_calibration_init(&cutout_cal);
    a90_controller_set_menu_active(menu_active);

    while (1) {
        struct pollfd fds[2];
        enum a90_controller_menu_request menu_request;
        int poll_rc;
        int fi;

        menu_request = a90_controller_consume_menu_request();
        if (menu_request != A90_CONTROLLER_MENU_REQUEST_NONE) {
            if (active_app == SCREEN_APP_CPU_STRESS && app_stress_pid > 0) {
                screen_app_stop_cpu_stress(&app_stress_pid);
            }
            active_app = SCREEN_APP_NONE;
            menu_active = menu_request == A90_CONTROLLER_MENU_REQUEST_SHOW;
            a90_menu_state_init(&menu_state);
            display_test_page = 0;
            cutout_calibration_init(&cutout_cal);
            cutout_down_mask = 0;
            cutout_power_down_ms = 0;
            cutout_last_power_up_ms = 0;
        }
        a90_controller_set_menu_state(menu_active || active_app != SCREEN_APP_NONE,
                            menu_active &&
                            active_app == SCREEN_APP_NONE &&
                            a90_menu_state_page_id(&menu_state) == SCREEN_MENU_PAGE_POWER);
        if (active_app == SCREEN_APP_INPUT_MONITOR) {
            input_monitor_app_tick();
        }

        /* draw */
        if (active_app == SCREEN_APP_LOG) {
            draw_screen_log_summary();
        } else if (active_app == SCREEN_APP_NETWORK) {
            draw_screen_network_summary();
        } else if (active_app == SCREEN_APP_INPUT_MONITOR) {
            draw_screen_input_monitor_app();
        } else if (active_app == SCREEN_APP_DISPLAY_TEST) {
            draw_screen_display_test_page(display_test_page);
        } else if (active_app == SCREEN_APP_CUTOUT_CAL) {
            draw_screen_cutout_calibration(&cutout_cal, true);
        } else if (a90_menu_app_is_about(active_app)) {
            draw_screen_about_app(active_app);
        } else if (active_app == SCREEN_APP_CPU_STRESS) {
            long now_ms = monotonic_millis();
            long remaining_ms = app_stress_deadline_ms - now_ms;

            if (screen_app_reap_cpu_stress(&app_stress_pid, &app_stress_failed) &&
                !app_stress_failed) {
                app_stress_done = true;
            } else if (app_stress_pid > 0 && now_ms > app_stress_deadline_ms + 2000L) {
                screen_app_stop_cpu_stress(&app_stress_pid);
                app_stress_done = true;
                app_stress_failed = true;
            }
            if (remaining_ms < 0) {
                remaining_ms = 0;
            }
            draw_screen_cpu_stress_app(app_stress_pid > 0,
                                       app_stress_done,
                                       app_stress_failed,
                                       remaining_ms,
                                       app_stress_duration_ms);
        } else if (a90_kms_begin_frame(0x000000) == 0) {
            const struct screen_menu_page *page = a90_menu_state_page(&menu_state);
            struct a90_hud_storage_status storage = current_hud_storage_status();

            a90_hud_draw_status_overlay(a90_kms_framebuffer(), &storage, 0, 0);
            if (menu_active)
                kms_draw_menu_section(a90_kms_framebuffer(),
                                      page,
                                      a90_menu_state_selected_index(&menu_state));
            else
                a90_hud_draw_hud_log_tail(a90_kms_framebuffer());
            a90_kms_present("autohud", false);
        }

        if (!has_input) {
            sleep(refresh_sec);
            continue;
        }

        fds[0].fd = ctx.fd0; fds[0].events = POLLIN;
        fds[1].fd = ctx.fd3; fds[1].events = POLLIN;
        poll_rc = poll(fds, 2, active_app == SCREEN_APP_NONE ? timeout_ms : 500);
        if (poll_rc <= 0)
            continue; /* timeout → redraw */

        for (fi = 0; fi < 2; fi++) {
            struct input_event ev;
            if (!(fds[fi].revents & POLLIN))
                continue;
            while (read(fds[fi].fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (active_app == SCREEN_APP_INPUT_MONITOR && ev.type == EV_KEY) {
                    if (input_monitor_app_feed_event(&ev, fi)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        a90_controller_set_menu_active(true);
                    }
                    continue;
                }

                if (active_app == SCREEN_APP_CUTOUT_CAL && ev.type == EV_KEY) {
                    if (cutout_calibration_feed_key(&cutout_cal,
                                                    &ev,
                                                    &cutout_down_mask,
                                                    &cutout_power_down_ms,
                                                    &cutout_last_power_up_ms)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        a90_controller_set_menu_active(true);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                    }
                    continue;
                }

                if (ev.type != EV_KEY || ev.value != 1)
                    continue;

                if (active_app != SCREEN_APP_NONE) {
                    if (active_app == SCREEN_APP_DISPLAY_TEST) {
                        if (ev.code == KEY_VOLUMEUP) {
                            display_test_page =
                                (display_test_page + DISPLAY_TEST_PAGE_COUNT - 1) %
                                DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                        if (ev.code == KEY_VOLUMEDOWN) {
                            display_test_page =
                                (display_test_page + 1) % DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                    }
                    if (active_app == SCREEN_APP_CPU_STRESS && app_stress_pid > 0) {
                        screen_app_stop_cpu_stress(&app_stress_pid);
                    }
                    active_app = SCREEN_APP_NONE;
                    menu_active = true;
                    a90_controller_set_menu_active(true);
                    continue;
                }

                if (ev.code == KEY_VOLUMEUP) {
                    if (!menu_active) {
                        menu_active = true;
                        a90_menu_state_init(&menu_state);
                    } else {
                        a90_menu_state_move(&menu_state, -1);
                    }
                } else if (ev.code == KEY_VOLUMEDOWN) {
                    if (!menu_active) {
                        menu_active = true;
                        a90_menu_state_init(&menu_state);
                    } else {
                        a90_menu_state_move(&menu_state, 1);
                    }
                } else if (ev.code == KEY_POWER && menu_active) {
                    const struct screen_menu_item *item = a90_menu_state_selected(&menu_state);

                    if (item == NULL) {
                        continue;
                    }

                    switch (item->action) {
                    case SCREEN_MENU_RESUME:
                        menu_active = false;
                        a90_menu_state_init(&menu_state);
                        a90_controller_set_menu_active(false);
                        break;
                    case SCREEN_MENU_SUBMENU:
                        a90_menu_state_set_page(&menu_state, item->target);
                        break;
                    case SCREEN_MENU_BACK:
                        a90_menu_state_back(&menu_state);
                        break;
                    case SCREEN_MENU_STATUS:
                        cmd_statushud();
                        menu_active = false;
                        a90_controller_set_menu_active(false);
                        break;
                    case SCREEN_MENU_LOG:
                        active_app = SCREEN_APP_LOG;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_NET_STATUS:
                        active_app = SCREEN_APP_NETWORK;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_INPUT_MONITOR:
                        input_monitor_app_reset();
                        active_app = SCREEN_APP_INPUT_MONITOR;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_DISPLAY_TEST:
                        display_test_page = 0;
                        active_app = SCREEN_APP_DISPLAY_TEST;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CUTOUT_CAL:
                        cutout_calibration_init(&cutout_cal);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                        active_app = SCREEN_APP_CUTOUT_CAL;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_ABOUT_VERSION:
                    case SCREEN_MENU_ABOUT_CHANGELOG:
                    case SCREEN_MENU_ABOUT_CREDITS:
                    case SCREEN_MENU_CHANGELOG_0840:
                    case SCREEN_MENU_CHANGELOG_0839:
                    case SCREEN_MENU_CHANGELOG_0838:
                    case SCREEN_MENU_CHANGELOG_0837:
                    case SCREEN_MENU_CHANGELOG_0836:
                    case SCREEN_MENU_CHANGELOG_0835:
                    case SCREEN_MENU_CHANGELOG_0834:
                    case SCREEN_MENU_CHANGELOG_0833:
                    case SCREEN_MENU_CHANGELOG_0832:
                    case SCREEN_MENU_CHANGELOG_0831:
                    case SCREEN_MENU_CHANGELOG_0830:
                    case SCREEN_MENU_CHANGELOG_0829:
                    case SCREEN_MENU_CHANGELOG_0828:
                    case SCREEN_MENU_CHANGELOG_0827:
                    case SCREEN_MENU_CHANGELOG_0826:
                    case SCREEN_MENU_CHANGELOG_0825:
                    case SCREEN_MENU_CHANGELOG_0824:
                    case SCREEN_MENU_CHANGELOG_0823:
                    case SCREEN_MENU_CHANGELOG_0822:
                    case SCREEN_MENU_CHANGELOG_0821:
                    case SCREEN_MENU_CHANGELOG_0820:
                    case SCREEN_MENU_CHANGELOG_0819:
                    case SCREEN_MENU_CHANGELOG_0818:
                    case SCREEN_MENU_CHANGELOG_0817:
                    case SCREEN_MENU_CHANGELOG_0816:
                    case SCREEN_MENU_CHANGELOG_0815:
                    case SCREEN_MENU_CHANGELOG_0814:
                    case SCREEN_MENU_CHANGELOG_0813:
                    case SCREEN_MENU_CHANGELOG_0812:
                    case SCREEN_MENU_CHANGELOG_0811:
                    case SCREEN_MENU_CHANGELOG_0810:
                    case SCREEN_MENU_CHANGELOG_089:
                    case SCREEN_MENU_CHANGELOG_088:
                    case SCREEN_MENU_CHANGELOG_087:
                    case SCREEN_MENU_CHANGELOG_086:
                    case SCREEN_MENU_CHANGELOG_085:
                    case SCREEN_MENU_CHANGELOG_084:
                    case SCREEN_MENU_CHANGELOG_083:
                    case SCREEN_MENU_CHANGELOG_082:
                    case SCREEN_MENU_CHANGELOG_081:
                    case SCREEN_MENU_CHANGELOG_080:
                    case SCREEN_MENU_CHANGELOG_075:
                    case SCREEN_MENU_CHANGELOG_074:
                    case SCREEN_MENU_CHANGELOG_073:
                    case SCREEN_MENU_CHANGELOG_072:
                    case SCREEN_MENU_CHANGELOG_071:
                    case SCREEN_MENU_CHANGELOG_070:
                    case SCREEN_MENU_CHANGELOG_060:
                    case SCREEN_MENU_CHANGELOG_051:
                    case SCREEN_MENU_CHANGELOG_050:
                    case SCREEN_MENU_CHANGELOG_041:
                    case SCREEN_MENU_CHANGELOG_040:
                    case SCREEN_MENU_CHANGELOG_030:
                    case SCREEN_MENU_CHANGELOG_020:
                    case SCREEN_MENU_CHANGELOG_010:
                        active_app = a90_menu_app_from_action(item->action);
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CPU_STRESS_5:
                    case SCREEN_MENU_CPU_STRESS_10:
                    case SCREEN_MENU_CPU_STRESS_30:
                    case SCREEN_MENU_CPU_STRESS_60:
                    {
                        long stress_seconds = a90_menu_cpu_stress_seconds(item->action);

                        active_app = SCREEN_APP_CPU_STRESS;
                        menu_active = false;
                        app_stress_done = false;
                        app_stress_failed = false;
                        app_stress_duration_ms = stress_seconds * 1000L;
                        app_stress_deadline_ms = monotonic_millis() + app_stress_duration_ms;
                        if (screen_app_start_cpu_stress(&app_stress_pid,
                                                        stress_seconds,
                                                        app_stress_workers) < 0) {
                            app_stress_failed = true;
                            app_stress_done = true;
                            app_stress_pid = -1;
                        }
                        break;
                    }
                    case SCREEN_MENU_RECOVERY:
                        a90_controller_set_menu_active(false);
                        a90_controller_clear_menu_request();
                        a90_input_close(&ctx);
                        cmd_recovery();
                        return;
                    case SCREEN_MENU_REBOOT:
                        a90_controller_set_menu_active(false);
                        a90_controller_clear_menu_request();
                        a90_input_close(&ctx);
                        sync();
                        reboot(RB_AUTOBOOT);
                        return;
                    case SCREEN_MENU_POWEROFF:
                        a90_controller_set_menu_active(false);
                        a90_controller_clear_menu_request();
                        a90_input_close(&ctx);
                        sync();
                        reboot(RB_POWER_OFF);
                        return;
                    }
                }
            }
        }
    }
}

static int start_auto_hud(int refresh_sec, bool verbose) {
    pid_t pid;
    int saved_errno;

    refresh_sec = clamp_hud_refresh(refresh_sec);

    stop_auto_hud(false);
    a90_controller_clear_menu_request();
    a90_controller_set_menu_active(true);

    pid = fork();
    if (pid < 0) {
        saved_errno = errno;
        a90_controller_clear_menu_ipc();
        if (verbose) {
            a90_console_printf("autohud: fork: %s\r\n", strerror(saved_errno));
        }
        return -saved_errno;
    }
    if (pid == 0) {
        auto_hud_loop((unsigned int)refresh_sec);
        _exit(0);
    }

    a90_service_set_pid(A90_SERVICE_HUD, pid);
    if (verbose) {
        a90_console_printf("autohud: pid=%ld refresh=%ds\r\n", (long)pid, refresh_sec);
    }
    return 0;
}

static int cmd_autohud(char **argv, int argc) {
    int refresh_sec = 2;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        a90_console_printf("usage: autohud [sec]\r\n");
        return -EINVAL;
    }

    return start_auto_hud(refresh_sec, true);
}

static int cmd_stophud(void) {
    stop_auto_hud(true);
    return 0;
}

static int cmd_clear_display(void) {
    stop_auto_hud(false);
    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (a90_kms_present("clear", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void boot_auto_frame(void) {
    if (a90_kms_begin_frame(0x000000) == 0) {
        a90_hud_draw_boot_splash(a90_kms_framebuffer());
        if (a90_kms_present("bootframe", true) == 0) {
            klogf("<6>A90v115: boot splash applied\n");
            if (!boot_splash_recorded) {
                boot_splash_recorded = true;
                a90_logf("boot", "display boot splash applied");
                a90_timeline_record(0, 0, "display-splash", "boot splash applied");
            }
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v115: boot splash skipped (%d)\n", saved_errno);
        if (!boot_splash_recorded) {
            boot_splash_recorded = true;
            a90_logf("boot", "display boot splash skipped errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            a90_timeline_record(-saved_errno,
                            saved_errno,
                            "display-splash",
                            "boot splash skipped: %s",
                            strerror(saved_errno));
        }
    }
}

static bool test_key_bit(const char *bitmap, unsigned int code) {
    char copy[1024];
    char *tokens[32];
    char *token;
    char *saveptr = NULL;
    unsigned int bits_per_word = 64;
    unsigned int token_count = 0;
    unsigned int word_index;

    if (strlen(bitmap) >= sizeof(copy)) {
        return false;
    }

    strcpy(copy, bitmap);
    trim_newline(copy);

    for (token = strtok_r(copy, " \t", &saveptr);
         token != NULL;
         token = strtok_r(NULL, " \t", &saveptr)) {
        if (token_count >= (sizeof(tokens) / sizeof(tokens[0]))) {
            return false;
        }
        tokens[token_count++] = token;
    }

    for (word_index = 0; word_index < token_count; ++word_index) {
        unsigned long value = strtoul(tokens[token_count - 1 - word_index], NULL, 16);
        unsigned int bit_base = word_index * bits_per_word;

        if (code >= bit_base && code < bit_base + bits_per_word) {
            unsigned int bit = code - bit_base;
            return ((value >> bit) & 1UL) != 0;
        }
    }

    return false;
}

static int cmd_inputcaps(char **argv, int argc) {
    char event_name[32];
    char key_path[PATH_MAX];
    char bitmap[1024];

    if (argc < 2) {
        a90_console_printf("usage: inputcaps <eventX>\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("inputcaps: invalid event name\r\n");
        return -EINVAL;
    }

    if (snprintf(key_path, sizeof(key_path),
                 "/sys/class/input/%s/device/capabilities/key", event_name) >=
        (int)sizeof(key_path)) {
        a90_console_printf("inputcaps: path too long\r\n");
        return -ENAMETOOLONG;
    }

    if (read_text_file(key_path, bitmap, sizeof(bitmap)) < 0) {
        a90_console_printf("inputcaps: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    trim_newline(bitmap);
    a90_console_printf("%s key-bitmap=%s\r\n", event_name, bitmap);
    a90_console_printf("  KEY_VOLUMEDOWN(114)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEDOWN) ? "yes" : "no");
    a90_console_printf("  KEY_VOLUMEUP(115)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEUP) ? "yes" : "no");
    a90_console_printf("  KEY_POWER(116)=%s\r\n",
            test_key_bit(bitmap, KEY_POWER) ? "yes" : "no");
    return 0;
}

static int cmd_readinput(char **argv, int argc) {
    char event_name[32];
    char dev_path[PATH_MAX];
    int count = 16;
    int fd;
    int index;

    if (argc < 2) {
        a90_console_printf("usage: readinput <eventX> [count]\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("readinput: invalid event name\r\n");
        return -EINVAL;
    }

    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("readinput: invalid count\r\n");
        return -EINVAL;
    }
    if (count <= 0) {
        count = 1;
    }

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        a90_console_printf("readinput: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    fd = open(dev_path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        a90_console_printf("readinput: open %s: %s\r\n", dev_path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("readinput: waiting on %s (%d events), q/Ctrl-C cancels\r\n",
            dev_path, count);

    index = 0;
    while (index < count) {
        struct pollfd fds[2];
        int poll_rc;

        fds[0].fd = fd;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = STDIN_FILENO;
        fds[1].events = POLLIN;
        fds[1].revents = 0;

        poll_rc = poll(fds, 2, -1);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("readinput: poll: %s\r\n", strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }

        if ((fds[1].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                close(fd);
                return a90_console_cancelled("readinput", cancel);
            }
        }

        if ((fds[0].revents & POLLIN) == 0) {
            continue;
        }

        while (index < count) {
            struct input_event event;
            ssize_t rd = read(fd, &event, sizeof(event));

            if (rd < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    break;
                }
                a90_console_printf("readinput: read: %s\r\n", strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
            if (rd != (ssize_t)sizeof(event)) {
                a90_console_printf("readinput: short read %ld\r\n", (long)rd);
                close(fd);
                return -EIO;
            }

            a90_console_printf("event %d: type=0x%04x code=0x%04x value=%d\r\n",
                    index,
                    event.type,
                    event.code,
                    event.value);
            ++index;
        }
        if ((fds[0].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
            a90_console_printf("readinput: poll error revents=0x%x\r\n", fds[0].revents);
            close(fd);
            return -EIO;
        }
    }

    close(fd);
    return 0;
}

static int cmd_recovery(void);

static int cmd_waitkey(char **argv, int argc) {
    struct a90_input_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitkey [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (a90_input_open(&ctx, "waitkey") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitkey: waiting for %d key press(es), q/Ctrl-C cancels\r\n", target);

    while (seen < target) {
        unsigned int code = 0;
        const char *name;

        int wait_rc = a90_input_wait_key_press(&ctx, "waitkey", &code);

        if (wait_rc < 0) {
            a90_input_close(&ctx);
            return wait_rc;
        }

        name = a90_input_key_name(code);
        if (name != NULL) {
            a90_console_printf("key %d: %s (0x%04x)\r\n", seen, name, code);
        } else {
            a90_console_printf("key %d: code=0x%04x\r\n", seen, code);
        }
        ++seen;
    }

    a90_input_close(&ctx);
    return 0;
}

static int cmd_inputlayout(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_input_print_layout();
    return a90_app_inputmon_draw_layout();
}

static int cmd_waitgesture(char **argv, int argc) {
    struct a90_input_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitgesture [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (a90_input_open(&ctx, "waitgesture") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitgesture: waiting for %d gesture(s), q/Ctrl-C cancels\r\n", target);
    a90_console_printf("waitgesture: double=%ldms long=%ldms\r\n",
            A90_INPUT_DOUBLE_CLICK_MS,
            A90_INPUT_LONG_PRESS_MS);

    while (seen < target) {
        struct a90_input_gesture gesture;
        char mask_text[64];
        int wait_rc = a90_input_wait_gesture(&ctx, "waitgesture", &gesture);

        if (wait_rc < 0) {
            a90_input_close(&ctx);
            return wait_rc;
        }

        a90_input_mask_text(gesture.mask, mask_text, sizeof(mask_text));
        a90_console_printf("gesture %d: %s mask=%s clicks=%u duration=%ldms action=%d\r\n",
                seen,
                a90_input_gesture_name(gesture.id),
                mask_text,
                gesture.clicks,
                gesture.duration_ms,
                (int)a90_input_menu_action_from_gesture(&gesture));
        ++seen;
    }

    a90_input_close(&ctx);
    return 0;
}

static struct a90_app_inputmon_state auto_input_monitor;

static void input_monitor_app_reset(void) {
    a90_app_inputmon_reset_state(&auto_input_monitor);
    a90_logf("inputmonitor", "app reset");
}

static void input_monitor_app_tick(void) {
    a90_app_inputmon_tick_state(&auto_input_monitor, false);
}

static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index) {
    return a90_app_inputmon_feed_state(&auto_input_monitor,
                                    event,
                                    source_index,
                                    false,
                                    true);
}

static int cmd_inputmonitor(char **argv, int argc) {
    struct a90_app_inputmon_state monitor;
    struct a90_input_context ctx;
    int target = 24;
    int seen = 0;
    int draw_rc;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: inputmonitor [events]\r\n");
        return -EINVAL;
    }
    if (target < 0) {
        target = 0;
    }

    reap_hud_child();
    stop_auto_hud(false);
    a90_app_inputmon_reset_state(&monitor);

    if (a90_input_open(&ctx, "inputmonitor") < 0) {
        restore_auto_hud_if_needed(true);
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("inputmonitor: raw DOWN/UP/REPEAT + gesture decode\r\n");
    a90_console_printf("inputmonitor: events=%d, 0 means until all-buttons/q/Ctrl-C\r\n", target);
    a90_console_printf("inputmonitor: all-buttons exits only in events=0 mode\r\n");

    draw_rc = a90_app_inputmon_draw_state(&monitor);
    if (draw_rc < 0) {
        a90_input_close(&ctx);
        restore_auto_hud_if_needed(true);
        return draw_rc;
    }

    while (target == 0 || seen < target) {
        struct pollfd fds[3];
        int timeout_ms;
        int poll_rc;
        int index;

        a90_app_inputmon_tick_state(&monitor, true);
        a90_app_inputmon_draw_state(&monitor);

        fds[0].fd = ctx.fd0;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = ctx.fd3;
        fds[1].events = POLLIN;
        fds[1].revents = 0;
        fds[2].fd = STDIN_FILENO;
        fds[2].events = POLLIN;
        fds[2].revents = 0;

        timeout_ms = a90_input_decoder_timeout_ms(&monitor.decoder);
        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("inputmonitor: poll: %s\r\n", strerror(saved_errno));
            a90_input_close(&ctx);
            restore_auto_hud_if_needed(true);
            return -saved_errno;
        }

        if (poll_rc == 0) {
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                a90_input_close(&ctx);
                restore_auto_hud_if_needed(true);
                return a90_console_cancelled("inputmonitor", cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if ((fds[index].revents & POLLIN) != 0) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    unsigned int before_count = monitor.event_count;

                    if (a90_app_inputmon_feed_state(&monitor,
                                                 &event,
                                                 index,
                                                 true,
                                                 target == 0)) {
                        a90_app_inputmon_draw_state(&monitor);
                        a90_input_close(&ctx);
                        restore_auto_hud_if_needed(true);
                        return 0;
                    }
                    if (monitor.event_count > before_count) {
                        ++seen;
                    }
                    a90_app_inputmon_draw_state(&monitor);
                    if (target > 0 && seen >= target) {
                        break;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    a90_console_printf("inputmonitor: read: %s\r\n", strerror(saved_errno));
                    a90_input_close(&ctx);
                    restore_auto_hud_if_needed(true);
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("inputmonitor: poll error revents=0x%x\r\n",
                        fds[index].revents);
                a90_input_close(&ctx);
                restore_auto_hud_if_needed(true);
                return -EIO;
            }
        }
    }

    a90_app_inputmon_tick_state(&monitor, true);
    a90_app_inputmon_draw_state(&monitor);
    a90_input_close(&ctx);
    restore_auto_hud_if_needed(true);
    return 0;
}

struct blind_menu_item {
    const char *name;
    const char *summary;
};

static void kms_draw_menu_section(struct a90_fb *fb,
                                  const struct screen_menu_page *page,
                                  size_t selected) {
    uint32_t scale = 5;
    uint32_t x = fb->width / 24;
    uint32_t line_h = scale * 10;
    uint32_t card_h = line_h + scale * 4;
    uint32_t glyph_h = scale * 7;
    uint32_t slot = line_h + scale * 3;
    uint32_t card_w = fb->width - x * 2;
    uint32_t menu_scale = scale;
    uint32_t y = fb->height / 16;
    uint32_t status_bottom;
    uint32_t divider_y;
    uint32_t menu_y;
    uint32_t item_h = scale * 14;
    uint32_t item_gap = scale * 2;
    uint32_t log_tail_y;
    uint32_t page_scale;
    size_t i;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    status_bottom = y + 3 * slot + card_h;
    divider_y = status_bottom + scale * 5;
    menu_y = divider_y + scale * 17;

    a90_draw_rect(fb, x, divider_y, card_w, 2, 0x383838);
    page_scale = shrink_text_scale(page->title, menu_scale, card_w / 2);
    a90_draw_text(fb, x, divider_y + scale * 2,
                  page->title, 0xffcc33, page_scale);
    a90_draw_text(fb, x, divider_y + scale * 10,
                  "VOL MOVE  PWR SELECT  COMBO BACK",
                  0x909090, menu_scale > 1 ? menu_scale - 1 : menu_scale);

    for (i = 0; i < page->count; ++i) {
        uint32_t iy = menu_y + (uint32_t)i * (item_h + item_gap);
        bool is_sel = (i == selected);
        uint32_t fill = is_sel ? 0x1a3560 : 0x141414;
        uint32_t name_color = is_sel ? 0xffffff : 0x707070;

        a90_draw_rect(fb, x - scale, iy - scale, card_w, item_h, fill);
        if (is_sel)
            a90_draw_rect(fb, x - scale, iy - scale, scale * 2, item_h, 0xffcc33);
        a90_draw_text(fb, x + scale * 3, iy + (item_h - glyph_h) / 2,
                      page->items[i].name, name_color, menu_scale);
    }

    {
        uint32_t last_y = menu_y + (uint32_t)page->count * (item_h + item_gap);
        uint32_t summary_y = last_y + scale * 6;
        const char *summary = page->items[selected].summary;

        log_tail_y = summary_y;

        if (summary_y + glyph_h < fb->height && summary != NULL && summary[0] != '\0') {
            a90_draw_rect(fb, x, summary_y - scale, card_w, 1, 0x282828);
            a90_draw_text(fb, x, summary_y + scale * 2,
                          summary, 0xffcc33,
                          shrink_text_scale(summary, menu_scale, card_w));
            log_tail_y = summary_y + glyph_h + scale * 8;
        }
    }

    a90_hud_draw_log_tail_panel(fb,
                            x,
                            log_tail_y,
                            card_w,
                            fb->height - scale * 42,
                            16,
                            "LIVE LOG TAIL",
                            menu_scale > 3 ? menu_scale - 3 : menu_scale);
}

static void print_blind_menu_selection(const struct blind_menu_item *items,
                                       size_t count,
                                       size_t selected) {
    a90_console_printf("blindmenu: [%d/%d] %s - %s\r\n",
            (int)(selected + 1),
            (int)count,
            items[selected].name,
            items[selected].summary);
}

static uint32_t display_width_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.width > 0 ? info.width : fallback;
}

static uint32_t display_height_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.height > 0 ? info.height : fallback;
}

static uint32_t menu_text_scale(void) {
    uint32_t width = display_width_or(0);

    if (width >= 1080) {
        return 6;
    }
    if (width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t shrink_text_scale(const char *text,
                                  uint32_t scale,
                                  uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int draw_screen_log_summary(void) {
    char boot_summary[64];
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];
    uint32_t scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    const struct shell_last_result *last = a90_shell_last_result();

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));
    snprintf(line1, sizeof(line1), "BOOT %.40s", boot_summary);
    snprintf(line2, sizeof(line2), "LOG %s", a90_log_ready() ? "READY" : "NOT READY");
    snprintf(line3, sizeof(line3), "LAST %.24s RC %d E %d",
             last->command,
             last->code,
             last->saved_errno);
    snprintf(line4, sizeof(line4), "PATH %.48s", a90_log_path());

    scale = menu_text_scale();
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 8;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 12;

    a90_draw_text(a90_kms_framebuffer(), x, y, "A90 LOG SUMMARY", 0xffcc33, scale + 1);
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(), x - scale, y - scale, card_w, line_h * 5, 0x202020);
    a90_draw_text(a90_kms_framebuffer(), x, y, line1, 0xffffff,
                  shrink_text_scale(line1, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line2, 0xffffff,
                  shrink_text_scale(line2, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line3, 0xffffff,
                  shrink_text_scale(line3, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line4, 0xffffff,
                  shrink_text_scale(line4, scale, card_w - scale * 2));

    a90_draw_text(a90_kms_framebuffer(), x, a90_kms_framebuffer()->height - scale * 12,
                  "PRESS ANY BUTTON TO RETURN", 0xffffff,
                  shrink_text_scale("PRESS ANY BUTTON TO RETURN", scale, card_w));

    if (a90_kms_present("screenlog", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_input_monitor_app(void) {
    return a90_app_inputmon_draw_state(&auto_input_monitor);
}

static int draw_screen_info_page(const char *title,
                                 const char *line1,
                                 const char *line2,
                                 const char *line3,
                                 const char *line4) {
    const char *footer = "PRESS ANY BUTTON TO RETURN";
    const char *lines[4];
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    lines[0] = line1;
    lines[1] = line2;
    lines[2] = line3;
    lines[3] = line4;

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 8;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 12;

    a90_draw_text(a90_kms_framebuffer(), x, y, title, 0xffcc33,
                  shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(), x - scale, y - scale, card_w, line_h * 5, 0x202020);
    for (index = 0; index < 4; ++index) {
        a90_draw_text(a90_kms_framebuffer(), x, y + (uint32_t)index * line_h,
                      lines[index] != NULL ? lines[index] : "",
                      0xffffff,
                      shrink_text_scale(lines[index] != NULL ? lines[index] : "",
                                        scale, card_w - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(), x, a90_kms_framebuffer()->height - scale * 12,
                  footer, 0xffffff, shrink_text_scale(footer, scale, card_w));

    if (a90_kms_present("screeninfo", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int clamp_int_value(int value, int min_value, int max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

static void cutout_calibration_clamp(struct cutout_calibration_state *cal) {
    int width = (int)display_width_or(1080);
    int height = (int)display_height_or(2400);
    int min_size = width / 40;
    int max_size = width / 8;
    int margin;

    if (min_size < 18) {
        min_size = 18;
    }
    if (max_size < min_size) {
        max_size = min_size;
    }
    cal->size = clamp_int_value(cal->size, min_size, max_size);
    margin = cal->size / 2 + 2;
    cal->center_x = clamp_int_value(cal->center_x, margin, width - margin);
    cal->center_y = clamp_int_value(cal->center_y, margin, height - margin);
    if ((int)cal->field < 0 || cal->field >= CUTOUT_CAL_FIELD_COUNT) {
        cal->field = CUTOUT_CAL_FIELD_Y;
    }
}

static void cutout_calibration_init(struct cutout_calibration_state *cal) {
    int width = (int)display_width_or(1080);
    int height = (int)display_height_or(2400);

    cal->center_x = width / 2;
    cal->center_y = height / 30;
    cal->size = width / 22;
    cal->field = CUTOUT_CAL_FIELD_Y;
    cutout_calibration_clamp(cal);
}

static void cutout_calibration_adjust(struct cutout_calibration_state *cal,
                                      int direction) {
    int step = 4;

    if (cal->field == CUTOUT_CAL_FIELD_SIZE) {
        step = 2;
    }
    switch (cal->field) {
    case CUTOUT_CAL_FIELD_X:
        cal->center_x += direction * step;
        break;
    case CUTOUT_CAL_FIELD_Y:
        cal->center_y += direction * step;
        break;
    case CUTOUT_CAL_FIELD_SIZE:
        cal->size += direction * step;
        break;
    default:
        break;
    }
    cutout_calibration_clamp(cal);
}

static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms) {
    unsigned int mask;
    long now_ms;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = a90_input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    now_ms = monotonic_millis();
    if (event->value == 1) {
        *down_mask |= mask;
        if ((*down_mask & (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) ==
            (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) {
            return true;
        }
        if (event->code == KEY_VOLUMEUP) {
            cutout_calibration_adjust(cal, -1);
        } else if (event->code == KEY_VOLUMEDOWN) {
            cutout_calibration_adjust(cal, 1);
        } else if (event->code == KEY_POWER) {
            *power_down_ms = now_ms;
        }
        return false;
    }

    *down_mask &= ~mask;
    if (event->code == KEY_POWER) {
        long duration_ms = *power_down_ms > 0 ? now_ms - *power_down_ms : 0;

        *power_down_ms = 0;
        if (duration_ms >= A90_INPUT_LONG_PRESS_MS) {
            return true;
        }
        if (*last_power_up_ms > 0 &&
            now_ms - *last_power_up_ms <= A90_INPUT_DOUBLE_CLICK_MS) {
            *last_power_up_ms = 0;
            return true;
        }
        *last_power_up_ms = now_ms;
        cal->field = (enum cutout_calibration_field)
                     (((int)cal->field + 1) % CUTOUT_CAL_FIELD_COUNT);
    }
    return false;
}

static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive) {
    return a90_app_displaytest_draw_cutout_calibration(cal, interactive);
}

static int draw_screen_display_test_page(unsigned int page_index) {
    struct a90_hud_storage_status storage = current_hud_storage_status();

    return a90_app_displaytest_draw_page(page_index, &storage);
}

static int draw_screen_network_summary(void) {
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];
    struct a90_netservice_status status;

    a90_netservice_status(&status);
    snprintf(line1, sizeof(line1), "NETSERVICE %s",
             status.enabled ? "ENABLED" : "DISABLED");
    snprintf(line2, sizeof(line2), "%s %s %s",
             status.ifname,
             status.ncm_present ? "PRESENT" : "ABSENT",
             status.device_ip);
    snprintf(line3, sizeof(line3), "TCPCTL %s%s%ld",
             status.tcpctl_running ? "RUNNING PID " : "STOPPED",
             status.tcpctl_running ? "" : "",
             status.tcpctl_running ? (long)status.tcpctl_pid : 0L);
    if (!status.tcpctl_running) {
        snprintf(line3, sizeof(line3), "TCPCTL STOPPED");
    }
    snprintf(line4, sizeof(line4), "PORT %s LOG %s", status.tcp_port, status.log_path);

    return draw_screen_info_page("NETWORK STATUS", line1, line2, line3, line4);
}

static long clamp_stress_duration_ms(long duration_ms) {
    if (duration_ms < 1000L) {
        return 1000L;
    }
    if (duration_ms > 120000L) {
        return 120000L;
    }
    return duration_ms;
}

static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms) {
    struct a90_metrics_snapshot snapshot;
    char online[64];
    char present[64];
    char freq0[32];
    char freq1[32];
    char freq2[32];
    char freq3[32];
    char freq4[32];
    char freq5[32];
    char freq6[32];
    char freq7[32];
    char lines[8][160];
    const char *status_word;
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    duration_ms = clamp_stress_duration_ms(duration_ms);

    if (failed) {
        status_word = "FAILED";
    } else if (running) {
        status_word = "RUNNING";
    } else if (done) {
        status_word = "DONE";
    } else {
        status_word = "READY";
    }

    a90_metrics_read_snapshot(&snapshot);
    if (read_trimmed_text_file("/sys/devices/system/cpu/online",
                               online,
                               sizeof(online)) < 0) {
        strcpy(online, "?");
    }
    if (read_trimmed_text_file("/sys/devices/system/cpu/present",
                               present,
                               sizeof(present)) < 0) {
        strcpy(present, "?");
    }
    a90_metrics_read_cpu_freq_label(0, freq0, sizeof(freq0));
    a90_metrics_read_cpu_freq_label(1, freq1, sizeof(freq1));
    a90_metrics_read_cpu_freq_label(2, freq2, sizeof(freq2));
    a90_metrics_read_cpu_freq_label(3, freq3, sizeof(freq3));
    a90_metrics_read_cpu_freq_label(4, freq4, sizeof(freq4));
    a90_metrics_read_cpu_freq_label(5, freq5, sizeof(freq5));
    a90_metrics_read_cpu_freq_label(6, freq6, sizeof(freq6));
    a90_metrics_read_cpu_freq_label(7, freq7, sizeof(freq7));

    snprintf(lines[0], sizeof(lines[0]), "STATE %s  REM %ld.%03ldS",
             status_word,
             remaining_ms / 1000L,
             remaining_ms % 1000L);
    snprintf(lines[1], sizeof(lines[1]), "CPU %s  USE %s  LOAD %s",
             snapshot.cpu_temp,
             snapshot.cpu_usage,
             snapshot.loadavg);
    snprintf(lines[2], sizeof(lines[2]), "CORES ONLINE %.24s  PRESENT %.24s", online, present);
    snprintf(lines[3], sizeof(lines[3]), "FREQ 0:%s 1:%s 2:%s 3:%s",
             freq0, freq1, freq2, freq3);
    snprintf(lines[4], sizeof(lines[4]), "FREQ 4:%s 5:%s 6:%s 7:%s",
             freq4, freq5, freq6, freq7);
    snprintf(lines[5], sizeof(lines[5]), "MEM %s  PWR %s",
             snapshot.memory,
             snapshot.power_now);
    snprintf(lines[6], sizeof(lines[6]), "WORKERS 8  TEST %ldS", duration_ms / 1000L);
    snprintf(lines[7], sizeof(lines[7]), "ANY BUTTON BACK / CANCEL");

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 10;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 11;

    a90_draw_text(a90_kms_framebuffer(), x, y, "TOOLS / CPU STRESS", 0xffcc33,
                  shrink_text_scale("TOOLS / CPU STRESS", title_scale, card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(), x - scale, y - scale, card_w, line_h * 9, 0x202020);
    for (index = 0; index < 8; ++index) {
        uint32_t color = 0xffffff;

        if (index == 0) {
            color = failed ? 0xff6666 : (running ? 0x88ee88 : 0xffcc33);
        } else if (index == 7) {
            color = 0xdddddd;
        }
        a90_draw_text(a90_kms_framebuffer(), x, y + (uint32_t)index * line_h,
                      lines[index],
                      color,
                      shrink_text_scale(lines[index], scale, card_w - scale * 2));
    }

    if (a90_kms_present("cpustress", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void restore_auto_hud_if_needed(bool restore_hud) {
    if (restore_hud) {
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) < 0) {
            a90_logf("screenmenu", "autohud restore failed errno=%d error=%s",
                        errno, strerror(errno));
        }
    }
}

static int cmd_blindmenu(void) {
    static const struct blind_menu_item items[] = {
        { "resume", "return to shell prompt" },
        { "recovery", "reboot to TWRP recovery" },
        { "reboot", "restart device" },
        { "poweroff", "power off device" },
    };
    struct a90_input_context ctx;
    size_t selected = 0;
    size_t count = sizeof(items) / sizeof(items[0]);

    if (a90_input_open(&ctx, "blindmenu") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("blindmenu: VOLUP=prev VOLDOWN=next POWER=select dbl/COMBO=back q/Ctrl-C=cancel\r\n");
    a90_console_printf("blindmenu: start with a safe default, then move as needed\r\n");
    print_blind_menu_selection(items, count, selected);

    while (1) {
        struct a90_input_gesture gesture;
        enum a90_input_menu_action menu_action;

        int wait_rc = a90_input_wait_gesture(&ctx, "blindmenu", &gesture);

        if (wait_rc < 0) {
            a90_input_close(&ctx);
            return wait_rc;
        }

        menu_action = a90_input_menu_action_from_gesture(&gesture);

        if (menu_action == A90_INPUT_MENU_ACTION_PREV ||
            menu_action == A90_INPUT_MENU_ACTION_PAGE_PREV) {
            size_t step = menu_action == A90_INPUT_MENU_ACTION_PAGE_PREV ?
                          A90_INPUT_PAGE_STEP : 1;

            selected = (selected + count - (step % count)) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == A90_INPUT_MENU_ACTION_NEXT ||
            menu_action == A90_INPUT_MENU_ACTION_PAGE_NEXT) {
            size_t step = menu_action == A90_INPUT_MENU_ACTION_PAGE_NEXT ?
                          A90_INPUT_PAGE_STEP : 1;

            selected = (selected + step) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == A90_INPUT_MENU_ACTION_BACK ||
            menu_action == A90_INPUT_MENU_ACTION_HIDE) {
            a90_console_printf("blindmenu: leaving menu\r\n");
            a90_input_close(&ctx);
            return 0;
        }

        if (menu_action == A90_INPUT_MENU_ACTION_RESERVED) {
            a90_console_printf("blindmenu: reserved gesture ignored for safety\r\n");
            continue;
        }

        if (menu_action != A90_INPUT_MENU_ACTION_SELECT) {
            a90_console_printf("blindmenu: ignoring gesture %s\r\n",
                    a90_input_gesture_name(gesture.id));
            continue;
        }

        a90_console_printf("blindmenu: selected %s\r\n", items[selected].name);
        a90_input_close(&ctx);

        if (selected == 0) {
            a90_console_printf("blindmenu: leaving menu\r\n");
            return 0;
        }
        if (selected == 1) {
            return cmd_recovery();
        }
        if (selected == 2) {
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
            return negative_errno_or(EIO);
        }

        sync();
        reboot(RB_POWER_OFF);
        return negative_errno_or(EIO);
    }

    a90_input_close(&ctx);
    return 0;
}

static int cmd_screenmenu(void) {
    int result;

    reap_hud_child();
    if (a90_service_pid(A90_SERVICE_HUD) <= 0) {
        result = start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false);
        if (result < 0) {
            return result;
        }
    }

    a90_controller_request_menu_show();
    a90_controller_set_menu_active(true);
    a90_console_printf("screenmenu: show requested on background HUD\r\n");
    a90_logf("menu", "show requested via screenmenu command");
    return 0;
}

static int cmd_hide_menu(void) {
    a90_controller_request_menu_hide();
    a90_controller_set_menu_active(false);
    a90_console_printf("menu: hide requested\r\n");
    a90_logf("menu", "hide requested via shell command");
    return 0;
}

static int ensure_char_node_exact(const char *path, unsigned int major_num, unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);
    struct stat st;

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            return 0;
        }
        if (unlink(path) < 0) {
            return -1;
        }
    } else if (errno != ENOENT) {
        return -1;
    }

    if (mknod(path, S_IFCHR | 0600, wanted) == 0 || errno == EEXIST) {
        return 0;
    }

    return -1;
}
