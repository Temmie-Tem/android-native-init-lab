/* Included by stage3/linux_init/init_v156.c. Do not compile standalone. */

#define AUTO_MENU_HOLD_REPEAT_START_MS 450L
#define AUTO_MENU_HOLD_REPEAT_INTERVAL_MS 120L

static void kms_draw_menu_section(struct a90_fb *fb,
                                  const struct screen_menu_page *page,
                                  size_t selected);
static int cmd_statushud(void);
static int cmd_recovery(void);
static int draw_screen_input_monitor_app(void);
static int draw_screen_display_test_page(unsigned int page_index);
static uint32_t shrink_text_scale(const char *text, uint32_t scale, uint32_t max_width);
static void restore_auto_hud_if_needed(bool restore_hud);
static void input_monitor_app_reset(void);
static void input_monitor_app_tick(void);
static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index);

static int draw_screen_about_app(enum screen_app_id app_id,
                                 size_t changelog_index,
                                 size_t page_index) {
    return a90_app_about_draw_paged(app_id, changelog_index, page_index);
}

struct auto_hud_state {
    bool menu_active;
    enum screen_app_id active_app;
    struct a90_menu_state menu_state;
    struct a90_app_cpustress_state app_stress;
    unsigned int display_test_page;
    size_t about_changelog_index;
    size_t about_page_index;
    struct a90_app_cutout_calibration cutout_cal;
    unsigned int menu_down_mask;
    bool menu_combo_back_sent;
    unsigned int menu_hold_code;
    long menu_hold_next_ms;
};

static void auto_hud_reset_hold_timer(struct auto_hud_state *state) {
    state->menu_hold_code = 0;
    state->menu_hold_next_ms = 0;
}

static void auto_hud_reset_cutout_state(struct auto_hud_state *state) {
    a90_app_displaytest_cutout_reset(&state->cutout_cal);
}

static void auto_hud_reset_input_state(struct auto_hud_state *state) {
    state->menu_down_mask = 0;
    state->menu_combo_back_sent = false;
    auto_hud_reset_hold_timer(state);
}

static void auto_hud_reset_app_context(struct auto_hud_state *state) {
    state->display_test_page = 0;
    state->about_changelog_index = 0;
    state->about_page_index = 0;
    auto_hud_reset_cutout_state(state);
    auto_hud_reset_input_state(state);
}

static void auto_hud_stop_active_app(struct auto_hud_state *state) {
    if (state->active_app == SCREEN_APP_CPU_STRESS) {
        a90_app_cpustress_stop(&state->app_stress);
    }
}

static void auto_hud_update_controller_state(struct auto_hud_state *state) {
    a90_controller_set_menu_state(state->menu_active ||
                                      state->active_app != SCREEN_APP_NONE,
                                  state->menu_active &&
                                      state->active_app == SCREEN_APP_NONE &&
                                      a90_menu_state_page_id(&state->menu_state) ==
                                          SCREEN_MENU_PAGE_POWER);
}

static void auto_hud_state_init(struct auto_hud_state *state) {
    memset(state, 0, sizeof(*state));
    state->menu_active = true;
    state->active_app = SCREEN_APP_NONE;
    a90_app_cpustress_init(&state->app_stress);
    a90_menu_state_init(&state->menu_state);
    auto_hud_reset_cutout_state(state);
    auto_hud_update_controller_state(state);
}

static void auto_hud_show_menu(struct auto_hud_state *state, bool reset_menu) {
    auto_hud_stop_active_app(state);
    state->active_app = SCREEN_APP_NONE;
    state->menu_active = true;
    if (reset_menu) {
        a90_menu_state_init(&state->menu_state);
        a90_menu_set_changelog_series(0);
    }
    auto_hud_reset_app_context(state);
    auto_hud_update_controller_state(state);
}

static void auto_hud_hide_to_hud(struct auto_hud_state *state, bool reset_menu) {
    auto_hud_stop_active_app(state);
    state->active_app = SCREEN_APP_NONE;
    state->menu_active = false;
    if (reset_menu) {
        a90_menu_state_init(&state->menu_state);
        a90_menu_set_changelog_series(0);
    }
    auto_hud_reset_app_context(state);
    auto_hud_update_controller_state(state);
}

static void auto_hud_enter_app(struct auto_hud_state *state,
                               enum screen_app_id app_id) {
    state->active_app = app_id;
    state->menu_active = false;
    auto_hud_reset_hold_timer(state);
    auto_hud_update_controller_state(state);
}

