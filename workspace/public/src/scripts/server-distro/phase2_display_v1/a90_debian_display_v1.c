/*
 * A90 Debian VT-less direct-DRM presenter.
 *
 * This process is launched by sysvinit after switch_root. It requires the
 * native release marker, proves that no DRM descriptor remains, acquires the
 * primary DRM master exactly once, drops to the dedicated display identity,
 * and presents a static Debian-owned framebuffer. It opens no network socket.
 */
#include "a90_draw.h"

#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#ifndef DRM_MODE_CONNECTED
#define DRM_MODE_CONNECTED 1
#endif

#define A90_DISPLAY_UID 3904
#define A90_DISPLAY_GID 3904
#define A90_DISPLAY_RUN_DIR "/run/a90-display"
#define A90_DISPLAY_MARKER A90_DISPLAY_RUN_DIR "/ready"
#define A90_DISPLAY_MARKER_TMP A90_DISPLAY_RUN_DIR "/ready.tmp"
#define A90_NATIVE_RELEASE_MARKER "/run/a90-native-display-release"
#define A90_CARD0_SYSFS "/sys/class/drm/card0/dev"
#define A90_CARD0_NODE "/dev/dri/card0"
#define A90_MAX_MARKER_BYTES 2048U

struct a90_display_kms {
    int fd;
    unsigned int drm_major;
    unsigned int drm_minor;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t handle;
    struct drm_mode_modeinfo mode;
    struct a90_fb fb;
};

static volatile sig_atomic_t keep_running = 1;

static void handle_stop(int signo) {
    (void)signo;
    keep_running = 0;
}

static int drm_ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);
    return rc;
}

static int write_all(int fd, const char *text, size_t size) {
    size_t offset = 0;

    while (offset < size) {
        ssize_t written = write(fd, text + offset, size - offset);

        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if (written == 0) {
            return -EIO;
        }
        offset += (size_t)written;
    }
    return 0;
}

static int read_small_regular_file(const char *path,
                                   char *out,
                                   size_t out_size,
                                   bool require_root_owner) {
    struct stat st;
    size_t offset = 0;
    int fd;

    if (out == NULL || out_size < 2U) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &st) < 0) {
        int rc = -errno;

        close(fd);
        return rc;
    }
    if (!S_ISREG(st.st_mode) ||
        (require_root_owner &&
         (st.st_uid != 0 || (st.st_mode & (S_IWGRP | S_IWOTH)) != 0))) {
        close(fd);
        return -EPERM;
    }
    while (offset < out_size - 1U) {
        ssize_t nread = read(fd, out + offset, out_size - 1U - offset);

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            {
                int rc = -errno;

                close(fd);
                return rc;
            }
        }
        if (nread == 0) {
            break;
        }
        offset += (size_t)nread;
    }
    if (offset == out_size - 1U) {
        char extra;
        ssize_t nread;

        do {
            nread = read(fd, &extra, 1U);
        } while (nread < 0 && errno == EINTR);
        if (nread < 0) {
            int rc = -errno;

            close(fd);
            return rc;
        }
        if (nread != 0) {
            close(fd);
            return -EFBIG;
        }
    }
    if (close(fd) < 0) {
        return -errno;
    }
    out[offset] = '\0';
    return 0;
}

static bool has_exact_line(const char *text, const char *expected) {
    size_t expected_size = strlen(expected);
    const char *cursor = text;

    while (cursor != NULL && *cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t size = end == NULL ? strlen(cursor) : (size_t)(end - cursor);

        if (size == expected_size &&
            memcmp(cursor, expected, expected_size) == 0) {
            return true;
        }
        cursor = end == NULL ? NULL : end + 1;
    }
    return false;
}

