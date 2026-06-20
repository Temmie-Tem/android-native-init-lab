/* Included by the current native-init translation unit. Do not compile standalone. */

#include "a90_badapple_beat_table.h"

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
    a90_console_printf("video.status.version=9\r\n");
    a90_console_printf("video.status.path=kms-dumb-buffer\r\n");
    a90_console_printf("video.status.display_owner=1\r\n");
    a90_console_printf("video.status.player_hud_fastpath=1\r\n");
    a90_console_printf("video.status.player_hud_incremental_panel=1\r\n");
    a90_console_printf("video.status.nyan_pal8_rle=1\r\n");
    a90_console_printf("video.status.doom_stub=1\r\n");
    a90_console_printf("video.status.doom_input=not-proven\r\n");
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
    a90_console_printf("video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale|nyan] play [--trust-cache]\r\n");
    a90_console_printf("video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom] [status|verify|play] [--trust-cache]\r\n");
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
#define VIDEO_STREAM_MAX_FRAMES 7200U
#define VIDEO_STREAM_MAX_FRAME_BYTES (64U * 1024U * 1024U)
#define VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE 1U
#define VIDEO_STREAM_PIXEL_FORMAT_GRAY8 2U
#define VIDEO_STREAM_PIXEL_FORMAT_MONO1 3U
#define VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE 4U
#define VIDEO_STREAM_VERSION_A90VSTR1 1U
#define VIDEO_STREAM_VERSION_A90VSTR2 2U
#define VIDEO_STREAM_PAL8_RAW_MODE 1U
#define VIDEO_STREAM_PAL8_RLE_MODE 2U
#define VIDEO_STREAM_PAL8_MAX_COLORS 256U
#define VIDEO_STREAM_AUDIO_STATUS_PATH "/cache/a90-audio-play/status.txt"
#define VIDEO_STREAM_AUDIO_SYNC_DEFAULT_WAIT_MS 90000U
#define VIDEO_STREAM_AUDIO_SYNC_POLL_MS 20U
#define VIDEO_STREAM_AUDIO_SYNC_MAX_START_OFFSET_MS 5000U
#define VIDEO_STREAM_CACHE_ROOT "/mnt/sdext/a90/runtime/video/cache"
#define VIDEO_STREAM_CACHE_DIR_PREFIX "sha256-"
#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME "badapple-scale"
#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_ASSET_ID "v2874-synthetic-mono1-checker-6501f"
#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_SHA256 "878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890"
#define VIDEO_CACHE_PRESET_BADAPPLE_NAME "badapple"
#define VIDEO_CACHE_PRESET_BADAPPLE_ASSET_ID "badapple-480x360-full-v2903"
#define VIDEO_CACHE_PRESET_BADAPPLE_SHA256 "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0"
#define VIDEO_CACHE_PRESET_NYAN_NAME "nyan"
#define VIDEO_CACHE_PRESET_NYAN_ASSET_ID "nyancat-v2973-pal8-rle-preview"
#define VIDEO_CACHE_PRESET_NYAN_SHA256 "9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573"
#define VIDEO_PLAYER_HUD_SCALE 2U

enum video_stream_present_mode {
    VIDEO_STREAM_PRESENT_SETCRTC = 0,
    VIDEO_STREAM_PRESENT_PAGEFLIP = 1,
};

enum video_stream_layout {
    VIDEO_STREAM_LAYOUT_FULL = 0,
    VIDEO_STREAM_LAYOUT_PLAYER_HUD = 1,
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
    uint32_t pixel_format;
    uint32_t stream_version;
    uint32_t palette_count;
    uint32_t max_payload_bytes;
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

struct __attribute__((packed)) video_stream_header_v2 {
    char magic[8];
    uint32_t version;
    uint32_t width;
    uint32_t height;
    uint32_t fps_num;
    uint32_t fps_den;
    uint32_t frame_count;
    uint32_t palette_count;
    uint32_t max_payload_bytes;
    uint32_t flags;
    uint8_t reserved[32];
};

struct __attribute__((packed)) video_stream_frame_record_v2 {
    uint32_t index;
    uint32_t mode;
    uint32_t payload_bytes;
    uint64_t pts_ns;
};

struct video_audio_sync_state {
    bool enabled;
    bool ready;
    char status_path[PATH_MAX];
    uint32_t wait_ms;
    uint32_t start_offset_ms;
    uint32_t sample_rate;
    uint32_t frame_bytes;
    uint32_t total_frames;
    uint64_t expected_duration_ns;
    uint64_t listen_begin_ns;
    uint64_t corrected_anchor_ns;
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
    bool is_v2_pal8 = false;
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
        !video_json_extract_u32(video_object, "fps_num", 1, 240, &manifest->fps_num) ||
        !video_json_extract_u32(video_object, "fps_den", 1, 1000000, &manifest->fps_den) ||
        !video_json_extract_u32(video_object, "frame_count", 1, VIDEO_STREAM_MAX_FRAMES, &manifest->frame_count)) {
        free(text);
        a90_console_printf("video.stream.error=manifest-field-invalid\r\n");
        return -EINVAL;
    }
    free(text);

