/* Included by stage3/linux_init/init_v84.c. Do not compile standalone. */

static int print_input_event_info(const char *event_name) {
    char name_path[PATH_MAX];
    char dev_path[PATH_MAX];
    char name_buf[256];
    char dev_info_path[PATH_MAX];
    char dev_info[64];

    if (snprintf(name_path, sizeof(name_path),
                 "/sys/class/input/%s/device/name", event_name) >= (int)sizeof(name_path) ||
        snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        a90_console_printf("inputinfo: %s: path too long\r\n", event_name);
        return -ENAMETOOLONG;
    }

    if (read_text_file(name_path, name_buf, sizeof(name_buf)) < 0) {
        a90_console_printf("inputinfo: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(name_buf);

    if (read_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        a90_console_printf("inputinfo: %s dev: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(dev_info);

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        a90_console_printf("%s  name=%s  dev=%s  node=<error:%s>\r\n",
                event_name, name_buf, dev_info, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("%s  name=%s  dev=%s  node=%s\r\n",
            event_name, name_buf, dev_info, dev_path);
    return 0;
}

static int cmd_inputinfo(char **argv, int argc) {
    if (argc >= 2) {
        char event_name[32];

        if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
            a90_console_printf("inputinfo: invalid event name\r\n");
            return -EINVAL;
        }
        return print_input_event_info(event_name);
    }

    {
        DIR *dir = opendir("/sys/class/input");
        struct dirent *entry;
        int first_error = 0;
        bool printed = false;

        if (dir == NULL) {
            a90_console_printf("inputinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "event", 5) == 0) {
                int result = print_input_event_info(entry->d_name);
                if (result == 0) {
                    printed = true;
                } else if (first_error == 0) {
                    first_error = result;
                }
            }
        }

        closedir(dir);
        return printed ? 0 : first_error;
    }
}

static void print_drm_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/drm/%s", entry_name) >= (int)sizeof(base_path)) {
        a90_console_printf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        a90_console_printf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        a90_console_printf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (((strncmp(entry_name, "card", 4) == 0) && strchr(entry_name, '-') == NULL) ||
            strncmp(entry_name, "renderD", 7) == 0 ||
            strncmp(entry_name, "controlD", 8) == 0) {
            if (get_char_device_path(path, "/dev/dri", entry_name,
                                     node_path, sizeof(node_path)) == 0) {
                a90_console_printf("  node=%s", node_path);
            } else {
                a90_console_printf("  node=<error:%s>", strerror(errno));
            }
        }
        a90_console_printf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/status", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  status=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/enabled", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  enabled=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/dpms", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  dpms=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        a90_console_printf("  modes=%s\r\n", value);
    }

    if (!printed_header) {
        a90_console_printf("%s\r\n", entry_name);
    }
}

static int cmd_drminfo(char **argv, int argc) {
    if (argc >= 2) {
        print_drm_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/drm");
        struct dirent *entry;

        if (dir == NULL) {
            a90_console_printf("drminfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (entry->d_name[0] == '.') {
                continue;
            }
            print_drm_entry_info(entry->d_name);
        }

        closedir(dir);
        return 0;
    }
}

static void print_fb_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/graphics/%s", entry_name) >= (int)sizeof(base_path)) {
        a90_console_printf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        a90_console_printf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        a90_console_printf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (get_char_device_path(path, "/dev/graphics", entry_name,
                                 node_path, sizeof(node_path)) == 0) {
            a90_console_printf("  node=%s", node_path);
        } else {
            a90_console_printf("  node=<error:%s>", strerror(errno));
        }
        a90_console_printf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/name", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  name=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/bits_per_pixel", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  bits_per_pixel=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/virtual_size", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  virtual_size=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        a90_console_printf("  modes=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/blank", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  blank=%s\r\n", value);
    }

    if (!printed_header) {
        a90_console_printf("%s\r\n", entry_name);
    }
}

static int cmd_fbinfo(char **argv, int argc) {
    if (argc >= 2) {
        print_fb_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/graphics");
        struct dirent *entry;

        if (dir == NULL) {
            a90_console_printf("fbinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "fb", 2) == 0) {
                print_fb_entry_info(entry->d_name);
            }
        }

        closedir(dir);
        return 0;
    }
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

static int drm_ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);

    return rc;
}