static int validate_native_release_marker(void) {
    char marker[A90_MAX_MARKER_BYTES];
    static const char *const required[] = {
        "schema=a90-native-display-release-v1",
        "native_pid1_drm_fd_count=0",
        "other_drm_fd_count=0",
        "native_kms_initialized=0",
        "display_services_restart_blocked=1",
        "release_complete=1",
    };
    size_t index;
    int rc = read_small_regular_file(
        A90_NATIVE_RELEASE_MARKER,
        marker,
        sizeof(marker),
        true);

    if (rc < 0) {
        return rc;
    }
    for (index = 0; index < sizeof(required) / sizeof(required[0]); ++index) {
        if (!has_exact_line(marker, required[index])) {
            return -EPROTO;
        }
    }
    return 0;
}

static int read_device_number(const char *path,
                              unsigned int *major_out,
                              unsigned int *minor_out) {
    char text[64];
    char trailing;
    int rc = read_small_regular_file(path, text, sizeof(text), true);

    if (rc < 0) {
        return rc;
    }
    if (sscanf(text, "%u:%u %c", major_out, minor_out, &trailing) != 2) {
        return -EINVAL;
    }
    return 0;
}

static int ensure_card0_node(unsigned int *major_out,
                              unsigned int *minor_out) {
    struct stat st;
    unsigned int major_num;
    unsigned int minor_num;
    dev_t expected;
    int rc;

    if (major_out == NULL || minor_out == NULL) {
        return -EINVAL;
    }
    rc = read_device_number(A90_CARD0_SYSFS, &major_num, &minor_num);
    if (rc < 0) {
        return rc;
    }
    expected = makedev(major_num, minor_num);
    if (mkdir("/dev/dri", 0755) < 0 && errno != EEXIST) {
        return -errno;
    }
    if (lstat(A90_CARD0_NODE, &st) == 0) {
        if (!S_ISCHR(st.st_mode) || st.st_rdev != expected) {
            return -EPERM;
        }
    } else {
        if (errno != ENOENT) {
            return -errno;
        }
        if (mknod(A90_CARD0_NODE, S_IFCHR | 0660, expected) < 0) {
            return -errno;
        }
    }
    if (chown(A90_CARD0_NODE, 0, A90_DISPLAY_GID) < 0 ||
        chmod(A90_CARD0_NODE, 0660) < 0) {
        return -errno;
    }
    *major_out = major_num;
    *minor_out = minor_num;
    return 0;
}

static bool drm_fd_target(const char *target) {
    return target != NULL &&
           (strstr(target, "/dev/dri/") != NULL ||
            strstr(target, "card0") != NULL);
}

static int count_pid_drm_fds(pid_t pid, unsigned int *count_out) {
    char directory_path[64];
    DIR *directory;
    struct dirent *entry;
    unsigned int count = 0;

    if (pid <= 0 || count_out == NULL) {
        return -EINVAL;
    }
    snprintf(
        directory_path,
        sizeof(directory_path),
        "/proc/%ld/fd",
        (long)pid);
    directory = opendir(directory_path);
    if (directory == NULL) {
        if (errno == ENOENT || errno == ESRCH) {
            *count_out = 0;
            return 0;
        }
        return -errno;
    }
    while ((entry = readdir(directory)) != NULL) {
        char fd_path[128];
        char target[512];
        ssize_t size;

        if (entry->d_name[0] == '.') {
            continue;
        }
        if (snprintf(
                fd_path,
                sizeof(fd_path),
                "%s/%s",
                directory_path,
                entry->d_name) >= (int)sizeof(fd_path)) {
            closedir(directory);
            return -ENAMETOOLONG;
        }
        size = readlink(fd_path, target, sizeof(target) - 1U);
        if (size < 0) {
            if (errno == ENOENT || errno == ESRCH) {
                continue;
            }
            {
                int rc = -errno;

                closedir(directory);
                return rc;
            }
        }
        target[size] = '\0';
        if (drm_fd_target(target)) {
            count++;
        }
    }
    closedir(directory);
    *count_out = count;
    return 0;
}

