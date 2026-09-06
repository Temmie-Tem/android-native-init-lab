/* H0 visible layout proposal. Pure pixel generation; no device I/O.
 * Not included in consumed P350 or any flashable candidate.
 * The caller supplies a 1080x2340 XRGB8888 buffer and its row stride.
 */
#include <stddef.h>
#include <stdint.h>

#define VISIBLE_WIDTH 1080U
#define VISIBLE_HEIGHT 2340U
static const uint16_t visible_glyph[16] = {
    0x7b6f,0x2492,0x73e7,0x73cf,0x5bc9,0x79cf,0x79ef,0x7249,
    0x7bef,0x7bcf,0x7bed,0x6bae,0x7927,0x6b6e,0x79e7,0x79e4
};
static int visible_hex(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}
static void visible_digit(uint32_t *pixels, size_t stride, unsigned x,
                          unsigned y, unsigned value, unsigned scale) {
    for (unsigned row = 0; row < 5; ++row)
        for (unsigned col = 0; col < 3; ++col)
            if (visible_glyph[value] & (1U << (14 - row * 3 - col)))
                for (unsigned dy = 0; dy < scale; ++dy)
                    for (unsigned dx = 0; dx < scale; ++dx)
                        pixels[(y + row * scale + dy) * stride + x + col * scale + dx] = 0x00000000;
}
int s22plus_display_paint_visible(uint32_t *pixels, size_t pixel_count,
                                  size_t stride, const char *run_id, unsigned frame) {
    if (!pixels || !run_id || stride < VISIBLE_WIDTH || stride > 4096 ||
        pixel_count < stride * VISIBLE_HEIGHT || frame > 9) return -1;
    for (unsigned i = 0; i < 32; ++i)
        if (visible_hex(run_id[i]) < 0) return -1;
    if (run_id[32] != '\0') return -1;
    for (size_t i = 0; i < stride * VISIBLE_HEIGHT; ++i) pixels[i] = 0x00ffffff;
    /* Large central 00..09: 660 pixels of ink width, 550 pixels high. */
    visible_digit(pixels, stride, 150, 650, 0, 110);
    visible_digit(pixels, stride, 600, 650, frame, 110);
    /* Large lower-half block, always visible, moving without full-screen flashes. */
    for (unsigned y = 1420; y < 1740; ++y)
        for (unsigned x = 60 + frame * 85; x < 240 + frame * 85; ++x)
            pixels[y * stride + x] = 0x00009640;
    /* Run identity is secondary, in two footer rows. */
    for (unsigned i = 0; i < 32; ++i)
        visible_digit(pixels, stride, 60 + (i % 16) * 60,
                      2020 + (i / 16) * 80, (unsigned)visible_hex(run_id[i]), 8);
    return 0;
}

#ifdef S22_DISPLAY_LAYOUT_PREVIEW
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    if (argc != 2 || argv[1][0] < '0' || argv[1][0] > '9' || argv[1][1]) return 2;
    const size_t count = VISIBLE_WIDTH * VISIBLE_HEIGHT;
    uint32_t *pixels = malloc(count * sizeof(*pixels));
    if (!pixels) return 2;
    if (s22plus_display_paint_visible(pixels, count, VISIBLE_WIDTH,
            "0123456789abcdef0123456789abcdef", (unsigned)(argv[1][0] - '0'))) {
        free(pixels); return 2;
    }
    if (printf("P6\n%u %u\n255\n", VISIBLE_WIDTH, VISIBLE_HEIGHT) < 0) {
        free(pixels); return 2;
    }
    for (size_t i = 0; i < count; ++i) {
        unsigned char rgb[3] = {(unsigned char)(pixels[i] >> 16),
                               (unsigned char)(pixels[i] >> 8), (unsigned char)pixels[i]};
        if (fwrite(rgb, 1, 3, stdout) != 3) { free(pixels); return 2; }
    }
    free(pixels);
    return fflush(stdout) ? 2 : 0;
}
#endif
