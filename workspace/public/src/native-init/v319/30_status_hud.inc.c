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
    a90_console_printf("video.status.version=5\r\n");
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
    a90_console_printf("video.status.next_stream=video stream --manifest PATH --video-only [--frames N]\r\n");
    a90_console_printf("video.status.next_stream_pageflip=video stream --manifest PATH --video-only [--frames N] --present pageflip\r\n");
    a90_console_printf("video.status.next_stream_sync=video stream --manifest PATH --video-only [--frames N] --present pageflip --sync-audio-status /cache/a90-audio-play/status.txt\r\n");
    a90_console_printf("video.status.next_flipprobe=video flipprobe [frames<=120]\r\n");
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

static int cmd_video_flipprobe(char **argv, int argc) {
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
    uint32_t flip_events = 0;
    struct a90_kms_flip_result last_flip;
    int result = 0;

    if (argc > 3) {
        a90_console_printf("usage: video flipprobe [frames<=120]\r\n");
        return -EINVAL;
    }
    if (argc >= 3 && !parse_u32_arg(argv[2], 1, 120, &frames)) {
        a90_console_printf("usage: video flipprobe [frames<=120]\r\n");
        return -EINVAL;
    }

    memset(&last_flip, 0, sizeof(last_flip));
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
        a90_console_printf("video.flipprobe.error=invalid-frame-geometry\r\n");
        return -EINVAL;
    }

    source = (uint32_t *)malloc(frame_bytes);
    if (source == NULL) {
        a90_console_printf("video.flipprobe.error=alloc-failed\r\n");
        return -ENOMEM;
    }
    video_blitbench_fill_source(source, fb->width, fb->height);

    if (a90_kms_present("videoflipprime", false) < 0) {
        free(source);
        return negative_errno_or(EIO);
    }

    started_ns = video_monotonic_ns();
    for (frame_index = 0; frame_index < frames; ++frame_index) {
        enum a90_cancel_kind cancel;
        struct a90_kms_flip_result flip;

        if (a90_kms_begin_frame_no_clear() < 0) {
            result = negative_errno_or(ENODEV);
            break;
        }
        fb = a90_kms_framebuffer();
        result = video_blitbench_copy_frame(fb, source);
        if (result < 0) {
            break;
        }
        if (a90_kms_present_pageflip("videoflipprobe", 1000, &flip) < 0) {
            result = negative_errno_or(EIO);
            break;
        }
        if (flip.event_received) {
            last_flip = flip;
            ++flip_events;
        }

        cancel = a90_console_poll_cancel(0);
        if (cancel != CANCEL_NONE) {
            a90_console_printf("video.flipprobe.presented=%u\r\n", frame_index + 1);
            free(source);
            return a90_console_cancelled("videoflipprobe", cancel);
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

    a90_console_printf("video.flipprobe.presented=%u\r\n", frames);
    a90_console_printf("video.flipprobe.frames=%u\r\n", frames);
    a90_console_printf("video.flipprobe.bytes=%llu\r\n", (unsigned long long)total_bytes);
    a90_console_printf("video.flipprobe.elapsed_ns=%llu\r\n", (unsigned long long)elapsed_ns);
    a90_console_printf("video.flipprobe.fps_milli=%llu\r\n", (unsigned long long)fps_milli);
    a90_console_printf("video.flipprobe.mbps_milli=%llu\r\n", (unsigned long long)mbps_milli);
    a90_console_printf("video.flipprobe.flip_events=%u\r\n", flip_events);
    a90_console_printf("video.flipprobe.last_sequence=%u\r\n", last_flip.sequence);
    a90_console_printf("video.flipprobe.last_crtc=%u\r\n", last_flip.crtc_id);
    a90_console_printf("video.flipprobe.last_timestamp_us=%llu\r\n",
                       (unsigned long long)last_flip.timestamp_us);
    a90_console_printf("video.flipprobe.ioctl=DRM_IOCTL_MODE_PAGE_FLIP\r\n");
    a90_console_printf("video.flipprobe.width=%u\r\n", fb->width);
    a90_console_printf("video.flipprobe.height=%u\r\n", fb->height);
    a90_console_printf("video.flipprobe.stride=%u\r\n", fb->stride);
    a90_console_printf("video.flipprobe.frame_bytes=%zu\r\n", frame_bytes);
    a90_console_printf("video.flipprobe.pixel_format=xbgr8888\r\n");
    a90_console_printf("video.flipprobe.path=kms-dumb-buffer-pageflip\r\n");
    return 0;
}

#define VIDEO_STREAM_MANIFEST_MAX_BYTES (64U * 1024U)
#define VIDEO_STREAM_OBJECT_MAX_BYTES (8U * 1024U)
#define VIDEO_STREAM_MAX_FRAMES 600U
#define VIDEO_STREAM_MAX_FRAME_BYTES (64U * 1024U * 1024U)
#define VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE 1U
#define VIDEO_STREAM_AUDIO_STATUS_PATH "/cache/a90-audio-play/status.txt"
#define VIDEO_STREAM_AUDIO_SYNC_DEFAULT_WAIT_MS 90000U
#define VIDEO_STREAM_AUDIO_SYNC_POLL_MS 20U

enum video_stream_present_mode {
    VIDEO_STREAM_PRESENT_SETCRTC = 0,
    VIDEO_STREAM_PRESENT_PAGEFLIP = 1,
};

struct video_stream_manifest {
    char video_path[PATH_MAX];
    char stream_path[PATH_MAX];
    char format[64];
    char sha256[65];
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t frame_bytes;
    uint32_t visible_row_bytes;
    uint32_t fps_num;
    uint32_t fps_den;
    uint32_t frame_count;
};

struct video_stream_header_v1 {
    char magic[8];
    uint32_t version;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t pixel_format;
    uint32_t fps_num;
    uint32_t fps_den;
    uint32_t frame_count;
    uint32_t frame_bytes;
    uint8_t reserved[32];
};

struct video_stream_frame_record_v1 {
    uint32_t index;
    uint32_t payload_bytes;
    uint64_t pts_ns;
};

struct video_audio_sync_state {
    bool enabled;
    bool ready;
    char status_path[PATH_MAX];
    uint32_t wait_ms;
    uint32_t sample_rate;
    uint32_t frame_bytes;
    uint32_t total_frames;
    uint64_t expected_duration_ns;
    uint64_t listen_begin_ns;
    uint64_t ready_elapsed_ms;
    uint64_t anchor_age_ns;
};

static bool video_json_space(char ch) {
    return ch == ' ' || ch == '\n' || ch == '\r' || ch == '\t';
}

static const char *video_json_skip_space(const char *cursor) {
    while (*cursor != '\0' && video_json_space(*cursor)) {
        ++cursor;
    }
    return cursor;
}

static const char *video_json_find_key(const char *json, const char *key) {
    char pattern[96];
    size_t key_len;
    const char *cursor;

    if (json == NULL || key == NULL) {
        return NULL;
    }
    key_len = strlen(key);
    if (key_len == 0 || key_len + 3 > sizeof(pattern)) {
        return NULL;
    }
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    cursor = json;
    while ((cursor = strstr(cursor, pattern)) != NULL) {
        const char *after = video_json_skip_space(cursor + strlen(pattern));

        if (*after == ':') {
            return video_json_skip_space(after + 1);
        }
        ++cursor;
    }
    return NULL;
}

static bool video_json_extract_string(const char *json, const char *key, char *out, size_t out_size) {
    const char *cursor;
    size_t used = 0;

    if (out == NULL || out_size == 0) {
        return false;
    }
    out[0] = '\0';
    cursor = video_json_find_key(json, key);
    if (cursor == NULL || *cursor != '"') {
        return false;
    }
    ++cursor;
    while (*cursor != '\0' && *cursor != '"') {
        unsigned char ch = (unsigned char)*cursor;

        if (*cursor == '\\' || ch < 0x20U || used + 1 >= out_size) {
            return false;
        }
        out[used++] = *cursor++;
    }
    if (*cursor != '"') {
        return false;
    }
    out[used] = '\0';
    return used > 0;
}

static bool video_json_extract_u32(const char *json, const char *key,
                                   uint32_t min_value, uint32_t max_value,
                                   uint32_t *out) {
    const char *cursor;
    char *end = NULL;
    unsigned long value;

    if (out == NULL) {
        return false;
    }
    cursor = video_json_find_key(json, key);
    if (cursor == NULL) {
        return false;
    }
    errno = 0;
    value = strtoul(cursor, &end, 10);
    if (errno != 0 || end == NULL || end == cursor || value < min_value || value > max_value) {
        return false;
    }
    *out = (uint32_t)value;
    return true;
}

static bool video_path_is_safe_relative(const char *path) {
    const char *cursor;
    const char *segment;

    if (path == NULL || path[0] == '\0' || path[0] == '/') {
        return false;
    }
    for (cursor = path; *cursor != '\0'; ++cursor) {
        if (*cursor == '\\') {
            return false;
        }
    }
    segment = path;
    for (;;) {
        const char *slash = strchr(segment, '/');
        size_t len = slash != NULL ? (size_t)(slash - segment) : strlen(segment);

        if (len == 0 || (len == 1 && segment[0] == '.') ||
            (len == 2 && segment[0] == '.' && segment[1] == '.')) {
            return false;
        }
        if (slash == NULL) {
            break;
        }
        segment = slash + 1;
    }
    return true;
}

static char video_ascii_lower_hex(char ch) {
    if (ch >= 'A' && ch <= 'F') {
        return (char)(ch - 'A' + 'a');
    }
    return ch;
}

static bool video_text_is_sha256(const char *text) {
    size_t index;

    if (text == NULL || strlen(text) != 64) {
        return false;
    }
    for (index = 0; index < 64; ++index) {
        char ch = text[index];

        if (!((ch >= '0' && ch <= '9') ||
              (ch >= 'a' && ch <= 'f') ||
              (ch >= 'A' && ch <= 'F'))) {
            return false;
        }
    }
    return true;
}

static bool video_find_json_object(const char *json, const char *key,
                                   const char **object_start, const char **object_end) {
    const char *cursor = video_json_find_key(json, key);
    unsigned int depth = 0;
    bool in_string = false;
    bool escaped = false;

    if (cursor == NULL || *cursor != '{') {
        return false;
    }
    *object_start = cursor;
    for (; *cursor != '\0'; ++cursor) {
        char ch = *cursor;

        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                in_string = false;
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
            continue;
        }
        if (ch == '{') {
            ++depth;
        } else if (ch == '}') {
            if (depth == 0) {
                return false;
            }
            --depth;
            if (depth == 0) {
                *object_end = cursor + 1;
                return true;
            }
        }
    }
    return false;
}

