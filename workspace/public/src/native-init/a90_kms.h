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
    uint32_t stride;
    size_t map_size;
    uint32_t pixel_format;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t current_buffer;
};

struct a90_kms_flip_result {
    bool event_received;
    uint32_t sequence;
    uint32_t crtc_id;
    uint64_t timestamp_us;
};

struct a90_kms_scaled_plane_result {
    bool attempted;
    bool presented;
    uint32_t plane_id;
    uint32_t fb_id;
    uint32_t crtc_id;
    int rc;
};

int a90_kms_begin_frame(uint32_t color);
int a90_kms_begin_frame_no_clear(void);
int a90_kms_present(const char *label, bool verbose);
int a90_kms_present_pageflip(const char *label, int timeout_ms, struct a90_kms_flip_result *result);
int a90_kms_present_scaled_plane_xbgr8888(const uint32_t *source,
                                          uint32_t source_width,
                                          uint32_t source_height,
                                          uint32_t source_stride,
                                          uint32_t dst_x,
                                          uint32_t dst_y,
                                          uint32_t dst_width,
                                          uint32_t dst_height,
                                          struct a90_kms_scaled_plane_result *result);
int a90_kms_disable_scaled_plane(void);
struct a90_fb *a90_kms_framebuffer(void);
void a90_kms_info(struct a90_kms_info *info);
int a90_kms_probe(bool verbose);

#endif
