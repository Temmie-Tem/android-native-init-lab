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
    int crtc_index;
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
    bool atomic_attempted;
    uint32_t plane_id;
    uint32_t fb_id;
    uint32_t crtc_id;
    uint32_t atomic_prop_count;
    uint32_t plane_count;
    uint32_t compatible_count;
    uint32_t idle_xbgr_count;
    int stage;
    int crtc_index;
    int used_cached_crtc_index;
    int universal_cap_rc;
    int atomic_cap_rc;
    int fetch_resources_rc;
    int atomic_props_rc;
    int atomic_commit_rc;
    int legacy_setplane_rc;
    int rc;
};

#define A90_KMS_SCALED_PLANE_STAGE_NONE 0
#define A90_KMS_SCALED_PLANE_STAGE_INPUT 1
#define A90_KMS_SCALED_PLANE_STAGE_CLIENT_CAPS 2
#define A90_KMS_SCALED_PLANE_STAGE_FETCH_RESOURCES 3
#define A90_KMS_SCALED_PLANE_STAGE_FIND_CRTC 4
#define A90_KMS_SCALED_PLANE_STAGE_FETCH_PLANES 5
#define A90_KMS_SCALED_PLANE_STAGE_SCAN_PLANES 6
#define A90_KMS_SCALED_PLANE_STAGE_CREATE_DUMB 7
#define A90_KMS_SCALED_PLANE_STAGE_ADDFB2 8
#define A90_KMS_SCALED_PLANE_STAGE_MAP_DUMB 9
#define A90_KMS_SCALED_PLANE_STAGE_MMAP 10
#define A90_KMS_SCALED_PLANE_STAGE_SETPLANE 11
#define A90_KMS_SCALED_PLANE_STAGE_PRESENTED 12
#define A90_KMS_SCALED_PLANE_STAGE_ATOMIC_PROPS 13
#define A90_KMS_SCALED_PLANE_STAGE_ATOMIC_COMMIT 14

int a90_kms_begin_frame(uint32_t color);
int a90_kms_begin_frame_no_clear(void);
int a90_kms_present(const char *label, bool verbose);
int a90_kms_present_pageflip(const char *label, int timeout_ms, struct a90_kms_flip_result *result);
const char *a90_kms_scaled_plane_stage_name(int stage);
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
