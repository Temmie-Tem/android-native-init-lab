/* Included by the current native-init translation unit. Do not compile standalone. */

#define AUTO_MENU_HOLD_REPEAT_START_MS 450L
#define AUTO_MENU_HOLD_REPEAT_INTERVAL_MS 120L

static void kms_draw_menu_section(struct a90_fb *fb,
                                  const struct screen_menu_page *page,
                                  size_t selected);
static int cmd_statushud(void);
static int cmd_recovery(void);
int a90_audio_cmd(char **argv, int argc);
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
    a90_app_wifi_reset(app_id);
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
    } else if (state->active_app == SCREEN_APP_WIFI_STATUS) {
        a90_app_wifi_draw_status();
    } else if (state->active_app == SCREEN_APP_WIFI_PROFILES) {
        a90_app_wifi_draw_profiles();
    } else if (state->active_app == SCREEN_APP_WIFI_SCAN) {
        a90_app_wifi_draw_scan();
    } else if (state->active_app == SCREEN_APP_WIFI_PING) {
        a90_app_wifi_draw_ping();
    } else if (state->active_app == SCREEN_APP_AUDIO_STATUS) {
        a90_app_audio_draw_status();
    } else if (state->active_app == SCREEN_APP_AUDIO_PROFILE) {
        a90_app_audio_draw_profile();
    } else if (state->active_app == SCREEN_APP_AUDIO_STAGES) {
        a90_app_audio_draw_stages();
    } else if (state->active_app == SCREEN_APP_AUDIO_MAP) {
        a90_app_audio_draw_map();
    } else if (state->active_app == SCREEN_APP_AUDIO_CHIME) {
        a90_app_audio_draw_chime();
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

        {
            enum screen_app_id opened_app = SCREEN_APP_NONE;

            if (a90_menu_action_opens_app(item->action, &opened_app)) {
                state->about_changelog_index = 0;
                state->about_page_index = 0;
                auto_hud_enter_app(state, opened_app);
                return true;
            }
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
        case SCREEN_MENU_DEMO_BADAPPLE: {
            char *audio_argv[] = {
                "audio", "play", "internal-speaker-safe",
                "--mode", "listen",
                "--amplitude-milli", "150",
                "--duration-ms", "232090",
                "--pcm-gain-milli", "780",
                "--pcm-file", "/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
                "--execute",
            };
            char *demo_argv[] = {
                "video", "demo", "badapple", "play",
                "--trust-cache",
                "--present", "setcrtc",
                "--layout", "player-hud",
                "--sync-audio-status", "/cache/a90-audio-play/status.txt",
                "--sync-wait-ms", "60000",
                "--sync-start-offset-ms", "450",
            };
            int audio_rc;
            int rc;

            a90_console_printf("menu.demo.badapple.action=play-av-fullsong\r\n");
            a90_console_printf("menu.demo.badapple.frames=6962\r\n");
            a90_console_printf("menu.demo.badapple.audio_duration_ms=232090\r\n");
            a90_console_printf("menu.demo.badapple.audio_amplitude_milli=150\r\n");
            a90_console_printf("menu.demo.badapple.audio_pcm_gain_milli=780\r\n");
            a90_console_printf("menu.demo.badapple.audio_pcm=/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le\r\n");
            a90_console_printf("menu.demo.badapple.video_present=setcrtc\r\n");
            a90_console_printf("menu.demo.badapple.audio_sync_status=/cache/a90-audio-play/status.txt\r\n");
            a90_console_printf("menu.demo.badapple.audio_sync_start_offset_ms=450\r\n");
            a90_console_printf("menu.demo.badapple.restore=menu\r\n");
            state->menu_active = false;
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            audio_rc = a90_audio_cmd(audio_argv,
                                     (int)(sizeof(audio_argv) / sizeof(audio_argv[0])));
            a90_console_printf("menu.demo.badapple.audio_rc=%d\r\n", audio_rc);
            if (audio_rc == 0) {
                rc = cmd_video_demo(demo_argv,
                                    (int)(sizeof(demo_argv) / sizeof(demo_argv[0])));
            } else {
                rc = audio_rc;
                a90_console_printf("menu.demo.badapple.video_skipped=audio-start-failed\r\n");
            }
            a90_console_printf("menu.demo.badapple.rc=%d\r\n", rc);
            auto_hud_show_menu(state, false);
            break;
        }
        case SCREEN_MENU_DEMO_NYAN: {
            char *audio_argv[] = {
                "audio", "play", "internal-speaker-safe",
                "--mode", "listen",
                "--amplitude-milli", "150",
                "--duration-ms", "10000",
                "--pcm-gain-milli", "780",
                "--pcm-file", "/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le",
                "--execute",
            };
            char *demo_argv[] = {
                "video", "demo", "nyan", "play",
                "--trust-cache",
                "--frames", "300",
                "--present", "setcrtc",
                "--layout", "player-hud",
                "--sync-audio-status", "/cache/a90-audio-play/status.txt",
                "--sync-wait-ms", "60000",
                "--sync-start-offset-ms", "450",
            };
            int audio_rc;
            int rc;

            a90_console_printf("menu.demo.nyan.action=play-av-preview\r\n");
            a90_console_printf("menu.demo.nyan.frames=300\r\n");
            a90_console_printf("menu.demo.nyan.audio_duration_ms=10000\r\n");
            a90_console_printf("menu.demo.nyan.audio_amplitude_milli=150\r\n");
            a90_console_printf("menu.demo.nyan.audio_pcm_gain_milli=780\r\n");
            a90_console_printf("menu.demo.nyan.audio_pcm=/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le\r\n");
            a90_console_printf("menu.demo.nyan.video_present=setcrtc\r\n");
            a90_console_printf("menu.demo.nyan.audio_sync_status=/cache/a90-audio-play/status.txt\r\n");
            a90_console_printf("menu.demo.nyan.audio_sync_start_offset_ms=450\r\n");
            a90_console_printf("menu.demo.nyan.restore=menu\r\n");
            state->menu_active = false;
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            audio_rc = a90_audio_cmd(audio_argv,
                                     (int)(sizeof(audio_argv) / sizeof(audio_argv[0])));
            a90_console_printf("menu.demo.nyan.audio_rc=%d\r\n", audio_rc);
            if (audio_rc == 0) {
                rc = cmd_video_demo(demo_argv,
                                    (int)(sizeof(demo_argv) / sizeof(demo_argv[0])));
            } else {
                rc = audio_rc;
                a90_console_printf("menu.demo.nyan.video_skipped=audio-start-failed\r\n");
            }
            a90_console_printf("menu.demo.nyan.rc=%d\r\n", rc);
            auto_hud_show_menu(state, false);
            break;
        }
        case SCREEN_MENU_DEMO_DOOM: {
            struct a90_doomgeneric_bridge_status doomgeneric;
            char *demo_argv[9];
            int rc;

            a90_doomgeneric_bridge_get_status(&doomgeneric);
            demo_argv[0] = "video";
            demo_argv[1] = "demo";
            demo_argv[2] = "doom";
            demo_argv[3] = "frame";
            demo_argv[4] = "8";
            demo_argv[5] = "--wad";
            demo_argv[6] = "runtime-private";
            demo_argv[7] = "--sha256";
            demo_argv[8] = (char *)doomgeneric.expected_wad_sha256;
            a90_console_printf("menu.demo.doom.action=visible-frame-preview\r\n");
            a90_console_printf("menu.demo.doom.status=doomgeneric-visible-frame-ready\r\n");
            a90_console_printf("menu.demo.doom.input=serial-doompad-consumed\r\n");
            a90_console_printf("menu.demo.doom.input.live_handoff=v3016-doompad-gameplay-loop\r\n");
            a90_console_printf("menu.demo.doom.input.virtual_controller=doompad-serial-v3014\r\n");
            a90_console_printf("menu.demo.doom.input.consumed=doompad-serial-v3014\r\n");
            a90_console_printf("menu.demo.doom.input.hardware_gate=none-serial-control\r\n");
            a90_console_printf("menu.demo.doom.input.command=doompad key <role> <0|1>\r\n");
            a90_console_printf("menu.demo.doom.play.command=video demo doom play [frames]\r\n");
            a90_console_printf("menu.demo.doom.frame.command=video demo doom frame 8 --wad runtime-private --sha256 %s\r\n",
                               doomgeneric.expected_wad_sha256);
            a90_console_printf("menu.demo.doom.input.keyboard_fallback=usb-keyboard-otg\r\n");
            a90_console_printf("menu.demo.doom.engine.bridge=%s\r\n", doomgeneric.candidate);
            a90_console_printf("menu.demo.doom.engine.active=%s\r\n",
                               doomgeneric.helper_executable ?
                                   doomgeneric.engine :
                                   "doompad-loop-not-doomgeneric");
            a90_console_printf("menu.demo.doom.engine.helper=%s\r\n", doomgeneric.helper_path);
            a90_console_printf("menu.demo.doom.engine.helper.present=%d\r\n",
                               doomgeneric.helper_present ? 1 : 0);
            a90_console_printf("menu.demo.doom.engine.helper.executable=%d\r\n",
                               doomgeneric.helper_executable ? 1 : 0);
            a90_console_printf("menu.demo.doom.asset.wad.active=%s\r\n",
                               doomgeneric.helper_executable ?
                                   "runtime-private-not-bundled" :
                                   "not-bundled");
            a90_console_printf("menu.demo.doom.asset.wad.runtime_path=%s\r\n",
                               doomgeneric.runtime_wad_path);
            a90_console_printf("menu.demo.doom.asset.wad.expected_sha256=%s\r\n",
                               doomgeneric.expected_wad_sha256);
            a90_console_printf("menu.demo.doom.asset.wad.present=%d\r\n",
                               doomgeneric.runtime_wad_present ? 1 : 0);
            a90_console_printf("menu.demo.doom.asset.wad.size_ok=%d\r\n",
                               doomgeneric.runtime_wad_size_ok ? 1 : 0);
            a90_console_printf("menu.demo.doom.input.active=%s\r\n", doomgeneric.input_path);
            a90_console_printf("menu.demo.doom.input.otg_required=0\r\n");
            a90_console_printf("menu.demo.doom.engine.probe.command=video demo doom engine-probe\r\n");
            a90_console_printf("menu.demo.doom.verify.command=video demo doom verify --wad runtime-private --sha256 %s\r\n",
                               doomgeneric.expected_wad_sha256);
            a90_console_printf("menu.demo.doom.sd_wad_play.command=video demo doom play [frames] --wad runtime-private --sha256 %s\r\n",
                               doomgeneric.expected_wad_sha256);
            a90_console_printf("menu.demo.doom.restore=menu\r\n");
            state->menu_active = false;
            a90_controller_set_menu_active(false);
            a90_controller_clear_menu_request();
            rc = cmd_video_demo(demo_argv,
                                (int)(sizeof(demo_argv) / sizeof(demo_argv[0])));
            a90_console_printf("menu.demo.doom.frame_rc=%d\r\n", rc);
            a90_console_printf("menu.demo.doom.rc=%d\r\n", rc);
            auto_hud_show_menu(state, false);
            break;
        }
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
            klogf("<6>A90v319: boot splash applied\n");
            if (!boot_splash_recorded) {
                boot_splash_recorded = true;
                a90_logf("boot", "display boot splash applied");
                a90_timeline_record(0, 0, "display-splash", "boot splash applied");
            }
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v319: boot splash skipped (%d)\n", saved_errno);
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

static bool inputscan_read_capability(const char *event_name,
                                      const char *capability,
                                      char *bitmap,
                                      size_t bitmap_size) {
    char path[PATH_MAX];

    if (snprintf(path, sizeof(path),
                 "/sys/class/input/%s/device/capabilities/%s",
                 event_name,
                 capability) >= (int)sizeof(path)) {
        return false;
    }
    if (read_text_file(path, bitmap, bitmap_size) < 0) {
        return false;
    }
    trim_newline(bitmap);
    return true;
}

static void inputscan_class_text(bool touch_candidate,
                                 bool keyboard_candidate,
                                 bool button_candidate,
                                 char *out,
                                 size_t out_size) {
    size_t used = 0;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (touch_candidate) {
        used += snprintf(out + used, used < out_size ? out_size - used : 0,
                         "%stouch", used > 0 ? "," : "");
    }
    if (keyboard_candidate) {
        used += snprintf(out + used, used < out_size ? out_size - used : 0,
                         "%skeyboard", used > 0 ? "," : "");
    }
    if (button_candidate) {
        used += snprintf(out + used, used < out_size ? out_size - used : 0,
                         "%sbuttons", used > 0 ? "," : "");
    }
    if (used == 0) {
        snprintf(out, out_size, "other");
    }
}

static int inputscan_print_event(const char *event_name,
                                 unsigned int *touch_count,
                                 unsigned int *keyboard_count,
                                 unsigned int *button_count,
                                 unsigned int *node_count) {
    char name_path[PATH_MAX];
    char name_buf[256] = "";
    char dev_info_path[PATH_MAX];
    char dev_info[64] = "";
    char node_path[PATH_MAX];
    char ev_bitmap[256] = "";
    char key_bitmap[1024] = "";
    char abs_bitmap[512] = "";
    char class_text[64];
    bool has_ev_key;
    bool has_ev_abs;
    bool has_key_bitmap;
    bool has_abs_bitmap;
    bool has_btn_touch;
    bool has_abs_xy;
    bool has_mt_xy;
    bool has_power;
    bool has_volup;
    bool has_voldown;
    bool has_wasd;
    bool has_enter_space_esc;
    bool touch_candidate;
    bool keyboard_candidate;
    bool button_candidate;
    bool node_ok;

    if (snprintf(name_path, sizeof(name_path),
                 "/sys/class/input/%s/device/name", event_name) >= (int)sizeof(name_path) ||
        snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        a90_console_printf("inputscan: %s: path too long\r\n", event_name);
        return -ENAMETOOLONG;
    }

    if (read_text_file(name_path, name_buf, sizeof(name_buf)) < 0) {
        snprintf(name_buf, sizeof(name_buf), "<unknown:%s>", strerror(errno));
    } else {
        trim_newline(name_buf);
    }
    if (read_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        snprintf(dev_info, sizeof(dev_info), "<unknown:%s>", strerror(errno));
    } else {
        trim_newline(dev_info);
    }

    node_ok = get_input_event_path(event_name, node_path, sizeof(node_path)) == 0;
    if (node_ok && node_count != NULL) {
        ++*node_count;
    }

    has_ev_key = false;
    has_ev_abs = false;
    if (inputscan_read_capability(event_name, "ev", ev_bitmap, sizeof(ev_bitmap))) {
        has_ev_key = test_key_bit(ev_bitmap, EV_KEY);
        has_ev_abs = test_key_bit(ev_bitmap, EV_ABS);
    }

    has_key_bitmap = inputscan_read_capability(event_name, "key", key_bitmap, sizeof(key_bitmap));
    has_abs_bitmap = inputscan_read_capability(event_name, "abs", abs_bitmap, sizeof(abs_bitmap));

    has_btn_touch = has_key_bitmap && test_key_bit(key_bitmap, BTN_TOUCH);
    has_power = has_key_bitmap && test_key_bit(key_bitmap, KEY_POWER);
    has_volup = has_key_bitmap && test_key_bit(key_bitmap, KEY_VOLUMEUP);
    has_voldown = has_key_bitmap && test_key_bit(key_bitmap, KEY_VOLUMEDOWN);
    has_wasd = has_key_bitmap &&
        test_key_bit(key_bitmap, KEY_W) &&
        test_key_bit(key_bitmap, KEY_A) &&
        test_key_bit(key_bitmap, KEY_S) &&
        test_key_bit(key_bitmap, KEY_D);
    has_enter_space_esc = has_key_bitmap &&
        test_key_bit(key_bitmap, KEY_ENTER) &&
        test_key_bit(key_bitmap, KEY_SPACE) &&
        test_key_bit(key_bitmap, KEY_ESC);
    has_abs_xy = has_abs_bitmap &&
        test_key_bit(abs_bitmap, ABS_X) &&
        test_key_bit(abs_bitmap, ABS_Y);
    has_mt_xy = has_abs_bitmap &&
        test_key_bit(abs_bitmap, ABS_MT_POSITION_X) &&
        test_key_bit(abs_bitmap, ABS_MT_POSITION_Y);

    touch_candidate = has_ev_abs && (has_btn_touch || has_abs_xy || has_mt_xy);
    keyboard_candidate = has_ev_key && has_wasd && has_enter_space_esc;
    button_candidate = has_ev_key && (has_power || has_volup || has_voldown);

    if (touch_candidate && touch_count != NULL) {
        ++*touch_count;
    }
    if (keyboard_candidate && keyboard_count != NULL) {
        ++*keyboard_count;
    }
    if (button_candidate && button_count != NULL) {
        ++*button_count;
    }

    inputscan_class_text(touch_candidate,
                         keyboard_candidate,
                         button_candidate,
                         class_text,
                         sizeof(class_text));
    a90_console_printf("inputscan.event=%s name=%s dev=%s node=%s class=%s\r\n",
            event_name,
            name_buf,
            dev_info,
            node_ok ? node_path : "<missing>",
            class_text);
    a90_console_printf("  ev.key=%d ev.abs=%d btn_touch=%d abs_xy=%d mt_xy=%d key_power=%d key_volup=%d key_voldown=%d key_wasd=%d key_enter_space_esc=%d\r\n",
            has_ev_key ? 1 : 0,
            has_ev_abs ? 1 : 0,
            has_btn_touch ? 1 : 0,
            has_abs_xy ? 1 : 0,
            has_mt_xy ? 1 : 0,
            has_power ? 1 : 0,
            has_volup ? 1 : 0,
            has_voldown ? 1 : 0,
            has_wasd ? 1 : 0,
            has_enter_space_esc ? 1 : 0);
    return 0;
}

static int cmd_inputscan(char **argv, int argc) {
    DIR *dir;
    struct dirent *entry;
    unsigned int event_count = 0;
    unsigned int touch_count = 0;
    unsigned int keyboard_count = 0;
    unsigned int button_count = 0;
    unsigned int node_count = 0;
    int first_error = 0;

    if (argc >= 2) {
        char event_name[32];

        if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
            a90_console_printf("inputscan: invalid event name\r\n");
            return -EINVAL;
        }
        return inputscan_print_event(event_name,
                                     &touch_count,
                                     &keyboard_count,
                                     &button_count,
                                     &node_count);
    }

    dir = opendir("/sys/class/input");
    if (dir == NULL) {
        a90_console_printf("inputscan: %s\r\n", strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        int result;

        if (strncmp(entry->d_name, "event", 5) != 0) {
            continue;
        }
        result = inputscan_print_event(entry->d_name,
                                       &touch_count,
                                       &keyboard_count,
                                       &button_count,
                                       &node_count);
        if (result == 0) {
            ++event_count;
        } else if (first_error == 0) {
            first_error = result;
        }
    }
    closedir(dir);

    a90_console_printf("inputscan.summary events=%u nodes=%u touch_candidates=%u keyboard_candidates=%u button_candidates=%u\r\n",
            event_count,
            node_count,
            touch_count,
            keyboard_count,
            button_count);
    return event_count > 0 ? 0 : first_error;
}

#ifndef ABS_MT_SLOT
#define ABS_MT_SLOT 0x2f
#endif
#ifndef ABS_MT_TOUCH_MAJOR
#define ABS_MT_TOUCH_MAJOR 0x30
#endif
#ifndef ABS_MT_PRESSURE
#define ABS_MT_PRESSURE 0x3a
#endif

static void inputcaps_print_capability(const char *event_name,
                                       const char *capability,
                                       char *bitmap,
                                       size_t bitmap_size) {
    if (inputscan_read_capability(event_name, capability, bitmap, bitmap_size)) {
        a90_console_printf("inputcaps.cap.%s=%s\r\n", capability, bitmap);
    } else {
        bitmap[0] = '\0';
        a90_console_printf("inputcaps.cap.%s=<missing errno=%d>\r\n",
                capability,
                errno);
    }
}

static void inputcaps_print_device_attr(const char *event_name,
                                        const char *label,
                                        const char *relative_path) {
    char path[PATH_MAX];
    char value[256];

    if (snprintf(path, sizeof(path),
                 "/sys/class/input/%s/device/%s",
                 event_name,
                 relative_path) >= (int)sizeof(path)) {
        a90_console_printf("inputcaps.%s=<path-too-long>\r\n", label);
        return;
    }
    if (read_text_file(path, value, sizeof(value)) < 0) {
        a90_console_printf("inputcaps.%s=<missing errno=%d>\r\n", label, errno);
        return;
    }
    trim_newline(value);
    a90_console_printf("inputcaps.%s=%s\r\n", label, value);
}

static int cmd_inputcaps(char **argv, int argc) {
    char event_name[32];
    char name_path[PATH_MAX];
    char dev_info_path[PATH_MAX];
    char node_path[PATH_MAX];
    char name_buf[256] = "";
    char dev_info[64] = "";
    char ev_bitmap[256] = "";
    char key_bitmap[1024] = "";
    char abs_bitmap[512] = "";
    char prop_bitmap[256] = "";
    char sw_bitmap[256] = "";
    bool ev_key;
    bool ev_abs;
    bool ev_syn;
    bool btn_touch;
    bool key_power;
    bool key_volup;
    bool key_voldown;
    bool key_w;
    bool key_a;
    bool key_s;
    bool key_d;
    bool key_up;
    bool key_down;
    bool key_left;
    bool key_right;
    bool key_enter;
    bool key_space;
    bool key_esc;
    bool key_leftctrl;
    bool key_rightctrl;
    bool key_leftshift;
    bool key_rightshift;
    bool abs_x;
    bool abs_y;
    bool abs_pressure;
    bool abs_mt_slot;
    bool abs_mt_touch_major;
    bool abs_mt_position_x;
    bool abs_mt_position_y;
    bool abs_mt_tracking_id;
    bool abs_mt_pressure;
    bool node_ok;

    if (argc < 2) {
        a90_console_printf("usage: inputcaps <eventX>\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("inputcaps: invalid event name\r\n");
        return -EINVAL;
    }

    if (snprintf(name_path, sizeof(name_path),
                 "/sys/class/input/%s/device/name", event_name) >= (int)sizeof(name_path) ||
        snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        a90_console_printf("inputcaps: path too long\r\n");
        return -ENAMETOOLONG;
    }

    if (read_text_file(name_path, name_buf, sizeof(name_buf)) < 0) {
        snprintf(name_buf, sizeof(name_buf), "<unknown:%s>", strerror(errno));
    } else {
        trim_newline(name_buf);
    }
    if (read_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        snprintf(dev_info, sizeof(dev_info), "<unknown:%s>", strerror(errno));
    } else {
        trim_newline(dev_info);
    }
    node_ok = get_input_event_path(event_name, node_path, sizeof(node_path)) == 0;

    a90_console_printf("inputcaps.event=%s name=%s dev=%s node=%s\r\n",
            event_name,
            name_buf,
            dev_info,
            node_ok ? node_path : "<missing>");

    inputcaps_print_capability(event_name, "ev", ev_bitmap, sizeof(ev_bitmap));
    inputcaps_print_capability(event_name, "key", key_bitmap, sizeof(key_bitmap));
    inputcaps_print_capability(event_name, "abs", abs_bitmap, sizeof(abs_bitmap));
    inputcaps_print_capability(event_name, "prop", prop_bitmap, sizeof(prop_bitmap));
    inputcaps_print_capability(event_name, "sw", sw_bitmap, sizeof(sw_bitmap));

    ev_syn = ev_bitmap[0] != '\0' && test_key_bit(ev_bitmap, EV_SYN);
    ev_key = ev_bitmap[0] != '\0' && test_key_bit(ev_bitmap, EV_KEY);
    ev_abs = ev_bitmap[0] != '\0' && test_key_bit(ev_bitmap, EV_ABS);
    btn_touch = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, BTN_TOUCH);
    key_power = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_POWER);
    key_volup = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_VOLUMEUP);
    key_voldown = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_VOLUMEDOWN);
    key_w = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_W);
    key_a = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_A);
    key_s = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_S);
    key_d = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_D);
    key_up = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_UP);
    key_down = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_DOWN);
    key_left = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_LEFT);
    key_right = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_RIGHT);
    key_enter = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_ENTER);
    key_space = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_SPACE);
    key_esc = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_ESC);
    key_leftctrl = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_LEFTCTRL);
    key_rightctrl = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_RIGHTCTRL);
    key_leftshift = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_LEFTSHIFT);
    key_rightshift = key_bitmap[0] != '\0' && test_key_bit(key_bitmap, KEY_RIGHTSHIFT);
    abs_x = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_X);
    abs_y = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_Y);
    abs_pressure = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_PRESSURE);
    abs_mt_slot = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_SLOT);
    abs_mt_touch_major = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_TOUCH_MAJOR);
    abs_mt_position_x = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_POSITION_X);
    abs_mt_position_y = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_POSITION_Y);
    abs_mt_tracking_id = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_TRACKING_ID);
    abs_mt_pressure = abs_bitmap[0] != '\0' && test_key_bit(abs_bitmap, ABS_MT_PRESSURE);

    a90_console_printf("inputcaps.decode ev_syn=%d ev_key=%d ev_abs=%d btn_touch=%d key_power=%d key_volup=%d key_voldown=%d\r\n",
            ev_syn ? 1 : 0,
            ev_key ? 1 : 0,
            ev_abs ? 1 : 0,
            btn_touch ? 1 : 0,
            key_power ? 1 : 0,
            key_volup ? 1 : 0,
            key_voldown ? 1 : 0);
    a90_console_printf("inputcaps.decode key_w=%d key_a=%d key_s=%d key_d=%d key_up=%d key_down=%d key_left=%d key_right=%d key_enter=%d key_space=%d key_esc=%d key_leftctrl=%d key_rightctrl=%d key_leftshift=%d key_rightshift=%d\r\n",
            key_w ? 1 : 0,
            key_a ? 1 : 0,
            key_s ? 1 : 0,
            key_d ? 1 : 0,
            key_up ? 1 : 0,
            key_down ? 1 : 0,
            key_left ? 1 : 0,
            key_right ? 1 : 0,
            key_enter ? 1 : 0,
            key_space ? 1 : 0,
            key_esc ? 1 : 0,
            key_leftctrl ? 1 : 0,
            key_rightctrl ? 1 : 0,
            key_leftshift ? 1 : 0,
            key_rightshift ? 1 : 0);
    a90_console_printf("inputcaps.decode abs_x=%d abs_y=%d abs_pressure=%d mt_slot=%d mt_touch_major=%d mt_x=%d mt_y=%d mt_tracking_id=%d mt_pressure=%d\r\n",
            abs_x ? 1 : 0,
            abs_y ? 1 : 0,
            abs_pressure ? 1 : 0,
            abs_mt_slot ? 1 : 0,
            abs_mt_touch_major ? 1 : 0,
            abs_mt_position_x ? 1 : 0,
            abs_mt_position_y ? 1 : 0,
            abs_mt_tracking_id ? 1 : 0,
            abs_mt_pressure ? 1 : 0);
    inputcaps_print_device_attr(event_name, "phys", "phys");
    inputcaps_print_device_attr(event_name, "uniq", "uniq");
    inputcaps_print_device_attr(event_name, "id.bustype", "id/bustype");
    inputcaps_print_device_attr(event_name, "id.vendor", "id/vendor");
    inputcaps_print_device_attr(event_name, "id.product", "id/product");
    inputcaps_print_device_attr(event_name, "id.version", "id/version");
    inputcaps_print_device_attr(event_name, "power.control", "power/control");
    inputcaps_print_device_attr(event_name, "power.runtime_status", "power/runtime_status");
    inputcaps_print_device_attr(event_name, "power.runtime_active_time", "power/runtime_active_time");
    inputcaps_print_device_attr(event_name, "power.runtime_suspended_time", "power/runtime_suspended_time");
    return 0;
}

