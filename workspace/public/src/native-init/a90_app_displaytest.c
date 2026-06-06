#include "a90_app_displaytest.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_config.h"
#include "a90_draw.h"
#include "a90_input.h"
#include "a90_kms.h"
#include "a90_menu.h"
#include "a90_util.h"

static uint32_t app_displaytest_width_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.width > 0 ? info.width : fallback;
}

static uint32_t app_displaytest_height_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.height > 0 ? info.height : fallback;
}

static uint32_t app_displaytest_text_scale(void) {
    uint32_t width = app_displaytest_width_or(0);

    if (width >= 1080) {
        return 4;
    }
    if (width >= 720) {
        return 3;
    }
    return 2;
}

static int app_displaytest_clamp_int(int value, int min_value, int max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

void a90_app_displaytest_cutout_clamp(struct cutout_calibration_state *cal) {
    int width = (int)app_displaytest_width_or(1080);
    int height = (int)app_displaytest_height_or(2400);
    int min_size = width / 40;
    int max_size = width / 8;
    int margin;

    if (min_size < 18) {
        min_size = 18;
    }
    if (max_size < min_size) {
        max_size = min_size;
    }
    cal->size = app_displaytest_clamp_int(cal->size, min_size, max_size);
    margin = cal->size / 2 + 2;
    cal->center_x = app_displaytest_clamp_int(cal->center_x, margin, width - margin);
    cal->center_y = app_displaytest_clamp_int(cal->center_y, margin, height - margin);
    if ((int)cal->field < 0 || cal->field >= CUTOUT_CAL_FIELD_COUNT) {
        cal->field = CUTOUT_CAL_FIELD_Y;
    }
}

void a90_app_displaytest_cutout_default(struct cutout_calibration_state *cal) {
    int width = (int)app_displaytest_width_or(1080);
    int height = (int)app_displaytest_height_or(2400);

    cal->center_x = width / 2;
    cal->center_y = height / 30;
    cal->size = width / 22;
    cal->field = CUTOUT_CAL_FIELD_Y;
    a90_app_displaytest_cutout_clamp(cal);
}

static void app_displaytest_cutout_adjust(struct cutout_calibration_state *cal,
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
    a90_app_displaytest_cutout_clamp(cal);
}

void a90_app_displaytest_cutout_reset(struct a90_app_cutout_calibration *state) {
    if (state == NULL) {
        return;
    }
    a90_app_displaytest_cutout_default(&state->cal);
    state->down_mask = 0;
    state->power_down_ms = 0;
    state->last_power_up_ms = 0;
}

bool a90_app_displaytest_cutout_feed_event(struct a90_app_cutout_calibration *state,
                                           const struct input_event *event) {
    unsigned int mask;
    long now_ms;

    if (state == NULL || event == NULL || event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = a90_input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    now_ms = monotonic_millis();
    if (event->value == 1) {
        state->down_mask |= mask;
        if ((state->down_mask & (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) ==
            (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN)) {
            return true;
        }
        if (event->code == KEY_VOLUMEUP) {
            app_displaytest_cutout_adjust(&state->cal, -1);
        } else if (event->code == KEY_VOLUMEDOWN) {
            app_displaytest_cutout_adjust(&state->cal, 1);
        } else if (event->code == KEY_POWER) {
            state->power_down_ms = now_ms;
        }
        return false;
    }

    state->down_mask &= ~mask;
    if (event->code == KEY_POWER) {
        long duration_ms = state->power_down_ms > 0 ? now_ms - state->power_down_ms : 0;

        state->power_down_ms = 0;
        if (duration_ms >= A90_INPUT_LONG_PRESS_MS) {
            return true;
        }
        if (state->last_power_up_ms > 0 &&
            now_ms - state->last_power_up_ms <= A90_INPUT_DOUBLE_CLICK_MS) {
            state->last_power_up_ms = 0;
            return true;
        }
        state->last_power_up_ms = now_ms;
        state->cal.field = (enum cutout_calibration_field)
                           (((int)state->cal.field + 1) % CUTOUT_CAL_FIELD_COUNT);
    }
    return false;
}

int a90_app_displaytest_cutout_draw(const struct a90_app_cutout_calibration *state,
                                    bool interactive) {
    if (state == NULL) {
        return -EINVAL;
    }
    return a90_app_displaytest_draw_cutout_calibration(&state->cal, interactive);
}

static void display_text_next_chunk(const char *line,
                                    size_t offset,
                                    size_t max_chars,
                                    char *out,
                                    size_t out_size,
                                    size_t *next_offset) {
    size_t len = strlen(line + offset);
    size_t chunk_len;
    size_t split;

    if (out_size == 0) {
        *next_offset = offset;
        return;
    }
    if (max_chars == 0) {
        out[0] = '\0';
        *next_offset = offset;
        return;
    }
    if (len <= max_chars) {
        snprintf(out, out_size, "%s", line + offset);
        *next_offset = offset + len;
        return;
    }

    chunk_len = max_chars;
    split = chunk_len;
    while (split > 8 && line[offset + split] != ' ' && line[offset + split] != '\t') {
        --split;
    }
    if (split > 8) {
        chunk_len = split;
    }
    if (chunk_len >= out_size) {
        chunk_len = out_size - 1;
    }

    memcpy(out, line + offset, chunk_len);
    out[chunk_len] = '\0';
    offset += chunk_len;
    while (line[offset] == ' ' || line[offset] == '\t') {
        ++offset;
    }
    *next_offset = offset;
}

static const char *app_displaytest_cutout_field_name(enum cutout_calibration_field field) {
    switch (field) {
    case CUTOUT_CAL_FIELD_X:
        return "X";
    case CUTOUT_CAL_FIELD_Y:
        return "Y";
    case CUTOUT_CAL_FIELD_SIZE:
        return "SIZE";
    default:
        return "?";
    }
}

int a90_app_displaytest_draw_cutout_calibration(const struct cutout_calibration_state *cal,
                                                bool interactive) {
    struct cutout_calibration_state local = *cal;
    char line[96];
    uint32_t scale;
    uint32_t small_scale;
    uint32_t width;
    uint32_t height;
    uint32_t center_x;
    uint32_t center_y;
    uint32_t size;
    uint32_t box_x;
    uint32_t box_y;
    uint32_t box_thick;
    uint32_t gap;
    uint32_t side_margin;
    uint32_t slot_y;
    uint32_t slot_h;
    uint32_t slot_label_y;
    uint32_t camera_zone_w;
    uint32_t camera_zone_x;
    uint32_t left_w;
    uint32_t right_x;
    uint32_t right_w;
    uint32_t safe_y;
    uint32_t safe_h;
    uint32_t panel_y;
    uint32_t panel_h;
    uint32_t panel_w;
    uint32_t footer_y;

    a90_app_displaytest_cutout_clamp(&local);
    if (a90_kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_displaytest_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    width = a90_kms_framebuffer()->width;
    height = a90_kms_framebuffer()->height;
    center_x = (uint32_t)local.center_x;
    center_y = (uint32_t)local.center_y;
    size = (uint32_t)local.size;
    box_x = center_x - size / 2;
    box_y = center_y - size / 2;
    box_thick = scale > 3 ? scale / 2 : 1;
    gap = scale * 3;
    side_margin = width / 24;
    if (side_margin < scale * 4) {
        side_margin = scale * 4;
    }
    footer_y = height > scale * 12 ? height - scale * 12 : height;

    slot_y = scale * 2;
    slot_h = center_y + size / 2 + scale * 12;
    if (slot_h < scale * 16) {
        slot_h = scale * 16;
    }
    slot_label_y = center_y + size / 2 + scale * 3;
    if (slot_label_y + scale * 8 > slot_y + slot_h) {
        slot_label_y = slot_y + scale * 2;
    }
    camera_zone_w = size + scale * 16;
    if (camera_zone_w < scale * 28) {
        camera_zone_w = scale * 28;
    }
    camera_zone_x = center_x > camera_zone_w / 2 ? center_x - camera_zone_w / 2 : 0;
    left_w = camera_zone_x > side_margin + gap ?
             camera_zone_x - side_margin - gap : 0;
    right_x = camera_zone_x + camera_zone_w + gap;
    right_w = side_margin + (width - side_margin * 2) > right_x ?
              side_margin + (width - side_margin * 2) - right_x : 0;

    if (left_w > scale * 18) {
        a90_draw_rect(a90_kms_framebuffer(), side_margin, slot_y, left_w, slot_h, 0x07182a);
        a90_draw_rect_outline(a90_kms_framebuffer(), side_margin, slot_y, left_w, slot_h,
                              box_thick, 0x315080);
        a90_draw_text_fit(a90_kms_framebuffer(), side_margin + scale * 2,
                          slot_label_y,
                          "LEFT SAFE", 0x66ddff, small_scale,
                          left_w - scale * 4);
    }
    if (right_w > scale * 18) {
        a90_draw_rect(a90_kms_framebuffer(), right_x, slot_y, right_w, slot_h, 0x07182a);
        a90_draw_rect_outline(a90_kms_framebuffer(), right_x, slot_y, right_w, slot_h,
                              box_thick, 0x315080);
        a90_draw_text_fit(a90_kms_framebuffer(), right_x + scale * 2,
                          slot_label_y,
                          "RIGHT SAFE", 0x66ddff, small_scale,
                          right_w - scale * 4);
    }
    a90_draw_rect_outline(a90_kms_framebuffer(), camera_zone_x, slot_y,
                          camera_zone_w, slot_h, box_thick, 0xff8040);
    a90_draw_text_fit(a90_kms_framebuffer(), camera_zone_x + scale * 2,
                      slot_label_y,
                      "CAMERA", 0xffcc33, small_scale,
                      camera_zone_w - scale * 4);

    a90_draw_rect_outline(a90_kms_framebuffer(), box_x, box_y, size, size,
                          box_thick, 0xff8040);
    if (box_x > scale * 8) {
        a90_draw_rect(a90_kms_framebuffer(), box_x - scale * 8, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_x + size + scale * 8 < width) {
        a90_draw_rect(a90_kms_framebuffer(), box_x + size, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_y > scale * 8) {
        a90_draw_rect(a90_kms_framebuffer(), center_x, box_y - scale * 8,
                      box_thick, scale * 8, 0x66ddff);
    }
    if (box_y + size + scale * 8 < height) {
        a90_draw_rect(a90_kms_framebuffer(), center_x, box_y + size,
                      box_thick, scale * 8, 0x66ddff);
    }
    a90_draw_rect(a90_kms_framebuffer(), center_x, center_y, box_thick, box_thick, 0xffffff);

    safe_y = center_y + size / 2 + scale * 12;
    if (safe_y < height / 5) {
        safe_y = height / 5;
    }
    if (safe_y + scale * 32 < footer_y) {
        safe_h = footer_y - safe_y - scale * 4;
        a90_draw_rect_outline(a90_kms_framebuffer(),
                              side_margin,
                              safe_y,
                              width - side_margin * 2,
                              safe_h,
                              box_thick,
                              0x4060a0);
        a90_draw_rect(a90_kms_framebuffer(), width / 2, safe_y,
                      box_thick, safe_h, 0x604020);
        a90_draw_rect(a90_kms_framebuffer(), side_margin,
                      safe_y + safe_h / 2,
                      width - side_margin * 2,
                      box_thick,
                      0x604020);
    }

    panel_y = safe_y + scale * 4;
    panel_w = width - side_margin * 2;
    panel_h = scale * 42;
    if (panel_y + panel_h > footer_y) {
        panel_y = height / 3;
    }
    a90_draw_rect(a90_kms_framebuffer(), side_margin, panel_y,
                  panel_w, panel_h, 0x101820);
    a90_draw_rect_outline(a90_kms_framebuffer(), side_margin, panel_y,
                          panel_w, panel_h, box_thick, 0x315080);
    a90_draw_text_fit(a90_kms_framebuffer(), side_margin + scale * 2,
                      panel_y + scale * 2,
                      interactive ? "ALIGN ORANGE BOX TO CAMERA HOLE"
                                  : "REFERENCE: ORANGE BOX SHOULD MATCH CAMERA",
                      0x88ee88, small_scale, panel_w - scale * 4);
    snprintf(line, sizeof(line), "X=%d  Y=%d  SIZE=%d  FIELD=%s",
             local.center_x,
             local.center_y,
             local.size,
             app_displaytest_cutout_field_name(local.field));
    a90_draw_text_fit(a90_kms_framebuffer(), side_margin + scale * 2,
                      panel_y + scale * 12,
                      line, 0xffffff, small_scale,
                      panel_w - scale * 4);
    a90_draw_text_fit(a90_kms_framebuffer(), side_margin + scale * 2,
                      panel_y + scale * 22,
                      interactive ? "VOL+/- ADJUST  POWER NEXT FIELD"
                                  : "SHELL: cutoutcal [x y size]",
                      0xffcc33, small_scale, panel_w - scale * 4);
    a90_draw_text_fit(a90_kms_framebuffer(), side_margin + scale * 2,
                      panel_y + scale * 32,
                      interactive ? "PWR LONG/DBL OR VOL+DN BACK"
                                  : "MENU APP: TOOLS > CUTOUT CAL",
                      0xdddddd, small_scale, panel_w - scale * 4);
    a90_draw_text_fit(a90_kms_framebuffer(), side_margin, footer_y,
                      interactive ? "CALIBRATION MODE" : "DISPLAYTEST SAFE",
                      0xffffff, small_scale, width - side_margin * 2);

    if (a90_kms_present("cutoutcal", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

const char *a90_app_displaytest_page_title(unsigned int page_index) {
    switch (page_index % DISPLAY_TEST_PAGE_COUNT) {
    case 0:
        return "COLOR / PIXEL";
    case 1:
        return "FONT / WRAP";
    case 2:
        return "SAFE / CUTOUT";
    case 3:
        return "HUD / MENU";
    default:
        return "DISPLAY";
    }
}

int a90_app_displaytest_draw_page(unsigned int page_index,
                                  const struct a90_hud_storage_status *storage) {
    struct display_test_color {
        const char *name;
        uint32_t fill;
        uint32_t text;
    };
    static const struct display_test_color palette[] = {
        { "BLACK",  0x000000, 0xffffff },
        { "WHITE",  0xffffff, 0x000000 },
        { "RED",    0xd84040, 0xffffff },
        { "GREEN",  0x30d060, 0x000000 },
        { "BLUE",   0x3080ff, 0xffffff },
        { "YELLOW", 0xffcc33, 0x000000 },
        { "CYAN",   0x40d8ff, 0x000000 },
        { "GRAY",   0x606060, 0xffffff },
    };
    static const char *layout_items[] = {
        "HIDE MENU",
        "STATUS",
        "LOG",
        "TOOLS",
        "POWER",
    };
    const char *wrap_sample =
        "LONG LOG LINE WRAPS INTO SAFE WIDTH WITHOUT CLIPPING AND KEEPS WORD BOUNDARIES";
    char line[96];
    char chunk[96];
    const char *cursor;
    uint32_t scale;
    uint32_t small_scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t body_top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t gap;
    uint32_t swatch_width;
    uint32_t swatch_height;
    uint32_t footer_y;
    uint32_t max_chars;
    size_t wrap_offset;
    size_t index;

    page_index %= DISPLAY_TEST_PAGE_COUNT;
    if (page_index == 2) {
        struct cutout_calibration_state cal;

        a90_app_displaytest_cutout_default(&cal);
        return a90_app_displaytest_draw_cutout_calibration(&cal, false);
    }

    if (a90_kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_displaytest_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    title_scale = scale + 1;
    left = a90_kms_framebuffer()->width / 24;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = a90_kms_framebuffer()->height / 16;
    content_width = a90_kms_framebuffer()->width > left * 2 ? a90_kms_framebuffer()->width - (left * 2) : a90_kms_framebuffer()->width;
    line_height = scale * 10;
    gap = scale * 3;
    footer_y = a90_kms_framebuffer()->height > scale * 14 ? a90_kms_framebuffer()->height - scale * 14 : a90_kms_framebuffer()->height;

    a90_draw_rect_outline(a90_kms_framebuffer(), left - scale, top - scale,
                          content_width + scale * 2,
                          footer_y - top + scale,
                          scale,
                          0x315080);

    snprintf(line, sizeof(line), "TOOLS / DISPLAY TEST %u/%u",
             page_index + 1,
             DISPLAY_TEST_PAGE_COUNT);
    a90_draw_text_fit(a90_kms_framebuffer(), left, top, line,
                      0xffcc33, title_scale, content_width);
    top += line_height + gap;
    a90_draw_text_fit(a90_kms_framebuffer(), left, top, a90_app_displaytest_page_title(page_index),
                      0x88aaff, scale, content_width);
    top += line_height + gap;
    body_top = top;

    if (page_index == 0) {
        swatch_width = (content_width - gap) / 2;
        swatch_height = line_height * 2;
        for (index = 0; index < SCREEN_MENU_COUNT(palette); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t swatch_x = left + col * (swatch_width + gap);
            uint32_t swatch_y = body_top + row * (swatch_height + gap);

            a90_draw_rect(a90_kms_framebuffer(), swatch_x, swatch_y,
                          swatch_width, swatch_height, palette[index].fill);
            a90_draw_rect(a90_kms_framebuffer(), swatch_x, swatch_y,
                          swatch_width, scale, 0xffffff);
            a90_draw_text_fit(a90_kms_framebuffer(),
                              swatch_x + scale * 2,
                              swatch_y + scale * 5,
                              palette[index].name,
                              palette[index].text,
                              scale,
                              swatch_width - scale * 4);
        }
        top = body_top + ((uint32_t)(SCREEN_MENU_COUNT(palette) + 1) / 2) *
              (swatch_height + gap) + gap;
        a90_draw_text_fit(a90_kms_framebuffer(), left, top,
                          "PIXEL FORMAT XBGR8888 / RGB LABEL CHECK",
                          0x88ee88, small_scale, content_width);
        top += line_height;
        a90_draw_text_fit(a90_kms_framebuffer(), left, top,
                          "WHITE BAR SHOULD BE WHITE, RED/GREEN/BLUE SHOULD MATCH LABELS",
                          0xdddddd, small_scale, content_width);
    } else if (page_index == 1) {
        for (index = 1; index <= 8; ++index) {
            uint32_t row_scale = (uint32_t)index;
            uint32_t row_height = row_scale * 8 + scale * 2;

            if (top + row_height >= footer_y - line_height * 5) {
                break;
            }
            snprintf(line, sizeof(line), "SCALE %u ABC123 %s", row_scale, INIT_VERSION);
            a90_draw_rect(a90_kms_framebuffer(), left, top,
                          content_width, row_height,
                          index % 2 ? 0x101620 : 0x182030);
            a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 2, top + scale,
                              line, 0xffffff, row_scale,
                              content_width - scale * 4);
            top += row_height + scale;
        }
        top += gap;
        a90_draw_text_fit(a90_kms_framebuffer(), left, top, "WRAP SAMPLE",
                          0x88aaff, scale, content_width);
        top += line_height;
        cursor = wrap_sample;
        max_chars = content_width / (small_scale * 6);
        if (max_chars < 8) {
            max_chars = 8;
        }
        wrap_offset = 0;
        for (index = 0; cursor[wrap_offset] != '\0' && index < 5; ++index) {
            size_t next_offset;

            display_text_next_chunk(cursor,
                                    wrap_offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 2, top,
                              chunk, 0xffffff, small_scale,
                              content_width - scale * 4);
            top += small_scale * 10;
            wrap_offset = next_offset;
        }
    } else if (page_index == 2) {
        uint32_t cutout_y = body_top + gap;
        uint32_t cutout_h = line_height * 3;
        uint32_t cutout_w = content_width / 5;
        uint32_t cutout_x;
        uint32_t cutout_center_x = a90_kms_framebuffer()->width / 2;
        uint32_t cutout_center_y = cutout_y + cutout_h / 2;
        uint32_t pocket_w;
        uint32_t right_x;
        uint32_t right_w;
        uint32_t hole = scale * 10;
        uint32_t grid_y;
        uint32_t grid_h;
        uint32_t center_x;
        uint32_t center_y;
        uint32_t label_y;
        uint32_t legend_y;
        uint32_t chip;

        if (cutout_w < scale * 24) {
            cutout_w = scale * 24;
        }
        if (cutout_w > content_width / 3) {
            cutout_w = content_width / 3;
        }
        cutout_x = (a90_kms_framebuffer()->width - cutout_w) / 2;
        pocket_w = cutout_x > left + gap ? cutout_x - left - gap : 0;
        right_x = cutout_x + cutout_w + gap;
        right_w = left + content_width > right_x ? left + content_width - right_x : 0;

        if (pocket_w > scale * 16) {
            a90_draw_rect(a90_kms_framebuffer(), left, cutout_y, pocket_w, cutout_h, 0x07182a);
            a90_draw_rect_outline(a90_kms_framebuffer(), left, cutout_y, pocket_w, cutout_h,
                                  scale, 0x315080);
            a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 2, cutout_y + scale * 2,
                              "LEFT SAFE", 0x66ddff, small_scale,
                              pocket_w - scale * 4);
        }
        a90_draw_rect(a90_kms_framebuffer(), cutout_x, cutout_y, cutout_w, cutout_h, 0x281018);
        a90_draw_rect_outline(a90_kms_framebuffer(), cutout_x, cutout_y, cutout_w, cutout_h,
                              scale, 0xff8040);
        a90_draw_text_fit(a90_kms_framebuffer(), cutout_x + scale * 2, cutout_y + scale * 2,
                          "CAMERA", 0xffcc33, small_scale,
                          cutout_w - scale * 4);
        if (hole > cutout_h - scale * 2) {
            hole = cutout_h - scale * 2;
        }
        if (hole >= scale * 4) {
            a90_draw_rect(a90_kms_framebuffer(),
                          cutout_center_x - hole / 2,
                          cutout_center_y - hole / 2,
                          hole,
                          hole,
                          0x000000);
            a90_draw_rect_outline(a90_kms_framebuffer(),
                                  cutout_center_x - hole / 2,
                                  cutout_center_y - hole / 2,
                                  hole,
                                  hole,
                                  scale,
                                  0xffffff);
        }
        if (right_w > scale * 16) {
            a90_draw_rect(a90_kms_framebuffer(), right_x, cutout_y, right_w, cutout_h, 0x07182a);
            a90_draw_rect_outline(a90_kms_framebuffer(), right_x, cutout_y, right_w, cutout_h,
                                  scale, 0x315080);
            a90_draw_text_fit(a90_kms_framebuffer(), right_x + scale * 2, cutout_y + scale * 2,
                              "RIGHT SAFE", 0x66ddff, small_scale,
                              right_w - scale * 4);
        }

        grid_y = cutout_y + cutout_h + gap * 3;
        grid_h = footer_y > grid_y + line_height ? footer_y - grid_y - line_height : 0;
        if (grid_h >= line_height * 4) {
            center_x = left + content_width / 2;
            center_y = grid_y + grid_h / 2;
            label_y = grid_y + scale * 2;
            a90_draw_rect(a90_kms_framebuffer(), left, grid_y, content_width, grid_h, 0x0b1018);
            a90_draw_rect_outline(a90_kms_framebuffer(), left, grid_y, content_width, grid_h,
                                  scale, 0xff8040);
            a90_draw_rect(a90_kms_framebuffer(), center_x, grid_y, scale, grid_h, 0x604020);
            a90_draw_rect(a90_kms_framebuffer(), left, center_y, content_width, scale, 0x604020);
            a90_draw_rect_outline(a90_kms_framebuffer(),
                                  left + content_width / 10,
                                  grid_y + grid_h / 7,
                                  content_width * 4 / 5,
                                  grid_h * 5 / 7,
                                  scale,
                                  0x4060a0);
            a90_draw_rect(a90_kms_framebuffer(), left + scale, label_y,
                          content_width - scale * 2,
                          line_height * 2 + scale,
                          0x101820);
            a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 3, label_y + scale,
                              "SAFE GRID", 0x88ee88, small_scale,
                              content_width - scale * 6);
            a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 3,
                              label_y + line_height,
                              "ORANGE EDGE  BLUE CONTENT", 0xdddddd,
                              small_scale, content_width - scale * 6);
            chip = scale * 4;
            legend_y = grid_y + grid_h;
            if (legend_y > line_height * 2 + scale * 6) {
                legend_y -= line_height * 2 + scale * 6;
            }
            if (legend_y > label_y + line_height * 3 && content_width > scale * 28) {
                a90_draw_rect(a90_kms_framebuffer(), left + scale * 3, legend_y,
                              chip, chip, 0xff8040);
                a90_draw_text_fit(a90_kms_framebuffer(), left + scale * 9,
                                  legend_y - scale,
                                  "EDGE", 0xffcc33, small_scale,
                                  content_width / 3);
                a90_draw_rect(a90_kms_framebuffer(), left + content_width / 2,
                              legend_y, chip, chip, 0x4060a0);
                a90_draw_text_fit(a90_kms_framebuffer(),
                                  left + content_width / 2 + scale * 6,
                                  legend_y - scale,
                                  "CONTENT", 0x66ddff, small_scale,
                                  content_width / 3);
            }
        }
    } else {
        uint32_t card_y = body_top;
        uint32_t card_h = line_height * 3;
        uint32_t half_w = (content_width - gap) / 2;

        if (storage != NULL) {
            a90_hud_draw_status_overlay(a90_kms_framebuffer(), storage, left, card_y);
        }
        card_y += line_height * 5;
        a90_draw_text_fit(a90_kms_framebuffer(), left, card_y,
                          "HUD/MENU PREVIEW - CHECK SPACING AND TEXT WEIGHT",
                          0x88ee88, small_scale, content_width);
        card_y += line_height + gap;
        for (index = 0; index < SCREEN_MENU_COUNT(layout_items); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t item_x = left + col * (half_w + gap);
            uint32_t item_y = card_y + row * (card_h + gap);
            uint32_t fill = index == 0 ? 0xd84040 : 0x182030;
            uint32_t edge = index == 0 ? 0x66ddff : 0x315080;

            if (item_y + card_h >= footer_y - line_height) {
                break;
            }
            a90_draw_rect(a90_kms_framebuffer(), item_x, item_y, half_w, card_h, fill);
            a90_draw_rect_outline(a90_kms_framebuffer(), item_x, item_y, half_w, card_h,
                                  scale, edge);
            a90_draw_text_fit(a90_kms_framebuffer(),
                              item_x + scale * 2,
                              item_y + scale * 4,
                              layout_items[index],
                              0xffffff,
                              scale,
                              half_w - scale * 4);
        }
        a90_draw_text_fit(a90_kms_framebuffer(),
                          left,
                          footer_y - line_height * 2,
                          "PREVIEW ONLY: REAL MENU STILL USES LIVE STATUS + LOG TAIL",
                          0xdddddd,
                          small_scale,
                          content_width - scale * 4);
    }

    a90_draw_text_fit(a90_kms_framebuffer(), left, footer_y, "VOL+/- PAGE  POWER BACK",
                      0xffffff, small_scale, content_width);

    if (a90_kms_present("displaytest", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}
