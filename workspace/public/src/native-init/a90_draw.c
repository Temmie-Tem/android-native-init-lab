#include "a90_draw.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>

static uint32_t a90_draw_pack_rgb_for_xbgr8888(uint32_t color) {
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;

    return ((uint32_t)blue << 16) | ((uint32_t)green << 8) | red;
}

void a90_draw_clear(struct a90_fb *fb, uint32_t color) {
    size_t y;
    uint32_t pixel = a90_draw_pack_rgb_for_xbgr8888(color);

    if (fb == NULL || fb->pixels == NULL || fb->pixels == MAP_FAILED) {
        return;
    }

    for (y = 0; y < fb->height; ++y) {
        uint32_t *row = (uint32_t *)((char *)fb->pixels + (y * fb->stride));
        size_t x;

        for (x = 0; x < fb->width; ++x) {
            row[x] = pixel;
        }
    }
}

void a90_draw_rect(struct a90_fb *fb,
                   uint32_t x,
                   uint32_t y,
                   uint32_t width,
                   uint32_t height,
                   uint32_t color) {
    uint32_t pixel = a90_draw_pack_rgb_for_xbgr8888(color);
    uint32_t y_end;

    if (fb == NULL || fb->pixels == NULL || fb->pixels == MAP_FAILED ||
        x >= fb->width || y >= fb->height) {
        return;
    }

    if (x + width > fb->width) {
        width = fb->width - x;
    }
    if (y + height > fb->height) {
        height = fb->height - y;
    }

    y_end = y + height;
    while (y < y_end) {
        uint32_t *row = (uint32_t *)((char *)fb->pixels + (y * fb->stride));
        uint32_t x_end = x + width;
        uint32_t cursor = x;

        while (cursor < x_end) {
            row[cursor++] = pixel;
        }
        ++y;
    }
}

static const uint8_t *font5x7_rows(char ch) {
    static const uint8_t blank[7] = { 0, 0, 0, 0, 0, 0, 0 };

    if (ch >= 'a' && ch <= 'z') {
        ch = (char)(ch - 'a' + 'A');
    }

    switch (ch) {
    case 'A': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11 }; return g; }
    case 'B': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E }; return g; }
    case 'C': { static const uint8_t g[7] = { 0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E }; return g; }
    case 'D': { static const uint8_t g[7] = { 0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C }; return g; }
    case 'E': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F }; return g; }
    case 'F': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10 }; return g; }
    case 'G': { static const uint8_t g[7] = { 0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F }; return g; }
    case 'H': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11 }; return g; }
    case 'I': { static const uint8_t g[7] = { 0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E }; return g; }
    case 'J': { static const uint8_t g[7] = { 0x01, 0x01, 0x01, 0x01, 0x11, 0x11, 0x0E }; return g; }
    case 'K': { static const uint8_t g[7] = { 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11 }; return g; }
    case 'L': { static const uint8_t g[7] = { 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F }; return g; }
    case 'M': { static const uint8_t g[7] = { 0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11 }; return g; }
    case 'N': { static const uint8_t g[7] = { 0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11 }; return g; }
    case 'O': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E }; return g; }
    case 'P': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10 }; return g; }
    case 'Q': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D }; return g; }
    case 'R': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11 }; return g; }
    case 'S': { static const uint8_t g[7] = { 0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E }; return g; }
    case 'T': { static const uint8_t g[7] = { 0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04 }; return g; }
    case 'U': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E }; return g; }
    case 'V': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04 }; return g; }
    case 'W': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A }; return g; }
    case 'X': { static const uint8_t g[7] = { 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11 }; return g; }
    case 'Y': { static const uint8_t g[7] = { 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04 }; return g; }
    case 'Z': { static const uint8_t g[7] = { 0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F }; return g; }
    case '0': { static const uint8_t g[7] = { 0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E }; return g; }
    case '1': { static const uint8_t g[7] = { 0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E }; return g; }
    case '2': { static const uint8_t g[7] = { 0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F }; return g; }
    case '3': { static const uint8_t g[7] = { 0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E }; return g; }
    case '4': { static const uint8_t g[7] = { 0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02 }; return g; }
    case '5': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x01, 0x01, 0x1E }; return g; }
    case '6': { static const uint8_t g[7] = { 0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E }; return g; }
    case '7': { static const uint8_t g[7] = { 0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08 }; return g; }
    case '8': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E }; return g; }
    case '9': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C }; return g; }
    case '%': { static const uint8_t g[7] = { 0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13 }; return g; }
    case '.': { static const uint8_t g[7] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x06 }; return g; }
    case '/': { static const uint8_t g[7] = { 0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10 }; return g; }
    case ':': { static const uint8_t g[7] = { 0x00, 0x06, 0x06, 0x00, 0x06, 0x06, 0x00 }; return g; }
    case '+': { static const uint8_t g[7] = { 0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00 }; return g; }
    case '-': { static const uint8_t g[7] = { 0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00 }; return g; }
    case ' ': return blank;
    default: return blank;
    }
}

static void a90_draw_char(struct a90_fb *fb,
                          uint32_t x,
                          uint32_t y,
                          char ch,
                          uint32_t color,
                          uint32_t scale) {
    const uint8_t *rows = font5x7_rows(ch);
    uint32_t row;

    for (row = 0; row < 7; ++row) {
        uint32_t col;
        for (col = 0; col < 5; ++col) {
            if ((rows[row] & (1U << (4 - col))) != 0) {
                a90_draw_rect(fb,
                              x + (col * scale),
                              y + (row * scale),
                              scale,
                              scale,
                              color);
            }
        }
    }
}

