#ifndef A90_DRAW_H
#define A90_DRAW_H

#include <stdint.h>
#include "a90_kms.h"

void a90_draw_clear(struct a90_fb *fb, uint32_t color);
void a90_draw_rect(struct a90_fb *fb,
                   uint32_t x,
                   uint32_t y,
                   uint32_t width,
                   uint32_t height,
                   uint32_t color);
void a90_draw_text(struct a90_fb *fb,
                   uint32_t x,
                   uint32_t y,
                   const char *text,
                   uint32_t color,
                   uint32_t scale);
void a90_draw_text_fit(struct a90_fb *fb,
                       uint32_t x,
                       uint32_t y,
                       const char *text,
                       uint32_t color,
                       uint32_t scale,
                       uint32_t max_width);
void a90_draw_rect_outline(struct a90_fb *fb,
                           uint32_t x,
                           uint32_t y,
                           uint32_t width,
                           uint32_t height,
                           uint32_t thickness,
                           uint32_t color);
void a90_draw_boot_frame(struct a90_fb *fb);
void a90_draw_giant_test_probe(struct a90_fb *fb);

#endif