static const char *readinput_event_type_name(unsigned int type) {
    switch (type) {
    case EV_SYN:
        return "EV_SYN";
    case EV_KEY:
        return "EV_KEY";
    case EV_ABS:
        return "EV_ABS";
    default:
        return "EV_OTHER";
    }
}

static const char *readinput_event_code_name(unsigned int type, unsigned int code) {
    if (type == EV_SYN) {
        switch (code) {
        case SYN_REPORT:
            return "SYN_REPORT";
        default:
            return "SYN_OTHER";
        }
    }

    if (type == EV_KEY) {
        switch (code) {
        case BTN_TOUCH:
            return "BTN_TOUCH";
        case KEY_W:
            return "KEY_W";
        case KEY_A:
            return "KEY_A";
        case KEY_S:
            return "KEY_S";
        case KEY_D:
            return "KEY_D";
        case KEY_UP:
            return "KEY_UP";
        case KEY_DOWN:
            return "KEY_DOWN";
        case KEY_LEFT:
            return "KEY_LEFT";
        case KEY_RIGHT:
            return "KEY_RIGHT";
        case KEY_ENTER:
            return "KEY_ENTER";
        case KEY_SPACE:
            return "KEY_SPACE";
        case KEY_ESC:
            return "KEY_ESC";
        case KEY_LEFTCTRL:
            return "KEY_LEFTCTRL";
        case KEY_RIGHTCTRL:
            return "KEY_RIGHTCTRL";
        case KEY_LEFTSHIFT:
            return "KEY_LEFTSHIFT";
        case KEY_RIGHTSHIFT:
            return "KEY_RIGHTSHIFT";
        case KEY_POWER:
            return "KEY_POWER";
        case KEY_VOLUMEUP:
            return "KEY_VOLUMEUP";
        case KEY_VOLUMEDOWN:
            return "KEY_VOLUMEDOWN";
        default:
            return "KEY_OTHER";
        }
    }

    if (type == EV_ABS) {
        switch (code) {
        case ABS_X:
            return "ABS_X";
        case ABS_Y:
            return "ABS_Y";
        case ABS_PRESSURE:
            return "ABS_PRESSURE";
        case ABS_MT_SLOT:
            return "ABS_MT_SLOT";
        case ABS_MT_TOUCH_MAJOR:
            return "ABS_MT_TOUCH_MAJOR";
        case ABS_MT_POSITION_X:
            return "ABS_MT_POSITION_X";
        case ABS_MT_POSITION_Y:
            return "ABS_MT_POSITION_Y";
        case ABS_MT_TRACKING_ID:
            return "ABS_MT_TRACKING_ID";
        case ABS_MT_PRESSURE:
            return "ABS_MT_PRESSURE";
        default:
            return "ABS_OTHER";
        }
    }

    return "CODE_OTHER";
}

