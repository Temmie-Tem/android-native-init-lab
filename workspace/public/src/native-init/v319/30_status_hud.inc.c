/* Included by the current native-init translation unit. Do not compile standalone. */

static struct a90_hud_storage_status current_hud_storage_status(void) {
    static struct a90_storage_status snapshot;
    static struct a90_runtime_status runtime;
    struct a90_hud_storage_status storage = {
        .backend = "unknown",
        .root = "",
        .warning = "",
    };

    if (a90_runtime_get_status(&runtime) == 0 && runtime.initialized) {
        storage.backend = runtime.backend;
        storage.root = runtime.root;
        storage.warning = runtime.warning;
    } else if (a90_storage_get_status(&snapshot) == 0) {
        storage.backend = snapshot.backend;
        storage.root = snapshot.root;
        storage.warning = snapshot.warning;
    }
    return storage;
}

static bool parse_color_arg(const char *arg, uint32_t *color_out) {
    unsigned int value;

    if (strcmp(arg, "black") == 0) {
        *color_out = 0x000000;
        return true;
    }
    if (strcmp(arg, "white") == 0) {
        *color_out = 0xffffff;
        return true;
    }
    if (strcmp(arg, "red") == 0) {
        *color_out = 0xff0000;
        return true;
    }
    if (strcmp(arg, "green") == 0) {
        *color_out = 0x00ff00;
        return true;
    }
    if (strcmp(arg, "blue") == 0) {
        *color_out = 0x0000ff;
        return true;
    }
    if (strcmp(arg, "gray") == 0 || strcmp(arg, "grey") == 0) {
        *color_out = 0x808080;
        return true;
    }
    if (sscanf(arg, "%x", &value) == 1) {
        *color_out = value & 0xffffffU;
        return true;
    }
    return false;
}

static bool parse_u32_arg(const char *arg, uint32_t min_value, uint32_t max_value,
                          uint32_t *value_out) {
    char *end = NULL;
    unsigned long value;

    if (arg == NULL || value_out == NULL || arg[0] == '\0') {
        return false;
    }
    errno = 0;
    value = strtoul(arg, &end, 10);
    if (errno != 0 || end == NULL || *end != '\0' || value < min_value || value > max_value) {
        return false;
    }
    *value_out = (uint32_t)value;
    return true;
}

static int cmd_kmsprobe(void) {
    return a90_kms_probe(true);
}

static int cmd_video_status(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    a90_console_printf("video.status.version=1\r\n");
    a90_console_printf("video.status.path=kms-dumb-buffer\r\n");
    a90_console_printf("video.status.venus=not-used\r\n");
    a90_console_printf("video.status.kgsl=not-used\r\n");
    a90_console_printf("video.status.raw_dsi=blocked\r\n");
    a90_console_printf("video.status.power_writes=blocked\r\n");
    a90_console_printf("video.status.kms.initialized=%d\r\n", info.initialized ? 1 : 0);
    if (info.initialized) {
        a90_console_printf("video.status.kms.size=%ux%u\r\n", info.width, info.height);
        a90_console_printf("video.status.kms.connector=%u\r\n", info.connector_id);
        a90_console_printf("video.status.kms.encoder=%u\r\n", info.encoder_id);
        a90_console_printf("video.status.kms.crtc=%u\r\n", info.crtc_id);
        a90_console_printf("video.status.kms.fb=%u\r\n", info.fb_id);
        a90_console_printf("video.status.kms.current_buffer=%u\r\n", info.current_buffer);
        a90_console_printf("video.status.kms.stride=%u\r\n", info.stride);
        a90_console_printf("video.status.kms.map_size=%zu\r\n", info.map_size);
        a90_console_printf("video.status.kms.pixel_format=xbgr8888\r\n");
    } else {
        a90_console_printf("video.status.kms.size=0x0\r\n");
        a90_console_printf("video.status.kms.stride=0\r\n");
        a90_console_printf("video.status.kms.map_size=0\r\n");
        a90_console_printf("video.status.kms.pixel_format=unknown\r\n");
    }
    a90_console_printf("video.status.next=video frame [bars|checker|mono|0xRRGGBB]\r\n");
    a90_console_printf("video.status.next_anim=video anim [bars|checker|pulse] [frames<=240] [delay_ms<=1000]\r\n");
    a90_console_printf("video.status.next_blitbench=video blitbench [frames<=240]\r\n");
    return 0;
}