    if (!video_text_is_sha256(manifest->sha256) ||
        !video_join_manifest_path(manifest_path, manifest->video_path,
                                  manifest->stream_path, sizeof(manifest->stream_path))) {
        a90_console_printf("video.stream.error=manifest-policy-reject\r\n");
        return -EINVAL;
    }
    if (strcmp(manifest->format, "xbgr8888-raw-stride") == 0) {
        manifest->pixel_format = VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE;
    } else if (strcmp(manifest->format, "gray8") == 0) {
        manifest->pixel_format = VIDEO_STREAM_PIXEL_FORMAT_GRAY8;
    } else if (strcmp(manifest->format, "mono1") == 0) {
        manifest->pixel_format = VIDEO_STREAM_PIXEL_FORMAT_MONO1;
    } else if (strcmp(manifest->format, "pal8-rle") == 0) {
        manifest->pixel_format = VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE;
        is_v2_pal8 = true;
    } else {
        a90_console_printf("video.stream.error=manifest-format-unsupported\r\n");
        return -EINVAL;
    }
    if (is_v2_pal8) {
        manifest->stream_version = VIDEO_STREAM_VERSION_A90VSTR2;
        if (!video_json_extract_u32(video_object,
                                    "stream_version",
                                    VIDEO_STREAM_VERSION_A90VSTR2,
                                    VIDEO_STREAM_VERSION_A90VSTR2,
                                    &manifest->stream_version) ||
            !video_json_extract_u32(video_object, "palette_count", 1, VIDEO_STREAM_PAL8_MAX_COLORS,
                                    &manifest->palette_count) ||
            !video_json_extract_u32(video_object, "max_payload_bytes", 1, VIDEO_STREAM_MAX_FRAME_BYTES,
                                    &manifest->max_payload_bytes)) {
            a90_console_printf("video.stream.error=manifest-field-invalid\r\n");
            return -EINVAL;
        }
        manifest->stride = manifest->width;
        manifest->visible_row_bytes = manifest->width;
        manifest->frame_bytes = manifest->max_payload_bytes;
        return 0;
    }
    manifest->stream_version = VIDEO_STREAM_VERSION_A90VSTR1;
    if (!video_json_extract_u32(video_object, "stride", 1, VIDEO_STREAM_MAX_FRAME_BYTES, &manifest->stride) ||
        !video_json_extract_u32(video_object, "frame_bytes", 1, VIDEO_STREAM_MAX_FRAME_BYTES, &manifest->frame_bytes) ||
        !video_json_extract_u32(video_object, "visible_row_bytes", 1, VIDEO_STREAM_MAX_FRAME_BYTES,
                                &manifest->visible_row_bytes)) {
        a90_console_printf("video.stream.error=manifest-field-invalid\r\n");
        return -EINVAL;
    }
    expected_frame_bytes = (uint64_t)manifest->stride * manifest->height;
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE &&
        ((uint64_t)manifest->width * 4ULL != manifest->visible_row_bytes ||
         manifest->stride < manifest->visible_row_bytes ||
         expected_frame_bytes != manifest->frame_bytes)) {
        a90_console_printf("video.stream.error=manifest-geometry-invalid\r\n");
        return -EINVAL;
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_GRAY8 &&
        ((uint64_t)manifest->width != manifest->visible_row_bytes ||
         manifest->stride < manifest->visible_row_bytes ||
         expected_frame_bytes != manifest->frame_bytes)) {
        a90_console_printf("video.stream.error=manifest-geometry-invalid\r\n");
        return -EINVAL;
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1 &&
        ((((uint64_t)manifest->width + 7ULL) / 8ULL) != manifest->visible_row_bytes ||
         manifest->stride < manifest->visible_row_bytes ||
         expected_frame_bytes != manifest->frame_bytes)) {
        a90_console_printf("video.stream.error=manifest-geometry-invalid\r\n");
        return -EINVAL;
    }
    if (expected_frame_bytes != manifest->frame_bytes) {
        a90_console_printf("video.stream.error=manifest-frame-bytes-invalid\r\n");
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

static int video_skip_exact_fd(int fd, size_t bytes) {
    uint8_t discard[4096];
    size_t done = 0;

    while (done < bytes) {
        size_t chunk = bytes - done;
        int rc;

        if (chunk > sizeof(discard)) {
            chunk = sizeof(discard);
        }
        rc = video_read_exact_fd(fd, discard, chunk);
        if (rc < 0) {
            return rc;
        }
        done += chunk;
    }
    return 0;
}

static const char *video_stream_pixel_format_name(uint32_t pixel_format) {
    if (pixel_format == VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE) {
        return "pal8-rle";
    }
    if (pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1) {
        return "mono1";
    }
    if (pixel_format == VIDEO_STREAM_PIXEL_FORMAT_GRAY8) {
        return "gray8";
    }
    return "xbgr8888";
}

static int video_expand_gray8_frame(struct a90_fb *fb,
                                    const uint8_t *source,
                                    const struct video_stream_manifest *manifest) {
    uint32_t y;

    if (fb == NULL || fb->pixels == NULL || source == NULL || manifest == NULL ||
        fb->width != manifest->width || fb->height != manifest->height ||
        fb->stride < (uint64_t)manifest->width * 4ULL ||
        manifest->stride < manifest->width) {
        return -EINVAL;
    }
    for (y = 0; y < manifest->height; ++y) {
        const uint8_t *src = source + ((size_t)y * manifest->stride);
        uint32_t *dst = (uint32_t *)((char *)fb->pixels + ((size_t)y * fb->stride));
        uint32_t x;

        for (x = 0; x < manifest->width; ++x) {
            uint32_t level = src[x];

            dst[x] = (level << 16) | (level << 8) | level;
        }
    }
    return 0;
}

static int video_expand_mono1_frame(struct a90_fb *fb,
                                    const uint8_t *source,
                                    const struct video_stream_manifest *manifest) {
    uint32_t y;

    if (fb == NULL || fb->pixels == NULL || source == NULL || manifest == NULL ||
        fb->width != manifest->width || fb->height != manifest->height ||
        fb->stride < (uint64_t)manifest->width * 4ULL ||
        manifest->stride < ((manifest->width + 7U) / 8U)) {
        return -EINVAL;
    }
    for (y = 0; y < manifest->height; ++y) {
        const uint8_t *src = source + ((size_t)y * manifest->stride);
        uint32_t *dst = (uint32_t *)((char *)fb->pixels + ((size_t)y * fb->stride));
        uint32_t x;

        for (x = 0; x < manifest->width; ++x) {
            uint8_t byte = src[x / 8U];
            uint32_t bit = (byte >> (7U - (x % 8U))) & 1U;

            dst[x] = bit ? 0x00FFFFFFU : 0x00000000U;
        }
    }
    return 0;
}

static int video_expand_mono1_frame_scaled(struct a90_fb *fb,
                                           const uint8_t *source,
                                           const struct video_stream_manifest *manifest,
                                           uint32_t dst_x,
                                           uint32_t dst_y,
                                           uint32_t scale) {
    uint32_t y;
    uint32_t scaled_width;
    uint32_t scaled_height;
    size_t scaled_row_bytes;

    if (fb == NULL || fb->pixels == NULL || source == NULL || manifest == NULL ||
        scale == 0 || fb->stride < (uint64_t)fb->width * 4ULL ||
        manifest->stride < ((manifest->width + 7U) / 8U)) {
        return -EINVAL;
    }
    scaled_width = manifest->width * scale;
    scaled_height = manifest->height * scale;
    if (scaled_width / scale != manifest->width ||
        scaled_height / scale != manifest->height ||
        dst_x > fb->width || dst_y > fb->height ||
        scaled_width > fb->width - dst_x ||
        scaled_height > fb->height - dst_y) {
        return -EINVAL;
    }
    scaled_row_bytes = (size_t)scaled_width * sizeof(uint32_t);
    for (y = 0; y < manifest->height; ++y) {
        const uint8_t *src = source + ((size_t)y * manifest->stride);
        uint32_t *dst0 = (uint32_t *)((char *)fb->pixels +
                         ((size_t)(dst_y + y * scale) * fb->stride)) + dst_x;
        uint32_t x;
        uint32_t yy;

        for (x = 0; x < manifest->width; ++x) {
            uint8_t byte = src[x / 8U];
            uint32_t bit = (byte >> (7U - (x % 8U))) & 1U;
            uint32_t color = bit ? 0x00FFFFFFU : 0x00000000U;
            uint32_t xx;

            for (xx = 0; xx < scale; ++xx) {
                dst0[x * scale + xx] = color;
            }
        }
        for (yy = 1; yy < scale; ++yy) {
            void *dst = (char *)fb->pixels +
                        ((size_t)(dst_y + y * scale + yy) * fb->stride) +
                        ((size_t)dst_x * sizeof(uint32_t));

            memcpy(dst, dst0, scaled_row_bytes);
        }
    }
    return 0;
}

static int video_expand_pal8_indices_scaled(struct a90_fb *fb,
                                            const uint8_t *indices,
                                            const struct video_stream_manifest *manifest,
                                            const uint32_t *palette,
                                            uint32_t palette_count,
                                            uint32_t dst_x,
                                            uint32_t dst_y,
                                            uint32_t scale) {
    uint32_t y;
    uint32_t scaled_width;
    uint32_t scaled_height;
    size_t scaled_row_bytes;

    if (fb == NULL || fb->pixels == NULL || indices == NULL || manifest == NULL ||
        palette == NULL || palette_count == 0 || palette_count > VIDEO_STREAM_PAL8_MAX_COLORS ||
        scale == 0 || fb->stride < (uint64_t)fb->width * 4ULL) {
        return -EINVAL;
    }
    scaled_width = manifest->width * scale;
    scaled_height = manifest->height * scale;
    if (scaled_width / scale != manifest->width ||
        scaled_height / scale != manifest->height ||
        dst_x > fb->width || dst_y > fb->height ||
        scaled_width > fb->width - dst_x ||
        scaled_height > fb->height - dst_y) {
        return -EINVAL;
    }
    scaled_row_bytes = (size_t)scaled_width * sizeof(uint32_t);
    for (y = 0; y < manifest->height; ++y) {
        const uint8_t *src = indices + ((size_t)y * manifest->width);
        uint32_t *dst0 = (uint32_t *)((char *)fb->pixels +
                         ((size_t)(dst_y + y * scale) * fb->stride)) + dst_x;
        uint32_t x;
        uint32_t yy;

        for (x = 0; x < manifest->width; ++x) {
            uint8_t palette_index = src[x];
            uint32_t color;
            uint32_t xx;

            if (palette_index >= palette_count) {
                return -EINVAL;
            }
            color = palette[palette_index];
            for (xx = 0; xx < scale; ++xx) {
                dst0[x * scale + xx] = color;
            }
        }
        for (yy = 1; yy < scale; ++yy) {
            void *dst = (char *)fb->pixels +
                        ((size_t)(dst_y + y * scale + yy) * fb->stride) +
                        ((size_t)dst_x * sizeof(uint32_t));

            memcpy(dst, dst0, scaled_row_bytes);
        }
    }
    return 0;
}

static int video_decode_pal8_rle_frame(uint8_t *indices,
                                       size_t indices_size,
                                       const uint8_t *payload,
                                       uint32_t payload_bytes,
                                       const struct video_stream_manifest *manifest) {
    uint32_t source_offset = 0;
    uint32_t y;

    if (indices == NULL || payload == NULL || manifest == NULL ||
        indices_size < (uint64_t)manifest->width * manifest->height) {
        return -EINVAL;
    }
    for (y = 0; y < manifest->height; ++y) {
        uint32_t row_pixels = 0;
        uint32_t row_base = y * manifest->width;

        while (row_pixels < manifest->width) {
            uint8_t run_length;
            uint8_t palette_index;

            if (source_offset + 2U > payload_bytes) {
                return -EINVAL;
            }
            run_length = payload[source_offset++];
            palette_index = payload[source_offset++];
            if (run_length == 0 || row_pixels + run_length > manifest->width) {
                return -EINVAL;
            }
            memset(indices + row_base + row_pixels, palette_index, run_length);
            row_pixels += run_length;
        }
    }
    return source_offset == payload_bytes ? 0 : -EINVAL;
}

static int video_render_pal8_player_hud_region(struct a90_fb *fb,
                                               uint8_t *indices,
                                               size_t indices_size,
                                               const uint8_t *payload,
                                               uint32_t payload_bytes,
                                               uint32_t mode,
                                               const struct video_stream_manifest *manifest,
                                               const uint32_t *palette,
                                               uint32_t palette_count,
                                               uint32_t dst_x,
                                               uint32_t dst_y,
                                               uint32_t scale) {
    uint64_t required_indices;

    if (indices == NULL || payload == NULL || manifest == NULL) {
        return -EINVAL;
    }
    required_indices = (uint64_t)manifest->width * manifest->height;
    if (required_indices == 0 || required_indices > indices_size) {
        return -EINVAL;
    }
    if (mode == VIDEO_STREAM_PAL8_RAW_MODE) {
        if (payload_bytes != required_indices) {
            return -EINVAL;
        }
        memcpy(indices, payload, (size_t)required_indices);
    } else if (mode == VIDEO_STREAM_PAL8_RLE_MODE) {
        int rc = video_decode_pal8_rle_frame(indices,
                                             indices_size,
                                             payload,
                                             payload_bytes,
                                             manifest);

        if (rc < 0) {
            return rc;
        }
    } else {
        return -EINVAL;
    }
    return video_expand_pal8_indices_scaled(fb,
                                            indices,
                                            manifest,
                                            palette,
                                            palette_count,
                                            dst_x,
                                            dst_y,
                                            scale);
}

static void video_format_time_mmss(uint64_t ms, char *out, size_t out_size) {
    uint64_t seconds;

    if (out == NULL || out_size == 0) {
        return;
    }
    seconds = ms / 1000ULL;
    snprintf(out, out_size, "%02llu:%02llu",
             (unsigned long long)(seconds / 60ULL),
             (unsigned long long)(seconds % 60ULL));
}

static uint32_t video_sync_lamp_color(int64_t delta_ms, bool valid) {
    int64_t abs_delta = delta_ms < 0 ? -delta_ms : delta_ms;

    if (!valid) {
        return 0x777777;
    }
    if (abs_delta < 33) {
        return 0x44EE66;
    }
    if (abs_delta < 66) {
        return 0xFFCC33;
    }
    return 0xFF4444;
}

static bool video_badapple_beat_flash_active(uint64_t audio_ms, uint32_t *nearest_ms) {
    uint32_t best_delta = UINT32_MAX;
    uint32_t best_ms = 0;
    uint32_t index;

    for (index = 0; index < A90_BADAPPLE_BEAT_COUNT; ++index) {
        uint32_t beat_ms = A90_BADAPPLE_BEAT_MS[index];
        uint32_t delta = audio_ms > beat_ms ?
                         (uint32_t)(audio_ms - beat_ms) :
                         (uint32_t)(beat_ms - audio_ms);

        if (delta < best_delta) {
            best_delta = delta;
            best_ms = beat_ms;
        }
        if (beat_ms > audio_ms && delta > A90_BADAPPLE_BEAT_WINDOW_MS) {
            break;
        }
    }
    if (nearest_ms != NULL) {
        *nearest_ms = best_ms;
    }
    return best_delta <= A90_BADAPPLE_BEAT_WINDOW_MS;
}

static int video_render_player_hud(struct a90_fb *fb,
                                   const uint8_t *frame_buffer,
                                   const struct video_stream_manifest *manifest,
                                   uint32_t payload_bytes,
                                   uint32_t frame_mode,
                                   uint8_t *decode_buffer,
                                   size_t decode_buffer_size,
                                   const uint32_t *palette,
                                   uint32_t palette_count,
                                   uint32_t frame_index,
                                   uint32_t total_frames,
                                   uint64_t frame_deadline_ns,
                                   const struct video_audio_sync_state *audio_sync) {
    static struct a90_metrics_snapshot metrics;
    static struct a90_hud_storage_status storage;
    static uint32_t metrics_frame = UINT32_MAX;
    static uint32_t storage_frame = UINT32_MAX;
    static uint32_t render_session_frames;
    static uint32_t previous_frame_index = UINT32_MAX;
    uint32_t scale = 2;
    uint32_t video_w;
    uint32_t video_h;
    uint32_t video_x;
    uint32_t video_y = 48;
    uint32_t panel_y;
    uint32_t progress_w;
    uint32_t progress_fill;
    uint64_t pos_ms;
    uint64_t total_ms;
    uint64_t audio_ms = 0;
    int64_t delta_ms = 0;
    bool delta_valid = false;
    bool beat_flash_active = false;
    uint32_t nearest_beat_ms = 0;
    bool is_pal8 = manifest != NULL && manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE;
    bool beat_flash_enabled = manifest != NULL && manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1;
    uint32_t lamp_color;
    uint32_t border_color;
    char pos[16];
    char total[16];
    char line[160];
    bool full_repaint;
    bool metrics_repaint = false;
    bool storage_repaint = false;

    if (fb == NULL || frame_buffer == NULL || manifest == NULL ||
        (manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 &&
         manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE) ||
        manifest->width == 0 || manifest->height == 0) {
        return -EINVAL;
    }
    video_w = manifest->width * VIDEO_PLAYER_HUD_SCALE;
    video_h = manifest->height * VIDEO_PLAYER_HUD_SCALE;
    if (video_w / VIDEO_PLAYER_HUD_SCALE != manifest->width ||
        video_h / VIDEO_PLAYER_HUD_SCALE != manifest->height ||
        video_w > fb->width || video_h + video_y + 260U > fb->height) {
        return -EINVAL;
    }
    if (metrics_frame == UINT32_MAX || frame_index < metrics_frame ||
        frame_index - metrics_frame >= 15U) {
        a90_metrics_read_snapshot(&metrics);
        metrics_frame = frame_index;
        metrics_repaint = true;
    }
    if (storage_frame == UINT32_MAX || frame_index < storage_frame ||
        frame_index - storage_frame >= 60U) {
        storage = current_hud_storage_status();
        storage_frame = frame_index;
        storage_repaint = true;
    }
    if (previous_frame_index == UINT32_MAX || frame_index <= previous_frame_index) {
        render_session_frames = 0;
    }
    previous_frame_index = frame_index;
    full_repaint = render_session_frames < 2U || (frame_index % 60U) == 0U;
    video_x = (fb->width - video_w) / 2U;
    panel_y = video_y + video_h + 40U;
    pos_ms = ((uint64_t)frame_index * 1000ULL * (uint64_t)manifest->fps_den) /
             (uint64_t)manifest->fps_num;
    total_ms = ((uint64_t)total_frames * 1000ULL * (uint64_t)manifest->fps_den) /
               (uint64_t)manifest->fps_num;
    if (audio_sync != NULL && audio_sync->ready && audio_sync->corrected_anchor_ns > 0 &&
        frame_deadline_ns >= audio_sync->corrected_anchor_ns) {
        audio_ms = (frame_deadline_ns - audio_sync->corrected_anchor_ns) / 1000000ULL;
        delta_ms = (int64_t)audio_ms - (int64_t)pos_ms;
        delta_valid = true;
        if (beat_flash_enabled) {
            beat_flash_active = video_badapple_beat_flash_active(audio_ms, &nearest_beat_ms);
        }
    }
    lamp_color = video_sync_lamp_color(delta_ms, delta_valid);
    border_color = beat_flash_active ? 0xFFFFFF : lamp_color;

    if (full_repaint) {
        a90_draw_rect(fb, 0, 0, fb->width, fb->height, 0x05070C);
    } else {
        uint32_t video_region_y = video_y > 8U ? video_y - 8U : 0U;
        uint32_t video_region_h = video_h + 16U;

        (void)video_region_y;
        (void)video_region_h;
    }
    ++render_session_frames;
    if (full_repaint) {
        a90_draw_text(fb, 48, 16, is_pal8 ? "DEMO / NYAN CAT" : "DEMO / BAD APPLE", 0x66DDFF, scale);
        a90_draw_text(fb, fb->width - 300U, 16, "A90 PLAYER HUD", 0xBBBBBB, scale);
    }
    a90_draw_rect_outline(fb, video_x - 4U, video_y - 4U, video_w + 8U, video_h + 8U, 4U, border_color);
    if (is_pal8) {
        if (video_render_pal8_player_hud_region(fb,
                                                decode_buffer,
                                                decode_buffer_size,
                                                frame_buffer,
                                                payload_bytes,
                                                frame_mode,
                                                manifest,
                                                palette,
                                                palette_count,
                                                video_x,
                                                video_y,
                                                VIDEO_PLAYER_HUD_SCALE) < 0) {
            return -EINVAL;
        }
    } else {
        if (payload_bytes != manifest->frame_bytes ||
            video_expand_mono1_frame_scaled(fb,
                                            frame_buffer,
                                            manifest,
                                            video_x,
                                            video_y,
                                            VIDEO_PLAYER_HUD_SCALE) < 0) {
            return -EINVAL;
        }
    }

    progress_w = fb->width > 120U ? fb->width - 120U : fb->width;
    progress_fill = total_frames > 0 ?
                    (uint32_t)(((uint64_t)progress_w * (uint64_t)(frame_index + 1U)) /
                               (uint64_t)total_frames) : 0;
    video_format_time_mmss(pos_ms, pos, sizeof(pos));
    video_format_time_mmss(total_ms, total, sizeof(total));
    if (full_repaint) {
        a90_draw_rect(fb, 48, panel_y, fb->width - 96U, 240U, 0x101820);
        a90_draw_rect_outline(fb, 48, panel_y, fb->width - 96U, 240U, 2U, 0x304050);
    } else {
        a90_draw_rect(fb, 72, panel_y + 24U, fb->width - 144U, 24U, 0x101820);
        a90_draw_rect(fb, 72, panel_y + 92U, fb->width - 144U, 24U, 0x101820);
        a90_draw_rect(fb, 168, panel_y + 124U, fb->width - 240U, 28U, 0x101820);
        a90_draw_rect(fb, 72, panel_y + 200U, fb->width - 144U, 24U, 0x101820);
    }
    snprintf(line, sizeof(line), "FRAME %u/%u  POS %s/%s", frame_index + 1U, total_frames, pos, total);
    a90_draw_text(fb, 72, panel_y + 24U, line, 0xFFFFFF, scale);
    a90_draw_rect(fb, 72, panel_y + 60U, progress_w, 16U, 0x303030);
    a90_draw_rect(fb, 72, panel_y + 60U, progress_fill, 16U, 0x66DDFF);
    a90_draw_rect_outline(fb, 72, panel_y + 60U, progress_w, 16U, 1U, 0xAAAAAA);
    snprintf(line, sizeof(line), "AUDIO %s  A-V %+lldms  LAMP %s",
             delta_valid ? "SYNC" : "WAIT",
             (long long)delta_ms,
             delta_valid ? (lamp_color == 0x44EE66 ? "GREEN" :
                            (lamp_color == 0xFFCC33 ? "YELLOW" : "RED")) : "GRAY");
    a90_draw_text(fb, 72, panel_y + 92U, line, lamp_color, scale);
    a90_draw_rect(fb, 72, panel_y + 124U, 72U, 28U, lamp_color);
    snprintf(line, sizeof(line), "CPU %s %s  GPU %s %s  LOAD %s  MEM %s",
             metrics.cpu_temp,
             metrics.cpu_usage,
             metrics.gpu_temp,
             metrics.gpu_usage,
             metrics.loadavg,
             metrics.memory);
    if (full_repaint || metrics_repaint) {
        a90_draw_text_fit(fb, 168, panel_y + 124U, line, 0xCCCCCC, scale, fb->width - 220U);
    }
    if (full_repaint || storage_repaint) {
        a90_draw_rect(fb, 72, panel_y + 164U, fb->width - 144U, 24U, 0x101820);
        snprintf(line, sizeof(line), "STORAGE %s %.48s  READONLY TELEMETRY /proc+/sys",
                 storage.backend != NULL ? storage.backend : "?",
                 storage.root != NULL ? storage.root : "?");
        a90_draw_text_fit(fb, 72, panel_y + 164U, line, 0xAAAAAA, scale, fb->width - 144U);
    }
    snprintf(line, sizeof(line), "BEAT FLASH %s  audio-clock onsets=%u nearest=%ums",
             beat_flash_enabled ? (beat_flash_active ? "PULSE" : (delta_valid ? "armed" : "waiting")) : "off",
             beat_flash_enabled ? A90_BADAPPLE_BEAT_COUNT : 0,
             nearest_beat_ms);
    a90_draw_text(fb, 72, panel_y + 200U, line, border_color, scale);
    return 0;
}

static int video_read_frame_payload(int fd,
                                    struct a90_fb *fb,
                                    uint8_t *frame_buffer,
                                    const struct video_stream_manifest *manifest,
                                    uint32_t payload_bytes) {
    if (manifest == NULL || fb == NULL || payload_bytes != manifest->frame_bytes) {
        return -EINVAL;
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE) {
        if (fb->pixels == NULL || fb->size < payload_bytes) {
            return -EINVAL;
        }
        return video_read_exact_fd(fd, fb->pixels, payload_bytes);
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_GRAY8) {
        int rc;

        if (frame_buffer == NULL) {
            return -EINVAL;
        }
        rc = video_read_exact_fd(fd, frame_buffer, payload_bytes);
        if (rc < 0) {
            return rc;
        }
        return video_expand_gray8_frame(fb, frame_buffer, manifest);
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1) {
        int rc;

        if (frame_buffer == NULL) {
            return -EINVAL;
        }
        rc = video_read_exact_fd(fd, frame_buffer, payload_bytes);
        if (rc < 0) {
            return rc;
        }
        return video_expand_mono1_frame(fb, frame_buffer, manifest);
    }
    return -EINVAL;
}

static int video_validate_stream_header(const struct video_stream_manifest *manifest,
                                        const struct video_stream_header_v1 *header) {
    if (memcmp(header->magic, "A90VSTR1", 8) != 0 ||
        header->version != 1 ||
        header->pixel_format != manifest->pixel_format ||
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

static int video_validate_stream_header_v2(const struct video_stream_manifest *manifest,
                                           const struct video_stream_header_v2 *header) {
    if (manifest == NULL || header == NULL ||
        memcmp(header->magic, "A90VSTR2", 8) != 0 ||
        header->version != VIDEO_STREAM_VERSION_A90VSTR2 ||
        manifest->stream_version != VIDEO_STREAM_VERSION_A90VSTR2 ||
        manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE ||
        header->width != manifest->width ||
        header->height != manifest->height ||
        header->fps_num != manifest->fps_num ||
        header->fps_den != manifest->fps_den ||
        header->frame_count != manifest->frame_count ||
        header->palette_count != manifest->palette_count ||
        header->max_payload_bytes != manifest->max_payload_bytes ||
        header->flags != 0 ||
        header->palette_count == 0 ||
        header->palette_count > VIDEO_STREAM_PAL8_MAX_COLORS ||
        header->max_payload_bytes == 0 ||
        header->max_payload_bytes > VIDEO_STREAM_MAX_FRAME_BYTES) {
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

static bool video_cache_manifest_path_for_sha(const char *sha256, char *out, size_t out_size) {
    if (!video_text_is_sha256(sha256) || out == NULL || out_size == 0) {
        return false;
    }
    return snprintf(out,
                    out_size,
                    "%s/%s%s/manifest.json",
                    VIDEO_STREAM_CACHE_ROOT,
                    VIDEO_STREAM_CACHE_DIR_PREFIX,
                    sha256) < (int)out_size;
}

static uint64_t video_stream_expected_total_bytes(const struct video_stream_manifest *manifest) {
    if (manifest == NULL) {
        return 0;
    }
    if (manifest->stream_version == VIDEO_STREAM_VERSION_A90VSTR2) {
        return 0;
    }
    return (uint64_t)sizeof(struct video_stream_header_v1) +
           ((uint64_t)manifest->frame_count *
            ((uint64_t)sizeof(struct video_stream_frame_record_v1) +
             (uint64_t)manifest->frame_bytes));
}

static int video_cache_load_manifest(const char *sha256,
                                     char *manifest_path,
                                     size_t manifest_path_size,
                                     struct video_stream_manifest *manifest) {
    int rc;

    if (!video_cache_manifest_path_for_sha(sha256, manifest_path, manifest_path_size)) {
        a90_console_printf("video.cache.error=invalid-sha256\r\n");
        return -EINVAL;
    }
    rc = video_parse_manifest(manifest_path, manifest);
    if (rc < 0) {
        a90_console_printf("video.cache.error=manifest-invalid rc=%d\r\n", rc);
        return rc;
    }
    if (!video_sha256_equal_fold(manifest->sha256, sha256)) {
        a90_console_printf("video.cache.expected_sha256=%s\r\n", sha256);
        a90_console_printf("video.cache.manifest_sha256=%s\r\n", manifest->sha256);
        a90_console_printf("video.cache.error=manifest-sha-mismatch\r\n");
        return -EINVAL;
    }
    return 0;
}

static int video_cache_stat_stream(const struct video_stream_manifest *manifest,
                                   bool *exists_out,
                                   uint64_t *size_out,
                                   bool *size_match_out) {
    struct stat st;
    uint64_t expected;

    if (exists_out != NULL) {
        *exists_out = false;
    }
    if (size_out != NULL) {
        *size_out = 0;
    }
    if (size_match_out != NULL) {
        *size_match_out = false;
    }
    if (manifest == NULL || stat(manifest->stream_path, &st) < 0 || !S_ISREG(st.st_mode)) {
        return negative_errno_or(ENOENT);
    }
    expected = video_stream_expected_total_bytes(manifest);
    if (exists_out != NULL) {
        *exists_out = true;
    }
    if (size_out != NULL) {
        *size_out = st.st_size > 0 ? (uint64_t)st.st_size : 0;
    }
    if (size_match_out != NULL) {
        if (manifest->stream_version == VIDEO_STREAM_VERSION_A90VSTR2) {
            *size_match_out = st.st_size > 0;
        } else {
            *size_match_out = st.st_size >= 0 && (uint64_t)st.st_size == expected;
        }
    }
    return 0;
}

static void video_cache_print_status(const char *sha256,
                                     const char *manifest_path,
                                     const struct video_stream_manifest *manifest) {
    bool stream_exists = false;
    bool stream_size_match = false;
    uint64_t stream_size = 0;
    uint64_t expected_size = video_stream_expected_total_bytes(manifest);

    (void)video_cache_stat_stream(manifest, &stream_exists, &stream_size, &stream_size_match);
    a90_console_printf("video.cache.version=1\r\n");
    a90_console_printf("video.cache.root=%s\r\n", VIDEO_STREAM_CACHE_ROOT);
    a90_console_printf("video.cache.sha256=%s\r\n", sha256);
    a90_console_printf("video.cache.manifest=%s\r\n", manifest_path);
    a90_console_printf("video.cache.stream=%s\r\n", manifest->stream_path);
    a90_console_printf("video.cache.manifest_ok=1\r\n");
    a90_console_printf("video.cache.stream_exists=%d\r\n", stream_exists ? 1 : 0);
    a90_console_printf("video.cache.stream_size=%llu\r\n", (unsigned long long)stream_size);
    a90_console_printf("video.cache.stream_expected_size=%llu\r\n", (unsigned long long)expected_size);
    a90_console_printf("video.cache.stream_size_match=%d\r\n", stream_size_match ? 1 : 0);
    a90_console_printf("video.cache.format=%s\r\n", manifest->format);
    a90_console_printf("video.cache.frames=%u\r\n", manifest->frame_count);
    a90_console_printf("video.cache.fps=%u/%u\r\n", manifest->fps_num, manifest->fps_den);
    a90_console_printf("video.cache.size=%ux%u\r\n", manifest->width, manifest->height);
    a90_console_printf("video.cache.stride=%u\r\n", manifest->stride);
    a90_console_printf("video.cache.frame_bytes=%u\r\n", manifest->frame_bytes);
}

static int video_cache_verify_hash(const struct video_stream_manifest *manifest,
                                   char *actual_out,
                                   size_t actual_out_size) {
    int rc = video_stream_verify_hash(manifest, actual_out, actual_out_size);

    a90_console_printf("video.cache.verify.expected_sha256=%s\r\n", manifest->sha256);
    a90_console_printf("video.cache.verify.actual_sha256=%s\r\n", rc == 0 ? actual_out : "hash-error");
    a90_console_printf("video.cache.verify.sha256_checked=1\r\n");
    a90_console_printf("video.cache.verify.sha256_match=%d\r\n", rc == 0 ? 1 : 0);
    return rc;
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

static const char *video_stream_layout_name(enum video_stream_layout layout) {
    return layout == VIDEO_STREAM_LAYOUT_PLAYER_HUD ? "player-hud" : "full";
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
            sync->corrected_anchor_ns = sync->listen_begin_ns +
                                        ((uint64_t)sync->start_offset_ms * 1000000ULL);
            now_ns = video_monotonic_ns();
            sync->anchor_age_ns = now_ns > sync->listen_begin_ns ? now_ns - sync->listen_begin_ns : 0;
            a90_console_printf("video.stream.audio_sync.ready=1 elapsed_ms=%llu\r\n",
                               (unsigned long long)sync->ready_elapsed_ms);
            a90_console_printf("video.stream.audio_sync.listen_begin_ns=%llu\r\n",
                               (unsigned long long)sync->listen_begin_ns);
            a90_console_printf("video.stream.audio_sync.anchor_age_ns=%llu\r\n",
                               (unsigned long long)sync->anchor_age_ns);
            a90_console_printf("video.stream.audio_sync.start_offset_ms=%u\r\n",
                               sync->start_offset_ms);
            a90_console_printf("video.stream.audio_sync.corrected_anchor_ns=%llu\r\n",
                               (unsigned long long)sync->corrected_anchor_ns);
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
                             enum video_stream_layout layout,
                             struct video_audio_sync_state *audio_sync) {
    struct video_stream_header_v1 header_v1;
    struct video_stream_header_v2 header_v2;
    uint32_t palette[VIDEO_STREAM_PAL8_MAX_COLORS];
    uint32_t limit_frames = requested_frames > 0 && requested_frames < manifest->frame_count ?
                            requested_frames : manifest->frame_count;
    uint64_t interval_ns = video_frame_interval_ns(manifest->fps_num, manifest->fps_den);
    uint64_t started_ns;
    uint64_t finished_ns;
    uint64_t total_bytes = 0;
    uint64_t late_frames = 0;
    uint64_t max_late_ns = 0;
    uint64_t initial_drop_late_ns = 0;
    uint32_t flip_events = 0;
    uint32_t presented_frames = 0;
    uint32_t dropped_frames = 0;
    uint32_t first_presented_frame = UINT32_MAX;
    uint32_t beat_flash_active_frames = 0;
    uint32_t beat_flash_first_frame = UINT32_MAX;
    uint32_t beat_flash_last_frame = UINT32_MAX;
    uint32_t flip_delta_count = 0;
    uint64_t previous_flip_timestamp_us = 0;
    uint64_t flip_delta_min_us = UINT64_MAX;
    uint64_t flip_delta_max_us = 0;
    uint64_t flip_delta_sum_us = 0;
    bool drop_late_frames = false;
    struct a90_kms_flip_result last_flip;
    uint8_t *frame_buffer = NULL;
    uint8_t *decode_buffer = NULL;
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
    memset(palette, 0, sizeof(palette));
    if (manifest->stream_version == VIDEO_STREAM_VERSION_A90VSTR2) {
        rc = video_read_exact_fd(fd, &header_v2, sizeof(header_v2));
        if (rc < 0 || video_validate_stream_header_v2(manifest, &header_v2) < 0) {
            close(fd);
            a90_console_printf("video.stream.error=stream-header-invalid\r\n");
            return rc < 0 ? rc : -EINVAL;
        }
        rc = video_read_exact_fd(fd, palette, (size_t)manifest->palette_count * sizeof(palette[0]));
        if (rc < 0) {
            close(fd);
            a90_console_printf("video.stream.error=stream-palette-invalid\r\n");
            return rc;
        }
    } else {
        rc = video_read_exact_fd(fd, &header_v1, sizeof(header_v1));
        if (rc < 0 || video_validate_stream_header(manifest, &header_v1) < 0) {
            close(fd);
            a90_console_printf("video.stream.error=stream-header-invalid\r\n");
            return rc < 0 ? rc : -EINVAL;
        }
    }

    if (a90_kms_begin_frame_no_clear() < 0) {
        close(fd);
        return negative_errno_or(ENODEV);
    }
    {
        struct a90_fb *fb = a90_kms_framebuffer();
        uint64_t required_fb_bytes = 0;

        if (fb == NULL || fb->pixels == NULL) {
            close(fd);
            a90_console_printf("video.stream.error=kms-geometry-mismatch\r\n");
            return -EINVAL;
        }
        required_fb_bytes = (uint64_t)fb->stride * fb->height;
        if (fb->stride < (uint64_t)manifest->width * 4ULL ||
            required_fb_bytes > fb->size) {
            close(fd);
            a90_console_printf("video.stream.error=kms-geometry-mismatch\r\n");
            return -EINVAL;
        }
        if (layout == VIDEO_STREAM_LAYOUT_FULL) {
            if (fb->width != manifest->width ||
                fb->height != manifest->height ||
                (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_XBGR8888_RAW_STRIDE &&
                 fb->stride != manifest->stride)) {
                close(fd);
                a90_console_printf("video.stream.error=kms-geometry-mismatch\r\n");
                return -EINVAL;
            }
        } else {
            if ((manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 &&
                 manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE) ||
                manifest->width * VIDEO_PLAYER_HUD_SCALE > fb->width ||
                manifest->height * VIDEO_PLAYER_HUD_SCALE + 360U > fb->height) {
                close(fd);
                a90_console_printf("video.stream.error=player-hud-geometry-mismatch\r\n");
                return -EINVAL;
            }
        }
    }
    if (layout == VIDEO_STREAM_LAYOUT_PLAYER_HUD ||
        manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_GRAY8 ||
        manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1) {
        frame_buffer = (uint8_t *)malloc(manifest->frame_bytes);
        if (frame_buffer == NULL) {
            close(fd);
            a90_console_printf("video.stream.error=frame-buffer-alloc-failed\r\n");
            return -ENOMEM;
        }
    }
    if (manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE) {
        uint64_t required_indices = (uint64_t)manifest->width * manifest->height;

        if (layout != VIDEO_STREAM_LAYOUT_PLAYER_HUD ||
            required_indices == 0 || required_indices > VIDEO_STREAM_MAX_FRAME_BYTES) {
            free(frame_buffer);
            close(fd);
            a90_console_printf("video.stream.error=pal8-rle-layout-unsupported\r\n");
            return -EINVAL;
        }
        if (frame_buffer == NULL) {
            frame_buffer = (uint8_t *)malloc(manifest->max_payload_bytes);
        }
        decode_buffer = (uint8_t *)malloc((size_t)required_indices);
        if (frame_buffer == NULL || decode_buffer == NULL) {
            free(decode_buffer);
            free(frame_buffer);
            close(fd);
            a90_console_printf("video.stream.error=frame-buffer-alloc-failed\r\n");
            return -ENOMEM;
        }
    }
    if (present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP &&
        a90_kms_present("videostreamprime", false) < 0) {
        free(decode_buffer);
        free(frame_buffer);
        close(fd);
        return negative_errno_or(EIO);
    }

    if (audio_sync != NULL && audio_sync->enabled) {
        a90_console_printf("video.stream.audio_sync.enabled=1\r\n");
        a90_console_printf("video.stream.audio_sync.status_path=%s\r\n", audio_sync->status_path);
        a90_console_printf("video.stream.audio_sync.wait_ms=%u\r\n", audio_sync->wait_ms);
        rc = video_audio_sync_wait_ready(audio_sync);
        if (rc < 0) {
            free(decode_buffer);
            free(frame_buffer);
            close(fd);
            return rc;
        }
        started_ns = audio_sync->corrected_anchor_ns > 0 ?
                     audio_sync->corrected_anchor_ns : audio_sync->listen_begin_ns;
        drop_late_frames = audio_sync->ready && present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP;
    } else {
        a90_console_printf("video.stream.audio_sync.enabled=0\r\n");
        started_ns = video_monotonic_ns();
    }
    a90_console_printf("video.stream.audio_sync.drop_policy=%s\r\n",
                       drop_late_frames ? "late-frame-skip" : "none");
    if (drop_late_frames) {
        a90_console_printf("video.stream.audio_sync.drop_threshold_ns=%llu\r\n",
                           (unsigned long long)interval_ns);
    }
    for (frame_index = 0; frame_index < limit_frames; ++frame_index) {
        struct video_stream_frame_record_v1 record;
        struct video_stream_frame_record_v2 record_v2;
        struct a90_fb *fb;
        uint32_t record_payload_bytes;
        uint32_t record_mode = 0;
        uint64_t deadline_ns = started_ns + ((uint64_t)frame_index * interval_ns);
        uint64_t before_wait_ns;
        uint64_t after_present_ns;
        enum a90_cancel_kind cancel;

        if (manifest->stream_version == VIDEO_STREAM_VERSION_A90VSTR2) {
            rc = video_read_exact_fd(fd, &record_v2, sizeof(record_v2));
            if (rc < 0) {
                break;
            }
            if (record_v2.index != frame_index ||
                record_v2.payload_bytes == 0 ||
                record_v2.payload_bytes > manifest->max_payload_bytes ||
                (record_v2.mode != VIDEO_STREAM_PAL8_RAW_MODE &&
                 record_v2.mode != VIDEO_STREAM_PAL8_RLE_MODE)) {
                a90_console_printf("video.stream.error=frame-record-invalid index=%u payload=%u\r\n",
                                   record_v2.index, record_v2.payload_bytes);
                rc = -EINVAL;
                break;
            }
            record_payload_bytes = record_v2.payload_bytes;
            record_mode = record_v2.mode;
        } else {
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
            record_payload_bytes = record.payload_bytes;
        }
        before_wait_ns = video_monotonic_ns();
        if (drop_late_frames && frame_index + 1U < limit_frames && before_wait_ns > deadline_ns) {
            uint64_t late_ns = before_wait_ns - deadline_ns;

            if (late_ns > interval_ns) {
                rc = video_skip_exact_fd(fd, record_payload_bytes);
                if (rc < 0) {
                    break;
                }
                if (dropped_frames == 0) {
                    initial_drop_late_ns = late_ns;
                }
                ++dropped_frames;
                cancel = a90_console_poll_cancel(0);
                if (cancel != CANCEL_NONE) {
                    free(decode_buffer);
                    free(frame_buffer);
                    close(fd);
                    a90_console_printf("video.stream.presented=%u\r\n", presented_frames);
                    a90_console_printf("video.stream.dropped_frames=%u\r\n", dropped_frames);
                    return a90_console_cancelled("videostream", cancel);
                }
                continue;
            }
        }
        if (a90_kms_begin_frame_no_clear() < 0) {
            rc = negative_errno_or(ENODEV);
            break;
        }
        fb = a90_kms_framebuffer();
        if (fb == NULL || fb->pixels == NULL) {
            rc = -EINVAL;
            break;
        }
        if (layout == VIDEO_STREAM_LAYOUT_PLAYER_HUD) {
            rc = video_read_exact_fd(fd, frame_buffer, record_payload_bytes);
            if (rc == 0) {
                rc = video_render_player_hud(fb,
                                             frame_buffer,
                                             manifest,
                                             record_payload_bytes,
                                             record_mode,
                                             decode_buffer,
                                             (size_t)manifest->width * manifest->height,
                                             palette,
                                             manifest->palette_count,
                                             frame_index,
                                             manifest->frame_count,
                                             deadline_ns,
                                             audio_sync);
            }
        } else {
            rc = video_read_frame_payload(fd, fb, frame_buffer, manifest, record_payload_bytes);
        }
        if (rc < 0) {
            break;
        }
        if (layout == VIDEO_STREAM_LAYOUT_PLAYER_HUD &&
            audio_sync != NULL && audio_sync->ready &&
            audio_sync->corrected_anchor_ns > 0 &&
            deadline_ns >= audio_sync->corrected_anchor_ns &&
            manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1) {
            uint64_t frame_audio_ms = (deadline_ns - audio_sync->corrected_anchor_ns) / 1000000ULL;

            if (video_badapple_beat_flash_active(frame_audio_ms, NULL)) {
                if (beat_flash_first_frame == UINT32_MAX) {
                    beat_flash_first_frame = frame_index;
                }
                beat_flash_last_frame = frame_index;
                ++beat_flash_active_frames;
            }
        }
        before_wait_ns = video_monotonic_ns();
        rc = video_wait_until_ns(deadline_ns);
        if (rc < 0) {
            free(decode_buffer);
            free(frame_buffer);
            close(fd);
            a90_console_printf("video.stream.presented=%u\r\n", presented_frames);
            a90_console_printf("video.stream.dropped_frames=%u\r\n", dropped_frames);
            return rc;
        }
        if (present_mode == VIDEO_STREAM_PRESENT_PAGEFLIP) {
            struct a90_kms_flip_result flip;

            if (a90_kms_present_pageflip("videostream", 1000, &flip) < 0) {
                rc = negative_errno_or(EIO);
                break;
            }
            if (flip.event_received) {
                if (previous_flip_timestamp_us > 0 && flip.timestamp_us >= previous_flip_timestamp_us) {
                    uint64_t delta_us = flip.timestamp_us - previous_flip_timestamp_us;

                    if (delta_us < flip_delta_min_us) {
                        flip_delta_min_us = delta_us;
                    }
                    if (delta_us > flip_delta_max_us) {
                        flip_delta_max_us = delta_us;
                    }
                    flip_delta_sum_us += delta_us;
                    ++flip_delta_count;
                }
                previous_flip_timestamp_us = flip.timestamp_us;
                last_flip = flip;
                ++flip_events;
            }
        } else {
            if (a90_kms_present("videostream", false) < 0) {
                rc = negative_errno_or(EIO);
                break;
            }
        }
        total_bytes += record_payload_bytes;
        if (first_presented_frame == UINT32_MAX) {
            first_presented_frame = frame_index;
        }
        ++presented_frames;
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
            free(decode_buffer);
            free(frame_buffer);
            close(fd);
            a90_console_printf("video.stream.presented=%u\r\n", presented_frames);
            a90_console_printf("video.stream.dropped_frames=%u\r\n", dropped_frames);
            return a90_console_cancelled("videostream", cancel);
        }
    }
    finished_ns = video_monotonic_ns();
    free(decode_buffer);
    free(frame_buffer);
    close(fd);
    if (rc < 0) {
        return rc;
    }

    {
        uint64_t elapsed_ns = finished_ns > started_ns ? finished_ns - started_ns : 1;
        uint64_t fps_milli = ((uint64_t)presented_frames * 1000000000000ULL) / elapsed_ns;
        uint64_t mbps_milli = (total_bytes * 1000000ULL) / elapsed_ns;

        a90_console_printf("video.stream.presented=%u\r\n", presented_frames);
        a90_console_printf("video.stream.frames_requested=%u\r\n", requested_frames);
        a90_console_printf("video.stream.frames_total=%u\r\n", manifest->frame_count);
        a90_console_printf("video.stream.dropped_frames=%u\r\n", dropped_frames);
        a90_console_printf("video.stream.bytes=%llu\r\n", (unsigned long long)total_bytes);
        a90_console_printf("video.stream.elapsed_ns=%llu\r\n", (unsigned long long)elapsed_ns);
        a90_console_printf("video.stream.fps_milli=%llu\r\n", (unsigned long long)fps_milli);
        a90_console_printf("video.stream.mbps_milli=%llu\r\n", (unsigned long long)mbps_milli);
        a90_console_printf("video.stream.late_frames=%llu\r\n", (unsigned long long)late_frames);
        a90_console_printf("video.stream.max_late_ns=%llu\r\n", (unsigned long long)max_late_ns);
        a90_console_printf("video.stream.present_mode=%s\r\n", video_stream_present_mode_name(present_mode));
        a90_console_printf("video.stream.layout=%s\r\n", video_stream_layout_name(layout));
        if (layout == VIDEO_STREAM_LAYOUT_PLAYER_HUD) {
            bool beat_enabled = manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1;

            a90_console_printf("video.stream.beat_flash.enabled=%d\r\n", beat_enabled ? 1 : 0);
            a90_console_printf("video.stream.beat_flash.source=%s\r\n",
                               beat_enabled ? A90_BADAPPLE_BEAT_SOURCE_ID : "none");
            a90_console_printf("video.stream.beat_flash.audio_sha256=%s\r\n",
                               beat_enabled ? A90_BADAPPLE_BEAT_AUDIO_SHA256 : "none");
            a90_console_printf("video.stream.beat_flash.table_count=%u\r\n",
                               beat_enabled ? A90_BADAPPLE_BEAT_COUNT : 0);
            a90_console_printf("video.stream.beat_flash.window_ms=%u\r\n",
                               beat_enabled ? A90_BADAPPLE_BEAT_WINDOW_MS : 0);
            a90_console_printf("video.stream.beat_flash.active_frames=%u\r\n", beat_flash_active_frames);
            a90_console_printf("video.stream.beat_flash.first_frame=%u\r\n",
                               beat_flash_first_frame == UINT32_MAX ? 0 : beat_flash_first_frame);
            a90_console_printf("video.stream.beat_flash.last_frame=%u\r\n",
                               beat_flash_last_frame == UINT32_MAX ? 0 : beat_flash_last_frame);
        }
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
            a90_console_printf("video.stream.audio_sync.start_offset_ms=%u\r\n",
                               audio_sync->start_offset_ms);
            a90_console_printf("video.stream.audio_sync.corrected_anchor_ns=%llu\r\n",
                               (unsigned long long)audio_sync->corrected_anchor_ns);
            a90_console_printf("video.stream.audio_sync.sample_rate=%u\r\n", audio_sync->sample_rate);
            a90_console_printf("video.stream.audio_sync.frame_bytes=%u\r\n", audio_sync->frame_bytes);
            a90_console_printf("video.stream.audio_sync.total_frames=%u\r\n", audio_sync->total_frames);
            a90_console_printf("video.stream.audio_sync.first_presented_frame=%u\r\n",
                               first_presented_frame == UINT32_MAX ? 0 : first_presented_frame);
            a90_console_printf("video.stream.audio_sync.initial_drop_late_ns=%llu\r\n",
                               (unsigned long long)initial_drop_late_ns);
        }
        a90_console_printf("video.stream.flip_events=%u\r\n", flip_events);
        a90_console_printf("video.stream.flip_delta_count=%u\r\n", flip_delta_count);
        a90_console_printf("video.stream.flip_delta_min_us=%llu\r\n",
                           (unsigned long long)(flip_delta_count > 0 ? flip_delta_min_us : 0));
        a90_console_printf("video.stream.flip_delta_max_us=%llu\r\n",
                           (unsigned long long)flip_delta_max_us);
        a90_console_printf("video.stream.flip_delta_avg_us=%llu\r\n",
                           (unsigned long long)(flip_delta_count > 0 ?
                                                flip_delta_sum_us / flip_delta_count : 0));
        a90_console_printf("video.stream.flip_delta_target_us=%llu\r\n",
                           (unsigned long long)(interval_ns / 1000ULL));
        a90_console_printf("video.stream.last_sequence=%u\r\n", last_flip.sequence);
        a90_console_printf("video.stream.last_crtc=%u\r\n", last_flip.crtc_id);
        a90_console_printf("video.stream.last_timestamp_us=%llu\r\n",
                           (unsigned long long)last_flip.timestamp_us);
        a90_console_printf("video.stream.width=%u\r\n", manifest->width);
        a90_console_printf("video.stream.height=%u\r\n", manifest->height);
        a90_console_printf("video.stream.stride=%u\r\n", manifest->stride);
        a90_console_printf("video.stream.frame_bytes=%u\r\n", manifest->frame_bytes);
        a90_console_printf("video.stream.pixel_format=%s\r\n",
                           video_stream_pixel_format_name(manifest->pixel_format));
        a90_console_printf("video.stream.path=%s\r\n", video_stream_present_path_name(present_mode));
    }
    return 0;
}

static const char *video_cache_preset_sha256(const char *preset_name) {
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_BADAPPLE_NAME) == 0) {
        return VIDEO_CACHE_PRESET_BADAPPLE_SHA256;
    }
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME) == 0) {
        return VIDEO_CACHE_PRESET_BADAPPLE_SCALE_SHA256;
    }
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_NYAN_NAME) == 0) {
        return VIDEO_CACHE_PRESET_NYAN_SHA256;
    }
    return NULL;
}