static const char *readinput_event_role_name(unsigned int type, unsigned int code) {
    if (type == EV_SYN && code == SYN_REPORT) {
        return "frame";
    }
    if (type == EV_KEY) {
        switch (code) {
        case BTN_TOUCH:
            return "touch_contact";
        case KEY_W:
        case KEY_UP:
            return "doom_forward";
        case KEY_S:
        case KEY_DOWN:
            return "doom_back";
        case KEY_A:
        case KEY_LEFT:
            return "doom_left";
        case KEY_D:
        case KEY_RIGHT:
            return "doom_right";
        case KEY_ENTER:
        case KEY_SPACE:
            return "doom_use";
        case KEY_ESC:
            return "doom_menu";
        case KEY_LEFTCTRL:
        case KEY_RIGHTCTRL:
            return "doom_fire";
        case KEY_LEFTSHIFT:
        case KEY_RIGHTSHIFT:
            return "doom_run";
        case KEY_VOLUMEUP:
            return "doom_button_forward";
        case KEY_VOLUMEDOWN:
            return "doom_button_back";
        case KEY_POWER:
            return "doom_button_fire";
        default:
            return "key_other";
        }
    }
    if (type == EV_ABS) {
        switch (code) {
        case ABS_X:
        case ABS_MT_POSITION_X:
            return "touch_x";
        case ABS_Y:
        case ABS_MT_POSITION_Y:
            return "touch_y";
        case ABS_PRESSURE:
        case ABS_MT_PRESSURE:
            return "touch_pressure";
        case ABS_MT_SLOT:
            return "touch_slot";
        case ABS_MT_TOUCH_MAJOR:
            return "touch_major";
        case ABS_MT_TRACKING_ID:
            return "touch_tracking";
        default:
            return "abs_other";
        }
    }
    return "other";
}

