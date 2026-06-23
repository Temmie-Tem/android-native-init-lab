#include "a90_kms.h"

#include "a90_console.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
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
    int crtc_index;
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

struct a90_kms_plane_select_result {
    int stage;
    int crtc_index;
    int used_cached_crtc_index;
    int universal_cap_rc;
    int atomic_cap_rc;
    int fetch_resources_rc;
    uint32_t plane_count;
    uint32_t compatible_count;
    uint32_t idle_xbgr_count;
};

struct a90_kms_atomic_plane_props {
    bool fetched;
    bool ready;
    uint32_t count;
    uint32_t fb_id;
    uint32_t crtc_id;
    uint32_t crtc_x;
    uint32_t crtc_y;
    uint32_t crtc_w;
    uint32_t crtc_h;
    uint32_t src_x;
    uint32_t src_y;
    uint32_t src_w;
    uint32_t src_h;
    int rc;
};

struct a90_kms_scaled_plane_state {
    uint32_t plane_id;
    uint32_t fb_id[2];
    uint32_t handle[2];
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    size_t map_size;
    void *map[2];
    uint32_t current_buffer;
    bool enabled;
    struct a90_kms_plane_select_result select;
    bool has_select;
    struct a90_kms_atomic_plane_props atomic_props;
};

static struct a90_kms_state kms_state = {
    .fd = -1,
    .crtc_index = -1,
    .map = { MAP_FAILED, MAP_FAILED },
};

static struct a90_kms_scaled_plane_state kms_scaled_plane = {
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

static int drm_set_client_cap_value(int fd, uint64_t capability, uint64_t value) {
    struct drm_set_client_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    cap.value = value;
    if (drm_ioctl_retry(fd, DRM_IOCTL_SET_CLIENT_CAP, &cap) < 0) {
        return -1;
    }
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
                            uint32_t *crtc_id_out,
                            int *crtc_index_out) {
    uint32_t index;

    if (encoder->crtc_id != 0) {
        for (index = 0; index < count_crtcs; ++index) {
            if (crtcs[index] == encoder->crtc_id) {
                *crtc_id_out = encoder->crtc_id;
                if (crtc_index_out != NULL) {
                    *crtc_index_out = (int)index;
                }
                return 0;
            }
        }
        errno = ENODEV;
        return -1;
    }

    for (index = 0; index < count_crtcs; ++index) {
        if ((encoder->possible_crtcs & (1U << index)) != 0) {
            *crtc_id_out = crtcs[index];
            if (crtc_index_out != NULL) {
                *crtc_index_out = (int)index;
            }
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
                           int *crtc_index_out,
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
            int crtc_index;

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

            if (drm_pick_crtc_id(&encoder, crtcs, res.count_crtcs, &crtc_id, &crtc_index) < 0) {
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
            if (crtc_index_out != NULL) {
                *crtc_index_out = crtc_index;
            }
            *mode_out = modes[mode_index];
            rc = 0;

            if (verbose) {
                a90_console_printf("kmsprobe: selected connector=%u encoder=%u crtc=%u crtc_index=%d mode=%s\r\n",
                        *connector_id_out, *encoder_id_out, *crtc_id_out,
                        crtc_index, mode_out->name);
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

static int drm_find_crtc_index(const uint32_t *crtcs, uint32_t count_crtcs, uint32_t crtc_id) {
    uint32_t index;

    for (index = 0; index < count_crtcs; ++index) {
        if (crtcs[index] == crtc_id) {
            return (int)index;
        }
    }
    errno = ENODEV;
    return -1;
}

static int drm_fetch_plane_ids(int fd, uint32_t **plane_ids_out, uint32_t *count_out) {
    struct drm_mode_get_plane_res pres;
    uint32_t *plane_ids = NULL;

    memset(&pres, 0, sizeof(pres));
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &pres) < 0) {
        return -1;
    }
    if (pres.count_planes > 0) {
        plane_ids = calloc(pres.count_planes, sizeof(*plane_ids));
        if (plane_ids == NULL) {
            errno = ENOMEM;
            return -1;
        }
        pres.plane_id_ptr = (uintptr_t)plane_ids;
    }
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &pres) < 0) {
        free(plane_ids);
        return -1;
    }
    *plane_ids_out = plane_ids;
    *count_out = pres.count_planes;
    return 0;
}

static int drm_fetch_plane(int fd,
                           uint32_t plane_id,
                           struct drm_mode_get_plane *plane,
                           uint32_t **formats_out) {
    uint32_t *formats = NULL;

    memset(plane, 0, sizeof(*plane));
    plane->plane_id = plane_id;
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANE, plane) < 0) {
        return -1;
    }
    if (plane->count_format_types > 0) {
        formats = calloc(plane->count_format_types, sizeof(*formats));
        if (formats == NULL) {
            errno = ENOMEM;
            return -1;
        }
        plane->format_type_ptr = (uintptr_t)formats;
    }
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANE, plane) < 0) {
        free(formats);
        return -1;
    }
    *formats_out = formats;
    return 0;
}