static uint64_t video_monotonic_ns(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

static uint32_t video_blitbench_pixel(uint32_t x, uint32_t y, uint32_t width, uint32_t height) {
    uint32_t red = (x * 255U) / (width > 1 ? width - 1 : 1);
    uint32_t green = (y * 255U) / (height > 1 ? height - 1 : 1);
    uint32_t blue = ((x ^ y) & 0xffU);

    return (blue << 16) | (green << 8) | red;
}

static void video_blitbench_fill_source(uint32_t *source, uint32_t width, uint32_t height) {
    uint32_t y;

    if (source == NULL) {
        return;
    }
    for (y = 0; y < height; ++y) {
        uint32_t x;

        for (x = 0; x < width; ++x) {
            source[((size_t)y * width) + x] = video_blitbench_pixel(x, y, width, height);
        }
    }
}

static int video_blitbench_copy_frame(struct a90_fb *fb, const uint32_t *source) {
    uint32_t y;
    size_t row_bytes;

    if (fb == NULL || fb->pixels == NULL || source == NULL || fb->width == 0 || fb->height == 0) {
        return -EINVAL;
    }
    row_bytes = (size_t)fb->width * sizeof(uint32_t);
    if (fb->stride < row_bytes) {
        return -EINVAL;
    }

    for (y = 0; y < fb->height; ++y) {
        memcpy((char *)fb->pixels + ((size_t)y * fb->stride),
               source + ((size_t)y * fb->width),
               row_bytes);
    }
    return 0;
}

static void video_draw_bars_phase(struct a90_fb *fb, uint32_t phase) {
    static const uint32_t colors[] = {
        0xffffff, 0xffff00, 0x00ffff, 0x00ff00,
        0xff00ff, 0xff0000, 0x0000ff, 0x202020,
    };
    uint32_t index;
    uint32_t bar_width;

    if (fb == NULL || fb->width == 0) {
        return;
    }
    bar_width = fb->width / (uint32_t)(sizeof(colors) / sizeof(colors[0]));
    if (bar_width == 0) {
        bar_width = 1;
    }
    for (index = 0; index < sizeof(colors) / sizeof(colors[0]); ++index) {
        uint32_t x = index * bar_width;
        uint32_t width = (index + 1 == sizeof(colors) / sizeof(colors[0])) ?
                         (fb->width > x ? fb->width - x : 0) :
                         bar_width;
        a90_draw_rect(fb, x, 0, width, fb->height,
                      colors[(index + phase) % (sizeof(colors) / sizeof(colors[0]))]);
    }
}

static void video_draw_bars(struct a90_fb *fb) {
    video_draw_bars_phase(fb, 0);
}

static void video_draw_checker_phase(struct a90_fb *fb, uint32_t phase) {
    uint32_t tile;
    uint32_t y;

    if (fb == NULL) {
        return;
    }
    tile = fb->width / 12;
    if (tile < 32) {
        tile = 32;
    }
    for (y = 0; y < fb->height; y += tile) {
        uint32_t x;

        for (x = 0; x < fb->width; x += tile) {
            uint32_t color = (((x / tile) + (y / tile) + phase) & 1U) ? 0x101820 : 0xd8e8ff;
            a90_draw_rect(fb, x, y, tile, tile, color);
        }
    }
}

static void video_draw_checker(struct a90_fb *fb) {
    video_draw_checker_phase(fb, 0);
}

static void video_draw_label(struct a90_fb *fb, const char *title, const char *subtitle) {
    uint32_t scale;

    if (fb == NULL) {
        return;
    }
    scale = fb->width >= 1080 ? 4 : 2;
    a90_draw_rect(fb, 24, 24, fb->width > 48 ? fb->width - 48 : fb->width, scale * 18, 0x06101c);
    a90_draw_rect_outline(fb, 24, 24, fb->width > 48 ? fb->width - 48 : fb->width,
                          scale * 18, scale > 2 ? 2 : 1, 0x66ddff);
    a90_draw_text(fb, 24 + scale * 3, 24 + scale * 4, title, 0x66ddff, scale);
    a90_draw_text(fb, 24 + scale * 3, 24 + scale * 11, subtitle, 0xffffff, scale > 2 ? 2 : 1);
}

static int cmd_video_frame(char **argv, int argc) {
    const char *pattern = argc >= 3 ? argv[2] : "bars";
    struct a90_fb *fb;
    uint32_t color = 0x05070c;
    bool solid = false;

    if (argc > 3) {
        a90_console_printf("usage: video frame [bars|checker|mono|0xRRGGBB]\r\n");
        return -EINVAL;
    }
    if (strcmp(pattern, "bars") != 0 &&
        strcmp(pattern, "checker") != 0 &&
        strcmp(pattern, "mono") != 0) {
        if (!parse_color_arg(pattern, &color)) {
            a90_console_printf("usage: video frame [bars|checker|mono|0xRRGGBB]\r\n");
            return -EINVAL;
        }
        solid = true;
    }

    if (a90_kms_begin_frame(color) < 0) {
        return negative_errno_or(ENODEV);
    }
    fb = a90_kms_framebuffer();
    if (fb == NULL) {
        return -ENODEV;
    }

    if (strcmp(pattern, "bars") == 0) {
        video_draw_bars(fb);
    } else if (strcmp(pattern, "checker") == 0) {
        video_draw_checker(fb);
    } else if (strcmp(pattern, "mono") == 0 || solid) {
        a90_draw_clear(fb, color);
    }

    video_draw_label(fb, "A90 VIDEO FRAME", pattern);

    if (a90_kms_present("videoframe", true) < 0) {
        return negative_errno_or(EIO);
    }
    a90_console_printf("video.frame.presented=1\r\n");
    a90_console_printf("video.frame.pattern=%s\r\n", pattern);
    a90_console_printf("video.frame.size=%ux%u\r\n", fb->width, fb->height);
    a90_console_printf("video.frame.path=kms-dumb-buffer\r\n");
    return 0;
}

static uint32_t video_pulse_color(uint32_t frame_index, uint32_t frame_count) {
    uint32_t denom = frame_count > 1 ? frame_count - 1 : 1;
    uint32_t level = (frame_index * 255U) / denom;
    uint32_t inverse = 255U - level;

    return ((level & 0xffU) << 16) | ((inverse & 0xffU) << 8) | 0x40U;
}

static int cmd_video_anim(char **argv, int argc) {
    const char *pattern = argc >= 3 ? argv[2] : "bars";
    uint32_t frames = 30;
    uint32_t delay_ms = 33;
    uint32_t frame_index;

    if (argc > 5 ||
        (strcmp(pattern, "bars") != 0 && strcmp(pattern, "checker") != 0 && strcmp(pattern, "pulse") != 0)) {
        a90_console_printf("usage: video anim [bars|checker|pulse] [frames<=240] [delay_ms<=1000]\r\n");
        return -EINVAL;
    }
    if (argc >= 4 && !parse_u32_arg(argv[3], 1, 240, &frames)) {
        a90_console_printf("usage: video anim [bars|checker|pulse] [frames<=240] [delay_ms<=1000]\r\n");
        return -EINVAL;
    }
    if (argc >= 5 && !parse_u32_arg(argv[4], 0, 1000, &delay_ms)) {
        a90_console_printf("usage: video anim [bars|checker|pulse] [frames<=240] [delay_ms<=1000]\r\n");
        return -EINVAL;
    }

    for (frame_index = 0; frame_index < frames; ++frame_index) {
        struct a90_fb *fb;
        char subtitle[64];
        uint32_t color = strcmp(pattern, "pulse") == 0 ? video_pulse_color(frame_index, frames) : 0x000000;

        if (a90_kms_begin_frame(color) < 0) {
            return negative_errno_or(ENODEV);
        }
        fb = a90_kms_framebuffer();
        if (fb == NULL) {
            return -ENODEV;
        }

        if (strcmp(pattern, "bars") == 0) {
            video_draw_bars_phase(fb, frame_index);
        } else if (strcmp(pattern, "checker") == 0) {
            video_draw_checker_phase(fb, frame_index);
        } else {
            a90_draw_clear(fb, color);
        }
        snprintf(subtitle, sizeof(subtitle), "%s %u/%u", pattern, frame_index + 1, frames);
        video_draw_label(fb, "A90 VIDEO ANIM", subtitle);

        if (a90_kms_present("videoanim", true) < 0) {
            return negative_errno_or(EIO);
        }
        if (frame_index + 1 < frames && delay_ms > 0) {
            enum a90_cancel_kind cancel = a90_console_poll_cancel((int)delay_ms);

            if (cancel != CANCEL_NONE) {
                a90_console_printf("video.anim.presented=%u\r\n", frame_index + 1);
                return a90_console_cancelled("videoanim", cancel);
            }
        }
    }

    a90_console_printf("video.anim.presented=%u\r\n", frames);
    a90_console_printf("video.anim.pattern=%s\r\n", pattern);
    a90_console_printf("video.anim.delay_ms=%u\r\n", delay_ms);
    a90_console_printf("video.anim.path=kms-dumb-buffer\r\n");
    return 0;
}

static int cmd_video_blitbench(char **argv, int argc) {
    uint32_t frames = 30;
    uint32_t frame_index;
    struct a90_fb *fb;
    uint32_t *source = NULL;
    size_t frame_bytes;
    size_t row_bytes;
    uint64_t started_ns;
    uint64_t finished_ns;
    uint64_t elapsed_ns;
    uint64_t total_bytes;
    uint64_t fps_milli;
    uint64_t mbps_milli;
    int result = 0;

    if (argc > 3) {
        a90_console_printf("usage: video blitbench [frames<=240]\r\n");
        return -EINVAL;
    }
    if (argc >= 3 && !parse_u32_arg(argv[2], 1, 240, &frames)) {
        a90_console_printf("usage: video blitbench [frames<=240]\r\n");
        return -EINVAL;
    }

    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    fb = a90_kms_framebuffer();
    if (fb == NULL || fb->width == 0 || fb->height == 0) {
        return -ENODEV;
    }

    row_bytes = (size_t)fb->width * sizeof(uint32_t);
    frame_bytes = row_bytes * fb->height;
    if (fb->stride < row_bytes || frame_bytes == 0 || frame_bytes > (64U * 1024U * 1024U)) {
        a90_console_printf("video.blitbench.error=invalid-frame-geometry\r\n");
        return -EINVAL;
    }

    source = (uint32_t *)malloc(frame_bytes);
    if (source == NULL) {
        a90_console_printf("video.blitbench.error=alloc-failed\r\n");
        return -ENOMEM;
    }
    video_blitbench_fill_source(source, fb->width, fb->height);

    started_ns = video_monotonic_ns();
    for (frame_index = 0; frame_index < frames; ++frame_index) {
        enum a90_cancel_kind cancel;

        if (a90_kms_begin_frame_no_clear() < 0) {
            result = negative_errno_or(ENODEV);
            break;
        }
        fb = a90_kms_framebuffer();
        result = video_blitbench_copy_frame(fb, source);
        if (result < 0) {
            break;
        }
        if (a90_kms_present("videoblitbench", false) < 0) {
            result = negative_errno_or(EIO);
            break;
        }

        cancel = a90_console_poll_cancel(0);
        if (cancel != CANCEL_NONE) {
            a90_console_printf("video.blitbench.presented=%u\r\n", frame_index + 1);
            free(source);
            return a90_console_cancelled("videoblitbench", cancel);
        }
    }
    finished_ns = video_monotonic_ns();

    free(source);
    if (result < 0) {
        return result;
    }

    elapsed_ns = finished_ns > started_ns ? finished_ns - started_ns : 1;
    total_bytes = (uint64_t)frame_bytes * frames;
    fps_milli = ((uint64_t)frames * 1000000000000ULL) / elapsed_ns;
    mbps_milli = (total_bytes * 1000000ULL) / elapsed_ns;

    a90_console_printf("video.blitbench.presented=%u\r\n", frames);
    a90_console_printf("video.blitbench.frames=%u\r\n", frames);
    a90_console_printf("video.blitbench.bytes=%llu\r\n", (unsigned long long)total_bytes);
    a90_console_printf("video.blitbench.elapsed_ns=%llu\r\n", (unsigned long long)elapsed_ns);
    a90_console_printf("video.blitbench.fps_milli=%llu\r\n", (unsigned long long)fps_milli);
    a90_console_printf("video.blitbench.mbps_milli=%llu\r\n", (unsigned long long)mbps_milli);
    a90_console_printf("video.blitbench.width=%u\r\n", fb->width);
    a90_console_printf("video.blitbench.height=%u\r\n", fb->height);
    a90_console_printf("video.blitbench.stride=%u\r\n", fb->stride);
    a90_console_printf("video.blitbench.frame_bytes=%zu\r\n", frame_bytes);
    a90_console_printf("video.blitbench.pixel_format=xbgr8888\r\n");
    a90_console_printf("video.blitbench.path=kms-dumb-buffer\r\n");
    return 0;
}

static int handle_video(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";

    if (strcmp(subcommand, "status") == 0) {
        if (argc != 1 && argc != 2) {
            a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]]\r\n");
            return -EINVAL;
        }
        return cmd_video_status();
    }
    if (strcmp(subcommand, "frame") == 0 || strcmp(subcommand, "demo") == 0) {
        return cmd_video_frame(argv, argc);
    }
    if (strcmp(subcommand, "anim") == 0) {
        return cmd_video_anim(argv, argc);
    }
    if (strcmp(subcommand, "blitbench") == 0) {
        return cmd_video_blitbench(argv, argc);
    }

    a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]]\r\n");
    return -EINVAL;
}

