#include "a90_app_audio.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_audio_chime.h"
#include "a90_audio_profile.h"
#include "a90_audio_route.h"
#include "a90_audio_stage.h"
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

static void app_audio_format_acdb_order(const struct audio_speaker_profile *profile,
                                        char *buffer,
                                        size_t buffer_size) {
    size_t used = 0;
    int index;

    if (buffer_size == 0) {
        return;
    }
    buffer[0] = '\0';
    if (profile == NULL) {
        snprintf(buffer, buffer_size, "-");
        return;
    }
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        int written = snprintf(buffer + used,
                               buffer_size - used,
                               "%s%d",
                               index == 0 ? "" : ",",
                               profile->acdb_set_order[index]);
        if (written < 0) {
            buffer[0] = '\0';
            return;
        }
        if ((size_t)written >= buffer_size - used) {
            break;
        }
        used += (size_t)written;
    }
}

static int app_audio_stage_native_count(void) {
    int count = 0;
    int index;

    for (index = 0; index < AUDIO_STAGE_CONTRACT_COUNT; ++index) {
        if (AUDIO_STAGE_CONTRACTS[index].native_implemented) {
            ++count;
        }
    }
    return count;
}

static int app_audio_stage_runtime_write_count(void) {
    int count = 0;
    int index;

    for (index = 0; index < AUDIO_STAGE_CONTRACT_COUNT; ++index) {
        if (AUDIO_STAGE_CONTRACTS[index].writes_runtime_state) {
            ++count;
        }
    }
    return count;
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
    snprintf(line1, sizeof(line1), "LATEST %s %s",
             AUDIO_PRODUCTIZATION_LATEST_VERSION, AUDIO_PRODUCTIZATION_LATEST_RUN);
    snprintf(line2, sizeof(line2), "PROFILE %s",
             profile != NULL ? profile->id : AUDIO_DEFAULT_PROFILE_ID);
    snprintf(line3, sizeof(line3), "APP %d  ACDB %d  %dHz %db",
             profile != NULL ? profile->app_type : -1,
             profile != NULL ? profile->acdb_id : -1,
             profile != NULL ? profile->sample_rate : 0,
             profile != NULL ? profile->bit_width : 0);
    snprintf(line4, sizeof(line4), "ROUTE %d  RESET %d  SPEAKERS %d",
             route_count, reset_count, speaker_count);
    snprintf(line5, sizeof(line5), "CHIME BOOT %s  STOP %s",
             AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT ? "ON" : "OFF",
             AUDIO_STOP_EXECUTE_SCOPE);
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

int a90_app_audio_draw_profile(void) {
    const struct audio_speaker_profile *profile =
        a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    char order[96];
    char line0[160];
    char line1[160];
    char line2[160];
    char line3[160];
    char line4[160];
    char line5[160];
    char line6[160];
    char line7[160];
    const char *lines[A90_APP_AUDIO_LINE_COUNT];

    app_audio_format_acdb_order(profile, order, sizeof(order));
    snprintf(line0, sizeof(line0), "PROFILE %s",
             profile != NULL ? profile->id : AUDIO_DEFAULT_PROFILE_ID);
    snprintf(line1, sizeof(line1), "ENDPOINT %s",
             profile != NULL ? app_audio_text_or_dash(profile->endpoint) : "-");
    snprintf(line2, sizeof(line2), "PCM card=%d dev=%d ch=%d",
             profile != NULL ? profile->card : -1,
             profile != NULL ? profile->pcm_device : -1,
             profile != NULL ? profile->channels : 0);
    snprintf(line3, sizeof(line3), "APP %d ACDB %d %dHz %db",
             profile != NULL ? profile->app_type : -1,
             profile != NULL ? profile->acdb_id : -1,
             profile != NULL ? profile->sample_rate : 0,
             profile != NULL ? profile->bit_width : 0);
    snprintf(line4, sizeof(line4), "GLOBAL CFG %s",
             profile != NULL ? app_audio_text_or_dash(profile->global_app_type_config) : "-");
    snprintf(line5, sizeof(line5), "STREAM CFG %s",
             profile != NULL ? app_audio_text_or_dash(profile->stream_app_type_config) : "-");
    snprintf(line6, sizeof(line6), "SETS %d: %s", AUDIO_PROFILE_ACDB_SET_COUNT, order);
    snprintf(line7, sizeof(line7), "STAGES %d native=%d writes=%d",
             AUDIO_STAGE_CONTRACT_COUNT,
             app_audio_stage_native_count(),
             app_audio_stage_runtime_write_count());

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;

    return app_audio_draw_lines("AUDIO PROFILE",
                                lines,
                                A90_APP_AUDIO_LINE_COUNT,
                                "DISPLAY ONLY - NO AUDIO WRITE",
                                0x99dd66);
}

int a90_app_audio_draw_stages(void) {
    char line0[160];
    char line1[160];
    char line2[160];
    char line3[160];
    char line4[160];
    char line5[160];
    char line6[160];
    char line7[160];
    const char *lines[A90_APP_AUDIO_LINE_COUNT];

    snprintf(line0, sizeof(line0), "CONTRACT v%d stages=%d native=%d writes=%d",
             AUDIO_STAGE_CONTRACT_VERSION,
             AUDIO_STAGE_CONTRACT_COUNT,
             app_audio_stage_native_count(),
             app_audio_stage_runtime_write_count());
    snprintf(line1, sizeof(line1), "BOOT preflight-v2321-health RO");
    snprintf(line2, sizeof(line2), "ADSP adsp-boot-once WRITE");
    snprintf(line3, sizeof(line3), "SND snd-materialize-once WRITE");
    snprintf(line4, sizeof(line4), "APP write-global-app-type-config WRITE");
    snprintf(line5, sizeof(line5), "ACDB verify/prep/load RO; SET WRITE");
    snprintf(line6, sizeof(line6), "ROUTE core WRITE; PCM bounded WRITE");
    snprintf(line7, sizeof(line7), "STOP cleanup/reset/dealloc WRITE");

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;

    return app_audio_draw_lines("AUDIO STAGES",
                                lines,
                                A90_APP_AUDIO_LINE_COUNT,
                                "DISPLAY ONLY - NO AUDIO WRITE",
                                0xddaa66);
}

int a90_app_audio_draw_map(void) {
    const struct audio_speaker_profile *profile =
        a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    int core_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_CORE, false);
    int feedback_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_FEEDBACK, false);
    int endpoint_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_ENDPOINT, false);
    int blocked_count = a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_BLOCKED, false);
    int left_route_count = a90_audio_route_count_for_speaker("SpkrLeft");
    int right_route_count = a90_audio_route_count_for_speaker("SpkrRight");
    int left_observer_count = a90_audio_observer_count_for_prefix(profile, "SpkrLeft");
    int right_observer_count = a90_audio_observer_count_for_prefix(profile, "SpkrRight");
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
    snprintf(line3, sizeof(line3), "BOOST WRITE BLOCKED %d  SP UNVERIFIED",
             blocked_count);
    snprintf(line4, sizeof(line4), "LEFT %s route=%d obs=%d boost=%d",
             app_audio_text_or_dash(left),
             left_route_count,
             left_observer_count,
             a90_audio_route_boost_count_for_speaker("SpkrLeft"));
    snprintf(line5, sizeof(line5), "RIGHT %s route=%d obs=%d boost=%d",
             app_audio_text_or_dash(right),
             right_route_count,
             right_observer_count,
             a90_audio_route_boost_count_for_speaker("SpkrRight"));
    snprintf(line6, sizeof(line6), "VI SPKR_VI_1/SPKR_VI_2 OBSERVED ONLY");
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