static bool video_manifest_dirname(const char *manifest_path, char *out, size_t out_size) {
    const char *slash;
    size_t len;

    if (manifest_path == NULL || manifest_path[0] == '\0' || out == NULL || out_size == 0) {
        return false;
    }
    slash = strrchr(manifest_path, '/');
    if (slash == NULL) {
        return snprintf(out, out_size, ".") < (int)out_size;
    }
    len = (size_t)(slash - manifest_path);
    if (len == 0) {
        len = 1;
    }
    if (len >= out_size) {
        return false;
    }
    memcpy(out, manifest_path, len);
    out[len] = '\0';
    return true;
}

static bool video_join_manifest_path(const char *manifest_path, const char *relative,
                                     char *out, size_t out_size) {
    char dir[PATH_MAX];

    if (!video_path_is_safe_relative(relative) ||
        !video_manifest_dirname(manifest_path, dir, sizeof(dir))) {
        return false;
    }
    if (strcmp(dir, ".") == 0) {
        return snprintf(out, out_size, "%s", relative) < (int)out_size;
    }
    return snprintf(out, out_size, "%s/%s", dir, relative) < (int)out_size;
}

static int video_read_manifest_file(const char *path, char **out_text) {
    struct stat st;
    char *text;
    int fd;
    size_t done = 0;

    if (path == NULL || out_text == NULL) {
        return -EINVAL;
    }
    *out_text = NULL;
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return negative_errno_or(ENOENT);
    }
    if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode) || st.st_size <= 0 ||
        st.st_size > (off_t)VIDEO_STREAM_MANIFEST_MAX_BYTES) {
        close(fd);
        return -EINVAL;
    }
    text = (char *)malloc((size_t)st.st_size + 1U);
    if (text == NULL) {
        close(fd);
        return -ENOMEM;
    }
    while (done < (size_t)st.st_size) {
        ssize_t rd = read(fd, text + done, (size_t)st.st_size - done);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            free(text);
            close(fd);
            return negative_errno_or(EIO);
        }
        if (rd == 0) {
            free(text);
            close(fd);
            return -EIO;
        }
        done += (size_t)rd;
    }
    close(fd);
    text[st.st_size] = '\0';
    *out_text = text;
    return 0;
}