static int count_process_state(pid_t self,
                               unsigned int *self_drm_fds_out,
                               unsigned int *other_drm_fds_out,
                               unsigned int *native_init_processes_out) {
    DIR *proc;
    struct dirent *entry;
    unsigned int self_drm_fds = 0;
    unsigned int other_drm_fds = 0;
    unsigned int native_init_processes = 0;

    if (self_drm_fds_out == NULL ||
        other_drm_fds_out == NULL ||
        native_init_processes_out == NULL) {
        return -EINVAL;
    }
    proc = opendir("/proc");
    if (proc == NULL) {
        return -errno;
    }
    while ((entry = readdir(proc)) != NULL) {
        char *end = NULL;
        long value;
        pid_t pid;
        unsigned int count = 0;
        char exe_path[64];
        char exe[512];
        ssize_t exe_size;
        int rc;

        errno = 0;
        value = strtol(entry->d_name, &end, 10);
        if (errno != 0 || end == entry->d_name || *end != '\0' ||
            value <= 0) {
            continue;
        }
        pid = (pid_t)value;
        rc = count_pid_drm_fds(pid, &count);
        if (rc < 0) {
            closedir(proc);
            return rc;
        }
        if (pid == self) {
            self_drm_fds += count;
        } else {
            other_drm_fds += count;
        }
        snprintf(exe_path, sizeof(exe_path), "/proc/%ld/exe", (long)pid);
        exe_size = readlink(exe_path, exe, sizeof(exe) - 1U);
        if (exe_size >= 0) {
            exe[exe_size] = '\0';
            if (strcmp(exe, "/init") == 0) {
                native_init_processes++;
            }
        } else if (errno != ENOENT && errno != ESRCH) {
            int saved_errno = errno;

            closedir(proc);
            return -saved_errno;
        }
    }
    closedir(proc);
    *self_drm_fds_out = self_drm_fds;
    *other_drm_fds_out = other_drm_fds;
    *native_init_processes_out = native_init_processes;
    return 0;
}

static int drm_get_cap(int fd, uint64_t capability, uint64_t *value_out) {
    struct drm_get_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    if (drm_ioctl_retry(fd, DRM_IOCTL_GET_CAP, &cap) < 0) {
        return -1;
    }
    *value_out = cap.value;
    return 0;
}

static int fetch_resources(int fd,
                           struct drm_mode_card_res *resources,
                           uint32_t **crtcs_out,
                           uint32_t **connectors_out,
                           uint32_t **encoders_out) {
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;

    memset(resources, 0, sizeof(*resources));
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, resources) < 0) {
        return -1;
    }
    if (resources->count_crtcs != 0U) {
        crtcs = calloc(resources->count_crtcs, sizeof(*crtcs));
    }
    if (resources->count_connectors != 0U) {
        connectors = calloc(resources->count_connectors, sizeof(*connectors));
    }
    if (resources->count_encoders != 0U) {
        encoders = calloc(resources->count_encoders, sizeof(*encoders));
    }
    if ((resources->count_crtcs != 0U && crtcs == NULL) ||
        (resources->count_connectors != 0U && connectors == NULL) ||
        (resources->count_encoders != 0U && encoders == NULL)) {
        free(crtcs);
        free(connectors);
        free(encoders);
        errno = ENOMEM;
        return -1;
    }
    resources->crtc_id_ptr = (uintptr_t)crtcs;
    resources->connector_id_ptr = (uintptr_t)connectors;
    resources->encoder_id_ptr = (uintptr_t)encoders;
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, resources) < 0) {
        free(crtcs);
        free(connectors);
        free(encoders);
        return -1;
    }
    *crtcs_out = crtcs;
    *connectors_out = connectors;
    *encoders_out = encoders;
    return 0;
}