static const char *video_cache_preset_asset_id(const char *preset_name) {
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_BADAPPLE_NAME) == 0) {
        return VIDEO_CACHE_PRESET_BADAPPLE_ASSET_ID;
    }
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME) == 0) {
        return VIDEO_CACHE_PRESET_BADAPPLE_SCALE_ASSET_ID;
    }
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_NYAN_NAME) == 0) {
        return VIDEO_CACHE_PRESET_NYAN_ASSET_ID;
    }
    return "unknown";
}

static enum video_stream_layout video_cache_preset_default_layout(const char *preset_name) {
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_BADAPPLE_NAME) == 0) {
        return VIDEO_STREAM_LAYOUT_PLAYER_HUD;
    }
    if (preset_name != NULL &&
        strcmp(preset_name, VIDEO_CACHE_PRESET_NYAN_NAME) == 0) {
        return VIDEO_STREAM_LAYOUT_PLAYER_HUD;
    }
    return VIDEO_STREAM_LAYOUT_FULL;
}

static int cmd_video_cache(char **argv, int argc);

static int video_demo_doom_status(const char *action) {
    a90_console_printf("video.demo.preset=doom\r\n");
    a90_console_printf("video.demo.asset_id=doomgeneric-pending\r\n");
    a90_console_printf("video.demo.status=blocked-input-prerequisite\r\n");
    a90_console_printf("video.demo.display=ready-kms-player-path\r\n");
    a90_console_printf("video.demo.audio=optional-ready\r\n");
    a90_console_printf("video.demo.input=not-proven\r\n");
    a90_console_printf("video.demo.input.touch=event6,event8-zero-events\r\n");
    a90_console_printf("video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat\r\n");
    a90_console_printf("video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate\r\n");
    a90_console_printf("video.demo.input.hardware_gate=usb-keyboard-otg\r\n");
    a90_console_printf("video.demo.input.next=attach-usb-keyboard-otg\r\n");
    a90_console_printf("video.demo.input.command=doominput <keyboard-event> 32 60000\r\n");
    a90_console_printf("video.demo.boot_asset_policy=boot-image-carries-status-not-doom\r\n");
    if (strcmp(action, "status") == 0) {
        a90_console_printf("video.demo.doom.status_rc=0\r\n");
        return 0;
    }
    a90_console_printf("video.demo.doom.%s=blocked-input-not-proven\r\n", action);
    return -EAGAIN;
}