static int video_parse_manifest(const char *manifest_path, struct video_stream_manifest *manifest) {
    char *text = NULL;
    char video_object[VIDEO_STREAM_OBJECT_MAX_BYTES];
    const char *object_start;
    const char *object_end;
    size_t object_len;
    uint64_t expected_frame_bytes;
    int rc;

    memset(manifest, 0, sizeof(*manifest));
    rc = video_read_manifest_file(manifest_path, &text);
    if (rc < 0) {
        a90_console_printf("video.stream.error=manifest-read-failed rc=%d\r\n", rc);
        return rc;
    }
    if (!video_find_json_object(text, "video", &object_start, &object_end)) {
        free(text);
        a90_console_printf("video.stream.error=manifest-video-object-missing\r\n");
        return -EINVAL;
    }
    object_len = (size_t)(object_end - object_start);
    if (object_len == 0 || object_len >= sizeof(video_object)) {
        free(text);
        a90_console_printf("video.stream.error=manifest-video-object-too-large\r\n");
        return -EINVAL;
    }
    memcpy(video_object, object_start, object_len);
    video_object[object_len] = '\0';

    if (!video_json_extract_string(video_object, "path", manifest->video_path, sizeof(manifest->video_path)) ||
        !video_json_extract_string(video_object, "format", manifest->format, sizeof(manifest->format)) ||
        !video_json_extract_string(video_object, "sha256", manifest->sha256, sizeof(manifest->sha256)) ||
        !video_json_extract_u32(video_object, "width", 1, 8192, &manifest->width) ||
        !video_json_extract_u32(video_object, "height", 1, 8192, &manifest->height) ||
        !video_json_extract_u32(video_object, "stride", 4, VIDEO_STREAM_MAX_FRAME_BYTES, &manifest->stride) ||
        !video_json_extract_u32(video_object, "frame_bytes", 4, VIDEO_STREAM_MAX_FRAME_BYTES, &manifest->frame_bytes) ||
        !video_json_extract_u32(video_object, "visible_row_bytes", 4, VIDEO_STREAM_MAX_FRAME_BYTES, &manifest->visible_row_bytes) ||
        !video_json_extract_u32(video_object, "fps_num", 1, 240, &manifest->fps_num) ||
        !video_json_extract_u32(video_object, "fps_den", 1, 1000000, &manifest->fps_den) ||
        !video_json_extract_u32(video_object, "frame_count", 1, VIDEO_STREAM_MAX_FRAMES, &manifest->frame_count)) {
        free(text);
        a90_console_printf("video.stream.error=manifest-field-invalid\r\n");
        return -EINVAL;
    }
    free(text);

    if (strcmp(manifest->format, "xbgr8888-raw-stride") != 0 ||
        !video_text_is_sha256(manifest->sha256) ||
        !video_join_manifest_path(manifest_path, manifest->video_path,
                                  manifest->stream_path, sizeof(manifest->stream_path))) {
        a90_console_printf("video.stream.error=manifest-policy-reject\r\n");
        return -EINVAL;
    }
    expected_frame_bytes = (uint64_t)manifest->stride * manifest->height;
    if ((uint64_t)manifest->width * 4ULL != manifest->visible_row_bytes ||
        manifest->stride < manifest->visible_row_bytes ||
        expected_frame_bytes != manifest->frame_bytes) {
        a90_console_printf("video.stream.error=manifest-geometry-invalid\r\n");
        return -EINVAL;
    }
    return 0;
}