static int select_crtc(const struct drm_mode_get_encoder *encoder,
                       const uint32_t *crtcs,
                       uint32_t count,
                       uint32_t *crtc_out) {
    uint32_t index;

    if (encoder->crtc_id != 0U) {
        for (index = 0; index < count; ++index) {
            if (crtcs[index] == encoder->crtc_id) {
                *crtc_out = encoder->crtc_id;
                return 0;
            }
        }
    }
    for (index = 0; index < count; ++index) {
        if ((encoder->possible_crtcs & (1U << index)) != 0U) {
            *crtc_out = crtcs[index];
            return 0;
        }
    }
    errno = ENODEV;
    return -1;
}

static int choose_output(int fd, struct a90_display_kms *kms) {
    struct drm_mode_card_res resources;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t index;
    int rc = -1;

    if (fetch_resources(
            fd,
            &resources,
            &crtcs,
            &connectors,
            &encoders) < 0) {
        return -1;
    }
    for (index = 0; index < resources.count_connectors; ++index) {
        struct drm_mode_get_connector connector;
        struct drm_mode_modeinfo *modes = NULL;
        uint32_t *connector_encoders = NULL;
        uint32_t *connector_props = NULL;
        uint64_t *connector_prop_values = NULL;
        uint32_t encoder_id;
        struct drm_mode_get_encoder encoder;
        int mode_index = -1;
        uint32_t item;

        memset(&connector, 0, sizeof(connector));
        connector.connector_id = connectors[index];
        if (drm_ioctl_retry(
                fd,
                DRM_IOCTL_MODE_GETCONNECTOR,
                &connector) < 0) {
            continue;
        }
        if (connector.count_modes != 0U) {
            modes = calloc(connector.count_modes, sizeof(*modes));
        }
        if (connector.count_encoders != 0U) {
            connector_encoders = calloc(
                connector.count_encoders,
                sizeof(*connector_encoders));
        }
        if (connector.count_props != 0U) {
            connector_props = calloc(
                connector.count_props,
                sizeof(*connector_props));
            connector_prop_values = calloc(
                connector.count_props,
                sizeof(*connector_prop_values));
        }
        if ((connector.count_modes != 0U && modes == NULL) ||
            (connector.count_encoders != 0U &&
             connector_encoders == NULL) ||
            (connector.count_props != 0U &&
             (connector_props == NULL || connector_prop_values == NULL))) {
            free(modes);
            free(connector_encoders);
            free(connector_props);
            free(connector_prop_values);
            errno = ENOMEM;
            break;
        }
        connector.modes_ptr = (uintptr_t)modes;
        connector.encoders_ptr = (uintptr_t)connector_encoders;
        connector.props_ptr = (uintptr_t)connector_props;
        connector.prop_values_ptr = (uintptr_t)connector_prop_values;
        if (drm_ioctl_retry(
                fd,
                DRM_IOCTL_MODE_GETCONNECTOR,
                &connector) < 0) {
            free(modes);
            free(connector_encoders);
            free(connector_props);
            free(connector_prop_values);
            continue;
        }
        if (connector.connection != DRM_MODE_CONNECTED ||
            connector.count_modes == 0U) {
            free(modes);
            free(connector_encoders);
            free(connector_props);
            free(connector_prop_values);
            continue;
        }
        for (item = 0; item < connector.count_modes; ++item) {
            if ((modes[item].type & DRM_MODE_TYPE_PREFERRED) != 0U) {
                mode_index = (int)item;
                break;
            }
        }
        if (mode_index < 0) {
            mode_index = 0;
        }
        encoder_id = connector.encoder_id;
        if (encoder_id == 0U && connector.count_encoders != 0U) {
            encoder_id = connector_encoders[0];
        }
        memset(&encoder, 0, sizeof(encoder));
        encoder.encoder_id = encoder_id;
        if (encoder_id != 0U &&
            drm_ioctl_retry(
                fd,
                DRM_IOCTL_MODE_GETENCODER,
                &encoder) == 0 &&
            select_crtc(
                &encoder,
                crtcs,
                resources.count_crtcs,
                &kms->crtc_id) == 0) {
            kms->connector_id = connector.connector_id;
            kms->encoder_id = encoder_id;
            kms->mode = modes[mode_index];
            rc = 0;
        }
        free(modes);
        free(connector_encoders);
        free(connector_props);
        free(connector_prop_values);
        if (rc == 0) {
            break;
        }
    }
    free(crtcs);
    free(connectors);
    free(encoders);
    if (rc < 0 && errno == 0) {
        errno = ENODEV;
    }
    return rc;
}