static void readinput_print_decoded_event(int index, const struct input_event *event) {
    a90_console_printf("event.decode %d: type=%s code=%s role=%s value=%d\r\n",
            index,
            readinput_event_type_name(event->type),
            readinput_event_code_name(event->type, event->code),
            readinput_event_role_name(event->type, event->code),
            event->value);
}

struct doominput_state {
    bool forward;
    bool back;
    bool left;
    bool right;
    bool fire;
    bool use;
    bool menu;
    bool run;
    bool touch_contact;
    bool has_touch_x;
    bool has_touch_y;
    bool has_touch_pressure;
    int touch_x;
    int touch_y;
    int touch_slot;
    int touch_tracking_id;
    int touch_pressure;
    unsigned int frame;
};

#define DOOMINPUTMUX_MAX_EVENTS 4

struct doominputmux_source {
    char name[32];
    char path[PATH_MAX];
    int fd;
};

static void doominput_reset_state(struct doominput_state *state) {
    memset(state, 0, sizeof(*state));
    state->touch_tracking_id = -1;
}

static void doominput_apply_key(struct doominput_state *state,
                                unsigned int code,
                                int value) {
    bool down = value != 0;

    switch (code) {
    case KEY_W:
    case KEY_UP:
        state->forward = down;
        break;
    case KEY_S:
    case KEY_DOWN:
        state->back = down;
        break;
    case KEY_A:
    case KEY_LEFT:
        state->left = down;
        break;
    case KEY_D:
    case KEY_RIGHT:
        state->right = down;
        break;
    case KEY_ENTER:
    case KEY_SPACE:
        state->use = down;
        break;
    case KEY_ESC:
        state->menu = down;
        break;
    case KEY_LEFTCTRL:
    case KEY_RIGHTCTRL:
        state->fire = down;
        break;
    case KEY_LEFTSHIFT:
    case KEY_RIGHTSHIFT:
        state->run = down;
        break;
    case KEY_VOLUMEUP:
        state->forward = down;
        break;
    case KEY_VOLUMEDOWN:
        state->back = down;
        break;
    case KEY_POWER:
        state->fire = down;
        break;
    case BTN_TOUCH:
        state->touch_contact = down;
        break;
    default:
        break;
    }
}