static bool drm_plane_has_format(const uint32_t *formats, uint32_t count, uint32_t wanted) {
    uint32_t index;

    for (index = 0; index < count; ++index) {
        if (formats[index] == wanted) {
            return true;
        }
    }
    return false;
}

static int drm_set_client_cap_result(int fd, uint64_t capability, uint64_t value) {
    if (drm_set_client_cap_value(fd, capability, value) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void drm_note_atomic_plane_prop(struct a90_kms_atomic_plane_props *props,
                                       uint32_t prop_id,
                                       const char *name) {
    if (props == NULL || name == NULL) {
        return;
    }
    if (strcmp(name, "FB_ID") == 0) {
        props->fb_id = prop_id;
    } else if (strcmp(name, "CRTC_ID") == 0) {
        props->crtc_id = prop_id;
    } else if (strcmp(name, "CRTC_X") == 0) {
        props->crtc_x = prop_id;
    } else if (strcmp(name, "CRTC_Y") == 0) {
        props->crtc_y = prop_id;
    } else if (strcmp(name, "CRTC_W") == 0) {
        props->crtc_w = prop_id;
    } else if (strcmp(name, "CRTC_H") == 0) {
        props->crtc_h = prop_id;
    } else if (strcmp(name, "SRC_X") == 0) {
        props->src_x = prop_id;
    } else if (strcmp(name, "SRC_Y") == 0) {
        props->src_y = prop_id;
    } else if (strcmp(name, "SRC_W") == 0) {
        props->src_w = prop_id;
    } else if (strcmp(name, "SRC_H") == 0) {
        props->src_h = prop_id;
    }
}

static bool kms_atomic_plane_props_ready(const struct a90_kms_atomic_plane_props *props) {
    return props != NULL &&
           props->fb_id != 0U &&
           props->crtc_id != 0U &&
           props->crtc_x != 0U &&
           props->crtc_y != 0U &&
           props->crtc_w != 0U &&
           props->crtc_h != 0U &&
           props->src_x != 0U &&
           props->src_y != 0U &&
           props->src_w != 0U &&
           props->src_h != 0U;
}

static int kms_fetch_atomic_plane_props(uint32_t plane_id,
                                        struct a90_kms_atomic_plane_props *props) {
    struct drm_mode_obj_get_properties obj_props;
    uint32_t *prop_ids = NULL;
    uint64_t *prop_values = NULL;
    uint32_t index;

    if (kms_state.fd < 0 || plane_id == 0U || props == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(props, 0, sizeof(*props));
    props->rc = -ENODEV;
    memset(&obj_props, 0, sizeof(obj_props));
    obj_props.obj_id = plane_id;
    obj_props.obj_type = DRM_MODE_OBJECT_PLANE;
    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &obj_props) < 0) {
        props->fetched = false;
        props->rc = negative_errno_or(EIO);
        return -1;
    }
    props->fetched = true;
    props->count = obj_props.count_props;
    if (obj_props.count_props == 0U) {
        errno = ENODEV;
        props->rc = -ENODEV;
        return -1;
    }
    prop_ids = calloc(obj_props.count_props, sizeof(*prop_ids));
    prop_values = calloc(obj_props.count_props, sizeof(*prop_values));
    if (prop_ids == NULL || prop_values == NULL) {
        free(prop_ids);
        free(prop_values);
        errno = ENOMEM;
        props->rc = -ENOMEM;
        return -1;
    }
    obj_props.props_ptr = (uintptr_t)prop_ids;
    obj_props.prop_values_ptr = (uintptr_t)prop_values;
    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &obj_props) < 0) {
        props->rc = negative_errno_or(EIO);
        free(prop_ids);
        free(prop_values);
        return -1;
    }
    for (index = 0; index < obj_props.count_props; ++index) {
        struct drm_mode_get_property prop;

        memset(&prop, 0, sizeof(prop));
        prop.prop_id = prop_ids[index];
        if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_GETPROPERTY, &prop) == 0) {
            drm_note_atomic_plane_prop(props, prop_ids[index], prop.name);
        }
    }
    free(prop_ids);
    free(prop_values);
    props->ready = kms_atomic_plane_props_ready(props);
    props->rc = props->ready ? 0 : -ENODEV;
    if (!props->ready) {
        errno = ENODEV;
        return -1;
    }
    return 0;
}