static void kms_init_empty(struct a90_display_kms *kms) {
    memset(kms, 0, sizeof(*kms));
    kms->fd = -1;
    kms->fb.pixels = MAP_FAILED;
}

static void cleanup_kms(struct a90_display_kms *kms) {
    if (kms->fd >= 0 && kms->crtc_id != 0U) {
        struct drm_mode_crtc disable;

        memset(&disable, 0, sizeof(disable));
        disable.crtc_id = kms->crtc_id;
        (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_SETCRTC, &disable);
    }
    if (kms->fb.pixels != NULL && kms->fb.pixels != MAP_FAILED) {
        (void)munmap(kms->fb.pixels, kms->fb.size);
        kms->fb.pixels = MAP_FAILED;
    }
    if (kms->fd >= 0 && kms->fb_id != 0U) {
        uint32_t fb_id = kms->fb_id;

        (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_RMFB, &fb_id);
        kms->fb_id = 0U;
    }
    if (kms->fd >= 0 && kms->handle != 0U) {
        struct drm_mode_destroy_dumb destroy;

        memset(&destroy, 0, sizeof(destroy));
        destroy.handle = kms->handle;
        (void)drm_ioctl_retry(
            kms->fd,
            DRM_IOCTL_MODE_DESTROY_DUMB,
            &destroy);
        kms->handle = 0U;
    }
    if (kms->fd >= 0) {
        (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_DROP_MASTER, NULL);
        (void)close(kms->fd);
        kms->fd = -1;
    }
}

static int initialize_kms(struct a90_display_kms *kms,
                          const char **failure_stage_out) {
    struct drm_mode_create_dumb create;
    struct drm_mode_fb_cmd2 addfb;
    struct drm_mode_map_dumb map;
    uint64_t dumb_buffer = 0;
    int fd_flags;

    if (failure_stage_out == NULL) {
        errno = EINVAL;
        return -1;
    }
    *failure_stage_out = "ensure-card0-node";
    if (ensure_card0_node(&kms->drm_major, &kms->drm_minor) < 0) {
        return -1;
    }
    *failure_stage_out = "open-card0";
    kms->fd = open(A90_CARD0_NODE, O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (kms->fd < 0) {
        return -1;
    }
    *failure_stage_out = "set-cloexec";
    fd_flags = fcntl(kms->fd, F_GETFD);
    if (fd_flags < 0 ||
        fcntl(kms->fd, F_SETFD, fd_flags | FD_CLOEXEC) < 0) {
        return -1;
    }
    *failure_stage_out = "set-master";
    if (drm_ioctl_retry(kms->fd, DRM_IOCTL_SET_MASTER, NULL) < 0) {
        return -1;
    }
    *failure_stage_out = "dumb-buffer-cap";
    if (drm_get_cap(
            kms->fd,
            DRM_CAP_DUMB_BUFFER,
            &dumb_buffer) < 0 ||
        dumb_buffer == 0U) {
        errno = ENOTSUP;
        return -1;
    }
    *failure_stage_out = "choose-connected-output";
    if (choose_output(kms->fd, kms) < 0) {
        return -1;
    }

    *failure_stage_out = "create-dumb-buffer";
    memset(&create, 0, sizeof(create));
    create.width = kms->mode.hdisplay;
    create.height = kms->mode.vdisplay;
    create.bpp = 32;
    if (drm_ioctl_retry(
            kms->fd,
            DRM_IOCTL_MODE_CREATE_DUMB,
            &create) < 0) {
        return -1;
    }
    kms->handle = create.handle;
    kms->fb.width = create.width;
    kms->fb.height = create.height;
    kms->fb.stride = create.pitch;
    kms->fb.size = create.size;

    *failure_stage_out = "add-framebuffer";
    memset(&addfb, 0, sizeof(addfb));
    addfb.width = create.width;
    addfb.height = create.height;
    addfb.pixel_format = DRM_FORMAT_XBGR8888;
    addfb.handles[0] = create.handle;
    addfb.pitches[0] = create.pitch;
    if (drm_ioctl_retry(
            kms->fd,
            DRM_IOCTL_MODE_ADDFB2,
            &addfb) < 0) {
        return -1;
    }
    kms->fb_id = addfb.fb_id;

    *failure_stage_out = "map-dumb-buffer";
    memset(&map, 0, sizeof(map));
    map.handle = create.handle;
    if (drm_ioctl_retry(
            kms->fd,
            DRM_IOCTL_MODE_MAP_DUMB,
            &map) < 0) {
        return -1;
    }
    *failure_stage_out = "mmap-dumb-buffer";
    kms->fb.pixels = mmap(
        NULL,
        create.size,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        kms->fd,
        (off_t)map.offset);
    if (kms->fb.pixels == MAP_FAILED) {
        return -1;
    }
    *failure_stage_out = "complete";
    return 0;
}

static int present(struct a90_display_kms *kms) {
    struct drm_mode_crtc setcrtc;
    uint32_t connector = kms->connector_id;

    memset(&setcrtc, 0, sizeof(setcrtc));
    setcrtc.crtc_id = kms->crtc_id;
    setcrtc.fb_id = kms->fb_id;
    setcrtc.set_connectors_ptr = (uintptr_t)&connector;
    setcrtc.count_connectors = 1U;
    setcrtc.mode = kms->mode;
    setcrtc.mode_valid = 1U;
    return drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_SETCRTC, &setcrtc);
}