static void doominput_apply_abs(struct doominput_state *state,
                                unsigned int code,
                                int value) {
    switch (code) {
    case ABS_X:
    case ABS_MT_POSITION_X:
        state->touch_x = value;
        state->has_touch_x = true;
        break;
    case ABS_Y:
    case ABS_MT_POSITION_Y:
        state->touch_y = value;
        state->has_touch_y = true;
        break;
    case ABS_PRESSURE:
    case ABS_MT_PRESSURE:
        state->touch_pressure = value;
        state->has_touch_pressure = true;
        break;
    case ABS_MT_SLOT:
        state->touch_slot = value;
        break;
    case ABS_MT_TRACKING_ID:
        state->touch_tracking_id = value;
        state->touch_contact = value >= 0;
        break;
    default:
        break;
    }
}

static void doominput_apply_event(struct doominput_state *state,
                                  const struct input_event *event) {
    if (event->type == EV_KEY) {
        doominput_apply_key(state, event->code, event->value);
    } else if (event->type == EV_ABS) {
        doominput_apply_abs(state, event->code, event->value);
    } else if (event->type == EV_SYN && event->code == SYN_REPORT) {
        ++state->frame;
    }
}

static bool doominput_state_active(const struct doominput_state *state) {
    return state->forward || state->back || state->left || state->right ||
        state->fire || state->use || state->menu || state->run ||
        state->touch_contact;
}

static struct doominput_state doompad_state;
static bool doompad_state_ready;
static unsigned int doompad_seq;

struct doompad_snapshot {
    bool forward;
    bool back;
    bool left;
    bool right;
    bool fire;
    bool use;
    bool menu;
    bool run;
    bool active;
    unsigned int seq;
};

static void doompad_init_once(void) {
    if (!doompad_state_ready) {
        doominput_reset_state(&doompad_state);
        doompad_state_ready = true;
    }
}

static int doompad_parse_role(const char *role,
                              unsigned int *key_code,
                              const char **canonical) {
    if (role == NULL || role[0] == '\0') {
        return -EINVAL;
    }

    if (strcmp(role, "forward") == 0 ||
        strcmp(role, "fwd") == 0 ||
        strcmp(role, "w") == 0 ||
        strcmp(role, "up") == 0) {
        *key_code = KEY_W;
        *canonical = "forward";
        return 0;
    }
    if (strcmp(role, "back") == 0 ||
        strcmp(role, "backward") == 0 ||
        strcmp(role, "s") == 0 ||
        strcmp(role, "down") == 0) {
        *key_code = KEY_S;
        *canonical = "back";
        return 0;
    }
    if (strcmp(role, "left") == 0 ||
        strcmp(role, "a") == 0) {
        *key_code = KEY_A;
        *canonical = "left";
        return 0;
    }
    if (strcmp(role, "right") == 0 ||
        strcmp(role, "d") == 0) {
        *key_code = KEY_D;
        *canonical = "right";
        return 0;
    }
    if (strcmp(role, "fire") == 0 ||
        strcmp(role, "ctrl") == 0 ||
        strcmp(role, "control") == 0) {
        *key_code = KEY_LEFTCTRL;
        *canonical = "fire";
        return 0;
    }
    if (strcmp(role, "use") == 0 ||
        strcmp(role, "enter") == 0 ||
        strcmp(role, "space") == 0) {
        *key_code = KEY_ENTER;
        *canonical = "use";
        return 0;
    }
    if (strcmp(role, "menu") == 0 ||
        strcmp(role, "esc") == 0 ||
        strcmp(role, "escape") == 0) {
        *key_code = KEY_ESC;
        *canonical = "menu";
        return 0;
    }
    if (strcmp(role, "run") == 0 ||
        strcmp(role, "shift") == 0) {
        *key_code = KEY_LEFTSHIFT;
        *canonical = "run";
        return 0;
    }

    return -EINVAL;
}

static int doompad_parse_value(const char *value, int *down) {
    if (value == NULL) {
        return -EINVAL;
    }

    if (strcmp(value, "1") == 0 ||
        strcmp(value, "down") == 0 ||
        strcmp(value, "press") == 0 ||
        strcmp(value, "on") == 0) {
        *down = 1;
        return 0;
    }
    if (strcmp(value, "0") == 0 ||
        strcmp(value, "up") == 0 ||
        strcmp(value, "release") == 0 ||
        strcmp(value, "off") == 0) {
        *down = 0;
        return 0;
    }

    return -EINVAL;
}

static void doompad_print_state(void) {
    a90_console_printf("doompad.version=1\r\n");
    a90_console_printf("doompad.source=serial-control\r\n");
    a90_console_printf("doompad.seq=%u\r\n", doompad_seq);
    a90_console_printf("doompad.state seq=%u forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d active=%d\r\n",
            doompad_seq,
            doompad_state.forward ? 1 : 0,
            doompad_state.back ? 1 : 0,
            doompad_state.left ? 1 : 0,
            doompad_state.right ? 1 : 0,
            doompad_state.fire ? 1 : 0,
            doompad_state.use ? 1 : 0,
            doompad_state.menu ? 1 : 0,
            doompad_state.run ? 1 : 0,
            doominput_state_active(&doompad_state) ? 1 : 0);
}

static void doompad_get_snapshot(struct doompad_snapshot *snapshot) {
    if (snapshot == NULL) {
        return;
    }
    doompad_init_once();
    snapshot->forward = doompad_state.forward;
    snapshot->back = doompad_state.back;
    snapshot->left = doompad_state.left;
    snapshot->right = doompad_state.right;
    snapshot->fire = doompad_state.fire;
    snapshot->use = doompad_state.use;
    snapshot->menu = doompad_state.menu;
    snapshot->run = doompad_state.run;
    snapshot->active = doominput_state_active(&doompad_state);
    snapshot->seq = doompad_seq;
}

static void doompad_apply_serial_role(unsigned int key_code,
                                      const char *canonical,
                                      int down) {
    doominput_apply_key(&doompad_state, key_code, down);
    ++doompad_state.frame;
    ++doompad_seq;
    a90_console_printf("doompad.event seq=%u role=%s value=%d\r\n",
            doompad_seq,
            canonical,
            down ? 1 : 0);
    doompad_print_state();
}

static int cmd_doompad(char **argv, int argc) {
    unsigned int key_code;
    const char *canonical;
    int down;
    int rc;

    doompad_init_once();

    if (argc < 2 || strcmp(argv[1], "status") == 0) {
        doompad_print_state();
        return 0;
    }

    if (strcmp(argv[1], "reset") == 0) {
        doominput_reset_state(&doompad_state);
        ++doompad_seq;
        a90_console_printf("doompad.reset seq=%u\r\n", doompad_seq);
        doompad_print_state();
        return 0;
    }

    if (strcmp(argv[1], "key") == 0) {
        if (argc < 4) {
            a90_console_printf("usage: doompad key <role> <0|1|down|up>\r\n");
            return -EINVAL;
        }
        rc = doompad_parse_role(argv[2], &key_code, &canonical);
        if (rc < 0) {
            a90_console_printf("doompad: invalid role %s\r\n", argv[2]);
            return rc;
        }
        rc = doompad_parse_value(argv[3], &down);
        if (rc < 0) {
            a90_console_printf("doompad: invalid value %s\r\n", argv[3]);
            return rc;
        }
        doompad_apply_serial_role(key_code, canonical, down);
        return 0;
    }

    if (strcmp(argv[1], "tap") == 0) {
        if (argc < 3) {
            a90_console_printf("usage: doompad tap <role>\r\n");
            return -EINVAL;
        }
        rc = doompad_parse_role(argv[2], &key_code, &canonical);
        if (rc < 0) {
            a90_console_printf("doompad: invalid role %s\r\n", argv[2]);
            return rc;
        }
        doompad_apply_serial_role(key_code, canonical, 1);
        doompad_apply_serial_role(key_code, canonical, 0);
        return 0;
    }

    a90_console_printf("usage: doompad [status|reset|key <role> <0|1>|tap <role>]\r\n");
    return -EINVAL;
}