static void auto_hud_apply_menu_request(struct auto_hud_state *state,
                                        enum a90_controller_menu_request request) {
    if (request == A90_CONTROLLER_MENU_REQUEST_SHOW) {
        auto_hud_show_menu(state, true);
    } else if (request == A90_CONTROLLER_MENU_REQUEST_HIDE) {
        auto_hud_hide_to_hud(state, true);
    }
}

static void auto_hud_back_or_hide(struct auto_hud_state *state) {
    if (state->active_app != SCREEN_APP_NONE) {
        auto_hud_show_menu(state, false);
        return;
    }
    if (!state->menu_active) {
        auto_hud_show_menu(state, true);
        return;
    }
    if (!a90_menu_state_back(&state->menu_state)) {
        auto_hud_hide_to_hud(state, false);
    } else {
        auto_hud_reset_hold_timer(state);
        auto_hud_update_controller_state(state);
    }
}

static bool auto_hud_handle_volume_step(struct auto_hud_state *state,
                                        unsigned int code) {
    int delta;

    if (code == KEY_VOLUMEUP) {
        delta = -1;
    } else if (code == KEY_VOLUMEDOWN) {
        delta = 1;
    } else {
        return false;
    }

    if (state->active_app != SCREEN_APP_NONE) {
        if (a90_menu_app_is_about(state->active_app)) {
            size_t page_count = a90_app_about_page_count(
                state->active_app,
                state->about_changelog_index);

            if (page_count > 1) {
                if (delta < 0) {
                    state->about_page_index =
                        (state->about_page_index + page_count - 1) % page_count;
                } else {
                    state->about_page_index =
                        (state->about_page_index + 1) % page_count;
                }
                return true;
            }
        }
        return false;
    }

    if (!state->menu_active) {
        auto_hud_show_menu(state, true);
    } else {
        a90_menu_state_move(&state->menu_state, delta);
        auto_hud_update_controller_state(state);
    }
    return true;
}

static void auto_hud_arm_hold_timer(struct auto_hud_state *state,
                                    unsigned int code) {
    if (state->menu_hold_code == 0 &&
        (code == KEY_VOLUMEUP || code == KEY_VOLUMEDOWN)) {
        state->menu_hold_code = code;
        state->menu_hold_next_ms = monotonic_millis() +
                                   AUTO_MENU_HOLD_REPEAT_START_MS;
    }
}

static int auto_hud_poll_timeout_ms(const struct auto_hud_state *state,
                                    int default_timeout_ms) {
    int poll_timeout = state->active_app == SCREEN_APP_NONE ?
                       default_timeout_ms : 500;

    if (state->menu_hold_code != 0) {
        long now_ms = monotonic_millis();
        long wait_ms = state->menu_hold_next_ms - now_ms;

        if (wait_ms < 0) {
            wait_ms = 0;
        }
        if (wait_ms < poll_timeout) {
            poll_timeout = (int)wait_ms;
        }
    }
    return poll_timeout;
}

static void auto_hud_handle_poll_timeout(struct auto_hud_state *state) {
    if (state->menu_hold_code != 0) {
        long now_ms = monotonic_millis();

        if (now_ms >= state->menu_hold_next_ms) {
            if (auto_hud_handle_volume_step(state, state->menu_hold_code)) {
                do {
                    state->menu_hold_next_ms +=
                        AUTO_MENU_HOLD_REPEAT_INTERVAL_MS;
                } while (state->menu_hold_next_ms <= now_ms);
            } else {
                auto_hud_reset_hold_timer(state);
            }
        }
    }
}

static void auto_hud_draw_current_screen(struct auto_hud_state *state) {
    if (state->active_app == SCREEN_APP_LOG) {
        a90_app_log_draw_summary();
    } else if (state->active_app == SCREEN_APP_NETWORK) {
        a90_app_network_draw_summary();
    } else if (state->active_app == SCREEN_APP_INPUT_MONITOR) {
        draw_screen_input_monitor_app();
    } else if (state->active_app == SCREEN_APP_DISPLAY_TEST) {
        draw_screen_display_test_page(state->display_test_page);
    } else if (state->active_app == SCREEN_APP_CUTOUT_CAL) {
        a90_app_displaytest_cutout_draw(&state->cutout_cal, true);
    } else if (a90_menu_app_is_about(state->active_app)) {
        draw_screen_about_app(state->active_app,
                              state->about_changelog_index,
                              state->about_page_index);
    } else if (state->active_app == SCREEN_APP_CPU_STRESS) {
        a90_app_cpustress_tick(&state->app_stress);
        a90_app_cpustress_draw(&state->app_stress);
    } else if (a90_kms_begin_frame(0x000000) == 0) {
        const struct screen_menu_page *page =
            a90_menu_state_page(&state->menu_state);
        struct a90_hud_storage_status storage = current_hud_storage_status();

        a90_hud_draw_status_overlay(a90_kms_framebuffer(), &storage, 0, 0);
        if (state->menu_active) {
            kms_draw_menu_section(a90_kms_framebuffer(),
                                  page,
                                  a90_menu_state_selected_index(
                                      &state->menu_state));
        } else {
            a90_hud_draw_hud_log_tail(a90_kms_framebuffer());
        }
        a90_kms_present("autohud", false);
    }
}