void a90_draw_text(struct a90_fb *fb,
                   uint32_t x,
                   uint32_t y,
                   const char *text,
                   uint32_t color,
                   uint32_t scale) {
    if (text == NULL) {
        return;
    }
    while (*text != '\0') {
        a90_draw_char(fb, x, y, *text, color, scale);
        x += scale * 6;
        ++text;
    }
}

static uint32_t a90_draw_shrink_text_scale(const char *text,
                                           uint32_t scale,
                                           uint32_t max_width) {
    size_t len = text != NULL ? strlen(text) : 0;

    while (scale > 1 && len * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

void a90_draw_text_fit(struct a90_fb *fb,
                       uint32_t x,
                       uint32_t y,
                       const char *text,
                       uint32_t color,
                       uint32_t scale,
                       uint32_t max_width) {
    a90_draw_text(fb, x, y, text, color,
                  a90_draw_shrink_text_scale(text, scale, max_width));
}

void a90_draw_rect_outline(struct a90_fb *fb,
                           uint32_t x,
                           uint32_t y,
                           uint32_t width,
                           uint32_t height,
                           uint32_t thickness,
                           uint32_t color) {
    if (thickness == 0 || width == 0 || height == 0) {
        return;
    }
    if (width <= thickness * 2 || height <= thickness * 2) {
        a90_draw_rect(fb, x, y, width, height, color);
        return;
    }

    a90_draw_rect(fb, x, y, width, thickness, color);
    a90_draw_rect(fb, x, y + height - thickness, width, thickness, color);
    a90_draw_rect(fb, x, y, thickness, height, color);
    a90_draw_rect(fb, x + width - thickness, y, thickness, height, color);
}

void a90_draw_boot_frame(struct a90_fb *fb) {
    uint32_t width;
    uint32_t height;
    uint32_t header_h;
    uint32_t footer_h;
    uint32_t gap;
    uint32_t footer_w;
    uint32_t footer_y;

    if (fb == NULL) {
        return;
    }

    width = fb->width;
    height = fb->height;
    header_h = height / 8;
    footer_h = height / 7;
    gap = width / 40;
    footer_w = (width - (gap * 4)) / 3;
    footer_y = height - footer_h - gap;

    a90_draw_clear(fb, 0x080808);
    a90_draw_rect(fb, 0, 0, width, header_h, 0x2a2a2a);
    a90_draw_rect(fb, gap, gap, width / 5, gap / 2 + 6, 0x0090ca);
    a90_draw_rect(fb, gap, footer_y, footer_w, footer_h, 0x202020);
    a90_draw_rect(fb, gap * 2 + footer_w, footer_y, footer_w, footer_h, 0x0090ca);
    a90_draw_rect(fb, gap * 3 + footer_w * 2, footer_y, footer_w, footer_h, 0x202020);
}

static void a90_draw_block_t(struct a90_fb *fb,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t stem_x = x + ((width - stroke) / 2);
    a90_draw_rect(fb, x, y, width, stroke, color);
    a90_draw_rect(fb, stem_x, y, stroke, height, color);
}

static void a90_draw_block_e(struct a90_fb *fb,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    a90_draw_rect(fb, x, y, stroke, height, color);
    a90_draw_rect(fb, x, y, width, stroke, color);
    a90_draw_rect(fb, x, mid_y, width - stroke / 2, stroke, color);
    a90_draw_rect(fb, x, y + height - stroke, width, stroke, color);
}

static void a90_draw_block_s(struct a90_fb *fb,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    a90_draw_rect(fb, x, y, width, stroke, color);
    a90_draw_rect(fb, x, y, stroke, mid_y - y + stroke, color);
    a90_draw_rect(fb, x, mid_y, width, stroke, color);
    a90_draw_rect(fb, x + width - stroke, mid_y, stroke, y + height - mid_y, color);
    a90_draw_rect(fb, x, y + height - stroke, width, stroke, color);
}

void a90_draw_giant_test_probe(struct a90_fb *fb) {
    uint32_t width;
    uint32_t height;
    uint32_t border;
    uint32_t stroke;
    uint32_t letter_h;
    uint32_t t_w;
    uint32_t e_w;
    uint32_t s_w;
    uint32_t gap;
    uint32_t start_x;
    uint32_t start_y;
    uint32_t label_h;

    if (fb == NULL) {
        return;
    }

    width = fb->width;
    height = fb->height;
    border = width / 20;
    stroke = width / 22;
    letter_h = (height * 11) / 32;
    t_w = stroke * 5;
    e_w = stroke * 4;
    s_w = stroke * 4;
    gap = stroke;
    label_h = stroke * 2;

    if (stroke < 18) {
        stroke = 18;
    }
    if (letter_h < stroke * 7) {
        letter_h = stroke * 7;
    }
    start_x = (width - (t_w + e_w + s_w + t_w + gap * 3)) / 2;
    start_y = (height - letter_h) / 2;

    a90_draw_clear(fb, 0x000000);
    a90_draw_rect(fb, 0, 0, width, border, 0xffffff);
    a90_draw_rect(fb, 0, height - border, width, border, 0xffffff);
    a90_draw_rect(fb, 0, 0, border, height, 0xffffff);
    a90_draw_rect(fb, width - border, 0, border, height, 0xffffff);
    a90_draw_rect(fb, border * 2, border * 2, width - border * 4, label_h, 0x00a0ff);
    a90_draw_rect(fb, border * 2, height - border * 3, width - border * 4, stroke, 0xffa000);

    a90_draw_block_t(fb, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
    start_x += t_w + gap;
    a90_draw_block_e(fb, start_x, start_y, stroke, e_w, letter_h, 0xffffff);
    start_x += e_w + gap;
    a90_draw_block_s(fb, start_x, start_y, stroke, s_w, letter_h, 0xffffff);
    start_x += s_w + gap;
    a90_draw_block_t(fb, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
}