#define DOOMPLAY_DEFAULT_FRAMES 90
#define DOOMPLAY_VERIFY_FRAMES 1
#define DOOMPLAY_MAX_FRAMES 300

static int doomplay_parse_frames(const char *text, int default_frames, int *frames_out) {
    int frames;
    char tail;

    if (frames_out == NULL) {
        return -EINVAL;
    }
    if (text == NULL) {
        *frames_out = default_frames;
        return 0;
    }
    if (sscanf(text, "%d%c", &frames, &tail) != 1 ||
        frames <= 0 ||
        frames > DOOMPLAY_MAX_FRAMES) {
        return -EINVAL;
    }
    *frames_out = frames;
    return 0;
}

static void doomplay_draw_state(struct a90_fb *fb,
                                const struct doompad_snapshot *input,
                                int player_x,
                                int player_y,
                                int frame_index,
                                int total_frames) {
    uint32_t scale;
    uint32_t arena_x;
    uint32_t arena_y;
    uint32_t arena_w;
    uint32_t arena_h;
    uint32_t player_size;
    uint32_t px;
    uint32_t py;
    uint32_t muzzle_w;
    uint32_t muzzle_h;
    char line[128];

    if (fb == NULL || input == NULL) {
        return;
    }
    scale = fb->width >= 1000 ? 3U : 2U;
    arena_x = fb->width / 12U;
    arena_y = fb->height / 10U;
    arena_w = fb->width - arena_x * 2U;
    arena_h = fb->height - arena_y * 2U - 96U;
    player_size = scale * 12U;
    px = player_x > 0 ? (uint32_t)player_x : 0U;
    py = player_y > 0 ? (uint32_t)player_y : 0U;
    muzzle_w = scale * 5U;
    muzzle_h = scale * 18U;

    a90_draw_rect(fb, arena_x, arena_y, arena_w, arena_h, 0x16120c);
    a90_draw_rect_outline(fb, arena_x, arena_y, arena_w, arena_h, scale, 0x67513a);
    a90_draw_rect(fb, arena_x + arena_w / 4U, arena_y + arena_h / 3U,
                  arena_w / 2U, scale * 5U, 0x4a3a2a);
    a90_draw_rect(fb, arena_x + arena_w / 2U, arena_y + arena_h / 2U,
                  scale * 5U, arena_h / 3U, 0x4a3a2a);
    if (input->use) {
        a90_draw_rect(fb, arena_x + arena_w - scale * 26U,
                      arena_y + arena_h / 2U - scale * 16U,
                      scale * 16U, scale * 32U, 0x66ddff);
    } else {
        a90_draw_rect(fb, arena_x + arena_w - scale * 26U,
                      arena_y + arena_h / 2U - scale * 16U,
                      scale * 16U, scale * 32U, 0x806030);
    }
    a90_draw_rect(fb, px, py, player_size, player_size,
                  input->run ? 0xffcc33 : 0x66ddff);
    a90_draw_rect_outline(fb, px, py, player_size, player_size, scale, 0xffffff);
    if (input->fire) {
        a90_draw_rect(fb, px + player_size / 2U - muzzle_w / 2U,
                      py > muzzle_h ? py - muzzle_h : 0U,
                      muzzle_w, muzzle_h, 0xff5533);
    }
    if (input->menu) {
        a90_draw_rect(fb, arena_x + scale * 8U, arena_y + scale * 8U,
                      arena_w / 2U, scale * 24U, 0x202020);
        a90_draw_text_fit(fb, arena_x + scale * 12U, arena_y + scale * 14U,
                          "MENU HELD", 0xffcc33, scale, arena_w / 2U - scale * 8U);
    }

    a90_draw_text(fb, arena_x, scale * 8U, "DEMO / DOOMPAD LOOP", 0x66ddff, scale);
    snprintf(line, sizeof(line), "FRAME %d/%d  SEQ %u",
             frame_index + 1,
             total_frames,
             input->seq);
    a90_draw_text_fit(fb, arena_x, arena_y + arena_h + scale * 10U,
                      line, 0xffffff, scale, arena_w);
    snprintf(line, sizeof(line),
             "F%d B%d L%d R%d FIRE%d USE%d RUN%d ACTIVE%d",
             input->forward ? 1 : 0,
             input->back ? 1 : 0,
             input->left ? 1 : 0,
             input->right ? 1 : 0,
             input->fire ? 1 : 0,
             input->use ? 1 : 0,
             input->run ? 1 : 0,
             input->active ? 1 : 0);
    a90_draw_text_fit(fb, arena_x, arena_y + arena_h + scale * 22U,
                      line, 0xbbbbbb, scale, arena_w);
}

static int doomplay_run_frames(int frames, bool render_frames) {
    struct doompad_snapshot input;
    int player_x = 0;
    int player_y = 0;
    int initial_x = 0;
    int initial_y = 0;
    int frame;
    int presented = 0;
    int last_rc = 0;

    doompad_get_snapshot(&input);
    a90_console_printf("doomplay.version=1\r\n");
    a90_console_printf("doomplay.source=doompad-state\r\n");
    a90_console_printf("doomplay.frames_requested=%d\r\n", frames);
    a90_console_printf("doomplay.consumed_doompad_seq=%u\r\n", input.seq);
    a90_console_printf("doomplay.input.forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d active=%d\r\n",
            input.forward ? 1 : 0,
            input.back ? 1 : 0,
            input.left ? 1 : 0,
            input.right ? 1 : 0,
            input.fire ? 1 : 0,
            input.use ? 1 : 0,
            input.menu ? 1 : 0,
            input.run ? 1 : 0,
            input.active ? 1 : 0);

    for (frame = 0; frame < frames; ++frame) {
        struct a90_fb *fb;
        int speed = input.run ? 18 : 9;
        enum a90_cancel_kind cancel;

        if (render_frames) {
            if (a90_kms_begin_frame(0x050505) < 0) {
                return negative_errno_or(ENODEV);
            }
            fb = a90_kms_framebuffer();
            if (frame == 0) {
                player_x = (int)(fb->width / 2U);
                player_y = (int)(fb->height / 2U);
            }
        } else {
            fb = NULL;
            if (frame == 0) {
                player_x = 540;
                player_y = 1200;
            }
        }
        if (frame == 0) {
            initial_x = player_x;
            initial_y = player_y;
        }
        if (input.forward) {
            player_y -= speed;
        }
        if (input.back) {
            player_y += speed;
        }
        if (input.left) {
            player_x -= speed;
        }
        if (input.right) {
            player_x += speed;
        }
        if (fb != NULL) {
            int min_x = (int)(fb->width / 12U) + (int)(fb->width >= 1000 ? 12 : 8);
            int min_y = (int)(fb->height / 10U) + (int)(fb->width >= 1000 ? 12 : 8);
            int max_x = (int)(fb->width - fb->width / 12U) - (int)(fb->width >= 1000 ? 56 : 40);
            int max_y = (int)(fb->height - fb->height / 10U - 96U) - (int)(fb->width >= 1000 ? 56 : 40);

            if (player_x < min_x) {
                player_x = min_x;
            }
            if (player_y < min_y) {
                player_y = min_y;
            }
            if (player_x > max_x) {
                player_x = max_x;
            }
            if (player_y > max_y) {
                player_y = max_y;
            }
            doomplay_draw_state(fb, &input, player_x, player_y, frame, frames);
            if (a90_kms_present("doomplay", false) < 0) {
                last_rc = negative_errno_or(EIO);
                break;
            }
            ++presented;
            usleep(33000);
        }
        cancel = a90_console_poll_cancel(1);
        if (cancel != CANCEL_NONE) {
            return a90_console_cancelled("doomplay", cancel);
        }
    }

    a90_console_printf("doomplay.initial.x=%d y=%d\r\n", initial_x, initial_y);
    a90_console_printf("doomplay.player.x=%d y=%d\r\n", player_x, player_y);
    a90_console_printf("doomplay.frames_presented=%d\r\n", render_frames ? presented : 0);
    a90_console_printf("doomplay.rendered=%d\r\n", render_frames ? 1 : 0);
    if (last_rc < 0) {
        a90_console_printf("doomplay.error=present-failed\r\n");
        return last_rc;
    }
    a90_console_printf("doomplay.rc=0\r\n");
    return 0;
}