static int video_read_exact_fd(int fd, void *buffer, size_t bytes) {
    size_t done = 0;

    while (done < bytes) {
        ssize_t rd = read(fd, (char *)buffer + done, bytes - done);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return negative_errno_or(EIO);
        }
        if (rd == 0) {
            return -EIO;
        }
        done += (size_t)rd;
    }
    return 0;
}

static int video_validate_stream_header(const struct video_stream_manifest *manifest,
                                        const struct video_stream_header_v1 *header) {
    if (memcmp(header->magic, "A90VSTR1", 8) != 0 ||
        header->version != 1 ||
        header->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE ||
        header->width != manifest->width ||
        header->height != manifest->height ||
        header->stride != manifest->stride ||
        header->fps_num != manifest->fps_num ||
        header->fps_den != manifest->fps_den ||
        header->frame_count != manifest->frame_count ||
        header->frame_bytes != manifest->frame_bytes) {
        return -EINVAL;
    }
    return 0;
}

static bool video_sha256_equal_fold(const char *actual, const char *expected) {
    size_t index;

    if (actual == NULL || expected == NULL) {
        return false;
    }
    for (index = 0; index < 64; ++index) {
        if (video_ascii_lower_hex(actual[index]) != video_ascii_lower_hex(expected[index])) {
            return false;
        }
    }
    return actual[64] == '\0' && expected[64] == '\0';
}

static int video_stream_verify_hash(const struct video_stream_manifest *manifest, char *actual_out,
                                    size_t actual_out_size) {
    if (a90_helper_sha256_file(manifest->stream_path, actual_out, actual_out_size) < 0) {
        return negative_errno_or(EIO);
    }
    if (!video_sha256_equal_fold(actual_out, manifest->sha256)) {
        a90_console_printf("video.stream.expected_sha256=%s\r\n", manifest->sha256);
        a90_console_printf("video.stream.actual_sha256=%s\r\n", actual_out);
        a90_console_printf("video.stream.sha256_match=0\r\n");
        return -EINVAL;
    }
    return 0;
}

static int video_wait_until_ns(uint64_t deadline_ns) {
    for (;;) {
        uint64_t now_ns = video_monotonic_ns();
        uint64_t remaining_ns;
        int wait_ms;
        enum a90_cancel_kind cancel;

        if (now_ns == 0 || now_ns >= deadline_ns) {
            return 0;
        }
        remaining_ns = deadline_ns - now_ns;
        wait_ms = (int)(remaining_ns / 1000000ULL);
        if (wait_ms <= 0) {
            wait_ms = 1;
        } else if (wait_ms > 100) {
            wait_ms = 100;
        }
        cancel = a90_console_poll_cancel(wait_ms);
        if (cancel != CANCEL_NONE) {
            return a90_console_cancelled("videostream", cancel);
        }
    }
}

