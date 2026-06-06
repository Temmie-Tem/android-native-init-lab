#include "a90_app_about.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_config.h"
#include "a90_changelog.h"
#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_util.h"

static uint32_t app_about_display_width_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.width > 0 ? info.width : fallback;
}

static uint32_t app_about_text_scale(void) {
    uint32_t width = app_about_display_width_or(0);

    if (width >= 1080) {
        return 4;
    }
    if (width >= 720) {
        return 3;
    }
    return 2;
}

static uint32_t app_about_shrink_text_scale(const char *text,
                                            uint32_t scale,
                                            uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static size_t app_about_visible_line_count(void) {
    uint32_t scale = app_about_text_scale();
    uint32_t height = 2400;
    uint32_t line_height = scale * 10;
    uint32_t top;
    uint32_t footer_y;
    uint32_t usable;
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.height > 0) {
        height = info.height;
    }
    top = height / 12;
    top += line_height + scale * 4;
    footer_y = height - scale * 16;
    if (footer_y <= top + line_height) {
        return 1;
    }
    usable = footer_y - top - scale * 4;
    if (usable < line_height) {
        return 1;
    }
    return usable / line_height;
}

static size_t app_about_page_count_for_lines(size_t count) {
    size_t visible = app_about_visible_line_count();

    if (visible == 0) {
        visible = 1;
    }
    if (count == 0) {
        return 1;
    }
    return (count + visible - 1) / visible;
}