static void render(struct a90_display_kms *kms) {
    struct a90_fb *fb = &kms->fb;
    uint32_t margin = fb->width / 14U;
    uint32_t card_width = fb->width - margin * 2U;
    uint32_t scale = fb->width >= 1080U ? 6U : 4U;

    a90_draw_clear(fb, 0x020713);
    a90_draw_rect(fb, 0, 0, fb->width, fb->height / 32U, 0x0b2a55);
    a90_draw_rect(
        fb,
        margin,
        fb->height / 5U,
        card_width,
        fb->height / 3U,
        0x101820);
    a90_draw_rect_outline(
        fb,
        margin,
        fb->height / 5U,
        card_width,
        fb->height / 3U,
        4U,
        0x1aa3ff);
    a90_draw_text_fit(
        fb,
        margin + 32U,
        fb->height / 5U + 60U,
        "A90 DEBIAN",
        0xffffff,
        scale + 2U,
        card_width - 64U);
    a90_draw_text_fit(
        fb,
        margin + 32U,
        fb->height / 5U + 180U,
        "DIRECT DRM SESSION",
        0xffcc33,
        scale,
        card_width - 64U);
    a90_draw_text_fit(
        fb,
        margin + 32U,
        fb->height / 5U + 280U,
        "PID 1: SYSVINIT / VT: NONE",
        0x88ee88,
        scale - 1U,
        card_width - 64U);
    a90_draw_text_fit(
        fb,
        margin + 32U,
        fb->height / 5U + 360U,
        "DISPLAY OWNER: DEBIAN",
        0x88ee88,
        scale - 1U,
        card_width - 64U);
}

static int read_cap_eff(char *out, size_t out_size);

static int drop_privileges(char *cap_eff, size_t cap_eff_size) {
    int rc;

    if (geteuid() != 0) {
        return -EPERM;
    }
    if (setgroups(0, NULL) < 0 ||
        setgid(A90_DISPLAY_GID) < 0 ||
        setuid(A90_DISPLAY_UID) < 0 ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) {
        return -errno;
    }
    if (geteuid() != A90_DISPLAY_UID ||
        getegid() != A90_DISPLAY_GID ||
        prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1) {
        return -EPERM;
    }
    rc = read_cap_eff(cap_eff, cap_eff_size);
    if (rc < 0) {
        return rc;
    }
    return 0;
}

