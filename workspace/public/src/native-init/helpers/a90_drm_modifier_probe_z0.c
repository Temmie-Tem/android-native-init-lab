// Read-only DRM plane format/modifier inventory helper for GPU Z0 zero-copy recon.

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef DRM_FORMAT_MOD_VENDOR_QCOM
#define DRM_FORMAT_MOD_VENDOR_QCOM 0x05
#endif
#ifndef fourcc_mod_code
#define fourcc_mod_code(vendor, val) ((((uint64_t)DRM_FORMAT_MOD_VENDOR_##vendor) << 56) | ((val) & 0x00ffffffffffffffULL))
#endif
#ifndef DRM_FORMAT_MOD_QCOM_COMPRESSED
#define DRM_FORMAT_MOD_QCOM_COMPRESSED fourcc_mod_code(QCOM, 1)
#endif
#ifndef DRM_FORMAT_MOD_QCOM_TILED2
#define DRM_FORMAT_MOD_QCOM_TILED2 fourcc_mod_code(QCOM, 2)
#endif
#ifndef DRM_FORMAT_MOD_QCOM_TILED3
#define DRM_FORMAT_MOD_QCOM_TILED3 fourcc_mod_code(QCOM, 3)
#endif

struct plane_props {
    bool got_props;
    bool has_fb_id;
    bool has_crtc_id;
    bool has_crtc_x;
    bool has_crtc_y;
    bool has_crtc_w;
    bool has_crtc_h;
    bool has_src_x;
    bool has_src_y;
    bool has_src_w;
    bool has_src_h;
    bool has_type;
    bool has_in_formats;
    unsigned int count;
    uint32_t in_formats_prop_id;
    uint32_t in_formats_blob_id;
};

struct modifier_summary {
    int rc;
    uint32_t blob_id;
    uint32_t blob_length;
    uint32_t blob_version;
    uint32_t format_count;
    uint32_t modifier_count;
    bool has_linear;
    bool has_qcom_tiled2;
    bool has_qcom_tiled3;
    bool has_qcom_compressed;
    bool xbgr_linear;
    bool xbgr_tiled2;
    bool xbgr_tiled3;
    bool xbgr_compressed;
    bool xrgb_linear;
    bool xrgb_tiled2;
    bool xrgb_tiled3;
    bool xrgb_compressed;
};

static int ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);
    return rc;
}

static int negative_errno(void) {
    int saved = errno;
    return saved > 0 ? -saved : -EIO;
}

static int read_trimmed(const char *path, char *out, size_t out_size) {
    FILE *fp;

    if (out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -1;
    }
    if (fgets(out, (int)out_size, fp) == NULL) {
        fclose(fp);
        errno = EIO;
        return -1;
    }
    fclose(fp);
    out[strcspn(out, "\r\n")] = '\0';
    return 0;
}