static int cmd_video_demo(char **argv, int argc) {
    const char *usage = "usage: video demo [bars|checker|mono|0xRRGGBB|badapple|badapple-scale|nyan|doom [status|verify|play] [--trust-cache] [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status /cache/a90-audio-play/status.txt] [--sync-wait-ms N] [--sync-start-offset-ms N]]\r\n";
    char *cache_argv[CMDV1X_MAX_ARGS];
    int cache_argc = 0;
    int index;

    if (argc >= 3 && strcmp(argv[2], "doom") == 0) {
        const char *action = argc >= 4 ? argv[3] : "status";

        if (argc > 4 ||
            (strcmp(action, "status") != 0 &&
             strcmp(action, "verify") != 0 &&
             strcmp(action, "play") != 0)) {
            a90_console_printf("%s", usage);
            return -EINVAL;
        }
        return video_demo_doom_status(action);
    }

    if (argc >= 3 &&
        (strcmp(argv[2], VIDEO_CACHE_PRESET_BADAPPLE_NAME) == 0 ||
         strcmp(argv[2], VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME) == 0 ||
         strcmp(argv[2], VIDEO_CACHE_PRESET_NYAN_NAME) == 0)) {
        if ((argc >= 4 && argc + 1 > CMDV1X_MAX_ARGS) ||
            (argc == 3 && 5 > CMDV1X_MAX_ARGS)) {
            a90_console_printf("%s", usage);
            return -EINVAL;
        }
        cache_argv[cache_argc++] = argv[0];
        cache_argv[cache_argc++] = "cache";
        cache_argv[cache_argc++] = "preset";
        cache_argv[cache_argc++] = argv[2];
        cache_argv[cache_argc++] = argc >= 4 ? argv[3] : "status";
        for (index = 4; index < argc; ++index) {
            cache_argv[cache_argc++] = argv[index];
        }
        a90_console_printf("video.demo.preset=%s\r\n", argv[2]);
        a90_console_printf("video.demo.asset_id=%s\r\n", video_cache_preset_asset_id(argv[2]));
        a90_console_printf("video.demo.storage=sd-sha-cache\r\n");
        a90_console_printf("video.demo.boot_asset_policy=boot-image-carries-player-not-frames\r\n");
        return cmd_video_cache(cache_argv, cache_argc);
    }
    return cmd_video_frame(argv, argc);
}