static uint64_t video_frame_interval_ns(uint32_t fps_num, uint32_t fps_den) {
    uint64_t numerator = (uint64_t)fps_den * 1000000000ULL;

    if (fps_num == 0) {
        return 0;
    }
    return numerator / fps_num;
}

static const char *video_stream_present_mode_name(enum video_stream_present_mode present_mode) {
    return present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP ? "pageflip" : "setcrtc";
}

static const char *video_stream_present_path_name(enum video_stream_present_mode present_mode) {
    return present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP ?
           "kms-dumb-buffer-pageflip" : "kms-dumb-buffer";
}

static bool video_audio_sync_status_path_allowed(const char *path) {
    return path != NULL && strcmp(path, VIDEO_STREAM_AUDIO_STATUS_PATH) == 0;
}

static bool video_audio_sync_extract_u64(const char *text, const char *key, uint64_t *out) {
    const char *cursor;
    char *end = NULL;
    unsigned long long value;
    char pattern[96];

    if (text == NULL || key == NULL || out == NULL || strlen(key) + 2 > sizeof(pattern)) {
        return false;
    }
    snprintf(pattern, sizeof(pattern), "%s=", key);
    cursor = strstr(text, pattern);
    if (cursor == NULL) {
        return false;
    }
    cursor += strlen(pattern);
    errno = 0;
    value = strtoull(cursor, &end, 10);
    if (errno != 0 || end == NULL || end == cursor) {
        return false;
    }
    *out = (uint64_t)value;
    return true;
}

static bool video_audio_sync_extract_u32(const char *text, const char *key, uint32_t *out) {
    uint64_t value;

    if (!video_audio_sync_extract_u64(text, key, &value) || value > UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)value;
    return true;
}

static bool video_audio_sync_read_status(struct video_audio_sync_state *sync) {
    char status[8192];

    if (sync == NULL || !sync->enabled || !video_audio_sync_status_path_allowed(sync->status_path)) {
        return false;
    }
    if (read_text_file(sync->status_path, status, sizeof(status)) < 0) {
        return false;
    }
    if (!video_audio_sync_extract_u64(status, "audio.play.worker.listen_begin_ns", &sync->listen_begin_ns) ||
        !video_audio_sync_extract_u32(status, "audio.play.worker.sample_rate", &sync->sample_rate) ||
        !video_audio_sync_extract_u32(status, "audio.play.worker.frame_bytes", &sync->frame_bytes) ||
        !video_audio_sync_extract_u32(status, "audio.play.worker.total_frames", &sync->total_frames)) {
        return false;
    }
    (void)video_audio_sync_extract_u64(status,
                                       "audio.play.worker.expected_duration_ns",
                                       &sync->expected_duration_ns);
    return sync->listen_begin_ns > 0 && sync->sample_rate > 0 &&
           sync->frame_bytes > 0 && sync->total_frames > 0;
}

static int video_audio_sync_wait_ready(struct video_audio_sync_state *sync) {
    uint32_t elapsed_ms = 0;
    uint64_t now_ns;

    if (sync == NULL || !sync->enabled) {
        return 0;
    }
    if (!video_audio_sync_status_path_allowed(sync->status_path)) {
        a90_console_printf("video.stream.audio_sync.error=status-path-not-allowed\r\n");
        return -EINVAL;
    }
    while (elapsed_ms <= sync->wait_ms) {
        if (video_audio_sync_read_status(sync)) {
            sync->ready = true;
            sync->ready_elapsed_ms = elapsed_ms;
            now_ns = video_monotonic_ns();
            sync->anchor_age_ns = now_ns > sync->listen_begin_ns ? now_ns - sync->listen_begin_ns : 0;
            a90_console_printf("video.stream.audio_sync.ready=1 elapsed_ms=%llu\r\n",
                               (unsigned long long)sync->ready_elapsed_ms);
            a90_console_printf("video.stream.audio_sync.listen_begin_ns=%llu\r\n",
                               (unsigned long long)sync->listen_begin_ns);
            a90_console_printf("video.stream.audio_sync.anchor_age_ns=%llu\r\n",
                               (unsigned long long)sync->anchor_age_ns);
            a90_console_printf("video.stream.audio_sync.sample_rate=%u\r\n", sync->sample_rate);
            a90_console_printf("video.stream.audio_sync.frame_bytes=%u\r\n", sync->frame_bytes);
            a90_console_printf("video.stream.audio_sync.total_frames=%u\r\n", sync->total_frames);
            a90_console_printf("video.stream.audio_sync.expected_duration_ns=%llu\r\n",
                               (unsigned long long)sync->expected_duration_ns);
            return 0;
        }
        usleep((useconds_t)VIDEO_STREAM_AUDIO_SYNC_POLL_MS * 1000U);
        elapsed_ms += VIDEO_STREAM_AUDIO_SYNC_POLL_MS;
    }
    a90_console_printf("video.stream.audio_sync.ready=0 elapsed_ms=%u errno=%d\r\n",
                       elapsed_ms,
                       ETIMEDOUT);
    return -ETIMEDOUT;
}