static int ensure_card0_path(char *out, size_t out_size) {
    return get_char_device_path("/sys/class/drm/card0/dev", "/dev/dri", "card0", out, out_size);
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

    if (ensure_card0_path(node_path, node_path_size) < 0) {
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

static void *kms_active_map(struct kms_display_state *state) {
    return state->map[state->current_buffer];
}

static uint32_t kms_pack_rgb_for_xbgr8888(uint32_t color) {
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;

    return ((uint32_t)blue << 16) | ((uint32_t)green << 8) | red;
}

static void kms_fill_color(struct kms_display_state *state, uint32_t color) {
    size_t y;
    uint32_t pixel = kms_pack_rgb_for_xbgr8888(color);
    void *map = kms_active_map(state);

    if (map == NULL || map == MAP_FAILED) {
        return;
    }

    for (y = 0; y < state->height; ++y) {
        uint32_t *row = (uint32_t *)((char *)map + (y * state->stride));
        size_t x;

        for (x = 0; x < state->width; ++x) {
            row[x] = pixel;
        }
    }
}

static void kms_fill_rect(struct kms_display_state *state,
                          uint32_t x,
                          uint32_t y,
                          uint32_t width,
                          uint32_t height,
                          uint32_t color) {
    uint32_t pixel = kms_pack_rgb_for_xbgr8888(color);
    uint32_t y_end;
    void *map = kms_active_map(state);

    if (map == NULL || map == MAP_FAILED || x >= state->width || y >= state->height) {
        return;
    }

    if (x + width > state->width) {
        width = state->width - x;
    }
    if (y + height > state->height) {
        height = state->height - y;
    }

    y_end = y + height;
    while (y < y_end) {
        uint32_t *row = (uint32_t *)((char *)map + (y * state->stride));
        uint32_t x_end = x + width;
        uint32_t cursor = x;

        while (cursor < x_end) {
            row[cursor++] = pixel;
        }
        ++y;
    }
}

static void kms_draw_boot_frame(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t header_h = height / 8;
    uint32_t footer_h = height / 7;
    uint32_t gap = width / 40;
    uint32_t footer_w = (width - (gap * 4)) / 3;
    uint32_t footer_y = height - footer_h - gap;

    kms_fill_color(state, 0x080808);
    kms_fill_rect(state, 0, 0, width, header_h, 0x2a2a2a);
    kms_fill_rect(state, gap, gap, width / 5, gap / 2 + 6, 0x0090ca);
    kms_fill_rect(state, gap, footer_y, footer_w, footer_h, 0x202020);
    kms_fill_rect(state, gap * 2 + footer_w, footer_y, footer_w, footer_h, 0x0090ca);
    kms_fill_rect(state, gap * 3 + footer_w * 2, footer_y, footer_w, footer_h, 0x202020);
}

static void __attribute__((unused)) kms_draw_visibility_probe(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t border = width / 12;
    uint32_t mid_w = width / 3;
    uint32_t mid_h = height / 10;
    uint32_t center_x = (width - mid_w) / 2;
    uint32_t center_y = (height - mid_h) / 2;

    kms_fill_color(state, 0x000000);
    kms_fill_rect(state, 0, 0, width, border, 0xffffff);
    kms_fill_rect(state, 0, height - border, width, border, 0xffffff);
    kms_fill_rect(state, 0, 0, border, height, 0xffffff);
    kms_fill_rect(state, width - border, 0, border, height, 0xffffff);
    kms_fill_rect(state, center_x, center_y, mid_w, mid_h, 0xffffff);
    kms_fill_rect(state, width / 12, height / 6, width / 5, border, 0xff0000);
    kms_fill_rect(state, width / 12, height / 6 + border * 2, width / 5, border, 0x00ff00);
    kms_fill_rect(state, width / 12, height / 6 + border * 4, width / 5, border, 0x0000ff);
}

static void kms_draw_block_t(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t stem_x = x + ((width - stroke) / 2);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, stem_x, y, stroke, height, color);
}

static void kms_draw_block_e(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    kms_fill_rect(state, x, y, stroke, height, color);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, x, mid_y, width - stroke / 2, stroke, color);
    kms_fill_rect(state, x, y + height - stroke, width, stroke, color);
}

static void kms_draw_block_s(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, x, y, stroke, mid_y - y + stroke, color);
    kms_fill_rect(state, x, mid_y, width, stroke, color);
    kms_fill_rect(state, x + width - stroke, mid_y, stroke, y + height - mid_y, color);
    kms_fill_rect(state, x, y + height - stroke, width, stroke, color);
}

static void kms_draw_giant_test_probe(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t border = width / 20;
    uint32_t stroke = width / 22;
    uint32_t letter_h = (height * 11) / 32;
    uint32_t t_w = stroke * 5;
    uint32_t e_w = stroke * 4;
    uint32_t s_w = stroke * 4;
    uint32_t gap = stroke;
    uint32_t start_x;
    uint32_t start_y;
    uint32_t label_h = stroke * 2;

    if (stroke < 18) {
        stroke = 18;
    }
    if (letter_h < stroke * 7) {
        letter_h = stroke * 7;
    }
    start_x = (width - (t_w + e_w + s_w + t_w + gap * 3)) / 2;
    start_y = (height - letter_h) / 2;

    kms_fill_color(state, 0x000000);
    kms_fill_rect(state, 0, 0, width, border, 0xffffff);
    kms_fill_rect(state, 0, height - border, width, border, 0xffffff);
    kms_fill_rect(state, 0, 0, border, height, 0xffffff);
    kms_fill_rect(state, width - border, 0, border, height, 0xffffff);
    kms_fill_rect(state, border * 2, border * 2, width - border * 4, label_h, 0x00a0ff);
    kms_fill_rect(state, border * 2, height - border * 3, width - border * 4, stroke, 0xffa000);

    kms_draw_block_t(state, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
    start_x += t_w + gap;
    kms_draw_block_e(state, start_x, start_y, stroke, e_w, letter_h, 0xffffff);
    start_x += e_w + gap;
    kms_draw_block_s(state, start_x, start_y, stroke, s_w, letter_h, 0xffffff);
    start_x += s_w + gap;
    kms_draw_block_t(state, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
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

static void kms_draw_char(struct kms_display_state *state,
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
                kms_fill_rect(state,
                              x + (col * scale),
                              y + (row * scale),
                              scale,
                              scale,
                              color);
            }
        }
    }
}

static void kms_draw_text(struct kms_display_state *state,
                          uint32_t x,
                          uint32_t y,
                          const char *text,
                          uint32_t color,
                          uint32_t scale) {
    while (*text != '\0') {
        kms_draw_char(state, x, y, *text, color, scale);
        x += scale * 6;
        ++text;
    }
}