static int ensure_card0_path(char *out, size_t out_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;
    struct stat st;

    if (snprintf(out, out_size, "/dev/dri/card0") >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (stat(out, &st) == 0 && S_ISCHR(st.st_mode)) {
        return 0;
    }
    if (read_trimmed("/sys/class/drm/card0/dev", dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }
    if (sscanf(dev_info, "%u:%u", &major_num, &minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    if (mkdir("/dev/dri", 0755) < 0 && errno != EEXIST) {
        return -1;
    }
    if (mknod(out, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int open_card0(char *node_path, size_t node_path_size) {
    int fd;

    if (ensure_card0_path(node_path, node_path_size) < 0) {
        return -1;
    }
    fd = open(node_path, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    return fd;
}

static int set_client_cap(int fd, uint64_t capability, uint64_t value) {
    struct drm_set_client_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    cap.value = value;
    if (ioctl_retry(fd, DRM_IOCTL_SET_CLIENT_CAP, &cap) < 0) {
        return negative_errno();
    }
    return 0;
}

static int get_cap(int fd, uint64_t capability, uint64_t *value) {
    struct drm_get_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    if (ioctl_retry(fd, DRM_IOCTL_GET_CAP, &cap) < 0) {
        return negative_errno();
    }
    *value = cap.value;
    return 0;
}

static int fetch_resources(int fd,
                           struct drm_mode_card_res *res,
                           uint32_t **crtcs_out,
                           uint32_t **connectors_out,
                           uint32_t **encoders_out) {
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;

    memset(res, 0, sizeof(*res));
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        return negative_errno();
    }
    if (res->count_crtcs > 0) {
        crtcs = calloc(res->count_crtcs, sizeof(*crtcs));
        if (crtcs == NULL) goto oom;
        res->crtc_id_ptr = (uintptr_t)crtcs;
    }
    if (res->count_connectors > 0) {
        connectors = calloc(res->count_connectors, sizeof(*connectors));
        if (connectors == NULL) goto oom;
        res->connector_id_ptr = (uintptr_t)connectors;
    }
    if (res->count_encoders > 0) {
        encoders = calloc(res->count_encoders, sizeof(*encoders));
        if (encoders == NULL) goto oom;
        res->encoder_id_ptr = (uintptr_t)encoders;
    }
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        int rc = negative_errno();
        free(crtcs);
        free(connectors);
        free(encoders);
        return rc;
    }
    *crtcs_out = crtcs;
    *connectors_out = connectors;
    *encoders_out = encoders;
    return 0;

oom:
    free(crtcs);
    free(connectors);
    free(encoders);
    return -ENOMEM;
}

static int find_crtc_index(const uint32_t *crtcs, uint32_t count_crtcs, uint32_t crtc_id) {
    uint32_t index;

    for (index = 0; index < count_crtcs; ++index) {
        if (crtcs[index] == crtc_id) {
            return (int)index;
        }
    }
    return -1;
}

static int fetch_connector(int fd,
                           uint32_t connector_id,
                           struct drm_mode_get_connector *conn,
                           uint32_t **encoders_out) {
    uint32_t *encoders = NULL;

    memset(conn, 0, sizeof(*conn));
    conn->connector_id = connector_id;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        return negative_errno();
    }
    if (conn->count_encoders > 0) {
        encoders = calloc(conn->count_encoders, sizeof(*encoders));
        if (encoders == NULL) {
            return -ENOMEM;
        }
        conn->encoders_ptr = (uintptr_t)encoders;
    }
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        int rc = negative_errno();
        free(encoders);
        return rc;
    }
    *encoders_out = encoders;
    return 0;
}

static int select_active_crtc(int fd,
                              const uint32_t *crtcs,
                              uint32_t count_crtcs,
                              const uint32_t *connectors,
                              uint32_t count_connectors,
                              uint32_t *connector_id_out,
                              uint32_t *encoder_id_out,
                              uint32_t *crtc_id_out,
                              int *crtc_index_out) {
    uint32_t index;

    for (index = 0; index < count_connectors; ++index) {
        struct drm_mode_get_connector conn;
        struct drm_mode_get_encoder encoder;
        uint32_t *conn_encoders = NULL;
        uint32_t encoder_id;
        int crtc_index;
        int rc;

        rc = fetch_connector(fd, connectors[index], &conn, &conn_encoders);
        if (rc < 0) {
            continue;
        }
        if (conn.connection != 1) {
            free(conn_encoders);
            continue;
        }
        encoder_id = conn.encoder_id;
        if (encoder_id == 0 && conn.count_encoders > 0) {
            encoder_id = conn_encoders[0];
        }
        free(conn_encoders);
        if (encoder_id == 0) {
            continue;
        }
        memset(&encoder, 0, sizeof(encoder));
        encoder.encoder_id = encoder_id;
        if (ioctl_retry(fd, DRM_IOCTL_MODE_GETENCODER, &encoder) < 0) {
            continue;
        }
        if (encoder.crtc_id == 0) {
            continue;
        }
        crtc_index = find_crtc_index(crtcs, count_crtcs, encoder.crtc_id);
        if (crtc_index < 0) {
            continue;
        }
        *connector_id_out = conn.connector_id;
        *encoder_id_out = encoder.encoder_id;
        *crtc_id_out = encoder.crtc_id;
        *crtc_index_out = crtc_index;
        return 0;
    }
    return -ENODEV;
}

static int fetch_plane_ids(int fd, uint32_t **plane_ids_out, uint32_t *count_out) {
    struct drm_mode_get_plane_res pres;
    uint32_t *plane_ids = NULL;

    memset(&pres, 0, sizeof(pres));
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &pres) < 0) {
        return negative_errno();
    }
    if (pres.count_planes > 0) {
        plane_ids = calloc(pres.count_planes, sizeof(*plane_ids));
        if (plane_ids == NULL) {
            return -ENOMEM;
        }
        pres.plane_id_ptr = (uintptr_t)plane_ids;
    }
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &pres) < 0) {
        int rc = negative_errno();
        free(plane_ids);
        return rc;
    }
    *plane_ids_out = plane_ids;
    *count_out = pres.count_planes;
    return 0;
}

