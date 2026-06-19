#include "a90_app_audio.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_audio_profile.h"
#include "a90_audio_route.h"
#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_util.h"

#define A90_APP_AUDIO_LINE_COUNT 8

static uint32_t app_audio_text_scale(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.width >= 1080) {
        return 5;
    }
    if (info.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t app_audio_shrink_text_scale(const char *text,
                                            uint32_t scale,
                                            uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static const char *app_audio_text_or_dash(const char *text) {
    return text != NULL && text[0] != '\0' ? text : "-";
}

static int app_audio_draw_lines(const char *title,
                                const char *const *lines,
                                size_t line_count,
                                const char *footer,
                                uint32_t accent) {
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

    scale = app_audio_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 10;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 11;

    a90_draw_text(a90_kms_framebuffer(), x, y, title, accent,
                  app_audio_shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(),
                  x - scale,
                  y - scale,
                  card_w,
                  line_h * ((uint32_t)line_count + 1U),
                  0x202020);
    for (index = 0; index < line_count; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";

        a90_draw_text(a90_kms_framebuffer(),
                      x,
                      y + (uint32_t)index * line_h,
                      line,
                      0xffffff,
                      app_audio_shrink_text_scale(line, scale, card_w - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(),
                  x,
                  a90_kms_framebuffer()->height - scale * 12,
                  footer,
                  0xffffff,
                  app_audio_shrink_text_scale(footer, scale, card_w));

    if (a90_kms_present("screenaudio", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_app_audio_draw_status(void) {
    const struct audio_speaker_profile *profile =
        a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    int route_count = a90_audio_route_control_count();
    int reset_count = a90_audio_route_reset_count();
    int speaker_count = a90_audio_speaker_map_count();
    bool boost_present = a90_audio_route_has_smart_amp_boost();
    bool boost_write_allowed = a90_audio_route_layer_write_allowed(AUDIO_ROUTE_LAYER_BLOCKED);
    char line0[160];
    char line1[160];
    char line2[160];
    char line3[160];
    char line4[160];
    char line5[160];
    char line6[160];
    char line7[160];
    const char *lines[A90_APP_AUDIO_LINE_COUNT];

    snprintf(line0, sizeof(line0), "CORE %s  %s",
             AUDIO_CORE_PROMOTION_VERSION, AUDIO_CORE_PROMOTION_RUN);
    snprintf(line1, sizeof(line1), "PROFILE %s",
             profile != NULL ? profile->id : AUDIO_DEFAULT_PROFILE_ID);
    snprintf(line2, sizeof(line2), "ENDPOINT %s",
             profile != NULL ? app_audio_text_or_dash(profile->endpoint) : "-");
    snprintf(line3, sizeof(line3), "APP %d  ACDB %d  %dHz %db",
             profile != NULL ? profile->app_type : -1,
             profile != NULL ? profile->acdb_id : -1,
             profile != NULL ? profile->sample_rate : 0,
             profile != NULL ? profile->bit_width : 0);
    snprintf(line4, sizeof(line4), "ROUTE %d  RESET %d  SPEAKERS %d",
             route_count, reset_count, speaker_count);
    snprintf(line5, sizeof(line5), "MAP %s",
             profile != NULL ? app_audio_text_or_dash(profile->speaker_map) : "-");
    snprintf(line6, sizeof(line6), "SAFETY AMP <=%dmilli DUR <=%dms",
             profile != NULL ? profile->amplitude_cap_milli : 0,
             profile != NULL ? profile->duration_cap_ms : 0);
    snprintf(line7, sizeof(line7), "BOOST %s WRITE %s SP UNVERIFIED",
             boost_present ? "PRESENT" : "NONE",
             boost_write_allowed ? "ALLOW" : "BLOCK");

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;

    return app_audio_draw_lines("AUDIO STATUS",
                                lines,
                                A90_APP_AUDIO_LINE_COUNT,
                                "DISPLAY ONLY - NO AUDIO WRITE",
                                0xffcc66);
}

int a90_app_audio_draw_map(void) {
    const struct audio_speaker_profile *profile =
        a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    int core_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_CORE, false);
    int feedback_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_FEEDBACK, false);
    int endpoint_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_ENDPOINT, false);
    int blocked_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_BLOCKED, false);
    char line0[160];
    char line1[160];
    char line2[160];
    char line3[160];
    char line4[160];
    char line5[160];
    char line6[160];
    char line7[160];
    const char *left = a90_audio_speaker_map_id(4);
    const char *right = a90_audio_speaker_map_id(5);
    const char *lines[A90_APP_AUDIO_LINE_COUNT];

    snprintf(line0, sizeof(line0), "PROFILE %s",
             profile != NULL ? profile->id : AUDIO_DEFAULT_PROFILE_ID);
    snprintf(line1, sizeof(line1), "PATH SLIMBUS_0_RX -> WSA_CDC_DMA_RX");
    snprintf(line2, sizeof(line2), "CORE %d  FEEDBACK %d  ENDPOINT %d",
             core_count, feedback_count, endpoint_count);
    snprintf(line3, sizeof(line3), "BLOCKED BOOST WRITES %d",
             blocked_count);
    snprintf(line4, sizeof(line4), "LEFT %s routes=%d boost=%d",
             app_audio_text_or_dash(left),
             a90_audio_route_count_for_speaker("SpkrLeft"),
             a90_audio_route_boost_count_for_speaker("SpkrLeft"));
    snprintf(line5, sizeof(line5), "RIGHT %s routes=%d boost=%d",
             app_audio_text_or_dash(right),
             a90_audio_route_count_for_speaker("SpkrRight"),
             a90_audio_route_boost_count_for_speaker("SpkrRight"));
    snprintf(line6, sizeof(line6), "VI SPKR_VI_1/SPKR_VI_2 observed");
    snprintf(line7, sizeof(line7), "APPTYPE 69941 ACDB 15 SETS %d",
             AUDIO_PROFILE_ACDB_SET_COUNT);

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;

    return app_audio_draw_lines("AUDIO ROUTE MAP",
                                lines,
                                A90_APP_AUDIO_LINE_COUNT,
                                "DISPLAY ONLY - NO AUDIO WRITE",
                                0x66ccff);
}