static int video_stream_play(const struct video_stream_manifest *manifest,
                             uint32_t requested_frames,
                             enum video_stream_present_mode present_mode,
                             struct video_audio_sync_state *audio_sync) {
    struct video_stream_header_v1 header;
    uint32_t limit_frames = requested_frames > 0 && requested_frames < manifest->frame_count ?
                            requested_frames : manifest->frame_count;
    uint64_t interval_ns = video_frame_interval_ns(manifest->fps_num, manifest->fps_den);
    uint64_t started_ns;
    uint64_t finished_ns;
    uint64_t total_bytes = 0;
    uint64_t late_frames = 0;
    uint64_t max_late_ns = 0;
    uint32_t flip_events = 0;
    struct a90_kms_flip_result last_flip;
    uint32_t frame_index;
    int fd;
    int rc;

    memset(&last_flip, 0, sizeof(last_flip));
    if (interval_ns == 0) {
        return -EINVAL;
    }
    fd = open(manifest->stream_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        a90_console_printf("video.stream.error=stream-open-failed\r\n");
        return negative_errno_or(ENOENT);
    }
    rc = video_read_exact_fd(fd, &header, sizeof(header));
    if (rc < 0 || video_validate_stream_header(manifest, &header) < 0) {
        close(fd);
        a90_console_printf("video.stream.error=stream-header-invalid\r\n");
        return rc < 0 ? rc : -EINVAL;
    }

    if (a90_kms_begin_frame_no_clear() < 0) {
        close(fd);
        return negative_errno_or(ENODEV);
    }
    {
        struct a90_fb *fb = a90_kms_framebuffer();

        if (fb == NULL || fb->pixels == NULL || fb->width != manifest->width ||
            fb->height != manifest->height || fb->stride != manifest->stride ||
            fb->size < manifest->frame_bytes) {
            close(fd);
            a90_console_printf("video.stream.error=kms-geometry-mismatch\r\n");
            return -EINVAL;
        }
    }
    if (present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP &&
        a90_kms_present("videostreamprime", false) < 0) {
        close(fd);
        return negative_errno_or(EIO);
    }

    if (audio_sync != NULL && audio_sync->enabled) {
        a90_console_printf("video.stream.audio_sync.enabled=1\r\n");
        a90_console_printf("video.stream.audio_sync.status_path=%s\r\n", audio_sync->status_path);
        a90_console_printf("video.stream.audio_sync.wait_ms=%u\r\n", audio_sync->wait_ms);
        rc = video_audio_sync_wait_ready(audio_sync);
        if (rc < 0) {
            close(fd);
            return rc;
        }
        started_ns = audio_sync->listen_begin_ns;
    } else {
        a90_console_printf("video.stream.audio_sync.enabled=0\r\n");
        started_ns = video_monotonic_ns();
    }
    for (frame_index = 0; frame_index < limit_frames; ++frame_index) {
        struct video_stream_frame_record_v1 record;
        struct a90_fb *fb;
        uint64_t deadline_ns = started_ns + ((uint64_t)frame_index * interval_ns);
        uint64_t after_present_ns;
        enum a90_cancel_kind cancel;

        rc = video_read_exact_fd(fd, &record, sizeof(record));
        if (rc < 0) {
            break;
        }
        if (record.index != frame_index || record.payload_bytes != manifest->frame_bytes) {
            a90_console_printf("video.stream.error=frame-record-invalid index=%u payload=%u\r\n",
                               record.index, record.payload_bytes);
            rc = -EINVAL;
            break;
        }
        if (a90_kms_begin_frame_no_clear() < 0) {
            rc = negative_errno_or(ENODEV);
            break;
        }
        fb = a90_kms_framebuffer();
        if (fb == NULL || fb->pixels == NULL || fb->size < record.payload_bytes) {
            rc = -EINVAL;
            break;
        }
        rc = video_read_exact_fd(fd, fb->pixels, record.payload_bytes);
        if (rc < 0) {
            break;
        }
        rc = video_wait_until_ns(deadline_ns);
        if (rc < 0) {
            close(fd);
            a90_console_printf("video.stream.presented=%u\r\n", frame_index);
            return rc;
        }
        if (present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP) {
            struct a90_kms_flip_result flip;

            if (a90_kms_present_pageflip("videostream", 1000, &flip) < 0) {
                rc = negative_errno_or(EIO);
                break;
            }
            if (flip.event_received) {
                last_flip = flip;
                ++flip_events;
            }
        } else {
            if (a90_kms_present("videostream", false) < 0) {
                rc = negative_errno_or(EIO);
                break;
            }
        }
        total_bytes += record.payload_bytes;
        after_present_ns = video_monotonic_ns();
        if (after_present_ns > deadline_ns) {
            uint64_t late_ns = after_present_ns - deadline_ns;

            ++late_frames;
            if (late_ns > max_late_ns) {
                max_late_ns = late_ns;
            }
        }
        cancel = a90_console_poll_cancel(0);
        if (cancel != CANCEL_NONE) {
            close(fd);
            a90_console_printf("video.stream.presented=%u\r\n", frame_index + 1);
            return a90_console_cancelled("videostream", cancel);
        }
    }
    finished_ns = video_monotonic_ns();
    close(fd);
    if (rc < 0) {
        return rc;
    }

    {
        uint64_t elapsed_ns = finished_ns > started_ns ? finished_ns - started_ns : 1;
        uint64_t fps_milli = ((uint64_t)limit_frames * 1000000000000ULL) / elapsed_ns;
        uint64_t mbps_milli = (total_bytes * 1000000ULL) / elapsed_ns;

        a90_console_printf("video.stream.presented=%u\r\n", limit_frames);
        a90_console_printf("video.stream.frames_requested=%u\r\n", requested_frames);
        a90_console_printf("video.stream.frames_total=%u\r\n", manifest->frame_count);
        a90_console_printf("video.stream.bytes=%llu\r\n", (unsigned long long)total_bytes);
        a90_console_printf("video.stream.elapsed_ns=%llu\r\n", (unsigned long long)elapsed_ns);
        a90_console_printf("video.stream.fps_milli=%llu\r\n", (unsigned long long)fps_milli);
        a90_console_printf("video.stream.mbps_milli=%llu\r\n", (unsigned long long)mbps_milli);
        a90_console_printf("video.stream.late_frames=%llu\r\n", (unsigned long long)late_frames);
        a90_console_printf("video.stream.max_late_ns=%llu\r\n", (unsigned long long)max_late_ns);
        a90_console_printf("video.stream.present_mode=%s\r\n", video_stream_present_mode_name(present_mode));
        a90_console_printf("video.stream.audio_sync.enabled=%d\r\n",
                           audio_sync != NULL && audio_sync->enabled ? 1 : 0);
        a90_console_printf("video.stream.audio_sync.ready=%d\r\n",
                           audio_sync != NULL && audio_sync->ready ? 1 : 0);
        if (audio_sync != NULL && audio_sync->enabled) {
            a90_console_printf("video.stream.audio_sync.ready_elapsed_ms=%llu\r\n",
                               (unsigned long long)audio_sync->ready_elapsed_ms);
            a90_console_printf("video.stream.audio_sync.anchor_age_ns=%llu\r\n",
                               (unsigned long long)audio_sync->anchor_age_ns);
            a90_console_printf("video.stream.audio_sync.listen_begin_ns=%llu\r\n",
                               (unsigned long long)audio_sync->listen_begin_ns);
            a90_console_printf("video.stream.audio_sync.sample_rate=%u\r\n", audio_sync->sample_rate);
            a90_console_printf("video.stream.audio_sync.frame_bytes=%u\r\n", audio_sync->frame_bytes);
            a90_console_printf("video.stream.audio_sync.total_frames=%u\r\n", audio_sync->total_frames);
        }
        a90_console_printf("video.stream.flip_events=%u\r\n", flip_events);
        a90_console_printf("video.stream.last_sequence=%u\r\n", last_flip.sequence);
        a90_console_printf("video.stream.last_crtc=%u\r\n", last_flip.crtc_id);
        a90_console_printf("video.stream.last_timestamp_us=%llu\r\n",
                           (unsigned long long)last_flip.timestamp_us);
        a90_console_printf("video.stream.width=%u\r\n", manifest->width);
        a90_console_printf("video.stream.height=%u\r\n", manifest->height);
        a90_console_printf("video.stream.stride=%u\r\n", manifest->stride);
        a90_console_printf("video.stream.frame_bytes=%u\r\n", manifest->frame_bytes);
        a90_console_printf("video.stream.pixel_format=xbgr8888\r\n");
        a90_console_printf("video.stream.path=%s\r\n", video_stream_present_path_name(present_mode));
    }
    return 0;
}