const char *a90_kms_scaled_plane_stage_name(int stage) {
    switch (stage) {
    case A90_KMS_SCALED_PLANE_STAGE_NONE:
        return "none";
    case A90_KMS_SCALED_PLANE_STAGE_INPUT:
        return "input";
    case A90_KMS_SCALED_PLANE_STAGE_CLIENT_CAPS:
        return "client-caps";
    case A90_KMS_SCALED_PLANE_STAGE_FETCH_RESOURCES:
        return "fetch-resources";
    case A90_KMS_SCALED_PLANE_STAGE_FIND_CRTC:
        return "find-crtc";
    case A90_KMS_SCALED_PLANE_STAGE_FETCH_PLANES:
        return "fetch-planes";
    case A90_KMS_SCALED_PLANE_STAGE_SCAN_PLANES:
        return "scan-planes";
    case A90_KMS_SCALED_PLANE_STAGE_CREATE_DUMB:
        return "create-dumb";
    case A90_KMS_SCALED_PLANE_STAGE_ADDFB2:
        return "addfb2";
    case A90_KMS_SCALED_PLANE_STAGE_MAP_DUMB:
        return "map-dumb";
    case A90_KMS_SCALED_PLANE_STAGE_MMAP:
        return "mmap";
    case A90_KMS_SCALED_PLANE_STAGE_SETPLANE:
        return "setplane";
    case A90_KMS_SCALED_PLANE_STAGE_PRESENTED:
        return "presented";
    case A90_KMS_SCALED_PLANE_STAGE_ATOMIC_PROPS:
        return "atomic-props";
    case A90_KMS_SCALED_PLANE_STAGE_ATOMIC_COMMIT:
        return "atomic-commit";
    default:
        return "unknown";
    }
}