static int fetch_plane(int fd,
                       uint32_t plane_id,
                       struct drm_mode_get_plane *plane,
                       uint32_t **formats_out) {
    uint32_t *formats = NULL;

    memset(plane, 0, sizeof(*plane));
    plane->plane_id = plane_id;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANE, plane) < 0) {
        return negative_errno();
    }
    if (plane->count_format_types > 0) {
        formats = calloc(plane->count_format_types, sizeof(*formats));
        if (formats == NULL) {
            return -ENOMEM;
        }
        plane->format_type_ptr = (uintptr_t)formats;
    }
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPLANE, plane) < 0) {
        int rc = negative_errno();
        free(formats);
        return rc;
    }
    *formats_out = formats;
    return 0;
}

static int infer_active_crtc_from_planes(int fd,
                                         const uint32_t *crtcs,
                                         uint32_t count_crtcs,
                                         const uint32_t *plane_ids,
                                         uint32_t plane_count,
                                         uint32_t *plane_id_out,
                                         uint32_t *plane_index_out,
                                         uint32_t *crtc_id_out,
                                         int *crtc_index_out) {
    uint32_t index;

    for (index = 0; index < plane_count; ++index) {
        struct drm_mode_get_plane plane;
        uint32_t *formats = NULL;
        int crtc_index;
        int rc;

        rc = fetch_plane(fd, plane_ids[index], &plane, &formats);
        free(formats);
        if (rc < 0 || plane.crtc_id == 0) {
            continue;
        }
        crtc_index = find_crtc_index(crtcs, count_crtcs, plane.crtc_id);
        if (crtc_index < 0) {
            continue;
        }
        *plane_id_out = plane.plane_id;
        *plane_index_out = index;
        *crtc_id_out = plane.crtc_id;
        *crtc_index_out = crtc_index;
        return 0;
    }
    return -ENODEV;
}

static void fourcc_string(uint32_t format, char out[5]) {
    unsigned int i;

    for (i = 0; i < 4; ++i) {
        unsigned char ch = (format >> (i * 8U)) & 0xffU;
        out[i] = isprint(ch) ? (char)ch : '.';
    }
    out[4] = '\0';
}

static bool has_format(const uint32_t *formats, uint32_t count, uint32_t wanted) {
    uint32_t index;

    for (index = 0; index < count; ++index) {
        if (formats[index] == wanted) {
            return true;
        }
    }
    return false;
}

static const char *modifier_name(uint64_t modifier) {
    if (modifier == DRM_FORMAT_MOD_LINEAR) return "LINEAR";
    if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) return "QCOM_COMPRESSED";
    if (modifier == DRM_FORMAT_MOD_QCOM_TILED2) return "QCOM_TILED2";
    if (modifier == DRM_FORMAT_MOD_QCOM_TILED3) return "QCOM_TILED3";
    if (modifier == DRM_FORMAT_MOD_INVALID) return "INVALID";
    return "OTHER";
}

static bool blob_modifier_applies_to_format(const struct drm_format_modifier *modifier,
                                            uint32_t format_index) {
    uint32_t bit;

    if (format_index < modifier->offset) {
        return false;
    }
    bit = format_index - modifier->offset;
    if (bit >= 64U) {
        return false;
    }
    return (modifier->formats & (1ULL << bit)) != 0ULL;
}