static int app_about_draw_lines_paged(const char *title,
                                      const char *const *lines,
                                      size_t count,
                                      size_t page) {
    char title_buf[96];
    const char *footer = "POWER BACK";
    uint32_t scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t footer_y;
    size_t visible;
    size_t page_count;
    size_t start;
    size_t end;
    size_t index;

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_about_text_scale();
    title_scale = scale + 1;
    left = a90_kms_framebuffer()->width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = a90_kms_framebuffer()->height / 12;
    content_width = a90_kms_framebuffer()->width - (left * 2);
    line_height = scale * 10;
    footer_y = a90_kms_framebuffer()->height - scale * 12;
    visible = app_about_visible_line_count();
    if (visible == 0) {
        visible = 1;
    }
    page_count = app_about_page_count_for_lines(count);
    if (page >= page_count) {
        page = page_count - 1;
    }
    start = page * visible;
    end = start + visible;
    if (end > count) {
        end = count;
    }
    if (page_count > 1) {
        snprintf(title_buf, sizeof(title_buf), "%s %u/%u",
                 title,
                 (unsigned int)(page + 1),
                 (unsigned int)page_count);
        title = title_buf;
        footer = "VOL/HOLD PAGE  POWER BACK";
    }

    a90_draw_text(a90_kms_framebuffer(), left, top, title, 0xffcc33,
                  app_about_shrink_text_scale(title, title_scale, content_width));
    top += line_height + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(),
                  left - scale,
                  top - scale,
                  content_width,
                  line_height * ((uint32_t)(end - start) + 1),
                  0x202020);

    for (index = start; index < end; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";
        uint32_t row = (uint32_t)(index - start);
        uint32_t color = index == 0 ? 0x88ee88 : 0xffffff;

        a90_draw_text(a90_kms_framebuffer(),
                      left,
                      top + row * line_height,
                      line,
                      color,
                      app_about_shrink_text_scale(line, scale, content_width - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(),
                  left,
                  footer_y,
                  footer,
                  0xffffff,
                  app_about_shrink_text_scale(footer, scale, content_width));

    if (a90_kms_present("screenabout", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int app_about_draw_lines(const char *title,
                                const char *const *lines,
                                size_t count) {
    return app_about_draw_lines_paged(title, lines, count, 0);
}

int a90_app_about_draw_version(void) {
    char version_line[96];
    const char *lines[5];

    snprintf(version_line, sizeof(version_line), "VERSION %s (%s)", INIT_VERSION, INIT_BUILD);
    lines[0] = INIT_BANNER;
    lines[1] = version_line;
    lines[2] = INIT_CREATOR;
    lines[3] = "KERNEL STOCK ANDROID LINUX 4.14";
    lines[4] = "RUNTIME CUSTOM STATIC PID 1";

    return app_about_draw_lines("ABOUT / VERSION", lines, SCREEN_MENU_COUNT(lines));
}

int a90_app_about_draw_changelog_paged(size_t page) {
    const char *lines[A90_CHANGELOG_MAX_SERIES];
    size_t count = a90_changelog_series_count();
    size_t index;

    if (count > A90_CHANGELOG_MAX_SERIES) {
        count = A90_CHANGELOG_MAX_SERIES;
    }
    for (index = 0; index < count; ++index) {
        const struct a90_changelog_series *series = a90_changelog_series_at(index);

        lines[index] = series != NULL ? series->label : "UNKNOWN";
    }
    return app_about_draw_lines_paged("ABOUT / CHANGELOG", lines, count, page);
}

int a90_app_about_draw_changelog(void) {
    return a90_app_about_draw_changelog_paged(0);
}

int a90_app_about_draw_changelog_detail_index(size_t index, size_t page) {
    const struct a90_changelog_entry *entry = a90_changelog_entry_at(index);
    const char *lines[A90_CHANGELOG_DETAIL_MAX + 1];
    char title[64];
    size_t count = 0;
    size_t detail_index;

    if (entry == NULL) {
        const char *fallback[] = {
            "UNKNOWN CHANGELOG ENTRY",
            "The selected changelog index is invalid",
        };

        return app_about_draw_lines_paged("CHANGELOG / UNKNOWN",
                                          fallback,
                                          SCREEN_MENU_COUNT(fallback),
                                          0);
    }

    lines[count++] = entry->label;
    for (detail_index = 0; detail_index < A90_CHANGELOG_DETAIL_MAX; ++detail_index) {
        if (entry->details[detail_index] == NULL) {
            break;
        }
        lines[count++] = entry->details[detail_index];
    }
    snprintf(title, sizeof(title), "CHANGELOG / %s", entry->label);
    return app_about_draw_lines_paged(title, lines, count, page);
}

int a90_app_about_draw_credits(void) {
    const char *lines[] = {
        INIT_CREATOR,
        "DEVICE SAMSUNG GALAXY A90 5G",
        "MODEL SM-A908N",
        "KERNEL SAMSUNG STOCK 4.14",
        "CONTROL USB ACM + NCM",
        "PROJECT NATIVE INIT USERSPACE",
    };

    return app_about_draw_lines("ABOUT / CREDITS", lines, SCREEN_MENU_COUNT(lines));
}

size_t a90_app_about_page_count(enum screen_app_id app_id, size_t changelog_index) {
    switch (app_id) {
    case SCREEN_APP_ABOUT_VERSION:
        return app_about_page_count_for_lines(5);
    case SCREEN_APP_ABOUT_CHANGELOG:
        return app_about_page_count_for_lines(a90_changelog_series_count());
    case SCREEN_APP_ABOUT_CREDITS:
        return app_about_page_count_for_lines(6);
    case SCREEN_APP_CHANGELOG_DETAIL:
    {
        const struct a90_changelog_entry *entry = a90_changelog_entry_at(changelog_index);
        size_t count = entry != NULL ? a90_changelog_detail_count(entry) + 1 : 2;

        return app_about_page_count_for_lines(count);
    }
    default:
        return 1;
    }
}

int a90_app_about_draw_paged(enum screen_app_id app_id, size_t changelog_index, size_t page) {
    switch (app_id) {
    case SCREEN_APP_ABOUT_VERSION:
        return a90_app_about_draw_version();
    case SCREEN_APP_ABOUT_CHANGELOG:
        return a90_app_about_draw_changelog_paged(page);
    case SCREEN_APP_ABOUT_CREDITS:
        return a90_app_about_draw_credits();
    case SCREEN_APP_CHANGELOG_DETAIL:
        return a90_app_about_draw_changelog_detail_index(changelog_index, page);
    default:
        return 0;
    }
}

int a90_app_about_draw(enum screen_app_id app_id) {
    return a90_app_about_draw_paged(app_id, 0, 0);
}