static int read_cap_eff(char *out, size_t out_size) {
    char status[4096];
    char *line;
    int rc = read_small_regular_file(
        "/proc/self/status",
        status,
        sizeof(status),
        false);

    if (rc < 0) {
        return rc;
    }
    line = strstr(status, "CapEff:\t");
    if (line == NULL || (line != status && line[-1] != '\n')) {
        return -EPROTO;
    }
    line += 8;
    if (strlen(line) < 16U || out_size < 17U) {
        return -EPROTO;
    }
    memcpy(out, line, 16U);
    out[16] = '\0';
    if (strcmp(out, "0000000000000000") != 0) {
        return -EPERM;
    }
    return 0;
}

static unsigned int mode_refresh(const struct drm_mode_modeinfo *mode) {
    uint64_t denominator;

    if (mode->clock == 0U || mode->htotal == 0U || mode->vtotal == 0U) {
        return 0U;
    }
    denominator = (uint64_t)mode->htotal * (uint64_t)mode->vtotal;
    return (unsigned int)(
        ((uint64_t)mode->clock * 1000ULL + denominator / 2ULL) /
        denominator);
}

static int write_ready_marker(const struct a90_display_kms *kms,
                              const char *pid1_exe,
                              const char *cap_eff,
                              unsigned int self_drm_fds,
                              unsigned int other_drm_fds,
                              unsigned int native_init_processes) {
    char marker[2048];
    int fd;
    int size;
    int rc;

    if (pid1_exe == NULL || strcmp(pid1_exe, "/usr/sbin/init") != 0 ||
        cap_eff == NULL || strcmp(cap_eff, "0000000000000000") != 0) {
        return -EPROTO;
    }
    size = snprintf(
        marker,
        sizeof(marker),
        "schema=a90-debian-display-v1\n"
        "pid1_exe=%s\n"
        "presenter_pid=%ld\n"
        "presenter_uid=%ld\n"
        "presenter_gid=%ld\n"
        "presenter_cap_eff=%s\n"
        "no_new_privs=1\n"
        "controlling_vt=none\n"
        "drm_node=%s\n"
        "drm_node_major_minor=%u:%u\n"
        "drm_master=1\n"
        "connector_id=%u\n"
        "crtc_id=%u\n"
        "mode=%ux%u@%u\n"
        "setcrtc_rc=0\n"
        "native_pid1_drm_fd_count=0\n"
        "other_native_drm_fd_count=0\n"
        "presenter_self_drm_fd_count=%u\n"
        "other_process_drm_fd_count=%u\n"
        "native_init_process_count=%u\n",
        pid1_exe,
        (long)getpid(),
        (long)geteuid(),
        (long)getegid(),
        cap_eff,
        A90_CARD0_NODE,
        kms->drm_major,
        kms->drm_minor,
        kms->connector_id,
        kms->crtc_id,
        kms->mode.hdisplay,
        kms->mode.vdisplay,
        mode_refresh(&kms->mode),
        self_drm_fds,
        other_drm_fds,
        native_init_processes);
    if (size < 0 || (size_t)size >= sizeof(marker)) {
        return -EOVERFLOW;
    }
    (void)unlink(A90_DISPLAY_MARKER_TMP);
    fd = open(
        A90_DISPLAY_MARKER_TMP,
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
        0600);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all(fd, marker, (size_t)size);
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc < 0) {
        (void)unlink(A90_DISPLAY_MARKER_TMP);
        return rc;
    }
    if (rename(A90_DISPLAY_MARKER_TMP, A90_DISPLAY_MARKER) < 0) {
        rc = -errno;
        (void)unlink(A90_DISPLAY_MARKER_TMP);
        return rc;
    }
    return 0;
}