static int fetch_property_blob(int fd, uint32_t blob_id, void **data_out, uint32_t *length_out) {
    struct drm_mode_get_blob blob;
    void *data;

    memset(&blob, 0, sizeof(blob));
    blob.blob_id = blob_id;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPROPBLOB, &blob) < 0) {
        return negative_errno();
    }
    if (blob.length == 0U) {
        return -ENODATA;
    }
    data = calloc(1, blob.length);
    if (data == NULL) {
        return -ENOMEM;
    }
    blob.data = (uintptr_t)data;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPROPBLOB, &blob) < 0) {
        int rc = negative_errno();
        free(data);
        return rc;
    }
    *data_out = data;
    *length_out = blob.length;
    return 0;
}

static void note_prop(struct plane_props *props, const char *name, uint32_t prop_id, uint64_t value) {
    if (strcmp(name, "FB_ID") == 0) props->has_fb_id = true;
    else if (strcmp(name, "CRTC_ID") == 0) props->has_crtc_id = true;
    else if (strcmp(name, "CRTC_X") == 0) props->has_crtc_x = true;
    else if (strcmp(name, "CRTC_Y") == 0) props->has_crtc_y = true;
    else if (strcmp(name, "CRTC_W") == 0) props->has_crtc_w = true;
    else if (strcmp(name, "CRTC_H") == 0) props->has_crtc_h = true;
    else if (strcmp(name, "SRC_X") == 0) props->has_src_x = true;
    else if (strcmp(name, "SRC_Y") == 0) props->has_src_y = true;
    else if (strcmp(name, "SRC_W") == 0) props->has_src_w = true;
    else if (strcmp(name, "SRC_H") == 0) props->has_src_h = true;
    else if (strcmp(name, "type") == 0) props->has_type = true;
    else if (strcmp(name, "IN_FORMATS") == 0) {
        props->has_in_formats = true;
        props->in_formats_prop_id = prop_id;
        props->in_formats_blob_id = (uint32_t)value;
    }
}

static int fetch_plane_props(int fd, uint32_t plane_id, struct plane_props *props) {
    struct drm_mode_obj_get_properties obj_props;
    uint32_t *prop_ids = NULL;
    uint64_t *prop_values = NULL;
    uint32_t index;

    memset(props, 0, sizeof(*props));
    memset(&obj_props, 0, sizeof(obj_props));
    obj_props.obj_id = plane_id;
    obj_props.obj_type = DRM_MODE_OBJECT_PLANE;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &obj_props) < 0) {
        return negative_errno();
    }
    props->count = obj_props.count_props;
    if (obj_props.count_props == 0) {
        props->got_props = true;
        return 0;
    }
    prop_ids = calloc(obj_props.count_props, sizeof(*prop_ids));
    prop_values = calloc(obj_props.count_props, sizeof(*prop_values));
    if (prop_ids == NULL || prop_values == NULL) {
        free(prop_ids);
        free(prop_values);
        return -ENOMEM;
    }
    obj_props.props_ptr = (uintptr_t)prop_ids;
    obj_props.prop_values_ptr = (uintptr_t)prop_values;
    if (ioctl_retry(fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &obj_props) < 0) {
        int rc = negative_errno();
        free(prop_ids);
        free(prop_values);
        return rc;
    }
    for (index = 0; index < obj_props.count_props; ++index) {
        struct drm_mode_get_property prop;

        memset(&prop, 0, sizeof(prop));
        prop.prop_id = prop_ids[index];
        if (ioctl_retry(fd, DRM_IOCTL_MODE_GETPROPERTY, &prop) == 0) {
            note_prop(props, prop.name, prop_ids[index], prop_values[index]);
        }
    }
    props->got_props = true;
    free(prop_ids);
    free(prop_values);
    return 0;
}

static bool has_rect_props(const struct plane_props *props) {
    return props->has_crtc_x && props->has_crtc_y &&
           props->has_crtc_w && props->has_crtc_h &&
           props->has_src_x && props->has_src_y &&
           props->has_src_w && props->has_src_h;
}