int a90_app_audio_draw_chime(void) {
    const struct audio_speaker_profile *profile =
        a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    char line0[160];
    char line1[160];
    char line2[160];
    char line3[160];
    char line4[160];
    char line5[160];
    char line6[160];
    char line7[160];
    const char *lines[A90_APP_AUDIO_LINE_COUNT];

    snprintf(line0, sizeof(line0), "COMMAND audio chime --execute");
    snprintf(line1, sizeof(line1), "DEFAULT %dmilli %dms LISTEN",
             AUDIO_CHIME_DEFAULT_AMPLITUDE_MILLI,
             AUDIO_CHIME_DEFAULT_DURATION_MS);
    snprintf(line2, sizeof(line2), "PROFILE %s -> audio play",
             profile != NULL ? profile->id : AUDIO_DEFAULT_PROFILE_ID);
    snprintf(line3, sizeof(line3), "BOOT AUTOPLAY %s BLOCKS_BOOT=0",
             AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT ? "ENABLED" : "DISABLED");
    snprintf(line4, sizeof(line4), "VALIDATED V2839 PCM ROUTE SETCAL OK");
    snprintf(line5, sizeof(line5), "ROLLBACK v2321 SELFTEST fail=0");
    snprintf(line6, sizeof(line6), "SAFETY AMP <=%dmilli DUR <=%dms",
             profile != NULL ? profile->amplitude_cap_milli : 0,
             profile != NULL ? profile->duration_cap_ms : 0);
    snprintf(line7, sizeof(line7), "NO SMART-AMP BOOST/SP BYPASS WRITE");

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;

    return app_audio_draw_lines("AUDIO CHIME",
                                lines,
                                A90_APP_AUDIO_LINE_COUNT,
                                "DISPLAY ONLY - MANUAL COMMAND",
                                0xff99cc);
}