static bool auto_hud_handle_combo_state(struct auto_hud_state *state,
                                        const struct input_event *event) {
    unsigned int mask = a90_input_button_mask_from_key(event->code);

    if (mask == 0) {
        return false;
    }
    if (event->value == 1) {
        state->menu_down_mask |= mask;
        if (mask == A90_INPUT_BUTTON_VOLUP ||
            mask == A90_INPUT_BUTTON_VOLDOWN) {
            auto_hud_arm_hold_timer(state, event->code);
        }
    } else if (event->value == 0) {
        state->menu_down_mask &= ~mask;
        if (event->code == state->menu_hold_code) {
            auto_hud_reset_hold_timer(state);
        }
        if ((state->menu_down_mask & (A90_INPUT_BUTTON_VOLUP |
                                      A90_INPUT_BUTTON_VOLDOWN)) !=
            (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) {
            state->menu_combo_back_sent = false;
        }
    }

    if (event->value == 1 &&
        !state->menu_combo_back_sent &&
        (state->menu_down_mask & (A90_INPUT_BUTTON_VOLUP |
                                  A90_INPUT_BUTTON_VOLDOWN)) ==
            (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) {
        state->menu_combo_back_sent = true;
        auto_hud_reset_hold_timer(state);
        auto_hud_back_or_hide(state);
        return true;
    }
    return false;
}

static bool auto_hud_handle_special_app_event(struct auto_hud_state *state,
                                              const struct input_event *event,
                                              int source_index) {
    if (state->active_app == SCREEN_APP_INPUT_MONITOR &&
        event->type == EV_KEY) {
        if (input_monitor_app_feed_event(event, source_index)) {
            auto_hud_show_menu(state, false);
        }
        return true;
    }

    if (state->active_app == SCREEN_APP_CUTOUT_CAL &&
        event->type == EV_KEY) {
        if (a90_app_displaytest_cutout_feed_event(&state->cutout_cal, event)) {
            auto_hud_show_menu(state, false);
            auto_hud_reset_cutout_state(state);
        }
        return true;
    }
    return false;
}

static bool auto_hud_handle_active_app_key(struct auto_hud_state *state,
                                           const struct input_event *event) {
    if (state->active_app == SCREEN_APP_NONE) {
        return false;
    }
    if (auto_hud_handle_volume_step(state, event->code)) {
        return true;
    }
    if (event->value == 2) {
        return true;
    }
    if (state->active_app == SCREEN_APP_DISPLAY_TEST) {
        if (event->code == KEY_VOLUMEUP) {
            state->display_test_page =
                (state->display_test_page + DISPLAY_TEST_PAGE_COUNT - 1) %
                DISPLAY_TEST_PAGE_COUNT;
            return true;
        }
        if (event->code == KEY_VOLUMEDOWN) {
            state->display_test_page =
                (state->display_test_page + 1) % DISPLAY_TEST_PAGE_COUNT;
            return true;
        }
    }
    auto_hud_show_menu(state, false);
    return true;
}

static void auto_hud_start_cpu_stress_app(struct auto_hud_state *state,
                                          long stress_seconds) {
    auto_hud_enter_app(state, SCREEN_APP_CPU_STRESS);
    (void)a90_app_cpustress_start(&state->app_stress,
                                  stress_seconds,
                                  state->app_stress.workers);
}

static bool auto_hud_handle_menu_key(struct auto_hud_state *state,
                                     struct a90_input_context *ctx,
                                     const struct input_event *event) {
    if (event->code == KEY_VOLUMEUP || event->code == KEY_VOLUMEDOWN) {
        auto_hud_handle_volume_step(state, event->code);
        return true;
    }
    if (event->code == KEY_POWER && event->value == 1 && state->menu_active) {
        const struct screen_menu_item *item =
            a90_menu_state_selected(&state->menu_state);

        if (item == NULL) {
            return true;
        }

        if (item->action == SCREEN_MENU_CHANGELOG_SERIES) {
            size_t series_index =
                a90_menu_changelog_series_for_selected_index(
                    a90_menu_state_selected_index(&state->menu_state));

            if (series_index == (size_t)-1) {
                return true;
            }
            a90_menu_set_changelog_series(series_index);
            a90_menu_state_set_page(&state->menu_state, item->target);
            auto_hud_update_controller_state(state);
            return true;
        }

        if (item->action == SCREEN_MENU_CHANGELOG_ENTRY) {
            size_t entry_index =
                a90_menu_changelog_entry_index_for_selected(
                    a90_menu_state_selected_index(&state->menu_state));

            if (entry_index == (size_t)-1) {
                return true;
            }
            state->about_changelog_index = entry_index;
            state->about_page_index = 0;
            auto_hud_enter_app(state, SCREEN_APP_CHANGELOG_DETAIL);
            return true;
        }

        if (a90_menu_action_opens_app(item->action, &state->active_app)) {
            state->about_changelog_index = 0;
            state->about_page_index = 0;
            state->menu_active = false;
            auto_hud_reset_hold_timer(state);
            auto_hud_update_controller_state(state);
            return true;
        }

        switch (item->action) {
        case SCREEN_MENU_RESUME:
            auto_hud_hide_to_hud(state, true);
            break;
        case SCREEN_MENU_SUBMENU:
            a90_menu_state_set_page(&state->menu_state, item->target);
            auto_hud_update_controller_state(state);
            break;
        case SCREEN_MENU_BACK:
            a90_menu_state_back(&state->menu_state);
            auto_hud_update_controller_state(state);
            break;
        case SCREEN_MENU_STATUS:
            cmd_statushud();
            auto_hud_hide_to_hud(state, false);
            break;
        case SCREEN_MENU_LOG:
            auto_hud_enter_app(state, SCREEN_APP_LOG);
            break;
        case SCREEN_MENU_NET_STATUS:
            auto_hud_enter_app(state, SCREEN_APP_NETWORK);
            break;
        case SCREEN_MENU_INPUT_MONITOR:
            input_monitor_app_reset();
            auto_hud_enter_app(state, SCREEN_APP_INPUT_MONITOR);
            break;
        case SCREEN_MENU_DISPLAY_TEST:
            state->display_test_page = 0;
            auto_hud_enter_app(state, SCREEN_APP_DISPLAY_TEST);
            break;
        case SCREEN_MENU_CUTOUT_CAL:
            auto_hud_reset_cutout_state(state);
            auto_hud_enter_app(state, SCREEN_APP_CUTOUT_CAL);
            break;
        case SCREEN_MENU_CPU_STRESS_5:
        case SCREEN_MENU_CPU_STRESS_10:
        case SCREEN_MENU_CPU_STRESS_30:
        case SCREEN_MENU_CPU_STRESS_60:
            auto_hud_start_cpu_stress_app(
                state,
                a90_menu_cpu_stress_seconds(item->action));
            break;
        case SCREEN_MENU_RECOVERY:
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            a90_input_close(ctx);
            cmd_recovery();
            return false;
        case SCREEN_MENU_REBOOT:
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            a90_input_close(ctx);
            sync();
            reboot(RB_AUTOBOOT);
            return false;
        case SCREEN_MENU_POWEROFF:
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            a90_input_close(ctx);
            sync();
            reboot(RB_POWER_OFF);
            return false;
        default:
            break;
        }
    }
    return true;
}

static void auto_hud_loop(unsigned int refresh_sec) {
    struct a90_input_context ctx;
    struct auto_hud_state state;
    bool has_input;
    int timeout_ms;

    signal(SIGTERM, SIG_DFL);
    has_input = (a90_input_open(&ctx, "autohud") == 0);
    timeout_ms = (refresh_sec > 0 && refresh_sec <= 60) ?
                 (int)(refresh_sec * 1000) : 2000;
    auto_hud_state_init(&state);

    while (1) {
        struct pollfd fds[2];
        enum a90_controller_menu_request menu_request;
        int poll_rc;
        int fi;

        menu_request = a90_controller_consume_menu_request();
        if (menu_request != A90_CONTROLLER_MENU_REQUEST_NONE) {
            auto_hud_apply_menu_request(&state, menu_request);
        }
        auto_hud_update_controller_state(&state);
        if (state.active_app == SCREEN_APP_INPUT_MONITOR) {
            input_monitor_app_tick();
        }

        auto_hud_draw_current_screen(&state);

        if (!has_input) {
            sleep(refresh_sec);
            continue;
        }

        fds[0].fd = ctx.fd0; fds[0].events = POLLIN;
        fds[1].fd = ctx.fd3; fds[1].events = POLLIN;
        poll_rc = poll(fds,
                       2,
                       auto_hud_poll_timeout_ms(&state, timeout_ms));
        if (poll_rc == 0) {
            auto_hud_handle_poll_timeout(&state);
            continue;
        }
        if (poll_rc < 0) {
            continue;
        }

        for (fi = 0; fi < 2; fi++) {
            struct input_event ev;

            if (!(fds[fi].revents & POLLIN)) {
                continue;
            }
            while (read(fds[fi].fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (auto_hud_handle_special_app_event(&state, &ev, fi)) {
                    continue;
                }

                if (ev.type == EV_KEY &&
                    ev.value != 2 &&
                    auto_hud_handle_combo_state(&state, &ev)) {
                    continue;
                }

                if (ev.type != EV_KEY || (ev.value != 1 && ev.value != 2)) {
                    continue;
                }

                if (auto_hud_handle_active_app_key(&state, &ev)) {
                    continue;
                }

                if (!auto_hud_handle_menu_key(&state, &ctx, &ev)) {
                    return;
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
            klogf("<6>A90v156: boot splash applied\n");
            if (!boot_splash_recorded) {
                boot_splash_recorded = true;
                a90_logf("boot", "display boot splash applied");
                a90_timeline_record(0, 0, "display-splash", "boot splash applied");
            }
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v156: boot splash skipped (%d)\n", saved_errno);
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

static void input_monitor_cmd_prepare(void *userdata) {
    (void)userdata;
    reap_hud_child();
    stop_auto_hud(false);
}

static void input_monitor_cmd_restore(void *userdata, bool restore_hud) {
    (void)userdata;
    restore_auto_hud_if_needed(restore_hud);
}

static int cmd_inputmonitor(char **argv, int argc) {
    const struct a90_app_inputmon_foreground_hooks hooks = {
        .prepare = input_monitor_cmd_prepare,
        .restore = input_monitor_cmd_restore,
        .userdata = NULL,
    };

    return a90_app_inputmon_run_foreground(argv, argc, &hooks);
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
    uint32_t max_items_h;
    size_t visible_count;
    size_t first_visible = 0;
    size_t last_visible;
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
                  "VOL/HOLD MOVE  PWR SELECT  VOL+DN BACK",
                  0x909090, menu_scale > 1 ? menu_scale - 1 : menu_scale);

    max_items_h = fb->height > menu_y + scale * 70 ? fb->height - menu_y - scale * 70 : item_h;
    visible_count = max_items_h / (item_h + item_gap);
    if (visible_count < 1) {
        visible_count = 1;
    }
    if (visible_count > page->count) {
        visible_count = page->count;
    }
    if (page->count > visible_count) {
        first_visible = selected >= visible_count ? selected - visible_count + 1 : 0;
        if (first_visible + visible_count > page->count) {
            first_visible = page->count - visible_count;
        }
    }
    last_visible = first_visible + visible_count;

    if (page->count > visible_count) {
        char range[48];

        snprintf(range, sizeof(range), "%u-%u/%u",
                 (unsigned int)(first_visible + 1),
                 (unsigned int)last_visible,
                 (unsigned int)page->count);
        a90_draw_text(fb,
                      x + card_w - scale * 30,
                      divider_y + scale * 2,
                      range,
                      0x909090,
                      menu_scale > 2 ? menu_scale - 2 : 1);
    }

    for (i = first_visible; i < last_visible; ++i) {
        uint32_t row = (uint32_t)(i - first_visible);
        uint32_t iy = menu_y + row * (item_h + item_gap);
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
        uint32_t last_y = menu_y + (uint32_t)visible_count * (item_h + item_gap);
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

static uint32_t shrink_text_scale(const char *text,
                                  uint32_t scale,
                                  uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int draw_screen_input_monitor_app(void) {
    return a90_app_inputmon_draw_state(&auto_input_monitor);
}

static int draw_screen_display_test_page(unsigned int page_index) {
    struct a90_hud_storage_status storage = current_hud_storage_status();

    return a90_app_displaytest_draw_page(page_index, &storage);
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