static uint32_t find_format_index(const uint32_t *formats, uint32_t count, uint32_t wanted) {
    uint32_t index;

    for (index = 0; index < count; ++index) {
        if (formats[index] == wanted) {
            return index;
        }
    }
    return UINT32_MAX;
}

static void modifier_summary_note(struct modifier_summary *summary,
                                  uint32_t fmt,
                                  uint64_t modifier) {
    bool is_xbgr = fmt == DRM_FORMAT_XBGR8888;
    bool is_xrgb = fmt == DRM_FORMAT_XRGB8888;

    if (modifier == DRM_FORMAT_MOD_LINEAR) {
        summary->has_linear = true;
        if (is_xbgr) summary->xbgr_linear = true;
        if (is_xrgb) summary->xrgb_linear = true;
    } else if (modifier == DRM_FORMAT_MOD_QCOM_TILED2) {
        summary->has_qcom_tiled2 = true;
        if (is_xbgr) summary->xbgr_tiled2 = true;
        if (is_xrgb) summary->xrgb_tiled2 = true;
    } else if (modifier == DRM_FORMAT_MOD_QCOM_TILED3) {
        summary->has_qcom_tiled3 = true;
        if (is_xbgr) summary->xbgr_tiled3 = true;
        if (is_xrgb) summary->xrgb_tiled3 = true;
    } else if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {
        summary->has_qcom_compressed = true;
        if (is_xbgr) summary->xbgr_compressed = true;
        if (is_xrgb) summary->xrgb_compressed = true;
    }
}

static int parse_in_formats_blob(int fd,
                                 const struct plane_props *props,
                                 struct modifier_summary *summary) {
    void *blob_data = NULL;
    uint32_t blob_length = 0;
    const struct drm_format_modifier_blob *blob;
    const uint32_t *formats;
    const struct drm_format_modifier *modifiers;
    uint32_t index;
    int rc;

    memset(summary, 0, sizeof(*summary));
    summary->rc = -ENODATA;
    summary->blob_id = props->in_formats_blob_id;
    if (!props->has_in_formats || props->in_formats_blob_id == 0U) {
        return summary->rc;
    }
    rc = fetch_property_blob(fd, props->in_formats_blob_id, &blob_data, &blob_length);
    if (rc < 0) {
        summary->rc = rc;
        return rc;
    }
    if (blob_length < sizeof(struct drm_format_modifier_blob)) {
        free(blob_data);
        summary->rc = -EINVAL;
        return -EINVAL;
    }
    blob = (const struct drm_format_modifier_blob *)blob_data;
    summary->blob_length = blob_length;
    summary->blob_version = blob->version;
    summary->format_count = blob->count_formats;
    summary->modifier_count = blob->count_modifiers;
    if (blob->formats_offset > blob_length ||
        blob->modifiers_offset > blob_length ||
        (uint64_t)blob->formats_offset + (uint64_t)blob->count_formats * sizeof(uint32_t) > blob_length ||
        (uint64_t)blob->modifiers_offset + (uint64_t)blob->count_modifiers * sizeof(struct drm_format_modifier) > blob_length) {
        free(blob_data);
        summary->rc = -EINVAL;
        return -EINVAL;
    }
    formats = (const uint32_t *)((const char *)blob_data + blob->formats_offset);
    modifiers = (const struct drm_format_modifier *)((const char *)blob_data + blob->modifiers_offset);

    for (index = 0; index < blob->count_modifiers; ++index) {
        const struct drm_format_modifier *modifier = &modifiers[index];
        uint32_t format_index;

        for (format_index = 0; format_index < blob->count_formats; ++format_index) {
            if (blob_modifier_applies_to_format(modifier, format_index)) {
                modifier_summary_note(summary, formats[format_index], modifier->modifier);
            }
        }
    }
    summary->rc = 0;
    free(blob_data);
    return 0;
}