static int cmd_doomplay(char **argv, int argc) {
    const char *action = argc >= 2 ? argv[1] : "status";
    int frames;

    if (strcmp(action, "status") == 0) {
        struct doompad_snapshot input;

        doompad_get_snapshot(&input);
        a90_console_printf("doomplay.version=1\r\n");
        a90_console_printf("doomplay.status=ready\r\n");
        a90_console_printf("doomplay.source=doompad-state\r\n");
        a90_console_printf("doomplay.consumed_doompad_seq=%u\r\n", input.seq);
        a90_console_printf("doomplay.input.active=%d\r\n", input.active ? 1 : 0);
        return 0;
    }
    if (strcmp(action, "verify") == 0) {
        if (argc > 2) {
            a90_console_printf("usage: doomplay [status|verify|play [frames]]\r\n");
            return -EINVAL;
        }
        a90_console_printf("video.demo.doom.verify=doompad-frame-loop\r\n");
        return doomplay_run_frames(DOOMPLAY_VERIFY_FRAMES, true);
    }
    if (strcmp(action, "play") == 0) {
        if (argc > 3 ||
            doomplay_parse_frames(argc >= 3 ? argv[2] : NULL,
                                  DOOMPLAY_DEFAULT_FRAMES,
                                  &frames) < 0) {
            a90_console_printf("usage: doomplay [status|verify|play [frames]]\r\n");
            return -EINVAL;
        }
        a90_console_printf("video.demo.doom.play=doompad-frame-loop\r\n");
        return doomplay_run_frames(frames, true);
    }
    a90_console_printf("usage: doomplay [status|verify|play [frames]]\r\n");
    return -EINVAL;
}

static void doominput_print_event(int index, const struct input_event *event) {
    a90_console_printf("doominput.event %d: type=%s code=%s role=%s value=%d\r\n",
            index,
            readinput_event_type_name(event->type),
            readinput_event_code_name(event->type, event->code),
            readinput_event_role_name(event->type, event->code),
            event->value);
}

static void doominput_print_state(int index, const struct doominput_state *state) {
    a90_console_printf("doominput.state %d: forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d touch=%d x=%d y=%d has_x=%d has_y=%d tracking=%d slot=%d pressure=%d has_pressure=%d active=%d frame=%u\r\n",
            index,
            state->forward ? 1 : 0,
            state->back ? 1 : 0,
            state->left ? 1 : 0,
            state->right ? 1 : 0,
            state->fire ? 1 : 0,
            state->use ? 1 : 0,
            state->menu ? 1 : 0,
            state->run ? 1 : 0,
            state->touch_contact ? 1 : 0,
            state->touch_x,
            state->touch_y,
            state->has_touch_x ? 1 : 0,
            state->has_touch_y ? 1 : 0,
            state->touch_tracking_id,
            state->touch_slot,
            state->touch_pressure,
            state->has_touch_pressure ? 1 : 0,
            doominput_state_active(state) ? 1 : 0,
            state->frame);
}

static void doominputmux_print_event(int index,
                                     const char *source,
                                     const struct input_event *event) {
    a90_console_printf("doominputmux.event %d: source=%s type=%s code=%s role=%s value=%d\r\n",
            index,
            source,
            readinput_event_type_name(event->type),
            readinput_event_code_name(event->type, event->code),
            readinput_event_role_name(event->type, event->code),
            event->value);
}

static void doominputmux_print_state(int index,
                                     const char *source,
                                     const struct doominput_state *state) {
    a90_console_printf("doominputmux.state %d: source=%s forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d touch=%d x=%d y=%d has_x=%d has_y=%d tracking=%d slot=%d pressure=%d has_pressure=%d active=%d frame=%u\r\n",
            index,
            source,
            state->forward ? 1 : 0,
            state->back ? 1 : 0,
            state->left ? 1 : 0,
            state->right ? 1 : 0,
            state->fire ? 1 : 0,
            state->use ? 1 : 0,
            state->menu ? 1 : 0,
            state->run ? 1 : 0,
            state->touch_contact ? 1 : 0,
            state->touch_x,
            state->touch_y,
            state->has_touch_x ? 1 : 0,
            state->has_touch_y ? 1 : 0,
            state->touch_tracking_id,
            state->touch_slot,
            state->touch_pressure,
            state->has_touch_pressure ? 1 : 0,
            doominput_state_active(state) ? 1 : 0,
            state->frame);
}

static void doominputmux_close_sources(struct doominputmux_source *sources,
                                       int source_count) {
    int index;

    for (index = 0; index < source_count; ++index) {
        if (sources[index].fd >= 0) {
            close(sources[index].fd);
            sources[index].fd = -1;
        }
    }
}

static int doominputmux_parse_sources(const char *arg,
                                      struct doominputmux_source *sources,
                                      int *source_count) {
    char spec[160];
    char *cursor;
    int copied;
    int count = 0;

    if (arg == NULL || arg[0] == '\0') {
        return -EINVAL;
    }
    copied = snprintf(spec, sizeof(spec), "%s", arg);
    if (copied < 0 || (size_t)copied >= sizeof(spec)) {
        return -EINVAL;
    }

    cursor = spec;
    while (cursor != NULL && *cursor != '\0') {
        char *comma = strchr(cursor, ',');

        if (comma != NULL) {
            *comma = '\0';
        }
        if (*cursor == '\0') {
            return -EINVAL;
        }
        if (count >= DOOMINPUTMUX_MAX_EVENTS) {
            return -E2BIG;
        }
        if (normalize_event_name(cursor, sources[count].name,
                                 sizeof(sources[count].name)) < 0) {
            return -EINVAL;
        }
        if (get_input_event_path(sources[count].name,
                                 sources[count].path,
                                 sizeof(sources[count].path)) < 0) {
            return negative_errno_or(ENOENT);
        }
        sources[count].fd = -1;
        ++count;
        cursor = comma != NULL ? comma + 1 : NULL;
    }
    if (count == 0) {
        return -EINVAL;
    }
    *source_count = count;
    return 0;
}