static int cmd_video_stream(char **argv, int argc) {
    const char *usage = "usage: video stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status /cache/a90-audio-play/status.txt] [--sync-wait-ms N] [--sync-start-offset-ms N]\r\n";
    const char *manifest_path;
    struct video_stream_manifest manifest;
    struct video_audio_sync_state audio_sync;
    char actual_sha256[65];
    uint32_t requested_frames = 0;
    uint32_t sync_wait_ms = VIDEO_STREAM_AUDIO_SYNC_DEFAULT_WAIT_MS;
    uint32_t sync_start_offset_ms = 0;
    enum video_stream_present_mode present_mode = VIDEO_STREAM_PRESENT_SETCRTC;
    enum video_stream_layout layout = VIDEO_STREAM_LAYOUT_FULL;
    bool present_seen = false;
    bool layout_seen = false;
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
        if (strcmp(argv[index], "--layout") == 0) {
            if (layout_seen || index + 1 >= argc) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            layout_seen = true;
            if (strcmp(argv[index + 1], "full") == 0) {
                layout = VIDEO_STREAM_LAYOUT_FULL;
            } else if (strcmp(argv[index + 1], "player-hud") == 0) {
                layout = VIDEO_STREAM_LAYOUT_PLAYER_HUD;
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
        if (strcmp(argv[index], "--sync-start-offset-ms") == 0) {
            if (index + 1 >= argc ||
                !parse_u32_arg(argv[index + 1], 0,
                               VIDEO_STREAM_AUDIO_SYNC_MAX_START_OFFSET_MS,
                               &sync_start_offset_ms)) {
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
    audio_sync.start_offset_ms = sync_start_offset_ms;
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
    a90_console_printf("video.stream.requested_layout=%s\r\n", video_stream_layout_name(layout));
    a90_console_printf("video.stream.requested_audio_sync=%d\r\n", audio_sync.enabled ? 1 : 0);
    if (audio_sync.enabled) {
        a90_console_printf("video.stream.requested_audio_sync_status=%s\r\n", audio_sync.status_path);
        a90_console_printf("video.stream.requested_audio_sync_wait_ms=%u\r\n", audio_sync.wait_ms);
        a90_console_printf("video.stream.requested_audio_sync_start_offset_ms=%u\r\n",
                           audio_sync.start_offset_ms);
    }
    return video_stream_play(&manifest, requested_frames, present_mode, layout, &audio_sync);
}

static int cmd_video_cache(char **argv, int argc) {
    const char *usage = "usage: video cache [status|verify|play] SHA256 [--trust-cache] [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status /cache/a90-audio-play/status.txt] [--sync-wait-ms N] [--sync-start-offset-ms N] | video cache preset [badapple|badapple-scale|nyan] [status|verify|play] [options]\r\n";
    const char *action;
    const char *sha256;
    const char *preset_name = NULL;
    const char *preset_sha256 = NULL;
    char manifest_path[PATH_MAX];
    char actual_sha256[65];
    struct video_stream_manifest manifest;
    struct video_audio_sync_state audio_sync;
    uint32_t requested_frames = 0;
    uint32_t sync_wait_ms = VIDEO_STREAM_AUDIO_SYNC_DEFAULT_WAIT_MS;
    uint32_t sync_start_offset_ms = 0;
    enum video_stream_present_mode present_mode = VIDEO_STREAM_PRESENT_SETCRTC;
    enum video_stream_layout layout = VIDEO_STREAM_LAYOUT_FULL;
    bool present_seen = false;
    bool layout_seen = false;
    bool trust_cache = false;
    bool stream_exists = false;
    bool stream_size_match = false;
    uint64_t stream_size = 0;
    int option_start = 4;
    int index;
    int rc;

    memset(&audio_sync, 0, sizeof(audio_sync));
    if (argc < 4) {
        a90_console_printf("%s", usage);
        return -EINVAL;
    }
    if (strcmp(argv[2], "preset") == 0) {
        if (argc < 5) {
            a90_console_printf("%s", usage);
            return -EINVAL;
        }
        preset_name = argv[3];
        preset_sha256 = video_cache_preset_sha256(preset_name);
        if (preset_sha256 == NULL) {
            a90_console_printf("video.cache.preset=%s\r\n", preset_name);
            a90_console_printf("video.cache.preset.error=unknown\r\n");
            return -EINVAL;
        }
        action = argv[4];
        sha256 = preset_sha256;
        layout = video_cache_preset_default_layout(preset_name);
        option_start = 5;
        a90_console_printf("video.cache.preset=%s\r\n", preset_name);
        a90_console_printf("video.cache.preset.asset_id=%s\r\n", video_cache_preset_asset_id(preset_name));
        a90_console_printf("video.cache.preset.sha256=%s\r\n", preset_sha256);
    } else {
        action = argv[2];
        sha256 = argv[3];
    }
    if (strcmp(action, "status") != 0 &&
        strcmp(action, "verify") != 0 &&
        strcmp(action, "play") != 0) {
        a90_console_printf("%s", usage);
        return -EINVAL;
    }
    rc = video_cache_load_manifest(sha256, manifest_path, sizeof(manifest_path), &manifest);
    if (rc < 0) {
        return rc;
    }
    if (strcmp(action, "status") == 0) {
        if (argc != option_start) {
            a90_console_printf("%s", usage);
            return -EINVAL;
        }
        video_cache_print_status(sha256, manifest_path, &manifest);
        return 0;
    }
    if (strcmp(action, "verify") == 0) {
        if (argc != option_start) {
            a90_console_printf("%s", usage);
            return -EINVAL;
        }
        video_cache_print_status(sha256, manifest_path, &manifest);
        return video_cache_verify_hash(&manifest, actual_sha256, sizeof(actual_sha256));
    }

    index = option_start;
    while (index < argc) {
        if (strcmp(argv[index], "--trust-cache") == 0) {
            if (trust_cache) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            trust_cache = true;
            index++;
            continue;
        }
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
        if (strcmp(argv[index], "--layout") == 0) {
            if (layout_seen || index + 1 >= argc) {
                a90_console_printf("%s", usage);
                return -EINVAL;
            }
            layout_seen = true;
            if (strcmp(argv[index + 1], "full") == 0) {
                layout = VIDEO_STREAM_LAYOUT_FULL;
            } else if (strcmp(argv[index + 1], "player-hud") == 0) {
                layout = VIDEO_STREAM_LAYOUT_PLAYER_HUD;
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
                a90_console_printf("video.cache.play.audio_sync.error=status-path-not-allowed\r\n");
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
        if (strcmp(argv[index], "--sync-start-offset-ms") == 0) {
            if (index + 1 >= argc ||
                !parse_u32_arg(argv[index + 1], 0,
                               VIDEO_STREAM_AUDIO_SYNC_MAX_START_OFFSET_MS,
                               &sync_start_offset_ms)) {
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
    audio_sync.start_offset_ms = sync_start_offset_ms;
    video_cache_print_status(sha256, manifest_path, &manifest);
    rc = video_cache_stat_stream(&manifest, &stream_exists, &stream_size, &stream_size_match);
    if (rc < 0) {
        a90_console_printf("video.cache.play.error=stream-not-ready\r\n");
        return rc;
    }
    if (!stream_exists || !stream_size_match) {
        a90_console_printf("video.cache.play.stream_exists=%d\r\n", stream_exists ? 1 : 0);
        a90_console_printf("video.cache.play.stream_size=%llu\r\n", (unsigned long long)stream_size);
        a90_console_printf("video.cache.play.error=stream-not-ready\r\n");
        return -EINVAL;
    }
    if (trust_cache) {
        a90_console_printf("video.cache.play.trust_cache=1\r\n");
        a90_console_printf("video.cache.verify.expected_sha256=%s\r\n", manifest.sha256);
        a90_console_printf("video.cache.verify.actual_sha256=trust-cache-not-checked\r\n");
        a90_console_printf("video.cache.verify.sha256_checked=0\r\n");
        a90_console_printf("video.cache.verify.sha256_match=0\r\n");
    } else {
        rc = video_cache_verify_hash(&manifest, actual_sha256, sizeof(actual_sha256));
        if (rc < 0) {
            return rc;
        }
        a90_console_printf("video.cache.play.trust_cache=0\r\n");
    }
    a90_console_printf("video.cache.play.manifest=%s\r\n", manifest_path);
    a90_console_printf("video.cache.play.file=%s\r\n", manifest.stream_path);
    a90_console_printf("video.cache.play.requested_present=%s\r\n", video_stream_present_mode_name(present_mode));
    a90_console_printf("video.cache.play.requested_layout=%s\r\n", video_stream_layout_name(layout));
    a90_console_printf("video.cache.play.requested_audio_sync=%d\r\n", audio_sync.enabled ? 1 : 0);
    if (audio_sync.enabled) {
        a90_console_printf("video.cache.play.requested_audio_sync_start_offset_ms=%u\r\n",
                           audio_sync.start_offset_ms);
    }
    return video_stream_play(&manifest, requested_frames, present_mode, layout, &audio_sync);
}


static int handle_video(char **argv, int argc) {
    const char *subcommand = argc > 1 ? argv[1] : "status";

    if (strcmp(subcommand, "status") == 0) {
        if (argc != 1 && argc != 2) {
            a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|demo [badapple|badapple-scale|nyan|frame-pattern]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]|flipprobe [frames]|stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status PATH]|cache [status|verify|play] SHA256 [--trust-cache] [--layout full|player-hud]|cache preset [badapple|badapple-scale|nyan] [status|verify|play]]\r\n");
            return -EINVAL;
        }
        return cmd_video_status();
    }
    if (strcmp(subcommand, "frame") == 0) {
        return cmd_video_frame(argv, argc);
    }
    if (strcmp(subcommand, "demo") == 0) {
        return cmd_video_demo(argv, argc);
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
    if (strcmp(subcommand, "cache") == 0) {
        return cmd_video_cache(argv, argc);
    }

    a90_console_printf("usage: video [status|frame [bars|checker|mono|0xRRGGBB]|demo [badapple|badapple-scale|nyan|frame-pattern]|anim [bars|checker|pulse] [frames] [delay_ms]|blitbench [frames]|flipprobe [frames]|stream --manifest PATH --video-only [--frames N] [--present setcrtc|pageflip] [--layout full|player-hud] [--sync-audio-status PATH]|cache [status|verify|play] SHA256 [--trust-cache] [--layout full|player-hud]|cache preset [badapple|badapple-scale|nyan] [status|verify|play]]\r\n");
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