static void print_format_sample(uint32_t plane_index,
                                const uint32_t *formats,
                                uint32_t count) {
    uint32_t index;
    uint32_t limit = count < 16U ? count : 16U;

    printf("plane.%u.formats.sample=", plane_index);
    for (index = 0; index < limit; ++index) {
        char name[5];
        fourcc_string(formats[index], name);
        printf("%s%s", index == 0 ? "" : ",", name);
    }
    if (count > limit) {
        printf(",...");
    }
    printf("\n");
}

static void print_target_modifiers(uint32_t plane_index,
                                   const uint32_t *formats,
                                   uint32_t format_count,
                                   const struct plane_props *props,
                                   const struct modifier_summary *summary) {
    uint32_t xbgr_index = find_format_index(formats, format_count, DRM_FORMAT_XBGR8888);
    uint32_t xrgb_index = find_format_index(formats, format_count, DRM_FORMAT_XRGB8888);

    printf("plane.%u.in_formats.has=%d prop_id=%u blob_id=%u rc=%d blob_len=%u version=%u formats=%u modifiers=%u\n",
           plane_index,
           props->has_in_formats ? 1 : 0,
           props->in_formats_prop_id,
           props->in_formats_blob_id,
           summary->rc,
           summary->blob_length,
           summary->blob_version,
           summary->format_count,
           summary->modifier_count);
    printf("plane.%u.modifiers.any linear=%d qcom_tiled2=%d qcom_tiled3=%d qcom_compressed=%d\n",
           plane_index,
           summary->has_linear ? 1 : 0,
           summary->has_qcom_tiled2 ? 1 : 0,
           summary->has_qcom_tiled3 ? 1 : 0,
           summary->has_qcom_compressed ? 1 : 0);
    printf("plane.%u.modifiers.XB24 format_index=%u linear=%d qcom_tiled2=%d qcom_tiled3=%d qcom_compressed=%d\n",
           plane_index,
           xbgr_index,
           summary->xbgr_linear ? 1 : 0,
           summary->xbgr_tiled2 ? 1 : 0,
           summary->xbgr_tiled3 ? 1 : 0,
           summary->xbgr_compressed ? 1 : 0);
    printf("plane.%u.modifiers.XR24 format_index=%u linear=%d qcom_tiled2=%d qcom_tiled3=%d qcom_compressed=%d\n",
           plane_index,
           xrgb_index,
           summary->xrgb_linear ? 1 : 0,
           summary->xrgb_tiled2 ? 1 : 0,
           summary->xrgb_tiled3 ? 1 : 0,
           summary->xrgb_compressed ? 1 : 0);
    printf("plane.%u.modifiers.names=%s%s%s%s\n",
           plane_index,
           summary->has_linear ? "LINEAR" : "",
           summary->has_qcom_tiled2 ? ",QCOM_TILED2" : "",
           summary->has_qcom_tiled3 ? ",QCOM_TILED3" : "",
           summary->has_qcom_compressed ? ",QCOM_COMPRESSED" : "");
    (void)modifier_name;
}