int main(int argc, char **argv) {
    struct a90_display_kms kms;
    char cap_eff[17];
    char pid1_exe[512];
    ssize_t pid1_size;
    unsigned int self_drm_fds = 0;
    unsigned int other_drm_fds = 0;
    unsigned int native_init_processes = 0;
    const char *kms_failure_stage = "not-started";
    int rc = 1;

    (void)argv;
    kms_init_empty(&kms);
    if (argc != 1) {
        fprintf(stderr, "a90-debian-display-v1: no arguments accepted\n");
        return 64;
    }
    if (getsid(0) != getpid() && setsid() < 0) {
        fprintf(stderr, "a90-debian-display-v1: setsid: %s\n", strerror(errno));
        return 65;
    }
    signal(SIGTERM, handle_stop);
    signal(SIGINT, handle_stop);
    signal(SIGHUP, handle_stop);

    if (validate_native_release_marker() < 0) {
        fprintf(stderr, "a90-debian-display-v1: native release marker invalid\n");
        goto out;
    }
    if (count_process_state(
            getpid(),
            &self_drm_fds,
            &other_drm_fds,
            &native_init_processes) < 0 ||
        self_drm_fds != 0U ||
        other_drm_fds != 0U ||
        native_init_processes != 0U) {
        fprintf(
            stderr,
            "a90-debian-display-v1: pre-open owner scan self=%u other=%u init=%u\n",
            self_drm_fds,
            other_drm_fds,
            native_init_processes);
        goto out;
    }
    if (initialize_kms(&kms, &kms_failure_stage) < 0) {
        int saved_errno = errno;

        fprintf(
            stderr,
            "a90-debian-display-v1: KMS init stage=%s errno=%d error=%s\n",
            kms_failure_stage,
            saved_errno,
            strerror(saved_errno));
        goto out;
    }
    if (count_process_state(
            getpid(),
            &self_drm_fds,
            &other_drm_fds,
            &native_init_processes) < 0 ||
        self_drm_fds != 1U ||
        other_drm_fds != 0U ||
        native_init_processes != 0U) {
        fprintf(
            stderr,
            "a90-debian-display-v1: post-open owner scan self=%u other=%u init=%u\n",
            self_drm_fds,
            other_drm_fds,
            native_init_processes);
        goto out;
    }
    pid1_size = readlink("/proc/1/exe", pid1_exe, sizeof(pid1_exe) - 1U);
    if (pid1_size < 0) {
        fprintf(stderr, "a90-debian-display-v1: PID1 identity unreadable\n");
        goto out;
    }
    pid1_exe[pid1_size] = '\0';
    if (strcmp(pid1_exe, "/usr/sbin/init") != 0) {
        fprintf(stderr, "a90-debian-display-v1: PID1 identity mismatch\n");
        goto out;
    }
    if (drop_privileges(cap_eff, sizeof(cap_eff)) < 0) {
        fprintf(stderr, "a90-debian-display-v1: privilege drop failed\n");
        goto out;
    }
    render(&kms);
    if (present(&kms) < 0) {
        int saved_errno = errno;

        fprintf(
            stderr,
            "a90-debian-display-v1: SETCRTC errno=%d error=%s\n",
            saved_errno,
            strerror(saved_errno));
        goto out;
    }
    if (write_ready_marker(
            &kms,
            pid1_exe,
            cap_eff,
            self_drm_fds,
            other_drm_fds,
            native_init_processes) < 0) {
        fprintf(stderr, "a90-debian-display-v1: ready marker failed\n");
        goto out;
    }
    fprintf(
        stderr,
        "a90-debian-display-v1: ready display=%ux%u connector=%u crtc=%u\n",
        kms.fb.width,
        kms.fb.height,
        kms.connector_id,
        kms.crtc_id);
    rc = 0;
    while (keep_running) {
        pause();
    }

out:
    (void)unlink(A90_DISPLAY_MARKER);
    cleanup_kms(&kms);
    return rc;
}