static int kms_select_unused_scaled_plane(uint32_t *plane_id_out,
                                          struct a90_kms_plane_select_result *select) {
    struct drm_mode_card_res res;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t *plane_ids = NULL;
    uint32_t plane_count = 0;
    uint32_t index;
    int crtc_index;
    int rc = -1;

    if (select != NULL) {
        memset(select, 0, sizeof(*select));
        select->stage = A90_KMS_SCALED_PLANE_STAGE_INPUT;
        select->crtc_index = -1;
        select->universal_cap_rc = -ENODEV;
        select->atomic_cap_rc = -ENODEV;
        select->fetch_resources_rc = 0;
    }
    if (kms_state.fd < 0 || plane_id_out == NULL) {
        errno = ENODEV;
        return -1;
    }
    if (select != NULL) {
        select->stage = A90_KMS_SCALED_PLANE_STAGE_CLIENT_CAPS;
        select->universal_cap_rc = drm_set_client_cap_result(
            kms_state.fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1);
        select->atomic_cap_rc = drm_set_client_cap_result(
            kms_state.fd, DRM_CLIENT_CAP_ATOMIC, 1);
    } else {
        (void)drm_set_client_cap_value(kms_state.fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1);
        (void)drm_set_client_cap_value(kms_state.fd, DRM_CLIENT_CAP_ATOMIC, 1);
    }
    if (kms_state.crtc_index >= 0) {
        crtc_index = kms_state.crtc_index;
        if (select != NULL) {
            select->stage = A90_KMS_SCALED_PLANE_STAGE_FIND_CRTC;
            select->crtc_index = crtc_index;
            select->used_cached_crtc_index = 1;
        }
    } else {
        if (select != NULL) {
            select->stage = A90_KMS_SCALED_PLANE_STAGE_FETCH_RESOURCES;
        }
        if (drm_fetch_resources(kms_state.fd, &res, &crtcs, &connectors, &encoders) < 0) {
            if (select != NULL) {
                select->fetch_resources_rc = negative_errno_or(EIO);
            }
            return -1;
        }
        if (select != NULL) {
            select->stage = A90_KMS_SCALED_PLANE_STAGE_FIND_CRTC;
        }
        crtc_index = drm_find_crtc_index(crtcs, res.count_crtcs, kms_state.crtc_id);
        if (crtc_index < 0) {
            errno = ENODEV;
            goto out;
        }
        if (select != NULL) {
            select->crtc_index = crtc_index;
        }
    }
    if (select != NULL) {
        select->stage = A90_KMS_SCALED_PLANE_STAGE_FETCH_PLANES;
    }
    if (drm_fetch_plane_ids(kms_state.fd, &plane_ids, &plane_count) < 0) {
        goto out;
    }
    if (select != NULL) {
        select->stage = A90_KMS_SCALED_PLANE_STAGE_SCAN_PLANES;
        select->plane_count = plane_count;
    }
    for (index = 0; index < plane_count; ++index) {
        struct drm_mode_get_plane plane;
        uint32_t *formats = NULL;
        bool compatible;
        bool idle;
        bool xbgr;

        if (drm_fetch_plane(kms_state.fd, plane_ids[index], &plane, &formats) < 0) {
            free(formats);
            continue;
        }
        compatible = (plane.possible_crtcs & (1U << (unsigned int)crtc_index)) != 0U;
        idle = plane.crtc_id == 0 && plane.fb_id == 0;
        xbgr = drm_plane_has_format(formats, plane.count_format_types, DRM_FORMAT_XBGR8888);
        if (select != NULL && compatible) {
            select->compatible_count++;
            if (idle && xbgr) {
                select->idle_xbgr_count++;
            }
        }
        free(formats);
        if (compatible && idle && xbgr) {
            *plane_id_out = plane.plane_id;
            rc = 0;
            break;
        }
    }
    if (rc < 0) {
        errno = ENODEV;
    }

out:
    free(plane_ids);
    free(crtcs);
    free(connectors);
    free(encoders);
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

static uint64_t kms_monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return ((uint64_t)ts.tv_sec * 1000ULL) + ((uint64_t)ts.tv_nsec / 1000000ULL);
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
    int crtc_index;
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

    if (kms_find_output(fd, false, &connector_id, &encoder_id, &crtc_id, &crtc_index, &mode) < 0) {
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
    kms_state.crtc_index = crtc_index;
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

int a90_kms_begin_frame_no_clear(void) {
    uint32_t next_buffer;

    if (kms_state.fd < 0 ||
        kms_state.map[0] == MAP_FAILED ||
        kms_state.map[1] == MAP_FAILED) {
        return a90_kms_begin_frame(0x000000);
    }

    next_buffer = 1U - kms_state.current_buffer;
    kms_state.current_buffer = next_buffer;
    kms_update_fb();
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

static int kms_wait_pageflip_event(const char *label,
                                   int timeout_ms,
                                   struct a90_kms_flip_result *result) {
    uint8_t event_buffer[256];
    uint64_t deadline_ms;

    if (result != NULL) {
        memset(result, 0, sizeof(*result));
    }
    if (timeout_ms <= 0) {
        timeout_ms = 1000;
    }
    deadline_ms = kms_monotonic_ms() + (uint64_t)timeout_ms;

    for (;;) {
        struct pollfd pfd;
        uint64_t now_ms = kms_monotonic_ms();
        int remaining_ms;
        ssize_t bytes_read;
        size_t offset;

        if (now_ms >= deadline_ms) {
            errno = ETIMEDOUT;
            a90_console_printf("%s: PAGE_FLIP event timeout\r\n", label);
            return -1;
        }
        remaining_ms = (int)(deadline_ms - now_ms);
        if (remaining_ms <= 0) {
            remaining_ms = 1;
        }

        memset(&pfd, 0, sizeof(pfd));
        pfd.fd = kms_state.fd;
        pfd.events = POLLIN;
        if (poll(&pfd, 1, remaining_ms) < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("%s: PAGE_FLIP poll failed: %s\r\n", label, strerror(errno));
            return -1;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        bytes_read = read(kms_state.fd, event_buffer, sizeof(event_buffer));
        if (bytes_read < 0) {
            if (errno == EINTR || errno == EAGAIN) {
                continue;
            }
            a90_console_printf("%s: PAGE_FLIP event read failed: %s\r\n", label, strerror(errno));
            return -1;
        }
        offset = 0;
        while (offset + sizeof(struct drm_event) <= (size_t)bytes_read) {
            struct drm_event *event = (struct drm_event *)(void *)(event_buffer + offset);

            if (event->length < sizeof(struct drm_event) ||
                offset + event->length > (size_t)bytes_read) {
                break;
            }
            if (event->type == DRM_EVENT_FLIP_COMPLETE &&
                event->length >= sizeof(struct drm_event_vblank)) {
                struct drm_event_vblank *vblank =
                    (struct drm_event_vblank *)(void *)event;

                if (result != NULL) {
                    result->event_received = true;
                    result->sequence = vblank->sequence;
                    result->crtc_id = vblank->crtc_id;
                    result->timestamp_us = ((uint64_t)vblank->tv_sec * 1000000ULL) +
                                           (uint64_t)vblank->tv_usec;
                }
                return 0;
            }
            offset += event->length;
        }
    }
}

int a90_kms_present_pageflip(const char *label, int timeout_ms, struct a90_kms_flip_result *result) {
    struct drm_mode_crtc_page_flip flip;

    if (kms_state.fd < 0 ||
        kms_state.map[kms_state.current_buffer] == MAP_FAILED) {
        errno = ENODEV;
        return -1;
    }

    memset(&flip, 0, sizeof(flip));
    flip.crtc_id = kms_state.crtc_id;
    flip.fb_id = kms_state.fb_id[kms_state.current_buffer];
    flip.flags = DRM_MODE_PAGE_FLIP_EVENT;
    flip.user_data = (uint64_t)kms_state.current_buffer;

    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_PAGE_FLIP, &flip) < 0) {
        a90_console_printf("%s: PAGE_FLIP failed: %s\r\n", label, strerror(errno));
        return -1;
    }
    return kms_wait_pageflip_event(label, timeout_ms, result);
}

static void kms_scaled_plane_destroy_buffers(void) {
    uint32_t index;

    for (index = 0; index < 2U; ++index) {
        if (kms_scaled_plane.map[index] != NULL &&
            kms_scaled_plane.map[index] != MAP_FAILED &&
            kms_scaled_plane.map_size > 0U) {
            munmap(kms_scaled_plane.map[index], kms_scaled_plane.map_size);
        }
        if (kms_state.fd >= 0 && kms_scaled_plane.fb_id[index] != 0U) {
            uint32_t fb_id = kms_scaled_plane.fb_id[index];

            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_RMFB, &fb_id);
        }
        if (kms_state.fd >= 0 && kms_scaled_plane.handle[index] != 0U) {
            struct drm_mode_destroy_dumb destroy;

            memset(&destroy, 0, sizeof(destroy));
            destroy.handle = kms_scaled_plane.handle[index];
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
        }
        kms_scaled_plane.map[index] = MAP_FAILED;
        kms_scaled_plane.fb_id[index] = 0U;
        kms_scaled_plane.handle[index] = 0U;
    }
    kms_scaled_plane.width = 0U;
    kms_scaled_plane.height = 0U;
    kms_scaled_plane.stride = 0U;
    kms_scaled_plane.map_size = 0U;
    kms_scaled_plane.current_buffer = 0U;
}

static void kms_scaled_plane_copy_select_result(struct a90_kms_scaled_plane_result *result,
                                                const struct a90_kms_plane_select_result *select) {
    if (result == NULL || select == NULL) {
        return;
    }
    result->stage = select->stage;
    result->crtc_index = select->crtc_index;
    result->used_cached_crtc_index = select->used_cached_crtc_index;
    result->universal_cap_rc = select->universal_cap_rc;
    result->atomic_cap_rc = select->atomic_cap_rc;
    result->fetch_resources_rc = select->fetch_resources_rc;
    result->plane_count = select->plane_count;
    result->compatible_count = select->compatible_count;
    result->idle_xbgr_count = select->idle_xbgr_count;
}

static void kms_scaled_plane_copy_cached_select_result(struct a90_kms_scaled_plane_result *result) {
    if (result == NULL || !kms_scaled_plane.has_select) {
        return;
    }
    kms_scaled_plane_copy_select_result(result, &kms_scaled_plane.select);
}

static int kms_scaled_plane_create_buffers(uint32_t width,
                                           uint32_t height,
                                           struct a90_kms_scaled_plane_result *result) {
    uint32_t index;

    if (kms_state.fd < 0 || width == 0U || height == 0U) {
        errno = EINVAL;
        return -1;
    }
    kms_scaled_plane_destroy_buffers();
    for (index = 0; index < 2U; ++index) {
        struct drm_mode_create_dumb create;
        struct drm_mode_fb_cmd2 addfb2;
        struct drm_mode_map_dumb map_dumb;
        void *map;

        memset(&create, 0, sizeof(create));
        create.width = width;
        create.height = height;
        create.bpp = 32;
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_CREATE_DUMB;
        }
        if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0) {
            if (result != NULL) {
                result->rc = negative_errno_or(EIO);
            }
            kms_scaled_plane_destroy_buffers();
            return -1;
        }
        memset(&addfb2, 0, sizeof(addfb2));
        addfb2.width = create.width;
        addfb2.height = create.height;
        addfb2.pixel_format = DRM_FORMAT_XBGR8888;
        addfb2.handles[0] = create.handle;
        addfb2.pitches[0] = create.pitch;
        addfb2.offsets[0] = 0;
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_ADDFB2;
        }
        if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_ADDFB2, &addfb2) < 0) {
            struct drm_mode_destroy_dumb destroy;

            if (result != NULL) {
                result->rc = negative_errno_or(EIO);
            }
            memset(&destroy, 0, sizeof(destroy));
            destroy.handle = create.handle;
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
            kms_scaled_plane_destroy_buffers();
            return -1;
        }
        memset(&map_dumb, 0, sizeof(map_dumb));
        map_dumb.handle = create.handle;
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_MAP_DUMB;
        }
        if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_MAP_DUMB, &map_dumb) < 0) {
            uint32_t fb_id = addfb2.fb_id;
            struct drm_mode_destroy_dumb destroy;

            if (result != NULL) {
                result->rc = negative_errno_or(EIO);
            }
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_RMFB, &fb_id);
            memset(&destroy, 0, sizeof(destroy));
            destroy.handle = create.handle;
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
            kms_scaled_plane_destroy_buffers();
            return -1;
        }
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_MMAP;
        }
        map = mmap(NULL, create.size, PROT_READ | PROT_WRITE, MAP_SHARED,
                   kms_state.fd, (off_t)map_dumb.offset);
        if (map == MAP_FAILED) {
            uint32_t fb_id = addfb2.fb_id;
            struct drm_mode_destroy_dumb destroy;

            if (result != NULL) {
                result->rc = negative_errno_or(EIO);
            }
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_RMFB, &fb_id);
            memset(&destroy, 0, sizeof(destroy));
            destroy.handle = create.handle;
            (void)drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
            kms_scaled_plane_destroy_buffers();
            return -1;
        }
        kms_scaled_plane.handle[index] = create.handle;
        kms_scaled_plane.fb_id[index] = addfb2.fb_id;
        kms_scaled_plane.map[index] = map;
        kms_scaled_plane.stride = create.pitch;
        kms_scaled_plane.map_size = create.size;
    }
    kms_scaled_plane.width = width;
    kms_scaled_plane.height = height;
    kms_scaled_plane.current_buffer = 0U;
    return 0;
}

