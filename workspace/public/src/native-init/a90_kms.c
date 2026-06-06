#include "a90_kms.h"

#include "a90_console.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

struct a90_kms_state {
    int fd;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id[2];
    uint32_t handle[2];
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    size_t map_size;
    void *map[2];
    uint32_t current_buffer;
    struct drm_mode_modeinfo mode;
};

static struct a90_kms_state kms_state = {
    .fd = -1,
    .map = { MAP_FAILED, MAP_FAILED },
};

static struct a90_fb kms_fb;

static int drm_ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);

    return rc;
}

static int kms_ensure_char_device_path(const char *sysfs_dev_path,
                                       const char *dev_dir,
                                       const char *name,
                                       char *out,
                                       size_t out_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;
    struct stat st;

    if (snprintf(out, out_size, "%s/%s", dev_dir, name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (stat(out, &st) == 0 && S_ISCHR(st.st_mode)) {
        return 0;
    }

    if (read_trimmed_text_file(sysfs_dev_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }
    if (sscanf(dev_info, "%u:%u", &major_num, &minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    if (ensure_dir(dev_dir, 0755) < 0) {
        return -1;
    }
    if (mknod(out, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }

    return 0;
}

static int kms_ensure_card0_path(char *out, size_t out_size) {
    return kms_ensure_char_device_path("/sys/class/drm/card0/dev",
                                       "/dev/dri",
                                       "card0",
                                       out,
                                       out_size);
}

static const char *drm_connection_name(uint32_t status) {
    if (status == 1) {
        return "connected";
    }
    if (status == 2) {
        return "disconnected";
    }
    if (status == 3) {
        return "unknown";
    }
    return "invalid";
}

static int drm_get_cap_value(int fd, uint64_t capability, uint64_t *value) {
    struct drm_get_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    if (drm_ioctl_retry(fd, DRM_IOCTL_GET_CAP, &cap) < 0) {
        return -1;
    }

    *value = cap.value;
    return 0;
}

static int drm_fetch_resources(int fd,
                               struct drm_mode_card_res *res,
                               uint32_t **crtcs_out,
                               uint32_t **connectors_out,
                               uint32_t **encoders_out) {
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;

    memset(res, 0, sizeof(*res));
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        return -1;
    }

    if (res->count_crtcs > 0) {
        crtcs = calloc(res->count_crtcs, sizeof(*crtcs));
        if (crtcs == NULL) {
            goto oom;
        }
        res->crtc_id_ptr = (uintptr_t)crtcs;
    }

    if (res->count_connectors > 0) {
        connectors = calloc(res->count_connectors, sizeof(*connectors));
        if (connectors == NULL) {
            goto oom;
        }
        res->connector_id_ptr = (uintptr_t)connectors;
    }

    if (res->count_encoders > 0) {
        encoders = calloc(res->count_encoders, sizeof(*encoders));
        if (encoders == NULL) {
            goto oom;
        }
        res->encoder_id_ptr = (uintptr_t)encoders;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        free(crtcs);
        free(connectors);
        free(encoders);
        return -1;
    }

    *crtcs_out = crtcs;
    *connectors_out = connectors;
    *encoders_out = encoders;
    return 0;

oom:
    free(crtcs);
    free(connectors);
    free(encoders);
    errno = ENOMEM;
    return -1;
}

static int drm_fetch_connector(int fd,
                               uint32_t connector_id,
                               struct drm_mode_get_connector *conn,
                               struct drm_mode_modeinfo **modes_out,
                               uint32_t **encoders_out) {
    struct drm_mode_modeinfo *modes = NULL;
    uint32_t *encoders = NULL;
    uint32_t *props = NULL;
    uint64_t *prop_values = NULL;
    struct drm_mode_modeinfo first_mode;

    memset(conn, 0, sizeof(*conn));
    conn->connector_id = connector_id;
    memset(&first_mode, 0, sizeof(first_mode));
    conn->count_modes = 1;
    conn->modes_ptr = (uintptr_t)&first_mode;
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        return -1;
    }

    if (conn->count_modes > 0) {
        modes = calloc(conn->count_modes, sizeof(*modes));
        if (modes == NULL) {
            goto oom;
        }
        conn->modes_ptr = (uintptr_t)modes;
    }

    if (conn->count_encoders > 0) {
        encoders = calloc(conn->count_encoders, sizeof(*encoders));
        if (encoders == NULL) {
            goto oom;
        }
        conn->encoders_ptr = (uintptr_t)encoders;
    }

    if (conn->count_props > 0) {
        props = calloc(conn->count_props, sizeof(*props));
        prop_values = calloc(conn->count_props, sizeof(*prop_values));
        if (props == NULL || prop_values == NULL) {
            goto oom;
        }
        conn->props_ptr = (uintptr_t)props;
        conn->prop_values_ptr = (uintptr_t)prop_values;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        free(modes);
        free(encoders);
        free(props);
        free(prop_values);
        return -1;
    }

    *modes_out = modes;
    *encoders_out = encoders;
    free(props);
    free(prop_values);
    return 0;

oom:
    free(modes);
    free(encoders);
    free(props);
    free(prop_values);
    errno = ENOMEM;
    return -1;
}

static int drm_pick_crtc_id(const struct drm_mode_get_encoder *encoder,
                            const uint32_t *crtcs,
                            uint32_t count_crtcs,
                            uint32_t *crtc_id_out) {
    uint32_t index;

    if (encoder->crtc_id != 0) {
        *crtc_id_out = encoder->crtc_id;
        return 0;
    }

    for (index = 0; index < count_crtcs; ++index) {
        if ((encoder->possible_crtcs & (1U << index)) != 0) {
            *crtc_id_out = crtcs[index];
            return 0;
        }
    }

    errno = ENODEV;
    return -1;
}

static int drm_find_mode_index(const struct drm_mode_modeinfo *modes, uint32_t count_modes) {
    uint32_t index;

    for (index = 0; index < count_modes; ++index) {
        if ((modes[index].type & DRM_MODE_TYPE_PREFERRED) != 0) {
            return (int)index;
        }
    }

    return (count_modes > 0) ? 0 : -1;
}

static int kms_find_output(int fd,
                           bool verbose,
                           uint32_t *connector_id_out,
                           uint32_t *encoder_id_out,
                           uint32_t *crtc_id_out,
                           struct drm_mode_modeinfo *mode_out) {
    struct drm_mode_card_res res;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t index;
    int rc = -1;

    if (drm_fetch_resources(fd, &res, &crtcs, &connectors, &encoders) < 0) {
        return -1;
    }

    if (verbose) {
        a90_console_printf("kmsprobe: crtcs=%u connectors=%u encoders=%u size=%ux%u..%ux%u\r\n",
                res.count_crtcs, res.count_connectors, res.count_encoders,
                res.min_width, res.min_height, res.max_width, res.max_height);
    }

    for (index = 0; index < res.count_connectors; ++index) {
        struct drm_mode_get_connector conn;
        struct drm_mode_modeinfo *modes = NULL;
        uint32_t *connector_encoders = NULL;
        int mode_index;

        if (drm_fetch_connector(fd, connectors[index], &conn, &modes, &connector_encoders) < 0) {
            if (verbose) {
                a90_console_printf("kmsprobe: connector %u: %s\r\n",
                        connectors[index], strerror(errno));
            }
            continue;
        }

        if (verbose) {
            a90_console_printf("kmsprobe: connector=%u type=%u status=%s encoders=%u modes=%u current_encoder=%u\r\n",
                    conn.connector_id,
                    conn.connector_type,
                    drm_connection_name(conn.connection),
                    conn.count_encoders,
                    conn.count_modes,
                    conn.encoder_id);
        }

        mode_index = drm_find_mode_index(modes, conn.count_modes);
        if (conn.connection == 1 && mode_index >= 0) {
            struct drm_mode_get_encoder encoder;
            uint32_t encoder_id = conn.encoder_id;
            uint32_t crtc_id;

            if (encoder_id == 0 && conn.count_encoders > 0) {
                encoder_id = connector_encoders[0];
            }

            memset(&encoder, 0, sizeof(encoder));
            encoder.encoder_id = encoder_id;

            if (encoder_id == 0 || drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETENCODER, &encoder) < 0) {
                if (verbose) {
                    a90_console_printf("kmsprobe: encoder lookup failed for connector %u: %s\r\n",
                            conn.connector_id, strerror(errno));
                }
                free(modes);
                free(connector_encoders);
                continue;
            }

            if (drm_pick_crtc_id(&encoder, crtcs, res.count_crtcs, &crtc_id) < 0) {
                if (verbose) {
                    a90_console_printf("kmsprobe: no CRTC for encoder %u\r\n", encoder.encoder_id);
                }
                free(modes);
                free(connector_encoders);
                continue;
            }

            *connector_id_out = conn.connector_id;
            *encoder_id_out = encoder.encoder_id;
            *crtc_id_out = crtc_id;
            *mode_out = modes[mode_index];
            rc = 0;

            if (verbose) {
                a90_console_printf("kmsprobe: selected connector=%u encoder=%u crtc=%u mode=%s\r\n",
                        *connector_id_out, *encoder_id_out, *crtc_id_out, mode_out->name);
            }

            free(modes);
            free(connector_encoders);
            break;
        }

        free(modes);
        free(connector_encoders);
    }

    free(crtcs);
    free(connectors);
    free(encoders);

    if (rc < 0 && errno == 0) {
        errno = ENODEV;
    }

    return rc;
}

static int kms_open_card(bool verbose, char *node_path, size_t node_path_size) {
    int fd;

    if (kms_ensure_card0_path(node_path, node_path_size) < 0) {
        return -1;
    }

    fd = open(node_path, O_RDWR);
    if (fd < 0) {
        return -1;
    }
    if (fd >= 0 && fd < STDERR_FILENO + 1) {
        int protected_fd = fcntl(fd, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
        if (protected_fd < 0) {
            close(fd);
            return -1;
        }
        close(fd);
        fd = protected_fd;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_SET_MASTER, NULL) < 0) {
        if (errno != EBUSY && errno != EINVAL) {
            if (verbose) {
                a90_console_printf("kmsprobe: SET_MASTER failed: %s\r\n", strerror(errno));
            }
        }
    }

    return fd;
}

static void *kms_active_map(void) {
    return kms_state.map[kms_state.current_buffer];
}

static uint32_t kms_pack_rgb_for_xbgr8888(uint32_t color) {
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;

    return ((uint32_t)blue << 16) | ((uint32_t)green << 8) | red;
}

static void kms_fill_color(uint32_t color) {
    size_t y;
    uint32_t pixel = kms_pack_rgb_for_xbgr8888(color);
    void *map = kms_active_map();

    if (map == NULL || map == MAP_FAILED) {
        return;
    }

    for (y = 0; y < kms_state.height; ++y) {
        uint32_t *row = (uint32_t *)((char *)map + (y * kms_state.stride));
        size_t x;

        for (x = 0; x < kms_state.width; ++x) {
            row[x] = pixel;
        }
    }
}

static void kms_update_fb(void) {
    kms_fb.width = kms_state.width;
    kms_fb.height = kms_state.height;
    kms_fb.stride = kms_state.stride;
    kms_fb.pixels = kms_active_map();
    kms_fb.size = kms_state.map_size;
}

int a90_kms_begin_frame(uint32_t color) {
    struct drm_mode_create_dumb create;
    struct drm_mode_fb_cmd2 addfb2;
    struct drm_mode_map_dumb map_dumb;
    char node_path[4096];
    int fd;
    uint64_t dumb_cap = 0;
    uint64_t preferred_depth = 0;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    struct drm_mode_modeinfo mode;
    void *map;
    uint32_t next_buffer;

    if (kms_state.fd >= 0 &&
        kms_state.map[0] != MAP_FAILED &&
        kms_state.map[1] != MAP_FAILED) {
        next_buffer = 1U - kms_state.current_buffer;
        kms_state.current_buffer = next_buffer;
        kms_fill_color(color);
        kms_update_fb();
        return 0;
    }

    fd = kms_open_card(false, node_path, sizeof(node_path));
    if (fd < 0) {
        a90_console_printf("kmssolid: open card0: %s\r\n", strerror(errno));
        return -1;
    }

    if (drm_get_cap_value(fd, DRM_CAP_DUMB_BUFFER, &dumb_cap) < 0 || dumb_cap == 0) {
        a90_console_printf("kmssolid: DRM_CAP_DUMB_BUFFER unavailable\r\n");
        close(fd);
        return -1;
    }

    if (drm_get_cap_value(fd, DRM_CAP_DUMB_PREFERRED_DEPTH, &preferred_depth) < 0) {
        preferred_depth = 24;
    }
    (void)preferred_depth;

    if (kms_find_output(fd, false, &connector_id, &encoder_id, &crtc_id, &mode) < 0) {
        a90_console_printf("kmssolid: no connected output: %s\r\n", strerror(errno));
        close(fd);
        return -1;
    }

    for (next_buffer = 0; next_buffer < 2; ++next_buffer) {
        memset(&create, 0, sizeof(create));
        create.width = mode.hdisplay;
        create.height = mode.vdisplay;
        create.bpp = 32;

        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0) {
            a90_console_printf("kmssolid: CREATE_DUMB[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        memset(&addfb2, 0, sizeof(addfb2));
        addfb2.width = create.width;
        addfb2.height = create.height;
        addfb2.pixel_format = DRM_FORMAT_XBGR8888;
        addfb2.handles[0] = create.handle;
        addfb2.pitches[0] = create.pitch;
        addfb2.offsets[0] = 0;

        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_ADDFB2, &addfb2) < 0) {
            a90_console_printf("kmssolid: ADDFB2[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        memset(&map_dumb, 0, sizeof(map_dumb));
        map_dumb.handle = create.handle;
        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_MAP_DUMB, &map_dumb) < 0) {
            a90_console_printf("kmssolid: MAP_DUMB[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        map = mmap(NULL, create.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (off_t)map_dumb.offset);
        if (map == MAP_FAILED) {
            a90_console_printf("kmssolid: mmap[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        kms_state.handle[next_buffer] = create.handle;
        kms_state.fb_id[next_buffer] = addfb2.fb_id;
        kms_state.map[next_buffer] = map;
        kms_state.stride = create.pitch;
        kms_state.map_size = create.size;
    }

    kms_state.fd = fd;
    kms_state.connector_id = connector_id;
    kms_state.encoder_id = encoder_id;
    kms_state.crtc_id = crtc_id;
    kms_state.width = create.width;
    kms_state.height = create.height;
    kms_state.current_buffer = 0;
    kms_state.mode = mode;

    kms_fill_color(color);
    kms_update_fb();
    a90_console_printf("kms: prepared %s %ux%u connector=%u crtc=%u\r\n",
            node_path, kms_state.width, kms_state.height,
            kms_state.connector_id, kms_state.crtc_id);
    return 0;
}

int a90_kms_present(const char *label, bool verbose) {
    struct drm_mode_crtc setcrtc;
    uint32_t connector_list[1];

    if (kms_state.fd < 0 ||
        kms_state.map[kms_state.current_buffer] == MAP_FAILED) {
        errno = ENODEV;
        return -1;
    }

    connector_list[0] = kms_state.connector_id;
    memset(&setcrtc, 0, sizeof(setcrtc));
    setcrtc.crtc_id = kms_state.crtc_id;
    setcrtc.fb_id = kms_state.fb_id[kms_state.current_buffer];
    setcrtc.set_connectors_ptr = (uintptr_t)connector_list;
    setcrtc.count_connectors = 1;
    setcrtc.mode = kms_state.mode;
    setcrtc.mode_valid = 1;

    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_SETCRTC, &setcrtc) < 0) {
        a90_console_printf("%s: SETCRTC failed: %s\r\n", label, strerror(errno));
        return -1;
    }

    if (verbose) {
        a90_console_printf("%s: presented framebuffer %ux%u on crtc=%u\r\n",
                label, kms_state.width, kms_state.height, kms_state.crtc_id);
    }
    return 0;
}

struct a90_fb *a90_kms_framebuffer(void) {
    if (kms_state.fd < 0 || kms_state.map[kms_state.current_buffer] == MAP_FAILED) {
        return NULL;
    }
    kms_update_fb();
    return &kms_fb;
}

void a90_kms_info(struct a90_kms_info *info) {
    if (info == NULL) {
        return;
    }

    memset(info, 0, sizeof(*info));
    info->initialized = kms_state.fd >= 0 &&
                        kms_state.map[kms_state.current_buffer] != MAP_FAILED;
    info->width = kms_state.width;
    info->height = kms_state.height;
    info->connector_id = kms_state.connector_id;
    info->encoder_id = kms_state.encoder_id;
    info->crtc_id = kms_state.crtc_id;
    info->fb_id = kms_state.fb_id[kms_state.current_buffer];
    info->current_buffer = kms_state.current_buffer;
}

int a90_kms_probe(bool verbose) {
    char node_path[4096];
    int fd;
    int result = 0;
    uint64_t dumb_cap = 0;
    uint64_t preferred_depth = 0;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    struct drm_mode_modeinfo mode;

    fd = kms_open_card(verbose, node_path, sizeof(node_path));
    if (fd < 0) {
        a90_console_printf("kmsprobe: open card0: %s\r\n", strerror(errno));
        return negative_errno_or(ENODEV);
    }

    a90_console_printf("kmsprobe: node=%s\r\n", node_path);
    if (drm_get_cap_value(fd, DRM_CAP_DUMB_BUFFER, &dumb_cap) == 0) {
        a90_console_printf("kmsprobe: DRM_CAP_DUMB_BUFFER=%llu\r\n",
                (unsigned long long)dumb_cap);
    }
    if (drm_get_cap_value(fd, DRM_CAP_DUMB_PREFERRED_DEPTH, &preferred_depth) == 0) {
        a90_console_printf("kmsprobe: DRM_CAP_DUMB_PREFERRED_DEPTH=%llu\r\n",
                (unsigned long long)preferred_depth);
    }

    if (kms_find_output(fd, verbose, &connector_id, &encoder_id, &crtc_id, &mode) == 0) {
        a90_console_printf("kmsprobe: chosen connector=%u encoder=%u crtc=%u mode=%s %ux%u@%u\r\n",
                connector_id, encoder_id, crtc_id,
                mode.name, mode.hdisplay, mode.vdisplay, mode.vrefresh);
    } else {
        a90_console_printf("kmsprobe: no usable display path: %s\r\n", strerror(errno));
        result = negative_errno_or(ENODEV);
    }

    close(fd);
    return result;
}