static int cmd_video_stream(char **argv, int argc) {
    const char *usage = "usage: video stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--sync-audio-status /cache/a90-audio-play/status.txt] [--sync-wait-ms N]\r\n";
    const char *manifest_path;
    struct video_stream_manifest manifest;
    struct video_audio_sync_state audio_sync;
    char actual_sha256[65];
    uint32_t requested_frames = 0;
    uint32_t sync_wait_ms = VIDEO_STREAM_AUDIO_SYNC_DEFAULT_WAIT_MS;
    enum video_stream_present_mode present_mode = VIDEO_STREAM_PRESENT_SETCRTC;
    bool present_seen = false;
    int index;
    int rc;

    memset(&audio_sync, 0, sizeof(audio_sync));
    if (!(argc >= 5 &&
          strcmp(argv[2], "--manifest") == 0 &&
          strcmp(argv[4], "--video-only") == 0)) {
        a90_console_printf("%s", usage);
        return -EINVAL;
    }
    index = 5;
    while (index < argc) {
        if (strcmp(argv[index], "--frames") == 0) {
            if (requested_frames != 0 ||
                index + 1 >= argc ||
                !parse_u32_arg(argv[index + 1], 1, VIDEO_STREAM_MAX_FRAMES, &requested_frames)) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            index += 2;
            continue;
        }
        if (strcmp(argv[index], "--present") == 0) {
            if (present_seen || index + 1 >= argc) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            present_seen = true;
            if (strcmp(argv[index + 1], "setcrtc") == 0) {
                present_mode = VIDEO_STREAM_PRESENT_SETCRTC;
            } else if (strcmp(argv[index + 1], "pageflip") == 0) {
                present_mode = VIDEO_STREAM_PRESENT_PAGEFLIP;
            } else {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            index += 2;
            continue;
        }
        if (strcmp(argv[index], "--sync-audio-status") == 0) {
            if (audio_sync.enabled || index + 1 >= argc ||
                !video_audio_sync_status_path_allowed(argv[index + 1])) {
                a90_console_printf("%s", usage);
                a90_console_printf("video.stream.audio_sync.error=status-path-not-allowed\r\n");
                return -EINVAL;
            }
            audio_sync.enabled = true;
            snprintf(audio_sync.status_path, sizeof(audio_sync.status_path), "%s", argv[index + 1]);
            index += 2;
            continue;
        }
        if (strcmp(argv[index], "--sync-wait-ms") == 0) {
            if (index + 1 >= argc ||
                !parse_u32_arg(argv[index + 1], 0, 120000, &sync_wait_ms)) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            index += 2;
            continue;
        }
        a90_console_printf("%s", usage);
        return -EINVAL;
    }
    audio_sync.wait_ms = sync_wait_ms;
    manifest_path = argv[3];
    rc = video_parse_manifest(manifest_path, &manifest);
    if (rc < 0) {
        return rc;
    }
    rc = video_stream_verify_hash(&manifest, actual_sha256, sizeof(actual_sha256));
    a90_console_printf("video.stream.expected_sha256=%s\r\n", manifest.sha256);
    a90_console_printf("video.stream.actual_sha256=%s\r\n", rc == 0 ? actual_sha256 : "hash-error");
    a90_console_printf("video.stream.sha256_checked=1\r\n");
    a90_console_printf("video.stream.sha256_match=%d\r\n", rc == 0 ? 1 : 0);
    if (rc < 0) {
        return rc;
    }
    a90_console_printf("video.stream.manifest=%s\r\n", manifest_path);
    a90_console_printf("video.stream.file=%s\r\n", manifest.stream_path);
    a90_console_printf("video.stream.format=%s\r\n", manifest.format);
    a90_console_printf("video.stream.fps=%u/%u\r\n", manifest.fps_num, manifest.fps_den);
    a90_console_printf("video.stream.requested_present=%s\r\n", video_stream_present_mode_name(present_mode));
    a90_console_printf("video.stream.requested_audio_sync=%d\r\n", audio_sync.enabled ? 1 : 0);
    if (audio_sync.enabled) {
        a90_console_printf("video.stream.requested_audio_sync_status=%s\r\n", audio_sync.status_path);
        a90_console_printf("video.stream.requested_audio_sync_wait_ms=%u\r\n", audio_sync.wait_ms);
    }
    return video_stream_play(&manifest, requested_frames, present_mode, &audio_sync);
}


static int handle_video(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";

    if (strcmp(subcommand, "status") == 0) {
        if (argc != 1 && argc != 2) {
            a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]|flipprobe [frames]|stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--sync-audio-status PATH]]\r\n");
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
    if (strcmp(subcommand, "flipprobe") == 0) {
        return cmd_video_flipprobe(argv, argc);
    }
    if (strcmp(subcommand, "stream") == 0) {
        return cmd_video_stream(argv, argc);
    }

    a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]|flipprobe [frames]|stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--sync-audio-status PATH]]\r\n");
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