static int kms_scaled_plane_ensure(uint32_t width,
                                   uint32_t height,
                                   struct a90_kms_scaled_plane_result *result) {
    struct a90_kms_plane_select_result select;
    bool selected_this_call = false;

    if (kms_state.fd < 0) {
        errno = ENODEV;
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_INPUT;
            result->rc = negative_errno_or(ENODEV);
        }
        return -1;
    }
    if (kms_scaled_plane.plane_id == 0U) {
        if (kms_select_unused_scaled_plane(&kms_scaled_plane.plane_id, &select) < 0) {
            kms_scaled_plane_copy_select_result(result, &select);
            if (result != NULL) {
                result->rc = negative_errno_or(ENODEV);
            }
            return -1;
        }
        kms_scaled_plane.select = select;
        kms_scaled_plane.has_select = true;
        memset(&kms_scaled_plane.atomic_props, 0, sizeof(kms_scaled_plane.atomic_props));
        kms_scaled_plane.atomic_props.rc = -ENODEV;
        selected_this_call = true;
    }
    if (selected_this_call) {
        kms_scaled_plane_copy_select_result(result, &select);
    } else {
        kms_scaled_plane_copy_cached_select_result(result);
    }
    if (kms_scaled_plane.plane_id != 0U) {
        if (result != NULL && result->plane_id == 0U) {
            result->plane_id = kms_scaled_plane.plane_id;
        }
    }
    if (kms_scaled_plane.map[0] != MAP_FAILED &&
        kms_scaled_plane.map[1] != MAP_FAILED &&
        kms_scaled_plane.width == width &&
        kms_scaled_plane.height == height) {
        return 0;
    }
    return kms_scaled_plane_create_buffers(width, height, result);
}

