#include "a90_app_log.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_log.h"
#include "a90_shell.h"
#include "a90_timeline.h"
#include "a90_util.h"

static uint32_t app_log_text_scale(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.width >= 1080) {
        return 6;
    }
    if (info.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t app_log_shrink_text_scale(const char *text,
                                          uint32_t scale,
                                          uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

int a90_app_log_draw_summary(void) {
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

    scale = app_log_text_scale();
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
                  app_log_shrink_text_scale(line1, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line2, 0xffffff,
                  app_log_shrink_text_scale(line2, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line3, 0xffffff,
                  app_log_shrink_text_scale(line3, scale, card_w - scale * 2));
    y += line_h;
    a90_draw_text(a90_kms_framebuffer(), x, y, line4, 0xffffff,
                  app_log_shrink_text_scale(line4, scale, card_w - scale * 2));

    a90_draw_text(a90_kms_framebuffer(), x, a90_kms_framebuffer()->height - scale * 12,
                  "PRESS ANY BUTTON TO RETURN", 0xffffff,
                  app_log_shrink_text_scale("PRESS ANY BUTTON TO RETURN", scale, card_w));

    if (a90_kms_present("screenlog", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}
