/*
 * Debian-side D-public HUD.
 *
 * This helper runs after switch_root inside the userdata Debian appliance.  It
 * materializes /dev/dri/card0 from sysfs, creates a DRM dumb framebuffer, and
 * presents a compact server-status HUD.  It does not open any network port.
 */
#include "a90_draw.h"

#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
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

#ifndef DRM_MODE_CONNECTED
#define DRM_MODE_CONNECTED 1
#endif

struct hud_kms {
    int fd;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t handle;
    struct drm_mode_modeinfo mode;
    struct a90_fb fb;
};

static volatile sig_atomic_t keep_running = 1;

static void on_signal(int signo) {
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

static int read_trimmed(const char *path, char *out, size_t out_size) {
    int fd;
    ssize_t nread;

    if (out_size == 0) {
        return -1;
    }
    out[0] = '\0';
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    nread = read(fd, out, out_size - 1);
    close(fd);
    if (nread < 0) {
        out[0] = '\0';
        return -1;
    }
    out[nread] = '\0';
    while (nread > 0 && (out[nread - 1] == '\n' || out[nread - 1] == '\r' ||
                         out[nread - 1] == ' ' || out[nread - 1] == '\t')) {
        out[--nread] = '\0';
    }
    return 0;
}

static int ensure_card0_node(char *path, size_t path_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;
    struct stat st;

    if (snprintf(path, path_size, "/dev/dri/card0") >= (int)path_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (stat(path, &st) == 0 && S_ISCHR(st.st_mode)) {
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
    if (mknod(path, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int get_resources(int fd,
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

static int fetch_connector(int fd,
                           uint32_t connector_id,
                           struct drm_mode_get_connector *conn,
                           struct drm_mode_modeinfo **modes_out,
                           uint32_t **encoders_out) {
    struct drm_mode_modeinfo *modes = NULL;
    uint32_t *encoders = NULL;
    uint32_t *props = NULL;
    uint64_t *prop_values = NULL;

    memset(conn, 0, sizeof(*conn));
    conn->connector_id = connector_id;
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
    free(props);
    free(prop_values);
    *modes_out = modes;
    *encoders_out = encoders;
    return 0;

oom:
    free(modes);
    free(encoders);
    free(props);
    free(prop_values);
    errno = ENOMEM;
    return -1;
}

static int fetch_encoder(int fd, uint32_t encoder_id, struct drm_mode_get_encoder *enc) {
    memset(enc, 0, sizeof(*enc));
    enc->encoder_id = encoder_id;
    return drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETENCODER, enc);
}

static int choose_output(int fd, struct hud_kms *kms) {
    struct drm_mode_card_res res;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t i;
    int rc = -1;

    if (get_resources(fd, &res, &crtcs, &connectors, &encoders) < 0) {
        return -1;
    }
    for (i = 0; i < res.count_connectors; ++i) {
        struct drm_mode_get_connector conn;
        struct drm_mode_modeinfo *modes = NULL;
        uint32_t *conn_encoders = NULL;
        uint32_t encoder_id = 0;
        struct drm_mode_get_encoder enc;

        if (fetch_connector(fd, connectors[i], &conn, &modes, &conn_encoders) < 0) {
            continue;
        }
        if (conn.connection == DRM_MODE_CONNECTED && conn.count_modes > 0) {
            encoder_id = conn.encoder_id;
            if (encoder_id == 0 && conn.count_encoders > 0) {
                encoder_id = conn_encoders[0];
            }
            if (encoder_id != 0 && fetch_encoder(fd, encoder_id, &enc) == 0) {
                kms->connector_id = conn.connector_id;
                kms->encoder_id = encoder_id;
                kms->crtc_id = enc.crtc_id != 0 ? enc.crtc_id : (res.count_crtcs > 0 ? crtcs[0] : 0);
                kms->mode = modes[0];
                rc = kms->crtc_id != 0 ? 0 : -1;
            }
        }
        free(modes);
        free(conn_encoders);
        if (rc == 0) {
            break;
        }
    }

    free(crtcs);
    free(connectors);
    free(encoders);
    if (rc < 0) {
        errno = ENODEV;
    }
    return rc;
}

static int init_kms(struct hud_kms *kms) {
    char path[128];
    struct drm_mode_create_dumb create;
    struct drm_mode_fb_cmd2 addfb2;
    struct drm_mode_map_dumb map_dumb;

    memset(kms, 0, sizeof(*kms));
    kms->fd = -1;
    kms->fb.pixels = MAP_FAILED;

    if (ensure_card0_node(path, sizeof(path)) < 0) {
        perror("ensure card0");
        return -1;
    }
    kms->fd = open(path, O_RDWR | O_CLOEXEC);
    if (kms->fd < 0) {
        perror("open card0");
        return -1;
    }
    (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_SET_MASTER, NULL);
    if (choose_output(kms->fd, kms) < 0) {
        perror("choose output");
        return -1;
    }

    memset(&create, 0, sizeof(create));
    create.width = kms->mode.hdisplay;
    create.height = kms->mode.vdisplay;
    create.bpp = 32;
    if (drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0) {
        perror("create dumb");
        return -1;
    }
    kms->handle = create.handle;
    kms->fb.width = create.width;
    kms->fb.height = create.height;
    kms->fb.stride = create.pitch;
    kms->fb.size = create.size;

    memset(&addfb2, 0, sizeof(addfb2));
    addfb2.width = create.width;
    addfb2.height = create.height;
    addfb2.pixel_format = DRM_FORMAT_XBGR8888;
    addfb2.handles[0] = create.handle;
    addfb2.pitches[0] = create.pitch;
    if (drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_ADDFB2, &addfb2) < 0) {
        perror("addfb2");
        return -1;
    }
    kms->fb_id = addfb2.fb_id;

    memset(&map_dumb, 0, sizeof(map_dumb));
    map_dumb.handle = create.handle;
    if (drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_MAP_DUMB, &map_dumb) < 0) {
        perror("map dumb");
        return -1;
    }
    kms->fb.pixels = mmap(NULL,
                          create.size,
                          PROT_READ | PROT_WRITE,
                          MAP_SHARED,
                          kms->fd,
                          (off_t)map_dumb.offset);
    if (kms->fb.pixels == MAP_FAILED) {
        perror("mmap dumb");
        return -1;
    }
    return 0;
}

static int present_kms(struct hud_kms *kms) {
    struct drm_mode_crtc setcrtc;
    uint32_t connector = kms->connector_id;

    memset(&setcrtc, 0, sizeof(setcrtc));
    setcrtc.crtc_id = kms->crtc_id;
    setcrtc.fb_id = kms->fb_id;
    setcrtc.set_connectors_ptr = (uintptr_t)&connector;
    setcrtc.count_connectors = 1;
    setcrtc.mode = kms->mode;
    setcrtc.mode_valid = 1;
    return drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_SETCRTC, &setcrtc);
}

static void cleanup_kms(struct hud_kms *kms) {
    if (kms->fb.pixels != MAP_FAILED) {
        munmap(kms->fb.pixels, kms->fb.size);
    }
    if (kms->fd >= 0 && kms->fb_id != 0) {
        uint32_t fb = kms->fb_id;
        (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_RMFB, &fb);
    }
    if (kms->fd >= 0 && kms->handle != 0) {
        struct drm_mode_destroy_dumb destroy;
        memset(&destroy, 0, sizeof(destroy));
        destroy.handle = kms->handle;
        (void)drm_ioctl_retry(kms->fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
    }
    if (kms->fd >= 0) {
        close(kms->fd);
    }
}

static bool pid_file_alive(const char *path) {
    char buf[32];
    long pid;
    char *end = NULL;

    if (read_trimmed(path, buf, sizeof(buf)) < 0) {
        return false;
    }
    pid = strtol(buf, &end, 10);
    if (end == buf || pid <= 1) {
        return false;
    }
    return kill((pid_t)pid, 0) == 0;
}

static bool tcp_port_listening(unsigned int port) {
    FILE *fp = fopen("/proc/net/tcp", "r");
    char line[256];
    bool found = false;

    if (fp == NULL) {
        return false;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        unsigned int local_port = 0;
        unsigned int state = 0;
        if (sscanf(line, " %*u: %*8X:%X %*8X:%*X %X", &local_port, &state) == 2 &&
            local_port == port && state == 0x0A) {
            found = true;
            break;
        }
    }
    fclose(fp);
    return found;
}

static void uptime_label(char *out, size_t out_size) {
    char raw[64];
    double seconds = 0.0;
    unsigned int minutes;
    unsigned int hours;

    if (read_trimmed("/proc/uptime", raw, sizeof(raw)) < 0) {
        snprintf(out, out_size, "UP ?");
        return;
    }
    sscanf(raw, "%lf", &seconds);
    minutes = (unsigned int)(seconds / 60.0);
    hours = minutes / 60U;
    minutes %= 60U;
    snprintf(out, out_size, "UP %02u:%02u", hours, minutes);
}

static void mem_label(char *out, size_t out_size) {
    FILE *fp = fopen("/proc/meminfo", "r");
    char key[64];
    char unit[32];
    unsigned long value;
    unsigned long total = 0;
    unsigned long available = 0;

    if (fp == NULL) {
        snprintf(out, out_size, "MEM ?");
        return;
    }
    while (fscanf(fp, "%63s %lu %31s\n", key, &value, unit) == 3) {
        if (strcmp(key, "MemTotal:") == 0) {
            total = value;
        } else if (strcmp(key, "MemAvailable:") == 0) {
            available = value;
        }
    }
    fclose(fp);
    if (total == 0) {
        snprintf(out, out_size, "MEM ?");
        return;
    }
    snprintf(out, out_size, "MEM %lu/%luMB", (total - available) / 1024UL, total / 1024UL);
}

static void battery_label(char *out, size_t out_size) {
    char cap[32];
    char status[32];

    if (read_trimmed("/sys/class/power_supply/battery/capacity", cap, sizeof(cap)) < 0) {
        snprintf(out, out_size, "BAT ?");
        return;
    }
    if (read_trimmed("/sys/class/power_supply/battery/status", status, sizeof(status)) < 0) {
        status[0] = '\0';
    }
    snprintf(out, out_size, "BAT %s%% %s", cap, status);
}

static void draw_line(struct a90_fb *fb, uint32_t x, uint32_t *y, const char *text, uint32_t color, uint32_t scale) {
    a90_draw_text_fit(fb, x, *y, text, color, scale, fb->width - x * 2U);
    *y += scale * 11U;
}

static void draw_card(struct a90_fb *fb,
                      uint32_t x,
                      uint32_t y,
                      uint32_t w,
                      uint32_t h,
                      const char *title) {
    a90_draw_rect(fb, x, y, w, h, 0x101820);
    a90_draw_rect(fb, x, y, w, 8, 0x1aa3ff);
    a90_draw_rect_outline(fb, x, y, w, h, 3, 0x2a4255);
    a90_draw_text_fit(fb, x + 18, y + 22, title, 0xffcc33, 5, w - 36);
}

static void render_hud(struct hud_kms *kms) {
    struct a90_fb *fb = &kms->fb;
    char debian[64] = "?";
    char pid1[64] = "?";
    char now[64];
    char up[64];
    char mem[64];
    char bat[64];
    char line[256];
    time_t t = time(NULL);
    struct tm tm_utc;
    uint32_t margin = fb->width / 18U;
    uint32_t y = fb->height / 12U;
    uint32_t card_w = fb->width - margin * 2U;
    uint32_t card_h = 270;
    uint32_t line_y;

    read_trimmed("/etc/debian_version", debian, sizeof(debian));
    read_trimmed("/proc/1/comm", pid1, sizeof(pid1));
    gmtime_r(&t, &tm_utc);
    strftime(now, sizeof(now), "%Y-%m-%d %H:%M UTC", &tm_utc);
    uptime_label(up, sizeof(up));
    mem_label(mem, sizeof(mem));
    battery_label(bat, sizeof(bat));

    a90_draw_clear(fb, 0x061019);
    a90_draw_rect(fb, 0, 0, fb->width, 56, 0x14395f);
    a90_draw_text_fit(fb, margin, 96, "A90 DEBIAN APPLIANCE", 0xffffff, 8, card_w);
    a90_draw_text_fit(fb, margin, 176, "D-PUBLIC SERVER READY", 0x88ee88, 5, card_w);

    draw_card(fb, margin, y + 210, card_w, card_h, "SYSTEM");
    line_y = y + 290;
    snprintf(line, sizeof(line), "DEBIAN %s  PID1 %s", debian, pid1);
    draw_line(fb, margin + 28, &line_y, line, 0xffffff, 5);
    draw_line(fb, margin + 28, &line_y, "/DEV/BLOCK/A90-USERDATA  EXT4 /", 0xbbbbbb, 4);
    snprintf(line, sizeof(line), "%s  %s  %s", up, mem, bat);
    draw_line(fb, margin + 28, &line_y, line, 0xffffff, 4);

    draw_card(fb, margin, y + 530, card_w, card_h, "NETWORK");
    line_y = y + 610;
    draw_line(fb, margin + 28, &line_y, "NCM0 192.168.7.2/24  HOST 192.168.7.1", 0xffffff, 5);
    snprintf(line, sizeof(line), "SSH %s  HTTP %s",
             tcp_port_listening(2222) ? "READY" : "DOWN",
             tcp_port_listening(8080) ? "READY" : "DOWN");
    draw_line(fb, margin + 28, &line_y, line, 0x88ee88, 5);
    snprintf(line, sizeof(line), "TUNNEL %s  %s",
             pid_file_alive("/run/a90-dpublic/cloudflared-live.pid") ? "RUNNING" : "STOPPED",
             now);
    draw_line(fb, margin + 28, &line_y, line, 0x88ee88, 4);

    draw_card(fb, margin, y + 850, card_w, card_h, "PUBLIC SERVICE");
    line_y = y + 930;
    draw_line(fb, margin + 28, &line_y, "EDGE: CLOUDFLARE QUICK TUNNEL", 0xffffff, 5);
    draw_line(fb, margin + 28, &line_y, "ORIGIN: 127.0.0.1:8080 LOOPBACK ONLY", 0xbbbbbb, 4);
    draw_line(fb, margin + 28, &line_y, "MARKER: A90_DPUBLIC_SMOKE_OK", 0x88ee88, 5);

    a90_draw_text_fit(fb,
                      margin,
                      fb->height - 110,
                      "A90 SERVER APPLIANCE / USB-NCM LOCAL ADMIN / OUTBOUND TUNNEL",
                      0xbbbbbb,
                      4,
                      card_w);
}

int main(int argc, char **argv) {
    struct hud_kms kms;
    unsigned int refresh_sec = 2;

    if (argc >= 2) {
        long parsed = strtol(argv[1], NULL, 10);
        if (parsed > 0 && parsed < 3600) {
            refresh_sec = (unsigned int)parsed;
        }
    }
    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);

    if (init_kms(&kms) < 0) {
        cleanup_kms(&kms);
        return 1;
    }
    fprintf(stderr,
            "a90-dpublic-hud display=%ux%u connector=%u crtc=%u refresh=%us\n",
            kms.fb.width,
            kms.fb.height,
            kms.connector_id,
            kms.crtc_id,
            refresh_sec);
    while (keep_running) {
        render_hud(&kms);
        if (present_kms(&kms) < 0) {
            perror("setcrtc");
            cleanup_kms(&kms);
            return 1;
        }
        sleep(refresh_sec);
    }
    cleanup_kms(&kms);
    return 0;
}