static int kms_scaled_plane_atomic_commit(uint32_t fb_id,
                                          uint32_t dst_x,
                                          uint32_t dst_y,
                                          uint32_t dst_width,
                                          uint32_t dst_height,
                                          uint32_t source_width,
                                          uint32_t source_height,
                                          struct a90_kms_scaled_plane_result *result) {
    const struct a90_kms_atomic_plane_props *props = &kms_scaled_plane.atomic_props;
    uint32_t objs[1];
    uint32_t count_props[1];
    uint32_t prop_ids[10];
    uint64_t prop_values[10];
    struct drm_mode_atomic atomic;
    uint32_t index = 0U;

    if (result != NULL) {
        result->atomic_attempted = true;
        result->atomic_prop_count = props->count;
        result->atomic_props_rc = props->rc;
        result->stage = A90_KMS_SCALED_PLANE_STAGE_ATOMIC_COMMIT;
    }
    if (!props->ready || kms_state.fd < 0 || kms_scaled_plane.plane_id == 0U) {
        errno = ENODEV;
        if (result != NULL) {
            result->atomic_commit_rc = -ENODEV;
        }
        return -1;
    }

    prop_ids[index] = props->fb_id;
    prop_values[index++] = fb_id;
    prop_ids[index] = props->crtc_id;
    prop_values[index++] = kms_state.crtc_id;
    prop_ids[index] = props->crtc_x;
    prop_values[index++] = dst_x;
    prop_ids[index] = props->crtc_y;
    prop_values[index++] = dst_y;
    prop_ids[index] = props->crtc_w;
    prop_values[index++] = dst_width;
    prop_ids[index] = props->crtc_h;
    prop_values[index++] = dst_height;
    prop_ids[index] = props->src_x;
    prop_values[index++] = 0U;
    prop_ids[index] = props->src_y;
    prop_values[index++] = 0U;
    prop_ids[index] = props->src_w;
    prop_values[index++] = (uint64_t)source_width << 16U;
    prop_ids[index] = props->src_h;
    prop_values[index++] = (uint64_t)source_height << 16U;

    objs[0] = kms_scaled_plane.plane_id;
    count_props[0] = index;
    memset(&atomic, 0, sizeof(atomic));
    atomic.count_objs = 1U;
    atomic.objs_ptr = (uintptr_t)objs;
    atomic.count_props_ptr = (uintptr_t)count_props;
    atomic.props_ptr = (uintptr_t)prop_ids;
    atomic.prop_values_ptr = (uintptr_t)prop_values;
    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_ATOMIC, &atomic) < 0) {
        int rc = negative_errno_or(EIO);

        if (result != NULL) {
            result->atomic_commit_rc = rc;
        }
        return -1;
    }
    if (result != NULL) {
        result->atomic_commit_rc = 0;
    }
    return 0;
}