static int cmd_readinput(char **argv, int argc) {
    char event_name[32];
    char dev_path[PATH_MAX];
    int count = 16;
    int timeout_ms = -1;
    int fd;
    int index;
    long deadline_ms = 0;

    if (argc < 2) {
        a90_console_printf("usage: readinput <eventX> [count] [timeout_ms]\r\n");
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
    if (argc >= 4 && sscanf(argv[3], "%d", &timeout_ms) != 1) {
        a90_console_printf("readinput: invalid timeout_ms\r\n");
        return -EINVAL;
    }
    if (timeout_ms < 0) {
        timeout_ms = -1;
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
    if (timeout_ms >= 0) {
        deadline_ms = monotonic_millis() + timeout_ms;
        a90_console_printf("readinput: timeout_ms=%d\r\n", timeout_ms);
    }

    index = 0;
    while (index < count) {
        struct pollfd fds[2];
        int poll_rc;
        int poll_timeout = -1;

        fds[0].fd = fd;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = STDIN_FILENO;
        fds[1].events = POLLIN;
        fds[1].revents = 0;

        if (timeout_ms >= 0) {
            long remaining_ms = deadline_ms - monotonic_millis();
            if (remaining_ms <= 0) {
                a90_console_printf("readinput: timeout after %dms captured=%d/%d\r\n",
                        timeout_ms,
                        index,
                        count);
                close(fd);
                return -ETIMEDOUT;
            }
            poll_timeout = remaining_ms > 2147483647L ? 2147483647 : (int)remaining_ms;
        }

        poll_rc = poll(fds, 2, poll_timeout);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("readinput: poll: %s\r\n", strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
        if (poll_rc == 0) {
            a90_console_printf("readinput: timeout after %dms captured=%d/%d\r\n",
                    timeout_ms,
                    index,
                    count);
            close(fd);
            return -ETIMEDOUT;
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
            readinput_print_decoded_event(index, &event);
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

static int cmd_doominputmux(char **argv, int argc) {
    struct doominputmux_source sources[DOOMINPUTMUX_MAX_EVENTS];
    int source_count = 0;
    int count = 32;
    int timeout_ms = -1;
    int index;
    int rc;
    long deadline_ms = 0;
    struct doominput_state state;
    char source_list[160];

    memset(sources, 0, sizeof(sources));
    for (index = 0; index < DOOMINPUTMUX_MAX_EVENTS; ++index) {
        sources[index].fd = -1;
    }

    if (argc < 2) {
        a90_console_printf("usage: doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]\r\n");
        return -EINVAL;
    }

    rc = doominputmux_parse_sources(argv[1], sources, &source_count);
    if (rc < 0) {
        a90_console_printf("doominputmux: invalid event list\r\n");
        return rc;
    }

    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("doominputmux: invalid count\r\n");
        return -EINVAL;
    }
    if (count <= 0) {
        count = 1;
    }
    if (argc >= 4 && sscanf(argv[3], "%d", &timeout_ms) != 1) {
        a90_console_printf("doominputmux: invalid timeout_ms\r\n");
        return -EINVAL;
    }
    if (timeout_ms < 0) {
        timeout_ms = -1;
    }

    source_list[0] = '\0';
    for (index = 0; index < source_count; ++index) {
        int written;
        size_t used = strlen(source_list);

        written = snprintf(source_list + used,
                           sizeof(source_list) - used,
                           "%s%s",
                           used == 0 ? "" : ",",
                           sources[index].name);
        if (written < 0 || (size_t)written >= sizeof(source_list) - used) {
            a90_console_printf("doominputmux: source list too long\r\n");
            return -EINVAL;
        }
    }

    for (index = 0; index < source_count; ++index) {
        sources[index].fd = open(sources[index].path, O_RDONLY | O_NONBLOCK);
        if (sources[index].fd < 0) {
            int saved_errno = errno;

            a90_console_printf("doominputmux: open %s: %s\r\n",
                    sources[index].path,
                    strerror(saved_errno));
            doominputmux_close_sources(sources, source_count);
            errno = saved_errno;
            return negative_errno_or(ENOENT);
        }
    }

    doominput_reset_state(&state);
    a90_console_printf("doominputmux: waiting on %s (%d events across %d fds), q/Ctrl-C cancels\r\n",
            source_list,
            count,
            source_count);
    if (timeout_ms >= 0) {
        deadline_ms = monotonic_millis() + timeout_ms;
        a90_console_printf("doominputmux: timeout_ms=%d\r\n", timeout_ms);
    }

    index = 0;
    while (index < count) {
        struct pollfd fds[DOOMINPUTMUX_MAX_EVENTS + 1];
        int poll_rc;
        int poll_timeout = -1;
        int fi;

        for (fi = 0; fi < source_count; ++fi) {
            fds[fi].fd = sources[fi].fd;
            fds[fi].events = POLLIN;
            fds[fi].revents = 0;
        }
        fds[source_count].fd = STDIN_FILENO;
        fds[source_count].events = POLLIN;
        fds[source_count].revents = 0;

        if (timeout_ms >= 0) {
            long remaining_ms = deadline_ms - monotonic_millis();
            if (remaining_ms <= 0) {
                a90_console_printf("doominputmux: timeout after %dms captured=%d/%d\r\n",
                        timeout_ms,
                        index,
                        count);
                doominputmux_close_sources(sources, source_count);
                return -ETIMEDOUT;
            }
            poll_timeout = remaining_ms > 2147483647L ? 2147483647 : (int)remaining_ms;
        }

        poll_rc = poll(fds, (nfds_t)(source_count + 1), poll_timeout);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("doominputmux: poll: %s\r\n", strerror(errno));
            doominputmux_close_sources(sources, source_count);
            return negative_errno_or(EIO);
        }
        if (poll_rc == 0) {
            a90_console_printf("doominputmux: timeout after %dms captured=%d/%d\r\n",
                    timeout_ms,
                    index,
                    count);
            doominputmux_close_sources(sources, source_count);
            return -ETIMEDOUT;
        }

        if ((fds[source_count].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                doominputmux_close_sources(sources, source_count);
                return a90_console_cancelled("doominputmux", cancel);
            }
        }

        for (fi = 0; fi < source_count && index < count; ++fi) {
            if ((fds[fi].revents & POLLIN) == 0) {
                continue;
            }

            while (index < count) {
                struct input_event event;
                ssize_t rd = read(sources[fi].fd, &event, sizeof(event));

                if (rd < 0) {
                    if (errno == EAGAIN || errno == EWOULDBLOCK) {
                        break;
                    }
                    a90_console_printf("doominputmux: read %s: %s\r\n",
                            sources[fi].name,
                            strerror(errno));
                    doominputmux_close_sources(sources, source_count);
                    return negative_errno_or(EIO);
                }
                if (rd != (ssize_t)sizeof(event)) {
                    a90_console_printf("doominputmux: short read %s %ld\r\n",
                            sources[fi].name,
                            (long)rd);
                    doominputmux_close_sources(sources, source_count);
                    return -EIO;
                }

                doominputmux_print_event(index, sources[fi].name, &event);
                doominput_apply_event(&state, &event);
                doominputmux_print_state(index, sources[fi].name, &state);
                ++index;
            }
        }

        for (fi = 0; fi < source_count; ++fi) {
            if ((fds[fi].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("doominputmux: poll error %s revents=0x%x\r\n",
                        sources[fi].name,
                        fds[fi].revents);
                doominputmux_close_sources(sources, source_count);
                return -EIO;
            }
        }
    }

    doominputmux_close_sources(sources, source_count);
    return 0;
}

static int cmd_doominput(char **argv, int argc) {
    char event_name[32];
    char dev_path[PATH_MAX];
    int count = 32;
    int timeout_ms = -1;
    int fd;
    int index;
    long deadline_ms = 0;
    struct doominput_state state;

    if (argc < 2) {
        a90_console_printf("usage: doominput <eventX> [count] [timeout_ms]\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("doominput: invalid event name\r\n");
        return -EINVAL;
    }

    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("doominput: invalid count\r\n");
        return -EINVAL;
    }
    if (count <= 0) {
        count = 1;
    }
    if (argc >= 4 && sscanf(argv[3], "%d", &timeout_ms) != 1) {
        a90_console_printf("doominput: invalid timeout_ms\r\n");
        return -EINVAL;
    }
    if (timeout_ms < 0) {
        timeout_ms = -1;
    }

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        a90_console_printf("doominput: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    fd = open(dev_path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        a90_console_printf("doominput: open %s: %s\r\n", dev_path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    doominput_reset_state(&state);
    a90_console_printf("doominput: waiting on %s (%d events), q/Ctrl-C cancels\r\n",
            dev_path, count);
    if (timeout_ms >= 0) {
        deadline_ms = monotonic_millis() + timeout_ms;
        a90_console_printf("doominput: timeout_ms=%d\r\n", timeout_ms);
    }

    index = 0;
    while (index < count) {
        struct pollfd fds[2];
        int poll_rc;
        int poll_timeout = -1;

        fds[0].fd = fd;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = STDIN_FILENO;
        fds[1].events = POLLIN;
        fds[1].revents = 0;

        if (timeout_ms >= 0) {
            long remaining_ms = deadline_ms - monotonic_millis();
            if (remaining_ms <= 0) {
                a90_console_printf("doominput: timeout after %dms captured=%d/%d\r\n",
                        timeout_ms,
                        index,
                        count);
                close(fd);
                return -ETIMEDOUT;
            }
            poll_timeout = remaining_ms > 2147483647L ? 2147483647 : (int)remaining_ms;
        }

        poll_rc = poll(fds, 2, poll_timeout);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("doominput: poll: %s\r\n", strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
        if (poll_rc == 0) {
            a90_console_printf("doominput: timeout after %dms captured=%d/%d\r\n",
                    timeout_ms,
                    index,
                    count);
            close(fd);
            return -ETIMEDOUT;
        }

        if ((fds[1].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                close(fd);
                return a90_console_cancelled("doominput", cancel);
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
                a90_console_printf("doominput: read: %s\r\n", strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
            if (rd != (ssize_t)sizeof(event)) {
                a90_console_printf("doominput: short read %ld\r\n", (long)rd);
                close(fd);
                return -EIO;
            }

            doominput_print_event(index, &event);
            doominput_apply_event(&state, &event);
            doominput_print_state(index, &state);
            ++index;
        }
        if ((fds[0].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
            a90_console_printf("doominput: poll error revents=0x%x\r\n", fds[0].revents);
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
    uint32_t glyph_h = scale * 7;
    uint32_t card_w = fb->width - x * 2;
    uint32_t menu_scale = scale;
    uint32_t y = a90_hud_status_origin_y(fb->height);
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

    status_bottom = y + a90_hud_status_overlay_height();
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

static int ensure_char_node_exact_mode(const char *path,
                                       unsigned int major_num,
                                       unsigned int minor_num,
                                       mode_t mode) {
    dev_t wanted = makedev(major_num, minor_num);
    struct stat st;

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            (void)chmod(path, mode);
            return 0;
        }
        if (unlink(path) < 0) {
            return -1;
        }
    } else if (errno != ENOENT) {
        return -1;
    }

    if (mknod(path, S_IFCHR | mode, wanted) == 0 || errno == EEXIST) {
        (void)chmod(path, mode);
        return 0;
    }

    return -1;
}

static int ensure_char_node_exact(const char *path, unsigned int major_num, unsigned int minor_num) {
    return ensure_char_node_exact_mode(path, major_num, minor_num, 0600);
}
