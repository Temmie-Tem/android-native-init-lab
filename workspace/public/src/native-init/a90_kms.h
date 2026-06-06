#ifndef A90_KMS_H
#define A90_KMS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct a90_fb {
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    void *pixels;
    size_t size;
};

struct a90_kms_info {
    bool initialized;
    uint32_t width;
    uint32_t height;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t current_buffer;
};

int a90_kms_begin_frame(uint32_t color);
int a90_kms_present(const char *label, bool verbose);
struct a90_fb *a90_kms_framebuffer(void);
void a90_kms_info(struct a90_kms_info *info);
int a90_kms_probe(bool verbose);

#endif