int main(void) {
    char node_path[128];
    struct drm_mode_card_res res;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t *plane_ids = NULL;
    uint32_t plane_count = 0;
    uint32_t connector_id = 0;
    uint32_t encoder_id = 0;
    uint32_t crtc_id = 0;
    uint32_t active_plane_id = 0;
    uint32_t active_plane_index = 0;
    int crtc_index = -1;
    int active_connector_rc;
    int active_select_rc;
    int active_fallback_rc = -ENODEV;
    const char *active_source = "connector";
    int fd;
    int rc;
    uint64_t dumb = 0;
    uint64_t addfb2_modifiers = 0;
    uint64_t prime = 0;
    unsigned int compatible_count = 0;
    unsigned int rect_props_count = 0;
    unsigned int xbgr_linear_count = 0;
    unsigned int xbgr_tiled3_count = 0;
    unsigned int xbgr_compressed_count = 0;
    unsigned int candidate_linear_count = 0;
    unsigned int candidate_implicit_linear_count = 0;
    unsigned int candidate_tiled3_count = 0;
    unsigned int candidate_compressed_count = 0;
    uint32_t index;

    printf("probe.version=1\n");
    printf("probe.scope=z0-drm-plane-format-modifier-inventory\n");
    fd = open_card0(node_path, sizeof(node_path));
    if (fd < 0) {
        printf("probe.open.rc=%d\n", negative_errno());
        return 1;
    }
    printf("probe.node=/dev/dri/card0\n");
    rc = set_client_cap(fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1);
    printf("probe.client_cap.universal_planes.rc=%d\n", rc);
    rc = set_client_cap(fd, DRM_CLIENT_CAP_ATOMIC, 1);
    printf("probe.client_cap.atomic.rc=%d\n", rc);
    if (get_cap(fd, DRM_CAP_DUMB_BUFFER, &dumb) == 0) {
        printf("probe.cap.dumb_buffer=%llu\n", (unsigned long long)dumb);
    }
    if (get_cap(fd, DRM_CAP_ADDFB2_MODIFIERS, &addfb2_modifiers) == 0) {
        printf("probe.cap.addfb2_modifiers=%llu\n", (unsigned long long)addfb2_modifiers);
    }
    if (get_cap(fd, DRM_CAP_PRIME, &prime) == 0) {
        printf("probe.cap.prime=0x%llx import=%d export=%d\n",
               (unsigned long long)prime,
               (prime & DRM_PRIME_CAP_IMPORT) ? 1 : 0,
               (prime & DRM_PRIME_CAP_EXPORT) ? 1 : 0);
    }

    rc = fetch_resources(fd, &res, &crtcs, &connectors, &encoders);
    if (rc < 0) {
        printf("probe.resources.rc=%d\n", rc);
        close(fd);
        return 1;
    }
    printf("probe.resources.crtcs=%u connectors=%u encoders=%u min=%ux%u max=%ux%u\n",
           res.count_crtcs, res.count_connectors, res.count_encoders,
           res.min_width, res.min_height, res.max_width, res.max_height);

    active_connector_rc = select_active_crtc(fd, crtcs, res.count_crtcs,
                                             connectors, res.count_connectors,
                                             &connector_id, &encoder_id, &crtc_id, &crtc_index);
    active_select_rc = active_connector_rc;

    rc = fetch_plane_ids(fd, &plane_ids, &plane_count);
    printf("probe.planes.rc=%d\n", rc);
    printf("probe.planes.count=%u\n", rc == 0 ? plane_count : 0);
    if (rc < 0) {
        free(crtcs);
        free(connectors);
        free(encoders);
        close(fd);
        return 1;
    }
    if (active_select_rc < 0) {
        active_fallback_rc = infer_active_crtc_from_planes(fd, crtcs, res.count_crtcs,
                                                           plane_ids, plane_count,
                                                           &active_plane_id, &active_plane_index,
                                                           &crtc_id, &crtc_index);
        if (active_fallback_rc == 0) {
            active_source = "current-plane";
            active_select_rc = 0;
        }
    }
    printf("probe.active.rc=%d\n", active_select_rc);
    printf("probe.active.connector_scan.rc=%d\n", active_connector_rc);
    printf("probe.active.fallback.current_plane.rc=%d\n", active_fallback_rc);
    printf("probe.active.source=%s\n", active_source);
    printf("probe.active.connector_id=%u encoder_id=%u crtc_id=%u crtc_index=%d current_plane_id=%u current_plane_index=%u\n",
           connector_id, encoder_id, crtc_id, crtc_index, active_plane_id, active_plane_index);

    for (index = 0; index < plane_count; ++index) {
        struct drm_mode_get_plane plane;
        struct plane_props props;
        struct modifier_summary modifiers;
        uint32_t *formats = NULL;
        bool compatible = false;
        bool rect_props = false;
        bool has_xbgr8888 = false;
        bool has_xrgb8888 = false;
        int props_rc;

        rc = fetch_plane(fd, plane_ids[index], &plane, &formats);
        if (rc < 0) {
            printf("plane.%u.id=%u get.rc=%d\n", index, plane_ids[index], rc);
            continue;
        }
        if (crtc_index >= 0 && (plane.possible_crtcs & (1U << (unsigned int)crtc_index)) != 0U) {
            compatible = true;
            ++compatible_count;
        }
        has_xbgr8888 = has_format(formats, plane.count_format_types, DRM_FORMAT_XBGR8888);
        has_xrgb8888 = has_format(formats, plane.count_format_types, DRM_FORMAT_XRGB8888);
        props_rc = fetch_plane_props(fd, plane.plane_id, &props);
        rect_props = props_rc == 0 && has_rect_props(&props);
        if (rect_props) {
            ++rect_props_count;
        }
        (void)parse_in_formats_blob(fd, &props, &modifiers);
        if (modifiers.xbgr_linear) ++xbgr_linear_count;
        if (modifiers.xbgr_tiled3) ++xbgr_tiled3_count;
        if (modifiers.xbgr_compressed) ++xbgr_compressed_count;
        if (compatible && rect_props && modifiers.xbgr_linear) ++candidate_linear_count;
        if (compatible && rect_props && has_xbgr8888 && !props.has_in_formats) ++candidate_implicit_linear_count;
        if (compatible && rect_props && modifiers.xbgr_tiled3) ++candidate_tiled3_count;
        if (compatible && rect_props && modifiers.xbgr_compressed) ++candidate_compressed_count;

        printf("plane.%u.id=%u current_crtc=%u current_fb=%u possible_crtcs=0x%x compatible_active_crtc=%d formats=%u has_xbgr8888=%d has_xrgb8888=%d props_rc=%d props_count=%u rect_props=%d\n",
               index,
               plane.plane_id,
               plane.crtc_id,
               plane.fb_id,
               plane.possible_crtcs,
               compatible ? 1 : 0,
               plane.count_format_types,
               has_xbgr8888 ? 1 : 0,
               has_xrgb8888 ? 1 : 0,
               props_rc,
               props.count,
               rect_props ? 1 : 0);
        printf("plane.%u.props.fb_id=%d crtc_id=%d crtc_rect=%d src_rect=%d type=%d in_formats=%d\n",
               index,
               props.has_fb_id ? 1 : 0,
               props.has_crtc_id ? 1 : 0,
               (props.has_crtc_x && props.has_crtc_y && props.has_crtc_w && props.has_crtc_h) ? 1 : 0,
               (props.has_src_x && props.has_src_y && props.has_src_w && props.has_src_h) ? 1 : 0,
               props.has_type ? 1 : 0,
               props.has_in_formats ? 1 : 0);
        print_format_sample(index, formats, plane.count_format_types);
        print_target_modifiers(index, formats, plane.count_format_types, &props, &modifiers);
        free(formats);
    }

    printf("probe.compatible_plane_count=%u\n", compatible_count);
    printf("probe.rect_props_plane_count=%u\n", rect_props_count);
    printf("probe.xbgr8888.linear_plane_count=%u\n", xbgr_linear_count);
    printf("probe.xbgr8888.qcom_tiled3_plane_count=%u\n", xbgr_tiled3_count);
    printf("probe.xbgr8888.qcom_compressed_plane_count=%u\n", xbgr_compressed_count);
    printf("probe.candidate.linear_count=%u\n", candidate_linear_count);
    printf("probe.candidate.implicit_linear_count=%u\n", candidate_implicit_linear_count);
    printf("probe.candidate.qcom_tiled3_count=%u\n", candidate_tiled3_count);
    printf("probe.candidate.qcom_compressed_count=%u\n", candidate_compressed_count);
    printf("probe.result=%s\n",
           candidate_linear_count > 0 ? "z0-linear-scanout-feasible" :
           candidate_implicit_linear_count > 0 ? "z0-implicit-linear-scanout-feasible" :
           candidate_tiled3_count > 0 ? "z0-tiled3-scanout-feasible" :
           candidate_compressed_count > 0 ? "z0-compressed-scanout-feasible" :
           "z0-no-matching-scanout-modifier");

    free(plane_ids);
    free(crtcs);
    free(connectors);
    free(encoders);
    close(fd);
    return 0;
}