int a90_kms_present_scaled_plane_xbgr8888(const uint32_t *source,
                                          uint32_t source_width,
                                          uint32_t source_height,
                                          uint32_t source_stride,
                                          uint32_t dst_x,
                                          uint32_t dst_y,
                                          uint32_t dst_width,
                                          uint32_t dst_height,
                                          struct a90_kms_scaled_plane_result *result) {
    struct drm_mode_set_plane setplane;
    uint32_t next_buffer;
    uint32_t row;

    if (result != NULL) {
        memset(result, 0, sizeof(*result));
        result->stage = A90_KMS_SCALED_PLANE_STAGE_NONE;
        result->crtc_index = -1;
        result->universal_cap_rc = -ENODEV;
        result->atomic_cap_rc = -ENODEV;
        result->atomic_props_rc = -ENODEV;
        result->atomic_commit_rc = -ENODEV;
        result->legacy_setplane_rc = -ENODEV;
        result->rc = -EINVAL;
    }
    if (source == NULL || source_width == 0U || source_height == 0U ||
        dst_width == 0U || dst_height == 0U ||
        source_stride < source_width * sizeof(uint32_t) ||
        kms_state.fd < 0 ||
        dst_x > kms_state.width || dst_y > kms_state.height ||
        dst_width > kms_state.width - dst_x ||
        dst_height > kms_state.height - dst_y) {
        errno = EINVAL;
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_INPUT;
            result->rc = -EINVAL;
        }
        return -1;
    }
    if (kms_scaled_plane_ensure(source_width, source_height, result) < 0) {
        if (result != NULL) {
            result->attempted = false;
            if (result->rc == 0) {
                result->rc = negative_errno_or(ENODEV);
            }
        }
        return -1;
    }

    next_buffer = 1U - kms_scaled_plane.current_buffer;
    for (row = 0; row < source_height; ++row) {
        memcpy((char *)kms_scaled_plane.map[next_buffer] +
                   ((size_t)row * kms_scaled_plane.stride),
               (const char *)source + ((size_t)row * source_stride),
               (size_t)source_width * sizeof(uint32_t));
    }

    if (!kms_scaled_plane.atomic_props.fetched) {
        if (result != NULL) {
            result->stage = A90_KMS_SCALED_PLANE_STAGE_ATOMIC_PROPS;
        }
        (void)kms_fetch_atomic_plane_props(kms_scaled_plane.plane_id,
                                           &kms_scaled_plane.atomic_props);
    }
    if (result != NULL) {
        result->atomic_prop_count = kms_scaled_plane.atomic_props.count;
        result->atomic_props_rc = kms_scaled_plane.atomic_props.rc;
    }
    if (kms_scaled_plane.atomic_props.ready &&
        kms_scaled_plane_atomic_commit(kms_scaled_plane.fb_id[next_buffer],
                                       dst_x,
                                       dst_y,
                                       dst_width,
                                       dst_height,
                                       source_width,
                                       source_height,
                                       result) == 0) {
        kms_scaled_plane.current_buffer = next_buffer;
        kms_scaled_plane.enabled = true;
        if (result != NULL) {
            result->attempted = true;
            result->presented = true;
            result->plane_id = kms_scaled_plane.plane_id;
            result->fb_id = kms_scaled_plane.fb_id[next_buffer];
            result->crtc_id = kms_state.crtc_id;
            result->crtc_index = kms_state.crtc_index;
            result->stage = A90_KMS_SCALED_PLANE_STAGE_PRESENTED;
            result->rc = 0;
        }
        return 0;
    }

    memset(&setplane, 0, sizeof(setplane));
    setplane.plane_id = kms_scaled_plane.plane_id;
    setplane.crtc_id = kms_state.crtc_id;
    setplane.fb_id = kms_scaled_plane.fb_id[next_buffer];
    setplane.crtc_x = (int32_t)dst_x;
    setplane.crtc_y = (int32_t)dst_y;
    setplane.crtc_w = dst_width;
    setplane.crtc_h = dst_height;
    setplane.src_x = 0U;
    setplane.src_y = 0U;
    setplane.src_w = source_width << 16U;
    setplane.src_h = source_height << 16U;
    if (result != NULL) {
        result->attempted = true;
        result->plane_id = kms_scaled_plane.plane_id;
        result->fb_id = kms_scaled_plane.fb_id[next_buffer];
        result->crtc_id = kms_state.crtc_id;
        result->crtc_index = kms_state.crtc_index;
        result->stage = A90_KMS_SCALED_PLANE_STAGE_SETPLANE;
    }
    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_SETPLANE, &setplane) < 0) {
        if (result != NULL) {
            result->legacy_setplane_rc = negative_errno_or(EIO);
            result->rc = result->legacy_setplane_rc;
        }
        return -1;
    }
    kms_scaled_plane.current_buffer = next_buffer;
    kms_scaled_plane.enabled = true;
    if (result != NULL) {
        result->presented = true;
        result->stage = A90_KMS_SCALED_PLANE_STAGE_PRESENTED;
        result->legacy_setplane_rc = 0;
        result->rc = 0;
    }
    return 0;
}