static int cmd_kmssolid(char **argv, int argc) {
    uint32_t color = 0x000000;

    if (argc >= 2 && !parse_color_arg(argv[1], &color)) {
        a90_console_printf("usage: kmssolid [black|white|red|green|blue|gray|0xRRGGBB]\r\n");
        return -EINVAL;
    }

    if (a90_kms_begin_frame(color) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (a90_kms_present("kmssolid", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_kmsframe(void) {
    if (a90_kms_begin_frame(0x080808) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_draw_boot_frame(a90_kms_framebuffer());
    if (a90_kms_present("kmsframe", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statusscreen(void) {
    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_console_printf("statusscreen: drawing giant TEST probe\r\n");
    a90_draw_giant_test_probe(a90_kms_framebuffer());
    if (a90_kms_present("statusscreen", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statushud(void) {
    struct a90_hud_storage_status storage = current_hud_storage_status();

    a90_console_printf("statushud: drawing sensor HUD\r\n");
    return a90_hud_draw_status_frame(&storage, "statushud", true);
}

static int wait_watch_delay(int refresh_sec) {
    int remaining_ticks = refresh_sec * 10;

    while (remaining_ticks-- > 0) {
        enum a90_cancel_kind cancel = a90_console_poll_cancel(100);

        if (cancel != CANCEL_NONE) {
            return a90_console_cancelled("watchhud", cancel);
        }
    }

    return 0;
}

static int clamp_hud_refresh(int refresh_sec);

static int cmd_watchhud(char **argv, int argc) {
    int refresh_sec = 2;
    int count = 0;
    int index = 0;
    int first_error = 0;
    bool drew_frame = false;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        a90_console_printf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    refresh_sec = clamp_hud_refresh(refresh_sec);

    a90_console_printf("watchhud: refresh=%ds count=%s, q/Ctrl-C cancels\r\n",
            refresh_sec,
            count > 0 ? argv[2] : "forever");

    while (count <= 0 || index < count) {
        if (a90_kms_begin_frame(0x000000) == 0) {
            struct a90_hud_storage_status storage = current_hud_storage_status();

            a90_hud_draw_status_overlay(a90_kms_framebuffer(),
                                        &storage,
                                        (unsigned int)refresh_sec,
                                        (unsigned int)(index + 1));
            if (a90_kms_present("watchhud", true) == 0) {
                drew_frame = true;
            } else if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        } else if (first_error == 0) {
            first_error = negative_errno_or(ENODEV);
        }
        ++index;
        if (count > 0 && index >= count) {
            break;
        }
        {
            int wait_rc = wait_watch_delay(refresh_sec);

            if (wait_rc < 0) {
                return wait_rc;
            }
        }
    }

    return drew_frame ? 0 : first_error;
}

static int clamp_hud_refresh(int refresh_sec) {
    if (refresh_sec < 1) {
        return 1;
    }
    if (refresh_sec > 60) {
        return 60;
    }
    return refresh_sec;
}

static void reap_hud_child(void) {
    if (a90_service_reap(A90_SERVICE_HUD, NULL) > 0) {
        a90_controller_clear_menu_ipc();
    }
}

static void stop_auto_hud(bool verbose) {
    reap_hud_child();
    if (a90_service_pid(A90_SERVICE_HUD) <= 0) {
        if (verbose) {
            a90_console_printf("autohud: not running\r\n");
        }
        return;
    }

    (void)a90_service_stop(A90_SERVICE_HUD, 2000);
    a90_controller_clear_menu_ipc();
    if (verbose) {
        a90_console_printf("autohud: stopped\r\n");
    }
}

/* forward declarations for auto_hud_loop */