int a90_kms_disable_scaled_plane(void) {
    struct drm_mode_set_plane setplane;

    if (kms_state.fd < 0 || kms_scaled_plane.plane_id == 0U || !kms_scaled_plane.enabled) {
        return 0;
    }
    memset(&setplane, 0, sizeof(setplane));
    setplane.plane_id = kms_scaled_plane.plane_id;
    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_SETPLANE, &setplane) < 0) {
        return negative_errno_or(EIO);
    }
    kms_scaled_plane.enabled = false;
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
    info->stride = kms_state.stride;
    info->map_size = kms_state.map_size;
    info->pixel_format = DRM_FORMAT_XBGR8888;
    info->connector_id = kms_state.connector_id;
    info->encoder_id = kms_state.encoder_id;
    info->crtc_id = kms_state.crtc_id;
    info->crtc_index = kms_state.crtc_index;
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
    int crtc_index;
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

    if (kms_find_output(fd, verbose, &connector_id, &encoder_id, &crtc_id, &crtc_index, &mode) == 0) {
        a90_console_printf("kmsprobe: chosen connector=%u encoder=%u crtc=%u crtc_index=%d mode=%s %ux%u@%u\r\n",
                connector_id, encoder_id, crtc_id, crtc_index,
                mode.name, mode.hdisplay, mode.vdisplay, mode.vrefresh);
    } else {
        a90_console_printf("kmsprobe: no usable display path: %s\r\n", strerror(errno));
        result = negative_errno_or(ENODEV);
    }

    close(fd);
    return result;
}
